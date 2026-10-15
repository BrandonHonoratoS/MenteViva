"""Adjuntos de una sesión: grabaciones de voz y fotos.

- La grabación se envía UNA vez a Gemini (entrada de audio nativa) para transcribirla y medir la voz (duración, palabras por minuto,
  muletillas, pausas, ritmo, variedad vocal, energía al cierre, seguridad). A partir de ahí la sesión trabaja con la transcripción y
  esas métricas (texto barato); el archivo de audio NO se guarda en disco ni en la base de datos.
- La foto se envía UNA vez para obtener una descripción objetiva de la vestimenta (sin describir ni juzgar el cuerpo de la persona);
  la imagen no se guarda. Sólo la descripción queda en el mensaje.
Costo aproximado: audio ≈ 32 tokens por segundo (3 min ≈ 5,800 tokens de entrada); imagen ≈ 260–1,000 tokens.
"""
from __future__ import annotations

import logging
import os
import subprocess
import tempfile

from ..config import settings
from ..llm import llm
from ..llm.gemini import ErrorLLM
from . import esquemas as E
from . import prompts as P
from . import validar as V

AUDIO_MIMES = {"audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav", "audio/x-wav", "audio/aac", "audio/m4a", "audio/x-m4a", "audio/mp3", "video/webm", "video/mp4"}
IMAGEN_MIMES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif", "image/avif"}
AUDIO_MAX_BYTES = 20 * 1024 * 1024
IMAGEN_MAX_BYTES = 8 * 1024 * 1024
AUDIO_MAX_SEG = 420   # 7 minutos (la simulación integral del programa dura 5 + 2 de preguntas)
GEMINI_AUDIO_OK = {"audio/wav", "audio/mpeg", "audio/aiff", "audio/aac", "audio/ogg", "audio/flac"}   # formatos que Gemini acepta nativamente
log = logging.getLogger("mv.adjuntos")


def _ffmpeg() -> str | None:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001
        return None


def convertir_a_flac(data: bytes, ext: str = "webm") -> tuple[bytes, str] | None:
    """El navegador graba WebM/Opus (Chrome) o MP4/AAC (Safari); Gemini no acepta WebM, así que se convierte a FLAC 16 kHz mono (ligero y sin pérdida).
    Devuelve (bytes, 'audio/flac') o None si no hay ffmpeg o falla (entonces se envía el original)."""
    exe = _ffmpeg()
    if not exe:
        return None
    src = dst = None
    try:
        with tempfile.NamedTemporaryFile(suffix="." + ext, delete=False) as f:
            f.write(data)
            src = f.name
        dst = src + ".flac"
        r = subprocess.run([exe, "-y", "-loglevel", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "flac", dst], capture_output=True, timeout=60)
        if r.returncode != 0 or not os.path.exists(dst):
            log.warning("ffmpeg no pudo convertir el audio: %s", r.stderr.decode(errors="ignore")[:200])
            return None
        with open(dst, "rb") as f:
            return f.read(), "audio/flac"
    except Exception as e:  # noqa: BLE001
        log.warning("conversión de audio fallida: %s", e)
        return None
    finally:
        for p in (src, dst):
            if p and os.path.exists(p):
                os.remove(p)   # nada de audio queda en disco


def _mime_audio(mime: str) -> str:
    m = (mime or "").split(";")[0].strip().lower()
    if m.startswith("video/"):
        m = "audio/" + m.split("/")[1]   # MediaRecorder en algunos navegadores etiqueta el audio como video/webm o video/mp4
    return {"audio/x-wav": "audio/wav", "audio/m4a": "audio/mp4", "audio/x-m4a": "audio/mp4", "audio/mp3": "audio/mpeg"}.get(m, m)


