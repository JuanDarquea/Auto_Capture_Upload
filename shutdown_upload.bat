@echo off
echo ================================================
echo Screenshot Upload - SHUTDOWN MODE (Enhanced) 
echo Time: %date% %time%
echo ================================================

cd /d "C:\Users\USUARIO\OneDrive\Documentos\My_Projects\Projects\Automation_Screen_Captures"
python fixed_uploader.py --mode shutdown --silent

echo.
echo ================================================
echo Shutdown upload process completed
echo ================================================

echo.
echo ================================================
echo Quick log check...
echo ================================================

REM Quick log check (faster for shutdown)
if exist execution_log.txt (
    echo ✅ Found execution_log.txt
    echo Last 2 entries:
    powershell "Get-Content execution_log.txt | Select-Object -Last 2"
) esle (
    echo execution_log.txt not found
    echo Looking in: %cd%
)

if exist detailed_execution_log.json (
    echo ✅ Found detailed_execution_log.json
) else (
    echo ❌ detailed_execution_log.json not found
)

echo Upload completed at %date% %time% >> upload_history.log
echo Shutdown process completed at %time%
timeout /t 2 /nobreak >nul
REM Brief pause then close automatically
REM Only 2 seconds here - shutdown scripts have time limits!