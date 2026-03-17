import json
import os
from pathlib import Path
from typing import Optional

from models.day_entry import DayEntry


def _get_storage_path() -> Path:
    """Return path to the JSON data file (in %APPDATA%/ChogoenCal or ~/ChogoenCal)."""
    app_data = os.getenv("APPDATA") or os.path.expanduser("~")
    storage_dir = Path(app_data) / "ChogoenCal"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir / "data.json"


def _load_all() -> dict:
    path = _get_storage_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_all(data: dict) -> None:
    path = _get_storage_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"[저장 실패] {exc}")


def load_month_state(year: int, month: int) -> Optional[dict]:
    """Return saved state for the given year/month, or None if not found."""
    key = f"{year:04d}-{month:02d}"
    return _load_all().get(key)


def save_month_state(
    year: int,
    month: int,
    entries: list[DayEntry],
    target_minutes: int,
    daily_max_minutes: int,
    base_actual_minutes: int = 0,
) -> None:
    """Persist state for the given year/month."""
    key = f"{year:04d}-{month:02d}"
    data = _load_all()
    data[key] = {
        "target_minutes": target_minutes,
        "daily_max_minutes": daily_max_minutes,
        "base_actual_minutes": base_actual_minutes,
        "entries": [e.to_dict() for e in entries],
    }
    _save_all(data)
