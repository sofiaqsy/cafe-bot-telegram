from telegram import Update
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler
)
import logging
from datetime import datetime

from utils.db import append_data
from utils.helpers import get_now_peru

# Estados para la conversación
NOMBRE_CLIENTE, TELEFONO, TIPO_CAFE, CANTIDAD, DIRECCION, CONFIRMAR = range(6)

# Configuración de logging
logger = logging.getLogger(__name__)

# Tipos de café disponibles
TIPOS_CAFE = {
    "1": {"nombre": "Café Arábica Premium", "precio": 50},
    "2": {"nombre": "Café Arábica Estándar", "precio": 40},
    "3": {"nombre": "Café Orgánico", "precio": 60},
    "4": {"nombre": "Café Mezcla", "precio": 35},
}

# Headers para la hoja de pedidos
PEDIDOS_HEADERS = ["fecha", "hora", "cliente", "telefono", "producto", "cantidad", "precio_unitario", "total", "direccion", "estado", "notas", "registrado_por"]

async def pedidos_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Iniciar el proceso de registro de pedidos"""
    keyboard_text = "Tipos de café disponibles:\n\n"
    for key, value in TIPOS_CAFE.items():
        keyboard_text += f"{key}. {value['nombre']} - S/ {value['precio']}/kg\n"
    
    keyboard_text += "\nPor favor, envía el nombre del cliente:"
    
    await update.message.reply_text(keyboard_text)
    return NOMBRE_CLIENTE

async def nombre_cliente_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibir nombre del cliente"""
    context.user_data['nombre_cliente'] = update.message.text
    
    await update.message.reply_text(
        "¡Perfecto! Ahora envía el número de teléfono del cliente (sin guiones ni espacios):"
    )
    return TELEFONO

async def telefono_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibir teléfono del cliente"""
    telefono = update.message.text.replace(" ", "").replace("-", "")
    
    # Validar teléfono (simple validación)
    if not telefono.isdigit() or len(telefono) < 8:
        await update.message.reply_text(
            "⚠️ El número de teléfono no es válido. Debe tener al menos 8 dígitos. Intenta nuevamente:"
        )
        return TELEFONO
    
    context.user_data['telefono'] = telefono
    
    keyboard_text = "Selecciona el tipo de café:\n\n"
    for key, value in TIPOS_CAFE.items():
        keyboard_text += f"{key}. {value['nombre']} - S/ {value['precio']}/kg\n"
    
    keyboard_text += "\nEnvía el número correspondiente:"
    
    await update.message.reply_text(keyboard_text)
    return TIPO_CAFE

async def tipo_cafe_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibir tipo de café"""
    tipo = update.message.text
    
    if tipo not in TIPOS_CAFE:
        await update.message.reply_text(
            "⚠️ Opción no válida. Selecciona un número del 1 al 4:"
        )
        return TIPO_CAFE
    
    context.user_data['tipo_cafe'] = TIPOS_CAFE[tipo]['nombre']
    context.user_data['precio'] = TIPOS_CAFE[tipo]['precio']
    
    await update.message.reply_text(
        "¿Cuántos kilogramos desea el cliente?"
    )
    return CANTIDAD

async def cantidad_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibir cantidad"""
    try:
        cantidad = float(update.message.text.replace(",", "."))
        if cantidad <= 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text(
            "⚠️ Por favor, ingresa una cantidad válida (número mayor a 0):"
        )
        return CANTIDAD
    
    context.user_data['cantidad'] = cantidad
    total = cantidad * context.user_data['precio']
    context.user_data['total'] = total
    
    await update.message.reply_text(
        f"Total del pedido: S/ {total:.2f}\n\n"
        "Ahora envía la dirección de entrega:"
    )
    return DIRECCION

async def direccion_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibir dirección"""
    context.user_data['direccion'] = update.message.text
    
    # Mostrar resumen del pedido
    resumen = f"""
📋 RESUMEN DEL PEDIDO

Cliente: {context.user_data['nombre_cliente']}
Teléfono: {context.user_data['telefono']}
Producto: {context.user_data['tipo_cafe']}
Cantidad: {context.user_data['cantidad']} kg
Precio unitario: S/ {context.user_data['precio']}/kg
Total: S/ {context.user_data['total']:.2f}
Dirección: {context.user_data['direccion']}

¿Confirmas el pedido? (Sí/No)
"""
    
    await update.message.reply_text(resumen)
    return CONFIRMAR

