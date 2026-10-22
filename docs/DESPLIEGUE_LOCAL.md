# Guía de despliegue local — Sistema Gestión Pagos Osorno Runners

> **Alcance:** ejecutar el MVP en un equipo local con **Uvicorn + MySQL/MariaDB
> de XAMPP** (P-8). La publicación productiva y los respaldos quedan como
> trabajo post-MVP (Q-3); al final se resumen las consideraciones a revisar
> cuando el sistema salga del entorno local.
>
> **Uso actual (vigente):** el sistema se usa de forma personal/local en el PC
> del usuario, en <http://127.0.0.1:8000>, con la base MySQL/MariaDB de XAMPP.
> No hay acceso público ni despliegue productivo. GitHub solo aloja el código y
> la documentación, no ejecuta la aplicación.

## 1. Requisitos

- Windows con **PowerShell** (los atajos `npm run dev` y `npm start` usan
  `dev.ps1`).
- **Python 3.11+** (probado con 3.13).
- **Node.js 18+** y npm.
- **XAMPP** instalado, con el módulo **MySQL** iniciado desde el Panel de
  Control.
- Puerto **8000** libre (o cambiar el puerto al ejecutar Uvicorn).
- La raíz del proyecto en `C:\xampp\htdocs\www\OR` (o ajustar las rutas de
  XAMPP si está en otra ubicación).

## 2. Preparar el entorno

```powershell
cd C:\xampp\htdocs\www\OR

# Entorno virtual de Python
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# Dependencias de estilos
npm install

# Configuración local
Copy-Item .env.example .env
```

Edita `.env` si es necesario:

- `SECRET_KEY`: reemplázala por una clave aleatoria.
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD`: deben coincidir
  con tu instalación de MySQL.
- En XAMPP el usuario `root` sin contraseña funciona solo en local.

Genera la clave de sesión con:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 3. Crear la base de datos

Con MySQL iniciado:

```powershell
& "C:\xampp\mysql\bin\mysql.exe" -u root -e "CREATE DATABASE IF NOT EXISTS osorno_runners CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

Verifica la conexión:

```powershell
& "C:\xampp\mysql\bin\mysql.exe" -u root -e "SHOW DATABASES LIKE 'osorno_runners';"
```

## 4. Crear el esquema y cargar la semilla

```powershell
npm run css:build
.\venv\Scripts\python.exe -m app.seed
```

`app.seed` es **idempotente**: crea el esquema si falta, agrega los índices
declarados que falten y carga catálogos, cuenta bancaria, plantilla de correo,
usuarios y miembros de ejemplo sin duplicar registros. Al final imprime las
credenciales de prueba.

Para preparar además el caso de negociación de la demo:

```powershell
.\venv\Scripts\python.exe -m app.demo
```

## 5. Ejecutar el sistema

### Opción recomendada

```powershell
npm run dev
```

- Levanta Uvicorn con recarga automática.
- Compila Tailwind en modo watch.
- Abre el navegador en <http://127.0.0.1:8000>.
- `Ctrl+C` detiene el servidor y el proceso de Tailwind.

### Opción manual

En una terminal:

