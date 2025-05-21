"""
Módulo para generar reportes detallados y exportar a Excel.
Permite visualizar totales diarios de compras, ventas, pagos y cálculo de ganancias.
"""
import logging
import datetime
import pandas as pd
import os
from typing import Dict, List, Any, Optional, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from config import COMPRAS_FILE, PROCESO_FILE, GASTOS_FILE, VENTAS_FILE
from utils.db import read_data, save_data
from utils.sheets.utils import format_date_for_sheets, get_current_datetime_str, safe_float
from utils.sheets.core import get_all_data, get_filtered_data

# Configurar logging
logger = logging.getLogger(__name__)

# Estados para el conversation handler
SELECCION_FECHAS = 0
FECHA_INICIO = 1
FECHA_FIN = 2

# Opciones de reportes detallados
REPORTE_DIARIO_DETALLADO = "diario_detallado"
REPORTE_RANGO_FECHAS = "rango_fechas"
EXPORTAR_EXCEL = "exportar_excel"

async def reportes_detallados_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra opciones de reportes detallados disponibles"""
    logger.info(f"Usuario {update.effective_user.id} inició comando /reportes_detallados")
    
    keyboard = [
        [
            InlineKeyboardButton("📊 Reporte Diario Detallado", callback_data=f"reporte_{REPORTE_DIARIO_DETALLADO}")
        ],
        [
            InlineKeyboardButton("📆 Reporte por Rango de Fechas", callback_data=f"reporte_{REPORTE_RANGO_FECHAS}")
        ],
        [
            InlineKeyboardButton("📥 Exportar a Excel", callback_data=f"reporte_{EXPORTAR_EXCEL}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Selecciona el tipo de reporte detallado que deseas generar:",
        reply_markup=reply_markup
    )

async def reportes_detallados_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    """Maneja los callbacks de los botones de reportes detallados"""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    # Obtener el tipo de reporte de callback_data
    tipo_reporte = query.data.split("_")[1]
    logger.info(f"Usuario {user_id} solicitó reporte detallado de tipo: {tipo_reporte}")
    
    if tipo_reporte == REPORTE_DIARIO_DETALLADO:
        # Generar reporte diario detallado para la fecha actual
        hoy = datetime.datetime.now().strftime("%Y-%m-%d")
        mensaje = await generar_reporte_diario_detallado(hoy)
        await query.edit_message_text(text=mensaje, parse_mode="Markdown")
        return ConversationHandler.END
    
    elif tipo_reporte == REPORTE_RANGO_FECHAS:
        # Solicitar fecha de inicio
        await query.edit_message_text(
            text="Ingresa la fecha de inicio del reporte (formato YYYY-MM-DD):",
            parse_mode="Markdown"
        )
        return FECHA_INICIO
    
    elif tipo_reporte == EXPORTAR_EXCEL:
        # Generar y enviar archivo Excel
        archivo_excel = await generar_excel_reportes()
        if archivo_excel:
            # Informar que el reporte se está generando
            await query.edit_message_text(
                text="Generando reporte en Excel. En breve estará disponible para descarga.",
                parse_mode="Markdown"
            )
            
            # Enviar el archivo
            try:
                with open(archivo_excel, 'rb') as file:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=file,
                        filename="reporte_cafe.xlsx",
                        caption="Reporte detallado en formato Excel"
                    )
                # Eliminar el archivo temporal
                os.remove(archivo_excel)
                logger.info(f"Archivo Excel enviado y eliminado: {archivo_excel}")
            except Exception as e:
                logger.error(f"Error al enviar archivo Excel: {e}")
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Error al enviar el archivo: {str(e)}"
                )
        else:
            await query.edit_message_text(
                text="No se pudo generar el reporte en Excel. Inténtalo de nuevo más tarde.",
                parse_mode="Markdown"
            )
        return ConversationHandler.END
    
    return ConversationHandler.END

async def fecha_inicio_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la entrada de la fecha de inicio"""
    fecha_inicio = update.message.text.strip()
    
    # Validar formato de fecha
    try:
        datetime.datetime.strptime(fecha_inicio, "%Y-%m-%d")
        context.user_data['fecha_inicio'] = fecha_inicio
        
        # Solicitar fecha de fin
        await update.message.reply_text(
            "Ingresa la fecha de fin del reporte (formato YYYY-MM-DD):",
            parse_mode="Markdown"
        )
        return FECHA_FIN
    except ValueError:
        await update.message.reply_text(
            "⚠️ Formato de fecha incorrecto. Por favor, ingresa la fecha en formato YYYY-MM-DD (ejemplo: 2025-05-21):",
            parse_mode="Markdown"
        )
        return FECHA_INICIO

