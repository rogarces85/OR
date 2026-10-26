# PLAN.md — Plan técnico del MVP

> Source: specs/PLAN.md
> Collected: 2026-10-26
> Published: Unknown

# Plan Técnico del MVP — Sistema Gestión Pagos Osorno Runners

> **Fuentes principales:** `specs/AGENT.md` y `specs/SPECS.md`.
> **Naturaleza del documento:** plan **técnico** (cómo se construye lo definido en las especificaciones).
> **Convenciones de estado:** cada decisión se marca como **Confirmada** (viene de `AGENT.md`/`SPECS.md`), **Propuesta** (recomendación técnica de este plan) o **Pendiente** (requiere decisión antes de codificar). Ver sección 14.

---

## 1. Arquitectura general

**Estilo:** **monolito modular por capas**. Para el tamaño del MVP (un club, pocos cientos de miembros) no se justifican microservicios; un monolito con módulos de dominio bien separados es más simple de desplegar y mantener.

**Capas y responsabilidades:**

```
┌───────────────────────────────────────────────────────────────┐
│ Presentación        Jinja2 · HTML/CSS · Tailwind · Alpine.js   │
├───────────────────────────────────────────────────────────────┤
│ Rutas/Controladores  FastAPI routers (formularios y vistas)    │
├───────────────────────────────────────────────────────────────┤
│ Aplicación/Negocio   Servicios de dominio (reglas de SPECS)    │
├───────────────────────────────────────────────────────────────┤
│ Acceso a datos       Repositorios + ORM (SQLAlchemy)           │
├───────────────────────────────────────────────────────────────┤
│ Persistencia         Base de datos relacional                  │
└───────────────────────────────────────────────────────────────┘
        Transversal: Seguridad · Configuración · Formato CLP
```

- **Presentación:** renderiza las plantillas y la interacción cliente (Alpine.js). No contiene reglas de negocio.
- **Rutas/Controladores:** reciben la petición, validan con Pydantic, invocan servicios y devuelven plantillas o redirecciones. Sin lógica financiera.
- **Aplicación/Negocio:** concentra las reglas de `SPECS.md` (activación, imputación de pagos, abono, morosidad, negociación, reportes). Es la capa más testeada.
- **Acceso a datos:** repositorios sobre el ORM; aíslan las consultas y permiten transacciones atómicas.
- **Persistencia:** base de datos **MySQL/MariaDB** mediante ORM (P-1).

**Módulos de dominio:** Seguridad/Usuarios · Miembros y Membresías · Pagos · Morosidad · Negociación · Finanzas (ingresos, egresos, activos, gastos fijos) · Compras y Cobro a Alumnos · Reportes · Comunicación (avisos/plantillas) · Marca/Landing.

**Principios:** lógica de negocio fuera de las rutas y de las plantillas; toda operación financiera es **atómica**; los montos se manejan como enteros (CLP, sin decimales).

---

## 2. Tecnologías

| Componente | Tecnología | Propósito | Justificación | Estado |
| :--- | :--- | :--- | :--- | :--- |
| Lenguaje | **Python 3.11+** | Desarrollo del backend y la lógica. | Ecosistema maduro, tipado, alineado con FastAPI. | Confirmada |
| Backend | **FastAPI** | Router HTTP, validación, servidor de vistas. | Exigido por `AGENT.md`; asíncrono y con validación integrada. | Confirmada |
| Plantillas | **Jinja2** | Renderizado HTML del lado servidor. | Exigido por `AGENT.md`. | Confirmada |
| Estilos | **Tailwind CSS** | Diseño utilitario, responsivo y paleta Rojo/Negro/Blanco usando los valores por defecto de Tailwind (ver §14, Q-1). | Exigido por `AGENT.md`. | Confirmada |
| Interactividad | **Alpine.js** | Menú móvil, modales, acordeones, formularios dinámicos. | Exigido por `AGENT.md`. | Confirmada |
| Validación | **Pydantic** | Validación de formularios y datos de entrada. | Integrado en FastAPI; evita dependencia extra. | Confirmada (por FastAPI) |
| ORM | **SQLAlchemy** | Mapeo objeto-relacional y transacciones. | ORM estándar con FastAPI; permite transacciones atómicas para pagos. | Propuesta |
| Base de datos | **MySQL/MariaDB** (XAMPP) | Persistencia de desarrollo y producción. | Ya disponible en el entorno XAMPP; no requiere instalar servicios nuevos. | Confirmada (P-1) |
| Servidor ASGI | **Uvicorn** | Ejecución de la aplicación. | Servidor estándar para FastAPI. | Propuesta |
| Sesiones | **Starlette SessionMiddleware** | Autenticación por sesión firmada. | Encaja con el renderizado en servidor (no requiere API token). | Propuesta |
| Hash de contraseñas | **passlib + bcrypt** (o argon2) | Protección de credenciales. | Estándar de la industria. | Propuesta |
| Configuración | **python-dotenv / pydantic-settings** | Variables de entorno y secretos. | Evita credenciales en el código. | Propuesta |
| Exportación | **openpyxl** (XLSX) y **WeasyPrint/ReportLab** (PDF) | Reportes consolidados en XLSX y el informe calendario en PDF. | Formato y librerías definidos en P-3. | Confirmada (P-3) |
| Pruebas | **pytest** | Pruebas unitarias e integración. | Estándar de Python. | Propuesta |
| Calidad de código | **ruff** | Linter/formateador. | Rápido y simple; opcional. | Propuesta |
| Migraciones | **Alembic** (opcional) | Evolución del esquema. | Útil si el esquema crece; en el MVP puede usarse creación directa. | Propuesta |