```powershell
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

En otra terminal, solo si se edita la interfaz:

```powershell
npm run css:dev
```

### Verificación

- <http://127.0.0.1:8000/salud> debe responder
  `{"estado":"ok", ..., "base_de_datos":"ok"}`.
- <http://127.0.0.1:8000/> debe mostrar la landing.
- El inicio de sesión está en <http://127.0.0.1:8000/ingresar>.

Credenciales de la semilla:

| Rol | Correo | Contraseña |
| :-- | :-- | :-- |
| Administrador | `admin@osornorunners.cl` | `Admin1234` |
| Tesorero | `tesorero@osornorunners.cl` | `Tesorero1234` |
| Miembro | `ana.saldivar@example.com` | `Miembro1234` |

## 6. Pruebas y calidad

```powershell
npm test
npm run lint
```

La suite usa SQLite en memoria por defecto. Para MySQL, usa una base de prueba
separada:

```powershell
& "C:\xampp\mysql\bin\mysql.exe" -u root -e "CREATE DATABASE IF NOT EXISTS osorno_runners_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
$env:TEST_DATABASE_URL = "mysql+pymysql://root:@localhost:3306/osorno_runners_test"
.\venv\Scripts\python.exe -m pytest
```

> No apuntes `TEST_DATABASE_URL` a `osorno_runners`: la suite crea y destruye el
> esquema por prueba.

## 7. Detener, reiniciar y limpiar

Detener el servidor: `Ctrl+C` en la terminal de Uvicorn.

Reinicio **total** de los datos de desarrollo:

```powershell
& "C:\xampp\mysql\bin\mysql.exe" -u root -e "DROP DATABASE IF EXISTS osorno_runners; CREATE DATABASE osorno_runners CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
.\venv\Scripts\python.exe -m app.seed
.\venv\Scripts\python.exe -m app.demo
```

> Esto elimina todos los datos. Úsalo solo en desarrollo.

## 8. Problemas comunes

| Síntoma | Causa / solución |
| :-- | :-- |
| `/salud` responde `base_de_datos: "error"` (HTTP 503) | MySQL de XAMPP está detenido. Inícialo desde el Panel de Control. |
| Error de conexión al arrancar | Revisa `.env`, que la base exista y que el usuario tenga permisos. |
| La página se ve sin estilos | Falta `npm run css:build` o no se está sirviendo `app/static/css/app.css`. |
| `npm run dev` no encuentra `venv` | Crea el entorno y ejecuta `pip install -r requirements.txt`. |
| Puerto 8000 ocupado | Ejecuta `uvicorn app.main:app --reload --port 8010` o libera el puerto. |
| Credenciales rechazadas | Vuelve a ejecutar `python -m app.seed` (idempotente). |
| No aparecen morosos de más de 6 meses | Ejecuta `python -m app.demo` para preparar el caso de negociación. |
| Tailwind muestra un aviso de `caniuse-lite` | Es informativo; actualiza con `npx update-browserslist-db@latest` si lo deseas. |

## 9. Consideraciones para producción futura (post-MVP)

El MVP está configurado para uso local. El plan de publicación, HTTPS y
respaldos está cerrado documentalmente en [`POST_MVP.md`](POST_MVP.md); la
ejecución queda pendiente de servidor y dominio. Antes de publicarlo:

1. **Servidor y proceso:** definir el host, ejecutar Uvicorn sin `--reload`
   (por ejemplo, con un servicio de Windows, `systemd` o un contenedor) y
   considerar varios workers según la carga.
2. **Proxy inverso y HTTPS:** publicar detrás de Nginx/Caddy, con Cloudflare
   Tunnel desde el PC local o con un proxy similar; redirigir HTTP a HTTPS y
   configurar los encabezados de proxy.
3. **Cookie de sesión:** cambiar `https_only=False` en `app/main.py` a `True`,
   mantener `HttpOnly` y `SameSite=Lax`, y usar una `SECRET_KEY` exclusiva del
   servidor.
4. **Base de datos:** crear un usuario de MySQL con permisos mínimos sobre
   `osorno_runners`, no usar `root`, y restringir el acceso de red.
5. **Respaldos:** definir frecuencia, retención y pruebas de restauración. Como
   base, un respaldo lógico con `mysqldump`:
   ```powershell
   & "C:\xampp\mysql\bin\mysqldump.exe" -u root --databases osorno_runners > respaldo_osorno_runners.sql
   ```
   En producción, programarlo y almacenarlo fuera del servidor.
6. **Operación:** recolectar logs, monitorear `/salud`, definir quién administra
   usuarios/contraseñas y documentar el procedimiento de recuperación.
7. **Secretos:** no versionar `.env`; usar variables del entorno o un gestor de
   secretos del servidor.

Estos puntos corresponden a **Q-3** y no bloquean el MVP local.
