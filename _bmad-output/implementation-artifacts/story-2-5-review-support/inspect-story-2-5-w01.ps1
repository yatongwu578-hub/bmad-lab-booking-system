[CmdletBinding()]
param(
    [string]$Passfile,
    [string]$Psql = 'C:\Program Files\PostgreSQL\17\bin\psql.exe',
    [string]$OutputRoot = 'F:\softwork\outputs',
    [ValidateRange(1024,65535)][int]$BrowserPort = 8005,
    [string]$BeforeEvidence,
    [switch]$CaptureSnapshot,
    [switch]$ToolFixture
)

# Read-only planning. Does not launch Django or Chrome or execute an authorization.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'w01-log-contract.ps1')
Set-W01WireEncoding
$sql = Join-Path $PSScriptRoot 'story-2-5-w01-inspect.sql'
$archive = Join-Path $OutputRoot ('story-2-5-w01-inspect-' +
    (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $archive
Write-Host "W01 evidence: $archive"
$rawOut = Join-Path $archive 'acl-and-samples.stdout.txt'
$rawErr = Join-Path $archive 'acl-and-samples.stderr.txt'
$reportPath = Join-Path $archive 'w01-inspect.json'
$previous = @{}
$db = if ($ToolFixture) { 'test_lab_booking' } else { 'lab_booking' }
$dbPort = if ($ToolFixture) { 55435 } else { 5433 }
function AclKey-W01($row) {
    "$($row.column)|$([uint32]$row.grantee)|$([uint32]$row.grantor)|$($row.privilege)|$([bool]$row.grantable)"
}

try {
    if (-not $Passfile) { $Passfile = $env:PGPASSFILE }
    if (-not $Passfile) { $Passfile = Join-Path $env:LOCALAPPDATA 'LabBooking/PostgreSQL17/pgpass.conf' }
    if ($Passfile -notmatch '^[A-Za-z]:[\\/]' -or -not (Test-Path -LiteralPath $Passfile -PathType Leaf)) {
        throw 'Existing protected local PGPASSFILE not available. Do not request or print its contents.'
    }
    if (-not (Test-Path -LiteralPath $Psql -PathType Leaf)) { throw 'Existing PostgreSQL 17 psql.exe is required.' }
    $conflicts = @('PGHOST','PGHOSTADDR','PGPORT','PGDATABASE','PGUSER','PGPASSWORD','PGSERVICE','PGSERVICEFILE','PGOPTIONS') |
        Where-Object { Test-Path -LiteralPath "Env:$_" }
    if ($conflicts) { throw ('Conflicting PostgreSQL environment variables: ' + ($conflicts -join ', ')) }
    foreach ($name in @('PGPASSFILE','PGCONNECT_TIMEOUT','PGCLIENTENCODING')) {
        $previous[$name] = [Environment]::GetEnvironmentVariable($name,'Process')
    }
    $env:PGPASSFILE = $Passfile
    $env:PGCONNECT_TIMEOUT = '5'
    $env:PGCLIENTENCODING = 'UTF8'
    $argv = @('-X','-w','-q','-A','-t','-h','127.0.0.1','-p',"$dbPort",'-U','lab_booking_app',
              '-d',$db,'-v','ON_ERROR_STOP=1')
    if ($ToolFixture) { $argv += @('-v','w01_fixture=true') }
    if ($CaptureSnapshot) { $argv += @('-v','w01_capture=true') }
    $argv += @('-f',$sql)
    $snapshotSql = Join-Path $PSScriptRoot 'story-2-5-w01-snapshot.sql'
    $native = Start-Process -FilePath $Psql -ArgumentList (($argv | ForEach-Object { '"' + $_ + '"' }) -join ' ') `
        -Wait -WindowStyle Hidden -PassThru -RedirectStandardOutput $rawOut -RedirectStandardError $rawErr
    "psql-read-only exit=$($native.ExitCode)" | Set-Content -LiteralPath (Join-Path $archive 'stages.txt') -Encoding UTF8
    Write-W01NativeReceipt (Join-Path $archive 'psql-native.json') $rawOut $rawErr $native.ExitCode 'UTF-8 psql row protocol' 'raw psql diagnostics'
    if ($native.ExitCode -ne 0) { throw 'Read-only psql failed. Check the archived raw error.' }
    $data = @{}
    foreach ($line in (Read-W01Lines $rawOut)) {
        if ($line -notmatch '^([a-z_]+)\|(.+)$') { throw 'Unexpected psql output; stop.' }
        $tag = $Matches[1]
        $value = $Matches[2]
        if ($data.ContainsKey($tag)) { throw 'Duplicate evidence tag; stop.' }
        if ($tag -cin @('complete','snapshot_complete')) { $data[$tag] = $value }
        elseif ($value -ceq '[]') { $data[$tag] = @() }
        else { $data[$tag] = ConvertFrom-Json -InputObject $value }
    }
    $tags = @('identity','history_table','history_columns','history_explicit','existing_rights','samples','complete')
    if ($CaptureSnapshot) { $tags += @('business_snapshot','snapshot_complete') }
    if ($data.Count -ne $tags.Count -or @($tags | Where-Object { -not $data.ContainsKey($_) }).Count -or
        $data.complete -cne 'STORY25_W01_SQL_READONLY_OK') { throw 'Incomplete read-only evidence.' }
    $id = $data.identity
    if ($id.database -cne $db -or $id.login -cne 'lab_booking_app' -or $id.role -cne $id.login -or
        $id.host -cne '127.0.0.1' -or $id.port -ne $dbPort -or $id.version -cne '170012' -or
        $id.isolation -cne 'repeatable read' -or $id.read_only -cne 'on') { throw 'Identity or isolation drift.' }
    $history = $data.history_table
    if ($history.name -cne 'audit_operationhistory' -or $history.owner -cne 'lab_booking_migrator' -or $history.caller_owns -or $history.select -or
        $history.select_grantable -or $history.insert -or $history.update -or $history.delete -or $history.truncate -or
        $history.references -or $history.trigger -or $history.maintain) {
        throw 'Unexpected table-level or owner permissions. Stop, do not generate a grant.'
    }
    $base = @('id','reservation_id','action','actor_type','reason')
    $allow = @('actor_id','before_status','after_status','decision_at','recorded_at')
    $all = $base + $allow + @('equipment_id','object_type')
    $columns = @($data.history_columns)
    $names = @($columns | ForEach-Object column)
    $effective = @($columns | Where-Object { $_.select -eq $true } | ForEach-Object column)
    if ($names.Count -ne $all.Count -or @($names | Sort-Object -Unique).Count -ne $all.Count -or
        @($names | Where-Object { $_ -cnotin $all }).Count -or
        @($effective | Where-Object { $_ -cnotin ($base+$allow) }).Count -or
        @($base | Where-Object { $_ -cnotin $effective }).Count -or
        @($columns | Where-Object { $_.select_grantable -or $_.insert_grantable -or $_.update -or $_.references -or
            $_.insert -ne ($_.column -cne 'id') }).Count) {
        throw 'Unexpected history projection or grant option. Stop, do not widen permissions.'
    }
    if (@($data.existing_rights.PSObject.Properties | Where-Object { $_.Value -ne $true }).Count) {
        throw 'Existing non-W01 rights no longer match the approved runtime prerequisites.'
    }
    $missing = @($allow | Where-Object { $_ -cnotin $effective })
    if ($CaptureSnapshot -and ($missing.Count -or $data.snapshot_complete -cne 'STORY25_W01_SNAPSHOT_OK')) {
        throw 'Formal snapshot requires the exact W01 effective ACL and its snapshot receipt.'
    }
    if ($BeforeEvidence) {
        $before = Read-W01Text $BeforeEvidence | ConvertFrom-Json
        if ($before.identity.database -cne $id.database -or $before.identity.role -cne $id.role -or
            $before.identity.host -cne $id.host -or $before.identity.port -ne $id.port -or
            $before.identity.version -cne $id.version -or $missing.Count) {
            throw 'Before evidence identity does not match or the after matrix still has missing SELECT rights.'
        }
        $ob = @($before.history_columns | Sort-Object column)
        $nb = @($columns | Sort-Object column)
        if ($ob.Count -ne $nb.Count -or
            ($before.history_table | ConvertTo-Json -Compress) -cne ($history | ConvertTo-Json -Compress)) {
            throw 'Unexpected table state in before/after comparison.'
        }
        for ($i=0; $i -lt $nb.Count; $i++) {
            $x=$ob[$i]; $y=$nb[$i]
            if ($x.column -cne $y.column -or $x.insert -ne $y.insert -or $x.update -ne $y.update -or
                $x.references -ne $y.references -or $x.insert_grantable -ne $y.insert_grantable -or
                $x.select_grantable -ne $y.select_grantable -or
                ($x.select -ne $y.select -and ($x.column -cnotin @($before.missing) -or -not $y.select))) {
                throw 'Effective ACL changed beyond the approved column SELECT delta.'
            }
        }
        $beforeRights = $before.existing_rights | ConvertTo-Json -Compress
        if ($beforeRights -cne ($data.existing_rights | ConvertTo-Json -Compress)) { throw 'Non-W01 rights differ.' }
        $priorAcl = @($before.history_explicit | ForEach-Object { AclKey-W01 $_ })
        $afterAcl = @($data.history_explicit | ForEach-Object { AclKey-W01 $_ })
        if (@($priorAcl | Where-Object { $_ -cnotin $afterAcl }).Count) { throw 'An explicit prior ACL entry was removed.' }
        $added = @($data.history_explicit | Where-Object { (AclKey-W01 $_) -cnotin $priorAcl })
        if ($added.Count -ne @($before.missing).Count -or
            @($added | Where-Object { $_.privilege -cne 'SELECT' -or $_.grantable -or
                                      $_.grantee -ne $id.role_oid -or $_.column -cnotin @($before.missing) }).Count) {
            throw 'Explicit ACL differs beyond the expected column-only grant.'
        }
        if ($CaptureSnapshot -and $before.business_snapshot) {
            foreach ($category in @('reservations','equipment','history_projected','account_security')) {
                $prior = $before.business_snapshot.$category
                $now = $data.business_snapshot.$category
                if (-not $prior -or -not $now -or $prior.count -ne $now.count -or $prior.digest -cne $now.digest) {
                    throw "Business snapshot drift after the formal smoke: $category."
                }
            }
        }
    }
    $localPortBusy = $false
    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,$BrowserPort)
    $listener.ExclusiveAddressUse = $true
    try { $listener.Start() } catch [Net.Sockets.SocketException] {
        if ($_.Exception.SocketErrorCode -notin [Net.Sockets.SocketError]::AddressAlreadyInUse,[Net.Sockets.SocketError]::AccessDenied) { throw }
        $localPortBusy = $true
    } finally { $listener.Stop() }
    $plan = [ordered]@{
        identity=$id; history_table=$history; history_columns=$columns; history_explicit=@($data.history_explicit)
        existing_rights=$data.existing_rights; samples=$data.samples; missing=$missing
        business_snapshot=$data.business_snapshot
        desired_port=$BrowserPort; port_in_use_at_inspection=$localPortBusy
        acl_result=$(if ($missing.Count) {'MISSING_COLUMNS'} else {'EXACT_COLUMNS_PRESENT'})
        stage='read-only inspection; no change made'
        inspection_sql_sha256=(Get-FileHash -LiteralPath $sql).Hash
        snapshot_sql_sha256=$(if ($CaptureSnapshot) { (Get-FileHash -LiteralPath $snapshotSql).Hash })
        raw_stdout_sha256=(Get-FileHash -LiteralPath $rawOut).Hash
    }
    $plan | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $reportPath -Encoding UTF8
    if ($missing.Count) {
        # Deliberately a text proposal, never passed to psql.
        ("GRANT SELECT (" + ($missing -join ', ') +
            ') ON TABLE public.audit_operationhistory TO lab_booking_app;') |
            Set-Content -LiteralPath (Join-Path $archive 'proposed-grant-not-executed.txt') -Encoding UTF8
    }
    "acl=$($plan.acl_result) missing=$($missing -join ',') port_busy=$localPortBusy"
    'STORY25_W01_INSPECT_OK' | Set-Content -LiteralPath (Join-Path $archive 'batch-marker.txt') -Encoding UTF8
    'STORY25_W01_INSPECT_OK'
} catch {
    $_.Exception.Message | Set-Content -LiteralPath (Join-Path $archive 'inspect-failure.txt') -Encoding UTF8
    throw
} finally {
    foreach ($name in $previous.Keys) { [Environment]::SetEnvironmentVariable($name,$previous[$name],'Process') }
}
