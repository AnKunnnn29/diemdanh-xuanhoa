"""Export current cloud logins and verified saved passwords; never reset accounts."""
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
from cloud_backend.database import Database
from cloud_backend.security import password_matches

SITE = 'https://giao-xu-xuan-hoa.vercel.app'


def saved_credentials(state_dir, rename_file):
    """Only read actual issuance files, excluding QA copies and backups."""
    aliases = {}
    if rename_file.is_file():
        plan = json.loads(rename_file.read_text(encoding='utf-8-sig'))
        for change in plan.get('changes', []):
            aliases.setdefault(change['oldUsername'].casefold(), set()).add(change['id'])
    result = []
    paths = sorted(state_dir.glob('tai-khoan-ban-dau-*.csv'))
    paths += sorted(state_dir.glob('staff-import-*/tai-khoan-glv-moi.csv'))
    for path in paths:
        with path.open(encoding='utf-8-sig', newline='') as source:
            for row in csv.DictReader(source):
                username = (row.get('Tên đăng nhập') or '').strip().casefold()
                password = row.get('Mật khẩu tạm') or ''
                if not username or not password:
                    continue
                result.append({'username': username, 'password': password,
                               'name': (row.get('Họ tên') or '').strip().casefold(),
                               'ids': aliases.get(username, set())})
    return result


def verified_password(user, candidates):
    seen = set()
    for candidate in candidates:
        if not (candidate['username'] == user['username'].casefold()
                or user['id'] in candidate['ids']
                or candidate['name'] == user['display_name'].strip().casefold()):
            continue
        password = candidate['password']
        if password in seen:
            continue
        seen.add(password)
        if password_matches(password, user['password_hash']):
            return password
    return None


def read_accounts(database):
    with database.transaction(readonly=True) as db:
        users = [dict(row) for row in db.execute(select(m.users).order_by(m.users.c.username)).mappings()]
        years = {row['id']: row['label'] for row in db.execute(select(m.years)).mappings()}
        classes = {(row['year_id'], row['id']): row['name']
                   for row in db.execute(select(m.classes.c.year_id, m.classes.c.id, m.classes.c.name)).mappings()}
        assignments = {}
        for row in db.execute(select(m.assignments)).mappings():
            label = '{} / {} / {}'.format(years.get(row['year_id'], row['year_id']),
                classes.get((row['year_id'], row['class_id']), row['class_id']), row['slot'])
            assignments.setdefault(row['user_id'], []).append(label)
    return users, assignments


def export_text(users, assignments, candidates, target, *, generated_at=None):
    visible = [user for user in users if not user.get('deleted_at')]
    known = 0
    lines = ['DANH SÁCH ĐĂNG NHẬP GIÁO XỨ XUÂN HÒA',
             'Website: ' + SITE,
             'Xuất lúc: ' + (generated_at or datetime.now().astimezone().isoformat(timespec='seconds')),
             'Nguồn: dữ liệu cloud hiện tại; chỉ đọc, không đổi mật khẩu.',
             'Mật khẩu ghi bên dưới đã được đối chiếu với hash hiện tại tại thời điểm xuất.',
             'Không truy xuất được nghĩa là không có mật khẩu đã lưu còn khớp; không phải mật khẩu trống.',
             'Không liệt kê tài khoản đã xóa. Có liệt kê tài khoản bị khóa và ghi rõ trạng thái.', '']
    for index, user in enumerate(visible, 1):
        password = verified_password(user, candidates)
        known += password is not None
        lines += [f'{index}. {user["display_name"]}',
                  'Tên đăng nhập: ' + user['username'],
                  'Mật khẩu: ' + (password if password is not None else '[Không truy xuất được; cần cấp lại nếu quên]'),
                  'Vai trò: ' + user['role'],
                  'Trạng thái: ' + ('Đang hoạt động' if user['active'] else 'Bị khóa'),
                  'Yêu cầu đổi mật khẩu: ' + ('Có' if user['must_change'] else 'Không'),
                  'Phạm vi: ' + ('Toàn bộ lớp' if user['role'] == 'Admin' else 'Theo phân công bên dưới')]
        lines.append('Phân công: ' + ('; '.join(sorted(assignments.get(user['id'], []))) or 'Chưa phân công'))
        lines.append('')
    lines += [f'Tổng tài khoản: {len(visible)}', f'Có mật khẩu đã xác minh: {known}',
              f'Không truy xuất được mật khẩu: {len(visible) - known}']
    # Exclusive creation: never overwrite a previously delivered list.
    with target.open('x', encoding='utf-8-sig', newline='') as output:
        output.write('\r\n'.join(lines) + '\r\n')
    return {'accounts': len(visible), 'verifiedPasswords': known,
            'unavailablePasswords': len(visible) - known,
            'lockedAccounts': sum(not user['active'] for user in visible)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', type=Path, default=PROJECT / '.local/bridge')
    parser.add_argument('--output-dir', type=Path, default=PROJECT / '.local/login-exports')
    args = parser.parse_args()
    private_root = (PROJECT / '.local').resolve()
    folder = args.output_dir.resolve()
    if not folder.is_relative_to(private_root):
        raise ValueError('Chỉ xuất vào thư mục .local riêng tư của dự án.')
    load_dotenv(PROJECT / '.env.cloud.local')
    database_url = os.environ.get('XH_DATABASE_URL')
    if not database_url:
        raise ValueError('Thiếu XH_DATABASE_URL trong môi trường hoặc .env.cloud.local.')
    candidates = saved_credentials(args.state_dir.resolve(), private_root / 'account-usernames/plan.json')
    database = Database(database_url)
    try:
        users, assignments = read_accounts(database)
    finally:
        database.engine.dispose()
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / ('danh-sach-dang-nhap-' + datetime.now().strftime('%Y%m%d-%H%M%S-')
                       + secrets.token_hex(3) + '.txt')
    summary = export_text(users, assignments, candidates, target)
    print(json.dumps({**summary, 'file': str(target), 'readOnly': True}, ensure_ascii=False))


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        main()
    except Exception as error:
        # Connection exceptions can contain DSNs. Never print exception payloads.
        print('Không xuất được danh sách (' + type(error).__name__
              + '). Kiểm tra kết nối cloud, cấu hình và thư mục đầu ra.', file=sys.stderr)
        raise SystemExit(1)
