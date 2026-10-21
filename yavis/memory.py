"""Lokales, dauerhaftes Gedächtnis (SQLite). Nichts verlässt den Rechner."""
import sqlite3, time
from pathlib import Path


class Memory:
    def __init__(self, path: Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS facts(key TEXT PRIMARY KEY, value TEXT, ts REAL);
        CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY, ts REAL,
            user_text TEXT, answer TEXT, rating INTEGER, note TEXT);
        """)
        self.db.commit()

    def remember(self, key: str, value: str):
        self.db.execute("INSERT OR REPLACE INTO facts VALUES(?,?,?)",
                        (key.strip().lower(), value.strip(), time.time()))
        self.db.commit()

    def forget(self, key: str) -> bool:
        cur = self.db.execute("DELETE FROM facts WHERE key=?", (key.strip().lower(),))
        self.db.commit()
        return cur.rowcount > 0

    def all_facts(self):
        return self.db.execute("SELECT key,value FROM facts ORDER BY ts DESC").fetchall()

    def facts_text(self) -> str:
        rows = self.db.execute("SELECT key,value FROM facts ORDER BY ts DESC LIMIT 50").fetchall()
        return "\n".join(f"- {k}: {v}" for k, v in rows) or "(noch nichts gespeichert)"

    def add_feedback(self, user_text: str, answer: str, rating: int, note: str = ""):
        self.db.execute("INSERT INTO feedback(ts,user_text,answer,rating,note) VALUES(?,?,?,?,?)",
                        (time.time(), user_text, answer, rating, note))
        self.db.commit()

    def lessons_text(self, n: int = 6) -> str:
        rows = self.db.execute(
            "SELECT rating,user_text,answer,note FROM feedback ORDER BY ts DESC LIMIT ?", (n,)).fetchall()
        out = []
        for rating, u, a, note in rows:
            tag = "GUT" if rating > 0 else "SCHLECHT"
            out.append(f"- [{tag}] Frage: {u[:100]} | Antwort: {a[:100]} | Hinweis: {note[:150]}")
        return "\n".join(out) or "(noch kein Feedback)"
