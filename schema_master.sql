/*
 * ======================================================================================
 * SAF-GDA: ESQUEMA MAESTRO (PRODUCCIÓN)
 * Basado en: DOCUMENTACIÓN MAESTRA - SECCIÓN 6
 * ======================================================================================
 */

BEGIN;

-- 1. TABLA DE UBICACIÓN FÍSICA (Topografía)
CREATE TABLE IF NOT EXISTS ubicacion_fisica (
    id SERIAL PRIMARY KEY,
    edificio VARCHAR(50),
    mueble VARCHAR(50),      -- Ej: "Archivero 1"
    contenedor VARCHAR(50),  -- Ej: "Caja Leitz 45"
    rango_folios VARCHAR(50),-- Ej: "3400-3499"
    capacidad_max INT,
    ocupacion_actual INT DEFAULT 0
);

-- 2. TABLA MAESTRA DE DOCUMENTOS
CREATE TABLE IF NOT EXISTS documentos_fiscales (
    uuid_interno UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- CLAVES DE NEGOCIO
    folio_rb INT,                   -- Vinculación Física (Sello)
    uuid_sat VARCHAR(36),           -- Vinculación Fiscal (QR/OCR) - UNIQUE
    rfc_emisor VARCHAR(13),         -- Dato Real (VISIBLE)
    razon_social VARCHAR(255),      -- Dato Real (VISIBLE)
    monto_total DECIMAL(12,2),
    fecha_emision DATE,

    -- UBICACIÓN Y CLASIFICACIÓN
    ubicacion_id INT REFERENCES ubicacion_fisica(id),
    serie_documental VARCHAR(20) DEFAULT '4C.3',

    -- INTEGRIDAD
    hash_sha256_original CHAR(64),  -- Hash del archivo crudo
    hash_sha256_final CHAR(64),     -- Hash del PDF procesado

    -- ESTADO Y CONTROL
    estado_proceso VARCHAR(20),     -- 'CONCILIADO', 'INCIDENCIA', 'PENDIENTE'
    notas_auditor TEXT,
    lote_origen VARCHAR(100),

    fecha_registro TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para búsqueda rápida
CREATE INDEX IF NOT EXISTS idx_rb_doc ON documentos_fiscales(folio_rb);
CREATE INDEX IF NOT EXISTS idx_uuid_sat ON documentos_fiscales(uuid_sat);

COMMIT;