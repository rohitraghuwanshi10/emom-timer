# EMOM Workout Timer

A modern, python-based EMOM (Every Minute on the Minute) timer application built with CustomTkinter. This app helps you track your high-intensity interval workouts with precision, offering visual cues, history tracking, and progress visualization.

## Features

### ⏱️ Advanced Timer
- **Flexible Configuration**: Set your **Total Rounds**, **Work Duration**, and **Rest Duration**.
- **Work & Rest Phases**: The timer clearly distinguishes between "Work" and "Rest" phases with visual status updates.
- **Smart Countdown**: 
    - **Work Phase**: Counts down your configured work time.
    - **Rest Phase**: Automatically switches to a rest timer before the next round begins.
- **Control**: Start, Pause, and Reset your workout at any time.

### 📊 History & Analytics
- **Automatic Logging**: Every completed workout is automatically saved to `workout_history.csv`.
    - Tracks: Start/End time, Rounds completed, Work/Rest settings, and Total duration.
- **History Dashboard**: Built-in "Show History" window.
    - **Table View**: Browse your past workouts with details.
    - **data Visualization**: A stacked bar chart visualizes your daily workout volume (Total Time in minutes) over time.

### 📝 Workout Notes
- Add custom **Notes** to any workout before starting or saving.
- Notes are saved alongside performance data for future reference (e.g., "16kg kettlebell ABC workout").

## Getting Started

### Prerequisites
- Python 3.x
- Required libraries:
  ```bash
  pip install customtkinter pillow matplotlib numpy
  ```

### Running the App
Run the `main.py` file:
```bash
python main.py
```

## Data Storage
Workout data is stored locally in `workout_history.csv`.
- **Columns**: `start_time`, `end_time`, `total_rounds_completed`, `round_timer_sec`, `total_time_sec`, `workout_notes`, `rest_time_sec`.

## Technologies
- **UI**: CustomTkinter
- **Plotting**: Matplotlib
- **Data**: CSV
