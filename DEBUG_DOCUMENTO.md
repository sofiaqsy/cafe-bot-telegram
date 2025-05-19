# Depuración del Comando /documento

Esta rama agrega logs detallados y herramientas de diagnóstico para resolver el problema con el comando `/documento` que no está respondiendo correctamente.

## Cambios Realizados

1. **Logs Detallados**: Se ha mejorado significativamente el sistema de logs en:
   - `handlers/documents.py`: Logs detallados en cada etapa del proceso
   - `bot.py`: Logs sobre la importación y registro de los handlers

2. **Herramientas de Diagnóstico**:
   - Nuevo comando `/diagnostico`: Muestra información del sistema y estado del bot
   - Comando `/documento_test`: Verifica si el handler está registrado correctamente
   - Comando `/test_bot`: Verifica si el bot responde a comandos básicos

3. **Manejo de Errores**:
   - Captura y registro detallado de excepciones en cada etapa
   - Notificación al usuario cuando ocurre un error
   - Recuperación automática cuando es posible

4. **Verificaciones de Sistema**:
   - Verificación de permisos en directorio de uploads
   - Impresión de variables de entorno relevantes (sin valores sensibles)
   - Validación de que todas las dependencias estén disponibles

## Comandos para Depuración

1. `/test_bot` - Prueba simple para verificar que el bot responde
2. `/diagnostico` - Muestra información detallada sobre el estado del bot
3. `/documento_test` - Verifica específicamente si el handler de documentos está disponible

## Cómo Usar la Depuración

1. Actualiza el bot con estos cambios
2. Reinicia el servicio del bot
3. Verifica los logs del servidor después del inicio
4. Prueba los comandos de diagnóstico en este orden:
   - `/test_bot` para confirmar que el bot está respondiendo
   - `/diagnostico` para verificar la configuración del sistema
   - `/documento_test` para verificar el handler de documentos
   - `/documento` para intentar usar la funcionalidad

5. Si alguno de estos comandos falla, revisa los logs detallados para identificar el problema específico

## Posibles Problemas y Soluciones

1. **Permisos de Carpeta**: Si los logs muestran errores de permisos en la carpeta `uploads`:
   ```bash
   chmod -R 755 /ruta/a/cafe-bot-telegram/uploads
   ```

2. **Falta de Dependencias**: Si los logs muestran errores de importación:
   ```bash
   pip install -r requirements.txt
   ```

3. **Error en Google Drive**: Si los logs muestran errores relacionados con Google Drive:
   - Verifica las credenciales
   - Desactiva temporalmente Drive con `DRIVE_ENABLED=FALSE`

4. **Problema de Registro de Handler**: Si no se registra el handler de documentos:
   - Verifica que no haya errores de sintaxis en `documents.py`
   - Confirma que `register_documents_handlers` está correctamente definido