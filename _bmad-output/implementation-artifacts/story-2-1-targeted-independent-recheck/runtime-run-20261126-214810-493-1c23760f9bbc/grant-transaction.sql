SET LOCAL lock_timeout = '8s';
SET LOCAL statement_timeout = '20s';
SELECT (current_database()='lab_booking' AND current_user='lab_booking_migrator'
          AND session_user='lab_booking_migrator' AND pg_catalog.host(pg_catalog.inet_server_addr())='127.0.0.1'
          AND pg_catalog.inet_server_port()=5433 AND current_setting('server_version_num')='170012'
          AND current_schema()='public' AND current_schemas(false)=ARRAY['public']::name[]) AS ok
\gset env_
\if :env_ok
\else
SELECT 1 / 0;
\endif
LOCK TABLE public.reservations_reservation,public.audit_operationhistory IN SHARE ROW EXCLUSIVE MODE;
WITH mm AS (WITH wanted(table_name, operation, col_names) AS (
  VALUES
    ('reservations_reservation', 'SELECT',
      ARRAY['id','applicant_id','equipment_id','start_at','end_at','status','applied_at']),
    ('reservations_reservation', 'INSERT',
      ARRAY['applicant_id','equipment_id','start_at','end_at','status','applied_at']),
    ('reservations_reservation', 'UPDATE', ARRAY['status']),
    ('audit_operationhistory', 'SELECT', ARRAY['id']),
    ('audit_operationhistory', 'INSERT',
      ARRAY['object_type','reservation_id','equipment_id','action','before_status','after_status',
            'actor_type','actor_id','reason','decision_at','recorded_at'])
), objects AS (
  SELECT c.oid, c.relname::text AS relation_name, c.relowner
  FROM pg_catalog.pg_class AS c
  JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public' AND c.relkind = 'r'
    AND c.relname IN ('reservations_reservation','audit_operationhistory')
), operations(operation) AS (
  VALUES ('SELECT'), ('INSERT'), ('UPDATE'), ('REFERENCES')
)
SELECT o.relation_name, pg_catalog.pg_get_userbyid(o.relowner) AS object_owner,
       a.attname AS column_name, q.operation,
       COALESCE(a.attname::text = ANY(w.col_names), false) AS expected_after,
       pg_catalog.has_column_privilege('lab_booking_app'::pg_catalog.name, o.oid, a.attnum, q.operation) AS effective,
       pg_catalog.has_column_privilege('lab_booking_app'::pg_catalog.name, o.oid, a.attnum,
                                       q.operation || ' WITH GRANT OPTION') AS can_delegate
FROM objects AS o
JOIN pg_catalog.pg_attribute AS a ON a.attrelid = o.oid AND a.attnum > 0 AND NOT a.attisdropped
CROSS JOIN operations AS q
LEFT JOIN wanted AS w ON w.table_name = o.relation_name AND w.operation = q.operation
ORDER BY o.relation_name, a.attnum, q.operation), rawacl AS (SELECT t.relname AS object,a.attname AS column_name,x.grantee,x.grantor,x.privilege_type,x.is_grantable
      FROM pg_catalog.pg_class AS t JOIN pg_catalog.pg_namespace AS n ON n.oid=t.relnamespace
      LEFT JOIN pg_catalog.pg_attribute AS a ON a.attrelid=t.oid AND a.attnum>0 AND NOT a.attisdropped
      CROSS JOIN LATERAL pg_catalog.aclexplode(
        CASE WHEN pg_catalog.cardinality(a.attacl)>0 THEN a.attacl END) AS x
      WHERE n.nspname='public' AND t.relname IN ('reservations_reservation','audit_operationhistory')
      UNION ALL
      SELECT t.relname,NULL,x.grantee,x.grantor,x.privilege_type,x.is_grantable
      FROM pg_catalog.pg_class AS t JOIN pg_catalog.pg_namespace AS n ON n.oid=t.relnamespace
      CROSS JOIN LATERAL pg_catalog.aclexplode(CASE
        WHEN t.relacl IS NULL THEN pg_catalog.acldefault('r',t.relowner)
        WHEN pg_catalog.cardinality(t.relacl)>0 THEN t.relacl END) AS x
      WHERE n.nspname='public' AND t.relname IN ('reservations_reservation','audit_operationhistory') AND x.grantee<>t.relowner), rr AS (SELECT 'lab_booking_app'::regrole::oid AS app,'lab_booking_migrator'::regrole::oid AS owner)
