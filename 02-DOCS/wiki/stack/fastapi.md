---
type: article
title: FastAPI — aplicación, rutas y seguridad
description: Cómo está construida la aplicación FastAPI — composición, routers, formularios, sesiones y RBAC.
tags: [stack, fastapi, rutas, seguridad]
timestamp: 2026-10-26T23:32:00Z
topic: stack
status: stable
sources: ["[PLAN](../../raw/proyecto/plan-tecnico-mvp.md)", "[README](../../raw/proyecto/sistema-gestion-pagos-osorno-runners.md)"]
score: 11.0
---

# FastAPI — aplicación, rutas y seguridad

> Sources: specs/PLAN.md; README.md
> Raw: [Plan técnico](../../raw/proyecto/plan-tecnico-mvp.md); [README](../../raw/proyecto/sistema-gestion-pagos-osorno-runners.md)

## Overview

FastAPI es el **framework de rutas y controladores**: valida la entrada con Pydantic, invoca los servicios de dominio y devuelve plantillas o redirects. La lógica financiera **nunca** vive en un router: los routers son la frontera entre lo que llega (formularios, sesiones) y las reglas de negocio.

## Composición de la aplicación

`app/main.py` monta, en orden: estáticos, la sesión firmada (itsdangerous), los routers por dominio y los handlers de error centralizados (`app/core/errores.py`). La configuración vive en `app/config.py` como `.env` **tipado** con `pydantic-settings` — `SECRET_KEY` y credenciales de base de datos nunca van en el código.

## Rutas y formularios

- **Routers por dominio** en `app/routers/`: `miembros`, `pagos`, `morosidad`, `negociacion`, `finanzas`, `compras`, `reportes`, `auth`, `landing`.
- **Formularios y vistas**: FastAPI puro con Jinja2 (no hay API JSON de front). Esquemas Pydantic (`app/schemas/`) validan cada formulario.
- **Respuestas**: HTML con plantilla o `RedirectResponse` tras una operación atómica.
- **Endpoint de salud**: `/salud` devuelve `{"estado": "ok", "base_de_datos": "ok"}` — el verificador básico del despliegue local.

## Sesiones y RBAC

- **Sesiones firmadas** (cookie `itsdangerous`) para el inicio de sesión; sin tokens ni JWT (no hay API pública).
- **Roles:** `admin`, `tesorero`, `miembro`. El guard vive en `app/core/seguridad.py`: dependencias que resuelven el usuario actual, exigen rol y filtran el alcance (el miembro solo ve lo suyo — RN-06/RN-07).
- **Contraseñas:** hash con `passlib[bcrypt]`; el correo electrónico es el identificador único (`email-validator`).

## Por qué encaja aquí

Monolito local de un club: sin microservicios, sin API pública, sin cola. FastAPI da validación y tipado donde importa (la frontera) y no obliga a más aparato. El detalle de comportamientos por módulo está en [Reglas de negocio del club](../proyecto/dominio.md).

## Related

- [Python, dependencias y calidad](./python.md) — las dependencias que sostienen el framework.
- [Base de datos: SQLAlchemy y MySQL](./base-datos.md) — lo que los routers invocan antes de persistir.
- [Frontend: Jinja2, Tailwind y Alpine](./frontend.md) — las plantillas que estas rutas renderizan.
- [Arquitectura por capas](../proyecto/arquitectura.md) — dónde encaja cada router.
