from dataclasses import dataclass
from enum import Enum, auto

class WorkoutState(Enum):
    IDLE = auto()
    PREP = auto()
    WORK = auto()
    REST = auto()
    PAUSED = auto()
    FINISHED = auto()

@dataclass
class WorkoutEvent:
    sound_name: str = None
    sound_count: int = 0
    phase_changed: bool = False
    finished: bool = False

class Workout:
    def __init__(self, total_rounds: int, work_duration: int, rest_duration: int):
        self.total_rounds = total_rounds
        self.work_duration = work_duration
        self.rest_duration = rest_duration
        
        self.current_round = 0
        self.time_left = 0
        self.state = WorkoutState.IDLE
        self.previous_state = None # To handle pause resume
        
    def start(self):
        self.state = WorkoutState.PREP
        self.current_round = 0
        self.time_left = 10 # Prep time
        
    def pause(self):
        if self.state != WorkoutState.PAUSED:
            self.previous_state = self.state
            self.state = WorkoutState.PAUSED
        else:
            self.state = self.previous_state
            self.previous_state = None
            
    def reset(self):
        self.state = WorkoutState.IDLE
        self.current_round = 0
        self.time_left = 0
        
    def tick(self) -> WorkoutEvent:
        event = WorkoutEvent()
        
        if self.state in [WorkoutState.IDLE, WorkoutState.PAUSED, WorkoutState.FINISHED]:
            return event
            
        if self.time_left > 1:
            self.time_left -= 1
        else:
            # Time is up, transition needed
            self._handle_transition(event)
            
        return event

    def _handle_transition(self, event: WorkoutEvent):
        if self.state == WorkoutState.PREP:
            self._start_round(event)
            
        elif self.state == WorkoutState.WORK:
            if self.rest_duration > 0 and self.current_round < self.total_rounds: # Check for rest only if not last round? 
                # Actually, usually EMOM ends after the last work (or rest if wanted). 
                # Let's check logic: if round < total, we might rest or go to next round.
                # If rest > 0, always rest unless it's the very last round? 
                # Usually last round ends with Work done.
                if self.current_round < self.total_rounds:
                     self._start_rest(event)
                else:
                    self._finish(event)
            else:
                if self.current_round < self.total_rounds:
                    self._start_round(event) # Next round immediately
                else:
                    self._finish(event)
                    
        elif self.state == WorkoutState.REST:
            if self.current_round < self.total_rounds:
                self._start_round(event)
            else:
                self._finish(event) # Should not really happen if logic above is correct
                
    def _start_round(self, event: WorkoutEvent):
        if self.state == WorkoutState.PREP:
             self.current_round = 1 # First round
        elif self.state == WorkoutState.REST or self.state == WorkoutState.WORK:
             if self.state == WorkoutState.REST:
                 self.current_round += 1
             elif self.state == WorkoutState.WORK: # Immediate transition
                 self.current_round += 1
                 
        self.state = WorkoutState.WORK
        self.time_left = self.work_duration
        
        event.phase_changed = True
        event.sound_name = "Glass"
        event.sound_count = 2 # 2x Glass for Round Start

    def _start_rest(self, event: WorkoutEvent):
        self.state = WorkoutState.REST
        self.time_left = self.rest_duration
        
        event.phase_changed = True
        event.sound_name = "Hero"
        event.sound_count = 1
        
    def _finish(self, event: WorkoutEvent):
        self.state = WorkoutState.FINISHED
        self.time_left = 0
        
        event.finished = True
        event.sound_name = "Glass"
        event.sound_count = 3

    @property
    def status_text(self):
        if self.state == WorkoutState.IDLE: return "READY"
        if self.state == WorkoutState.PREP: return "GET READY"
        if self.state == WorkoutState.WORK: return "WORK"
        if self.state == WorkoutState.REST: return "REST"
        if self.state == WorkoutState.PAUSED: return "PAUSED"
        if self.state == WorkoutState.FINISHED: return "COMPLETED!"
        return ""
        
    @property
    def time_display(self):
        minutes = self.time_left // 60
        seconds = self.time_left % 60
        return f"{minutes:02}:{seconds:02}"
        
    @property
    def round_display(self):
        if self.state == WorkoutState.PREP:
            return "PREP"
        return f"{self.current_round} / {self.total_rounds}"
