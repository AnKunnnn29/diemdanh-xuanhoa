"""Management console, scoped reminders and registered school-year workspaces."""
import base64
import csv
import hashlib
import io
import json
import os
import re
import secrets
import shutil
import sqlite3
import tempfile
from collections import Counter
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path

from accounts import AccessError
from catalog import Catalog, macro_signature
from development import digest
from exceptions import normalize_vi
from validation import profile_date


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def csv_bytes(rows):
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    for row in rows:
        writer.writerow([("'"+str(v)) if str(v).lstrip().startswith(('=','+','-','@')) else v for v in row])
    return ('\ufeff'+output.getvalue()).encode()


def recover_management(base, trusted):
    """Recover management journals before Catalog opens any changed workbooks."""
    base = Path(base).resolve()
    registry_path = base/'school-years.json'
    if not registry_path.exists(): return
    registry = json.loads(registry_path.read_text(encoding='utf-8'))
    roots = [Path(y['root']).resolve() for y in registry['years']]
    states = [Path(y['state']).resolve() for y in registry['years']]
    for journal_path in (base/'management-transactions').glob('*/journal.json'):
        journal = json.loads(journal_path.read_text(encoding='utf-8'))
        if journal['status'] != 'prepared': continue
        for item in journal['files']:
            target = Path(item['path']).resolve()
            backup = Path(item['original']).resolve()
            allowed = (target == base/'accounts.sqlite3' or target == registry_path or
                       any(target == state/'attendance.sqlite3' for state in states) or
                       (target.suffix.lower()=='.xlsm' and any(target.is_relative_to(root) for root in roots)))
            if not allowed or not backup.is_relative_to(journal_path.parent):
                raise ValueError('Đường dẫn giao dịch quản lý không hợp lệ.')
            actual = digest(target) if target.exists() else None
            if actual not in (item['oldSha'],item['newSha']):
                raise ValueError('Giao dịch quản lý gián đoạn và file đã sửa ngoài. Giữ bản sao để kiểm tra.')
            if item['oldSha'] is not None:
                if digest(backup) != item['oldSha']: raise ValueError('Bản sao giao dịch bị hỏng.')
                if target.suffix.lower()=='.xlsm' and macro_signature(backup)[0]!=trusted:
                    raise ValueError('Macro của bản sao giao dịch không hợp lệ.')
        for item in journal['files']:
            target = Path(item['path'])
            if item['oldSha'] is None:
                if target.exists(): target.unlink()
            else:
                stage = target.with_name('.recover-'+secrets.token_hex(8)+target.suffix)
                shutil.copy2(item['original'],stage)
                os.replace(stage,target)
        journal['status']='rolled-back'
        journal_path.write_text(json.dumps(journal),encoding='utf-8')


