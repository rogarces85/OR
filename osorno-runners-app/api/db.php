<?php
declare(strict_types=1);

function db(): PDO
{
    static $pdo = null;
    if ($pdo instanceof PDO) {
        return $pdo;
    }

    $host = 'localhost';
    $port = 3306;
    $dbname = 'osorno_runners';
    $user = 'root';
    $pass = '';

    $dsn = "mysql:host={$host};port={$port};dbname={$dbname};charset=utf8mb4";
    $pdo = new PDO($dsn, $user, $pass, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);

    return $pdo;
}

function build_periods(string $startPeriod, int $count): array
{
    if (!preg_match('/^\d{4}-\d{2}$/', $startPeriod) || $count < 1) {
        return [];
    }
    [$year, $month] = array_map('intval', explode('-', $startPeriod));
    $periods = [];
    for ($i = 0; $i < $count; $i++) {
        $ts = strtotime(sprintf('%04d-%02d-01 +%d month', $year, $month, $i));
        if ($ts !== false) {
            $periods[] = date('Y-m', $ts);
        }
    }
    return $periods;
}

function normalize_periods(array $periods): array
{
    $clean = [];
    foreach ($periods as $period) {
        $value = trim((string)$period);
        if (preg_match('/^\d{4}-\d{2}$/', $value) === 1) {
            $clean[] = $value;
        }
    }
    $clean = array_values(array_unique($clean));
    sort($clean);
    return $clean;
}

function find_socio_by_rut(PDO $pdo, string $rut): ?array
{
    $stmt = $pdo->prepare('SELECT * FROM socios WHERE rut = :rut LIMIT 1');
    $stmt->execute([':rut' => $rut]);
    $row = $stmt->fetch();
    return $row ?: null;
}

function normalize_tipo_cuota(?string $tipo): string
{
    $value = strtoupper(trim((string)$tipo));
    $allowed = ['ACTIVO', 'MEMBRESIA', 'BECADO', 'OTRO'];
    return in_array($value, $allowed, true) ? $value : 'ACTIVO';
}

function cuota_por_tipo(string $tipoCuota): float
{
    $tipo = normalize_tipo_cuota($tipoCuota);
    return match ($tipo) {
        'ACTIVO' => 15000,
        'MEMBRESIA' => 5000,
        'BECADO' => 0,
        default => 15000,
    };
}

