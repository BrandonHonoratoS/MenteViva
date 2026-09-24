"""Puebla una base LOCAL con datos simulados para revisar la interfaz sin API key (LLM_PROVEEDOR=stub).

Uso:  DATA_DIR=./data_demo LLM_PROVEEDOR=stub ANALISIS_SINCRONO=1 python scripts/demo_local.py
Crea: empresa Ingeniería Cóndor, 2 áreas, 2 directores, 6 colaboradores con diagnóstico y sesiones, evaluaciones y análisis.
Credenciales: todos con contraseña Demo12345678 (ver salida). NUNCA usar en producción.
"""
from __future__ import annotations

import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("LLM_PROVEEDOR", "stub")
os.environ.setdefault("ANALISIS_SINCRONO", "1")
os.environ.setdefault("SCHEDULE_ENABLED", "0")
os.environ.setdefault("EMPRESA_INICIAL", "Ingeniería Cóndor")
os.environ.setdefault("RRHH_INICIAL_EMAIL", "rrhh@demo.mx")
os.environ.setdefault("RRHH_INICIAL_PASSWORD", "Demo12345678")
os.environ.setdefault("SUPERADMIN_EMAIL", "admin@menteviva.mx")
os.environ.setdefault("SUPERADMIN_PASSWORD", "Demo12345678")

from app import db  # noqa: E402
from app.agents import analista, catalogo as C, motor, roadmap  # noqa: E402
from app.llm import gemini  # noqa: E402

random.seed(7)
CLAVE = "Demo12345678"
db.init_db()
empresa = db.empresas()[0]
EID = empresa["id"]
with db.conn() as con:
    con.execute("UPDATE usuarios SET debe_cambiar_password=0")

areas = {a["nombre"]: a for a in db.areas(EID)}
for nombre in ("Odoo", "Oracle"):
    if nombre not in areas:
        db.crear_area(EID, nombre)
areas = {a["nombre"]: a for a in db.areas(EID)}

PERSONAS = [
    ("Diana Rivera", "diana@demo.mx", "director", "Odoo", "Directora Odoo"),
    ("Óscar Luna", "oscar@demo.mx", "director", "Oracle", "Director Oracle"),
    ("Daniel Vega", "dg@demo.mx", "dg", None, "Director General"),
    ("Carlos Méndez", "carlos@demo.mx", "colaborador", "Odoo", "Consultor funcional"),
    ("Lucía Ortiz", "lucia@demo.mx", "colaborador", "Odoo", "Consultora senior"),
    ("Mariana Soto", "mariana@demo.mx", "colaborador", "Odoo", "Delivery Manager"),
    ("Jorge Pérez", "jorge@demo.mx", "colaborador", "Oracle", "Consultor técnico"),
    ("Areli Campos", "areli@demo.mx", "colaborador", "Oracle", "Ejecutiva comercial"),
    ("Bertín Haro", "bertin@demo.mx", "colaborador", "Oracle", "Consultor junior"),
]
usuarios = {u["email"]: u for u in db.usuarios(EID, activos=None)}
for nombre, email, rol, area, puesto in PERSONAS:
    if email not in usuarios:
        uid = db.crear_usuario(email, CLAVE, nombre, rol, EID, areas[area]["id"] if area else None, puesto, debe_cambiar=False)
        if rol == "director":
            db.actualizar_area(areas[area]["id"], director_id=uid)
usuarios = {u["email"]: u for u in db.usuarios(EID, activos=None)}

ONB = {
    "funciones": ["Vendo o asesoro a clientes", "Ejecuto proyectos / consultoría"], "industria": "Manufactura / industria", "experiencia": "2 a 5 años",
    "tipo_producto": "Software / SaaS", "modelo_venta": "A empresas (B2B)", "canal_venta": "Videollamada", "tamano_cliente": "Mediana empresa (100–500)",
    "ticket": "$5,000 — $50,000", "estilo": "Consultivo / asesor", "etapa_debil": "Manejar objeciones", "objetivo_ventas": "Mejorar mi tasa de conversión",
    "dm_lidera": "No lidero a nadie", "dm_trabajo": "Asesorar al cliente", "dm_antiguedad": "6 meses a 2 años", "dm_representa": "A veces, acompañado",
    "tiempo_semana": "1 hora", "meta": "Ascender en la ruta de desarrollo", "producto_concreto": "Implementación de Odoo para PYMES",
}
FORT = [("Escucha activa", "Cuando contaste sobre el cliente de Monterrey, preguntaste tres veces antes de proponer", "En asesoría, entender antes de proponer construye confianza"),
        ("Orientación a resultados", "Cuantificaste el ahorro: '18 % menos horas de captura'", "El siguiente nivel exige hablar en números del cliente"),
        ("Resolución de problemas", "Describiste el árbol de causas de la falla de facturación", "Diagnosticar es el corazón del asesor")]
