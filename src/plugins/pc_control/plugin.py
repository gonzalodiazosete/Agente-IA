import subprocess
import os
import ctypes
import webbrowser
import urllib.parse
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

    def open_url(self, url: str) -> str:
        """
        Abre una URL en el navegador predeterminado.

        Args:
            url: Dirección web o URL a abrir (ej: 'https://www.google.com').
        """
        try:
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"
            webbrowser.open(url)
            return f"URL '{url}' abierta en el navegador."
        except Exception as e:
            return f"No se pudo abrir la URL '{url}': {str(e)}"

    def search_google(self, query: str) -> str:
        """
        Construye la URL de búsqueda de Google y la abre en el navegador predeterminado.

        Args:
            query: Texto o consulta a buscar en Google.
        """
        try:
            encoded_query = urllib.parse.quote(query)
            search_url = f"https://www.google.com/search?q={encoded_query}"
            webbrowser.open(search_url)
            return f"Búsqueda de '{query}' abierta en Google."
        except Exception as e:
            return f"No se pudo realizar la búsqueda de '{query}': {str(e)}"

    def get_tools(self) -> List[Dict[str, Any]]:
        return []

    def get_executors(self) -> Dict[str, Callable[..., Any]]:
        return {
            "open_application": self.open_application,
            "set_volume_mute": self.set_volume_mute,
            "execute_command": self.execute_command,
            "open_url": self.open_url,
            "search_google": self.search_google,
        }
