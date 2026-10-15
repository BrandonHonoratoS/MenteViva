"""Sócrates: master class personalizada ligada al plan y a la biblioteca, dos pasos (dossier con búsqueda → lección con esquema), chat de dudas,
tope mensual y reintento."""
from __future__ import annotations

from app import db
from app.llm import gemini
from tests.test_laboratorio import _colaborador_con_diagnostico

LECCION = {
    "titulo": "Manejo de objeciones para vender software a manufactura", "gancho": "Las objeciones son información, no rechazo.",
    "idea_central": "Validar, aislar y diagnosticar antes de responder.", "duracion_min": 15,
    "mapa_mermaid": "```mermaid\nflowchart TD\n  A[\"Objeción\"] --> B[\"Validar\"]\n  B --> C[\"Aislar\"]\n  C --> D[\"Diagnosticar\"]\n  D --> E[\"Técnica T-01..T-08\"]\n```",
    "marcos": [{"nombre": "SPIN Selling", "origen": "Neil Rackham (1988)", "que_es": "x", "como_aplicarlo": "y", "ejemplo": "Cliente de manufactura: …"}] * 3,
    "proceso": [{"nombre": f"Paso {i}", "que_hacer": "a", "frase_o_accion": "b", "error_tipico": "c"} for i in range(1, 5)],
    "comparativa": [{"situacion": "s", "enfoque_debil": "d", "enfoque_experto": "e"}] * 3,
    "errores_comunes": [{"error": "Descuento prematuro", "por_que_ocurre": "miedo", "alternativa": "reencuadre"}] * 3,
    "caso": {"titulo": "La planta que decía que era caro", "narrativa": "…", "lectura": "…"},
    "preguntas_socraticas": [{"pregunta": "¿Qué cuesta no actuar?", "pista": "p", "respuesta_modelo": "r"}] * 4,
    "checklist_practica": ["Validar antes de responder", "Aislar la objeción", "Pregunta de implicación", "No descontar", "Cerrar con fecha"],
    "cierre": "Nos vemos en la práctica.",
    "fuentes": [{"autor_u_organismo": "Neil Rackham", "obra": "SPIN Selling", "anio": "1988", "url": "", "para_que": "Diagnóstico"},
                {"autor_u_organismo": "Harvard Business Review", "obra": "The New Sales Imperative", "anio": "2017", "url": "https://hbr.org/x", "para_que": "Evidencia"},
                {"autor_u_organismo": "Mente Viva", "obra": "Guion CAT-01", "anio": "2026", "url": "", "para_que": "Técnicas T-01..T-08"}],
}


def test_socrates_plan_biblioteca_chat_y_tope(client, stub):
    vale = _colaborador_con_diagnostico(client, stub, "vale@condor.mx", "Vale Sócrates")
    uid = vale.u["id"]
    r = vale.get("/socrates")
    assert r.status_code == 200 and "Prepárate con Sócrates" in r.text and "Manejo de objeciones" in r.text
    assert "Prepárate con Sócrates" in vale.get("/hoy").text
    # lección ligada al siguiente ítem del plan de ventas
    sig = db.siguiente_item(uid, "ventas")
    stub["socrates.investigar"] = "DOSSIER: Rackham (1988) SPIN Selling… Referencias: Neil Rackham — SPIN Selling (1988)."
    stub["socrates.leccion"] = LECCION
    gemini.STUB_LLAMADAS.clear()
    r = vale.post("/socrates/estudiar", {"habilidad": "ventas", "tema": "Manejo de objeciones", "competencia": "", "item": str(sig["id"])})
    assert r.status_code == 303
    lid = int(r.headers["location"].rsplit("/", 1)[1])
    lec = db.leccion(lid)
    assert lec["estado"] == "lista" and lec["roadmap_item_id"] == sig["id"], lec.get("error")
    c = lec["contenido"]
    assert c["titulo"].startswith("Manejo de objeciones") and c["mapa_mermaid"].startswith("flowchart TD") and "```" not in c["mapa_mermaid"]
    assert len(c["fuentes"]) >= 3 and c["fuentes"][1]["url"] == "https://hbr.org/x"
    llamadas = [x for x in gemini.STUB_LLAMADAS if x["origen"].startswith("socrates.")]
    assert [x["origen"] for x in llamadas] == ["socrates.investigar", "socrates.leccion"]
    assert llamadas[0]["grounding"] is True and "PERFIL DE QUIEN APRENDE" in llamadas[0]["contents"][0]["text"]
    texto_leccion = llamadas[1]["contents"][0]["text"]
    assert "contexto_persona" in texto_leccion and "dossier_con_fuentes" in texto_leccion and "Manufactura" in texto_leccion   # personalización con el onboarding
    assert "PRAINCODERECI" in llamadas[1]["system"]                                                                            # materiales internos de ventas
    r = vale.get(f"/socrates/{lid}")
    assert r.status_code == 200 and "Mapa conceptual" in r.text and "Preguntas socráticas" in r.text and "SPIN Selling" in r.text
    assert db.leccion(lid)["leida_en"]
    # misma persona + mismo tema → no se vuelve a generar
    gemini.STUB_LLAMADAS.clear()
    r = vale.post("/socrates/estudiar", {"habilidad": "ventas", "tema": "Manejo de objeciones", "competencia": "", "item": "0"})
    assert r.headers["location"].endswith(f"/socrates/{lid}") and not [x for x in gemini.STUB_LLAMADAS if x["origen"].startswith("socrates.")]
    # chat de dudas con la lección como contexto
    r = vale.api(f"/api/socrates/{lid}/chat", {"texto": "¿Cómo aplico aikido si el cliente ya tiene proveedor?"})
    assert r.status_code == 200 and r.json()["texto"]
    assert "LECCIÓN:" in gemini.STUB_LLAMADAS[-1]["system"] and "Vale Sócrates" in gemini.STUB_LLAMADAS[-1]["system"]
    # Hoy muestra "Releer" cuando la lección del siguiente ítem ya existe; el plan tiene el botón Teoría
    assert "Sócrates" in vale.get("/hoy").text
    assert "📘 Teoría" in vale.get("/roadmaps").text
    # biblioteca Ruta DM: competencias del nivel actual y el siguiente
    r = vale.get("/socrates")
    assert "Gestión de conflictos" in r.text and "Escucha activa" in r.text
    # tope mensual
    from app.config import settings
    settings.SOCRATES_MAX_MES = 1
    r = vale.post("/socrates/estudiar", {"habilidad": "ventas", "tema": "Cierre y siguiente paso", "competencia": "", "item": "0"})
    assert r.status_code == 303 and "/socrates?error=" in r.headers["location"]
    assert "máximo de 1 lecciones" in vale.get(r.headers["location"]).text
    settings.SOCRATES_MAX_MES = 12
    # error de la IA → estado error + reintentar
    stub["socrates.leccion"] = {"titulo": ""}
    from app.agents import socrates as S
    original = S.llm.generar
    def falla(**kw):
        from app.llm.gemini import ErrorLLM
        raise ErrorLLM("El modelo de IA está saturado en este momento (alta demanda).")
    S.llm.generar = falla
    r = vale.post("/socrates/estudiar", {"habilidad": "ruta_dm", "tema": "Gestión de conflictos", "competencia": "Gestión de conflictos", "item": "0"})
    lid2 = int(r.headers["location"].rsplit("/", 1)[1])
    assert db.leccion(lid2)["estado"] == "error"
    assert "Reintentar" in vale.get(f"/socrates/{lid2}").text
    S.llm.generar = original
    stub["socrates.leccion"] = LECCION
    assert vale.post(f"/socrates/{lid2}/reintentar").status_code == 303
    assert db.leccion(lid2)["estado"] == "lista"
    assert "Taller DM2" in [x for x in gemini.STUB_LLAMADAS if x["origen"] == "socrates.leccion"][-1]["system"]   # materiales de la Ruta DM


