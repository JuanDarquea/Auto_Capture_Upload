@echo off
REM This hides the commands from showing up, so you only see our custom output

echo ================================================
echo Screenshot Upload - STARTUP MODE (Enhanced)
echo Time: %date% %time%
echo ================================================
REM Always good to timestamp when automation runs - helps with debugging

cd /d "C:\Users\USUARIO\OneDrive\Documentos\My_Projects\Projects\Automation_Screen_Captures"
REM /d flag changes both drive AND directory in one command
REM Critical: This ensures Python can find your script and credential files

python fixed_uploader.py --mode startup --silent
REM Here's where we call your script with the specific mode

echo.
echo ================================================
echo Startup upload process completed
echo ================================================

echo.
echo ================================================
echo Checking execution logs...
echo ================================================

REM Show the last few lines of the log file
if exist execution_log.txt (
    echo Latest log entries:
    powershell "Get-Content execution_log.txt | Select-Object -Last 3"
) else (
    echo No log file found yet.
)

echo.
echo Startup process completed at %time%
pause
timeout /t 5 /nobreak >nul
REM Give user 5 seconds to see the results before window closes
REM /nobreak means they can't cancel the timeout
REM >nul means don't show the countdown