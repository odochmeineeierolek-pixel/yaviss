import json, os
from pathlib import Path

DATA_DIR = Path(os.environ.get("APPDATA", str(Path.home() / ".yavis"))) / "YAVIS"
CONFIG_FILE = DATA_DIR / "config.json"

DEFAULTS = {
    # Lokales Modell (Ollama). Kleinere PCs: "llama3.2:3b" eintragen.
    "model": "qwen2.5:7b",
    "ollama_url": "http://127.0.0.1:11434",
    "whisper_model": "base",          # tiny / base / small (small = genauer, langsamer)
    "language": "de",
    "wake_words": ["yavis", "jarvis", "javis", "yarvis", "jawis", "yavies", "yavi"],
    "silence_seconds": 0.8,
    "energy_threshold": 0.015,
    "speech_rate": 170,          # nur für Windows-Notfallstimme
    "voice_engine": "piper",     # piper (lokal) | edge (online, sehr natürlich) | sapi (Windows, roboterhaft)
    "piper_voice": "ramona",     # ramona | kerstin | eva_k
    "edge_voice": "de-DE-KatjaNeural",
    "voice_speed": 1.0,          # >1 = langsamer
    "allowed_apps": {
        "editor": "notepad", "notepad": "notepad", "rechner": "calc",
        "explorer": "explorer", "dateien": "explorer",
        "edge": "start msedge", "browser": "start msedge",
        "chrome": "start chrome", "paint": "mspaint",
        "einstellungen": "start ms-settings:", "eingabeaufforderung": "start cmd",
    },
    "speak": True,        # Antworten vorlesen
    "show_text": True,    # Antworten im Fenster anzeigen
    "search_roots": ["~/Documents", "~/Desktop", "~/Downloads"],
}


def load() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cfg = json.loads(json.dumps(DEFAULTS))
    if CONFIG_FILE.exists():
        try:
            cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    else:
        CONFIG_FILE.write_text(json.dumps(DEFAULTS, indent=2, ensure_ascii=False), encoding="utf-8")
    return cfg


def save(cfg: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
