---
type: article
title: Herramientas operativas (01-TOOLS)
description: La capa de herramientas del workspace — convención, catálogo (aún vacío) y cómo agregar una herramienta.
tags: [operations, tools, 01-tools]
timestamp: 2026-10-26T23:32:00Z
topic: operations
status: stable
sources: ["[01-TOOLS/README](../../raw/operations/readme-01-tools.md)"]
score: 4.0
---

# Herramientas operativas (01-TOOLS)

> Sources: 01-TOOLS/README.md
> Raw: [README de la capa de herramientas](../../raw/operations/readme-01-tools.md)

## Overview

`01-TOOLS/` es el **arsenal operativo** del workspace: una carpeta por proveedor externo, con las credenciales (`.env`) y los scripts que las consumen, juntos. Hoy está **vacía** — solo existe `_TEMPLATE/` como base.

## Por qué está vacía

Este proyecto es una aplicación **local**: FastAPI + MySQL/MariaDB de XAMPP, sin servicios externos. El único secreto (`SECRET_KEY`, credenciales de base) vive en el `.env` de la aplicación, no aquí. Por tanto no hay proveedores (Stripe, Mailjet, etc.) que operar.

## Cuándo se agrega una herramienta

Cuando el proyecto integre un servicio externo en runtime **o** exista una operación manual recurrente que duela:

1. `cp -r 01-TOOLS/_TEMPLATE 01-TOOLS/<NOMBRE>` (mayúsculas con `_`, sin acentos).
2. `.env.example` con los nombres de variables, `.env` real con `chmod 600`, `.gitignore` local.
3. **Primero el smoke-test** (`test_connection.py`) — probar que las credenciales funcionan.
4. README y `CREDENTIALS.md` de la carpeta.
5. Actualizar el catálogo en `01-TOOLS/README.md`.

## Convención de scripts

- Python 3.11+ con `argparse` obligatorio (`--help` siempre útil).
- Salida legible en stdout, error con exit código ≠ 0.
- Acciones destructivas exigen un flag explícito (`--confirmar`); sin él, dry-run.

## Related

- [Plano de control del workspace](../meta/plano-de-control.md) — dónde encaja esta capa en el gobierno del repositorio.
