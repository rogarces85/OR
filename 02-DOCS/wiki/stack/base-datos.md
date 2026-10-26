---
type: article
title: Base de datos — SQLAlchemy y MySQL
description: SQLAlchemy ORM sobre MySQL/MariaDB de XAMPP — modelos, transacciones atómicas, seed idempotente y pruebas con SQLite.
tags: [stack, base-datos, sqlalchemy, mysql]
timestamp: 2026-10-26T23:32:00Z
topic: stack
status: stable
sources: ["[PLAN](../../raw/proyecto/plan-tecnico-mvp.md)", "[README](../../raw/proyecto/sistema-gestion-pagos-osorno-runners.md)"]
score: 12.0
---

# Base de datos — SQLAlchemy y MySQL

> Sources: specs/PLAN.md; README.md
> Raw: [Plan técnico](../../raw/proyecto/plan-tecnico-mvp.md); [README](../../raw/proyecto/sistema-gestion-pagos-osorno-runners.md)

## Overview

SQLAlchemy 2.x (estilo ORM) sobre **MySQL/MariaDB de XAMPP** con el driver `pymysql` + `cryptography`. El acceso a datos vive exclusivamente en `app/repositories/`; los servicios nunca escriben SQL ni tocan la sesión directamente — así las transacciones atómicas tienen un único lugar.

## Motor y conexión

- `app/database.py` define el engine, la sesión y la `Base` declarativa.
- URL desde el `.env` tipado (`DATABASE_URL`), típica: `mysql+pymysql://root:@localhost:3306/osorno_runners`.
- Charset **utf8mb4** (tildes y "ñ" — RN-16).
- **Dinero:** columnas enteras (CLP). Jamás float — es una regla de forma del proyecto.

## Modelo

Los grupos del esquema (entidades, propiedades y relaciones completas en [specs/PLAN.md §4](../../../specs/PLAN.md)):

- **Membresía:** `Usuario`, `Miembro`, `HistorialCategoria`, `NivelCuota`, `CuotaMensual` (estados pendiente/pagada/parcial/exenta).
- **Pagos:** `Pago` → `ImputacionPago` (descomposición por cuota) y `Abono` (saldo a favor).
- **Morosidad/negociación:** derivada de `CuotaMensual`; `NegociacionDeuda` (descuento %, estados).
- **Finanzas:** `CategoriaEgreso`, `Egreso`, `GastoFijo`.
- **Compras:** `CompraClub` → `CompraItem` → `CargoAlumno`.
- **Config/comunicación:** `CuentaBancaria`, `PlantillaCorreo`, `AvisoMorosidad`.

## Transacciones y atomicidad

Toda operación financiera (registro de pago + sus imputaciones + actualización de cuotas + generación de abono) ocurre **dentro de una transacción**: se confirma o se descarta entera. Los repositories compran esa atomicidad; los servicios declaran el orden.

## Seed idempotente

`app/seed.py` (o `npm run seed`) crea el esquema, agrega índices declarados que falten y carga catálogos + usuarios/miembros de ejemplo **sin duplicar**. Repetirlo nunca corrompe datos. `app/demo.py` agrega el caso de negociación para la demo guiada.

## Pruebas

- **SQLite en memoria** por defecto: la suite completa corre sin XAMPP.
- MySQL opcional vía `TEST_DATABASE_URL` con base **separada** (`osorno_runners_test`); la suite crea y destruye el esquema por prueba — **nunca** apuntar a la base de desarrollo.

## Related

- [FastAPI: aplicación y rutas](./fastapi.md) — quién consume los repositories.
- [Python, dependencias y calidad](./python.md) — los paquetes de persistencia y sus rangos.
- [Arquitectura por capas](../proyecto/arquitectura.md) — la capa de acceso a datos en contexto.
- [Operación local](../proyecto/operacion.md) — cómo se crea la base y se corre el seed.
