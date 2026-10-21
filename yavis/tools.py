"""PC-Steuerung & Werkzeuge. Alles Gefährliche läuft über confirm()."""
import os, subprocess, time, re
from pathlib import Path
from urllib.parse import urlparse


def _t(name, desc, props=None, req=None):
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props or {}, "required": req or []}}}

S = {"type": "string"}
SCHEMA = [
    _t("open_app", "Startet ein erlaubtes Programm (z.B. editor, rechner, browser, explorer).", {"name": S}, ["name"]),
    _t("search_files", "Sucht Dateien nach Namen in Dokumente/Desktop/Downloads.", {"query": S}, ["query"]),
    _t("focus_window", "Holt ein Fenster anhand eines Titelteils in den Vordergrund.", {"title": S}, ["title"]),
    _t("type_text", "Tippt Text in das aktive Fenster.", {"text": S}, ["text"]),
    _t("press_keys", "Drückt eine Tastenkombination, z.B. 'ctrl+s'.", {"keys": S}, ["keys"]),
    _t("web_search", "Kostenlose Webrecherche. Liefert Treffer mit Quellen.", {"query": S}, ["query"]),
    _t("remember", "Speichert eine Information dauerhaft lokal (nur wenn der Master es wünscht).", {"key": S, "value": S}, ["key", "value"]),
    _t("forget", "Löscht eine gespeicherte Information.", {"key": S}, ["key"]),
    _t("save_draft", "Speichert einen Text-Entwurf (Produktbeschreibung/Angebot). Veröffentlicht NICHTS.", {"title": S, "text": S}, ["title", "text"]),
    _t("delete_file", "Verschiebt eine Datei in den Papierkorb (nur nach Bestätigung).", {"path": S}, ["path"]),
]

BLOCKED_KEYS = {"ctrl+alt+delete", "alt+f4", "win+l", "ctrl+shift+delete"}


class Tools:
    def __init__(self, cfg, mem, confirm):
        self.cfg, self.mem, self.confirm = cfg, mem, confirm

    def dispatch(self, name: str, args: dict) -> str:
        fn = getattr(self, "t_" + name, None)
        if fn is None:
            return f"Unbekanntes Werkzeug: {name}"
        try:
            return str(fn(**(args or {})))
        except TypeError as e:
            return f"Ungültige Argumente: {e}"
        except Exception as e:
            return f"Fehler: {e}"

    def t_open_app(self, name):
        cmd = self.cfg["allowed_apps"].get(name.strip().lower())
        if not cmd:
            return f"'{name}' ist nicht freigegeben. Erlaubt: {', '.join(sorted(self.cfg['allowed_apps']))}"
        subprocess.Popen(cmd, shell=True)
        return f"{name} gestartet."

    def t_search_files(self, query):
        words = [w for w in re.split(r"\s+", query.lower()) if w]
        hits = []
        for root in self.cfg["search_roots"]:
            for dp, _, files in os.walk(os.path.expanduser(root)):
                for f in files:
                    if all(w in f.lower() for w in words):
                        hits.append(os.path.join(dp, f))
                        if len(hits) >= 10:
                            return "\n".join(hits)
        return "\n".join(hits) or "Nichts gefunden."

    def t_focus_window(self, title):
        import pygetwindow as gw
        wins = [w for w in gw.getAllWindows() if w.title and title.lower() in w.title.lower()]
        if not wins:
            return "Kein passendes Fenster."
        w = wins[0]
        if w.isMinimized:
            w.restore()
        w.activate()
        return f"Fenster '{w.title}' aktiviert."

    def t_type_text(self, text):
        import pyperclip, pyautogui
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        return "Text eingefügt."

    def t_press_keys(self, keys):
        k = keys.lower().replace(" ", "")
        if k in BLOCKED_KEYS:
            return "Diese Tastenkombination ist aus Sicherheitsgründen gesperrt."
        import pyautogui
        pyautogui.hotkey(*k.split("+"))
        return f"{keys} gedrückt."

    def t_web_search(self, query):
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        res = DDGS().text(query, region="de-de", max_results=5)
        if not res:
            return "Keine Treffer (Internet verfügbar?)."
        lines = []
        for i, r in enumerate(res, 1):
            dom = urlparse(r.get("href", "")).netloc.replace("www.", "")
            lines.append(f"[{i}] ({dom}) {r.get('title','')}: {r.get('body','')[:300]}")
        return "\n".join(lines) + "\nNenne in der Antwort die Quellen (Webseitennamen)."

    def t_remember(self, key, value):
        self.mem.remember(key, value)
        return "Gespeichert."

    def t_forget(self, key):
        return "Gelöscht." if self.mem.forget(key) else "Nicht gefunden."

    def t_save_draft(self, title, text):
        d = Path.home() / "Documents" / "YAVIS" / "Entwuerfe"
        d.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^\w\- ]", "", title)[:60] or "entwurf"
        p = d / f"{time.strftime('%Y%m%d-%H%M')}-{safe}.txt"
        p.write_text(text, encoding="utf-8")
        return f"Entwurf gespeichert: {p}. Es wurde nichts veröffentlicht oder versendet."

    def t_delete_file(self, path):
        p = Path(os.path.expanduser(path)).resolve()
        if Path.home().resolve() not in p.parents:
            return "Löschen außerhalb des Benutzerordners ist gesperrt."
        if not p.is_file():
            return "Datei nicht gefunden."
        if not self.confirm(f"Soll ich die Datei {p.name} wirklich in den Papierkorb verschieben?"):
            return "Abgebrochen, nichts gelöscht."
        from send2trash import send2trash
        send2trash(str(p))
        return "In den Papierkorb verschoben."
