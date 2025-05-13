#!/usr/bin/env python3
"""
Script para exportar datos de Excel a CSV
"""

import os
import pandas as pd
import sys
import argparse
import logging

# Configurar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def export_excel_to_csv(excel_path, csv_dir):
    """
    Exporta datos de Excel a archivos CSV
    
    Args:
        excel_path (str): Ruta al archivo Excel
        csv_dir (str): Directorio para guardar archivos CSV
    """
    logger.info(f"Exportando datos de {excel_path} a {csv_dir}...")
    
    # Definir mapeo de hojas de Excel a archivos CSV
    sheet_to_csv = {
        'Compras': 'compras.csv',
        'Proceso': 'proceso.csv',
        'Gastos': 'gastos.csv',
        'Ventas': 'ventas.csv',
        'Adelantos': 'adelantos.csv',
        'Pedidos': 'pedidos.csv',
        'PedidosWhatsApp': 'pedidos_whatsapp.csv'
    }
    
    # Verificar si el archivo Excel existe
    if not os.path.exists(excel_path):
        logger.error(f"El archivo {excel_path} no existe.")
        return False
    
    # Crear directorio si no existe
    if not os.path.exists(csv_dir):
        os.makedirs(csv_dir)
    
    # Leer hojas de Excel
    try:
        xl = pd.ExcelFile(excel_path)
        available_sheets = xl.sheet_names
    except Exception as e:
        logger.error(f"❌ Error al abrir archivo Excel: {e}")
        return False
    
    # Exportar cada hoja
    any_exported = False
    for sheet_name, csv_file in sheet_to_csv.items():
        if sheet_name in available_sheets:
            try:
                # Leer hoja
                df = pd.read_excel(excel_path, sheet_name=sheet_name)
                
                # Guardar como CSV
                csv_path = os.path.join(csv_dir, csv_file)
                df.to_csv(csv_path, index=False)
                
                logger.info(f"✅ Exportada hoja {sheet_name} a {csv_file}")
                any_exported = True
            except Exception as e:
                logger.error(f"❌ Error al exportar hoja {sheet_name}: {e}")
        else:
            logger.warning(f"⚠️ Hoja {sheet_name} no encontrada en el Excel. Omitiendo.")
    
    if any_exported:
        logger.info(f"✅ Datos exportados exitosamente a {csv_dir}")
        return True
    else:
        logger.warning("⚠️ No se encontraron hojas para exportar.")
        return False

def main():
    """
    Función principal
    """
    # Analizar argumentos
    parser = argparse.ArgumentParser(description='Exportar datos de Excel a CSV')
    parser.add_argument('--excel-path', default='proceso_cafe.xlsx', help='Ruta al archivo Excel')
    parser.add_argument('--csv-dir', default='data', help='Directorio para guardar archivos CSV')
    
    args = parser.parse_args()
    
    # Exportar datos
    success = export_excel_to_csv(args.excel_path, args.csv_dir)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())