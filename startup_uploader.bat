@echo off
echo ================================================
echo Screenshot Upload - STARTUP MODE
echo Time: %date% %time%
echo ================================================

cd /d "C:\Users\USUARIO\OneDrive\Documentos\My_Projects\Projects\Automation_Screen_Captures"
python fixed_uploader.py --mode startup --silent

echo.
echo ================================================
echo Startup upload process completed
echo ================================================

REM Keep window open for 3 seconds to see results
timeout /t 3 /nobreak >nul
