"""Laboratorio Interactivo de Habilidades para Delivery Managers: guion fijo, avance por eventos, profundización acotada, reporte de 100 puntos,
evidencia en la Ruta DM, reordenamiento del plan, checkpoint con casos generados y cierres anticipados."""
from __future__ import annotations

from app import db
from app.agents import laboratorio as L
from app.llm import gemini
from tests.conftest import ONBOARDING_VENDEDOR, Sesion

FEEDBACK_LAB = {
    "sintesis": "Escucha antes de decidir y comunica con estructura; bajo presión tiende a prometer fechas.",
    "dimensiones": [
        {"id": "escucha", "puntos": 26, "radar": "Sólido", "lectura": "Pregunta antes de comprometer."},
        {"id": "estres", "puntos": 15, "radar": "En desarrollo", "lectura": "Prometió el viernes sin evidencia."},
        {"id": "pmbok", "puntos": 20, "radar": "Sólido", "lectura": "Controla cambios de alcance."},
        {"id": "comunicacion", "puntos": 17, "radar": "Fortalecido", "lectura": "Mensaje ejecutivo en tres ideas."},
    ],
    "fortalezas": [{"nombre": "Investigación antes de decidir", "evidencia": "Pidió evidencia a QA", "por_que": "Reduce riesgo"},
                   {"nombre": "Comunicación ejecutiva", "evidencia": "Resumen de 90 segundos", "por_que": "Claridad"},
                   {"nombre": "Cierre de acuerdos", "evidencia": "Fijó seguimiento 7 pm", "por_que": "Cierra el loop"}],
    "oportunidades": [{"nombre": "Sostener incertidumbre", "observado": "Dijo 'sí salimos'", "riesgo": "Compromiso prematuro", "como_fortalecer": "Responder con condiciones y checkpoint"},
                      {"nombre": "Fatiga del equipo", "observado": "No redistribuyó carga", "riesgo": "Errores", "como_fortalecer": "Relevar al desarrollador"},
                      {"nombre": "Culpabilización", "observado": "Señaló al desarrollador", "riesgo": "Defensividad", "como_fortalecer": "Hablar de hechos"}],
    "momentos_clave": [{"situacion": "Presión del cliente", "respuesta": "Prometió el viernes", "lectura": "Manejo de presión"},
                       {"situacion": "Riesgo oculto", "respuesta": "Pidió reproducir la falla", "lectura": "Evidencia"},
                       {"situacion": "CIO", "respuesta": "Tres ideas y siguiente paso", "lectura": "Comunicación ejecutiva"}],
    "recomendaciones": ["Antes de responder sí/no, enumera lo que falta por validar.", "Define un checkpoint con hora.", "Reparte la carga cuando alguien lleve más de 10 h."],
    "prioridad": {"dimension": "estres", "por_que": "Las promesas bajo presión son el mayor riesgo.", "que_practicar": ["Sostener incertidumbre con un plan", "Pausar antes de responder"]},
    "cierre": "Tienes base sólida de escucha y comunicación; el siguiente paso es decidir con evidencia bajo presión.",
}


