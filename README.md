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

```powershell
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Durante el desarrollo de la interfaz, recompilar Tailwind con:

```powershell
npm run css:dev
```

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
