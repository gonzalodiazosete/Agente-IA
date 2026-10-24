# Zodi — Asistente Personal IA (Jarvis Windows)

## Arquitectura del Proyecto

Zodi es un asistente personal de escritorio tipo Jarvis para Windows que utiliza la **Gemini Live API** para conversación fluida y bidireccional por voz y texto en tiempo real.

```
Zodi/
├── config/
│   └── settings.json            # Configuración general (nombre, voz, audio, plugins)
├── data/
│   └── memory.json              # Base de recuerdos persistentes tipada y estructurada
├── src/
│   ├── core/
│   │   ├── gemini_live.py       # Cliente Gemini Live API (WebSocket / Async Session)
│   │   ├── memory_manager.py    # Gestión de memoria persistente en disco
│   │   ├── plugin_base.py       # Clase base e interfaz para plugins
│   │   └── plugin_manager.py    # Carga dinámica y ejecución de herramientas (Function Calling)
│   ├── audio/
│   │   ├── capture.py           # Captura de micrófono (16kHz PCM 16-bit)
│   │   └── playback.py          # Reproducción de audio (24kHz PCM 16-bit)
│   ├── plugins/
│   │   ├── pc_control/          # Control de apps, volumen y comandos Windows
│   │   ├── obsidian/            # Vault de notas Markdown
│   │   ├── weather/             # Clima vía OpenWeatherMap / wttr.in
│   │   ├── memory/              # Guardar y consultar recuerdos y tareas
│   │   ├── spotify/             # Control de Spotify Web API
│   │   ├── google_workspace/    # Gmail & Google Calendar API
│   │   ├── vision/              # Imágenes adjuntas (sesión Live + analyze_image)
│   │   └── mobile/              # Notificaciones push y control Android (ntfy / Tasker / ADB)
│   └── ui/
│       ├── main_window.py       # Ventana principal PyQt6 (Chat, Mic Toggle, Drag&Drop)
│       ├── settings_dialog.py   # Diálogo de ajustes (Voz, Nombre, Vaults)
│       ├── system_tray.py       # Icono de la bandeja del sistema (Modo Juego)
│       └── styles.qss           # Estilos CSS oscuros
├── requirements.txt
├── .env.example
├── main.py                      # Punto de entrada (qasync + PyQt6)
└── AGENT.md                     # Documentación de arquitectura para desarrolladores
```

---

## Módulos y Plugins Implementados

### 1. Núcleo (`src/core/`)
- **`MemoryManager`**: Mantiene la memoria del usuario estructurada en `data/memory.json` (perfil, fitness/gimnasio, tareas pendientes, notas contextuales y preferencias). Inyecta contexto dinámicamente en el prompt del sistema.
- **`GeminiLiveClient`**: Gestiona la sesión WebSocket continua con `google-genai`, recibe fragmentos de audio PCM 24kHz y maneja el *Tool Calling* asíncrono.
- **`PluginManager`**: Registra las herramientas expuestas por cada plugin y las ejecuta cuando Gemini envía llamadas a funciones.

### 2. Audio (`src/audio/`)
- **`AudioCapture`**: Graba desde el micrófono predeterminado a 16kHz int16 mono. Controlado por el botón de activación (Mic Toggle).
- **`AudioPlayback`**: Buffer FIFO en tiempo real a 24kHz int16 mono con soporte para interrupción instantánea cuando el usuario habla.

### 3. Plugins Disponibles (`src/plugins/`)
- `memory`: Guardar recuerdos, añadir/completar tareas pendientes y registrar entrenamientos.
- `pc_control`: Abrir ejecutables de Windows, silenciar el sistema o ejecutar comandos seguros en PowerShell.
- `obsidian`: Crear, leer y buscar notas Markdown en el Vault de Obsidian.
- `weather`: Clima actual por ciudad con OpenWeatherMap o fallback a wttr.in.
- `spotify`: Reproducir, pausar, cambiar canciones e identificar temas sonando mediante Spotipy.
- `google_workspace`: Consultar correos de Gmail y consultar/crear eventos en Google Calendar.
- `mobile`: Enviar notificaciones instantáneas al móvil vía ntfy.sh (app gratuita para Android), webhook a Tasker o comandos ADB directos.
- `vision`: Adjuntar imágenes a la conversación.

### 4. Visión (`src/plugins/vision/`)
La imagen adjuntada se reduce a 1280 px de lado máximo y se reencoda en JPEG
(calidad 85) antes de salir del plugin: una captura de 12 MB llega a la API
como ~600 KB. Después viaja **dentro de la misma sesión Live**, en el mismo
turno que el aviso, así que el modelo la ve y responde en una sola vuelta, sin
un segundo cliente ni un segundo modelo. La herramienta `analyze_image` queda
como segunda lectura y usa un cliente reutilizado con `api_version="v1beta"` y
timeout explícito, una cadena de modelos con descanso por cuota/errores y una
caché de la última respuesta. Modelo por defecto: `gemini-3.1-flash-lite`
(medido; `gemini-3.8-flash` devuelve 504 a los ~28 s con esta clave), se puede
cambiar con la variable `VISION_MODEL`.

---

## Instrucciones para Ejecución Local

1. **Crear y activar el entorno virtual:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar variables de entorno (`.env`):**
   Copia el archivo `.env.example` a `.env` y añade tu clave de Gemini API:
   ```env
   GEMINI_API_KEY=tu_clave_de_gemini
   ```

4. **Ejecutar el asistente:**
   ```bash
   python main.py
   ```
