import asyncio
import os
import traceback
from typing import Callable, Optional
from google import genai
from google.genai import types

from src.audio.playback import AudioPlayback
from src.core.memory_manager import MemoryManager
from src.core.plugin_manager import PluginManager


class GeminiLiveClient:
    """
    Cliente principal para Gemini Live API (Audio & Texto bidireccional en tiempo real).
    Maneja la sesión WebSocket streaming con Google GenAI SDK.
    """

    def __init__(
        self,
        memory_manager: MemoryManager,
        plugin_manager: PluginManager,
        playback: AudioPlayback,
        model_name: str = "gemini-3.8-live",
        api_key: Optional[str] = None
    ):
        self.memory_manager = memory_manager
        self.plugin_manager = plugin_manager
        self.playback = playback
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")

        self.genai_client: Optional[genai.Client] = None
        self.session: Optional[genai.live.AsyncSession] = None
        self.is_connected = False
        self._receive_task: Optional[asyncio.Task] = None

        # Callbacks para la UI
        self.on_text_received: Optional[Callable[[str, str], None]] = None  # (speaker, text)
        self.on_state_changed: Optional[Callable[[str], None]] = None        # "idle", "listening", "thinking", "speaking"
        self.on_error: Optional[Callable[[str], None]] = None

    def _set_state(self, state: str) -> None:
        if self.on_state_changed:
            self.on_state_changed(state)

    def _emit_text(self, speaker: str, text: str) -> None:
        if self.on_text_received:
            self.on_text_received(speaker, text)

    def _emit_error(self, error: str) -> None:
        if self.on_error:
            self.on_error(error)

    async def connect(self) -> bool:
        """Establece la conexión WebSocket con la Live API de Gemini."""
        if not self.api_key:
            self._emit_error("No se encontró la clave de API (GEMINI_API_KEY). Configúrala en el archivo .env")
            return False

        try:
            self.genai_client = genai.Client(api_key=self.api_key)
            voice_name = self.memory_manager.get_voice_name()
            system_instruction = self.memory_manager.build_system_instruction()
            tools = self.plugin_manager.get_gemini_tools()

            config = types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                    )
                ),
                system_instruction=types.Content(
                    parts=[types.Part.from_text(text=system_instruction)]
                ),
                tools=tools if tools else None
            )

            # Iniciar conexión WebSocket streaming
            session_cm = self.genai_client.aio.live.connect(
                model=self.model_name,
                config=config
            )
            self.session = await session_cm.__aenter__()
            self.is_connected = True
            self._set_state("idle")

            # Lanzar tarea de recepción continua en segundo plano
            self._receive_task = asyncio.create_task(self._listen_loop())
            return True

        except Exception as e:
            err = f"Error conectando a Gemini Live API: {str(e)}"
            self._emit_error(err)
            print(f"[GeminiLiveClient] {err}\n{traceback.format_exc()}")
            self.is_connected = False
            return False

    async def _listen_loop(self) -> None:
        """Bucle que escucha de forma continua las respuestas recibidas de Gemini."""
        if not self.session:
            return

        try:
            async for response in self.session.receive():
                server_content = response.server_content
                if server_content:
                    model_turn = server_content.model_turn
                    if model_turn and model_turn.parts:
                        for part in model_turn.parts:
                            # 1. Audio PCM recibido
                            if part.inline_data and part.inline_data.data:
                                pcm_bytes = part.inline_data.data
                                self._set_state("speaking")
                                self.playback.put_audio(pcm_bytes)

                            # 2. Texto o pensamientos del modelo
                            if part.text:
                                self._emit_text("Jarvis", part.text)

                    # Eventos de transcripción de voz si el servidor los envía
                    if server_content.input_transcription and server_content.input_transcription.text:
                        self._emit_text("Gonzalo (Voz)", server_content.input_transcription.text)

                    if server_content.turn_complete:
                        self._set_state("idle")

                # 3. Llamadas a herramientas / plugins (Function Calling)
                tool_call = response.tool_call
                if tool_call and tool_call.function_calls:
                    self._set_state("thinking")
                    for fc in tool_call.function_calls:
                        func_name = fc.name
                        func_args = fc.args or {}
                        call_id = fc.id

                        self._emit_text("Jarvis", f"*[Ejecutando herramienta: {func_name}...]*")
                        result = await self.plugin_manager.execute_tool_call(func_name, func_args)

                        # Responder a Gemini con el resultado de la función
                        if self.session:
                            await self.session.send_tool_response(
                                function_responses=[
                                    types.FunctionResponse(
                                        name=func_name,
                                        id=call_id,
                                        response={"result": result}
                                    )
                                ]
                            )

        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self.is_connected:
                err = f"Error en la sesión de Gemini Live: {str(e)}"
                print(f"[GeminiLiveClient] {err}\n{traceback.format_exc()}")
                self._emit_error(err)
        finally:
            self.is_connected = False
            self._set_state("idle")

    async def send_audio_chunk(self, pcm_bytes: bytes) -> None:
        """Envía un fragmento de audio PCM (16kHz 16bit) a Gemini."""
        if self.session and self.is_connected:
            try:
                await self.session.send_realtime_input(
                    audio=types.Blob(
                        data=pcm_bytes,
                        mime_type="audio/pcm;rate=16000"
                    )
                )
            except Exception as e:
                print(f"[GeminiLiveClient] Error enviando chunk de audio: {e}")

    async def send_text_message(self, text: str) -> None:
        """Envía un mensaje de texto escrito a Gemini."""
        if self.session and self.is_connected:
            try:
                self._set_state("thinking")
                await self.session.send_realtime_input(text=text)
            except Exception as e:
                err = f"Error enviando mensaje de texto: {str(e)}"
                self._emit_error(err)

    async def disconnect(self) -> None:
        """Cierra la sesión WebSocket limpiamente."""
        self.is_connected = False
        if self._receive_task:
            self._receive_task.cancel()
            self._receive_task = None

        if self.session:
            try:
                await self.session.close()
            except Exception:
                pass
            self.session = None
        self._set_state("idle")
