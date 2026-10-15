"""Estándares por empresa: la metodología y el estilo con los que cada organización quiere que se entrene y se evalúe.

Ejemplos: una empresa vende con AIDA (no con PRAINCODERECI), otra quiere presentaciones breves con gráficas y otra largas con datos
duros; una usa su propio modelo de competencias en entrevistas. RRHH captura texto libre por habilidad (metodología, etapas,
terminología, reglas) y un estilo general de comunicación; los agentes lo reciben como bloque prioritario sobre el genérico de
Mente Viva. Si la empresa no captura nada, todo sigue con los estándares de Mente Viva (lo que hoy usa Cóndor).
"""
from __future__ import annotations

import hashlib

from .. import db
from . import catalogo as C

CAMPOS_HABILIDAD = [
    ("metodologia", "Metodología y etapas que usan", "Ej. Vendemos con AIDA (Atención → Interés → Deseo → Acción). No usamos PRAINCODERECI. El cierre siempre con una propuesta por escrito."),
    ("terminologia", "Terminología, reglas y criterios propios", "Ej. Llamamos 'sondeo' al diagnóstico; nunca se ofrece descuento sin aprobación del gerente; el seguimiento es a las 24 h."),
    ("no_evaluar", "Qué NO se debe exigir ni evaluar", "Ej. No exigir técnicas de PNL ni silencio activo; no penalizar hablar de precio al inicio si el cliente lo pide."),
]
CAMPOS_GENERAL = [
    ("comunicacion", "Estilo de comunicación y presentaciones", "Ej. Presentaciones breves, poco texto, una gráfica por idea; mensajes a dirección en 3 puntos. / Ej. Presentaciones largas con datos duros y anexos."),
    ("cultura", "Valores y cultura que deben reflejarse", "Ej. Cercanía con el cliente, hablar de 'usted', decisiones por consenso, cero promesas sin fecha."),
]
# Qué estándar de Mente Viva se usa por defecto (lo que ve el usuario para saber qué está sustituyendo)
DEFAULTS = {
    "ventas": "Clínica de Ventas CAT-01 v3.0: ciclo PRAINCODERECI, diagnóstico SPIN, técnicas T-01…T-08, KPI-1…KPI-6.",
    "entrevistas": "Entrevista por competencias BEI + STAR con 5 KPIs (estructura, especificidad, autoconciencia, comunicación, ajuste).",
    "ruta_dm": "Ruta Delivery Manager de Ingeniería Cóndor (7 niveles) y Laboratorio DM: escucha activa, estrés, PMBOK y comunicación ejecutiva.",
}


def de_empresa(empresa_id: int | None) -> dict:
    e = db.empresa(empresa_id) if empresa_id else None
    return ((e or {}).get("config") or {}).get("estandares") or {}


def guardar(empresa_id: int, estandares: dict) -> None:
    e = db.empresa(empresa_id)
    if not e:
        return
    cfg = dict(e.get("config") or {})
    cfg["estandares"] = estandares
    db.actualizar_empresa(empresa_id, config_json=cfg)


def _limpio(d: dict | None, campos) -> dict:
    return {k: str((d or {}).get(k, "") or "").strip()[:1500] for k, _, _ in campos}


def normalizar(form: dict, habilidades: list[str]) -> dict:
    """Del formulario de RRHH a la estructura guardada: {'general': {...}, 'ventas': {...}, ...}."""
    out = {"general": _limpio({k: form.get(f"general.{k}") for k, _, _ in CAMPOS_GENERAL}, CAMPOS_GENERAL)}
    for hid in habilidades:
        out[hid] = _limpio({k: form.get(f"{hid}.{k}") for k, _, _ in CAMPOS_HABILIDAD}, CAMPOS_HABILIDAD)
    return out


def tiene(empresa_id: int | None, habilidad: str | None = None) -> bool:
    est = de_empresa(empresa_id)
    if habilidad:
        return any(est.get(habilidad, {}).values())
    return any(any(v.values()) for v in est.values() if isinstance(v, dict))


def bloque(empresa_id: int | None, habilidad: str | None = None, para: str = "avatar") -> str:
    """Texto que se inserta en los prompts. Vacío si la empresa no definió nada (→ estándar Mente Viva, como hasta ahora)."""
    est = de_empresa(empresa_id)
    partes = []
    hab = est.get(habilidad or "", {}) if habilidad else {}
    if hab.get("metodologia"):
        partes.append(f"Metodología de la empresa (PRIORITARIA sobre la de Mente Viva; evalúa y entrena con ESTAS etapas y criterios, mapeando los KPIs a ellas y sin exigir lo que la empresa no usa): {hab['metodologia']}")
    if hab.get("terminologia"):
        partes.append(f"Terminología y reglas propias (úsalas tal cual): {hab['terminologia']}")
    if hab.get("no_evaluar"):
        partes.append(f"NO exigir ni penalizar: {hab['no_evaluar']}")
    gen = est.get("general", {})
    if gen.get("comunicacion"):
        partes.append(f"Estilo de comunicación y presentaciones de la empresa (evalúa claridad y estructura con este estándar): {gen['comunicacion']}")
    if gen.get("cultura"):
        partes.append(f"Valores y cultura que deben reflejarse: {gen['cultura']}")
    if not partes:
        return ""
    nombre = (db.empresa(empresa_id) or {}).get("nombre", "la empresa")
    return f"\nESTÁNDAR DE {nombre.upper()}\n- " + "\n- ".join(partes) + "\n"


def huella(empresa_id: int | None, habilidad: str) -> str:
    """Hash corto del estándar aplicable (para que las lecciones base de Sócrates no se compartan entre metodologías distintas)."""
    b = bloque(empresa_id, habilidad)
    return "mv" if not b else hashlib.sha1(b.encode()).hexdigest()[:8]


def habilidades_editables(empresa: dict | None) -> list[dict]:
    return [h for h in C.habilidades_empresa(empresa) if h["id"] != "ruta_dm"]   # la Ruta DM es la metodología de Cóndor: no se sustituye
