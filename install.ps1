# Installs ROLI for Live into the Ableton User Library (Windows).
# Usage: powershell -ExecutionPolicy Bypass -File install.ps1 [-UserLibrary "D:\path\to\User Library"]
# (In a release download, just double-click "Install on Windows.cmd".)
param([string]$UserLibrary)

$ErrorActionPreference = 'Stop'

# Works from a git checkout (src\ROLI_for_Live) and from a release zip (ROLI_for_Live).
$src = @((Join-Path $PSScriptRoot 'ROLI_for_Live'), (Join-Path $PSScriptRoot 'src\ROLI_for_Live')) |
    Where-Object { Test-Path (Join-Path $_ '__init__.py') } | Select-Object -First 1
if (-not $src) { throw "Can't find the ROLI_for_Live folder next to this installer." }

if (Get-Process | Where-Object { $_.ProcessName -like 'Ableton Live*' }) {
    Write-Host 'Ableton Live is running. Please quit Live first, then press Enter to continue.' -ForegroundColor Yellow
    [void](Read-Host)
}

if (-not $UserLibrary) {
    # The newest Live preferences folder's Library.cfg holds the User Library location.
    $prefs = Get-ChildItem "$env:APPDATA\Ableton\Live *\Preferences\Library.cfg" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($prefs) {
        $m = [regex]::Match((Get-Content $prefs.FullName -Raw), '(?s)<UserLibrary>.*?<ProjectPath Value="([^"]+)"')
        if ($m.Success) { $UserLibrary = Join-Path $m.Groups[1].Value 'User Library' }
    }
    if (-not $UserLibrary) { $UserLibrary = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Ableton\User Library' }
}

$dest = Join-Path $UserLibrary 'Remote Scripts\ROLI_for_Live'
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Get-ChildItem $src -File -Filter '*.py' | Copy-Item -Destination $dest -Force

Write-Host ''
Write-Host "ROLI for Live installed to: $dest" -ForegroundColor Green
Write-Host ''
Write-Host 'Next, once only:'
Write-Host '  1. Connect your ROLI keyboard and start Ableton Live.'
Write-Host '  2. Settings > Tempo & MIDI: in an empty Control Surface row choose "ROLI for Live",'
Write-Host '     with Input and Output "ROLI Piano".'
Write-Host '  3. Under Input Ports, turn on Track and MPE for "ROLI Piano".'
