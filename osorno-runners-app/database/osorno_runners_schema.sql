CREATE DATABASE IF NOT EXISTS osorno_runners
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE osorno_runners;

CREATE TABLE IF NOT EXISTS socios (
  id_socio INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  rut VARCHAR(12) NOT NULL,
  nombre VARCHAR(120) NOT NULL,
  anio SMALLINT NOT NULL,
  sexo VARCHAR(20) NULL,
  estado VARCHAR(30) NULL,
  activo TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_socios_rut (rut),
  KEY idx_socios_nombre (nombre)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pagos (
  id_pago BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  codigo_pago VARCHAR(30) NULL,
  id_socio INT UNSIGNED NOT NULL,
  rut VARCHAR(12) NOT NULL,
  nombre_snapshot VARCHAR(120) NOT NULL,
  anio SMALLINT NOT NULL,
  sexo VARCHAR(20) NULL,
  estado VARCHAR(30) NULL,
  situacion VARCHAR(30) NULL,
  fecha_pago DATE NOT NULL,
  total_pago DECIMAL(12,0) NOT NULL,
  valor_cuota DECIMAL(12,0) NOT NULL,
  tipo_cuota ENUM('ACTIVO','MEMBRESIA','BECADO','OTRO') NOT NULL DEFAULT 'ACTIVO',
  meses_cantidad INT UNSIGNED NOT NULL,
  meses_detalle VARCHAR(120) NULL,
  observacion VARCHAR(255) NULL,
  origen ENUM('manual','banco','historico') NOT NULL DEFAULT 'manual',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_pagos_socio
    FOREIGN KEY (id_socio) REFERENCES socios(id_socio)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,
  KEY idx_pagos_rut (rut),
  KEY idx_pagos_fecha (fecha_pago),
  KEY idx_pagos_anio (anio),
  KEY idx_pagos_origen (origen),
  UNIQUE KEY uq_pago_dedupe (rut, fecha_pago, total_pago, origen)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pago_meses (
  id_pago_mes BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  id_pago BIGINT UNSIGNED NOT NULL,
  id_socio INT UNSIGNED NOT NULL,
  rut VARCHAR(12) NOT NULL,
  periodo CHAR(7) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_pago_meses_pago
    FOREIGN KEY (id_pago) REFERENCES pagos(id_pago)
    ON UPDATE CASCADE
    ON DELETE CASCADE,
  CONSTRAINT fk_pago_meses_socio
    FOREIGN KEY (id_socio) REFERENCES socios(id_socio)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,
  UNIQUE KEY uq_rut_periodo (rut, periodo),
  KEY idx_pago_meses_periodo (periodo)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS movimientos_bancarios (
  id_movimiento BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  fecha DATE NOT NULL,
  monto DECIMAL(12,0) NOT NULL,
  descripcion VARCHAR(255) NOT NULL,
  cargo_abono ENUM('A','C') NOT NULL,
  rut_detectado VARCHAR(12) NULL,
  id_socio INT UNSIGNED NULL,
  categoria ENUM('Cuota','Otro ingreso','Egreso') NOT NULL,
  tipo_cuota ENUM('ACTIVO','MEMBRESIA','BECADO','OTRO') NULL,
  valor_cuota DECIMAL(12,0) NULL,
  meses_cantidad INT UNSIGNED NULL,
  periodo_inicio CHAR(7) NULL,
  estado ENUM('pendiente','procesado') NOT NULL DEFAULT 'pendiente',
  id_pago_generado BIGINT UNSIGNED NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_movimientos_socio
    FOREIGN KEY (id_socio) REFERENCES socios(id_socio)
    ON UPDATE CASCADE
    ON DELETE SET NULL,
  CONSTRAINT fk_movimientos_pago
    FOREIGN KEY (id_pago_generado) REFERENCES pagos(id_pago)
    ON UPDATE CASCADE
    ON DELETE SET NULL,
  KEY idx_mov_fecha (fecha),
  KEY idx_mov_rut (rut_detectado),
  KEY idx_mov_estado (estado),
  KEY idx_mov_categoria (categoria)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS otros_ingresos (
  id_otro_ingreso BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  fecha DATE NOT NULL,
  monto DECIMAL(12,0) NOT NULL,
  rut VARCHAR(12) NULL,
  descripcion VARCHAR(255) NOT NULL,
  id_movimiento BIGINT UNSIGNED NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_otros_ingresos_mov
    FOREIGN KEY (id_movimiento) REFERENCES movimientos_bancarios(id_movimiento)
    ON UPDATE CASCADE
    ON DELETE SET NULL,
  KEY idx_otros_ingresos_fecha (fecha)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS egresos (
  id_egreso BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  fecha DATE NOT NULL,
  monto DECIMAL(12,0) NOT NULL,
  descripcion VARCHAR(255) NOT NULL,
  id_movimiento BIGINT UNSIGNED NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_egresos_mov
    FOREIGN KEY (id_movimiento) REFERENCES movimientos_bancarios(id_movimiento)
    ON UPDATE CASCADE
    ON DELETE SET NULL,
  KEY idx_egresos_fecha (fecha)
) ENGINE=InnoDB;

CREATE OR REPLACE VIEW vw_saldos AS
SELECT
  (SELECT IFNULL(SUM(total_pago), 0) FROM pagos) AS total_cuotas,
  (SELECT IFNULL(SUM(monto), 0) FROM otros_ingresos) AS total_otros_ingresos,
  (SELECT IFNULL(SUM(monto), 0) FROM egresos) AS total_egresos,
  ((SELECT IFNULL(SUM(total_pago), 0) FROM pagos)
   + (SELECT IFNULL(SUM(monto), 0) FROM otros_ingresos)
   - (SELECT IFNULL(SUM(monto), 0) FROM egresos)) AS saldo_neto;
