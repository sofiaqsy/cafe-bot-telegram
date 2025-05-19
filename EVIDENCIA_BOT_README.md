# 🚨 Bot Independiente para Registro de Evidencias 📸

## Descripción

Este repositorio contiene una solución independiente para el registro de evidencias de pago, diseñada para operar en paralelo con el bot principal de gestión de café.

## Problema resuelto

Tras múltiples intentos de solucionar los problemas con el comando `/documento` en el bot principal, hemos desarrollado este bot independiente para garantizar que los usuarios puedan seguir registrando sus evidencias de pago sin interrupciones.

## 🛠️ Configuración rápida (5 minutos)

### 1. Crear un nuevo bot en BotFather

1. Abrir Telegram y buscar [@BotFather](https://t.me/botfather)
2. Enviar el comando `/newbot`
3. Seguir las instrucciones para crear un nuevo bot (por ejemplo, "CafeEvidenciasBot")
4. Guardar el token que te proporciona BotFather

### 2. Configurar el bot

Existen dos formas de configurar el token del bot:

#### Opción A: Archivo de configuración

Crear un archivo llamado `token_evidencia.txt` en el mismo directorio que `evidencia_bot.py` con el token del bot:

```
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

#### Opción B: Variable de entorno

Establecer la variable de entorno `TELEGRAM_BOT_EVIDENCIA_TOKEN` con el token del bot:

```bash
# Linux/Mac
export TELEGRAM_BOT_EVIDENCIA_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Windows (PowerShell)
$env:TELEGRAM_BOT_EVIDENCIA_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"

# Windows (CMD)
set TELEGRAM_BOT_EVIDENCIA_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

### 3. Instalar dependencias

```bash
pip install python-telegram-bot
```

### 4. Ejecutar el bot

```bash
python evidencia_bot.py
```

## 🤖 Uso del bot

### Comandos disponibles

- `/start` - Inicia el bot
- `/ayuda` - Muestra el mensaje de ayuda
- `/evidencia` - Inicia el proceso de registro de evidencia

### Flujo de registro

1. El usuario envía el comando `/evidencia`
2. Selecciona el tipo de operación (COMPRA o VENTA)
3. Ingresa el ID de la operación
4. Envía la foto de la evidencia de pago
5. Confirma el registro

## 📁 Estructura de datos

Las evidencias se guardan en el directorio `evidencias_uploads/` con la siguiente estructura:

- Imágenes: `evidencias_uploads/E-YYYYMMDD-XXXXXX.jpg`
- Registro CSV: `evidencias_uploads/evidencias.csv`

El archivo CSV contiene los siguientes campos:
- fecha
- evidencia_id
- tipo
- operacion_id
- usuario_id
- usuario_nombre
- foto_id
- ruta_archivo

## 🔄 Integración con el sistema principal

Este bot funciona de forma independiente, pero los administradores pueden integrar manualmente los datos:

1. Revisar periódicamente el archivo `evidencias.csv`
2. Procesar las nuevas evidencias
3. Marcarlas como procesadas

## 📋 Instrucciones para usuarios

1. Busca el bot en Telegram (nombre_del_bot)
2. Inicia una conversación con el bot
3. Usa el comando `/evidencia` para registrar una nueva evidencia
4. Sigue las instrucciones del bot
5. Cuando termines, recibirás un ID de confirmación

## 🚀 Próximos pasos

1. Configurar el bot en un servidor para que esté disponible 24/7
2. Mejorar la integración con el sistema principal
3. Implementar notificaciones automáticas para los administradores

## 📝 Notas para desarrolladores

- El código está diseñado para ser lo más simple y robusto posible
- Se utilizan variables de entorno para configuración segura
- Los errores se registran en el archivo `evidencia_bot.log`

## ⚠️ Importante

Este es un sistema temporal mientras se resuelven los problemas con el bot principal. Los administradores deben revisar regularmente las evidencias registradas para procesarlas.