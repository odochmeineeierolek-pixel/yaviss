"""Lokale Spracherkennung (faster-whisper) und Stimme (Windows-SAPI)."""
import re
import numpy as np

SR = 16000


class Ears:
    def __init__(self, cfg):
        self.cfg = cfg
        self.model = None

    def load(self):
        if self.model is None:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(self.cfg["whisper_model"], device="cpu", compute_type="int8")
        return self.model

    def record(self, max_wait=None, max_len=20.0):
        """Wartet auf Sprache, nimmt bis zur Pause auf. None bei Timeout."""
        import sounddevice as sd
        blk = int(SR * 0.03)
        thr = self.cfg["energy_threshold"]
        sil_need = int(self.cfg["silence_seconds"] / 0.03)
        buf, pre, started, silent, waited = [], [], False, 0, 0.0
        with sd.InputStream(samplerate=SR, channels=1, dtype="float32", blocksize=blk) as st:
            while True:
                data, _ = st.read(blk)
                x = data[:, 0].copy()
                loud = float(np.sqrt(np.mean(x ** 2))) > thr
                if not started:
                    pre = (pre + [x])[-8:]
                    waited += 0.03
                    if loud:
                        started, buf = True, list(pre)
                    elif max_wait and waited > max_wait:
                        return None
                else:
                    buf.append(x)
                    silent = 0 if loud else silent + 1
                    if silent > sil_need or len(buf) * 0.03 > max_len:
                        return np.concatenate(buf)

    def transcribe(self, audio) -> str:
        if audio is None or len(audio) < SR * 0.3:
            return ""
        segs, _ = self.load().transcribe(audio, language=self.cfg["language"],
                                         beam_size=1, vad_filter=True)
        return " ".join(s.text.strip() for s in segs).strip()


def norm(t: str) -> str:
    return re.sub(r"[^\w\säöüß]", " ", t.lower())


def split_wake(text: str, wake_words):
    """-> (wake_gefunden, restlicher_befehl)"""
    n = norm(text)
    for w in wake_words:
        m = re.search(r"\b" + re.escape(w) + r"\b", n)
        if m:
            return True, re.sub(r"\s+", " ", n[m.end():]).strip()
    return False, ""


class Mouth:
    def __init__(self, cfg):
        self.cfg = cfg

    def say(self, text: str):
        from . import voice
        eng = self.cfg.get("voice_engine", "piper")
        try:
            if eng == "edge":
                return voice.speak_edge(text, self.cfg["edge_voice"])
            if eng == "piper":
                name = self.cfg["piper_voice"]
                if not voice.piper_ready(name):
                    voice.ensure_piper(name, lambda m: None)
                return voice.speak_piper(text, name, self.cfg.get("voice_speed", 1.0))
        except Exception:
            import logging
            logging.exception("Stimme %s fehlgeschlagen, nutze Windows-Stimme", eng)
        self._sapi(text)

    def _sapi(self, text: str):
        import pyttsx3
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
