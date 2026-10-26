---
type: article
title: Reglas de negocio del club
description: Las reglas del dominio (cuotas, activación, mora, imputación, exenciones, negociación, finanzas) que la aplicación debe cumplir.
tags: [dominio, reglas, pagos, morosidad]
timestamp: 2026-10-26T23:32:00Z
topic: proyecto
status: stable
sources: ["[AGENT](../../raw/proyecto/agent-contexto-y-requisitos.md)", "[SPECS](../../raw/proyecto/especificaciones-funcionales-mvp.md)"]
score: 9.0
---

# Reglas de negocio del club

> Sources: specs/AGENT.md; specs/SPECS.md
> Raw: [Contexto y requisitos](../../raw/proyecto/agent-contexto-y-requisitos.md); [Especificaciones del MVP](../../raw/proyecto/especificaciones-funcionales-mvp.md)

## Overview

Este artículo destila las reglas de negocio (RN-*) que la aplicación implementa. El texto normativo completo y verificable vive en [specs/SPECS.md](../../../specs/SPECS.md) (sección 8); aquí queda la síntesis que el agente debe tener en mente antes de tocar cualquier módulo.

## Cuotas y activación

- **Niveles de cuota (RN-01):** Matrícula 5.000 CLP (pago único de incorporación); Membresía Estándar 5.000 CLP/mes (opción de apoyo, sin entrenamiento); Membresía Activa 15.000 CLP/mes (alumnos).
- **Activación (RN-02):** el miembro pasa a **Activo** al completar **Matrícula + la cuota de su categoría**. La Matrícula se omite si ya está **matriculado** o ingresó **antes del 01/09/2025** (RN-27).
- **Corte al día 5 (RN-03):** el pago registrado después del día 5 se imputa al **ciclo siguiente**.
- **Categorías:** el miembro puede cambiar entre **Activo** (alumno) y **Membresía** (apoyo); cada cambio queda registrado en el historial.

## Pagos personalizados e imputación

- **Monto libre (RN-09):** se acepta cualquier monto; puede cubrir varias cuotas y cruzar años, indicando año y meses (F-12).
- **Orden de imputación (RN-17):** **deuda más antigua → meses/año indicados → abono**.
- **Abono (RN-18):** el excedente queda como **saldo a favor** y se aplica **automáticamente** a la siguiente cuota.
- **Unicidad (RN-08):** no se duplica el pago de un mismo miembro, tipo de cuota y ciclo.
- **Observaciones:** todo pago admite notas libres.

## Morosidad y negociación

- **Mora (RN-04):** la cuota impaga del mes **acumula deuda** y el miembro pasa a **Moroso**, conservando el acceso de consulta a su estado de cuenta.
- **Colores (RN-21/F-22):** rojo (desierto), **verde** (al día), **naranjo** (deuda hasta 3 meses), **rojo** (más de 3 meses).
- **Negociación (F-24/RN-26):** para morosos de **más de 6 meses**, con **descuento en % editable**; deuda negociada deja de contar para el color en estado "aceptada".

## Exenciones y avisos

- **Exención (RN-05):** beados, invitados/influencers y retirados **no generan cobro ni avisos** mientras dure la condición; su cuota figura como **exenta**, nunca como deuda.
- **Avisos manuales (RN-13):** el sistema **no** envía correos; **avisa al Tesorero** en la plataforma y le ofrece la **plantilla** (datos del alumno, morosidad, adeudado y cuenta para transferir).

## Finanzas, compras y forma

- **Egresos:** todo egreso lleva **categoría** (base fija: Activos, Gastos fijos, Transferencias, Tarjeta, Otros — más personalizadas).
- **Activos:** bienes del club con **miembro encargado** de gestionar la compra (sin cobro a su persona).
- **Gastos fijos:** recurrentes mensuales (sueldo del profesor, mantención de cuenta corriente).
- **Compras y reventa (F-25):** la compra del club genera **cargos separados** a los alumnos; **no afectan la morosidad de cuotas**.
- **Forma:** dinero como **entero CLP** (nunca float); todo texto en español RAA/UTF-8 correcto; **correo electrónico** es el identificador único del miembro (RN-11); trazabilidad fecha/monto/categoría en cada movimiento (RN-15).

## Related

- [Visión y alcance](./vision.md) — quién es quien y qué se busca con estas reglas.
- [Arquitectura por capas](./arquitectura.md) — dónde vive cada regla (services).
