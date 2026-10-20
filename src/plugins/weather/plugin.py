import os
import requests
from typing import Any, Callable, Dict, List, Optional
from src.core.plugin_base import PluginBase


class WeatherPlugin(PluginBase):
    """Plugin para consultar el clima usando OpenWeatherMap o fallback público."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENWEATHER_API_KEY", "")

    @property
    def name(self) -> str:
        return "weather"

    @property
    def description(self) -> str:
        return "Consulta información meteorológica en tiempo real de cualquier ciudad."

    def get_weather(self, city: str = "Madrid") -> str:
        """
        Obtiene el clima actual para una ciudad especificada.

        Args:
            city: Nombre de la ciudad (ej: 'Madrid', 'Barcelona', 'Mexico City').
        """
        if self.api_key:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={self.api_key}&units=metric&lang=es"
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    temp = data["main"]["temp"]
                    feels = data["main"]["feels_like"]
                    desc = data["weather"][0]["description"]
                    humidity = data["main"]["humidity"]
                    return f"El clima en {city} es {desc}. Temperatura actual: {temp}°C (sensación térmica {feels}°C). Humedad: {humidity}%."
                else:
                    return f"No se pudo obtener el clima para {city} (código {resp.status_code})."
            except Exception as e:
                return f"Error conectando a OpenWeatherMap: {str(e)}"
        
        # Fallback gratuito vía wttr.in
        try:
            url = f"https://wttr.in/{city}?format=3&lang=es"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                return f"Clima en {resp.text.strip()}"
        except Exception:
            pass

        return f"Información del clima para {city} no disponible actualmente."

    def get_tools(self) -> List[Dict[str, Any]]:
        return []

    def get_executors(self) -> Dict[str, Callable[..., Any]]:
        return {
            "get_weather": self.get_weather
        }
