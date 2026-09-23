"""PDF con identidad Mente Viva (reportlab): reporte de sesión y ficha de colaborador."""
from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..agents import catalogo as C
from ..agents.avatares import AVATARES

VIOLETA = colors.HexColor("#6D28D9")
AQUA = colors.HexColor("#06B6D4")
GRIS = colors.HexColor("#475569")
SUAVE = colors.HexColor("#F5F3FF")


def _estilos():
    ss = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("h1", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=20, textColor=VIOLETA, alignment=TA_LEFT, spaceAfter=4),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=12.5, textColor=VIOLETA, spaceBefore=10, spaceAfter=4),
        "p": ParagraphStyle("p", parent=ss["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13, textColor=colors.HexColor("#1E293B")),
        "meta": ParagraphStyle("meta", parent=ss["BodyText"], fontName="Helvetica", fontSize=8.5, textColor=GRIS),
        "chip": ParagraphStyle("chip", parent=ss["BodyText"], fontName="Helvetica-Bold", fontSize=9, textColor=VIOLETA),
    }


def _esc(t) -> str:
    return str(t if t is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _pie(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GRIS)
    canvas.drawString(18 * mm, 12 * mm, "Mente Viva · Crece desde adentro, impacta hacia afuera · Reporte generado por IA con evidencia de la sesión; uso interno.")
    canvas.drawRightString(letter[0] - 18 * mm, 12 * mm, f"Página {doc.page}")
    canvas.setStrokeColor(VIOLETA)
    canvas.setLineWidth(2)
    canvas.line(18 * mm, letter[1] - 14 * mm, letter[0] - 18 * mm, letter[1] - 14 * mm)
    canvas.restoreState()


def reporte_sesion(sesion: dict, usuario: dict) -> bytes:
    st = _estilos()
    res = sesion.get("resultado") or {}
    hab = C.HABILIDADES.get(sesion["habilidad"], {})
    avatar = AVATARES.get(sesion["agente"], {})
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=20 * mm, bottomMargin=20 * mm,
                            title=f"Mente Viva · Reporte de sesión #{sesion['id']}")
    el = [Paragraph("Mente Viva · Reporte de sesión", st["h1"]),
          Paragraph(f"{_esc(usuario['nombre'])} · {_esc(hab.get('nombre'))} · Nivel {_esc(sesion.get('nivel'))}"
                    f"{' · ' + _esc(sesion.get('competencia')) if sesion.get('competencia') else ''} · {_esc(sesion['inicio'][:10])} · con {_esc(avatar.get('nombre'))}", st["meta"]),
          Spacer(1, 6)]
    score = sesion.get("score_global")
    el.append(Table([[Paragraph(f"<b>Score global</b><br/><font size=22 color='#6D28D9'>{score:.0f}</font><font size=9>/100</font>" if score is not None else "—", st["p"]),
                      Paragraph(f"<b>Objetivo de la sesión</b><br/>{_esc(sesion.get('objetivo') or '—')}", st["p"]),
                      Paragraph(f"<b>Turnos</b><br/>{sesion.get('turnos')}<br/><b>Tensión máxima</b> {sesion.get('tension_max')}", st["p"])]],
                    colWidths=[45 * mm, 95 * mm, 40 * mm], style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), SUAVE), ("BOX", (0, 0), (-1, -1), 0.5, AQUA),
                                                                             ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 8)])))
    el += [Spacer(1, 8), Paragraph("Resumen", st["h2"]), Paragraph(_esc(res.get("resumen")), st["p"])]
    if res.get("kpis"):
        el.append(Paragraph("Puntuación por KPI", st["h2"]))
        filas = [["KPI", "Score", "Evidencia", "Mejora"]]
        nombres = {k["id"]: k["nombre"] for k in hab.get("kpis", [])}
        for k in res["kpis"]:
            filas.append([Paragraph(f"<b>{_esc(k.get('id'))}</b> {_esc(nombres.get(k.get('id'), ''))}", st["p"]), Paragraph(f"{k.get('score')}", st["chip"]),
                          Paragraph(_esc(k.get("evidencia")), st["p"]), Paragraph(_esc(k.get("mejora")), st["p"])])
        el.append(Table(filas, colWidths=[42 * mm, 14 * mm, 62 * mm, 62 * mm], style=_tabla()))
    if res.get("subdimensiones"):
        el.append(Paragraph(f"Sub-dimensiones · dominio: {_esc(res.get('nivel_dominio'))} ({res.get('score_global')}/10)", st["h2"]))
        filas = [["Sub-dimensión", "Score", "Evidencia"]] + [[Paragraph(_esc(s.get("nombre")), st["p"]), Paragraph(f"{s.get('score')}/10", st["chip"]), Paragraph(_esc(s.get("evidencia")), st["p"])]
                                                            for s in res["subdimensiones"]]
        el.append(Table(filas, colWidths=[50 * mm, 18 * mm, 112 * mm], style=_tabla()))
        el.append(Paragraph(_esc(res.get("justificacion")), st["p"]))
    for titulo, clave, campos in (("Fortalezas", "fortalezas", ("habilidad", "evidencia", "por_que_importa")),
                                  ("Áreas de oportunidad", "oportunidades", ("habilidad", "evidencia", "micro_practica")),
                                  ("Brechas para ascender", "brechas", ("brecha", "evidencia", "impacto_siguiente_nivel"))):
        if res.get(clave):
            el.append(Paragraph(titulo, st["h2"]))
            for f in res[clave]:
                el.append(Paragraph(f"<b>{_esc(f.get(campos[0]))}</b> — {_esc(f.get(campos[1]))}<br/><i>{_esc(f.get(campos[2]))}</i>", st["p"]))
                el.append(Spacer(1, 3))
    if res.get("momentos_clave"):
        el.append(Paragraph("Momentos clave", st["h2"]))
        for m in res["momentos_clave"]:
            el.append(Paragraph(f"<b>Turno {m.get('turno')} · {_esc(m.get('tipo'))}</b>: {_esc(m.get('que_paso'))} <i>{_esc(m.get('que_habria_cambiado'))}</i>", st["p"]))
    if res.get("momento_clave"):
        m = res["momento_clave"]
        el += [Paragraph("El momento clave", st["h2"]), Paragraph(f"{_esc(m.get('que_hizo'))}<br/><b>Alternativa:</b> {_esc(m.get('alternativa'))}<br/><b>Qué habría cambiado:</b> {_esc(m.get('que_habria_cambiado'))}", st["p"])]
    if res.get("plan_accion"):
        el.append(Paragraph("Plan de acción", st["h2"]))
        for i, p in enumerate(res["plan_accion"], 1):
            el.append(Paragraph(f"<b>{i}.</b> {_esc(p.get('paso'))} <i>({_esc(p.get('como_medir') or p.get('senal_de_logro'))})</i>"
                                + (f"<br/>{_esc(p.get('como_practicar_esta_semana'))}" if p.get("como_practicar_esta_semana") else ""), st["p"]))
    if res.get("tips"):
        el.append(Paragraph("Tips", st["h2"]))
        for t in res["tips"]:
            el.append(Paragraph(f"• {_esc(t)}", st["p"]))
    reco = res.get("recomendacion") or res.get("siguiente_paso")
    if reco:
        el.append(Paragraph("Siguiente paso", st["h2"]))
        el.append(Paragraph(_esc(reco.get("objetivo_siguiente") or reco.get("competencia")) + (f" · nivel {_esc(reco.get('nivel_sugerido'))}" if reco.get("nivel_sugerido") else "")
                            + f"<br/><i>{_esc(reco.get('razon') or reco.get('por_que'))}</i>", st["p"]))
    if res.get("pregunta_para_llevarse"):
        el += [Spacer(1, 6), HRFlowable(width="100%", color=AQUA), Paragraph(f"<i>Pregunta para llevarte: {_esc(res['pregunta_para_llevarse'])}</i>", st["p"])]
    doc.build(el, onFirstPage=_pie, onLaterPages=_pie)
    return buf.getvalue()


