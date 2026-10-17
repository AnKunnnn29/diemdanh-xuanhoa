"""Personal accounts, opaque sessions, class assignments and security audit.

Independent of the workbook database: restoring attendance must not restore old
passwords or revive revoked permissions.
"""
import base64
import csv
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SLOTS = ('glv1', 'glv2', 'glv3', 'souer')
SESSION_SECONDS = 12 * 3600
IDLE_SECONDS = 3600


class AccessError(Exception):
    def __init__(self, message, status=403, code='forbidden'):
        super().__init__(message)
        self.status, self.code = status, code


def password_hash(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode('utf-8'), salt=salt, n=2**17, r=8, p=1,
                            maxmem=256*1024*1024, dklen=32)
    return 'scrypt$' + base64.b64encode(salt).decode() + '$' + base64.b64encode(digest).decode()


def password_matches(password, encoded):
    try:
        algorithm, salt, expected = encoded.split('$')
        if algorithm != 'scrypt':
            return False
        digest = hashlib.scrypt(password.encode('utf-8'), salt=base64.b64decode(salt),
                                n=2**17, r=8, p=1, maxmem=256*1024*1024, dklen=32)
        return hmac.compare_digest(digest, base64.b64decode(expected))
    except (ValueError, TypeError):
        return False


def token_hash(token):
    return hashlib.sha256(str(token or '').encode()).hexdigest()


