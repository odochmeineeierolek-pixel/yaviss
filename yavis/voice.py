"""Stimmen mit Gefühlen.

- Piper: lokal, offline, kostenlos (MIT). Tonhöhe/Tempo/Gefühl werden hier zusätzlich eingestellt.
- Edge:  optional online, kostenlos ohne Schlüssel, sehr natürlich (Text geht dafür an Microsoft).
Beides erzeugt eine WAV-Datei; daraus wird auch die Lautstärkekurve für den bewegten Kreis berechnet.
"""
import json, os, subprocess, tempfile, time, wave, zipfile
from pathlib import Path
import numpy as np
from . import config

NOWIN = config.NOWIN  # kein Konsolenfenster

PIPER_ZIP = "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip"
VOICE_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
PIPER_VOICES = {
    "ramona": "de/de_DE/ramona/low/de_DE-ramona-low",                 # Frau
    "kerstin": "de/de_DE/kerstin/low/de_DE-kerstin-low",              # Frau
    "eva_k": "de/de_DE/eva_k/x_low/de_DE-eva_k-x_low",                # Frau
    "thorsten": "de/de_DE/thorsten/medium/de_DE-thorsten-medium",     # Mann
    "karlsson": "de/de_DE/karlsson/low/de_DE-karlsson-low",           # Mann
    "thorsten_emotional": "de/de_DE/thorsten_emotional/medium/de_DE-thorsten_emotional-medium",  # Mann, 8 Emotionen
}

# Auswahl in den Einstellungen. length = Tempo (>1 langsamer), pitch = Tonhöhe (<1 tiefer)
VOICES = {
    "ramona": {"label": "Ramona – warm & natürlich (Frau, offline)", "engine": "piper", "piper": "ramona"},
    "mommy": {"label": "Mommy – sanft, ruhig & mütterlich (Frau, offline)", "engine": "piper",
              "piper": "kerstin", "length": 1.12, "pitch": 0.97},
    "thorsten": {"label": "Thorsten – klar & freundlich (Mann, offline)", "engine": "piper", "piper": "thorsten"},
    "muskel": {"label": "Muskelmann – tief, kräftig & selbstsicher (Mann, offline)", "engine": "piper",
               "piper": "karlsson", "length": 1.05, "pitch": 0.93},
    "thorsten_emo": {"label": "Thorsten Emotional – echte Gefühlsstimme (Mann, offline)", "engine": "piper",
                     "piper": "thorsten_emotional"},
    "katja": {"label": "Katja – sehr natürlich (Frau, online)", "engine": "edge",
              "edge": "de-DE-KatjaNeural", "piper": "ramona"},
    "mommy_online": {"label": "Mommy – extra weich & mütterlich (Frau, online)", "engine": "edge",
                     "edge": "de-DE-SeraphinaMultilingualNeural", "edge_rate": -8, "edge_pitch": -2, "piper": "kerstin"},
    "conrad": {"label": "Conrad – sehr natürlich (Mann, online)", "engine": "edge",
               "edge": "de-DE-ConradNeural", "piper": "thorsten"},
    "muskel_online": {"label": "Muskelmann – extra tief & kraftvoll (Mann, online)", "engine": "edge",
                      "edge": "de-DE-KillianNeural", "edge_rate": -6, "edge_pitch": -12, "piper": "karlsson"},
}
DEFAULT_VOICE = "ramona"

