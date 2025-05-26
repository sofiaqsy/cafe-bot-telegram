"""
Módulo que contiene las constantes utilizadas por el sistema de hojas de cálculo.
"""

# Definir constantes
FASES_CAFE = ["CEREZO", "MOTE", "PERGAMINO", "VERDE", "TOSTADO", "MOLIDO"]

# Definir transiciones válidas entre fases
TRANSICIONES_PERMITIDAS = {
    "CEREZO": ["MOTE", "PERGAMINO"],  # Actualizado para permitir CEREZO a PERGAMINO
    "MOTE": ["PERGAMINO"],
    "PERGAMINO": ["VERDE", "TOSTADO", "MOLIDO"],
    "VERDE": ["TOSTADO"],
    "TOSTADO": ["MOLIDO"],
    "MOLIDO": []
}

# Porcentajes aproximados de merma por tipo de transición
MERMAS_SUGERIDAS = {
    "CEREZO_MOTE": 0.85,      # 85% de pérdida de peso cerezo a mote
    "CEREZO_PERGAMINO": 0.88, # 88% de pérdida de cerezo a pergamino (agregado)
    "MOTE_PERGAMINO": 0.20,   # 20% de pérdida de mote a pergamino
    "PERGAMINO_VERDE": 0.18,  # 18% de pérdida de pergamino a verde
    "PERGAMINO_TOSTADO": 0.20, # 20% de pérdida de pergamino a tostado
    "PERGAMINO_MOLIDO": 0.25, # 25% de pérdida de pergamino a molido
    "VERDE_TOSTADO": 0.15,    # 15% de pérdida de verde a tostado
    "TOSTADO_MOLIDO": 0.05    # 5% de pérdida de tostado a molido
}

# Cabeceras para las hojas
HEADERS = {
    "compras": ["id", "fecha", "tipo_cafe", "proveedor", "cantidad", "precio", "preciototal", "registrado_por", "notas"],
    "proceso": ["fecha", "origen", "destino", "cantidad", "compras_ids", "merma", "merma_estimada", "cantidad_resultante_esperada", "cantidad_resultante", "notas", "registrado_por"],
    "gastos": ["fecha", "categoria", "monto", "descripcion", "registrado_por"],
    "ventas": ["fecha", "cliente", "tipo_cafe", "peso", "precio_kg", "total", "almacen_id", "notas", "registrado_por"],
    "pedidos": ["fecha", "cliente", "tipo_cafe", "cantidad", "precio_kg", "total", "estado", "fecha_entrega", "notas", "registrado_por"],
    "adelantos": ["fecha", "hora", "proveedor", "monto", "saldo_restante", "notas", "registrado_por"],
    "almacen": ["id", "compra_id", "tipo_cafe_origen", "fecha", "cantidad", "fase_actual", "cantidad_actual", "notas", "fecha_actualizacion"],
    "documentos": ["id", "fecha", "tipo_operacion", "operacion_id", "archivo_id", "ruta_archivo", "drive_file_id", "drive_view_link", "registrado_por", "notas"],
    "capitalizacion": ["id", "fecha", "monto", "origen", "destino", "concepto", "registrado_por", "notas"]
}