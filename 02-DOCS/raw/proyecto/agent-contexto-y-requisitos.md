# AGENT.md — Contexto y requisitos funcionales

> Source: specs/AGENT.md
> Collected: 2026-10-26
> Published: Unknown

# AGENT.md

## 🚀 Contexto General del Proyecto: Sistema Gestión Pagos Osorno Runners

### 🎯 Título del Proyecto
**Sistema Gestión Pagos Osorno Runners**

### 💡 Problema y Necesidad a Resolver
El club de running requiere una plataforma integral, robusta y centralizada para gestionar el ciclo completo de vida de sus miembros, abarcando desde la incorporación y el pago hasta la facturación recurrente, el control de la morosidad, la negociación de deudas y la generación de reportes. El objetivo primordial es establecer una transparencia operativa para el Tesorero y proporcionar una experiencia de usuario fluida y atractiva para todos los miembros.

### 💡 Concepto Central de la Solución
El proyecto se concibe como el desarrollo del *backend* y *frontend* operativo para un club deportivo de running. La prioridad es la facilidad de registro, la precisión en el cobro, la claridad visual de la morosidad y la personalización de la comunicación con los usuarios. No se trata de un sistema de gimnasio, sino de una herramienta diseñada específicamente para la comunidad de corredores.

### 🎯 Objetivo General del Proyecto
Implementar una plataforma integral y robusta que centralice toda la gestión financiera, administrativa y de membresía, asegurando la transparencia operativa para el Tesorero y ofreciendo una experiencia de usuario fluida y atractiva para los miembros.

### 🛠️ Stack Técnico
*   **Backend:** **FastAPI** (Python).
*   **Plantillas / Frontend:** **HTML/CSS** servido con **Jinja2**.
*   **Estilos:** **Tailwind CSS**.
*   **Interactividad:** **Alpine.js** (menú móvil, modales, acordeones, navegación dinámica).
*   **Identidad visual:** paleta **Rojo, Negro y Blanco**.

### 👥 Usuarios y Público Objetivo
1.  **Administrador (Admin):** Persona con control total del sistema, responsable de la gestión de usuarios, la configuración de cuotas y la visibilidad completa de la información financiera y operativa.
2.  **Tesorero:** Usuario con acceso a todos los módulos de ingresos y egresos, encargado de reportar, generar estados de cuenta y gestionar la morosidad.
3.  **Usuarios Normales (Miembros):** El público final. Su acceso debe ser limitado y restringido, permitiéndoles únicamente revisar su propio estado de cuenta, su información personal y los avisos asociados a su perfil.

> **Nota de permisos:** el **Admin y el Tesorero operan con permisos iguales** en el MVP (usuarios, membresías, finanzas y reportes).

### 🧩 Alcance Funcional y Requerimientos Clave

**1. Identidad, Marca y Stack:**
*   **Nombre oficial:** Sistema Gestión Pagos Osorno Runners.
*   **Identidad Visual:** Aplicación consistente de la paleta de colores Rojo, Negro y Blanco.
*   **Moneda oficial:** CLP (pesos chilenos). Los montos se muestran con separador de miles por punto (ej. `45.000`) y **montos cerrados** (sin decimales).
*   **Stack:** FastAPI + Jinja2 + HTML/CSS + Tailwind CSS + Alpine.js.

**2. Cuenta Bancaria y Medios de Pago:**
*   **Datos de Transferencia** (ver sección de Datos de Transferencia): se usan en la plataforma y en las plantillas de correo.
*   **Medios de pago:** los pagos se realizan **siempre por transferencia**; el **efectivo** se admite como **excepción** (casos puntuales). **No existen otros medios de pago**.

**3. Estructura de Membresías, Estados y Cobros:**
*   **Gestión de Niveles de Cuotas:** Implementar la lógica para manejar tres niveles de cuotas con sus condiciones asociadas:
    *   Matrícula: 5.000 CLP (Pago único de incorporación).
    *   Membresía Estándar: 5.000 CLP (Cuota mensual **opción de apoyo**: miembros que no quieren retirarse y siguen en contacto con el club, sin entrenamiento activo).
    *   Membresía Activa: 15.000 CLP (Cuota mensual **estándar para los alumnos** que entrenan activamente).
*   **Estados del Miembro:** los miembros pueden **cambiar de estado entre "Activo" (alumno) y "Membresía" (apoyo) y viceversa**; cada cambio queda registrado. Otros estados: **Moroso**, **Exento** y **Retirado**.
*   **Manejo de Exenciones:** debe existir una funcionalidad que permita la exclusión automática de pagos para casos específicos (becados, invitados/influencers y miembros retirados).
*   **Lógica de Activación:** un usuario obtiene el acceso como "Activo" una vez que se ha completado el pago inicial (**Matrícula + la cuota de su categoría elegida**: Activa para alumnos o Estándar para apoyo).
*   **Ciclo de Cobro Proactivo:** la facturación mensual aplica automáticamente la cuota al **siguiente ciclo** si el pago se realiza **después del día 5** de cada mes.
*   **Mora:** si el miembro **no paga** dentro del mes, la cuota se **acumula como deuda** y el miembro pasa a estado **Moroso**, conservando el acceso de consulta a su estado de cuenta.
*   **Los pagos no generan impuestos:** solo se registran; la morosidad se refleja por estado y color.
*   **Registro de Datos:** la **fecha de incorporación** se captura automáticamente como la fecha de **alta** del miembro en el sistema.

