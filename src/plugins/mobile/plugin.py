import os
import requests
import subprocess
from typing import Any, Callable, Dict, List, Optional
from src.core.plugin_base import PluginBase


class MobilePlugin(PluginBase):
    """
    Plugin para comunicación con el dispositivo móvil Android.
    Soporta:
    1. Notificaciones Push gratuitas e inmediatas vía ntfy.sh (sin coste, app open-source de Android).
    2. Webhooks HTTP locales hacia Tasker / Automate / Join.
    3. Comandos directos por ADB si el dispositivo está conectado por USB/Wi-Fi.
    """

    def __init__(
        self,
        ntfy_topic: Optional[str] = None,
        tasker_url: Optional[str] = None
    ):
        self.ntfy_topic = ntfy_topic or os.getenv("MOBILE_NTFY_TOPIC", "zodi_gonzalo_alerts")
        self.tasker_url = tasker_url or os.getenv("TASKER_WEBHOOK_URL", "")

    @property
    def name(self) -> str:
        return "mobile"

    @property
    def description(self) -> str:
        return "Envía rutinas, notificaciones y órdenes de control al teléfono móvil Android."

    def send_mobile_notification(self, title: str, message: str, priority: str = "default") -> str:
        """
        Envía una notificación instantánea al teléfono móvil del usuario.

        Args:
            title: Título de la notificación.
            message: Contenido o cuerpo del mensaje.
            priority: Prioridad ('low', 'default', 'high', 'urgent').
        """
        # Método 1: ntfy.sh (gratuito, sin registro requerido)
        try:
            url = f"https://ntfy.sh/{self.ntfy_topic}"
            headers = {
                "Title": title.encode("utf-8").decode("latin-1", "ignore"),
                "Priority": priority
            }
            resp = requests.post(url, data=message.encode("utf-8"), headers=headers, timeout=5)
            if resp.status_code == 200:
                return f"Notificación '{title}' enviada con éxito al móvil."
        except Exception as e:
            print(f"[MobilePlugin] Error con ntfy: {e}")

        # Método 2: Webhook Tasker
        if self.tasker_url:
            try:
                payload = {"title": title, "message": message, "priority": priority}
                requests.post(self.tasker_url, json=payload, timeout=5)
                return f"Orden enviada a Tasker: {title}."
            except Exception as e:
                return f"Error enviando a Tasker: {e}"

        return "No se pudo enviar la notificación. Verifica la conexión o configura el tópico móvil."

    def send_gym_routine_to_phone(self, routine_name: str, exercises: str) -> str:
        """
        Envía la rutina de entrenamiento del gimnasio estructurada al teléfono móvil.

        Args:
            routine_name: Nombre de la rutina (ej: 'Empuje / Pecho y Hombro', 'Pierna').
            exercises: Lista detallada de ejercicios, series y repeticiones.
        """
        title = f"🏋️ Rutina del Día: {routine_name}"
        body = f"¡A entrenar, Gonzalo!\n\n{exercises}\n\nEnviado por Jarvis."
        return self.send_mobile_notification(title, body, priority="high")

    def adb_execute_action(self, action_type: str, param: str = "") -> str:
        """
        Ejecuta una acción directa en el móvil si está conectado por ADB (USB o Wi-Fi).

        Args:
            action_type: Tipo de acción ('open_app', 'keyevent', 'volume_up', 'volume_down').
            param: Parámetro adicional (ej: paquete de la app o código de tecla).
        """
        try:
            cmd = ["adb"]
            if action_type == "open_app":
                cmd.extend(["shell", "monkey", "-p", param, "-c", "android.intent.category.LAUNCHER", "1"])
            elif action_type == "volume_up":
                cmd.extend(["shell", "input", "keyevent", "24"])
            elif action_type == "volume_down":
                cmd.extend(["shell", "input", "keyevent", "25"])
            else:
                return f"Acción ADB no reconocida: {action_type}"

            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return f"Comando ADB '{action_type}' ejecutado correctamente en el teléfono."
            return f"ADB devolvió código {res.returncode}: {res.stderr}"
        except Exception as e:
            return f"Error ejecutando ADB (verifica si ADB está instalado y el móvil conectado): {str(e)}"

    def get_tools(self) -> List[Dict[str, Any]]:
        return []

    def get_executors(self) -> Dict[str, Callable[..., Any]]:
        return {
            "send_mobile_notification": self.send_mobile_notification,
            "send_gym_routine_to_phone": self.send_gym_routine_to_phone,
            "mobile_adb_action": self.adb_execute_action
        }
