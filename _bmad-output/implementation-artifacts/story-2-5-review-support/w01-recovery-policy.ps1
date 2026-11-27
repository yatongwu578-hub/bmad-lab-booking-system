# Shared by the formal launcher and isolated tool qualification. No connection or write.
function Get-W01NextAction($Plan,[switch]$ResumeBrowser) {
    $allowed = @('actor_id','before_status','after_status','decision_at','recorded_at')
    $missing = @($Plan.missing)
    if ($missing.Count -ne @($allowed | Where-Object { $_ -cin $missing }).Count -or
        @($missing | Where-Object { $_ -cnotin $allowed }).Count -ne 0) { throw 'Unapproved or repeated ACL delta.' }
    if ($Plan.acl_result -ceq 'EXACT_COLUMNS_PRESENT' -and $missing.Count -eq 0) { return 'skip-grant' }
    if ($Plan.acl_result -cne 'MISSING_COLUMNS' -or $missing.Count -eq 0) { throw 'Inconsistent fresh ACL result.' }
    if ($ResumeBrowser) { throw 'Current ACL is not exact. Browser-only recovery cannot grant.' }
    'grant-missing-only'
}

function Assert-W01Window($Plan,[int]$Port,[DateTimeOffset]$Now=[DateTimeOffset]::UtcNow) {
    if ($null -eq $Plan.samples.full_unsafe_pending -or $Plan.samples.full_unsafe_pending -ne 0 -or
        [DateTimeOffset]::Parse($Plan.samples.safe_until) -le $Now.AddMinutes(2)) {
        throw 'FR-018 risk or insufficient safe window; no browser requests were started.'
    }
    if ($Plan.port_in_use_at_inspection -ne $false -or $Plan.desired_port -ne $Port) { throw 'Chosen loopback port is occupied or unverified.' }
    if ($Plan.samples.active_roles.admin -ne 1 -or $Plan.samples.active_roles.student -ne 1 -or
        $Plan.samples.active_roles.teacher -ne 1 -or -not $Plan.samples.filter -or -not $Plan.samples.detail) {
        throw 'Missing required existing accounts or samples; do not seed data.'
    }
}

function Get-W01QualifiedSources([string]$Support) {
    @('run-story-2-5-w01-formal.ps1','inspect-story-2-5-w01.ps1','w01-recovery-policy.ps1',
      'story-2-5-w01-inspect.sql','story-2-5-w01-snapshot.sql','story-2-5-w01-grant.sql',
      'serve-story-2-5-w01-smoke.py','capture-story-2-5-browser.mjs','check-story-2-5-w01-smoke.py',
      'test-story-2-5-w01-toolchain.ps1','test-story-2-5-w01-browser.py',
      'w01-log-contract.ps1','test-w01-log-contract.ps1') |
        ForEach-Object { (Get-FileHash -LiteralPath (Join-Path $Support $_) -Algorithm SHA256).Hash + '  ' + $_ }
}

function Assert-W01Qualification([string]$Directory,[string]$Support,[string]$LiveIoEvidence) {
    if (-not $Directory) { throw 'The isolated W01 toolchain qualification receipt is required.' }
    $marker = @(Read-W01Lines (Join-Path $Directory 'batch-marker.txt'))
    if ($marker.Count -ne 1 -or $marker[0] -cne 'STORY25_W01_TOOLCHAIN_OK') { throw 'No successful isolated toolchain receipt.' }
    $data = Read-W01Text (Join-Path $Directory 'qualification.json') | ConvertFrom-Json
    if ($data.target -cne '127.0.0.1:55435/test_lab_booking' -or $data.server_version -cne '17.12' -or
        $data.fixture_stopped -ne $true -or $data.browser -cne 'real Chrome, local synthetic fixture' -or
        $data.sql_cases -lt 17 -or $data.encoding_contract -cne 'utf8-wire-and-raw-native-v1') { throw 'Incomplete isolated tool qualification.' }
    $m = @(Get-W01QualifiedSources $Support)
    $old = @(Read-W01Lines (Join-Path $Directory 'tools.sha256'))
    if (($m -join "`n") -ceq ($old -join "`n")) { return }
    if (-not $LiveIoEvidence) { throw 'Tool files changed since isolated qualification; require targeted live I/O evidence.' }
    $accepted=@('run-story-2-5-w01-formal.ps1','serve-story-2-5-w01-smoke.py','w01-log-contract.ps1',
        'w01-recovery-policy.ps1','test-w01-log-contract.ps1')
    if ($m.Count -ne $old.Count) { throw 'Unexpected qualification manifest scope.' }
    for ($i=0; $i -lt $m.Count; $i++) {
        $newName=$m[$i].Substring(66)
        if ($newName -cne $old[$i].Substring(66) -or ($m[$i] -cne $old[$i] -and $newName -cnotin $accepted)) {
            throw 'Changes extend beyond the tested live I/O patch.'
        }
    }
    $new=@(Read-W01Lines (Join-Path $LiveIoEvidence 'live-io-inputs.sha256'))
    if (($m -join "`n") -cne ($new -join "`n")) { throw 'Live I/O evidence does not cover current inputs.' }
    Assert-W01Marker @(Read-W01Lines (Join-Path $LiveIoEvidence 'batch-marker.txt')) 0 'STORY25_W01_LIVE_IO_OK'
    $proof=Read-W01Text (Join-Path $LiveIoEvidence 'live-io.json') | ConvertFrom-Json
    if ($proof.http_status -ne 204 -or $proof.process_exit -ne 0 -or $proof.shared_receipt -ne $true -or
        $proof.exclusive_after_exit -ne $true -or $proof.live_writes_on_both_streams -ne $true) { throw 'Incomplete live I/O proof.' }
    $raw=Read-W01Text (Join-Path $LiveIoEvidence 'fixture.native.json') | ConvertFrom-Json
    if ($raw.exit -ne 0 -or
        (Get-FileHash -LiteralPath (Join-Path $LiveIoEvidence 'fixture.stdout.txt')).Hash -cne $raw.stdout_sha256 -or
        (Get-FileHash -LiteralPath (Join-Path $LiveIoEvidence 'fixture.stderr.txt')).Hash -cne $raw.stderr_sha256) {
        throw 'Live I/O raw logs changed.'
    }
}
