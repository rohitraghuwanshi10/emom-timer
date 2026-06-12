import customtkinter as ctk
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime
import storage

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
ACCENT_PURPLE = "#BF5AF2"

# Nord Palette for Workouts (consistent with history_ui.py)
ACCENT_COLORS = ["#5E81AC", "#88C0D0", "#A3BE8C", "#EBCB8B", "#D08770", "#B48EAD"]

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
        
        for i in range(4):
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

    def update_view(self, data, max_hr_profile=None, profile_name="Default"):
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
            ("Rounds", str(data.get("total_rounds_completed", 0)), TEXT_COLOR),
            ("Total Time", fmt_sec(data.get("total_time_sec", 0)), TEXT_COLOR),
            ("Work Time", fmt_sec(data.get("work_time_sec", 0)), ACCENT_GREEN),
            ("Rest Time", fmt_sec(data.get("rest_time_sec", 0)), ACCENT_ORANGE),
            ("Peak HR", f"{data.get('max_hr', 0)} BPM", ACCENT_RED),
            ("Avg HR", f"{data.get('avg_hr', 0)} BPM", ACCENT_BLUE),
            ("Calories", f"{data.get('calories_burnt_kcal', 0)} kcal", ACCENT_PURPLE),
        ]
        
        # Row 1
        for i, (title, val, col) in enumerate(stats[:4]):
             var = ctk.StringVar(value=val)
             self._create_stat_card(self.stats_frame, 0, i, title, var, col)
             
        # Row 2 (HR)
        if data.get("max_hr", 0) > 0:
             for i, (title, val, col) in enumerate(stats[4:]):
                 var = ctk.StringVar(value=val)
                 self._create_stat_card(self.stats_frame, 1, i, title, var, col)
                 
        # Notes
        notes = data.get("workout_notes", "")
        if notes:
            lbl = ctk.CTkLabel(self.stats_frame, text=f"Notes: {notes}", font=("Arial", 14), text_color=TEXT_SECONDARY)
            lbl.grid(row=2, column=0, columnspan=4, pady=10)

        # Load all workouts of the same day for this profile
        day_workouts = []
        try:
            start_time_str = data.get("start_time", "")
            if start_time_str:
                selected_dt = datetime.datetime.fromisoformat(start_time_str)
                selected_date = selected_dt.date()
                
                # Load history to find other files
                history = storage.load_history(profile_name)
                # Find column index for workout_details_file
                if history:
                    headers = history[0]
                    file_col_idx = -1
                    if "workout_details_file" in headers:
                        file_col_idx = headers.index("workout_details_file")
                    elif "Details File" in headers:
                        file_col_idx = headers.index("Details File")
                    
                    if file_col_idx != -1:
                        # Scan through history
                        for row in history[1:]:
                            if len(row) > 0:
                                try:
                                    row_dt = datetime.datetime.fromisoformat(row[0])
                                    if row_dt.date() == selected_date:
                                        if file_col_idx < len(row):
                                            fname = row[file_col_idx]
                                            w_details = storage.load_workout_details_json(fname)
                                            if w_details:
                                                day_workouts.append(w_details)
                                except Exception as ex:
                                    print(f"Error reading row or details file: {ex}")
        except Exception as e:
            print(f"Error loading day workouts: {e}")

        # Fallback/Safety: make sure selected data is included
        if not any(w.get("start_time") == data.get("start_time") for w in day_workouts):
            day_workouts.append(data)

        # Sort day_workouts by start_time
        day_workouts.sort(key=lambda w: w.get("start_time", ""))

        # Graph
        self._render_graph(day_workouts, max_hr_profile, selected_start_time=data.get("start_time"))

    def _render_graph(self, workouts, max_hr_profile, selected_start_time=None):
        # Clear/Create Graph Frame
        if hasattr(self, 'graph_container'):
            self.graph_container.destroy()
            
        self.graph_container = ctk.CTkFrame(self, fg_color=CARD_COLOR, corner_radius=15)
        self.graph_container.grid(row=2, column=0, padx=20, pady=20, sticky="nsew")
        
        # Check if there's any heart rate data at all in any workout
        has_any_hr = any(w.get("hr_details") for w in workouts)
        if not has_any_hr:
             ctk.CTkLabel(self.graph_container, text="No Heart Rate Data Available", font=("Arial", 16)).place(relx=0.5, rely=0.5, anchor="center")
             return

        # Plotting Setup
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

        # We will iterate through workouts and plot them sequentially with an offset
        offset = 0.0
        gap = 1.0 # 1 minute gap between workouts on the timeline
        
        all_plotted_times = []
        all_plotted_bpms = []
        
        for idx, w_data in enumerate(workouts):
            hr_details = w_data.get("hr_details", [])
            if not hr_details:
                continue
                
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
                    times.append(offset + (delta / 60.0))
                    bpms.append(bpm)
            except Exception as e:
                print(f"Error parsing graph data for workout {idx+1}: {e}")
                continue
                
            if not times:
                continue
            
            # Determine color from ACCENT_COLORS Nord palette (consistent with history_ui.py)
            color = ACCENT_COLORS[idx % len(ACCENT_COLORS)]
            
            is_selected = (w_data.get("start_time") == selected_start_time)
            
            # Label
            lbl_text = f"WO {idx+1}"
            if is_selected:
                lbl_text += " (Selected)"
                
            # Plot line and fill
            # Selected workout line is slightly thicker
            linewidth = 3 if is_selected else 1.8
            ax.plot(times, bpms, color=color, linewidth=linewidth, label=lbl_text)
            ax.fill_between(times, bpms, 40, color=color, alpha=0.1)
            
            # Draw vertical dashed separator line at the start of workout (if not the first one)
            if offset > 0:
                ax.axvline(x=times[0], color='#555555', linestyle='--', linewidth=1, alpha=0.7)
            
            # Label at the top using blended transform (data x, axes y)
            mid_time = (times[0] + times[-1]) / 2.0
            y_pos = 0.95
            
            # Add a subtle background box or highlight to the selected text label to make it pop
            transform = mtransforms.blended_transform_factory(ax.transData, ax.transAxes)
            bbox_dict = dict(boxstyle="round,pad=0.2", fc="#2C2C2E", ec=color, alpha=0.9, lw=1) if is_selected else None
            fontweight = "bold" if is_selected else "normal"
            ax.text(mid_time, y_pos, f"WO {idx+1}", color=color, fontsize=9, ha="center", va="top", 
                    fontweight=fontweight, transform=transform, bbox=bbox_dict)
            
            # Record points for axis scaling
            all_plotted_times.extend(times)
            all_plotted_bpms.extend(bpms)
            
            # Update offset for next workout
            offset = times[-1] + gap

        # Set Minimum/Maximum Y
        if all_plotted_bpms:
            max_bpm = max(all_plotted_bpms)
            ax.set_ylim(bottom=40, top=max(140, max_bpm + 15))
        else:
            ax.set_ylim(bottom=40)
            
        # Format Axis
        ax.set_xlabel("Cumulative Time (min)", color=TEXT_SECONDARY, fontsize=9)
        ax.set_ylabel("Heart Rate (BPM)", color=TEXT_SECONDARY, fontsize=9)
        ax.set_title("Cumulative Daily Heart Rate Intensity", color="white", fontsize=11, pad=15)
        
        ax.grid(color="#333333", linestyle='--', linewidth=0.5)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color("#333333")
        ax.spines['bottom'].set_color("#333333")
        ax.tick_params(colors=TEXT_SECONDARY)
        
        # Add a subtle legend if there are multiple workouts
        handles, labels = ax.get_legend_handles_labels()
        if len(labels) > 1:
            ax.legend(handles, labels, loc="upper right", frameon=False, fontsize=8, labelcolor=TEXT_SECONDARY)
            
        # Ensure labels are visible
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=self.graph_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
