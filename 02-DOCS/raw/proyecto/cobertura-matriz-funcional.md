# COBERTURA.md — Matriz de cobertura

> Source: specs/COBERTURA.md
> Collected: 2026-10-26
> Published: Unknown

# Matriz final de cobertura — SPECS.md

> **Tarea:** T10.4 · Revisión final de cobertura contra `SPECS.md`.
> **Fecha:** 19-10-2026.
> **Alcance:** F-01 … F-29, RN-01 … RN-26 y CA-01 … CA-31.
> **Resultado:** **sin faltantes funcionales**. La suite ejecuta **132 pruebas**
> (`pytest`) y `ruff check app tests` sin hallazgos. También se ejecutó contra
> MySQL: **131 aprobadas + 1 omitida** (el plan de consulta se verifica solo
> sobre SQLite). La verificación manual de responsive y copy se mantiene como
> revisión de demo (ver `specs/UAT.md`).

## 1. Funcionalidades (F)

| F | Funcionalidad | Implementación | Evidencia |
| :-- | :-- | :-- | :-- |
| F-01 | Registro de miembros con ficha ampliada y fecha de incorporación | `app/services/membresias.py` (`crear_miembro`), `app/routers/miembros.py`, `app/templates/miembros/` | `tests/test_web.py` (alta y duplicados), `tests/test_integracion_activacion.py` |
| F-02 | Autenticación por inicio de sesión | `app/routers/auth.py`, `app/core/seguridad.py` | `tests/test_web.py` (login válido/inválido y CSRF) |
| F-03 | Permisos por rol (Admin/Tesorero iguales; Miembro restringido) | `app/core/seguridad.py` (`requiere_rol`), menús por rol en `app/templates/parciales/` | `tests/test_web.py` |
| F-04 | Autoconsulta del miembro | `app/routers/cuenta.py`, `app/templates/cuenta/estado.html` | `tests/test_web.py::test_miembro_no_accede_a_modulos_de_gestion` |
| F-05 | Cambio de categoría con historial | `app/services/membresias.py` (`cambiar_categoria`), `app/repositories/miembro.py` | `tests/test_membresias.py::test_cambio_de_categoria_registra_historial_y_ajusta_cuota` |
| F-06 | Catálogo de cuotas | `app/models/membresia.py`, `app/seed.py`, `app/routers/membresias.py` | `tests/test_membresias.py::test_catalogo_de_cuotas_rn01` |
| F-07 | Activación con pago inicial | `app/services/activacion.py`, `app/services/pagos.py` | `tests/test_activacion.py`, `tests/test_integracion_activacion.py` |
| F-08 | Registro de pagos | `app/services/pagos.py` (`registrar_pago`), `app/routers/pagos.py` | `tests/test_integracion_pago.py` |
| F-09 | Exenciones (becado, invitado/influencer, retirado) | `app/services/membresias.py` (`marcar_exencion`), `app/models/miembro.py` | `tests/test_membresias.py::test_exencion_marca_cuotas_y_excluye_del_cobro` |
| F-10 | Ciclo mensual y corte al día 5 | `app/services/membresias.py` (`generar_cuotas_del_periodo`), `app/services/pagos.py` (`periodo_de_cobro`) | `tests/test_corte_dia5.py`, `tests/test_membresias.py` |
| F-11 | Estado de cuenta y mora | `app/services/morosidad.py`, `app/routers/cuenta.py` | `tests/test_morosidad.py`, `tests/test_web.py` |
| F-12 | Pago personalizado multimes/multiaño | `app/services/pagos.py`, `app/schemas/pago.py`, `app/routers/pagos.py` | `tests/test_imputacion.py`, `tests/test_validaciones.py` |
| F-13 | Imputación deuda → meses → abono | `app/services/pagos.py` | `tests/test_imputacion.py`, `tests/test_abono.py` |
| F-14 | Observaciones del pago | `app/models/pago.py` (`Pago.observaciones`), `app/schemas/pago.py` | `tests/test_validaciones.py::test_monto_distinto_a_la_cuota_y_observaciones` |
| F-15 | Listado de ingresos con filtros | `app/services/finanzas.py` (`listar_ingresos`), `app/routers/pagos.py` | `tests/test_finanzas.py::test_filtros_de_ingresos_por_tipo_y_estado` |
| F-16 | Egresos con categoría base o personalizada | `app/services/finanzas.py`, `app/routers/finanzas.py` | `tests/test_finanzas.py::test_egreso_con_categoria_base_y_personalizada` |
| F-17 | Adquisición de activos con responsable | `app/services/finanzas.py` (`registrar_activo`) | `tests/test_finanzas.py::test_registro_de_activo_con_responsable` |
| F-18 | Gastos fijos operativos | `app/services/finanzas.py` (`registrar_gasto_fijo`) | `tests/test_finanzas.py::test_registro_de_gasto_fijo` |
| F-19 | Reporte consolidado por periodo | `app/services/reportes.py`, `app/routers/reportes.py` | `tests/test_finanzas.py::test_reporte_consolidado_suma_movimientos` |
| F-20 | Exportación de reportes | `app/services/exportacion.py` (XLSX), `app/routers/reportes.py` | `tests/test_reportes.py`, `tests/test_web.py` |
| F-21 | Informe calendario mensual por miembro y PDF | `app/services/reportes.py`, `app/services/exportacion.py` | `tests/test_reportes.py`, `tests/test_web.py::test_descarga_del_informe_pdf` |
| F-22 | Clasificación de morosidad por colores | `app/services/morosidad.py`, `app/templates/parciales/macros.html` | `tests/test_morosidad.py` |
| F-23 | Avisos de morosidad manuales y plantilla | `app/services/correo.py`, `app/routers/morosidad.py`, `app/seed.py` | `tests/test_correo.py` |
| F-24 | Negociación de deuda | `app/services/negociacion.py`, `app/routers/negociaciones.py` | `tests/test_negociacion.py` |
| F-25 | Compras del club y cargos separados | `app/services/compras.py`, `app/routers/compras.py` | `tests/test_integracion_compras.py` |
| F-26 | Cuenta bancaria y medios de pago | `app/models/configuracion.py`, `app/models/pago.py` (`MEDIOS_PAGO`), `app/seed.py` | `tests/test_correo.py`, `tests/test_validaciones.py` |
| F-27 | Montos en CLP sin decimales | `app/core/formato.py`, filtros Jinja | `tests/test_formato.py` |
| F-28 | Landing page integrada | `app/routers/landing.py`, `app/templates/landing/index.html` | `tests/test_web.py::test_landing_publica` |
| F-29 | Identidad visual Rojo/Negro/Blanco | `tailwind.config.js`, `app/templates/base.html` | Revisión visual en landing y panel (CA-18); clases de marca en plantillas |

