---
type: article
title: Arquitectura por capas
description: Monolito modular en capas — estructura de app/, módulos de dominio, modelo de datos y principios de construcción.
tags: [arquitectura, capas, modelo-datos]
timestamp: 2026-10-26T23:32:00Z
topic: proyecto
status: stable
sources: ["[PLAN](../../raw/proyecto/plan-tecnico-mvp.md)", "[README](../../raw/proyecto/sistema-gestion-pagos-osorno-runners.md)"]
score: 11.0
---

# Arquitectura por capas

> Sources: specs/PLAN.md; README.md
> Raw: [Plan técnico](../../raw/proyecto/plan-tecnico-mvp.md); [README](../../raw/proyecto/sistema-gestion-pagos-osorno-runners.md)

## Overview

**Monolito modular por capas:** para un club con cientos de miembros, los microservicios no se justifican. Cada capa tiene una responsabilidad única y las reglas de negocio nunca viven en rutas ni en plantillas. Toda operación financiera es **atómica** y los montos son **enteros en CLP**.

## Capas

| Capa | Componente | Responsabilidad |
| :--- | :--- | :--- |
| Presentación | Jinja2 · Tailwind · Alpine.js | Renderiza; sin reglas de negocio. |
| Rutas/Controladores | FastAPI routers + Pydantic | Valida entrada, invoca servicios, devuelve plantillas/redirects. Sin lógica financiera. |
| Aplicación/Negocio | `app/services/` | Reglas de especificación: activación, imputación, abonos, morosidad, negociación, reportes. **Capa más testeada.** |
| Acceso a datos | `app/repositories/` + ORM | Aísla consultas; transacciones atómicas. |
| Persistencia | MySQL/MariaDB (XAMPP) | Datos del club. |

**Transversal:** seguridad, configuración y formato CLP (`app/core/`).

## Estructura de `app/`

- `main.py` — compone la app (static, sesiones, routers); `config.py` — `.env` tipado; `database.py` — engine/sesión/Base; `dependencies.py` — usuario actual, rol, sesión de BD; `seed.py`/`demo.py` — esquema y datos idempotentes.
- `core/` — `seguridad.py` (hash, sesiones, RBAC), `formato.py` (CLP), `errores.py` (errores centralizados).
- `models/` (SQLAlchemy) · `schemas/` (Pydantic de formularios) · `repositories/` · `services/` · `routers/` (por dominio) · `templates/` · `static/`.

## Módulos de dominio

Seguridad/Usuarios · Miembros y Membresías · Pagos · Morosidad · Negociación · Finanzas · Compras y cobro · Reportes · Comunicación · Configuración · Marca/Landing.

## Modelo de datos (síntesis)

- **Núcleo de membresía:** `Usuario` (rol admin/tesorero/miembro) · `Miembro` (categoría, matriculado, exención, correo único) · `HistorialCategoria` · `NivelCuota` · `CuotaMensual` (pendiente/pagada/parcial/exenta).
- **Pagos:** `Pago` (monto libre, medio) → `ImputacionPago` (descomposición por cuota) · `Abono` (saldo a favor aplicable).
- **Morosidad:** derivada de `CuotaMensual` de meses cerrados; `NegociacionDeuda` (descuento %, estados propuesta/aceptada/pagada).
- **Finanzas:** `CategoriaEgreso` · `Egreso` (tipo general/activo/gasto_fijo/compra) · `GastoFijo`.
- **Compras:** `CompraClub` → `CompraItem` → `CargoAlumno` (pendiente/pagado).
- **Config/comunicación:** `CuentaBancaria` · `PlantillaCorreo` · `AvisoMorosidad`.

El esquema completo, con propiedades y relaciones, vive en [specs/PLAN.md §4](../../../specs/PLAN.md).

## Related

- [FastAPI: aplicación y rutas](../stack/fastapi.md) — la capa-Presentación/Control en detalle.
- [Base de datos: SQLAlchemy y MySQL](../stack/base-datos.md) — la persistencia.
- [Frontend: Jinja2, Tailwind y Alpine](../stack/frontend.md) — la presentación visual.
- [Reglas de negocio del club](./dominio.md) — el contenido de `services/`.
- [Visión y alcance](./vision.md) — el porqué de estas decisiones.
