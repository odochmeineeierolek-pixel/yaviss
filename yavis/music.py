"""Hintergrundmusik: eigene Lieder abspielen, Lautstärke regeln, leiser beim Sprechen.

Wiedergabe über die in Windows eingebaute Mediensteuerung (MCI) – keine zusätzliche Software, 0 €.
Ordner für Lieder: %APPDATA%\\YAVIS\\music  (Lieder lassen sich im Menü „Musik“ hinzufügen).
"""
import logging, os, shutil, sys, threading, time
from pathlib import Path
from . import config

EXTENSIONS = (".mp3", ".wav", ".wma", ".m4a", ".aac")
DUCK_FACTOR = 0.25   # so laut bleibt die Musik, während YAVIS spricht/zuhört


class NullBackend:
    """Ersatz ohne Ton (Tests, Nicht-Windows)."""
    def __init__(self):
        self.path, self.volume, self.playing, self.finished = None, 0.0, False, False

    def open(self, path): self.path, self.playing, self.finished = str(path), False, False
    def play(self): self.playing = True
    def pause(self): self.playing = False
    def resume(self): self.playing = True
    def set_volume(self, v): self.volume = v
    def is_finished(self): return self.finished
    def close(self): self.path, self.playing = None, False


class MciBackend:
    """Windows-Mediensteuerung (winmm)."""
    ALIAS = "yavismusic"

    def _send(self, cmd):
        import ctypes
        buf = ctypes.create_unicode_buffer(128)
        err = ctypes.windll.winmm.mciSendStringW(cmd, buf, 128, 0)
        return err, buf.value

    def open(self, path):
        self.close()
        err, _ = self._send(f'open "{path}" type mpegvideo alias {self.ALIAS}')
        if err:
            raise RuntimeError(f"Datei kann nicht abgespielt werden ({err}): {path}")

    def play(self): self._send(f"play {self.ALIAS} from 0")
    def pause(self): self._send(f"pause {self.ALIAS}")
    def resume(self): self._send(f"resume {self.ALIAS}")
    def set_volume(self, v): self._send(f"setaudio {self.ALIAS} volume to {int(max(0.0, min(1.0, v)) * 1000)}")
    def is_finished(self): return self._send(f"status {self.ALIAS} mode")[1] == "stopped"
    def close(self): self._send(f"close {self.ALIAS}")


def default_backend():
    return MciBackend() if os.name == "nt" else NullBackend()


def bundled_music_dir() -> Path:
    """Ordner mit den vom Installer mitgelieferten Liedern."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "music"
    return Path(__file__).resolve().parent.parent / "music"


class MusicPlayer:
    def __init__(self, cfg, backend=None, folder=None):
        self.cfg = cfg
        self.backend = backend or default_backend()
        self.folder = Path(folder) if folder else config.DATA_DIR / "music"
        self.index = 0
        self.playing = False
        self.paused = False
        self._ducked = False
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread = None

    # ---------- Lieder ----------
    def tracks(self):
        if not self.folder.is_dir():
            return []
        return sorted(p for p in self.folder.iterdir() if p.suffix.lower() in EXTENSIONS)

    def seed(self, src: Path = None):
        """Beim ersten Start die mitgelieferten Lieder in den Musikordner kopieren."""
        if self.cfg.get("music_seeded"):
            return
        src = Path(src) if src else bundled_music_dir()
        if src.is_dir():
            self.add([p for p in src.iterdir() if p.suffix.lower() in EXTENSIONS])
        self.cfg["music_seeded"] = True
        try:
            config.save(self.cfg)
        except Exception:
            logging.exception("Konnte Einstellung nicht speichern")

    def add(self, paths) -> int:
        """Kopiert Lieder in den Musikordner. Gibt die Anzahl neu hinzugefügter zurück."""
        self.folder.mkdir(parents=True, exist_ok=True)
        n = 0
        for p in map(Path, paths):
            if p.suffix.lower() not in EXTENSIONS or not p.is_file():
                continue
            dest = self.folder / p.name
            if dest.exists():
                continue
            shutil.copy2(p, dest)
            n += 1
        return n

    def remove(self, name) -> bool:
        with self._lock:
            target = self.folder / name
            if not target.is_file() or target.parent != self.folder:
                return False
            if self.current_name() == name:
                self.stop()
            target.unlink()
            self.index = 0
            return True

    def current_name(self):
        t = self.tracks()
        return t[self.index % len(t)].name if t else None

    # ---------- Wiedergabe ----------
    def effective_volume(self):
        v = float(self.cfg.get("music_volume", 0.35))
        if self._ducked and self.cfg.get("music_duck", True):
            v *= DUCK_FACTOR
        return max(0.0, min(1.0, v))

    def _start_track(self):
        t = self.tracks()
        if not t:
            return False
        self.index %= len(t)
        try:
            self.backend.open(t[self.index])
            self.backend.set_volume(self.effective_volume())
            self.backend.play()
        except Exception:
            logging.exception("Musik konnte nicht gestartet werden")
            self.playing = False
            return False
        self.playing, self.paused = True, False
        self._ensure_thread()
        return True

    def play(self, index=None):
        with self._lock:
            if index is not None:
                self.index = index
                return self._start_track()
            if self.paused and self.playing:
                self.backend.resume()
                self.paused = False
                return True
            if self.playing:
                return True
            return self._start_track()

    def pause(self):
        with self._lock:
            if self.playing and not self.paused:
                self.backend.pause()
                self.paused = True

    def stop(self):
        with self._lock:
            self.backend.close()
            self.playing = self.paused = False

    def toggle(self):
        with self._lock:
            if self.playing and not self.paused:
                self.pause()
            else:
                self.play()

    def next(self):
        with self._lock:
            self.index += 1
            return self._start_track()

    def prev(self):
        with self._lock:
            self.index = max(0, self.index - 1)
            return self._start_track()

    def set_volume(self, v):
        self.cfg["music_volume"] = round(max(0.0, min(1.0, float(v))), 3)
        self.backend.set_volume(self.effective_volume())

    def duck(self, on: bool):
        """Musik leiser (True) bzw. wieder normal (False) – wenn YAVIS spricht oder zuhört."""
        self._ducked = on
        if self.playing:
            self.backend.set_volume(self.effective_volume())

    def autoplay(self):
        if self.cfg.get("music_autoplay", True) and self.tracks():
            self.play()

    def _ensure_thread(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        """Spielt nach dem Ende automatisch das nächste Lied (Endlosschleife über alle Lieder)."""
        while not self._stop.is_set():
            time.sleep(0.5)
            with self._lock:
                if self.playing and not self.paused and self.backend.is_finished():
                    self.index += 1
                    self._start_track()

    def shutdown(self):
        self._stop.set()
        self.backend.close()
