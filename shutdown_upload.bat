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
    echo Last entry:
    powershell "Get-Content execution_log.txt | Select-Object -Last 1"
)

echo Upload completed at %date% %time% >> upload_history.log
echo Shutdown process completed at %time%
timeout /t 2 /nobreak >nul
REM Brief pause then close automatically
REM Only 2 seconds here - shutdown scripts have time limits!