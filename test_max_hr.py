import storage
import json
import os

print("--- Testing Storage ---")

# 1. Add Profile
storage.add_profile("TestMaxHR")
print("Added profile TestMaxHR")

# 2. Update Max HR
storage.update_profile("TestMaxHR", max_hr=185)
print("Updated Max HR to 185")

# 3. Verify via get_profile_details
details = storage.get_profile_details("TestMaxHR")
print(f"Retrieved Details: {details}")

if details.get("max_hr") == 185:
    print("SUCCESS: Max HR verified in memory.")
else:
    print("FAILURE: Max HR mismatch in memory.")

# 4. Verify DB file directly
conn = storage.get_db_connection()
try:
    c = conn.cursor()
    c.execute("SELECT max_hr FROM profiles WHERE name = ?", ("TestMaxHR",))
    row = c.fetchone()
    saved_val = row["max_hr"] if row else None
    print(f"Saved Value in DB: {saved_val}")
    
    if saved_val == 185:
        print("SUCCESS: Max HR verified in DB file.")
    else:
        print("FAILURE: Max HR mismatch in DB file.")
except Exception as e:
    print(f"FAILURE: DB query failed: {e}")
finally:
    conn.close()
