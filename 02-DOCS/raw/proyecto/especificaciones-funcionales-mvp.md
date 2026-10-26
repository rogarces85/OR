# SPECS.md — Especificaciones funcionales del MVP

> Source: specs/SPECS.md
> Collected: 2026-10-26
> Published: Unknown

# Especificaciones Funcionales del MVP — Sistema Gestión Pagos Osorno Runners

> **Fuente principal:** `specs/AGENT.md`.
> **Naturaleza del documento:** especificación **funcional** (qué debe hacer el producto), sin decisiones de implementación.
> **Convenciones:** los requisitos confirmados se identifican con códigos `F-` (funcionalidad), `RN-` (regla de negocio) y `CA-` (criterio de aceptación). Las decisiones tomadas durante la revisión se identifican con `D-` y se resumen en la sección 13. Las contradicciones detectadas se documentan en la sección 12.

---

## 1. Descripción del MVP

El MVP es la **plataforma operativa** (backend y frontend) del club de running **Osorno Runners**, cuyo sistema se denomina **Sistema Gestión Pagos Osorno Runners**. Centraliza el ciclo de vida de sus miembros: incorporación, activación de la membresía, cobro de cuotas, control visual de la morosidad, negociación de deudas, registro de ingresos y egresos, y generación de reportes financieros consolidados.

**Problema que resuelve:** hoy la gestión de membresías, cobros, morosidad y finanzas del club no está centralizada, lo que dificulta la transparencia y el control operativo del Tesorero y la consulta del propio estado por parte de los miembros.

**Propósito:** entregar al Tesorero una herramienta transparente de gestión financiera y administrativa, con control claro de la morosidad, y a los miembros una experiencia simple y atractiva para revisar su estado de cuenta. No es un sistema de gimnasio: está diseñado específicamente para la comunidad de corredores.

**Resultado observable del MVP:** un club puede registrar a sus miembros, activarlos mediante el pago inicial, registrar pagos personalizados (que cubren varias cuotas y cruzan años, con abonos), ver la morosidad en colores, negociar deudas, registrar gastos e ingresos (incluidas compras que luego se cobran a los alumnos), y obtener un reporte consolidado de ingresos contra egresos en un periodo.

---

## 2. Objetivos

### Objetivo general
Implementar una plataforma integral y robusta que centralice toda la gestión financiera, administrativa y de membresía, asegurando la transparencia operativa para el Tesorero y ofreciendo una experiencia de usuario fluida y atractiva para los miembros.

### Objetivos específicos
- **OE-1:** Gestionar los niveles de cuota y sus condiciones (Matrícula, Membresía Estándar y Membresía Activa).
- **OE-2:** Implementar la lógica de activación de miembros a partir del pago inicial obligatorio.
- **OE-3:** Implementar el ciclo de cobro mensual proactivo con corte al día 5 y el manejo de la mora.
- **OE-4:** Permitir el manejo de exenciones de pago (becados, invitados/influencers y retirados).
- **OE-5:** Permitir el registro de **pagos personalizados** que cubran varias cuotas y años, con **abonos**.
- **OE-6:** Reflejar la **morosidad por colores** y permitir la **negociación de deuda**.
- **OE-7:** Proveer el registro de ingresos y egresos, incluyendo activos, gastos fijos y **compras cobradas a alumnos**.
- **OE-8:** Generar y exportar reportes financieros consolidados por periodo.
- **OE-9:** Garantizar el control de permisos por rol (Admin, Tesorero, Miembro).
- **OE-10:** Entregar la identidad visual consistente, la landing page y los avisos de morosidad (manuales).

---

## 3. Usuarios

| Tipo de usuario | Descripción y necesidades | Permisos conceptuales |
| :--- | :--- | :--- |
| **Administrador (Admin)** | Control total del sistema. Necesita gestionar usuarios, configurar cuotas y acceder a toda la información financiera y operativa. | **Permisos iguales a los del Tesorero** (ver D-7): usuarios, membresías, finanzas y reportes. |
| **Tesorero** | Responsable financiero. Necesita registrar ingresos y egresos, pagos personalizados, gestionar morosidad y negociaciones, y generar estados de cuenta y reportes. | **Permisos iguales a los del Admin** (ver D-7): usuarios, membresías, finanzas y reportes. |
| **Miembro (usuario normal)** | Público final. Necesita revisar únicamente su propio estado de cuenta y su información personal. | Acceso limitado y restringido: solo su propio estado de cuenta, perfil y avisos. |

> **D-7 (decisión):** el Admin y el Tesorero operan con **permisos iguales** en el MVP, incluida la gestión de usuarios y membresías. La única diferencia funcional relevante respecto del miembro es el acceso pleno a finanzas y administración.

**Necesidades transversales:** registro fácil, claridad sobre cuánto y cuándo pagar, control visual de la morosidad y transparencia sobre el estado de la propia membresía.

---

## 4. Funcionalidades

Cada funcionalidad describe el **comportamiento esperado** (qué hace), no cómo se implementa.

### A. Usuarios, acceso y seguridad
- **F-01 — Registro y edición de miembros.** El Admin/Tesorero puede incorporar un nuevo miembro y editar su **ficha ampliada**: nombre completo, correo electrónico (identificador único), teléfono, RUT, fecha de nacimiento, **fecha de ingreso**, dirección, contacto de emergencia y estado de **matriculado** (ver D-3 y D-6). La fecha de ingreso se propone como la fecha de alta en el sistema, pero queda editable para registrar la fecha real de incorporación al club.
- **F-02 — Autenticación.** Cada usuario accede al sistema mediante inicio de sesión identificándose de forma única.
- **F-03 — Control de permisos por rol.** El sistema restringe qué puede ver y hacer cada rol conforme a la sección 3 (Admin y Tesorero con permisos iguales; Miembro restringido a su propia información).
- **F-04 — Autoconsulta del miembro.** El miembro puede ver únicamente su información personal y su propio estado de cuenta; no puede ver datos de otros miembros ni información financiera global del club.
- **F-05 — Cambio de categoría de membresía.** El Admin/Tesorero puede cambiar la categoría de un miembro entre **Activo** (alumno) y **Membresía** (apoyo), y viceversa. Cada cambio queda **registrado** (ver D-26 y RN-25).

