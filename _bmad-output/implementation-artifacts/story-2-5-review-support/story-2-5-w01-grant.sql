\set ON_ERROR_STOP on
\set VERBOSITY verbose
\if :{?w01_fixture}
\else
\set w01_fixture false
\endif
BEGIN ISOLATION LEVEL READ COMMITTED;
SET LOCAL search_path = pg_catalog;
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '10s';
SELECT set_config('story25.expected_missing', :'expected_missing', true) AS reviewed,
       set_config('story25.fixture', :'w01_fixture', true) AS fixture \gset
DO $w01$
DECLARE
    rel oid;
    app oid := 'lab_booking_app'::regrole;
    target_owner oid := 'lab_booking_migrator'::regrole;
    baseline text[] := ARRAY['id','reservation_id','action','actor_type','reason'];
    permitted text[] := ARRAY['actor_id','before_status','after_status','decision_at','recorded_at'];
    other text[] := ARRAY['object_type','equipment_id'];
    missing_names text[];
    reviewed_names text[] := COALESCE(string_to_array(current_setting('story25.expected_missing'), ','), ARRAY[]::text[]);
    existing_acl jsonb;
    after_acl jsonb;
    expected_acl jsonb;
    table_acl aclitem[];
    fixture boolean := current_setting('story25.fixture')::boolean;
