import csv
import os
import glob
import sys

# Define base path (User Documents)
DOCS_DIR = os.path.expanduser("~/Documents/EMOM Timer")

def _ensure_dir():
    if not os.path.exists(DOCS_DIR):
        os.makedirs(DOCS_DIR)

LEGACY_FILE = os.path.join(DOCS_DIR, "workout_history.csv")

def get_filename(profile_name="Default"):
    _ensure_dir()
    safe_name = profile_name.lower().replace(" ", "_")
    return os.path.join(DOCS_DIR, f"{safe_name}_workout_history.csv")

def get_available_profiles():
    _ensure_dir()
    
    # 1. Migration Check
    default_file = get_filename("Default")
    if os.path.exists(LEGACY_FILE) and not os.path.exists(default_file):
        try:
            os.rename(LEGACY_FILE, default_file)
            print(f"Migrated legacy history to {default_file}")
        except OSError as e:
            print(f"Error migrating legacy file: {e}")

    # 2. Scan
    pattern = os.path.join(DOCS_DIR, "*_workout_history.csv")
    files = glob.glob(pattern)
    
    profiles = []
    for f in files:
        basename = os.path.basename(f)
        # remove _workout_history.csv
        raw_name = basename.replace("_workout_history.csv", "")
        # Convert "rohit_raghu" -> "Rohit Raghu"
        pretty_name = raw_name.replace("_", " ").title()
        profiles.append(pretty_name)
    
    if not profiles:
        profiles = ["Default"]
        
    return sorted(profiles)

def save_workout(row, profile_name="Default"):
    filename = get_filename(profile_name)
    file_exists = os.path.isfile(filename)
    
    try:
        with open(filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["Start Time", "End Time", "Rounds", "Work Duration", "Rest Duration", "Total Time", "Notes"])
            writer.writerow(row)
    except IOError as e:
        print(f"Error saving to CSV: {e}")

def load_history(profile_name="Default"):
    filename = get_filename(profile_name)
    history = []
    if not os.path.exists(filename):
        return history
        
    try:
        with open(filename, mode='r') as file:
            reader = csv.reader(file)
            next(reader, None)  # Skip header
            for row in reader:
                history.append(row)
    except IOError as e:
        print(f"Error loading CSV: {e}")
        
    return history
