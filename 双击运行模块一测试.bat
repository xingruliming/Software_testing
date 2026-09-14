@echo off
chcp 65001 >nul
setlocal
set "PYTHONIOENCODING=utf-8"

rem =====================================================================
rem  VGGT Module 1 launcher - double-click entry point
rem
rem  ASCII ONLY BY DESIGN. cmd.exe parses .bat files using DBCS byte
rem  offsets; after `chcp 65001` it can split a multi-byte UTF-8 character
rem  across its read buffer and execute the line tail as a command. Keeping
rem  every parsed byte inside 0x20-0x7E removes that failure class.
rem
rem  All Chinese output comes from run_tests.ps1 and the Python test
rem  runner, which write UTF-8 explicitly.
rem
rem  Usage: just double-click this file.
rem
rem  Exit codes (identical to run_tests.ps1):
rem    0 = all cases passed
rem    1 = failures / errors present
rem    2 = test project not found
rem    3 = cannot import the module under test
rem =====================================================================

rem  Switch to this file's own directory (the repo root) so that every
rem  relative path below resolves regardless of the shortcut's start-in dir.
cd /d "%~dp0"

title VGGT Module 1 - Coordinate Transform : One-Click Test

echo.
echo [1/3] Checking prerequisites ...

rem --- 1. run_tests.ps1 must sit next to this launcher --------------------
if not exist "%~dp0run_tests.ps1" goto :no_script

rem --- 2. Locate PowerShell ----------------------------------------------
rem  Prefer pwsh (PowerShell 7+); fall back to the inbox powershell.exe.
echo [2/3] Locating PowerShell ...

set "PSEXE="
where pwsh >nul 2>nul
if %ERRORLEVEL% EQU 0 set "PSEXE=pwsh"
if not defined PSEXE where powershell >nul 2>nul
if not defined PSEXE if %ERRORLEVEL% EQU 0 set "PSEXE=powershell"

if not defined PSEXE goto :no_powershell

echo        using: %PSEXE%
echo.
echo [3/3] Running the Module 1 test suite ...
echo.

rem --- 3. Run the one-click test script ----------------------------------
rem  -NoProfile                skip the user profile, avoid environment noise
rem  -ExecutionPolicy Bypass   allow this run only, change nothing system-wide
"%PSEXE%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_tests.ps1"
set "TEST_EXIT=%ERRORLEVEL%"

rem --- 4. Report the outcome and hold the window open --------------------
echo.
if "%TEST_EXIT%"=="0" goto :pass
if "%TEST_EXIT%"=="1" goto :fail
if "%TEST_EXIT%"=="2" goto :no_tests
if "%TEST_EXIT%"=="3" goto :no_module
goto :other

:pass
echo ====================================================================
echo   RESULT: ALL CASES PASSED  (exit code 0)
echo ====================================================================
echo   Results archived in: test_results\module1\
echo.
pause
exit /b 0

:fail
echo ====================================================================
echo   RESULT: SOME CASES FAILED  (exit code 1)
echo ====================================================================
echo   A failing test is not automatically a valid defect: a valid defect
echo   needs reproduce / analyse / fix / retest, with evidence retained.
echo   See the ERROR detail above and test_results\module1\.
echo.
echo   M1-GEO-016 and M1-GEO-018 fail on the open defect DEF-M1-001.
echo.
pause
exit /b 1

:no_tests
echo ====================================================================
echo   RESULT: TEST PROJECT NOT FOUND  (exit code 2)
echo ====================================================================
echo   Check that the M1-GEO case files exist under
echo   tests\module1_coordinate\.
echo.
pause
exit /b 2

:no_module
echo ====================================================================
echo   RESULT: CANNOT IMPORT MODULE UNDER TEST  (exit code 3)
echo ====================================================================
echo   Check that Python can import vggt.utils.geometry, and that
echo   vggt-main\vggt\utils\geometry.py exists.
echo.
pause
exit /b 3

:other
echo ====================================================================
echo   RESULT: UNEXPECTED EXIT CODE %TEST_EXIT%
echo ====================================================================
echo.
pause
exit /b %TEST_EXIT%

:no_script
echo [ERROR] run_tests.ps1 was not found; it must sit next to this file.
echo         current directory: %CD%
echo.
goto :hold

:no_powershell
echo [ERROR] PowerShell was not found.
echo         Windows PowerShell is required to run the tests.
echo.
goto :hold

:hold
echo ====================================================================
echo   The run did not start. Fix the problem above and try again.
echo ====================================================================
echo.
pause
exit /b 9