def test_socrates_reutiliza_base_para_perfiles_iguales(client, stub):
    """Juan y Pedro (mismo rol, giro, nivel y tema): la segunda lección se adapta con el modelo ligero sin volver a investigar ni construir."""
    juan = _colaborador_con_diagnostico(client, stub, "juan.v@condor.mx", "Juan Vendedor")
    pedro = _colaborador_con_diagnostico(client, stub, "pedro.v@condor.mx", "Pedro Vendedor")
    stub["socrates.investigar"] = "DOSSIER…"
    stub["socrates.leccion"] = LECCION
    gemini.STUB_LLAMADAS.clear()
    r = juan.post("/socrates/estudiar", {"habilidad": "ventas", "tema": "Cierre y siguiente paso", "competencia": "", "item": "0"})
    l1 = db.leccion(int(r.headers["location"].rsplit("/", 1)[1]))
    assert l1["estado"] == "lista" and [x["origen"] for x in gemini.STUB_LLAMADAS if x["origen"].startswith("socrates.")] == ["socrates.investigar", "socrates.leccion"]
    from app.agents import socrates as S
    clave, perfil = S.clave_base(db.usuario(juan.u["id"]), "ventas", "Cierre y siguiente paso", "Principiante")
    base = db.leccion_base(clave)
    assert base and perfil == "vende:Software / SaaS:mv" and base["contenido"]["titulo"] == LECCION["titulo"]   # "mv" = estándar Mente Viva (la empresa no definió otro)
    gemini.STUB_LLAMADAS.clear()
    stub["socrates.adaptar"] = {**LECCION, "gancho": "Pedro, en tu cuenta de manufactura…", "marcos": []}   # la IA omite marcos → se restauran de la base
    r = pedro.post("/socrates/estudiar", {"habilidad": "ventas", "tema": "Cierre y siguiente paso", "competencia": "", "item": "0"})
    l2 = db.leccion(int(r.headers["location"].rsplit("/", 1)[1]))
    llamadas = [x for x in gemini.STUB_LLAMADAS if x["origen"].startswith("socrates.")]
    assert l2["estado"] == "lista" and [x["origen"] for x in llamadas] == ["socrates.adaptar"] and llamadas[0]["grounding"] is False
    assert "leccion_base" in llamadas[0]["contents"][0]["text"] and "Pedro Vendedor" in llamadas[0]["contents"][0]["text"]
    assert l2["contenido"]["gancho"].startswith("Pedro") and len(l2["contenido"]["marcos"]) == 3 and db.leccion_base(clave)["usos"] == 1
    # el briefing de la sesión (modalidad completa) muestra a Sócrates en 60 segundos con la lección existente
    stub["socrates.adaptar"] = LECCION
    sig = db.siguiente_item(pedro.u["id"], "ventas")
    pedro.post("/socrates/estudiar", {"habilidad": "ventas", "tema": S.tema_para_item("ventas", sig), "competencia": "", "item": str(sig["id"])})
    r = pedro.get(f"/entrenar/ventas?item={sig['id']}")
    assert r.status_code == 200 and "Sócrates en 60 segundos" in r.text
    pedro.post("/cuenta/preferencias", {"modalidad": "micro", "correo_notif": "1"})
    assert "Sócrates en 60 segundos" not in pedro.get(f"/entrenar/ventas?item={sig['id']}").text   # en 5 minutos, Sócrates sólo en su apartado
