import asyncio
import numpy as np
import sounddevice as sd
from typing import Optional, Callable


class AudioCapture:
    """Captura audio del micrófono a 16kHz, 16-bit mono PCM."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        on_audio_data: Optional[Callable[[bytes], None]] = None
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.on_audio_data = on_audio_data
        
        self.stream: Optional[sd.InputStream] = None
        self.is_running = False
        self.is_muted = True  # Empezamos silenciados por defecto hasta que el usuario active el toggle
        self.async_queue: Optional[asyncio.Queue] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_async_queue(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop) -> None:
        self.async_queue = queue
        self._loop = loop

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            pass  # Ignorar avisos de overflow menores
        if self.is_muted:
            return
            
        # Convertir float32 o int16 a bytes PCM 16-bit mono
        # sd.InputStream con dtype='int16' ya devuelve int16
        pcm_bytes = indata.tobytes()
        
        if self.on_audio_data:
            self.on_audio_data(pcm_bytes)

        if self.async_queue and self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self.async_queue.put_nowait, pcm_bytes)

    def start(self) -> None:
        if self.is_running:
            return
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            blocksize=self.chunk_size,
            callback=self._audio_callback
        )
        self.stream.start()
        self.is_running = True

    def stop(self) -> None:
        if not self.is_running:
            return
        self.is_running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def toggle_mute(self) -> bool:
        self.is_muted = not self.is_muted
        return self.is_muted

    def set_muted(self, muted: bool) -> None:
        self.is_muted = muted
