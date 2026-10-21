"""Der bewegte Kreis. Reine Zeichenlogik (kein Tkinter nötig) – dadurch testbar."""
import math, random

BG, RED, DRED, YEL = "#0b0b0d", "#e11d2e", "#7a0f19", "#ffc400"
TXT, MUTED = "#f4f4f5", "#8b8b92"
FONT = "Segoe UI"

# Gefühl -> Farben/Bewegung des Kreises
EMO_STYLE = {
    "neutral":   dict(core="#ffc400", ring="#e11d2e", speed=1.0, jitter=0.0, amp=1.0),
    "nett":      dict(core="#ffcf33", ring="#e8392b", speed=1.0, jitter=0.0, amp=1.0),
    "lieb":      dict(core="#ffb84d", ring="#ff5a6a", speed=0.6, jitter=0.0, amp=0.85),
    "froehlich": dict(core="#ffe14d", ring="#ff2a3c", speed=1.7, jitter=0.0, amp=1.3),
    "traurig":   dict(core="#8a6d00", ring="#5a0a12", speed=0.4, jitter=0.0, amp=0.6),
    "boese":     dict(core="#e11d2e", ring="#ffc400", speed=2.4, jitter=7.0, amp=1.4),
}


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def hexc(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(v))) for v in c)


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


class Orb:
    def __init__(self):
        self.phase, self.lv, self.r = 0.0, 0.0, 0.0
        self.core_c, self.ring_c = rgb(YEL), rgb(RED)

    def draw(self, c, w, h, status, emotion, level, caption="", show_caption=False):
        """Zeichnet einen Frame auf ein Canvas-ähnliches Objekt (create_oval/arc/text, delete)."""
        sty = EMO_STYLE.get(emotion, EMO_STYLE["neutral"])
        speaking, hearing = status.startswith("Spricht"), status.startswith("Hört")
        thinking = status.startswith(("Denkt", "Richtet", "Startet"))
        paused = status.startswith("Pausiert")

        tc, tr = rgb(sty["core"]), rgb(sty["ring"])
        if paused:
            tc, tr = mix(tc, (70, 70, 70), 0.7), mix(tr, (50, 50, 50), 0.7)
        self.core_c, self.ring_c = mix(self.core_c, tc, 0.12), mix(self.ring_c, tr, 0.12)
        self.phase += 0.033 * sty["speed"]
        self.lv += (level - self.lv) * 0.5

        base = min(w, h * 0.9) * 0.15
        breathe = math.sin(self.phase * 2.0) * (0.03 if paused else 0.05)
        target = base * (1 + breathe + 0.6 * self.lv * sty["amp"])
        if self.r == 0:
            self.r = target
        self.r += (target - self.r) * 0.5
        r = self.r + (random.random() * sty["jitter"] if (speaking and sty["jitter"]) else 0)
        cx, cy = w / 2, h * 0.45
        core, ring, bg = self.core_c, self.ring_c, rgb(BG)

        c.delete("all")
        for i in (3, 2, 1):                                   # weiche Ringe
            rr = min(r * (1.16 + 0.2 * i) + self.lv * base * 0.3 * i, min(w, h) * 0.5 - 6)
            c.create_oval(cx - rr, cy - rr, cx + rr, cy + rr,
                          outline=hexc(mix(ring, bg, 0.25 + 0.22 * i)), width=3)
        spin = self.phase * (260 if thinking else 40)         # kreisende Bögen
        R2 = base * 2.0
        for k in range(3):
            c.create_arc(cx - R2, cy - R2, cx + R2, cy + R2, start=(spin + k * 120) % 360,
                         extent=55 if thinking else 30, style="arc",
                         outline=hexc(mix(core, bg, 0.15)), width=4)
        c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=hexc(ring),
                      outline=hexc(mix(ring, (255, 255, 255), 0.2)), width=2)
        r2 = r * 0.84
        c.create_oval(cx - r2, cy - r2, cx + r2, cy + r2, fill=hexc(core), outline="")
        r3 = r * 0.5
        c.create_oval(cx - r3, cy - r3, cx + r3, cy + r3, fill=hexc(mix(core, (255, 255, 255), 0.4)), outline="")

        col = YEL if (speaking or hearing) else (RED if thinking else MUTED)
        y = cy + base * 3.0
        c.create_text(cx, y, text=status or "Bereit", fill=col, font=(FONT, 14))
        if show_caption and caption:
            c.create_text(cx, y + 34, text=caption, fill=TXT, font=(FONT, 15), anchor="n",
                          width=max(240, min(w - 80, 680)), justify="center")
