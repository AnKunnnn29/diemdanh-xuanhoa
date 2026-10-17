"""Apply the requested 2026–2027 parish leadership Admin assignments."""
import argparse
import csv
import json
import os
import secrets
import sys
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from dotenv import load_dotenv
from sqlalchemy import select
from cloud_backend import models as m
from cloud_backend.account_naming import name_words
from cloud_backend.database import Database
from cloud_backend.office import Office
from cloud_backend.persistence import fingerprint
from cloud_backend.security import CloudError
from cloud_backend.service import Service

def load_targets():
    path = PROJECT / '.local/parish-admin-targets.json'
    if not path.is_file():
        raise ValueError('Cần file .local/parish-admin-targets.json do quản trị viên chuẩn bị.')
    targets = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(targets, list) or not targets or any(
            not isinstance(row, list) or len(row) != 2
            or any(not isinstance(value, str) or not value.strip() for value in row)
            for row in targets):
        raise ValueError('Mỗi mục cần một cặp họ tên dân sự và họ tên đầy đủ.')
    return targets


def plan_accounts(users, targets=None):
    targets = load_targets() if targets is None else targets
    result = []
    for civil_name, full_name in targets:
        suffix = name_words(civil_name)
        matches = [row for row in users if name_words(row['display_name'])[-len(suffix):] == suffix]
        if len(matches) > 1:
            raise CloudError('Có nhiều tài khoản trùng họ tên; cần đối chiếu trước khi cấp quyền.')
        user = matches[0] if matches else None
        if user and (user.get('deleted_at') or not user['active']):
            raise CloudError('Tài khoản đích bị khóa hoặc đã xóa; chưa thay đổi trạng thái.')
        result.append({'displayName': full_name, 'id': user['id'] if user else None,
                       'username': user['username'] if user else None,
                       'action': 'create' if not user else 'promote' if user['role'] != 'Admin' else 'unchanged'})
    ids = [row['id'] for row in result if row['id']]
    if len(ids) != len(set(ids)):
        raise CloudError('Hai người trong danh sách khớp cùng tài khoản; cần kiểm tra lại.')
    return result


def accounts(db):
    return [dict(row) for row in db.execute(select(m.users)).mappings()]


