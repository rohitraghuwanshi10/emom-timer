import unittest
from workout import Workout

class TestWorkoutIncrementalRest(unittest.TestCase):
    def test_incremental_rest_logic(self):
        # Config: 10 Rounds, 30s Rest.
        # Increment: 5s, Every: 2 rounds, Start: after Round 5.
        
        # Expected Rest:
        # After R1: 30 (Base)
        # After R2: 30
        # After R3: 30
        # After R4: 30
        # After R5: 35 (Base + 1*5) -> Delta 0 (5-5=0). Inc = (0//2)+1 = 1.
        # After R6: 35 (Base + 1*5) -> Delta 1 (6-5=1). Inc = (1//2)+1 = 1.
        # After R7: 40 (Base + 2*5) -> Delta 2 (7-5=2). Inc = (2//2)+1 = 2.
        
        workout = Workout(
            total_rounds=10, 
            work_duration=60, 
            rest_duration=30,
            rest_increment=5,
            rest_interval=2,
            rest_start_round=5
        )
        
        # Simulate Rounds
        # R1
        workout.current_round = 1
        self.assertEqual(workout._calculate_rest_duration(), 30, "Round 1 should be base rest")
        
        # R4
        workout.current_round = 4
        self.assertEqual(workout._calculate_rest_duration(), 30, "Round 4 should be base rest")
        
        # R5
        workout.current_round = 5
        self.assertEqual(workout._calculate_rest_duration(), 35, "Round 5 should have 1 increment")
        
        # R6
        workout.current_round = 6
        self.assertEqual(workout._calculate_rest_duration(), 35, "Round 6 should have 1 increment")
        
        # R7
        workout.current_round = 7
        self.assertEqual(workout._calculate_rest_duration(), 40, "Round 7 should have 2 increments")

    def test_completed_rounds_logic(self):
        from workout import WorkoutState
        
        # Test case: 60s work, 30s rest
        workout = Workout(total_rounds=5, work_duration=60, rest_duration=30)
        
        # 1. Prep phase / Initial state
        workout.current_round = 0
        workout.state = WorkoutState.PREP
        self.assertEqual(workout.get_completed_rounds(), 0)
        
        # 2. Work phase of Round 1
        workout.current_round = 1
        workout.state = WorkoutState.WORK
        
        # Exactly 0s completed (60s left)
        workout.time_left = 60
        self.assertEqual(workout.get_completed_rounds(), 0)
        
        # 29s completed (31s left)
        workout.time_left = 31
        self.assertEqual(workout.get_completed_rounds(), 0)
        
        # Exactly 50% (30s completed, 30s left)
        workout.time_left = 30
        self.assertEqual(workout.get_completed_rounds(), 0)
        
        # More than 50% (31s completed, 29s left)
        workout.time_left = 29
        self.assertEqual(workout.get_completed_rounds(), 1)
        
        # 3. Rest phase of Round 1
        workout.state = WorkoutState.REST
        self.assertEqual(workout.get_completed_rounds(), 1)
        
        # 4. Paused state (WORK)
        workout.state = WorkoutState.PAUSED
        workout.previous_state = WorkoutState.WORK
        
        workout.time_left = 30 # Exactly 50%
        self.assertEqual(workout.get_completed_rounds(), 0)
        
        workout.time_left = 29 # More than 50%
        self.assertEqual(workout.get_completed_rounds(), 1)
        
        # 5. Paused state (REST)
        workout.previous_state = WorkoutState.REST
        self.assertEqual(workout.get_completed_rounds(), 1)

if __name__ == '__main__':
    unittest.main()
