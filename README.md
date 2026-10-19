# Sistema Gestión Pagos Osorno Runners

Sistema de gestión de pagos, membresías y finanzas del club **Osorno Runners**.

Documentación oficial:

- `specs/AGENT.md` — contexto y requisitos funcionales.
- `specs/SPECS.md` — especificación funcional verificada (F / RN / CA / D).
- `specs/PLAN.md` — plan técnico y decisiones.
- `specs/TASK.md` — hoja de ruta de implementación.
- `specs/UAT.md` — matriz de aceptación CA-01 … CA-31.
- `specs/COBERTURA.md` — matriz final de cobertura F / RN / CA.
- `specs/GUIA_DEMO.md` — guion de demostración del MVP paso a paso.
- `docs/DESPLIEGUE_LOCAL.md` — guía de ejecución local y consideraciones de
  producción futura.

## Stack

| Componente | Tecnología |
| :--- | :--- |
| Backend | **FastAPI** |
| Plantillas | **Jinja2** |
| Estilos | **Tailwind CSS** (paleta Rojo/Negro/Blanco) |
| Interactividad | **Alpine.js** |
| Base de datos | **MySQL/MariaDB** (XAMPP) |
| ORM | **SQLAlchemy** |
| Servidor ASGI | **Uvicorn** |
| Moneda | **CLP** (entero, separador de miles por punto) |
| Pruebas | **pytest** (SQLite en memoria por defecto) |
| Calidad | **ruff** |

## Requisitos

- **Python 3.11+** (probado con 3.13).
- **Node.js 18+ y npm** (para compilar Tailwind).
- **XAMPP** con **MySQL/MariaDB** en marcha.
- **Windows + PowerShell** para los atajos `npm run dev` / `npm start`
  (`dev.ps1`). En otro sistema operativo se puede ejecutar Uvicorn y Tailwind
  manualmente (ver más abajo).

## Instalación

```powershell
# 1. Entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Dependencias de Python
pip install -r requirements.txt

# 3. Dependencias de estilos (Tailwind)
npm install

# 4. Configuración
Copy-Item .env.example .env

# 5. Base de datos (MySQL/MariaDB de XAMPP)
& "C:\xampp\mysql\bin\mysql.exe" -u root -e "CREATE DATABASE IF NOT EXISTS osorno_runners CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 6. Compilar Tailwind
npm run css:build

# 7. Crear el esquema y cargar la semilla (idempotente)
.\venv\Scripts\python.exe -m app.seed
```

La semilla (paso 7) crea el catálogo de cuotas (5.000 / 5.000 / 15.000 CLP),
las categorías de egreso base, la cuenta bancaria para transferencias, la
plantilla de correo y un conjunto de miembros de ejemplo en los cuatro estados
de morosidad. Cada miembro recibe además su **obligación inicial** (Matrícula +
la cuota de su categoría; Flujo 1). Volver a ejecutarla **no duplica datos** e
imprime las credenciales de prueba (Admin, Tesorero y un Miembro).

## Configuración

Los valores se leen desde `.env` (ver `.env.example`). Nunca se versionan
credenciales.

| Variable | Uso | Valor por defecto |
| :--- | :--- | :--- |
| `APP_NAME` | Nombre visible de la aplicación y de `/salud`. | `Sistema Gestión Pagos Osorno Runners` |
| `ENTORNO` | Etiqueta informativa del entorno (`desarrollo`, `produccion`, etc.). | `desarrollo` |
| `SECRET_KEY` | Firma de la cookie de sesión. **Cámbiala** en cualquier entorno real. | Valor de ejemplo |
| `DB_HOST` | Host de MySQL/MariaDB. | `localhost` |
| `DB_PORT` | Puerto de MySQL/MariaDB. | `3306` |
| `DB_NAME` | Nombre de la base. | `osorno_runners` |
| `DB_USER` | Usuario de MySQL. | `root` |
| `DB_PASSWORD` | Contraseña de MySQL (vacía en XAMPP local). | *(vacía)* |
| `SESSION_COOKIE` | Nombre de la cookie de sesión. | `or_sesion` |
| `SESSION_MAX_AGE` | Duración de la sesión en segundos. | `28800` (8 h) |
| `TEST_DATABASE_URL` | Solo pruebas: URL de la base de test. Si se omite, pytest usa SQLite en memoria. | *(no definida)* |

Genera una clave de sesión propia con:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Ejecución (desarrollo)

Con el entorno ya instalado, basta un comando:

```powershell
npm run dev
```

Esto levanta el servidor en <http://127.0.0.1:8000>, compila Tailwind en modo
watch, abre el navegador y avisa si MySQL (XAMPP) no está respondiendo.
`Ctrl+C` detiene ambos procesos.

Otros atajos:

