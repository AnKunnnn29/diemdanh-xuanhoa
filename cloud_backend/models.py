"""Cloud-owned relational data. Schema is installed explicitly, never on a request."""
from sqlalchemy import (MetaData, Table, Column, String, Text, Integer, Float,
                        Boolean, JSON, LargeBinary, ForeignKey, ForeignKeyConstraint, Index, UniqueConstraint)

metadata = MetaData()
settings = Table('xh_settings', metadata, Column('key', String(100), primary_key=True), Column('value', JSON, nullable=False))
users = Table('xh_users', metadata,
    Column('id', String(64), primary_key=True), Column('username', String(100), unique=True, nullable=False),
    Column('display_name', String(150), nullable=False), Column('role', String(10), nullable=False),
    Column('password_hash', Text, nullable=False), Column('active', Boolean, nullable=False, default=True),
    Column('must_change', Boolean, nullable=False, default=True), Column('revision', Integer, nullable=False, default=1),
    Column('created_at', String(50), nullable=False), Column('deleted_at', String(50)))
years = Table('xh_years', metadata, Column('id', String(64), primary_key=True),
    Column('label', String(20), nullable=False), Column('active', Boolean, nullable=False), Column('created_at', String(50), nullable=False))
classes = Table('xh_classes', metadata,
    Column('id', String(64), primary_key=True), Column('year_id', ForeignKey('xh_years.id'), primary_key=True),
    Column('name', String(100), nullable=False), Column('archived', Boolean, nullable=False, default=False),
    Column('payload', JSON, nullable=False), Column('revision', Integer, nullable=False, default=1),
    UniqueConstraint('year_id', 'name', name='xh_unique_class_name'))
students = Table('xh_students', metadata,
    Column('year_id', ForeignKey('xh_years.id'), primary_key=True), Column('code', String(40), primary_key=True),
    Column('class_id', String(64), nullable=False), Column('payload', JSON, nullable=False),
    Column('revision', Integer, nullable=False, default=1),
    ForeignKeyConstraint(['year_id', 'class_id'], ['xh_classes.year_id', 'xh_classes.id']))
Index('xh_students_class', students.c.year_id, students.c.class_id)
assignments = Table('xh_assignments', metadata,
    Column('year_id', ForeignKey('xh_years.id'), primary_key=True), Column('class_id', String(64), primary_key=True),
    Column('slot', String(20), primary_key=True), Column('user_id', ForeignKey('xh_users.id'), nullable=False),
    ForeignKeyConstraint(['year_id', 'class_id'], ['xh_classes.year_id', 'xh_classes.id']))
sessions = Table('xh_auth_sessions', metadata,
    Column('token_hash', String(64), primary_key=True), Column('user_id', ForeignKey('xh_users.id'), nullable=False),
    Column('csrf', String(100), nullable=False), Column('expires', Float, nullable=False), Column('last_seen', Float, nullable=False))
limits = Table('xh_login_limits', metadata,
    Column('key', String(64), primary_key=True), Column('attempts', Integer, nullable=False), Column('window_start', Float, nullable=False))
Index('xh_limits_window', limits.c.window_start)
audit = Table('xh_audit', metadata,
    Column('id', String(64), primary_key=True), Column('user_id', String(64)), Column('action', String(100), nullable=False),
    Column('stamp', String(50), nullable=False), Column('details', JSON, nullable=False))
Index('xh_audit_actor_action_stamp', audit.c.user_id, audit.c.action, audit.c.stamp)
staff = Table('xh_staff_profiles', metadata,
    Column('id', String(64), primary_key=True), Column('user_id', ForeignKey('xh_users.id'), unique=True), Column('payload', JSON, nullable=False))
records = Table('xh_records', metadata,
    Column('year_id', ForeignKey('xh_years.id'), primary_key=True), Column('kind', String(60), primary_key=True),
    Column('id', String(100), primary_key=True), Column('payload', JSON, nullable=False), Column('revision', Integer, nullable=False, default=1))
marks = Table('xh_marks', metadata,
    Column('year_id', ForeignKey('xh_years.id'), primary_key=True), Column('code', String(40), primary_key=True),
    Column('day', String(10), primary_key=True), Column('activity', String(20), primary_key=True),
    Column('status', String(1), nullable=False), Column('stamp', String(50)), Column('source', String(100)))
imports = Table('xh_imports', metadata,
    Column('digest', String(64), primary_key=True), Column('stamp', String(50), nullable=False), Column('report', JSON, nullable=False))
blobs = Table('xh_blobs', metadata,
    Column('digest', String(64), primary_key=True), Column('content', LargeBinary, nullable=False),
    Column('size', Integer, nullable=False), Column('created_at', String(50), nullable=False))
