---
author: Rodrigo Garces
branch: portal-movil-pwa
status: draft
type: spec
title: Portal Móvil del Miembro (PWA/Responsive)
description: Portal PWA instalable para que miembros consulten estado de cuenta, historial, comprobantes, avisos y soliciten cambio de categoría. Solo lectura + subida comprobantes. Auth JWT en HttpOnly cookie.
timestamp: 2026-11-10T00:00:00Z
topic: ftd
depends_on: ["2026-11-10-boveda-documentos-cifrada"]
blocks: ["2026-11-10-carga-comprobantes-socio", "2026-11-10-recibos-email", "2026-11-10-push-notificaciones", "2026-11-10-gastos-comunes"]
---

# FTD-001: Portal Móvil del Miembro (PWA/Responsive)

## Intent

Entregar a cada miembro un **portal móvil instalable (PWA)** donde consultar su estado de cuenta, historial de pagos, deudas, comprobantes subidos, avisos/notificaciones y perfil — **sin intervención del Tesorero**. Reduce carga operativa, mejora transparencia (RN-06/RN-07) y sienta la base para FT-02 (carga comprobantes), FT-04 (recibos), FT-09 (push), FT-10 (gastos comunes).

## Scope

### Incluido

**Autenticación Miembro:**
- Login: email + contraseña (bcrypt, misma tabla `Usuario` con `rol = 'miembro'`)
- JWT en **HttpOnly Secure SameSite=Strict cookie** (access 15min, refresh 7d rotativo)
- Rate-limit: 10 req/min login, 60 req/min API autenticada
- Recuperación contraseña: token JWT 1h → email con link (respeta RN-13: plantilla, no envío masivo)
- Bloqueo 5 intentos fallidos → 15 min cooldown

**Vistas (Mobile-First, Jinja2 + Tailwind + Alpine.js):**
| Vista | Ruta | Descripción |
|-------|------|-------------|
| Login | `/miembro/login` | Formulario email/password, "¿Olvidó clave?", link registro (solo si habilitado) |
| Dashboard | `/miembro/` | Resumen: color mora (badge), próxima cuota (monto+fecha), saldo a favor, acciones rápidas |
| Estado de Cuenta | `/miembro/estado-cuenta` | Tabla paginada (20 rows): Mes, Categoría, Monto, Estado, Pago, Comprobante (ver/descargar) |
| Comprobantes | `/miembro/comprobantes` | Grid lista: thumbnail, fecha, tipo, estado validación, descargar |
| Visor Comprobante | `/miembro/comprobantes/{id}` | Modal/Fullscreen: zoom, rotar, descargar (valida propiedad) |
| Avisos | `/miembro/avisos` | Lista: ícono tipo, título, fecha, leído/no leído, marcar leído, filtro |
| Perfil | `/miembro/perfil` | Solo lectura: nombre, email, RUT, teléfono, categoría actual, fecha ingreso, cuenta bancaria club |
| Cambio Categoría | `/miembro/categoria/solicitar` | Form: seleccionar nueva (ACTIVO↔ESTANDAR), motivo opcional → notifica Tesorero |

**PWA (Progressive Web App):**
- `manifest.json`: name, short_name, icons (192/512), start_url `/miembro/`, display `standalone`, theme_color `#dc2626`, background_color `#ffffff`
- `sw.js` (Service Worker): **Cache-First** para assets estáticos (CSS, JS, imágenes, manifest), **Network-First** para API GET (con fallback cache 5min), **Stale-While-Revalidate** para dashboard/estado-cuenta
- `offline.html`: página amable si sin conexión y sin cache
- Registra SW en `_base_miembro.html` (layout portal)
- **Instalable**: cumple criterios Chrome/Edge/Firefox/Safari (HTTPS, manifest, SW, icons)

**Responsive Breakpoints:**
- `< 640px`: Mobile (stack, bottom nav, touch targets 44px)
- `640px - 1023px`: Tablet (sidebar colapsable, 2-col grids)
- `≥ 1024px`: Desktop (layout completo, sidebar fija)

**Seguridad:**
- Dependency `get_current_miembro`: valida rol `miembro` + activo + no exento (exentos ven portal pero sin deudas)
- Rate-limit por IP + usuario (Redis/in-memory)
- CSP: `default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; font-src 'self' https://fonts.gstatic.com; frame-ancestors 'none';`
- HSTS, X-Frame-Options DENY, X-Content-Type-Options nosniff
- Auditoría: login, logout, vista estado-cuenta, descarga comprobante, solicitud cambio categoría

### Excluido

- Registro público de miembros (solo Admin/Tesorero crean miembros)
- Acciones de escritura salvo: subir comprobante (FT-02), solicitar cambio categoría, marcar aviso leído
- Ver datos de otros miembros o finanzas globales (RN-06/RN-07)
- Pagos online / Webpay (descartado por stakeholder)
- Notificaciones email automáticas (respeta RN-13: solo plantilla para Tesorero)
- App nativa iOS/Android (PWA cubre caso de uso)

## Arquitectura

### Capas Portal Miembro

