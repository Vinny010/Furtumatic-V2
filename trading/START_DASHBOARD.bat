@echo off
REM ============================================================
REM  Sat Stacker — live paper-trading grid dashboard (Windows)
REM  Double-click this file. It runs the bot on LIVE Binance
REM  prices with fake money and opens the window automatically.
REM  No API keys, no real money, no orders are ever sent.
REM  Close this black window (or press Ctrl+C) to stop.
REM ============================================================
cd /d "%~dp0"

REM --- find Python ---
where python >nul 2>&1
if %errorlevel%==0 (
  set PY=python
) else (
  where py >nul 2>&1
  if %errorlevel%==0 (
    set PY=py
  ) else (
    echo.
    echo   Python is not installed.
    echo   Get it free from https://www.python.org/downloads/
    echo   IMPORTANT: on the first install screen, tick
    echo   "Add python.exe to PATH", then re-run this file.
    echo.
    start "" "https://www.python.org/downloads/"
    pause
    exit /b
  )
)

echo.
echo   Starting live paper dashboard on BTCUSDT...
echo   A browser window will open in a few seconds.
echo   Leave this black window open while it runs.
echo.
%PY% grid_dashboard.py --live --symbol BTCUSDT --step 0.004
pause
