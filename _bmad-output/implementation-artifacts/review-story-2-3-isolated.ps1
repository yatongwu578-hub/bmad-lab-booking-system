[CmdletBinding()]
param(
    [string]$EvidenceDirectory,
    [string]$Passfile,
    [string]$Chrome,
    [string]$Psql,
    [string]$OutputRoot = 'F:\softwork\outputs'
)

# Ordinary Windows PowerShell. No -EvidenceDirectory: one fresh isolation run.
# With -EvidenceDirectory: local files only, never executes the test runner or connects to a database.
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$development = Join-Path $PSScriptRoot 'story-2-3-run-20261127-111101-492-41d9eb74'
$ledger = '_bmad-output/implementation-artifacts/story-2-2-run-20261126-224427-552-98c04aee/regression.stderr.txt'
$spec = '_bmad-output/implementation-artifacts/spec-2-3-query-own-reservations.md'
$fresh = -not $EvidenceDirectory
function Assert-Review([bool]$Ok, [string]$Message) { if (-not $Ok) { throw $Message } }
function Hash-Review([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash }
function Read-Review([string]$Name) { Get-Content -LiteralPath (Join-Path $evidence $Name) -Encoding UTF8 }
function Mark-Review([string]$Name, [string]$Marker) {
    Assert-Review (@(Read-Review $Name | Where-Object { $_ -ceq $Marker }).Count -eq 1) "Invalid marker in $Name."
}
function Compact-Review($Value) { ConvertTo-Json -InputObject $Value -Depth 24 -Compress }
function Get-ReviewIds([string[]]$Lines) {
    foreach ($line in $Lines) {
        if ($line -cmatch '^test_\w+ \(([a-zA-Z_][a-zA-Z0-9_.]+)\) \.\.\. ok$') { $Matches[1] }
    }
}
function Get-ReviewManifest([string]$Path, [int]$Count) {
    $map = @{}
    foreach ($line in (Get-Content -LiteralPath $Path -Encoding UTF8)) {
        Assert-Review ($line -cmatch '^(?<hash>[0-9A-F]{64})  (?<path>[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*)$') "Malformed manifest: $Path"
        $rel = $Matches.path
        Assert-Review (-not $map.ContainsKey($rel) -and $rel -notmatch '(?:^|/)\.{1,2}(?:/|$)') "Duplicate or unsafe manifest path: $rel"
        $map[$rel] = $Matches.hash
    }
    Assert-Review ($map.Count -eq $Count) "Unexpected manifest count: $Path"
    return $map
}
function Assert-ReviewInputs($Manifest, [string]$ArchivedSpec) {
    $expected = @('manage.py','requirements.txt','_bmad-output/planning-artifacts/epics.md',
        $spec,$ledger,'_bmad-output/implementation-artifacts/story-2-3-checkpoint-1.md',
        '_bmad-output/implementation-artifacts/preflight-story-2-1.ps1',
        '_bmad-output/implementation-artifacts/verify-story-2-3.ps1')
    foreach ($module in 'accounts','equipment','lab_booking','audit','reservations') {
        $expected += Get-ChildItem -LiteralPath (Join-Path $repo $module) -File -Recurse |
            Where-Object { $_.Extension -in '.py','.html' } |
            ForEach-Object { $_.FullName.Substring($repo.Length + 1).Replace('\','/') }
    }
    Assert-Review (@(Compare-Object @($expected | Sort-Object -Unique) @($Manifest.Keys) -CaseSensitive).Count -eq 0) 'Input file set differs.'
    foreach ($rel in $Manifest.Keys) {
        $file = Join-Path $repo $rel
        if ($ArchivedSpec -and $rel -ceq $spec) { $file = $ArchivedSpec }
        Assert-Review ((Hash-Review $file) -ceq $Manifest[$rel]) "Input differs from reviewed manifest: $rel"
    }
}

$reviewed = Get-ReviewManifest (Join-Path $development 'before.sha256') 83
if ($fresh) {
    # Check the reviewed code before starting any work. The review-state spec may have advanced since the development batch.
    Assert-ReviewInputs $reviewed (Join-Path $development 'spec-at-run.md')
    $parent = Join-Path (Resolve-Path -LiteralPath $OutputRoot).Path ('story-2-3-review-run-' + [guid]::NewGuid().ToString('N'))
    $parent = (New-Item -ItemType Directory -Path $parent).FullName
    Write-Host "New independent evidence parent: $parent"
    $arguments = @{ OutputRoot = $parent }
    foreach ($name in 'Passfile','Chrome','Psql') {
        if ($PSBoundParameters.ContainsKey($name)) { $arguments[$name] = $PSBoundParameters[$name] }
    }
    $out = @(& (Join-Path $PSScriptRoot 'verify-story-2-3.ps1') @arguments)
    $out | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $parent 'runner.stdout.txt')
    Assert-Review (@($out | Where-Object { $_ -ceq 'STORY23_VERIFICATION_OK' }).Count -eq 1) 'Runner did not complete.'
    $runs = @(Get-ChildItem -LiteralPath $parent -Directory -Filter 'story-2-3-run-*')
    Assert-Review ($runs.Count -eq 1) 'Expected exactly one new isolated run.'
    $EvidenceDirectory = $runs[0].FullName
}

$evidence = (Resolve-Path -LiteralPath $EvidenceDirectory).Path
$stages = @(Read-Review 'stages.txt')
$names = 'verification-locks','preflight','baseline-before','check','migration-drift','regression',
    'baseline-after-regression','independent','baseline-after-independent','complete'
Assert-Review ($stages.Count -eq $names.Count) 'Expected 10 stages.'
for ($i = 0; $i -lt $names.Count; $i++) {
    Assert-Review ($stages[$i] -cmatch ('^\S+ ' + [regex]::Escape($names[$i]) + ' exit=0$')) "Invalid stage: $($stages[$i])"
}
Assert-Review (-not (Test-Path -LiteralPath (Join-Path $evidence 'failure.txt'))) 'Runner failure receipt present.'
Mark-Review 'preflight.stdout.txt' 'python=Python 3.13.17 django=5.2.19'
Mark-Review 'preflight.stdout.txt' 'isolated_identity=test_lab_booking|lab_booking_test|127.0.0.1|5433|170012'
Mark-Review 'preflight.stdout.txt' 'STORY21_PREFLIGHT_OK'
Mark-Review 'check.stdout.txt' 'System check identified no issues (0 silenced).'
Mark-Review 'migration-drift.stdout.txt' 'No changes detected'
Mark-Review 'regression.stdout.txt' 'Found 113 test(s).'
Mark-Review 'regression.stderr.txt' 'OK'
Mark-Review 'independent.stdout.txt' 'STORY23_PROBE_OK cases=15'
Assert-Review ((Get-Item -LiteralPath (Join-Path $evidence 'independent.stderr.txt')).Length -eq 0) 'Probe stderr is not empty.'

$regression = @(Read-Review 'regression.stderr.txt')
$prior = @(Get-ReviewIds @(Get-Content -LiteralPath (Join-Path $repo $ledger) -Encoding UTF8))
$tests = @(Get-ReviewIds $regression)
Assert-Review ($prior.Count -eq 103 -and @($prior | Sort-Object -Unique).Count -eq 103 -and
    $tests.Count -eq 113 -and @($tests | Sort-Object -Unique).Count -eq 113 -and
    @($prior | Where-Object { $_ -cnotin $tests }).Count -eq 0 -and
    @($tests | Where-Object { $_ -cmatch '^reservations\.test_own_reservations\.' }).Count -eq 10 -and
    ($tests -join '|') -ceq ((Read-Review 'passed-tests.txt') -join '|') -and
    @($regression | Where-Object { $_ -cmatch '^Ran 113 tests in ' }).Count -eq 1 -and
    @($regression | Where-Object { $_ -cmatch '\.\.\. (skipped|FAIL|ERROR)|^FAILED' }).Count -eq 0) 'Django ledger differs.'

$manifestPath = Join-Path $evidence 'before.sha256'
$manifest = Get-ReviewManifest $manifestPath 83
Assert-Review ((Hash-Review $manifestPath) -ceq (Hash-Review (Join-Path $evidence 'after.sha256'))) 'Run input hashes differ.'
if ($fresh) {
    Assert-ReviewInputs $manifest ''
    foreach ($rel in $reviewed.Keys) {
        if ($rel -cne $spec) { Assert-Review ($reviewed[$rel] -ceq $manifest[$rel]) "Reviewed input changed: $rel" }
    }
} elseif (Test-Path -LiteralPath (Join-Path $evidence 'archive.sha256') -PathType Leaf) {
    $archive = Get-ReviewManifest (Join-Path $evidence 'archive.sha256') 26
    $files = @(Get-ChildItem -LiteralPath $evidence -File | Where-Object { $_.Name -cnotin 'README.md','archive.sha256' })
    Assert-Review (@(Compare-Object @($files.Name) @($archive.Keys) -CaseSensitive).Count -eq 0) 'Archive file set differs.'
    foreach ($name in $archive.Keys) {
        Assert-Review ((Hash-Review (Join-Path $evidence $name)) -ceq $archive[$name]) "Archive hash differs: $name"
    }
    Assert-ReviewInputs $manifest (Join-Path $evidence 'spec-at-run.md')
}

$baseHash = Hash-Review (Join-Path $evidence 'baseline-before.json')
foreach ($stage in 'baseline-before','baseline-after-regression','baseline-after-independent') {
    Mark-Review "$stage.stdout.txt" 'STORY21_PROBE_OK baseline'
    Assert-Review ((Hash-Review (Join-Path $evidence "$stage.json")) -ceq $baseHash) "Database baseline differs: $stage"
}
$base = (Read-Review 'baseline-before.json') | ConvertFrom-Json
$raw = @(Read-Review 'independent.jsonl' | ForEach-Object { ConvertFrom-Json $_ })
$caseNames = 'history-navigation','current-equipment','projected-reasons','ordered-scope','no-pending','permissions',
    'revoked-while-waiting','frozen-new-row','crossed-start','submit-first','query-first',
    'history-second','commit-rejected','commit-disconnected','confirmation-lost'
Assert-Review ($raw.Count -eq 17 -and ($raw[1..15].case -join '|') -ceq ($caseNames -join '|')) 'Expected 15 named probe results.'
$id = $raw[0].database
Assert-Review ($id.Count -eq 10 -and ($id[0..6] -join '|') -ceq 'test_lab_booking|lab_booking_test|lab_booking_test|127.0.0.1|5433|170012|read committed' -and
    $id[7] -is [bool] -and -not $id[7] -and $id[8] -is [bool] -and -not $id[8] -and [int]$id[9] -gt 0) 'Unverified test role or database.'
Assert-Review ($raw[-1].cleanup -eq $true -and $base.schema[0].Count -eq 12 -and $base.schema[1].Count -eq 19 -and
    (Compact-Review $raw[0].schema_before) -ceq (Compact-Review $base.schema) -and
    (Compact-Review $raw[-1].schema_after) -ceq (Compact-Review $base.schema)) 'Cleanup schema inventory differs.'
foreach ($table in 'accounts_user','django_session','equipment_equipment','reservations_reservation','audit_operationhistory') {
    $head = $raw[0].before.$table
    $tail = $raw[-1].after.$table
    $baseTable = $base.rows.$table
    Assert-Review ($null -ne $head -and $null -ne $tail -and $null -ne $baseTable -and
        $head.count -eq 0 -and $tail.count -eq 0 -and $baseTable.count -eq 0 -and
        $head.sha256 -cmatch '^[0-9a-f]{64}$' -and
        $head.sha256 -ceq $tail.sha256 -and $head.sha256 -ceq $baseTable.sha256) "Cleanup differs: $table."
}

$c = @{}
foreach ($item in $raw[1..15]) { $c[$item.case] = $item }
$denied = $c.permissions.denied
Assert-Review ($denied.Count -eq 12 -and ($denied.response.status -join ',') -ceq '302,302,403,403,302,302,404,404,404,404,405,405' -and
    $denied[6].server.principal.role -ceq 'student' -and $denied[8].server.principal.role -ceq 'teacher' -and
    (Compact-Review $c.permissions.before.rows) -ceq (Compact-Review $c.permissions.after.rows) -and
    (Compact-Review $c.permissions.before.history) -ceq (Compact-Review $c.permissions.after.history) -and
    (Compact-Review $c.permissions.before.effective) -ceq (Compact-Review $c.permissions.after.effective) -and
    (Compact-Review $c.permissions.before.device) -ceq (Compact-Review $c.permissions.after.device)) 'Unauthorized before/after receipts differ.'
foreach ($i in 6,7,8,9) {
    $entry = $denied[$i]
    $trace = $entry.server
    $business = @($trace.statements | Where-Object { $_.sql -notmatch 'FROM "accounts_user"' })
    $pk = [long]([regex]::Match($entry.path,'^/reservations/([0-9]+)/result/$').Groups[1].Value)
    Assert-Review ($business.Count -eq 1 -and $business[0].sql -cmatch '^SELECT .*FROM "reservations_reservation".*"applicant_id" = %s.*"id" = %s' -and
        $business[0].sql -cnotmatch 'FOR UPDATE|JOIN|audit_operationhistory' -and $business[0].bind.Count -eq 2 -and
        $business[0].bind[0] -eq $trace.principal.user_id -and $business[0].bind[1] -eq $pk -and @($trace.decisions).Count -eq 0) 'Denied route accessed more than the authorized candidate check.'
}
Assert-Review ($denied[6].response.body -ceq $denied[7].response.body -and $denied[8].response.body -ceq $denied[9].response.body) 'Foreign and missing responses differ.'
$foreignOwner = @($c.permissions.before.rows | Where-Object { $_.id -eq $denied[6].server.statements[0].bind[1] })
Assert-Review ($foreignOwner.Count -eq 1 -and $foreignOwner[0].applicant_id -ne $denied[6].server.principal.user_id) 'Same-role ownership contrast missing.'

$ordered = $c['ordered-scope']
$server = $ordered.result.server
$locks = @($server.statements | Where-Object { $_.sql -cmatch 'FOR UPDATE' })
$clock = @($server.statements | Where-Object { $_.sql -ceq 'SELECT clock_timestamp() AS decision_at' })
$updates = @($server.statements | Where-Object { $_.sql -cmatch '^UPDATE "reservations_reservation"' })
$histories = @($server.statements | Where-Object { $_.sql -cmatch '^INSERT INTO "audit_operationhistory"' })
Assert-Review ($locks.Count -eq 2 -and $locks[0].bind[0] -eq $ordered.before[0].device.id -and
    $locks[1].bind[0] -eq $ordered.before[1].device.id -and $locks[0].bind[0] -lt $locks[1].bind[0] -and
    $clock.Count -eq 1 -and $server.decisions.Count -eq 1 -and $updates.Count -eq 3 -and $histories.Count -eq 3 -and
    $server.commits.Count -eq 1 -and $ordered.blockers.Count -gt 0) 'Device scope, unique clock or atomic write count differs.'
for ($i = 0; $i -lt $updates.Count; $i++) {
    Assert-Review ($locks[1].at_ns -lt $clock[0].at_ns -and $clock[0].at_ns -lt $updates[$i].at_ns -and
        $updates[$i].at_ns -lt $histories[$i].at_ns -and $histories[$i].at_ns -lt $server.commits[0]) 'Clock/write/history/commit order differs.'
}
$cross = $c['crossed-start']
Assert-Review ($cross.before.effective.Count -eq 1 -and @($cross.after.effective).Count -eq 0 -and
    $cross.after.rows[0].status -ceq 'expired' -and $cross.after.history.Count -eq 1 -and
    [DateTimeOffset]::Parse($cross.waiting_at) -lt [DateTimeOffset]::Parse($cross.start) -and
    [DateTimeOffset]::Parse($cross.start) -le [DateTimeOffset]::Parse($cross.result.server.decisions[0])) 'Cross-start occupancy transition not demonstrated.'

foreach ($name in 'history-second','commit-rejected','commit-disconnected','confirmation-lost') {
    $fault = $c[$name]
    Assert-Review ($fault.result.response.status -eq 503 -and $fault.retry -eq $false -and
        $fault.result.response.body -cnotmatch '<tbody>') "Fault passed as successful: $name"
    if ($name -in 'history-second','commit-rejected') {
        Assert-Review ($fault.result.response.body -match '\u5DF2\u56DE\u6EDA') "Confirmed rollback message missing: $name"
    } else {
        Assert-Review ($fault.result.response.body -match '\u7ED3\u679C\u5F85\u6838\u67E5' -and
            $fault.result.response.body -notmatch '\u5DF2\u56DE\u6EDA') "Unknown outcome presented as known: $name"
    }
    if ($name -ne 'confirmation-lost') {
        for ($i = 0; $i -lt $fault.before.Count; $i++) {
            foreach ($field in 'device','rows','history','effective') {
                Assert-Review ((Compact-Review $fault.before[$i].$field) -ceq (Compact-Review $fault.after[$i].$field)) "Unexpected persisted state: $name"
            }
        }
    } else {
        Assert-Review ($fault.driver_confirmation_simulated -eq $true -and $fault.result.server.commit_return_ns -gt 0 -and
            $fault.after.Count -eq 2 -and @($fault.after.rows | Where-Object { $_.status -ceq 'expired' }).Count -eq 2 -and
            @($fault.after.history).Count -eq 2) 'Simulated confirmation loss did not preserve the real commit.'
    }
}
$inserts = @($c['history-second'].result.server.statements | Where-Object { $_.sql -cmatch '^INSERT INTO "audit_operationhistory"' })
Assert-Review ($inserts.Count -eq 2 -and $inserts[1].bind[0] -ceq 'invalid' -and
    $c['history-second'].result.server.sqlstate -ceq '23514' -and @($c['history-second'].result.server.commits).Count -eq 0 -and
    $c['commit-rejected'].result.server.sqlstate -ceq '23505') 'Actual history injection or COMMIT rejection does not match.'

$summary = @(
    "Evidence directory: $evidence"
    "Django=113/113 skipped=0 probes=15/15 stages=10 inputs=83 baseline_sha256=$baseHash"
    "Probe SHA256: $(Hash-Review (Join-Path $evidence 'independent.jsonl'))"
)
if ($fresh) {
    $marker = 'STORY23_INDEPENDENT_REVIEW_RUN_OK'
    ($summary + $marker) | Set-Content -LiteralPath (Join-Path $parent 'review-audit.txt') -Encoding UTF8
} else {
    $marker = 'STORY23_ARCHIVE_AUDIT_OK'
}
$summary
$marker

