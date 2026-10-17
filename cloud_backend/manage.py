"""Local, explicit schema/import commands. Does not print connection secrets."""
import argparse
import json
import os
from pathlib import Path
from sqlalchemy.schema import CreateTable, CreateIndex
from sqlalchemy.dialects import postgresql
from dotenv import load_dotenv
from .database import Database
from .models import metadata
from .migration import import_bundle, bundle_digest, read_workbooks


def schema_sql():
    dialect = postgresql.dialect()
    lines = ['-- Xuan Hoa cloud v2. No source data or account secrets.', 'BEGIN;']
    for table in metadata.sorted_tables:
        lines.append(str(CreateTable(table, if_not_exists=True).compile(dialect=dialect)).strip()+';')
        for index in sorted(table.indexes, key=lambda i:i.name):
            lines.append(str(CreateIndex(index, if_not_exists=True).compile(dialect=dialect))+';')
        lines.append(f'ALTER TABLE {table.name} ENABLE ROW LEVEL SECURITY;')
        lines.append(f'REVOKE ALL ON TABLE {table.name} FROM PUBLIC, anon, authenticated;')
    lines.append('ALTER TABLE xh_users ADD COLUMN IF NOT EXISTS deleted_at VARCHAR(50);')
    lines.append('COMMIT;')
    return '\n\n'.join(lines)+'\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('schema', 'check', 'import'))
    parser.add_argument('--env-file', default='.env.cloud.local')
    parser.add_argument('--output')
    parser.add_argument('--source')
    parser.add_argument('--commit', action='store_true')
    parser.add_argument('--expected-digest')
    args = parser.parse_args()
    if args.command == 'schema':
        content = schema_sql()
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output).write_text(content, encoding='utf-8')
            print('Prepared schema SQL without credentials or personal data.')
        else:
            print(content)
        return
    load_dotenv(args.env_file, override=False)
    if args.command == 'import':
        if not args.source:
            parser.error('import requires --source')
        bundle = json.loads(Path(args.source).read_text(encoding='utf-8'))
        artifacts = read_workbooks(args.source, bundle)
        digest = bundle_digest(bundle)
        if not args.commit:
            print(json.dumps({'digest':digest,'years':len(bundle.get('years',[])),
                              'users':len(bundle.get('accounts',{}).get('users',[])), 'written':False}))
            return
        if not args.expected_digest:
            parser.error('--commit requires --expected-digest from the dry run')
        database = Database(os.environ.get('XH_DATABASE_URL',''))
        print(json.dumps(import_bundle(database,bundle,expected_digest=args.expected_digest,workbooks=artifacts)))
        return
    from sqlalchemy import text
    database = Database(os.environ.get('XH_DATABASE_URL',''))
    with database.transaction() as connection:
        connection.execute(text('SELECT 1'))
        tables = connection.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'xh_%'")).scalar_one()
    print(json.dumps({'database':'connected','cloudTables':tables,'secretsPrinted':False}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Provider connection errors frequently contain DSNs. Do not echo them.
        print(json.dumps({'error':type(error).__name__, 'message':'Chưa hoàn tất. Kiểm tra cấu hình riêng trên máy; không gửi secret vào chat.'}))
        raise SystemExit(1)
