import csv
import os
import glob
import sys
import json
import datetime
import time
import sqlite3

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

# Module level exports for compatibility
PROFILES_FILE = os.path.join(get_base_dir(), "profiles.json")

def get_profiles_file():
    return os.path.join(get_base_dir(), "profiles.json")

def get_db_file():
    return os.path.join(get_base_dir(), "emom_timer.db")

def _ensure_dir():
    base = get_base_dir()
    if not os.path.exists(base):
        os.makedirs(base)

# Database initialization
_DB_INITIALIZED = False

def get_db_connection():
    global _DB_INITIALIZED
    db_file = get_db_file()
    _ensure_dir()
    conn = sqlite3.connect(db_file)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    
    if not _DB_INITIALIZED:
        _DB_INITIALIZED = True
        _init_db_with_connection(conn)
        
    return conn

def _init_db_with_connection(conn):
    try:
        cursor = conn.cursor()
        
        # 1. profiles table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            name TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            max_hr INTEGER,
            max_prework_hr INTEGER,
            sex TEXT,
            birth_date TEXT,
            weight_kg REAL,
            weight_unit_pref TEXT,
            auto_connect_hr INTEGER
        )
        """)
        
        # 2. workout_templates table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_name TEXT,
            template_name TEXT,
            rounds INTEGER,
            work_time INTEGER,
            rest_time INTEGER,
            notes TEXT,
            FOREIGN KEY(profile_name) REFERENCES profiles(name) ON DELETE CASCADE,
            UNIQUE(profile_name, template_name)
        )
        """)
        
        # 3. workouts table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_name TEXT,
            start_time TEXT NOT NULL,
            end_time TEXT,
            total_rounds_completed INTEGER,
            work_duration INTEGER,
            rest_duration INTEGER,
            total_time_sec INTEGER,
            work_time_sec INTEGER,
            rest_time_sec INTEGER,
            max_hr INTEGER,
            avg_hr INTEGER,
            calories_burnt_kcal REAL,
            notes TEXT,
            details_file_legacy TEXT,
            FOREIGN KEY(profile_name) REFERENCES profiles(name) ON DELETE CASCADE
        )
        """)
        
        # Indices for speed
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workouts_start_time ON workouts(start_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workouts_profile_name ON workouts(profile_name)")
        
        # 4. heart_rate_logs table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS heart_rate_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER,
            capture_time TEXT,
            bpm INTEGER,
            zone TEXT,
            FOREIGN KEY(workout_id) REFERENCES workouts(id) ON DELETE CASCADE
        )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hr_logs_workout_id ON heart_rate_logs(workout_id)")
        
        conn.commit()
    except Exception as e:
        print(f"Error initializing database tables: {e}")

def load_profiles():
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT name FROM profiles ORDER BY name")
        names = [row["name"] for row in c.fetchall()]
        if not names:
            # Auto-create Default profile if DB is brand new
            conn.close()
            add_profile("Default")
            return ["Default"]
        return names
    except Exception as e:
        print(f"Error loading profiles from DB: {e}")
        return ["Default"]
    finally:
        try: conn.close()
        except: pass

def add_profile(profile_name, max_hr=None, max_prework_hr=None, sex=None, birth_date=None, weight_kg=None, weight_unit_pref="kg", auto_connect_hr=True):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT name FROM profiles WHERE name = ?", (profile_name,))
        if not c.fetchone():
            c.execute("""
            INSERT INTO profiles (name, created_at, max_hr, max_prework_hr, sex, birth_date, weight_kg, weight_unit_pref, auto_connect_hr)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (profile_name, datetime.datetime.now().isoformat(), max_hr, max_prework_hr, sex, birth_date, weight_kg, weight_unit_pref, 1 if auto_connect_hr else 0))
            conn.commit()
            print(f"Profile {profile_name} created in database.")
    except Exception as e:
        print(f"Error adding profile to DB: {e}")
    finally:
        conn.close()
        
    return f"{profile_name.lower().replace(' ', '_')}_workout_history.csv"

