import os
import shutil
import tempfile
import sqlite3
import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# ----------------------------------------------------
# 1. ISOLATE DATABASE & BASE DIR (MONKEY PATCH)
# ----------------------------------------------------
# Create a temporary directory for the test database
test_dir = tempfile.mkdtemp()
test_db = os.path.join(test_dir, "emom_timer.db")

print("--------------------------------------------------")
print(f"Setting up isolated test environment in {test_dir}...")
print("--------------------------------------------------")

import storage
# Override storage methods so we don't touch production data
storage.get_db_file = lambda: test_db
storage.get_base_dir = lambda: test_dir

import sync_client

# ----------------------------------------------------
# 2. RUN TEST SUITE
# ----------------------------------------------------
def run_integration_test():
    # Find service account file
    service_file = None
    candidates = [
        os.path.join(os.path.expanduser("~/Documents/EMOM Timer"), "service-account.json"),
        os.path.join(os.getcwd(), "service-account.json"),
        os.path.expanduser("~/.emom_timer_service_account.json"),
        os.path.join(test_dir, "service-account.json")
    ]
    for c in candidates:
        if os.path.exists(c):
            service_file = c
            break
            
    if not service_file:
        print("\n[SKIP] Test skipped because service-account.json was not found.")
        print("Please download your Firebase service-account.json and place it at:")
        print(f"  ~/Documents/EMOM Timer/service-account.json")
        return

    # Copy the credential file to our temp test directory so sync_client can find it
    shutil.copy(service_file, os.path.join(test_dir, "service-account.json"))

    # Initialize SQLite database structure
    conn = storage.get_db_connection()
    c = conn.cursor()
    
    # Define test data
    test_profile = "Test Sync User"
    test_start_time = "2026-06-19 12:00:00"
    test_end_time = "2026-06-19 12:15:00"
    
    print("\n1. Inserting mock local data into SQLite...")
    # Insert a test profile
    c.execute("""
    INSERT OR REPLACE INTO profiles (name, created_at, max_hr, max_prework_hr, sex, birth_date, weight_kg, weight_unit_pref, auto_connect_hr)
    VALUES (?, ?, 180, 130, 'Male', '1990-01-01', 75.0, 'kg', 1)
    """, (test_profile, datetime.datetime.now().isoformat()))
    
    # Insert a test template
    c.execute("""
    INSERT OR REPLACE INTO workout_templates (profile_name, template_name, rounds, work_time, rest_time, notes)
    VALUES (?, 'Test Template', 10, 45, 15, 'Test template notes')
    """, (test_profile,))
    
    # Insert a test workout
    c.execute("""
    INSERT INTO workouts (
        profile_name, start_time, end_time, total_rounds_completed, 
        work_duration, rest_duration, total_time_sec, work_time_sec, 
        rest_time_sec, max_hr, avg_hr, calories_burnt_kcal, notes
    ) VALUES (?, ?, ?, 10, 45, 15, 600, 450, 150, 175, 145, 120.5, 'Sync test workout notes')
    """, (test_profile, test_start_time, test_end_time))
    workout_id = c.lastrowid
    
    # Insert test heart rate logs
    c.execute("""
    INSERT INTO heart_rate_logs (workout_id, capture_time, bpm, zone)
    VALUES (?, '2026-06-19 12:01:00', 140, 'ZONE 2')
    """, (workout_id,))
    c.execute("""
    INSERT INTO heart_rate_logs (workout_id, capture_time, bpm, zone)
    VALUES (?, '2026-06-19 12:02:00', 160, 'ZONE 4')
    """, (workout_id,))
    
    conn.commit()
    conn.close()
    print("✓ Local test data inserted into SQLite.")

    # Run the sync client to upload the data to Firestore
    print("\n2. Running sync client (upload phase)...")
    sync_success = sync_client.run_sync()
    assert sync_success, "Sync client failed to run successfully."
    print("✓ Sync client completed successfully.")

    # Initialize Firestore client directly to verify data was uploaded
    if not firebase_admin._apps:
        cred = credentials.Certificate(service_file)
        firebase_admin.initialize_app(cred)
    db_firestore = firestore.client()

    print("\n3. Verifying records exist in Cloud Firestore...")
    
    profile_ref = db_firestore.collection("profiles").document(test_profile)
    assert profile_ref.get().exists, "Profile was not uploaded to Firestore."
    print("✓ Profile exists in Firestore.")
    
    template_ref = db_firestore.collection("templates").document(f"{test_profile}_Test Template")
    assert template_ref.get().exists, "Template was not uploaded to Firestore."
    print("✓ Template exists in Firestore.")
    
    workout_doc_id = f"{test_profile}_{test_start_time}"
    workout_ref = db_firestore.collection("workouts").document(workout_doc_id)
    workout_snap = workout_ref.get()
    assert workout_snap.exists, "Workout was not uploaded to Firestore."
    
    workout_data = workout_snap.to_dict()
    assert workout_data["avg_hr"] == 145, "Workout data in Firestore is incorrect."
    assert len(workout_data["hr_details"]) == 2, "Heart rate details were not uploaded correctly."
    print("✓ Workout and heart rate logs exist in Firestore.")

    print("\n4. Wiping local SQLite database to test download/restore...")
    # Delete the SQLite file completely
    if os.path.exists(test_db):
        os.remove(test_db)
    
    # Reinitialize an empty SQLite database structure
    storage._DB_INITIALIZED = False
    conn = storage.get_db_connection()
    c = conn.cursor()
    # Confirm it is empty
    c.execute("SELECT COUNT(*) FROM workouts")
    assert c.fetchone()[0] == 0, "Failed to clean SQLite database."
    conn.close()
    print("✓ Local database wiped successfully.")

    # Run the sync client again to download the data back
    print("\n5. Running sync client (download/restore phase)...")
    sync_success = sync_client.run_sync()
    assert sync_success, "Sync client failed to restore database."
    print("✓ Sync client completed successfully.")

    # Verify SQLite database contains the downloaded data
    print("\n6. Verifying restored records in SQLite...")
    conn = sqlite3.connect(test_db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM profiles WHERE name = ?", (test_profile,))
    profile_row = c.fetchone()
    assert profile_row is not None, "Profile was not restored to SQLite."
    assert profile_row["max_hr"] == 180, "Restored profile details are incorrect."
    print("✓ Profile restored successfully.")
    
    c.execute("SELECT * FROM workout_templates WHERE profile_name = ?", (test_profile,))
    template_row = c.fetchone()
    assert template_row is not None, "Template was not restored to SQLite."
    assert template_row["template_name"] == "Test Template", "Restored template details are incorrect."
    print("✓ Template restored successfully.")
    
    c.execute("SELECT * FROM workouts WHERE profile_name = ?", (test_profile,))
    workout_row = c.fetchone()
    assert workout_row is not None, "Workout was not restored to SQLite."
    assert workout_row["avg_hr"] == 145, "Restored workout details are incorrect."
    
    c.execute("SELECT * FROM heart_rate_logs WHERE workout_id = ? ORDER BY id ASC", (workout_row["id"],))
    hr_rows = c.fetchall()
    assert len(hr_rows) == 2, "Heart rate logs were not restored."
    assert hr_rows[1]["bpm"] == 160, "Restored heart rate details are incorrect."
    print("✓ Workout and heart rate logs restored successfully.")
    
    # Clean up remote test records in Firestore so we don't leave dummy data
    print("\n7. Cleaning up Firestore test documents...")
    profile_ref.delete()
    template_ref.delete()
    workout_ref.delete()
    print("✓ Firestore test documents deleted.")
    
    conn.close()
    print("\n==================================================")
    print(" 🎉 ALL SYNC INTEGRATION TESTS PASSED SUCCESSFULLY! ")
    print("==================================================")

if __name__ == "__main__":
    try:
        run_integration_test()
    finally:
        # Clean up local temporary directories
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
