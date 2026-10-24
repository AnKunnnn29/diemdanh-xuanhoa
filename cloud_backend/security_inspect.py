"""Read-only database permission report; never prints connection credentials."""
import argparse
import json
import os
from dotenv import load_dotenv
from sqlalchemy import text
from .database import Database


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--env-file', default='.env.cloud.local')
    args = parser.parse_args()
    load_dotenv(args.env_file, override=False)
    database = Database(os.environ['XH_DATABASE_URL'])
    try:
        with database.transaction(readonly=True) as db:
            role = dict(db.execute(text('SELECT current_user AS name, rolsuper, rolbypassrls, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname=current_user')).mappings().one())
            tables = [dict(row) for row in db.execute(text("SELECT c.relname AS name, c.relrowsecurity AS rls, pg_get_userbyid(c.relowner)=current_user AS runtime_owns_table FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r' AND left(c.relname,3)='xh_' ORDER BY c.relname")).mappings()]
            policies = [dict(row) for row in db.execute(text("SELECT tablename, policyname, roles, cmd FROM pg_policies WHERE schemaname='public' AND left(tablename,3)='xh_'" )).mappings()]
        print(json.dumps({'role': role, 'tables': tables, 'policies': policies}))
    except Exception as error:
        print(json.dumps({'success': False, 'errorType': type(error).__name__}))
        raise SystemExit(1)
    finally:
        database.engine.dispose()


if __name__ == '__main__':
    main()
