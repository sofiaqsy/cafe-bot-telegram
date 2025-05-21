"""
Módulo para formateo de números y valores consistentes en todo el sistema.
"""

def formatear_numero(numero):
    """
    Formatea un número usando coma como separador decimal y punto como separador de miles.
    
    Args:
        numero: Valor numérico o cadena a formatear
        
    Returns:
        str: Número formateado con el formato estándar (ej: 1.234,56)
    """
    # Convertir a string si es necesario
    if isinstance(numero, (int, float)):
        # Convertir a string con 2 decimales si es float
        if isinstance(numero, float):
            numero_str = f"{numero:.2f}"
        else:
            numero_str = str(numero)
    else:
        numero_str = str(numero)
    
    # Separar parte entera y decimal
    partes = numero_str.split('.')
    parte_entera = partes[0]
    
    # Añadir separador de miles (cada 3 dígitos)
    if len(parte_entera) > 3:
        # Formato de miles con puntos
        chars = list(parte_entera)
        for i in range(len(parte_entera) - 3, 0, -3):
            chars.insert(i, '.')
        parte_entera = ''.join(chars)
    
    # Volver a juntar con coma como separador decimal
    if len(partes) > 1:
        return f"{parte_entera},{partes[1]}"
    else:
        return parte_entera

def procesar_entrada_numerica(entrada):
    """
    Convierte una entrada de usuario (que puede usar punto o coma) a un valor numérico 
    para operaciones internas.
    
    Args:
        entrada (str): Entrada de usuario que puede contener comas o puntos
        
    Returns:
        float: Valor numérico para operaciones
        
    Raises:
        ValueError: Si la entrada no puede convertirse a un número válido
    """
    if not entrada or not isinstance(entrada, str):
        raise ValueError(f"Entrada inválida: {entrada}")
    
    # Eliminar espacios
    entrada = entrada.strip()
    
    try:
        # Si hay coma decimal, convertir a punto para procesamiento interno
        if ',' in entrada:
            # Primero eliminar puntos de miles si existen
            entrada_limpia = entrada.replace('.', '')
            # Luego reemplazar coma por punto para convertir a float
            entrada_limpia = entrada_limpia.replace(',', '.')
            return float(entrada_limpia)
        else:
            # Si usa punto decimal o no tiene decimal
            return float(entrada)
    except ValueError:
        raise ValueError(f"El valor '{entrada}' no es un número válido")

def formatear_precio(precio):
    """
    Formatea un precio específicamente para mostrar S/ y dos decimales.
    
    Args:
        precio: Valor numérico del precio
        
    Returns:
        str: Precio formateado (ej: S/ 1.234,56)
    """
    return f"S/ {formatear_numero(precio)}"
