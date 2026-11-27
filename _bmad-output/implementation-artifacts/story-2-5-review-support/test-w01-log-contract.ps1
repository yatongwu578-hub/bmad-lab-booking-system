[CmdletBinding()]
param([string]$OutputRoot='F:\softwork\outputs',[string]$ReferenceInitLog,[switch]$LiveIo,
    [string]$FixturePython='C:\Users\15860\miniconda3\python.exe')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'w01-log-contract.ps1')
Set-W01WireEncoding
$archive = (New-Item -ItemType Directory -Path (Join-Path $OutputRoot ('w01-encoding-' + [guid]::NewGuid().ToString('N')))).FullName
Write-Output "W01 encoding evidence: $archive"
function Verify-Encoding($Condition,[string]$Case) {
    if (-not $Condition) { throw "W01 encoding check failed: $Case" }
    Add-Content -LiteralPath (Join-Path $archive 'cases.txt') -Value $Case -Encoding UTF8
}
if ($LiveIo) {
    . (Join-Path $PSScriptRoot 'w01-recovery-policy.ps1')
    $inputs=@(Get-W01QualifiedSources $PSScriptRoot)
    $fixture=Join-Path $archive 'live-fixture.py'
    $out=Join-Path $archive 'fixture.stdout.txt'; $err=Join-Path $archive 'fixture.stderr.txt'
    $events=Join-Path $archive 'fixture.jsonl'; $stop=Join-Path $archive 'fixture.stop'
    $listener=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,0)
    try { $listener.Start(); $port=([Net.IPEndPoint]$listener.LocalEndpoint).Port } finally { $listener.Stop() }
    @'
import json, os, pathlib, sys
from wsgiref.simple_server import make_server
from runpy import run_path
src, port, events, stop = sys.argv[1:]
ready = run_path(src)["w01_ready"]
def guard(environ, start_response):
    response = ready(environ, start_response)
    if response is not None:
        return response
    start_response("404 Not Found", [])
    return []
with make_server("127.0.0.1", int(port), guard) as server, open(events, "x", encoding="utf-8") as stream:
    server.timeout = .10
    print(json.dumps({"event":"ready","pid":os.getpid()}), file=stream, flush=True)
    print("STORY25_W01_SMOKE_READY", flush=True)
    while not pathlib.Path(stop).exists():
        print("stdout-tick", flush=True)
        print("stderr-tick", file=sys.stderr, flush=True)
        server.handle_request()
    print(json.dumps({"event":"stop"}), file=stream, flush=True)
    print("stdout-stop", flush=True)
    print("stderr-stop", file=sys.stderr, flush=True)