def _colaborador_con_diagnostico(client, stub, email: str, nombre: str) -> Sesion:
    try:
        rrhh = Sesion(client, "rrhh@condor.mx", "NuevaClaveRRHH1")      # contraseña cambiada por test_flujo
    except AssertionError:
        rrhh = Sesion(client, "rrhh@condor.mx", "ClaveRRHH123")
        rrhh.cambiar_password("NuevaClaveRRHH1")
    eid = rrhh.u["empresa_id"]
    emp = db.empresa(eid)
    if "ruta_dm" not in (emp.get("habilidades") or []):
        db.actualizar_empresa(eid, habilidades_json=list(emp.get("habilidades") or []) + ["ruta_dm"])
    if not db.areas(eid):
        db.crear_area(eid, "Odoo")
    r = rrhh.post("/gestion/usuarios", {"nombre": nombre, "email": email, "puesto": "Consultor", "rol": "colaborador", "area_id": db.areas(eid)[0]["id"]})
    clave = r.headers["location"].split("clave=")[1]
    u = Sesion(client, email, clave)
    u.cambiar_password("ClaveLab123456")
    assert u.api("/api/diagnostico/onboarding", {"respuestas": ONBOARDING_VENDEDOR}).status_code == 200
    r = u.post("/diagnostico/iniciar")
    sid = int(r.headers["location"].rsplit("/", 1)[1])
    stub["elena.analisis"] = {"nivel_dm": "DM1", "prioridades": [{"habilidad_id": "ventas", "brecha": "media", "razon": "x", "competencias_relacionadas": []}]}
    u.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Hola Elena"})
    stub["elena.turno"] = {"fase": "fin", "mensaje": "Gracias, cerramos."}
    u.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Listo"})
    stub.pop("elena.turno")
    assert db.perfil(u.u["id"])["estado"] == "completo"
    return u


def _llamadas(origen: str) -> int:
    return sum(1 for c in gemini.STUB_LLAMADAS if c["origen"] == origen)


