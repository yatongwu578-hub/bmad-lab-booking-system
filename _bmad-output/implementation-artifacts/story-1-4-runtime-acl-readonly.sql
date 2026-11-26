-- D-035 recovery. Call as lab_booking_migrator within BEGIN READ ONLY.
SET LOCAL search_path = pg_catalog, public;
SET LOCAL client_min_messages = notice;
DO $verify$
DECLARE
    v_role name := 'lab_booking_app';
    v_tbl oid := pg_catalog.to_regclass('public.equipment_equipment');
    v_fields text[] := ARRAY['id','number','name','category','location','description','status'];
    v_allowed text[] := ARRAY['name','category','location','description'];
    v_updates text[] := ARRAY[]::text[];
    v_seq text;
    v_priv text;
    v_col text;
    v_state text;
    v_role_id oid;
    v_inherited jsonb;
    v_matrix jsonb;
BEGIN
    IF current_database() <> 'lab_booking'
      OR session_user <> 'lab_booking_migrator' OR current_user <> 'lab_booking_migrator'
      OR host(inet_server_addr()) IS DISTINCT FROM '127.0.0.1'
      OR inet_server_port() IS DISTINCT FROM 5433
      OR current_setting('server_version_num') <> '170012'
      OR current_setting('transaction_read_only') <> 'on'
    THEN RAISE EXCEPTION 'Unexpected database, role, endpoint, version or transaction mode'; END IF;
    IF (SELECT pg_get_userbyid(pc.relowner) FROM pg_class AS pc WHERE pc.oid=v_tbl AND pc.relkind='r')
        IS DISTINCT FROM 'lab_booking_migrator'
    THEN RAISE EXCEPTION 'Unexpected equipment table owner'; END IF;
    IF (SELECT array_agg(pa.attname::text ORDER BY pa.attnum) FROM pg_attribute AS pa
        WHERE pa.attrelid=v_tbl AND pa.attnum>0 AND NOT pa.attisdropped) IS DISTINCT FROM v_fields
    THEN RAISE EXCEPTION 'Unexpected equipment columns'; END IF;
    IF (SELECT count(*) FROM public.django_migrations AS dm WHERE dm.app='equipment' AND dm.name='0001_initial') <> 1
    THEN RAISE EXCEPTION 'Equipment migration baseline is missing'; END IF;
    RAISE NOTICE 'verified_target=lab_booking endpoint=127.0.0.1:5433 version=17.12 owner=% transaction=read-only',current_user;

    SELECT r.oid INTO v_role_id FROM pg_roles AS r WHERE r.rolname=v_role
      AND NOT (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls);
    v_seq := pg_get_serial_sequence('public.equipment_equipment','id');
    IF v_role_id IS NULL OR v_seq IS NULL OR has_sequence_privilege(v_role,v_seq,'USAGE,SELECT,UPDATE')
      OR has_schema_privilege(v_role,'public','CREATE')
      OR has_database_privilege(v_role,'lab_booking','CREATE')
      OR NOT has_schema_privilege(v_role,'public','USAGE')
      OR NOT has_column_privilege(v_role,'public.accounts_user','id','SELECT')
      OR NOT has_column_privilege(v_role,'public.accounts_user','is_active','SELECT')
      OR NOT has_column_privilege(v_role,'public.accounts_user','role','SELECT')
    THEN RAISE EXCEPTION 'Unexpected role, schema, sequence or account-read rights'; END IF;
    SELECT coalesce(jsonb_agg(r.rolname ORDER BY r.rolname),'[]'::jsonb) INTO v_inherited
      FROM pg_roles AS r WHERE r.oid<>v_role_id AND pg_has_role(v_role_id,r.oid,'USAGE');
    RAISE NOTICE 'effective_inherited_roles=%',v_inherited;
    FOREACH v_priv IN ARRAY ARRAY['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER','MAINTAIN'] LOOP
        IF has_table_privilege(v_role,v_tbl,v_priv) OR has_table_privilege(v_role,v_tbl,v_priv || ' WITH GRANT OPTION')
        THEN RAISE EXCEPTION 'Unexpected effective table privilege: %',v_priv; END IF;
    END LOOP;
    FOREACH v_col IN ARRAY v_fields LOOP
        IF NOT has_column_privilege(v_role,v_tbl,v_col,'SELECT')
          OR has_column_privilege(v_role,v_tbl,v_col,'INSERT') IS DISTINCT FROM (v_col <> 'id')
          OR has_column_privilege(v_role,v_tbl,v_col,'REFERENCES')
          OR has_column_privilege(v_role,v_tbl,v_col,'SELECT WITH GRANT OPTION')
          OR has_column_privilege(v_role,v_tbl,v_col,'INSERT WITH GRANT OPTION')
          OR has_column_privilege(v_role,v_tbl,v_col,'UPDATE WITH GRANT OPTION')
          OR has_column_privilege(v_role,v_tbl,v_col,'REFERENCES WITH GRANT OPTION')
        THEN RAISE EXCEPTION 'Unexpected effective column privileges: %',v_col; END IF;
        IF has_column_privilege(v_role,v_tbl,v_col,'UPDATE') THEN
            v_updates := array_append(v_updates,v_col);
        END IF;
    END LOOP;
    SELECT jsonb_object_agg(t.col,jsonb_build_object('SELECT',has_column_privilege(v_role,v_tbl,t.col,'SELECT'),
      'INSERT',has_column_privilege(v_role,v_tbl,t.col,'INSERT'),
      'UPDATE',has_column_privilege(v_role,v_tbl,t.col,'UPDATE'))) INTO v_matrix
      FROM unnest(v_fields) AS t(col);
    RAISE NOTICE 'effective_equipment_acl=%',v_matrix;
    IF v_updates = ARRAY[]::text[] THEN v_state := 'NOT_GRANTED';
    ELSIF v_updates = v_allowed THEN v_state := 'GRANTED';
    ELSE RAISE EXCEPTION 'Unexpected effective UPDATE columns: %',v_updates;
    END IF;
    RAISE NOTICE 'D035_ACL_STATE=%',v_state;
END
$verify$;
