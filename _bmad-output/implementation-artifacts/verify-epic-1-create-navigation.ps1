[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$ExecutedBy,
    [string]$Passfile,
    [switch]$Restart8001
)
$ErrorActionPreference = 'Stop'
$operator = $ExecutedBy.Trim()
if (-not $operator -or $operator -match '[\r\n]') { throw 'Supply the actual operator name.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$python = Join-Path $root '.venv/Scripts/python.exe'
$patch = Join-Path $PSScriptRoot 'epic-1-create-navigation.patch'
$run = Join-Path $PSScriptRoot ('epic-1-create-navigation-run-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Path $run | Out-Null
$utf8 = [Text.UTF8Encoding]::new($false)
$raw = Join-Path $run 'raw.txt'
$start = Get-Date -Format o
$tests = 'NOT RUN'
$service = 'UNCHANGED'
$failure = ''
$serverLogs = ''
$runtimeKey = 'NOT APPLICABLE'
$oldConsole = [Console]::OutputEncoding
$prior = @{}
foreach ($name in @('LAB_BOOKING_DB_MODE','LAB_BOOKING_SECRET_KEY','PGPASSFILE','PGCLIENTENCODING','PYTHONIOENCODING','DJANGO_SETTINGS_MODULE')) {
    $prior[$name] = [Environment]::GetEnvironmentVariable($name,'Process')
}

function Invoke-LoggedPython([string[]]$NativeArguments) {
    $ErrorActionPreference = 'Continue'
    $PSNativeCommandUseErrorActionPreference = $false
    & $python @NativeArguments 2>&1 | ForEach-Object {
        $line = $_.ToString()
        [IO.File]::AppendAllText($raw,$line + [Environment]::NewLine,$utf8)
        Write-Host $line
    }
    $code = $LASTEXITCODE
    [IO.File]::AppendAllText($raw,"Exit $code" + [Environment]::NewLine,$utf8)
    $code
}

function Listener8001 {
    $lines = @(netstat -ano -p TCP)
    if ($LASTEXITCODE -ne 0) { throw 'Could not inspect the local listener.' }
    $bound = @($lines | Where-Object { $_ -match '^\s*TCP\s+\S+:8001\s+\S+\s+LISTENING\s+\d+\s*$' })
    if ($bound.Count -eq 0) { return $null }
    if ($bound.Count -ne 1 -or $bound[0] -notmatch '^\s*TCP\s+127\.0\.0\.1:8001\s+\S+\s+LISTENING\s+(\d+)\s*$') {
        throw 'Port 8001 is not exclusively the expected loopback listener. No process was stopped.'
    }
    [int]$Matches[1]
}

function Assert-RecordedService([int]$Listener,[string]$BasePython) {
    $identity = Join-Path $PSScriptRoot 'story-1-4-runtime-run-20261126-114602-260/service-identity.txt'
    if ($Listener -ne 5364 -or (Get-FileHash -LiteralPath $identity).Hash -cne '9E0C598530EEFFFC8C8319AD88806B659E1167C733280C9B5D965D74C6E87DAF') {
        throw '8001 is not the D-035 recorded service. No process was stopped.'
    }
    $launcher = Get-CimInstance Win32_Process -Filter 'ProcessId=39000'
    $worker = Get-CimInstance Win32_Process -Filter 'ProcessId=5364'
    $argsPattern = '(?:^|\s)"?-B"?\s+"?-u"?\s+"?manage\.py"?\s+"?runserver"?\s+"?127\.0\.0\.1:8001"?\s+"?--noreload"?\s*$'
    if (-not $launcher -or -not $worker -or $worker.ParentProcessId -ne 39000 -or
        $launcher.ExecutablePath -ine $python -or $worker.ExecutablePath -ine $BasePython -or
        $launcher.CommandLine -notmatch $argsPattern -or $worker.CommandLine -notmatch $argsPattern -or
        $launcher.CreationDate.ToUniversalTime().ToString('o') -cne '2026-11-26T03:20:28.9653080Z' -or
        $worker.CreationDate.ToUniversalTime().ToString('o') -cne '2026-11-26T03:20:29.0762310Z') {
        throw 'D-035 process identity or lineage could not be verified. No process was stopped.'
    }
}

function Assert-RuntimeGet {
    $handler = [Net.Http.HttpClientHandler]::new()
    $handler.AllowAutoRedirect = $false
    $handler.UseCookies = $false
    $handler.UseProxy = $false
    $http = [Net.Http.HttpClient]::new($handler)
    $http.Timeout = [TimeSpan]::FromSeconds(5)
    try {
        $login = $http.GetAsync('http://127.0.0.1:8001/login/').GetAwaiter().GetResult()
        $create = $http.GetAsync('http://127.0.0.1:8001/equipment/new/').GetAwaiter().GetResult()
        $next = if ($create.Headers.Location) { $create.Headers.Location.OriginalString } else { '' }
        [IO.File]::WriteAllLines((Join-Path $run 'runtime-smoke.txt'),[string[]]@(
            "GET /login/ $([int]$login.StatusCode)", "GET /equipment/new/ $([int]$create.StatusCode) Location=$next"
        ),$utf8)
        if ([int]$login.StatusCode -ne 200 -or [int]$create.StatusCode -ne 302 -or $next -cne '/login/?next=/equipment/new/') {
            throw 'Runtime GET smoke failed. No login or submission was attempted.'
        }
    } finally {
        if ($login) { $login.Dispose() }
        if ($create) { $create.Dispose() }
        $http.Dispose()
    }
}

Push-Location -LiteralPath $root
try {
    [Console]::OutputEncoding = $utf8
    $env:PGCLIENTENCODING = 'UTF8'
    $env:PYTHONIOENCODING = 'utf-8'
    $env:DJANGO_SETTINGS_MODULE = 'lab_booking.settings'
    if (-not $Passfile) { $Passfile = Join-Path $env:LOCALAPPDATA 'LabBooking/PostgreSQL17/pgpass.conf' }
    if (-not [IO.Path]::IsPathRooted($Passfile) -or -not (Test-Path -LiteralPath $Passfile -PathType Leaf) -or
        -not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'Existing protected input or canonical venv unavailable.' }
    $conflicts = @('PGHOST','PGHOSTADDR','PGPORT','PGDATABASE','PGUSER','PGPASSWORD','PGSERVICE','PGSERVICEFILE','PGOPTIONS') |
        Where-Object { Test-Path "Env:$_" }
    if ($conflicts) { throw ('Unset conflicting libpq variables: ' + ($conflicts -join ', ')) }
    if ((Get-FileHash -LiteralPath $patch).Hash -cne 'A4392ED98CC2D8406A6BC708252181344D5E7481D94D302F39F7ABC30D951799') {
        throw 'Navigation patch does not match the reviewed SHA-256.'
    }
    git apply --reverse --check -- $patch
    if ($LASTEXITCODE -ne 0) { throw 'The exact four-file navigation patch is not applied.' }
    $head = git rev-parse HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read the tested Git baseline.' }
    $targets = @('accounts/templates/accounts/identity.html','equipment/templates/equipment/catalog.html',
        'equipment/templates/equipment/_create_link.html','equipment/test_create_navigation.py')
    $before = @($targets | ForEach-Object { "$((Get-FileHash -LiteralPath $_).Hash)  $_" })
    [IO.File]::WriteAllLines((Join-Path $run 'before.sha256'),[string[]]$before,$utf8)
    $code = Invoke-LoggedPython @('--version')
    if ($code -ne 0 -or @(Select-String -LiteralPath $raw -CaseSensitive -Pattern '^Python 3\.13\.17$').Count -ne 1) {
        throw 'Original Python 3.13.17 did not run.'
    }
    $env:PGPASSFILE = $Passfile
    $env:LAB_BOOKING_DB_MODE = 'test'
    $env:LAB_BOOKING_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
    $tests = 'STARTED'
    $code = Invoke-LoggedPython @('-B','manage.py','test','equipment.test_create_navigation','--keepdb','--parallel','1','-v','2')
    $lines = @(Get-Content -LiteralPath $raw -Encoding UTF8)
    if ($code -ne 0 -or @($lines -cmatch '^Ran 4 tests in ').Count -ne 1 -or
        @($lines -cmatch '^OK\s*$').Count -ne 1 -or
        @($lines -match '127\.0\.0\.1:5433/test_lab_booking.*lab_booking_test').Count -ne 1) {
        throw 'Targeted tests, the exact test count, or the approved database guard did not pass.'
    }
    $after = @($targets | ForEach-Object { "$((Get-FileHash -LiteralPath $_).Hash)  $_" })
    [IO.File]::WriteAllLines((Join-Path $run 'after.sha256'),[string[]]$after,$utf8)
    if (($before -join [Environment]::NewLine) -cne ($after -join [Environment]::NewLine)) { throw 'Tested sources changed during verification.' }
    $tests = 'PASS 4/4 via test_lab_booking; no skips'

    if ($Restart8001) {
        $env:LAB_BOOKING_DB_MODE = 'runtime'
        $runtimeKey = 'REUSED FROM CALLER ENVIRONMENT'
        if ($prior['LAB_BOOKING_SECRET_KEY']) {
            $env:LAB_BOOKING_SECRET_KEY = $prior['LAB_BOOKING_SECRET_KEY']
        } else {
            $env:LAB_BOOKING_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
            $runtimeKey = 'FRESH KEY; SIGN IN AGAIN'
        }
        $basePython = @(Get-Content -LiteralPath '.venv/pyvenv.cfg' | Where-Object { $_ -match '^executable\s*=' } |
            ForEach-Object { ($_ -split '=',2)[1].Trim() })
        if ($basePython.Count -ne 1 -or -not [IO.Path]::IsPathRooted($basePython[0])) { throw 'Cannot identify the original venv base Python.' }
        Add-Type -AssemblyName System.Net.Http
        $serverLogs = Join-Path $env:TEMP ('lab-booking-navigation-8001-' + [guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $serverLogs | Out-Null
        $oldListener = Listener8001
        if ($oldListener) {
            Assert-RecordedService $oldListener $basePython[0]
            $worker = Get-Process -Id 5364
            $launcher = Get-Process -Id 39000
            # Obtain both process handles before stopping either process.
            $null = $worker.Handle
            $null = $launcher.Handle
            Assert-RecordedService (Listener8001) $basePython[0]
            $service = 'STOPPING VERIFIED D-035 SERVICE'
            $worker.Kill()
            if (-not $worker.WaitForExit(5000)) { throw 'Verified worker did not exit.' }
            if (-not $launcher.WaitForExit(2000)) {
                $launcher.Kill()
                if (-not $launcher.WaitForExit(5000)) { throw 'Verified launcher did not exit.' }
            }
        }
        if (Listener8001) { throw 'Port 8001 remains occupied; no further process was stopped.' }
        $service = 'START ATTEMPTED'
        $options = @{
            FilePath=$python; ArgumentList=@('-B','-u','manage.py','runserver','127.0.0.1:8001','--noreload')
            WorkingDirectory=$root; RedirectStandardOutput=(Join-Path $serverLogs 'stdout.txt')
            RedirectStandardError=(Join-Path $serverLogs 'stderr.txt'); WindowStyle='Hidden'; PassThru=$true
        }
        $new = Start-Process @options
        $listener = $null
        $deadline = [DateTime]::UtcNow.AddSeconds(15)
        while (-not $listener -and [DateTime]::UtcNow -lt $deadline) {
            if ($new.HasExited) { throw 'New project service exited. See the separate local server logs.' }
            $listener = Listener8001
            if (-not $listener) { Start-Sleep -Milliseconds 250 }
        }
        if (-not $listener) { throw 'New project service did not obtain port 8001.' }
        if ($listener -ne $new.Id) {
            $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$listener"
            if (-not $proc -or $proc.ParentProcessId -ne $new.Id -or $proc.ExecutablePath -ine $basePython[0]) {
                throw 'New port owner is not the launched project process. No unknown process was stopped.'
            }
        }
        Assert-RuntimeGet
        if ((Listener8001) -ne $listener) { throw 'Verified listener changed.' }
        $service = "PASS launcher=$($new.Id) listener=$listener http://127.0.0.1:8001/login/"
    }
} catch {
    $failure = $_.Exception.Message
    throw
} finally {
    foreach ($name in $prior.Keys) { [Environment]::SetEnvironmentVariable($name,$prior[$name],'Process') }
    [Console]::OutputEncoding = $oldConsole
    Pop-Location
    [IO.File]::WriteAllLines((Join-Path $run 'run-summary.txt'),[string[]]@(
        "actual operator(s), as reported: $operator","started=$start",('ended=' + (Get-Date -Format o)),"git=$head",
        'isolated_target=127.0.0.1:5433/test_lab_booking (lab_booking_test)',"tests=$tests","service=$service",
        "runtime_key=$runtimeKey","temporary_server_logs=$serverLogs",$failure
    ),$utf8)
    Write-Host "Evidence: $run"
    if ($serverLogs) { Write-Host "Local server logs: $serverLogs" }
    if ($runtimeKey -eq 'FRESH KEY; SIGN IN AGAIN') { Write-Host 'The new runtime uses a fresh key. Sign in again.' }
}