```
┌─────────────────────────────────────────────────────────────────┐
│                      PORTAL MIEMBRO (PWA)                       │
├─────────────────────────────────────────────────────────────────┤
│  PRESENTACIÓN                                                   │
│  ├── templates/miembro/                                         │
│  │   ├── _base.html          # Layout + SW register + manifest  │
│  │   ├── login.html          # Form login + recuperacion        │
│  │   ├── dashboard.html      # KPIs + acciones rápidas          │
│  │   ├── estado_cuenta.html  # Tabla paginada + filtros         │
│  │   ├── comprobantes.html   # Grid + modal visor               │
│  │   ├── avisos.html         # Lista + toggle leido             │
│  │   ├── perfil.html         # Solo lectura + boton solicitud   │
│  │   └── categoria_solicitud.html                                            │
│  ├── static/css/miembro.css   # Tailwind + utilidades custom   │
│  ├── static/js/miembro.js     # Alpine.js components + API client                                 │
│  ├── static/js/sw.js          # Service Worker (Workbox-like)  │
│  └── manifest.json            # PWA manifest                   │
├─────────────────────────────────────────────────────────────────┤
│  RUTAS / CONTROLADORES (FastAPI)                                │
│  ├── app/routers/miembro.py  # Prefijo /miembro, tags=["miembro"]│
│  │   ├── GET  /login          # Form login                      │
│  │   ├── POST /login          # Autentica → set cookies JWT     │
│  │   ├── POST /logout         # Limpia cookies + revoca refresh │
│  │   ├── POST /refresh        # Renueva access token            │
│  │   ├── GET  /               # Dashboard (requiere auth)       │
│  │   ├── GET  /estado-cuenta  # Tabla paginada                  │
│  │   ├── GET  /comprobantes   # Lista paginada                  │
│  │   ├── GET  /comprobantes/{id}/descargar  # Streaming vault   │
│  │   ├── GET  /comprobantes/{id}/ver        # Inline view       │
│  │   ├── GET  /avisos         # Lista + filtro                  │
│  │   ├── PATCH /avisos/{id}/leer             # Marcar leído     │
│  │   ├── GET  /perfil         # Datos solo lectura              │
│  │   ├── POST /categoria/solicitar           # Solicitud cambio │
│  │   ├── POST /password/olvido                # Request reset   │
│  │   ├── POST /password/reset                # Reset con token  │
│  │   └── GET  /vapid-public                   # Clave pública   │
│  └── Dependencies: get_current_miembro, rate_limiter_miembro   │
├─────────────────────────────────────────────────────────────────┤
│  SERVICIOS (Reutilizan + Extienden)                             │
│  ├── app/services/portal_miembro.py  # Vistas agregadas        │
│  │   ├── get_dashboard_data(miembro_id) → dict                 │
│  │   ├── get_estado_cuenta(miembro_id, page, per_page) → Page │
│  │   ├── get_comprobantes(miembro_id, page, per_page) → Page  │
│  │   ├── get_avisos(miembro_id, solo_no_leidos, page) → Page  │
│  │   └── solicitar_cambio_categoria(miembro_id, nueva_cat, motivo)│
│  ├── app/services/auth_miembro.py  # JWT cookies, refresh, revocación│
│  └── Reutiliza: services/miembros.py, pagos.py, notificaciones.py│
├─────────────────────────────────────────────────────────────────┤
│  REPOSITORIOS (Consultas Optimizadas)                           │
│  ├── selectinload(CuotaMensual.pago).selectinload(Pago.comprobante)│
│  ├── Índices compuestos: (miembro_id, estado), (miembro_id, fecha_vencimiento)│
│  └── Paginación: keyset (cursor) para listas grandes           │
└─────────────────────────────────────────────────────────────────┘
```

### Flujo Autenticación (JWT en Cookies)

```mermaid
sequenceDiagram
    participant Miembro
    participant Navegador
    participant Portal
    participant AuthService
    
    Miembro->>Navegador: Ingresa email + password
    Navegador->>Portal: POST /miembro/login (form)
    Portal->>AuthService: verify_password(email, password)
    AuthService-->>Portal: Usuario + rol="miembro"
    Portal->>AuthService: create_access_token(15min) + create_refresh_token(7d)
    Portal-->>Navegador: 200 OK + Set-Cookie: access=...; HttpOnly; Secure; SameSite=Strict<br/>Set-Cookie: refresh=...; HttpOnly; Secure; SameSite=Strict; Path=/miembro/refresh
    Navegador->>Portal: GET /miembro/ (Cookie access)
    Portal->>Portal: validate_access_token → miembro_id
    Portal-->>Navegador: Dashboard HTML
    
    Note over Navegador,Portal: Access token expira (15min)
    Navegador->>Portal: GET /miembro/estado-cuenta (Cookie access EXPIRADO)
    Portal-->>Navegador: 401 Unauthorized
    Navegador->>Portal: POST /miembro/refresh (Cookie refresh automático)
    Portal->>AuthService: validate_refresh_token → nueva pareja tokens
    Portal-->>Navegador: 200 + Nuevas cookies
    Navegador->>Portal: Reintenta GET /miembro/estado-cuenta
    Portal-->>Navegador: 200 Estado de cuenta
```

### Service Worker Strategy

