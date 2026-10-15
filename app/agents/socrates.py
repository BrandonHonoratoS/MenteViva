"""Sócrates: el tutor de Mente Viva. Imparte la parte teórica de cada habilidad como una master class personalizada
(el contexto, los ejemplos y los casos se adaptan al rol, industria, producto y plan de cada persona) y conversa para
resolver dudas o ampliar un punto.

Diseño de costo y calidad
- Una lección se genera UNA vez por persona y tema y se guarda (releerla no cuesta). Dos llamadas:
  1. "dossier" con búsqueda de Google (grounding): hechos, marcos y referencias verificables (autor/obra/organismo + enlaces);
  2. la lección estructurada (JSON con esquema) a partir del dossier + los materiales internos de Mente Viva, sin herramientas.
- El chat de dudas usa la lección guardada como contexto (sin búsqueda), con historial corto.
- Tope mensual de lecciones por persona (SOCRATES_MAX_MES) además del tope duro de presupuesto.
"""
from __future__ import annotations

import logging
import threading

from .. import db
from ..config import settings
from ..llm import PresupuestoAgotado, llm
from ..llm.gemini import ErrorLLM
from . import catalogo as C
from . import esquemas as E
from . import laboratorio as L
from . import prompts as P
from . import validar as V
from .avatares import _texto_perfil, json_compacto

log = logging.getLogger("mv.socrates")

AVATAR = {"nombre": "Sócrates", "rol": "Tutor · master class personalizada", "color": "#0EA5E9", "inicial": "S",
          "descripcion": "Te da la teoría de alto nivel que necesitas antes de practicar: marcos, modelos y casos adaptados a tu trabajo, con fuentes."}

