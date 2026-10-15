"""Escenarios nuevos: Presentaciones (voz), Imagen (foto), Comunicación (público general), Liderazgo (test + directores) y el diplomado en la Ruta DM."""
from __future__ import annotations

from app import db
from app.agents import catalogo as C, conocimiento as K, laboratorio as L, socrates as S
from app.agents.avatares import AGENTES, Juan
from app.llm import gemini
from tests.conftest import Sesion, sesion_rrhh
from tests.test_laboratorio import _colaborador_con_diagnostico

FEEDBACK_PRES = {
    "resumen": "Presentó la automatización de actividades a una líder de área con apertura de pregunta.",
    "kpis": [{"id": f"KPI-{i}", "score": s, "evidencia": f"turno {i}", "bien": "b", "mejora": "m"} for i, s in zip(range(1, 10), (80, 70, 75, 60, 55, 65, 70, 85, 90))],
    "fortalezas": [{"habilidad": "Apertura con gancho", "evidencia": "¿Cuánto tiempo pierde tu equipo…?", "por_que_importa": "x"}],
    "oportunidades": [{"habilidad": "Cierre", "evidencia": "terminó con 'eso sería todo'", "impacto": "y", "micro_practica": "z"}],
    "blind_spot": "Repite 'este' al cambiar de idea.", "momentos_clave": [{"turno": 1, "tipo": "destacó", "que_paso": "a", "que_habria_cambiado": "b"}],
    "plan_accion": [{"paso": "p1", "como_medir": "m1"}, {"paso": "p2", "como_medir": "m2"}, {"paso": "p3", "como_medir": "m3"}], "tips": ["t1", "t2", "t3"],
    "pregunta_para_llevarse": "¿Qué quieres que recuerden?", "recomendacion": {"nivel_sugerido": "Intermedio", "objetivo_siguiente": "Cerrar en 30–45 s con un siguiente paso", "razon": "r"},
    "mantener_mejorar_practicar": {"mantener": "La pregunta inicial", "mejorar": "El cierre", "practicar": "Grabar tres cierres"},
}
AUDIO_STUB = {"transcripcion": "Eh, buenos días. ¿Cuánto tiempo pierde tu equipo cada semana en tareas que podrían automatizarse? Hoy veremos, este, cómo una automatización en Odoo…",
              "duracion_s": 62, "palabras": 150, "palabras_por_minuto": 145, "muletillas": 3, "muletillas_detalle": "eh 1, este 2", "pausas_largas": 1, "ritmo": "adecuado",
              "variedad_vocal": "adecuada", "volumen": "adecuado", "energia_cierre": "estable", "seguridad": 3, "observaciones_voz": "Énfasis en 'tiempo'; pausa antes de la pregunta."}


def _llamadas(origen: str) -> list[dict]:
    return [c for c in gemini.STUB_LLAMADAS if c["origen"] == origen]


def test_catalogo_rubricas_y_relevancia():
    for hid in ("presentaciones", "imagen", "comunicacion", "liderazgo"):
        h = C.HABILIDADES[hid]
        assert h["kpis"] and all(sum(p.values()) == 100 for p in h["pesos"].values()) and h["agente"] in AGENTES
    assert C.kpis_audio("presentaciones") == {"KPI-4", "KPI-5", "KPI-9"} and not C.kpis_audio("imagen")
    # público general: el cerrajero ve ventas, imagen y comunicación; nunca Ruta DM ni liderazgo; el hogar sólo comunicación
    assert "liderazgo" not in C.habilidades_que_usa({"contexto": "Tengo mi negocio u oficio", "funciones": ["Atiendo clientes en mi negocio u oficio"]})
    assert C.habilidades_nucleo({"contexto": "Me dedico al hogar y la familia", "funciones": ["Cuido mi hogar / familia"]}) == {"comunicacion"}
    assert C.habilidades_que_usa({"contexto": "Me dedico al hogar y la familia", "funciones": ["Cuido mi hogar / familia"]}) == {"comunicacion"}
    assert "liderazgo" in C.habilidades_que_usa({"contexto": "Trabajo en una empresa", "funciones": ["Lidero personas o proyectos"]})
    assert "presentaciones" in C.habilidades_que_usa({"contexto": "Estudio", "funciones": ["Estudio"]})
    # las categorías nuevas salen de "próximamente"
    assert not any(c["id"] in ("CAT-04", "CAT-05", "CAT-07", "CAT-09") for c in C.PROXIMAMENTE)
    # test de liderazgo
    est = K.estilo_liderazgo(list("aaabbbcccd"))
    assert est["predominante"] == "Directivo" and est["conteo"]["a"] == 3 and est["perfil"]["Indiferente"] == 1
    assert S.temas_biblioteca("presentaciones") and S.temas_biblioteca("imagen") and S.temas_biblioteca("liderazgo")


