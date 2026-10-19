# Checklist UAT — Criterios de aceptación (T8.11)

> **Alcance:** verificación de **CA-01 … CA-31** de `specs/SPECS.md` §10.
> **Fecha:** 19-10-2026.
> **Entorno:** Windows + Python del `venv`; suite sobre SQLite en memoria
> (opcionalmente MySQL con `TEST_DATABASE_URL`).
> **Comando:** `.\venv\Scripts\python.exe -m pytest`
> **Resultado:** **131 pruebas aprobadas** (incluye las pruebas de optimización de la Fase 9) y `ruff check app tests` sin hallazgos.

## Matriz de cobertura

| CA | Criterio (resumen) | Estado | Evidencia automatizada |
| :--- | :--- | :--- | :--- |
| CA-01 | Pago inicial completo activa; parcial queda pendiente | ✅ Automatizado | `tests/test_activacion.py`, `tests/test_integracion_activacion.py` |
| CA-02 | Catálogo 5.000 / 5.000 / 15.000 | ✅ Automatizado | `tests/test_membresias.py::test_catalogo_de_cuotas_rn01` |
| CA-03 | Exención sin cobros ni avisos; cuota exenta | ✅ Automatizado | `tests/test_membresias.py::test_exencion_marca_cuotas_y_excluye_del_cobro` |
| CA-04 | Pago posterior al día 5 pasa al ciclo siguiente | ✅ Automatizado | `tests/test_corte_dia5.py` |
| CA-05 | Mes cerrado impago genera deuda visible para el miembro | ✅ Automatizado | `tests/test_morosidad.py`, `tests/test_web.py::test_miembro_ve_su_deuda_en_el_estado_de_cuenta` |
| CA-06 | Ingresos filtrables por tipo de cuota y estado | ✅ Automatizado | `tests/test_finanzas.py::test_filtros_de_ingresos_por_tipo_y_estado` |
| CA-07 | Egreso con categoría base o personalizada | ✅ Automatizado | `tests/test_finanzas.py::test_egreso_con_categoria_base_y_personalizada` |
| CA-08 | Activo con costo y miembro responsable | ✅ Automatizado | `tests/test_finanzas.py::test_registro_de_activo_con_responsable` |
| CA-09 | Gasto fijo reflejado como egreso recurrente | ✅ Automatizado | `tests/test_finanzas.py::test_registro_de_gasto_fijo` |
| CA-10 | Reporte consolidado: ingresos − egresos | ✅ Automatizado | `tests/test_finanzas.py::test_reporte_consolidado_suma_movimientos` |
| CA-11 | Exportación XLSX con los mismos totales | ✅ Automatizado | `tests/test_reportes.py::test_exportacion_xlsx_contiene_los_mismos_totales`, `tests/test_web.py::test_descarga_del_reporte_xlsx` |
| CA-12 | El miembro solo ve su información | ✅ Automatizado | `tests/test_web.py::test_miembro_no_accede_a_modulos_de_gestion` |
| CA-13 | Admin/Tesorero con las mismas acciones; Miembro restringido | ✅ Automatizado | `tests/test_web.py::test_tesorero_tiene_las_mismas_acciones_que_admin` |
| CA-14 | Informe calendario con estado y monto; exportable a PDF | ✅ Automatizado | `tests/test_reportes.py`, `tests/test_web.py::test_descarga_del_informe_pdf` |
| CA-15 | Aviso al Tesorero con plantilla y `mailto:`, sin envío automático | ✅ Automatizado | `tests/test_correo.py::test_enlace_mailto_contiene_asunto_y_cuerpo` |
| CA-16 | Ficha ampliada obligatoria y correo único | ✅ Automatizado | `tests/test_web.py::test_alta_rechaza_correo_duplicado`, `tests/test_web.py::test_alta_con_datos_invalidos_no_guarda` |
| CA-17 | Monto distinto al de la cuota se acepta | ✅ Automatizado | `tests/test_validaciones.py::test_monto_distinto_a_la_cuota_y_observaciones` |
| CA-18 | Landing con las secciones y paleta definida | ✅ Automatizado + manual | `tests/test_web.py::test_landing_publica`; revisión responsive en navegador (abajo) |
| CA-19 | Textos en español correcto | 🕵️ Manual | Revisión de copy en plantillas (abajo) |
| CA-20 | Se impide duplicar el pago de un ciclo | ✅ Automatizado | `tests/test_integracion_pago.py::test_rechaza_segundo_pago_del_mismo_ciclo` |
| CA-21 | Datos vacíos/inválidos no se guardan y se explican | ✅ Automatizado | `tests/test_web.py::test_alta_con_datos_invalidos_no_guarda`, `tests/test_validaciones.py` |
| CA-22 | Imputación deuda antigua → mes/año → abono | ✅ Automatizado | `tests/test_imputacion.py` |
| CA-23 | Abono aplicado automáticamente a la siguiente cuota | ✅ Automatizado | `tests/test_abono.py` |
| CA-24 | Colores verde / naranjo / rojo por meses de deuda | ✅ Automatizado | `tests/test_morosidad.py` |
| CA-25 | Negociación para morosos > 6 meses con % editable | ✅ Automatizado | `tests/test_negociacion.py` |
| CA-26 | Montos CLP con punto de miles y sin decimales | ✅ Automatizado | `tests/test_formato.py` |
| CA-27 | Cargo de compra separado que no altera la morosidad | ✅ Automatizado | `tests/test_integracion_compras.py` |
| CA-28 | Solo transferencia (principal) o efectivo (excepcional) | ✅ Automatizado | `tests/test_validaciones.py` |
| CA-29 | Cambio de categoría con historial y ajuste de cuota | ✅ Automatizado | `tests/test_membresias.py::test_cambio_de_categoria_registra_historial_y_ajusta_cuota` |
| CA-30 | Datos de la cuenta en la plataforma y en la plantilla | ✅ Automatizado | `tests/test_correo.py::test_plantilla_rellena_datos_del_alumno_y_cuenta` |
| CA-31 | Observaciones del pago registradas | ✅ Automatizado | `tests/test_validaciones.py::test_monto_distinto_a_la_cuota_y_observaciones` |

## Verificaciones manuales recomendadas antes de la demo

No bloquean el MVP; se registran para la revisión final con el club.

1. **CA-18 · Responsive:** abrir `http://127.0.0.1:8000` en escritorio y en
   vista móvil; comprobar menú, acordeón y modales de la landing.
2. **CA-19 · Copy:** leer landing, panel y mensajes de error buscando tildes,
   ñ y redacción; corregir cualquier texto detectado.
3. **CA-15 · `mailto:`:** pulsar el enlace de aviso en un equipo con cliente de
   correo configurado y confirmar que asunto y cuerpo se abren completos.
4. **CA-11 / CA-14 · Descargas reales:** descargar el XLSX y el PDF desde el
   navegador y abrirlos con Excel/Lector PDF (el contenido ya está cubierto por
   pruebas de servicio y de endpoint).

## Notas de ejecución

- La suite usa **SQLite en memoria** por defecto para no depender de XAMPP.
- Para correr contra MySQL:

  ```powershell
  $env:TEST_DATABASE_URL = "mysql+pymysql://root:@localhost:3306/osorno_runners_test"
  .\venv\Scripts\python.exe -m pytest
  ```

- `tests/conftest.py` crea y destruye el esquema por prueba; no usar la base de
  desarrollo en `TEST_DATABASE_URL`.
