<?php
declare(strict_types=1);

require __DIR__ . '/_init.php';
require __DIR__ . '/db.php';

try {
    $pdo = db();
    respond(['ok' => true, 'data' => fetch_bootstrap($pdo)]);
} catch (Throwable $e) {
    respond(['ok' => false, 'error' => $e->getMessage()], 500);
}