# Gefühle -> Sprechweise
EMOTIONS = {
    "neutral":   dict(length=1.00, pitch=1.00, noise=0.667, noise_w=0.80, vol=1.00, er=0,   ep=0,  ev=0),
    "nett":      dict(length=1.03, pitch=1.01, noise=0.75,  noise_w=0.85, vol=1.00, er=-2,  ep=1,  ev=0),
    "lieb":      dict(length=1.10, pitch=1.00, noise=0.60,  noise_w=0.70, vol=0.90, er=-8,  ep=-1, ev=-8),
    "froehlich": dict(length=0.93, pitch=1.04, noise=0.85,  noise_w=0.90, vol=1.05, er=6,   ep=5,  ev=5),
    "traurig":   dict(length=1.25, pitch=0.95, noise=0.45,  noise_w=0.50, vol=0.85, er=-18, ep=-8, ev=-12),
    "boese":     dict(length=0.92, pitch=0.94, noise=0.90,  noise_w=1.00, vol=1.15, er=8,   ep=-5, ev=10),
}
# Für die Gefühlsstimme (Thorsten Emotional) gibt es echte Emotions-Sprecher
EMO_SPEAKERS = {"froehlich": "amused", "boese": "angry", "traurig": "sleepy", "neutral": "neutral",
                "nett": "neutral", "lieb": "neutral"}

PIPER_DIR = config.DATA_DIR / "piper"
VOICE_DIR = config.DATA_DIR / "voices"


def piper_exe():
    return PIPER_DIR / "piper" / "piper.exe"


def voice_urls(name):
    base = VOICE_BASE + PIPER_VOICES[name]
    return base + ".onnx", base + ".onnx.json"


def voice_file(name):
    return VOICE_DIR / (PIPER_VOICES[name].split("/")[-1] + ".onnx")


def piper_ready(name):
    return piper_exe().exists() and voice_file(name).exists()


def _download(url, dest, log=print):
    import requests
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length") or 0)
        done, last = 0, -1
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
                done += len(chunk)
                if total and int(100 * done / total) // 10 != last:
                    last = int(100 * done / total) // 10
                    log(f"{dest.name}: {int(100 * done / total)}%")
    os.replace(tmp, dest)


def ensure_piper(name, log=print):
    """Lädt Piper-Programm und Stimme einmalig."""
    if not piper_exe().exists():
        log("Lade Stimmen-Engine ...")
        z = config.DATA_DIR / "piper.zip"
        _download(PIPER_ZIP, z, log)
        with zipfile.ZipFile(z) as zf:
            zf.extractall(PIPER_DIR)
        z.unlink(missing_ok=True)
    vf = voice_file(name)
    if not vf.exists():
        log(f"Lade Stimme {name} ...")
        onnx, js = voice_urls(name)
        _download(js, vf.with_suffix(".onnx.json"), log)
        _download(onnx, vf, log)


def voice_cfg(cfg):
    return VOICES.get(cfg.get("voice"), VOICES[DEFAULT_VOICE])


def emotion_cfg(emotion):
    return EMOTIONS.get(emotion, EMOTIONS["neutral"])


def speaker_id(piper_name, emotion):
    """Nummer des Emotions-Sprechers (nur bei Thorsten Emotional), sonst None."""
    if piper_name != "thorsten_emotional":
        return None
    try:
        meta = json.loads(Path(str(voice_file(piper_name)) + ".json").read_text(encoding="utf-8"))
        return meta["speaker_id_map"][EMO_SPEAKERS.get(emotion, "neutral")]
    except Exception:
        return None


def postprocess(path, pitch=1.0, vol=1.0):
    """Tonhöhe (über die Abspielrate) und Lautstärke anpassen."""
    if abs(pitch - 1) < 0.005 and abs(vol - 1) < 0.01:
        return
    with wave.open(path, "rb") as w:
        ch, sw, fr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        data = w.readframes(n)
    if sw == 2 and abs(vol - 1) >= 0.01:
        a = np.frombuffer(data, dtype=np.int16).astype(np.float32) * vol
        data = np.clip(a, -32768, 32767).astype(np.int16).tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(sw)
        w.setframerate(int(fr * pitch))
        w.writeframes(data)