def promote(db, service, actor, plan):
    """Uses the same role updates, audits and session revocation as the admin UI."""
    before = {row['id']: row for row in accounts(db)}
    assignments = list(db.execute(select(m.assignments)))
    sessions = {row['token_hash']: dict(row) for row in db.execute(select(m.sessions)).mappings()}
    profiles = {row['id']: dict(row) for row in db.execute(select(m.staff)).mappings()}
    created = []
    promoted = set()
    results = []
    for target in plan:
        if target['action'] == 'create':
            credential = service.account_write(db, actor, 'accounts/create',
                {'displayName': target['displayName'], 'role': 'Admin', 'assignments': []})
            created.append(credential)
            results.append({**target, 'id': credential['id'], 'username': credential['username'], 'role': 'Admin'})
        else:
            user = before[target['id']]
            if target['action'] == 'promote':
                service.account_write(db, actor, 'accounts/update',
                    {'id': user['id'], 'role': 'Admin', 'active': user['active']})
                promoted.add(user['id'])
            results.append({**target, 'role': 'Admin'})
    after = {row['id']: row for row in accounts(db)}
    if set(after) != set(before) | {row['id'] for row in created}:
        raise CloudError('Số lượng tài khoản thay đổi ngoài phạm vi yêu cầu.')
    for identifier, original in before.items():
        expected = dict(original)
        if identifier in promoted:
            expected.update(role='Admin', revision=original['revision'] + 1)
        if after[identifier] != expected:
            raise CloudError('Thông tin tài khoản thay đổi ngoài phạm vi cấp quyền; hủy giao dịch.')
    if sorted(assignments) != sorted(db.execute(select(m.assignments))):
        raise CloudError('Phân công lớp thay đổi ngoài yêu cầu; hủy giao dịch.')
    expected_sessions = {key: row for key, row in sessions.items() if row['user_id'] not in promoted}
    if expected_sessions != {row['token_hash']: dict(row) for row in db.execute(select(m.sessions)).mappings()}:
        raise CloudError('Phiên đăng nhập thay đổi ngoài phạm vi cấp quyền; hủy giao dịch.')
    current_profiles = {row['id']: dict(row) for row in db.execute(select(m.staff)).mappings()}
    if any(current_profiles.get(key) != row for key, row in profiles.items()):
        raise CloudError('Hồ sơ cũ thay đổi ngoài yêu cầu; hủy giao dịch.')
    for row in results:
        current = after[row['id']]
        if current['role'] != 'Admin' or not current['active'] or current['deleted_at']:
            raise CloudError('Chưa xác minh đủ các tài khoản Admin.')
    service.audit(db, actor['id'], 'parish-leadership-admins', {'accounts': results,
                  'passwordsAndAssignmentsPreserved': True})
    return results, created


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    load_dotenv(PROJECT / '.env.cloud.local')
    database = Database(os.environ['XH_DATABASE_URL'])
    service = Service(database, os.environ['XH_SESSION_SECRET'])
    try:
        if not args.apply:
            with database.transaction(readonly=True) as db:
                plan = plan_accounts(accounts(db))
            print(json.dumps({'written': False, 'accounts': plan}, ensure_ascii=False))
            return
        identifier = datetime.now().strftime('%Y%m%d-%H%M%S-') + secrets.token_hex(3)
        folder = PROJECT / '.local' / ('parish-admin-' + identifier)
        folder.mkdir(parents=True)
        credential_folder = PROJECT / '.local/bridge' / ('staff-import-parish-admin-' + identifier)
        credential_folder.mkdir(parents=True)
        credential_file = credential_folder / 'tai-khoan-glv-moi.csv'
        receipt_file = folder / 'receipt.json'
        # Keep an explicit status in case the connection drops while committing.
        receipt_file.write_text(json.dumps({'committed': False}), encoding='utf-8')
        try:
            with database.transaction() as db:
                users = accounts(db)
                plan = plan_accounts(users)
                actor = next((row for row in users if row['username'] == 'admin'
                              and row['role'] == 'Admin' and row['active'] and not row['deleted_at']), None)
                if not actor:
                    raise CloudError('Không tìm thấy tài khoản quản trị chính đang hoạt động.')
                office = Office(service, db, actor)
                try:
                    snapshot = office.snapshot('Trước cấp Admin cho Ban Trị Sự, Sr phụ trách và Cha xứ')
                finally:
                    office.shutdown()
                business = {table.name: fingerprint([dict(row) for row in db.execute(select(table)).mappings()])
                            for table in (m.classes, m.students, m.marks)}
                results, credentials = promote(db, service, actor, plan)
                for table in (m.classes, m.students, m.marks):
                    if business[table.name] != fingerprint([dict(row) for row in db.execute(select(table)).mappings()]):
                        raise CloudError('Dữ liệu lớp thay đổi ngoài yêu cầu; hủy giao dịch.')
                # Persist newly issued passwords before committing their hashes.
                with credential_file.open('x', encoding='utf-8-sig', newline='') as output:
                    writer = csv.writer(output)
                    writer.writerow(['Tên đăng nhập', 'Mật khẩu tạm', 'Họ tên', 'Vai trò'])
                    for row in credentials:
                        writer.writerow([row['username'], row['temporaryPassword'], row['displayName'], 'Admin'])
                    output.flush()
                    os.fsync(output.fileno())
        except Exception:
            receipt_file.write_text(json.dumps({'committed': False, 'commitStatus': 'not_confirmed',
                                               'credentialsMustBeVerified': True}), encoding='utf-8')
            raise
        report = {'committed': True, 'accounts': results, 'snapshot': snapshot['id'],
                  'promoted': sum(row['action'] == 'promote' for row in results),
                  'created': len(credentials), 'alreadyAdmin': sum(row['action'] == 'unchanged' for row in results),
                  'credentialFile': str(credential_file), 'passwordsAndAssignmentsPreserved': True}
        receipt_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        # Verify persisted results through a fresh connection after commit.
        with database.transaction(readonly=True) as db:
            actual = {row['id']: row for row in accounts(db)}
            for row in results:
                current = actual[row['id']]
                if current['username'] != row['username'] or current['role'] != 'Admin' or not current['active']:
                    raise CloudError('Cần đối chiếu lại trạng thái sau commit; không chạy lại thao tác tạo mật khẩu.')
        print(json.dumps({**report, 'receiptFile': str(receipt_file)}, ensure_ascii=False))
    finally:
        database.engine.dispose()


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        main()
    except Exception as error:
        print(json.dumps({'error': type(error).__name__,
                          'message': 'Chưa xác nhận hoàn tất. Kiểm tra receipt riêng tư; không in secret.'}))
        raise SystemExit(1)
