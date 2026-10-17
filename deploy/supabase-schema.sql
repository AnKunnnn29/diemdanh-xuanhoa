-- Xuan Hoa cloud v2. No source data or account secrets.

BEGIN;

CREATE TABLE IF NOT EXISTS xh_audit (
	id VARCHAR(64) NOT NULL, 
	user_id VARCHAR(64), 
	action VARCHAR(100) NOT NULL, 
	stamp VARCHAR(50) NOT NULL, 
	details JSON NOT NULL, 
	PRIMARY KEY (id)
);

ALTER TABLE xh_audit ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE xh_audit FROM PUBLIC, anon, authenticated;

CREATE TABLE IF NOT EXISTS xh_blobs (
	digest VARCHAR(64) NOT NULL, 
	content BYTEA NOT NULL, 
	size INTEGER NOT NULL, 
	created_at VARCHAR(50) NOT NULL, 
	PRIMARY KEY (digest)
);

ALTER TABLE xh_blobs ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE xh_blobs FROM PUBLIC, anon, authenticated;

CREATE TABLE IF NOT EXISTS xh_imports (
	digest VARCHAR(64) NOT NULL, 
	stamp VARCHAR(50) NOT NULL, 
	report JSON NOT NULL, 
	PRIMARY KEY (digest)
);

ALTER TABLE xh_imports ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE xh_imports FROM PUBLIC, anon, authenticated;

CREATE TABLE IF NOT EXISTS xh_login_limits (
	key VARCHAR(64) NOT NULL, 
	attempts INTEGER NOT NULL, 
	window_start FLOAT NOT NULL, 
	PRIMARY KEY (key)
);

ALTER TABLE xh_login_limits ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE xh_login_limits FROM PUBLIC, anon, authenticated;

CREATE TABLE IF NOT EXISTS xh_settings (
	key VARCHAR(100) NOT NULL, 
	value JSON NOT NULL, 
	PRIMARY KEY (key)
);

ALTER TABLE xh_settings ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE xh_settings FROM PUBLIC, anon, authenticated;

CREATE TABLE IF NOT EXISTS xh_users (
	id VARCHAR(64) NOT NULL, 
	username VARCHAR(100) NOT NULL, 
	display_name VARCHAR(150) NOT NULL, 
	role VARCHAR(10) NOT NULL, 
	password_hash TEXT NOT NULL, 
	active BOOLEAN NOT NULL, 
	must_change BOOLEAN NOT NULL, 
	revision INTEGER NOT NULL, 
	created_at VARCHAR(50) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (username)
);

ALTER TABLE xh_users ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE xh_users FROM PUBLIC, anon, authenticated;

CREATE TABLE IF NOT EXISTS xh_years (
	id VARCHAR(64) NOT NULL, 
	label VARCHAR(20) NOT NULL, 
	active BOOLEAN NOT NULL, 
	created_at VARCHAR(50) NOT NULL, 
	PRIMARY KEY (id)
);

ALTER TABLE xh_years ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE xh_years FROM PUBLIC, anon, authenticated;

CREATE TABLE IF NOT EXISTS xh_auth_sessions (
	token_hash VARCHAR(64) NOT NULL, 
	user_id VARCHAR(64) NOT NULL, 
	csrf VARCHAR(100) NOT NULL, 
	expires FLOAT NOT NULL, 
	last_seen FLOAT NOT NULL, 
	PRIMARY KEY (token_hash), 
	FOREIGN KEY(user_id) REFERENCES xh_users (id)
);

ALTER TABLE xh_auth_sessions ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE xh_auth_sessions FROM PUBLIC, anon, authenticated;

CREATE TABLE IF NOT EXISTS xh_classes (
	id VARCHAR(64) NOT NULL, 
	year_id VARCHAR(64) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	archived BOOLEAN NOT NULL, 
	payload JSON NOT NULL, 
	revision INTEGER NOT NULL, 
	PRIMARY KEY (id, year_id), 
	CONSTRAINT xh_unique_class_name UNIQUE (year_id, name), 
	FOREIGN KEY(year_id) REFERENCES xh_years (id)
);

ALTER TABLE xh_classes ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE xh_classes FROM PUBLIC, anon, authenticated;

CREATE TABLE IF NOT EXISTS xh_marks (
	year_id VARCHAR(64) NOT NULL, 
	code VARCHAR(40) NOT NULL, 
	day VARCHAR(10) NOT NULL, 
	activity VARCHAR(20) NOT NULL, 
	status VARCHAR(1) NOT NULL, 
	stamp VARCHAR(50), 
	source VARCHAR(100), 
	PRIMARY KEY (year_id, code, day, activity), 
	FOREIGN KEY(year_id) REFERENCES xh_years (id)
);

ALTER TABLE xh_marks ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE xh_marks FROM PUBLIC, anon, authenticated;

CREATE TABLE IF NOT EXISTS xh_records (
	year_id VARCHAR(64) NOT NULL, 
	kind VARCHAR(60) NOT NULL, 
	id VARCHAR(100) NOT NULL, 
	payload JSON NOT NULL, 
	revision INTEGER NOT NULL, 
	PRIMARY KEY (year_id, kind, id), 
	FOREIGN KEY(year_id) REFERENCES xh_years (id)
);

ALTER TABLE xh_records ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE xh_records FROM PUBLIC, anon, authenticated;

CREATE TABLE IF NOT EXISTS xh_staff_profiles (
	id VARCHAR(64) NOT NULL, 
	user_id VARCHAR(64), 
	payload JSON NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES xh_users (id)
);

ALTER TABLE xh_staff_profiles ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE xh_staff_profiles FROM PUBLIC, anon, authenticated;

CREATE TABLE IF NOT EXISTS xh_assignments (
	year_id VARCHAR(64) NOT NULL, 
	class_id VARCHAR(64) NOT NULL, 
	slot VARCHAR(20) NOT NULL, 
	user_id VARCHAR(64) NOT NULL, 
	PRIMARY KEY (year_id, class_id, slot), 
	FOREIGN KEY(year_id, class_id) REFERENCES xh_classes (year_id, id), 
	FOREIGN KEY(year_id) REFERENCES xh_years (id), 
	FOREIGN KEY(user_id) REFERENCES xh_users (id)
);

ALTER TABLE xh_assignments ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE xh_assignments FROM PUBLIC, anon, authenticated;

CREATE TABLE IF NOT EXISTS xh_students (
	year_id VARCHAR(64) NOT NULL, 
	code VARCHAR(40) NOT NULL, 
	class_id VARCHAR(64) NOT NULL, 
	payload JSON NOT NULL, 
	revision INTEGER NOT NULL, 
	PRIMARY KEY (year_id, code), 
	FOREIGN KEY(year_id, class_id) REFERENCES xh_classes (year_id, id), 
	FOREIGN KEY(year_id) REFERENCES xh_years (id)
);

CREATE INDEX IF NOT EXISTS xh_students_class ON xh_students (year_id, class_id);

ALTER TABLE xh_students ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE xh_students FROM PUBLIC, anon, authenticated;

COMMIT;
