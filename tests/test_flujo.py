"""Flujo completo: alta de empresa y personas → diagnóstico con Elena → roadmaps → sesiones con Celeste y Juan → Analista → ascenso DM → tableros."""
from __future__ import annotations

import pytest

from app import db, metrics
from app.agents import analista, catalogo as C
from tests.conftest import ONBOARDING_VENDEDOR, Sesion

ESTADO: dict = {}


def _diagnostico_completo(s: Sesion, stub):
    r = s.api("/api/diagnostico/onboarding", {"respuestas": ONBOARDING_VENDEDOR, "producto_concreto": "Implementación de Odoo"})
    assert r.status_code == 200, r.text
    r = s.post("/diagnostico/iniciar")
    assert r.status_code == 303, r.text
    sid = int(r.headers["location"].rsplit("/", 1)[1])
    ses = db.sesion(sid)
    assert ses["tipo"] == "diagnostico" and ses["estado"] == "en_curso"
    assert len(db.mensajes(sid)) == 1   # apertura de Elena
    for i in range(4):
        r = s.api(f"/api/sesiones/{sid}/mensaje", {"texto": f"Respuesta {i}: en un proyecto con un cliente de manufactura yo lideré la migración…"})
        assert r.status_code == 200, r.text
    stub["elena.turno"] = {"fase": "fin", "mensaje": "Gracias, con esto cierro."}
    stub["elena.analisis"] = {"nivel_ventas": "Principiante", "nivel_dm": "DM1", "nivel_entrevistas": "Principiante",
                              "prioridades": [{"habilidad_id": "ventas", "brecha": "alta", "razon": "objeciones", "competencias_relacionadas": ["Comunicación"]},
                                              {"habilidad_id": "entrevistas", "brecha": "baja", "razon": "estructura STAR", "competencias_relacionadas": []}]}
    r = s.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Fin"})
    assert r.status_code == 200 and r.json()["fin"], r.text
    return sid


def test_01_alta_empresa_y_personas(client):
    admin = Sesion(client, "admin@menteviva.mx", "SuperClave123")
    assert admin.get("/admin").status_code == 200
    r = admin.post("/admin/empresas", {"nombre": "Empresa Demo", "industria": "Servicios", "rrhh_nombre": "Ana", "rrhh_email": "ana@demo.mx", "ruta_dm": "1"})
    assert r.status_code == 303 and "clave=" in r.headers["location"]
    rrhh = Sesion(client, "rrhh@condor.mx", "ClaveRRHH123")
    assert rrhh.get("/rrhh").status_code == 307   # debe cambiar contraseña primero
    rrhh.cambiar_password("NuevaClaveRRHH1")
    assert rrhh.get("/rrhh").status_code == 200
    r = rrhh.post("/gestion/areas", {"nombre": "Odoo", "director_id": "0"})
    assert r.status_code == 303
    area = db.areas(rrhh.u["empresa_id"])[0]
    r = rrhh.post("/gestion/usuarios", {"nombre": "Diana Directora", "email": "diana@condor.mx", "puesto": "Directora Odoo", "rol": "director", "area_id": area["id"]})
    clave_dir = r.headers["location"].split("clave=")[1]
    r = rrhh.post("/gestion/usuarios", {"nombre": "Carlos Colaborador", "email": "carlos@condor.mx", "puesto": "Consultor", "rol": "colaborador", "area_id": area["id"]})
    clave_col = r.headers["location"].split("clave=")[1]
    r = rrhh.post("/gestion/usuarios", {"nombre": "Daniel DG", "email": "dg@condor.mx", "puesto": "Director General", "rol": "dg", "area_id": "0"})
    clave_dg = r.headers["location"].split("clave=")[1]
    assert db.area(area["id"])["director_id"] == db.usuarios(rrhh.u["empresa_id"], rol="director")[0]["id"]
    ESTADO.update(rrhh=rrhh, area=area, claves={"diana": clave_dir, "carlos": clave_col, "dg": clave_dg}, admin=admin)


