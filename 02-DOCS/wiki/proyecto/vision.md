---
type: article
title: Visión y alcance
description: Qué es el Sistema Gestión Pagos Osorno Runners, el problema que resuelve, sus usuarios y su estado actual.
tags: [proyecto, vision, roles]
timestamp: 2026-10-26T23:32:00Z
topic: proyecto
status: stable
sources: ["[README](../../raw/proyecto/sistema-gestion-pagos-osorno-runners.md)", "[AGENT](../../raw/proyecto/agent-contexto-y-requisitos.md)", "[SPECS](../../raw/proyecto/especificaciones-funcionales-mvp.md)"]
score: 14.0
---

# Visión y alcance

> Sources: README.md del repositorio; specs/AGENT.md; specs/SPECS.md
> Raw: [README](../../raw/proyecto/sistema-gestion-pagos-osorno-runners.md); [Contexto y requisitos](../../raw/proyecto/agent-contexto-y-requisitos.md); [Especificaciones del MVP](../../raw/proyecto/especificaciones-funcionales-mvp.md)

## Overview

Sistema web operativo del club de running **Osorno Runners**: centraliza el ciclo completo de sus miembros — incorporación, activación, cobro de cuotas, morosidad por colores, negociación de deudas, ingresos y egresos, compras con cobro a alumnos y reportes consolidados. Su prioridad es la transparencia operativa para el Tesorero y una experiencia simple para el miembro. No es un sistema de gimnasio: está hecho para una comunidad de corredores.

## Problema y objetivo

Sin sistema centralizado, la gestión de membresías, cobros, morosidad y finanzas del club es difícil de auditar. **Objetivo:** plataforma integral que centralice la gestión financiera, administrativa y de membresía del club, de forma **fiable y local** (decisión de proyecto: sin acceso público por ahora).

## Usuarios y roles

| Rol | Alcance |
| :-- | :-- |
| **Administrador** | Control total del sistema (usuarios, cuotas, finanzas). |
| **Tesorero** | Ingresos/egresos, pagos personalizados, morosidad y reportes. |
| **Miembro** | Restringido: solo su perfil, su estado de cuenta y sus avisos. |

> Decisión D-7: **Admin y Tesorero tienen permisos iguales** en el MVP. El miembro nunca ve información de otros ni la financiera global del club (RN-06/RN-07).

## Identidad transversal

- **Moneda:** CLP, entero, separador de miles por punto, montos cerrados (D-23).
- **Paleta:** Rojo/Negro/Blanco consistente (F-29).
- **Idioma:** español con RAE estricta, UTF-8, tildes y "ñ" (RN-16).
- **Medios de pago:** transferencia; efectivo solo como excepción puntual.

## Estado del proyecto

- **MVP completo** (fases 1–10 de `specs/TASK.md`): 29 funcionalidades (F-01…F-29) cubiertas por la matriz de `specs/COBERTURA.md`.
- **Uso actual:** personal y local — Uvicorn en `127.0.0.1:8000` con MySQL/MariaDB de XAMPP. GitHub solo aloja código y documentación.
- **Post-MVP:** plan de publicación productiva (HTTPS, respaldos) cerrado documentalmente en `docs/POST_MVP.md`, **no ejecutado** (Q-3).

## Related

- [Reglas de negocio del club](./dominio.md) — el comportamiento concreto que el sistema obliga a cumplir.
- [Arquitectura por capas](./arquitectura.md) — cómo está construido para sostener esas reglas.
- [Operación local](./operacion.md) — cómo se instala, ejecuta y verifica.
- [Calidad, pruebas y aceptación](./calidad.md) — cómo se demuestra que funciona.
