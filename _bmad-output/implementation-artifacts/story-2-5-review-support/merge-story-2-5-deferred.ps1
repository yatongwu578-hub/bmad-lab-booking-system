[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$LedgerPath,
    [Parameter(Mandatory)][string]$PendingPath,
    [Parameter(Mandatory)][ValidatePattern('^[0-9A-Fa-f]{64}$')][string]$ExpectedSha256,
    [switch]$Apply
)
$ErrorActionPreference = 'Stop'
$ledger = (Resolve-Path -LiteralPath $LedgerPath).Path
if ([IO.Path]::GetFileName($ledger) -cne 'deferred-work.md') { throw 'Expected deferred-work.md.' }
$heading = '## Deferred from: Story 2.5 full code review of spec-2-5-admin-reservation-query.md (2026-11-27)'
$utf8 = [Text.UTF8Encoding]::new($false, $true)
$pending = [IO.File]::ReadAllText((Resolve-Path -LiteralPath $PendingPath).Path,$utf8).Replace("`r`n","`n").TrimEnd()
if (-not $pending.StartsWith($heading + "`n",[StringComparison]::Ordinal) -or
    [regex]::Matches($pending,'(?m)^## ').Count -ne 1 -or $pending.Contains("`r")) {
    throw 'Bad Story 2.5 pending block.'
}
$tags = @([regex]::Matches($pending,'2\.5-[PD][0-9]+') | ForEach-Object Value)
if (-not $tags.Count -or @($tags | Sort-Object -Unique).Count -ne $tags.Count) { throw 'Bad or duplicate pending IDs.' }
function Get-Sha([byte[]]$bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-','') } finally { $sha.Dispose() }
}
function Read-Entire([IO.FileStream]$stream) {
    if ($stream.Length -gt 4MB) { throw 'Unexpected ledger size.' }
    $stream.Position = 0
    $data = [byte[]]::new([int]$stream.Length)
    $offset = 0
    while ($offset -lt $data.Length) {
        $got = $stream.Read($data,$offset,$data.Length-$offset)
        if ($got -le 0) { throw 'Could not read complete ledger.' }
        $offset += $got
    }
    return ,$data
}
$access = if ($Apply) { [IO.FileAccess]::ReadWrite } else { [IO.FileAccess]::Read }
$stream = [IO.File]::Open($ledger,[IO.FileMode]::Open,$access,[IO.FileShare]::None)
try {
    $old = Read-Entire $stream
    $before = Get-Sha $old
    $raw = $utf8.GetString($old)
    $text = $raw.Replace("`r`n","`n")
    $count = [regex]::Matches($text,[regex]::Escape($heading)).Count
    $counts = @($tags | ForEach-Object { [regex]::Matches($text,[regex]::Escape($_) + '(?!\d)').Count })
    if ($count -eq 1 -and @($counts | Where-Object {$_ -ne 1}).Count -eq 0 -and
        ($text.TrimEnd().EndsWith($pending,[StringComparison]::Ordinal) -or
         $text.Contains($pending + "`n`n## "))) {
        "already-present sha256=$before"
        'STORY25_DEFERRED_MERGE_OK'
        return
    }
    if ($count -ne 0 -or @($counts | Where-Object {$_ -ne 0}).Count -ne 0) {
        throw 'Partial or conflicting Story 2.5 block. Nothing appended.'
    }
    if ($before -ine $ExpectedSha256) { throw "Review current ledger before refreshing the approved expected hash. Current: $before" }
    if ($text.Contains("`r") -or ($raw.Contains("`r`n") -and $raw.Replace("`r`n",'').Contains("`n"))) {
        throw 'Unexpected mixed ledger line endings. Nothing appended.'
    }
    $nl = if ($raw.Contains("`r`n")) {"`r`n"} else {"`n"}
    $separator = if ($text.EndsWith("`n`n")) {''} elseif ($text.EndsWith("`n")) {$nl} else {$nl+$nl}
    $suffix = $utf8.GetBytes($separator + $pending.Replace("`n",$nl) + $nl)
    $candidate = [byte[]]($old+$suffix)
    $after = Get-Sha $candidate
    if (-not $Apply) {
        "preview before=$before after=$after ids=$($tags -join ',')"
        'STORY25_DEFERRED_PREVIEW_OK'
        return
    }
    try {
        $stream.Position = $old.Length
        $stream.Write($suffix,0,$suffix.Length)
        $stream.Flush($true)
        if ([Convert]::ToBase64String((Read-Entire $stream)) -cne [Convert]::ToBase64String($candidate)) {
            throw 'Post-append bytes differ.'
        }
    } catch {
        $stream.SetLength($old.Length)
        $stream.Flush($true)
        throw
    }
    "appended before=$before after=$after"
    'STORY25_DEFERRED_MERGE_OK'
} finally { $stream.Dispose() }
