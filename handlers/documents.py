                # Descargar el archivo a memoria
                logger.debug("Descargando archivo a memoria")
                file_bytes = await file.download_as_bytearray()
                logger.debug("Archivo descargado, tamaño: %s bytes", len(file_bytes))
                
                # Determinar la carpeta donde guardar el archivo según tipo de operación
                if tipo_op.upper() == "COMPRA":
                    folder_id = DRIVE_EVIDENCIAS_COMPRAS_ID
                    logger.info(f"Guardando evidencia de COMPRA en carpeta ID: {folder_id}")
                else:  # VENTA
                    folder_id = DRIVE_EVIDENCIAS_VENTAS_ID
                    logger.info(f"Guardando evidencia de VENTA en carpeta ID: {folder_id}")
                
                # Subir el archivo a Drive
                logger.info("Subiendo archivo a Drive: %s", nombre_archivo)