def test_presentaciones_con_grabacion_de_voz(client, stub):
    vale = _colaborador_con_diagnostico(client, stub, "valentina@condor.mx", "Valentina Voz")
    uid = vale.u["id"]
    assert db.nivel(uid, "presentaciones")   # el diagnóstico deja nivel inicial para los escenarios nuevos
    r = vale.get("/entrenar/presentaciones")
    assert r.status_code == 200 and "grabar tu voz" in r.text and "KPI-5" in r.text and "Valeria" in r.text
    stub["valeria.diseno"] = {"titulo": "Automatización de actividades para la líder de operaciones", "encuadre": "Hoy practicas apertura y presentación de 3 min.",
                              "personaje": "Laura, líder de operaciones", "situacion": "Reunión de 15 min; Laura quiere saber si vale la pena.",
                              "primer_mensaje": "Hola, tengo 15 minutos. ¿De qué me vas a hablar? Graba tu apertura de 30 segundos.", "tarea": "Graba tu apertura de 30 s y después una presentación de 3 min",
                              "duracion_objetivo_s": 180, "dificultad_inicial": 2}
    r = vale.post("/entrenar/presentaciones/iniciar", {"nivel": "Intermedio"})
    assert r.status_code == 303
    sid = int(r.headers["location"].rsplit("/", 1)[1])
    html = vale.get(f"/sesion/{sid}").text
    assert 'id="grabar"' in html and "Tu tarea" in html and "Graba tu apertura" in html
    s = db.sesion(sid)
    assert s["escenario"]["titulo"].startswith("Automatización") and s["escenario"]["duracion_objetivo_s"] == 180
    # grabación: se transcribe (una llamada con adjunto), se guardan transcripción + métricas y el avatar responde
    stub["audio.transcribir"] = AUDIO_STUB
    stub["valeria.turno"] = {"mensaje": "Me interesa. ¿Qué tendría que hacer mi equipo el lunes?", "tension": 40, "estado": "en_curso"}
    r = vale.upload(f"/api/sesiones/{sid}/audio", "grabacion.webm", b"\x1aE\xdf\xa3fake-webm-opus" * 50, "audio/webm", {"duracion": "62"})
    assert r.status_code == 200, r.text
    js = r.json()
    assert js["transcripcion"].startswith("Eh, buenos") and js["audio"]["muletillas"] == 3 and js["mensaje"].startswith("Me interesa")
    llamada = _llamadas("audio.transcribir")[-1]
    assert llamada["contents"][0]["adjuntos"] == 1 and "inline" not in llamada["contents"][0]
    msgs = [m for m in db.mensajes(sid) if m["rol"] == "usuario"]
    assert msgs[-1]["meta"]["audio"]["ppm"] == 145 and msgs[-1]["meta"]["audio"]["muletillas_min"] == 2.9 and "Eh, buenos" in msgs[-1]["texto"]
    assert db.sesion(sid)["escenario"]["grabaciones"] == 1 and db.sesion(sid)["escenario"]["voz_resumen"]["duracion_s"] == 62
    # el avatar recibe la nota entre corchetes (métricas) junto con la transcripción
    turno = _llamadas("valeria.turno")[-1]
    assert any("[Grabación de voz · 1:02" in c["text"] for c in turno["contents"])
    # texto normal + cierre → reporte con métricas de voz y KPIs de voz evaluados
    vale.api(f"/api/sesiones/{sid}/mensaje", {"texto": "El lunes elegimos un proceso piloto y medimos el tiempo actual."})
    stub["valeria.turno"] = {"mensaje": "Perfecto, nos vemos el lunes.", "tension": 20, "estado": "fin"}
    stub["valeria.feedback"] = FEEDBACK_PRES
    r = vale.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Fin"})
    assert r.json()["fin"]
    s = db.sesion(sid)
    assert s["estado"] == "completada"
    res = s["resultado"]
    assert res["voz"]["grabaciones"] == 1 and res["voz"]["muletillas_min"] == 2.9 and res["mantener_mejorar_practicar"]["mejorar"] == "El cierre"
    assert all(k.get("evaluable", True) for k in res["kpis"])
    esperado = round(sum(sc * w for sc, w in zip((80, 70, 75, 60, 55, 65, 70, 85, 90), (12, 15, 12, 12, 10, 10, 9, 12, 8))) / 100, 1)
    assert s["score_global"] == esperado
    fb = _llamadas("valeria.feedback")[-1]
    assert "MÉTRICAS DE VOZ" in fb["system"] and "Toastmasters" in fb["system"] and "[Grabación de voz" in fb["contents"][0]["text"]
    html = vale.get(f"/sesion/{sid}/reporte").text
    assert "Tu voz en esta sesión" in html and "muletillas / min" in html and "Mantener" in html and "Práctica de" not in html
    assert vale.get(f"/sesion/{sid}/reporte.pdf").status_code == 200
    # sesión SIN grabación: los KPIs de voz no cuentan y el score se renormaliza
    r = vale.post("/entrenar/presentaciones/iniciar", {"nivel": "Intermedio"})
    sid2 = int(r.headers["location"].rsplit("/", 1)[1])
    stub["valeria.turno"] = {"mensaje": "Adelante.", "tension": 30, "estado": "en_curso"}
    vale.api(f"/api/sesiones/{sid2}/mensaje", {"texto": "¿Cuánto tiempo pierde tu equipo en capturas manuales? Hoy veremos cómo recuperarlo."})
    stub["valeria.turno"] = {"mensaje": "Gracias.", "tension": 20, "estado": "fin"}
    vale.api(f"/api/sesiones/{sid2}/mensaje", {"texto": "Fin"})
    res2 = db.sesion(sid2)["resultado"]
    sin = [k for k in res2["kpis"] if not k.get("evaluable", True)]
    assert {k["id"] for k in sin} == {"KPI-4", "KPI-5", "KPI-9"} and res2["voz"] is None
    esperado2 = round(sum(sc * w for sc, w in zip((80, 70, 75, 65, 70, 85), (12, 15, 12, 10, 9, 12))) / 70, 1)
    assert db.sesion(sid2)["score_global"] == esperado2
    assert "no evaluado (sin grabación)" in vale.get(f"/sesion/{sid2}/reporte").text
    # validaciones del endpoint
    r = vale.post("/entrenar/presentaciones/iniciar", {"nivel": "Principiante"})
    sid3 = int(r.headers["location"].rsplit("/", 1)[1])
    assert vale.upload(f"/api/sesiones/{sid3}/audio", "x.txt", b"hola", "text/plain").status_code == 400
    assert vale.upload(f"/api/sesiones/{sid3}/audio", "g.webm", b"", "audio/webm").status_code == 400
    assert vale.upload(f"/api/sesiones/{sid3}/foto", "o.jpg", b"\xff\xd8\xff", "image/jpeg").status_code == 400   # presentaciones no usa fotos
    vale.api(f"/api/sesiones/{sid3}/descartar")