### B. Membresías y cobros
- **F-06 — Catálogo de niveles de cuota.** El sistema maneja tres niveles de cuota con sus condiciones:
  - **Matrícula:** 5.000 CLP, pago único de incorporación.
  - **Membresía Estándar:** 5.000 CLP, cuota mensual **opción de apoyo**: para miembros que no quieren retirarse y siguen en contacto con el club (sin entrenamiento activo).
  - **Membresía Activa:** 15.000 CLP, cuota mensual **estándar para los alumnos** (miembros que entrenan activamente).
- **F-07 — Activación de membresía.** Un miembro pasa a estado **Activo** solo cuando se ha completado el pago inicial: **Matrícula + la cuota de su categoría elegida** (Activa para alumnos, Estándar para miembros de apoyo; ver D-11 y RN-02). La Matrícula no se cobra a quienes ya están marcados como **matriculados** ni a ingresos anteriores al **01/09/2025** (ver RN-27).
- **F-08 — Registro de pagos.** El Admin/Tesorero registra los pagos recibidos de cada miembro (ver F-12 para el pago personalizado), asociándolos al tipo de cuota y al periodo/ciclo correspondiente.
- **F-09 — Manejo de exenciones.** El sistema permite marcar a un miembro de forma que quede excluido automáticamente del pago en casos específicos: **becados**, **invitados/influencers** y **miembros retirados**. Un miembro exento no genera cobro mientras mantenga esa condición.
- **F-10 — Ciclo de cobro mensual proactivo.** El sistema aplica la facturación mensual con **corte al día 5**: si el pago del mes se realiza **después del día 5**, la cuota se aplica automáticamente al **siguiente ciclo**.
- **F-11 — Estado de cuenta y mora.** El miembro (y el Admin/Tesorero respecto de cualquier miembro) puede consultar el detalle de sus cuotas. Si un miembro **no paga** dentro del mes, la cuota se **acumula como deuda** y el miembro pasa a condición **Moroso** hasta regularizar, **conservando el acceso de consulta** a su estado de cuenta (ver D-1).

### C. Registro de pagos personalizados
- **F-12 — Pago personalizado con cobertura múltiple.** El formulario de pagos permite registrar un **monto personalizado** que puede cubrir **varias cuotas**, incluso **cruzando de un año a otro**, indicando el **año** y los **meses** a cubrir (ver D-14, D-20).
- **F-13 — Imputación y abono.** El monto se imputa en el orden: **deuda más antigua → meses/año indicados → abono**. Si el excedente no alcanza para la siguiente cuota, queda como **abono (saldo a favor)** que **se aplica automáticamente** a la siguiente cuota (ver D-14, D-15).
- **F-14 — Observaciones del pago.** El formulario de pagos incluye un **cuadro de observaciones** para registrar notas cuando sea necesario (ver D-20).

### D. Gestión financiera (Admin/Tesorero)
- **F-15 — Registro de ingresos.** Registro de todos los pagos recibidos, con capacidad de **filtrar por tipo de cuota** y por **estado del usuario**.
- **F-16 — Registro de egresos (gastos).** Registro de todas las salidas de dinero (por ejemplo, transferencias o pagos con tarjeta), **vinculando cada gasto a una categoría**. El catálogo tiene una **base fija** (Activos, Gastos fijos, Transferencias, Tarjeta y Otros) y admite **categorías personalizadas** creadas por el Admin/Tesorero (ver D-5 y D-12).
- **F-17 — Adquisición de activos.** Registro de la compra de bienes del club (por ejemplo, camisetas o polerones), especificando el **costo** y el **miembro responsable**, entendido como el miembro **encargado de gestionar la compra** (sin que ello implique un cobro a su persona; ver D-9).
- **F-18 — Gastos fijos operativos.** Registro de costos operativos mensuales recurrentes (por ejemplo, sueldo del profesor y mantención de cuenta corriente).
- **F-19 — Reportes consolidados.** Generación de informes que contrastan **ingresos totales contra egresos totales** en un periodo seleccionado.
- **F-20 — Exportación de reportes.** Capacidad de exportar los informes para su distribución.

### E. Informes, avisos y marca
- **F-21 — Informes mensuales de cuotas.** Informes mensuales con **formato calendario** para cada miembro, que reflejan las cuotas del periodo distinguiendo pagadas, pendientes y exentas, y que llevan el **estado** y su **pago en dinero**. El **miembro los visualiza (solo lectura)**; el **Admin/Tesorero los visualizan y los exportan** (ver D-4).
- **F-22 — Clasificación de morosidad por colores.** El sistema resalta la morosidad de los pagos: **verde** (al día), **naranjo** (deuda de hasta 3 meses) y **rojo** (más de 3 meses) (ver D-17, RN-21).
- **F-23 — Avisos de morosidad (manuales).** El sistema **no** envía correos automáticos: **avisa al Tesorero** dentro de la plataforma y el **Tesorero envía el correo** usando una **plantilla** que incluye los datos del alumno, el detalle de la morosidad, lo adeudado y los datos de la cuenta para transferir (ver D-8, D-13, D-21).
- **F-24 — Negociación de deuda.** Sección para negociar la deuda de alumnos **morosos de más de 6 meses**, aplicando un **descuento en porcentaje (%) editable** (ver D-18).
- **F-25 — Compras del club y cobro a alumnos.** Registro de las **compras del club** (como pagos/depósitos) y de un **módulo de reventa**: compras de polerones, poleras u otros extras que luego se **cobran a los alumnos** como **cargo separado** (ver D-19).
- **F-26 — Cuenta bancaria y medios de pago.** El sistema maneja los **datos de la cuenta** para transferencias y los **medios de pago** admitidos: **transferencia** (principal) y **efectivo excepcional**; sin otros medios (ver D-16, D-22).
- **F-27 — Presentación de montos en CLP.** Todos los montos se expresan en **CLP**, con separador de miles por punto y **montos cerrados** (sin decimales) (ver D-23).
- **F-28 — Landing page.** Página de entrada profesional que presenta al club y da acceso al sistema, construida con el stack **FastAPI + Jinja2 + HTML/CSS + Tailwind CSS + Alpine.js** y los colores oficiales (ver D-24 y UI-01).
- **F-29 — Identidad visual.** Aplicación consistente de la paleta **Rojo, Negro y Blanco** en todas las vistas.