async def fecha_fin_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la entrada de la fecha de fin y genera el reporte"""
    fecha_fin = update.message.text.strip()
    fecha_inicio = context.user_data.get('fecha_inicio')
    
    # Validar formato de fecha
    try:
        datetime.datetime.strptime(fecha_fin, "%Y-%m-%d")
        
        # Generar reporte para el rango de fechas
        mensaje = await generar_reporte_rango_fechas(fecha_inicio, fecha_fin)
        await update.message.reply_text(
            text=mensaje,
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(
            "⚠️ Formato de fecha incorrecto. Por favor, ingresa la fecha en formato YYYY-MM-DD (ejemplo: 2025-05-21):",
            parse_mode="Markdown"
        )
        return FECHA_FIN

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la conversación."""
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END

async def generar_reporte_diario_detallado(fecha: str) -> str:
    """
    Genera un reporte detallado de un día específico con todos los totales requeridos.
    
    Args:
        fecha (str): Fecha para el reporte en formato YYYY-MM-DD
        
    Returns:
        str: Mensaje formateado con el reporte
    """
    try:
        logger.info(f"Generando reporte diario detallado para la fecha: {fecha}")
        
        # Obtener todos los datos
        compras = get_all_data("compras")
        ventas = get_all_data("ventas")
        gastos = get_all_data("gastos")
        procesos = get_all_data("proceso")
        
        # Filtrar datos por la fecha especificada
        compras_dia = [c for c in compras if c.get("fecha", "").startswith(fecha)]
        ventas_dia = [v for v in ventas if v.get("fecha", "").startswith(fecha)]
        gastos_dia = [g for g in gastos if g.get("fecha", "").startswith(fecha)]
        procesos_dia = [p for p in procesos if p.get("fecha", "").startswith(fecha)]
        
        # 1. Total de kg de café comprados por día
        total_kg_comprados = sum(safe_float(c.get("cantidad", 0)) for c in compras_dia)
        
        # 2. Total de gastos por día
        total_gastos = sum(safe_float(g.get("monto", 0)) for g in gastos_dia)
        
        # 3. Método de pago análisis (efectivo vs transferencia)
        # Asumiendo que los gastos tienen un campo para método de pago, si no, hay que adaptar
        gastos_efectivo = [g for g in gastos_dia if g.get("descripcion", "").upper().find("EFECTIVO") >= 0]
        gastos_transferencia = [g for g in gastos_dia if g.get("descripcion", "").upper().find("TRANSFERENCIA") >= 0]
        
        total_efectivo = sum(safe_float(g.get("monto", 0)) for g in gastos_efectivo)
        total_transferencia = sum(safe_float(g.get("monto", 0)) for g in gastos_transferencia)
        
        # 4. Total de ingresos por día
        total_ingresos = sum(safe_float(v.get("total", 0)) for v in ventas_dia)
        
        # 5. Ganancia del día (ingresos - gastos)
        ganancia_dia = total_ingresos - total_gastos
        
        # Generar el reporte formateado
        mensaje = f"📊 *REPORTE DIARIO DETALLADO ({fecha})*\n\n"
        
        # Sección de Operaciones
        mensaje += "*OPERACIONES:*\n"
        mensaje += f"• Compras registradas: {len(compras_dia)}\n"
        mensaje += f"• Ventas realizadas: {len(ventas_dia)}\n"
        mensaje += f"• Gastos registrados: {len(gastos_dia)}\n"
        mensaje += f"• Procesos ejecutados: {len(procesos_dia)}\n\n"
        
        # Sección de Inventario
        mensaje += "*INVENTARIO:*\n"
        mensaje += f"• Café comprado: {total_kg_comprados:.2f} kg\n"
        
        # Desglose por tipo de café si hay compras
        if compras_dia:
            tipos_cafe = {}
            for c in compras_dia:
                tipo = c.get("tipo_cafe", "No especificado")
                cantidad = safe_float(c.get("cantidad", 0))
                tipos_cafe[tipo] = tipos_cafe.get(tipo, 0) + cantidad
            
            mensaje += "*Desglose por tipo:*\n"
            for tipo, cantidad in tipos_cafe.items():
                mensaje += f"  - {tipo}: {cantidad:.2f} kg\n"
        
        # Sección Financiera
        mensaje += "\n*FINANCIERO:*\n"
        mensaje += f"• Gastos totales: S/. {total_gastos:.2f}\n"
        mensaje += f"• Ingresos totales: S/. {total_ingresos:.2f}\n"
        mensaje += f"• *Ganancia del día: S/. {ganancia_dia:.2f}*\n\n"
        
        # Sección de Métodos de Pago
        mensaje += "*MÉTODOS DE PAGO:*\n"
        mensaje += f"• Pagos en efectivo: S/. {total_efectivo:.2f}\n"
        mensaje += f"• Pagos por transferencia: S/. {total_transferencia:.2f}\n"
        
        # Si hay una discrepancia en el total, mostrarla
        diff = total_gastos - (total_efectivo + total_transferencia)
        if abs(diff) > 0.01:  # Considerar pequeñas diferencias por redondeo
            mensaje += f"• Sin método especificado: S/. {diff:.2f}\n"
        
        return mensaje
    except Exception as e:
        logger.error(f"Error al generar reporte diario detallado: {e}")
        return f"Error al generar el reporte diario detallado: {str(e)}"

