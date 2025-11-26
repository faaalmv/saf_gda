/*
 * ======================================================================================
 * PROYECTO: SAF-GDA (Sistema de Auditoría Forense)
 * MÓDULO:   Ingesta de Datos (DDL)
 * ROL:      SAF-SYNTH-LEAD (Arquitecto de Datos)
 * MOTOR:    PostgreSQL 16
 * 
 * DESCRIPCIÓN:
 * Definición maestra de la tabla 'tbl_entradas_raw'.
 * Diseñada para alto rendimiento de escritura (Write-Heavy), integridad criptográfica
 * y soporte para patrones de cola de trabajo (Queue Pattern).
 * ======================================================================================
 */

BEGIN;

-- --------------------------------------------------------------------------------------
-- 1. ENTORNO DE SEGURIDAD
-- --------------------------------------------------------------------------------------

-- Habilitación de pgcrypto. Necesario si se requieren validaciones de hash server-side
-- o para futuros procedimientos de comparación forense.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Limpieza atómica para despliegues idempotentes.
DROP TABLE IF EXISTS tbl_entradas_raw CASCADE;

-- --------------------------------------------------------------------------------------
-- 2. DEFINICIÓN DE LA TABLA (LANDING ZONE)
-- --------------------------------------------------------------------------------------

CREATE TABLE tbl_entradas_raw (
    -- IDENTIDAD:
    -- 'GENERATED ALWAYS AS IDENTITY' es el estándar ANSI SQL en PG16.
    -- Evita los problemas de permisos y secuencias huérfanas del tipo 'SERIAL'.
    id_entrada_raw  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- HEADER CSV (Datos de Negocio):
    -- Se permiten NULLs para garantizar que la ingesta no falle por calidad de datos.
    -- La limpieza y validación de reglas de negocio ocurre en la capa 'Staging'.
    div             INTEGER,
    provedor        TEXT, -- Grafía 'provedor' mantenida según especificación del origen.
    orden_compra    INTEGER,
    mov             INTEGER,
    fecha_entrada   DATE,
    folio_factura   TEXT,
    codigo_articulo TEXT,
    articulo        TEXT,

    -- PRECISIÓN FINANCIERA:
    -- NUMERIC(18, 4) es mandatorio para auditoría.
    -- Permite montos hasta 99 billones y 4 decimales para prorrateos exactos.
    cantidad        NUMERIC(18, 4),
    precio_unitario NUMERIC(18, 4),
    importe         NUMERIC(18, 4),

    fondeo          TEXT,
    folio_rb        TEXT,

    -- ----------------------------------------------------------------------------------
    -- 3. AUDITORÍA TÉCNICA Y CONTROL
    -- ----------------------------------------------------------------------------------
    
    -- HUELLA DIGITAL (Integridad):
    -- El ETL debe calcular este SHA-256 antes de insertar.
    -- CHECK constraint asegura que no se inserten cadenas arbitrarias.
    registro_hash   TEXT NOT NULL 
                    CONSTRAINT chk_entradas_raw_hash_fmt CHECK (length(registro_hash) = 64),

    -- CONTROL DE FLUJO (Queue Pattern):
    -- FALSE = Registro crudo pendiente de normalización.
    procesado       BOOLEAN DEFAULT FALSE NOT NULL,

    -- CADENA DE CUSTODIA:
    -- Momento exacto de la persistencia en disco.
    fecha_ingesta   TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- --------------------------------------------------------------------------------------
-- 3. ESTRATEGIA DE ÍNDICES (PERFORMANCE)
-- --------------------------------------------------------------------------------------

-- IDEMPOTENCIA FUERTE:
-- Evita duplicidad de registros CSV a nivel de base de datos.
-- Si el hash ya existe, la inserción fallará, protegiendo la integridad.
CREATE UNIQUE INDEX idx_entradas_raw_hash_unique 
    ON tbl_entradas_raw (registro_hash);

-- COLA DE PROCESAMIENTO OPTIMIZADA (Partial Index):
-- Solo indexa las filas pendientes. Mantiene el índice pequeño y rápido 
-- incluso si la tabla crece a millones de registros históricos.
CREATE INDEX idx_entradas_raw_cola_pendiente 
    ON tbl_entradas_raw (id_entrada_raw) 
    WHERE procesado = FALSE;

-- BÚSQUEDAS OPERATIVAS (Forensics):
-- Índices B-Tree estándar para filtrado rápido en dashboard de auditoría.
CREATE INDEX idx_entradas_raw_oc ON tbl_entradas_raw (orden_compra);
CREATE INDEX idx_entradas_raw_factura ON tbl_entradas_raw (folio_factura);
CREATE INDEX idx_entradas_raw_fecha ON tbl_entradas_raw (fecha_entrada);

-- --------------------------------------------------------------------------------------
-- 4. DOCUMENTACIÓN
-- --------------------------------------------------------------------------------------
COMMENT ON TABLE tbl_entradas_raw IS 'Repositorio de ingesta SAF-GDA. Registros inmutables validados por Hash.';
COMMENT ON COLUMN tbl_entradas_raw.registro_hash IS 'SHA-256 del registro. Llave única de integridad.';
COMMENT ON COLUMN tbl_entradas_raw.procesado IS 'Bandera de estado ETL. FALSE indica pendiente de procesamiento.';

COMMIT;
