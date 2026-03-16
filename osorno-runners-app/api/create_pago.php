<?php
declare(strict_types=1);

require __DIR__ . '/_init.php';
require __DIR__ . '/db.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    respond(['ok' => false, 'error' => 'Metodo no permitido'], 405);
}

$body = json_input();
$rut = strtoupper(trim((string)($body['rut'] ?? '')));
$fechaPago = (string)($body['fechaPago'] ?? '');
$totalPago = (float)($body['totalPago'] ?? 0);
$valorCuota = (float)($body['valorCuota'] ?? 0);
$mesesCantidad = max(1, (int)($body['mesesCantidad'] ?? 1));
$periodoInicio = (string)($body['periodoInicio'] ?? '');
$periodos = is_array($body['periodos'] ?? null) ? normalize_periods($body['periodos']) : [];
$observacion = trim((string)($body['observacion'] ?? ''));
$origen = (string)($body['origen'] ?? 'manual');
$tipoCuota = normalize_tipo_cuota((string)($body['tipoCuota'] ?? 'ACTIVO'));

if ($rut === '' || $fechaPago === '' || $totalPago <= 0 || $valorCuota <= 0) {
    respond(['ok' => false, 'error' => 'Datos incompletos para registrar pago'], 422);
}

if ($tipoCuota === 'BECADO') {
    respond(['ok' => false, 'error' => 'Socio becado: no corresponde registrar cobro de cuota'], 422);
}

try {
    $pdo = db();
    $socio = find_socio_by_rut($pdo, $rut);
    if (!$socio) {
        respond(['ok' => false, 'error' => 'No existe socio para el RUT indicado'], 404);
    }

    $pdo->beginTransaction();

    $sql = 'INSERT INTO pagos (
                id_socio, rut, nombre_snapshot, anio, sexo, estado, situacion,
                fecha_pago, total_pago, valor_cuota, tipo_cuota, meses_cantidad, meses_detalle,
                observacion, origen
            ) VALUES (
                :id_socio, :rut, :nombre_snapshot, :anio, :sexo, :estado, :situacion,
                :fecha_pago, :total_pago, :valor_cuota, :tipo_cuota, :meses_cantidad, :meses_detalle,
                :observacion, :origen
            )';

    $periods = !empty($periodos) ? $periodos : build_periods($periodoInicio, $mesesCantidad);
    $mesesCantidad = max(1, count($periods) > 0 ? count($periods) : $mesesCantidad);
    $mesesDetalle = implode(', ', $periods);

    $stmt = $pdo->prepare($sql);
    $stmt->execute([
        ':id_socio' => $socio['id_socio'],
        ':rut' => $socio['rut'],
        ':nombre_snapshot' => $socio['nombre'],
        ':anio' => $socio['anio'],
        ':sexo' => $socio['sexo'],
        ':estado' => $socio['estado'],
        ':situacion' => 'PAGADO',
        ':fecha_pago' => $fechaPago,
        ':total_pago' => $totalPago,
        ':valor_cuota' => $valorCuota,
        ':tipo_cuota' => $tipoCuota,
        ':meses_cantidad' => $mesesCantidad,
        ':meses_detalle' => $mesesDetalle,
        ':observacion' => $observacion,
        ':origen' => $origen,
    ]);

    $idPago = (int)$pdo->lastInsertId();

    if (!empty($periods)) {
        $insertPeriodo = $pdo->prepare(
            'INSERT IGNORE INTO pago_meses (id_pago, id_socio, rut, periodo)
             VALUES (:id_pago, :id_socio, :rut, :periodo)'
        );
        foreach ($periods as $periodo) {
            $insertPeriodo->execute([
                ':id_pago' => $idPago,
                ':id_socio' => $socio['id_socio'],
                ':rut' => $socio['rut'],
                ':periodo' => $periodo,
            ]);
        }
    }

    $pdo->commit();
    respond(['ok' => true, 'idPago' => $idPago]);
} catch (PDOException $e) {
    if (isset($pdo) && $pdo instanceof PDO && $pdo->inTransaction()) {
        $pdo->rollBack();
    }
    if ((int)$e->getCode() === 23000) {
        respond(['ok' => false, 'error' => 'Pago duplicado'], 409);
    }
    respond(['ok' => false, 'error' => $e->getMessage()], 500);
} catch (Throwable $e) {
    if (isset($pdo) && $pdo instanceof PDO && $pdo->inTransaction()) {
        $pdo->rollBack();
    }
    respond(['ok' => false, 'error' => $e->getMessage()], 500);
}
