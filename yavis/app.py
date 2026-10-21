"""Assistent-Logik: Aktivierungswort -> Befehl -> Antwort mit Gefühl. Die Oberfläche hängt sich per Callbacks an."""
import logging, threading, time
from . import config
from .memory import Memory
from .tools import Tools
from .brain import Brain
from .speech import Ears, Mouth, split_wake, norm
from .setup_ollama import ensure_ollama
from .music import MusicPlayer

YES = ("ja", "jawohl", "bestätig", "mach das", "okay", "ok", "klar", "gerne")
NO = ("nein", "abbrechen", "stopp", "nicht")
GOOD = ("das war gut", "das war richtig", "gut gemacht", "das war super")
BAD = ("das war falsch", "das war schlecht", "das war nicht richtig", "das stimmt nicht")
MUSIC_CMDS = {   # Sprachbefehl-Satzteil -> Aktion
    "off":  ("musik aus", "musik stopp", "musik pausieren", "musik ausschalten", "stopp die musik", "pausiere die musik"),
    "on":   ("musik an", "musik starten", "spiel musik", "musik abspielen", "musik einschalten", "musik weiter"),
    "next": ("nächstes lied", "nächster song", "nächstes lied", "überspring das lied", "anderes lied"),
    "prev": ("vorheriges lied", "voriges lied", "letztes lied"),
    "down": ("musik leiser", "musik runter", "musik etwas leiser"),
    "up":   ("musik lauter", "musik hoch", "musik etwas lauter"),
}
NEUTRAL_ON = ("sei neutral", "bleib neutral", "neutral bleiben", "keine gefühle", "sei sachlich", "gefühle aus")
NEUTRAL_OFF = ("zeig gefühle", "zeig wieder gefühle", "du darfst gefühle", "sei nicht mehr neutral",
               "sei wieder du selbst", "gefühle an", "gefühle wieder")


def is_yes(t):
    n = norm(t)
    return any(w in n for w in YES) and not any(w in n.split() for w in NO)


