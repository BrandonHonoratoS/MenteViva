"""Configuración central de Mente Viva (12-factor: todo por variables de entorno).

Nada sensible vive en el código: la API key de Gemini, la clave secreta y el
superadministrador inicial se definen en Render (o en .env en local).
"""
from __future__ import annotations

import json
import os
from pathlib import Path


def _b(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).strip().lower() in {"1", "true", "yes", "si", "sí", "on"}


def _i(key: str, default: int) -> int:
    try:
        return int(float(os.getenv(key, "") or default))
    except (TypeError, ValueError):
        return default


def _f(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, "") or default)
    except (TypeError, ValueError):
        return default


class Settings:
    APP_NAME = "Mente Viva"
    TAGLINE = "Crece desde adentro, impacta hacia afuera"
    VERSION = "1.0.2"

    def __init__(self) -> None:
        self.APP_ENV = os.getenv("APP_ENV", "development")
        self.SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-cambiar-en-produccion")
        self.BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
        self.TZ = os.getenv("TZ", "America/Mexico_City")

        # Disco persistente: Render monta /data. En local cae a ./data
        data_dir = os.getenv("DATA_DIR") or str(Path.cwd() / "data")
        self.DATA_DIR = Path(data_dir)
        self.DB_PATH = self.DATA_DIR / "mente_viva.db"
        self.EXPORT_DIR = self.DATA_DIR / "exportes"
        for d in (self.DATA_DIR, self.EXPORT_DIR):
            d.mkdir(parents=True, exist_ok=True)

        # ── Superadministrador inicial (equipo Mente Viva) ──────────────────
        self.SUPERADMIN_EMAIL = os.getenv("SUPERADMIN_EMAIL", "admin@menteviva.mx").strip().lower()
        self.SUPERADMIN_PASSWORD = os.getenv("SUPERADMIN_PASSWORD", "cambiar-esta-clave")
        self.SUPERADMIN_NOMBRE = os.getenv("SUPERADMIN_NOMBRE", "Equipo Mente Viva")
        # Empresa inicial (opcional): se crea con su usuario de RRHH al arrancar si la base está vacía
        self.EMPRESA_INICIAL = os.getenv("EMPRESA_INICIAL", "").strip()
        self.RRHH_INICIAL_EMAIL = os.getenv("RRHH_INICIAL_EMAIL", "").strip().lower()
        self.RRHH_INICIAL_PASSWORD = os.getenv("RRHH_INICIAL_PASSWORD", "")
        self.RRHH_INICIAL_NOMBRE = os.getenv("RRHH_INICIAL_NOMBRE", "Recursos Humanos")

        # ── Seguridad ───────────────────────────────────────────────────────
        self.LOGIN_MAX_INTENTOS = _i("LOGIN_MAX_INTENTOS", 8)
        self.LOGIN_VENTANA_MIN = _i("LOGIN_VENTANA_MIN", 15)
        self.SESION_HORAS = _i("SESION_HORAS", 12)
        self.PASSWORD_MIN = _i("PASSWORD_MIN", 10)
        self.COOKIE_SECURE = _b("COOKIE_SECURE", self.APP_ENV == "production")

        # ── Gemini ──────────────────────────────────────────────────────────
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
        # "gemini" = API real; "stub" = simulador determinista SÓLO para pruebas automáticas y desarrollo sin key
        self.LLM_PROVEEDOR = os.getenv("LLM_PROVEEDOR", "gemini" if self.GEMINI_API_KEY else "stub").strip().lower()
        self.GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")            # avatares, feedback, analista
        self.GEMINI_MODEL_LIGERO = os.getenv("GEMINI_MODEL_LIGERO", "gemini-3.5-flash-lite")  # resúmenes, clasificación
        self.GEMINI_THINKING_AVATAR = os.getenv("GEMINI_THINKING_AVATAR", "low")     # low|medium|high
        self.GEMINI_THINKING_ANALISIS = os.getenv("GEMINI_THINKING_ANALISIS", "medium")
        self.GEMINI_TIMEOUT = _i("GEMINI_TIMEOUT", 90)
        # Modelos de respaldo si el principal está saturado (503/429): se prueban en orden
        self.GEMINI_FALLBACKS = [m.strip() for m in os.getenv("GEMINI_FALLBACKS", "gemini-3.7-flash,gemini-3.5-flash,gemini-3.5-flash-lite,gemini-2.5-flash").split(",") if m.strip()]
        self.GROUNDING_MAX_MES = _i("GROUNDING_MAX_MES", 40)   # llamadas con búsqueda de Google al mes (tienen costo aparte)

        # ── Presupuesto de IA (tope duro) ───────────────────────────────────
        self.PRESUPUESTO_MXN = _f("PRESUPUESTO_MXN", 500.0)
        self.TIPO_CAMBIO_MXN_USD = _f("TIPO_CAMBIO_MXN_USD", 20.0)
        self.PRESUPUESTO_AVISO_PCT = _i("PRESUPUESTO_AVISO_PCT", 80)
        # Tarifas USD por millón de tokens (entrada, salida). Verificar en ai.google.dev/gemini-api/docs/pricing
        self.PRICE_TABLE: dict[str, tuple[float, float]] = {
            "gemini-3.8-flash": (0.75, 3.75),
            "gemini-3.7-flash": (0.75, 3.75),
            "gemini-3.5-flash": (1.50, 9.00),
            "gemini-3.5-flash-lite": (0.30, 2.50),
            "gemini-3.1-flash-lite": (0.25, 1.50),
            "gemini-2.5-flash": (0.30, 2.50),
            "gemini-2.5-flash-lite": (0.10, 0.40),
        }
        try:
            self.PRICE_TABLE.update({k: (float(v[0]), float(v[1])) for k, v in json.loads(os.getenv("PRICE_TABLE", "{}")).items()})
        except (ValueError, TypeError, IndexError):
            pass
        self.PRICE_GROUNDING_USD = _f("PRICE_GROUNDING_USD", 0.035)   # costo estimado por consulta con Google Search

        # ── Sesiones de práctica ────────────────────────────────────────────
        self.TURNOS_MAX_SESION = _i("TURNOS_MAX_SESION", 60)       # tope absoluto de intercambios por sesión
        self.TURNOS_RESUMEN = _i("TURNOS_RESUMEN", 10)             # cada N turnos se comprime el historial antiguo
        self.TURNOS_VENTANA = _i("TURNOS_VENTANA", 14)             # mensajes recientes que viajan completos al modelo
        self.ANALISIS_SINCRONO = _b("ANALISIS_SINCRONO", False)    # pruebas: analizar en el mismo hilo

        # ── Programador de tareas ───────────────────────────────────────────
        self.SCHEDULE_ENABLED = _b("SCHEDULE_ENABLED", self.APP_ENV == "production")
        self.RESUMEN_SEMANAL_DIA = _i("RESUMEN_SEMANAL_DIA", 0)     # 0 = lunes
        self.RESUMEN_SEMANAL_HORA = _i("RESUMEN_SEMANAL_HORA", 7)
        self.INACTIVIDAD_DIAS = _i("INACTIVIDAD_DIAS", 7)


settings = Settings()
