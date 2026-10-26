---
type: constitution
title: OR — Constitution
description: The non-negotiable principles every rsc-sdd phase obeys.
tags: [sdd, constitution]
timestamp: 2026-10-26T22:45:30Z
topic: sdd
version: v1.0.0
---

# OR — Constitution

> Version: v1.0.0 · Ratified: 2026-10-26 · Last amended: 2026-10-26
> The non-negotiable principles every rsc-sdd phase obeys. Stack mechanics live in
> `02-DOCS/wiki/stack/*`; this file ratifies the principle and links the detail.

## Known facts (from onboarding)

- Goal: Gestionar pagos, membresias y finanzas del club Osorno Runners de forma fiable y local.
- Project kind: software · software scope: growing.
- How code changes land: branches closed with a pull request; `main` is closed to direct work.

## 1. Stack canon

1. Runtime: **Python 3.11+** (probado con 3.13). Dependencias Python solo vía `requirements.txt`
   con rango acotado. Node 18+/npm solo para compilar Tailwind; una sola lockfile
   (`package-lock.json`), commiteada.
2. Frameworks fijos: **FastAPI** + Jinja2, **SQLAlchemy 2.x** sobre MySQL/MariaDB de XAMPP,
   Tailwind CSS, Alpine.js, **pytest**, **ruff**. Cambiar uno es una enmienda MAJOR.

## 2. Quality bar

3. `npm run lint` (ruff sobre `app` y `tests`) pasa sin advertencias en cada cambio. ruff es la
   única puerta estática; mypy no se exige.
4. `npm test` (pytest: unitarias + integración + E2E `tests/test_e2e_mvp.py`) pasa en verde en
   cada PR. Sin piso numérico de cobertura.
5. Toda funcionalidad nueva o corrección llega con pruebas que la ejercitan. La disciplina TDD
   (rojo→verde) queda a elección del autor.

## 3. Conventions

6. Las capas de `app/` se mantienen: `models/` (SQLAlchemy), `schemas/` (Pydantic de formularios),
   `repositories/` (acceso a datos), `services/` (reglas de negocio y transacciones), `routers/`
   (rutas web). El acceso a datos vive en `repositories/`; la regla de negocio en `services/`.
   Añadir o mover una capa es decisión registrada.
7. Dinero: CLP como **entero**, nunca float; separador de miles con punto.
8. Mensajes de commit: `Ámbito: descripción en español` (ej. `Miembros: …`, `Docs: …`,
   `Fase N: …`). Sin pies de "generado con IA".
9. La documentación oficial de `specs/` (`SPECS.md`, `UAT.md`, `COBERTURA.md`) se actualiza en el
   mismo PR que cambia el comportamiento que describe.

## 4. Branching & shipping

10. Todo cambio de código va en una rama y se integra por pull request. `main` está cerrada al
    trabajo directo.
11. **La autoría de git es del humano.** Sin `Co-Authored-By` de IA, sin pies "generated with".
    Se aplica en la fase `ship`.

## 5. Security & privacy floor

12. Ningún secreto se commitea: credenciales en `.env` (gitignored; plantilla `.env.example`);
    `SECRET_KEY` propia en todo entorno real. Sesiones firmadas, contraseñas con bcrypt, CSRF
    activo — mecanismos en `app/core/`.
13. Los datos del club permanecen en local (MySQL de XAMPP). Ninguna función envía datos fuera
    de localhost sin una enmienda que lo autorice.
14. Dependencia nueva: rango acotado en `requirements.txt` (o `package.json` si es de estilos) y
    justificación en el PR que la introduce.

## 6. UX / accessibility floor

15. UI en español, operable por teclado, con foco visible y contraste AA en formularios y tablas
    del panel; paleta Rojo/Negro/Blanco de `tailwind.config.js`.

## 7. Knowledge & decisions

16. Toda decisión significativa se registra en [decisions.md](./decisions.md) (fecha, opciones,
    por qué). Esta constitución es el registro de mayor orden.

## Definition of Done (the merge bar `verify` runs against)

- [ ] ruff limpio (principio 3).
- [ ] Suite pytest en verde (principio 4).
- [ ] Lo nuevo/corregido llega con pruebas (principio 5).
- [ ] Capas, CLP entero y `specs/` al día (principios 6-9).
- [ ] En rama, integrado por PR, autoría humana (principios 10-11).
- [ ] Sin secretos; datos locales; dependencias justificadas (principios 12-14).
- [ ] Barra de accesibilidad cumplida en la UI tocada (principio 15).
- [ ] Decisiones significativas registradas (principio 16).

## Amendment log (append-only)

| Date | Version | Change | Why |
|------|---------|--------|-----|
| 2026-10-26 | v1.0.0 | Constitución inicial ratificada (16 principios). | Arranque del flujo SDD del proyecto. |
