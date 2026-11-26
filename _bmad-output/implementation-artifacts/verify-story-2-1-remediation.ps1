[CmdletBinding()]
param(
    [string]$Passfile,
    [string]$Chrome,
    [string]$Psql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe',
    [switch]$RecheckConcurrencyAndFaults
)

# Run in ordinary Windows PowerShell from this repository. The isolated DB must already be migrated.
# Never connects to the formal DB, migrates, grants, or waits for a real hour boundary.
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$python = Join-Path $repo '.venv/Scripts/python.exe'
$preflight = Join-Path $PSScriptRoot 'preflight-story-2-1.ps1'
$review = Join-Path $PSScriptRoot 'story-2-1-independent-verification'
$historicalBaseline = '5DF4D59616196EA9BC2604E46B584A1281CAD313151634F0C5F4DB0035A34272'
$tag = (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,12)
$out = Join-Path $PSScriptRoot "story-2-1-remediation-run-$tag"
$null = New-Item -ItemType Directory -Path $out
Write-Host "Story 2.1 remediation output: $out"
$utf8 = [Text.UTF8Encoding]::new($false)
$vars = @('LAB_BOOKING_DB_MODE','LAB_BOOKING_R1_CHROME','LAB_BOOKING_SECRET_KEY','DJANGO_SETTINGS_MODULE',
          'PGPASSFILE','PYTHONIOENCODING','PYTHONDONTWRITEBYTECODE','PYTHONPATH')
$old = @{}
foreach ($name in $vars) { $old[$name] = [Environment]::GetEnvironmentVariable($name,'Process') }
if (-not $Passfile) { $Passfile = $env:PGPASSFILE }
if (-not $Passfile) { $Passfile = Join-Path $env:LOCALAPPDATA 'LabBooking/PostgreSQL17/pgpass.conf' }
if (-not $Chrome) { $Chrome = $env:LAB_BOOKING_R1_CHROME }
if (-not $Chrome) { $Chrome = Join-Path $env:ProgramFiles 'Google/Chrome/Application/chrome.exe' }
$changed = @('reservations/forms.py','reservations/tests.py',
             'reservations/management/commands/verify_reservation_transactions.py')
$added = @('reservations/management/commands/_chrome_probe.py')
$remediationHashes = @{
    'reservations/forms.py' = 'A2BF45D9CA6DE3DC080C4292876BAA78DF84D7E6E721CA883B3A3812E0C9D471'
    'reservations/tests.py' = 'E51781E7C789CA07AAF1CA4FFA1762C4F88CC871E12248D7D993D328333FA85C'
    'reservations/management/commands/_chrome_probe.py' = '1191F3E221CD25246824CB483008775BC985C2F6E42731061C3C694EA814CF80'
    'reservations/management/commands/verify_reservation_transactions.py' = '1AE129E802721B7822CA5EC5D8FEF21E0274E49968809EF03C04F991AC7CF972'
}
$historicalPath = Join-Path $PSScriptRoot 'story-2-1-recheck-2ee949f8d8014388a2d9792c86a4978c/story-2-1-run-20261126-173610-155-37026c15'
$historicalHashes = [ordered]@{
    'faults' = 'FC59FC3DC9B32531A4E02FE0DB7D03100B615E93ECF6C56935A3AA96503C2FD2'
    'nfr001-standard' = '3364EDF809D5F11C2E865C6608636C6A80FA16736D16C74CA4E1C759D9A7AEC1'
    'time-boundaries' = 'BCCB5AFA5B7F2AC96F8B0454F0A69EA6E4A1CA157A95E84946DCD5CF4C308C9E'
}
$summary = [ordered]@{source='Story 2.1 targeted D-040 evidence execution'; evidenceRevision='D-040'; target='127.0.0.1:5433/test_lab_booking'}

