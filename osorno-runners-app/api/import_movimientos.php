<?php
declare(strict_types=1);

require __DIR__ . '/_init.php';
require __DIR__ . '/db.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    respond(['ok' => false, 'error' => 'Metodo no permitido'], 405);
}

$body = json_input();
$movimientos = is_array($body['movimientos'] ?? null) ? $body['movimientos'] : [];

try {
    $pdo = db();

    $findSocio = $pdo->prepare('SELECT id_socio FROM socios WHERE rut = :rut LIMIT 1');
    $findDuplicate = $pdo->prepare(
        'SELECT id_movimiento FROM movimientos_bancarios
         WHERE fecha = :fecha
           AND monto = :monto
           AND descripcion = :descripcion
           AND cargo_abono = :cargo_abono
         LIMIT 1'
    );

    $insert = $pdo->prepare(
        'INSERT INTO movimientos_bancarios (
            fecha, monto, descripcion, cargo_abono, rut_detectado, id_socio,
            categoria, tipo_cuota, valor_cuota, meses_cantidad, periodo_inicio, estado
         ) VALUES (
            :fecha, :monto, :descripcion, :cargo_abono, :rut_detectado, :id_socio,
            :categoria, :tipo_cuota, :valor_cuota, :meses_cantidad, :periodo_inicio, :estado
         )'
    );

    $created = 0;
    foreach ($movimientos as $m) {
        $fecha = trim((string)($m['fecha'] ?? ''));
        $monto = (float)($m['monto'] ?? 0);
        $descripcion = trim((string)($m['descripcion'] ?? ''));
        $cargoAbono = strtoupper(trim((string)($m['cargoAbono'] ?? '')));
        if ($fecha === '' || $descripcion === '' || !in_array($cargoAbono, ['A', 'C'], true) || $monto === 0.0) {
            continue;
        }

        $findDuplicate->execute([
            ':fecha' => $fecha,
            ':monto' => $monto,
            ':descripcion' => $descripcion,
            ':cargo_abono' => $cargoAbono,
        ]);
        if ($findDuplicate->fetch()) {
            continue;
        }

        $rut = strtoupper(trim((string)($m['rut'] ?? '')));
        $idSocio = null;
        if ($rut !== '') {
            $findSocio->execute([':rut' => $rut]);
            $row = $findSocio->fetch();
            if ($row) {
                $idSocio = (int)$row['id_socio'];
            }
        }

        $periodos = is_array($m['periodos'] ?? null) ? normalize_periods($m['periodos']) : [];
        $mesesCantidad = !empty($periodos) ? count($periodos) : max(1, (int)($m['mesesCantidad'] ?? 1));
        $periodoInicio = !empty($periodos) ? $periodos[0] : (string)($m['periodoInicio'] ?? '');

        $tipoCuota = normalize_tipo_cuota((string)($m['tipoCuota'] ?? 'ACTIVO'));
        $insert->execute([
            ':fecha' => $fecha,
            ':monto' => $monto,
            ':descripcion' => $descripcion,
            ':cargo_abono' => $cargoAbono,
            ':rut_detectado' => $rut !== '' ? $rut : null,
            ':id_socio' => $idSocio,
            ':categoria' => (string)($m['categoria'] ?? 'Cuota'),
            ':tipo_cuota' => $tipoCuota,
            ':valor_cuota' => (float)($m['valorCuota'] ?? cuota_por_tipo($tipoCuota)),
            ':meses_cantidad' => $mesesCantidad,
            ':periodo_inicio' => $periodoInicio,
            ':estado' => 'pendiente',
        ]);
        $created++;
    }

    respond(['ok' => true, 'movimientosNuevos' => $created]);
} catch (Throwable $e) {
    respond(['ok' => false, 'error' => $e->getMessage()], 500);
}
