# Zodi ⚡

**Zodi** es un asistente de escritorio por voz para Windows, construido en Python sobre la **Gemini Live API**. Conversación natural en tiempo real, interrupciones fluidas, memoria persistente, gestión de ficheros, integración con Obsidian, búsqueda web y análisis de imágenes.

---

## ✨ Características

### 🎙️ Conversación por voz en tiempo real
- Audio bidireccional con Gemini Live API (16 kHz entrada / 24 kHz salida).
- **Barge-in**: puedes interrumpir a Zodi mientras habla y responderá a tu nueva petición.
- Detección automática de actividad de voz (VAD) ajustada para no cortarte mientras piensas.
- Chat por texto además de voz.

### 🧠 Memoria persistente
- Recuerda datos entre sesiones almacenados en `data/memory.json`.
- Configuración de nombre del asistente y voz desde la interfaz de ajustes.

### 📁 Gestión de ficheros
- Crear, leer, editar, borrar y mover archivos por voz o texto.
- Creación de archivos Markdown.
- Adjuntar archivos de texto (`.txt`, `.md`, `.py`, `.json`, `.csv`…) y **PDF** (extracción de texto con `pypdf`).

### 🖼️ Visión
- Adjunta imágenes con el botón **Adjuntar**, arrastrándolas a la ventana o pegándolas con **Ctrl+V** (capturas de `Win+Shift+S` incluidas).
- Las imágenes se comprimen automáticamente (lado máximo 1280 px, JPEG) para un análisis rápido.
- La imagen viaja en la propia sesión Live, sin llamadas REST adicionales.

### 📓 Integración con Obsidian
- Crear, leer y buscar notas dentro de tu vault.
- Conoce la estructura del vault mediante el system prompt, para guardar cada nota en la carpeta correcta.

### 🌐 Herramientas
- **Clima** (OpenWeatherMap / wttr.in).
- **Búsqueda en Google** y apertura de URLs en el navegador.
- **Control del PC**: abrir aplicaciones, volumen y comandos básicos de Windows.
- **Google Workspace** (Gmail y Calendar) — en desarrollo.
- **Spotify** — solo lectura (requiere Premium para controlar la reproducción).

---

## 🏗️ Arquitectura

```
src/
├── core/          # Cliente Gemini Live, gestor de memoria, gestor de plugins
├── audio/         # Captura de micrófono (PyAudio) y reproducción
├── plugins/       # Un plugin por dominio (pc_control, obsidian, weather, vision…)
└── ui/            # Ventana principal PyQt6, ajustes y bandeja del sistema
```

Cada funcionalidad es un **plugin** que expone sus herramientas (*function calling*) al modelo. Añadir una nueva capacidad consiste en crear un plugin y registrarlo en `main.py`.

---

## 🚀 Instalación

### Requisitos
- Windows 10/11
- Python 3.13
- Micrófono y auriculares (recomendado)
- Clave de API de Gemini

### Pasos

```bash
git clone https://github.com/<tu-usuario>/Zodi.git
cd Zodi

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
```

Crea un archivo `.env` a partir de `.env.example`:

```dotenv
GEMINI_API_KEY=tu_clave
OBSIDIAN_VAULT_PATH="C:/ruta/a/tu/vault"
OPENWEATHER_API_KEY=opcional
```

Ejecuta la aplicación:

```bash
python main.py
```

> ⚠️ Si instalas dependencias nuevas, hazlo siempre con `.venv\Scripts\pip install ...` para que queden en el entorno del proyecto.

---

## ⚙️ Configuración

Desde el botón **Ajustes** en la ventana puedes cambiar:
- Nombre del asistente
- Voz de Gemini
- Ruta del vault de Obsidian

---

## 🗺️ Roadmap

**v1.0.0 (actual)**
- Voz en tiempo real con barge-in
- Memoria, ficheros, PDF, imágenes, Obsidian, búsqueda web

**v2.0 (planificado)**
- Nueva interfaz con Electron + React
- Control de Spotify (requiere Premium)
- Posible modo IA local como alternativa a Gemini

---

## ⚠️ Limitaciones conocidas
- Requiere conexión a internet y cuota de la API de Gemini.
- Spotify en modo solo lectura sin cuenta Premium.
- Solo probado en Windows.

---
