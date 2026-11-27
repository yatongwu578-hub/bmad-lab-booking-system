-- Read-only. No migrations, GRANT, account writes, or FR-018.
\set ON_ERROR_STOP on
\set VERBOSITY verbose
\if :{?w01_fixture}
\else
\set w01_fixture false
\endif
\if :{?w01_capture}
\else
\set w01_capture false
\endif
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '5s';
SET LOCAL lock_timeout = '2s';
SET LOCAL search_path = pg_catalog;
SET LOCAL TIME ZONE 'UTC';
SELECT set_config('story25.fixture', :'w01_fixture', true) AS fixture \gset
DO $guard$
DECLARE
    fixture boolean := current_setting('story25.fixture')::boolean;
BEGIN
    IF current_database() <> (CASE WHEN fixture THEN 'test_lab_booking' ELSE 'lab_booking' END) OR session_user <> 'lab_booking_app'
       OR current_user <> 'lab_booking_app'
       OR host(inet_server_addr()) IS DISTINCT FROM '127.0.0.1'
       OR inet_server_port() IS DISTINCT FROM (CASE WHEN fixture THEN 55435 ELSE 5433 END)
       OR current_setting('server_version_num') <> '170012'
       OR current_setting('transaction_read_only') <> 'on'
       OR EXISTS (SELECT 1 FROM pg_catalog.pg_roles AS r WHERE r.rolname = current_user
                   AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls))
    THEN
        RAISE EXCEPTION 'Unexpected or elevated formal PostgreSQL connection';
    END IF;
END
$guard$;

SELECT 'identity|' || json_build_object(
    'database', current_database(), 'login', session_user, 'role', current_user,
    'role_oid', to_regrole(current_user::text)::oid,
    'host', host(inet_server_addr()), 'port', inet_server_port(), 'version', current_setting('server_version_num'),
    'isolation', current_setting('transaction_isolation'), 'read_only', current_setting('transaction_read_only'));

SELECT 'history_table|' || json_build_object(
    'name', c.relname, 'owner', pg_get_userbyid(c.relowner), 'caller_owns', pg_has_role(c.relowner, 'USAGE'),
    'select', has_table_privilege(current_user,c.oid,'SELECT'),
    'select_grantable', has_table_privilege(current_user,c.oid,'SELECT WITH GRANT OPTION'),
    'insert', has_table_privilege(current_user,c.oid,'INSERT'),
    'update', has_table_privilege(current_user,c.oid,'UPDATE'),
    'delete', has_table_privilege(current_user,c.oid,'DELETE'),
    'truncate', has_table_privilege(current_user,c.oid,'TRUNCATE'),
    'references', has_table_privilege(current_user,c.oid,'REFERENCES'),
    'trigger', has_table_privilege(current_user,c.oid,'TRIGGER'),
    'maintain', has_table_privilege(current_user,c.oid,'MAINTAIN'))
FROM pg_class AS c WHERE c.oid = 'public.audit_operationhistory'::regclass;

SELECT 'history_columns|' || COALESCE(json_agg(json_build_object(
    'column', a.attname, 'select', has_column_privilege(current_user,a.attrelid,a.attnum,'SELECT'),
    'select_grantable', has_column_privilege(current_user,a.attrelid,a.attnum,'SELECT WITH GRANT OPTION'),
    'insert', has_column_privilege(current_user,a.attrelid,a.attnum,'INSERT'),
    'insert_grantable', has_column_privilege(current_user,a.attrelid,a.attnum,'INSERT WITH GRANT OPTION'),
    'update', has_column_privilege(current_user,a.attrelid,a.attnum,'UPDATE'),
    'references', has_column_privilege(current_user,a.attrelid,a.attnum,'REFERENCES'))
    ORDER BY a.attname), '[]'::json)
FROM pg_attribute AS a
WHERE a.attrelid = 'public.audit_operationhistory'::regclass AND a.attnum > 0 AND NOT a.attisdropped;

SELECT 'history_explicit|' || COALESCE(json_agg(json_build_object(
    'column', x.column_name, 'grantee', x.grantee, 'grantor', x.grantor,
    'privilege', x.privilege_type, 'grantable', x.is_grantable)
    ORDER BY x.column_name, x.grantee, x.grantor, x.privilege_type), '[]'::json)
FROM (
    SELECT a.attname::text AS column_name, acl.grantee, acl.grantor, acl.privilege_type, acl.is_grantable
    FROM pg_attribute AS a CROSS JOIN LATERAL aclexplode(CASE WHEN cardinality(a.attacl)>0 THEN a.attacl END) AS acl
    WHERE a.attrelid = 'public.audit_operationhistory'::regclass AND a.attnum > 0 AND NOT a.attisdropped
    UNION ALL
    SELECT ''::text, acl.grantee, acl.grantor, acl.privilege_type, acl.is_grantable
    FROM pg_class AS c CROSS JOIN LATERAL aclexplode(CASE WHEN cardinality(c.relacl)>0 THEN c.relacl END) AS acl
    WHERE c.oid = 'public.audit_operationhistory'::regclass
) AS x;

