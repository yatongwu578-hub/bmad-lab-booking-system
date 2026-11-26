[CmdletBinding()]
param(
    [string]$Passfile,
    [string]$Chrome,
    [string]$Psql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe',
    [string]$OutputRoot
)

# Apply the complete Story 2.2 changes, including any separate equipment detail patch,
# before reading and executing this file in ordinary Windows PowerShell.
# No migrations, flush, application runtime database, or Git mutation.
$ErrorActionPreference = 'Stop'
$storyRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$storyPython = Join-Path $storyRoot '.venv/Scripts/python.exe'
$storyPreflight = Join-Path $PSScriptRoot 'preflight-story-2-1.ps1'
$storyArtifacts = '_bmad-output/implementation-artifacts'
$storyWiring = @{
    'equipment/views.py' = '"occupancy_pk": pk'
    'equipment/templates/equipment/detail.html' = 'equipment-occupancy'
}
foreach ($storyPath in $storyWiring.Keys) {
    if (-not (Select-String -LiteralPath (Join-Path $storyRoot $storyPath) -SimpleMatch $storyWiring[$storyPath] -Quiet)) {
        throw 'Apply the Story 2.2 equipment detail wiring patch before starting verification.'
    }
}
if (-not $OutputRoot) { $OutputRoot = $PSScriptRoot }
$storyOut = Join-Path $OutputRoot ("story-2-2-run-" + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') +
    '-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
$storyOut = (New-Item -ItemType Directory -Path $storyOut).FullName
Write-Host "Story 2.2 evidence: $storyOut"

if (-not $Passfile) { $Passfile = $env:PGPASSFILE }
if (-not $Passfile) { $Passfile = Join-Path $env:LOCALAPPDATA 'LabBooking/PostgreSQL17/pgpass.conf' }
if (-not $Chrome) { $Chrome = $env:LAB_BOOKING_R1_CHROME }
if (-not $Chrome) { $Chrome = Join-Path $env:ProgramFiles 'Google/Chrome/Application/chrome.exe' }
$storyEnvNames = @('LAB_BOOKING_DB_MODE','LAB_BOOKING_R1_CHROME','LAB_BOOKING_SECRET_KEY',
    'DJANGO_SETTINGS_MODULE','PGPASSFILE','PYTHONIOENCODING','PYTHONDONTWRITEBYTECODE')
$storyPreviousEnv = @{}
foreach ($storyName in $storyEnvNames) {
    $storyPreviousEnv[$storyName] = [Environment]::GetEnvironmentVariable($storyName, 'Process')
}
$storyInputs = @('manage.py', 'requirements.txt', '_bmad-output/planning-artifacts/epics.md',
    "$storyArtifacts/spec-2-2-query-equipment-occupancy.md", "$storyArtifacts/story-2-2-checkpoint-1.md",
    "$storyArtifacts/preflight-story-2-1.ps1", "$storyArtifacts/verify-story-2-2.ps1")
foreach ($storyDir in @('accounts','equipment','lab_booking','audit','reservations')) {
    $storyInputs += Get-ChildItem -LiteralPath (Join-Path $storyRoot $storyDir) -File -Recurse |
        Where-Object { $_.Extension -in '.py', '.html' } |
        ForEach-Object { $_.FullName.Substring($storyRoot.Length + 1).Replace('\','/') }
}

function Save-Story22Hashes([string]$Name) {
    $storyInputs | Sort-Object -Unique | ForEach-Object {
        $storyHash = Get-FileHash -LiteralPath (Join-Path $storyRoot $_) -Algorithm SHA256
        "$($storyHash.Hash)  $_"
    } | Set-Content -LiteralPath (Join-Path $storyOut "$Name.sha256") -Encoding UTF8
}

function Write-Story22Stage([string]$Stage, [int]$Code) {
    "$(Get-Date -Format o) $Stage exit=$Code" | Add-Content -LiteralPath (Join-Path $storyOut 'stages.txt') -Encoding UTF8
    if ($Code -ne 0) { throw "Stage $Stage exited $Code. See $storyOut." }
}

function Invoke-Story22Python([string]$Stage, [string[]]$StoryArgs, [string]$Marker) {
    $storyStdout = Join-Path $storyOut "$Stage.stdout.txt"
    $storyStderr = Join-Path $storyOut "$Stage.stderr.txt"
    ('python ' + ($StoryArgs -join ' ')) | Set-Content -LiteralPath (Join-Path $storyOut "$Stage.command.txt") -Encoding UTF8
    $storyProcess = @{
        FilePath = $storyPython
        ArgumentList = ($StoryArgs | ForEach-Object { '"' + $_ + '"' }) -join ' '
        WorkingDirectory = $storyRoot
        WindowStyle = 'Hidden'
        Wait = $true
        PassThru = $true
        RedirectStandardOutput = $storyStdout
        RedirectStandardError = $storyStderr
    }
    $storyResult = Start-Process @storyProcess
    Write-Story22Stage $Stage $storyResult.ExitCode
    $storyLines = @(Get-Content -LiteralPath $storyStdout,$storyStderr -Encoding UTF8)
    if (@($storyLines | Where-Object { $_ -ceq $Marker }).Count -ne 1) {
        throw "Stage $Stage did not emit exactly one '$Marker'."
    }
    return $storyLines
}

function Get-Story22Baseline([string]$Stage) {
    $storyFile = Join-Path $storyOut "$Stage.json"
    $null = Invoke-Story22Python $Stage @('manage.py','verify_reservation_transactions','--group','baseline','--evidence',
        $storyFile) 'STORY21_PROBE_OK baseline'
    return (Get-FileHash -LiteralPath $storyFile -Algorithm SHA256).Hash
}

$storyHeld = @()
Push-Location -LiteralPath $storyRoot
try {
    Save-Story22Hashes 'before'
    foreach ($storyScript in @($PSCommandPath, $storyPreflight)) {
        $storyTokens = $null
        $storyErrors = $null
        $null = [System.Management.Automation.Language.Parser]::ParseFile($storyScript, [ref]$storyTokens, [ref]$storyErrors)
        if ($storyErrors.Count) { throw ($storyErrors -join [Environment]::NewLine) }
    }
    Write-Story22Stage 'powershell-parse' 0

    # Refuse overlap with another run or an older verifier holding its existing lock.
    $storyLeasePath = Join-Path ([IO.Path]::GetTempPath()) 'LabBooking-test-127.0.0.1-5433-story22.lock'
    $storyHeld += [IO.File]::Open($storyLeasePath,
        [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    foreach ($storyLock in @('.story-2-1-remediation.lock','story-2-1-targeted-independent-recheck/.d041-release.lock')) {
        $storyLockPath = Join-Path $PSScriptRoot $storyLock
        if (Test-Path -LiteralPath $storyLockPath -PathType Leaf) {
            $storyHeld += [IO.File]::Open($storyLockPath, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::None)
        }
    }
    Write-Story22Stage 'verification-locks' 0
    try {
        & $storyPreflight -Passfile $Passfile -Chrome $Chrome -Psql $Psql -ProbeIsolatedDatabase 2>&1 |
            Tee-Object -FilePath (Join-Path $storyOut 'preflight.txt') | Write-Host
        if (@(Get-Content -LiteralPath (Join-Path $storyOut 'preflight.txt') |
                Where-Object { $_ -ceq 'STORY21_PREFLIGHT_OK' }).Count -ne 1) {
            throw 'Preflight did not confirm the guarded test database and original tools.'
        }
    } catch {
        $_ | Out-String | Add-Content -LiteralPath (Join-Path $storyOut 'preflight.txt')
        Write-Story22Stage 'preflight' 1
    }
    Write-Story22Stage 'preflight' 0

    $env:PGPASSFILE = $Passfile
    $env:LAB_BOOKING_R1_CHROME = $Chrome
    $env:LAB_BOOKING_DB_MODE = 'test'
    $env:DJANGO_SETTINGS_MODULE = 'lab_booking.settings'
    $env:PYTHONIOENCODING = 'utf-8'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:LAB_BOOKING_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')

    $storyBefore = Get-Story22Baseline 'baseline-before'
    $null = Invoke-Story22Python 'check' @('manage.py','check') 'System check identified no issues (0 silenced).'
    $null = Invoke-Story22Python 'migration-drift' @('manage.py','makemigrations','--check','--dry-run') 'No changes detected'
    $storyReg = @(Invoke-Story22Python 'regression' @('manage.py','test','--keepdb','--parallel','1','-v','2') 'OK')
    $storyExpected = 103  # 91 pre-existing plus 12 discoverable Story 2.2 Django tests.
    $storyFound = @($storyReg | Where-Object { $_ -cmatch '^Found \d+ test\(s\)\.$' })
    $storyRan = @($storyReg | Where-Object { $_ -cmatch '^Ran \d+ tests in ' })
    $storyPassed = @($storyReg | Where-Object { $_ -cmatch '^ok$|\.{3} ok$' }).Count
    $storySkipped = @($storyReg | Where-Object { $_ -cmatch '\.{3} skipped ' }).Count
    $storyNewCount = @($storyReg | Where-Object { $_ -cmatch '^test_.*reservations\.test_occupancy\.' }).Count
    "found=$storyFound ran=$storyRan passed=$storyPassed skipped=$storySkipped expected=$storyExpected new=$storyNewCount" |
        Set-Content -LiteralPath (Join-Path $storyOut 'regression-counts.txt') -Encoding UTF8
    if ($storyFound.Count -ne 1 -or $storyFound[0] -cne "Found $storyExpected test(s)." -or $storyRan.Count -ne 1 -or
        $storyRan[0] -cnotmatch "^Ran $storyExpected tests in " -or $storyPassed -ne $storyExpected -or
        $storySkipped -ne 0 -or $storyNewCount -ne 12) {
        throw 'Regression discovery or zero-skip denominator differs. See regression-counts.txt.'
    }
    if ((Get-Story22Baseline 'baseline-after-regression') -cne $storyBefore) {
        throw 'Django regression changed the isolated schema or data baseline.'
    }

    $storyEvidence = Join-Path $storyOut 'independent.jsonl'
    $storyProbe = @('manage.py','verify_equipment_occupancy','--evidence',$storyEvidence)
    $null = Invoke-Story22Python 'independent' $storyProbe 'STORY22_PROBE_OK cases=21'
    $storyRecords = @(Get-Content -LiteralPath $storyEvidence -Encoding UTF8 | ForEach-Object { ConvertFrom-Json $_ })
    $storyCases = @($storyRecords | Where-Object { $_.case } | ForEach-Object { $_.case })
    if ($storyCases.Count -ne 21 -or @($storyCases | Sort-Object -Unique).Count -ne 21 -or
        $storyRecords[0].database[0] -cne 'test_lab_booking' -or -not $storyRecords[-1].cleanup) {
        throw 'Independent probe evidence does not match its reported denominator, identity and cleanup.'
    }
    if ((Get-Story22Baseline 'baseline-after-independent') -cne $storyBefore) {
        throw 'Independent probe changed the isolated schema or data baseline.'
    }
} catch {
    $_ | Out-String | Add-Content -LiteralPath (Join-Path $storyOut 'failure.txt') -Encoding UTF8
    throw
} finally {
    try {
        if (Test-Path -LiteralPath (Join-Path $storyOut 'before.sha256')) {
            Save-Story22Hashes 'after'
            if ((Get-FileHash -LiteralPath (Join-Path $storyOut 'after.sha256')).Hash -cne
                (Get-FileHash -LiteralPath (Join-Path $storyOut 'before.sha256')).Hash) {
                throw 'Verification inputs changed during execution.'
            }
        }
    } finally {
        foreach ($storyHandle in $storyHeld) { $storyHandle.Dispose() }
        foreach ($storyName in $storyEnvNames) {
            [Environment]::SetEnvironmentVariable($storyName, $storyPreviousEnv[$storyName], 'Process')
        }
        Pop-Location
    }
}
Write-Story22Stage 'complete' 0
Write-Output 'STORY22_VERIFICATION_OK'