def test_imagen_con_foto(client, stub):
    rrhh = sesion_rrhh(client)
    dana = _colaborador_con_diagnostico(client, stub, "dana@condor.mx", "Dana Imagen")
    stub["renata.diseno"] = {"titulo": "Comida con el director de compras", "encuadre": "e", "personaje": "Renata y el director de compras", "situacion": "Comida formal en restaurante del cliente.",
                             "primer_mensaje": "Describe o fotografía el outfit que llevarías a la comida.", "tarea": "Envía una foto o describe tu outfit y luego saluda al director",
                             "duracion_objetivo_s": 0, "dificultad_inicial": 2}
    r = dana.post("/entrenar/imagen/iniciar", {"nivel": "Principiante"})
    sid = int(r.headers["location"].rsplit("/", 1)[1])
    html = dana.get(f"/sesion/{sid}").text
    assert 'id="foto"' in html and 'id="grabar"' not in html
    stub["foto.describir"] = {"es_outfit": True, "descripcion": "Traje azul marino, camisa blanca, corbata gris, zapatos negros de piel.", "codigo_detectado": "formal de negocios",
                              "ajuste": "manga del saco cubre el puño por completo", "cuidado": "camisa planchada", "color": "coherente", "accesorios": "reloj discreto, cinturón café",
                              "detalles_a_revisar": ["calcetines", "largo del pantalón"], "nota_privacidad": "imagen de referencia/catálogo"}
    stub["renata.turno"] = {"mensaje": "Veo el conjunto. ¿Qué calcetín llevas y de qué color es el cinturón?", "tension": 30, "estado": "en_curso"}
    r = dana.upload(f"/api/sesiones/{sid}/foto", "outfit.jpg", b"\xff\xd8\xff\xe0fake-jpeg" * 20, "image/jpeg", {"comentario": "Es un ejemplo que encontré en internet"})
    assert r.status_code == 200, r.text
    js = r.json()
    assert js["foto"]["codigo_detectado"] == "formal de negocios" and js["mensaje"].startswith("Veo el conjunto")
    m = [x for x in db.mensajes(sid) if x["rol"] == "usuario"][-1]
    assert m["meta"]["foto"]["descripcion"].startswith("Traje azul") and "foto de mi outfit" in m["texto"] and "ejemplo que encontré" in m["texto"]
    assert db.sesion(sid)["escenario"]["fotos"] == 1
    turno = _llamadas("renata.turno")[-1]
    assert any("[Foto (imagen de referencia/catálogo)" in c["text"] and "cinturón café" in c["text"] for c in turno["contents"])
    stub["renata.turno"] = {"mensaje": "Buen cierre.", "tension": 10, "estado": "fin"}
    stub["renata.feedback"] = {**{k: v for k, v in FEEDBACK_PRES.items() if k != "kpis"}, "kpis": [{"id": f"KPI-{i}", "score": 70, "evidencia": "e", "bien": "b", "mejora": "m"} for i in range(1, 7)]}
    dana.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Fin"})
    s = db.sesion(sid)
    assert s["estado"] == "completada" and s["score_global"] == 70.0 and s["resultado"]["fotos"] == 1
    fb = _llamadas("renata.feedback")[-1]
    assert "PERFUME" in fb["system"] and "cinturón café" in fb["contents"][0]["text"]
    # RRHH ve el score de imagen en la ficha; la transcripción sigue siendo sólo de RRHH y la persona
    assert rrhh.get(f"/colaborador/{dana.u['id']}").status_code == 200


