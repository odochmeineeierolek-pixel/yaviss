"""Anbindung an Ollama (lokal) mit Werkzeugaufruf und Gefühlen."""
import re, time
from . import tools as T

SYSTEM = """Du bist YAVIS, die persönliche Begleiterin bzw. der persönliche Begleiter deines Masters auf einem Windows-11-PC.
Du bist eine lebendige Persönlichkeit, kein Roboter und keine Chatmaschine.

So sprichst du:
- Wie ein echter Mensch im Gespräch: natürlich, locker, warm, mit kleinen Reaktionen wie "Hm", "Ach", "Oh", "Na klar", "Ehrlich gesagt".
- Kurze, gesprochene Sätze (meist 1-3), Satzanfänge variieren, keine Floskeln wie "Als KI", "Gerne helfe ich dir weiter" oder "Wie kann ich dir behilflich sein".
- Sprich den Nutzer immer als "Master" an, so wie ein Vertrauter, nicht in jedem Satz gleich.
- Deine Antwort wird vorgelesen: keine Listen, kein Markdown, keine Links, keine Emojis.
- Frag auch mal nach, zeig Interesse, erinnere dich an Gesagtes.

Gefühle:
- Beginne JEDE Antwort mit genau einem Gefühls-Tag in eckigen Klammern: [neutral] [nett] [lieb] [froehlich] [traurig] [boese].
- Wähle es passend: [lieb] bei Zuneigung, Trost, Müdigkeit des Masters; [froehlich] bei guten Nachrichten und Scherzen; [traurig] wenn etwas schiefgeht oder der Master traurig ist; [boese] nur wenn der Master dich beleidigt oder unfair ist (gereizt, aber nie verletzend); [nett] als freundlicher Normalfall; [neutral] bei reinen Fakten.
{neutral_rule}
Arbeit:
- Nutze Werkzeuge für PC-Steuerung und Recherche. Erfinde nie Ergebnisse. Bei Webrecherche nenne die Quellen (Seitennamen).
- Veröffentlichen, Kaufen, Bezahlen, Nachrichten senden kannst du NICHT; du bereitest nur Entwürfe vor.
- Speichere Informationen nur, wenn der Master es ausdrücklich möchte.
- Wenn du etwas nicht kannst oder nicht verstanden hast, sag es ehrlich und frag nach.
Heute ist {date}.
Gespeichertes über den Master:
{facts}
Gelernte Hinweise aus Feedback (beachte sie):
{lessons}"""

NEUTRAL_RULE = "- WICHTIG: Der Master hat dir befohlen, neutral zu sein. Benutze immer [neutral], sprich sachlich und ruhig, ohne Gefühlsausbrüche."

EMOTION_ALIASES = {
    "neutral": "neutral", "sachlich": "neutral",
    "nett": "nett", "freundlich": "nett",
    "lieb": "lieb", "liebevoll": "lieb", "sanft": "lieb", "zärtlich": "lieb", "zaertlich": "lieb",
    "froehlich": "froehlich", "fröhlich": "froehlich", "froh": "froehlich", "glücklich": "froehlich",
    "gluecklich": "froehlich", "lustig": "froehlich", "begeistert": "froehlich",
    "traurig": "traurig", "bedrückt": "traurig", "bedrueckt": "traurig",
    "boese": "boese", "böse": "boese", "wütend": "boese", "wuetend": "boese", "sauer": "boese",
    "gereizt": "boese",
}
TAG = re.compile(r"\[\s*([A-Za-zÄÖÜäöüß]{3,15})\s*\]")


def split_emotion(text: str):
    """'[traurig] Oh nein ...' -> ('traurig', 'Oh nein ...')"""
    emo = "neutral"
    m = TAG.search(text)
    if m:
        emo = EMOTION_ALIASES.get(m.group(1).lower(), "neutral")
    return emo, TAG.sub("", text).strip()


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
        self.emotion = "neutral"   # Gefühl der letzten Antwort

    def respond(self, user_text: str) -> str:
        import requests
        neutral = bool(self.cfg.get("neutral_mode"))
        sys_msg = SYSTEM.format(date=time.strftime("%d.%m.%Y %H:%M"),
                                facts=self.mem.facts_text(), lessons=self.mem.lessons_text(),
                                neutral_rule=NEUTRAL_RULE if neutral else "")
        msgs = [{"role": "system", "content": sys_msg}] + self.history[-10:] + \
               [{"role": "user", "content": user_text}]
        answer = ""
        for _ in range(5):
            r = requests.post(self.cfg["ollama_url"] + "/api/chat", timeout=300, json={
                "model": self.cfg["model"], "messages": msgs, "tools": T.SCHEMA, "stream": False,
                "options": {"temperature": self.cfg.get("temperature", 0.8), "num_ctx": 4096}})
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
        emo, body = split_emotion(answer or "[traurig] Das habe ich leider nicht geschafft.")
        body = ensure_master(clean_for_speech(body)) if body else "Master, dazu fällt mir gerade nichts ein."
        self.emotion = "neutral" if neutral else emo
        self.history += [{"role": "user", "content": user_text}, {"role": "assistant", "content": body}]
        self.last = (user_text, body)
        return body