async def generar_reporte_rango_fechas(fecha_inicio: str, fecha_fin: str) -> str:
    """
    Genera un reporte detallado para un rango de fechas.
    
    Args:
        fecha_inicio (str): Fecha de inicio en formato YYYY-MM-DD
        fecha_fin (str): Fecha de fin en formato YYYY-MM-DD
        
    Returns:
        str: Mensaje formateado con el reporte
    """
    try:
        logger.info(f"Generando reporte para el rango: {fecha_inicio} al {fecha_fin}")
        
        # Convertir fechas a objetos datetime para comparación
        fecha_inicio_dt = datetime.datetime.strptime(fecha_inicio, "%Y-%m-%d")
        fecha_fin_dt = datetime.datetime.strptime(fecha_fin, "%Y-%m-%d")
        
        # Obtener todos los datos
        compras = get_all_data("compras")
        ventas = get_all_data("ventas")
        gastos = get_all_data("gastos")
        procesos = get_all_data("proceso")
        
        # Filtrar datos por rango de fechas
        def en_rango_fechas(fecha_str):
            if not fecha_str:
                return False
            try:
                fecha_dt = datetime.datetime.strptime(fecha_str.split()[0], "%Y-%m-%d")
                return fecha_inicio_dt <= fecha_dt <= fecha_fin_dt
            except:
                return False
        
        compras_rango = [c for c in compras if en_rango_fechas(c.get("fecha", ""))]
        ventas_rango = [v for v in ventas if en_rango_fechas(v.get("fecha", ""))]
        gastos_rango = [g for g in gastos if en_rango_fechas(g.get("fecha", ""))]
        procesos_rango = [p for p in procesos if en_rango_fechas(p.get("fecha", ""))]
        
        # Calcular totales
        total_kg_comprados = sum(safe_float(c.get("cantidad", 0)) for c in compras_rango)
        total_gastos = sum(safe_float(g.get("monto", 0)) for g in gastos_rango)
        
        # Análisis método de pago
        gastos_efectivo = [g for g in gastos_rango if g.get("descripcion", "").upper().find("EFECTIVO") >= 0]
        gastos_transferencia = [g for g in gastos_rango if g.get("descripcion", "").upper().find("TRANSFERENCIA") >= 0]
        
        total_efectivo = sum(safe_float(g.get("monto", 0)) for g in gastos_efectivo)
        total_transferencia = sum(safe_float(g.get("monto", 0)) for g in gastos_transferencia)
        
        # Ingresos y ganancias
        total_ingresos = sum(safe_float(v.get("total", 0)) for v in ventas_rango)
        ganancia_periodo = total_ingresos - total_gastos
        
        # Análisis por día para mostrar tendencias
        dias = (fecha_fin_dt - fecha_inicio_dt).days + 1
        
        # Generar el reporte formateado
        mensaje = f"📊 *REPORTE DE PERIODO ({fecha_inicio} al {fecha_fin})*\n\n"
        
        # Resumen del periodo
        mensaje += "*RESUMEN DEL PERIODO:*\n"
        mensaje += f"• Días analizados: {dias}\n"
        mensaje += f"• Compras registradas: {len(compras_rango)}\n"
        mensaje += f"• Ventas realizadas: {len(ventas_rango)}\n"
        mensaje += f"• Gastos registrados: {len(gastos_rango)}\n"
        mensaje += f"• Procesos ejecutados: {len(procesos_rango)}\n\n"
        
        # Inventario del periodo
        mensaje += "*INVENTARIO:*\n"
        mensaje += f"• Café comprado en el periodo: {total_kg_comprados:.2f} kg\n"
        mensaje += f"• Promedio diario de compra: {(total_kg_comprados/dias):.2f} kg/día\n"
        
        # Desglose por tipo de café si hay compras
        if compras_rango:
            tipos_cafe = {}
            for c in compras_rango:
                tipo = c.get("tipo_cafe", "No especificado")
                cantidad = safe_float(c.get("cantidad", 0))
                tipos_cafe[tipo] = tipos_cafe.get(tipo, 0) + cantidad
            
            mensaje += "*Desglose por tipo:*\n"
            for tipo, cantidad in tipos_cafe.items():
                mensaje += f"  - {tipo}: {cantidad:.2f} kg\n"
        
        # Financiero del periodo
        mensaje += "\n*FINANCIERO:*\n"
        mensaje += f"• Gastos totales: S/. {total_gastos:.2f}\n"
        mensaje += f"• Ingresos totales: S/. {total_ingresos:.2f}\n"
        mensaje += f"• *Ganancia del periodo: S/. {ganancia_periodo:.2f}*\n"
        mensaje += f"• Promedio diario de gastos: S/. {(total_gastos/dias):.2f}/día\n"
        mensaje += f"• Promedio diario de ingresos: S/. {(total_ingresos/dias):.2f}/día\n"
        mensaje += f"• Promedio diario de ganancia: S/. {(ganancia_periodo/dias):.2f}/día\n\n"
        
        # Métodos de pago
        mensaje += "*MÉTODOS DE PAGO:*\n"
        mensaje += f"• Pagos en efectivo: S/. {total_efectivo:.2f} ({(total_efectivo/total_gastos*100):.1f}%)\n"
        mensaje += f"• Pagos por transferencia: S/. {total_transferencia:.2f} ({(total_transferencia/total_gastos*100):.1f}%)\n"
        
        # Si hay una discrepancia en el total, mostrarla
        diff = total_gastos - (total_efectivo + total_transferencia)
        if abs(diff) > 0.01:  # Considerar pequeñas diferencias por redondeo
            mensaje += f"• Sin método especificado: S/. {diff:.2f} ({(diff/total_gastos*100):.1f}%)\n"
        
        return mensaje
    except Exception as e:
        logger.error(f"Error al generar reporte de rango de fechas: {e}")
        return f"Error al generar el reporte: {str(e)}"

