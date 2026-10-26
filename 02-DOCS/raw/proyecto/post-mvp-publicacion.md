# POST_MVP.md — Plan post-MVP

> Source: docs/POST_MVP.md
> Collected: 2026-10-26
> Published: Unknown

# Plan post-MVP — publicación productiva, HTTPS y respaldos

> **Estado:** 📋 **Plan cerrado documentalmente; ejecución pendiente.**
> **Decisión:** Q-3. El MVP se mantiene en el entorno local (Uvicorn + MySQL de
> XAMPP). Este documento define cómo publicarlo cuando exista servidor, dominio
> y responsables de operación.
>
> **Uso actual:** exclusivamente personal/local en el PC del usuario, con
> Uvicorn en <http://127.0.0.1:8000> y MySQL/MariaDB de XAMPP. No hay acceso
> público, VPS, Cloudflare ni despliegue productivo. GitHub solo almacena el
> código.
>
> **No se ha desplegado nada en producción ni se han creado credenciales,
> dominios, certificados o respaldos reales.** Este archivo cierra el pendiente
> documental para que la ejecución futura sea una tarea acotada y verificable.

## 1. Alcance

Al publicar el sistema se deben resolver, como mínimo:

1. Servidor de aplicación y proceso de ejecución.
2. Proxy inverso y HTTPS.
3. Base de datos MySQL/MariaDB de producción y usuario dedicado.
4. Respaldo, retención y restauración de la base de datos.
5. Endurecimiento de sesión, secretos, red y monitoreo.
6. Procedimiento de despliegue y reversión.

Queda fuera de este plan cualquier cambio funcional del MVP (nuevas pantallas,
reportes o reglas de negocio). Tampoco incluye integración SMTP: los avisos de
morosidad siguen siendo manuales mediante `mailto:` (P-2).

## 2. Arquitectura de referencia

Hay tres alternativas válidas. La decisión final depende del proveedor, la
disponibilidad esperada y el equipo que operará el sistema.

### Opción A — Docker Compose + Caddy (recomendada para producción)

