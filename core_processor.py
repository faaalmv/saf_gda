"""
CORE_PROCESSOR.PY (Versión Día 3 - FINAL, Trazabilidad Corregida)
-------------------------------------------------------
AUTOR: SAF-SYNTH-LEAD
ARQUITECTURA: Python 3.12 (AsyncIO + Multiprocessing)
CLASIFICACIÓN: GOLDEN MASTER / PRODUCTION READY
"""

import asyncio
import concurrent.futures
import logging
import os
import sys
import time
from typing import List, Dict, Any, Final, Tuple, Optional
import cv2
import numpy as np
import pytesseract
from PIL import Image
from pyzbar import pyzbar
from pathlib import Path

# --- CONFIGURACIÓN ESTRATÉGICA ---
MAX_CPU_WORKERS: Final[int] = 4
BATCH_SIZE: Final[int] = 4
TIMEOUT_IO_SEC: Final[float] = 10.0
TIMEOUT_CPU_TASK_SEC: Final[float] = 15.0

# Rutas estándar SAF-GDA
BASE_DIR: Final[Path] = Path.home() / "saf_gda"
VISION_INPUT_PATH: Final[str] = str(BASE_DIR / "vision_lab" / "entrada_raw" / "test_factura.png")
VISION_OUTPUT_DIR: Final[str] = str(BASE_DIR / "vision_lab" / "salida_debug_pipeline") 

# Coordenadas Normalizadas (Base 1000x1000)
ZONA_FOLIO_FISCAL: Tuple[int, int, int, int] = (700, 100, 950, 150)
ZONA_TOTAL: Tuple[int, int, int, int] = (700, 750, 950, 800)
TESS_CONFIG: str = "--psm 6 -l spa"

# --- LOGGING FORENSE ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | PID:%(process)-5d | %(levelname)-7s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("SAF_CORE")

# ==============================================================================
# LÓGICA DE NEGOCIO (CPU BOUND) - Ejecutada en ProcessPoolExecutor
# ==============================================================================

def _denormalize_coords(roi: Tuple[int, int, int, int], img_w: int, img_h: int) -> Tuple[int, int, int, int]:
    x1, y1, x2, y2 = roi
    abs_x1 = int((x1 / 1000.0) * img_w)
    abs_y1 = int((y1 / 1000.0) * img_h)
    abs_x2 = int((x2 / 1000.0) * img_w)
    abs_y2 = int((y2 / 1000.0) * img_h)
    abs_x2 = max(abs_x1 + 1, min(abs_x2, img_w))
    abs_y2 = max(abs_y1 + 1, min(abs_y2, img_h))
    return (abs_x1, abs_y1, abs_x2, abs_y2)

def _preprocess_image(image: np.ndarray) -> np.ndarray:
    """ Ejecuta el pipeline de pre-procesamiento de visión (OpenCV). """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    if np.mean(binary) < 127:
        binary = cv2.bitwise_not(binary)
        
    return binary