def test_comunicacion_para_quien_se_dedica_al_hogar(client, stub):
    rrhh = sesion_rrhh(client)
    eid = rrhh.u["empresa_id"]
    r = rrhh.post("/gestion/usuarios", {"nombre": "Doña Mary", "email": "mary@externos.mx", "puesto": "Hogar", "rol": "colaborador", "area_id": db.areas(eid)[0]["id"]})
    clave = r.headers["location"].split("clave=")[1]
    db.limpiar_intentos("ip:testclient")
    mary = Sesion(client, "mary@externos.mx", clave)
    mary.cambiar_password("ClaveMary12345")
    uid = mary.u["id"]
    onb = {"contexto": "Me dedico al hogar y la familia", "funciones": ["Cuido mi hogar / familia"], "industria": "Personas y familias (clientes particulares)", "experiencia": "Más de 5 años",
           "tiempo_semana": "30 min", "meta": "Comunicarme mejor con mi familia y comunidad"}
    assert mary.api("/api/diagnostico/onboarding", {"respuestas": onb}).status_code == 200
    r = mary.post("/diagnostico/iniciar")
    sid = int(r.headers["location"].rsplit("/", 1)[1])
    stub["elena.analisis"] = {"nivel_ventas": "Principiante", "nivel_dm": "DM Básico", "prioridades": [{"habilidad_id": "comunicacion", "brecha": "alta", "razon": "límites con los hijos", "competencias_relacionadas": []}]}
    mary.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Con mi hijo adolescente siempre terminamos gritando."})
    stub["elena.turno"] = {"fase": "fin", "mensaje": "Gracias."}
    mary.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Fin"})
    stub.pop("elena.turno")
    assert db.perfil(uid)["estado"] == "completo"
    assert {r["habilidad"] for r in db.roadmaps(uid)} == {"comunicacion"}
    rel, otras = C.habilidades_relevantes(onb, db.perfil(uid)["diagnostico"], C.habilidades_empresa(db.empresa(eid)))
    assert [h["id"] for h in rel] == ["comunicacion"] and "ruta_dm" in {h["id"] for h in otras} and "liderazgo" in {h["id"] for h in otras}
    html = mary.get("/catalogo").text
    assert "Mateo Ibarra" in html and "Laboratorio DM" not in mary.get("/hoy").text
    # sesión con Mateo como hijo adolescente, con grabación de voz disponible
    stub["mateo.diseno"] = {"titulo": "La hora de llegada del fin de semana", "encuadre": "e", "personaje": "Diego, tu hijo de 16 años", "situacion": "Llegó dos horas tarde el sábado.",
                            "primer_mensaje": "¿Otra vez con lo mismo? Ya te dije que se me fue el tiempo.", "tarea": "Pon un límite claro sin pelear y cierra un acuerdo", "duracion_objetivo_s": 0, "dificultad_inicial": 2}
    r = mary.post("/entrenar/comunicacion/iniciar", {})
    sid = int(r.headers["location"].rsplit("/", 1)[1])
    s = db.sesion(sid)
    assert s["escenario"]["personaje"].startswith("Diego") and s["nivel"] in C.NIVELES_3
    dis = _llamadas("mateo.diseno")[-1]
    assert "Se dedica al hogar" in dis["system"] and "Rosenberg" in dis["system"] and "hijo" in dis["system"]
    assert 'id="grabar"' in mary.get(f"/sesion/{sid}").text
    stub["mateo.turno"] = {"mensaje": "Bueno… ¿y si te aviso a las 10?", "tension": 35, "estado": "en_curso"}
    mary.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Diego, el sábado llegaste a la 1 y me preocupé. Necesito saber que estás bien: ¿puedes avisarme antes de las 11 si vas a tardar?"})
    stub["mateo.turno"] = {"mensaje": "Va, te aviso.", "tension": 15, "estado": "fin"}
    stub["mateo.feedback"] = {**{k: v for k, v in FEEDBACK_PRES.items() if k != "kpis"}, "kpis": [{"id": f"KPI-{i}", "score": 80, "evidencia": "e", "bien": "b", "mejora": "m"} for i in range(1, 7)]}
    mary.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Fin"})
    assert db.sesion(sid)["estado"] == "completada" and db.sesion(sid)["score_global"] == 80.0
    assert "Mantener" in mary.get(f"/sesion/{sid}/reporte").text
    assert S.temas_biblioteca("comunicacion")[0]["tema"].startswith("Comunicación no violenta")


