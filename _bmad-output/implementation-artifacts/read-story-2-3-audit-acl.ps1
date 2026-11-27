[CmdletBinding()]
param(
    [string]$Passfile,
    [string]$Psql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe'
)

# Read-only catalog probe. Runs no app code, tests, migration or GRANT.
$ErrorActionPreference = 'Stop'
if (-not $Passfile) { $Passfile = $env:PGPASSFILE }
if (-not $Passfile) { $Passfile = Join-Path $env:LOCALAPPDATA 'LabBooking/PostgreSQL17/pgpass.conf' }
if ($Passfile -notmatch '^[A-Za-z]:[\\/]' -or -not (Test-Path -LiteralPath $Passfile -PathType Leaf)) {
    throw 'Use the existing protected absolute local PGPASSFILE.'
}
if (-not (Test-Path -LiteralPath $Psql -PathType Leaf)) { throw 'Existing psql.exe is required.' }
$conflict = @('PGHOST','PGHOSTADDR','PGPORT','PGDATABASE','PGUSER','PGPASSWORD','PGSERVICE','PGSERVICEFILE','PGOPTIONS') |
    Where-Object { Test-Path -LiteralPath "Env:$_" }
if ($conflict) { throw ('Conflicting PostgreSQL environment names: ' + ($conflict -join ', ')) }

$sql = @'
BEGIN ISOLATION LEVEL READ COMMITTED READ ONLY;
SET LOCAL statement_timeout = '5s';
SELECT (
    pg_catalog.current_database() = 'lab_booking'
    AND session_user = 'lab_booking_app' AND current_user = 'lab_booking_app'
    AND pg_catalog.host(pg_catalog.inet_server_addr()) = '127.0.0.1'
    AND pg_catalog.inet_server_port() = 5433
    AND pg_catalog.current_setting('server_version_num') = '170012'
    AND pg_catalog.current_setting('transaction_read_only') = 'on'
) AS target_ok \gset
\if :target_ok
SELECT 'identity', pg_catalog.current_database(), current_user,
       pg_catalog.host(pg_catalog.inet_server_addr()), pg_catalog.inet_server_port(),
       pg_catalog.current_setting('server_version_num');
SELECT 'table_select',
       pg_catalog.has_table_privilege(current_user, c.oid, 'SELECT'),
       pg_catalog.has_table_privilege(current_user, c.oid, 'SELECT WITH GRANT OPTION')
FROM pg_catalog.pg_class AS c
WHERE c.oid = 'public.audit_operationhistory'::pg_catalog.regclass;
SELECT 'column', a.attname,
       pg_catalog.has_column_privilege(current_user, a.attrelid, a.attnum, 'SELECT'),
       pg_catalog.has_column_privilege(current_user, a.attrelid, a.attnum, 'SELECT WITH GRANT OPTION')
FROM pg_catalog.pg_attribute AS a
WHERE a.attrelid = 'public.audit_operationhistory'::pg_catalog.regclass
  AND a.attnum > 0 AND NOT a.attisdropped
ORDER BY a.attname;
\endif
ROLLBACK;
SELECT 'STORY23_ACL_READONLY_OK';
'@
$oldPassfile = $env:PGPASSFILE
$oldTimeout = $env:PGCONNECT_TIMEOUT
try {
    $env:PGPASSFILE = $Passfile
    $env:PGCONNECT_TIMEOUT = '5'
    $lines = @($sql | & $Psql -X -w -q -A -t -F '|' -h 127.0.0.1 -p 5433 -U lab_booking_app -d lab_booking -v ON_ERROR_STOP=1 -f -)
    $code = $LASTEXITCODE
    if ($code -ne 0) { throw "Read-only psql exited $code." }
    if (@($lines | Where-Object {$_ -ceq 'identity|lab_booking|lab_booking_app|127.0.0.1|5433|170012'}).Count -ne 1 -or
        @($lines | Where-Object {$_ -ceq 'STORY23_ACL_READONLY_OK'}).Count -ne 1 -or
        @($lines | Where-Object {$_ -match '^column\|[a-z_]+\|[tf]\|[tf]$'}).Count -ne 12 -or
        @($lines | Where-Object {$_ -match '^table_select\|[tf]\|[tf]$'}).Count -ne 1) {
        throw 'Missing or unexpected ACL evidence. Do not infer readiness.'
    }
    $lines | Where-Object {$_ -cne 'STORY23_ACL_READONLY_OK'}
    $authorized = @($lines | Where-Object {$_ -match '^column\|[a-z_]+\|t\|f$'} | ForEach-Object {($_ -split '\|')[1]} | Sort-Object)
    if (@($lines | Where-Object {$_ -ceq 'table_select|f|f'}).Count -ne 1 -or
        @($lines | Where-Object {$_ -match '^column\|[a-z_]+\|[tf]\|t$'}).Count) {
        throw 'Unexpected table-level SELECT or grant option. Review drift.'
    }
    if (($authorized -join ',') -ceq 'id') { 'ACL_RESULT=NEEDS_FOUR_COLUMN_GRANT' }
    elseif (($authorized -join ',') -ceq 'action,actor_type,id,reason,reservation_id') { 'ACL_RESULT=EXACT_COLUMNS_PRESENT' }
    else { throw 'ACL differs from both expected sets. Review drift.' }
    'STORY23_ACL_READONLY_OK'
} finally {
    [Environment]::SetEnvironmentVariable('PGPASSFILE', $oldPassfile, 'Process')
    [Environment]::SetEnvironmentVariable('PGCONNECT_TIMEOUT', $oldTimeout, 'Process')
}
