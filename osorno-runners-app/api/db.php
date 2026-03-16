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

function fetch_bootstrap(PDO $pdo): array
{
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
    ];
}