def test_laboratorio_guion_fijo_reporte_y_ruta_dm(client, stub):
    lucia = _colaborador_con_diagnostico(client, stub, "lucia@condor.mx", "Lucía Lab")
    uid = lucia.u["id"]
    # 1) el plan de la Ruta DM arranca con el laboratorio y /hoy lleva a él
    rm = db.roadmap_activo(uid, "ruta_dm")
    assert rm["items"][0]["tipo"] == "laboratorio"
    sig = db.siguiente_item(uid, "ruta_dm")
    assert sig["tipo"] == "laboratorio"
    assert lucia.get("/hoy").status_code == 200
    assert lucia.get(f"/entrenar/ruta_dm?item={sig['id']}").headers["location"].endswith(f"/laboratorio?item={sig['id']}")
    assert lucia.get("/laboratorio").status_code == 200

    # 2) inicio: bienvenida fija (0 tokens) y Caso 1 · Evento 1 al confirmar (0 tokens)
    gemini.STUB_LLAMADAS.clear()
    r = lucia.post("/laboratorio/iniciar", {"item": str(sig["id"])})
    assert r.status_code == 303, r.text
    sid = int(r.headers["location"].rsplit("/", 1)[1])
    s = db.sesion(sid)
    assert s["tipo"] == "laboratorio" and s["escenario"]["variante"] == "fija" and s["roadmap_item_id"] == sig["id"]
    msgs = db.mensajes(sid)
    assert len(msgs) == 1 and msgs[0]["texto"] == L.MENSAJE_BIENVENIDA
    assert _llamadas("juan.laboratorio") == 0
    assert lucia.get(f"/sesion/{sid}").status_code == 200
    r = lucia.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Estoy listo, comencemos."})
    js = r.json()
    assert "CASO 1" in js["mensaje"] and "Proyecto Fénix" in js["mensaje"] and "¿Qué haces o qué dices en este momento?" in js["mensaje"]
    assert js["meta"]["lab"] == {"caso": 1, "casos": 2, "evento": 1, "eventos": 5, "titulo": L.CASOS_FIJOS[0]["titulo"], "respondidos": 0, "total": 10}
    assert _llamadas("juan.laboratorio") == 0

    # 3) evento 1 → Juan reacciona (1 llamada corta) y el sistema añade el evento 2 tal cual
    stub["juan.laboratorio"] = {"mensaje": "El cliente escucha tu respuesta y cruza los brazos.", "accion": "avanzar", "tension": 55}
    r = lucia.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Antes de comprometer una fecha necesito entender qué falta en pruebas. QA, ¿qué flujos quedan?"})
    js = r.json()
    assert js["mensaje"].startswith("El cliente escucha tu respuesta") and L.CASOS_FIJOS[0]["eventos"][1]["texto"] in js["mensaje"]
    assert js["meta"]["lab"]["evento"] == 2 and js["meta"]["lab"]["respondidos"] == 1 and js["meta"]["tension"] == 55
    assert _llamadas("juan.laboratorio") == 1
    llamada = gemini.STUB_LLAMADAS[-1]
    assert "REGLA DE NO CONTAMINACIÓN" in llamada["system"] and "Evento actual (1 de 5)" in llamada["system"]

    # 4) profundización: una sola vez por evento; la segunda se bloquea y avanza
    stub["juan.laboratorio"] = {"mensaje": "¿Qué harías específicamente a continuación?", "accion": "profundizar", "tension": 60}
    js = lucia.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Pues ver qué pasa."}).json()
    assert js["meta"]["lab"]["evento"] == 2 and js["meta"]["lab"]["respondidos"] == 1 and js["mensaje"].startswith("¿Qué harías")
    js = lucia.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Sigo sin saber."}).json()   # el modelo insiste en profundizar → el motor avanza de todos modos
    assert js["meta"]["lab"]["evento"] == 3 and js["meta"]["lab"]["respondidos"] == 2
    assert "ya no puedes profundizar" in gemini.STUB_LLAMADAS[-1]["system"]

    # 5) resto del caso 1 y transición al caso 2
    stub["juan.laboratorio"] = {"mensaje": "Después de tu intervención ocurre lo siguiente.", "accion": "avanzar", "tension": 70}
    for _ in range(2):
        js = lucia.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Reviso el impacto con el equipo y defino responsables."}).json()
    assert js["meta"]["lab"] | {"titulo": ""} == {"caso": 1, "casos": 2, "evento": 5, "eventos": 5, "titulo": "", "respondidos": 4, "total": 10}
    js = lucia.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Estamos a 80 % de pruebas; propongo salir el lunes con checkpoint el viernes."}).json()
    assert "CASO 2" in js["mensaje"] and "War Room" in js["mensaje"] and js["meta"]["lab"]["caso"] == 2 and js["meta"]["lab"]["evento"] == 1
    assert lucia.get(f"/sesion/{sid}").status_code == 200

    # 6) caso 2 completo → fin → reporte de 100 puntos
    for _ in range(4):
        js = lucia.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Primero evidencia; nadie busca culpables. DBA, ¿qué muestran los procesos?"}).json()
        assert not js["fin"]
    assert js["meta"]["lab"]["evento"] == 5
    stub["juan.laboratorio"] = {"mensaje": "Gracias. El laboratorio concluye; el reporte se genera a continuación.", "accion": "fin", "tension": 20}
    stub["juan.lab_feedback"] = FEEDBACK_LAB
    js = lucia.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Documento causa raíz, acciones preventivas y comunico el cierre."}).json()
    assert js["fin"] and js["meta"]["lab"]["respondidos"] == 10
    s = db.sesion(sid)
    assert s["estado"] == "completada", s.get("error")
    lab = s["resultado"]["laboratorio"]
    assert s["score_global"] == 78.0 and lab["total"] == 78.0 and lab["nivel"] == "Competencia funcional"
    assert [d["puntos"] for d in lab["dimensiones"]] == [26, 15, 20, 17] and lab["prioridad"]["nombre"].startswith("Manejo del estrés")
    assert s["resultado"]["score_global"] == 7.8 and s["resultado"]["siguiente_paso"]["competencia"] == "Manejo de ansiedad"
    assert _llamadas("juan.lab_feedback") == 1 and _llamadas("juan.laboratorio") == 11
    assert "GUION DE LOS CASOS" in gemini.STUB_LLAMADAS[-1]["contents"][0]["text"] or any("GUION DE LOS CASOS" in c["contents"][0]["text"] for c in gemini.STUB_LLAMADAS if c["origen"] == "juan.lab_feedback")

    # 7) evidencia en la Ruta DM, plan reordenado por la prioridad y checkpoint programado
    niv = db.nivel(uid, "ruta_dm")
    comp = niv["competencias"]
    assert comp["Escucha activa"]["score"] == 8.7 and comp["Escucha activa"]["fuente"] == "laboratorio"
    assert comp["PMBOK"]["score"] == 8.0 and comp["Manejo de ansiedad"]["score"] == 6.0 and comp["Comunicación"]["score"] == 8.5
    rm = db.roadmap_activo(uid, "ruta_dm")
    assert db.roadmap_item(sig["id"])["estado"] == "completada"
    pendientes = [it for it in rm["items"] if it["estado"] == "pendiente"]
    assert pendientes[0]["competencia"] == "Manejo de ansiedad"   # prioridad del laboratorio → siguiente sesión
    assert any(it["tipo"] == "laboratorio" for it in pendientes)  # checkpoint futuro
    assert lucia.get("/roadmaps").status_code == 200
    r = lucia.get(f"/sesion/{sid}/reporte")
    assert r.status_code == 200 and "Prioridad de desarrollo" in r.text and "Tus 3 principales fortalezas" in r.text and "78" in r.text
    r = lucia.get(f"/sesion/{sid}/reporte.pdf")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    analisis = db.analisis(lucia.u["empresa_id"], tipo="post_sesion", sesion_id=sid, limite=1)
    assert analisis and any("Laboratorio DM #1" in d for d in analisis[0]["contenido"]["decisiones"])
    assert db.notificaciones(uid) and any("reordenó" in n["titulo"] for n in db.notificaciones(uid))
    # el reporte se evaluó con la fuente única (materiales del taller) y el coach del reporte responde sólo con ellos
    fb = [c for c in gemini.STUB_LLAMADAS if c["origen"] == "juan.lab_feedback"][-1]
    assert "MATERIALES:" in fb["system"] and "L.E.A.D." in fb["system"] and "C.O.N.E.C.T.A." in fb["system"] and "Triángulo del diablo" in fb["system"]
    r = lucia.api(f"/api/reporte/{sid}/chat", {"texto": "¿Cómo practico sostener la incertidumbre sin prometer de más?"})
    assert r.status_code == 200
    coach = [c for c in gemini.STUB_LLAMADAS if c["origen"] == "coach.reporte"][-1]
    assert "MATERIALES:" in coach["system"] and "MANEJO DEL ESTRÉS" in coach["system"] and "[ESCUCHA ACTIVA]" not in coach["system"]