OPOR = [("Estructura del discurso", "Saltaste del problema al resultado sin contar qué hiciste tú", "El cliente no ve tu aporte", "Cuenta una historia en STAR cada día en voz alta, 2 minutos"),
        ("Manejo de objeciones", "Ante 'está caro' ofreciste descuento en el turno 3", "Regalas margen sin construir valor", "Practica Validar-Aislar-Diagnosticar con 3 objeciones"),
        ("Control emocional", "Al escuchar el NO cambiaste de tema", "Se percibe inseguridad", "Usa un silencio de 5 segundos después de cada pregunta de cierre")]


def diag_stub(nivel_v, nivel_dm, brechas):
    return {"resumen_ejecutivo": "Se presentó con energía y ejemplos reales; comunica bien el contexto pero diluye su aporte personal. Patrón dominante: explica el 'qué' y poco el 'cómo'.",
            "fortalezas": [{"habilidad": a, "evidencia": b, "por_que_importa": c} for a, b, c in FORT[:2]],
            "oportunidades": [{"habilidad": a, "evidencia": b, "impacto": c, "micro_practica": d} for a, b, c, d in OPOR[:2]],
            "blind_spot": "Tiende a usar 'nosotros' cuando el logro fue suyo: se resta protagonismo frente al cliente.",
            "pregunta_para_llevarse": "¿Qué parte de tu último proyecto solo pudo pasar porque tú estabas ahí?",
            "competencias": [{"nombre": c, "nivel": random.choice([2, 3, 3, 4, 4]), "justificacion": "Evidencia en la historia del cliente de manufactura."} for c in C.COMPETENCIAS_DIAGNOSTICO],
            "estilo_comunicacion": "consultivo y relacional", "nivel_ventas": nivel_v, "nivel_ventas_justificacion": "Narró dos negociaciones con estructura parcial.",
            "nivel_dm": nivel_dm, "nivel_dm_justificacion": "Asesora al cliente con autonomía; aún no lidera personas.", "nivel_entrevistas": "Principiante",
            "prioridades": [{"habilidad_id": h, "brecha": b, "razon": r, "competencias_relacionadas": []} for h, b, r in brechas],
            "mensaje_para_la_persona": "Gracias por la honestidad. Tienes material valioso; ahora vamos a convertirlo en hábito."}


def feedback_ventas(base):
    kp = [max(20, min(98, int(random.gauss(base, 9)))) for _ in range(6)]
    return {"resumen": "Vendiste una implementación de Odoo a una directora de compras escéptica. Patrón dominante: buenas preguntas de situación, pocas de implicación; cerraste con un siguiente paso sin fecha.",
            "kpis": [{"id": f"KPI-{i+1}", "score": kp[i], "evidencia": f"Turno {random.randint(2, 9)}: “{random.choice(['¿Cuánto les cuesta hoy un error de captura?', 'Entiendo, y además del precio, ¿qué más le preocupa?', 'Le puedo dar 10 % ahora mismo'])}”",
                       "bien": "Validaste antes de responder.", "mejora": "Aísla la objeción antes de aplicar la técnica."} for i in range(6)],
            "evidencia": {"tecnicas_usadas": [{"id": "T-02", "turno": 4}, {"id": "T-04", "turno": 7}], "spin": {"S": 3, "P": 2, "I": random.randint(0, 3), "N": random.randint(0, 2)},
                          "etapas_cumplidas": ["Presentación", "Atención", "Interés", "Convicción"], "turno_primer_descuento": random.choice([0, 0, 3, 6]), "uso_silencio_activo": random.random() > .5,
                          "objeciones_lanzadas": 3, "objeciones_resueltas": random.randint(1, 3), "cierre": random.choice(["siguiente_paso", "sin_cierre", "siguiente_paso", "venta"])},
            "fortalezas": [{"habilidad": a, "evidencia": b, "por_que_importa": c} for a, b, c in random.sample(FORT, 2)],
            "oportunidades": [{"habilidad": a, "evidencia": b, "impacto": c, "micro_practica": d} for a, b, c, d in random.sample(OPOR, 2)],
            "momentos_clave": [{"turno": 3, "tipo": "destacó", "que_paso": "Preguntaste por el costo del problema antes de hablar del producto.", "que_habria_cambiado": "—"},
                               {"turno": 7, "tipo": "falló", "que_paso": "Ofreciste descuento sin contraprestación.", "que_habria_cambiado": "Pedir la firma antes de fin de mes a cambio del 10 %."}],
            "plan_accion": [{"paso": "Prepara 3 preguntas de implicación por reunión", "como_medir": "Ratio I+N/S+P > 1 en la siguiente sesión"},
                            {"paso": "Ensaya Validar-Aislar-Diagnosticar con la objeción de precio", "como_medir": "0 descuentos antes del turno 10"},
                            {"paso": "Cierra siempre con fecha", "como_medir": "Siguiente paso con día y hora"}],
            "tips": ["Antes de responder 'está caro', pregunta 'caro comparado con qué'.", "Cuando la clienta dé un número real, repítelo antes de continuar.", "Un silencio de 5 segundos vale más que un argumento más."],
            "pregunta_para_llevarse": "¿Qué te hizo ofrecer descuento en ese momento?", "metrica_etapa_debil": "Resolviste 2 de 3 objeciones; en la anterior fueron 1 de 3.",
            "recomendacion": {"nivel_sugerido": "Intermedio" if base > 72 else "Principiante", "objetivo_siguiente": "Maneja 3 objeciones sin ceder en precio y cierra con fecha", "razon": "Ya domina la apertura; falta resistencia en Resolución."}}