**4. Registro de Pagos Personalizados:**
*   **Monto personalizado en el formulario de pagos:** el Tesorero puede registrar un monto libre que puede cubrir **varias cuotas** e incluso **cubrir cuotas de un año a otro**. Ejemplo: un alumno paga 45.000, debía 30.000 del año anterior y el resto queda como saldo a favor para una cuota del año siguiente.
*   **Selección de año y meses a cubrir** por el pago.
*   **Imputación del monto:** primero la **deuda más antigua**, luego los **meses/año indicados**, y el excedente como **abono**.
*   **Abono (saldo a favor):** si el saldo no alcanza para la siguiente cuota, queda como **abono** que **se aplica automáticamente** a la siguiente cuota.
*   **Observaciones:** el formulario incluye un cuadro para agregar **observaciones** cuando sea necesario.
*   El monto y el formulario contemplan todas las opciones de estado y categoría del miembro (año, meses, abonos y observaciones).

**5. Gestión Financiera (Módulo Tesorero):**
*   **Registro de Ingresos:** capacidad para registrar todos los pagos recibidos, permitiendo el filtrado por tipo de cuota y estado del usuario.
*   **Registro de Egresos (Gastos):** módulo detallado para registrar todas las salidas de dinero (transferencias, pagos con tarjeta) y vinculando estos gastos a categorías.
*   **Adquisición de Activos:** funcionalidad para registrar la compra de bienes del club (ejemplo: camisetas, polerones), especificando el costo y el miembro encargado de gestionar la compra.
*   **Gastos Fijos:** capacidad para registrar costos operativos mensuales recurrentes (sueldo del profesor y mantención de cuenta corriente).
*   **Reportes Consolidados:** generación de informes financieros que contrasten ingresos totales contra egresos totales en un periodo seleccionado.

**6. Mora, Colores y Negociación:**
*   **Clasificación visual de la morosidad:** los pagos **al día** se resaltan en **verde**; los con deuda de **hasta 3 meses**, en **naranjo**; y los con deuda de **más de 3 meses**, en **rojo**. La morosidad debe quedar resaltada.
*   **Estado de cuotas para entrega del informe:** el informe de cuotas lleva el **estado** y su **pago en dinero**.
*   **Negociación de deuda:** debe existir una sección para **negociar la deuda** de alumnos morosos de **más de 6 meses**, aplicando un **descuento en porcentaje (%) editable**.

**7. Compras del Club y Cobro a Alumnos:**
*   **Registro de compras del club** como pagos o depósitos.
*   **Módulo de compras y reventa:** ocasionalmente el club compra polerones, poleras u otros extras que luego se cobran a los alumnos; debe existir un módulo para registrar estas compras y su cobro posterior a los alumnos.

**8. Comunicación, Marca y Avisos:**
*   **Avisos de morosidad (manuales):** los correos que recuerdan la morosidad **no son automáticos**. El sistema **avisa al Tesorero** dentro de la plataforma y el **Tesorero envía el correo**.
*   **Plantilla de correo:** debe existir una plantilla tipo que incluya los **datos del alumno**, el **detalle de la morosidad** y lo **adeudado**, además de los **datos de la cuenta corriente** a la cual se realizan las transferencias.
*   **Informes de Cuotas:** informes mensuales con formato calendario para cada usuario, que muestran el estado y el monto.
*   **Exportación de Reportes:** capacidad para exportar los informes para su distribución.
*   **Plataforma de Entrada (Landing Page):** diseño de una *Landing Page* profesional con la paleta oficial, que sirva como punto de entrada y se integre de forma fluida con el sistema.

**9. Roles y Seguridad:**
*   **Definición de Permisos:** implementar control de permisos estricto (Admin, Tesorero, Normal), con Admin y Tesorero de permisos iguales.

### 🏦 Datos de Transferencia (Configuración)

Estos datos se muestran en la plataforma y en las plantillas de correo:

*   **Titular:** Olimpia Runners Osorno.
*   **Banco:** Banco Santander.
*   **Cuenta Corriente:** 72769929.
*   **RUT:** 65.161.804-5.
*   **Correo:** tesoreriaor@gmail.com.

> **Nota:** aunque el titular diga "Olimpia Runners Osorno", corresponde al mismo club. "Olimpia Runners" era el nombre anterior del club; el cambio de nombre en el banco no se ha realizado por lo engorroso del trámite.

### ⚙️ Restricciones y Consideraciones Generales

*   **Idioma y Estilo:** el proyecto debe ser desarrollado bajo el estándar de codificación UTF-8 y cumplir estrictamente con las reglas ortográficas de la Real Academia Española (RAE), incluyendo el uso correcto de todos los tildes (acentos gráficos) y la letra "ñ".
*   **Moneda:** oficial en **CLP**, con separador de miles por punto y montos cerrados.
*   **Alcance:** el desarrollo inicial se limitará estrictamente a las funcionalidades esenciales del MVP. Se evitarán detalles técnicos de implementación (ej. nombres de clases, código específico, estructuras de carpetas).

---
**Nota:** Este documento establece el marco de referencia. El siguiente paso es traducir estas especificaciones en un plan técnico ejecutable. El detalle funcional verificado se encuentra en `specs/SPECS.md`.
