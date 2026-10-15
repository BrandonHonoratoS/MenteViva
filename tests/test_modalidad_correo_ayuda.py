"""Modalidad "Prepárate 5 minutos" (RRHH o la persona), racha diaria, recordatorios del programador, avisos por correo y página de Ayuda."""
from __future__ import annotations

from app import correo, db, scheduler
from app.config import settings
from tests.conftest import Sesion
from tests.test_laboratorio import _colaborador_con_diagnostico


def test_modalidad_racha_recordatorios_correo_y_ayuda(client, stub):
    leo = _colaborador_con_diagnostico(client, stub, "leo@condor.mx", "Leo Micro")
    uid = leo.u["id"]
    rrhh = Sesion(client, "rrhh@condor.mx", "NuevaClaveRRHH1")
    # 1) la persona elige su modalidad en Mi cuenta mientras RRHH no la fije
    r = leo.post("/cuenta/preferencias", {"modalidad": "micro", "correo_notif": "1"})
    assert r.status_code == 303 and db.usuario(uid)["modalidad"] == "micro"
    assert "Prepárate 5 minutos" in leo.get("/hoy").text and "0 de 3 bloques" in leo.get("/hoy").text
    # la decide sólo la persona: RRHH no puede fijarla (el campo se ignora), y puede cambiarla cuando quiera
    r = rrhh.post(f"/gestion/usuarios/{uid}", {"nombre": "Leo Micro", "puesto": "Consultor", "rol": "colaborador", "area_id": str(leo.u["area_id"]), "modalidad": "completa"})
    assert r.status_code == 303 and db.usuario(uid)["modalidad"] == "micro"
    leo.post("/cuenta/preferencias", {"modalidad": "completa", "correo_notif": "1"})
    assert db.usuario(uid)["modalidad"] == "completa"
    leo.post("/cuenta/preferencias", {"modalidad": "micro", "correo_notif": "1"})
    assert db.usuario(uid)["modalidad"] == "micro" and "exactamente los mismos" in leo.get("/cuenta").text
    # 2) bloques y racha
    r = leo.api("/api/actividad/bloque")
    assert r.status_code == 200 and r.json()["bloques_hoy"] == 1 and r.json()["racha"] == 1
    assert db.racha_dias(uid)["hoy"] and "1 de 3 bloques" in leo.get("/hoy").text
    # 3) recordatorio del programador: sólo a quien le falta el bloque de la franja
    antes = len(db.notificaciones(uid))
    n = scheduler.correr_micro(settings.MICRO_HORAS[0])          # franja 1: Leo ya tiene 1 bloque → no se le avisa
    assert n == 0 and len(db.notificaciones(uid)) == antes
    n = scheduler.correr_micro(settings.MICRO_HORAS[1])          # franja 2: le falta → aviso con racha y enlace al siguiente paso
    assert n >= 1
    ultimo = db.notificaciones(uid)[0]
    assert ultimo["titulo"].startswith("Prepárate 5 minutos (2/3)") and "racha de 1 día" in ultimo["titulo"] and ultimo["enlace"]
    # 4) el aviso salió también por correo (modo prueba: se registra sin SMTP) y se respeta la preferencia
    assert any(c["a"] == "leo@condor.mx" and c["titulo"].startswith("Prepárate 5 minutos") for c in correo.ENVIADOS_PRUEBA)
    leo.post("/cuenta/preferencias", {"correo_notif": ""})
    assert db.usuario(uid)["correo_notif"] == 0
    correo.ENVIADOS_PRUEBA.clear()
    db.notificar(uid, "Aviso sin correo", "x", "/hoy")
    assert not correo.ENVIADOS_PRUEBA
    # 5) Ayuda con contacto de soporte y acceso desde la barra; prueba de correo en Admin informa que falta SMTP
    r = leo.get("/ayuda")
    assert r.status_code == 200 and "Brandon Honorato" in r.text and "brandon.honorato@i-condor.com" in r.text and "wa.me/525519521615" in r.text
    assert 'href="/ayuda"' in leo.get("/hoy").text
    assert "Como Recursos Humanos" in rrhh.get("/ayuda").text
    admin = Sesion(client, "admin@menteviva.mx", "SuperClave123")
    r = admin.post("/admin/correo/probar", {"destinatario": ""})
    assert r.status_code == 303 and "SMTP" in r.headers["location"]
    assert "no configurado" in admin.get("/admin").text