SELECT COALESCE(count(*)=76 AND count(*) FILTER (WHERE m.expected_after)=26 AND bool_and(m.object_owner='lab_booking_migrator' AND NOT m.can_delegate) AND bool_and(NOT m.effective) AND (SELECT bool_and(NOT pg_catalog.has_table_privilege('lab_booking_app'::name,t.oid,p.op)
        AND NOT pg_catalog.has_table_privilege('lab_booking_app'::name,t.oid,p.op||' WITH GRANT OPTION'))
      FROM pg_catalog.pg_class AS t JOIN pg_catalog.pg_namespace AS n ON n.oid=t.relnamespace
      CROSS JOIN (VALUES ('SELECT'),('INSERT'),('UPDATE'),('DELETE'),('TRUNCATE'),('REFERENCES'),
                         ('TRIGGER'),('MAINTAIN')) AS p(op)
      WHERE n.nspname='public' AND t.relname IN ('reservations_reservation','audit_operationhistory')) AND (SELECT pg_catalog.has_schema_privilege('lab_booking_app','public','USAGE')
      AND NOT pg_catalog.has_schema_privilege('lab_booking_app','public','CREATE')
      AND NOT pg_catalog.has_database_privilege('lab_booking_app','lab_booking','CREATE')
      AND NOT pg_catalog.pg_has_role('lab_booking_app','lab_booking_migrator','MEMBER')
      AND NOT(r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls) FROM pg_catalog.pg_roles AS r WHERE r.rolname='lab_booking_app') AND NOT EXISTS (SELECT 1 FROM rawacl),false) AS ok FROM mm AS m
\gset before_
\if :before_ok
GRANT SELECT (id, applicant_id, equipment_id, start_at, end_at, status, applied_at)
ON TABLE public.reservations_reservation TO lab_booking_app;

GRANT INSERT (applicant_id, equipment_id, start_at, end_at, status, applied_at),
      UPDATE (status)
ON TABLE public.reservations_reservation TO lab_booking_app;

GRANT INSERT (object_type, reservation_id, equipment_id, action, before_status, after_status,
              actor_type, actor_id, reason, decision_at, recorded_at),
      SELECT (id)
