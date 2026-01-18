import csv
import os
import glob
import sys
import json
import datetime
import time

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
    
    # Run Migration for new column (Before loading/returning)
    # 1. Add Details Column if missing
    migrate_csv_add_details_column()
    # 2. Standardize Headers (Rename old to new)
    migrate_csv_headers()
    
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

def migrate_csv_add_details_column():
    """Ensures all CSVs have the 'Details File' column."""
    pattern = os.path.join(DOCS_DIR, "*_workout_history.csv")
    files = glob.glob(pattern)
    
    for filename in files:
        try:
            rows = []
            with open(filename, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            if not rows: continue
            
            headers = rows[0]
            # Check for header. We use 'Details File' as pretty name
            if "Details File" not in headers and "workout_details_file" not in headers:
                # Add Header
                headers.append("workout_details_file")
                
                # Add empty column to rows that need it
                # Note: Some rows might already have it if app ran before migration
                target_len = len(headers)
                for i in range(1, len(rows)):
                    if len(rows[i]) < target_len:
                        rows[i].append("")
                
                # Write back
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(rows)
                print(f"Migrated CSV structure for {os.path.basename(filename)}")
        except Exception as e:
            print(f"Error migrating {filename}: {e}")

def migrate_csv_headers():
    """Renames old English headers to snake_case."""
    pattern = os.path.join(DOCS_DIR, "*_workout_history.csv")
    files = glob.glob(pattern)
    
    map_to_new = {
        "Start Time": "start_time",
        "End Time": "end_time",
        "Rounds": "rounds",
        "Work Duration": "work_duration",
        "Rest Duration": "rest_duration",
        "Total Time": "total_time",
        "Notes": "notes",
        "Details File": "workout_details_file" # Handle potential old name if exists
    }
    
    for filename in files:
        try:
            rows = []
            with open(filename, 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            if not rows: continue
            
            headers = rows[0]
            changed = False
            for i, h in enumerate(headers):
                if h in map_to_new:
                    headers[i] = map_to_new[h]
                    changed = True
            
            # If "Details File" was added by previous migration, it might be needing rename or not.
            # Just to be safe, previous step ensured 'workout_details_file' but if I used 'Details File' in verify...
            # The previous step used 'workout_details_file' in code, so headers should be fine if new.
            # But if old file had 'Start Time', we rename it.
            
            if changed:
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(rows)
                print(f"Standardized headers for {os.path.basename(filename)}")
                
        except Exception as e:
            print(f"Error standardizing headers for {filename}: {e}")

def add_profile(profile_name, max_hr=None, max_prework_hr=None, sex=None, birth_date=None, weight_kg=None, weight_unit_pref="kg"):
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
            "created_at": datetime.datetime.now().isoformat(),
            "max_hr": max_hr,
            "max_prework_hr": max_prework_hr,
            "sex": sex,
            "birth_date": birth_date,
            "weight_kg": weight_kg,
            "weight_unit_pref": weight_unit_pref
        }
        
        with open(PROFILES_FILE, 'w') as f:
            json.dump(data, f, indent=4)
            
    return data["profiles"][profile_name]["filename"]

def update_profile(profile_name, max_hr=None, max_prework_hr=None, sex=None, birth_date=None, weight_kg=None, weight_unit_pref=None):
    """Updates existing profile metadata."""
    if not os.path.exists(PROFILES_FILE):
        return
        
    try:
        with open(PROFILES_FILE, 'r') as f:
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
                
            with open(PROFILES_FILE, 'w') as f:
                json.dump(data, f, indent=4)
                print(f"Updated profile {profile_name}: max_hr={max_hr}, max_prework_hr={max_prework_hr}")
                
    except Exception as e:
        print(f"Error updating profile: {e}")

def get_profile_details(profile_name):
    """Returns dict of profile metadata or empty dict."""
    if not os.path.exists(PROFILES_FILE):
        return {}
        
    try:
        with open(PROFILES_FILE, 'r') as f:
            data = json.load(f)
            return data.get("profiles", {}).get(profile_name, {})
    except Exception:
        return {}

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
    pattern = os.path.join(DOCS_DIR, f"{base_pattern}*.json")
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
    filepath = os.path.join(DOCS_DIR, filename)
    
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
    filepath = os.path.join(DOCS_DIR, filename)
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
