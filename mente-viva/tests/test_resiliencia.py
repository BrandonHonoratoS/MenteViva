"""Resiliencia ante fallos transitorios de Gemini: apertura pendiente, /continuar, cadena de modelos de respaldo."""
from __future__ import annotations

import types as _t

import pytest

from app import db
from app.llm import gemini
from app.llm.gemini import ErrorLLM, LLM
from tests.conftest import ONBOARDING_VENDEDOR, Sesion


def test_apertura_pendiente_y_continuar(client, stub, monkeypatch):
    rrhh = Sesion(client, "rrhh@condor.mx", "NuevaClaveRRHH1")
    r = rrhh.post("/gestion/usuarios", {"nombre": "Sofía Prueba", "email": "sofia@condor.mx", "puesto": "Consultora", "rol": "colaborador", "area_id": db.areas(rrhh.u["empresa_id"])[0]["id"]})
    clave = r.headers["location"].split("clave=")[1]
    sofia = Sesion(client, "sofia@condor.mx", clave)
    sofia.cambiar_password("ClaveSofia1234")
    assert sofia.api("/api/diagnostico/onboarding", {"respuestas": ONBOARDING_VENDEDOR}).status_code == 200

    # 1) la IA falla en la apertura → la sesión queda abierta sin mensajes y el botón lleva a ella (sin bucle)
    original = gemini.llm.generar
    def falla(**kw):
        raise ErrorLLM("El modelo de IA está saturado en este momento (alta demanda).")
    monkeypatch.setattr(gemini.llm, "generar", falla)
    r = sofia.post("/diagnostico/iniciar")
    assert r.status_code == 303 and "/sesion/" in r.headers["location"], r.text
    sid = int(r.headers["location"].rsplit("/", 1)[1])
    s = db.sesion(sid)
    assert s["estado"] == "en_curso" and db.mensajes(sid) == []
    assert sofia.get("/diagnostico").headers["location"].endswith(f"/sesion/{sid}")   # redirige a la sesión abierta
    assert sofia.post("/diagnostico/iniciar").headers["location"].endswith(f"/sesion/{sid}")
    # /continuar con la IA aún caída → 503 con mensaje amable
    r = sofia.api(f"/api/sesiones/{sid}/continuar")
    assert r.status_code == 503 and "saturado" in r.json()["error"]

    # 2) la IA vuelve → /continuar genera la apertura; un mensaje del usuario sin respuesta también se recupera
    monkeypatch.setattr(gemini.llm, "generar", original)
    r = sofia.api(f"/api/sesiones/{sid}/continuar")
    assert r.status_code == 200 and r.json()["mensaje"] and r.json()["n_mensajes"] == 1
    r = sofia.api(f"/api/sesiones/{sid}/continuar")   # idempotente: no genera otro mensaje
    assert r.json()["n_mensajes"] == 1
    monkeypatch.setattr(gemini.llm, "generar", falla)
    r = sofia.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Hola Elena"})
    assert r.status_code == 503
    assert db.mensajes(sid)[-1]["rol"] == "usuario"
    monkeypatch.setattr(gemini.llm, "generar", original)
    r = sofia.api(f"/api/sesiones/{sid}/continuar")
    assert r.status_code == 200 and r.json()["n_mensajes"] == 3
    assert db.mensajes(sid)[-1]["rol"] == "avatar"
    # cerrar con Fin pendiente también termina la sesión
    monkeypatch.setattr(gemini.llm, "generar", falla)
    assert sofia.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Fin"}).status_code == 503
    monkeypatch.setattr(gemini.llm, "generar", original)
    stub["elena.analisis"] = {"nivel_dm": "DM1", "prioridades": [{"habilidad_id": "ventas", "brecha": "media", "razon": "x", "competencias_relacionadas": []}]}
    r = sofia.api(f"/api/sesiones/{sid}/continuar")
    assert r.json()["fin"]
    assert db.sesion(sid)["estado"] == "completada"
    assert db.perfil(sofia.u["id"])["estado"] == "completo"


