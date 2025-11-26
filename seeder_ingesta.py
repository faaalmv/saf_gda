import os
import sys
import hashlib
import logging
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Final

# Verificación de dependencias
try:
    import psycopg
    from psycopg import sql
except ImportError as e:
    sys.exit(f"FATAL: Dependencia faltante -> {e}")

# --- CONFIGURACIÓN DE LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] SAF-INGESTA: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("SAF_CORE")

# --- CONSTANTES ---
COLUMNS_ORDER: Final[List[str]] = [
    'div', 'provedor', 'orden_compra', 'mov', 'fecha_entrada',
    'folio_factura', 'codigo_articulo', 'articulo', 'cantidad',
    'precio_unitario', 'importe', 'fondeo', 'folio_rb'
]

# Definición estricta de tipos para PostgreSQL
INTEGER_COLUMNS: Final[List[str]] = ['div', 'orden_compra', 'mov']
NUMERIC_COLUMNS: Final[List[str]] = ['cantidad', 'precio_unitario', 'importe']

CSV_FILENAME: Final[str] = 'Datos_Entradas.csv'
TARGET_TABLE: Final[str] = 'tbl_entradas_raw'

# --- CONFIGURACIÓN BD ---
@dataclass(frozen=True)
class DBConfig:
    host: str = os.getenv("DB_HOST", "127.0.0.1")
    port: str = os.getenv("DB_PORT", "5432")
    dbname: str = os.getenv("DB_NAME", "saf_gda_db")
    user: str = os.getenv("DB_USER", "saf_user")
    password: str = os.getenv("DB_PASSWORD", "SAF-Key16")

    @property
    def conn_string(self) -> str:
        return f"host={self.host} port={self.port} dbname={self.dbname} user={self.user} password={self.password}"

# --- LÓGICA DE NEGOCIO ---

def load_and_transform_data(filepath: str) -> pd.DataFrame:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"El archivo {filepath} no existe.")

    logger.info(f"Cargando archivo: {filepath}...")
    
    # 1. Leer todo como String inicialmente para no perder formatos
    try:
        df = pd.read_csv(filepath, dtype=str, usecols=COLUMNS_ORDER)
    except ValueError as e:
        logger.error("Error estructural en CSV.")
        raise e

    # 2. Eliminar duplicados exactos
    registros_iniciales = len(df)
    df.drop_duplicates(subset=COLUMNS_ORDER, keep='first', inplace=True)
    if len(df) != registros_iniciales:
        logger.warning(f"Se eliminaron {registros_iniciales - len(df)} duplicados.")
    
    # *** CORRECCIÓN MAESTRA DE TIPOS (V5) ***
    
    # A. Limpieza de Columnas ENTERAS (INTEGER)
    # Convertimos a numérico coercitivo, y luego a Int64 (Nullable Integer).
    # Esto asegura que 3269.0 se convierta a 3269, y los errores a <NA>.
    for col in INTEGER_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')

    # B. Limpieza de Columnas DECIMALES (NUMERIC)
    # Aquí los flotantes están permitidos.
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # C. Estandarización de Nulos para PostgreSQL
    # Convertimos pd.NA (de Int64), np.nan (de float) y None a un objeto None nativo de Python.
    # Esto es CRÍTICO para que psycopg envíe NULL y no 'NaN' o 'nan'.
    df = df.astype(object).where(pd.notnull(df), None)

    logger.info("Calculando Hash SHA-256...")

    # 3. Hash Vectorizado sobre los datos limpios
    # Nota: Usamos str(val) para que 3269 sea "3269" y None sea "" (cadena vacía)
    subset_df = df[COLUMNS_ORDER]
    hashes = [
        hashlib.sha256("".join(str(val) if val is not None else '' for val in row).encode('utf-8')).hexdigest()
        for row in subset_df.itertuples(index=False, name=None)
    ]
    df['registro_hash'] = hashes
    
    logger.info(f"Transformación lista. Registros a insertar: {len(df)}")
    return df

def execute_bulk_copy(df: pd.DataFrame, config: DBConfig) -> None:
    conn_str = config.conn_string
    final_columns = COLUMNS_ORDER + ['registro_hash']
    
    copy_sql = sql.SQL("COPY {table} ({fields}) FROM STDIN").format(
        table=sql.Identifier(TARGET_TABLE),
        fields=sql.SQL(', ').join(map(sql.Identifier, final_columns))
    )

    logger.info(f"Conectando a PostgreSQL...")
    try:
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                logger.info("Iniciando carga masiva (COPY)...")
                with cur.copy(copy_sql) as copy_stream:
                    for row in df[final_columns].itertuples(index=False, name=None):
                        copy_stream.write_row(row)
            conn.commit()
            logger.info("✅ Transacción confirmada EXITOSAMENTE.")

    except psycopg.Error as db_err:
        logger.critical(f"Error DB: {db_err}")
        raise
    except Exception as ex:
        logger.critical(f"Error inesperado: {ex}")
        raise

def main():
    try:
        config = DBConfig()
        df = load_and_transform_data(CSV_FILENAME)
        if df.empty: sys.exit(0)
        execute_bulk_copy(df, config)
        print("\n=== ✨ PROCESO FINALIZADO CON ÉXITO ✨ ===\n")
    except Exception as e:
        logger.critical(f"Fallo: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
