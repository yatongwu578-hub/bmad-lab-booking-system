-- Included by the guarded inspector in the same repeatable-read snapshot as its ACL.
DO $guard$
BEGIN
    IF current_setting('transaction_read_only') <> 'on'
       OR current_setting('transaction_isolation') <> 'repeatable read'
       OR session_user <> 'lab_booking_app' OR current_user <> 'lab_booking_app' THEN
        RAISE EXCEPTION 'Unexpected formal snapshot target';
    END IF;
END
$guard$;

-- Stable, ordered row digests. Exclude authenticated session rows and last_login
-- intentionally. Do not export raw passwords, account names, reasons, or tokens.
WITH
r AS (
    SELECT count(*) AS rows, COALESCE(jsonb_agg(to_jsonb(x) ORDER BY x.id), '[]'::jsonb)::text AS doc
    FROM (SELECT z.id,z.equipment_id,z.applicant_id,z.status,z.start_at,z.end_at,z.applied_at
          FROM public.reservations_reservation AS z) AS x
),
e AS (
    SELECT count(*) AS rows, COALESCE(jsonb_agg(to_jsonb(x) ORDER BY x.id), '[]'::jsonb)::text AS doc
    FROM (SELECT z.id,z.number,z.name,z.category,z.location,z.description,z.status
          FROM public.equipment_equipment AS z) AS x
),
h AS (
    SELECT count(*) AS rows, COALESCE(jsonb_agg(to_jsonb(x) ORDER BY x.id), '[]'::jsonb)::text AS doc
    FROM (SELECT z.id,z.reservation_id,z.actor_type,z.actor_id,z.action,z.before_status,
                 z.after_status,z.decision_at,z.recorded_at,z.reason
          FROM public.audit_operationhistory AS z) AS x
),
u AS (
    SELECT count(*) AS rows, COALESCE(jsonb_agg(to_jsonb(x) ORDER BY x.id), '[]'::jsonb)::text AS doc
    FROM (SELECT z.id,z.username,z.role,z.is_active,z.is_staff,z.is_superuser,z.password
          FROM public.accounts_user AS z) AS x
)
SELECT 'business_snapshot|' || json_build_object(
    'observed_at',clock_timestamp(),
    'reservations',json_build_object('count',r.rows,'digest',encode(sha256(convert_to(r.doc,'UTF8')),'hex')),
    'equipment',json_build_object('count',e.rows,'digest',encode(sha256(convert_to(e.doc,'UTF8')),'hex')),
    'history_projected',json_build_object('count',h.rows,'digest',encode(sha256(convert_to(h.doc,'UTF8')),'hex')),
    'account_security',json_build_object('count',u.rows,'digest',encode(sha256(convert_to(u.doc,'UTF8')),'hex')))
FROM r CROSS JOIN e CROSS JOIN h CROSS JOIN u;
SELECT 'snapshot_complete|STORY25_W01_SNAPSHOT_OK';
