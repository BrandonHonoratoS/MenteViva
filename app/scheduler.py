"""Tareas programadas ligeras (un hilo): alertas de inactividad (diario), resumen semanal por área y organización (lunes)."""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from . import db
from .agents import analista
from .config import settings

log = logging.getLogger("mv.scheduler")
_hilo: threading.Thread | None = None


def correr_diario() -> dict:
    out = {"inactividad": 0}
    for e in db.empresas():
        if e["activa"]:
            out["inactividad"] += analista.alertas_inactividad(e["id"])
    return out


def correr_semanal() -> dict:
    out = {"resumenes": 0}
    for e in db.empresas():
        if not e["activa"]:
            continue
        for a in db.areas(e["id"]):
            if analista.resumen_periodico(e["id"], "area", area_id=a["id"], dias=7):
                out["resumenes"] += 1
        if analista.resumen_periodico(e["id"], "organizacion", dias=7):
            out["resumenes"] += 1
    return out


def correr_micro(hora: int) -> int:
    """Recordatorio "Prepárate 5 minutos" a quienes tienen la modalidad micro y aún no completaron el bloque de esta franja."""
    enviados = 0
    franjas = sorted(settings.MICRO_HORAS)
    idx = franjas.index(hora) if hora in franjas else 0
    for e in db.empresas():
        if not e["activa"]:
            continue
        for u in db.usuarios(e["id"], rol="colaborador"):
            if (u.get("modalidad") or "completa") != "micro":
                continue
            hoy = db.actividad_hoy(u["id"])
            if int(hoy.get("bloques") or 0) + (1 if int(hoy.get("turnos") or 0) >= 3 else 0) > idx:
                continue   # ya lleva el bloque de esta franja
            racha = db.racha_dias(u["id"])
            destino, que = _siguiente_paso(u)
            titulo = f"Prepárate 5 minutos ({idx + 1}/{len(franjas)})" + (f" · racha de {racha['dias']} día{'s' if racha['dias'] != 1 else ''} 🔥" if racha["dias"] else "")
            db.notificar(u["id"], titulo, que, destino, "aviso")
            enviados += 1
    return enviados


def _siguiente_paso(u: dict) -> tuple[str, str]:
    s = db.sesion_en_curso(u["id"])
    if s:
        return f"/sesion/{s['id']}", f"Tienes una sesión abierta de {s['habilidad']}: 5 minutos más y la dejas lista para el análisis."
    it = db.siguiente_item(u["id"])
    if it:
        if it.get("tipo") == "laboratorio":
            return f"/laboratorio?item={it['id']}", "Tu siguiente paso es el Laboratorio DM: puedes avanzarlo por bloques."
        return f"/entrenar/{it['habilidad']}?item={it['id']}", f"Tu siguiente sesión: {it['objetivo'][:90]}. Entra 5 minutos; la sesión se queda abierta si te interrumpen."
    return "/socrates", "Sin sesiones pendientes: lee 5 minutos de una master class de Sócrates o entrena libre desde el catálogo."


def _loop() -> None:
    tz = ZoneInfo(settings.TZ)
    while True:
        try:
            ahora = datetime.now(tz)
            hoy = ahora.strftime("%Y-%m-%d")
            if ahora.hour >= 6 and db.get_ajuste("ultimo_diario") != hoy:
                db.set_ajuste("ultimo_diario", hoy)
                r = correr_diario()
                db.log("info", "programador", "Corrida diaria", str(r))
            for h in settings.MICRO_HORAS:
                clave = f"micro_{hoy}_{h}"
                if ahora.hour >= h and ahora.hour < h + 3 and ahora.weekday() < 5 and db.get_ajuste(clave) != "1":
                    db.set_ajuste(clave, "1")
                    n = correr_micro(h)
                    if n:
                        db.log("info", "programador", f"Recordatorios 'Prepárate 5 minutos' ({h}:00)", f"{n} avisos")
            semana = ahora.strftime("%G-W%V")
            if ahora.weekday() == settings.RESUMEN_SEMANAL_DIA and ahora.hour >= settings.RESUMEN_SEMANAL_HORA and db.get_ajuste("ultimo_semanal") != semana:
                db.set_ajuste("ultimo_semanal", semana)
                r = correr_semanal()
                db.log("info", "programador", "Resumen semanal", str(r))
        except Exception as e:  # noqa: BLE001
            log.exception("programador")
            db.log("error", "programador", "Fallo en tarea programada", str(e))
        time.sleep(600)


def iniciar() -> None:
    global _hilo
    if settings.SCHEDULE_ENABLED and (_hilo is None or not _hilo.is_alive()):
        _hilo = threading.Thread(target=_loop, daemon=True, name="mv-scheduler")
        _hilo.start()
