@echo off
setlocal

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 run.py
  exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python run.py
  exit /b %ERRORLEVEL%
)

where python3 >nul 2>nul
if %ERRORLEVEL%==0 (
  python3 run.py
  exit /b %ERRORLEVEL%
)

set CODEX_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
if exist "%CODEX_PY%" (
  "%CODEX_PY%" run.py
  exit /b %ERRORLEVEL%
)

echo Python was not found.
echo Install Python 3.11+ from https://www.python.org/downloads/
echo During install, check: Add python.exe to PATH
exit /b 1
