-- D-035: call only as lab_booking_app with BEGIN READ ONLY and COMMIT.
SET LOCAL search_path = pg_catalog, public;
DO $verify$
DECLARE
    c text;
    p text;
BEGIN
    IF current_database() <> 'lab_booking'
      OR session_user <> 'lab_booking_app' OR current_user <> 'lab_booking_app'
      OR host(inet_server_addr()) IS DISTINCT FROM '127.0.0.1'
      OR inet_server_port() IS DISTINCT FROM 5433
      OR current_setting('server_version_num') <> '170012'
      OR current_setting('transaction_read_only') <> 'on'
      OR current_setting('transaction_isolation') <> 'read committed'
    THEN RAISE EXCEPTION 'Unexpected runtime snapshot target'; END IF;
    FOREACH c IN ARRAY ARRAY['id','number','name','category','location','description','status'] LOOP
        IF NOT has_column_privilege('public.equipment_equipment',c,'SELECT')
           OR has_column_privilege('public.equipment_equipment',c,'INSERT') IS DISTINCT FROM (c <> 'id')
           OR has_column_privilege('public.equipment_equipment',c,'UPDATE') IS DISTINCT FROM
              (c IN ('name','category','location','description'))
           OR has_column_privilege('public.equipment_equipment',c,'UPDATE WITH GRANT OPTION')
        THEN RAISE EXCEPTION 'Unexpected runtime equipment ACL: %', c; END IF;
    END LOOP;
    FOREACH p IN ARRAY ARRAY['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER','MAINTAIN'] LOOP
        IF has_table_privilege('public.equipment_equipment',p)
        THEN RAISE EXCEPTION 'Unexpected runtime table privilege: %',p; END IF;
    END LOOP;
END
$verify$;
SELECT jsonb_build_object(
    'database',current_database(),'role',current_user,'port',inet_server_port(),
    'version',current_setting('server_version'),'isolation',current_setting('transaction_isolation'),
    'row',to_jsonb(e),'device_count',(SELECT count(*) FROM public.equipment_equipment),
    'other_devices_sha256',(
        SELECT encode(sha256(convert_to(coalesce(jsonb_agg(to_jsonb(o) ORDER BY o.id)::text,'[]'),'UTF8')),'hex')
          FROM public.equipment_equipment o WHERE o.id<>e.id
    ),
    'migrations',(SELECT count(*) FROM public.django_migrations),
    'sessions',(SELECT count(*) FROM public.django_session)
) FROM public.equipment_equipment e WHERE e.number='EQ-DEMO-S12-20261125';
