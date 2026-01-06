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

# 4. Verify JSON file directly
with open(storage.PROFILES_FILE, 'r') as f:
    data = json.load(f)
    saved_val = data["profiles"]["TestMaxHR"].get("max_hr")
    print(f"Saved Value in JSON: {saved_val}")
    
    if saved_val == 185:
        print("SUCCESS: Max HR verified in JSON file.")
    else:
        print("FAILURE: Max HR mismatch in JSON file.")
