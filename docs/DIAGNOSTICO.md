# 🔍 Guía de Diagnóstico para el Bot de Café

Este documento proporciona instrucciones para diagnosticar y solucionar problemas con el comando `/documento` en el bot de Telegram para gestión de café.

## 📋 Archivos de diagnóstico

Los siguientes archivos de log se generan automáticamente:

- `bot_debug.log` - Log principal del bot con información detallada de inicialización
- `documento_debug.log` - Log específico del módulo de documentos

Estos archivos contienen información valiosa para identificar la causa de los problemas.

## 🛠️ Comandos de diagnóstico

Se han añadido comandos de diagnóstico al bot:

- `/test_bot` - Verifica si el bot está funcionando correctamente
- `/test_documento` - Verifica específicamente el estado del handler de documentos

## 🔍 Diagnóstico del problema con `/documento`

Sigue estos pasos para diagnosticar el problema:

1. **Verificar la versión de python-telegram-bot**:
   - Debe ser v20.0 o superior
   - Los logs iniciales en `bot_debug.log` mostrarán la versión actual

2. **Verificar la importación del módulo documents**:
   - Buscar en `bot_debug.log` mensajes relacionados con la importación de `handlers.documents`
   - Verificar que `register_documents_handlers` se ha importado correctamente

3. **Verificar el registro del handler**:
   - Buscar en `bot_debug.log` mensajes relacionados con "Registrando handler completo documents"
   - Si falló, buscar los intentos alternativos de registro

4. **Verificar la estructura de directorios**:
   - Asegurarse de que el directorio `UPLOADS_FOLDER` existe y tiene permisos adecuados
   - Los logs en `documento_debug.log` mostrarán información sobre este directorio

5. **Verificar la ejecución del comando**:
   - Cuando se ejecuta `/documento`, buscar en `documento_debug.log` mensajes de "COMANDO /documento INICIADO"
   - Seguir la ejecución a través de los diferentes estados

## 🔧 Solución de problemas comunes

1. **El comando no responde en absoluto**:
   - Verificar si el handler está registrado correctamente
   - Comprobar si hay errores en la fase de registro
   - Usar `/test_documento` para ver el estado actual

2. **El comando inicia pero falla en algún estado**:
   - Buscar errores específicos en `documento_debug.log`
   - Identificar en qué estado de la conversación falla

3. **Errores relacionados con directorios**:
   - Verificar permisos y existencia del directorio `UPLOADS_FOLDER`
   - Comprobar permisos de escritura

4. **Errores relacionados con Google Drive** (si está habilitado):
   - Verificar credenciales y configuración de carpetas en Drive
   - Comprobar logs relacionados con la subida a Drive

## 📊 Estructura del módulo de documentos

El sistema utiliza un `ConversationHandler` con los siguientes estados:

1. `SELECCIONAR_TIPO` - Selección de tipo de operación (COMPRA/VENTA)
2. `SELECCIONAR_ID` - Ingreso del ID de operación
3. `SUBIR_DOCUMENTO` - Subida de la evidencia fotográfica
4. `CONFIRMAR` - Confirmación del registro

Los errores pueden ocurrir en cualquiera de estos estados.

## 📱 Feedback adicional

El sistema ahora detecta palabras clave relacionadas con "documento" o "evidencia" en los mensajes y sugiere usar el comando `/test_documento` para verificar el estado del sistema.

## 🧪 Validación de componentes

Se ha añadido una función `validate_handler()` en `documents.py` que verifica automáticamente que todos los componentes necesarios estén disponibles antes de intentar registrar el handler.