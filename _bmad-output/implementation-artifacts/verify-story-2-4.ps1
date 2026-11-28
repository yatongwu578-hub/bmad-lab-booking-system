[CmdletBinding()]
param(
    [string]$Passfile,
    [string]$Chrome,
    [string]$Psql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe',
    [string]$OutputRoot = $PSScriptRoot,
    [switch]$M01Only
)

# Run in ordinary Windows PowerShell on the original environment.
$ErrorActionPreference = 'Stop'
$storyRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$storyPython = Join-Path $storyRoot '.venv/Scripts/python.exe'
$storyPreflight = Join-Path $PSScriptRoot 'preflight-story-2-1.ps1'
. (Join-Path $PSScriptRoot 'story-2-5-review-support/w01-log-contract.ps1')
$storyLedger = Join-Path $PSScriptRoot 'story-2-4-legacy-125-ledger.bin'
$storyLedgerHash = 'F5C1F361C28EA77BD5AF2D9D0A0559FCBE8C00833FB50934551D4279D5B39928'
$storyNew = @(
    'test_legal_cancellation_retains_record_and_history_and_releases_slot',
    'test_locked_status_and_exact_start_boundary',
    'test_elapsed_pending_expiry_is_target_only_and_repeat_does_not_write',
    'test_confirmation_is_read_only_and_exposes_actions_only_for_candidates',
    'test_request_guards_and_same_shape_missing_responses',
    'test_csrf_and_expiry_and_retry_feedback',
    'test_stale_account_stops_before_business_query',
    'test_database_failure_responses_have_no_success_or_replay',
    'test_m01_rejects_non_native_or_incomplete_forms_before_business_queries',
    'test_m01_native_confirmation_form_cancels_with_django_csrf'
) | ForEach-Object { "reservations.test_own_cancellation.OwnCancellationTests.$_" }
$storyM01Tests = @($storyNew | Where-Object {
    $_ -cmatch '\.(test_m01_.+|test_request_guards_and_same_shape_missing_responses|test_csrf_and_expiry_and_retry_feedback|test_database_failure_responses_have_no_success_or_replay)$'
})
if ($storyM01Tests.Count -ne 5) { throw 'M01 test selection does not match the expected five tests.' }
$storyCases = @('A01-A05','A06','P01-P07-V01','P08-off','P08-role','I01','I02','I03',
    'I04','I05','I06','I07','I08','I09','A08','V01-M01','Chrome')
