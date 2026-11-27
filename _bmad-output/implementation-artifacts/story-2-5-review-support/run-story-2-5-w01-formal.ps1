[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$InspectionEvidence,
    [Parameter(Mandatory)][string]$ToolchainEvidence,
    [string]$LiveIoEvidence,
    [string]$Passfile,
    [string]$AccountsJson = (Join-Path $env:LOCALAPPDATA 'LabBooking\Protected\accounts.json'),
    [string]$Psql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe',
    [string]$Chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe',
    [string]$OutputRoot = 'F:\softwork\outputs',
    [ValidateRange(1024,65535)][int]$BrowserPort = 8005,
    [switch]$LeaveGuardedLink,
    [switch]$ResumeBrowser
)

$ErrorActionPreference = 'Stop'
$support = $PSScriptRoot
. (Join-Path $support 'w01-log-contract.ps1')
Set-W01WireEncoding
. (Join-Path $support 'w01-recovery-policy.ps1')
$repo = (Resolve-Path -LiteralPath (Join-Path $support '../../..')).Path
$python = Join-Path $repo '.venv/Scripts/python.exe'
$node = (Get-Command node.exe -CommandType Application).Source
$inspection = Join-Path $support 'inspect-story-2-5-w01.ps1'
$grant = Join-Path $support 'story-2-5-w01-grant.sql'
$serverScript = Join-Path $support 'serve-story-2-5-w01-smoke.py'
$browserScript = Join-Path $support 'capture-story-2-5-browser.mjs'
$finishScript = Join-Path $support 'check-story-2-5-w01-smoke.py'
$certRaw = 'F:\softwork\outputs\story-2-5-isolated-review-20261127-205155-201-532c39d28e5240d286211a51b403131f\story-2-5-run-20261127-205155-298-776c5f4004c44734b4b250578a781884'
$run = (New-Item -ItemType Directory -Path (Join-Path $OutputRoot ('story-2-5-w01-formal-' +
    (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + [guid]::NewGuid().ToString('N')))).FullName
Write-Host "W01 formal archive: $run"
$utf8 = New-Object System.Text.UTF8Encoding($false)
$server = $null
$live = $null
$liveReady = $false
$phase = 'qualification'
$fresh = $null
$before = $null
$after = $null
$grantAttempted = $false
$grantReceipt = 'not-attempted'
$stopped = Join-Path $run 'server-stop.flag'
$bindings = 'PGPASSFILE','PGCONNECT_TIMEOUT','PGCLIENTENCODING','LAB_BOOKING_DB_MODE','LAB_BOOKING_SECRET_KEY','DJANGO_SETTINGS_MODULE','PYTHONUTF8','PYTHONIOENCODING','PYTHONDONTWRITEBYTECODE'
$old = @{}
foreach ($name in $bindings) { $old[$name] = [Environment]::GetEnvironmentVariable($name,'Process') }

function Require-W01($ok,[string]$message) { if (-not $ok) { throw $message } }
function FileHash-W01($file) { (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash }
function Stage-W01([string]$stage,[int]$code) {
    "$(Get-Date -Format o) $stage exit=$code" | Add-Content -LiteralPath (Join-Path $run 'stages.txt') -Encoding UTF8
    Require-W01 ($code -eq 0) "Stage $stage failed; see the first archive."
}
function Phase-W01([string]$name,[string]$state,[string]$evidence) {
    [ordered]@{at=(Get-Date -Format o);phase=$name;state=$state;evidence=$evidence} |
        ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $run 'phases.jsonl') -Encoding UTF8
}
function Start-W01([string]$name,[string]$file,[string[]]$argv,[switch]$Async) {
    Start-W01Redirected $file $repo $argv (Join-Path $run "$name.stdout.txt") (Join-Path $run "$name.stderr.txt") -Async:$Async
}
function Native-W01([string]$name,[string]$file,[string[]]$argv,[string]$marker) {
    $p = Start-W01 $name $file $argv
    Write-W01NativeReceipt (Join-Path $run "$name.native.json") (Join-Path $run "$name.stdout.txt") (Join-Path $run "$name.stderr.txt") $p.ExitCode 'UTF-8 W01 protocol' 'raw diagnostics'
    Stage-W01 $name $p.ExitCode
    $lines = @(Read-W01Lines (Join-Path $run "$name.stdout.txt"))
    if ($marker) { Assert-W01Marker $lines $p.ExitCode $marker }
    $lines
}
function Inspect-W01([string]$name,[string]$prior,[switch]$Snapshot) {
    $argv = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$inspection,'-Passfile',$Passfile,'-Psql',$Psql,'-OutputRoot',$run,'-BrowserPort',"$BrowserPort")
    if ($prior) { $argv += @('-BeforeEvidence',$prior) }
    if ($Snapshot) { $argv += '-CaptureSnapshot' }
    $lines = @(Native-W01 $name 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' $argv 'STORY25_W01_INSPECT_OK')
    $hits = @($lines | Where-Object { $_ -cmatch '^W01 evidence: ' })
    Require-W01 ($hits.Count -eq 1) 'Could not uniquely identify inspection evidence.'
    $path = (Resolve-Path -LiteralPath ($hits[0].Substring(14))).Path
    Require-W01 ((Split-Path $path -Parent) -ceq $run) 'Inspection receipt escaped this batch.'
    Join-Path $path 'w01-inspect.json'
}
function ReadPlan-W01($file) { Read-W01Text $file | ConvertFrom-Json }
function Wait-W01($condition,[string]$failure,[int]$seconds=12) {
    $end = [DateTime]::UtcNow.AddSeconds($seconds)
    while ([DateTime]::UtcNow -lt $end) {
        if (& $condition) { return }
        Start-Sleep -Milliseconds 150
    }
    throw $failure
}
function Stop-W01Server {
    if ($server -and -not $server.HasExited) {
        if (-not (Test-Path -LiteralPath $stopped)) { [IO.File]::WriteAllText($stopped,'stop',$utf8) }
        if (-not $server.WaitForExit(8000)) { $server.Kill(); throw 'This batch server did not stop cleanly.' }
    }
}
function Archive-W01StoppedServer {
    $receipt=Join-Path $run 'server.native.json'
    if ($server -and $server.HasExited -and -not (Test-Path -LiteralPath $receipt)) {
        Write-W01NativeReceipt $receipt (Join-Path $run 'server.stdout.txt') (Join-Path $run 'server.stderr.txt') $server.ExitCode 'UTF-8 Python after exit' 'raw Python diagnostics after exit'
    }
}
function Verify-W01Listener([string]$Events,[string]$HttpPid,[string]$Inspection) {
    $first = Read-W01SharedFirstLine $Events | ConvertFrom-Json
    $name = 'netstat-' + [IO.Path]::GetFileNameWithoutExtension($Events)
    $p = Start-W01 $name (Join-Path $env:SystemRoot 'System32/netstat.exe') @('-ano','-p','TCP')
    $out = Join-Path $run "$name.stdout.txt"
    Write-W01NativeReceipt (Join-Path $run "$name.native.json") $out (Join-Path $run "$name.stderr.txt") $p.ExitCode 'raw native; ASCII address and PID only' 'raw native'
    Stage-W01 $name $p.ExitCode
    $rows = [Text.Encoding]::GetEncoding(28591).GetString([IO.File]::ReadAllBytes($out)) -split '\r?\n'
    $pids = @(foreach ($line in $rows) {
        if ($line -match "^\s*TCP\s+127\.0\.0\.1:${BrowserPort}\s+0\.0\.0\.0:0\s+\S+\s+(\d+)\s*$") { [int]$Matches[1] }
    })
    Require-W01 ($pids.Count -eq 1 -and $pids[0] -eq $first.pid -and $HttpPid -eq [string]$first.pid -and $first.port -eq $BrowserPort -and
        $first.event -ceq 'ready' -and $first.python -ieq $python -and $first.source_sha256 -ieq (FileHash-W01 $serverScript) -and
        $first.inspection_sha256 -ieq (FileHash-W01 $Inspection)) 'New listener PID, verified source or interpreter does not match its receipt.'
    [ordered]@{status=204;pid=$first.pid;port=$BrowserPort;source_sha256=$first.source_sha256} |
        ConvertTo-Json -Compress | Set-Content -LiteralPath (Join-Path $run ($name + '.http-ready.json')) -Encoding UTF8
}
function Invoke-W01Chrome([string]$Name,[string]$Role,[string]$Uri,[string]$Receipt,[switch]$Probe) {
    $profile = (New-Item -ItemType Directory -Path (Join-Path ([IO.Path]::GetTempPath()) ('story25-chrome-' + [guid]::NewGuid().ToString('N')))).FullName
    $chromeProcess = $null
    try {
        $chromeProcess = Start-W01 "chrome-$Name" $Chrome @('--headless=new','--no-first-run','--no-default-browser-check',
            '--disable-background-networking','--disable-extensions',('--user-data-dir='+$profile),
            '--remote-debugging-address=127.0.0.1','--remote-debugging-port=0','about:blank') -Async
        $debug = Join-Path $profile 'DevToolsActivePort'
        Wait-W01 { $chromeProcess.Refresh(); if ($chromeProcess.HasExited) { throw 'Dedicated Chrome exited before capture.' }; Test-Path -LiteralPath $debug -PathType Leaf } 'Chrome debugger readiness timeout.'
        $cdp = Read-W01SharedFirstLine $debug -Ascii
        Require-W01 ($cdp -match '^[0-9]+$' -and [int]$cdp -ge 1024 -and [int]$cdp -ne $BrowserPort) 'Unexpected Chrome debug port.'
        $argv = @($browserScript,'--origin',$Uri,'--debug',$cdp,'--role',$Role,'--out',(Join-Path $run "$Name.jsonl"))
        if ($Probe) { $argv += '--probe'; $marker='STORY25_W01_CHROME_PROBE_OK' }
        else { $argv += @('--inspection',$Receipt,'--accounts',$AccountsJson); $marker='STORY25_CHROME_CAPTURE_OK' }
        $null = Native-W01 "browser-$Name" $node $argv $marker
    } finally {
        if ($chromeProcess -and -not $chromeProcess.HasExited) {
            Stop-Process -Id $chromeProcess.Id -ErrorAction SilentlyContinue
            [void]$chromeProcess.WaitForExit(4000)
        }
        $profileItem = Get-Item -LiteralPath $profile -ErrorAction SilentlyContinue
        if ($profileItem -and $profileItem.Name -cmatch '^story25-chrome-[0-9a-f]{32}$' -and
            $profileItem.Parent.FullName.TrimEnd('\') -ieq ([IO.Path]::GetTempPath()).TrimEnd('\') -and
            -not ($profileItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            Remove-Item -LiteralPath $profileItem.FullName -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

Push-Location -LiteralPath $repo
try {
    Assert-W01Qualification $ToolchainEvidence $support $LiveIoEvidence
    Phase-W01 'qualification' 'complete' $ToolchainEvidence
    $phase = 'A'
    if (-not $Passfile) { $Passfile = $env:PGPASSFILE }
    if (-not $Passfile) { $Passfile = Join-Path $env:LOCALAPPDATA 'LabBooking\PostgreSQL17\pgpass.conf' }
    foreach ($file in @($Passfile,$AccountsJson,$python,$Psql,$Chrome,$InspectionEvidence)) {
        Require-W01 ($file -match '^[A-Za-z]:[\\/]' -and (Test-Path -LiteralPath $file -PathType Leaf)) 'Required executable, read-only receipt or protected local input is unavailable.'
    }
    foreach ($file in @($Passfile,$AccountsJson)) {
        $protected = (Resolve-Path -LiteralPath $file).Path
        Require-W01 (-not $protected.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase) -and
            -not $protected.StartsWith($run+'\',[StringComparison]::OrdinalIgnoreCase)) 'Protected inputs must remain outside the repository and evidence.'
    }
    $prior = ReadPlan-W01 $InspectionEvidence
    $priorDir = Split-Path -Parent $InspectionEvidence
    Require-W01 ($prior.identity.database -ceq 'lab_booking' -and $prior.identity.role -ceq 'lab_booking_app' -and
        $prior.identity.read_only -ceq 'on' -and (FileHash-W01 (Join-Path $priorDir 'acl-and-samples.stdout.txt')) -ceq $prior.raw_stdout_sha256) 'Supplied historical read-only receipt is not bound to its source.'
    $conflicts = @('PGHOST','PGHOSTADDR','PGPORT','PGDATABASE','PGUSER','PGPASSWORD','PGSERVICE','PGSERVICEFILE','PGOPTIONS' |
        Where-Object { Test-Path -LiteralPath "Env:$_" })
    Require-W01 ($conflicts.Count -eq 0) 'Remove conflicting libpq environment overrides before running.'
    Require-W01 ($BrowserPort -notin 8000,8001,5433) 'Use a dedicated smoke port.'
    $socket = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,$BrowserPort)
    try { $socket.Start() } finally { $socket.Stop() }

    $env:PGPASSFILE = $Passfile
    $env:PGCONNECT_TIMEOUT = '5'
    $env:PGCLIENTENCODING = 'UTF8'
    $env:LAB_BOOKING_DB_MODE = 'runtime'
    $env:DJANGO_SETTINGS_MODULE = 'lab_booking.settings'
    $env:LAB_BOOKING_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8:strict'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $null = Native-W01 'python' $python @('--version') 'Python 3.13.17'
    $null = Native-W01 'django-version' $python @('-B','-m','django','--version') '5.2.19'
    $null = Native-W01 'chrome-driver-syntax' $node @('--check',$browserScript) ''
    $null = Native-W01 'node-websocket' $node @('-p','typeof WebSocket') 'function'
    $manifest = Join-Path $certRaw 'before.sha256'
    Require-W01 ((FileHash-W01 $manifest) -ceq (FileHash-W01 (Join-Path $certRaw 'after.sha256'))) 'Independent tested input manifests differ.'
    $inputs = @(Get-W01QualifiedSources $support | ForEach-Object { Join-Path $support $_.Substring(66) })
    foreach ($line in (Read-W01Lines $manifest)) {
        Require-W01 ($line -cmatch '^([0-9A-F]{64})  (.+)$') 'Invalid certified source record.'
        $oldHash=$Matches[1]; $relative=$Matches[2]
        if ($relative -cmatch '^(accounts|equipment|reservations|audit|lab_booking)/|^(manage\.py|requirements\.txt)$') {
            $f=(Resolve-Path -LiteralPath (Join-Path $repo $relative)).Path
            Require-W01 ($f.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase) -and (FileHash-W01 $f) -ceq $oldHash) "Independently verified source drift: $relative"
            $inputs += $f
        }
    }
    $sourceHashes = @($inputs | Sort-Object -Unique | ForEach-Object { (FileHash-W01 $_) + '  ' + $_ })
    $sourceHashes | Set-Content -LiteralPath (Join-Path $run 'inputs-before.sha256') -Encoding UTF8

    $ownerArgs = @('-X','-w','-q','-A','-t','-h','127.0.0.1','-p','5433','-U','lab_booking_migrator','-d','lab_booking','-v','ON_ERROR_STOP=1')
    if (-not $ResumeBrowser) {
    $msql = Join-Path $run 'migration-readonly.sql'
    [IO.File]::WriteAllText($msql,@'
BEGIN READ ONLY;
SET LOCAL statement_timeout = '5s';
SELECT current_database() || '|' || session_user || '|' || host(inet_server_addr()) || '|' || inet_server_port() || '|' || current_setting('server_version_num');
SELECT m.app || '.' || m.name FROM public.django_migrations AS m ORDER BY m.app COLLATE "C",m.name COLLATE "C";
ROLLBACK;
'@,$utf8)
    $migrations = @(Native-W01 'migration-readonly' $Psql ($ownerArgs+@('-f',$msql)) 'lab_booking|lab_booking_migrator|127.0.0.1|5433|170012')
    $certSchema = ReadPlan-W01 (Join-Path $certRaw 'baseline-before.json')
    $expectedMigrations = @($certSchema.schema[1] | ForEach-Object { $_ -join '.' })
    Require-W01 ($migrations.Count -eq 20 -and ($migrations[1..19] -join '|') -ceq ($expectedMigrations -join '|')) 'Formal migration ledger drift; no migration is authorized.'
    }
    $fresh = Inspect-W01 'runtime-before-grant' ''
    $plan = ReadPlan-W01 $fresh
    Phase-W01 'A' 'readback' $fresh
    Assert-W01Window $plan $BrowserPort
    $null = Native-W01 'accounts-readonly' $python @('-B',$serverScript,'--check-accounts',$AccountsJson) 'STORY25_W01_ACCOUNTS_READONLY_OK'
    $uri = "http://127.0.0.1:$BrowserPort"
    if (-not $ResumeBrowser) { Invoke-W01Chrome 'renderer-probe' 'anonymous' $uri '' -Probe }
    Assert-W01Window $plan $BrowserPort
    $missing = @($plan.missing)
    $next = Get-W01NextAction $plan -ResumeBrowser:$ResumeBrowser
    Phase-W01 'A' 'complete' $fresh
    $phase = 'B'
    if ($next -ceq 'grant-missing-only') {
        $grantAttempted = $true
        $grantReceipt = 'commit-not-yet-corroborated'
        Phase-W01 'B' 'started' (Join-Path $run 'grant-column-delta.stdout.txt')
        $null = Native-W01 'grant-column-delta' $Psql ($ownerArgs+@('-v',('expected_missing='+($missing -join ',')),'-f',$grant)) 'STORY25_W01_GRANT_COMMITTED'
        $grantReceipt = 'commit-marker-recorded'
    } else { $grantReceipt = 'skipped-exact-acl'; Stage-W01 'grant-not-needed' 0 }
    Phase-W01 'B' $grantReceipt $fresh
    $phase = 'C'
    $before = Inspect-W01 'runtime-after-grant-before-smoke' $fresh -Snapshot
    $plan = ReadPlan-W01 $before
    Phase-W01 'C' 'complete' $before
    Assert-W01Window $plan $BrowserPort
    $phase = 'D'
    $events = Join-Path $run 'server-http.jsonl'
    $server = Start-W01 'server' $python @('-B',$serverScript,'--inspection',$before,'--events',$events,'--stop-file',$stopped) -Async
    $httpPid = Wait-W01HttpReady $server $BrowserPort
    Verify-W01Listener $events $httpPid $before
    foreach ($role in @('anonymous','student','teacher','admin')) {
        Invoke-W01Chrome $role $role $uri $before
    }
    Stop-W01Server
    Archive-W01StoppedServer
    Stage-W01 'server-stop' $server.ExitCode
    Assert-W01Marker @(Read-W01Lines (Join-Path $run 'server.stdout.txt')) $server.ExitCode 'STORY25_W01_SMOKE_READY'
    Phase-W01 'D' 'complete' $events
    $phase = 'E'
    $after = Inspect-W01 'runtime-after-smoke' $before -Snapshot
    $finish = @('-B',$finishScript,'--before',$before,'--after',$after,'--server',$events,'--result',(Join-Path $run 'smoke-result.json'),'--automated')
    foreach ($role in @('anonymous','student','teacher','admin')) { $finish += @("--$role",(Join-Path $run "$role.jsonl")) }
    $null = Native-W01 'formal-evidence-check' $python $finish 'STORY25_W01_SMOKE_EVIDENCE_OK'
    $afterHashes = @($inputs | Sort-Object -Unique | ForEach-Object { (FileHash-W01 $_) + '  ' + $_ })
    $afterHashes | Set-Content -LiteralPath (Join-Path $run 'inputs-after.sha256') -Encoding UTF8
    Require-W01 (($sourceHashes -join "`n") -ceq ($afterHashes -join "`n")) 'Runtime input drift.'
    if ($LeaveGuardedLink) {
        $last = ReadPlan-W01 $after
        Assert-W01Window $last $BrowserPort
        $live = Start-W01 'server-live' $python @('-B',$serverScript,'--inspection',$after,
            '--events',(Join-Path $run 'server-live-http.jsonl'),'--stop-file',(Join-Path $run 'server-live-stop.flag')) -Async
        $httpPid = Wait-W01HttpReady $live $BrowserPort
        Verify-W01Listener (Join-Path $run 'server-live-http.jsonl') $httpPid $after
    }
    [ordered]@{verified_url=$uri+'/reservations/manage/'; guarded_link_available=[bool]$LeaveGuardedLink;
        guarded_link_deadline=$(if ($LeaveGuardedLink) { $last.samples.safe_until }); granted_columns=@($missing);
        pre_grant=$fresh; before_browser=$before; after_browser=$after} | ConvertTo-Json -Depth 6 |
        Set-Content -LiteralPath (Join-Path $run 'formal-summary.json') -Encoding UTF8
    Phase-W01 'E' 'complete' $after
    Stage-W01 'complete' 0
    'STORY25_W01_FORMAL_OK' | Set-Content -LiteralPath (Join-Path $run 'batch-marker.txt') -Encoding UTF8
    $liveReady = [bool]$LeaveGuardedLink
    Write-Host ('W01 verified URL: '+$uri+'/reservations/manage/')
    if ($liveReady) { Write-Host "Guarded link ends at $($last.samples.safe_until) UTC." }
    'STORY25_W01_FORMAL_OK'
} catch {
    $original = $_
    $original.Exception.Message | Set-Content -LiteralPath (Join-Path $run 'failure.txt') -Encoding UTF8
    Phase-W01 $phase 'failed' (Join-Path $run 'failure.txt')
    $recovery = [ordered]@{failed_phase=$phase; grant_process_receipt=$grantReceipt;
        before_independent_readback=$before; state_source='fresh read-only evidence only'; acl_readback=$null; post_failure=$null}
    try {
        Stop-W01Server
        if ($before -and -not $after) { $recovery.post_failure = Inspect-W01 'failure-business-readback' $before -Snapshot }
    } catch { $recovery['post_failure_error'] = $_.Exception.Message }
    try { Archive-W01StoppedServer } catch { $recovery['server_archive_error'] = $_.Exception.Message }
    if ($grantAttempted -or $before) {
        try { $recovery.acl_readback = Inspect-W01 'failure-acl-readback' '' }
        catch { $recovery['acl_readback_error'] = $_.Exception.Message }
    }
    $recovery | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $run 'recovery.json') -Encoding UTF8
    throw $original
} finally {
    try { Stop-W01Server } finally {
        if ($live -and -not $liveReady -and -not $live.HasExited) { Stop-Process -Id $live.Id -ErrorAction SilentlyContinue }
        foreach ($name in $bindings) { [Environment]::SetEnvironmentVariable($name,$old[$name],'Process') }
        Pop-Location
    }
}