# ── Biblioteca de temas por habilidad ───────────────────────────────────────
TEMAS_VENTAS = [
    ("El ciclo de la venta consultiva (PRAINCODERECI)", "Las 10 etapas y qué decide el cliente en cada una"),
    ("Diagnóstico con preguntas SPIN", "Situación, problema, implicación y necesidad: cómo hacer que el cliente descubra el costo de no actuar"),
    ("Presentación de valor y propuesta", "De características a impacto: estructurar una propuesta que el cliente pueda defender internamente"),
    ("Manejo de objeciones", "Validar, aislar, diagnosticar y las ocho técnicas (boomerang, aikido, sí-y, costo, clarificadora, testimonio, posponer, silencio)"),
    ("Negociación y defensa del precio", "Ancla, concesiones con contraprestación, reencuadre precio→ROI y cuándo decir no"),
    ("Cierre y siguiente paso", "Tipos de cierre, señales de compra, silencio activo y compromisos con fecha"),
    ("Postventa y cuentas que crecen", "Onboarding del cliente, referidos y expansión"),
]
TEMAS_PRESENTACIONES = [
    ("El arte de comunicar una idea", "Propósito, audiencia y mensaje; estructura apertura–desarrollo–cierre; una idea central y tres puntos (Heath, Duarte, Lucas)"),
    ("Aperturas que captan la atención", "Cinco formas de abrir en 30 segundos, conectar necesidad → relevancia → beneficio y los errores que pierden a la audiencia"),
    ("La voz como herramienta de impacto", "Volumen, dicción, ritmo, pausas y énfasis; detectar y reducir muletillas; variedad vocal con intención"),
    ("Seguridad, fluidez y dominio del mensaje", "Preparación mental, respiración y postura; palabras clave en vez de memorizar; qué hacer al perder el hilo; vocabulario preciso"),
    ("De explicar funcionalidades a comunicar valor", "Funcionalidad → beneficio → impacto esperado; descubrir la necesidad antes de explicar; evidencia que respalda (Rackham, Cialdini)"),
    ("Interacción, comprensión y manejo de preguntas", "Validar comprensión con evidencia, escuchar antes de responder, R-C-E-C, qué hacer cuando no sabes y cómo responder objeciones"),
    ("Cómo construir un cierre memorable", "Cinco elementos del cierre, cuatro tipos según el objetivo, la última frase y la energía final"),
    ("La presentación integral de alto impacto", "Checklist de preparación, rúbrica de 9 criterios, retroalimentación mantener–mejorar–practicar y plan individual"),
]
TEMAS_IMAGEN = [
    ("Los cinco códigos de vestimenta", "Formal de negocios, business casual, smart casual, casual y casual viernes: cuándo, qué proyecta cada uno y qué se excluye"),
    ("Ajuste y medidas: el traje, la camisa y el pantalón", "Hombro, puño, caída del pantalón, calcetín, cinturón y zapatos; la talla importa más que la marca"),
    ("Falda, vestido, calzado y accesorios con criterio", "Largos correctos, escote discreto, tacón moderado o zapato bajo elegante, joyería y bolso; ir de pantalón también es formal"),
    ("Color, combinación y cuidado de las prendas", "Neutros de base, un acento, coherencia; planchado, calzado lustrado, grooming y los detalles que delatan"),
    ("Perfume, grooming y los primeros 7 segundos", "Cómo y cuándo aplicar fragancia, postura, mirada, sonrisa y tono: la imagen vendedora y las neuroventas (Klarić)"),
    ("Etiqueta y buenos modales en los negocios", "Puntualidad, saludos, presentaciones, 'usted', celular, comida de negocios y videollamadas"),
]
TEMAS_COMUNICACION = [
    ("Comunicación no violenta: observar, sentir, necesitar, pedir", "El modelo de Rosenberg para pedir sin reclamar en casa y en el trabajo"),
    ("Escucha activa y validación", "Parafrasear, nombrar la emoción, preguntar antes de responder; validar no es dar la razón (Rogers)"),
    ("Asertividad: ni agredir ni ceder", "Mensajes 'yo', DESC, disco rayado, banco de niebla y cómo decir que no"),
    ("Conversaciones difíciles y acuerdos", "Propósito común, hechos antes que conclusiones, seguridad en el diálogo y cierre con responsables y fechas"),
    ("Comunicarse en pareja y en familia", "Los cuatro jinetes de Gottman y sus antídotos; pausas fisiológicas; límites con hijos y familia extendida"),
    ("Claridad y estructura al hablar", "Idea principal primero, PREP, mensaje en tres ideas y verificación de comprensión"),
]
TEMAS_LIDERAZGO = [
    ("Qué es un líder y el grid gerencial", "Tarea vs. personas: directivo, productor, complaciente, indiferente y el estilo de equipo (Blake & Mouton)"),
    ("Liderazgo situacional", "Dirigir, persuadir, participar y delegar según la madurez de cada persona (Hersey & Blanchard)"),
    ("El pentágono del poder", "Poder legítimo, experto, carismático, premiador y coercitivo: con qué sostener la autoridad (French & Raven)"),
    ("Delegar y dar retroalimentación", "Objetivo, responsable, fecha y criterio de éxito; feedback de conducta sin etiquetas; reconocer en público y corregir en privado"),
    ("Gestión del cambio: Lewin y Kotter", "Fuerzas impulsoras y restrictivas, descongelar–cambiar–recongelar y los ocho pasos de Kotter"),
    ("Liderar bajo presión y con equipos ágiles", "Decidir con evidencia, repartir carga, cuidar la fatiga; el líder servicial del Scrum Master"),
]
TEMAS_POR_HABILIDAD = {"presentaciones": TEMAS_PRESENTACIONES, "imagen": TEMAS_IMAGEN, "comunicacion": TEMAS_COMUNICACION, "liderazgo": TEMAS_LIDERAZGO}
TEMAS_ENTREVISTAS = [
    ("Entrevista por competencias (BEI) y método STAR", "Cómo se construye una historia que demuestra una competencia y cómo la lee un entrevistador experto"),
    ("Preparar tu banco de historias", "Inventario de logros, métricas y aprendizajes para cualquier competencia que te pregunten"),
    ("Comunicación bajo presión en entrevistas", "Estructura, síntesis y manejo de preguntas incómodas"),
    ("Preguntas de cierre y negociación de oferta", "Qué preguntar, cómo hablar de expectativas y cómo cerrar con elegancia"),
]


