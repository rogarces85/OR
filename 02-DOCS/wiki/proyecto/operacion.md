---
type: article
title: Operación local del sistema
description: Instalación, ejecución, verificación y comandos del MVP en el entorno local (Uvicorn + MySQL de XAMPP).
tags: [operacion, despliegue, comandos]
timestamp: 2026-10-26T23:32:00Z
topic: proyecto
status: stable
sources: ["[README](../../raw/proyecto/sistema-gestion-pagos-osorno-runners.md)", "[DESPLIEGUE](../../raw/proyecto/despliegue-local.md)"]
score: 9.0
---

# Operación local del sistema

> Sources: README.md; docs/DESPLIEGUE_LOCAL.md
> Raw: [README](../../raw/proyecto/sistema-gestion-pagos-osorno-runners.md); [Guía de despliegue local](../../raw/proyecto/despliegue-local.md)

## Overview

El sistema corre **solo en el PC del usuario**: Uvicorn en `http://127.0.0.1:8000` con MySQL/MariaDB de XAMPP, sin exposición pública. La guía completa paso a paso es [docs/DESPLIEGUE_LOCAL.md](../../../docs/DESPLIEGUE_LOCAL.md); aquí queda la referencia rápida.

## Requisitos

Windows + PowerShell **Python 3.11+** (probado 3.13) · Node 18+ · **XAMPP** con el módulo MySQL iniciado · puerto 8000 libre · raíz del proyecto en `C:\xampp\htdocs\www\OR`.

## Instalación (resumen)

```powershell
python -m venv venv; .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm install
Copy-Item .env.example .env   # luego: SECRET_KEY propia, credenciales DB
& "C:\xampp\mysql\bin\mysql.exe" -u root -e "CREATE DATABASE IF NOT EXISTS osorno_runners CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
npm run css:build
.\venv\Scripts\python.exe -m app.seed
```

`app.seed` es **idempotente**: crea el esquema, agrega índices declarados que falten y carga catálogos (cuotas, cuenta bancaria, plantilla de correo, usuarios y miembros de ejemplo) sin duplicar. Repetirlo nunca corrompe datos.

## Ejecución

| Comando | Qué hace |
| :-- | :-- |
| `npm run dev` | Servidor + Tailwind watch + navegador (recomendado). |
| `npm start` | Solo el servidor, sin recompilar CSS. |
| `npm run seed` | Semilla idempotente. |
| `npm run demo` | Datos del caso de negociación. |
| `npm test` / `npm run lint` | pytest / ruff. |
| `npm run css:build` / `css:dev` | Tailwind minificado / watch. |

## Verificación

- `http://127.0.0.1:8000/salud` → `{"estado":"ok", ..., "base_de_datos":"ok"}`.
- `/` → landing; `/ingresar` → inicio de sesión.
- **Credenciales de la semilla:** `admin@osornorunners.cl` / `Admin1234` · `tesorero@osornorunners.cl` / `Tesorero1234` · `ana.saldivar@example.com` / `Miembro1234`.

## Base de pruebas (MySQL)

```powershell
$env:TEST_DATABASE_URL = "mysql+pymysql://root:@localhost:3306/osorno_runners_test"
.\venv\Scripts\python.exe -m pytest
```

**Nunca** apuntar `TEST_DATABASE_URL` a `osorno_runners`: la suite crea y destruye el esquema por prueba.

## Publicación (post-MVP)

El plan de publicación (Docker+Caddy, VPS+Nginx o Cloudflare Tunnel), HTTPS y respaldos está cerrado en `docs/POST_MVP.md` pero **no ejecutado** (Q-3).

## Related

- [Base de datos: SQLAlchemy y MySQL](../stack/base-datos.md) — lo que `seed` y el `.env` tocan.
- [Calidad, pruebas y aceptación](./calidad.md) — cómo se prueba antes de declarar algo listo.
- [Visión y alcance](./vision.md) — por qué todo corre en local.