def test_liderazgo_directores_entrenan_con_test_de_estilo(client, stub):
    rrhh = sesion_rrhh(client)
    eid = rrhh.u["empresa_id"]
    area = db.areas(eid)[0]
    r = rrhh.post("/gestion/usuarios", {"nombre": "Diana Directora", "email": "diana.dir@condor.mx", "puesto": "Directora Odoo", "rol": "director", "area_id": area["id"]})
    clave = r.headers["location"].split("clave=")[1]
    db.limpiar_intentos("ip:testclient")
    diana = Sesion(client, "diana.dir@condor.mx", clave)
    diana.cambiar_password("ClaveDiana12345")
    uid = diana.u["id"]
    # navegación y acceso: sólo Liderazgo; sin diagnóstico previo
    html = diana.get("/equipo").text
    assert "Entrenar liderazgo" in html
    assert diana.get("/entrenar/ventas").status_code == 404 and diana.get("/catalogo").status_code == 403
    r = diana.get("/entrenar/liderazgo")
    assert r.status_code == 200 and "¿qué tipo de liderazgo ejerces?" in r.text and "Entrar con Patricia" not in r.text
    # test incompleto → 400; completo → estilo guardado y formulario de inicio
    assert diana.post("/entrenar/liderazgo/test", {"q0": "a"}).status_code == 400
    r = diana.post("/entrenar/liderazgo/test", {f"q{i}": c for i, c in enumerate("ccccaabbcd")})
    assert r.status_code == 303
    est = db.nivel(uid, "liderazgo")["competencias"]["estilo"]
    assert est["predominante"] == "Complaciente"
    r = diana.get("/entrenar/liderazgo")
    assert r.status_code == 200 and "Complaciente" in r.text and "Entrar con Patricia" in r.text
    # sesión: Patricia diseña con el estilo del test y la base del diplomado
    stub["patricia.diseno"] = {"titulo": "El consultor senior que no quiere el cambio de metodología", "encuadre": "e", "personaje": "Marco, consultor senior",
                               "situacion": "Anunciaste que el área adopta el nuevo estándar de documentación y Marco se resiste.", "primer_mensaje": "La verdad no veo para qué cambiar lo que funciona.",
                               "tarea": "Gestiona la resistencia, decide y acuerda siguientes pasos", "duracion_objetivo_s": 0, "dificultad_inicial": 3}
    r = diana.post("/entrenar/liderazgo/iniciar", {"nivel": "Intermedio"})
    assert r.status_code == 303
    sid = int(r.headers["location"].rsplit("/", 1)[1])
    dis = _llamadas("patricia.diseno")[-1]
    assert "Complaciente" in dis["system"] and "Kotter" in dis["system"] and "Grid gerencial" in dis["system"]
    assert db.sesion(sid)["escenario"]["estilo_test"]["predominante"] == "Complaciente"
    assert diana.get(f"/sesion/{sid}").status_code == 200
    stub["patricia.turno"] = {"mensaje": "Ok, pero ¿quién me va a ayudar con la carga?", "tension": 50, "estado": "en_curso"}
    diana.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Marco, entiendo que funciona; el cambio es por los clientes que piden trazabilidad. ¿Qué te preocupa concretamente?"})
    stub["patricia.turno"] = {"mensaje": "Va, lo intento esta semana.", "tension": 20, "estado": "fin"}
    stub["patricia.feedback"] = {**{k: v for k, v in FEEDBACK_PRES.items() if k != "kpis"}, "kpis": [{"id": f"KPI-{i}", "score": 72, "evidencia": "e", "bien": "b", "mejora": "m"} for i in range(1, 7)]}
    diana.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Fin"})
    s = db.sesion(sid)
    assert s["estado"] == "completada" and s["score_global"] == 72.0
    fb = _llamadas("patricia.feedback")[-1]
    assert "ESTILO DE LIDERAZGO del test: Complaciente" in fb["system"]
    assert diana.get(f"/sesion/{sid}/reporte").status_code == 200 and diana.get("/historial").status_code == 200
    # RRHH ve la ficha y el reporte de la directora; su equipo (colaborador) no
    assert rrhh.get(f"/sesion/{sid}/reporte").status_code == 200
    db.limpiar_intentos("ip:testclient")
    vale = Sesion(client, "valentina@condor.mx", "ClaveLab123456")
    assert vale.get(f"/sesion/{sid}/reporte").status_code == 404
    # colaboradores de empresa también tienen Liderazgo en su catálogo (empresa: todas las habilidades)
    assert "Patricia Navarro" in vale.get("/catalogo").text


