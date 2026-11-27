[CmdletBinding()]
param(
    [ValidateSet('Acl','Recover','Inspect','Serve','Chrome','Finish')][string]$Phase = 'Acl',
    [string]$RunDirectory,
    [string]$SmokeName,
    [string]$AccountsManifest,
    [switch]$AuthorizedDemo,
    [string]$Passfile,
    [string]$Psql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe',
    [string]$Chrome = "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    [string]$OutputRoot = 'F:\softwork\outputs'
)
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$python=Join-Path $root '.venv/Scripts/python.exe'
$reader=Join-Path $PSScriptRoot 'read-story-2-3-formal.py'
$narrow=Join-Path $PSScriptRoot 'read-story-2-3-audit-acl.ps1'
$grant=Join-Path $PSScriptRoot 'story-2-3-history-select-reviewed.sql'
$approved=Join-Path $PSScriptRoot 'story-2-3-independent-run-20261127-114813-950-de7b7f2c/before.sha256'
$origin='http://127.0.0.1:8003'
$nl=[Environment]::NewLine
$utf8=[Text.UTF8Encoding]::new($false)
$run=$null

function Must([bool]$ok,[string]$message) { if (!$ok) { throw $message } }
function Fingerprint([string]$path,[string]$expected) {
    Must ((Get-FileHash -LiteralPath $path).Hash -ceq $expected) ('Fingerprint differs: ' + (Split-Path -Leaf $path))
}
function Stage([string]$name,[string]$result) {
    Add-Content -LiteralPath (Join-Path $run 'stages.txt') -Encoding UTF8 -Value ('{0:o} {1} {2}' -f (Get-Date),$name,$result)
}
function NewText([string]$name,[string]$content) {
    $p=Join-Path $run $name
    Must (!(Test-Path -LiteralPath $p)) ('Refusing to overwrite ' + $name)
    [IO.File]::WriteAllText($p,$content+$nl,$utf8)
}
function Native([string]$stage,[string]$exe,[string[]]$argList) {
    $o=Join-Path $run ($stage+'.stdout.txt')
    $e=Join-Path $run ($stage+'.stderr.txt')
    Must (!(Test-Path -LiteralPath $o) -and !(Test-Path -LiteralPath $e)) ('Evidence already exists for ' + $stage)
    $quoted=($argList | ForEach-Object { Must ($_ -notmatch '["\r\n]') 'Unexpected argument'; '"' + $_ + '"' }) -join ' '
    $start=@{FilePath=$exe;ArgumentList=$quoted;WorkingDirectory=$root;WindowStyle='Hidden';Wait=$true;PassThru=$true;
             RedirectStandardOutput=$o;RedirectStandardError=$e}
    $proc=Start-Process @start
    Stage $stage ('exit='+$proc.ExitCode)
    if ($proc.ExitCode -ne 0) {
        if ($stage -eq 'grant') { throw 'Grant did not return exit 0. Preserve the logs and use only the read-back recovery.' }
        throw ($stage+' exited '+$proc.ExitCode+'. Read '+$stage+'.stderr.txt in this attempt. No automatic retry.')
    }
    Get-Content -LiteralPath $o -Encoding UTF8
}
function Catalog([string]$stage,[string]$expected) {
    $lines=@(Native ($stage+'-catalog') $python @('-B',$reader,$stage,$run))
    $marks=@($lines | Where-Object {$_ -cin @('STORY23_READ_EXACT_OK','STORY23_READ_NEEDS_FOUR_OK')})
    Must ($marks.Count -eq 1 -and (!$expected -or $marks[0] -ceq $expected)) 'Catalog marker absent, duplicate or unexpected'
    $marks[0]
}
function AppAcl([string]$stage) {
    $o=Join-Path $run ($stage+'-app.stdout.txt')
    $e=Join-Path $run ($stage+'-app.stderr.txt')
    Must (!(Test-Path -LiteralPath $o) -and !(Test-Path -LiteralPath $e)) 'App evidence already exists'
    try {
        $lines=@(& $narrow -Psql $Psql -Passfile $Passfile 2> $e)
        $lines | Set-Content -LiteralPath $o -Encoding UTF8
        $states=@($lines | Where-Object {$_ -cin @('ACL_RESULT=NEEDS_FOUR_COLUMN_GRANT','ACL_RESULT=EXACT_COLUMNS_PRESENT')})
        Must ($states.Count -eq 1 -and @($lines|Where-Object {$_ -ceq 'STORY23_ACL_READONLY_OK'}).Count -eq 1) 'App ACL marker absent or duplicated'
        Stage ($stage+'-app') 'exit=0'
        $states[0]
    } catch {
        $_ | Out-String | Add-Content -LiteralPath $e -Encoding UTF8
        Stage ($stage+'-app') 'exit=1'
        throw
    }
}
function Listeners {
    @(netstat -ano -p tcp | Where-Object {$_ -match '^\s*TCP\s+\S+:8003\s+\S+\s+LISTENING\s+\d+\s*$'})
}
function Sources {
    Fingerprint $approved 'F12EB1C9C5947E37BE7AC3E4E760F846A480AD4557FD7B92DE99C6193B892E06'
    $actual=@('manage.py','requirements.txt')
    foreach ($sub in @('accounts','audit','equipment','lab_booking','reservations')) {
        $actual+=@(Get-ChildItem -LiteralPath (Join-Path $root $sub) -File -Recurse |
            Where-Object {$_.Extension -in '.py','.html'} |
            ForEach-Object {$_.FullName.Substring($root.Length+1).Replace('\','/')})
    }
    $rows=@(Get-Content -LiteralPath $approved -Encoding UTF8 | Where-Object {
        $_ -cmatch '^[0-9A-F]{64}  (manage\.py|requirements\.txt|(accounts|audit|equipment|lab_booking|reservations)/[^:]+(?:\.html|\.py))$'
    })
    $paths=@($rows | ForEach-Object {$_.Substring(66)})
    Must ($paths.Count -gt 0 -and @($paths|Sort-Object -Unique).Count -eq $paths.Count -and
          @(Compare-Object $actual $paths -CaseSensitive).Count -eq 0) 'Runtime source inventory differs'
    foreach ($line in $rows) {
        $path=$line.Substring(66)
        Must ($path -notmatch '[:\\]' -and $path -notmatch '(?:^|/)\.\.(?:/|$)') 'Unsafe source path'
        Fingerprint (Join-Path $root $path) $line.Substring(0,64)
        $line
    }
}
function CheckSources([string]$scope) {
    $actual=@(Sources)
    $saved=@(Get-Content -LiteralPath (Join-Path $scope 'runtime-source.sha256') -Encoding UTF8)
    Must (($actual -join '|') -ceq ($saved -join '|')) 'Runtime source drift'
}
function ReadSample([string]$scope) {
    $p=Join-Path $scope 'sample-before.json'
    $hash=(Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $scope 'sample-before.sha256')).Trim()
    Fingerprint $p $hash
    (Get-Content -Raw -Encoding UTF8 -LiteralPath $p|ConvertFrom-Json).sample
}
function EvidenceDirectory([string]$path,[string]$pattern) {
    $item=Get-Item -LiteralPath $path
    Must ($item.PSIsContainer -and $item.Name -cmatch $pattern -and
        !(($item.Attributes -band [IO.FileAttributes]::ReparsePoint))) 'Unexpected receipt directory'
    $item.FullName
}
function NewAttempt([string]$parent,[string]$kind,[string]$name='') {
    if (!$name) { $name=$kind+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8) }
    Must ($name -cmatch ('^'+[regex]::Escape($kind)+'-\d{8}-\d{6}-\d{3}-[a-f0-9]{8}$')) 'Invalid attempt name'
    $path=Join-Path $parent $name
    Must (!(Test-Path -LiteralPath $path)) 'Attempt already exists. Use a new attempt, never overwrite evidence.'
    (New-Item -ItemType Directory -Path $path).FullName
}
function CopyInputs([string]$from,[string]$to,[string[]]$names) {
    foreach($name in $names) {
        $p=Join-Path $from $name
        $q=Join-Path $to $name
        $hash=(Get-FileHash -LiteralPath $p).Hash
        [IO.File]::Copy($p,$q,$false)
        Fingerprint $q $hash
        "$hash  $name"
    }
}
function CheckAclLink([string]$scope) {
    $names=@('acl-before.json','acl-after.json','acl-ready.txt','runtime-source.sha256')
    $rows=@(Get-Content -LiteralPath (Join-Path $scope 'acl-origin.sha256') -Encoding UTF8)
    $parent=Split-Path -Parent $scope
    Must ($rows.Count -eq $names.Count) 'ACL source inventory differs'
    for($i=0;$i -lt $names.Count;$i++) {
        $name=$names[$i]
        if($rows[$i] -cnotmatch ('^([0-9A-F]{64})  '+[regex]::Escape($name)+'$')) { throw 'ACL source row differs' }
        $hash=$Matches[1]
        Fingerprint (Join-Path $scope $name) $hash
        Fingerprint (Join-Path $parent $name) $hash
    }
}
function SameServer([string]$commandLine,[string]$attempt,[bool]$demo=$false) {
    $tag='story23_attempt='+[regex]::Escape($attempt)
    $pattern=if($demo){'(?i)run-story-2-3-demo-server\.py.*127\.0\.0\.1:8003.*--noreload'}else{'(?i)manage\.py.*runserver.*127\.0\.0\.1:8003.*--noreload'}
    $commandLine -match $pattern -and
        $commandLine -cmatch ('(?:^|[\s"])'+$tag+'(?=[\s"]|$)')
}

function DemoTools([string]$scope,[bool]$write) {
    $files=@('run-story-2-3-demo-server.py','story23_formal_demo.py','read-story-2-3-formal.py')
    $lines=@(foreach($name in $files){ (Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $name)).Hash+'  '+$name })
    $value=$lines -join $nl
    if($write){ NewText 'demo-tools.sha256' $value }
    else {
        $actual=(Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $scope 'demo-tools.sha256')).TrimEnd()
        Must ($actual -ceq $value) 'Approved demo tools changed after launch'
    }
}
function ShowDemo($demo) {
    Write-Host ('Student #1 mode: '+$demo.expiry_mode+'; read your student list twice before teacher submission.')
    if($demo.teacher.mode -ceq 'reuse') {
        Write-Host ('Teacher: reuse reservation #'+$demo.teacher.reservation_id+'; no POST.')
    } else {
        Write-Host ('Teacher once only: '+$origin+$demo.teacher.path+' device='+$demo.teacher.device_number)
        Write-Host ('Exact Beijing form start='+$demo.teacher.form_start+' end='+$demo.teacher.form_end)
    }
}

