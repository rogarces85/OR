import { useEffect, useMemo, useState } from 'react'
import * as XLSX from 'xlsx'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import './App.css'

const DEFAULT_CUOTA = 15000
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost/Cuotas_OR/osorno-runners-app/api'
const CUOTA_POR_TIPO = { ACTIVO: 15000, MEMBRESIA: 5000, BECADO: 0, OTRO: 15000 }

const normalizeHeader = (value) =>
  String(value ?? '')
    .toUpperCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^A-Z0-9]/g, '')

const normalizeRut = (value) => {
  const cleaned = String(value ?? '')
    .toUpperCase()
    .replace(/[^0-9K]/g, '')
    .replace(/\.0$/, '')
  return cleaned.replace(/^0+/, '')
}

const normalizeTipoCuota = (value) => {
  const tipo = String(value || '').toUpperCase().trim()
  return CUOTA_POR_TIPO[tipo] !== undefined ? tipo : 'ACTIVO'
}

const cuotaPorTipo = (tipoCuota) => CUOTA_POR_TIPO[normalizeTipoCuota(tipoCuota)] ?? DEFAULT_CUOTA

const parseNumber = (value) => {
  if (typeof value === 'number') return Number.isFinite(value) ? value : 0
  const cleaned = String(value ?? '').replace(/\./g, '').replace(',', '.').trim()
  const parsed = Number(cleaned)
  return Number.isFinite(parsed) ? parsed : 0
}

const formatMoney = (value) =>
  new Intl.NumberFormat('es-CL', {
    style: 'currency',
    currency: 'CLP',
    maximumFractionDigits: 0,
  }).format(Number(value || 0))

const toIsoDate = (value) => {
  if (!value) return ''
  if (value instanceof Date && !Number.isNaN(value.getTime())) return value.toISOString().slice(0, 10)
  if (typeof value === 'number') {
    const parsed = XLSX.SSF.parse_date_code(value)
    if (parsed) {
      const d = new Date(Date.UTC(parsed.y, parsed.m - 1, parsed.d))
      return d.toISOString().slice(0, 10)
    }
  }
  const text = String(value).trim()
  const dmY = text.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/)
  if (dmY) {
    const [, d, m, y] = dmY
    return `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`
  }
  const guess = new Date(text)
  if (!Number.isNaN(guess.getTime())) return guess.toISOString().slice(0, 10)
  return ''
}

