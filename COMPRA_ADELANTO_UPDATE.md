## Implementación completa de la funcionalidad Compra con Adelanto

Este commit completa la implementación de la funcionalidad "Compra con Adelanto", permitiendo al bot actualizar automáticamente los saldos de adelantos en Google Sheets cuando se realiza una compra utilizando adelantos existentes.

### Cambios realizados:

1. Adición de funcionalidad en `utils/sheets.py`:
   - Nueva función `update_cell()` para actualizar celdas específicas en Google Sheets
   - Mejora en `get_all_data()` para incluir el índice de fila en los registros devueltos

2. Actualización de `handlers/compra_adelanto.py`:
   - Implementación completa del flujo de "Compra con Adelanto"
   - Actualización automática de saldos de adelantos en Google Sheets
   - Mejora en la presentación de información al usuario

### Comportamiento antiguo:
Anteriormente, la funcionalidad "Compra con Adelanto" estaba parcialmente implementada. Registraba la compra pero no actualizaba automáticamente los saldos de adelantos, requiriendo actualización manual en Google Sheets.

### Comportamiento nuevo:
- Selección de proveedor con adelantos disponibles mediante botones
- Registro de datos de la compra (cantidad, precio, calidad)
- Cálculo automático de montos a pagar con adelanto y en efectivo
- Actualización automática de saldos de adelantos en Google Sheets
- Presentación detallada de los cambios realizados en los adelantos

Esta implementación completa el ciclo de funcionalidades relacionadas con adelantos, permitiendo:
1. Registrar adelantos a proveedores (`/adelanto`)
2. Visualizar adelantos vigentes (`/adelantos`)
3. Realizar compras utilizando adelantos (`/compra_adelanto`)

Con estos cambios, el bot ahora ofrece una solución integral para la gestión de adelantos a proveedores, mejorando significativamente la experiencia del usuario y reduciendo la necesidad de tareas manuales.