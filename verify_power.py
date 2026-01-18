from power_management import PowerManager
import time
import sys

def verify():
    print("Initializing PowerManager...")
    pm = PowerManager()
    
    print(f"Detected OS: {pm.os_type}")
    
    print("\n--- Prevention Test ---")
    print("Calling prevent_sleep()...")
    pm.prevent_sleep()
    
    if sys.platform == 'darwin':
        print("Check 'pmset -g assertions' in another terminal now.")
        print("Look for 'PreventUserIdleDisplaySleep' with reason 'EMOM Timer Workout'")
    elif sys.platform == 'win32':
        print("Check 'powercfg -requests' in admin cmd now.")
        print("Look for DISPLAY and SYSTEM requests.")
        
    print("Waiting 5 seconds...")
    time.sleep(5)
    
    print("\n--- Release Test ---")
    print("Calling allow_sleep()...")
    pm.allow_sleep()
    print("Released.")
    
    if sys.platform == 'darwin':
        print("Check 'pmset -g assertions' again. It should be gone.")
        
    print("\nVerification Complete.")

if __name__ == "__main__":
    verify()
