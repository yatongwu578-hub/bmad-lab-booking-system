[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$FixturePython,
    [string]$PgBin = 'C:\Program Files\PostgreSQL\17\bin',
    [string]$Chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe',
    [string]$Node = (Get-Command node.exe -ErrorAction Stop).Source,
    [string]$OutputRoot = 'F:\softwork\outputs',
    [string]$ResumeFrom,
    [string]$FormalInspectionEvidence
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'w01-log-contract.ps1')
Set-W01WireEncoding
. (Join-Path $PSScriptRoot 'w01-recovery-policy.ps1')
$port = 55435
$browserPort = 49173
$guid = [guid]::NewGuid().ToString('N')
$run = Join-Path $OutputRoot ('story-2-5-w01-toolchain-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + $guid)
$null = New-Item -ItemType Directory -Path $run
Write-Host "W01 TOOLCHAIN evidence: $run"
$private = Join-Path ([IO.Path]::GetTempPath()) ('story25-w01-tool-fixture-' + $guid)
$null = New-Item -ItemType Directory -Path $private
$data = Join-Path $private 'data'
$pass = Join-Path $private 'pgpass.conf'
$initPass = Join-Path $private 'init.pw'
$bootstrap = Join-Path $private 'bootstrap.sql'
$psql = Join-Path $PgBin 'psql.exe'
$psExe = Join-Path $PSHOME 'powershell.exe'
$server = $null
$caseLog = [System.Collections.Generic.List[string]]::new()
$envBefore = @{}
$utf8 = [Text.UTF8Encoding]::new($false,$true)
$grant = Join-Path $PSScriptRoot 'story-2-5-w01-grant.sql'
$inspector = Join-Path $PSScriptRoot 'inspect-story-2-5-w01.ps1'
$allowed = 'actor_id,before_status,after_status,decision_at,recorded_at'
$serverVersion = $null
$sources = @(Get-W01QualifiedSources $PSScriptRoot)
$formalAnchor = $null

function Assert-Tool($Value,[string]$Why) { if (-not $Value) { throw $Why } }
function Note-Tool([string]$Name) {
    $caseLog.Add($Name)
    Add-Content -LiteralPath (Join-Path $run 'cases.txt') -Value $Name -Encoding UTF8
}
function Invoke-Tool([string]$Name,[string]$Exe,[string[]]$Argv,[switch]$ReadOnFailure,[switch]$NativeDiagnostic) {
    $stem = Join-Path $run $Name
    if (Test-Path -LiteralPath "$stem.exit") { throw "Repeated native stage $Name" }
    if (@($Argv | Where-Object { $_ -match '"' }).Count) { throw "Unexpected quote in native args for $Name" }
    $proc = Start-Process -FilePath $Exe -ArgumentList (($Argv | ForEach-Object { '"' + $_ + '"' }) -join ' ') -Wait -PassThru -WindowStyle Hidden -RedirectStandardOutput "$stem.stdout" -RedirectStandardError "$stem.stderr"
    $proc.ExitCode | Set-Content -LiteralPath "$stem.exit" -Encoding ASCII
    $profile = if ($NativeDiagnostic) { 'raw native diagnostic; no protocol parse' } else { 'UTF-8 W01 protocol on expected branch' }
    Write-W01NativeReceipt "$stem.native.json" "$stem.stdout" "$stem.stderr" $proc.ExitCode $profile 'raw diagnostics'
    $out = @()
    if (-not $NativeDiagnostic -and ($proc.ExitCode -eq 0 -or $ReadOnFailure)) { $out = @(Read-W01Lines "$stem.stdout") }
    [pscustomobject]@{ Code=$proc.ExitCode; Out=$out; OutPath="$stem.stdout"; ErrPath="$stem.stderr" }
}
function Read-Fixture([string]$Name,[switch]$Snapshot,[string]$Before,[string]$Failure) {
    $nativeArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$inspector,'-ToolFixture',
        '-Passfile',$pass,'-OutputRoot',$run,'-BrowserPort',"$browserPort",'-Psql',$psql)
    if ($Snapshot) { $nativeArgs += '-CaptureSnapshot' }
    if ($Before) { $nativeArgs += @('-BeforeEvidence',$Before) }
    $native = Invoke-Tool $Name $psExe $nativeArgs -ReadOnFailure:([bool]$Failure)
    if (-not $Failure) { Assert-Tool ($native.Code -eq 0) "$Name exited $($native.Code); see raw logs" }
    $p = @($native.Out | Where-Object { $_ -clike 'W01 evidence: *' })
    Assert-Tool ($p.Count -eq 1) "$Name missing one inspection archive path"
    $dir = $p[0].Substring('W01 evidence: '.Length)
    $json = Join-Path $dir 'w01-inspect.json'
    $batch = Join-Path $dir 'batch-marker.txt'
    if ($Failure) {
        Assert-Tool ($native.Code -ne 0 -and -not (Test-Path -LiteralPath $batch) -and
            ((Read-W01Text (Join-Path $dir 'inspect-failure.txt')).Contains($Failure))) "$Name did not fail closed: $Failure"
        return
    }
    Assert-Tool ($native.Code -eq 0 -and @($native.Out | Where-Object { $_ -ceq 'STORY25_W01_INSPECT_OK' }).Count -eq 1 -and
        (@(Read-W01Lines $batch).Count -eq 1) -and (@(Read-W01Lines $batch)[0] -ceq 'STORY25_W01_INSPECT_OK')) "$Name readback failed"
    [pscustomobject]@{ Path=$json; Value=(Read-W01Text $json | ConvertFrom-Json) }
}
function Invoke-FixtureSql([string]$Name,[string]$Sql) {
    $path = Join-Path $run "$Name.sql"
    [IO.File]::WriteAllText($path,"\set ON_ERROR_STOP on`n\set VERBOSITY verbose`n" + $Sql,$utf8)
    $res = Invoke-Tool $Name $psql (@('-U','lab_booking_migrator','-d','test_lab_booking') + $common + @('-f',$path))
    Assert-Tool ($res.Code -eq 0) "$Name fixture SQL failed"
    $res.Out
}
function Invoke-FixtureAdmin([string]$Name,[string]$Sql) {
    $path = Join-Path $run "$Name.sql"
    [IO.File]::WriteAllText($path,"\set ON_ERROR_STOP on`n" + $Sql,$utf8)
    $res = Invoke-Tool $Name $psql (@('-U','fixture_admin','-d','test_lab_booking') + $common + @('-f',$path))
    Assert-Tool ($res.Code -eq 0) "$Name disposable fixture administration failed"
}
function Test-Grant([string]$Name,[string]$Expected,[int]$Count,[string]$Failure) {
    $g = Invoke-Tool $Name $psql (@('-U','lab_booking_migrator','-d','test_lab_booking') + $common +
        @('-v','w01_fixture=true','-v',("expected_missing=" + $Expected),'-f',$grant))
    $marks = @($g.Out | Where-Object { $_ -ceq 'STORY25_W01_GRANT_COMMITTED' }).Count
    if ($Failure) {
        Assert-Tool ($g.Code -eq 3 -and -not (Test-W01AsciiDiagnostic $g.OutPath '(?m)^STORY25_W01_GRANT_COMMITTED\r?$') -and
            (Test-W01AsciiDiagnostic $g.ErrPath ('\bP0001:\s*' + [regex]::Escape($Failure)))) "$Name did not record the matching failed SQLSTATE/exit"
    } else {
        Assert-Tool ($g.Code -eq 0 -and $marks -eq 1 -and
            (Test-W01AsciiDiagnostic $g.ErrPath "W01 exact SELECT delta count=$Count(?:\D|$)")) "$Name unexpected committed delta"
    }
    Note-Tool $Name
}
function Import-PassedFixtureCases([string]$Directory) {
    $proof = [ordered]@{
        'cases.txt'='78AC0F5149DCFD5C0C3468CAF636BABF186ECE29DA5BB80108AAA715521A4A6C'
        'audited-sources-not-qualification.sha256'='3DF2C78D6D734D2D44B8F9A4E5C4593F477F912949F2E08DBD7E4B740A4558AB'
        'shutdown.exit'='13BF7B3039C63BF5A50491FA3CFD8EB4E699D1BA1436315AEF9CBE5711530354'
        'b-after-grant-rollback-confirmed.stderr'='C0A1AB5BC893FF6FCE1D6188BDE328B95BBD81EA65D1193F879230499BE61A8D'
        'b-after-grant-rollback-confirmed.exit'='24BA1E99DC06B19351323AAE0D7370243D586475A634B7F6FF7927FBC72CFAED'
        'b-grant-unsorted-exact.stdout'='694AD3F225C3D005A410EF67E811108745BB42B048AFD73214B8868CD16E1100'
        'b-grant-unsorted-exact.exit'='13BF7B3039C63BF5A50491FA3CFD8EB4E699D1BA1436315AEF9CBE5711530354'
        'e-post-drift-rejected.exit'='F1B2F662800122BED0FF255693DF89C4487FBDCF453D3524A42D4EC20C3D9C04'
    }
    foreach ($name in $proof.Keys) {
        Assert-Tool ((Get-FileHash -LiteralPath (Join-Path $Directory $name)).Hash -ceq $proof[$name]) "Prior partial receipt changed: $name"
    }
    $baselineSources=@(Read-W01Lines (Join-Path $Directory 'audited-sources-not-qualification.sha256'))
    foreach ($name in @('story-2-5-w01-grant.sql','story-2-5-w01-inspect.sql','story-2-5-w01-snapshot.sql')) {
        $entry=(Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $name)).Hash + '  ' + $name
        Assert-Tool ($entry -cin $baselineSources) "Reused SQL source changed: $name"
    }
    $oldCases=@(Read-W01Lines (Join-Path $Directory 'cases.txt'))
    Assert-Tool ($oldCases.Count -eq 17 -and @($oldCases | Sort-Object -Unique).Count -eq 17) 'Prior SQL case list is not exact'
    foreach ($name in $oldCases) { $caseLog.Add($name) }
    [ordered]@{ original=(Resolve-Path -LiteralPath $Directory).Path; reused_case_count=$oldCases.Count; files_sha256=$proof;
        unchanged_sql=$true; scope='17 completed cases only; no browser qualification reused' } |
        ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $run 'reused-qualification.json') -Encoding UTF8
    $oldCases | Set-Content -LiteralPath (Join-Path $run 'reused-cases.txt') -Encoding UTF8
}

