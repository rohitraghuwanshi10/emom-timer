import os
import csv
import json
import glob
import datetime
import sqlite3
import storage

def run_migration():
    print("==================================================")
    print("       EMOM TIMER SQLITE MIGRATION SCRIPT         ")
    print("==================================================")
    
    # 1. Initialize the SQLite database connection and tables
    print("Initializing SQLite database connection...")
    db_file = storage.get_db_file()
    print(f"Database File: {db_file}")
    
    conn = storage.get_db_connection()
    c = conn.cursor()
    
    # Check profiles.json
    profiles_json_file = storage.get_profiles_file()
    print(f"Checking for legacy profiles: {profiles_json_file}")
    
    # Track profiles we find to process
    profiles_to_migrate = {}
    last_used_profile = "Default"
    
    # Case A: profiles.json exists
    if os.path.exists(profiles_json_file):
        print("Found legacy profiles.json. Reading profiles...")
        try:
            with open(profiles_json_file, 'r') as f:
                data = json.load(f)
                profiles_to_migrate = data.get("profiles", {})
                last_used_profile = data.get("last_used_profile", "Default")
        except Exception as e:
            print(f"Error reading profiles.json: {e}")
    else:
        print("profiles.json not found. Scanning folder for CSV files...")
        
    # Case B: Check if there are orphaned CSV history files in the base directory
    base_dir = storage.get_base_dir()
    pattern = os.path.join(base_dir, "*_workout_history.csv")
    csv_files = glob.glob(pattern)
    
    for csv_file in csv_files:
        basename = os.path.basename(csv_file)
        if basename.endswith(".csv.bak"):
            continue
        raw_name = basename.replace("_workout_history.csv", "")
        pretty_name = raw_name.replace("_", " ").title()
        
        if pretty_name not in profiles_to_migrate:
            print(f"Found orphaned CSV history: {basename} -> Adding to migration list as '{pretty_name}'")
            profiles_to_migrate[pretty_name] = {
                "filename": basename,
                "created_at": datetime.datetime.now().isoformat(),
                "max_hr": None,
                "max_prework_hr": None
            }

    if not profiles_to_migrate:
        print("No profiles or workout history files found to migrate.")
        print("Creating default profile in database...")
        storage.add_profile("Default")
        print("Migration complete (fresh database created).")
        conn.close()
        return

    print(f"\nFound {len(profiles_to_migrate)} profile(s) to migrate.")
    
    # Set the last used profile in config
    storage.update_last_used_profile(last_used_profile)
    print(f"Set last used profile in config to: {last_used_profile}")

    for profile_name, p_data in profiles_to_migrate.items():
        print(f"\n--------------------------------------------------")
        print(f"Migrating Profile: '{profile_name}'")
        print(f"--------------------------------------------------")
        
        # 1. Insert Profile into profiles table
        max_hr = p_data.get("max_hr")
        max_prework_hr = p_data.get("max_prework_hr")
        sex = p_data.get("sex")
        birth_date = p_data.get("birth_date")
        weight_kg = p_data.get("weight_kg")
        weight_unit_pref = p_data.get("weight_unit_pref", "kg")
        auto_connect_hr = p_data.get("auto_connect_hr", True)
        created_at = p_data.get("created_at", datetime.datetime.now().isoformat())
        
        c.execute("SELECT name FROM profiles WHERE name = ?", (profile_name,))
        if not c.fetchone():
            c.execute("""
            INSERT INTO profiles (name, created_at, max_hr, max_prework_hr, sex, birth_date, weight_kg, weight_unit_pref, auto_connect_hr)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (profile_name, created_at, max_hr, max_prework_hr, sex, birth_date, weight_kg, weight_unit_pref, 1 if auto_connect_hr else 0))
            conn.commit()
            print(f"Added profile '{profile_name}' to DB.")
        else:
            print(f"Profile '{profile_name}' already exists in DB.")
            
        # 2. Migrate Workout Templates for this profile
        templates = p_data.get("templates", {})
        if templates:
            print(f"Found {len(templates)} templates. Migrating...")
            for t_name, t_data in templates.items():
                try:
                    c.execute("""
                    INSERT OR REPLACE INTO workout_templates (profile_name, template_name, rounds, work_time, rest_time, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (profile_name, t_name, t_data.get("rounds"), t_data.get("work_time"), t_data.get("rest_time"), t_data.get("notes", "")))
                    print(f"  -> Migrated Template: '{t_name}'")
                except Exception as e:
                    print(f"  -> Error migrating template '{t_name}': {e}")
            conn.commit()

        # 3. Migrate Workout History CSV
        csv_filename = p_data.get("filename")
        if not csv_filename:
            csv_filename = f"{profile_name.lower().replace(' ', '_')}_workout_history.csv"
            
        csv_path = os.path.join(base_dir, csv_filename)
        
        if os.path.exists(csv_path):
            print(f"Found CSV history file: {csv_filename}. Parsing...")
            workouts_migrated = 0
            
            try:
                with open(csv_path, mode='r') as file:
                    reader = csv.reader(file)
                    header = next(reader, None)
                    
                    if header:
                        # Find column indices
                        col_start = 0
                        col_end = 1
                        col_rounds = 2
                        col_work_dur = 3
                        col_rest_dur = 4
                        col_total_time = 5
                        col_notes = 6
                        col_det_file = 7
                        
                        # Dynamically find index if headers mismatched
                        try: col_start = header.index("start_time")
                        except: pass
                        try: col_end = header.index("end_time")
                        except: pass
                        try: col_rounds = header.index("rounds")
                        except:
                            try: col_rounds = header.index("total_rounds_completed")
                            except: pass
                        try: col_work_dur = header.index("work_duration")
                        except: pass
                        try: col_rest_dur = header.index("rest_duration")
                        except: pass
                        try: col_total_time = header.index("total_time")
                        except:
                            try: col_total_time = header.index("total_time_sec")
                            except: pass
                        try: col_notes = header.index("notes")
                        except:
                            try: col_notes = header.index("workout_notes")
                            except: pass
                        try: col_det_file = header.index("workout_details_file")
                        except:
                            try: col_det_file = header.index("Details File")
                            except: pass
                        
                        # Loop through rows
                        for row in reader:
                            if not row or len(row) < 2:
                                continue
                            
                            start_time = row[col_start]
                            end_time = row[col_end]
                            
                            # Check if already migrated to avoid duplicates
                            c.execute("SELECT id FROM workouts WHERE profile_name = ? AND start_time = ?", (profile_name, start_time))
                            if c.fetchone():
                                print(f"  -> Workout at {start_time} already exists in DB. Skipping.")
                                continue
                                
                            # Basic summary details from CSV
                            try: rounds_completed = int(row[col_rounds])
                            except: rounds_completed = 0
                            try: work_duration = int(row[col_work_dur])
                            except: work_duration = 0
                            try: rest_duration = int(row[col_rest_dur])
                            except: rest_duration = 0
                            try: total_time_sec = int(row[col_total_time])
                            except: total_time_sec = 0
                            notes = row[col_notes] if len(row) > col_notes else ""
                            
                            det_file = row[col_det_file] if len(row) > col_det_file else ""
                            
                            # Detailed metrics from JSON
                            work_time_sec = work_duration * rounds_completed
                            rest_time_sec = total_time_sec - work_time_sec
                            max_hr = 0
                            avg_hr = 0
                            calories_burnt = 0.0
                            hr_details = []
                            
                            json_parsed_successfully = False
                            
                            if det_file and det_file.endswith(".json"):
                                json_path = os.path.join(base_dir, det_file)
                                if os.path.exists(json_path):
                                    try:
                                        with open(json_path, 'r') as jf:
                                            j_data = json.load(jf)
                                            # Read detailed fields
                                            work_time_sec = j_data.get("work_time_sec", work_time_sec)
                                            rest_time_sec = j_data.get("rest_time_sec", rest_time_sec)
                                            total_time_sec = j_data.get("total_time_sec", total_time_sec)
                                            max_hr = j_data.get("max_hr", 0)
                                            avg_hr = j_data.get("avg_hr", 0)
                                            calories_burnt = j_data.get("calories_burnt_kcal", 0.0)
                                            hr_details = j_data.get("hr_details", [])
                                            notes = j_data.get("workout_notes", notes)
                                            json_parsed_successfully = True
                                    except Exception as e:
                                        print(f"  -> Error parsing JSON details {det_file}: {e}")
                                else:
                                    print(f"  -> JSON details file not found: {det_file}")
                            
                            # Insert into workouts table
                            c.execute("""
                            INSERT INTO workouts (
                                profile_name, start_time, end_time, total_rounds_completed, 
                                work_duration, rest_duration, total_time_sec, work_time_sec, 
                                rest_time_sec, max_hr, avg_hr, calories_burnt_kcal, notes, details_file_legacy
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                profile_name, start_time, end_time, rounds_completed, 
                                work_duration, rest_duration, total_time_sec, work_time_sec, 
                                rest_time_sec, max_hr, avg_hr, calories_burnt, notes, det_file
                            ))
                            
                            workout_id = c.lastrowid
                            workouts_migrated += 1
                            
                            # Insert heart rate logs if present
                            if hr_details:
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
                            
                            # Rename the detail JSON to JSON.bak
                            if json_parsed_successfully:
                                try:
                                    os.rename(json_path, json_path + ".bak")
                                except Exception as e:
                                    print(f"  -> Error renaming JSON details file {det_file}: {e}")
                                    
                print(f"Successfully migrated {workouts_migrated} workouts for '{profile_name}'.")
                
                # Rename the CSV to CSV.bak
                try:
                    os.rename(csv_path, csv_path + ".bak")
                    print(f"Renamed legacy CSV history to: {csv_filename}.bak")
                except Exception as e:
                    print(f"Error renaming CSV history file: {e}")
                    
            except Exception as e:
                print(f"Error migrating CSV history for '{profile_name}': {e}")
        else:
            print(f"No CSV history file found for '{profile_name}' (expected: {csv_filename}).")
            
    # Rename profiles.json to profiles.json.bak
    if os.path.exists(profiles_json_file):
        try:
            os.rename(profiles_json_file, profiles_json_file + ".bak")
            print("\nRenamed legacy profiles.json to: profiles.json.bak")
        except Exception as e:
            print(f"\nError renaming profiles.json: {e}")
            
    conn.close()
    print("\n==================================================")
    print(" MIGRATION COMPLETED SUCCESSFULLY!                ")
    print("==================================================")

if __name__ == "__main__":
    run_migration()
