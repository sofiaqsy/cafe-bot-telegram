"""
Módulo para gestionar clientes de WhatsApp desde Telegram
Permite ver, filtrar y actualizar el estado de los clientes
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters
)
import logging
from datetime import datetime
import pytz
from config import SPREADSHEET_ID, DRIVE_EVIDENCIAS_ROOT_ID
import time

# Configurar zona horaria de Perú
peru_tz = pytz.timezone('America/Lima')

# Estados de conversación
MENU_PRINCIPAL, BUSCAR_INPUT, VER_CLIENTE, CAMBIAR_ESTADO = range(4)

# Configuración de logging
logger = logging.getLogger(__name__)

# Cache para reducir llamadas a la API
CACHE_CLIENTES = {
    'data': None,
    'timestamp': None,
    'ttl': 30  # segundos de vida del caché
}

# Estados disponibles para los clientes
ESTADOS_CLIENTE = [
    "Pendiente",
    "Verificado", 
    "Prospecto",
    "Cliente activo",
    "Cliente VIP",
    "Suspendido",
    "Rechazado",
    "Inactivo"
]

def obtener_datos_clientes(force_refresh=False):
    """
    Obtiene los clientes de Google Sheets con caché
    
    Args:
        force_refresh: Si True, ignora el caché y obtiene datos frescos
    """
    global CACHE_CLIENTES
    
    # Verificar si el caché es válido
    ahora = time.time()
    if not force_refresh and CACHE_CLIENTES['data'] and CACHE_CLIENTES['timestamp']:
        edad_cache = ahora - CACHE_CLIENTES['timestamp']
        if edad_cache < CACHE_CLIENTES['ttl']:
            logger.info(f"Usando caché de clientes ({edad_cache:.1f}s de antigüedad)")
            return CACHE_CLIENTES['data']
    
    try:
        logger.info("Obteniendo clientes frescos de Google Sheets...")
        from utils.sheets import get_sheet_service
        service = get_sheet_service()
        
        if not service:
            logger.error("No se pudo obtener el servicio de Google Sheets")
            if CACHE_CLIENTES['data']:
                logger.info("Usando caché anterior debido a error de servicio")
                return CACHE_CLIENTES['data']
            return None
            
        # Obtener datos de la hoja Clientes (columnas A hasta Q para incluir URLs de imágenes)
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='Clientes!A:Q'
        ).execute()
        
        values = result.get('values', [])
        
        # Actualizar caché
        CACHE_CLIENTES['data'] = values
        CACHE_CLIENTES['timestamp'] = ahora
        
        logger.info(f"Clientes actualizados: {len(values)} filas")
        return values
        
    except Exception as e:
        if "RATE_LIMIT_EXCEEDED" in str(e):
            logger.warning("Límite de API excedido, usando caché si está disponible")
            if CACHE_CLIENTES['data']:
                return CACHE_CLIENTES['data']
            else:
                logger.error("No hay caché disponible")
                return None
        else:
            logger.error(f"Error obteniendo clientes: {e}")
            if CACHE_CLIENTES['data']:
                logger.info("Usando caché anterior debido a error")
                return CACHE_CLIENTES['data']
            return None

def limpiar_cache():
    """Limpia el caché de clientes"""
    global CACHE_CLIENTES
    CACHE_CLIENTES['data'] = None
    CACHE_CLIENTES['timestamp'] = None
    logger.info("Caché limpiado")

def actualizar_celda_cliente(fila, columna, valor):
    """Actualiza una celda en Google Sheets con retry en caso de límite"""
    max_reintentos = 3
    espera = 2  # segundos
    
    for intento in range(max_reintentos):
        try:
            from utils.sheets import get_sheet_service
            service = get_sheet_service()
            
            if not service:
                return False
            
            # Convertir columna número a letra
            columna_letra = chr(64 + columna)  # 1=A, 2=B, etc.
            rango = f'Clientes!{columna_letra}{fila}'
            
            body = {'values': [[valor]]}
            
            result = service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=rango,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            # Si la actualización fue exitosa, limpiar caché
            limpiar_cache()
            
            return True
            
        except Exception as e:
            if "RATE_LIMIT_EXCEEDED" in str(e) and intento < max_reintentos - 1:
                logger.warning(f"Límite excedido, esperando {espera}s antes de reintentar...")
                time.sleep(espera)
                espera *= 2  # Backoff exponencial
            else:
                logger.error(f"Error actualizando celda: {e}")
                return False
    
    return False

async def clientes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Comando principal para gestionar clientes"""
    
    # Limpiar cualquier dato anterior del contexto
    context.user_data.clear()
    
    keyboard = [
        [InlineKeyboardButton("Ver clientes pendientes", callback_data="cli_pendientes")],
        [InlineKeyboardButton("Ver todos los clientes", callback_data="cli_todos")],
        [InlineKeyboardButton("Buscar por WhatsApp", callback_data="cli_buscar_whatsapp")],
        [InlineKeyboardButton("Buscar por empresa", callback_data="cli_buscar_empresa")],
        [InlineKeyboardButton("Actualizar caché", callback_data="cli_refresh")],
        [InlineKeyboardButton("Salir", callback_data="cli_salir")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Mostrar estado del caché
    cache_info = ""
    if CACHE_CLIENTES['timestamp']:
        edad = int(time.time() - CACHE_CLIENTES['timestamp'])
        if edad < 60:
            cache_info = f"_Caché: actualizado hace {edad}s_\n"
        else:
            cache_info = f"_Caché: actualizado hace {edad//60}min_\n"
    
    mensaje = f"""
*👥 GESTIÓN DE CLIENTES*
━━━━━━━━━━━━━━━━━━━━━

{cache_info}
Selecciona una opción:

• *Ver pendientes*: Clientes por verificar
• *Ver todos*: Lista completa de clientes
• *Buscar por WhatsApp*: Buscar cliente específico
• *Buscar por empresa*: Filtrar por nombre
• *Actualizar caché*: Recargar datos

_Comando rápido: /cli_
"""
    
    try:
        if update.message:
            await update.message.reply_text(
                mensaje,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                mensaje,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error en clientes_command: {e}")
        if update.message:
            await update.message.reply_text(mensaje, reply_markup=reply_markup, parse_mode='Markdown')
        elif update.callback_query:
            await update.callback_query.message.reply_text(mensaje, reply_markup=reply_markup, parse_mode='Markdown')
    
    return MENU_PRINCIPAL

async def menu_principal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja las opciones del menú principal"""
    query = update.callback_query
    await query.answer()
    
    opcion = query.data.replace("cli_", "")
    
    if opcion == "salir":
        await query.edit_message_text("Sesión finalizada\n\nUsa /clientes o /cli para volver a empezar")
        return ConversationHandler.END
    
    elif opcion == "refresh":
        await query.edit_message_text("Actualizando caché...")
        limpiar_cache()
        clientes = obtener_datos_clientes(force_refresh=True)
        
        if clientes:
            mensaje = f"Caché actualizado\n\nTotal de filas: {len(clientes)}\n"
            if len(clientes) > 1:
                mensaje += f"Clientes (sin header): {len(clientes) - 1}"
            else:
                mensaje += "No hay clientes registrados"
                
            keyboard = [[InlineKeyboardButton("Volver", callback_data="cli_volver_menu")]]
            await query.edit_message_text(
                mensaje,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text("Error al actualizar caché\n\nIntenta más tarde")
            return ConversationHandler.END
        
        return MENU_PRINCIPAL
    
    elif opcion == "volver_menu":
        return await clientes_command(update, context)
    
    elif opcion == "pendientes":
        await query.edit_message_text("Cargando clientes pendientes...")
        
        clientes = obtener_datos_clientes()
        
        if not clientes:
            await query.edit_message_text(
                "Error al obtener clientes\n\n"
                "_Posible límite de API excedido. Intenta en unos segundos._"
            )
            return ConversationHandler.END
        
        if len(clientes) <= 1:
            keyboard = [[InlineKeyboardButton("Volver", callback_data="cli_volver_menu")]]
            await query.edit_message_text(
                "No hay clientes registrados",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return MENU_PRINCIPAL
        
        # Filtrar clientes PENDIENTES
        clientes_pendientes = []
        
        for i, cliente in enumerate(clientes[1:], start=2):  # Skip header
            if len(cliente) > 15:
                estado = cliente[15] if cliente[15] else "Pendiente"
                if estado == "Pendiente":
                    clientes_pendientes.append((i, cliente))
        
        if not clientes_pendientes:
            keyboard = [[InlineKeyboardButton("Volver", callback_data="cli_volver_menu")]]
            await query.edit_message_text(
                "No hay clientes pendientes de verificación",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return MENU_PRINCIPAL
        
        await mostrar_lista_clientes(query, clientes_pendientes, "👥 CLIENTES PENDIENTES")
        return VER_CLIENTE
    
    elif opcion == "todos":
        await query.edit_message_text("Cargando todos los clientes...")
        
        clientes = obtener_datos_clientes()
        
        if not clientes or len(clientes) <= 1:
            keyboard = [[InlineKeyboardButton("Volver", callback_data="cli_volver_menu")]]
            await query.edit_message_text(
                "No hay clientes registrados",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return MENU_PRINCIPAL
        
        todos_clientes = [(i, cliente) for i, cliente in enumerate(clientes[1:], start=2)]
        
        await mostrar_lista_clientes(query, todos_clientes, "👥 TODOS LOS CLIENTES")
        return VER_CLIENTE
    
    elif opcion == "buscar_whatsapp":
        await query.edit_message_text(
            "*BUSCAR POR WHATSAPP*\n\n"
            "Envía el número de WhatsApp\n"
            "Ejemplo: `936934501`\n\n"
            "_Escribe /cancelar para salir_",
            parse_mode='Markdown'
        )
        context.user_data['buscar_tipo'] = 'whatsapp'
        return BUSCAR_INPUT
    
    elif opcion == "buscar_empresa":
        await query.edit_message_text(
            "*BUSCAR POR EMPRESA*\n\n"
            "Envía el nombre de la empresa\n"
            "Ejemplo: `Café Rico`\n\n"
            "_Escribe /cancelar para salir_",
            parse_mode='Markdown'
        )
        context.user_data['buscar_tipo'] = 'empresa'
        return BUSCAR_INPUT

async def buscar_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la búsqueda por WhatsApp o empresa"""
    texto = update.message.text.strip()
    tipo_busqueda = context.user_data.get('buscar_tipo')
    
    await update.message.reply_text("Buscando...")
    
    clientes = obtener_datos_clientes()
    
    if not clientes:
        await update.message.reply_text(
            "Error al obtener clientes\n\n"
            "_Posible límite de API excedido. Intenta en unos segundos._"
        )
        return ConversationHandler.END
        
    if len(clientes) <= 1:
        await update.message.reply_text("No hay clientes registrados")
        return ConversationHandler.END
    
    clientes_encontrados = []
    
    if tipo_busqueda == 'whatsapp':
        # Normalizar teléfono
        texto = texto.replace("+51", "").replace(" ", "").replace("-", "")
        
        # Buscar por WhatsApp en columna B (índice 1)
        for i, cliente in enumerate(clientes[1:], start=2):
            if len(cliente) > 1:
                whatsapp_cliente = str(cliente[1]).replace("+51", "").replace("'", "")
                if texto in whatsapp_cliente:
                    clientes_encontrados.append((i, cliente))
    
    elif tipo_busqueda == 'empresa':
        # Buscar por empresa en columna C (índice 2)
        for i, cliente in enumerate(clientes[1:], start=2):
            if len(cliente) > 2 and cliente[2]:
                if texto.lower() in str(cliente[2]).lower():
                    clientes_encontrados.append((i, cliente))
    
    if not clientes_encontrados:
        keyboard = [[InlineKeyboardButton("Volver al menú", callback_data="cli_volver_menu")]]
        await update.message.reply_text(
            f"No se encontraron clientes\n\nBuscaste: *{texto}*\nTipo: {tipo_busqueda}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return MENU_PRINCIPAL
    
    titulo = f"BÚSQUEDA: {texto}"
    await mostrar_lista_clientes(update, clientes_encontrados, titulo)
    return VER_CLIENTE

async def mostrar_lista_clientes(query_or_update, clientes, titulo):
    """Muestra una lista de clientes con botones"""
    mensaje = f"""
*{titulo}*
━━━━━━━━━━━━━━━━━━━━━
Total: *{len(clientes)}* cliente(s)

"""
    
    keyboard = []
    
    for fila, cliente in clientes[:10]:  # Máximo 10 clientes
        try:
            # Columnas esperadas:
            # A:ID, B:WhatsApp, C:Empresa, D:Contacto, E:Telefono, 
            # F:Email, G:Direccion, H:Distrito, I:Ciudad, J:FechaRegistro,
            # K:UltimaCompra, L:TotalPedidos, M:TotalComprado, N:TotalKg, 
            # O:Notas, P:EstadoCliente, Q:URLImagenes
            
            id_cliente = cliente[0] if len(cliente) > 0 else "Sin ID"
            whatsapp = cliente[1] if len(cliente) > 1 else "-"
            empresa = cliente[2] if len(cliente) > 2 else "-"
            contacto = cliente[3] if len(cliente) > 3 else "-"
            distrito = cliente[7] if len(cliente) > 7 else "-"
            total_pedidos = cliente[11] if len(cliente) > 11 else "0"
            estado = cliente[15] if len(cliente) > 15 else "Pendiente"
            
            # Truncar nombres largos
            if len(empresa) > 20:
                empresa_corta = empresa[:20] + "..."
            else:
                empresa_corta = empresa
            
            mensaje += f"`{id_cliente}`\n"
            mensaje += f"WhatsApp: {whatsapp}\n"
            mensaje += f"Empresa: {empresa}\n"
            mensaje += f"Contacto: {contacto}\n"
            mensaje += f"Distrito: {distrito}\n"
            mensaje += f"Pedidos: {total_pedidos} | Estado: *{estado}*\n"
            mensaje += f"━━━━━━━━━━━━━━━\n"
            
            # Botón con empresa y estado
            texto_boton = f"{empresa_corta} - {estado}"
            if len(texto_boton) > 35:
                texto_boton = texto_boton[:32] + "..."
            
            keyboard.append([
                InlineKeyboardButton(
                    texto_boton,
                    callback_data=f"ver_{fila}_{id_cliente}"
                )
            ])
            
        except Exception as e:
            logger.error(f"Error formateando cliente: {e}")
            continue
    
    if len(clientes) > 10:
        mensaje += f"\n_Mostrando 10 de {len(clientes)} clientes_"
    
    keyboard.append([
        InlineKeyboardButton("Volver al menú", callback_data="cli_volver_menu")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        if hasattr(query_or_update, 'edit_message_text'):
            await query_or_update.edit_message_text(
                mensaje,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await query_or_update.message.reply_text(
                mensaje,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error mostrando lista: {e}")
        if hasattr(query_or_update, 'message'):
            await query_or_update.message.reply_text(mensaje, reply_markup=reply_markup, parse_mode='Markdown')

async def ver_detalle_cliente(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra el detalle de un cliente específico"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cli_volver_menu":
        return await clientes_command(update, context)
    
    # Parsear datos del callback
    partes = query.data.split("_", 2)
    if len(partes) < 3 or partes[0] != "ver":
        return VER_CLIENTE
    
    try:
        fila = int(partes[1])
        id_cliente = partes[2]
    except (ValueError, IndexError):
        await query.edit_message_text("Error al procesar el cliente")
        return VER_CLIENTE
    
    # Guardar en contexto
    context.user_data['fila_actual'] = fila
    context.user_data['id_cliente_actual'] = id_cliente
    
    await query.edit_message_text("Cargando detalle...")
    
    # Obtener cliente actualizado
    clientes = obtener_datos_clientes()
    if not clientes or len(clientes) < fila:
        await query.edit_message_text("Error al obtener el cliente")
        return ConversationHandler.END
    
    cliente = clientes[fila - 1]
    
    # Formatear detalle
    mensaje = formatear_detalle_cliente(cliente)
    
    # Crear botones de estados
    keyboard = []
    estado_actual = cliente[15] if len(cliente) > 15 else "Pendiente"
    
    # Organizar estados en filas de 2
    estados_disponibles = []
    for i, estado in enumerate(ESTADOS_CLIENTE):
        if estado != estado_actual:
            if estado in ["Verificado", "Cliente activo", "Cliente VIP"]:
                texto_estado = f"✅ {estado}"
            elif estado in ["Rechazado", "Suspendido"]:
                texto_estado = f"❌ {estado}"
            else:
                texto_estado = estado
                
            estados_disponibles.append(
                InlineKeyboardButton(
                    texto_estado,
                    callback_data=f"estado_{i}"
                )
            )
    
    # Agrupar de a 2
    for i in range(0, len(estados_disponibles), 2):
        if i + 1 < len(estados_disponibles):
            keyboard.append([estados_disponibles[i], estados_disponibles[i + 1]])
        else:
            keyboard.append([estados_disponibles[i]])
    
    # Botón de volver
    keyboard.append([
        InlineKeyboardButton("↩️ Volver", callback_data="cli_volver_menu")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        mensaje,
        reply_markup=reply_markup,
        parse_mode='Markdown',
        disable_web_page_preview=True  # Para no mostrar preview de URLs
    )
    
    return CAMBIAR_ESTADO

def formatear_detalle_cliente(cliente):
    """Formatea el detalle de un cliente"""
    try:
        # Extraer campos con valores por defecto
        id_cliente = cliente[0] if len(cliente) > 0 else "N/A"
        whatsapp = cliente[1] if len(cliente) > 1 else "N/A"
        empresa = cliente[2] if len(cliente) > 2 else "N/A"
        contacto = cliente[3] if len(cliente) > 3 else "N/A"
        telefono = cliente[4] if len(cliente) > 4 else "N/A"
        email = cliente[5] if len(cliente) > 5 else "N/A"
        direccion = cliente[6] if len(cliente) > 6 else "N/A"
        distrito = cliente[7] if len(cliente) > 7 else "N/A"
        ciudad = cliente[8] if len(cliente) > 8 else "N/A"
        fecha_registro = cliente[9] if len(cliente) > 9 else "N/A"
        ultima_compra = cliente[10] if len(cliente) > 10 else "N/A"
        total_pedidos = cliente[11] if len(cliente) > 11 else "0"
        total_comprado = cliente[12] if len(cliente) > 12 else "0"
        total_kg = cliente[13] if len(cliente) > 13 else "0"
        notas = cliente[14] if len(cliente) > 14 else ""
        estado = cliente[15] if len(cliente) > 15 else "Pendiente"
        url_imagenes = cliente[16] if len(cliente) > 16 else ""
        
        # Limpiar WhatsApp
        if whatsapp != "N/A":
            whatsapp = str(whatsapp).replace("'", "")
        
        mensaje = f"""
*DETALLE DEL CLIENTE*
━━━━━━━━━━━━━━━━━━━━━

ID: `{id_cliente}`
Estado: *{estado}*

*INFORMACIÓN DE CONTACTO*
WhatsApp: {whatsapp}
Teléfono: {telefono}
Email: {email}

*DATOS EMPRESARIALES*
Empresa: *{empresa}*
Contacto: {contacto}
Dirección: {direccion}
Distrito: {distrito}
Ciudad: {ciudad}

*HISTORIAL*
Fecha registro: {fecha_registro}
Última compra: {ultima_compra}
Total pedidos: *{total_pedidos}*
Total comprado: *S/ {total_comprado}*
Total kg: *{total_kg} kg*
"""
        
        # Agregar notas si existen
        if notas and notas != "N/A":
            mensaje += f"\n*NOTAS*\n_{notas}_\n"
        
        # Agregar URL de imágenes si existe
        if url_imagenes and url_imagenes != "N/A":
            # Si hay múltiples URLs, separarlas
            if "," in url_imagenes:
                urls = url_imagenes.split(",")
                mensaje += f"\n*DOCUMENTOS ({len(urls)} archivo(s))*\n"
                for i, url in enumerate(urls[:3], 1):  # Máximo 3 URLs
                    url = url.strip()
                    if url.startswith("http"):
                        mensaje += f"{i}. [Ver documento {i}]({url})\n"
                if len(urls) > 3:
                    mensaje += f"_...y {len(urls) - 3} más_\n"
            else:
                mensaje += f"\n*DOCUMENTOS*\n[Ver documento]({url_imagenes})\n"
        
        mensaje += f"""
━━━━━━━━━━━━━━━━━━━━━
_Selecciona nuevo estado:_
"""
        
        return mensaje
        
    except Exception as e:
        logger.error(f"Error formateando detalle: {e}")
        return f"Error al formatear cliente"

async def cambiar_estado_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cambia el estado de un cliente"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cli_volver_menu":
        return await clientes_command(update, context)
    
    if not query.data.startswith("estado_"):
        return CAMBIAR_ESTADO
    
    try:
        # Obtener nuevo estado
        estado_index = int(query.data.replace("estado_", ""))
        nuevo_estado = ESTADOS_CLIENTE[estado_index]
    except (ValueError, IndexError):
        await query.edit_message_text("Error: Estado no válido")
        return CAMBIAR_ESTADO
    
    # Obtener datos guardados
    fila = context.user_data.get('fila_actual')
    id_cliente = context.user_data.get('id_cliente_actual')
    
    if not fila or not id_cliente:
        await query.edit_message_text("Error: No se pudo identificar el cliente")
        return ConversationHandler.END
    
    await query.edit_message_text(f"Actualizando estado a: {nuevo_estado}...")
    
    # Actualizar estado (columna P = columna 16)
    exito = actualizar_celda_cliente(fila, 16, nuevo_estado)
    
    if exito:
        # Actualizar notas con timestamp
        ahora = datetime.now(peru_tz)
        timestamp = ahora.strftime("%d/%m %H:%M")
        usuario = update.effective_user.username or update.effective_user.first_name
        
        # Obtener notas actuales
        clientes = obtener_datos_clientes()
        notas_actuales = ""
        if clientes and len(clientes) >= fila and len(clientes[fila - 1]) > 14:
            notas_actuales = clientes[fila - 1][14] or ""
        
        # Nueva nota
        nueva_nota = f"[{timestamp}] Estado: {nuevo_estado} - @{usuario}"
        if notas_actuales:
            nueva_nota = f"{nueva_nota}\n{notas_actuales}"
        
        # Limitar longitud
        if len(nueva_nota) > 500:
            nueva_nota = nueva_nota[:497] + "..."
        
        # Actualizar notas (columna O = columna 15)
        actualizar_celda_cliente(fila, 15, nueva_nota)
        
        # Mensaje de confirmación con emojis según el estado
        emoji = ""
        if nuevo_estado in ["Verificado", "Cliente activo", "Cliente VIP"]:
            emoji = "✅"
        elif nuevo_estado in ["Rechazado", "Suspendido"]:
            emoji = "❌"
        elif nuevo_estado == "Pendiente":
            emoji = "⏳"
        elif nuevo_estado == "Prospecto":
            emoji = "🔍"
        else:
            emoji = "📝"
        
        mensaje = f"""
{emoji} *ESTADO ACTUALIZADO*
━━━━━━━━━━━━━━━━━━━━━

Cliente: `{id_cliente}`
Nuevo estado: *{nuevo_estado}*
Actualizado por: @{usuario}
Hora: {timestamp}

_El cambio se ha guardado en Google Sheets_
"""
        
        keyboard = [
            [InlineKeyboardButton("Ver más clientes", callback_data="cli_pendientes")],
            [InlineKeyboardButton("Menú principal", callback_data="cli_volver_menu")]
        ]
        
        await query.edit_message_text(
            mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return MENU_PRINCIPAL
        
    else:
        keyboard = [[InlineKeyboardButton("Intentar de nuevo", callback_data="cli_volver_menu")]]
        await query.edit_message_text(
            "Error al actualizar el estado\n\nIntenta de nuevo en unos segundos",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return MENU_PRINCIPAL

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación actual"""
    context.user_data.clear()
    await update.message.reply_text("Operación cancelada\n\nUsa /clientes o /cli para empezar de nuevo")
    return ConversationHandler.END

async def timeout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja timeout de la conversación"""
    context.user_data.clear()
    if update.callback_query:
        await update.callback_query.answer("Sesión expirada. Usa /clientes para empezar de nuevo")
    return ConversationHandler.END

def register_clientes_handlers(application):
    """Registra los handlers del módulo de clientes"""
    
    # Configurar el ConversationHandler con timeout
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('clientes', clientes_command),
            CommandHandler('cli', clientes_command)  # Alias corto
        ],
        states={
            MENU_PRINCIPAL: [
                CallbackQueryHandler(menu_principal_callback, pattern='^cli_'),
                MessageHandler(filters.COMMAND, cancelar)
            ],
            BUSCAR_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, buscar_input),
                CallbackQueryHandler(menu_principal_callback, pattern='^cli_volver_menu$'),
                MessageHandler(filters.COMMAND, cancelar)
            ],
            VER_CLIENTE: [
                CallbackQueryHandler(ver_detalle_cliente, pattern='^ver_'),
                CallbackQueryHandler(clientes_command, pattern='^cli_volver_menu$'),
                MessageHandler(filters.COMMAND, cancelar)
            ],
            CAMBIAR_ESTADO: [
                CallbackQueryHandler(cambiar_estado_callback, pattern='^estado_'),
                CallbackQueryHandler(clientes_command, pattern='^cli_volver_menu$'),
                MessageHandler(filters.COMMAND, cancelar)
            ],
            ConversationHandler.TIMEOUT: [
                CallbackQueryHandler(timeout_handler),
                MessageHandler(filters.ALL, timeout_handler)
            ]
        },
        fallbacks=[
            CommandHandler('cancelar', cancelar),
            CommandHandler('cli', clientes_command),
            CommandHandler('clientes', clientes_command)
        ],
        conversation_timeout=300  # 5 minutos de timeout
    )
    
    application.add_handler(conv_handler)
    logger.info("Handlers de clientes registrados correctamente con timeout de 5 minutos")
