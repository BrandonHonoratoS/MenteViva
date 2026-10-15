"""Definición de los avatares (Elena, Celeste, Juan): instrucciones por sesión, apertura y rúbrica de feedback.

Cada avatar expone:
- system(sesion, usuario, perfil) → instrucciones de sistema (bloque estable primero)
- schema_turno → esquema JSON del turno
- apertura(sesion) → primer mensaje o pista para que el modelo abra
- prompt_feedback(sesion) → (instrucciones, esquema) para el análisis final
- score(resultado, sesion) → score global 0–100 y detalle
"""
from __future__ import annotations

import json

from . import catalogo as C
from . import esquemas as E
from . import estandares as ES
from . import prompts as P

AVATARES = {
    "elena": {"nombre": "Elena Ríos", "rol": "Entrevistadora por competencias", "color": "#3B82F6", "inicial": "E",
              "descripcion": "Te entrevista con método BEI + STAR, diagnostica tus competencias y diseña tus roadmaps."},
    "celeste": {"nombre": "Celeste López", "rol": "Clienta exigente · Clínica de Ventas", "color": "#7C3AED", "inicial": "C",
                "descripcion": "Una clienta analítica que no compra por simpatía: revela si dominas la venta o improvisas."},
    "juan": {"nombre": "Juan Artiaga", "rol": "Mentor · Ruta Delivery Manager", "color": "#10B981", "inicial": "J",
             "descripcion": "Diagnostica tu nivel DM y entrena, con roleplay, casos o retos, las competencias del siguiente nivel."},
    "valeria": {"nombre": "Valeria Campos", "rol": "Audiencia exigente · Presentaciones de alto impacto", "color": "#F59E0B", "inicial": "V",
                "descripcion": "Es tu público: escucha, pregunta, objeta y se distrae si pierdes el hilo. Graba tu voz y mide apertura, síntesis, voz, muletillas, interacción, cierre y tiempo."},
    "renata": {"nombre": "Renata Solís", "rol": "Consultora de imagen y etiqueta", "color": "#D946EF", "inicial": "R",
               "descripcion": "Te pone en situaciones reales (cliente, dirección, entrevista, comida de negocios) y evalúa tu outfit —descrito o en foto— y tus modales con los cinco códigos de vestimenta."},
    "mateo": {"nombre": "Mateo Ibarra", "rol": "Interlocutor · comunicación cotidiana", "color": "#EC4899", "inicial": "M",
              "descripcion": "Interpreta a la persona con quien necesitas hablar (pareja, hijo, jefe, vecino, cliente) y revela si comunicas con claridad, escucha, asertividad y acuerdo."},
    "patricia": {"nombre": "Patricia Navarro", "rol": "Integrante del equipo · Liderazgo", "color": "#10B981", "inicial": "P",
                 "descripcion": "Es la persona de tu equipo que hay que dirigir, escuchar, corregir o convencer; mide tu claridad, adaptación situacional, retroalimentación, decisión y gestión del cambio."},
    "analista": {"nombre": "El Analista", "rol": "Inteligencia de desarrollo", "color": "#F59E0B", "inicial": "A",
                 "descripcion": "Lee todas las sesiones, recalcula planes y niveles, y orienta a líderes y RRHH con evidencia."},
}


