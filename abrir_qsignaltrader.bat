@echo off
title QSignalTrader

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [ERRO] Ambiente virtual nao encontrado em .venv\
    echo Execute: python -m venv .venv
    echo Em seguida: pip install -r requirements.txt
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo ============================================
echo         QSignalTrader - Iniciando...
echo ============================================
echo.
echo  Servidor: http://127.0.0.1:8080
echo  Pressione Ctrl+C para parar
echo.

timeout /t 3 /nobreak >nul
start http://127.0.0.1:8080

.venv\Scripts\python.exe -m uvicorn web.app:app --host 127.0.0.1 --port 8080

pause
