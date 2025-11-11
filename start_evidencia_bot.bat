@echo off
REM Script para ejecutar el bot de evidencias en Windows

REM Comprobar si Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python no está instalado. Por favor, instálalo e intenta de nuevo.
    pause
    exit /b 1
)

REM Comprobar si las dependencias están instaladas
python -c "import telegram" >nul 2>&1
if %errorlevel% neq 0 (
    echo Instalando dependencias necesarias...
    pip install python-telegram-bot
    if %errorlevel% neq 0 (
        echo Error al instalar dependencias. Por favor, instala manualmente: pip install python-telegram-bot
        pause
        exit /b 1
    )
)

REM Crear directorio para evidencias si no existe
if not exist "evidencias_uploads\" mkdir evidencias_uploads

REM Comprobar si existe el archivo de token
if not exist "token_evidencia.txt" (
    echo No se encontró el archivo token_evidencia.txt.
    echo Por favor, crea un archivo 'token_evidencia.txt' con el token del bot
    echo o establece la variable de entorno TELEGRAM_BOT_EVIDENCIA_TOKEN.
    pause
    exit /b 1
)

REM Ejecutar el bot
echo Iniciando bot de evidencias...
python evidencia_bot.py

REM Si el bot se detiene, mostrar mensaje
echo Bot detenido. Para reiniciarlo, ejecuta este script nuevamente.
pause