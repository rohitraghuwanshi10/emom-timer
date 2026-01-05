import csv
import os
import glob
import sys
import json
import datetime

# Define base path (User Documents)
DOCS_DIR = os.path.expanduser("~/Documents/EMOM Timer")
PROFILES_FILE = os.path.join(DOCS_DIR, "profiles.json")

def _ensure_dir():
    if not os.path.exists(DOCS_DIR):
        os.makedirs(DOCS_DIR)

LEGACY_FILE = os.path.join(DOCS_DIR, "workout_history.csv")

def _generate_filename(profile_name):
    safe_name = profile_name.lower().replace(" ", "_")
    return os.path.join(DOCS_DIR, f"{safe_name}_workout_history.csv")

def get_filename(profile_name="Default"):
    _ensure_dir()
    
    # Try to get from JSON
    if os.path.exists(PROFILES_FILE):
        try:
            with open(PROFILES_FILE, 'r') as f:
                data = json.load(f)
                profiles = data.get("profiles", {})
                if profile_name in profiles:
                    # Return absolute path assuming filename in JSON is relative or absolute
                    # Let's verify if we store relative. Plan says "default_workout_history.csv".
                    fname = profiles[profile_name]["filename"]
                    return os.path.join(DOCS_DIR, fname)
        except Exception as e:
            print(f"Error reading profiles.json: {e}")
            
    # Fallback / Default behavior
    return _generate_filename(profile_name)

def load_profiles():
    _ensure_dir()
    
    # Check for profiles.json
    if os.path.exists(PROFILES_FILE):
        try:
            with open(PROFILES_FILE, 'r') as f:
                data = json.load(f)
                return sorted(list(data.get("profiles", {}).keys()))
        except Exception as e:
            print(f"Error loading profiles.json: {e}")
            return ["Default"]

    # --- MIGRATION LOGIC (First Run) ---
    print("Migrating profiles to JSON...")
    
    # 1. Migration Check (Legacy file)
    default_filename = "default_workout_history.csv"
    default_abs_path = os.path.join(DOCS_DIR, default_filename)
    
    if os.path.exists(LEGACY_FILE) and not os.path.exists(default_abs_path):
        try:
            os.rename(LEGACY_FILE, default_abs_path)
            print(f"Migrated legacy history to {default_abs_path}")
        except OSError as e:
            print(f"Error migrating legacy file: {e}")

    # 2. Scan
    pattern = os.path.join(DOCS_DIR, "*_workout_history.csv")
    files = glob.glob(pattern)
    
    profiles_data = {
        "profiles": {},
        "last_used_profile": "Default"
    }
    
    # Ensure Default exists
    if not any(f.endswith(default_filename) for f in files):
        # If no files at all, creates empty default entry
        pass

    found_profiles = []
    
    for f in files:
        basename = os.path.basename(f)
        # remove _workout_history.csv
        raw_name = basename.replace("_workout_history.csv", "")
        # Convert "rohit_raghu" -> "Rohit Raghu"
        pretty_name = raw_name.replace("_", " ").title()
        
        profiles_data["profiles"][pretty_name] = {
            "filename": basename,
            "created_at": datetime.datetime.now().isoformat()
        }
        found_profiles.append(pretty_name)
    
    if "Default" not in profiles_data["profiles"]:
         profiles_data["profiles"]["Default"] = {
            "filename": default_filename,
            "created_at": datetime.datetime.now().isoformat()
        }
        
    # Save JSON
    try:
        with open(PROFILES_FILE, 'w') as f:
            json.dump(profiles_data, f, indent=4)
    except Exception as e:
        print(f"Error creating profiles.json: {e}")
        
    sorted_profiles = sorted(list(profiles_data["profiles"].keys()))
    return sorted_profiles

def add_profile(profile_name):
    _ensure_dir()
    
    # Load existing
    data = {"profiles": {}, "last_used_profile": "Default"}
    if os.path.exists(PROFILES_FILE):
        try:
            with open(PROFILES_FILE, 'r') as f:
                data = json.load(f)
        except:
            pass

    # Add new
    if profile_name not in data["profiles"]:
        filename = f"{profile_name.lower().replace(' ', '_')}_workout_history.csv"
        data["profiles"][profile_name] = {
            "filename": filename,
            "created_at": datetime.datetime.now().isoformat()
        }
        
        with open(PROFILES_FILE, 'w') as f:
            json.dump(data, f, indent=4)
            
    return data["profiles"][profile_name]["filename"]

def get_last_used_profile():
    if os.path.exists(PROFILES_FILE):
            try:
                with open(PROFILES_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get("last_used_profile", "Default")
            except:
                pass
    return "Default"

def update_last_used_profile(profile_name):
    if os.path.exists(PROFILES_FILE):
            try:
                with open(PROFILES_FILE, 'r') as f:
                    data = json.load(f)
                
                data["last_used_profile"] = profile_name
                
                with open(PROFILES_FILE, 'w') as f:
                    json.dump(data, f, indent=4)
            except Exception as e:
                print(f"Error updating last profile: {e}")

# Kept for backward compatibility if needed, but main calls load_profiles now
def get_available_profiles():
    return load_profiles()

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