def temas_biblioteca(habilidad_id: str, nivel_dm: str | None = None) -> list[dict]:
    """Temas disponibles para estudiar con Sócrates (libres, además de los ligados al plan)."""
    out = []
    if habilidad_id == "ventas":
        out = [{"tema": t, "descripcion": d, "competencia": ""} for t, d in TEMAS_VENTAS]
    elif habilidad_id == "entrevistas":
        out = [{"tema": t, "descripcion": d, "competencia": ""} for t, d in TEMAS_ENTREVISTAS]
    elif habilidad_id in TEMAS_POR_HABILIDAD:
        out = [{"tema": t, "descripcion": d, "competencia": ""} for t, d in TEMAS_POR_HABILIDAD[habilidad_id]]
    elif habilidad_id == "ruta_dm":
        actual = nivel_dm or "DM Básico"
        sig = C.nivel_dm_siguiente(actual) or actual
        for n in C.RUTA_DM:
            if n["nivel"] in (actual, sig):
                for comp in n["competencias"]:
                    out.append({"tema": comp, "descripcion": f"Competencia de {n['nivel']} · {n['valor']}", "competencia": comp, "nivel": n["nivel"]})
    return out


_PALABRAS_TEMA = [
    (("objeci",), "Manejo de objeciones"), (("cierre", "cerrar", "siguiente paso"), "Cierre y siguiente paso"),
    (("spin", "diagnós", "diagnos", "pregunta"), "Diagnóstico con preguntas SPIN"), (("precio", "negoci", "descuento"), "Negociación y defensa del precio"),
    (("propuesta", "valor", "present"), "Presentación de valor y propuesta"), (("postventa", "referid", "cuenta"), "Postventa y cuentas que crecen"),
    (("star", "historia", "bei"), "Entrevista por competencias (BEI) y método STAR"), (("banco", "logro", "inventario"), "Preparar tu banco de historias"),
    (("presión", "presion", "incómod", "incomod"), "Comunicación bajo presión en entrevistas"), (("oferta", "salario", "expectativ"), "Preguntas de cierre y negociación de oferta"),
    (("apertura", "gancho", "abrir", "inicio"), "Aperturas que captan la atención"), (("voz", "muletilla", "ritmo", "pausa"), "La voz como herramienta de impacto"),
    (("seguridad", "fluidez", "nervio"), "Seguridad, fluidez y dominio del mensaje"), (("valor", "beneficio", "funcionalidad"), "De explicar funcionalidades a comunicar valor"),
    (("pregunta", "interac", "comprensi", "objeci"), "Interacción, comprensión y manejo de preguntas"), (("cierre", "cerrar", "siguiente paso", "memorable"), "Cómo construir un cierre memorable"),
    (("integral", "final", "simulaci", "5 min"), "La presentación integral de alto impacto"), (("idea", "estructura", "síntesis", "sintesis", "claridad"), "El arte de comunicar una idea"),
    (("código", "codigo", "formal", "casual"), "Los cinco códigos de vestimenta"), (("traje", "camisa", "pantal", "saco", "ajuste", "medida"), "Ajuste y medidas: el traje, la camisa y el pantalón"),
    (("falda", "vestido", "tac", "zapato", "accesorio"), "Falda, vestido, calzado y accesorios con criterio"), (("color", "combina", "planch", "cuidado"), "Color, combinación y cuidado de las prendas"),
    (("perfume", "fragancia", "7 segundos", "primera impresi"), "Perfume, grooming y los primeros 7 segundos"), (("etiqueta", "modales", "saludo", "mesa", "comida"), "Etiqueta y buenos modales en los negocios"),
    (("no violenta", "pedir", "petici", "necesidad"), "Comunicación no violenta: observar, sentir, necesitar, pedir"), (("escuch", "valid", "parafras"), "Escucha activa y validación"),
    (("asertiv", "límite", "limite", "decir no"), "Asertividad: ni agredir ni ceder"), (("difícil", "dificil", "acuerdo", "conflicto"), "Conversaciones difíciles y acuerdos"),
    (("pareja", "familia", "hijo", "gottman"), "Comunicarse en pareja y en familia"), (("claridad", "estructura", "prep"), "Claridad y estructura al hablar"),
    (("grid", "estilo", "directivo", "complaciente"), "Qué es un líder y el grid gerencial"), (("situacional", "madurez", "delegar", "dirigir"), "Liderazgo situacional"),
    (("poder", "autoridad", "influencia"), "El pentágono del poder"), (("retroaliment", "feedback", "reconoc", "deleg"), "Delegar y dar retroalimentación"),
    (("cambio", "kotter", "lewin", "resisten"), "Gestión del cambio: Lewin y Kotter"), (("presión", "presion", "ágil", "agil", "scrum", "fatiga"), "Liderar bajo presión y con equipos ágiles"),
]