BEGIN
    IF current_database() <> (CASE WHEN fixture THEN 'test_lab_booking' ELSE 'lab_booking' END) OR session_user <> 'lab_booking_migrator'
       OR current_user <> 'lab_booking_migrator' OR host(inet_server_addr()) IS DISTINCT FROM '127.0.0.1'
       OR inet_server_port() IS DISTINCT FROM (CASE WHEN fixture THEN 55435 ELSE 5433 END)
       OR current_setting('server_version_num') <> '170012'
       OR current_setting('transaction_read_only') <> 'off'
       OR EXISTS (SELECT 1 FROM pg_roles AS r WHERE r.oid=app
                  AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls))
       OR pg_has_role(app,target_owner,'USAGE') THEN
        RAISE EXCEPTION 'Unexpected formal endpoint, grantor, or runtime role';
    END IF;
    SELECT c.oid,c.relacl INTO STRICT rel,table_acl FROM pg_class AS c JOIN pg_namespace AS n ON n.oid=c.relnamespace
    WHERE n.nspname='public' AND c.relname='audit_operationhistory' AND c.relkind='r' AND c.relowner=target_owner;
    IF EXISTS (SELECT 1 FROM unnest(ARRAY['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER','MAINTAIN']) AS p(priv)
               WHERE has_table_privilege(app,rel,p.priv))
       OR (SELECT count(*) FROM pg_attribute AS a WHERE a.attrelid=rel AND a.attnum>0 AND NOT a.attisdropped) <> 12
       OR EXISTS (SELECT 1 FROM pg_attribute AS a WHERE a.attrelid=rel AND a.attnum>0 AND NOT a.attisdropped
                  AND (a.attname::text <> ALL(baseline||permitted||other)
                       OR has_column_privilege(app,rel,a.attnum,'SELECT WITH GRANT OPTION')
                       OR has_column_privilege(app,rel,a.attnum,'UPDATE')
                       OR has_column_privilege(app,rel,a.attnum,'REFERENCES')
                       OR has_column_privilege(app,rel,a.attnum,'INSERT WITH GRANT OPTION')
                       OR has_column_privilege(app,rel,a.attnum,'INSERT') IS DISTINCT FROM (a.attname::text<>'id')
                       OR (a.attname::text=ANY(baseline) AND NOT has_column_privilege(app,rel,a.attnum,'SELECT'))
                       OR (a.attname::text=ANY(other) AND has_column_privilege(app,rel,a.attnum,'SELECT')))) THEN
        RAISE EXCEPTION 'Unexpected current history ACL; no grant applied';
    END IF;
    SELECT COALESCE(array_agg(x.col ORDER BY x.col COLLATE "C"), ARRAY[]::text[]) INTO missing_names
    FROM unnest(permitted) AS x(col) WHERE NOT has_column_privilege(app,rel,x.col,'SELECT');
    -- The psql input is a set contract, not a cross-language serialization of sort order.
    IF EXISTS (SELECT 1 FROM unnest(reviewed_names) AS x(col) WHERE x.col <> ALL(permitted))
       OR cardinality(reviewed_names) <> (SELECT count(DISTINCT x.col) FROM unnest(reviewed_names) AS x(col))
       OR NOT (missing_names @> reviewed_names AND missing_names <@ reviewed_names) THEN
        RAISE EXCEPTION 'Current ACL set differs from the approved readback; no grant applied';
    END IF;
    IF EXISTS (SELECT 1 FROM public.reservations_reservation AS r
               WHERE r.status='pending' AND r.start_at<=clock_timestamp()+interval '20 minutes') THEN
        RAISE EXCEPTION 'FR-018 risk in full query scope; no grant applied';
    END IF;
    SELECT COALESCE(jsonb_agg(x.item), '[]'::jsonb) INTO existing_acl
    FROM pg_attribute AS a
    CROSS JOIN LATERAL aclexplode(CASE WHEN cardinality(a.attacl)>0 THEN a.attacl END) AS g
    CROSS JOIN LATERAL (SELECT jsonb_build_array(a.attname::text,g.grantee,g.grantor,g.privilege_type,g.is_grantable) AS item) AS x
    WHERE a.attrelid=rel AND a.attnum>0 AND NOT a.attisdropped;
    IF cardinality(missing_names)>0 THEN
        EXECUTE format('GRANT SELECT (%s) ON TABLE public.audit_operationhistory TO lab_booking_app',
                       (SELECT string_agg(quote_ident(x.col), ', ' ORDER BY x.ord)
                        FROM unnest(missing_names) WITH ORDINALITY AS x(col,ord)));
    END IF;
    SELECT COALESCE(jsonb_agg(x.item ORDER BY x.item), '[]'::jsonb) INTO after_acl
    FROM pg_attribute AS a
    CROSS JOIN LATERAL aclexplode(CASE WHEN cardinality(a.attacl)>0 THEN a.attacl END) AS g
    CROSS JOIN LATERAL (SELECT jsonb_build_array(a.attname::text,g.grantee,g.grantor,g.privilege_type,g.is_grantable) AS item) AS x
    WHERE a.attrelid=rel AND a.attnum>0 AND NOT a.attisdropped;
    SELECT COALESCE(jsonb_agg(x.item ORDER BY x.item), '[]'::jsonb) INTO expected_acl
    FROM (SELECT e.value AS item FROM jsonb_array_elements(existing_acl) AS e
          UNION ALL
          SELECT jsonb_build_array(m.col,app,target_owner,'SELECT',false) FROM unnest(missing_names) AS m(col)) AS x;
    IF after_acl IS DISTINCT FROM expected_acl
       OR (SELECT c.relacl FROM pg_class AS c WHERE c.oid=rel) IS DISTINCT FROM table_acl
       OR has_table_privilege(app,rel,'SELECT')
       OR EXISTS (SELECT 1 FROM pg_attribute AS a WHERE a.attrelid=rel AND a.attnum>0 AND NOT a.attisdropped
                  AND (has_column_privilege(app,rel,a.attnum,'SELECT') IS DISTINCT FROM (a.attname::text=ANY(baseline||permitted))
                       OR has_column_privilege(app,rel,a.attnum,'SELECT WITH GRANT OPTION'))) THEN
        RAISE EXCEPTION 'Unexpected post-grant history ACL; transaction will roll back';
    END IF;
    RAISE NOTICE 'W01 exact SELECT delta count=%', cardinality(missing_names);
END
$w01$;
COMMIT;
\echo STORY25_W01_GRANT_COMMITTED
