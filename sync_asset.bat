@echo off
echo === SYNC ASSETS ===
cd /d "C:\Users\andre\OneDrive\Desktop\zero_to_system_v2"
echo Cartella: %cd%

echo.
echo Aggiungo assets...
git add assets\music_input\ assets\stories\

echo.
echo Controllo cambiamenti...
git diff --cached --quiet
if %errorlevel% == 0 (
    echo Nessun cambiamento da sincronizzare.
    goto fine
)

echo.
echo Pull da GitHub...
git pull origin main --no-edit

echo.
echo Commit...
git commit -m "Auto-sync assets %date% %time%"

echo.
echo Push su GitHub...
git push origin main

:fine
echo === FINE ===
pause