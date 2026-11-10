---
author: Rodrigo Garces
branch: miembros-visuales-ajustes
status: done
type: brief
title: Ajustes visuales de listado Miembros
description: Botones de acciones visibles (quitar onclick de fila que los bloqueaba) y textos de categoría simplificados a Activo / Membresía.
timestamp: 2026-10-31T12:30:00Z
topic: ftd
merged: 2026-10-31
pr: #5
---

# Ajustes visuales de listado Miembros

## Intent

Corregir dos problemas visuales del listado de miembros: los botones de acciones no eran clickeables porque el `onclick` de la fila los bloqueaba, y los textos de categoría mostraban sufijos que el usuario no pidió.

## Scope

**Incluido:**
- Quitar `onclick="location.href=..."` y `cursor-pointer` del `<tr>` del listado para que los botones "Editar" y "Ver ficha" reciban el clic correctamente.
- Cambiar badge de categoría de "Activo (alumno)" / "Membresía (apoyo)" a solo "Activo" / "Membresía".
- Mantener el nombre del miembro como enlace a la edición (compatible con prueba existente).

**Excluido:**
- Cambios de lógica de negocio o modelo de datos.

## Checklist

- [x] Botones de acciones del listado visibles y clickeables.
- [x] Texto de categoría simplificado a Activo / Membresía.
- [x] Suite completa: 149 passed.
- [x] Ruff: All checks passed.

## Evidence

- `pytest -q` → **149 passed**.
- `ruff check app tests` → **All checks passed!**

## Next
Fusionado en main el 2026-10-31 (c44d4f0).
