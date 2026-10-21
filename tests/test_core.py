import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from pathlib import Path
from yavis.memory import Memory
from yavis.tools import Tools, SCHEMA
from yavis.brain import ensure_master, clean_for_speech
from yavis.speech import split_wake
from yavis import config


class Core(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mem = Memory(Path(self.tmp) / "m.db")
        self.cfg = config.DEFAULTS.copy()
        self.confirmed = None
        self.tools = Tools(self.cfg, self.mem, lambda q: self.confirmed)

    def test_memory_persist(self):
        self.mem.remember("Lieblingsfarbe", "Blau")
        self.assertIn("blau", Memory(Path(self.tmp) / "m.db").facts_text().lower())
        self.assertTrue(self.mem.forget("lieblingsfarbe"))

    def test_feedback_lessons(self):
        self.mem.add_feedback("Wetter?", "Sonnig", -1, "zu lang")
        self.assertIn("SCHLECHT", self.mem.lessons_text())

    def test_wake_word(self):
        self.assertEqual(split_wake("Yavis, öffne den Rechner", self.cfg["wake_words"]), (True, "öffne den rechner"))
        self.assertFalse(split_wake("Guten Morgen", self.cfg["wake_words"])[0])

    def test_master(self):
        self.assertTrue(ensure_master("Es ist 12 Uhr.").startswith("Master"))
        self.assertEqual(ensure_master("Gerne, Master."), "Gerne, Master.")
        self.assertNotIn("http", clean_for_speech("Siehe https://x.de **fett**"))

    def test_app_allowlist(self):
        self.assertIn("nicht freigegeben", self.tools.dispatch("open_app", {"name": "virus.exe"}))

    def test_blocked_keys(self):
        self.assertIn("gesperrt", self.tools.dispatch("press_keys", {"keys": "alt+f4"}))

    def test_delete_needs_confirmation(self):
        f = Path.home() / "yavis_test_delete.txt"
        f.write_text("x")
        try:
            self.confirmed = False
            self.assertIn("Abgebrochen", self.tools.dispatch("delete_file", {"path": str(f)}))
            self.assertTrue(f.exists())
            self.assertIn("gesperrt", self.tools.dispatch("delete_file", {"path": "/etc/passwd"}))
        finally:
            f.unlink(missing_ok=True)

    def test_draft_publishes_nothing(self):
        r = self.tools.dispatch("save_draft", {"title": "Test", "text": "Angebot"})
        self.assertIn("nichts veröffentlicht", r)

    def test_voice_only_by_default(self):
        self.assertTrue(config.DEFAULTS["speak"])
        self.assertFalse(config.DEFAULTS["show_text"])

    def test_schema_matches_tools(self):
        for t in SCHEMA:
            self.assertTrue(hasattr(Tools, "t_" + t["function"]["name"]))


class AssistantLogic(unittest.TestCase):
    def setUp(self):
        from yavis.app import Assistant
        self.cfg = dict(config.DEFAULTS, speak=False)
        self.msgs = []
        self.a = Assistant(self.cfg, on_message=lambda r, t: self.msgs.append((r, t)),
                           mem_path=Path(tempfile.mkdtemp()) / "m.db")
        self.a.brain.respond = lambda t: "Hallo Master"
        self.a.brain.last = ("Frage", "Antwort")

    def test_reply_shown_without_speaking(self):
        self.assertTrue(self.a.handle("wie geht es dir"))
        self.assertEqual(self.msgs, [("user", "wie geht es dir"), ("yavis", "Hallo Master")])

    def test_feedback_and_quit(self):
        self.a.handle("das war falsch weil zu lang")
        self.assertIn("SCHLECHT", self.a.mem.lessons_text())
        self.assertFalse(self.a.handle("beenden"))


class Feelings(unittest.TestCase):
    def test_emotion_tag(self):
        from yavis.brain import split_emotion
        self.assertEqual(split_emotion("[traurig] Oh nein, Master."), ("traurig", "Oh nein, Master."))
        self.assertEqual(split_emotion("[Böse] Das war frech."), ("boese", "Das war frech."))
        self.assertEqual(split_emotion("Ohne Tag."), ("neutral", "Ohne Tag."))
        self.assertEqual(split_emotion("[quatsch] Hallo")[0], "neutral")

    def test_fuzzy_wake_and_custom_words(self):
        self.assertTrue(split_wake("Yavis öffne den Rechner", ["yavis"])[0])
        self.assertTrue(split_wake("Jarvis, wie spät ist es", ["yavis", "jarvis"])[0])
        self.assertTrue(split_wake("Yavies mach Licht an", ["yavis"])[0])      # kleiner Hörfehler
        self.assertEqual(split_wake("hey computer wie spät", ["hey computer"]), (True, "wie spät"))
        self.assertFalse(split_wake("das Wetter ist schön heute", ["yavis"])[0])

    def test_neutral_mode_commands(self):
        from yavis.app import Assistant
        cfg = dict(config.DEFAULTS, speak=False)
        a = Assistant(cfg, mem_path=Path(tempfile.mkdtemp()) / "m.db")
        a.save_cfg = lambda c: None
        a.brain.respond = lambda t: "Hallo Master"
        a.handle("sei neutral")
        self.assertTrue(cfg["neutral_mode"])
        a.handle("zeig wieder Gefühle")
        self.assertFalse(cfg["neutral_mode"])

    def test_emotion_forced_neutral(self):
        from yavis.app import Assistant
        cfg = dict(config.DEFAULTS, speak=False, neutral_mode=True)
        seen = []
        a = Assistant(cfg, on_emotion=seen.append, mem_path=Path(tempfile.mkdtemp()) / "m.db")
        a.say("Test", "boese")
        self.assertEqual(seen[0], "neutral")


class Music(unittest.TestCase):
    def setUp(self):
        from yavis.music import MusicPlayer, NullBackend
        self.tmp = Path(tempfile.mkdtemp())
        self.src = self.tmp / "src"
        self.src.mkdir()
        for n in ("a.mp3", "b.mp3", "c.txt"):
            (self.src / n).write_bytes(b"x")
        self.cfg = dict(config.DEFAULTS)
        self.be = NullBackend()
        self.m = MusicPlayer(self.cfg, self.be, folder=self.tmp / "music")

    def test_add_only_music_files(self):
        self.assertEqual(self.m.add(list(self.src.iterdir())), 2)
        self.assertEqual([t.name for t in self.m.tracks()], ["a.mp3", "b.mp3"])
        self.assertEqual(self.m.add(list(self.src.iterdir())), 0)       # keine Doppelten

    def test_play_volume_duck(self):
        self.m.add(list(self.src.iterdir()))
        self.cfg["music_volume"] = 0.8
        self.assertTrue(self.m.play())
        self.assertTrue(self.be.playing)
        self.assertAlmostEqual(self.be.volume, 0.8)
        self.m.duck(True)
        self.assertAlmostEqual(self.be.volume, 0.2)                      # 25 % beim Sprechen
        self.m.duck(False)
        self.assertAlmostEqual(self.be.volume, 0.8)
        self.m.set_volume(1.7)                                          # wird begrenzt
        self.assertEqual(self.cfg["music_volume"], 1.0)
        self.cfg["music_duck"] = False
        self.m.duck(True)
        self.assertAlmostEqual(self.be.volume, 1.0)                      # Ducking abgeschaltet
        self.m.shutdown()

    def test_next_wraps_and_pause(self):
        self.m.add(list(self.src.iterdir()))
        self.m.play()
        self.m.next(); self.m.next()
        self.assertEqual(self.m.current_name(), "a.mp3")                 # nach dem letzten wieder von vorn
        self.m.pause()
        self.assertFalse(self.be.playing)
        self.m.play()
        self.assertTrue(self.be.playing)
        self.m.shutdown()

    def test_remove_and_empty(self):
        self.assertFalse(self.m.play())                                  # ohne Lieder nichts
        self.m.add(list(self.src.iterdir()))
        self.assertTrue(self.m.remove("a.mp3"))
        self.assertFalse(self.m.remove("../src/c.txt"))                  # nichts außerhalb des Ordners
        self.assertEqual(len(self.m.tracks()), 1)

    def test_seed_once(self):
        cfg = dict(config.DEFAULTS, music_seeded=False)
        from yavis.music import MusicPlayer, NullBackend
        m = MusicPlayer(cfg, NullBackend(), folder=self.tmp / "m2")
        import yavis.music as mm
        mm.config.save = lambda c: None
        m.seed(self.src)
        self.assertEqual(len(m.tracks()), 2)
        self.assertTrue(cfg["music_seeded"])

    def test_voice_commands(self):
        from yavis.app import Assistant
        cfg = dict(config.DEFAULTS, speak=False)
        a = Assistant(cfg, mem_path=self.tmp / "m.db")
        a.save_cfg = lambda c: None
        from yavis.music import MusicPlayer
        a.music = MusicPlayer(cfg, self.be, folder=self.tmp / "music")
        a.music.add(list(self.src.iterdir()))
        called = []
        a.brain.respond = lambda t: called.append(t) or "Hallo Master"
        a.handle("YAVIS mach die Musik an")
        self.assertTrue(self.be.playing)
        a.handle("Musik leiser")
        self.assertAlmostEqual(cfg["music_volume"], 0.20)
        a.handle("Musik aus")
        self.assertFalse(self.be.playing)
        a.handle("welche Musik magst du")                                # normales Gespräch geht ans Sprachmodell
        self.assertEqual(called, ["welche Musik magst du"])
        a.music.shutdown()


class VoiceCatalog(unittest.TestCase):
    def test_catalog_is_consistent(self):
        from yavis import voice
        self.assertIn(voice.DEFAULT_VOICE, voice.VOICES)
        for k, v in voice.VOICES.items():
            self.assertIn(v["piper"], voice.PIPER_VOICES, k)      # jede Stimme hat eine Offline-Variante
            if v["engine"] == "edge":
                self.assertTrue(v["edge"].startswith("de-DE-"))
        for e in ("neutral", "nett", "lieb", "froehlich", "traurig", "boese"):
            self.assertIn(e, voice.EMOTIONS)

    def test_pitch_volume_and_envelope(self):
        import wave, numpy as np
        from yavis import voice
        p = os.path.join(tempfile.mkdtemp(), "t.wav")
        t = np.linspace(0, 1, 22050, endpoint=False)
        pcm = (np.sin(2 * np.pi * 220 * t) * 12000 * np.minimum(1, t * 4)).astype(np.int16)
        with wave.open(p, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050); w.writeframes(pcm.tobytes())
        voice.postprocess(p, pitch=0.9, vol=0.5)
        with wave.open(p, "rb") as w:
            self.assertEqual(w.getframerate(), int(22050 * 0.9))     # tiefer = langsamere Abspielrate
        env, dur = voice.envelope(p)
        self.assertTrue(0 <= env.min() and env.max() <= 1 and dur > 1.0)


class VoiceTests(unittest.TestCase):
    def test_urls(self):
        from yavis import voice
        for n in voice.PIPER_VOICES:
            onnx, js = voice.voice_urls(n)
            self.assertTrue(onnx.startswith("https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/"))
            self.assertTrue(js.endswith(".onnx.json"))

    def test_fallback_to_sapi(self):
        from yavis import voice
        from yavis.speech import Mouth
        voice.ensure_piper = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline"))
        m = Mouth(dict(config.DEFAULTS))
        called = []
        m._sapi = lambda t: called.append(t)
        m.say("Hallo Master")
        self.assertEqual(called, ["Hallo Master"])


if __name__ == "__main__":
    unittest.main()
