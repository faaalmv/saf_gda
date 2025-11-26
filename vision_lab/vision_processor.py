#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import logging
import cv2
import numpy as np
from pathlib import Path
from typing import Final

# --- CONFIGURACIÓN ---
BLOCK_SIZE: Final[int] = 11
C_CONSTANT: Final[int] = 2
VALID_EXTENSIONS: Final[set[str]] = {'.jpg', '.jpeg', '.png'}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SAF-VISION] - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger("VisionEngine")

def validate_input(file_path: Path) -> None:
    if not file_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
    if file_path.suffix.lower() not in VALID_EXTENSIONS:
        raise ValueError(f"Extensión no soportada: {file_path.suffix}")

def enforce_text_polarity(binary_img: np.ndarray) -> np.ndarray:
    mean_intensity = cv2.mean(binary_img)[0]
    if mean_intensity < 127:
        logger.info(f"Fondo oscuro detectado ({mean_intensity:.2f}). Invirtiendo polaridad...")
        return cv2.bitwise_not(binary_img)
    return binary_img

def process_image(input_path_str: str, output_dir_str: str) -> None:
    try:
        input_path = Path(input_path_str).resolve()
        output_dir = Path(output_dir_str).resolve()

        validate_input(input_path)

        logger.info(f"Procesando: {input_path.name}")
        image = cv2.imread(str(input_path))

        if image is None: raise IOError("Error al leer la imagen (cv2.imread es None).")

        # Pipeline
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, BLOCK_SIZE, C_CONSTANT)
        final = enforce_text_polarity(binary)

        output_path = output_dir / f"{input_path.stem}_ocr_ready.png"
        if not cv2.imwrite(str(output_path), final):
            raise IOError("Fallo al guardar imagen.")

        logger.info("PROCESAMIENTO EXITOSO")
        print(f"OUTPUT_FILE:{output_path}")

    except Exception as e:
        logger.error(f"Error Crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Uso: python vision_processor.py <imagen>")

    base_output = Path.home() / "saf_gda" / "vision_lab" / "salida_debug"
    base_output.mkdir(parents=True, exist_ok=True)

    process_image(sys.argv[1], str(base_output))
