"""Streaming application backup through age; never writes a plaintext archive.

Uses its own backup credential. Verify decrypts/checks every row without touching
the database. Restore only targets an explicitly configured, empty database.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from sqlalchemy import inspect, select
from dotenv import load_dotenv
from . import models as m
from .database import Database

FORMAT = 'xuanhoa-encrypted-rows-v1'
OMIT = {m.sessions.name, m.limits.name}


def encode(value):
    if isinstance(value, bytes):
        return {'$bytes': base64.b64encode(value).decode('ascii')}
    raise TypeError('Unsupported database value')


def decode(value):
    if set(value) == {'$bytes'}:
        return base64.b64decode(value['$bytes'], validate=True)
    return value


def line(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, default=encode)+'\n').encode('utf8')


def executable():
    result = shutil.which('age')
    if not result:
        raise ValueError('Cần cài age từ https://age-encryption.org trước khi sao lưu.')
    return result


def backup(database, recipient, output):
    output = Path(output).resolve()
    root = Path(__file__).resolve().parents[1]
    if output.suffix != '.age' or output.exists() or any(output.is_relative_to(root/name) for name in ('dist', 'public')):
        raise ValueError('Chọn file .age mới trong thư mục riêng, không dùng dist/public.')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name+'.partial')
    digest, counts = hashlib.sha256(), {}
    age = executable()
    created = False
    try:
        with temporary.open('xb') as ciphertext:
            created = True
            child = subprocess.Popen([age, '-r', recipient], stdin=subprocess.PIPE, stdout=ciphertext,
                                     stderr=subprocess.PIPE, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            try:
                child.stdin.write(line({'format': FORMAT, 'tables': [t.name for t in m.metadata.sorted_tables]}))
                with database.transaction(readonly=True) as db:
                    for table in m.metadata.sorted_tables:
                        counts[table.name] = 0
                        if table.name in OMIT:
                            continue
                        statement = select(table)
                        if table is m.settings:
                            statement = statement.where(~m.settings.c.key.like('reauth:%'))
                        for row in db.execution_options(stream_results=True).execute(statement).mappings():
                            payload = line({'table': table.name, 'row': dict(row)})
                            child.stdin.write(payload); digest.update(payload); counts[table.name] += 1
                child.stdin.write(line({'manifest': counts, 'sha256': digest.hexdigest()}))
                child.stdin.close()
                child.stderr.read()
                if child.wait() != 0:
                    raise ValueError('Mã hóa thất bại; không tạo bản sao hoàn tất.')
                ciphertext.flush(); os.fsync(ciphertext.fileno())
            finally:
                if child.poll() is None:
                    child.kill(); child.wait()
                child.stdin.close(); child.stderr.close()
        if temporary.stat().st_size < 100:
            raise ValueError('Bản sao mã hóa không hợp lệ.')
        # Hard-link publication refuses to overwrite another backup, even in a race.
        os.link(temporary, output)
        temporary.unlink()
        return {'encrypted': True, 'tables': counts, 'bytes': output.stat().st_size}
    finally:
        if created and temporary.exists():
            temporary.unlink()


def read_archive(archive, identity, consume=lambda table, row: None):
    age = executable()
    child = subprocess.Popen([age, '-d', '-i', str(identity), str(archive)], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    digest, counts = hashlib.sha256(), {t.name: 0 for t in m.metadata.sorted_tables}
    tables = {t.name: t for t in m.metadata.sorted_tables}
    manifest = None
    try:
        header = json.loads(child.stdout.readline())
        if header.get('format') != FORMAT or header.get('tables') != list(tables):
            raise ValueError('Định dạng/schema backup không khớp phiên bản ứng dụng.')
        for payload in child.stdout:
            item = json.loads(payload)
            if 'manifest' in item:
                if manifest is not None:
                    raise ValueError('Backup có nhiều manifest.')
                manifest = item
                continue
            if manifest is not None or set(item) != {'table', 'row'} or item['table'] not in tables:
                raise ValueError('Cấu trúc backup không hợp lệ.')
            name = item['table']
            row = item['row']
            if name == m.blobs.name:
                row = {**row, 'content': decode(row['content'])}
            if set(row) != set(tables[name].columns.keys()) or name in OMIT:
                raise ValueError('Backup chứa hàng/bảng không được phép.')
            if name == m.settings.name and str(row['key']).startswith('reauth:'):
                raise ValueError('Backup không được chứa bằng chứng phiên cũ.')
            digest.update(payload); counts[name] += 1
            consume(tables[name], row)
        child.stderr.read()
        if child.wait() != 0 or manifest != {'manifest': counts, 'sha256': digest.hexdigest()}:
            raise ValueError('Sai khóa, file hỏng hoặc manifest không khớp.')
        return {'verified': True, 'tables': counts}
    finally:
        if child.poll() is None:
            child.kill(); child.wait()
        child.stdout.close(); child.stderr.close()


def restore(database, archive, identity):
    # Authenticate the complete archive before creating any database objects.
    read_archive(archive, identity)
    with database.engine.begin() as db:
        if any(name.startswith('xh_') for name in inspect(db).get_table_names()):
            raise ValueError('Chỉ được phục hồi vào database trống, không ghi đè dữ liệu hiện có.')
        m.metadata.create_all(db)
        if db.dialect.name == 'postgresql':
            from sqlalchemy import text
            roles = list(db.execute(text("SELECT rolname FROM pg_roles WHERE rolname IN ('anon','authenticated')")).scalars())
            recipients = 'PUBLIC'+''.join(', '+db.dialect.identifier_preparer.quote(role) for role in roles)
            for table in m.metadata.sorted_tables:
                name = db.dialect.identifier_preparer.format_table(table)
                db.execute(text(f'ALTER TABLE {name} ENABLE ROW LEVEL SECURITY'))
                db.execute(text(f'REVOKE ALL ON TABLE {name} FROM {recipients}'))
        result = read_archive(archive, identity, lambda table, row: db.execute(table.insert().values(**row)))
    return {**result, 'restored': True, 'sessionsRestored': False,
            'nextStep': 'Cài grants/RLS bằng migration và kiểm tra quyền trước khi mở truy cập.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('backup', 'verify', 'restore'))
    parser.add_argument('--env-file', default='.env.cloud.local')
    parser.add_argument('--output'); parser.add_argument('--recipient')
    parser.add_argument('--archive'); parser.add_argument('--identity')
    parser.add_argument('--confirm')
    args = parser.parse_args()
    load_dotenv(args.env_file, override=False)
    try:
        if args.command == 'backup':
            if not args.output or not args.recipient or not os.environ.get('XH_BACKUP_DATABASE_URL'):
                parser.error('backup cần --output, --recipient và XH_BACKUP_DATABASE_URL riêng.')
            result = backup(Database(os.environ['XH_BACKUP_DATABASE_URL']), args.recipient, args.output)
        else:
            if not args.archive or not args.identity:
                parser.error('Cần --archive và --identity trỏ đến khóa riêng được bảo vệ.')
            if args.command == 'verify':
                result = read_archive(args.archive, args.identity)
            else:
                if args.confirm != 'RESTORE-EMPTY-DATABASE' or not os.environ.get('XH_RESTORE_DATABASE_URL'):
                    parser.error('restore cần XH_RESTORE_DATABASE_URL riêng và --confirm RESTORE-EMPTY-DATABASE.')
                result = restore(Database(os.environ['XH_RESTORE_DATABASE_URL']), args.archive, args.identity)
        print(json.dumps(result))
    except Exception as error:
        # Do not print exceptions containing database URI/SQL parameters/records.
        print(json.dumps({'success': False, 'stage': args.command, 'errorType': type(error).__name__}))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
