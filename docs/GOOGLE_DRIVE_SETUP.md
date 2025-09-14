# Configuración de Google Drive para Almacenamiento de Evidencias

Este documento explica cómo configurar correctamente Google Drive para almacenar las evidencias de compras y ventas.

## Requisitos Previos

1. Una cuenta de Google
2. Acceso a [Google Cloud Console](https://console.cloud.google.com/)

## Pasos para Configurar Google Drive

### 1. Crear un Proyecto en Google Cloud

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Haz clic en "Seleccionar un proyecto" en la parte superior
3. Haz clic en "Nuevo proyecto"
4. Asigna un nombre al proyecto (por ejemplo, "CafeBot")
5. Haz clic en "Crear"

### 2. Habilitar la API de Google Drive

1. En el menú lateral, ve a "APIs y servicios" > "Biblioteca"
2. Busca "Google Drive API"
3. Selecciona la API y haz clic en "Habilitar"

### 3. Crear Credenciales

1. En el menú lateral, ve a "APIs y servicios" > "Credenciales"
2. Haz clic en "Crear credenciales" > "Cuenta de servicio"
3. Asigna un nombre a la cuenta de servicio (por ejemplo, "cafebot-service")
4. Haz clic en "Crear y continuar"
5. En el rol, selecciona "Proyecto" > "Editor" (o un rol con permisos de escritura en Drive)
6. Haz clic en "Continuar" y luego en "Listo"

### 4. Generar Clave JSON

1. En la lista de cuentas de servicio, haz clic en la que acabas de crear
2. Ve a la pestaña "Claves"
3. Haz clic en "Agregar clave" > "Crear nueva clave"
4. Selecciona "JSON" y haz clic en "Crear"
5. Se descargará un archivo JSON con las credenciales

### 5. Configurar Variables de Entorno

1. Abre el archivo JSON descargado con un editor de texto
2. Copia todo el contenido del archivo
3. Abre el archivo `.env` de tu proyecto
4. Añade la siguiente línea, reemplazando `[CONTENIDO_JSON]` con el contenido que copiaste:

```
GOOGLE_CREDENTIALS='[CONTENIDO_JSON]'
```

5. Habilita Google Drive añadiendo esta línea:

```
DRIVE_ENABLED=True
```

### 6. Verificar y Configurar Carpetas

1. Ejecuta el script de verificación para comprobar que todo está configurado correctamente:

```
python check_drive.py
```

2. Si todo está bien, el script te mostrará los IDs de las carpetas creadas.
3. Añade esos IDs a tu archivo `.env`:

```
DRIVE_EVIDENCIAS_ROOT_ID=id_carpeta_principal
DRIVE_EVIDENCIAS_COMPRAS_ID=id_carpeta_compras
DRIVE_EVIDENCIAS_VENTAS_ID=id_carpeta_ventas
```

## Verificación Final

1. Reinicia el bot
2. Ejecuta el comando `/evidencia`
3. Selecciona una compra o venta
4. Sube una imagen
5. Verifica que en el mensaje de confirmación aparezca el enlace de Google Drive

## Solución de Problemas

- **No aparece el enlace de Drive**: Verifica que `DRIVE_ENABLED` esté configurado como `True`
- **Error al subir archivos**: Verifica que las credenciales tengan los permisos correctos
- **Carpetas no creadas**: Sigue las instrucciones de `check_drive.py` para configurar las carpetas manualmente

## Nota Importante

Las credenciales de Google Cloud son sensibles. Nunca las compartas ni las subas a repositorios públicos.