```javascript
// static/js/sw.js
const CACHE_STATIC = 'or-static-v1';
const CACHE_API = 'or-api-v1';
const CACHE_DASHBOARD = 'or-dashboard-v1';

const STATIC_ASSETS = [
  '/static/css/miembro.css',
  '/static/js/miembro.js',
  '/manifest.json',
  '/static/images/logo-192.png',
  '/static/images/logo-512.png',
  '/offline.html'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE_STATIC).then(c => c.addAll(STATIC_ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => 
    Promise.all(keys.filter(k => !k.startsWith('or-')).map(k => caches.delete(k)))
  ));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  
  // Assets estáticos: Cache-First
  if (url.pathname.startsWith('/static/') || url.pathname === '/manifest.json') {
    e.respondWith(cacheFirst(e.request, CACHE_STATIC));
    return;
  }
  
  // API GET: Network-First con fallback cache (5 min max-age)
  if (url.pathname.startsWith('/miembro/') && e.request.method === 'GET') {
    const isDashboard = url.pathname === '/miembro/' || url.pathname.startsWith('/miembro/estado-cuenta');
    const cacheName = isDashboard ? CACHE_DASHBOARD : CACHE_API;
    e.respondWith(networkFirstWithTimeout(e.request, cacheName, 5000));
    return;
  }
  
  // Navegación HTML: Stale-While-Revalidate
  if (e.request.mode === 'navigate') {
    e.respondWith(staleWhileRevalidate(e.request, CACHE_DASHBOARD));
    return;
  }
  
  // Resto: Network only
  e.respondWith(fetch(e.request));
});

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) cache.put(request, response.clone());
  return response;
}

async function networkFirstWithTimeout(request, cacheName, timeoutMs) {
  const cache = await caches.open(cacheName);
  try {
    const response = await Promise.race([
      fetch(request),
      new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), timeoutMs))
    ]);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch {
    const cached = await cache.match(request);
    if (cached) return cached;
    return caches.match('/offline.html');
  }
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  const fetchPromise = fetch(request).then(response => {
    if (response.ok) cache.put(request, response.clone());
    return response;
  }).catch(() => cached);
  return cached || fetchPromise;
}
```

## Modelo de Datos (Extensiones)

```python
# app/models/portal.py
import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Index, JSON, Boolean, func, LargeBinary
from sqlalchemy.orm import relationship
from app.database import Base

class TipoNotificacionMiembro(str, enum.Enum):
    RECORDATORIO_CORTE = "RECORDATORIO_CORTE"
    PAGO_CONFIRMADO = "PAGO_CONFIRMADO"
    NEGOCIACION_ACEPTADA = "NEGOCIACION_ACEPTADA"
    COMPROBANTE_RECHAZADO = "COMPROBANTE_RECHAZADO"
    CARGO_COMPRA = "CARGO_COMPRA"
    AVISO_GENERAL = "AVISO_GENERAL"
    CAMBIO_CATEGORIA = "CAMBIO_CATEGORIA"

class SesionMiembro(Base):
    __tablename__ = "sesiones_miembro"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    miembro_id = Column(Integer, ForeignKey("miembros.id"), nullable=False, index=True)
    refresh_token_hash = Column(String(64), nullable=False, unique=True, index=True)  # SHA-256
    access_token_jti = Column(String(36), nullable=False, index=True)  # JWT ID para revocación
    user_agent = Column(Text)
    ip = Column(String(45))
    creado_en = Column(DateTime, default=func.now(), nullable=False)
    expira_en = Column(DateTime, nullable=False)  # 7 días
    revocado_en = Column(DateTime, nullable=True)
    ultimo_uso = Column(DateTime, nullable=True)
    
    miembro = relationship("Miembro", backref="sesiones")

class NotificacionMiembro(Base):
    __tablename__ = "notificaciones_miembro"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    miembro_id = Column(Integer, ForeignKey("miembros.id"), nullable=False, index=True)
    tipo = Column(Enum(TipoNotificacionMiembro), nullable=False, index=True)
    titulo = Column(String(200), nullable=False)
    cuerpo = Column(Text, nullable=False)
    leida = Column(Boolean, default=False, nullable=False, index=True)
    metadata_json = Column(JSON, nullable=True)  # {"cuota_id": 1, "pago_id": 2, "url": "/miembro/estado-cuenta"}
    creado_en = Column(DateTime, default=func.now(), nullable=False)
    leida_en = Column(DateTime, nullable=True)
    
    miembro = relationship("Miembro", backref="notificaciones")
    
    __table_args__ = (
        Index("ix_notif_miembro_leida_creado", "miembro_id", "leida", "creado_en"),
    )

class SolicitudCambioCategoria(Base):
    __tablename__ = "solicitudes_cambio_categoria"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    miembro_id = Column(Integer, ForeignKey("miembros.id"), nullable=False, index=True)
    categoria_actual = Column(String(20), nullable=False)  # ACTIVO, ESTANDAR
    categoria_solicitada = Column(String(20), nullable=False)
    motivo = Column(Text, nullable=True)
    estado = Column(Enum(EstadoSolicitud), default=EstadoSolicitud.PENDIENTE, nullable=False)
    revisado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    revisado_en = Column(DateTime, nullable=True)
    observaciones_tesorero = Column(Text, nullable=True)
    creado_en = Column(DateTime, default=func.now(), nullable=False)
    
    miembro = relationship("Miembro", backref="solicitudes_categoria")

class EstadoSolicitud(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    APROBADA = "APROBADA"
    RECHAZADA = "RECHAZADA"
```

## Endpoints API (Portal Miembro)