def test_laboratorio_checkpoint_con_casos_generados_y_cierres(client, stub):
    mateo = _colaborador_con_diagnostico(client, stub, "mateo@condor.mx", "Mateo Lab")
    uid = mateo.u["id"]
    # primer laboratorio cerrado con "Fin" tras una sola respuesta → se analiza con lo respondido
    r = mateo.post("/laboratorio/iniciar")
    sid = int(r.headers["location"].rsplit("/", 1)[1])
    mateo.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Listo"})
    stub["juan.laboratorio"] = {"mensaje": "El cliente asiente.", "accion": "avanzar", "tension": 40}
    mateo.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Pido a QA el estado de pruebas antes de responder."})
    stub["juan.lab_feedback"] = FEEDBACK_LAB
    js = mateo.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Fin"}).json()
    assert js["fin"] and db.sesion(sid)["estado"] == "completada"
    assert _llamadas("juan.lab_variante") == 0

    # segundo laboratorio: Juan genera casos nuevos (variante) ambientados en el perfil
    casos = {"casos": [
        {"titulo": "Migración Atlas — corte el jueves", "contexto": "Migración de ERP a punto de cortar.", "personajes": "Gerente de operaciones, líder técnico, QA, consultor",
         "eventos": [{"titulo": f"Evento {i}", "texto": f"Gerente: «Necesito certeza» ({i}).", "pregunta": "¿Qué haces?", "evalua": "escucha"} for i in range(1, 6)]},
        {"titulo": "Interfaz caída con el banco", "contexto": "La interfaz bancaria dejó de responder.", "personajes": "Tesorería, DBA, integrador, Director",
         "eventos": [{"titulo": f"Evento {i}", "texto": f"Tesorería: «No podemos pagar» ({i}).", "pregunta": "¿Cómo respondes?", "evalua": "estrés"} for i in range(1, 6)]},
    ]}
    stub["juan.lab_variante"] = casos
    r = mateo.get("/laboratorio")
    assert r.status_code == 200 and "Tu último laboratorio" in r.text
    r = mateo.post("/laboratorio/iniciar")
    sid2 = int(r.headers["location"].rsplit("/", 1)[1])
    s = db.sesion(sid2)
    assert s["escenario"]["variante"] == "generada" and s["escenario"]["casos"][0]["titulo"] == "Migración Atlas — corte el jueves"
    assert _llamadas("juan.lab_variante") == 1 and "Lucía" not in gemini.STUB_LLAMADAS[-1]["system"] and "Mateo Lab" in gemini.STUB_LLAMADAS[-1]["system"]
    js = mateo.api(f"/api/sesiones/{sid2}/mensaje", {"texto": "Vamos"}).json()
    assert "Migración Atlas" in js["mensaje"] and "«Necesito certeza» (1)" in js["mensaje"]
    # descartar un laboratorio sin respuestas no genera reporte
    assert mateo.api(f"/api/sesiones/{sid2}/terminar").status_code == 200
    assert db.sesion(sid2)["estado"] == "descartada"
    # variante inválida de la IA → error amable y la sesión queda abierta para reintentar
    stub["juan.lab_variante"] = {"casos": [{"titulo": "x"}]}
    r = mateo.post("/laboratorio/iniciar")
    sid3 = int(r.headers["location"].rsplit("/", 1)[1])
    assert db.sesion(sid3)["estado"] == "en_curso" and db.mensajes(sid3) == []
    r = mateo.api(f"/api/sesiones/{sid3}/continuar")
    assert r.status_code == 503 and "casos" in r.json()["error"]
    stub["juan.lab_variante"] = casos
    r = mateo.api(f"/api/sesiones/{sid3}/continuar")
    assert r.status_code == 200 and r.json()["mensaje"] == L.MENSAJE_BIENVENIDA
    assert mateo.api(f"/api/sesiones/{sid3}/descartar").status_code == 200
    assert mateo.get("/catalogo").status_code == 200 and "Laboratorio DM" in mateo.get("/catalogo").text
    assert db.sesiones(usuario_id=uid, tipo="laboratorio", estado="completada")