def update_profile(profile_name, max_hr=None, max_prework_hr=None, sex=None, birth_date=None, weight_kg=None, weight_unit_pref=None, auto_connect_hr=None):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        updates = []
        params = []
        if max_hr is not None:
            updates.append("max_hr = ?")
            params.append(max_hr)
        if max_prework_hr is not None:
            updates.append("max_prework_hr = ?")
            params.append(max_prework_hr)
        if sex is not None:
            updates.append("sex = ?")
            params.append(sex)
        if birth_date is not None:
            updates.append("birth_date = ?")
            params.append(birth_date)
        if weight_kg is not None:
            updates.append("weight_kg = ?")
            params.append(weight_kg)
        if weight_unit_pref is not None:
            updates.append("weight_unit_pref = ?")
            params.append(weight_unit_pref)
        if auto_connect_hr is not None:
            updates.append("auto_connect_hr = ?")
            params.append(1 if auto_connect_hr else 0)
            
        if updates:
            params.append(profile_name)
            query = f"UPDATE profiles SET {', '.join(updates)} WHERE name = ?"
            c.execute(query, params)
            conn.commit()
            print(f"Updated profile {profile_name} details in DB.")
    except Exception as e:
        print(f"Error updating profile in DB: {e}")
    finally:
        conn.close()

def get_profile_details(profile_name):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM profiles WHERE name = ?", (profile_name,))
        row = c.fetchone()
        if row:
            d = dict(row)
            d["auto_connect_hr"] = bool(d["auto_connect_hr"])
            # Ensure keys exist
            d.setdefault("max_hr", None)
            d.setdefault("max_prework_hr", None)
            d.setdefault("sex", None)
            d.setdefault("birth_date", None)
            d.setdefault("weight_kg", None)
            d.setdefault("weight_unit_pref", "kg")
            return d
        return {}
    except Exception as e:
        print(f"Error getting profile details from DB: {e}")
        return {}
    finally:
        conn.close()

