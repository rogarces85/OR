# OR — Sistema Gestión Pagos Osorno Runners

## Knowledge map

Antes de trabajar en este repositorio, lee en este orden:

1. **Perfil del humano** — [`02-DOCS/wiki/harness/user-profile.md`](02-DOCS/wiki/harness/user-profile.md): idioma (español), registro técnico, cómo cerrar cada respuesta.
2. **Constitución técnica** — [`02-DOCS/wiki/sdd/constitution.md`](02-DOCS/wiki/sdd/constitution.md): las 16 reglas no negociables del trabajo (pytest en verde, ruff único linter, pruebas siempre, commits en español, trazabilidad de matrices, autoría de commits del humano).
3. **Índice completo de la wiki** — [`02-DOCS/wiki/index.md`](02-DOCS/wiki/index.md): catálogo canónico de todos los artículos por tema con puntajes.

## Mapa rápido

| Qué necesitas saber | Leer |
|---|---|
| Qué es el proyecto, usuarios, estado | `02-DOCS/wiki/proyecto/vision.md` |
| Reglas de negocio (cuotas, mora, imputación, exenciones) | `02-DOCS/wiki/proyecto/dominio.md` |
| Arquitectura, estructura de `app/`, modelo de datos | `02-DOCS/wiki/proyecto/arquitectura.md` |
| Cómo instalar, correr y verificar el sistema | `02-DOCS/wiki/proyecto/operacion.md` |
| Cómo se prueba y qué está aceptado | `02-DOCS/wiki/proyecto/calidad.md` |
| Stack técnico (Python, FastAPI, BD, frontend) | `02-DOCS/wiki/stack/` |
| Decisiones técnicas y su porqué | `02-DOCS/wiki/sdd/decisions.md` |
| Herramientas operativas externas | `02-DOCS/wiki/operations/herramientas.md` |

La fuente normativa completa (lo que el wiki destila) sigue siendo **`specs/`** (especificación funcional y planes) y **`docs/`** (despliegue local y post-MVP); las copias inmutables de referencia viven en `02-DOCS/raw/`.
