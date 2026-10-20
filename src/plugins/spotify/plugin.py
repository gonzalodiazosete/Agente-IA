import os
from typing import Any, Callable, Dict, List, Optional
from src.core.plugin_base import PluginBase

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False


class SpotifyPlugin(PluginBase):
    """
    Plugin para controlar la reproducción de Spotify mediante Spotify Web API.
    Permite reproducir, pausar, cambiar de canción y buscar canciones/artistas.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None
    ):
        self.client_id = client_id or os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("SPOTIFY_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")
        
        self.sp: Optional[Any] = None
        self._init_spotify()

    def _init_spotify(self) -> bool:
        if not SPOTIPY_AVAILABLE or not self.client_id or not self.client_secret:
            return False

        try:
            scope = (
                "user-read-playback-state "
                "user-modify-playback-state "
                "user-read-currently-playing "
                "playlist-read-private"
            )
            auth_manager = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=scope,
                open_browser=False
            )
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            return True
        except Exception as e:
            print(f"[SpotifyPlugin] Error al autenticar: {e}")
            self.sp = None
            return False

    @property
    def name(self) -> str:
        return "spotify"

    @property
    def description(self) -> str:
        return "Controla Spotify: reproduce, pausa, salta canciones y busca música o playlists."

    def play_music(self, query: Optional[str] = None) -> str:
        """
        Reanuda la música o busca y reproduce una canción o artista.

        Args:
            query: Nombre de la canción, artista o playlist (opcional). Si se omite, reanuda la reproducción.
        """
        if not self.sp:
            return "Spotify no está configurado. Añade SPOTIFY_CLIENT_ID y SPOTIFY_CLIENT_SECRET en el archivo .env."

        try:
            if not query:
                self.sp.start_playback()
                return "Reproducción reanudada en Spotify."

            # Buscar track
            results = self.sp.search(q=query, limit=1, type="track")
            tracks = results.get("tracks", {}).get("items", [])
            if not tracks:
                return f"No encontré canciones para '{query}' en Spotify."

            track = tracks[0]
            track_uri = track["uri"]
            track_name = track["name"]
            artist_name = track["artists"][0]["name"]

            self.sp.start_playback(uris=[track_uri])
            return f"Reproduciendo '{track_name}' de {artist_name} en Spotify."
        except Exception as e:
            return f"Error en Spotify: {str(e)}"

    def pause_music(self) -> str:
        """Pausa la música en Spotify."""
        if not self.sp:
            return "Spotify no está configurado."
        try:
            self.sp.pause_playback()
            return "Música pausada en Spotify."
        except Exception as e:
            return f"Error al pausar Spotify: {str(e)}"

    def next_track(self) -> str:
        """Pasa a la siguiente canción en Spotify."""
        if not self.sp:
            return "Spotify no está configurado."
        try:
            self.sp.next_track()
            return "Saltando a la siguiente canción."
        except Exception as e:
            return f"Error al saltar de canción: {str(e)}"

    def previous_track(self) -> str:
        """Vuelve a la canción anterior en Spotify."""
        if not self.sp:
            return "Spotify no está configurado."
        try:
            self.sp.previous_track()
            return "Volviendo a la canción anterior."
        except Exception as e:
            return f"Error al retroceder canción: {str(e)}"

    def get_current_track(self) -> str:
        """Devuelve información de la canción que está sonando actualmente."""
        if not self.sp:
            return "Spotify no está configurado."
        try:
            current = self.sp.current_playback()
            if not current or not current.get("item"):
                return "No hay ninguna canción reproduciéndose actualmente."
            item = current["item"]
            title = item.get("name")
            artist = item.get("artists", [{}])[0].get("name", "Desconocido")
            is_playing = current.get("is_playing", False)
            state = "sonando" if is_playing else "en pausa"
            return f"Actualmente {state}: '{title}' de {artist}."
        except Exception as e:
            return f"Error consultando canción actual: {str(e)}"

    def get_tools(self) -> List[Dict[str, Any]]:
        return []

    def get_executors(self) -> Dict[str, Callable[..., Any]]:
        return {
            "spotify_play": self.play_music,
            "spotify_pause": self.pause_music,
            "spotify_next": self.next_track,
            "spotify_previous": self.previous_track,
            "spotify_current": self.get_current_track
        }
