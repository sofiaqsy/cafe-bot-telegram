import logging
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from config import COMPRAS_FILE, PROCESO_FILE, GASTOS_FILE, VENTAS_FILE
from utils.db import read_data

# Configurar logging
logger = logging.getLogger(__name__)

# Tipos de reportes
GENERAL = "general"
DIARIO = "diario"
SEMANAL = "semanal"
MENSUAL = "mensual"

async def reporte_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra opciones de reportes disponibles"""
    logger.info(f"Usuario {update.effective_user.id} inició comando /reporte")
    
    keyboard = [
        [
            InlineKeyboardButton("📊 General", callback_data=f"reporte_{GENERAL}"),
            InlineKeyboardButton("📆 Diario", callback_data=f"reporte_{DIARIO}")
        ],
        [
            InlineKeyboardButton("🗓️ Semanal", callback_data=f"reporte_{SEMANAL}"),
            InlineKeyboardButton("📅 Mensual", callback_data=f"reporte_{MENSUAL}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Selecciona el tipo de reporte que deseas ver:",
        reply_markup=reply_markup
    )

async def reporte_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja los callbacks de los botones de reportes"""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    # Obtener el tipo de reporte de callback_data
    tipo_reporte = query.data.split("_")[1]
    logger.info(f"Usuario {user_id} solicitó reporte de tipo: {tipo_reporte}")
    
    # Generar el reporte según el tipo
    if tipo_reporte == GENERAL:
        mensaje = await generar_reporte_general()
    elif tipo_reporte == DIARIO:
        mensaje = await generar_reporte_diario()
    elif tipo_reporte == SEMANAL:
        mensaje = await generar_reporte_semanal()
    elif tipo_reporte == MENSUAL:
        mensaje = await generar_reporte_mensual()
    else:
        mensaje = "Tipo de reporte no válido."
        logger.warning(f"Usuario {user_id} solicitó un tipo de reporte inválido: {tipo_reporte}")
    
    logger.info(f"Enviando reporte de tipo {tipo_reporte} a usuario {user_id}")
    await query.edit_message_text(
        text=mensaje,
        parse_mode="Markdown"
    )

async def generar_reporte_general() -> str:
    """Genera un reporte general con todas las operaciones"""
    try:
        logger.info("Generando reporte general")
        
        # Leer datos
        compras = read_data(COMPRAS_FILE)
        procesos = read_data(PROCESO_FILE)
        gastos = read_data(GASTOS_FILE)
        ventas = read_data(VENTAS_FILE)
        
        logger.info(f"Datos leídos para reporte general: {len(compras)} compras, {len(procesos)} procesos, {len(gastos)} gastos, {len(ventas)} ventas")
        
        # Estadísticas básicas
        total_compras = sum(float(c.get("cantidad", 0)) for c in compras)
        total_ventas = sum(float(v.get("cantidad", 0)) for v in ventas)
        monto_compras = sum(float(c.get("cantidad", 0)) * float(c.get("precio", 0)) for c in compras)
        monto_ventas = sum(float(v.get("total", 0)) for v in ventas)
        monto_gastos = sum(float(g.get("monto", 0)) for g in gastos)
        
        # Calcular utilidad
        utilidad = monto_ventas - monto_compras - monto_gastos
        
        # Generar mensaje de reporte
        mensaje = "📊 *REPORTE GENERAL*\n\n"
        mensaje += "*Estadísticas Globales:*\n"
        mensaje += f"- Compras registradas: {len(compras)}\n"
        mensaje += f"- Procesos registrados: {len(procesos)}\n"
        mensaje += f"- Gastos registrados: {len(gastos)}\n"
        mensaje += f"- Ventas registradas: {len(ventas)}\n\n"
        
        mensaje += "*Café:*\n"
        mensaje += f"- Total comprado: {total_compras} kg\n"
        mensaje += f"- Total vendido: {total_ventas} kg\n"
        mensaje += f"- Inventario estimado: {total_compras - total_ventas} kg\n\n"
        
        mensaje += "*Financiero:*\n"
        mensaje += f"- Monto en compras: {monto_compras}\n"
        mensaje += f"- Monto en gastos: {monto_gastos}\n"
        mensaje += f"- Monto en ventas: {monto_ventas}\n"
        mensaje += f"- *Utilidad: {utilidad}*\n"
        
        return mensaje
    except Exception as e:
        logger.error(f"Error al generar el reporte general: {e}")
        return f"Error al generar el reporte general: {str(e)}"

