import subprocess
import os
import ctypes
from typing import Any, Callable, Dict, List
from src.core.plugin_base import PluginBase


class PCControlPlugin(PluginBase):
    """Plugin para control de aplicaciones, volumen y comandos básicos en Windows."""

    @property
    def name(self) -> str:
        return "pc_control"

    @property
    def description(self) -> str:
        return "Controla aplicaciones, accesos directos, volumen y tareas del PC en Windows."

    def open_application(self, app_name: str) -> str:
        """
        Abre una aplicación de Windows por su nombre (ej: 'notepad', 'calc', 'chrome', 'spotify', 'code').

        Args:
            app_name: Nombre del ejecutable o aplicación a abrir.
        """
        try:
            # Intentar inicio con start
            subprocess.Popen(f"start {app_name}", shell=True)
            return f"Aplicación '{app_name}' iniciada correctamente."
        except Exception as e:
            return f"No se pudo abrir '{app_name}': {str(e)}"

    def set_volume_mute(self, mute: bool) -> str:
        """
        Silencia o activa el sonido del sistema en Windows.

        Args:
            mute: True para silenciar, False para activar sonido.
        """
        try:
            # Tecla virtual de Mute en Windows
            WM_APPCOMMAND = 0x0319
            APPCOMMAND_VOLUME_MUTE = 0x80000
            HWND_BROADCAST = 0xFFFF
            ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_APPCOMMAND, 0, APPCOMMAND_VOLUME_MUTE)
            status = "silenciado" if mute else "activado"
            return f"Sonido del sistema {status}."
        except Exception as e:
            return f"Error al cambiar volumen: {str(e)}"

    def execute_command(self, command: str) -> str:
        """
        Ejecuta un comando de PowerShell o CMD en el sistema (usar solo para tareas seguras).

        Args:
            command: Comando a ejecutar en la consola.
        """
        try:
            res = subprocess.run(["powershell", "-Command", command], capture_output=True, text=True, timeout=10)
            output = res.stdout if res.returncode == 0 else res.stderr
            return f"Resultado:\n{output[:500]}"
        except Exception as e:
            return f"Error ejecutando comando: {str(e)}"

    def get_tools(self) -> List[Dict[str, Any]]:
        return []

    def get_executors(self) -> Dict[str, Callable[..., Any]]:
        return {
            "open_application": self.open_application,
            "set_volume_mute": self.set_volume_mute,
            "execute_command": self.execute_command
        }
