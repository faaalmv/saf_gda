# Usamos la imagen base
FROM python:3.9-slim

WORKDIR /app

# ---------------------------------------------------------------------
# CORRECCIÓN: Reemplazamos 'libgl1-mesa-glx' por 'libgl1'
# Esto soluciona el error: "Package has no installation candidate"
# ---------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    libgl1 \
    libglib2.0-0 \
    libzbar0 \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Instalación de librerías Python
RUN pip install --no-cache-dir \
    streamlit \
    pandas \
    psycopg[binary] \
    pillow \
    opencv-python-headless \
    pytesseract \
    pyzbar \
    numpy

EXPOSE 8501

CMD ["streamlit", "run", "app.py"]