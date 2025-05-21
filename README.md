# Bot de Telegram para Gestión de Café

Bot de Telegram para la gestión completa de un negocio de café, desde la compra hasta la venta.

## Características

- **Gestión de Compras**: Registra y organiza compras de café.
- **Procesamiento**: Seguimiento del procesamiento de café.
- **Ventas**: Registro y gestión de ventas.
- **Gestión de Costos**: Registro de gastos asociados a la operación.
- **Evidencias**: Subida de evidencias fotográficas de compras y ventas, con integración a Google Drive.
- **Pedidos**: Gestión de pedidos y estado de entrega.
- **Reportes**: Generación de reportes de operación.
- **Adelantos**: Manejo de adelantos de pago.
- **Control de Almacén**: Seguimiento de inventario.

## Configuración

### Requisitos

- Python 3.9 o superior
- Una cuenta de Telegram
- Token de bot de Telegram (obtenido a través de [BotFather](https://t.me/botfather))
- Cuenta de Google y credenciales para Google Sheets y Google Drive

### Variables de Entorno

Crea un archivo `.env` en el directorio raíz con las siguientes variables:

```
TELEGRAM_BOT_TOKEN=tu_token_de_bot
SPREADSHEET_ID=id_de_tu_hoja_de_google_sheets
GOOGLE_CREDENTIALS=contenido_del_json_de_credenciales_o_ruta_al_archivo
DRIVE_ENABLED=true
```

### Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/sofiaqsy/cafe-bot-telegram.git
   cd cafe-bot-telegram
   ```

2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Ejecuta el bot:
   ```bash
   python bot.py
   ```

## Despliegue en Heroku

Este proyecto incluye la configuración necesaria para desplegarlo en Heroku. Para obtener instrucciones detalladas, consulta [HEROKU_DEPLOY.md](HEROKU_DEPLOY.md).

## Comandos del Bot

- `/start` - Inicia el bot y muestra información básica
- `/help` o `/ayuda` - Muestra la lista de comandos disponibles
- `/compra` - Registra una nueva compra de café
- `/venta` - Registra una nueva venta
- `/proceso` - Registra procesamiento de café
- `/gastos` - Registra gastos operativos
- `/evidencia` - Sube evidencias fotográficas de compras o ventas
- `/pedido` - Gestiona pedidos
- `/reporte` - Genera reportes de operación
- `/almacen` - Gestiona inventario
- `/adelanto` - Registra adelantos de pago
- `/drive_status` - Verifica el estado de la integración con Google Drive
- `/test_bot` - Comprueba que el bot está funcionando correctamente

## Estructura del Proyecto

- `bot.py` - Punto de entrada principal del bot
- `config.py` - Configuración del bot
- `handlers/` - Manejadores de comandos del bot
  - `start.py` - Manejador de los comandos `/start` y `/help`
  - `compras.py` - Manejador del comando `/compra`
  - `ventas.py` - Manejador del comando `/venta`
  - `evidencias.py` - Manejador del comando `/evidencia`
  - (y otros manejadores de comandos)
- `utils/` - Funciones de utilidad
  - `sheets.py` - Funciones para interactuar con Google Sheets
  - `drive.py` - Funciones para interactuar con Google Drive
  - `helpers.py` - Funciones auxiliares generales
- `uploads/` - Directorio para almacenar archivos subidos (no incluido en el repositorio)

## Diagnóstico y Solución de Problemas

Si encuentras problemas con la integración de Google Drive, puedes usar el comando `/drive_status` para obtener información sobre la configuración actual. También puedes verificar los logs para obtener más detalles sobre posibles errores.

## Licencia

Este proyecto está licenciado bajo la licencia MIT. Ver el archivo LICENSE para más detalles.

## Contribuciones

Las contribuciones son bienvenidas. Por favor, sigue estos pasos:

1. Haz un fork del repositorio
2. Crea una rama para tu característica (`git checkout -b feature/amazing-feature`)
3. Haz commit de tus cambios (`git commit -m 'Add some amazing feature'`)
4. Empuja tu rama (`git push origin feature/amazing-feature`)
5. Abre un Pull Request