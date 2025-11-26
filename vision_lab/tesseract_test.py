#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAF-GDA: Tesseract OCR Execution Module (Golden Master)
-------------------------------------------------------
Script autocontenido y endurecido para la extracción de texto OCR.
Diseñado para alta disponibilidad y trazabilidad de errores.

Autor: SAF-SYNTH-LEAD
Estándar: Python 3.12+ (Type Hinting, PEP 8)
"""

import sys
import logging
import re
from pathlib import Path
from typing import Optional

# Verificación defensiva de dependencias
try:
    import pytesseract
    from PIL import Image, UnidentifiedImageError
except ImportError as e:
    sys.exit(f"[CRITICAL ERROR] Dependencia faltante: {e}. Ejecute: pip install pytesseract pillow")

# Configuración del Logger (Auditoría Técnica)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [SAF-OCR] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("OCR_Engine")

def clean_ocr_text(raw_text: str) -> str:
    """
    Sanitiza la salida del OCR eliminando caracteres de control y normalizando espacios.
    Convierte cualquier secuencia de espacios/newlines en un único espacio.

    Args:
        raw_text (str): Texto crudo retornado por Tesseract.

    Returns:
        str: Texto limpio en una sola línea.
    """
    if not raw_text:
        return ""
    # Regex: Reemplaza \n, \t, \r y espacios múltiples por un solo espacio
    cleaned = re.sub(r'\s+', ' ', raw_text)
    return cleaned.strip()

def run_ocr(image_path: str) -> Optional[str]:
    """
    Ejecuta el pipeline de OCR sobre una imagen dada.
    
    Configuración Tesseract:
    - PSM 7: Tratar imagen como una sola línea de texto.
    - Lang: Español (spa).

    Args:
        image_path (str): Ruta al archivo de imagen.

    Returns:
        Optional[str]: Texto extraído limpio o None si ocurre un error crítico.
    """
    # Resolución segura de la ruta (expande '~' y resuelve symlinks)
    target_path = Path(image_path).expanduser().resolve()

    # 1. Validación de Entrada
    if not target_path.exists():
        logger.error(f"El archivo no existe: {target_path}")
        return None
    
    if not target_path.is_file():
        logger.error(f"La ruta no apunta a un archivo válido: {target_path}")
        return None

    logger.info(f"Procesando imagen: {target_path.name}")

    # Configuración de parámetros Tesseract
    tess_config = r'--psm 7 -l spa'

    try:
        # 2. Gestión Segura de Memoria (Context Manager)
        # CRÍTICO: 'with' garantiza el cierre del file descriptor tras la lectura.
        with Image.open(target_path) as img:
            
            # Validación de integridad básica
            img.load() 
            
            # 3. Ejecución del Motor OCR
            raw_text = pytesseract.image_to_string(img, config=tess_config)
            
            # 4. Limpieza de Datos
            final_text = clean_ocr_text(raw_text)
            
            logger.info("Lectura OCR completada.")
            return final_text

    except UnidentifiedImageError:
        logger.error("PIL Error: El archivo está corrupto o no es una imagen soportada.")
    except pytesseract.TesseractNotFoundError:
        logger.critical("Entorno Error: Binario de Tesseract no encontrado. Verifique instalación y PATH.")
    except pytesseract.TesseractError as e:
        logger.error(f"Motor Error: Fallo interno de Tesseract - {e}")
    except Exception as e:
        logger.error(f"Runtime Error: Excepción inesperada - {e}")

    return None

def main():
    """
    Orquestador principal del script.
    """
    # Ruta definida por la arquitectura del proyecto SAF-GDA
    TARGET_IMAGE = "~/saf_gda/vision_lab/salida_debug/test_factura_ocr_ready.png"

    print("=" * 60)
    print("SAF-GDA: VISION LAB - TESSERACT DIAGNOSTIC TOOL")
    print("=" * 60)

    # Ejecución del Pipeline
    extracted_text = run_ocr(TARGET_IMAGE)

    print("-" * 60)
    
    if extracted_text is not None:
        print("RESULTADO FINAL:")
        # Usamos comillas para delimitar claramente el contenido extraído
        print(f"'{extracted_text}'")
        
        if not extracted_text:
            logger.warning("El proceso finalizó sin errores, pero no se detectó texto (cadena vacía).")
        
        print("-" * 60)
        print("Ejecución finalizada correctamente.")
        sys.exit(0)
    else:
        print("FALLO CRÍTICO: No se pudo obtener el texto.")
        sys.exit(1)

if __name__ == "__main__":
    main()
