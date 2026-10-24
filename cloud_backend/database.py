"""Short-lived transactions suitable for the Supabase transaction pooler."""
from contextlib import contextmanager
from sqlalchemy import create_engine, text, event, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool


class Database:
    def __init__(self, url, *, testing=False):
        parsed = make_url(url)
        options = {}
        if parsed.drivername in ('postgres', 'postgresql', 'postgresql+psycopg'):
            parsed = parsed.set(drivername='postgresql+psycopg')
            # Prepared statements cannot outlive a transaction-pooler connection.
            import os
            tls = {'sslmode': 'require'}
            if os.environ.get('XH_DATABASE_CA_FILE'):
                tls = {'sslmode': 'verify-full', 'sslrootcert': os.environ['XH_DATABASE_CA_FILE']}
            options = {'connect_args': {'prepare_threshold': None, 'connect_timeout': 8,
                       **tls}, 'poolclass': NullPool, 'hide_parameters': True}
        elif parsed.drivername.startswith('sqlite') and testing:
            options = {'connect_args': {'check_same_thread': False}, 'poolclass': NullPool}
            if ':memory:' in str(parsed):
                from sqlalchemy.pool import StaticPool
                options['poolclass'] = StaticPool
        else:
            raise ValueError('Cloud cần PostgreSQL. SQLite chỉ dành cho kiểm thử riêng.')
        self.engine = create_engine(parsed, **options)
        if parsed.drivername.startswith('sqlite'):
            @event.listens_for(self.engine, 'connect')
            def foreign_keys(connection, _):
                connection.execute('PRAGMA foreign_keys=ON')
        self.testing = testing

    @contextmanager
    def transaction(self, *, readonly=False, serialized=True):
        with self.engine.begin() as connection:
            # Trial traffic is small. Serialize mutations across *all* function
            # instances; process locks do not protect serverless concurrency.
            if connection.dialect.name == 'postgresql':
                if readonly:
                    connection.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
                connection.execute(text("SET LOCAL statement_timeout = '15000'"))
                connection.execute(text("SET LOCAL lock_timeout = '8000'"))
                if not readonly and serialized:
                    connection.execute(text('SELECT pg_advisory_xact_lock(20261016, 8765)'))
            elif connection.dialect.name == 'sqlite':
                connection.exec_driver_sql('BEGIN' if readonly else 'BEGIN IMMEDIATE')
            yield connection

    def install(self):
        from .models import metadata
        metadata.create_all(self.engine)
        with self.transaction() as connection:
            if 'deleted_at' not in {column['name'] for column in inspect(connection).get_columns('xh_users')}:
                connection.execute(text('ALTER TABLE xh_users ADD COLUMN deleted_at VARCHAR(50)'))
        if self.engine.dialect.name == 'postgresql':
            with self.engine.begin() as connection:
                for table in metadata.sorted_tables:
                    # A server database connection owns these tables. The public
                    # Supabase anon/authenticated REST roles receive no access.
                    name = connection.dialect.identifier_preparer.quote(table.name)
                    connection.execute(text(f'ALTER TABLE {name} ENABLE ROW LEVEL SECURITY'))
                    connection.execute(text(f'REVOKE ALL ON TABLE {name} FROM PUBLIC, anon, authenticated'))
