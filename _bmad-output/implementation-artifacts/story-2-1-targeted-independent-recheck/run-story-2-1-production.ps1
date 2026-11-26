[CmdletBinding()]
param([string]$Passfile,[string]$AccountsJson,[string]$BackupRoot,
 [string]$PostgresBin='C:\Program Files\PostgreSQL\17\bin',
 [string]$Chrome='C:\Program Files\Google\Chrome\Application\chrome.exe',[string]$ReadOnlyRecovery,
 [string]$ResumeAfterRecovery)
$ErrorActionPreference='Stop'
if($ReadOnlyRecovery -and $ResumeAfterRecovery){throw 'Read-only recovery and deployment continuation are separate modes.'}
$group=$PSScriptRoot
$art=Split-Path -Parent $group
$root=(Resolve-Path -LiteralPath (Join-Path $art '../..')).Path
$python=Join-Path $root '.venv/Scripts/python.exe'
$helper=Join-Path $group 'release-story-2-1.py'
$cert=Join-Path $art 'story-2-1-remediation-run-20261126-205236-052-255e13d05b24/after.sha256'
$oldRun=Join-Path $art 'epic-1-create-navigation-run-20261126-155547-825'
if(-not $Passfile){$Passfile=$env:PGPASSFILE}
if(-not $Passfile){$Passfile=Join-Path $env:LOCALAPPDATA 'LabBooking/PostgreSQL17/pgpass.conf'}
if(-not $AccountsJson){$AccountsJson=Join-Path $env:LOCALAPPDATA 'LabBooking/Protected/accounts.json'}
if(-not $BackupRoot){$BackupRoot=Join-Path $env:LOCALAPPDATA 'LabBooking/Protected'}
$tag=(Get-Date -Format 'yyyyMMdd-HHmmss-fff')+'-'+([guid]::NewGuid().ToString('N')).Substring(0,12)
$run=Join-Path $group ("runtime-run-"+$tag)
$null=New-Item -ItemType Directory -Path $run
Write-Host "Story 2.1 production runtime evidence: $run"
$utf8=[Text.UTF8Encoding]::new($false)
$priorEncoding=[Console]::OutputEncoding
$envs=@('PGPASSFILE','PGCLIENTENCODING','PGCONNECT_TIMEOUT','DJANGO_SETTINGS_MODULE','LAB_BOOKING_DB_MODE',
 'LAB_BOOKING_SECRET_KEY','LAB_BOOKING_R1_CHROME','STORY21_ACCOUNTS','STORY21_PSQL','STORY21_PG_DUMP','STORY21_PG_RESTORE',
 'STORY21_BACKUP_FILE','STORY21_RECOVERY','STORY21_RESUME')
