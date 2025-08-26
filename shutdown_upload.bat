@echo off
echo ================================================
echo Screenshot Upload - SHUTDOWN MODE  
echo Time: %date% %time%
echo ================================================

cd /d "C:\Users\USUARIO\OneDrive\Documentos\My_Projects\Projects\Automation_Screen_Captures"
python fixed_uploader.py --mode shutdown --silent

echo.
echo ================================================
echo Shutdown upload process completed
echo ================================================

REM Brief pause then close automatically
timeout /t 2 /nobreak >nul