try {
    foreach ($exe in @($psExe,$psql,$Chrome,$Node,$FixturePython)) {
        Assert-Tool (Test-Path -LiteralPath $exe -PathType Leaf) "Missing prerequisite: $exe"
    }
    foreach ($name in @('PGPASSFILE','PGCONNECT_TIMEOUT','PGCLIENTENCODING','PGHOST','PGHOSTADDR','PGPORT','PGDATABASE',
                         'PGUSER','PGPASSWORD','PGSERVICE','PGSERVICEFILE','PGOPTIONS','PGSSLMODE','PYTHONUTF8','PYTHONIOENCODING')) {
        $envBefore[$name] = [Environment]::GetEnvironmentVariable($name,'Process')
        [Environment]::SetEnvironmentVariable($name,$null,'Process')
    }
    $env:PGPASSFILE = $pass
    $env:PGCONNECT_TIMEOUT = '3'
    $env:PGCLIENTENCODING = 'UTF8'
    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8:strict'
    $enc = Invoke-Tool 'verify-log-contract' $psExe @('-NoProfile','-ExecutionPolicy','Bypass','-File',
        (Join-Path $PSScriptRoot 'test-w01-log-contract.ps1'),'-OutputRoot',$run)
    Assert-W01Marker $enc.Out $enc.Code 'STORY25_W01_ENCODING_OK'
    if ($ResumeFrom) { Import-PassedFixtureCases $ResumeFrom }
    if ($FormalInspectionEvidence) {
        # Validate the offline receipt only. Never open the formal database here.
        $formalAnchor = (Resolve-Path -LiteralPath $FormalInspectionEvidence).Path
        $prior = Read-W01Text $formalAnchor | ConvertFrom-Json
        $raw = Join-Path (Split-Path -Parent $formalAnchor) 'acl-and-samples.stdout.txt'
        Assert-Tool ($prior.identity.database -ceq 'lab_booking' -and $prior.identity.role -ceq 'lab_booking_app' -and
            $prior.identity.read_only -ceq 'on' -and $prior.desired_port -eq 8005 -and
            (Get-FileHash -LiteralPath $raw).Hash -ceq $prior.raw_stdout_sha256) 'Invalid formal read-only anchor'
    }
    foreach ($portNumber in @($port,$browserPort)) {
        $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,$portNumber)
        $listener.ExclusiveAddressUse = $true
        try { $listener.Start() } finally { $listener.Stop() }
    }
    $superPw = [guid]::NewGuid().ToString('N')
    $ownerPw = [guid]::NewGuid().ToString('N')
    $appPw = [guid]::NewGuid().ToString('N')
    [IO.File]::WriteAllText($initPass,"$superPw`n",$utf8)
    [IO.File]::WriteAllLines($pass,@("127.0.0.1:${port}:*:fixture_admin:$superPw",
        "127.0.0.1:${port}:test_lab_booking:lab_booking_migrator:$ownerPw",
        "127.0.0.1:${port}:test_lab_booking:lab_booking_app:$appPw"),$utf8)
    $init = Invoke-Tool 'initdb' (Join-Path $PgBin 'initdb.exe') @('-D',$data,'-U','fixture_admin',
        '--auth-host=scram-sha-256','--auth-local=scram-sha-256',"--pwfile=$initPass",'--encoding=UTF8','--locale=C','--no-instructions') -NativeDiagnostic
    Assert-Tool ($init.Code -eq 0) 'initdb failed'
    $server = Start-Process (Join-Path $PgBin 'postgres.exe') -ArgumentList ('-D "' + $data + '" -h 127.0.0.1 -p ' + $port) -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $run 'postgres.stdout') -RedirectStandardError (Join-Path $run 'postgres.stderr')
    $common = @('-X','-w','-q','-A','-t','-h','127.0.0.1','-p',"$port",'-v','ON_ERROR_STOP=1')
    for ($i=0; $i -lt 15; $i++) {
        $version = Invoke-Tool "version-$i" $psql (@('-U','fixture_admin','-d','postgres') + $common + @('-c','SHOW server_version'))
        if ($version.Code -eq 0) { break }
        if ($server.HasExited) { throw 'Disposable postgres exited before readiness' }
        Start-Sleep -Milliseconds 300
    }
    Assert-Tool ($version.Code -eq 0 -and $version.Out.Count -eq 1 -and $version.Out[0] -match '^17\.12(?:\s|$)') 'Disposable PostgreSQL is not 17.12'
    $serverVersion = ($version.Out[0] -split '\s+')[0]
    $seedRoles = @'