## 2. Reglas de negocio (RN)

| RN | Regla | Implementación / evidencia |
| :-- | :-- | :-- |
| RN-01 | Montos fijos 5.000 / 5.000 / 15.000 | `app/seed.py`, `app/models/membresia.py`; `tests/test_membresias.py::test_catalogo_de_cuotas_rn01` |
| RN-02 | Activación con Matrícula + cuota de la categoría (Matrícula omitida para matriculados) | `app/services/activacion.py`, `app/services/pagos.py`; `tests/test_activacion.py` |
| RN-03 | Corte al día 5 | `app/services/pagos.py::periodo_de_cobro`; `tests/test_corte_dia5.py` |
| RN-04 | Mora y acceso de consulta | `app/services/morosidad.py`, `app/routers/cuenta.py`; `tests/test_morosidad.py`, `tests/test_web.py` |
| RN-05 | Exención automática de cobros y avisos | `app/services/membresias.py`; `tests/test_membresias.py` |
| RN-06 | Aislamiento de la información del miembro | `app/core/seguridad.py`, `app/routers/cuenta.py`; `tests/test_web.py` |
| RN-07 | Admin y Tesorero con permisos iguales | `app/core/seguridad.py` (`ROLES_GESTION`); `tests/test_web.py` |
| RN-08 | Unicidad de pago por ciclo | `app/services/pagos.py::_validar_ciclos_no_duplicados`; `tests/test_integracion_pago.py::test_rechaza_segundo_pago_del_mismo_ciclo` |
| RN-09 | Monto libre | `app/services/pagos.py::validar_pago`; `tests/test_validaciones.py` |
| RN-10 | Categorías base y personalizadas | `app/models/finanzas.py`, `app/services/finanzas.py`; `tests/test_finanzas.py` |
| RN-11 | Correo como identificador único | `app/models/miembro.py`; `tests/test_web.py::test_alta_rechaza_correo_duplicado` |
| RN-12 | Recurrencia mensual de cuotas y gastos fijos | `app/services/membresias.py`, `app/services/finanzas.py`; `tests/test_membresias.py`, `tests/test_finanzas.py` |
| RN-13 | Avisos manuales, sin correo automático | `app/services/correo.py`, `app/routers/morosidad.py`; `tests/test_correo.py` |
| RN-14 | Fecha de ingreso editable (por defecto, fecha de alta) | `app/services/membresias.py::crear_miembro`, `app/repositories/miembro.py`; `tests/test_e2e_mvp.py`, `tests/test_web.py` |
| RN-15 | Trazabilidad de ingresos y egresos | Campos `fecha`, `monto`, `miembro_id`, `categoria_egreso_id` en `app/models/pago.py` y `app/models/finanzas.py`; reportes en `app/services/reportes.py` |
| RN-16 | Español correcto, UTF-8, tildes y ñ | Plantillas y mensajes en `app/templates/` y `app/services/`; revisión de copy de `specs/UAT.md` (CA-19) |
| RN-17 | Orden de imputación | `app/services/pagos.py::registrar_pago`; `tests/test_imputacion.py` |
| RN-18 | Abono automático a la siguiente cuota | `app/services/pagos.py` (`_aplicar_abono`, `aplicar_abonos_disponibles`); `tests/test_abono.py` |
| RN-19 | Solo transferencia o efectivo excepcional | `app/models/pago.py` (`MEDIOS_PAGO`), `app/services/pagos.py`; `tests/test_validaciones.py` |
| RN-20 | Sin impuestos | No existe lógica de impuestos/retenciones: `Pago.monto_clp` se registra y reporta íntegro (`app/models/pago.py`, `app/services/reportes.py`; `tests/test_reportes.py`) |
| RN-21 | Colores verde/naranjo/rojo | `app/services/morosidad.py`; `tests/test_morosidad.py` |
| RN-22 | Negociación solo > 6 meses y % editable | `app/services/negociacion.py`; `tests/test_negociacion.py` |
| RN-23 | Cargo de compra separado de la mora | `app/services/compras.py`; `tests/test_integracion_compras.py` |
| RN-24 | CLP con punto de miles y sin decimales | `app/core/formato.py`; `tests/test_formato.py` |
| RN-25 | Cambio de categoría con historial y ajuste | `app/services/membresias.py`; `tests/test_membresias.py` |
| RN-26 | Datos de la cuenta en plataforma y plantilla | `app/models/configuracion.py`, `app/seed.py`, `app/services/correo.py`; `tests/test_correo.py` |
| RN-27 | Cobro de matrícula desde 01/09/2025 y exclusión de matriculados | `app/services/activacion.py` (`debe_cobrar_matricula`); `tests/test_activacion.py` |

