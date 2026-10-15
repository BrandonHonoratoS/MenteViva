"""Pruebas con LLM simulado (sin API key): base temporal, análisis síncrono, clientes por rol."""
from __future__ import annotations

import os
import tempfile

import pytest

_TMP = tempfile.mkdtemp(prefix="mv-test-")
os.environ.update({
    "DATA_DIR": _TMP, "LLM_PROVEEDOR": "stub", "ANALISIS_SINCRONO": "1", "SCHEDULE_ENABLED": "0", "APP_ENV": "test",
    "SUPERADMIN_EMAIL": "admin@menteviva.mx", "SUPERADMIN_PASSWORD": "SuperClave123", "EMPRESA_INICIAL": "Ingeniería Cóndor",
    "RRHH_INICIAL_EMAIL": "rrhh@condor.mx", "RRHH_INICIAL_PASSWORD": "ClaveRRHH123", "PRESUPUESTO_MXN": "500",
})

from fastapi.testclient import TestClient  # noqa: E402

from app import db  # noqa: E402
from app.llm import gemini  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


class Sesion:
    """Cliente HTTP con cookie y CSRF de un usuario."""

    def __init__(self, client: TestClient, email: str, password: str):
        self.c = client
        self.email = email
        self.password = password
        r = client.post("/login", data={"email": email, "password": password, "next": "/"}, follow_redirects=False)
        assert r.status_code == 303, r.text
        self.cookie = r.cookies.get("mv_sesion")
        client.cookies.clear()
        u = db.usuario_por_token(self.cookie)
        assert u, "sesión no creada"
        self.u = u
        self.csrf = u["csrf"]

    def _h(self):
        return {"Cookie": f"mv_sesion={self.cookie}", "Origin": "http://testserver", "Sec-Fetch-Site": "same-origin"}

    def get(self, url, **kw):
        return self.c.get(url, headers=self._h(), follow_redirects=kw.pop("follow", False), **kw)

    def post(self, url, data=None, **kw):
        data = dict(data or {})
        data.setdefault("csrf", self.csrf)
        return self.c.post(url, data=data, headers=self._h(), follow_redirects=False, **kw)

    def upload(self, url, nombre: str, contenido: bytes, mime: str, data=None):
        data = dict(data or {})
        data.setdefault("csrf", self.csrf)
        return self.c.post(url, data=data, files={"archivo": (nombre, contenido, mime)}, headers=self._h())

    def api(self, url, body=None):
        body = dict(body or {})
        body.setdefault("csrf", self.csrf)
        return self.c.post(url, json=body, headers=self._h())

    def cambiar_password(self, nueva: str):
        r = self.post("/cuenta/password", {"actual": self.password, "nueva": nueva, "confirmar": nueva})
        assert r.status_code == 303, r.text
        self.password = nueva
        self.u = db.usuario_por_token(self.cookie)


@pytest.fixture
def stub():
    """Permite fijar salidas simuladas por origen; se limpia al terminar."""
    gemini.STUB_OVERRIDES.clear()
    gemini.STUB_LLAMADAS.clear()
    yield gemini.STUB_OVERRIDES
    gemini.STUB_OVERRIDES.clear()


ONBOARDING_VENDEDOR = {
    "contexto": "Trabajo en una empresa",
    "funciones": ["Vendo o asesoro a clientes", "Ejecuto proyectos / consultoría"], "industria": "Manufactura / industria", "experiencia": "2 a 5 años",
    "tipo_producto": "Software / SaaS", "modelo_venta": "A empresas (B2B)", "canal_venta": "Videollamada", "tamano_cliente": "Mediana empresa (100–500)",
    "ticket": "$5,000 — $50,000", "estilo": "Consultivo / asesor", "etapa_debil": "Manejar objeciones", "objetivo_ventas": "Mejorar mi tasa de conversión",
    "dm_lidera": "Superviso a una persona", "dm_trabajo": "Asesorar al cliente", "dm_antiguedad": "6 meses a 2 años", "dm_representa": "Sí, de forma habitual",
    "tiempo_semana": "1 hora", "meta": "Ascender en la ruta de desarrollo",
}


def sesion_rrhh(client) -> Sesion:
    """RRHH con cualquiera de sus dos contraseñas (test_flujo la cambia); limpia el contador de intentos por IP."""
    try:
        s = Sesion(client, "rrhh@condor.mx", "NuevaClaveRRHH1")
    except AssertionError:
        db.limpiar_intentos("ip:testclient")
        s = Sesion(client, "rrhh@condor.mx", "ClaveRRHH123")
        s.cambiar_password("NuevaClaveRRHH1")
    db.limpiar_intentos("ip:testclient")
    return s


ENCUESTA_VALIDA = {"relacion": "Colaborador de mi empresa", "veces_uso": "Una vez", "edad": "25–34", "experiencia": "2 a 5", "uso_ia": "Cada semana", "dispositivo": "Computadora",
                   "capacitacion_previa": "No", "utilidad": "4 · Muy útil", "calificacion": "9", "realismo": "4", "utilidad_feedback": "5", "facilidad": "4",
                   "valora": ["Retroalimentación de la IA", "Poder practicar sin temor a equivocarme"], "aprendizaje": "Sí, claramente", "frecuencia": "Una vez por semana", "nps": "10",
                   "gusto": "El feedback con evidencia", "mejora": "Más escenarios", "fallo": "", "pagaria": "Sí, con las funcionalidades actuales", "monto_mensual": "$150 a $199 MXN",
                   "precio_unico": "1500", "modalidad_pago": "Mensual", "cuando_pagar": "De inmediato", "quien_paga": "Mi empresa", "funciones": ["Avatares con voz", "App móvil"],
                   "comparacion": "", "entrevista": "Sí", "comentario": "Gracias"}


@pytest.fixture(autouse=True)
def encuesta_no_bloquea(request, monkeypatch):
    """La encuesta de experiencia es obligatoria tras la primera práctica; en las pruebas sólo se exige donde se prueba explícitamente."""
    if request.node.get_closest_marker("encuesta_obligatoria"):
        yield
        return
    from app.routes import colaborador
    monkeypatch.setattr(colaborador, "_encuesta_obligatoria", lambda u: None)
    yield
