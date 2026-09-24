"""Capa de modelo de lenguaje (Gemini) diseñada para gastar pocos tokens.

Principios
- Un solo punto de entrada `llm.generar()` con salida estructurada (JSON Schema) para no re-parsear texto.
- Dos modelos: `principal` (avatares, feedback, analista) y `ligero` (resúmenes, clasificación).
- El contenido estable (instrucciones del avatar + escenario) va primero para aprovechar la caché implícita de Gemini.
- Cada llamada registra tokens y costo; si el presupuesto mensual (MXN) se agotó, se rechaza ANTES de llamar.
- La búsqueda de Google (grounding) es opcional, acotada por mes y siempre devuelve las fuentes usadas.
- `LLM_PROVEEDOR=stub` activa un simulador determinista sólo para pruebas automáticas y desarrollo sin key.
"""
from __future__ import annotations

import json
import logging
import random
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from .. import db
from ..config import settings

log = logging.getLogger("mv.llm")


class PresupuestoAgotado(RuntimeError):
    """El paquete mensual de IA se terminó: hay que ampliar el presupuesto (superadmin)."""


class ErrorLLM(RuntimeError):
    pass


@dataclass
class Respuesta:
    texto: str = ""
    json: Any = None
    fuentes: list[dict] = field(default_factory=list)
    modelo: str = ""
    tok_in: int = 0
    tok_out: int = 0
    tok_think: int = 0
    tok_cache: int = 0
    costo_usd: float = 0.0
    ms: int = 0
    llamadas_funcion: list[dict] = field(default_factory=list)


def _precio(modelo: str) -> tuple[float, float]:
    tabla = db.get_ajuste("price_table", None) or {}
    if modelo in tabla:
        return float(tabla[modelo][0]), float(tabla[modelo][1])
    return settings.PRICE_TABLE.get(modelo, (1.0, 5.0))


def costo_usd(modelo: str, tok_in: int, tok_out: int, tok_think: int = 0, tok_cache: int = 0, grounded: bool = False) -> float:
    pin, pout = _precio(modelo)
    # los tokens en caché cuestan ~10 % de la entrada; el pensamiento se cobra como salida
    c = ((tok_in - tok_cache) * pin + tok_cache * pin * 0.1 + (tok_out + tok_think) * pout) / 1_000_000
    if grounded:
        c += settings.PRICE_GROUNDING_USD
    return round(max(c, 0.0), 6)


TRANSITORIOS = ("429", "503", "500", "502", "504", "timeout", "Timeout", "RESOURCE_EXHAUSTED", "UNAVAILABLE", "overloaded", "high demand", "Deadline")


def _transitorio(msg: str) -> bool:
    return any(k in msg for k in TRANSITORIOS)


def _mensaje_error(msg: str) -> str:
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
        return "El modelo de IA alcanzó su límite de peticiones por minuto (nivel gratuito). Espera 30–60 segundos y pulsa Reintentar."
    if _transitorio(msg):
        return "El modelo de IA está saturado en este momento (alta demanda). Pulsa Reintentar; si persiste, espera un minuto."
    if "API key" in msg or "API_KEY" in msg or "401" in msg or "403" in msg:
        return "La API key de Gemini no es válida o no tiene permisos. Revísala en Render → Environment."
    return f"La IA no respondió ({msg[:120]}). Intenta de nuevo en un momento."


_SATURADO: dict[str, float] = {}     # modelo → hasta cuándo evitarlo (epoch)
SATURADO_SEG = 180


def _thinking_config(types, modelo: str, nivel: str | None):
    """Gemini 3.x usa thinking_level; 2.5 usa thinking_budget. 'off' desactiva donde se puede."""
    if not nivel:
        return None
    if modelo.startswith("gemini-2.5"):
        presupuesto = {"off": 0, "low": 512, "medium": 2048, "high": 8192}.get(nivel, 512)
        if "pro" in modelo and presupuesto == 0:
            presupuesto = 128   # 2.5 Pro no permite desactivar el pensamiento
        return types.ThinkingConfig(thinking_budget=presupuesto)
    if nivel == "off":
        return None if "lite" in modelo else types.ThinkingConfig(thinking_level="low")
    return types.ThinkingConfig(thinking_level=nivel)


