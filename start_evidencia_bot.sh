#!/bin/bash
# Script para ejecutar el bot de evidencias

# Comprobar si Python está instalado
if ! command -v python3 &> /dev/null
then
    echo "Python 3 no está instalado. Por favor, instálalo e intenta de nuevo."
    exit 1
fi

# Comprobar si las dependencias están instaladas
python3 -c "import telegram" &> /dev/null
if [ $? -ne 0 ]; then
    echo "Instalando dependencias necesarias..."
    pip install python-telegram-bot
    if [ $? -ne 0 ]; then
        echo "Error al instalar dependencias. Por favor, instala manualmente: pip install python-telegram-bot"
        exit 1
    fi
fi

# Crear directorio para evidencias si no existe
mkdir -p evidencias_uploads

# Comprobar si existe el archivo de token
if [ ! -f "token_evidencia.txt" ] && [ -z "$TELEGRAM_BOT_EVIDENCIA_TOKEN" ]; then
    echo "No se encontró el token del bot."
    echo "Por favor, crea un archivo 'token_evidencia.txt' con el token del bot"
    echo "o establece la variable de entorno TELEGRAM_BOT_EVIDENCIA_TOKEN."
    exit 1
fi

# Ejecutar el bot
echo "Iniciando bot de evidencias..."
python3 evidencia_bot.py

# Si el bot se detiene, mostrar mensaje
echo "Bot detenido. Para reiniciarlo, ejecuta este script nuevamente."