import asyncio
import mimetypes
import os
import pypdf
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLineEdit, QPushButton, QLabel, QFileDialog, QFrame
)
from PyQt6.QtCore import Qt, QBuffer, QEvent, QIODevice, pyqtSignal, QObject
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from src.core.memory_manager import MemoryManager
from src.core.plugin_manager import PluginManager
from src.audio.capture import AudioCapture
from src.audio.playback import AudioPlayback
from src.core.gemini_live import GeminiLiveClient
from src.ui.settings_dialog import SettingsDialog
from src.ui.system_tray import SystemTrayManager


# Extensiones que se interpretan siempre como texto plano.
TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".py", ".json", ".csv", ".tsv", ".log",
    ".xml", ".html", ".htm", ".css", ".js", ".jsx", ".ts", ".tsx",
    ".yaml", ".yml", ".ini", ".cfg", ".conf", ".toml", ".sql", ".sh",
    ".bash", ".bat", ".ps1", ".java", ".c", ".h", ".cpp", ".hpp", ".cs",
    ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".kts", ".r", ".tex",
    ".env", ".gitignore", ".dockerfile",
}

# Extensiones de imagen que se adjuntan a la sesión Live.
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

# Tipos MIME que, sin empezar por "text/", también son texto.
TEXT_MIME_TYPES = {
    "application/json",
    "application/xml",
    "application/javascript",
    "application/x-javascript",
    "application/x-yaml",
    "application/yaml",
    "application/x-sh",
    "application/sql",
}


def is_text_file(file_path: str) -> bool:
    """Determina si un archivo debe leerse como texto según su extensión/MIME."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in TEXT_EXTENSIONS:
        return True

    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type and (mime_type.startswith("text/") or mime_type in TEXT_MIME_TYPES):
        return True

    return False


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

        # Capturar Ctrl+V en toda la ventana para poder pegar imágenes.
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

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

    def attach_image(
        self,
        file_name: str,
        image_bytes: bytes,
        mime_type: str,
        source: str = ""
    ) -> None:
        """Adjunta una imagen a la sesión Live y la guarda para analyze_image."""
        vision_plugin = self.plugin_manager.plugins.get("vision")
        if vision_plugin is None:
            self.show_error("El plugin de visión no está disponible.")
            return

        # El plugin reduce la imagen y la reencoda en JPEG (1280 px de lado
        # máximo). Es la misma versión que se guarda y la que viaja al modelo,
        # así que solo se procesa una vez.
        image_bytes, mime_type = vision_plugin.set_last_image(
            image_bytes, mime_type
        )

        self.lbl_attachment.setText(f"📄 Adjunto: {file_name}")

        detail = f" ({source})" if source else ""
        self.append_chat_message(
            "Sistema", f"Imagen adjuntada: <b>{file_name}</b>{detail}"
        )
        self.append_chat_message(
            self.memory_manager.get_user_name(), f"📎 {file_name}"
        )
        # La imagen va en el mismo mensaje que el aviso: el modelo la ve al
        # instante, sin una segunda llamada a la API ni un segundo modelo.
        asyncio.ensure_future(
            self.gemini_client.send_text_message(
                f"[Imagen adjunta: {file_name}{detail}]\n"
                "La imagen viaja en este mismo mensaje. Mírala y describe o "
                "responde lo que corresponda. No hace falta llamar a "
                "analyze_image salvo que necesites una segunda lectura.",
                image_data=image_bytes,
                mime_type=mime_type,
            )
        )

    def eventFilter(self, obj, event):
        if (
            event.type() == QEvent.Type.KeyPress
            and event.key() == Qt.Key.Key_V
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
            and self.isActiveWindow()
        ):
            if self.paste_clipboard_image():
                return True
        return super().eventFilter(obj, event)

    def paste_clipboard_image(self) -> bool:
        """Pega una imagen del portapapeles si la hay. Devuelve True si la consumió."""
        image = QApplication.clipboard().image()
        if image.isNull():
            return False

        buffer = QBuffer()
        if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
            return False

        try:
            if not image.save(buffer, "PNG"):
                return False
            image_bytes = bytes(buffer.data())
        finally:
            buffer.close()

        self.attach_image(
            "imagen_portapapeles.png",
            image_bytes,
            "image/png",
            "pegada desde el portapapeles",
        )
        return True

    def handle_file_selected(self, file_path: str):
        file_name = os.path.basename(file_path)
        self.lbl_attachment.setText(f"📄 Adjunto: {file_name}")

        ext = os.path.splitext(file_path)[1].lower()
        image_data = None
        image_mime_type = None

        try:
            if ext in IMAGE_EXTENSIONS:
                # La imagen se adjunta a la sesión Live en el mismo mensaje,
                # así que el modelo la ve sin llamar a ninguna herramienta.
                with open(file_path, "rb") as f:
                    image_data = f.read()
                image_mime_type = (
                    mimetypes.guess_type(file_path)[0] or "image/jpeg"
                )
            elif ext == ".pdf":
                try:
                    reader = pypdf.PdfReader(file_path)
                    content = "\n".join(
                        (page.extract_text() or "") for page in reader.pages
                    )
                except Exception as e:
                    self.show_error(f"No se pudo leer el PDF {file_name}: {e}")
                    return
            elif is_text_file(file_path):
                with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
                    content = f.read()
            else:
                # Archivos sin extensión conocida: intentar decodificar como UTF-8.
                with open(file_path, "rb") as f:
                    raw_data = f.read()
                try:
                    content = raw_data.decode("utf-8-sig")
                except UnicodeDecodeError:
                    self.show_error(f"Tipo de archivo no soportado: {file_name}")
                    return
        except OSError as e:
            self.show_error(f"No se pudo leer el archivo {file_name}: {e}")
            return

        if image_data is not None:
            self.attach_image(file_name, image_data, image_mime_type, file_path)
            return

        self.append_chat_message(
            "Sistema", f"Archivo adjuntado: <b>{file_name}</b> ({file_path})"
        )
        self.append_chat_message(
            self.memory_manager.get_user_name(), f"📎 {file_name}"
        )

        message = f"[Archivo adjunto: {file_name}]\n\nContenido:\n{content}"
        asyncio.ensure_future(
            self.gemini_client.send_text_message(message)
        )

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
