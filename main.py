import customtkinter as ctk
import threading
from PIL import Image, ImageTk
import os
import sys
import datetime
import time
import storage
import subprocess
from history_ui import HistoryFrame
from heart_rate import HeartRateMonitor
from workout import Workout, WorkoutState

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
ACCENT_YELLOW = "#FFD60A"    # iOS System Yellow

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
        self.geometry("800x850") # Detailed History View
        self.configure(fg_color=BG_COLOR)
        self.resizable(False, False)
        
        # Load Icon
        try:
            if hasattr(sys, '_MEIPASS'):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            icon_path = os.path.join(base_path, "icon.png")
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
        
        # Incremental Rest Vars
        self.incremental_rest_var = ctk.BooleanVar(value=False)
        self.inc_time_var = ctk.StringVar(value="5")
        self.inc_interval_var = ctk.StringVar(value="2")
        self.inc_start_var = ctk.StringVar(value="5")
        
        # Profile Vars
        self.profile_var = ctk.StringVar(value="Default")
        self.available_profiles = []
        
        # Logic Delegation
        self.workout = None
        self.timer_job = None
        self.start_time = None
        self.history_frame = None
        
        # --- Heart Rate Variables ---
        self.hr_monitor = HeartRateMonitor(on_hr_update=self.on_hr_update, on_status_change=self.on_hr_status_change)
        self.current_hr = ctk.StringVar(value="--")
        self.hr_status = ctk.StringVar(value="Disconnected")
        self.is_hr_connecting = False
        
        # --- UI Layout ---
        self._create_widgets()
        self.load_profiles()
        
        # Clean up on exit
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_profiles(self):
        self.available_profiles = storage.get_available_profiles()
        if self.available_profiles:
            self.profile_var.set(self.available_profiles[0])
            if hasattr(self, 'profile_menu'):
                self.profile_menu.configure(values=self.available_profiles)
                self.change_profile(self.available_profiles[0])

    def change_profile(self, choice):
        print(f"Profile changed to: {choice}")
        if self.history_frame:
            self.history_frame.refresh(choice)

    def add_profile(self):
        dialog = ctk.CTkInputDialog(text="Enter Profile Name:", title="New Profile")
        new_name = dialog.get_input()
        if new_name and new_name.strip():
            clean_name = new_name.strip().replace("_", " ").title()
            if clean_name not in self.available_profiles:
                self.available_profiles.append(clean_name)
                self.available_profiles.sort()
                self.profile_menu.configure(values=self.available_profiles)
                self.profile_var.set(clean_name)
                self.change_profile(clean_name)

    def _create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Tab View
        self.tabview = ctk.CTkTabview(self, fg_color="transparent", corner_radius=15, width=460)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.tabview.add("Workout")
        self.tabview.add("History")
        
        # --- WORKOUT TAB ---
        workout_tab = self.tabview.tab("Workout")
        workout_tab.grid_columnconfigure(0, weight=1)

        # 1. Config Card
        self.config_frame = ctk.CTkFrame(workout_tab, fg_color=CARD_COLOR, corner_radius=CORNER_RADIUS)
        self.config_frame.grid(row=0, column=0, padx=10, pady=(20, 10), sticky="ew")
        self.config_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Profile Selector (Top of Config)
        self.profile_frame = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        self.profile_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=15, pady=(15, 5))
        
        lbl_profile = ctk.CTkLabel(self.profile_frame, text="PROFILE", font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY)
        lbl_profile.pack(side="left", padx=(0, 10))
        
        self.profile_menu = ctk.CTkOptionMenu(self.profile_frame, variable=self.profile_var, 
                                              values=["Default"], command=self.change_profile,
                                              fg_color=ACCENT_PURPLE, button_color=ACCENT_PURPLE,
                                              text_color="white", font=(FONT_FAMILY, 12, "bold"))
        self.profile_menu.pack(side="left", fill="x", expand=True)
        
        btn_add_profile = ctk.CTkButton(self.profile_frame, text="+", command=self.add_profile, width=30,
                                        fg_color=CARD_COLOR, hover_color="#3A3A3C", text_color=ACCENT_PURPLE, font=(FONT_FAMILY, 18, "bold"))
        btn_add_profile.pack(side="left", padx=(10, 0))

        # Labels (Secondary Text)
        self.lbl_rounds = ctk.CTkLabel(self.config_frame, text="ROUNDS", font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY)
        self.lbl_rounds.grid(row=1, column=0, pady=(5, 5))
        
        self.lbl_work = ctk.CTkLabel(self.config_frame, text="WORK (SEC)", font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY)
        self.lbl_work.grid(row=1, column=1, pady=(5, 5))
        
        self.lbl_rest = ctk.CTkLabel(self.config_frame, text="REST (SEC)", font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY)
        self.lbl_rest.grid(row=1, column=2, pady=(5, 5))

        # Inputs (Big Number Style)
        entry_font = (FONT_FAMILY, 24, "bold")
        
        self.entry_rounds = ctk.CTkEntry(self.config_frame, textvariable=self.total_rounds_var, width=60, 
                                         font=entry_font, justify="center", fg_color="transparent", border_width=0, text_color=ACCENT_BLUE)
        self.entry_rounds.grid(row=2, column=0, pady=(0, 15))

        self.entry_timer = ctk.CTkEntry(self.config_frame, textvariable=self.work_time_var, width=60, 
                                        font=entry_font, justify="center", fg_color="transparent", border_width=0, text_color=ACCENT_GREEN)
        self.entry_timer.grid(row=2, column=1, pady=(0, 15))

        self.entry_rest = ctk.CTkEntry(self.config_frame, textvariable=self.rest_time_var, width=60, 
                                       font=entry_font, justify="center", fg_color="transparent", border_width=0, text_color=ACCENT_ORANGE)
        self.entry_rest.grid(row=2, column=2, pady=(0, 15))

        # Divider for Notes
        self.notes_frame = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        self.notes_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=15, pady=(0, 15))
        
        self.lbl_notes = ctk.CTkLabel(self.notes_frame, text="NOTES", font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY)
        self.lbl_notes.pack(anchor="w", pady=(0, 5))
        
        self.entry_notes = ctk.CTkEntry(self.notes_frame, textvariable=self.notes_var, placeholder_text="Workout details...",
                                        fg_color="#2C2C2E", border_width=0, corner_radius=10, height=35, text_color=TEXT_COLOR)
        self.entry_notes.pack(fill="x")

        # Incremental Rest Switch
        self.switch_inc = ctk.CTkSwitch(self.config_frame, text="Incremental Rest", variable=self.incremental_rest_var, 
                                        command=self.toggle_inc_options, font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY,
                                        progress_color=ACCENT_PURPLE)
        self.switch_inc.grid(row=4, column=0, columnspan=3, pady=(10, 10))

        # Incremental Rest Options Frame (Initially Hidden logic handled by toggle)
        self.inc_frame = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        self.inc_frame.grid(row=5, column=0, columnspan=3, sticky="ew", padx=15, pady=(0, 15))
        self.inc_frame.grid_remove() # Hide initially if False
        self.inc_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        lbl_inc_time = ctk.CTkLabel(self.inc_frame, text="+ SECONDS", font=(FONT_FAMILY, 10, "bold"), text_color=TEXT_SECONDARY)
        lbl_inc_time.grid(row=0, column=0)
        self.entry_inc_time = ctk.CTkEntry(self.inc_frame, textvariable=self.inc_time_var, width=50, justify="center")
        self.entry_inc_time.grid(row=1, column=0)

        lbl_inc_int = ctk.CTkLabel(self.inc_frame, text="EVERY (RNDS)", font=(FONT_FAMILY, 10, "bold"), text_color=TEXT_SECONDARY)
        lbl_inc_int.grid(row=0, column=1)
        self.entry_inc_int = ctk.CTkEntry(self.inc_frame, textvariable=self.inc_interval_var, width=50, justify="center")
        self.entry_inc_int.grid(row=1, column=1)

        lbl_inc_start = ctk.CTkLabel(self.inc_frame, text="START (RND)", font=(FONT_FAMILY, 10, "bold"), text_color=TEXT_SECONDARY)
        lbl_inc_start.grid(row=0, column=2)
        self.entry_inc_start = ctk.CTkEntry(self.inc_frame, textvariable=self.inc_start_var, width=50, justify="center")
        self.entry_inc_start.grid(row=1, column=2)
        
        # 2. Timer Display (Center Stage)
        self.display_frame = ctk.CTkFrame(workout_tab, fg_color="transparent")
        self.display_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.display_frame.grid_columnconfigure(0, weight=1)
        
        # Round Indicator
        self.lbl_current_round = ctk.CTkLabel(self.display_frame, text="0 / 0", font=(FONT_FAMILY, 90, "bold"), text_color=TEXT_SECONDARY)
        self.lbl_current_round.grid(row=0, column=0, sticky="s", pady=(0, 10))

        # Main Timer
        self.lbl_main_timer = ctk.CTkLabel(self.display_frame, text="00:00", font=(FONT_FAMILY, 90, "bold"), text_color=TEXT_COLOR)
        self.lbl_main_timer.grid(row=1, column=0)

        # Heart Rate Display (Embedded in Timer Area)
        self.hr_frame = ctk.CTkFrame(self.display_frame, fg_color="transparent")
        self.hr_frame.grid(row=2, column=0, sticky="n", pady=(5, 0))
        
        self.lbl_hr_icon = ctk.CTkLabel(self.hr_frame, text="♥", font=(FONT_FAMILY, 24), text_color=ACCENT_RED)
        self.lbl_hr_icon.pack(side="left", padx=(0, 5))
        
        self.lbl_hr_value = ctk.CTkLabel(self.hr_frame, textvariable=self.current_hr, font=(FONT_FAMILY, 24, "bold"), text_color=TEXT_COLOR)
        self.lbl_hr_value.pack(side="left")
        
        self.lbl_hr_unit = ctk.CTkLabel(self.hr_frame, text="BPM", font=(FONT_FAMILY, 14, "bold"), text_color=TEXT_SECONDARY)
        self.lbl_hr_unit.pack(side="left", padx=(5, 0), pady=(8, 0))

        # Status
        self.lbl_status = ctk.CTkLabel(self.display_frame, text="READY", font=(FONT_FAMILY, 18, "bold"), text_color=ACCENT_BLUE)
        self.lbl_status.grid(row=3, column=0, sticky="n", pady=(10, 0))

        # 3. Controls (Bottom)
        self.button_frame = ctk.CTkFrame(workout_tab, fg_color="transparent")
        self.button_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
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
        
        # 4. Heart Rate Controls
        self.hr_control_frame = ctk.CTkFrame(workout_tab, fg_color=CARD_COLOR, corner_radius=15)
        self.hr_control_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.hr_control_frame.grid_columnconfigure(0, weight=1)
        self.hr_control_frame.grid_columnconfigure(1, weight=0)

        self.lbl_hr_status = ctk.CTkLabel(self.hr_control_frame, textvariable=self.hr_status, 
                                          font=(FONT_FAMILY, 12), text_color=TEXT_SECONDARY)
        self.lbl_hr_status.grid(row=0, column=0, padx=15, pady=8, sticky="w")
        
        self.btn_connect_hr = ctk.CTkButton(self.hr_control_frame, text="Connect HR", command=self.toggle_hr_connection,
                                            fg_color=ACCENT_BLUE, hover_color="#0060df", height=28, width=100, corner_radius=14,
                                            font=(FONT_FAMILY, 12, "bold"))
        self.btn_connect_hr.grid(row=0, column=1, padx=10, pady=8, sticky="e")

        # 5. Footer (History)
        self.footer_frame = ctk.CTkFrame(workout_tab, fg_color="transparent")
        self.footer_frame.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.footer_frame.grid_columnconfigure(1, weight=1)

        self.chk_history = ctk.CTkCheckBox(self.footer_frame, text="Save History", variable=self.save_history_var,
                                           font=(FONT_FAMILY, 12), text_color=TEXT_SECONDARY,
                                           fg_color=ACCENT_BLUE, hover_color=ACCENT_BLUE, border_color=TEXT_SECONDARY)
        self.chk_history.grid(row=0, column=0, sticky="w")
        
        # --- HISTORY TAB ---
        history_tab = self.tabview.tab("History")
        history_tab.grid_columnconfigure(0, weight=1)
        history_tab.grid_rowconfigure(0, weight=1)
        
        self.history_frame = HistoryFrame(history_tab) # Embed new frame
        self.history_frame.grid(row=0, column=0, sticky="nsew")

    def toggle_inc_options(self):
        if self.incremental_rest_var.get():
            self.inc_frame.grid()
        else:
            self.inc_frame.grid_remove()

    def toggle_hr_connection(self):
        if self.hr_monitor.is_connected:
            self.hr_monitor.stop()
            self.btn_connect_hr.configure(text="Connect HR", fg_color=ACCENT_BLUE)
            self.current_hr.set("--")
        else:
            self.hr_monitor.start()
            self.btn_connect_hr.configure(text="Disconnect", fg_color=ACCENT_RED)
            
    def on_hr_update(self, valid_bpm):
        self.after(0, lambda: self.current_hr.set(str(valid_bpm)))

    def on_hr_status_change(self, status):
        self.after(0, lambda: self.hr_status.set(status))
        if status == "Disconnected":
             self.after(0, lambda: self.btn_connect_hr.configure(text="Connect HR", fg_color=ACCENT_BLUE))
             self.after(0, lambda: self.current_hr.set("--"))
        elif status.endswith("Connected") and not status == "Disconnected":
             self.after(0, lambda: self.btn_connect_hr.configure(text="Disconnect", fg_color=ACCENT_RED))

    def on_close(self):
        if self.hr_monitor:
            self.hr_monitor.stop()
        self.destroy()

    def toggle_pause(self):
        if not self.workout: return
        
        self.workout.pause()
        
        if self.workout.state == WorkoutState.PAUSED:
             self.btn_start.configure(text="RESUME", fg_color=ACCENT_GREEN, text_color="black")
             if self.timer_job:
                self.after_cancel(self.timer_job)
                self.timer_job = None
        else:
             self.btn_start.configure(text="PAUSE", fg_color=ACCENT_ORANGE, text_color="black")
             self.update_timer()

    def update_timer(self):
        if not self.workout: return

        # 1. Tick Logic
        print("Ticking...") # Debug
        events = self.workout.tick()
        
        # 2. Handle Events
        if events.sound_name:
             self.play_sound(events.sound_name, events.sound_count)

        if events.finished:
             self.finish_workout()
             return

        # 3. Update UI
        self.lbl_main_timer.configure(text=self.workout.time_display)
        self.lbl_current_round.configure(text=self.workout.round_display)
        self.lbl_status.configure(text=self.workout.status_text)
        
        # Update Colors based on state
        if self.workout.state == WorkoutState.PREP:
             self.lbl_status.configure(text_color=ACCENT_YELLOW)
             self.lbl_main_timer.configure(text_color=ACCENT_YELLOW)
        elif self.workout.state == WorkoutState.WORK:
             self.lbl_status.configure(text_color=ACCENT_GREEN)
             self.lbl_main_timer.configure(text_color=TEXT_COLOR)
        elif self.workout.state == WorkoutState.REST:
             self.lbl_status.configure(text_color=ACCENT_ORANGE)
             self.lbl_main_timer.configure(text_color=ACCENT_ORANGE)

        # 4. Schedule next tick if still running/active
        if self.workout.state not in [WorkoutState.IDLE, WorkoutState.FINISHED, WorkoutState.PAUSED]:
            self.timer_job = self.after(1000, self.update_timer)

    def play_sound(self, sound_name="Glass", count=1):
        def _play():
            try:
                # Default to .wav for everyone (cross-platform standard)
                is_windows = sys.platform == 'win32'
                
                if hasattr(sys, '_MEIPASS'):
                    base_path = sys._MEIPASS
                else:
                    base_path = os.path.dirname(os.path.abspath(__file__))
                
                # 1. Try target .wav
                sound_file = os.path.join(base_path, "sounds", f"{sound_name}.wav")
                
                # 2. Play if found
                if os.path.exists(sound_file):
                    for i in range(count):
                        if is_windows:
                            import winsound
                            winsound.PlaySound(sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
                        else:
                            # Use Popen to avoid blocking, so we can control timing manually
                            subprocess.Popen(["afplay", sound_file])
                        
                        if i < count - 1:
                            time.sleep(0.4) # Short delay between dings
                else:
                    print(f"Sound file not found: {sound_file}")

            except Exception as e:
                print(f"Error playing sound: {e}")

        # Run in a separate thread to not block UI
        threading.Thread(target=_play, daemon=True).start()

    def finish_workout(self):
        # UI Updates for Finished
        self.lbl_status.configure(text="COMPLETED!", text_color=ACCENT_BLUE)
        self.lbl_main_timer.configure(text="00:00", text_color=TEXT_COLOR)
        
        self.save_history(self.workout.total_rounds) # Use workout attribute directly
        
        self.btn_start.configure(state="normal", text="START", fg_color=ACCENT_GREEN, text_color="black", command=self.start_workout)
        self.entry_rounds.configure(state="normal")
        self.entry_timer.configure(state="normal")
        self.entry_rest.configure(state="normal")
        self.switch_inc.configure(state="normal") # Enable Swtich

        if self.incremental_rest_var.get():
             self.entry_inc_time.configure(state="normal")
             self.entry_inc_int.configure(state="normal")
             self.entry_inc_start.configure(state="normal")
        
        # Reset Logic container? Or keep it for inspection? 
        # Usually fine to keep until next start or reset.

    def reset_workout(self):
        # Call workout reset if exists
        if self.workout:
             # If interrupted mid-workout, maybe save? existing logic:
             if self.start_time is not None and self.workout.current_round > 0:
                 completed_rounds = max(0, self.workout.current_round - 1)
                 self.save_history(completed_rounds)
                 
             self.workout.reset()

        if self.timer_job:
            self.after_cancel(self.timer_job)
            self.timer_job = None
            
        self.start_time = None
        
        self.lbl_main_timer.configure(text="00:00", text_color=TEXT_COLOR)
        self.lbl_current_round.configure(text="0 / 0")
        self.lbl_status.configure(text="READY", text_color=ACCENT_BLUE)
        
        self.btn_start.configure(state="normal", text="START", fg_color=ACCENT_GREEN, text_color="black", command=self.start_workout)
        self.entry_rounds.configure(state="normal")
        self.entry_timer.configure(state="normal")
        self.entry_rest.configure(state="normal")
        self.switch_inc.configure(state="normal") # Enable Swtich

        if self.incremental_rest_var.get():
             self.entry_inc_time.configure(state="normal")
             self.entry_inc_int.configure(state="normal")
             self.entry_inc_start.configure(state="normal")
        
    def start_workout(self):
        # If already running
        if self.workout and self.workout.state not in [WorkoutState.IDLE, WorkoutState.FINISHED] and self.workout.state != WorkoutState.PAUSED:
             return 

        if self.workout and self.workout.state == WorkoutState.PAUSED:
            self.toggle_pause()
            return
            
        try:
            total_rounds = int(self.total_rounds_var.get())
            work_duration = int(self.work_time_var.get())
            rest_val = self.rest_time_var.get().strip()
            rest_duration = int(rest_val) if rest_val else 0
            
            # Incremental Params
            rest_inc = 0
            rest_interval = 1
            rest_start = 1
            
            if self.incremental_rest_var.get():
                rest_inc = int(self.inc_time_var.get())
                rest_interval = int(self.inc_interval_var.get())
                rest_start = int(self.inc_start_var.get())

        except ValueError:
            self.lbl_status.configure(text="INVALID INPUT", text_color=ACCENT_RED)
            return

        # Instantiate Logic
        self.workout = Workout(total_rounds, work_duration, rest_duration, rest_inc, rest_interval, rest_start)
        self.start_time = datetime.datetime.now()
        
        # Prep UI
        self.btn_start.configure(text="PAUSE", fg_color=ACCENT_ORANGE, text_color="black", command=self.toggle_pause)
        self.entry_rounds.configure(state="disabled")
        self.entry_timer.configure(state="disabled")
        self.entry_rest.configure(state="disabled")
        self.switch_inc.configure(state="disabled")
        self.entry_inc_time.configure(state="disabled")
        self.entry_inc_int.configure(state="disabled")
        self.entry_inc_start.configure(state="disabled")
        
        # Start Logic
        self.workout.start()
        
        # Start Loop
        self.update_timer()
        
        # Initial Sound
        self.play_sound("Glass", 1)


    def save_history(self, completed_rounds):
        if not self.save_history_var.get():
            return

        try:
            end_time = datetime.datetime.now().replace(microsecond=0)
            
            # Use attributes from self.workout if available, else from input (fallback)
            if self.workout:
                duration = self.workout.work_duration
                rest = self.workout.rest_duration
            else:
                duration = int(self.work_time_var.get())
                rest = int(self.rest_time_var.get() or 0)
                
            total_time = completed_rounds * (duration + rest)
            
            if self.start_time:
                start_str = self.start_time.replace(microsecond=0).isoformat()
            else:
                start_str = end_time.isoformat()
            
            notes = self.entry_notes.get()
            
            # Clear notes after saving
            self.entry_notes.delete(0, 'end')

            row = [
                start_str,
                end_time.isoformat(),
                completed_rounds,
                duration,
                rest,
                total_time,
                notes
            ]
            
            current_profile = self.profile_var.get()
            storage.save_workout(row, current_profile)
            print(f"History saved for {current_profile}")
            
            # Refresh history tab logic
            if self.history_frame:
                self.history_frame.refresh(current_profile)
            
        except Exception as e:
            print(f"Error saving history: {e}")

if __name__ == "__main__":
    app = EMOMApp()
    app.mainloop()