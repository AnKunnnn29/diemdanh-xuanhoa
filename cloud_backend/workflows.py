"""Request-scoped attendance working set, committed atomically to PostgreSQL.

The SQLite connection below is strictly :memory:. It runs the existing tested
parish rules without files, processes, a background service or Office. PostgreSQL
is the sole durable store. Its transaction lock covers load, validation and save
across separate Vercel instances, including marks and request/scan histories.
"""
import hashlib
import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from sqlalchemy import select, insert, update, delete
from . import models as m
from .security import CloudError
from .workflow_rules import CareRules, ExceptionWorkflow, ACTIVITIES, normalize_vi

LOCAL_TZ = timezone(timedelta(hours=7))
TABLES = ('sessions', 'locks', 'requests', 'request_events', 'scans', 'recurring_mass',
          'student_status', 'care_notes', 'management_events', 'settings', 'year_plans',
          'issued_codes', 'supplemental_mass', 'pending_scans')
OPERATIONS = {
    'sessions': 'create_session', 'scan': 'scan', 'scan-preview': 'scan_preview', 'mark': 'set_mark', 'close': 'close_session',
    'requests': 'create_request', 'review': 'review_request', 'reschedule-makeup': 'reschedule_makeup',
    'close-preview': 'close_preview', 'close-makeup': 'close_makeups',
    'recurring-preview': 'recurring_preview', 'recurring-mass': 'create_recurring',
    'recurring-stop': 'stop_recurring', 'student-status': 'set_student_status', 'care-note': 'save_care_note',
    'pending-scans-approve': 'approve_pending_scans', 'pending-scans-reject': 'reject_pending_scans',
}


class Catalog:
    def __init__(self, db, year):
        self.classes = {r['id']: {**r['payload'], 'id': r['id'], 'name': r['name'],
                        'archived': r['archived'], 'revision': r['revision']}
                        for r in db.execute(select(m.classes).where(m.classes.c.year_id == year)).mappings()}
        self.students = {r['code']: {'enrolledFrom': None, 'saintName': '', 'fullName': '', **r['payload'], 'id': r['code'], 'classId': r['class_id'],
                         'className': self.classes[r['class_id']]['name'], 'revision': r['revision']}
                         for r in db.execute(select(m.students).where(m.students.c.year_id == year)).mappings()}
        self.marks = {f"{r['day']}|{r['activity']}|{r['code']}": {
                      'status': r['status'], 'timestamp': r['stamp'], 'source': r['source']}
                      for r in db.execute(select(m.marks).where(m.marks.c.year_id == year)).mappings()}
        for c in self.classes.values():
            c['count'] = sum(s['classId'] == c['id'] for s in self.students.values())

    def refresh(self):
        # This working set belongs to the current locked PostgreSQL transaction.
        pass

    def public(self):
        dates = sorted(d for c in self.classes.values() for d in c['calendar']['mass'])
        start = int(dates[0][:4]) if dates else datetime.now(LOCAL_TZ).year
        if dates and int(dates[0][5:7]) < 9:
            start -= 1
        return {'year': f'{start}-{start+1}', 'classes': list(self.classes.values()),
                'students': list(self.students.values()), 'marks': self.marks}

    def eligible(self, session):
        return [s for s in self.students.values() if
                (session['scope'] == 'all' or s['className'] == session['scope']) and
                session['date'] in self.classes[s['classId']]['calendar'][session['activity']] and
                (not s.get('enrolledFrom') or s['enrolledFrom'] <= session['date'])]


