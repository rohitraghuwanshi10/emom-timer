import sys
import os
import time

sys.path.append("/Users/rohitraghuwanshi/PythonProjects/emom-timer")

import customtkinter as ctk
from main import EMOMApp

def run_and_capture():
    app = EMOMApp()
    
    # Let layout resolve and center the window
    app.update()
    time.sleep(0.5)
    app.update()
    
    # Open settings dialog
    app.open_settings()
    
    # Wait for the settings dialog to render
    app.update()
    time.sleep(1.0)
    app.update()
    
    dialog = None
    for child in app.winfo_children():
        if isinstance(child, ctk.CTkToplevel):
            dialog = child
            break
            
    if dialog:
        # Make sure layout is fully drawn
        dialog.update()
        time.sleep(0.5)
        dialog.update()
        
        x = dialog.winfo_rootx()
        y = dialog.winfo_rooty()
        w = dialog.winfo_width()
        h = dialog.winfo_height()
        
        # Capture the rectangle
        cmd = f"screencapture -x -R{x},{y},{w},{h} /Users/rohitraghuwanshi/PythonProjects/emom-timer-flutter/screenshots/macOS_Profile.png"
        print(f"Capturing dialog at {x},{y},{w},{h}...")
        os.system(cmd)
    else:
        print("Settings dialog not found!")
        
    app.destroy()

if __name__ == "__main__":
    run_and_capture()
