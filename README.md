# Sistema Gestión Pagos Osorno Runners

Sistema de gestión de pagos, membresías y finanzas del club **Osorno Runners**.

Documentación oficial en `specs/`:

- `specs/AGENT.md` — contexto y requisitos funcionales.
- `specs/SPECS.md` — especificación funcional verificada (F / RN / CA / D).
- `specs/PLAN.md` — plan técnico.
- `specs/TASK.md` — hoja de ruta de implementación.
- `specs/GUIA_DEMO.md` — guion de demostración del MVP paso a paso.

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

## Requisitos

- **Python 3.11+** (probado con 3.13).
- **Node.js + npm** (para compilar Tailwind).
- **XAMPP** con **MySQL/MariaDB** en marcha.

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

La semilla (paso 7) crea el catálogo de cuotas (5.000 / 5.000 / 15.000 CLP), las
categorías de egreso base, la cuenta bancaria para transferencias, la plantilla
de correo y un conjunto de miembros de ejemplo en los cuatro estados de
morosidad. Cada miembro recibe además su **obligación inicial** (Matrícula + la
cuota de su categoría; Flujo 1). Volver a ejecutarla **no duplica datos** e
imprime las credenciales de prueba (Admin, Tesorero y un Miembro).

## Configuración

Los valores se leen desde `.env` (ver `.env.example`). Nunca se versionan
credenciales. La clave de sesión se puede generar con:

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

Equivalente manual, si se prefiere hacerlo paso a paso:

```powershell
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
npm run css:dev        # en otra terminal, solo si se edita la interfaz
```

## Pruebas

La suite usa **SQLite en memoria** por defecto, así que no necesita XAMPP:

```powershell
.\venv\Scripts\python.exe -m pytest
```

Para ejecutarla contra MySQL, crear una base de prueba y apuntar
`TEST_DATABASE_URL` (nunca a la base de desarrollo):

```powershell
$env:TEST_DATABASE_URL = "mysql+pymysql://root:@localhost:3306/osorno_runners_test"
.\venv\Scripts\python.exe -m pytest
```

Revisión de estilo:

```powershell
.\venv\Scripts\python.exe -m ruff check app tests
```

La matriz de cobertura de los criterios de aceptación (CA-01 … CA-31) está en
[`specs/UAT.md`](specs/UAT.md).

## Optimización y producción

- `npm run css:build` genera el CSS de Tailwind **minificado** en
  `app/static/css/app.css` (la aplicación lo sirve desde `base.html`).
- `npm run seed` crea el esquema y, si la base ya existía, agrega los índices
  declarados que falten (T9.1) sin borrar datos.
- Los catálogos de niveles de cuota, cuenta bancaria y categorías de egreso se
  cachean 60 segundos en proceso y se invalidan al modificarlos (T9.4).

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
│   ├── config.py            Configuración y variables de entorno
│   ├── static/css/          Tailwind: input.css y app.css compilado
│   ├── static/js/           Alpine.js y utilidades
│   └── templates/           Plantillas Jinja2
├── specs/                   Documentación oficial
├── requirements.txt         Dependencias de Python
├── package.json             Compilación de Tailwind
├── tailwind.config.js       Paleta y rutas de contenido
└── .env.example             Plantilla de variables de entorno
```

## Estado

MVP en construcción. Hoja de ruta en `specs/TASK.md`.

- **Entorno local** (Uvicorn + MySQL de XAMPP) para el MVP; la publicación
  productiva y los respaldos quedan como trabajo **post-MVP** (Q-3).