def test_meta_del_lider_alcanzada_recalibra_y_notifica(client, stub):
    """Las metas del director entran al Analista: al cumplirse (promedio de 2 sesiones ≥ mínimo) se marca alcanzada y se avisa a quien la creó."""
    nora = _colaborador_con_diagnostico(client, stub, "nora@condor.mx", "Nora Meta")
    uid = nora.u["id"]
    rrhh = Sesion(client, "rrhh@condor.mx", "NuevaClaveRRHH1")
    r = rrhh.post("/metas", {"habilidad": "ventas", "score_minimo": "80", "plazo": "2026-12-31", "prioridad": "alta", "descripcion": "Cierre de año", "usuario_id": uid})
    assert r.status_code == 303
    meta = [m for m in db.metas(rrhh.u["empresa_id"], usuario_id=uid) if m["usuario_id"] == uid][0]
    kpis = [{"id": f"KPI-{i}", "score": 88, "evidencia": "t1", "bien": "b", "mejora": "m"} for i in range(1, 7)]
    stub["celeste.feedback"] = {"kpis": kpis, "recomendacion": {"nivel_sugerido": "Intermedio", "objetivo_siguiente": "Cierra con fecha", "razon": "listo"}}
    for n in range(2):
        item = db.siguiente_item(uid, "ventas")
        r = nora.post("/entrenar/ventas/iniciar", {"item": item["id"], "nivel": item["nivel"], "competencia": ""})
        sid = int(r.headers["location"].rsplit("/", 1)[1])
        nora.api(f"/api/sesiones/{sid}/mensaje", {"texto": "¿Qué le preocupa hoy de su operación?"})
        assert nora.api(f"/api/sesiones/{sid}/terminar").status_code == 200
        assert db.sesion(sid)["estado"] == "completada"
        if n == 0:
            assert db.metas(rrhh.u["empresa_id"], usuario_id=uid, solo_activas=False)[0]["estado"] == "activa"
    m = [x for x in db.metas(rrhh.u["empresa_id"], usuario_id=uid, solo_activas=False) if x["id"] == meta["id"]][0]
    assert m["estado"] == "alcanzada"
    an = db.analisis(rrhh.u["empresa_id"], tipo="post_sesion", usuario_id=uid, limite=1)[0]
    assert any("Meta del líder alcanzada" in d for d in an["contenido"]["decisiones"])
    assert any("Meta alcanzada" in n["titulo"] for n in db.notificaciones(rrhh.u["id"]))
    assert any("Alcanzaste una meta" in n["titulo"] for n in db.notificaciones(uid))
    # el siguiente objetivo del plan se reescribió con la lectura del Analista tras la sesión
    sig = db.siguiente_item(uid, "ventas")
    assert sig and "Ajustado por el Analista" in (sig.get("porque") or "")