def feedback_dm(base10, comp):
    subs = ["Escucha del otro lado", "Regulación emocional", "Búsqueda de solución conjunta", "Firmeza sin agresión"]
    sc = [round(max(2, min(10, random.gauss(base10, .8))), 1) for _ in subs]
    g = round(sum(sc) / len(sc), 1)
    return {"resumen": f"Entrenaste {comp} en un roleplay con un gerente molesto. Mantuviste la calma y buscaste acuerdos; te faltó firmeza al fijar límites.",
            "subdimensiones": [{"nombre": n, "score": s, "evidencia": "Turno 4: “Entiendo su molestia, cuénteme qué pasó”."} for n, s in zip(subs, sc)],
            "score_global": g, "nivel_dominio": C.dominio_dm(g), "justificacion": "Escucha sólida; la firmeza aparece tarde y con disculpas.",
            "fortalezas": [{"habilidad": "Escucha", "evidencia": "“¿Qué necesitaría ver para confiar de nuevo?”", "por_que_importa": "En DM2 gestionas clientes en conflicto."}],
            "brechas": [{"brecha": "Firmeza", "evidencia": "Turno 6: aceptaste una fecha imposible.", "impacto_siguiente_nivel": "Compromisos incumplibles dañan al equipo.", "causa_probable": "Evitar el conflicto inmediato."}],
            "momento_clave": {"que_hizo": "Aceptó la fecha del cliente sin negociar.", "alternativa": "Ofrecer dos opciones realistas.", "que_habria_cambiado": "Credibilidad y control del alcance."},
            "plan_accion": [{"paso": "Prepara dos alternativas antes de cada reunión difícil", "como_practicar_esta_semana": "En la junta del jueves", "senal_de_logro": "Ninguna fecha aceptada sin alternativa"}],
            "tips": ["Nombra la emoción del otro antes de proponer.", "Di 'no puedo eso, sí puedo esto'.", "Cierra con un resumen de acuerdos."],
            "siguiente_paso": {"competencia": random.choice(C.competencias_dm("DM2")), "por_que": "Complementa la gestión de conflictos con delegación."}}


gemini.STUB_OVERRIDES["juan.diseno"] = {"formato": "roleplay", "titulo": "Cliente molesto por un retraso", "personaje": "Lic. Ruiz, gerente de operaciones",
                                        "encuadre": "Gestión de conflictos es clave para DM2: representarás a Cóndor ante un cliente molesto.",
                                        "situacion": "El go-live se retrasó dos semanas; el gerente exige una fecha hoy.", "primer_mensaje": "Buenas tardes. Le seré directo: llevamos dos semanas de retraso y mi director quiere una fecha hoy. ¿Qué me va a decir?",
                                        "subdimensiones": ["Escucha del otro lado", "Regulación emocional", "Búsqueda de solución conjunta", "Firmeza sin agresión"], "dificultad_inicial": 3}