**Restricciones respetadas:** todo el contenido textual en **UTF-8** y español correcto (RAE, tildes y "ñ"); montos en **CLP** enteros; paleta **Rojo/Negro/Blanco**; no se agregan tecnologías ajenas a las exigidas salvo las estrictamente necesarias para persistir, validar y exportar (justificadas arriba).

---

## 3. Estructura del proyecto

```
OR/                                  Raíz del repositorio
├── app/
│   ├── main.py                      Crea la app FastAPI, monta static, sesiones y routers
│   ├── config.py                    Configuración y variables de entorno
│   ├── database.py                  Motor, sesión y base declarativa del ORM
│   ├── dependencies.py              Dependencias compartidas (usuario actual, rol, sesión de BD)
│   ├── core/
│   │   ├── seguridad.py             Hash, sesiones, control de roles (RBAC)
│   │   ├── formato.py               Formato y parseo de montos CLP
│   │   └── errores.py               Manejo centralizado de errores y mensajes
│   ├── models/                      Modelos ORM (entidades)
│   │   ├── usuario.py
│   │   ├── miembro.py
│   │   ├── membresia.py
│   │   ├── pago.py
│   │   ├── finanzas.py
│   │   ├── compras.py
│   │   └── configuracion.py
│   ├── schemas/                     Esquemas Pydantic (validación de formularios)
│   ├── repositories/                Consultas y persistencia por entidad
│   ├── services/                    Reglas de negocio (ver sección 6)
│   │   ├── activacion.py
│   │   ├── membresias.py
│   │   ├── pagos.py
│   │   ├── morosidad.py
│   │   ├── negociacion.py
│   │   ├── finanzas.py
│   │   ├── compras.py
│   │   ├── reportes.py
│   │   └── correo.py
│   ├── routers/                     Endpoints y controladores por dominio
│   │   ├── landing.py
│   │   ├── auth.py
│   │   ├── miembros.py
│   │   ├── membresias.py
│   │   ├── pagos.py
│   │   ├── morosidad.py
│   │   ├── negociaciones.py
│   │   ├── finanzas.py
│   │   ├── compras.py
│   │   ├── reportes.py
│   │   └── cuenta.py
│   ├── templates/                   Plantillas Jinja2
│   │   ├── base.html
│   │   ├── landing/index.html
│   │   ├── auth/login.html
│   │   ├── miembros/
│   │   ├── pagos/
│   │   ├── morosidad/
│   │   ├── negociaciones/
│   │   ├── finanzas/
│   │   ├── compras/
│   │   ├── reportes/
│   │   ├── cuenta/
│   │   └── parciales/               Header, footer, alertas, tabla de cuotas, etc.
│   └── static/
│       ├── css/                     (Tailwind compilado)
│       ├── js/                      (Alpine.js y utilidades)
│       └── img/                     (logo e imágenes)
├── tests/                           Pruebas unitarias e integración
├── requirements.txt                 Dependencias
├── .env.example                     Plantilla de variables de entorno
├── tailwind.config.js               Paleta Rojo/Negro/Blanco y contenido
├── package.json                     Compilación de Tailwind (solo build de CSS)
├── README.md                        Instrucciones de instalación y ejecución
└── specs/                           AGENT.md · SPECS.md · PLAN.md
```

**Responsabilidades clave:** `main.py` compone la aplicación; `services/` contiene toda la lógica de `SPECS.md`; `repositories/` aísla la base de datos; `templates/` y `static/` no contienen reglas de negocio.

> **Nota:** `AGENT.md` pedía evitar estructuras de carpetas en la fase de requisitos; este `PLAN.md` **sí** las detalla porque este documento es el plan técnico solicitado.

---

