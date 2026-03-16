<?php
declare(strict_types=1);

require __DIR__ . '/_init.php';
require __DIR__ . '/db.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    respond(['ok' => false, 'error' => 'Metodo no permitido'], 405);
}

$body = json_input();
$socios = is_array($body['socios'] ?? null) ? $body['socios'] : [];
$pagos = is_array($body['pagos'] ?? null) ? $body['pagos'] : [];

try {
    $pdo = db();
    $pdo->beginTransaction();

    $upsertSocio = $pdo->prepare(
        'INSERT INTO socios (rut, nombre, anio, sexo, estado)
         VALUES (:rut, :nombre, :anio, :sexo, :estado)
         ON DUPLICATE KEY UPDATE
            nombre = VALUES(nombre),
            anio = VALUES(anio),
            sexo = VALUES(sexo),
            estado = VALUES(estado)'
    );

    $countSocios = 0;
    foreach ($socios as $s) {
        $rut = strtoupper(trim((string)($s['rut'] ?? '')));
        $nombre = trim((string)($s['nombre'] ?? ''));
        if ($rut === '' || $nombre === '') {
            continue;
        }
        $upsertSocio->execute([
            ':rut' => $rut,
            ':nombre' => $nombre,
            ':anio' => (int)($s['anio'] ?? date('Y')),
            ':sexo' => trim((string)($s['sexo'] ?? '')),
            ':estado' => trim((string)($s['estado'] ?? '')),
        ]);
        $countSocios++;
    }

    $getSocioId = $pdo->prepare('SELECT id_socio, rut, nombre, anio, sexo, estado FROM socios WHERE rut = :rut LIMIT 1');
    $insertPago = $pdo->prepare(
        'INSERT IGNORE INTO pagos (
            id_socio, rut, nombre_snapshot, anio, sexo, estado, situacion,
            fecha_pago, total_pago, valor_cuota, tipo_cuota, meses_cantidad, meses_detalle,
            observacion, origen
         ) VALUES (
            :id_socio, :rut, :nombre_snapshot, :anio, :sexo, :estado, :situacion,
            :fecha_pago, :total_pago, :valor_cuota, :tipo_cuota, :meses_cantidad, :meses_detalle,
            :observacion, :origen
         )'
    );

    $countPagos = 0;
    foreach ($pagos as $p) {
        $rut = strtoupper(trim((string)($p['rut'] ?? '')));
        $fechaPago = trim((string)($p['fechaPago'] ?? ''));
        $totalPago = (float)($p['totalPago'] ?? 0);
        if ($rut === '' || $fechaPago === '' || $totalPago <= 0) {
            continue;
        }
        $getSocioId->execute([':rut' => $rut]);
        $socio = $getSocioId->fetch();
        if (!$socio) {
            continue;
        }

        $tipoCuota = normalize_tipo_cuota((string)($p['tipoCuota'] ?? $socio['estado'] ?? 'ACTIVO'));
        $valorCuota = (float)($p['valorCuota'] ?? cuota_por_tipo($tipoCuota));
        $insertPago->execute([
            ':id_socio' => (int)$socio['id_socio'],
            ':rut' => $socio['rut'],
            ':nombre_snapshot' => $socio['nombre'],
            ':anio' => (int)$socio['anio'],
            ':sexo' => $socio['sexo'],
            ':estado' => $socio['estado'],
            ':situacion' => trim((string)($p['situacion'] ?? 'PAGADO')),
            ':fecha_pago' => $fechaPago,
            ':total_pago' => $totalPago,
            ':valor_cuota' => max(0, $valorCuota),
            ':tipo_cuota' => $tipoCuota,
            ':meses_cantidad' => max(1, (int)($p['mesesCantidad'] ?? 1)),
            ':meses_detalle' => trim((string)($p['mesesDetalle'] ?? '')),
            ':observacion' => trim((string)($p['observacion'] ?? '')),
            ':origen' => trim((string)($p['origen'] ?? 'historico')),
        ]);
        if ($insertPago->rowCount() > 0) {
            $countPagos++;
        }
    }

    $pdo->commit();
    respond(['ok' => true, 'sociosProcesados' => $countSocios, 'pagosNuevos' => $countPagos]);
} catch (Throwable $e) {
    if (isset($pdo) && $pdo instanceof PDO && $pdo->inTransaction()) {
        $pdo->rollBack();
    }
    respond(['ok' => false, 'error' => $e->getMessage()], 500);
}