def document_full_processor(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """ Procesador Síncrono Maestro para Documentos Fiscales. """
    start_time = time.perf_counter()
    worker_pid = os.getpid() # CRÍTICO: Capturar PID del worker al inicio
    
    response: Dict[str, Any] = {
        "status": "PROCESS_FAIL", "ocr_total": None, "ocr_folio_fiscal": None,
        "qr_data": None, "time_total": 0.0, "error_msg": None, 
        "job_id": job_data.get("job_id"),
        "worker_pid": worker_pid # CRÍTICO: Asegurar que el PID siempre esté presente
    }
    cv_img = None

    try:
        document_path = job_data.get('document_path')
        if not document_path: raise ValueError("Falta 'document_path'.")
        if not os.path.exists(document_path): raise FileNotFoundError(f"Archivo no encontrado: {document_path}")

        # 1. Carga y Pre-procesamiento
        cv_img = cv2.imread(document_path)
        if cv_img is None: raise ValueError("Fallo de decodificación de imagen.")
        height, width = cv_img.shape[:2]
        
        processed_bin = _preprocess_image(cv_img)

        # 2. Extracción de Códigos de Barras / QR (Intento sobre imagen original)
        barcodes = pyzbar.decode(cv_img)
        qr_candidates = [barcode.data.decode("utf-8") for barcode in barcodes if barcode.data]
        response["qr_data"] = qr_candidates[0] if qr_candidates else None

        # 3. OCR Zonal (pytesseract + PIL)
        pil_img = Image.fromarray(processed_bin)

        # A. Extracción Folio Fiscal
        coords_folio = _denormalize_coords(ZONA_FOLIO_FISCAL, width, height)
        roi_folio = pil_img.crop(coords_folio)
        text_folio = pytesseract.image_to_string(roi_folio, config=TESS_CONFIG)
        response["ocr_folio_fiscal"] = " ".join(text_folio.split()) if text_folio else None

        # B. Extracción Total
        coords_total = _denormalize_coords(ZONA_TOTAL, width, height)
        roi_total = pil_img.crop(coords_total)
        text_total = pytesseract.image_to_string(roi_total, config=TESS_CONFIG)
        response["ocr_total"] = " ".join(text_total.split()) if text_total else None

        response["status"] = "PROCESS_OK"

    except Exception as e:
        logger.error(f"Error crítico procesando {document_path}: {str(e)}")
        response["status"] = "PROCESS_FAIL"
        response["error_msg"] = str(e)

    finally:
        end_time = time.perf_counter()
        response["time_total"] = round(end_time - start_time, 4)
        # Se elimina el 'del' innecesario para evitar warnings de sintaxis
        
    return response # Retorno final y único

# ==============================================================================
# CAPA DE ORQUESTACIÓN ASÍNCRONA (I/O BOUND) - MAIN THREAD
# ==============================================================================

async def fetch_job_queue() -> List[Dict[str, Any]]:
    logger.info(f"Conectando a la Cola (Simulación I/O)...")
    await asyncio.sleep(0.1)
    
    jobs = []
    for i in range(BATCH_SIZE):
        jobs.append({
            "job_id": f"TASK_{i:02d}",
            "document_path": VISION_INPUT_PATH,
            "priority": "HIGH"
        })
    
    logger.info(f"Se han recibido {len(jobs)} trabajos de visión.")
    return jobs

async def run_cpu_task_async(
    executor: concurrent.futures.ProcessPoolExecutor,
    item: Dict[str, Any]
) -> Dict[str, Any]:
    loop = asyncio.get_running_loop()
    job_id = item.get("job_id")
    
    try:
        # Llama a la función de procesamiento final
        result = await asyncio.wait_for(
            loop.run_in_executor(executor, document_full_processor, item),
            timeout=TIMEOUT_CPU_TASK_SEC
        )
        return result
        
    except asyncio.TimeoutError:
        logger.error(f"TIMEOUT: La tarea {job_id} excedió {TIMEOUT_CPU_TASK_SEC}s.")
        return {"status": "TIMEOUT", "error_msg": "Max execution time exceeded", "job_id": job_id, "worker_pid": 0}
    except Exception as e:
        logger.error(f"Error de infraestructura en tarea {job_id}: {e}")
        return {"status": "INFRA_ERROR", "error_msg": str(e), "job_id": job_id, "worker_pid": 0}

async def main_processor() -> None:
    logger.info(f"=== INICIANDO SAF-GDA CORE | POOL: {MAX_CPU_WORKERS} WORKERS ===")

    try:
        jobs = await asyncio.wait_for(fetch_job_queue(), timeout=TIMEOUT_IO_SEC)
        
        if not jobs: return

        with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_CPU_WORKERS) as executor:
            logger.info("Distribuyendo carga de OCR Zonal al cluster de CPU...")
            
            futures = [run_cpu_task_async(executor, job) for job in jobs]
            results = await asyncio.gather(*futures, return_exceptions=True)
            
            # 3. Análisis de Resultados
            metrics = {"OK": 0, "FAIL": 0, "TOTAL_TIME": 0.0}
            
            for res in results:
                if isinstance(res, Exception):
                    logger.critical(f"Excepción no manejada: {res}")
                    metrics["FAIL"] += 1
                    continue
                    
                status = res.get("status")
                jid = res.get("job_id")
                
                if status == "PROCESS_OK":
                    metrics["OK"] += 1
                    t = res.get("time_total", 0)
                    metrics["TOTAL_TIME"] += t
                    # LOGGING DE LA CONCILIACIÓN (Nivel de Trazabilidad SAF-GDA)
                    logger.info(
                        f"✓ {jid} | PID:{res['worker_pid']} | {t}s | "
                        f"Folio OCR:'{res['ocr_folio_fiscal']}' | Total OCR:'{res['ocr_total']}' | QR:'{res['qr_data']}'"
                    )
                else:
                    metrics["FAIL"] += 1
                    # Añadir el PID incluso en el Warning
                    logger.warning(f"✗ {jid} | PID:{res.get('worker_pid', 'N/A')} | {status} | Error: {res.get('error_msg')}")

            avg_time = metrics["TOTAL_TIME"] / metrics["OK"] if metrics["OK"] > 0 else 0
            logger.info(f"--- RESUMEN DE PROCESAMIENTO CONCILIACIÓN ---")
            logger.info(f"Éxito {metrics['OK']}/{len(jobs)} | Latencia Promedio Total: {avg_time:.4f}s")
            
    except Exception as e:
        logger.critical(f"Fallo sistémico en main_processor: {e}", exc_info=True)

# ==============================================================================
# PUNTO DE ENTRADA SEGURO
# ==============================================================================

if __name__ == "__main__":
    try:
        start_global = time.perf_counter()
        asyncio.run(main_processor())
        duration = time.perf_counter() - start_global
        logger.info(f"=== EJECUCIÓN TOTAL DE PIPELINE COMPLETADA EN {duration:.2f}s ===")
        sys.exit(0)
    except KeyboardInterrupt:
        logger.warning("\nInterrupción manual. Apagando suavemente...")
        sys.exit(130)
    except Exception as fatal_error:
        logger.critical(f"Error irrecuperable de arranque: {fatal_error}")
        sys.exit(1)
