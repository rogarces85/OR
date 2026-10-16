# Tareas de Implementación del MVP — Sistema Gestión Pagos Osorno Runners

> **Fuentes:** `specs/AGENT.md`, `specs/SPECS.md`, `specs/PLAN.md`.
> **Uso:** hoja de ruta de implementación. Cada tarea es pequeña y verificable mediante un **resultado observable**. Las tareas grandes se dividen en subtareas. Se indican **dependencias** cuando ayudan a evitar ambigüedades.
> **Estado:** todas las tareas comienzan **pendientes** (`[ ]`). El proyecto está vacío (solo `.git` y `specs/`).
> **Trazabilidad:** cada tarea referencia los requisitos de `SPECS.md` (`F-`, `RN-`, `CA-`) y las secciones de `PLAN.md`.
> **Regla:** no se agregan funcionalidades fuera de las especificaciones. Las decisiones no cerradas se registran como dependencia/pendiente (ver "Decisiones resueltas y pendientes" al final).

---

## Fase 1 — Preparación y configuración

- [x] **T1.1 · Verificar el entorno de Python**
  - Qué: confirmar que hay un intérprete Python 3.11 o superior y acceso a `pip`.
  - Verificación: `python --version` (o `py --version`) muestra 3.11+.
- [x] **T1.2 · Confirmar el stack congelado**
  - Qué: dejar registrado en el `README` el stack definitivo (FastAPI + Jinja2 + HTML/CSS + Tailwind + Alpine.js + MySQL/MariaDB).
  - Verificación: el `README` lista el stack y coincide con `AGENT.md`.
- [x] **T1.3 · Preparar rama de trabajo en Git**
  - Qué: crear una rama de desarrollo (por ejemplo `feat/mvp`) y confirmar el commit base con `specs/`.
  - Verificación: `git status` limpio y `git branch` muestra la rama activa.
- [x] **T1.4 · Crear el entorno virtual e instalarlo**
  - Qué: crear `venv` en la raíz y activarlo.
  - Verificación: el prompt muestra el entorno activado y `pip list` responde.
- [x] **T1.5 · Definir `requirements.txt`**
  - Qué: declarar dependencias: `fastapi`, `uvicorn[standard]`, `jinja2`, `sqlalchemy`, `pymysql`, `cryptography` (auth MySQL), `itsdangerous` (sesiones), `passlib[bcrypt]` (o `argon2-cffi`), `python-multipart` (formularios), `python-dotenv`/`pydantic-settings`, `openpyxl` (XLSX), `weasyprint`/`reportlab` (PDF), `pytest`, `ruff`.
  - Verificación: `pip install -r requirements.txt` termina sin errores.
  - Relación: `PLAN.md` §2.
- [x] **T1.6 · Crear el archivo `.env.example` y `app/config.py`**
  - Qué: plantilla de variables (cadena de conexión MySQL, `SECRET_KEY`, entorno) y su carga tipada.
  - Verificación: la app lee la configuración sin credenciales en el código.
  - Relación: `PLAN.md` §9, §11.
- [x] **T1.7 · Crear la base de datos MySQL/MariaDB**
  - Qué: crear la base **`osorno_runners`** y el usuario en XAMPP; probar conexión.
  - Verificación: una conexión de prueba (`pymysql`) responde correctamente.
  - Relación: P-1, Q-4, `PLAN.md` §9.
