import csv
import os
import glob
import sys
import json
import datetime
import time

# Define base path (User Documents)
# Define Config Path
_CONFIG_FILE = os.path.expanduser("~/.emom_timer_config.json")
_BASE_DIR = None # Lazily loaded

def get_base_dir():
    global _BASE_DIR
    if _BASE_DIR:
        return _BASE_DIR
        
    # Load from config
    default_dir = os.path.expanduser("~/Documents/EMOM Timer")
    try:
        if os.path.exists(_CONFIG_FILE):
            with open(_CONFIG_FILE, 'r') as f:
                config = json.load(f)
                path = config.get("base_dir")
                if path:
                    _BASE_DIR = path
                    return _BASE_DIR
    except Exception as e:
        print(f"Error loading config: {e}")
        
    _BASE_DIR = default_dir
    return _BASE_DIR

def set_base_dir(new_path):
    global _BASE_DIR
    if not new_path: return
    
    _BASE_DIR = new_path
    
    # Save to config
    try:
        config = {}
        if os.path.exists(_CONFIG_FILE):
             with open(_CONFIG_FILE, 'r') as f:
                 config = json.load(f)
        
        config["base_dir"] = new_path
        
        with open(_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
            
        print(f"Base dir updated to: {new_path}")
        
    except Exception as e:
        print(f"Error saving config: {e}")

def get_profiles_file():
    return os.path.join(get_base_dir(), "profiles.json")

def _ensure_dir():
    base = get_base_dir()
    if not os.path.exists(base):
        os.makedirs(base)



def _generate_filename(profile_name):
    safe_name = profile_name.lower().replace(" ", "_")
    return os.path.join(get_base_dir(), f"{safe_name}_workout_history.csv")

def get_filename(profile_name="Default"):
    _ensure_dir()
    
    # Try to get from JSON
    profiles_file = get_profiles_file()
    if os.path.exists(profiles_file):
        try:
            with open(profiles_file, 'r') as f:
                data = json.load(f)
                profiles = data.get("profiles", {})
                if profile_name in profiles:
                    # Return absolute path assuming filename in JSON is relative or absolute
                    # Let's verify if we store relative. Plan says "default_workout_history.csv".
                    fname = profiles[profile_name]["filename"]
                    return os.path.join(get_base_dir(), fname)
        except Exception as e:
            print(f"Error reading profiles.json: {e}")
            
    # Fallback / Default behavior
    return _generate_filename(profile_name)

def load_profiles():
    _ensure_dir()
    
    # Check for profiles.json
    profiles_file = get_profiles_file()
    if os.path.exists(profiles_file):
        try:
            with open(profiles_file, 'r') as f:
                data = json.load(f)
                return sorted(list(data.get("profiles", {}).keys()))
        except Exception as e:
            print(f"Error loading profiles.json: {e}")
            return ["Default"]

    # --- MIGRATION LOGIC (First Run) ---
    print("Migrating profiles to JSON...")
    
    # 1. Migration Check (Legacy file)
    # 1. Migration Check (Legacy file)
    legacy_file = os.path.join(get_base_dir(), "workout_history.csv")
    default_filename = "default_workout_history.csv"
    default_abs_path = os.path.join(get_base_dir(), default_filename)
    
    if os.path.exists(legacy_file) and not os.path.exists(default_abs_path):
        try:
            os.rename(legacy_file, default_abs_path)
            print(f"Migrated legacy history to {default_abs_path}")
        except OSError as e:
            print(f"Error migrating legacy file: {e}")

    # 2. Scan
    pattern = os.path.join(get_base_dir(), "*_workout_history.csv")
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
        with open(profiles_file, 'w') as f:
            json.dump(profiles_data, f, indent=4)
    except Exception as e:
        print(f"Error creating profiles.json: {e}")
        
    sorted_profiles = sorted(list(profiles_data["profiles"].keys()))
    
    return sorted_profiles



def add_profile(profile_name, max_hr=None, max_prework_hr=None, sex=None, birth_date=None, weight_kg=None, weight_unit_pref="kg", auto_connect_hr=True):
    _ensure_dir()
    
    # Load existing
    data = {"profiles": {}, "last_used_profile": "Default"}
    profiles_file = get_profiles_file()
    if os.path.exists(profiles_file):
        try:
            with open(profiles_file, 'r') as f:
                data = json.load(f)
        except:
            pass

    # Add new
    if profile_name not in data["profiles"]:
        filename = f"{profile_name.lower().replace(' ', '_')}_workout_history.csv"
        data["profiles"][profile_name] = {
            "filename": filename,
            "created_at": datetime.datetime.now().isoformat(),
            "max_hr": max_hr,
            "max_prework_hr": max_prework_hr,
            "sex": sex,
            "birth_date": birth_date,
            "weight_kg": weight_kg,
            "weight_unit_pref": weight_unit_pref,
            "auto_connect_hr": auto_connect_hr
        }
        
        with open(profiles_file, 'w') as f:
            json.dump(data, f, indent=4)
            
    return data["profiles"][profile_name]["filename"]

def update_profile(profile_name, max_hr=None, max_prework_hr=None, sex=None, birth_date=None, weight_kg=None, weight_unit_pref=None, auto_connect_hr=None):
    """Updates existing profile metadata."""
    profiles_file = get_profiles_file()
    if not os.path.exists(profiles_file):
        return
        
    try:
        with open(profiles_file, 'r') as f:
            data = json.load(f)
            
        if profile_name in data["profiles"]:
            # Update fields if provided
            if max_hr is not None:
                data["profiles"][profile_name]["max_hr"] = max_hr
            if max_prework_hr is not None:
                data["profiles"][profile_name]["max_prework_hr"] = max_prework_hr
            if sex is not None:
                data["profiles"][profile_name]["sex"] = sex
            if birth_date is not None:
                data["profiles"][profile_name]["birth_date"] = birth_date
            if weight_kg is not None:
                data["profiles"][profile_name]["weight_kg"] = weight_kg
            if weight_unit_pref is not None:
                data["profiles"][profile_name]["weight_unit_pref"] = weight_unit_pref
            if auto_connect_hr is not None:
                data["profiles"][profile_name]["auto_connect_hr"] = auto_connect_hr
                
            with open(profiles_file, 'w') as f:
                json.dump(data, f, indent=4)
                print(f"Updated profile {profile_name}: max_hr={max_hr}, max_prework_hr={max_prework_hr}")
                
    except Exception as e:
        print(f"Error updating profile: {e}")

def get_profile_details(profile_name):
    """Returns dict of profile metadata or empty dict."""
    profiles_file = get_profiles_file()
    if not os.path.exists(profiles_file):
        return {}
        
    try:
        with open(profiles_file, 'r') as f:
            data = json.load(f)
            return data.get("profiles", {}).get(profile_name, {})
    except Exception:
        return {}

def get_last_used_profile():
    profiles_file = get_profiles_file()
    if os.path.exists(profiles_file):
            try:
                with open(profiles_file, 'r') as f:
                    data = json.load(f)
                    return data.get("last_used_profile", "Default")
            except:
                pass
    return "Default"

def update_last_used_profile(profile_name):
    profiles_file = get_profiles_file()
    if os.path.exists(profiles_file):
            try:
                with open(profiles_file, 'r') as f:
                    data = json.load(f)
                
                data["last_used_profile"] = profile_name
                
                with open(profiles_file, 'w') as f:
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
                writer.writerow(["start_time", "end_time", "rounds", "work_duration", "rest_duration", "total_time", "notes", "workout_details_file"])
            writer.writerow(row)
    except IOError as e:
        print(f"Error saving to CSV: {e}")

def get_timezone_str():
    try:
        return time.strftime("%Z")
    except:
        return datetime.datetime.now().astimezone().tzname()

def get_next_workout_number(profile_name, date_str, timezone_str):
    safe_profile = profile_name.lower().replace(" ", "_").replace(".", "")
    base_pattern = f"{safe_profile}_{date_str}_{timezone_str}_WO"
    
    # List files matching the pattern
    pattern = os.path.join(get_base_dir(), f"{base_pattern}*.json")
    files = glob.glob(pattern)
    
    max_num = 0
    for f in files:
        basename = os.path.basename(f)
        # Extract number part: ..._WO1.json -> 1
        try:
            # Remove extension
            name_no_ext = os.path.splitext(basename)[0]
            # Split by _WO
            parts = name_no_ext.split("_WO")
            if len(parts) > 1:
                num_part = parts[-1]
                num = int(num_part)
                if num > max_num:
                    max_num = num
        except:
            pass
            
    return max_num + 1

def save_workout_json(data, profile_name="Default"):
    _ensure_dir()
    
    # 1. Prepare Filename Components
    safe_profile = profile_name.lower().replace(" ", "_").replace(".", "")
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    timezone_str = get_timezone_str()
    
    # 2. Get Next Number
    wo_num = get_next_workout_number(profile_name, date_str, timezone_str)
    
    filename = f"{safe_profile}_{date_str}_{timezone_str}_WO{wo_num}.json"
    filepath = os.path.join(get_base_dir(), filename)
    
    # 3. Save
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Saved JSON workout to {filepath}")
        return filename
    except Exception as e:
        print(f"Error saving JSON workout: {e}")
        return ""

def load_workout_details_json(filename):
    if not filename: return {}
    filepath = os.path.join(get_base_dir(), filename)
    if not os.path.exists(filepath):
        return {}
    
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading details {filename}: {e}")
        return {}

def load_history(profile_name="Default"):
    filename = get_filename(profile_name)
    history = []
    if not os.path.exists(filename):
        return history
        
    try:
        with open(filename, mode='r') as file:
            reader = csv.reader(file)
            # Do not skip header, UI expects it
            for row in reader:
                history.append(row)
    except IOError as e:
        print(f"Error loading CSV: {e}")
        
    return history

def save_template(profile_name, template_name, rounds, work_time, rest_time, notes):
    profiles_file = get_profiles_file()
    if not os.path.exists(profiles_file):
        return
        
    try:
        with open(profiles_file, 'r') as f:
            data = json.load(f)
            
        if profile_name in data["profiles"]:
            profile = data["profiles"][profile_name]
            if "templates" not in profile:
                profile["templates"] = {}
                
            profile["templates"][template_name] = {
                "rounds": rounds,
                "work_time": work_time,
                "rest_time": rest_time,
                "notes": notes
            }
            
            with open(profiles_file, 'w') as f:
                json.dump(data, f, indent=4)
                print(f"Saved template '{template_name}' for profile {profile_name}")
                
    except Exception as e:
        print(f"Error saving template: {e}")

def delete_template(profile_name, template_name):
    profiles_file = get_profiles_file()
    if not os.path.exists(profiles_file):
        return
        
    try:
        with open(profiles_file, 'r') as f:
            data = json.load(f)
            
        if profile_name in data["profiles"]:
            profile = data["profiles"][profile_name]
            if "templates" in profile and template_name in profile["templates"]:
                del profile["templates"][template_name]
                
                with open(profiles_file, 'w') as f:
                    json.dump(data, f, indent=4)
                    print(f"Deleted template '{template_name}' for profile {profile_name}")
                    
    except Exception as e:
        print(f"Error deleting template: {e}")

def get_templates(profile_name):
    profiles_file = get_profiles_file()
    if not os.path.exists(profiles_file):
        return {}
        
    try:
        with open(profiles_file, 'r') as f:
            data = json.load(f)
            return data.get("profiles", {}).get(profile_name, {}).get("templates", {})
    except Exception as e:
        print(f"Error getting templates: {e}")
        return {}
