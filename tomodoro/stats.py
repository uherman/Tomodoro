import json
from dataclasses import dataclass, asdict, field
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List

STATS_FILE = Path.home() / ".config" / "tomodoro" / "stats.json"


@dataclass
class DailyRecord:
    date: str
    completed_sessions: int = 0
    total_focus_seconds: int = 0

    @property
    def total_focus_minutes(self) -> int:
        return self.total_focus_seconds // 60


class StatsStore:
    def __init__(self, records: Dict[str, DailyRecord] = None):
        self.records: Dict[str, DailyRecord] = records or {}

    @classmethod
    def load(cls) -> "StatsStore":
        if STATS_FILE.exists():
            try:
                raw = json.loads(STATS_FILE.read_text())
                records = {}
                for k, v in raw.get("records", {}).items():
                    records[k] = DailyRecord(**v)
                return cls(records=records)
            except (json.JSONDecodeError, TypeError):
                pass
        return cls()

    def save(self) -> None:
        STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {"records": {k: asdict(v) for k, v in self.records.items()}}
        STATS_FILE.write_text(json.dumps(data, indent=2))

    def record_session(self, focus_seconds: int) -> None:
        today = date.today().isoformat()
        if today not in self.records:
            self.records[today] = DailyRecord(date=today)
        self.records[today].completed_sessions += 1
        self.records[today].total_focus_seconds += focus_seconds
        self.save()

    def get_today(self) -> DailyRecord:
        today = date.today().isoformat()
        return self.records.get(today, DailyRecord(date=today))

    def get_week(self, week_offset: int = 0) -> List[DailyRecord]:
        today = date.today()
        monday = today - timedelta(days=today.weekday()) - timedelta(weeks=week_offset)
        result = []
        for i in range(7):
            d = (monday + timedelta(days=i)).isoformat()
            result.append(self.records.get(d, DailyRecord(date=d)))
        return result

    def current_streak(self) -> int:
        streak = 0
        d = date.today()
        # Allow today to have 0 sessions (day not started yet)
        if d.isoformat() not in self.records or self.records[d.isoformat()].completed_sessions == 0:
            d -= timedelta(days=1)
        while True:
            key = d.isoformat()
            if key in self.records and self.records[key].completed_sessions > 0:
                streak += 1
                d -= timedelta(days=1)
            else:
                break
        return streak

    def get_totals(self) -> dict:
        total_sessions = 0
        total_focus = 0
        for rec in self.records.values():
            total_sessions += rec.completed_sessions
            total_focus += rec.total_focus_seconds
        return {
            "total_sessions": total_sessions,
            "total_focus_minutes": total_focus // 60,
            "active_days": len([r for r in self.records.values() if r.completed_sessions > 0]),
        }
