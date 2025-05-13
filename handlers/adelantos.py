import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler
)
from datetime import datetime
import traceback

# Importar módulos para Google Sheets
from utils.db import append_data, get_all_data
from utils.helpers import format_currency, get_now_peru
from utils.sheets import update_cell

# Estados para la conversación
PROVEEDOR, MONTO, NOTAS, CONFIRMAR = range(4)

# Estados para la gestión de adelantos
EDITAR_MONTO, EDITAR_NOTAS, CONFIRMAR_EDICION = range(4, 7)

# Estados para el filtro de proveedores
SELECCIONAR_PROVEEDOR = 7

# Logger
logger = logging.getLogger(__name__)

# Headers para la hoja de adelantos
ADELANTOS_HEADERS = ["fecha", "hora", "proveedor", "monto", "saldo_restante", "notas", "registrado_por"]

# Función para obtener fecha y hora actuales
def get_now():
    now = datetime.now()
    return now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")

# Funciones para el manejo de adelantos
async def adelanto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Iniciar el proceso de registro de adelanto"""
    await update.message.reply_text(
        "📝 Registro de adelanto a proveedor\n\n"
        "Los adelantos son pagos anticipados a proveedores que se descontarán de futuras compras.\n\n"
        "Por favor, ingresa el nombre del proveedor:"
    )
    return PROVEEDOR

async def proveedor_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibir nombre del proveedor"""
    context.user_data['proveedor'] = update.message.text.strip()
    
    # Verificar si ya tiene adelantos vigentes
    try:
        adelantos = get_all_data("adelantos")
        
        # Filtrar adelantos del proveedor con saldo
        adelantos_proveedor = []
        for adelanto in adelantos:
            if adelanto.get('proveedor') == context.user_data['proveedor']:
                try:
                    saldo = float(adelanto.get('saldo_restante', 0))
                    if saldo > 0:
                        adelantos_proveedor.append(adelanto)
                except (ValueError, TypeError):
                    continue
        
        # Calcular saldo total
        if adelantos_proveedor:
            saldo_total = sum(float(adelanto.get('saldo_restante', 0)) for adelanto in adelantos_proveedor)
            await update.message.reply_text(
                f"ℹ️ El proveedor {context.user_data['proveedor']} ya tiene adelantos vigentes "
                f"por un total de {format_currency(saldo_total)}.\n\n"
                "Este nuevo adelanto se sumará al saldo existente."
            )
    except Exception as e:
        logger.error(f"Error al verificar adelantos del proveedor: {e}")
    
    await update.message.reply_text(
        "💸 ¿Cuál es el monto del adelanto? (en S/)"
    )
    return MONTO

async def monto_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibir monto del adelanto"""
    try:
        monto_text = update.message.text.replace(',', '.').strip()
        monto = float(monto_text)
        
        if monto <= 0:
            await update.message.reply_text("⚠️ El monto debe ser mayor a cero. Intenta de nuevo:")
            return MONTO
        
        context.user_data['monto'] = monto
        context.user_data['saldo_restante'] = monto
        
        await update.message.reply_text(
            "📝 Opcionalmente, puedes agregar notas o detalles sobre este adelanto:\n"
            "(Envía '-' si no deseas agregar notas)"
        )
        return NOTAS
    except ValueError:
        await update.message.reply_text(
            "⚠️ El valor ingresado no es válido. Por favor, ingresa solo números:"
        )
        return MONTO

async def notas_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibir notas adicionales"""
    if update.message.text.strip() == '-':
        context.user_data['notas'] = ''
    else:
        context.user_data['notas'] = update.message.text.strip()
    
    # Mostrar resumen para confirmar
    await update.message.reply_text(
        f"📋 RESUMEN DEL ADELANTO\n\n"
        f"Proveedor: {context.user_data['proveedor']}\n"
        f"Monto: {format_currency(context.user_data['monto'])}\n"
        f"Saldo restante: {format_currency(context.user_data['saldo_restante'])}\n"
        f"Notas: {context.user_data['notas'] or 'N/A'}\n\n"
        f"¿Confirmas este adelanto? (Sí/No)"
    )
    return CONFIRMAR