- [x] **T1.8 · Confirmar la paleta oficial y los colores de morosidad**
  - Qué: fijar los valores (hex) de **Rojo, Negro y Blanco** y de los estados de morosidad (**verde**, **naranjo**, **rojo**).
  - Verificación: `tailwind.config.js` incluye Rojo `red-600` (#DC2626), Negro `black` (#000000), Blanco `white` (#FFFFFF); morosidad verde `green-600` (#16A34A), naranjo `amber-500` (#F59E0B), rojo `red-500` (#EF4444).
  - Relación: F-29, F-22, D-17, Q-1.
- [x] **T1.9 · Configurar la compilación de Tailwind CSS**
  - Qué: crear `package.json`, `tailwind.config.js` (paleta y rutas de plantillas) e `input.css`.
  - Verificación: `npx tailwindcss` genera un CSS de salida sin errores.
  - Relación: D-24, UI-10.
- [x] **T1.10 · Crear el `.gitignore`**
  - Qué: excluir `venv`, `.env`, `__pycache__`, `node_modules`, CSS compilado y archivos temporales.
  - Verificación: `git status` no muestra esos artefactos.

---

## Fase 2 — Estructura base

- [x] **T2.1 · Crear el árbol de carpetas del proyecto**
  - Qué: crear `app/` con `core`, `models`, `schemas`, `repositories`, `services`, `routers`, `templates`, `static` (y `tests/`), con `__init__.py` donde corresponda.
  - Verificación: el árbol coincide con `PLAN.md` §3.
- [x] **T2.2 · Crear la aplicación FastAPI (`app/main.py`)**
  - Qué: instanciar `FastAPI`, montar `/static`, configurar Jinja2 y registrar los routers.
  - Verificación: `uvicorn app.main:app --reload` levanta y responde en una ruta de prueba.
  - Depende de: T1.5, T2.1.
- [x] **T2.3 · Crear la capa de base de datos (`app/database.py`)**
  - Qué: engine MySQL, fábrica de sesiones, `Base` declarativa y dependencia `get_db`.
  - Verificación: una consulta trivial a la base funciona desde la app.
  - Depende de: T1.7.
- [x] **T2.4 · Definir el esquema inicial y su creación**
  - Qué: decidir y aplicar el mecanismo de creación de tablas (creación directa del esquema en el MVP; Alembic queda opcional).
  - Verificación: las tablas se crean en MySQL sin errores.
  - Relación: `PLAN.md` §9.
- [x] **T2.5 · Crear el layout base (`templates/base.html`)**
  - Qué: estructura común con header, zona de contenido, footer con el nombre oficial y carga de CSS/Alpine.js.
  - Verificación: una página de prueba hereda del layout y muestra header y footer.
  - Relación: `PLAN.md` §8.
- [x] **T2.6 · Integrar el CSS compilado de Tailwind**
  - Qué: enlazar el CSS generado en `base.html` y compilar tras cada cambio relevante.
  - Verificación: los estilos Tailwind se aplican en la página de prueba.
  - Depende de: T1.9, T2.5.
- [x] **T2.7 · Integrar Alpine.js**
  - Qué: cargar Alpine.js y crear un componente mínimo de prueba (por ejemplo, un toggle).
  - Verificación: el componente responde a la interacción en el navegador.
  - Relación: D-24.
- [x] **T2.8 · Ruta de salud y páginas de error base**
  - Qué: ruta `/salud` y plantillas base para 404 y 500.
  - Verificación: `/salud` responde y una URL inexistente muestra la página 404.

---

## Fase 3 — Modelos de datos y persistencia

- [ ] **T3.1 · Modelo `Usuario` (`models/usuario.py`)**
  - Qué: `id`, `email` (único), `password_hash`, `rol`, `activo`, `creado_en`.
  - Verificación: la tabla se crea y un registro de prueba se inserta/lee.
  - Relación: F-02, D-7.
- [ ] **T3.2 · Modelos `Miembro` e `HistorialCategoria` (`models/miembro.py`)**
  - Qué: ficha ampliada (nombre, email único, teléfono, RUT, fecha de nacimiento, dirección, contacto de emergencia), `fecha_incorporacion`, `categoria`, `situacion_activacion`, `condicion_especial`, `motivo_exencion`, `usuario_id`; e historial de cambios de categoría.
  - Verificación: las tablas se crean y respetan la unicidad de email.
  - Relación: F-01, F-05, RN-11, RN-14.
- [ ] **T3.3 · Modelos `NivelCuota` y `CuotaMensual` (`models/membresia.py`)**
  - Qué: catálogo de cuotas (código, monto, tipo) y cuota mensual por miembro/periodo con estado y montos; incluir aquí `NegociacionDeuda` (deuda, descuento %, monto negociado, estado).
  - Verificación: las tablas se crean y permiten asociar cuotas a un miembro.
  - Relación: F-06, F-10, F-24.
- [ ] **T3.4 · Modelos `Pago`, `ImputacionPago` y `Abono` (`models/pago.py`)**
  - Qué: pago (monto, fecha, medio, observaciones, registrado por), imputación (pago↔cuota, monto, orden) y abono (saldo disponible).
  - Verificación: las tablas se crean y las relaciones se mantienen.
  - Relación: F-08, F-12, F-13.
- [ ] **T3.5 · Modelos `CategoriaEgreso`, `Egreso` y `GastoFijo` (`models/finanzas.py`)**
  - Qué: categorías (base/personalizada, activo), egresos (monto, fecha, concepto, categoría, tipo, miembro responsable) y gastos fijos.
  - Verificación: las tablas se crean y un egreso se asocia a una categoría.
  - Relación: F-16, F-17, F-18, RN-10.
- [ ] **T3.6 · Modelos `CompraClub`, `CompraItem` y `CargoAlumno` (`models/compras.py`)**
  - Qué: compras del club, ítems y cargos a alumnos (cargo separado, estado, pago asociado).
  - Verificación: una compra con ítems genera cargos a distintos alumnos.
  - Relación: F-25, RN-23.
- [ ] **T3.7 · Modelos de configuración y comunicación (`models/configuracion.py`)**
  - Qué: `CuentaBancaria`, `PlantillaCorreo` y `AvisoMorosidad`.
  - Verificación: las tablas se crean y la cuenta/plantilla se guardan.
  - Relación: F-23, F-26, D-21, D-22.
- [ ] **T3.8 · Crear repositorios base por entidad (`repositories/`)**
  - Qué: capa de acceso a datos (altas, búsquedas y filtros frecuentes) usada por los servicios.
  - Verificación: los servicios no acceden al ORM directamente (revisión de código).
  - Relación: `PLAN.md` §1, §9.
- [ ] **T3.9 · Crear la semilla (seed) inicial**
  - Qué: niveles de cuota (Matrícula 5.000, Estándar 5.000, Activa 15.000), categorías base de egreso (Activos, Gastos fijos, Transferencias, Tarjeta, Otros), cuenta bancaria, plantilla de correo y un usuario Admin.
  - Verificación: ejecutar la semilla deja esos datos disponibles y es **idempotente**.
  - Relación: F-06, D-12, D-22, RN-01.
- [ ] **T3.10 · Script reproducible de esquema + semilla**
  - Qué: comando único para crear el esquema y cargar la semilla en un entorno nuevo.
  - Verificación: en una base vacía, el comando deja el sistema listo para operar.
  - Depende de: T2.4, T3.9.

---

## Fase 4 — Interfaz y navegación

### 4.A · Seguridad y sesiones

- [ ] **T4.1 · Implementar hash de contraseñas (`core/seguridad.py`)**
  - Qué: `hash_password` y `verify_password` con bcrypt/argon2.
  - Verificación: una prueba confirma que el hash no es reversible y la verificación es correcta.
  - Relación: `PLAN.md` §11.
- [ ] **T4.2 · Configurar sesiones firmadas**
  - Qué: `SessionMiddleware` con cookie `HttpOnly` y `SameSite`; helpers `iniciar_sesion`/`cerrar_sesion`/`usuario_actual`.
  - Verificación: tras iniciar sesión, la sesión persiste entre peticiones.
  - Nota: esquema **confirmado** (Q-2): sesión firmada `HttpOnly` + `SameSite=Lax`.
- [ ] **T4.3 · Rutas de login y logout**
  - Qué: formulario de acceso (UI-02), validación de credenciales y cierre de sesión.
  - Verificación: credenciales válidas acceden; inválidas muestran error sin revelar datos.
  - Relación: F-02, CA-21.
- [ ] **T4.4 · Dependencia de autorización por rol (`requiere_rol`)**
  - Qué: restringir rutas por rol; Admin y Tesorero con permisos iguales; Miembro restringido.
  - Verificación: un miembro recibe "acceso denegado" al intentar entrar a módulos financieros.
  - Relación: F-03, RN-07, CA-12, CA-13.
- [ ] **T4.5 · Protección CSRF en formularios de escritura**
  - Qué: token CSRF incluido en formularios POST y validado en el servidor.
  - Verificación: un POST sin token válido se rechaza.
  - Nota: confirmado como parte del esquema de seguridad (Q-2).
- [ ] **T4.6 · Navegación por rol en el layout**
  - Qué: menú y accesos visibles según el rol del usuario autenticado.
  - Verificación: el Admin/Tesorero ve los módulos de gestión; el Miembro solo su estado de cuenta.

### 4.B · Interfaz

- [x] **T4.7 · Landing page con las 8 secciones (UI-01)**
  - Subtareas: Header/Nav · Hero · Quiénes somos · Membresías (con precios 5.000/5.000/15.000) · Cómo funciona · Datos de transferencia · Contacto · Footer.
  - Verificación: la landing pública muestra las 8 secciones y es responsive.
  - Relación: F-28, UI-01, D-24.
- [x] **T4.8 · Interactividad de la landing con Alpine.js**
  - Qué: menú móvil, acordeón de "Cómo funciona" y modales.
  - Verificación: los componentes funcionan en escritorio y móvil.
  - Depende de: T2.7, T4.7.
- [ ] **T4.9 · Shell del panel Admin/Tesorero (UI-03)**
  - Qué: estructura de las vistas de gestión (miembros, membresías, pagos, morosidad, negociación, finanzas, compras, reportes).
  - Verificación: el panel carga con navegación y zona de contenido.
  - Relación: UI-03, UI-04.
- [ ] **T4.10 · Shell de la vista del Miembro (UI-05)**
  - Qué: vista restringida con perfil, estado de cuenta y avisos propios.
  - Verificación: el miembro solo ve su información.
- [ ] **T4.11 · Parcial de alertas y retroalimentación (UI-12)**
  - Qué: componente reutilizable de mensajes de éxito/error en español correcto.
  - Verificación: los formularios muestran confirmaciones y errores con este parcial.
  - Relación: UI-12, RN-16.
- [ ] **T4.12 · Utilidad y filtro de formato CLP (RN-24)**
  - Qué: `core/formato.py` con `formatear_clp`/`parsear_clp` y un filtro Jinja para usarlo en plantillas.
  - Verificación: `45000` se muestra como `45.000` en la interfaz.
  - Relación: F-27, RN-24.
- [ ] **T4.13 · Definir estilos de morosidad en Tailwind**
  - Qué: clases/utilidades para verde/naranjo/rojo reutilizables en tablas y tarjetas.
  - Verificación: un dato de prueba se resalta con el color correspondiente.
  - Relación: F-22, D-17.

---

## Fase 5 — Funcionalidades y reglas de negocio

> Fase núcleo. Se subdivide por dominio. Depende de las Fases 2, 3 y 4.

### 5.A · Miembros (F-01, F-04, F-05)

- [ ] **T5.1 · Alta de miembro**
  - Qué: formulario y validación de la ficha ampliada; captura automática de `fecha_incorporacion` como fecha de alta.
  - Verificación: se crea un miembro completo y la fecha de incorporación queda registrada (CA-16).
  - Relación: F-01, RN-11, RN-14, D-3, D-6.
- [ ] **T5.2 · Listado y búsqueda de miembros**
  - Qué: listado con búsqueda/filtro (por estado, categoría, morosidad).
  - Verificación: el listado muestra los miembros y los filtros devuelven resultados coherentes.
- [ ] **T5.3 · Edición de datos del miembro**
  - Qué: modificar datos de la ficha ampliada sin alterar el historial.
  - Verificación: los cambios se reflejan y se validan.
- [ ] **T5.4 · Cambio de categoría con historial (Activo ↔ Membresía)**
  - Qué: cambiar categoría entre Activo y Membresía, registrando el cambio y ajustando la cuota mensual.
  - Verificación: el historial registra el cambio y la cuota se ajusta (CA-29).
  - Relación: F-05, RN-25, D-26.
- [ ] **T5.5 · Activación de membresía**
  - Qué: evaluar el pago inicial (Matrícula + cuota de la categoría) y activar al miembro.
  - Verificación: con pago parcial queda pendiente; con pago completo queda activo (CA-01).
  - Relación: F-07, RN-02, D-11.
- [ ] **T5.6 · Vista del miembro (autoconsulta restringida)**
  - Qué: el miembro ve solo su perfil, estado de cuenta y avisos.
  - Verificación: no puede ver datos de otro miembro (CA-12).
  - Relación: F-04, RN-06.

### 5.B · Membresías y cuotas (F-06, F-09, F-10)

- [ ] **T5.7 · Administración del catálogo de cuotas**
  - Qué: vista de los tres niveles con sus montos (5.000 / 5.000 / 15.000).
  - Verificación: el catálogo coincide con RN-01 (CA-02).
  - Relación: F-06, RN-01.
- [ ] **T5.8 · Generación de cuotas mensuales**
  - Qué: crear las cuotas del periodo para miembros activos y no exentos, según su categoría.
  - Verificación: al generar un periodo, cada miembro activo/no exento recibe su cuota del monto correcto.
  - Relación: F-10, RN-12.
- [ ] **T5.9 · Regla del corte al día 5**
  - Qué: imputar al ciclo siguiente el pago realizado después del día 5.
  - Verificación: un pago posterior al día 5 queda imputado al siguiente ciclo (CA-04).
  - Relación: F-10, RN-03.
- [ ] **T5.10 · Manejo de exenciones**
  - Qué: marcar/quitar exención (becado, invitado/influencer, retirado) y excluir de cobros y avisos.
  - Verificación: un miembro exento no genera cuota ni avisos y su cuota se muestra exenta (CA-03).
  - Relación: F-09, RN-05.

### 5.C · Pagos (F-08, F-11, F-12, F-13, F-14)

- [ ] **T5.11 · Formulario de pago personalizado (UI-07)**
  - Qué: monto libre, selección de **año** y **meses**, medio (transferencia/efectivo excepcional) y **cuadro de observaciones**.
  - Verificación: el formulario permite ingresar un monto y seleccionar año/meses y guardar observaciones (CA-31).
  - Relación: F-12, F-14, F-26, D-20.
- [ ] **T5.12 · Registro de pago atómico**
  - Qué: `registrar_pago` valida y persiste el pago y sus imputaciones en una **única transacción**.
  - Verificación: si la imputación falla, no queda un pago parcial guardado.
  - Relación: F-08, `PLAN.md` §7, §9.
- [ ] **T5.13 · Imputación del monto (deuda antigua → mes/año → abono)**
  - Qué: aplicar el orden de imputación definido.
  - Verificación: un pago de 45.000 con deuda de 30.000 del año anterior salda esa deuda y cubre meses del año y deja saldo (CA-22).
  - Relación: F-13, RN-17, D-14.
- [ ] **T5.14 · Abono y aplicación automática**
  - Qué: generar abono cuando el excedente no alcanza una cuota y aplicarlo automáticamente a la siguiente.
  - Verificación: el saldo a favor se aplica solo a la próxima cuota (CA-23).
  - Relación: F-13, RN-18, D-15.
- [ ] **T5.15 · Estado de cuenta e informe calendario (UI-06)**
  - Qué: ver cuotas pagadas, pendientes y exentas, con estado y monto en CLP, más el abono disponible.
  - Verificación: el estado refleja fielmente los pagos e imputaciones (CA-14).
  - Relación: F-11, F-21, D-4.
- [ ] **T5.16 · Listado de ingresos con filtros (F-15)**
  - Qué: filtrar ingresos por tipo de cuota y por estado del usuario.
  - Verificación: los resultados coinciden con el filtro aplicado (CA-06).
  - Relación: F-15.

### 5.D · Mora y avisos (F-22, F-23)

- [ ] **T5.17 · Cálculo de morosidad (meses cerrados)**
  - Qué: calcular meses de deuda y monto considerando **solo meses cerrados**.
  - Verificación: el mes en curso no cuenta como deuda (P-5).
  - Relación: F-11, RN-04, P-5.
- [ ] **T5.18 · Clasificación por color**
  - Qué: verde (al día), naranjo (≤3 meses), rojo (>3 meses).
  - Verificación: cada caso de prueba se clasifica en el color correcto (CA-24).
  - Relación: F-22, RN-21, D-17.
- [ ] **T5.19 · Panel de morosidad (UI-08)**
  - Qué: listado de morosos con color, monto y meses, con selección para acciones.
  - Verificación: los morosos se muestran resaltados por color.
  - Relación: F-22, UI-08.
- [ ] **T5.20 · Aviso y plantilla de correo (mailto)**
  - Qué: generar el aviso para el Tesorero y armar el texto con datos del alumno, detalle de morosidad, adeudado y datos de cuenta; ofrecer enlace **mailto:** y marcar como enviado.
  - Verificación: el sistema **no** envía correo automático; el Tesorero dispone del texto y el aviso pasa a "enviado" al marcarlo (CA-15, CA-30).
  - Relación: F-23, RN-13, D-21, P-2.

### 5.E · Negociación de deuda (F-24)

- [ ] **T5.21 · Regla de elegibilidad y cálculo del descuento**
  - Qué: permitir negociar solo a morosos de **más de 6 meses** y calcular el monto con un **% editable** (0–100).
  - Verificación: un moroso de <6 meses es bloqueado; el monto negociado respeta el % (CA-25).
  - Relación: F-24, RN-22, D-18.
- [ ] **T5.22 · Crear y aceptar negociación + efecto en el color**
  - Qué: registrar la negociación (propuesta/aceptada/pagada); al pasar a "aceptada", esa deuda deja de contar para el color.
  - Verificación: en "aceptada" el color se recalcula sin esa deuda; en "propuesta" sigue contando (P-6).
  - Depende de: T5.18.
- [ ] **T5.23 · Registro de pago de una negociación**
  - Qué: al pagar, descargar la deuda negociada y actualizar el estado.
  - Verificación: la deuda queda saldada parcial o totalmente.

### 5.F · Finanzas (F-16, F-17, F-18)

- [ ] **T5.24 · Categorías de egreso (base + personalizadas)**
  - Qué: mantener la base fija, permitir crear personalizadas y activar/desactivar categorías.
  - Verificación: se puede registrar un egreso con categoría base o personalizada (CA-07).
  - Relación: F-16, RN-10, D-5, D-12, P-7.
- [ ] **T5.25 · Registro de egresos**
  - Qué: alta de egresos con monto, fecha, concepto y categoría.
  - Verificación: el egreso queda guardado y asociado a su categoría.
  - Relación: F-16.
- [ ] **T5.26 · Registro de adquisición de activos**
  - Qué: registrar compra de bienes con costo y miembro encargado de gestionar la compra.
  - Verificación: el activo queda registrado con ambos datos (CA-08).
  - Relación: F-17, D-9.
- [ ] **T5.27 · Registro de gastos fijos operativos**
  - Qué: registrar costos mensuales recurrentes.
  - Verificación: el gasto fijo se refleja como egreso recurrente (CA-09).
  - Relación: F-18, RN-12.
- [ ] **T5.28 · Listado y filtros de egresos**
  - Qué: listar egresos filtrados por categoría y por periodo.
  - Verificación: los resultados coinciden con los filtros.

### 5.G · Compras y cobro a alumnos (F-25)

- [ ] **T5.29 · Registro de compras del club y sus ítems**
  - Qué: registrar la compra (como pago/depósito) con sus ítems y montos.
  - Verificación: la compra y sus ítems quedan guardados.
  - Relación: F-25.
- [ ] **T5.30 · Generación de cargos a alumnos (cargo separado)**
  - Qué: asociar ítems a alumnos y generar cargos **separados** que no afectan la morosidad de cuotas.
  - Verificación: cada alumno recibe su cargo y su color de mora de cuotas no cambia (CA-27).
  - Relación: F-25, RN-23, D-19.
- [ ] **T5.31 · Saldar un cargo de alumno**
  - Qué: registrar el pago del cargo y marcarlo como pagado.
  - Verificación: el cargo pasa a "pagado" y refleja el monto.

### 5.H · Reportes e informes (F-19, F-20, F-21)

- [ ] **T5.32 · Reporte consolidado por periodo**
  - Qué: totalizar ingresos, egresos y diferencia para un rango de fechas.
  - Verificación: los totales coinciden con la suma de los movimientos (CA-10).
  - Relación: F-19.
- [ ] **T5.33 · Informe calendario por miembro**
  - Qué: informe mensual con estado y monto, visible por el miembro (lectura) y por Admin/Tesorero.
  - Verificación: el informe distingue pagadas, pendientes y exentas (CA-14).
  - Relación: F-21, D-4.
- [ ] **T5.34 · Selección de periodo y vista de reportes (UI-09)**
  - Qué: seleccionar el rango y presentar los totales.
  - Verificación: cambiar el rango recalcula el reporte.
  - Relación: UI-09.

---

## Fase 6 — Validaciones y manejo de errores

- [ ] **T6.1 · Esquemas Pydantic por formulario**
  - Qué: definir esquemas de entrada con campos obligatorios y tipos (montos enteros positivos, correo válido, fechas).
  - Verificación: un formulario con datos inválidos no se guarda y explica el motivo (CA-21).
  - Relación: `PLAN.md` §10.
- [ ] **T6.2 · Validación de reglas de negocio en los servicios**
  - Qué: aplicar activación completa, unicidad de pago por ciclo, rango de descuento, elegibilidad de negociación, exención y categoría válida.
  - Verificación: cada regla rechaza el caso inválido con mensaje claro.
  - Relación: RN-02, RN-08, RN-10, RN-22.
- [ ] **T6.3 · Manejo centralizado de errores (`core/errores.py`)**
  - Qué: respuestas y páginas para 400, 403, 404 y 409, con mensajes en español correcto.
  - Verificación: cada código muestra una página/mensaje adecuado (CA-13, CA-21).
  - Relación: RN-16, `PLAN.md` §10.
- [ ] **T6.4 · Cubrir los casos límite de `SPECS.md` §9**
  - Subtareas: datos vacíos/incompletos · datos inválidos · duplicados (email y pago por ciclo) · monto personalizado que genera abono o deuda · selección de meses inválida · pago a exento · pago posterior al día 5 · impago · negociación <6 meses · descuento fuera de rango · reporte sin datos ("sin movimientos") · exportación vacía · categoría inexistente · acceso no autorizado · operación no permitida por estado.
  - Verificación: cada caso se comporta como describe la especificación.
- [ ] **T6.5 · Retroalimentación en todos los formularios**
  - Qué: confirmaciones y errores visibles mediante el parcial de alertas.
  - Verificación: cada acción devuelve un mensaje claro.
  - Relación: UI-12.

---

## Fase 7 — Integraciones

- [ ] **T7.1 · Integrar la conexión MySQL/MariaDB end-to-end**
  - Qué: confirmar la conexión desde la app (dev y configuración productiva local).
  - Verificación: la app opera con MySQL de XAMPP.
  - Relación: P-1.
- [ ] **T7.2 · Exportación de reportes consolidados a XLSX**
  - Qué: generar el archivo XLSX del reporte con `openpyxl`.
  - Verificación: el archivo descargado contiene los mismos totales que la pantalla (CA-11).
  - Relación: F-20, P-3.
- [ ] **T7.3 · Exportación del informe calendario a PDF**
  - Qué: generar el PDF del informe calendario.
  - Verificación: el PDF refleja el estado y los montos del informe.
  - Relación: F-21, P-3.
- [ ] **T7.4 · Integrar la generación del enlace mailto en el aviso de morosidad**
  - Qué: componer el enlace `mailto:` con asunto y cuerpo de la plantilla y datos de la cuenta.
  - Verificación: al pulsarlo se abre el cliente de correo con el texto completo (CA-15).
  - Relación: F-23, P-2.

---

## Fase 8 — Pruebas y revisión

- [ ] **T8.1 · Configurar pytest y base de datos de prueba**
  - Qué: fixtures, base de prueba y utilidades para datos de ejemplo (miembros en distintos estados: al día, naranjo, rojo, exento).
  - Verificación: `pytest` corre y las pruebas base pasan.
- [ ] **T8.2 · Pruebas unitarias: activación**
  - Verificación: pago completo activa; pago parcial no (RN-02).
- [ ] **T8.3 · Pruebas unitarias: imputación**
  - Verificación: cubre deuda antigua → mes/año → abono, incluyendo el ejemplo de 45.000/30.000 (RN-17, CA-22).
- [ ] **T8.4 · Pruebas unitarias: abono automático**
  - Verificación: el abono se aplica a la siguiente cuota (RN-18, CA-23).
- [ ] **T8.5 · Pruebas unitarias: morosidad y colores**
  - Verificación: meses cerrados y umbrales verde/naranjo/rojo correctos (P-5, RN-21, CA-24).
- [ ] **T8.6 · Pruebas unitarias: negociación**
  - Verificación: elegibilidad >6 meses, % válido y efecto "aceptada" (RN-22, P-6, CA-25).
- [ ] **T8.7 · Pruebas unitarias: corte del día 5**
  - Verificación: pago posterior al día 5 al ciclo siguiente (RN-03, CA-04).
- [ ] **T8.8 · Prueba de integración: flujo de pago completo**
  - Verificación: registrar pago → imputar → actualizar estado de cuenta (transacción atómica).
- [ ] **T8.9 · Prueba de integración: alta y activación**
  - Verificación: alta de miembro → pago inicial → activo.
- [ ] **T8.10 · Prueba de integración: compra → cargo a alumno**
  - Verificación: la compra genera cargos separados sin alterar la mora de cuotas.
- [ ] **T8.11 · Checklist UAT contra los criterios de aceptación**
  - Qué: verificar **CA-01 … CA-31** de `SPECS.md` §10.
  - Verificación: cada criterio queda comprobado o registrado como pendiente.
- [ ] **T8.12 · Revisión de código y linting**
  - Qué: ejecutar `ruff` y revisar por pares la lógica crítica (pagos, mora, negociación).
  - Verificación: sin hallazgos bloqueantes; los observados quedan registrados.

---

## Fase 9 — Optimización básica

- [ ] **T9.1 · Índices de base de datos**
  - Qué: índices en `miembro_id`, `(anio, mes)`, `email`.
  - Verificación: los listados y el cálculo de mora responden con tiempos razonables.
- [ ] **T9.2 · Revisar consultas N+1 en listados**
  - Qué: cargar relaciones necesarias (miembros, cuotas, pagos) sin consultas redundantes.
  - Verificación: el número de consultas por pantalla es acotado.
- [ ] **T9.3 · Compilar Tailwind en modo producción**
  - Qué: generar el CSS minificado final.
  - Verificación: la interfaz usa el CSS compilado y sin errores.
- [ ] **T9.4 · Caché de catálogos estáticos**
  - Qué: cachear niveles de cuota, cuenta bancaria y categorías base.
  - Verificación: los catálogos no se consultan repetidamente en cada request.

---

## Fase 10 — Documentación y preparación final

- [ ] **T10.1 · Completar el `README.md`**
  - Qué: requisitos, instalación, configuración, semilla, ejecución y estructura.
  - Verificación: una persona puede levantar el proyecto siguiendo el README.
- [ ] **T10.2 · Documentar `.env.example`**
  - Qué: describir cada variable (conexión, secreto, entorno).
  - Verificación: el archivo cubre todas las variables usadas.
- [ ] **T10.3 · Guía de despliegue local (Uvicorn + XAMPP/MySQL)**
  - Qué: pasos de ejecución local y consideraciones de producción futura.
  - Verificación: la guía permite ejecutar el MVP localmente.
  - Relación: P-8.
- [ ] **T10.4 · Revisión final de cobertura contra `SPECS.md`**
  - Qué: comprobar que cada `F-` y `RN-` está implementado y cada `CA-` es verificable.
  - Verificación: matriz de cobertura sin faltantes.
- [ ] **T10.5 · Validación end-to-end del MVP**
  - Qué: recorrido completo (alta → activación → pago → mora → negociación → egresos → compras → reportes → landing).
  - Verificación: el recorrido se completa sin errores.
- [ ] **T10.6 · Registrar pendientes no bloqueantes**
  - Qué: dejar constancia de la publicación productiva y los respaldos como trabajo **post-MVP** (Q-3).
  - Verificación: quedan documentados en el README o en `PLAN.md` §14.

---

## Dependencias clave (resumen)

- Fases 2 y 3 dependen de la Fase 1.
- Fase 4.A (seguridad/sesiones) es requisito para las vistas protegidas de la Fase 5.
- Fase 5.C (Pagos) depende de 5.A y 5.B; es el núcleo y la base de 5.D, 5.E, 5.H.
- 5.E depende de 5.D (color/mora); 5.H depende de 5.C y 5.F.
- Fase 6 es transversal; conviene aplicarla junto con cada tarea de la Fase 5.
- Fase 7 depende de 5.H y 5.D.
- Fase 8 depende de las funcionalidades implementadas (Fases 5–7).
- Fases 9 y 10 cierran el MVP.

---

## Decisiones resueltas y pendientes

### Resueltas (ronda Q-1…Q-4)

| Código | Tema | Decisión |
| :--- | :--- | :--- |
| **Q-1** | Paleta y morosidad | Valores por defecto de Tailwind: Rojo `red-600` (#DC2626), Negro `black` (#000000), Blanco `white` (#FFFFFF); morosidad verde `green-600` (#16A34A), naranjo `amber-500` (#F59E0B), rojo `red-500` (#EF4444). Desbloquea T1.8 y T4.13. |
| **Q-2** | Sesión y CSRF | **Confirmada** la propuesta: sesión firmada `HttpOnly` + `SameSite=Lax` y token CSRF en formularios de escritura. Desbloquea T4.2 y T4.5. |
| **Q-3** | Publicación y respaldos | Solo entorno local (Uvicorn + MySQL de XAMPP) para el MVP; publicación productiva y respaldos como trabajo post-MVP (T10.6). |
| **Q-4** | Nombre de la base de datos | `osorno_runners`. Aplicado en T1.7. |

### Pendientes (post-MVP, no bloqueantes)

- **Publicación productiva y respaldos:** definir servidor, proxy inverso, HTTPS y política de copias de seguridad cuando el sistema salga de local (Q-3, T10.6).
