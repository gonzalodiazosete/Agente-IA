import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QGroupBox, QFileDialog, QMessageBox
)
from src.core.memory_manager import MemoryManager


class SettingsDialog(QDialog):
    """Panel de configuración del asistente Zodi."""

    VOICES = ["Puck", "Charon", "Kore", "Fenrir", "Aoede"]

    def __init__(self, memory_manager: MemoryManager, parent=None):
        super().__init__(parent)
        self.memory_manager = memory_manager
        self.setWindowTitle("Ajustes de Zodi Jarvis")
        self.resize(450, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Grupo Asistente
        grp_assistant = QGroupBox("Personalización del Asistente")
        lay_assistant = QVBoxLayout()

        lay_assistant.addWidget(QLabel("Nombre del Asistente:"))
        self.txt_name = QLineEdit(self.memory_manager.get_assistant_name())
        lay_assistant.addWidget(self.txt_name)

        lay_assistant.addWidget(QLabel("Voz de Gemini:"))
        self.cmb_voice = QComboBox()
        self.cmb_voice.addItems(self.VOICES)
        current_voice = self.memory_manager.get_voice_name()
        if current_voice in self.VOICES:
            self.cmb_voice.setCurrentText(current_voice)
        lay_assistant.addWidget(self.cmb_voice)

        grp_assistant.setLayout(lay_assistant)
        layout.addWidget(grp_assistant)

        # Grupo Integraciones / Rutas
        grp_paths = QGroupBox("Integraciones y Rutas")
        lay_paths = QVBoxLayout()

        lay_paths.addWidget(QLabel("Ruta del Vault de Obsidian:"))
        h_obs = QHBoxLayout()
        self.txt_obsidian = QLineEdit(os.getenv("OBSIDIAN_VAULT_PATH", ""))
        btn_browse_obs = QPushButton("Examinar...")
        btn_browse_obs.clicked.connect(self.browse_obsidian)
        h_obs.addWidget(self.txt_obsidian)
        h_obs.addWidget(btn_browse_obs)
        lay_paths.addLayout(h_obs)

        grp_paths.setLayout(lay_paths)
        layout.addWidget(grp_paths)

        # Botones de guardar / cancelar
        h_buttons = QHBoxLayout()
        btn_save = QPushButton("Guardar")
        btn_save.clicked.connect(self.save_settings)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        
        h_buttons.addStretch()
        h_buttons.addWidget(btn_cancel)
        h_buttons.addWidget(btn_save)

        layout.addLayout(h_buttons)
        self.setLayout(layout)

    def browse_obsidian(self):
        directory = QFileDialog.getExistingDirectory(self, "Seleccionar Vault de Obsidian")
        if directory:
            self.txt_obsidian.setText(directory)

    def save_settings(self):
        new_name = self.txt_name.text().strip()
        new_voice = self.cmb_voice.currentText()
        obsidian_path = self.txt_obsidian.text().strip()

        if new_name:
            self.memory_manager.set_assistant_name(new_name)
        self.memory_manager.set_voice_name(new_voice)

        # Actualizar variable de entorno local para Obsidian
        os.environ["OBSIDIAN_VAULT_PATH"] = obsidian_path

        QMessageBox.information(self, "Ajustes", "Configuración guardada correctamente.")
        self.accept()
