"""Authenticated parish workflows backed by durable PostgreSQL transactions.

No native bridge import, local database, file lock, Excel process, or user directory.
"""
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timezone
from sqlalchemy import select, insert, update, delete, func
from . import models as m
from .security import CloudError, password_hash, password_matches, token_hash, validate_password, audit_details
from .workflows import Workflow, OPERATIONS
from .workbooks import Workbook
from .office import Office
from .persistence import document, save_document, fingerprint
from .account_naming import choose_username

SESSION_SECONDS = 43200
IDLE_SECONDS = 3600
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
        self._dummy = None

    def audit(self, db, actor, action, details):
        db.execute(insert(m.audit).values(id=secrets.token_hex(16), user_id=actor,
                   action=action, stamp=stamp(), details=audit_details(details)))

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
                'role': user['role'], 'active': user['active'], 'mustChangePassword': user['must_change'], 'classIds': ids}

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
        return {'token': token, 'csrfToken': csrf, 'user': self.public_user(db, user)}

    def login(self, values, address):
        username = str(values.get('username') or '').strip().casefold()
        password = values.get('password')
        if not username or len(username) > 100 or not isinstance(password, str) or not 1 <= len(password) <= 128:
            raise CloudError('Tên đăng nhập hoặc mật khẩu không đúng.', 401, 'invalid_credentials')
        # Rate limits live in PostgreSQL, shared by separate Vercel instances.
        keys = [hmac.new(self.secret.encode(), value.encode(), hashlib.sha256).hexdigest()
                for value in ('address:'+address, 'username:'+username)]
        error = None
        with self.database.transaction() as db:
            now = time.time()
            for key in keys:
                limit = one(db, select(m.limits).where(m.limits.c.key == key))
                if limit and now-limit['window_start'] < 900 and limit['attempts'] >= 8:
                    raise CloudError('Đã thử quá nhiều lần. Thử lại sau 15 phút.', 429, 'rate_limited')
                if not limit or now-limit['window_start'] >= 900:
                    db.execute(delete(m.limits).where(m.limits.c.key == key))
                    db.execute(insert(m.limits).values(key=key, attempts=0, window_start=now))
            user = one(db, select(m.users).where(m.users.c.username == username))
            if self._dummy is None:
                self._dummy = password_hash(secrets.token_urlsafe(24))
            valid = password_matches(password, user['password_hash'] if user else self._dummy)
            if not valid or not user or not user['active'] or user['deleted_at']:
                for key in keys:
                    db.execute(update(m.limits).where(m.limits.c.key == key).values(attempts=m.limits.c.attempts+1))
                error = CloudError('Tên đăng nhập hoặc mật khẩu không đúng.', 401, 'invalid_credentials')
            else:
                db.execute(delete(m.limits).where(m.limits.c.key.in_(keys)))
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
        return [{'id':row['id'],'username':row['username'],'displayName':row['display_name'],'role':row['role'],
                 'active':row['active'],'mustChangePassword':row['must_change'],'revision':row['revision'],
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
            people.append({**row['payload'], 'id': row['code'], 'classId': row['class_id'], 'revision': row['revision']})
        for row in db.execute(select(m.classes).where(m.classes.c.year_id == year['id'], m.classes.c.id.in_(ids))).mappings():
            groups.append({**row['payload'], 'id': row['id'], 'name': row['name'], 'archived': row['archived'],
                           'count': sum(s['classId'] == row['id'] for s in people)})
        class_names = {row['id']: row['name'] for row in groups}
        for person in people:
            person['className'] = class_names[person['classId']]
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
        return {'year': year['label'], 'classes': groups, 'students': people, 'marks': marks,
                'user': principal, 'yearId': year['id'], 'accounts': self.account_list(db) if user['role'] == 'Admin' else [],
                'isManager': user['role'] == 'Admin', 'connected': True, 'mode': 'cloud', 'gradeMode': 'portable',
                **operational, 'downloads': [],
                'cloudReadiness': self.readiness(db)}

    def get(self, action, token, query=None):
        # Computing/exporting a workbook may take longer than attendance. Use a
        # consistent read snapshot without holding the shared mutation lock.
        readonly = action not in ('bootstrap','auth/me')
        with self.database.transaction(readonly=readonly) as db:
            user, session = self.principal(db, token, allow_change=action == 'auth/me',touch=not readonly)
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
                book = Workbook(db, self.year(db)['id'], cid)
                if action == 'grades':
                    try:
                        semester = int(query.get('semester', '1'))
                    except (TypeError, ValueError):
                        raise CloudError('Học kỳ không hợp lệ.')
                    return book.response(semester)
                return book.export()
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

    def post(self, action, token, csrf, values):
        if action == 'auth/password':
            return self.change_password(token, csrf, values)
        with self.database.transaction() as db:
            user, _ = self.principal(db, token, csrf, allow_change=action == 'auth/logout')
            if action == 'auth/logout':
                db.execute(delete(m.sessions).where(m.sessions.c.token_hash == token_hash(token)))
                return {'loggedOut': True}
            if not self.foundation_preview and not self.readiness(db)['ready']:
                raise CloudError('Bản cloud chưa sẵn sàng để ghi nghiệp vụ. Chưa lưu thay đổi.', 503, 'cloud_migration_incomplete')
            if action.startswith('accounts/'):
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
        if 'feastDay' in values:
            import re
            feast = values['feastDay']
            if not isinstance(feast, str):
                raise CloudError('Ngày bổn mạng không hợp lệ.')
            feast = feast.strip()
            if feast:
                if re.fullmatch(r'\d{2}/\d{2}', feast):
                    feast = feast[3:] + '-' + feast[:2]
                if not re.fullmatch(r'\d{2}-\d{2}', feast):
                    raise CloudError('Nhập ngày bổn mạng theo dạng dd/mm.')
                try:
                    datetime.strptime('2000-' + feast, '%Y-%m-%d')
                except ValueError:
                    raise CloudError('Ngày bổn mạng không tồn tại.')
                if values.get('feastConfirmed') is not True:
                    raise CloudError('Xác nhận ngày bổn mạng đã được kiểm tra trước khi lưu.')
            profile.update(feastDay=feast, feastConfirmed=bool(feast),
                           feastConfirmedBy=user['id'] if feast else '', feastConfirmedAt=stamp() if feast else '')
        if len(profile.get('fullName', '')) < 2 or profile.get('gender', '') not in ('', 'Nam', 'Nữ'):
            raise CloudError('Kiểm tra họ tên và giới tính.')
        profile['name'] = ' '.join(filter(None, (profile.get('saintName'), profile['fullName'])))
        db.execute(update(m.students).where(m.students.c.year_id == year['id'], m.students.c.code == code).values(
            payload=profile, revision=row['revision']+1))
        self.audit(db, user['id'], 'student-profile', {'code': code, 'before': before, 'after': profile})
        return {'saved': True, 'student': {**profile, 'id': code, 'revision': row['revision']+1}}

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
