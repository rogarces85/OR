# GUIA_DEMO.md — Guion de demostración

> Source: specs/GUIA_DEMO.md
> Collected: 2026-10-26
> Published: Unknown

# Guía de demo — Sistema Gestión Pagos Osorno Runners

Recorrido guiado de punta a punta para mostrar el MVP en funcionamiento
(fases 1 a 7): miembros, membresías, pagos, morosidad, negociación, finanzas,
compras y reportes con exportación.

- **Duración:** ~15 minutos.
- **Requisitos cubiertos:** F-01 a F-25, RN-01 a RN-25 y los criterios de
  aceptación CA-01 a CA-15.

---

## 1. Antes de empezar

Necesitas **MySQL de XAMPP encendido** y el entorno ya instalado
(`venv`, dependencias y CSS compilado; ver el `README.md`).

```powershell
# 1) Cargar la semilla (idempotente: no duplica datos)
.\venv\Scripts\python.exe -m app.seed

# 2) Preparar el caso de negociación (idempotente; deja a Carla con >6 meses)
.\venv\Scripts\python.exe -m app.demo

# 3) Levantar el servidor (recarga automática al guardar)
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Abre el navegador en **http://127.0.0.1:8000**.

> Comprobación rápida de la base de datos: http://127.0.0.1:8000/salud debe
> responder `{"estado":"ok","base_de_datos":"ok"}`.

### Credenciales de prueba

| Rol | Correo | Contraseña |
| :-- | :-- | :-- |
| Administrador | `admin@osornorunners.cl` | `Admin1234` |
| Tesorero | `tesorero@osornorunners.cl` | `Tesorero1234` |
| Miembro | `ana.saldivar@example.com` | `Miembro1234` |

---

## 2. Datos de ejemplo (qué esperar)

### Miembros

| Miembro | Categoría | Estado | Uso en la demo |
| :-- | :-- | :-- | :-- |
| Ana Saldívar | Activo (alumna) | Al día (verde) | Casos de abono y carpeta del miembro |
| Bruno Mora | Activo (alumno) | 2 meses (naranjo) | Pago que cubre deuda antigua |
| Carla Deudora | Activo (alumna) | 5 meses (rojo); con `app.demo`, 7 | Aviso y negociación de deuda |
| Diego Exento | Membresía (apoyo) | Exento | Cuotas exentas, sin cobros ni avisos |
| Elena Pendiente | Activo (alumna) | Incorporación pendiente | Activación con el pago inicial |

### Catálogo de cuotas

| Concepto | Monto |
| :-- | --: |
| Matrícula (pago único) | $ 5.000 |
| Membresía Estándar (mensual, apoyo) | $ 5.000 |
| Membresía Activa (mensual, alumno) | $ 15.000 |

Pago inicial de un alumno = Matrícula + Membresía Activa = **$ 20.000**.

### Otros datos

- Compra del club **“Compra de polerones de entrenamiento”** ($ 250.000) con un
  cargo de **$ 25.000** asignado a Ana.
- Cuenta bancaria para transferencias y plantilla de correo (aviso de morosidad).

---

## 3. Guion de la demo

### Acto 1 — Acceso y roles (F-02, F-03, RN-06, RN-07)

| Paso | Acción | Qué observar |
| --: | :-- | :-- |
| 1 | Abre `/` (landing) y pulsa **Ingresar**. | Página pública del club. |
| 2 | Ingresa con credenciales incorrectas. | Mensaje genérico, sin revelar si el correo existe. |
| 3 | Entra como **Administrador**. | Redirige al panel de gestión (`/miembros`). |
| 4 | Cierra sesión y entra como **Miembro** (`ana…`). | Solo ve su carpeta (`/mi/estado`). |
| 5 | Con el miembro logueado, escribe `/reportes`. | Página **403 · Acceso denegado** (RBAC). |

### Acto 2 — Miembros y alta (F-01, F-04, F-05, RN-01, RN-25)

| Paso | Acción | Qué observar |
| --: | :-- | :-- |
| 1 | Entra a **Miembros** (`/miembros`). | Listado con buscador/filtros y colores de morosidad. |
| 2 | Pulsa **Nuevo miembro** y da de alta “Prueba Demo”. | Validación de campos y correo único. |
| 3 | Repite el alta con un correo ya existente. | Mensaje de validación en español. |
| 4 | Abre la ficha del recién creado. | Se registró la **obligación inicial** (Matrícula + cuota). |
| 5 | Abre la ficha de **Diego Exento**. | Cuotas exentas; no genera deuda (RN-05). |
| 6 | En la ficha de un miembro, cambia la **categoría**. | Ajusta la cuota mensual impaga y deja **historial** (RN-25). |

> La **Matrícula** es un cargo único de incorporación y **no** cuenta para la
> morosidad, que solo considera cuotas mensuales (F-11).

### Acto 3 — Activación con pago inicial (RN-02, RN-03, RN-17)

Usa a **Elena Pendiente** (incorporación pendiente).

| Paso | Acción | Qué observar |
| --: | :-- | :-- |
| 1 | Abre la ficha de **Elena** → sección **Activación de la membresía**. | Total del pago inicial requerido: **$ 20.000**. |
| 2 | Pulsa **Registrar pago** e ingresa **$ 10.000**. | El pago queda **parcial**: el miembro **no** se activa. |
| 3 | Registra el saldo restante (**$ 10.000**). | El pago inicial queda completo. |
| 4 | Pulsa **Activar membresía**. | La situación pasa a **Activa** (RN-02). |
| 5 | Revisa la tabla de cuotas. | La Matrícula se imputó **primero** (deuda más antigua; RN-17). |

### Acto 4 — Pagos: imputación y abono (RN-17, RN-18, RN-03)

Usa a **Bruno Mora** (2 meses de deuda).

| Paso | Acción | Qué observar |
| --: | :-- | :-- |
| 1 | Abre **Ingresos** (`/pagos`) → **Registrar pago**. | Se ve la **deuda vigente** y el **saldo a favor**. |
| 2 | Rellena un pago que cubra la deuda antigua. | La imputación va de la deuda **más antigua** a la más reciente. |
| 3 | Registra un pago **mayor** a la deuda. | El excedente queda como **abono** para la siguiente cuota (RN-18). |
| 4 | Revisa la ficha del miembro. | “Saldo a favor” refleja el abono. |

> **Corte del día 5 (RN-03):** un pago posterior al día 5, referido al mes en
> curso, se imputa al ciclo siguiente. Según la fecha en que hagas la demo, el
> mes en curso puede redirigirse al mes siguiente.

### Acto 5 — Morosidad, colores y aviso (F-11, F-22, F-23, RN-13, RN-21)

| Paso | Acción | Qué observar |
| --: | :-- | :-- |
| 1 | Entra a **Morosidad** (`/morosidad`). | Resumen por color y filtros. |
| 2 | Observa la clasificación. | Verde = al día, **naranjo** = hasta 3 meses, **rojo** = más de 3. |
| 3 | En la fila de **Carla**, pulsa **Generar aviso**. | Se abre el aviso con el **correo sugerido**. |
| 4 | Revisa destinatario, asunto y cuerpo. | Incluye deuda, detalle y datos de la cuenta (plantilla D-21). |
| 5 | Pulsa **Abrir en mi correo (mailto)**. | Abre tu cliente de correo con el texto listo (CA-15). |
| 6 | Pulsa **Marcar como enviado**. | El aviso queda registrado en `/morosidad/avisos`. |

> La morosidad solo considera **meses cerrados**: el mes en curso no cuenta (P-5).

### Acto 6 — Negociación de deuda (F-24, RN-22, P-6)

Requiere haber ejecutado `python -m app.demo` (deja a Carla con **7 meses**).

| Paso | Acción | Qué observar |
| --: | :-- | :-- |
| 1 | Entra a **Negociaciones** (`/negociaciones`). | Carla aparece en “Morosos elegibles (más de 6 meses)”. |
| 2 | Propón una negociación con **descuento 20%**. | Se calcula el **monto negociado** sobre la deuda. |
| 3 | Pulsa **Aceptar**. | La deuda negociada deja de contar para el color (P-6). |
| 4 | Revisa **Morosidad**: Carla ya no está en rojo. | El color se recalcula descontando lo negociado. |
| 5 | Vuelve a Negociaciones y pulsa **Registrar pago**. | La negociación queda **Pagada** (regularizada). |

### Acto 7 — Finanzas (F-16, F-17, F-18, RN-10, RN-12)

| Paso | Acción | Qué observar |
| --: | :-- | :-- |
| 1 | Entra a **Finanzas** (`/finanzas`). | Categorías base + formularios de egreso, activos y gastos fijos. |
| 2 | **Registrar egreso** (p. ej. “Arriendo sede”, $ 30.000). | Aparece en el listado y en el total del periodo. |
| 3 | **Agregar categoría** y luego **Desactivar/Activar**. | Las categorías base no se desactivan (RN-10). |
| 4 | **Registrar activo** y **Registrar gasto fijo**. | Se listan; el activo genera además un egreso. |

### Acto 8 — Compras y cargos (F-25, RN-23)

| Paso | Acción | Qué observar |
| --: | :-- | :-- |
| 1 | Entra a **Compras** (`/compras`). | Compra de polerones con sus ítems. |
| 2 | Asigna un ítem a un alumno y pulsa **Generar cargos**. | Se crea un **cargo separado** de la mora de cuotas (RN-23). |
| 3 | En “Cargos a alumnos”, pulsa **Saldar** (transferencia). | El cargo pasa a **Pagado**. |
| 4 | Vuelve a **Morosidad**. | El cargo **no** alteró el color de mora del alumno. |

### Acto 9 — Reportes y exportación (F-19, F-20, F-21, CA-10, CA-11, CA-12)

| Paso | Acción | Qué observar |
| --: | :-- | :-- |
| 1 | Entra a **Reportes** (`/reportes`) y ajusta **Desde/Hasta**. | Totales de **Ingresos**, **Egresos** y **Balance**. |
| 2 | Pulsa **Exportar XLSX**. | Descarga un `.xlsx` con **los mismos totales** que la pantalla. |
| 3 | Abre `/reportes/informe/1` (Ana) y cambia el **Año**. | Calendario con estado y montos por mes. |
| 4 | Pulsa **Exportar PDF**. | Descarga un PDF con estados y montos del informe. |
| 5 | Elige un periodo **sin movimientos**. | Muestra “No hay contenido para exportar.” |

### Acto 10 — Carpeta del miembro (UI-05)

| Paso | Acción | Qué observar |
| --: | :-- | :-- |
| 1 | Cierra sesión y entra como **Ana**. | Redirige a `/mi/estado`. |
| 2 | Revisa su estado de cuenta. | Cuotas, deuda y datos para transferencia; sin acceso a la gestión. |

---

## 4. Cierre y limpieza

```powershell
# Detener el servidor:  Ctrl + C  en la terminal de Uvicorn

