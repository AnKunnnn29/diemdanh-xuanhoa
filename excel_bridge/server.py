"""Local web + authenticated LAN HTTPS + a serialized native Excel API."""
import argparse
import hashlib
import io
import ipaddress
import json
import logging
import mimetypes
import os
import secrets
import socket
import sqlite3
import ssl
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta, date
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

from catalog import Catalog, ACTIVITIES
from exceptions import ExceptionWorkflow
from validation import PROFILE_FIELDS, validate_grades
from development import DevelopmentFeatures, recover_transactions
from parity import ExcelParity
from accounts import Accounts, AccessError
from access import Gateway
from management import Management, recover_management

LOCAL_TZ = timezone(timedelta(hours=7))
HERE = Path(__file__).resolve().parent
WEB = HERE.parent / 'dist'
DEFAULT_ROOT = HERE.parents[2]
# Hash of the complete VBA source inspected in the supplied template, filled at implementation time.
TRUSTED_VBA = 'eb99a820b87a4277893f5e867dae51229a02a3f82546fa99cf1faa3b7a9b00ea'


def ExcelEngine(catalog):
    # Grade calculation/export can run on Linux without importing Windows COM.
    from native import ExcelEngine as NativeEngine
    return NativeEngine(catalog)


class Store(ExcelParity, DevelopmentFeatures, ExceptionWorkflow):
    local_tz = LOCAL_TZ
    def __init__(self, root, state_dir, grade_mode='native'):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        recover_transactions(root, self.state_dir, TRUSTED_VBA)
        self.catalog = Catalog(root, self.state_dir, TRUSTED_VBA)
        self.engine = None
        self.grade_mode = grade_mode
        self._grades = None
        self.database = self.state_dir / 'attendance.sqlite3'
        with self.db() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, day TEXT, activity TEXT, scope TEXT, closed INTEGER DEFAULT 0);
              CREATE TABLE IF NOT EXISTS locks(day TEXT, activity TEXT, class_id TEXT, PRIMARY KEY(day,activity,class_id));
              CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, mark_key TEXT, status TEXT, stamp TEXT, source TEXT, workbook TEXT, macro TEXT);
              CREATE TABLE IF NOT EXISTS pending_scans(
                  id TEXT PRIMARY KEY,
                  code TEXT NOT NULL,
                  class_id TEXT NOT NULL,
                  session_id TEXT NOT NULL,
                  date TEXT NOT NULL,
                  activity TEXT NOT NULL,
                  scanned_by_id TEXT NOT NULL,
                  scanned_by_name TEXT NOT NULL,
                  scanned_at TEXT NOT NULL,
                  status TEXT NOT NULL DEFAULT 'pending',
                  reviewer TEXT,
                  reviewed_at TEXT
              );
              CREATE INDEX IF NOT EXISTS idx_pending_scans_class_status ON pending_scans(class_id, status);
            ''')
        with self.db() as db:
            if 'attended_at' not in {r['name'] for r in db.execute('PRAGMA table_info(pending_scans)')}:
                db.execute('ALTER TABLE pending_scans ADD COLUMN attended_at TEXT')
        self.init_exceptions()
        self.init_development()
        self.init_parity()

    def grade_service(self):
        if self._grades is None:
            from portable_grades import PortableGrades
            self._grades=PortableGrades(self.catalog,self.database)
        return self._grades

    def read_grades(self,class_id,semester=1):
        if self.grade_mode=='portable':return self.grade_service().read(class_id,semester)
        self.catalog.refresh()
        return self.catalog.read_grades(class_id,semester)

    def export_grades(self,class_id):
        if self.grade_mode=='portable':return self.grade_service().export(class_id)
        self.catalog.refresh()
        info=self.catalog.classes.get(class_id)
        if not info:raise ValueError('Không tìm thấy lớp.')
        return info['path'].read_bytes(),info['filename'],'application/vnd.ms-excel.sheet.macroEnabled.12'

    def resolve_grade_conflict(self,values):
        if self.grade_mode!='portable':raise ValueError('Chỉ bộ tính điểm trên server có thao tác này.')
        if type(values.get('semester')) is not int or values['semester'] not in (1,2,3):raise ValueError('Học kỳ không hợp lệ.')
        return self.grade_service().resolve_conflict(values.get('classId'),values)

    @contextmanager
    def db(self):
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def sessions(self):
        with self.db() as db:
            return [{'id': r['id'], 'date': r['day'], 'activity': r['activity'], 'scope': r['scope'],
                     'closed': bool(r['closed'])} for r in db.execute('SELECT * FROM sessions ORDER BY rowid')]

    def session(self, identifier):
        result = next((s for s in self.sessions() if s['id'] == identifier), None)
        if not result:
            raise ValueError('Buổi điểm danh không tồn tại. Hãy tải lại trang.')
        return result

    def bootstrap(self):
        self.catalog.refresh()
        today = datetime.now(LOCAL_TZ).date().isoformat()
        today_session = next((s for s in self.sessions() if s['date'] == today and s['activity'] == 'mass' and s['scope'] == 'all'), None)
        if not today_session:
            self.create_session({'date': today, 'activity': 'mass', 'scope': 'all'})
        result = self.catalog.public()
        with self.db() as db:
            for row in db.execute('SELECT * FROM audit ORDER BY id'):
                entry = result['marks'].get(row['mark_key'])
                if entry and entry['status'] == row['status']:
                    result['marks'][row['mark_key']] = {'status': row['status'], 'timestamp': row['stamp'], 'source': row['source']}
            locks = {(r['day'], r['activity'], r['class_id']) for r in db.execute('SELECT * FROM locks')}
        sessions = self.sessions()
        for s in sessions:
            classes = {person['classId'] for person in self.session_people(s)}
            s['lockedClassIds'] = [c for c in classes if (s['date'], s['activity'], c) in locks]
            s['closed'] = bool(s['closed']) or (bool(classes) and all((s['date'], s['activity'], c) in locks for c in classes))
        with self.db() as db:
            events = [dict(r) for r in db.execute('SELECT * FROM request_events ORDER BY id DESC LIMIT 100')]
        return {**result, **self.development_public(), 'sessions': sessions, 'requests': self.requests(), 'requestEvents': events,
                'pendingScans': self.pending_scans(), 'mode': 'excel', 'connected': True, 'gradeMode': self.grade_mode}

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

    def write(self, class_id, session, changes, source):
        if self.engine is None:
            self.engine = ExcelEngine(self.catalog)
        result = self.engine.write(class_id, session, changes)
        stamp = datetime.now(LOCAL_TZ).isoformat()
        with self.db() as db:
            for code, status in changes.items():
                db.execute('INSERT INTO audit(mark_key,status,stamp,source,workbook,macro) VALUES (?,?,?,?,?,?)',
                           (f'{session["date"]}|{session["activity"]}|{code}', status, stamp, source, result['workbook'], result['macro']))
        return {**result, 'timestamp': stamp}

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

    def export(self, query):
        self.catalog.refresh()
        session = self.session(query.get('sessionId', [''])[0])
        choice = query.get('classId', ['all'])[0]
        infos = [c for c in self.catalog.classes.values() if (choice == 'all' or c['id'] == choice)
                 and (session['scope'] == 'all' or c['name'] == session['scope'])]
        if not infos:
            raise ValueError('Không có file lớp trong phạm vi đã chọn.')
        if choice != 'all':
            return self.export_grades(infos[0]['id'])
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
            for info in infos:
                package,filename,_=self.export_grades(info['id'])
                archive.writestr(filename,package)
        return stream.getvalue(), f'DiemDanh_CacLop_{self.catalog.public()["year"]}.zip', 'application/zip'

    def update_profile(self, values):
        self.catalog.refresh()
        code = str(values.get('code', '')).strip().upper()
        student = self.catalog.students.get(code)
        if not student:
            raise ValueError('Không tìm thấy học sinh.')
        if self.engine is None:
            self.engine = ExcelEngine(self.catalog)
        profile = {name: values[name] for name in PROFILE_FIELDS | {'saintName','fullName'} if name in values}
        res = self.engine.write_profile(student['classId'], code, profile)
        return {**res, 'student': self.catalog.students.get(code), 'state': self.bootstrap()}

    def update_teachers(self, values):
        self.catalog.refresh()
        class_id = values.get('classId')
        if class_id not in self.catalog.classes:
            raise ValueError('Không tìm thấy lớp.')
        if self.engine is None:
            self.engine = ExcelEngine(self.catalog)
        teachers = {name: values[name] for name in ('glv1', 'glv2', 'souer', 'glv3') if name in values}
        res = self.engine.write_teachers(class_id, teachers)
        return {**res, 'state': self.bootstrap()}

    def update_grades(self, values):
        self.catalog.refresh()
        class_id = values.get('classId')
        semester = values.get('semester', 1)
        grades = values.get('grades', [])
        if class_id not in self.catalog.classes:
            raise ValueError('Không tìm thấy lớp.')
        if type(semester) is not int or semester not in (1, 2):
            raise ValueError('Học kỳ phải là 1 hoặc 2.')
        grades = validate_grades(grades, class_id, self.catalog.students)
        if self.grade_mode=='portable':
            return self.grade_service().save(class_id,semester,grades,values.get('expectedRevision'))
        if self.engine is None:
            self.engine = ExcelEngine(self.catalog)
        res = self.engine.write_grades(class_id, semester, grades)
        return {**res, 'grades': self.catalog.read_grades(class_id, semester)}

    def shutdown(self):
        if self.engine is not None:
            self.engine.close()


def tls_context(state_dir, addresses):
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    folder = state_dir / 'tls'
    folder.mkdir(exist_ok=True)
    certificate, private = folder / 'server.pem', folder / 'server-key.pem'
    refresh_certificate = not certificate.exists() or not private.exists()
    if not refresh_certificate:
        existing = x509.load_pem_x509_certificate(certificate.read_bytes())
        previous_addresses = {str(a) for a in existing.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.IPAddress)}
        refresh_certificate = previous_addresses != set(addresses) or existing.not_valid_after_utc <= datetime.now(timezone.utc)
    if refresh_certificate:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Giao Xu Xuan Hoa - Excel')])
        now = datetime.now(timezone.utc)
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
                .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=5))
                .not_valid_after(now+timedelta(days=365)).add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
                .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')] +
                               [x509.IPAddress(ipaddress.ip_address(a)) for a in addresses]), critical=False).sign(key, hashes.SHA256()))
        private.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        certificate.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        (folder / 'XuanHoa-Certificate.cer').write_bytes(cert.public_bytes(serialization.Encoding.DER))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certificate, private)
    return context


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--state-dir', type=Path, default=HERE.parent / '.local/bridge')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--lan', action='store_true')
    parser.add_argument('--public-origin',default='',help='Exact HTTPS origin served by a trusted loopback reverse proxy')
    parser.add_argument('--web-root', type=Path, default=WEB)
    parser.add_argument('--grade-engine',choices=('portable','native'),default='portable')
    args = parser.parse_args()
    if args.public_origin:
        origin=urlparse(args.public_origin)
        if origin.scheme!='https' or not origin.hostname or origin.path or origin.query or origin.fragment or origin.username:
            raise ValueError('--public-origin cần HTTPS và tên miền, không có đường dẫn.')
        if args.lan: raise ValueError('Public proxy chạy qua loopback; không dùng cùng --lan.')
    args.state_dir=args.state_dir.resolve()
    recover_management(args.state_dir,TRUSTED_VBA)
    registry=args.state_dir/'school-years.json'
    working_root,working_state=args.root,args.state_dir
    if registry.exists():
        years=json.loads(registry.read_text(encoding='utf-8'))
        active=next(y for y in years['years'] if y['id']==years['active'])
        working_root,working_state=Path(active['root']),Path(active['state'])
    mutex=None
    if os.name=='nt':
        import win32event, win32api
        mutex = win32event.CreateMutex(None, False, 'Local\\XuanHoaExcel-' + hashlib.sha256(str(args.root.resolve()).casefold().encode()).hexdigest())
        if win32api.GetLastError() == 183:
            raise RuntimeError('Dịch vụ điểm danh đã chạy cho thư mục này. Dừng phiên trước khi mở phiên mới.')
    store = Store(working_root, working_state,grade_mode=args.grade_engine)
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='Excel-STA')
    addresses = sorted({'127.0.0.1', *socket.gethostbyname_ex(socket.gethostname())[2]})
    valid_hosts = {'localhost', *addresses}
    accounts = Accounts(args.state_dir, store.catalog)
    accounts.bootstrap_accounts()
    accounts.recover_assignments(store.catalog)
    management = Management(store,accounts)
    gateway = Gateway(store, accounts)
    control_token = secrets.token_urlsafe(32)
    (args.state_dir / 'control-token.txt').write_text(control_token)
    stopping = False
    backup_stop = threading.Event()

    def backup_loop():
        # The same STA queue serializes snapshots with every Excel/SQLite write.
        while not backup_stop.wait(60):
            if not stopping:
                executor.submit(store.scheduled_backup).result()

    threading.Thread(target=backup_loop, daemon=True, name='Backup-timer').start()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *_):
            pass

        def send(self, status, data, content_type='application/json; charset=utf-8', extra=None):
            if isinstance(data, (dict, list)):
                data = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'same-origin')
            if extra:
                for name, value in extra.items():
                    self.send_header(name, value)
            self.end_headers()
            self.wfile.write(data)

        def safe_origin(self):
            host = self.headers.get('Host', '')
            if args.public_origin and host==urlparse(args.public_origin).netloc:
                return self.headers.get('Origin') in (None,args.public_origin)
            parsed = urlparse('http://' + host)
            try: port=parsed.port
            except ValueError: return False
            if parsed.hostname not in valid_hosts or port != args.port:
                return False
            origin = self.headers.get('Origin')
            expected = ('https://' if args.lan else 'http://') + host
            return origin is None or origin == expected

        def token(self):
            cookies = SimpleCookie()
            try:
                cookies.load(self.headers.get('Cookie',''))
                return cookies['xuanhoa_session'].value if 'xuanhoa_session' in cookies else ''
            except Exception:
                return ''

        def cookie(self, token):
            secure = '; Secure' if args.lan or (args.public_origin and self.headers.get('Host')==urlparse(args.public_origin).netloc) else ''
            return {'Set-Cookie': f'xuanhoa_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={43200 if token else 0}{secure}'}

        def auth_result(self, result):
            result = dict(result)
            token = result.pop('token')
            return self.send(200,result,extra=self.cookie(token))

        def login_address(self):
            # Only a configured public host on the loopback listener may supply Cloudflare's client IP.
            if args.public_origin and self.client_address[0]=='127.0.0.1' and self.headers.get('Host')==urlparse(args.public_origin).netloc:
                try: return str(ipaddress.ip_address(self.headers.get('CF-Connecting-IP','')))
                except ValueError: pass
            return self.client_address[0]

        def do_GET(self):
            if not self.safe_origin():
                return self.send(403, {'error':'Nguồn truy cập không hợp lệ.'})
            parsed = urlparse(self.path)
            if parsed.path == '/certificate.cer' and args.lan:
                return self.send(200,(args.state_dir/'tls/XuanHoa-Certificate.cer').read_bytes(),'application/pkix-cert')
            if parsed.path.startswith('/api/'):
                try:
                    result = executor.submit(gateway.get,parsed.path,parse_qs(parsed.query),self.token()).result()
                    if isinstance(result,tuple):
                        data,filename,mime = result
                        from urllib.parse import quote
                        extra = {'Content-Disposition': "attachment; filename*=UTF-8''"+quote(filename)} if filename else None
                        return self.send(200,data,mime,extra)
                    return self.send(200,result)
                except AccessError as error:
                    return self.send(error.status,{'error':str(error),'code':error.code})
                except (ValueError,KeyError,TypeError) as error:
                    return self.send(409,{'error':str(error)})
                except Exception:
                    logging.exception('Read operation failed')
                    return self.send(503,{'error':'Dịch vụ chưa sẵn sàng. Kiểm tra file dữ liệu rồi thử lại.'})
            relative = unquote(parsed.path).lstrip('/') or 'index.html'
            target = (args.web_root / relative).resolve()
            if not target.is_relative_to(args.web_root.resolve()) or not target.is_file():
                return self.send(404, b'Not found', 'text/plain')
            return self.send(200, target.read_bytes(), mimetypes.guess_type(target)[0] or 'application/octet-stream')

        def do_POST(self):
            nonlocal stopping
            if not self.safe_origin() or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.send(403, {'error': 'Nguồn hoặc định dạng yêu cầu không hợp lệ.'})
            try:
                length = int(self.headers.get('Content-Length', 0))
                if not 0 < length <= 4_000_000:
                    raise ValueError('Yêu cầu không hợp lệ.')
                values = json.loads(self.rfile.read(length))
                if not isinstance(values, dict):
                    raise ValueError('Yêu cầu không hợp lệ.')
                csrf = self.headers.get('X-CSRF-Token','')
                if self.path == '/api/shutdown':
                    local_control = self.client_address[0]=='127.0.0.1' and secrets.compare_digest(self.headers.get('X-Bridge-Control',''),control_token)
                    if not local_control:
                        def authorize_shutdown():
                            gateway.require_admin(accounts.principal(self.token(),csrf))
                        executor.submit(authorize_shutdown).result()
                    stopping = True
                    self.send(200, {'stopping':True})
                    threading.Thread(target=server.shutdown,daemon=True).start()
                    return
                if stopping:
                    return self.send(503,{'error':'Dịch vụ đang dừng. Chưa nhận thêm lượt ghi.'})
                if self.path == '/api/auth/login':
                    return self.auth_result(executor.submit(accounts.login,values,self.login_address()).result())
                if self.path == '/api/auth/password':
                    return self.auth_result(executor.submit(accounts.change_password,self.token(),csrf,values).result())
                if self.path == '/api/auth/logout':
                    result = executor.submit(accounts.logout,self.token(),csrf).result()
                    return self.send(200,result,extra=self.cookie(''))
                result = executor.submit(gateway.post,self.path,values,self.token(),csrf).result()
                return self.send(200,result)
            except AccessError as error:
                return self.send(error.status,{'error':str(error),'code':error.code})
            except (ValueError, KeyError, TypeError) as error:
                return self.send(409, {'error': str(error)})
            except Exception:
                logging.exception('Excel operation failed')
                return self.send(503, {'error': 'Chưa ghi được Excel. Kiểm tra Excel, file đang mở hoặc quyền ghi rồi quét lại. Chưa báo thành công.'})

    server = ThreadingHTTPServer(('0.0.0.0' if args.lan else '127.0.0.1', args.port), Handler)
    if args.lan:
        server.socket = tls_context(args.state_dir, addresses).wrap_socket(server.socket, server_side=True)
    print(f'READY {"https" if args.lan else "http"}://localhost:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        backup_stop.set()
        server.server_close()
        executor.submit(store.shutdown).result()
        executor.shutdown()
        if mutex is not None:win32api.CloseHandle(mutex)


if __name__ == '__main__':
    main()
