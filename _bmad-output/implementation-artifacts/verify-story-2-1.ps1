[CmdletBinding()]
param(
    [string]$Passfile,
    [string]$Chrome,
    [string]$OutputRoot,
    [string]$Psql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe',
    [string]$ResumeFrom,
    [ValidateSet('interleavings','remaining')]
    [string]$ResumePhase = 'interleavings',
    [string]$InterleavingsEvidence
)

$ErrorActionPreference = 'Stop'
if ((-not $ResumeFrom -and ($PSBoundParameters.ContainsKey('ResumePhase') -or $InterleavingsEvidence)) -or
    (($ResumePhase -eq 'remaining') -ne [bool]$InterleavingsEvidence)) {
    throw 'Resume requires -ResumeFrom; only -ResumePhase remaining requires -InterleavingsEvidence.'
}
if ($ResumeFrom) { $ResumeFrom = (Resolve-Path -LiteralPath $ResumeFrom).Path }
if ($InterleavingsEvidence) { $InterleavingsEvidence = (Resolve-Path -LiteralPath $InterleavingsEvidence).Path }
$storyRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$storyPython = Join-Path $storyRoot '.venv/Scripts/python.exe'
$storyPreflight = Join-Path $PSScriptRoot 'preflight-story-2-1.ps1'
$storyStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
if (-not $OutputRoot) { $OutputRoot = $PSScriptRoot }
$storyOut = Join-Path $OutputRoot "story-2-1-run-$storyStamp-$([guid]::NewGuid().ToString('N').Substring(0, 8))"
$null = New-Item -ItemType Directory -Path $storyOut
$storyOut = (Resolve-Path -LiteralPath $storyOut).Path
Write-Host "Story 2.1 evidence: $storyOut"

if (-not $Passfile) { $Passfile = $env:PGPASSFILE }
if (-not $Passfile) { $Passfile = Join-Path $env:LOCALAPPDATA 'LabBooking/PostgreSQL17/pgpass.conf' }
if (-not $Chrome) { $Chrome = $env:LAB_BOOKING_R1_CHROME }
if (-not $Chrome) { $Chrome = Join-Path $env:ProgramFiles 'Google/Chrome/Application/chrome.exe' }
$storyEnvironment = @('LAB_BOOKING_DB_MODE','LAB_BOOKING_R1_CHROME','LAB_BOOKING_SECRET_KEY',
    'DJANGO_SETTINGS_MODULE','PGPASSFILE','PYTHONIOENCODING','PYTHONDONTWRITEBYTECODE')