def tema_para_item(habilidad_id: str, item: dict) -> str:
    """Tema de la master class para un ítem del plan: la competencia (Ruta DM) o el tema de la biblioteca que mejor encaja con el objetivo."""
    if item.get("competencia"):
        return item["competencia"]
    obj = (item.get("objetivo") or "").lower()
    temas = {t for t, _ in (TEMAS_VENTAS if habilidad_id == "ventas" else TEMAS_ENTREVISTAS if habilidad_id == "entrevistas" else TEMAS_POR_HABILIDAD.get(habilidad_id, []))}
    for claves, tema in _PALABRAS_TEMA:
        if tema in temas and any(k in obj for k in claves):
            return tema
    return (item.get("objetivo") or C.HABILIDADES[habilidad_id]["nombre"])[:100]


# ── Materiales internos (fuente de Mente Viva / Cóndor) ─────────────────────
CAT01_RESUMEN = """Guion MenteViva CAT-01 (Clínica de Ventas v3.0): ciclo PRAINCODERECI (Prospección → Precontacto → Presentación → Atención → Interés →
Convicción → Deseo → Resolución → Cierre → Postventa); diagnóstico con SPIN (Situación, Problema, Implicación, Necesidad; las preguntas de
Implicación y Necesidad son las que abren al cliente); en Resolución: Validar → Aislar → Diagnosticar y después una técnica: T-01 Boomerang,
T-02 Aikido, T-03 Sí-Y, T-04 Comparación del costo del problema, T-05 Pregunta clarificadora, T-06 Testimonio, T-07 Posponer, T-08 Silencio activo;
PNL aplicada (reencuadre precio→ROI, espejeo, anclas, lenguaje de presuposición); regla: un descuento prematuro sin valor demostrado sube la
resistencia del cliente; ceder sin contraprestación no cuenta como cierre exitoso. KPIs que mide Celeste: KPI-1 diagnóstico (preguntas I/N),
KPI-2 manejo de objeciones, KPI-3 argumentación de valor, KPI-4 cierre, KPI-5 negociación, KPI-6 ética y relación."""

