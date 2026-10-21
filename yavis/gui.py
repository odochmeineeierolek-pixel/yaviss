"""Oberfläche: schwarz / rot / gelb. Ein großer Kreis in der Mitte atmet mit der Stimme."""
import math, os, queue, random, re, threading, time
import tkinter as tk
import customtkinter as ctk
from . import config, voice
from .app import Assistant
from .orb import Orb, BG, RED, DRED, YEL, TXT, MUTED, FONT

PANEL, BTN = "#141417", "#26262b"
EMO_NAMES = {"Neutral": "neutral", "Nett": "nett", "Lieb": "lieb", "Fröhlich": "froehlich",
             "Traurig": "traurig", "Böse": "boese"}

ctk.set_appearance_mode("dark")


class App(ctk.CTk):
    def __init__(self, cfg, start_hidden=False):
        super().__init__()
        self.cfg = cfg
        self.title("YAVIS")
        self.geometry("1040x720")
        self.minsize(820, 560)
        self.configure(fg_color=BG)
        self.q = queue.Queue()
        self.status = "Startet"
        self.emotion = "neutral"
        self.caption = ""
        self.orb = Orb()
        self.assistant = Assistant(cfg, on_status=lambda s: self.q.put(("status", s)),
                                   on_message=lambda r, t: self.q.put(("msg", (r, t))),
                                   on_emotion=self._set_emotion)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._sidebar()
        self.pages = {"Start": self._home_page(), "Verlauf": self._history_page(), "Musik": self._music_page(),
                      "Gedächtnis": self._memory_page(), "Einstellungen": self._settings_page()}
        self.show_page("Start")
        self.protocol("WM_DELETE_WINDOW", self.withdraw)   # Fenster zu = im Tray weiterlaufen
        self._tray()
        threading.Thread(target=self.assistant.run, daemon=True).start()
        self.after(100, self._poll)
        self.after(50, self._animate)
        self.assistant.music.seed()                       # mitgelieferte Lieder beim ersten Start übernehmen
        self._refresh_tracks()
        self.after(800, self.assistant.music.autoplay)    # Musik startet von selbst (abschaltbar)
        self.after(700, self._music_tick)
        if start_hidden:
            self.after(300, self.withdraw)

    def _set_emotion(self, e):
        self.emotion = e

    # ---------- Layout ----------
    def _btn(self, parent, text, cmd, color=RED, hover="#b3121f", **kw):
        return ctk.CTkButton(parent, text=text, command=cmd, fg_color=color, hover_color=hover,
                             font=ctk.CTkFont(family=FONT, size=14), **kw)

    def _sidebar(self):
        sb = ctk.CTkFrame(self, width=210, corner_radius=0, fg_color=PANEL)
        sb.grid(row=0, column=0, sticky="nsw")
        sb.grid_propagate(False)
        ctk.CTkLabel(sb, text="YAVIS", font=ctk.CTkFont(family=FONT, size=32, weight="bold"),
                     text_color=YEL).pack(pady=(30, 0))
        ctk.CTkFrame(sb, height=3, width=60, fg_color=RED, corner_radius=2).pack(pady=(4, 6))
        ctk.CTkLabel(sb, text="Dein persönlicher Assistent", text_color=MUTED,
                     font=ctk.CTkFont(family=FONT, size=12)).pack(pady=(0, 26))
        self.nav = {}
        for name in ("Start", "Verlauf", "Musik", "Gedächtnis", "Einstellungen"):
            b = ctk.CTkButton(sb, text=name, anchor="w", height=42, fg_color="transparent",
                              hover_color="#2a0f14", text_color=TXT, corner_radius=10,
                              font=ctk.CTkFont(family=FONT, size=15),
                              command=lambda n=name: self.show_page(n))
            b.pack(fill="x", padx=14, pady=3)
            self.nav[name] = b
        ctk.CTkLabel(sb, text="").pack(expand=True)
        ctk.CTkLabel(sb, text="🎵 Musik-Lautstärke", text_color=MUTED,
                     font=ctk.CTkFont(family=FONT, size=12)).pack(anchor="w", padx=18)
        self.s_side_vol = ctk.CTkSlider(sb, from_=0, to=1, width=170, progress_color=RED, button_color=YEL,
                                        command=self._on_volume)
        self.s_side_vol.set(self.cfg.get("music_volume", 0.35))
        self.s_side_vol.pack(padx=14, pady=(2, 14))
        self.s_side_vol.bind("<ButtonRelease-1>", lambda e: config.save(self.cfg))
        self.pause_btn = self._btn(sb, "⏸  Zuhören pausieren", self._toggle_pause, color=BTN, hover="#33333a")
        self.pause_btn.pack(fill="x", padx=14, pady=4)
        self._btn(sb, "⏻  Beenden", lambda: os._exit(0), color=DRED, hover="#991b1b"
                  ).pack(fill="x", padx=14, pady=(4, 20))

    def _page_frame(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.grid(row=0, column=1, sticky="nsew", padx=18, pady=18)
        f.grid_columnconfigure(0, weight=1)
        return f

    def _home_page(self):
        f = self._page_frame()
        f.grid_rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(f, bg=BG, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        bar = ctk.CTkFrame(f, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        bar.grid_columnconfigure(0, weight=1)
        self.entry = ctk.CTkEntry(bar, placeholder_text="Oder schreibe YAVIS etwas …", height=44, corner_radius=22,
                                  fg_color=PANEL, border_color=DRED, text_color=TXT,
                                  font=ctk.CTkFont(family=FONT, size=14))
        self.entry.grid(row=0, column=0, sticky="ew")
        self.entry.bind("<Return>", lambda e: self._send())
        self._btn(bar, "Senden", self._send, width=90, height=44, corner_radius=22
                  ).grid(row=0, column=1, padx=(8, 0))
        self._btn(bar, "🎤", self._mic, color=BTN, hover="#33333a", width=52, height=44, corner_radius=22
                  ).grid(row=0, column=2, padx=(8, 0))
        return f

    def _history_page(self):
        f = self._page_frame()
        f.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(f, text="Verlauf", text_color=YEL, font=ctk.CTkFont(family=FONT, size=22, weight="bold")
                     ).grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.chat = ctk.CTkScrollableFrame(f, corner_radius=14, fg_color=PANEL)
        self.chat.grid(row=1, column=0, sticky="nsew")
        return f

    def _memory_page(self):
        f = self._page_frame()
        f.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(f, text="Was YAVIS über dich weiß", text_color=YEL,
                     font=ctk.CTkFont(family=FONT, size=22, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.mem_list = ctk.CTkScrollableFrame(f, corner_radius=14, fg_color=PANEL)
        self.mem_list.grid(row=1, column=0, sticky="nsew")
        return f

    def _mic_names(self):
        try:
            import sounddevice as sd
            return ["Standard"] + [f"{i}: {d['name']}" for i, d in enumerate(sd.query_devices())
                                   if d["max_input_channels"] > 0]
        except Exception:
            return ["Standard"]

    def _settings_page(self):
        f = self._page_frame()
        f.grid_rowconfigure(0, weight=1)
        sc = ctk.CTkScrollableFrame(f, fg_color="transparent")
        sc.grid(row=0, column=0, sticky="nsew")
        W = 420
        ctk.CTkLabel(sc, text="Einstellungen", text_color=YEL,
                     font=ctk.CTkFont(family=FONT, size=22, weight="bold")).pack(anchor="w", pady=(0, 10))

        def label(t):
            ctk.CTkLabel(sc, text=t, text_color=TXT, font=ctk.CTkFont(family=FONT, size=13, weight="bold")
                         ).pack(anchor="w", pady=(16, 2))

        def hint(t):
            ctk.CTkLabel(sc, text=t, text_color=MUTED, wraplength=520, justify="left",
                         font=ctk.CTkFont(family=FONT, size=12)).pack(anchor="w")

        def menu(values, width=W):
            return ctk.CTkOptionMenu(sc, width=width, values=values, fg_color="#1c1c20",
                                     button_color=RED, button_hover_color="#b3121f", dropdown_fg_color=PANEL)

        def switch(text, var):
            ctk.CTkSwitch(sc, text=text, variable=var, progress_color=RED, button_color=YEL,
                          font=ctk.CTkFont(family=FONT, size=14)).pack(anchor="w", pady=5)

        self.v_speak = ctk.BooleanVar(value=self.cfg.get("speak", True))
        self.v_show = ctk.BooleanVar(value=self.cfg.get("show_text", False))
        self.v_neutral = ctk.BooleanVar(value=self.cfg.get("neutral_mode", False))
        switch("Antworten vorlesen", self.v_speak)
        switch("Antwort als Text unter dem Kreis zeigen", self.v_show)
        switch("Neutral-Modus (keine Gefühle)", self.v_neutral)
        hint("Du kannst auch sagen: „YAVIS, sei neutral“ oder „YAVIS, zeig wieder Gefühle“.")

        label("Aktivierungswörter")
        self.e_wake = ctk.CTkEntry(sc, width=W, fg_color=PANEL, border_color=DRED)
        self.e_wake.insert(0, ", ".join(self.cfg["wake_words"]))
        self.e_wake.pack(anchor="w")
        hint("Mehrere mit Komma trennen, z. B.  yavis, hey yavis, computer. Gilt sofort nach „Speichern“.")
        label("Genauigkeit beim Aktivierungswort (links locker, rechts streng)")
        self.s_fuzzy = ctk.CTkSlider(sc, from_=0.6, to=0.95, width=W, progress_color=RED, button_color=YEL)
        self.s_fuzzy.set(self.cfg.get("wake_fuzzy", 0.78))
        self.s_fuzzy.pack(anchor="w")

        label("Stimme")
        self.voice_keys = {v["label"]: k for k, v in voice.VOICES.items()}
        self.o_voice = menu(list(self.voice_keys), width=520)
        self.o_voice.set(voice.voice_cfg(self.cfg)["label"])
        self.o_voice.pack(anchor="w")
        hint("„offline“ = läuft nur auf deinem PC. „online“ klingt oft natürlicher, schickt den Text aber an Microsoft "
             "(kostenlos, ohne Konto). Ohne Internet nimmt YAVIS automatisch die Offline-Variante.")
        label("Sprechtempo (links schneller, rechts langsamer)")
        self.s_speed = ctk.CTkSlider(sc, from_=0.8, to=1.4, width=W, progress_color=RED, button_color=YEL)
        self.s_speed.set(self.cfg.get("voice_speed", 1.0))
        self.s_speed.pack(anchor="w")
        label("Stimme mit Gefühl testen")
        row = ctk.CTkFrame(sc, fg_color="transparent")
        row.pack(anchor="w")
        self.o_emo = ctk.CTkOptionMenu(row, width=160, values=list(EMO_NAMES), fg_color="#1c1c20",
                                       button_color=RED, button_hover_color="#b3121f", dropdown_fg_color=PANEL)
        self.o_emo.set("Nett")
        self.o_emo.pack(side="left")
        self._btn(row, "Stimme testen", self._test_voice, color=BTN, hover="#33333a", width=180
                  ).pack(side="left", padx=10)

        label("Mikrofon")
        self.o_mic = menu(self._mic_names(), width=520)
        cur = self.cfg.get("mic_device")
        self.o_mic.set("Standard" if cur is None else next(
            (n for n in self._mic_names() if n.startswith(f"{cur}:")), "Standard"))
        self.o_mic.pack(anchor="w")
        label("Spracherkennung (größer = genauer, aber langsamer)")
        self.o_whisper = menu(["tiny", "base", "small", "medium"])
        self.o_whisper.set(self.cfg["whisper_model"])
        self.o_whisper.pack(anchor="w")
        label("KI-Modell (Ollama)")
        self.e_model = ctk.CTkEntry(sc, width=W, fg_color=PANEL, border_color=DRED)
        self.e_model.insert(0, self.cfg["model"])
        self.e_model.pack(anchor="w")

        self._btn(sc, "Speichern", self._save, width=W, height=42).pack(anchor="w", pady=(24, 4))
        self.save_info = ctk.CTkLabel(sc, text="", text_color=MUTED, wraplength=520, justify="left")
        self.save_info.pack(anchor="w")
        return f

    def _apply(self):
        words = [w.strip().lower() for w in re.split(r"[,;\n]", self.e_wake.get()) if w.strip()]
        mic = self.o_mic.get()
        self.cfg.update(
            speak=bool(self.v_speak.get()), show_text=bool(self.v_show.get()),
            neutral_mode=bool(self.v_neutral.get()),
            voice=self.voice_keys.get(self.o_voice.get(), voice.DEFAULT_VOICE),
            voice_speed=round(float(self.s_speed.get()), 2),
            wake_fuzzy=round(float(self.s_fuzzy.get()), 2),
            mic_device=None if mic == "Standard" else int(mic.split(":")[0]),
            model=self.e_model.get().strip() or self.cfg["model"], whisper_model=self.o_whisper.get())
        if words:
            self.cfg["wake_words"] = words

    def _test_voice(self):
        self._apply()
        emo = EMO_NAMES[self.o_emo.get()]

        def run():
            self._set_emotion(emo)
            self.status = "Spricht"
            self.assistant.mouth.say("Hallo Master, so klinge ich. Gefällt dir meine Stimme?", emo)
            self._set_emotion("neutral")
            self.status = "Wartet"
        threading.Thread(target=run, daemon=True).start()
        self.show_page("Start")

    # ---------- Musik ----------
    def _music_page(self):
        f = self._page_frame()
        f.grid_rowconfigure(5, weight=1)
        ctk.CTkLabel(f, text="Musik", text_color=YEL,
                     font=ctk.CTkFont(family=FONT, size=22, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.now_label = ctk.CTkLabel(f, text="", text_color=TXT, anchor="w",
                                      font=ctk.CTkFont(family=FONT, size=15))
        self.now_label.grid(row=1, column=0, sticky="w", pady=(0, 10))
        ctl = ctk.CTkFrame(f, fg_color="transparent")
        ctl.grid(row=2, column=0, sticky="w")
        self._btn(ctl, "⏮", lambda: (self.assistant.music.prev(), self._music_tick(once=True)),
                  color=BTN, hover="#33333a", width=56, height=44).pack(side="left")
        self.play_btn = self._btn(ctl, "▶", lambda: (self.assistant.music.toggle(), self._music_tick(once=True)),
                                  width=70, height=44)
        self.play_btn.pack(side="left", padx=8)
        self._btn(ctl, "⏭", lambda: (self.assistant.music.next(), self._music_tick(once=True)),
                  color=BTN, hover="#33333a", width=56, height=44).pack(side="left")
        vol = ctk.CTkFrame(f, fg_color="transparent")
        vol.grid(row=3, column=0, sticky="w", pady=(16, 0))
        ctk.CTkLabel(vol, text="Lautstärke", text_color=TXT, font=ctk.CTkFont(family=FONT, size=13, weight="bold")
                     ).pack(side="left", padx=(0, 12))
        self.s_music_vol = ctk.CTkSlider(vol, from_=0, to=1, width=300, progress_color=RED, button_color=YEL,
                                         command=self._on_volume)
        self.s_music_vol.set(self.cfg.get("music_volume", 0.35))
        self.s_music_vol.pack(side="left")
        self.s_music_vol.bind("<ButtonRelease-1>", lambda e: config.save(self.cfg))
        self.vol_pct = ctk.CTkLabel(vol, text=f"{int(self.cfg.get('music_volume', 0.35) * 100)} %", text_color=YEL, width=50)
        self.vol_pct.pack(side="left", padx=8)
        opts = ctk.CTkFrame(f, fg_color="transparent")
        opts.grid(row=4, column=0, sticky="w", pady=(12, 8))
        self.v_autoplay = ctk.BooleanVar(value=self.cfg.get("music_autoplay", True))
        self.v_duck = ctk.BooleanVar(value=self.cfg.get("music_duck", True))
        for text, var, key in (("Beim Start automatisch abspielen", self.v_autoplay, "music_autoplay"),
                               ("Leiser, wenn YAVIS spricht oder zuhört", self.v_duck, "music_duck")):
            ctk.CTkSwitch(opts, text=text, variable=var, progress_color=RED, button_color=YEL,
                          font=ctk.CTkFont(family=FONT, size=14),
                          command=lambda v=var, k=key: self._music_opt(k, v)).pack(anchor="w", pady=3)
        box = ctk.CTkFrame(f, fg_color="transparent")
        box.grid(row=5, column=0, sticky="nsew")
        box.grid_columnconfigure(0, weight=1)
        box.grid_rowconfigure(1, weight=1)
        self._btn(box, "＋  Musik hinzufügen …", self._music_add, height=42).grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.track_list = ctk.CTkScrollableFrame(box, corner_radius=14, fg_color=PANEL)
        self.track_list.grid(row=1, column=0, sticky="nsew")
        ctk.CTkLabel(f, text="Tipp: Mit Kopfhörer versteht YAVIS dich am besten – laute Musik über Lautsprecher "
                             "kann das Zuhören stören. Auch per Sprache: „YAVIS, Musik aus“, „Musik leiser“, "
                             "„nächstes Lied“.", text_color=MUTED, wraplength=640, justify="left",
                     font=ctk.CTkFont(family=FONT, size=12)).grid(row=6, column=0, sticky="w", pady=(8, 0))
        return f

    def _on_volume(self, v):
        self.assistant.music.set_volume(v)
        for name in ("s_side_vol", "s_music_vol"):
            w = getattr(self, name, None)
            if w is not None and abs(w.get() - v) > 0.005:
                w.set(v)
        if hasattr(self, "vol_pct"):
            self.vol_pct.configure(text=f"{int(v * 100)} %")

    def _music_opt(self, key, var):
        self.cfg[key] = bool(var.get())
        config.save(self.cfg)

    def _music_add(self):
        from tkinter import filedialog
        paths = filedialog.askopenfilenames(
            title="Musik auswählen", filetypes=[("Musik", "*.mp3 *.wav *.wma *.m4a *.aac"), ("Alle Dateien", "*.*")])
        if paths:
            self.assistant.music.add(paths)
            self._refresh_tracks()

    def _refresh_tracks(self):
        for w in self.track_list.winfo_children():
            w.destroy()
        tracks = self.assistant.music.tracks()
        if not tracks:
            ctk.CTkLabel(self.track_list, text="Noch keine Musik. Klicke auf „Musik hinzufügen“ (MP3, WAV, WMA, M4A).",
                         text_color=MUTED).pack(pady=20)
        for i, t in enumerate(tracks):
            row = ctk.CTkFrame(self.track_list, corner_radius=10, fg_color="#1c1c20")
            row.pack(fill="x", pady=3, padx=4)
            ctk.CTkLabel(row, text=t.stem.replace("_", " "), anchor="w", text_color=TXT
                         ).pack(side="left", padx=12, pady=8)
            self._btn(row, "Löschen", lambda name=t.name: (self.assistant.music.remove(name), self._refresh_tracks()),
                      color=DRED, hover="#991b1b", width=70).pack(side="right", padx=6)
            self._btn(row, "▶", lambda idx=i: (self.assistant.music.play(idx), self._music_tick(once=True)),
                      color=BTN, hover="#33333a", width=40).pack(side="right")

    def _music_tick(self, once=False):
        m = self.assistant.music
        name = m.current_name()
        if not name:
            txt = "Keine Musik vorhanden"
        elif m.playing and not m.paused:
            txt = "Es läuft: " + name.rsplit(".", 1)[0].replace("_", " ")
        else:
            txt = "Pausiert: " + name.rsplit(".", 1)[0].replace("_", " ")
        self.now_label.configure(text=txt)
        self.play_btn.configure(text="⏸" if (m.playing and not m.paused) else "▶")
        if not once:
            self.after(700, self._music_tick)

    # ---------- Verhalten ----------
    def show_page(self, name):
        for n, fr in self.pages.items():
            fr.grid_remove()
            self.nav[n].configure(fg_color=RED if n == name else "transparent")
        self.pages[name].grid()
        if name == "Gedächtnis":
            self._refresh_memory()

    def _bubble(self, role, text):
        mine = role == "user"
        row = ctk.CTkFrame(self.chat, fg_color="transparent")
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(row, text=text, wraplength=520, justify="left", anchor="w", text_color=TXT,
                     fg_color="#3a1016" if mine else "#2b2410", corner_radius=14,
                     padx=14, pady=10).pack(side="right" if mine else "left", padx=6)
        ctk.CTkLabel(row, text=time.strftime("%H:%M"), text_color=MUTED,
                     font=ctk.CTkFont(size=10)).pack(side="right" if mine else "left", padx=2, anchor="s")
        self.after(60, lambda: self.chat._parent_canvas.yview_moveto(1.0))

    def _poll(self):
        try:
            while True:
                kind, data = self.q.get_nowait()
                if kind == "status":
                    self.status = data
                elif kind == "msg":
                    role, text = data
                    self._bubble(role, text)
                    if role == "yavis":
                        self.caption = text
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _animate(self):
        """Zeichnet den Kreis ~30x pro Sekunde: Größe = Lautstärke, Farbe/Tempo = Gefühl."""
        c = self.canvas
        w, h = c.winfo_width(), c.winfo_height()
        if w < 60 or h < 60 or not c.winfo_ismapped():
            self.after(80, self._animate)
            return
        st = self.status
        if st.startswith("Spricht"):
            lv = self.assistant.mouth.level
        elif st.startswith("Hört"):
            lv = self.assistant.ears.level
        elif st.startswith("Wartet"):
            lv = self.assistant.ears.level * 0.45
        else:
            lv = 0.0
        self.orb.draw(c, w, h, st, self.emotion, lv, self.caption, bool(self.cfg.get("show_text")))
        self.after(33, self._animate)

    def _send(self):
        t = self.entry.get().strip()
        if t:
            self.entry.delete(0, "end")
            threading.Thread(target=self.assistant.handle, args=(t,), daemon=True).start()

    def _mic(self):
        self.assistant.force_listen = True
        self.assistant.paused = False
        self.status = "Hört zu"

    def _toggle_pause(self):
        self.assistant.paused = not self.assistant.paused
        self.pause_btn.configure(text="▶  Zuhören fortsetzen" if self.assistant.paused else "⏸  Zuhören pausieren")

    def _refresh_memory(self):
        for w in self.mem_list.winfo_children():
            w.destroy()
        facts = self.assistant.mem.all_facts()
        if not facts:
            ctk.CTkLabel(self.mem_list, text="Noch nichts gespeichert. Sage z. B. „YAVIS, merk dir, dass …“",
                         text_color=MUTED).pack(pady=20)
        for k, v in facts:
            row = ctk.CTkFrame(self.mem_list, corner_radius=10, fg_color="#1c1c20")
            row.pack(fill="x", pady=4, padx=4)
            ctk.CTkLabel(row, text=f"{k}: {v}", wraplength=480, justify="left", anchor="w", text_color=TXT
                         ).pack(side="left", padx=12, pady=8)
            self._btn(row, "Löschen", lambda key=k: (self.assistant.mem.forget(key), self._refresh_memory()),
                      color=DRED, hover="#991b1b", width=70).pack(side="right", padx=8)

    def _save(self):
        self._apply()
        config.save(self.cfg)
        self.save_info.configure(text="Gespeichert. Stimme, Gefühle und Aktivierungswörter gelten sofort; "
                                      "KI-Modell und Spracherkennung nach einem Neustart von YAVIS.")

    def _tray(self):
        try:
            import pystray
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (64, 64), BG)
            d = ImageDraw.Draw(img)
            d.ellipse((6, 6, 58, 58), outline=RED, width=5)
            d.ellipse((20, 20, 44, 44), fill=YEL)
            menu = pystray.Menu(
                pystray.MenuItem("YAVIS öffnen", lambda i, _: self.after(0, self._restore), default=True),
                pystray.MenuItem("Beenden", lambda i, _: os._exit(0)))
            pystray.Icon("YAVIS", img, "YAVIS läuft", menu).run_detached()
        except Exception:
            pass

    def _restore(self):
        self.deiconify()
        self.lift()
        self.focus_force()