$prior=@{}
foreach($n in $envs){$prior[$n]=[Environment]::GetEnvironmentVariable($n,'Process')}
$lease=$null
$pushed=$false
function Stage([string]$stage,[string]$result){
 [IO.File]::AppendAllText((Join-Path $run 'stages.txt'),"$(Get-Date -Format o) $stage $result"+[Environment]::NewLine,$utf8)
}
function Note([string]$name,$value){
 [IO.File]::WriteAllText((Join-Path $run ($name+'.json')),($value|ConvertTo-Json -Depth 12)+[Environment]::NewLine,$utf8)
}
function Require($ok,[string]$message){if(-not $ok){throw $message}}
function Pin([string]$f,[string]$sha){Require ((Get-FileHash -LiteralPath $f).Hash -ceq $sha) ('Digest mismatch: '+(Split-Path -Leaf $f))}
function Prior-Run([string]$path){
 $src=(Resolve-Path -LiteralPath $path).Path
 Require ((Split-Path -Parent $src) -ieq $group -and (Split-Path -Leaf $src) -cmatch '^runtime-run-\d{8}-\d{6}-\d{3}-[0-9a-f]{12}$' -and $src -ine $run) 'Expected an earlier D-041 evidence directory.'
 return $src
}
function Protected([string]$path,[string]$kind){
 Require ([IO.Path]::IsPathRooted($path) -and (Test-Path -LiteralPath $path -PathType $kind)) 'Required protected local input/container unavailable.'
 $path=(Resolve-Path -LiteralPath $path).Path
 Require (-not $path.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)) 'Protected inputs or backups must not be inside the repository.'
 Require (-not ((Get-Item -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint)) 'Protected path may not be a reparse point.'
 $current=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
 $allowed=@($current,'S-1-5-18','S-1-5-32-544')
 foreach($rule in (Get-Acl -LiteralPath $path).Access){
  if($rule.AccessControlType -eq [Security.AccessControl.AccessControlType]::Allow){
   $sid=$rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value
   Require ($sid -in $allowed) 'Protected input or backup has a broader Windows access rule.'
  }
 }
 return $path
}
function Files {
 [string[]]$expected=Get-Content -LiteralPath $cert -Encoding UTF8
 Require ($expected.Count -eq 75) 'Reviewed manifest must have 75 inputs.'
 $seen=@{}
 foreach($line in $expected){
  Require ($line -cmatch '^([A-F0-9]{64})  ([A-Za-z0-9_./-]+)$') 'Malformed reviewed manifest.'
  $h=$Matches[1]; $rel=$Matches[2]
  Require (-not $seen.ContainsKey($rel) -and -not ($rel -match '(^|/)\.\.(/|$)')) 'Duplicate or unsafe manifest path'
  $seen[$rel]=$true
  Pin (Join-Path $root $rel) $h
 }
 $actual=@('manage.py','requirements.txt')
 foreach($dir in @('accounts','equipment','lab_booking','audit','reservations')){
  $actual+=@(Get-ChildItem -LiteralPath (Join-Path $root $dir) -File -Recurse |
   Where-Object {$_.Extension -in @('.py','.html')} |
   ForEach-Object {$_.FullName.Substring($root.Length+1).Replace('\','/')})
 }
 $approved=@($seen.Keys | Where-Object {$_ -cmatch '^(accounts|equipment|lab_booking|audit|reservations)/|^(manage\.py|requirements\.txt)$'})
 Require (@(Compare-Object ($approved | Sort-Object -CaseSensitive) ($actual | Sort-Object -CaseSensitive) -CaseSensitive).Count -eq 0) 'Runtime source inventory changed.'
}
function Native([string]$stage,[string]$prog,[string[]]$nativeArgs,[string]$marker=''){
 $ErrorActionPreference='Continue'
 [string[]]$log=@(& $prog @nativeArgs 2>&1 | ForEach-Object {$_.ToString()})
 $exit=$LASTEXITCODE
 [IO.File]::WriteAllLines((Join-Path $run ($stage+'.log')),$log,$utf8)
 Stage $stage "exit=$exit"
 Require ($exit -eq 0) ("$stage failed; see its raw log. Do not replay writes.")
 if($marker){Require (@($log | Where-Object {$_ -ceq $marker}).Count -eq 1) ("$stage exact marker absent or repeated. Do not replay writes.")}
}
function Listener {
 $lines=@(netstat -ano -p tcp | Where-Object {$_ -match '^\s*TCP\s+\S+:8001\s+\S+\s+LISTENING\s+\d+\s*$'})
 Require ($LASTEXITCODE -eq 0) 'Cannot inspect port 8001.'
 if(-not $lines){return 0}
 Require ($lines.Count -eq 1 -and $lines[0] -match '^\s*TCP\s+127\.0\.0\.1:8001\s+\S+\s+LISTENING\s+(\d+)\s*$') 'Unknown or wildcard listener on 8001; no process stopped.'
 return [int]$Matches[1]
}
function Proc([int]$processId){
 $p=Get-CimInstance Win32_Process -Filter "ProcessId=$processId"
 Require ($p -and $p.ExecutablePath -and $p.CommandLine -and $p.CreationDate) 'Cannot establish process identity.'
 return $p
}
function Known-Old([int]$listenerPid){
 $oldSummary=Join-Path $oldRun 'run-summary.txt'
 Pin $oldSummary 'F8D1A68573E400E885A2CDEC01F3703E7D228D0446B6F3E071FE7E962BB57D93'
 Pin (Join-Path $oldRun 'runtime-smoke.txt') '0C10908337E2345C2FEEC4F3E004654580656F6FB1D079523DA192D9B3E2E70D'
 $receipt=Get-Content -LiteralPath $oldSummary -Encoding UTF8 -Raw
 Require ($receipt -match '(?m)^service=PASS launcher=(\d+) listener=(\d+) http://127\.0\.0\.1:8001/login/\r?$') 'Old service record unavailable.'
 $launcher=[int]$Matches[1]
 Require ([int]$Matches[2] -eq $listenerPid) 'Port is not the certified Epic 1 listener; no process stopped.'
 $start=[DateTimeOffset]::Parse(([regex]::Match($receipt,'(?m)^started=([^\r\n]+)').Groups[1].Value)).UtcDateTime
 $end=[DateTimeOffset]::Parse(([regex]::Match($receipt,'(?m)^ended=([^\r\n]+)').Groups[1].Value)).UtcDateTime
 $base=@(Get-Content -LiteralPath (Join-Path $root '.venv/pyvenv.cfg') | Where-Object {$_ -match '^executable\s*='} |
         ForEach-Object {($_ -split '=',2)[1].Trim()})
 Require ($base.Count -eq 1 -and [IO.Path]::IsPathRooted($base[0])) 'Cannot verify original interpreter lineage.'
 $argsPattern='(?:^|\s)"?-B"?\s+"?-u"?\s+"?manage\.py"?\s+"?runserver"?\s+"?127\.0\.0\.1:8001"?\s+"?--noreload"?\s*$'
 $owner=Proc $launcher
 $worker=Proc $listenerPid
 Require ($launcher -ne $listenerPid -and [int]$worker.ParentProcessId -eq $launcher) 'Prior service parent lineage differs.'
 foreach($item in @($owner,$worker)){
  $exe=if([int]$item.ProcessId -eq $launcher){$python}else{$base[0]}
  $created=([datetime]$item.CreationDate).ToUniversalTime()
  Require ([IO.Path]::GetFullPath($item.ExecutablePath) -ieq [IO.Path]::GetFullPath($exe) -and
    $item.CommandLine -match $argsPattern -and $created -ge $start -and $created -le $end) 'Previous listener does not match its certified launch.'
 }
 return [ordered]@{launcher=$launcher;listener=$listenerPid;launcher_started=$owner.CreationDate.ToString('o');
   worker_started=$worker.CreationDate.ToString('o');source='certified D-037 Epic 1 run';live_version='previous launch, not Story 2.1'}
}
function Check-OldIdle {
 $busy=@(netstat -ano -p tcp | Where-Object {$_ -match '^\s*TCP\s+127\.0\.0\.1:8001\s+\S+\s+ESTABLISHED\s+\d+\s*$'})
 Require ($LASTEXITCODE -eq 0 -and $busy.Count -eq 0) 'Old project service has an active connection; stop without terminating it.'
}
try{
 [Console]::OutputEncoding=$utf8
 Push-Location -LiteralPath $root; $pushed=$true
 $lease=[IO.File]::Open((Join-Path $group '.d041-release.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
 Require ((git rev-parse HEAD) -ceq 'e196aba098771a31eb203be4270b460d5e0aab42' -and $LASTEXITCODE -eq 0) 'Unexpected release baseline.'
 Pin $cert '4A6EF690D72AEACF4D7844455081C68D2C7B3399395D7F9D4B7A2C9185DD5F4A'
 Files
 Pin $helper '4AACBDF0AD62531F8852E00EA9703FFC3D6038E8188903C463810078576EDA31'
 $fingerprints=Get-FileHash -LiteralPath $PSCommandPath,$helper,$cert
 Note 'reviewed-inputs' ($fingerprints|Select-Object Path,Hash)
 Native 'python-version' $python @('--version') 'Python 3.13.17'
 $conflict=@('PGHOST','PGHOSTADDR','PGPORT','PGDATABASE','PGUSER','PGPASSWORD','PGSERVICE','PGSERVICEFILE','PGOPTIONS') |
     Where-Object {Test-Path "Env:$_"}
 Require (-not $conflict) ('Remove conflicting libpq environment variables: '+($conflict -join ', '))
 $env:PGPASSFILE=Protected $Passfile 'Leaf'
 $env:PGCLIENTENCODING='UTF8'
 $env:PGCONNECT_TIMEOUT='5'
 $env:DJANGO_SETTINGS_MODULE='lab_booking.settings'
 $env:LAB_BOOKING_DB_MODE='migration'
 $env:LAB_BOOKING_SECRET_KEY=[Guid]::NewGuid().ToString('N')+[Guid]::NewGuid().ToString('N')
 $env:STORY21_PSQL=Join-Path $PostgresBin 'psql.exe'
 $env:STORY21_PG_DUMP=Join-Path $PostgresBin 'pg_dump.exe'
 $env:STORY21_PG_RESTORE=Join-Path $PostgresBin 'pg_restore.exe'
 if($ReadOnlyRecovery){
  $src=Prior-Run $ReadOnlyRecovery
  Require (@(Get-ChildItem -LiteralPath $src -Filter '*-intent.json').Count -gt 0) 'No prior write intent recorded; follow its exact failure log.'
  $env:STORY21_RECOVERY=$src
  Note 'recovery-source' @{source=$src;mode='read only; not a retry'}
  Native 'recovery' $python @('-E','-X','utf8','-B',$helper,'recover',$run) 'STORY21_D041_READ_ONLY_RECOVERY_OK'
  Write-Output "STORY21_D041_READ_ONLY_RECOVERY_OK $run"
  exit 0
 }
 $priorWrites=@(Get-ChildItem -LiteralPath $group -Directory -Filter 'runtime-run-*' | Where-Object {$_.FullName -ine $run} |
   Where-Object {@(Get-ChildItem -LiteralPath $_.FullName -File -Filter '*-intent.json').Count -gt 0})
 $dbPhase='prepare'
 if($ResumeAfterRecovery){
  $receipt=Prior-Run $ResumeAfterRecovery
  $exitLines=@(Get-Content -LiteralPath (Join-Path $receipt 'stages.txt') | Where-Object {$_ -cmatch ' recovery exit=0$'})
  $marks=@(Get-Content -LiteralPath (Join-Path $receipt 'recovery.log') -Encoding UTF8 | Where-Object {$_ -ceq 'STORY21_D041_READ_ONLY_RECOVERY_OK'})
  Require ($exitLines.Count -eq 1 -and $marks.Count -eq 1 -and -not (Test-Path -LiteralPath (Join-Path $receipt 'failure.txt'))) 'A successful read-only recovery receipt is required.'
  $review=Get-Content -LiteralPath (Join-Path $receipt 'recovery-summary.json') -Raw -Encoding UTF8 | ConvertFrom-Json
  Require ($review.both_migrated -eq $true -and $review.acl -cin @('pristine','ready') -and @($review.slot_beijing).Count -eq 2 -and -not $review.demo_blocker) 'Recovery did not certify both migrations, expected ACL and a safe demo slot; no write.'
  $from=Get-Content -LiteralPath (Join-Path $receipt 'recovery-source.json') -Raw -Encoding UTF8 | ConvertFrom-Json
  $src=Prior-Run $from.source
  Require ((Split-Path -Leaf $src) -ceq 'runtime-run-20261126-213638-448-312206ec440e') 'This continuation only covers the recorded D-041 ACL incident.'
  $migration=Get-Content -LiteralPath (Join-Path $src 'migration-result.jsonl') -Raw -Encoding UTF8 | ConvertFrom-Json
  Require ($migration.exit -eq 0 -and $migration.outcome -ceq 'confirmed by Django and readback') 'Original migration receipt not confirmed.'
  foreach($priorRun in $priorWrites){
   Require (-not (Test-Path -LiteralPath (Join-Path $priorRun.FullName 'reservation-intent.json'))) 'Prior reservation intent exists. No browser POST may be replayed.'
   if($review.acl -ceq 'pristine'){
    Require (-not (Test-Path -LiteralPath (Join-Path $priorRun.FullName 'grant-intent.json'))) 'Prior GRANT intent exists. Do not replay it.'
   }
  }
  $env:STORY21_RECOVERY=$src
  $env:STORY21_RESUME=$receipt
  $dbPhase='resume'
  Note 'resume-source' @{original=$src;recovery=$receipt;acl=$review.acl;mode='no migration; no replay'}
 } else {
  Require (-not $priorWrites) 'Prior write intent exists. Do not rerun writes. Use -ReadOnlyRecovery with the prior evidence directory.'
 }
 $env:STORY21_ACCOUNTS=Protected $AccountsJson 'Leaf'
 $secure=Protected $BackupRoot 'Container'
 if($dbPhase -ceq 'resume'){
  $backupDir=Protected (Join-Path $secure ((Split-Path -Leaf $src) -replace '^runtime-run-','story21-d041-')) 'Container'
  $env:STORY21_BACKUP_FILE=Protected (Join-Path $backupDir 'lab_booking-before-story-2-1.dump') 'Leaf'
 }else{
  $backupDir=Join-Path $secure ('story21-d041-'+$tag)
  $null=New-Item -ItemType Directory -Path $backupDir
  $backupDir=Protected $backupDir 'Container'
  $env:STORY21_BACKUP_FILE=Join-Path $backupDir 'lab_booking-before-story-2-1.dump'
 }
 $env:LAB_BOOKING_R1_CHROME=(Resolve-Path -LiteralPath $Chrome).Path
 $tools=@{psql=$env:STORY21_PSQL;pg_dump=$env:STORY21_PG_DUMP;pg_restore=$env:STORY21_PG_RESTORE}
 foreach($tool in $tools.GetEnumerator()){
  Require ([IO.Path]::IsPathRooted($tool.Value) -and (Test-Path -LiteralPath $tool.Value -PathType Leaf)) 'Existing PostgreSQL 17 tools required.'
  Native ($tool.Key+'-version') $tool.Value @('--version') ($tool.Key+' (PostgreSQL) 17.12')
 }
 $portOwner=Listener
 $old=$null
 if($portOwner){$old=Known-Old $portOwner; Note 'service-before' $old; Check-OldIdle}else{Note 'service-before' @{listener=0}}
 Native 'production-database' $python @('-E','-X','utf8','-B',$helper,$dbPhase,$run) 'STORY21_D041_DATABASE_READY'
 Require ((Protected $env:STORY21_BACKUP_FILE 'Leaf') -ieq $env:STORY21_BACKUP_FILE) 'Backup protection no longer matches.'
 Files
 Require ((Listener) -eq $portOwner) 'Port ownership changed. No unknown process stopped.'
 if($old){
  $same=Known-Old $portOwner
  Require ($same.worker_started -ceq $old.worker_started -and $same.launcher_started -ceq $old.launcher_started) 'Listener identity changed. No unknown process stopped.'
  Check-OldIdle
  Stage 'old-project-service' 'stop-confirmed-D037-lineage'
  Stop-Process -Id $old.launcher -ErrorAction Stop
  if((Listener) -eq $old.listener){
   $child=Proc $old.listener
   Require ($child.CreationDate.ToString('o') -ceq $old.worker_started -and [int]$child.ParentProcessId -eq $old.launcher) 'Prior worker identity changed; no unknown process stopped.'
   Stop-Process -Id $old.listener -ErrorAction Stop
  }
  for($i=0;$i -lt 25 -and (Listener) -eq $old.listener;$i++){Start-Sleep -Milliseconds 120}
 }
 Require ((Listener) -eq 0) '8001 not free; no unapproved port used.'
 $env:LAB_BOOKING_DB_MODE='runtime'
 $arguments=@('-E','-X','utf8','-B','-u','manage.py','runserver','127.0.0.1:8001','--noreload')
 $cfg=@{FilePath=$python;ArgumentList=$arguments;WorkingDirectory=$root;WindowStyle='Hidden';PassThru=$true
    RedirectStandardOutput=(Join-Path $run 'server.stdout.txt');RedirectStandardError=(Join-Path $run 'server.stderr.txt')}
 $service=Start-Process @cfg
 Stage 'new-project-service' ("launcher_pid="+$service.Id)
 $newListener=0
 for($i=0;$i -lt 70;$i++){
  Start-Sleep -Milliseconds 200
  $newListener=Listener
  if($newListener){break}
  $service.Refresh()
  Require (-not $service.HasExited) 'New service process exited; inspect raw server logs.'
 }
 Require ($newListener -gt 0) 'New service did not listen on 127.0.0.1:8001.'
 $worker=Proc $newListener
 Require ($newListener -eq $service.Id -or [int]$worker.ParentProcessId -eq $service.Id) 'Unexpected new listener lineage. No process stopped.'
 Require ($worker.CommandLine -match 'manage\.py"?\s+"?runserver"?\s+"?127\.0\.0\.1:8001"?\s+"?--noreload"?\s*$') 'Unexpected actual runtime command.'
 $starts=@(Get-Content -LiteralPath (Join-Path $run 'server.stdout.txt') -Encoding UTF8)
 Require (($starts -join [char]10) -match 'Starting development server at http://127\.0\.0\.1:8001/' -and
    ($starts -join [char]10) -match 'lab_booking\.settings') 'New service startup marker absent.'
 Note 'service-after' @{launcher=$service.Id;listener=$newListener;mode='runtime';source=$root;manifest=(Get-FileHash $cert).Hash;
     url='http://127.0.0.1:8001/login/'}
 Native 'production-chrome' $python @('-E','-X','utf8','-B',$helper,'browser',$run) 'STORY21_D041_BROWSER_AND_DB_OK'
 Files
 Pin $helper '4AACBDF0AD62531F8852E00EA9703FFC3D6038E8188903C463810078576EDA31'
 Require ((Listener) -eq $newListener) 'Listener changed after browser verification.'
 $result=Get-Content -LiteralPath (Join-Path $run 'runtime-result.json') -Raw -Encoding UTF8 | ConvertFrom-Json
 Require ($result.status -ceq 'pending' -and $result.history_delta -eq 0 -and $result.reservation_id -gt 0) 'Missing valid final result.'
 Stage 'd041-production-runtime-complete' 'exit=0'
 Write-Output "STORY21_D041_PRODUCTION_RUNTIME_OK $run"
 Write-Output ("Login: "+$result.login)
 Write-Output ("Application: "+$result.reservation_entry)
 Write-Output ("Own result: "+$result.own_result)
}catch{
 Stage 'run-stopped' 'exit=1; do not replay any write'
 [IO.File]::WriteAllText((Join-Path $run 'failure.txt'),$_.Exception.Message+[Environment]::NewLine,$utf8)
 throw
}finally{
 if($lease){$lease.Dispose()}
 if($pushed){Pop-Location}
 [Console]::OutputEncoding=$priorEncoding
 foreach($n in $envs){[Environment]::SetEnvironmentVariable($n,$prior[$n],'Process')}
}