async def generar_reporte_diario() -> str:
    """Genera un reporte de las operaciones del día actual"""
    try:
        logger.info("Generando reporte diario")
        
        # Obtener fecha actual
        hoy = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Leer datos
        compras = read_data(COMPRAS_FILE)
        procesos = read_data(PROCESO_FILE)
        gastos = read_data(GASTOS_FILE)
        ventas = read_data(VENTAS_FILE)
        
        # Filtrar datos del día
        compras_hoy = [c for c in compras if c.get("fecha", "").startswith(hoy)]
        procesos_hoy = [p for p in procesos if p.get("fecha", "").startswith(hoy)]
        gastos_hoy = [g for g in gastos if g.get("fecha", "").startswith(hoy)]
        ventas_hoy = [v for v in ventas if v.get("fecha", "").startswith(hoy)]
        
        logger.info(f"Datos filtrados para reporte diario: {len(compras_hoy)} compras, {len(procesos_hoy)} procesos, {len(gastos_hoy)} gastos, {len(ventas_hoy)} ventas")
        
        # Estadísticas básicas
        total_compras = sum(float(c.get("cantidad", 0)) for c in compras_hoy)
        total_ventas = sum(float(v.get("cantidad", 0)) for v in ventas_hoy)
        monto_compras = sum(float(c.get("cantidad", 0)) * float(c.get("precio", 0)) for c in compras_hoy)
        monto_ventas = sum(float(v.get("total", 0)) for v in ventas_hoy)
        monto_gastos = sum(float(g.get("monto", 0)) for g in gastos_hoy)
        
        # Calcular utilidad
        utilidad = monto_ventas - monto_compras - monto_gastos
        
        # Generar mensaje de reporte
        mensaje = f"📆 *REPORTE DIARIO ({hoy})*\n\n"
        mensaje += "*Operaciones del día:*\n"
        mensaje += f"- Compras realizadas: {len(compras_hoy)}\n"
        mensaje += f"- Procesos realizados: {len(procesos_hoy)}\n"
        mensaje += f"- Gastos realizados: {len(gastos_hoy)}\n"
        mensaje += f"- Ventas realizadas: {len(ventas_hoy)}\n\n"
        
        mensaje += "*Café:*\n"
        mensaje += f"- Café comprado hoy: {total_compras} kg\n"
        mensaje += f"- Café vendido hoy: {total_ventas} kg\n\n"
        
        mensaje += "*Financiero:*\n"
        mensaje += f"- Gastos del día: {monto_gastos}\n"
        mensaje += f"- Ingresos del día: {monto_ventas}\n"
        mensaje += f"- *Flujo neto: {utilidad}*\n"
        
        return mensaje
    except Exception as e:
        logger.error(f"Error al generar el reporte diario: {e}")
        return f"Error al generar el reporte diario: {str(e)}"

async def generar_reporte_semanal() -> str:
    """Genera un reporte de las operaciones de la última semana"""
    try:
        logger.info("Generando reporte semanal")
        
        # Obtener fechas
        hoy = datetime.datetime.now()
        hace_una_semana = hoy - datetime.timedelta(days=7)
        fecha_inicio = hace_una_semana.strftime("%Y-%m-%d")
        fecha_fin = hoy.strftime("%Y-%m-%d")
        
        # Leer datos
        compras = read_data(COMPRAS_FILE)
        procesos = read_data(PROCESO_FILE)
        gastos = read_data(GASTOS_FILE)
        ventas = read_data(VENTAS_FILE)
        
        # Filtrar datos de la semana (implementación simplificada)
        # Esto asume que las fechas en los datos están en formato "YYYY-MM-DD HH:MM:SS"
        def es_de_esta_semana(fecha_str):
            if not fecha_str:
                return False
            try:
                fecha = datetime.datetime.strptime(fecha_str.split()[0], "%Y-%m-%d")
                return hace_una_semana <= fecha <= hoy
            except:
                return False
        
        compras_semana = [c for c in compras if es_de_esta_semana(c.get("fecha", ""))]
        procesos_semana = [p for p in procesos if es_de_esta_semana(p.get("fecha", ""))]
        gastos_semana = [g for g in gastos if es_de_esta_semana(g.get("fecha", ""))]
        ventas_semana = [v for v in ventas if es_de_esta_semana(v.get("fecha", ""))]
        
        logger.info(f"Datos filtrados para reporte semanal: {len(compras_semana)} compras, {len(procesos_semana)} procesos, {len(gastos_semana)} gastos, {len(ventas_semana)} ventas")
        
        # Estadísticas básicas
        total_compras = sum(float(c.get("cantidad", 0)) for c in compras_semana)
        total_ventas = sum(float(v.get("cantidad", 0)) for v in ventas_semana)
        monto_compras = sum(float(c.get("cantidad", 0)) * float(c.get("precio", 0)) for c in compras_semana)
        monto_ventas = sum(float(v.get("total", 0)) for v in ventas_semana)
        monto_gastos = sum(float(g.get("monto", 0)) for g in gastos_semana)
        
        # Calcular utilidad
        utilidad = monto_ventas - monto_compras - monto_gastos
        
        # Generar mensaje de reporte
        mensaje = f"🗓️ *REPORTE SEMANAL ({fecha_inicio} al {fecha_fin})*\n\n"
        
        mensaje += "*Operaciones de la semana:*\n"
        mensaje += f"- Compras realizadas: {len(compras_semana)}\n"
        mensaje += f"- Procesos realizados: {len(procesos_semana)}\n"
        mensaje += f"- Gastos realizados: {len(gastos_semana)}\n"
        mensaje += f"- Ventas realizadas: {len(ventas_semana)}\n\n"
        
        mensaje += "*Café:*\n"
        mensaje += f"- Café comprado: {total_compras} kg\n"
        mensaje += f"- Café vendido: {total_ventas} kg\n\n"
        
        mensaje += "*Financiero:*\n"
        mensaje += f"- Gastos: {monto_gastos}\n"
        mensaje += f"- Ingresos: {monto_ventas}\n"
        mensaje += f"- *Utilidad semanal: {utilidad}*\n"
        
        return mensaje
    except Exception as e:
        logger.error(f"Error al generar el reporte semanal: {e}")
        return f"Error al generar el reporte semanal: {str(e)}"

