# W01 wire formats. Raw capture files are never rewritten by these readers.
$script:W01StrictUtf8 = [Text.UTF8Encoding]::new($false,$true)
function Set-W01WireEncoding {
    [Console]::OutputEncoding = $script:W01StrictUtf8
    $script:OutputEncoding = $script:W01StrictUtf8
}
function Get-W01NativeCodePage {
    # Windows PowerShell 5.1 runs on .NET Framework, where Default is the OS ACP.
    if ($PSVersionTable.PSEdition -ne 'Desktop') { throw 'Use Windows PowerShell 5.1 for Windows ACP diagnostics.' }
    [Text.Encoding]::Default.CodePage
}
function Read-W01Text([string]$Path,[ValidateSet('Utf8','Ascii','NativeDiagnostic')][string]$Profile='Utf8',
    [int]$NativeCodePage=0) {
    $bytes = [IO.File]::ReadAllBytes($Path)
    $offset = 0
    $codec = $script:W01StrictUtf8
    if ($Profile -ceq 'Ascii') {
        $codec = [Text.Encoding]::GetEncoding(20127,[Text.EncoderFallback]::ExceptionFallback,[Text.DecoderFallback]::ExceptionFallback)
    } elseif ($bytes.Length -ge 3 -and $bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191) {
        $offset = 3
    } elseif ($Profile -ceq 'NativeDiagnostic') {
        if (-not $NativeCodePage) { $NativeCodePage = Get-W01NativeCodePage }
        $codec = [Text.Encoding]::GetEncoding($NativeCodePage,[Text.EncoderFallback]::ExceptionFallback,[Text.DecoderFallback]::ExceptionFallback)
    }
    try {
        $codec.GetString($bytes,$offset,$bytes.Length-$offset)
    } catch {
        throw "W01 log decode failed for '$Path' using $Profile (CP$($codec.CodePage)). Raw SHA256=$((Get-FileHash -LiteralPath $Path).Hash). $($_.Exception.Message)"
    }
}
function Read-W01Lines([string]$Path,[ValidateSet('Utf8','Ascii','NativeDiagnostic')][string]$Profile='Utf8') {
    $reader = [IO.StringReader]::new((Read-W01Text $Path $Profile))
    try {
        while ($null -ne ($line = $reader.ReadLine())) { $line }
    } finally { $reader.Dispose() }
}
function Test-W01AsciiDiagnostic([string]$Path,[string]$Pattern) {
    # The regex is a fixed ASCII machine token. ISO-8859-1 is a reversible byte
    # projection for matching that token in native stderr, not a text decoder.
    if ($Pattern -match '[^\x00-\x7F]') { throw 'Diagnostic patterns must be ASCII.' }
    $wire = [Text.Encoding]::GetEncoding(28591).GetString([IO.File]::ReadAllBytes($Path))
    [regex]::IsMatch($wire,$Pattern)
}
function Write-W01NativeReceipt([string]$Path,[string]$Stdout,[string]$Stderr,[Nullable[int]]$Code,
    [string]$StdoutProfile,[string]$StderrProfile) {
    if ($null -eq $Code) { throw 'Native exit code unavailable; do not certify these logs.' }
    [ordered]@{exit=$Code;stdout_profile=$StdoutProfile;stderr_profile=$StderrProfile;
        stdout_bytes=(Get-Item -LiteralPath $Stdout).Length;stderr_bytes=(Get-Item -LiteralPath $Stderr).Length;
        stdout_sha256=(Get-FileHash -LiteralPath $Stdout).Hash;stderr_sha256=(Get-FileHash -LiteralPath $Stderr).Hash} |
        ConvertTo-Json -Compress | Set-Content -LiteralPath $Path -Encoding UTF8
}
function Assert-W01Marker($Lines,[Nullable[int]]$ExitCode,[string]$Marker) {
    if ($null -eq $ExitCode -or $ExitCode -ne 0 -or @($Lines | Where-Object { $_ -ceq $Marker }).Count -ne 1) {
        throw "W01 marker check failed: exit=$ExitCode expected=$Marker"
    }
}

# Only for a running process's dedicated receipt, never its redirected stdout/stderr.
function Read-W01SharedFirstLine([string]$Path,[switch]$Ascii) {
    $codec=$script:W01StrictUtf8
    if ($Ascii) { $codec=[Text.Encoding]::GetEncoding(20127,[Text.EncoderFallback]::ExceptionFallback,[Text.DecoderFallback]::ExceptionFallback) }
    $file=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
    try {
        $lineReader=[IO.StreamReader]::new($file,$codec,$false)
        try { $lineReader.ReadLine() } finally { $lineReader.Dispose() }
    } finally { $file.Dispose() }
}

function Start-W01Redirected([string]$File,[string]$WorkingDirectory,[string[]]$Argv,
    [string]$Stdout,[string]$Stderr,[switch]$Async) {
    if (@($Argv | Where-Object { $_ -match '["\r\n]' }).Count -or (Test-Path -LiteralPath $Stdout) -or (Test-Path -LiteralPath $Stderr)) {
        throw 'Unexpected native argument quoting or existing raw output.'
    }
    $options=@{FilePath=$File;WorkingDirectory=$WorkingDirectory;
        ArgumentList=(($Argv | ForEach-Object { '"' + $_ + '"' }) -join ' ');
        RedirectStandardOutput=$Stdout;RedirectStandardError=$Stderr;PassThru=$true;WindowStyle='Hidden'}
    if (-not $Async) { $options.Wait=$true }
    $process=Start-Process @options
    if ($Async) { $null=$process.Handle }  # Keep a real process handle for ExitCode after an async Windows launch.
    $process
}

function Wait-W01HttpReady($Process,[int]$Port,[int]$Seconds=15) {
    $end=[DateTime]::UtcNow.AddSeconds($Seconds)
    while ([DateTime]::UtcNow -lt $end) {
        $Process.Refresh()
        if ($Process.HasExited) { throw "Guarded server exited before HTTP readiness: $($Process.ExitCode)" }
        $req=[Net.HttpWebRequest][Net.WebRequest]::Create("http://127.0.0.1:$Port/__w01_ready")
        $req.Proxy=$null; $req.Method='HEAD'; $req.AllowAutoRedirect=$false; $req.Timeout=500; $req.KeepAlive=$false
        try {
            $res=$req.GetResponse()
            try {
                $pidHeader=$res.Headers['X-W01-Ready']
                if ([int]$res.StatusCode -ne 204 -or $pidHeader -cnotmatch '^[1-9][0-9]{0,9}$') {
                    throw 'Unexpected W01 HTTP readiness response; do not trust this listener.'
                }
                return $pidHeader
            } finally { $res.Dispose() }
        } catch [Net.WebException] {
            # Expected only while the known process is still starting.
            if ($_.Exception.Response) { $_.Exception.Response.Dispose() }
            if ($_.Exception.Status -notin [Net.WebExceptionStatus]::ConnectFailure,[Net.WebExceptionStatus]::Timeout) { throw }
        }
        Start-Sleep -Milliseconds 150
    }
    throw 'W01 HTTP readiness timed out.'
}
