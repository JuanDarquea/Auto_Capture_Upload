@echo off
REM This hides the commands from showing up, so you only see our custom output

echo ================================================
echo Screenshot Upload - MANUAL MODE (Enhanced)
echo Time: %date% %time%
echo ================================================

cd /d "C:\Users\USUARIO\OneDrive\Documentos\My_Projects\Projects\Automation_Screen_Captures"
python fixed_uploader.py

echo.
echo ================================================
echo Upload process completed
echo Upload completed at %date% %time% >> upload_history.log
echo ================================================

echo.
echo ================================================
echo Checking execution logs...
echo ================================================

if exist execution_log.txt (
    echo Found execution_log.txt
    echo Latest log entries:
    powershell "Get-Content execution_log.txt | Select-Object -Last 5"
) else (
    echo execution_log.txt not found
    echo Looking in: %cd%
)

if exist detailed_execution_log.json (
    echo Found detailed_execution_log.json
) else (
    echo ❌ detailed_execution_log.json not found
)

echo.
echo Upload process completed at %time%
pause
timeout /t 3 /nobreak >nul