RUTA_DM_RESUMEN = """Ruta Delivery Manager (Ingeniería Cóndor): el DM no es un cargo sino un modelo de desarrollo de 7 niveles (DM Básico → DM1 … DM5 →
Emprendedor); cada nivel desbloquea un "valor" (aprender a trabajar profesionalmente → asesorar → liderar personas → liderar conocimiento e
innovación → construir soluciones → generar negocio → crear empresas). Filosofía: el valor ya no está en saber más que el cliente sino en crear
valor que no puede generar solo; el asesor identifica oportunidades y acompaña al resultado. ADN: creatividad mexicana + disciplina china +
valores (honestidad, responsabilidad, excelencia, lealtad). Cuatro pilares: Cultura, Técnico, Interpersonal (el corazón) y Profesional (Ikigai,
Flow, bienestar)."""

ENTREVISTAS_RESUMEN = """Entrevista por competencias (BEI, Behavioral Event Interview) y método STAR (Situación, Tarea, Acción, Resultado): el
entrevistador busca evidencia conductual pasada, no opiniones; profundiza en tres niveles (qué hiciste tú exactamente, qué pensaste/decidiste,
qué resultado medible); señales de historia débil: generalidades, "nosotros" sin tu parte, sin métrica, sin aprendizaje. KPIs que mide Elena:
estructura STAR, especificidad y evidencia, autoconciencia (aprendizajes y errores), comunicación, ajuste al puesto."""

_MAPA_DM_LAB = {"Escucha activa": "escucha", "Manejo de ansiedad": "estres", "Resiliencia": "estres", "PMBOK": "pmbok", "Comunicación": "comunicacion",
                "Influencia": "comunicacion", "Gestión de conflictos": "escucha", "Gestión de clientes": "escucha", "Retroalimentación": "escucha",
                "Delegación": "estres", "Toma de decisiones": "pmbok", "PMO": "pmbok", "Gestión del cambio": "pmbok", "Scrum": "pmbok"}


def materiales_internos(habilidad_id: str, competencia: str = "", empresa_id: int | None = None) -> str:
    from . import estandares as ES
    partes = []
    est = ES.bloque(empresa_id, habilidad_id)
    if est:
        partes.append("ESTÁNDAR DE LA EMPRESA DE LA PERSONA (prioritario: enseña su metodología y sus términos; lo genérico de Mente Viva sólo como complemento cuando no contradiga):" + est)
    from . import conocimiento as K
    if habilidad_id == "ventas":
        partes.append(CAT01_RESUMEN)
        partes.append(K.OBJECIONES_TECNICOS)
        partes.append("Imagen vendedora y neuroventas (resumen): " + K.IMAGEN.split("NEUROVENTAS")[-1][:1200])
    elif habilidad_id == "entrevistas":
        partes.append(ENTREVISTAS_RESUMEN)
    elif habilidad_id == "ruta_dm":
        partes.append(RUTA_DM_RESUMEN)
        dim = _MAPA_DM_LAB.get(competencia)
        if dim and dim in L.BASE_CONOCIMIENTO:
            partes.append(f"Taller DM2 · {L.dimension(dim)['nombre']}:\n{L.BASE_CONOCIMIENTO[dim]}")
        if competencia in _COMPETENCIAS_DIPLOMADO or not competencia:
            partes.append(K.DIPLOMADO_PM)
        if competencia in ("Delegación", "Desarrollo gerencial", "Gestión del cambio", "Retroalimentación", "Influencia", "Gestión de conflictos"):
            partes.append(K.LIDERAZGO)
    elif habilidad_id in K.BASES:
        partes.append(K.base(habilidad_id))
    return "\n\n".join(partes)


_COMPETENCIAS_DIPLOMADO = {"PMBOK", "Scrum", "Toma de decisiones", "Administración de recursos", "PMO", "Gestión del cambio", "Finanzas", "ROI", "Accountability",
                           "Autogestión", "Gestión de clientes", "Innovación operativa"}


