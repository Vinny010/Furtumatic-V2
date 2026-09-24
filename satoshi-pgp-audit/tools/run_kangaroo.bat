@echo off
REM ===================================================================
REM  24/7 Kangaroo supervisor for Windows - auto-restart + resume.
REM
REM  Runs JeanLucPons' CUDA Kangaroo (the FAST engine) against an
REM  exposed-pubkey puzzle, saving a work file periodically so a crash
REM  or reboot resumes instead of starting over. Edit the paths below.
REM
REM  Kangaroo work-file flags used:
REM    -w  work.kcp    save work here
REM    -wi 300         auto-save every 300 seconds
REM    -i  work.kcp    resume from it if present
REM ===================================================================

setlocal
set KANGAROO=C:\tools\Kangaroo\Kangaroo.exe
set INPUT=C:\tools\Kangaroo\puzzle135.txt   REM contains: start end pubkey
set WORK=C:\tools\Kangaroo\work.kcp
set LOG=C:\tools\Kangaroo\kangaroo.log

:loop
echo [%date% %time%] starting/resuming Kangaroo >> "%LOG%"
if exist "%WORK%" (
    "%KANGAROO%" -gpu -w "%WORK%" -wi 300 -i "%WORK%" "%INPUT%" >> "%LOG%" 2>&1
) else (
    "%KANGAROO%" -gpu -w "%WORK%" -wi 300 "%INPUT%" >> "%LOG%" 2>&1
)

echo [%date% %time%] Kangaroo exited (code %errorlevel%). Restarting in 10s... >> "%LOG%"
REM If it exited 0 with a key found, Kangaroo writes the key to its output; stop then.
findstr /C:"Key# " "%LOG%" >nul && (
    echo [%date% %time%] KEY FOUND - stopping supervisor. >> "%LOG%"
    goto :eof
)
timeout /t 10 /nobreak >nul
goto loop
