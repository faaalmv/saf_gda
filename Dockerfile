# Usamos una imagen base ligera pero oficial
FROM python:3.9-slim

# Establecemos el directorio de trabajo
WORKDIR /app

# ---------------------------------------------------------------------
# 1. INSTALACIÓN DE DEPENDENCIAS DEL SISTEMA OPERATIVO (Nivel OS)
# ---------------------------------------------------------------------
# tesseract-ocr: El motor de OCR.
# tesseract-ocr-spa: El paquete de idioma español (Crítico para tu config).
# libgl1-mesa-glx & libglib2.0-0: Dependencias gráficas requeridas por OpenCV.
# libzbar0: Librería base requerida por pyzbar para leer QRs.
# ---------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libzbar0 \
    && rm -rf /var/lib/apt/lists/*

# Copiamos el código fuente
COPY . .

# ---------------------------------------------------------------------
# 2. INSTALACIÓN DE LIBRERÍAS PYTHON
# ---------------------------------------------------------------------
# Agregamos las librerías que tu core_processor.py importa:
# - opencv-python-headless: Versión optimizada para servidores (sin GUI).
# - pytesseract: Wrapper para el motor OCR.
# - pyzbar: Para decodificación de QR/Barras.
# - numpy: Para manipulación de matrices de imagen.
# ---------------------------------------------------------------------
RUN pip install --no-cache-dir \
    streamlit \
    pandas \
    psycopg[binary] \
    pillow \
    opencv-python-headless \
    pytesseract \
    pyzbar \
    numpy

# Exponemos el puerto de Streamlit
EXPOSE 8501

# Ejecutamos la aplicación
CMD ["streamlit", "run", "app.py"]