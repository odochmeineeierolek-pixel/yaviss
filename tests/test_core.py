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
