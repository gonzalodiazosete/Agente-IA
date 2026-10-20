import importlib
import inspect
from typing import Any, Callable, Dict, List, Optional
from google.genai import types
from src.core.plugin_base import PluginBase


class PluginManager:
    """Administra la carga, activación y ejecución de plugins."""

    def __init__(self):
        self.plugins: Dict[str, PluginBase] = {}
        self.active_plugins: set[str] = set()
        self.executors: Dict[str, Callable[..., Any]] = {}

    def register_plugin(self, plugin: PluginBase) -> None:
        self.plugins[plugin.name] = plugin
        self.active_plugins.add(plugin.name)
        for func_name, func in plugin.get_executors().items():
            self.executors[func_name] = func

    def enable_plugin(self, name: str) -> bool:
        if name in self.plugins:
            self.active_plugins.add(name)
            return True
        return False

    def disable_plugin(self, name: str) -> bool:
        if name in self.active_plugins:
            self.active_plugins.remove(name)
            return True
        return False

    def get_gemini_tools(self) -> List[Any]:
        """
        Retorna las funciones de los plugins activos en el formato
        esperado por google-genai Client (o lista de funciones Python directamente).
        """
        active_tools = []
        for name in self.active_plugins:
            plugin = self.plugins.get(name)
            if plugin:
                # Cada ejecutor puede pasarse directamente si tiene type hints y docstring,
                # o pasamos las declaraciones dict.
                for func_name, executor in plugin.get_executors().items():
                    active_tools.append(executor)
        return active_tools

    async def execute_tool_call(self, name: str, args: Dict[str, Any]) -> Any:
        """Ejecuta una función solicitada por Gemini y devuelve el resultado."""
        if name not in self.executors:
            return {"error": f"Herramienta '{name}' no encontrada."}
        
        executor = self.executors[name]
        try:
            if inspect.iscoroutinefunction(executor):
                res = await executor(**args)
            else:
                res = executor(**args)
            return res
        except Exception as e:
            return {"error": f"Error al ejecutar '{name}': {str(e)}"}
