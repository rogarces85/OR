---
type: article
title: Calidad, pruebas y aceptación
description: Suite pytest (incluida la E2E del MVP), ruff, matrices UAT y COBERTURA, y la barra de Definition of Done.
tags: [calidad, pruebas, aceptacion]
timestamp: 2026-10-26T23:32:00Z
topic: proyecto
status: stable
sources: ["[README](../../raw/proyecto/sistema-gestion-pagos-osorno-runners.md)", "[UAT](../../raw/proyecto/uat-matriz-aceptacion.md)", "[COBERTURA](../../raw/proyecto/cobertura-matriz-funcional.md)", "[GUIA_DEMO](../../raw/proyecto/guia-demo-mvp.md)"]
score: 11.0
---

# Calidad, pruebas y aceptación

> Sources: README.md; specs/UAT.md; specs/COBERTURA.md; specs/GUIA_DEMO.md
> Raw: [README](../../raw/proyecto/sistema-gestion-pagos-osorno-runners.md); [UAT](../../raw/proyecto/uat-matriz-aceptacion.md); [COBERTURA](../../raw/proyecto/cobertura-matriz-funcional.md); [Guion de demostración](../../raw/proyecto/guia-demo-mvp.md)

## Overview

La calidad del proyecto se demuestra con tres cosas: la **suite pytest** en verde, **ruff** sin advertencias y las **matrices de trazabilidad** (`UAT`/`COBERTURA`) actualizadas. Todo cambio nuevo debe llegar además con pruebas que lo ejerciten.

## Suite de pruebas

- `npm test` = `pytest` sobre `tests/`. Unitarias + integración + un recorrido **end-to-end del MVP** (`tests/test_e2e_mvp.py`): alta → activación → pago → mora → negociación → egresos → compras → reportes → landing.
- **SQLite en memoria** por defecto (no requiere XAMPP). Para MySQL: base **separada** vía `TEST_DATABASE_URL` (nunca la de desarrollo).

## Estilo

- `npm run lint` = `ruff check app tests` — la **única puerta estática**; sin mypy (decisión registrada).
- Cobertura: **sin piso numérico** (decisión); la suite completa en verde es el piso de cada PR.

## Matrices de trazabilidad

- [specs/UAT.md](../../../specs/UAT.md) — matriz de aceptación **CA-01…CA-31**: cada criterio con su verificación observada.
- [specs/COBERTURA.md](../../../specs/COBERTURA.md) —Digite cobertura final F/RN/CA: qué cada funcionalidad y regla cumple y con qué prueba.
- Regla (constitución P9): cuando un PR cambia comportamiento descrito en SPECS/UAT/COBERTURA, las matrices se actualizan **en el mismo PR**.

## Demo guiada

`app.seed` + `app.demo` preparan el caso de negociación; el guion paso a paso con credenciales y datos esperados está en `specs/GUIA_DEMO.md`.

## Related

- [Operación local](./operacion.md) — los comandos existentes para correr todo esto.
- [Python, dependencias y calidad](../stack/python.md) — herramientas concretas (pytest, ruff) y su configuración.
- [Reglas de negocio del club](./dominio.md) — lo que las pruebas protegen.
