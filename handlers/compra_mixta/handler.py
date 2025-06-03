"""
Registro de handlers para el módulo de compra mixta
"""
import logging
import traceback
from telegram.ext import (
    CommandHandler, ConversationHandler, 
    MessageHandler, filters, CallbackQueryHandler
)

from handlers.compra_mixta.config import (
    TIPO_CAFE, PROVEEDOR, CANTIDAD, PRECIO, METODO_PAGO, 
    MONTO_EFECTIVO, MONTO_TRANSFERENCIA, MONTO_ADELANTO, 
    MONTO_POR_PAGAR, SELECCIONAR_ADELANTO, CONFIRMAR
)
from handlers.compra_mixta.steps_inicio import (
    compra_mixta_command, tipo_cafe_step, proveedor_step
)
from handlers.compra_mixta.steps_compra import (
    cantidad_step, precio_step, metodo_pago_step
)
from handlers.compra_mixta.steps_pagos import (
    monto_efectivo_step, monto_transferencia_step, monto_adelanto_step
)
from handlers.compra_mixta.steps_adelanto import (
    seleccionar_adelanto_callback
)
from handlers.compra_mixta.steps_resumen import (
    confirmar_step, cancelar
)

logger = logging.getLogger(__name__)

def register_compra_mixta_handlers(application):
    """Registra los handlers para el módulo de compra mixta"""
    try:
        logger.info("Registrando handlers para compra mixta")
        
        # Crear manejador de conversación
        compra_mixta_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("compra_mixta", compra_mixta_command)],
            states={
                TIPO_CAFE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tipo_cafe_step)],
                PROVEEDOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, proveedor_step)],
                CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, cantidad_step)],
                PRECIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, precio_step)],
                METODO_PAGO: [MessageHandler(filters.TEXT & ~filters.COMMAND, metodo_pago_step)],
                MONTO_EFECTIVO: [MessageHandler(filters.TEXT & ~filters.COMMAND, monto_efectivo_step)],
                MONTO_TRANSFERENCIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, monto_transferencia_step)],
                MONTO_ADELANTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, monto_adelanto_step)],
                SELECCIONAR_ADELANTO: [CallbackQueryHandler(seleccionar_adelanto_callback, pattern=r'^adelanto_')],
                CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar_step)],
            },
            fallbacks=[CommandHandler("cancelar", cancelar)],
            # Añadir opción para permitir que se caigan las conversaciones después de cierto tiempo de inactividad
            conversation_timeout=900  # 15 minutos - para evitar conversaciones colgadas
        )
        
        # Agregar el manejador a la aplicación
        application.add_handler(compra_mixta_conv_handler)
        logger.info("Handlers de compra mixta registrados correctamente")
        
        return True
    except Exception as e:
        logger.error(f"Error al registrar handlers de compra_mixta: {e}")
        logger.error(traceback.format_exc())
        return False