def synth_piper(text, piper_name, vcfg, emo_name, speed, out):
    emo = emotion_cfg(emo_name)
    pitch = vcfg.get("pitch", 1.0) * emo["pitch"]
    # Höher abspielen = schneller, deshalb Tempo gegenrechnen
    length = vcfg.get("length", 1.0) * emo["length"] * speed * pitch
    cmd = [str(piper_exe()), "--model", str(voice_file(piper_name)), "--output_file", out,
           "--length_scale", f"{length:.3f}", "--noise_scale", str(emo["noise"]),
           "--noise_w", str(emo["noise_w"]), "--sentence_silence", "0.3"]
    sid = speaker_id(piper_name, emo_name)
    if sid is not None:
        cmd += ["--speaker", str(sid)]
    subprocess.run(cmd, input=text.encode("utf-8"), cwd=str(piper_exe().parent),
                   creationflags=NOWIN, check=True, capture_output=True, timeout=120)
    postprocess(out, pitch, emo["vol"])


def _mp3_to_wav(src, dst):
    import av
    frames = []
    with av.open(src) as c:
        rs = av.AudioResampler(format="s16", layout="mono", rate=24000)
        for fr in c.decode(c.streams.audio[0]):
            for o in rs.resample(fr):
                frames.append(o.to_ndarray().tobytes())
        for o in rs.resample(None):
            frames.append(o.to_ndarray().tobytes())
    with wave.open(dst, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"".join(frames))


def synth_edge(text, vcfg, emo_name, speed, out):
    import asyncio, edge_tts
    emo = emotion_cfg(emo_name)
    rate = int(round((1 / speed - 1) * 100)) + vcfg.get("edge_rate", 0) + emo["er"]
    pitch = vcfg.get("edge_pitch", 0) + emo["ep"]
    mp3 = out + ".mp3"
    try:
        asyncio.run(edge_tts.Communicate(text, vcfg["edge"], rate=f"{rate:+d}%", pitch=f"{pitch:+d}Hz",
                                         volume=f"{emo['ev']:+d}%").save(mp3))
        _mp3_to_wav(mp3, out)
    finally:
        try:
            os.unlink(mp3)
        except OSError:
            pass


def envelope(path, step=0.02):
    """Lautstärke pro 20 ms (0..1) und Dauer – für den bewegten Kreis."""
    with wave.open(path, "rb") as w:
        fr, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
        a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32)
    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1)
    win = max(1, int(fr * step))
    k = len(a) // win
    if k == 0:
        return np.zeros(1), n / fr
    rms = np.sqrt((a[:k * win].reshape(k, win) ** 2).mean(axis=1))
    peak = np.percentile(rms, 95) or 1.0
    env = np.clip(rms / peak, 0, 1)
    env = np.convolve(env, np.ones(3) / 3, mode="same")
    return env, n / fr


def play_wav(path, on_level=lambda v: None):
    import winsound
    env, dur = envelope(path)
    winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    t0 = time.time()
    while True:
        t = time.time() - t0
        if t >= dur:
            break
        on_level(float(env[min(int(t / 0.02), len(env) - 1)]))
        time.sleep(0.02)
    time.sleep(0.15)
    on_level(0.0)


def speak(text, cfg, emotion="neutral", on_level=lambda v: None, log=lambda m: None):
    """Spricht den Text mit der gewählten Stimme und dem Gefühl. Wirft bei Problemen eine Ausnahme."""
    import logging
    vcfg = voice_cfg(cfg)
    speed = float(cfg.get("voice_speed", 1.0))
    out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    try:
        done = False
        if vcfg["engine"] == "edge":
            try:
                synth_edge(text, vcfg, emotion, speed, out)
                done = True
            except Exception:
                logging.exception("Online-Stimme nicht verfügbar, nutze Offline-Stimme")
        if not done:
            name = vcfg["piper"]
            if not piper_ready(name):
                ensure_piper(name, log)
            synth_piper(text, name, vcfg if vcfg["engine"] == "piper" else {}, emotion, speed, out)
        play_wav(out, on_level)
    finally:
        try:
            os.unlink(out)
        except OSError:
            pass