### Relaciones y dependencias funcionales
- **F-07** depende de **F-06** (definición de cuotas) y de **F-08** (registro del pago inicial).
- **F-10** depende de **F-06** y **F-08**, y su resultado alimenta **F-11**, **F-15**, **F-22** y **F-23**.
- **F-12** y **F-13** dependen de **F-06**, **F-08** y **F-05** (la categoría del miembro determina el monto de la cuota).
- **F-09** condiciona **F-07**, **F-10**, **F-15** y **F-23** (un miembro exento no genera ni requiere cobro ni avisos de pago).
- **F-22** y **F-23** dependen de **F-11** (condición de mora).
- **F-24** depende de **F-11** y **F-22** (aplica a morosos de más de 6 meses).
- **F-19** y **F-20** dependen de **F-08**, **F-12**, **F-15**, **F-16**, **F-17**, **F-18** y **F-25** (necesitan ingresos y egresos registrados).
- **F-21** depende de **F-08** y **F-10**.
- **F-01**, **F-02**, **F-03** y **F-05** son transversales: habilitan el acceso y la categorización de los miembros.

---

## 5. Flujos principales

### Flujo 1 — Incorporación y activación de un nuevo miembro
1. El Admin/Tesorero registra los datos del nuevo miembro (ficha ampliada, incluida su fecha de nacimiento y fecha de ingreso).
2. El sistema propone la **fecha de ingreso** como la fecha de alta, pero permite ajustarla a la fecha real de incorporación al club (D-3).
3. El sistema genera la obligación inicial: **Matrícula + la cuota de la categoría elegida** (Activa o Estándar; ver RN-02). La Matrícula se omite si el miembro ya está matriculado o ingresó antes del 01/09/2025 (RN-27).
4. El miembro permanece **pendiente** hasta completar ese pago inicial.
5. Al registrarse el pago completo, el miembro queda en estado **Activo**.

### Flujo 2 — Pago mensual de cuota
1. El sistema determina, para cada miembro activo y no exento, la cuota del ciclo mensual vigente.
2. Si el pago se registra **hasta el día 5** del mes, se imputa al ciclo en curso.
3. Si el pago se registra **después del día 5**, el sistema lo imputa al **siguiente ciclo**.
4. El Admin/Tesorero registra el ingreso en el módulo de ingresos (F-15).
5. El estado de cuenta del miembro (F-11) refleja la cuota pagada y la pendiente.

### Flujo 3 — Pago personalizado que cubre varias cuotas y años
1. El Admin/Tesorero abre el formulario de pagos del miembro.
2. Ingresa el **monto personalizado** y selecciona el **año** y los **meses** a cubrir.
3. El sistema imputa el monto en orden: **deuda más antigua → meses/año indicados → abono** (D-14).
4. Si queda un excedente menor a la siguiente cuota, se registra como **abono** y **se aplica automáticamente** a la siguiente cuota (D-15).
5. El Admin/Tesorero puede agregar **observaciones** (F-14).
6. El estado de cuenta se actualiza con las cuotas cubiertas y el abono vigente.

### Flujo 4 — Impago, mora y aviso manual
1. Al cerrarse el mes sin pago, la cuota impaga se **acumula como deuda** del miembro.
2. El miembro pasa a condición **Moroso** y el sistema lo resalta con el **color correspondiente** (naranjo hasta 3 meses; rojo más de 3 meses).
3. El sistema **avisa al Tesorero** dentro de la plataforma (no envía correos automáticos).
4. El Tesorero genera el correo recordatorio usando la **plantilla** (datos del alumno, morosidad, adeudado y datos de cuenta) y lo envía.
5. Cuando el miembro regulariza, la deuda acumulada se salda y vuelve a **al día**.

### Flujo 5 — Negociación de deuda
1. El Admin/Tesorero selecciona a un miembro **moroso de más de 6 meses**.
2. El sistema muestra la deuda acumulada y permite definir un **descuento en %** (editable, 0–100).
3. El sistema calcula el **monto negociado** y lo registra.
4. Al concretarse el pago, la deuda queda regularizada parcial o totalmente.

### Flujo 6 — Exención de un miembro
1. El Admin/Tesorero marca a un miembro como **becado**, **invitado/influencer** o **retirado**.
2. El sistema excluye automáticamente a ese miembro de la generación de cobros y de los avisos mientras mantenga la condición.
3. El estado de cuenta sigue siendo consultable, mostrando la cuota como **exenta** (no como deuda).

### Flujo 7 — Cambio de categoría (Activo ↔ Membresía)
1. El Admin/Tesorero cambia la categoría del miembro entre **Activo** (alumno) y **Membresía** (apoyo).
2. El sistema registra el cambio y ajusta la cuota mensual a la categoría correspondiente.
3. El estado de cuenta refleja la nueva categoría.

### Flujo 8 — Registro de un gasto (egreso)
1. El Admin/Tesorero accede al módulo de egresos.
2. Registra la salida de dinero con su concepto, monto, fecha y **categoría** (base fija o personalizada).
3. El sistema valida los datos y registra el egreso.
4. El egreso queda disponible para los reportes consolidados.

### Flujo 9 — Compra del club y cobro a un alumno
1. El Admin/Tesorero registra la **compra del club** (por ejemplo, polerones, poleras o extras) como pago/depósito.
2. En el **módulo de reventa** asocia los ítems a los alumnos correspondientes.
3. El sistema genera el **cargo separado** para cada alumno (no afecta la morosidad de cuotas; ver D-19).
4. Cuando el alumno paga, el cargo se salda.

