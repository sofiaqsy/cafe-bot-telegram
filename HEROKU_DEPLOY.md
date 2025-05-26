# Instrucciones para desplegar en Heroku

## Requisitos previos
1. Una cuenta en [Heroku](https://www.heroku.com/)
2. [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli) instalado
3. Credenciales de Google Cloud con acceso a Google Drive y Google Sheets
4. Una cuenta en [Telegram](https://telegram.org/) y un token de bot de Telegram

## Pasos para desplegar el bot

### 1. Preparar el archivo de credenciales de Google

Descarga el archivo JSON de credenciales de servicio desde Google Cloud Console:
1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Selecciona tu proyecto
3. Ve a "APIs y servicios" > "Credenciales"
4. Crea o descarga una clave de cuenta de servicio existente
5. Guarda el archivo JSON

### 2. Crear una aplicación en Heroku

```bash
# Iniciar sesión en Heroku
heroku login

# Crear una nueva aplicación en Heroku
heroku create cafe-bot-telegram

# O si quieres un nombre específico
heroku create nombre-de-tu-app
```

### 3. Configurar variables de entorno en Heroku

Configura las variables de entorno necesarias para el bot:

```bash
# Token del bot de Telegram (obtenido de BotFather)
heroku config:set TELEGRAM_BOT_TOKEN="tu_token_del_bot"

# ID de la hoja de Google Sheets
heroku config:set SPREADSHEET_ID="id_de_tu_hoja_de_google_sheets"

# Habilitar Google Drive
heroku config:set DRIVE_ENABLED=true

# Credenciales de Google (contenido del archivo JSON)
heroku config:set GOOGLE_CREDENTIALS='$(cat ruta/al/archivo-de-credenciales.json)'
```

### 4. Preparar las hojas de Google Sheets

El bot utiliza múltiples hojas dentro del documento de Google Sheets para almacenar diferentes tipos de datos. Asegúrate de que existan estas hojas:

- **Compras**: Registro de compras de café
- **Ventas**: Registro de ventas
- **Proceso**: Registro de procesamiento de café
- **Gastos**: Registro de gastos operativos
- **Adelantos**: Registro de adelantos a proveedores
- **Pedidos**: Registro de pedidos de clientes
- **Almacen**: Control de inventario
- **capitalizacion**: Registro de ingresos de capital (sin tilde y en minúsculas)

Si alguna de estas hojas no existe, el bot intentará crearla automáticamente la primera vez que se use la funcionalidad correspondiente.

### 5. Desplegar en Heroku

```bash
# Agregar el repositorio de Heroku como remoto
git remote add heroku https://git.heroku.com/nombre-de-tu-app.git

# Desplegar en Heroku
git push heroku main
```

Alternativamente, puedes configurar GitHub para despliegue automático:
1. Ve al panel de control de tu aplicación en Heroku
2. Ve a la pestaña "Deploy"
3. Conecta con GitHub y selecciona el repositorio
4. Habilita el despliegue automático desde la rama main

### 6. Verificar la configuración de Google Drive

Después de desplegar, ejecuta el script de verificación:

```bash
bash heroku_check_drive.sh
```

Este script verificará si todas las variables de entorno necesarias están configuradas correctamente.

### 7. Verificar que el bot está funcionando

Para verificar que el bot está funcionando correctamente:

```bash
# Ver los logs de la aplicación en Heroku
heroku logs --tail
```

También puedes enviar el comando `/test_bot` o `/drive_status` a tu bot en Telegram para verificar su estado.

## Solución de problemas

### El bot no responde
1. Verifica los logs de Heroku con `heroku logs --tail`
2. Asegúrate de que el token del bot sea válido
3. Verifica que los dyno estén activos con `heroku ps`

### Problemas con Google Drive
1. Verifica que DRIVE_ENABLED esté configurado como true
2. Verifica que GOOGLE_CREDENTIALS contenga las credenciales correctas
3. Asegúrate de que la cuenta de servicio tenga permisos de Drive
4. Usa el comando `/drive_status` en el bot para diagnósticos

### Otros problemas
- Reinicia los dynos con `heroku restart`
- Verifica la configuración con `heroku config`
- Consulta los logs de la aplicación con `heroku logs --tail`

## Mantenimiento

### Actualizar el bot
```bash
git push heroku main
```

### Escalar la aplicación
```bash
# Un solo dyno para mantener bajo el costo
heroku ps:scale web=1

# Para aplicaciones con más tráfico
heroku ps:scale web=2
```

### Copia de seguridad de datos
Heroku no proporciona almacenamiento persistente para archivos locales. Las evidencias se guardan en Google Drive cuando DRIVE_ENABLED=true, pero es recomendable verificar periódicamente que la integración funcione correctamente.