def _texto_perfil(usuario: dict, onboarding: dict, diagnostico: dict | None = None, incluir_ventas: bool = True) -> str:
    lineas = [f"Nombre: {usuario['nombre']}. Puesto/ocupación: {usuario.get('puesto') or 'no indicado'}. Área: {usuario.get('area_nombre') or 'no indicada'}."]
    if onboarding:
        rol = ", ".join(onboarding.get("funciones") or []) or "no indicado"
        ctx = onboarding.get("contexto", "")
        if ctx:
            lineas.append(f"Situación de vida: {ctx}. " + {"Tengo mi negocio u oficio": "Es independiente: sus 'clientes' son personas o negocios que lo contratan directamente; no hay jefes, áreas ni corporativo.",
                                                          "Estudio": "Es estudiante: sus situaciones vienen de la escuela, proyectos, servicio social, trabajos de medio tiempo y su futuro empleo.",
                                                          "Me dedico al hogar y la familia": "Se dedica al hogar: sus situaciones vienen de la familia, la comunidad, la escuela de los hijos, trámites y negociaciones cotidianas.",
                                                          "Estoy buscando empleo": "Busca empleo: sus situaciones vienen de trabajos anteriores, entrevistas y su red de contactos."}.get(ctx, "Trabaja en una organización con equipos, clientes y jefes."))
        lineas.append(f"Lo que hace en su día a día: {rol}. Con quién trata: {onboarding.get('industria', '')}. Experiencia: {onboarding.get('experiencia', '')}.")
        if incluir_ventas and onboarding.get("tipo_producto"):
            lineas.append(f"Vende: {onboarding.get('tipo_producto')} · a {onboarding.get('modelo_venta')} · canal {onboarding.get('canal_venta')} · "
                          f"clientes {onboarding.get('tamano_cliente')} · ticket {onboarding.get('ticket')} · estilo {onboarding.get('estilo')} · "
                          f"etapa débil: {onboarding.get('etapa_debil')} · objetivo: {onboarding.get('objetivo_ventas')}.")
        if onboarding.get("dm_trabajo") or onboarding.get("dm_lidera"):
            lineas.append(f"Ruta DM: lidera → {onboarding.get('dm_lidera', '')}; trabajo → {onboarding.get('dm_trabajo', '')}; antigüedad → "
                          f"{onboarding.get('dm_antiguedad', '')}; representa a la empresa → {onboarding.get('dm_representa', '')}.")
        lineas.append(f"Tiempo semanal: {onboarding.get('tiempo_semana', '')}. Meta: {onboarding.get('meta', '')}.")
    if diagnostico:
        lineas.append(f"Estilo de comunicación observado: {diagnostico.get('estilo_comunicacion', '')}. "
                      f"Fortalezas: {'; '.join(f['habilidad'] for f in diagnostico.get('fortalezas', []))}. "
                      f"Oportunidades: {'; '.join(o['habilidad'] for o in diagnostico.get('oportunidades', []))}.")
    return "\n".join(lineas)


def _kpis_texto(hab: dict, nivel: str) -> str:
    pesos = hab["pesos"].get(nivel, {})
    return "\n".join(f"- {k['id']} {k['nombre']} (peso {pesos.get(k['id'], 0)} %): {k['que']}" for k in hab["kpis"])


def score_ponderado(hab: dict, nivel: str, kpis: list[dict]) -> float:
    pesos = hab["pesos"].get(nivel) or hab["pesos"][hab["niveles"][0]]
    total = sum(pesos.values()) or 100
    return round(sum(float(k.get("score", 0)) * pesos.get(k.get("id", ""), 0) for k in kpis) / total, 1)


# ── Elena ────────────────────────────────────────────────────────────────────
class Elena:
    id = "elena"
    schema_turno = E.TURNO_ELENA_DIAG

    @staticmethod
    def system(sesion: dict, usuario: dict, perfil: dict) -> str:
        if sesion["tipo"] == "diagnostico":
            return P.ELENA_DIAGNOSTICO.format(turnos_objetivo=C.turnos_max("entrevistas", "Intermedio"),
                                              perfil=_texto_perfil(usuario, perfil.get("onboarding", {})))
        ob = perfil.get("onboarding", {})
        esc = sesion.get("escenario") or {}
        nivel = sesion.get("nivel") or "Principiante"
        return P.ELENA_PRACTICA.format(nivel=nivel, config_nivel=P.ELENA_PRACTICA_NIVELES.get(nivel, ""),
                                       puesto=esc.get("puesto") or usuario.get("puesto") or "su puesto actual",
                                       industria=ob.get("industria", "no indicada"),
                                       competencias_foco=", ".join(esc.get("competencias_foco") or ["Comunicación", "Resolución de problemas", "Trabajo en equipo", "Orientación a resultados"]),
                                       objetivo=sesion.get("objetivo") or "practicar historias STAR completas",
                                       turnos_objetivo=C.turnos_max("entrevistas", nivel), estandar=ES.bloque(sesion.get("empresa_id"), "entrevistas"))

    @staticmethod
    def schema_para(sesion: dict) -> dict:
        return E.TURNO_ELENA_DIAG if sesion["tipo"] == "diagnostico" else E.TURNO_ELENA_PRACT

    @staticmethod
    def apertura(sesion: dict) -> tuple[str | None, str]:
        if sesion["tipo"] == "diagnostico":
            return None, "(La persona acaba de entrar a la entrevista de diagnóstico. Salúdala por su nombre y abre con calidez.)"
        return None, "(La persona acaba de entrar a la entrevista. Salúdala y abre con calidez.)"

    @staticmethod
    def prompt_feedback(sesion: dict) -> tuple[str, dict]:
        hab = C.HABILIDADES["entrevistas"]
        nivel = sesion.get("nivel") or "Principiante"
        return (P.FEEDBACK_ENTREVISTAS.format(kpis=_kpis_texto(hab, nivel), nivel=nivel, objetivo=sesion.get("objetivo") or "—", reglas=P.REGLAS_FEEDBACK,
                                              estandar=ES.bloque(sesion.get("empresa_id"), "entrevistas")), E.FEEDBACK_ENTREVISTAS)

    @staticmethod
    def score(resultado: dict, sesion: dict) -> float:
        return score_ponderado(C.HABILIDADES["entrevistas"], sesion.get("nivel") or "Principiante", resultado.get("kpis", []))


