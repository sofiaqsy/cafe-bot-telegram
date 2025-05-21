# Instrucciones Post-Despliegue para Heroku

Después de desplegar el bot en Heroku, es importante asegurarse de que esté correctamente configurado para funcionar. Sigue estas instrucciones para completar la configuración:

## 1. Escalar los Dynos

Por defecto, el dyno worker puede no estar activado. Debes escalarlo para que el bot funcione:

```bash
# Escalar el dyno worker a 1 (activarlo)
heroku ps:scale worker=1 --app nombre-de-tu-app

# Asegurarse de que el dyno web está apagado (si existe)
heroku ps:scale web=0 --app nombre-de-tu-app
```

## 2. Verificar la Configuración de Drive

Ejecuta el comando para verificar que la configuración de Google Drive es correcta:

```bash
# Ver todas las variables de configuración
heroku config --app nombre-de-tu-app | grep DRIVE
```

Asegúrate de que DRIVE_ENABLED esté configurado como "true" y que los IDs de carpetas estén correctamente configurados.

## 3. Verificar Logs

Observa los logs para asegurarte de que el bot está funcionando correctamente:

```bash
heroku logs --tail --app nombre-de-tu-app
```

## 4. Inicializar Carpetas (si es necesario)

Si las carpetas de uploads no se crean automáticamente, puedes ejecutar:

```bash
heroku run bash --app nombre-de-tu-app
$ bash init_dirs.sh
```

## 5. Probar el Bot

Envía el comando `/test_bot` al bot en Telegram para verificar que está funcionando correctamente.

## 6. Diagnosticar Problemas de Drive

Si tienes problemas con la integración de Google Drive, envía el comando `/drive_status` al bot para obtener información sobre la configuración actual.

## Solución de Problemas Comunes

### El bot no responde
- Verifica que los dynos estén correctamente escalados: `heroku ps --app nombre-de-tu-app`
- Revisa los logs en busca de errores: `heroku logs --app nombre-de-tu-app`

### Las imágenes no se suben a Google Drive
- Asegúrate de que DRIVE_ENABLED esté configurado como "true"
- Verifica que las credenciales de Google tengan los permisos correctos
- Comprueba que los IDs de carpetas estén configurados correctamente
- Usa el comando `/drive_status` para diagnosticar problemas