| Método | Ruta | Auth | Descripción | Response |
|--------|------|------|-------------|----------|
| GET | `/miembro/login` | No | Formulario login | HTML |
| POST | `/miembro/login` | No | Autentica, set cookies | Redirect `/miembro/` o 401 |
| POST | `/miembro/logout` | Sí | Revoca refresh, limpia cookies | Redirect `/miembro/login` |
| POST | `/miembro/refresh` | Cookie | Renueva access token | 200 + nuevas cookies |
| GET | `/miembro/` | Sí | Dashboard HTML | HTML |
| GET | `/miembro/dashboard/data` | Sí | JSON para Alpine.js | `{color_mora, proxima_cuota, saldo_favor, ...}` |
| GET | `/miembro/estado-cuenta` | Sí | HTML tabla paginada | HTML |
| GET | `/miembro/estado-cuenta/data` | Sí | JSON paginado | `{items: [], total, page, per_page}` |
| GET | `/miembro/comprobantes` | Sí | HTML grid | HTML |
| GET | `/miembro/comprobantes/data` | Sí | JSON paginado | `{items: [], total, page, per_page}` |
| GET | `/miembro/comprobantes/{id}/descargar` | Sí | Streaming desde Vault | `application/octet-stream` |
| GET | `/miembro/comprobantes/{id}/ver` | Sí | Inline view (PDF/imagen) | `inline; filename=...` |
| GET | `/miembro/avisos` | Sí | HTML lista | HTML |
| GET | `/miembro/avisos/data` | Sí | JSON paginado | `{items: [], total, page, per_page}` |
| PATCH | `/miembro/avisos/{id}/leer` | Sí | Marcar leída | 200 `{leida: true}` |
| GET | `/miembro/perfil` | Sí | HTML solo lectura | HTML |
| GET | `/miembro/perfil/data` | Sí | JSON datos perfil | `{nombre, email, rut, categoria, ...}` |
| POST | `/miembro/categoria/solicitar` | Sí | Crea solicitud | 201 `{id, estado: "PENDIENTE"}` |
| POST | `/miembro/password/olvido` | No | Request reset token | 200 (siempre, anti-enumeración) |
| POST | `/miembro/password/reset` | No | Reset con token | 200 / 400 |
| GET | `/miembro/vapid-public` | Sí | Clave pública VAPID | `{"public_key": "..."}` |
| GET | `/miembro/manifest.json` | No | PWA Manifest | `application/manifest+json` |
| GET | `/miembro/sw.js` | No | Service Worker | `application/javascript` |

## Schemas Pydantic (API JSON)

```python
# app/schemas/portal.py
from pydantic import BaseModel, EmailStr
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Literal
from enum import Enum

class ColorMora(str, Enum):
    VERDE = "VERDE"
    NARANJO = "NARANJO"
    ROJO = "ROJO"

class CuotaResumen(BaseModel):
    mes: str  # "2025-01"
    categoria: Literal["MATRICULA", "ESTANDAR", "ACTIVA"]
    monto: int
    estado: Literal["PAGADA", "PENDIENTE", "PARCIAL", "EXENTA", "NEGOCIADA"]
    fecha_pago: Optional[date] = None
    comprobante_id: Optional[int] = None

class DashboardData(BaseModel):
    color_mora: ColorMora
    proxima_cuota: Optional[CuotaResumen] = None
    saldo_favor: int
    total_deuda: int
    comprobantes_pendientes: int
    avisos_no_leidos: int

class ComprobanteItem(BaseModel):
    id: int
    fecha_subida: datetime
    tipo: Literal["COMPROBANTE", "BOLETA"]
    mime_type: str
    tamano_bytes: int
    estado: Literal["PENDIENTE", "VALIDADO", "RECHAZADO"]
    monto_declarado: Optional[int] = None
    observaciones: Optional[str] = None

class AvisoItem(BaseModel):
    id: int
    tipo: str
    titulo: str
    cuerpo: str
    leida: bool
    creado_en: datetime
    metadata: Optional[dict] = None

class PerfilData(BaseModel):
    nombre_completo: str
    email: EmailStr
    rut: Optional[str] = None
    telefono: Optional[str] = None
    categoria_actual: Literal["ACTIVO", "ESTANDAR", "EXENTO", "RETIRADO"]
    fecha_ingreso: date
    matriculado: bool
    cuenta_bancaria_club: str  # Solo para mostrar, no editable

class SolicitudCambioCategoriaIn(BaseModel):
    categoria_nueva: Literal["ACTIVO", "ESTANDAR"]
    motivo: Optional[str] = None

class SolicitudCambioCategoriaOut(BaseModel):
    id: int
    estado: Literal["PENDIENTE", "APROBADA", "RECHAZADA"]
    creado_en: datetime
```

## UI/UX Especificaciones (Tailwind + Alpine.js)

### Layout Base (`_base.html`)

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="theme-color" content="#dc2626">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="Osorno Runners">
  <link rel="manifest" href="/miembro/manifest.json">
  <link rel="apple-touch-icon" href="/static/images/logo-192.png">
  <title>{% block title %}Osorno Runners{% endblock %}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.13.3/dist/cdn.min.js"></script>
  <link rel="stylesheet" href="/static/css/miembro.css">
  {% block head_extra %}{% endblock %}
