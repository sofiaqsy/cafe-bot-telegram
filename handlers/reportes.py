from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
import datetime
from config import COMPRAS_FILE, PROCESO_FILE, GASTOS_FILE, VENTAS_FILE
from utils.db import read_data

# Tipos de reportes
GENERAL = "general"
DIARIO = "diario"
SEMANAL = "semanal"
MENSUAL = "mensual"

async def reporte_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra opciones de reportes disponibles"""
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
    await query.answer()
    
    # Obtener el tipo de reporte de callback_data
    tipo_reporte = query.data.split("_")[1]
    
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
    
    await query.edit_message_text(
        text=mensaje,
        parse_mode="Markdown"
    )

async def generar_reporte_general() -> str:
    """Genera un reporte general con todas las operaciones"""
    try:
        # Leer datos
        compras = read_data(COMPRAS_FILE)
        procesos = read_data(PROCESO_FILE)
        gastos = read_data(GASTOS_FILE)
        ventas = read_data(VENTAS_FILE)
        
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
        return f"Error al generar el reporte general: {str(e)}"

async def generar_reporte_diario() -> str:
    """Genera un reporte de las operaciones del día actual"""
    try:
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
        return f"Error al generar el reporte diario: {str(e)}"

async def generar_reporte_semanal() -> str:
    """Genera un reporte de las operaciones de la última semana"""
    try:
        # Obtener fechas
        hoy = datetime.datetime.now()
        hace_una_semana = hoy - datetime.timedelta(days=7)
        
        # Leer datos
        compras = read_data(COMPRAS_FILE)
        procesos = read_data(PROCESO_FILE)
        gastos = read_data(GASTOS_FILE)
        ventas = read_data(VENTAS_FILE)
        
        # Filtrar datos
        # Nota: Esta implementación es simplista y asume que tenemos un campo 'fecha'
        # En una implementación real deberíamos convertir las fechas a objetos datetime
        compras_semana = []  # Aquí filtrarías las compras de la última semana
        procesos_semana = []  # Aquí filtrarías los procesos de la última semana
        gastos_semana = []  # Aquí filtrarías los gastos de la última semana
        ventas_semana = []  # Aquí filtrarías las ventas de la última semana
        
        # Estadísticas básicas
        total_compras = sum(float(c.get("cantidad", 0)) for c in compras_semana)
        total_ventas = sum(float(v.get("cantidad", 0)) for v in ventas_semana)
        monto_compras = sum(float(c.get("cantidad", 0)) * float(c.get("precio", 0)) for c in compras_semana)
        monto_ventas = sum(float(v.get("total", 0)) for v in ventas_semana)
        monto_gastos = sum(float(g.get("monto", 0)) for g in gastos_semana)
        
        # Calcular utilidad
        utilidad = monto_ventas - monto_compras - monto_gastos
        
        # Generar mensaje de reporte
        fecha_inicio = hace_una_semana.strftime("%Y-%m-%d")
        fecha_fin = hoy.strftime("%Y-%m-%d")
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
        return f"Error al generar el reporte semanal: {str(e)}"

async def generar_reporte_mensual() -> str:
    """Genera un reporte de las operaciones del último mes"""
    try:
        # Obtener fechas
        hoy = datetime.datetime.now()
        hace_un_mes = hoy - datetime.timedelta(days=30)  # Aproximación simple
        
        # Leer datos
        compras = read_data(COMPRAS_FILE)
        procesos = read_data(PROCESO_FILE)
        gastos = read_data(GASTOS_FILE)
        ventas = read_data(VENTAS_FILE)
        
        # Filtrar datos
        # Nota: Esta implementación es simplista y asume que tenemos un campo 'fecha'
        # En una implementación real deberíamos convertir las fechas a objetos datetime
        compras_mes = []  # Aquí filtrarías las compras del último mes
        procesos_mes = []  # Aquí filtrarías los procesos del último mes
        gastos_mes = []  # Aquí filtrarías los gastos del último mes
        ventas_mes = []  # Aquí filtrarías las ventas del último mes
        
        # Estadísticas básicas
        total_compras = sum(float(c.get("cantidad", 0)) for c in compras_mes)
        total_ventas = sum(float(v.get("cantidad", 0)) for v in ventas_mes)
        monto_compras = sum(float(c.get("cantidad", 0)) * float(c.get("precio", 0)) for c in compras_mes)
        monto_ventas = sum(float(v.get("total", 0)) for v in ventas_mes)
        monto_gastos = sum(float(g.get("monto", 0)) for g in gastos_mes)
        
        # Calcular utilidad
        utilidad = monto_ventas - monto_compras - monto_gastos
        
        # Generar mensaje de reporte
        fecha_inicio = hace_un_mes.strftime("%Y-%m-%d")
        fecha_fin = hoy.strftime("%Y-%m-%d")
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
        return f"Error al generar el reporte mensual: {str(e)}"

def register_reportes_handlers(application):
    """Registra los handlers para el módulo de reportes"""
    application.add_handler(CommandHandler("reporte", reporte_command))
    application.add_handler(CallbackQueryHandler(reporte_callback, pattern="^reporte_"))