function Assert-Stage([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}
function Stage([string]$Name, [string]$Value) {
    [IO.File]::AppendAllText((Join-Path $out 'stages.txt'),"$(Get-Date -Format o) $Name $Value" + [Environment]::NewLine,$utf8)
}
function Save-Source([string]$Label) {
    $pin = Join-Path $review 'reviewed-inputs.sha256'
    $oldHashes = @{}
    foreach ($line in (Get-Content -LiteralPath $pin -Encoding UTF8 | Where-Object {$_})) {
        Assert-Stage ($line -cmatch '^([A-F0-9]{64}) {2}(.+)$') 'Malformed historical manifest.'
        $oldHashes[$Matches[2]] = $Matches[1]
    }
    $runtime = @('manage.py','requirements.txt')
    foreach ($folder in @('accounts','equipment','lab_booking','audit','reservations')) {
        $runtime += @(Get-ChildItem -LiteralPath (Join-Path $repo $folder) -File -Recurse |
            Where-Object { $_.Extension -in '.py','.html' } |
            ForEach-Object { $_.FullName.Substring($repo.Length+1).Replace('\','/') })
    }
    $oldRuntime = @($oldHashes.Keys | Where-Object { $_ -cmatch '^(accounts|equipment|lab_booking|audit|reservations)/|^(manage\.py|requirements\.txt)$' })
    Assert-Stage ($oldHashes.Count -eq 77 -and
        @(Compare-Object (($oldRuntime + $added) | Sort-Object -CaseSensitive) ($runtime | Sort-Object -CaseSensitive) -CaseSensitive).Count -eq 0) 'Changed runtime inventory.'
    $tools = @('_bmad-output/implementation-artifacts/preflight-story-2-1.ps1',
               '_bmad-output/implementation-artifacts/story-2-1-independent-verification/review_navigation.py')
    $paths = $runtime + $tools + @('_bmad-output/implementation-artifacts/verify-story-2-1-remediation.ps1',
                                   '_bmad-output/implementation-artifacts/story-2-1-independent-verification/reviewed-inputs.sha256')
    $lines = @(foreach ($path in ($paths | Sort-Object -CaseSensitive)) {
        $hash = (Get-FileHash -LiteralPath (Join-Path $repo $path) -Algorithm SHA256).Hash
        if ($path -in ($oldRuntime + $tools)) {
            Assert-Stage ($oldHashes.ContainsKey($path) -and (($hash -cne $oldHashes[$path]) -eq ($path -in $changed))) "Unexpected source difference: $path"
        }
        if ($path -in ($changed + $added)) {
            Assert-Stage ($hash -ceq $remediationHashes[$path]) "Remediation source differs from the reviewed input: $path"
        }
        "$hash  $path"
    })
    [IO.File]::WriteAllLines((Join-Path $out "$Label.sha256"),[string[]]$lines,$utf8)
}
function Run-Python([string]$Name, [string[]]$Arguments, [string]$Marker) {
    Write-Host "Running $Name"
    $stdout = Join-Path $out "$Name.stdout.txt"
    $stderr = Join-Path $out "$Name.stderr.txt"
    foreach ($arg in $Arguments) { Assert-Stage ($arg -notmatch '["\r\n]') 'Invalid process argument.' }
    $quoted = ($Arguments | ForEach-Object { '"' + $_ + '"' }) -join ' '
    [IO.File]::WriteAllText((Join-Path $out "$Name.command.txt"),('"' + $python + '" ' + $quoted),$utf8)
    $process = Start-Process -FilePath $python -ArgumentList $quoted -WorkingDirectory $repo -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    Stage $Name "exit=$($process.ExitCode)"
    Assert-Stage ($process.ExitCode -eq 0) "$Name exited $($process.ExitCode)."
    $lines = @(Get-Content -LiteralPath $stdout,$stderr -Encoding UTF8)
    Assert-Stage (@($lines | Where-Object { $_ -ceq $Marker }).Count -eq 1) "$Name exact completion line missing or duplicated."
    return $lines
}
function Regression([string]$Name, [string[]]$Labels, [int]$Count) {
    $lines = @(Run-Python $Name (@('manage.py','test') + $Labels + @('--keepdb','--parallel','1','-v','2')) 'OK')
    $found = @($lines | Where-Object { $_ -cmatch '^Found [0-9]+ test\(s\)\.$' })
    $ran = @($lines | Where-Object { $_ -cmatch '^Ran [0-9]+ tests? in [0-9.]+s$' })
    $passed = @($lines | Where-Object { $_ -cmatch '^ok$|\.{3} ok$' }).Count
    $skipped = @($lines | Where-Object { $_ -cmatch '\.{3} skipped ' }).Count
    Assert-Stage ($found.Count -eq 1 -and $found[0] -ceq "Found $Count test(s)." -and
        $ran.Count -eq 1 -and $ran[0] -cmatch "^Ran $Count tests? in [0-9.]+s$" -and
        $passed -eq $Count -and $skipped -eq 0) "Unexpected $Name test counts."
    return [ordered]@{found=$Count; run=$Count; passed=$passed; skipped=$skipped}
}
function Probe([string]$Group, [string]$Name, [int]$Count = 0) {
    $jsonl = Join-Path $out "$Name.jsonl"
    $null = Run-Python $Name @('manage.py','verify_reservation_transactions','--group',$Group,'--evidence',$jsonl,'--traceback') "STORY21_PROBE_OK $Group"
    if ($Group -ceq 'baseline') {
        Assert-Stage ((Get-FileHash -LiteralPath $jsonl).Hash -ceq $historicalBaseline) 'Isolated database baseline differs from the historical zero-fixture baseline.'
        return
    }
    $records = @(Get-Content -LiteralPath $jsonl -Encoding UTF8 | Where-Object {$_} | ForEach-Object { $_ | ConvertFrom-Json })
    Assert-Stage ($records.Count -eq ($Count + 2) -and $records[0].group -ceq $Group -and
        $records[0].python -ceq '3.13.17' -and $records[-1].cleanup -eq $true) "$Group case count or cleanup evidence mismatch."
    Assert-Stage ((@($records[0].database)[0..8] -join '|') -ceq
        'test_lab_booking|lab_booking_test|lab_booking_test|127.0.0.1|5433|170012|read committed|False|False') "$Group isolated DB identity mismatch."
    foreach ($pair in @('before:after','schema_before:schema_after')) {
        $from,$to = $pair.Split(':')
        Assert-Stage (($records[0].$from | ConvertTo-Json -Depth 30 -Compress) -ceq
            ($records[-1].$to | ConvertTo-Json -Depth 30 -Compress)) "$Group before/after baseline mismatch."
    }
    return $records[1..$Count]
}
function Read-Historical {
    $historic = [ordered]@{}
    $counts = @{'faults'=5; 'nfr001-standard'=10; 'time-boundaries'=4}
    foreach ($group in $historicalHashes.Keys) {
        $path = Join-Path $historicalPath "$group.jsonl"
        $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
        Assert-Stage ($hash -ceq $historicalHashes[$group]) "Historic $group raw evidence changed."
        $records = @(Get-Content -LiteralPath $path -Encoding UTF8 | Where-Object {$_} | ForEach-Object { $_ | ConvertFrom-Json })
        Assert-Stage ($records.Count -eq ($counts[$group] + 2) -and $records[0].group -ceq $group -and
                      $records[-1].cleanup -eq $true) "Historic $group evidence count or cleanup differs."
        $historic[$group] = [ordered]@{path=$path;sha256=$hash;records=$counts[$group]}
    }
    return $historic
}
$lease = $null
$checkedBaseline = $false
try {
    $lease = [IO.File]::Open((Join-Path $PSScriptRoot '.story-2-1-remediation.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
    $head = @(git -C $repo rev-parse HEAD)
    Assert-Stage ($LASTEXITCODE -eq 0 -and $head.Count -eq 1 -and $head[0] -ceq 'e196aba098771a31eb203be4270b460d5e0aab42') 'Unexpected Git baseline.'
    Save-Source 'before'
    $historic = Read-Historical
    $summary.reusedHistorical = [ordered]@{'time-boundaries'=$historic['time-boundaries']}
    if (-not $RecheckConcurrencyAndFaults) {
        $summary.reusedHistorical['faults'] = $historic['faults']
        $summary.reusedHistorical['nfr001-standard'] = $historic['nfr001-standard']
    }
    [IO.File]::WriteAllText((Join-Path $out 'historical-evidence.json'),($summary.reusedHistorical | ConvertTo-Json -Depth 5),$utf8)
    Stage 'historical-evidence-integrity' 'confirmed=true'
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
        Assert-Stage (@($pre | Where-Object {$_ -ceq 'STORY21_PREFLIGHT_OK'}).Count -eq 1) 'Isolated preflight failed.'
        Stage 'preflight' 'exit=0'
    } catch {
        Stage 'preflight' 'exit=1'
        throw
    }
    Probe 'baseline' 'before-db'
    $checkedBaseline = $true
    $null = Run-Python 'check' @('manage.py','check') 'System check identified no issues (0 silenced).'
    $null = Run-Python 'migration-drift' @('manage.py','makemigrations','--check','--dry-run') 'No changes detected'
    $summary.regression = Regression -Name 'regression' -Labels @() -Count 91
    $env:PYTHONPATH = $review
    try { $summary.navigation = Regression -Name 'navigation' -Labels @('review_navigation') -Count 1 }
    finally { Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue }
    $browser = Probe 'browser-correction' 'browser-correction' 1
    Assert-Stage ($browser.case -ceq 'P01-chrome-correction' -and
        (($browser.documents | ForEach-Object {$_.status}) -join ',') -ceq '200,200,400,201,200' -and
        $browser.corrected_validity.valid -eq $true -and $browser.corrected_validity.buttonNoValidate -eq $false) 'Missing real Chrome correction evidence.'
    $summary.browserCorrection = 1
    $permissions = @(Probe 'permissions' 'permissions' 22)
    $denied = @($permissions | Where-Object { $_.case -ceq 'foreign-result-same-role' })
    $permissionTotal = @($permissions | Where-Object { $_.PSObject.Properties.Name -contains 'denied' })
    Assert-Stage ($permissionTotal.Count -eq 1 -and $permissionTotal[0].denied -eq 13 -and $permissionTotal[0].missing_control -eq 2 -and
        $denied.Count -eq 1 -and (($denied[0].responses | ForEach-Object {$_.response.status}) -join ',') -ceq '404,404' -and
        @($denied[0].fingerprints | Sort-Object -Unique).Count -eq 1) 'Current same-role evidence or permission denominator mismatch.'
    $summary.permissionDenials = $permissionTotal[0].denied
    $interleavings = @(Probe 'interleavings' 'interleavings' 15)
    $want = @{I1=1; I2=2; I3=2; I4=2; I5=3; I6=4; I7=1}
    foreach ($id in $want.Keys) {
        Assert-Stage (@($interleavings | Where-Object {$_.case -ceq $id}).Count -eq $want[$id]) "Wrong interleaving case count for $id."
    }
    $i7 = $interleavings | Where-Object {$_.case -ceq 'I7'}
    Assert-Stage ($i7.candidates.same_owner_added.applicant_id -eq $i7.candidates.target.applicant_id -and
        $i7.candidates.other_owner_added.applicant_id -ne $i7.candidates.target.applicant_id -and
        $i7.blockers -contains $i7.blocker_pid -and @($i7.after.history).Count -eq 1) 'Missing I7 same-owner or real lock evidence.'
    $summary.interleavings = $interleavings.Count
    if ($RecheckConcurrencyAndFaults) {
        $faults = @(Probe 'faults' 'faults' 5)
        Assert-Stage ((($faults | ForEach-Object {$_.case}) -join ',') -ceq 'F1-history,F1-reservation,F2,F3,F4') 'Fault denominator mismatch.'
        $summary.faults = $faults.Count
        $rounds = @(Probe 'nfr001-standard' 'nfr001-standard' 10)
        # Independently freeze the conflict message with an ASCII representation for Windows PowerShell.
        $conflictMessage = -join [char[]]@(25152,36873,26102,27573,19982,26377,25928,39044,32422,20914,31361,65292,35831,36873,25321,20854,20182,26102,27573,12290)
        $summary.nfr001 = @(for ($i=0; $i -lt 10; $i++) {
            $round = $rounds[$i]
            $successful = @($round.responses | Where-Object { $_.response.status -eq 201 })
            $conflicts = @($round.responses | Where-Object { $_.response.status -eq 409 -and $_.response.body.Contains($conflictMessage) })
            $pids = @($round.responses | ForEach-Object { $_.server.pid } | Sort-Object -Unique)
            Assert-Stage ($round.round -eq ($i+1) -and @($round.responses).Count -eq 20 -and $successful.Count -eq 1 -and
                $conflicts.Count -eq 19 -and $round.counts.conflict -eq 19 -and $pids.Count -eq 20 -and
                @($round.observed_overlaps).Count -gt 0 -and @($round.after.rows).Count -eq 1 -and
                @($round.after.effective).Count -eq 1 -and $round.after.effective[0].status -ceq 'pending') "NFR round $($i+1) does not meet the standard gate."
            [ordered]@{round=$round.round; responses=20; successes=$successful.Count; conflicts=$conflicts.Count; backendPids=$pids.Count}
        })
    }
} catch {
    [IO.File]::WriteAllText((Join-Path $out 'failure.txt'),($_ | Out-String),$utf8)
    throw
} finally {
    try {
        if ($checkedBaseline) { Probe 'baseline' 'after-db' }
    } finally {
        try {
            if (Test-Path -LiteralPath (Join-Path $out 'before.sha256')) {
                Save-Source 'after'
                Assert-Stage ((Get-FileHash -LiteralPath (Join-Path $out 'before.sha256')).Hash -ceq
                    (Get-FileHash -LiteralPath (Join-Path $out 'after.sha256')).Hash) 'Source changed during the verification run.'
                $null = Read-Historical
            }
        } finally {
            foreach ($name in $vars) { [Environment]::SetEnvironmentVariable($name,$old[$name],'Process') }
            if ($lease) { $lease.Dispose() }
        }
    }
}
[IO.File]::WriteAllText((Join-Path $out 'summary.json'),($summary | ConvertTo-Json -Depth 10),$utf8)
Stage 'remediation-complete' 'exit=0'
Write-Output "STORY21_REMEDIATION_OK $out"
