from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List


class PluginBase(ABC):
    """Clase base abstracta para todos los plugins de Zodi."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre único del plugin (ej. 'pc_control', 'weather')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Descripción del plugin."""
        pass

    @abstractmethod
    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Retorna la lista de declaraciones de herramientas (functions)
        en formato dict compatible con Gemini API / OpenAPI Schema.
        """
        pass

    @abstractmethod
    def get_executors(self) -> Dict[str, Callable[..., Any]]:
        """
        Retorna un diccionario maopeando el nombre de la función a su invocable Python.
        Ej: {"open_application": self.open_app}
        """
        pass
