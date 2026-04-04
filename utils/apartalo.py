"""
Integration with apartalo-core API for BIZ-006 (Finca Rosal).
- On new PERGAMINO compra  → add stock to PROD-666413 (Pergamino Finca Rosal)
- On daily price snapshot  → update precio of PROD-666413 and PROD-548579 (Verde Finca Rosal)
"""
import logging
import requests

logger = logging.getLogger(__name__)

APARTALO_BASE  = "https://apartalo-core-9d633cdb9e1a.herokuapp.com"
BUSINESS_ID    = "BIZ-006"

# Product codes in apartalo-core
PROD_PERGAMINO = "PROD-666413"   # Pergamino Finca Rosal
PROD_VERDE     = "PROD-548579"   # Verde Finca Rosal  (Oro Verde)
PROD_CEREZO    = "PROD-487793"   # Cerezo Finca Rosal

_HEADERS = {"Content-Type": "application/json"}
_TIMEOUT = 10


def _url(path: str) -> str:
    return f"{APARTALO_BASE}/api/{path}"


def agregar_stock(tipo_cafe: str, cantidad: float, motivo: str = "") -> bool:
    """
    Add kg to the matching product stock in apartalo-core based on tipo_cafe.
    Supports: PERGAMINO → PROD-666413, CEREZO → PROD-487793.
    """
    tipo = tipo_cafe.upper().strip()
    if tipo == "PERGAMINO":
        codigo = PROD_PERGAMINO
    elif tipo == "CEREZO":
        codigo = PROD_CEREZO
    else:
        logger.info(f"[APARTALO] Tipo '{tipo_cafe}' sin producto en apartalo-core — omitiendo.")
        return False
    try:
        payload = {
            "cantidad": int(cantidad),
            "operacion": "agregar",
            "motivo": motivo or f"Compra {tipo} via bot cafe ({cantidad} kg)",
        }
        resp = requests.post(
            _url(f"productos/{BUSINESS_ID}/{codigo}/stock"),
            json=payload,
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        data = resp.json()
        if resp.status_code == 200 and data.get("success"):
            logger.info(
                f"[APARTALO] Stock {tipo} ({codigo}) actualizado: "
                f"{data.get('stockAnterior')} → {data.get('stockNuevo')} kg"
            )
            return True
        else:
            logger.warning(f"[APARTALO] Stock {tipo} no actualizado: {data}")
            return False
    except Exception as e:
        logger.error(f"[APARTALO] Error actualizando stock {tipo}: {e}")
        return False


# Keep old name as alias so existing callers don't break
def agregar_stock_pergamino(cantidad: float, motivo: str = "") -> bool:
    return agregar_stock("PERGAMINO", cantidad, motivo)


def actualizar_precios(precio_pergamino: float, precio_oro_verde: float, precio_cerezo: float = 0) -> bool:
    """
    Update prices of Pergamino, Cerezo and Verde Finca Rosal in apartalo-core.
    Called daily by the price scheduler in web.py.
    """
    ok_perg  = _update_precio(PROD_PERGAMINO, precio_pergamino, "Pergamino")
    ok_verde = _update_precio(PROD_VERDE,     precio_oro_verde, "Verde (Oro Verde)")
    ok_cere  = _update_precio(PROD_CEREZO,    precio_cerezo,    "Cerezo") if precio_cerezo else True
    return ok_perg and ok_verde and ok_cere


def _update_precio(codigo: str, precio: float, nombre: str) -> bool:
    try:
        resp = requests.put(
            _url(f"productos/{BUSINESS_ID}/{codigo}"),
            json={"precio": round(precio, 2)},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        if resp.status_code == 200:
            logger.info(f"[APARTALO] Precio {nombre} actualizado → S/. {precio:.2f}")
            return True
        else:
            logger.warning(f"[APARTALO] Precio {nombre} no actualizado: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"[APARTALO] Error actualizando precio {nombre}: {e}")
        return False