async def confirmar_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirmar y guardar el pedido"""
    respuesta = update.message.text.lower()
    
    if respuesta in ['sí', 'si', 's', 'yes', 'y']:
        # Guardar el pedido
        now = datetime.now()
        
        data = {
            "fecha": now.strftime("%Y-%m-%d"),
            "hora": now.strftime("%H:%M:%S"),
            "cliente": context.user_data['nombre_cliente'],
            "telefono": context.user_data['telefono'],
            "producto": context.user_data['tipo_cafe'],
            "cantidad": context.user_data['cantidad'],
            "precio_unitario": context.user_data['precio'],
            "total": context.user_data['total'],
            "direccion": context.user_data['direccion'],
            "estado": "Pendiente",
            "notas": "",
            "registrado_por": update.effective_user.username or update.effective_user.first_name
        }
        
        try:
            # Guardar el pedido usando la función append_data con los headers de pedidos
            append_data("pedidos", data, PEDIDOS_HEADERS)
            
            await update.message.reply_text(
                f"✅ Pedido registrado correctamente\n\n"
                f"Se ha generado el pedido para {context.user_data['nombre_cliente']}.\n"
                f"Total: S/ {context.user_data['total']:.2f}\n\n"
                f"Use /pedidos para ver los pedidos pendientes."
            )
        except Exception as e:
            logger.error(f"Error al guardar pedido: {e}")
            await update.message.reply_text(
                "❌ Error al registrar el pedido. Por favor, intenta nuevamente.\n\n"
                f"Error: {str(e)}"
            )
    else:
        await update.message.reply_text("❌ Pedido cancelado")
    
    # Limpiar datos de usuario
    context.user_data.clear()
    return ConversationHandler.END

async def cancelar_pedido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancelar el registro de pedido"""
    await update.message.reply_text(
        "❌ Registro de pedido cancelado",
        reply_markup=None
    )
    context.user_data.clear()
    return ConversationHandler.END

async def lista_pedidos_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostrar lista de pedidos pendientes"""
    try:
        # Obtener los pedidos (implementación futura con Google Sheets)
        # Por ahora, mostraremos un mensaje de que no hay pedidos
        await update.message.reply_text(
            "Esta función estará disponible próximamente. Se implementará la gestión de pedidos con Google Sheets."
        )
    except Exception as e:
        logger.error(f"Error obteniendo pedidos: {e}")
        await update.message.reply_text("Error al obtener los pedidos.")

async def marcar_entregado_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Marcar un pedido como entregado"""
    # Por implementar: un menú para seleccionar qué pedido marcar como entregado
    await update.message.reply_text(
        "Función en desarrollo. Por ahora, puedes ver los pedidos con /pedidos"
    )

def register_pedidos_handlers(application):
    """Registrar handlers de pedidos"""
    # Conversación para registro de pedidos
    pedido_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("pedido", pedidos_command)],
        states={
            NOMBRE_CLIENTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, nombre_cliente_step)],
            TELEFONO: [MessageHandler(filters.TEXT & ~filters.COMMAND, telefono_step)],
            TIPO_CAFE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tipo_cafe_step)],
            CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, cantidad_step)],
            DIRECCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, direccion_step)],
            CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar_step)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_pedido)],
    )
    
    application.add_handler(pedido_conv_handler)
    application.add_handler(CommandHandler("pedidos", lista_pedidos_command))
    application.add_handler(CommandHandler("entregado", marcar_entregado_command))