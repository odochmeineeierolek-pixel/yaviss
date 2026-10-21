"""Zuhören (faster-whisper, lokal) und Sprechen."""
import difflib, logging, random, re, threading, time
import numpy as np

SR = 16000
BLOCK = 0.03
# Typische Whisper-"Halluzinationen" bei Rauschen/Stille
GHOSTS = ("untertitel", "vielen dank fürs zuschauen", "danke fürs zuschauen", "amara.org",
          "copyright", "musik", "bis zum nächsten mal")


class Ears:
    def __init__(self, cfg):
        self.cfg = cfg
        self.model = None
        self.level = 0.0       # aktuelle Mikrofonlautstärke 0..1 (für den Kreis)
        self.noise = 0.004     # laufend geschätztes Grundrauschen

    def load(self):
        if self.model is None:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(self.cfg["whisper_model"], device="cpu", compute_type="int8")
        return self.model

    def record(self, max_wait=None, max_len=25.0):
        """Wartet auf Sprache, nimmt bis zur Pause auf. None bei Timeout.
        Die Schwelle passt sich automatisch dem Raumrauschen an."""
        import sounddevice as sd
        blk = int(SR * BLOCK)
        sil_need = int(self.cfg["silence_seconds"] / BLOCK)
        floor = self.cfg.get("min_energy", 0.008)
        buf, pre, started, silent, waited, hot = [], [], False, 0, 0.0, 0
        with sd.InputStream(samplerate=SR, channels=1, dtype="float32", blocksize=blk,
                            device=self.cfg.get("mic_device")) as st:
            while True:
                data, _ = st.read(blk)
                x = data[:, 0].copy()
                rms = float(np.sqrt(np.mean(x ** 2)))
                self.level = min(1.0, rms * 12)
                thr = max(floor, self.noise * 3.0)
                loud = rms > thr
                if not started:
                    # leise: schnell anpassen; dauerhaft laut (z. B. Hintergrundmusik): langsam mitwandern
                    self.noise = (0.97 * self.noise + 0.03 * rms) if not loud else (0.998 * self.noise + 0.002 * rms)
                    pre = (pre + [x])[-20:]          # 0,6 s Vorlauf, damit der Satzanfang nicht fehlt
                    waited += BLOCK
                    hot = hot + 1 if loud else 0
                    if hot >= 2:                      # 2 laute Blöcke in Folge = Sprache, kein Klick
                        started, buf = True, list(pre)
                    elif max_wait and waited > max_wait:
                        self.level = 0.0
                        return None
                else:
                    buf.append(x)
                    silent = 0 if loud else silent + 1
                    if silent > sil_need or len(buf) * BLOCK > max_len:
                        self.level = 0.0
                        return np.concatenate(buf)

    def transcribe(self, audio) -> str:
        if audio is None or len(audio) < SR * 0.4:
            return ""
        prompt = "Hallo " + (self.cfg["wake_words"][0].upper() if self.cfg["wake_words"] else "YAVIS") + "."
        segs, _ = self.load().transcribe(
            audio, language=self.cfg["language"], beam_size=5, temperature=0.0,
            condition_on_previous_text=False, initial_prompt=prompt,
            vad_filter=True, vad_parameters={"min_silence_duration_ms": 500})
        parts = [s.text.strip() for s in segs if getattr(s, "no_speech_prob", 0) < 0.6]
        text = " ".join(parts).strip()
        if any(g in text.lower() for g in GHOSTS) and len(text.split()) < 8:
            return ""
        return text


def norm(t: str) -> str:
    return re.sub(r"[^\w\säöüß]", " ", t.lower())


def split_wake(text: str, wake_words, fuzzy: float = 0.78):
    """-> (wake_gefunden, restlicher_befehl). Erkennt Aktivierungswörter auch bei kleinen Hörfehlern."""
    n = norm(text)
    words = [w.strip().lower() for w in wake_words if w.strip()]
    for w in words:
        m = re.search(r"\b" + re.escape(w) + r"\b", n)
        if m:
            return True, re.sub(r"\s+", " ", n[m.end():]).strip()
    toks = list(re.finditer(r"\S+", n))
    for i, tok in enumerate(toks[:4]):
        t = tok.group()
        if len(t) < 3:
            continue
        for w in words:
            if len(w) >= 4 and difflib.SequenceMatcher(None, t, w).ratio() >= fuzzy:
                return True, re.sub(r"\s+", " ", n[tok.end():]).strip()
    return False, ""


class Mouth:
    def __init__(self, cfg):
        self.cfg = cfg
        self.level = 0.0       # aktuelle Sprechlautstärke 0..1 (für den Kreis)
        self.log = lambda m: None

    def _set_level(self, v):
        self.level = v

    def say(self, text: str, emotion: str = "neutral"):
        from . import voice
        try:
            return voice.speak(text, self.cfg, emotion, self._set_level, self.log)
        except Exception:
            logging.exception("Stimme fehlgeschlagen, nutze Windows-Stimme")
        finally:
            self.level = 0.0
        self._sapi(text)

    def _sapi(self, text: str):
        import pyttsx3
        run = threading.Event()
        run.set()

        def wiggle():
            while run.is_set():
                self.level = random.uniform(0.15, 0.8)
                time.sleep(0.07)
            self.level = 0.0
        threading.Thread(target=wiggle, daemon=True).start()
        try:
            eng = pyttsx3.init()
            eng.setProperty("rate", self.cfg["speech_rate"])
            best = None
            for v in eng.getProperty("voices"):
                name = (v.name or "").lower()
                info = (str(getattr(v, "languages", "")) + (v.id or "")).lower()
                if "de" in info or "german" in name or "deutsch" in name:
                    if any(f in name for f in ("hedda", "katja", "female")):
                        best = v.id
                        break
                    best = best or v.id
            if best:
                eng.setProperty("voice", best)
            eng.say(text)
            eng.runAndWait()
            eng.stop()
        finally:
            run.clear()