async def confirmar_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirmar y guardar el adelanto"""
    respuesta = update.message.text.lower()
    
    if respuesta in ['sí', 'si', 's', 'yes', 'y']:
        # Guardar el adelanto
        fecha, hora = get_now()
        
        data = {
            "fecha": fecha,
            "hora": hora,
            "proveedor": context.user_data['proveedor'],
            "monto": context.user_data['monto'],
            "saldo_restante": context.user_data['saldo_restante'],
            "notas": context.user_data['notas'],
            "registrado_por": update.effective_user.username or update.effective_user.first_name
        }
        
        try:
            # Guardar el adelanto usando la función append_data
            append_data("adelantos", data, ADELANTOS_HEADERS)
            
            await update.message.reply_text(
                f"✅ Adelanto registrado correctamente\n\n"
                f"Se ha registrado un adelanto de {format_currency(context.user_data['monto'])} "
                f"para el proveedor {context.user_data['proveedor']}.\n\n"
                f"Este monto se descontará automáticamente de futuras compras a este proveedor.\n\n"
                f"Usa /compra_adelanto para registrar una compra con este adelanto."
            )
        except Exception as e:
            logger.error(f"Error guardando adelanto: {e}")
            logger.error(traceback.format_exc())
            await update.message.reply_text(
                "❌ Error al registrar el adelanto. Por favor, intenta nuevamente."
            )
    else:
        await update.message.reply_text("❌ Registro cancelado")
    
    # Limpiar datos de usuario
    context.user_data.clear()
    return ConversationHandler.END

async def cancelar_adelanto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancelar el registro de adelanto"""
    await update.message.reply_text(
        "❌ Registro de adelanto cancelado",
        reply_markup=None
    )
    context.user_data.clear()
    return ConversationHandler.END

