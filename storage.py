import csv
import os

# Save to user's Documents folder for persistence
DOCS_DIR = os.path.expanduser("~/Documents/EMOM Timer")
FILENAME = os.path.join(DOCS_DIR, "workout_history.csv")
HEADERS = ["start_time", "end_time", "total_rounds_completed", "work_time_sec", "rest_time_sec", "total_time_sec", "workout_notes"]

def _ensure_dir():
    """Ensures the directory exists."""
    if not os.path.exists(DOCS_DIR):
        os.makedirs(DOCS_DIR)

def initialize_csv():
    """Creates the CSV file with headers if it doesn't exist."""
    _ensure_dir()
    if not os.path.exists(FILENAME):
        with open(FILENAME, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)

def save_workout(workout_data):
    """
    Appends a workout record to the CSV.
    workout_data: list corresponding to HEADERS
    """
    initialize_csv() # Ensure file exists (and dir)
    
    with open(FILENAME, mode='a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(workout_data)

def load_workouts():
    """Returns a list of rows from the CSV (including header)."""
    if not os.path.exists(FILENAME):
        return []
    
    with open(FILENAME, mode='r') as f:
        reader = csv.reader(f)
        data = list(reader)
    return data
