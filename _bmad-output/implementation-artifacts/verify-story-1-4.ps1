[CmdletBinding()]
param(
    [string]$Passfile,
    [string]$Chrome,
    [string]$LogPath
)

$ErrorActionPreference = 'Stop'
$storyRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$storyPatch = Join-Path $PSScriptRoot 'story-1-4-edit-equipment-basics.patch'
if (-not $LogPath) {
    $storyStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    $LogPath = Join-Path $PSScriptRoot "story-1-4-verification-$storyStamp.txt"
}
if (Test-Path -LiteralPath $LogPath) { throw 'Log file exists. Choose a new path.' }
$LogPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($LogPath)
New-Item -ItemType File -Path $LogPath | Out-Null

function Write-StoryVerification([string]$Line) {
    $Line | Tee-Object -FilePath $LogPath -Append | Write-Host
}

function Invoke-StoryPython([string[]]$StoryArguments) {
    Write-StoryVerification ('.\.venv\Scripts\python.exe ' + ($StoryArguments -join ' '))
    $ErrorActionPreference = 'Continue'
    & $storyPython @StoryArguments 2>&1 |
        ForEach-Object { $_.ToString() } |
        Tee-Object -FilePath $LogPath -Append | Write-Host
    $storyExitCode = $LASTEXITCODE
    Write-StoryVerification "Exit $storyExitCode"
    if ($storyExitCode -ne 0) { throw "Verification command failed. See $LogPath" }
}

$storyEnvironment = @(
    'LAB_BOOKING_DB_MODE', 'LAB_BOOKING_R1_CHROME', 'LAB_BOOKING_SECRET_KEY',
    'DJANGO_SETTINGS_MODULE', 'PGPASSFILE', 'PYTHONIOENCODING'
)
$storyOriginalEnvironment = @{}
foreach ($name in $storyEnvironment) {
    $storyOriginalEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
$storyOriginalConsoleEncoding = [Console]::OutputEncoding
$storyUtf8 = New-Object System.Text.UTF8Encoding($false)

Push-Location -LiteralPath $storyRoot
try {
    [Console]::OutputEncoding = $storyUtf8
    $env:PYTHONIOENCODING = 'utf-8'
    Write-StoryVerification ("Story 1.4 isolated verification, " + (Get-Date -Format o))
    Write-StoryVerification 'Target: 127.0.0.1:5433/test_lab_booking; PostgreSQL 17.12; Chrome R1 required.'

    $storyPython = Join-Path $storyRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $storyPython -PathType Leaf)) { throw 'Original .venv Python is required.' }
    Invoke-StoryPython -StoryArguments @('--version')
    $storyVersion = & $storyPython --version
    if ($LASTEXITCODE -ne 0 -or $storyVersion -cne 'Python 3.13.17') {
        throw 'Expected Python 3.13.17 in the original .venv.'
    }

    $storyConflict = @('PGHOST', 'PGHOSTADDR', 'PGPORT', 'PGDATABASE', 'PGUSER',
        'PGPASSWORD', 'PGSERVICE', 'PGSERVICEFILE', 'PGOPTIONS') |
        Where-Object { Test-Path "Env:$_" }
    if ($storyConflict) { throw "Remove conflicting PostgreSQL variables: $($storyConflict -join ', ')." }
    if (-not $Passfile) { $Passfile = $env:PGPASSFILE }
    if (-not $Passfile) { $Passfile = Join-Path $env:LOCALAPPDATA 'LabBooking/PostgreSQL17/pgpass.conf' }
    if (-not [IO.Path]::IsPathRooted($Passfile) -or -not (Test-Path -LiteralPath $Passfile -PathType Leaf)) {
        throw 'Provide the existing protected PostgreSQL password file as an absolute path (-Passfile).'
    }
    if (-not $Chrome) { $Chrome = $env:LAB_BOOKING_R1_CHROME }
    if (-not $Chrome) { $Chrome = Join-Path $env:ProgramFiles 'Google/Chrome/Application/chrome.exe' }
    if (-not [IO.Path]::IsPathRooted($Chrome) -or -not (Test-Path -LiteralPath $Chrome -PathType Leaf)) {
        throw 'Provide the existing Chrome R1 executable as an absolute path (-Chrome).'
    }
    $env:PGPASSFILE = $Passfile
    $env:LAB_BOOKING_DB_MODE = 'test'
    $env:DJANGO_SETTINGS_MODULE = 'lab_booking.settings'
    $env:LAB_BOOKING_R1_CHROME = $Chrome
    $env:LAB_BOOKING_SECRET_KEY = & $storyPython -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
    if ($LASTEXITCODE -ne 0 -or -not $env:LAB_BOOKING_SECRET_KEY) { throw 'Cannot initialize a temporary Django key.' }

    if (-not ((Test-Path -LiteralPath 'equipment/test_edit.py') -and
              (Test-Path -LiteralPath 'equipment/management/commands/verify_equipment_edit_transactions.py'))) {
        throw "Apply the implementation patch first: $storyPatch"
    }
    Invoke-StoryPython -StoryArguments @('manage.py', 'check')
    Invoke-StoryPython -StoryArguments @('manage.py', 'makemigrations', '--check', '--dry-run')
    Invoke-StoryPython -StoryArguments @('manage.py', 'test', '--keepdb', '--parallel', '1', '-v', '2')
    Invoke-StoryPython -StoryArguments @('manage.py', 'verify_equipment_edit_transactions')
    Write-StoryVerification 'Commands completed. Confirm test counts, absence of skips, and probe cleanup before review.'
}
catch {
    Write-StoryVerification ("Stopped: " + $_.Exception.Message)
    throw
}
finally {
    [Console]::OutputEncoding = $storyOriginalConsoleEncoding
    foreach ($name in $storyEnvironment) {
        [Environment]::SetEnvironmentVariable($name, $storyOriginalEnvironment[$name], 'Process')
    }
    Pop-Location
}