async def lista_adelantos_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostrar lista de adelantos vigentes con opciones interactivas"""
    try:
        # Obtener adelantos desde Google Sheets
        adelantos = get_all_data("adelantos")
        
        if not adelantos:
            await update.message.reply_text("No hay adelantos registrados.")
            return
        
        # Filtrar adelantos con saldo positivo
        adelantos_vigentes = []
        for adelanto in adelantos:
            try:
                saldo = float(adelanto.get('saldo_restante', 0))
                if saldo > 0:
                    adelantos_vigentes.append(adelanto)
            except (ValueError, TypeError):
                continue
        
        if not adelantos_vigentes:
            await update.message.reply_text("No hay adelantos vigentes con saldo disponible.")
            return
        
        # Agrupar adelantos por proveedor
        proveedores = {}
        for adelanto in adelantos_vigentes:
            proveedor = adelanto.get('proveedor', '')
            monto = float(adelanto.get('monto', 0))
            saldo = float(adelanto.get('saldo_restante', 0))
            fecha = adelanto.get('fecha', '')
            row_index = adelanto.get('_row_index')
            
            if proveedor not in proveedores:
                proveedores[proveedor] = {
                    'adelantos': [],
                    'total_monto': 0,
                    'total_saldo': 0
                }
            
            proveedores[proveedor]['adelantos'].append({
                'fecha': fecha,
                'monto': monto,
                'saldo': saldo,
                'row_index': row_index
            })
            proveedores[proveedor]['total_monto'] += monto
            proveedores[proveedor]['total_saldo'] += saldo
        
        # Crear mensaje con los adelantos agrupados
        mensaje = "💰 ADELANTOS VIGENTES:\n\n"
        
        # Crear botones para filtrar por proveedor
        keyboard = []
        keyboard.append([InlineKeyboardButton("🔍 Buscar por proveedor", callback_data="buscar_proveedor")])
        keyboard.append([InlineKeyboardButton("📊 Ver todos los proveedores", callback_data="ver_todos")])
        
        for proveedor, datos in proveedores.items():
            keyboard.append([InlineKeyboardButton(
                f"{proveedor} - {format_currency(datos['total_saldo'])}", 
                callback_data=f"proveedor_{proveedor}"
            )])
            
            mensaje += f"👨‍🌾 Proveedor: {proveedor}\n"
            mensaje += f"💵 Total adelantado: {format_currency(datos['total_monto'])}\n"
            mensaje += f"💰 Saldo disponible: {format_currency(datos['total_saldo'])}\n"
            mensaje += "📝 Detalle de adelantos:\n"
            
            for adelanto in datos['adelantos']:
                mensaje += f"   • {adelanto['fecha']}: {format_currency(adelanto['monto'])} " \
                           f"(Saldo: {format_currency(adelanto['saldo'])})\n"
            
            mensaje += "\n"
        
        # Añadir instrucciones para usar adelantos
        mensaje += "Para usar estos adelantos en una compra, utiliza el comando /compra_adelanto.\n"
        mensaje += "Para ver detalles o gestionar un adelanto específico, usa los botones a continuación:"
        
        # Crear teclado inline para botones
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Enviar mensaje (limitar a 4000 caracteres si es necesario)
        if len(mensaje) > 4000:
            mensaje = mensaje[:3950] + "...\n\n(Mensaje truncado debido a su longitud)"
        
        await update.message.reply_text(mensaje, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error obteniendo adelantos: {e}")
        logger.error(traceback.format_exc())
        await update.message.reply_text(f"Error al obtener los adelantos: {str(e)}")

async def proveedor_adelantos_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostrar los adelantos de un proveedor específico"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "ver_todos":
        # Volver a mostrar todos los adelantos
        await lista_adelantos_command(update, context)
        return
    
    if query.data == "buscar_proveedor":
        # Iniciar búsqueda por proveedor
        await query.edit_message_text(
            "🔍 Introduce el nombre del proveedor que deseas buscar:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancelar", callback_data="ver_todos")]
            ])
        )
        return
    
    # Extraer nombre del proveedor del callback_data
    proveedor = query.data.replace("proveedor_", "")
    
    try:
        # Obtener adelantos del proveedor
        adelantos = get_all_data("adelantos")
        
        # Filtrar adelantos del proveedor con saldo positivo
        adelantos_proveedor = []
        for adelanto in adelantos:
            if adelanto.get('proveedor') == proveedor:
                try:
                    saldo = float(adelanto.get('saldo_restante', 0))
                    if saldo > 0:
                        adelantos_proveedor.append(adelanto)
                except (ValueError, TypeError):
                    continue
        
        if not adelantos_proveedor:
            await query.edit_message_text(
                f"No hay adelantos vigentes para el proveedor {proveedor}.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver", callback_data="ver_todos")]
                ])
            )
            return
        
        # Calcular totales
        total_monto = sum(float(adelanto.get('monto', 0)) for adelanto in adelantos_proveedor)
        total_saldo = sum(float(adelanto.get('saldo_restante', 0)) for adelanto in adelantos_proveedor)
        
        # Crear mensaje detallado
        mensaje = f"📋 ADELANTOS DE {proveedor.upper()}\n\n"
        mensaje += f"💵 Total adelantado: {format_currency(total_monto)}\n"
        mensaje += f"💰 Saldo disponible: {format_currency(total_saldo)}\n\n"
        mensaje += "📝 DETALLE DE ADELANTOS:\n\n"
        
        # Crear teclado con opciones para cada adelanto
        keyboard = []
        
        for i, adelanto in enumerate(adelantos_proveedor):
            fecha = adelanto.get('fecha', '')
            monto = float(adelanto.get('monto', 0))
            saldo = float(adelanto.get('saldo_restante', 0))
            notas = adelanto.get('notas', 'Sin notas')
            row_index = adelanto.get('_row_index')
            
            mensaje += f"Adelanto #{i+1}:\n"
            mensaje += f"📅 Fecha: {fecha}\n"
            mensaje += f"💲 Monto: {format_currency(monto)}\n"
            mensaje += f"💰 Saldo: {format_currency(saldo)}\n"
            mensaje += f"📝 Notas: {notas}\n\n"
            
            # Añadir botones para editar este adelanto
            keyboard.append([
                InlineKeyboardButton(
                    f"✏️ Editar #{i+1}: {format_currency(saldo)}", 
                    callback_data=f"editar_{row_index}"
                )
            ])
        
        # Añadir botón para volver
        keyboard.append([InlineKeyboardButton("⬅️ Volver a todos los proveedores", callback_data="ver_todos")])
        
        # Añadir botón para registrar nuevo adelanto
        keyboard.append([InlineKeyboardButton("➕ Nuevo adelanto", callback_data="nuevo_adelanto")])
        
        # Enviar mensaje con teclado inline
        await query.edit_message_text(
            mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error al mostrar adelantos del proveedor: {e}")
        logger.error(traceback.format_exc())
        await query.edit_message_text(
            f"Error al obtener los adelantos: {str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Volver", callback_data="ver_todos")]
            ])
        )

async def editar_adelanto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Iniciar edición de un adelanto"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "nuevo_adelanto":
        await query.edit_message_text("Para registrar un nuevo adelanto, utiliza el comando /adelanto")
        return ConversationHandler.END
    
    # Extraer el row_index del adelanto
    row_index = int(query.data.replace("editar_", ""))
    context.user_data['row_index'] = row_index
    
    try:
        # Obtener datos del adelanto
        adelantos = get_all_data("adelantos")
        
        adelanto = None
        for a in adelantos:
            if a.get('_row_index') == row_index:
                adelanto = a
                break
        
        if not adelanto:
            await query.edit_message_text("No se encontró el adelanto seleccionado.")
            return ConversationHandler.END
        
        # Guardar datos del adelanto en el contexto
        context.user_data['adelanto'] = adelanto
        context.user_data['proveedor'] = adelanto.get('proveedor', '')
        context.user_data['monto_original'] = float(adelanto.get('monto', 0))
        context.user_data['saldo_original'] = float(adelanto.get('saldo_restante', 0))
        context.user_data['notas_original'] = adelanto.get('notas', '')
        
        # Crear teclado con opciones
        keyboard = [
            [InlineKeyboardButton("💰 Modificar saldo", callback_data="editar_saldo")],
            [InlineKeyboardButton("📝 Modificar notas", callback_data="editar_notas")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_edicion")]
        ]
        
        await query.edit_message_text(
            f"📋 EDITAR ADELANTO\n\n"
            f"Proveedor: {context.user_data['proveedor']}\n"
            f"Monto original: {format_currency(context.user_data['monto_original'])}\n"
            f"Saldo actual: {format_currency(context.user_data['saldo_original'])}\n"
            f"Notas: {context.user_data['notas_original'] or 'Sin notas'}\n\n"
            f"Selecciona qué quieres modificar:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return EDITAR_MONTO
    
    except Exception as e:
        logger.error(f"Error al iniciar edición de adelanto: {e}")
        logger.error(traceback.format_exc())
        await query.edit_message_text(
            f"Error al editar el adelanto: {str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Volver", callback_data="ver_todos")]
            ])
        )
        return ConversationHandler.END

async def editar_campo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Manejar la selección del campo a editar"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancelar_edicion":
        await query.edit_message_text("❌ Edición cancelada.")
        return ConversationHandler.END
    
    if query.data == "editar_saldo":
        await query.edit_message_text(
            f"Proveedor: {context.user_data['proveedor']}\n"
            f"Saldo actual: {format_currency(context.user_data['saldo_original'])}\n\n"
            "Ingresa el nuevo saldo para este adelanto:\n"
            "(Envía el mensaje con el nuevo monto)"
        )
        return EDITAR_MONTO
    
    if query.data == "editar_notas":
        await query.edit_message_text(
            f"Proveedor: {context.user_data['proveedor']}\n"
            f"Notas actuales: {context.user_data['notas_original'] or 'Sin notas'}\n\n"
            "Ingresa las nuevas notas para este adelanto:\n"
            "(Envía el mensaje con las nuevas notas)"
        )
        return EDITAR_NOTAS
    
    # Si llegamos aquí, algo salió mal
    await query.edit_message_text("⚠️ Opción no válida.")
    return ConversationHandler.END

async def editar_monto_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibir el nuevo monto del adelanto"""
    try:
        nuevo_monto_text = update.message.text.replace(',', '.').strip()
        nuevo_monto = float(nuevo_monto_text)
        
        if nuevo_monto < 0:
            await update.message.reply_text("⚠️ El saldo no puede ser negativo. Intenta de nuevo:")
            return EDITAR_MONTO
        
        if nuevo_monto > context.user_data['monto_original']:
            await update.message.reply_text(
                "⚠️ El nuevo saldo no puede ser mayor que el monto original del adelanto. "
                "Si deseas aumentar el saldo, registra un nuevo adelanto."
            )
            return EDITAR_MONTO
        
        context.user_data['nuevo_saldo'] = nuevo_monto
        
        await update.message.reply_text(
            f"📋 RESUMEN DE CAMBIOS:\n\n"
            f"Proveedor: {context.user_data['proveedor']}\n"
            f"Saldo anterior: {format_currency(context.user_data['saldo_original'])}\n"
            f"Nuevo saldo: {format_currency(context.user_data['nuevo_saldo'])}\n\n"
            f"¿Confirmas esta modificación? (Sí/No)"
        )
        return CONFIRMAR_EDICION
    except ValueError:
        await update.message.reply_text(
            "⚠️ El valor ingresado no es válido. Por favor, ingresa solo números:"
        )
        return EDITAR_MONTO

