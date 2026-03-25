from __future__ import annotations

import curses
import subprocess
from dataclasses import asdict

from .art import C_BODY, C_LABEL, C_STEM, get_tomato_progress
from .brightness import get_brightness, set_brightness
from .config import Config
from .keyboard_backlight import get_keyboard_brightness, set_keyboard_brightness
from .sounds import SAD_TRUMPET_WAV, TRUMPET_WAV
from .stats import StatsStore
from .timer import Phase, TimerEngine, TimerState

# ---------------------------------------------------------------------------
# Color pair IDs
# ---------------------------------------------------------------------------
PAIR_RED = 1
PAIR_GREEN = 2
PAIR_YELLOW = 3
PAIR_CYAN = 4
PAIR_WHITE = 5
PAIR_MAGENTA = 6
PAIR_HIGHLIGHT = 7

# Map art color types -> curses color pair for work / break states
COLOR_MAP = {
    C_BODY: PAIR_RED,
    C_STEM: PAIR_GREEN,
    C_LABEL: PAIR_RED,
}

MIN_WIDTH = 50
MIN_HEIGHT = 24


def safe_addstr(win, y: int, x: int, text: str, attr: int = 0) -> None:
    h, w = win.getmaxyx()
    if y < 0 or y >= h or x >= w:
        return
    if x < 0:
        text = text[-x:]
        x = 0
    max_len = w - x
    if max_len <= 0:
        return
    try:
        win.addstr(y, x, text[:max_len], attr)
    except curses.error:
        pass