# ── Celeste ──────────────────────────────────────────────────────────────────
class Celeste:
    id = "celeste"
    schema_turno = E.TURNO_CELESTE

    @staticmethod
    def system(sesion: dict, usuario: dict, perfil: dict) -> str:
        ob = perfil.get("onboarding", {})
        nivel = sesion.get("nivel") or "Principiante"
        contexto = (f"Vende: {ob.get('tipo_producto', 'no indicado')}. Modelo: {ob.get('modelo_venta', 'no indicado')}. "
                    f"Industria de sus clientes: {ob.get('industria', 'no indicada')}. Tamaño típico del cliente: {ob.get('tamano_cliente', 'no indicado')}. "
                    f"Ticket promedio: {ob.get('ticket', 'no indicado')} (a mayor ticket, pides más justificación, tiempo y pruebas). "
                    f"Experiencia del vendedor: {ob.get('experiencia', 'no indicada')}. Estilo declarado: {ob.get('estilo', 'no indicado')}. "
                    f"Etapa débil declarada: {ob.get('etapa_debil', 'no indicada')} (concentra ahí el 60 % de la presión). "
                    f"Producto concreto de esta sesión: {(sesion.get('escenario') or {}).get('producto') or 'el que el vendedor presente; pregúntale qué ofrece si no queda claro'}.")
        return P.CELESTE.format(personaje=P.personaje_celeste(ob), nivel=nivel, config_nivel=P.CELESTE_NIVELES.get(nivel, P.CELESTE_NIVELES["Principiante"]),
                                objeciones="\n".join(P.CELESTE_OBJECIONES.get(nivel, P.CELESTE_OBJECIONES["Principiante"])), contexto=contexto,
                                canal=ob.get("canal_venta", "cara a cara"), objetivo=sesion.get("objetivo") or "ejecutar el ciclo completo",
                                estandar=ES.bloque(sesion.get("empresa_id"), "ventas"))

    @staticmethod
    def schema_para(sesion: dict) -> dict:
        return E.TURNO_CELESTE

    @staticmethod
    def apertura(sesion: dict) -> tuple[str | None, str]:
        return None, "(El vendedor llega a la reunión contigo. Abre la conversación como Celeste recibiéndolo, según tu nivel.)"

    @staticmethod
    def prompt_feedback(sesion: dict) -> tuple[str, dict]:
        hab = C.HABILIDADES["ventas"]
        nivel = sesion.get("nivel") or "Principiante"
        esc = sesion.get("escenario") or {}
        return (P.FEEDBACK_VENTAS.format(kpis=_kpis_texto(hab, nivel), nivel=nivel, objetivo=sesion.get("objetivo") or "—",
                                         etapa_debil=esc.get("etapa_debil") or "no declarada", reglas=P.REGLAS_FEEDBACK,
                                         estandar=ES.bloque(sesion.get("empresa_id"), "ventas")), E.FEEDBACK_VENTAS)

    @staticmethod
    def score(resultado: dict, sesion: dict) -> float:
        s = score_ponderado(C.HABILIDADES["ventas"], sesion.get("nivel") or "Principiante", resultado.get("kpis", []))
        ev = resultado.get("evidencia") or {}
        if ev.get("cierre") == "fallido_por_ceder":
            s = min(s, 59.0)   # ceder sin negociar no puede contar como sesión exitosa (regla del guion)
        return round(s, 1)


