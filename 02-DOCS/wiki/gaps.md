# Knowledge Gaps

Append-only log of wanted-but-missing topics. Entries are flagged
`[FILLED YYYY-MM-DD]` when an Improve pass writes the article — never
deleted.

## [2026-10-26] gap | Integración continua (CI)

Source: El repositorio tiene GitHub pero no workflow: `npm test` y
`npm run lint` solo corren a mano.

Mentioned in: [Calidad, pruebas y aceptación](proyecto/calidad.md)

Suggested topic: meta

Status: open

## [2026-10-26] gap | Respaldo automático de la base de datos

Source: El plan de respaldos existe documentalmente (`docs/POST_MVP.md`,
Q-3) pero no hay ninguna copia programada de `osorno_runners`.

Mentioned in: [Operación local](proyecto/operacion.md)

Suggested topic: operations

Status: open

## [2026-10-26] gap | Publicación productiva post-MVP (Q-3)

Source: El plan está cerrado en `docs/POST_MVP.md` (Docker/Caddy, VPS/Nginx
o Cloudflare Tunnel, HTTPS) pero pendiente de ejecución; al ejecutarse
necesita un artículo propio.

Mentioned in: [Operación local](proyecto/operacion.md)

Suggested topic: operations

Status: open

## [2026-10-26] gap | Página de seguridad y manejo de secretos

Source: Se menciona disperso (`.env`tipado, RBAC, bcrypt) pero no existe una
página consolidada de amenazas, sesiones y secretos del sistema.

Mentioned in: [FastAPI — aplicación, rutas y seguridad](stack/fastapi.md)

Suggested topic: stack

Status: open

## [2026-10-26] gap | Modelo de datos con esquema de referencia

Source: [Arquitectura por capas](proyecto/arquitectura.md) resume el modelo;
el detalle completo vive en `specs/PLAN.md §4`. Si el esquema crece, conviene
un artículo propio con el diagrama ER.

Mentioned in: [Arquitectura por capas](proyecto/arquitectura.md)

Suggested topic: proyecto

Status: open
