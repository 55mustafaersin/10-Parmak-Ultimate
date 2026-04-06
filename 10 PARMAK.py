import tkinter as tk
from tkinter import ttk, messagebox
import random
import json
import os
import sys
import hashlib
import threading
import tempfile
import pygame
from gtts import gTTS
import base64
import array
import ctypes

class DualTypingGame:
    def __init__(self, root):
        self.root = root
        self.root.title("10 Parmak Pro - Ultimate Edition")
        self.root.geometry("850x650")
        
        # --- GÖREV ÇUBUĞU LOGOSU AYARI (Windows için) ---
        try:
            myappid = 'murat55.10parmak.pro.1.0' 
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except: pass

        # --- TEMA MOTORU ---
        self.themes = {
            "Koyu Gri & Mavi": {"bg": "#1e272e", "fg": "#f5f6fa", "accent": "#00a8ff", "success": "#4cd137", "error": "#e84118", "box": "#2f3640"},
            "Siyah & Yeşil": {"bg": "#0d0d0d", "fg": "#00ff00", "accent": "#00ff00", "success": "#00ff00", "error": "#ff0000", "box": "#1a1a1a"},
            "Mavi & Beyaz": {"bg": "#0984e3", "fg": "#ffffff", "accent": "#00cec9", "success": "#55efc4", "error": "#d63031", "box": "#74b9ff"},
            "Koyu Gri & Pembe": {"bg": "#2d3436", "fg": "#ffeaa7", "accent": "#fd79a8", "success": "#00b894", "error": "#d63031", "box": "#636e72"},
            "Açık Gri & Mavi": {"bg": "#f5f6fa", "fg": "#2f3640", "accent": "#0097e6", "success": "#44bd32", "error": "#c23616", "box": "#dcdde1"}
        }
        self.current_theme = "Koyu Gri & Mavi"
        self.theme = self.themes[self.current_theme]
        self.root.configure(bg=self.theme["bg"])
        
        # --- PENCERE LOGOSUNU AYARLA ---
        # Hem senin bilgisayarındaki uzun isimli iconu hem de standart logo.ico ismini arar
        icon_yolu = self.kaynak_yolu_bul("10 parmak klavye eğitimi görseli.ico")
        if os.path.exists(icon_yolu):
            self.root.iconbitmap(icon_yolu)
        elif os.path.exists(self.kaynak_yolu_bul("logo.ico")):
             self.root.iconbitmap(self.kaynak_yolu_bul("logo.ico"))

        # --- OYUN DEĞİŞKENLERİ ---
        self.time_left = 60
        self.max_time = 60
        self.score = 0
        self.wrong_count = 0
        self.high_score = 0
        self.first_run = True 
        self.wrong_word_stats = {}
        self.game_active = False
        self.paused = False
        self.current_eng = ""
        self.current_turk = ""
        self.typing_phase = "eng" 
        self.previous_screen = "main_menu" 
        
        # --- SES SİSTEMİ ---
        pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        self.konusma_sesi_acik = True
        self.tus_sesi_acik = True
        buf = array.array('h', [int(15000) if i % 10 < 5 else int(-15000) for i in range(110)])
        self.click_sound = pygame.mixer.Sound(buffer=buf)
        self.click_sound.set_volume(0.2)
        
        # --- GÜVENLİK ---
        self.SALT = "murat55_samsun_2026"
        app_data = os.getenv('LOCALAPPDATA')
        self.save_dir = os.path.join(app_data, "10ParmakPro_Sys")
        if not os.path.exists(self.save_dir): os.makedirs(self.save_dir)
        self.SCORE_FILE = os.path.join(self.save_dir, "sys_cache.dat") 
        self.words = {}

        self.load_words()
        self.load_system_data() 
        self.frames = {}
        self.create_all_screens()
        
        self.root.bind('<Return>', self.handle_return)
        self.root.bind_all('<Escape>', self.handle_escape)
        self.root.bind('<Key>', self.handle_keypress)
        
        self.switch_screen("main_menu")

        if self.first_run:
            self.show_welcome_warning()
            self.first_run = False
            self.save_system_data()

    def show_welcome_warning(self):
        baslik = "Geliştirici Notu & Geri Bildirim"
        mesaj = (
            "Bu program, yapay zeka (AI) desteği ile geliştirilmiştir.\n\n"
            "İçerisinde bazı ufak teknik hatalar veya geliştirilmeye açık noktalar olabilir. "
            "Karşılaştığınız hataları bildirmek veya uygulamada görmek istediğiniz "
            "yeni özellikleri bize iletmekten çekinmeyin! \n\n"
            "Fikirlerinizle bu projeyi birlikte daha ileriye taşıyabiliriz.\n\n"
            "Keyifli antrenmanlar dileriz!\n"
            "- Mustafa Ersin ALBAYRAK & Ali Tarık ŞİMŞEK"
        )
        messagebox.showinfo(baslik, mesaj)

    def validate_input(self, P):
        if not self.game_active or self.paused: return True
        target = self.current_eng if self.typing_phase == "eng" else self.current_turk
        if len(P) > len(target): return False
        return True

    def create_all_screens(self):
        for name in ["main_menu", "game", "settings", "credits", "info", "stats"]:
            self.frames[name] = tk.Frame(self.root, bg=self.theme["bg"])
            self.frames[name].place(relx=0, rely=0, relwidth=1, relheight=1)
        self.build_main_menu()
        self.build_settings()
        self.build_credits()
        self.build_info()
        self.build_stats()
        self.build_game_ui()

    def switch_screen(self, screen_name):
        if screen_name in ["settings", "credits", "info", "stats"]:
            if self.paused: self.previous_screen = "paused"
            elif not self.game_active and hasattr(self, 'game_over_overlay') and self.game_over_overlay.winfo_exists():
                self.previous_screen = "game_over"
            else: self.previous_screen = "main_menu"
        self.hide_pause_menu()
        if hasattr(self, 'game_over_overlay'): self.game_over_overlay.destroy()
        self.frames[screen_name].tkraise()
        if screen_name == "stats": self.refresh_stats_table()
        if screen_name == "game" and not self.game_active and not self.paused: self.start_new_game()

    def go_back(self):
        if self.previous_screen == "paused":
            self.switch_screen("game")
            self.show_pause_menu()
        elif self.previous_screen == "game_over":
            self.switch_screen("game")
            self.show_game_over_menu()
        else:
            self.switch_screen("main_menu")

    def build_main_menu(self):
        f = self.frames["main_menu"]
        tk.Label(f, text="10 PARMAK PRO", font=("Segoe UI", 48, "bold"), fg=self.theme["accent"], bg=self.theme["bg"]).pack(pady=(60, 10))
        tk.Label(f, text="⚡ Teknik Kelime Hafızanı ve Klavye Hızını Sınırlarına Zorla!", font=("Segoe UI", 16, "italic"), fg=self.theme["fg"], bg=self.theme["bg"]).pack(pady=(0, 40))
        btn_kw = {"font": ("Segoe UI", 14, "bold"), "width": 25, "pady": 8, "bd": 0, "cursor": "hand2"}
        tk.Button(f, text="▶ YAZMAYA BAŞLA", bg=self.theme["success"], fg="#ffffff", command=lambda: self.switch_screen("game"), **btn_kw).pack(pady=8)
        tk.Button(f, text="📊 HATA İSTATİSTİKLERİ", bg=self.theme["accent"], fg="#ffffff", command=lambda: self.switch_screen("stats"), **btn_kw).pack(pady=8)
        tk.Button(f, text="⚙ AYARLAR", bg=self.theme["box"], fg=self.theme["fg"], command=lambda: self.switch_screen("settings"), **btn_kw).pack(pady=8)
        tk.Button(f, text="ℹ BİLGİLENDİRME", bg=self.theme["box"], fg=self.theme["fg"], command=lambda: self.switch_screen("info"), **btn_kw).pack(pady=8)
        tk.Button(f, text="👨‍💻 HAZIRLAYANLAR", bg=self.theme["box"], fg=self.theme["fg"], command=lambda: self.switch_screen("credits"), **btn_kw).pack(pady=8)

    def build_stats(self):
        f = self.frames["stats"]
        tk.Label(f, text="📊 HATA İSTATİSTİKLERİ", font=("Segoe UI", 32, "bold"), fg=self.theme["accent"], bg=self.theme["bg"]).pack(pady=(40, 10))
        tk.Label(f, text="En çok zorlandığınız ve yanlış yazdığınız kelimeler", font=("Segoe UI", 12, "italic"), fg=self.theme["fg"], bg=self.theme["bg"]).pack(pady=(0, 20))
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background=self.theme["box"], foreground=self.theme["fg"], rowheight=30, fieldbackground=self.theme["box"], borderwidth=0, font=("Segoe UI", 11))
        style.map('Treeview', background=[('selected', self.theme["accent"])])
        style.configure("Treeview.Heading", background=self.theme["accent"], foreground="white", font=("Segoe UI", 12, "bold"))
        columns = ("eng", "turk", "errors")
        self.tree = ttk.Treeview(f, columns=columns, show="headings", height=10)
        self.tree.heading("eng", text="İngilizce Terim"); self.tree.heading("turk", text="Türkçe Karşılığı"); self.tree.heading("errors", text="Yanlış Sayısı")
        self.tree.column("eng", width=220, anchor="center"); self.tree.column("turk", width=250, anchor="center"); self.tree.column("errors", width=120, anchor="center")
        self.tree.pack(pady=10)
        tk.Button(f, text="🔙 GERİ DÖN", font=("Segoe UI", 14, "bold"), bg=self.theme["error"], fg="#ffffff", width=15, command=self.go_back).pack(pady=20)

    def refresh_stats_table(self):
        for row in self.tree.get_children(): self.tree.delete(row)
        if not self.wrong_word_stats:
            self.tree.insert("", tk.END, values=("-", "Henüz hiç hata yapmadınız!", "-"))
            return
        sirali = sorted(self.wrong_word_stats.items(), key=lambda x: x[1], reverse=True)
        for eng, count in sirali:
            self.tree.insert("", tk.END, values=(eng, self.words.get(eng, "Bilinmiyor"), f"{count} Kez"))

    def build_settings(self):
        f = self.frames["settings"]
        tk.Label(f, text="⚙ AYARLAR", font=("Segoe UI", 32, "bold"), fg=self.theme["accent"], bg=self.theme["bg"]).pack(pady=(50, 40))
        ses_frame = tk.Frame(f, bg=self.theme["bg"]); ses_frame.pack(pady=20)
        self.settings_konusma_btn = tk.Button(ses_frame, text="🗣 Konuşma: AÇIK", font=("Segoe UI", 14, "bold"), bg=self.theme["success"], fg="#ffffff", width=18, command=self.toggle_konusma)
        self.settings_konusma_btn.pack(side="left", padx=10)
        self.settings_tus_btn = tk.Button(ses_frame, text="⌨ Tuş Sesi: AÇIK", font=("Segoe UI", 14, "bold"), bg=self.theme["success"], fg="#ffffff", width=18, command=self.toggle_tus)
        self.settings_tus_btn.pack(side="left", padx=10)
        tk.Label(f, text="🎨 Tema Seçimi", font=("Segoe UI", 16), fg=self.theme["fg"], bg=self.theme["bg"]).pack(pady=(30, 5))
        tema_frame = tk.Frame(f, bg=self.theme["bg"]); tema_frame.pack()
        for t_name in self.themes.keys():
            tk.Button(tema_frame, text=t_name, font=("Segoe UI", 11), width=16, bg=self.themes[t_name]["box"], fg=self.themes[t_name]["fg"], command=lambda name=t_name: self.apply_theme(name)).pack(side="left", padx=5)
        tk.Button(f, text="🔙 GERİ DÖN", font=("Segoe UI", 14, "bold"), bg=self.theme["error"], fg="#ffffff", width=15, command=self.go_back).pack(pady=60)

    def build_credits(self):
        f = self.frames["credits"]
        tk.Label(f, text="👨‍💻 HAZIRLAYANLAR", font=("Segoe UI", 32, "bold"), fg=self.theme["accent"], bg=self.theme["bg"]).pack(pady=(80, 40))
        tk.Label(f, text="Mustafa Ersin ALBAYRAK", font=("Segoe UI", 24, "bold"), fg=self.theme["success"], bg=self.theme["bg"]).pack(pady=5)
        tk.Label(f, text="&", font=("Segoe UI", 18), fg=self.theme["fg"], bg=self.theme["bg"]).pack(pady=5)
        tk.Label(f, text="Ali Tarık ŞİMŞEK", font=("Segoe UI", 24, "bold"), fg=self.theme["success"], bg=self.theme["bg"]).pack(pady=5)
        tk.Button(f, text="🔙 GERİ DÖN", font=("Segoe UI", 14, "bold"), bg=self.theme["error"], fg="#ffffff", width=15, command=self.go_back).pack(pady=60)

    def build_info(self):
        f = self.frames["info"]
        tk.Label(f, text="ℹ UYGULAMA REHBERİ", font=("Segoe UI", 32, "bold"), fg=self.theme["accent"], bg=self.theme["bg"]).pack(pady=(40, 20))
        info_text = (
            "🚀 TEMEL MEKANİK\nOyun 'Çift Aşamalı' çalışır. Önce İNGİLİZCE, sonra TÜRKÇE yazmalısınız.\n\n"
            "💡 ESNEK KELİME SİSTEMİ\nEğik çizgi (/) veya parantez () olan terimlerde tek bir kelime yeterlidir.\n\n"
            "📊 ANALİZ MOTORU\nYaptığınız hatalar kaydedilir. 'Hata İstatistikleri' bölümünden eksiklerinizi görebilirsiniz.\n\n"
            "📝 KENDİ SÖZLÜĞÜNÜ EKLE\nUygulamanın (.exe) bulunduğu klasöre 'kelimeler.json' adında bir dosya\noluşturarak kendi terimlerinizi ekleyebilir ve size özel bir sözlükle çalışabilirsiniz."
        )
        tk.Label(f, text=info_text, font=("Segoe UI", 13), fg=self.theme["fg"], bg=self.theme["bg"], justify="left", padx=50).pack(pady=10)
        tk.Button(f, text="🔙 GERİ DÖN", font=("Segoe UI", 14, "bold"), bg=self.theme["error"], fg="#ffffff", width=15, command=self.go_back).pack(pady=20)

    def build_game_ui(self):
        f = self.frames["game"]
        self.info_frame = tk.Frame(f, bg=self.theme["bg"]); self.info_frame.pack(pady=15, fill="x", padx=40)
        self.score_label = tk.Label(self.info_frame, text=f"🔥 Skor: {self.score}", font=("Segoe UI", 20, "bold"), fg=self.theme["accent"], bg=self.theme["bg"]); self.score_label.pack(side="left")
        self.high_score_label = tk.Label(self.info_frame, text=f"👑 Rekor: {self.high_score}", font=("Segoe UI", 16, "bold"), fg=self.theme["success"], bg=self.theme["bg"]); self.high_score_label.pack(side="right")
        self.time_text = tk.Label(f, text=f"{self.time_left} Saniye Kaldı", font=("Segoe UI", 12, "bold"), fg=self.theme["fg"], bg=self.theme["bg"]); self.time_text.pack(pady=(10, 0))
        self.time_bar = ttk.Progressbar(f, length=600, mode="determinate"); self.time_bar.pack(pady=5); self.time_bar["maximum"] = self.max_time
        self.word_label = tk.Label(f, text="Hazır mısın?", font=("Consolas", 36, "bold"), fg=self.theme["fg"], bg=self.theme["bg"], wraplength=700); self.word_label.pack(pady=30)
        vcmd = (self.root.register(self.validate_input), '%P')
        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(f, textvariable=self.entry_var, font=("Consolas", 28), justify="center", bg=self.theme["box"], fg=self.theme["accent"], insertbackground=self.theme["fg"], relief="flat", validate="key", validatecommand=vcmd)
        self.entry.pack(pady=10, ipadx=10, ipady=10)
        self.feedback_label = tk.Label(f, text="ESC: Duraklat | Enter: Onayla", font=("Segoe UI", 12), fg=self.theme["fg"], bg=self.theme["bg"]); self.feedback_label.pack(pady=20)

    def apply_theme(self, theme_name):
        self.current_theme = theme_name; self.theme = self.themes[theme_name]
        self.root.configure(bg=self.theme["bg"])
        for widget in self.root.winfo_children(): widget.destroy()
        self.create_all_screens(); self.switch_screen("settings")
        self.toggle_konusma(True); self.toggle_tus(True)

    def toggle_konusma(self, only_update=False):
        if not only_update:
            self.konusma_sesi_acik = not self.konusma_sesi_acik
            if not self.konusma_sesi_acik: pygame.mixer.music.stop()
        txt = "🗣 Konuşma: " + ("AÇIK" if self.konusma_sesi_acik else "KAPALI")
        col = self.theme["success"] if self.konusma_sesi_acik else self.theme["error"]
        if hasattr(self, 'settings_konusma_btn'): self.settings_konusma_btn.config(text=txt, bg=col)
        if hasattr(self, 'pause_konusma_btn'): self.pause_konusma_btn.config(text=txt, bg=col)

    def toggle_tus(self, only_update=False):
        if not only_update: self.tus_sesi_acik = not self.tus_sesi_acik
        txt = "⌨ Tuş Sesi: " + ("AÇIK" if self.tus_sesi_acik else "KAPALI")
        col = self.theme["success"] if self.tus_sesi_acik else self.theme["error"]
        if hasattr(self, 'settings_tus_btn'): self.settings_tus_btn.config(text=txt, bg=col)
        if hasattr(self, 'pause_tus_btn'): self.pause_tus_btn.config(text=txt, bg=col)

    def sesli_oku(self, metin, dil="en"):
        if not self.konusma_sesi_acik or self.paused: return
        def run():
            try:
                tts = gTTS(text=metin, lang=dil)
                temp = os.path.join(tempfile.gettempdir(), f"s_{random.randint(1,999)}.mp3")
                tts.save(temp); pygame.mixer.music.load(temp); pygame.mixer.music.play()
            except: pass
        threading.Thread(target=run, daemon=True).start()

    def start_new_game(self):
        self.score = 0; self.wrong_count = 0; self.time_left = self.max_time
        self.game_active = False; self.paused = False
        self.score_label.config(text=f"🔥 Skor: {self.score}")
        self.update_timer_ui(); self.entry.config(state="normal")
        self.entry.delete(0, tk.END); self.entry.focus(); self.next_word()

    def handle_return(self, event):
        if self.frames["game"].winfo_ismapped(): self.check_word()

    def handle_escape(self, event):
        if self.frames["game"].winfo_ismapped(): self.toggle_pause()

    def handle_keypress(self, event):
        if self.tus_sesi_acik and event.keysym not in ['Return', 'Escape', 'Shift_L', 'Shift_R', 'Caps_Lock']:
            self.click_sound.play()
        if self.frames["game"].winfo_ismapped() and event.keysym not in ['Return', 'Escape']:
            if not self.game_active: self.game_active = True; self.update_timer()

    def record_mistake(self):
        self.wrong_count += 1
        if self.current_eng not in self.wrong_word_stats: self.wrong_word_stats[self.current_eng] = 0
        self.wrong_word_stats[self.current_eng] += 1
        self.hata_efekti()

    def check_word(self):
        if not self.game_active or self.paused: return
        typed = self.entry_var.get().strip().lower()
        if self.typing_phase == "eng" and typed == self.current_eng:
            self.typing_phase = "turk"; self.entry.delete(0, tk.END)
            self.entry.config(fg=self.theme["success"]); self.sesli_oku(self.current_turk, "tr")
        elif self.typing_phase == "turk":
            temiz = self.current_turk.replace("/", " ").replace("(", " ").replace(")", " ").split()
            if typed == " ".join(temiz).lower() or typed in temiz or typed == self.current_turk.lower():
                self.score += 1; self.time_left = min(60, self.time_left + 2)
                self.score_label.config(text=f"🔥 Skor: {self.score}"); self.next_word()
            elif typed != "": self.record_mistake()
        elif typed != "": self.record_mistake()

    def next_word(self):
        if not self.words: self.create_default_words()
        self.current_eng = random.choice(list(self.words.keys()))
        self.current_turk = self.words[self.current_eng]
        self.typing_phase = "eng"; self.entry.config(fg=self.theme["accent"])
        self.word_label.config(text=f"{self.current_eng}\n({self.current_turk})")
        self.entry.delete(0, tk.END); self.sesli_oku(self.current_eng, "en")

    def update_timer(self):
        if self.game_active and not self.paused:
            if self.time_left > 0:
                self.time_left -= 1; self.update_timer_ui()
                self.root.after(1000, self.update_timer)
            else: self.end_game()
        elif self.paused: self.root.after(500, self.update_timer)

    def update_timer_ui(self):
        self.time_bar["value"] = self.time_left
        self.time_text.config(text=f"{self.time_left} Saniye Kaldı")
        self.time_text.config(fg=self.theme["error"] if self.time_left <= 10 else self.theme["fg"])

    def hata_efekti(self):
        self.entry.config(bg=self.theme["error"])
        self.root.after(200, lambda: self.entry.config(bg=self.theme["box"]))
        self.entry.delete(0, tk.END)

    def end_game(self):
        self.game_active = False; self.entry.config(state="disabled")
        if self.score > self.high_score: self.high_score = self.score
        self.save_system_data(); self.show_game_over_menu()

    def toggle_pause(self):
        if not self.frames["game"].winfo_ismapped(): return
        self.paused = not self.paused
        if self.paused: self.show_pause_menu()
        else: self.hide_pause_menu()

    def show_pause_menu(self):
        self.pause_overlay = tk.Frame(self.frames["game"], bg=self.theme["box"], bd=2, relief="ridge")
        self.pause_overlay.place(relx=0.5, rely=0.5, anchor="center", width=420, height=380)
        tk.Label(self.pause_overlay, text="OYUN DURDURULDU", font=("Segoe UI", 20, "bold"), fg=self.theme["accent"], bg=self.theme["box"]).pack(pady=10)
        f = tk.Frame(self.pause_overlay, bg=self.theme["box"]); f.pack(pady=5)
        self.pause_konusma_btn = tk.Button(f, text="", font=("Segoe UI", 9, "bold"), width=15, command=self.toggle_konusma); self.pause_konusma_btn.pack(side="left", padx=5)
        self.pause_tus_btn = tk.Button(f, text="", font=("Segoe UI", 9, "bold"), width=15, command=self.toggle_tus); self.pause_tus_btn.pack(side="left", padx=5)
        self.toggle_konusma(True); self.toggle_tus(True)
        kw = {"font": ("Segoe UI", 12, "bold"), "fg": "white", "width": 20, "pady": 5}
        tk.Button(self.pause_overlay, text="▶ DEVAM ET", bg=self.theme["success"], command=self.toggle_pause, **kw).pack(pady=4)
        tk.Button(self.pause_overlay, text="🔄 YENİDEN BAŞLAT", bg=self.theme["accent"], command=self.start_new_game, **kw).pack(pady=4)
        tk.Button(self.pause_overlay, text="⚙ AYARLAR", bg="#9c88ff", command=lambda: self.switch_screen("settings"), **kw).pack(pady=4)
        tk.Button(self.pause_overlay, text="🏠 ANA MENÜ", bg=self.theme["error"], command=lambda: self.switch_screen("main_menu"), **kw).pack(pady=4)

    def hide_pause_menu(self):
        if hasattr(self, 'pause_overlay'): self.pause_overlay.destroy()

    def show_game_over_menu(self):
        self.game_over_overlay = tk.Frame(self.frames["game"], bg=self.theme["box"], bd=5, relief="ridge")
        self.game_over_overlay.place(relx=0.5, rely=0.5, anchor="center", width=450, height=420)
        tk.Label(self.game_over_overlay, text="SÜRE BİTTİ!", font=("Segoe UI", 24, "bold"), fg=self.theme["error"], bg=self.theme["box"]).pack(pady=10)
        tk.Label(self.game_over_overlay, text=f"✅ Doğru: {self.score} | ❌ Yanlış: {self.wrong_count}", font=("Segoe UI", 14, "bold"), fg=self.theme["fg"], bg=self.theme["box"]).pack(pady=5)
        kw = {"font": ("Segoe UI", 12, "bold"), "fg": "white", "width": 20, "pady": 5}
        tk.Button(self.game_over_overlay, text="🔄 TEKRAR DENE", bg=self.theme["success"], command=self.start_new_game, **kw).pack(pady=(15,5))
        tk.Button(self.game_over_overlay, text="📊 HATA İSTATİSTİKLERİ", bg="#9c88ff", command=lambda: self.switch_screen("stats"), **kw).pack(pady=5)
        tk.Button(self.game_over_overlay, text="🏠 ANA MENÜ", bg=self.theme["error"], command=lambda: self.switch_screen("main_menu"), **kw).pack(pady=5)

    def kaynak_yolu_bul(self, dosya_adi):
        try: base_path = sys._MEIPASS
        except: base_path = os.path.abspath(".")
        return os.path.join(base_path, dosya_adi)

    def load_words(self):
        p = self.kaynak_yolu_bul("kelimeler.json")
        if os.path.exists("kelimeler.json"): p = "kelimeler.json"
        try:
            with open(p, "r", encoding="utf-8") as f: self.words = json.load(f)
        except: self.create_default_words()

    def create_default_words(self):
        self.words = {"software": "yazılım", "firewall": "güvenlik (duvarı)"}
        with open("kelimeler.json", "w", encoding="utf-8") as f: json.dump(self.words, f, ensure_ascii=False, indent=4)

    def save_system_data(self):
        data = {"score": self.high_score, "first_run": self.first_run, "wrong_word_stats": self.wrong_word_stats, "hash": hashlib.sha256((str(self.high_score)+self.SALT).encode()).hexdigest()}
        try:
            d = base64.b64encode(json.dumps(data).encode('utf-8'))
            with open(self.SCORE_FILE, "wb") as f: f.write(d)
        except: pass

    def load_system_data(self):
        self.first_run = True; self.high_score = 0; self.wrong_word_stats = {}
        if os.path.exists(self.SCORE_FILE):
            try:
                with open(self.SCORE_FILE, "rb") as f:
                    d = json.loads(base64.b64decode(f.read()).decode('utf-8'))
                if hashlib.sha256((str(d.get('score',0))+self.SALT).encode()).hexdigest() == d.get('hash',''): 
                    self.high_score = d.get('score', 0)
                    self.first_run = d.get('first_run', True)
                    self.wrong_word_stats = d.get('wrong_word_stats', {})
            except: pass

if __name__ == "__main__":
    root = tk.Tk(); app = DualTypingGame(root); root.mainloop()