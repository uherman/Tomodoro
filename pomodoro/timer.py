import time
from enum import Enum, auto
from typing import Callable, Optional

from .config import Config


class Phase(Enum):
    IDLE = auto()
    WORK = auto()
    SHORT_BREAK = auto()
    LONG_BREAK = auto()


class TimerState(Enum):
    RUNNING = auto()
    PAUSED = auto()
    STOPPED = auto()


class TimerEngine:
    def __init__(self, config: Config):
        self.config = config
        self.phase = Phase.IDLE
        self.state = TimerState.STOPPED
        self.remaining: float = 0.0
        self.total_seconds: int = 0
        self.completed_sessions: int = 0
        self.on_phase_complete: Optional[Callable[[Phase], None]] = None

        self._last_tick: float = 0.0
        self._pause_remaining: float = 0.0

    def start(self) -> None:
        if self.phase == Phase.IDLE:
            self.phase = Phase.WORK
        self.total_seconds = self._phase_duration()
        self.remaining = float(self.total_seconds)
        self.state = TimerState.RUNNING
        self._last_tick = time.monotonic()

    def pause(self) -> None:
        if self.state == TimerState.RUNNING:
            self._update_remaining()
            self.state = TimerState.PAUSED

    def resume(self) -> None:
        if self.state == TimerState.PAUSED:
            self.state = TimerState.RUNNING
            self._last_tick = time.monotonic()

    def toggle_pause(self) -> None:
        if self.state == TimerState.RUNNING:
            self.pause()
        elif self.state == TimerState.PAUSED:
            self.resume()
        elif self.state == TimerState.STOPPED:
            self.start()

    def skip(self) -> None:
        if self.phase == Phase.IDLE:
            return
        self._transition()

    def reset(self) -> None:
        self.total_seconds = self._phase_duration()
        self.remaining = float(self.total_seconds)
        if self.state == TimerState.RUNNING:
            self._last_tick = time.monotonic()

    def stop(self) -> None:
        self.phase = Phase.IDLE
        self.state = TimerState.STOPPED
        self.remaining = 0.0
        self.total_seconds = 0
        self.completed_sessions = 0

    def tick(self) -> None:
        if self.state != TimerState.RUNNING:
            return
        self._update_remaining()
        if self.remaining <= 0:
            self.remaining = 0
            self._transition()

    def _update_remaining(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_tick
        self._last_tick = now
        self.remaining -= elapsed

    def _transition(self) -> None:
        completed_phase = self.phase
        if self.phase == Phase.WORK:
            self.completed_sessions += 1
            if self.completed_sessions >= self.config.sessions_before_long_break:
                self.phase = Phase.LONG_BREAK
            else:
                self.phase = Phase.SHORT_BREAK
        elif self.phase in (Phase.SHORT_BREAK, Phase.LONG_BREAK):
            if self.phase == Phase.LONG_BREAK:
                self.completed_sessions = 0
            self.phase = Phase.WORK

        self.total_seconds = self._phase_duration()
        self.remaining = float(self.total_seconds)
        self.state = TimerState.RUNNING
        self._last_tick = time.monotonic()

        if self.on_phase_complete:
            self.on_phase_complete(completed_phase)

    def _phase_duration(self) -> int:
        if self.phase == Phase.WORK:
            return self.config.work_minutes * 60
        elif self.phase == Phase.SHORT_BREAK:
            return self.config.short_break_minutes * 60
        elif self.phase == Phase.LONG_BREAK:
            return self.config.long_break_minutes * 60
        return 0

    @property
    def progress(self) -> float:
        if self.total_seconds == 0:
            return 0.0
        return 1.0 - (max(0, self.remaining) / self.total_seconds)

    @property
    def display_time(self) -> str:
        secs = max(0, int(self.remaining))
        m, s = divmod(secs, 60)
        return f"{m:02d}:{s:02d}"

    @property
    def phase_label(self) -> str:
        labels = {
            Phase.IDLE: "READY",
            Phase.WORK: "FOCUS",
            Phase.SHORT_BREAK: "SHORT BREAK",
            Phase.LONG_BREAK: "LONG BREAK",
        }
        return labels.get(self.phase, "")