class Assistant:
    def __init__(self, cfg, on_status=None, on_message=None, on_emotion=None, mem_path=None):
        self.cfg = cfg
        self.on_status = on_status or (lambda s: None)
        self.on_message = on_message or (lambda role, text: None)
        self.on_emotion = on_emotion or (lambda e: None)
        self.mem = Memory(mem_path or (config.DATA_DIR / "memory.db"))
        self.ears, self.mouth = Ears(cfg), Mouth(cfg)
        self.mouth.log = self._log
        self.music = MusicPlayer(cfg)
        self.brain = Brain(cfg, self.mem, Tools(cfg, self.mem, self.confirm))
        self.stop = threading.Event()
        self.paused = False
        self.force_listen = False   # Mikrofon-Knopf: nächster Satz braucht kein "YAVIS"
        self.follow_until = 0.0     # Gesprächsfenster: kurz nach einer Antwort geht es ohne "YAVIS" weiter
        self.lock = threading.Lock()
        self.save_cfg = config.save

    def _log(self, msg):
        logging.info(msg)
        self.on_status("Richtet ein: " + str(msg))

    def say(self, text, emotion="nett"):
        if self.cfg.get("neutral_mode"):
            emotion = "neutral"
        self.on_message("yavis", text)
        self.on_emotion(emotion)
        if self.cfg.get("speak", True):
            self.on_status("Spricht")
            self.music.duck(True)          # Musik leiser, solange YAVIS spricht
            try:
                self.mouth.say(text, emotion)
            finally:
                self.music.duck(False)
        self.on_emotion("neutral")

    def confirm(self, question):
        self.say(question + " Bitte sage Ja oder Nein.", "nett")
        self.on_status("Hört zu")
        self.music.duck(True)
        try:
            return is_yes(self.ears.transcribe(self.ears.record(max_wait=10)))
        finally:
            self.music.duck(False)

    def _set_neutral(self, value: bool):
        self.cfg["neutral_mode"] = value
        try:
            self.save_cfg(self.cfg)
        except Exception:
            logging.exception("Einstellung konnte nicht gespeichert werden")

    def _music_command(self, n):
        """Sprachbefehle für die Musik. Gibt True zurück, wenn der Satz einer war."""
        act = next((a for a, ps in MUSIC_CMDS.items() if any(p in n for p in ps)), None)
        if act is None:
            return False
        m = self.music
        if act in ("on", "next", "prev") and not m.tracks():
            self.say("Master, ich habe noch keine Musik. Füge Lieder im Menü Musik hinzu.", "nett")
            return True
        if act == "off":
            m.pause()
            self.say("Musik aus, Master.", "nett")
        elif act == "on":
            m.play()
            self.say("Gerne, Master. Musik läuft.", "froehlich")
        elif act == "next":
            m.next()
            self.say("Das nächste Lied, Master.", "nett")
        elif act == "prev":
            m.prev()
            self.say("Das Lied davor, Master.", "nett")
        elif act in ("down", "up"):
            m.set_volume(float(self.cfg.get("music_volume", 0.35)) + (0.15 if act == "up" else -0.15))
            self.say("Lauter, Master." if act == "up" else "Leiser, Master.", "nett")
        try:
            self.save_cfg(self.cfg)
        except Exception:
            logging.exception("Einstellung konnte nicht gespeichert werden")
        return True

    def handle(self, cmd) -> bool:
        """Führt einen Befehl aus. False = YAVIS soll beenden."""
        with self.lock:
            self.on_message("user", cmd)
            n = norm(cmd)
            if any(w in n for w in ("beenden", "schlaf ein", "tschüss")) and len(n.split()) < 4:
                self.say("Bis später, Master.", "lieb")
                return False
            if self._music_command(n):
                return True
            if any(p in n for p in NEUTRAL_OFF):
                self._set_neutral(False)
                self.say("Sehr gerne, Master. Ich darf wieder ich selbst sein.", "froehlich")
                return True
            if any(p in n for p in NEUTRAL_ON):
                self._set_neutral(True)
                self.say("Verstanden, Master. Ich bleibe ab jetzt neutral.", "neutral")
                return True
            if any(n.startswith(p) for p in GOOD):
                self.mem.add_feedback(*self.brain.last, 1, cmd)
                self.say("Danke, Master. Ich merke mir das.", "froehlich")
                return True
            if any(n.startswith(p) for p in BAD):
                self.mem.add_feedback(*self.brain.last, -1, cmd)
                self.say("Verstanden, Master. Ich werde es besser machen.", "traurig")
                return True
            self.on_status("Denkt nach")
            try:
                answer = self.brain.respond(cmd)
                self.say(answer, getattr(self.brain, "emotion", "nett"))
            except Exception:
                logging.exception("Fehler")
                self.say("Entschuldigung Master, da ist ein Fehler aufgetreten.", "traurig")
            self.follow_until = time.time() + float(self.cfg.get("conversation_seconds", 10))
            return True

    def run(self):
        self.on_status("Startet")
        try:
            ensure_ollama(self.cfg, self._log)
            from . import voice
            vc = voice.voice_cfg(self.cfg)
            try:
                if not voice.piper_ready(vc["piper"]):
                    self.on_status("Richtet ein: lade Stimme")
                    voice.ensure_piper(vc["piper"], self._log)
            except Exception:
                logging.exception("Stimmen-Download fehlgeschlagen (Windows-Stimme als Ersatz)")
            self.on_status("Richtet ein: lade Spracherkennung (einmalig)")
            self.ears.load()
        except Exception as e:
            logging.error(e)
            self.say("Master, die Einrichtung ist unvollständig. Bitte prüfe die Internetverbindung und starte mich neu.", "traurig")
            self.on_status("Fehler")
            return
        self.say("Master, ich bin bereit.", "froehlich")
        while not self.stop.is_set():
            try:
                self.on_status("Pausiert" if self.paused else "Wartet auf „YAVIS“")
                text = self.ears.transcribe(self.ears.record())
                if self.paused or not text:
                    continue
                if self.force_listen:
                    self.force_listen, cmd = False, text
                else:
                    woke, cmd = split_wake(text, self.cfg["wake_words"], self.cfg.get("wake_fuzzy", 0.78))
                    if not woke:
                        if time.time() < self.follow_until:   # Gespräch läuft noch
                            cmd = norm(text).strip()
                        else:
                            continue
                    elif len(cmd) < 3:
                        self.say("Ja, Master?", "nett")
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
