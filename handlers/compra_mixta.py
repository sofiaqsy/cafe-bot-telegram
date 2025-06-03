# Headers para la hoja de compras mixtas
# NOTA: Esta hoja está definida en utils/sheets/constants.py junto con las demás hojas
# Fue necesario corregir el problema de sintaxis en constants.py para evitar errores 
# durante la inicialización del bot.
COMPRAS_MIXTAS_HEADERS = [
    "id", "fecha", "tipo_cafe", "proveedor", "cantidad", "precio", "preciototal", 
    "metodo_pago", "monto_efectivo", "monto_transferencia", "monto_adelanto", 
    "adelanto_id", "registrado_por", "notas"
]