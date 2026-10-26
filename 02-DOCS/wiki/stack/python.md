---
type: article
title: Python, dependencias y calidad de código
description: Runtime, gestión de dependencias, pytest y ruff — la mecánica técnica detrás de los principios 3–5 de la constitución.
tags: [stack, python, dependencias, ruff, pytest]
timestamp: 2026-10-26T23:32:00Z
topic: stack
status: stable
sources: ["[README](../../raw/proyecto/sistema-gestion-pagos-osorno-runners.md)", "[PLAN](../../raw/proyecto/plan-tecnico-mvp.md)"]
score: 9.0
---

# Python, dependencias y calidad de código

> Sources: README.md; specs/PLAN.md
> Raw: [README](../../raw/proyecto/sistema-gestion-pagos-osorno-runners.md); [Plan técnico](../../raw/proyecto/plan-tecnico-mvp.md)

## Overview

La mecánica técnica de la barra de calidad ratificada en la [constitución](../sdd/constitution.md) (principios 3–5): runtime pirado, dependencias acotadas, pytest y ruff.

## Runtime y dependencias

- **Python 3.11+** (probado con 3.13); entorn virtuales en `venv/` (gitignored).
- **`requirements.txt`** es la única declaración de dependencias Python, con **rangos acotados** (`fastapi>=0.115,<1.0`, etc.). Dependencia nueva = rango acotado + justificación en el PR (constitución P14).
- Deps clave: `fastapi`, `uvicorn[standard]`, `jinja2`, `sqlalchemy`, `pymysql`+`cryptography`, `pydantic-settings`, `itsdangerous`, `passlib[bcrypt]`+`bcrypt`, `email-validator`, `openpyxl` (XLSX), `reportlab` (PDF), `pytest`, `httpx`, `ruff`.
- **Node/npm solo para Tailwind**; una lockfile (`package-lock.json`) commiteada.

## pytest

- `pytest.ini`: `testpaths = tests`, `addopts = -ra`.
- Fixtures del proyecto: SQLite en memoria por defecto; MySQL opcional vía `TEST_DATABASE_URL` (base **separada**).

## ruff

- `npm run lint` = `ruff check app tests` (versión `0.8.x` en requirements).
- Es la **única puerta estática**: sin mypy (decisión D registrada en [decisions sdd](../sdd/decisions.md) — Pydantic/SQLAlchemy validan en runtime).
- Todo cambio debe dejar ruff **sin advertencias**.

## Disciplina de pruebas

- Toda funcionalidad nueva o corrección llega **con pruebas** que la ejerciten.
- TDD con paso rojo previo: **opcional** y a elección del autor (decisión registrada); lo que no es opcional es que la suite completa pase en verde.

## Related

- [FastAPI: aplicación y rutas](./fastapi.md) — el framework que estas dependencias sostienen.
- [Base de datos: SQLAlchemy y MySQL](./base-datos.md) — las dependencias de persistencia en uso.
- [Calidad, pruebas y aceptación](../proyecto/calidad.md) — el piso de calidad del proyecto.
