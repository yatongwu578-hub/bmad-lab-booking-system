[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ExecutedBy,
    [string]$Passfile,
    [string]$AccountsJson,
    [switch]$RuntimeOnly,
    [switch]$ResumeInterruptedRun
)
$ErrorActionPreference = 'Stop'
$operator = $ExecutedBy.Trim()
if (-not $operator -or $operator -match 'placeholder|your name|\u586B\u5199') { throw 'Supply the actual operator name.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$python = Join-Path $root '.venv/Scripts/python.exe'
$psql = 'C:/Program Files/PostgreSQL/17/bin/psql.exe'
$chrome = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
$grantSql = Join-Path $PSScriptRoot 'story-1-4-runtime-grant.sql'
$snapshotSql = Join-Path $PSScriptRoot 'story-1-4-runtime-snapshot.sql'
$chromeScript = Join-Path $PSScriptRoot 'story-1-4-runtime-chrome.mjs'
$interruptedRun = Join-Path $PSScriptRoot 'story-1-4-runtime-run-20261126-112028-249'
if ($ResumeInterruptedRun -and -not $RuntimeOnly) { throw 'Recovery requires -RuntimeOnly.' }
if (-not $RuntimeOnly -and (Test-Path -LiteralPath $interruptedRun)) {
    throw 'D-035 already has a committed grant record. Do not run GRANT again. Verify ACL read-only and use -RuntimeOnly.'
}
if ($RuntimeOnly -and -not $ResumeInterruptedRun -and (Test-Path -LiteralPath $interruptedRun)) {
    throw 'Use -RuntimeOnly -ResumeInterruptedRun to verify the recorded service and pre-edit baseline.'
}
$run = Join-Path $PSScriptRoot ('story-1-4-runtime-run-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Path $run | Out-Null
$utf8 = [Text.UTF8Encoding]::new($false)
$start = Get-Date -Format o
$grantResult = 'NOT RUN'
$runtimeResult = 'NOT RUN'
$failure = ''
$owned = $null
$listener = $null
$serviceRootPid = $null
$serviceMode = 'NOT RUN'
$recoveryBaseline = $null
$console = [Console]::OutputEncoding
$envNames = @('PGPASSFILE','PGCLIENTENCODING','LAB_BOOKING_DB_MODE','DJANGO_SETTINGS_MODULE','LAB_BOOKING_SECRET_KEY',
    'PYTHONIOENCODING','STORY14_PSQL','STORY14_SNAPSHOT_SQL','STORY14_CHROME','STORY14_ACCOUNTS_JSON','STORY14_RECOVERY_BASELINE')
$previous = @{}
foreach ($name in $envNames) { $previous[$name] = [Environment]::GetEnvironmentVariable($name,'Process') }

function Invoke-Recorded([string]$Program,[string[]]$NativeArguments,[string]$Log) {
    $ErrorActionPreference = 'Continue'
    $PSNativeCommandUseErrorActionPreference = $false
    & $Program @NativeArguments 2>&1 | ForEach-Object { $_.ToString() } |
        ForEach-Object { [IO.File]::AppendAllText($Log,$_ + [Environment]::NewLine,$utf8); Write-Host $_ }
    $code = $LASTEXITCODE
    [IO.File]::AppendAllText($Log,"Exit $code" + [Environment]::NewLine,$utf8)
    $code
}
function Find-LoopbackListener {
    $sockets = @(netstat -ano -p TCP)
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect port 8001.' }
    $line = @($sockets | Where-Object { $_ -match '^\s*TCP\s+127\.0\.0\.1:8001\s+\S+\s+LISTENING\s+(\d+)\s*$' })
    if ($line.Count -eq 0) { return $null }
    if ($line.Count -ne 1) { throw 'Unexpected listener count on 8001.' }
    [int]([regex]::Match($line[0],'\d+\s*$').Value.Trim())
}
function Find-OwnedListener([int]$RootPid) {
    $listenerPid = Find-LoopbackListener
    if (-not $listenerPid) { return $null }
    $p = $listenerPid
    for ($i=0; $i -lt 5; $i++) {
        if ($p -eq $RootPid) { return $listenerPid }
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$p"
        if (-not $proc -or -not $proc.ParentProcessId -or $proc.ParentProcessId -eq $p) { break }
        $p = [int]$proc.ParentProcessId
    }
    throw 'Wrong listener ownership. No process was stopped.'
}
function Get-InputHashes([string[]]$Paths) {
    foreach ($path in $Paths) {
        "$((Get-FileHash -LiteralPath $path).Hash)  $(Split-Path $path -Leaf)"
    }
}
function Confirm-ExistingService([int]$ListenerPid,[string]$Log) {
    $prior = Join-Path $interruptedRun 'run-summary.txt'
    $values = @{}
    foreach ($line in Get-Content -LiteralPath $prior -Encoding UTF8) {
        if ($line -match '^(started|ended|started-pid|listener-pid)=(.+)$') { $values[$Matches[1]] = $Matches[2] }
    }
    $start = [DateTimeOffset]::ParseExact($values['started'],'o',[Globalization.CultureInfo]::InvariantCulture).UtcDateTime
    $end = [DateTimeOffset]::ParseExact($values['ended'],'o',[Globalization.CultureInfo]::InvariantCulture).UtcDateTime
    $rootPid = [int]$values['started-pid']
    if ($rootPid -le 0 -or $ListenerPid -ne [int]$values['listener-pid']) {
        throw 'Port 8001 does not belong to the recorded run. No process was stopped.'
    }
    $basePython = @(
        Get-Content -LiteralPath (Join-Path $root '.venv/pyvenv.cfg') |
            Where-Object { $_ -match '^executable\s*=\s*(.+)$' } |
            ForEach-Object { ($_ -split '=',2)[1].Trim() }
    )
    if ($basePython.Count -ne 1 -or -not [IO.Path]::IsPathRooted($basePython[0])) {
        throw 'Could not establish the original venv interpreter lineage.'
    }
    $argv = '(?:^|\s)"?-B"?\s+"?-u"?\s+"?manage\.py"?\s+"?runserver"?\s+"?127\.0\.0\.1:8001"?\s+"?--noreload"?\s*$'
    $rootCreated = $null
    foreach ($id in (@($rootPid,$ListenerPid) | Select-Object -Unique)) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$id" -ErrorAction Stop
        if (-not $proc -or -not $proc.CommandLine -or $proc.CommandLine -notmatch $argv) {
            throw 'Cannot verify the recorded Django command line. No process was stopped.'
        }
        $expectedExe = if ($id -eq $rootPid) { $python } else { $basePython[0] }
        if (-not $proc.ExecutablePath -or
            [IO.Path]::GetFullPath($proc.ExecutablePath) -ine [IO.Path]::GetFullPath($expectedExe)) {
            throw 'Recorded process does not match the project interpreter. No process was stopped.'
        }
        $created = ([datetime]$proc.CreationDate).ToUniversalTime()
        if ($created -lt $start -or $created -gt $end) {
            throw 'Process creation time does not match the original launch window. No process was stopped.'
        }
        if ($id -eq $rootPid) { $rootCreated = $created }
        [IO.File]::AppendAllText($Log,"pid=$id executable=$($proc.ExecutablePath) created_utc=$($created.ToString('o')) args=manage.py runserver 127.0.0.1:8001 --noreload" + [Environment]::NewLine,$utf8)
    }
    if (-not $rootCreated -or (Find-OwnedListener $rootPid) -ne $ListenerPid) { throw 'Recorded listener lineage changed.' }
    foreach ($path in $certifiedPaths) {
        if ((Get-Item -LiteralPath $path).LastWriteTimeUtc -gt $rootCreated) {
            throw 'Certified source has a write time after service launch. Do not reuse this service.'
        }
    }
    $startupLog = @(Get-Content -LiteralPath (Join-Path $interruptedRun 'server-stdout.txt') -Encoding UTF8)
    if (-not ($startupLog -match "using settings 'lab_booking\.settings'") -or
        -not ($startupLog -match 'Starting development server at http://127\.0\.0\.1:8001/')) {
        throw 'The prior startup log does not confirm this Django service.'
    }
    [IO.File]::AppendAllText($Log,"reused_from=$interruptedRun project=$root git=$head certified_files=$($certifiedPaths.Count)" + [Environment]::NewLine,$utf8)
    $rootPid
}

Push-Location -LiteralPath $root
try {
    [Console]::OutputEncoding = $utf8
    $env:PYTHONIOENCODING = 'utf-8'
    $node = (Get-Command node -CommandType Application -ErrorAction Stop).Source
    if (-not $Passfile) { $Passfile = Join-Path $env:LOCALAPPDATA 'LabBooking/PostgreSQL17/pgpass.conf' }
    if (-not $AccountsJson) { $AccountsJson = Join-Path $env:LOCALAPPDATA 'LabBooking/Protected/accounts.json' }
    foreach ($path in @($python,$psql,$chrome,$grantSql,$snapshotSql,$chromeScript,$Passfile,$AccountsJson)) {
        if (-not [IO.Path]::IsPathRooted($path) -or -not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw 'Required runtime executable, script or existing protected input is missing.'
        }
    }
    $conflicts = @('PGHOST','PGHOSTADDR','PGPORT','PGDATABASE','PGUSER','PGPASSWORD','PGSERVICE','PGSERVICEFILE','PGOPTIONS') |
        Where-Object { Test-Path "Env:$_" }
    if ($conflicts) { throw ('Remove conflicting libpq environment variables: ' + ($conflicts -join ', ')) }
    $version = & $python --version
    if ($LASTEXITCODE -ne 0 -or $version -cne 'Python 3.13.17') { throw 'The original Python 3.13.17 venv is required.' }
    $nodeVersion = & $node --version
    if ($LASTEXITCODE -ne 0 -or $nodeVersion -notmatch '^v(2[4-9]|[3-9]\d)\.') { throw 'Existing Node 24+ is required.' }
    & $node --check $chromeScript
    if ($LASTEXITCODE -ne 0) { throw 'Chrome verification source did not pass syntax check.' }
    try {
        $accounts = @(Get-Content -LiteralPath $AccountsJson -Raw -Encoding UTF8 | ConvertFrom-Json)
        foreach ($role in @('student','teacher','admin')) {
            if (@($accounts | Where-Object { $_.role -ceq $role -and $_.username -and $_.password }).Count -ne 1) { throw 'Invalid role set.' }
        }
    } catch { throw 'Protected account file could not be validated. No sensitive contents were logged.' }
    finally { Remove-Variable accounts -ErrorAction SilentlyContinue }
    $head = git rev-parse HEAD
    if ($LASTEXITCODE -ne 0 -or $head -cne 'e200fee335536941e0705c112aefbf6751b244c3') { throw 'Unexpected Git baseline.' }
    $certified = Join-Path $PSScriptRoot 'story-1-4-independent-remediation-20261126-103026-904-00f7bfce/after.sha256'
    if ((Get-FileHash -LiteralPath $certified).Hash -cne 'A9B6F16E107385EB52A013ADA19C13DC21C9987AFC287A307F1398DFA6A358CA') {
        throw 'Independent certification manifest changed.'
    }
    $certifiedPaths = @(foreach ($entry in Get-Content -LiteralPath $certified -Encoding UTF8) {
        if ($entry -notmatch '^([0-9A-F]{64})  (.+)$') { throw 'Invalid certification row.' }
        $sha = $Matches[1]; $source = Join-Path $root $Matches[2]
        if ((Get-FileHash -LiteralPath $source).Hash -cne $sha) { throw "Tested source drift: $source" }
        $source
    })
    $inputs = @($grantSql,$snapshotSql,$chromeScript,$PSCommandPath)
    if ($ResumeInterruptedRun) {
        $priorHashes = @{
            'acl-raw.txt'              = '046286208CA3DC460E7E5EC74E1BC4B70457737E747B17F83C4544D138D7CE18'
            'chrome-db-raw.txt'        = 'C4B5DB0DEE64F217C80B7879D8421A89F40DBF4CB37A74322F156B331F9808EC'
            'inputs.sha256'            = 'D80097BD28DE6F84B766B46EC268A0D80C81747F0E49F4A73B8DA6AD39D8EDAA'
            'run-summary.txt'          = '58B5AB0A1991F785B39ACB080CEAFE226265243F16372C7279DEEBE358DFBEAB'
            'runtime-acl-readback.txt' = 'BD983CD2D8B087B59D36FE6328FAD80FB7994DB5281F129F3494477D72AD8A96'
        }
        foreach ($name in $priorHashes.Keys) {
            $path = Join-Path $interruptedRun $name
            if ((Get-FileHash -LiteralPath $path).Hash -cne $priorHashes[$name]) {
                throw "Prior recovery evidence changed: $name"
            }
            $inputs += $path
        }
        $recoveryBaseline = Join-Path $interruptedRun 'runtime-acl-readback.txt'
    }
    $inputBefore = @(Get-InputHashes $inputs)
    [IO.File]::WriteAllLines((Join-Path $run 'inputs.sha256'),[string[]]$inputBefore,$utf8)

    $existing = Find-LoopbackListener
    if ($existing) {
        if (-not $ResumeInterruptedRun) { throw '127.0.0.1:8001 is already in use. No process was stopped.' }
        $serviceRootPid = Confirm-ExistingService $existing (Join-Path $run 'service-identity.txt')
        $listener = $existing
        $serviceMode = 'REUSED VERIFIED INTERRUPTED-RUN SERVICE'
    } else {
        $socket = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,8001)
        try { $socket.ExclusiveAddressUse = $true; $socket.Start() }
        catch { throw '127.0.0.1:8001 unavailable. Do not terminate an unidentified process.' }
        finally { $socket.Stop() }
    }

    $env:PGPASSFILE = $Passfile
    $env:PGCLIENTENCODING = 'UTF8'
    $target = @('-X','-w','-h','127.0.0.1','-p','5433','-d','lab_booking','-v','ON_ERROR_STOP=1')
    if ($RuntimeOnly) { $grantResult = 'SKIPPED BY -RuntimeOnly; existing ACL must pass independent snapshot' }
    else {
        $aclLog = Join-Path $run 'acl-raw.txt'
        $grantResult = 'STARTED; DO NOT REPLAY IF UNCONFIRMED'
        $code = Invoke-Recorded $psql ($target + @('-U','lab_booking_migrator','--single-transaction','-f',$grantSql)) $aclLog
        if ($code -ne 0 -or @(Select-String -LiteralPath $aclLog -SimpleMatch 'D035_ACL_ASSERTIONS_PASSED').Count -ne 1) {
            throw 'Grant transaction not confirmed. Keep ACL output and independently check before any further action.'
        }
        $grantResult = 'COMMIT CONFIRMED; D035 assertion and psql exit 0'
    }
    $preLog = Join-Path $run 'runtime-acl-readback.txt'
    $code = Invoke-Recorded $psql ($target + @('-qAt','-U','lab_booking_app','-c','BEGIN READ ONLY','-f',$snapshotSql,'-c','COMMIT')) $preLog
    if ($code -ne 0 -or @(Select-String -LiteralPath $preLog -SimpleMatch 'EQ-DEMO-S12-20261125').Count -ne 1) {
        throw 'Runtime ACL, target or approved demonstration record could not be verified read-only.'
    }
    $preLines = @(Get-Content -LiteralPath $preLog -Encoding UTF8)
    if ($preLines.Count -ne 2 -or $preLines[1] -cne 'Exit 0') { throw 'Unexpected runtime read-back output.' }
    $pre = $preLines[0] | ConvertFrom-Json
    if ($pre.database -cne 'lab_booking' -or $pre.role -cne 'lab_booking_app' -or
        $pre.port -ne 5433 -or $pre.version -cne '17.12' -or $pre.isolation -cne 'read committed' -or
        $pre.row.number -cne 'EQ-DEMO-S12-20261125' -or $pre.row.id -isnot [ValueType] -or $pre.row.id -le 0) {
        throw 'Read-back target or demonstration row did not match D-035.'
    }
    $env:LAB_BOOKING_DB_MODE = 'runtime'
    $env:DJANGO_SETTINGS_MODULE = 'lab_booking.settings'
    if (-not $env:LAB_BOOKING_SECRET_KEY) {
        $env:LAB_BOOKING_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
    }
    if (-not $listener) {
        $serverOptions = @{
            FilePath=$python; ArgumentList=@('-B','-u','manage.py','runserver','127.0.0.1:8001','--noreload')
            WorkingDirectory=$root; RedirectStandardOutput=(Join-Path $run 'server-stdout.txt')
            RedirectStandardError=(Join-Path $run 'server-stderr.txt'); WindowStyle='Hidden'; PassThru=$true
        }
        $owned = Start-Process @serverOptions
        $serviceRootPid = $owned.Id
        $deadline = (Get-Date).AddSeconds(15)
        while (-not $listener -and (Get-Date) -lt $deadline) {
            $owned.Refresh()
            if ($owned.HasExited) { throw 'The new server process exited. See server logs.' }
            $listener = Find-OwnedListener $serviceRootPid
            if (-not $listener) { Start-Sleep -Milliseconds 250 }
        }
        if (-not $listener) { throw 'The new server did not obtain the intended listener.' }
        $serviceMode = 'STARTED NEW CERTIFIED SERVICE'
    }
    if ((Find-OwnedListener $serviceRootPid) -ne $listener) { throw 'Verified listener changed before Chrome.' }
    $env:STORY14_PSQL = $psql
    $env:STORY14_SNAPSHOT_SQL = $snapshotSql
    $env:STORY14_CHROME = $chrome
    $env:STORY14_ACCOUNTS_JSON = $AccountsJson
    [Environment]::SetEnvironmentVariable('STORY14_RECOVERY_BASELINE',$recoveryBaseline,'Process')
    $browserLog = Join-Path $run 'chrome-db-raw.txt'
    $runtimeResult = 'STARTED; DO NOT REPLAY IF AN EDIT MAY HAVE COMMITTED'
    $code = Invoke-Recorded $node @($chromeScript) $browserLog
    $success = @(Get-Content -LiteralPath $browserLog -Encoding UTF8 | Where-Object { $_ -cmatch '^\{"result":"passed",' })
    if ($code -ne 0 -or $success.Count -ne 1) {
        throw 'Chrome or independent readback did not complete. Preserve the logs and do not replay.'
    }
    $result = $success[0] | ConvertFrom-Json
    $detailUrl = "http://127.0.0.1:8001/equipment/$($pre.row.id)/"
    if ($result.result -cne 'passed' -or $result.detail_url -cne $detailUrl -or $result.edit_url -cne ($detailUrl + 'edit/')) {
        throw 'Unexpected Chrome success result. Preserve the logs and do not replay.'
    }
    if ((Find-OwnedListener $serviceRootPid) -ne $listener) { throw 'Verified listener changed.' }
    if ((Get-FileHash -LiteralPath $certified).Hash -cne 'A9B6F16E107385EB52A013ADA19C13DC21C9987AFC287A307F1398DFA6A358CA') {
        throw 'Independent certification manifest changed during runtime.'
    }
    foreach ($entry in Get-Content -LiteralPath $certified -Encoding UTF8) {
        if ($entry -notmatch '^([0-9A-F]{64})  (.+)$') { throw 'Invalid certification row after runtime.' }
        $sha = $Matches[1]; $source = $Matches[2]
        if ((Get-FileHash -LiteralPath (Join-Path $root $source)).Hash -cne $sha) { throw "Tested source drift during runtime: $source" }
    }
    $inputAfter = @(Get-InputHashes $inputs)
    [IO.File]::WriteAllLines((Join-Path $run 'inputs.after.sha256'),[string[]]$inputAfter,$utf8)
    if (($inputBefore -join [Environment]::NewLine) -cne ($inputAfter -join [Environment]::NewLine)) {
        throw 'Runtime verification input drift. Preserve the logs and do not replay.'
    }
    $runtimeResult = 'PASS; Chrome and independent database readback'
}
catch { $failure = $_.Exception.Message }
finally {
    foreach ($name in $envNames) { [Environment]::SetEnvironmentVariable($name,$previous[$name],'Process') }
    [Console]::OutputEncoding = $console
    Pop-Location
    [IO.File]::WriteAllLines((Join-Path $run 'run-summary.txt'),[string[]]@(
        "actual operator(s), as reported: $operator", "started=$start", ('ended=' + (Get-Date -Format o)),
        'target=PostgreSQL 17.12, 127.0.0.1:5433/lab_booking', "python=$version", "node=$nodeVersion",
        "acl=$grantResult", "runtime=$runtimeResult", "service=$serviceMode",
        "started-pid=$(if($owned){$owned.Id})", "service-root-pid=$serviceRootPid", "listener-pid=$listener",
        'login=http://127.0.0.1:8001/login/', $failure
    ),$utf8)
    Write-Host "Evidence: $run"
    if ($listener) { Write-Host 'Verified service left on http://127.0.0.1:8001/login/. Existing 8000 process was not touched.' }
}
if ($failure) { throw 'D-035 incomplete. Preserve the exact logs and do not replay an unconfirmed operation.' }
