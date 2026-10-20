import asyncio
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLineEdit, QPushButton, QLabel, QFileDialog, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from src.core.memory_manager import MemoryManager
from src.core.plugin_manager import PluginManager
from src.audio.capture import AudioCapture
from src.audio.playback import AudioPlayback
from src.core.gemini_live import GeminiLiveClient
from src.ui.settings_dialog import SettingsDialog
from src.ui.system_tray import SystemTrayManager


class UISignals(QObject):
    """Señales de PyQt6 para actualización segura desde tareas asíncronas."""
    text_received = pyqtSignal(str, str)   # (speaker, message)
    state_changed = pyqtSignal(str)        # state string
    error_occurred = pyqtSignal(str)       # error message


class MainWindow(QMainWindow):
    """Ventana Principal de la app de escritorio Zodi."""

    def __init__(
        self,
        memory_manager: MemoryManager,
        plugin_manager: PluginManager,
        audio_capture: AudioCapture,
        audio_playback: AudioPlayback,
        gemini_client: GeminiLiveClient
    ):
        super().__init__()
        self.memory_manager = memory_manager
        self.plugin_manager = plugin_manager
        self.audio_capture = audio_capture
        self.audio_playback = audio_playback
        self.gemini_client = gemini_client

        self.signals = UISignals()
        self.setup_signals()

        self.setWindowTitle(f"{self.memory_manager.get_assistant_name()} — Asistente IA")
        self.resize(700, 600)
        self.setAcceptDrops(True)

        self.init_ui()
        self.system_tray = SystemTrayManager(self, on_toggle_pause=self.on_game_mode_toggle)

    def setup_signals(self):
        self.signals.text_received.connect(self.append_chat_message)
        self.signals.state_changed.connect(self.update_status)
        self.signals.error_occurred.connect(self.show_error)

        # Vincular callbacks del cliente Gemini
        self.gemini_client.on_text_received = lambda spk, txt: self.signals.text_received.emit(spk, txt)
        self.gemini_client.on_state_changed = lambda st: self.signals.state_changed.emit(st)
        self.gemini_client.on_error = lambda err: self.signals.error_occurred.emit(err)

        # Vincular cambio de estado de reproducción de audio
        self.audio_playback.on_playback_state_change = lambda playing: (
            self.signals.state_changed.emit("speaking" if playing else "idle")
        )

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Barra superior (Título + Estado + Ajustes)
        top_layout = QHBoxLayout()
        
        self.lbl_title = QLabel(f"⚡ {self.memory_manager.get_assistant_name()}")
        self.lbl_title.setObjectName("titleLabel")

        self.lbl_status = QLabel("● Desconectado")
        self.lbl_status.setObjectName("statusLabel")

        btn_settings = QPushButton("⚙ Ajustes")
        btn_settings.clicked.connect(self.open_settings)

        top_layout.addWidget(self.lbl_title)
        top_layout.addStretch()
        top_layout.addWidget(self.lbl_status)
        top_layout.addWidget(btn_settings)

        main_layout.addLayout(top_layout)

        # Área de Chat
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        main_layout.addWidget(self.chat_display, stretch=1)

        # Zona Drop / Adjuntos
        self.attachment_frame = QFrame()
        self.attachment_frame.setStyleSheet("""
            QFrame {
                border: 1px dashed #3b82f6;
                border-radius: 6px;
                background-color: #121526;
                padding: 4px;
            }
        """)
        lay_att = QHBoxLayout(self.attachment_frame)
        lay_att.setContentsMargins(10, 4, 10, 4)
        
        self.lbl_attachment = QLabel("📎 Arrastra un archivo o documento aquí...")
        self.lbl_attachment.setStyleSheet("color: #64748b; font-size: 11px;")
        
        btn_attach = QPushButton("Adjuntar")
        btn_attach.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        btn_attach.clicked.connect(self.browse_file)

        lay_att.addWidget(self.lbl_attachment)
        lay_att.addStretch()
        lay_att.addWidget(btn_attach)

        main_layout.addWidget(self.attachment_frame)

        # Barra inferior de controles (Toggle Mic + Input Texto + Enviar)
        bottom_layout = QHBoxLayout()

        self.btn_mic = QPushButton("🎤 Mic: OFF")
        self.btn_mic.setObjectName("micButtonMuted")
        self.btn_mic.setCheckable(True)
        self.btn_mic.clicked.connect(self.toggle_microphone)

        self.txt_input = QLineEdit()
        self.txt_input.setPlaceholderText("Escribe un mensaje o habla directamente...")
        self.txt_input.returnPressed.connect(self.send_text_message)

        btn_send = QPushButton("Enviar")
        btn_send.clicked.connect(self.send_text_message)

        bottom_layout.addWidget(self.btn_mic)
        bottom_layout.addWidget(self.txt_input, stretch=1)
        bottom_layout.addWidget(btn_send)

        main_layout.addLayout(bottom_layout)
        central_widget.setLayout(main_layout)

    def update_status(self, state: str):
        states = {
            "idle": ("● En reposo", "color: #10b981; background-color: #064e3b;"),
            "listening": ("🎤 Escuchando...", "color: #ef4444; background-color: #7f1d1d;"),
            "thinking": ("🧠 Pensando...", "color: #f59e0b; background-color: #78350f;"),
            "speaking": ("🔊 Hablando...", "color: #3b82f6; background-color: #1e3a8a;"),
            "disconnected": ("● Desconectado", "color: #94a3b8; background-color: #1e293b;")
        }
        text, style = states.get(state, ("● " + state, "color: #94a3b8; background-color: #1e293b;"))
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet(f"font-weight: bold; font-size: 12px; padding: 4px 10px; border-radius: 12px; {style}")

    def append_chat_message(self, speaker: str, text: str):
        color = "#60a5fa" if "Jarvis" in speaker else "#34d399"
        if "Voz" in speaker:
            color = "#f472b6"
        html = f"<div style='margin-bottom: 8px;'><b style='color: {color};'>{speaker}:</b> {text}</div>"
        self.chat_display.append(html)

    def show_error(self, message: str):
        self.append_chat_message("Sistema (Error)", f"<span style='color: #ef4444;'>{message}</span>")

    def toggle_microphone(self):
        is_muted = self.audio_capture.toggle_mute()
        if not is_muted:
            self.btn_mic.setText("🎤 Mic: ON")
            self.btn_mic.setObjectName("micButtonActive")
            self.btn_mic.setStyle(self.btn_mic.style())
            self.update_status("listening")
        else:
            self.btn_mic.setText("🎤 Mic: OFF")
            self.btn_mic.setObjectName("micButtonMuted")
            self.btn_mic.setStyle(self.btn_mic.style())
            self.update_status("idle")

    def send_text_message(self):
        text = self.txt_input.text().strip()
        if not text:
            return

        self.append_chat_message(self.memory_manager.get_user_name(), text)
        self.txt_input.clear()

        # Enviar mensaje de forma asíncrona a Gemini
        asyncio.create_task(self.gemini_client.send_text_message(text))

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo para Zodi")
        if file_path:
            self.handle_file_selected(file_path)

    def handle_file_selected(self, file_path: str):
        file_name = os.path.basename(file_path)
        self.lbl_attachment.setText(f"📄 Adjunto: {file_name}")
        self.append_chat_message("Sistema", f"Archivo adjuntado: <b>{file_name}</b> ({file_path})")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.exists(file_path):
                self.handle_file_selected(file_path)

    def open_settings(self):
        dialog = SettingsDialog(self.memory_manager, self)
        if dialog.exec():
            # Actualizar título si cambió el nombre
            new_name = self.memory_manager.get_assistant_name()
            self.setWindowTitle(f"{new_name} — Asistente IA")
            self.lbl_title.setText(f"⚡ {new_name}")

    def on_game_mode_toggle(self, is_paused: bool):
        if is_paused:
            self.audio_capture.set_muted(True)
            self.btn_mic.setChecked(False)
            self.btn_mic.setText("🎤 Mic: OFF (Pausado)")
            self.btn_mic.setObjectName("micButtonMuted")
            self.btn_mic.setStyle(self.btn_mic.style())
            self.update_status("disconnected")
        else:
            self.btn_mic.setText("🎤 Mic: OFF")
            self.update_status("idle")

    def closeEvent(self, event):
        # Ocultar a la bandeja en vez de cerrar la app al darle a la X
        if self.system_tray.tray.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()
