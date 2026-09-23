"""Métricas de Mente Viva — definiciones precisas y trazables.

Cada índice devuelve su valor, su fórmula y sus componentes para que la interfaz explique "¿cómo se calcula?".
Escalas: scores de sesión 0–100 (la Ruta DM se convierte de /10 a /100); evaluaciones 1–5.

Dimensiones (marco KPI de Mente Viva: Desarrollo · Práctica · Aplicación · Cultura)
- IDSS  Índice de Desarrollo de Soft Skills = (score posterior − score inicial) / score inicial × 100; inicial = diagnóstico de Elena,
        posterior = promedio de las últimas 3 sesiones de práctica. Se promedia entre colaboradores con ambos datos.
- Práctica = sesiones de roadmap completadas / sesiones planeadas a la fecha × 100.
- Participación = colaboradores con ≥1 sesión en el periodo / colaboradores activos × 100.
- Engagement = colaboradores con sesiones en ≥2 semanas distintas del periodo / colaboradores activos × 100.
- Autodesarrollo = sesiones voluntarias (fuera del roadmap) / sesiones del periodo × 100.
- Aplicación = colaboradores cuya última evaluación del líder marca "aplica" ≥ 4 / colaboradores evaluados × 100.
- Transferencia = habilidades aplicadas / habilidades aprendidas × 100 (aprendida: promedio de últimas 3 sesiones ≥ 75; aplicada: además el líder marca "aplica" ≥ 4).
- Evolución conductual = (última evaluación del líder − primera) / primera × 100, promedio entre colaboradores con ≥2 evaluaciones.
- Madurez organizacional (1–5) = ponderación de Participación 25 %, Engagement 25 %, Práctica 20 %, Aplicación 15 %, Nivel de habilidad 15 %.
- IIHO  Índice de Inteligencia Humana Organizacional = promedio de las 4 dimensiones disponibles (0–100).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from . import db
from .agents import catalogo as C

MADUREZ = [(80, 5, "Cultura consolidada"), (60, 4, "Integrado"), (40, 3, "Funcional"), (20, 2, "En desarrollo"), (0, 1, "Inicial")]


def _semana(ts: str) -> str:
    d = datetime.fromisoformat(ts)
    return f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"


def _dias_desde(ts: str | None) -> int | None:
    if not ts:
        return None
    return max(0, (datetime.now(timezone.utc) - datetime.fromisoformat(ts)).days)


MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _etiqueta(ts: str) -> str:
    d = datetime.fromisoformat(ts)
    return f"{d.day} {MESES[d.month - 1]}"


def _prom(xs: list[float]) -> float | None:
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 1) if xs else None


# ── colaborador ──────────────────────────────────────────────────────────────
def racha_semanas(usuario_id: int) -> int:
    semanas = {_semana(s["inicio"]) for s in db.sesiones(usuario_id=usuario_id, estado="completada", limite=200)}
    if not semanas:
        return 0
    n, d = 0, datetime.now(timezone.utc)
    while _semana(d.isoformat()) in semanas:
        n += 1
        d -= timedelta(days=7)
    return n


def serie_scores(usuario_id: int, habilidad: str | None = None, limite: int = 12) -> list[dict]:
    ss = [s for s in reversed(db.sesiones(usuario_id=usuario_id, habilidad=habilidad, estado="completada", limite=200)) if s["tipo"] == "practica"]
    return [{"fecha": _etiqueta(s["inicio"]), "iso": s["inicio"][:10], "score": s["score_global"], "habilidad": s["habilidad"], "nivel": s.get("nivel"), "id": s["id"]} for s in ss][-limite:]


def kpis_promedio(usuario_id: int, habilidad: str, ultimas: int = 3) -> list[dict]:
    """Promedio por KPI de las últimas N sesiones de una habilidad (para radar/tendencia)."""
    ss = [s for s in db.sesiones(usuario_id=usuario_id, habilidad=habilidad, estado="completada", limite=ultimas) if s["tipo"] == "practica"]
    acc: dict[str, list[float]] = defaultdict(list)
    nombres: dict[str, str] = {}
    for s in ss:
        for k in (s.get("resultado") or {}).get("kpis", []):
            acc[k["id"]].append(float(k.get("score", 0)))
        for sd in (s.get("resultado") or {}).get("subdimensiones", []):
            acc[sd["nombre"]].append(float(sd.get("score", 0)) * 10)
    hab = C.HABILIDADES.get(habilidad) or {}
    for k in hab.get("kpis", []):
        nombres[k["id"]] = k["nombre"]
    return [{"id": k, "nombre": nombres.get(k, k), "score": _prom(v)} for k, v in acc.items()]


def resumen_colaborador(u: dict) -> dict:
    ss = [s for s in db.sesiones(usuario_id=u["id"], estado="completada", limite=100) if s["tipo"] == "practica"]
    scores = [float(s["score_global"]) for s in ss if s["score_global"] is not None]
    ult3 = scores[:3]
    prev3 = scores[3:6]
    perfil = db.perfil(u["id"])
    niveles = db.niveles(u["id"])
    ultima = db.sesiones(usuario_id=u["id"], limite=1)
    prom = _prom(ult3)
    tendencia = round(prom - _prom(prev3), 1) if prom is not None and _prom(prev3) is not None else None
    rms = db.roadmaps(u["id"], ("activo",))
    plan = {"total": sum(r["total"] for r in rms), "completadas": sum(r["completadas"] for r in rms)}
    return {"id": u["id"], "nombre": u["nombre"], "puesto": u.get("puesto", ""), "area": u.get("area_nombre") or "", "area_id": u.get("area_id"), "color": u.get("color"),
            "diagnostico": perfil.get("estado"), "niveles": {h: n["nivel"] for h, n in niveles.items()}, "sesiones": len(ss), "score_promedio": prom,
            "tendencia": tendencia, "semaforo": C.semaforo(prom), "ultima_actividad": ultima[0]["inicio"][:10] if ultima else None,
            "dias_inactivo": _dias_desde(ultima[0]["inicio"]) if ultima else None, "racha": racha_semanas(u["id"]), "plan": plan,
            "score_inicial": (perfil.get("diagnostico") or {}).get("score_inicial")}


def ficha(u: dict, incluir_feedback: bool = False) -> dict:
    base = resumen_colaborador(u)
    perfil = db.perfil(u["id"])
    diag = perfil.get("diagnostico") or {}
    niveles = db.niveles(u["id"])
    ss = [s for s in db.sesiones(usuario_id=u["id"], estado="completada", limite=12) if s["tipo"] == "practica"]
    sesiones = []
    for s in ss:
        r = s.get("resultado") or {}
        d = {"id": s["id"], "fecha": s["inicio"][:10], "habilidad": s["habilidad"], "nivel": s.get("nivel"), "competencia": s.get("competencia"),
             "score": s["score_global"], "objetivo": s.get("objetivo"), "turnos": s["turnos"]}
        if incluir_feedback:
            d["resumen"] = r.get("resumen")
            d["recomendacion"] = r.get("recomendacion") or r.get("siguiente_paso")
            d["oportunidades"] = [o.get("habilidad") for o in r.get("oportunidades", [])] or [b.get("brecha") for b in r.get("brechas", [])]
        sesiones.append(d)
    evals = db.evaluaciones(usuario_id=u["id"])
    return {**base, "estilo": diag.get("estilo_comunicacion"), "fortalezas": [f.get("habilidad") for f in diag.get("fortalezas", [])],
            "oportunidades": [o.get("habilidad") for o in diag.get("oportunidades", [])], "competencias": diag.get("competencias", []),
            "niveles_detalle": {h: {"nivel": n["nivel"], "score_inicial": n.get("score_inicial"), "score_actual": n.get("score_actual"), "sesiones": n.get("sesiones"),
                                    "competencias": n.get("competencias") or {}} for h, n in niveles.items()},
            "sesiones_recientes": sesiones, "roadmaps": [{"habilidad": r["habilidad"], "estado": r["estado"], "objetivo": r["objetivo"], "avance": f"{r['completadas']}/{r['total']}",
                                                          "siguiente": next((i["objetivo"] for i in r["items"] if i["estado"] == "pendiente"), None)}
                                                         for r in db.roadmaps(u["id"], ("activo", "propuesto"))],
            "evaluaciones": [{"tipo": e["tipo"], "periodo": e["periodo"], "promedio": e["promedio"], "evaluador": e["evaluador_nombre"]} for e in evals[:6]],
            "metas": [{"habilidad": m["habilidad"], "score_minimo": m["score_minimo"], "plazo": m.get("plazo")} for m in
                      (db.metas(u["empresa_id"], area_id=u.get("area_id"), usuario_id=u["id"]) if u.get("empresa_id") else [])],
            "propuestas": [{"tipo": p["tipo"], "titulo": p["titulo"], "estado": p["estado"]} for p in db.propuestas(u["empresa_id"], estado=None, usuario_id=u["id"], limite=5)] if u.get("empresa_id") else [],
            "serie": serie_scores(u["id"])}


# ── organización / área ──────────────────────────────────────────────────────
def kpis_organizacion(empresa_id: int, area_id: int | None = None, dias: int = 30) -> dict:
    colabs = [u for u in db.usuarios(empresa_id, area_id=area_id) if u["rol"] == "colaborador"]
    N = len(colabs)
    ids = {u["id"] for u in colabs}
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    todas = [s for s in db.sesiones(empresa_id=empresa_id, area_id=area_id, estado="completada", limite=5000) if s["tipo"] == "practica" and s["usuario_id"] in ids]
    periodo = [s for s in todas if s["inicio"] >= desde]

    # participación / engagement / autodesarrollo
    activos = {s["usuario_id"] for s in periodo}
    semanas_por_u: dict[int, set] = defaultdict(set)
    for s in periodo:
        semanas_por_u[s["usuario_id"]].add(_semana(s["inicio"]))
    recurrentes = {u for u, w in semanas_por_u.items() if len(w) >= 2}
    participacion = round(len(activos) / N * 100, 1) if N else None
    engagement = round(len(recurrentes) / N * 100, 1) if N else None
    voluntarias = sum(1 for s in periodo if s.get("voluntaria"))
    autodesarrollo = round(voluntarias / len(periodo) * 100, 1) if periodo else None

    # nivel de habilidad e IDSS
    por_u: dict[int, list[float]] = defaultdict(list)
    for s in todas:  # más recientes primero
        if s["score_global"] is not None:
            por_u[s["usuario_id"]].append(float(s["score_global"]))
    posterior = {u: _prom(v[:3]) for u, v in por_u.items()}
    idss_lista, inicial_lista = [], []
    for u in colabs:
        ini = (db.perfil(u["id"]).get("diagnostico") or {}).get("score_inicial")
        post = posterior.get(u["id"])
        if ini and post is not None:
            idss_lista.append((post - ini) / ini * 100)
            inicial_lista.append(ini)
    idss = round(sum(idss_lista) / len(idss_lista), 1) if idss_lista else None
    nivel_habilidad = _prom(list(posterior.values()))

    # práctica (roadmaps activos)
    planeadas = completadas = 0
    ahora = datetime.now(timezone.utc)
    for u in colabs:
        for r in db.roadmaps(u["id"], ("activo",)):
            semana_actual = min(r["horizonte_semanas"], (ahora - datetime.fromisoformat(r["creado_en"])).days // 7 + 1)
            vencidas = [i for i in r["items"] if i["semana"] <= semana_actual]
            planeadas += len(vencidas)
            completadas += sum(1 for i in vencidas if i["estado"] == "completada")
    practica = round(completadas / planeadas * 100, 1) if planeadas else None

    # aplicación / transferencia / evolución (evaluaciones del líder)
    evals = [e for e in db.evaluaciones(tipo="lider", empresa_id=empresa_id, area_id=area_id) if e["usuario_id"] in ids]
    ult_eval: dict[int, dict] = {}
    primera_eval: dict[int, dict] = {}
    for e in evals:  # vienen de más reciente a más antigua
        ult_eval.setdefault(e["usuario_id"], e)
        primera_eval[e["usuario_id"]] = e
    aplica = [float((e.get("respuestas") or {}).get("aplica", 0)) >= 4 for e in ult_eval.values()]
    aplicacion = round(sum(aplica) / len(aplica) * 100, 1) if aplica else None
    aprendidas = aplicadas = 0
    for u in colabs:
        for h in C.HABILIDADES:
            v = [float(s["score_global"]) for s in todas if s["usuario_id"] == u["id"] and s["habilidad"] == h and s["score_global"] is not None][:3]
            if len(v) >= 1 and sum(v) / len(v) >= 75:
                aprendidas += 1
                e = ult_eval.get(u["id"])
                if e and float((e.get("respuestas") or {}).get("aplica", 0)) >= 4:
                    aplicadas += 1
    transferencia = round(aplicadas / aprendidas * 100, 1) if aprendidas else None
    evol = []
    for uid, e1 in primera_eval.items():
        e2 = ult_eval[uid]
        if e1["id"] != e2["id"] and e1["promedio"]:
            evol.append((float(e2["promedio"]) - float(e1["promedio"])) / float(e1["promedio"]) * 100)
    evolucion = round(sum(evol) / len(evol), 1) if evol else None

    # madurez e IIHO
    comp_mad = [(participacion, 0.25), (engagement, 0.25), (practica, 0.20), (aplicacion, 0.15), (nivel_habilidad, 0.15)]
    disponibles = [(v, w) for v, w in comp_mad if v is not None]
    madurez_score = round(sum(v * w for v, w in disponibles) / sum(w for _, w in disponibles), 1) if disponibles else None
    madurez_nivel, madurez_nombre = next(((n, nom) for um, n, nom in MADUREZ if madurez_score is not None and madurez_score >= um), (None, "Sin datos"))
    dim_desarrollo = nivel_habilidad
    dim_practica = _prom([participacion, engagement, practica])
    dim_aplicacion = _prom([aplicacion, transferencia])
    dim_cultura = round(madurez_nivel * 20, 1) if madurez_nivel else None
    iiho = _prom([dim_desarrollo, dim_practica, dim_aplicacion, dim_cultura])

    # distribución Ruta DM y niveles
    dist_dm: dict[str, int] = {n: 0 for n in C.NIVELES_DM}
    dist_niv: dict[str, dict[str, int]] = {h: defaultdict(int) for h in ("ventas", "entrevistas")}
    for u in colabs:
        for h, n in db.niveles(u["id"]).items():
            if h == "ruta_dm" and n["nivel"] in dist_dm:
                dist_dm[n["nivel"]] += 1
            elif h in dist_niv:
                dist_niv[h][n["nivel"]] += 1

    # ranking y atención
    resumenes = [resumen_colaborador(u) for u in colabs]
    con_score = [r for r in resumenes if r["score_promedio"] is not None]
    top = sorted(con_score, key=lambda r: -r["score_promedio"])[:3]
    atencion = [r for r in resumenes if (r["dias_inactivo"] or 0) >= 7 or r["semaforo"] == "rojo" or (r["tendencia"] is not None and r["tendencia"] <= -10)]
    sin_diag = [r for r in resumenes if r["diagnostico"] != "completo"]

    # serie semanal (8 semanas)
    serie: dict[str, list[float]] = defaultdict(list)
    for s in todas:
        if s["inicio"] >= (ahora - timedelta(weeks=8)).isoformat() and s["score_global"] is not None:
            serie[_semana(s["inicio"])].append(float(s["score_global"]))
    semanas_serie = []
    for i in range(7, -1, -1):
        w = _semana((ahora - timedelta(weeks=i)).isoformat())
        semanas_serie.append({"semana": w, "sesiones": len(serie.get(w, [])), "score": _prom(serie.get(w, []))})

    # KPIs por habilidad (promedio organizacional de las últimas 3 sesiones por persona)
    kpis_hab: dict[str, dict[str, list[float]]] = {h: defaultdict(list) for h in C.HABILIDADES}
    for u in colabs:
        for h in ("ventas", "entrevistas", "ruta_dm"):
            for k in kpis_promedio(u["id"], h):
                if k["score"] is not None:
                    kpis_hab[h][k["nombre"]].append(k["score"])
    radar = {h: [{"nombre": n, "score": _prom(v)} for n, v in d.items()] for h, d in kpis_hab.items() if d}

    # por área (sólo organización)
    por_area = []
    if area_id is None:
        for a in db.areas(empresa_id):
            rs = [r for r in resumenes if r["area_id"] == a["id"]]
            por_area.append({"id": a["id"], "nombre": a["nombre"], "director": a.get("director_nombre"), "colaboradores": len(rs),
                             "score": _prom([r["score_promedio"] for r in rs]), "activos": sum(1 for r in rs if r["id"] in activos),
                             "sesiones": sum(1 for s in periodo if s["area_id"] == a["id"]), "atencion": sum(1 for r in rs if r in atencion)})

    return {
        "periodo_dias": dias, "colaboradores": N, "sesiones_periodo": len(periodo), "sesiones_total": len(todas), "activos": len(activos),
        "indices": {
            "iiho": {"nombre": "Inteligencia Humana Organizacional (IIHO)", "valor": iiho, "unidad": "/100", "dimension": "Transversal",
                     "formula": "Promedio de las dimensiones Desarrollo, Práctica, Aplicación y Cultura (las que tienen datos).",
                     "componentes": {"Desarrollo": dim_desarrollo, "Práctica": dim_practica, "Aplicación": dim_aplicacion, "Cultura": dim_cultura}},
            "idss": {"nombre": "Desarrollo de Soft Skills (IDSS)", "valor": idss, "unidad": "%", "dimension": "Desarrollo",
                     "formula": "(score posterior − score inicial) / score inicial × 100. Inicial = diagnóstico de Elena; posterior = promedio de las últimas 3 sesiones.",
                     "componentes": {"colaboradores con ambos datos": len(idss_lista), "score inicial promedio": _prom(inicial_lista), "score actual promedio": nivel_habilidad}},
            "nivel_habilidad": {"nombre": "Nivel de habilidad", "valor": nivel_habilidad, "unidad": "/100", "dimension": "Desarrollo",
                                "formula": "Promedio del score de las últimas 3 sesiones de cada colaborador.", "componentes": {"colaboradores con sesiones": len(posterior)}},
            "practica": {"nombre": "Índice de Práctica", "valor": practica, "unidad": "%", "dimension": "Práctica",
                         "formula": "Sesiones del roadmap completadas / sesiones planeadas a la fecha × 100.", "componentes": {"completadas": completadas, "planeadas": planeadas}},
            "participacion": {"nombre": "Participación en Desarrollo", "valor": participacion, "unidad": "%", "dimension": "Práctica",
                              "formula": f"Colaboradores con ≥1 sesión en {dias} días / colaboradores activos × 100.", "componentes": {"activos": len(activos), "registrados": N}},
            "engagement": {"nombre": "Engagement en Desarrollo", "valor": engagement, "unidad": "%", "dimension": "Práctica",
                           "formula": f"Colaboradores con sesiones en ≥2 semanas distintas en {dias} días / registrados × 100.", "componentes": {"recurrentes": len(recurrentes), "registrados": N}},
            "autodesarrollo": {"nombre": "Autodesarrollo", "valor": autodesarrollo, "unidad": "%", "dimension": "Desarrollo",
                               "formula": "Sesiones voluntarias (fuera del roadmap) / sesiones del periodo × 100.", "componentes": {"voluntarias": voluntarias, "total": len(periodo)}},
            "aplicacion": {"nombre": "Aplicación en el Entorno Laboral", "valor": aplicacion, "unidad": "%", "dimension": "Aplicación",
                           "formula": "Colaboradores cuya última evaluación del líder marca 'aplica' ≥ 4 / evaluados × 100.", "componentes": {"evaluados": len(aplica)}},
            "transferencia": {"nombre": "Transferencia del Aprendizaje", "valor": transferencia, "unidad": "%", "dimension": "Aplicación",
                              "formula": "Habilidades aplicadas / habilidades aprendidas × 100 (aprendida: promedio ≥ 75; aplicada: además el líder marca 'aplica' ≥ 4).",
                              "componentes": {"aprendidas": aprendidas, "aplicadas": aplicadas}},
            "evolucion": {"nombre": "Evolución Conductual", "valor": evolucion, "unidad": "%", "dimension": "Aplicación",
                          "formula": "(última evaluación del líder − primera) / primera × 100, promedio entre colaboradores con ≥2 evaluaciones.", "componentes": {"colaboradores": len(evol)}},
            "madurez": {"nombre": "Madurez de Soft Skills Organizacional", "valor": madurez_nivel, "unidad": "/5", "dimension": "Cultura", "etiqueta": madurez_nombre,
                        "formula": "Puntaje ponderado (Participación 25 %, Engagement 25 %, Práctica 20 %, Aplicación 15 %, Nivel de habilidad 15 %) → 1 Inicial · 2 En desarrollo · 3 Funcional · 4 Integrado · 5 Cultura consolidada.",
                        "componentes": {"puntaje": madurez_score}},
        },
        "distribucion_dm": dist_dm, "distribucion_niveles": {h: dict(d) for h, d in dist_niv.items()}, "top": top, "atencion": atencion, "sin_diagnostico": sin_diag,
        "serie": semanas_serie, "radar": radar, "por_area": por_area, "colaboradores_resumen": resumenes,
    }


def resumen_para_analista(empresa_id: int, area_id: int | None = None, dias: int = 7) -> dict:
    k = kpis_organizacion(empresa_id, area_id=area_id, dias=dias)
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    ss = [s for s in db.sesiones(empresa_id=empresa_id, area_id=area_id, estado="completada", desde=desde, limite=300) if s["tipo"] == "practica"]
    return {
        "periodo_dias": dias, "colaboradores": k["colaboradores"], "activos": k["activos"],
        "indices": {n: v["valor"] for n, v in k["indices"].items()},
        "sesiones": [{"colaborador": s["usuario_nombre"], "habilidad": s["habilidad"], "nivel": s.get("nivel"), "score": s.get("score_global"),
                      "recomendacion": ((s.get("resultado") or {}).get("recomendacion") or {}).get("objetivo_siguiente")} for s in ss[:60]],
        "top": [{"nombre": t["nombre"], "score": t["score_promedio"], "tendencia": t["tendencia"]} for t in k["top"]],
        "atencion": [{"nombre": a["nombre"], "score": a["score_promedio"], "dias_inactivo": a["dias_inactivo"], "tendencia": a["tendencia"]} for a in k["atencion"]],
        "sin_diagnostico": [a["nombre"] for a in k["sin_diagnostico"]],
        "distribucion_dm": k["distribucion_dm"], "por_area": [{"area": a["nombre"], "score": a["score"], "activos": a["activos"], "atencion": a["atencion"]} for a in k["por_area"]],
        "propuestas_pendientes": [{"tipo": p["tipo"], "titulo": p["titulo"]} for p in db.propuestas(empresa_id, area_id=area_id)[:10]],
    }