</head>
<body class="bg-gray-50 min-h-screen" x-data="portalApp()">
  <!-- Service Worker Registration -->
  <script>
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/miembro/sw.js')
        .then(reg => console.log('SW registered:', reg.scope))
        .catch(err => console.log('SW registration failed:', err));
    }
  </script>
  
  {% block content %}{% endblock %}
  
  <!-- Bottom Nav (Mobile) -->
  <nav class="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 md:hidden z-50" x-show="!isLoginPage">
    <div class="grid grid-cols-4">
      <a href="/miembro/" class="nav-item" :class="{'active': activeTab==='dashboard'}" @click.prevent="activeTab='dashboard'">
        <svg class="w-6 h-6 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"></path></svg>
        <span class="text-xs">Inicio</span>
      </a>
      <a href="/miembro/estado-cuenta" class="nav-item" :class="{'active': activeTab==='cuenta'}">
        <svg class="w-6 h-6 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
        <span class="text-xs">Cuenta</span>
      </a>
      <a href="/miembro/comprobantes" class="nav-item" :class="{'active': activeTab==='comprobantes'}">
        <svg class="w-6 h-6 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path></svg>
        <span class="text-xs">Comprob.</span>
      </a>
      <a href="/miembro/avisos" class="nav-item" :class="{'active': activeTab==='avisos'}">
        <svg class="w-6 h-6 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path></svg>
        <span class="text-xs">Avisos</span>
      </a>
    </div>
  </nav>
  
  <script src="/static/js/miembro.js"></script>
  {% block scripts %}{% endblock %}
</body>
</html>
```

### Dashboard (`dashboard.html`)

```html
{% extends "miembro/_base.html" %}
{% block title %}Dashboard - Osorno Runners{% endblock %}

{% block content %}
<div class="min-h-screen pb-20 md:pb-0">
  <!-- Header -->
  <header class="bg-red-600 text-white p-4 md:p-6">
    <div class="max-w-4xl mx-auto flex items-center justify-between">
      <div>
        <h1 class="text-xl md:text-2xl font-bold">Osorno Runners</h1>
        <p class="text-red-100 text-sm mt-1">Portal del Miembro</p>
      </div>
      <div class="text-right">
        <p class="text-sm opacity-90" x-text="usuarioNombre"></p>
        <p class="text-xs opacity-70" x-text="categoriaActual"></p>
      </div>
    </div>
  </header>
  
  <main class="max-w-4xl mx-auto px-4 py-6">
    <!-- Estado Mora Badge -->
    <div class="mb-6">
      <div class="flex items-center gap-3 p-4 bg-white rounded-xl shadow-sm border border-gray-200">
        <div class="w-16 h-16 rounded-full flex items-center justify-center" 
             :class="colorMoraClass">
          <span class="text-2xl font-bold text-white" x-text="colorMoraChar"></span>
        </div>
        <div>
          <p class="text-sm text-gray-500">Estado de Cuota</p>
          <p class="text-xl font-semibold text-gray-900" x-text="colorMoraLabel"></p>
          <p class="text-xs text-gray-400 mt-1" x-text="colorMoraDetail"></p>
        </div>
      </div>
    </div>
    
    <!-- KPI Cards -->
    <div class="grid grid-cols-2 gap-3 mb-6">
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">Próxima Cuota</p>
        <p class="text-2xl font-bold text-gray-900 mt-1" x-text="proximaCuotaMonto | clp"></p>
        <p class="text-xs text-gray-400" x-text="proximaCuotaFecha"></p>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">Saldo a Favor</p>
        <p class="text-2xl font-bold text-green-600 mt-1" x-text="saldoFavor | clp"></p>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">Deuda Total</p>
        <p class="text-2xl font-bold text-red-600 mt-1" x-text="deudaTotal | clp"></p>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <p class="text-sm text-gray-500">Comprob. Pendientes</p>
        <p class="text-2xl font-bold text-yellow-600 mt-1" x-text="comprobantesPendientes"></p>
      </div>
    </div>
    
    <!-- Acciones Rápidas -->
    <div class="grid grid-cols-2 gap-3 mb-6">
      <a href="/miembro/estado-cuenta" class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center hover:border-red-300 transition">
        <svg class="w-8 h-8 mx-auto text-red-600 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
        <p class="font-medium text-gray-900">Estado de Cuenta</p>
        <p class="text-xs text-gray-500 mt-1">Ver historial completo</p>
      </a>
      <a href="/miembro/comprobantes" class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center hover:border-red-300 transition">
        <svg class="w-8 h-8 mx-auto text-blue-600 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path></svg>
        <p class="font-medium text-gray-900">Mis Comprobantes</p>
        <p class="text-xs text-gray-500 mt-1">{{ comprobantesPendientes }} pendientes</p>
      </a>
      <a href="/miembro/avisos" class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center hover:border-red-300 transition">
        <svg class="w-8 h-8 mx-auto text-yellow-600 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path></svg>
        <p class="font-medium text-gray-900">Avisos</p>
        <p class="text-xs text-gray-500 mt-1">{{ avisosNoLeidos }} sin leer</p>
      </a>
      <a href="/miembro/perfil" class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center hover:border-red-300 transition">
        <svg class="w-8 h-8 mx-auto text-gray-600 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>
        <p class="font-medium text-gray-900">Mi Perfil</p>
        <p class="text-xs text-gray-500 mt-1">Datos y categoría</p>
      </a>
    </div>
  </main>