const monthCode = (date = new Date()) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`

const buildPeriodWindow = (dateString, back = 2, forward = 10) => {
  const base = dateString ? new Date(`${dateString}T00:00:00`) : new Date()
  if (Number.isNaN(base.getTime())) return [monthCode()]
  const periods = []
  for (let i = -back; i <= forward; i += 1) {
    const d = new Date(base.getFullYear(), base.getMonth() + i, 1)
    periods.push(monthCode(d))
  }
  return periods
}

const resolveRowGetter = (row) => {
  const map = {}
  Object.keys(row || {}).forEach((key) => {
    map[normalizeHeader(key)] = row[key]
  })
  return (...keys) => {
    for (const key of keys) {
      if (map[key] !== undefined && map[key] !== null && map[key] !== '') return map[key]
    }
    return ''
  }
}

const signature = (item) => `${item.fecha}|${Number(item.monto)}|${item.descripcion}|${item.cargoAbono}`

const apiRequest = async (path, options = {}) => {
  const response = await fetch(`${API_BASE}/${path}`, options)
  const payload = await response.json()
  if (!response.ok || !payload.ok) throw new Error(payload.error || 'Error de API')
  return payload
}

function App() {
  const [tab, setTab] = useState('dashboard')
  const [socios, setSocios] = useState([])
  const [pagos, setPagos] = useState([])
  const [movimientos, setMovimientos] = useState([])
  const [otrosIngresos, setOtrosIngresos] = useState([])
  const [egresos, setEgresos] = useState([])
  const [cartolaDraft, setCartolaDraft] = useState([])
  const [resolucionPendientes, setResolucionPendientes] = useState({})
  const [filtroConflictoRut, setFiltroConflictoRut] = useState('')
  const [mensaje, setMensaje] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const [manualForm, setManualForm] = useState({
    rut: '',
    fechaPago: new Date().toISOString().slice(0, 10),
    totalPago: '',
    tipoCuota: 'ACTIVO',
    valorCuota: DEFAULT_CUOTA,
    periodos: [monthCode()],
    observacion: '',
  })

  const refreshData = async () => {
    const payload = await apiRequest('bootstrap.php')
    const data = payload.data || {}
    setSocios(data.socios || [])
    setPagos(data.pagos || [])
    setMovimientos(data.movimientos || [])
    setOtrosIngresos(data.otrosIngresos || [])
    setEgresos(data.egresos || [])
    return data
  }

  useEffect(() => {
    setIsLoading(true)
    refreshData()
      .catch((error) => setMensaje(error.message))
      .finally(() => setIsLoading(false))
  }, [])

  const socioMap = useMemo(() => {
    const map = new Map()
    socios.forEach((socio) => map.set(socio.rut, socio))
    return map
  }, [socios])

  const pendientes = useMemo(() => movimientos.filter((m) => m.estado === 'pendiente'), [movimientos])
  const pagosOrdenados = useMemo(() => [...pagos].sort((a, b) => (a.fechaPago < b.fechaPago ? 1 : -1)), [pagos])
  const draftConflictos = useMemo(
    () => cartolaDraft.filter((m) => m.categoria === 'Cuota' && (!m.rut || !m.socioNombre)),
    [cartolaDraft],
  )
  const pendientesConflictos = useMemo(
    () => pendientes.filter((m) => m.categoria === 'Cuota' && (!m.rut || !m.socioNombre)),
    [pendientes],
  )
  const filtroConfRutNorm = useMemo(() => normalizeRut(filtroConflictoRut), [filtroConflictoRut])
  const draftConflictosFiltrados = useMemo(() => {
    if (!filtroConfRutNorm) return draftConflictos
    return draftConflictos.filter((m) => normalizeRut(m.rut || '').includes(filtroConfRutNorm))
  }, [draftConflictos, filtroConfRutNorm])
  const pendientesConflictosFiltrados = useMemo(() => {
    if (!filtroConfRutNorm) return pendientesConflictos
    return pendientesConflictos.filter((m) => normalizeRut(m.rut || '').includes(filtroConfRutNorm))
  }, [pendientesConflictos, filtroConfRutNorm])

  const seleccionarSocio = (rut) => {
    const socio = socioMap.get(rut)
    const tipoCuota = normalizeTipoCuota(socio?.estado || 'ACTIVO')
    setManualForm((prev) => ({ ...prev, rut, tipoCuota, valorCuota: cuotaPorTipo(tipoCuota) }))
  }

  const toggleManualPeriodo = (periodo) => {
    setManualForm((prev) => {
      const has = prev.periodos.includes(periodo)
      const next = has ? prev.periodos.filter((p) => p !== periodo) : [...prev.periodos, periodo]
      return { ...prev, periodos: next.sort() }
    })
  }

  const importarSociosYPagos = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    try {
      setIsLoading(true)
      const data = await file.arrayBuffer()
      const workbook = XLSX.read(data, { type: 'array' })
      const sheet = workbook.Sheets.BD_Pagos || workbook.Sheets[workbook.SheetNames[0]]
      const rows = XLSX.utils.sheet_to_json(sheet, { defval: '' })

      const socioByRut = new Map()
      const nuevosPagos = []

      rows.forEach((row) => {
        const get = resolveRowGetter(row)
        const rut = normalizeRut(get('RUT'))
        const nombre = String(get('INTEGRANTE', 'NOMBREYAPELLIDO', 'NOMBRE')).trim()
        if (!rut || !nombre) return

        const socio = {
          rut,
          nombre,
          anio: Number(get('ANO', 'AO')) || new Date().getFullYear(),
          sexo: String(get('SEXO')).trim(),
          estado: String(get('ESTADO')).trim(),
          actualizado: toIsoDate(get('FECHAPAGO')),
        }

        const existing = socioByRut.get(rut)
        if (!existing || (socio.actualizado && socio.actualizado > existing.actualizado)) socioByRut.set(rut, socio)

        const fechaPago = toIsoDate(get('FECHAPAGO'))
        const totalPago = parseNumber(get('TOTALPAGO'))
        if (!fechaPago || !totalPago) return

        const tipoCuota = normalizeTipoCuota(String(get('ESTADO')).trim())
        nuevosPagos.push({
          rut,
          fechaPago,
          totalPago,
          valorCuota: parseNumber(get('VALORCUOTA')) || cuotaPorTipo(tipoCuota),
          tipoCuota,
          mesesCantidad: Math.max(1, Number(get('MESES')) || 1),
          mesesDetalle: String(get('MESESDEPAGO')).trim(),
          observacion: String(get('OBSERVACION')).trim(),
          origen: 'historico',
        })
      })

      const response = await apiRequest('import_base.php', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ socios: Array.from(socioByRut.values()), pagos: nuevosPagos }),
      })

      await refreshData()
      setMensaje(`Importacion lista: ${response.sociosProcesados} socios procesados y ${response.pagosNuevos} pagos nuevos en BD.`)
    } catch (error) {
      setMensaje(error.message)
    } finally {
      setIsLoading(false)
      event.target.value = ''
    }
  }

  const cargarCartolaARevision = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    try {
      const data = await file.arrayBuffer()
      const workbook = XLSX.read(data, { type: 'array' })
      const sheet = workbook.Sheets[workbook.SheetNames[0]]
      const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' })
      const headerIndex = rows.findIndex((row) => {
        const headers = row.map(normalizeHeader)
        return headers.includes('MONTO') && headers.includes('FECHA') && headers.includes('CARGOABONO')
      })
      if (headerIndex < 0) {
        setMensaje('No se encontro la tabla de movimientos. Revisa el formato del archivo.')
        return
      }

      const keywordsOtros = /(camiseta|rifa|evento|aporte|inscrip|polera|donaci)/i
      const draft = rows.slice(headerIndex + 1).reduce((acc, row) => {
        const monto = parseNumber(row[0])
        const descripcion = String(row[1] || '').trim()
        const fecha = toIsoDate(row[2])
        const cargoAbono = String(row[6] || '').trim().toUpperCase()
        if (!monto || !fecha || !['A', 'C'].includes(cargoAbono)) return acc

        const rut = normalizeRut(descripcion.match(/(0?\d{7,8}[0-9Kk])/)?.[1] || '')
        const socio = rut ? socioMap.get(rut) : null
        const categoria = cargoAbono === 'C' ? 'Egreso' : keywordsOtros.test(descripcion) ? 'Otro ingreso' : 'Cuota'
        const tipoCuota = normalizeTipoCuota(socio?.estado || 'ACTIVO')
        const valorCuota = cuotaPorTipo(tipoCuota)
        const estimado = categoria === 'Cuota' && valorCuota > 0 ? Math.max(1, Math.floor(Math.abs(monto) / valorCuota)) : 1
        const periodOptions = buildPeriodWindow(fecha)
        const firstIndex = periodOptions.findIndex((p) => p === monthCode(new Date(`${fecha}T00:00:00`)))
        const start = firstIndex >= 0 ? firstIndex : 0
        const periodos = categoryDefaultPeriods(periodOptions, start, estimado)

        acc.push({
          id: `TMP-${Date.now()}-${Math.floor(Math.random() * 100000)}-${acc.length}`,
          selected: true,
          fecha,
          monto,
          descripcion,
          cargoAbono,
          rut,
          socioNombre: socio?.nombre || '',
          categoria,
          tipoCuota,
          valorCuota,
          periodOptions,
          periodos,
        })
        return acc
      }, [])

      setCartolaDraft(draft)
      setTab('banco')
      setMensaje(`Cartola cargada en revision: ${draft.length} filas.`)
    } catch (error) {
      setMensaje(error.message)
    } finally {
      event.target.value = ''
    }
  }

  const actualizarDraft = (id, key, value) => {
    setCartolaDraft((prev) =>
      prev.map((item) => {
        if (item.id !== id) return item
        if (key === 'tipoCuota') {
          const tipo = normalizeTipoCuota(value)
          return { ...item, tipoCuota: tipo, valorCuota: cuotaPorTipo(tipo) }
        }
        return { ...item, [key]: value }
      }),
    )
  }

  const asignarSocioDraft = (id, rutInput) => {
    const rut = normalizeRut(rutInput)
    const socio = socioMap.get(rut)
    if (!socio) return
    const tipoCuota = normalizeTipoCuota(socio.estado || 'ACTIVO')
    setCartolaDraft((prev) =>
      prev.map((item) =>
        item.id === id
          ? {
              ...item,
              rut,
              socioNombre: socio.nombre,
              tipoCuota,
              valorCuota: cuotaPorTipo(tipoCuota),
              resolverSocio: `${socio.rut} - ${socio.nombre}`,
            }
          : item,
      ),
    )
  }

  const toggleDraftPeriodo = (id, periodo) => {
    setCartolaDraft((prev) =>
      prev.map((item) => {
        if (item.id !== id) return item
        const has = item.periodos.includes(periodo)
        const next = has ? item.periodos.filter((p) => p !== periodo) : [...item.periodos, periodo]
        return { ...item, periodos: next.sort() }
      }),
    )
  }

  const processDraft = async (singleId = null) => {
    const selected = cartolaDraft.filter((d) => d.selected && (!singleId || d.id === singleId))
    if (!selected.length) {
      setMensaje('No hay filas seleccionadas para procesar.')
      return
    }

    try {
      setIsLoading(true)
      await apiRequest('import_movimientos.php', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          movimientos: selected.map((s) => ({
            fecha: s.fecha,
            monto: s.monto,
            descripcion: s.descripcion,
            cargoAbono: s.cargoAbono,
            rut: s.rut,
            categoria: s.categoria,
            tipoCuota: s.tipoCuota,
            valorCuota: s.valorCuota,
            periodos: s.periodos,
          })),
        }),
      })

      const fresh = await refreshData()
      const pendingList = (fresh.movimientos || []).filter((m) => m.estado === 'pendiente')
      const bag = new Map()
      pendingList.forEach((m) => {
        const key = signature(m)
        if (!bag.has(key)) bag.set(key, [])
        bag.get(key).push(m)
      })

      const results = []
      for (const row of selected) {
        const key = signature(row)
        const list = bag.get(key) || []
        const mov = list.shift()
        if (!mov) {
          results.push({ rowId: row.id, status: 'ya_existia', message: `Movimiento ya existia: ${row.descripcion}` })
          continue
        }
        try {
          const res = await apiRequest('procesar_movimiento.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              id: mov.id,
              categoria: row.categoria,
              tipoCuota: row.tipoCuota,
              periodos: row.periodos,
              mesesCantidad: row.periodos.length || 1,
              periodoInicio: row.periodos[0] || monthCode(new Date(`${row.fecha}T00:00:00`)),
            }),
          })
          results.push({ rowId: row.id, status: res.status || 'ok', message: res.message || 'Procesado' })
        } catch (error) {
          results.push({ rowId: row.id, status: 'error', message: error.message })
        }
      }

      await refreshData()
      const guardados = results.filter((r) => ['pago_creado', 'otro_ingreso_creado', 'egreso_creado'].includes(r.status)).length
      const duplicados = results.filter((r) => ['duplicado_pago', 'ya_existia', 'ya_procesado'].includes(r.status)).length
      const errores = results.filter((r) => r.status === 'error').length

      const withError = new Set(results.filter((r) => r.status === 'error').map((r) => r.rowId))
      setCartolaDraft((prev) => prev.filter((d) => !(selected.some((s) => s.id === d.id) && !withError.has(d.id))))
      setMensaje(`Proceso cartola: guardados ${guardados}, existentes/duplicados ${duplicados}, errores ${errores}.`)
    } catch (error) {
      setMensaje(error.message)
    } finally {
      setIsLoading(false)
    }
  }

  const actualizarResolucionPendiente = (id, key, value) => {
    setResolucionPendientes((prev) => ({
      ...prev,
      [id]: {
        rut: prev[id]?.rut || '',
        categoria: prev[id]?.categoria || 'Cuota',
        tipoCuota: prev[id]?.tipoCuota || 'ACTIVO',
        ...prev[id],
        [key]: value,
      },
    }))
  }

  const guardarConflictoPendiente = async (item) => {
    const edit = resolucionPendientes[item.id] || {}
    const rut = normalizeRut(edit.rut || item.rut || '')
    if (!rut) {
      setMensaje('Debes ingresar un RUT valido para resolver conflicto pendiente.')
      return
    }
    const socio = socioMap.get(rut)
    if (!socio) {
      setMensaje('El RUT indicado no existe en la base de socios.')
      return
    }
    const categoria = edit.categoria || item.categoria || 'Cuota'
    const tipoCuota = normalizeTipoCuota(edit.tipoCuota || item.tipoCuota || socio.estado)
    try {
      setIsLoading(true)
      await apiRequest('update_movimiento.php', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: item.id,
          rut,
          categoria,
          tipoCuota,
          valorCuota: cuotaPorTipo(tipoCuota),
          mesesCantidad: Math.max(1, Number(item.mesesCantidad || 1)),
          periodoInicio: item.periodoInicio || monthCode(new Date(`${item.fecha}T00:00:00`)),
        }),
      })
      await refreshData()
      setMensaje(`Conflicto ${item.id} resuelto y guardado.`)
    } catch (error) {
      setMensaje(error.message)
    } finally {
      setIsLoading(false)
    }
  }

  const procesarPendienteBD = async (item) => {
    try {
      setIsLoading(true)
      await apiRequest('procesar_movimiento.php', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: item.id,
          categoria: item.categoria,
          tipoCuota: item.tipoCuota,
          mesesCantidad: item.mesesCantidad,
          periodoInicio: item.periodoInicio,
        }),
      })
      await refreshData()
      setMensaje(`Movimiento ${item.id} procesado.`)
    } catch (error) {
      setMensaje(error.message)
    } finally {
      setIsLoading(false)
    }
  }

  const submitManualPayment = async (event) => {
    event.preventDefault()
    if (manualForm.tipoCuota === 'BECADO') {
      setMensaje('Socio becado: no corresponde cobro de cuota.')
      return
    }
    if (!manualForm.periodos.length) {
      setMensaje('Debes seleccionar al menos un mes a pagar.')
      return
    }
    try {
      setIsLoading(true)
      await apiRequest('create_pago.php', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...manualForm,
          mesesCantidad: manualForm.periodos.length,
          periodoInicio: manualForm.periodos[0],
          periodos: manualForm.periodos,
          origen: 'manual',
        }),
      })
      await refreshData()
      setMensaje('Pago manual guardado en BD.')
    } catch (error) {
      setMensaje(error.message)
    } finally {
      setIsLoading(false)
    }
  }

  const totalPagos = pagos.reduce((acc, item) => acc + Number(item.totalPago || 0), 0)
  const totalAbonosPendientes = pendientes
    .filter((item) => item.cargoAbono === 'A')
    .reduce((acc, item) => acc + Math.abs(item.monto), 0)
  const totalOtrosIngresos = otrosIngresos.reduce((acc, item) => acc + Number(item.monto || 0), 0)
  const totalEgresos = egresos.reduce((acc, item) => acc + Number(item.monto || 0), 0)
  const saldoNeto = totalPagos + totalOtrosIngresos - totalEgresos
  const manualPeriodOptions = useMemo(() => buildPeriodWindow(manualForm.fechaPago, 3, 12), [manualForm.fechaPago])
  const dashboardSeries = useMemo(() => {
    const map = new Map()
    const add = (key, field, amount) => {
      if (!map.has(key)) map.set(key, { periodo: key, cuotas: 0, otros: 0, egresos: 0 })
      map.get(key)[field] += Number(amount || 0)
    }
    pagos.forEach((p) => {
      if (!p.fechaPago) return
      add(String(p.fechaPago).slice(0, 7), 'cuotas', Number(p.totalPago || 0))
    })
    otrosIngresos.forEach((i) => {
      if (!i.fecha) return
      add(String(i.fecha).slice(0, 7), 'otros', Number(i.monto || 0))
    })
    egresos.forEach((e) => {
      if (!e.fecha) return
      add(String(e.fecha).slice(0, 7), 'egresos', Number(e.monto || 0))
    })
    return [...map.values()]
      .sort((a, b) => a.periodo.localeCompare(b.periodo))
      .slice(-8)
      .map((row) => ({ ...row, neto: row.cuotas + row.otros - row.egresos }))
  }, [egresos, otrosIngresos, pagos])

  return (
    <main className="app-shell mx-auto min-h-screen w-[96vw] max-w-[1280px] py-6">
      <header className="topbar border border-zinc-200 bg-white/90 backdrop-blur">
        <div>
          <p className="eyebrow">CLUB DEPORTIVO</p>
          <h1>OSORNO RUNNERS</h1>
          <p className="subtitle">Gestion de socios, cuotas por mes e importacion controlada de cartolas bancarias.</p>
        </div>
        <div className="stats-grid">
          <article><span>Socios</span><strong>{socios.length}</strong></article>
          <article><span>Pagos</span><strong>{pagos.length}</strong></article>
          <article><span>Ingresos registrados</span><strong>{formatMoney(totalPagos)}</strong></article>
          <article><span>Abonos pendientes</span><strong>{formatMoney(totalAbonosPendientes)}</strong></article>
        </div>
      </header>

      <nav className="tabbar rounded-2xl border border-zinc-200 bg-white p-2 shadow-sm">
        {[
          ['dashboard', 'Inicio'],
          ['socios', 'Socios y base'],
          ['manual', 'Registrar pago'],
          ['banco', 'Importar banco'],
          ['conflictos', `Conflictos (${draftConflictos.length + pendientesConflictos.length})`],
          ['pagos', 'Historial pagos'],
        ].map(([id, label]) => (
          <button
            key={id}
            className={`${tab === id ? 'active !bg-red-700 !text-white' : ''} rounded-xl px-4 py-2 text-sm font-semibold transition`}
            onClick={() => setTab(id)}
            disabled={isLoading}
          >
            {label}
          </button>
        ))}
      </nav>

      {mensaje && <p className="alert">{mensaje}</p>}

      {tab === 'dashboard' && (
        <section className="panel rounded-2xl border border-zinc-200 bg-gradient-to-br from-white to-red-50/30 p-6 shadow-sm">
          <div className="mb-4 flex flex-col gap-1">
            <h2 className="text-2xl font-bold tracking-tight text-zinc-900">Panel operativo</h2>
            <p className="text-sm text-zinc-600">Vista diaria de cobranza, movimientos bancarios y pendientes de conciliacion.</p>
          </div>
          <div className="grid gap-3 md:grid-cols-4">
            <article className="rounded-xl border border-zinc-200 bg-white p-4">
              <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">Cuotas ingresadas</span>
              <strong className="mt-1 block text-xl text-zinc-900">{formatMoney(totalPagos)}</strong>
            </article>
            <article className="rounded-xl border border-zinc-200 bg-white p-4">
              <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">Otros ingresos</span>
              <strong className="mt-1 block text-xl text-zinc-900">{formatMoney(totalOtrosIngresos)}</strong>
            </article>
            <article className="rounded-xl border border-zinc-200 bg-white p-4">
              <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">Egresos</span>
              <strong className="mt-1 block text-xl text-zinc-900">{formatMoney(totalEgresos)}</strong>
            </article>
            <article className="rounded-xl border border-red-200 bg-red-50 p-4">
              <span className="text-xs font-medium uppercase tracking-wide text-red-700">Saldo neto</span>
              <strong className="mt-1 block text-xl text-red-800">{formatMoney(saldoNeto)}</strong>
            </article>
          </div>

          <div className="mt-5 grid gap-4 xl:grid-cols-[2fr_1fr]">
            <div className="rounded-xl border border-zinc-200 bg-white p-4">
              <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-zinc-500">Tendencia mensual</p>
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={dashboardSeries} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="cuotasFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#C1121F" stopOpacity={0.34} />
                        <stop offset="95%" stopColor="#C1121F" stopOpacity={0.03} />
                      </linearGradient>
                      <linearGradient id="netoFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#111827" stopOpacity={0.25} />
                        <stop offset="95%" stopColor="#111827" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f1f1" />
                    <XAxis dataKey="periodo" tick={{ fill: '#52525b', fontSize: 11 }} />
                    <YAxis tick={{ fill: '#52525b', fontSize: 11 }} />
                    <Tooltip
                      formatter={(value) => formatMoney(value)}
                      contentStyle={{ borderRadius: 12, borderColor: '#e4e4e7' }}
                    />
                    <Area type="monotone" dataKey="cuotas" name="Cuotas" stroke="#C1121F" fill="url(#cuotasFill)" strokeWidth={2.2} />
                    <Area type="monotone" dataKey="neto" name="Neto" stroke="#111827" fill="url(#netoFill)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="rounded-xl border border-zinc-200 bg-white p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Control inmediato</p>
              <div className="mt-3 space-y-3 text-sm text-zinc-700">
                <div className="rounded-lg border border-zinc-200 p-3">
                  <p>Pendientes de banco</p>
                  <p className="text-lg font-semibold text-zinc-900">{pendientes.length}</p>
                </div>
                <div className="rounded-lg border border-zinc-200 p-3">
                  <p>Conflictos en revision</p>
                  <p className="text-lg font-semibold text-zinc-900">{draftConflictos.length}</p>
                </div>
                <div className="rounded-lg border border-zinc-200 p-3">
                  <p>Conflictos en BD</p>
                  <p className="text-lg font-semibold text-zinc-900">{pendientesConflictos.length}</p>
                </div>
                <div className="rounded-lg border border-red-100 bg-red-50 p-3">
                  <p>Abonos pendientes</p>
                  <p className="text-lg font-semibold text-red-700">{formatMoney(totalAbonosPendientes)}</p>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {tab === 'socios' && (
        <section className="panel">
          <div className="panel-header">
            <h2>Base principal</h2>
            <label className="file-input">
              Cargar Ejercicio_Cuotas.xlsx
              <input type="file" accept=".xlsx,.xls" onChange={importarSociosYPagos} disabled={isLoading} />
            </label>
          </div>
          <table>
            <thead>
              <tr><th>RUT</th><th>Nombre</th><th>Ano</th><th>Sexo</th><th>Estado</th></tr>
            </thead>
            <tbody>
              {socios.slice(0, 100).map((socio) => (
                <tr key={socio.rut}><td>{socio.rut}</td><td>{socio.nombre}</td><td>{socio.anio}</td><td>{socio.sexo}</td><td>{socio.estado}</td></tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {tab === 'manual' && (
        <section className="panel">
          <h2>Registrar pago manual</h2>
          <form className="form-grid" onSubmit={submitManualPayment}>
            <label>
              Socio (RUT)
              <input list="ruts" value={manualForm.rut} onChange={(e) => seleccionarSocio(normalizeRut(e.target.value))} required />
              <datalist id="ruts">
                {socios.map((socio) => (
                  <option key={socio.rut} value={socio.rut}>{`${socio.rut} - ${socio.nombre}`}</option>
                ))}
              </datalist>
            </label>
            <label>
              Fecha de pago
              <input type="date" value={manualForm.fechaPago} onChange={(e) => setManualForm((p) => ({ ...p, fechaPago: e.target.value }))} required />
            </label>
            <label>
              Total pago
              <input type="number" min="0" value={manualForm.totalPago} onChange={(e) => setManualForm((p) => ({ ...p, totalPago: Number(e.target.value) }))} required />
            </label>
            <label>
              Tipo cuota
              <select value={manualForm.tipoCuota} onChange={(e) => {
                const tipo = normalizeTipoCuota(e.target.value)
                setManualForm((p) => ({ ...p, tipoCuota: tipo, valorCuota: cuotaPorTipo(tipo) }))
              }}>
                <option value="ACTIVO">ACTIVO</option>
                <option value="MEMBRESIA">MEMBRESIA</option>
                <option value="BECADO">BECADO</option>
                <option value="OTRO">OTRO</option>
              </select>
            </label>
            <label>
              Valor cuota
              <input type="number" min="0" value={manualForm.valorCuota} onChange={(e) => setManualForm((p) => ({ ...p, valorCuota: Number(e.target.value) }))} required />
            </label>
            <label className="full-width">
              Observacion
              <input value={manualForm.observacion} onChange={(e) => setManualForm((p) => ({ ...p, observacion: e.target.value }))} />
            </label>

            <div className="full-width period-box">
              <p className="hint">Asignar cuotas por mes (checklist)</p>
              <div className="period-list">
                {manualPeriodOptions.map((periodo) => (
                  <label key={periodo} className="period-item">
                    <input type="checkbox" checked={manualForm.periodos.includes(periodo)} onChange={() => toggleManualPeriodo(periodo)} />
                    <span>{periodo}</span>
                  </label>
                ))}
              </div>
            </div>

            {manualForm.tipoCuota === 'BECADO' && <p className="hint full-width">Becado: no genera cobro de cuota.</p>}
            <button type="submit" disabled={isLoading}>Guardar pago</button>
          </form>
        </section>
      )}

      {tab === 'banco' && (
        <section className="panel">
          <div className="panel-header">
            <h2>Importar cartola y revisar</h2>
            <label className="file-input">
              Cargar Marzo 16-03-2026.xlsx
              <input type="file" accept=".xlsx,.xls" onChange={cargarCartolaARevision} disabled={isLoading} />
            </label>
          </div>

          {cartolaDraft.length > 0 && (
            <>
              <div className="panel-header">
                <p className="hint">Formulario de asignacion previa (RUT + checklist de meses)</p>
                <div>
                  <button className="small" onClick={() => processDraft()} disabled={isLoading}>Procesar todos seleccionados</button>
                </div>
              </div>
              <table>
                <thead>
                  <tr>
                    <th>OK</th><th>Fecha</th><th>Monto</th><th>RUT</th><th>Socio</th><th>Categoria</th><th>Tipo cuota</th><th>Meses checklist</th><th>Accion</th>
                  </tr>
                </thead>
                <tbody>
                  {cartolaDraft.map((item) => (
                    <tr key={item.id}>
                      <td><input type="checkbox" checked={item.selected} onChange={(e) => actualizarDraft(item.id, 'selected', e.target.checked)} /></td>
                      <td>{item.fecha}</td>
                      <td>{formatMoney(item.monto)}</td>
                      <td>{item.rut || '-'}</td>
                      <td>{item.socioNombre || '-'}</td>
                      <td>
                        <select value={item.categoria} onChange={(e) => actualizarDraft(item.id, 'categoria', e.target.value)}>
                          <option>Cuota</option><option>Otro ingreso</option><option>Egreso</option>
                        </select>
                      </td>
                      <td>
                        <select value={item.tipoCuota} onChange={(e) => actualizarDraft(item.id, 'tipoCuota', e.target.value)}>
                          <option value="ACTIVO">ACTIVO</option>
                          <option value="MEMBRESIA">MEMBRESIA</option>
                          <option value="BECADO">BECADO</option>
                          <option value="OTRO">OTRO</option>
                        </select>
                      </td>
                      <td>
                        <div className="period-list compact">
                          {item.periodOptions.map((periodo) => (
                            <label key={`${item.id}-${periodo}`} className="period-item">
                              <input type="checkbox" checked={item.periodos.includes(periodo)} onChange={() => toggleDraftPeriodo(item.id, periodo)} />
                              <span>{periodo}</span>
                            </label>
                          ))}
                        </div>
                      </td>
                      <td><button className="small" onClick={() => processDraft(item.id)} disabled={isLoading}>Procesar 1</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          <h3>Pendientes ya guardados en BD</h3>
          <table>
            <thead>
              <tr><th>Fecha</th><th>Monto</th><th>RUT</th><th>Categoria</th><th>Tipo cuota</th><th>Accion</th></tr>
            </thead>
            <tbody>
              {pendientes.map((item) => (
                <tr key={item.id}>
                  <td>{item.fecha}</td>
                  <td>{formatMoney(item.monto)}</td>
                  <td>{item.rut || '-'}</td>
                  <td>{item.categoria}</td>
                  <td>{item.tipoCuota || 'ACTIVO'}</td>
                  <td><button className="small" onClick={() => procesarPendienteBD(item)} disabled={isLoading}>Procesar</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {tab === 'conflictos' && (
        <section className="panel rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <h2>Conflictos de asignacion</h2>
          <p className="hint">Cuotas sin socio detectado por RUT. Resuelvelas antes de procesar.</p>
          <div className="my-3 flex max-w-sm items-center gap-2">
            <label className="text-sm font-medium text-zinc-700">Filtro por RUT</label>
            <input
              className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm"
              value={filtroConflictoRut}
              onChange={(e) => setFiltroConflictoRut(e.target.value)}
              placeholder="Ej: 17682512K"
            />
          </div>

          <h3>Conflictos en revision de cartola</h3>
          <table>
            <thead>
              <tr><th>Fecha</th><th>Monto</th><th>Descripcion</th><th>RUT detectado</th><th>Asignar socio</th><th>Estado</th></tr>
            </thead>
            <tbody>
              {draftConflictosFiltrados.map((item) => (
                <tr key={item.id}>
                  <td>{item.fecha}</td>
                  <td>{formatMoney(item.monto)}</td>
                  <td>{item.descripcion}</td>
                  <td>{item.rut || '-'}</td>
                  <td>
                    <input
                      list="ruts-conf"
                      value={item.resolverSocio || ''}
                      onChange={(e) => {
                        actualizarDraft(item.id, 'resolverSocio', e.target.value)
                        asignarSocioDraft(item.id, e.target.value)
                      }}
                      placeholder="RUT o nombre"
                    />
                  </td>
                  <td>{item.socioNombre ? `OK: ${item.socioNombre}` : 'Pendiente'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!draftConflictosFiltrados.length && <p className="hint">No hay conflictos en revision de cartola para ese RUT.</p>}

          <h3>Conflictos pendientes en BD</h3>
          <table>
            <thead>
              <tr><th>ID</th><th>Fecha</th><th>Monto</th><th>Descripcion</th><th>RUT actual</th><th>Resolver</th><th>Accion</th></tr>
            </thead>
            <tbody>
              {pendientesConflictosFiltrados.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td>{item.fecha}</td>
                  <td>{formatMoney(item.monto)}</td>
                  <td>{item.descripcion}</td>
                  <td>{item.rut || '-'}</td>
                  <td>
                    <input
                      list="ruts-conf"
                      value={resolucionPendientes[item.id]?.rut || ''}
                      onChange={(e) => actualizarResolucionPendiente(item.id, 'rut', e.target.value)}
                      placeholder="RUT"
                    />
                  </td>
                  <td><button className="small" onClick={() => guardarConflictoPendiente(item)} disabled={isLoading}>Guardar</button></td>
                </tr>
              ))}
            </tbody>
          </table>
          {!pendientesConflictosFiltrados.length && <p className="hint">No hay conflictos pendientes en BD para ese RUT.</p>}
          <datalist id="ruts-conf">
            {socios.map((socio) => (
              <option key={`conf-${socio.rut}`} value={`${socio.rut} - ${socio.nombre}`} />
            ))}
          </datalist>
        </section>
      )}

      {tab === 'pagos' && (
        <section className="panel">
          <h2>Historial de pagos</h2>
          <table>
            <thead>
              <tr><th>Fecha</th><th>RUT</th><th>Nombre</th><th>Total</th><th>Tipo cuota</th><th>Valor cuota</th><th>Meses</th><th>Detalle meses</th><th>Origen</th></tr>
            </thead>
            <tbody>
              {pagosOrdenados.slice(0, 250).map((pago) => (
                <tr key={pago.id}>
                  <td>{pago.fechaPago}</td><td>{pago.rut}</td><td>{pago.nombre}</td><td>{formatMoney(pago.totalPago)}</td>
                  <td>{pago.tipoCuota || '-'}</td><td>{formatMoney(pago.valorCuota)}</td><td>{pago.mesesCantidad}</td><td>{pago.mesesDetalle || '-'}</td><td>{pago.origen}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </main>
  )
}

function categoryDefaultPeriods(periodOptions, startIndex, count) {
  const size = Math.max(1, count)
  return periodOptions.slice(startIndex, startIndex + size)
}

export default App
