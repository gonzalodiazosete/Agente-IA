from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter


def create_tray_icon_pixmap(color_hex: str = "#3b82f6") -> QIcon:
    """Genera un icono circular de color para la bandeja del sistema."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(color_hex))
    painter.setPen(QColor("#ffffff"))
    painter.drawEllipse(2, 2, 28, 28)
    painter.end()
    return QIcon(pixmap)


class SystemTrayManager:
    """Maneja el icono en la bandeja de sistema de Windows."""

    def __init__(self, main_window, on_toggle_pause=None):
        self.main_window = main_window
        self.on_toggle_pause = on_toggle_pause

        self.tray = QSystemTrayIcon(create_tray_icon_pixmap("#3b82f6"), main_window)
        self.tray.setToolTip("Zodi - Asistente Personal IA")

        menu = QMenu()
        
        act_show = menu.addAction("Mostrar Zodi")
        act_show.triggered.connect(self.show_window)

        self.act_pause = menu.addAction("Pausar Asistente (Modo Juego)")
        self.act_pause.triggered.connect(self.toggle_pause)

        menu.addSeparator()

        act_exit = menu.addAction("Salir")
        act_exit.triggered.connect(QApplication.instance().quit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

        self.is_paused = False

    def show_window(self):
        self.main_window.show()
        self.main_window.activateWindow()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.main_window.isVisible():
                self.main_window.hide()
            else:
                self.show_window()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.act_pause.setText("Reanudar Asistente")
            self.tray.setIcon(create_tray_icon_pixmap("#ef4444"))
            self.tray.showMessage("Zodi Pausado", "El asistente ha sido pausado para liberar recursos.", QSystemTrayIcon.IconInformation, 2000)
        else:
            self.act_pause.setText("Pausar Asistente (Modo Juego)")
            self.tray.setIcon(create_tray_icon_pixmap("#3b82f6"))
            self.tray.showMessage("Zodi Reanudado", "El asistente está activo.", QSystemTrayIcon.IconInformation, 2000)

        if self.on_toggle_pause:
            self.on_toggle_pause(self.is_paused)
