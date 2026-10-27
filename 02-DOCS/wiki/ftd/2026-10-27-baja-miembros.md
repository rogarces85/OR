---
author: Rodrigo Garces
branch: main
status: in-progress
type: brief
title: Baja y reactivación de miembros (soft-delete)
description: Retiro lógico de miembros con fecha y motivo de baja, sin borrar ficha ni historial.
timestamp: 2026-10-27T10:30:00Z
topic: ftd
---

# Baja y reactivación de miembros (soft-delete)

## Intent

Permitir retirar a un miembro del club sin destruir su historia: la ficha y los pagos se conservan, pero el miembro deja de aparecer en el panel y de entrar al ciclo de cobro. Debe poder reactivarse después.

## Scope

**Incluido:** columnas `fecha_baja`/`motivo_baja` (modelo + migración idempotente en `crear_indices_faltantes`), property `esta_activo`, filtro `incluir_bajas` en el repositorio y en el listado web, servicios `dar_de_baja`/`reactivar_miembro`, rutas POST `/miembros/{id}/baja` y `/miembros/{id}/reactivar`, UI en ficha (sello de baja + formularios) y en listado (filtro "Incluir dados de baja" y sello por fila), pruebas de servicio y web.

**Excluido:** borrado físico de filas (nunca); alterar cuotas ya generadas; reglas de deuda al dar de baja.

## Checklist

- [x] Modelo y migración — `fecha_baja DATE NULL`, `motivo_baja VARCHAR(200) NULL` e índice, aplicados de forma idempotente.
- [x] Repositorio — `listar()` excluye bajas por defecto; `incluir_bajas=True` y `listar_todos()` las devuelven.
- [x] Servicios — `dar_de_baja` (fecha por defecto hoy, motivo recortado, rechaza doble baja y motivo > 200) y `reactivar_miembro` (limpia ambos campos, rechaza reactivar a quien no está de baja).
- [x] Rutas y UI — POST con CSRF y flash; ficha con sello/formatos; listado con filtro de bajas.
- [x] Pruebas — 10 casos en `tests/test_miembro_softdelete.py` (modelo, repositorio, servicio, ciclo de cobro y flujo web completo).
- [x] Suite completa y ruff en verde.

## Evidence

- `pytest -q` → **147 passed** (antes 140; +7 netos nuevos).
- `ruff check app tests` → **All checks passed!**
- Flujo web probado: ficha → POST baja (303) → desaparece de `/miembros` → aparece con `?incluir_bajas=1` → POST reactivar (303) → reaparece en `/miembros`.
- Un miembro de baja sale de `miembros_facturables`, así que `generar_cuotas_del_periodo` deja de cobrarle (F-10).

## Next

Commitear el cambio de código cuando el humano elija la vía (main o rama + PR).