if ($M01Only) { $storyCases = @('V01-M01','Chrome') }
$storyRun = Join-Path (Resolve-Path -LiteralPath $OutputRoot).Path (
    'story-2-4-run-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + [guid]::NewGuid().ToString('N'))
$storyOut = (New-Item -ItemType Directory -Path $storyRun).FullName
Write-Host "Story 2.4 evidence: $storyOut"
if (-not $Passfile) { $Passfile = $env:PGPASSFILE }
if (-not $Passfile) { $Passfile = Join-Path $env:LOCALAPPDATA 'LabBooking/PostgreSQL17/pgpass.conf' }
if (-not $Chrome) { $Chrome = $env:LAB_BOOKING_R1_CHROME }
if (-not $Chrome) { $Chrome = Join-Path $env:ProgramFiles 'Google/Chrome/Application/chrome.exe' }

function Save-Story24Hashes([string]$Phase) {
    $rel = @('manage.py','requirements.txt','_bmad-output/planning-artifacts/epics.md')
    $art = '_bmad-output/implementation-artifacts'
    $rel += @('spec-2-4-cancel-own-reservation.md','story-2-4-checkpoint-1.md','verify-story-2-4.ps1',
        'story-2-4-legacy-125-ledger.bin','preflight-story-2-1.ps1','story-2-5-review-support/w01-log-contract.ps1') |
        ForEach-Object { "$art/$_" }
    foreach ($dir in @('accounts','equipment','lab_booking','audit','reservations')) {
        $rel += Get-ChildItem -LiteralPath (Join-Path $storyRoot $dir) -File -Recurse |
            Where-Object { $_.Extension -in '.py', '.html' } |
            ForEach-Object { $_.FullName.Substring($storyRoot.Length + 1).Replace('\','/') }
    }
    $rel | Sort-Object -Unique | ForEach-Object {
        "$((Get-FileHash -LiteralPath (Join-Path $storyRoot $_) -Algorithm SHA256).Hash)  $_"
    } | Set-Content -LiteralPath (Join-Path $storyOut "$Phase.sha256") -Encoding UTF8
}

function Invoke-Story24Stage([string]$Stage,[string]$File,[string[]]$Argv,[string]$Marker,
    [string]$Protocol = 'Utf8',[string]$DisplayCommand) {
    $stdout = Join-Path $storyOut "$Stage.stdout.txt"
    $stderr = Join-Path $storyOut "$Stage.stderr.txt"
    if (-not $DisplayCommand) { $DisplayCommand = $File + ' ' + (($Argv | ForEach-Object { '"' + $_ + '"' }) -join ' ') }
    $DisplayCommand | Set-Content -LiteralPath (Join-Path $storyOut "$Stage.command.txt") -Encoding UTF8
    $native = Start-W01Redirected -File $File -WorkingDirectory $storyRoot -Argv $Argv -Stdout $stdout -Stderr $stderr
    $code = $native.ExitCode
    $native.Dispose()
    $errProfile = if ($Protocol -eq 'Ascii') { 'NativeDiagnostic' } else { 'Utf8' }
    $receipt = Join-Path $storyOut "$Stage.native.json"
    Write-W01NativeReceipt $receipt $stdout $stderr $code $Protocol $errProfile
    "$(Get-Date -Format o) $Stage exit=$code" | Add-Content -LiteralPath (Join-Path $storyOut 'stages.txt') -Encoding UTF8
    if ($code -ne 0) { throw "Story 2.4 stage $Stage exited $code. Raw logs: $storyOut" }
    $lines = @(Read-W01Lines $stdout $Protocol)
    if ($Protocol -eq 'Utf8') { $lines += @(Read-W01Lines $stderr) }
    Assert-W01Marker -Lines $lines -ExitCode $code -Marker $Marker
    $lines
}

function Read-Story24Baseline([string]$Stage) {
    $evidence = Join-Path $storyOut "$Stage.json"
    $null = Invoke-Story24Stage $Stage $storyPython @('manage.py','verify_admin_reservations','--baseline-only',
        '--evidence',$evidence) 'STORY25_BASELINE_OK'
    (Get-FileHash -LiteralPath $evidence -Algorithm SHA256).Hash
}

$storyEnvs = @('LAB_BOOKING_DB_MODE','LAB_BOOKING_R1_CHROME','LAB_BOOKING_SECRET_KEY',
    'DJANGO_SETTINGS_MODULE','PGPASSFILE','PYTHONIOENCODING','PYTHONDONTWRITEBYTECODE','PYTHONUTF8')
$storyOldEnv = @{}
foreach ($name in $storyEnvs) { $storyOldEnv[$name] = [Environment]::GetEnvironmentVariable($name,'Process') }
$storyHandles = @()
$storyBefore = $null
$storyFailure = $null
try {
    Save-Story24Hashes 'before'
    if ((Get-FileHash -LiteralPath $storyLedger -Algorithm SHA256).Hash -cne $storyLedgerHash) {
        throw 'Historical 125-test ledger does not match the verified SHA-256.'
    }
    $legacyCopy = Join-Path $storyOut 'legacy-125-passed-tests.txt'
    Copy-Item -LiteralPath $storyLedger -Destination $legacyCopy
    $legacy = @(Read-W01Lines $legacyCopy)
    if ($legacy.Count -ne 125 -or @($legacy | Sort-Object -Unique).Count -ne 125) {
        throw 'Historical test ledger must have 125 distinct full names.'
    }
    $leases = @('story24','story25','story23','story22') | ForEach-Object {
        Join-Path ([IO.Path]::GetTempPath()) "LabBooking-test-127.0.0.1-5433-$_.lock"
    }
    foreach ($lease in $leases) {
        $storyHandles += [IO.File]::Open($lease,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
    }
    foreach ($oldLease in @('.story-2-1-remediation.lock','story-2-1-targeted-independent-recheck/.d041-release.lock')) {
        $lease = Join-Path $PSScriptRoot $oldLease
        if (Test-Path -LiteralPath $lease -PathType Leaf) {
            $storyHandles += [IO.File]::Open($lease,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::None)
        }
    }
    $shell = Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe'
    $preflightArgs = @{
        Stage = 'preflight'
        File = $shell
        Argv = @('-NoProfile','-File',$storyPreflight,'-ProbeIsolatedDatabase','-Passfile',$Passfile,'-Chrome',$Chrome,'-Psql',$Psql)
        Marker = 'STORY21_PREFLIGHT_OK'
        Protocol = 'Ascii'
        DisplayCommand = 'powershell.exe -NoProfile -File preflight-story-2-1.ps1 -ProbeIsolatedDatabase (local paths omitted)'
    }
    $null = Invoke-Story24Stage @preflightArgs

    $env:PGPASSFILE = $Passfile
    $env:LAB_BOOKING_R1_CHROME = $Chrome
    $env:LAB_BOOKING_DB_MODE = 'test'
    $env:DJANGO_SETTINGS_MODULE = 'lab_booking.settings'
    $env:PYTHONIOENCODING = 'utf-8'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:PYTHONUTF8 = '1'
    $env:LAB_BOOKING_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')

    $storyBefore = Read-Story24Baseline 'baseline-before'
    $null = Invoke-Story24Stage 'check' $storyPython @('manage.py','check') 'System check identified no issues (0 silenced).'
    $null = Invoke-Story24Stage 'migration-drift' $storyPython @('manage.py','makemigrations','--check','--dry-run') 'No changes detected'
    $testStage = if ($M01Only) { 'm01-targeted' } else { 'regression' }
    $testArgs = @('manage.py','test','--keepdb','--parallel','1','-v','2')
    if ($M01Only) { $testArgs += $storyM01Tests }
    $lines = @(Invoke-Story24Stage $testStage $storyPython $testArgs 'OK')
    $passed = @(foreach ($line in $lines) {
        if ($line -cmatch '^test_\w+ \(([a-zA-Z_][a-zA-Z0-9_.]+)\) \.\.\. ok$') { $Matches[1] }
    })
    $expected = if ($M01Only) { $storyM01Tests } else { $legacy + $storyNew }
    $total = $expected.Count
    $missing = @($expected | Where-Object { $_ -cnotin $passed })
    $unexpected = @($passed | Where-Object { $_ -cnotin $expected })
    $skipped = @($lines | Where-Object { $_ -cmatch '\.{3} skipped ' })
    $passed | Set-Content -LiteralPath (Join-Path $storyOut 'passed-tests.txt') -Encoding UTF8
    $denominator = if ($M01Only) { "targeted=$total" } else { "legacy=$($legacy.Count) added=$($storyNew.Count)" }
    "$denominator passed=$($passed.Count) missing=$($missing.Count) unexpected=$($unexpected.Count) skipped=$($skipped.Count)" |
        Set-Content -LiteralPath (Join-Path $storyOut "$testStage-counts.txt") -Encoding UTF8
    if ($passed.Count -ne $total -or @($passed | Sort-Object -Unique).Count -ne $total -or
        $missing.Count -or $unexpected.Count -or $skipped.Count -or
        @($lines | Where-Object { $_ -ceq "Found $total test(s)." }).Count -ne 1 -or
        @($lines | Where-Object { $_ -cmatch "^Ran $total tests in " }).Count -ne 1) {
        throw 'Actual test names, denominator or skip count do not match the expected ledger.'
    }
    if ((Read-Story24Baseline "baseline-after-$testStage") -cne $storyBefore) { throw 'Django tests changed the isolated database baseline.' }

    $probe = Join-Path $storyOut 'independent.jsonl'
    $probeArgs = @('manage.py','verify_own_cancellation','--evidence',$probe)
    if ($M01Only) { $probeArgs += '--m01-only' }
    $null = Invoke-Story24Stage 'independent' $storyPython $probeArgs "STORY24_PROBE_OK cases=$($storyCases.Count)"
    $records = @(Read-W01Lines $probe | ForEach-Object { ConvertFrom-Json $_ })
    $actual = @($records | Where-Object { $_.case } | ForEach-Object { $_.case })
    if (($actual -join '|') -cne ($storyCases -join '|') -or $records.Count -ne ($storyCases.Count + 2) -or
        ($records[0].database[0..8] -join '|') -cne 'test_lab_booking|lab_booking_test|lab_booking_test|127.0.0.1|5433|170012|read committed|False|False' -or
        -not $records[-1].cleanup) {
        throw 'Independent probes did not provide the expected cases, isolated identity and verified cleanup.'
    }
    $browser = @($records | Where-Object { $_.case -ceq 'Chrome' })[0]
    $m01 = @($records | Where-Object { $_.case -ceq 'V01-M01' })[0]
    if (($m01.runs.state -join '|') -cne 'future|due' -or @($browser.results).Count -ne 2) {
        throw 'M01 fixture or browser records are incomplete.'
    }
    foreach ($run in $m01.runs) {
        $legalCode = if ($run.state -ceq 'future') { 200 } else { 409 }
        if (@($run.invalid | Where-Object { $_.result.response.status -eq 400 }).Count -ne 10 -or @($run.invalid).Count -ne 10 -or
            @($run.csrf_denied | Where-Object { $_.result.response.status -eq 403 }).Count -ne 2 -or @($run.csrf_denied).Count -ne 2 -or
            $run.legal.response.status -ne $legalCode -or $run.repeat.response.status -ne 409) {
            throw 'Missing M01 rejection, legitimate outcome or repeat-control evidence.'
        }
    }
    'invalid=20 csrf_denied=4 legal=2 repeat=2 chrome_roles=2' |
        Set-Content -LiteralPath (Join-Path $storyOut 'm01-counts.txt') -Encoding UTF8
    if (-not $M01Only) {
        $permissions = @($records | Where-Object { $_.case -ceq 'P01-P07-V01' })[0]
        $fault = @($records | Where-Object { $_.case -ceq 'A08' })[0]
        if ($permissions.rejected_count -ne 14 -or @($permissions.denied).Count -ne 14 -or
            @($permissions.invalid).Count -ne 12 -or @($permissions.missing).Count -ne 6 -or @($fault.cases).Count -ne 10) {
            throw 'Independent permissions or failure records are incomplete.'
        }
        $revoked = @($records | Where-Object { $_.case -cin @('P08-off','P08-role') })
        if ($revoked.Count -ne 2 -or @($revoked | Where-Object { $_.result.response.status -eq 403 -and $_.blockers.Count -ge 1 }).Count -ne 2) {
            throw 'Independent revocation coverage is incomplete.'
        }
        "denied=$($permissions.denied.Count + $revoked.Count) invalid=$($permissions.invalid.Count) missing_controls=$($permissions.missing.Count)" |
            Set-Content -LiteralPath (Join-Path $storyOut 'permissions-counts.txt') -Encoding UTF8
    }
    foreach ($result in $browser.results) {
        if (@($result.screenshots).Count -ne 2 -or $result.confirmation.enctype -cne 'application/x-www-form-urlencoded') {
            throw 'Chrome did not confirm native URL encoding and archive both screens.'
        }
        foreach ($name in $result.screenshots) {
            if ($name -cnotmatch '^chrome-(student|teacher)-(confirm|result)\.png$' -or
                -not (Test-Path -LiteralPath (Join-Path $storyOut $name) -PathType Leaf)) { throw 'Missing Chrome screenshot.' }
        }
    }
    if ((Read-Story24Baseline 'baseline-after-independent') -cne $storyBefore) { throw 'Independent verification changed the isolated database baseline.' }
} catch {
    $storyFailure = $_
    $storyFailure | Out-String | Set-Content -LiteralPath (Join-Path $storyOut 'failure.txt') -Encoding UTF8
    if ($storyBefore) {
        try {
            $hash = Read-Story24Baseline 'baseline-after-failure'
            "unchanged=$($hash -ceq $storyBefore) before=$storyBefore after=$hash" |
                Set-Content -LiteralPath (Join-Path $storyOut 'failure-readback.txt') -Encoding UTF8
        } catch {
            $_ | Out-String | Set-Content -LiteralPath (Join-Path $storyOut 'failure-readback.txt') -Encoding UTF8
        }
    }
    throw $storyFailure
} finally {
    try {
        $beforeHashes = Join-Path $storyOut 'before.sha256'
        if (Test-Path -LiteralPath $beforeHashes -PathType Leaf) {
            Save-Story24Hashes 'after'
            if ((Get-FileHash -LiteralPath $beforeHashes).Hash -cne (Get-FileHash -LiteralPath (Join-Path $storyOut 'after.sha256')).Hash) {
                throw 'Implementation or verification source changed during the run.'
            }
        }
    } catch {
        $_ | Out-String | Set-Content -LiteralPath (Join-Path $storyOut 'source-hash-failure.txt') -Encoding UTF8
        if (-not $storyFailure) { throw }
    } finally {
        foreach ($handle in $storyHandles) { $handle.Dispose() }
        foreach ($name in $storyEnvs) { [Environment]::SetEnvironmentVariable($name,$storyOldEnv[$name],'Process') }
    }
}
$success = if ($M01Only) { 'STORY24_M01_DEV_OK' } else { 'STORY24_VERIFICATION_OK' }
$success | Set-Content -LiteralPath (Join-Path $storyOut 'batch-marker.txt') -Encoding UTF8
Write-Output $success