function ensure_estado_cuotas_tables(PDO $pdo): void
{
    $pdo->exec(
        "CREATE TABLE IF NOT EXISTS estado_cuotas_imports (
            id_import BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            source_name VARCHAR(190) NOT NULL,
            imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            KEY idx_estado_imported_at (imported_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    );

    $pdo->exec(
        "CREATE TABLE IF NOT EXISTS estado_cuotas_detalle (
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    );
}

function fetch_latest_estado_cuotas(PDO $pdo): ?array
{
    ensure_estado_cuotas_tables($pdo);

    $import = $pdo->query(
        'SELECT id_import AS idImport, source_name AS sourceName, imported_at AS importedAt
         FROM estado_cuotas_imports
         ORDER BY imported_at DESC, id_import DESC
         LIMIT 1'
    )->fetch();

    if (!$import) {
        return null;
    }

    $stmt = $pdo->prepare(
        'SELECT periodo_anio AS year, hoja_nombre AS sheetName, integrante_nombre AS name,
                rut, estado_club AS socioEstado, deuda_arrastre AS carryDebt,
                total_pagado AS paidTotal, deuda_anual AS debt, meses_pagados AS paidMonths,
                meses_actividad AS activityMonths, notas_json AS notesJson, meses_json AS monthStatesJson
         FROM estado_cuotas_detalle
         WHERE id_import = :id_import
         ORDER BY periodo_anio ASC, integrante_nombre ASC'
    );
    $stmt->execute([':id_import' => (int)$import['idImport']]);
    $rows = $stmt->fetchAll();

    $sheets = [];
    foreach ($rows as $row) {
        $year = (int)$row['year'];
        if (!isset($sheets[$year])) {
            $sheets[$year] = [
                'year' => $year,
                'sheetName' => $row['sheetName'],
                'entries' => [],
                'totals' => [
                    'members' => 0,
                    'paidTotal' => 0,
                    'carryDebtTotal' => 0,
                    'debtTotal' => 0,
                    'withCarryDebt' => 0,
                    'withDebt' => 0,
                ],
            ];
        }

        $entry = [
            'id' => $year . '-' . preg_replace('/[^A-Z0-9]+/', '-', strtoupper((string)$row['name'])),
            'year' => $year,
            'name' => $row['name'],
            'rut' => $row['rut'] ?? '',
            'socioEstado' => $row['socioEstado'] ?? '',
            'linkedName' => $row['name'],
            'carryDebt' => (float)$row['carryDebt'],
            'paidTotal' => (float)$row['paidTotal'],
            'debt' => (float)$row['debt'],
            'paidMonths' => (int)$row['paidMonths'],
            'activityMonths' => (int)$row['activityMonths'],
            'notes' => json_decode((string)($row['notesJson'] ?? '[]'), true) ?: [],
            'monthStates' => json_decode((string)($row['monthStatesJson'] ?? '[]'), true) ?: [],
        ];

        $sheets[$year]['entries'][] = $entry;
        $sheets[$year]['totals']['members']++;
        $sheets[$year]['totals']['paidTotal'] += (float)$entry['paidTotal'];
        $sheets[$year]['totals']['carryDebtTotal'] += (float)$entry['carryDebt'];
        $sheets[$year]['totals']['debtTotal'] += (float)$entry['debt'];
        if ((float)$entry['carryDebt'] > 0) {
            $sheets[$year]['totals']['withCarryDebt']++;
        }
        if ((float)$entry['debt'] > 0) {
            $sheets[$year]['totals']['withDebt']++;
        }
    }

    return [
        'sourceName' => $import['sourceName'],
        'importedAt' => $import['importedAt'],
        'sheets' => array_values($sheets),
    ];
}

function fetch_bootstrap(PDO $pdo): array
{
    $estadoCuotas = fetch_latest_estado_cuotas($pdo);
    $socios = $pdo->query(
        'SELECT rut, nombre, anio, sexo, estado
         FROM socios ORDER BY nombre ASC'
    )->fetchAll();

    $pagos = $pdo->query(
        'SELECT id_pago AS id, rut, nombre_snapshot AS nombre, anio, sexo, estado, situacion,
                fecha_pago AS fechaPago, total_pago AS totalPago, valor_cuota AS valorCuota,
                tipo_cuota AS tipoCuota, meses_cantidad AS mesesCantidad, meses_detalle AS mesesDetalle,
                observacion, origen, created_at AS createdAt
         FROM pagos ORDER BY fecha_pago DESC, id_pago DESC LIMIT 3000'
    )->fetchAll();

    $movimientos = $pdo->query(
        "SELECT id_movimiento AS id, fecha, monto, descripcion, cargo_abono AS cargoAbono,
                rut_detectado AS rut, categoria, COALESCE(tipo_cuota, 'ACTIVO') AS tipoCuota,
                COALESCE(valor_cuota, 15000) AS valorCuota,
                COALESCE(meses_cantidad, 1) AS mesesCantidad, periodo_inicio AS periodoInicio,
                estado,
                (SELECT nombre FROM socios s WHERE s.id_socio = mb.id_socio) AS socioNombre
         FROM movimientos_bancarios mb
         ORDER BY fecha DESC, id_movimiento DESC LIMIT 3000"
    )->fetchAll();

    $otrosIngresos = $pdo->query(
        'SELECT id_otro_ingreso AS id, fecha, monto, rut, descripcion
         FROM otros_ingresos ORDER BY fecha DESC, id_otro_ingreso DESC LIMIT 1000'
    )->fetchAll();

    $egresos = $pdo->query(
        'SELECT id_egreso AS id, fecha, monto, descripcion
         FROM egresos ORDER BY fecha DESC, id_egreso DESC LIMIT 1000'
    )->fetchAll();

    return [
        'socios' => $socios,
        'pagos' => $pagos,
        'movimientos' => $movimientos,
        'otrosIngresos' => $otrosIngresos,
        'egresos' => $egresos,
        'estadoCuotas' => $estadoCuotas,
    ];
}
