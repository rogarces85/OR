---
author: Rodrigo Garces
branch: miembros-mejoras-visuales
status: in-progress
type: brief
title: Mejoras visuales del módulo Miembros
description: Listado con badges de estado y columna de acciones, ficha con tarjeta de resumen y secciones en cards, modal con campos agrupados y validación en tiempo real.
timestamp: 2026-10-31T12:00:00Z
topic: ftd
---

# Mejoras visuales del módulo Miembros

## Intent

Mejorar la experiencia visual y de uso del módulo Miembros: listado más escaneable, ficha con información resumida de un vistazo y modal de edición con validación en tiempo real.

## Scope

**Incluido:**
- Listado: badges de estado (Activo/Pendiente/Baja/Exento), chip de matrícula, columna de acciones, filas interactivas (clic va a ficha), estado vacío ilustrado.
- Ficha: tarjeta de resumen superior, secciones en cards (Activación, Cambio de categoría, Exención, Estado del miembro, Historial, Cuotas), indicadores de morosidad visuales, botones de acción con jerarquía.
- Modal: campos agrupados por fieldset (Datos personales, Fechas, Contacto, Estado), validación en tiempo real (blur), spinner al guardar, confirmación de cierre si hay cambios sin guardar.
- Pruebas existentes sin cambios (149 pasadas).

**Excluido:**
- Cambios de lógica de negocio o modelo de datos.
- Nuevas pruebas específicas de UI (las pruebas existentes cubren rutas y servicios).

## Checklist

- [x] Listado con badges de estado y chip de matrícula.
- [x] Columna de acciones con botones Editar y Ver ficha.
- [x] Estado vacío ilustrado en el listado.
- [x] Ficha con tarjeta de resumen y secciones en cards.
- [x] Modal con campos agrupados por fieldset.
- [x] Validación en tiempo real (blur) en el modal.
- [x] Spinner en botón Guardar del modal.
- [x] Confirmación de cierre con cambios sin guardar.
- [x] Suite completa: 149 passed.
- [x] Ruff: All checks passed.

## Evidence

- `pytest -q` → **149 passed** (sin regressiones).
- `ruff check app tests` → **All checks passed!**

## Next

Commitear en rama `miembros-mejoras-visuales` y abrir PR para fusione en `main`.
