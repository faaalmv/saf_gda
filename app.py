import streamlit as st
import psycopg
import os
import math
import logging
import tempfile
from typing import Optional, Dict

# IMPORTACIÓN DEL MOTOR DE INTELIGENCIA (NUEVO)
# Importamos la función maestra directamente desde tu script core_processor.py
from core_processor import document_full_processor

# ==========================================
# 1. CONFIGURACIÓN Y LOGGING
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [SAF-WEB] - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="SAF-GDA: Ingesta", page_icon="🛡️", layout="wide")

# ==========================================
# 2. GESTIÓN DE SECRETOS (SEGURA)
# ==========================================
def get_db_config() -> Dict[str, str]:
    try:
        return {
            "host": "127.0.0.1", # Al usar network host, localhost es correcto
            "port": os.environ.get("SAF_DB_PORT", "5432"),
            "dbname": os.environ["SAF_DB_NAME"],
            "user": os.environ["SAF_DB_USER"],
            "password": os.environ["SAF_DB_PASSWORD"]
        }
    except KeyError as e:
        # Fallback seguro: Si no hay .env, no rompemos la app hasta que se intente conectar
        logger.warning(f"Modo sin credenciales: Falta {e}")
        return {}

DB_CONFIG = get_db_config()

# ==========================================
# 3. UTILERÍAS
# ==========================================
def get_db_status() -> int:
    if not DB_CONFIG: return -1
    try:
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM tbl_entradas_raw;")
                return int(cur.fetchone()[0])
    except Exception as e:
        logger.error(f"DB Error: {e}")
        return -1

def _format_size(size_bytes: int) -> str:
    if size_bytes == 0: return "0B"
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    return f"{round(size_bytes / p, 2)} {('B', 'KB', 'MB', 'GB')[i]}"

# ==========================================
# 4. INTERFAZ PRINCIPAL
# ==========================================
def main():
    st.title("🛡️ SAF-GDA: Ingesta & Auditoría Forense")
    st.markdown("---")

    col_status, col_upload = st.columns([1, 2], gap="large")

    # --- PANEL IZQUIERDO: ESTADO ---
    with col_status:
        count = get_db_status()
        status_color = "normal" if count >= 0 else "inverse"
        status_msg = "Online" if count >= 0 else "Offline"
        
        st.metric(
            label="REPOSITORIO SQL (Entradas RAW)",
            value=f"{count:,} Registros" if count >= 0 else "ERROR CONEXIÓN",
            delta=status_msg,
            delta_color=status_color
        )
        
        st.info("""
        **Instrucciones:**
        1. Suba imagen (.png/.jpg)
        2. El motor extraerá:
           - Folio Fiscal (OCR)
           - Monto Total (OCR)
           - Código QR (Decodificación)
        """)

    # --- PANEL DERECHO: PROCESAMIENTO ---
    with col_upload:
        st.subheader("Carga y Procesamiento de Evidencia")
        
        uploaded_file = st.file_uploader("Evidencia Digital", type=['png', 'jpg', 'jpeg'])

        if uploaded_file is not None:
            c1, c2 = st.columns(2)
            c1.info(f"📄 **Archivo:** `{uploaded_file.name}`")
            c2.info(f"📦 **Peso:** `{_format_size(uploaded_file.size)}`")

            # Botón de Ejecución Real
            if st.button("⚡ EJECUTAR ANÁLISIS FORENSE", type="primary", use_container_width=True):
                
                with st.status("Procesando evidencia...", expanded=True) as status:
                    # 1. Guardar archivo temporalmente
                    st.write("💾 Persistiendo archivo en contenedor...")
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                        tmp_file.write(uploaded_file.getbuffer())
                        tmp_path = tmp_file.name
                    
                    try:
                        # 2. Invocar al Core Processor (Tu lógica real)
                        st.write("🧠 Invocando Red Neuronal / Tesseract OCR...")
                        
                        # Preparamos el payload que espera tu función
                        job_payload = {
                            "job_id": f"WEB_{uploaded_file.name}",
                            "document_path": tmp_path
                        }
                        
                        # ¡AQUÍ OCURRE LA MAGIA!
                        result = document_full_processor(job_payload)
                        
                        status.update(label="¡Procesamiento Completado!", state="complete", expanded=False)
                        
                        # 3. Mostrar Resultados
                        if result["status"] == "PROCESS_OK":
                            st.success("✅ Extracción Exitosa")
                            
                            # Mostramos los datos extraídos
                            res_col1, res_col2 = st.columns(2)
                            with res_col1:
                                st.caption("Folio Fiscal (OCR Zonal)")
                                st.code(result.get("ocr_folio_fiscal") or "NO DETECTADO")
                                
                                st.caption("Total Factura (OCR Zonal)")
                                st.code(result.get("ocr_total") or "NO DETECTADO")
                                
                            with res_col2:
                                st.caption("Datos QR")
                                st.text_area("Decodificación", result.get("qr_data") or "QR ilegible/ausente", height=100)
                                
                            with st.expander("🔍 Ver JSON Crudo (Auditoría Técnica)"):
                                st.json(result)
                        else:
                            st.error(f"❌ Fallo en procesamiento: {result.get('error_msg')}")

                    except Exception as e:
                        st.error(f"Error Crítico en Runtime: {e}")
                    finally:
                        # Limpieza
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)

if __name__ == "__main__":
    main()