class Management:
    def __init__(self, store, accounts):
        self.store, self.accounts = store, accounts
        self.base = accounts.path.parent.resolve()
        self.registry_path = self.base/'school-years.json'
        if not self.registry_path.exists():
            self.save_registry({'active':'initial','years':[{'id':'initial','year':store.catalog.public()['year'],
                'root':str(store.catalog.root),'state':str(store.state_dir.resolve()),'createdAt':store.stamp()}]})
        with accounts.db() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS staff_profiles(id TEXT PRIMARY KEY,user_id TEXT UNIQUE,
                full_name TEXT NOT NULL,phone TEXT,email TEXT,birth_date TEXT,address TEXT,
                status TEXT NOT NULL,service_from TEXT,service_to TEXT,note TEXT,updated_at TEXT,birth_year INTEGER);
              CREATE TABLE IF NOT EXISTS assignment_history(id INTEGER PRIMARY KEY,user_id TEXT,class_id TEXT,
                class_name TEXT,slot TEXT,year TEXT,event TEXT,actor_id TEXT,stamp TEXT);
              CREATE TABLE IF NOT EXISTS year_assignments(year_id TEXT,user_id TEXT,class_id TEXT,slot TEXT,
                PRIMARY KEY(year_id,class_id,slot));
              CREATE TABLE IF NOT EXISTS notification_reads(user_id TEXT,item_id TEXT,stamp TEXT,
                PRIMARY KEY(user_id,item_id));
              CREATE TABLE IF NOT EXISTS notification_preferences(user_id TEXT PRIMARY KEY,value TEXT);
            ''')
            if 'birth_year' not in {row['name'] for row in db.execute('PRAGMA table_info(staff_profiles)')}:
                db.execute('ALTER TABLE staff_profiles ADD COLUMN birth_year INTEGER')
            if 'feast_day' not in {row['name'] for row in db.execute('PRAGMA table_info(staff_profiles)')}:
                db.execute("ALTER TABLE staff_profiles ADD COLUMN feast_day TEXT DEFAULT ''")
            for user in db.execute("SELECT * FROM users WHERE role='GLV'").fetchall():
                db.execute('INSERT OR IGNORE INTO staff_profiles(id,user_id,full_name,phone,email,birth_date,address,status,service_from,service_to,note,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                    (user['id'],user['id'],user['display_name'],'','','','','active','','','',store.stamp()))
            if not db.execute('SELECT 1 FROM assignment_history LIMIT 1').fetchone():
                for assignment in db.execute('SELECT * FROM assignments').fetchall():
                    info = store.catalog.classes.get(assignment['class_id'])
                    db.execute('INSERT INTO assignment_history(user_id,class_id,class_name,slot,year,event,stamp) VALUES (?,?,?,?,?,?,?)',
                        (assignment['user_id'],assignment['class_id'],info['name'] if info else assignment['class_id'],
                         assignment['slot'],store.catalog.public()['year'],'initial',store.stamp()))
        self.init_year()
        store.management = self

    def init_year(self):
        with self.store.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS class_settings(class_id TEXT PRIMARY KEY,archived INTEGER NOT NULL DEFAULT 0,updated_at TEXT)')
        # Reservations survive year switches and interrupted activation, including graduates.
        reserved=set()
        for year in self.registry()['years']:
            database=Path(year['state'])/'attendance.sqlite3'
            if database.exists():
                with closing(sqlite3.connect(database)) as source:
                    reserved.update(r[0] for r in source.execute('SELECT code FROM issued_codes'))
        manifest=Path(self.store.catalog.root)/'manifest.json'
        if manifest.exists(): reserved.update(json.loads(manifest.read_text(encoding='utf-8')).get('issuedCodes',[]))
        with self.store.db() as db:
            db.executemany('INSERT OR IGNORE INTO issued_codes VALUES (?,?)',[(code,self.store.stamp()) for code in reserved])

    def registry(self):
        return json.loads(self.registry_path.read_text(encoding='utf-8'))

    def save_registry(self, value):
        stage = self.registry_path.with_suffix('.tmp')
        stage.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
        os.replace(stage,self.registry_path)

    def class_statuses(self):
        with self.store.db() as db:
            return {r['class_id']:bool(r['archived']) for r in db.execute('SELECT * FROM class_settings')}

    def accounts_revision(self):
        # Browser session timestamps change on every request and are not configuration.
        with self.accounts.db() as db:
            return fingerprint({table:[tuple(r) for r in db.execute('SELECT * FROM '+table+' ORDER BY 1,2')]
                for table in ('users','assignments','staff_profiles','year_assignments')})

    def staff(self):
        with self.accounts.db() as db:
            profiles = [dict(r) for r in db.execute('SELECT * FROM staff_profiles ORDER BY full_name')]
            history = [dict(r) for r in db.execute('SELECT * FROM assignment_history ORDER BY id DESC')]
        return {'profiles':profiles,'history':history,'accounts':self.accounts.users()}

    def staff_celebrations(self):
        profiles = []
        current = date.today().isoformat()
        for person in self.staff()['profiles']:
            if person.get('status', 'active') != 'active':
                continue
            if person.get('service_from') and person['service_from'] > current or person.get('service_to') and person['service_to'] < current:
                continue
            birthday = ''
            try:
                birthday = date.fromisoformat(person.get('birth_date') or '').strftime('%m-%d')
            except (ValueError, TypeError):
                pass
            profiles.append({'id':person['id'], 'name':person['full_name'], 'birthDay':birthday, 'feastDay':person.get('feast_day') or ''})
        return {'profiles':profiles}

    def save_staff(self, user, values):
        name = str(values.get('full_name') or '').strip()
        status = values.get('status','active')
        if not 2<=len(name)<=100 or status not in ('active','paused','retired'):
            raise ValueError('Nhập họ tên và chọn trạng thái phục vụ.')
        fields = ('phone','email','birth_date','address','service_from','service_to','note')
        data = {key:str(values.get(key) or '').strip() for key in fields}
        if any(len(v)>500 for v in data.values()): raise ValueError('Thông tin hồ sơ quá dài.')
        for key in ('birth_date','service_from','service_to'):
            if data[key]: date.fromisoformat(data[key])
        raw_year='' if values.get('birth_year') is None else str(values['birth_year']).strip()
        if raw_year and (not re.fullmatch(r'\d{4}',raw_year) or not 1900<=int(raw_year)<=date.today().year):
            raise ValueError('Năm sinh phải gồm 4 chữ số, từ 1900 đến năm hiện tại.')
        if data['birth_date'] and date.fromisoformat(data['birth_date'])>date.today():
            raise ValueError('Ngày sinh không được ở tương lai.')
        birth_year=int(raw_year) if raw_year else None
        if data['birth_date']:
            year=date.fromisoformat(data['birth_date']).year
            if birth_year and birth_year!=year:raise ValueError('Ngày sinh không khớp năm sinh.')
            birth_year=year
        if data['service_to'] and data['service_from'] and data['service_to']<data['service_from']:
            raise ValueError('Ngày kết thúc phải sau ngày bắt đầu phục vụ.')
        if data['email'] and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',data['email']):
            raise ValueError('Email không hợp lệ.')
        identifier = str(values.get('id') or secrets.token_hex(16))
        linked = values.get('user_id') or None
        with self.accounts.db() as db:
            before = db.execute('SELECT * FROM staff_profiles WHERE id=?',(identifier,)).fetchone()
            feast = values.get('feast_day', before['feast_day'] if before else '')
            if not isinstance(feast, str):
                raise ValueError('Nhập ngày bổn mạng theo dạng dd/mm.')
            feast = feast.strip()
            if feast:
                if re.fullmatch(r'\d{2}/\d{2}', feast):
                    feast = feast[3:] + '-' + feast[:2]
                if not re.fullmatch(r'\d{2}-\d{2}', feast):
                    raise ValueError('Nhập ngày bổn mạng theo dạng dd/mm.')
                try:
                    date.fromisoformat('2000-' + feast)
                except ValueError:
                    raise ValueError('Ngày bổn mạng không tồn tại.')
            if 'birth_year' not in values and not data['birth_date'] and before:
                birth_year=before['birth_year']
            if linked and not db.execute('SELECT 1 FROM users WHERE id=?',(linked,)).fetchone():
                raise ValueError('Tài khoản liên kết không tồn tại.')
            if linked and db.execute('SELECT 1 FROM staff_profiles WHERE user_id=? AND id<>?',(linked,identifier)).fetchone():
                raise ValueError('Tài khoản này đã liên kết hồ sơ GLV khác.')
            db.execute('INSERT OR REPLACE INTO staff_profiles(id,user_id,full_name,phone,email,birth_date,address,status,service_from,service_to,note,updated_at,birth_year) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (identifier,linked,name,data['phone'],data['email'],data['birth_date'],data['address'],status,
                 data['service_from'],data['service_to'],data['note'],self.store.stamp(),birth_year))
            db.execute('UPDATE staff_profiles SET feast_day=? WHERE id=?',(feast,identifier))
            after = dict(db.execute('SELECT * FROM staff_profiles WHERE id=?',(identifier,)).fetchone())
            self.accounts.audit(db,user['id'],'staff-saved',{'before':dict(before) if before else None,'after':after})
        return {'saved':True,'staff':self.staff()}

    def audit(self, query, export=False):
        clauses, params = [], []
        for key in ('from','to'):
            if query.get(key):
                day = date.fromisoformat(query[key]).isoformat()
                clauses.append('substr(a.stamp,1,10) '+('>=' if key=='from' else '<=')+' ?'); params.append(day)
        if query.get('actor'): clauses.append('a.user_id=?'); params.append(query['actor'])
        if query.get('action'): clauses.append('a.action LIKE ?'); params.append('%'+query['action'][:100]+'%')
        if query.get('search'):
            clauses.append('(a.details LIKE ? OR u.display_name LIKE ? OR a.action LIKE ?)')
            params.extend(['%'+query['search'][:100]+'%']*3)
        where = ' WHERE '+' AND '.join(clauses) if clauses else ''
        try: offset = max(0,int(query.get('offset',0)))
        except ValueError: raise ValueError('Trang nhật ký không hợp lệ.')
        with self.accounts.db() as db:
            total = db.execute('SELECT COUNT(*) FROM security_audit a LEFT JOIN users u ON u.id=a.user_id'+where,params).fetchone()[0]
            rows = db.execute('SELECT a.*,u.display_name,u.username FROM security_audit a LEFT JOIN users u ON u.id=a.user_id'+where+
                ' ORDER BY a.id DESC LIMIT ? OFFSET ?',params+[10000 if export else 100,0 if export else offset]).fetchall()
            result = [{**dict(r),'details':json.loads(r['details'])} for r in rows]
        if export:
            if total>10000: raise ValueError('Lọc nhật ký xuống dưới 10.000 dòng trước khi xuất.')
            return csv_bytes([['Thời gian UTC','Người thực hiện','Tên đăng nhập','Thao tác','Chi tiết']]+
                [[r['stamp'],r['display_name'] or 'Hệ thống',r['username'] or '',r['action'],json.dumps(r['details'],ensure_ascii=False)] for r in result]),'Nhat-ky-quan-ly.csv','text/csv; charset=utf-8'
        return {'items':result,'total':total,'offset':offset}

    def capture(self, path, values):
        """Capture useful domain data, never credentials, CSRF tokens or workbook bytes."""
        store = self.store
        code = str(values.get('code') or '').strip().upper()
        cid = values.get('classId')
        if path in ('/api/student-profile','/api/student-status'):
            person = store.catalog.students.get(code)
            return {'student':person,'statuses':[s for s in store.development_public()['studentStatuses'] if s['code']==code]}
        if path in ('/api/grades','/api/grade-reconcile') and cid in store.catalog.classes:
            return store.read_grades(cid,int(values.get('semester',1)))
        if path == '/api/teachers' and cid in store.catalog.classes:
            with self.accounts.db() as db: assignments=[dict(r) for r in db.execute('SELECT * FROM assignments WHERE class_id=?',(cid,))]
            return {'teachers':store.catalog.classes[cid]['teachers'],'assignments':assignments}
        if path in ('/api/mark','/api/scan','/api/close'):
            session = store.session(values.get('sessionId'))
            prefix = session['date']+'|'+session['activity']+'|'
            return {'session':session,'marks':{k:v for k,v in store.catalog.marks.items() if k.startswith(prefix)}}
        if path in ('/api/review','/api/reschedule-makeup','/api/requests'):
            return [r for r in store.requests() if r['id']==values.get('id') or (code and r['code']==code)]
        if path == '/api/care-note':
            return [r for r in store.development_public()['careNotes'] if r['id']==values.get('id') or (code and r['code']==code)]
        if path in ('/api/backup-settings',): return store.settings()
        if path in ('/api/restore','/api/excel-save','/api/bulk-save','/api/transfer'):
            return {'workbooks':{k:digest(c['path']) for k,c in store.catalog.classes.items()},'student':store.catalog.students.get(code)}
        return None

    def backup_extras(self, stage, manifest):
        with closing(sqlite3.connect(self.accounts.path)) as source, closing(sqlite3.connect(stage/'accounts.sqlite3')) as dest:
            source.backup(dest)
            # A backup must never revive browser sessions or retain temporary login throttles.
            dest.execute('DELETE FROM auth_sessions');dest.execute('DELETE FROM login_limits');dest.commit()
        manifest['accountsSha256']=digest(stage/'accounts.sqlite3')
        manifest['includesAccounts']=True
        registry = self.registry()
        (stage/'school-years.json').write_text(json.dumps(registry,ensure_ascii=False),encoding='utf-8')
        manifest['registrySha256']=digest(stage/'school-years.json')
        manifest['archivedYears']=[]
        for year in registry['years']:
            if year['id']==registry['active']: continue
            target = stage/'years'/year['id']; target.mkdir(parents=True)
            catalog = Catalog(year['root'],year['state'],self.store.catalog.trusted_signature)
            files=[]
            for info in catalog.classes.values():
                relative=info['path'].relative_to(catalog.root).as_posix()
                before = digest(info['path']); destination=target/relative
                destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(info['path'],destination)
                if digest(destination)!=before or digest(info['path'])!=before: raise ValueError('Năm lưu trữ thay đổi trong lúc sao lưu.')
                files.append({'file':relative,'sha256':before})
            database = Path(year['state'])/'attendance.sqlite3'
            if database.exists():
                with closing(sqlite3.connect(database)) as source, closing(sqlite3.connect(target/'attendance.sqlite3')) as dest: source.backup(dest)
            manifest['archivedYears'].append({'id':year['id'],'year':year['year'],'files':files,
                'databaseSha256':digest(target/'attendance.sqlite3') if (target/'attendance.sqlite3').exists() else None})
        manifest['preparedYears']=[]
        for year in self.years()['years']:
            if not year.get('prepared'): continue
            info=self.locate_year(year['id']);source=Path(info['root']);target=stage/'prepared-years'/year['id']
            target.mkdir(parents=True)
            source_manifest=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
            for name,sha in source_manifest['files'].items():
                shutil.copy2(source/name,target/name)
                if digest(target/name)!=sha or digest(source/name)!=sha: raise ValueError('Bộ năm đã chuẩn bị thay đổi trong lúc sao lưu.')
            shutil.copy2(source/'manifest.json',target/'manifest.json')
            manifest['preparedYears'].append({'id':year['id'],'year':year['year'],'files':source_manifest['files']})

    def accounts_restore_preview(self, values):
        folder = self.store.snapshot_folder(values.get('id'))
        manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        source = folder/'accounts.sqlite3'
        if not manifest.get('accountsSha256') or not source.exists() or digest(source)!=manifest['accountsSha256']:
            raise ValueError('Bản sao này chưa có tài khoản hoặc mã kiểm tra không khớp.')
        with closing(sqlite3.connect(source)) as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('Cơ sở dữ liệu tài khoản bị hỏng.')
            users = db.execute('SELECT username,display_name,role,active FROM users ORDER BY username').fetchall()
            if not any(r[2]=='Admin' and r[3] for r in users): raise ValueError('Bản sao không có Admin hoạt động.')
            assignments=[r[0] for r in db.execute('SELECT DISTINCT class_id FROM assignments')]
        missing=[cid for cid in assignments if cid not in self.store.catalog.classes]
        if missing: raise ValueError('Bản quyền chứa lớp không còn trong năm hiện tại. Phục hồi bộ Excel phù hợp trước.')
        token=fingerprint({'id':manifest['id'],'source':digest(source),'current':self.accounts_revision(),
                           'classes':sorted(self.store.catalog.classes)})
        return {'id':manifest['id'],'token':token,'count':len(users),'users':[{'username':r[0],'name':r[1],'role':r[2],'active':bool(r[3])} for r in users],
                'warning':'Mật khẩu và phân quyền sẽ quay về bản sao. Tất cả phiên đăng nhập sẽ kết thúc.'}

    def workbooks_restore_preview(self, values):
        folder=self.store.snapshot_folder(values.get('id'))
        manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        if manifest['year']!=self.store.catalog.public()['year']:
            raise ValueError('Bản sao thuộc năm học khác. Chuyển về năm phù hợp trước khi phục hồi.')
        seen=set()
        for item in manifest['files']:
            source=(folder/'workbooks'/item['relative']).resolve()
            target=(self.store.catalog.root/item['relative']).resolve()
            if item['relative'] in seen or not source.is_relative_to((folder/'workbooks').resolve()) or not target.is_relative_to(self.store.catalog.root) or target.suffix!='.xlsm':
                raise ValueError('Đường dẫn bản sao không hợp lệ.')
            seen.add(item['relative'])
            if digest(source)!=item['sha256'] or macro_signature(source)[0]!=self.store.catalog.trusted_signature:
                raise ValueError('Bản sao Excel thiếu, bị sửa hoặc macro không hợp lệ.')
        source=folder/'attendance.sqlite3'
        if digest(source)!=manifest['databaseSha256']: raise ValueError('Cơ sở dữ liệu sao lưu không khớp.')
        with closing(sqlite3.connect(source)) as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Cơ sở dữ liệu sao lưu bị hỏng.')
        # Parse the entire backup now, before any target is replaced.
        Catalog(folder/'workbooks',folder/'verify',self.store.catalog.trusted_signature)
        current={c['path'].relative_to(self.store.catalog.root).as_posix():digest(c['path']) for c in self.store.catalog.classes.values()}
        token=fingerprint({'current':current,'database':digest(self.store.database),'manifest':manifest})
        return {'id':manifest['id'],'stamp':manifest['stamp'],'count':manifest['count'],'label':manifest['label'],'token':token,
                'currentHashes':current,
                'addedFiles':sorted(seen-set(current)),'removedFiles':sorted(set(current)-seen),
                'warning':'Phục hồi bộ lớp, chuyên cần, điểm và hồ sơ. Tài khoản và phân quyền giữ nguyên.'}

    def restore_workbooks(self, values):
        actor,reason=self.store.actor(values);plan=self.workbooks_restore_preview(values)
        if values.get('previewToken')!=plan['token'] or values.get('confirmation')!='KHÔI PHỤC':
            raise ValueError('Xem trước lại và nhập KHÔI PHỤC để xác nhận.')
        folder=self.store.snapshot_folder(values['id']);manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        self.store.snapshot({'_manager':True,'actor':actor,'label':'Trước khôi phục: '+reason})
        # Snapshot changes backup settings only. Recheck workbook hashes and obtain a fresh DB rollback.
        old_manifest=self.workbooks_restore_preview(values)
        if old_manifest['addedFiles']!=plan['addedFiles'] or old_manifest['removedFiles']!=plan['removedFiles']:
            raise ValueError('Danh sách lớp vừa thay đổi. Xem trước lại.')
        if old_manifest['currentHashes']!=plan['currentHashes']:
            raise ValueError('Excel đổi trong lúc sao lưu. Xem trước lại.')
        packages={}
        supplied={f['relative'] for f in manifest['files']}
        for info in self.store.catalog.classes.values():
            owners=[info['path'].with_name('~$'+info['path'].name),info['path'].with_name('~$'+info['path'].name[2:])]
            if any(p.exists() for p in owners): raise ValueError('Đóng file Excel trước khi khôi phục.')
            relative=info['path'].relative_to(self.store.catalog.root).as_posix()
            if relative not in supplied: packages[info['path']]=None
        for item in manifest['files']:
            target=self.store.catalog.root/item['relative'];target.parent.mkdir(parents=True,exist_ok=True)
            packages[target]=(folder/'workbooks'/item['relative']).read_bytes()
        with tempfile.TemporaryDirectory(dir=self.base,prefix='.restore-data-') as temporary:
            prepared=Path(temporary)/'attendance.sqlite3';shutil.copy2(folder/'attendance.sqlite3',prepared)
            with self.store.db() as current, closing(sqlite3.connect(prepared)) as db:
                db.execute('CREATE TABLE IF NOT EXISTS issued_codes(code TEXT PRIMARY KEY,stamp TEXT)')
                db.executemany('INSERT OR IGNORE INTO issued_codes VALUES (?,?)',[(r['code'],self.store.stamp()) for r in current.execute('SELECT code FROM issued_codes')])
                db.commit()
            packages[self.store.database]=prepared.read_bytes();self.transaction(packages)
        self.store.catalog.stamps={};self.store.catalog.refresh();self.store._grades=None
        self.store.init_development();self.store.init_parity();self.init_year()
        with self.store.db() as db: self.store.management_event(db,'snapshot',values['id'],'restored',actor,reason)
        return {'saved':True,'state':self.store.bootstrap(),'system':self.store.system_info()}

    def restore_accounts(self, user, values):
        plan=self.accounts_restore_preview(values)
        if values.get('previewToken')!=plan['token'] or values.get('confirmation')!='KHÔI PHỤC TÀI KHOẢN':
            raise ValueError('Xem trước lại và nhập KHÔI PHỤC TÀI KHOẢN để xác nhận.')
        folder=self.store.snapshot_folder(values['id'])
        # Preserve the audit trail even when passwords/permissions return to an older version.
        with tempfile.TemporaryDirectory(dir=self.base,prefix='.accounts-restore-') as temporary:
            prepared=Path(temporary)/'accounts.sqlite3';shutil.copy2(folder/'accounts.sqlite3',prepared)
            with closing(sqlite3.connect(self.accounts.path)) as current, closing(sqlite3.connect(prepared)) as db:
                for row in current.execute('SELECT stamp,user_id,action,details FROM security_audit'):
                    if not db.execute('SELECT 1 FROM security_audit WHERE stamp=? AND user_id IS ? AND action=? AND details=?',row).fetchone():
                        db.execute('INSERT INTO security_audit(stamp,user_id,action,details) VALUES (?,?,?,?)',row)
                db.execute('DELETE FROM auth_sessions');db.execute('DELETE FROM login_limits')
                self.accounts.audit(db,user['id'],'accounts-restored',{'snapshot':values['id'],'actorName':user['displayName'],'reason':self.reason(values)})
                db.commit()
            self.transaction({self.accounts.path:prepared.read_bytes()})
        return {'saved':True,'requireReauth':True}

    def reason(self, values):
        value=str(values.get('reason') or '').strip()
        if not 3<=len(value)<=500: raise ValueError('Nhập lý do từ 3 đến 500 ký tự.')
        return value

    def transaction(self, packages):
        folder=self.base/'management-transactions'/secrets.token_hex(12);folder.mkdir(parents=True)
        files=[]
        for index,(target,content) in enumerate(packages.items()):
            target=Path(target).resolve();before=digest(target) if target.exists() else None
            original=folder/f'{index}.original';prepared=folder/f'{index}.prepared'
            if target.exists(): shutil.copy2(target,original)
            if content is not None: prepared.write_bytes(content)
            if content is not None and target.suffix=='.xlsm' and macro_signature(prepared)[0]!=self.store.catalog.trusted_signature:
                raise ValueError('Macro bản chuẩn bị không hợp lệ.')
            if (digest(target) if target.exists() else None)!=before: raise ValueError('Dữ liệu thay đổi trong khi chuẩn bị.')
            files.append({'path':str(target),'original':str(original),'prepared':str(prepared),'oldSha':before,'newSha':digest(prepared) if content is not None else None})
        journal={'status':'prepared','files':files};path=folder/'journal.json'
        path.write_text(json.dumps(journal),encoding='utf-8')
        try:
            for item in files:
                target=Path(item['path'])
                if (digest(target) if target.exists() else None)!=item['oldSha']: raise ValueError('File đã sửa ngoài. Chưa ghi đè.')
                if item['newSha'] is None:
                    target.unlink()
                else:
                    staged=target.with_name('.management-'+secrets.token_hex(8)+target.suffix)
                    shutil.copy2(item['prepared'],staged);os.replace(staged,target)
            journal['status']='committed';path.write_text(json.dumps(journal),encoding='utf-8')
        except Exception:
            recover_management(self.base,self.store.catalog.trusted_signature)
            raise

    def class_preview(self, values):
        store=self.store;store.catalog.refresh();self.reason(values)
        op=values.get('operation')
        if op not in ('create','rename','archive','reopen'): raise ValueError('Thao tác lớp không hợp lệ.')
        cid=values.get('classId');info=store.catalog.classes.get(cid)
        if not info: raise ValueError('Chọn lớp hoặc bản mẫu đang tồn tại.')
        name=' '.join(str(values.get('name') or info['name']).split())
        if op in ('create','rename'):
            if not 3<=len(name)<=80 or ' ' not in name or re.search(r'[<>:"/\\|?*\x00-\x1f]',name):
                raise ValueError('Tên lớp cần gồm khối và số/tên lớp; không dùng ký tự đường dẫn.')
            if any(normalize_vi(c['name'])==normalize_vi(name) and (op=='create' or c['id']!=cid) for c in store.catalog.classes.values()):
                raise ValueError('Tên lớp đã tồn tại.')
        if op=='create' and (store.catalog.root/(name+'.xlsm')).exists(): raise ValueError('File lớp mới đã tồn tại.')
        return {'operation':op,'classId':cid,'name':name,'count':info['count'],'reason':values['reason'],
                'token':fingerprint({'values':{k:values.get(k) for k in ('operation','classId','name','reason')},
                    'files':{k:digest(c['path']) for k,c in store.catalog.classes.items()},'statuses':self.class_statuses()})}

    def save_class(self, user, values):
        plan=self.class_preview(values)
        if values.get('previewToken')!=plan['token']: raise ValueError('Dữ liệu đã thay đổi. Xem trước lại.')
        store=self.store;cid=plan['classId'];before=dict(store.catalog.classes[cid]);op=plan['operation']
        backup=store.snapshot({'_manager':True,'actor':user['displayName'],'label':'Trước '+op+' lớp'})['snapshot']['id']
        if self.class_preview(values)['token']!=plan['token']: raise ValueError('File đổi trong lúc sao lưu. Xem trước lại.')
        if op in ('create','rename'):
            from management_native import class_package
            new_id,package=class_package(store.parity_engine(),cid,plan['name'],op=='create')
            if op=='create':
                self.transaction({store.catalog.root/(plan['name']+'.xlsm'):package});cid=new_id
            else:
                def change(db):
                    db.execute('UPDATE sessions SET scope=? WHERE scope=?',(plan['name'],before['name']))
                    store.management_event(db,'class',cid,'renamed',user['displayName'],self.reason(values))
                store.parity_transaction({'revisions':{cid:digest(before['path'])}},{cid:package},change)
        else:
            with store.db() as db:
                db.execute('INSERT OR REPLACE INTO class_settings VALUES (?,?,?)',(cid,int(op=='archive'),store.stamp()))
        store.catalog.stamps={};store.catalog.refresh()
        with self.accounts.db() as db:
            self.accounts.audit(db,user['id'],'class-'+op,{'classId':cid,'before':{'name':before['name'],'count':before['count']},
                'after':{'name':store.catalog.classes[cid]['name'],'archived':self.class_statuses().get(cid,False)},'reason':self.reason(values),'backup':backup})
        return {'saved':True,'state':store.bootstrap()}

    def import_rows(self, values):
        columns=['classId','code','saintName','fullName','gender','birthDate','baptismDate','parents','address','subParish','phone','enrolledFrom']
        if isinstance(values.get('rows'),list):
            rows=values['rows']
        elif values.get('fileBase64'):
            try: data=base64.b64decode(values['fileBase64'],validate=True)
            except (ValueError,TypeError): raise ValueError('File tải lên không hợp lệ.')
            if len(data)>2_000_000: raise ValueError('File nhập tối đa 2 MB.')
            filename=str(values.get('filename') or '').lower()
            if filename.endswith('.xlsx'):
                import zipfile
                import openpyxl
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    if sum(i.file_size for i in archive.infolist())>20_000_000: raise ValueError('File Excel giải nén quá lớn.')
                book=openpyxl.load_workbook(io.BytesIO(data),read_only=True,data_only=False)
                try:
                    iterator=book.active.iter_rows(values_only=True)
                    header=[str(c or '').strip() for c in next(iterator)]
                    rows=[]
                    for row in iterator:
                        if len(rows)>800: raise ValueError('Chỉ nhập tối đa 800 dòng một lần.')
                        if any(v not in (None,'') for v in row):
                            rows.append({key:(value.date().isoformat() if isinstance(value,datetime) else str(value or '')) for key,value in zip(header,row)})
                finally: book.close()
            elif filename.endswith(('.csv','.tsv','.txt')):
                text=data.decode('utf-8-sig');rows=self.parse_text(text)
            else: raise ValueError('Chỉ nhận .xlsx, CSV hoặc TSV UTF-8.')
        else: rows=self.parse_text(str(values.get('text') or ''))
        if not 1<=len(rows)<=800: raise ValueError('Nhập từ 1 đến 800 dòng hồ sơ.')
        if any(not isinstance(r,dict) or set(r)-set(columns) for r in rows): raise ValueError('Có tên cột không được hỗ trợ. Dùng file mẫu.')
        return rows

    def parse_text(self, text):
        if len(text)>2_000_000: raise ValueError('Danh sách quá lớn.')
        delimiter='\t' if '\t' in text.split('\n',1)[0] else ','
        reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')),delimiter=delimiter)
        if not reader.fieldnames or 'code' not in reader.fieldnames or 'fullName' not in reader.fieldnames:
            raise ValueError('Dòng đầu cần tên cột theo file mẫu: code, fullName…')
        rows=[]
        for row in reader:
            if len(rows)>=800: raise ValueError('Chỉ nhập tối đa 800 dòng một lần.')
            if any(v for v in row.values()): rows.append(row)
        return rows

    def import_preview(self, values):
        store=self.store;self.reason(values);store.catalog.refresh()
        rows=self.import_rows(values); normalized=[];issues=[];warnings=[];seen=set();counts=Counter();profiles=set()
        for number,row in enumerate(rows,2):
            cid=row.get('classId') or values.get('classId')
            if cid not in store.catalog.classes:
                cid=next((c['id'] for c in store.catalog.classes.values() if c['name']==cid),cid)
            entry={**row,'classId':cid,'actor':values['actor'],'reason':values['reason'],'_manager':True,'operation':'student-add'}
            try:
                if str(row.get('code') or '').upper() in seen: raise ValueError('Mã trùng trong file nhập.')
                if self.class_statuses().get(cid): raise ValueError('Lớp đã lưu trữ; mở lại lớp trước khi thêm.')
                plan=store.parity_plan(entry);payload=plan['payload'];seen.add(payload['code']);counts[cid]+=1
                for key in ('birthDate','baptismDate'):
                    parsed=profile_date(payload[key]);payload[key]=parsed.date().isoformat() if parsed else ''
                key=(normalize_vi(payload['fullName']),payload['birthDate'])
                if key in profiles or any(normalize_vi(s['fullName'])==key[0] and s['birthDate']==key[1] for s in store.catalog.students.values()):
                    warnings.append(f'Dòng {number}: trùng họ tên/ngày sinh, cần kiểm tra {payload["fullName"]}.')
                profiles.add(key);normalized.append({'classId':cid,**payload})
            except (ValueError,KeyError,TypeError) as error: issues.append(f'Dòng {number}: {error}')
        for cid,count in counts.items():
            if store.catalog.classes[cid]['count']+count>40: issues.append(store.catalog.classes[cid]['name']+': vượt sức chứa 40 em.')
        revisions={cid:digest(store.catalog.classes[cid]['path']) for cid in counts}
        with store.db() as db: issued=[r['code'] for r in db.execute('SELECT code FROM issued_codes ORDER BY code')]
        return {'rows':normalized,'issues':issues,'warnings':warnings,'counts':dict(counts),'revisions':revisions,
                'token':fingerprint({'rows':normalized,'revisions':revisions,'issued':issued,'reason':values['reason'],'issues':issues,'warnings':warnings})}

    def import_commit(self, user, values):
        plan=self.import_preview(values)
        if plan['issues']: raise ValueError('Sửa tất cả dòng lỗi trước khi nhập.')
        if plan['warnings'] and values.get('acceptWarnings') is not True: raise ValueError('Xác nhận đã kiểm tra các hồ sơ có thể trùng.')
        if values.get('previewToken')!=plan['token']: raise ValueError('Dữ liệu đã thay đổi. Xem trước lại.')
        store=self.store
        backup=store.snapshot({'_manager':True,'actor':user['displayName'],'label':'Trước nhập hồ sơ hàng loạt'})['snapshot']['id']
        packages={}
        from native import ExcelEngine
        with tempfile.TemporaryDirectory(dir=store.catalog.root,prefix='.roster-import-') as temporary:
            for cid in plan['counts']: shutil.copy2(store.catalog.classes[cid]['path'],Path(temporary)/store.catalog.classes[cid]['filename'])
            catalog=Catalog(temporary,Path(temporary)/'state',store.catalog.trusted_signature)
            engine=object.__new__(ExcelEngine);engine.catalog=catalog;engine.app=store.parity_engine().excel()
            for row in plan['rows']:
                package,_=engine.parity_package(row['classId'],'student-add',row)
                catalog.classes[row['classId']]['path'].write_bytes(package);catalog.stamps={};catalog.refresh()
            for cid in plan['counts']: packages[cid]=catalog.classes[cid]['path'].read_bytes()
        def change(db):
            db.executemany('INSERT INTO issued_codes VALUES (?,?)',[(r['code'],store.stamp()) for r in plan['rows']])
            store.management_event(db,'roster-import',backup,'imported',user['displayName'],self.reason(values))
        store.parity_transaction(plan,packages,change)
        with self.accounts.db() as db:
            self.accounts.audit(db,user['id'],'roster-imported',{'before':None,'after':plan['rows'],'backup':backup,'reason':self.reason(values)})
        return {'saved':True,'count':len(plan['rows']),'state':store.bootstrap()}

    def years(self):
        registry=self.registry();results=[{k:y[k] for k in ('id','year','createdAt')} for y in registry['years']]
        existing={y['id'] for y in results}
        # Prepared years remain reviewable before activation.
        for year in registry['years']:
            for path in (Path(year['state'])/'year_exports').glob('*/manifest.json'):
                identifier=path.parent.name
                if identifier in existing: continue
                manifest=json.loads(path.read_text(encoding='utf-8'))
                results.append({'id':identifier,'year':manifest['year'],'createdAt':identifier[:15],'prepared':True})
                existing.add(identifier)
        return {'active':registry['active'],'years':results}

    def locate_year(self, identifier):
        registry=self.registry()
        year=next((y for y in registry['years'] if y['id']==identifier),None)
        if year: return year
        if not isinstance(identifier,str) or not re.fullmatch(r'[0-9a-f-]+',identifier): raise ValueError('Mã năm học không hợp lệ.')
        for item in registry['years']:
            folder=Path(item['state'])/'year_exports'/identifier
            if (folder/'manifest.json').exists():
                manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
                if any(Path(name).name!=name or not name.endswith('.xlsm') or digest(folder/name)!=sha for name,sha in manifest['files'].items()):
                    raise ValueError('Bộ năm học đã thay đổi trước khi kích hoạt.')
                return {'id':identifier,'year':manifest['year'],'root':str(folder),'state':str(self.base/'years'/identifier),
                        'createdAt':identifier[:15],'prepared':True}
        raise ValueError('Không tìm thấy năm học.')

    def year_history(self, identifier, code=''):
        year=self.locate_year(identifier)
        catalog=Catalog(year['root'],year['state'],self.store.catalog.trusted_signature)
        result=catalog.public()
        database=Path(year['state'])/'attendance.sqlite3'
        if database.exists():
            with closing(sqlite3.connect(database)) as db:
                db.row_factory=sqlite3.Row
                result['requests']=[dict(r) for r in db.execute('SELECT * FROM requests'+(' WHERE code=?' if code else '')+' ORDER BY created_at DESC',(code,) if code else ())]
                result['careNotes']=[dict(r) for r in db.execute('SELECT * FROM care_notes'+(' WHERE code=?' if code else '')+' ORDER BY updated_at DESC',(code,) if code else ())]
                result['studentStatuses']=[dict(r) for r in db.execute('SELECT * FROM student_status'+(' WHERE code=?' if code else '')+' ORDER BY effective_day,stamp',(code,) if code else ())]
        if code:
            if code not in catalog.students: return {'year':year['year'],'students':[],'marks':{},'grades':[]}
            result['students']=[catalog.students[code]]
            result['marks']={k:v for k,v in result['marks'].items() if k.endswith('|'+code)}
            cid=catalog.students[code]['classId']
            result['grades']=[{**g,'semester':sem} for sem in (1,2,3) for g in catalog.read_grades(cid,sem)['students'] if g['code']==code]
        return result

    def year_activate_preview(self, values):
        self.reason(values);year=self.locate_year(values.get('id'))
        if year['id']==self.registry()['active']: raise ValueError('Năm này đang là năm làm việc.')
        catalog=Catalog(year['root'],year['state'],self.store.catalog.trusted_signature)
        return {'id':year['id'],'year':year['year'],'count':len(catalog.students),'classes':len(catalog.classes),
                'token':fingerprint({'year':year,'files':{cid:digest(c['path']) for cid,c in catalog.classes.items()},
                    'registry':self.registry(),'accounts':self.accounts_revision()}),
                'warning':'Toàn bộ phiên đăng nhập sẽ kết thúc. Mỗi năm giữ riêng chuyên cần, điểm, đơn và hồ sơ.'}

    def activate_year(self, user, values):
        plan=self.year_activate_preview(values)
        if values.get('previewToken')!=plan['token'] or values.get('confirmation')!=plan['year']:
            raise ValueError('Xem trước lại và nhập đúng năm học đích để xác nhận.')
        registry=self.registry();year=self.locate_year(plan['id']);store=self.store
        store.snapshot({'_manager':True,'actor':user['displayName'],'label':'Trước chuyển năm làm việc'})
        if self.year_activate_preview(values)['token']!=plan['token']: raise ValueError('Dữ liệu đổi khi sao lưu. Xem trước lại.')
        catalog=Catalog(year['root'],year['state'],store.catalog.trusted_signature)
        target_state=Path(year['state']);target_state.mkdir(parents=True,exist_ok=True)
        reserved=set()
        for item in registry['years']:
            database=Path(item['state'])/'attendance.sqlite3'
            if database.exists():
                with closing(sqlite3.connect(database)) as db:
                    reserved.update(r[0] for r in db.execute('SELECT code FROM issued_codes'))
        old_id=registry['active'];ids=set(catalog.classes)
        with tempfile.TemporaryDirectory(dir=self.base,prefix='.year-switch-') as temporary:
            prepared=Path(temporary)/'accounts.sqlite3'
            with closing(sqlite3.connect(self.accounts.path)) as source, closing(sqlite3.connect(prepared)) as db:
                source.backup(db)
                db.execute('DELETE FROM year_assignments WHERE year_id=?',(old_id,))
                db.execute('INSERT INTO year_assignments SELECT ?,user_id,class_id,slot FROM assignments',(old_id,))
                saved=list(db.execute('SELECT user_id,class_id,slot FROM year_assignments WHERE year_id=?',(year['id'],)))
                if not saved and year.get('prepared'):
                    saved=[r for r in db.execute('SELECT user_id,class_id,slot FROM assignments') if r[1] in ids]
                db.execute('DELETE FROM assignments')
                db.executemany('INSERT INTO assignments VALUES (?,?,?)',[r for r in saved if r[1] in ids])
                if year.get('prepared'):
                    for who,cid,slot in saved:
                        if cid in ids:
                            db.execute('INSERT INTO assignment_history(user_id,class_id,class_name,slot,year,event,actor_id,stamp) VALUES (?,?,?,?,?,?,?,?)',
                                (who,cid,catalog.classes[cid]['name'],slot,year['year'],'inherited',user['id'],store.stamp()))
                db.execute('DELETE FROM auth_sessions')
                self.accounts.audit(db,user['id'],'year-activated',{'before':old_id,'after':year['id'],'year':year['year'],'reason':self.reason(values)})
                db.commit()
            if not any(y['id']==year['id'] for y in registry['years']):
                registry['years'].append({k:v for k,v in year.items() if k!='prepared'})
            registry['active']=year['id']
            # Shutdown stays in the serialized Excel worker; Store identity remains unchanged.
            store.shutdown()
            self.transaction({self.accounts.path:prepared.read_bytes(),self.registry_path:json.dumps(registry,ensure_ascii=False,indent=2).encode()})
        mode=store.grade_mode
        type(store).__init__(store,year['root'],target_state,grade_mode=mode)
        self.accounts.catalog=store.catalog;store.management=self;self.init_year()
        manifest=Path(year['root'])/'manifest.json'
        if manifest.exists():
            with store.db() as db:
                db.executemany('INSERT OR IGNORE INTO issued_codes VALUES (?,?)',[(c,store.stamp()) for c in json.loads(manifest.read_text(encoding='utf-8')).get('issuedCodes',[])])
        with store.db() as db:
            db.executemany('INSERT OR IGNORE INTO issued_codes VALUES (?,?)',[(c,store.stamp()) for c in reserved])
        return {'saved':True,'requireReauth':True,'year':year['year']}

    def notifications(self, user, filtered_state):
        today=datetime.now(self.store.local_tz).date().isoformat();year=self.registry()['active'];items=[]
        statuses=self.class_statuses()
        inactive_names={c['name'] for c in filtered_state['classes'] if statuses.get(c['id'])}
        def add(key,kind,title,detail,target):
            items.append({'id':year+':'+key,'kind':kind,'title':title,'detail':detail,'target':target})
        for request in filtered_state['requests']:
            if request['status']=='pending': add('request:'+request['id'],'requests','Đơn chờ duyệt',request['code']+' · '+request['day'],'requests')
        for session in filtered_state['sessions']:
            if session['date']<=today and not session['closed'] and session['scope'] not in inactive_names:
                add('session:'+session['id'],'sessions','Buổi chưa chốt',session['date']+' · '+session['scope'],'attendance')
        for note in filtered_state['careNotes']:
            if note['status']!='done' and note['due_day'] and note['due_day']<=today:
                add('care:'+note['id']+':'+note['updated_at'],'care','Đến hạn theo dõi',note['code']+' · '+note['content'][:160],'care')
        for info in filtered_state['classes']:
            if statuses.get(info['id']): continue
            # Only report missing semester exams once that semester's last month has ended.
            for sem,key in ((1,'hk1'),(2,'hk2')):
                months=info['semesterMonths'][key]
                if not months or today[:7]<=max(months): continue
                data=self.store.read_grades(info['id'],sem)
                missing=sum(1 for s in data['students'] if s.get('thiHk') in (None,''))
                if missing: add(f'grades:{info["id"]}:{sem}','grades','Thiếu điểm thi học kỳ',info['name']+f' · HK{sem}: {missing} em','grades')
        if user['role']=='Admin':
            system=self.store.system_info()
            if system['lastBackupError']: add('backup-error','system','Sao lưu cần kiểm tra',system['lastBackupError'],'management')
            for info in filtered_state['classes']:
                if not any(str(n or '').strip() for n in info['teachers'].values()) and not statuses.get(info['id']):
                    add('teacher:'+info['id'],'system','Lớp chưa phân công GLV',info['name'],'teachers')
        with self.accounts.db() as db:
            reads={r['item_id'] for r in db.execute('SELECT item_id FROM notification_reads WHERE user_id=?',(user['id'],))}
            pref=db.execute('SELECT value FROM notification_preferences WHERE user_id=?',(user['id'],)).fetchone()
        prefs=json.loads(pref['value']) if pref else {'requests':True,'sessions':True,'care':True,'grades':True,'system':True}
        items=[{**r,'read':r['id'] in reads} for r in items if prefs.get(r['kind'],True)]
        return {'items':items,'unread':sum(not r['read'] for r in items),'preferences':prefs}

    def notification_write(self, user, values, filtered_state, preferences=False):
        if preferences:
            data=values.get('preferences')
            if not isinstance(data,dict) or set(data)!=set(('requests','sessions','care','grades','system')) or any(type(v) is not bool for v in data.values()):
                raise ValueError('Tùy chọn nhắc việc không hợp lệ.')
            with self.accounts.db() as db: db.execute('INSERT OR REPLACE INTO notification_preferences VALUES (?,?)',(user['id'],json.dumps(data)))
        else:
            items=self.notifications(user,filtered_state)['items'];allowed={i['id'] for i in items}
            selected=values.get('ids')
            if not isinstance(selected,list) or len(selected)>2000 or any(i not in allowed for i in selected):
                raise AccessError('Thông báo ngoài phạm vi tài khoản.')
            with self.accounts.db() as db:
                db.executemany('INSERT OR REPLACE INTO notification_reads VALUES (?,?,?)',[(user['id'],i,self.store.stamp()) for i in selected])
        return self.notifications(user,filtered_state)