def _materiales_dm(competencia: str) -> str:
    """Base del diplomado de administración de proyectos (y de liderazgo) para las competencias de la Ruta DM que la usan; vacío para el resto."""
    from . import conocimiento as K
    partes = []
    if competencia in ("PMBOK", "Scrum", "Toma de decisiones", "Administración de recursos", "PMO", "Gestión del cambio", "Finanzas", "ROI", "Accountability", "Autogestión", "Innovación operativa"):
        partes.append(K.DIPLOMADO_PM)
    if competencia in ("Delegación", "Desarrollo gerencial", "Gestión del cambio", "Retroalimentación", "Influencia", "Gestión de conflictos"):
        partes.append(K.LIDERAZGO)
    return ("MATERIALES DE REFERENCIA (diseña, observa y evalúa conductas con esta base; no exijas que la persona cite nombres):\n" + "\n\n".join(partes) + "\n") if partes else ""


# ── Juan Artiaga ─────────────────────────────────────────────────────────────
class Juan:
    id = "juan"
    schema_turno = E.TURNO_JUAN

    @staticmethod
    def prompt_diseno(sesion: dict, usuario: dict, perfil: dict, historial: list[dict]) -> tuple[str, dict]:
        nivel_actual = sesion.get("nivel") or "DM Básico"
        sig = C.nivel_dm_siguiente(nivel_actual) or nivel_actual
        comp = sesion.get("competencia") or (C.competencias_dm(sig) or ["Comunicación"])[0]
        hist = "; ".join(f"{h['fecha'][:10]}: {h['score']}/10 ({h['dominio']})" for h in historial[-3:]) or "sin sesiones previas en esta competencia"
        return (P.JUAN_DISENO.format(nivel_actual=nivel_actual, nivel_siguiente=sig, valor_siguiente=C.valor_dm(sig), competencia=comp,
                                     formato_sugerido=C.formato_sugerido(comp), perfil=_texto_perfil(usuario, perfil.get("onboarding", {}), perfil.get("diagnostico"), incluir_ventas=False),
                                     objetivo=sesion.get("objetivo") or f"entrenar {comp} para el siguiente nivel", historial=hist, materiales=_materiales_dm(comp)), E.JUAN_DISENO)

    @staticmethod
    def system(sesion: dict, usuario: dict, perfil: dict) -> str:
        esc = sesion.get("escenario") or {}
        sig = C.nivel_dm_siguiente(sesion.get("nivel") or "DM Básico") or sesion.get("nivel")
        return P.JUAN_SESION.format(formato=esc.get("formato", "roleplay"), personaje=esc.get("personaje") or "—", titulo=esc.get("titulo", "Sesión"),
                                    competencia=sesion.get("competencia") or "", nivel_siguiente=sig, situacion=esc.get("situacion", ""),
                                    subdimensiones=", ".join(esc.get("subdimensiones") or []), estandar=ES.bloque(sesion.get("empresa_id"), None))

    @staticmethod
    def schema_para(sesion: dict) -> dict:
        return E.TURNO_JUAN

    @staticmethod
    def apertura(sesion: dict) -> tuple[str | None, str]:
        esc = sesion.get("escenario") or {}
        return (esc.get("primer_mensaje") or None), "(Comienza el ejercicio.)"

    @staticmethod
    def prompt_feedback(sesion: dict) -> tuple[str, dict]:
        esc = sesion.get("escenario") or {}
        nivel_actual = sesion.get("nivel") or "DM Básico"
        sig = C.nivel_dm_siguiente(nivel_actual) or nivel_actual
        return (P.FEEDBACK_DM.format(titulo=esc.get("titulo", "Sesión"), formato=esc.get("formato", "roleplay"), competencia=sesion.get("competencia") or "",
                                     nivel_siguiente=sig, valor_siguiente=C.valor_dm(sig), nivel_actual=nivel_actual,
                                     subdimensiones=", ".join(esc.get("subdimensiones") or []), competencias_siguiente=", ".join(C.competencias_dm(sig)),
                                     reglas=P.REGLAS_FEEDBACK, estandar=ES.bloque(sesion.get("empresa_id"), None), materiales=_materiales_dm(sesion.get("competencia") or "")), E.FEEDBACK_DM)

    @staticmethod
    def score(resultado: dict, sesion: dict) -> float:
        subs = resultado.get("subdimensiones") or []
        if subs:
            prom = sum(float(s.get("score", 0)) for s in subs) / len(subs)
            glob = float(resultado.get("score_global") or prom)
            return round(((prom + glob) / 2) * 10, 1)
        return round(float(resultado.get("score_global") or 0) * 10, 1)