def test_cadena_de_respaldo(monkeypatch):
    """Con la API real simulada: el modelo principal responde 503 y el de respaldo contesta."""
    llamadas = []

    class Resp:
        text = '{"mensaje": "hola", "fase": "rapport", "historias": 0}'
        function_calls = None
        usage_metadata = _t.SimpleNamespace(prompt_token_count=100, candidates_token_count=20, thoughts_token_count=0, cached_content_token_count=0)
        candidates = []

    class Modelos:
        def generate_content(self, model, contents, config):
            llamadas.append(model)
            if model == "gemini-3.8-flash":
                raise RuntimeError("503 UNAVAILABLE. This model is currently experiencing high demand.")
            return Resp()

    llm = LLM()
    monkeypatch.setattr(llm, "_client", lambda: _t.SimpleNamespace(models=Modelos()))
    monkeypatch.setattr(gemini.settings, "LLM_PROVEEDOR", "gemini")
    monkeypatch.setattr(gemini.settings, "GEMINI_API_KEY", "x")
    monkeypatch.setattr(gemini.time, "sleep", lambda s: None)
    r = llm.generar(origen="prueba", system="s", contents=[{"role": "user", "text": "hola"}], schema={"type": "object", "properties": {"mensaje": {"type": "string"}}}, reintentos=1)
    assert r.json["mensaje"] == "hola"
    assert llamadas[:2] == ["gemini-3.8-flash", "gemini-3.8-flash"] and llamadas[2] == "gemini-3.7-flash" and r.modelo == "gemini-3.7-flash"
    # error no transitorio → mensaje claro sin recorrer la cadena
    class ModelosKey:
        def generate_content(self, model, contents, config):
            raise RuntimeError("400 API key not valid. Please pass a valid API key.")
    monkeypatch.setattr(llm, "_client", lambda: _t.SimpleNamespace(models=ModelosKey()))
    with pytest.raises(ErrorLLM) as ex:
        llm.generar(origen="prueba", system="s", contents=[{"role": "user", "text": "hola"}], reintentos=0)
    assert "API key" in str(ex.value)


def test_regenerar_planes_faltantes(client, stub):
    sofia = Sesion(client, "sofia@condor.mx", "ClaveSofia1234")
    uid = sofia.u["id"]
    for r in db.roadmaps(uid, ("activo", "propuesto")):
        db.actualizar_roadmap(r["id"], estado="rechazado")
    assert not db.roadmaps(uid, ("activo", "propuesto"))
    assert "Generar mis planes" in sofia.get("/mi-diagnostico").text
    r = sofia.post("/diagnostico/planes")
    assert r.status_code == 303
    habs = {r["habilidad"] for r in db.roadmaps(uid, ("activo", "propuesto"))}
    assert habs == {"ventas", "ruta_dm"}


def test_salidas_malformadas_no_rompen_agentes(client, stub):
    """La IA devuelve JSON incompleto o con valores fuera de rango: la sesión se completa igual con valores normalizados."""
    from app.agents import catalogo as C
    sofia = Sesion(client, "sofia@condor.mx", "ClaveSofia1234")
    uid = sofia.u["id"]
    # Celeste: kpis con ids incorrectos y scores fuera de rango, sin evidencia ni recomendación
    stub["celeste.feedback"] = {"kpis": [{"id": "KPI-X", "score": 140}, {"score": -5}], "evidencia": "nada", "recomendacion": "texto suelto", "momentos_clave": ["hola"], "tips": None}
    stub["celeste.apertura"] = {"mensaje": "  ", "tension": 250, "estado": "raro"}
    r = sofia.post("/entrenar/ventas/iniciar", {"item": "0", "nivel": "Principiante"})
    sid = int(r.headers["location"].rsplit("/", 1)[1])
    assert db.mensajes(sid) == []                      # apertura vacía → se pide de nuevo
    stub["celeste.apertura"] = {"mensaje": "Buenos días, ¿cuánto tiempo necesita?", "tension": 250, "estado": "raro"}
    r = sofia.api(f"/api/sesiones/{sid}/continuar")
    assert r.status_code == 200 and r.json()["meta"]["tension"] == 100 and r.json()["meta"]["estado"] == "en_curso"
    sofia.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Hola Celeste"})
    sofia.api(f"/api/sesiones/{sid}/terminar")
    s = db.sesion(sid)
    assert s["estado"] == "completada", s.get("error")
    res = s["resultado"]
    assert [k["id"] for k in res["kpis"]] == [k["id"] for k in C.HABILIDADES["ventas"]["kpis"]]
    assert res["kpis"][0]["score"] == 100 and res["kpis"][1]["score"] == 0
    assert res["evidencia"]["cierre"] == "sin_cierre" and res["recomendacion"]["nivel_sugerido"] == "Principiante"
    assert sofia.get(f"/sesion/{sid}/reporte").status_code == 200
    # Juan: diseño sin formato ni sub-dimensiones, feedback sin subdimensiones
    stub["juan.diseno"] = {"titulo": "", "formato": "otro", "subdimensiones": None, "primer_mensaje": "Empecemos."}
    stub["juan.feedback"] = {"score_global": 12, "subdimensiones": [], "siguiente_paso": {"competencia": "Inexistente"}}
    r = sofia.post("/entrenar/ruta_dm/iniciar", {"item": "0", "nivel": "DM1", "competencia": "Escucha activa"})
    sid = int(r.headers["location"].rsplit("/", 1)[1])
    s = db.sesion(sid)
    assert s["escenario"]["formato"] == "roleplay" and len(s["escenario"]["subdimensiones"]) == 4
    sofia.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Cuénteme qué pasó"})
    sofia.api(f"/api/sesiones/{sid}/terminar")
    s = db.sesion(sid)
    assert s["estado"] == "completada", s.get("error")
    assert s["resultado"]["score_global"] == 10 and s["resultado"]["siguiente_paso"]["competencia"] in C.competencias_dm("DM2")
    assert sofia.get(f"/sesion/{sid}/reporte").status_code == 200
