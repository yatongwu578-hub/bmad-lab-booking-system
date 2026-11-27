[CmdletBinding()]
param(
    [string]$Repo = 'F:\softwork\SE-Management\bmad-lab-booking-system',
    [string]$Passfile,
    [string]$Chrome,
    [string]$Psql,
    [string]$OutputRoot
)
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path -LiteralPath $Repo).Path
$verifier = Join-Path $repoRoot '_bmad-output/implementation-artifacts/verify-story-2-5.ps1'
$python = Join-Path $repoRoot '.venv/Scripts/python.exe'
$audit = Join-Path $PSScriptRoot 'audit-story-2-5-evidence.py'
if (-not $OutputRoot) { $OutputRoot = [IO.Path]::GetFullPath((Join-Path $repoRoot '../../outputs')) }
$batchRoot = Join-Path $OutputRoot ('story-2-5-isolated-review-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') +
    '-' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $batchRoot
Write-Host "New reviewer archive: $batchRoot"

# Do not run concurrently with any other same-database verification.
# The preflight, original Python and DB identity checks run inside the single serial batch.
$options = @{ Remediation = $true; OutputRoot = $batchRoot }
foreach ($name in 'Passfile','Chrome','Psql') {
    if ($PSBoundParameters.ContainsKey($name)) { $options[$name] = $PSBoundParameters[$name] }
}
try {
    $marker = @(& $verifier @options | Tee-Object -FilePath (Join-Path $batchRoot 'batch-marker.txt'))
    if ($marker.Count -ne 1 -or $marker[0] -cne 'STORY25_VERIFICATION_OK') {
        throw 'The batch did not emit its unique exact success marker.'
    }
    $batch = @(Get-ChildItem -LiteralPath $batchRoot -Directory -Filter 'story-2-5-run-*')
    if ($batch.Count -ne 1) { throw 'Cannot uniquely identify the raw reviewer archive.' }
    $auditOut = Join-Path $batchRoot 'review-offline-audit.txt'
    $auditErr = Join-Path $batchRoot 'review-offline-audit.stderr.txt'
    & $python $audit --repo $repoRoot --run $batch[0].FullName 1> $auditOut 2> $auditErr
    $auditCode = $LASTEXITCODE
    "offline-audit exit=$auditCode" | Set-Content -Encoding UTF8 (Join-Path $batchRoot 'review-audit-stage.txt')
    if ($auditCode -ne 0 -or @(Get-Content -Encoding UTF8 $auditOut | Where-Object {
        $_ -ceq 'STORY25_OFFLINE_AUDIT_OK'
    }).Count -ne 1) {
        throw "Offline evidence checks failed, see the archive: $batchRoot"
    }
    Get-Content -Encoding UTF8 -LiteralPath $auditOut
    'STORY25_REVIEW_RUN_OK'
} catch {
    $_.Exception.Message | Set-Content -Encoding UTF8 (Join-Path $batchRoot 'review-failure.txt')
    throw
}