## 4. Modelo de datos

Persistencia relacional. Los montos son **enteros en CLP**. Se indican entidades, propiedades relevantes, identificadores, relaciones y estados.

**Seguridad y acceso**

| Entidad | Propiedades clave | Relaciones | Estados |
| :--- | :--- | :--- | :--- |
| **Usuario** | `id` (PK), `email` (única), `password_hash`, `rol`, `activo`, `creado_en` | 1–1 opcional con Miembro | activo/inactivo; rol: admin/tesorero/miembro |

**Miembros y membresías**

| Entidad | Propiedades clave | Relaciones | Estados |
| :--- | :--- | :--- | :--- |
| **Miembro** | `id` (PK), `nombre_completo`, `email` (única), `telefono`, `rut`, `fecha_nacimiento`, `direccion`, `contacto_emergencia`, `fecha_incorporacion` (fecha de ingreso), `matriculado`, `categoria`, `situacion_activacion`, `condicion_especial`, `motivo_exencion`, `usuario_id` (FK, opcional) | N–1 Usuario; 1–N CuotaMensual, Pago, HistorialCategoria | categoria: activo/membresia; activación: pendiente/activo; especial: normal/exento (becado, invitado, retirado); matriculado: sí/no |
| **HistorialCategoria** | `id` (PK), `miembro_id` (FK), `categoria_anterior`, `categoria_nueva`, `fecha`, `usuario_id` (FK) | N–1 Miembro | — |
| **NivelCuota** | `id` (PK), `codigo` (matricula/estandar/activa), `nombre`, `monto_clp`, `tipo` (unico/mensual), `activo` | 1–N CuotaMensual | activo/inactivo |
| **CuotaMensual** | `id` (PK), `miembro_id` (FK), `anio`, `mes`, `nivel_cuota_id` (FK), `monto_clp`, `monto_pagado_clp`, `estado` | N–1 Miembro, NivelCuota; 1–N ImputacionPago | pendiente/pagada/parcial/exenta |

**Pagos, imputación y abonos**

| Entidad | Propiedades clave | Relaciones | Estados |
| :--- | :--- | :--- | :--- |
| **Pago** | `id` (PK), `miembro_id` (FK), `monto_clp`, `fecha_pago`, `medio` (transferencia/efectivo), `observaciones`, `registrado_por` (FK), `creado_en` | N–1 Miembro, Usuario; 1–N ImputacionPago | registrado |
| **ImputacionPago** | `id` (PK), `pago_id` (FK), `cuota_id` (FK, opcional), `monto_clp`, `orden` | N–1 Pago, CuotaMensual | aplicada |
| **Abono** | `id` (PK), `miembro_id` (FK), `monto_clp`, `saldo_disponible_clp`, `origen_pago_id` (FK), `creado_en` | N–1 Miembro, Pago | disponible/aplicado |

**Morosidad y negociación**

| Entidad | Propiedades clave | Relaciones | Estados |
| :--- | :--- | :--- | :--- |
| **Morosidad** (derivada) | `miembro_id`, `meses_deuda`, `monto_deuda_clp`, `color` | Se calcula desde CuotaMensual de **meses ya cerrados** (P-5) | al día / naranjo / rojo |
| **NegociacionDeuda** | `id` (PK), `miembro_id` (FK), `deuda_total_clp`, `descuento_pct`, `monto_negociado_clp`, `fecha`, `usuario_id` (FK), `estado` | N–1 Miembro, Usuario | propuesta/aceptada/pagada (en "aceptada" la deuda deja de contar para el color; P-6) |

**Finanzas**

| Entidad | Propiedades clave | Relaciones | Estados |
| :--- | :--- | :--- | :--- |
| **CategoriaEgreso** | `id` (PK), `nombre`, `es_base`, `activo` | 1–N Egreso | activo/inactivo (base fija + personalizadas; P-7) |
| **Egreso** | `id` (PK), `monto_clp`, `fecha`, `concepto`, `categoria_egreso_id` (FK), `tipo` (general/activo/gasto_fijo/compra), `miembro_responsable_id` (FK, opcional), `registrado_por` (FK) | N–1 CategoriaEgreso, Miembro, Usuario | registrado |
| **GastoFijo** | `id` (PK), `concepto`, `monto_clp`, `periodicidad` (mensual), `activo` | 1–N Egreso | activo/inactivo |

**Compras y cobro a alumnos**