def test_meta_nueva_recalibra_planes_activos(client, stub):
    """Al crear una meta, el Analista reescribe los objetivos pendientes del plan y, si fija una competencia DM, la pone como siguiente sesión."""
    pablo = _colaborador_con_diagnostico(client, stub, "pablo@condor.mx", "Pablo Meta")
    uid = pablo.u["id"]
    rrhh = Sesion(client, "rrhh@condor.mx", "NuevaClaveRRHH1")
    rm = db.roadmap_activo(uid, "ruta_dm")
    pend = [it for it in rm["items"] if it["estado"] == "pendiente" and it["tipo"] != "laboratorio"]
    objetivo_dm = pend[-1]["competencia"]                          # una competencia que hoy está al final del plan
    stub["analista.recalibrar_meta"] = {"items": [{"n": i + 1, "objetivo": f"Meta del líder · sesión {i + 1}: demostrar {it['competencia']} con score ≥ 85", "porque": "Apunta a la meta"} for i, it in enumerate(pend)]}
    gemini.STUB_LLAMADAS.clear()
    r = rrhh.post("/metas", {"habilidad": "ruta_dm", "competencia": objetivo_dm, "score_minimo": "85", "plazo": "2026-12-31", "prioridad": "alta", "descripcion": "Cerrar proyectos con carta de DM", "usuario_id": uid})
    assert r.status_code == 303
    rm2 = db.roadmap_activo(uid, "ruta_dm")
    pend2 = [it for it in rm2["items"] if it["estado"] == "pendiente" and it["tipo"] != "laboratorio"]
    assert pend2[0]["competencia"] == objetivo_dm                   # la competencia de la meta pasa al frente
    assert rm2["version"] == rm["version"] + 1 and rm2["ajustes"] == (rm["ajustes"] or 0) + 1
    assert all(it["objetivo"].startswith("Meta del líder") for it in pend2)
    llamada = [c for c in gemini.STUB_LLAMADAS if c["origen"] == "analista.recalibrar_meta"]
    assert len(llamada) == 1 and llamada[0]["modelo"] != "" and "score_minimo" in llamada[0]["contents"][0]["text"] and "85" in llamada[0]["contents"][0]["text"]
    assert any("se ajustó a una meta" in n["titulo"] for n in db.notificaciones(uid))
    assert any("Meta integrada" in n["titulo"] for n in db.notificaciones(rrhh.u["id"]))
    # una meta de área sin planes afectados no rompe nada
    r = rrhh.post("/metas", {"habilidad": "entrevistas", "score_minimo": "70", "prioridad": "baja", "area_id": "0", "usuario_id": "0"})
    assert r.status_code == 303
