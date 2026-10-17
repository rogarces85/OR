"""Utilidades compartidas para validar los formularios (T6.1, CA-21).

Los formularios del panel envían todos los valores como texto. Estas funciones
convierten y validan esos valores con mensajes en español, de modo que cada
router rechace los datos inválidos antes de tocar la base de datos.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.core.formato import parsear_clp

MESES_VALIDOS: tuple[int, ...] = tuple(range(1, 13))

# Etiquetas visibles de los campos, usadas al componer el mensaje de error.
ETIQUETAS_CAMPO: dict[str, str] = {
    "monto": "Monto",
    "costo": "Costo",
    "concepto": "Concepto",
    "descripcion": "Descripción",
    "proveedor": "Proveedor",
    "categoria_id": "Categoría",
    "miembro_responsable_id": "Miembro responsable",
    "fecha": "Fecha",
    "fecha_pago": "Fecha del pago",
    "anio": "Año",
    "mes": "Mes",
    "meses": "Meses",
    "medio": "Medio de pago",
    "observaciones": "Observaciones",
    "descuento_pct": "Descuento",
    "nombre": "Nombre",
    "items": "Ítems",
    "cantidad": "Cantidad",
    "precio_unitario_clp": "Precio unitario",
    "compra_item_id": "Ítem",
    "miembro_id": "Miembro",
}


def monto_clp(valor: Any) -> int:
    """Convierte un monto escrito por el usuario (``"45.000"``) en entero CLP."""
    if isinstance(valor, int):
        return valor
    return parsear_clp("" if valor is None else str(valor))


def monto_positivo(valor: Any) -> int:
    """Valida que un monto sea un entero positivo (sección 9 de SPECS)."""
    numero = int(valor)
    if numero <= 0:
        raise ValueError("El monto debe ser un entero positivo.")
    return numero


def entero(valor: Any) -> int:
    """Convierte un valor del formulario en entero, con mensaje en español."""
    texto = "" if valor is None else str(valor).strip()
    if not texto:
        raise ValueError("Este campo es obligatorio.")
    try:
        return int(texto)
    except (TypeError, ValueError) as exc:
        raise ValueError("El valor debe ser un número entero.") from exc


def entero_positivo(valor: Any) -> int:
    """Convierte y exige un entero mayor que cero."""
    numero = entero(valor)
    if numero <= 0:
        raise ValueError("El valor debe ser un entero positivo.")
    return numero


def entero_opcional(valor: Any) -> int | None:
    """Convierte un campo opcional: el texto vacío equivale a ``None``."""
    if valor is None:
        return None
    if isinstance(valor, str) and not valor.strip():
        return None
    return entero(valor)


def lista_enteros(valor: Any) -> list[int]:
    """Normaliza una selección múltiple (lista de textos) a enteros."""
    if valor is None:
        return []
    if isinstance(valor, (list, tuple, set)):
        return [entero(item) for item in valor]
    return [entero(valor)]


def fecha_opcional(valor: Any) -> Any:
    """Deja que Pydantic valide la fecha; el texto vacío equivale a ``None``."""
    if valor is None:
        return None
    if isinstance(valor, str) and not valor.strip():
        return None
    return valor


def _texto_de_error(campo: str, detalle: dict[str, Any]) -> str:
    """Construye el mensaje en español de un error de validación."""
    tipo = str(detalle.get("type", ""))
    if tipo == "missing":
        return "Este campo es obligatorio."
    if tipo == "value_error":
        # Los validadores propios ya entregan un mensaje claro en español.
        return str(detalle.get("msg", "")).replace("Value error, ", "")
    entrada = detalle.get("input")
    if isinstance(entrada, str) and not entrada.strip():
        return "Este campo es obligatorio."
    if tipo == "string_too_short":
        minimo = (detalle.get("ctx") or {}).get("min_length", 1)
        return f"Debe tener al menos {minimo} caracteres."
    if tipo == "string_too_long":
        maximo = (detalle.get("ctx") or {}).get("max_length", 1)
        return f"No puede superar los {maximo} caracteres."
    if tipo.startswith("date_"):
        return "Ingresa una fecha válida (formato AAAA-MM-DD)."
    if tipo in ("int_parsing", "int_type", "float_parsing", "float_type"):
        return "Ingresa un número entero."
    if tipo in ("greater_than", "greater_than_equal"):
        contexto = detalle.get("ctx") or {}
        limite = contexto.get("gt", contexto.get("ge", 0))
        return f"El valor debe ser mayor o igual a {limite}."
    if tipo in ("less_than", "less_than_equal"):
        contexto = detalle.get("ctx") or {}
        limite = contexto.get("lt", contexto.get("le", 0))
        return f"El valor debe ser menor o igual a {limite}."
    if campo == "email":
        return "Ingresa un correo electrónico válido."
    return "El valor ingresado no es válido."


def _campo_de(detalle: dict[str, Any]) -> str:
    """Devuelve el nombre del campo (ignora los índices de las listas)."""
    ubicacion = [p for p in (detalle.get("loc") or ()) if not isinstance(p, int)]
    return str(ubicacion[-1]) if ubicacion else ""


def mensajes_por_campo(error: ValidationError) -> dict[str, str]:
    """Traduce los errores de Pydantic a mensajes en español por campo (CA-16)."""
    mensajes: dict[str, str] = {}
    for detalle in error.errors():
        ubicacion = detalle.get("loc") or ()
        campo = str(ubicacion[0]) if ubicacion else "formulario"
        if campo in mensajes:
            continue
        mensajes[campo] = _texto_de_error(campo, detalle)
    return mensajes


def primer_mensaje(error: ValidationError) -> str:
    """Devuelve el primer error en español, precedido por el campo (CA-21)."""
    detalles = error.errors()
    if not detalles:
        return "Los datos ingresados no son válidos."
    detalle = detalles[0]
    campo = _campo_de(detalle)
    texto = _texto_de_error(campo, detalle)
    if str(detalle.get("type", "")) == "value_error":
        # Los validadores propios ya entregan una oración completa.
        return texto
    etiqueta = ETIQUETAS_CAMPO.get(campo)
    return f"{etiqueta}: {texto}" if etiqueta else texto