| Entidad | Propiedades clave | Relaciones | Estados |
| :--- | :--- | :--- | :--- |
| **CompraClub** | `id` (PK), `descripcion`, `proveedor`, `fecha`, `monto_total_clp`, `estado` | 1–N CompraItem, CargoAlumno | registrada |
| **CompraItem** | `id` (PK), `compra_id` (FK), `descripcion`, `precio_unitario_clp`, `cantidad` | N–1 CompraClub; 1–N CargoAlumno | — |
| **CargoAlumno** | `id` (PK), `miembro_id` (FK), `compra_item_id` (FK), `monto_clp`, `fecha`, `estado`, `pago_id` (FK, opcional) | N–1 Miembro, CompraItem, Pago | pendiente/pagado |

**Configuración y comunicación**

| Entidad | Propiedades clave | Relaciones | Estados |
| :--- | :--- | :--- | :--- |
| **CuentaBancaria** | `id` (PK), `titular`, `banco`, `numero_cuenta`, `rut`, `correo` | — | activa |
| **PlantillaCorreo** | `id` (PK), `nombre`, `asunto`, `cuerpo` | 1–N AvisoMorosidad | activa |
| **AvisoMorosidad** | `id` (PK), `miembro_id` (FK), `generado_en`, `detalle`, `estado`, `enviado_por` (FK, opcional), `enviado_en` | N–1 Miembro, PlantillaCorreo, Usuario | pendiente/enviado |

**Identificadores:** claves primarias enteras autoincrementales; `email` es el identificador único del miembro y del usuario (RN-11). **Relaciones:** un miembro tiene muchas cuotas, pagos y cargos; cada pago se descompone en imputaciones; un abono pertenece a un miembro y se origina en un pago; cada egreso pertenece a una categoría; una compra origina varios cargos a alumnos.

---

## 5. Componentes y módulos

| Módulo | Responsabilidad | Datos que gestiona | Funcionalidades (`SPECS`) |
| :--- | :--- | :--- | :--- |
| **Seguridad/Usuarios** | Autenticación, sesiones y permisos por rol. | Usuario | F-02, F-03 |
| **Miembros** | Alta y mantenimiento de la ficha ampliada; cambio de categoría. | Miembro, HistorialCategoria | F-01, F-04, F-05 |
| **Membresías** | Catálogo de cuotas, activación, generación de cuotas mensuales, exenciones. | NivelCuota, CuotaMensual | F-06, F-07, F-09, F-10 |
| **Pagos** | Registro de pagos (monto libre, año, meses, observaciones), imputación y abonos. | Pago, ImputacionPago, Abono, CuotaMensual | F-08, F-11, F-12, F-13, F-14 |
| **Morosidad** | Cálculo de deuda, meses y color; listados de morosos. | CuotaMensual (derivado) | F-11, F-22 |
| **Negociación** | Negociar deuda de morosos >6 meses con % editable. | NegociacionDeuda | F-24 |
| **Finanzas** | Ingresos, egresos, activos y gastos fijos; filtros. | Egreso, CategoriaEgreso, GastoFijo | F-15, F-16, F-17, F-18 |
| **Compras** | Registro de compras del club y cobro a alumnos (cargo separado). | CompraClub, CompraItem, CargoAlumno | F-25 |
| **Reportes** | Reportes consolidados, informe calendario y exportación. | Derivado de pagos/egresos/cuotas | F-19, F-20, F-21 |
| **Comunicación** | Avisos de morosidad y plantilla de correo. | AvisoMorosidad, PlantillaCorreo | F-23 |
| **Configuración** | Cuenta bancaria, categorías base y parámetros. | CuentaBancaria, CategoriaEgreso | F-26 |
| **Marca/Landing** | Landing page, paleta y formato CLP. | — | F-27, F-28, F-29 |

**Relaciones entre módulos:** Membresías produce `CuotaMensual`, que consume Pagos (imputación) y Morosidad (deuda). Morosidad alimenta Negociación y Comunicación. Finanzas y Compras alimentan Reportes. Seguridad es transversal y condiciona el acceso a todos los módulos (salvo la landing pública).

---

## 6. Funciones y lógica

Nombres sugeridos, responsabilidad, parámetros, resultado y dependencias. (Sin código: descripción de firmas.)

**`core/formato.py`**
- `formatear_clp(monto: int) -> str` → devuelve `"45.000"` (separador de miles por punto, sin decimales). Dependencia base de toda la interfaz.
- `parsear_clp(texto: str) -> int` → convierte la entrada del formulario a entero.

**`core/seguridad.py`**
- `hash_password(plano: str) -> str` / `verify_password(plano, hash) -> bool`.
- `iniciar_sesion(request, usuario) -> None` / `cerrar_sesion(request) -> None`.
- `usuario_actual(request) -> Usuario | None`.
- `requiere_rol(*roles) -> Callable` → dependencia de FastAPI que restringe por rol (admin/tesorero tienen los mismos permisos, D-7).

