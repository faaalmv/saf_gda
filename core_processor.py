"""
CORE_PROCESSOR.PY (Versión Definitiva - Solo Extracción)
-------------------------------------------------------
OBJETIVO:
Extraer 5 datos clave usando Regex sobre imágenes pre-procesadas.
Sin validaciones de negocio. Solo datos.
"""

import logging
import re
import time
from typing import Dict, Any, Optional
import cv2
import numpy as np
import pytesseract
from PIL import Image

# --- CONFIGURACIÓN ---
TESS_CONFIG: str = "--psm 3 -l spa"

# --- PATRONES DE EXTRACCIÓN ---
PATTERNS = {
    # 1. UUID (Folio Fiscal)
    "UUID": r'[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}',
    
    # 2. RFC Emisor (Cualquier RFC con estructura válida)
    "RFC_EMISOR": r'[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}',
    
    # 3. Orden de Compra (OC/XX/XXXX)
    "ORDEN_COMPRA": r'(?:OC|ORDEN\s+DE\s+COMPRA|PEDIDO|N°\s+DE\s+ORDEN)[^\d]*(\d{2}[/.-]\d+)',
    
    # 4. Fecha (ISO o MX)
    "FECHA": r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})',
    
    # 5. Total (Moneda)
    "TOTAL": r'(?:Total|TOTAL|Neto|Pagar|Importe|Gran Total)[^0-9\n]*\$?\s*([\d,]+\.\d{2})'
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SAF_CORE")

def _preprocess_heavy_duty(image_path: str) -> np.ndarray:
    """ Limpieza: Zoom 2.5x + Umbral Adaptativo. """
    img = cv2.imread(image_path)
    if img is None: raise ValueError("Error leyendo imagen")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 5)
    return binary

def _clean_amount(amount_str: str) -> Optional[float]:
    """ Limpia formato moneda. """
    try:
        return float(re.sub(r'[^\d.]', '', amount_str.replace(',', '')))
    except:
        return None

def document_full_processor(job_data: Dict[str, Any]) -> Dict[str, Any]:
    response = {
        "status": "PROCESS_FAIL",
        "ocr_folio_fiscal": None,
        "ocr_total": None,
        "rfc_emisor": None,
        "orden_compra": None,
        "fecha_emision": None,
        "error_msg": None
    }

    try:
        doc_path = job_data.get('document_path')
        
        # 1. OCR
        processed_img = _preprocess_heavy_duty(doc_path)
        full_text = pytesseract.image_to_string(Image.fromarray(processed_img), config=TESS_CONFIG)

        # 2. Extracción Regex
        
        # UUID
        match_uuid = re.search(PATTERNS["UUID"], full_text, re.IGNORECASE)
        if match_uuid: 
            response["ocr_folio_fiscal"] = match_uuid.group(0).upper()

        # Total (Última coincidencia)
        matches_total = re.findall(PATTERNS["TOTAL"], full_text, re.IGNORECASE)
        if matches_total:
            response["ocr_total"] = str(_clean_amount(matches_total[-1]))

        # Orden de Compra
        match_oc = re.search(PATTERNS["ORDEN_COMPRA"], full_text, re.IGNORECASE)
        if match_oc:
            response["orden_compra"] = match_oc.group(1)

        # Fecha
        match_fecha = re.search(PATTERNS["FECHA"], full_text)
        if match_fecha:
            response["fecha_emision"] = match_fecha.group(1)

        # RFC Emisor (Tomamos el primero que encuentre)
        match_rfc = re.search(PATTERNS["RFC_EMISOR"], full_text)
        if match_rfc:
            response["rfc_emisor"] = match_rfc.group(0)

        response["status"] = "PROCESS_OK"

    except Exception as e:
        response["error_msg"] = str(e)
        logger.error(f"Error OCR: {e}")

    return response