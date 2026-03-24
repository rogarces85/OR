# OSORNO RUNNERS - Sistema de Cuotas (React)

Aplicacion web responsiva para:

- cargar base historica desde `Ejercicio_Cuotas.xlsx`
- registrar pagos manuales
- importar cartola bancaria (`A` y `C`)
- clasificar movimientos en `Cuota`, `Otro ingreso` o `Egreso`
- generar detalle de meses pagados desde un periodo inicial (`YYYY-MM`)

## Requisitos

- Node.js 18+
- npm

## Instalacion

```bash
npm install
```

## Ejecutar en desarrollo

```bash
npm run dev
```

## Build produccion

```bash
npm run build
```

## Flujo recomendado

1. Ir a `Socios y base` y cargar `Ejercicio_Cuotas.xlsx`.
2. Ir a `Importar banco` y cargar la cartola del banco.
3. Revisar cada movimiento pendiente (categoria, meses, periodo).
4. Procesar filas:
   - `Cuota`: crea pago del socio.
   - `Otro ingreso`: guarda ingreso no-cuota.
   - `Egreso`: guarda salida de dinero.
5. Revisar resultados en `Historial pagos`.

## Persistencia

Los datos quedan guardados en `localStorage` del navegador (clave `osorno-runners-app-v1`).

## Base de datos MySQL creada

Conexion usada:

- host: `localhost`
- puerto: `3306`
- usuario: `root`
- password: `""` (vacia)

Schema aplicado: `database/osorno_runners_schema.sql`

Base creada: `osorno_runners`

Tablas:

- `socios`
- `pagos`
- `pago_meses`
- `movimientos_bancarios`
- `otros_ingresos`
- `egresos`
- vista `vw_saldos`

## Backend PHP (API)

Se agrego API en `api/` para que toda la operacion quede en MySQL:

- `api/bootstrap.php`
- `api/import_base.php`
- `api/import_estado_cuotas.php`
- `api/import_movimientos.php`
- `api/create_pago.php`
- `api/procesar_movimiento.php`

La app React usa por defecto:

- `http://localhost/Cuotas_OR/osorno-runners-app/api`

Si necesitas otra URL, configura `VITE_API_BASE`.

## Carga inicial de socios 2025 y 2026

Script generado y ejecutado:

- `scripts/import_socios_2025_2026.py`
- `database/import_socios_2025_2026.sql`

Resultado actual en BD:

- 54 socios cargados entre 2025 y 2026.

## Modelo actualizado (socios vs pagos)

- `socios` ahora guarda solo: `rut`, `nombre`, `anio`, `sexo`, `estado`.
- `pagos` guarda el contexto del cobro: `tipo_cuota`, `valor_cuota`, `meses_cantidad`, `meses_detalle`, etc.
- Tipos de cuota operativos: `ACTIVO`, `MEMBRESIA`, `BECADO`, `OTRO`.
- Regla aplicada: si `tipo_cuota = BECADO`, no se permite registrar cobro de cuota.
- Se agrego modulo `Conflictos` para resolver cuotas sin socio detectado (RUT) antes de procesar.
- En `Conflictos` se agrego filtro por `RUT` para revision rapida.

## UI modernizada

- Se integro `TailwindCSS` en la app (config en `tailwind.config.js` y `postcss.config.js`).
- Dashboard renovado con visual mas moderno, tarjetas operativas y foco en pendientes/conflictos.
- Se agrego grafico de tendencia mensual usando `Recharts`.
- Se agrego modulo `Estado anual` para leer y guardar en MySQL el archivo `Estado de cuotas OR 2024.xlsx`.

Migration aplicada en BD:

- `database/migration_2026_03_modelo_socios_pagos.sql`
- `database/migration_2026_03_estado_cuotas.sql`