**`services/activacion.py`**
- `evaluar_activacion(miembro, pagos_validos) -> EstadoActivacion` → decide si el pago inicial (Matrícula + cuota de la categoría) está completo (RN-02). La Matrícula se omite si el miembro está marcado como matriculado o ingresó antes del 01/09/2025 (RN-27).
- `aplicar_activacion(miembro) -> None` → marca al miembro como activo.

**`services/membresias.py`**
- `monto_cuota(nivel: NivelCuota) -> int`.
- `generar_cuotas_del_periodo(anio, mes) -> list[CuotaMensual]` → crea cuotas para miembros activos y no exentos.
- `cambiar_categoria(miembro, nueva_categoria, usuario) -> HistorialCategoria` (RN-25).
- `marcar_exencion(miembro, motivo) -> None` / `quitar_exencion(miembro) -> None` (RN-05).
- `aplicar_corte_dia_5(pago, cuota) -> CuotaMensual` → imputa al ciclo siguiente si el pago es posterior al día 5 (RN-03).

**`services/pagos.py`**
- `registrar_pago(miembro, monto_clp, fecha, medio, anio, meses, observaciones, usuario) -> Pago` — valida y persiste el pago; delega la imputación. Todo dentro de una **transacción atómica**.
- `imputar_pago(pago, cuotas_objetivo) -> list[ImputacionPago]` → orden **deuda más antigua → meses/año indicados → abono** (RN-17).
- `generar_abono(miembro, monto, origen_pago_id) -> Abono`.
- `aplicar_abono(miembro) -> list[ImputacionPago]` → consume el abono en la siguiente cuota (RN-18).
- `obtener_deuda(miembro) -> list[CuotaMensual]` y `saldo_a_favor(miembro) -> int`.

**`services/morosidad.py`**
- `calcular_morosidad(miembro, fecha_referencia) -> MorosidadInfo` → meses de deuda y monto, considerando **solo meses cerrados** (RN-04, P-5).
- `clasificar_color(meses_deuda: int) -> str` → `"verde" | "naranjo" | "rojo"` (RN-21).
- `listar_morosos(filtros) -> list[MorosidadInfo]`.
- `sugerir_aviso(miembro) -> AvisoMorosidad` → crea la alerta para el Tesorero (RN-13).

**`services/negociacion.py`**
- `puede_negociar(miembro) -> bool` → deuda > 6 meses (RN-22).
- `calcular_monto_negociado(deuda_total, descuento_pct) -> int` → valida 0–100.
- `crear_negociacion(miembro, descuento_pct, usuario) -> NegociacionDeuda`.
- `aplicar_efecto_negociacion(negociacion) -> None` → al pasar a **"aceptada"**, excluye esa deuda del cálculo de color (P-6).
- `registrar_pago_negociacion(negociacion, pago) -> None`.

**`services/finanzas.py`**
- `registrar_egreso(monto, fecha, concepto, categoria_id, usuario) -> Egreso`.
- `registrar_activo(costo, descripcion, miembro_responsable_id, usuario) -> Egreso` (tipo = activo).
- `registrar_gasto_fijo(concepto, monto, usuario) -> GastoFijo`.
- `listar_ingresos(filtros) -> list[Pago]` / `listar_egresos(filtros) -> list[Egreso]`.
- `crear_categoria_egreso(nombre, usuario) -> CategoriaEgreso`.

**`services/compras.py`**
- `registrar_compra(descripcion, proveedor, fecha, items, usuario) -> CompraClub`.
- `generar_cargos_alumnos(compra, asignaciones) -> list[CargoAlumno]` → cargo **separado** (RN-23).
- `saldar_cargo(cargo, pago) -> None`.

**`services/reportes.py`**
- `reporte_consolidado(desde, hasta) -> ReporteConsolidado` → ingresos, egresos y neto.
- `informe_calendario(miembro, anio) -> InformeCalendario` → cuotas por mes con estado y monto.
- `exportar_reporte(reporte, formato) -> bytes` → **XLSX** para reportes consolidados y **PDF** para el informe calendario (P-3).

**`services/correo.py`**
- `renderizar_plantilla(plantilla, aviso, cuenta) -> str` → datos del alumno, detalle de morosidad, adeudado y datos de cuenta.
- `generar_enlace_correo(destinatario, asunto, cuerpo) -> str` → enlace **mailto:** que abre el cliente de correo del Tesorero (P-2).
- `marcar_aviso_enviado(aviso, usuario) -> None`.

---

## 7. Flujos técnicos

Colaboración de módulos para los flujos de `SPECS.md` (sección 5).

