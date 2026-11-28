param([switch]$PrepareOnly)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$root = 'F:\softwork\outputs'
$prep = Join-Path $root 'experiment-a-preparation-10c193e\integration-prep-20261128'
$verifiedRunner = Join-Path $prep 'run-formal-detail-26-27.ps1'
$w = Join-Path $PSScriptRoot 'story-2-5-review-support'
$pass = 'C:\Users\15860\AppData\Local\LabBooking\PostgreSQL17\pgpass.conf'
$accounts = 'C:\Users\15860\AppData\Local\LabBooking\Protected\accounts.json'
$chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
$psql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe'
$python = Join-Path $repo '.venv\Scripts\python.exe'
$node = (Get-Command node.exe -CommandType Application).Source
$port = 8007
. (Join-Path $w 'w01-log-contract.ps1')
Set-W01WireEncoding
$utf8 = [Text.UTF8Encoding]::new($false)
if ((Get-FileHash -LiteralPath $verifiedRunner).Hash -cne '4AEF188527D66702BBAB0DABAC653EE36A20556ECB9F29F290F504CBD967138D') {
    throw 'Verified Story 2.6/2.7 runner differs from the accepted version.'
}
$tokens=$null; $parseErrors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($verifiedRunner,[ref]$tokens,[ref]$parseErrors)
if ($parseErrors.Count) { throw 'Could not read verified runner functions.' }
$functionNames=@('Need','ReadJson','Sha','Start-Log','Record','Native','Inspect','Check-GuardReady','Launch-Chrome')
foreach($name in $functionNames) {
    $definition=@($ast.EndBlock.Statements | Where-Object { $_ -is [Management.Automation.Language.FunctionDefinitionAst] -and $_.Name -ceq $name })
    if ($definition.Count -ne 1) { throw "Missing verified function $name." }
    . ([scriptblock]::Create($definition[0].Extent.Text))
}

function Swap28([string]$source,[string]$from,[string]$to) {
    Need ([regex]::Matches($source,[regex]::Escape($from)).Count -eq 1) "Adapter anchor changed: $from"
    $source.Replace($from,$to)
}
function Sources28 {
    $beforeHashes = Join-Path $PSScriptRoot 'story-2-8-run-20261128-234855-694\source-before.sha256'
    $found=0
    foreach($line in Read-W01Lines $beforeHashes) {
        Need ($line -cmatch '^([0-9A-F]{64})  (.+)$') 'Invalid independent input manifest.'
        $hash,$rel=$Matches[1],$Matches[2]
        if ($rel -ceq '_bmad-output/implementation-artifacts/spec-2-8-admin-cancellation.md') { continue }
        Need ((Sha (Join-Path $repo $rel)) -ceq $hash) "Verified input drift: $rel"
        $found++
    }
    Need ($found -eq 14) 'Incomplete independent input manifest.'
}

