@echo off
rem Double-click to install ROLI for Live into your Ableton User Library.
title ROLI for Live installer
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if errorlevel 1 (
  echo.
  echo Installation failed. See the message above.
)
echo.
pause
