from dataclasses import dataclass
from datetime import date


@dataclass
class DayEntry:
    date: date
    is_weekend: bool = False
    is_holiday: bool = False
    holiday_name: str = ""
    included: bool = True            # whether this day is an auto-assign target
    planned_minutes: int = 0         # planned overtime (auto-calc or manual)
    is_planned_manual: bool = False  # True = user has locked planned_minutes manually
    actual_minutes: int = 0          # user-entered actual overtime

    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "is_weekend": self.is_weekend,
            "is_holiday": self.is_holiday,
            "holiday_name": self.holiday_name,
            "included": self.included,
            "planned_minutes": self.planned_minutes,
            "is_planned_manual": self.is_planned_manual,
            "actual_minutes": self.actual_minutes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DayEntry":
        return cls(
            date=date.fromisoformat(data["date"]),
            is_weekend=data.get("is_weekend", False),
            is_holiday=data.get("is_holiday", False),
            holiday_name=data.get("holiday_name", ""),
            included=data.get("included", True),
            planned_minutes=data.get("planned_minutes", 0),
            is_planned_manual=data.get("is_planned_manual", False),
            actual_minutes=data.get("actual_minutes", 0),
        )
