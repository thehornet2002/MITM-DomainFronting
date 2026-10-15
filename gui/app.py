import os
import sys
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from core.config_builder import build_xray_config, DEFAULT_SETTINGS
from core.scanner import IPScanner, test_tcp_ping
from core.system_manager import (
    ProcessManager,
    get_xray_path,
    download_xray_core,
    set_system_proxy,
    clear_system_proxy,
    is_system_proxy_enabled,
    install_ca_to_windows_store,
    check_ca_installed,
    BASE_DIR
)
from core.asn_extractor import (
    get_all_catalog_asns,
    fetch_live_asn,
    sample_ips_from_cidrs
)

SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")


def load_user_settings():
    settings = dict(DEFAULT_SETTINGS)
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                settings.update(saved)
        except Exception:
            pass
    return settings


def save_user_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


class MITMServerlessApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MITM-DomainFronting & Serverless Studio | @patterniha Enhanced")
        self.geometry("980x720")
        self.minsize(860, 620)
        self.configure(bg="#1a1a24")

        self.settings = load_user_settings()
        self.process_manager = ProcessManager()
        self.scanner = IPScanner(max_threads=25)

        self._init_theme()
        self._init_ui()
        self._update_status_loop()

    def _init_theme(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Dark modern palette
        bg_dark = "#1a1a24"
        card_bg = "#242434"
        card_fg = "#e2e8f0"
        accent_blue = "#3b82f6"
        accent_hover = "#2563eb"

        self.colors = {
            "bg": bg_dark,
            "card": card_bg,
            "fg": card_fg,
            "accent": accent_blue,
            "green": "#10b981",
            "red": "#ef4444",
            "yellow": "#f59e0b",
            "input_bg": "#12121c",
            "border": "#374151"
        }

        style.configure(".", background=bg_dark, foreground=card_fg, font=("Segoe UI", 9))
        style.configure("TNotebook", background=bg_dark, borderwidth=0)
        style.configure("TNotebook.Tab", background=card_bg, foreground=card_fg, padding=[12, 6], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", accent_blue)], foreground=[("selected", "#ffffff")])

        style.configure("Card.TFrame", background=card_bg, relief="flat")
        style.configure("TLabel", background=card_bg, foreground=card_fg)
        style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"), foreground="#60a5fa", background=card_bg)
        style.configure("Status.TLabel", font=("Segoe UI", 11, "bold"), background=card_bg)

        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), background=accent_blue, foreground="#ffffff", borderwidth=0, padding=6)
        style.map("Accent.TButton", background=[("active", accent_hover)])

        style.configure("Green.TButton", font=("Segoe UI", 10, "bold"), background=self.colors["green"], foreground="#ffffff", borderwidth=0, padding=6)
        style.map("Green.TButton", background=[("active", "#059669")])

        style.configure("Red.TButton", font=("Segoe UI", 10, "bold"), background=self.colors["red"], foreground="#ffffff", borderwidth=0, padding=6)
        style.map("Red.TButton", background=[("active", "#dc2626")])

        style.configure("Treeview", background="#12121c", foreground="#f8fafc", fieldbackground="#12121c", rowheight=24)
        style.configure("Treeview.Heading", background="#2a2a3e", foreground="#93c5fd", font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", accent_blue)])

    def _init_ui(self):
        # Top Header Bar
        top_bar = tk.Frame(self, bg="#11111a", height=50)
        top_bar.pack(side="top", fill="x")

        title_lbl = tk.Label(top_bar, text="MITM & Serverless Xray Controller", font=("Segoe UI", 13, "bold"), fg="#60a5fa", bg="#11111a")
        title_lbl.pack(side="left", padx=15, pady=10)

        self.core_status_lbl = tk.Label(top_bar, text="● هسته: خاموش", font=("Segoe UI", 10, "bold"), fg=self.colors["red"], bg="#11111a")
        self.core_status_lbl.pack(side="right", padx=15, pady=10)

        self.proxy_status_lbl = tk.Label(top_bar, text="● پراکسی ویندوز: خاموش", font=("Segoe UI", 10, "bold"), fg=self.colors["yellow"], bg="#11111a")
        self.proxy_status_lbl.pack(side="right", padx=10, pady=10)

        # Tab Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self._build_dashboard_tab()
        self._build_cdn_tab()
        self._build_scanner_tab()
        self._build_asn_tab()
        self._build_advanced_tab()

    def _build_dashboard_tab(self):
        tab = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(tab, text="داشبورد و کنترل")

        # Top Control Card
        ctrl_card = tk.LabelFrame(tab, text="کنترل عملیات", bg=self.colors["card"], fg="#93c5fd", font=("Segoe UI", 10, "bold"), padx=15, pady=10)
        ctrl_card.pack(fill="x", padx=15, pady=10)

        btn_box = tk.Frame(ctrl_card, bg=self.colors["card"])
        btn_box.pack(fill="x", pady=5)

        self.start_btn = tk.Button(btn_box, text="▶ شروع هسته Xray", bg=self.colors["green"], fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=15, pady=6, cursor="hand2", command=self._start_xray)
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = tk.Button(btn_box, text="■ توقف هسته", bg=self.colors["red"], fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=15, pady=6, cursor="hand2", command=self._stop_xray)
        self.stop_btn.pack(side="left", padx=5)

        self.proxy_btn = tk.Button(btn_box, text="تغییر وضعیت پراکسی سیستم", bg="#4f46e5", fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=12, pady=6, cursor="hand2", command=self._toggle_proxy)
        self.proxy_btn.pack(side="left", padx=10)

        self.download_btn = tk.Button(btn_box, text="دانلود خودکار Xray Core", bg="#374151", fg="white", font=("Segoe UI", 9), relief="flat", padx=10, pady=6, cursor="hand2", command=self._download_xray)
        self.download_btn.pack(side="right", padx=5)

        # Mode Selection
        mode_card = tk.LabelFrame(tab, text="حالت اجرایی (Execution Mode)", bg=self.colors["card"], fg="#93c5fd", font=("Segoe UI", 10, "bold"), padx=15, pady=10)
        mode_card.pack(fill="x", padx=15, pady=5)

        self.mode_var = tk.StringVar(value=self.settings.get("mode", "hybrid"))
        modes = [
            ("hybrid", "ترکیبی هوشمند (Hybrid: فرگمنت ترافیک عمومی + اتصال مستقیم MITM Fronting با IP تمیز برای یوتیوب، اینستاگرام، ردیت) [پیشنهادی]"),
            ("mitm", "فقط MITM و Domain Fronting (رمزگشایی محلی با گواهی اختصاصی و ارسال به CDN هدف)"),
            ("serverless_a", "فقط سرورلس فریم‌ورک A (Serverless FragA - تکه‌تکه‌سازی پکت‌های TLS بدون نیاز به گواهی)"),
            ("serverless_b", "فقط سرورلس فریم‌ورک B (Serverless FragB - قطعه‌بندی نوع دوم بدون گواهی)")
        ]
        for val, desc in modes:
            rb = tk.Radiobutton(mode_card, text=desc, value=val, variable=self.mode_var, bg=self.colors["card"], fg=self.colors["fg"], selectcolor="#11111a", activebackground=self.colors["card"], activeforeground="#ffffff", font=("Segoe UI", 9))
            rb.pack(anchor="w", pady=3)

        # CA Certificate Setup Card
        ca_card = tk.LabelFrame(tab, text="وضعیت گواهی امنیتی MITM", bg=self.colors["card"], fg="#93c5fd", font=("Segoe UI", 10, "bold"), padx=15, pady=10)
        ca_card.pack(fill="x", padx=15, pady=5)

        ca_info = tk.Label(ca_card, text="برای کارکرد حالت‌های MITM و Hybrid، نیاز به تولید و معرفی یک‌باره گواهی به مخزن سیستم (Trusted Root) است.", bg=self.colors["card"], fg="#94a3b8", font=("Segoe UI", 9))
        ca_info.pack(anchor="w", pady=2)

        ca_btn_box = tk.Frame(ca_card, bg=self.colors["card"])
        ca_btn_box.pack(fill="x", pady=5)

        self.install_ca_btn = tk.Button(ca_btn_box, text="نصب و فعال‌سازی خودکار گواهی در ویندوز (One-Click CA Install)", bg="#0284c7", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=5, cursor="hand2", command=self._install_ca)
        self.install_ca_btn.pack(side="left", padx=5)

        self.ca_status_text = tk.Label(ca_btn_box, text="", font=("Segoe UI", 9, "bold"), bg=self.colors["card"])
        self.ca_status_text.pack(side="left", padx=15)
        self._check_ca_status()

        # Port Settings
        port_box = tk.Frame(tab, bg=self.colors["card"])
        port_box.pack(fill="x", padx=15, pady=10)
        tk.Label(port_box, text="پورت لوکال Mixed (SOCKS/HTTP):", bg=self.colors["card"], fg=self.colors["fg"]).pack(side="left", padx=5)
        self.port_entry = tk.Entry(port_box, width=8, bg=self.colors["input_bg"], fg="white", insertbackground="white", relief="flat")
        self.port_entry.insert(0, str(self.settings.get("local_port", 10808)))
        self.port_entry.pack(side="left", padx=5)

    def _build_cdn_tab(self):
        tab = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(tab, text="تنظیمات CDN و IPهای تمیز")

        desc_lbl = tk.Label(tab, text="تعیین IP تمیز اختصاصی برای هر CDN (در صورت خالی بودن، به دامنه‌های پیش‌فرض Fronting متصل می‌شود):", font=("Segoe UI", 10, "bold"), fg="#93c5fd", bg=self.colors["card"])
        desc_lbl.pack(anchor="w", padx=15, pady=10)

        form_frame = tk.Frame(tab, bg=self.colors["card"])
        form_frame.pack(fill="both", expand=True, padx=15, pady=5)

        self.cdn_entries = {}
        cdn_targets = [
            ("fastly", "Fastly CDN (سایت‌های Reddit, GitHub, BuzzFeed, CNN)", "151.101.65.140"),
            ("cloudflare", "Cloudflare CDN (سایت‌های پشت کلودفلر، چالش‌ها و ECH)", "104.16.132.229"),
            ("google", "Google / YouTube (سرویس‌های ویدیویی یوتیوب و گوگل)", "142.250.180.206"),
            ("meta", "Meta (اینستاگرام، واتس‌آپ، فیسبوک)", "157.240.22.35"),
            ("gcore", "GCore CDN (شبکه‌های استریم و محتوای گیمینگ)", "92.223.84.1"),
            ("cloudfront", "Amazon CloudFront (سرویس‌های ابری AWS)", "13.224.160.10")
        ]

        saved_cdn_ips = self.settings.get("cdn_ips", {})
        for idx, (cdn_key, label_text, default_sample) in enumerate(cdn_targets):
            row = tk.Frame(form_frame, bg=self.colors["card"])
            row.pack(fill="x", pady=6)

            lbl = tk.Label(row, text=f"{label_text}:", width=45, anchor="w", bg=self.colors["card"], fg=self.colors["fg"], font=("Segoe UI", 9))
            lbl.pack(side="left", padx=5)

            ent = tk.Entry(row, width=22, bg=self.colors["input_bg"], fg="white", insertbackground="white", relief="flat")
            curr_val = saved_cdn_ips.get(cdn_key, "")
            ent.insert(0, curr_val)
            ent.pack(side="left", padx=5)
            self.cdn_entries[cdn_key] = ent

            test_btn = tk.Button(row, text="تست پینگ", bg="#374151", fg="white", font=("Segoe UI", 8), relief="flat", padx=8, pady=2, cursor="hand2", command=lambda k=cdn_key, e=ent: self._ping_cdn_ip(k, e.get()))
            test_btn.pack(side="left", padx=5)

            def_btn = tk.Button(row, text="نمونه", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 8), relief="flat", padx=6, pady=2, cursor="hand2", command=lambda e=ent, s=default_sample: self._set_entry(e, s))
            def_btn.pack(side="left", padx=2)

        save_box = tk.Frame(tab, bg=self.colors["card"])
        save_box.pack(fill="x", padx=15, pady=15)

        save_btn = tk.Button(save_box, text="ذخیره تنظیمات IPهای CDN", bg=self.colors["green"], fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=15, pady=6, cursor="hand2", command=self._save_cdn_ips)
        save_btn.pack(side="left", padx=5)

        clear_btn = tk.Button(save_box, text="پاک‌سازی تمام IPها (حالت خودکار)", bg="#4b5563", fg="white", font=("Segoe UI", 9), relief="flat", padx=10, pady=6, cursor="hand2", command=self._clear_cdn_ips)
        clear_btn.pack(side="left", padx=5)

    def _build_scanner_tab(self):
        tab = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(tab, text="اسکنر پیشرفته IP")

        # Top Control Frame
        ctrl_box = tk.Frame(tab, bg=self.colors["card"])
        ctrl_box.pack(fill="x", padx=15, pady=10)

        # Target Selector
        tk.Label(ctrl_box, text="هدف اسکن:", bg=self.colors["card"], fg=self.colors["fg"]).grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self.scan_target_combo = ttk.Combobox(ctrl_box, width=32, state="readonly")
        self.scan_target_combo["values"] = [
            "Cloudflare (AS13335)",
            "Fastly (AS54113)",
            "Google / YouTube (AS15169)",
            "Meta / Instagram (AS32934)",
            "Amazon CloudFront (AS16509)",
            "GCore (AS199524)",
            "همراه اول MCI (AS197207)",
            "ایرانسل Irancell (AS44244)",
            "مخابرات ایران TCI (AS58224)",
            "رایتل Rightel (AS57218)",
            "شاتل Shatel (AS56402)",
            "سفارشی (ورود رنج دستی)"
        ]
        self.scan_target_combo.current(0)
        self.scan_target_combo.grid(row=0, column=1, sticky="w", padx=5, pady=3)

        # Test Type
        tk.Label(ctrl_box, text="نوع تست:", bg=self.colors["card"], fg=self.colors["fg"]).grid(row=0, column=2, sticky="w", padx=10, pady=3)
        self.scan_type_combo = ttk.Combobox(ctrl_box, width=15, state="readonly")
        self.scan_type_combo["values"] = ["tcp", "tls", "icmp", "udp"]
        self.scan_type_combo.current(0)
        self.scan_type_combo.grid(row=0, column=3, sticky="w", padx=5, pady=3)

        # Port
        tk.Label(ctrl_box, text="پورت:", bg=self.colors["card"], fg=self.colors["fg"]).grid(row=0, column=4, sticky="w", padx=10, pady=3)
        self.scan_port_entry = tk.Entry(ctrl_box, width=6, bg=self.colors["input_bg"], fg="white", insertbackground="white", relief="flat")
        self.scan_port_entry.insert(0, "443")
        self.scan_port_entry.grid(row=0, column=5, sticky="w", padx=5, pady=3)

        # Thread & Count limit
        tk.Label(ctrl_box, text="حداکثر IP:", bg=self.colors["card"], fg=self.colors["fg"]).grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.scan_count_entry = tk.Entry(ctrl_box, width=10, bg=self.colors["input_bg"], fg="white", insertbackground="white", relief="flat")
        self.scan_count_entry.insert(0, "50")
        self.scan_count_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        # Start / Stop Buttons
        btn_sub_box = tk.Frame(ctrl_box, bg=self.colors["card"])
        btn_sub_box.grid(row=1, column=2, columnspan=4, sticky="w", padx=10, pady=5)

        self.start_scan_btn = tk.Button(btn_sub_box, text="شروع اسکن", bg=self.colors["accent"], fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4, cursor="hand2", command=self._start_scan)
        self.start_scan_btn.pack(side="left", padx=5)

        self.stop_scan_btn = tk.Button(btn_sub_box, text="توقف", bg=self.colors["red"], fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=4, cursor="hand2", command=self._stop_scan)
        self.stop_scan_btn.pack(side="left", padx=5)

        self.scan_progress_lbl = tk.Label(btn_sub_box, text="", bg=self.colors["card"], fg="#94a3b8")
        self.scan_progress_lbl.pack(side="left", padx=10)

        # Treeview Results Table
        columns = ("ip", "port", "type", "latency", "status")
        self.scan_tree = ttk.Treeview(tab, columns=columns, show="headings", height=15)
        self.scan_tree.heading("ip", text="IP Address")
        self.scan_tree.heading("port", text="Port")
        self.scan_tree.heading("type", text="تست")
        self.scan_tree.heading("latency", text="تاخیر (ms)")
        self.scan_tree.heading("status", text="نتیجه / وضعیت")

        self.scan_tree.column("ip", width=180, anchor="center")
        self.scan_tree.column("port", width=70, anchor="center")
        self.scan_tree.column("type", width=80, anchor="center")
        self.scan_tree.column("latency", width=100, anchor="center")
        self.scan_tree.column("status", width=220, anchor="w")

        self.scan_tree.pack(fill="both", expand=True, padx=15, pady=5)

        # Bottom Actions
        act_box = tk.Frame(tab, bg=self.colors["card"])
        act_box.pack(fill="x", padx=15, pady=10)

        tk.Label(act_box, text="انتخاب ردیف و اعمال به عنوان IP تمیز برای CDN:", bg=self.colors["card"], fg=self.colors["fg"]).pack(side="left", padx=5)
        self.target_cdn_for_apply = ttk.Combobox(act_box, width=15, state="readonly", values=["fastly", "cloudflare", "google", "meta", "gcore", "cloudfront"])
        self.target_cdn_for_apply.current(0)
        self.target_cdn_for_apply.pack(side="left", padx=5)

        apply_btn = tk.Button(act_box, text="اعمال IP انتخاب شده", bg=self.colors["green"], fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=4, cursor="hand2", command=self._apply_scanned_ip)
        apply_btn.pack(side="left", padx=5)

    def _build_asn_tab(self):
        tab = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(tab, text="پایگاه داده و استخراج ASN")

        # Top Search Bar
        search_box = tk.Frame(tab, bg=self.colors["card"])
        search_box.pack(fill="x", padx=15, pady=10)

        tk.Label(search_box, text="جستجو / ورود شماره ASN دلخواه (مثال: AS13335 یا AS44244):", bg=self.colors["card"], fg=self.colors["fg"]).pack(side="left", padx=5)
        self.asn_input = tk.Entry(search_box, width=20, bg=self.colors["input_bg"], fg="white", insertbackground="white", relief="flat")
        self.asn_input.insert(0, "AS13335")
        self.asn_input.pack(side="left", padx=5)

        fetch_btn = tk.Button(search_box, text="استخراج زنده رنج‌ها از RIPEstat", bg=self.colors["accent"], fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=4, cursor="hand2", command=self._fetch_asn_live)
        fetch_btn.pack(side="left", padx=5)

        self.asn_fetch_lbl = tk.Label(search_box, text="", bg=self.colors["card"], fg="#94a3b8")
        self.asn_fetch_lbl.pack(side="left", padx=10)

        # Split frame for catalog table and prefix viewer
        split_frame = tk.Frame(tab, bg=self.colors["card"])
        split_frame.pack(fill="both", expand=True, padx=15, pady=5)

        # Left: Catalog Table
        left_box = tk.Frame(split_frame, bg=self.colors["card"])
        left_box.pack(side="left", fill="both", expand=True, padx=(0, 5))

        tk.Label(left_box, text="ASNهای کاتالوگ (جهانی و ایران):", font=("Segoe UI", 9, "bold"), fg="#93c5fa", bg=self.colors["card"]).pack(anchor="w", pady=2)
        columns = ("asn", "name", "category")
        self.asn_tree = ttk.Treeview(left_box, columns=columns, show="headings", height=12)
        self.asn_tree.heading("asn", text="ASN")
        self.asn_tree.heading("name", text="نام شرکت / اپراتور")
        self.asn_tree.heading("category", text="دسته‌بندی")
        self.asn_tree.column("asn", width=70, anchor="center")
        self.asn_tree.column("name", width=220, anchor="w")
        self.asn_tree.column("category", width=130, anchor="center")
        self.asn_tree.pack(fill="both", expand=True)
        self.asn_tree.bind("<<TreeviewSelect>>", self._on_asn_selected)

        # Populate catalog
        self._populate_asn_tree()

        # Right: Prefixes Box
        right_box = tk.Frame(split_frame, bg=self.colors["card"])
        right_box.pack(side="right", fill="both", expand=True, padx=(5, 0))

        tk.Label(right_box, text="رنج‌های اعلام‌شده (Prefixes CIDR):", font=("Segoe UI", 9, "bold"), fg="#93c5fa", bg=self.colors["card"]).pack(anchor="w", pady=2)
        self.asn_prefixes_text = scrolledtext.ScrolledText(right_box, width=35, height=12, bg="#12121c", fg="#f8fafc", insertbackground="white", relief="flat")
        self.asn_prefixes_text.pack(fill="both", expand=True)

        # Action: Send to scanner
        send_btn_box = tk.Frame(tab, bg=self.colors["card"])
        send_btn_box.pack(fill="x", padx=15, pady=10)
        send_to_scan_btn = tk.Button(send_btn_box, text="ارسال رنج‌های این ASN به اسکنر", bg=self.colors["green"], fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=5, cursor="hand2", command=self._send_asn_to_scanner)
        send_to_scan_btn.pack(side="left")

    def _build_advanced_tab(self):
        tab = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(tab, text="تنظیمات پیشرفته و لاگ")

        adv_card = tk.LabelFrame(tab, text="ویژگی‌های تکمیلی و دورزدن تحریم", bg=self.colors["card"], fg="#93c5fd", font=("Segoe UI", 10, "bold"), padx=15, pady=10)
        adv_card.pack(fill="x", padx=15, pady=5)

        self.warp_var = tk.BooleanVar(value=self.settings.get("enable_warp", False))
        tk.Checkbutton(adv_card, text="فعال‌سازی لایه سرورلس WARP جهت عبور از خطای 403 تحریم سرویس‌های خارجی (OpenAI, Spotify, etc.)", variable=self.warp_var, bg=self.colors["card"], fg=self.colors["fg"], selectcolor="#11111a", activebackground=self.colors["card"], font=("Segoe UI", 9)).pack(anchor="w", pady=3)

        self.noise_var = tk.BooleanVar(value=self.settings.get("enable_udp_noise", True))
        tk.Checkbutton(adv_card, text="تزریق نویز تصادفی UDP (UDP Noise Disguise) برای پنهان‌سازی هندشیک QUIC و DNS", variable=self.noise_var, bg=self.colors["card"], fg=self.colors["fg"], selectcolor="#11111a", activebackground=self.colors["card"], font=("Segoe UI", 9)).pack(anchor="w", pady=3)

        self.turbo_var = tk.BooleanVar(value=self.settings.get("turbo_happy_eyeballs", True))
        tk.Checkbutton(adv_card, text="توربو Happy-Eyeballs (مسابقه هم‌زمان و اتصالات چندمسیره IPv4/IPv6 برای کاهش پکت‌لاس)", variable=self.turbo_var, bg=self.colors["card"], fg=self.colors["fg"], selectcolor="#11111a", activebackground=self.colors["card"], font=("Segoe UI", 9)).pack(anchor="w", pady=3)

        # Log Window
        log_card = tk.LabelFrame(tab, text="لاگ زنده هسته Xray", bg=self.colors["card"], fg="#93c5fd", font=("Segoe UI", 10, "bold"), padx=10, pady=5)
        log_card.pack(fill="both", expand=True, padx=15, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_card, height=12, bg="#0d0d14", fg="#38bdf8", insertbackground="white", relief="flat", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)

        clear_log_btn = tk.Button(log_card, text="پاک‌سازی لاگ", bg="#374151", fg="white", font=("Segoe UI", 8), relief="flat", padx=8, pady=2, cursor="hand2", command=lambda: self.log_text.delete("1.0", tk.END))
        clear_log_btn.pack(side="right", pady=3)

    # --- Actions ---
    def _save_current_settings(self):
        self.settings["mode"] = self.mode_var.get()
        try:
            self.settings["local_port"] = int(self.port_entry.get().strip())
        except ValueError:
            self.settings["local_port"] = 10808
        self.settings["enable_warp"] = self.warp_var.get()
        self.settings["enable_udp_noise"] = self.noise_var.get()
        self.settings["turbo_happy_eyeballs"] = self.turbo_var.get()

        for k, ent in self.cdn_entries.items():
            self.settings["cdn_ips"][k] = ent.get().strip()

        save_user_settings(self.settings)

    def _start_xray(self):
        self._save_current_settings()
        xray_path = get_xray_path()
        if not xray_path:
            ans = messagebox.askyesno("دانلود هسته Xray", "فایل هسته xray.exe یافت نشد. مایلید اکنون به‌طور خودکار دانلود و نصب شود؟")
            if ans:
                self._download_xray()
            return

        cfg = build_xray_config(self.settings, base_dir=BASE_DIR)
        try:
            self.process_manager.start(cfg)
            messagebox.showinfo("موفق", f"هسته Xray با موفقیت روی پورت {self.settings['local_port']} اجرا شد.")
        except Exception as e:
            messagebox.showerror("خطا در اجرا", str(e))

    def _stop_xray(self):
        self.process_manager.stop()

    def _toggle_proxy(self):
        if is_system_proxy_enabled():
            clear_system_proxy()
        else:
            port = int(self.port_entry.get().strip() or 10808)
            set_system_proxy(port)

    def _download_xray(self):
        self.download_btn.config(state="disabled", text="در حال دانلود...")
        def _task():
            try:
                def _prog(pct, msg):
                    self.after(0, lambda: self.download_btn.config(text=f"{pct}% {msg[:15]}"))
                path = download_xray_core(_prog)
                self.after(0, lambda: messagebox.showinfo("موفقیت", f"هسته Xray در مسیر زیر نصب شد:\n{path}"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("خطا در دانلود", str(e)))
            finally:
                self.after(0, lambda: self.download_btn.config(state="normal", text="دانلود خودکار Xray Core"))
        threading.Thread(target=_task, daemon=True).start()

    def _check_ca_status(self):
        if check_ca_installed():
            self.ca_status_text.config(text="● فایل‌های mycert.crt و mycert.key موجود است", fg=self.colors["green"])
        else:
            self.ca_status_text.config(text="● گواهی هنوز ساخته نشده است", fg=self.colors["yellow"])

    def _install_ca(self):
        ok, msg = install_ca_to_windows_store()
        if ok:
            messagebox.showinfo("نصب گواهی", msg)
            self._check_ca_status()
        else:
            messagebox.showerror("خطای نصب گواهی", msg)

    def _set_entry(self, entry, text):
        entry.delete(0, tk.END)
        entry.insert(0, text)

    def _save_cdn_ips(self):
        self._save_current_settings()
        messagebox.showinfo("ذخیره", "تنظیمات IPهای CDN با موفقیت ذخیره شد.")

    def _clear_cdn_ips(self):
        for ent in self.cdn_entries.values():
            ent.delete(0, tk.END)
        self._save_cdn_ips()

    def _ping_cdn_ip(self, cdn_key, ip_str):
        ip_val = ip_str.strip()
        if not ip_val:
            messagebox.showwarning("ورودی نامعتبر", "لطفاً ابتدا یک IP وارد کنید.")
            return
        def _task():
            ok, lat, msg = test_tcp_ping(ip_val, port=443, timeout=2.5)
            status_text = f"اتصال برقرار است | تاخیر: {lat}ms" if ok else f"خطا در اتصال: {msg}"
            self.after(0, lambda: messagebox.showinfo(f"نتیجه تست {cdn_key.upper()}", f"IP: {ip_val}\nوضعیت: {status_text}"))
        threading.Thread(target=_task, daemon=True).start()

    # --- Scanner Methods ---
    def _start_scan(self):
        target = self.scan_target_combo.get()
        test_type = self.scan_type_combo.get()
        try:
            port = int(self.scan_port_entry.get().strip() or 443)
            max_ips = int(self.scan_count_entry.get().strip() or 50)
        except ValueError:
            port, max_ips = 443, 50

        # Clear existing
        for item in self.scan_tree.get_children():
            self.scan_tree.delete(item)

        ip_list = []
        if "سفارشی" in target:
            # Custom input or from ASN prefixes text
            text_val = self.asn_prefixes_text.get("1.0", tk.END).strip().splitlines()
            cidrs = [line.strip() for line in text_val if line.strip()]
            ip_list = sample_ips_from_cidrs(cidrs, max_ips=max_ips)
        else:
            # Extract ASN from combo
            catalog_asns = get_all_catalog_asns()
            matched_asn = None
            for item in catalog_asns:
                if str(item["asn"]) in target:
                    matched_asn = item
                    break
            if matched_asn:
                cidrs = matched_asn.get("cidrs_v4", [])
                ip_list = sample_ips_from_cidrs(cidrs, max_ips=max_ips)

        if not ip_list:
            messagebox.showwarning("اسکن", "هیچ آدرس IP معتبری برای اسکن پیدا نشد.")
            return

        self.start_scan_btn.config(state="disabled")
        self.scan_progress_lbl.config(text=f"در حال اسکن {len(ip_list)} آدرس...")

        def _on_result(res):
            self.after(0, lambda: self._add_scan_result(res))

        def _scan_thread():
            self.scanner.scan(ip_list, test_type=test_type, port=port, timeout=2.5, callback=_on_result)
            self.after(0, lambda: self._on_scan_finished())

        threading.Thread(target=_scan_thread, daemon=True).start()

    def _add_scan_result(self, res):
        lat_display = f"{res['latency']}" if res['latency'] is not None else "-"
        status_display = res['message']
        self.scan_tree.insert("", "end", values=(res["ip"], res["port"], res["type"], lat_display, status_display))

    def _stop_scan(self):
        self.scanner.stop()
        self.scan_progress_lbl.config(text="اسکن متوقف شد.")
        self.start_scan_btn.config(state="normal")

    def _on_scan_finished(self):
        self.start_scan_btn.config(state="normal")
        self.scan_progress_lbl.config(text="اسکن تکمیل شد.")

    def _apply_scanned_ip(self):
        selected = self.scan_tree.selection()
        if not selected:
            messagebox.showwarning("انتخاب", "لطفاً ابتدا یک ردیف از جدول را انتخاب کنید.")
            return
        item_vals = self.scan_tree.item(selected[0], "values")
        ip = item_vals[0]
        cdn_key = self.target_cdn_for_apply.get()
        if cdn_key in self.cdn_entries:
            self.cdn_entries[cdn_key].delete(0, tk.END)
            self.cdn_entries[cdn_key].insert(0, ip)
            messagebox.showinfo("اعمال IP", f"آدرس {ip} برای {cdn_key.upper()} در تب تنظیمات CDN ثبت شد.")

    # --- ASN Methods ---
    def _populate_asn_tree(self):
        for item in self.asn_tree.get_children():
            self.asn_tree.delete(item)
        asns = get_all_catalog_asns()
        for a in asns:
            self.asn_tree.insert("", "end", values=(f"AS{a['asn']}", a["name"], a.get("category", "")), tags=(str(a["asn"]),))

    def _on_asn_selected(self, event):
        selected = self.asn_tree.selection()
        if not selected:
            return
        vals = self.asn_tree.item(selected[0], "values")
        asn_str = vals[0].replace("AS", "")
        asns = get_all_catalog_asns()
        matched = [a for a in asns if str(a["asn"]) == asn_str]
        if matched:
            data = matched[0]
            self.asn_prefixes_text.delete("1.0", tk.END)
            v4 = data.get("cidrs_v4", [])
            v6 = data.get("cidrs_v6", [])
            text = "# IPv4 CIDRs:\n" + "\n".join(v4) + "\n\n# IPv6 CIDRs:\n" + "\n".join(v6)
            self.asn_prefixes_text.insert("1.0", text)

    def _fetch_asn_live(self):
        val = self.asn_input.get().strip()
        if not val:
            return
        self.asn_fetch_lbl.config(text="در حال دریافت از RIPEstat...")
        def _task():
            res = fetch_live_asn(val)
            if "error" in res:
                self.after(0, lambda: messagebox.showerror("خطا", res["error"]))
                self.after(0, lambda: self.asn_fetch_lbl.config(text="خطا در دریافت."))
            else:
                v4 = res.get("cidrs_v4", [])
                v6 = res.get("cidrs_v6", [])
                text = f"# {res.get('name', '')} (AS{res.get('asn')})\n\n# IPv4 ({len(v4)} prefixes):\n" + "\n".join(v4[:200])
                if len(v4) > 200:
                    text += f"\n... ({len(v4) - 200} پیشوند دیگر)"
                text += f"\n\n# IPv6 ({len(v6)} prefixes):\n" + "\n".join(v6[:100])
                self.after(0, lambda: self._show_fetched_asn(res, text))
        threading.Thread(target=_task, daemon=True).start()

    def _show_fetched_asn(self, res, text):
        self.asn_fetch_lbl.config(text=f"تعداد رنج‌ها: {len(res.get('cidrs_v4', []))} IPv4")
        self.asn_prefixes_text.delete("1.0", tk.END)
        self.asn_prefixes_text.insert("1.0", text)

    def _send_asn_to_scanner(self):
        self.notebook.select(2)  # Switch to Scanner tab
        self.scan_target_combo.set("سفارشی (ورود رنج دستی)")

    # --- Status Loop ---
    def _update_status_loop(self):
        # Update Core status
        if self.process_manager.is_running():
            self.core_status_lbl.config(text="● هسته: فعال", fg=self.colors["green"])
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
        else:
            self.core_status_lbl.config(text="● هسته: خاموش", fg=self.colors["red"])
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")

        # Update Proxy status
        if is_system_proxy_enabled():
            self.proxy_status_lbl.config(text="● پراکسی ویندوز: فعال (10808)", fg=self.colors["green"])
        else:
            self.proxy_status_lbl.config(text="● پراکسی ویندوز: خاموش", fg=self.colors["yellow"])

        # Update Logs
        logs = self.process_manager.get_logs()
        if logs:
            current_len = int(self.log_text.index("end-1c").split(".")[0])
            if current_len <= len(logs):
                self.log_text.delete("1.0", tk.END)
                self.log_text.insert("1.0", "\n".join(logs[-150:]))
                self.log_text.see(tk.END)

        self.after(1000, self._update_status_loop)


def main():
    app = MITMServerlessApp()
    app.mainloop()


if __name__ == "__main__":
    main()
