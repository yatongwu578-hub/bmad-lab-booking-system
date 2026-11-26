[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ExecutedBy,
    [string]$Passfile
)
$ErrorActionPreference = 'Stop'
$operator = $ExecutedBy.Trim()
if (-not $operator -or $operator -match 'placeholder|your name|\u586B\u5199|[\r\n]') { throw 'Supply the actual operator name.' }
$psql = 'C:/Program Files/PostgreSQL/17/bin/psql.exe'
$sql = Join-Path $PSScriptRoot 'story-1-4-runtime-acl-readonly.sql'
if (-not $Passfile) { $Passfile = Join-Path $env:LOCALAPPDATA 'LabBooking/PostgreSQL17/pgpass.conf' }
$run = Join-Path $PSScriptRoot ('story-1-4-runtime-acl-check-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Path $run | Out-Null
$log = Join-Path $run 'acl-raw.txt'
$utf8 = [Text.UTF8Encoding]::new($false)
$start = Get-Date -Format o
$state = 'UNCONFIRMED'
$code = 'NOT RUN'
$failure = ''
$priorPassfile = [Environment]::GetEnvironmentVariable('PGPASSFILE','Process')
$priorEncoding = [Environment]::GetEnvironmentVariable('PGCLIENTENCODING','Process')
$priorConsole = [Console]::OutputEncoding

function Invoke-ReadOnlyPsql([string[]]$NativeArguments) {
    $ErrorActionPreference = 'Continue'
    $PSNativeCommandUseErrorActionPreference = $false
    & $psql @NativeArguments 2>&1 | ForEach-Object {
        $line = $_.ToString()
        [IO.File]::AppendAllText($log,$line + [Environment]::NewLine,$utf8)
        Write-Host $line
    }
    $LASTEXITCODE
}

try {
    foreach ($path in @($psql,$sql,$Passfile)) {
        if (-not [IO.Path]::IsPathRooted($path) -or -not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw 'Required psql, read-only SQL or existing protected passfile is unavailable.'
        }
    }
    $conflicts = @('PGHOST','PGHOSTADDR','PGPORT','PGDATABASE','PGUSER','PGPASSWORD','PGSERVICE','PGSERVICEFILE','PGOPTIONS') |
        Where-Object { Test-Path "Env:$_" }
    if ($conflicts) { throw ('Remove conflicting libpq environment variables: ' + ($conflicts -join ', ')) }
    [IO.File]::WriteAllLines((Join-Path $run 'inputs.sha256'),[string[]]@(
        foreach ($path in @($sql,$PSCommandPath)) {
            "$((Get-FileHash -LiteralPath $path).Hash)  $(Split-Path $path -Leaf)"
        }
    ),$utf8)
    $env:PGPASSFILE = $Passfile
    $env:PGCLIENTENCODING = 'UTF8'
    [Console]::OutputEncoding = $utf8
    $target = @('-X','-w','-h','127.0.0.1','-p','5433','-d','lab_booking','-U','lab_booking_migrator',
        '-v','ON_ERROR_STOP=1','-c','BEGIN READ ONLY','-f',$sql,'-c','COMMIT')
    $code = Invoke-ReadOnlyPsql $target
    [IO.File]::AppendAllText($log,"Exit $code" + [Environment]::NewLine,$utf8)
    if ($code -ne 0) { throw 'Read-only ACL check failed. Do not run the grant or runtime verification.' }
    $lines = @(Select-String -LiteralPath $log -CaseSensitive -Pattern '(?:^|:\s*)D035_ACL_STATE=(NOT_GRANTED|GRANTED)\s*$')
    $commit = @(Select-String -LiteralPath $log -CaseSensitive -Pattern '^COMMIT\s*$')
    if ($lines.Count -ne 1 -or $commit.Count -ne 1) {
        throw 'Read-only ACL state is unconfirmed. Do not run the grant or runtime verification.'
    }
    $state = $lines[0].Matches[0].Groups[1].Value
}
catch {
    $failure = $_.Exception.Message
    throw
}
finally {
    [Environment]::SetEnvironmentVariable('PGPASSFILE',$priorPassfile,'Process')
    [Environment]::SetEnvironmentVariable('PGCLIENTENCODING',$priorEncoding,'Process')
    [Console]::OutputEncoding = $priorConsole
    [IO.File]::WriteAllLines((Join-Path $run 'run-summary.txt'),[string[]]@(
        "actual operator(s), as reported: $operator", "started=$start", ('ended=' + (Get-Date -Format o)),
        'target=PostgreSQL 17.12, 127.0.0.1:5433/lab_booking, lab_booking_migrator, read-only',
        "psql_exit=$code", "acl_state=$state", $failure
    ),$utf8)
    Write-Host "Evidence: $run"
}
Write-Output $state