- **Flujo 1 — Incorporación y activación:** `routers/miembros` (POST) → valida con `schemas` → `services/membresias.crear_miembro` registra la fecha de ingreso (editable, por defecto hoy) y el estado de matrícula → `services/activacion.evaluar_activacion` al registrarse el pago inicial → `repositories` persiste → redirección al perfil.
- **Flujo 3 — Pago personalizado:** `routers/pagos` → `services/pagos.registrar_pago` (transacción) → `imputar_pago` aplica RN-17 → `generar_abono`/`aplicar_abono` (RN-18) → `repositories` guarda Pago, Imputaciones y Abono → `templates/pagos` muestra el resultado.
- **Flujo 4 — Mora y aviso manual:** `services/morosidad.calcular_morosidad` (job o cálculo al abrir la vista) → `clasificar_color` → `listar_morosos` alimenta `templates/morosidad` → `correo.renderizar_plantilla` produce el texto → el Tesorero **envía manualmente** → `marcar_aviso_enviado`.
- **Flujo 5 — Negociación:** `routers/negociaciones` → `negociacion.puede_negociar`/`calcular_monto_negociado` → `crear_negociacion` → al pagar, `registrar_pago_negociacion` descarga la deuda.
- **Flujo 7 — Cambio de categoría:** `routers/miembros` → `membresias.cambiar_categoria` → registra `HistorialCategoria` y ajusta la cuota vigente.
- **Flujo 8/9 — Egresos y compras:** `routers/finanzas` y `routers/compras` → `services/finanzas` / `services/compras` → `Egreso`/`CompraClub` + `CargoAlumno` → visibles en Reportes.
- **Flujo 10 — Reportes:** `routers/reportes` → `services/reportes.reporte_consolidado` → `exportar_reporte` → descarga.
- **Flujo 11 — Consulta del miembro:** `routers/miembros` (vista propia) → `morosidad.calcular_morosidad` + `reportes.informe_calendario` → `templates/miembros` (solo lectura).

**Regla transversal:** toda operación que registre dinero (pago, egreso, abono, cargo) se ejecuta en una única **transacción de base de datos** (todo o nada).

---

## 8. Implementación de la interfaz

