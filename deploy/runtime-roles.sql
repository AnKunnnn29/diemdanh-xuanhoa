-- Review/run with the database owner AFTER an encrypted restore drill.
-- NOLOGIN group roles only: create separate login credentials in your secret manager.
-- Runtime policies isolate database roles/tables; application checks still enforce GLV scope.
BEGIN;
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='xh_runtime') THEN
    CREATE ROLE xh_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='xh_backup_reader') THEN
    CREATE ROLE xh_backup_reader NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
  END IF;
END $$;
GRANT USAGE ON SCHEMA public TO xh_runtime, xh_backup_reader;
DO $$
DECLARE table_name text;
BEGIN
  FOREACH table_name IN ARRAY ARRAY['xh_settings','xh_users','xh_years','xh_classes','xh_students',
    'xh_assignments','xh_auth_sessions','xh_login_limits','xh_audit','xh_staff_profiles',
    'xh_records','xh_marks','xh_imports','xh_blobs']
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated, xh_runtime, xh_backup_reader', table_name);
    EXECUTE format('GRANT SELECT ON TABLE public.%I TO xh_backup_reader', table_name);
    EXECUTE format('DROP POLICY IF EXISTS xh_backup_read ON public.%I', table_name);
    EXECUTE format('CREATE POLICY xh_backup_read ON public.%I FOR SELECT TO xh_backup_reader USING (true)', table_name);
    EXECUTE format('GRANT SELECT, INSERT ON TABLE public.%I TO xh_runtime', table_name);
    IF table_name NOT IN ('xh_audit','xh_blobs','xh_imports') THEN
      EXECUTE format('GRANT UPDATE ON TABLE public.%I TO xh_runtime', table_name);
    END IF;
    IF table_name IN ('xh_settings','xh_assignments','xh_auth_sessions','xh_login_limits','xh_marks') THEN
      EXECUTE format('GRANT DELETE ON TABLE public.%I TO xh_runtime', table_name);
    END IF;
    EXECUTE format('DROP POLICY IF EXISTS xh_runtime_access ON public.%I', table_name);
    EXECUTE format('CREATE POLICY xh_runtime_access ON public.%I TO xh_runtime USING (true) WITH CHECK (true)', table_name);
  END LOOP;
END $$;
CREATE INDEX IF NOT EXISTS xh_audit_actor_action_stamp ON public.xh_audit(user_id, action, stamp);
CREATE INDEX IF NOT EXISTS xh_limits_window ON public.xh_login_limits(window_start);
-- Do not give the runtime login owner-role membership or use its credential for migrations.
-- Full restore/account restore runs as a separate maintenance identity, not xh_runtime.
COMMIT;
