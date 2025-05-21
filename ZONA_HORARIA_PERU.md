# Estandarización de la Zona Horaria de Perú en Todo el Bot

## Descripción del Problema
Se ha detectado que varias funcionalidades del bot, incluyendo el comando `/adelanto`, no están usando consistentemente la zona horaria de Perú al registrar fechas y horas, lo que causa inconsistencias en los registros.

Este problema se manifiesta en:
1. Fechas y horas incorrectas en los registros de adelantos
2. Posibles errores en el proveedor debido al formato incorrecto
3. Inconsistencia en los formatos de fecha a lo largo de diferentes funcionalidades

## Cambios Realizados

### 1. En `/handlers/adelantos.py`
- Eliminada la función local `get_now()` que usaba `datetime.now()` sin especificar zona horaria
- Modificada la función `confirmar_step()` para usar `get_now_peru()` y `format_date_for_sheets()`
- Actualizado el import para incluir `format_date_for_sheets`

### 2. En `/handlers/ventas.py`
- Reemplazado `datetime.datetime.now()` con `get_now_peru()`
- Aplicado `format_date_for_sheets()` a la fecha para evitar conversiones automáticas en Google Sheets
- Actualizado el import para incluir `get_now_peru` y `format_date_for_sheets`

## Beneficios
1. **Consistencia**: Todos los registros de fecha y hora en la base de datos ahora usan la misma zona horaria (Perú)
2. **Precisión**: Las fechas y horas registradas corresponden a la hora local de Perú
3. **Formato estandarizado**: Se evitan conversiones automáticas incorrectas en Google Sheets
4. **Mantenibilidad**: Se usa la función centralizada `get_now_peru()` en vez de múltiples implementaciones locales

## Verificación
- Se ha probado el comando `/adelanto` y verifica que los datos de fecha, hora y proveedor se registren correctamente
- Se ha probado el comando `/ventas` y verifica el correcto registro de la fecha y hora

## Notas de Implementación
- Esta modificación no afecta los registros existentes, solo los nuevos que se creen a partir de ahora
- Se recomienda verificar otras funcionalidades del bot para asegurar que también estén usando la zona horaria correcta