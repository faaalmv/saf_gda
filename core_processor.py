"""
CORE_PROCESSOR.PY (Versión Smart Regex - Flexible)
-------------------------------------------------------
AUTOR: SAF-SYNTH-LEAD
ARQUITECTURA: Python 3.12 (AsyncIO + Multiprocessing)
DESCRIPCIÓN: Reemplaza coordenadas fijas por búsqueda de patrones (Regex).
"""

import asyncio
import concurrent.futures
import logging
import os
import sys
import time
import re  # IMPORTANTE: Para expresiones regulares
from typing import List, Dict, Any, Final, Tuple, Optional
import cv2
import numpy as np
import pytesseract
from PIL import Image
from pyzbar import pyzbar
from pathlib import Path

# --- CONFIGURACIÓN ESTRATÉGICA ---
MAX_CPU_WORKERS: Final[int] = 4
TIMEOUT_IO_SEC: Final[float] = 10.0
TIMEOUT_CPU_TASK_SEC: Final[float] = 20.0 # Aumentado para lectura completa
TESS_CONFIG: str = "--psm 3 -l spa" # PSM 3: Auto page segmentation (lee todo)

# Regex para Folio Fiscal (UUID v4 estándar del SAT)
REGEX_UUID = r'[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}'

# Regex para detectar montos (Busca formato $ 1,234.56 o 1234.56 cerca de la palabra Total)
REGEX_TOTAL = r'(?:Total|TOTAL|Neto)[\s:.$]*([\d,]+\.\d{2})'

# --- LOGGING FORENSE ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | PID:%(process)-5d | %(levelname)-7s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("SAF_CORE")

# ==============================================================================
# LÓGICA DE NEGOCIO (CPU BOUND)
# ==============================================================================

def _preprocess_image(image: np.ndarray) -> np.ndarray:
    """ Pre-procesamiento para mejorar contraste de texto. """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # Binarización simple suele funcionar mejor para texto completo que adaptativa agresiva
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary

def document_full_processor(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """ Procesador que lee TODO el documento y busca patrones. """
    start_time = time.perf_counter()
    worker_pid = os.getpid()
    
    response: Dict[str, Any] = {
        "status": "PROCESS_FAIL", "ocr_total": None, "ocr_folio_fiscal": None,
        "qr_data": None, "time_total": 0.0, "error_msg": None, 
        "job_id": job_data.get("job_id"),
        "worker_pid": worker_pid,
        "full_text_debug": "" # Para ver qué leyó realmente
    }

    try:
        document_path = job_data.get('document_path')
        if not os.path.exists(document_path): 
            raise FileNotFoundError(f"Archivo no encontrado: {document_path}")

        # 1. Carga OpenCV
        cv_img = cv2.imread(document_path)
        processed_bin = _preprocess_image(cv_img)

        # 2. Extracción QR (Igual que antes, funciona bien)
        barcodes = pyzbar.decode(cv_img)
        qr_candidates = [b.data.decode("utf-8") for b in barcodes if b.data]
        response["qr_data"] = qr_candidates[0] if qr_candidates else None

        # 3. OCR DE PÁGINA COMPLETA (El cambio clave)
        pil_img = Image.fromarray(processed_bin)
        full_text = pytesseract.image_to_string(pil_img, config=TESS_CONFIG)
        response["full_text_debug"] = full_text[:200] + "..." # Guardamos un snippet

        # 4. INTELIGENCIA DE PATRONES (REGEX)
        
        # A. Buscar UUID (Folio Fiscal)
        uuid_match = re.search(REGEX_UUID, full_text)
        if uuid_match:
            response["ocr_folio_fiscal"] = uuid_match.group(0)
        else:
            # Fallback: Si no lo encuentra en el texto, intentar extraer del QR si existe
            if response["qr_data"] and "id=" in response["qr_data"]:
                try:
                    # Extraer id=UUID del string del QR del SAT
                    match_qr = re.search(r'id=([a-fA-F0-9-]{36})', response["qr_data"])
                    if match_qr:
                        response["ocr_folio_fiscal"] = match_qr.group(1) + " (Vía QR)"
                except:
                    pass

        # B. Buscar Total
        # Buscamos patrones de dinero. Esto es más heurístico.
        total_match = re.search(REGEX_TOTAL, full_text)
        if total_match:
            response["ocr_total"] = total_match.group(1)
        
        response["status"] = "PROCESS_OK"

    except Exception as e:
        logger.error(f"Error crítico: {str(e)}")
        response["status"] = "PROCESS_FAIL"
        response["error_msg"] = str(e)

    finally:
        end_time = time.perf_counter()
        response["time_total"] = round(end_time - start_time, 4)
        
    return response

# ... (El resto del código boilerplate main/asyncio se queda igual) ...