</div>
{% endblock %}
```

### Alpine.js App (`static/js/miembro.js`)

```javascript
// static/js/miembro.js
function portalApp() {
  return {
    // Estado global
    usuarioNombre: '',
    categoriaActual: '',
    colorMora: 'VERDE',
    colorMoraChar: '✓',
    colorMoraLabel: 'Al día',
    colorMoraDetail: 'Sin deudas pendientes',
    colorMoraClass: 'bg-green-500',
    proximaCuotaMonto: 0,
    proximaCuotaFecha: '',
    saldoFavor: 0,
    deudaTotal: 0,
    comprobantesPendientes: 0,
    avisosNoLeidos: 0,
    activeTab: 'dashboard',
    isLoginPage: window.location.pathname.includes('/login'),
    
    // API Client
    apiBase: '/miembro',
    
    async init() {
      // Verificar auth en cada carga (excepto login)
      if (!this.isLoginPage) {
        await this.loadDashboard();
      }
      
      // Detectar tab activa por URL
      const path = window.location.pathname;
      if (path.includes('/estado-cuenta')) this.activeTab = 'cuenta';
      else if (path.includes('/comprobantes')) this.activeTab = 'comprobantes';
      else if (path.includes('/avisos')) this.activeTab = 'avisos';
      else if (path.includes('/perfil')) this.activeTab = 'perfil';
    },
    
    async apiGet(endpoint) {
      const resp = await fetch(`${this.apiBase}${endpoint}`, {
        credentials: 'include', // Cookies HttpOnly
        headers: { 'Accept': 'application/json' }
      });
      if (resp.status === 401) {
        // Intentar refresh
        const refreshed = await this.refreshToken();
        if (refreshed) return this.apiGet(endpoint);
        window.location.href = '/miembro/login';
        return null;
      }
      return resp.json();
    },
    
    async refreshToken() {
      const resp = await fetch(`${this.apiBase}/refresh`, {
        method: 'POST',
        credentials: 'include'
      });
      return resp.ok;
    },
    
    async loadDashboard() {
      const data = await this.apiGet('/dashboard/data');
      if (!data) return;
      
      this.usuarioNombre = data.nombre || '';
      this.categoriaActual = data.categoria || '';
      this.updateColorMora(data.color_mora);
      this.proximaCuotaMonto = data.proxima_cuota?.monto || 0;
      this.proximaCuotaFecha = data.proxima_cuota?.fecha_vencimiento ? this.formatDate(data.proxima_cuota.fecha_vencimiento) : '—';
      this.saldoFavor = data.saldo_favor || 0;
      this.deudaTotal = data.deuda_total || 0;
      this.comprobantesPendientes = data.comprobantes_pendientes || 0;
      this.avisosNoLeidos = data.avisos_no_leidos || 0;
    },
    
    updateColorMora(color) {
      this.colorMora = color;
      const config = {
        VERDE: { char: '✓', label: 'Al día', detail: 'Sin deudas pendientes', class: 'bg-green-500' },
        NARANJO: { char: '⚠', label: 'Con deuda (≤3 meses)', detail: 'Regularice antes del corte', class: 'bg-orange-500' },
        ROJO: { char: '✕', label: 'Moroso (>3 meses)', detail: 'Contacte a Tesorería', class: 'bg-red-500' }
      };
      const c = config[color] || config.VERDE;
      this.colorMoraChar = c.char;
      this.colorMoraLabel = c.label;
      this.colorMoraDetail = c.detail;
      this.colorMoraClass = c.class;
    },
    
    formatDate(dateStr) {
      const d = new Date(dateStr + 'T00:00:00');
      return d.toLocaleDateString('es-CL', { day: '2-digit', month: '2-digit', year: 'numeric' });
    },
    
    // Filtros para templates
    clp(value) {
      if (value === null || value === undefined) return '$0';
      return new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', minimumFractionDigits: 0 }).format(value);
    }
  };
}

