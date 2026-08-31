#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Cleanly stop all hometools streaming server processes (serve-all,
    serve-audio, serve-video, serve-channel), including the venv-wrapper
    plus real-interpreter child pairs each one spawns on Windows.

.DESCRIPTION
    "Stop-Process -Name python" is unsafe on a dev machine -- it kills every
    Python process (PyCharm's own interpreter, unrelated scripts, ...).
    This script matches on the process COMMAND LINE instead
    ("hometools.cli serve-all" / "hometools serve-audio" / "serve-video" /
    "serve-channel"), so only actual hometools streaming servers are hit.

.EXAMPLE
    pwsh scripts/stop-streaming.ps1
#>

$hmtPattern = 'hometools(\.cli)?\s+serve-(all|audio|video|channel)'

$hmtProcs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match $hmtPattern }

if (-not $hmtProcs) {
    Write-Host "No hometools streaming server processes found."
    exit 0
}

Write-Host "Stopping $($hmtProcs.Count) hometools streaming process(es):"
foreach ($p in $hmtProcs) {
    Write-Host "  PID $($p.ProcessId): $($p.CommandLine)"
}

foreach ($p in $hmtProcs) {
    try {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
    } catch {
        # Already exited (e.g. parent killed before child polled) -- ignore.
    }
}

Start-Sleep -Milliseconds 500
$stillAlive = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match $hmtPattern }
if ($stillAlive) {
    Write-Warning "$($stillAlive.Count) process(es) still alive after stop -- retrying once."
    foreach ($p in $stillAlive) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
}

Write-Host "Done."


