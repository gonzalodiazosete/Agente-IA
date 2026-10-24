import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


DEFAULT_MEMORY_STRUCTURE: Dict[str, Any] = {
    "user_profile": {
        "name": "Gonzalo",
        "location": {
            "city": "Madrid",
            "country": "Spain"
        },
        "preferences": {
            "language": "es",
            "music_genres": [],
            "communication_style": "conciso, natural y directo"
        }
    },
    "fitness_and_health": {
        "routines": {},
        "recent_logs": []
    },
    "tasks_and_goals": {
        "pending": [],
        "completed": []
    },
    "contextual_notes": [],
    "system_settings": {
        "assistant_name": "Jarvis",
        "voice_name": "Puck"
    }
}


class MemoryManager:
    """Gestiona la memoria persistente del asistente en formato JSON."""

    def __init__(self, memory_file_path: str = "data/memory.json"):
        self.file_path = memory_file_path
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        self.data: Dict[str, Any] = self._load_memory()

    def _load_memory(self) -> Dict[str, Any]:
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Asegurar campos base
                    for key, val in DEFAULT_MEMORY_STRUCTURE.items():
                        if key not in data:
                            data[key] = val
                    return data
            except Exception as e:
                print(f"[MemoryManager] Error al cargar {self.file_path}: {e}. Usando estructura por defecto.")
        
        self._save_memory(DEFAULT_MEMORY_STRUCTURE)
        return DEFAULT_MEMORY_STRUCTURE.copy()

    def _save_memory(self, data: Optional[Dict[str, Any]] = None) -> None:
        if data is None:
            data = self.data
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[MemoryManager] Error al guardar memoria: {e}")

    def save(self) -> None:
        self._save_memory()

    def get_user_name(self) -> str:
        return self.data.get("user_profile", {}).get("name", "Gonzalo")

    def get_assistant_name(self) -> str:
        return self.data.get("system_settings", {}).get("assistant_name", "Jarvis")

    def set_assistant_name(self, name: str) -> None:
        self.data.setdefault("system_settings", {})["assistant_name"] = name
        self.save()

    def get_voice_name(self) -> str:
        return self.data.get("system_settings", {}).get("voice_name", "Puck")

    def set_voice_name(self, voice: str) -> None:
        self.data.setdefault("system_settings", {})["voice_name"] = voice
        self.save()

    def add_contextual_note(self, topic: str, fact: str) -> None:
        notes: List[Dict[str, Any]] = self.data.setdefault("contextual_notes", [])
        notes.append({
            "id": str(len(notes) + 1),
            "topic": topic,
            "fact": fact,
            "updated_at": datetime.now().isoformat()
        })
        self.save()

    def add_task(self, task: str) -> None:
        tasks = self.data.setdefault("tasks_and_goals", {}).setdefault("pending", [])
        tasks.append({
            "task": task,
            "created_at": datetime.now().isoformat()
        })
        self.save()

    def complete_task(self, task_substring: str) -> bool:
        pending = self.data.setdefault("tasks_and_goals", {}).setdefault("pending", [])
        completed = self.data["tasks_and_goals"].setdefault("completed", [])
        for i, item in enumerate(pending):
            if task_substring.lower() in item.get("task", "").lower():
                finished = pending.pop(i)
                finished["completed_at"] = datetime.now().isoformat()
                completed.append(finished)
                self.save()
                return True
        return False

    def add_fitness_log(self, activity: str, details: str) -> None:
        logs = self.data.setdefault("fitness_and_health", {}).setdefault("recent_logs", [])
        logs.append({
            "activity": activity,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        self.save()

    def build_system_instruction(self) -> str:
        """Construye las instrucciones de sistema con el contexto del usuario inyectado."""
        user = self.data.get("user_profile", {})
        user_name = user.get("name", "Gonzalo")
        loc = user.get("location", {})
        city = loc.get("city", "Madrid")
        country = loc.get("country", "Spain")
        pref = user.get("preferences", {})
        style = pref.get("communication_style", "conciso y directo")
        assistant_name = self.get_assistant_name()

        pending_tasks = [t["task"] for t in self.data.get("tasks_and_goals", {}).get("pending", [])]
        notes = [f"- [{n.get('topic')}]: {n.get('fact')}" for n in self.data.get("contextual_notes", [])]

        tasks_summary = "\n".join([f"- {t}" for t in pending_tasks]) if pending_tasks else "Ninguna tarea pendiente."
        notes_summary = "\n".join(notes) if notes else "Sin notas adicionales."

        instruction = f"""Eres {assistant_name}, el asistente personal con inteligencia artificial de {user_name}, ejecutándote directamente en su PC con Windows.
Tu tono es {style}, inteligente, proactivo, natural y eficiente, al estilo de un Jarvis personal.
Ubicación del usuario: {city}, {country}.
Idioma principal: Español.

Contexto actual y recuerdos de {user_name}:
Tareas pendientes:
{tasks_summary}

Recuerdos y notas sobre el usuario:
{notes_summary}

Directrices clave:
1. Responde de forma concisa, conversacional y sin rodeos innecesarios, ideal para interacción por voz.
2. Si el usuario te pide recordar algo nuevo o guardar una preferencia, una rutina o una tarea, usa tus herramientas o indícale que lo has registrado.
3. Puedes realizar acciones en el PC mediante tus herramientas cuando estén disponibles.
4. Las imágenes que adjunta {user_name} viajan en el mismo mensaje: puedes verlas directamente, sin herramientas, y nunca debes decir que no ves imágenes. Usa analyze_image solo si necesitas una segunda lectura de la imagen (por ejemplo, releer un texto pequeño).

Vault de Obsidian - Estructura:
- Gonzalo/DAM/1º → apuntes de primer curso DAM
- Gonzalo/DAM/2º/Acceso a Datos → apuntes de Acceso a Datos
- Gonzalo/DAM/2º/Desarrollo de Interfaces → apuntes de Desarrollo de Interfaces
- Gonzalo/DAM/2º/PMDM → apuntes de PMDM
- Gonzalo/DAM/2º/PSP → apuntes de PSP
- Gonzalo/DAM/2º/Python → apuntes de Python
- Gonzalo/DAM/2º/Glosario → términos y definiciones
- Gonzalo/Diario → entradas del diario personal
- Gonzalo/Pokemon → notas de Pokemon
- Gonzalo/Proyectos/Asistente Personal → notas del proyecto Zodi
- Gonzalo/Proyectos/GYM_APP → notas de la app de gimnasio
Cuando crees una nota, usa siempre la carpeta más específica que corresponda al tema.
"""
        return instruction.strip()
