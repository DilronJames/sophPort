@echo off
title Dilpreet's Portfolio
cd /d "%~dp0"

echo.
echo  ============================================
echo   Starting the portfolio...
echo   It will open in your browser in a moment.
echo.
echo   To stop the server: press Ctrl+C here
echo   or just close this window.
echo  ============================================
echo.

REM Open the browser ~3 seconds after Flask boots
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:5000"

python app.py

echo.
echo Server stopped.
pause
