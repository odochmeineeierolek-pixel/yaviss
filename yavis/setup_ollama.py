"""Ersteinrichtung: Ollama installieren, Modell und Whisper-Modell laden (einmalig, braucht Internet)."""
import json, os, shutil, subprocess, time, threading


def _alive(url):
    import requests
    try:
        return requests.get(url + "/api/tags", timeout=3).ok
    except Exception:
        return False


def _find_ollama():
    p = shutil.which("ollama")
    if p:
        return p
    cand = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
    return cand if os.path.exists(cand) else None


def ensure_ollama(cfg, log=print):
    import requests
    url = cfg["ollama_url"]
    if not _alive(url):
        exe = _find_ollama()
        if not exe:
            log("Installiere Ollama (kostenlos, MIT-Lizenz) ...")
            try:
                subprocess.run(["winget", "install", "-e", "--id", "Ollama.Ollama", "--silent",
                                "--accept-source-agreements", "--accept-package-agreements"],
                               check=False, creationflags=0x08000000)
            except FileNotFoundError:
                pass
            exe = _find_ollama()
        if not exe:
            log("winget nicht verfügbar – lade Ollama-Installer direkt ...")
            from . import config, voice
            p = config.DATA_DIR / "OllamaSetup.exe"
            voice._download("https://ollama.com/download/OllamaSetup.exe", p, log)
            subprocess.run([str(p), "/SILENT"], check=False, creationflags=0x08000000)
            exe = _find_ollama()
        if not exe:
            raise RuntimeError("Ollama konnte nicht installiert werden. Bitte von https://ollama.com/download installieren.")
        log("Starte Ollama ...")
        subprocess.Popen([exe, "serve"], creationflags=0x08000000)  # CREATE_NO_WINDOW
        for _ in range(30):
            if _alive(url):
                break
            time.sleep(1)
        else:
            raise RuntimeError("Ollama startet nicht.")
    tags = requests.get(url + "/api/tags", timeout=10).json().get("models", [])
    if not any(m["name"].startswith(cfg["model"]) for m in tags):
        log(f"Lade KI-Modell {cfg['model']} (einige GB, einmalig) ...")
        with requests.post(url + "/api/pull", json={"model": cfg["model"], "stream": True}, stream=True) as r:
            last = ""
            for line in r.iter_lines():
                if not line:
                    continue
                d = json.loads(line)
                s = d.get("status", "")
                if d.get("total"):
                    s += f" {int(100 * d.get('completed', 0) / d['total'])}%"
                if s != last:
                    log(s)
                    last = s


def prefetch_whisper(cfg, log=print):
    log(f"Lade Spracherkennungs-Modell '{cfg['whisper_model']}' ...")
    from .speech import Ears
    Ears(cfg).load()


def run_setup_gui(cfg):
    """Kleines Fenster mit Fortschrittsprotokoll (für den Installer)."""
    import tkinter as tk
    root = tk.Tk()
    root.title("YAVIS – Ersteinrichtung")
    txt = tk.Text(root, width=70, height=16, state="disabled")
    txt.pack(padx=8, pady=8)

    def log(s):
        root.after(0, lambda: (txt.config(state="normal"), txt.insert("end", s + "\n"),
                               txt.see("end"), txt.config(state="disabled")))

    def work():
        try:
            ensure_ollama(cfg, log)
            prefetch_whisper(cfg, log)
            from . import voice
            voice.ensure_piper(voice.voice_cfg(cfg)["piper"], log)
            log("\nFertig! YAVIS kann jetzt gestartet werden. Sage 'YAVIS'.")
        except Exception as e:
            log(f"\nFEHLER: {e}\nBitte Internetverbindung prüfen und YAVIS-Einrichtung erneut starten.")
        root.after(0, lambda: tk.Button(root, text="Schließen", command=root.destroy).pack(pady=6))

    threading.Thread(target=work, daemon=True).start()
    root.mainloop()
