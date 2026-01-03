import unittest
from workout import Workout, WorkoutState, WorkoutEvent

class TestWorkoutIncrementalRestBug(unittest.TestCase):
    def test_zero_base_rest(self):
        # Config: Base 0s, Inc 5s, Start R1, Every 1
        # Expectation: 
        # R1 Work -> Rest (0+5=5s)
        
        workout = Workout(
            total_rounds=10, 
            work_duration=10, 
            rest_duration=0, # ZERO BASE
            rest_increment=5,
            rest_interval=1,
            rest_start_round=1
        )
        
        workout.start() # To Prep
        workout.state = WorkoutState.WORK # Force to Work
        workout.current_round = 1
        workout.time_left = 1
        
        # Tick to finish work
        event = workout.tick()
        
        # Should transition to REST because calculated rest is 5s
        # But logic checks `if self.rest_duration > 0` which is False.
        # So it likely transitions strictly to Work (Round 2) or Finish.
        
        self.assertEqual(workout.state, WorkoutState.REST, "Should transition to REST even if base rest is 0")
        self.assertEqual(workout.time_left, 5, "Rest time should be 5s")

if __name__ == '__main__':
    unittest.main()