## 3. Criterios de aceptación (CA)

| CA | Criterio (resumen) | Estado | Evidencia |
| :-- | :-- | :-- | :-- |
| CA-01 | Pago inicial completo activa; parcial queda pendiente | ✅ Automatizado | `tests/test_activacion.py`, `tests/test_integracion_activacion.py` |
| CA-02 | Catálogo 5.000 / 5.000 / 15.000 | ✅ Automatizado | `tests/test_membresias.py::test_catalogo_de_cuotas_rn01` |
| CA-03 | Exención sin cobros ni avisos | ✅ Automatizado | `tests/test_membresias.py::test_exencion_marca_cuotas_y_excluye_del_cobro` |
| CA-04 | Pago posterior al día 5 al ciclo siguiente | ✅ Automatizado | `tests/test_corte_dia5.py` |
| CA-05 | Mes cerrado impago genera deuda visible | ✅ Automatizado | `tests/test_morosidad.py`, `tests/test_web.py` |
| CA-06 | Ingresos filtrables por tipo y estado | ✅ Automatizado | `tests/test_finanzas.py::test_filtros_de_ingresos_por_tipo_y_estado` |
| CA-07 | Egreso con categoría base o personalizada | ✅ Automatizado | `tests/test_finanzas.py::test_egreso_con_categoria_base_y_personalizada` |
| CA-08 | Activo con costo y responsable | ✅ Automatizado | `tests/test_finanzas.py::test_registro_de_activo_con_responsable` |
| CA-09 | Gasto fijo como egreso recurrente | ✅ Automatizado | `tests/test_finanzas.py::test_registro_de_gasto_fijo` |
| CA-10 | Reporte consolidado: ingresos − egresos | ✅ Automatizado | `tests/test_finanzas.py::test_reporte_consolidado_suma_movimientos` |
| CA-11 | XLSX con los mismos totales | ✅ Automatizado | `tests/test_reportes.py`, `tests/test_web.py` |
| CA-12 | El miembro solo ve su información | ✅ Automatizado | `tests/test_web.py::test_miembro_no_accede_a_modulos_de_gestion` |
| CA-13 | Admin y Tesorero con las mismas acciones | ✅ Automatizado | `tests/test_web.py::test_tesorero_tiene_las_mismas_acciones_que_admin` |
| CA-14 | Informe calendario y PDF | ✅ Automatizado | `tests/test_reportes.py`, `tests/test_web.py::test_descarga_del_informe_pdf` |
| CA-15 | Aviso al Tesorero y `mailto:` sin envío automático | ✅ Automatizado | `tests/test_correo.py::test_enlace_mailto_contiene_asunto_y_cuerpo` |
| CA-16 | Ficha ampliada obligatoria y correo único | ✅ Automatizado | `tests/test_web.py` (alta y duplicado) |
| CA-17 | Monto distinto al de la cuota se acepta | ✅ Automatizado | `tests/test_validaciones.py::test_monto_distinto_a_la_cuota_y_observaciones` |
| CA-18 | Landing con secciones y paleta | ✅ Automatizado + manual | `tests/test_web.py::test_landing_publica`; revisión responsive |
| CA-19 | Textos en español correcto | 🕵️ Manual | Revisión de copy en plantillas; ver `specs/UAT.md` |
| CA-20 | Se impide duplicar el pago de un ciclo | ✅ Automatizado | `tests/test_integracion_pago.py::test_rechaza_segundo_pago_del_mismo_ciclo` |
| CA-21 | Datos vacíos/inválidos no se guardan | ✅ Automatizado | `tests/test_web.py`, `tests/test_validaciones.py` |
| CA-22 | Imputación deuda antigua → mes/año → abono | ✅ Automatizado | `tests/test_imputacion.py` |
| CA-23 | Abono aplicado automáticamente | ✅ Automatizado | `tests/test_abono.py` |
| CA-24 | Colores verde/naranjo/rojo | ✅ Automatizado | `tests/test_morosidad.py` |
| CA-25 | Negociación > 6 meses con % editable | ✅ Automatizado | `tests/test_negociacion.py` |
| CA-26 | CLP con punto de miles y sin decimales | ✅ Automatizado | `tests/test_formato.py` |
| CA-27 | Cargo de compra separado sin alterar mora | ✅ Automatizado | `tests/test_integracion_compras.py` |
| CA-28 | Solo transferencia o efectivo excepcional | ✅ Automatizado | `tests/test_validaciones.py` |
| CA-29 | Cambio de categoría con historial y ajuste | ✅ Automatizado | `tests/test_membresias.py` |
| CA-30 | Datos de cuenta en plataforma y plantilla | ✅ Automatizado | `tests/test_correo.py` |
| CA-31 | Observaciones del pago registradas | ✅ Automatizado | `tests/test_validaciones.py::test_monto_distinto_a_la_cuota_y_observaciones` |

## 4. Recorrido end-to-end (T10.5)

`tests/test_e2e_mvp.py` recorre en una sola prueba:

1. Alta de miembro y obligación inicial.
2. Pago parcial y pago completo con activación.
3. Generación de cuotas cerradas y cálculo de mora roja (> 3 meses).
4. Negociación (> 6 meses), aceptación, efecto en el color y pago.
5. Egreso, activo, gasto fijo y categoría personalizada.
6. Compra con cargo separado y saldo sin alterar la mora.
7. Reporte consolidado, exportación XLSX e informe PDF.
8. Landing pública.
9. Alta sin fecha explícita (fecha de incorporación automática).

## 5. Límites y verificaciones manuales

- **CA-18 (responsive):** revisar landing y panel en escritorio y móvil.
- **CA-19 (copy):** leer textos visibles buscando tildes, ñ y redacción.
- **CA-15 (`mailto:`):** probar en un equipo con cliente de correo configurado.
- **CA-11 / CA-14 (descargas):** abrir los archivos XLSX/PDF descargados con
  Excel y un lector de PDF.

No se detectaron funcionalidades `F-` ni reglas `RN-` sin implementación. Los
puntos anteriores son verificaciones de presentación/entorno, no faltantes del
MVP.
