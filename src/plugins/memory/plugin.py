from typing import Any, Callable, Dict, List
from src.core.plugin_base import PluginBase
from src.core.memory_manager import MemoryManager


class MemoryPlugin(PluginBase):
    """
    Plugin que permite a Gemini interactuar directamente con la memoria persistente
    del usuario (guardar notas, rutinas, tareas pendientes y preferencias).
    """

    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager

    @property
    def name(self) -> str:
        return "memory"

    @property
    def description(self) -> str:
        return "Permite guardar, recordar y gestionar notas contextuales, tareas y entrenamientos del usuario."

    def remember_note(self, topic: str, fact: str) -> str:
        """
        Guarda una nota o recuerdo relevante sobre el usuario, sus gustos, rutinas o datos personales.

        Args:
            topic: Tema de la nota (ej: 'gym', 'preferencias', 'trabajo', 'familia', 'dieta').
            fact: El hecho o información específica a recordar.
        """
        self.memory_manager.add_contextual_note(topic, fact)
        return f"Recuerdo guardado con éxito sobre [{topic}]: '{fact}'."

    def add_todo_task(self, task: str) -> str:
        """
        Añade una nueva tarea u objetivo pendiente a la lista del usuario.

        Args:
            task: Descripción de la tarea pendiente.
        """
        self.memory_manager.add_task(task)
        return f"Tarea añadida a la lista de pendientes: '{task}'."

    def complete_todo_task(self, task_name: str) -> str:
        """
        Marca una tarea pendiente como completada.

        Args:
            task_name: Nombre o parte del texto de la tarea a completar.
        """
        success = self.memory_manager.complete_task(task_name)
        if success:
            return f"Tarea '{task_name}' marcada como completada."
        return f"No se encontró ninguna tarea pendiente que coincida con '{task_name}'."

    def log_workout(self, activity: str, details: str) -> str:
        """
        Registra un entrenamiento, ejercicio o actividad física del usuario.

        Args:
            activity: Tipo de entrenamiento (ej: 'Pecho y Tríceps', 'Correr 5km', 'Pierna').
            details: Detalles del entreno (ej: 'Series, pesos, sensaciones o duración').
        """
        self.memory_manager.add_fitness_log(activity, details)
        return f"Entrenamiento registrado: {activity} ({details})."

    def get_tools(self) -> List[Dict[str, Any]]:
        return []

    def get_executors(self) -> Dict[str, Callable[..., Any]]:
        return {
            "remember_note": self.remember_note,
            "add_todo_task": self.add_todo_task,
            "complete_todo_task": self.complete_todo_task,
            "log_workout": self.log_workout
        }