### Flujo 10 — Generación y exportación de un reporte financiero
1. El Admin/Tesorero selecciona un **rango de fechas**.
2. El sistema consolida los ingresos y egresos del periodo.
3. El sistema genera el informe comparativo (total de ingresos contra total de egresos, con el resultado neto).
4. El Admin/Tesorero **exporta** el informe para su distribución.

### Flujo 11 — Consulta del miembro y aviso
1. El miembro inicia sesión.
2. El sistema lo identifica y le muestra **únicamente** su información personal, su estado de cuenta y su morosidad con el **color** correspondiente.
3. El miembro revisa sus cuotas (pagadas, pendientes y exentas), su abono y su informe mensual en formato calendario (solo lectura).

---

## 6. Interfaz y experiencia de usuario

Descripción de pantallas, vistas y comportamiento esperado (sin detalle de código).

- **UI-01 — Landing page.** Página de entrada profesional y pública con las siguientes secciones: **Header/Nav** (logo + "Osorno Runners", enlaces Inicio, Quiénes somos, Membresías, Contacto, y botón **Ingresar**), **Hero** (nombre del club, lema y llamada a la acción), **Quiénes somos**, **Membresías** (Matrícula 5.000, Estándar 5.000 y Activa 15.000), **Cómo funciona**, **Datos de transferencia**, **Contacto** y **Footer** con el nombre oficial del sistema. Construida con FastAPI + Jinja2 + HTML/CSS + Tailwind CSS + Alpine.js, responsive y con menú móvil, acordeón de preguntas y modales dinámicos (Alpine.js) (ver D-24).
- **UI-02 — Inicio de sesión.** Vista de acceso con identificación del usuario y manejo visible de errores de credenciales.
- **UI-03 — Panel administrativo (Admin/Tesorero).** Vistas para gestión de usuarios y membresías, cambios de categoría, configuración de cuotas, y acceso completo a información financiera y operativa. Ambos roles comparten las mismas vistas y acciones (D-7).
- **UI-04 — Panel financiero (Admin/Tesorero).** Vistas para ingresos, egresos, activos, gastos fijos, compras/reventa y reportes, con filtros por tipo de cuota y estado del usuario.
- **UI-05 — Vista del Miembro.** Vista restringida que muestra solo el perfil, el estado de cuenta y los avisos propios.
- **UI-06 — Estado de cuenta e informe calendario.** Presentación de las cuotas del miembro en **formato calendario**, con el **estado** y el **monto en CLP**, y distinción visual entre cuotas pagadas, pendientes (incluida la deuda acumulada) y exentas, más el **abono** disponible. El miembro la ve en solo lectura (D-4).
- **UI-07 — Formulario de pago personalizado.** Formulario con monto libre, selección de **año** y **meses**, visualización del **abono** resultante y un **cuadro de observaciones** (F-12, F-13, F-14).
- **UI-08 — Panel de morosidad.** Vista con la morosidad resaltada por **colores** (verde/naranjo/rojo), selección de morosos, generación del **correo con plantilla** y acceso a la **negociación de deuda** (F-22, F-23, F-24).
- **UI-09 — Vista de reportes.** Selección de periodo, presentación de totales de ingresos y egresos, y acción de exportación.
- **UI-10 — Identidad visual.** Paleta **Rojo, Negro y Blanco** aplicada de forma consistente, con estética intencional y diseño responsivo.
- **UI-11 — Avisos y plantilla de correo.** Zona donde el Tesorero ve la alerta de morosidad y la **plantilla de correo** con los datos del alumno, el detalle de la morosidad, lo adeudado y los **datos de la cuenta** para transferir (F-23).
- **UI-12 — Retroalimentación.** Toda acción (registrar, exportar, activar, aplicar descuento) debe entregar una confirmación o mensaje de error claro, en español correcto (RAE, con tildes y "ñ").

---

## 7. Datos

Información que debe manejarse, su significado y sus relaciones conceptuales (sin estructura técnica).

- **Datos del miembro (ficha ampliada, D-6).** Nombre completo, **correo electrónico (identificador único)**, teléfono, RUT, fecha de nacimiento, fecha de ingreso, dirección, contacto de emergencia y estado de **matriculado**.
- **Fecha de ingreso.** Fecha real de incorporación al club. Se propone la fecha de alta en el sistema, pero es editable (D-3).
- **Categoría de membresía.** **Activo** (alumno, cuota Activa) o **Membresía** (apoyo, cuota Estándar). El miembro puede cambiar de categoría y el **cambio queda registrado** (D-26).
- **Situación de activación.** **Pendiente** (sin pago inicial) o **Activo** (con pago inicial completo).
- **Condición de morosidad.** **Al día** o **Moroso**, con antigüedad de la deuda (para los colores).
- **Condición especial.** **Normal**, **Exento** (becado, invitado/influencer o retirado).
- **Niveles de cuota.** Catálogo de cuotas con su monto y condición: Matrícula (5.000 CLP, única), Membresía Estándar (5.000 CLP, mensual) y Membresía Activa (15.000 CLP, mensual).
- **Pagos.** Registro de cada pago recibido: monto, fecha, tipo de cuota asociado, miembro, **año y meses cubiertos**, imputación, **observaciones** y estado. El monto es libre (D-10, D-14, D-20).
- **Abono (saldo a favor).** Excedente de un pago que se aplica automáticamente a la siguiente cuota (D-15).
- **Egresos (gastos).** Registro de cada salida de dinero: monto, fecha, concepto y categoría asociada.
- **Categorías de egreso.** Clasificación de los gastos: una **base fija** (Activos, Gastos fijos, Transferencias, Tarjeta y Otros) más las **personalizadas** que cree el Admin/Tesorero (D-5, D-12).
- **Activos del club.** Bienes adquiridos: descripción, costo y **miembro encargado de gestionar la compra** (D-9).
- **Compras y reventa.** Compras del club y su cobro posterior a los alumnos como **cargo separado** (D-19).
- **Gastos fijos.** Costos operativos recurrentes de carácter mensual (sueldo del profesor, mantención de cuenta corriente).
- **Deuda acumulada.** Suma de cuotas impagas de un miembro moroso (D-1).
- **Negociación de deuda.** Deuda de un moroso de más de 6 meses, con el **% de descuento** aplicado y el monto negociado (D-18).
- **Cuenta bancaria.** Titular, banco, cuenta corriente, RUT y correo para transferencias (D-22).
- **Plantilla de correo.** Texto tipo con datos del alumno, detalle de morosidad, monto adeudado y datos de la cuenta (D-21).
- **Moneda.** CLP, con separador de miles por punto y montos cerrados (D-23).

