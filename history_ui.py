import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import defaultdict
import numpy as np
import datetime
import storage

# --- Colors for Graph ---
BG_COLOR = "#000000"
CARD_COLOR = "#1C1C1E"
TEXT_COLOR = "#FFFFFF"
ACCENT_COLORS = ["#5E81AC", "#88C0D0", "#A3BE8C", "#EBCB8B", "#D08770", "#B48EAD"] # Nord Palette (Soft Blue, Cyan, Green, Yellow, Orange, Purple)

class HistoryFrame(ctk.CTkFrame):
    def __init__(self, master, on_select_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color=BG_COLOR)
        
        self.on_select_callback = on_select_callback
        
        # Configure grid weights
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Scrollable Frame for Table (Top Half)
        self.table_frame = ctk.CTkScrollableFrame(self, fg_color=CARD_COLOR, corner_radius=15)
        self.table_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        # Frame for Graph (Bottom Half)
        self.graph_frame = ctk.CTkFrame(self, fg_color=CARD_COLOR, corner_radius=15)
        self.graph_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        self.current_profile = "Default"
        self.load_history()

    def refresh(self, profile_name=None):
        try:
            if profile_name is None:
                profile_name = self.current_profile
                
            # Clear existing widgets
            for widget in self.table_frame.winfo_children():
                widget.destroy()
            for widget in self.graph_frame.winfo_children():
                widget.destroy()
            
            # Reload
            self.load_history(profile_name)
        except Exception as e:
            print("ERROR REFRESHING HISTORY:")
            import traceback
            traceback.print_exc()
            
            # Show error in UI
            for widget in self.table_frame.winfo_children(): widget.destroy()
            lbl = ctk.CTkLabel(self.table_frame, text=f"Error loading history: {e}", text_color="red")
            lbl.pack(pady=20)

    def load_history(self, profile_name="Default"):
        self.current_profile = profile_name
        data = storage.load_history(profile_name)
            
        if not data:
            lbl = ctk.CTkLabel(self.table_frame, text="No history found or file is empty.", font=("Arial", 16))
            lbl.pack(pady=20)
            return

        # Headers
        headers = data[0]
        
        # Detect if data rows have more columns than headers (e.g. added notes later)
        max_cols = max(len(r) for r in data)
        # Naive patching for structure evolution
        if len(headers) < max_cols:
            if len(headers) == 5 and max_cols >= 6:
                headers.append("workout_notes")
            elif len(headers) == 6 and max_cols >= 7: # Added rest_time
                 pass
            while len(headers) < max_cols:
                 headers.append(f"Column {len(headers)+1}")

        # Header Title Mapping (Short & Clean)
        # Header Title Mapping (Short & Clean)
        header_map = {
            "start_time": "Date",
            "end_time": "End",
            "total_rounds_completed": "Rounds",
            "rounds": "Rounds",
            "work_time_sec": "Work (s)",
            "work_duration": "Work (s)",
            "rest_time_sec": "Rest (s)",
            "rest_duration": "Rest (s)",
            "total_time_sec": "Total Time",
            "total_time": "Total Time",
            "workout_notes": "Notes",
            "notes": "Notes",
            "workout_details_file": "Details File"
        }

        # Find filename index
        file_col_idx = -1
        if "workout_details_file" in headers:
             file_col_idx = headers.index("workout_details_file")
        elif "Details File" in headers:
             file_col_idx = headers.index("Details File")

        # Configure columns for better spacing (excluding details file column)
        col_count = 0
        for i, h in enumerate(headers):
            if i == file_col_idx:
                continue
            self.table_frame.grid_columnconfigure(col_count, weight=1)
            col_count += 1

        col_count = 0
        for i, h in enumerate(headers):
            if i == file_col_idx:
                continue
            title = header_map.get(h, h.replace('_', ' ').title())
            lbl = ctk.CTkLabel(self.table_frame, text=title, font=("Arial", 13, "bold"), text_color="#8E8E93")
            lbl.grid(row=0, column=col_count, padx=15, pady=10, sticky="ew")
            col_count += 1

        # Data
        for r_idx, row in enumerate(data[1:], start=1):
            row_color = TEXT_COLOR
            
            # Extract filename/ID for this row
            details_file = ""
            if file_col_idx != -1 and file_col_idx < len(row):
                details_file = row[file_col_idx]
            
            col_count = 0
            for c_idx, val in enumerate(row):
                if c_idx == file_col_idx:
                    continue
                    
                display_text = val
                header_name = headers[c_idx]
                
                if c_idx == 0 or c_idx == 1:
                    try:
                        dt = datetime.datetime.fromisoformat(val)
                        if c_idx == 0: # Start Time -> "Dec 06, 14:30"
                            display_text = dt.strftime("%b %d, %H:%M")
                        else: # End Time -> "14:45"
                            display_text = dt.strftime("%H:%M")
                    except ValueError:
                        pass
                
                elif header_name in ["total_time_sec", "Total Time", "total_time"]:
                    display_text = self._format_seconds(val)
                
                lbl = ctk.CTkLabel(self.table_frame, text=display_text, font=("Arial", 12), text_color=row_color)
                lbl.grid(row=r_idx, column=col_count, padx=15, pady=5, sticky="ew")
                col_count += 1
                
                # Bind Click
                if details_file and self.on_select_callback:
                     lbl.bind("<Button-1>", lambda e, f=details_file: self.on_select_callback(f))
                     lbl.configure(cursor="pointinghand")
        
        # Load Graph
        self.load_graph(data[1:], headers)

    def _format_seconds(self, seconds_str):
        try:
            total_seconds = int(float(seconds_str))
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02}:{minutes:02}:{seconds:02}"
        except (ValueError, TypeError):
            return seconds_str

    def load_graph(self, rows, headers=None):
        # Data Processing
        # date_map: {date_str: [(duration, notes, filename), ...]}
        date_map = defaultdict(list)
        
        try:
            # Find filename index
            file_col_idx = -1
            if headers:
                if "workout_details_file" in headers:
                     file_col_idx = headers.index("workout_details_file")
                elif "Details File" in headers:
                     file_col_idx = headers.index("Details File")

            for row in rows:
                if not row or len(row) < 6: continue
                
                # row[0] is start_time string ISO format
                try:
                    start_dt = datetime.datetime.fromisoformat(row[0])
                except ValueError:
                    continue
                    
                date_str = start_dt.strftime("%Y-%m-%d") # ISO format for correct sorting
                
                # row[5] is total_time in seconds -> convert to minutes
                try:
                    duration_min = float(row[5]) / 60.0
                except (ValueError, IndexError):
                    duration_min = 0
                
                # row[6] is workout_notes (optional)
                # row[6] is workout_notes (optional)
                notes = ""
                if len(row) > 6:
                    notes = row[6]
                    
                filename = ""
                if file_col_idx != -1 and file_col_idx < len(row):
                    filename = row[file_col_idx]

                date_map[date_str].append((duration_min, notes, filename))
            
            if not date_map:
                return

            # Prepare Data for Stacking
            dates = sorted(date_map.keys())
            
            # Limit to last 7 days of data
            dates = dates[-7:]
            
            display_dates = [d[5:] for d in dates] # Show MM-DD
            max_workouts = max(len(v) for v in date_map.values())
            
            # Prepare series
            series_list = []
            notes_series_list = []
            files_series_list = []

            for i in range(max_workouts):
                series = []
                notes_list = []
                files_list = []
                for d in dates:
                    workouts = date_map[d]
                    if i < len(workouts):
                        series.append(workouts[i][0])
                        notes_list.append(workouts[i][1])
                        files_list.append(workouts[i][2])
                    else:
                        series.append(0)
                        notes_list.append("")
                        files_list.append("")
                series_list.append(series)
                notes_series_list.append(notes_list)
                files_series_list.append(files_list)

            # --- Modern Graph Styling ---
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(5, 3), dpi=100)
            fig.patch.set_facecolor(CARD_COLOR)
            ax.set_facecolor(CARD_COLOR)
            
            bottom = [0] * len(dates)
            x_vals = range(len(dates))
            
            bar_containers = []

            # Create Bars
            for i, series in enumerate(series_list):
                color = ACCENT_COLORS[i % len(ACCENT_COLORS)]
                bars = ax.bar(x_vals, series, bottom=bottom, label=f'WO {i+1}', color=color, alpha=0.9, width=0.5, edgecolor=CARD_COLOR, linewidth=0.5)
                bar_containers.append(bars)
                # Update bottom
                for j in range(len(bottom)):
                    bottom[j] += series[j]

            # Customizing Axes
            ax.set_xticks(x_vals) # Set ticks at integer positions
            ax.set_xticklabels(display_dates) # Label with MM-DD


            # Customizing Axes
            ax.set_xlabel("Date", fontsize=8, color="#8E8E93")
            ax.set_ylabel("Minutes", fontsize=8, color="#8E8E93")
            ax.set_title("Daily Activity", fontsize=10, color="white", fontweight="bold", pad=15)
            
            # Grid
            ax.grid(color="#3A3A3C", linestyle=':', linewidth=0.5, axis='y', alpha=0.5)
            ax.set_axisbelow(True)
            
            # Spines
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color("#3A3A3C")
            ax.spines['bottom'].set_color("#3A3A3C")
            
            ax.tick_params(axis='x', colors="#8E8E93", rotation=0, labelsize=7)
            ax.tick_params(axis='y', colors="#8E8E93", labelsize=7)
            
            # Remove legend to keep it clean if too many, or style it
            if max_workouts > 1:
                legend = ax.legend(frameon=False, fontsize=7, labelcolor="#8E8E93")

            plt.tight_layout()

            # --- Hover Annotation ---
            annot = ax.annotate("", xy=(0,0), xytext=(10,10), textcoords="offset points",
                                bbox=dict(boxstyle="round", fc=CARD_COLOR, ec="white", alpha=0.9),
                                arrowprops=dict(arrowstyle="->", color="white"),
                                color="white", fontsize=9)
            annot.set_visible(False)
            annot.last_bar = None

            def update_annot(bar, notes, wo_idx):
                x = bar.get_x() + bar.get_width() / 2.
                y = bar.get_y() + bar.get_height() / 2.
                annot.xy = (x, y)
                text = f"WO{wo_idx}- {notes}"
                annot.set_text(text)
                
                # Dynamic positioning to avoid cutoff
                # Get current x-axis limits
                x_min, x_max = ax.get_xlim()
                graph_width = x_max - x_min
                
                # If we are in the right half of the graph, shift text to the left
                if x > (x_min + graph_width / 2):
                    annot.xyann = (-10, 10)
                    annot.set_horizontalalignment('right')
                else:
                    annot.xyann = (10, 10)
                    annot.set_horizontalalignment('left')

            def hover(event):
                vis = annot.get_visible()
                if event.inaxes == ax:
                    found_bar = None
                    found_idx = -1
                    found_notes = ""

                    # Find which bar we are hovering over
                    for i, bars in enumerate(bar_containers):
                        for j, bar in enumerate(bars):
                            if bar.contains(event)[0]:
                                found_bar = bar
                                found_idx = i + 1
                                found_notes = notes_series_list[i][j]
                                break
                        if found_bar: break
                    
                    if found_bar:
                        # If it's a new bar, update the annotation
                        if found_bar != annot.last_bar:
                            update_annot(found_bar, found_notes, found_idx)
                            annot.set_visible(True)
                            annot.last_bar = found_bar
                            canvas.draw_idle()
                        
                        # Change cursor
                        canvas.get_tk_widget().configure(cursor="pointinghand")
                        
                    else:
                        # Not hovering over any bar
                        if vis:
                            annot.set_visible(False)
                            annot.last_bar = None
                            canvas.draw_idle()
                        
                        # Reset cursor
                        canvas.get_tk_widget().configure(cursor="")
                else:
                    if vis:
                         annot.set_visible(False)
                         annot.last_bar = None
                         canvas.draw_idle()
                    canvas.get_tk_widget().configure(cursor="")

            def on_click(event):
                 if event.inaxes == ax and event.button == 1: # Left click
                    for i, bars in enumerate(bar_containers):
                        for j, bar in enumerate(bars):
                            if bar.contains(event)[0]:
                                filename = files_series_list[i][j]
                                if filename and self.on_select_callback:
                                    print(f"Graph clicked: {filename}") # Debug
                                    self.on_select_callback(filename)
                                return

            # Embed in Tkinter
            canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
            
            # Connect hover event
            canvas.mpl_connect("motion_notify_event", hover)
            # Connect click event
            canvas.mpl_connect("button_press_event", on_click)
            
        except Exception as e:
            print(f"Error generating graph: {e}")
            lbl = ctk.CTkLabel(self.graph_frame, text=f"Error generating graph: {e}", text_color="red")
            lbl.pack()