gemini.STUB_OVERRIDES["elena.roadmap"] = {"objetivo": "Pasar de Principiante a Intermedio manejando objeciones sin ceder", "razon": "Primero estructura y escucha; luego presión con objeciones encadenadas; al final cierres con fecha.",
                                          "items": [{"semana": 1, "nivel": "Principiante", "competencia": "", "objetivo": o, "porque": "Progresión de fundamentos a presión."} for o in
                                                    ["Ejecuta las 8 etapas en orden y genera curiosidad en 20 palabras", "Haz 2 preguntas de implicación antes de presentar", "Maneja 2 objeciones con Validar-Aislar-Técnica",
                                                     "Cierra con un siguiente paso con fecha", "Sobrevive el primer NO sin ofrecer descuento", "Integra SPIN completo y cierra"] * 3]}
gemini.STUB_OVERRIDES["analista.post_sesion"] = {"lectura": "La sesión confirma avance en escucha; el patrón de descuento prematuro persiste en presión. Con dos sesiones más así, estaría lista para subir de nivel.",
                                                  "riesgo": "medio", "riesgo_motivo": "Cede en precio bajo presión.", "recomendacion_lider": "Acompáñala en una llamada real esta semana y observa el momento del primer descuento.",
                                                  "siguiente_objetivo": "Maneja 3 objeciones sin ceder en precio", "ajuste_plan": "ninguno", "ajuste_motivo": "Progresión dentro de lo esperado.",
                                                  "senales": ["I+N/S+P = 0.8", "descuento en turno 6", "cierre sin fecha"]}
gemini.STUB_OVERRIDES["analista.resumen"] = {"titulo": "Semana con avance sostenido en Odoo", "resumen": "El área Odoo practicó 9 sesiones con score promedio 68 (+6 vs. semana anterior). Lucía y Mariana avanzan en objeciones; Carlos lleva 8 días sin practicar. Oracle arranca con 4 sesiones y buen engagement.",
                                              "avanzan": ["Lucía Ortiz (+9)", "Mariana Soto (+5)"], "atencion": ["Carlos Méndez: 8 días sin sesión"],
                                              "recomendaciones": [{"accion": "Agenda 15 min con Carlos para desbloquear su práctica", "responsable": "Diana Rivera", "senal_exito": "1 sesión esta semana", "prioridad": "alta"},
                                                                  {"accion": "Registrar evaluación del líder del periodo", "responsable": "Directores", "senal_exito": "100 % evaluados", "prioridad": "media"},
                                                                  {"accion": "Meta de KPI-1 ≥ 75 para el equipo comercial", "responsable": "RRHH", "senal_exito": "Meta activa", "prioridad": "media"}]}

def _retrodatar(sid, dias):
    t = (datetime.now(timezone.utc) - timedelta(days=dias, minutes=random.randint(0, 600))).isoformat(timespec="seconds")
    with db.conn() as con:
        con.execute("UPDATE sesiones SET inicio=?, fin=? WHERE id=?", (t, t, sid))
        con.execute("UPDATE mensajes SET creado_en=? WHERE sesion_id=?", (t, sid))


colabs = [u for u in db.usuarios(EID, rol="colaborador")]
PERFILES = {"carlos@demo.mx": (62, 4.5, 8, "Principiante"), "lucia@demo.mx": (78, 7.5, 1, "Intermedio"), "mariana@demo.mx": (84, 8.8, 0, "Avanzado"),
            "jorge@demo.mx": (55, 5.5, 2, "Principiante"), "areli@demo.mx": (70, 6.0, 1, "Intermedio"), "bertin@demo.mx": (48, 4.0, 12, "Principiante")}
