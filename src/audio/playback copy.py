import queue
import threading
import sounddevice as sd
from typing import Optional, Callable


class AudioPlayback:
    """Reproduce audio recibido (24kHz, 16-bit mono PCM) de forma fluida y sin bloqueos."""

    def __init__(
        self,
        sample_rate: int = 24000,
        channels: int = 1,
        on_playback_state_change: Optional[Callable[[bool], None]] = None
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.on_playback_state_change = on_playback_state_change
        
        self.audio_queue: queue.Queue = queue.Queue()
        self.stream: Optional[sd.RawOutputStream] = None
        self.is_running = False
        self._is_playing = False

    def _audio_callback(self, outdata, frames, time_info, status):
        # Cada frame es de 2 bytes (16-bit mono)
        bytes_needed = frames * self.channels * 2
        collected = bytearray()
        
        while len(collected) < bytes_needed:
            try:
                chunk = self.audio_queue.get_nowait()
                collected.extend(chunk)
            except queue.Empty:
                break

        if len(collected) < bytes_needed:
            # Rellenar con silencio
            silence_len = bytes_needed - len(collected)
            collected.extend(b"\x00" * silence_len)
            if self._is_playing and self.audio_queue.empty():
                self._is_playing = False
                if self.on_playback_state_change:
                    self.on_playback_state_change(False)
        else:
            if not self._is_playing:
                self._is_playing = True
                if self.on_playback_state_change:
                    self.on_playback_state_change(True)

        outdata[:bytes_needed] = bytes(collected[:bytes_needed])

    def start(self) -> None:
        if self.is_running:
            return
        self.stream = sd.RawOutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            callback=self._audio_callback
        )
        self.stream.start()
        self.is_running = True

    def put_audio(self, pcm_bytes: bytes) -> None:
        if not self.is_running:
            self.start()
        self.audio_queue.put(pcm_bytes)

    def stop(self) -> None:
        self.clear()
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.is_running = False
        self._is_playing = False

    def clear(self) -> None:
        """Limpia el buffer de audio inmediatamente (interrupción de voz)."""
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        self._is_playing = False
        if self.on_playback_state_change:
            self.on_playback_state_change(False)

    def is_playing(self) -> bool:
        return self._is_playing
