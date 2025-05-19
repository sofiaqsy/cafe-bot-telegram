# Implementación de la Funcionalidad de Carga de Documentos con Google Drive

## Descripción

Esta rama añade una nueva funcionalidad al Bot de Gestión de Café que permite a los usuarios cargar imágenes como evidencia de pago para las operaciones de compra y venta registradas en el sistema. Las imágenes se pueden almacenar tanto localmente como en Google Drive según la configuración.

## Cambios Realizados

1. Creación del módulo `handlers/documents.py` para manejar la carga y registro de documentos
2. Creación del módulo `utils/drive.py` para la integración con Google Drive
3. Actualización de `config.py` para añadir la configuración de la carpeta de uploads y parámetros de Google Drive
4. Actualización de `utils/sheets/constants.py` para agregar la estructura de la nueva hoja "documentos" con campos para Drive
5. Actualización de `bot.py` para registrar los nuevos handlers
6. Actualización de `handlers/start.py` para incluir el nuevo comando en la ayuda
7. Creación de documentación en `docs/evidencias_pago.md`
8. Creación de la carpeta `uploads` para almacenamiento local de respaldo

## Principales Funcionalidades

### 1. Almacenamiento en Google Drive

- Subida de imágenes directamente a Google Drive
- Organización automática en carpetas por tipo de operación (compra/venta)
- Generación de enlaces para acceso directo a las evidencias
- Sistema de respaldo automático a almacenamiento local en caso de error

### 2. Proceso Guiado de Carga

Los usuarios pueden utilizar el comando `/documento` para iniciar el proceso de carga de evidencias de pago. El proceso guía al usuario para:

1. Seleccionar el tipo de operación (COMPRA o VENTA)
2. Ingresar el ID de la operación asociada
3. Enviar la imagen de la evidencia
4. Confirmar la carga

### 3. Integración con Google Sheets

- Registro completo de evidencias en Google Sheets
- Almacenamiento de enlaces a los archivos en Drive
- Compatibilidad con el modelo de datos existente

## Implementación Técnica

### API de Google Drive

- Utiliza la biblioteca oficial `google-api-python-client`
- Implementa autenticación mediante cuenta de servicio
- Manejo de errores y respaldo automático
- Creación de carpetas y generación de enlaces

### Almacenamiento Configurable

- Configuración mediante variables de entorno:
  - `DRIVE_ENABLED`: Activa/desactiva el uso de Google Drive
  - `DRIVE_EVIDENCIAS_ROOT_ID`, `DRIVE_EVIDENCIAS_COMPRAS_ID`, `DRIVE_EVIDENCIAS_VENTAS_ID`: IDs de carpetas en Drive

## Instrucciones de Despliegue

1. Actualizar variables de entorno:
   ```
   DRIVE_ENABLED=TRUE
   GOOGLE_CREDENTIALS=<credenciales-de-cuenta-de-servicio>
   ```

2. Asegurarse de que la cuenta de servicio tenga permisos adecuados en Google Drive y Google Sheets

3. Opcional: Configurar IDs de carpetas existentes en Drive:
   ```
   DRIVE_EVIDENCIAS_ROOT_ID=<id-carpeta-principal>
   DRIVE_EVIDENCIAS_COMPRAS_ID=<id-carpeta-compras>
   DRIVE_EVIDENCIAS_VENTAS_ID=<id-carpeta-ventas>
   ```

## Ventajas para Entornos de Producción

Esta implementación resulta especialmente útil para despliegues en plataformas como Heroku con sistema de archivos efímero, ya que:

1. Almacena las imágenes de forma persistente en Google Drive
2. Proporciona acceso universal a las evidencias mediante enlaces
3. Mantiene un respaldo local en caso de problemas de conectividad
4. Garantiza la integridad de los datos incluso en reinicios del servidor

## Próximos Pasos

- Implementar una función para visualizar las evidencias asociadas a una operación
- Añadir opciones de seguridad adicionales para acceso a las imágenes
- Mejorar la gestión de errores durante la carga de imágenes
- Añadir soporte para múltiples imágenes por operación