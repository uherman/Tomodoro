# Tomodoro

A terminal-based pomodoro timer with ASCII tomato art, built with Python curses.

![macOS](https://img.shields.io/badge/platform-macOS-lightgrey)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

## Features

- Animated ASCII tomato that fills up as your focus session progresses
- Work sessions, short breaks, and long breaks with configurable durations
- Automatic screen dimming during breaks (macOS)
- Keyboard backlight progress indicator during breaks
- Session statistics with daily, weekly, and all-time tracking
- Sound notifications (trumpet on session complete)
- Settings with arrow-key stepping and custom number input

## Installation

### Homebrew (recommended)

```bash
brew install uherman/tomodoro/tomodoro
```

### From source

```bash
git clone https://github.com/uherman/tomodoro.git
cd tomodoro
pip install -e .
```

## Usage

```bash
# Run directly
python -m tomodoro

# Or if installed via pip
tomodoro
```

## Controls

### Timer
| Key       | Action          |
|-----------|-----------------|
| `Space`   | Start / Pause / Resume |
| `S`       | Skip phase      |
| `R`       | Reset timer     |

### Navigation
| Key       | Action          |
|-----------|-----------------|
| `1`       | Timer screen    |
| `2`       | Stats screen    |
| `3`       | Settings screen |
| `Tab`     | Cycle screens   |
| `Q`       | Quit            |

### Settings
| Key       | Action                  |
|-----------|-------------------------|
| `↑` / `↓` | Select setting         |
| `←` / `→` | Step value by 1        |
| `Space`   | Type a custom value     |
| `Enter`   | Save settings           |
| `Esc`     | Cancel                  |

## Configuration

Settings are stored in `~/.config/tomodoro/config.json`:

| Setting                    | Default | Range  |
|----------------------------|---------|--------|
| Work Duration              | 25 min  | 1–90   |
| Short Break                | 5 min   | 1–30   |
| Long Break                 | 15 min  | 1–60   |
| Sessions Before Long Break | 4       | 1–10   |
| Daily Goal                 | 8       | 1–20   |
| Sound                      | ON      | ON/OFF |

## License

[MIT](LICENSE)
