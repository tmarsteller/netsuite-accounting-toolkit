# setup.ps1 — one-time setup for netsuite-file-attach (Windows)
#
# What this script does (and nothing else):
#   1. Checks that Python 3 is installed (offers to install it via winget)
#   2. Installs the Python dependencies from requirements.txt
#   3. Creates .env from .env.example and prompts you for your credentials
#   4. Optionally installs this folder as a Claude Code skill
#
# It never sends your credentials anywhere — they are only written to the
# local .env file. Run it again any time; existing values are kept unless
# you type new ones.
#
# Easiest way to run: double-click setup.bat in this folder.

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

function Write-Step([string]$Text) { Write-Host "`n== $Text ==" -ForegroundColor Cyan }
function Write-Ok([string]$Text)   { Write-Host "   $Text" -ForegroundColor Green }
function Write-Warn2([string]$Text){ Write-Host "   $Text" -ForegroundColor Yellow }

Write-Host 'netsuite-file-attach setup' -ForegroundColor Cyan
Write-Host 'This sets up the Python client. The RESTlet itself must be deployed'
Write-Host 'in NetSuite by your administrator first (see README, Part 1).'

# ---------------------------------------------------------------- 1. Python
Write-Step 'Checking for Python 3'

$script:PyExe  = $null
$script:PyArgs = @()

foreach ($candidate in @('py', 'python', 'python3')) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($null -eq $cmd) { continue }
    # Skip the Microsoft Store stub that just opens the Store window
    if ($cmd.Source -like '*WindowsApps*' -and (Get-Item $cmd.Source).Length -eq 0) { continue }
    try {
        if ($candidate -eq 'py') { $ver = & py -3 --version 2>&1 }
        else                     { $ver = & $candidate --version 2>&1 }
    } catch { continue }
    if ("$ver" -match 'Python 3\.') {
        if ($candidate -eq 'py') { $script:PyExe = 'py'; $script:PyArgs = @('-3') }
        else                     { $script:PyExe = $candidate }
        Write-Ok "Found $ver"
        break
    }
}

if ($null -eq $script:PyExe) {
    Write-Warn2 'Python 3 was not found on this computer.'
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($null -ne $winget) {
        $answer = Read-Host '   Install Python 3.12 automatically now? (Y/n)'
        if ($answer -eq '' -or $answer -match '^[Yy]') {
            winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
            Write-Warn2 'Python installed. Please close this window and run setup.bat again'
            Write-Warn2 '(a fresh window is needed so Windows can find Python).'
            exit 0
        }
    }
    Write-Warn2 'Opening the official Python download page. Install Python'
    Write-Warn2 '(check "Add python.exe to PATH" on the first screen!),'
    Write-Warn2 'then run setup.bat again.'
    Start-Process 'https://www.python.org/downloads/'
    exit 1
}

function Invoke-Py { & $script:PyExe @($script:PyArgs + $args) }

# ---------------------------------------------------------- 2. Dependencies
Write-Step 'Installing Python dependencies (requests, requests-oauthlib)'
Invoke-Py -m pip install --disable-pip-version-check -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Warn2 'Standard install failed, retrying with --user ...'
    Invoke-Py -m pip install --disable-pip-version-check --user -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'pip install failed - see the messages above.' }
}
Write-Ok 'Dependencies installed.'

# ------------------------------------------------------------- 3. .env file
Write-Step 'Setting up your credentials (.env)'

if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    Write-Ok 'Created .env from the template.'
}

function Get-DotEnvValue([string]$Key) {
    $line = Get-Content '.env' | Where-Object { $_ -match "^\s*$([regex]::Escape($Key))=" } | Select-Object -First 1
    if ($null -eq $line) { return '' }
    return ($line -split '=', 2)[1].Trim()
}

function Set-DotEnvValue([string]$Key, [string]$Value) {
    $found = $false
    $newLines = foreach ($line in (Get-Content '.env')) {
        if (-not $found -and $line -match "^\s*$([regex]::Escape($Key))=") { $found = $true; "$Key=$Value" }
        else { $line }
    }
    if (-not $found) { $newLines = @($newLines) + "$Key=$Value" }
    Set-Content -Path '.env' -Value $newLines -Encoding ASCII
}

function Read-EnvVar([string]$Key, [string]$Label, [string]$OptionalNote) {
    $current = Get-DotEnvValue $Key
    if ($current -ne '') {
        $entry = Read-Host "   $Label (already set - press Enter to keep)"
    } elseif ($OptionalNote -ne '') {
        $entry = Read-Host "   $Label ($OptionalNote - press Enter to skip)"
    } else {
        $entry = Read-Host "   $Label"
    }
    if ($entry.Trim() -ne '') { Set-DotEnvValue $Key $entry.Trim() }
}

Write-Host '   Paste the five values from your NetSuite administrator.'
Write-Host '   (They are saved only to the local .env file in this folder.)'
Read-EnvVar 'NS_ACCOUNT_ID'      'Account ID (e.g. 1234567 or 1234567-sb1)' ''
Read-EnvVar 'NS_CONSUMER_KEY'    'Consumer key'    ''
Read-EnvVar 'NS_CONSUMER_SECRET' 'Consumer secret' ''
Read-EnvVar 'NS_TOKEN_ID'        'Token ID'        ''
Read-EnvVar 'NS_TOKEN_SECRET'    'Token secret'    ''
Read-EnvVar 'NS_DEFAULT_FOLDER_ID' 'Default File Cabinet folder ID' 'optional but recommended'

$missing = @('NS_ACCOUNT_ID','NS_CONSUMER_KEY','NS_CONSUMER_SECRET','NS_TOKEN_ID','NS_TOKEN_SECRET') |
    Where-Object { (Get-DotEnvValue $_) -eq '' }
if ($missing.Count -gt 0) {
    Write-Warn2 ('Still missing: ' + ($missing -join ', ') + ' - run setup.bat again when you have them.')
} else {
    Write-Ok 'All five credentials are set.'
}

# ----------------------------------------------- 4. Claude Code skill (opt.)
Write-Step 'Claude Code skill (optional)'
Write-Host '   If you use Claude Code, this lets you just ask in plain English,'
Write-Host '   e.g. "attach this workbook to journal entry 4242".'
$answer = Read-Host '   Install as a Claude Code skill? (y/N)'
if ($answer -match '^[Yy]') {
    $dest = Join-Path $env:USERPROFILE '.claude\skills\netsuite-file-attach'
    robocopy $PSScriptRoot $dest /E /XD .git /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -lt 8) { Write-Ok "Skill installed to $dest"; $global:LASTEXITCODE = 0 }
    else { Write-Warn2 'Copy reported a problem - you can copy the folder there manually.' }
}

# ------------------------------------------------------------------ Summary
Write-Step 'Done'
if ($missing.Count -eq 0) {
    Write-Host '   Try it with any small PDF or spreadsheet:'
    if ($script:PyArgs.Count -gt 0) { $pyShown = "$($script:PyExe) $($script:PyArgs -join ' ')" } else { $pyShown = $script:PyExe }
    if ((Get-DotEnvValue 'NS_DEFAULT_FOLDER_ID') -ne '') {
        Write-Host "     $pyShown attach_file.py --file `"test.pdf`"" -ForegroundColor White
    } else {
        Write-Host "     $pyShown attach_file.py --file `"test.pdf`" --folder-id <folder id>" -ForegroundColor White
    }
    Write-Host '   Expected output:  OK - fileId=12345 attached=False'
}
Write-Host '   Reminder: the RESTlet must be deployed in NetSuite (README, Part 1)'
Write-Host '   before uploads will work.'
exit 0
