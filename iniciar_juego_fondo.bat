@echo off
chcp 65001 >nul
title Abrir WordGalaxy en modo fondo
cd /d "%~dp0"
set PUERTO=9222
set RUTA=

if exist ruta_juego.txt set /p RUTA=<ruta_juego.txt

rem 1) si el juego ya esta abierto, usar su ruta
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "(Get-Process -Name 'WordGalaxy-Client' -ErrorAction SilentlyContinue | Select-Object -First 1).Path"`) do set RUTA=%%i

rem 2) si no, buscarlo en las carpetas comunes
if defined RUTA if exist "%RUTA%" goto lanzar
echo Buscando WordGalaxy-Client.exe ...
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Get-ChildItem -Path $env:LOCALAPPDATA,$env:ProgramFiles,'C:\Program Files (x86)',$env:USERPROFILE\Desktop,$env:USERPROFILE\Downloads,$env:APPDATA -Filter WordGalaxy-Client.exe -Recurse -Depth 5 -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName"`) do set RUTA=%%i

rem 3) si tampoco, pedirlo
if defined RUTA if exist "%RUTA%" goto lanzar
echo No lo encontre. Arrastra aqui el acceso directo o el WordGalaxy-Client.exe y presiona Enter:
set /p RUTA=Ruta: 
set RUTA=%RUTA:"=%

:lanzar
if not exist "%RUTA%" (
  echo No existe: %RUTA%
  pause
  exit /b
)
(echo %RUTA%)> ruta_juego.txt

echo Cerrando el juego si estaba abierto...
taskkill /f /im WordGalaxy-Client.exe >nul 2>&1
timeout /t 4 >nul

echo Abriendo WordGalaxy con el puerto %PUERTO% ...
start "" "%RUTA%" --remote-debugging-port=%PUERTO% --remote-allow-origins=* --disable-renderer-backgrounding --disable-background-timer-throttling --disable-backgrounding-occluded-windows

echo.
python bot_puertas.py --puerto
echo.
echo Listo. Inicia sesion en el juego si te la pide.
echo Despues abre iniciar_bot_puertas.bat: el bot maximiza las ventanas, pulsa START
echo y espera a que aparezca la nave. Ya puedes usar tu PC normal.
pause
