<?php
declare(strict_types=1);

require __DIR__ . '/_init.php';
require __DIR__ . '/db.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    respond(['ok' => false, 'error' => 'Metodo no permitido'], 405);
}

$body = json_input();
$id = (int)($body['id'] ?? 0);
$rut = strtoupper(trim((string)($body['rut'] ?? '')));
$categoria = trim((string)($body['categoria'] ?? 'Cuota'));
$tipoCuota = normalize_tipo_cuota((string)($body['tipoCuota'] ?? 'ACTIVO'));
$valorCuota = (float)($body['valorCuota'] ?? cuota_por_tipo($tipoCuota));
$mesesCantidad = max(1, (int)($body['mesesCantidad'] ?? 1));
$periodoInicio = trim((string)($body['periodoInicio'] ?? ''));

if ($id <= 0) {
    respond(['ok' => false, 'error' => 'ID de movimiento invalido'], 422);
}

try {
    $pdo = db();
    $socio = null;
    if ($rut !== '') {
      $socio = find_socio_by_rut($pdo, $rut);
      if (!$socio) {
          respond(['ok' => false, 'error' => 'RUT no existe en socios'], 422);
      }
    }

    $stmt = $pdo->prepare(
        'UPDATE movimientos_bancarios
         SET rut_detectado = :rut, id_socio = :id_socio,
             categoria = :categoria, tipo_cuota = :tipo_cuota,
             valor_cuota = :valor_cuota, meses_cantidad = :meses_cantidad,
             periodo_inicio = :periodo_inicio
         WHERE id_movimiento = :id'
    );

    $stmt->execute([
        ':rut' => $rut !== '' ? $rut : null,
        ':id_socio' => $socio ? (int)$socio['id_socio'] : null,
        ':categoria' => $categoria,
        ':tipo_cuota' => $tipoCuota,
        ':valor_cuota' => $valorCuota,
        ':meses_cantidad' => $mesesCantidad,
        ':periodo_inicio' => $periodoInicio,
        ':id' => $id,
    ]);

    respond(['ok' => true]);
} catch (Throwable $e) {
    respond(['ok' => false, 'error' => $e->getMessage()], 500);
}
