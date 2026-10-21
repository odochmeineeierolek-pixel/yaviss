"""Moderne Oberfläche (customtkinter): Chat mit Text, Status, Gedächtnis, Einstellungen."""
import os, queue, threading, time
import customtkinter as ctk
from . import config
from .app import Assistant

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ACCENT = "#4cc9f0"
STATUS_COLORS = {"Wartet": "#4ade80", "Hört": "#facc15", "Denkt": "#fb923c",
                 "Spricht": "#4cc9f0", "Pausiert": "#9ca3af", "Fehler": "#f87171", "Startet": "#9ca3af"}


class App(ctk.CTk):
    def __init__(self, cfg, start_hidden=False):
        super().__init__()
        self.cfg = cfg
        self.title("YAVIS")
        self.geometry("980x680")
        self.minsize(760, 520)
        self.q = queue.Queue()
        self.assistant = Assistant(cfg, on_status=lambda s: self.q.put(("status", s)),
                                   on_message=lambda r, t: self.q.put(("msg", (r, t))))
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._sidebar()
        self.pages = {"Chat": self._chat_page(), "Gedächtnis": self._memory_page(),
                      "Einstellungen": self._settings_page()}
        self.show_page("Chat")
        self.protocol("WM_DELETE_WINDOW", self.withdraw)   # Fenster zu = im Tray weiterlaufen
        self._tray()
        threading.Thread(target=self.assistant.run, daemon=True).start()
        self.after(100, self._poll)
        if start_hidden:
            self.after(300, self.withdraw)

    # ---------- Layout ----------
    def _sidebar(self):
        sb = ctk.CTkFrame(self, width=210, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsw")
        sb.grid_propagate(False)
        ctk.CTkLabel(sb, text="YAVIS", font=ctk.CTkFont(size=30, weight="bold"),
                     text_color=ACCENT).pack(pady=(28, 2))
        ctk.CTkLabel(sb, text="Dein persönlicher Assistent", text_color="gray").pack(pady=(0, 18))
        self.status_dot = ctk.CTkLabel(sb, text="● Startet", font=ctk.CTkFont(size=14), text_color="#9ca3af")
        self.status_dot.pack(pady=(0, 20))
        self.nav = {}
        for name in ("Chat", "Gedächtnis", "Einstellungen"):
            b = ctk.CTkButton(sb, text=name, anchor="w", height=40, fg_color="transparent",
                              hover_color="#26324a", command=lambda n=name: self.show_page(n))
            b.pack(fill="x", padx=14, pady=3)
            self.nav[name] = b
        ctk.CTkLabel(sb, text="").pack(expand=True)
        self.pause_btn = ctk.CTkButton(sb, text="⏸  Zuhören pausieren", command=self._toggle_pause,
                                       fg_color="#334155")
        self.pause_btn.pack(fill="x", padx=14, pady=4)
        ctk.CTkButton(sb, text="⏻  Beenden", fg_color="#7f1d1d", hover_color="#991b1b",
                      command=lambda: os._exit(0)).pack(fill="x", padx=14, pady=(4, 18))

    def _page_frame(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.grid(row=0, column=1, sticky="nsew", padx=18, pady=18)
        f.grid_columnconfigure(0, weight=1)
        return f

    def _chat_page(self):
        f = self._page_frame()
        f.grid_rowconfigure(0, weight=1)
        self.chat = ctk.CTkScrollableFrame(f, corner_radius=14)
        self.chat.grid(row=0, column=0, sticky="nsew")
        bar = ctk.CTkFrame(f, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        bar.grid_columnconfigure(0, weight=1)
        self.entry = ctk.CTkEntry(bar, placeholder_text="Schreibe YAVIS einen Befehl …", height=44,
                                  corner_radius=22)
        self.entry.grid(row=0, column=0, sticky="ew")
        self.entry.bind("<Return>", lambda e: self._send())
        ctk.CTkButton(bar, text="Senden", width=90, height=44, corner_radius=22,
                      command=self._send).grid(row=0, column=1, padx=(8, 0))
        ctk.CTkButton(bar, text="🎤", width=52, height=44, corner_radius=22, fg_color="#334155",
                      command=self._mic).grid(row=0, column=2, padx=(8, 0))
        return f

    def _memory_page(self):
        f = self._page_frame()
        f.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(f, text="Was YAVIS über dich weiß", font=ctk.CTkFont(size=20, weight="bold")
                     ).grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.mem_list = ctk.CTkScrollableFrame(f, corner_radius=14)
        self.mem_list.grid(row=1, column=0, sticky="nsew")
        return f

    def _settings_page(self):
        from . import voice
        f = self._page_frame()
        f.grid_rowconfigure(0, weight=1)
        sc = ctk.CTkScrollableFrame(f, fg_color="transparent")
        sc.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(sc, text="Einstellungen", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(0, 12))
        self.v_speak = ctk.BooleanVar(value=self.cfg.get("speak", True))
        self.v_show = ctk.BooleanVar(value=self.cfg.get("show_text", True))
        ctk.CTkSwitch(sc, text="Antworten vorlesen", variable=self.v_speak).pack(anchor="w", pady=5)
        ctk.CTkSwitch(sc, text="Antworten als Text anzeigen", variable=self.v_show).pack(anchor="w", pady=5)

        def label(t): ctk.CTkLabel(sc, text=t).pack(anchor="w", pady=(14, 0))
        label("Stimme")
        self.o_engine = ctk.CTkOptionMenu(sc, width=360, values=[
            "piper – lokal & offline", "edge – sehr natürlich (online)", "sapi – Windows-Notfallstimme"])
        self.o_engine.set({"piper": "piper – lokal & offline", "edge": "edge – sehr natürlich (online)",
                           "sapi": "sapi – Windows-Notfallstimme"}[self.cfg.get("voice_engine", "piper")])
        self.o_engine.pack(anchor="w")
        label("Piper-Stimme (weiblich)")
        self.o_piper = ctk.CTkOptionMenu(sc, width=360, values=list(voice.PIPER_VOICES))
        self.o_piper.set(self.cfg.get("piper_voice", "ramona"))
        self.o_piper.pack(anchor="w")
        label("Edge-Stimme (nur bei Edge)")
        self.o_edge = ctk.CTkOptionMenu(sc, width=360, values=voice.EDGE_VOICES)
        self.o_edge.set(self.cfg.get("edge_voice", voice.EDGE_VOICES[0]))
        self.o_edge.pack(anchor="w")
        label("Sprechtempo (links schneller, rechts langsamer)")
        self.s_speed = ctk.CTkSlider(sc, from_=0.8, to=1.4, width=360)
        self.s_speed.set(self.cfg.get("voice_speed", 1.0))
        self.s_speed.pack(anchor="w")
        ctk.CTkButton(sc, text="Stimme testen", width=360, fg_color="#334155",
                      command=self._test_voice).pack(anchor="w", pady=(10, 0))
        label("KI-Modell (Ollama)")
        self.e_model = ctk.CTkEntry(sc, width=360)
        self.e_model.insert(0, self.cfg["model"])
        self.e_model.pack(anchor="w")
        label("Spracherkennung")
        self.o_whisper = ctk.CTkOptionMenu(sc, values=["tiny", "base", "small"], width=360)
        self.o_whisper.set(self.cfg["whisper_model"])
        self.o_whisper.pack(anchor="w")
        ctk.CTkButton(sc, text="Speichern", width=360, command=self._save).pack(anchor="w", pady=(22, 4))
        self.save_info = ctk.CTkLabel(sc, text="", text_color="gray", wraplength=480, justify="left")
        self.save_info.pack(anchor="w")
        return f

    def _apply(self):
        self.cfg.update(speak=bool(self.v_speak.get()), show_text=bool(self.v_show.get()),
                        voice_engine=self.o_engine.get().split()[0], piper_voice=self.o_piper.get(),
                        edge_voice=self.o_edge.get(), voice_speed=round(float(self.s_speed.get()), 2),
                        model=self.e_model.get().strip(), whisper_model=self.o_whisper.get())

    def _test_voice(self):
        self._apply()
        threading.Thread(target=self.assistant.mouth.say, daemon=True,
                         args=("Hallo Master, so klinge ich. Gefällt dir meine Stimme?",)).start()

    # ---------- Verhalten ----------
    def show_page(self, name):
        for n, f in self.pages.items():
            f.grid_remove()
            self.nav[n].configure(fg_color="#26324a" if n == name else "transparent")
        self.pages[name].grid()
        if name == "Gedächtnis":
            self._refresh_memory()

    def _bubble(self, role, text):
        mine = role == "user"
        row = ctk.CTkFrame(self.chat, fg_color="transparent")
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(row, text=text, wraplength=520, justify="left", anchor="w",
                     fg_color="#1e3a5f" if mine else "#2a2f3a", corner_radius=14,
                     padx=14, pady=10).pack(side="right" if mine else "left", padx=6)
        ctk.CTkLabel(row, text=time.strftime("%H:%M"), text_color="gray",
                     font=ctk.CTkFont(size=10)).pack(side="right" if mine else "left", padx=2, anchor="s")
        self.after(60, lambda: self.chat._parent_canvas.yview_moveto(1.0))

    def _poll(self):
        try:
            while True:
                kind, data = self.q.get_nowait()
                if kind == "status":
                    key = data.split()[0]
                    self.status_dot.configure(text="● " + data,
                                              text_color=STATUS_COLORS.get(key, "#9ca3af"))
                elif kind == "msg":
                    role, text = data
                    if role == "user" or self.cfg.get("show_text", True):
                        self._bubble(role, text)
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _send(self):
        t = self.entry.get().strip()
        if t:
            self.entry.delete(0, "end")
            threading.Thread(target=self.assistant.handle, args=(t,), daemon=True).start()

    def _mic(self):
        self.assistant.force_listen = True
        self.assistant.paused = False
        self.q.put(("status", "Hört zu"))

    def _toggle_pause(self):
        self.assistant.paused = not self.assistant.paused
        self.pause_btn.configure(text="▶  Zuhören fortsetzen" if self.assistant.paused else "⏸  Zuhören pausieren")

    def _refresh_memory(self):
        for w in self.mem_list.winfo_children():
            w.destroy()
        facts = self.assistant.mem.all_facts()
        if not facts:
            ctk.CTkLabel(self.mem_list, text="Noch nichts gespeichert. Sage z.B. „YAVIS, merk dir, dass …“",
                         text_color="gray").pack(pady=20)
        for k, v in facts:
            row = ctk.CTkFrame(self.mem_list, corner_radius=10)
            row.pack(fill="x", pady=4, padx=4)
            ctk.CTkLabel(row, text=f"{k}: {v}", wraplength=480, justify="left", anchor="w"
                         ).pack(side="left", padx=12, pady=8)
            ctk.CTkButton(row, text="Löschen", width=70, fg_color="#7f1d1d",
                          command=lambda key=k: (self.assistant.mem.forget(key), self._refresh_memory())
                          ).pack(side="right", padx=8)

    def _save(self):
        self._apply()
        config.save(self.cfg)
        self.save_info.configure(text="Gespeichert. Die Stimme gilt sofort; Modell-Änderungen nach Neustart von YAVIS.")

    def _tray(self):
        try:
            import pystray
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (64, 64), "#0f172a")
            ImageDraw.Draw(img).ellipse((10, 10, 54, 54), outline="#4cc9f0", width=5)
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
