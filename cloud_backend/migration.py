"""Explicit, transactional import. A new deployment cannot overwrite live users."""
import hashlib
import json
import re
from pathlib import Path
from sqlalchemy import select, insert, func
from . import models as m
from .security import CloudError, audit_details
from .service import stamp
from .persistence import store_blob


def bundle_digest(bundle):
    return hashlib.sha256(json.dumps(bundle, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def read_workbooks(source, bundle):
    root = Path(source).resolve().parent
    artifacts = {}
    for entry in bundle.get('workbooks', []):
        path = (root/entry['relative']).resolve()
        if not path.is_relative_to(root/'workbooks') or not path.is_file() or path.stat().st_size > 4_000_000:
            raise CloudError('Đường dẫn hoặc dung lượng sổ nguồn không hợp lệ.')
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if digest != entry['sha256']:
            raise CloudError('Sổ nguồn đã thay đổi sau khi xuất gói chuyển đổi.')
        artifacts[digest] = content
    for year in bundle['years']:
        if any(r.get('status') in ('pending', 'conflict') for r in year.get('sourceTables', {}).get('xh_grade_jobs', [])):
            raise CloudError('Còn bảng điểm chờ/đang xung đột ở bản cũ. Đối chiếu và xuất gói lại trước khi chuyển cloud.')
    return artifacts


def import_bundle(database, bundle, *, expected_digest=None, workbooks=None):
    if bundle.get('format') != 'xuanhoa-cloud-source-v1' or not isinstance(bundle.get('years'), list):
        raise CloudError('Định dạng dữ liệu chuyển đổi không hợp lệ.')
    digest = bundle_digest(bundle)
    if expected_digest is not None and digest != expected_digest:
        raise CloudError('Mã kiểm tra bản chuyển đổi không khớp.')
    accounts = bundle.get('accounts', {})
    account_rows = accounts.get('users', [])
    known = {r['id'] for r in account_rows}
    if not account_rows or len(known) != len(account_rows):
        raise CloudError('Thiếu tài khoản hoặc mã tài khoản bị trùng.')
    if not any(r.get('role') == 'Admin' and r.get('active') for r in account_rows):
        raise CloudError('Bản chuyển đổi cần có Admin đang hoạt động.')
    active = [y for y in bundle['years'] if y.get('active')]
    if len(active) != 1:
        raise CloudError('Cần đúng một năm học đang hoạt động.')
    report = {'users': len(account_rows), 'years': len(bundle['years']),
              'classes': sum(len(y['catalog']['classes']) for y in bundle['years']),
              'students': sum(len(y['catalog']['students']) for y in bundle['years'])}
    with database.transaction() as db:
        if db.execute(select(m.imports.c.digest).where(m.imports.c.digest == digest)).first():
            return {**report, 'alreadyImported': True, 'digest': digest}
        if db.execute(select(func.count()).select_from(m.users)).scalar_one() or db.execute(select(func.count()).select_from(m.years)).scalar_one():
            raise CloudError('Cloud đã có dữ liệu. Chưa ghi đè; cần kế hoạch chuyển đổi riêng.')
        usernames = set()
        for row in account_rows:
            username = str(row['username']).strip().casefold()
            if not username or username in usernames or row['role'] not in ('Admin', 'GLV') or not re.fullmatch(r'scrypt\$[A-Za-z0-9+/=]+\$[A-Za-z0-9+/=]+', row['password_hash']):
                raise CloudError('Tài khoản nguồn không hợp lệ hoặc trùng tên đăng nhập.')
            usernames.add(username)
            db.execute(insert(m.users).values(id=row['id'], username=username, display_name=row['display_name'],
                       role=row['role'], password_hash=row['password_hash'], active=bool(row['active']),
                       must_change=bool(row['must_change']), created_at=row['created_at'], revision=1))
        for year in bundle['years']:
            year_id, catalog = year['id'], year['catalog']
            db.execute(insert(m.years).values(id=year_id, label=catalog['year'], active=bool(year.get('active')), created_at=stamp()))
            class_ids = set()
            for group in catalog['classes']:
                identifier = group['id']
                if identifier in class_ids:
                    raise CloudError('Mã lớp bị trùng trong năm học.')
                class_ids.add(identifier)
                db.execute(insert(m.classes).values(id=identifier, year_id=year_id, name=group['name'],
                           archived=bool(group.get('archived')), payload={k:v for k,v in group.items() if k not in ('id','name','path')}, revision=1))
            codes = set()
            for person in catalog['students']:
                code = person['id']
                if code in codes or person['classId'] not in class_ids:
                    raise CloudError('Mã thiếu nhi bị trùng hoặc sai lớp.')
                codes.add(code)
                payload = {k:v for k,v in person.items() if k not in ('id','classId')}
                db.execute(insert(m.students).values(year_id=year_id, code=code, class_id=person['classId'], payload=payload, revision=1))
            history = {r['mark_key']:r for r in sorted(year.get('sourceTables', {}).get('audit', []),key=lambda r:r['id'])}
            for key, mark in catalog.get('marks', {}).items():
                day, activity, code = key.split('|')
                if code not in codes or activity not in ('mass', 'lesson', 'early') or mark.get('status') not in ('X', 'P', 'O'):
                    raise CloudError('Dữ liệu điểm danh nguồn không hợp lệ.')
                previous = history.get(key, {})
                matches = previous.get('status') == mark['status']
                db.execute(insert(m.marks).values(year_id=year_id, code=code, day=day, activity=activity,
                           status=mark['status'], stamp=previous.get('stamp') if matches else mark.get('timestamp'),
                           source=str((previous.get('source') if matches else mark.get('source')) or 'Excel')[:100]))
            assignment_keys = set()
            for assignment in year.get('assignments', []):
                key = (assignment['class_id'], assignment['slot'])
                if assignment['user_id'] not in known or assignment['class_id'] not in class_ids or assignment['slot'] not in ('glv1','glv2','glv3','souer') or key in assignment_keys:
                    raise CloudError('Phân công nguồn không hợp lệ.')
                assignment_keys.add(key)
                db.execute(insert(m.assignments).values(year_id=year_id, class_id=assignment['class_id'], slot=assignment['slot'], user_id=assignment['user_id']))
            for name, rows in year.get('sourceTables', {}).items():
                # Preserve old histories/grades for the next migration stage.
                # They are not represented as migrated operational services.
                db.execute(insert(m.records).values(year_id=year_id, kind='source-table', id=name, payload={'rows':rows}, revision=1))
            for workbook in bundle.get('workbooks', []):
                if workbook['yearId'] == year_id:
                    if workbooks is not None:
                        if workbook['sha256'] not in workbooks:
                            raise CloudError('Thiếu sổ lớp trong gói chuyển đổi.')
                        content = workbooks[workbook['sha256']]
                        if hashlib.sha256(content).hexdigest() != workbook['sha256']:
                            raise CloudError('Nội dung sổ không khớp mã kiểm tra.')
                        store_blob(db, content)
                    db.execute(insert(m.records).values(year_id=year_id, kind='source-workbook', id=workbook['classId'],
                               payload=workbook, revision=1))
        for row in accounts.get('staff_profiles', []):
            if row.get('user_id') and row['user_id'] not in known:
                raise CloudError('Hồ sơ GLV liên kết tài khoản không tồn tại.')
            db.execute(insert(m.staff).values(id=row['id'], user_id=row.get('user_id'), payload={k:v for k,v in row.items() if k not in ('id','user_id')}))
        for row in accounts.get('security_audit', []):
            details = row.get('details') or {}
            if isinstance(details,str):
                details = json.loads(details)
            db.execute(insert(m.audit).values(id='legacy-'+str(row['id']), user_id=row.get('user_id'),
                action=row.get('action') or 'source-event', stamp=row.get('stamp') or stamp(), details=audit_details(details)))
        # Retain all source account history except sessions/rate-limit buckets.
        for name, rows in accounts.items():
            if name in ('auth_sessions', 'login_limits', 'users', 'staff_profiles'):
                continue
            db.execute(insert(m.records).values(year_id=active[0]['id'], kind='source-accounts', id=name, payload={'rows':rows}, revision=1))
        db.execute(insert(m.settings).values(key='schema-version', value={'version':2,'stage':'cloud'}))
        db.execute(insert(m.imports).values(digest=digest, stamp=stamp(), report=report))
    return {**report, 'alreadyImported': False, 'digest': digest}
