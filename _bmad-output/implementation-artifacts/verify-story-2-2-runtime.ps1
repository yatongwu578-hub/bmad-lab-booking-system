[CmdletBinding()]
param(
    [string]$Passfile,
    [ValidateRange(1024,65535)][int]$Port = 8002,
    [string]$VerifyAfter
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$python = Join-Path $root '.venv/Scripts/python.exe'
$reader = Join-Path $PSScriptRoot 'read-story-2-2-runtime.py'
$manifest = Join-Path $root '_bmad-output/implementation-artifacts/story-2-2-review-run-50b9a0bc1f4746b59dae49cc5f2ebe44/story-2-2-run-20261126-232700-557-c6cf7cc2/before.sha256'
$utf8 = [Text.UTF8Encoding]::new($false)

function Require-Story22($Ok, [string]$Message) {
    if (-not $Ok) { throw $Message }
}

function Confirm-Story22Source {
    Require-Story22 ((Get-FileHash -LiteralPath $manifest).Hash -ceq '22C7B1C42B26794245AB2C43CCBFE7DB6D5DDFD92BC82B8E175B12244EF3B07A') 'Independent input manifest changed.'
    $pinned = @{}
    foreach ($line in (Get-Content -LiteralPath $manifest -Encoding UTF8)) {
        if ($line -cmatch '^([A-F0-9]{64})  ((?:accounts|audit|equipment|lab_booking|reservations)/[A-Za-z0-9_./-]+\.(?:py|html)|manage\.py|requirements\.txt)$') {
            $hash = $Matches[1]; $rel = $Matches[2]
            Require-Story22 (-not $pinned.ContainsKey($rel) -and $rel -notmatch '(?:^|/)\.\.(?:/|$)') 'Invalid source manifest entry.'
            $pinned[$rel] = $hash
            Require-Story22 ((Get-FileHash -LiteralPath (Join-Path $root $rel)).Hash -ceq $hash) "Independent runtime source differs: $rel"
        }
    }
    $actual = @('manage.py','requirements.txt')
    foreach ($dir in @('accounts','audit','equipment','lab_booking','reservations')) {
        $actual += @(Get-ChildItem -LiteralPath (Join-Path $root $dir) -File -Recurse |
            Where-Object { $_.Extension -in '.py','.html' } |
            ForEach-Object { $_.FullName.Substring($root.Length+1).Replace('\','/') })
    }
    Require-Story22 (@(Compare-Object @($pinned.Keys) $actual -CaseSensitive).Count -eq 0) 'Runtime source inventory differs.'
}

function Invoke-Story22ReadOnly([string]$Phase, [string]$RunDir) {
    $ErrorActionPreference = 'Continue'
    [string[]]$lines = @(& $python -B $reader $Phase $RunDir 2>&1 | ForEach-Object { $_.ToString() })
    $nativeExit = $LASTEXITCODE
    $log = Join-Path $RunDir ("readonly-$Phase.log")
    [IO.File]::WriteAllLines($log, $lines, $utf8)
    [IO.File]::AppendAllText((Join-Path $RunDir 'stages.txt'),
        ("{0:o} readonly-{1} exit={2}" -f (Get-Date),$Phase,$nativeExit) + [Environment]::NewLine,$utf8)
    $marker = 'STORY22_RUNTIME_READONLY_' + $Phase.ToUpperInvariant() + '_OK'
    Require-Story22 ($nativeExit -eq 0 -and @($lines | Where-Object { $_ -ceq $marker }).Count -eq 1) "Read-only $Phase did not pass. See $log. No writes or retries are authorized by this result."
    Write-Output $marker
}

Require-Story22 (Test-Path -LiteralPath $python -PathType Leaf) 'Original project interpreter missing.'
if (-not $Passfile) { $Passfile = $env:PGPASSFILE }
if (-not $Passfile) { $Passfile = Join-Path $env:LOCALAPPDATA 'LabBooking/PostgreSQL17/pgpass.conf' }
Require-Story22 ($Passfile -match '^[A-Za-z]:[\\/]' -and (Test-Path -LiteralPath $Passfile -PathType Leaf)) 'Use the existing protected absolute local PGPASSFILE.'
$Passfile = (Resolve-Path -LiteralPath $Passfile).Path
Require-Story22 (-not $Passfile.StartsWith($root + '\',[StringComparison]::OrdinalIgnoreCase) -and
    -not ((Get-Item -LiteralPath $Passfile).Attributes -band [IO.FileAttributes]::ReparsePoint)) 'Passfile must stay protected, outside the repository.'
$allowedSids = @([Security.Principal.WindowsIdentity]::GetCurrent().User.Value,'S-1-5-18','S-1-5-32-544')
foreach ($rule in (Get-Acl -LiteralPath $Passfile).Access) {
    if ($rule.AccessControlType -eq [Security.AccessControl.AccessControlType]::Allow) {
        Require-Story22 ($rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value -in $allowedSids) 'Passfile Windows ACL exceeds original scope.'
    }
}
$overrides = @('PGHOST','PGHOSTADDR','PGPORT','PGDATABASE','PGUSER','PGPASSWORD','PGSERVICE','PGSERVICEFILE','PGOPTIONS' |
    Where-Object { Test-Path -LiteralPath "Env:$_" })
Require-Story22 ($overrides.Count -eq 0) ('Remove conflicting connection overrides in this terminal: ' + ($overrides -join ', '))
Confirm-Story22Source
if (-not $VerifyAfter) {
    Require-Story22 ($Port -ne 8001) 'Do not use or stop the previous 8001 listener.'
    $net = @(netstat.exe -ano -p TCP)
    Require-Story22 ($LASTEXITCODE -eq 0) 'Unable to inspect local ports; do not start the app.'
    Require-Story22 (@($net | Where-Object { $_ -match ("^\s*TCP\s+\S+:{0}\s+" -f $Port) }).Count -eq 0) "Port $Port is occupied. Stop here or select a different free loopback port. No process stopped."
    $tag = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + ([guid]::NewGuid().ToString('N')).Substring(0,8)
    $run = [IO.Directory]::CreateDirectory((Join-Path $PSScriptRoot ('story-2-2-runtime-' + $tag))).FullName
} else {
    $run = (Resolve-Path -LiteralPath $VerifyAfter).Path
    Require-Story22 ((Split-Path -Parent $run) -ieq $PSScriptRoot -and
        (Split-Path -Leaf $run) -cmatch '^story-2-2-runtime-\d{8}-\d{6}-[a-f0-9]{8}$' -and
        -not ((Get-Item -LiteralPath $run).Attributes -band [IO.FileAttributes]::ReparsePoint)) 'Use the exact Story 2.2 runtime receipt directory.'
    Require-Story22 ((Test-Path -LiteralPath (Join-Path $run 'runtime-readonly-before.json') -PathType Leaf) -and
        -not (Test-Path -LiteralPath (Join-Path $run 'runtime-readonly-after.json'))) 'Missing before receipt or after already recorded. Do not overwrite or replay.'
}
Write-Host "Story 2.2 runtime evidence: $run"

$saved = @{}
foreach ($name in @('PGPASSFILE','LAB_BOOKING_DB_MODE','LAB_BOOKING_SECRET_KEY','DJANGO_SETTINGS_MODULE','PYTHONUTF8')) {
    $saved[$name] = [Environment]::GetEnvironmentVariable($name,'Process')
}
Push-Location -LiteralPath $root
try {
    $env:PGPASSFILE = $Passfile
    $env:LAB_BOOKING_DB_MODE = 'runtime'
    $env:DJANGO_SETTINGS_MODULE = 'lab_booking.settings'
    $env:PYTHONUTF8 = '1'
    if ($VerifyAfter) {
        Invoke-Story22ReadOnly 'after' $run
    } else {
        Invoke-Story22ReadOnly 'before' $run
        $receipt = Get-Content -LiteralPath (Join-Path $run 'runtime-readonly-before.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        Require-Story22 (@($receipt.smoke_dates_without_pending.PSObject.Properties | ForEach-Object { $_.Name }).Count -gt 0) 'No safe smoke date was observed. Do not add fixtures.'
        $env:LAB_BOOKING_SECRET_KEY = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
        $target = "127.0.0.1:$Port"
        [IO.File]::WriteAllLines((Join-Path $run 'listener-plan.txt'),
            @("loopback=$target","launch_requested_at=$(Get-Date -Format o)","input_manifest_sha256=$((Get-FileHash -LiteralPath $manifest).Hash)"),$utf8)
        Write-Host "Use a fresh browser profile, http://$target/login/"
        Write-Host "Device: $($receipt.device_number) (id=$($receipt.snapshot.device_id))"
        Write-Host ("Dates without pending bookings: " + ($receipt.smoke_dates_without_pending | ConvertTo-Json -Compress))
        Write-Host 'Run only the documented occupancy smoke. Stop this foreground command with Ctrl+C; do not use port 8001.'
        & $python -B -u manage.py runserver $target --noreload
        if ($LASTEXITCODE -ne 0) { throw "Runtime server exited with $LASTEXITCODE. No automatic restart." }
    }
} finally {
    Pop-Location
    foreach ($name in $saved.Keys) {
        [Environment]::SetEnvironmentVariable($name,$saved[$name],'Process')
    }
}
