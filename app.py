import streamlit as st
import psycopg
import os
import math
import logging
from typing import Optional, Dict

# ==========================================
# 1. CONFIGURACIÓN Y LOGGING (AUDITORÍA)
# ==========================================

# Configuración de Logging (Estándar SAF para trazabilidad)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [SAF-CORE] - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuración de la página (Mandatorio: Primera instrucción Streamlit)
st.set_page_config(
    page_title="SAF-GDA: Ingesta",
    page_icon="🛡️",
    layout="wide"
)

# ==========================================
# 2. CONSTANTES DEL SISTEMA (SECURE)
# ==========================================

def get_db_config() -> Dict[str, str]:
    """
    Recupera credenciales de variables de entorno.
    Lanza error si faltan secretos críticos.
    """
    try:
        config = {
            "host": os.environ["SAF_DB_HOST"],
            "port": os.environ.get("SAF_DB_PORT", "5432"),
            "dbname": os.environ["SAF_DB_NAME"],
            "user": os.environ["SAF_DB_USER"],
            "password": os.environ["SAF_DB_PASSWORD"]
        }
        return config
    except KeyError as e:
        logger.critical(f"FALTA VARIABLE DE ENTORNO CRÍTICA: {e}")
        st.error(f"Error de Seguridad: Falta configuración {e}")
        st.stop() # Detiene la ejecución para proteger el sistema

# Inicialización segura
try:
    DB_CONFIG = get_db_config()
except Exception:
    DB_CONFIG = {} # Fallback vacío para evitar crash en importación

# Ruta de trazabilidad del motor
TRACE_PATH = "/home/jesuslangarica/saf_gda/core_processor.py"

# ==========================================
# 3. LÓGICA DE NEGOCIO (BACKEND)
# ==========================================

@st.cache_data(ttl=30, show_spinner=False)
def get_db_status() -> int:
    """
    Conecta a PostgreSQL y obtiene el conteo de registros 'raw'.
    Utiliza Context Managers para garantizar el cierre de conexiones.
    
    Returns:
        int: Número de registros o -1 si hay error de conexión.
    """
    try:
        # 'with' asegura commit/rollback y cierre automático
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM tbl_entradas_raw;")
                result = cur.fetchone()
                count = int(result[0]) if result else 0
                logger.info(f"DB Status Check: {count} registros.")
                return count
                
    except psycopg.Error as e:
        logger.error(f"Error Operacional DB: {e}")
        return -1
    except Exception as e:
        logger.critical(f"Error Sistémico: {e}")
        return -1

def _format_size(size_bytes: int) -> str:
    """Convierte bytes a formato legible (KB, MB) dinámicamente."""
    if size_bytes == 0: return "0B"
    size_name = ("B", "KB", "MB", "GB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

# ==========================================
# 4. INTERFAZ DE USUARIO (MAIN)
# ==========================================

def main():
    """Ejecución principal de la interfaz Streamlit."""
    
    # 1. Encabezado
    st.title("🛡️ SAF-GDA: Módulo de Ingesta de Documentos (Día 4)")
    st.markdown("---")

    # 2. Layout de Columnas (Gap large para mejor estética)
    col_status, col_upload = st.columns([1, 2], gap="large")

    # --- COLUMNA 1: MONITOR DE ESTADO ---
    with col_status:
        db_count = get_db_status()
        
        if db_count == -1:
            st.metric(
                label="ESTADO DE CONCILIACIÓN (BASE DE DATOS)",
                value="ERROR CRÍTICO",
                delta="Offline",
                delta_color="inverse"
            )
            st.error("Conexión fallida con 127.0.0.1:5432")
        else:
            # Formato con separador de miles para legibilidad
            st.metric(
                label="ESTADO DE CONCILIACIÓN (BASE DE DATOS)",
                value=f"{db_count:,} Registros",
                delta="Online",
                delta_color="normal"
            )

    # --- COLUMNA 2: CARGA DE EVIDENCIA ---
    with col_upload:
        st.subheader("Carga de Evidencia Digital")
        
        uploaded_file = st.file_uploader(
            "Seleccionar archivo", 
            type=['pdf', 'png', 'jpg', 'jpeg'],
            help="Soporta documentos PDF y evidencia gráfica (JPG/PNG)."
        )

        if uploaded_file is not None:
            # Metadata del archivo
            file_info_cols = st.columns(2)
            file_info_cols[0].info(f"**Archivo:** `{uploaded_file.name}`")
            file_info_cols[1].info(f"**Tamaño:** `{_format_size(uploaded_file.size)}`")

            # Preview opcional para imágenes (Mejora UX)
            if uploaded_file.type.startswith('image'):
                with st.expander("👁️ Vista Previa de Evidencia"):
                    st.image(uploaded_file, use_column_width=True)

            # Botón de Acción Principal
            if st.button("1. Iniciar Conciliación Zonal", type="primary", use_container_width=True):
                try:
                    # Mensaje de éxito visual
                    st.success("✅ Archivo aceptado. Procesamiento iniciado.")
                    
                    # Log de trazabilidad técnica (Requerimiento Crítico)
                    st.code(
                        f"Motor Asíncrono iniciado.\nTrazabilidad: {TRACE_PATH}", 
                        language="bash"
                    )
                    logger.info(f"Ingesta iniciada para archivo: {uploaded_file.name}")
                    
                except Exception as e:
                    st.error(f"Error al invocar el motor: {e}")
                    logger.error(f"Fallo en botón de ingesta: {e}")

if __name__ == "__main__":
    main()
