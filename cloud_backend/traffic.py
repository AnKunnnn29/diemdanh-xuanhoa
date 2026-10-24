"""Atomic, bounded DB counters shared by all serverless instances."""
import hashlib
import hmac
import time
from sqlalchemy import delete, insert, update, select
from . import models as m
from .security import CloudError


def clock():
    return time.time()


def limit(database, secret, action, user_id, session_hash, address):
    if action in ('auth/logout', 'auth/me'):
        return
    group, maximum, seconds = ('read', 120, 60)
    if action == 'student-contact-view':
        group, maximum = 'contact', 10
    elif action == 'auth/reauth':
        group, maximum, seconds = 'reauth', 5, 900
    elif 'export' in action or action in ('year-file', 'snapshot-part'):
        group, maximum, seconds = 'export', 30 if action.endswith('part') else 5, 900
    elif action in ('scan', 'scan-preview', 'offline-scan'):
        group, maximum = 'scan', 120
    now = clock()
    window = int(now // seconds) * seconds
    retry = max(1, int(window+seconds-now)+1)
    blocked = False
    # Lock only these counter rows (ordered identically), never the business lock.
    with database.transaction(serialized=False) as db:
        db.execute(delete(m.limits).where(m.limits.c.window_start < now-86400))
        dimensions = [('account', user_id, maximum), ('session', session_hash, max(1, maximum//2)),
                      ('ip', address, max(1200, maximum*40))]
        values, caps = [], {}
        for dimension, value, cap in dimensions:
            key = hmac.new(secret.encode(), f'traffic:{group}:{dimension}:{value}:{window}'.encode(), hashlib.sha256).hexdigest()
            values.append({'key': key, 'attempts': 1, 'window_start': window}); caps[key] = cap
        table = m.limits
        if db.dialect.name == 'postgresql':
            from sqlalchemy.dialects.postgresql import insert as upsert
        else:
            from sqlalchemy.dialects.sqlite import insert as upsert
        statement = upsert(table).values(sorted(values, key=lambda row: row['key']))
        counts = db.execute(statement.on_conflict_do_update(index_elements=[table.c.key],
            set_={'attempts': table.c.attempts+1}).returning(table.c.key, table.c.attempts)).all()
        blocked = any(count > caps[key] for key, count in counts)
    if blocked:
        error = CloudError('Đã vượt giới hạn thao tác. Chờ một lúc rồi thử lại.', 429, 'rate_limited')
        error.retry_after = retry
        raise error
