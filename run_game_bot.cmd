@echo off
setlocal

cd /d "D:\New_world\auto_bot"

if not exist "logs" mkdir "logs"
echo [%date% %time%] scheduled run start >> "logs\scheduled_run.log"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

"C:\WINDOWS\py.exe" -3 -X utf8 "D:\New_world\auto_bot\game_bot.py" >> "logs\scheduled_run.log" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"

echo [%date% %time%] scheduled run end >> "logs\scheduled_run.log"

endlocal & exit /b %EXIT_CODE%
