import os
import base64
from typing import Any, Callable, Dict, List, Optional
from src.core.plugin_base import PluginBase

try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False


class GoogleWorkspacePlugin(PluginBase):
    """
    Plugin para interactuar con Gmail y Google Calendar.
    Permite consultar emails no leídos, resumir correos y ver/crear eventos de Google Calendar.
    """

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/calendar.events"
    ]

    def __init__(self, token_path: str = "config/google_token.json"):
        self.token_path = token_path
        self.creds: Optional[Credentials] = None
        self._load_credentials()

    def _load_credentials(self) -> None:
        if not GOOGLE_LIBS_AVAILABLE:
            return
        if os.path.exists(self.token_path):
            try:
                self.creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
            except Exception as e:
                print(f"[GoogleWorkspace] Error cargando credenciales: {e}")
                self.creds = None

    @property
    def name(self) -> str:
        return "google_workspace"

    @property
    def description(self) -> str:
        return "Consulta correos recientes de Gmail y gestiona eventos en Google Calendar."

    def get_recent_emails(self, max_results: int = 5) -> str:
        """
        Consulta los correos más recientes en la bandeja de entrada de Gmail.

        Args:
            max_results: Número de correos a consultar (por defecto 5).
        """
        if not self.creds or not self.creds.valid:
            return "Gmail no está conectado. Añade 'config/google_token.json' con permisos OAuth de Google."

        try:
            service = build("gmail", "v1", credentials=self.creds)
            results = service.users().messages().list(userId="me", maxResults=max_results, q="label:INBOX").execute()
            messages = results.get("messages", [])

            if not messages:
                return "No tienes correos recientes en la bandeja de entrada."

            summaries = []
            for msg_meta in messages:
                msg = service.users().messages().get(userId="me", id=msg_meta["id"], format="metadata").execute()
                headers = msg.get("payload", {}).get("headers", [])
                subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "(Sin asunto)")
                sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "Desconocido")
                snippet = msg.get("snippet", "")
                summaries.append(f"• De: {sender}\n  Asunto: {subject}\n  Detalle: {snippet[:120]}...")

            return "Correos recientes en Gmail:\n\n" + "\n\n".join(summaries)
        except Exception as e:
            return f"Error consultando Gmail: {str(e)}"

    def get_upcoming_calendar_events(self, max_events: int = 5) -> str:
        """
        Obtiene los próximos eventos programados en Google Calendar.

        Args:
            max_events: Cantidad máxima de eventos a listar.
        """
        if not self.creds or not self.creds.valid:
            return "Google Calendar no está conectado. Añade 'config/google_token.json' con permisos OAuth."

        try:
            import datetime
            service = build("calendar", "v3", credentials=self.creds)
            now = datetime.datetime.utcnow().isoformat() + "Z"

            events_result = service.events().list(
                calendarId="primary",
                timeMin=now,
                maxResults=max_events,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            events = events_result.get("items", [])

            if not events:
                return "No tienes eventos próximos programados en tu calendario."

            lines = []
            for ev in events:
                start = ev.get("start", {}).get("dateTime", ev.get("start", {}).get("date"))
                summary = ev.get("summary", "(Sin título)")
                lines.append(f"• {start}: {summary}")

            return "Próximos eventos en tu Google Calendar:\n" + "\n".join(lines)
        except Exception as e:
            return f"Error consultando Google Calendar: {str(e)}"

    def create_calendar_event(self, summary: str, start_time_iso: str, duration_minutes: int = 60) -> str:
        """
        Crea un nuevo evento en Google Calendar.

        Args:
            summary: Título o descripción del evento.
            start_time_iso: Fecha y hora de inicio en formato ISO (ej: '2026-10-19T18:00:00').
            duration_minutes: Duración en minutos (por defecto 60).
        """
        if not self.creds or not self.creds.valid:
            return "Google Calendar no está conectado."

        try:
            import datetime
            service = build("calendar", "v3", credentials=self.creds)
            start_dt = datetime.datetime.fromisoformat(start_time_iso)
            end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)

            event = {
                "summary": summary,
                "start": {"dateTime": start_dt.isoformat(), "timeZone": "Europe/Madrid"},
                "end": {"dateTime": end_dt.isoformat(), "timeZone": "Europe/Madrid"}
            }

            created_event = service.events().insert(calendarId="primary", body=event).execute()
            link = created_event.get("htmlLink", "")
            return f"Evento '{summary}' creado para el {start_time_iso}. Enlace: {link}"
        except Exception as e:
            return f"Error creando evento en Calendar: {str(e)}"

    def get_tools(self) -> List[Dict[str, Any]]:
        return []

    def get_executors(self) -> Dict[str, Callable[..., Any]]:
        return {
            "gmail_recent_emails": self.get_recent_emails,
            "calendar_upcoming_events": self.get_upcoming_calendar_events,
            "calendar_create_event": self.create_calendar_event
        }
