@echo off
rem ============================================================
rem  VGGT Module 2 (AI output) unit-test launcher
rem  This file is intentionally ASCII-only: cmd.exe codepage
rem  switching corrupts non-ASCII text in .bat files. All the
rem  Chinese output is produced by run_tests.ps1 instead.
rem
rem  Usage:
rem    double-click            -> run all M2-AI-* cases
rem    run_tests.bat -Prepare:$false  -> skip GPU data generation
rem ============================================================
chcp 65001 >nul
setlocal

set "SCRIPT_DIR=%~dp0"
set "PS_EXE="

where pwsh >nul 2>nul
if %ERRORLEVEL% EQU 0 set "PS_EXE=pwsh"
if defined PS_EXE goto :run

where powershell >nul 2>nul
if %ERRORLEVEL% EQU 0 set "PS_EXE=powershell"
if defined PS_EXE goto :run
goto :nops

:run
"%PS_EXE%" -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%run_tests.ps1" %*
set "RC=%ERRORLEVEL%"
goto :report

:nops
echo [ERROR] PowerShell was not found on this machine.
echo         Please run run_tests.ps1 manually with a PowerShell host.
set "RC=3"

:report
echo.
echo Exit code: %RC%   [0=all passed, 1=failures, 2=project incomplete, 3=import failed]
if "%~1"=="" pause
exit /b %RC%
