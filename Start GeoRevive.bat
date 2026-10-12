@echo off
REM GeoRevive Africa - start the app and open it in Microsoft Edge.
REM The backend (FastAPI) also serves the built web interface, so one window runs everything.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo GeoRevive is not set up yet. Run setup first:
  echo   powershell -ExecutionPolicy Bypass -File .\setup.ps1
  pause
  exit /b 1
)
if not exist "frontend\dist\index.html" (
  echo Building the web interface...
  pushd frontend
  call npm.cmd run build
  popd
)

echo Starting GeoRevive on http://127.0.0.1:8000 ...
start "GeoRevive server (close this window to stop)" ".venv\Scripts\python.exe" -m uvicorn georevive.api.app:app --host 127.0.0.1 --port 8000

REM wait until the server answers (up to ~60 s)
set /a tries=0
:wait
set /a tries+=1
powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/health -TimeoutSec 2) | Out-Null; exit 0 } catch { exit 1 }"
if %errorlevel%==0 goto open
if %tries% GEQ 30 goto open
timeout /t 2 /nobreak >nul
goto wait

:open
start "" msedge "http://127.0.0.1:8000/"
if errorlevel 1 start "" "http://127.0.0.1:8000/"
echo GeoRevive is running. Close the "GeoRevive server" window to stop it.
endlocal
