"""Público general (externos): un cerrajero con negocio propio sólo ve y entrena lo que le sirve; Cóndor conserva la experiencia completa."""
from __future__ import annotations

from app import db
from app.agents import catalogo as C
from app.llm import gemini
from tests.conftest import Sesion, sesion_rrhh
from tests.test_laboratorio import _colaborador_con_diagnostico  # noqa: F401  (asegura empresa con ruta_dm y RRHH)

ONB_CERRAJERO = {
    "contexto": "Tengo mi negocio u oficio", "funciones": ["Atiendo clientes en mi negocio u oficio"], "industria": "Personas y familias (clientes particulares)",
    "experiencia": "Más de 5 años", "tipo_producto": "Oficio o servicio local (cerrajería, plomería, estética, reparaciones…)", "modelo_venta": "A personas (B2C)",
    "canal_venta": "WhatsApp / chat", "tamano_cliente": "Persona independiente / freelance", "ticket": "Menos de $500", "estilo": "Directo / orientado al cierre",
    "etapa_debil": "Cerrar la venta", "objetivo_ventas": "Cerrar más ventas este mes", "tiempo_semana": "15 min", "meta": "Vender más en mi negocio",
}


def test_cerrajero_externo_solo_ve_lo_que_le_sirve(client, stub):
    rrhh = sesion_rrhh(client)
    eid = rrhh.u["empresa_id"]
    r = rrhh.post("/gestion/usuarios", {"nombre": "Don Chucho", "email": "chucho@externos.mx", "puesto": "Cerrajero", "rol": "colaborador", "area_id": db.areas(eid)[0]["id"]})
    clave = r.headers["location"].split("clave=")[1]
    db.limpiar_intentos("ip:testclient")
    chucho = Sesion(client, "chucho@externos.mx", clave)
    chucho.cambiar_password("ClaveChucho123")
    uid = chucho.u["id"]
    # onboarding sin el grupo Ruta DM (no aplica a negocio propio) y diagnóstico
    assert chucho.api("/api/diagnostico/onboarding", {"respuestas": ONB_CERRAJERO}).status_code == 200
    assert "ruta_dm" not in C.habilidades_que_usa(ONB_CERRAJERO) and C.nivel_dm_estimado(ONB_CERRAJERO) == "DM Básico"
    gemini.STUB_LLAMADAS.clear()
    r = chucho.post("/diagnostico/iniciar")
    sid = int(r.headers["location"].rsplit("/", 1)[1])
    sistema = [x for x in gemini.STUB_LLAMADAS if x["origen"] == "elena.apertura"][-1]["system"]
    assert "Es independiente" in sistema and "Tengo mi negocio u oficio" in sistema and "cerrajero" in sistema.lower()
    chucho.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Un cliente me regateó el cambio de chapa y al final no cerré."})
    stub["elena.turno"] = {"fase": "fin", "mensaje": "Gracias, con esto cierro."}
    stub["elena.analisis"] = {"nivel_ventas": "Intermedio", "nivel_dm": "DM1", "prioridades": [{"habilidad_id": "ventas", "brecha": "alta", "razon": "cierre", "competencias_relacionadas": []},
                                                                                             {"habilidad_id": "entrevistas", "brecha": "baja", "razon": "no aplica", "competencias_relacionadas": []}]}
    chucho.api(f"/api/sesiones/{sid}/mensaje", {"texto": "Fin"})
    stub.pop("elena.turno")
    assert db.perfil(uid)["estado"] == "completo"
    # sólo plan de ventas: nada de Ruta DM ni de entrevistas (aunque la empresa las tenga habilitadas)
    rms = db.roadmaps(uid)
    assert {r["habilidad"] for r in rms} == {"ventas"}
    assert not db.propuestas(eid, tipo="roadmap") or all(p["usuario_id"] != uid for p in db.propuestas(eid, tipo="roadmap"))
    rel, otras = C.habilidades_relevantes(ONB_CERRAJERO, db.perfil(uid)["diagnostico"], C.habilidades_empresa(db.empresa(eid)))
    assert [h["id"] for h in rel] == ["ventas", "imagen", "comunicacion"] and {h["id"] for h in otras} == {"entrevistas", "ruta_dm", "presentaciones", "liderazgo"}
    html = chucho.get("/catalogo").text
    assert "Otras habilidades disponibles" in html and html.index("Clínica de Ventas") < html.index("Ruta Delivery Manager")
    assert "Laboratorio DM" not in chucho.get("/hoy").text
    soc = chucho.get("/socrates").text
    assert "Manejo de objeciones" in soc and "Ruta Delivery Manager" not in soc
    # Celeste se vuelve clienta particular y habla como persona común
    gemini.STUB_LLAMADAS.clear()
    r = chucho.post("/entrenar/ventas/iniciar", {"item": str(db.siguiente_item(uid, "ventas")["id"]), "nivel": "Intermedio", "competencia": ""})
    assert r.status_code == 303
    sistema = [x for x in gemini.STUB_LLAMADAS if x["origen"] == "celeste.apertura"][-1]["system"]
    assert "Clienta particular" in sistema and "madre de familia" in sistema and "Directora de Compras" not in sistema
    # Cóndor (contexto empresa) sigue viendo todo: catálogo sin sección de "otras"
    from tests.test_flujo import ESTADO
    carlos = ESTADO["carlos"]
    assert "Otras habilidades disponibles" not in carlos.get("/catalogo").text
    assert C.habilidades_relevantes(db.perfil(carlos.u["id"])["onboarding"], db.perfil(carlos.u["id"])["diagnostico"], C.habilidades_empresa(db.empresa(eid)))[1] == []
