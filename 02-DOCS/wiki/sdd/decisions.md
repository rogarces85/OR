---
title: SDD decisions
description: Registro append-only de decisiones significativas del flujo SDD.
tags: [sdd, decisions]
topic: sdd
---

# SDD decisions

Registro append-only de decisiones significativas (principio 16 de la constitución).

| Fecha | Decisión | Opciones consideradas | Por qué |
|---|---|---|---|
| 2026-10-26 | Constitución v1.0.0 ratificada: 16 principios. | — | Arranque del flujo SDD del proyecto. |
| 2026-10-26 | Cobertura: suite pytest verde en cada PR, sin piso numérico. | suite verde / pytest-cov ≥80% en código cambiado / piso solo módulo dinero | La suite existente (unitaria + integración + E2E del MVP) ya protege los flujos completos; añadir pytest-cov suma fricción sin beneficio real para un club local. |
| 2026-10-26 | Tipos: ruff como única puerta estática; sin mypy. | solo ruff / mypy gradual / mypy estricto | Pydantic y SQLAlchemy validan tipos en runtime; el repo es un MVP maduro; añadir mypy exigiría una migración que ninguna enmienda pide. |
| 2026-10-26 | Pruebas: toda funcionalidad o corrección llega con tests; TDD libre. | tests siempre, TDD libre / TDD estricto red→green→refactor / solo reglas de dinero | Garantiza cobertura de cada cambio sin imponer ritual; el proyecto ya tiene cultura de pruebas E2E. |
| 2026-10-26 | Commits: patrón `Ámbito: descripción en español`. | patrón actual / Conventional Commits / gitmoji + conventional | Ratifica la práctica real del historial; evita reescribir un historial ya consistente. |
| 2026-10-26 | Accesibilidad: barra pragmática — teclado, foco visible, contraste AA en formularios y tablas. | pragmática / WCAG 2.2 AA completo / sin piso | Panel interno de club; barra verificable en revisión sin auditoría formal completa. |
