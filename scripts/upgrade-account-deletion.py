"""Add the nullable deletion marker without changing existing accounts."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import inspect, text
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cloud_backend.database import Database

load_dotenv('.env.cloud.local')
database = Database(os.environ['XH_DATABASE_URL'])
try:
    with database.transaction() as db:
        before = list(db.execute(text('SELECT id, username, password_hash, active, role FROM xh_users ORDER BY id')))
        if 'deleted_at' not in {c['name'] for c in inspect(db).get_columns('xh_users')}:
            db.execute(text('ALTER TABLE xh_users ADD COLUMN deleted_at VARCHAR(50)'))
        assert before == list(db.execute(text('SELECT id, username, password_hash, active, role FROM xh_users ORDER BY id')))
    print('Account deletion schema ready; existing accounts unchanged; no secrets printed.')
finally:
    database.engine.dispose()