def test_ruta_dm_y_ventas_con_diplomado_y_objeciones(client, stub):
    base = L.base_conocimiento_texto()
    assert "DIPLOMADO LEAN PROGRESS" in base and "ruta crítica" in base and "Kotter" not in base
    p, _ = Juan.prompt_diseno({"nivel": "DM1", "competencia": "PMBOK", "escenario": {}}, {"nombre": "X", "puesto": ""}, {"onboarding": {}}, [])
    assert "MATERIALES DE REFERENCIA" in p and "PERT" in p
    p, _ = Juan.prompt_feedback({"nivel": "DM2", "competencia": "Delegación", "escenario": {}})
    assert "Liderazgo situacional" in p and "PERT" not in p
    p, _ = Juan.prompt_feedback({"nivel": "DM1", "competencia": "Escucha activa", "escenario": {}})
    assert "MATERIALES DE REFERENCIA" not in p
    mat = S.materiales_internos("ventas")
    assert "todos vendemos" in mat.lower() and "7 segundos" in mat and "Klarić" in mat
    mat = S.materiales_internos("ruta_dm", "Scrum")
    assert "Product Owner" in mat
    assert S.tema_para_item("liderazgo", {"objetivo": "Comunicar un cambio y manejar la resistencia"}) == "Gestión del cambio: Lewin y Kotter"
