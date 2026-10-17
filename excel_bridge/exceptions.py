"""Approved leave and weekday makeups; Excel retains its original X/O/P cells."""
import secrets
import re
import unicodedata
from datetime import date, datetime, timedelta, time as clock_time

from catalog import ACTIVITIES


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
            raise ValueError('Nhập bổ sung lễ sớm ngoài khung giờ cần người quản lý trên máy Excel xác nhận.')
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
            raise ValueError('Buổi đã chốt; người quản lý trên máy Excel mới được xác nhận ngoại lệ.')
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
            raise ValueError('Ngày gốc / hoạt động không có trong lịch Excel của lớp.')
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
            raise ValueError('Không tìm thấy học sinh trong Excel.')
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
                raise ValueError('Buổi gốc đã chốt. Người quản lý trên máy Excel mới được xử lý đơn bổ sung.')
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
                raise ValueError('Buổi gốc đã chốt. Chỉ người quản lý trên máy Excel được xử lý đơn này.')
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
                    raise ValueError('Một lễ bù đã có X hoặc P trong Excel. Người quản lý cần kiểm tra đơn trước khi chốt.')
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

    def scan_preview(self, values):
        self.catalog.refresh()
        session = self.session(values.get('sessionId'))
        code = str(values.get('code') or '').strip().strip('*').upper()
        student = self.catalog.students.get(code)
        if not student:
            raise ValueError('Không tìm thấy thiếu nhi theo mã thẻ này.')
        if not self.student_active(code, session['date']):
            raise ValueError('Thiếu nhi đang tạm nghỉ/nghỉ học vào ngày quét.')
        return {'student': {key: student.get(key, '') for key in
                            ('id', 'saintName', 'fullName', 'classId', 'className')},
                'sessionId': session['id'],
                'proxy': session['scope'] != 'all' and session['scope'] != student['className']}

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