\set ON_ERROR_STOP on
DO $body$
BEGIN
    IF current_database() <> 'postgres' OR current_user <> 'fixture_admin' OR inet_server_port() <> 55435
       OR host(inet_server_addr()) <> '127.0.0.1' THEN RAISE EXCEPTION 'Not the disposable tool fixture'; END IF;
END
$body$;
CREATE ROLE lab_booking_migrator LOGIN PASSWORD '@OWNER@';
CREATE ROLE lab_booking_app LOGIN PASSWORD '@APP@';
CREATE DATABASE test_lab_booking OWNER lab_booking_migrator;
'@
    [IO.File]::WriteAllText($bootstrap,$seedRoles.Replace('@OWNER@',$ownerPw).Replace('@APP@',$appPw),$utf8)
    $init2 = Invoke-Tool 'bootstrap' $psql (@('-U','fixture_admin','-d','postgres') + $common + @('-f',$bootstrap))
    Assert-Tool ($init2.Code -eq 0) 'Disposable fixture bootstrap failed'
    $null = Invoke-FixtureSql 'seed-fixture' @'
CREATE TABLE public.audit_operationhistory (
 id bigint PRIMARY KEY, action text, actor_id bigint, actor_type text, before_status text, after_status text,
 decision_at timestamptz, equipment_id bigint, object_type text, reason text, recorded_at timestamptz, reservation_id bigint);