async def generar_reporte_mensual() -> str:
    """Genera un reporte de las operaciones del último mes"""
    try:
        logger.info("Generando reporte mensual")
        
        # Obtener fechas
        hoy = datetime.datetime.now()
        hace_un_mes = hoy - datetime.timedelta(days=30)  # Aproximación simple
        fecha_inicio = hace_un_mes.strftime("%Y-%m-%d")
        fecha_fin = hoy.strftime("%Y-%m-%d")
        
        # Leer datos
        compras = read_data(COMPRAS_FILE)
        procesos = read_data(PROCESO_FILE)
        gastos = read_data(GASTOS_FILE)
        ventas = read_data(VENTAS_FILE)
        
        # Filtrar datos del mes (implementación simplificada)
        def es_de_este_mes(fecha_str):
            if not fecha_str:
                return False
            try:
                fecha = datetime.datetime.strptime(fecha_str.split()[0], "%Y-%m-%d")
                return hace_un_mes <= fecha <= hoy
            except:
                return False
        
        compras_mes = [c for c in compras if es_de_este_mes(c.get("fecha", ""))]
        procesos_mes = [p for p in procesos if es_de_este_mes(p.get("fecha", ""))]
        gastos_mes = [g for g in gastos if es_de_este_mes(g.get("fecha", ""))]
        ventas_mes = [v for v in ventas if es_de_este_mes(v.get("fecha", ""))]
        
        logger.info(f"Datos filtrados para reporte mensual: {len(compras_mes)} compras, {len(procesos_mes)} procesos, {len(gastos_mes)} gastos, {len(ventas_mes)} ventas")
        
        # Estadísticas básicas
        total_compras = sum(float(c.get("cantidad", 0)) for c in compras_mes)
        total_ventas = sum(float(v.get("cantidad", 0)) for v in ventas_mes)
        monto_compras = sum(float(c.get("cantidad", 0)) * float(c.get("precio", 0)) for c in compras_mes)
        monto_ventas = sum(float(v.get("total", 0)) for v in ventas_mes)
        monto_gastos = sum(float(g.get("monto", 0)) for g in gastos_mes)
        
        # Calcular utilidad
        utilidad = monto_ventas - monto_compras - monto_gastos
        
        # Generar mensaje de reporte
        mensaje = f"📅 *REPORTE MENSUAL ({fecha_inicio} al {fecha_fin})*\n\n"
        
        mensaje += "*Operaciones del mes:*\n"
        mensaje += f"- Compras realizadas: {len(compras_mes)}\n"
        mensaje += f"- Procesos realizados: {len(procesos_mes)}\n"
        mensaje += f"- Gastos realizados: {len(gastos_mes)}\n"
        mensaje += f"- Ventas realizadas: {len(ventas_mes)}\n\n"
        
        mensaje += "*Café:*\n"
        mensaje += f"- Café comprado: {total_compras} kg\n"
        mensaje += f"- Café vendido: {total_ventas} kg\n\n"
        
        mensaje += "*Financiero:*\n"
        mensaje += f"- Gastos totales: {monto_gastos}\n"
        mensaje += f"- Ingresos totales: {monto_ventas}\n"
        mensaje += f"- *Utilidad mensual: {utilidad}*\n"
        
        return mensaje
    except Exception as e:
        logger.error(f"Error al generar el reporte mensual: {e}")
        return f"Error al generar el reporte mensual: {str(e)}"

def register_reportes_handlers(application):
    """Registra los handlers para el módulo de reportes"""
    application.add_handler(CommandHandler("reporte", reporte_command))
    application.add_handler(CallbackQueryHandler(reporte_callback, pattern="^reporte_"))
    logger.info("Handlers de reportes registrados")