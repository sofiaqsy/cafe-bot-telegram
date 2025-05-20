"""
Manejador para el comando /evidencia.
Este comando es un alias simplificado del comando /documento,
específicamente para que sea más intuitivo para los usuarios.
"""

import logging
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from handlers.documents import documento_command, register_documents_handlers
from utils.sheets import get_all_data

# Configurar logging
logger = logging.getLogger(__name__)

async def evidencia_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Comando /evidencia para mostrar las compras registradas y permitir subir evidencias
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    logger.info(f"=== COMANDO /evidencia INICIADO por {username} (ID: {user_id}) ===")
    
    # Mostrar las compras recientes para que el usuario pueda ver sus IDs
    try:
        compras = get_all_data('compras')
        if compras:
            # Ordenar las compras por fecha (más recientes primero)
            compras_recientes = sorted(compras, key=lambda x: x.get('fecha', ''), reverse=True)[:10]
            
            mensaje = "📋 *ÚLTIMAS COMPRAS REGISTRADAS*\n\n"
            for compra in compras_recientes:
                compra_id = compra.get('id', 'Sin ID')
                fecha = compra.get('fecha', 'Fecha desconocida')
                proveedor = compra.get('proveedor', 'Proveedor desconocido')
                tipo_cafe = compra.get('tipo_cafe', 'Tipo desconocido')
                cantidad = compra.get('cantidad', '0')
                total = compra.get('preciototal', '0')
                
                mensaje += f"• *ID: {compra_id}*\n"
                mensaje += f"  📅 {fecha} | {proveedor}\n"
                mensaje += f"  ☕ {tipo_cafe}: {cantidad} kg | S/ {total}\n\n"
            
            mensaje += "Para subir una evidencia de pago, selecciona una de las compras."
            await update.message.reply_text(mensaje, parse_mode="Markdown")
        else:
            await update.message.reply_text("No hay compras registradas. Usa /compra para registrar una nueva compra.")
    except Exception as e:
        logger.error(f"Error al obtener compras: {e}")
        await update.message.reply_text("Ocurrió un error al obtener las compras. Continuando con el proceso de carga de evidencia.")
    
    logger.info(f"Redirigiendo al flujo de /documento para seleccionar tipo de operación")
    # Redirigimos al comando /documento para mantener un solo flujo
    return await documento_command(update, context)

def register_evidencias_handlers(application):
    """Registra los handlers para el módulo de evidencias"""
    # Agregar el comando /evidencia como alias de /documento
    application.add_handler(CommandHandler("evidencia", evidencia_command))
    logger.info("Handler de evidencias registrado")
