"""Natürliche Stimmen: Piper (lokal, offline, MIT) und optional Edge-Neural (online, kostenlos)."""
import os, subprocess, tempfile, zipfile
from . import config

PIPER_ZIP = "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip"
VOICE_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
PIPER_VOICES = {   # alle weiblich, deutsch
    "ramona": "de/de_DE/ramona/low/de_DE-ramona-low",
    "kerstin": "de/de_DE/kerstin/low/de_DE-kerstin-low",
    "eva_k": "de/de_DE/eva_k/x_low/de_DE-eva_k-x_low",
}
EDGE_VOICES = ["de-DE-KatjaNeural", "de-DE-AmalaNeural", "de-DE-SeraphinaMultilingualNeural"]

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


def _download(url, dest, log):
    import requests
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    os.replace(tmp, dest)


def ensure_piper(name, log=print):
    """Lädt Piper-Programm und Stimme einmalig (ca. 90 MB)."""
    if not piper_exe().exists():
        log("Lade Stimmen-Engine Piper ...")
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


def speak_piper(text, name, speed=1.0):
    import winsound
    out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    try:
        subprocess.run([str(piper_exe()), "--model", str(voice_file(name)), "--output_file", out,
                        "--length_scale", str(speed), "--sentence_silence", "0.25"],
                       input=text.encode("utf-8"), cwd=str(piper_exe().parent),
                       creationflags=0x08000000, check=True, capture_output=True, timeout=120)
        winsound.PlaySound(out, winsound.SND_FILENAME)
    finally:
        try:
            os.unlink(out)
        except OSError:
            pass


def speak_edge(text, voice):
    import asyncio, ctypes, edge_tts
    out = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
    try:
        asyncio.run(edge_tts.Communicate(text, voice).save(out))
        mci = ctypes.windll.winmm.mciSendStringW
        mci("close yavis", None, 0, 0)
        mci(f'open "{out}" type mpegvideo alias yavis', None, 0, 0)
        mci("play yavis wait", None, 0, 0)
        mci("close yavis", None, 0, 0)
    finally:
        try:
            os.unlink(out)
        except OSError:
            pass
