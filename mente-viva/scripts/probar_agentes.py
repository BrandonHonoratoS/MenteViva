"""Prueba de punta a punta de los 4 agentes con Gemini REAL (necesita GEMINI_API_KEY).

Uso (en tu computadora, dentro de la carpeta del proyecto):
    pip install -r requirements.txt
    set GEMINI_API_KEY=AIza...            (Windows)   |   export GEMINI_API_KEY=AIza...   (Mac/Linux)
    python scripts/probar_agentes.py

Crea una base temporal, un colaborador de prueba y ejecuta: diagnóstico con Elena (con respuestas guionizadas) → roadmaps →
sesión con Celeste → sesión con Juan → Analista (lectura, chat con herramientas e investigación con fuentes).
Imprime cada respuesta, las validaciones y el costo. Al final resume qué pasó y qué falló. No usa Render ni la base real.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if not os.getenv("GEMINI_API_KEY"):
    print("Falta GEMINI_API_KEY en el entorno."); sys.exit(1)
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="mv-prueba-")
os.environ.update({"LLM_PROVEEDOR": "gemini", "ANALISIS_SINCRONO": "1", "SCHEDULE_ENABLED": "0", "EMPRESA_INICIAL": "Ingeniería Cóndor",
                   "RRHH_INICIAL_EMAIL": "rrhh@prueba.mx", "RRHH_INICIAL_PASSWORD": "Prueba12345678", "SUPERADMIN_EMAIL": "admin@prueba.mx",
                   "SUPERADMIN_PASSWORD": "Prueba12345678", "PRESUPUESTO_MXN": os.getenv("PRESUPUESTO_MXN", "500")})

from app import db  # noqa: E402
from app.agents import analista, catalogo as C, motor  # noqa: E402
from app.llm.gemini import ErrorLLM  # noqa: E402

OK, FALLOS = [], []


def paso(nombre, fn):
    t = time.time()
    try:
        out = fn()
        print(f"  ✔ {nombre} ({time.time() - t:.1f}s)")
        OK.append(nombre)
        return out
    except Exception as e:  # noqa: BLE001
        print(f"  ✘ {nombre}: {e}")
        FALLOS.append((nombre, str(e)))
        return None


def hablar(sesion, usuario, textos, mostrar=True):
    for t in textos:
        s = db.sesion(sesion["id"])
        if s["estado"] != "en_curso":
            break
        for intento in range(3):
            try:
                r = motor.turno(s, usuario, t)
                break
            except ErrorLLM as e:
                print(f"     · reintento por: {e}"); time.sleep(5)
        else:
            raise ErrorLLM("turno falló 3 veces")
        if mostrar:
            print(f"     TÚ: {t}\n     {r.get('fase', r.get('estado', ''))} · tensión {r.get('tension', '-')} → {r['texto'][:220]}")
        if r.get("estado") == "fin" or r.get("fase") == "fin":
            motor.terminar(db.sesion(sesion["id"]), usuario, en_hilo=False)
            return
    s = db.sesion(sesion["id"])
    if s["estado"] == "en_curso":
        motor.terminar(s, usuario, en_hilo=False)


db.init_db()
emp = db.empresas()[0]
aid = db.crear_area(emp["id"], "Odoo")
uid = db.crear_usuario("prueba@prueba.mx", "Prueba12345678", "Sofía Prueba", "colaborador", emp["id"], aid, "Consultora funcional", debe_cambiar=False)
did = db.crear_usuario("dir@prueba.mx", "Prueba12345678", "Diana Directora", "director", emp["id"], aid, "Directora", debe_cambiar=False)
db.actualizar_area(aid, director_id=did)
u = db.usuario(uid)
onb = {"funciones": ["Vendo o asesoro a clientes", "Ejecuto proyectos / consultoría"], "industria": "Manufactura / industria", "experiencia": "2 a 5 años",
       "tipo_producto": "Software / SaaS", "modelo_venta": "A empresas (B2B)", "canal_venta": "Videollamada", "tamano_cliente": "Mediana empresa (100–500)",
       "ticket": "$5,000 — $50,000", "estilo": "Consultivo / asesor", "etapa_debil": "Manejar objeciones", "objetivo_ventas": "Mejorar mi tasa de conversión",
       "dm_lidera": "No lidero a nadie", "dm_trabajo": "Asesorar al cliente", "dm_antiguedad": "6 meses a 2 años", "dm_representa": "A veces, acompañado",
       "tiempo_semana": "1 hora", "meta": "Ascender en la ruta de desarrollo", "producto_concreto": "Implementación de Odoo para PYMES de manufactura"}
db.guardar_perfil(uid, onboarding=onb, estado="onboarding")
print(f"\nModelo principal: {db.get_ajuste('modelo_principal', os.getenv('GEMINI_MODEL', 'gemini-3.8-flash'))}\n")

# ── 1. Elena · diagnóstico ───────────────────────────────────────────────────
print("1) ELENA · diagnóstico")
ses = paso("apertura", lambda: motor.iniciar(u, "entrevistas", tipo="diagnostico", nivel="Intermedio", objetivo="Diagnóstico inicial de competencias"))
if ses:
    db.guardar_perfil(uid, estado="entrevista", sesion_diagnostico_id=ses["id"])
    print("     ELENA:", db.mensajes(ses["id"])[0]["texto"][:220])
    paso("entrevista (8 turnos + Fin)", lambda: hablar(ses, u, [
        "Bien, gracias. Fue un día movido: cerré la configuración de inventarios de un cliente de manufactura.",
        "Sí, tiene sentido. Adelante.",
        "El proyecto más difícil fue una migración de Odoo para una planta en Monterrey. El cliente quería arrancar en 4 semanas y el equipo éramos tres.",
        "Yo llevaba la relación con el gerente de operaciones. Cuando vi que no llegábamos, propuse arrancar solo con compras e inventario y dejar manufactura para una segunda fase.",
        "Le dije: 'Prefiero que arranquen con dos módulos funcionando a con cinco a medias'. Al principio se molestó, pero le mostré el plan por semana y aceptó.",
        "Arrancamos a tiempo con dos módulos; manufactura salió 3 semanas después. El cliente nos dio una carta de referencia.",
        "Un error: en otro proyecto no confirmé por escrito el alcance y el cliente pidió reportes que no estaban contemplados. Aprendí a cerrar todo por correo.",
        "Fin"]))
    s = db.sesion(ses["id"])
    if s["estado"] == "completada":
        perfil = db.perfil(uid); d = perfil["diagnostico"]
        print(f"     Diagnóstico: ventas={d['nivel_ventas']} · DM={d['nivel_dm']} · score inicial={d['score_inicial']} · estilo={d['estilo_comunicacion']}")
        print("     Fortalezas:", "; ".join(f["habilidad"] for f in d["fortalezas"]))
        print("     Prioridades:", ", ".join(f"{p['habilidad_id']}({p['brecha']})" for p in d["prioridades"]))
        rms = db.roadmaps(uid)
        print("     Roadmaps:", ", ".join(f"{r['habilidad']}:{r['estado']}:{r['total']} sesiones" for r in rms))
        paso("roadmaps generados", lambda: rms or (_ for _ in ()).throw(RuntimeError("sin roadmaps")))
        for r in rms[:1]:
            for it in r["items"][:3]:
                print(f"       S{it['semana']} {it['competencia'] or ''} → {it['objetivo']}")
    else:
        FALLOS.append(("diagnóstico", s.get("error") or s["estado"]))

# ── 2. Celeste ───────────────────────────────────────────────────────────────
print("\n2) CELESTE · Clínica de Ventas")
item = db.siguiente_item(uid, "ventas")
ses = paso("apertura", lambda: motor.iniciar(u, "ventas", item=item, nivel=None if item else "Principiante", voluntaria=item is None))
if ses:
    print("     CELESTE:", db.mensajes(ses["id"])[0]["texto"][:220] if db.mensajes(ses["id"]) else "(sin apertura)")
    paso("roleplay (7 turnos)", lambda: hablar(ses, u, [
        "Buenos días, Celeste. Antes de hablarle del sistema, ¿me cuenta cómo controlan hoy los pedidos y el inventario?",
        "Entiendo. ¿Y cuánto les cuesta al mes un error de captura, entre retrabajo y entregas tardías?",
        "Si eso pasa dos veces al mes, son unos 40 mil pesos al año solo en retrabajo. ¿Qué pasaría si además pierden un cliente por una entrega mal hecha?",
        "Comparado con qué le parece caro: ¿con otro software o con lo que pierden hoy? Nuestra implementación se paga con dos meses de esos errores.",
        "Le propongo esto: una sesión diagnóstica de 2 horas en su planta el martes a las 10 para cuantificarlo con sus números. ¿Le acomoda?",
        "(silencio)",
        "Fin"]))
    s = db.sesion(ses["id"])
    if s["estado"] == "completada":
        res = s["resultado"]
        print(f"     Score {s['score_global']} · cierre={res['evidencia']['cierre']} · técnicas={[t['id'] for t in res['evidencia']['tecnicas_usadas']]} · SPIN={res['evidencia']['spin']}")
        for k in res["kpis"]:
            print(f"       {k['id']} {k['score']:>3} · {k['evidencia'][:90]}")
        print("     Siguiente:", res["recomendacion"]["objetivo_siguiente"])
        an = db.analisis(emp["id"], tipo="post_sesion", usuario_id=uid, limite=1)
        paso("lectura del Analista", lambda: an or (_ for _ in ()).throw(RuntimeError("sin análisis")))
        if an:
            print(f"     ANALISTA: riesgo {an[0]['contenido']['riesgo']} · {an[0]['contenido']['lectura'][:200]}")
    else:
        FALLOS.append(("celeste", s.get("error") or s["estado"]))

# ── 3. Juan Artiaga ──────────────────────────────────────────────────────────
print("\n3) JUAN ARTIAGA · Ruta DM")
item = db.siguiente_item(uid, "ruta_dm")
ses = paso("diseño + apertura", lambda: motor.iniciar(u, "ruta_dm", item=item, nivel=None if item else "DM1", voluntaria=item is None))
if ses:
    e = ses["escenario"]
    print(f"     Diseño: {e.get('formato')} · {e.get('titulo')} · personaje: {e.get('personaje') or '-'} · sub-dimensiones: {e.get('subdimensiones')}")
    print("     JUAN:", db.mensajes(ses["id"])[0]["texto"][:220] if db.mensajes(ses["id"]) else "(sin apertura)")
    paso("ejercicio (5 turnos)", lambda: hablar(ses, u, [
        "Entiendo la situación. Antes de proponer algo, ¿me ayuda a entender qué es lo que más le preocupa de esto?",
        "Le agradezco la franqueza. Lo que puedo comprometer hoy es un plan por semana con entregables verificables; lo que no puedo es una fecha que no se pueda cumplir.",
        "Propongo dos opciones: A) arrancar el 15 con el módulo crítico y el resto en dos semanas; B) todo el 30 con pruebas completas. ¿Cuál le sirve más a su operación?",
        "Perfecto. Lo dejo por escrito hoy mismo con responsables y fechas, y le doy seguimiento cada viernes.",
        "Fin"]))
    s = db.sesion(ses["id"])
    if s["estado"] == "completada":
        res = s["resultado"]
        print(f"     Score {res['score_global']}/10 · {res['nivel_dominio']} · sub-dimensiones: " + ", ".join(f"{x['nombre']} {x['score']}" for x in res["subdimensiones"]))
        print("     Momento clave:", res["momento_clave"]["que_hizo"][:160])
        print("     Siguiente competencia:", res["siguiente_paso"]["competencia"])
    else:
        FALLOS.append(("juan", s.get("error") or s["estado"]))

# ── 4. Analista · chat e investigación ───────────────────────────────────────
print("\n4) ANALISTA · chat con herramientas e investigación")
dirx = db.usuario(did)
r = paso("chat del director", lambda: analista.chat(dirx, "¿Cómo va Sofía y qué debo hacer con ella esta semana?"))
if r:
    print(f"     usó: {r['herramientas']} → {r['texto'][:300]}")
r = paso("investigación con fuentes", lambda: analista.investigar("evidencia sobre práctica deliberada y feedback inmediato para desarrollar habilidades de venta", dirx))
if r:
    print(f"     fuentes: {[f['dominio'] for f in r['fuentes']]} → {r['texto'][:200]}")
r = paso("resumen semanal", lambda: analista.resumen_periodico(emp["id"], "organizacion", dias=30))

# ── resumen ──────────────────────────────────────────────────────────────────
uso = db.uso_periodo()
print(f"\nUso: {uso['llamadas']} llamadas · {uso['tok_in']} tokens entrada · {uso['tok_out']} salida · {uso['tok_think']} pensamiento · {uso['costo_usd']:.4f} USD ≈ {uso['costo_usd'] * 20:.2f} MXN")
print("Modelos usados:", sorted({o["origen"] for o in uso["por_origen"]}))
print(f"\n{len(OK)} pasos OK · {len(FALLOS)} fallos")
for n, e in FALLOS:
    print(f"  ✘ {n}: {e}")
for f in db.bitacora(50):
    if f["nivel"] in ("warn", "error") and f["origen"] in ("llm", "sesion", "roadmap", "analista"):
        print(f"  [{f['nivel']}] {f['evento']}: {f['detalle'][:160]}")