$storyPrevious = @{}
foreach ($storyName in $storyEnvironment) {
    $storyPrevious[$storyName] = [Environment]::GetEnvironmentVariable($storyName, 'Process')
}
$storyInputs = @('manage.py', 'requirements.txt')
foreach ($storyDir in @('accounts','equipment','lab_booking','audit','reservations')) {
    $storyInputs += Get-ChildItem -LiteralPath (Join-Path $storyRoot $storyDir) -File -Recurse |
        Where-Object { $_.Extension -in '.py', '.html' } |
        ForEach-Object { $_.FullName.Substring($storyRoot.Length + 1).Replace('\','/') }
}
$storyInputs += @('_bmad-output/implementation-artifacts/spec-2-1-submit-reservation.md',
    '_bmad-output/implementation-artifacts/story-2-1-checkpoint-1.md',
    '_bmad-output/planning-artifacts/epics.md',
    '_bmad-output/implementation-artifacts/preflight-story-2-1.ps1',
    '_bmad-output/implementation-artifacts/verify-story-2-1.ps1')

function Save-StoryHashes([string]$Name) {
    $storyInputs | Sort-Object -Unique | ForEach-Object {
        $storyDigest = Get-FileHash -LiteralPath (Join-Path $storyRoot $_) -Algorithm SHA256
        "$($storyDigest.Hash)  $_"
    } | Set-Content -LiteralPath (Join-Path $storyOut "$Name.sha256") -Encoding UTF8
}

function Write-StoryStage([string]$Name, [int]$Code) {
    "$(Get-Date -Format o) $Name exit=$Code" | Add-Content -LiteralPath (Join-Path $storyOut 'stages.txt') -Encoding UTF8
    if ($Code -ne 0) { throw "Stage $Name failed (exit $Code). Evidence: $storyOut" }
}

function Run-StoryPython([string]$Name, [string[]]$StoryArguments, [string]$ExactLine) {
    Write-Host "Running $Name"
    ('python ' + ($StoryArguments -join ' ')) | Set-Content -LiteralPath (Join-Path $storyOut "$Name.command.txt") -Encoding UTF8
    $storyStdout = Join-Path $storyOut "$Name.stdout.txt"
    $storyStderr = Join-Path $storyOut "$Name.stderr.txt"
    $storyQuoted = ($StoryArguments | ForEach-Object { '"' + $_ + '"' }) -join ' '
    $storyProcess = Start-Process -FilePath $storyPython -ArgumentList $storyQuoted -WorkingDirectory $storyRoot -Wait -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput $storyStdout -RedirectStandardError $storyStderr
    Write-StoryStage $Name $storyProcess.ExitCode
    if ($ExactLine) {
        $storyLines = @(Get-Content -LiteralPath $storyStdout,$storyStderr -Encoding UTF8)
        if (@($storyLines | Where-Object { $_ -ceq $ExactLine }).Count -ne 1) {
            throw "Stage $Name did not provide exact success line '$ExactLine'."
        }
    }
}

function Invoke-StoryProbe([string]$Group, [string]$EvidenceName) {
    $storyEvidencePath = Join-Path $storyOut "$EvidenceName.jsonl"
    $storyProbeArgs = @('manage.py','verify_reservation_transactions','--group',$Group,'--evidence',$storyEvidencePath)
    if ($ResumeFrom) { $storyProbeArgs += '--traceback' }
    Run-StoryPython $EvidenceName $storyProbeArgs "STORY21_PROBE_OK $Group"
}

function Assert-StoryResumeStage([string]$Dir, [string]$Stage, [string]$Marker) {
    $storyStageLines = @(Get-Content -LiteralPath (Join-Path $Dir 'stages.txt') -Encoding UTF8 |
        Where-Object { $_ -cmatch " $([regex]::Escape($Stage)) exit=" })
    if ($storyStageLines.Count -ne 1 -or $storyStageLines[0] -cnotmatch ' exit=0$') {
        throw "Missing successful $Stage stage in $Dir."
    }
    if ($Marker) {
        $storyStageOutput = @(Get-Content -LiteralPath (Join-Path $Dir "$Stage.stdout.txt"),(Join-Path $Dir "$Stage.stderr.txt") -Encoding UTF8)
        if (@($storyStageOutput | Where-Object { $_ -ceq $Marker }).Count -ne 1) {
            throw "Missing exact $Stage success marker in $Dir."
        }
    }
}

function Invoke-StoryResume {
    $storyResumeBefore = Join-Path $ResumeFrom 'before.sha256'
    $storyResumeAfter = Join-Path $ResumeFrom 'after.sha256'
    $storyCurrent = Join-Path $storyOut 'before.sha256'
    if ((Get-FileHash -LiteralPath $storyResumeBefore).Hash -cne (Get-FileHash -LiteralPath $storyResumeAfter).Hash) {
        throw 'Historical input hashes changed during the original run.'
    }
    # Only the two verification tools may differ from the original run.
    $storyAllowedChanges = @('reservations/management/commands/verify_reservation_transactions.py',
        '_bmad-output/implementation-artifacts/verify-story-2-1.ps1')
    $storyHistoricalLines = @(Get-Content -LiteralPath $storyResumeAfter -Encoding UTF8 |
        Where-Object { (($_ -split '  ', 2)[1]) -cnotin $storyAllowedChanges })
    $storyCurrentLines = @(Get-Content -LiteralPath $storyCurrent -Encoding UTF8 |
        Where-Object { (($_ -split '  ', 2)[1]) -cnotin $storyAllowedChanges })
    $storyChanged = @(Compare-Object -ReferenceObject $storyHistoricalLines -DifferenceObject $storyCurrentLines -CaseSensitive)
    if ($storyChanged.Count) { throw 'Verification inputs outside the two tools changed; historical evidence cannot be reused.' }
    Assert-StoryResumeStage $ResumeFrom 'migrate-isolated'
    Assert-StoryResumeStage $ResumeFrom 'check' 'System check identified no issues (0 silenced).'
    Assert-StoryResumeStage $ResumeFrom 'migration-drift' 'No changes detected'
    Assert-StoryResumeStage $ResumeFrom 'regression' 'OK'
    Assert-StoryResumeStage $ResumeFrom 'permissions' 'STORY21_PROBE_OK permissions'
    $storyCounts = Get-Content -LiteralPath (Join-Path $ResumeFrom 'regression-counts.txt') -Raw -Encoding UTF8
    if ($storyCounts.Trim() -cnotmatch '^found=Found 90 test\(s\)\. ran=Ran 90 tests in [0-9.]+s passed=90 skipped=0 expected=90$') {
        throw 'Historical regression evidence does not show 90 passes and zero skips.'
    }
    $storyBaselineHash = (Get-FileHash -LiteralPath (Join-Path $ResumeFrom 'regression-after.jsonl')).Hash
    if ((Get-FileHash -LiteralPath (Join-Path $ResumeFrom 'regression-before.jsonl')).Hash -cne $storyBaselineHash) {
        throw 'Historical regression database snapshots differ.'
    }
    if ($InterleavingsEvidence) {
        Assert-StoryResumeStage $InterleavingsEvidence 'interleavings' 'STORY21_PROBE_OK interleavings'
        Assert-StoryResumeStage $InterleavingsEvidence 'resume-complete'
        $storyCurrentHash = (Get-FileHash -LiteralPath $storyCurrent).Hash
        foreach ($storyManifest in @('before.sha256','after.sha256')) {
            if ((Get-FileHash -LiteralPath (Join-Path $InterleavingsEvidence $storyManifest)).Hash -cne $storyCurrentHash) {
                throw 'Interleavings evidence was produced with different verification inputs.'
            }
        }
        if ((Get-FileHash -LiteralPath (Join-Path $InterleavingsEvidence 'resume-after.jsonl')).Hash -cne $storyBaselineHash) {
            throw 'Interleavings evidence was produced with a different database baseline.'
        }
    }
    @("phase=$ResumePhase", "original=$ResumeFrom", "interleavings=$InterleavingsEvidence",
      "reused=migrate-isolated,check,migration-drift,regression,permissions", "baseline_sha256=$storyBaselineHash") |
        Set-Content -LiteralPath (Join-Path $storyOut 'resume.txt') -Encoding UTF8
    Invoke-StoryProbe 'baseline' 'resume-before'
    if ((Get-FileHash -LiteralPath (Join-Path $storyOut 'resume-before.jsonl')).Hash -cne $storyBaselineHash) {
        throw 'Current isolated database differs from the historical baseline; no fixtures or migrations were run.'
    }
    if ($ResumePhase -eq 'remaining') {
        $storyGroups = @('faults','nfr001-standard','time-boundaries')
    } else {
        $storyGroups = @('interleavings')
    }
    foreach ($storyGroup in $storyGroups) { Invoke-StoryProbe $storyGroup $storyGroup }
    Invoke-StoryProbe 'baseline' 'resume-after'
    if ((Get-FileHash -LiteralPath (Join-Path $storyOut 'resume-after.jsonl')).Hash -cne $storyBaselineHash) {
        throw 'Isolated database after resumed verification differs from the historical baseline.'
    }
    Write-StoryStage 'resume-complete' 0
}

Push-Location -LiteralPath $storyRoot
try {
    Save-StoryHashes 'before'
    foreach ($storyScript in @($PSCommandPath,$storyPreflight)) {
        $storyTokens = $null
        $storyParseErrors = $null
        $null = [System.Management.Automation.Language.Parser]::ParseFile($storyScript, [ref]$storyTokens, [ref]$storyParseErrors)
        if ($storyParseErrors.Count) { throw ($storyParseErrors -join [Environment]::NewLine) }
    }
    Write-StoryStage 'powershell-parse' 0
    try {
        & $storyPreflight -Passfile $Passfile -Chrome $Chrome -Psql $Psql -ProbeIsolatedDatabase 2>&1 |
            Tee-Object -FilePath (Join-Path $storyOut 'preflight.txt') | Write-Host
        if (@(Get-Content -LiteralPath (Join-Path $storyOut 'preflight.txt') | Where-Object { $_ -ceq 'STORY21_PREFLIGHT_OK' }).Count -ne 1) {
            throw 'Preflight did not confirm the guarded test database.'
        }
    } catch {
        $_ | Out-String | Add-Content -LiteralPath (Join-Path $storyOut 'preflight.txt')
        Write-StoryStage 'preflight' 1
    }
    Write-StoryStage 'preflight' 0
    $env:PGPASSFILE = $Passfile
    $env:LAB_BOOKING_R1_CHROME = $Chrome
    $env:LAB_BOOKING_DB_MODE = 'test'
    $env:DJANGO_SETTINGS_MODULE = 'lab_booking.settings'
    $env:PYTHONIOENCODING = 'utf-8'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:LAB_BOOKING_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')

    if ($ResumeFrom) {
        Invoke-StoryResume
    } else {
    Invoke-StoryProbe 'pre-migrate' 'migration-before'
    Run-StoryPython 'plan' @('manage.py','showmigrations','--plan')
    $storyUnapplied = @(Get-Content -LiteralPath (Join-Path $storyOut 'plan.stdout.txt') -Encoding UTF8 |
        Where-Object { $_ -match '^\[ \]' } | ForEach-Object { ($_ -split '\s+')[2] })
    if (@($storyUnapplied | Where-Object { $_ -cnotin @('reservations.0001_initial','audit.0001_initial') }).Count) {
        throw "Test database has unapplied migrations outside Story 2.1. See plan.stdout.txt."
    }
    Run-StoryPython 'reservation-sql' @('manage.py','sqlmigrate','reservations','0001')
    Run-StoryPython 'audit-sql' @('manage.py','sqlmigrate','audit','0001')
    # No old named target: the guarded plan allows only the two forward initial migrations.
    Run-StoryPython 'migrate-isolated' @('manage.py','migrate','--noinput')
    Invoke-StoryProbe 'baseline' 'regression-before'
    $storyMigrationBefore = Get-Content -LiteralPath (Join-Path $storyOut 'migration-before.jsonl') -Raw -Encoding UTF8 | ConvertFrom-Json
    $storyMigrationAfter = Get-Content -LiteralPath (Join-Path $storyOut 'regression-before.jsonl') -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($storyProperty in $storyMigrationBefore.rows.PSObject.Properties) {
        $storyCurrent = $storyMigrationAfter.rows.PSObject.Properties[$storyProperty.Name]
        if (-not $storyCurrent -or $storyCurrent.Value.count -ne $storyProperty.Value.count -or
            $storyCurrent.Value.sha256 -cne $storyProperty.Value.sha256) {
            throw "Migration changed existing rows in $($storyProperty.Name)."
        }
    }
    Run-StoryPython 'check' @('manage.py','check') 'System check identified no issues (0 silenced).'
    Run-StoryPython 'migration-drift' @('manage.py','makemigrations','--check','--dry-run') 'No changes detected'

    Run-StoryPython 'regression' @('manage.py','test','--keepdb','--parallel','1','-v','2') 'OK'
    Invoke-StoryProbe 'baseline' 'regression-after'
    $storyRegBefore = Get-FileHash -LiteralPath (Join-Path $storyOut 'regression-before.jsonl')
    $storyRegAfter = Get-FileHash -LiteralPath (Join-Path $storyOut 'regression-after.jsonl')
    if ($storyRegBefore.Hash -cne $storyRegAfter.Hash) { throw 'Regression changed the isolated database rows/schema.' }
    $storyRegLines = @(Get-Content -LiteralPath (Join-Path $storyOut 'regression.stdout.txt'),(Join-Path $storyOut 'regression.stderr.txt') -Encoding UTF8)
    $storyFound = @($storyRegLines | Where-Object { $_ -match '^Found \d+ test\(s\)\.$' })
    $storyRan = @($storyRegLines | Where-Object { $_ -match '^Ran \d+ tests in ' })
    $storyPassed = @($storyRegLines | Where-Object { $_ -cmatch '^ok$|\.{3} ok$' }).Count
    $storySkipped = @($storyRegLines | Where-Object { $_ -match '\.{3} skipped ' }).Count
    "found=$storyFound ran=$storyRan passed=$storyPassed skipped=$storySkipped expected=90" |
        Set-Content -LiteralPath (Join-Path $storyOut 'regression-counts.txt') -Encoding UTF8
    if ($storyFound.Count -ne 1 -or $storyFound[0] -cne 'Found 90 test(s).' -or $storyRan.Count -ne 1 -or
        $storyRan[0] -cnotmatch '^Ran 90 tests in ' -or $storyPassed -ne 90 -or $storySkipped -ne 0) {
        throw 'Expected 90 discovered, run and passed tests, with zero skips. See regression-counts.txt.'
    }
    foreach ($storyGroup in @('permissions','interleavings','faults','nfr001-standard','time-boundaries')) {
        Invoke-StoryProbe $storyGroup $storyGroup
    }
    Write-StoryStage 'complete' 0
    }
} catch {
    $_ | Out-String | Add-Content -LiteralPath (Join-Path $storyOut 'failure.txt') -Encoding UTF8
    throw
} finally {
    try {
        if (Test-Path -LiteralPath (Join-Path $storyOut 'before.sha256')) {
            Save-StoryHashes 'after'
            $storyHashBefore = Get-FileHash -LiteralPath (Join-Path $storyOut 'before.sha256')
            $storyHashAfter = Get-FileHash -LiteralPath (Join-Path $storyOut 'after.sha256')
            if ($storyHashBefore.Hash -cne $storyHashAfter.Hash) { throw 'Verification input SHA-256 changed during verification.' }
        }
    } finally {
        foreach ($storyName in $storyEnvironment) {
            [Environment]::SetEnvironmentVariable($storyName, $storyPrevious[$storyName], 'Process')
        }
        Pop-Location
    }
}
if ($ResumeFrom) {
    Write-Output "STORY21_RESUME_OK $ResumePhase"
} else {
    Write-Output 'STORY21_VERIFICATION_OK'
}