'@ | Set-Content -LiteralPath $fixture -Encoding ASCII
    $proc=Start-W01Redirected $FixturePython $PSScriptRoot @('-B','-X','utf8',$fixture,
        (Join-Path $PSScriptRoot 'serve-story-2-5-w01-smoke.py'),"$port",$events,$stop) $out $err -Async
    $originalReadBlocked=$false
    try {
        $httpPid=Wait-W01HttpReady $proc $port
        $event=Read-W01SharedFirstLine $events | ConvertFrom-Json
        Verify-Encoding ($event.event -ceq 'ready' -and $event.pid -eq $proc.Id -and [string]$event.pid -ceq $httpPid) 'HTTP 204 and shared live readiness receipt match actual process PID'
        try { $null=[IO.File]::ReadAllBytes($out) } catch {
            $e=$_.Exception
            if ($e.InnerException) { $e=$e.InnerException }
            if ($e -isnot [IO.IOException] -or (($e.HResult -band 65535) -notin 32,33)) { throw }
            $originalReadBlocked=$true
        }
        # Only the test tries the old read. A sharing result depends on the Windows launcher.
        Verify-Encoding (-not $proc.HasExited) 'Actual redirected writer still running'
        Start-Sleep -Milliseconds 350
    } finally {
        [IO.File]::WriteAllText($stop,'stop',$script:W01StrictUtf8)
        if (-not $proc.WaitForExit(6000)) { Stop-Process -Id $proc.Id; throw 'Fixture failed to stop within six seconds' }
    }
    Write-W01NativeReceipt (Join-Path $archive 'fixture.native.json') $out $err $proc.ExitCode 'UTF-8 after child exit' 'raw after child exit'
    $lines=@(Read-W01Lines $out); $stderr=@(Read-W01Lines $err)
    Assert-W01Marker $lines $proc.ExitCode 'STORY25_W01_SMOKE_READY'
    $writes=@($lines | Where-Object {$_ -ceq 'stdout-tick'}).Count -ge 2 -and @($stderr | Where-Object {$_ -ceq 'stderr-tick'}).Count -ge 2
    Verify-Encoding ($writes -and $lines[-1] -ceq 'stdout-stop' -and $stderr[-1] -ceq 'stderr-stop' -and
        (@(Read-W01Lines $events)[-1] | ConvertFrom-Json).event -ceq 'stop') 'Continuous stdout/stderr then complete normal stop'
    foreach ($path in @($out,$err,$events)) {
        $handle=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::None)
        $handle.Dispose()
    }
    Verify-Encoding $true 'Exclusive opens succeed after stop; no outstanding handles'
    Verify-Encoding (($inputs -join "`n") -ceq ((Get-W01QualifiedSources $PSScriptRoot) -join "`n")) 'Inputs unchanged throughout the live test'
    [ordered]@{http_status=204;process_exit=$proc.ExitCode;pid=$proc.Id;port=$port;shared_receipt=$true;
        exclusive_after_exit=$true;live_writes_on_both_streams=$writes;old_read_sharing_violation=$originalReadBlocked} |
        ConvertTo-Json -Compress | Set-Content -LiteralPath (Join-Path $archive 'live-io.json') -Encoding UTF8
    $inputs | Set-Content -LiteralPath (Join-Path $archive 'live-io-inputs.sha256') -Encoding UTF8
    'STORY25_W01_LIVE_IO_OK' | Set-Content -LiteralPath (Join-Path $archive 'batch-marker.txt') -Encoding UTF8
    'STORY25_W01_LIVE_IO_OK'
    return
}
$cn = ([string][char]0x4e2d)+[char]0x6587
$content = "$cn English"
$legacy = [Text.Encoding]::GetEncoding(936,[Text.EncoderFallback]::ExceptionFallback,[Text.DecoderFallback]::ExceptionFallback)
$rawUtf = Join-Path $archive 'control.utf8.raw'
$rawCp = Join-Path $archive 'native.cp936.raw'
$bad = Join-Path $archive 'malformed-utf8.raw'
$json = Join-Path $archive 'protocol.json'
[IO.File]::WriteAllBytes($rawUtf,$script:W01StrictUtf8.GetBytes("$content`r`nSTORY25_ENCODING_FIXTURE`r`n"))
[IO.File]::WriteAllBytes($rawCp,$legacy.GetBytes("$content`r`nERROR: P0001: expected diagnostic`r`n"))
[IO.File]::WriteAllBytes($bad,[byte[]]@(0xE4,0xB8,0x0D,0x0A))
@{message=$content} | ConvertTo-Json -Compress | Set-Content -LiteralPath $json -Encoding UTF8
$hash = (Get-FileHash -LiteralPath $rawCp).Hash
Verify-Encoding ((@(Read-W01Lines $rawUtf)[0] -ceq $content)) 'UTF-8 Chinese, English and CRLF'
Verify-Encoding (((Read-W01Text $json | ConvertFrom-Json).message -ceq $content)) 'UTF-8 BOM JSON round trip'
Verify-Encoding (((Read-W01Text $rawCp 'NativeDiagnostic' 936).StartsWith($content))) 'CP936 native UTF-8-independent diagnostics'
Verify-Encoding (Test-W01AsciiDiagnostic $rawCp '(?m)^ERROR: P0001: expected diagnostic\r?$') 'ASCII diagnostic token on raw CP936'
$fail = $false
try { $null = Read-W01Text $bad } catch { $fail = $_.Exception.Message -match 'CP65001.*Raw SHA256=' }
Verify-Encoding $fail 'Malformed UTF-8 rejected with source/hash'
$fail = $false
try { $null = Read-W01Text $rawCp } catch { $fail = $_.Exception.Message -match 'CP65001.*Raw SHA256=' }
Verify-Encoding $fail 'No fallback for machine protocol'
Verify-Encoding ((Get-FileHash -LiteralPath $rawCp).Hash -ceq $hash) 'Raw SHA256 unchanged'
if ($ReferenceInitLog) {
    $raw = [IO.File]::ReadAllBytes($ReferenceInitLog)
    $translated = Read-W01Text $ReferenceInitLog 'NativeDiagnostic' 936
    Verify-Encoding ($raw[0] -eq 0xB4 -and [Convert]::ToBase64String($raw) -ceq [Convert]::ToBase64String($legacy.GetBytes($translated))) 'Actual initdb capture strictly round trips CP936'
}
$child = Join-Path $archive 'native-exit-fixture.ps1'
@'
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false,$true)
$c=([string][char]0x4e2d)+[char]0x6587
[Console]::WriteLine($c + ' English')
[Console]::WriteLine('STORY25_ENCODING_FIXTURE')
[Console]::Error.WriteLine($c + ' error')
exit 23
'@ | Set-Content -LiteralPath $child -Encoding ASCII
$childOut=Join-Path $archive 'child.stdout.raw'
$childErr=Join-Path $archive 'child.stderr.raw'
$proc=Start-Process (Join-Path $PSHOME 'powershell.exe') -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -File "'+$child+'"') -PassThru -Wait -WindowStyle Hidden -RedirectStandardOutput $childOut -RedirectStandardError $childErr
Write-W01NativeReceipt (Join-Path $archive 'child.native.json') $childOut $childErr $proc.ExitCode 'UTF-8' 'UTF-8'
$lines=@(Read-W01Lines $childOut)
Verify-Encoding ($proc.ExitCode -eq 23 -and $lines[0] -ceq $content -and @(Read-W01Lines $childErr)[0] -ceq "$cn error") 'Actual child stdout/stderr UTF-8 and exit 23 preserved'
$fail=$false
try { Assert-W01Marker $lines $proc.ExitCode 'STORY25_ENCODING_FIXTURE' } catch { $fail=$_.Exception.Message -match 'exit=23' }
Verify-Encoding $fail 'Failure with plausible success text still fails'
$fail=$false
try { Assert-W01Marker @($lines[1],$lines[1]) 0 'STORY25_ENCODING_FIXTURE' } catch { $fail=$true }
Verify-Encoding $fail 'Repeated success marker rejected'
'STORY25_W01_ENCODING_OK' | Set-Content -LiteralPath (Join-Path $archive 'batch-marker.txt') -Encoding UTF8
'STORY25_W01_ENCODING_OK'
