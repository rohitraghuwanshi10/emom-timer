import customtkinter as ctk
import threading
from PIL import Image, ImageTk
import os
import datetime
import storage
import subprocess
from history_ui import HistoryWindow

# --- Modern "Liquid" / iOS Dark Mode Theme ---
# Backgrounds
BG_COLOR = "#000000"         # Pure black for OLED feel
CARD_COLOR = "#1C1C1E"       # Secondary dark
TEXT_COLOR = "#FFFFFF"
TEXT_SECONDARY = "#8E8E93"

# Accents
ACCENT_BLUE = "#0A84FF"      # iOS System Blue
ACCENT_GREEN = "#30D158"     # iOS System Green
ACCENT_RED = "#FF453A"       # iOS System Red
ACCENT_ORANGE = "#FF9F0A"    # iOS System Orange
ACCENT_PURPLE = "#BF5AF2"    # iOS System Purple

# Config
CORNER_RADIUS = 20
BUTTON_HEIGHT = 55
FONT_FAMILY = "Arial"        # Fallback to Arial, ideally SF Pro on Mac

# Set appearance mode and color theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class EMOMApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window Setup ---
        self.title("EMOM Workout Timer")
        self.geometry("450x750") # Taller, sleeker aspect ratio
        self.configure(fg_color=BG_COLOR)
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
        self.work_time_var = ctk.StringVar(value="60")
        self.rest_time_var = ctk.StringVar(value="0")
        self.save_history_var = ctk.BooleanVar(value=True)
        self.notes_var = ctk.StringVar()
        
        self.current_round = 0
        self.time_left = 0
        self.is_running = False
        self.is_rest_phase = False 
        self.is_paused = False
        self.timer_job = None
        self.start_time = None
        self.history_window = None
        
        # --- UI Layout ---
        self._create_widgets()

    def _create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Config
        self.grid_rowconfigure(1, weight=1) # Timer
        self.grid_rowconfigure(2, weight=0) # Controls
        self.grid_rowconfigure(3, weight=0) # History
        
        # 1. Config Card
        self.config_frame = ctk.CTkFrame(self, fg_color=CARD_COLOR, corner_radius=CORNER_RADIUS)
        self.config_frame.grid(row=0, column=0, padx=20, pady=(30, 10), sticky="ew")
        self.config_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Labels (Secondary Text)
        self.lbl_rounds = ctk.CTkLabel(self.config_frame, text="ROUNDS", font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY)
        self.lbl_rounds.grid(row=0, column=0, pady=(15, 5))
        
        self.lbl_work = ctk.CTkLabel(self.config_frame, text="WORK (SEC)", font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY)
        self.lbl_work.grid(row=0, column=1, pady=(15, 5))
        
        self.lbl_rest = ctk.CTkLabel(self.config_frame, text="REST (SEC)", font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY)
        self.lbl_rest.grid(row=0, column=2, pady=(15, 5))

        # Inputs (Big Number Style)
        entry_font = (FONT_FAMILY, 24, "bold")
        
        self.entry_rounds = ctk.CTkEntry(self.config_frame, textvariable=self.total_rounds_var, width=60, 
                                         font=entry_font, justify="center", fg_color="transparent", border_width=0, text_color=ACCENT_BLUE)
        self.entry_rounds.grid(row=1, column=0, pady=(0, 15))

        self.entry_timer = ctk.CTkEntry(self.config_frame, textvariable=self.work_time_var, width=60, 
                                        font=entry_font, justify="center", fg_color="transparent", border_width=0, text_color=ACCENT_GREEN)
        self.entry_timer.grid(row=1, column=1, pady=(0, 15))

        self.entry_rest = ctk.CTkEntry(self.config_frame, textvariable=self.rest_time_var, width=60, 
                                       font=entry_font, justify="center", fg_color="transparent", border_width=0, text_color=ACCENT_ORANGE)
        self.entry_rest.grid(row=1, column=2, pady=(0, 15))

        # Divider for Notes
        self.notes_frame = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        self.notes_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=15, pady=(0, 15))
        
        self.lbl_notes = ctk.CTkLabel(self.notes_frame, text="NOTES", font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY)
        self.lbl_notes.pack(anchor="w", pady=(0, 5))
        
        self.entry_notes = ctk.CTkEntry(self.notes_frame, textvariable=self.notes_var, placeholder_text="Workout details...",
                                        fg_color="#2C2C2E", border_width=0, corner_radius=10, height=35, text_color=TEXT_COLOR)
        self.entry_notes.pack(fill="x")

        # 2. Timer Display (Center Stage)
        self.display_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.display_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.display_frame.grid_columnconfigure(0, weight=1)
        self.display_frame.grid_rowconfigure(0, weight=1)
        self.display_frame.grid_rowconfigure(1, weight=0)
        self.display_frame.grid_rowconfigure(2, weight=1)

        # Round Indicator Pills
        self.lbl_current_round = ctk.CTkLabel(self.display_frame, text="ROUND 0 / 0", font=(FONT_FAMILY, 14, "bold"), text_color=TEXT_SECONDARY)
        self.lbl_current_round.grid(row=0, column=0, sticky="s", pady=(0, 10))

        # Main Timer (Huge)
        self.lbl_main_timer = ctk.CTkLabel(self.display_frame, text="00:00", font=(FONT_FAMILY, 90, "bold"), text_color=TEXT_COLOR)
        self.lbl_main_timer.grid(row=1, column=0)

        # Status
        self.lbl_status = ctk.CTkLabel(self.display_frame, text="READY", font=(FONT_FAMILY, 18, "bold"), text_color=ACCENT_BLUE)
        self.lbl_status.grid(row=2, column=0, sticky="n", pady=(10, 0))


        # 3. Controls (Bottom)
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.grid(row=2, column=0, padx=30, pady=(0, 30), sticky="ew")
        self.button_frame.grid_columnconfigure((0, 1), weight=1)

        self.btn_start = ctk.CTkButton(self.button_frame, text="START", command=self.start_workout, 
                                       height=BUTTON_HEIGHT, corner_radius=BUTTON_HEIGHT//2,
                                       fg_color=ACCENT_GREEN, hover_color="#28a745", 
                                       font=(FONT_FAMILY, 18, "bold"), text_color="black")
        self.btn_start.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.btn_reset = ctk.CTkButton(self.button_frame, text="RESET", command=self.reset_workout, 
                                       height=BUTTON_HEIGHT, corner_radius=BUTTON_HEIGHT//2,
                                       fg_color=CARD_COLOR, hover_color="#3A3A3C", 
                                       font=(FONT_FAMILY, 18, "bold"), text_color=ACCENT_RED)
        self.btn_reset.grid(row=0, column=1, padx=(10, 0), sticky="ew")

        # 4. Footer (History)
        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.footer_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.footer_frame.grid_columnconfigure(1, weight=1)

        self.chk_history = ctk.CTkCheckBox(self.footer_frame, text="Save History", variable=self.save_history_var,
                                           font=(FONT_FAMILY, 12), text_color=TEXT_SECONDARY,
                                           fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE, border_color=TEXT_SECONDARY)
        self.chk_history.grid(row=0, column=0, sticky="w")
        
        self.btn_history = ctk.CTkButton(self.footer_frame, text="History", command=self.open_history_window,
                                         fg_color="transparent", hover_color=CARD_COLOR, 
                                         text_color=ACCENT_PURPLE, font=(FONT_FAMILY, 14, "bold"), 
                                         height=30, width=80, corner_radius=15)
        self.btn_history.grid(row=0, column=1, sticky="e")

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
            self.btn_start.configure(text="PAUSE", fg_color=ACCENT_ORANGE, text_color="black")
            self.update_timer()
        else:
            # Pause
            self.is_paused = True
            self.btn_start.configure(text="RESUME", fg_color=ACCENT_GREEN, text_color="black")
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
        self.lbl_current_round.configure(text=f"ROUND {self.current_round} / {self.total_rounds}")

        # Check conditions
        if self.time_left > 1:
            self.time_left -= 1
            self.timer_job = self.after(1000, self.update_timer)
        else:
            if not self.is_rest_phase:
                 if self.rest_duration > 0:
                     self.start_rest_phase()
                 else:
                     self.next_round()
            else:
                self.next_round()

    def play_sound(self, sound_name="Tink", count=1):
        def _play():
            try:
                # Use local sounds directory relative to this script
                base_path = os.path.dirname(os.path.abspath(__file__))
                sound_file = os.path.join(base_path, "sounds", f"{sound_name}.aiff")
                
                if os.path.exists(sound_file):
                    for _ in range(count):
                        subprocess.run(["afplay", sound_file])
                else:
                    print(f"Sound file not found: {sound_file}")
            except Exception as e:
                print(f"Error playing sound: {e}")

        # Run in a separate thread to not block UI
        threading.Thread(target=_play, daemon=True).start()

    def start_rest_phase(self):
        self.is_rest_phase = True
        self.time_left = self.rest_duration
        self.lbl_status.configure(text="REST TIME", text_color=ACCENT_ORANGE)
        self.lbl_main_timer.configure(text_color=ACCENT_ORANGE)
        self.play_sound("Hero", 1) # Warm, pleasant chime for rest
        self.after(1000, self.update_timer)

    def next_round(self):
        if self.current_round < self.total_rounds:
            self.current_round += 1
            self.is_rest_phase = False
            self.time_left = self.round_duration 
            
            self.lbl_status.configure(text="WORK", text_color=ACCENT_GREEN)
            self.lbl_main_timer.configure(text_color=TEXT_COLOR)
            self.play_sound("Glass", 1) # Exciting 'ding' for work start
            
            self.after(1000, self.update_timer)
            
        else:
            self.finish_workout()

    def finish_workout(self):
        self.save_history(self.total_rounds)
        self.is_running = False
        self.lbl_status.configure(text="COMPLETED!", text_color=ACCENT_BLUE)
        self.lbl_main_timer.configure(text="00:00", text_color=TEXT_COLOR)
        
        self.btn_start.configure(state="normal", text="START", fg_color=ACCENT_GREEN, text_color="black", command=self.start_workout)
        self.entry_rounds.configure(state="normal")
        self.entry_timer.configure(state="normal")
        self.entry_rest.configure(state="normal")

    def reset_workout(self):
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
        
        self.lbl_main_timer.configure(text="00:00", text_color=TEXT_COLOR)
        self.lbl_current_round.configure(text="ROUND 0 / 0")
        self.lbl_status.configure(text="READY", text_color=ACCENT_BLUE)
        
        self.btn_start.configure(state="normal", text="START", fg_color=ACCENT_GREEN, text_color="black", command=self.start_workout)
        self.entry_rounds.configure(state="normal")
        self.entry_timer.configure(state="normal")
        self.entry_rest.configure(state="normal")
        
    def start_workout(self):
        if self.is_running:
            return

        try:
            self.total_rounds = int(self.total_rounds_var.get())
            self.round_duration = int(self.work_time_var.get())
            rest_val = self.rest_time_var.get().strip()
            self.rest_duration = int(rest_val) if rest_val else 0
        except ValueError:
            self.lbl_status.configure(text="INVALID INPUT", text_color=ACCENT_RED)
            return

        self.current_round = 1
        self.time_left = self.round_duration         
        
        self.is_running = True
        self.is_rest_phase = False
        self.is_paused = False
        self.start_time = datetime.datetime.now()
        
        self.btn_start.configure(text="PAUSE", fg_color=ACCENT_ORANGE, text_color="black", command=self.toggle_pause)
        
        self.entry_rounds.configure(state="disabled")
        self.entry_timer.configure(state="disabled")
        self.entry_rest.configure(state="disabled")
        
        self.lbl_status.configure(text="WORK", text_color=ACCENT_GREEN)
        self.lbl_current_round.configure(text=f"ROUND 1 / {self.total_rounds}")
        
        self.play_sound("Glass", 1) # Single beep for first round
        self.update_timer()

    def save_history(self, completed_rounds):
        if not self.save_history_var.get():
            return

        try:
            end_time = datetime.datetime.now().replace(microsecond=0)
            duration = getattr(self, 'round_duration', 0)
            rest = getattr(self, 'rest_duration', 0)
            total_time = completed_rounds * (duration + rest)
            
            if self.start_time:
                start_str = self.start_time.replace(microsecond=0).isoformat()
            else:
                start_str = end_time.isoformat()
            
            notes = self.entry_notes.get()

            row = [
                start_str,
                end_time.isoformat(),
                completed_rounds,
                duration,
                rest,
                total_time,
                notes
            ]
            
            storage.save_workout(row)
            print(f"History saved")
            
        except Exception as e:
            print(f"Error saving history: {e}")

if __name__ == "__main__":
    app = EMOMApp()
    app.mainloop()