def transcribir_audio(usuario: dict, sesion: dict, data: bytes, mime: str, duracion_s: float | None = None) -> dict:
    if not data or len(data) > AUDIO_MAX_BYTES:
        raise ValueError("La grabación está vacía o pesa más de 20 MB.")
    if (mime or "").split(";")[0].strip().lower() not in AUDIO_MIMES:
        raise ValueError("Formato de audio no soportado (usa el micrófono del navegador).")
    if duracion_s and duracion_s > AUDIO_MAX_SEG:
        raise ValueError(f"La grabación supera el máximo de {AUDIO_MAX_SEG // 60} minutos.")
    texto = "Transcribe y analiza esta grabación." + (f" Duración medida por el navegador: {int(duracion_s)} s." if duracion_s else "")
    m = _mime_audio(mime)
    if m not in GEMINI_AUDIO_OK and not llm.simulado:
        conv = convertir_a_flac(data, {"audio/webm": "webm", "audio/mp4": "mp4", "audio/ogg": "ogg"}.get(m, "webm"))
        if conv:
            data, m = conv
    r = llm.generar(origen="audio.transcribir", system=P.AUDIO_TRANSCRIBIR, contents=[{"role": "user", "text": texto, "inline": [{"mime": m, "data": data}]}],
                    schema=E.AUDIO, thinking="low", max_tokens=6000, temperatura=0.1, usuario_id=usuario["id"], sesion_id=sesion["id"])
    if not isinstance(r.json, dict):
        raise ErrorLLM("No se pudo transcribir la grabación. Pulsa Reintentar o escribe tu respuesta.")
    a = V.audio(r.json, duracion_s)
    if llm.simulado and not a["transcripcion"]:
        a["transcripcion"] = "[simulado] transcripción de la grabación"
    if not a["transcripcion"]:
        raise ValueError("La grabación no tiene voz audible. Revisa tu micrófono e inténtalo de nuevo.")
    return a


def _mime_imagen(data: bytes, mime: str, nombre: str = "") -> str:
    """Tipo real de la imagen: por la firma de los bytes (algunos navegadores mandan HEIC/JPG como application/octet-stream o vacío)."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[4:8] == b"ftyp" and data[8:12] in (b"heic", b"heix", b"hevc", b"heim", b"heis", b"mif1", b"msf1", b"avif"):
        return "image/avif" if data[8:12] == b"avif" else "image/heic"
    m = (mime or "").split(";")[0].strip().lower()
    if m in IMAGEN_MIMES:
        return m
    ext = (nombre or "").lower().rsplit(".", 1)[-1]
    return {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp", "heic": "image/heic", "heif": "image/heif"}.get(ext, m)


def describir_foto(usuario: dict, sesion: dict, data: bytes, mime: str, nombre: str = "") -> dict:
    if not data or len(data) > IMAGEN_MAX_BYTES:
        raise ValueError("La imagen está vacía o pesa más de 8 MB.")
    m = _mime_imagen(data, mime, nombre)
    if m not in IMAGEN_MIMES:
        raise ValueError("Formato de imagen no soportado: usa una foto JPG, PNG, WEBP o HEIC (iPhone).")
    esc = sesion.get("escenario") or {}
    contexto = f"de la situación «{esc.get('titulo', 'práctica')}»: {esc.get('situacion', '')[:300]}"
    r = llm.generar(origen="foto.describir", system=P.FOTO_DESCRIBIR.format(contexto=contexto), contents=[{"role": "user", "text": "Describe la vestimenta de esta imagen.", "inline": [{"mime": m, "data": data}]}],
                    schema=E.FOTO, thinking="low", max_tokens=1500, temperatura=0.2, usuario_id=usuario["id"], sesion_id=sesion["id"])
    if not isinstance(r.json, dict):
        raise ErrorLLM("No se pudo analizar la imagen. Inténtalo de nuevo o describe tu outfit por texto.")
    return V.foto(r.json)


def texto_mensaje_audio(a: dict) -> str:
    return a["transcripcion"]


def texto_mensaje_foto(f: dict, comentario: str = "") -> str:
    base = "Te envío una foto de mi outfit." if f.get("es_outfit", True) else "Te envié una imagen."
    return (base + (" " + comentario.strip() if comentario.strip() else "")).strip()


def activo_audio() -> bool:
    return settings.AUDIO_ENABLED
