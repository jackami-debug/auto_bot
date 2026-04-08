@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

cd /d "D:\New_world\auto_bot"

if not exist "logs" mkdir "logs"
set "LOG_FILE=logs\daily_mission_scheduled_run.log"
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH:mm:ss"') do set "TS=%%I"
echo [!TS!] daily mission scheduled run start >> "!LOG_FILE!"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

"C:\WINDOWS\py.exe" -3 -X utf8 "D:\New_world\auto_bot\game_bot_daily_mission.py" >> "!LOG_FILE!" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH:mm:ss"') do set "TS=%%I"
echo [!TS!] daily mission scheduled run end (exit=!EXIT_CODE!) >> "!LOG_FILE!"

endlocal & exit /b %EXIT_CODE%