[CmdletBinding()]
param(
    [string]$Passfile,
    [string]$Chrome,
    [string]$Psql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe',
    [string]$OutputRoot = $PSScriptRoot
)

# Run from ordinary Windows PowerShell after applying all Story 2.3 changes.
# Uses only the existing test database; no production connection, grants, migrations or flush.
$ErrorActionPreference = 'Stop'
$storyRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$storyPython = Join-Path $storyRoot '.venv/Scripts/python.exe'
$storyPreflight = Join-Path $PSScriptRoot 'preflight-story-2-1.ps1'
$storyLedger = '_bmad-output/implementation-artifacts/story-2-2-run-20261126-224427-552-98c04aee/regression.stderr.txt'
$storyExpectedCases = @('history-navigation','current-equipment','projected-reasons','ordered-scope',
    'no-pending','permissions','revoked-while-waiting','frozen-new-row','crossed-start',
    'submit-first','query-first','history-second','commit-rejected','commit-disconnected','confirmation-lost')
$storyRun = Join-Path $OutputRoot ("story-2-3-run-" + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') +
    '-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
$storyOut = (New-Item -ItemType Directory -Path $storyRun).FullName
Write-Host "Story 2.3 evidence: $storyOut"

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

function Save-Story23Hashes([string]$Phase) {
    $storyArtifacts = '_bmad-output/implementation-artifacts'
    $storyInputs = @('manage.py','requirements.txt','_bmad-output/planning-artifacts/epics.md',
        "$storyArtifacts/spec-2-3-query-own-reservations.md","$storyArtifacts/story-2-3-checkpoint-1.md",
        "$storyArtifacts/preflight-story-2-1.ps1","$storyArtifacts/verify-story-2-3.ps1",$storyLedger)
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

function Write-Story23Stage([string]$Stage, [int]$Code) {
    "$(Get-Date -Format o) $Stage exit=$Code" | Add-Content -LiteralPath (Join-Path $storyOut 'stages.txt') -Encoding UTF8
    if ($Code -ne 0) { throw "Stage $Stage exited $Code. See $storyOut." }
}

function Invoke-Story23Python([string]$Stage, [string[]]$Arguments, [string]$Marker) {
    $storyStdout = Join-Path $storyOut "$Stage.stdout.txt"
    $storyStderr = Join-Path $storyOut "$Stage.stderr.txt"
    ('.venv/Scripts/python.exe ' + ($Arguments -join ' ')) |
        Set-Content -LiteralPath (Join-Path $storyOut "$Stage.command.txt") -Encoding UTF8
    $storyResult = Start-Process -FilePath $storyPython -WorkingDirectory $storyRoot -WindowStyle Hidden -Wait -PassThru `
        -ArgumentList (($Arguments | ForEach-Object { '"' + $_ + '"' }) -join ' ') `
        -RedirectStandardOutput $storyStdout -RedirectStandardError $storyStderr
    Write-Story23Stage $Stage $storyResult.ExitCode
    $storyLines = @(Get-Content -LiteralPath $storyStdout,$storyStderr -Encoding UTF8)
    if (@($storyLines | Where-Object { $_ -ceq $Marker }).Count -ne 1) {
        throw "Stage $Stage did not emit exactly one '$Marker'."
    }
    return $storyLines
}

function Get-Story23Baseline([string]$Stage) {
    $storyEvidence = Join-Path $storyOut "$Stage.json"
    $null = Invoke-Story23Python $Stage @('manage.py','verify_reservation_transactions','--group','baseline',
        '--evidence',$storyEvidence) 'STORY21_PROBE_OK baseline'
    return (Get-FileHash -LiteralPath $storyEvidence -Algorithm SHA256).Hash
}

function Get-Story23PassedIds([string[]]$Lines) {
    foreach ($storyLine in $Lines) {
        if ($storyLine -cmatch '^test_\w+ \(([a-zA-Z_][a-zA-Z0-9_.]+)\) \.\.\. ok$') { $Matches[1] }
    }
}

$storyHeld = @()
Push-Location -LiteralPath $storyRoot
try {
    Save-Story23Hashes 'before'

    # Coordinate with this verifier, and recognize already-existing older verifier leases without modifying them.
    $storyTemp = [IO.Path]::GetTempPath()
    $storyHeld += [IO.File]::Open((Join-Path $storyTemp 'LabBooking-test-127.0.0.1-5433-story23.lock'),
        [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    $storyEarlierLeases = @(
        (Join-Path $storyTemp 'LabBooking-test-127.0.0.1-5433-story22.lock'),
        (Join-Path $PSScriptRoot '.story-2-1-remediation.lock'),
        (Join-Path $PSScriptRoot 'story-2-1-targeted-independent-recheck/.d041-release.lock')
    )
    foreach ($storyLock in $storyEarlierLeases) {
        if (Test-Path -LiteralPath $storyLock -PathType Leaf) {
            $storyHeld += [IO.File]::Open($storyLock, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::None)
        }
    }
    Write-Story23Stage 'verification-locks' 0
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
        Write-Story23Stage 'preflight' 1
    }
    Write-Story23Stage 'preflight' 0

    $env:PGPASSFILE = $Passfile
    $env:LAB_BOOKING_R1_CHROME = $Chrome
    $env:LAB_BOOKING_DB_MODE = 'test'
    $env:DJANGO_SETTINGS_MODULE = 'lab_booking.settings'
    $env:PYTHONIOENCODING = 'utf-8'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:LAB_BOOKING_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')

    $storyBefore = Get-Story23Baseline 'baseline-before'
    $null = Invoke-Story23Python 'check' @('manage.py','check') 'System check identified no issues (0 silenced).'
    $null = Invoke-Story23Python 'migration-drift' @('manage.py','makemigrations','--check','--dry-run') 'No changes detected'
    $storyTests = @(Invoke-Story23Python 'regression' @('manage.py','test','--keepdb','--parallel','1','-v','2') 'OK')
    $storyPrior = @(Get-Story23PassedIds @(Get-Content -LiteralPath $storyLedger -Encoding UTF8))
    $storyPassed = @(Get-Story23PassedIds $storyTests)
    $storyNew = @($storyPassed | Where-Object { $_ -cmatch '^reservations\.test_own_reservations\.' })
    $storyMissing = @($storyPrior | Where-Object { $_ -cnotin $storyPassed })
    $storySkipped = @($storyTests | Where-Object { $_ -cmatch '\.{3} skipped ' })
    $storyPassed | Set-Content -LiteralPath (Join-Path $storyOut 'passed-tests.txt') -Encoding UTF8
    "legacy=$($storyPrior.Count) missing=$($storyMissing.Count) new=$($storyNew.Count) total=$($storyPassed.Count) skipped=$($storySkipped.Count)" |
        Set-Content -LiteralPath (Join-Path $storyOut 'regression-counts.txt') -Encoding UTF8
    if ($storyPrior.Count -ne 103 -or @($storyPrior | Sort-Object -Unique).Count -ne 103 -or $storyMissing.Count -ne 0 -or
        $storyNew.Count -ne 10 -or $storyPassed.Count -ne 113 -or @($storyPassed | Sort-Object -Unique).Count -ne 113 -or
        $storySkipped.Count -ne 0 -or @($storyTests | Where-Object { $_ -ceq 'Found 113 test(s).' }).Count -ne 1 -or
        @($storyTests | Where-Object { $_ -cmatch '^Ran 113 tests in ' }).Count -ne 1) {
        throw 'Regression test identity, denominator or skip count differs. See regression evidence.'
    }
    if ((Get-Story23Baseline 'baseline-after-regression') -cne $storyBefore) {
        throw 'Regression changed isolated schema or data.'
    }

    $storyEvidence = Join-Path $storyOut 'independent.jsonl'
    $storyMarker = "STORY23_PROBE_OK cases=$($storyExpectedCases.Count)"
    $null = Invoke-Story23Python 'independent' @('manage.py','verify_own_reservations','--evidence',$storyEvidence) $storyMarker
    $storyRecords = @(Get-Content -LiteralPath $storyEvidence -Encoding UTF8 | ForEach-Object { ConvertFrom-Json $_ })
    $storyActualCases = @($storyRecords | Where-Object { $_.case } | ForEach-Object { $_.case })
    if (($storyActualCases -join '|') -cne ($storyExpectedCases -join '|') -or
        ($storyRecords[0].database[0..8] -join '|') -cne
            'test_lab_booking|lab_booking_test|lab_booking_test|127.0.0.1|5433|170012|read committed|False|False' -or
        -not $storyRecords[-1].cleanup) {
        throw 'Probe evidence is missing an expected case, isolated identity or verified cleanup.'
    }
    if ((Get-Story23Baseline 'baseline-after-independent') -cne $storyBefore) {
        throw 'Independent probes changed isolated schema or data.'
    }
} catch {
    $_ | Out-String | Add-Content -LiteralPath (Join-Path $storyOut 'failure.txt') -Encoding UTF8
    throw
} finally {
    try {
        if (Test-Path -LiteralPath (Join-Path $storyOut 'before.sha256')) {
            Save-Story23Hashes 'after'
            if ((Get-FileHash -LiteralPath (Join-Path $storyOut 'before.sha256')).Hash -cne
                    (Get-FileHash -LiteralPath (Join-Path $storyOut 'after.sha256')).Hash) {
                throw 'Source or verification inputs changed during the run.'
            }
        }
    } finally {
        foreach ($storyHandle in $storyHeld) { $storyHandle.Dispose() }
        foreach ($storyName in $storyEnvNames) {
            [Environment]::SetEnvironmentVariable($storyName, $storyOldEnv[$storyName], 'Process')
        }
        Pop-Location
    }
}
Write-Story23Stage 'complete' 0
Write-Output 'STORY23_VERIFICATION_OK'