def modelos_respaldo() -> list[str]:
    conf = db.get_ajuste("modelos_respaldo", None)
    if isinstance(conf, list) and conf:
        return [str(m) for m in conf]
    return list(settings.GEMINI_FALLBACKS)


def modelo_para(clase: str) -> str:
    if clase == "ligero":
        return db.get_ajuste("modelo_ligero", settings.GEMINI_MODEL_LIGERO)
    return db.get_ajuste("modelo_principal", settings.GEMINI_MODEL)


# ── simulador determinista (pruebas) ────────────────────────────────────────
STUB_OVERRIDES: dict[str, Any] = {}        # origen → dict/valor que se mezcla en la salida simulada
STUB_LLAMADAS: list[dict] = []             # registro de llamadas para las pruebas


def _stub_valor(schema: dict, nombre: str = "", prof: int = 0) -> Any:
    t = schema.get("type")
    if "enum" in schema:
        return schema["enum"][0]
    if t == "object":
        return {k: _stub_valor(v, k, prof + 1) for k, v in (schema.get("properties") or {}).items()}
    if t == "array":
        n = min(int(schema.get("minItems", 2) or 2), 3)
        return [_stub_valor(schema.get("items", {"type": "string"}), nombre, prof + 1) for _ in range(n)]
    if t == "integer":
        lo, hi = schema.get("minimum", 0), schema.get("maximum", 100)
        return int((lo + hi) / 2)
    if t == "number":
        lo, hi = schema.get("minimum", 0), schema.get("maximum", 100)
        return round((lo + hi) / 2, 1)
    if t == "boolean":
        return True
    return f"[simulado] {nombre or 'texto'}"


def _stub_responder(origen: str, schema: dict | None, contents: list[dict]) -> tuple[str, Any]:
    ultimo = next((c["text"] for c in reversed(contents) if c.get("role") == "user"), "")
    if schema:
        val = _stub_valor(schema)
        ov = STUB_OVERRIDES.get(origen)
        if isinstance(ov, dict) and isinstance(val, dict):
            val.update(ov)
        elif ov is not None:
            val = ov
        if isinstance(val, dict) and "mensaje" in val and "mensaje" not in (ov or {}):
            val["mensaje"] = f"[{origen}] Entendido. Cuéntame más sobre eso." if ultimo else f"[{origen}] Hola, empecemos."
        return json.dumps(val, ensure_ascii=False), val
    return STUB_OVERRIDES.get(origen) or f"[simulado:{origen}] Respuesta a: {ultimo[:80]}", None


