# Knowledge Base Index

> **OKF v0.1 reserved file** — `index.md` carries **no frontmatter** (it is a
> directory listing for progressive disclosure, per the OKF spec). Links are
> standard markdown, relative to this file (`topic/article.md`), NEVER wikilinks.
>
> **Human navigation lives in the `.base` views** (`Articles.base`, `Worklog.base`,
> `Decisions.base`) — live tables over frontmatter, sorted by score/status/date.
> This index is the **machine-readable catalog + fallback** the agent maintains;
> it is not the primary surface a human browses in Obsidian.

## proyecto

Qué es el Sistema Gestión Pagos Osorno Runners, su dominio, arquitectura, operación y calidad.

| Article | Summary | Updated | Score |
|---------|---------|---------|-------|
| [Visión y alcance](proyecto/vision.md) | Qué es el sistema, el problema que resuelve, usuarios y estado actual. | 2026-10-26 | 14.0 |
| [Arquitectura por capas](proyecto/arquitectura.md) | Monolito modular: capas, estructura de `app/`, modelo de datos. | 2026-10-26 | 11.0 |
| [Calidad, pruebas y aceptación](proyecto/calidad.md) | Suite pytest, ruff, matrices UAT/COBERTURA y Definition of Done. | 2026-10-26 | 11.0 |
| [Reglas de negocio del club](proyecto/dominio.md) | Cuotas, activación, mora, imputación, exenciones, negociación y finanzas. | 2026-10-26 | 9.0 |
| [Operación local del sistema](proyecto/operacion.md) | Instalación, ejecución, verificación y comandos del entorno local. | 2026-10-26 | 9.0 |

## stack

La mecánica técnica por componente: Python, FastAPI, base de datos y frontend.

| Article | Summary | Updated | Score |
|---------|---------|---------|-------|
| [Base de datos — SQLAlchemy y MySQL](stack/base-datos.md) | ORM, motor, transacciones atómicas, seed idempotente y pruebas. | 2026-10-26 | 12.0 |
| [FastAPI — aplicación, rutas y seguridad](stack/fastapi.md) | Composición, routers, formularios, sesiones y RBAC. | 2026-10-26 | 11.0 |
| [Python, dependencias y calidad de código](stack/python.md) | Runtime, dependencias acotadas, pytest y ruff. | 2026-10-26 | 9.0 |
| [Frontend — Jinja2, Tailwind y Alpine.js](stack/frontend.md) | Presentación server-rendered, build de CSS y accesibilidad. | 2026-10-26 | 7.0 |

## sdd

El gobierno del trabajo: constitución técnica ratificada y decisiones registradas.

| Article | Summary | Updated | Score |
|---------|---------|---------|-------|
| [Constitución técnica v1.0.0](sdd/constitution.md) | Las 16 reglas ratificadas: pruebas, estilo, commits, trazabilidad, autoría. | 2026-10-26 | 5.0 |
| [Decisiones técnicas](sdd/decisions.md) | Registro abierto de decisiones de implementación (sin mypy, TDD libre, …). | 2026-10-26 | 3.0 |

## ftd

Documentos de característica de cada cambio autorizado (uno por feature).

| Article | Summary | Updated | Score |
|---------|---------|---------|-------|
| [Documentación completa del proyecto](ftd/2026-10-26-documentacion-completa.md) | Bootstrap de la wiki 02-DOCS desde la documentación oficial. | 2026-10-26 | -4.0 |
| [Baja y reactivación de miembros (soft-delete)](ftd/2026-10-27-baja-miembros.md) | Retiro lógico con fecha/motivo, fuera del panel y del cobro, reversible. | 2026-10-27 | -4.0 |
| [Modales de edición completa de miembros](ftd/2026-10-31-modales-edicion-miembros.md) | Botón "Editar todos los datos" en listado y ficha; modal con todos los campos. | 2026-10-31 | -4.0 |

## harness

Plano de control instalado por el bootstrap del workspace.

| Article | Summary | Updated | Score |
|---------|---------|---------|-------|
| [Perfil del humano](harness/user-profile.md) | Idioma, registro técnico y formato de cierre del dueño del proyecto. | 2026-10-26 | 3.0 |
| [Plan de instalación del harness](harness/installation-plan.md) | Qué instaló el bootstrap y su identificación. | 2026-10-26 | 3.0 |
| [Decisiones del harness](harness/decisions.md) | Elecciones del onboarding (ramas y PR, asistente de destino, etc.). | 2026-10-26 | 3.0 |

## meta

El mapa del propio plano de control: reglas, registros y navegación.

| Article | Summary | Updated | Score |
|---------|---------|---------|-------|
| [Plano de control del workspace](meta/plano-de-control.md) | Qué gobierna el repositorio y dónde vive cada pieza. | 2026-10-26 | 5.0 |

## operations

Capa de herramientas operativas externas (01-TOOLS).

| Article | Summary | Updated | Score |
|---------|---------|---------|-------|
| [Herramientas operativas (01-TOOLS)](operations/herramientas.md) | Convención de la capa, catálogo vacío y cómo agregar una herramienta. | 2026-10-26 | 4.0 |