def _tabla():
    return TableStyle([("BACKGROUND", (0, 0), (-1, 0), VIOLETA), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                       ("FONTSIZE", (0, 0), (-1, 0), 9), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDD6FE")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                       ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SUAVE]), ("PADDING", (0, 0), (-1, -1), 5)])


def ficha_colaborador(ficha: dict) -> bytes:
    st = _estilos()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=20 * mm, bottomMargin=20 * mm, title=f"Mente Viva · Ficha {ficha['nombre']}")
    el = [Paragraph(f"Ficha de desarrollo · {_esc(ficha['nombre'])}", st["h1"]),
          Paragraph(f"{_esc(ficha.get('puesto'))} · {_esc(ficha.get('area'))} · Score promedio {ficha.get('score_promedio') or '—'} · Tendencia {ficha.get('tendencia') if ficha.get('tendencia') is not None else '—'} · Racha {ficha.get('racha')} semanas", st["meta"]),
          Spacer(1, 6), Paragraph("Niveles", st["h2"])]
    filas = [["Habilidad", "Nivel", "Score inicial", "Score actual", "Sesiones"]]
    for h, n in (ficha.get("niveles_detalle") or {}).items():
        filas.append([C.HABILIDADES.get(h, {}).get("nombre", h), n.get("nivel"), n.get("score_inicial") or "—", n.get("score_actual") or "—", n.get("sesiones")])
    el.append(Table(filas, colWidths=[60 * mm, 35 * mm, 28 * mm, 28 * mm, 25 * mm], style=_tabla()))
    if ficha.get("fortalezas") or ficha.get("oportunidades"):
        el += [Paragraph("Diagnóstico de Elena", st["h2"]),
               Paragraph(f"<b>Estilo:</b> {_esc(ficha.get('estilo'))}<br/><b>Fortalezas:</b> {_esc(', '.join(ficha.get('fortalezas') or []))}<br/><b>Oportunidades:</b> {_esc(', '.join(ficha.get('oportunidades') or []))}", st["p"])]
    if ficha.get("sesiones_recientes"):
        el.append(Paragraph("Sesiones recientes", st["h2"]))
        filas = [["Fecha", "Habilidad", "Nivel", "Score", "Objetivo"]] + [[s["fecha"], C.HABILIDADES.get(s["habilidad"], {}).get("corto", s["habilidad"]), s.get("nivel"), s.get("score"),
                                                                          Paragraph(_esc(s.get("objetivo")), st["p"])] for s in ficha["sesiones_recientes"]]
        el.append(Table(filas, colWidths=[22 * mm, 28 * mm, 28 * mm, 16 * mm, 86 * mm], style=_tabla()))
    if ficha.get("roadmaps"):
        el.append(Paragraph("Planes activos", st["h2"]))
        for r in ficha["roadmaps"]:
            el.append(Paragraph(f"<b>{_esc(C.HABILIDADES.get(r['habilidad'], {}).get('nombre', r['habilidad']))}</b> ({_esc(r['estado'])}, {_esc(r['avance'])}): {_esc(r['objetivo'])}<br/><i>Siguiente: {_esc(r.get('siguiente') or '—')}</i>", st["p"]))
    if ficha.get("evaluaciones"):
        el.append(Paragraph("Evaluaciones", st["h2"]))
        filas = [["Tipo", "Periodo", "Promedio", "Evaluador"]] + [[e["tipo"], e["periodo"], e["promedio"], e["evaluador"]] for e in ficha["evaluaciones"]]
        el.append(Table(filas, colWidths=[30 * mm, 30 * mm, 30 * mm, 90 * mm], style=_tabla()))
    doc.build(el, onFirstPage=_pie, onLaterPages=_pie)
    return buf.getvalue()