async def editar_notas_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibir las nuevas notas del adelanto"""
    context.user_data['nuevas_notas'] = update.message.text.strip()
    
    await update.message.reply_text(
        f"📋 RESUMEN DE CAMBIOS:\n\n"
        f"Proveedor: {context.user_data['proveedor']}\n"
        f"Notas anteriores: {context.user_data['notas_original'] or 'Sin notas'}\n"
        f"Nuevas notas: {context.user_data['nuevas_notas'] or 'Sin notas'}\n\n"
        f"¿Confirmas esta modificación? (Sí/No)"
    )
    return CONFIRMAR_EDICION

async def confirmar_edicion_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirmar y guardar la edición del adelanto"""
    respuesta = update.message.text.lower()
    
    if respuesta in ['sí', 'si', 's', 'yes', 'y']:
        try:
            row_index = context.user_data['row_index']
            
            # Actualizar el campo correspondiente
            if 'nuevo_saldo' in context.user_data:
                # Actualizar saldo
                nuevo_saldo = context.user_data['nuevo_saldo']
                update_cell("adelantos", row_index, "saldo_restante", nuevo_saldo)
                
                # Añadir nota sobre la modificación
                fecha_mod = get_now_peru().strftime("%Y-%m-%d %H:%M")
                usuario = update.effective_user.username or update.effective_user.first_name
                notas_originales = context.user_data['notas_original'] or ''
                nuevas_notas = f"{notas_originales}\n[{fecha_mod}] Saldo modificado de {format_currency(context.user_data['saldo_original'])} a {format_currency(nuevo_saldo)} por {usuario}"
                
                update_cell("adelantos", row_index, "notas", nuevas_notas)
                
                await update.message.reply_text(
                    f"✅ Saldo actualizado correctamente de "
                    f"{format_currency(context.user_data['saldo_original'])} a "
                    f"{format_currency(nuevo_saldo)}.\n\n"
                    f"Usa /adelantos para ver la lista actualizada."
                )
            
            elif 'nuevas_notas' in context.user_data:
                # Actualizar notas
                nuevas_notas = context.user_data['nuevas_notas']
                update_cell("adelantos", row_index, "notas", nuevas_notas)
                
                await update.message.reply_text(
                    f"✅ Notas actualizadas correctamente.\n\n"
                    f"Usa /adelantos para ver la lista actualizada."
                )
            
        except Exception as e:
            logger.error(f"Error actualizando adelanto: {e}")
            logger.error(traceback.format_exc())
            await update.message.reply_text(
                f"❌ Error al actualizar el adelanto: {str(e)}"
            )
    else:
        await update.message.reply_text("❌ Edición cancelada")
    
    # Limpiar datos de usuario
    context.user_data.clear()
    return ConversationHandler.END

