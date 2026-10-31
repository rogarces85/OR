---
author: Rodrigo Garces
branch: miembros-baja-softdelete
status: in-progress
type: brief
title: Modales de edición completa de miembros
description: Botón "Editar todos los datos" en listado y ficha que abre un modal con todos los campos del atleta, carga la información y guarda sin salir de la página.
timestamp: 2026-10-31T10:30:00Z
topic: ftd
---

# Modales de edición completa de miembros

## Intent

Desde el listado y la ficha de cada atleta, un botón "Editar todos los datos" abre un modal con todos los campos de la ficha (nombre, email, teléfono, RUT, fechas, dirección, contacto de emergencia, matrícula y categoría), carga la información actual, permite editar y guardar sin salir de la página ni recargar.

## Scope

**Incluido:**
- Partial `app/templates/miembros/modal_editar.html` con formulario completo y macros de campo.
- Botón "Editar" en cada fila del listado (`miembros/lista.html`).
- Botón "Editar todos los datos" en la ficha (`miembros/detalle.html`).
- Router `POST /miembros/{id}/editar` acepta `categoria` y valida con `MiembroEntrada` (incluye categoría y matrícula).
- JS simple: deshabilita botón al guardar ("Guardando…").
- Pruebas de suite existente (sin nuevas pruebas específicas de modal por ser UI renderizada por servidor).

**Excluido:**
- Guardado vía fetch/AJAX (el modal usa POST tradicional; errores de validación renderizan la página de edición completa).
- Cambio de categoría sin historial (usa `servicio_membresias.cambiar_categoria` existente).

## Checklist

- [x] Modal partial con todos los campos de `MiembroEntrada`.
- [x] Botón "Editar" en cada fila del listado.
- [x] Botón "Editar todos los datos" en la ficha.
- [x] Router acepta `categoria` en la edición y valida.
- [x] Suite completa: 147 passed.
- [x] Ruff: All checks passed.

## Evidence

- `pytest -q` → **147 passed** (sin regressiones).
- `ruff check app tests` → **All checks passed!**

## Next

Commitear en rama `miembros-modales-edicion` y abrir PR para fusione en `main`.
