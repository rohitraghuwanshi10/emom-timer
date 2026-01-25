from workout import Workout

class MockStringVar:
    def __init__(self, value):
        self.value = value
    def get(self):
        return self.value
    def set(self, value):
        self.value = value

class MockApp:
    def __init__(self):
        # Initialize with Auto Reg OFF
        self.workout = Workout(10, 60, 30, auto_regulation=False)
        self.auto_regulation_var = MockStringVar(False)
        
    def update_auto_regulation(self):
        """Updates the running workout instance if the user toggles the checkbox mid-workout."""
        if self.workout:
            val = self.auto_regulation_var.get()
            self.workout.auto_regulation = val
            print(f"Updated active workout auto_regulation to: {val}")

def test_toggle():
    app = MockApp()
    
    print(f"Initial Workout AutoReg: {app.workout.auto_regulation}")
    assert app.workout.auto_regulation == False
    
    # Simulate Toggle ON
    print("User toggles ON...")
    app.auto_regulation_var.set(True)
    app.update_auto_regulation()
    
    print(f"Updated Workout AutoReg: {app.workout.auto_regulation}")
    assert app.workout.auto_regulation == True
    
    # Simulate Toggle OFF
    print("User toggles OFF...")
    app.auto_regulation_var.set(False)
    app.update_auto_regulation()
    
    print(f"Updated Workout AutoReg: {app.workout.auto_regulation}")
    assert app.workout.auto_regulation == False
    
    print("TEST PASSED")

if __name__ == "__main__":
    test_toggle()
