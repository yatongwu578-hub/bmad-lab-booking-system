[CmdletBinding()]
param(
    [string]$Passfile,
    [string]$Chrome,
    [string]$Psql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe',
    [string]$OutputRoot,
    [switch]$Remediation,
    [switch]$M01Only
)

# Run from ordinary Windows PowerShell after applying all Story 2.5 changes.
# Uses only the existing test database; no production connection, grants, migrations or flush.
$ErrorActionPreference = 'Stop'
$storyRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$storyPython = Join-Path $storyRoot '.venv/Scripts/python.exe'
$storyPreflight = Join-Path $PSScriptRoot 'preflight-story-2-1.ps1'
if ($Remediation -and $M01Only) { throw 'Choose either -Remediation or -M01Only.' }
if (-not $OutputRoot) { $OutputRoot = $PSScriptRoot }
$storyLedger = '_bmad-output/implementation-artifacts/story-2-3-run-20261127-111101-492-41d9eb74/passed-tests.txt'
$storyExpectedCases = @('navigation-history','filtered-affected','ordered-locks','no-pending-clock','edge-input',
    'permissions','revoked-while-waiting','frozen-concurrent-additions','crossed-start','submit-first','query-first',
    'commit-after-end','late-projection-failed','history-second','commit-rejected','commit-disconnected','confirmation-lost')
$storyNewTests = @(
    'test_identity_navigation_uses_business_role',
    'test_full_list_keeps_five_states_with_dual_status_and_persisted_reason',
    'test_filter_uses_exact_code_and_single_time_across_start_and_end_boundaries',
    'test_empty_invalid_and_absent_results_do_not_fall_back_or_write',
    'test_detail_keeps_history_order_actor_identity_and_validated_navigation',
    'test_due_detail_expires_once_with_persisted_system_reason',
    'test_list_locks_only_pending_device_ids_once_in_sorted_order',
    'test_approved_only_filter_has_clock_but_no_lock',
    'test_unauthorized_requests_never_touch_business_tables',
    'test_stale_effective_role_is_rejected_before_business_scope',
    'test_late_history_projection_failure_rolls_back_expiry',
    'test_unknown_and_confirmed_failures_have_distinct_unsuccessful_pages'
) | ForEach-Object { 'reservations.test_admin_reservations.AdminReservationTests.' + $_ }
$storyTargetTests = @(
    'reservations.test_own_reservations.OwnReservationsTests.test_ac1_role_navigation_and_actual_201_contract',
    'reservations.test_own_reservations.OwnReservationsTests.test_ac6_unauthorized_and_tampered_requests_never_touch_foreign_rows',
    'reservations.test_admin_reservations.AdminReservationTests.test_identity_navigation_uses_business_role',
    'equipment.test_create_navigation.EquipmentCreateNavigationTests.test_active_admin_can_follow_create_link_from_identity_and_catalog',
    'equipment.test_edit.EquipmentEditTests.test_service_enforces_active_admin_and_allowlist_before_database_access'
)
if ($M01Only) {
    $storyTargetTests = @(
        'reservations.test_admin_reservations.AdminReservationTests.test_detail_keeps_history_order_actor_identity_and_validated_navigation',
        'reservations.test_admin_reservations.AdminReservationTests.test_due_detail_expires_once_with_persisted_system_reason',
        'reservations.test_admin_reservations.AdminReservationTests.test_unauthorized_requests_never_touch_business_tables'
    )
    $storyExpectedCases = @('m01-detail')
}
$storyRun = Join-Path $OutputRoot ("story-2-5-run-" + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') +
    '-' + [guid]::NewGuid().ToString('N'))
$storyOut = (New-Item -ItemType Directory -Path $storyRun).FullName
Write-Host "Story 2.5 evidence: $storyOut"