class Workflow(CareRules, ExceptionWorkflow):
    local_tz = LOCAL_TZ

    def __init__(self, connection, year_id):
        self.connection, self.year_id = connection, year_id
        self.catalog = Catalog(connection, year_id)
        self.management = SimpleNamespace(class_statuses=lambda: {
            cid: c['archived'] for cid, c in self.catalog.classes.items()})
        self.memory = sqlite3.connect(':memory:')
        self.memory.row_factory = sqlite3.Row
        self.memory.executescript('''
            CREATE TABLE sessions(id TEXT PRIMARY KEY,day TEXT,activity TEXT,scope TEXT,closed INTEGER DEFAULT 0);
            CREATE TABLE locks(day TEXT,activity TEXT,class_id TEXT,PRIMARY KEY(day,activity,class_id));
            CREATE TABLE issued_codes(code TEXT PRIMARY KEY,stamp TEXT);
            CREATE TABLE supplemental_mass(id TEXT PRIMARY KEY,code TEXT,actual_day TEXT,actor TEXT,reason TEXT,status TEXT,stamp TEXT,updated_at TEXT);
            CREATE UNIQUE INDEX one_supplement_per_day ON supplemental_mass(code,actual_day) WHERE status='active';
            CREATE TABLE IF NOT EXISTS pending_scans(
                id TEXT PRIMARY KEY, code TEXT, class_id TEXT, session_id TEXT, date TEXT, activity TEXT,
                scanned_by_id TEXT, scanned_by_name TEXT, scanned_at TEXT, status TEXT DEFAULT 'pending',
                reviewer TEXT, reviewed_at TEXT, attended_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_pending_scans_cloud ON pending_scans(class_id, status);
        ''')
        self.init_exceptions()
        self.init_development()
        rows = connection.execute(select(m.records).where(m.records.c.year_id == year_id,
            m.records.c.kind.in_(('workflow-state', 'source-table')))).mappings().all()
        stored = next((r for r in rows if r['kind'] == 'workflow-state' and r['id'] == 'v1'), None)
        self.stored = stored is not None
        tables = stored['payload']['tables'] if stored else {
            r['id']: r['payload'].get('rows', []) for r in rows if r['kind'] == 'source-table'}
        for name in TABLES:
            allowed = {r['name'] for r in self.memory.execute(f'PRAGMA table_info("{name}")')}
            for row in tables.get(name, []):
                keys = [key for key in row if key in allowed]
                if keys:
                    self.memory.execute(f'INSERT INTO "{name}" ('+', '.join('"'+k+'"' for k in keys)+
                        ') VALUES ('+', '.join('?' for _ in keys)+')', [row[key] for key in keys])
        for code in self.catalog.students:
            self.memory.execute('INSERT OR IGNORE INTO issued_codes VALUES (?,?)', (code, self.stamp()))
        self.memory.commit()
        self.original = self.dump()

    @contextmanager
    def db(self):
        yield self.memory

    def bootstrap(self):
        # The outer API attaches the authorized state after all operations finish.
        return {}

    def dump(self):
        return {'tables': {table: [dict(row) for row in self.memory.execute(f'SELECT * FROM "{table}"')]
                           for table in TABLES}}

    def flush(self):
        payload = self.dump()
        if payload == self.original:
            return
        condition = (m.records.c.year_id == self.year_id, m.records.c.kind == 'workflow-state', m.records.c.id == 'v1')
        if self.stored:
            self.connection.execute(update(m.records).where(*condition).values(payload=payload, revision=m.records.c.revision+1))
        else:
            self.connection.execute(insert(m.records).values(year_id=self.year_id, kind='workflow-state', id='v1', payload=payload, revision=1))
        self.stored, self.original = True, payload

    def shutdown(self):
        self.memory.close()

    def write(self, class_id, session, changes, source):
        group = self.catalog.classes[class_id]
        if group['archived']:
            raise CloudError('Lớp đã lưu trữ. Mở lại trước khi ghi điểm danh.')
        for code, status in changes.items():
            if status not in ('', 'X', 'P', 'O') or self.catalog.students.get(code, {}).get('classId') != class_id:
                raise CloudError('Trạng thái hoặc thiếu nhi không hợp lệ.')
            key = f'{session["date"]}|{session["activity"]}|{code}'
            self.connection.execute(delete(m.marks).where(m.marks.c.year_id == self.year_id, m.marks.c.code == code,
                m.marks.c.day == session['date'], m.marks.c.activity == session['activity']))
            self.catalog.marks.pop(key, None)
            if status:
                saved = {'status': status, 'timestamp': self.stamp(), 'source': source[:100]}
                self.connection.execute(insert(m.marks).values(year_id=self.year_id, code=code,
                    day=session['date'], activity=session['activity'], status=status, stamp=saved['timestamp'], source=saved['source']))
                self.catalog.marks[key] = saved
        return {'saved': True, 'vbaExecuted': False, 'timestamp': self.stamp()}

    def public(self, user):
        ids = set(user['classIds'])
        names = {c['name'] for cid, c in self.catalog.classes.items() if cid in ids}
        codes = {s['id'] for s in self.catalog.students.values() if s['classId'] in ids}
        requests = [r for r in self.requests() if r['code'] in codes]
        request_ids = {r['id'] for r in requests}
        sessions = []
        for s in self.sessions():
            if s['scope'] not in names and not (s['scope'] == 'all' and user['role'] == 'Admin'):
                continue
            classes = {p['classId'] for p in self.session_people(s)}
            locked = [cid for cid in classes if self.locked(s, cid)]
            sessions.append({**s, 'lockedClassIds': locked,
                'closed': s['closed'] or bool(classes) and len(locked) == len(classes)})
        data = self.development_public()
        for name in ('recurringMass', 'studentStatuses', 'careNotes'):
            data[name] = [r for r in data[name] if r['code'] in codes]
        if user['role'] != 'Admin':
            data['managementEvents'], data['yearPlans'] = [], []
        return {**data, 'sessions': sessions, 'requests': requests,
                'pendingScans': self.pending_scans(ids),
                'requestEvents': [dict(r) for r in self.memory.execute('SELECT * FROM request_events ORDER BY id DESC')
                                  if r['request_id'] in request_ids]}

    def authorize(self, user, action, values):
        admin = user['role'] == 'Admin'
        ids = set(user['classIds'])
        def group(cid):
            c = self.catalog.classes.get(cid)
            if not c or cid not in ids:
                raise CloudError('Thiếu nhi hoặc lớp ngoài phạm vi được phân công.', 403, 'forbidden')
            if c['archived']:
                raise CloudError('Lớp đã lưu trữ. Admin cần mở lại trước khi chỉnh sửa.')
            return c
        def student(code):
            s = self.catalog.students.get(str(code or '').strip().strip('*').upper())
            group(s['classId'] if s else None)
            return s
        def scope(value):
            if value == 'all' and admin:
                return
            group(next((c['id'] for c in self.catalog.classes.values() if c['name'] == value), None))
        if action in ('sessions', 'close-makeup'):
            scope(values.get('scope', 'all'))
        elif action in ('pending-scans-approve', 'pending-scans-reject'):
            rows = self.select_pending_scans(values)
            if values.get('classId'):
                group(values['classId'])
            if values.get('sessionId'):
                scope(self.session(values.get('sessionId'))['scope'])
            for row in rows:
                group(row['class_id'])
                student(row['code'])
        elif action in ('scan', 'scan-preview', 'mark', 'close', 'close-preview'):
            session = self.session(values.get('sessionId'))
            scope(session['scope'])
            if action == 'scan':
                raw = str(values.get('code') or '').strip().strip('*')
                if raw.upper() not in self.catalog.students:
                    query = normalize_vi(raw)
                    people = [s for s in self.catalog.students.values() if s['classId'] in ids
                        and (session['scope'] == 'all' or s['className'] == session['scope'])]
                    matches = [s for s in people if query and query in (normalize_vi(s['fullName']), normalize_vi(s['name']))]
                    matches = matches or [s for s in people if query and any(query in normalize_vi(s[k]) for k in ('fullName', 'name', 'id'))]
                    if not matches:
                        all_matches = [s for s in self.catalog.students.values() if query and (query in (normalize_vi(s['fullName']), normalize_vi(s['name'])) or any(query in normalize_vi(s[k]) for k in ('fullName', 'name', 'id')))]
                        if len(all_matches) == 1:
                            matches = all_matches
                        elif len(all_matches) > 1:
                            raise CloudError('Có nhiều em trùng tên. Chọn em hoặc nhập mã thẻ.')
                        else:
                            raise CloudError('Không tìm thấy thiếu nhi theo tên hoặc mã thẻ.')
                    values['code'] = matches[0]['id']
                else:
                    values['code'] = raw.upper()
            elif action == 'mark':
                student(values.get('code'))
        elif action in ('review', 'reschedule-makeup'):
            student(self.request(values.get('id'))['code'])
        elif action == 'recurring-stop':
            row = self.memory.execute('SELECT code FROM recurring_mass WHERE id=?', (values.get('id'),)).fetchone()
            student(row['code'] if row else None)
        else:
            student(values.get('code'))

    def execute(self, user, action, values):
        values = {k: v for k, v in values.items() if k not in ('_manager', '_bypass_time', 'actor', 'user')}
        values.update(actor=user['displayName'], _manager=user['role'] == 'Admin', _user_id=user['id'])
        try:
            self.authorize(user, action, values)
            result = getattr(self, OPERATIONS[action])(values)
        except (ValueError, sqlite3.IntegrityError, TypeError, KeyError) as error:
            raise CloudError(str(error) if isinstance(error,ValueError) else 'Dữ liệu yêu cầu chưa hợp lệ.') from error
        self.flush()
        return result


    def sessions(self):
        with self.db() as db:
            return [{'id': r['id'], 'date': r['day'], 'activity': r['activity'], 'scope': r['scope'],
                     'closed': bool(r['closed'])} for r in db.execute('SELECT * FROM sessions ORDER BY rowid')]

    def session(self, identifier):
        result = next((s for s in self.sessions() if s['id'] == identifier), None)
        if not result:
            raise ValueError('Buổi điểm danh không tồn tại. Hãy tải lại trang.')
        return result

    def create_session(self, values):
        self.catalog.refresh()
        try:
            day = date.fromisoformat(values['date']).isoformat()
        except (KeyError, TypeError, ValueError):
            raise ValueError('Ngày điểm danh không hợp lệ.')
        activity = values.get('activity', 'mass')
        scope = values.get('scope', 'all')
        if activity not in ACTIVITIES or (scope != 'all' and scope not in [c['name'] for c in self.catalog.classes.values()]):
            raise ValueError('Hoạt động hoặc lớp không hợp lệ.')
        if scope!='all' and getattr(self,'management',None):
            cid=next(c['id'] for c in self.catalog.classes.values() if c['name']==scope)
            if self.management.class_statuses().get(cid): raise ValueError('Lớp đã lưu trữ. Mở lại lớp trước khi tạo buổi.')
        if activity in ('early', 'lesson') and date.fromisoformat(day).weekday() != 6:
            raise ValueError('Đi lễ sớm và học giáo lý chỉ diễn ra vào ngày Chúa Nhật.')
        session = {'date': day, 'activity': activity, 'scope': scope}
        identifier = hashlib.sha256(f'{day}|{activity}|{scope}'.encode()).hexdigest()[:24]
        with self.db() as db:
            db.execute('INSERT OR IGNORE INTO sessions(id,day,activity,scope) VALUES (?,?,?,?)', (identifier, day, activity, scope))
        return {'id': identifier, **session, 'closed': False}

    def locked(self, session, class_id):
        with self.db() as db:
            return db.execute('SELECT 1 FROM locks WHERE day=? AND activity=? AND class_id=?',
                              (session['date'], session['activity'], class_id)).fetchone() is not None

    def check(self, session, code):
        if not self.student_active(code, session['date']):
            raise ValueError('Thiếu nhi đang tạm nghỉ/nghỉ học vào ngày này.')
        self.catalog.refresh()
        student = self.catalog.students.get(code)
        if not student:
            raise ValueError('Không tìm thấy mã QR trong danh sách Excel. Kiểm tra thẻ hoặc mã học sinh.')
        if session['scope'] != 'all' and student['className'] != session['scope']:
            raise ValueError(f'Học sinh thuộc {student["className"]}, ngoài phạm vi buổi này.')
        info = self.catalog.classes[student['classId']]
        if session['date'] not in info['calendar'][session['activity']]:
            raise ValueError(f'{student["className"]} không có hoạt động này ngày {session["date"]} trong Excel. Đổi ngày / hoạt động trước khi quét.')
        if student['enrolledFrom'] and student['enrolledFrom'] > session['date']:
            raise ValueError('Ngày điểm danh sớm hơn tháng nhập học của học sinh.')
        if self.locked(session, student['classId']):
            raise ValueError('Lớp này đã chốt buổi điểm danh; chưa thay đổi Excel.')
        return student

    def scan(self, values):
        return self.workflow_scan(values)

    def set_mark(self, values):
        status = values.get('status')
        if status not in ('', 'X', 'P', 'O'):
            raise ValueError('Trạng thái không hợp lệ.')
        session = self.session(values.get('sessionId'))
        code = str(values.get('code', '')).strip().upper()
        actor, reason = self.actor(values)
        self.catalog.refresh()
        student = self.catalog.students.get(code)
        if not student or (session['scope'] != 'all' and student['className'] != session['scope']):
            raise ValueError('Học sinh không thuộc phạm vi buổi này.')
        self.obligation(student, session['date'], session['activity'])
        early_info = self.validate_early_attendance(session, {**values, 'manual': True}) if status == 'X' and session['activity'] == 'early' else {}
        if (self.locked(session, student['classId']) or status == 'P') and not values.get('_manager'):
            raise ValueError('Xin phép cần lập và duyệt đơn; sửa buổi đã chốt cần người quản lý trên máy Excel.')
        old = self.catalog.marks.get(f'{session["date"]}|{session["activity"]}|{code}', {}).get('status', '')
        detail = f'; đi thực tế {early_info["attendedAt"]}' if early_info else ''
        result = {'saved': True, 'vbaExecuted': False} if old == status else self.write(student['classId'], session, {code: status}, f'Điều chỉnh {old or "trống"} → {status or "trống"}; {actor}; {reason}{detail}')
        if old != status:
            with self.db() as db:
                if status != 'X':
                    db.execute('DELETE FROM scans WHERE code=? AND activity=? AND actual_day=?', (code, session['activity'], session['date']))
                for record in self.requests():
                    if record['code'] == code and record['day'] == session['date'] and record['activity'] == session['activity'] and record['status'] in ('pending','approved','completed'):
                        db.execute('UPDATE requests SET status=? WHERE id=?', ('cancelled', record['id']))
                        self.request_event(db, record['id'], 'corrected', actor, reason)
                self.request_event(db, None, 'corrected', actor, f'{code}; {session["date"]}; {session["activity"]}; {old or "trống"} → {status or "trống"}; {reason}{detail}')
        return {**result, **early_info, 'student': student, 'state': self.bootstrap()}

    def close_session(self, values):
        session = self.session(values.get('sessionId'))
        if session['date'] > datetime.now(LOCAL_TZ).date().isoformat():
            raise ValueError('Không chốt vắng trước ngày diễn ra buổi điểm danh.')
        self.catalog.refresh()
        if self.pending_for(session):
            raise ValueError('Có đơn chưa duyệt trong buổi này. Duyệt hoặc từ chối đơn trước khi chốt.')
        classes = {s['classId'] for s in self.session_people(session)}
        for class_id in classes:
            if self.locked(session, class_id):
                continue
            changes = {s['id']: 'O' for s in self.catalog.eligible(session) if s['classId'] == class_id
                       and self.student_active(s['id'],session['date'])
                       and f'{session["date"]}|{session["activity"]}|{s["id"]}' not in self.catalog.marks
                       and not self.awaiting_makeup(s['id'], session['date'], session['activity'])}
            if changes:
                self.write(class_id, session, changes, 'Chốt buổi')
            if session['activity'] == 'mass':
                self.finish_makeups(session['date'], self.catalog.classes[class_id]['name'], exact=True)
            with self.db() as db:
                db.execute('INSERT OR IGNORE INTO locks VALUES (?,?,?)', (session['date'], session['activity'], class_id))
        with self.db() as db:
            db.execute('UPDATE sessions SET closed=1 WHERE id=?', (session['id'],))
        return {'saved': True, 'state': self.bootstrap()}
