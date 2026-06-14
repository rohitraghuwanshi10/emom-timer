import storage
import json
import os

def test_profile_fields():
    print("Testing Profile Storage...")
    
    profile_name = "Test User"
    
    # 1. Add Profile with new fields
    print(f"Creating profile '{profile_name}'...")
    storage.add_profile(profile_name, max_hr=190, max_prework_hr=120, 
                        sex="Male", birth_date="1990-01-01", weight_kg=75.5, weight_unit_pref="kg")
    
    # Verify
    details = storage.get_profile_details(profile_name)
    assert details["sex"] == "Male"
    assert details["birth_date"] == "1990-01-01"
    assert details["weight_kg"] == 75.5
    assert details["weight_unit_pref"] == "kg"
    print("Initial creation verified.")
    
    # 2. Update Profile
    print("Updating profile fields...")
    storage.update_profile(profile_name, sex="Female", birth_date="1995-05-05", 
                           weight_kg=60.0, weight_unit_pref="lbs")
                           
    # Verify Update
    details = storage.get_profile_details(profile_name)
    assert details["sex"] == "Female"
    assert details["birth_date"] == "1995-05-05"
    assert details["weight_kg"] == 60.0
    assert details["weight_unit_pref"] == "lbs"
    print("Update verified.")
    
    # 3. Check DB directly
    print("Checking DB profile content...")
    conn = storage.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM profiles WHERE name = ?", (profile_name,))
    p = dict(c.fetchone())
    print(p)
    conn.close()
        
    print("\nSUCCESS: All storage tests passed.")

if __name__ == "__main__":
    test_profile_fields()
