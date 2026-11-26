
[CmdletBinding()]
param([string]$Passfile,[string]$Chrome,[string]$Psql='C:\Program Files\PostgreSQL\17\bin\psql.exe')
$ErrorActionPreference='Stop'
$art=Split-Path -Parent $PSScriptRoot
$repo=(Resolve-Path -LiteralPath (Join-Path $art '../..')).Path
$runner=Join-Path $art 'verify-story-2-1-remediation.ps1'
$auditor=Join-Path $PSScriptRoot 'audit-targeted-run.py'
$python=Join-Path $repo '.venv/Scripts/python.exe'
$windowsPowerShell=Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe'
$started=[DateTimeOffset]::Now
$tag=(Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + ([Guid]::NewGuid().ToString('N')).Substring(0,12)
$receipt=Join-Path $PSScriptRoot ('independent-run-'+$tag)
$null=New-Item -ItemType Directory -Path $receipt
Write-Host "Story 2.1 independent recheck output: $receipt"
$utf8=[Text.UTF8Encoding]::new($false)
$scope=[ordered]@{
 purpose='independent D-040 targeted retest'; evidence_revision='D-040'; started=$started.ToString('o')
 target='127.0.0.1:5433/test_lab_booking'; baseline='e196aba098771a31eb203be4270b460d5e0aab42'
 review_diff_sha256='FD6CE7161481C4899B6DB6DEE26B4A13D17756914D7DDB18B3E1DB298F625727'
 child_launcher_sha256='885014C61C690A959B00222CD4293B35A605B348179B4F3DDED2B9FFAC579200'
 auditor_sha256='8DA622C75BF661C0A1DCA145803945BDCB73902C42AF5204B30968F0873F0F32'; wrapper_sha256=(Get-FileHash -LiteralPath $PSCommandPath).Hash
 reused=@('nfr001-standard','faults','time-boundaries')
 fresh=@('regression-91','navigation','browser-correction','permissions','interleavings')
 child_metadata_note='D-040 enables actual request principal and I7 driver bindings; fresh and archived evidence remain separate.'
}
function Emit([string]$Name,$Value) {
 [IO.File]::WriteAllText((Join-Path $receipt $Name),($Value | ConvertTo-Json -Depth 14),$utf8)
}
function Pin([string]$Path,[string]$Expected) {
 if((Get-FileHash -LiteralPath $Path).Hash -cne $Expected){throw ('File digest mismatch: '+(Split-Path -Leaf $Path))}
}
function Quoted([string[]]$Values) {
 foreach($v in $Values) {if($v -match '["\x00-\x1F]' -or $v.EndsWith('\',[StringComparison]::Ordinal)){throw 'Invalid process argument'}}
 return (($Values | ForEach-Object {'"'+$_+'"'}) -join ' ')
}
function Exit-Record([string]$Name,[int]$Code) {
 [IO.File]::AppendAllText((Join-Path $receipt 'stages.txt'),"$(Get-Date -Format o) $Name exit=$Code"+[Environment]::NewLine,$utf8)
}
function Child-Directory([string[]]$Stdout,[string[]]$BeforeDirs) {
 $m=@($Stdout | Where-Object {$_ -cmatch '^Story 2\.1 remediation output: '})
 if($m.Count -ne 1){throw 'Expected exactly one fresh evidence directory.'}
 $path=(Resolve-Path -LiteralPath ($m[0] -creplace '^Story 2\.1 remediation output: ','')).Path
 $leaf=Split-Path -Leaf $path
 if((Split-Path -Parent $path) -ine $art -or $leaf -cnotmatch '^story-2-1-remediation-run-\d{8}-\d{6}-\d{3}-[0-9a-f]{12}$' -or $leaf -in $BeforeDirs){
  throw 'Invalid or previously existing launcher evidence directory.'
 }
 return $path
}
Emit 'scope.json' $scope
$encodingBefore=[Environment]::GetEnvironmentVariable('PYTHONIOENCODING','Process')
try {
 Pin $runner $scope.child_launcher_sha256
 Pin $auditor $scope.auditor_sha256
 $beforeDirs=@(Get-ChildItem -LiteralPath $art -Directory -Filter 'story-2-1-remediation-run-*' | ForEach-Object {$_.Name})
 $argsForChild=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$runner,'-Psql',$Psql)
 if($Passfile){$argsForChild+=@('-Passfile',$Passfile)}
 if($Chrome){$argsForChild+=@('-Chrome',$Chrome)}
 $childOut=Join-Path $receipt 'launcher.stdout.txt'
 $childErr=Join-Path $receipt 'launcher.stderr.txt'
 # No optional fault/competition rerun switch or hour wait.
 $child=Start-Process -FilePath $windowsPowerShell -ArgumentList (Quoted $argsForChild) -WorkingDirectory $repo -WindowStyle Hidden -PassThru -Wait -RedirectStandardOutput $childOut -RedirectStandardError $childErr
 Exit-Record 'live-launcher' $child.ExitCode
 $childText=@(Get-Content -LiteralPath $childOut -Encoding Default)
 $rawDir=Child-Directory $childText $beforeDirs
 Emit 'raw-run-pointer.json' ([ordered]@{rawDir=$rawDir;launcherExit=$child.ExitCode})
 if($child.ExitCode -ne 0){throw "Live launcher failed (exit $($child.ExitCode)). Preserve the raw logs."}
 if(@($childText | Where-Object {$_ -ceq "STORY21_REMEDIATION_OK $rawDir"}).Count -ne 1){throw 'Missing exact success marker.'}
 Pin $runner $scope.child_launcher_sha256
 Pin $auditor $scope.auditor_sha256
 Pin $PSCommandPath $scope.wrapper_sha256
 $env:PYTHONIOENCODING='utf-8'
 $audit=Join-Path $receipt 'raw-audit.json'
 $auditErr=Join-Path $receipt 'raw-audit.stderr.txt'
 $auditProcess=Start-Process -FilePath $python -ArgumentList (Quoted @('-E','-X','utf8','-B',$auditor,$rawDir)) -WorkingDirectory $repo -WindowStyle Hidden -PassThru -Wait -RedirectStandardOutput $audit -RedirectStandardError $auditErr
 Exit-Record 'reviewer-raw-audit' $auditProcess.ExitCode
 if($auditProcess.ExitCode -ne 0){throw "Reviewer audit rejected the fresh evidence (exit $($auditProcess.ExitCode))."}
 $audited=Get-Content -LiteralPath $audit -Raw -Encoding UTF8 | ConvertFrom-Json
 if($audited.evidence_revision -cne $scope.evidence_revision -or $audited.run -cne (Split-Path -Leaf $rawDir)){throw 'Audit result points to a different run.'}
 $completed=[DateTimeOffset]::Parse($audited.completed,[Globalization.CultureInfo]::InvariantCulture)
 if($completed -lt $started -or $completed -gt [DateTimeOffset]::Now){throw 'Invalid fresh-run timeline.'}
 Exit-Record 'independent-recheck-complete' 0
 Write-Output "STORY21_TARGETED_INDEPENDENT_OK $receipt"
} catch {
 [IO.File]::WriteAllText((Join-Path $receipt 'failure.txt'),($_ | Out-String),$utf8)
 throw
} finally {
 [Environment]::SetEnvironmentVariable('PYTHONIOENCODING',$encodingBefore,'Process')
}
