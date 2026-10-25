@echo off
chcp 65001 >nul
title Bot Puertas Galacticas - WordGalaxy
cd /d "%~dp0"

:menu
cls
echo ==========================================
echo    BOT PUERTAS GALACTICAS - WORDGALAXY
echo ==========================================
echo  1) ALPHA     6) LAMBDA
echo  2) BETA      7) KRONOS
echo  3) GAMMA     8) ZETA
echo  4) DELTA     9) HADES
echo  5) KAPPA
echo.
echo  I) Instalar dependencias
echo  C) Ver coordenadas del mouse
echo  D) Diagnostico de ventanas
echo  G) Abrir el juego en modo fondo
echo  N) Modo normal (usa tu mouse, ventanas a la vista)
echo  F) Modo fondo (sin usar tu mouse)
echo  S) Salir
echo ==========================================
set /p op="Elige la puerta: "

if /i "%op%"=="1" set G=ALPHA& goto run
if /i "%op%"=="2" set G=BETA& goto run
if /i "%op%"=="3" set G=GAMMA& goto run
if /i "%op%"=="4" set G=DELTA& goto run
if /i "%op%"=="5" set G=KAPPA& goto run
if /i "%op%"=="6" set G=LAMBDA& goto run
if /i "%op%"=="7" set G=KRONOS& goto run
if /i "%op%"=="8" set G=ZETA& goto run
if /i "%op%"=="9" set G=HADES& goto run
if /i "%op%"=="I" goto instalar
if /i "%op%"=="C" python bot_puertas.py --coords & goto menu
if /i "%op%"=="D" python bot_puertas.py --diag & pause & goto menu
if /i "%op%"=="G" call iniciar_juego_fondo.bat & goto menu
if /i "%op%"=="N" python bot_puertas.py --modo normal & pause & goto menu
if /i "%op%"=="F" python bot_puertas.py --modo fondo & pause & goto menu
if /i "%op%"=="S" exit /b
goto menu

:instalar
python -m pip install pyautogui mss opencv-python numpy keyboard pytesseract pygetwindow websocket-client
echo.
echo Instala tambien Tesseract-OCR: https://github.com/UB-Mannheim/tesseract/wiki
pause
goto menu

:run
python bot_puertas.py %G%
pause
goto menu
