import sys
import os
import asyncio
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication
from qasync import QEventLoop

# Cargar variables de entorno desde .env si existe
load_dotenv()

from src.core.memory_manager import MemoryManager
from src.core.plugin_manager import PluginManager
from src.audio.capture import AudioCapture
from src.audio.playback import AudioPlayback
from src.core.gemini_live import GeminiLiveClient
from src.plugins.pc_control.plugin import PCControlPlugin
from src.plugins.obsidian.plugin import ObsidianPlugin
from src.plugins.weather.plugin import WeatherPlugin
from src.plugins.memory.plugin import MemoryPlugin
from src.plugins.spotify.plugin import SpotifyPlugin
from src.plugins.google_workspace.plugin import GoogleWorkspacePlugin
from src.plugins.mobile.plugin import MobilePlugin
from src.ui.main_window import MainWindow


async def main():
    # 1. Inicializar componentes del sistema
    memory_manager = MemoryManager("data/memory.json")
    plugin_manager = PluginManager()

    # Registrar plugins modulares
    plugin_manager.register_plugin(MemoryPlugin(memory_manager))
    plugin_manager.register_plugin(PCControlPlugin())
    plugin_manager.register_plugin(ObsidianPlugin())
    plugin_manager.register_plugin(WeatherPlugin())
    plugin_manager.register_plugin(SpotifyPlugin())
    plugin_manager.register_plugin(GoogleWorkspacePlugin())
    plugin_manager.register_plugin(MobilePlugin())

    # Inicializar audio
    audio_capture = AudioCapture()
    audio_playback = AudioPlayback()

    # Obtener bucle actual de qasync
    loop = asyncio.get_running_loop()

    # Cliente Gemini Live API
    gemini_client = GeminiLiveClient(
        memory_manager=memory_manager,
        plugin_manager=plugin_manager,
        playback=audio_playback,
        model_name="gemini-3.8-live"
    )

    # El callback de captura corre en el hilo de PortAudio, así que el envío se
    # agenda en el bucle de asyncio en lugar de usar una tarea intermedia.
    def on_audio_captured(pcm_bytes: bytes) -> None:
        if not gemini_client.is_connected or loop.is_closed():
            return
        try:
            asyncio.run_coroutine_threadsafe(
                gemini_client.send_audio_chunk(pcm_bytes), loop
            )
        except RuntimeError:
            pass  # El bucle se cerró entre la comprobación y el envío

    audio_capture.on_audio_data = on_audio_captured

    # Iniciar captura y reproducción de audio en segundo plano
    audio_capture.start()
    audio_playback.start()

    # Conectar WebSocket con Gemini Live API
    asyncio.create_task(gemini_client.connect())

    # 2. Inicializar Interfaz PyQt6
    window = MainWindow(
        memory_manager=memory_manager,
        plugin_manager=plugin_manager,
        audio_capture=audio_capture,
        audio_playback=audio_playback,
        gemini_client=gemini_client
    )

    # Cargar hoja de estilos QSS si existe
    qss_path = "src/ui/styles.qss"
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            window.setStyleSheet(f.read())

    window.show()

    # Mantener el bucle activo mientras la aplicación esté abierta
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    event_loop = QEventLoop(app)
    asyncio.set_event_loop(event_loop)

    with event_loop:
        try:
            event_loop.run_until_complete(main())
        except KeyboardInterrupt:
            pass
