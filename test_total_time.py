
import unittest
from workout import Workout, WorkoutState, WorkoutEvent

class TestTotalTime(unittest.TestCase):
    def test_basic_time_accumulation(self):
        """Test simple work/rest accumulation."""
        # 1 Round, 5 work, 5 rest
        workout = Workout(total_rounds=1, work_duration=5, rest_duration=5)
        workout.start() # To PREP
        
        # Finish PREP
        for _ in range(10): 
            workout.tick()
        
        # Should be in WORK now
        self.assertEqual(workout.state, WorkoutState.WORK)
        
        # Tick 5 seconds Work
        for _ in range(5):
            workout.tick()
        
        self.assertEqual(workout.actual_work_time_sec, 5)
        
        # Transition/Tick 5 seconds Rest
        # Note: Last tick of Work transitions to Rest or Finish.
        # Let's see behavior. logic says if time_left > 1 decrement.. else transition.
        # Work duration 5.
        # Start: time_left = 5.
        # T1: time_left=4. AcWork=1.
        # T2: time_left=3. AcWork=2.
        # T3: time_left=2. AcWork=3.
        # T4: time_left=1. AcWork=4.
        # T5: time_left=1? -> transition. AcWork=5.
        
        # In continuous workout mode, the workout transitions to REST state instead of auto-finishing.
        self.assertEqual(workout.state, WorkoutState.REST)
        
        # Finish manually (simulating the STOP button click)
        event = WorkoutEvent()
        workout._finish(event)
        
        self.assertEqual(workout.state, WorkoutState.FINISHED)
        self.assertEqual(workout.total_actual_time, 5)

    def test_incremental_rest_accumulation(self):
        """Test time with incremental rest."""
        # 2 Rounds. Work 5. Rest 5.
        # Round 1: Work 5 -> Rest 5.
        # Round 2: Work 5 -> REST (continuous mode keeps running).
        # Total: 5 + 5 + 5 = 15.
        
        workout = Workout(total_rounds=2, work_duration=5, rest_duration=5)
        workout.start()
        
        # Skip PREP
        workout.state = WorkoutState.PREP
        workout.time_left = 1
        workout.tick() # transitions to WORK
        
        # R1 Work (5s)
        for _ in range(5): workout.tick()
        self.assertEqual(workout.state, WorkoutState.REST)
        self.assertEqual(workout.actual_work_time_sec, 5)
        
        # R1 Rest (5s)
        for _ in range(5): workout.tick()
        self.assertEqual(workout.state, WorkoutState.WORK)
        self.assertEqual(workout.actual_rest_time_sec, 5)
        
        # R2 Work (5s)
        for _ in range(5): workout.tick()
        self.assertEqual(workout.state, WorkoutState.REST)
        self.assertEqual(workout.actual_work_time_sec, 10)
        
        # Finish manually (simulating the STOP button click)
        event = WorkoutEvent()
        workout._finish(event)
        self.assertEqual(workout.state, WorkoutState.FINISHED)
        self.assertEqual(workout.total_actual_time, 15)

    def test_auto_regulation_accumulation(self):
        """Test time with auto regulation (waiting)."""
        # 2 Rounds. Work 5, Rest 0. AutoReg on.
        # R1 Work 5s.
        # Enters Rest (technically skips rest duration, but might wait for HR).
        # But wait, logic says: if calculate_rest() > 0 or current < total...
        # If rest=0, it might skip rest state?
        # Let's check logic:
        # if _calculate_rest_duration() > 0 ...: _start_rest
        # else: if current < total: _start_round
        
        # So if rest=0, it skips REST state entirely.
        # Auto-regulation check is INSIDE REST state loop.
        # So we MUST have some rest duration for auto-reg to work currently?
        # Or at least logic implies it checks auto-reg strictly while in REST state.
        
        # Let's assume Rest=5. Max Pre-Work HR = 100.
        workout = Workout(total_rounds=2, work_duration=5, rest_duration=5, 
                          max_prework_hr=100, auto_regulation=True)
        workout.start()
        # Skip PREP
        workout.state = WorkoutState.PREP
        workout.time_left = 1
        workout.tick() 
        
        # R1 Work (5s)
        for _ in range(5): workout.tick()
        
        # R1 Rest.
        # Provide High HR to force wait.
        # Tick 1: Rest decrements. HR=120.
        workout.tick(current_hr=120) 
        self.assertEqual(workout.actual_rest_time_sec, 1)
        
        # Tick until Rest time is up (4 more times)
        for _ in range(4): workout.tick(current_hr=120)
        self.assertEqual(workout.actual_rest_time_sec, 5)
        
        # Now time_left is passed (transition logic called).
        # Inside _handle_transition(REST):
        # Checks HR. If > 100, "return" (stay in REST, waiting_for_hr=True).
        # It does NOT start next round.
        # Next tick, time_left is likely 0? Or does it reset?
        # Logic: if time_left > 1... else transition.
        # If we return from transition without changing state/time, time_left stays 0?
        # Wait, if time_left is 0 (or low), tick calls transition.
        # Transition returns.
        # Next tick: time_left is still low/0. Calls transition again.
        
        # We need to ensure we count time while waiting.
        # workout.tick -> if time_left > 1 (decrement) else (increment actual time, call transition).
        # So every tick calls transition, which returns early. actual_rest_time_sec increments.
        
        # Simulate 5 seconds of waiting for HR
        for _ in range(5):
            workout.tick(current_hr=120)
            
        self.assertEqual(workout.actual_rest_time_sec, 10) # 5 normal + 5 waiting
        self.assertTrue(workout.waiting_for_hr)
        
        # Recover HR
        workout.tick(current_hr=90)
        # Should transition to WORK (R2)
        self.assertEqual(workout.state, WorkoutState.WORK)
        self.assertEqual(workout.current_round, 2)

if __name__ == '__main__':
    unittest.main()
