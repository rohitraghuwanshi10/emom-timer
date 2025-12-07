import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import defaultdict
import numpy as np
import datetime
import storage

class HistoryWindow(ctk.CTkToplevel):
    def __init__(self):
        super().__init__()
        self.title("Workout History")
        self.geometry("800x700")
        
        # Configure grid weights
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Scrollable Frame for Table (Top Half)
        self.table_frame = ctk.CTkScrollableFrame(self)
        self.table_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Frame for Graph (Bottom Half)
        self.graph_frame = ctk.CTkFrame(self)
        self.graph_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        self.load_history()

    def load_history(self):
        data = storage.load_workouts()
            
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
                 # Usually if we use storage.load_workouts() we get raw rows
                 pass
            while len(headers) < max_cols:
                 headers.append(f"Column {len(headers)+1}")

        # Header Title Mapping
        header_map = {
            "work_time_sec": "Work Time (Sec)",
            "rest_time_sec": "Rest Time (Sec)",
            "total_time_sec": "Total Time (HH:MM:SS)"
        }

        for i, h in enumerate(headers):
            # Use map or fallback to Title Case
            title = header_map.get(h, h.replace('_', ' ').title())
            lbl = ctk.CTkLabel(self.table_frame, text=title, font=("Arial", 14, "bold"))
            lbl.grid(row=0, column=i, padx=10, pady=5, sticky="ew")

        # Data
        for r_idx, row in enumerate(data[1:], start=1):
            for c_idx, val in enumerate(row):
                display_text = val
                # Format Total Time (Index 5)
                if c_idx == 5:
                    display_text = self._format_seconds(val)
                
                lbl = ctk.CTkLabel(self.table_frame, text=display_text, font=("Arial", 12))
                lbl.grid(row=r_idx, column=c_idx, padx=10, pady=2, sticky="ew")
        
        # Load Graph
        self.load_graph(data[1:])

    def _format_seconds(self, seconds_str):
        try:
            total_seconds = int(float(seconds_str))
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02}:{minutes:02}:{seconds:02}"
        except (ValueError, TypeError):
            return seconds_str

    def load_graph(self, rows):
        # Data Processing
        # date_map: {date_str: [duration1, duration2, ...]}
        date_map = defaultdict(list)
        
        try:
            for row in rows:
                if not row or len(row) < 6: continue
                
                # row[0] is start_time string ISO format
                try:
                    start_dt = datetime.datetime.fromisoformat(row[0])
                except ValueError:
                    continue
                    
                date_str = start_dt.strftime("%Y-%m-%d")
                
                # row[5] is total_time in seconds -> convert to minutes
                try:
                    duration_min = float(row[5]) / 60.0
                except (ValueError, IndexError):
                    duration_min = 0
                    
                date_map[date_str].append(duration_min)
            
            if not date_map:
                return

            # Prepare Data for Stacking
            dates = sorted(date_map.keys())
            max_workouts = max(len(v) for v in date_map.values())
            
            # Prepare series: series[i] is list of values for the i-th workout of each day
            series_list = []
            for i in range(max_workouts):
                series = []
                for d in dates:
                    workouts = date_map[d]
                    if i < len(workouts):
                        series.append(workouts[i])
                    else:
                        series.append(0)
                series_list.append(series)

            # Plotting
            fig, ax = plt.subplots(figsize=(5, 3), dpi=100)
            
            bottom = [0] * len(dates)
            colors = plt.cm.viridis(np.linspace(0, 1, max_workouts)) if 'np' in globals() else None 
            
            for i, series in enumerate(series_list):
                ax.bar(dates, series, bottom=bottom, label=f'Workout {i+1}')
                # Update bottom
                for j in range(len(bottom)):
                    bottom[j] += series[j]

            ax.set_xlabel("Date")
            ax.set_ylabel("Total Time (Minutes)")
            ax.set_title("Daily Workout Time")
            plt.xticks(rotation=45)
            
            plt.tight_layout()

            # Embed in Tkinter
            canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
        except Exception as e:
            print(f"Error generating graph: {e}")
            lbl = ctk.CTkLabel(self.graph_frame, text=f"Error generating graph: {e}", text_color="red")
            lbl.pack()
