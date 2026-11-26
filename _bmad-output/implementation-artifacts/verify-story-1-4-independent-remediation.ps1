[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ExecutedBy,
    [string]$Passfile,
    [string]$Chrome
)

$ErrorActionPreference = 'Stop'
$operator = $ExecutedBy.Trim()
if (-not $operator -or $operator -match 'placeholder|your name|\u586B\u5199|\u5B9E\u9645\u64CD\u4F5C\u8005\u59D3\u540D') {
    throw 'Enter the actual operator name, not a placeholder.'
}
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$python = Join-Path $root '.venv/Scripts/python.exe'
$wrapper = Join-Path $PSScriptRoot 'verify-story-1-4-remediation.ps1'
$probe = Join-Path $PSScriptRoot 'check-story-1-4-existing-crlf.py'
$artifactPrefix = '_bmad-output/implementation-artifacts/'
$out = Join-Path $PSScriptRoot ('story-1-4-independent-remediation-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $out | Out-Null
$utf8 = [Text.UTF8Encoding]::new($false)
$started = Get-Date -Format o
$old = @(Get-ChildItem -LiteralPath $PSScriptRoot -Directory -Filter 'story-1-4-remediation-run-*' | ForEach-Object { $_.Name })
$names = @('LAB_BOOKING_DB_MODE','DJANGO_SETTINGS_MODULE','PGPASSFILE','LAB_BOOKING_SECRET_KEY','PYTHONIOENCODING')
$previous = @{}
foreach ($name in $names) { $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
$consoleEncoding = [Console]::OutputEncoding
$before = 'NOT CAPTURED'
$after = 'NOT CAPTURED'
$fullRun = 'NOT CAPTURED'
$q3Log = Join-Path $out 'q3-raw.txt'
$q3Exit = 'NOT RUN'
$exit = 1
$failure = ''

function Write-ReviewManifest([string]$Phase) {
    $tracked = @(git ls-files --cached --others --exclude-standard -- accounts equipment lab_booking manage.py requirements.txt)
    if ($LASTEXITCODE -ne 0 -or -not $tracked.Count) { throw 'Could not enumerate tested files.' }
    $inputs = @('verify-story-1-4.ps1','verify-story-1-4-remediation.ps1','verify-story-1-4-independent-remediation.ps1',
        'check-story-1-4-existing-crlf.py','story-1-4-r1-r2-r7.patch','story-1-4-verification-20261125-221855-930.txt')
    $allPaths = @($tracked + @($inputs | ForEach-Object { $artifactPrefix + $_ }) | Sort-Object -Unique)
    $rows = foreach ($path in $allPaths) { "$((Get-FileHash -LiteralPath (Join-Path $root $path)).Hash)  $path" }
    $manifest = Join-Path $out "$Phase.sha256"
    [IO.File]::WriteAllLines($manifest, [string[]]$rows, $utf8)
    (Get-FileHash -LiteralPath $manifest).Hash
}

function Find-FullRun {
    @(Get-ChildItem -LiteralPath $PSScriptRoot -Directory -Filter 'story-1-4-remediation-run-*' |
        Where-Object { $_.Name -cnotin $old })
}

function Invoke-Q3 {
    [IO.File]::WriteAllLines($q3Log, [string[]]@(
        'Q-3 isolated independent recheck; only 127.0.0.1:5433/test_lab_booking, lab_booking_test',
        '.\.venv\Scripts\python.exe -B _bmad-output/implementation-artifacts/check-story-1-4-existing-crlf.py'
    ), $utf8)
    $ErrorActionPreference = 'Continue'
    & $python -B $probe 2>&1 | ForEach-Object { $_.ToString() } |
        ForEach-Object { [IO.File]::AppendAllText($q3Log, $_ + [Environment]::NewLine, $utf8); Write-Host $_ }
    $LASTEXITCODE
}

Push-Location -LiteralPath $root
try {
    $before = Write-ReviewManifest 'before'
    $correctedMarker = 'R2 whitespace preserved: new description and unchanged textarea with CRLF; detail auto-escaped.'
    $wrapperText = Get-Content -Raw -Encoding UTF8 -LiteralPath $wrapper
    if (-not $wrapperText.Contains($correctedMarker) -or -not $wrapperText.Contains('@($lines -ceq $r2Marker).Count -eq 1')) {
        throw 'The corrected exact R2 marker check is required.'
    }
    if (-not $Passfile) { $Passfile = $env:PGPASSFILE }
    if (-not $Passfile) { $Passfile = Join-Path $env:LOCALAPPDATA 'LabBooking/PostgreSQL17/pgpass.conf' }
    $arguments = @{ ExecutedBy = $operator; Passfile = $Passfile }
    if ($Chrome) { $arguments.Chrome = $Chrome }
    & $wrapper @arguments

    $created = @(Find-FullRun)
    if ($created.Count -ne 1) { throw 'Expected one new full-suite evidence directory. Run verification serially.' }
    $fullRun = $created[0].Name
    $raw = Join-Path $created[0].FullName 'raw.txt'
    $summary = @(Get-Content -LiteralPath (Join-Path $created[0].FullName 'run-summary.txt') -Encoding UTF8)
    $lines = @(Get-Content -LiteralPath $raw)
    if (@($summary -ceq 'verification exit=0').Count -ne 1 -or
        @($summary -ceq 'result=PASS: 67 baseline + 1 new Django tests; 8 prior + 2 R1 probes; 6 T-03 denial records.').Count -ne 1 -or
        @($summary -ceq "raw-log-sha256=$((Get-FileHash -LiteralPath $raw).Hash)").Count -ne 1 -or
        @($lines -match '^Ran 68 tests in ').Count -ne 1 -or @($lines -ceq 'OK').Count -ne 1 -or
        @($lines -match '^Exit -?\d+$').Count -ne 5 -or @($lines -ceq 'Exit 0').Count -ne 5) {
        throw 'Full-suite result does not establish 68 Django tests and 10 real probes.'
    }

    # The shared entry already verified the original Python and protected passfile.
    $env:LAB_BOOKING_DB_MODE = 'test'
    $env:DJANGO_SETTINGS_MODULE = 'lab_booking.settings'
    $env:PGPASSFILE = $Passfile
    $env:LAB_BOOKING_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
    $env:PYTHONIOENCODING = 'utf-8'
    [Console]::OutputEncoding = $utf8
    $q3Exit = Invoke-Q3
    [IO.File]::AppendAllText($q3Log, "Exit $q3Exit" + [Environment]::NewLine, $utf8)
    $q3 = @(Get-Content -LiteralPath $q3Log -Encoding UTF8)
    $proof = '^Q-3 transport={0} before_sha256=([0-9a-f]{{64}}) after_sha256=\1$'
    if ($q3Exit -ne 0 -or @($q3 -match '^Ran 1 test in ').Count -ne 1 -or @($q3 -ceq 'OK').Count -ne 1 -or
        @($q3 -cmatch ($proof -f 'CRLF')).Count -ne 1 -or @($q3 -cmatch ($proof -f 'LF-equivalent')).Count -ne 1 -or
        @($q3 -ceq 'Q-3 stored CRLF preserved: 2 transport variants; identity and escaped detail verified.').Count -ne 1 -or
        @($q3 -ceq 'Q-3 cleanup: full equipment snapshot restored.').Count -ne 1) {
        throw 'Q-3 failed or lacks complete proof. Keep the exact output and distinguish data mismatch from an environment failure.'
    }
    $exit = 0
}
catch {
    $failure = $_.Exception.Message
}
finally {
    try {
        if ($before -ne 'NOT CAPTURED') {
            $after = Write-ReviewManifest 'after'
            if ($before -cne $after) { throw 'Reviewed source or test inputs changed during the run.' }
        }
        if ($fullRun -eq 'NOT CAPTURED') {
            $created = @(Find-FullRun)
            if ($created.Count -eq 1) { $fullRun = $created[0].Name }
        }
    }
    catch { $exit = 1; $failure += ' ' + $_.Exception.Message }
    foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process') }
    [Console]::OutputEncoding = $consoleEncoding
    $q3Hash = if (Test-Path -LiteralPath $q3Log) { (Get-FileHash -LiteralPath $q3Log).Hash } else { 'NOT CAPTURED' }
    $meaning = if ($exit -eq 0) { '68 Django + 10 PostgreSQL probes; separate Q-3 1 test with 2 cases.' } else { 'INCOMPLETE OR FAILED' }
    [IO.File]::WriteAllLines((Join-Path $out 'independent-summary.txt'), [string[]]@(
        "actual operator(s), as reported: $operator", 'mode: independent review rerun in ordinary PowerShell',
        'target: lab_booking_test@127.0.0.1:5433/test_lab_booking',
        "started=$started", ('ended=' + (Get-Date -Format o)),
        "full-suite-sibling-directory=$fullRun", 'Full-suite nested metadata uses its historical development-self-test label.',
        "before-manifest-sha256=$before", "after-manifest-sha256=$after", "q3-raw-sha256=$q3Hash",
        "q3-exit=$q3Exit", "verification-exit=$exit", "result=$meaning", $failure
    ), $utf8)
    Pop-Location
    Write-Host "Independent evidence: $out"
    Write-Host "Full-suite raw evidence (sibling): $fullRun"
}
if ($exit -ne 0) { throw 'Independent verification incomplete or failed. Preserve both evidence folders.' }
