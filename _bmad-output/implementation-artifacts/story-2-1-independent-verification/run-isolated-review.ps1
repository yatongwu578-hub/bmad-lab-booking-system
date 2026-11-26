
[CmdletBinding()]
param([string]$Passfile, [string]$Chrome,
      [string]$Psql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe')

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$art = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repo '.venv/Scripts/python.exe'
$preflight = Join-Path $art 'preflight-story-2-1.ps1'
$pin = Join-Path $PSScriptRoot 'reviewed-inputs.sha256'
$historicalBaseline = '5DF4D59616196EA9BC2604E46B584A1281CAD313151634F0C5F4DB0035A34272'
$tag = (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + ([Guid]::NewGuid().ToString('N').Substring(0,12))
$out = Join-Path $PSScriptRoot ("independent-run-$tag")
$null = New-Item -ItemType Directory -Path $out
Write-Host "Independent review output: $out"
$utf8 = [Text.UTF8Encoding]::new($false)

if (-not $Passfile) { $Passfile = $env:PGPASSFILE }
if (-not $Passfile) { $Passfile = Join-Path $env:LOCALAPPDATA 'LabBooking/PostgreSQL17/pgpass.conf' }
if (-not $Chrome) { $Chrome = $env:LAB_BOOKING_R1_CHROME }
if (-not $Chrome) { $Chrome = Join-Path $env:ProgramFiles 'Google/Chrome/Application/chrome.exe' }
$vars = @('LAB_BOOKING_DB_MODE','LAB_BOOKING_R1_CHROME','LAB_BOOKING_SECRET_KEY',
          'DJANGO_SETTINGS_MODULE','PGPASSFILE','PYTHONIOENCODING','PYTHONDONTWRITEBYTECODE','PYTHONPATH')
$old = @{}
foreach ($name in $vars) { $old[$name] = [Environment]::GetEnvironmentVariable($name,'Process') }

function Stage([string]$Name, [string]$Value) {
    [IO.File]::AppendAllText((Join-Path $out 'stages.txt'),"$(Get-Date -Format o) $Name $Value" + [Environment]::NewLine,$utf8)
}
function Assert-Review([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}
function Hash-Snapshot([string]$Label) {
    $rows = @(Get-Content -LiteralPath $pin -Encoding UTF8 | Where-Object { $_ })
    $rel = @()
    $observed = @(foreach ($row in $rows) {
        Assert-Review ($row -cmatch '^([A-F0-9]{64}) {2}(.+)$') 'Malformed reviewed-inputs manifest.'
        $path = $Matches[2]
        $rel += $path
        $got = (Get-FileHash -LiteralPath (Join-Path $repo $path) -Algorithm SHA256).Hash
        "$got  $path"
    })
    Assert-Review ($rows.Count -eq 77 -and @($rel | Sort-Object -Unique).Count -eq 77) 'Unexpected number of hash inputs.'
    $runtime = @('manage.py','requirements.txt')
    foreach ($folder in @('accounts','equipment','lab_booking','audit','reservations')) {
        $runtime += @(Get-ChildItem -LiteralPath (Join-Path $repo $folder) -File -Recurse |
            Where-Object { $_.Extension -in '.py','.html' } |
            ForEach-Object { $_.FullName.Substring($repo.Length+1).Replace('\','/') })
    }
    $actualRuntime = @($rel | Where-Object { $_ -cmatch '^(accounts|equipment|lab_booking|audit|reservations)/|^(manage\.py|requirements\.txt)$' })
    Assert-Review (@(Compare-Object ($actualRuntime | Sort-Object -CaseSensitive) ($runtime | Sort-Object -CaseSensitive) -CaseSensitive).Count -eq 0) 'Extra or missing runtime/test input.'
    [IO.File]::WriteAllLines((Join-Path $out "$Label.sha256"),[string[]]$observed,$utf8)
    Assert-Review (@(Compare-Object $rows $observed -CaseSensitive).Count -eq 0) 'Reviewed inputs changed. See observed hashes.'
}
function Run-Python([string]$Name, [string[]]$Arguments, [string]$Mark) {
    Write-Host "Running $Name"
    $stdout = Join-Path $out "$Name.stdout.txt"
    $stderr = Join-Path $out "$Name.stderr.txt"
    foreach ($arg in $Arguments) { Assert-Review ($arg -notmatch '["\r\n]') 'Unexpected process argument.' }
    $quoted = ($Arguments | ForEach-Object { '"' + $_ + '"' }) -join ' '
    [IO.File]::WriteAllText((Join-Path $out "$Name.command.txt"),('"' + $python + '" ' + $quoted),$utf8)
    $process = Start-Process -FilePath $python -ArgumentList $quoted -WorkingDirectory $repo -Wait -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    Stage $Name "exit=$($process.ExitCode)"
    Assert-Review ($process.ExitCode -eq 0) "$Name exited $($process.ExitCode)."
    $all = @(Get-Content -LiteralPath $stdout,$stderr -Encoding UTF8)
    Assert-Review (@($all | Where-Object { $_ -ceq $Mark }).Count -eq 1) "$Name exact completion line missing or duplicated."
    Stage "$Name-marker" 'confirmed=true'
    return $all
}
function Probe([string]$Group, [string]$Name) {
    $null = Run-Python $Name @('manage.py','verify_reservation_transactions','--group',$Group,'--evidence',(Join-Path $out "$Name.jsonl"),'--traceback') "STORY21_PROBE_OK $Group"
}
function Exact-Regression([object[]]$Lines,[int]$Count) {
    $found = @($Lines | Where-Object { $_ -cmatch '^Found [0-9]+ test\(s\)\.$' })
    $ran = @($Lines | Where-Object { $_ -cmatch '^Ran [0-9]+ tests? in [0-9.]+s$' })
    $passed = @($Lines | Where-Object { $_ -cmatch '^ok$|\.{3} ok$' }).Count
    $skipped = @($Lines | Where-Object { $_ -cmatch '\.{3} skipped ' }).Count
    Assert-Review ($found.Count -eq 1 -and $found[0] -ceq "Found $Count test(s)." -and
        $ran.Count -eq 1 -and $ran[0] -cmatch "^Ran $Count tests? in [0-9.]+s$" -and $passed -eq $Count -and $skipped -eq 0) 'Unexpected regression counts.'
    return [ordered]@{found=$Count;run=$Count;passed=$passed;skipped=$skipped}
}
function Read-Probe([string]$Name, [int]$Cases) {
    $records = @(Get-Content -LiteralPath (Join-Path $out "$Name.jsonl") -Encoding UTF8 |
        Where-Object {$_} | ForEach-Object { $_ | ConvertFrom-Json })
    Assert-Review ($records.Count -eq ($Cases + 2) -and $records[0].group -ceq $Name -and
                   $records[-1].cleanup -eq $true -and $records[0].python -ceq '3.13.17') "$Name case count or cleanup evidence mismatch."
    Assert-Review (((@($records[0].database)[0..8] -join '|')) -ceq 'test_lab_booking|lab_booking_test|lab_booking_test|127.0.0.1|5433|170012|read committed|False|False') "$Name DB target mismatch."
    foreach ($pair in @('before:after','schema_before:schema_after')) {
        $from,$to = $pair.Split(':')
        Assert-Review (($records[0].$from | ConvertTo-Json -Depth 30 -Compress) -ceq
                       ($records[-1].$to | ConvertTo-Json -Depth 30 -Compress)) "$Name baseline transition mismatch."
    }
    return $records[1..$Cases]
}
$checkedBaseline = $false
$summary = [ordered]@{source='new independent-review execution on ordinary PowerShell'; target='127.0.0.1:5433/test_lab_booking'; boundary='reuse audited development B3/B4/readback only'}
$runLease = $null
try {
    $runLease = [IO.File]::Open((Join-Path $PSScriptRoot '.independent-review.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
    $head = @(git -C $repo rev-parse HEAD)
    Assert-Review ($LASTEXITCODE -eq 0 -and $head.Count -eq 1 -and $head[0] -ceq 'e196aba098771a31eb203be4270b460d5e0aab42') 'Unexpected Git baseline.'
    Hash-Snapshot 'before'
    Stage 'source-integrity' 'confirmed=true'
    foreach ($script in @($PSCommandPath,$preflight)) {
        $tokens = $null
        $parseErrors = $null
        $null = [Management.Automation.Language.Parser]::ParseFile($script,[ref]$tokens,[ref]$parseErrors)
        Assert-Review ($parseErrors.Count -eq 0) "PowerShell syntax errors in $script."
    }
    $env:LAB_BOOKING_DB_MODE = 'test'
    $env:LAB_BOOKING_R1_CHROME = $Chrome
    $env:LAB_BOOKING_SECRET_KEY = [Guid]::NewGuid().ToString('N') + [Guid]::NewGuid().ToString('N')
    $env:DJANGO_SETTINGS_MODULE = 'lab_booking.settings'
    $env:PGPASSFILE = $Passfile
    $env:PYTHONIOENCODING = 'utf-8'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    try {
        $pre = @(& $preflight -Passfile $Passfile -Chrome $Chrome -Psql $Psql -ProbeIsolatedDatabase 2>&1 |
                 Tee-Object -FilePath (Join-Path $out 'preflight.txt'))
        Assert-Review (@($pre | Where-Object { $_ -ceq 'STORY21_PREFLIGHT_OK' }).Count -eq 1) 'Preflight did not confirm the isolated environment.'
        Stage 'preflight' 'exit=0'
    } catch {
        Stage 'preflight' 'exit=1'
        throw
    }
    Probe 'baseline' 'review-before'
    Assert-Review ((Get-FileHash -LiteralPath (Join-Path $out 'review-before.jsonl')).Hash -ceq $historicalBaseline) 'Isolated initial state differs from reviewed historical baseline; no tests run.'
    $checkedBaseline = $true
    $null = Run-Python 'check' @('manage.py','check') 'System check identified no issues (0 silenced).'
    $null = Run-Python 'migration-drift' @('manage.py','makemigrations','--check','--dry-run') 'No changes detected'
    $summary.regression = Exact-Regression @(Run-Python 'regression' @('manage.py','test','--keepdb','--parallel','1','-v','2') 'OK') 90

    # The separate reviewer-owned label is not part of the 90-test discovery count.
    $env:PYTHONPATH = $PSScriptRoot
    try {
        $nav = @(Run-Python 'navigation' @('manage.py','test','review_navigation','--keepdb','--parallel','1','-v','2') 'OK')
    } finally { Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue }
    $summary.navigation = Exact-Regression $nav 1
    Assert-Review (@($nav | Where-Object { $_ -cmatch '^STORY21_NAVIGATION (student|teacher) ' }).Count -eq 2 -and
                   @($nav | Where-Object { $_ -cmatch '^STORY21_NAVIGATION student ' }).Count -eq 1) 'Missing distinct student/teacher navigation evidence.'

    Probe 'permissions' 'permissions'
    $perms = @(Read-Probe 'permissions' 21)
    Assert-Review (@($perms | Where-Object { $_.denied -eq 12 }).Count -eq 1) 'Permission denominator mismatch.'
    $summary.permissionDenials = 12

    Probe 'interleavings' 'interleavings'
    $il = @(Read-Probe 'interleavings' 15)
    $want = @{I1=1;I2=2;I3=2;I4=2;I5=3;I6=4;I7=1}
    foreach ($id in $want.Keys) {
        Assert-Review (@($il | Where-Object { $_.case -ceq $id }).Count -eq $want[$id]) "Wrong interleaving case count for $id."
    }
    $summary.interleavings = 15

    Probe 'faults' 'faults'
    $fx = @(Read-Probe 'faults' 5)
    Assert-Review ((($fx | ForEach-Object { $_.case }) -join ',') -ceq 'F1-history,F1-reservation,F2,F3,F4') 'Fault case IDs mismatch.'
    $summary.faults = 5

    Probe 'nfr001-standard' 'nfr001-standard'
    $rounds = @(Read-Probe 'nfr001-standard' 10)
    $summary.nfr001 = @(for($i=0;$i -lt 10;$i++) {
        $round = $rounds[$i]
        $ok = @($round.responses | Where-Object { $_.response.status -eq 201 })
        $conflicts = @($round.responses | Where-Object { $_.response.status -eq 409 -and $_.response.body.Contains('所选时段与有效预约冲突，请选择其他时段。') })
        $pids = @($round.responses | ForEach-Object { $_.server.pid } | Sort-Object -Unique)
        Assert-Review ($round.round -eq ($i+1) -and @($round.responses).Count -eq 20 -and $ok.Count -eq 1 -and
                       $conflicts.Count -eq 19 -and $pids.Count -eq 20 -and @($round.observed_overlaps).Count -gt 0 -and
                       @($round.after.rows).Count -eq 1 -and @($round.after.effective).Count -eq 1 -and
                       $round.after.effective[0].status -ceq 'pending') "Round $($i+1) failed the full NFR gate."
        [ordered]@{round=$i+1;responses=20;conflicts=19;success=1;backendPids=20;effective=1;overlapPairs=@($round.observed_overlaps).Count}
    })
    Stage 'verification-groups' 'confirmed=true'
} catch {
    [IO.File]::WriteAllText((Join-Path $out 'failure.txt'),($_ | Out-String),$utf8)
    throw
} finally {
    try {
        if ($checkedBaseline) {
            Probe 'baseline' 'review-after'
            Assert-Review ((Get-FileHash -LiteralPath (Join-Path $out 'review-after.jsonl')).Hash -ceq $historicalBaseline) 'Isolated full-row or migration/table baseline changed.'
            Stage 'final-database-integrity' 'confirmed=true'
        }
    } finally {
        try {
            if (Test-Path -LiteralPath (Join-Path $out 'before.sha256')) { Hash-Snapshot 'after' }
        } finally {
            foreach ($name in $vars) { [Environment]::SetEnvironmentVariable($name,$old[$name],'Process') }
            if ($runLease) { $runLease.Dispose() }
        }
    }
}
[IO.File]::WriteAllText((Join-Path $out 'summary.json'),($summary | ConvertTo-Json -Depth 12),$utf8)
Stage 'independent-complete' 'exit=0'
Write-Output "STORY21_INDEPENDENT_REVIEW_OK $out"
