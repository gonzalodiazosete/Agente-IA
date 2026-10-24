import hashlib
import os
import time
from io import BytesIO
from typing import Any, Callable, Dict, List, Optional

from google import genai
from google.genai import types
from PIL import Image, ImageOps

from src.core.plugin_base import PluginBase


# ---------------------------------------------------------------------------
# La imagen se envía dentro de la misma sesión Live cuando el usuario la
# adjunta (ver src/ui/main_window.py), así que esta llamada REST es el camino
# de respaldo: releer la imagen, sacar un texto pequeño, pedir una segunda
# opinión. Aun así se prepara igual que la rápida, porque cada byte y cada
# segundo que se ahorra aquí también se ahorra allí.
# ---------------------------------------------------------------------------

# Lado máximo al que se reduce la imagen. Gemini trocea las imágenes grandes y
# una captura 4K viaja como varios MB sin aportar nada: se paga subida y se
# paga espera. 1280 px es lo mismo que usaba Zodi antes, pero en JPEG.
MAX_IMAGE_SIDE = 1280
JPEG_QUALITY = 85

# Medido contra esta clave con una captura de 1280x720:
#   gemini-3.1-flash-lite    1.1 - 1.7 s
#   gemini-3.6-flash         1.8 - 2.1 s
#   gemini-3.5-flash-lite    1.8 - 6.3 s
#   gemini-3.8-flash         504 DEADLINE_EXCEEDED a los ~28 s, siempre
# gemini-2.5-flash y gemini-2.5-flash-lite no están disponibles para esta
# clave (404), así que no entran en la cadena. El orden es medido, no supuesto.
DEFAULT_MODEL = "gemini-3.1-flash-lite"
FALLBACK_MODELS = (
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
)

# La API rechaza cualquier deadline por debajo de 10 s. Analizar una imagen
# tarda más que clasificar una frase, así que el margen es mayor.
DEFAULT_TIMEOUT_MS = 30_000
MIN_TIMEOUT_MS = 10_000

# Un modelo que agota cuota, desaparece o deja de responder no debe costar una
# vuelta en cada llamada: se aparta un rato y la cadena sigue con el siguiente.
_COOLDOWN_SECONDS = 5 * 60
_GONE_SECONDS = 6 * 60 * 60
_UNAVAILABLE_SECONDS = 30 * 60


def _is_quota_error(err: str) -> bool:
    return "429" in err or "RESOURCE_EXHAUSTED" in err


def _is_gone_error(err: str) -> bool:
    low = err.lower()
    return ("404" in err or "not found" in low or "is not supported" in low
            or "permission" in low or "403" in err)


def _is_unavailable_error(err: str) -> bool:
    low = err.lower()
    return ("503" in err or "504" in err
            or "unavailable" in low or "deadline_exceeded" in low)


