"""
Plain-Python Pomodoro timer used by the PyGame loop.
Only relies on built-in types so it mirrors the ThinkPython notebook style.
"""

class PomodoroTimer:
    """Represents a simple Pomodoro timer with work/break sessions.

    The timer stores all state in attributes and exposes small methods
    that mutate those attributes. The game loop drives it by calling
    start_* methods and tick() every frame with the elapsed seconds.
    """

    def __init__(self, work_seconds=1500, break_seconds=300):
        # Default durations are the real Pomodoro values (25/5 minutes).
        self.work_seconds = work_seconds
        self.break_seconds = break_seconds

        # Count-down value for the current session (in seconds, float friendly).
        self.remaining = work_seconds

        # Flag set by start_work/start_break; prevents tick from changing state
        # when the timer is paused or finished.
        self.running = False

        # Tracks which session is active so the UI can show the phase clearly.
        self.mode = "work"

    def start_work(self, demo=False):
        """Begin a work session.

        Passing demo=True switches to a short 30s timer so the main loop can
        be demonstrated quickly without waiting 25 minutes.
        """
        self.mode = "work"
        self.remaining = 30 if demo else self.work_seconds
        self.running = True

    def start_break(self, demo=False):
        """Begin a break session (mirrors start_work)."""
        self.mode = "break"
        self.remaining = 10 if demo else self.break_seconds
        self.running = True

    def tick(self, dt):
        """Advance the timer by dt seconds.

        The game loop supplies dt as the time since the previous frame.
        If the timer is not running we exit early to avoid negative values.
        """
        if not self.running:
            return

        self.remaining -= dt

        if self.remaining <= 0:
            # Clamp to zero and pause so finished() returns True once.
            self.remaining = 0
            self.running = False

    def finished(self):
        """Return True when the active session has completed."""
        return (not self.running) and (self.remaining <= 0)
