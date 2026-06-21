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

class EditNotesDialog(ctk.CTkToplevel):
    def __init__(self, parent, current_notes, on_save):
        super().__init__(parent)
        self.title("Edit Workout Notes")
        self.geometry("400x250")
        self.resizable(False, False)
        self.configure(fg_color=CARD_COLOR)
        
        # Make modal
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        
        # Center the window relative to parent
        self.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        x = parent_x + (parent_w - 400) // 2
        y = parent_y + (parent_h - 250) // 2
        self.geometry(f"+{x}+{y}")
        
        # Title Label
        lbl_title = ctk.CTkLabel(self, text="Edit Workout Notes", font=("Arial", 16, "bold"), text_color=TEXT_COLOR)
        lbl_title.pack(pady=(15, 10))
        
        # TextBox for multi-line notes
        self.textbox = ctk.CTkTextbox(self, width=360, height=120, fg_color=BG_COLOR, text_color=TEXT_COLOR, corner_radius=10)
        self.textbox.pack(padx=20, pady=5)
        self.textbox.insert("1.0", current_notes)
        
        # Buttons Frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)
        
        btn_cancel = ctk.CTkButton(btn_frame, text="Cancel", fg_color="#555555", hover_color="#444444", width=100, height=30, corner_radius=15, command=self.destroy)
        btn_cancel.pack(side="left", padx=(40, 10))
        
        def save_clicked():
            new_notes = self.textbox.get("1.0", "end-1c").strip()
            on_save(new_notes)
            self.destroy()
            
        btn_save = ctk.CTkButton(btn_frame, text="Save", fg_color=ACCENT_BLUE, hover_color="#0060df", width=100, height=30, corner_radius=15, command=save_clicked)
        btn_save.pack(side="right", padx=(10, 40))

class DetailsFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color=BG_COLOR)
        
        # Grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Header
        self.grid_rowconfigure(1, weight=0) # Stats
        self.grid_rowconfigure(2, weight=1) # Graph
        
        # 1. Header (Date/Title + Export Button)
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        self.lbl_title = ctk.CTkLabel(self.header_frame, text="Workout Details", font=("Arial", 24, "bold"), text_color=TEXT_COLOR)
        self.lbl_title.pack(side="left")
        
        self.btn_export = ctk.CTkButton(self.header_frame, text="📤 Export Day to CSV", command=self.export_day_csv,
                                        fg_color=ACCENT_BLUE, hover_color="#0060df", height=30, corner_radius=15,
                                        font=("Arial", 12, "bold"), state="disabled")
        self.btn_export.pack(side="right")
        
        self.current_day_workouts = []
        self.current_profile_name = "Default"
        self.current_date_str = ""
        
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
            date_str = start_dt.strftime("%B %d, %Y")
        except:
            date_str = "Unknown Date"
            
        self.lbl_title.configure(text=f"Workouts for {date_str}")
        
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

        # Load all workouts of the same day for this profile from SQLite
        day_workouts = []
        try:
            start_time_str = data.get("start_time", "")
            if start_time_str and profile_name:
                day_workouts = storage.get_workouts_for_day(profile_name, start_time_str)
        except Exception as e:
            print(f"Error loading day workouts: {e}")

        # Fallback/Safety: make sure selected data is included
        if not any(w.get("start_time") == data.get("start_time") for w in day_workouts):
            day_workouts.append(data)

        # Sort day_workouts by start_time
        day_workouts.sort(key=lambda w: w.get("start_time", ""))

        self.current_day_workouts = day_workouts
        self.current_profile_name = profile_name
        self.current_date_str = date_str
        self.btn_export.configure(state="normal")

        # Configure self.stats_frame to stretch row frames horizontally
        self.stats_frame.grid_columnconfigure(0, weight=1)

        # Table Headers
        headers = ["Workout", "Start Time", "Rounds", "Total Time", "Work Time", "Rest Time", "Peak HR (BPM)", "Avg HR (BPM)", "Calories (kcal)", "Notes"]
        
        # Header Row Frame
        header_frame = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        for c_idx in range(len(headers)):
            header_frame.grid_columnconfigure(c_idx, weight=3 if c_idx == 9 else 1, uniform="col_group")

        # Render Headers
        for col_idx, header in enumerate(headers):
            sticky = "w" if col_idx == 9 or col_idx == 0 else ""
            lbl = ctk.CTkLabel(header_frame, text=header, font=("Arial", 12, "bold"), text_color=TEXT_SECONDARY)
            if sticky:
                lbl.grid(row=0, column=col_idx, padx=10, pady=2, sticky=sticky)
            else:
                lbl.grid(row=0, column=col_idx, padx=10, pady=2)

        # Render Rows
        for row_idx, w_data in enumerate(day_workouts, start=1):
            color = ACCENT_COLORS[(row_idx - 1) % len(ACCENT_COLORS)]
            
            # Row Background Frame
            row_frame = ctk.CTkFrame(self.stats_frame, fg_color="transparent", corner_radius=8)
            row_frame.grid(row=row_idx, column=0, sticky="ew", padx=5, pady=2)
            
            # Configure columns of the row frame
            for c_idx in range(len(headers)):
                row_frame.grid_columnconfigure(c_idx, weight=3 if c_idx == 9 else 1, uniform="col_group")
                
            # 1. Workout Name
            wo_text = f"WO {row_idx}"
            lbl = ctk.CTkLabel(row_frame, text=wo_text, font=("Arial", 12, "bold"), text_color=color)
            lbl.grid(row=0, column=0, padx=10, pady=6, sticky="w")
            
            # Parse Start Time
            try:
                start_dt_row = datetime.datetime.fromisoformat(w_data.get("start_time", ""))
                start_time_val = start_dt_row.strftime("%I:%M %p")
            except:
                start_time_val = "--"

            # Helper for empty values
            def fmt_hr(val):
                return str(val) if val and int(val) > 0 else "--"
                
            def fmt_cal(val):
                return str(val) if val and float(val) > 0 else "--"

            # Row values mapping
            row_vals = [
                start_time_val,
                str(w_data.get("total_rounds_completed", 0)),
                fmt_sec(w_data.get("total_time_sec", 0)),
                fmt_sec(w_data.get("work_time_sec", 0)),
                fmt_sec(w_data.get("rest_time_sec", 0)),
                fmt_hr(w_data.get("max_hr", 0)),
                fmt_hr(w_data.get("avg_hr", 0)),
                fmt_cal(w_data.get("calories_burnt_kcal", 0)),
                w_data.get("workout_notes", "")
            ]
            
            for c_idx, val in enumerate(row_vals, start=1):
                sticky = "w" if c_idx == 9 else ""
                
                # Apply vibrant accent colors to all rows as requested
                val_color = TEXT_COLOR
                if c_idx in [1, 2, 3]: # Start Time, Rounds, or Total Time
                    val_color = TEXT_COLOR
                elif c_idx == 4: # Work Time
                    val_color = ACCENT_GREEN
                elif c_idx == 5: # Rest Time
                    val_color = ACCENT_ORANGE
                elif c_idx == 6: # Peak HR
                    val_color = ACCENT_RED
                elif c_idx == 7: # Avg HR
                    val_color = ACCENT_BLUE
                elif c_idx == 8: # Calories
                    val_color = ACCENT_PURPLE
                elif c_idx == 9: # Notes
                    val_color = TEXT_SECONDARY
                
                if c_idx == 9:
                    # Notes: text + edit button frame
                    notes_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
                    if sticky:
                        notes_frame.grid(row=0, column=c_idx, padx=10, pady=2, sticky=sticky)
                    else:
                        notes_frame.grid(row=0, column=c_idx, padx=10, pady=2)
                        
                    notes_txt = str(val) if val else "Add notes..."
                    if len(notes_txt) > 25:
                        notes_txt = notes_txt[:22] + "..."
                        
                    lbl = ctk.CTkLabel(notes_frame, text=notes_txt, font=("Arial", 12), text_color=val_color)
                    lbl.pack(side="left")
                    
                    w_id = w_data.get("id")
                    if w_id:
                        btn_edit = ctk.CTkLabel(notes_frame, text=" ✏️", font=("Arial", 10), text_color=ACCENT_BLUE, cursor="hand2")
                        btn_edit.pack(side="left", padx=5)
                        btn_edit.bind("<Button-1>", lambda event, wid=w_id, wdata=w_data: self.edit_notes_dialog(wid, wdata))
                else:
                    lbl = ctk.CTkLabel(row_frame, text=str(val), font=("Arial", 12), text_color=val_color)
                    if sticky:
                        lbl.grid(row=0, column=c_idx, padx=10, pady=6, sticky=sticky)
                    else:
                        lbl.grid(row=0, column=c_idx, padx=10, pady=6)

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
            
            # Label
            lbl_text = f"WO {idx+1}"
                
            # Plot line and fill
            # Thinner graph lines (linewidth=1.0) for cleaner display
            linewidth = 1.0
            ax.plot(times, bpms, color=color, linewidth=linewidth, label=lbl_text)
            ax.fill_between(times, bpms, 40, color=color, alpha=0.1)
            
            # Draw vertical dashed separator line at the start of workout (if not the first one)
            if offset > 0:
                ax.axvline(x=times[0], color='#555555', linestyle='--', linewidth=1, alpha=0.7)
            
            # Label at the top using blended transform (data x, axes y)
            mid_time = (times[0] + times[-1]) / 2.0
            y_pos = 0.95
            
            transform = mtransforms.blended_transform_factory(ax.transData, ax.transAxes)
            ax.text(mid_time, y_pos, f"WO {idx+1}", color=color, fontsize=9, ha="center", va="top", 
                    fontweight="normal", transform=transform)
            
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
        
        # Ensure labels are visible
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=self.graph_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def export_day_csv(self):
        if not hasattr(self, 'current_day_workouts') or not self.current_day_workouts:
            print("No workouts to export.")
            return
            
        # Open file save dialog
        default_filename = f"{self.current_profile_name}_{self.current_date_str.replace(' ', '_').replace(',', '')}_workouts.csv"
        dest_file = ctk.filedialog.asksaveasfilename(
            initialfile=default_filename,
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Export Day's Workouts to CSV"
        )
        
        if not dest_file:
            return
            
        try:
            import csv
            
            def fmt_sec(s):
                try:
                    s = int(float(s))
                    h = s // 3600
                    m = (s % 3600) // 60
                    sec = s % 60
                    return f"{h:02}:{m:02}:{sec:02}"
                except:
                    return "00:00:00"

            def fmt_hr(val):
                return str(val) if val and int(val) > 0 else "--"
                
            def fmt_cal(val):
                return str(val) if val and float(val) > 0 else "--"

            with open(dest_file, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Headers matching the details table
                writer.writerow(["Workout", "Start Time", "Rounds", "Total Time", "Work Time", "Rest Time", "Peak HR (BPM)", "Avg HR (BPM)", "Calories (kcal)", "Notes"])
                
                for idx, w_data in enumerate(self.current_day_workouts, start=1):
                    # Parse Start Time
                    try:
                        start_dt_row = datetime.datetime.fromisoformat(w_data.get("start_time", ""))
                        start_time_val = start_dt_row.strftime("%I:%M %p")
                    except:
                        start_time_val = "--"
                        
                    writer.writerow([
                        f"WO {idx}",
                        start_time_val,
                        str(w_data.get("total_rounds_completed", 0)),
                        fmt_sec(w_data.get("total_time_sec", 0)),
                        fmt_sec(w_data.get("work_time_sec", 0)),
                        fmt_sec(w_data.get("rest_time_sec", 0)),
                        fmt_hr(w_data.get("max_hr", 0)),
                        fmt_hr(w_data.get("avg_hr", 0)),
                        fmt_cal(w_data.get("calories_burnt_kcal", 0)),
                        w_data.get("workout_notes", "")
                    ])
            print(f"Exported day's workouts to {dest_file}")
        except Exception as e:
            print(f"Error exporting day's workouts to CSV: {e}")

    def edit_notes_dialog(self, w_id, w_data):
        if not w_id:
            return
            
        current_notes = w_data.get("workout_notes", "")
        
        def save_callback(new_notes):
            # 1. Update SQLite
            success = storage.update_workout_notes(w_id, new_notes)
            if success:
                # 2. Trigger sync in background thread
                import threading
                import sync_client
                threading.Thread(target=sync_client.run_sync, daemon=True).start()
                
                # 3. Reload view
                try:
                    p_details = storage.get_profile_details(self.current_profile_name)
                    max_hr = p_details.get("max_hr") or 190
                except:
                    max_hr = 190
                    
                w_data["workout_notes"] = new_notes
                self.update_view(w_data, max_hr_profile=max_hr, profile_name=self.current_profile_name)
                
        # Open custom edit dialog
        EditNotesDialog(self, current_notes, save_callback)
