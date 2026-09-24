@echo off
REM ===================================================================
REM  24/7 sequential brute-force supervisor for Windows - Rotor-CUDA.
REM
REM  For an ADDRESS-ONLY puzzle (no exposed pubkey, e.g. #72). Walks the
REM  range bottom-to-top in fixed blocks, persisting a CURSOR to a file
REM  so a crash/reboot resumes from where it left off instead of
REM  restarting. Each block is one Rotor-CUDA run over -range start:end.
REM
REM  This is the FAST engine (your GPU, ~1.7 Gkey/s). The Python
REM  spa.lab.sweep module is the reference/verify/bookkeeping half.
REM
REM  >>> EDIT the paths and the Rotor-CUDA flags to match YOUR build. <<<
REM  Rotor-Cuda flag names vary by fork; -range / -a (address) / -o are
REM  typical. Confirm with `Rotor-Cuda.exe -h` on your machine.
REM ===================================================================

setlocal enabledelayedexpansion
set ROTOR=C:\tools\Rotor-Cuda\Rotor-Cuda.exe
set ADDRESS=1JTK7s9YVYywfm5XUH7RNhHJH1LshCaRFR
set HI=ffffffffffffffffffff
REM  ^ #72 top of range (2^72 - 1). Bottom is 800000000000000000.
set CURSORFILE=C:\tools\Rotor-Cuda\cursor72.txt
set FOUND=C:\tools\Rotor-Cuda\found72.txt
set LOG=C:\tools\Rotor-Cuda\sweep72.log
REM  Block size in hex (how many keys per Rotor launch). 40000000000 = 2^42.
set BLOCK=40000000000

REM  Seed the cursor to the bottom of the #72 range on first run.
if not exist "%CURSORFILE%" echo 800000000000000000> "%CURSORFILE%"

:loop
if exist "%FOUND%" (
    echo [%date% %time%] KEY FOUND - see %FOUND%. Stopping. >> "%LOG%"
    goto :eof
)
set /p START=<"%CURSORFILE%"

REM  end = start + BLOCK, computed in PowerShell (batch can't do 72-bit math).
for /f %%E in ('powershell -NoProfile -Command ^
  "$s=[bigint]::Parse('0%START%',[System.Globalization.NumberStyles]::HexNumber); ^
   $b=[bigint]::Parse('0%BLOCK%',[System.Globalization.NumberStyles]::HexNumber); ^
   $hi=[bigint]::Parse('0%HI%',[System.Globalization.NumberStyles]::HexNumber); ^
   $e=$s+$b; if($e -gt $hi){$e=$hi}; $e.ToString('x')"') do set END=%%E

echo [%date% %time%] scanning %START% : %END% >> "%LOG%"
"%ROTOR%" -gpu -a "%ADDRESS%" -range %START%:%END% -o "%FOUND%" >> "%LOG%" 2>&1

REM  Advance the cursor to END, then loop. (Atomicity note: write temp+move.)
echo %END%> "%CURSORFILE%.tmp"
move /y "%CURSORFILE%.tmp" "%CURSORFILE%" >nul

REM  Stop if we've reached the top of the range.
if /i "%END%"=="%HI%" (
    echo [%date% %time%] reached top of range, sweep complete. >> "%LOG%"
    goto :eof
)
goto loop
