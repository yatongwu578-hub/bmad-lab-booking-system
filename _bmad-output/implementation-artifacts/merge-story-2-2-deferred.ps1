[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ledgerPath = Join-Path $PSScriptRoot 'deferred-work.md'
$pendingPath = Join-Path $PSScriptRoot 'story-2-2-d044-deferred-pending.md'
$utf8 = [Text.UTF8Encoding]::new($false, $true)
$lf = [string][char]10
$crlf = ([string][char]13) + $lf
$section = '## Deferred from: Story 2.2 full code review and D-044 (2026-11-26)'
$ids = @('2.2-P1','2.2-P2','2.2-P3','2.2-P4','2.2-P5','2.2-P6','2.2-D1')

function Read-Story22Ledger([IO.Stream]$Stream) {
    $memory = [IO.MemoryStream]::new()
    try {
        $Stream.Position = 0
        $Stream.CopyTo($memory)
        $utf8.GetString($memory.ToArray())
    } finally {
        $memory.Dispose()
    }
}

function Count-Story22Line([string]$Source, [string]$Prefix) {
    [regex]::Matches($Source, '(?m)^' + [regex]::Escape($Prefix)).Count
}

$pending = [IO.File]::ReadAllText($pendingPath, $utf8).Replace($crlf, $lf).TrimEnd([char]10)
if (-not $pending.StartsWith($section + $lf, [StringComparison]::Ordinal) -or
    (Count-Story22Line $pending $section) -ne 1) {
    throw 'Unexpected D-044 pending section. Nothing was written.'
}
foreach ($id in $ids) {
    if ((Count-Story22Line $pending "- **$id") -ne 1) {
        throw "Unexpected pending entry $id. Nothing was written."
    }
}

$lease = [IO.File]::Open($ledgerPath, [IO.FileMode]::Open, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
try {
    $current = Read-Story22Ledger $lease
    $currentNormalized = $current.Replace($crlf, $lf)
    $headCount = Count-Story22Line $currentNormalized $section
    $counts = @($ids | ForEach-Object { Count-Story22Line $currentNormalized "- **$_" })
    $sameBlock = ($currentNormalized + $lf).Contains($pending + $lf)
    if ($headCount -eq 1 -and $sameBlock -and @($counts | Where-Object { $_ -ne 1 }).Count -eq 0) {
        $result = 'already-present'
    } else {
        $legacyHeader = '## Deferred from: code review of spec-2-2-query-equipment-occupancy (2026-11-26)'
        if ($headCount -ne 0 -or @($counts | Where-Object { $_ -ne 0 }).Count -ne 0 -or
            (Count-Story22Line $currentNormalized $legacyHeader) -ne 0) {
            throw 'Partial or conflicting Story 2.2 ledger entries found. Nothing was written.'
        }

        $newline = [regex]::Match($current, '\r\n|\n').Value
        if (-not $newline) { $newline = [Environment]::NewLine }
        $separator = $newline + $newline
        if ($current.EndsWith($separator)) { $separator = '' }
        elseif ($current.EndsWith($newline)) { $separator = $newline }
        $addition = $separator + $pending.Replace($lf, $newline) + $newline
        $initialLength = $lease.Length
        try {
            $lease.Position = $initialLength
            $bytes = $utf8.GetBytes($addition)
            $lease.Write($bytes, 0, $bytes.Length)
            $lease.Flush($true)
            if ((Read-Story22Ledger $lease) -cne ($current + $addition)) {
                throw 'Ledger read-back differs from the expected append.'
            }
        } catch {
            $lease.SetLength($initialLength)
            $lease.Flush($true)
            throw
        }
        $result = 'appended'
    }
} finally {
    $lease.Dispose()
}

Write-Output "Story 2.2 D-044 deferred entries: result=$result count=7"
Write-Output 'STORY22_D044_DEFERRED_MERGE_OK'