async def buscar_proveedor_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Buscar un proveedor por nombre"""
    texto_busqueda = update.message.text.strip().lower()
    
    # Realizar búsqueda de adelantos por nombre de proveedor
    try:
        adelantos = get_all_data("adelantos")
        
        # Filtrar adelantos por coincidencia en el nombre del proveedor
        proveedores_coincidentes = set()
        for adelanto in adelantos:
            proveedor = adelanto.get('proveedor', '').lower()
            if texto_busqueda in proveedor and float(adelanto.get('saldo_restante', 0)) > 0:
                proveedores_coincidentes.add(adelanto.get('proveedor'))
        
        if not proveedores_coincidentes:
            await update.message.reply_text(
                f"No se encontraron proveedores con adelantos vigentes que coincidan con '{texto_busqueda}'.\n\n"
                f"Usa /adelantos para ver la lista completa."
            )
            return ConversationHandler.END
        
        # Crear teclado con los proveedores encontrados
        keyboard = []
        for proveedor in proveedores_coincidentes:
            keyboard.append([InlineKeyboardButton(
                f"{proveedor}", 
                callback_data=f"proveedor_{proveedor}"
            )])
        
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="ver_todos")])
        
        await update.message.reply_text(
            f"🔍 Resultados para '{texto_busqueda}':\n\n"
            f"Selecciona un proveedor:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return ConversationHandler.END
    
    except Exception as e:
        logger.error(f"Error en búsqueda de proveedor: {e}")
        logger.error(traceback.format_exc())
        await update.message.reply_text(
            f"❌ Error al buscar proveedores: {str(e)}"
        )
        return ConversationHandler.END

async def cancelar_busqueda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancelar la búsqueda de proveedor"""
    await update.message.reply_text(
        "❌ Búsqueda cancelada.\n\nUsa /adelantos para ver la lista completa."
    )
    return ConversationHandler.END

