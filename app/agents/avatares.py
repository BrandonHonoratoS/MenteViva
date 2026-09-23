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
from . import prompts as P

AVATARES = {
    "elena": {"nombre": "Elena Ríos", "rol": "Entrevistadora por competencias", "color": "#3B82F6", "inicial": "E",
              "descripcion": "Te entrevista con método BEI + STAR, diagnostica tus competencias y diseña tus roadmaps."},
    "celeste": {"nombre": "Celeste López", "rol": "Clienta exigente · Clínica de Ventas", "color": "#7C3AED", "inicial": "C",
                "descripcion": "Una clienta analítica que no compra por simpatía: revela si dominas la venta o improvisas."},
    "juan": {"nombre": "Juan Artiaga", "rol": "Mentor · Ruta Delivery Manager", "color": "#10B981", "inicial": "J",
             "descripcion": "Diagnostica tu nivel DM y entrena, con roleplay, casos o retos, las competencias del siguiente nivel."},
    "analista": {"nombre": "El Analista", "rol": "Inteligencia de desarrollo", "color": "#F59E0B", "inicial": "A",
                 "descripcion": "Lee todas las sesiones, recalcula planes y niveles, y orienta a líderes y RRHH con evidencia."},
}


def _texto_perfil(usuario: dict, onboarding: dict, diagnostico: dict | None = None, incluir_ventas: bool = True) -> str:
    lineas = [f"Nombre: {usuario['nombre']}. Puesto: {usuario.get('puesto') or 'no indicado'}. Área: {usuario.get('area_nombre') or 'no indicada'}."]
    if onboarding:
        rol = ", ".join(onboarding.get("funciones") or []) or "no indicado"
        lineas.append(f"Funciones: {rol}. Industria de sus clientes: {onboarding.get('industria', '')}. Experiencia: {onboarding.get('experiencia', '')}.")
        if incluir_ventas and onboarding.get("tipo_producto"):
            lineas.append(f"Vende: {onboarding.get('tipo_producto')} · a {onboarding.get('modelo_venta')} · canal {onboarding.get('canal_venta')} · "
                          f"clientes {onboarding.get('tamano_cliente')} · ticket {onboarding.get('ticket')} · estilo {onboarding.get('estilo')} · "
                          f"etapa débil: {onboarding.get('etapa_debil')} · objetivo: {onboarding.get('objetivo_ventas')}.")
        lineas.append(f"Ruta DM: lidera → {onboarding.get('dm_lidera', '')}; trabajo → {onboarding.get('dm_trabajo', '')}; antigüedad → "
                      f"{onboarding.get('dm_antiguedad', '')}; representa a la empresa → {onboarding.get('dm_representa', '')}. "
                      f"Tiempo semanal: {onboarding.get('tiempo_semana', '')}. Meta: {onboarding.get('meta', '')}.")
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
                                       turnos_objetivo=C.turnos_max("entrevistas", nivel))

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
        return (P.FEEDBACK_ENTREVISTAS.format(kpis=_kpis_texto(hab, nivel), nivel=nivel, objetivo=sesion.get("objetivo") or "—", reglas=P.REGLAS_FEEDBACK),
                E.FEEDBACK_ENTREVISTAS)

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
                                canal=ob.get("canal_venta", "cara a cara"), objetivo=sesion.get("objetivo") or "ejecutar el ciclo completo")

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
                                         etapa_debil=esc.get("etapa_debil") or "no declarada", reglas=P.REGLAS_FEEDBACK), E.FEEDBACK_VENTAS)

    @staticmethod
    def score(resultado: dict, sesion: dict) -> float:
        s = score_ponderado(C.HABILIDADES["ventas"], sesion.get("nivel") or "Principiante", resultado.get("kpis", []))
        ev = resultado.get("evidencia") or {}
        if ev.get("cierre") == "fallido_por_ceder":
            s = min(s, 59.0)   # ceder sin negociar no puede contar como sesión exitosa (regla del guion)
        return round(s, 1)


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
                                     objetivo=sesion.get("objetivo") or f"entrenar {comp} para el siguiente nivel", historial=hist), E.JUAN_DISENO)

    @staticmethod
    def system(sesion: dict, usuario: dict, perfil: dict) -> str:
        esc = sesion.get("escenario") or {}
        sig = C.nivel_dm_siguiente(sesion.get("nivel") or "DM Básico") or sesion.get("nivel")
        return P.JUAN_SESION.format(formato=esc.get("formato", "roleplay"), personaje=esc.get("personaje") or "—", titulo=esc.get("titulo", "Sesión"),
                                    competencia=sesion.get("competencia") or "", nivel_siguiente=sig, situacion=esc.get("situacion", ""),
                                    subdimensiones=", ".join(esc.get("subdimensiones") or []))

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
                                     reglas=P.REGLAS_FEEDBACK), E.FEEDBACK_DM)

    @staticmethod
    def score(resultado: dict, sesion: dict) -> float:
        subs = resultado.get("subdimensiones") or []
        if subs:
            prom = sum(float(s.get("score", 0)) for s in subs) / len(subs)
            glob = float(resultado.get("score_global") or prom)
            return round(((prom + glob) / 2) * 10, 1)
        return round(float(resultado.get("score_global") or 0) * 10, 1)


AGENTES = {"elena": Elena, "celeste": Celeste, "juan": Juan}


def agente_para(habilidad_id: str):
    return AGENTES[C.HABILIDADES[habilidad_id]["agente"]]


def transcript_texto(mensajes: list[dict], nombre_usuario: str, nombre_avatar: str) -> str:
    """Transcripción compacta numerada por turno (lo que consume el análisis final)."""
    out, turno = [], 0
    for m in mensajes:
        if m["rol"] == "usuario":
            turno += 1
            out.append(f"[{turno}] {nombre_usuario}: {m['texto']}")
        elif m["rol"] == "avatar":
            out.append(f"    {nombre_avatar}: {m['texto']}")
    return "\n".join(out)


def json_compacto(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"))
