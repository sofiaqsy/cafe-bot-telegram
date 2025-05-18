import logging
import datetime
from telegram import Update
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes
from config import COMPRAS_FILE
from utils.db import append_data

# Configurar logging
logger = logging.getLogger(__name__)

# Estados para la conversación
PROVEEDOR, TIPO_CAFE, CANTIDAD, PRECIO, CONFIRMAR = range(5)  # Eliminamos CALIDAD

# Datos temporales
datos_compra = {}

# Headers para la hoja de compras
COMPRAS_HEADERS = ["fecha", "tipo_cafe", "proveedor", "cantidad", "precio", "total"]

async def compra_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de registro de compra"""
    logger.info(f"Usuario {update.effective_user.id} inició comando /compra")
    await update.message.reply_text(
        "Vamos a registrar una nueva compra de café.\n\n"
        "Por favor, ingresa el nombre del proveedor:"
    )
    return PROVEEDOR

async def proveedor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el proveedor y solicita el tipo de café"""
    user_id = update.effective_user.id
    proveedor_nombre = update.message.text
    logger.info(f"Usuario {user_id} ingresó proveedor: {proveedor_nombre}")
    
    datos_compra[user_id] = {"proveedor": proveedor_nombre}
    
    await update.message.reply_text(
        f"Proveedor: {proveedor_nombre}\n\n"
        "Ahora, ingresa el tipo de café (por ejemplo: Cereza, Pergamino, Oro, etc.):"
    )
    return TIPO_CAFE

async def tipo_cafe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el tipo de café y solicita la cantidad"""
    user_id = update.effective_user.id
    tipo = update.message.text.strip()
    logger.info(f"Usuario {user_id} ingresó tipo de café: {tipo}")
    
    if not tipo:
        await update.message.reply_text(
            "Por favor, ingresa un tipo de café válido."
        )
        return TIPO_CAFE
    
    datos_compra[user_id]["tipo_cafe"] = tipo
    
    await update.message.reply_text(
        f"Tipo de café: {tipo}\n\n"
        "Ahora, ingresa la cantidad de café en kg:"
    )
    return CANTIDAD

async def cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda la cantidad y solicita el precio"""
    user_id = update.effective_user.id
    try:
        cantidad_text = update.message.text.replace(',', '.').strip()
        cantidad = float(cantidad_text)
        logger.info(f"Usuario {user_id} ingresó cantidad: {cantidad}")
        
        if cantidad <= 0:
            await update.message.reply_text("La cantidad debe ser mayor que cero. Intenta nuevamente:")
            return CANTIDAD
        
        datos_compra[user_id]["cantidad"] = cantidad
        
        await update.message.reply_text(
            f"Cantidad: {cantidad} kg\n\n"
            "Ahora, ingresa el precio por kg (solo el número):"
        )
        return PRECIO
    except ValueError:
        logger.warning(f"Usuario {user_id} ingresó un valor inválido para cantidad: {update.message.text}")
        await update.message.reply_text(
            "Por favor, ingresa un número válido para la cantidad."
        )
        return CANTIDAD

