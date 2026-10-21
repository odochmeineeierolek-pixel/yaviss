"""Assistent-Logik: Aktivierungswort -> Befehl -> Antwort. Die Oberfläche hängt sich per Callbacks an."""
import logging, threading, time
from . import config
from .memory import Memory
from .tools import Tools
from .brain import Brain
from .speech import Ears, Mouth, split_wake, norm
from .setup_ollama import ensure_ollama

YES = ("ja", "jawohl", "bestätig", "mach das", "okay", "ok", "klar", "gerne")
NO = ("nein", "abbrechen", "stopp", "nicht")
GOOD = ("das war gut", "das war richtig", "gut gemacht", "das war super")
BAD = ("das war falsch", "das war schlecht", "das war nicht richtig", "das stimmt nicht")


def is_yes(t):
    n = norm(t)
    return any(w in n for w in YES) and not any(w in n.split() for w in NO)


class Assistant:
    def __init__(self, cfg, on_status=None, on_message=None, mem_path=None):
        self.cfg = cfg
        self.on_status = on_status or (lambda s: None)
        self.on_message = on_message or (lambda role, text: None)
        self.mem = Memory(mem_path or (config.DATA_DIR / "memory.db"))
        self.ears, self.mouth = Ears(cfg), Mouth(cfg)
        self.brain = Brain(cfg, self.mem, Tools(cfg, self.mem, self.confirm))
        self.stop = threading.Event()
        self.paused = False
        self.force_listen = False   # Mikrofon-Knopf: nächster Satz braucht kein "YAVIS"
        self.lock = threading.Lock()

    def say(self, text):
        self.on_message("yavis", text)
        if self.cfg.get("speak", True):
            self.on_status("Spricht")
            self.mouth.say(text)

    def confirm(self, question):
        self.say(question + " Bitte sage Ja oder Nein.")
        self.on_status("Hört zu")
        return is_yes(self.ears.transcribe(self.ears.record(max_wait=10)))

    def handle(self, cmd) -> bool:
        """Führt einen Befehl aus. False = YAVIS soll beenden."""
        with self.lock:
            self.on_message("user", cmd)
            n = norm(cmd)
            if any(w in n for w in ("beenden", "schlaf ein", "tschüss")) and len(n.split()) < 4:
                self.say("Bis später, Master.")
                return False
            if any(n.startswith(p) for p in GOOD):
                self.mem.add_feedback(*self.brain.last, 1, cmd)
                self.say("Danke, Master. Ich merke mir das.")
                return True
            if any(n.startswith(p) for p in BAD):
                self.mem.add_feedback(*self.brain.last, -1, cmd)
                self.say("Verstanden, Master. Ich werde es besser machen.")
                return True
            self.on_status("Denkt nach")
            try:
                self.say(self.brain.respond(cmd))
            except Exception:
                logging.exception("Fehler")
                self.say("Entschuldigung Master, da ist ein Fehler aufgetreten.")
            return True

    def run(self):
        self.on_status("Startet")
        try:
            ensure_ollama(self.cfg, logging.info)
            if self.cfg.get("voice_engine") == "piper":
                self.on_status("Lädt Stimme")
                try:
                    from . import voice
                    voice.ensure_piper(self.cfg["piper_voice"], logging.info)
                except Exception:
                    logging.exception("Piper-Download fehlgeschlagen (Windows-Stimme als Ersatz)")
            self.on_status("Lädt Spracherkennung")
            self.ears.load()
        except Exception as e:
            logging.error(e)
            self.say("Master, die Einrichtung ist unvollständig. Bitte starte die YAVIS-Ersteinrichtung.")
            self.on_status("Fehler")
            return
        self.say("Master, YAVIS ist bereit.")
        while not self.stop.is_set():
            try:
                self.on_status("Pausiert" if self.paused else "Wartet auf „YAVIS“")
                text = self.ears.transcribe(self.ears.record())
                if self.paused or not text:
                    continue
                if self.force_listen:
                    self.force_listen, cmd = False, text
                else:
                    woke, cmd = split_wake(text, self.cfg["wake_words"])
                    if not woke:
                        continue
                    if len(cmd) < 3:
                        self.say("Ja, Master?")
                        self.on_status("Hört zu")
                        cmd = self.ears.transcribe(self.ears.record(max_wait=8))
                        if not cmd:
                            continue
                if not self.handle(cmd):
                    break
            except Exception:
                logging.exception("Schleifenfehler")
                time.sleep(1)
        self.stop.set()


def main():
    import sys
    cfg = config.load()
    logging.basicConfig(filename=str(config.DATA_DIR / "yavis.log"), level=logging.INFO,
                        format="%(asctime)s %(message)s")
    from .gui import App
    App(cfg, start_hidden="--minimized" in sys.argv).mainloop()
