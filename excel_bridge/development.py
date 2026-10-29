"""Persistent parish workflows, recurring transfers and verified whole-system snapshots."""
import math
import hashlib
import io
import json
import os
import secrets
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

from catalog import macro_signature
from exceptions import check_makeup, day


def digest(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda:source.read(65536),b''):
            value.update(chunk)
    return value.hexdigest()


def recover_transactions(root, state_dir, trusted_signature):
    """Roll back an interrupted multi-workbook change before reading the catalog."""
    root, state_dir = Path(root).resolve(), Path(state_dir).resolve()
    for journal_path in list((state_dir/'transfers').glob('*/journal.json'))+list((state_dir/'restores').glob('*/journal.json'))+list((state_dir/'parity-transactions').glob('*/journal.json')):
        journal=json.loads(journal_path.read_text(encoding='utf-8'))
        if journal['status']!='prepared':
            continue
        for f in journal['files']:
            target, original=Path(f['path']).resolve(),Path(f['original']).resolve()
            database=target==state_dir/'attendance.sqlite3'
            if (not database and not target.is_relative_to(root)) or not original.is_relative_to(journal_path.parent):
                raise ValueError('Đường dẫn khôi phục giao dịch không hợp lệ.')
            if digest(original)!=f['oldSha'] or digest(target) not in (f['oldSha'],f['newSha']):
                raise ValueError('Giao dịch bị gián đoạn và file đã sửa bên ngoài. Cần kiểm tra bản sao trước khi mở dịch vụ.')
            if not database and macro_signature(original)[0]!=trusted_signature:
                raise ValueError('VBA trong bản sao giao dịch không hợp lệ.')
        for f in journal['files']:
            target=Path(f['path'])
            stage=target.parent/('.recover-'+secrets.token_hex(8)+target.suffix)
            shutil.copy2(f['original'],stage)
            os.replace(stage,target)
        journal['status']='rolled-back'
        journal_path.write_text(json.dumps(journal),encoding='utf-8')


