import os
import sqlite3
import firebase_admin
from firebase_admin import credentials, firestore
import storage

def run_sync():
    """Runs a bidirectional sync between local SQLite and Cloud Firestore."""
    db_path = storage.get_db_file()
    
    # 1. Look for service-account.json in base dir or current directory
    service_file = None
    candidates = [
        os.path.join(storage.get_base_dir(), "service-account.json"),
        os.path.join(os.getcwd(), "service-account.json"),
        os.path.expanduser("~/Documents/EMOM Timer/service-account.json"),
        os.path.expanduser("~/.emom_timer_service_account.json")
    ]
    for c in candidates:
        if os.path.exists(c):
            service_file = c
            break
            
    if not service_file:
        print("SyncClient: service-account.json not found. Cloud sync skipped (offline mode).")
        return False
        
    print(f"SyncClient: Found credentials at {service_file}. Initializing sync...")
    
    try:
        # 2. Initialize Firebase Admin SDK
        if not firebase_admin._apps:
            cred = credentials.Certificate(service_file)
            firebase_admin.initialize_app(cred)
        
        db_firestore = firestore.client()
        
        # Connect to local SQLite
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # ----------------------------------------------------
        # A. SYNC PROFILES
        # ----------------------------------------------------
        c.execute("SELECT * FROM profiles")
        local_profiles = [dict(row) for row in c.fetchall()]
        
        # Upload local to Firestore
        for lp in local_profiles:
            doc_ref = db_firestore.collection("profiles").document(lp["name"])
            doc_ref.set({
                "name": lp["name"],
                "created_at": lp["created_at"],
                "max_hr": lp["max_hr"],
                "max_prework_hr": lp["max_prework_hr"],
                "sex": lp["sex"],
                "birth_date": lp["birth_date"],
                "weight_kg": lp["weight_kg"],
                "weight_unit_pref": lp["weight_unit_pref"],
                "auto_connect_hr": lp["auto_connect_hr"],
                "save_history": lp.get("save_history", 1)
            }, merge=True)
            
        # Download remote from Firestore
        remote_profiles = db_firestore.collection("profiles").get()
        for doc in remote_profiles:
            p_name = doc.id
            data = doc.to_dict()
            c.execute("SELECT name FROM profiles WHERE name = ?", (p_name,))
            if not c.fetchone():
                print(f"SyncClient: Downloading profile '{p_name}'...")
                c.execute("""
                INSERT INTO profiles (name, created_at, max_hr, max_prework_hr, sex, birth_date, weight_kg, weight_unit_pref, auto_connect_hr, save_history)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p_name,
                    data.get("created_at"),
                    data.get("max_hr"),
                    data.get("max_prework_hr"),
                    data.get("sex"),
                    data.get("birth_date"),
                    data.get("weight_kg"),
                    data.get("weight_unit_pref"),
                    data.get("auto_connect_hr"),
                    data.get("save_history", 1)
                ))
            else:
                # Update settings locally in case they changed on iPad
                c.execute("""
                UPDATE profiles SET 
                    max_hr = ?, max_prework_hr = ?, sex = ?, birth_date = ?, weight_kg = ?, weight_unit_pref = ?, auto_connect_hr = ?, save_history = ?
                WHERE name = ?
                """, (
                    data.get("max_hr"),
                    data.get("max_prework_hr"),
                    data.get("sex"),
                    data.get("birth_date"),
                    data.get("weight_kg"),
                    data.get("weight_unit_pref"),
                    data.get("auto_connect_hr"),
                    data.get("save_history", 1),
                    p_name
                ))
        conn.commit()

        # ----------------------------------------------------
        # B. SYNC WORKOUT TEMPLATES
        # ----------------------------------------------------
        c.execute("SELECT * FROM workout_templates")
        local_templates = [dict(row) for row in c.fetchall()]
        
        # Upload local templates to Firestore
        for lt in local_templates:
            doc_id = f"{lt['profile_name']}_{lt['template_name']}"
            doc_ref = db_firestore.collection("templates").document(doc_id)
            doc_ref.set({
                "profile_name": lt["profile_name"],
                "template_name": lt["template_name"],
                "rounds": lt["rounds"],
                "work_time": lt["work_time"],
                "rest_time": lt["rest_time"],
                "notes": lt["notes"]
            }, merge=True)
            
        # Download remote templates from Firestore
        remote_templates = db_firestore.collection("templates").get()
        for doc in remote_templates:
            data = doc.to_dict()
            p_name = data.get("profile_name")
            t_name = data.get("template_name")
            c.execute("SELECT id FROM workout_templates WHERE profile_name = ? AND template_name = ?", (p_name, t_name))
            if not c.fetchone():
                print(f"SyncClient: Downloading template '{t_name}' for profile '{p_name}'...")
                c.execute("""
                INSERT INTO workout_templates (profile_name, template_name, rounds, work_time, rest_time, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    p_name,
                    t_name,
                    data.get("rounds"),
                    data.get("work_time"),
                    data.get("rest_time"),
                    data.get("notes")
                ))
            else:
                c.execute("""
                UPDATE workout_templates SET 
                    rounds = ?, work_time = ?, rest_time = ?, notes = ?
                WHERE profile_name = ? AND template_name = ?
                """, (
                    data.get("rounds"),
                    data.get("work_time"),
                    data.get("rest_time"),
                    data.get("notes"),
                    p_name,
                    t_name
                ))
        conn.commit()

        # ----------------------------------------------------
        # C. SYNC WORKOUTS & HEART RATE LOGS
        # ----------------------------------------------------
        c.execute("SELECT * FROM workouts")
        local_workouts = [dict(row) for row in c.fetchall()]
        
        remote_workouts = db_firestore.collection("workouts").get()
        remote_workouts_map = {doc.id: doc.to_dict() for doc in remote_workouts}
        remote_doc_ids = set(remote_workouts_map.keys())
        
        # Upload local workouts that are missing in Firestore or have updated notes
        for w in local_workouts:
            p_name = w["profile_name"]
            s_time = w["start_time"]
            doc_id = f"{p_name}_{s_time}"
            
            if doc_id not in remote_doc_ids:
                print(f"SyncClient: Uploading workout {doc_id}...")
                c.execute("SELECT capture_time, bpm, zone FROM heart_rate_logs WHERE workout_id = ? ORDER BY id ASC", (w["id"],))
                hr_logs = [dict(row) for row in c.fetchall()]
                
                doc_ref = db_firestore.collection("workouts").document(doc_id)
                doc_ref.set({
                    "profile_name": p_name,
                    "start_time": s_time,
                    "end_time": w["end_time"],
                    "total_rounds_completed": w["total_rounds_completed"],
                    "work_duration": w["work_duration"],
                    "rest_duration": w["rest_duration"],
                    "total_time_sec": w["total_time_sec"],
                    "work_time_sec": w["work_time_sec"],
                    "rest_time_sec": w["rest_time_sec"],
                    "max_hr": w["max_hr"],
                    "avg_hr": w["avg_hr"],
                    "calories_burnt_kcal": w["calories_burnt_kcal"],
                    "notes": w["notes"],
                    "hr_details": hr_logs
                })
                remote_doc_ids.add(doc_id)
                remote_workouts_map[doc_id] = {"profile_name": p_name, "start_time": s_time, "notes": w["notes"]}
            else:
                remote_data = remote_workouts_map.get(doc_id)
                if remote_data:
                    remote_notes = remote_data.get("notes") or ""
                    local_notes = w["notes"] or ""
                    if local_notes != remote_notes and local_notes:
                        print(f"SyncClient: Updating remote workout notes for {doc_id}...")
                        doc_ref = db_firestore.collection("workouts").document(doc_id)
                        doc_ref.update({"notes": local_notes})
                        remote_data["notes"] = local_notes
                
        # Download remote workouts that are missing locally or have updated notes
        for doc_id, data in remote_workouts_map.items():
            p_name = data.get("profile_name")
            s_time = data.get("start_time")
            
            c.execute("SELECT id, notes FROM workouts WHERE profile_name = ? AND start_time = ?", (p_name, s_time))
            local_row = c.fetchone()
            if not local_row:
                print(f"SyncClient: Downloading workout {doc_id}...")
                c.execute("""
                INSERT INTO workouts (
                    profile_name, start_time, end_time, total_rounds_completed, 
                    work_duration, rest_duration, total_time_sec, work_time_sec, 
                    rest_time_sec, max_hr, avg_hr, calories_burnt_kcal, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p_name,
                    s_time,
                    data.get("end_time"),
                    data.get("total_rounds_completed"),
                    data.get("work_duration"),
                    data.get("rest_duration"),
                    data.get("total_time_sec"),
                    data.get("work_time_sec"),
                    data.get("rest_time_sec"),
                    data.get("max_hr"),
                    data.get("avg_hr"),
                    data.get("calories_burnt_kcal"),
                    data.get("notes")
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
            else:
                local_notes = local_row["notes"] or ""
                remote_notes = data.get("notes") or ""
                if local_notes != remote_notes and not local_notes and remote_notes:
                    print(f"SyncClient: Downloading updated notes for {doc_id}...")
                    c.execute("UPDATE workouts SET notes = ? WHERE id = ?", (remote_notes, local_row["id"]))
        conn.commit()
        conn.close()
        print("SyncClient: Database sync completed successfully.")
        return True
    except Exception as e:
        print(f"SyncClient: Sync failed with error: {e}")
        return False

if __name__ == "__main__":
    run_sync()