def test_02_seguridad_basica(client):
    r = client.get("/hoy", follow_redirects=False)
    assert r.status_code == 307 and "/login" in r.headers["location"]
    rrhh: Sesion = ESTADO["rrhh"]
    # CSRF: token ausente
    r = client.post("/gestion/areas", data={"nombre": "X"}, headers={"Cookie": f"mv_sesion={rrhh.cookie}", "Sec-Fetch-Site": "same-origin"})
    assert r.status_code == 403
    # origen cruzado
    r = client.post("/gestion/areas", data={"nombre": "X", "csrf": rrhh.csrf}, headers={"Cookie": f"mv_sesion={rrhh.cookie}", "Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 403
    # colaborador no entra a RRHH
    carlos = Sesion(client, "carlos@condor.mx", ESTADO["claves"]["carlos"])
    carlos.cambiar_password("ClaveCarlos123")
    assert carlos.get("/rrhh").status_code == 403
    assert carlos.get("/admin").status_code == 403
    ESTADO["carlos"] = carlos
    # límite de intentos (por usuario y por IP)
    for _ in range(9):
        client.post("/login", data={"email": "nadie@x.mx", "password": "mal"})
    r = client.post("/login", data={"email": "nadie@x.mx", "password": "mal"})
    assert r.status_code == 429
    db.limpiar_intentos("ip:testclient")


def test_03_diagnostico_elena_y_roadmaps(client, stub):
    carlos: Sesion = ESTADO["carlos"]
    assert carlos.get("/hoy").status_code == 200
    sid = _diagnostico_completo(carlos, stub)
    ses = db.sesion(sid)
    assert ses["estado"] == "completada", ses.get("error")
    perfil = db.perfil(carlos.u["id"])
    assert perfil["estado"] == "completo"
    assert perfil["diagnostico"]["nivel_dm"] == "DM1" and perfil["diagnostico"]["score_inicial"] is not None
    niveles = db.niveles(carlos.u["id"])
    assert niveles["ventas"]["nivel"] == "Principiante" and niveles["ruta_dm"]["nivel"] == "DM1"
    rms = db.roadmaps(carlos.u["id"])
    habs = {r["habilidad"]: r for r in rms}
    assert set(habs) == {"ventas", "entrevistas", "ruta_dm"}
    assert habs["ventas"]["estado"] == "activo" and habs["ruta_dm"]["estado"] == "activo"
    assert habs["entrevistas"]["estado"] == "propuesto"   # no forma parte del rol → RRHH decide
    assert habs["ventas"]["horizonte_semanas"] == 8 and habs["ventas"]["total"] >= 3
    assert all(it["competencia"] in C.competencias_dm("DM2") for it in habs["ruta_dm"]["items"])
    assert carlos.get("/mi-diagnostico").status_code == 200
    assert carlos.get("/roadmaps").status_code == 200
    props = db.propuestas(carlos.u["empresa_id"], tipo="roadmap")
    assert props and props[0]["estado"] == "pendiente"
    ESTADO["prop_roadmap"] = props[0]["id"]


def test_04_sesion_celeste_y_reglas_de_nivel(client, stub):
    carlos: Sesion = ESTADO["carlos"]
    uid = carlos.u["id"]
    kpis_altos = [{"id": f"KPI-{i}", "score": 85, "evidencia": "t1", "bien": "b", "mejora": "m"} for i in range(1, 7)]
    stub["celeste.feedback"] = {"kpis": kpis_altos, "recomendacion": {"nivel_sugerido": "Intermedio", "objetivo_siguiente": "Cierra con fecha", "razon": "listo"}}
    scores = []
    for n in range(2):
        item = db.siguiente_item(uid, "ventas")
        assert item
        r = carlos.post("/entrenar/ventas/iniciar", {"item": item["id"], "nivel": item["nivel"], "competencia": ""})
        assert r.status_code == 303, r.text
        sid = int(r.headers["location"].rsplit("/", 1)[1])
        assert carlos.get(f"/sesion/{sid}").status_code == 200
        for i in range(3):
            r = carlos.api(f"/api/sesiones/{sid}/mensaje", {"texto": "¿Qué le preocupa hoy de su operación? (SPIN Implicación)"})
            assert r.status_code == 200, r.text
        r = carlos.api(f"/api/sesiones/{sid}/terminar")
        assert r.status_code == 200
        ses = db.sesion(sid)
        assert ses["estado"] == "completada", ses.get("error")
        scores.append(ses["score_global"])
        assert carlos.get(f"/sesion/{sid}/reporte").status_code == 200
        assert db.roadmap_item(item["id"])["estado"] == "completada"
    assert scores == [85.0, 85.0]
    niv = db.nivel(uid, "ventas")
    assert niv["nivel"] == "Intermedio", niv     # dos sesiones > 75 → sube
    assert niv["sesiones"] == 2
    sig = db.siguiente_item(uid, "ventas")
    assert sig["nivel"] == "Intermedio"           # los pendientes se renivelan
    assert db.analisis(carlos.u["empresa_id"], tipo="post_sesion", usuario_id=uid)
    # baja: score < 50 en Intermedio
    stub["celeste.feedback"] = {"kpis": [{"id": f"KPI-{i}", "score": 30, "evidencia": "t", "bien": "b", "mejora": "m"} for i in range(1, 7)],
                               "evidencia": {"tecnicas_usadas": [], "spin": {"S": 1, "P": 0, "I": 0, "N": 0}, "etapas_cumplidas": [], "turno_primer_descuento": 2,
                                             "uso_silencio_activo": False, "objeciones_lanzadas": 2, "objeciones_resueltas": 0, "cierre": "fallido_por_ceder"}}
    r = carlos.post("/entrenar/ventas/iniciar", {"item": sig["id"], "nivel": sig["nivel"]})
    sid = int(r.headers["location"].rsplit("/", 1)[1])
    carlos.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Le doy 30 % de descuento."})
    carlos.api(f"/api/sesiones/{sid}/terminar")
    assert db.sesion(sid)["estado"] == "completada"
    assert db.nivel(uid, "ventas")["nivel"] == "Principiante"
    # PDF y Excel
    assert carlos.get(f"/sesion/{sid}/reporte.pdf").status_code == 200
    r = carlos.api(f"/api/reporte/{sid}/chat", {"texto": "¿Cómo mejoro mi KPI-1?"})
    assert r.status_code == 200 and r.json()["texto"]


def test_05_refuerzo_por_estancamiento(client, stub):
    carlos: Sesion = ESTADO["carlos"]
    uid = carlos.u["id"]
    stub["celeste.feedback"] = {"kpis": [{"id": f"KPI-{i}", "score": 55, "evidencia": "t", "bien": "b", "mejora": "m"} for i in range(1, 7)]}
    antes = len(db.roadmap_activo(uid, "ventas")["items"])
    for _ in range(4):   # 30 → 55 mejora; luego tres 55 seguidos sin mejora
        item = db.siguiente_item(uid, "ventas")
        r = carlos.post("/entrenar/ventas/iniciar", {"item": item["id"], "nivel": item["nivel"]})
        sid = int(r.headers["location"].rsplit("/", 1)[1])
        carlos.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Hola"})
        carlos.api(f"/api/sesiones/{sid}/terminar")
        assert db.sesion(sid)["estado"] == "completada"
    rm = db.roadmap_activo(uid, "ventas")
    refuerzos = [it for it in rm["items"] if it["tipo"] == "refuerzo"]
    assert refuerzos and len(rm["items"]) == antes + 1
    assert db.nivel(uid, "ventas")["sin_mejora"] == 0


def test_06_juan_artiaga_y_ascenso_dm(client, stub):
    carlos: Sesion = ESTADO["carlos"]
    rrhh: Sesion = ESTADO["rrhh"]
    uid = carlos.u["id"]
    comps = C.competencias_dm("DM2")
    stub["juan.diseno"] = {"formato": "roleplay", "titulo": "Cliente molesto", "personaje": "Lic. Ruiz, gerente", "primer_mensaje": "Buenas tardes, tenemos un problema serio.",
                           "subdimensiones": ["Escucha", "Regulación", "Solución conjunta"], "dificultad_inicial": 3, "encuadre": "e", "situacion": "s"}
    for comp in comps:
        stub["juan.feedback"] = {"score_global": 9.5, "nivel_dominio": "Listo para el siguiente nivel",
                                 "subdimensiones": [{"nombre": "Escucha", "score": 9.5, "evidencia": "x"}, {"nombre": "Regulación", "score": 9.5, "evidencia": "x"}, {"nombre": "Solución conjunta", "score": 9.5, "evidencia": "x"}],
                                 "siguiente_paso": {"competencia": comp, "por_que": "p"}}
        r = carlos.post("/entrenar/ruta_dm/iniciar", {"item": "0", "nivel": "DM1", "competencia": comp, "objetivo": "entrenar"})
        assert r.status_code == 303, r.text
        sid = int(r.headers["location"].rsplit("/", 1)[1])
        ses = db.sesion(sid)
        assert ses["formato"] == "roleplay" and ses["escenario"]["personaje"] == "Lic. Ruiz, gerente"
        assert db.mensajes(sid)[0]["texto"].startswith("Buenas tardes")
        carlos.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Entiendo su molestia; cuénteme qué pasó exactamente."})
        stub["juan.turno"] = {"estado": "fin", "mensaje": "Cerramos el ejercicio."}
        r = carlos.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Propongo un plan conjunto."})
        stub.pop("juan.turno")
        assert r.json()["fin"]
        assert db.sesion(sid)["estado"] == "completada", db.sesion(sid).get("error")
    niv = db.nivel(uid, "ruta_dm")
    assert set(niv["competencias"]) == set(comps)
    props = db.propuestas(carlos.u["empresa_id"], tipo="ascenso_dm")
    assert props and props[0]["detalle"]["a"] == "DM2"
    r = rrhh.post(f"/aprobaciones/{props[0]['id']}", {"decision": "aprobada", "motivo": "evidencia sólida"})
    assert r.status_code == 303
    assert db.nivel(uid, "ruta_dm")["nivel"] == "DM2"
    rm = db.roadmap_activo(uid, "ruta_dm")
    assert rm and all(it["competencia"] in C.competencias_dm("DM3") for it in rm["items"])
    # aprobar roadmap propuesto de entrevistas
    r = rrhh.post(f"/aprobaciones/{ESTADO['prop_roadmap']}", {"decision": "aprobada"})
    assert db.roadmaps(uid, ("activo",)) and any(x["habilidad"] == "entrevistas" for x in db.roadmaps(uid, ("activo",)))


def test_07_tableros_metricas_y_alcance(client, stub):
    rrhh: Sesion = ESTADO["rrhh"]
    carlos: Sesion = ESTADO["carlos"]
    diana = Sesion(client, "diana@condor.mx", ESTADO["claves"]["diana"])
    diana.cambiar_password("ClaveDiana1234")
    dg = Sesion(client, "dg@condor.mx", ESTADO["claves"]["dg"])
    dg.cambiar_password("ClaveDG12345")
    for s, url in ((rrhh, "/rrhh"), (rrhh, "/gestion"), (rrhh, "/aprobaciones"), (rrhh, "/metas"), (rrhh, "/analisis"), (rrhh, "/analista"), (rrhh, "/evaluaciones"),
                   (diana, "/equipo"), (diana, "/metas"), (diana, "/analista"), (dg, "/direccion"), (dg, "/analisis"), (carlos, "/hoy"), (carlos, "/historial"),
                   (carlos, "/catalogo"), (carlos, "/autoevaluacion"), (rrhh, f"/colaborador/{carlos.u['id']}"), (diana, f"/colaborador/{carlos.u['id']}"),
                   (dg, f"/colaborador/{carlos.u['id']}"), (diana, f"/evaluar/{carlos.u['id']}"), (rrhh, "/exportar/tablero.xlsx"), (rrhh, "/exportar/sesiones.xlsx"),
                   (diana, f"/colaborador/{carlos.u['id']}/ficha.pdf"), (rrhh, "/notificaciones")):
        r = s.get(url)
        assert r.status_code == 200, (url, s.email, r.status_code)
    # evaluación del líder y autoevaluación
    r = diana.post(f"/evaluar/{carlos.u['id']}", {"aplica": "5", "comunicacion": "4", "escucha": "4", "presion": "4", "resultados": "4", "comentario": "Se nota"})
    assert r.status_code == 303
    r = carlos.post("/autoevaluacion", {"aplica": "4", "confianza": "4", "habito": "3", "utilidad": "5"})
    assert r.status_code == 303
    k = metrics.kpis_organizacion(rrhh.u["empresa_id"])
    assert k["colaboradores"] == 1 and k["sesiones_total"] >= 9
    assert k["indices"]["participacion"]["valor"] == 100.0
    assert k["indices"]["aplicacion"]["valor"] == 100.0
    assert k["indices"]["iiho"]["valor"] is not None and k["indices"]["madurez"]["valor"] in (1, 2, 3, 4, 5)
    assert k["distribucion_dm"]["DM2"] == 1
    # transcripción: sólo colaborador y RRHH
    sid = db.sesiones(usuario_id=carlos.u["id"], estado="completada", limite=1)[0]["id"]
    assert rrhh.get(f"/sesion/{sid}/reporte").status_code == 200
    assert diana.get(f"/sesion/{sid}/reporte").status_code == 200
    assert "Transcripción completa" in rrhh.get(f"/sesion/{sid}/reporte").text
    assert "Transcripción completa" not in diana.get(f"/sesion/{sid}/reporte").text
    assert diana.get(f"/sesion/{sid}").status_code == 404
    # otro director no ve al colaborador de otra área
    rrhh.post("/gestion/areas", {"nombre": "Oracle", "director_id": "0"})
    rrhh.post("/gestion/usuarios", {"nombre": "Otro Director", "email": "otro@condor.mx", "puesto": "Dir", "rol": "director", "area_id": db.areas(rrhh.u["empresa_id"])[1]["id"]})
    ESTADO.update(diana=diana, dg=dg)


def test_08_analista_chat_metas_y_propuestas(client, stub):
    diana: Sesion = ESTADO["diana"]
    rrhh: Sesion = ESTADO["rrhh"]
    carlos: Sesion = ESTADO["carlos"]
    r = diana.post("/metas", {"habilidad": "ventas", "score_minimo": "80", "plazo": "2026-12-31", "prioridad": "alta", "descripcion": "Cierre de año", "usuario_id": carlos.u["id"]})
    assert r.status_code == 303
    assert db.metas(rrhh.u["empresa_id"])[0]["habilidad"] == "ventas"
    # chat: el stub pide una herramienta y luego responde
    stub["analista.chat.funcion"] = {"name": "ficha_colaborador", "args": {"nombre": "Carlos"}}
    stub["analista.chat"] = "Carlos está en DM2 y su score reciente es 55."
    r = diana.api("/api/analista/chat", {"texto": "¿Cómo va Carlos?"})
    assert r.status_code == 200, r.text
    js = r.json()
    assert js["texto"].startswith("Carlos") and "ficha_colaborador" in js["herramientas"]
    # herramientas con alcance: director sólo su área
    res = analista.ejecutar_herramienta(diana.u, "listar_colaboradores", {})
    assert [c["nombre"] for c in res["colaboradores"]] == ["Carlos Colaborador"]
    res = analista.ejecutar_herramienta(diana.u, "kpis", {})
    assert res["colaboradores"] == 1
    res = analista.ejecutar_herramienta(rrhh.u, "proponer", {"tipo": "refuerzo", "nombre": "Carlos", "titulo": "Refuerzo de objeciones", "detalle": "3 sesiones sin mejora"})
    assert res["ok"]
    inv = analista.investigar("técnicas de manejo de objeciones basadas en evidencia", rrhh.u)
    assert inv["fuentes"] and inv["fuentes"][0]["dominio"] == "example.org"
    assert db.analisis(rrhh.u["empresa_id"], tipo="investigacion")
    # colaborador no puede usar el analista
    assert carlos.api("/api/analista/chat", {"texto": "hola"}).status_code == 403
    # resumen periódico y alertas
    aid = analista.resumen_periodico(rrhh.u["empresa_id"], "organizacion", dias=30)
    assert aid
    assert analista.alertas_inactividad(rrhh.u["empresa_id"]) == 0


def test_09_presupuesto_tope_duro(client, stub):
    carlos: Sesion = ESTADO["carlos"]
    admin: Sesion = ESTADO["admin"]
    r = admin.post("/admin/config", {"modelo_principal": "gemini-3.8-flash", "modelo_ligero": "gemini-3.5-flash-lite", "presupuesto_mxn": "0.0001", "tipo_cambio": "20", "grounding_max_mes": "40"})
    assert r.status_code == 303
    assert db.presupuesto()["agotado"]
    r = carlos.post("/entrenar/ventas/iniciar", {"item": "0", "nivel": "Principiante"})
    assert r.status_code == 503 or r.status_code == 402
    assert "agotó" in carlos.get("/hoy").text
    admin.post("/admin/config", {"modelo_principal": "gemini-3.8-flash", "modelo_ligero": "gemini-3.5-flash-lite", "presupuesto_mxn": "500", "tipo_cambio": "20", "grounding_max_mes": "40"})
    assert not db.presupuesto()["agotado"]
    assert admin.get("/admin/uso").status_code == 200 and admin.get("/admin/bitacora").status_code == 200
    uso = db.uso_periodo()
    assert uso["llamadas"] > 10 and uso["costo_usd"] > 0


def test_10_tokens_por_turno_acotados(client, stub):
    """Cada turno envía sólo instrucciones + ventana reciente; el análisis final recibe la transcripción una vez."""
    from app.llm.gemini import STUB_LLAMADAS
    carlos: Sesion = ESTADO["carlos"]
    STUB_LLAMADAS.clear()
    r = carlos.post("/entrenar/ventas/iniciar", {"item": "0", "nivel": "Avanzado"})
    sid = int(r.headers["location"].rsplit("/", 1)[1])
    for i in range(16):
        carlos.api(f"/api/sesiones/{sid}/mensaje", {"texto": f"Mensaje {i} " + "x" * 200})
    turnos = [c for c in STUB_LLAMADAS if c["origen"] == "celeste.turno"]
    assert turnos
    ultimo = turnos[-1]
    assert len(ultimo["contents"]) <= 14 * 2 + 3
    assert any(c["origen"] == "motor.resumen" for c in STUB_LLAMADAS)   # compresión de memoria al exceder la ventana
    assert ultimo["contents"][0]["text"].startswith("[Memoria")
    carlos.api(f"/api/sesiones/{sid}/terminar")
    fb = [c for c in STUB_LLAMADAS if c["origen"] == "celeste.feedback"]
    assert len(fb) == 1 and "TRANSCRIPCIÓN" in fb[0]["contents"][0]["text"]