def register_adelantos_handlers(application):
    """Registrar handlers para adelantos"""
    logger.info("Registrando handlers de adelantos")
    
    # Registro de adelantos
    adelanto_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("adelanto", adelanto_command)],
        states={
            PROVEEDOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, proveedor_step)],
            MONTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, monto_step)],
            NOTAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, notas_step)],
            CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar_step)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_adelanto)],
    )
    
    # Edición de adelantos
    editar_adelanto_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(editar_adelanto_callback, pattern=r'^editar_\d+$')],
        states={
            EDITAR_MONTO: [
                CallbackQueryHandler(editar_campo_callback, pattern=r'^editar_(saldo|notas|cancelar_edicion)$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, editar_monto_step)
            ],
            EDITAR_NOTAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, editar_notas_step)],
            CONFIRMAR_EDICION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar_edicion_step)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_adelanto)],
    )
    
    # Búsqueda de proveedor
    buscar_proveedor_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(lambda u, c: SELECCIONAR_PROVEEDOR, pattern=r'^buscar_proveedor$')],
        states={
            SELECCIONAR_PROVEEDOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, buscar_proveedor_step)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_busqueda)],
    )
    
    # Listar adelantos
    application.add_handler(CommandHandler("adelantos", lista_adelantos_command))
    
    # Callbacks para manejar interacciones con los botones
    application.add_handler(CallbackQueryHandler(proveedor_adelantos_callback, pattern=r'^proveedor_|^ver_todos$'))
    application.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.edit_message_text("Usa /adelanto para registrar un nuevo adelanto"), pattern=r'^nuevo_adelanto$'))
    
    application.add_handler(adelanto_conv_handler)
    application.add_handler(editar_adelanto_conv_handler)
    application.add_handler(buscar_proveedor_conv_handler)
    
    logger.info("Handlers de adelantos registrados correctamente")