param([switch]$RemediationOnly)

$ErrorActionPreference = 'Stop'
$root = 'F:\softwork\SE-Management\bmad-lab-booking-system'
$artifacts = Join-Path $root '_bmad-output\implementation-artifacts'
$python = Join-Path $root '.venv\Scripts\python.exe'
$shell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$psql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe'
$chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
$passfile = if ($env:PGPASSFILE) { $env:PGPASSFILE } else { Join-Path $env:LOCALAPPDATA 'LabBooking\PostgreSQL17\pgpass.conf' }
. (Join-Path $artifacts 'story-2-5-review-support\w01-log-contract.ps1')
Set-W01WireEncoding
$out = (New-Item -ItemType Directory -Path (Join-Path $artifacts ('story-2-8-run-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff')))).FullName
Write-Host "Story 2.8 evidence directory: $out"

function Get-Story28Source {
    foreach ($path in @('audit/services.py','reservations/forms.py','reservations/services.py','reservations/urls.py',
        'reservations/views.py','reservations/templates/reservations/admin_cancel.html',
        'reservations/templates/reservations/admin_detail.html','reservations/templates/reservations/admin_list.html',
        'reservations/test_admin_cancellation.py','reservations/management/commands/verify_admin_cancellation.py',
        'lab_booking/test_runner.py','lab_booking/database_config.py','lab_booking/settings.py',
        '_bmad-output/implementation-artifacts/spec-2-8-admin-cancellation.md',
        '_bmad-output/implementation-artifacts/run-story-2-8-isolated.ps1')) {
        "$((Get-FileHash -LiteralPath (Join-Path $root $path)).Hash)  $path"
    }
}

function Invoke-Story28Stage($Name, $File, [string[]]$Argv, $Marker) {
    $stdout = Join-Path $out "$Name.stdout.txt"
    $stderr = Join-Path $out "$Name.stderr.txt"
    [ordered]@{ executable=$File; argv=$Argv; cwd=$root } | ConvertTo-Json -Depth 3 |
        Set-Content -LiteralPath (Join-Path $out "$Name.command.json") -Encoding UTF8
    $process = Start-W01Redirected $File $root $Argv $stdout $stderr
    Write-W01NativeReceipt (Join-Path $out "$Name.receipt.json") $stdout $stderr $process.ExitCode 'Utf8' 'Utf8_or_raw_native'
    if ($process.ExitCode -ne 0) { throw "$Name exited $($process.ExitCode). See $stdout and $stderr" }
    $lines = @(Read-W01Lines $stdout)
    if ($Marker) { Assert-W01Marker $lines $process.ExitCode $Marker }
}

