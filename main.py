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
from details_ui import DetailsFrame
from heart_rate import HeartRateMonitor
from workout import Workout, WorkoutState
from power_management import PowerManager
import json

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

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert") 
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        # Make transparent/floating look
        # Note: CTkLabel inside CTkToplevel automatically inherits theme
        label = ctk.CTkLabel(self.tooltip_window, text=self.text, fg_color="#333333", 
                             text_color="#FFFFFF", corner_radius=6, padx=10, pady=5, font=("Arial", 11))
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class SaveTemplateDialog(ctk.CTkToplevel):
    def __init__(self, parent, default_name, on_save):
        super().__init__(parent)
        self.title("Save Template")
        self.geometry("380x180")
        self.resizable(False, False)
        self.configure(fg_color="#1C1C1E")
        
        # Make modal
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        
        # Center relative to parent
        self.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        x = parent_x + (parent_w - 380) // 2
        y = parent_y + (parent_h - 180) // 2
        self.geometry(f"+{x}+{y}")
        
        lbl_title = ctk.CTkLabel(self, text="Save Template", font=("Arial", 16, "bold"), text_color="#FFFFFF")
        lbl_title.pack(pady=(15, 10))
        
        self.entry = ctk.CTkEntry(self, width=320, fg_color="#000000", text_color="#FFFFFF", corner_radius=8)
        self.entry.pack(pady=(5, 15))
        if default_name:
            self.entry.insert(0, default_name)
            self.entry.select_range(0, 'end')
            self.entry.focus()
            
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        btn_cancel = ctk.CTkButton(btn_frame, text="Cancel", fg_color="#3A3A3C", hover_color="#2C2C2E", width=100, height=32, corner_radius=16, command=self.destroy)
        btn_cancel.pack(side="left", padx=(20, 0))
        
        def save_clicked():
            name = self.entry.get().strip()
            if name:
                on_save(name)
            self.destroy()
            
        btn_save = ctk.CTkButton(btn_frame, text="Save", fg_color="#0A84FF", hover_color="#0060df", width=100, height=32, corner_radius=16, command=save_clicked)
        btn_save.pack(side="right", padx=(0, 20))

class EMOMApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window Setup ---
        self.title("ChronoPulse Active")
        self.geometry("800x900") # Detailed History View + Inc Rest
        self.configure(fg_color=BG_COLOR)
        self.resizable(True, True)
        
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
        self.current_save_history = True
        self.notes_var = ctk.StringVar()
        self.template_var = ctk.StringVar(value="Select Template...")
        
        # Incremental Rest Vars
        self.incremental_rest_var = ctk.BooleanVar(value=False)
        self.inc_time_var = ctk.StringVar(value="5")
        self.inc_interval_var = ctk.StringVar(value="2")
        self.inc_start_var = ctk.StringVar(value="5")

        # Auto Regulation
        self.auto_regulation_var = ctk.BooleanVar(value=False)
        
        # Profile Vars
        self.profile_var = ctk.StringVar(value="Default")
        self.available_profiles = []
        
        # Profile Settings Widgets (Dynamic)
        self.entry_profile_name = None
        self.entry_profile_birth = None
        self.entry_profile_weight = None
        
        # Logic Delegation
        self.workout = None
        self.timer_job = None
        self.start_time = None
        self.history_frame = None
        
        # --- Heart Rate Variables ---
        self.hr_monitor = HeartRateMonitor(on_hr_update=self.on_hr_update, on_status_change=self.on_hr_status_change)
        self.reconnect_attempts = 0
        self.reconnect_job = None
        self.expecting_disconnect = False
        self.current_hr = ctk.StringVar(value="--")
        self.hr_zone = ctk.StringVar(value="")
        self.current_hr = ctk.StringVar(value="--")
        self.hr_zone = ctk.StringVar(value="")
        self.current_max_hr = None
        self.current_max_prework_hr = None
        self.hr_status = ctk.StringVar(value="Disconnected")
        self.is_hr_connecting = False
        
        # --- Power Management ---
        self.power_manager = PowerManager()
        
        # --- UI Layout ---
        self._create_widgets()
        self.load_profiles()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Shortcuts
        self.bind("<space>", self.on_space_pressed)

        # Start background sync with UI refresh callback
        self.trigger_startup_sync()

    def trigger_startup_sync(self):
        def run_sync_and_refresh():
            try:
                import sync_client
                success = sync_client.run_sync()
                if success:
                    self.after(100, self._refresh_after_sync)
            except Exception as e:
                print(f"Error in background sync: {e}")

        import threading
        threading.Thread(target=run_sync_and_refresh, daemon=True).start()

    def _refresh_after_sync(self):
        try:
            print("Sync complete. Refreshing profiles and history UI.")
            old_profile = self.profile_var.get()
            self.load_profiles()
            self.profile_var.set(old_profile)
            if self.history_frame:
                self.history_frame.refresh(old_profile)
        except Exception as e:
            print(f"Error refreshing UI: {e}")

    def on_space_pressed(self, event=None):
        if self._is_typing_active():
            return

        if self.workout is None or self.workout.state in [WorkoutState.IDLE, WorkoutState.FINISHED]:
            self.start_workout()
        else:
            self.toggle_pause()

    def _is_typing_active(self):
        """Checks if focus is currently on a TEXT input (blocking shortcuts)."""
        focused = self.focus_get()
        if not focused: return False
        
        # Only block shortcut if we are in a field where 'Space' is valid text
        text_inputs = [
            self.entry_notes,
            self.entry_profile_name, 
            # self.entry_profile_birth, # Date could technically have spaces? Let's assume yes to be safe
        ]
        
        # Check against text inputs
        for widget in text_inputs:
             if not widget or not widget.winfo_exists(): continue
             try:
                if hasattr(widget, "_entry") and widget._entry == focused:
                    return True
                if hasattr(widget, "_textbox") and widget._textbox == focused:
                    return True
             except:
                pass
                
        # Also check dynamic profile widgets if likely text
        if self.entry_profile_birth:
             try:
                 if self.entry_profile_birth._entry == focused: return True
             except: pass
             
        return False

    def load_profiles(self):
        self.available_profiles = storage.load_profiles()
        if self.available_profiles:
            last = storage.get_last_used_profile()
            if last in self.available_profiles:
                self.profile_var.set(last)
                target = last
            else:
                self.profile_var.set(self.available_profiles[0])
                target = self.available_profiles[0]
                
            if hasattr(self, 'profile_menu'):
                self.profile_menu.configure(values=self.available_profiles)
                self.change_profile(target)

    def change_profile(self, choice):
        print(f"Profile changed to: {choice}")
        storage.update_last_used_profile(choice)
        
        # Cache Max HR
        details = storage.get_profile_details(choice)
        self.current_max_hr = details.get("max_hr")
        self.current_max_prework_hr = details.get("max_prework_hr")
        self.current_auto_connect_hr = details.get("auto_connect_hr", True)
        self.current_save_history = details.get("save_history", 1)
        
        if self.history_frame:
            self.history_frame.refresh(choice)
            
        self.load_templates()

        if hasattr(self, 'lbl_active_profile') and self.lbl_active_profile:
            self.lbl_active_profile.configure(text=f"PROFILE: {choice.upper()}")
            
        # Update Auto-Regulation if HR connected
        if hasattr(self, 'hr_monitor') and self.hr_monitor.is_connected: # Check connection
            if self.current_max_prework_hr:
                self.auto_regulation_var.set(True)
                self.update_auto_regulation()
                print(f"Auto-enabled Auto Regulation for {choice}")
            else:
                self.auto_regulation_var.set(False)
                self.update_auto_regulation()
        elif hasattr(self, 'hr_monitor') and not self.hr_monitor.is_connected:
             self.auto_regulation_var.set(False) # Ensure off if disconnected (though usually handled by status change)
             self.update_auto_regulation()

    def add_profile(self):
        dialog = ctk.CTkInputDialog(text="Enter Profile Name:", title="New Profile")
        new_name = dialog.get_input()
        if new_name and new_name.strip():
            clean_name = new_name.strip().replace("_", " ").title()
            if clean_name not in self.available_profiles:
                # Save to database
                storage.add_profile(clean_name)
                
                # Refresh list
                self.available_profiles = storage.load_profiles()
                
                self.profile_menu.configure(values=self.available_profiles)
                self.profile_var.set(clean_name)
                self.change_profile(clean_name)

    def load_templates(self):
        if not hasattr(self, 'template_menu'):
            return
            
        current_profile = self.profile_var.get()
        templates_dict = storage.get_templates(current_profile)
        
        values = ["Select Template..."]
        if templates_dict:
            values.extend(sorted(list(templates_dict.keys())))
            
        self.template_menu.configure(values=values)
        self.template_var.set("Select Template...")
        if hasattr(self, 'lbl_active_template') and self.lbl_active_template:
            self.lbl_active_template.configure(text="")

    def select_template(self, choice):
        if choice == "Select Template...":
            if hasattr(self, 'lbl_active_template') and self.lbl_active_template:
                self.lbl_active_template.configure(text="")
            return
            
        current_profile = self.profile_var.get()
        templates_dict = storage.get_templates(current_profile)
        
        if choice in templates_dict:
            template = templates_dict[choice]
            self.total_rounds_var.set(str(template.get("rounds", 10)))
            self.work_time_var.set(str(template.get("work_time", 60)))
            self.rest_time_var.set(str(template.get("rest_time", 0)))
            self.notes_var.set(template.get("notes", ""))
            if hasattr(self, 'lbl_active_template') and self.lbl_active_template:
                self.lbl_active_template.configure(text=f"TEMPLATE: {choice.upper()}")
            print(f"Loaded template '{choice}': rounds={template.get('rounds')}, work={template.get('work_time')}, rest={template.get('rest_time')}")

    def save_template_click(self):
        current_profile = self.profile_var.get()
        selected_temp = self.template_var.get()
        default_name = ""
        if selected_temp and selected_temp != "Select Template...":
            default_name = selected_temp
            
        def on_save(template_name):
            clean_name = template_name.strip()
            try:
                rounds = int(self.total_rounds_var.get())
                work_time = int(self.work_time_var.get())
                rest_time = int(self.rest_time_var.get() or 0)
                notes = self.notes_var.get()
            except ValueError:
                print("Invalid configuration values; cannot save template.")
                return
                
            storage.save_template(current_profile, clean_name, rounds, work_time, rest_time, notes)
            self.load_templates()
            self.template_var.set(clean_name)
            if hasattr(self, 'lbl_active_template') and self.lbl_active_template:
                self.lbl_active_template.configure(text=f"TEMPLATE: {clean_name.upper()}")
            print(f"Saved and selected template: {clean_name}")

        SaveTemplateDialog(self, default_name, on_save)

    def delete_template_click(self):
        current_profile = self.profile_var.get()
        selected_template = self.template_var.get()
        
        if not selected_template or selected_template == "Select Template...":
            return
            
        storage.delete_template(current_profile, selected_template)
        self.load_templates()

    def _create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Header
        self.grid_rowconfigure(1, weight=1) # Tabs

        # 0. Global Header Frame (for Profile Selector)
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1) # Spacer to push right

        # Profile UI (Top Right)
        self.profile_ui = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.profile_ui.grid(row=0, column=1, sticky="e")
        
        lbl_profile = ctk.CTkLabel(self.profile_ui, text="Profile:", font=(FONT_FAMILY, 12), text_color=TEXT_SECONDARY)
        lbl_profile.pack(side="left", padx=(0, 5))
        
        self.profile_menu = ctk.CTkOptionMenu(self.profile_ui, variable=self.profile_var, 
                                              values=["Default"], command=self.change_profile,
                                              fg_color=CARD_COLOR, button_color=CARD_COLOR,
                                              button_hover_color="#3A3A3C",
                                              text_color=TEXT_COLOR, font=(FONT_FAMILY, 12))
        self.profile_menu.pack(side="left", padx=(0, 5))
        
        btn_settings = ctk.CTkButton(self.profile_ui, text="⚙️", command=self.open_settings, width=24, height=24,
                                        fg_color="transparent", hover_color="#3A3A3C", text_color=TEXT_SECONDARY, font=(FONT_FAMILY, 14))
        btn_settings.pack(side="left", padx=(0, 0))

        btn_add_profile = ctk.CTkButton(self.profile_ui, text="+", command=self.add_profile, width=24, height=24,
                                        fg_color="transparent", hover_color="#3A3A3C", text_color=TEXT_SECONDARY, font=(FONT_FAMILY, 16))
        btn_add_profile.pack(side="left")

        # Tab View
        self.tabview = ctk.CTkTabview(self, fg_color="transparent", corner_radius=15, width=460)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.tab_workout = self.tabview.add("Workout")
        self.tab_history = self.tabview.add("History")
        self.tab_details = self.tabview.add("Workout Details")
        
        # --- WORKOUT TAB ---
        workout_tab = self.tab_workout
        workout_tab.grid_columnconfigure(0, weight=1)
        workout_tab.grid_rowconfigure(0, weight=0)
        workout_tab.grid_rowconfigure(1, weight=1) # Timer takes available space
        workout_tab.grid_rowconfigure(2, weight=0)
        workout_tab.grid_rowconfigure(3, weight=0)
        workout_tab.grid_rowconfigure(4, weight=0)
        
        # 1. Config Card -> Row 0
        self.config_frame = ctk.CTkFrame(workout_tab, fg_color=CARD_COLOR, corner_radius=CORNER_RADIUS)
        self.config_frame.grid(row=0, column=0, padx=10, pady=(5, 5), sticky="ew")
        self.config_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Template Selection Frame (Row 0)
        self.template_frame = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        self.template_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=15, pady=(15, 5))
        
        lbl_template = ctk.CTkLabel(self.template_frame, text="TEMPLATE", font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY)
        lbl_template.pack(side="left", padx=(0, 5))
        
        self.template_menu = ctk.CTkOptionMenu(self.template_frame, variable=self.template_var,
                                              values=["Select Template..."], command=self.select_template,
                                              fg_color="#2C2C2E", button_color="#2C2C2E",
                                              button_hover_color="#3A3A3C",
                                              text_color=TEXT_COLOR, font=(FONT_FAMILY, 12), height=28)
        self.template_menu.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.btn_save_template = ctk.CTkButton(self.template_frame, text="Save", command=self.save_template_click,
                                               fg_color=ACCENT_BLUE, hover_color="#0060df", height=28, width=50, corner_radius=14,
                                               font=(FONT_FAMILY, 12, "bold"), text_color="white")
        self.btn_save_template.pack(side="left", padx=(0, 5))
        
        self.btn_delete_template = ctk.CTkButton(self.template_frame, text="❌", command=self.delete_template_click,
                                                 fg_color="transparent", hover_color="#3A3A3C", height=28, width=28, corner_radius=14,
                                                 text_color=ACCENT_RED, font=(FONT_FAMILY, 12, "bold"))
        self.btn_delete_template.pack(side="left")

        # Labels (Secondary Text) - Row 1
        self.lbl_rounds = ctk.CTkLabel(self.config_frame, text="ROUNDS", font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY)
        self.lbl_rounds.grid(row=1, column=0, pady=(15, 5))
        
        self.lbl_work = ctk.CTkLabel(self.config_frame, text="WORK (SEC)", font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY)
        self.lbl_work.grid(row=1, column=1, pady=(15, 5))
        
        self.lbl_rest = ctk.CTkLabel(self.config_frame, text="REST (SEC)", font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY)
        self.lbl_rest.grid(row=1, column=2, pady=(15, 5))

        # Inputs (Big Number Style) - Row 2
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

        # Divider for Notes - Row 3
        self.notes_frame = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        self.notes_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=15, pady=(0, 15))
        
        self.lbl_notes = ctk.CTkLabel(self.notes_frame, text="NOTES", font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY)
        self.lbl_notes.pack(anchor="w", pady=(0, 5))
        
        self.entry_notes = ctk.CTkEntry(self.notes_frame, textvariable=self.notes_var, placeholder_text="Workout details...",
                                        fg_color="#2C2C2E", border_width=0, corner_radius=10, height=35, text_color=TEXT_COLOR)
        self.entry_notes.pack(fill="x")

        # Incremental Rest Switch - Row 4
        self.switch_inc = ctk.CTkSwitch(self.config_frame, text="Incremental Rest", variable=self.incremental_rest_var, 
                                        command=self.toggle_inc_options, font=(FONT_FAMILY, 12, "bold"), text_color=TEXT_SECONDARY,
                                        progress_color=ACCENT_PURPLE)
        self.switch_inc.grid(row=4, column=0, columnspan=3, pady=(10, 10))

        # Incremental Rest Options Frame (Initially Hidden logic handled by toggle) - Row 5
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
        
        # 2. Timer Display (Monitor Card) -> Row 1
        self.display_frame = ctk.CTkFrame(workout_tab, fg_color=CARD_COLOR, corner_radius=CORNER_RADIUS)
        self.display_frame.grid(row=1, column=0, padx=10, pady=(5, 5), sticky="nsew")
        self.display_frame.grid_columnconfigure(0, weight=1)
        self.display_frame.grid_columnconfigure(1, weight=1)
        
        # Row 0: Active Profile Name
        self.lbl_active_profile = ctk.CTkLabel(self.display_frame, text="PROFILE: DEFAULT", font=(FONT_FAMILY, 14, "bold"), text_color=TEXT_SECONDARY)
        self.lbl_active_profile.grid(row=0, column=0, sticky="w", padx=20, pady=(15, 0))

        self.lbl_active_template = ctk.CTkLabel(self.display_frame, text="", font=(FONT_FAMILY, 14, "bold"), text_color=ACCENT_BLUE)
        self.lbl_active_template.grid(row=0, column=1, sticky="e", padx=20, pady=(15, 0))

        # Row 1: Header (Rounds | Status)
        self.lbl_current_round = ctk.CTkLabel(self.display_frame, text="ROUND 0 / 0", font=(FONT_FAMILY, 40, "bold"), text_color=TEXT_COLOR)
        self.lbl_current_round.grid(row=1, column=0, sticky="w", padx=20, pady=(5, 0))

        self.lbl_status = ctk.CTkLabel(self.display_frame, text="READY", font=(FONT_FAMILY, 24, "bold"), text_color=ACCENT_BLUE)
        self.lbl_status.grid(row=1, column=1, sticky="e", padx=20, pady=(5, 0))

        # Row 2: Main Timer
        self.lbl_main_timer = ctk.CTkLabel(self.display_frame, text="00:00", font=(FONT_FAMILY, 120, "bold"), text_color=TEXT_COLOR)
        self.lbl_main_timer.grid(row=2, column=0, columnspan=2, pady=(10, 10))

        # Row 3: Heart Rate Display
        self.hr_frame = ctk.CTkFrame(self.display_frame, fg_color="transparent")
        self.hr_frame.grid(row=3, column=0, columnspan=2, sticky="n", pady=(0, 20))
        
        self.lbl_hr_icon = ctk.CTkLabel(self.hr_frame, text="♥", font=(FONT_FAMILY, 50), text_color=ACCENT_RED)
        self.lbl_hr_icon.pack(side="left", padx=(0, 10))
        
        self.lbl_hr_value = ctk.CTkLabel(self.hr_frame, textvariable=self.current_hr, font=(FONT_FAMILY, 90, "bold"), text_color=TEXT_COLOR)
        self.lbl_hr_value.pack(side="left")
        
        self.lbl_hr_unit = ctk.CTkLabel(self.hr_frame, text="BPM", font=(FONT_FAMILY, 20, "bold"), text_color=TEXT_SECONDARY)
        self.lbl_hr_unit.pack(side="left", padx=(5, 0), pady=(30, 0))
        
        self.lbl_hr_zone = ctk.CTkLabel(self.hr_frame, textvariable=self.hr_zone, font=(FONT_FAMILY, 50, "bold"), text_color=ACCENT_BLUE)
        self.lbl_hr_zone.pack(side="left", padx=(20, 0), pady=(15, 0))
        
        # 3. Controls (Bottom) -> Row 2
        self.button_frame = ctk.CTkFrame(workout_tab, fg_color="transparent")
        self.button_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.button_frame.grid_columnconfigure((0, 1), weight=1)

        self.btn_start = ctk.CTkButton(self.button_frame, text="START", command=self.start_workout, 
                                       height=BUTTON_HEIGHT, corner_radius=BUTTON_HEIGHT//2,
                                       fg_color=ACCENT_GREEN, hover_color="#28a745", 
                                       font=(FONT_FAMILY, 18, "bold"), text_color="black")
        self.btn_start.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.btn_stop = ctk.CTkButton(self.button_frame, text="STOP", command=self.reset_workout, 
                                       height=BUTTON_HEIGHT, corner_radius=BUTTON_HEIGHT//2,
                                       fg_color=CARD_COLOR, hover_color="#3A3A3C", 
                                       font=(FONT_FAMILY, 18, "bold"), text_color=ACCENT_RED,
                                       state="disabled")
        self.btn_stop.grid(row=0, column=1, padx=(10, 0), sticky="ew")

        # 4. Heart Rate Controls -> Row 3
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

        # Checkbox for Auto-Regulation (New)
        self.chk_auto_reg = ctk.CTkCheckBox(self.hr_control_frame, text="Auto Regulate Rest", variable=self.auto_regulation_var,
                                            font=(FONT_FAMILY, 12), text_color=TEXT_SECONDARY,
                                            fg_color=ACCENT_PURPLE, hover_color=ACCENT_PURPLE, border_color=TEXT_SECONDARY,
                                            state="disabled", command=self.update_auto_regulation) # Initially disabled
        self.chk_auto_reg.grid(row=0, column=2, padx=10, pady=8, sticky="e")
        
        ToolTip(self.chk_auto_reg, "Extends rest period until HR drops below configured Max Pre-Work HR.")


        # Note: Footer frame removed since Save History is now a profile-level setting
        
        # --- HISTORY TAB ---
        self.history_frame = HistoryFrame(self.tab_history, on_select_callback=self.show_details)
        self.history_frame.pack(fill="both", expand=True)
        
        # --- DETAILS TAB ---
        self.details_frame = DetailsFrame(self.tab_details)
        self.details_frame.pack(fill="both", expand=True)

        # Initial Load
        self._load_config_and_history()

    def _load_config_and_history(self):
        """Loads initial configuration and refreshes history."""
        self.load_profiles()
        if self.history_frame:
            self.history_frame.refresh(self.profile_var.get())

    def update_auto_regulation(self):
        """Updates the running workout instance if the user toggles the checkbox mid-workout."""
        if self.workout:
            val = self.auto_regulation_var.get()
            self.workout.auto_regulation = val
            self.workout.max_prework_hr = self.current_max_prework_hr
            print(f"Updated active workout auto_regulation to: {val}, max_prework_hr to: {self.current_max_prework_hr}")

    def open_settings(self):
        # Create Dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Settings")
        dialog.geometry("400x500")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        # Tab View
        tabview = ctk.CTkTabview(dialog, width=380, height=480)
        tabview.pack(padx=10, pady=10, fill="both", expand=True)
        
        tab_profile = tabview.add("Profile")
        tab_general = tabview.add("General")
        
        # --- PROFILE TAB ---
        current_profile = self.profile_var.get()
        details = storage.get_profile_details(current_profile)
        current_max_hr = details.get("max_hr", "")
        current_max_prework_hr = details.get("max_prework_hr", "")
        current_sex = details.get("sex", "Male")
        current_birth = details.get("birth_date", "")
        current_weight_kg = details.get("weight_kg", "")
        current_unit = details.get("weight_unit_pref", "kg")
        current_auto_connect = details.get("auto_connect_hr", True)

        lbl_title = ctk.CTkLabel(tab_profile, text=f"Edit {current_profile}", font=(FONT_FAMILY, 16, "bold"))
        lbl_title.pack(pady=(10, 10))
        
        # Helper to create rows
        def create_row(parent):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(pady=5)
            return f

        # Max HR
        frm_hr = create_row(tab_profile)
        ctk.CTkLabel(frm_hr, text="Max HR:", font=(FONT_FAMILY, 12)).pack(side="left", padx=5)
        entry_max_hr = ctk.CTkEntry(frm_hr, width=60, justify="center")
        entry_max_hr.pack(side="left", padx=5)
        if current_max_hr: entry_max_hr.insert(0, str(current_max_hr))
        
        # Max Pre-Work HR
        frm_pre_hr = create_row(tab_profile)
        ctk.CTkLabel(frm_pre_hr, text="Pre-Work HR:", font=(FONT_FAMILY, 12)).pack(side="left", padx=5)
        entry_max_pre_hr = ctk.CTkEntry(frm_pre_hr, width=60, justify="center")
        entry_max_pre_hr.pack(side="left", padx=5)
        if current_max_prework_hr: entry_max_pre_hr.insert(0, str(current_max_prework_hr))
        
        # Sex
        frm_sex = create_row(tab_profile)
        ctk.CTkLabel(frm_sex, text="Sex:", font=(FONT_FAMILY, 12)).pack(side="left", padx=5)
        sex_var = ctk.StringVar(value=current_sex)
        opt_sex = ctk.CTkOptionMenu(frm_sex, variable=sex_var, values=["Male", "Female"], width=100)
        opt_sex.pack(side="left", padx=5)
        
        # Birth Date
        frm_birth = create_row(tab_profile)
        ctk.CTkLabel(frm_birth, text="Birth Date:", font=(FONT_FAMILY, 12)).pack(side="left", padx=5)
        entry_birth = ctk.CTkEntry(frm_birth, width=100, justify="center", placeholder_text="YYYY-MM-DD")
        entry_birth.pack(side="left", padx=5)
        if current_birth: entry_birth.insert(0, str(current_birth))
        
        # Weight
        frm_weight = create_row(tab_profile)
        ctk.CTkLabel(frm_weight, text="Weight:", font=(FONT_FAMILY, 12)).pack(side="left", padx=5)
        
        display_weight = ""
        if current_weight_kg:
            try:
                kg_val = float(current_weight_kg)
                if current_unit == "lbs":
                    display_weight = f"{kg_val * 2.20462:.1f}"
                else:
                    display_weight = f"{kg_val:.1f}"
            except: pass

        entry_weight = ctk.CTkEntry(frm_weight, width=60, justify="center")
        entry_weight.pack(side="left", padx=5)
        if display_weight: entry_weight.insert(0, display_weight)
        
        unit_var = ctk.StringVar(value=current_unit)
        seg_unit = ctk.CTkSegmentedButton(frm_weight, values=["kg", "lbs"], variable=unit_var, width=60)
        seg_unit.pack(side="left", padx=5)

        # Auto Connect HR
        frm_auto_connect = create_row(tab_profile)
        auto_connect_var = ctk.BooleanVar(value=current_auto_connect)
        chk_auto_connect = ctk.CTkCheckBox(frm_auto_connect, text="Auto connect HR monitor", variable=auto_connect_var, font=(FONT_FAMILY, 12))
        chk_auto_connect.pack(side="left", padx=5)

        # Save History
        frm_save_history = create_row(tab_profile)
        save_history_var = ctk.BooleanVar(value=details.get("save_history", 1))
        chk_save_history = ctk.CTkCheckBox(frm_save_history, text="Save workout history", variable=save_history_var, font=(FONT_FAMILY, 12))
        chk_save_history.pack(side="left", padx=5)

        def save_profile():
            try:
                val = entry_max_hr.get().strip()
                max_hr = int(val) if val else None
                
                val_pre = entry_max_pre_hr.get().strip()
                max_prework_hr = int(val_pre) if val_pre else None
                
                sex = sex_var.get()
                birth_date = entry_birth.get().strip()
                
                weight_input = entry_weight.get().strip()
                weight_kg = None
                unit_pref = unit_var.get()
                auto_connect_hr = auto_connect_var.get()
                
                if weight_input:
                    try:
                        w_val = float(weight_input)
                        if unit_pref == "lbs":
                            weight_kg = round(w_val / 2.20462, 2)
                        else:
                            weight_kg = round(w_val, 2)
                    except: pass
                
                storage.update_profile(current_profile, max_hr=max_hr, max_prework_hr=max_prework_hr,
                                       sex=sex, birth_date=birth_date, weight_kg=weight_kg, weight_unit_pref=unit_pref, 
                                       auto_connect_hr=auto_connect_hr, save_history=save_history_var.get())
                                       
                self.current_max_hr = max_hr 
                self.current_max_prework_hr = max_prework_hr
                self.current_auto_connect_hr = auto_connect_hr
                self.current_save_history = save_history_var.get()
                dialog.destroy()
                print(f"Saved Settings for {current_profile}")
                
                # Trigger sync in background thread
                import threading
                import sync_client
                threading.Thread(target=sync_client.run_sync, daemon=True).start()
            except ValueError:
                print("Invalid input")

        btn_save = ctk.CTkButton(tab_profile, text="Save Profile", command=save_profile, fg_color=ACCENT_BLUE)
        btn_save.pack(pady=20)

        # --- GENERAL TAB ---
        lbl_general = ctk.CTkLabel(tab_general, text="General Settings", font=(FONT_FAMILY, 16, "bold"))
        lbl_general.pack(pady=(10, 10))
        
        lbl_folder = ctk.CTkLabel(tab_general, text="Data Storage Folder:", font=(FONT_FAMILY, 12, "bold"))
        lbl_folder.pack(anchor="w", padx=20, pady=(10, 0))
        
        current_path = storage.get_base_dir()
        entry_path = ctk.CTkEntry(tab_general, width=300)
        entry_path.pack(pady=5, padx=20)
        entry_path.insert(0, current_path)
        entry_path.configure(state="readonly")
        
        def change_folder():
            new_dir = ctk.filedialog.askdirectory(initialdir=current_path, title="Select Data Folder")
            if new_dir:
                storage.set_base_dir(new_dir)
                entry_path.configure(state="normal")
                entry_path.delete(0, "end")
                entry_path.insert(0, new_dir)
                entry_path.configure(state="readonly")
                
                # Reload App State
                self.load_profiles()
                self._load_config_and_history()
                
                ctk.CTkLabel(tab_general, text="Folder updated! History refreshed.", text_color=ACCENT_GREEN).pack()

        btn_change = ctk.CTkButton(tab_general, text="Change Folder...", command=change_folder, fg_color=ACCENT_ORANGE)
        btn_change.pack(pady=10)
        
        def export_history():
            dest_file = ctk.filedialog.asksaveasfilename(
                initialfile=f"{current_profile}_workout_history_export.csv",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="Export History to CSV"
            )
            if dest_file:
                success = storage.export_to_csv(current_profile, dest_file)
                if success:
                    lbl_export_status.configure(text="History exported successfully!", text_color=ACCENT_GREEN)
                else:
                    lbl_export_status.configure(text="Failed to export history or no workouts found.", text_color=ACCENT_RED)
                    
        btn_export = ctk.CTkButton(tab_general, text="Export History to CSV...", command=export_history, fg_color=ACCENT_BLUE)
        btn_export.pack(pady=(10, 0))
        
        lbl_export_status = ctk.CTkLabel(tab_general, text="", font=(FONT_FAMILY, 11))
        lbl_export_status.pack(pady=(2, 10))
        
        lbl_info = ctk.CTkLabel(tab_general, text="Note: Existing data is NOT moved automatically.\nYou must manually move files if needed.", 
                                text_color=TEXT_SECONDARY, font=(FONT_FAMILY, 11), wraplength=300)
        lbl_info.pack(pady=10)

    def toggle_inc_options(self):
        if self.incremental_rest_var.get():
            self.inc_frame.grid()
        else:
            self.inc_frame.grid_remove()

    def toggle_hr_connection(self):
        # Cancel any pending reconnect job
        if self.reconnect_job:
            self.after_cancel(self.reconnect_job)
            self.reconnect_job = None
        self.reconnect_attempts = 0

        if self.hr_monitor.is_connected:
            self.expecting_disconnect = True
            self.hr_monitor.stop()
            self.btn_connect_hr.configure(text="Connect HR", fg_color=ACCENT_BLUE)
            self.current_hr.set("--")
            self.hr_zone.set("")
        else:
            self.expecting_disconnect = False
            self.hr_monitor.start()
            self.btn_connect_hr.configure(text="Disconnect", fg_color=ACCENT_RED)
            
    def on_hr_update(self, valid_bpm):
        self.after(0, lambda: self.current_hr.set(str(valid_bpm)))
        
        # Zone Calc
        if self.current_max_hr:
            try:
                bpm = int(valid_bpm)
                max_hr = int(self.current_max_hr)
                pct = (bpm / max_hr) * 100
                
                zone = ""
                color = TEXT_SECONDARY
                
                if pct < 50:
                    zone = "WARM UP"
                    color = TEXT_SECONDARY
                elif 50 <= pct < 60:
                    zone = "ZONE 1"
                    color = ACCENT_BLUE 
                elif 60 <= pct < 70:
                    zone = "ZONE 2"
                    color = ACCENT_GREEN
                elif 70 <= pct < 80:
                    zone = "ZONE 3"
                    color = ACCENT_YELLOW
                elif 80 <= pct < 90:
                    zone = "ZONE 4"
                    color = ACCENT_ORANGE
                elif pct >= 90:
                    zone = "ZONE 5"
                    color = ACCENT_RED
                
                print(f"[DEBUG] BPM:{bpm} Max:{max_hr} Pct:{pct:.1f}% Zone:{zone}")
                self.after(0, lambda z=zone, c=color: self._update_zone_ui(z, c))
            except Exception as e:
                print(f"Error calcing zone: {e}")
        else:
             print(f"[DEBUG] No Max HR set (BPM: {valid_bpm})")
             self.after(0, lambda: self._update_zone_ui("", TEXT_SECONDARY))

    def _update_zone_ui(self, text, color):
        self.hr_zone.set(text)
        self.lbl_hr_zone.configure(text_color=color)

    def on_hr_status_change(self, status):
        # Schedule all UI updates on main thread
        self.after(0, lambda: self._handle_hr_status(status))

    def _handle_hr_status(self, status):
        # Check if workout is active
        is_workout_active = (self.workout is not None and 
                             self.workout.state not in [WorkoutState.IDLE, WorkoutState.FINISHED])

        if status == "Disconnected":
            if not self.expecting_disconnect and is_workout_active:
                if self.reconnect_attempts < 2:
                    self.reconnect_attempts += 1
                    retry_status = f"Reconnecting (Attempt {self.reconnect_attempts}/2)..."
                    self.hr_status.set(retry_status)
                    
                    # Schedule reconnection after a short delay
                    if self.reconnect_job:
                        self.after_cancel(self.reconnect_job)
                    self.reconnect_job = self.after(2000, self.hr_monitor.start)
                    return
                else:
                    self.hr_status.set("Reconnection Failed")
                    self.reconnect_attempts = 0
                    self._on_monitor_disconnected()
            else:
                self.reconnect_attempts = 0
                self.hr_status.set(status)
                self._on_monitor_disconnected()
        elif status.endswith("Connected") and status != "Disconnected":
            self.reconnect_attempts = 0
            self.hr_status.set(status)
            self._on_monitor_connected()
        else:
            # For intermediate statuses like "Scanning...", "No HR Device Found", "Error..."
            display_status = status
            if self.reconnect_attempts > 0:
                display_status = f"{status} (Retry {self.reconnect_attempts}/2)"
            self.hr_status.set(display_status)

    def _on_monitor_disconnected(self):
        self.btn_connect_hr.configure(text="Connect HR", fg_color=ACCENT_BLUE)
        self.current_hr.set("--")
        self.hr_zone.set("")
        
        # Disable Auto Reg
        self.chk_auto_reg.configure(state="disabled")
        self.auto_regulation_var.set(False)
        self.update_auto_regulation()

    def _on_monitor_connected(self):
        self.btn_connect_hr.configure(text="Disconnect", fg_color=ACCENT_RED)
        # Enable Auto Reg
        self.chk_auto_reg.configure(state="normal")
        
        # Auto-Check if configured
        if self.current_max_prework_hr:
             try:
                 self.auto_regulation_var.set(True)
                 self.update_auto_regulation()
                 print(f"Auto-enabled Auto Regulation (Max Pre-Work HR: {self.current_max_prework_hr})")
             except Exception as e:
                 print(f"Error auto-enabling regulation: {e}")
    
    def show_details(self, workout_id):
        """Callback from history to show details tab."""
        if not workout_id: return
        
        # Load Data
        data = storage.load_workout_details(workout_id)
        if not data:
            print("No details found for workout ID:", workout_id)
            return
            
        profile_name = self.profile_var.get()
        details = storage.get_profile_details(profile_name)
        max_hr = details.get("max_hr") or 190
        
        self.details_frame.update_view(data, max_hr_profile=max_hr, profile_name=profile_name)
        
        # Switch Tab
        self.tabview.set("Workout Details")
    
    def on_close(self):
        if self.hr_monitor:
            self.hr_monitor.stop()
        if self.power_manager:
            self.power_manager.allow_sleep()
        self.destroy()

    def toggle_pause(self):
        if not self.workout: return
        
        self.workout.pause()
        
        if self.workout.state == WorkoutState.PAUSED:
             self.btn_start.configure(text="RESUME", fg_color=ACCENT_GREEN, text_color="black")
             # Unlock Rounds Input
             self.entry_rounds.configure(state="normal")
             
             if self.timer_job:
                self.after_cancel(self.timer_job)
                self.timer_job = None
        else:
             self.btn_start.configure(text="PAUSE", fg_color=ACCENT_ORANGE, text_color="black")
             # Lock Rounds Input & Update Value
             self.entry_rounds.configure(state="disabled")
             try:
                 new_rounds = int(self.total_rounds_var.get())
                 if new_rounds > 0:
                     # Validation: Cannot go lower than current round
                     if new_rounds < self.workout.current_round:
                         new_rounds = self.workout.current_round
                         self.total_rounds_var.set(str(new_rounds))
                         
                     self.workout.total_rounds = new_rounds
                     self.lbl_current_round.configure(text=self.workout.round_display)
             except:
                 pass
                 
             self.update_timer()

    def update_timer(self):
        if not self.workout: return

        # 1. Tick Logic
        # print("Ticking...") # Debug
        
        current_hr_val = None
        try:
            val_str = self.current_hr.get()
            if val_str and val_str != "--":
                 current_hr_val = int(val_str)
        except:
             pass
             
        current_zone_val = self.hr_zone.get()
        events = self.workout.tick(current_hr=current_hr_val, current_zone=current_zone_val)
        
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
        self.btn_stop.configure(state="disabled")
        self.entry_rounds.configure(state="normal")
        self.entry_timer.configure(state="normal")
        self.entry_rest.configure(state="normal")
        self.template_menu.configure(state="normal")
        self.btn_save_template.configure(state="normal")
        self.btn_delete_template.configure(state="normal")
        self.switch_inc.configure(state="normal") # Enable Swtich

        if self.incremental_rest_var.get():
             self.entry_inc_time.configure(state="normal")
             self.entry_inc_int.configure(state="normal")
             self.entry_inc_start.configure(state="normal")
        
        # Allow Sleep
        self.power_manager.allow_sleep()
        
        # Reset Logic container? Or keep it for inspection? 
        # Usually fine to keep until next start or reset.

    def reset_workout(self):
        # Call workout reset if exists
        if self.workout:
             # If interrupted mid-workout, maybe save? existing logic:
             if self.start_time is not None and self.workout.current_round > 0:
                 completed_rounds = self.workout.get_completed_rounds()
                 if completed_rounds > 0:
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
        self.btn_stop.configure(state="disabled")
        self.entry_rounds.configure(state="normal")
        self.entry_timer.configure(state="normal")
        self.entry_rest.configure(state="normal")
        self.template_menu.configure(state="normal")
        self.btn_save_template.configure(state="normal")
        self.btn_delete_template.configure(state="normal")
        self.switch_inc.configure(state="normal") # Enable Swtich

        if self.incremental_rest_var.get():
             self.entry_inc_time.configure(state="normal")
             self.entry_inc_int.configure(state="normal")
             self.entry_inc_start.configure(state="normal")
             
        # Allow Sleep
        self.power_manager.allow_sleep()
        
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
                
            max_pre_hr = self.current_max_prework_hr
            auto_reg = self.auto_regulation_var.get()

        except ValueError:
            self.lbl_status.configure(text="INVALID INPUT", text_color=ACCENT_RED)
            return

        # Instantiate Logic
        self.workout = Workout(total_rounds, work_duration, rest_duration, rest_inc, rest_interval, rest_start,
                               max_prework_hr=max_pre_hr, auto_regulation=auto_reg)
        self.start_time = datetime.datetime.now()
        
        # Prep UI
        self.btn_start.configure(text="PAUSE", fg_color=ACCENT_ORANGE, text_color="black", command=self.toggle_pause)
        self.btn_stop.configure(state="normal") # Enable Stop
        self.entry_rounds.configure(state="disabled")
        self.entry_timer.configure(state="disabled")
        self.entry_rest.configure(state="disabled")
        self.template_menu.configure(state="disabled")
        self.btn_save_template.configure(state="disabled")
        self.btn_delete_template.configure(state="disabled")
        self.switch_inc.configure(state="disabled")
        self.entry_inc_time.configure(state="disabled")
        self.entry_inc_int.configure(state="disabled")
        self.entry_inc_start.configure(state="disabled")
        
        # Start Logic
        self.workout.start()
        
        # Auto-connect HR if not connected
        if hasattr(self, 'current_auto_connect_hr') and self.current_auto_connect_hr:
            if not self.hr_monitor.is_connected:
                self.toggle_hr_connection()
        
        # Start Loop
        self.update_timer()
        
        # Initial Sound
        self.play_sound("Glass", 1)
        
        # Prevent Sleep
        self.power_manager.prevent_sleep()


    def save_history(self, completed_rounds):
        if not getattr(self, "current_save_history", True):
            return

        try:
            end_time = datetime.datetime.now().replace(microsecond=0)
            
            # Use attributes from self.workout if available, else from input (fallback)
            # Use attributes from self.workout if available, else from input (fallback)
            if self.workout:
                duration = int(self.workout.actual_work_time_sec)
                rest = int(self.workout.actual_rest_time_sec)
                total_time = duration + rest
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

            current_profile = self.profile_var.get()

            # Prepare workout details data
            
            # HR Stats
            hr_details = []
            max_hr = 0
            avg_hr = 0
            
            if self.workout and hasattr(self.workout, 'hr_details'):
                hr_details = self.workout.hr_details
                if hr_details:
                    bpms = [x['bpm'] for x in hr_details]
                    max_hr = max(bpms)
                    if len(bpms) > 0:
                        avg_hr = int(sum(bpms) / len(bpms))

            json_data = {
                "start_time": start_str,
                "end_time": end_time.isoformat(),
                "total_rounds_completed": completed_rounds,
                "work_time_sec": duration,
                "rest_time_sec": rest,
                "total_time_sec": total_time,
                "workout_notes": notes,
                "hr_details": hr_details,
                "max_hr": max_hr,
                "avg_hr": avg_hr
            }
            
            # --- Calorie Calculation ---
            try:
                details = storage.get_profile_details(current_profile)
                sex = details.get("sex")
                birth = details.get("birth_date")
                weight = details.get("weight_kg")
                
                if sex and birth and weight and avg_hr > 0:
                     age = self._calculate_age(birth)
                     total_mins = total_time / 60
                     
                     if sex == "Male":
                         # Calories per minute = [(-55.0969 + (0.6309 × avg_hr) + (0.1988 × weight_kg) + (0.2017 × age)) / 4.184]
                         cpm = (-55.0969 + (0.6309 * avg_hr) + (0.1988 * weight) + (0.2017 * age)) / 4.184
                     else:
                         # Calories per minute = [(-20.4022 + (0.4472 × avg_hr) - (0.1263 × weight_kg) + (0.074 × age)) / 4.184]
                         cpm = (-20.4022 + (0.4472 * avg_hr) - (0.1263 * weight) + (0.074 * age)) / 4.184
                     
                     total_cal = cpm * total_mins
                     json_data["calories_burnt_kcal"] = round(total_cal, 2)
                     print(f"Calories Burnt: {json_data['calories_burnt_kcal']} (Age: {age}, Weight: {weight}, Avg HR: {avg_hr})")
            except Exception as e:
                print(f"Error calculating calories: {e}")
            
            # SQLite database save
            configured_work = int(self.work_time_var.get())
            rest_val = self.rest_time_var.get().strip()
            configured_rest = int(rest_val) if rest_val else 0
            storage.save_workout_to_db(current_profile, json_data, configured_work, configured_rest)
            
            print(f"History saved to SQLite DB for {current_profile}")
            
            # Trigger background sync to Firestore
            try:
                import threading
                import sync_client
                threading.Thread(target=sync_client.run_sync, daemon=True).start()
            except Exception as se:
                print(f"Error triggering background sync: {se}")
            
            # Refresh history tab logic
            if self.history_frame:
                self.history_frame.refresh(current_profile)
            
        except Exception as e:
            print(f"Error saving history: {e}")

    def _calculate_age(self, birth_date_str):
        try:
             birth = datetime.datetime.strptime(birth_date_str, "%Y-%m-%d")
             today = datetime.datetime.now()
             return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        except:
             return 0

if __name__ == "__main__":
    app = EMOMApp()
    app.mainloop()