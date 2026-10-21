"""Anbindung an Ollama (lokal) mit Werkzeugaufruf."""
import re, time
from . import tools as T

SYSTEM = """Du bist YAVIS, der persönliche Sprachassistent auf einem Windows-11-PC.
Regeln:
- Sprich Deutsch, warm, freundlich, kurz (1-3 Sätze). Sprich den Nutzer IMMER mit "Master" an.
- Deine Antwort wird vorgelesen: keine Listen, kein Markdown, keine URLs vorlesen.
- Nutze Werkzeuge für PC-Steuerung und Recherche. Erfinde nie Ergebnisse. Bei Webrecherche nenne die Quellen.
- Veröffentlichen, Kaufen, Bezahlen, Nachrichten senden kannst du NICHT; du bereitest nur Entwürfe vor.
- Speichere Informationen nur, wenn der Master es ausdrücklich möchte.
- Wenn du etwas nicht kannst, sag es ehrlich.
Heute ist {date}.
Gespeichertes über den Master:
{facts}
Gelernte Hinweise aus Feedback (beachte sie):
{lessons}"""


def clean_for_speech(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[*_#`>~]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def ensure_master(text: str) -> str:
    return text if "master" in text.lower() else f"Master, {text}"


class Brain:
    def __init__(self, cfg, mem, tools):
        self.cfg, self.mem, self.tools = cfg, mem, tools
        self.history = []
        self.last = ("", "")

    def respond(self, user_text: str) -> str:
        import requests
        sys_msg = SYSTEM.format(date=time.strftime("%d.%m.%Y %H:%M"),
                                facts=self.mem.facts_text(), lessons=self.mem.lessons_text())
        msgs = [{"role": "system", "content": sys_msg}] + self.history[-8:] + \
               [{"role": "user", "content": user_text}]
        answer = ""
        for _ in range(5):
            r = requests.post(self.cfg["ollama_url"] + "/api/chat", timeout=300, json={
                "model": self.cfg["model"], "messages": msgs, "tools": T.SCHEMA, "stream": False})
            r.raise_for_status()
            m = r.json()["message"]
            msgs.append(m)
            calls = m.get("tool_calls") or []
            if not calls:
                answer = m.get("content", "")
                break
            for c in calls:
                f = c["function"]
                msgs.append({"role": "tool", "tool_name": f["name"],
                             "content": self.tools.dispatch(f["name"], f.get("arguments"))})
        answer = ensure_master(clean_for_speech(answer or "Das habe ich leider nicht geschafft."))
        self.history += [{"role": "user", "content": user_text}, {"role": "assistant", "content": answer}]
        self.last = (user_text, answer)
        return answer
