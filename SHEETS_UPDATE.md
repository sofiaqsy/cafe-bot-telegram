## Actualización de la configuración de Google Sheets

Este commit añade soporte para las nuevas hojas "adelantos" y "pedidos" en la configuración de Google Sheets.

### Cambios realizados:

1. Actualización del diccionario `SHEET_IDS` en `utils/sheets.py`:
   - Añadida la hoja "adelantos" con índice 4
   - Añadida la hoja "pedidos" con índice 5

2. Actualización del diccionario `HEADERS` en `utils/sheets.py`:
   - Añadidas las cabeceras para la hoja "adelantos": `['fecha', 'hora', 'proveedor', 'monto', 'saldo_restante', 'notas', 'registrado_por']`
   - Añadidas las cabeceras para la hoja "pedidos": `['fecha', 'hora', 'cliente', 'telefono', 'producto', 'cantidad', 'precio_unitario', 'total', 'direccion', 'estado', 'notas', 'registrado_por']`

Estos cambios permitirán que el bot pueda interactuar correctamente con las hojas "adelantos" y "pedidos" que ya existen en el documento de Google Sheets.

### Comportamiento anterior:
Antes de este cambio, el bot lanzaba un error `Nombre de hoja inválido: adelantos` al intentar registrar un adelanto, ya que la hoja no estaba definida en la configuración.

### Comportamiento nuevo:
Con este cambio, el bot podrá agregar y leer datos de las hojas "adelantos" y "pedidos" sin problemas, permitiendo el correcto funcionamiento de las nuevas funcionalidades implementadas.