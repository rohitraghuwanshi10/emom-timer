
import unittest
from workout import Workout, WorkoutState

class TestAutoRegulation(unittest.TestCase):
    def test_auto_regulation_off(self):
        # Setup: Rest duration 10s. Start workout.
        w = Workout(10, 60, 10, auto_regulation=False, max_prework_hr=100)
        w.start() # PREP
        
        # Advance through PREP
        w.time_left = 1
        w.tick() # Transition to WORK R1
        self.assertEqual(w.state, WorkoutState.WORK)
        
        # Advance through WORK
        w.time_left = 1
        w.tick() # Transition to REST R1
        self.assertEqual(w.state, WorkoutState.REST)
        
        # Advance through REST
        w.time_left = 1
        # Tick with High HR (should transition because Auto Reg is OFF)
        w.tick(current_hr=150) 
        self.assertEqual(w.state, WorkoutState.WORK) # R2
        
    def test_auto_regulation_hold(self):
        # Setup: Auto Reg ON, Max 100
        w = Workout(10, 60, 10, auto_regulation=True, max_prework_hr=100)
        w.start()
        w.time_left = 1
        w.tick() # WORK R1
        w.time_left = 1
        w.tick() # REST R1
        
        # Near end of rest
        w.time_left = 1
        # Tick with High HR
        w.tick(current_hr=150)
        
        # Should STAY in REST (Holding)
        self.assertEqual(w.state, WorkoutState.REST) 
        self.assertTrue(w.waiting_for_hr)
        
        # Tick again with High HR
        w.tick(current_hr=150)
        self.assertEqual(w.state, WorkoutState.REST)
        
        # Tick with Low HR
        w.tick(current_hr=90)
        # Should transition
        self.assertEqual(w.state, WorkoutState.WORK) # R2
        self.assertFalse(w.waiting_for_hr)

    def test_auto_regulation_no_max_set(self):
        # Setup: Auto Reg ON, but No Max set
        w = Workout(10, 60, 10, auto_regulation=True, max_prework_hr=None)
        w.start()
        w.time_left = 1
        w.tick() # WORK R1
        w.time_left = 1
        w.tick() # REST R1
        
        w.time_left = 1
        w.tick(current_hr=150)
        # Should transition because max_prework_hr is None
        self.assertEqual(w.state, WorkoutState.WORK)

if __name__ == '__main__':
    unittest.main()
