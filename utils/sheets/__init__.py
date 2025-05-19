"""
Inicialización del paquete utils/sheets refactorizado.
Este archivo expone todas las funciones necesarias para mantener compatibilidad con el código existente.
"""

# Constantes
from utils.sheets.constants import (
    FASES_CAFE,
    TRANSICIONES_PERMITIDAS,
    MERMAS_SUGERIDAS,
    HEADERS
)

# Servicios
from utils.sheets.service import (
    get_sheet_service,
    get_or_create_sheet,
    get_sheets_initialized,
    set_sheets_initialized
)

# Funciones principales (core)
from utils.sheets.core import (
    initialize_sheets,
    append_data,
    update_cell,
    get_all_data,
    get_filtered_data
)

# Funciones de almacén
from utils.sheets.almacen import (
    get_compras_por_fase,
    get_almacen_cantidad,
    update_almacen_tostado,
    update_almacen,
    leer_almacen_para_proceso,
    sincronizar_almacen_con_compras
)

# Funciones de proceso
from utils.sheets.process import (
    es_transicion_valida,
    calcular_merma_sugerida,
    actualizar_almacen_desde_proceso
)

# Utilidades
from utils.sheets.utils import (
    generate_unique_id,
    generate_almacen_id,
    format_date_for_sheets,
    get_current_datetime_str,
    safe_float
)
