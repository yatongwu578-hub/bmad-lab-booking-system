-- D-035 only. Run as one transaction with psql -X -w -v ON_ERROR_STOP=1 --single-transaction.
SET LOCAL search_path = pg_catalog, public;
DO $verify$
DECLARE
    p text;
    field text;
    phase int;
    tbl oid := pg_catalog.to_regclass('public.equipment_equipment');
    app name := 'lab_booking_app';
    seq_name text;
    fields text[] := ARRAY['id','number','name','category','location','description','status'];
    editable text[] := ARRAY['name','category','location','description'];
    matrix jsonb;
    inherited_before jsonb;
    inherited_now jsonb;
BEGIN
    IF current_database() <> 'lab_booking'
      OR session_user <> 'lab_booking_migrator' OR current_user <> 'lab_booking_migrator'
      OR host(inet_server_addr()) IS DISTINCT FROM '127.0.0.1'
      OR inet_server_port() IS DISTINCT FROM 5433
      OR current_setting('server_version_num') <> '170012'
    THEN RAISE EXCEPTION 'Unexpected database, role, endpoint or version'; END IF;
    IF (SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid=tbl AND relkind='r')
       IS DISTINCT FROM 'lab_booking_migrator'
    THEN RAISE EXCEPTION 'Unexpected equipment table owner'; END IF;
    IF (SELECT array_agg(attname::text ORDER BY attnum) FROM pg_attribute
        WHERE attrelid=tbl AND attnum>0 AND NOT attisdropped) IS DISTINCT FROM fields
    THEN RAISE EXCEPTION 'Unexpected equipment columns'; END IF;
    IF (SELECT count(*) FROM public.django_migrations AS dm WHERE dm.app='equipment' AND dm.name='0001_initial') <> 1
    THEN RAISE EXCEPTION 'Equipment migration baseline is missing'; END IF;
    seq_name := pg_get_serial_sequence('public.equipment_equipment','id');
    RAISE NOTICE 'verified_target=lab_booking endpoint=127.0.0.1:5433 version=17.12 owner=%',current_user;
    FOR phase IN 0..1 LOOP
        IF phase = 1 THEN
            EXECUTE 'GRANT UPDATE (name, category, location, description) ON TABLE public.equipment_equipment TO lab_booking_app';
        END IF;
        SELECT coalesce(jsonb_agg(rolname ORDER BY rolname),'[]'::jsonb) INTO inherited_now
          FROM pg_roles WHERE rolname <> app AND pg_has_role((SELECT r.oid FROM pg_roles r WHERE r.rolname=app),oid,'USAGE');
        IF phase = 0 THEN inherited_before := inherited_now;
        ELSIF inherited_before IS DISTINCT FROM inherited_now THEN RAISE EXCEPTION 'Inherited roles changed';
        END IF;
        RAISE NOTICE 'inherited_roles_phase_%=%',phase,inherited_now;
        IF seq_name IS NULL OR has_sequence_privilege(app,seq_name,'USAGE,SELECT,UPDATE')
          OR has_schema_privilege(app,'public','CREATE')
          OR has_database_privilege(app,'lab_booking','CREATE')
          OR NOT has_schema_privilege(app,'public','USAGE')
          OR (SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls
                FROM pg_roles WHERE rolname=app) IS DISTINCT FROM false
          OR NOT has_column_privilege(app,'public.accounts_user','id','SELECT')
          OR NOT has_column_privilege(app,'public.accounts_user','is_active','SELECT')
          OR NOT has_column_privilege(app,'public.accounts_user','role','SELECT')
        THEN RAISE EXCEPTION 'Unexpected role, schema, sequence or account-read rights'; END IF;
        FOREACH p IN ARRAY ARRAY['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER','MAINTAIN'] LOOP
            IF has_table_privilege(app,tbl,p) OR has_table_privilege(app,tbl,p || ' WITH GRANT OPTION')
            THEN RAISE EXCEPTION 'Unexpected effective table privilege: %',p; END IF;
        END LOOP;
        FOREACH field IN ARRAY fields LOOP
            IF NOT has_column_privilege(app,tbl,field,'SELECT')
              OR has_column_privilege(app,tbl,field,'INSERT') IS DISTINCT FROM (field <> 'id')
              OR has_column_privilege(app,tbl,field,'UPDATE') IS DISTINCT FROM (phase = 1 AND field = ANY (editable))
              OR has_column_privilege(app,tbl,field,'REFERENCES')
              OR has_column_privilege(app,tbl,field,'SELECT WITH GRANT OPTION')
              OR has_column_privilege(app,tbl,field,'INSERT WITH GRANT OPTION')
              OR has_column_privilege(app,tbl,field,'UPDATE WITH GRANT OPTION')
              OR has_column_privilege(app,tbl,field,'REFERENCES WITH GRANT OPTION')
            THEN RAISE EXCEPTION 'Unexpected effective column privileges at phase %: %',phase,field; END IF;
        END LOOP;
        SELECT jsonb_object_agg(f,jsonb_build_object('SELECT',has_column_privilege(app,tbl,f,'SELECT'),
          'INSERT',has_column_privilege(app,tbl,f,'INSERT'),'UPDATE',has_column_privilege(app,tbl,f,'UPDATE')))
          INTO matrix FROM unnest(fields) AS t(f);
        RAISE NOTICE 'effective_acl_phase_%=%',phase,matrix;
    END LOOP;
    RAISE NOTICE 'D035_ACL_ASSERTIONS_PASSED';
END
$verify$;
