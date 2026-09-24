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
