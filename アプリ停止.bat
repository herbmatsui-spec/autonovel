@echo off
rem AutoNovel stopper - thin wrapper around scripts\stop_local.ps1 (Step 6)
rem Gracefully terminates Backend (8200), Frontend (5173), and Huey processes.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\stop_local.ps1"
pause