for u in colabs:
    if db.perfil(u["id"]).get("estado") == "completo":
        continue
    base, base10, inact, nivel_v = PERFILES.get(u["email"], (60, 5, 3, "Principiante"))
    ob = dict(ONB)
    if "comercial" not in (u.get("puesto") or "").lower() and "senior" not in (u.get("puesto") or "").lower():
        ob["funciones"] = ["Vendo o asesoro a clientes", "Ejecuto proyectos / consultoría"]
    db.guardar_perfil(u["id"], onboarding=ob, estado="onboarding")
    gemini.STUB_OVERRIDES["elena.turno"] = {"fase": "fin", "mensaje": "Gracias, con esto tengo muy buen material."}
    gemini.STUB_OVERRIDES["elena.analisis"] = diag_stub(nivel_v, "DM1" if base < 80 else "DM2", [("ventas", "alta" if base < 70 else "media", "Objeciones y cierre"), ("entrevistas", "baja", "Estructura STAR")])
    s = motor.iniciar(db.usuario(u["id"]), "entrevistas", tipo="diagnostico", nivel="Intermedio", objetivo="Diagnóstico inicial de competencias")
    db.guardar_perfil(u["id"], estado="entrevista", sesion_diagnostico_id=s["id"])
    for i in range(3):
        motor.turno(db.sesion(s["id"]), db.usuario(u["id"]), "En el proyecto de manufactura yo coordiné la migración con el cliente…")
    motor.terminar(db.sesion(s["id"]), db.usuario(u["id"]), en_hilo=False)
    _retrodatar(s["id"], 40)
    gemini.STUB_OVERRIDES.pop("elena.turno", None)
    # sesiones de práctica retrodatadas
    n_ses = random.randint(4, 8)
    for k in range(n_ses):
        dias = 36 - k * (30 // n_ses) - random.randint(0, 2)
        if k == n_ses - 1:
            dias = inact
        gemini.STUB_OVERRIDES["celeste.feedback"] = feedback_ventas(base + k * 2)
        gemini.STUB_OVERRIDES["celeste.turno"] = {"estado": "en_curso", "mensaje": random.choice(["Voy al grano: ¿por qué debería cambiar de proveedor?", "Esto está muy caro, vi opciones más baratas.", "¿Y cómo sé que van a cumplir?"]), "tension": random.randint(30, 85), "etapa": "Resolución"}
        item = db.siguiente_item(u["id"], "ventas")
        ses = motor.iniciar(db.usuario(u["id"]), "ventas", item=item, voluntaria=item is None)
        for t in range(random.randint(3, 6)):
            motor.turno(db.sesion(ses["id"]), db.usuario(u["id"]), random.choice(["¿Qué le preocupa hoy de su operación?", "Entiendo. ¿Comparado con qué le parece caro?", "Le propongo una sesión diagnóstica el martes a las 10."]))
        motor.terminar(db.sesion(ses["id"]), db.usuario(u["id"]), en_hilo=False)
        _retrodatar(ses["id"], dias)
        if k % 2 == 1:
            gemini.STUB_OVERRIDES["juan.feedback"] = feedback_dm(base10 + k * .2, "Gestión de conflictos")
            gemini.STUB_OVERRIDES["juan.turno"] = {"estado": "en_curso", "mensaje": "Eso no me resuelve nada. Necesito una fecha.", "tension": random.randint(40, 90)}
            item = db.siguiente_item(u["id"], "ruta_dm")
            ses = motor.iniciar(db.usuario(u["id"]), "ruta_dm", item=item, voluntaria=item is None)
            for t in range(3):
                motor.turno(db.sesion(ses["id"]), db.usuario(u["id"]), "Entiendo la urgencia; déjeme proponerle dos alternativas realistas.")
            motor.terminar(db.sesion(ses["id"]), db.usuario(u["id"]), en_hilo=False)
            _retrodatar(ses["id"], dias)
    # evaluaciones
    d = db.area(u["area_id"])
    if d and d.get("director_id"):
        db.guardar_evaluacion("lider", d["director_id"], u["id"], db.periodo(), {"aplica": random.randint(3, 5), "comunicacion": 4, "escucha": random.randint(3, 5), "presion": 3, "resultados": 4}, "Se nota en las juntas.")
    db.guardar_evaluacion("auto", u["id"], u["id"], db.periodo(), {"aplica": 4, "confianza": 4, "habito": 3, "utilidad": 5})

for a in db.areas(EID):
    analista.resumen_periodico(EID, "area", area_id=a["id"], dias=30)
analista.resumen_periodico(EID, "organizacion", dias=30)
analista.alertas_inactividad(EID)
rr = db.usuarios(EID, rol="rrhh")[0]
db.crear_meta(EID, "ventas", rr["id"], area_id=areas["Odoo"]["id"], score_minimo=75, plazo="2026-12-15", prioridad="alta", descripcion="Equipo comercial listo para el cierre de año")
inv = analista.investigar("Evidencia sobre práctica deliberada y feedback inmediato en habilidades de venta", rr)
print("Listo. Usuarios (contraseña Demo12345678):")
for u in db.usuarios(EID, activos=None):
    print(f"  {u['rol']:12} {u['email']}")
print("  superadmin   admin@menteviva.mx")
