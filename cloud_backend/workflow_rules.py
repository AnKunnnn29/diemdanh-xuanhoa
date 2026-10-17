"""Attendance rules ported from the local bridge; no disk or native Excel dependency.

SQL in these rules operates only on a disposable in-memory working set. The
cloud unit of work persists its state in PostgreSQL in the outer transaction.
"""
import secrets
import re
import unicodedata
from datetime import date, datetime, timedelta, time as clock_time

ACTIVITIES = {"mass": range(5, 19), "early": range(19, 24), "lesson": range(24, 29)}


def normalize_vi(text):
    if not text:
        return ''
    s = unicodedata.normalize('NFD', str(text).strip().lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.replace('đ', 'd').replace('Đ', 'd')


def day(value):
    try:
        return date.fromisoformat(value).isoformat()
    except (ValueError, TypeError):
        raise ValueError('Ngày không hợp lệ.')


def check_makeup(original, replacement, activity):
    original, replacement = date.fromisoformat(day(original)), date.fromisoformat(day(replacement))
    if activity != 'mass':
        raise ValueError('Chỉ Thánh lễ được đổi ngày; giáo lý và đi lễ sớm giữ lịch riêng.')
    if original.weekday() == 6 or replacement.weekday() == 6:
        raise ValueError('Chủ nhật không được đổi và không được dùng làm ngày bù.')
    if original == replacement:
        raise ValueError('Ngày lễ bù phải khác ngày gốc.')
    if original - timedelta(days=original.weekday()) != replacement - timedelta(days=replacement.weekday()):
        raise ValueError('Ngày gốc và ngày lễ bù phải trong cùng tuần, thứ Hai đến thứ Bảy.')


class ExceptionWorkflow:
    def init_exceptions(self):
        with self.db() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS requests(
                id TEXT PRIMARY KEY, group_id TEXT, code TEXT, kind TEXT, activity TEXT, day TEXT,
                target_day TEXT, reason TEXT, author TEXT, status TEXT DEFAULT 'pending',
                reviewer TEXT, reviewed_at TEXT, actual_day TEXT, created_at TEXT);
              CREATE UNIQUE INDEX IF NOT EXISTS one_active_request ON requests(code,day,activity)
                WHERE status IN ('pending','approved','completed');
              CREATE UNIQUE INDEX IF NOT EXISTS one_makeup_day ON requests(code,target_day)
                WHERE kind='makeup' AND status IN ('pending','approved','completed');
              CREATE TABLE IF NOT EXISTS request_events(
                id INTEGER PRIMARY KEY, request_id TEXT, action TEXT, actor TEXT, reason TEXT, stamp TEXT);
              CREATE TABLE IF NOT EXISTS scans(
                id TEXT PRIMARY KEY, code TEXT, activity TEXT, actual_day TEXT, obligation_day TEXT,
                request_id TEXT, status TEXT, stamp TEXT,
                UNIQUE(code,activity,actual_day), UNIQUE(code,activity,obligation_day));
            ''')
            columns = {r['name'] for r in db.execute('PRAGMA table_info(requests)')}
            if 'exception_day' not in columns:
                db.execute('ALTER TABLE requests ADD COLUMN exception_day TEXT')
            db.execute('''CREATE UNIQUE INDEX IF NOT EXISTS one_effective_makeup_day
                          ON requests(code, COALESCE(exception_day, target_day))
                          WHERE kind='makeup' AND status IN ('pending','approved','completed')''')

    def stamp(self):
        return datetime.now(self.local_tz).isoformat()

    def actor(self, values):
        if not isinstance(values.get('actor'),str) or not isinstance(values.get('reason'),str):
            raise ValueError('Nhập tên người xử lý và lý do hợp lệ.')
        actor = str(values.get('actor', '')).strip()
        reason = str(values.get('reason', '')).strip()
        if not 2 <= len(actor) <= 100 or not 3 <= len(reason) <= 500:
            raise ValueError('Nhập tên người xử lý và lý do (ít nhất 3 ký tự).')
        return actor, reason

    def validate_early_attendance(self, session, values):
        scan_day = date.fromisoformat(session['date'])
        if scan_day.weekday() != 6:
            raise ValueError('Đi lễ sớm chỉ diễn ra vào sáng Chủ Nhật.')
        now = datetime.now(self.local_tz)
        current_window = now.date() == scan_day and 360 <= now.hour * 60 + now.minute <= 380
        manual = values.get('manual', False)
        if not isinstance(manual, bool):
            raise ValueError('Hình thức nhập điểm danh không hợp lệ.')
        if not manual:
            if not current_window:
                raise ValueError('Quét lễ sớm phải đúng ngày Chủ Nhật đang diễn ra, từ 06:00 đến 06:20. Nhập bổ sung cần người quản lý xác nhận.')
            return {'attendedAt': now.isoformat()}
        if current_window and not values.get('attendedTime'):
            return {'attendedAt': now.isoformat()}
        if not values.get('_manager'):
            raise ValueError('Nhập bổ sung lễ sớm ngoài khung giờ cần Admin xác nhận.')
        self.actor(values)
        actual_time = values.get('attendedTime')
        if not isinstance(actual_time, str) or not re.fullmatch(r'\d{2}:\d{2}', actual_time):
            raise ValueError('Nhập giờ đi lễ thực tế theo dạng HH:MM, từ 06:00 đến 06:20.')
        try:
            actual_time = clock_time.fromisoformat(actual_time)
        except ValueError:
            raise ValueError('Giờ đi lễ thực tế không hợp lệ.')
        if not 360 <= actual_time.hour * 60 + actual_time.minute <= 380:
            raise ValueError('Giờ đi lễ thực tế phải từ 06:00 đến 06:20.')
        attended_at = datetime.combine(scan_day, actual_time, tzinfo=self.local_tz)
        if attended_at > now:
            raise ValueError('Không ghi nhận đã đi lễ sớm cho thời điểm chưa diễn ra.')
        return {'attendedAt': attended_at.isoformat()}

    def requests(self):
        with self.db() as db:
            return [self.public_request(r) for r in db.execute('SELECT * FROM requests ORDER BY created_at DESC,id')]

    def public_request(self, record):
        record = dict(record)
        record['effective_target_day'] = record['exception_day'] or record['target_day']
        return record

    def request(self, identifier):
        with self.db() as db:
            record = db.execute('SELECT * FROM requests WHERE id=?', (identifier,)).fetchone()
        if not record:
            raise ValueError('Không tìm thấy đơn.')
        return self.public_request(record)

    def check_makeup_available(self, code, target, exclude_id=None):
        with self.db() as db:
            conflict = db.execute('''SELECT 1 FROM requests WHERE code=? AND kind='makeup'
                AND COALESCE(exception_day,target_day)=? AND status IN ('pending','approved','completed')
                AND id<>?''', (code, target, exclude_id or '')).fetchone()
            scanned = db.execute('SELECT 1 FROM scans WHERE code=? AND activity=? AND actual_day=?',
                                 (code, 'mass', target)).fetchone()
        if conflict or scanned or self.status_at(code, target, 'mass') == 'X':
            raise ValueError('Ngày này đã có đơn hoặc lượt đi lễ được tính. Không dùng lại cho một buổi khác.')

    def reschedule_makeup(self, values):
        """Override one approved occurrence; preserve its original target and all other requests."""
        self.catalog.refresh()
        actor, reason = self.actor(values)
        record = self.request(values.get('id'))
        target = day(values.get('targetDate'))
        attended = values.get('attended', False)
        if not isinstance(attended, bool):
            raise ValueError('Xác nhận đã đi lễ không hợp lệ.')
        if record['kind'] != 'makeup' or record['activity'] != 'mass':
            raise ValueError('Chỉ đơn đổi ngày Thánh lễ mới được dời riêng một buổi.')
        check_makeup(record['day'], target, 'mass')
        student = self.catalog.students[record['code']]
        if student['enrolledFrom'] and target < student['enrolledFrom']:
            raise ValueError('Ngày ngoại lệ sớm hơn tháng nhập học.')
        if attended and target > datetime.now(self.local_tz).date().isoformat():
            raise ValueError('Không ghi nhận đã đi lễ cho ngày chưa diễn ra.')
        if record['status'] == 'completed' and record['exception_day'] == target and attended:
            # A client retry after a completed native write must not add another credit.
            session = self.create_session({'date': target, 'activity': 'mass', 'scope': student['className']})
            return self.workflow_scan({**values, 'sessionId': session['id'], 'code': record['code'], 'manual': True})
        if record['status'] not in ('approved', 'missed'):
            raise ValueError('Chỉ dời đơn đã duyệt chưa đi lễ, hoặc đơn vắng cần người quản lý xử lý.')
        original = self.obligation(student, record['day'], 'mass')
        manager = bool(values.get('_manager'))
        if (record['status'] == 'missed' or self.locked(original, student['classId'])
                or self.locked({'date': target, 'activity': 'mass'}, student['classId'])) and not manager:
            raise ValueError('Buổi đã chốt; Admin mới được xác nhận ngoại lệ.')
        existing = self.status_at(record['code'], record['day'], 'mass')
        if existing in ('X', 'P'):
            raise ValueError('Ngày gốc đã có X hoặc P. Kiểm tra trước khi dời riêng buổi này.')
        with self.db() as db:
            reserved = db.execute('SELECT 1 FROM scans WHERE code=? AND activity=? AND obligation_day=?',
                                  (record['code'], 'mass', record['day'])).fetchone()
            active = db.execute('''SELECT 1 FROM requests WHERE code=? AND day=? AND activity='mass'
                AND id<>? AND status IN ('pending','approved','completed')''',
                (record['code'], record['day'], record['id'])).fetchone()
        if reserved or active:
            raise ValueError('Buổi gốc có lượt quét hoặc đơn khác đang xử lý. Chưa thay đổi ngày ngoại lệ.')
        self.check_makeup_available(record['code'], target, record['id'])
        exception = None if target == record['target_day'] else target
        changed = record['exception_day'] != exception or record['status'] != 'approved'
        if changed:
            import sqlite3
            try:
                with self.db() as db:
                    db.execute('UPDATE requests SET exception_day=?,status=? WHERE id=?',
                               (exception, 'approved', record['id']))
                    self.request_event(db, record['id'], 'rescheduled', actor,
                        f'Chỉ buổi {record["day"]}: {record["effective_target_day"]} → {target}. '
                        f'Ngày đã xin vẫn là {record["target_day"]}; các buổi khác giữ nguyên. {reason}')
            except sqlite3.IntegrityError as error:
                raise ValueError('Ngày ngoại lệ hoặc buổi gốc đã được dùng cho một đơn khác.') from error
        if existing == 'O':
            try:
                self.write(student['classId'], original, {record['code']: ''},
                           f'Mở lại buổi có ngoại lệ; {actor}; {reason}')
            except Exception:
                self.catalog.refresh()
                if self.status_at(record['code'], record['day'], 'mass') == 'O' and changed:
                    with self.db() as db:
                        db.execute('UPDATE requests SET exception_day=?,status=? WHERE id=?',
                                   (record['exception_day'], record['status'], record['id']))
                        self.request_event(db, record['id'], 'reschedule_failed', actor,
                                           'Chưa mở lại được Excel; giữ ngày hẹn trước đó. ' + reason)
                raise
        if attended:
            session = self.create_session({'date': target, 'activity': 'mass', 'scope': student['className']})
            return self.workflow_scan({**values, 'sessionId': session['id'], 'code': record['code'], 'manual': True})
        return {'saved': True, 'state': self.bootstrap()}

    def request_event(self, db, identifier, action, actor, reason):
        db.execute('INSERT INTO request_events(request_id,action,actor,reason,stamp) VALUES (?,?,?,?,?)',
                   (identifier, action, actor, reason, self.stamp()))

    def obligation(self, student, original, activity):
        session = {'date': day(original), 'activity': activity, 'scope': student['className']}
        if activity not in ACTIVITIES or session['date'] not in self.catalog.classes[student['classId']]['calendar'][activity]:
            raise ValueError('Ngày gốc / hoạt động không có trong lịch của lớp của lớp.')
        if student['enrolledFrom'] and student['enrolledFrom'] > session['date']:
            raise ValueError('Ngày gốc sớm hơn tháng nhập học.')
        return session

    def status_at(self, code, original, activity):
        return self.catalog.marks.get(f'{original}|{activity}|{code}', {}).get('status', '')

    def session_people(self, session):
        people = {s['id']: s for s in self.catalog.eligible(session)}
        if session['activity'] == 'mass':
            for s in self.catalog.students.values():
                if (session['scope'] == 'all' or s['className'] == session['scope']) and (not s['enrolledFrom'] or s['enrolledFrom'] <= session['date']):
                    people[s['id']] = s
            for request in self.requests():
                student = self.catalog.students.get(request['code'])
                if (student and request['kind'] == 'makeup' and request['effective_target_day'] == session['date']
                        and request['status'] in ('approved', 'completed', 'missed')
                        and request['actual_day'] in (None, session['date'])
                        and (session['scope'] == 'all' or student['className'] == session['scope'])):
                    people[student['id']] = student
        return list(people.values())

    def create_request(self, values):
        self.catalog.refresh()
        actor, reason = self.actor(values)
        student = self.catalog.students.get(str(values.get('code', '')).upper().strip())
        if not student:
            raise ValueError('Không tìm thấy học sinh trong sổ.')
        kind = values.get('kind')
        activities = values.get('activities', [values.get('activity')])
        if kind not in ('leave', 'makeup') or not isinstance(activities, list) or not activities or len(activities) > 3 or len(set(activities)) != len(activities):
            raise ValueError('Loại đơn hoặc hoạt động không hợp lệ.')
        original = day(values.get('date'))
        replacement = day(values.get('targetDate')) if kind == 'makeup' else None
        if kind == 'makeup' and activities != ['mass']:
            raise ValueError('Chỉ Thánh lễ được đổi ngày.')
        for activity in activities:
            session = self.obligation(student, original, activity)
            if self.locked(session, student['classId']) and not values.get('_manager'):
                raise ValueError('Buổi gốc đã chốt. Admin mới được xử lý đơn bổ sung.')
            if self.status_at(student['id'], original, activity) in ('X', 'P'):
                raise ValueError('Học sinh đã có X hoặc P tại buổi gốc. Kiểm tra trạng thái trước khi lập đơn.')
            if kind == 'makeup':
                check_makeup(original, replacement, activity)
                self.check_makeup_available(student['id'], replacement)
                if student['enrolledFrom'] and replacement < student['enrolledFrom']:
                    raise ValueError('Ngày lễ bù sớm hơn tháng nhập học.')
                if self.locked({'date': replacement, 'activity': 'mass'}, student['classId']):
                    raise ValueError('Ngày lễ bù đã chốt. Chọn một ngày khác trong tuần.')
                with self.db() as db:
                    used = db.execute('SELECT 1 FROM scans WHERE code=? AND activity=? AND actual_day=?',
                                      (student['id'], 'mass', replacement)).fetchone()
                if used or self.status_at(student['id'], replacement, 'mass') == 'X':
                    raise ValueError('Ngày thay thế đã có lượt đi lễ được tính. Không dùng lại để tính lễ bù.')
        group, identifiers = secrets.token_hex(12), []
        import sqlite3
        try:
            with self.db() as db:
                for activity in activities:
                    identifier = secrets.token_hex(12)
                    db.execute('INSERT INTO requests(id,group_id,code,kind,activity,day,target_day,reason,author,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
                               (identifier, group, student['id'], kind, activity, original, replacement, reason, actor, self.stamp()))
                    self.request_event(db, identifier, 'created', actor, reason)
                    identifiers.append(identifier)
        except sqlite3.IntegrityError:
            raise ValueError('Buổi này đã có đơn đang xử lý, hoặc ngày thay thế đã được dùng cho một đơn khác.')
        return {'requestIds': identifiers, 'state': self.bootstrap()}

    def review_request(self, values):
        actor, reason = self.actor(values)
        decision = values.get('decision')
        if decision not in ('approve', 'reject', 'cancel'):
            raise ValueError('Hướng xử lý không hợp lệ.')
        request = self.request(values.get('id'))
        # A leave for both activities is approved in the same action; successful parts survive a failed write.
        records = [r for r in self.requests() if r['group_id'] == request['group_id'] and
                   r['status'] in (('pending', 'approved') if decision == 'cancel' else ('pending',))]
        records.sort(key=lambda r: ('mass', 'early', 'lesson').index(r['activity']))
        if not records:
            return {'saved': True, 'state': self.bootstrap()}
        self.catalog.refresh()
        for record in records:
            student = self.catalog.students[record['code']]
            session = self.obligation(student, record['day'], record['activity'])
            if self.locked(session, student['classId']) and not values.get('_manager'):
                raise ValueError('Buổi gốc đã chốt. Chỉ Admin được xử lý đơn này.')
            status = self.status_at(record['code'], record['day'], record['activity'])
            if decision == 'reject':
                new_status = 'rejected'
            elif decision == 'cancel':
                if record['status'] == 'approved':
                    expected = 'P' if record['kind'] == 'leave' else ''
                    if status != expected:
                        raise ValueError('Trạng thái Excel đã thay đổi. Kiểm tra trước khi huỷ đơn.')
                    restored = 'O' if self.locked(session, student['classId']) else ''
                    if status != restored:
                        self.write(student['classId'], session, {record['code']: restored}, f'Huỷ đơn; {actor}; {reason}')
                new_status = 'cancelled'
            else:
                expected = 'P' if record['kind'] == 'leave' else ''
                if status == 'X' or (status == 'P' and record['kind'] != 'leave'):
                    raise ValueError('Excel đã có điểm danh khác với đơn. Không ghi đè tự động.')
                if record['kind'] == 'makeup' and self.locked({'date': record['effective_target_day'], 'activity': 'mass'}, student['classId']):
                    raise ValueError('Buổi lễ bù đã chốt; không thể duyệt đổi vào ngày này.')
                if record['kind'] == 'makeup':
                    with self.db() as db:
                        used = db.execute('SELECT 1 FROM scans WHERE code=? AND activity=? AND actual_day=?',
                                          (record['code'], 'mass', record['effective_target_day'])).fetchone()
                    if used or self.status_at(record['code'], record['effective_target_day'], 'mass') == 'X':
                        raise ValueError('Ngày thay thế đã được tính cho lượt đi lễ khác. Chọn ngày khác trước khi duyệt.')
                if status != expected:
                    self.write(student['classId'], session, {record['code']: expected}, f'Duyệt đơn; {actor}; {reason}')
                new_status = 'approved'
            with self.db() as db:
                db.execute('UPDATE requests SET status=?,reviewer=?,reviewed_at=? WHERE id=?',
                           (new_status, actor, self.stamp(), record['id']))
                self.request_event(db, record['id'], decision, actor, reason)
        return {'saved': True, 'state': self.bootstrap()}

    def request_history(self, identifier):
        record = self.request(identifier)
        with self.db() as db:
            return [dict(r) for r in db.execute('''SELECT e.* FROM request_events e JOIN requests r
                      ON r.id=e.request_id WHERE r.group_id=? ORDER BY e.id DESC''', (record['group_id'],))]

    def awaiting_makeup(self, code, original, activity):
        return next((r for r in self.requests() if r['code'] == code and r['day'] == original and
                     r['activity'] == activity and r['kind'] == 'makeup' and r['status'] == 'approved'), None)

    def pending_for(self, session):
        return [r for r in self.requests() if r['status'] == 'pending' and r['day'] == session['date']
                and r['activity'] == session['activity'] and r['code'] in self.catalog.students
                and (session['scope'] == 'all' or self.catalog.students[r['code']]['className'] == session['scope'])]

    def close_preview(self, values):
        self.catalog.refresh()
        session = self.session(values.get('sessionId'))
        people = [s for s in self.catalog.eligible(session) if self.student_active(s['id'],session['date'])]
        counts = {status: sum(self.status_at(s['id'], session['date'], session['activity']) == status for s in people)
                  for status in ('X', 'P', 'O')}
        waiting = [s for s in people if self.awaiting_makeup(s['id'], session['date'], session['activity'])
                   and not self.status_at(s['id'], session['date'], session['activity'])]
        blanks = sum(not self.status_at(s['id'], session['date'], session['activity']) for s in people)
        due = [r for r in self.requests() if r['kind'] == 'makeup' and r['status'] == 'approved'
               and r['effective_target_day'] == session['date'] and r['code'] in {s['id'] for s in self.session_people(session)}]
        return {'present': counts['X'], 'permitted': counts['P'], 'absent': counts['O'], 'waitingMakeup': len(waiting),
                'willMarkAbsent': blanks-len(waiting), 'makeupsWillMiss': len(due), 'pendingRequests': self.pending_for(session)}

    def finish_makeups(self, cutoff, scope, exact=False):
        self.catalog.refresh()
        records = [r for r in self.requests() if r['kind'] == 'makeup' and r['status'] == 'approved'
                   and (r['effective_target_day'] == cutoff if exact else r['effective_target_day'] <= cutoff)
                   and (scope == 'all' or self.catalog.students[r['code']]['className'] == scope)]
        groups = {}
        for record in records:
            student = self.catalog.students[record['code']]
            groups.setdefault((student['classId'], record['day']), []).append(record)
        for (class_id, original), group in groups.items():
            changes = {}
            for record in group:
                if self.status_at(record['code'], original, 'mass') not in ('', 'O'):
                    raise ValueError('Một lễ bù đã có X hoặc P trong sổ. Người quản lý cần kiểm tra đơn trước khi chốt.')
                with self.db() as db:
                    reserved = db.execute('SELECT 1 FROM scans WHERE code=? AND activity=? AND obligation_day=? AND status=?',
                                          (record['code'], 'mass', original, 'reserved')).fetchone()
                if reserved:
                    raise ValueError('Có lượt quét chưa hoàn tất. Quét lại để xác nhận trước khi chốt lễ bù.')
                if not self.status_at(record['code'], original, 'mass'):
                    changes[record['code']] = 'O'
            if changes:
                self.write(class_id, {'date': original, 'activity': 'mass'}, changes, 'Chốt lễ bù không tham dự')
            with self.db() as db:
                for record in group:
                    db.execute('UPDATE requests SET status=? WHERE id=?', ('missed', record['id']))
                    self.request_event(db, record['id'], 'missed', 'Hệ thống', f'Chốt lễ bù đến ngày {cutoff}')
        return len(records)

    def close_makeups(self, values):
        cutoff = day(values.get('date'))
        if cutoff > datetime.now(self.local_tz).date().isoformat():
            raise ValueError('Không chốt vắng lễ bù trước ngày hẹn.')
        scope = values.get('scope', 'all')
        if scope != 'all' and scope not in [c['name'] for c in self.catalog.classes.values()]:
            raise ValueError('Lớp không hợp lệ.')
        count = self.finish_makeups(cutoff, scope)
        return {'saved': True, 'count': count, 'state': self.bootstrap()}

    def pending_scan(self, identifier):
        with self.db() as db:
            row = db.execute("SELECT * FROM pending_scans WHERE id=?", (identifier,)).fetchone()
            return dict(row) if row else None

    def pending_scans(self, class_ids=None):
        with self.db() as db:
            if class_ids is None:
                rows = db.execute("SELECT * FROM pending_scans WHERE status='pending' ORDER BY scanned_at DESC").fetchall()
            else:
                cids = list(class_ids)
                if not cids:
                    return []
                placeholders = ','.join('?' for _ in cids)
                rows = db.execute(f"SELECT * FROM pending_scans WHERE class_id IN ({placeholders}) AND status='pending' ORDER BY scanned_at DESC", cids).fetchall()
            result = []
            for r in rows:
                s = self.catalog.students.get(r['code'])
                result.append({
                    'id': r['id'],
                    'code': r['code'],
                    'classId': r['class_id'],
                    'className': s['className'] if s else '',
                    'saintName': s['saintName'] if s else '',
                    'fullName': s['fullName'] if s else '',
                    'studentName': f"{s.get('saintName','') + ' ' if s and s.get('saintName') else ''}{s['fullName'] if s else r['code']}".strip(),
                    'sessionId': r['session_id'],
                    'date': r['date'],
                    'activity': r['activity'],
                    'scannedById': r['scanned_by_id'],
                    'scannedByName': r['scanned_by_name'],
                    'scannedAt': r['scanned_at'],
                    'status': r['status']
                })
            return result

    def record_pending_scan(self, session, student, values):
        code = student['id']
        actor = values.get('actor', 'GLV')
        user_id = values.get('_user_id', '')
        # Validate without writing a mark or reserving a scan. Only the receiving
        # class may approve it; retain the server-validated early attendance time.
        preview = self.apply_student_scan(session, student, values, validate_only=True)
        if preview.get('choiceRequired'):
            raise ValueError('Có nhiều buổi cần tính điểm danh. Nhờ GLV phụ trách lớp kiểm tra.')
        public_student = {key: student.get(key, '') for key in
                          ('id', 'saintName', 'fullName', 'classId', 'className')}
        if preview.get('duplicate'):
            return {
                'saved': False,
                'duplicate': True,
                'pending': False,
                'message': f"Em {student.get('saintName', '')} {student['fullName']} ({student['className']}) đã được điểm danh có mặt từ trước.",
                'student': public_student,
                'state': self.bootstrap()
            }
        with self.db() as db:
            existing = db.execute("SELECT * FROM pending_scans WHERE code=? AND date=? AND activity=? AND status='pending'",
                                  (code, session['date'], session['activity'])).fetchone()
        if existing:
            return {
                'saved': False,
                'duplicate': True,
                'pending': True,
                'message': f"Đã có yêu cầu điểm danh giùm cho {student.get('saintName', '')} {student['fullName']} ({student['className']}) đang chờ duyệt.",
                'student': public_student,
                'state': self.bootstrap()
            }
        import secrets
        pending_id = secrets.token_hex(12)
        stamp = self.stamp()
        with self.db() as db:
            db.execute('''INSERT INTO pending_scans(id, code, class_id, session_id, date, activity, scanned_by_id, scanned_by_name, scanned_at, status, attended_at)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)''',
                       (pending_id, code, student['classId'], session['id'], session['date'], session['activity'], user_id, actor, stamp, preview.get('attendedAt')))
        s_name = f"{student.get('saintName', '') + ' ' if student.get('saintName') else ''}{student['fullName']}".strip()
        return {
            'saved': True,
            'pending': True,
            'message': f"Đã ghi nhận điểm danh giùm cho {s_name} ({student['className']}). Yêu cầu đã được chuyển vào danh sách chờ duyệt của lớp.",
            'student': public_student,
            'state': self.bootstrap()
        }

    def select_pending_scans(self, values):
        # Authorization and mutation must resolve precisely the same selection.
        single, multiple = bool(values.get('id')), bool(values.get('ids'))
        bulk = values.get('all', False)
        if not isinstance(bulk, bool) or sum((single, multiple, bulk)) != 1:
            raise ValueError('Chọn một yêu cầu, danh sách yêu cầu hoặc duyệt theo buổi.')
        if not bulk:
            if values.get('classId') or values.get('sessionId'):
                raise ValueError('Không kết hợp mã yêu cầu với bộ lọc lớp hoặc buổi.')
            identifiers = [values['id']] if single else values['ids']
            if (not isinstance(identifiers, list) or not identifiers or
                    any(not isinstance(pid, str) or not pid.strip() for pid in identifiers)):
                raise ValueError('Danh sách yêu cầu không hợp lệ.')
            rows = [self.pending_scan(pid) for pid in dict.fromkeys(identifiers)]
            if any(row is None for row in rows):
                raise ValueError('Không tìm thấy yêu cầu điểm danh giùm.')
            return rows
        if not values.get('classId') and not values.get('sessionId'):
            raise ValueError('Chọn lớp hoặc buổi điểm danh trước khi xử lý hàng loạt.')
        conditions, params = ["status='pending'"], []
        if values.get('classId'):
            conditions.append('class_id=?')
            params.append(values['classId'])
        if values.get('sessionId'):
            session = self.session(values['sessionId'])
            conditions.extend(('date=?', 'activity=?'))
            params.extend((session['date'], session['activity']))
            if session['scope'] != 'all':
                cid = next(c['id'] for c in self.catalog.classes.values() if c['name'] == session['scope'])
                conditions.append('class_id=?')
                params.append(cid)
        with self.db() as db:
            return [dict(row) for row in db.execute(
                'SELECT * FROM pending_scans WHERE '+' AND '.join(conditions), params)]

    def approve_pending_scans(self, values):
        self.catalog.refresh()
        actor = values.get('actor', 'GLV')
        rows = [r for r in self.select_pending_scans(values) if r['status'] == 'pending']
        prepared = []
        # Preflight the whole batch before the first mark is written.
        for row in rows:
            student = self.catalog.students.get(row['code'])
            if not student or student['classId'] != row['class_id']:
                raise ValueError('Thiếu nhi đã đổi lớp hoặc không còn trong danh sách. Kiểm tra lại yêu cầu.')
            session = {'date': row['date'], 'activity': row['activity'], 'scope': student['className']}
            early_info = {}
            if row['activity'] == 'early':
                if not row.get('attended_at'):
                    raise ValueError('Lượt lễ sớm chưa có giờ đi lễ được xác minh. Nhờ Admin kiểm tra hoặc quét lại.')
                early_info = {'attendedAt': row['attended_at']}
            scan_values = {'manual': False, 'actor': actor, '_manager': False}
            detail = f"Điểm danh giùm bởi {row['scanned_by_name']}, duyệt bởi {actor}"
            preview = self.apply_student_scan(session, student, scan_values, early_info=early_info, validate_only=True)
            if preview.get('choiceRequired'):
                raise ValueError('Có nhiều buổi cần tính điểm danh. Kiểm tra đơn đổi lễ trước khi duyệt.')
            prepared.append((row, student, session, scan_values, early_info, detail))
        approved_count = 0
        stamp = self.stamp()
        for r, student, session, scan_values, early_info, detail in prepared:
            self.apply_student_scan(session, student, scan_values, early_info=early_info, source_detail=detail)
            with self.db() as db:
                db.execute("UPDATE pending_scans SET status='approved', reviewer=?, reviewed_at=? WHERE id=?",
                           (actor, stamp, r['id']))
            approved_count += 1
        return {'saved': True, 'count': approved_count, 'message': f"Đã duyệt điểm danh cho {approved_count} em.", 'state': self.bootstrap()}

    def reject_pending_scans(self, values):
        actor = values.get('actor', 'GLV')
        rows = self.select_pending_scans(values)
        stamp = self.stamp()
        with self.db() as db:
            for row in rows:
                db.execute("UPDATE pending_scans SET status='rejected', reviewer=?, reviewed_at=? WHERE id=? AND status='pending'",
                           (actor, stamp, row['id']))
        return {'saved': True, 'message': "Đã bỏ qua các yêu cầu điểm danh giùm.", 'state': self.bootstrap()}

    def workflow_scan(self, values):
        self.catalog.refresh()
        session = self.session(values.get('sessionId'))
        raw_code = str(values.get('code', '')).strip().strip('*')
        code = raw_code.upper()
        student = self.catalog.students.get(code)
        if not student:
            norm_q = normalize_vi(raw_code)
            if norm_q:
                exact = [s for s in self.catalog.students.values()
                         if normalize_vi(s['fullName']) == norm_q or normalize_vi(s['name']) == norm_q]
                if not exact:
                    exact = [s for s in self.catalog.students.values()
                             if norm_q in normalize_vi(s['fullName']) or norm_q in normalize_vi(s['name']) or norm_q in normalize_vi(s['id'])]
                if session['scope'] != 'all' and len(exact) > 1:
                    scoped = [s for s in exact if s['className'] == session['scope']]
                    if scoped:
                        exact = scoped
                if len(exact) == 1:
                    student = exact[0]
                    code = student['id']
                elif len(exact) > 1:
                    names = ', '.join(f"{s['name']} ({s['className']})" for s in exact[:4])
                    raise ValueError(f"Tìm thấy {len(exact)} em có tên phù hợp ({names}). Vui lòng nhập mã thẻ hoặc chọn đúng em.")
        if not student:
            raise ValueError(f"Không tìm thấy học sinh theo tên hoặc mã '{raw_code}' trong sổ.")
        if session['scope'] != 'all' and session['scope'] != student['className']:
            if hasattr(self, 'record_pending_scan'):
                return self.record_pending_scan(session, student, values)
            raise ValueError(f'Học sinh thuộc {student["className"]}, ngoài phạm vi buổi này.')
        return self.apply_student_scan(session, student, values)

    def apply_student_scan(self, session, student, values, *, early_info=None, validate_only=False, source_detail=''):
        code = student['id']
        if not self.student_active(code, session['date']):
            raise ValueError('Thiếu nhi đang tạm nghỉ/nghỉ học vào ngày quét.')
        with self.db() as db:
            scanned = db.execute('SELECT * FROM scans WHERE code=? AND activity=? AND actual_day=?',
                                 (code, session['activity'], session['date'])).fetchone()
        if not isinstance(values.get('manual', False), bool):
            raise ValueError('Hình thức nhập điểm danh không hợp lệ.')
        if early_info is None:
            early_info = self.validate_early_attendance(session, values) if session['activity'] == 'early' else {}
        options = []
        if session['date'] in self.catalog.classes[student['classId']]['calendar'][session['activity']]:
            options.append({'date': session['date'], 'kind': 'regular', 'requestId': None})
        if session['activity'] == 'mass':
            makeups = [{'date': r['day'], 'kind': 'makeup', 'requestId': r['id']} for r in self.requests()
                       if r['code'] == code and r['kind'] == 'makeup' and r['status'] == 'approved'
                       and r['effective_target_day'] == session['date']]
            # An approved transfer credits its original Excel date, even when
            # the replacement date also has a regular Mass in the class calendar.
            # Never infer a transfer from another blank date in the same week.
            if makeups:
                options = makeups
        if scanned:
            if scanned['status']=='supplemental':
                return {'student':student,'duplicate':True,'creditedDate':session['date'],'saved':True,
                        'message':'Ngày đi lễ này đã được cộng lễ bổ sung; không cộng thêm điểm danh.','state':self.bootstrap()}
            if values.get('obligationDate') and values['obligationDate'] != scanned['obligation_day']:
                raise ValueError('Lượt quét ngày này đã được tính cho một buổi khác. Không cộng hai lần.')
            chosen = {'date': scanned['obligation_day'], 'kind': 'makeup' if scanned['request_id'] else 'regular', 'requestId': scanned['request_id']}
        else:
            if not options:
                raise ValueError('Học sinh không có lịch hoặc đơn lễ bù đã duyệt trong ngày này.')
            if len(options) > 1 and not values.get('obligationDate'):
                return {'choiceRequired': True, 'student': student, 'options': options}
            chosen = next((o for o in options if not values.get('obligationDate') or o['date'] == values['obligationDate']), None)
            if not chosen:
                raise ValueError('Buổi được chọn không khớp lịch hoặc đơn đã duyệt.')
        original = self.obligation(student, chosen['date'], session['activity'])
        if not scanned and self.locked(session, student['classId']):
            exception_request = self.request(chosen['requestId']) if chosen['requestId'] else None
            if not (exception_request and exception_request['exception_day'] == session['date']
                    and values.get('_manager') and values.get('manual')):
                raise ValueError('Buổi quét đã chốt; chưa ghi thêm lượt.')
            self.actor(values)
        if chosen['kind'] == 'regular' and not scanned and self.locked(original, student['classId']):
            raise ValueError('Buổi gốc đã chốt.')
        existing = self.status_at(code, chosen['date'], session['activity'])
        if scanned and scanned['status'] == 'saved' and existing != 'X':
            raise ValueError('Lượt điểm danh này đã được điều chỉnh. Không tự ghi đè bằng cách quét lại; nhờ người quản lý kiểm tra.')
        if existing and existing != 'X':
            raise ValueError(f'Buổi gốc đã có {existing}. Kiểm tra đơn hoặc chỉnh trạng thái trước khi quét.')
        if chosen['kind'] == 'makeup' and existing == 'X' and not scanned:
            raise ValueError('Buổi gốc đã có X bên ngoài lượt lễ bù này. Không tính thêm lượt.')
        if validate_only:
            return {**early_info, 'duplicate': existing == 'X' or bool(scanned and scanned['status'] == 'supplemental')}
        if not scanned:
            # Reservation persists before native save, so a restart between Excel and SQLite cannot double-credit.
            import sqlite3
            try:
                with self.db() as db:
                    db.execute('INSERT INTO scans VALUES (?,?,?,?,?,?,?,?)',
                               (secrets.token_hex(12), code, session['activity'], session['date'], chosen['date'], chosen['requestId'], 'reserved', self.stamp()))
            except sqlite3.IntegrityError:
                raise ValueError('Buổi gốc đã được tính bởi một lượt quét khác. Không ghi thêm.')
        duplicate = existing == 'X'
        if not duplicate:
            source_desc = f'Nhập tay (quên thẻ/nhập sau) - Ngày {session["date"]}' if values.get('manual') else f'Quét ngày {session["date"]}; tính buổi {chosen["date"]}'
            if early_info:
                source_desc += f'; đi thực tế {early_info["attendedAt"]}'
                if values.get('manual') and values.get('actor'):
                    source_desc += f'; {values["actor"]}; {values.get("reason", "")}'
            if source_detail:
                source_desc += '; '+source_detail
            try:
                result = self.write(student['classId'], original, {code: 'X'}, source_desc)
            except Exception:
                # Only release a reservation if Excel proves the input was not saved.
                self.catalog.refresh()
                if self.status_at(code, chosen['date'], session['activity']) != 'X':
                    with self.db() as db:
                        db.execute('DELETE FROM scans WHERE code=? AND activity=? AND actual_day=? AND status=?',
                                   (code, session['activity'], session['date'], 'reserved'))
                raise
        else:
            result = {'saved': True, 'vbaExecuted': False}
        with self.db() as db:
            db.execute('UPDATE scans SET status=? WHERE code=? AND activity=? AND actual_day=?', ('saved', code, session['activity'], session['date']))
            active = [r for r in self.requests() if r['code'] == code and r['day'] == chosen['date'] and r['activity'] == session['activity'] and r['status'] in ('pending', 'approved')]
            for record in active:
                status = 'completed' if record['kind'] == 'makeup' and record['status'] == 'approved' else 'cancelled'
                db.execute('UPDATE requests SET status=?,actual_day=? WHERE id=?', (status, session['date'], record['id']))
                self.request_event(db, record['id'], status, 'Nhập tay' if values.get('manual') else 'Quét QR', f'Có mặt ngày {session["date"]}; tính cho {chosen["date"]}')
        return {**result, **early_info, 'student': student, 'duplicate': duplicate, 'creditedDate': chosen['date'],
                'actualDate': session['date'], 'isMakeup': chosen['date'] != session['date'], 'state': self.bootstrap()}


import hashlib
import json


class CareRules:
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
                    raise ValueError('Ngày gốc đã có trạng thái trong sổ.')
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
            issues.append('Không có buổi lễ gốc phù hợp trong lịch của lớp.')
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