# Volver a dejar los datos de ejemplo como al inicio (idempotente):
.\venv\Scripts\python.exe -m app.seed
```

La semilla **no duplica** datos: se puede ejecutar las veces que quieras. Para un
reinicio **total** de la base, elimínala y vuelve a crear el esquema y la semilla:

```powershell
& "C:\xampp\mysql\bin\mysql.exe" -u root -e "DROP DATABASE IF EXISTS osorno_runners; CREATE DATABASE osorno_runners CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
.\venv\Scripts\python.exe -m app.seed
.\venv\Scripts\python.exe -m app.demo
```

---

## 5. Problemas comunes

| Síntoma | Causa / solución |
| :-- | :-- |
| `/salud` responde `base_de_datos: "error"` (HTTP 503) | MySQL de XAMPP está apagado. Inícialo desde el panel de XAMPP. |
| Error de conexión al arrancar | Falta `.env` (`Copy-Item .env.example .env`) o la base `osorno_runners` no existe. |
| La página se ve “sin estilos” | Falta compilar Tailwind: `npm run css:build`. |
| “No hay morosos de más de 6 meses” | No ejecutaste `python -m app.demo`. |
| Puerto 8000 ocupado | Usa otro puerto: `--port 8010`. |
| Credenciales rechazadas | Vuelve a cargar la semilla: `python -m app.seed`. |

> Documentación relacionada: `README.md`, `specs/SPECS.md` (F / RN / CA),
> `specs/PLAN.md` y `specs/TASK.md` (hoja de ruta).
