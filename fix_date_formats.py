#!/usr/bin/env python
"""
Script para corregir el formato de fechas en todas las hojas de Google Sheets.
Este script debe ejecutarse una sola vez para corregir los datos existentes.
"""

import os
import sys
import logging
from dotenv import load_dotenv
import time

# Configurar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Agregar el directorio actual al path para importar módulos locales
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar funciones necesarias
from utils.sheets import get_all_data, update_cell, HEADERS
from utils.helpers import format_date_for_sheets

def fix_date_formats():
    """Corregir el formato de fechas en todas las hojas"""
    sheets_with_dates = ['compras', 'proceso', 'gastos', 'ventas', 'adelantos']
    
    for sheet_name in sheets_with_dates:
        if sheet_name not in HEADERS:
            logger.warning(f"Hoja '{sheet_name}' no encontrada en la configuración")
            continue
        
        logger.info(f"Procesando hoja '{sheet_name}'...")
        
        try:
            # Obtener todos los datos
            data = get_all_data(sheet_name)
            
            if not data:
                logger.info(f"No hay datos en la hoja '{sheet_name}'")
                continue
            
            # Identificar columnas de fecha
            date_columns = []
            for column in HEADERS[sheet_name]:
                if 'fecha' in column.lower():
                    date_columns.append(column)
            
            if not date_columns:
                logger.info(f"No se encontraron columnas de fecha en '{sheet_name}'")
                continue
            
            # Procesar cada fila
            fixed_count = 0
            for row in data:
                row_index = row.get('_row_index')
                if row_index is None:
                    continue
                
                # Procesar cada columna de fecha
                for date_column in date_columns:
                    date_value = row.get(date_column)
                    if not date_value:
                        continue
                    
                    # Si no tiene el formato correcto (prefijo de comilla simple)
                    if not str(date_value).startswith("'"):
                        # Formatear correctamente
                        formatted_date = format_date_for_sheets(date_value)
                        
                        # Actualizar celda
                        success = update_cell(sheet_name, row_index, date_column, formatted_date)
                        if success:
                            fixed_count += 1
                            logger.info(f"Corregido formato de {date_column} en fila {row_index}: {date_value} -> {formatted_date}")
                        
                        # Pequeña pausa para evitar sobrecargar la API
                        time.sleep(0.1)
            
            logger.info(f"Proceso completado para '{sheet_name}'. Se corrigieron {fixed_count} fechas.")
            
        except Exception as e:
            logger.error(f"Error al procesar la hoja '{sheet_name}': {e}")
    
    logger.info("Proceso de corrección de fechas completado para todas las hojas.")

if __name__ == "__main__":
    logger.info("Iniciando corrección de formatos de fecha...")
    fix_date_formats()
