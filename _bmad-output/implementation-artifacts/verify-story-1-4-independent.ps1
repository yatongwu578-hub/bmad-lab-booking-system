[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$ExecutedBy,
    [string]$Passfile,
    [string]$Chrome,
    [switch]$SnapshotOnly
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$baseline = 'e200fee335536941e0705c112aefbf6751b244c3'
$harness = '_bmad-output/implementation-artifacts/verify-story-1-4.ps1'
$oldResults = '_bmad-output/implementation-artifacts/story-1-3-independent-recheck-output.txt'
$runId = (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$out = Join-Path ([IO.Path]::GetTempPath()) "story-1-4-independent-$runId"
New-Item -ItemType Directory -Path $out | Out-Null
$raw = Join-Path $out 'raw.txt'
$summary = Join-Path $out 'run-summary.txt'
$utf8 = [Text.UTF8Encoding]::new($false)

function Run-Git([string[]]$Arguments) {
    $result = & git -C $root @Arguments
    if ($LASTEXITCODE -ne 0) { throw ('Git failed: ' + ($Arguments -join ' ')) }
    $result
}

function Record-Snapshot([string]$Name) {
    $head = Run-Git -Arguments @('rev-parse', 'HEAD')
    if ($head -cne $baseline) { throw "Unexpected HEAD: $head" }
    $paths = @(Run-Git -Arguments @('ls-files', '--cached', '--others', '--exclude-standard', '--',
        'manage.py', 'requirements.txt', 'accounts', 'equipment', 'lab_booking', $harness, $oldResults))
    $paths += '_bmad-output/implementation-artifacts/verify-story-1-4-independent.ps1'
    $paths = @($paths | Sort-Object -Unique)
    foreach ($required in @('equipment/test_edit.py',
            'equipment/management/commands/verify_equipment_edit_transactions.py', $harness, $oldResults)) {
        if ($required -notin $paths) { throw "Missing verification input: $required" }
    }
    $rows = @("head=$head", "story-1.3-baseline=$baseline")
    foreach ($path in $paths) {
        $hash = (Get-FileHash -LiteralPath (Join-Path $root $path) -Algorithm SHA256).Hash
        $rows += "$hash  $path"
    }
    $destination = Join-Path $out "$Name.sha256"
    [IO.File]::WriteAllLines($destination, [string[]]$rows, $utf8)
    (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
}

function Get-PassingTestIds([string]$Path) {
    $pattern = '^test_\w+ \((?<id>[\w.]+)\)\s+\.\.\.\s+ok\s*$'
    foreach ($line in (Get-Content -LiteralPath $Path)) {
        if ($line -match $pattern) { $Matches.id }
    }
}

Write-Host "Evidence directory: $out"
$start = Get-Date -Format o
$before = 'NOT CAPTURED'
$after = 'NOT CAPTURED'
$result = 'NOT RUN'
$verificationExit = 1
$errorText = ''
try {
    $before = Record-Snapshot 'before'
    if ($SnapshotOnly) {
        $result = 'SNAPSHOT ONLY. NO DJANGO OR POSTGRESQL EXECUTION.'
    }
    else {
        $arguments = @{ LogPath = $raw }
        if ($Passfile) { $arguments.Passfile = $Passfile }
        if ($Chrome) { $arguments.Chrome = $Chrome }
        # The unchanged harness pins test mode, calls the original venv, and records each command exit.
        & (Join-Path $root $harness) @arguments

        $lines = @(Get-Content -LiteralPath $raw)
        $exits = @($lines -match '^Exit -?\d+$')
        if ($exits.Count -ne 5 -or @($exits -ne 'Exit 0').Count -ne 0) {
            throw 'Expected five command exit codes, all zero. See raw.txt.'
        }
        $knownTests = @(Get-PassingTestIds (Join-Path $root $oldResults) | Sort-Object -Unique)
        $tested = @(Get-PassingTestIds $raw)
        $testedUnique = @($tested | Sort-Object -Unique)
        $added = @($testedUnique | Where-Object { $_ -notin $knownTests })
        $missing = @($knownTests | Where-Object { $_ -notin $testedUnique })
        if ($knownTests.Count -ne 55 -or $tested.Count -ne 67 -or $testedUnique.Count -ne 67 -or
            $missing.Count -ne 0 -or $added.Count -ne 12 -or
            @($added -notmatch '^equipment\.test_edit\.EquipmentEditTests\.').Count -ne 0 -or
            @($lines -match '^Ran 67 tests in ').Count -ne 1 -or @($lines -ceq 'OK').Count -ne 1) {
            throw 'Expected 55 preserved and 12 new passing test IDs, zero skips, and an exact OK summary.'
        }
        foreach ($role in @('anonymous', 'student', 'teacher')) {
            $code = if ($role -eq 'anonymous') { 302 } else { 403 }
            foreach ($verb in @('GET', 'POST')) {
                if (@($lines -match "^T-03 ${role} ${verb} ${code}\D").Count -ne 1) {
                    throw "Missing T-03 denial output: $role $verb"
                }
            }
        }
        if (@($lines -match 'admin GET 200.+POST 302').Count -ne 1 -or
            @($lines -match '^CSRF .+admin missing 403').Count -ne 1 -or
            @($lines -match '^CSRF .+admin mismatch 403').Count -ne 1) {
            throw 'Expected the authorized control and both CSRF denial records.'
        }
        foreach ($fault in @('write-rollback', 'commit-rejected', 'commit-pre-disconnect', 'commit-lost-ack')) {
            if (@($lines -match "^AC-8 ${fault} PID=").Count -ne 1) { throw "Missing AC-8 output: $fault" }
        }
        if (@($lines -match '^T-01 .*PID=\{').Count -ne 4 -or
            @($lines -match '^T-01 .*B=\d+').Count -ne 2 -or
            @($lines -match '^\u6E05\u7406\u901A\u8FC7').Count -ne 1 -or
            @($lines -match '^AC-6.+T-01 4/4.+AC-8.*4/4').Count -ne 1) {
            throw 'Expected four T-01 cases, two observed lock waits, verified cleanup, and the full eight-probe summary.'
        }
        $result = '67 passing test IDs, 8 successful probes with cleanup, 6 T-03 role denials. Review raw details.'
    }
    $verificationExit = 0
}
catch {
    $errorText = $_.Exception.Message
    $result = 'INCOMPLETE OR FAILED. Do not count missing results as passed.'
}
finally {
    try {
        $after = Record-Snapshot 'after'
        if ($before -cne $after) {
            $verificationExit = 1
            $result = 'SOURCE SNAPSHOTS DIFFER. Do not attribute these results to the reviewed code.'
        }
    }
    catch {
        $verificationExit = 1
        $errorText += ' After-snapshot error: ' + $_.Exception.Message
    }
    $rawHash = if (Test-Path -LiteralPath $raw -PathType Leaf) {
        (Get-FileHash -LiteralPath $raw -Algorithm SHA256).Hash
    } else { 'NO RAW LOG' }
    $commandExits = if ($rawHash -ne 'NO RAW LOG') {
        @(Get-Content -LiteralPath $raw | Where-Object { $_ -match '^Exit -?\d+$' }) -join ', '
    } else { 'NONE' }
    $runMode = if ($SnapshotOnly) { 'read-only snapshot; no application execution' } else {
        'local team terminal; not a Codex-executed database test'
    }
    [IO.File]::WriteAllLines($summary, [string[]]@(
        "actual operator(s), as reported: $ExecutedBy",
        "run mode: $runMode",
        'target: lab_booking_test@127.0.0.1:5433/test_lab_booking',
        "started=$start", ('ended=' + (Get-Date -Format o)),
        "before-manifest-sha256=$before", "after-manifest-sha256=$after", "raw-log-sha256=$rawHash",
        "recorded command exits=$commandExits", "verification exit=$verificationExit", "result=$result", $errorText
    ), $utf8)
    Write-Host "Summary: $summary"
}
if ($verificationExit -ne 0) { throw "Verification incomplete or failed. See $summary" }
