import json, os, subprocess
from pathlib import Path

DATA_DIR = Path(os.environ.get("APPDATA", str(Path.home() / ".yavis"))) / "YAVIS"
CONFIG_FILE = DATA_DIR / "config.json"
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)   # Hilfsprogramme ohne Konsolenfenster starten

DEFAULTS = {
    # Lokales Modell (Ollama). Schwächerer PC: "llama3.2:3b" eintragen.
    "model": "qwen2.5:7b",
    "ollama_url": "http://127.0.0.1:11434",
    "temperature": 0.8,               # höher = lebendiger, menschlicher
    # Zuhören
    "whisper_model": "small",         # tiny / base / small / medium (größer = genauer, langsamer)
    "language": "de",
    "mic_device": None,               # None = Standard-Mikrofon
    "silence_seconds": 1.0,           # Pause, ab der ein Satz als beendet gilt
    "min_energy": 0.008,              # Untergrenze der automatischen Lautstärke-Schwelle
    "wake_words": ["yavis", "jarvis", "javis", "yarvis", "jawis", "yavies", "yavi"],
    "wake_fuzzy": 0.78,               # Toleranz bei Aktivierungswörtern (0.6 locker … 1.0 exakt)
    # Sprechen
    "voice": "ramona",                # siehe voice.VOICES
    "voice_speed": 1.0,               # >1 = langsamer
    "speech_rate": 170,               # nur für Windows-Notfallstimme
    "speak": True,                    # Antworten vorlesen
    "show_text": False,               # Standard: nur Sprache, keine Textausgabe
    "neutral_mode": False,            # True = YAVIS zeigt keine Gefühle
    # Hintergrundmusik
    "music_volume": 0.35,             # 0 = aus … 1 = voll
    "music_autoplay": True,           # beim Start automatisch abspielen
    "music_duck": True,               # leiser, während YAVIS spricht oder zuhört
    "music_seeded": False,            # mitgelieferte Lieder schon kopiert?
    "allowed_apps": {
        "editor": "notepad", "notepad": "notepad", "rechner": "calc",
        "explorer": "explorer", "dateien": "explorer",
        "edge": "start msedge", "browser": "start msedge",
        "chrome": "start chrome", "paint": "mspaint",
        "einstellungen": "start ms-settings:", "eingabeaufforderung": "start cmd",
    },
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
