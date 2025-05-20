# Inclusión del monto en el nombre del archivo de evidencia

## Problema
Actualmente, cuando se sube una evidencia de pago a través del comando `/EVIDENCIA`, el nombre del archivo generado no incluye el monto de la operación, lo que dificulta la identificación rápida de los archivos por su valor monetario.

## Solución
Se modificó el archivo `handlers/evidencias.py` para incluir el monto de la compra o venta en el nombre del archivo de evidencia, facilitando su identificación y organización.

## Cambios realizados

1. **Obtención del monto**: Se modificó la función `seleccionar_operacion` para buscar y almacenar el monto de la operación seleccionada:
   ```python
   operacion_data = get_filtered_data(operacion_sheet, {"id": operacion_id})
   if operacion_data and len(operacion_data) > 0:
       # Guardar el monto para usarlo en el nombre del archivo
       if tipo_operacion == "COMPRA":
           monto = operacion_data[0].get('preciototal', '0')
       else:  # VENTA
           monto = operacion_data[0].get('total', '0')
       datos_evidencia[user_id]["monto"] = monto_limpio
   ```

2. **Inclusión en el nombre del archivo**: Se modificó la generación del nombre del archivo para incluir el monto:
   ```python
   nombre_archivo = f"{tipo_op}_{op_id}_S{monto}_{uuid.uuid4().hex[:8]}.jpg"
   ```

3. **Visualización del monto en los mensajes**: Se actualizaron los mensajes de confirmación y éxito para mostrar explícitamente el monto:
   ```python
   mensaje_confirmacion = f"Tipo de operación: {datos_evidencia[user_id]['tipo_operacion']}\n" \
                       f"ID de operación: {op_id}\n" \
                       f"Monto: S/ {monto}\n" \
                       f"Archivo guardado como: {nombre_archivo}"
   ```

## Formato del nuevo nombre de archivo
El nuevo formato para los nombres de archivo es:
```
{tipo_de_operacion}_{id_operacion}_S{monto}_{identificador_unico}.jpg
```

Por ejemplo:
```
compra_C2025051234_S530.50_a1b2c3d4.jpg
```

Este formato permite identificar:
- Tipo de operación (compra/venta)
- ID de la operación
- Monto de la operación (prefijado con "S" para indicar soles)
- Identificador único para evitar duplicados

## Cómo probar
1. Ejecutar el comando `/EVIDENCIA`
2. Seleccionar "Compras" o "Ventas"
3. Elegir una operación de la lista
4. Subir una imagen de evidencia
5. Verificar que el nombre del archivo mostrado en el mensaje de confirmación incluya el monto de la operación
6. Si se usa Google Drive, verificar que el archivo en Drive también tenga el monto en su nombre
