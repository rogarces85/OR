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

const normalizeName = (value) =>
  String(value ?? '')
    .toUpperCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^A-Z0-9 ]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

const MONTH_HEADER_MAP = {
  ENERO: '01',
  FEBRERO: '02',
  MARZO: '03',
  ABRIL: '04',
  MAYO: '05',
  JUNIO: '06',
  JULIO: '07',
  AGOSTO: '08',
  SEPTIEMBRE: '09',
  OCTUBRE: '10',
  NOVIEMBRE: '11',
  DICIEMBRE: '12',
}

const isMeaningfulMemberName = (value) => {
  const name = normalizeName(value)
  if (!name || name.length < 3) return false
  return !['INTEGRANTE', 'TOTAL', 'PAGABAS', 'PENDIENTES'].includes(name)
}

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

const parseEstadoCuotasSheet = (sheetName, sheet) => {
  const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' })
  const headerIndex = rows.findIndex((row) => row.some((cell) => normalizeHeader(cell) === 'INTEGRANTE'))
  if (headerIndex < 0) return null

  const yearMatch = String(sheetName).match(/\d{4}/)
  const year = Number(yearMatch?.[0] || new Date().getFullYear())
  const headerRow = rows[headerIndex] || []
  let carryDebtIndex = -1
  let debtIndex = -1
  let totalPaidIndex = -1
  const monthColumns = []

  headerRow.forEach((cell, index) => {
    const normalized = normalizeHeader(cell)
    if (MONTH_HEADER_MAP[normalized]) {
      monthColumns.push({
        index,
        label: String(cell || normalized).trim(),
        period: `${year}-${MONTH_HEADER_MAP[normalized]}`,
      })
      return
    }
    if (normalized === 'TOTALPAGADO') {
      totalPaidIndex = index
      return
    }
    if (normalized === 'DEUDA') {
      debtIndex = index
      return
    }
    if (normalized.startsWith('DEUDA') && carryDebtIndex < 0) carryDebtIndex = index
  })

  const entries = rows
    .slice(headerIndex + 1)
    .map((row) => {
      const name = String(row[0] ?? '').trim()
      if (!isMeaningfulMemberName(name)) return null

      const monthStates = monthColumns.map(({ index, label, period }) => {
        const raw = row[index]
        const amount = parseNumber(raw)
        const text = String(raw ?? '').trim()
        const normalizedText = normalizeHeader(text)
        const kind = amount > 0 ? 'paid' : normalizedText === 'INGRESO' ? 'ingreso' : normalizedText === 'RETIRO' ? 'retiro' : text ? 'note' : 'empty'
        return {
          label,
          period,
          raw: text,
          amount,
          kind,
          display: amount > 0 ? formatMoney(amount) : text || '-',
        }
      })

      const paidTotal = totalPaidIndex >= 0 ? parseNumber(row[totalPaidIndex]) : monthStates.reduce((sum, month) => sum + month.amount, 0)
      const carryDebt = carryDebtIndex >= 0 ? parseNumber(row[carryDebtIndex]) : 0
      const currentDebt = debtIndex >= 0 ? parseNumber(row[debtIndex]) : 0
      const notes = monthStates.filter((month) => ['ingreso', 'retiro', 'note'].includes(month.kind)).map((month) => `${month.label}: ${month.display}`)

      return {
        id: `${year}-${normalizeName(name)}`,
        year,
        name,
        paidTotal,
        carryDebt,
        debt: currentDebt,
        paidMonths: monthStates.filter((month) => month.kind === 'paid').length,
        activityMonths: monthStates.filter((month) => month.kind !== 'empty').length,
        notes,
        monthStates,
      }
    })
    .filter(Boolean)

  return {
    year,
    sheetName,
    entries,
    totals: {
      members: entries.length,
      paidTotal: entries.reduce((sum, item) => sum + item.paidTotal, 0),
      carryDebtTotal: entries.reduce((sum, item) => sum + item.carryDebt, 0),
      debtTotal: entries.reduce((sum, item) => sum + item.debt, 0),
      withCarryDebt: entries.filter((item) => item.carryDebt > 0).length,
      withDebt: entries.filter((item) => item.debt > 0).length,
    },
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
  const [estadoWorkbook, setEstadoWorkbook] = useState({ sourceName: '', importedAt: '', sheets: [] })
  const [estadoYear, setEstadoYear] = useState('')
  const [estadoQuery, setEstadoQuery] = useState('')
  const [estadoFilter, setEstadoFilter] = useState('todos')
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
    if (data.estadoCuotas) {
      setEstadoWorkbook({
        sourceName: data.estadoCuotas.sourceName || '',
        importedAt: data.estadoCuotas.importedAt || '',
        sheets: data.estadoCuotas.sheets || [],
      })
      setEstadoYear((prev) => prev || String(data.estadoCuotas.sheets?.[data.estadoCuotas.sheets.length - 1]?.year || ''))
    }
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

  const socioByNormalizedName = useMemo(() => {
    const map = new Map()
    socios.forEach((socio) => {
      const key = normalizeName(socio.nombre)
      if (key && !map.has(key)) map.set(key, socio)
    })
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

  const cargarEstadoCuotas = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    try {
      setIsLoading(true)
      const data = await file.arrayBuffer()
      const workbook = XLSX.read(data, { type: 'array' })
      const sheets = workbook.SheetNames
        .map((sheetName) => parseEstadoCuotasSheet(sheetName, workbook.Sheets[sheetName]))
        .filter(Boolean)
        .map((sheetData) => ({
          ...sheetData,
          entries: sheetData.entries.map((entry) => {
            const socio = socioByNormalizedName.get(normalizeName(entry.name))
            return {
              ...entry,
              rut: socio?.rut || '',
              socioEstado: socio?.estado || '',
              linkedName: socio?.nombre || entry.name,
            }
          }),
        }))
        .sort((a, b) => a.year - b.year)

      if (!sheets.length) {
        setMensaje('No se detectaron hojas validas de estado de cuotas en el archivo.')
        return
      }

      const saveResponse = await apiRequest('import_estado_cuotas.php', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sourceName: file.name, sheets }),
      })

      setEstadoWorkbook({
        sourceName: file.name,
        importedAt: new Date().toISOString(),
        sheets,
      })
      setEstadoYear(String(sheets[sheets.length - 1].year))
      setEstadoQuery('')
      setEstadoFilter('todos')
      setTab('estado')
      setMensaje(`Estado anual cargado y guardado en BD: ${file.name}, ${saveResponse.rowsSaved} filas.`)
    } catch (error) {
      setMensaje(error.message)
    } finally {
      setIsLoading(false)
      event.target.value = ''
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
  const estadoSheets = useMemo(() => estadoWorkbook.sheets || [], [estadoWorkbook.sheets])
  const estadoActual = useMemo(
    () => estadoSheets.find((sheet) => String(sheet.year) === String(estadoYear)) || estadoSheets[estadoSheets.length - 1] || null,
    [estadoSheets, estadoYear],
  )
  const estadoRows = useMemo(() => {
    if (!estadoActual) return []
    const query = normalizeName(estadoQuery)
    return estadoActual.entries
      .filter((entry) => {
        const searchBase = `${normalizeName(entry.name)} ${entry.rut}`.trim()
        if (query && !searchBase.includes(query)) return false
        if (estadoFilter === 'deuda' && entry.debt <= 0 && entry.carryDebt <= 0) return false
        if (estadoFilter === 'al-dia' && (entry.debt > 0 || entry.carryDebt > 0)) return false
        if (estadoFilter === 'eventos' && !entry.notes.length) return false
        return true
      })
      .sort((a, b) => (b.debt + b.carryDebt) - (a.debt + a.carryDebt) || b.paidTotal - a.paidTotal || a.name.localeCompare(b.name))
  }, [estadoActual, estadoFilter, estadoQuery])
  const estadoTopDebt = useMemo(() => estadoRows.filter((entry) => entry.debt + entry.carryDebt > 0).slice(0, 5), [estadoRows])

  return (
    <main className="app-shell">
      <header className="topbar">
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

      <nav className="tabbar">
        {[
          ['dashboard', 'Inicio'],
          ['socios', 'Socios y base'],
          ['estado', 'Estado anual'],
          ['manual', 'Registrar pago'],
          ['banco', 'Importar banco'],
          ['conflictos', `Conflictos (${draftConflictos.length + pendientesConflictos.length})`],
          ['pagos', 'Historial pagos'],
        ].map(([id, label]) => (
          <button
            key={id}
            className={tab === id ? 'active' : ''}
            onClick={() => setTab(id)}
            disabled={isLoading}
          >
            {label}
          </button>
        ))}
      </nav>

      {mensaje && <p className="alert">{mensaje}</p>}

      {tab === 'dashboard' && (
        <section className="panel">
          <div className="landing-grid mb-6">
            <div className="landing-hero-card">
              <p className="eyebrow">RUNNING CLUB + CONTROL DE CUOTAS</p>
              <h2 className="mt-2 text-3xl font-bold tracking-tight md:text-5xl" style={{ color: '#dee5ff' }}>Osorno Runners corre en comunidad y administra sus cuotas con orden.</h2>
              <p className="mt-3 max-w-2xl text-base leading-7" style={{ color: 'var(--muted)' }}>
                Esta portada mezcla landing del club y acceso interno: presenta la comunidad, visibiliza el estado operativo y deja a mano los modulos que ya usan para socios, pagos y conciliacion.
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                <button type="button" onClick={() => setTab('manual')} disabled={isLoading}>Registrar pago</button>
                <button type="button" className="ghost-btn" onClick={() => setTab('estado')} disabled={isLoading}>Revisar estado anual</button>
              </div>
              <div className="mt-5 flex flex-wrap gap-2 text-sm" style={{ color: 'var(--muted)' }}>
                <span className="mini-badge">Comunidad runner</span>
                <span className="mini-badge">Control de cuotas</span>
                <span className="mini-badge">Conciliacion bancaria</span>
                <span className="mini-badge">Historial por ano</span>
              </div>
            </div>

            <div className="landing-side-card">
              <p className="eyebrow">Lo esencial hoy</p>
              <div className="mt-4 grid gap-3">
                <article>
                  <span>Socios en base</span>
                  <strong>{socios.length}</strong>
                </article>
                <article>
                  <span>Pagos registrados</span>
                  <strong>{formatMoney(totalPagos)}</strong>
                </article>
                <article>
                  <span>Pendientes por conciliar</span>
                  <strong>{pendientes.length}</strong>
                </article>
              </div>
            </div>
          </div>

          <div className="landing-features mb-6">
            <article className="landing-feature">
              <h3>Club visible</h3>
              <p>Una portada con identidad para mostrar Osorno Runners y abrir el sistema desde el mismo lugar.</p>
            </article>
            <article className="landing-feature">
              <h3>Operacion trazable</h3>
              <p>Pagos manuales, historicos y movimientos bancarios quedan centralizados con contexto por socio y periodo.</p>
            </article>
            <article className="landing-feature">
              <h3>Estado anual</h3>
              <p>El archivo de estado de cuotas ahora se puede leer para revisar arrastre, deuda y eventos por ano.</p>
            </article>
          </div>

          <div className="mb-4 flex flex-col gap-1">
            <h2 style={{ color: '#dee5ff' }}>Panel operativo</h2>
            <p style={{ color: 'var(--muted)' }}>Vista diaria de cobranza, movimientos bancarios y pendientes de conciliacion.</p>
          </div>
          <div className="summary-cards" style={{ gridTemplateColumns: 'repeat(4, minmax(0, 1fr))' }}>
            <article>
              <span>Cuotas ingresadas</span>
              <strong>{formatMoney(totalPagos)}</strong>
            </article>
            <article>
              <span>Otros ingresos</span>
              <strong>{formatMoney(totalOtrosIngresos)}</strong>
            </article>
            <article>
              <span>Egresos</span>
              <strong>{formatMoney(totalEgresos)}</strong>
            </article>
            <article style={{ border: '1px solid #ff9157' }}>
              <span style={{ color: '#ff9157' }}>Saldo neto</span>
              <strong style={{ color: '#ff9157' }}>{formatMoney(saldoNeto)}</strong>
            </article>
          </div>

          <div className="mt-5 grid gap-4 xl:grid-cols-[2fr_1fr]">
            <div className="landing-side-card" style={{ padding: '24px' }}>
              <p className="eyebrow" style={{ marginBottom: '16px' }}>Tendencia mensual</p>
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={dashboardSeries} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="cuotasFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ff9157" stopOpacity={0.34} />
                        <stop offset="95%" stopColor="#ff9157" stopOpacity={0.0} />
                      </linearGradient>
                      <linearGradient id="netoFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#47c4ff" stopOpacity={0.34} />
                        <stop offset="95%" stopColor="#47c4ff" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#40485d" strokeOpacity={0.3} vertical={false} />
                    <XAxis dataKey="periodo" tick={{ fill: '#a3aac4', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: '#a3aac4', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(val) => `$${val / 1000}k`} />
                    <Tooltip
                      formatter={(value) => formatMoney(value)}
                      contentStyle={{ borderRadius: 12, borderColor: '#40485d', backgroundColor: '#192540', color: '#dee5ff' }}
                      itemStyle={{ color: '#dee5ff' }}
                    />
                    <Area type="monotone" dataKey="cuotas" name="Cuotas" stroke="#ff9157" fill="url(#cuotasFill)" strokeWidth={3} />
                    <Area type="monotone" dataKey="neto" name="Neto" stroke="#47c4ff" fill="url(#netoFill)" strokeWidth={3} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="landing-side-card">
              <p className="eyebrow" style={{ marginBottom: '16px' }}>Control inmediato</p>
              <div className="mt-3 space-y-3 text-sm" style={{ color: 'var(--text)' }}>
                <article>
                  <span>Pendientes de banco</span>
                  <strong>{pendientes.length}</strong>
                </article>
                <article>
                  <span>Conflictos en revision</span>
                  <strong>{draftConflictos.length}</strong>
                </article>
                <article>
                  <span>Conflictos en BD</span>
                  <strong>{pendientesConflictos.length}</strong>
                </article>
                <article style={{ border: '1px solid #ff9157', boxShadow: '0 0 10px rgba(255, 145, 87, 0.1)' }}>
                  <span style={{ color: '#ff9157' }}>Abonos pendientes</span>
                  <strong style={{ color: '#ff9157' }}>{formatMoney(totalAbonosPendientes)}</strong>
                </article>
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

      {tab === 'estado' && (
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Estado anual de cuotas</h2>
              <p className="hint">Carga `Estado de cuotas OR 2024.xlsx` para revisar las hojas 2024, 2025 y 2026 desde una sola interfaz.</p>
            </div>
            <label className="file-input">
              Cargar estado anual
              <input type="file" accept=".xlsx,.xls" onChange={cargarEstadoCuotas} disabled={isLoading} />
            </label>
          </div>

          {!estadoActual && (
            <div className="empty-state-box">
              <p className="mb-2 text-base font-semibold text-zinc-900">Listo para revisar el estado del club.</p>
              <p className="m-0 text-sm text-zinc-600">El analizador resume deuda de arrastre, total pagado, deuda del ano y marcas como `INGRESO` o `RETIRO` por integrante.</p>
            </div>
          )}

          {estadoActual && (
            <>
              <div className="panel-header items-end">
                <div>
                  <p className="hint">Archivo actual: {estadoWorkbook.sourceName}{estadoWorkbook.importedAt ? ` · guardado ${String(estadoWorkbook.importedAt).slice(0, 19).replace('T', ' ')}` : ''}</p>
                  <div className="sheet-tabs mt-2">
                    {estadoSheets.map((sheet) => (
                      <button
                        type="button"
                        key={sheet.year}
                        className={String(sheet.year) === String(estadoActual.year) ? 'active small' : 'small ghost-btn'}
                        onClick={() => setEstadoYear(String(sheet.year))}
                      >
                        {sheet.year}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="filters-row">
                  <input value={estadoQuery} onChange={(e) => setEstadoQuery(e.target.value)} placeholder="Buscar por nombre o RUT" />
                  <select value={estadoFilter} onChange={(e) => setEstadoFilter(e.target.value)}>
                    <option value="todos">Todos</option>
                    <option value="deuda">Con deuda</option>
                    <option value="al-dia">Al dia</option>
                    <option value="eventos">Con eventos</option>
                  </select>
                </div>
              </div>

              <div className="summary-cards annual-cards">
                <article><span>Integrantes</span><strong>{estadoActual.totals.members}</strong></article>
                <article><span>Total pagado</span><strong>{formatMoney(estadoActual.totals.paidTotal)}</strong></article>
                <article><span>Deuda arrastre</span><strong>{formatMoney(estadoActual.totals.carryDebtTotal)}</strong></article>
                <article><span>Deuda del ano</span><strong>{formatMoney(estadoActual.totals.debtTotal)}</strong></article>
                <article><span>Socios con arrastre</span><strong>{estadoActual.totals.withCarryDebt}</strong></article>
                <article><span>Socios con deuda</span><strong>{estadoActual.totals.withDebt}</strong></article>
              </div>

              {!!estadoTopDebt.length && (
                <div className="top-debt-box">
                  <p className="mb-3 text-xs font-semibold uppercase tracking-[0.22em] text-red-700">Mayores saldos a revisar</p>
                  <div className="top-debt-grid">
                    {estadoTopDebt.map((entry) => (
                      <article key={`top-${entry.id}`}>
                        <strong>{entry.name}</strong>
                        <span>{entry.rut || 'Sin RUT vinculado'}</span>
                        <em>{formatMoney(entry.debt + entry.carryDebt)}</em>
                      </article>
                    ))}
                  </div>
                </div>
              )}

              <table>
                <thead>
                  <tr><th>Integrante</th><th>RUT</th><th>Estado club</th><th>Arrastre</th><th>Pagado</th><th>Deuda</th><th>Detalle mensual</th></tr>
                </thead>
                <tbody>
                  {estadoRows.map((entry) => (
                    <tr key={entry.id}>
                      <td>
                        <strong>{entry.name}</strong>
                        {entry.notes.length > 0 && <div className="hint">{entry.notes.join(' | ')}</div>}
                      </td>
                      <td>{entry.rut || '-'}</td>
                      <td>{entry.socioEstado || '-'}</td>
                      <td>{formatMoney(entry.carryDebt)}</td>
                      <td>{formatMoney(entry.paidTotal)}</td>
                      <td>{formatMoney(entry.debt)}</td>
                      <td>
                        <div className="month-cells">
                          {entry.monthStates.filter((month) => month.kind !== 'empty').map((month) => (
                            <span key={`${entry.id}-${month.period}`} className={`month-cell ${month.kind}`}>
                              {month.label.slice(0, 3)}: {month.display}
                            </span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!estadoRows.length && <p className="hint">No hay resultados para el filtro actual.</p>}
            </>
          )}
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
        <section className="panel">
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