// Registrar filtros globales para Alpine
document.addEventListener('alpine:init', () => {
  Alpine.magic('clp', () => (value) => {
    if (value === null || value === undefined) return '$0';
    return new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', minimumFractionDigits: 0 }).format(value);
  });
});
```

## Tests Requeridos

### Unitarios (`tests/test_portal_miembro.py`)

```python
def test_dashboard_data_color_mora_verde(client, miembro_al_dia, tesorero_auth):
    # Miembro al día → color VERDE
    resp = client.get("/miembro/dashboard/data", headers=miembro_al_dia_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["color_mora"] == "VERDE"
    assert data["deuda_total"] == 0

def test_dashboard_data_color_mora_naranjo(client, miembro_deuda_2_meses, miembro_headers):
    # Deuda 2 meses → NARANJO
    resp = client.get("/miembro/dashboard/data", headers=miembro_headers)
    assert resp.json()["color_mora"] == "NARANJO"

def test_dashboard_data_color_mora_rojo(client, miembro_deuda_4_meses, miembro_headers):
    # Deuda 4 meses → ROJO
    resp = client.get("/miembro/dashboard/data", headers=miembro_headers)
    assert resp.json()["color_mora"] == "ROJO"

def test_estado_cuenta_paginacion(client, miembro_con_historial, miembro_headers):
    # Página 1 (20 items)
    resp = client.get("/miembro/estado-cuenta/data?page=1&per_page=20", headers=miembro_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) <= 20
    assert data["page"] == 1
    assert data["total"] == 45  # total en fixture

def test_comprobantes_solo_propios(client, miembro_a, miembro_b, comprobante_a, comprobante_b):
    # Miembro A solo ve sus comprobantes
    resp = client.get("/miembro/comprobantes/data", headers=miembro_a_headers)
    ids = [c["id"] for c in resp.json()["items"]]
    assert comprobante_a.id in ids
    assert comprobante_b.id not in ids

def test_descargar_comprobante_propietario(client, miembro_a, comprobante_a, miembro_a_headers):
    resp = client.get(f"/miembro/comprobantes/{comprobante_a.id}/descargar", headers=miembro_a_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"

def test_descargar_comprobante_ajeno_403(client, miembro_a, comprobante_b, miembro_a_headers):
    resp = client.get(f"/miembro/comprobantes/{comprobante_b.id}/descargar", headers=miembro_a_headers)
    assert resp.status_code == 403

def test_aviso_marcar_leido(client, miembro_a, aviso_no_leido, miembro_a_headers):
    resp = client.patch(f"/miembro/avisos/{aviso_no_leido.id}/leer", headers=miembro_a_headers)
    assert resp.status_code == 200
    assert resp.json()["leida"] is True
    
    # Verificar en BD
    db.refresh(aviso_no_leido)
    assert aviso_no_leido.leida is True
    assert aviso_no_leido.leida_en is not None

def test_solicitud_cambio_categoria_crea_registro(client, miembro_activo, miembro_headers):
    resp = client.post("/miembro/categoria/solicitar", 
                       json={"categoria_nueva": "ESTANDAR", "motivo": "Cambio laboral"},
                       headers=miembro_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["estado"] == "PENDIENTE"
    assert data["categoria_solicitada"] == "ESTANDAR"

def test_rate_limit_login(client):
    # 10 requests → 429
    for i in range(10):
        client.post("/miembro/login", data={"email": "test@test.cl", "password": "wrong"})
    resp = client.post("/miembro/login", data={"email": "test@test.cl", "password": "wrong"})
    assert resp.status_code == 429

def test_jwt_cookies_httponly_secure(client, miembro_valido):
    resp = client.post("/miembro/login", data={"email": miembro_valido.email, "password": "correcto"})
    assert resp.status_code == 200
    cookies = resp.headers.get("set-cookie", "")
    assert "HttpOnly" in cookies
    assert "Secure" in cookies
    assert "SameSite=Strict" in cookies
    assert "access=" in cookies
    assert "refresh=" in cookies
```

### Integración PWA (`tests/test_pwa.py`)

```python
def test_manifest_json_valido(client):
    resp = client.get("/miembro/manifest.json")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/manifest+json"
    manifest = resp.json()
    assert manifest["name"] == "Osorno Runners"
    assert manifest["short_name"] == "OR"
    assert manifest["start_url"] == "/miembro/"
    assert manifest["display"] == "standalone"
    assert manifest["theme_color"] == "#dc2626"
    assert len(manifest["icons"]) >= 2
    assert any(i["sizes"] == "192x192" for i in manifest["icons"])
    assert any(i["sizes"] == "512x512" for i in manifest["icons"])

def test_service_worker_servido(client):
    resp = client.get("/miembro/sw.js")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/javascript"
    content = resp.text
    assert "CACHE_STATIC" in content
    assert "cacheFirst" in content
    assert "networkFirstWithTimeout" in content
    assert "staleWhileRevalidate" in content

def test_offline_page_existe(client):
    resp = client.get("/offline.html")
    assert resp.status_code == 200
    assert "sin conexión" in resp.text.lower()

def test_pwa_installable_criteria(client):
    # Verificar headers necesarios para instalabilidad
    resp = client.get("/miembro/")
    assert resp.status_code == 200
    # HTTPS se verifica en entorno real (mkcert local)
    # Manifest link en HTML
    assert 'rel="manifest"' in resp.text
    assert 'href="/miembro/manifest.json"' in resp.text
    # Theme color
    assert 'name="theme-color"' in resp.text
    assert 'content="#dc2626"' in resp.text
```

### E2E Flujo Completo (`tests/test_portal_e2e.py`)

```python
def test_flujo_login_dashboard_estado_cuenta(client, miembro_valido):
    # 1. Login
    resp = client.post("/miembro/login", data={
        "email": miembro_valido.email,
        "password": "password123"
    }, follow_redirects=False)
    assert resp.status_code == 302  # Redirect a dashboard
    assert resp.headers["location"] == "/miembro/"
    
    # Extraer cookies
    cookies = resp.headers.get("set-cookie", "")
    headers = {"Cookie": cookies}
    
    # 2. Dashboard HTML
    resp = client.get("/miembro/", headers=headers)
    assert resp.status_code == 200
    assert "Osorno Runners" in resp.text
    assert "Portal del Miembro" in resp.text
    
    # 3. Dashboard Data (JSON)
    resp = client.get("/miembro/dashboard/data", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "color_mora" in data
    assert "proxima_cuota" in data
    
    # 4. Estado de Cuenta HTML
    resp = client.get("/miembro/estado-cuenta", headers=headers)
    assert resp.status_code == 200
    assert "Estado de Cuenta" in resp.text
    
    # 5. Estado de Cuenta Data
    resp = client.get("/miembro/estado-cuenta/data", headers=headers)
    assert resp.status_code == 200
    assert "items" in resp.json()
    
    # 6. Logout
    resp = client.post("/miembro/logout", headers=headers, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/miembro/login"
    # Cookies limpiadas
    assert "access=;" in resp.headers.get("set-cookie", "")
    assert "refresh=;" in resp.headers.get("set-cookie", "")

def test_refresh_token_automatico(client, miembro_valido):
    # Login
    resp = client.post("/miembro/login", data={"email": miembro_valido.email, "password": "password123"})
    cookies = resp.headers.get("set-cookie", "")
    headers = {"Cookie": cookies}
    
    # Simular access token expirado (manipulando cookie o mock time)
    # En test real: freezer time + 20 min
    # Aquí verificamos que endpoint refresh funciona
    refresh_cookie = [c for c in cookies.split("; ") if c.startswith("refresh=")][0]
    refresh_headers = {"Cookie": refresh_cookie}
    
    resp = client.post("/miembro/refresh", headers=refresh_headers)
    assert resp.status_code == 200
    new_cookies = resp.headers.get("set-cookie", "")
    assert "access=" in new_cookies
    assert "refresh=" in new_cookies  # Rotativo
```

## Checklist de Implementación

### Modelos y Migración
- [ ] Crear `app/models/portal.py` con 4 modelos nuevos
- [ ] Migración Alembic: `alembic revision --autogenerate -m "add portal miembro models"`
- [ ] Índices compuestos creados correctamente

### Autenticación Miembro
- [ ] `app/core/auth_miembro.py`: `create_access_token`, `create_refresh_token`, `verify_token`, `revoke_refresh_token`
- [ ] Dependency `get_current_miembro` en `app/dependencies.py`
- [ ] Rate-limiter específico miembro (10 login/min, 60 api/min)
- [ ] Login/Logout/Refresh endpoints en `app/routers/miembro.py`
- [ ] Recuperación contraseña: token JWT 1h + email plantilla (reutiliza `PlantillaCorreo`)

### Router y Endpoints
- [ ] `app/routers/miembro.py` con 18 endpoints listados
- [ ] Schemas Pydantic en `app/schemas/portal.py`
- [ ] Validación ownership en descarga comprobantes (FK miembro_id)
- [ ] Paginación keyset para listas > 1000 items

### Servicios
- [ ] `app/services/portal_miembro.py` con 5 funciones de vistas agregadas
- [ ] `app/services/notificaciones_miembro.py`: crear notificaciones desde eventos (pago validado, comprobante rechazado, etc.)
- [ ] Reutilizar `services/miembros.py`, `pagos.py` con `selectinload` optimizado

### Templates y Static
- [ ] `templates/miembro/_base.html` + 7 templates vistas
- [ ] `static/css/miembro.css`: utilidades + animaciones + print styles
- [ ] `static/js/miembro.js`: Alpine.js app + API client + filtros
- [ ] `static/js/sw.js`: Service Worker completo
- [ ] `manifest.json` + icons (192, 512) + `offline.html`
- [ ] Responsive testado: 375px, 768px, 1024px, 1440px

### PWA Checklist
- [ ] HTTPS local con `mkcert` (`.localhost` certificates)
- [ ] Manifest válido (PWA Builder / Lighthouse)
- [ ] SW registrado y funcional (DevTools Application tab)
- [ ] Install prompt aparece en Chrome/Edge móvil
- [ ] Offline: dashboard + estado-cuenta cargan desde cache
- [ ] Icons maskable para Android adaptive icons

### Seguridad
- [ ] CSP headers en responses portal
- [ ] HSTS, X-Frame-Options, X-Content-Type-Options
- [ ] Auditoría logs: login, vista cuenta, descarga, solicitud categoría
- [ ] Rate-limit por IP + usuario (Redis preferido, in-memory fallback)
- [ ] Bloqueo 5 intentos fallidos → 15 min

### Tests
- [ ] Unitarios: `tests/test_portal_miembro.py` (≥12 tests)
- [ ] PWA: `tests/test_pwa.py` (≥4 tests)
- [ ] E2E: `tests/test_portal_e2e.py` (≥3 tests)
- [ ] `pytest -q` → **all passed**
- [ ] `ruff check app tests` → **All checks passed!**

### Documentación
- [ ] Actualizar `02-DOCS/wiki/operacion.md` con sección "Portal Miembro"
- [ ] Documentar configuración HTTPS local (`mkcert -install && mkcert localhost`)
- [ ] Documentar flujo recuperación contraseña
- [ ] Capturas de pantalla mobile/desktop para wiki

## Evidence Requerida

- `pytest tests/test_portal_miembro.py tests/test_pwa.py tests/test_portal_e2e.py -q` → **X passed**
- `ruff check app tests` → **All checks passed!**
- Lighthouse PWA score ≥ 90 (Performance, Accessibility, Best Practices, SEO, PWA)
- Manual test: Login → Dashboard → Estado Cuenta → Comprobantes → Avisos → Perfil → Logout en Chrome móvil (DevTools device toolbar)
- Manual test: Instalar PWA en Android/iOS → Funciona offline (dashboard cacheado)

## Next

1. Crear rama `portal-movil-pwa`
2. Implementar en orden: models → auth → router → service → templates → static → PWA → tests
3. Configurar `mkcert` para HTTPS local en `02-DOCS/wiki/operacion.md`
4. Commitear y abrir PR para revisión
5. Merge a `main` tras approval
6. **Desbloquea:** FT-02 Carga Comprobantes, FT-04 Recibos Email, FT-09 Push, FT-10 Gastos Comunes