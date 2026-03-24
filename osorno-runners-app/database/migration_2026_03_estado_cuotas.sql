USE osorno_runners;

CREATE TABLE IF NOT EXISTS estado_cuotas_imports (
  id_import BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  source_name VARCHAR(190) NOT NULL,
  imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_estado_imported_at (imported_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS estado_cuotas_detalle (
  id_detalle BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  id_import BIGINT UNSIGNED NOT NULL,
  periodo_anio SMALLINT NOT NULL,
  hoja_nombre VARCHAR(120) NOT NULL,
  integrante_nombre VARCHAR(160) NOT NULL,
  rut VARCHAR(12) NULL,
  estado_club VARCHAR(30) NULL,
  deuda_arrastre DECIMAL(12,0) NOT NULL DEFAULT 0,
  total_pagado DECIMAL(12,0) NOT NULL DEFAULT 0,
  deuda_anual DECIMAL(12,0) NOT NULL DEFAULT 0,
  meses_pagados INT UNSIGNED NOT NULL DEFAULT 0,
  meses_actividad INT UNSIGNED NOT NULL DEFAULT 0,
  notas_json LONGTEXT NULL,
  meses_json LONGTEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_estado_detalle_import
    FOREIGN KEY (id_import) REFERENCES estado_cuotas_imports(id_import)
    ON UPDATE CASCADE
    ON DELETE CASCADE,
  KEY idx_estado_detalle_import (id_import),
  KEY idx_estado_detalle_anio (periodo_anio),
  KEY idx_estado_detalle_rut (rut)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
