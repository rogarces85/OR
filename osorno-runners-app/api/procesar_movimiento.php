<?php
declare(strict_types=1);

require __DIR__ . '/_init.php';
require __DIR__ . '/db.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    respond(['ok' => false, 'error' => 'Metodo no permitido'], 405);
}

$body = json_input();
$idMovimiento = (int)($body['id'] ?? 0);
$categoria = trim((string)($body['categoria'] ?? ''));
$tipoCuota = normalize_tipo_cuota((string)($body['tipoCuota'] ?? 'ACTIVO'));
$mesesCantidad = max(1, (int)($body['mesesCantidad'] ?? 1));
$periodoInicio = trim((string)($body['periodoInicio'] ?? ''));
$periodosInput = is_array($body['periodos'] ?? null) ? normalize_periods($body['periodos']) : [];

if ($idMovimiento <= 0) {
    respond(['ok' => false, 'error' => 'Movimiento invalido'], 422);
}

try {
    $pdo = db();
    $pdo->beginTransaction();

    $getMov = $pdo->prepare('SELECT * FROM movimientos_bancarios WHERE id_movimiento = :id LIMIT 1 FOR UPDATE');
    $getMov->execute([':id' => $idMovimiento]);
    $mov = $getMov->fetch();
    if (!$mov) {
        $pdo->rollBack();
        respond(['ok' => false, 'error' => 'Movimiento no encontrado'], 404);
    }
    if ($mov['estado'] === 'procesado') {
        $pdo->rollBack();
        respond(['ok' => true, 'status' => 'ya_procesado', 'message' => 'Movimiento ya estaba procesado']);
    }

    if ($categoria === '') {
        $categoria = (string)$mov['categoria'];
    }

    if (($body['tipoCuota'] ?? '') === '') {
        $tipoCuota = normalize_tipo_cuota((string)($mov['tipo_cuota'] ?? (($mov['categoria'] === 'Cuota') ? 'ACTIVO' : 'OTRO')));
    }

    $periods = !empty($periodosInput)
        ? $periodosInput
        : build_periods($periodoInicio !== '' ? $periodoInicio : date('Y-m', strtotime((string)$mov['fecha'])), $mesesCantidad);
    if (empty($periods)) {
        $periods = [date('Y-m', strtotime((string)$mov['fecha']))];
    }
    $mesesCantidad = count($periods);
    $periodoInicio = $periods[0];

    $updMovMeta = $pdo->prepare(
        'UPDATE movimientos_bancarios
         SET categoria = :categoria, tipo_cuota = :tipo_cuota, meses_cantidad = :meses_cantidad, periodo_inicio = :periodo_inicio
         WHERE id_movimiento = :id'
    );
    $updMovMeta->execute([
        ':categoria' => $categoria,
        ':tipo_cuota' => $tipoCuota,
        ':meses_cantidad' => $mesesCantidad,
        ':periodo_inicio' => $periodoInicio,
        ':id' => $idMovimiento,
    ]);

    $idPagoGenerado = null;
    $resultStatus = 'procesado';
    $resultMessage = 'Movimiento procesado';

    if ($categoria === 'Cuota') {
        $rut = (string)$mov['rut_detectado'];
        $socio = find_socio_by_rut($pdo, $rut);
        if (!$socio) {
            $pdo->rollBack();
            respond(['ok' => false, 'error' => 'No existe socio para registrar cuota'], 422);
        }

        if ($tipoCuota === 'BECADO') {
            $pdo->rollBack();
            respond(['ok' => false, 'error' => 'Socio becado: recategoriza este abono como Otro ingreso'], 422);
        }

        $mesesDetalle = implode(', ', $periods);

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

        $totalPago = abs((float)$mov['monto']);
        $valorCuota = max(1, (float)($mov['valor_cuota'] ?? cuota_por_tipo($tipoCuota)));
        $insertPago->execute([
            ':id_socio' => $socio['id_socio'],
            ':rut' => $socio['rut'],
            ':nombre_snapshot' => $socio['nombre'],
            ':anio' => $socio['anio'],
            ':sexo' => $socio['sexo'],
            ':estado' => $socio['estado'],
            ':situacion' => 'PAGADO',
            ':fecha_pago' => $mov['fecha'],
            ':total_pago' => $totalPago,
            ':valor_cuota' => $valorCuota,
            ':tipo_cuota' => $tipoCuota,
            ':meses_cantidad' => $mesesCantidad,
            ':meses_detalle' => $mesesDetalle,
            ':observacion' => 'Importado desde banco. ' . $mov['descripcion'],
            ':origen' => 'banco',
        ]);

        if ($insertPago->rowCount() === 0) {
            $findPago = $pdo->prepare(
                "SELECT id_pago FROM pagos WHERE rut = :rut AND fecha_pago = :fecha_pago
                 AND total_pago = :total_pago AND origen = 'banco' LIMIT 1"
            );
            $findPago->execute([
                ':rut' => $socio['rut'],
                ':fecha_pago' => $mov['fecha'],
                ':total_pago' => $totalPago,
            ]);
            $existing = $findPago->fetch();
            $idPagoGenerado = $existing ? (int)$existing['id_pago'] : null;
            $resultStatus = 'duplicado_pago';
            $resultMessage = 'Pago ya existia, se vinculo al registro existente';
        } else {
            $idPagoGenerado = (int)$pdo->lastInsertId();
            $resultStatus = 'pago_creado';
            $resultMessage = 'Pago creado correctamente';
        }

        if ($idPagoGenerado && !empty($periods)) {
            $insPeriodo = $pdo->prepare(
                'INSERT IGNORE INTO pago_meses (id_pago, id_socio, rut, periodo)
                 VALUES (:id_pago, :id_socio, :rut, :periodo)'
            );
            foreach ($periods as $periodo) {
                $insPeriodo->execute([
                    ':id_pago' => $idPagoGenerado,
                    ':id_socio' => $socio['id_socio'],
                    ':rut' => $socio['rut'],
                    ':periodo' => $periodo,
                ]);
            }
        }
    } elseif ($categoria === 'Otro ingreso') {
        $ins = $pdo->prepare(
            'INSERT INTO otros_ingresos (fecha, monto, rut, descripcion, id_movimiento)
             VALUES (:fecha, :monto, :rut, :descripcion, :id_movimiento)'
        );
        $ins->execute([
            ':fecha' => $mov['fecha'],
            ':monto' => abs((float)$mov['monto']),
            ':rut' => $mov['rut_detectado'] ?: null,
            ':descripcion' => $mov['descripcion'],
            ':id_movimiento' => $idMovimiento,
        ]);
        $resultStatus = 'otro_ingreso_creado';
        $resultMessage = 'Movimiento guardado como otro ingreso';
    } elseif ($categoria === 'Egreso') {
        $ins = $pdo->prepare(
            'INSERT INTO egresos (fecha, monto, descripcion, id_movimiento)
             VALUES (:fecha, :monto, :descripcion, :id_movimiento)'
        );
        $ins->execute([
            ':fecha' => $mov['fecha'],
            ':monto' => abs((float)$mov['monto']),
            ':descripcion' => $mov['descripcion'],
            ':id_movimiento' => $idMovimiento,
        ]);
        $resultStatus = 'egreso_creado';
        $resultMessage = 'Movimiento guardado como egreso';
    }

    $updFinal = $pdo->prepare(
        'UPDATE movimientos_bancarios
         SET estado = :estado, id_pago_generado = :id_pago_generado
         WHERE id_movimiento = :id'
    );
    $updFinal->execute([
        ':estado' => 'procesado',
        ':id_pago_generado' => $idPagoGenerado,
        ':id' => $idMovimiento,
    ]);

    $pdo->commit();
    respond(['ok' => true, 'status' => $resultStatus, 'message' => $resultMessage, 'id' => $idMovimiento]);
} catch (Throwable $e) {
    if (isset($pdo) && $pdo instanceof PDO && $pdo->inTransaction()) {
        $pdo->rollBack();
    }
    respond(['ok' => false, 'error' => $e->getMessage()], 500);
}
