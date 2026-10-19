"""Aviso de morosidad y plantilla de correo (CA-15, CA-30, F-23)."""

from __future__ import annotations

from urllib.parse import unquote

from app.models.configuracion import ESTADO_AVISO_ENVIADO, ESTADO_AVISO_PENDIENTE
from app.repositories import configuracion as repo_configuracion
from app.services import correo as servicio_correo
from app.services.morosidad import MorosidadInfo

CUENTA = {
    "titular": "Olimpia Runners Osorno",
    "banco": "Banco Santander",
    "numero_cuenta": "72769929",
    "rut": "65.161.804-5",
    "correo": "tesoreriaor@gmail.com",
}


def _info(meses: int = 5) -> MorosidadInfo:
    return MorosidadInfo(
        miembro_id=1,
        meses_deuda=meses,
        monto_deuda_clp=meses * 15_000,
        color="rojo",
    )


def _cuenta(db):
    cuenta = repo_configuracion.crear_cuenta(db, **CUENTA)
    db.commit()
    return cuenta


def test_detalle_de_morosidad_y_datos(db, miembro_factory):
    miembro = miembro_factory()
    cuenta = _cuenta(db)
    info = _info(5)

    datos = servicio_correo.datos_de_plantilla(miembro, info, cuenta)

    assert datos["nombre"] == miembro.nombre_completo
    assert datos["meses"] == "5"
    assert datos["adeudado"] == "$ 75.000"
    assert datos["detalle"] == "5 mes(es) impago(s) por un total de $ 75.000."
    assert datos["titular"] == CUENTA["titular"]
    assert datos["banco"] == CUENTA["banco"]
    assert datos["cuenta"] == CUENTA["numero_cuenta"]
    assert datos["rut"] == CUENTA["rut"]
    assert datos["correo"] == CUENTA["correo"]


def test_plantilla_rellena_datos_del_alumno_y_cuenta(db, miembro_factory):
    """CA-30: los datos de la cuenta están en la plantilla de correo."""
    miembro = miembro_factory()
    cuenta = _cuenta(db)
    plantilla = repo_configuracion.crear_plantilla(
        db,
        nombre="Aviso",
        asunto="Cuota pendiente - {nombre}",
        cuerpo=(
            "Hola {nombre}: debes {adeudado}. Detalle: {detalle}. "
            "Transfiere a {titular} / {banco} / {cuenta} / {rut} / {correo}."
        ),
    )
    db.commit()

    asunto, cuerpo = servicio_correo.renderizar_plantilla(
        plantilla, miembro, _info(5), cuenta
    )

    assert asunto == f"Cuota pendiente - {miembro.nombre_completo}"
    assert "$ 75.000" in cuerpo
    for valor in CUENTA.values():
        assert valor in cuerpo


def test_sin_plantilla_usa_cuerpo_por_defecto(db, miembro_factory):
    miembro = miembro_factory()
    cuenta = _cuenta(db)

    asunto, cuerpo = servicio_correo.renderizar_plantilla(
        None, miembro, _info(2), cuenta
    )

    assert asunto == servicio_correo.ASUNTO_POR_DEFECTO
    assert miembro.nombre_completo in cuerpo
    assert "$ 30.000" in cuerpo
    assert CUENTA["correo"] in cuerpo


def test_enlace_mailto_contiene_asunto_y_cuerpo(db, miembro_factory):
    """CA-15: se ofrece un enlace mailto; el sistema no envía el correo solo."""
    miembro = miembro_factory()
    cuenta = _cuenta(db)
    asunto, cuerpo = servicio_correo.renderizar_plantilla(
        None, miembro, _info(3), cuenta
    )

    enlace = servicio_correo.generar_enlace_correo(
        "tesoreriaor@gmail.com", asunto, cuerpo
    )

    texto = unquote(enlace)
    assert texto.startswith("mailto:tesoreriaor@gmail.com?subject=")
    assert texto.count("subject=") == 1
    assert asunto in texto
    assert miembro.nombre_completo in texto


def test_marcar_aviso_como_enviado(db, miembro_factory):
    miembro = miembro_factory()
    aviso = repo_configuracion.crear_aviso(
        db, miembro_id=miembro.id, detalle="Aviso de prueba"
    )
    db.commit()
    assert aviso.estado == ESTADO_AVISO_PENDIENTE

    actualizado = servicio_correo.marcar_aviso_enviado(db, aviso)

    assert actualizado.estado == ESTADO_AVISO_ENVIADO
    assert actualizado.enviado_en is not None