# ── cliente ─────────────────────────────────────────────────────────────────
class LLM:
    def __init__(self) -> None:
        self._cliente = None
        self._lock = threading.Lock()

    @property
    def activo(self) -> bool:
        return settings.LLM_PROVEEDOR == "gemini" and bool(settings.GEMINI_API_KEY)

    @property
    def simulado(self) -> bool:
        return settings.LLM_PROVEEDOR == "stub"

    def _client(self):
        if self._cliente is None:
            with self._lock:
                if self._cliente is None:
                    from google import genai
                    self._cliente = genai.Client(api_key=settings.GEMINI_API_KEY,
                                                 http_options={"timeout": settings.GEMINI_TIMEOUT * 1000})
        return self._cliente

    # ------------------------------------------------------------------
    def generar(self, *, origen: str, system: str, contents: list[dict], schema: dict | None = None, clase: str = "principal",
                temperatura: float = 0.7, max_tokens: int = 1024, thinking: str | None = None, grounding: bool = False,
                herramientas: list[dict] | None = None, usuario_id: int | None = None, sesion_id: int | None = None,
                reintentos: int = 2) -> Respuesta:
        """Genera una respuesta. `contents` = [{"role": "user"|"model", "text": "..."}] o partes de función.

        - `schema`: JSON Schema de la salida (se fuerza response_mime_type=application/json).
        - `grounding`: activa Google Search; incompatible con `herramientas` en la misma llamada.
        - `herramientas`: declaraciones de función [{name, description, parameters}]; la respuesta trae `llamadas_funcion`.
        """
        pres = db.presupuesto()
        if pres["agotado"]:
            db.log("warn", "presupuesto", "Llamada rechazada: presupuesto agotado", origen, str(usuario_id or ""))
            raise PresupuestoAgotado("El paquete mensual de IA se agotó. Pide al equipo Mente Viva ampliar el presupuesto.")
        if grounding and pres["grounded_mes"] >= pres["grounding_max"]:
            grounding = False   # se degrada a respuesta sin búsqueda; el agente lo indica

        modelo = modelo_para(clase)
        inicio = time.time()
        if self.simulado:
            texto, js = _stub_responder(origen, schema, contents)
            STUB_LLAMADAS.append({"origen": origen, "modelo": modelo, "system": system, "contents": contents, "schema": schema, "grounding": grounding})
            r = Respuesta(texto=texto, json=js, modelo=modelo, tok_in=len(system) // 4 + sum(len(c.get("text", "")) for c in contents) // 4,
                          tok_out=len(texto) // 4, ms=1)
            if grounding:
                r.fuentes = [{"titulo": "Fuente simulada", "url": "https://example.org/simulado", "dominio": "example.org"}]
            if herramientas and STUB_OVERRIDES.get(origen + ".funcion"):
                r.llamadas_funcion = [STUB_OVERRIDES[origen + ".funcion"]]
            r.costo_usd = costo_usd(modelo, r.tok_in, r.tok_out, grounded=grounding)
            db.registrar_uso(modelo, origen, r.tok_in, r.tok_out, grounded=grounding, costo_usd=r.costo_usd, usuario_id=usuario_id, ms=1)
            if sesion_id:
                db.sumar_uso_sesion(sesion_id, r.tok_in, r.tok_out, r.costo_usd)
            return r
        if not self.activo:
            raise ErrorLLM("La IA no está configurada: falta GEMINI_API_KEY en el servidor.")

        from google.genai import types
        partes_contents = []
        for c in contents:
            if "function_response" in c:
                partes_contents.append(types.Content(role="user", parts=[types.Part.from_function_response(
                    name=c["function_response"]["name"], response=c["function_response"]["response"])]))
            elif "function_call" in c:
                partes_contents.append(types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(
                    name=c["function_call"]["name"], args=c["function_call"]["args"]))]))
            else:
                partes_contents.append(types.Content(role=c.get("role", "user"), parts=[types.Part(text=c.get("text", ""))]))

        cfg: dict[str, Any] = {"system_instruction": system, "temperature": temperatura, "max_output_tokens": max_tokens,
                               "safety_settings": [types.SafetySetting(category=cat, threshold="BLOCK_ONLY_HIGH") for cat in (
                                   "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_DANGEROUS_CONTENT")]}
        nivel_think = thinking or (settings.GEMINI_THINKING_AVATAR if clase == "principal" else "low")
        if schema:
            cfg["response_mime_type"] = "application/json"
            cfg["response_json_schema"] = schema
        tools = []
        if grounding:
            tools.append(types.Tool(google_search=types.GoogleSearch()))
        if herramientas:
            decl = []
            for h in herramientas:
                params = h.get("parameters") if (h.get("parameters") or {}).get("properties") else None
                decl.append(types.FunctionDeclaration(name=h["name"], description=h.get("description", ""), parameters=params))
            tools.append(types.Tool(function_declarations=decl))
            cfg["automatic_function_calling"] = types.AutomaticFunctionCallingConfig(disable=True)
        if tools:
            cfg["tools"] = tools

        # Cadena de modelos: el principal y, si está saturado (503/429/500), los de respaldo en orden.
        cadena = [modelo] + [m for m in modelos_respaldo() if m != modelo]
        ahora = time.time()
        cadena = [m for m in cadena if _SATURADO.get(m, 0) < ahora] + [m for m in cadena if _SATURADO.get(m, 0) >= ahora]   # los saturados al final
        resp = None
        ultimo_error: Exception | None = None
        for idx, mdl in enumerate(cadena):
            sin_thinking = False
            for intento in range(reintentos + 1):
                try:
                    cfg_m = dict(cfg)
                    tc = None if sin_thinking else _thinking_config(types, mdl, nivel_think)
                    if tc is not None:
                        cfg_m["thinking_config"] = tc
                    resp = self._client().models.generate_content(model=mdl, contents=partes_contents, config=types.GenerateContentConfig(**cfg_m))
                    break
                except Exception as e:  # noqa: BLE001 — la API puede fallar por red/cuota; se reintenta con espera
                    ultimo_error = e
                    if _transitorio(str(e)) and intento < reintentos:
                        time.sleep(min(8.0, 1.5 * (2 ** intento)) + random.random())
                        continue
                    if not _transitorio(str(e)) and "thinking" in str(e).lower() and not sin_thinking:
                        sin_thinking = True    # el modelo no acepta esa configuración de pensamiento: se repite sin ella
                        continue
                    if not _transitorio(str(e)):
                        db.log("error", "llm", f"Fallo de Gemini en {origen}", str(e)[:500], str(usuario_id or ""))
                        raise ErrorLLM(_mensaje_error(str(e))) from e
                    _SATURADO[mdl] = time.time() + SATURADO_SEG   # se evita este modelo unos minutos
                    break   # transitorio y sin reintentos: probar el siguiente modelo
            if resp is not None:
                if mdl != modelo:
                    db.log("warn", "llm", f"Modelo de respaldo usado en {origen}", f"{modelo} → {mdl}", str(usuario_id or ""))
                modelo = mdl
                break
        if resp is None:
            db.log("error", "llm", f"Gemini saturado en {origen}", str(ultimo_error)[:500], str(usuario_id or ""))
            raise ErrorLLM(_mensaje_error(str(ultimo_error))) from ultimo_error

        ms = int((time.time() - inicio) * 1000)
        um = getattr(resp, "usage_metadata", None)
        tok_in = int(getattr(um, "prompt_token_count", 0) or 0)
        tok_out = int(getattr(um, "candidates_token_count", 0) or 0)
        tok_think = int(getattr(um, "thoughts_token_count", 0) or 0)
        tok_cache = int(getattr(um, "cached_content_token_count", 0) or 0)
        r = Respuesta(modelo=modelo, tok_in=tok_in, tok_out=tok_out, tok_think=tok_think, tok_cache=tok_cache, ms=ms)

        # llamadas a función
        try:
            for fc in (resp.function_calls or []):
                r.llamadas_funcion.append({"name": fc.name, "args": dict(fc.args or {})})
        except Exception:  # noqa: BLE001
            pass
        # texto
        try:
            r.texto = (resp.text or "").strip() if not r.llamadas_funcion else (resp.text or "")
        except Exception:  # noqa: BLE001
            r.texto = ""
        if schema and not r.llamadas_funcion:
            r.json = _parse_json(r.texto)
            if r.json is None:
                db.log("warn", "llm", f"JSON inválido en {origen}", r.texto[:300])
        # fuentes (grounding)
        if grounding:
            r.fuentes = _fuentes(resp)
        grounded_real = grounding and bool(r.fuentes)
        r.costo_usd = costo_usd(modelo, tok_in, tok_out, tok_think, tok_cache, grounded=grounded_real)
        db.registrar_uso(modelo, origen, tok_in, tok_out, tok_think, tok_cache, grounded=grounded_real, costo_usd=r.costo_usd, usuario_id=usuario_id, ms=ms)
        if sesion_id:
            db.sumar_uso_sesion(sesion_id, tok_in, tok_out + tok_think, r.costo_usd)
        return r


def _parse_json(texto: str) -> Any:
    if not texto:
        return None
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}|\[.*\]", texto, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


def _fuentes(resp) -> list[dict]:
    out: list[dict] = []
    try:
        gm = resp.candidates[0].grounding_metadata
        for ch in (gm.grounding_chunks or []):
            w = getattr(ch, "web", None)
            if w and w.uri:
                dominio = re.sub(r"^https?://(www\.)?", "", w.uri).split("/")[0]
                if not any(f["url"] == w.uri for f in out):
                    out.append({"titulo": w.title or dominio, "url": w.uri, "dominio": dominio})
    except Exception:  # noqa: BLE001
        pass
    return out


llm = LLM()