| Comando | Qué hace |
| :--- | :--- |
| `npm run dev` | Servidor + Tailwind en watch + navegador |
| `npm start` | Solo el servidor (sin recompilar CSS) |
| `npm run seed` | Carga/actualiza los datos de ejemplo (idempotente) |
| `npm run demo` | Prepara el caso de negociación de la demo |
| `npm test` | Ejecuta la suite de pruebas |
| `npm run lint` | Revisa el estilo con `ruff` |
| `npm run css:build` | Compila Tailwind una vez (minificado) |
| `npm run css:dev` | Compila Tailwind en modo watch |

Equivalente manual, si se prefiere hacerlo paso a paso:

```powershell
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
npm run css:dev        # en otra terminal, solo si se edita la interfaz
```

Comprueba el estado en <http://127.0.0.1:8000/salud>; debe responder con
`base_de_datos: "ok"`.

## Pruebas

La suite usa **SQLite en memoria** por defecto, así que no necesita XAMPP:

```powershell
npm test
# equivalente: .\venv\Scripts\python.exe -m pytest
```

Incluye pruebas unitarias, de integración y un recorrido **end-to-end** del MVP
(`tests/test_e2e_mvp.py`): alta → activación → pago → mora → negociación →
egresos → compras → reportes → landing.

Para ejecutarla contra MySQL, crear una base de prueba y apuntar
`TEST_DATABASE_URL` (nunca a la base de desarrollo):

```powershell
$env:TEST_DATABASE_URL = "mysql+pymysql://root:@localhost:3306/osorno_runners_test"
.\venv\Scripts\python.exe -m pytest
```

Revisión de estilo:

```powershell
npm run lint
# equivalente: .\venv\Scripts\python.exe -m ruff check app tests
```

Las matrices de aceptación y cobertura están en [`specs/UAT.md`](specs/UAT.md)
y [`specs/COBERTURA.md`](specs/COBERTURA.md).

## Optimización y producción

- `npm run css:build` genera el CSS de Tailwind **minificado** en
  `app/static/css/app.css` (la aplicación lo sirve desde `base.html`).
- `npm run seed` crea el esquema y, si la base ya existía, agrega los índices
  declarados que falten (T9.1) sin borrar datos.
- Los catálogos de niveles de cuota, cuenta bancaria y categorías de egreso se
  cachean 60 segundos en proceso y se invalidan al modificarlos (T9.4).
- El MVP está pensado para el **entorno local** (Uvicorn + MySQL de XAMPP).
  La publicación productiva, el proxy inverso/HTTPS y los respaldos quedan como
  trabajo **post-MVP** (Q-3). Ver
  [`docs/DESPLIEGUE_LOCAL.md`](docs/DESPLIEGUE_LOCAL.md).

## Demo guiada

Para una demostración completa del MVP (miembros, pagos, morosidad,
negociación, finanzas, compras y reportes):

```powershell
.\venv\Scripts\python.exe -m app.seed   # datos de ejemplo (idempotente)
.\venv\Scripts\python.exe -m app.demo   # caso de negociación (idempotente)
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

El guion paso a paso, con credenciales y datos esperados, está en
[`specs/GUIA_DEMO.md`](specs/GUIA_DEMO.md).

## Estructura del proyecto

```
OR/
├── app/
│   ├── main.py                 Aplicación FastAPI, middleware y /salud
│   ├── config.py               Configuración tipada desde .env
│   ├── database.py             Engine, sesión, esquema e índices
│   ├── dependencies.py         Dependencias de sesión y plantillas
│   ├── seed.py                 Esquema + semilla idempotente
│   ├── demo.py                 Datos del caso de negociación
│   ├── core/                   Seguridad, CSRF, errores, formato CLP, caché
│   ├── models/                 Modelos SQLAlchemy
│   ├── schemas/                Validación Pydantic de formularios
│   ├── repositories/           Acceso a datos y consultas
│   ├── services/               Reglas de negocio y transacciones
│   ├── routers/                Rutas web por módulo
│   ├── templates/              Plantillas Jinja2
│   └── static/                 CSS de Tailwind, JS y recursos
├── docs/                       Guía de despliegue local
├── specs/                      Documentación oficial
├── tests/                      Suite pytest (SQLite/MySQL)
├── dev.ps1                     Arranque local con verificaciones
├── requirements.txt            Dependencias de Python
├── package.json                Scripts de npm y Tailwind
├── tailwind.config.js          Paleta y rutas de contenido
└── .env.example                Plantilla de variables de entorno
```

## Estado

**MVP completo (fases 1 a 10).** Hoja de ruta y detalle en `specs/TASK.md`;
cobertura funcional en `specs/COBERTURA.md`.

### Pendientes post-MVP (no bloqueantes, Q-3)

- Definir servidor de publicación, proxy inverso y HTTPS.
- Configurar un usuario de MySQL con permisos mínimos para producción.
- Definir y automatizar la política de respaldos de la base de datos.
- Revisar el endurecimiento de producción (cookie `Secure`, `https_only`,
  logs y monitoreo).