$leases = @()
try {
    $sourceBefore = @(Get-Story28Source) -join "`n"
    $sourceBefore | Set-Content -LiteralPath (Join-Path $out 'source-before.sha256') -Encoding UTF8
    foreach ($id in @('story28','story24','story25','story23','story22')) {
        $path = Join-Path ([IO.Path]::GetTempPath()) "LabBooking-test-127.0.0.1-5433-$id.lock"
        $leases += [IO.File]::Open($path, 'OpenOrCreate', 'ReadWrite', 'None')
    }
    foreach ($name in @('.story-2-1-remediation.lock','story-2-1-targeted-independent-recheck/.d041-release.lock')) {
        $path = Join-Path $artifacts $name
        if (Test-Path -LiteralPath $path -PathType Leaf) { $leases += [IO.File]::Open($path, 'Open', 'Read', 'None') }
    }
    $env:PYTHONUTF8 = '1'
    $env:PYTHONIOENCODING = 'utf-8'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    Invoke-Story28Stage 'preflight' $shell @('-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $artifacts 'preflight-story-2-1.ps1'),'-ProbeIsolatedDatabase','-Passfile',$passfile,'-Psql',$psql,'-Chrome',$chrome) 'STORY21_PREFLIGHT_OK'
    $env:PGPASSFILE = $passfile
    $env:LAB_BOOKING_DB_MODE = 'test'
    $env:DJANGO_SETTINGS_MODULE = 'lab_booking.settings'
    $env:LAB_BOOKING_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
    $before = Join-Path $out 'baseline-before.json'
    $after = Join-Path $out 'baseline-after.json'
    $probe = Join-Path $out 'probe.jsonl'
    Invoke-Story28Stage 'baseline-before' $python @('manage.py','verify_admin_reservations','--baseline-only','--evidence',$before) 'STORY25_BASELINE_OK'
    try {
        $testArgs = @('manage.py','test','--keepdb','--parallel','1','-v','2')
        $probeArgs = @('manage.py','verify_admin_cancellation','--evidence',$probe)
        if ($RemediationOnly) {
            $testArgs += 'reservations.test_admin_cancellation.AdminCancellationTests.test_malformed_submissions_and_methods_do_not_expire_target'
            $probeArgs += '--remediation-only'
            $testCount = $newCount = 1
            $maxSkips = 0
            $probeCount = 2
            $probeMarker = 'STORY28_PROBE_OK cases=2'
        } else {
            Invoke-Story28Stage 'check' $python @('manage.py','check') 'System check identified no issues (0 silenced).'
            Invoke-Story28Stage 'migration-drift' $python @('manage.py','makemigrations','--check','--dry-run') 'No changes detected'
            $testCount = 159
            $newCount = 9
            $maxSkips = 1
            $probeCount = 36
            $probeMarker = 'STORY28_PROBE_OK cases=36 (F4 simulates confirmation loss after real COMMIT)'
        }
        Invoke-Story28Stage 'regression' $python $testArgs
        $stdout = @(Read-W01Lines (Join-Path $out 'regression.stdout.txt'))
        $testLog = @(Read-W01Lines (Join-Path $out 'regression.stderr.txt'))
        $new = @($testLog | Where-Object { $_ -cmatch '^test_\w+ \(reservations\.test_admin_cancellation\.AdminCancellationTests\.test_\w+\) \.\.\. ok$' })
        $skips = @($testLog | Where-Object { $_ -cmatch '\.\.\. skipped ' })
        if ($stdout -cnotcontains "Found $testCount test(s)." -or -not ($testLog -cmatch "^Ran $testCount tests? in ") -or
            $new.Count -ne $newCount -or $skips.Count -gt $maxSkips -or
            ($skips.Count -eq 1 -and $skips[0] -cnotmatch 'Set LAB_BOOKING_R1_CHROME to opt in')) {
            throw 'Unexpected Django test denominator, new test outcomes, or skip.'
        }
        "discovered=$testCount passed=$(($testCount - $skips.Count)) skipped=$($skips.Count) story28_passed=$($new.Count)" |
            Set-Content -LiteralPath (Join-Path $out 'regression-counts.txt') -Encoding UTF8
        Invoke-Story28Stage 'probe' $python $probeArgs $probeMarker
        $records = @(Read-W01Lines $probe | ForEach-Object { ConvertFrom-Json $_ })
        $ownerCases = @($records | Where-Object { $_.case -cmatch '^owner-cancel-' } | ForEach-Object { $_.case })
        if ($records.Count -ne ($probeCount + 2) -or -not $records[-1].cleanup -or
            ($ownerCases -join '|') -cne 'owner-cancel-admin-first|owner-cancel-owner-first' -or
            ($records[0].database[0..8] -join '|') -cne 'test_lab_booking|lab_booking_test|lab_booking_test|127.0.0.1|5433|170012|read committed|False|False') {
            throw 'Probe identity, case count, or cleanup evidence mismatch.'
        }
    } finally {
        Invoke-Story28Stage 'baseline-after' $python @('manage.py','verify_admin_reservations','--baseline-only','--evidence',$after) 'STORY25_BASELINE_OK'
        if ((Get-FileHash -LiteralPath $before).Hash -cne (Get-FileHash -LiteralPath $after).Hash) { throw 'Isolated database baseline changed.' }
    }
    $sourceAfter = @(Get-Story28Source) -join "`n"
    $sourceAfter | Set-Content -LiteralPath (Join-Path $out 'source-after.sha256') -Encoding UTF8
    if ($sourceBefore -cne $sourceAfter) { throw 'Verification inputs changed during the batch.' }
    $outcome = if ($RemediationOnly) { 'STORY28_REMEDIATION_BATCH_OK' } else { 'STORY28_ISOLATED_BATCH_OK' }
    $outcome | Set-Content -LiteralPath (Join-Path $out 'outcome.txt') -Encoding UTF8
    Write-Host $outcome
} finally {
    foreach ($lease in $leases) { $lease.Dispose() }
    Get-ChildItem -LiteralPath $out -File | Sort-Object Name | ForEach-Object {
        "$((Get-FileHash -LiteralPath $_.FullName).Hash)  $($_.Name)"
    } | Set-Content -LiteralPath (Join-Path $out 'archive.sha256') -Encoding UTF8
}