# ── Contexto personal ───────────────────────────────────────────────────────
def contexto_persona(usuario: dict, habilidad_id: str, item: dict | None = None, competencia: str = "") -> dict:
    perfil = db.perfil(usuario["id"])
    ob = perfil.get("onboarding", {})
    diag = perfil.get("diagnostico") or {}
    niv = db.nivel(usuario["id"], habilidad_id) or {}
    metas = [{"score_minimo": m["score_minimo"], "competencia": m.get("competencia"), "plazo": m.get("plazo"), "descripcion": m.get("descripcion")}
             for m in (db.metas(usuario["empresa_id"], area_id=usuario.get("area_id"), usuario_id=usuario["id"]) if usuario.get("empresa_id") else [])
             if m["habilidad"] == habilidad_id]
    ultimas = [s for s in db.sesiones(usuario_id=usuario["id"], habilidad=habilidad_id, estado="completada", limite=3) if s["tipo"] in ("practica", "laboratorio")]
    brechas = []
    for s in ultimas:
        res = s.get("resultado") or {}
        brechas += [o.get("habilidad") for o in res.get("oportunidades", [])][:2] + [b.get("brecha") for b in res.get("brechas", [])][:2]
    return {
        "perfil": _texto_perfil(usuario, ob, diag, incluir_ventas=habilidad_id == "ventas"),
        "vende_algo": bool(ob.get("tipo_producto")) and habilidad_id == "ventas",
        "producto": ob.get("producto_concreto") or ob.get("tipo_producto") or "",
        "nivel_actual": niv.get("nivel") or C.HABILIDADES[habilidad_id]["niveles"][0],
        "competencia": competencia, "objetivo_sesion": (item or {}).get("objetivo") or "", "porque_sesion": (item or {}).get("porque") or "",
        "metas_lider": metas, "brechas_recientes": [b for b in brechas if b][:4],
        "estilo": diag.get("estilo_comunicacion") or "",
    }


# ── Generación ──────────────────────────────────────────────────────────────
def obtener_o_crear(usuario: dict, habilidad_id: str, tema: str, competencia: str = "", item: dict | None = None, en_hilo: bool = True) -> dict:
    """Devuelve la lección del tema para la persona; si no existe la crea (estado 'generando') y lanza la generación."""
    hab = C.habilidad(habilidad_id)
    if not hab:
        raise ValueError("Habilidad desconocida")
    existente = db.leccion_por_tema(usuario["id"], habilidad_id, tema)
    if existente and existente["estado"] in ("lista", "generando"):
        if item and not existente.get("roadmap_item_id"):
            db.actualizar_leccion(existente["id"], roadmap_item_id=item["id"])
        return db.leccion(existente["id"])
    if db.lecciones_mes(usuario["id"]) >= settings.SOCRATES_MAX_MES:
        raise ErrorLLM(f"Alcanzaste el máximo de {settings.SOCRATES_MAX_MES} lecciones nuevas este mes. Puedes releer las que ya tienes o pedir más a RRHH.")
    lid = db.crear_leccion(usuario["id"], habilidad_id, tema, competencia=competencia, roadmap_item_id=(item or {}).get("id"))
    if en_hilo and not settings.ANALISIS_SINCRONO:
        threading.Thread(target=generar, args=(lid,), daemon=True, name=f"socrates-{lid}").start()
    else:
        generar(lid)
    return db.leccion(lid)


def clave_base(usuario: dict, habilidad_id: str, tema: str, nivel: str) -> tuple[str, str]:
    """Perfil compartible: dos personas con el mismo tema, nivel, rol (vende / no vende / lidera) y giro reutilizan la misma base."""
    ob = db.perfil(usuario["id"]).get("onboarding", {})
    f = set(ob.get("funciones") or [])
    rol = "vende" if f & {"Vendo o asesoro a clientes", "Genero negocio nuevo"} else ("lidera" if "Lidero personas o proyectos" in f else "ejecuta")
    giro = (ob.get("tipo_producto") if rol == "vende" else ob.get("industria")) or "general"
    from . import estandares as ES
    perfil = f"{rol}:{giro}:{ES.huella(usuario.get('empresa_id'), habilidad_id)}"
    return f"{habilidad_id}|{tema.strip().lower()}|{nivel}|{perfil}", perfil