# ── Avatares genéricos por KPI (Valeria, Renata, Mateo, Patricia) ────────────
class Generico:
    """Avatar de un escenario definido por su configuración en prompts.ESCENARIOS y su rúbrica de KPIs en el catálogo.
    Diseña la escena una vez (con la base de conocimiento), conversa barato por turnos y evalúa al final con la misma base."""
    generico = True
    schema_turno = E.TURNO_GENERICO

    def __init__(self, habilidad_id: str) -> None:
        self.habilidad_id = habilidad_id
        self.hab = C.HABILIDADES[habilidad_id]
        self.id = self.hab["agente"]
        self.cfg = P.ESCENARIOS[habilidad_id]

    def _base(self) -> str:
        from . import conocimiento as K
        return K.base(self.habilidad_id)

    def _nivel(self, sesion: dict) -> str:
        return sesion.get("nivel") or self.hab["niveles"][0]

    def prompt_diseno(self, sesion: dict, usuario: dict, perfil: dict, historial: list[dict]) -> tuple[str, dict]:
        nivel = self._nivel(sesion)
        hist = "; ".join(f"{h['fecha'][:10]}: {h['score']}" for h in historial[-3:]) or "sin sesiones previas"
        extra = ""
        if self.hab.get("test") == "liderazgo":
            est = (sesion.get("escenario") or {}).get("estilo_test") or {}
            if est.get("predominante"):
                extra = f" Estilo de liderazgo según el test (grid gerencial): {est['predominante']} — {est.get('lectura', '')}. Diseña una escena que lo rete a flexibilizar hacia el estilo situacional."
        return (P.GENERICO_DISENO.format(identidad=self.cfg["identidad"], base=self._base(), tipos=self.cfg["tipos"], nivel=nivel,
                                         config_nivel=self.cfg["niveles"].get(nivel, ""), perfil=_texto_perfil(usuario, perfil.get("onboarding", {}), perfil.get("diagnostico"), incluir_ventas=self.habilidad_id in ("imagen", "presentaciones")) + extra,
                                         objetivo=sesion.get("objetivo") or f"practicar {self.hab['nombre'].lower()} en una situación real", historial=hist,
                                         estandar=ES.bloque(sesion.get("empresa_id"), self.habilidad_id)), E.DISENO_GENERICO)

    def system(self, sesion: dict, usuario: dict, perfil: dict) -> str:
        esc = sesion.get("escenario") or {}
        nivel = self._nivel(sesion)
        return P.GENERICO_SESION.format(identidad=self.cfg["identidad"], reglas=self.cfg["reglas"], nivel=nivel, config_nivel=self.cfg["niveles"].get(nivel, ""),
                                        titulo=esc.get("titulo", "Práctica"), personaje=esc.get("personaje") or self.hab["avatar"], situacion=esc.get("situacion", ""),
                                        tarea=esc.get("tarea") or "conversar la situación hasta resolverla", estandar=ES.bloque(sesion.get("empresa_id"), self.habilidad_id),
                                        objetivo=sesion.get("objetivo") or "—")

    def schema_para(self, sesion: dict) -> dict:
        return E.TURNO_GENERICO

    def apertura(self, sesion: dict) -> tuple[str | None, str]:
        esc = sesion.get("escenario") or {}
        return (esc.get("primer_mensaje") or None), "(Comienza la escena con tu primer turno e indica claramente qué debe hacer ahora la persona.)"

    def prompt_feedback(self, sesion: dict) -> tuple[str, dict]:
        esc = sesion.get("escenario") or {}
        nivel = self._nivel(sesion)
        extra = self.cfg.get("feedback_extra", "")
        if self.hab.get("test") == "liderazgo" and (esc.get("estilo_test") or {}).get("predominante"):
            extra += f" ESTILO DE LIDERAZGO del test: {esc['estilo_test']['predominante']} ({esc['estilo_test'].get('lectura', '')})."
        return (P.FEEDBACK_GENERICO.format(avatar=self.hab["avatar"], habilidad=self.hab["nombre"].lower(), base=self._base(), kpis=_kpis_texto(self.hab, nivel), feedback_extra=extra,
                                           titulo=esc.get("titulo", "—"), tarea=esc.get("tarea") or "—", nivel=nivel, objetivo=sesion.get("objetivo") or "—",
                                           estandar=ES.bloque(sesion.get("empresa_id"), self.habilidad_id), reglas=P.REGLAS_FEEDBACK), E.feedback_generico(len(self.hab["kpis"])))

    def score(self, resultado: dict, sesion: dict) -> float:
        kpis = [k for k in resultado.get("kpis", []) if k.get("evaluable", True)]
        pesos = self.hab["pesos"].get(self._nivel(sesion)) or self.hab["pesos"][self.hab["niveles"][0]]
        total = sum(pesos.get(k["id"], 0) for k in kpis) or 100
        return round(sum(float(k.get("score", 0)) * pesos.get(k.get("id", ""), 0) for k in kpis) / total, 1)