SELECT 'existing_rights|' || json_build_object(
    'account_projection', has_schema_privilege(current_user,'public','USAGE')
        AND NOT EXISTS (SELECT 1 FROM unnest(ARRAY['id','username','role','is_active','is_staff','is_superuser','password','last_login']) AS x(column_name)
                         WHERE NOT has_column_privilege(current_user,'public.accounts_user',x.column_name,'SELECT')),
    'native_login_write', has_column_privilege(current_user,'public.accounts_user','last_login','UPDATE'),
    'reservation_projection', NOT EXISTS (
        SELECT 1 FROM unnest(ARRAY['id','equipment_id','applicant_id','status','start_at','end_at','applied_at']) AS x(column_name)
        WHERE NOT has_column_privilege(current_user,'public.reservations_reservation',x.column_name,'SELECT')),
    'equipment_projection', NOT EXISTS (
        SELECT 1 FROM unnest(ARRAY['id','number','name','category','location','description','status']) AS x(column_name)
        WHERE NOT has_column_privilege(current_user,'public.equipment_equipment',x.column_name,'SELECT')),
    'equipment_row_lock', has_any_column_privilege(current_user,'public.equipment_equipment','UPDATE'),
    'reservation_expiry_update', has_column_privilege(current_user,'public.reservations_reservation','status','UPDATE'),
    'session_rights', NOT EXISTS (SELECT 1 FROM unnest(ARRAY['SELECT','INSERT','UPDATE','DELETE']) AS x(privilege)
                                  WHERE NOT has_table_privilege(current_user,'public.django_session',x.privilege)));

-- Sample survey runs only if all pre-existing SELECT rights for the survey are effective.
-- Every candidate is read without invoking Django or FR-018. No personal names or reasons.
WITH observed AS MATERIALIZED (
    SELECT clock_timestamp() AS instant
), horizon AS (
    SELECT o.instant, o.instant + interval '20 minutes' AS safe_until FROM observed AS o
), row_flags AS MATERIALIZED (
    SELECT r.id, r.equipment_id, r.status, r.start_at, r.end_at,
           r.status = 'pending' AND r.start_at <= h.safe_until AS risky,
           r.end_at > h.instant AND (r.status = 'approved' OR
               (r.status = 'pending' AND r.start_at > h.instant)) AS effective
    FROM public.reservations_reservation AS r CROSS JOIN horizon AS h
), scoped_devices AS (
    SELECT e.id, e.number,
           count(f.id) FILTER (WHERE f.risky) AS unsafe_pending,
           count(f.id) FILTER (WHERE f.effective) AS affected,
           COALESCE(min(f.id) FILTER (WHERE f.effective AND f.id=2),
                    min(f.id) FILTER (WHERE f.effective)) AS detail_id
    FROM public.equipment_equipment AS e LEFT JOIN row_flags AS f ON f.equipment_id = e.id
    GROUP BY e.id, e.number
), detail_pick AS (
    SELECT f.id, f.equipment_id, f.status,
           EXISTS (SELECT 1 FROM public.audit_operationhistory AS h WHERE h.reservation_id=f.id) AS has_history
    FROM row_flags AS f WHERE NOT f.risky
    ORDER BY has_history DESC, (f.id=1) DESC, (f.status <> 'pending') DESC, f.id
    LIMIT 1
), filter_pick AS (
    SELECT d.id,d.number,d.affected,d.detail_id FROM scoped_devices AS d
    WHERE d.unsafe_pending=0 ORDER BY (d.detail_id=2) DESC NULLS LAST,(d.affected>0) DESC,d.id LIMIT 1
)
SELECT 'samples|' || json_build_object(
    'at', h.instant, 'safe_until', h.safe_until,
    'full_unsafe_pending', (SELECT count(*) FROM row_flags AS f WHERE f.risky),
    'status_counts', (SELECT COALESCE(json_object_agg(c.status,c.n), '{}'::json)
                      FROM (SELECT f.status,count(*) n FROM row_flags AS f GROUP BY f.status) AS c),
    'active_roles', (SELECT COALESCE(json_object_agg(g.role,g.n), '{}'::json)
                     FROM (SELECT u.role,count(*) n FROM public.accounts_user AS u
                           WHERE u.is_active GROUP BY u.role) AS g),
    'detail', (SELECT row_to_json(d) FROM detail_pick AS d),
    'filter', (SELECT row_to_json(d) FROM filter_pick AS d))
FROM horizon AS h;
\if :w01_capture
\ir story-2-5-w01-snapshot.sql
\endif
ROLLBACK;
SELECT 'complete|STORY25_W01_SQL_READONLY_OK';