- **Layout base (`base.html`):** header con logo y navegación según rol, zona de alertas, footer con el nombre oficial "Sistema Gestión Pagos Osorno Runners", y carga de Tailwind y Alpine.js.
- **Landing (`templates/landing/index.html`):** las 8 secciones de UI-01 (Header/Nav, Hero, Quiénes somos, Membresías, Cómo funciona, Datos de transferencia, Contacto, Footer). Menú móvil, acordeón de "Cómo funciona" y modales con **Alpine.js**; diseño responsive con **Tailwind**. La landing **solo ofrece inicio de sesión** (sin autorregistro); el alta de miembros la realizan Admin/Tesorero (P-4).
- **Paleta:** `tailwind.config.js` define la escala de la paleta institucional con los valores por defecto de Tailwind — **Rojo** `red-600` (#DC2626), **Negro** `black` (#000000), **Blanco** `white` (#FFFFFF) — y los colores de morosidad: **verde** `green-600` (#16A34A), **naranjo** `amber-500` (#F59E0B) y **rojo** `red-500` (#EF4444) (UI-10, §14 Q-1).
- **Panel Admin/Tesorero:** vistas separadas para miembros, membresías, pagos, morosidad, negociaciones, finanzas, compras y reportes (UI-03, UI-04).
- **Formulario de pago personalizado (UI-07):** monto libre, selección de año y meses, previsualización del abono y cuadro de observaciones; validación con Pydantic y ayudas dinámicas con Alpine.js.
- **Panel de morosidad (UI-08):** tabla con **colores** verde/naranjo/rojo, selección de morosos, botón para ver la **plantilla de correo** y acceso a negociación.
- **Estado de cuenta e informe calendario (UI-06):** calendario anual con estado y monto en CLP; solo lectura para el miembro.
- **Formato de montos:** todo monto pasa por `formatear_clp` antes de renderizarse (RN-24).
- **Feedback (UI-12):** mensajes de confirmación y de error en español correcto, reutilizando un parcial de alertas.

---

## 9. Persistencia y estado

- **Almacenamiento:** base de datos **MySQL/MariaDB** (XAMPP) mediante ORM (P-1).
- **Recuperación/actualización:** repositorios encapsulan las consultas; los servicios no acceden al ORM directamente.
- **Consistencia:** operaciones de dinero en **transacciones atómicas**; integridad referencial con claves foráneas; los montos se guardan como enteros CLP.
- **Estado del usuario en el servidor:** **sesión firmada** con el identificador y rol del usuario (Propuesta). El estado de morosidad y el abono son **derivados** de los datos persistidos, no almacenados por duplicado (se recalculan).
- **Esquema:** creación directa del esquema en el MVP; **Alembic** opcional si el modelo crece (Propuesta).
- **Concurrencia:** las vistas de solo lectura no bloquean; los registros de pago/egreso usan transacción para evitar imputaciones dobles.

---

## 10. Validaciones y errores

- **Validación de entrada:** esquemas Pydantic por formulario (campos obligatorios, formatos, montos enteros positivos, correo válido) → CA-21.
- **Validación de negocio:** en `services` (activación completa, exención, unicidad de pago por ciclo RN-08, rango de descuento 0–100, negociación solo >6 meses, categoría válida RN-10).
- **Manejo centralizado de errores (`core/errores.py`):** respuestas claras y en español; estados HTTP coherentes (400 datos inválidos, 403 permisos, 404 no encontrado, 409 duplicado).
- **Casos límite de `SPECS.md` (sección 9):** reportes sin datos ("sin movimientos"), exportación vacía, montos personalizados que generan abono o deuda, selección de meses inválida, operación no permitida por estado.
- **Reutilización:** un parcial de alertas muestra los mensajes de error/confirmación sin duplicar texto.

---

## 11. Seguridad

- **Contraseñas:** hash con bcrypt/argon2; nunca en texto plano.
- **Sesiones:** cookie firmada, `HttpOnly`, `SameSite=Lax`; expiración configurable.
- **Autorización (RBAC):** dependencia `requiere_rol`; Admin y Tesorero comparten permisos (D-7); el Miembro solo accede a su información (RN-06) — se valida el **aislamiento por propietario** en cada vista del miembro.
- **CSRF:** token en formularios de escritura (Propuesta), dado que se usa autenticación por cookie.
- **Inyección SQL:** evitada por el uso del ORM con parámetros.
- **Secretos y configuración:** clave de sesión y credenciales en variables de entorno (`.env`), no en el repositorio.
- **Transporte:** HTTPS en producción (pendiente **post-MVP**; ver §14 Q-3).
- **Datos sensibles:** los datos bancarios y personales solo son visibles para Admin/Tesorero y para el propio miembro.

---

## 12. Orden de implementación

1. **Fase 1 — Fundación:** esqueleto FastAPI + Jinja2 + Tailwind + Alpine; layout base; configuración y conexión a **MySQL/MariaDB**; ORM y entidades; sesiones y login.
2. **Fase 2 — Miembros y membresías:** alta de miembros, categorías, catálogo de cuotas, activación y generación de cuotas; estados y exenciones.
3. **Fase 3 — Pagos:** registro de pago personalizado, imputación, abono y estado de cuenta (el núcleo de negocio; máximo cuidado y pruebas).
4. **Fase 4 — Mora y avisos:** morosidad, colores, panel del Tesorero y plantilla de correo (envío manual); negociación de deuda.
5. **Fase 5 — Finanzas y compras:** ingresos, egresos, categorías, activos, gastos fijos; compras y cobro a alumnos.
6. **Fase 6 — Reportes y landing:** reportes consolidados, informe calendario, exportación; landing page y pulido de marca.
7. **Fase 7 — Calidad:** validaciones, manejo de errores, pruebas y revisión final.

**Dependencias:** la Fase 3 depende de la 2; las Fases 4 y 6 dependen de la 3; la 5 es relativamente independiente; la 6 depende de 3 y 5.

---

## 13. Pruebas y calidad

- **Unitarias (`pytest`):** servicios críticos — activación, imputación (deuda antigua → mes/año → abono), abono automático, clasificación de morosidad por color, cálculo de negociación, corte del día 5.
- **Integración:** flujo de pago completo, alta y activación, mora y aviso, compra con cargo a alumno, reporte consolidado.
- **Pruebas de aceptación (UAT):** con Admin, Tesorero y un Miembro, verificando los criterios `CA-01…CA-31` de `SPECS.md`.
- **Calidad de código:** `ruff` (lint/format) y revisión por pares antes de fusionar.
- **Datos de prueba:** semilla con miembros en distintos estados (al día, naranjo, rojo, exento) para validar colores y reportes.

---

## 14. Riesgos y decisiones pendientes

### Decisiones confirmadas (vienen de las especificaciones)
- Stack FastAPI + Jinja2 + HTML/CSS + Tailwind CSS + Alpine.js.
- Moneda CLP entera, con separador de puntos.
- Roles Admin/Tesorero (permisos iguales) y Miembro (restringido).
- Reglas de activación, corte del día 5, mora, colores, negociación >6 meses, compras con cargo separado, correos manuales y cuenta bancaria.

### Decisiones propuestas (este plan)
- SQLAlchemy como ORM sobre **MySQL/MariaDB** (XAMPP).
- Autenticación por sesión firmada; bcrypt/argon2; CSRF en formularios.
- Capa `services/` como único lugar de reglas de negocio; transacciones atómicas para el dinero.
- `ruff` y `pytest` para calidad.

### Decisiones resueltas (ronda P-1…P-8)

| Código | Pregunta | Decisión |
| :--- | :--- | :--- |
| **P-1** | Motor de base de datos | **MySQL/MariaDB** (XAMPP), para desarrollo y producción. |
| **P-2** | Envío del correo de morosidad | **mailto:** — el sistema genera el texto y abre el cliente de correo del Tesorero (sin credenciales SMTP). |
| **P-3** | Exportación | **XLSX** para reportes consolidados y **PDF** para el informe calendario. |
| **P-4** | Alta de miembros | **Solo Admin/Tesorero** dan de alta; la landing solo ofrece inicio de sesión (sin autorregistro). |
| **P-5** | Referencia de la mora | La deuda cuenta con **meses ya cerrados**; el mes en curso no cuenta (se requiere al menos un mes completo de atraso). |
| **P-6** | Negociación y color | La deuda negociada deja de contar para el color **solo cuando la negociación está "aceptada"** (en "propuesta" sigue contando). |
| **P-7** | Categorías de egreso | **Base fija confirmada** (Activos, Gastos fijos, Transferencias, Tarjeta y Otros) **+ personalizadas**; las base no se eliminan y cualquiera puede desactivarse. |
| **P-8** | Despliegue | **Uvicorn local** con MySQL de XAMPP para el MVP; la publicación productiva se define más adelante. |

### Decisiones resueltas (ronda Q-1…Q-4)

| Código | Pregunta | Decisión |
| :--- | :--- | :--- |
| **Q-1** | Paleta y colores de morosidad | **Valores por defecto de Tailwind**: Rojo `red-600` (#DC2626), Negro `black` (#000000), Blanco `white` (#FFFFFF); morosidad verde `green-600` (#16A34A), naranjo `amber-500` (#F59E0B), rojo `red-500` (#EF4444). |
| **Q-2** | Sesión y CSRF | **Confirmada** la propuesta: sesión firmada en cookie `HttpOnly` con `SameSite=Lax` + token CSRF en formularios de escritura. |
| **Q-3** | Publicación y respaldos | **Uso actual personal/local** (Uvicorn + MySQL de XAMPP en `127.0.0.1:8000`), sin acceso público. La publicación productiva y los respaldos quedan como trabajo **post-MVP** documentado en `docs/POST_MVP.md` (no ejecutado). |
| **Q-4** | Nombre de la base de datos | **`osorno_runners`**. |

### Uso actual

- El sistema se usa **solo en el PC del usuario**, para el registro personal de
  pagos del club.
- Se ejecuta con **Uvicorn + FastAPI** en `http://127.0.0.1:8000` y
  **MySQL/MariaDB de XAMPP**.
- **No hay acceso público ni despliegue productivo.** GitHub solo almacena el
  código y la documentación.
- La publicación futura (Cloudflare Tunnel, VPS o Docker) está documentada en
  `docs/POST_MVP.md` y no se ha ejecutado.

### Pendientes (post-MVP, no bloqueantes)

- **Publicación productiva y respaldos:** plan cerrado documentalmente en
  `docs/POST_MVP.md`; la ejecución queda pendiente de servidor y dominio
  (Q-3). No se ha desplegado nada en producción.

### Riesgos
- **Integridad de la imputación:** la lógica de pago multimes/multiaño y abonos es la más compleja; un error afecta saldos. *Mitigación:* pruebas unitarias exhaustivas y transacciones atómicas.
- **Ambigüedad de la morosidad:** sin la decisión P-5, los colores pueden diferir de lo esperado. *Mitigación:* resolver antes de la Fase 4.
- **Envío de correo manual:** depende del cliente de correo del Tesorero; la trazabilidad de "enviado" es declarativa. *Mitigación:* ver P-2.
- **Crecimiento del esquema:** añadir reportes/consultas puede requerir índices; el ORM ayuda pero conviene planificar índices por miembro y periodo.
- **Doble captura de datos:** si la landing ofreciera autorregistro (P-4), habría que validar duplicados contra el alta administrativa.

---

**Nota final:** este plan respeta `specs/AGENT.md` y `specs/SPECS.md`. Las decisiones **P-1…P-8** y **Q-1…Q-4** quedaron resueltas en la sección 14; el único pendiente es la **ejecución** del plan post-MVP (publicación productiva y respaldos), documentada en `docs/POST_MVP.md`.