def generar(leccion_id: int) -> None:
    lec = db.leccion(leccion_id)
    if not lec or lec["estado"] == "lista":
        return
    usuario = db.usuario(lec["usuario_id"])
    item = db.roadmap_item(lec["roadmap_item_id"]) if lec.get("roadmap_item_id") else None
    hab = C.HABILIDADES[lec["habilidad"]]
    try:
        ctx = contexto_persona(usuario, lec["habilidad"], item, lec.get("competencia") or "")
        clave, perfil = clave_base(usuario, lec["habilidad"], lec["tema"], ctx["nivel_actual"])
        base = db.leccion_base(clave)
        costo = 0.0
        if base and base.get("contenido"):
            # Reutilización: la base (mismo tema, nivel y perfil) se adapta a la persona con el modelo ligero (~1/5 del costo)
            fuentes_web = [f for f in (base.get("fuentes") or []) if f.get("url")]
            system = P.SOCRATES_ADAPTAR.format(nombre=usuario["nombre"], habilidad=hab["nombre"], tema=lec["tema"])
            entrada = {"contexto_persona": ctx, "leccion_base": base["contenido"]}
            r = llm.generar(origen="socrates.adaptar", system=system, contents=[{"role": "user", "text": json_compacto(entrada)}], schema=E.LECCION,
                            clase="ligero", thinking="low", max_tokens=12000, temperatura=0.4, usuario_id=usuario["id"])
            if not isinstance(r.json, dict):
                raise ErrorLLM("Sócrates no pudo adaptar la lección. Pulsa Reintentar.")
            V.registrar_si_incompleto("socrates.adaptar", r.json, usuario.get("email", ""))
            contenido = V.leccion(r.json, lec["tema"], fuentes_web)
            # el núcleo (marcos, comparativa, errores, fuentes) viene de la base; si la adaptación lo perdió, se restaura
            for k in ("marcos", "comparativa", "errores_comunes", "fuentes", "mapa_mermaid"):
                if not contenido.get(k):
                    contenido[k] = base["contenido"].get(k)
            db.usar_leccion_base(clave)
            costo = float(r.costo_usd)
            origen = f"base compartida #{base['id']} ({perfil})"
        else:
            # 1) dossier con búsqueda: hechos verificables y referencias
            r1 = llm.generar(origen="socrates.investigar", system=P.SOCRATES_INVESTIGAR,
                             contents=[{"role": "user", "text": f"TEMA: {lec['tema']} (habilidad: {hab['nombre']}{' · competencia ' + lec['competencia'] if lec.get('competencia') else ''}).\n"
                                                                  f"PERFIL DE QUIEN APRENDE: {ctx['perfil']}"}],
                             grounding=True, thinking="low", max_tokens=3500, temperatura=0.2, usuario_id=usuario["id"])
            dossier = r1.texto or ""
            fuentes_web = r1.fuentes or []
            # 2) lección estructurada (sin herramientas, con esquema)
            system = P.SOCRATES_LECCION.format(nombre=usuario["nombre"], habilidad=hab["nombre"], tema=lec["tema"], materiales=materiales_internos(lec["habilidad"], lec.get("competencia") or "", usuario.get("empresa_id")))
            entrada = {"contexto_persona": ctx, "dossier_con_fuentes": dossier[:9000], "fuentes_web": [{"titulo": f["titulo"], "url": f["url"]} for f in fuentes_web][:10]}
            r2 = llm.generar(origen="socrates.leccion", system=system, contents=[{"role": "user", "text": json_compacto(entrada)}], schema=E.LECCION,
                             thinking=settings.GEMINI_THINKING_ANALISIS, max_tokens=14000, temperatura=0.5, usuario_id=usuario["id"])
            if not isinstance(r2.json, dict):
                raise ErrorLLM("Sócrates no pudo estructurar la lección. Pulsa Reintentar.")
            V.registrar_si_incompleto("socrates.leccion", r2.json, usuario.get("email", ""))
            contenido = V.leccion(r2.json, lec["tema"], fuentes_web)
            db.guardar_leccion_base(clave, lec["habilidad"], lec["tema"], ctx["nivel_actual"], perfil, contenido, fuentes_web, dossier[:9000])
            costo = float(r1.costo_usd) + float(r2.costo_usd)
            origen = "generada de cero (queda como base para perfiles iguales)"
        db.actualizar_leccion(leccion_id, estado="lista", titulo=contenido["titulo"], contenido_json=contenido, fuentes_json=contenido["fuentes"],
                              lista_en=db.now(), error="", costo_usd=round(costo, 5))
        db.log("info", "socrates", f"Lección {leccion_id}: {origen}", f"{lec['habilidad']} · {lec['tema']} · {costo * settings.TIPO_CAMBIO_MXN_USD:.2f} MXN", usuario["email"])
        db.notificar(usuario["id"], f"Sócrates preparó tu master class: {contenido['titulo'][:60]}", "Léela antes de tu siguiente práctica.", f"/socrates/{leccion_id}", "exito")
        db.log("info", "socrates", f"Lección {leccion_id} lista", f"{lec['habilidad']} · {lec['tema']} · {len(contenido['fuentes'])} fuentes", usuario["email"])
    except (PresupuestoAgotado, ErrorLLM) as e:
        db.actualizar_leccion(leccion_id, estado="error", error=str(e))
        db.log("warn", "socrates", f"Lección {leccion_id} sin generar", str(e), usuario["email"])
    except Exception as e:  # noqa: BLE001
        log.exception("Fallo generando lección %s", leccion_id)
        db.actualizar_leccion(leccion_id, estado="error", error=f"Error interno: {e}")
        db.log("error", "socrates", f"Lección {leccion_id} error interno", str(e), usuario["email"])


