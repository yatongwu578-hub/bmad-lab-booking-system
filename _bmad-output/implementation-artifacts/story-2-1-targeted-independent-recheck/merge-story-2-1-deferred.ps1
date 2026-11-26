[CmdletBinding()]
param([switch]$ValidateOnly)
$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot 'd040-approved-deferred-pending.md'
$target=Join-Path (Split-Path -Parent $PSScriptRoot) 'deferred-work.md'
$utf=[Text.UTF8Encoding]::new($false,$true)
$text=[IO.File]::ReadAllText($source,$utf)
$wanted=@('P04（原始 #6，Medium）','spec-2-1-submit-reservation.md (2026-11-26, targeted recheck)','Story 2.1 targeted code review and D-040 (2026-11-26)')
$blocks=@([regex]::Matches($text,'(?ms)^## Deferred from:.*?(?=^## Deferred from:|\z)') | ForEach-Object {$_.Value.Trim()})
if($blocks.Count -ne $wanted.Count){throw 'Unexpected number of Story 2.1 deferred sections.'}
for($n=0;$n -lt $wanted.Count;$n++){if(-not $blocks[$n].Contains($wanted[$n])){throw 'Source section/order changed.'}}
if($ValidateOnly){Write-Output 'STORY21_DEFERRED_INPUT_VALID 3'; exit 0}
$stream=$null
try{
 $stream=[IO.File]::Open($target,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
 $start=$stream.Length
 if($start -gt 10485760){throw 'Unexpected ledger size.'}
 function Read-Bytes {
  $memory=[IO.MemoryStream]::new()
  try{$stream.Seek(0,[IO.SeekOrigin]::Begin)|Out-Null; $stream.CopyTo($memory); return ,$memory.ToArray()}
  finally{$memory.Dispose()}
 }
 [byte[]]$before=Read-Bytes
 $current=$utf.GetString($before)
 $nl=if($current.Contains([string][char]13+[char]10)){[string][char]13+[char]10}else{[string][char]10}
 $join=@(for($i=0;$i -lt $wanted.Count;$i++){
  $marker=$wanted[$i]
  $matches=[regex]::Matches($current,[regex]::Escape($marker)).Count
  if($matches -gt 1){throw 'Duplicate deferred section marker; no changes made.'}
  if(-not $matches){$blocks[$i].Replace([string][char]13+[char]10,[string][char]10).Replace([string][char]10,$nl)}
 })
 if(-not $join.Count){Write-Output 'STORY21_DEFERRED_MERGE_OK appended=0 already_present=3'; exit 0}
 [byte[]]$extra=$utf.GetBytes($nl+$nl+($join -join ($nl+$nl))+$nl)
 try{
  $stream.Seek(0,[IO.SeekOrigin]::End)|Out-Null
  $stream.Write($extra,0,$extra.Length); $stream.Flush($true)
  $after=$utf.GetString((Read-Bytes))
  if(-not $after.StartsWith($current,[StringComparison]::Ordinal) -or $stream.Length -ne ($start+$extra.Length)){throw 'Prior ledger bytes or append length changed.'}
  foreach($marker in $wanted){if([regex]::Matches($after,[regex]::Escape($marker)).Count -ne 1){throw 'A Story 2.1 section was not written exactly once.'}}
 }catch{
  $stream.SetLength($start); $stream.Flush($true)
  if($utf.GetString((Read-Bytes)) -cne $current){throw 'Ledger rollback verification failed. Stop and inspect before retrying.'}
  throw
 }
 Write-Output ("STORY21_DEFERRED_MERGE_OK appended="+$join.Count+" retained="+(3-$join.Count))
}finally{
 if($stream){$stream.Dispose()}
}

