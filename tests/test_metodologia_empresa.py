"""Estándares por empresa: una empresa que vende con AIDA y presenta breve. Sin estándar (Cóndor), los prompts quedan exactamente como antes."""
from __future__ import annotations

from app import db
from app.agents import estandares as ES
from app.llm import gemini
from tests.conftest import Sesion
from tests.test_laboratorio import _colaborador_con_diagnostico
from tests.test_socrates import LECCION


def test_estandar_de_empresa_en_avatares_socrates_y_base(client, stub):
    sofia = _colaborador_con_diagnostico(client, stub, "sofia.aida@condor.mx", "Sofía AIDA")   # deja a RRHH con su contraseña definitiva
    rrhh = Sesion(client, "rrhh@condor.mx", "NuevaClaveRRHH1")
    eid = rrhh.u["empresa_id"]
    # 0) sin estándar: el bloque es vacío y los prompts no cambian
    assert ES.bloque(eid, "ventas") == "" and ES.huella(eid, "ventas") == "mv" and not ES.tiene(eid)
    gemini.STUB_LLAMADAS.clear()
    r = sofia.post("/entrenar/ventas/iniciar", {"item": "0", "nivel": "Principiante", "competencia": ""})
    sid0 = int(r.headers["location"].rsplit("/", 1)[1])
    sistema0 = [x for x in gemini.STUB_LLAMADAS if x["origen"] == "celeste.apertura"][-1]["system"]
    assert "ESTÁNDAR DE" not in sistema0
    sofia.api(f"/api/sesiones/{sid0}/descartar")
    # 1) RRHH define la metodología de la empresa
    r = rrhh.get("/estandares")
    assert r.status_code == 200 and "Clínica de Ventas" in r.text and "Ruta Delivery Manager" in r.text
    r = rrhh.post("/estandares", {"general.comunicacion": "Presentaciones breves, poco texto y una gráfica por idea.", "general.cultura": "",
                                  "ventas.metodologia": "Vendemos con AIDA: Atención, Interés, Deseo, Acción. No usamos PRAINCODERECI.",
                                  "ventas.terminologia": "Al diagnóstico le llamamos sondeo.", "ventas.no_evaluar": "No exigir silencio activo.",
                                  "entrevistas.metodologia": "", "entrevistas.terminologia": "", "entrevistas.no_evaluar": ""})
    assert r.status_code == 303
    est = ES.de_empresa(eid)
    assert est["ventas"]["metodologia"].startswith("Vendemos con AIDA") and est["general"]["comunicacion"].startswith("Presentaciones breves") and not any(est["entrevistas"].values())
    assert "ESTÁNDAR DE" in ES.bloque(eid, "ventas") and "AIDA" in ES.bloque(eid, "ventas") and "sondeo" in ES.bloque(eid, "ventas") and ES.huella(eid, "ventas") != "mv"
    assert "AIDA" not in ES.bloque(eid, "entrevistas") and "Presentaciones breves" in ES.bloque(eid, "entrevistas")   # estilo general aplica a todas
    assert "Presentaciones breves" in ES.bloque(eid, None)
    # 2) Celeste (roleplay y feedback) recibe el estándar
    gemini.STUB_LLAMADAS.clear()
    r = sofia.post("/entrenar/ventas/iniciar", {"item": "0", "nivel": "Principiante", "competencia": ""})
    sid = int(r.headers["location"].rsplit("/", 1)[1])
    sistema = [x for x in gemini.STUB_LLAMADAS if x["origen"] == "celeste.apertura"][-1]["system"]
    assert "ESTÁNDAR DE" in sistema and "AIDA" in sistema and "No exigir silencio activo" in sistema
    sofia.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Buenos días, ¿me permite hacerle un sondeo?"})
    stub["celeste.turno"] = {"estado": "fin", "mensaje": "Me voy."}
    sofia.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Fin"})
    stub.pop("celeste.turno")
    fb = [x for x in gemini.STUB_LLAMADAS if x["origen"] == "celeste.feedback"][-1]["system"]
    assert "ESTÁNDAR DE" in fb and "AIDA" in fb and "sus etapas y criterios sustituyen" in fb
    # 3) Juan recibe sólo el estilo general; Sócrates enseña la metodología de la empresa y su base no se mezcla con la de Mente Viva
    from app.agents import socrates as S
    assert "AIDA" in S.materiales_internos("ventas", "", eid) and "ESTÁNDAR DE LA EMPRESA DE LA PERSONA" in S.materiales_internos("ventas", "", eid)
    assert "ESTÁNDAR" not in S.materiales_internos("ventas", "", None)
    clave, perfil = S.clave_base(db.usuario(sofia.u["id"]), "ventas", "Cierre y siguiente paso", "Principiante")
    assert perfil.endswith(ES.huella(eid, "ventas")) and not perfil.endswith(":mv")
    stub["socrates.investigar"] = "DOSSIER AIDA"; stub["socrates.leccion"] = LECCION
    gemini.STUB_LLAMADAS.clear()
    r = sofia.post("/socrates/estudiar", {"habilidad": "ventas", "tema": "Cierre y siguiente paso", "competencia": "", "item": "0"})
    assert db.leccion(int(r.headers["location"].rsplit("/", 1)[1]))["estado"] == "lista"
    assert "AIDA" in [x for x in gemini.STUB_LLAMADAS if x["origen"] == "socrates.leccion"][-1]["system"]
    # 4) el superadmin puede editar los estándares de cualquier empresa
    admin = Sesion(client, "admin@menteviva.mx", "SuperClave123")
    r = admin.get(f"/admin/empresas/{eid}/estandares")
    assert r.status_code == 200 and "Vendemos con AIDA" in r.text and "Metodología y estándares" in admin.get("/admin").text
    # limpiar para no afectar a otras pruebas
    ES.guardar(eid, {})
    assert not ES.tiene(eid)
