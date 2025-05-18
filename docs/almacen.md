# Sistema de Almacén Centralizado

## Introducción

El sistema de almacén centralizado es una mejora crucial para el bot de gestión de café que permite tener un control unificado y actualizado de todo el inventario de café en sus diferentes fases.

Anteriormente, el sistema dependía únicamente de rastrear los kilogramos disponibles en cada compra individual, lo que dificultaba tener una visión global del inventario. Con el nuevo sistema de almacén, se mantiene un registro centralizado que se actualiza automáticamente con cada operación de compra, proceso o venta.

## Características principales

- **Registro centralizado**: Mantiene un registro único de todas las existencias de café por fase.
- **Actualización automática**: Se sincroniza automáticamente cuando se registran compras o procesos.
- **Consistencia de datos**: Garantiza que la información de inventario esté siempre actualizada y sea confiable.
- **Gestión simplificada**: Permite ver y gestionar el inventario desde un único lugar.
- **Operaciones manuales**: Permite realizar ajustes manuales cuando sea necesario.

## Comandos y funciones

### Comando /almacen

Este comando permite acceder a todas las funcionalidades del sistema de almacén. Al ejecutarlo, se muestran las siguientes opciones:

- **Ver inventario**: Muestra un resumen de las cantidades disponibles en cada fase.
- **Sincronizar con compras**: Actualiza el almacén basándose en los registros de compras actuales.
- **Actualizar manualmente**: Permite ajustar manualmente las cantidades de una fase específica.

### Integración con el comando /proceso

El sistema de almacén se integra con el comando /proceso para:

1. Mostrar las cantidades disponibles en cada fase al iniciar un proceso.
2. Validar que hay suficiente cantidad disponible para procesar.
3. Actualizar automáticamente las cantidades de origen y destino cuando se completa un proceso.
4. Registrar las mermas adecuadamente.

## Estructura técnica

El sistema se compone de los siguientes elementos:

1. **Tabla en Google Sheets**: Una nueva hoja llamada "almacen" con las columnas:
   - fase: Identifica la fase del café (CEREZO, MOTE, PERGAMINO, etc.)
   - cantidad: Cantidad disponible en kilogramos
   - ultima_actualizacion: Fecha y hora de la última modificación
   - notas: Información adicional sobre los cambios

2. **Funciones en utils/sheets.py**:
   - `get_almacen_cantidad`: Obtiene la cantidad disponible para una fase
   - `update_almacen`: Actualiza la cantidad de una fase (sumar, restar o establecer)
   - `actualizar_almacen_desde_proceso`: Actualiza el almacén durante un proceso
   - `sincronizar_almacen_con_compras`: Sincroniza el almacén con las compras registradas

3. **Handlers en handlers/almacen.py**:
   - Gestiona la conversación para visualizar y modificar el almacén
   - Implementa lógica para sincronizar con las compras
   - Proporciona validación de datos de entrada

## Flujo de trabajo común

1. **Inicialización**: Al iniciar el bot, se crea y configura la hoja de almacén si no existe.
2. **Compra**: Al registrar una compra, se actualiza automáticamente el inventario.
3. **Proceso**: Al procesar café, se restan kilos de la fase de origen y se suman a la fase de destino (menos la merma).
4. **Verificación**: En cualquier momento, el usuario puede usar el comando /almacen para verificar el estado del inventario.
5. **Sincronización**: Si hay discrepancias, se puede usar la opción de sincronización para corregirlas.

## Mejores prácticas

- **Verificación periódica**: Es recomendable revisar el inventario regularmente para detectar discrepancias.
- **Sincronización**: Ejecutar la sincronización con compras si se sospecha que hay inconsistencias.
- **Ajustes manuales**: Utilizar los ajustes manuales solo cuando sea estrictamente necesario y documentar la razón.
- **Trazabilidad**: Revisar las notas de actualización para entender los cambios en el inventario.

## Solución de problemas

Si se observan discrepancias entre las cantidades mostradas en el almacén y las reales:

1. Verificar que todas las operaciones (compras, procesos) se hayan registrado correctamente.
2. Utilizar la opción "Sincronizar con compras" para actualizar el almacén.
3. Si persisten las discrepancias, realizar un ajuste manual con notas detalladas.
4. Para problemas técnicos, revisar los logs del bot donde se registran todas las operaciones de almacén.