import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime

# Theme Constants matched from main.py
BG_COLOR = "#000000"
CARD_COLOR = "#1C1C1E"
TEXT_COLOR = "#FFFFFF"
TEXT_SECONDARY = "#8E8E93"
ACCENT_BLUE = "#0A84FF"
ACCENT_GREEN = "#30D158"
ACCENT_ORANGE = "#FF9F0A"
ACCENT_RED = "#FF453A"
ACCENT_YELLOW = "#FFD60A"

class DetailsFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color=BG_COLOR)
        
        # Grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Header
        self.grid_rowconfigure(1, weight=0) # Stats
        self.grid_rowconfigure(2, weight=1) # Graph
        
        # 1. Header (Date/Title)
        self.lbl_title = ctk.CTkLabel(self, text="Workout Details", font=("Arial", 24, "bold"), text_color=TEXT_COLOR)
        self.lbl_title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # 2. Stats Grid
        self.stats_frame = ctk.CTkFrame(self, fg_color=CARD_COLOR, corner_radius=15)
        self.stats_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        for i in range(3):
            self.stats_frame.grid_columnconfigure(i, weight=1)
            
        # Placeholders
        self.stat_widgets = {}
        
    def _create_stat_card(self, parent, row, col, title, value_var, color=TEXT_COLOR):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=row, column=col, padx=10, pady=10)
        
        t = ctk.CTkLabel(f, text=title, font=("Arial", 12), text_color=TEXT_SECONDARY)
        t.pack()
        
        v = ctk.CTkLabel(f, textvariable=value_var, font=("Arial", 20, "bold"), text_color=color)
        v.pack()

    def update_view(self, data, max_hr_profile=None):
        # Clear existing
        for w in self.stats_frame.winfo_children():
            w.destroy()
            
        # Parse Dates
        try:
            start_dt = datetime.datetime.fromisoformat(data.get("start_time", ""))
            date_str = start_dt.strftime("%B %d, %Y at %I:%M %p")
        except:
            date_str = "Unknown Date"
            
        self.lbl_title.configure(text=f"Workout: {date_str}")
        
        # Helper for formatting
        def fmt_sec(s):
            try:
                s = int(float(s))
                h = s // 3600
                m = (s % 3600) // 60
                sec = s % 60
                return f"{h:02}:{m:02}:{sec:02}"
            except:
                return "00:00:00"

        # Stats to show
        stats = [
            ("Total Time", fmt_sec(data.get("total_time_sec", 0)), TEXT_COLOR),
            ("Work Time", fmt_sec(data.get("work_time_sec", 0)), ACCENT_GREEN),
            ("Rest Time", fmt_sec(data.get("rest_time_sec", 0)), ACCENT_ORANGE),
            ("Peak HR", f"{data.get('max_hr', 0)} BPM", ACCENT_RED),
            ("Avg HR", f"{data.get('avg_hr', 0)} BPM", ACCENT_BLUE),
        ]
        
        # Row 1
        for i, (title, val, col) in enumerate(stats[:3]):
             var = ctk.StringVar(value=val)
             self._create_stat_card(self.stats_frame, 0, i, title, var, col)
             
        # Row 2 (HR)
        if data.get("max_hr", 0) > 0:
             for i, (title, val, col) in enumerate(stats[3:]):
                 var = ctk.StringVar(value=val)
                 self._create_stat_card(self.stats_frame, 1, i, title, var, col)
                 
        # Notes
        notes = data.get("workout_notes", "")
        if notes:
            lbl = ctk.CTkLabel(self.stats_frame, text=f"Notes: {notes}", font=("Arial", 14), text_color=TEXT_SECONDARY)
            lbl.grid(row=2, column=0, columnspan=3, pady=10)

        # Graph
        hr_details = data.get("hr_details", [])
        self._render_graph(hr_details, max_hr_profile)

    def _render_graph(self, hr_details, max_hr_profile):
        # Clear/Create Graph Frame
        if hasattr(self, 'graph_container'):
            self.graph_container.destroy()
            
        self.graph_container = ctk.CTkFrame(self, fg_color=CARD_COLOR, corner_radius=15)
        self.graph_container.grid(row=2, column=0, padx=20, pady=20, sticky="nsew")
        
        if not hr_details:
             ctk.CTkLabel(self.graph_container, text="No Heart Rate Data Available", font=("Arial", 16)).place(relx=0.5, rely=0.5, anchor="center")
             return

        # Prepare Data
        times = []
        bpms = []
        start_ts = None
        
        try:
             for item in hr_details:
                 ts_str = item.get("capture_time")
                 bpm = item.get("bpm")
                 if not ts_str or not bpm: continue
                 
                 dt = datetime.datetime.fromisoformat(ts_str)
                 if start_ts is None: start_ts = dt
                 
                 delta = (dt - start_ts).total_seconds()
                 times.append(delta)
                 bpms.append(bpm)
        except Exception as e:
            print(f"Error parsing graph data: {e}")
            return

        if not times: return
        
        # Plotting
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
        fig.patch.set_facecolor(CARD_COLOR)
        ax.set_facecolor(CARD_COLOR)
        
        # Draw Zones if Max HR available
        if max_hr_profile:
            try:
                mh = int(max_hr_profile)
                # Zones: 50, 60, 70, 80, 90, 100
                zones = [
                    (0.5 * mh, 0.6 * mh, '#1C1C1E'), # Warmup (Invisible/Bg)
                    (0.6 * mh, 0.7 * mh, ACCENT_BLUE), # Z1
                    (0.7 * mh, 0.8 * mh, ACCENT_GREEN), # Z2
                    (0.8 * mh, 0.9 * mh, ACCENT_YELLOW), # Z3
                    (0.9 * mh, 1.0 * mh, ACCENT_ORANGE), # Z4
                    (1.0 * mh, 1.2 * mh, ACCENT_RED), # Z5
                ]
                
                for low, high, color in zones:
                    if color != '#1C1C1E':
                        ax.axhspan(low, high, color=color, alpha=0.15, linewidth=0)
            except:
                pass

        ax.plot(times, bpms, color=ACCENT_RED, linewidth=2)
        ax.fill_between(times, bpms, 0, color=ACCENT_RED, alpha=0.1)
        
        # Format Axis
        ax.set_xlabel("Time (s)", color=TEXT_SECONDARY, fontsize=9)
        ax.set_ylabel("Heart Rate (BPM)", color=TEXT_SECONDARY, fontsize=9)
        ax.set_title("Heart Rate Intensity", color="white", fontsize=11, pad=10)
        
        ax.grid(color="#333333", linestyle='--', linewidth=0.5)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color("#333333")
        ax.spines['bottom'].set_color("#333333")
        ax.tick_params(colors=TEXT_SECONDARY)
        
        canvas = FigureCanvasTkAgg(fig, master=self.graph_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
