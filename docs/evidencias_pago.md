# Documentación: Carga de Evidencias de Pago

Esta funcionalidad permite a los usuarios cargar imágenes como evidencia de pago para operaciones de compra y venta registradas en el sistema. Las imágenes pueden almacenarse localmente o en Google Drive, según la configuración del sistema.

## Comandos Disponibles

- `/documento` - Iniciar el proceso de carga de evidencia de pago

## Proceso de Carga de Evidencias

1. Ejecuta el comando `/documento`
2. Selecciona el tipo de operación (COMPRA o VENTA)
3. Ingresa el ID de la operación (obtenido al registrar la compra o venta)
4. Envía la imagen de la evidencia de pago
5. Confirma la operación

## Almacenamiento de Imágenes

El sistema ofrece dos opciones para el almacenamiento de las evidencias de pago:

### 1. Almacenamiento en Google Drive

Cuando la variable de entorno `DRIVE_ENABLED` está configurada como `TRUE`, las imágenes se suben automáticamente a Google Drive, lo que ofrece las siguientes ventajas:

- Persistencia de archivos incluso en entornos como Heroku con sistema de archivos efímero
- Acceso a los archivos desde cualquier dispositivo mediante el enlace proporcionado
- Organización automática de las evidencias en carpetas específicas para compras y ventas
- Respaldo seguro en la nube

Para configurar el almacenamiento en Google Drive:

1. Configura las siguientes variables de entorno:
   - `DRIVE_ENABLED=TRUE`
   - `GOOGLE_CREDENTIALS=<credenciales-de-cuenta-de-servicio>`

2. Opcionalmente, puedes configurar las carpetas específicas:
   - `DRIVE_EVIDENCIAS_ROOT_ID=<id-carpeta-principal>`
   - `DRIVE_EVIDENCIAS_COMPRAS_ID=<id-carpeta-compras>`
   - `DRIVE_EVIDENCIAS_VENTAS_ID=<id-carpeta-ventas>`

Si no se configuran las carpetas, el sistema creará automáticamente la estructura necesaria en Google Drive.

### 2. Almacenamiento Local

Cuando `DRIVE_ENABLED` está configurado como `FALSE` o no está configurado, las imágenes se almacenan localmente en la carpeta `/uploads` del servidor.

Estructura de almacenamiento local:
- Directorio: `/uploads`
- Nombres de archivo: `tipo_operacion_id_operacion_uuid.jpg`

## Información Guardada en Google Sheets

La información de las evidencias se guarda en la hoja "documentos" de Google Sheets con la siguiente estructura:

- **id**: Identificador único de la evidencia
- **fecha**: Fecha y hora del registro
- **tipo_operacion**: COMPRA o VENTA
- **operacion_id**: ID de la operación asociada
- **archivo_id**: ID del archivo en Telegram
- **ruta_archivo**: Nombre del archivo guardado o referencia a Drive
- **drive_file_id**: ID del archivo en Google Drive (si aplica)
- **drive_view_link**: Enlace para ver el archivo en Drive (si aplica)
- **registrado_por**: Usuario que registró la evidencia
- **notas**: Notas adicionales (opcional)

## Consideraciones Técnicas

### Implementación de Google Drive

La integración con Google Drive utiliza la API oficial de Google Drive a través de las siguientes características:

- Autenticación mediante cuenta de servicio de Google
- Creación automática de estructura de carpetas
- Subida de archivos usando la API de Google Drive v3
- Generación de enlaces de visualización para acceso fácil

### Fallback a Almacenamiento Local

En caso de error al subir a Google Drive, el sistema automáticamente utiliza el almacenamiento local como respaldo para garantizar que no se pierdan evidencias.

## Recomendaciones para los Usuarios

- Las imágenes deben ser claras y legibles
- Se recomienda tomar la foto con buena iluminación
- Asegúrate de tener el ID de la operación antes de iniciar el proceso
- La imagen debe mostrar claramente la información relevante del pago
- Si utilizas Google Drive, guarda el enlace proporcionado para acceso futuro

## Solución de Problemas

- Si la carga falla, revisa la conexión a internet e intenta nuevamente
- Si no recuerdas el ID de la operación, puedes consultarlo en los mensajes anteriores o en Google Sheets
- Si la imagen no es clara, se recomienda tomar una nueva foto y reiniciar el proceso
- Si el enlace de Google Drive no funciona, verifica que la cuenta de servicio tenga permisos adecuados

## Configuración Avanzada

Para configurar las credenciales de Google Drive:

1. Crea una cuenta de servicio en Google Cloud Console
2. Habilita las APIs de Google Drive y Google Sheets
3. Crea una clave para la cuenta de servicio y descarga el archivo JSON
4. Configura la variable de entorno `GOOGLE_CREDENTIALS` con el contenido del archivo JSON
5. Comparte la carpeta de destino en Google Drive con la dirección de correo de la cuenta de servicio