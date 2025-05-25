"""
Módulo para el comando /evidencias.
Este comando permite visualizar las últimas evidencias registradas.
"""

import logging
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from utils.sheets import get_all_data

# Configurar logging
logger = logging.getLogger(__name__)

async def evidencias_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /evidencias para mostrar las últimas 10 evidencias registradas
    ordenadas por fecha (más reciente primero)
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    logger.info(f"=== COMANDO /evidencias INICIADO por {username} (ID: {user_id}) ===")
    
    try:
        # Obtener todas las evidencias
        evidencias = get_all_data("documentos")
        
        if not evidencias:
            await update.message.reply_text(
                "📂 *EVIDENCIAS REGISTRADAS*\n\n"
                "No hay evidencias registradas en el sistema.\n\n"
                "Utiliza el comando /evidencia para registrar una nueva evidencia.",
                parse_mode="Markdown"
            )
            return
        
        # Ordenar por fecha descendente (más reciente primero)
        evidencias_ordenadas = sorted(evidencias, key=lambda x: x.get('fecha', ''), reverse=True)
        
        # Limitar a las últimas 10 evidencias
        evidencias_recientes = evidencias_ordenadas[:10]
        
        # Preparar mensaje
        mensaje = "📂 *ÚLTIMAS EVIDENCIAS REGISTRADAS*\n\n"
        
        # Añadir cada evidencia al mensaje
        for i, evidencia in enumerate(evidencias_recientes, 1):
            tipo_op = evidencia.get('tipo_operacion', 'N/A')
            op_id = evidencia.get('operacion_id', 'N/A')
            fecha = evidencia.get('fecha', 'Fecha desconocida')
            id_doc = evidencia.get('id', 'N/A')
            
            drive_link = ""
            if evidencia.get('drive_view_link'):
                drive_link = f" - [Ver en Drive]({evidencia.get('drive_view_link')})"
            
            mensaje += f"{i}. *{tipo_op}* - ID: {op_id}\n"
            mensaje += f"   📅 {fecha} - Doc: {id_doc}{drive_link}\n\n"
        
        # Añadir nota sobre el total de evidencias
        total_evidencias = len(evidencias)
        if total_evidencias > 10:
            mensaje += f"_Mostrando 10 de {total_evidencias} evidencias. Las evidencias se ordenan por fecha (más reciente primero)._"
        
        await update.message.reply_text(mensaje, parse_mode="Markdown", disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error al listar evidencias: {e}")
        await update.message.reply_text(
            "❌ Error al obtener las evidencias.\n\n"
            "Por favor, intenta nuevamente más tarde o contacta al administrador.",
            parse_mode="Markdown"
        )

def register_evidencias_list_handlers(application):
    """Registra los handlers para el módulo de listado de evidencias"""
    try:
        # Registrar comando para listar evidencias
        application.add_handler(CommandHandler("evidencias", evidencias_command))
        logger.info("Handler de listado de evidencias registrado")
        return True
    except Exception as e:
        logger.error(f"Error al registrar handler de listado de evidencias: {e}")
        return False