CREATE TABLE public.reservations_reservation (id bigint PRIMARY KEY, equipment_id bigint, applicant_id bigint,
 status text, start_at timestamptz, end_at timestamptz, applied_at timestamptz);
CREATE TABLE public.equipment_equipment (id bigint PRIMARY KEY, number text, name text, category text, location text, description text, status text);
CREATE TABLE public.accounts_user (id bigint PRIMARY KEY, username text, role text, is_active boolean,
 is_staff boolean, is_superuser boolean, password text, last_login timestamptz);
CREATE TABLE public.django_session (session_key text);
INSERT INTO public.equipment_equipment VALUES (1,'FIXTURE-1','Synthetic One','fixture','fixture','fixture','available'),
 (2,'FIXTURE-2','Synthetic Two','fixture','fixture','fixture','available');
INSERT INTO public.accounts_user VALUES (1,'fixture_admin','admin',true,false,false,'synthetic',NULL),
 (2,'fixture_student','student',true,false,false,'synthetic',NULL),(3,'fixture_teacher','teacher',true,false,false,'synthetic',NULL);
INSERT INTO public.reservations_reservation VALUES
 (1,1,2,'expired',now()-interval '3 days',now()-interval '2 days',now()-interval '4 days'),
 (2,2,3,'pending',now()+interval '2 days',now()+interval '3 days',now()-interval '1 day');
