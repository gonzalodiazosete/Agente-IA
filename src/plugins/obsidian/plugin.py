import os
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from src.core.plugin_base import PluginBase


class ObsidianPlugin(PluginBase):
    """Plugin para leer y escribir notas Markdown en un Vault de Obsidian."""

    def __init__(self, vault_path: Optional[str] = None):
        self.vault_path = vault_path or os.getenv("OBSIDIAN_VAULT_PATH", "")

    @property
    def name(self) -> str:
        return "obsidian"

    @property
    def description(self) -> str:
        return "Lee, crea y edita notas Markdown en el vault de Obsidian del usuario."

    def create_note(self, title: str, content: str, folder: str = "") -> str:
        """
        Crea una nueva nota en el Vault de Obsidian.

        Args:
            title: Título de la nota (sin extensión .md).
            content: Contenido en formato Markdown.
            folder: Carpeta relativa dentro del vault (opcional).
        """
        if not self.vault_path or not os.path.exists(self.vault_path):
            return "Error: La ruta del Vault de Obsidian no está configurada o no existe."

        try:
            target_dir = os.path.join(self.vault_path, folder)
            os.makedirs(target_dir, exist_ok=True)
            
            filename = f"{title}.md"
            file_path = os.path.join(target_dir, filename)

            note_text = f"# {title}\n*Creada el {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n{content}"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(note_text)

            return f"Nota '{title}.md' creada exitosamente en {folder or 'raíz del vault'}."
        except Exception as e:
            return f"Error al crear la nota: {str(e)}"

    def read_note(self, title: str) -> str:
        """
        Lee el contenido de una nota de Obsidian por su nombre.

        Args:
            title: Título o nombre del archivo de la nota.
        """
        if not self.vault_path or not os.path.exists(self.vault_path):
            return "Error: La ruta del Vault de Obsidian no está configurada."

        title_clean = title if title.endswith(".md") else f"{title}.md"

        # Buscar en la raíz y subcarpetas
        for root, _, files in os.walk(self.vault_path):
            if title_clean in files:
                full_path = os.path.join(root, title_clean)
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        return f.read()[:2000]  # Limitar tamaño
                except Exception as e:
                    return f"Error leyendo archivo: {str(e)}"

        return f"Nota '{title}' no encontrada en el vault."

    def search_notes(self, query: str) -> str:
        """
        Busca notas en el vault que contengan una palabra o frase clave.

        Args:
            query: Texto a buscar.
        """
        if not self.vault_path or not os.path.exists(self.vault_path):
            return "Error: La ruta del Vault de Obsidian no está configurada."

        matches = []
        for root, _, files in os.walk(self.vault_path):
            for file in files:
                if file.endswith(".md"):
                    full_path = os.path.join(root, file)
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            if query.lower() in content.lower():
                                matches.append(file)
                    except Exception:
                        continue

        if matches:
            return f"Notas encontradas con '{query}':\n- " + "\n- ".join(matches[:10])
        return f"No se encontraron notas con el texto '{query}'."

    def get_tools(self) -> List[Dict[str, Any]]:
        return []

    def get_executors(self) -> Dict[str, Callable[..., Any]]:
        return {
            "create_obsidian_note": self.create_note,
            "read_obsidian_note": self.read_note,
            "search_obsidian_notes": self.search_notes
        }