if (-not $Passfile) { $Passfile = $env:PGPASSFILE }
if (-not $Passfile) { $Passfile = Join-Path $env:LOCALAPPDATA 'LabBooking/PostgreSQL17/pgpass.conf' }
if (-not $Chrome) { $Chrome = $env:LAB_BOOKING_R1_CHROME }
if (-not $Chrome) { $Chrome = Join-Path $env:ProgramFiles 'Google/Chrome/Application/chrome.exe' }
$storyEnvNames = @('LAB_BOOKING_DB_MODE','LAB_BOOKING_R1_CHROME','LAB_BOOKING_SECRET_KEY',
    'DJANGO_SETTINGS_MODULE','PGPASSFILE','PYTHONIOENCODING','PYTHONDONTWRITEBYTECODE')
$storyOldEnv = @{}
foreach ($storyName in $storyEnvNames) {
    $storyOldEnv[$storyName] = [Environment]::GetEnvironmentVariable($storyName, 'Process')
}

function Save-Story25Hashes([string]$Phase) {
    $storyArtifacts = '_bmad-output/implementation-artifacts'
    $storyInputs = @('manage.py','requirements.txt','_bmad-output/planning-artifacts/epics.md',
        "$storyArtifacts/spec-2-5-admin-reservation-query.md","$storyArtifacts/story-2-5-checkpoint-1.md",
        "$storyArtifacts/preflight-story-2-1.ps1","$storyArtifacts/verify-story-2-5.ps1",$storyLedger)
    foreach ($storyDir in @('accounts','equipment','lab_booking','audit','reservations')) {
        $storyInputs += Get-ChildItem -LiteralPath (Join-Path $storyRoot $storyDir) -File -Recurse |
            Where-Object { $_.Extension -in '.py', '.html' } |
            ForEach-Object { $_.FullName.Substring($storyRoot.Length + 1).Replace('\','/') }
    }
    $storyInputs | Sort-Object -Unique | ForEach-Object {
        $storyHash = Get-FileHash -LiteralPath (Join-Path $storyRoot $_) -Algorithm SHA256
        "$($storyHash.Hash)  $_"
    } | Set-Content -LiteralPath (Join-Path $storyOut "$Phase.sha256") -Encoding UTF8
}

function Write-Story25Stage([string]$Stage, [int]$Code) {
    "$(Get-Date -Format o) $Stage exit=$Code" | Add-Content -LiteralPath (Join-Path $storyOut 'stages.txt') -Encoding UTF8
    if ($Code -ne 0) { throw "Stage $Stage exited $Code. See $storyOut." }
}

function Invoke-Story25Python([string]$Stage, [string[]]$Arguments, [string]$Marker) {
    $storyStdout = Join-Path $storyOut "$Stage.stdout.txt"
    $storyStderr = Join-Path $storyOut "$Stage.stderr.txt"
    ('.venv/Scripts/python.exe ' + ($Arguments -join ' ')) |
        Set-Content -LiteralPath (Join-Path $storyOut "$Stage.command.txt") -Encoding UTF8
    $storyResult = Start-Process -FilePath $storyPython -WorkingDirectory $storyRoot -WindowStyle Hidden -Wait -PassThru `
        -ArgumentList (($Arguments | ForEach-Object { '"' + $_ + '"' }) -join ' ') `
        -RedirectStandardOutput $storyStdout -RedirectStandardError $storyStderr
    Write-Story25Stage $Stage $storyResult.ExitCode
    $storyLines = @(Get-Content -LiteralPath $storyStdout,$storyStderr -Encoding UTF8)
    if (@($storyLines | Where-Object { $_ -ceq $Marker }).Count -ne 1) {
        throw "Stage $Stage did not emit exactly one '$Marker'."
    }
    return $storyLines
}

function Get-Story25Baseline([string]$Stage) {
    $storyEvidence = Join-Path $storyOut "$Stage.json"
    $null = Invoke-Story25Python $Stage @('manage.py','verify_admin_reservations','--baseline-only',
        '--evidence',$storyEvidence) 'STORY25_BASELINE_OK'
    return (Get-FileHash -LiteralPath $storyEvidence -Algorithm SHA256).Hash
}

function Get-Story25PassedIds([string[]]$Lines) {
    foreach ($storyLine in $Lines) {
        if ($storyLine -cmatch '^test_\w+ \(([a-zA-Z_][a-zA-Z0-9_.]+)\) \.\.\. ok$') { $Matches[1] }
    }
}

$storyHeld = @()
$storyBefore = $null
$storyActiveTestStage = $null
$storyPrimaryFailure = $null
Push-Location -LiteralPath $storyRoot
try {
    Save-Story25Hashes 'before'

    # Coordinate with this verifier, and recognize already-existing older verifier leases without modifying them.
    $storyTemp = [IO.Path]::GetTempPath()
    $storyHeld += [IO.File]::Open((Join-Path $storyTemp 'LabBooking-test-127.0.0.1-5433-story25.lock'),
        [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    $storyEarlierLeases = @(
        (Join-Path $storyTemp 'LabBooking-test-127.0.0.1-5433-story23.lock'),
        (Join-Path $storyTemp 'LabBooking-test-127.0.0.1-5433-story22.lock'),
        (Join-Path $PSScriptRoot '.story-2-1-remediation.lock'),
        (Join-Path $PSScriptRoot 'story-2-1-targeted-independent-recheck/.d041-release.lock')
    )
    foreach ($storyLock in $storyEarlierLeases) {
        if (Test-Path -LiteralPath $storyLock -PathType Leaf) {
            $storyHeld += [IO.File]::Open($storyLock, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::None)
        }
    }
    Write-Story25Stage 'verification-locks' 0
    'preflight-story-2-1.ps1 -ProbeIsolatedDatabase (protected passfile omitted)' |
        Set-Content -LiteralPath (Join-Path $storyOut 'preflight.command.txt') -Encoding UTF8
    try {
        & $storyPreflight -Passfile $Passfile -Chrome $Chrome -Psql $Psql -ProbeIsolatedDatabase `
            2> (Join-Path $storyOut 'preflight.stderr.txt') |
            Tee-Object -FilePath (Join-Path $storyOut 'preflight.stdout.txt') | Write-Host
        if (@(Get-Content -LiteralPath (Join-Path $storyOut 'preflight.stdout.txt') |
                Where-Object { $_ -ceq 'STORY21_PREFLIGHT_OK' }).Count -ne 1) {
            throw 'Preflight did not confirm the isolated database identity and original Python.'
        }
    } catch {
        $_ | Out-String | Add-Content -LiteralPath (Join-Path $storyOut 'preflight.stderr.txt')
        Write-Story25Stage 'preflight' 1
    }
    Write-Story25Stage 'preflight' 0

    $env:PGPASSFILE = $Passfile
    $env:LAB_BOOKING_R1_CHROME = $Chrome
    $env:LAB_BOOKING_DB_MODE = 'test'
    $env:DJANGO_SETTINGS_MODULE = 'lab_booking.settings'
    $env:PYTHONIOENCODING = 'utf-8'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:LAB_BOOKING_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')

    $storyBefore = Get-Story25Baseline 'baseline-before'
    $null = Invoke-Story25Python 'check' @('manage.py','check') 'System check identified no issues (0 silenced).'
    $null = Invoke-Story25Python 'migration-drift' @('manage.py','makemigrations','--check','--dry-run') 'No changes detected'
    $storyTestArguments = @('manage.py','test','--keepdb','--parallel','1','-v','2')
    if ($Remediation -or $M01Only) {
        $storyActiveTestStage = 'targeted'
        $storyTargetLines = @(Invoke-Story25Python 'targeted' ($storyTestArguments + $storyTargetTests) 'OK')
        $storyTargetPassed = @(Get-Story25PassedIds $storyTargetLines)
        $storyTargetCount = $storyTargetTests.Count
        $storyTargetPassed | Set-Content -LiteralPath (Join-Path $storyOut 'targeted-passed-tests.txt') -Encoding UTF8
        if ($storyTargetPassed.Count -ne $storyTargetCount -or
            @($storyTargetPassed | Where-Object { $_ -cnotin $storyTargetTests }).Count -ne 0 -or
            @($storyTargetTests | Where-Object { $_ -cnotin $storyTargetPassed }).Count -ne 0 -or
            @($storyTargetLines | Where-Object { $_ -cmatch '\.{3} skipped ' }).Count -ne 0 -or
            @($storyTargetLines | Where-Object { $_ -ceq "Found $storyTargetCount test(s)." }).Count -ne 1 -or
            @($storyTargetLines | Where-Object { $_ -cmatch "^Ran $storyTargetCount tests in " }).Count -ne 1) {
            throw 'Targeted test identity, denominator or skip count differs. See targeted evidence.'
        }
        if ((Get-Story25Baseline 'baseline-after-targeted') -cne $storyBefore) {
            throw 'Targeted tests changed isolated schema, ACL or data.'
        }
    }
    if (-not $M01Only) {
    $storyActiveTestStage = 'regression'
    $storyTests = @(Invoke-Story25Python 'regression' $storyTestArguments 'OK')
    $storyPrior = @(Get-Content -LiteralPath $storyLedger -Encoding UTF8)
    $storyPassed = @(Get-Story25PassedIds $storyTests)
    $storyNew = @($storyPassed | Where-Object { $_ -cmatch '^reservations\.test_admin_reservations\.' })
    $storyMissing = @($storyPrior | Where-Object { $_ -cnotin $storyPassed })
    $storySkipped = @($storyTests | Where-Object { $_ -cmatch '\.{3} skipped ' })
    $storyPassed | Set-Content -LiteralPath (Join-Path $storyOut 'passed-tests.txt') -Encoding UTF8
    "legacy=$($storyPrior.Count) missing=$($storyMissing.Count) new=$($storyNew.Count) total=$($storyPassed.Count) skipped=$($storySkipped.Count)" |
        Set-Content -LiteralPath (Join-Path $storyOut 'regression-counts.txt') -Encoding UTF8
    $storyExpected = $storyPrior + $storyNewTests
    $storyUnexpected = @($storyPassed | Where-Object { $_ -cnotin $storyExpected })
    $storyMissingNew = @($storyNewTests | Where-Object { $_ -cnotin $storyNew })
    $storyTotal = $storyExpected.Count
    if ($storyPrior.Count -ne 113 -or @($storyPrior | Sort-Object -Unique).Count -ne 113 -or
        $storyMissing.Count -ne 0 -or $storyMissingNew.Count -ne 0 -or $storyUnexpected.Count -ne 0 -or
        $storyPassed.Count -ne $storyTotal -or @($storyPassed | Sort-Object -Unique).Count -ne $storyTotal -or
        $storySkipped.Count -ne 0 -or @($storyTests | Where-Object { $_ -ceq "Found $storyTotal test(s)." }).Count -ne 1 -or
        @($storyTests | Where-Object { $_ -cmatch "^Ran $storyTotal tests in " }).Count -ne 1) {
        throw 'Regression test identity, denominator or skip count differs. See regression evidence.'
    }
    if ((Get-Story25Baseline 'baseline-after-regression') -cne $storyBefore) {
        throw 'Regression changed isolated schema or data.'
    }
    }

    $storyActiveTestStage = 'independent'
    $storyEvidence = Join-Path $storyOut 'independent.jsonl'
    $storyMarker = "STORY25_PROBE_OK cases=$($storyExpectedCases.Count)"
    $storyProbeArgs = @('manage.py','verify_admin_reservations','--evidence',$storyEvidence)
    if ($M01Only) { $storyProbeArgs += '--m01-only' }
    $null = Invoke-Story25Python 'independent' $storyProbeArgs $storyMarker
    $storyRecords = @(Get-Content -LiteralPath $storyEvidence -Encoding UTF8 | ForEach-Object { ConvertFrom-Json $_ })
    $storyActualCases = @($storyRecords | Where-Object { $_.case } | ForEach-Object { $_.case })
    if (($storyActualCases -join '|') -cne ($storyExpectedCases -join '|') -or
        ($storyRecords[0].database[0..8] -join '|') -cne
            'test_lab_booking|lab_booking_test|lab_booking_test|127.0.0.1|5433|170012|read committed|False|False' -or
        -not $storyRecords[-1].cleanup -or $storyRecords.Count -ne ($storyExpectedCases.Count + 2)) {
        throw 'Probe evidence is missing an expected case, isolated identity or verified cleanup.'
    }
    $storyM01Case = if ($M01Only) { 'm01-detail' } else { 'edge-input' }
    $storyM01 = @($storyRecords | Where-Object { $_.case -ceq $storyM01Case })[0].m01
    if (-not $storyM01 -or @($storyM01.invalid).Count -ne 5 -or
        @($storyM01.invalid | Where-Object { $_.result.response.status -eq 400 }).Count -ne 5 -or
        $storyM01.legal.response.status -ne 200 -or $storyM01.repeated.response.status -ne 200) {
        throw 'M01 raw record is missing the five invalid responses or legal/repeat controls.'
    }
    if ((Get-Story25Baseline 'baseline-after-independent') -cne $storyBefore) {
        throw 'Independent probes changed isolated schema or data.'
    }
    $storyActiveTestStage = $null
} catch {
    $storyPrimaryFailure = $_
    $storyPrimaryFailure | Out-String | Add-Content -LiteralPath (Join-Path $storyOut 'failure.txt') -Encoding UTF8
    if ($storyBefore -and $storyActiveTestStage) {
        try {
            $storyAfterFailure = Get-Story25Baseline 'baseline-after-failure'
            $storyReadback = if ($storyAfterFailure -ceq $storyBefore) { 'unchanged' } else { 'changed' }
            "stage=$storyActiveTestStage baseline=$storyReadback before=$storyBefore after=$storyAfterFailure" |
                Set-Content -LiteralPath (Join-Path $storyOut 'failure-readback.txt') -Encoding UTF8
        } catch {
            "stage=$storyActiveTestStage baseline=unavailable" |
                Set-Content -LiteralPath (Join-Path $storyOut 'failure-readback.txt') -Encoding UTF8
            $_ | Out-String | Add-Content -LiteralPath (Join-Path $storyOut 'failure-readback.txt') -Encoding UTF8
        }
    }
    throw $storyPrimaryFailure
} finally {
    try {
        if (Test-Path -LiteralPath (Join-Path $storyOut 'before.sha256')) {
            Save-Story25Hashes 'after'
            if ((Get-FileHash -LiteralPath (Join-Path $storyOut 'before.sha256')).Hash -cne
                    (Get-FileHash -LiteralPath (Join-Path $storyOut 'after.sha256')).Hash) {
                throw 'Source or verification inputs changed during the run.'
            }
        }
    } catch {
        $_ | Out-String | Add-Content -LiteralPath (Join-Path $storyOut 'hash-validation-failure.txt') -Encoding UTF8
        if (-not $storyPrimaryFailure) { throw }
    } finally {
        foreach ($storyHandle in $storyHeld) { $storyHandle.Dispose() }
        foreach ($storyName in $storyEnvNames) {
            [Environment]::SetEnvironmentVariable($storyName, $storyOldEnv[$storyName], 'Process')
        }
        Pop-Location
    }
}
Write-Story25Stage 'complete' 0
$storySuccess = if ($M01Only) { 'STORY25_M01_DEV_OK' } else { 'STORY25_VERIFICATION_OK' }
$storySuccess | Set-Content -LiteralPath (Join-Path $storyOut 'batch-marker.txt') -Encoding UTF8
Write-Output $storySuccess