class DevelopmentFeatures:
    def init_development(self):
        with self.db() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS recurring_mass(id TEXT PRIMARY KEY, code TEXT, original_weekday INTEGER,
                target_weekday INTEGER, starts TEXT, ends TEXT, actor TEXT, reason TEXT, status TEXT, created_at TEXT);
              CREATE TABLE IF NOT EXISTS student_status(id TEXT PRIMARY KEY, code TEXT, status TEXT, effective_day TEXT,
                actor TEXT, reason TEXT, stamp TEXT);
              CREATE TABLE IF NOT EXISTS care_notes(id TEXT PRIMARY KEY, code TEXT, kind TEXT, content TEXT,
                actor TEXT, due_day TEXT, status TEXT, created_at TEXT, updated_at TEXT);
              CREATE TABLE IF NOT EXISTS management_events(id INTEGER PRIMARY KEY, entity TEXT, entity_id TEXT,
                action TEXT, actor TEXT, reason TEXT, stamp TEXT);
              CREATE TABLE IF NOT EXISTS settings(name TEXT PRIMARY KEY, value TEXT);
              CREATE TABLE IF NOT EXISTS year_plans(id TEXT PRIMARY KEY, start_year INTEGER, placements TEXT,
                actor TEXT, reason TEXT, status TEXT, created_at TEXT, export_id TEXT);
            ''')
            if 'recurring_id' not in {r['name'] for r in db.execute('PRAGMA table_info(requests)')}:
                db.execute('ALTER TABLE requests ADD COLUMN recurring_id TEXT')

    def management_event(self, db, entity, identifier, action, actor, reason):
        db.execute('INSERT INTO management_events(entity,entity_id,action,actor,reason,stamp) VALUES (?,?,?,?,?,?)',
                   (entity, identifier, action, actor, reason, self.stamp()))

    def development_public(self):
        with self.db() as db:
            return {
                'recurringMass': [dict(r) for r in db.execute('SELECT * FROM recurring_mass ORDER BY created_at DESC')],
                'studentStatuses': [dict(r) for r in db.execute('SELECT * FROM student_status ORDER BY effective_day,stamp,id')],
                'careNotes': [dict(r) for r in db.execute('SELECT * FROM care_notes ORDER BY updated_at DESC')],
                'managementEvents': [dict(r) for r in db.execute('SELECT * FROM management_events ORDER BY id DESC LIMIT 200')],
                'yearPlans': [dict(r) for r in db.execute('SELECT * FROM year_plans ORDER BY created_at DESC')],
            }

    def student_active(self, code, when):
        person=self.catalog.students.get(code)
        if person and getattr(self,'management',None) and self.management.class_statuses().get(person['classId']):
            return False
        with self.db() as db:
            row = db.execute('SELECT status FROM student_status WHERE code=? AND effective_day<=? '
                             'ORDER BY effective_day DESC,stamp DESC,rowid DESC LIMIT 1', (code, when)).fetchone()
        return row is None or row['status'] == 'active'

    def obligation(self, student, original, activity):
        if not self.student_active(student['id'], day(original)):
            raise ValueError('Thiếu nhi đang tạm nghỉ/nghỉ học vào ngày này. Cập nhật trạng thái trước khi điểm danh.')
        return super().obligation(student, original, activity)

    def session_people(self, session):
        return [s for s in super().session_people(session) if self.student_active(s['id'], session['date'])]

    def set_student_status(self, values):
        self.catalog.refresh()
        actor, reason = self.actor(values)
        code = str(values.get('code', '')).strip().upper()
        status = values.get('status')
        effective = day(values.get('effectiveDate'))
        if code not in self.catalog.students or status not in ('active', 'paused', 'left'):
            raise ValueError('Thiếu nhi hoặc trạng thái không hợp lệ.')
        # Status changes never alter historical marks, finalized sessions or approved requests.
        if effective < datetime.now(self.local_tz).date().isoformat():
            raise ValueError('Ngày hiệu lực phải từ hôm nay; dữ liệu chuyên cần cũ được giữ nguyên.')
        with self.db() as db:
            pending = db.execute("SELECT 1 FROM requests WHERE code=? AND status IN ('pending','approved') "
                                 "AND (day>=? OR COALESCE(exception_day,target_day)>=?)", (code, effective, effective)).fetchone()
            if status != 'active' and pending:
                raise ValueError('Còn đơn tương lai đang chờ/đã duyệt. Huỷ hoặc xử lý các đơn đó trước khi cho nghỉ.')
            identifier = secrets.token_hex(12)
            db.execute('INSERT INTO student_status VALUES (?,?,?,?,?,?,?)',
                       (identifier, code, status, effective, actor, reason, self.stamp()))
            self.management_event(db, 'student', code, status, actor, f'{effective}: {reason}')
        return {'saved': True, 'state': self.bootstrap()}

    def recurring_preview(self, values):
        self.catalog.refresh()
        code = str(values.get('code', '')).strip().upper()
        student = self.catalog.students.get(code)
        original, target = values.get('originalWeekday'), values.get('targetWeekday')
        if not student or type(original) is not int or type(target) is not int or original not in range(6) or target not in range(6) or original == target:
            raise ValueError('Chọn thiếu nhi và hai thứ khác nhau từ thứ Hai đến thứ Bảy.')
        starts, ends = day(values.get('startDate')), day(values.get('endDate'))
        if ends < starts or (date.fromisoformat(ends) - date.fromisoformat(starts)).days > 366:
            raise ValueError('Khoảng hiệu lực tối đa một năm và ngày kết thúc không sớm hơn ngày bắt đầu.')
        occurrences, issues = [], []
        requests = self.requests()
        for original_day in self.catalog.classes[student['classId']]['calendar']['mass']:
            d = date.fromisoformat(original_day)
            if not starts <= original_day <= ends or d.weekday() != original:
                continue
            actual = (d + timedelta(days=target-original)).isoformat()
            if not starts <= actual <= ends:
                issues.append(f'{original_day}: ngày thay thế {actual} ngoài khoảng hiệu lực.')
                continue
            try:
                check_makeup(original_day, actual, 'mass')
                session = self.obligation(student, original_day, 'mass')
                if self.status_at(code, original_day, 'mass'):
                    raise ValueError('Ngày gốc đã có trạng thái trong Excel.')
                if self.locked(session, student['classId']) or self.locked({'date': actual, 'activity': 'mass'}, student['classId']):
                    raise ValueError('Buổi gốc hoặc buổi thay thế đã chốt.')
                if not self.student_active(code, actual) or student['enrolledFrom'] and actual < student['enrolledFrom']:
                    raise ValueError('Ngày thay thế ngoài thời gian đang học.')
                if any(r['code'] == code and r['activity'] == 'mass' and r['day'] == original_day and r['status'] in ('pending','approved','completed') for r in requests):
                    raise ValueError('Ngày gốc đã có đơn.')
                self.check_makeup_available(code, actual)
                occurrences.append({'date': original_day, 'targetDate': actual})
            except ValueError as error:
                issues.append(f'{original_day}: {error}')
        if not occurrences and not issues:
            issues.append('Không có buổi lễ gốc phù hợp trong lịch Excel.')
        plan = {'code': code, 'originalWeekday': original, 'targetWeekday': target, 'startDate': starts,
                'endDate': ends, 'occurrences': occurrences, 'issues': issues}
        plan['token'] = hashlib.sha256(json.dumps(plan, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        return plan

    def create_recurring(self, values):
        actor, reason = self.actor(values)
        plan = self.recurring_preview(values)
        if plan['issues']:
            raise ValueError('Lịch có xung đột. Xem trước và chỉnh khoảng hiệu lực trước khi lưu.')
        if values.get('previewToken') != plan['token']:
            raise ValueError('Lịch đã thay đổi. Xem trước lại trước khi xác nhận.')
        identifier, stamp = secrets.token_hex(12), self.stamp()
        with self.db() as db:
            db.execute('INSERT INTO recurring_mass VALUES (?,?,?,?,?,?,?,?,?,?)',
                       (identifier, plan['code'], plan['originalWeekday'], plan['targetWeekday'], plan['startDate'], plan['endDate'], actor, reason, 'active', stamp))
            for occurrence in plan['occurrences']:
                rid = secrets.token_hex(12)
                db.execute('''INSERT INTO requests(id,group_id,code,kind,activity,day,target_day,reason,author,status,
                              reviewer,reviewed_at,created_at,recurring_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                           (rid, rid, plan['code'], 'makeup', 'mass', occurrence['date'], occurrence['targetDate'], reason, actor, 'approved', actor, stamp, stamp, identifier))
                self.request_event(db, rid, 'created', actor, 'Từ lịch hằng tuần. ' + reason)
                self.request_event(db, rid, 'approve', actor, 'Xác nhận lịch hằng tuần. ' + reason)
            self.management_event(db, 'recurring', identifier, 'created', actor, reason)
        return {'saved': True, 'count': len(plan['occurrences']), 'state': self.bootstrap()}

    def stop_recurring(self, values):
        actor, reason = self.actor(values)
        effective = day(values.get('effectiveDate'))
        if effective < datetime.now(self.local_tz).date().isoformat():
            raise ValueError('Chỉ dừng từ hôm nay hoặc ngày tương lai; các buổi cũ giữ lịch sử.')
        self.catalog.refresh()
        with self.db() as db:
            recurring = db.execute('SELECT * FROM recurring_mass WHERE id=?', (values.get('id'),)).fetchone()
            if not recurring:
                raise ValueError('Không tìm thấy lịch.')
            records = list(db.execute("SELECT * FROM requests WHERE recurring_id=? AND status='approved' AND day>=? AND COALESCE(exception_day,target_day)>=?", (recurring['id'], effective, effective)))
            for r in records:
                student = self.catalog.students[r['code']]
                if self.status_at(r['code'], r['day'], 'mass') or self.locked({'date': r['day'], 'activity': 'mass'}, student['classId']):
                    raise ValueError('Có buổi đã chốt hoặc đã có dữ liệu; xử lý từng đơn trước khi dừng lịch.')
                db.execute("UPDATE requests SET status='cancelled' WHERE id=?", (r['id'],))
                self.request_event(db, r['id'], 'cancel', actor, 'Dừng lịch từ ' + effective + '. ' + reason)
            db.execute("UPDATE recurring_mass SET status='stopped' WHERE id=?", (recurring['id'],))
            self.management_event(db, 'recurring', recurring['id'], 'stopped', actor, f'Từ {effective}: {reason}')
        return {'saved': True, 'count': len(records), 'state': self.bootstrap()}

    def save_care_note(self, values):
        self.catalog.refresh()
        actor, content = self.actor({**values, 'reason': values.get('content')})
        code = str(values.get('code', '')).strip().upper()
        kind, status = values.get('kind', 'contact'), values.get('status', 'open')
        due = day(values['dueDate']) if values.get('dueDate') else None
        if code not in self.catalog.students or kind not in ('contact','visit','followup') or status not in ('open','following','done'):
            raise ValueError('Thiếu nhi, loại ghi chú hoặc trạng thái không hợp lệ.')
        identifier, stamp = values.get('id') or secrets.token_hex(12), self.stamp()
        with self.db() as db:
            existing = db.execute('SELECT * FROM care_notes WHERE id=?', (identifier,)).fetchone()
            if values.get('id') and (not existing or existing['code'] != code):
                raise ValueError('Không tìm thấy ghi chú của thiếu nhi.')
            db.execute('''INSERT INTO care_notes VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                          kind=excluded.kind,content=excluded.content,actor=excluded.actor,due_day=excluded.due_day,
                          status=excluded.status,updated_at=excluded.updated_at''',
                       (identifier, code, kind, content, actor, due, status, existing['created_at'] if existing else stamp, stamp))
            before = f' Trước: {existing["status"]}; {existing["content"]}.' if existing else ''
            self.management_event(db, 'care', identifier, 'updated' if existing else 'created', actor, f'{status}: {content}.{before}')
        return {'saved': True, 'state': self.bootstrap()}

    def snapshots(self):
        folder = self.state_dir / 'snapshots'
        results = []
        if folder.exists():
            for p in sorted(folder.glob('*/manifest.json'), reverse=True):
                try:
                    m = json.loads(p.read_text(encoding='utf-8'))
                    results.append({**{k: m[k] for k in ('id','stamp','label','year','count','actor')},
                        'includesAccounts':bool(m.get('includesAccounts')),'archivedYearCount':len(m.get('archivedYears',[])),
                        'preparedYearCount':len(m.get('preparedYears',[]))})
                except (ValueError, KeyError):
                    continue
        return results

    def settings(self):
        with self.db() as db:
            return {r['name']: r['value'] for r in db.execute('SELECT * FROM settings')}

    def system_info(self):
        self.catalog.refresh()
        settings = self.settings()
        return {'snapshots': self.snapshots(), 'backupHours': int(settings.get('backupHours', 24)),
                'dataRoot': str(self.catalog.root), 'stateDir': str(self.state_dir.resolve()),
                'localFiles': len(self.catalog.classes), 'cloudStatus': 'unverified',
                'lastBackupError': settings.get('lastBackupError',''), 'lastBackupAt': settings.get('lastBackupAt','')}

    def snapshot(self, values):
        if not values.get('_manager'):
            raise ValueError('Tạo sao lưu toàn hệ thống trên máy Excel.')
        self.catalog.refresh()
        identifier = datetime.now(self.local_tz).strftime('%Y%m%d-%H%M%S-') + secrets.token_hex(4)
        folder = self.state_dir / 'snapshots'
        folder.mkdir(exist_ok=True)
        stage = folder / ('.' + identifier)
        stage.mkdir()
        files = []
        try:
            for info in self.catalog.classes.values():
                relative = info['path'].relative_to(self.catalog.root).as_posix()
                target = stage / 'workbooks' / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                before = digest(info['path'])
                shutil.copy2(info['path'], target)
                if digest(target) != before or digest(info['path']) != before:
                    raise ValueError('File thay đổi trong lúc sao lưu. Thử lại khi không sửa Excel.')
                files.append({'classId': info['id'], 'relative': relative, 'sha256': before})
            with self.db() as db:
                destination = sqlite3.connect(stage / 'attendance.sqlite3')
                try:
                    db.backup(destination)
                finally:
                    destination.close()
            # Recheck all sources after the database snapshot for a consistent workbook set.
            if any(digest(self.catalog.root / f['relative']) != f['sha256'] for f in files):
                raise ValueError('File đã thay đổi trong lúc sao lưu. Chưa tạo bản sao hoàn chỉnh.')
            manifest = {'id': identifier, 'stamp': self.stamp(), 'label': str(values.get('label') or 'Sao lưu thủ công')[:100],
                        'actor': str(values.get('actor') or 'Máy Excel')[:100], 'year': self.catalog.public()['year'], 'count': len(files),
                        'files': files, 'databaseSha256': digest(stage / 'attendance.sqlite3')}
            if getattr(self, 'management', None):
                self.management.backup_extras(stage, manifest)
            (stage / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
            os.replace(stage, folder / identifier)
            with self.db() as db:
                for name, value in (('lastBackupAt', manifest['stamp']), ('lastBackupError','')):
                    db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (name, value))
                self.management_event(db, 'snapshot', identifier, 'created', manifest['actor'], manifest['label'])
            return {'saved': True, 'snapshot': manifest, 'system': self.system_info()}
        except Exception:
            shutil.rmtree(stage, ignore_errors=True)
            raise

    def snapshot_folder(self, identifier):
        if not isinstance(identifier, str) or not identifier or any(c not in '0123456789abcdef-' for c in identifier):
            raise ValueError('Mã sao lưu không hợp lệ.')
        folder = (self.state_dir / 'snapshots' / identifier).resolve()
        if not folder.is_dir() or not folder.is_relative_to((self.state_dir / 'snapshots').resolve()):
            raise ValueError('Không tìm thấy bản sao lưu.')
        return folder

    def snapshot_export(self, identifier):
        folder = self.snapshot_folder(identifier)
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
            for p in folder.rglob('*'):
                if p.is_file():
                    archive.write(p, p.relative_to(folder).as_posix())
        return stream.getvalue(), f'XuanHoa-{identifier}.zip', 'application/zip'

    def restore_preview(self, values):
        if not values.get('_manager'):
            raise ValueError('Xem trước khôi phục trên máy Excel.')
        if getattr(self,'management',None): return self.management.workbooks_restore_preview(values)
        folder = self.snapshot_folder(values.get('id'))
        manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
        self.catalog.refresh()
        expected = {str(c['path'].relative_to(self.catalog.root).as_posix()) for c in self.catalog.classes.values()}
        supplied = {f['relative'] for f in manifest['files']}
        if supplied != expected or len(supplied) != len(manifest['files']):
            raise ValueError('Danh sách file/lớp hiện tại khác bản sao. Không phục hồi tự động.')
        current = {}
        for f in manifest['files']:
            target = (self.catalog.root / f['relative']).resolve()
            source = (folder / 'workbooks' / f['relative']).resolve()
            if not target.is_relative_to(self.catalog.root) or not source.is_relative_to(folder / 'workbooks'):
                raise ValueError('Đường dẫn trong bản sao không hợp lệ.')
            if not source.is_file() or digest(source) != f['sha256']:
                raise ValueError('Bản sao Excel thiếu hoặc không khớp mã kiểm tra.')
            if macro_signature(source)[0] != self.catalog.trusted_signature:
                raise ValueError('Macro trong bản sao không đúng mẫu đã kiểm tra.')
            current[f['relative']] = digest(target)
        database = folder / 'attendance.sqlite3'
        if not database.is_file() or digest(database) != manifest['databaseSha256']:
            raise ValueError('Cơ sở dữ liệu sao lưu không khớp mã kiểm tra.')
        with sqlite3.connect(database) as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Cơ sở dữ liệu sao lưu bị hỏng.')
        current['database'] = digest(self.database)
        token = hashlib.sha256(json.dumps(current, sort_keys=True).encode()).hexdigest()
        return {'id': manifest['id'], 'stamp': manifest['stamp'], 'count': len(supplied), 'token': token,
                'label': manifest['label'], 'currentHashes': current}

    def restore_snapshot(self, values):
        if not values.get('_manager'):
            raise ValueError('Chỉ phục hồi trên máy Excel.')
        if getattr(self,'management',None): return self.management.restore_workbooks(values)
        actor, reason = self.actor(values)
        preview = self.restore_preview(values)
        if values.get('previewToken') != preview['token'] or values.get('confirmation') != 'KHÔI PHỤC':
            raise ValueError('Xem trước lại và nhập KHÔI PHỤC để xác nhận thay toàn bộ dữ liệu.')
        # Ensure every source is writable through Excel before modifying any file.
        from native import ExcelEngine
        if self.engine is None:
            self.engine = ExcelEngine(self.catalog)
        app = self.engine.excel()
        for info in self.catalog.classes.values():
            book = app.Workbooks.Open(str(info['path']), UpdateLinks=0, ReadOnly=False, Notify=False)
            try:
                if book.ReadOnly:
                    raise ValueError('Đóng tất cả file lớp trong Excel trước khi phục hồi.')
            finally:
                book.Close(SaveChanges=False)
        rollback = self.snapshot({'_manager': True, 'actor': actor, 'label': 'Trước khôi phục: ' + reason})['snapshot']
        with self.db() as db:issued_before=[r['code'] for r in db.execute('SELECT code FROM issued_codes')]
        # snapshot() writes settings/audit in SQLite, so use the post-snapshot database as rollback state.
        folder = self.snapshot_folder(values['id'])
        rollback_folder = self.snapshot_folder(rollback['id'])
        changed = []
        transaction=self.state_dir/'restores'/(datetime.now(self.local_tz).strftime('%Y%m%d-%H%M%S-')+secrets.token_hex(4))
        transaction.mkdir(parents=True)
        with tempfile.TemporaryDirectory(prefix='.restore-', dir=self.catalog.root) as temporary:
            temporary = Path(temporary)
            db_rollback = transaction / 'database-before.sqlite3'
            shutil.copy2(self.database, db_rollback)
            manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
            journal={'status':'prepared','files':[]}
            for index,f in enumerate(manifest['files']):
                original=transaction/f'original-{index}.xlsm'
                shutil.copy2(rollback_folder/'workbooks'/f['relative'],original)
                journal['files'].append({'path':str((self.catalog.root/f['relative']).resolve()),'original':str(original.resolve()),
                                         'oldSha':digest(original),'newSha':f['sha256']})
            journal['files'].append({'path':str(self.database.resolve()),'original':str(db_rollback.resolve()),
                                     'oldSha':digest(db_rollback),'newSha':manifest['databaseSha256']})
            prepared_db=transaction/'database-after.sqlite3'
            shutil.copy2(folder/'attendance.sqlite3',prepared_db)
            reserved_db=sqlite3.connect(prepared_db)
            try:
                with reserved_db:
                    reserved_db.execute('CREATE TABLE IF NOT EXISTS issued_codes(code TEXT PRIMARY KEY, stamp TEXT)')
                    reserved_db.executemany('INSERT OR IGNORE INTO issued_codes VALUES (?,?)',[(code,self.stamp()) for code in issued_before])
            finally:reserved_db.close()
            journal['files'][-1]['newSha']=digest(prepared_db)
            journal_path=transaction/'journal.json'
            journal_path.write_text(json.dumps(journal),encoding='utf-8')
            try:
                manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
                for f in manifest['files']:
                    target = self.catalog.root / f['relative']
                    if digest(target) != preview['currentHashes'][f['relative']]:
                        raise ValueError('Excel thay đổi sau khi xem trước. Chưa phục hồi.')
                    staged = temporary / (secrets.token_hex(8) + '.xlsm')
                    shutil.copy2(folder / 'workbooks' / f['relative'], staged)
                    os.replace(staged, target)
                    changed.append(f['relative'])
                staged_db = self.state_dir / ('.restore-' + secrets.token_hex(8) + '.sqlite3')
                shutil.copy2(prepared_db, staged_db)
                os.replace(staged_db, self.database)
                self.catalog.stamps = {}
                self.catalog.refresh()
                journal['status']='committed'
                journal_path.write_text(json.dumps(journal),encoding='utf-8')
                self.init_development()
                self.init_parity()
                self._grades=None
                with self.db() as db:
                    self.management_event(db, 'snapshot', values['id'], 'restored', actor, reason)
            except Exception:
                for relative in reversed(changed):
                    source = rollback_folder / 'workbooks' / relative
                    staged = temporary / (secrets.token_hex(8) + '.xlsm')
                    shutil.copy2(source, staged)
                    os.replace(staged, self.catalog.root / relative)
                shutil.copy2(db_rollback, self.database)
                self.catalog.stamps = {}
                self.catalog.refresh()
                journal['status']='rolled-back'
                self._grades=None
                journal_path.write_text(json.dumps(journal),encoding='utf-8')
                raise
        return {'saved': True, 'state': self.bootstrap(), 'system': self.system_info()}

    def backup_settings(self, values):
        if not values.get('_manager') or type(values.get('hours')) is not int or values['hours'] not in (0,12,24,168):
            raise ValueError('Chọn lịch sao lưu trên máy Excel: tắt, 12 giờ, 24 giờ hoặc 7 ngày.')
        with self.db() as db:
            db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', ('backupHours', str(values['hours'])))
        return {'saved': True, 'system': self.system_info()}

    def transfer_preview(self, values):
        self.catalog.refresh()
        code = str(values.get('code','')).strip().upper()
        student = self.catalog.students.get(code)
        target = self.catalog.classes.get(values.get('classId'))
        if not student or not target or target['id'] == student['classId']:
            raise ValueError('Chọn thiếu nhi và lớp đích khác lớp hiện tại.')
        issues = []
        if target['count'] >= 40:
            issues.append('Lớp đích đã đủ 40 em theo mẫu Excel.')
        with self.db() as db:
            active = db.execute("SELECT 1 FROM requests WHERE code=? AND status IN ('pending','approved')", (code,)).fetchone()
            if active:
                issues.append('Xử lý/dừng đơn đang chờ hoặc đã duyệt trước khi chuyển lớp.')
        source = self.catalog.classes[student['classId']]
        for key in self.catalog.marks:
            d, activity, mark_code = key.split('|')
            if mark_code == code and (d,activity) not in target['targets']:
                issues.append(f'{d}: lớp đích không có cột {activity} cho dữ liệu cũ.')
        # All old marks must remain representable; calendars may differ across levels.
        fingerprint = {'source': digest(source['path']), 'target': digest(target['path']), 'code': code,
                       'classId': target['id'], 'issues': issues}
        token = hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()
        return {'code': code, 'classId': target['id'], 'issues': issues, 'token': token,
                'description': f'{student["name"]}: {source["name"]} → {target["name"]}. Chuyển hồ sơ, điểm và các buổi đã ghi nhận trong năm; giữ nguyên mã.'}

    def transfer_student(self, values):
        if not values.get('_manager'):
            raise ValueError('Chuyển lớp trên máy Excel.')
        actor, reason = self.actor(values)
        plan = self.transfer_preview(values)
        if plan['issues'] or values.get('previewToken') != plan['token']:
            raise ValueError('Lớp/lịch đã thay đổi hoặc có xung đột. Xem trước lại trước khi chuyển.')
        from native import ExcelEngine
        if self.engine is None:
            self.engine = ExcelEngine(self.catalog)
        backup = self.snapshot({'_manager': True, 'actor': actor, 'label': 'Trước chuyển lớp ' + plan['code']})['snapshot']
        if self.transfer_preview(values)['token']!=plan['token']:
            raise ValueError('File thay đổi sau khi xác nhận. Xem trước chuyển lớp lại.')
        old_class = self.catalog.students[plan['code']]['classId']
        self.engine.transfer_student(plan['code'], plan['classId'])
        with self.db() as db:
            self.management_event(db, 'student', plan['code'], 'transferred', actor,
                                  f'{old_class} → {plan["classId"]}; sao lưu {backup["id"]}. {reason}')
        return {'saved': True, 'state': self.bootstrap()}

    def year_preview(self, values):
        self.catalog.refresh()
        year = values.get('startYear')
        current_year = int(self.catalog.public()['year'][:4])
        if type(year) is not int or year not in range(current_year+1,2100):
            raise ValueError('Chọn năm bắt đầu sau năm học hiện tại, đến 2099.')
        placements = values.get('placements')
        if not isinstance(placements,list) or len(placements)!=len(self.catalog.students):
            raise ValueError('Danh sách lên lớp phải bao gồm từng thiếu nhi hiện tại.')
        codes,counts,issues=set(),{},[]
        results = {}
        for p in placements:
            if not isinstance(p,dict) or p.get('code') not in self.catalog.students or p['code'] in codes:
                raise ValueError('Mã thiếu nhi không hợp lệ hoặc bị trùng.')
            codes.add(p['code'])
            if p.get('autoApproved') is True:
                cid = self.catalog.students[p['code']]['classId']
                if cid not in results:
                    results[cid] = self.read_grades(cid, 3)
                report = results[cid]
                row = next((r for r in report['students'] if r['code'] == p['code']), {})
                thresholds = report.get('thresholds', {})
                numeric = lambda v: type(v) in (int, float) and math.isfinite(v)
                valid = (not report.get('calculationIssues') and row.get('assessment') == 'ĐẠT'
                    and all(numeric(v) for v in [row.get('diemGiaoLy'), row.get('combinedMassScore'), thresholds.get('catechism'), thresholds.get('attendance')])
                    and row['diemGiaoLy'] >= thresholds['catechism'] and row['combinedMassScore'] >= thresholds['attendance'])
                if not valid or not report.get('revision') or p.get('gradeRevision') != report['revision']:
                    issues.append(p['code']+': kết quả đã đổi hoặc chưa đủ điều kiện tự động lên lớp. Mở lại danh sách để đọc kết quả mới.')
            if p.get('classId') not in self.catalog.classes and p.get('classId')!='graduate':
                issues.append(p['code']+': chưa chọn lớp đích.')
            elif p['classId']!='graduate':
                counts[p['classId']]=counts.get(p['classId'],0)+1
            if p.get('approved') is not True:
                issues.append(p['code']+': chưa duyệt lên lớp.')
        for identifier,count in counts.items():
            if count>40:
                issues.append(self.catalog.classes[identifier]['name']+f': {count} em, vượt 40 dòng.')
        fingerprint={'startYear':year,'placements':placements,'hashes':{i:digest(c['path']) for i,c in self.catalog.classes.items()}}
        return {'startYear':year,'placements':placements,'issues':issues,'counts':counts,
                'token':hashlib.sha256(json.dumps(fingerprint,sort_keys=True).encode()).hexdigest()}

    def save_year_plan(self, values):
        if not values.get('_manager'):
            raise ValueError('Lập kế hoạch năm học trên máy Excel.')
        actor,reason=self.actor(values)
        plan=self.year_preview(values)
        identifier=secrets.token_hex(12)
        with self.db() as db:
            db.execute('INSERT INTO year_plans VALUES (?,?,?,?,?,?,?,?)',
                       (identifier,plan['startYear'],json.dumps(plan['placements']),actor,reason,'draft',self.stamp(),None))
            self.management_event(db,'year',identifier,'draft',actor,reason)
        return {'saved':True,'id':identifier,'state':self.bootstrap()}

    def prepare_year(self, values):
        if not values.get('_manager'):
            raise ValueError('Tạo bộ Excel năm mới trên máy Excel.')
        actor,reason=self.actor(values)
        plan=self.year_preview(values)
        if plan['issues'] or values.get('previewToken')!=plan['token']:
            raise ValueError('Duyệt từng em và xử lý sức chứa, rồi xem trước lại trước khi tạo năm mới.')
        from native import ExcelEngine
        if self.engine is None:
            self.engine=ExcelEngine(self.catalog)
        snapshot=self.snapshot({'_manager':True,'actor':actor,'label':'Lưu trữ trước tạo năm học mới'})['snapshot']
        if self.year_preview(values)['token']!=plan['token']:
            raise ValueError('Sổ thay đổi sau khi xác nhận. Xem trước năm mới lại.')
        identifier=datetime.now(self.local_tz).strftime('%Y%m%d-%H%M%S-')+secrets.token_hex(4)
        folder=self.state_dir/'year_exports'/identifier
        with self.db() as db:plan['issuedCodes']=[r['code'] for r in db.execute('SELECT code FROM issued_codes ORDER BY code')]
        self.engine.prepare_year(plan,folder)
        with self.db() as db:
            db.execute('INSERT INTO year_plans VALUES (?,?,?,?,?,?,?,?)',
                       (identifier,plan['startYear'],json.dumps(plan['placements']),actor,reason,'prepared',self.stamp(),identifier))
            self.management_event(db,'year',identifier,'prepared',actor,f'Sao lưu {snapshot["id"]}. {reason}')
        return {'saved':True,'id':identifier,'path':str(folder.resolve()),'state':self.bootstrap()}

    def year_export(self, identifier):
        if not isinstance(identifier,str) or not identifier or any(c not in '0123456789abcdef-' for c in identifier):
            raise ValueError('Mã bộ năm học không hợp lệ.')
        folder=(self.state_dir/'year_exports'/identifier).resolve()
        if not folder.is_dir() or not folder.is_relative_to((self.state_dir/'year_exports').resolve()):
            raise ValueError('Không tìm thấy bộ Excel đã tạo.')
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
            for p in folder.glob('*.xlsm'):
                archive.write(p,p.name)
            archive.write(folder/'manifest.json','manifest.json')
        return stream.getvalue(),f'XuanHoa-NamHoc-{identifier}.zip','application/zip'

    def scheduled_backup(self):
        settings = self.settings()
        hours = int(settings.get('backupHours', 24))
        if not hours:
            return
        previous = settings.get('lastBackupAt')
        if previous and (datetime.now(self.local_tz)-datetime.fromisoformat(previous)).total_seconds() < hours*3600:
            return
        try:
            self.snapshot({'_manager': True, 'actor': 'Sao lưu định kỳ', 'label': 'Sao lưu định kỳ'})
        except Exception as error:
            with self.db() as db:
                db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', ('lastBackupError', str(error)[:500]))
