# Wiki Log

Newest first. One entry per maintenance/ingestion/improvement event, in this
shape: `## [YYYY-MM-DD HH:MM] {kind} — {title}` with a short body.

## [2026-10-26 23:55] bootstrap — ingest inicial

Ingesta de bootstrap de la wiki: **13 fuentes → 11 artículos**, más índice
canónico, vistas `.base`, ledger de hashes (`wiki/.ingested.json`) y dashboard.
Fuentes: `README.md`, `specs/` (7 documentos), `docs/` (2), `CLAUDE.md`,
`AGENTS.md` y `01-TOOLS/README.md` — copiadas (nunca movidas) a
`raw/{proyecto,meta,operations}/` y verificadas byte a byte.

## [2026-10-26 23:50] cosmetic — enlace en la constitución P16

Corrección cosmética en `wiki/sdd/constitution.md` (principio 16): la ruta
`02-DOCS/wiki/sdd/decisions.md` pasa a ser un enlace markdown al archivo. Sin
cambio de versión ni de sentido.

## [2026-10-26 23:45] maintenance — inicialización del protocolo

Scaffolding completo del wiki según el protocolo: `inbox/`, `raw/` (con
`worklog/`), `audits/`, `wiki/reports/`, `attachments/`, 3 vistas `.base`,
configuración de Obsidian, `.gitignore` y `.rscignore` de `02-DOCS/`.
