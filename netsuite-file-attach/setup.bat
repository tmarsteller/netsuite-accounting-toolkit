@echo off
rem One-click launcher for setup.ps1. PowerShell blocks scripts by default;
rem this runs it with that restriction bypassed for this one script only.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
echo.
pause