INSERT INTO public.audit_operationhistory VALUES
 (1,'expire',NULL,'system','pending','expired',now()-interval '3 days',1,'reservation',U&'\8FC7\671F',now()-interval '3 days',1);
GRANT SELECT ON public.accounts_user, public.reservations_reservation, public.equipment_equipment TO lab_booking_app;
GRANT UPDATE(last_login) ON public.accounts_user TO lab_booking_app;
GRANT UPDATE(status) ON public.reservations_reservation,public.equipment_equipment TO lab_booking_app;
GRANT SELECT,INSERT,UPDATE,DELETE ON public.django_session TO lab_booking_app;
GRANT INSERT(action,actor_id,actor_type,before_status,after_status,decision_at,equipment_id,object_type,reason,recorded_at,reservation_id)
 ON public.audit_operationhistory TO lab_booking_app;
GRANT SELECT(id,reservation_id,action,actor_type,reason) ON public.audit_operationhistory TO lab_booking_app;
'@
    if ($ResumeFrom) {
        $a = Read-Fixture 'resume-a-encoding-readback'
        Assert-W01Window $a.Value $browserPort
        Test-Grant 'resume-b-prepare-disposable-fixture' ($a.Value.missing -join ',') 5
        $baseline = Read-Fixture 'resume-c-fresh-browser-snapshot' -Snapshot -Before $a.Path
        Assert-Tool ((Get-W01NextAction $baseline.Value -ResumeBrowser) -ceq 'skip-grant') 'Fresh fixture cannot safely resume browser'
    } else {
    $empty = @(Invoke-FixtureSql 'null-empty-acl' "SELECT (SELECT count(*) FROM aclexplode(CASE WHEN cardinality(NULL::aclitem[])>0 THEN NULL::aclitem[] END)) || '|' || (SELECT count(*) FROM aclexplode(CASE WHEN cardinality(ARRAY[]::aclitem[])>0 THEN ARRAY[]::aclitem[] END));")
    Assert-Tool ($empty.Count -eq 1 -and $empty[0] -ceq '0|0') 'NULL/empty ACL guard failed'
    Note-Tool 'null-empty-acl'
    $a = Read-Fixture 'a-all-missing'
    Assert-Tool (($a.Value.missing -join ',') -ceq $allowed -and (Get-W01NextAction $a.Value) -ceq 'grant-missing-only') 'A failed to classify five absent grants'
    Assert-W01Window $a.Value $browserPort
    Note-Tool 'a-all-missing'
    Test-Grant 'b-grant-unsorted-exact' $allowed 5
    $c = Read-Fixture 'c-readback-five' -Snapshot -Before $a.Path
    Assert-Tool ((Get-W01NextAction $c.Value -ResumeBrowser) -ceq 'skip-grant') 'Resume failed to skip B'
    Note-Tool 'c-readback-five'
    Test-Grant 'b-zero-delta-in-fixture-only' '' 0
    $null = Read-Fixture 'c-zero-delta-unchanged' -Snapshot -Before $c.Path
    $null = Invoke-FixtureSql 'set-partial' "REVOKE SELECT (before_status,after_status,recorded_at) ON public.audit_operationhistory FROM lab_booking_app;"
    $partial = Read-Fixture 'a-partial'
    Assert-Tool (($partial.Value.missing -join ',') -ceq 'before_status,after_status,recorded_at') 'A missed partial ACL'
    $resumed = $false
    try { $null = Get-W01NextAction $partial.Value -ResumeBrowser; $resumed = $true } catch {}
    Assert-Tool (-not $resumed) 'Browser-only recovery would have allowed write'
    Test-Grant 'b-stale-plan-rejected' 'before_status,after_status' 0 'Current ACL set differs'
    Test-Grant 'b-duplicate-plan-rejected' 'before_status,after_status,recorded_at,recorded_at' 0 'Current ACL set differs'
    $r = Read-Fixture 'a-after-denied-grants'
    Assert-Tool (($r.Value.missing -join ',') -ceq ($partial.Value.missing -join ',')) 'Failed transaction changed rights'
    Invoke-FixtureAdmin 'inject-after-grant-rollback' @'
CREATE FUNCTION public.fixture_add_out_of_scope_acl() RETURNS event_trigger LANGUAGE plpgsql AS $f$
BEGIN
    IF session_user='lab_booking_migrator' AND current_setting('w01_fixture.in_fault',true) IS DISTINCT FROM 'yes' THEN
        PERFORM set_config('w01_fixture.in_fault','yes',true);
        EXECUTE 'GRANT SELECT (object_type) ON public.audit_operationhistory TO lab_booking_app';
    END IF;
END
$f$;
CREATE EVENT TRIGGER w01_post_grant_fault ON ddl_command_end WHEN TAG IN ('GRANT')
EXECUTE FUNCTION public.fixture_add_out_of_scope_acl();
'@
    Test-Grant 'b-after-grant-rollback-confirmed' 'recorded_at,before_status,after_status' 0 'Unexpected post-grant history ACL'
    Invoke-FixtureAdmin 'remove-after-grant-fault' 'DROP EVENT TRIGGER w01_post_grant_fault; DROP FUNCTION public.fixture_add_out_of_scope_acl();'
    $rollback = Read-Fixture 'c-confirmed-rollback-fresh-acl'
    Assert-Tool (($rollback.Value.missing -join ',') -ceq ($partial.Value.missing -join ',')) 'Post-GRANT rollback did not keep the prior ACL'
    Test-Grant 'b-grant-partial' 'recorded_at,before_status,after_status' 3
    $null = Read-Fixture 'c-readback-partial' -Snapshot -Before $partial.Path
    foreach ($case in @(
        @{Key='table'; Add='GRANT SELECT ON'; Undo='REVOKE SELECT ON'; Who='PUBLIC'; Message='Unexpected table-level'},
        @{Key='extra-column'; Add='GRANT SELECT (object_type) ON'; Undo='REVOKE SELECT (object_type) ON'; Message='Unexpected history projection'},
        @{Key='grant-option'; Add='GRANT SELECT (decision_at) ON'; Undo='REVOKE GRANT OPTION FOR SELECT (decision_at) ON'; Tail=' WITH GRANT OPTION'; Message='Unexpected history projection'})) {
        $grantee = if ($case.Who) { $case.Who } else { 'lab_booking_app' }
        $null = Invoke-FixtureSql ('inject-' + $case.Key) ("$($case.Add) public.audit_operationhistory TO $grantee$($case.Tail);")
        Read-Fixture ('a-deny-' + $case.Key) -Failure $case.Message
        Test-Grant ('b-deny-' + $case.Key) '' 0 'Unexpected current history ACL'
        $null = Invoke-FixtureSql ('undo-' + $case.Key) ("$($case.Undo) public.audit_operationhistory FROM $grantee;")
    }
    $null = Invoke-FixtureSql 'inject-risk' "REVOKE SELECT (recorded_at) ON public.audit_operationhistory FROM lab_booking_app; UPDATE public.reservations_reservation SET start_at=now()-interval '1 minute' WHERE id=2;"
    $risky = Read-Fixture 'a-risk'
    Assert-Tool ($risky.Value.samples.full_unsafe_pending -eq 1) 'Risky row in an unfiltered scope was missed'
    $riskyAllowed = $false
    try { Assert-W01Window $risky.Value $browserPort; $riskyAllowed = $true } catch {}
    Assert-Tool (-not $riskyAllowed) 'Runner did not block full-scope risk'
    Test-Grant 'b-risk-denied' 'recorded_at' 0 'FR-018 risk in full query scope'
    $riskyAfter = Read-Fixture 'a-risk-no-grant'
    Assert-Tool (($riskyAfter.Value.missing -join ',') -ceq 'recorded_at') 'Risk branch granted a column'
    $null = Invoke-FixtureSql 'restore-fixture-window' "UPDATE public.reservations_reservation SET start_at=now()+interval '2 days' WHERE id=2;"
    $restored = Read-Fixture 'a-restored'
    Test-Grant 'b-restore-one' 'recorded_at' 1
    $baseline = Read-Fixture 'c-before-browser' -Snapshot -Before $restored.Path
    $lost = Read-Fixture 'c-lost-transport-receipt-readback' -Snapshot -Before $baseline.Path
    Assert-Tool ((Get-W01NextAction $lost.Value -ResumeBrowser) -ceq 'skip-grant') 'Known-present ACL did not resolve an unknown commit receipt'
    Note-Tool 'lost-receipt-resolved-with-fresh-acl'
    $elapsedAllowed = $false
    try {
        Assert-W01Window $baseline.Value $browserPort ([DateTimeOffset]::Parse($baseline.Value.samples.safe_until))
        $elapsedAllowed = $true
    } catch {}
    Assert-Tool (-not $elapsedAllowed) 'Expired evidence window was accepted'
    $busy = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,$browserPort)
    $busy.ExclusiveAddressUse = $true
    try {
        $busy.Start()
        $busyA = Read-Fixture 'a-port-busy'
        Assert-Tool ($busyA.Value.port_in_use_at_inspection -eq $true) 'Inspector missed a real occupied loopback port'
    } finally { $busy.Stop() }
    Note-Tool 'expired-window-and-occupied-port-rejected'
    $null = Invoke-FixtureSql 'inject-business-drift' "UPDATE public.equipment_equipment SET status='maintenance' WHERE id=1;"
    Read-Fixture 'e-post-drift-rejected' -Snapshot -Before $baseline.Path -Failure 'Business snapshot drift'
    $null = Invoke-FixtureSql 'restore-fixture-row' "UPDATE public.equipment_equipment SET status='available' WHERE id=1;"
    $null = Read-Fixture 'e-restored-baseline' -Snapshot -Before $baseline.Path
    Note-Tool 'business-drift-blocked'
    }
    $chromeTest = Join-Path $PSScriptRoot 'test-story-2-5-w01-browser.py'
    $driverArgs = @('-B',$chromeTest,'--before',$baseline.Path,'--chrome',$Chrome,'--node',$Node)
    $stoppedDir = Join-Path $run 'browser-aborted'
    $stopped = Invoke-Tool 'd-injected-real-browser-stop' $FixturePython ($driverArgs + @('--archive',$stoppedDir,'--inject-browser-stop'))
    Assert-Tool ($stopped.Code -eq 0 -and @($stopped.Out | Where-Object { $_ -ceq 'W01_TOOL_BROWSER_STOP_CONFIRMED' }).Count -eq 1) "Injected browser stop did not reach its expected outcome (fixture exit=$($stopped.Code)); see browser-aborted raw logs"
    $recovery = Read-Fixture 'e-after-failed-browser' -Snapshot -Before $baseline.Path
    Assert-Tool ((Get-W01NextAction $recovery.Value -ResumeBrowser) -ceq 'skip-grant') 'Browser failure would require repeated B'
    Note-Tool 'post-commit-browser-failure-independent-readback-skip-B'
    Assert-W01Window $recovery.Value $browserPort
    $chromeDir = Join-Path $run 'browser'
    $chromeOk = Invoke-Tool 'd-resume-real-chrome' $FixturePython (@('-B',$chromeTest,'--before',$recovery.Path,'--chrome',$Chrome,'--node',$Node,'--archive',$chromeDir))
    Assert-Tool ($chromeOk.Code -eq 0 -and @($chromeOk.Out | Where-Object { $_ -ceq 'W01_TOOL_REAL_CHROME_OK' }).Count -eq 1) 'Real Chrome/CDP fixture failed'
    $post = Read-Fixture 'e-after-real-chrome' -Snapshot -Before $recovery.Path
    $checker = Join-Path $PSScriptRoot 'check-story-2-5-w01-smoke.py'
    $check = Invoke-Tool 'e-offline-correlate' $FixturePython @($checker,'--before',$recovery.Path,'--after',$post.Path,
        '--server',(Join-Path $chromeDir 'server.jsonl'),'--anonymous',(Join-Path $chromeDir 'anonymous.jsonl'),
        '--student',(Join-Path $chromeDir 'student.jsonl'),'--teacher',(Join-Path $chromeDir 'teacher.jsonl'),
        '--admin',(Join-Path $chromeDir 'admin.jsonl'),'--result',(Join-Path $run 'browser-result.json'),'--automated','--tool-fixture')
    Assert-Tool ($check.Code -eq 0 -and @($check.Out | Where-Object { $_ -ceq 'STORY25_W01_SMOKE_EVIDENCE_OK' }).Count -eq 1) 'Offline evidence checker failed'
} catch {
    $_ | Out-String | Set-Content -LiteralPath (Join-Path $run 'failure.txt') -Encoding UTF8
    throw
} finally {
    try {
        if ($server -and -not $server.HasExited) {
            $shutdown = Invoke-Tool 'shutdown' (Join-Path $PgBin 'pg_ctl.exe') @('-D',$data,'-m','fast','-w','-t','10','stop') -NativeDiagnostic
            Assert-Tool ($shutdown.Code -eq 0 -and $server.WaitForExit(10000)) 'Disposable PostgreSQL did not stop'
        }
    } finally {
        foreach ($name in $envBefore.Keys) { [Environment]::SetEnvironmentVariable($name,$envBefore[$name],'Process') }
        foreach ($item in @($initPass,$pass,$bootstrap)) {
            if (Test-Path -LiteralPath $item) { Remove-Item -LiteralPath $item -ErrorAction Stop }
        }
        if ((-not $server -or $server.HasExited) -and -not (Test-Path -LiteralPath (Join-Path $data 'postmaster.pid'))) {
            $scratch = Get-Item -LiteralPath $private
            if ($scratch.Name -ceq ('story25-w01-tool-fixture-' + $guid) -and
                $scratch.Parent.FullName.TrimEnd('\') -ieq ([IO.Path]::GetTempPath()).TrimEnd('\') -and
                -not ($scratch.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
                Remove-Item -LiteralPath $scratch.FullName -Recurse -Force
            }
        }
        [ordered]@{postgres_started=[bool]$server; postgres_exited=($null -eq $server -or $server.HasExited);
            scratch_remaining=(Test-Path -LiteralPath $private)} |
            ConvertTo-Json -Compress | Set-Content -LiteralPath (Join-Path $run 'fixture-cleanup.json') -Encoding UTF8
    }
}
Assert-Tool ($server -and $server.HasExited) 'Missing PostgreSQL cleanup evidence'
Assert-Tool (-not (Test-Path -LiteralPath $private)) 'Disposable PostgreSQL scratch directory was not removed'
Assert-Tool (($sources -join "`n") -ceq ((Get-W01QualifiedSources $PSScriptRoot) -join "`n")) 'Source hashes changed during qualification'
$sources | Set-Content -LiteralPath (Join-Path $run 'tools.sha256') -Encoding UTF8
[ordered]@{ target='127.0.0.1:55435/test_lab_booking'; server_version=$serverVersion; fixture_stopped=$true
    encoding_contract='utf8-wire-and-raw-native-v1'
    browser='real Chrome, local synthetic fixture'; sql_cases=$caseLog.Count
    reused_case_count=$(if ($ResumeFrom) {17} else {0}); passed_cases=$caseLog.ToArray() } |
    ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $run 'qualification.json') -Encoding UTF8
$entryPath = $null
if ($formalAnchor) {
    $entryPath = Join-Path $run 'formal-ready.ps1'
    $entry = @'
[CmdletBinding()]
param([switch]$ResumeBrowser,[switch]$LeaveGuardedLink)
$ErrorActionPreference = 'Stop'
$scriptFile = @RUN_SCRIPT@
$receipt = @FORMAL_INSPECTION@
$launcher = @POWERSHELL@
$cli = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$scriptFile,
    '-InspectionEvidence',$receipt,'-ToolchainEvidence',$PSScriptRoot,'-BrowserPort','8005')
if ($ResumeBrowser) { $cli += '-ResumeBrowser' }
if ($LeaveGuardedLink) { $cli += '-LeaveGuardedLink' }
& $launcher @cli
exit $LASTEXITCODE
'@
    $entry = $entry.Replace('@RUN_SCRIPT@',("'" + (Join-Path $PSScriptRoot 'run-story-2-5-w01-formal.ps1').Replace("'","''") + "'")).
        Replace('@FORMAL_INSPECTION@',("'" + $formalAnchor.Replace("'","''") + "'")).
        Replace('@POWERSHELL@',("'" + $psExe.Replace("'","''") + "'"))
    $tokens=$null; $parseError=$null
    $null=[Management.Automation.Language.Parser]::ParseInput($entry,[ref]$tokens,[ref]$parseError)
    Assert-Tool (@($parseError).Count -eq 0) 'Generated formal entry did not parse'
    $entry | Set-Content -LiteralPath $entryPath -Encoding UTF8
}
'STORY25_W01_TOOLCHAIN_OK' | Set-Content -LiteralPath (Join-Path $run 'batch-marker.txt') -Encoding UTF8
if ($entryPath) { Write-Output "W01 formal entry: $entryPath" }
'STORY25_W01_TOOLCHAIN_OK'