class VisionPlugin(PluginBase):
    """
    Plugin que permite a Zodi ver imágenes adjuntas.

    La imagen se envía en la misma sesión Live al adjuntarla, de modo que el
    modelo la ve sin gastar una llamada extra. La herramienta analyze_image
    queda para volver a mirarla o pedir un análisis independiente, y usa un
    cliente reutilizado, una cadena de modelos y compresión JPEG en vez de
    crear un cliente y subir un PNG en cada llamada.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ):
        self.api_key = api_key
        self.model_name = (
            model_name or os.getenv("VISION_MODEL", "") or DEFAULT_MODEL
        ).strip()
        self.timeout_ms = max(MIN_TIMEOUT_MS, int(timeout_ms))

        self._image_bytes: Optional[bytes] = None
        self._image_mime_type: Optional[str] = None
        self._image_digest: str = ""

        self._client: Optional[genai.Client] = None
        self._cooldown: Dict[str, float] = {}

        # Última respuesta, para que dos llamadas idénticas sobre la misma
        # imagen no cuesten dos peticiones.
        self._cache_key: Optional[tuple] = None
        self._cache_value: str = ""

    @property
    def name(self) -> str:
        return "vision"

    @property
    def description(self) -> str:
        return "Permite a Zodi ver y analizar la última imagen adjuntada por el usuario."

    # ------------------------------------------------------------------
    # Imagen
    # ------------------------------------------------------------------

    def prepare_image(
        self, image_bytes: bytes, mime_type: Optional[str] = None
    ) -> tuple[bytes, str]:
        """
        Reduce la imagen y la reencoda en JPEG antes de enviarla al modelo.

        Un PNG de 1280 px puede pesar varios cientos de KB; el mismo contenido
        en JPEG q85 ronda las decenas, y el modelo ve exactamente lo mismo.
        Si el reencodado no sale más pequeño (capturas planas, imágenes
        diminutas), se conserva el original.
        """
        source_mime = mime_type or "image/jpeg"
        try:
            with Image.open(BytesIO(image_bytes)) as img:
                img.load()
                # Las fotos traen la orientación en EXIF; sin esto el modelo
                # recibe la imagen girada.
                img = ImageOps.exif_transpose(img)

                # JPEG no lleva transparencia: se aplana sobre blanco.
                if img.mode in ("RGBA", "LA", "P"):
                    rgba = img.convert("RGBA")
                    fondo = Image.new("RGB", rgba.size, (255, 255, 255))
                    fondo.paste(rgba, mask=rgba.split()[-1])
                    img = fondo
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                ancho, alto = img.size
                lado = max(ancho, alto)
                if lado > MAX_IMAGE_SIDE:
                    escala = MAX_IMAGE_SIDE / lado
                    img = img.resize(
                        (max(1, round(ancho * escala)), max(1, round(alto * escala))),
                        Image.Resampling.BILINEAR,
                    )

                buffer = BytesIO()
                img.save(
                    buffer, format="JPEG", quality=JPEG_QUALITY, optimize=False
                )
                data = buffer.getvalue()
        except Exception as e:
            print(f"[Vision] No se pudo recomprimir la imagen: {e}")
            return image_bytes, source_mime

        if len(data) >= len(image_bytes):
            return image_bytes, source_mime
        return data, "image/jpeg"

    def set_last_image(
        self, image_bytes: bytes, mime_type: Optional[str] = None
    ) -> tuple[bytes, str]:
        """
        Guarda la última imagen para analyze_image y devuelve la versión ya
        preparada, que es la que debe viajar al modelo.
        """
        data, mime = self.prepare_image(image_bytes, mime_type)
        self._image_bytes = data
        self._image_mime_type = mime
        self._image_digest = hashlib.sha1(data).hexdigest()
        self._cache_key = None
        self._cache_value = ""
        return data, mime

    # ------------------------------------------------------------------
    # Cliente y modelos
    # ------------------------------------------------------------------

    def _models(self) -> tuple[str, ...]:
        """El modelo elegido primero, y detrás los que responden si falla."""
        return (self.model_name,) + tuple(
            m for m in FALLBACK_MODELS if m != self.model_name
        )

    def _get_client(self) -> genai.Client:
        """
        Un único cliente para toda la sesión.

        Crear un genai.Client por llamada (lo que hacía antes este plugin)
        repite la inicialización del transporte y deja cada petición sin
        deadline. El cliente se construye una vez, se reutiliza y lleva
        api_version y timeout fijados.
        """
        if self._client is None:
            key = self.api_key or os.getenv("GEMINI_API_KEY", "")
            if not key:
                raise RuntimeError(
                    "No se encontró la clave GEMINI_API_KEY para analizar la imagen."
                )
            # La REST estándar vive en v1beta; v1alpha solo hace falta para
            # las funciones Live experimentales, que aquí no se usan.
            self._client = genai.Client(
                api_key=key,
                http_options=types.HttpOptions(
                    api_version="v1beta", timeout=self.timeout_ms
                ),
            )
        return self._client

    def _cooling(self, model: str) -> bool:
        until = self._cooldown.get(model, 0.0)
        if until and time.monotonic() < until:
            return True
        self._cooldown.pop(model, None)
        return False

    def _note_failure(self, model: str, error: str) -> None:
        if _is_quota_error(error):
            self._cooldown[model] = time.monotonic() + _COOLDOWN_SECONDS
            print(f"[Vision] {model}: sin cuota, se aparta 5 minutos")
        elif _is_gone_error(error):
            self._cooldown[model] = time.monotonic() + _GONE_SECONDS
            print(f"[Vision] {model}: no disponible para esta clave, se aparta")
        elif _is_unavailable_error(error):
            self._cooldown[model] = time.monotonic() + _UNAVAILABLE_SECONDS
            print(f"[Vision] {model}: no responde, se aparta 30 minutos")

    # ------------------------------------------------------------------
    # Herramienta
    # ------------------------------------------------------------------

    async def analyze_image(self, question: str) -> str:
        """
        Vuelve a mirar la última imagen adjunta y responde a la pregunta.

        Úsala solo para una segunda lectura de la imagen (por ejemplo, releer
        un texto pequeño): cuando el usuario adjunta una imagen, esta viaja ya
        dentro del mismo mensaje y puedes verla sin llamar a ninguna
        herramienta.

        Args:
            question: Pregunta o instrucción sobre la imagen (ej: '¿Qué se ve en la imagen?').
        """
        if not self._image_bytes:
            return "No hay ninguna imagen adjuntada."

        prompt = (question or "").strip()
        if not prompt:
            prompt = "Describe detalladamente lo que se ve en esta imagen."

        cache_key = (self._image_digest, prompt)
        if self._cache_key == cache_key and self._cache_value:
            return self._cache_value

        models = self._models()
        # Si todos están en descanso se intenta igualmente: negarse a responder
        # nunca es mejor que probar.
        tried = [m for m in models if not self._cooling(m)] or list(models)

        last_error = "no se intentó ningún modelo"
        for model in tried:
            try:
                client = self._get_client()
                response = await client.aio.models.generate_content(
                    model=model,
                    contents=[
                        types.Part.from_bytes(
                            data=self._image_bytes,
                            mime_type=self._image_mime_type or "image/jpeg",
                        ),
                        prompt,
                    ],
                )
                texto = (response.text or "").strip()
                if not texto:
                    raise RuntimeError("la respuesta vino vacía")
                self._cache_key, self._cache_value = cache_key, texto
                return texto
            except Exception as e:
                last_error = str(e)
                self._note_failure(model, last_error)
                print(f"[Vision] {model}: {type(e).__name__}: {last_error[:140]}")

        return f"No se pudo analizar la imagen: {last_error[:300]}"

    async def close(self) -> None:
        """Cierra el cliente HTTP reutilizado."""
        client, self._client = self._client, None
        if client is not None:
            try:
                await client.aio.aclose()
            except Exception:
                pass

    def get_tools(self) -> List[Dict[str, Any]]:
        return []

    def get_executors(self) -> Dict[str, Callable[..., Any]]:
        return {
            "analyze_image": self.analyze_image
        }
