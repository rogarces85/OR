---
type: article
title: Plano de control del workspace
description: Qué gobierna este repositorio — perfil del humano, constitución técnica, decisiones y dónde vive cada pieza de la fábrica de software.
tags: [meta, control, constitucion, decisiones]
timestamp: 2026-10-26T23:32:00Z
topic: meta
status: stable
sources: ["[CLAUDE.md](../../raw/meta/claude-md-mapa-de-conocimiento.md)", "[AGENTS.md](../../raw/meta/agents-md-rsc-suggest.md)"]
score: 5.0
---

# Plano de control del workspace

> Sources: CLAUDE.md; AGENTS.md (root)
> Raw: [Mapa de conocimiento de la raíz](../../raw/meta/claude-md-mapa-de-conocimiento.md); [Bloque rsc-suggest](../../raw/meta/agents-md-rsc-suggest.md)

## Overview

Este repositorio no se ejecuta solo con código: tiene un **plano de control** — las reglas y registros que determinan cómo se trabaja. Este artículo es el mapa de esas piezas y de dónde viven, para que cualquier sesión pueda gobernar antes de construir.

## Las piezas y dónde viven

| Pieza | Ubicación | Qué gobierna |
| :-- | :-- | :-- |
| Perfil del humano | [`harness/user-profile.md`](../harness/user-profile.md) | Cómo se comunica: idioma, registro técnico y formato de cierre. |
| **Constitución técnica** | [`sdd/constitution.md`](../sdd/constitution.md) | Las 16 reglas ratificadas: pytest en verde, ruff sin mypy, pruebas siempre, commits en español, accesibilidad pragmática, autoría humana. |
| Decisiones técnicas | [`sdd/decisions.md`](../sdd/decisions.md) | Decisiones individuales registradas (p. ej. por qué sin mypy, TDD libre). |
| Instalación del harness | [`harness/installation-plan.md`](../harness/installation-plan.md) | Qué instaló el bootstrap y su identificación. |
| Decisiones del harness | [`harness/decisions.md`](../harness/decisions.md) | Elecciones del onboarding (ramas y PR, asistente de destino, etc.) |
| Capa de herramientas | [`operations/herramientas.md`](../operations/herramientas.md) | Cómo operar servicios externos si llegan a existir. |

> Nota: las rutas anteriores son relativas a `02-DOCS/wiki/` — la vista canónica es `02-DOCS/wiki/index.md`.

## Cómo se actualiza

- **Decisiones que cambian reglas de trabajo** → constitución (con ratificación explícita).
- **Decisiones puntuales de implementación** → `sdd/decisions.md`.
- **Nuevos conocimientos del proyecto** → artículos del wiki (inyectados desde `inbox/` o `raw/`).
- El índice canónico (`index.md`) y los scores se mantienen en cada ingestión o mejora.

## Related

- [Constitución](../sdd/constitution.md) — el texto ratificado completo.
- [Decisiones técnicas](../sdd/decisions.md) — el registro puro de decisiones.
- [Perfil del humano](../harness/user-profile.md) — cómo dirigirse al dueño del proyecto.
- [Herramientas operativas](../operations/herramientas.md) — la otra mitad del control (lo externo).
