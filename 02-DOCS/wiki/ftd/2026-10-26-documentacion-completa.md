---
author: Rodrigo Garces
branch: main
status: in-progress
type: brief
title: Documentación completa del proyecto (wiki 02-DOCS)
description: Bootstrap del wiki 02-DOCS a partir de la documentación oficial del repositorio.
timestamp: 2026-10-26T23:10:00Z
topic: ftd
---

# Documentación completa del proyecto (wiki 02-DOCS)

## Intent

Construir la documentación completa del agente (wiki `02-DOCS/`) antes del primer commit del harness. Toda sesión futura debe encontrar el conocimiento del proyecto sin releer el repositorio completo. La fuente es la documentación oficial ya existente (README, `specs/`, `docs/`): se destila y se enlaza, nunca se duplica ni se mueve.

## Scope

**Incluido:** inicialización del wiki según el protocolo (inbox, raw, log, gaps, scores, vistas `.base`, Obsidian, `.rscignore`, `.gitignore`), 13 copias raw verificadas, 11 artículos compilados (proyecto/stack/meta/operations), índice canónico, mapa de conocimiento en `CLAUDE.md` y `AGENTS.md`, README de `01-TOOLS/`, registro de gaps reales y dashboard.

**Excluido:** mover o eliminar las fuentes originales (`specs/`, `docs/`, `README.md` quedan en su sitio — principio 9 de la constitución); tocar código de la aplicación; abrir rama (documentación pura, sin trabajo de código).

## Checklist

- [x] Inicialización del wiki completa — comprobación: existen `inbox/README.md`, `raw/`, `wiki/log.md`, `gaps.md`, `scores.json`, `.ingested.json`, `reports/`, `audits/`, `attachments/`, 3 vistas `.base`, `.obsidian/app.json`, `.gitignore` de 02-DOCS y `.rscignore`.
- [x] 13 copias raw verificadas — comprobación: cada archivo raw termina exactamente con el contenido de su original (verificación programática, no visual).
- [x] 11 artículos compilados — comprobación: los archivos existen con frontmatter OKF válido y el campo Raw apuntando a archivos reales de `raw/`.
- [x] Índice, log, gaps, scores y ledger coherentes — comprobación: cada `.md` de `wiki/` (salvo `index.md`/`log.md`) aparece en `index.md`; los enlaces internos de los artículos resuelven a archivos existentes.
- [x] Mapa de conocimiento en raíz — comprobación: `CLAUDE.md` y `AGENTS.md` tienen la sección con perfil + constitución + índice completo.

## Evidence

- **Raw 13/13 `ok`** — script PowerShell con `EndsWith` verbatim por archivo: `README`, `specs/*` (AGENT, SPECS, PLAN, TASK, UAT, COBERTURA, GUIA_DEMO), `docs/*` (DESPLIEGUE_LOCAL, POST_MVP), `CLAUDE.md`, `AGENTS.md`, `01-TOOLS/README.md`. Ledger `wiki/.ingested.json` con SHA-256 de cada fuente.
- **Artículos 17/17 en índice** — script de verificación: "índice: 17 articulos comprobados" (los 11 nuevos + constitución, decisions sdd, ftd y 3 de harness + plano-de-control = 17 `.md` en wiki).
- **Enlaces internos 123/123 resuelven** — misma corrida: "VERIFICACION OK - 123 enlaces internos resuelven; 17 articulos todos en el indice". Los enlaces relictos dentro de `raw/` se excluyen por diseño: son texto fuente preservado verbatim.
- **Puntajes calculados** (fórmula OKF) en `wiki/scores.json`; índice canónico en formato protocolo (sin frontmatter); dashboard autónomo en `wiki/dashboard.html` (gitignored); 5 gaps reales en `wiki/gaps.md`.

## Next

Commitear los archivos (autoría del humano, principio 11 de la constitución).
