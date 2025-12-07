import sys
from unittest.mock import MagicMock

# Mock customtkinter before importing main
mock_ctk = MagicMock()
sys.modules["customtkinter"] = mock_ctk

# Ensure CTk class in mock can be inherited
class MockCTk:
    def __init__(self):
        pass
    def title(self, *args, **kwargs): pass
    def geometry(self, *args, **kwargs): pass
    def resizable(self, *args, **kwargs): pass
    def grid_columnconfigure(self, *args, **kwargs): pass
    def after(self, ms, func): 
        # Mock after to just return a dummy id
        return "job_id"
    def after_cancel(self, id): pass
    def mainloop(self): pass

mock_ctk.CTk = MockCTk

# Generic Mock Widget
class MockWidget(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__()
    def grid(self, *args, **kwargs): pass
    def pack(self, *args, **kwargs): pass
    def configure(self, *args, **kwargs): pass
    def grid_columnconfigure(self, *args, **kwargs): pass

mock_ctk.CTkFrame = MockWidget
mock_ctk.CTkLabel = MockWidget
mock_ctk.CTkEntry = MockWidget
# Mock return values for StringVar
def mock_string_var(*args, **kwargs):
    val = kwargs.get("value", "0")
    m = MagicMock()
    m.get.return_value = str(val)
    return m

# Assign mock factory
mock_ctk.StringVar = MagicMock(side_effect=mock_string_var)

# Now import main
import main

print("Instantiating App...")
app = main.EMOMApp()

print("Testing Start Workout (2 Rounds, 5 seconds)...")
# Mock inputs
app.total_rounds_var.get.return_value = "2"
app.round_timer_var.get.return_value = "5"

app.start_workout()

# Check Initial State
# Logic: time_left starts at 4, but update_timer decrements it to 3 immediately after display
# So displayed time is 4, but internal variable is 3.
expected_time = 3
print(f"State after start: Round {app.current_round}, TimeLeft {app.time_left}")

assert app.current_round == 1, f"Expected Round 1, got {app.current_round}"
assert app.time_left == expected_time, f"Expected Time {expected_time}, got {app.time_left}"

print("Testing Timer Update...")
# update_timer() should print, then decrement from 3 to 2
app.update_timer()

# Now time should be 2
print(f"State after 1 tick: TimeLeft {app.time_left}")
assert app.time_left == 2, f"Expected Time 2, got {app.time_left}"

print("Simulating Round End...")
# Set time to 0 to simulate end of round
app.time_left = 0
app.update_timer() 
# This should fulfill 'time_left > 0' as False, so it goes to else -> next_round()
# next_round() increments round to 2, resets time to 4 (5-1)
# And calls after() to continue.

print(f"State after round end: Round {app.current_round}, TimeLeft {app.time_left}")
assert app.current_round == 2, f"Expected Round 2, got {app.current_round}"
assert app.time_left == 4, f"Expected Time 4 (reset), got {app.time_left}"

print("Simulating Workout End...")
# Set to last round, end of time
app.current_round = 2
app.time_left = 0
app.update_timer() # Triggers next_round -> but round is 2 (total 2).
# next_round logic: if current_round < total_rounds (2 < 2 is False) -> else finish_workout()

print(f"State after finish: IsRunning {app.is_running}")
assert app.is_running == False, "Expected is_running to be False"

print("VERIFICATION SUCCESSFUL: Logic works as expected.")