**Relaciones conceptuales:**
- Un **miembro** tiene una **categoría** (con historial de cambios), una fecha de incorporación y una condición (normal/exento).
- Un **miembro** tiene muchos **pagos**; cada **pago** cubre uno o más **ciclos** y puede generar un **abono**.
- Un **miembro moroso** acumula **deuda** por sus cuotas impagas y puede tener una **negociación**.
- Un **egreso** pertenece a exactamente una **categoría**.
- Un **activo** referencia al **miembro encargado** de gestionar su compra.
- Una **compra** puede originar varios **cargos** a distintos alumnos (cargo separado).
- Un **gasto fijo** es un tipo recurrente de **egreso**.
- La **plantilla de correo** usa los datos del **miembro** y de la **cuenta bancaria**.
- Los **reportes** se derivan de la unión de **pagos** y **egresos** en un rango de fechas.

---

## 8. Reglas de negocio

- **RN-01 — Montos fijos.** Matrícula = 5.000 CLP (única); Membresía Estándar = 5.000 CLP (mensual); Membresía Activa = 15.000 CLP (mensual).
- **RN-02 — Condición de activación.** Un miembro solo es **Activo** si completó el pago de **Matrícula + la cuota de su categoría elegida** (Activa para alumnos o Estándar para miembros de apoyo). La Matrícula se excluye cuando el miembro ya está marcado como **matriculado** o cuando su fecha de ingreso es anterior al **01/09/2025** (RN-27). Esta decisión (D-11) prevalece sobre la redacción literal de `AGENT.md`, que indicaba "Matrícula + Estándar".
- **RN-03 — Corte de cobro al día 5.** Si el pago del mes se realiza después del día 5, la cuota se aplica al siguiente ciclo mensual.
- **RN-04 — Mora.** Si el miembro no paga dentro del mes, la cuota se **acumula como deuda** y el miembro pasa a condición **Moroso**, conservando el acceso de consulta a su estado de cuenta (D-1).
- **RN-05 — Exención automática.** Los miembros becados, invitados/influencers y retirados quedan excluidos automáticamente del cobro y de los avisos mientras mantengan esa condición.
- **RN-06 — Aislamiento de la información del miembro.** Un miembro solo puede ver su propia información, su propio estado de cuenta y sus propios avisos.
- **RN-07 — Permisos de gestión.** El Admin y el Tesorero tienen **permisos iguales** para gestionar usuarios, membresías, finanzas y reportes (D-7). El miembro no accede a estos módulos.
- **RN-08 — Unicidad de pago por ciclo.** No debe registrarse más de un pago para el mismo miembro, tipo de cuota y ciclo. (La libre elección de **monto** no habilita duplicar el pago de un ciclo; ver D-10.)
- **RN-09 — Monto libre.** El sistema **acepta cualquier monto** ingresado en un pago, sin exigir coincidencia con el monto de la cuota (D-10).
- **RN-10 — Categorías de egreso.** La base fija es **Activos, Gastos fijos, Transferencias, Tarjeta y Otros**; el Admin/Tesorero puede crear categorías personalizadas; todo egreso debe tener una categoría válida (D-5, D-12).
- **RN-11 — Identificador único del miembro.** El **correo electrónico** es el identificador único del miembro (D-6).
- **RN-12 — Recurrencia mensual.** Las cuotas de membresía y los gastos fijos operativos son de periodicidad mensual.
- **RN-13 — Avisos de morosidad (manual).** El sistema **no** envía correos automáticos: resalta la morosidad con colores, **avisa al Tesorero** y ofrece una **plantilla** para que el Tesorero envíe el correo (D-8, D-13, D-21).
- **RN-14 — Fecha de ingreso.** Se propone la fecha de alta en el sistema, pero el Admin/Tesorero puede ajustarla para reflejar la fecha real de incorporación al club (D-3).
- **RN-15 — Trazabilidad.** Todo ingreso y egreso queda vinculado a su fecha, monto y, cuando corresponda, a un miembro y a una categoría.
- **RN-16 — Idioma y estilo.** Todo el contenido textual debe cumplir el estándar de codificación UTF-8 y las reglas ortográficas de la RAE, con tildes correctas y uso de la "ñ".
- **RN-17 — Imputación de pagos.** El monto se imputa primero a la **deuda más antigua**, luego a los **meses/año indicados** y, finalmente, el excedente como **abono** (D-14).
- **RN-18 — Abono automático.** El saldo a favor (abono) **se aplica automáticamente** a la siguiente cuota (D-15).
- **RN-19 — Medios de pago.** Los pagos son por **transferencia** (principal); el **efectivo** se admite como **excepción**. No existen otros medios (D-16).
- **RN-20 — Sin impuestos.** Los pagos **no generan impuestos**; solo se registran y su morosidad se refleja por estado y color (D-25).
- **RN-21 — Colores de morosidad.** **Verde** = al día; **naranjo** = deuda de hasta 3 meses; **rojo** = deuda de más de 3 meses (D-17).
- **RN-22 — Negociación de deuda.** Aplica a morosos de **más de 6 meses**, con un **descuento en % editable** sobre la deuda acumulada (D-18).
- **RN-23 — Compras cobradas a alumnos.** Las compras cobradas a alumnos son un **cargo separado** y **no afectan** la morosidad de las cuotas mensuales (D-19).
- **RN-24 — Presentación de montos.** Todos los montos se expresan en **CLP**, con separador de miles por punto y **sin decimales** (D-23).
- **RN-25 — Cambio de categoría.** Un miembro puede cambiar entre **Activo** y **Membresía**; cada cambio queda registrado y ajusta la cuota mensual (D-26).
- **RN-26 — Datos de la cuenta.** Los datos de la cuenta bancaria (titular, banco, cuenta corriente, RUT y correo) se usan en la plataforma y en la plantilla de correo (D-22).
- **RN-27 — Cobro de matrícula.** La Matrícula se cobra solo a miembros **no matriculados** cuya fecha de ingreso sea igual o posterior al **01/09/2025**. Los miembros antiguos se marcan como **matriculados** para no generarles ese cobro (D-27).