ON TABLE public.audit_operationhistory TO lab_booking_app;
\else
SELECT 1 / 0;
\endif
WITH mm AS (WITH wanted(table_name, operation, col_names) AS (
  VALUES
    ('reservations_reservation', 'SELECT',
      ARRAY['id','applicant_id','equipment_id','start_at','end_at','status','applied_at']),
    ('reservations_reservation', 'INSERT',
      ARRAY['applicant_id','equipment_id','start_at','end_at','status','applied_at']),
    ('reservations_reservation', 'UPDATE', ARRAY['status']),
    ('audit_operationhistory', 'SELECT', ARRAY['id']),
    ('audit_operationhistory', 'INSERT',
      ARRAY['object_type','reservation_id','equipment_id','action','before_status','after_status',
            'actor_type','actor_id','reason','decision_at','recorded_at'])
), objects AS (
  SELECT c.oid, c.relname::text AS relation_name, c.relowner
  FROM pg_catalog.pg_class AS c
  JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public' AND c.relkind = 'r'
    AND c.relname IN ('reservations_reservation','audit_operationhistory')
), operations(operation) AS (
  VALUES ('SELECT'), ('INSERT'), ('UPDATE'), ('REFERENCES')
)
SELECT o.relation_name, pg_catalog.pg_get_userbyid(o.relowner) AS object_owner,
       a.attname AS column_name, q.operation,
       COALESCE(a.attname::text = ANY(w.col_names), false) AS expected_after,
       pg_catalog.has_column_privilege('lab_booking_app'::pg_catalog.name, o.oid, a.attnum, q.operation) AS effective,
       pg_catalog.has_column_privilege('lab_booking_app'::pg_catalog.name, o.oid, a.attnum,
                                       q.operation || ' WITH GRANT OPTION') AS can_delegate
FROM objects AS o
JOIN pg_catalog.pg_attribute AS a ON a.attrelid = o.oid AND a.attnum > 0 AND NOT a.attisdropped
CROSS JOIN operations AS q
LEFT JOIN wanted AS w ON w.table_name = o.relation_name AND w.operation = q.operation
ORDER BY o.relation_name, a.attnum, q.operation), rawacl AS (SELECT t.relname AS object,a.attname AS column_name,x.grantee,x.grantor,x.privilege_type,x.is_grantable
      FROM pg_catalog.pg_class AS t JOIN pg_catalog.pg_namespace AS n ON n.oid=t.relnamespace
      LEFT JOIN pg_catalog.pg_attribute AS a ON a.attrelid=t.oid AND a.attnum>0 AND NOT a.attisdropped
      CROSS JOIN LATERAL pg_catalog.aclexplode(
        CASE WHEN pg_catalog.cardinality(a.attacl)>0 THEN a.attacl END) AS x
      WHERE n.nspname='public' AND t.relname IN ('reservations_reservation','audit_operationhistory')
      UNION ALL
      SELECT t.relname,NULL,x.grantee,x.grantor,x.privilege_type,x.is_grantable
      FROM pg_catalog.pg_class AS t JOIN pg_catalog.pg_namespace AS n ON n.oid=t.relnamespace
      CROSS JOIN LATERAL pg_catalog.aclexplode(CASE
        WHEN t.relacl IS NULL THEN pg_catalog.acldefault('r',t.relowner)
        WHEN pg_catalog.cardinality(t.relacl)>0 THEN t.relacl END) AS x
      WHERE n.nspname='public' AND t.relname IN ('reservations_reservation','audit_operationhistory') AND x.grantee<>t.relowner), rr AS (SELECT 'lab_booking_app'::regrole::oid AS app,'lab_booking_migrator'::regrole::oid AS owner)
SELECT COALESCE(count(*)=76 AND count(*) FILTER (WHERE m.expected_after)=26 AND bool_and(m.object_owner='lab_booking_migrator' AND NOT m.can_delegate) AND bool_and(m.effective=m.expected_after) AND (SELECT bool_and(NOT pg_catalog.has_table_privilege('lab_booking_app'::name,t.oid,p.op)
        AND NOT pg_catalog.has_table_privilege('lab_booking_app'::name,t.oid,p.op||' WITH GRANT OPTION'))
      FROM pg_catalog.pg_class AS t JOIN pg_catalog.pg_namespace AS n ON n.oid=t.relnamespace
      CROSS JOIN (VALUES ('SELECT'),('INSERT'),('UPDATE'),('DELETE'),('TRUNCATE'),('REFERENCES'),
                         ('TRIGGER'),('MAINTAIN')) AS p(op)
      WHERE n.nspname='public' AND t.relname IN ('reservations_reservation','audit_operationhistory')) AND (SELECT pg_catalog.has_schema_privilege('lab_booking_app','public','USAGE')
      AND NOT pg_catalog.has_schema_privilege('lab_booking_app','public','CREATE')
      AND NOT pg_catalog.has_database_privilege('lab_booking_app','lab_booking','CREATE')
      AND NOT pg_catalog.pg_has_role('lab_booking_app','lab_booking_migrator','MEMBER')
      AND NOT(r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls) FROM pg_catalog.pg_roles AS r WHERE r.rolname='lab_booking_app') AND (SELECT count(*)=26 AND bool_and(r.grantee=k.app AND r.grantor=k.owner AND NOT r.is_grantable AND r.column_name IS NOT NULL) FROM rawacl AS r CROSS JOIN rr AS k),false) AS ok FROM mm AS m
\gset after_
\if :after_ok
\echo STORY21_D041_GRANT_ASSERTIONS_OK
\else
SELECT 1 / 0;
\endif
