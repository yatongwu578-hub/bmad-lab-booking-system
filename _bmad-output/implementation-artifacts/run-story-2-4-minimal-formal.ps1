[CmdletBinding()]
param(
    [string]$Passfile,
    [string]$AccountsJson = (Join-Path $env:LOCALAPPDATA 'LabBooking/Protected/accounts.json'),
    [string]$Psql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe',
    [string]$Chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe',
    [string]$OutputRoot = 'F:\softwork\outputs',
    [ValidateRange(1024,65535)][int]$BrowserPort = 8006
)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$w01=Join-Path $PSScriptRoot 'story-2-5-review-support'
. (Join-Path $w01 'w01-log-contract.ps1')
Set-W01WireEncoding
$utf8=[Text.UTF8Encoding]::new($false)
$python=Join-Path $repo '.venv/Scripts/python.exe'
$node=(Get-Command node.exe -CommandType Application).Source
$ps=Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe'
$serverScript=Join-Path $PSScriptRoot 'serve-story-2-4-formal-smoke.py'
$template=Join-Path $w01 'capture-story-2-5-browser.mjs'
$drive=Join-Path $PSScriptRoot 'story-2-4-formal-browser-drive.mjs'
$inspector=Join-Path $w01 'inspect-story-2-5-w01.ps1'
$baseline=Join-Path $PSScriptRoot 'story-2-4-independent-run-20261128-094455'
$run=(New-Item -ItemType Directory -Path (Join-Path (Resolve-Path -LiteralPath $OutputRoot).Path ('story-2-4-formal-'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff')+'-'+[guid]::NewGuid().ToString('N')))).FullName
Write-Host "Story 2.4 formal evidence: $run"
$browser=Join-Path $run 'capture-story-2-4.generated.mjs'
$planPath=Join-Path $run 'sample-plan.json'
$events=Join-Path $run 'server.jsonl'
$stop=Join-Path $run 'server-stop.flag'
$server=$null; $before=$null; $after=$null; $failure=$null
$names='PGPASSFILE','PGCLIENTENCODING','PGCONNECT_TIMEOUT','LAB_BOOKING_DB_MODE','LAB_BOOKING_SECRET_KEY','DJANGO_SETTINGS_MODULE','PYTHONUTF8','PYTHONIOENCODING','PYTHONDONTWRITEBYTECODE'
$prior=@{}; foreach($n in $names){$prior[$n]=[Environment]::GetEnvironmentVariable($n,'Process')}
function Need24($ok,$message){if(!$ok){throw $message}}
function Hash24($p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash}
function Read24($p){Read-W01Text $p | ConvertFrom-Json}
function Start24($name,$file,$argv,[switch]$Async){
    Start-W01Redirected $file $repo $argv (Join-Path $run "$name.stdout.txt") (Join-Path $run "$name.stderr.txt") -Async:$Async
}
function Receipt24($name,$code){
    Write-W01NativeReceipt (Join-Path $run "$name.native.json") (Join-Path $run "$name.stdout.txt") (Join-Path $run "$name.stderr.txt") $code 'UTF-8 protocol' 'raw diagnostic bytes'
    "$(Get-Date -Format o) $name exit=$code" | Add-Content -LiteralPath (Join-Path $run 'stages.txt') -Encoding UTF8
}
function Native24($name,$file,$argv,$marker){
    $p=Start24 $name $file $argv
    try{$code=$p.ExitCode}finally{$p.Dispose()}
    Receipt24 $name $code
    Need24 ($code -eq 0) "Stage $name failed; see original diagnostics."
    $lines=@(Read-W01Lines (Join-Path $run "$name.stdout.txt"))
    if($marker){Assert-W01Marker $lines $code $marker}
    $lines
}
function Inspect24($name,$compare){
    $argv=@('-NoProfile','-File',$inspector,'-CaptureSnapshot','-Passfile',$Passfile,'-Psql',$Psql,'-OutputRoot',$run,'-BrowserPort',"$BrowserPort")
    if($compare){$argv+=@('-BeforeEvidence',$compare)}
    $hits=@(Native24 $name $ps $argv 'STORY25_W01_INSPECT_OK' | Where-Object {$_ -cmatch '^W01 evidence: '})
    Need24 ($hits.Count -eq 1) 'Inspection receipt path is not unique.'
    $folder=(Resolve-Path -LiteralPath $hits[0].Substring(14)).Path
    Need24 ((Split-Path -Parent $folder) -ceq $run) 'Inspection receipt escaped the batch.'
    $file=Join-Path $folder 'w01-inspect.json'; $inspect=Read24 $file
    Need24 ((Hash24 (Join-Path $folder 'acl-and-samples.stdout.txt')) -ceq $inspect.raw_stdout_sha256) 'Inspection is not bound to the raw SQL receipt.'
    $file
}
function Chrome24($role,[switch]$Probe){
    $label=if($Probe){'renderer'}else{$role}
    $profile=(New-Item -ItemType Directory -Path (Join-Path ([IO.Path]::GetTempPath()) ('story24-chrome-'+[guid]::NewGuid().ToString('N')))).FullName
    $p=$null
    try{
        $p=Start24 "chrome-$label" $Chrome @('--headless=new','--no-first-run','--no-default-browser-check','--disable-background-networking','--disable-extensions','--no-proxy-server',('--user-data-dir='+$profile),'--remote-debugging-address=127.0.0.1','--remote-debugging-port=0','about:blank') -Async
        $debug=Join-Path $profile 'DevToolsActivePort'; $deadline=[DateTime]::UtcNow.AddSeconds(15)
        while(!(Test-Path -LiteralPath $debug -PathType Leaf)){
            $p.Refresh()
            Need24 (!$p.HasExited -and [DateTime]::UtcNow -lt $deadline) 'Dedicated Chrome renderer did not start.'
            Start-Sleep -Milliseconds 100
        }
        $cdp=Read-W01SharedFirstLine $debug -Ascii
        Need24 ($cdp -cmatch '^[0-9]{4,5}$' -and [int]$cdp -le 65535 -and [int]$cdp -ne $BrowserPort) 'Invalid Chrome debug port.'
        $argv=@($browser,'--origin',"http://127.0.0.1:$BrowserPort",'--debug',$cdp,'--role',$role,'--out',(Join-Path $run "$label.chrome.jsonl"))
        if($Probe){$argv+='--probe';$marker='STORY25_W01_CHROME_PROBE_OK'}
        else{$argv+=@('--inspection',$planPath,'--accounts',$AccountsJson);$marker='STORY25_CHROME_CAPTURE_OK'}
        $null=Native24 "browser-$label" $node $argv $marker
    }finally{
        if($p){
            if(!$p.HasExited){Stop-Process -Id $p.Id -ErrorAction SilentlyContinue;[void]$p.WaitForExit(4000)}
            $p.Dispose()
        }
        $item=Get-Item -LiteralPath $profile -ErrorAction SilentlyContinue
        if($item -and $item.Name -cmatch '^story24-chrome-[0-9a-f]{32}$' -and $item.Parent.FullName.TrimEnd('\') -ieq ([IO.Path]::GetTempPath()).TrimEnd('\') -and -not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)){
            Remove-Item -LiteralPath $item.FullName -Recurse -Force
        }
    }
}
try{
    if(!$Passfile){$Passfile=$env:PGPASSFILE}
    if(!$Passfile){$Passfile=Join-Path $env:LOCALAPPDATA 'LabBooking/PostgreSQL17/pgpass.conf'}
    foreach($p in @($Passfile,$AccountsJson)){
        Need24 ([IO.Path]::IsPathRooted($p)) 'Protected input requires an absolute path.'
        $resolved=(Resolve-Path -LiteralPath $p).Path
        Need24 (!$resolved.StartsWith($repo+'\',[StringComparison]::OrdinalIgnoreCase) -and !$resolved.StartsWith((Resolve-Path -LiteralPath $OutputRoot).Path+'\',[StringComparison]::OrdinalIgnoreCase)) 'Keep protected inputs outside the repo and archive root.'
        $f=[IO.File]::Open($resolved,'Open','Read','ReadWrite');$f.Dispose()
    }
    Need24 ($BrowserPort -notin 5433,8000,8001) 'Use a dedicated smoke port.'
    $listener=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,$BrowserPort)
    $listener.ExclusiveAddressUse=$true
    try{$listener.Start()}finally{$listener.Stop()}
    Need24 ((Hash24 (Join-Path $baseline 'before.sha256')) -ceq (Hash24 (Join-Path $baseline 'after.sha256'))) 'Independent manifests disagree.'
    $files=@(foreach($line in (Read-W01Lines (Join-Path $baseline 'before.sha256'))){
        $relative=$line.Substring(66)
        if($relative -notmatch '^_bmad-output/'){
            $src=Join-Path $repo $relative
            Need24 ((Hash24 $src) -ceq $line.Substring(0,64)) "Independently tested source drift: $relative."
            $src
        }
    })
    $files+=@($serverScript,$template,$drive,$inspector,(Join-Path $w01 'w01-log-contract.ps1'),(Join-Path $w01 'story-2-5-w01-inspect.sql'),(Join-Path $w01 'story-2-5-w01-snapshot.sql'),$PSCommandPath)
    $hashes=@($files | ForEach-Object {"$(Hash24 $_)  $($_.Substring($repo.Length+1))"})
    [IO.File]::WriteAllLines((Join-Path $run 'sources-before.sha256'),[string[]]$hashes,$utf8)
    $env:PGPASSFILE=$Passfile;$env:PGCONNECT_TIMEOUT='5';$env:PGCLIENTENCODING='UTF8'
    $env:LAB_BOOKING_DB_MODE='runtime';$env:DJANGO_SETTINGS_MODULE='lab_booking.settings'
    $env:PYTHONUTF8='1';$env:PYTHONIOENCODING='utf-8';$env:PYTHONDONTWRITEBYTECODE='1'
    $env:LAB_BOOKING_SECRET_KEY=[guid]::NewGuid().ToString('N')+[guid]::NewGuid().ToString('N')
    $null=Native24 'python' $python @('--version') 'Python 3.13.17'
    $null=Native24 'django' $python @('-B','-m','django','--version') '5.2.19'
    $original=Read-W01Text $template
    $start=$original.IndexOf('async function drive() {',[StringComparison]::Ordinal)
    $stopMatch=[regex]::Match($original,'(?m)^try \{\r?\n    await new Promise\(\(resolve, reject\) => \{')
    $oldScope='\/reservations\/manage\/(?:\d+\/)?'
    Need24 ($start -gt 0 -and $stopMatch.Success -and $stopMatch.Index -gt $start -and [regex]::Matches($original,[regex]::Escape($oldScope)).Count -eq 1) 'Unexpected W01 CDP template anchors.'
    $generated=$original.Substring(0,$start)+(Read-W01Text $drive)+[Environment]::NewLine+$original.Substring($stopMatch.Index)
    $generated=$generated.Replace($oldScope,'\/reservations\/(?:\d+\/(?:result|cancel)\/)?').Replace('readFileSync, writeSync','readFileSync, writeFileSync, writeSync')
    [IO.File]::WriteAllText($browser,$generated,$utf8)
    $null=Native24 'driver-syntax' $node @('--check',$browser) ''
    Chrome24 'anonymous' -Probe
    $before=Inspect24 'before-readonly' ''
    $null=Native24 'sample-and-migrations-readonly' $python @('-B',$serverScript,'--inspection',$before,'--plan',$planPath,'--accounts',$AccountsJson,'--baseline',(Join-Path $baseline 'baseline-before.json')) 'STORY24_FORMAL_PLAN_OK'
    $plan=Read24 $planPath
    Need24 ([DateTimeOffset]::UtcNow.AddSeconds(60) -lt [DateTimeOffset]::Parse($plan.deadline)) 'Inspected safe window is too short.'
    $server=Start24 'server' $python @('-B',$serverScript,'--inspection',$before,'--plan',$planPath,'--events',$events,'--stop',$stop) -Async
    $httpPid=Wait-W01HttpReady $server $BrowserPort
    $startReceipt=Read-W01SharedFirstLine $events | ConvertFrom-Json
    Need24 ($startReceipt.event -ceq 'ready' -and $startReceipt.port -eq $BrowserPort -and "$($startReceipt.pid)" -ceq $httpPid -and $startReceipt.plan_sha256 -ieq (Hash24 $planPath)) 'Port, PID or inspected plan does not match.'
    $roles=@('anonymous',$plan.deny_role,'admin');if($plan.owner_role){$roles+=$plan.owner_role}
    foreach($role in $roles){Chrome24 $role}
}catch{$failure=$_}
finally{
    try{
        if($server){
            [IO.File]::WriteAllText($stop,'stop',$utf8)
            if(!$server.WaitForExit(8000)){Stop-Process -Id $server.Id;[void]$server.WaitForExit(4000)}
            $code=$server.ExitCode;Receipt24 'server' $code;$server.Dispose()
            Assert-W01Marker @(Read-W01Lines (Join-Path $run 'server.stdout.txt')) $code 'STORY24_FORMAL_SERVER_READY'
        }
    }catch{if(!$failure){$failure=$_}}
    try{if($before -and $server){$after=Inspect24 'after-readonly' $before}}
    catch{if(!$failure){$failure=$_}}
    finally{foreach($n in $names){[Environment]::SetEnvironmentVariable($n,$prior[$n],'Process')}}
}
if($failure){
    $failure.Exception.Message | Set-Content -LiteralPath (Join-Path $run 'failure.txt') -Encoding UTF8
    throw $failure
}
Need24 ($before -and $after) 'Missing independent before/after verification.'
$final=@($files | ForEach-Object {"$(Hash24 $_)  $($_.Substring($repo.Length+1))"})
Need24 (($hashes -join '|') -ceq ($final -join '|')) 'Inputs changed during smoke.'
[IO.File]::WriteAllLines((Join-Path $run 'sources-after.sha256'),[string[]]$final,$utf8)
$rows=@(Read-W01Lines $events | ForEach-Object {ConvertFrom-Json $_})
$serverDocs=@($rows | Where-Object {$_.event -ceq 'document'})
$browserDocs=@(foreach($role in $roles){
    Read-W01Lines (Join-Path $run "$role.chrome.jsonl") | ForEach-Object {ConvertFrom-Json $_} | Where-Object {$_.event -ceq 'document'}
})
function Key24($r){"$($r.method)|$($r.path)|$($r.query_sha256)|$($r.status)"}
function Assert24Documents($serverDocs,$browserDocs,$plan,$stopped){
    Need24 $stopped 'The guarded server stop receipt is missing.'
    Need24 ($browserDocs.Count -gt 0 -and (($browserDocs | ForEach-Object {Key24 $_} | Sort-Object) -join '|') -ceq (($serverDocs | ForEach-Object {Key24 $_} | Sort-Object) -join '|')) 'Chrome and actual guarded server requests disagree.'
    foreach($row in $serverDocs){
        Need24 (!$row.guard_blocked.Count -and !($row.method -eq 'POST' -and $row.path -notin '/login/','/logout/')) 'Unexpected request or guard rejection.'
        if($row.path -notmatch '/cancel/$' -or $row.status -eq 200){continue}
        $paths=@("/reservations/$($plan.absent)/cancel/")
        if($plan.existing_target){$paths+="/reservations/$($plan.existing_target)/cancel/"}
        $scopedMiss=$row.method -ceq 'GET' -and $row.status -eq 404 -and $row.path -cin $paths -and !$row.technical.Count -and
            $row.business.Count -eq 1 -and $row.business[0] -ceq 'business-read' -and
            @($browserDocs | Where-Object {$_.role -ceq $plan.deny_role -and (Key24 $_) -ceq (Key24 $row)}).Count -eq 1
        Need24 ($scopedMiss -or !$row.business.Count) 'Unexpected SQL category for a rejected cancellation request.'
    }
}
Assert24Documents $serverDocs $browserDocs $plan ($rows[-1].event -ceq 'stop')
Need24 (@($browserDocs | Where-Object {$_.served_from_cache -or ($_.status -ne 302 -and -not $_.body_sha256)}).Count -eq 0) 'Incomplete or cached browser evidence.'
[ordered]@{marker='STORY24_FORMAL_SMOKE_OK';before=$before;after=$after;actual_documents=$browserDocs.Count;browser_roles=$roles;
    owner_role=$plan.owner_role;list_roundtrip=[bool]$plan.list_safe;applicant_denial=$(if($plan.existing_target){'foreign-and-missing'}else{'missing-only'});
    product_post_count=0;migration_or_grant_count=0;capture_driver_sha256=(Hash24 $browser);sources_match=$true;acl_and_business_unchanged=$true} |
    ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $run 'verified-smoke.json') -Encoding UTF8
'STORY24_FORMAL_SMOKE_OK' | Set-Content -LiteralPath (Join-Path $run 'batch-marker.txt') -Encoding UTF8
'STORY24_FORMAL_SMOKE_OK'