---

## 9. Casos límite y errores

Comportamiento esperado ante situaciones anómalas.

- **Datos vacíos o incompletos.** No se puede registrar un miembro, pago, egreso, compra o activo si faltan campos obligatorios (según la ficha ampliada, D-6); el sistema indica qué falta.
- **Datos inválidos.** Fechas inválidas, campos con formato incorrecto, correo electrónico con formato inválido y montos no numéricos o negativos se rechazan con un mensaje claro.
- **Duplicados.** Se impide registrar un miembro con un **correo electrónico ya existente** (identificador único, RN-11) y duplicar un pago del mismo tipo de cuota y ciclo para un mismo miembro (RN-08).
- **Monto personalizado.** El sistema acepta montos libres (D-10); si el monto **no alcanza** a cubrir la cuota, el excedente o faltante se refleja como **abono** o **deuda pendiente** según corresponda (RN-17, RN-18).
- **Selección de meses inválida.** No se permite seleccionar meses/años inconsistentes o duplicados; el sistema lo advierte.
- **Pago de un miembro exento.** Registrar un cobro a un miembro exento (becado, invitado/influencer o retirado) debe advertirse o bloquearse, ya que no genera obligación.
- **Pago posterior al día 5.** No se rechaza: se imputa al siguiente ciclo (RN-03) y el estado de cuenta lo refleja.
- **Impago dentro del mes.** Genera deuda acumulada y condición **Moroso** (RN-04); no bloquea el acceso de consulta.
- **Deuda menor a 6 meses para negociar.** La sección de negociación rechaza o bloquea a morosos con menos de 6 meses de deuda (RN-22).
- **Descuento fuera de rango.** Un porcentaje de descuento fuera de 0–100 se rechaza con mensaje claro.
- **Correo de morosidad.** Si el Tesorero no envía el correo, no hay envío automático; el sistema solo mantiene la alerta y la plantilla disponible (RN-13).
- **Cargo de compra.** Un cargo por compra vencido **no** altera los colores de morosidad de las cuotas mensuales (RN-23).
- **Rango de fechas inválido.** En reportes, un rango vacío, invertido o mal formado se rechaza con un mensaje claro.
- **Reporte sin datos.** Si el periodo no tiene movimientos, el informe se muestra explícitamente como "sin movimientos" (no como error).
- **Exportación sin datos.** Se informa que no hay contenido para exportar.
- **Categoría de egreso inexistente.** No se puede registrar un egreso sin una categoría válida del catálogo (RN-10).
- **Acceso no autorizado.** Un miembro que intenta acceder a información de otros miembros o a módulos financieros recibe un mensaje de acceso denegado y no se le muestra la información.
- **Operación no permitida por estado.** Un miembro retirado o exento no recibe cobros ni avisos; el sistema informa su condición.

---

## 10. Criterios de aceptación

Condiciones observables y comprobables para verificar cada funcionalidad.