- Contenedor de aplicación con Uvicorn.
- Contenedor MySQL 8/MariaDB con volumen persistente.
- Caddy como proxy inverso y terminación HTTPS automática (Let's Encrypt).
- Respaldo programado con `mysqldump` desde el host o un contenedor dedicado.
- Ventajas: despliegue reproducible, HTTPS automático y aislamiento.
- Requisitos: Docker Engine + Compose, dominio apuntando al servidor y puertos
  80/443 abiertos.

### Opción B — VPS Linux + Nginx + systemd

- Ubuntu/Debian LTS con Uvicorn gestionado por `systemd`.
- Nginx como proxy inverso y Certbot para certificados.
- MySQL/MariaDB instalado en el servidor o gestionado por el proveedor.
- Respaldo programado con `mysqldump` y `cron`/`systemd timer`.
- Ventajas: menos capas y control directo del sistema.
- Requisitos: administración de Linux, firewall y actualizaciones de seguridad.

### Opción C — Cloudflare Tunnel sobre el PC local

- `cloudflared` se ejecuta en el PC y conecta **salida** hacia Cloudflare; no
  requiere IP pública ni abrir puertos en el router.
- Cloudflare termina el HTTPS público y enruta hacia `127.0.0.1:8000`.
- La aplicación y MySQL de XAMPP siguen siendo locales; la base **no** se
  expone.
- Ventajas: dominio y HTTPS sin migrar la base; útil para uso personal o piloto.
- Limitaciones: el PC debe estar encendido y con Internet estable; no ofrece
  alta disponibilidad. Requiere cuenta Cloudflare y un dominio.
- No confundir con Cloudflare Pages/Workers: no ejecutan este stack Python +
  MySQL. Para publicar de forma permanente se prefiere la opción A o B.

### Comparación rápida

| Criterio | Docker + Caddy | VPS + Nginx/systemd | Cloudflare Tunnel |
| :--- | :--- | :--- | :--- |
| Dónde corre la app | Servidor con Docker | VPS Linux | PC local |
| Disponibilidad | Alta | Alta | Depende del PC |
| HTTPS | Automático | Certbot | Cloudflare |
| Base de datos | Contenedor con volumen | MySQL del VPS | XAMPP local |
| Complejidad inicial | Media | Media | Baja |
| Recomendado para | Producción | Producción | Uso personal/piloto |

En las opciones A y B el flujo es: **cliente → HTTPS (proxy) → Uvicorn →
MySQL**. En la opción C: **cliente → Cloudflare → `cloudflared` → Uvicorn →
MySQL local**.

## 3. Requisitos previos

- Dominio o subdominio definido (por ejemplo, `pagos.osornorunners.cl`).
- Según la opción: VPS con IP pública (A/B) o PC local con salida a Internet
  (C).
- Registro DNS `A`/`AAAA` hacia el servidor (A/B) o túnel de Cloudflare (C).
- Servidor o PC con acceso administrativo y reloj sincronizado.
- MySQL/MariaDB con base `osorno_runners` y usuario dedicado.
- `SECRET_KEY` de producción generada aparte.
- Responsable de operación, respaldos y restauración.
- Ventana de mantenimiento acordada con el club.

## 4. Variables de producción

No reutilizar el `.env` de desarrollo. Como referencia:

```dotenv
APP_NAME="Sistema Gestión Pagos Osorno Runners"
ENTORNO=produccion
SECRET_KEY=<clave-aleatoria-exclusiva-de-produccion>

DB_HOST=<host-mysql>
DB_PORT=3306
DB_NAME=osorno_runners
DB_USER=<usuario-dedicado>
DB_PASSWORD=<contraseña-fuerte>

SESSION_COOKIE=or_sesion
SESSION_MAX_AGE=28800
```

Buenas prácticas:

- Guardar los secretos en el gestor de secretos del servidor o en variables de
  entorno, nunca en Git.
- Usar un usuario MySQL con permisos solo sobre `osorno_runners` (sin `GRANT`,
  sin acceso a otras bases).
- Restringir el acceso a MySQL a la red interna o a la IP de la aplicación.
- No usar `root` ni contraseñas vacías.

## 5. Cambios de código/configuración requeridos antes de publicar

Estos cambios **no están aplicados** en el MVP local:

1. **Cookie segura:** hoy `SessionMiddleware` usa `https_only=False` en
   `app/main.py`. En producción debe ser `True` detrás de HTTPS.
2. **Configuración por entorno:** exponer `https_only` (por ejemplo,
   `SESSION_HTTPS_ONLY=true`) en `app/config.py` y `.env.example`, en lugar de
   un valor fijo.
3. **Hosts permitidos:** evaluar `TrustedHostMiddleware` con el dominio real.
4. **Proxy:** ejecutar Uvicorn con `--proxy-headers` y
   `--forwarded-allow-ips` acotado al proxy.
5. **Proceso:** ejecutar sin `--reload`; definir workers según la carga.
6. **Estáticos:** compilar Tailwind con `npm run css:build` durante el build o
   despliegue; `app/static/css/app.css` no se versiona.
7. **Esquema:** ejecutar `python -m app.seed` una vez en la base nueva
   (idempotente) o definir una tarea de inicialización equivalente. Para
   cambios futuros de esquema, evaluar migraciones formales (Alembic).
8. **Logs:** enviar stdout/stderr al sistema de logs del servidor; no registrar
   contraseñas ni secretos.
9. **Monitoreo:** usar `/salud` como health check y alertar si responde 503.
10. **CSRF/sesión:** mantener `HttpOnly`, `SameSite=Lax` y el token CSRF ya
    implementados.

## 6. Despliegue (pasos de referencia)

### Opción A — Docker Compose

1. Crear el servidor y el registro DNS.
2. Instalar Docker Engine y Compose.
3. Clonar el repositorio en el servidor.
4. Crear el archivo de variables de producción fuera de Git.
5. Construir la imagen de la aplicación y compilar Tailwind.
6. Levantar MySQL, esperar su disponibilidad y ejecutar la inicialización.
7. Levantar la aplicación y Caddy.
8. Verificar `/salud`, la landing y un inicio de sesión de prueba.
9. Configurar respaldos y monitoreo.
10. Documentar la versión desplegada y el procedimiento de reversión.

### Opción B — VPS + Nginx + systemd

1. Crear el servidor, usuario de despliegue y firewall (22/80/443).
2. Instalar Python, Node.js, Nginx, MySQL/MariaDB y Certbot.
3. Crear `venv`, instalar `requirements.txt` y compilar Tailwind.
4. Configurar `.env` de producción y la base de datos.
5. Crear la unidad `systemd` de Uvicorn (sin `--reload`, con `Restart=always`).
6. Configurar Nginx como proxy a `127.0.0.1:8000` y los encabezados
   `X-Forwarded-*`.
7. Obtener el certificado con Certbot y activar la redirección a HTTPS.
8. Verificar `/salud`, landing, login y permisos por rol.
9. Configurar respaldos, logs y monitoreo.
10. Documentar la versión y el procedimiento de reversión.

### Opción C — Cloudflare Tunnel (PC local)

1. Tener el dominio administrado en Cloudflare y el PC con salida a Internet.
2. Instalar `cloudflared` en Windows.
3. Autenticar y crear el túnel (por ejemplo, `or-pagos`).
4. Configurar el `ingress` para enviar el dominio a
   `http://127.0.0.1:8000`.
5. Registrar el hostname del túnel en DNS.
6. Ejecutar `cloudflared tunnel run or-pagos` y comprobar el acceso externo.
7. Instalar `cloudflared` como servicio para que arranque con Windows.
8. Ejecutar Uvicorn sin `--reload`, con `--proxy-headers` y
   `--forwarded-allow-ips` acotado al proxy local.
9. Verificar `/salud`, landing, login y permisos por rol.
10. Mantener MySQL en XAMPP solo local; no abrir 3306 ni publicar el puerto
    8000 en el router.
11. Programar respaldos locales y copiarlos fuera del PC.
12. Documentar que la disponibilidad depende de que el PC permanezca encendido.

## 7. Respaldo y restauración

### Respaldo lógico

```bash
mysqldump \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  --set-gtid-purged=OFF \
  -u "$DB_USER" -p"$DB_PASSWORD" \
  "$DB_NAME" > "/respaldos/osorno_runners_$(date +%Y%m%d_%H%M%S).sql"
```

En el PC local con XAMPP se puede usar
`C:\xampp\mysql\bin\mysqldump.exe` y programar la tarea con el Programador de
tareas de Windows. Guardar la copia fuera de la carpeta del proyecto y, si es
posible, fuera del PC.

### Política mínima propuesta

- Frecuencia: diaria.
- Retención: 30 días en el servidor y 90 días fuera de él.
- Almacenamiento: disco cifrado o almacenamiento de objetos con acceso
  restringido.
- Verificación: revisar el tamaño y la cabecera del archivo; alertar si falla.
- **Prueba de restauración:** mensual, sobre una base temporal, verificando
  conteos básicos y un inicio de sesión.
- Documentar quién ejecuta, dónde se guarda y por cuánto tiempo.

### Restauración de prueba

```bash
mysql -u "$DB_USER" -p"$DB_PASSWORD" osorno_runners_restauracion < respaldo.sql
```

Nunca restaurar directamente sobre producción sin una copia previa y una
ventana de mantenimiento.

## 8. Seguridad y operación

- HTTPS obligatorio; redirigir HTTP a HTTPS.
- Firewall: exponer solo 80/443; SSH restringido por IP o clave.
- Actualizaciones de sistema y dependencias programadas.
- Contraseñas de usuarios del sistema con gestión individual; no compartir la
  cuenta de administrador.
- Revisar permisos de Admin/Tesorero y dar de baja usuarios que dejen el club.
- Copias de seguridad cifradas y acceso mínimo.
- Monitoreo de `/salud`, espacio en disco, errores 5xx y duración de respaldos.
- Registro de cambios de versión y plan de reversión.
- Revisar los logs sin exponer datos personales innecesarios.

## 9. Criterios de cierre de la publicación

La publicación se considerará terminada cuando:

- [ ] El dominio resuelve al servidor y HTTPS funciona sin advertencias.
- [ ] `/salud` responde `base_de_datos: "ok"` desde fuera del servidor.
- [ ] La landing y el inicio de sesión funcionan por HTTPS.
- [ ] Admin y Tesorero acceden a sus módulos; un Miembro solo ve su estado.
- [ ] La cookie de sesión es `Secure`, `HttpOnly` y `SameSite=Lax`.
- [ ] La base usa un usuario dedicado y no `root`.
- [ ] Existe un respaldo automático y una restauración de prueba exitosa.
- [ ] Los logs y el monitoreo de `/salud` están activos.
- [ ] El procedimiento de despliegue y reversión está documentado.
- [ ] El club designó responsables de operación y respaldos.

## 10. Riesgos y pendientes de decisión

| Tema | Riesgo | Decisión necesaria |
| :--- | :--- | :--- |
| Proveedor | Costos, región y soporte | Elegir VPS/proveedor y responsable |
| Arquitectura | Docker vs. systemd | Definir opción A o B |
| Dominio | DNS, certificados y renovación | Confirmar dominio y acceso |
| Base de datos | Pérdida de datos o accesos indebidos | Definir usuario, red y respaldos |
| Operación | Falta de monitoreo o respuesta a incidentes | Asignar responsables y alertas |
| Correo | Dependencia del cliente del Tesorero | Mantener `mailto:` o evaluar SMTP en otro ciclo |

## 11. Estado final del cierre documental

- **MVP local:** completo y verificado (fases 1 a 10).
- **Post-MVP:** planificado y cerrado documentalmente; **no ejecutado**.
- **Próximo paso cuando exista infraestructura:** elegir la opción A o B,
  aplicar los cambios de la sección 5 y ejecutar la lista de la sección 9.
