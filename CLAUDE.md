# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tomodoro is a terminal-based pomodoro timer built with Python curses. It features an animated ASCII tomato (braille art) that fills up as focus sessions progress, screen/keyboard brightness control during breaks (macOS-only via private frameworks), sound notifications, and session statistics tracking.

## Commands

```bash
# Install in editable mode
pip install -e .

# Run the app
python -m tomodoro
# or after pip install:
tomodoro
```

There are no tests, linter, or CI configured.

## Architecture

**Entry point:** `tomodoro/__main__.py` → creates `App` and runs it via `curses.wrapper`.

**Core modules:**

- `ui.py` — `App` class: main loop (~60 FPS), screen routing (timer/stats/settings), all curses rendering and key handling. This is the largest file and where most UI changes happen.
- `timer.py` — `TimerEngine`: phase state machine (IDLE → WORK → SHORT_BREAK/LONG_BREAK → WORK…), uses `time.monotonic()` for tick-based countdown. Fires `on_phase_complete` callback.
- `config.py` — `Config` dataclass, persisted to `~/.config/tomodoro/config.json`.
- `stats.py` — `StatsStore` with `DailyRecord` entries, persisted to `~/.config/tomodoro/stats.json`. Provides daily/weekly/all-time aggregations and streak calculation.
- `art.py` — Braille tomato art with per-character color masks (stem=green, body=red). `get_tomato_progress()` reveals characters bottom-up based on a 0.0–1.0 progress float.
- `brightness.py` / `keyboard_backlight.py` — macOS-only hardware control via ctypes into private frameworks (DisplayServices, CoreBrightness). Screen dims to 0 during breaks; keyboard backlight shows break progress.
- `sounds/` — WAV files played via `afplay` subprocess. `trumpet.wav` on work complete, `sad_trumpet.wav` on break complete.

**Key design patterns:**

- The `App` class owns all state and delegates timing logic to `TimerEngine` via composition.
- Phase transitions trigger the `on_phase_complete` callback, which handles stats recording, brightness changes, and sound playback.
- All curses writes go through `safe_addstr()` to handle terminal boundary edge cases.
- No external dependencies — stdlib only (curses, ctypes, json, subprocess).
