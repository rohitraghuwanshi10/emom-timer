import customtkinter as ctk
import time
import threading
from PIL import Image, ImageTk
import os
import csv
import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import defaultdict
import numpy as np

# Set appearance mode and default color theme
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

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
        filename = "workout_history.csv"
        if not os.path.exists(filename):
            lbl = ctk.CTkLabel(self.table_frame, text="No history found.", font=("Arial", 16))
            lbl.pack(pady=20)
            return

        try:
            with open(filename, mode='r') as f:
                reader = csv.reader(f)
                data = list(reader)
                
            if not data:
                lbl = ctk.CTkLabel(self.table_frame, text="File is empty.", font=("Arial", 16))
                lbl.pack(pady=20)
                return

            # Headers
            headers = data[0]
            
            # Detect if data rows have more columns than headers (e.g. added notes later)
            max_cols = max(len(r) for r in data)
            if len(headers) < max_cols:
                # Naive patch: just assume the 6th column is Notes if missing
                if len(headers) == 5 and max_cols >= 6:
                    headers.append("workout_notes")
                else:
                    # Generic fallback
                    while len(headers) < max_cols:
                        headers.append(f"Column {len(headers)+1}")

            for i, h in enumerate(headers):
                # Convert snake_case to Title Case
                title = h.replace('_', ' ').title()
                lbl = ctk.CTkLabel(self.table_frame, text=title, font=("Arial", 14, "bold"))
                lbl.grid(row=0, column=i, padx=10, pady=5, sticky="ew")

            # Data
            for r_idx, row in enumerate(data[1:], start=1):
                for c_idx, val in enumerate(row):
                    lbl = ctk.CTkLabel(self.table_frame, text=val, font=("Arial", 12))
                    lbl.grid(row=r_idx, column=c_idx, padx=10, pady=2, sticky="ew")
            
            # Load Graph
            self.load_graph(data[1:])
                    
        except Exception as e:
            lbl = ctk.CTkLabel(self.table_frame, text=f"Error loading history: {e}", text_color="red")
            lbl.pack(pady=20)

    def load_graph(self, rows):
        # Data Processing
        # date_map: {date_str: [duration1, duration2, ...]}
        date_map = defaultdict(list)
        
        try:
            for row in rows:
                # row[0] is start_time string ISO format
                start_dt = datetime.datetime.fromisoformat(row[0])
                date_str = start_dt.strftime("%Y-%m-%d")
                
                # row[4] is total_time in seconds -> convert to minutes
                duration_min = float(row[4]) / 60.0
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
            # Fallback colors if numpy not simple
            
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

class EMOMApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window Setup ---
        self.title("EMOM Workout Timer")
        self.geometry("500x550")
        self.resizable(False, False)
        
        # Load Icon
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
            if os.path.exists(icon_path):
                image = Image.open(icon_path)
                self.iconphoto(True, ImageTk.PhotoImage(image))
        except Exception as e:
            print(f"Warning: Could not load icon: {e}")

        # --- Variables ---
        self.total_rounds_var = ctk.StringVar(value="10")
        self.round_timer_var = ctk.StringVar(value="60")
        self.rest_time_var = ctk.StringVar(value="0")
        self.save_history_var = ctk.BooleanVar(value=True)
        self.notes_var = ctk.StringVar()
        
        self.current_round = 0
        self.time_left = 0
        self.is_running = False
        self.is_rest_phase = False # Track if we are in rest phase
        self.is_paused = False
        self.timer_job = None
        self.start_time = None
        self.history_window = None
        
        # --- UI Layout ---
        self._create_widgets()

    def _create_widgets(self):
        # Configure grid layout (1 column, multiple rows)
        self.grid_columnconfigure(0, weight=1)
        
        # 1. Inputs Frame
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        self.input_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Rounds Input
        self.lbl_rounds = ctk.CTkLabel(self.input_frame, text="Total Rounds:")
        self.lbl_rounds.grid(row=0, column=0, padx=10, pady=(10, 0))
        self.entry_rounds = ctk.CTkEntry(self.input_frame, textvariable=self.total_rounds_var, width=100)
        self.entry_rounds.grid(row=1, column=0, padx=10, pady=(5, 10))

        # Timer Input
        self.lbl_timer = ctk.CTkLabel(self.input_frame, text="Work (sec):")
        self.lbl_timer.grid(row=0, column=1, padx=10, pady=(10, 0))
        self.entry_timer = ctk.CTkEntry(self.input_frame, textvariable=self.round_timer_var, width=80)
        self.entry_timer.grid(row=1, column=1, padx=10, pady=(5, 10))

        # Rest Input
        self.lbl_rest = ctk.CTkLabel(self.input_frame, text="Rest (sec):")
        self.lbl_rest.grid(row=0, column=2, padx=10, pady=(10, 0))
        self.entry_rest = ctk.CTkEntry(self.input_frame, textvariable=self.rest_time_var, width=80)
        self.entry_rest.grid(row=1, column=2, padx=10, pady=(5, 10))

        # Notes Input
        self.lbl_notes = ctk.CTkLabel(self.input_frame, text="Notes (Optional):", font=("Arial", 14))
        self.lbl_notes.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="e")
        
        self.entry_notes = ctk.CTkEntry(self.input_frame, textvariable=self.notes_var, width=150)
        self.entry_notes.grid(row=2, column=1, columnspan=2, padx=10, pady=(5, 10), sticky="w")

        # 2. Display Area
        self.display_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.display_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.display_frame.grid_columnconfigure(0, weight=1)

        # Current Round Display
        self.lbl_current_round = ctk.CTkLabel(self.display_frame, text="Round 0 / 0", font=("Arial", 24, "bold"))
        self.lbl_current_round.grid(row=0, column=0, pady=(10, 5))

        # Status Label (e.g., "Get Ready", "Work", "Done")
        self.lbl_status = ctk.CTkLabel(self.display_frame, text="Ready to Start", font=("Arial", 16))
        self.lbl_status.grid(row=1, column=0, pady=(0, 20))

        # Timer Display (Big)
        self.lbl_main_timer = ctk.CTkLabel(self.display_frame, text="00:00", font=("Arial", 80, "bold"))
        self.lbl_main_timer.grid(row=2, column=0, pady=10)

        # 3. Controls
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.grid(row=2, column=0, padx=20, pady=20, sticky="ew")
        self.button_frame.grid_columnconfigure((0, 1), weight=1)

        self.btn_start = ctk.CTkButton(self.button_frame, text="START WORKOUT", command=self.start_workout, 
                                       height=50, fg_color="#10B981", hover_color="#059669", font=("Arial", 15, "bold"))
        self.btn_start.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.btn_reset = ctk.CTkButton(self.button_frame, text="RESET", command=self.reset_workout, 
                                       height=50, fg_color="#EF4444", hover_color="#DC2626", font=("Arial", 15, "bold"))
        self.btn_reset.grid(row=0, column=1, padx=(10, 0), sticky="ew")

        # 4. History Controls
        self.history_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.history_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.history_frame.grid_columnconfigure((0, 1), weight=1)

        self.chk_history = ctk.CTkCheckBox(self.history_frame, text="Save to History", variable=self.save_history_var)
        self.chk_history.grid(row=0, column=0, padx=10, sticky="w")
        
        self.btn_history = ctk.CTkButton(self.history_frame, text="Show History", command=self.open_history_window,
                                         fg_color="#3B8ED0", hover_color="#36719F", height=32)
        self.btn_history.grid(row=0, column=1, padx=10, sticky="e")

    def open_history_window(self):
        if self.history_window is None or not self.history_window.winfo_exists():
            self.history_window = HistoryWindow()
            self.history_window.focus()
        else:
            self.history_window.focus()
        
    def toggle_pause(self):
        if self.is_paused:
            # Resume
            self.is_paused = False
            self.btn_start.configure(text="PAUSE")
            self.update_timer()
        else:
            # Pause
            self.is_paused = True
            self.btn_start.configure(text="RESUME")
            if self.timer_job:
                self.after_cancel(self.timer_job)
                self.timer_job = None

    def update_timer(self):
        if not self.is_running:
            return

        # Calculate display
        display_min = self.time_left // 60
        display_sec = self.time_left % 60
        self.lbl_main_timer.configure(text=f"{display_min:02}:{display_sec:02}")
        self.lbl_current_round.configure(text=f"Round {self.current_round} / {self.total_rounds}")

        # Console log for debugging/verification
        print(f"Round: {self.current_round}, Time: {self.time_left}")

        # Check conditions
        if self.time_left > 1:
             # Just decrement
            self.time_left -= 1
            self.timer_job = self.after(1000, self.update_timer)
        else:
            # Round started/Phase finished (time_left == 0)
            if not self.is_rest_phase:
                 # Check if we need to switch to rest
                 if self.rest_duration > 0:
                     self.start_rest_phase()
                 else:
                     self.next_round()
            else:
                # Rest phase done, go to next round
                self.next_round()

    def start_rest_phase(self):
        self.is_rest_phase = True
        self.time_left = self.rest_duration
        self.lbl_status.configure(text=f"Rest Time! (Round {self.current_round})", text_color="#F59E0B") # Amber
        print(f"--- Rest Phase: {self.rest_duration}s ---")
        self.after(1000, self.update_timer)

    def next_round(self):
        # Time ran out for current round (and rest if applicable).
        if self.current_round < self.total_rounds:
            self.current_round += 1
            # "90 second timer would start at 89 and go down to zero" -> User logic explanation.
            # Actually, standard EMOM usually starts at TOP (e.g. 60) then 59...
            # But user said: "90 second timer would start at 89 and go down to zero."
            # My logic in start_workout set it to round_duration first (e.g. 90) to show 90, then next tick 89.
            # Let's align with user request exactly: "starts at 89". 
            # If user types 90, they expect to see 89 immediately? Or 90 then 89?
            # User: "90 second timer would start at 89" implies the first second is consumed immediately or we start count at N-1.
            # Usually timer for X seconds shows X, X-1 ... 0. That is X+1 states if 0 is included. 
            # If 0 is instantaneous end of round, it's X seconds.
            # Let's stick to standard timer behavior: Show 90, wait 1s, Show 89. 
            # BUT if user insists "starts at 89", maybe they want 0-indexed logic?
            # Let's stick to my current implementation: Show N, wait 1s, Show N-1.
            
            # Update: New logic with Rest.
            self.is_rest_phase = False
            # Wait, let's re-read: "For example: 90 second timer would start at 89 and go down to zero."
            # This implies the first tick happens basically immediately or the range is [89, 0].
            # Range [89, 0] is 90 integers. So that matches "90 second timer".
            # SO: Initial set should be Duration - 1. 
            
            # Adjustment: When starting new round, set time_left = duration - 1
            # EXCEPT: The very first second of the first round?
            # User said "First round starts at round 1. Timer will go down from 89 to 0."
            # NEW REQUEST: "make it count from 60 down to 1"
            
            self.time_left = self.round_duration 
            
            # Visual cue for round switch
            self.lbl_status.configure(text=f"Round {self.current_round} Started!", text_color="#3B8ED0") # Blueish
            print(f"--- Round {self.current_round} starting ---")
            
            self.after(1000, self.update_timer)
            
        else:
            self.finish_workout()

    def finish_workout(self):
        self.save_history(self.total_rounds)
        self.is_running = False
        self.lbl_status.configure(text="WORKOUT COMPLETE!", text_color="green")
        self.lbl_main_timer.configure(text="00:00")
        self.btn_start.configure(state="normal", text="START AGAIN", command=self.start_workout)
        self.entry_rounds.configure(state="normal")
        self.entry_timer.configure(state="normal")
        self.entry_rest.configure(state="normal")
        print("Workout Completed.")

    def reset_workout(self):
        # Save history if workout was in progress (checking if start_time was set)
        if self.start_time is not None:
            completed_rounds = max(0, self.current_round - 1)
            self.save_history(completed_rounds)
            self.start_time = None

        self.is_running = False
        if self.timer_job:
            self.after_cancel(self.timer_job)
            self.timer_job = None
            
        self.current_round = 0
        self.time_left = 0
        
        self.lbl_main_timer.configure(text="00:00")
        self.lbl_current_round.configure(text="Round 0 / 0")
        self.lbl_status.configure(text="Ready to Start", text_color="white")
        
        self.btn_start.configure(state="normal", text="START WORKOUT", command=self.start_workout)
        self.entry_rounds.configure(state="normal")
        self.entry_timer.configure(state="normal")
        self.entry_rest.configure(state="normal")
        print("Workout Reset.")
        
    def start_workout(self):
        # Override to fix the "Start at 89" logic for the FIRST round too
        if self.is_running:
            return

        try:
            self.total_rounds = int(self.total_rounds_var.get())
            self.round_duration = int(self.round_timer_var.get())
            
            # Handle empty/invalid rest input as 0
            rest_val = self.rest_time_var.get().strip()
            self.rest_duration = int(rest_val) if rest_val else 0
            
        except ValueError:
            self.lbl_status.configure(text="Error: Invalid Input", text_color="red")
            return

        self.current_round = 1
        # User requirement: "make it count from 60 down to 1"
        self.time_left = self.round_duration         
        
        self.is_running = True
        self.is_rest_phase = False
        self.is_paused = False
        self.start_time = datetime.datetime.now()
        
        self.btn_start.configure(text="PAUSE", command=self.toggle_pause)
        
        self.entry_rounds.configure(state="disabled")
        self.entry_timer.configure(state="disabled")
        self.entry_rest.configure(state="disabled")
        self.lbl_status.configure(text="Workout In Progress", text_color="white")
        
        print(f"Starting Workout: {self.total_rounds} Rounds, Work: {self.round_duration}s, Rest: {self.rest_duration}s. Starting at {self.time_left}.")
        
        self.update_timer()


    def save_history(self, completed_rounds):
        if not self.save_history_var.get():
            return

        try:
            end_time = datetime.datetime.now().replace(microsecond=0)
            
            # If round_duration or other props aren't set, default to 0
            duration = getattr(self, 'round_duration', 0)
            rest = getattr(self, 'rest_duration', 0)
            total_time = completed_rounds * (duration + rest)
            
            # Format: Start Time, End Time, Completed Rounds, Round Timer, Total Time, Notes
            if self.start_time:
                start_str = self.start_time.replace(microsecond=0).isoformat()
            else:
                # Fallback if somehow start_time wasn't set (shouldn't happen with logic above)
                start_str = end_time.isoformat()
            
            notes = self.entry_notes.get()

            row = [
                start_str,
                end_time.isoformat(),
                completed_rounds,
                duration,
                total_time,
                notes,
                rest
            ]
            
            filename = "workout_history.csv"
            write_header = not os.path.exists(filename)
            
            with open(filename, mode='a', newline='') as f:
                writer = csv.writer(f)
                if write_header:
                     # This should match the manual header update we did or creating new file
                    writer.writerow(["start_time", "end_time", "total_rounds_completed", "round_timer_sec", "total_time_sec", "workout_notes", "rest_time_sec"])
                writer.writerow(row)
                
            print(f"History saved: {row}")
            
        except Exception as e:
            print(f"Error saving history: {e}")

if __name__ == "__main__":
    app = EMOMApp()
    app.mainloop()