[CmdletBinding()]
param(
    [string]$Passfile,
    [string]$Chrome,
    [switch]$ProbeIsolatedDatabase,
    [string]$Psql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe'
)

# Run in a regular Windows PowerShell. No migrations, application tests, or business DB access.
$ErrorActionPreference = 'Stop'
$storyRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$storyPython = Join-Path $storyRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $storyPython -PathType Leaf)) { throw 'Missing original project .venv interpreter.' }

$storyVersion = & $storyPython --version
$storyCode = $LASTEXITCODE
if ($storyCode -ne 0) { throw "Project Python preflight exited $storyCode." }
if ($storyVersion -cne 'Python 3.13.17') { throw 'Expected Python 3.13.17 in the original .venv.' }
$storyDjangoProbe = @'
from importlib.metadata import version
print(version("Django"))
'@
$storyDjango = $storyDjangoProbe | & $storyPython -B -
$storyCode = $LASTEXITCODE
if ($storyCode -ne 0 -or $storyDjango -cne '5.2.19') { throw 'Expected Django 5.2.19 as pinned in requirements.txt.' }
Write-Output "python=$storyVersion django=$storyDjango"

$storyConflicts = @('PGHOST','PGHOSTADDR','PGPORT','PGDATABASE','PGUSER','PGPASSWORD','PGSERVICE','PGSERVICEFILE','PGOPTIONS') |
    Where-Object { Test-Path -LiteralPath "Env:$_" }
if ($storyConflicts) { throw "Remove conflicting PostgreSQL environment variables: $($storyConflicts -join ', ')." }
if (-not $Passfile) { $Passfile = $env:PGPASSFILE }
if (-not $Passfile) { $Passfile = Join-Path $env:LOCALAPPDATA 'LabBooking/PostgreSQL17/pgpass.conf' }
$storyAbsolutePassfile = $Passfile -match '^(?:[A-Za-z]:[\\/]|\\\\[^\\]+\\[^\\]+\\)'
if (-not $storyAbsolutePassfile -or -not (Test-Path -LiteralPath $Passfile -PathType Leaf)) {
    throw 'Supply the existing protected PostgreSQL passfile by absolute path. Do not print its contents.'
}
Write-Output 'protected_passfile_exists=true'

if (-not $Chrome) { $Chrome = $env:LAB_BOOKING_R1_CHROME }
if (-not $Chrome) { $Chrome = Join-Path $env:ProgramFiles 'Google/Chrome/Application/chrome.exe' }
if (-not (Test-Path -LiteralPath $Chrome -PathType Leaf)) {
    throw 'Supply the existing Chrome executable with -Chrome for the legacy display regression.'
}
Write-Output 'chrome_exists=true'

if ($ProbeIsolatedDatabase) {
    if (-not (Test-Path -LiteralPath $Psql -PathType Leaf)) { throw 'Supply the existing PostgreSQL 17 psql.exe with -Psql.' }
    $storyOldPassfile = [Environment]::GetEnvironmentVariable('PGPASSFILE', 'Process')
    $storySql = @'
SELECT pg_catalog.current_database() AS db_name,
       session_user AS login_role, current_user AS effective_role,
       pg_catalog.host(pg_catalog.inet_server_addr()) AS server_host,
       pg_catalog.inet_server_port() AS server_port,
       pg_catalog.current_setting('server_version_num') AS version_num,
       (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls) AS role_excess,
       pg_catalog.has_database_privilege(current_user, 'lab_booking', 'CONNECT') AS business_connect
FROM pg_catalog.pg_roles AS r WHERE r.rolname = current_user;
'@
    try {
        $env:PGPASSFILE = $Passfile
        $storyIdentity = $storySql | & $Psql -X -w -q -A -t -F '|' -h 127.0.0.1 -p 5433 -U lab_booking_test -d test_lab_booking -v ON_ERROR_STOP=1 -f -
        $storyCode = $LASTEXITCODE
        if ($storyCode -ne 0 -or @($storyIdentity).Count -ne 1 -or
            ([string]$storyIdentity) -cne 'test_lab_booking|lab_booking_test|lab_booking_test|127.0.0.1|5433|170012|f|f') {
            throw "Isolated identity or privilege probe failed (psql exit $storyCode)."
        }
        Write-Output 'isolated_identity=test_lab_booking|lab_booking_test|127.0.0.1|5433|170012'
    } finally {
        [Environment]::SetEnvironmentVariable('PGPASSFILE', $storyOldPassfile, 'Process')
    }
}
Write-Output ('isolated_probe_requested=' + $ProbeIsolatedDatabase.IsPresent.ToString().ToLowerInvariant())
Write-Output 'STORY21_PREFLIGHT_OK'