- **CA-01 (F-07/RN-02/RN-27):** Al registrar un miembro y completar el pago inicial (**Matrícula + la cuota de su categoría**, o solo la cuota si ya está matriculado), el sistema lo muestra como **Activo**; con pago parcial, queda **pendiente**.
- **CA-02 (F-06/RN-01):** El sistema presenta la Matrícula en 5.000 CLP como pago único, y las membresías Estándar y Activa en 5.000 y 15.000 CLP como cuotas mensuales.
- **CA-03 (F-09/RN-05):** Al marcar a un miembro como becado, invitado/influencer o retirado, el sistema deja de generar cobros y avisos para él y muestra su cuota como **exenta**.
- **CA-04 (F-10/RN-03):** Un pago registrado después del día 5 del mes queda imputado al siguiente ciclo, y el estado de cuenta lo refleja.
- **CA-05 (F-11/RN-04):** Al cerrarse un mes sin pago, la cuota se acumula como deuda, el miembro pasa a **Moroso** y puede seguir viendo su estado de cuenta.
- **CA-06 (F-15):** El Admin/Tesorero puede listar los ingresos y filtrarlos por tipo de cuota y por estado del usuario, obteniendo resultados coherentes con el filtro aplicado.
- **CA-07 (F-16/RN-10):** El Admin/Tesorero puede registrar un egreso con una categoría de la base fija o con una categoría personalizada que haya creado.
- **CA-08 (F-17):** El Admin/Tesorero puede registrar un activo indicando su costo y el miembro encargado de la compra, y ambos datos quedan visibles en el registro.
- **CA-09 (F-18/RN-12):** El Admin/Tesorero puede registrar un gasto fijo operativo mensual y este se refleja como egreso recurrente.
- **CA-10 (F-19):** Dado un periodo con ingresos y egresos conocidos, el reporte muestra el total de ingresos, el total de egresos y su diferencia, coincidiendo con la suma de los movimientos del periodo.
- **CA-11 (F-20):** El Admin/Tesorero puede exportar un reporte generado y el archivo resultante contiene los mismos totales mostrados en pantalla.
- **CA-12 (F-04/RN-06):** Un miembro autenticado puede ver su propio estado de cuenta y **no** puede ver el de otro miembro ni reportes globales.
- **CA-13 (F-03/RN-07):** El Admin y el Tesorero disponen exactamente de las mismas acciones; un miembro tiene denegado el acceso a los módulos de usuarios, membresías, finanzas y reportes.
- **CA-14 (F-21/D-4):** El miembro visualiza su informe mensual de cuotas en formato calendario con estado y monto (solo lectura), y el Admin/Tesorero pueden visualizarlo y exportarlo.
- **CA-15 (F-23/D-8/D-13/D-21):** Ante un moroso, el sistema **avisa al Tesorero** en la plataforma y le ofrece una **plantilla de correo** con los datos del alumno, el detalle de la morosidad, lo adeudado y los datos de la cuenta; **no** se envía correo automático.
- **CA-16 (F-01/D-6):** El sistema exige los datos de la ficha ampliada al registrar un miembro y rechaza un correo electrónico ya registrado.
- **CA-17 (F-08/D-10):** El sistema acepta el registro de un pago con un monto distinto al de la cuota, sin bloquearlo.
- **CA-18 (F-28/F-29):** Existe una landing page de entrada, integrada con el sistema, con las secciones definidas, construida con Jinja2/Tailwind/Alpine y que aplica la paleta Rojo, Negro y Blanco.
- **CA-19 (RN-16):** Todos los textos visibles están en español correcto, con tildes y "ñ" según la RAE.
- **CA-20 (RN-08):** Al intentar registrar un segundo pago para el mismo miembro, tipo de cuota y ciclo, el sistema lo impide e informa el motivo.
- **CA-21 (sección 9):** Ante datos vacíos, inválidos o campos incompletos, el sistema no guarda el registro y muestra un mensaje de error comprensible.
- **CA-22 (F-12/RN-17):** Al registrar un monto que cubre varias cuotas y cruza años, el sistema imputa primero la deuda más antigua, luego los meses/año indicados y el excedente como abono.
- **CA-23 (F-13/RN-18):** Un abono resultante se aplica automáticamente a la siguiente cuota del miembro.
- **CA-24 (F-22/RN-21):** Los pagos al día se muestran en verde, los de deuda de hasta 3 meses en naranjo y los de más de 3 meses en rojo.
- **CA-25 (F-24/RN-22):** Un moroso de más de 6 meses puede acceder a la negociación, y el descuento en % es editable; el sistema calcula el monto negociado.
- **CA-26 (F-27/RN-24):** Todos los montos se muestran en CLP con separador de miles por punto y sin decimales (ej. 45.000).
- **CA-27 (F-25/RN-23):** Una compra del club puede asociarse a alumnos y genera un cargo separado que no altera los colores de morosidad de las cuotas.
- **CA-28 (F-26/RN-19):** El sistema permite registrar el medio de pago como transferencia (principal) o efectivo (excepcional), y no ofrece otros medios.
- **CA-29 (F-05/RN-25):** Al cambiar la categoría de un miembro entre Activo y Membresía, el cambio queda registrado y la cuota mensual se ajusta.
- **CA-30 (F-26/RN-26):** Los datos de la cuenta (Olimpia Runners Osorno, Santander, Cta. Cte. 72769929, RUT 65.161.804-5, tesoreriaor@gmail.com) están disponibles en la plataforma y en la plantilla de correo.
- **CA-31 (F-14):** El formulario de pago permite agregar observaciones y estas quedan registradas con el pago.

---

## 11. Alcance

### Incluido en el MVP
- Gestión de los **tres niveles de cuota** y sus condiciones (Matrícula, Estándar, Activa).
- **Lógica de activación** por pago inicial (**Matrícula + la cuota de la categoría elegida**; ver RN-02 y D-11).
- **Cambio de categoría** entre Activo y Membresía, con registro (D-26).
- **Ciclo de cobro mensual** con corte al día 5 y manejo de **mora** (deuda acumulada).
- **Pago personalizado** con monto libre, año, meses, **abono** automático y **observaciones**.
- **Clasificación de morosidad por colores** (verde/naranjo/rojo).
- **Avisos de morosidad manuales** (alerta al Tesorero + plantilla de correo).
- **Negociación de deuda** para morosos de más de 6 meses (descuento % editable).
- **Exenciones** para becados, invitados/influencers y retirados.
- Registro de **ingresos** y **egresos** (incluyendo activos, gastos fijos y compras/reventa) por el Admin/Tesorero.
- **Categorías de egreso** con base fija y categorías personalizadas.
- **Compras del club** y su **cobro a alumnos** como cargo separado.
- **Reportes consolidados** de ingresos contra egresos por periodo y su **exportación**.
- **Control de permisos** por rol (Admin y Tesorero con permisos iguales; Miembro restringido).
- **Estado de cuenta** e **informe mensual en formato calendario** del miembro, con estado y monto en CLP.
- **Cuenta bancaria** y **medios de pago** (transferencia y efectivo excepcional).
- **Landing page** (FastAPI + Jinja2 + HTML/CSS + Tailwind CSS + Alpine.js) e **identidad visual** (Rojo, Negro, Blanco).

### Excluido del MVP
- Integración con **pasarelas de pago**: el sistema solo registra los pagos internamente; no cobra en línea.
- **Sistema avanzado de notificaciones automáticas**: los correos de morosidad son manuales (los envía el Tesorero).
- Módulos de **gestión de contenido o comunicación** (por ejemplo, foro interno, chat o gestión de redes).
- **E-commerce general y tienda pública**: solo se incluye el módulo interno de compras y su cobro a los alumnos.
- **Módulos no mencionados** en `AGENT.md` (por ejemplo, control de asistencia a entrenamientos o calendario de carreras).

---

## 12. Contradicciones detectadas y su estado