async def precio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el precio y solicita confirmación"""
    user_id = update.effective_user.id
    try:
        precio_text = update.message.text.replace(',', '.').strip()
        precio = float(precio_text)
        logger.info(f"Usuario {user_id} ingresó precio: {precio}")
        
        if precio <= 0:
            await update.message.reply_text("El precio debe ser mayor que cero. Intenta nuevamente:")
            return PRECIO
        
        datos_compra[user_id]["precio"] = precio
        
        # Calcular el total
        compra = datos_compra[user_id]
        total = compra["cantidad"] * compra["precio"]
        
        # Guardar el total en los datos
        datos_compra[user_id]["total"] = total
        
        # Mostrar resumen para confirmar
        await update.message.reply_text(
            "📝 *Resumen de la compra*\n\n"
            f"Proveedor: {compra['proveedor']}\n"
            f"Tipo de café: {compra['tipo_cafe']}\n"
            f"Cantidad: {compra['cantidad']} kg\n"
            f"Precio: {compra['precio']} por kg\n"
            f"Total: {total}\n\n"
            "¿Confirmar esta compra? (Sí/No)",
            parse_mode="Markdown"
        )
        return CONFIRMAR
        
    except ValueError:
        logger.warning(f"Usuario {user_id} ingresó un valor inválido para precio: {update.message.text}")
        await update.message.reply_text(
            "Por favor, ingresa un número válido para el precio."
        )
        return PRECIO

async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y guarda la compra"""
    user_id = update.effective_user.id
    respuesta = update.message.text.lower()
    logger.info(f"Usuario {user_id} respondió a confirmación: {respuesta}")
    
    if respuesta in ["sí", "si", "s", "yes", "y"]:
        # Preparar datos para guardar
        compra = datos_compra[user_id].copy()
        
        # Añadir fecha
        compra["fecha"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Verificar que todos los datos requeridos estén presentes
        campos_requeridos = ["proveedor", "tipo_cafe", "cantidad", "precio", "total"]
        datos_completos = all(campo in compra for campo in campos_requeridos)
        
        if not datos_completos:
            logger.error(f"Datos incompletos para usuario {user_id}: {compra}")
            await update.message.reply_text(
                "❌ Error: Datos incompletos. Por favor, inicia el proceso nuevamente con /compra."
            )
            if user_id in datos_compra:
                del datos_compra[user_id]
            return ConversationHandler.END
        
        logger.info(f"Guardando compra en Google Sheets: {compra}")
        
        # Guardar la compra en Google Sheets a través de db.py
        try:
            # Convertir valores numéricos a string para evitar problemas
            compra["cantidad"] = str(compra["cantidad"]).replace('.', ',')
            compra["precio"] = str(compra["precio"]).replace('.', ',')
            compra["total"] = str(compra["total"]).replace('.', ',')
            
            # Llamar a la función para guardar los datos
            append_data(COMPRAS_FILE, compra, COMPRAS_HEADERS)
            
            logger.info(f"Compra guardada exitosamente para usuario {user_id}")
            
            await update.message.reply_text(
                "✅ ¡Compra registrada exitosamente!\n\n"
                "Usa /compra para registrar otra compra."
            )
        except Exception as e:
            logger.error(f"Error al guardar compra: {e}")
            await update.message.reply_text(
                "❌ Error al guardar la compra. Por favor, intenta nuevamente.\n\n"
                f"Error: {str(e)}\n\n"
                "Contacta al administrador si el problema persiste."
            )
    else:
        logger.info(f"Usuario {user_id} canceló la compra")
        await update.message.reply_text(
            "❌ Compra cancelada.\n\n"
            "Usa /compra para iniciar de nuevo."
        )
    
    # Limpiar datos temporales
    if user_id in datos_compra:
        del datos_compra[user_id]
    
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la conversación"""
    user_id = update.effective_user.id
    logger.info(f"Usuario {user_id} canceló el proceso de compra con /cancelar")
    
    # Limpiar datos temporales
    if user_id in datos_compra:
        del datos_compra[user_id]
    
    await update.message.reply_text(
        "❌ Operación cancelada.\n\n"
        "Usa /compra para iniciar de nuevo cuando quieras."
    )
    
    return ConversationHandler.END

def register_compras_handlers(application):
    """Registra los handlers para el módulo de compras"""
    # Crear manejador de conversación
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("compra", compra_command)],
        states={
            PROVEEDOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, proveedor)],
            TIPO_CAFE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tipo_cafe)],
            CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, cantidad)],
            PRECIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, precio)],
            CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    
    # Agregar el manejador al dispatcher
    application.add_handler(conv_handler)
    logger.info("Handlers de compras registrados")