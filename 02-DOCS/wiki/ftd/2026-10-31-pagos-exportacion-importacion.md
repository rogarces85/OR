---
author: Rodrigo Garces
branch: pagos-exportacion-importacion
status: done
type: brief
title: Exportación e importación masiva de pagos
description: Exportar pagos a XLSX y cargar múltiples pagos desde un archivo XLSX o CSV.
timestamp: 2026-10-31T13:00:00Z
topic: ftd
merged: 2026-10-31
pr: #6
---

# Exportación e importación masiva de pagos

## Intent

Permitir exportar los pagos registrados a un archivo XLSX y importar múltiples pagos de una sola vez desde un archivo XLSX o CSV, útil para cargar datos de una base de datos existente.

## Scope

**Incluido:**
- Ruta `GET /pagos/exportar` — genera un XLSX con columnas: Fecha, Miembro, Email, RUT, Medio de pago, Monto (CLP), Observaciones. Respeta los mismos filtros de fecha que la lista de ingresos.
- Ruta `GET /pagos/importar` — muestra el formulario para subir un archivo con el formato esperado.
- Ruta `POST /pagos/importar` — procesa el archivo, valida cada fila (miembro por email/RUT, monto positivo, fecha válida, medio transferencia/efectivo), registra los pagos válidos en una transacción atómica cada uno, y reporta exitosos y fallidos con detalle de errores.
- Plantillas `pagos/importar.html` y botones en `pagos/lista.html` (Exportar a XLSX, Importar pagos).
- Repositorio: `obtener_por_rut` en `miembro.py` para buscar miembros por RUT en la importación.
- Pruebas: 149 existentes sin regressiones.

**Excluido:**
- Importación que cree miembros automáticamente (el miembro debe existir ya).
- Validación de duplicados entre filas del mismo archivo (cada fila se valida contra la base de datos actual).

## Checklist

- [x] Servicio: `exportar_pagos_a_xlsx` genera bytes de XLSX con formato y anchos de columna.
- [x] Servicio: `importar_pagos_desde_archivo` lee XLSX y CSV, valida filas, registra pagos, reporta errores por fila.
- [x] Repositorio: `obtener_por_rut` en miembro.py.
- [x] Rutas: exportar, importar (GET y POST).
- [x] Plantillas: importar.html, botones en lista.html.
- [x] Suite completa: 149 passed.
- [x] Ruff: All checks passed.

## Evidence

- `pytest -q` → **149 passed**.
- `ruff check app tests` → **All checks passed!**

## Next
Fusionado en main el 2026-10-31 (8bf2123).
