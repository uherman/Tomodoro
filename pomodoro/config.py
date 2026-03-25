import dataclasses
import json
from dataclasses import dataclass, asdict
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "tomodoro"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class Config:
    work_minutes: int = 25
    short_break_minutes: int = 5
    long_break_minutes: int = 15
    sessions_before_long_break: int = 4
    daily_goal: int = 8
    sound_enabled: bool = True

    @classmethod
    def load(cls) -> "Config":
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
                known = {f.name for f in dataclasses.fields(cls)}
                return cls(**{k: v for k, v in data.items() if k in known})
            except (json.JSONDecodeError, TypeError):
                pass
        return cls()

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(asdict(self), indent=2))
