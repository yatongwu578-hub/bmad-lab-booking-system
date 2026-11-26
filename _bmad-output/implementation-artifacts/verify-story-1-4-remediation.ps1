[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateNotNullOrEmpty()][string]$ExecutedBy,
    [string]$Passfile,
    [string]$Chrome
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$patch = Join-Path $PSScriptRoot 'story-1-4-r1-r2-r7.patch'
$previousLog = Join-Path $PSScriptRoot 'story-1-4-verification-20261125-221855-930.txt'
$runDirectory = Join-Path $PSScriptRoot ('story-1-4-remediation-run-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Path $runDirectory -ErrorAction Stop | Out-Null
$raw = Join-Path $runDirectory 'raw.txt'
$summary = Join-Path $runDirectory 'run-summary.txt'
$utf8 = [Text.UTF8Encoding]::new($false)
$start = Get-Date -Format o

function Assert-Evidence([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

function Save-Manifest([string]$Phase) {
    $paths = @(git ls-files --cached --others --exclude-standard -- accounts equipment lab_booking manage.py requirements.txt)
    Assert-Evidence ($LASTEXITCODE -eq 0 -and $paths.Count -gt 0) 'Cannot enumerate the tested files.'
    $entries = foreach ($path in ($paths | Sort-Object -Unique)) {
        $hash = (Get-FileHash -LiteralPath (Join-Path $root $path) -Algorithm SHA256).Hash
        "$hash  $path"
    }
    $manifestPath = Join-Path $runDirectory "$Phase.sha256"
    [IO.File]::WriteAllLines($manifestPath, [string[]]$entries, $utf8)
    (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash
}

function Get-TestIds([string[]]$Lines) {
    foreach ($line in $Lines) {
        if ($line -match '^test_\w+ \(([\w.]+)\) \.\.\. ok$') { $Matches[1] }
    }
}

$before = 'NOT CAPTURED'
$after = 'NOT CAPTURED'
$patchHash = 'NOT CAPTURED'
$outcome = 'INCOMPLETE OR FAILED'
$failure = ''
$code = 1
Push-Location -LiteralPath $root
try {
    $patchText = Get-Content -LiteralPath $patch -Raw -Encoding UTF8
    $patchHash = (Get-FileHash -LiteralPath $patch -Algorithm SHA256).Hash
    $postimages = [regex]::Matches($patchText, '(?m)^diff --git a/([^ ]+) b/([^ \r\n]+)\r?\nindex [0-9a-f]+\.\.([0-9a-f]+) ')
    $allowedPaths = @('equipment/forms.py', 'equipment/services.py', 'equipment/test_edit.py',
        'equipment/management/commands/verify_equipment_edit_transactions.py')
    $diffHeaders = @($patchText -split '\r?\n' | Where-Object { $_ -match '^diff --git ' })
    $postimagePaths = @($postimages | ForEach-Object { $_.Groups[2].Value } | Sort-Object -Unique)
    Assert-Evidence ($postimages.Count -eq 4 -and $diffHeaders.Count -eq 4 -and $postimagePaths.Count -eq 4) 'The remediation patch must cover only four expected files.'
    foreach ($entry in $postimages) {
        $path = $entry.Groups[2].Value
        Assert-Evidence ($path -in $allowedPaths -and $path -ceq $entry.Groups[1].Value) 'Unexpected patch path.'
        $actual = git hash-object --no-filters -- $path
        Assert-Evidence ($LASTEXITCODE -eq 0 -and $actual -and $actual.StartsWith($entry.Groups[3].Value)) "Apply the exact incremental patch first: $path"
    }
    $before = Save-Manifest 'before'
    $arguments = @{ LogPath = $raw }
    if ($Passfile) { $arguments.Passfile = $Passfile }
    if ($Chrome) { $arguments.Chrome = $Chrome }
    # Reuse the guarded test target, original venv, Chrome prerequisite and exit capture.
    & (Join-Path $PSScriptRoot 'verify-story-1-4.ps1') @arguments

    $lines = @(Get-Content -LiteralPath $raw)
    $exits = @($lines -match '^Exit -?\d+$')
    Assert-Evidence ($exits.Count -eq 5 -and @($exits -ne 'Exit 0').Count -eq 0) 'Expected all five commands to exit zero.'
    $previousLines = @(Get-Content -LiteralPath $previousLog)
    $baseline = @(Get-TestIds $previousLines | Sort-Object -Unique)
    $tested = @(Get-TestIds $lines)
    $found = @($tested | Sort-Object -Unique)
    $added = @($found | Where-Object { $_ -notin $baseline })
    $expectedAdded = @(Select-String -LiteralPath 'equipment/test_edit.py' -Pattern '^    def (test_r[127]_\w+)\(self\)' | ForEach-Object {
        'equipment.test_edit.EquipmentEditTests.' + $_.Matches[0].Groups[1].Value
    })
    $skips = @($lines -match '\.\.\. (skipped|FAIL|ERROR|expected failure|unexpected success)')
    Assert-Evidence ($baseline.Count -eq 67 -and $expectedAdded.Count -ge 1 -and
        $tested.Count -eq $found.Count -and $found.Count -eq (67 + $expectedAdded.Count) -and
        @($baseline | Where-Object { $_ -notin $found }).Count -eq 0 -and
        @($expectedAdded | Where-Object { $_ -notin $added }).Count -eq 0 -and
        @($lines -match "^Ran $($found.Count) tests in ").Count -eq 1 -and
        @($lines -ceq 'OK').Count -eq 1 -and $skips.Count -eq 0) 'Regression/new-test coverage or zero-skip check failed.'

    $records = @($lines -match '^T-03 record ')
    Assert-Evidence ($records.Count -eq 6) 'Expected six structured denial records.'
    $cases = @($records | ForEach-Object { $_.Substring('T-03 record '.Length) | ConvertFrom-Json })
    foreach ($role in @('anonymous', 'student', 'teacher')) {
        $expected = if ($role -eq 'anonymous') { 302 } else { 403 }
        foreach ($method in @('GET', 'POST')) {
            $matchesCase = @($cases | Where-Object { $_.role -ceq $role -and $_.method -ceq $method })
            Assert-Evidence ($matchesCase.Count -eq 1) "Missing T-03 record: $role $method"
            $case = $matchesCase[0]
            $requestKeys = @($case.request.PSObject.Properties | ForEach-Object { $_.Name })
            $validRequest = if ($method -eq 'GET') { $requestKeys.Count -eq 0 } else {
                $requestKeys.Count -eq 5 -and @($requestKeys | Where-Object { $_ -notin @('name', 'category', 'location', 'description', 'csrf') }).Count -eq 0 -and
                    $case.request.csrf -ceq 'valid-redacted'
            }
            Assert-Evidence ($case.route -match '^/equipment/\d+/edit/$' -and $case.target -and $validRequest -and
                $null -ne $case.request -and $case.expected_status -eq $expected -and $case.actual_status -eq $expected -and
                $case.denied -eq $true -and $case.no_leak -eq $true -and
                $case.before.count -gt 0 -and $case.before.count -eq $case.after.count -and
                $case.before.sha256 -match '^[0-9a-f]{64}$' -and $case.before.sha256 -ceq $case.after.sha256) "Invalid T-03 evidence: $role $method"
        }
    }
    $r2Marker = 'R2 whitespace preserved: new description and unchanged textarea with CRLF; detail auto-escaped.'
    Assert-Evidence (@($lines -ceq $r2Marker).Count -eq 1) 'Expected exact R2 whitespace evidence.'
    Assert-Evidence (@($lines -match 'admin GET 200.+POST 302').Count -eq 1 -and
        @($lines -match '^CSRF .+admin missing 403').Count -eq 1 -and
        @($lines -match '^CSRF .+admin mismatch 403').Count -eq 1) 'Expected separate legal and CSRF controls.'
    foreach ($fault in @('write-rollback', 'commit-rejected', 'commit-pre-disconnect', 'commit-lost-ack')) {
        Assert-Evidence (@($lines -match "^AC-8 ${fault} PID=").Count -eq 1) "Missing AC-8 probe: $fault"
    }
    foreach ($revocation in @('account-inactive', 'role-revoked')) {
        $proofPattern = "^R1 ${revocation} status=403 wait_verified=true blockers=\[\d+(?:, \d+)*\] pid=\d+ account_reread=1 updates=0 no_leak=true equipment_unchanged=true count=\d+$"
        Assert-Evidence (@($lines -match $proofPattern).Count -eq 1) "Missing lock-after-revocation proof: $revocation"
    }
    Assert-Evidence (@($lines -match '^T-01 .*PID=\{').Count -eq 4 -and
        @($lines -match '^T-01 .*B=\d+').Count -eq 2 -and
        @($lines -match '^AC-6.+T-01 4/4.+AC-8.*4/4').Count -eq 1 -and
        @($lines -match '^R1 2/2(?:\s|$)').Count -eq 1 -and
        @($lines -match '^\u6E05\u7406\u901A\u8FC7').Count -eq 1) 'Missing successful real-probe or cleanup evidence.'
    $outcome = "PASS: 67 baseline + $($added.Count) new Django tests; 8 prior + 2 R1 probes; 6 T-03 denial records."
    $code = 0
}
catch {
    $failure = $_.Exception.Message
}
finally {
    try {
        if ($before -ne 'NOT CAPTURED') {
            $after = Save-Manifest 'after'
            Assert-Evidence ($after -ceq $before) 'Tested files changed while verification was running.'
        }
    }
    catch {
        $code = 1
        $outcome = 'INCOMPLETE OR FAILED'
        $failure += ' ' + $_.Exception.Message
    }
    $rawHash = if (Test-Path -LiteralPath $raw -PathType Leaf) { (Get-FileHash -LiteralPath $raw -Algorithm SHA256).Hash } else { 'NO RAW LOG' }
    [IO.File]::WriteAllLines($summary, [string[]]@(
        "actual operator(s), as reported: $ExecutedBy", 'run mode: ordinary PowerShell, team development self-test',
        'target: lab_booking_test@127.0.0.1:5433/test_lab_booking',
        "started=$start", ('ended=' + (Get-Date -Format o)), "patch-sha256=$patchHash",
        "before-manifest-sha256=$before", "after-manifest-sha256=$after", "raw-log-sha256=$rawHash",
        "verification exit=$code", "result=$outcome", $failure
    ), $utf8)
    Pop-Location
    Write-Host "Evidence: $runDirectory"
}
if ($code -ne 0) { throw "Verification incomplete or failed. See $summary" }