- **C-1 — Redacción del cobro proactivo. ✅ RESUELTA.** Se adoptó la redacción de `AGENT.md` (pago **después del día 5** → siguiente ciclo). El caso de **impago** quedó cubierto por D-1 (deuda acumulada).
- **C-2 — Fecha de incorporación ligada a la fecha de nacimiento. ✅ RESUELTA.** Se interpretó como error de redacción; la fecha de incorporación es la **fecha de alta en el sistema** (D-3).
- **C-3 — "Registrar sus propios egresos" (criterio de una versión previa). ✅ RESUELTA.** Solo el Admin/Tesorero registran egresos; el miembro no (CA-12 y CA-13).
- **C-4 — Relación entre "Membresía Activa" (15.000 CLP) y la activación. ✅ RESUELTA.** D-2 aclara el significado de las cuotas; D-11 define que la activación exige **Matrícula + la cuota de la categoría elegida**.
- **C-5 — Correos de morosidad (automáticos → manuales). ✅ RESUELTA por decisión.** La versión previa (D-8/D-13) definía avisos por correo **automáticos**. Se cambió a **manuales**: el sistema **avisa al Tesorero** y él envía el correo con una plantilla (D-21). Se actualizaron F-23, RN-13 y CA-15.
- **C-6 — Módulo de compras y cobro a alumnos. ✅ RESUELTA por decisión.** La versión previa excluía módulos de "tienda o e-commerce". Se agregó un **módulo interno de compras y reventa** con cargo separado (D-19); se mantiene **excluido** el e-commerce general y público.

---

## 13. Decisiones tomadas y pendientes

### Decisiones tomadas (revisión de especificación)

| Código | Tema | Decisión |
| :--- | :--- | :--- |
| **D-1** | Impago / mora | La cuota impaga se **acumula como deuda**; el miembro pasa a condición **Moroso** y **conserva** el acceso de consulta a su estado de cuenta hasta regularizar. |
| **D-2** | Significado de las cuotas | **Membresía Activa (15.000 CLP)** = cuota estándar de los **alumnos**. **Membresía Estándar (5.000 CLP)** = opción para miembros que **no quieren retirarse** y siguen en contacto con el club (apoyo). |
| **D-3** | Fecha de ingreso | Se propone la **fecha de registro/alta** en el sistema al crear al miembro, pero queda **editable** para reflejar la fecha real de incorporación al club. |
| **D-4** | Informe calendario | El **miembro** lo visualiza en **solo lectura**; el **Admin/Tesorero** lo visualizan y lo **exportan**. Muestra estado y monto en dinero. |
| **D-5** | Categorías de egreso | **Base fija** (Activos, Gastos fijos, Transferencias, Tarjeta y Otros) **+ categorías personalizadas** creadas por el Admin/Tesorero. |
| **D-6** | Datos del miembro | **Ficha ampliada**: nombre completo, **correo electrónico (identificador único)**, teléfono, RUT, fecha de nacimiento, fecha de ingreso, dirección, contacto de emergencia y estado de **matriculado**. |
| **D-7** | Permisos Admin/Tesorero | Ambos tienen **permisos iguales** en todas las áreas (usuarios, membresías, finanzas y reportes). |
| **D-8** | Avisos de morosidad | Aviso **en la plataforma** (colores + alerta al Tesorero) y **correo MANUAL** enviado por el Tesorero con una plantilla. *(Revisado: antes era correo automático; ver C-5.)* |
| **D-9** | Responsable del activo | Es el miembro **encargado de gestionar la compra** (sin implicar un cobro a su persona). |
| **D-10** | Monto del pago | Se **acepta cualquier monto**; no se exige coincidencia con el monto de la cuota. |
| **D-11** | Activación y categoría | La activación exige **Matrícula + la cuota de la categoría elegida** (Activa para alumnos, Estándar para apoyo). |
| **D-12** | Base de categorías de egreso | Base fija: **Activos, Gastos fijos, Transferencias, Tarjeta y Otros** (más las personalizadas). |
| **D-13** | Momento del aviso | La alerta de morosidad (al Tesorero) se genera **después del día 5 del mes si la cuota sigue pendiente**; el correo lo envía el Tesorero. *(Revisado: ver C-5.)* |
| **D-14** | Imputación de pagos | Orden de imputación: **deuda más antigua → meses/año indicados → abono**. |
| **D-15** | Abono | El **saldo a favor** (abono) **se aplica automáticamente** a la siguiente cuota. |
| **D-16** | Medios de pago | **Transferencia** (principal) y **efectivo** (excepcional); sin otros medios. |
| **D-17** | Colores de morosidad | **Verde** = al día · **Naranjo** = deuda de hasta 3 meses · **Rojo** = más de 3 meses. |
| **D-18** | Negociación de deuda | Aplica a morosos de **más de 6 meses**, con **descuento en % editable** (0–100) sobre la deuda acumulada; lo aplica el Admin/Tesorero. |
| **D-19** | Compras cobradas a alumnos | **Cargo separado** que **no afecta** la morosidad de las cuotas mensuales. |
| **D-20** | Formulario de pago | Incluye **monto libre**, **año**, **meses**, **abono** y un **cuadro de observaciones**. |
| **D-21** | Correos de morosidad | **Manuales**: el sistema alerta al Tesorero y le da una **plantilla** (datos del alumno, detalle de morosidad, adeudado y datos de la cuenta). |
| **D-22** | Cuenta bancaria | Titular **Olimpia Runners Osorno**, Banco Santander, Cta. Cte. 72769929, RUT 65.161.804-5, correo tesoreriaor@gmail.com. |
| **D-23** | Moneda y formato | **CLP** con separador de miles por punto y **montos cerrados** (sin decimales). |
| **D-24** | Landing page y stack | Landing con secciones (Header/Nav, Hero, Quiénes somos, Membresías, Cómo funciona, Datos de transferencia, Contacto, Footer), con **FastAPI + Jinja2 + HTML/CSS + Tailwind CSS + Alpine.js**. |
| **D-25** | Impuestos | Los pagos **no generan impuestos**; solo se registran y la morosidad se refleja por estado y color. |
| **D-26** | Cambio de categoría | Los miembros pueden cambiar entre **Activo** y **Membresía** (y viceversa); cada cambio queda registrado y ajusta la cuota. |
| **D-27** | Matrícula y miembros antiguos | Los miembros antiguos se marcan como **matriculados** para no volver a cobrarles la Matrícula. El cobro de Matrícula rige desde el **01/09/2025** para los miembros nuevos no matriculados. |

### Preguntas abiertas restantes

No quedan preguntas bloqueantes tras la ronda de decisiones. La especificación funcional del MVP se considera **cerrada**; cualquier ajuste futuro debe registrarse como una nueva decisión.