$baseOut=if ($PrepareOnly) { [IO.Path]::GetTempPath() } else { $root }
$run=Join-Path $baseOut ('story-2-8-formal-'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8))
[void](New-Item -ItemType Directory -Path $run)
Write-Host "Story 2.8 formal evidence: $run"
$inspector=Join-Path $w 'inspect-story-2-5-w01.ps1'
$guardBase=Join-Path $w 'serve-story-2-5-w01-smoke.py'
$template=Join-Path $w 'capture-story-2-5-browser.mjs'
$guard=Join-Path $run 'guard.generated.py'
$generated=Join-Path $run 'capture.generated.mjs'
$planPath=Join-Path $run 'approved-scope.json'
$events=Join-Path $run 'server.jsonl'
$stop=Join-Path $run 'server-stop.flag'
$server=$null; $before=$null; $after=$null; $failure=$null; $sample=$null
$roles=@('anonymous','student','admin')
$names=@('PGPASSFILE','PGCLIENTENCODING','PGCONNECT_TIMEOUT','LAB_BOOKING_DB_MODE','LAB_BOOKING_SECRET_KEY','DJANGO_SETTINGS_MODULE','PYTHONUTF8','PYTHONIOENCODING','PYTHONDONTWRITEBYTECODE')
$old=@{}; foreach($name in $names){$old[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
try {
    Sources28
    # Restrict the reused W01 guard to exactly one detail and one confirmation GET.
    $g=(Read-W01Text $guardBase).Replace([string][char]13,'')
    $originalScope=[regex]::Match($g,'(?ms)^        def scoped\(path, raw\):\n.*?(?=^        def guard\()')
    Need ($originalScope.Success) 'W01 scope anchor changed.'
    $scope=@'
        def scoped(path, raw):
            cancel_paths = {item + "cancel/" for item in detail_paths}
            if path == "/login/" and raw:
                params = parse_qs(raw, keep_blank_values=True, strict_parsing=True, max_num_fields=1)
                return any(params == {"next": [item]} for item in cancel_paths)
            return not raw and path in (account_paths | detail_paths | cancel_paths)

'@
    $g=Swap28 $g $originalScope.Value ($scope+[char]10)
    $g=Swap28 $g 'str(Path(__file__).resolve().parents[3])' 'os.getcwd()'
    $g=Swap28 $g 'method in {"GET", "HEAD", "POST"}' 'method in {"GET", "POST"} and (method != "POST" or not query)'
    $g=Swap28 $g 'r"/reservations/manage/(?:\d+/)?"' 'r"/reservations/manage/(?:\d+/(?:cancel/)?)?"'
    [IO.File]::WriteAllText($guard,$g,$utf8)
    $js=Read-W01Text $template
    $js=Swap28 $js '\/reservations\/manage\/(?:\d+\/)?' '\/reservations\/manage\/\d+\/(?:cancel\/)?'
    $js=Swap28 $js 'x.status === 409)' '(x.status === 409 && status !== 409))'
    $begin=$js.IndexOf('async function drive() {',[StringComparison]::Ordinal)
    $end=[regex]::Match($js,'(?m)^try \{\r?\n    await new Promise\(\(resolve, reject\) => \{')
    Need ($begin -gt 0 -and $end.Success -and $end.Index -gt $begin) 'W01 CDP template anchors changed.'
    $drive=Read-W01Text (Join-Path $PSScriptRoot 'story-2-8-formal-browser-drive.mjs')
    [IO.File]::WriteAllText($generated,$js.Substring(0,$begin)+$drive+[Environment]::NewLine+$js.Substring($end.Index),$utf8)
    Native 'driver-syntax' $node @('--check',$generated) ''
    if ($PrepareOnly) { Write-Output "STORY28_FORMAL_PREPARED_ONLY. Evidence: $run"; return }

    foreach($secret in @($pass,$accounts)){ $f=[IO.File]::Open($secret,'Open','Read','ReadWrite');$f.Dispose() }
    $env:PGPASSFILE=$pass; $env:PGCONNECT_TIMEOUT='5'; $env:PGCLIENTENCODING='UTF8'
    $env:LAB_BOOKING_DB_MODE='runtime'; $env:DJANGO_SETTINGS_MODULE='lab_booking.settings'
    $env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:PYTHONDONTWRITEBYTECODE='1'
    $env:LAB_BOOKING_SECRET_KEY=[Guid]::NewGuid().ToString('N')+[Guid]::NewGuid().ToString('N')
    Native 'python-version' $python @('--version') 'Python 3.13.17'
    $before=Inspect 'before-readonly' ''
    $plan=ReadJson $before
    $deadline=[string]$plan.samples.safe_until
    Need (!$plan.port_in_use_at_inspection -and $plan.acl_result -ceq 'EXACT_COLUMNS_PRESENT' -and
        [DateTimeOffset]::UtcNow.AddMinutes(2) -lt [DateTimeOffset]::Parse($deadline)) 'Formal ACL, port or safe window is unsuitable.'
    $sql=Join-Path $run 'sample-readonly.sql'
    @'
BEGIN ISOLATION LEVEL READ COMMITTED READ ONLY;
SET LOCAL statement_timeout = '5s';
DO $guard$
BEGIN
  IF current_database() <> 'lab_booking' OR current_user <> 'lab_booking_app'
     OR session_user <> current_user OR host(inet_server_addr()) <> '127.0.0.1' OR inet_server_port() <> 5433
     OR current_setting('server_version_num') <> '170012'
     OR current_setting('transaction_read_only') <> 'on'
     OR current_setting('transaction_isolation') <> 'read committed' THEN
    RAISE EXCEPTION 'Unexpected runtime target';
  END IF;
END
$guard$;
WITH eligible AS (
  SELECT r.id, r.status, CASE
      WHEN r.status='approved' AND r.end_at > :'safe_until'::timestamptz THEN 1
      WHEN r.status='pending' AND r.start_at > :'safe_until'::timestamptz THEN 2
      WHEN r.status IN ('rejected','cancelled','expired') THEN 3 END AS priority
  FROM public.reservations_reservation AS r
)
SELECT json_build_object('isolation',current_setting('transaction_isolation'),
  'window_current',clock_timestamp() < :'safe_until'::timestamptz,
  'migrations',(SELECT json_agg(json_build_array(m.app,m.name) ORDER BY m.app COLLATE "C",m.name COLLATE "C") FROM public.django_migrations AS m),
  'sample',(SELECT json_build_object('id',e.id::text,'status',e.status,'positive',e.priority < 3)
            FROM eligible AS e WHERE e.priority IS NOT NULL ORDER BY e.priority,e.id LIMIT 1));
ROLLBACK;
'@ | Set-Content -LiteralPath $sql -Encoding ASCII
    Native 'sample-readonly' $psql @('-X','-w','-q','-A','-t','-h','127.0.0.1','-p','5433','-U','lab_booking_app','-d','lab_booking','-v','ON_ERROR_STOP=1','-v',("safe_until="+$deadline),'-f',$sql) ''
    $source=ReadJson (Join-Path $run 'sample-readonly.stdout.txt')
    $isolated=ReadJson (Join-Path $PSScriptRoot 'story-2-8-run-20261128-234855-694\baseline-before.json')
    Need ($source.window_current -and $source.isolation -ceq 'read committed' -and $source.migrations.Count -eq 19 -and
          (ConvertTo-Json -InputObject $source.migrations -Depth 5 -Compress) -ceq
          (ConvertTo-Json -InputObject $isolated.schema[1] -Depth 5 -Compress)) 'Formal migration ledger or safe window differs.'
    Native 'accounts-readonly' $python @('-B',$guardBase,'--check-accounts',$accounts) 'STORY25_W01_ACCOUNTS_READONLY_OK'
    $sample=$source.sample
    if ($sample) {
        Need ($sample.id -cmatch '^[1-9][0-9]*$' -and $sample.status -cin @('approved','pending','rejected','cancelled','expired')) 'Invalid qualified target.'
        $plan.samples.detail=$sample
        $plan.samples.filter=$null
        $plan.samples.full_unsafe_pending=1
        [IO.File]::WriteAllText($planPath,($plan|ConvertTo-Json -Depth 14)+[Environment]::NewLine,$utf8)
        $server=Start-Log 'server' $python @('-B',$guard,'--inspection',$planPath,'--events',$events,'--stop-file',$stop) -Async
        $httpPid=Wait-W01HttpReady $server $port
        $ready=Read-W01SharedFirstLine $events|ConvertFrom-Json
        Check-GuardReady $server $ready $httpPid $port $planPath $guard $python $deadline (Join-Path $run 'guard-readiness-receipt.json')
        $listener=@(Get-NetTCPConnection -State Listen -LocalAddress '127.0.0.1' -LocalPort $port)
        Need ($listener.Count -eq 1 -and $listener[0].OwningProcess -eq [int]$ready.pid) 'Listening PID differs from the verified worker.'
        [ordered]@{listener_pid=$listener[0].OwningProcess; http_pid=$httpPid; worker_pid=$ready.pid; port=$port} |
          ConvertTo-Json | Set-Content -LiteralPath (Join-Path $run 'listener-pid.json') -Encoding UTF8
        foreach($role in $roles){ Launch-Chrome $role }
    }
} catch { $failure=$_ }
finally {
    try {
        if ($server) {
            [IO.File]::WriteAllText($stop,'stop',$utf8)
            Need ($server.WaitForExit(12000)) 'Dedicated worker did not stop; no unrelated process was touched.'
            $code=$server.ExitCode
            Record 'server' $code
            $server.Dispose()
            Assert-W01Marker @(Read-W01Lines (Join-Path $run 'server.stdout.txt')) $code 'STORY25_W01_SMOKE_READY'
        }
    } catch { if (!$failure){$failure=$_} }
    try { if ($before) {$after=Inspect 'after-readonly' $before} }
    catch { if (!$failure){$failure=$_} }
    finally { foreach($name in $names){[Environment]::SetEnvironmentVariable($name,$old[$name],'Process')} }
}

try {
    if ($failure) { throw $failure }
    Need ($before -and $after) 'Before/after evidence is missing.'
    $count=0
    $coverage='no-sample'
    if ($sample) {
        $detail="/reservations/manage/$($sample.id)/"; $confirm=$detail+'cancel/'
        $rows=@(Read-W01Lines $events|ForEach-Object{$_|ConvertFrom-Json})
        $serverDocs=@($rows|Where-Object event -CEQ 'document')
        $chromeDocs=@(foreach($role in $roles){
            Read-W01Lines (Join-Path $run "$role.chrome.jsonl")|ForEach-Object{$_|ConvertFrom-Json}|Where-Object event -CEQ 'document'
        })
        function Key28($x){"$($x.method)|$($x.path)|$($x.query_sha256)|$($x.status)"}
        Need ($rows[-1].event -ceq 'stop' -and $chromeDocs.Count -gt 0 -and
            (($serverDocs|ForEach-Object {Key28 $_}|Sort-Object)-join '|') -ceq
            (($chromeDocs|ForEach-Object {Key28 $_}|Sort-Object)-join '|')) 'Chrome and guard log differ.'
        foreach($r in $serverDocs){
            Need (!$r.guard_blocked.Count -and $r.path -cin @($detail,$confirm,'/login/','/logout/','/identity/') -and
                !($r.method -ceq 'POST' -and $r.path -cnotin @('/login/','/logout/'))) 'Unexpected route, business POST or guard block.'
        }
        $expected=@{anonymous=302;student=403;admin=$(if ($sample.positive) {200}else{409})}
        foreach($role in $roles){
            Need (@($chromeDocs|Where-Object {$_.role -ceq $role -and $_.method -ceq 'GET' -and $_.path -ceq $confirm -and $_.status -eq $expected[$role]}).Count -eq 1) "Missing confirmation evidence for $role."
        }
        $count=$chromeDocs.Count
        $coverage=if ($sample.positive) {'positive-confirmation-and-abandon'} else {'terminal-only'}
    }
    Sources28
    [ordered]@{status='pass'; finished=(Get-Date -Format o); coverage=$coverage; sample_status=$sample.status;
        document_count=$count; product_posts=0; product_writes=0; migrations_checked=19; grants_performed=0;
        positive_mutations_use_bound_isolated_evidence=$true; runtime_source_match=$true; acl_and_business_snapshot_match=$true} |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $run 'formal-receipt.json') -Encoding UTF8
    'STORY28_FORMAL_SMOKE_OK' | Set-Content -LiteralPath (Join-Path $run 'batch-marker.txt') -Encoding UTF8
    Write-Output "STORY28_FORMAL_SMOKE_OK. Evidence: $run"
} catch {
    $_.Exception.Message | Set-Content -LiteralPath (Join-Path $run 'failure.txt') -Encoding UTF8
    throw
} finally {
    Get-ChildItem -LiteralPath $run -File -Recurse | Sort-Object FullName | ForEach-Object { "$(Sha $_.FullName)  $($_.FullName.Substring($run.Length+1))" } |
        Set-Content -LiteralPath (Join-Path $run 'SHA256SUMS') -Encoding UTF8
}
