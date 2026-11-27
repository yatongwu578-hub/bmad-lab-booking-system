-- Story 2.3 W1. Reviewed proposal only. Run after explicit authorization.
-- psql -X -w -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5433 -U lab_booking_migrator -d lab_booking -f <this file>
\set ON_ERROR_STOP on
BEGIN ISOLATION LEVEL READ COMMITTED;
SET LOCAL search_path = pg_catalog;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '15s';

SELECT (
    pg_catalog.current_database() = 'lab_booking'
    AND session_user = 'lab_booking_migrator'
    AND current_user = 'lab_booking_migrator'
    AND pg_catalog.host(pg_catalog.inet_server_addr()) = '127.0.0.1'
    AND pg_catalog.inet_server_port() = 5433
    AND pg_catalog.current_setting('server_version_num') = '170012'
    AND pg_catalog.current_setting('transaction_read_only') = 'off'
) AS story23_target_ok \gset
\if :story23_target_ok
\else
DO $gate$ BEGIN
    RAISE EXCEPTION 'Story 2.3 authorization refused: wrong database, role, endpoint, or mode';
END; $gate$;
\endif

WITH relation AS (
    SELECT c.oid, c.relnamespace
    FROM pg_catalog.pg_class AS c
    JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relname = 'audit_operationhistory'
      AND c.relkind = 'r'
      AND c.relowner = 'lab_booking_migrator'::pg_catalog.regrole
),
columns AS (
    SELECT a.attname::text AS column_name,
           pg_catalog.has_column_privilege('lab_booking_app'::pg_catalog.name, r.oid, a.attnum, 'SELECT') AS readable,
           pg_catalog.has_column_privilege('lab_booking_app'::pg_catalog.name, r.oid, a.attnum, 'SELECT WITH GRANT OPTION') AS grantable
    FROM relation AS r
    JOIN pg_catalog.pg_attribute AS a ON a.attrelid = r.oid
    WHERE a.attnum > 0 AND NOT a.attisdropped
),
matrix AS (
    SELECT pg_catalog.count(*) = 12 AND pg_catalog.bool_and(NOT x.grantable)
             AND EXISTS (
                 SELECT 1 FROM relation AS r
                 WHERE pg_catalog.has_schema_privilege('lab_booking_app'::pg_catalog.name, r.relnamespace, 'USAGE')
                   AND NOT pg_catalog.has_table_privilege('lab_booking_app'::pg_catalog.name, r.oid, 'SELECT')
                   AND NOT pg_catalog.has_table_privilege('lab_booking_app'::pg_catalog.name, r.oid, 'SELECT WITH GRANT OPTION')
             ) AS safe,
           pg_catalog.array_agg(x.column_name ORDER BY x.column_name COLLATE pg_catalog."C")
               FILTER (WHERE x.readable) AS allowed
    FROM columns AS x
)
SELECT COALESCE(m.safe AND m.allowed = ARRAY['id']::text[], false) AS story23_needs_grant,
       COALESCE(m.safe AND m.allowed = ARRAY['action','actor_type','id','reason','reservation_id']::text[], false) AS story23_exact
FROM matrix AS m \gset
\if :story23_exact
ROLLBACK;
\echo STORY23_HISTORY_SELECT_ALREADY_EXACT
\elif :story23_needs_grant
GRANT SELECT (reservation_id, action, actor_type, reason)
ON TABLE public.audit_operationhistory TO lab_booking_app;

WITH relation AS (
    SELECT c.oid
    FROM pg_catalog.pg_class AS c
    JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relname = 'audit_operationhistory'
      AND c.relkind = 'r'
      AND c.relowner = 'lab_booking_migrator'::pg_catalog.regrole
),
columns AS (
    SELECT a.attname::text AS column_name,
           pg_catalog.has_column_privilege('lab_booking_app'::pg_catalog.name, r.oid, a.attnum, 'SELECT') AS readable,
           pg_catalog.has_column_privilege('lab_booking_app'::pg_catalog.name, r.oid, a.attnum, 'SELECT WITH GRANT OPTION') AS grantable
    FROM relation AS r
    JOIN pg_catalog.pg_attribute AS a ON a.attrelid = r.oid
    WHERE a.attnum > 0 AND NOT a.attisdropped
)
SELECT COALESCE(
    pg_catalog.count(*) = 12 AND pg_catalog.bool_and(NOT x.grantable)
    AND pg_catalog.bool_and(x.readable = (x.column_name IN ('action','actor_type','id','reason','reservation_id')))
    AND pg_catalog.count(*) FILTER (WHERE x.readable) = 5
    AND EXISTS (
        SELECT 1 FROM relation AS r
        WHERE NOT pg_catalog.has_table_privilege('lab_booking_app'::pg_catalog.name, r.oid, 'SELECT')
          AND NOT pg_catalog.has_table_privilege('lab_booking_app'::pg_catalog.name, r.oid, 'SELECT WITH GRANT OPTION')
    ), false) AS story23_post_ok
FROM columns AS x \gset
\if :story23_post_ok
COMMIT;
\echo STORY23_HISTORY_SELECT_COMMITTED
\else
DO $gate$ BEGIN
    RAISE EXCEPTION 'Story 2.3 authorization rolled back: unexpected effective ACL';
END; $gate$;
\endif
\else
DO $gate$ BEGIN
    RAISE EXCEPTION 'Story 2.3 authorization refused: preexisting ACL differs from the reviewed states';
END; $gate$;
\endif