async def generar_excel_reportes() -> Optional[str]:
    """
    Genera un archivo Excel con reportes detallados.
    
    Returns:
        Optional[str]: Ruta al archivo Excel generado, o None si hay error
    """
    try:
        logger.info("Generando archivo Excel con reportes detallados")
        
        # Obtener datos de todas las colecciones
        compras = get_all_data("compras")
        ventas = get_all_data("ventas")
        gastos = get_all_data("gastos")
        procesos = get_all_data("proceso")
        
        # Crear un escritor de Excel
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_path = f"reporte_cafe_{timestamp}.xlsx"
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # Convertir a DataFrames
            df_compras = pd.DataFrame(compras)
            df_ventas = pd.DataFrame(ventas)
            df_gastos = pd.DataFrame(gastos)
            df_procesos = pd.DataFrame(procesos)
            
            # Guardar datos originales
            df_compras.to_excel(writer, sheet_name="Datos_Compras", index=False)
            df_ventas.to_excel(writer, sheet_name="Datos_Ventas", index=False)
            df_gastos.to_excel(writer, sheet_name="Datos_Gastos", index=False)
            df_procesos.to_excel(writer, sheet_name="Datos_Procesos", index=False)
            
            # Crear un DataFrame para el reporte diario
            # Primero, obtener todas las fechas únicas
            todas_fechas = set()
            for df in [df_compras, df_ventas, df_gastos]:
                if 'fecha' in df.columns:
                    fechas = df['fecha'].dropna().apply(lambda x: x.split()[0] if ' ' in x else x)
                    todas_fechas.update(fechas)
            
            todas_fechas = sorted(list(todas_fechas))
            
            # Preparar datos para el reporte diario
            reporte_diario = []
            for fecha in todas_fechas:
                # Filtrar datos por fecha
                compras_dia = df_compras[df_compras['fecha'].str.startswith(fecha, na=False)] if 'fecha' in df_compras.columns else pd.DataFrame()
                ventas_dia = df_ventas[df_ventas['fecha'].str.startswith(fecha, na=False)] if 'fecha' in df_ventas.columns else pd.DataFrame()
                gastos_dia = df_gastos[df_gastos['fecha'].str.startswith(fecha, na=False)] if 'fecha' in df_gastos.columns else pd.DataFrame()
                
                # Calcular totales
                kg_comprados = compras_dia['cantidad'].astype(float).sum() if 'cantidad' in compras_dia.columns else 0
                ingresos = ventas_dia['total'].astype(float).sum() if 'total' in ventas_dia.columns else 0
                gastos = gastos_dia['monto'].astype(float).sum() if 'monto' in gastos_dia.columns else 0
                
                # Analizar método de pago (usando descripción como aproximación)
                if 'descripcion' in gastos_dia.columns:
                    efectivo = gastos_dia[gastos_dia['descripcion'].str.upper().str.contains('EFECTIVO', na=False)]['monto'].astype(float).sum()
                    transferencia = gastos_dia[gastos_dia['descripcion'].str.upper().str.contains('TRANSFERENCIA', na=False)]['monto'].astype(float).sum()
                else:
                    efectivo = 0
                    transferencia = 0
                
                # Calcular ganancia
                ganancia = ingresos - gastos
                
                # Agregar fila al reporte
                reporte_diario.append({
                    'Fecha': fecha,
                    'Kg_Comprados': kg_comprados,
                    'Gastos_Totales': gastos,
                    'Pagos_Efectivo': efectivo,
                    'Pagos_Transferencia': transferencia,
                    'Ingresos': ingresos,
                    'Ganancia': ganancia
                })
            
            # Convertir a DataFrame y guardar
            df_reporte_diario = pd.DataFrame(reporte_diario)
            df_reporte_diario.to_excel(writer, sheet_name="Reporte_Diario", index=False)
            
            # Crear hoja de resumen de tipos de café
            if 'tipo_cafe' in df_compras.columns:
                # Agrupar por tipo de café
                tipos_cafe = df_compras.groupby('tipo_cafe')['cantidad'].astype(float).sum().reset_index()
                tipos_cafe.columns = ['Tipo de Café', 'Cantidad Total (kg)']
                tipos_cafe.to_excel(writer, sheet_name="Resumen_Tipos_Cafe", index=False)
            
            # Crear hoja de análisis de métodos de pago
            if 'descripcion' in df_gastos.columns:
                # Inicializar diccionario para almacenar categorías de métodos de pago
                categorias_metodos = {
                    'EFECTIVO': [],
                    'TRANSFERENCIA': [],
                    'OTROS': []
                }
                
                # Categorizar gastos por método de pago
                for _, gasto in df_gastos.iterrows():
                    descripcion = str(gasto.get('descripcion', '')).upper()
                    if 'EFECTIVO' in descripcion:
                        categorias_metodos['EFECTIVO'].append(gasto)
                    elif 'TRANSFERENCIA' in descripcion:
                        categorias_metodos['TRANSFERENCIA'].append(gasto)
                    else:
                        categorias_metodos['OTROS'].append(gasto)
                
                # Crear DataFrame de resumen
                metodos_pago = []
                for metodo, gastos_lista in categorias_metodos.items():
                    if gastos_lista:
                        # Convertir lista de dict a DataFrame
                        df_temp = pd.DataFrame(gastos_lista)
                        total = df_temp['monto'].astype(float).sum() if 'monto' in df_temp.columns else 0
                        metodos_pago.append({
                            'Método de Pago': metodo,
                            'Total (S/.)': total,
                            'Cantidad de Operaciones': len(gastos_lista)
                        })
                
                df_metodos_pago = pd.DataFrame(metodos_pago)
                df_metodos_pago.to_excel(writer, sheet_name="Análisis_Métodos_Pago", index=False)
            
            # Actualizar el archivo
            writer.close()
        
        logger.info(f"Archivo Excel generado: {excel_path}")
        return excel_path
    except Exception as e:
        logger.error(f"Error al generar archivo Excel: {e}")
        return None

def register_reportes_detallados_handlers(application):
    """Registra los handlers para el módulo de reportes detallados"""
    # Handler para el comando
    application.add_handler(CommandHandler("reportes_detallados", reportes_detallados_command))
    
    # Handler para los callbacks iniciales
    application.add_handler(CallbackQueryHandler(reportes_detallados_callback, pattern="^reporte_"))
    
    # Conversation handler para el ingreso de fechas
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(reportes_detallados_callback, pattern=f"^reporte_{REPORTE_RANGO_FECHAS}$")],
        states={
            FECHA_INICIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, fecha_inicio_input)],
            FECHA_FIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, fecha_fin_input)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    application.add_handler(conv_handler)
    
    logger.info("Handlers de reportes detallados registrados")
