@echo off
rem AutoNovel local launcher - thin wrapper around scripts\start_local.ps1 (Step 5)
rem Double-clicking this file starts Backend + Huey Worker + Frontend.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\start_local.ps1"
pause