def reintentar(leccion_id: int) -> None:
    lec = db.leccion(leccion_id)
    if lec and lec["estado"] == "error":
        db.actualizar_leccion(leccion_id, estado="generando", error="")
        if settings.ANALISIS_SINCRONO:
            generar(leccion_id)
        else:
            threading.Thread(target=generar, args=(leccion_id,), daemon=True).start()


# ── Chat de dudas sobre la lección ──────────────────────────────────────────
def chat(usuario: dict, lec: dict, texto: str) -> dict:
    ambito = f"leccion:{lec['id']}"
    ch = db.obtener_chat(usuario["id"], ambito, "Sócrates")
    db.guardar_chat_mensaje(ch["id"], "usuario", texto)
    c = lec.get("contenido") or {}
    compacto = {k: c.get(k) for k in ("titulo", "idea_central", "marcos", "proceso", "errores_comunes", "caso", "checklist", "fuentes") if c.get(k) is not None}
    ctx = contexto_persona(usuario, lec["habilidad"], None, lec.get("competencia") or "")
    system = P.SOCRATES_CHAT.format(nombre=usuario["nombre"], tema=lec["tema"], perfil=ctx["perfil"]) + "\nLECCIÓN:\n" + json_compacto(compacto)
    hist = [m for m in ch["mensajes"] if m["rol"] in ("usuario", "socrates")][-8:]
    contents = [{"role": "user" if m["rol"] == "usuario" else "model", "text": m["texto"]} for m in hist]
    if not contents or contents[-1]["text"] != texto:
        contents.append({"role": "user", "text": texto})
    r = llm.generar(origen="socrates.chat", system=system, contents=contents, thinking="low", max_tokens=1500, temperatura=0.5, usuario_id=usuario["id"])
    db.guardar_chat_mensaje(ch["id"], "socrates", r.texto)
    return {"texto": r.texto}
