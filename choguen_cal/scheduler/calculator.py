from datetime import date
from typing import List

from models.day_entry import DayEntry


def minutes_to_str(minutes: int) -> str:
    """Convert total minutes to '시간 분' string."""
    if minutes < 0:
        return f"-{minutes_to_str(-minutes)}"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}시간 {mins:02d}분"


def _floor_to_10(minutes: int) -> int:
    """Floor minutes down to the nearest 10-minute boundary."""
    return (minutes // 10) * 10


def _distribute_minutes(
    days: List[DayEntry],
    total_to_distribute: int,
    daily_max_minutes: int,
) -> None:
    """
    Distribute total_to_distribute across days in-place.

    Strategy: fill each day with daily_max first (front-to-back).
    The last partial day receives the remainder.
    All values are multiples of 10 minutes.
    """
    n = len(days)
    if n == 0:
        return

    for d in days:
        d.planned_minutes = 0

    if total_to_distribute <= 0 or daily_max_minutes <= 0:
        return

    # Cap at the absolute maximum assignable
    max_assignable = n * daily_max_minutes
    total = min(total_to_distribute, max_assignable)

    # Work in 10-minute quanta
    total_10 = _floor_to_10(total)
    if total_10 <= 0:
        return

    daily_max_10 = _floor_to_10(daily_max_minutes)
    if daily_max_10 <= 0:
        daily_max_10 = daily_max_minutes

    # Fill from the first day with the max; last partial day gets the remainder
    remaining = total_10
    for d in days:
        if remaining <= 0:
            d.planned_minutes = 0
        elif remaining >= daily_max_10:
            d.planned_minutes = daily_max_10
            remaining -= daily_max_10
        else:
            d.planned_minutes = remaining  # partial last day (already a multiple of 10)
            remaining = 0


def recalculate(
    entries: List[DayEntry],
    target_minutes: int,
    daily_max_minutes: int,
    today: date,
    base_actual_minutes: int = 0,
) -> dict:
    """
    Recalculate the overtime schedule for a month.

    Modifies planned_minutes in each DayEntry in-place.
    Returns a summary dict with statistics and status messages.

    base_actual_minutes: overtime already accrued before per-day tracking began
                         (entered as a lump sum in the settings panel).
    """
    # 1. Reset planned for excluded / past days; leave manual future-included days intact
    for e in entries:
        if not e.included or e.date <= today:
            e.planned_minutes = 0
            e.is_planned_manual = False
        elif not e.is_planned_manual:
            e.planned_minutes = 0  # will be recalculated below

    # 2. Actual total: ALL days + lump-sum base entered in settings
    actual_total = sum(e.actual_minutes for e in entries) + base_actual_minutes

    # 3. Future included days (manual + auto)
    future_included: List[DayEntry] = [
        e for e in entries
        if e.included and e.date > today
    ]
    future_included_count = len(future_included)

    manual_future: List[DayEntry] = [e for e in future_included if e.is_planned_manual]
    auto_future: List[DayEntry] = [e for e in future_included if not e.is_planned_manual]

    manual_planned_sum = sum(e.planned_minutes for e in manual_future)

    # 4. Max achievable = actual + theoretical max for ALL future-included days
    max_possible_total = actual_total + future_included_count * daily_max_minutes

    # 5. Effective target
    effective_target = min(target_minutes, max_possible_total)

    # 6. Remaining to cover (across manual + auto planned)
    remaining = effective_target - actual_total

    status = ""
    warning = ""

    if remaining <= 0:
        # Target already met / exceeded — clear auto days
        for e in auto_future:
            e.planned_minutes = 0
        status = "🎉 초과 달성" if actual_total > target_minutes else "✅ 목표 달성"
    elif future_included_count == 0:
        warning = (
            f"⚠️ 배정 가능한 날짜가 없습니다. "
            f"목표까지 {minutes_to_str(remaining)} 부족합니다."
        )
    else:
        # How much is left for auto days after honouring manual allocations?
        remaining_for_auto = remaining - manual_planned_sum
        if remaining_for_auto <= 0:
            for e in auto_future:
                e.planned_minutes = 0
        elif auto_future:
            _distribute_minutes(auto_future, remaining_for_auto, daily_max_minutes)

    # 7. Planned total after distribution
    planned_total = sum(e.planned_minutes for e in entries)

    return {
        "actual_total": actual_total,
        "planned_total": planned_total,
        "original_target": target_minutes,
        "max_possible_total": max_possible_total,
        "effective_target": effective_target,
        "remaining": remaining,
        "future_included_count": future_included_count,
        "status": status,
        "warning": warning,
    }
