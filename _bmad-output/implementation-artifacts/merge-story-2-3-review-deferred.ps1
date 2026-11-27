[CmdletBinding()]
param(
    [string]$LedgerPath = (Join-Path $PSScriptRoot 'deferred-work.md'),
    [string]$PendingPath = (Join-Path $PSScriptRoot 'story-2-3-review-deferred-pending.md'),
    [ValidatePattern('^[0-9A-Fa-f]{64}$')]
    [string]$ExpectedSha256 = 'E96C14BB6DBA24F89E4D98C1E209EC0DFBA433FE2986CE05CF6D75973EFF68D0'
)
$ErrorActionPreference = 'Stop'
$ledger = (Resolve-Path -LiteralPath $LedgerPath).Path
if ([IO.Path]::GetFileName($ledger) -cne 'deferred-work.md') { throw 'Expected deferred-work.md.' }
$heading = '## Deferred from: code review of spec-2-3-query-own-reservations.md (2026-11-27)'
$releaseHeading = '## Release Gate for: Story 2.3 (2026-11-27)'
$tags = '2.3-P01','2.3-P02','2.3-P03','2.3-P04','2.3-P05','2.3-P06','2.3-P07','2.3-P08','2.3-W2','2.3-W1'
$utf8 = New-Object System.Text.UTF8Encoding($false,$true)
$pending = [IO.File]::ReadAllText((Resolve-Path -LiteralPath $PendingPath).Path,$utf8).Replace("`r`n","`n").TrimEnd()
if (-not $pending.StartsWith($heading + "`n",[StringComparison]::Ordinal) -or
    [regex]::Matches($pending,[regex]::Escape($releaseHeading)).Count -ne 1) { throw 'Unexpected pending headings.' }
foreach ($tag in $tags) {
    if ([regex]::Matches($pending,[regex]::Escape($tag)).Count -ne 1) { throw "Unexpected pending marker: $tag" }
}
$f = [IO.File]::Open($ledger,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {
    if ($f.Length -gt 4MB) { throw 'Unexpected ledger size.' }
    $old = New-Object byte[] ([int]$f.Length)
    if ($f.Read($old,0,$old.Length) -ne $old.Length) { throw 'Could not read the complete ledger.' }
    $sha = [Security.Cryptography.SHA256]::Create()
    try { $before = [BitConverter]::ToString($sha.ComputeHash($old)).Replace('-','') } finally { $sha.Dispose() }
    $text = $utf8.GetString($old).Replace("`r`n","`n")
    $headingCount = [regex]::Matches($text,[regex]::Escape($heading)).Count
    $releaseCount = [regex]::Matches($text,[regex]::Escape($releaseHeading)).Count
    $tagCounts = @($tags | ForEach-Object { [regex]::Matches($text,[regex]::Escape($_)).Count })
    if ($headingCount -eq 1 -and $releaseCount -eq 1 -and @($tagCounts | Where-Object { $_ -ne 1 }).Count -eq 0 -and
        ($text.TrimEnd().EndsWith($pending,[StringComparison]::Ordinal) -or
         $text.Contains($pending + "`n`n## "))) {
        "already-present sha256=$before"
        'STORY23_DEFERRED_MERGE_OK'
        return
    }
    if ($headingCount -ne 0 -or $releaseCount -ne 0 -or @($tagCounts | Where-Object { $_ -ne 0 }).Count -ne 0) { throw 'Partial, duplicate, or conflicting Story 2.3 block. Nothing appended.' }
    if ($before -ine $ExpectedSha256) { throw "Ledger changed; review its content before explicitly passing the new ExpectedSha256. Current: $before" }
    $raw = $utf8.GetString($old)
    $firstLF = $raw.IndexOf("`n",[StringComparison]::Ordinal)
    $nl = if ($firstLF -gt 0 -and $raw[$firstLF-1] -eq "`r") { "`r`n" } else { "`n" }
    $separator = if ($text.EndsWith("`n`n")) { '' } elseif ($text.EndsWith("`n")) { $nl } else { $nl + $nl }
    $suffix = $utf8.GetBytes($separator + $pending.Replace("`n",$nl) + $nl)
    $length = $f.Length
    try {
        $f.Position = $length
        $f.Write($suffix,0,$suffix.Length)
        $f.Flush($true)
        $f.Position = 0
        $all = New-Object byte[] ([int]$f.Length)
        if ($f.Read($all,0,$all.Length) -ne $all.Length -or
            [Convert]::ToBase64String($all) -cne [Convert]::ToBase64String([byte[]]($old+$suffix))) {
            throw 'Ledger copy after append differs.'
        }
    } catch {
        $f.SetLength($length)
        $f.Flush($true)
        throw
    }
    $sha = [Security.Cryptography.SHA256]::Create()
    try { $after = [BitConverter]::ToString($sha.ComputeHash($all)).Replace('-','') } finally { $sha.Dispose() }
    "appended before=$before after=$after"
    'STORY23_DEFERRED_MERGE_OK'
} finally { $f.Dispose() }