class Accounts:
    def __init__(self, state_dir, catalog):
        self.path = Path(state_dir) / 'accounts.sqlite3'
        self.catalog = catalog
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('Admin','GLV')),
                password_hash TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
                must_change INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS assignments(user_id TEXT NOT NULL REFERENCES users(id),
                class_id TEXT NOT NULL, slot TEXT NOT NULL, PRIMARY KEY(class_id,slot));
              CREATE TABLE IF NOT EXISTS auth_sessions(token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id), csrf TEXT NOT NULL,
                expires REAL NOT NULL, last_seen REAL NOT NULL);
              CREATE TABLE IF NOT EXISTS login_limits(key TEXT PRIMARY KEY, attempts INTEGER,
                window_start REAL NOT NULL);
              CREATE TABLE IF NOT EXISTS security_audit(id INTEGER PRIMARY KEY, stamp TEXT NOT NULL,
                user_id TEXT, action TEXT NOT NULL, details TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS account_settings(key TEXT PRIMARY KEY,value TEXT);
              CREATE TABLE IF NOT EXISTS assignment_jobs(id TEXT PRIMARY KEY,class_id TEXT NOT NULL,
                expected_sha TEXT NOT NULL, names TEXT NOT NULL, selections TEXT NOT NULL,
                actor_id TEXT NOT NULL,status TEXT NOT NULL,stamp TEXT NOT NULL);
            ''')
        self.dummy_hash = password_hash(secrets.token_urlsafe(24))

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def audit(self, db, user_id, action, details):
        db.execute('INSERT INTO security_audit(stamp,user_id,action,details) VALUES (?,?,?,?)',
                   (datetime.now(timezone.utc).isoformat(), user_id, action,
                    json.dumps(details, ensure_ascii=False)))

    def _username(self, db, role):
        prefix = 'admin' if role == 'Admin' else 'glv'
        number = 1
        while db.execute('SELECT 1 FROM users WHERE username=?', (f'{prefix}{number:03}',)).fetchone():
            number += 1
        return f'{prefix}{number:03}'

    def _create(self, db, name, role, username=None):
        password = secrets.token_urlsafe(12)
        identifier = secrets.token_hex(16)
        username = username or self._username(db, role)
        db.execute('INSERT INTO users VALUES (?,?,?,?,?,1,1,?)',
                   (identifier, username, name, role, password_hash(password),
                    datetime.now(timezone.utc).isoformat()))
        return {'id':identifier, 'username':username, 'displayName':name,
                'role':role, 'temporaryPassword':password}

    def bootstrap_accounts(self):
        """One-time import; later Excel edits never silently grant permissions."""
        with self.db() as db:
            if db.execute('SELECT 1 FROM users LIMIT 1').fetchone():
                return
            credentials = [self._create(db, 'Quản trị giáo xứ', 'Admin', 'admin')]
            by_name = {}
            for class_id, info in sorted(self.catalog.classes.items(), key=lambda x:x[1]['name']):
                for slot in SLOTS:
                    name = str(info['teachers'].get(slot) or '').strip()
                    if not name or name in ('-', '—', '0'):
                        continue
                    key = ' '.join(name.casefold().split())
                    if key not in by_name:
                        account = self._create(db, name, 'GLV')
                        by_name[key] = account['id']
                        credentials.append(account)
                    db.execute('INSERT INTO assignments VALUES (?,?,?)', (by_name[key], class_id, slot))
            filename = self.path.parent / ('tai-khoan-ban-dau-' + secrets.token_hex(4) + '.csv')
            with filename.open('x', encoding='utf-8-sig', newline='') as output:
                writer = csv.writer(output)
                writer.writerow(['Tên đăng nhập','Mật khẩu tạm','Họ tên','Role','Lớp được phân công'])
                for account in credentials:
                    classes = [self.catalog.classes[r['class_id']]['name'] for r in db.execute(
                        'SELECT DISTINCT class_id FROM assignments WHERE user_id=?', (account['id'],))]
                    writer.writerow([account['username'],account['temporaryPassword'],account['displayName'],
                                     account['role'], 'Toàn bộ' if account['role']=='Admin' else ', '.join(classes)])
                output.flush()
                os.fsync(output.fileno())
            db.execute('INSERT INTO account_settings VALUES (?,?)', ('initial_credentials', str(filename)))
            self.audit(db, credentials[0]['id'], 'bootstrap', {'accounts':len(credentials)})

    def _public(self, db, row):
        assignments = [dict(a) for a in db.execute('SELECT class_id,slot FROM assignments WHERE user_id=? ORDER BY class_id,slot', (row['id'],))]
        return {'id':row['id'], 'username':row['username'], 'displayName':row['display_name'],
                'role':row['role'], 'active':bool(row['active']), 'mustChangePassword':bool(row['must_change']),
                'classIds':sorted({a['class_id'] for a in assignments}), 'assignments':assignments}

    def _new_session(self, db, row):
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        now = time.time()
        db.execute('DELETE FROM auth_sessions WHERE expires<=? OR last_seen<?', (now,now-IDLE_SECONDS))
        db.execute('INSERT INTO auth_sessions VALUES (?,?,?,?,?)', (token_hash(token),row['id'],csrf,now+SESSION_SECONDS,now))
        return {'token':token, 'csrfToken':csrf, 'user':self._public(db,row)}

    def login(self, values, address):
        username = str(values.get('username') or '').strip().lower()[:80]
        password = values.get('password')
        if not isinstance(password,str) or not 1 <= len(password) <= 128:
            raise AccessError('Tên đăng nhập hoặc mật khẩu chưa đúng.',401,'invalid_credentials')
        now = time.time()
        keys = ['ip:'+address, 'user:'+token_hash(username)]
        with self.db() as db:
            for key in keys:
                old = db.execute('SELECT * FROM login_limits WHERE key=?', (key,)).fetchone()
                limit = 30 if key.startswith('ip:') else 5
                if old and now-old['window_start'] < 300 and old['attempts'] >= limit:
                    raise AccessError('Thử quá nhiều lần. Chờ 5 phút rồi đăng nhập lại.',429,'rate_limited')
                if not old or now-old['window_start'] >= 300:
                    db.execute('INSERT OR REPLACE INTO login_limits VALUES (?,1,?)',(key,now))
                else:
                    db.execute('UPDATE login_limits SET attempts=attempts+1 WHERE key=?',(key,))
            row = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        valid = password_matches(password, row['password_hash'] if row else self.dummy_hash)
        with self.db() as db:
            current = db.execute('SELECT * FROM users WHERE id=?', (row['id'] if row else '',)).fetchone()
            if not valid or not current or not current['active'] or current['password_hash'] != row['password_hash']:
                self.audit(db, row['id'] if row else None, 'login-failed', {'address':address})
                failure = True
            else:
                db.execute('DELETE FROM login_limits WHERE key=?', (keys[1],))
                self.audit(db, current['id'], 'login', {'address':address})
                result = self._new_session(db,current)
                failure = False
        if failure:
            raise AccessError('Tên đăng nhập hoặc mật khẩu chưa đúng.',401,'invalid_credentials')
        return result

    def principal(self, token, csrf=None, allow_change=False):
        now = time.time()
        with self.db() as db:
            session = db.execute('SELECT * FROM auth_sessions WHERE token_hash=?',(token_hash(token),)).fetchone()
            row = db.execute('SELECT * FROM users WHERE id=?',(session['user_id'],)).fetchone() if session else None
            if not row or not row['active'] or session['expires'] <= now or now-session['last_seen'] > IDLE_SECONDS:
                raise AccessError('Vui lòng đăng nhập để tiếp tục.',401,'auth_required')
            if csrf is not None and not hmac.compare_digest(str(csrf),session['csrf']):
                raise AccessError('Phiên thao tác chưa hợp lệ. Tải lại trang rồi thử lại.',403,'csrf_invalid')
            if now-session['last_seen'] > 60:
                db.execute('UPDATE auth_sessions SET last_seen=? WHERE token_hash=?',(now,token_hash(token)))
            public = self._public(db,row)
            public['csrfToken'] = session['csrf']
            if row['must_change'] and not allow_change:
                raise AccessError('Cần đổi mật khẩu tạm trước khi sử dụng.',403,'password_change_required')
            return public

    def logout(self, token, csrf):
        user = self.principal(token,csrf,allow_change=True)
        with self.db() as db:
            db.execute('DELETE FROM auth_sessions WHERE token_hash=?',(token_hash(token),))
            self.audit(db,user['id'],'logout',{})
        return {'loggedOut':True}

    def change_password(self, token, csrf, values):
        user = self.principal(token,csrf,allow_change=True)
        old, new = values.get('currentPassword'), values.get('newPassword')
        if not isinstance(new,str) or not 15 <= len(new) <= 128:
            raise ValueError('Mật khẩu mới cần từ 15 đến 128 ký tự; có thể dùng một câu dễ nhớ.')
        with self.db() as db:
            row = db.execute('SELECT * FROM users WHERE id=?',(user['id'],)).fetchone()
            original = row['password_hash']
            first_change = bool(row['must_change'])
        if first_change:
            # A valid session already authenticated the temporary password.
            if password_matches(new,original):
                raise ValueError('Mật khẩu mới phải khác mật khẩu tạm đang dùng.')
        else:
            if not isinstance(old,str) or len(old)>128 or not password_matches(old,original):
                raise AccessError('Mật khẩu hiện tại chưa đúng.',403,'incorrect_password')
            if hmac.compare_digest(old.encode(),new.encode()):
                raise ValueError('Mật khẩu mới phải khác mật khẩu đang dùng.')
        encoded = password_hash(new)
        with self.db() as db:
            row = db.execute('SELECT * FROM users WHERE id=?',(user['id'],)).fetchone()
            if row['password_hash'] != original:
                raise AccessError('Mật khẩu đã thay đổi. Đăng nhập lại.',401,'auth_required')
            db.execute('UPDATE users SET password_hash=?,must_change=0 WHERE id=?',(encoded,user['id']))
            db.execute('DELETE FROM auth_sessions WHERE user_id=?',(user['id'],))
            self.audit(db,user['id'],'password-changed',{})
            return self._new_session(db,db.execute('SELECT * FROM users WHERE id=?',(user['id'],)).fetchone())

    def users(self):
        with self.db() as db:
            return [self._public(db,row) for row in db.execute('SELECT * FROM users ORDER BY role,display_name')]

    def create(self, actor, values):
        name, role = str(values.get('displayName') or '').strip(), values.get('role','GLV')
        if not 2 <= len(name) <= 100 or role not in ('Admin','GLV'):
            raise ValueError('Nhập họ tên và chọn role Admin hoặc GLV.')
        with self.db() as db:
            result = self._create(db,name,role)
            if role=='GLV' and db.execute("SELECT 1 FROM sqlite_master WHERE name='staff_profiles'").fetchone():
                db.execute('INSERT INTO staff_profiles(id,user_id,full_name,phone,email,birth_date,address,status,service_from,service_to,note,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                    (result['id'],result['id'],name,'','','','','active','','','',datetime.now(timezone.utc).isoformat()))
            self.audit(db,actor['id'],'account-created',{'id':result['id'],'before':None,'after':{'username':result['username'],'name':name,'role':role}})
        return result

    def update(self, actor, values):
        role, active = values.get('role'), values.get('active')
        if role not in ('Admin','GLV') or type(active) is not bool:
            raise ValueError('Role hoặc trạng thái tài khoản không hợp lệ.')
        with self.db() as db:
            row = db.execute('SELECT * FROM users WHERE id=?',(values.get('id'),)).fetchone()
            if not row:
                raise ValueError('Không tìm thấy tài khoản.')
            if row['id']==actor['id'] and (role!='Admin' or not active):
                raise ValueError('Dùng một tài khoản Admin khác để thay đổi quyền của chính bạn.')
            if row['role']=='Admin' and row['active'] and (role!='Admin' or not active):
                count = db.execute("SELECT COUNT(*) FROM users WHERE role='Admin' AND active=1").fetchone()[0]
                if count<=1:
                    raise ValueError('Cần giữ ít nhất một Admin hoạt động.')
            db.execute('UPDATE users SET role=?,active=? WHERE id=?',(role,int(active),row['id']))
            db.execute('DELETE FROM auth_sessions WHERE user_id=?',(row['id'],))
            self.audit(db,actor['id'],'account-updated',{'id':row['id'],
                'before':{'role':row['role'],'active':bool(row['active'])},'after':{'role':role,'active':active}})
        return {'saved':True}

    def reset_password(self, actor, values):
        password = secrets.token_urlsafe(12)
        encoded = password_hash(password)
        with self.db() as db:
            row = db.execute('SELECT * FROM users WHERE id=?',(values.get('id'),)).fetchone()
            if not row:
                raise ValueError('Không tìm thấy tài khoản.')
            db.execute('UPDATE users SET password_hash=?,must_change=1 WHERE id=?',(encoded,row['id']))
            db.execute('DELETE FROM auth_sessions WHERE user_id=?',(row['id'],))
            self.audit(db,actor['id'],'password-reset',{'id':row['id']})
            return {'username':row['username'],'displayName':row['display_name'],'temporaryPassword':password}

    def _apply_assignment(self, db, class_id, selections, actor_id, job_id):
        previous={r['slot']:r['user_id'] for r in db.execute('SELECT * FROM assignments WHERE class_id=?',(class_id,))}
        db.execute('DELETE FROM assignments WHERE class_id=?',(class_id,))
        for slot, user_id in selections.items():
            if user_id:
                db.execute('INSERT INTO assignments VALUES (?,?,?)',(user_id,class_id,slot))
        db.execute("UPDATE assignment_jobs SET status='applied' WHERE id=?",(job_id,))
        self.audit(db,actor_id,'class-assigned',{'classId':class_id,'before':previous,'after':selections})
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='assignment_history'").fetchone():
            info=self.catalog.classes.get(class_id)
            for slot in SLOTS:
                if previous.get(slot)==selections.get(slot): continue
                for who,event in ((previous.get(slot),'ended'),(selections.get(slot),'assigned')):
                    if who: db.execute('INSERT INTO assignment_history(user_id,class_id,class_name,slot,year,event,actor_id,stamp) VALUES (?,?,?,?,?,?,?,?)',
                        (who,class_id,info['name'] if info else class_id,slot,self.catalog.public()['year'],event,actor_id,datetime.now(timezone.utc).isoformat()))

    def assign_class(self, store, actor, values):
        class_id = values.get('classId')
        info = store.catalog.classes.get(class_id)
        if not info:
            raise ValueError('Không tìm thấy lớp.')
        selections = values.get('accountAssignments')
        if not isinstance(selections,dict) or set(selections)!=set(SLOTS):
            raise ValueError('Chọn tài khoản cho GLV1, GLV2, GLV3 và Soeur.')
        assigned = [v for v in selections.values() if v]
        if len(set(assigned))!=len(assigned):
            raise ValueError('Một người chỉ được chọn một vị trí trong cùng lớp.')
        names = {}
        with self.db() as db:
            for slot,user_id in selections.items():
                row = db.execute('SELECT * FROM users WHERE id=?',(user_id,)).fetchone() if user_id else None
                if user_id and (not row or not row['active']):
                    raise ValueError('Chỉ phân công tài khoản đang hoạt động.')
                names[slot] = row['display_name'] if row else ''
            identifier = secrets.token_hex(12)
            original_sha = hashlib.sha256(info['path'].read_bytes()).hexdigest()
            db.execute('INSERT INTO assignment_jobs VALUES (?,?,?,?,?,?,?,?)',
                       (identifier,class_id,original_sha,json.dumps(names,ensure_ascii=False),
                        json.dumps(selections),actor['id'],'pending',datetime.now(timezone.utc).isoformat()))
        try:
            result = store.update_teachers({'classId':class_id,**names,'actor':actor['displayName']})
        except Exception:
            self.recover_assignments(store.catalog)
            raise
        with self.db() as db:
            self._apply_assignment(db,class_id,selections,actor['id'],identifier)
        return {**result,'saved':True}

    def recover_assignments(self, catalog):
        catalog.refresh()
        with self.db() as db:
            for job in db.execute("SELECT * FROM assignment_jobs WHERE status='pending'").fetchall():
                info = catalog.classes.get(job['class_id'])
                if not info:
                    continue
                names, selections = json.loads(job['names']), json.loads(job['selections'])
                if all(str(info['teachers'].get(slot) or '')==name for slot,name in names.items()):
                    self._apply_assignment(db,job['class_id'],selections,job['actor_id'],job['id'])
                elif hashlib.sha256(info['path'].read_bytes()).hexdigest()==job['expected_sha']:
                    db.execute("UPDATE assignment_jobs SET status='cancelled' WHERE id=?",(job['id'],))
                else:
                    db.execute("UPDATE assignment_jobs SET status='conflict' WHERE id=?",(job['id'],))

    def audit_operation(self, actor, path, values, before=None, after=None):
        safe = {key:values[key] for key in ('classId','code','sessionId','id') if key in values}
        safe.update(before=before,after=after)
        if values.get('reason'): safe['reason']=str(values['reason'])[:500]
        with self.db() as db:
            self.audit(db,actor['id'],path,safe)
