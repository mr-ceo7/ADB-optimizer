#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import threading
import time
import re
import os

class ADBOptimizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Antigravity Android ADB Tool & Optimizer")
        self.root.geometry("1000x820")
        self.root.minsize(900, 700)
        self.root.resizable(True, True)
        
        # Style configuration for dark theme
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure_styles()
        
        self.root.configure(bg="#121212")
        
        # State variables
        self.selected_device = tk.StringVar(value="None")
        self.device_list = []
        self.is_running = True
        self.all_packages = [] # Stores tuple (pkg_name, status)
        self.logcat_process = None
        self.logcat_running = False
        self.cpu_load_1min = 0.0
        
        # Search & Filter
        self.app_search_var = tk.StringVar()
        self.app_search_var.trace_add("write", self.filter_apps_list)
        
        # Create Layout
        self.create_widgets()
        
        # Start background polling thread for dashboard
        self.polling_thread = threading.Thread(target=self.poll_device_metrics, daemon=True)
        self.polling_thread.start()

    def get_friendly_name(self, pkg):
        mappings = {
            "com.whatsapp": "WhatsApp",
            "com.instagram.android": "Instagram",
            "com.facebook.katana": "Facebook",
            "com.facebook.orca": "Messenger",
            "com.facebook.stella": "Facebook View",
            "com.facebook.appmanager": "Facebook App Manager",
            "com.facebook.services": "Facebook Services",
            "com.google.android.youtube": "YouTube",
            "com.google.android.googlequicksearchbox": "Google Search",
            "com.google.android.googlequicksearchbox:interactor": "Google Assistant",
            "com.google.android.gms": "Google Play Services",
            "com.google.android.gms.persistent": "Google Play Services (Persistent)",
            "com.google.android.gms.unstable": "Google Play Services (Background)",
            "com.google.android.apps.messaging": "Google Messages",
            "com.google.android.apps.turbo": "Google Turbo",
            "com.google.android.providers.media.module": "Media Storage",
            "com.google.android.inputmethod.latin": "Gboard (Keyboard)",
            "com.android.systemui": "System UI",
            "system_server": "System Server",
            "surfaceflinger": "Screen Renderer (SurfaceFlinger)",
            "com.android.phone": "Phone Services",
            "com.android.settings": "Settings",
            "com.android.launcher3": "System Launcher",
            "com.heytap.mcs": "HeyTap Cloud Services",
            "com.arlosoft.macrodroid": "MacroDroid",
            "com.taboola.scoop": "Taboola Scoop",
            "com.lemon.lvoverseas": "CapCut",
            "com.binance.dev": "Binance",
            "android.process.media": "Media Downloader",
            "com.android.chrome": "Chrome Browser",
            "com.google.android.apps.maps": "Google Maps",
            "org.telegram.messenger": "Telegram",
            "com.spotify.music": "Spotify",
            "com.zhiliaoapp.musically": "TikTok",
            "com.tencent.ig": "PUBG Mobile",
            "com.dts.freefireth": "Free Fire",
        }
        pkg_clean = pkg.split("/")[0].strip("[]()")
        if pkg_clean in mappings:
            return mappings[pkg_clean]
        parts = pkg_clean.split(".")
        if len(parts) >= 2:
            useful_parts = [p.capitalize() for p in parts if p not in ("com", "org", "net", "android", "google", "apps", "androids", "dev")]
            if useful_parts:
                name = " ".join(useful_parts)
                name = name.replace("Systemui", "System UI").replace("Gms", "Play Services")
                return name
        return pkg_clean.replace("_", " ").capitalize()

    def get_package_from_display(self, display_str):
        match = re.search(r'\(([^)]+)\)', display_str)
        if match:
            return match.group(1)
        return display_str.split("/")[0].strip("[]()")

    def configure_styles(self):
        # Dark Theme Settings
        self.style.configure(".", background="#121212", foreground="#ffffff", fieldbackground="#1e1e1e")
        self.style.configure("TFrame", background="#121212")
        self.style.configure("TLabelframe", background="#121212", foreground="#3399ff", bordercolor="#333333")
        self.style.configure("TLabelframe.Label", background="#121212", foreground="#3399ff", font=("Helvetica", 10, "bold"))
        self.style.configure("TLabel", background="#121212", foreground="#ffffff", font=("Helvetica", 10))
        self.style.configure("Header.TLabel", font=("Helvetica", 12, "bold"), foreground="#00ff66")
        
        # Buttons
        self.style.configure("TButton", background="#1e1e1e", foreground="#ffffff", borderwidth=1, font=("Helvetica", 9, "bold"))
        self.style.map("TButton",
            background=[('active', '#3399ff'), ('pressed', '#005bbf')],
            foreground=[('active', '#000000'), ('pressed', '#ffffff')]
        )
        
        self.style.configure("Action.TButton", background="#00aa50", foreground="#ffffff")
        self.style.configure("Danger.TButton", background="#cc2222", foreground="#ffffff")
        self.style.map("Danger.TButton", background=[('active', '#ff3333')])
        
        # Progress Bars
        self.style.configure("TProgressbar", thickness=15, troughcolor="#1e1e1e", background="#3399ff")
        
        # Treeview
        self.style.configure("Treeview", background="#1e1e1e", foreground="#ffffff", fieldbackground="#1e1e1e", rowheight=22)
        self.style.configure("Treeview.Heading", background="#2a2a2a", foreground="#ffffff", font=("Helvetica", 9, "bold"))
        self.style.map("Treeview", background=[('selected', '#3399ff')], foreground=[('selected', '#000000')])
        
        # Notebook (Tabs)
        self.style.configure("TNotebook", background="#121212", borderwidth=0)
        self.style.configure("TNotebook.Tab", background="#1e1e1e", foreground="#ffffff", font=("Helvetica", 9, "bold"), padding=[10, 4])
        self.style.map("TNotebook.Tab",
            background=[('selected', '#3399ff')],
            foreground=[('selected', '#000000')]
        )

    def create_widgets(self):
        # Top Panel: Connection status
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill="x", padx=15, pady=10)
        
        ttk.Label(top_frame, text="Connected Device:", style="Header.TLabel").pack(side="left", padx=5)
        self.device_label = ttk.Label(top_frame, text="Searching...", foreground="#ffcc00", font=("Helvetica", 10, "bold"))
        self.device_label.pack(side="left", padx=5)
        
        ttk.Button(top_frame, text="Refresh Devices", command=self.refresh_devices).pack(side="right", padx=5)
        self.btn_speedup = ttk.Button(top_frame, text="⚡ Quick Speed Up", style="Action.TButton", command=self.quick_speedup)
        self.btn_speedup.pack(side="right", padx=5)

        # Tab Layout Setup
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=5)
        
        # Tab 1: Dashboard
        self.tab_dashboard = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_dashboard, text="   Dashboard   ")
        
        # Tab 2: App Manager (Freeze & Debloat)
        self.tab_apps = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_apps, text=" App Manager (Debloat / Freeze) ")
        
        # Tab 3: System Tweaks (Dark mode, DNS, Screen Mirroring)
        self.tab_tweaks = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_tweaks, text=" System Tweaks & Mirroring ")
        
        # Tab 4: Storage & File Transfer
        self.tab_storage = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_storage, text=" Files & Storage ")
        
        # Tab 5: Logcat Live Viewer
        self.tab_logcat = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_logcat, text=" Live Logcat Viewer ")

        # ------------------ TAB 1: DASHBOARD LAYOUT ------------------
        main_pane = ttk.Frame(self.tab_dashboard)
        main_pane.pack(fill="both", expand=True, pady=5)
        
        # Left Panel (Width 45%)
        left_panel = ttk.Frame(main_pane)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Left Panel: 1. Resource Metrics
        metrics_lf = ttk.LabelFrame(left_panel, text=" Device Resource Metrics ")
        metrics_lf.pack(fill="x", pady=(0, 10))
        
        # CPU Load
        ttk.Label(metrics_lf, text="CPU Load Average:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.cpu_lbl = ttk.Label(metrics_lf, text="--", font=("Courier", 10, "bold"), foreground="#00ff66")
        self.cpu_lbl.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        
        # Battery Temp / Status
        ttk.Label(metrics_lf, text="Battery / Thermal:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.battery_lbl = ttk.Label(metrics_lf, text="--", font=("Helvetica", 9, "bold"), foreground="#3399ff")
        self.battery_lbl.grid(row=1, column=1, columnspan=2, sticky="w", padx=10, pady=5)
        
        # RAM Free
        ttk.Label(metrics_lf, text="Physical RAM:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.ram_bar = ttk.Progressbar(metrics_lf, orient="horizontal", mode="determinate")
        self.ram_bar.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        self.ram_lbl = ttk.Label(metrics_lf, text="-- / --")
        self.ram_lbl.grid(row=2, column=2, padx=5)
        
        # ZRAM / Swap
        ttk.Label(metrics_lf, text="ZRAM Swap:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.swap_bar = ttk.Progressbar(metrics_lf, orient="horizontal", mode="determinate")
        self.swap_bar.grid(row=3, column=1, sticky="ew", padx=10, pady=5)
        self.swap_lbl = ttk.Label(metrics_lf, text="-- / --")
        self.swap_lbl.grid(row=3, column=2, padx=5)
        
        # Storage
        ttk.Label(metrics_lf, text="Internal Storage:").grid(row=4, column=0, sticky="w", padx=10, pady=5)
        self.storage_bar = ttk.Progressbar(metrics_lf, orient="horizontal", mode="determinate")
        self.storage_bar.grid(row=4, column=1, sticky="ew", padx=10, pady=5)
        self.storage_lbl = ttk.Label(metrics_lf, text="-- / --")
        self.storage_lbl.grid(row=4, column=2, padx=5)
        
        metrics_lf.columnconfigure(1, weight=1)
        
        # CPU Analysis / Slowdown Reason Label
        self.cpu_analysis_lbl = ttk.Label(metrics_lf, text="Status: Running diagnostics...", font=("Helvetica", 9, "italic"), foreground="#00ff66", wraplength=350)
        self.cpu_analysis_lbl.grid(row=5, column=0, columnspan=3, sticky="w", padx=10, pady=5)
        
        # Left Panel: 2. System Profiles & Recyclables
        profiles_lf = ttk.LabelFrame(left_panel, text=" Secondary Profiles & Recyclables ")
        profiles_lf.pack(fill="x", pady=(0, 10))
        
        # User Profiles
        ttk.Label(profiles_lf, text="CloneUser (User 10):").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.clone_lbl = ttk.Label(profiles_lf, text="Unknown", font=("Helvetica", 9, "bold"))
        self.clone_lbl.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        
        ttk.Label(profiles_lf, text="Island (User 11):").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.island_lbl = ttk.Label(profiles_lf, text="Unknown", font=("Helvetica", 9, "bold"))
        self.island_lbl.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        
        # Trash Sizes
        ttk.Label(profiles_lf, text="Trash/Recycle Size:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.trash_lbl = ttk.Label(profiles_lf, text="--", font=("Helvetica", 9, "bold"), foreground="#ffcc00")
        self.trash_lbl.grid(row=2, column=1, sticky="w", padx=10, pady=5)
        self.btn_empty_trash = ttk.Button(profiles_lf, text="Empty Trash", command=self.empty_trash)
        self.btn_empty_trash.grid(row=2, column=2, padx=10, pady=5)
        
        # Left Panel: 3. Global Optimizer Configuration
        config_lf = ttk.LabelFrame(left_panel, text=" System-Wide Optimizations ")
        config_lf.pack(fill="x", pady=(0, 10))
        
        # Freezer Toggle
        self.var_freezer = tk.BooleanVar(value=False)
        self.chk_freezer = ttk.Checkbutton(config_lf, text="Enable Cached Apps Freezer (Suspends background apps at 0% CPU)", 
                                           variable=self.var_freezer, command=self.toggle_freezer)
        self.chk_freezer.pack(anchor="w", padx=10, pady=5)
        
        # Auto Restriction Toggle
        self.var_restrict = tk.BooleanVar(value=False)
        self.chk_restrict = ttk.Checkbutton(config_lf, text="Enable Auto-Restriction of Battery/CPU Abusive Apps", 
                                            variable=self.var_restrict, command=self.toggle_auto_restrict)
        self.chk_restrict.pack(anchor="w", padx=10, pady=5)

        # Right Panel: Process Manager & Kill Switches (Width 55%)
        proc_lf = ttk.LabelFrame(main_pane, text=" Background Process Manager (Kill Switches) ")
        proc_lf.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        # Process Treeview Table
        self.proc_tree = ttk.Treeview(proc_lf, columns=("PID", "USER", "CPU", "RAM", "NAME"), show="headings")
        self.proc_tree.heading("PID", text="PID")
        self.proc_tree.heading("USER", text="USER")
        self.proc_tree.heading("CPU", text="CPU %")
        self.proc_tree.heading("RAM", text="RAM (RES)")
        self.proc_tree.heading("NAME", text="PROCESS / PACKAGE NAME")
        
        self.proc_tree.column("PID", width=60, anchor="center")
        self.proc_tree.column("USER", width=80, anchor="center")
        self.proc_tree.column("CPU", width=60, anchor="center")
        self.proc_tree.column("RAM", width=80, anchor="center")
        self.proc_tree.column("NAME", width=230, anchor="w")
        
        # Scrollbar for Treeview
        scroll = ttk.Scrollbar(proc_lf, orient="vertical", command=self.proc_tree.yview)
        self.proc_tree.configure(yscrollcommand=scroll.set)
        
        self.proc_tree.pack(side="top", fill="both", expand=True, padx=5, pady=5)
        scroll.pack(side="right", fill="y")
        
        # Kill Buttons
        btn_frame = ttk.Frame(proc_lf)
        btn_frame.pack(fill="x", side="bottom", padx=5, pady=5)
        
        self.btn_kill = ttk.Button(btn_frame, text="🛑 Kill App / Package", style="Danger.TButton", command=self.kill_selected_app)
        self.btn_kill.pack(side="right", padx=5)
        self.btn_restrict_app = ttk.Button(btn_frame, text="🔒 Restrict Background", command=self.restrict_selected_app)
        self.btn_restrict_app.pack(side="right", padx=5)


        # ------------------ TAB 2: APP MANAGER LAYOUT ------------------
        app_main_frame = ttk.Frame(self.tab_apps)
        app_main_frame.pack(fill="both", expand=True, pady=5)
        
        search_frame = ttk.Frame(app_main_frame)
        search_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(search_frame, text="Search App / Package:").pack(side="left", padx=5)
        self.ent_search = ttk.Entry(search_frame, textvariable=self.app_search_var, width=30)
        self.ent_search.pack(side="left", padx=5)
        
        ttk.Button(search_frame, text="Reload App List", command=self.load_installed_packages).pack(side="right", padx=5)
        
        app_body_frame = ttk.Frame(app_main_frame)
        app_body_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.app_tree = ttk.Treeview(app_body_frame, columns=("NAME", "STATUS"), show="headings")
        self.app_tree.heading("NAME", text="PACKAGE NAME")
        self.app_tree.heading("STATUS", text="LIFECYCLE STATUS")
        self.app_tree.column("NAME", width=350, anchor="w")
        self.app_tree.column("STATUS", width=120, anchor="center")
        
        app_scroll = ttk.Scrollbar(app_body_frame, orient="vertical", command=self.app_tree.yview)
        self.app_tree.configure(yscrollcommand=app_scroll.set)
        
        self.app_tree.pack(side="left", fill="both", expand=True)
        app_scroll.pack(side="left", fill="y", padx=(0, 10))
        
        self.app_tree.bind("<<TreeviewSelect>>", self.on_app_selected)
        
        actions_lf = ttk.LabelFrame(app_body_frame, text=" App Actions ")
        actions_lf.pack(side="right", fill="both", expand=False, ipadx=10, ipady=10)
        
        self.lbl_selected_app = ttk.Label(actions_lf, text="No app selected", font=("Helvetica", 10, "bold"), foreground="#3399ff", wrap=220)
        self.lbl_selected_app.pack(anchor="w", padx=10, pady=(10, 5))
        
        self.lbl_app_bucket = ttk.Label(actions_lf, text="Standby Bucket: --")
        self.lbl_app_bucket.pack(anchor="w", padx=10, pady=2)
        
        self.lbl_app_appop = ttk.Label(actions_lf, text="Background AppOp: --")
        self.lbl_app_appop.pack(anchor="w", padx=10, pady=(2, 15))
        
        self.btn_freeze = ttk.Button(actions_lf, text="❄️ Freeze / Disable App", command=self.freeze_selected_package)
        self.btn_freeze.pack(fill="x", padx=10, pady=5)
        
        self.btn_unfreeze = ttk.Button(actions_lf, text="🔥 Unfreeze / Enable App", command=self.unfreeze_selected_package)
        self.btn_unfreeze.pack(fill="x", padx=10, pady=5)
        
        self.btn_restrict_bucket = ttk.Button(actions_lf, text="🔒 Restrict Background", command=self.restrict_package_background)
        self.btn_restrict_bucket.pack(fill="x", padx=10, pady=5)
        
        self.btn_allow_bucket = ttk.Button(actions_lf, text="🔓 Allow Background", command=self.allow_package_background)
        self.btn_allow_bucket.pack(fill="x", padx=10, pady=5)
        
        self.btn_extract_apk = ttk.Button(actions_lf, text="📦 Extract APK to PC", command=self.extract_selected_apk)
        self.btn_extract_apk.pack(fill="x", padx=10, pady=5)
        
        self.btn_uninstall = ttk.Button(actions_lf, text="🗑️ Uninstall Package", style="Danger.TButton", command=self.uninstall_selected_package)
        self.btn_uninstall.pack(fill="x", padx=10, pady=(15, 5))


        # ------------------ TAB 3: SYSTEM TWEAKS LAYOUT ------------------
        tweaks_scroll_frame = ttk.Frame(self.tab_tweaks)
        tweaks_scroll_frame.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Split into two columns for layout clarity
        tweaks_left = ttk.Frame(tweaks_scroll_frame)
        tweaks_left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        tweaks_right = ttk.Frame(tweaks_scroll_frame)
        tweaks_right.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        # Col 1: System Customization
        ui_lf = ttk.LabelFrame(tweaks_left, text=" System UI Customizer ")
        ui_lf.pack(fill="x", pady=(0, 10))
        
        # Animation Tweaks
        ttk.Label(ui_lf, text="UI Animation Scales:").pack(anchor="w", padx=10, pady=(10, 2))
        anim_btn_frame = ttk.Frame(ui_lf)
        anim_btn_frame.pack(fill="x", padx=10, pady=(2, 10))
        
        ttk.Button(anim_btn_frame, text="Off (0.0x)", command=lambda: self.set_animation_scales("0")).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(anim_btn_frame, text="Fast (0.5x)", command=lambda: self.set_animation_scales("0.5")).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(anim_btn_frame, text="Normal (1.0x)", command=lambda: self.set_animation_scales("1")).pack(side="left", expand=True, fill="x", padx=2)
        
        # Dark Mode Toggles
        ttk.Label(ui_lf, text="System Theme Mode:").pack(anchor="w", padx=10, pady=(10, 2))
        theme_btn_frame = ttk.Frame(ui_lf)
        theme_btn_frame.pack(fill="x", padx=10, pady=(2, 10))
        
        ttk.Button(theme_btn_frame, text="Force Dark Mode 🌙", command=lambda: self.set_dark_mode(True)).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(theme_btn_frame, text="Force Light Mode ☀️", command=lambda: self.set_dark_mode(False)).pack(side="left", expand=True, fill="x", padx=2)
        
        # Ad-Blocking Tweak (Private DNS)
        dns_lf = ttk.LabelFrame(tweaks_left, text=" Ad-Blocking (System Private DNS) ")
        dns_lf.pack(fill="x", pady=(0, 10))
        
        ttk.Label(dns_lf, text="Blocks advertisements system-wide via Private DNS:", wrap=350).pack(anchor="w", padx=10, pady=(10, 5))
        dns_btn_frame = ttk.Frame(dns_lf)
        dns_btn_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(dns_btn_frame, text="Enable Ad-Blocking (AdGuard DNS)", style="Action.TButton", 
                   command=lambda: self.set_private_dns(True)).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Button(dns_btn_frame, text="Disable Ad-Blocking", 
                   command=lambda: self.set_private_dns(False)).pack(side="left", expand=True, fill="x", padx=2)
        
        # Col 2: Screen Mirroring and Capture Tools
        mirror_lf = ttk.LabelFrame(tweaks_right, text=" Screen Control & Capture Tools ")
        mirror_lf.pack(fill="x", pady=(0, 10))
        
        ttk.Label(mirror_lf, text="Run mirror streams and take screenshots/recordings directly:", wrap=350).pack(anchor="w", padx=10, pady=(10, 10))
        
        self.btn_scrcpy = ttk.Button(mirror_lf, text="📺 Launch Screen Mirroring (scrcpy)", command=self.launch_scrcpy)
        self.btn_scrcpy.pack(fill="x", padx=10, pady=5)
        
        self.btn_screenshot = ttk.Button(mirror_lf, text="📸 Capture Screenshot to PC", command=self.capture_screenshot)
        self.btn_screenshot.pack(fill="x", padx=10, pady=5)
        
        self.btn_screenrecord = ttk.Button(mirror_lf, text="🎥 Record 10s Screen Video", command=self.capture_screen_video)
        self.btn_screenrecord.pack(fill="x", padx=10, pady=5)


        # ------------------ TAB 4: FILES & STORAGE ------------------
        storage_main_frame = ttk.Frame(self.tab_storage)
        storage_main_frame.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Top Panel: Scanning Large Files
        scan_frame = ttk.Frame(storage_main_frame)
        scan_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(scan_frame, text="Large Files Analyzer (>100MB):", style="Header.TLabel").pack(side="left", padx=5)
        ttk.Button(scan_frame, text="🔍 Scan Storage", command=self.scan_large_files).pack(side="left", padx=10)
        self.lbl_scan_status = ttk.Label(scan_frame, text="Not scanned", foreground="#ffcc00")
        self.lbl_scan_status.pack(side="left", padx=5)
        
        # Split Layout: Left list of large files, Right File Transfer
        storage_body_frame = ttk.Frame(storage_main_frame)
        storage_body_frame.pack(fill="both", expand=True)
        
        # Table of large files
        self.file_tree = ttk.Treeview(storage_body_frame, columns=("SIZE", "PATH"), show="headings")
        self.file_tree.heading("SIZE", text="SIZE")
        self.file_tree.heading("PATH", text="FILE PATH")
        self.file_tree.column("SIZE", width=100, anchor="center")
        self.file_tree.column("PATH", width=380, anchor="w")
        
        file_scroll = ttk.Scrollbar(storage_body_frame, orient="vertical", command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=file_scroll.set)
        
        self.file_tree.pack(side="left", fill="both", expand=True)
        file_scroll.pack(side="left", fill="y", padx=(0, 10))
        
        # Right Side: File Transfer Box
        transfer_lf = ttk.LabelFrame(storage_body_frame, text=" File Transfer (PC ⇿ Phone) ")
        transfer_lf.pack(side="right", fill="both", expand=False, ipadx=10, ipady=10)
        
        # Transfer widgets
        ttk.Label(transfer_lf, text="Local PC File/Folder:").pack(anchor="w", padx=10, pady=(10, 2))
        self.ent_local_path = ttk.Entry(transfer_lf, width=28)
        self.ent_local_path.pack(fill="x", padx=10, pady=2)
        ttk.Button(transfer_lf, text="Browse PC File", command=self.browse_local_file).pack(anchor="e", padx=10, pady=2)
        
        ttk.Label(transfer_lf, text="Phone Storage Destination:").pack(anchor="w", padx=10, pady=(10, 2))
        self.ent_phone_path = ttk.Entry(transfer_lf, width=28)
        self.ent_phone_path.insert(0, "/sdcard/Download/")
        self.ent_phone_path.pack(fill="x", padx=10, pady=2)
        
        # Push / Pull Buttons
        ttk.Button(transfer_lf, text="📤 Upload to Phone (Push)", style="Action.TButton", command=self.push_file_to_phone).pack(fill="x", padx=10, pady=(15, 5))
        ttk.Button(transfer_lf, text="📥 Download from Phone (Pull)", command=self.pull_file_from_phone).pack(fill="x", padx=10, pady=5)


        # ------------------ TAB 5: LIVE LOGCAT VIEWER ------------------
        logcat_main_frame = ttk.Frame(self.tab_logcat)
        logcat_main_frame.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Top toolbar
        logcat_tool = ttk.Frame(logcat_main_frame)
        logcat_tool.pack(fill="x", pady=(0, 10))
        
        self.btn_logcat_toggle = ttk.Button(logcat_tool, text="▶️ Start Live Logcat", style="Action.TButton", command=self.toggle_logcat)
        self.btn_logcat_toggle.pack(side="left", padx=5)
        
        ttk.Button(logcat_tool, text="🧹 Clear Logcat Console", command=self.clear_logcat_text).pack(side="left", padx=5)
        
        # Filter logcat
        ttk.Label(logcat_tool, text="Filter log lines:").pack(side="left", padx=(20, 5))
        self.ent_logcat_filter = ttk.Entry(logcat_tool, width=25)
        self.ent_logcat_filter.pack(side="left", padx=5)
        
        # Logcat text display
        self.logcat_text = tk.Text(logcat_main_frame, bg="#0d0d0d", fg="#00ff66", font=("Courier", 9), wrap="none", borderwidth=0)
        logcat_scroll_y = ttk.Scrollbar(logcat_main_frame, orient="vertical", command=self.logcat_text.yview)
        logcat_scroll_x = ttk.Scrollbar(logcat_main_frame, orient="horizontal", command=self.logcat_text.xview)
        
        self.logcat_text.configure(yscrollcommand=logcat_scroll_y.set, xscrollcommand=logcat_scroll_x.set)
        
        self.logcat_text.pack(side="top", fill="both", expand=True)
        logcat_scroll_y.pack(side="right", fill="y", before=self.logcat_text)
        logcat_scroll_x.pack(side="bottom", fill="x")


        # ------------------ GLOBAL CONSOLE LOG ------------------
        # Console Log at the very bottom (visible under all tabs)
        console_lf = ttk.LabelFrame(self.root, text=" Log Console ")
        console_lf.pack(fill="x", padx=15, pady=(5, 15))
        
        self.console_text = tk.Text(console_lf, height=4, bg="#1e1e1e", fg="#00ff66", font=("Courier", 9), wrap="word", borderwidth=0)
        self.console_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Initial logs
        self.log_message("System initialized. Searching for ADB devices...")

    def log_message(self, message):
        self.console_text.config(state="normal")
        self.console_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.console_text.see("end")
        self.console_text.config(state="disabled")

    def run_adb(self, cmd_list):
        try:
            res = subprocess.run(cmd_list, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return res.stdout.strip()
            else:
                return f"ERROR: {res.stderr.strip()}"
        except subprocess.TimeoutExpired:
            return "ERROR: ADB Timeout"
        except Exception as e:
            return f"ERROR: {str(e)}"

    def refresh_devices(self):
        out = self.run_adb(["adb", "devices"])
        lines = out.split("\n")
        self.device_list = []
        for line in lines[1:]:
            if "device" in line and not "devices" in line:
                parts = line.split()
                if parts:
                    self.device_list.append(parts[0])
        
        if self.device_list:
            self.selected_device.set(self.device_list[0])
            self.device_label.config(text=f"CONNECTED ({self.device_list[0]})", foreground="#00ff66")
            self.log_message(f"Connected to device: {self.device_list[0]}")
            # Fetch freezer states and load apps list
            self.update_freezer_checkbuttons()
            threading.Thread(target=self.load_installed_packages, daemon=True).start()
        else:
            self.selected_device.set("None")
            self.device_label.config(text="NO DEVICE CONNECTED", foreground="#ff3333")
            self.log_message("Warning: No devices detected. Check USB debugging connection.")

    def update_freezer_checkbuttons(self):
        out_freezer = self.run_adb(["adb", "shell", "device_config get activity_manager use_freezer"])
        self.var_freezer.set("true" in out_freezer.lower())
        
        out_restrict = self.run_adb(["adb", "shell", "device_config get activity_manager bg_current_drain_auto_restrict_abusive_apps_enabled"])
        self.var_restrict.set("true" in out_restrict.lower())

    def toggle_freezer(self):
        val = "true" if self.var_freezer.get() else "false"
        out = self.run_adb(["adb", "shell", f"device_config put activity_manager use_freezer {val}"])
        self.log_message(f"Cached Apps Freezer toggled to: {val.upper()}. System responded: {out}")

    def toggle_auto_restrict(self):
        val = "true" if self.var_restrict.get() else "false"
        out = self.run_adb(["adb", "shell", f"device_config put activity_manager bg_current_drain_auto_restrict_abusive_apps_enabled {val}"])
        self.log_message(f"Abusive Apps Auto-Restriction toggled to: {val.upper()}. System responded: {out}")

    def empty_trash(self):
        self.log_message("Emptying hidden recycle bins on device storage...")
        out1 = self.run_adb(["adb", "shell", "rm -rf /storage/emulated/0/MT2/.recycle/*"])
        out2 = self.run_adb(["adb", "shell", "rm -rf /storage/emulated/0/.trash-storage/*"])
        self.log_message("Trash cleared successfully! Reclaimed storage space.")
        self.poll_once()

    def quick_speedup(self):
        self.log_message("⚡ Triggering Quick Speed Up optimizations...")
        self.run_adb(["adb", "shell", "rm -rf /storage/emulated/0/MT2/.recycle/*"])
        self.run_adb(["adb", "shell", "rm -rf /storage/emulated/0/.trash-storage/*"])
        
        self.run_adb(["adb", "shell", "am stop-user -f 10"])
        self.run_adb(["adb", "shell", "am stop-user -f 11"])
        
        heavy_apps = ["com.instagram.android", "com.facebook.stella", "com.whatsapp", "com.lemon.lvoverseas", "com.google.android.googlequicksearchbox"]
        for app in heavy_apps:
            self.run_adb(["adb", "shell", f"am force-stop {app}"])
            
        self.log_message("⚡ Quick Speed Up done! Secondary profiles suspended, trash emptied, and background loops killed.")
        self.poll_once()

    def kill_selected_app(self):
        selected_item = self.proc_tree.selection()
        if not selected_item:
            messagebox.showwarning("Select App", "Please select a process from the table first.")
            return
            
        values = self.proc_tree.item(selected_item, "values")
        pid = values[0]
        name = values[4]
        user = values[1]
        
        pkg_name = self.get_package_from_display(name)
        
        user_id = 0
        if user.startswith("u10_"):
            user_id = 10
        elif user.startswith("u11_"):
            user_id = 11
            
        self.log_message(f"Killing process {pkg_name} (PID: {pid}) for user {user_id}...")
        
        if user_id > 0:
            self.run_adb(["adb", "shell", f"am force-stop --user {user_id} {pkg_name}"])
        else:
            self.run_adb(["adb", "shell", f"am force-stop {pkg_name}"])
            
        self.run_adb(["adb", "shell", f"kill -9 {pid} 2>/dev/null"])
        self.log_message(f"Process {pkg_name} terminated.")
        self.poll_once()

    def restrict_selected_app(self):
        selected_item = self.proc_tree.selection()
        if not selected_item:
            messagebox.showwarning("Select App", "Please select a process from the table first.")
            return
            
        values = self.proc_tree.item(selected_item, "values")
        name = values[4]
        pkg_name = self.get_package_from_display(name)
        
        self.log_message(f"Restricting background activities for: {pkg_name}...")
        self.run_adb(["adb", "shell", f"am set-standby-bucket {pkg_name} restricted"])
        self.run_adb(["adb", "shell", f"cmd appops set {pkg_name} RUN_IN_BACKGROUND ignore"])
        self.log_message(f"Success! {pkg_name} is now permanently restricted.")

    # ------------------ TAB 2: APP CONTROL OPERATIONS ------------------
    def load_installed_packages(self):
        if self.selected_device.get() == "None":
            return
        self.log_message("Loading third-party packages list from device...")
        
        enabled_out = self.run_adb(["adb", "shell", "pm list packages -3 -e"])
        disabled_out = self.run_adb(["adb", "shell", "pm list packages -3 -d"])
        
        enabled_list = [line.replace("package:", "").strip() for line in enabled_out.split("\n") if line.strip()]
        disabled_list = [line.replace("package:", "").strip() for line in disabled_out.split("\n") if line.strip()]
        
        self.all_packages = []
        for pkg in enabled_list:
            self.all_packages.append((pkg, "Enabled"))
        for pkg in disabled_list:
            self.all_packages.append((pkg, "Frozen/Disabled"))
            
        self.all_packages.sort(key=lambda x: x[0])
        self.filter_apps_list()
        self.log_message(f"Successfully loaded {len(self.all_packages)} third-party packages.")

    def filter_apps_list(self, *args):
        search_query = self.app_search_var.get().lower().strip()
        for row in self.app_tree.get_children():
            self.app_tree.delete(row)
        for pkg, status in self.all_packages:
            friendly_name = self.get_friendly_name(pkg)
            display_name = f"{friendly_name} ({pkg})"
            if not search_query or search_query in display_name.lower():
                self.app_tree.insert("", "end", values=(display_name, status))

    def on_app_selected(self, event):
        selected_item = self.app_tree.selection()
        if not selected_item:
            return
            
        values = self.app_tree.item(selected_item, "values")
        pkg_name = self.get_package_from_display(values[0])
        self.lbl_selected_app.config(text=pkg_name)
        
        bucket_out = self.run_adb(["adb", "shell", f"am get-standby-bucket {pkg_name} 2>/dev/null"])
        appop_out = self.run_adb(["adb", "shell", f"cmd appops get {pkg_name} RUN_IN_BACKGROUND 2>/dev/null"])
        
        bucket_map = {"10": "ACTIVE (10)", "20": "WORKING SET (20)", "30": "FREQUENT (30)", "40": "RARE (40)", "45": "RESTRICTED (45)"}
        bucket_desc = bucket_map.get(bucket_out.strip(), f"Other ({bucket_out.strip()})")
        
        appop_desc = "ALLOW"
        if "ignore" in appop_out.lower():
            appop_desc = "IGNORE/BLOCKED"
        elif "deny" in appop_out.lower():
            appop_desc = "DENIED/BLOCKED"
            
        self.lbl_app_bucket.config(text=f"Standby Bucket: {bucket_desc}")
        self.lbl_app_appop.config(text=f"Background AppOp: {appop_desc}")

    def freeze_selected_package(self):
        selected_item = self.app_tree.selection()
        if not selected_item:
            return
        pkg_display = self.app_tree.item(selected_item, "values")[0]
        pkg_name = self.get_package_from_display(pkg_display)
        self.log_message(f"Freezing (disabling) {pkg_name}...")
        out = self.run_adb(["adb", "shell", f"pm disable-user --user 0 {pkg_name}"])
        if "disabled" in out.lower() or "success" in out.lower():
            self.log_message(f"Successfully froze {pkg_name}.")
            self.load_installed_packages()
        else:
            self.log_message(f"Failed to freeze {pkg_name}. Error: {out}")

    def unfreeze_selected_package(self):
        selected_item = self.app_tree.selection()
        if not selected_item:
            return
        pkg_display = self.app_tree.item(selected_item, "values")[0]
        pkg_name = self.get_package_from_display(pkg_display)
        self.log_message(f"Unfreezing (enabling) {pkg_name}...")
        out = self.run_adb(["adb", "shell", f"pm enable {pkg_name}"])
        if "enabled" in out.lower() or "success" in out.lower():
            self.log_message(f"Successfully unfroze {pkg_name}.")
            self.load_installed_packages()
        else:
            self.log_message(f"Failed to unfreeze {pkg_name}. Error: {out}")

    def restrict_package_background(self):
        selected_item = self.app_tree.selection()
        if not selected_item:
            return
        pkg_display = self.app_tree.item(selected_item, "values")[0]
        pkg_name = self.get_package_from_display(pkg_display)
        self.log_message(f"Restricting background activities for: {pkg_name}...")
        self.run_adb(["adb", "shell", f"am set-standby-bucket {pkg_name} restricted"])
        self.run_adb(["adb", "shell", f"cmd appops set {pkg_name} RUN_IN_BACKGROUND ignore"])
        self.log_message(f"Success! {pkg_name} is now permanently restricted.")
        self.on_app_selected(None)

    def allow_package_background(self):
        selected_item = self.app_tree.selection()
        if not selected_item:
            return
        pkg_display = self.app_tree.item(selected_item, "values")[0]
        pkg_name = self.get_package_from_display(pkg_display)
        self.log_message(f"Restoring default background access for: {pkg_name}...")
        self.run_adb(["adb", "shell", f"am set-standby-bucket {pkg_name} active"])
        self.run_adb(["adb", "shell", f"cmd appops set {pkg_name} RUN_IN_BACKGROUND allow"])
        self.log_message(f"Success! Background access restored to defaults for {pkg_name}.")
        self.on_app_selected(None)

    def extract_selected_apk(self):
        selected_item = self.app_tree.selection()
        if not selected_item:
            messagebox.showwarning("Select App", "Please select an app from the list first.")
            return
        pkg_display = self.app_tree.item(selected_item, "values")[0]
        pkg_name = self.get_package_from_display(pkg_display)
        self.log_message(f"Locating APK path for {pkg_name}...")
        path_out = self.run_adb(["adb", "shell", f"pm path {pkg_name}"])
        
        # Matches package:/data/app/.../base.apk
        match = re.search(r'package:(.*\.apk)', path_out)
        if not match:
            self.log_message(f"Could not locate APK file path on phone. Response: {path_out}")
            return
            
        apk_remote_path = match.group(1)
        
        # Resolve desktop downloads folder
        dest_dir = os.path.expanduser("~/Downloads")
        if not os.path.exists(dest_dir):
            dest_dir = os.path.expanduser("~")
            
        local_apk_path = os.path.join(dest_dir, f"{pkg_name}.apk")
        
        self.log_message(f"Extracting APK to {local_apk_path}...")
        
        # Run pull in separate thread to prevent lockup
        def do_pull():
            res = self.run_adb(["adb", "pull", apk_remote_path, local_apk_path])
            if "error" not in res.lower() and "file pulled" in res.lower():
                self.log_message(f"Successfully extracted APK to: {local_apk_path}")
            else:
                self.log_message(f"Failed to pull APK file. Error: {res}")
                
        threading.Thread(target=do_pull, daemon=True).start()

    def uninstall_selected_package(self):
        selected_item = self.app_tree.selection()
        if not selected_item:
            return
        pkg_display = self.app_tree.item(selected_item, "values")[0]
        pkg_name = self.get_package_from_display(pkg_display)
        
        confirm = messagebox.askyesno("Uninstall Package", f"Are you sure you want to permanently uninstall {pkg_name} for the current user?")
        if not confirm:
            return
            
        self.log_message(f"Uninstalling {pkg_name}...")
        out = self.run_adb(["adb", "shell", f"pm uninstall --user 0 {pkg_name}"])
        if "success" in out.lower():
            self.log_message(f"Uninstall successful for {pkg_name}.")
            self.load_installed_packages()
        else:
            self.log_message(f"Uninstall failed. Error: {out}")


        # ------------------ TAB 3: SYSTEM TWEAKS OPERATIONS ------------------
    def set_animation_scales(self, value):
        self.log_message(f"Setting window/animator animation scales to {value}x...")
        self.run_adb(["adb", "shell", f"settings put global window_animation_scale {value}"])
        self.run_adb(["adb", "shell", f"settings put global transition_animation_scale {value}"])
        self.run_adb(["adb", "shell", f"settings put global animator_duration_scale {value}"])
        self.log_message("Animation speeds updated successfully.")

    def set_dark_mode(self, enabled):
        val = "yes" if enabled else "no"
        mode_str = "DARK" if enabled else "LIGHT"
        self.log_message(f"Forcing system-wide UI theme to {mode_str} mode...")
        out = self.run_adb(["adb", "shell", f"cmd uimode night {val}"])
        self.log_message(f"System theme mode updated: {out}")

    def set_private_dns(self, enabled):
        if enabled:
            self.log_message("Enabling Private DNS Ad-Blocking (dns.adguard.com)...")
            self.run_adb(["adb", "shell", "settings put global private_dns_mode hostname"])
            out = self.run_adb(["adb", "shell", "settings put global private_dns_specifier dns.adguard.com"])
        else:
            self.log_message("Disabling Private DNS Ad-Blocking...")
            out = self.run_adb(["adb", "shell", "settings put global private_dns_mode opportunity"])
        self.log_message(f"Private DNS updated: {out}")

    def launch_scrcpy(self):
        # Launches scrcpy on host PC in background thread
        self.log_message("Attempting to launch scrcpy mirroring service...")
        
        # Verify scrcpy in path or snap bin
        scrcpy_cmd = "scrcpy"
        try:
            subprocess.run(["which", "scrcpy"], capture_output=True, check=True)
        except:
            if os.path.exists("/snap/bin/scrcpy"):
                scrcpy_cmd = "/snap/bin/scrcpy"
            else:
                self.log_message("⚠️ Error: 'scrcpy' not detected on your Linux PC.")
                messagebox.showerror("scrcpy Missing", "scrcpy is not installed on this PC.")
                return
            
        def run_mirror():
            env_vars = os.environ.copy()
            env_vars["SNAP_LAUNCHER_NOTICE_ENABLED"] = "false"
            res = subprocess.run([scrcpy_cmd, "--window-title", "ADB Mirror Stream"], capture_output=True, text=True, env=env_vars)
            if res.returncode != 0:
                self.log_message(f"scrcpy closed with code {res.returncode}. Output: {res.stderr.strip()}")
            else:
                self.log_message("Mirror stream session closed.")
                
        threading.Thread(target=run_mirror, daemon=True).start()

    def capture_screenshot(self):
        dest_dir = os.path.expanduser("~/Downloads")
        if not os.path.exists(dest_dir):
            dest_dir = os.path.expanduser("~")
            
        filename = f"screenshot_{int(time.time())}.png"
        local_path = os.path.join(dest_dir, filename)
        
        self.log_message("📸 Capturing phone screen...")
        
        def do_capture():
            self.run_adb(["adb", "shell", "screencap -p /sdcard/temp_screenshot.png"])
            res = self.run_adb(["adb", "pull", "/sdcard/temp_screenshot.png", local_path])
            self.run_adb(["adb", "shell", "rm /sdcard/temp_screenshot.png"])
            
            if "file pulled" in res.lower():
                self.log_message(f"📸 Screenshot successfully saved to PC: {local_path}")
            else:
                self.log_message(f"Failed to capture screenshot. Error: {res}")
                
        threading.Thread(target=do_capture, daemon=True).start()

    def capture_screen_video(self):
        dest_dir = os.path.expanduser("~/Downloads")
        if not os.path.exists(dest_dir):
            dest_dir = os.path.expanduser("~")
            
        filename = f"screenrecord_{int(time.time())}.mp4"
        local_path = os.path.join(dest_dir, filename)
        
        self.log_message("🎥 Recording phone screen for 10 seconds. Keep the screen active...")
        
        def do_record():
            # records up to 10 seconds
            self.run_adb(["adb", "shell", "screenrecord --time-limit 10 /sdcard/temp_record.mp4"])
            self.log_message("🎥 Recording complete. Pulling video file to PC...")
            res = self.run_adb(["adb", "pull", "/sdcard/temp_record.mp4", local_path])
            self.run_adb(["adb", "shell", "rm /sdcard/temp_record.mp4"])
            
            if "file pulled" in res.lower():
                self.log_message(f"🎥 Video recording successfully saved to PC: {local_path}")
            else:
                self.log_message(f"Failed to pull video file. Error: {res}")
                
        threading.Thread(target=do_record, daemon=True).start()


        # ------------------ TAB 4: FILE TRANSFER & STORAGE OPERATIONS ------------------
    def scan_large_files(self):
        if self.selected_device.get() == "None":
            return
            
        self.lbl_scan_status.config(text="Scanning...", foreground="#ffcc00")
        self.log_message("Scanning device storage for files larger than 100MB...")
        
        # Clear Treeview
        for row in self.file_tree.get_children():
            self.file_tree.delete(row)
            
        def do_scan():
            # Searches /sdcard up to depth 5 for speed
            out = self.run_adb(["adb", "shell", "find /storage/emulated/0 -maxdepth 5 -type f -size +100M -exec du -h {} \\; 2>/dev/null"])
            lines = out.split("\n")
            
            count = 0
            for line in lines:
                parts = line.split(None, 1)
                if len(parts) == 2:
                    self.file_tree.insert("", "end", values=(parts[0], parts[1]))
                    count += 1
            
            self.lbl_scan_status.config(text=f"Scan complete ({count} files)", foreground="#00ff66")
            self.log_message(f"Scan complete. Found {count} files larger than 100MB.")
            
        threading.Thread(target=do_scan, daemon=True).start()

    def browse_local_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.ent_local_path.delete(0, tk.END)
            self.ent_local_path.insert(0, file_path)

    def push_file_to_phone(self):
        local_path = self.ent_local_path.get().strip()
        remote_path = self.ent_phone_path.get().strip()
        
        if not local_path or not os.path.exists(local_path):
            messagebox.showwarning("Invalid File", "Please select a valid local PC file to push.")
            return
            
        self.log_message(f"Uploading file to phone: {local_path} ➔ {remote_path}...")
        
        def do_push():
            res = self.run_adb(["adb", "push", local_path, remote_path])
            if "error" not in res.lower() and ("pushed" in res.lower() or "file" in res.lower()):
                self.log_message(f"Upload successful: {res}")
            else:
                self.log_message(f"Upload failed: {res}")
                
        threading.Thread(target=do_push, daemon=True).start()

    def pull_file_from_phone(self):
        # Pulls selected file from list, or custom path from entry if selected in Treeview
        selected_item = self.file_tree.selection()
        remote_path = ""
        
        if selected_item:
            remote_path = self.file_tree.item(selected_item, "values")[1]
        else:
            remote_path = self.ent_phone_path.get().strip()
            
        if not remote_path:
            messagebox.showwarning("Invalid File", "Please select a file from the list or write a path in the destination entry.")
            return
            
        dest_dir = os.path.expanduser("~/Downloads")
        if not os.path.exists(dest_dir):
            dest_dir = os.path.expanduser("~")
            
        filename = os.path.basename(remote_path)
        local_path = os.path.join(dest_dir, filename)
        
        self.log_message(f"Downloading file from phone: {remote_path} ➔ {local_path}...")
        
        def do_pull():
            res = self.run_adb(["adb", "pull", remote_path, local_path])
            if "error" not in res.lower() and "file pulled" in res.lower():
                self.log_message(f"Download successful: File saved to {local_path}")
            else:
                self.log_message(f"Download failed: {res}")
                
        threading.Thread(target=do_pull, daemon=True).start()


        # ------------------ TAB 5: LIVE LOGCAT VIEWER OPERATIONS ------------------
    def toggle_logcat(self):
        if self.logcat_running:
            # Stop logcat
            self.stop_logcat_stream()
        else:
            # Start logcat
            self.start_logcat_stream()

    def start_logcat_stream(self):
        if self.selected_device.get() == "None":
            messagebox.showwarning("Device Offline", "No active device connected.")
            return
            
        self.logcat_running = True
        self.btn_logcat_toggle.config(text="⏸️ Pause Logcat Stream", style="Danger.TButton")
        self.log_message("Live Logcat stream started.")
        
        # Clear terminal logcat buffer on phone to show fresh logs
        self.run_adb(["adb", "logcat", "-c"])
        
        # Run logcat in separate process thread
        def stream_logcat():
            try:
                self.logcat_process = subprocess.Popen(
                    ["adb", "logcat", "-v", "time"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                
                # Read stdout line by line
                for line in iter(self.logcat_process.stdout.readline, ''):
                    if not self.logcat_running:
                        break
                        
                    # Filter matching
                    filter_val = self.ent_logcat_filter.get().strip().lower()
                    if filter_val and filter_val not in line.lower():
                        continue
                        
                    # Append line safely to Tkinter text box from thread
                    self.append_logcat_line(line)
                    
            except Exception as e:
                self.log_message(f"Logcat streaming error: {str(e)}")
            finally:
                self.stop_logcat_stream()
                
        threading.Thread(target=stream_logcat, daemon=True).start()

    def append_logcat_line(self, line):
        # Safely insert from background threads
        def task():
            self.logcat_text.config(state="normal")
            self.logcat_text.insert("end", line)
            
            # Limit lines to prevent RAM bloating on PC
            line_count = int(self.logcat_text.index('end-1c').split('.')[0])
            if line_count > 500:
                self.logcat_text.delete("1.0", "2.0")
                
            self.logcat_text.see("end")
            self.logcat_text.config(state="disabled")
            
        self.root.after(0, task)

    def stop_logcat_stream(self):
        self.logcat_running = False
        self.btn_logcat_toggle.config(text="▶️ Start Live Logcat", style="Action.TButton")
        
        if self.logcat_process:
            self.logcat_process.terminate()
            self.logcat_process = None
            
        self.log_message("Live Logcat stream paused.")

    def clear_logcat_text(self):
        self.logcat_text.config(state="normal")
        self.logcat_text.delete("1.0", tk.END)
        self.logcat_text.config(state="disabled")
        self.log_message("Logcat console text cleared.")


        # ------------------ TAB 1 POLLING METRICS ------------------
    def poll_once(self):
        threading.Thread(target=self.update_metrics_ui, daemon=True).start()

    def poll_device_metrics(self):
        while self.is_running:
            if self.selected_device.get() == "None":
                self.refresh_devices()
                time.sleep(4)
                continue
            
            self.update_metrics_ui()
            time.sleep(3)

    def update_metrics_ui(self):
        uptime_out = self.run_adb(["adb", "shell", "uptime"])
        load_match = re.search(r'load average:\s*([\d\.]+),\s*([\d\.]+),\s*([\d\.]+)', uptime_out)
        if load_match:
            try:
                l1 = float(load_match.group(1))
                self.cpu_load_1min = l1
                if l1 < 4.0:
                    desc = "Normal 🟢"
                elif l1 < 8.0:
                    desc = "Moderate Load 🟡"
                elif l1 < 12.0:
                    desc = "High Load ⚠️"
                else:
                    desc = "Extreme Overload 🛑"
                self.cpu_lbl.config(text=f"{load_match.group(1)}, {load_match.group(2)}, {load_match.group(3)} ({desc})")
            except ValueError:
                self.cpu_lbl.config(text=f"{load_match.group(1)}, {load_match.group(2)}, {load_match.group(3)}")
        else:
            self.cpu_lbl.config(text="N/A")

        battery_out = self.run_adb(["adb", "shell", "dumpsys battery 2>/dev/null"])
        bat_level = "--"
        bat_temp = "--"
        bat_status = "Unknown"
        for line in battery_out.split("\n"):
            if "level:" in line:
                bat_level = re.search(r'\d+', line).group()
            elif "temperature:" in line:
                temp_raw = re.search(r'\d+', line).group()
                bat_temp = f"{float(temp_raw)/10:.1f}°C"
            elif "status:" in line:
                stat_code = re.search(r'\d+', line).group()
                stat_map = {"2": "Charging ⚡", "3": "Discharging 🔋", "4": "Not Charging", "5": "Full 🔋"}
                bat_status = stat_map.get(stat_code, "Unknown")
        self.battery_lbl.config(text=f"{bat_level}% | {bat_temp} | Status: {bat_status}")

        meminfo = self.run_adb(["adb", "shell", "cat /proc/meminfo 2>/dev/null"])
        mem_total = 0
        mem_free = 0
        swap_total = 0
        swap_free = 0
        for line in meminfo.split("\n"):
            if "MemTotal" in line:
                mem_total = int(re.search(r'\d+', line).group())
            elif "MemFree" in line:
                mem_free = int(re.search(r'\d+', line).group())
            elif "SwapTotal" in line:
                swap_total = int(re.search(r'\d+', line).group())
            elif "SwapFree" in line:
                swap_free = int(re.search(r'\d+', line).group())

        if mem_total > 0:
            ram_used = mem_total - mem_free
            ram_pct = (ram_used / mem_total) * 100
            self.ram_bar['value'] = ram_pct
            self.ram_lbl.config(text=f"{ram_used // 1024} MB / {mem_total // 1024} MB ({int(ram_pct)}%)")
            
        if swap_total > 0:
            swap_used = swap_total - swap_free
            swap_pct = (swap_used / swap_total) * 100
            self.swap_bar['value'] = swap_pct
            self.swap_lbl.config(text=f"{swap_used // 1024} MB / {swap_total // 1024} MB ({int(swap_pct)}%)")
        else:
            self.swap_bar['value'] = 0
            self.swap_lbl.config(text="No Swap Active")

        df_out = self.run_adb(["adb", "shell", "df -h /data 2>/dev/null"])
        lines = df_out.split("\n")
        if len(lines) > 1:
            parts = lines[1].split()
            if len(parts) >= 5:
                try:
                    self.storage_lbl.config(text=f"Used {parts[2]} / {parts[1]} ({parts[4]} Free: {parts[3]})")
                    pct_val = int(parts[4].replace("%", ""))
                    self.storage_bar['value'] = pct_val
                except (ValueError, IndexError):
                    pass

        users_out = self.run_adb(["adb", "shell", "pm list users"])
        self.clone_lbl.config(text="RUNNING" if "10:CloneUser" in users_out and "running" in users_out else "STOPPED",
                              foreground="#00ff66" if "10:CloneUser" in users_out and "running" in users_out else "#ff3333")
        self.island_lbl.config(text="RUNNING" if "11: Island" in users_out and "running" in users_out else "STOPPED",
                               foreground="#00ff66" if "11: Island" in users_out and "running" in users_out else "#ff3333")

        trash_out1 = self.run_adb(["adb", "shell", "du -sh /storage/emulated/0/MT2/.recycle 2>/dev/null"])
        trash_out2 = self.run_adb(["adb", "shell", "du -sh /storage/emulated/0/.trash-storage 2>/dev/null"])
        size_str = "0 MB"
        try:
            m1 = trash_out1.split()[0] if trash_out1 and "ERROR" not in trash_out1 else "0"
            m2 = trash_out2.split()[0] if trash_out2 and "ERROR" not in trash_out2 else "0"
            size_str = f"MT Recycle: {m1} | System Trash: {m2}"
        except:
            pass
        self.trash_lbl.config(text=size_str)

        top_out = self.run_adb(["adb", "shell", "top -b -n 1 2>/dev/null"])
        procs = []
        lines = top_out.split("\n")
        for line in lines:
            parts = line.split()
            if len(parts) >= 12 and parts[0].isdigit():
                pid = parts[0]
                user = parts[1]
                res = parts[5]
                cpu_str = parts[8].replace("%", "")
                name = parts[11]
                try:
                    cpu_val = float(cpu_str)
                    if cpu_val > 1.0 or "top" not in name:
                        procs.append((pid, user, cpu_val, res, name))
                except ValueError:
                    continue
        
        # Sort by CPU% descending
        procs.sort(key=lambda x: x[2], reverse=True)
        
        # Clear Table & Insert
        for row in self.proc_tree.get_children():
            self.proc_tree.delete(row)
            
        for proc in procs[:25]:
            friendly_name = self.get_friendly_name(proc[4])
            display_name = f"{friendly_name} ({proc[4]})"
            self.proc_tree.insert("", "end", values=(proc[0], proc[1], f"{proc[2]}%", proc[3], display_name))
            
        # Diagnostics
        if self.cpu_load_1min >= 8.0:
            primary_offender = None
            for p in procs[:5]:
                p_name = p[4]
                p_cpu = p[2]
                if p_cpu > 15.0 and not p_name.startswith("[") and p_name != "top":
                    primary_offender = p
                    break
            
            if primary_offender:
                offender_name = primary_offender[4]
                friendly_offender = self.get_friendly_name(offender_name)
                offender_cpu = primary_offender[2]
                self.cpu_analysis_lbl.config(
                    text=f"🚨 Overload Reason: '{friendly_offender}' is consuming {offender_cpu}% CPU. Select it and click 'Kill App'!", 
                    foreground="#ff3333"
                )
            else:
                self.cpu_analysis_lbl.config(
                    text="🚨 Overload Reason: High system overhead. System is swapping memory (ZRAM) due to low RAM. Click 'Quick Speed Up'!",
                    foreground="#ffaa00"
                )
        else:
            self.cpu_analysis_lbl.config(
                text="🟢 System status: Running smoothly.", 
                foreground="#00ff66"
            )

    def on_closing(self):
        self.is_running = False
        self.stop_logcat_stream()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ADBOptimizerGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
