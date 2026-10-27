"""Authenticated parish workflows backed by durable PostgreSQL transactions.

No native bridge import, local database, file lock, Excel process, or user directory.
"""
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timezone
from sqlalchemy import select, insert, update, delete, func, case
from . import models as m
from .security import CloudError, password_hash, password_matches, token_hash, validate_password, audit_details, DUMMY_PASSWORD_HASH
from .workflows import Workflow, OPERATIONS
from .workbooks import Workbook
from .office import Office
from .persistence import document, save_document, fingerprint
from .account_naming import choose_username
from . import privacy

SESSION_SECONDS = 28800
IDLE_SECONDS = 1800
SLOTS = ('glv1', 'glv2', 'glv3', 'souer')
COMPLETED = ('accounts', 'class-directory', 'student-profile', 'teacher-assignments',
             'attendance-and-makeup', 'grades-and-workbook-export', 'class-and-import-management',
             'school-year-transition', 'backup-and-restore', 'care-and-notification-workflows')


def stamp():
    return datetime.now(timezone.utc).isoformat()


def one(connection, statement):
    row = connection.execute(statement).mappings().first()
    return dict(row) if row else None


class Service:
    def __init__(self, database, secret, *, foundation_preview=False):
        self.database, self.secret = database, secret
        self.foundation_preview = foundation_preview

    def audit(self, db, actor, action, details):
        db.execute(insert(m.audit).values(id=secrets.token_hex(16), user_id=actor,
                   action=action, stamp=stamp(), details=audit_details(details)))

    def preflight(self, action, token, address, *, csrf=None):
        with self.database.transaction(readonly=True) as db:
            user, _ = self.principal(db, token, csrf, allow_change=action in ('auth/me', 'auth/logout', 'auth/password'), touch=False)
        from .traffic import limit
        limit(self.database, self.secret, action, user['id'], token_hash(token), address)
        return user

    def denied(self, user, action, error, target=None):
        # Separate transaction: a rejected business transaction must not erase it.
        if error.status not in (403, 429):
            return
        with self.database.transaction(serialized=False) as db:
            self.audit(db, user['id'] if user else None, 'access-denied',
                       {'operation': action[:100], 'result': error.code,
                        'targetRef': hmac.new(self.secret.encode(), str(target or '').encode(), hashlib.sha256).hexdigest()})

    def require_recent_auth(self, db, token):
        expires = db.execute(select(m.settings.c.value).where(m.settings.c.key == 'reauth:'+token_hash(token))).scalar_one_or_none()
        if not isinstance(expires, (int, float)) or expires <= time.time():
            raise CloudError('Nhập lại mật khẩu trước khi tải hồ sơ riêng.', 403, 'reauth_required')

    def student_row(self, db, user, code):
        row = one(db, select(m.students).where(m.students.c.year_id == self.year(db)['id'], m.students.c.code == str(code or '').strip().upper()))
        if not row or row['class_id'] not in self.public_user(db, user)['classIds']:
            raise CloudError('Không có quyền truy cập hồ sơ này.', 403, 'forbidden')
        return row

    def readiness(self, db):
        years = list(db.execute(select(m.years.c.id).where(m.years.c.active.is_(True))).scalars())
        pending = []
        if len(years) != 1:
            pending.append('data-import')
        else:
            ids = set(db.execute(select(m.classes.c.id).where(m.classes.c.year_id == years[0])).scalars())
            books = {r['id']:r['payload'] for r in db.execute(select(m.records.c.id, m.records.c.payload).where(
                m.records.c.year_id == years[0], m.records.c.kind == 'source-workbook')).mappings()}
            digests = {v.get('sha256') or v.get('blobDigest') for k,v in books.items() if k in ids}
            available = set(db.execute(select(m.blobs.c.digest).where(m.blobs.c.digest.in_(digests - {None}))).scalars())
            if not ids or not ids.issubset(books) or None in digests or not digests.issubset(available):
                pending.append('workbook-import')
        return {'ready':not pending, 'completed':list(COMPLETED), 'pending':pending, 'database':db.dialect.name}

    def year(self, db):
        year = one(db, select(m.years).where(m.years.c.active.is_(True)))
        if not year:
            raise CloudError('Chưa nhập dữ liệu năm học vào cloud.', 503, 'data_not_imported')
        return year

    def public_user(self, db, user):
        year = self.year(db)
        if user['role'] == 'Admin':
            ids = list(db.execute(select(m.classes.c.id).where(m.classes.c.year_id == year['id'])).scalars())
        else:
            ids = list(db.execute(select(m.assignments.c.class_id).where(
                m.assignments.c.year_id == year['id'], m.assignments.c.user_id == user['id']).distinct()).scalars())
        return {'id': user['id'], 'username': user['username'], 'displayName': user['display_name'],
                'role': user['role'], 'active': user['active'], 'mustChangePassword': user['must_change'], 'classIds': ids,
                'proxyClassIds': ids}

    def principal(self, db, token, csrf=None, *, allow_change=False, touch=True):
        session = one(db, select(m.sessions).where(m.sessions.c.token_hash == token_hash(token)))
        now = time.time()
        if not session or session['expires'] <= now or session['last_seen'] + IDLE_SECONDS <= now:
            raise CloudError('Phiên đăng nhập đã hết hạn.', 401, 'session_expired')
        user = one(db, select(m.users).where(m.users.c.id == session['user_id']))
        if not user or not user['active'] or user['deleted_at']:
            raise CloudError('Phiên đăng nhập không còn hiệu lực.', 401, 'session_expired')
        if csrf is not None and (not csrf or not hmac.compare_digest(csrf, session['csrf'])):
            raise CloudError('Mã bảo vệ yêu cầu không hợp lệ.', 403, 'invalid_csrf')
        if user['must_change'] and not allow_change:
            raise CloudError('Cần đổi mật khẩu tạm trước khi sử dụng.', 403, 'password_change_required')
        if touch and now - session['last_seen'] >= 60:
            db.execute(update(m.sessions).where(m.sessions.c.token_hash == session['token_hash']).values(last_seen=now))
        return user, session

    def issue(self, db, user):
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        now = time.time()
        db.execute(delete(m.sessions).where(m.sessions.c.expires <= now))
        db.execute(insert(m.sessions).values(token_hash=token_hash(token), user_id=user['id'], csrf=csrf,
                   expires=now+SESSION_SECONDS, last_seen=now))
        db.execute(delete(m.settings).where(m.settings.c.key.like('reauth:%'),
                   ~m.settings.c.key.in_(select('reauth:'+m.sessions.c.token_hash))))
        db.execute(insert(m.settings).values(key='reauth:'+token_hash(token), value=now+300))
        return {'token': token, 'csrfToken': csrf, 'user': self.public_user(db, user)}

    def login(self, values, address):
        username = str(values.get('username') or '').strip().casefold()
        password = values.get('password')
        if not username or len(username) > 100 or not isinstance(password, str) or not 1 <= len(password) <= 128:
            raise CloudError('Tên đăng nhập hoặc mật khẩu không đúng.', 401, 'invalid_credentials')
        # Reserve attempts atomically before expensive hashing. Pending attempts
        # count against the budget too: parallel failures cannot bypass it.
        keys = [hmac.new(self.secret.encode(), value.encode(), hashlib.sha256).hexdigest()
                for value in ('address:'+address, 'username:'+username)]
        with self.database.transaction(serialized=False) as db:
            now = time.time()
            if db.dialect.name == 'postgresql':
                from sqlalchemy.dialects.postgresql import insert as upsert
            else:
                from sqlalchemy.dialects.sqlite import insert as upsert
            table = m.limits
            expired = table.c.window_start <= now-900
            statement = upsert(table).values([
                {'key': key, 'attempts': 1, 'window_start': now} for key in sorted(keys)])
            reservations = db.execute(statement.on_conflict_do_update(index_elements=[table.c.key],
                set_={'attempts': case((expired, 1), else_=table.c.attempts+1),
                      'window_start': case((expired, now), else_=table.c.window_start)})
                .returning(table.c.key, table.c.attempts, table.c.window_start)).mappings().all()
            caps = dict(zip(keys, (80, 8)))
            blocked = [row for row in reservations if row['attempts'] > caps[row['key']]]
            if blocked:
                error = CloudError('Đã thử quá nhiều lần. Thử lại sau 15 phút.', 429, 'rate_limited')
                error.retry_after = max(1, int(max(row['window_start']+900-now for row in blocked))+1)
                raise error  # Roll back both reservations together.
            candidate = one(db, select(m.users).where(m.users.c.username == username))

        # No connection or business lock is held during scrypt.
        valid = password_matches(password, candidate['password_hash'] if candidate else DUMMY_PASSWORD_HASH)
        error = None
        with self.database.transaction() as db:
            user = one(db, select(m.users).where(m.users.c.id == candidate['id']).with_for_update()) if candidate else None
            credential_fields = ('id', 'username', 'password_hash', 'revision', 'active', 'deleted_at', 'role', 'must_change')
            unchanged = user and all(user[key] == candidate[key] for key in credential_fields)
            if not valid or not unchanged or not user['active'] or user['deleted_at']:
                error = CloudError('Tên đăng nhập hoặc mật khẩu không đúng.', 401, 'invalid_credentials')
                self.audit(db, None, 'login-failed', {'sourceRef': keys[0], 'accountRef': keys[1]})
            else:
                # Refund only this successful attempt, never another in-flight
                # or failed attempt, and never a replacement time window.
                for row in sorted(reservations, key=lambda row: row['key']):
                    db.execute(update(m.limits).where(m.limits.c.key == row['key'],
                        m.limits.c.window_start == row['window_start'], m.limits.c.attempts > 0)
                        .values(attempts=m.limits.c.attempts-1))
                result = self.issue(db, user)
                self.audit(db, user['id'], 'login', {})
        # Failed attempts must commit before returning the error.
        if error:
            raise error
        return result

    def change_password(self, token, csrf, values):
        with self.database.transaction() as db:
            user, _ = self.principal(db, token, csrf, allow_change=True)
            new = validate_password(values.get('newPassword'))
            if not user['must_change'] and not password_matches(values.get('currentPassword'), user['password_hash']):
                raise CloudError('Mật khẩu hiện tại chưa đúng.', 403, 'incorrect_password')
            if password_matches(new, user['password_hash']):
                raise CloudError('Mật khẩu mới cần khác mật khẩu đang dùng.')
            encoded = password_hash(new)
            db.execute(update(m.users).where(m.users.c.id == user['id']).values(password_hash=encoded, must_change=False,
                       revision=m.users.c.revision+1))
            db.execute(delete(m.sessions).where(m.sessions.c.user_id == user['id']))
            user.update(password_hash=encoded, must_change=False)
            self.audit(db, user['id'], 'password-changed', {})
            return self.issue(db, user)

    def admin(self, user):
        if user['role'] != 'Admin':
            raise CloudError('Chức năng này dành cho Admin.', 403, 'forbidden')

    def account_list(self, db):
        year = self.year(db)
        all_ids = list(db.execute(select(m.classes.c.id).where(m.classes.c.year_id == year['id'])).scalars())
        assigned, slots = {}, {}
        for row in db.execute(select(m.assignments).where(m.assignments.c.year_id == year['id'])).mappings():
            assigned.setdefault(row['user_id'], set()).add(row['class_id'])
            slots.setdefault(row['user_id'], []).append({'class_id':row['class_id'],'slot':row['slot']})
        def access_for(row):
            ids = sorted(all_ids if row['role'] == 'Admin' else assigned.get(row['id'], ()))
            return {key: ids for key in privacy.CAPABILITIES}
        return [{'id':row['id'],'username':row['username'],'displayName':row['display_name'],'role':row['role'],
                 'active':row['active'],'mustChangePassword':row['must_change'],'revision':row['revision'],
                 'access': access_for(row),
                 'classIds':all_ids if row['role']=='Admin' else sorted(assigned.get(row['id'],())),
                 'assignments':sorted(slots.get(row['id'],[]),key=lambda a:(a['class_id'],a['slot'])),
                 'assignmentRevision':fingerprint(sorted(slots.get(row['id'],[]),key=lambda a:(a['class_id'],a['slot'])))}
                for row in db.execute(select(m.users).where(m.users.c.deleted_at.is_(None)).order_by(m.users.c.username)).mappings()]

    def bootstrap(self, db, user):
        year = self.year(db)
        principal = self.public_user(db, user)
        ids = principal['classIds']
        people, groups = [], []
        for row in db.execute(select(m.students).where(m.students.c.year_id == year['id'], m.students.c.class_id.in_(ids))).mappings():
            people.append(privacy.directory({**row['payload'], 'id': row['code'], 'classId': row['class_id']}))
        for row in db.execute(select(m.classes).where(m.classes.c.year_id == year['id'], m.classes.c.id.in_(ids))).mappings():
            groups.append({**row['payload'], 'id': row['id'], 'name': row['name'], 'archived': row['archived'],
                           'count': sum(s['classId'] == row['id'] for s in people)})
        class_names = {row['id']: row['name'] for row in groups}
        codes = {s['id'] for s in people}
        marks = {f"{r['day']}|{r['activity']}|{r['code']}": {'status': r['status'], 'timestamp': r['stamp'], 'source': r['source']}
                 for r in db.execute(select(m.marks).where(m.marks.c.year_id == year['id'], m.marks.c.code.in_(codes))).mappings()}
        workflow = Workflow(db, year['id'])
        try:
            from .workflows import LOCAL_TZ
            today = datetime.now(LOCAL_TZ).date().isoformat()
            scopes = ['all'] if user['role'] == 'Admin' else [g['name'] for g in groups if not g['archived']]
            for scope in scopes:
                workflow.create_session({'date':today, 'activity':'mass', 'scope':scope})
            workflow.flush()
            operational = workflow.public(principal)
        finally:
            workflow.shutdown()
        attendance_rules = {r['code']: {'enrolledFrom': r['payload'].get('enrolledFrom')}
            for r in db.execute(select(m.students).where(m.students.c.year_id == year['id'], m.students.c.class_id.in_(ids))).mappings()}
        return {'privacyVersion': 2, 'access': privacy.grants(db, year['id'], principal),
                'attendanceRules': attendance_rules,
                'year': year['label'], 'classes': groups, 'students': people, 'marks': marks,
                'user': principal, 'yearId': year['id'], 'accounts': self.account_list(db) if user['role'] == 'Admin' else [],
                'isManager': user['role'] == 'Admin', 'connected': True, 'mode': 'cloud', 'gradeMode': 'portable',
                **operational, 'downloads': [],
                'cloudReadiness': self.readiness(db)}

    def get(self, action, token, query=None, address='local'):
        user = None
        try:
            user = self.preflight(action, token, address)
            result = self._get(action, token, query)
            from .persistence import Download
            if action in ('export', 'grade-export', 'grade-pending-export', 'year-file', 'year-export',
                          'export-manifest', 'reports/attendance-export', 'admin/audit-export'):
                with self.database.transaction(serialized=False) as log:
                    self.audit(log, user['id'], 'private-export' if action != 'reports/attendance-export' else 'aggregate-export',
                        {'operation': action, 'classId': (query or {}).get('classId'),
                         'bytes': len(result.content) if isinstance(result, Download) else 0})
            return result if action in ('student-detail', 'admin/staff') else privacy.public_result(result)
        except CloudError as error:
            self.denied(user, action, error, (query or {}).get('code'))
            raise

    def _get(self, action, token, query=None):
        # Computing/exporting a workbook may take longer than attendance. Use a
        # consistent read snapshot without holding the shared mutation lock.
        readonly = action not in ('bootstrap','auth/me')
        with self.database.transaction(readonly=readonly) as db:
            user, session = self.principal(db, token, allow_change=action == 'auth/me',touch=False)
            query = query or {}
            if action == 'students':
                principal = self.public_user(db, user)
                ids = principal['classIds']
                cid = query.get('classId')
                if cid and cid not in ids:
                    raise CloudError('Lớp ngoài phạm vi được phân công.', 403, 'forbidden')
                try:
                    size = int(query.get('limit', 50))
                    if not 1 <= size <= 100:
                        raise ValueError()
                except (ValueError, TypeError):
                    raise CloudError('Số lượng mỗi trang phải từ 1 đến 100.', 400)
                statement = select(m.students).where(m.students.c.year_id == self.year(db)['id'],
                    m.students.c.class_id.in_([cid] if cid else ids))
                if query.get('cursor'):
                    statement = statement.where(m.students.c.code > query['cursor'])
                rows = list(db.execute(statement.order_by(m.students.c.code).limit(size+1)).mappings())
                return {'items': [privacy.directory({**r['payload'], 'id': r['code'], 'classId': r['class_id']}) for r in rows[:size]],
                    'nextCursor': rows[size-1]['code'] if len(rows) > size else None}
            if action == 'student-detail':
                row = self.student_row(db, user, query.get('code'))
                return {'student': privacy.detail({**row['payload'], 'id': row['code'], 'classId': row['class_id'],
                    'revision': row['revision']}), 'access': privacy.grants(db, self.year(db)['id'], self.public_user(db, user))}
            if action == 'reports/attendance':
                from .insights import attendance_report
                return attendance_report(self, db, user, query)
            if action == 'reports/attendance-export':
                from .insights import report_csv, attendance_report
                return report_csv(attendance_report(self, db, user, query))
            if action in ('snapshot-export', 'snapshot-part'):
                raise CloudError('Bản sao đầy đủ được xuất mã hóa bằng công cụ backup riêng.', 410, 'encrypted_backup_required')
            if action == 'auth/me':
                return {'user': self.public_user(db, user), 'csrfToken': session['csrf']}
            if action == 'bootstrap':
                if not self.foundation_preview and not self.readiness(db)['ready']:
                    raise CloudError('Bản cloud đang chuyển dữ liệu và chức năng; chưa mở cho GLV sử dụng.', 503, 'cloud_migration_incomplete')
                return self.bootstrap(db, user)
            if action == 'cloud/readiness':
                self.admin(user)
                return self.readiness(db)
            if action == 'accounts':
                self.admin(user)
                return {'accounts': self.account_list(db)}
            if action in ('grades', 'grade-export', 'grade-pending-export', 'export'):
                query = query or {}
                cid = query.get('classId')
                ids = self.public_user(db, user)['classIds']
                if action == 'export' and cid == 'all':
                    self.admin(user)
                    raise CloudError('Tải toàn bộ sổ trên cloud cần tải từng lớp rồi ghép ZIP.', 409, 'download_manifest_required')
                if cid not in ids:
                    raise CloudError('Lớp ngoài phạm vi được phân công.', 403, 'forbidden')
                if action != 'grades':
                    privacy.require(db, self.year(db)['id'], self.public_user(db, user), 'privateExport', cid)
                    self.require_recent_auth(db, token)
                book = Workbook(db, self.year(db)['id'], cid)
                if action == 'grades':
                    try:
                        semester = int(query.get('semester', '1'))
                    except (TypeError, ValueError):
                        raise CloudError('Học kỳ không hợp lệ.')
                    return book.response(semester)
                result = book.export()
                return result
            if action == 'qr':
                import qrcode
                from qrcode.image.svg import SvgPathImage
                from .persistence import Download
                code = (query or {}).get('code','')
                person = one(db,select(m.students).where(m.students.c.year_id == self.year(db)['id'],m.students.c.code == code))
                if not person or person['class_id'] not in self.public_user(db,user)['classIds']:
                    raise CloudError('Thiếu nhi ngoài lớp được phân công.',403,'forbidden')
                return Download(qrcode.make(code,image_factory=SvgPathImage,border=4).to_string(),'QR-'+code+'.svg','image/svg+xml')
            if action in Office.READ_ACTIONS:
                if action in ('year-export', 'year-file', 'export-manifest'):
                    self.admin(user)
                    self.require_recent_auth(db, token)
                office = Office(self,db,user)
                try:
                    return office.read(action,query or {})
                except ValueError as error:
                    raise CloudError(str(error)) from error
                finally:
                    office.shutdown()
            if action == 'request-history':
                workflow = Workflow(db, self.year(db)['id'])
                try:
                    identifier = (query or {}).get('id', '')
                    code = workflow.request(identifier)['code']
                    person = workflow.catalog.students.get(code)
                    if not person or person['classId'] not in self.public_user(db, user)['classIds']:
                        raise CloudError('Đơn ngoài phạm vi lớp được phân công.', 403, 'forbidden')
                    return workflow.request_history(identifier)
                except ValueError as error:
                    raise CloudError('Không tìm thấy đơn.',404,'not_found') from error
                finally:
                    workflow.shutdown()
            raise CloudError('Chức năng này đang được chuyển sang cloud; chưa thể dùng trên bản thử này.', 503, 'cloud_workflow_pending')

    def post(self, action, token, csrf, values, address='local'):
        user = None
        try:
            user = self.preflight(action, token, address, csrf=csrf)
            result = self._post(action, token, csrf, values)
            if action == 'student-contact-view':
                return result
            safe = privacy.public_result(result)
            if action == 'student-profile':
                safe['student'] = result['student']  # Already positively projected, one authorized profile.
            if action == 'admin/staff-save':
                safe['staff'] = result['staff']  # Admin-only staff API; not a student projection.
            return safe
        except CloudError as error:
            self.denied(user, action, error, values.get('code'))
            raise

    def _post(self, action, token, csrf, values):
        if action == 'auth/password':
            return self.change_password(token, csrf, values)
        with self.database.transaction() as db:
            user, _ = self.principal(db, token, csrf, allow_change=action == 'auth/logout')
            if action == 'auth/logout':
                db.execute(delete(m.sessions).where(m.sessions.c.token_hash == token_hash(token)))
                return {'loggedOut': True}
            if action == 'auth/reauth':
                if not password_matches(values.get('password'), user['password_hash']):
                    raise CloudError('Mật khẩu chưa đúng.', 403, 'incorrect_password')
                key = 'reauth:'+token_hash(token)
                db.execute(delete(m.settings).where(m.settings.c.key == key))
                db.execute(insert(m.settings).values(key=key, value=time.time()+300))
                return {'verified': True}
            if action == 'student-contact-view':
                row = self.student_row(db, user, values.get('code'))
                privacy.require(db, row['year_id'], self.public_user(db, user), 'contactRead', row['class_id'])
                self.audit(db, user['id'], 'contact-viewed', {'code': row['code'], 'classId': row['class_id'],
                    'yearId': row['year_id'], 'sessionRef': token_hash(token)[:16]})
                day = stamp()[:10]
                distinct = db.execute(select(func.count(func.distinct(m.audit.c.details['code'].as_string()))).where(
                    m.audit.c.user_id == user['id'], m.audit.c.action == 'contact-viewed', m.audit.c.stamp >= day)).scalar_one()
                if distinct and distinct % 30 == 0:
                    self.audit(db, user['id'], 'contact-volume-review', {'distinctStudents': distinct, 'day': day})
                return {'code': row['code'], 'revision': row['revision'],
                        'contact': {key: row['payload'].get(key, '') for key in privacy.CONTACT_FIELDS}}
            if not self.foundation_preview and not self.readiness(db)['ready']:
                raise CloudError('Bản cloud chưa sẵn sàng để ghi nghiệp vụ. Chưa lưu thay đổi.', 503, 'cloud_migration_incomplete')
            if action == 'reports/groups':
                self.admin(user)
                year = self.year(db)['id']
                known = set(self.public_user(db, user)['classIds'])
                groups = values.get('groups')
                if not isinstance(groups, dict) or set(groups)-known or any(not isinstance(v, str) or len(v) > 80 for v in groups.values()):
                    raise CloudError('Phân khối chưa hợp lệ.')
                key = 'report-groups:'+year
                db.execute(delete(m.settings).where(m.settings.c.key == key))
                db.execute(insert(m.settings).values(key=key, value={k: v.strip() for k,v in groups.items()}))
                self.audit(db, user['id'], 'report-groups-changed', {'classes': len(groups)})
                result = {'saved': True}
            elif action.startswith('accounts/'):
                result = self.account_write(db, user, action, values)
            elif action == 'offline-scan':
                from .offline import replay_scan
                result = replay_scan(self, db, user, values)
            elif action == 'student-profile':
                result = self.profile_write(db, user, values)
            elif action == 'teachers':
                result = self.teacher_write(db, user, values)
            elif action == 'grades':
                cid = values.get('classId')
                if cid not in self.public_user(db, user)['classIds']:
                    raise CloudError('Lớp ngoài phạm vi được phân công.', 403, 'forbidden')
                result = Workbook(db, self.year(db)['id'], cid).save(values.get('semester'), values.get('grades'), values.get('expectedRevision'))
                self.audit(db, user['id'], 'grades', {'classId': cid, 'semester': values.get('semester'), 'changes': values.get('grades')})
            elif action in OPERATIONS:
                workflow = Workflow(db, self.year(db)['id'])
                try:
                    result = workflow.execute(self.public_user(db, user), action, values)
                    if action in ('scan', 'scan-preview'):
                        self.audit(db, user['id'], 'card-lookup', {'sessionId': values.get('sessionId'),
                            'targetRef': hmac.new(self.secret.encode(), str(values.get('code') or '').encode(), hashlib.sha256).hexdigest(),
                            'result': 'accepted'})
                finally:
                    workflow.shutdown()
                if not action.endswith('preview'):
                    self.audit(db, user['id'], action, {key: values[key] for key in
                        ('sessionId', 'code', 'id', 'date', 'status', 'reason') if key in values})
            else:
                office = Office(self,db,user)
                try:
                    result = office.dispatch(action,values)
                except (ValueError,TypeError,KeyError) as error:
                    raise CloudError(str(error) if isinstance(error,ValueError) else 'Dữ liệu yêu cầu chưa hợp lệ.') from error
                finally:
                    office.shutdown()
                if not action.endswith('preview'):
                    self.audit(db,user['id'],action,{k:v for k,v in values.items() if k not in ('fileBase64','password','newPassword','currentPassword')})
            if result.get('requireReauth'):
                return result
            if action.endswith('preview'):
                return result
            result['state'] = self.bootstrap(db, user)
            policy = db.execute(select(m.settings.c.value).where(m.settings.c.key == 'backup-policy')).scalar_one_or_none() or {'hours':24}
            from .workflows import LOCAL_TZ
            last = datetime.fromisoformat(policy['lastAt']) if policy.get('lastAt') else None
            if policy['hours'] and (last is None or (datetime.now(LOCAL_TZ)-last).total_seconds() >= policy['hours']*3600):
                office = Office(self,db,user)
                try:
                    office.snapshot('Sao lưu định kỳ khi cập nhật dữ liệu')
                finally:
                    office.shutdown()
            if action.startswith('accounts/'):
                result['accounts'] = self.account_list(db)
            return result

    def profile_write(self, db, user, values):
        if {'feastDay', 'feastConfirmed'}.intersection(values):
            raise CloudError('Lịch sinh nhật và bổn mạng chỉ dành cho hồ sơ GLV do Admin quản lý.', 403, 'forbidden')
        year = self.year(db)
        code = str(values.get('code') or '').strip().upper()
        row = one(db, select(m.students).where(m.students.c.year_id == year['id'], m.students.c.code == code))
        ids = self.public_user(db, user)['classIds']
        if not row or row['class_id'] not in ids:
            raise CloudError('Thiếu nhi không thuộc lớp được phân công.', 403, 'forbidden')
        group = one(db, select(m.classes).where(m.classes.c.id == row['class_id'], m.classes.c.year_id == year['id']))
        if group['archived']:
            raise CloudError('Lớp đã lưu trữ. Admin cần mở lại trước khi chỉnh sửa.')
        revision = values.get('expectedRevision')
        if revision is None or str(revision) != str(row['revision']):
            raise CloudError('Hồ sơ đã thay đổi hoặc chưa có phiên bản. Tải lại hồ sơ trước khi lưu.', 409, 'revision_conflict')
        before = row['payload']
        if privacy.CONTACT_FIELDS.intersection(values):
            privacy.require(db, year['id'], self.public_user(db, user), 'contactWrite', row['class_id'])
        profile = dict(before)
        for name, maximum in {'saintName': 100, 'fullName': 150, 'gender': 10, 'parents': 1000,
                             'phone': 500, 'address': 500, 'subParish': 150, 'birthDate': 20, 'baptismDate': 20}.items():
            if name not in values:
                continue
            value = values[name]
            if not isinstance(value, str) or len(value) > maximum or '\x00' in value:
                raise CloudError('Thông tin hồ sơ không hợp lệ.')
            value = value.strip()
            if name in ('birthDate', 'baptismDate') and value:
                for pattern in ('%Y-%m-%d', '%d/%m/%Y'):
                    try:
                        value = datetime.strptime(value, pattern).date().isoformat()
                        break
                    except ValueError:
                        pass
                else:
                    raise CloudError('Ngày sinh / rửa tội không hợp lệ.')
            profile[name] = value
        if len(profile.get('fullName', '')) < 2 or profile.get('gender', '') not in ('', 'Nam', 'Nữ'):
            raise CloudError('Kiểm tra họ tên và giới tính.')
        profile['name'] = ' '.join(filter(None, (profile.get('saintName'), profile['fullName'])))
        db.execute(update(m.students).where(m.students.c.year_id == year['id'], m.students.c.code == code).values(
            payload=profile, revision=row['revision']+1))
        self.audit(db, user['id'], 'student-profile', {'code': code,
            'changedFields': sorted(key for key in profile if profile.get(key) != before.get(key)),
            'revisionBefore': row['revision'], 'revisionAfter': row['revision']+1})
        return {'saved': True, 'student': privacy.detail({**profile, 'id': code, 'classId': row['class_id'], 'revision': row['revision']+1})}

    def teacher_write(self, db, user, values, *, allow_archived=False):
        self.admin(user)
        cid = values.get('classId')
        group = one(db, select(m.classes).where(m.classes.c.id == cid, m.classes.c.year_id == self.year(db)['id']))
        selections = values.get('accountAssignments')
        if not group or group['archived'] and not allow_archived or not isinstance(selections, dict) or set(selections) != set(SLOTS):
            raise CloudError('Phân công chưa hợp lệ.')
        previous = {r['slot']:r['user_id'] for r in db.execute(select(m.assignments).where(
            m.assignments.c.class_id == cid,m.assignments.c.year_id == group['year_id'])).mappings()}
        teachers = {}
        for slot in SLOTS:
            identifier = selections[slot]
            teacher = one(db, select(m.users).where(m.users.c.id == identifier)) if identifier else None
            if identifier and (not teacher or teacher['deleted_at'] or not teacher['active'] and previous.get(slot) != identifier):
                raise CloudError('Tài khoản GLV/Soeur chưa hoạt động.')
            teachers[slot] = teacher['display_name'] if teacher else ''
        affected = set(previous.values()) | {v for v in selections.values() if v}
        history = document(db,group['year_id'],'staff-assignment-history','events',{'rows':[]})
        for slot in SLOTS:
            if previous.get(slot) != selections[slot]:
                for who,event in ((previous.get(slot),'ended'),(selections[slot],'assigned')):
                    if who:
                        history['rows'].append({'user_id':who,'class_id':cid,'class_name':group['name'],
                            'slot':slot,'year':self.year(db)['label'],'event':event,'actor_id':user['id'],'stamp':stamp()})
        save_document(db,group['year_id'],'staff-assignment-history','events',history)
        db.execute(delete(m.assignments).where(m.assignments.c.class_id == cid, m.assignments.c.year_id == group['year_id']))
        for slot, identifier in selections.items():
            if identifier:
                db.execute(insert(m.assignments).values(year_id=group['year_id'], class_id=cid, slot=slot, user_id=identifier))
        payload = {**group['payload'], 'teachers': teachers}
        db.execute(update(m.classes).where(m.classes.c.id == cid, m.classes.c.year_id == group['year_id']).values(payload=payload, revision=group['revision']+1))
        # End sessions affected by a permission change; no stale class rights.
        db.execute(delete(m.sessions).where(m.sessions.c.user_id.in_(affected-{user['id']})))
        self.audit(db, user['id'], 'teacher-assignments', {'classId': cid, 'selections': selections})
        return {'saved': True}

    def account_write(self, db, actor, action, values):
        self.admin(actor)
        if action == 'accounts/create':
            name, role = values.get('displayName'), values.get('role')
            if not isinstance(name, str) or not 2 <= len(name.strip()) <= 100 or role not in ('Admin', 'GLV'):
                raise CloudError('Họ tên hoặc vai trò không hợp lệ.')
            taken = set(db.execute(select(m.users.c.username)).scalars())
            try:
                username=choose_username(name,role,taken)
            except ValueError as error:
                raise CloudError(str(error)) from error
            identifier, password = secrets.token_hex(16), secrets.token_urlsafe(12)
            db.execute(insert(m.users).values(id=identifier, username=username, display_name=name.strip(), role=role,
                       password_hash=password_hash(password), active=True, must_change=True, revision=1, created_at=stamp()))
            # A new login has a matching staff profile from the start.
            db.execute(insert(m.staff).values(id=secrets.token_hex(16),user_id=identifier,payload={
                'full_name':name.strip(),'status':'active','birth_year':None,
                **{key:'' for key in ('phone','email','birth_date','address','service_from','service_to','note')}}))
            self.set_account_assignments(db,actor,{'id':identifier,'active':True},values.get('assignments',[]))
            self.audit(db, actor['id'], 'account-created', {'id': identifier, 'role': role})
            return {'username': username, 'temporaryPassword': password, 'displayName': name.strip(), 'id': identifier}
        target = one(db, select(m.users).where(m.users.c.id == values.get('id')))
        if not target or target['deleted_at'] or target['id'] == actor['id'] and action != 'accounts/assignments':
            raise CloudError('Không thể thay đổi tài khoản này qua thao tác quản lý.')
        if action == 'accounts/access':
            raise CloudError('Quyền dữ liệu đã theo lớp được phân công của từng tài khoản; không cần cấp riêng.', 410, 'access_grants_retired')
        if action == 'accounts/assignments':
            current = next(a for a in self.account_list(db) if a['id']==target['id'])
            if values.get('assignmentRevision') != current['assignmentRevision'] or type(values.get('expectedRevision')) is not int or values['expectedRevision'] != target['revision']:
                raise CloudError('Phân công hoặc tài khoản đã thay đổi. Mở lại để xem thông tin mới.',409,'revision_conflict')
            self.set_account_assignments(db,actor,target,values.get('assignments'))
            return {'saved':True}
        if action == 'accounts/delete':
            return self.account_delete(db, actor, target, values)
        if action == 'accounts/update':
            role, active = values.get('role'), values.get('active')
            if isinstance(active, str):
                if active not in ('true', 'false'):
                    raise CloudError('Trạng thái không hợp lệ.')
                active = active == 'true'
            if role not in ('Admin', 'GLV') or not isinstance(active, bool):
                raise CloudError('Vai trò hoặc trạng thái không hợp lệ.')
            if target['role'] == 'Admin' and (role != 'Admin' or not active):
                total = db.execute(select(func.count()).select_from(m.users).where(m.users.c.role == 'Admin', m.users.c.active.is_(True))).scalar_one()
                if total <= 1:
                    raise CloudError('Cần giữ ít nhất một Admin đang hoạt động.')
            db.execute(update(m.users).where(m.users.c.id == target['id']).values(role=role, active=active, revision=target['revision']+1))
            result = {'saved': True}
        elif action == 'accounts/reset-password':
            password = secrets.token_urlsafe(12)
            db.execute(update(m.users).where(m.users.c.id == target['id']).values(password_hash=password_hash(password), must_change=True,
                       revision=target['revision']+1))
            result = {'username': target['username'], 'temporaryPassword': password, 'displayName': target['display_name']}
        else:
            raise CloudError('Không tìm thấy chức năng.', 404, 'not_found')
        db.execute(delete(m.sessions).where(m.sessions.c.user_id == target['id']))
        self.audit(db, actor['id'], action, {'id': target['id']})
        return result

    def set_account_assignments(self, db, actor, target, selections):
        if not isinstance(selections,list) or len(selections)>200:
            raise CloudError('Danh sách phân công chưa hợp lệ.')
        if selections and not target['active']:
            raise CloudError('Mở khoá tài khoản trước khi phân công vào lớp.')
        year=self.year(db)['id']
        existing=list(db.execute(select(m.assignments).where(m.assignments.c.year_id==year)).mappings())
        previous={r['class_id']:r['slot'] for r in existing if r['user_id']==target['id']}
        requested={}
        groups={r['id']:r for r in db.execute(select(m.classes).where(m.classes.c.year_id==year)).mappings()}
        for item in selections:
            if not isinstance(item,dict) or set(item)!={'classId','slot'}:
                raise CloudError('Chọn lớp và vị trí phụ trách hợp lệ.')
            cid,slot=item['classId'],item['slot']
            if not isinstance(cid,str) or not isinstance(slot,str) or cid not in groups or slot not in SLOTS or cid in requested:
                raise CloudError('Mỗi lớp chỉ chọn một vị trí cho tài khoản này.')
            if groups[cid]['archived'] and previous.get(cid)!=slot:
                raise CloudError('Không thể phân công mới vào lớp đã lưu trữ.')
            occupant=next((r['user_id'] for r in existing if r['class_id']==cid and r['slot']==slot),None)
            if occupant and occupant!=target['id']:
                raise CloudError('Vị trí đã có người phụ trách. Chọn vị trí trống hoặc chỉnh phân công của lớp.',409,'assignment_occupied')
            requested[cid]=slot
        for cid in sorted(set(previous)|set(requested)):
            if previous.get(cid)==requested.get(cid):continue
            if any(name and not any(r['class_id']==cid and r['slot']==slot for r in existing) for slot,name in groups[cid]['payload'].get('teachers',{}).items()):
                raise CloudError('Lớp có tên GLV chưa liên kết tài khoản. Mở Phân công GLV để đối chiếu trước.')
            selection={slot:next((r['user_id'] for r in existing if r['class_id']==cid and r['slot']==slot and r['user_id']!=target['id']),'') for slot in SLOTS}
            if cid in requested:selection[requested[cid]]=target['id']
            self.teacher_write(db,actor,{'classId':cid,'accountAssignments':selection},allow_archived=True)

    def account_delete(self, db, actor, target, values):
        if values.get('confirmation') != target['username']:
            raise CloudError('Nhập đúng tên đăng nhập để xác nhận xoá.', 409, 'confirmation_required')
        if type(values.get('expectedRevision')) is not int or values['expectedRevision'] != target['revision']:
            raise CloudError('Tài khoản đã thay đổi. Mở lại phần quản lý trước khi xoá.', 409, 'revision_conflict')
        reason = values.get('reason')
        if not isinstance(reason, str) or not 3 <= len(reason.strip()) <= 500:
            raise CloudError('Nhập lý do xoá từ 3 đến 500 ký tự.')
        if target['role'] == 'Admin' and target['active']:
            total = db.execute(select(func.count()).select_from(m.users).where(
                m.users.c.role == 'Admin', m.users.c.active.is_(True), m.users.c.deleted_at.is_(None))).scalar_one()
            if total <= 1:
                raise CloudError('Cần giữ ít nhất một Admin đang hoạt động.')
        office = Office(self, db, actor)
        try:
            backup = office.snapshot('Trước xoá tài khoản '+target['username'])
        finally:
            office.shutdown()
        current = self.year(db)
        # Historical years keep their assignments. End the current and prepared
        # future assignments so the deleted identity cannot be carried forward.
        years = list(db.execute(select(m.years).where(m.years.c.label >= current['label'])).mappings())
        ended = []
        deleted_at = stamp()
        for year in years:
            rows = list(db.execute(select(m.assignments).where(
                m.assignments.c.year_id == year['id'], m.assignments.c.user_id == target['id'])).mappings())
            history = document(db, year['id'], 'staff-assignment-history', 'events', {'rows':[]})
            for assignment in rows:
                group = one(db, select(m.classes).where(m.classes.c.year_id == year['id'], m.classes.c.id == assignment['class_id']))
                payload = {**group['payload'], 'teachers':{**group['payload'].get('teachers',{}), assignment['slot']:''}}
                db.execute(update(m.classes).where(m.classes.c.year_id == year['id'], m.classes.c.id == group['id']).values(
                    payload=payload, revision=m.classes.c.revision+1))
                event = {'user_id':target['id'], 'display_name':target['display_name'], 'class_id':group['id'],
                    'class_name':group['name'], 'slot':assignment['slot'], 'year':year['label'],
                    'event':'ended', 'actor_id':actor['id'], 'stamp':deleted_at, 'reason':reason.strip()}
                history['rows'].append(event)
                ended.append({'year':year['label'], 'classId':group['id'], 'slot':assignment['slot']})
            if rows:
                save_document(db, year['id'], 'staff-assignment-history', 'events', history)
                db.execute(delete(m.assignments).where(m.assignments.c.year_id == year['id'], m.assignments.c.user_id == target['id']))
        db.execute(update(m.staff).where(m.staff.c.user_id == target['id']).values(user_id=None))
        # Retain identity solely for history/audit references; erase login material.
        db.execute(update(m.users).where(m.users.c.id == target['id']).values(
            active=False, deleted_at=deleted_at, password_hash='deleted', must_change=True, revision=target['revision']+1))
        db.execute(delete(m.sessions).where(m.sessions.c.user_id == target['id']))
        self.audit(db, actor['id'], 'account-deleted', {'id':target['id'], 'username':target['username'],
            'displayName':target['display_name'], 'reason':reason.strip(), 'endedAssignments':ended, 'snapshotId':backup['id']})
        return {'deleted':True, 'id':target['id']}