def get_last_used_profile():
    try:
        if os.path.exists(_CONFIG_FILE):
            with open(_CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get("last_used_profile", "Default")
    except Exception as e:
        print(f"Error reading config for last profile: {e}")
    return "Default"

def update_last_used_profile(profile_name):
    try:
        config = {}
        if os.path.exists(_CONFIG_FILE):
             with open(_CONFIG_FILE, 'r') as f:
                 config = json.load(f)
        
        config["last_used_profile"] = profile_name
        
        with open(_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving config for last profile: {e}")

def get_available_profiles():
    return load_profiles()

def save_workout_to_db(profile_name, data, work_duration, rest_duration):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("""
        INSERT INTO workouts (
            profile_name, start_time, end_time, total_rounds_completed, 
            work_duration, rest_duration, total_time_sec, work_time_sec, 
            rest_time_sec, max_hr, avg_hr, calories_burnt_kcal, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile_name,
            data.get("start_time"),
            data.get("end_time"),
            data.get("total_rounds_completed"),
            work_duration,
            rest_duration,
            data.get("total_time_sec"),
            data.get("work_time_sec"),
            data.get("rest_time_sec"),
            data.get("max_hr"),
            data.get("avg_hr"),
            data.get("calories_burnt_kcal"),
            data.get("workout_notes")
        ))
        workout_id = c.lastrowid
        
        hr_details = data.get("hr_details", [])
        for log in hr_details:
            c.execute("""
            INSERT INTO heart_rate_logs (workout_id, capture_time, bpm, zone)
            VALUES (?, ?, ?, ?)
            """, (
                workout_id,
                log.get("capture_time"),
                log.get("bpm"),
                log.get("zone")
            ))
        conn.commit()
        print(f"Workout saved to DB under ID: {workout_id}")
        return workout_id
    except Exception as e:
        print(f"Error saving workout to DB: {e}")
        return None
    finally:
        conn.close()

# Kept for backward compatibility / emergency fallbacks
def save_workout(row, profile_name="Default"):
    print("Warning: save_workout is obsolete. Use save_workout_to_db.")
    pass

def save_workout_json(data, profile_name="Default"):
    print("Warning: save_workout_json is obsolete. Use save_workout_to_db.")
    return ""

def load_workout_details_json(identifier):
    if not identifier: return {}
    
    # Check if this is a legacy JSON filename
    if str(identifier).endswith(".json"):
        filepath = os.path.join(get_base_dir(), str(identifier))
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading legacy details file {identifier}: {e}")
        return {}
        
    # Otherwise, query SQLite
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM workouts WHERE id = ?", (identifier,))
        w_row = c.fetchone()
        if not w_row:
            return {}
            
        workout = dict(w_row)
        
        c.execute("SELECT capture_time, bpm, zone FROM heart_rate_logs WHERE workout_id = ? ORDER BY id ASC", (identifier,))
        logs = [dict(log) for log in c.fetchall()]
        
        data = {
            "profile_name": workout["profile_name"],
            "start_time": workout["start_time"],
            "end_time": workout["end_time"],
            "total_rounds_completed": workout["total_rounds_completed"],
            "work_time_sec": workout["work_time_sec"],
            "rest_time_sec": workout["rest_time_sec"],
            "total_time_sec": workout["total_time_sec"],
            "workout_notes": workout["notes"] or "",
            "hr_details": logs,
            "max_hr": workout["max_hr"],
            "avg_hr": workout["avg_hr"],
            "calories_burnt_kcal": workout["calories_burnt_kcal"]
        }
        return data
    except Exception as e:
        print(f"Error loading workout details from DB: {e}")
        return {}
    finally:
        conn.close()

def load_history(profile_name="Default"):
    conn = get_db_connection()
    history = [["start_time", "end_time", "rounds", "work_duration", "rest_duration", "total_time", "notes", "workout_details_file"]]
    try:
        c = conn.cursor()
        c.execute("""
        SELECT id, start_time, end_time, total_rounds_completed, work_duration, rest_duration, total_time_sec, notes 
        FROM workouts 
        WHERE profile_name = ? 
        ORDER BY start_time DESC
        """, (profile_name,))
        rows = c.fetchall()
        for row in rows:
            history.append([
                row["start_time"],
                row["end_time"],
                str(row["total_rounds_completed"]),
                str(row["work_duration"]),
                str(row["rest_duration"]),
                str(row["total_time_sec"]),
                row["notes"] or "",
                str(row["id"]) # Pass DB ID to history UI callback
            ])
    except Exception as e:
        print(f"Error loading history from DB: {e}")
    finally:
        conn.close()
    return history

def get_workouts_for_day(profile_name, start_time_str):
    if not start_time_str: return []
    
    # Parse date portion
    try:
        dt = datetime.datetime.fromisoformat(start_time_str)
        date_str = dt.date().isoformat()
    except Exception:
        date_str = start_time_str[:10]
        
    conn = get_db_connection()
    day_workouts = []
    try:
        c = conn.cursor()
        c.execute("""
        SELECT id FROM workouts 
        WHERE profile_name = ? AND date(start_time) = date(?) 
        ORDER BY start_time ASC
        """, (profile_name, date_str))
        rows = c.fetchall()
        for row in rows:
            w_details = load_workout_details_json(row["id"])
            if w_details:
                day_workouts.append(w_details)
    except Exception as e:
        print(f"Error getting day workouts from DB: {e}")
    finally:
        conn.close()
    return day_workouts

def save_template(profile_name, template_name, rounds, work_time, rest_time, notes):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        # Verify profile exists
        c.execute("SELECT name FROM profiles WHERE name = ?", (profile_name,))
        if not c.fetchone():
            return
            
        c.execute("""
        INSERT OR REPLACE INTO workout_templates (profile_name, template_name, rounds, work_time, rest_time, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (profile_name, template_name, rounds, work_time, rest_time, notes))
        conn.commit()
        print(f"Saved template '{template_name}' for profile {profile_name} in DB.")
    except Exception as e:
        print(f"Error saving template to DB: {e}")
    finally:
        conn.close()

def delete_template(profile_name, template_name):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("""
        DELETE FROM workout_templates WHERE profile_name = ? AND template_name = ?
        """, (profile_name, template_name))
        conn.commit()
        print(f"Deleted template '{template_name}' for profile {profile_name} from DB.")
    except Exception as e:
        print(f"Error deleting template from DB: {e}")
    finally:
        conn.close()

def get_templates(profile_name):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("""
        SELECT template_name, rounds, work_time, rest_time, notes 
        FROM workout_templates 
        WHERE profile_name = ?
        """, (profile_name,))
        rows = c.fetchall()
        templates = {}
        for row in rows:
            templates[row["template_name"]] = {
                "rounds": row["rounds"],
                "work_time": row["work_time"],
                "rest_time": row["rest_time"],
                "notes": row["notes"]
            }
        return templates
    except Exception as e:
        print(f"Error getting templates from DB: {e}")
        return {}
    finally:
        conn.close()

def export_to_csv(profile_name, destination_path):
    history = load_history(profile_name)
    if not history or len(history) <= 1:
        return False
    try:
        with open(destination_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            # Write rows, but slice each row to exclude the last column (the database workout_id)
            for row in history:
                writer.writerow(row[:-1])
        return True
    except Exception as e:
        print(f"Error exporting CSV: {e}")
        return False
