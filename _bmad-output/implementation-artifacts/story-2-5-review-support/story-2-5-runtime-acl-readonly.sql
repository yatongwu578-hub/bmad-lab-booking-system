-- For the later authorized formal window only, using the protected runtime login.
-- Run psql -X -v ON_ERROR_STOP=1, with the connection explicitly pinned to
-- 127.0.0.1:5433/lab_booking as lab_booking_app. This file has no GRANT or DDL.
BEGIN READ ONLY;
DO $check$
BEGIN
    IF current_database() <> 'lab_booking' OR session_user <> 'lab_booking_app'
       OR current_user <> 'lab_booking_app' OR host(inet_server_addr()) IS DISTINCT FROM '127.0.0.1'
       OR inet_server_port() IS DISTINCT FROM 5433
       OR current_setting('server_version_num') <> '170012' THEN
        RAISE EXCEPTION 'Unexpected formal connection identity';
    END IF;
END
$check$;

SELECT current_database() AS db, session_user AS login, current_user AS role_name,
       host(inet_server_addr()) AS host, inet_server_port() AS port,
       current_setting('server_version_num') AS version,
       current_setting('transaction_isolation') AS isolation, current_setting('transaction_read_only') AS read_only;

SELECT p.rolsuper, p.rolcreatedb, p.rolcreaterole, p.rolreplication, p.rolbypassrls
FROM pg_catalog.pg_roles AS p WHERE p.rolname = current_user;

SELECT p.privilege, has_table_privilege(current_user,'public.audit_operationhistory',p.privilege) AS allowed,
       has_table_privilege(current_user,'public.audit_operationhistory',p.privilege || ' WITH GRANT OPTION') AS delegable
FROM (VALUES ('SELECT'),('INSERT'),('UPDATE'),('DELETE'),('TRUNCATE'),('REFERENCES'),('TRIGGER')) AS p(privilege);

SELECT a.attname AS column_name, p.privilege,
       has_column_privilege(current_user,a.attrelid,a.attnum,p.privilege) AS allowed,
       has_column_privilege(current_user,a.attrelid,a.attnum,p.privilege || ' WITH GRANT OPTION') AS delegable,
       CASE WHEN p.privilege = 'SELECT' THEN a.attname IN
           ('id','reservation_id','action','actor_type','reason','actor_id','before_status',
            'after_status','decision_at','recorded_at') END AS expected_select
FROM pg_catalog.pg_attribute AS a
CROSS JOIN (VALUES ('SELECT'),('INSERT'),('UPDATE'),('REFERENCES')) AS p(privilege)
WHERE a.attrelid = 'public.audit_operationhistory'::regclass AND a.attnum > 0 AND NOT a.attisdropped
ORDER BY a.attname, p.privilege;

-- aclexplode is set-returning. A NULL or empty ACL yields no rows, not a malformed ACL.
SELECT a.attname AS column_name, acl.grantee, acl.grantor, acl.privilege_type, acl.is_grantable
FROM pg_catalog.pg_attribute AS a
CROSS JOIN LATERAL pg_catalog.aclexplode(a.attacl) AS acl
WHERE a.attrelid = 'public.audit_operationhistory'::regclass AND a.attnum > 0 AND NOT a.attisdropped
ORDER BY a.attname, acl.grantee, acl.grantor, acl.privilege_type;

SELECT c.relname, acl.grantee, acl.grantor, acl.privilege_type, acl.is_grantable
FROM pg_catalog.pg_class AS c
CROSS JOIN LATERAL pg_catalog.aclexplode(c.relacl) AS acl
WHERE c.oid = 'public.audit_operationhistory'::regclass
ORDER BY acl.grantee, acl.grantor, acl.privilege_type;

SELECT has_schema_privilege(current_user, 'public', 'USAGE') AS schema_usage,
       has_column_privilege(current_user, 'public.accounts_user', 'id', 'SELECT') AS account_id,
       has_column_privilege(current_user, 'public.accounts_user', 'username', 'SELECT') AS account_name,
       has_column_privilege(current_user, 'public.accounts_user', 'is_active', 'SELECT') AS account_active,
       has_column_privilege(current_user, 'public.accounts_user', 'role', 'SELECT') AS account_role;
ROLLBACK;