class App:
    def __init__(self):
        self.config = Config.load()
        self.stats = StatsStore.load()
        self.timer = TimerEngine(self.config)
        self.timer.on_phase_complete = self._on_phase_complete
        self.screen = "timer"  # timer | stats | settings
        self.frame = 0
        self.flash_frames = 0  # countdown for completion flash effect
        self.stats_week_offset = 0
        self.settings_cursor = 0
        self.settings_values: dict = {}
        self.settings_editing = False  # True when typing a custom number
        self.settings_edit_buf = ""    # digit buffer for manual input
        self._saved_brightness: float | None = None
        self._saved_kbd_brightness: float | None = None

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self, stdscr) -> None:
        self._setup(stdscr)
        while True:
            h, w = stdscr.getmaxyx()
            if h < MIN_HEIGHT or w < MIN_WIDTH:
                self._draw_too_small(stdscr, h, w)
                curses.napms(200)
                continue

            key = stdscr.getch()
            if key == curses.KEY_RESIZE:
                stdscr.clear()
                continue

            # Skip global keys only when in settings edit mode
            if not (self.screen == "settings" and self.settings_editing):
                action = self._handle_global_keys(key)
                if action == "quit":
                    break

            if self.screen == "timer":
                self._handle_timer_keys(key)
            elif self.screen == "stats":
                self._handle_stats_keys(key)
            elif self.screen == "settings":
                self._handle_settings_keys(key)

            self.timer.tick()
            self.frame += 1

            # Update keyboard backlight as break progress indicator
            if (
                self._saved_kbd_brightness is not None
                and self.timer.phase in (Phase.SHORT_BREAK, Phase.LONG_BREAK)
                and self.timer.state == TimerState.RUNNING
                and self.frame % 60 == 0  # update ~once per second
            ):
                set_keyboard_brightness(self.timer.progress)

            stdscr.erase()
            if self.screen == "timer":
                self._draw_timer(stdscr)
            elif self.screen == "stats":
                self._draw_stats(stdscr)
            elif self.screen == "settings":
                self._draw_settings(stdscr)
            stdscr.refresh()

            curses.napms(16)  # ~60 FPS

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup(self, stdscr) -> None:
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.keypad(True)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(PAIR_RED, curses.COLOR_RED, -1)
        curses.init_pair(PAIR_GREEN, curses.COLOR_GREEN, -1)
        curses.init_pair(PAIR_YELLOW, curses.COLOR_YELLOW, -1)
        curses.init_pair(PAIR_CYAN, curses.COLOR_CYAN, -1)
        curses.init_pair(PAIR_WHITE, curses.COLOR_WHITE, -1)
        curses.init_pair(PAIR_MAGENTA, curses.COLOR_MAGENTA, -1)
        curses.init_pair(PAIR_HIGHLIGHT, curses.COLOR_BLACK, curses.COLOR_WHITE)

    # ------------------------------------------------------------------
    # Key handling
    # ------------------------------------------------------------------

    def _restore_brightness(self) -> None:
        if self._saved_brightness is not None:
            set_brightness(self._saved_brightness)
            self._saved_brightness = None
        if self._saved_kbd_brightness is not None:
            set_keyboard_brightness(self._saved_kbd_brightness)
            self._saved_kbd_brightness = None

    def _handle_global_keys(self, key: int) -> str | None:
        if key == ord("Q"):
            self._restore_brightness()
            return "quit"
        if key == ord("1") or key == ord("t"):
            self.screen = "timer"
        elif key == ord("2"):
            self.screen = "stats"
            self.stats_week_offset = 0
        elif key == ord("3"):
            self.screen = "settings"
            self.settings_cursor = 0
            self.settings_values = asdict(self.config)
            self.settings_editing = False
            self.settings_edit_buf = ""
        elif key == 9:  # Tab
            screens = ["timer", "stats", "settings"]
            idx = screens.index(self.screen)
            self.screen = screens[(idx + 1) % len(screens)]
            if self.screen == "settings":
                self.settings_cursor = 0
                self.settings_values = asdict(self.config)
                self.settings_editing = False
                self.settings_edit_buf = ""
        return None

    def _handle_timer_keys(self, key: int) -> None:
        if key == ord(" ") or key == 10:  # Space or Enter
            self.timer.toggle_pause()
        elif key == ord("s") or key == ord("n"):
            self.timer.skip()
        elif key == ord("r"):
            self.timer.reset()
        elif key == ord("q"):
            self._restore_brightness()
            self.timer.stop()

    def _handle_stats_keys(self, key: int) -> None:
        if key == curses.KEY_LEFT:
            self.stats_week_offset += 1
        elif key == curses.KEY_RIGHT:
            self.stats_week_offset = max(0, self.stats_week_offset - 1)
        elif key == 27 or key == ord("q"):
            self.screen = "timer"

    def _commit_edit(self, fields) -> None:
        """Commit the edit buffer to the current setting value."""
        name, _, min_v, max_v = fields[self.settings_cursor]
        if self.settings_edit_buf:
            val = max(min_v, min(max_v, int(self.settings_edit_buf)))
        else:
            val = min_v
        self.settings_values[name] = val
        self.settings_editing = False
        self.settings_edit_buf = ""

    def _handle_settings_keys(self, key: int) -> None:
        fields = self._settings_fields()
        name, _, min_v, max_v = fields[self.settings_cursor]

        # --- Editing mode: typing a custom number ---
        if self.settings_editing:
            if ord("0") <= key <= ord("9"):
                self.settings_edit_buf += chr(key)
                if int(self.settings_edit_buf) > max_v:
                    self.settings_edit_buf = str(max_v)
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                self.settings_edit_buf = self.settings_edit_buf[:-1]
                if not self.settings_edit_buf:
                    self.settings_editing = False
            elif key == 27:  # Escape — cancel edit
                self.settings_editing = False
                self.settings_edit_buf = ""
            elif key == 10:  # Enter — commit edit
                self._commit_edit(fields)
            return

        # --- Normal mode ---
        if key == curses.KEY_UP:
            self.settings_cursor = (self.settings_cursor - 1) % len(fields)
        elif key == curses.KEY_DOWN:
            self.settings_cursor = (self.settings_cursor + 1) % len(fields)
        elif key == curses.KEY_LEFT or key == curses.KEY_RIGHT:
            val = self.settings_values[name]
            if isinstance(val, bool):
                self.settings_values[name] = not val
            else:
                delta = 1 if key == curses.KEY_RIGHT else -1
                self.settings_values[name] = max(min_v, min(max_v, val + delta))
        elif key == ord(" ") and not isinstance(self.settings_values[name], bool):
            # Space enters edit mode for numeric fields
            self.settings_editing = True
            self.settings_edit_buf = ""
        elif key == 10:  # Enter — save
            for n, _, _, _ in fields:
                setattr(self.config, n, self.settings_values[n])
            self.config.save()
            self.timer.config = self.config
            self.screen = "timer"
        elif key == 27 or key == ord("q"):
            self.screen = "timer"

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_phase_complete(self, completed_phase: Phase) -> None:
        if completed_phase == Phase.WORK:
            self.stats.record_session(self.config.work_minutes * 60)
            # Entering break: save brightness and dim screen
            self._saved_brightness = get_brightness()
            set_brightness(0.0)
            # Save keyboard brightness and start progress from 0
            self._saved_kbd_brightness = get_keyboard_brightness()
            set_keyboard_brightness(0.0)
        elif completed_phase in (Phase.SHORT_BREAK, Phase.LONG_BREAK):
            # Break over: restore brightness
            if self._saved_brightness is not None:
                set_brightness(self._saved_brightness)
                self._saved_brightness = None
            if self._saved_kbd_brightness is not None:
                set_keyboard_brightness(self._saved_kbd_brightness)
                self._saved_kbd_brightness = None
        self.flash_frames = 15  # flash for ~1.5s
        if self.config.sound_enabled:
            sound = SAD_TRUMPET_WAV if completed_phase in (Phase.SHORT_BREAK, Phase.LONG_BREAK) else TRUMPET_WAV
            subprocess.Popen(
                ["afplay", str(sound)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    # ------------------------------------------------------------------
    # Timer screen
    # ------------------------------------------------------------------

    def _draw_timer(self, win) -> None:
        h, w = win.getmaxyx()
        is_break = self.timer.phase in (Phase.SHORT_BREAK, Phase.LONG_BREAK)
        is_paused = self.timer.state == TimerState.PAUSED

        # Flash effect
        flashing = False
        if self.flash_frames > 0:
            self.flash_frames -= 1
            flashing = self.flash_frames % 4 < 2

        if self.timer.phase == Phase.IDLE:
            time_str = f"{self.config.work_minutes:02d}:00"
        else:
            time_str = self.timer.display_time

        # Get tomato art filled based on progress
        if self.timer.phase == Phase.IDLE:
            progress = 0.0
        elif is_break:
            progress = 1.0
        else:
            progress = self.timer.progress
        tomato_lines = get_tomato_progress(progress)

        # Layout: label(1) + gap(1) + timer(1) + gap(1) + tomato(15) + gap(1) + session(1) + gap(1) + nav(1)
        total_height = 1 + 1 + 1 + 1 + len(tomato_lines) + 1 + 1 + 1 + 1
        start_y = max(0, (h - total_height) // 2)
        y = start_y

        # Phase label
        label = self.timer.phase_label
        if is_paused and self.timer.phase != Phase.IDLE:
            label = "PAUSED"
        label_color = curses.color_pair(COLOR_MAP.get(C_LABEL, PAIR_RED)) | curses.A_BOLD
        safe_addstr(win, y, (w - len(label)) // 2, label, label_color)
        y += 2

        # Timer display
        time_attr = curses.color_pair(PAIR_YELLOW) | curses.A_BOLD
        if flashing:
            time_attr = curses.color_pair(PAIR_RED) | curses.A_BOLD
        safe_addstr(win, y, (w - len(time_str)) // 2, time_str, time_attr)
        y += 2

        # Tomato art — per-character coloring
        for line, color_mask in tomato_lines:
            cx = (w - len(line)) // 2
            for j, (ch, cm) in enumerate(zip(line, color_mask)):
                if cm == 'S':
                    attr = curses.color_pair(PAIR_GREEN)
                elif cm == 'R':
                    attr = curses.color_pair(PAIR_RED)
                else:
                    attr = curses.color_pair(PAIR_WHITE)
                safe_addstr(win, y, cx + j, ch, attr)
            y += 1

        y += 2

        # Session counter
        if self.timer.phase != Phase.IDLE:
            sess = f"Session {self.timer.completed_sessions + (1 if self.timer.phase == Phase.WORK else 0)} of {self.config.sessions_before_long_break}"
            safe_addstr(win, y, (w - len(sess)) // 2, sess, curses.color_pair(PAIR_WHITE))
        else:
            today = self.stats.get_today()
            info = f"Today: {today.completed_sessions} sessions | {today.total_focus_minutes}m focus"
            safe_addstr(win, y, (w - len(info)) // 2, info, curses.color_pair(PAIR_WHITE))
        y += 2

        # Navigation bar
        if self.timer.phase == Phase.IDLE:
            nav = "[Space] Start   [2] Stats   [3] Settings   [Q] Quit"
        else:
            nav = "[Space] Pause   [S] Skip   [R] Reset   [Q] Quit"
            if is_paused:
                nav = "[Space] Resume  [S] Skip   [R] Reset   [Q] Quit"
        safe_addstr(win, h - 1, (w - len(nav)) // 2, nav, curses.color_pair(PAIR_CYAN))

        # Tab bar at top
        self._draw_tab_bar(win, w)

    # ------------------------------------------------------------------
    # Stats screen
    # ------------------------------------------------------------------

    def _draw_stats(self, win) -> None:
        h, w = win.getmaxyx()
        self._draw_tab_bar(win, w)

        y = 2

        # Title
        title = "STATISTICS"
        safe_addstr(win, y, (w - len(title)) // 2, title, curses.color_pair(PAIR_RED) | curses.A_BOLD)
        y += 2

        # Today's summary
        today = self.stats.get_today()
        safe_addstr(win, y, 4, "Today", curses.color_pair(PAIR_YELLOW) | curses.A_BOLD)
        y += 1
        safe_addstr(win, y, 6, f"Sessions completed: {today.completed_sessions}", curses.color_pair(PAIR_WHITE))
        y += 1
        hrs = today.total_focus_minutes // 60
        mins = today.total_focus_minutes % 60
        safe_addstr(win, y, 6, f"Focus time: {hrs}h {mins}m", curses.color_pair(PAIR_WHITE))
        y += 2

        # Streak
        streak = self.stats.current_streak()
        streak_str = f"Current streak: {streak} day{'s' if streak != 1 else ''}"
        safe_addstr(win, y, 4, streak_str, curses.color_pair(PAIR_MAGENTA) | curses.A_BOLD)
        y += 2

        # Weekly bar chart
        week = self.stats.get_week(self.stats_week_offset)
        if self.stats_week_offset == 0:
            week_label = "This Week"
        else:
            monday_date = week[0].date
            week_label = f"Week of {monday_date}"
        safe_addstr(win, y, 4, week_label, curses.color_pair(PAIR_YELLOW) | curses.A_BOLD)
        y += 1

        max_sessions = max((r.completed_sessions for r in week), default=0) or 1
        chart_height = min(8, h - y - 8)
        chart_height = max(chart_height, 3)
        bar_width = 3
        gap = 2
        total_chart_w = 7 * bar_width + 6 * gap
        chart_x = max(4, (w - total_chart_w) // 2)
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        for i, record in enumerate(week):
            x = chart_x + i * (bar_width + gap)
            bar_h = int((record.completed_sessions / max_sessions) * chart_height) if max_sessions > 0 else 0

            for row in range(chart_height):
                ry = y + chart_height - 1 - row
                if row < bar_h:
                    safe_addstr(win, ry, x, "|||", curses.color_pair(PAIR_RED) | curses.A_BOLD)
                else:
                    safe_addstr(win, ry, x, " . ", curses.color_pair(PAIR_WHITE))

            # Day label
            safe_addstr(win, y + chart_height, x, day_names[i], curses.color_pair(PAIR_CYAN))

            # Count above bar
            if record.completed_sessions > 0:
                count = str(record.completed_sessions)
                safe_addstr(win, y + chart_height - bar_h - 1, x, count.center(bar_width),
                           curses.color_pair(PAIR_YELLOW))

        y += chart_height + 2

        # All-time totals
        totals = self.stats.get_totals()
        safe_addstr(win, y, 4, "All Time", curses.color_pair(PAIR_YELLOW) | curses.A_BOLD)
        y += 1
        safe_addstr(win, y, 6, f"Total sessions: {totals['total_sessions']}", curses.color_pair(PAIR_WHITE))
        y += 1
        t_hrs = totals["total_focus_minutes"] // 60
        t_mins = totals["total_focus_minutes"] % 60
        safe_addstr(win, y, 6, f"Total focus: {t_hrs}h {t_mins}m", curses.color_pair(PAIR_WHITE))
        y += 1
        safe_addstr(win, y, 6, f"Active days: {totals['active_days']}", curses.color_pair(PAIR_WHITE))

        # Nav
        nav = "[</>] Navigate weeks   [1] Timer   [3] Settings   [Q] Quit"
        safe_addstr(win, h - 1, (w - len(nav)) // 2, nav, curses.color_pair(PAIR_CYAN))

    # ------------------------------------------------------------------
    # Settings screen
    # ------------------------------------------------------------------

    def _settings_fields(self):
        return [
            ("work_minutes", "Work Duration (min)", 1, 90),
            ("short_break_minutes", "Short Break (min)", 1, 30),
            ("long_break_minutes", "Long Break (min)", 1, 60),
            ("sessions_before_long_break", "Sessions Before Long Break", 1, 10),
            ("daily_goal", "Daily Goal (sessions)", 1, 20),
            ("sound_enabled", "Sound", 0, 1),
        ]

    def _draw_settings(self, win) -> None:
        h, w = win.getmaxyx()
        self._draw_tab_bar(win, w)

        y = 2
        title = "SETTINGS"
        safe_addstr(win, y, (w - len(title)) // 2, title, curses.color_pair(PAIR_RED) | curses.A_BOLD)
        y += 2

        fields = self._settings_fields()
        for i, (name, label, min_v, max_v) in enumerate(fields):
            val = self.settings_values[name]
            is_selected = i == self.settings_cursor

            if is_selected:
                marker = ">"
                attr = curses.color_pair(PAIR_HIGHLIGHT) | curses.A_BOLD
            else:
                marker = " "
                attr = curses.color_pair(PAIR_WHITE)

            if isinstance(val, bool):
                val_str = "ON" if val else "OFF"
            else:
                val_str = str(val)

            line = f" {marker} {label}"
            safe_addstr(win, y + i * 2, 4, line, attr)

            val_x = w - 16
            if is_selected and self.settings_editing:
                # Show edit buffer with cursor
                buf = self.settings_edit_buf
                display = f"  {buf}_   "
                safe_addstr(win, y + i * 2, val_x, display,
                           curses.color_pair(PAIR_GREEN) | curses.A_BOLD)
            elif is_selected:
                display = f"< {val_str:^5} >"
                safe_addstr(win, y + i * 2, val_x, display,
                           curses.color_pair(PAIR_YELLOW) | curses.A_BOLD)
            else:
                safe_addstr(win, y + i * 2, val_x + 2, f"{val_str:^5}",
                           curses.color_pair(PAIR_CYAN))

        y += len(fields) * 2 + 1
        if self.settings_editing:
            hint = "Type a number, Enter to confirm, Esc to cancel"
        else:
            hint = "←/→ to step, Space to type a custom value"
        safe_addstr(win, y, (w - len(hint)) // 2, hint, curses.color_pair(PAIR_WHITE))

        nav = "[Enter] Save   [Esc] Cancel   [1] Timer   [2] Stats   [Q] Quit"
        safe_addstr(win, h - 1, (w - len(nav)) // 2, nav, curses.color_pair(PAIR_CYAN))

    # ------------------------------------------------------------------
    # Common UI elements
    # ------------------------------------------------------------------

    def _draw_tab_bar(self, win, w: int) -> None:
        tabs = [("1:Timer", "timer"), ("2:Stats", "stats"), ("3:Settings", "settings")]
        tab_str_parts = []
        for label, name in tabs:
            if name == self.screen:
                tab_str_parts.append(f"[{label}]")
            else:
                tab_str_parts.append(f" {label} ")
        tab_str = "  ".join(tab_str_parts)
        x = (w - len(tab_str)) // 2
        for i, (label, name) in enumerate(tabs):
            part = tab_str_parts[i]
            if name == self.screen:
                attr = curses.color_pair(PAIR_RED) | curses.A_BOLD
            else:
                attr = curses.color_pair(PAIR_WHITE)
            safe_addstr(win, 0, x, part, attr)
            x += len(part) + 2

    def _draw_too_small(self, win, h: int, w: int) -> None:
        win.erase()
        msg = f"Terminal too small ({w}x{h})"
        msg2 = f"Need at least {MIN_WIDTH}x{MIN_HEIGHT}"
        safe_addstr(win, h // 2 - 1, max(0, (w - len(msg)) // 2), msg, curses.color_pair(PAIR_RED))
        safe_addstr(win, h // 2, max(0, (w - len(msg2)) // 2), msg2, curses.color_pair(PAIR_WHITE))
        win.refresh()
