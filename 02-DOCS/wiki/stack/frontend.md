---
type: article
title: Frontend — Jinja2, Tailwind y Alpine.js
description: Presentación server-rendered — plantillas Jinja2, utilidades Tailwind compiladas y Alpine.js para la interacción mínima.
tags: [stack, frontend, jinja, tailwind, alpine]
timestamp: 2026-10-26T23:32:00Z
topic: stack
status: stable
sources: ["[PLAN](../../raw/proyecto/plan-tecnico-mvp.md)", "[README](../../raw/proyecto/sistema-gestion-pagos-osorno-runners.md)"]
score: 7.0
---

# Frontend — Jinja2, Tailwind y Alpine.js

> Sources: specs/PLAN.md; README.md
> Raw: [Plan técnico](../../raw/proyecto/plan-tecnico-mvp.md); [README](../../raw/proyecto/sistema-gestion-pagos-osorno-runners.md)

## Overview

La presentación es **server-rendered**: no hay SPA ni framework de front. Jinja2 renderiza las vistas, Tailwind da el estilo por utilidades y Alpine.js agrega la interacción mínima (confirmaciones, toggles de formulario). Sin reglas de negocio en el front: todo lo que calcula o valida monto vive en los servicios.

## Capa de plantillas

- `app/templates/` con herencia: `base.html` (+ tema del club: paleta Rojo/Negro/Blanco, F-29), layouts por rol, partials de tablas y modales.
- Router de FastAPI decide la plantilla y el contexto; la plantilla solo muestra.
- Formularios clásicos (`POST` + redirect), con mensajes de error del esquema Pydantic.
- Locale de presentación: CLP entero con separador de miles por punto (formateo centralizado en `app/core/formato.py`) y español RAE estricto (RN-16).

## Tailwind y build

- **Solo desarrollo:** `npm run css:dev` (watch). **Producción local:** `npm run css:build` (minificado).
- Clases utilitarias en las plantillas; la salida compilada vive en `app/static/`.
- Node/npm existen **solo para el CSS**: no hay dependencias de front en runtime.

## Alpine.js

Para los pequeños comportamientos de interfaz: confirmar acciones destructivas, mostrar/ocultar campos según selección (p. ej. edición del % en una negociación). Sin bundler: se carga desde `static/` y se declara inline.

## Accesibilidad pragmática

Barra de la constitución (principio de accesibilidad): navegación completa por teclado, foco visible y estilos AA en contraste. Es una barra de calidad, no una auditoría formal por cada plantilla.

## Related

- [FastAPI: aplicación y rutas](./fastapi.md) — quién renderiza estas plantillas y con qué contexto.
- [Arquitectura por capas](../proyecto/arquitectura.md) — la capa de presentación en el diagrama.
- [Visión y alcance](../proyecto/vision.md) — la identidad visual y de idioma que el front debe respetar.