$old=@{}
$names=@('PGPASSFILE','PGCONNECT_TIMEOUT','PGCLIENTENCODING','LAB_BOOKING_DB_MODE','LAB_BOOKING_SECRET_KEY',
         'DJANGO_SETTINGS_MODULE','PYTHONDONTWRITEBYTECODE','STORY23_ACCOUNTS_MANIFEST','STORY23_DEMO_RECEIPT','STORY23_ACCOUNT_STUDENT','STORY23_ACCOUNT_TEACHER','STORY23_ACCOUNT_ADMIN')
foreach ($n in $names) { $old[$n]=[Environment]::GetEnvironmentVariable($n,'Process') }
try {
    if ($Phase -ne 'Chrome') {
        if (!$Passfile) { $Passfile=$env:PGPASSFILE }
        if (!$Passfile) { $Passfile=Join-Path $env:LOCALAPPDATA 'LabBooking/PostgreSQL17/pgpass.conf' }
        Must ($Passfile -match '^[A-Za-z]:[\\/]' -and (Test-Path -LiteralPath $Passfile -PathType Leaf)) 'Use the existing protected absolute PGPASSFILE'
        $Passfile=(Resolve-Path -LiteralPath $Passfile).Path
        Must (!$Passfile.StartsWith($root.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)) 'Keep the passfile outside the repository'
        $conflicts=@('PGHOST','PGHOSTADDR','PGPORT','PGDATABASE','PGUSER','PGPASSWORD','PGSERVICE','PGSERVICEFILE',
                     'PGOPTIONS','PYTHONHOME','PYTHONPATH') | Where-Object {Test-Path -LiteralPath "Env:$_"}
        Must (!$conflicts) ('Conflicting environment settings: '+($conflicts -join ', '))
        $env:PGPASSFILE=$Passfile
        $env:PGCONNECT_TIMEOUT='5'
        $env:PGCLIENTENCODING='UTF8'
        $env:LAB_BOOKING_DB_MODE='runtime'
        $env:DJANGO_SETTINGS_MODULE='lab_booking.settings'
        $env:PYTHONDONTWRITEBYTECODE='1'
        $env:LAB_BOOKING_SECRET_KEY=[Guid]::NewGuid().ToString('N')+[Guid]::NewGuid().ToString('N')
        Fingerprint $grant '1E3B21C4B9AE065A7A3FD9BEA5116DF2981BAC0AB0A8A696938635F3EC3B72E5'
        Fingerprint $narrow '54F77DF433450784D8BB83E37C6817116BE728B180535B2F8E971E21D66CCF4D'
    }
    if ($Phase -eq 'Acl') {
        Must (!$RunDirectory) 'Acl starts a new receipt, never reuses a path'
        $name='story-2-3-formal-'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8)
        $run=(New-Item -ItemType Directory -Path (Join-Path (Resolve-Path -LiteralPath $OutputRoot).Path $name)).FullName
    } else {
        Must (!!$RunDirectory) 'Supply the ACL parent for Inspect/Serve/Recover, or the smoke attempt for Chrome/Finish'
        if ($Phase -in @('Chrome','Finish')) {
            $run=EvidenceDirectory $RunDirectory '^smoke-\d{8}-\d{6}-\d{3}-[a-f0-9]{8}$'
            $null=EvidenceDirectory (Split-Path -Parent $run) '^story-2-3-formal-\d{8}-\d{6}-\d{3}-[a-f0-9]{8}$'
        } else {
            $run=EvidenceDirectory $RunDirectory '^story-2-3-formal-\d{8}-\d{6}-\d{3}-[a-f0-9]{8}$'
        }
    }
    Must (!$SmokeName -or $Phase -in @('Inspect','Serve')) 'SmokeName applies only to Inspect or Serve'
    Must (!$AccountsManifest -or $Phase -in @('Inspect','Serve')) 'AccountsManifest applies only to Inspect or Serve'
    Must (!$AuthorizedDemo -or ($Phase -eq 'Serve' -and $AccountsManifest)) 'AuthorizedDemo is for Serve with the protected manifest only'
    Write-Host ('Evidence input: '+$run)
    switch ($Phase) {
      'Acl' {
        $v=@(Native 'python-version' $python @('--version'))
        Must ($v.Count -eq 1 -and $v[0] -ceq 'Python 3.13.17') 'Original Python version differs'
        NewText 'runtime-source.sha256' ((@(Sources)) -join $nl)
        $catalog=Catalog 'acl-before' ''
        $scope=AppAcl 'before'
        if ($catalog -ceq 'STORY23_READ_NEEDS_FOUR_OK' -and $scope -ceq 'ACL_RESULT=NEEDS_FOUR_COLUMN_GRANT') {
            NewText 'grant-intent.txt' 'Only SELECT(reservation_id,action,actor_type,reason) on public.audit_operationhistory to lab_booking_app.'
            $argsGrant=@('-X','-w','-v','ON_ERROR_STOP=1','-h','127.0.0.1','-p','5433','-U','lab_booking_migrator','-d','lab_booking','-f',$grant)
            $result=@(Native 'grant' $Psql $argsGrant)
            $mark=@($result|Where-Object {$_ -cin @('STORY23_HISTORY_SELECT_COMMITTED','STORY23_HISTORY_SELECT_ALREADY_EXACT')})
            Must ($mark.Count -eq 1) 'Unconfirmed GRANT output. Use Recover; do not replay.'
            NewText 'grant-outcome.txt' $mark[0]
        } elseif ($catalog -ceq 'STORY23_READ_EXACT_OK' -and $scope -ceq 'ACL_RESULT=EXACT_COLUMNS_PRESENT') {
            NewText 'grant-outcome.txt' 'ALREADY_EXACT_NO_GRANT'
        } else { throw 'Read-only permission checks disagree; no GRANT executed.' }
        $null=Catalog 'acl-after' 'STORY23_READ_EXACT_OK'
        Must ((AppAcl 'after') -ceq 'ACL_RESULT=EXACT_COLUMNS_PRESENT') 'Postcheck does not confirm exact ACL'
        NewText 'acl-ready.txt' 'STORY23_FORMAL_ACL_READY'
        'STORY23_FORMAL_ACL_READY'
      }
      'Recover' {
        $tag='recover-'+(Get-Date -Format 'yyyyMMddHHmmssfff')
        $catalog=Catalog $tag ''
        $scope=AppAcl $tag
        if ($catalog -ceq 'STORY23_READ_EXACT_OK' -and $scope -ceq 'ACL_RESULT=EXACT_COLUMNS_PRESENT') {
            if ((Test-Path -LiteralPath (Join-Path $run 'acl-before.json')) -and !(Test-Path -LiteralPath (Join-Path $run 'acl-ready.txt'))) {
                $before=(Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $run 'acl-before.json')|ConvertFrom-Json)
                $now=(Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $run ($tag+'.json'))|ConvertFrom-Json)
                Must ($now.prior_acl_sha256 -ceq $before.prior_acl_sha256 -and
                    (ConvertTo-Json -InputObject $now.migrations -Depth 8 -Compress) -ceq
                    (ConvertTo-Json -InputObject $before.migrations -Depth 8 -Compress)) 'Unexpected drift during read-back'
                if (!(Test-Path -LiteralPath (Join-Path $run 'acl-after.json'))) {
                    Copy-Item -LiteralPath (Join-Path $run ($tag+'.json')) -Destination (Join-Path $run 'acl-after.json')
                    NewText 'acl-after-recovery-source.txt' ($tag+'.json')
                }
                NewText 'acl-ready.txt' 'STORY23_FORMAL_ACL_READY_BY_READBACK'
            }
            'STORY23_FORMAL_ACL_EXACT_READBACK'
        } elseif ($catalog -ceq 'STORY23_READ_NEEDS_FOUR_OK' -and $scope -ceq 'ACL_RESULT=NEEDS_FOUR_COLUMN_GRANT') {
            'STORY23_FORMAL_ACL_STILL_NEEDS_FOUR'
        } else { throw 'Readbacks disagree. No GRANT executed.' }
      }
      {$_ -in @('Inspect','Serve')} {
        $aclRun=$run
        $run=$null
        $run=NewAttempt $aclRun 'smoke' $SmokeName
        Write-Host ('Smoke evidence: '+$run)
        $ready=(Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $aclRun 'acl-ready.txt')).Trim()
        Must ($ready -cin @('STORY23_FORMAL_ACL_READY','STORY23_FORMAL_ACL_READY_BY_READBACK')) 'Complete ACL postcheck first'
        $after=Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $aclRun 'acl-after.json')|ConvertFrom-Json
        Must ($after.state -ceq 'EXACT') 'ACL parent does not contain exact readback'
        NewText 'acl-origin.sha256' ((@(CopyInputs $aclRun $run @('acl-before.json','acl-after.json','acl-ready.txt','runtime-source.sha256'))) -join $nl)
        NewText 'acl-origin.txt' ('source=..; acl_run='+(Split-Path -Leaf $aclRun)+'; see acl-origin.sha256')
        CheckAclLink $run
        if ($Phase -eq 'Serve') {
            Must (@(Listeners).Count -eq 0) '8003 is occupied. Do not touch existing processes.'
            Must (Test-Path -LiteralPath $Chrome -PathType Leaf) 'Chrome executable unavailable'
        }
        CheckSources $run
        if ($AccountsManifest) {
            $manifest=Get-Item -LiteralPath $AccountsManifest
            Must (!$manifest.PSIsContainer -and !$manifest.FullName.StartsWith($root.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)) 'Use the existing protected account manifest outside the repository'
            $env:STORY23_ACCOUNTS_MANIFEST=$manifest.FullName
        } else {
            [Environment]::SetEnvironmentVariable('STORY23_ACCOUNTS_MANIFEST',$null,'Process')
            foreach ($role in @('student','teacher','admin')) {
                $user=(Read-Host ("Exact active preset $role login username, not display label or password")).Trim()
                Must (![string]::IsNullOrWhiteSpace($user)) 'No authorized sample user selected'
                [Environment]::SetEnvironmentVariable(('STORY23_ACCOUNT_'+$role.ToUpperInvariant()),$user,'Process')
            }
        }
        try {
            if ($Phase -eq 'Inspect') { $null=Catalog 'sample-inspect' 'STORY23_READ_EXACT_OK' }
            elseif ($AuthorizedDemo) {
                DemoTools $run $true
                $null=Catalog 'demo-before' 'STORY23_READ_EXACT_OK'
            } else { $null=Catalog 'sample-before' 'STORY23_READ_EXACT_OK' }
        } finally {
            foreach($role in @('STUDENT','TEACHER','ADMIN')) {
                [Environment]::SetEnvironmentVariable(('STORY23_ACCOUNT_'+$role),$null,'Process')
            }
            [Environment]::SetEnvironmentVariable('STORY23_ACCOUNTS_MANIFEST',$null,'Process')
        }
        if ($Phase -eq 'Inspect') {
            $sample=(Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $run 'sample-inspect.json')|ConvertFrom-Json).sample
            $hasChrome=Test-Path -LiteralPath $Chrome -PathType Leaf
            $free=@(Listeners).Count -eq 0
            $stillSafe=[DateTimeOffset]::Now -lt [DateTimeOffset]::Parse($sample.deadline_beijing)
            foreach($role in @('student','teacher','admin')) {
                $a=$sample.accounts.$role
                '{0}: account_id={1}; reservations={2}; unsafe_pending={3}' -f $role,$a.account_id,@($a.reservations).Count,(@($a.unsafe_pending_ids) -join ',')
            }
            "Port8003Free=$free ChromeAvailable=$hasChrome WindowSufficient=$($sample.window_sufficient) FullDetailReady=$($sample.browser_full_ready)"
            if ($sample.browser_full_ready -and $free -and $hasChrome -and $stillSafe) {
                NewText 'planning-result.txt' 'STORY23_FORMAL_SMOKE_FULL_READY'
                'STORY23_FORMAL_SMOKE_FULL_READY'
            } else {
                NewText 'planning-result.txt' 'STORY23_FORMAL_SMOKE_HOLD'
                'STORY23_FORMAL_SMOKE_HOLD'
            }
            Write-Host 'Planning only. No credentials saved, no service started, and no business data written.'
            break
        }
        NewText 'sample-before.sha256' (Get-FileHash -LiteralPath (Join-Path $run 'sample-before.json')).Hash
        $sample=ReadSample $run
        if ($AuthorizedDemo) {
            Must ($null -ne $sample.demo -and $sample.demo.ready) 'Approved demo plan is absent'
            DemoTools $run $false
            ShowDemo $sample.demo
        } else { Must $sample.browser_business_safe 'Read-only FR-018 evidence is unsafe' }
        Must ([DateTimeOffset]::Now -lt [DateTimeOffset]::Parse($sample.deadline_beijing) -and
              @(Listeners).Count -eq 0) 'Verification window expired or 8003 newly occupied'
        [IO.File]::Copy((Join-Path $PSScriptRoot 'story-2-3-chrome-receipt-template.md'),(Join-Path $run 'chrome-receipt.md'),$false)
        $attempt=Split-Path -Leaf $run
        NewText 'launch.txt' ((@((Get-Date -Format o),$origin,'original .venv; runtime; --noreload',$attempt)) -join $nl)
        Write-Host ('Target '+$origin+'; Beijing deadline '+$sample.deadline_beijing+'. Run Chrome in another PowerShell.')
        Write-Host ('Receipt for this attempt: '+(Join-Path $run 'chrome-receipt.md')+' (cite existing evidence; do not transcribe machine fields).')
        Write-Host 'Keep this foreground window. Use Ctrl+C here only; never stop 8000 or 8001.'
        $out=Join-Path $run 'server.stdout.txt'
        $err=Join-Path $run 'server.stderr.txt'
        Must (!(Test-Path -LiteralPath $out) -and !(Test-Path -LiteralPath $err)) 'Server output would overwrite evidence'
        Push-Location -LiteralPath $root
        $policy=$ErrorActionPreference
        try {
            $ErrorActionPreference='Continue'
            if ($AuthorizedDemo) {
                $env:STORY23_DEMO_RECEIPT=$run
                $demoServer=Join-Path $PSScriptRoot 'run-story-2-3-demo-server.py'
                & $python -B -u -X "story23_attempt=$attempt" $demoServer '127.0.0.1:8003' --noreload 1> $out 2> $err
            } else {
                & $python -B -u -X "story23_attempt=$attempt" manage.py runserver '127.0.0.1:8003' --noreload 1> $out 2> $err
            }
            Stage 'server' ('exit='+$LASTEXITCODE)
        } finally { $ErrorActionPreference=$policy; Pop-Location }
      }
      'Chrome' {
        $scope=$run
        $run=$null
        $run=NewAttempt $scope 'chrome'
        Write-Host ('Chrome evidence: '+$run)
        CheckAclLink $scope
        CheckSources $scope
        $native=@(Listeners)
        Must ($native.Count -eq 1) 'Wait for the new 8003 listener before opening Chrome'
        if ($native[0] -notmatch '^\s*TCP\s+127\.0\.0\.1:8003\s+\S+\s+LISTENING\s+(\d+)\s*$') { throw 'Wrong listener binding' }
        $listenPid=[int]$Matches[1]
        $launch=@(Get-Content -LiteralPath (Join-Path $scope 'launch.txt') -Encoding UTF8)
        $attempt=Split-Path -Leaf $scope
        Must ($launch.Count -eq 4 -and $launch[1] -ceq $origin -and $launch[3] -ceq $attempt) 'Launch receipt differs from requested attempt'
        $started=[DateTimeOffset]::Parse($launch[0])
        $proc=Get-Process -Id $listenPid
        Must ($proc.ProcessName -eq 'python' -and ([DateTimeOffset]$proc.StartTime) -ge $started) 'Listener is not the Python process for this run'
        $cim=Get-CimInstance Win32_Process -Filter ('ProcessId='+$listenPid)
        $sample=ReadSample $scope
        $isDemo=$null -ne $sample.demo
        Must (SameServer $cim.CommandLine $attempt $isDemo) 'Listener command belongs to a different attempt'
        if ($isDemo) {
            DemoTools $scope $false
            Must ($sample.demo.ready -and (Test-Path -LiteralPath (Join-Path $scope 'guard-start.txt') -PathType Leaf)) 'Guarded smoke did not start'
            ShowDemo $sample.demo
        } else { Must $sample.browser_business_safe 'Read-only FR-018 evidence is unsafe' }
        Must ([DateTimeOffset]::Now -lt [DateTimeOffset]::Parse($sample.deadline_beijing)) 'Do not open list/detail outside verified window'
        $ver=(Get-Item -LiteralPath $Chrome).VersionInfo.ProductVersion
        NewText 'listener.txt' ((@(('pid='+$listenPid),('origin='+$origin),('start={0:o}' -f $proc.StartTime),('chrome='+$ver),('attempt='+$attempt))) -join $nl)
        foreach ($role in @('student','teacher','admin')) {
            $profile=Join-Path ([IO.Path]::GetTempPath()) ('LabBooking-story23-'+$role+'-'+[Guid]::NewGuid().ToString('N'))
            Start-Process -FilePath $Chrome -WindowStyle Normal -ArgumentList ('--user-data-dir="'+$profile+'" --no-first-run --disable-sync --new-window '+$origin+'/login/')
            Stage ('chrome-'+$role) 'launch-requested'
        }
        NewText 'opened.txt' 'STORY23_CHROME_LAUNCHES_REQUESTED'
        Write-Host ('Network / Preserve log; keep only necessary redacted evidence and actual page observations. Do not access business routes after '+$sample.deadline_beijing)
      }
      'Finish' {
        $scope=$run
        $run=$null
        $run=NewAttempt $scope 'finish'
        Write-Host ('Finish evidence: '+$run)
        Must (@(Listeners).Count -eq 0) 'Stop only the newly started 8003 service with Ctrl+C first'
        CheckAclLink $scope
        $sample=ReadSample $scope
        $isDemo=$null -ne $sample.demo
        if ($isDemo) {
            DemoTools $scope $false
            Must $sample.demo.ready 'Approved demo plan is absent'
        } else { Must $sample.browser_business_safe 'Read-only FR-018 evidence is unsafe' }
        Must (Test-Path -LiteralPath (Join-Path $scope 'chrome-receipt.md') -PathType Leaf) 'No browser receipt file'
        $attempt=Split-Path -Leaf $scope
        $opened=@(Get-ChildItem -LiteralPath $scope -Directory -Filter 'chrome-*' | Where-Object {
            $o=Join-Path $_.FullName 'opened.txt'
            $l=Join-Path $_.FullName 'listener.txt'
            !(($_.Attributes -band [IO.FileAttributes]::ReparsePoint)) -and
                (Test-Path -LiteralPath $o -PathType Leaf) -and (Test-Path -LiteralPath $l -PathType Leaf) -and
                ((Get-Content -Raw -Encoding UTF8 -LiteralPath $o).Trim() -ceq 'STORY23_CHROME_LAUNCHES_REQUESTED') -and
                (@(Get-Content -LiteralPath $l -Encoding UTF8) -ccontains ('attempt='+$attempt))
        })
        Must ($opened.Count -gt 0) 'No complete Chrome launch receipt for this smoke attempt'
        NewText 'chrome-attempts.txt' ((@($opened|ForEach-Object {$_.Name})) -join $nl)
        $inputs=@('acl-before.json','acl-after.json','runtime-source.sha256','sample-before.json','sample-before.sha256')
        if ($isDemo) { $inputs+=@('browser-http.jsonl','guard-start.txt','demo-tools.sha256') }
        NewText 'sample-origin.sha256' ((@(CopyInputs $scope $run $inputs)) -join $nl)
        $null=ReadSample $run
        CheckSources $run
        if ($isDemo) { $null=Catalog 'demo-after' 'STORY23_READ_EXACT_OK' }
        else { $null=Catalog 'sample-after' 'STORY23_READ_EXACT_OK' }
        Must ((AppAcl 'browser-after') -ceq 'ACL_RESULT=EXACT_COLUMNS_PRESENT') 'Post-browser ACL drift'
        NewText 'postcheck.txt' 'STORY23_FORMAL_POSTCHECK_OK'
        'STORY23_FORMAL_POSTCHECK_OK'
        Write-Host 'Read-back is not the browser verdict. Use the smoke chrome-receipt.md to cite machine evidence and retain the actual page observations and human decision.'
      }
    }
} catch {
    if ($run) { Stage $Phase ('STOP: '+$_.Exception.Message) }
    throw
} finally {
    foreach($n in $names){[Environment]::SetEnvironmentVariable($n,$old[$n],'Process')}
}
