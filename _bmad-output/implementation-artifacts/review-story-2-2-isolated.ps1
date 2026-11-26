[CmdletBinding()]
param(
    [string]$EvidenceDirectory,
    [string]$Passfile,
    [string]$Chrome,
    [string]$Psql,
    [string]$OutputRoot
)

# Without -EvidenceDirectory, starts one new guarded isolation run in regular Windows PowerShell.
# With -EvidenceDirectory, audits an existing batch without executing Python, HTTP, or SQL.
$ErrorActionPreference = 'Stop'
$story22Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$story22Fresh = -not $EvidenceDirectory

function Assert-Story22([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Get-Story22Hash([string]$Path) {
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

if ($story22Fresh) {
    # Keep fresh evidence separate from the original developer batch. Do not run other verifiers in parallel.
    if (-not $OutputRoot) { $OutputRoot = $PSScriptRoot }
    $reviewBatch = Join-Path $OutputRoot ('story-2-2-review-run-' + [guid]::NewGuid().ToString('N'))
    $reviewBatch = (New-Item -ItemType Directory -Path $reviewBatch).FullName
    Write-Host "Independent evidence parent: $reviewBatch"
    $runnerArgs = @{ OutputRoot = $reviewBatch }
    foreach ($arg in @('Passfile','Chrome','Psql')) {
        if ($PSBoundParameters.ContainsKey($arg)) { $runnerArgs[$arg] = $PSBoundParameters[$arg] }
    }
    $runOutput = @(& (Join-Path $PSScriptRoot 'verify-story-2-2.ps1') @runnerArgs)
    Assert-Story22 (@($runOutput | Where-Object { $_ -ceq 'STORY22_VERIFICATION_OK' }).Count -eq 1) 'Missing or duplicated runner success marker.'
    $directories = @(Get-ChildItem -LiteralPath $reviewBatch -Directory -Filter 'story-2-2-run-*')
    Assert-Story22 ($directories.Count -eq 1) 'Expected exactly one new isolated run.'
    $EvidenceDirectory = $directories[0].FullName
}

$evidence = (Resolve-Path -LiteralPath $EvidenceDirectory).Path
function Read-Story22Evidence([string]$Name) {
    Get-Content -LiteralPath (Join-Path $evidence $Name) -Encoding UTF8
}
function Assert-Story22Marker([string]$File, [string]$Marker) {
    Assert-Story22 (@((Read-Story22Evidence $File) | Where-Object { $_ -ceq $Marker }).Count -eq 1) "Unexpected marker in $File."
}

$stages = @(Read-Story22Evidence 'stages.txt')
$stageNames = 'powershell-parse','verification-locks','preflight','baseline-before','check','migration-drift','regression','baseline-after-regression','independent','baseline-after-independent','complete'
Assert-Story22 ($stages.Count -eq $stageNames.Count) 'Stage count is not 11.'
for ($i = 0; $i -lt $stageNames.Count; $i++) {
    Assert-Story22 ($stages[$i] -cmatch ('^\S+ ' + [regex]::Escape($stageNames[$i]) + ' exit=0$')) "Unexpected stage: $($stages[$i])."
}
Assert-Story22 (-not (Test-Path -LiteralPath (Join-Path $evidence 'failure.txt'))) 'The runner recorded a failure.'
Assert-Story22Marker 'preflight.txt' 'python=Python 3.13.17 django=5.2.19'
Assert-Story22Marker 'preflight.txt' 'isolated_identity=test_lab_booking|lab_booking_test|127.0.0.1|5433|170012'
Assert-Story22Marker 'preflight.txt' 'STORY21_PREFLIGHT_OK'
Assert-Story22Marker 'check.stdout.txt' 'System check identified no issues (0 silenced).'
Assert-Story22Marker 'migration-drift.stdout.txt' 'No changes detected'
Assert-Story22Marker 'regression.stdout.txt' 'Found 103 test(s).'
Assert-Story22Marker 'regression.stderr.txt' 'OK'
Assert-Story22Marker 'independent.stdout.txt' 'STORY22_PROBE_OK cases=21'
Assert-Story22 ((Get-Item -LiteralPath (Join-Path $evidence 'independent.stderr.txt')).Length -eq 0) 'The probe wrote to stderr.'

$regression = @(Read-Story22Evidence 'regression.stderr.txt')
$tests = @(foreach ($line in $regression) {
    if ($line -cmatch '^(test_\S+ \([\w.]+\))') { $Matches[1] }
})
Assert-Story22 ($tests.Count -eq 103 -and @($tests | Sort-Object -Unique).Count -eq 103) 'Django test names are not 103 distinct cases.'
Assert-Story22 (@($tests | Where-Object { $_ -cmatch '\(reservations\.test_occupancy\.' }).Count -eq 12) 'Expected 12 named occupancy regression cases.'
Assert-Story22 (@($regression | Where-Object { $_ -cmatch '^ok$|\.\.\. ok$' }).Count -eq 103 -and
    @($regression | Where-Object { $_ -cmatch '^Ran 103 tests in ' }).Count -eq 1 -and
    @($regression | Where-Object { $_ -cmatch '\.\.\. (skipped|FAIL|ERROR)|^FAILED' }).Count -eq 0) 'Django run did not record 103 successes and zero skips.'

$baselineHash = Get-Story22Hash (Join-Path $evidence 'baseline-before.json')
foreach ($snapshot in @('baseline-after-regression.json','baseline-after-independent.json')) {
    Assert-Story22 ((Get-Story22Hash (Join-Path $evidence $snapshot)) -ceq $baselineHash) "Baseline differs in $snapshot."
}
$baseline = (Read-Story22Evidence 'baseline-before.json') | ConvertFrom-Json
$records = @(Read-Story22Evidence 'independent.jsonl' | ForEach-Object { ConvertFrom-Json $_ })
Assert-Story22 ($records.Count -eq 23) 'Expected 21 raw scenarios plus opening identity and cleanup records.'
$identity = $records[0].database
Assert-Story22 ($identity.Count -eq 10 -and ($identity[0..6] -join '|') -ceq 'test_lab_booking|lab_booking_test|lab_booking_test|127.0.0.1|5433|170012|read committed' -and
    $identity[7] -eq $false -and $identity[8] -eq $false) 'Wrong PostgreSQL identity, isolation, or role access.'
$expectedCases = 'role-student','role-teacher','role-admin','anonymous','inactive-session','invalid-date','missing-equipment','no-pending','empty','revoked-while-waiting','frozen-legal','frozen-due','real-start-boundary','real-post-decision-boundary','submit-first','query-first','stale-result-conflict','history-second','commit-rejected','commit-disconnected','confirmation-lost'
Assert-Story22 (($records[1..21].case -join '|') -ceq ($expectedCases -join '|')) 'Unexpected probe names, count or order.'

$close = $records[-1]
Assert-Story22 ($close.cleanup -eq $true -and $baseline.schema[0].Count -eq 12 -and $baseline.schema[1].Count -eq 19) 'Cleanup marker or baseline table/migration counts are invalid.'
$beforeSchema = ConvertTo-Json -InputObject $records[0].schema_before -Depth 10 -Compress
$afterSchema = ConvertTo-Json -InputObject $close.schema_after -Depth 10 -Compress
$baselineSchema = ConvertTo-Json -InputObject $baseline.schema -Depth 10 -Compress
Assert-Story22 ($beforeSchema -ceq $afterSchema -and $beforeSchema -ceq $baselineSchema) 'Probe schema/owner/migration inventory differs.'
foreach ($table in @('accounts_user','django_session','equipment_equipment','reservations_reservation','audit_operationhistory')) {
    $head = $records[0].before.$table
    $tail = $close.after.$table
    $base = $baseline.rows.$table
    Assert-Story22 ($null -ne $head -and $null -ne $tail -and $null -ne $base -and
        $head.count -eq 0 -and $tail.count -eq 0 -and $base.count -eq 0 -and
        $head.sha256 -ceq $tail.sha256 -and $head.sha256 -ceq $base.sha256) "Fixture cleanup differs for $table."
}

$manifestHash = Get-Story22Hash (Join-Path $evidence 'before.sha256')
Assert-Story22 ((Get-Story22Hash (Join-Path $evidence 'after.sha256')) -ceq $manifestHash) 'The before/after input manifests differ.'
$paths = @{}
foreach ($line in @(Read-Story22Evidence 'before.sha256')) {
    Assert-Story22 ($line -cmatch '^(?<sha>[0-9A-F]{64})  (?<file>.+)$') 'Malformed manifest line.'
    $rel = $Matches.file
    $sha = $Matches.sha
    Assert-Story22 (-not $paths.ContainsKey($rel)) "Duplicate manifest path: $rel."
    $paths[$rel] = $sha
    if ($story22Fresh) {
        $absolute = [IO.Path]::GetFullPath((Join-Path $story22Root $rel))
        Assert-Story22 ($absolute.StartsWith($story22Root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) "Manifest path is outside the repository: $rel."
        Assert-Story22 ((Get-Story22Hash $absolute) -ceq $sha) "Current input differs from the fresh manifest: $rel."
    }
}

if ($story22Fresh) {
    $expectedPaths = @('manage.py','requirements.txt','_bmad-output/planning-artifacts/epics.md',
        '_bmad-output/implementation-artifacts/spec-2-2-query-equipment-occupancy.md',
        '_bmad-output/implementation-artifacts/story-2-2-checkpoint-1.md',
        '_bmad-output/implementation-artifacts/preflight-story-2-1.ps1',
        '_bmad-output/implementation-artifacts/verify-story-2-2.ps1')
    foreach ($folder in @('accounts','equipment','lab_booking','audit','reservations')) {
        $expectedPaths += Get-ChildItem -LiteralPath (Join-Path $story22Root $folder) -File -Recurse |
            Where-Object { $_.Extension -in '.py','.html' } |
            ForEach-Object { $_.FullName.Substring($story22Root.Length + 1).Replace('\','/') }
    }
    Assert-Story22 (@(Compare-Object @($expectedPaths | Sort-Object -Unique) @($paths.Keys)).Count -eq 0) 'Current input file set differs from the run manifest.'
}
$fail = $records | Where-Object { $_.case -ceq 'history-second' }
Assert-Story22 ($fail.result.response.status -eq 503 -and $fail.result.server.commits -eq 0 -and
    $fail.result.server.history_inserts -eq 2 -and $fail.result.server.sqlstate -ceq '23514' -and -not $fail.retry) 'Unexpected second history failure outcome.'
foreach ($key in @('device','rows','effective','history')) {
    Assert-Story22 ((ConvertTo-Json -InputObject $fail.before.$key -Depth 15 -Compress) -ceq
        (ConvertTo-Json -InputObject $fail.after.$key -Depth 15 -Compress)) "Atomic rollback check differs for $key."
}
$historyInserts = @($fail.result.server.statements | Where-Object { $_.sql -cmatch '^INSERT INTO "audit_operationhistory"' })
if ($historyInserts.Count -eq 2 -and $historyInserts[1].bind[0] -ceq 'reservation') {
    Write-Output 'Fault trace limitation: history-second bind is captured before injection. Rollback uses SQLSTATE and independent read-back.'
}
Write-Output "Evidence directory: $evidence"
Write-Output "Django=103/103 skipped=0 probes=21/21 stages=11 inputs=$($paths.Count) baseline_sha256=$baselineHash"
Write-Output "Probe SHA256: $(Get-Story22Hash (Join-Path $evidence 'independent.jsonl'))"
if ($story22Fresh) {
    Write-Output 'STORY22_INDEPENDENT_REVIEW_RUN_OK'
} else {
    Write-Output 'STORY22_ARCHIVE_AUDIT_OK'
}
