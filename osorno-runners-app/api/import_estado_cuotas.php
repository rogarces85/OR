<?php
declare(strict_types=1);

require __DIR__ . '/_init.php';
require __DIR__ . '/db.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    respond(['ok' => false, 'error' => 'Metodo no permitido'], 405);
}

$body = json_input();
$sourceName = trim((string)($body['sourceName'] ?? 'Estado de cuotas'));
$sheets = is_array($body['sheets'] ?? null) ? $body['sheets'] : [];

if ($sourceName === '' || $sheets === []) {
    respond(['ok' => false, 'error' => 'Faltan datos para guardar el estado anual'], 422);
}

try {
    $pdo = db();
    ensure_estado_cuotas_tables($pdo);
    $pdo->beginTransaction();

    $insertImport = $pdo->prepare(
        'INSERT INTO estado_cuotas_imports (source_name)
         VALUES (:source_name)'
    );
    $insertImport->execute([':source_name' => $sourceName]);
    $idImport = (int)$pdo->lastInsertId();

    $insertDetalle = $pdo->prepare(
        'INSERT INTO estado_cuotas_detalle (
            id_import, periodo_anio, hoja_nombre, integrante_nombre, rut, estado_club,
            deuda_arrastre, total_pagado, deuda_anual, meses_pagados, meses_actividad,
            notas_json, meses_json
         ) VALUES (
            :id_import, :periodo_anio, :hoja_nombre, :integrante_nombre, :rut, :estado_club,
            :deuda_arrastre, :total_pagado, :deuda_anual, :meses_pagados, :meses_actividad,
            :notas_json, :meses_json
         )'
    );

    $savedRows = 0;
    foreach ($sheets as $sheet) {
        $year = (int)($sheet['year'] ?? 0);
        $sheetName = trim((string)($sheet['sheetName'] ?? $year));
        $entries = is_array($sheet['entries'] ?? null) ? $sheet['entries'] : [];
        if ($year < 2000 || $entries === []) {
            continue;
        }

        foreach ($entries as $entry) {
            $name = trim((string)($entry['name'] ?? ''));
            if ($name === '') {
                continue;
            }

            $notes = is_array($entry['notes'] ?? null) ? $entry['notes'] : [];
            $monthStates = is_array($entry['monthStates'] ?? null) ? $entry['monthStates'] : [];

            $insertDetalle->execute([
                ':id_import' => $idImport,
                ':periodo_anio' => $year,
                ':hoja_nombre' => $sheetName,
                ':integrante_nombre' => $name,
                ':rut' => trim((string)($entry['rut'] ?? '')) ?: null,
                ':estado_club' => trim((string)($entry['socioEstado'] ?? '')) ?: null,
                ':deuda_arrastre' => (float)($entry['carryDebt'] ?? 0),
                ':total_pagado' => (float)($entry['paidTotal'] ?? 0),
                ':deuda_anual' => (float)($entry['debt'] ?? 0),
                ':meses_pagados' => max(0, (int)($entry['paidMonths'] ?? 0)),
                ':meses_actividad' => max(0, (int)($entry['activityMonths'] ?? 0)),
                ':notas_json' => json_encode($notes, JSON_UNESCAPED_UNICODE),
                ':meses_json' => json_encode($monthStates, JSON_UNESCAPED_UNICODE),
            ]);
            $savedRows++;
        }
    }

    $pdo->commit();
    respond(['ok' => true, 'idImport' => $idImport, 'rowsSaved' => $savedRows]);
} catch (Throwable $e) {
    if (isset($pdo) && $pdo instanceof PDO && $pdo->inTransaction()) {
        $pdo->rollBack();
    }
    respond(['ok' => false, 'error' => $e->getMessage()], 500);
}