AGENTES = {"elena": Elena, "celeste": Celeste, "juan": Juan}
for _hid, _h in C.HABILIDADES.items():
    if _h["agente"] not in AGENTES:
        AGENTES[_h["agente"]] = Generico(_hid)


def agente_para(habilidad_id: str):
    return AGENTES[C.HABILIDADES[habilidad_id]["agente"]]


def es_generico(agente) -> bool:
    return bool(getattr(agente, "generico", False))


def nota_adjunto(meta: dict | None) -> str:
    """Resumen entre corchetes de una grabación o foto adjunta a un mensaje (lo que ven el avatar y el análisis final)."""
    meta = meta or {}
    a = meta.get("audio")
    if a:
        m, s = divmod(int(a.get("duracion_s") or 0), 60)
        return (f"[Grabación de voz · {m}:{s:02d} · {a.get('ppm', 0)} palabras/min · {a.get('muletillas', 0)} muletillas ({a.get('muletillas_min', 0)}/min) · "
                f"pausas largas {a.get('pausas_largas', 0)} · ritmo {a.get('ritmo')} · variedad vocal {a.get('variedad_vocal')} · volumen {a.get('volumen')} · "
                f"energía al cierre: {a.get('energia_cierre')} · seguridad {a.get('seguridad')}/4 · {a.get('observaciones_voz', '')}]")
    f = meta.get("foto")
    if f:
        if not f.get("es_outfit", True):
            return "[Foto enviada: no muestra vestimenta]"
        return (f"[Foto ({f.get('nota_privacidad') or 'imagen'}) · código detectado: {f.get('codigo_detectado')} · {f.get('descripcion', '')} · Ajuste: {f.get('ajuste', '')} · "
                f"Cuidado: {f.get('cuidado', '')} · Color: {f.get('color', '')} · Accesorios: {f.get('accesorios', '')} · Sin ver: {', '.join(f.get('detalles_a_revisar') or []) or '—'}]")
    return ""


def transcript_texto(mensajes: list[dict], nombre_usuario: str, nombre_avatar: str) -> str:
    """Transcripción compacta numerada por turno (lo que consume el análisis final)."""
    out, turno = [], 0
    for m in mensajes:
        if m["rol"] == "usuario":
            turno += 1
            nota = nota_adjunto(m.get("meta"))
            out.append(f"[{turno}] {nombre_usuario}: {(nota + ' ') if nota else ''}{m['texto']}")
        elif m["rol"] == "avatar":
            out.append(f"    {nombre_avatar}: {m['texto']}")
    return "\n".join(out)


def json_compacto(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"))
