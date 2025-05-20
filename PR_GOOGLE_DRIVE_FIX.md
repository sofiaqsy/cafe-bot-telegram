# Corrección del almacenamiento en Google Drive

## Problema
Las imágenes no se están guardando correctamente en Google Drive cuando se utilizan como evidencias en el comando `/EVIDENCIA`.

## Causa
El problema se debe a que no existe una guía clara de configuración de Google Drive y no hay herramientas para verificar que la configuración sea correcta:

1. Faltan variables de entorno necesarias en el archivo `.env.example`
2. No existe un script para verificar la configuración de Google Drive
3. No hay documentación sobre cómo configurar correctamente Google Drive

## Solución
Se implementaron las siguientes mejoras:

1. **Script de verificación**: Se creó `check_drive.py` que verifica que todas las credenciales y configuraciones estén correctas.
2. **Documentación detallada**: Se creó una guía paso a paso en `docs/GOOGLE_DRIVE_SETUP.md` que explica cómo configurar Google Drive.
3. **Ejemplo completo**: Se actualizó `.env.example` para incluir todas las variables necesarias para Google Drive.

## Cómo verificar la configuración
Para verificar que Google Drive esté configurado correctamente:

1. Ejecuta el script `python check_drive.py`
2. Sigue las instrucciones que muestra el script
3. Asegúrate de que todas las variables de entorno estén configuradas correctamente
4. Prueba el comando `/EVIDENCIA` para subir una imagen

## Impacto
- Facilita la configuración de Google Drive para los desarrolladores
- Proporciona herramientas de diagnóstico para identificar problemas
- Mejora la documentación para una implementación correcta
- Asegura que las evidencias se guarden correctamente en Google Drive

## Archivos afectados
- `check_drive.py` (nuevo)
- `docs/GOOGLE_DRIVE_SETUP.md` (nuevo)
- `.env.example` (actualizado)
