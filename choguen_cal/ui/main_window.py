import calendar
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QSplitter, QWidget

from models.day_entry import DayEntry
from scheduler.calculator import recalculate
from scheduler.holidays import get_holiday_name, is_holiday
from storage.json_store import load_month_state, save_month_state
from ui.calendar_widget import CalendarWidget
from ui.detail_panel import DetailPanel

DEFAULT_TARGET_MINUTES = 57 * 60   # 57 hours
DEFAULT_DAILY_MAX_MINUTES = 4 * 60  # 4 hours


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("초과근무 일정 자동 생성기")
        self.resize(1200, 720)

        today = date.today()
        self.current_year = today.year
        self.current_month = today.month
        self.target_minutes = DEFAULT_TARGET_MINUTES
        self.daily_max_minutes = DEFAULT_DAILY_MAX_MINUTES
        self.base_actual_minutes = 0        # lump-sum prior actual (설정 패널 입력)
        self.entries: list[DayEntry] = []
        self.selected_date: date | None = None
        self.summary: dict = {}

        self._setup_ui()
        self._load_month(self.current_year, self.current_month)

    # ── UI setup ──────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)

        self.calendar_widget = CalendarWidget()
        self.detail_panel = DetailPanel()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.calendar_widget)
        splitter.addWidget(self.detail_panel)
        splitter.setSizes([720, 480])

        layout.addWidget(splitter)

        # Connect signals
        self.calendar_widget.date_selected.connect(self._on_date_selected)
        self.calendar_widget.prev_month.connect(self._on_prev_month)
        self.calendar_widget.next_month.connect(self._on_next_month)

        self.detail_panel.target_changed.connect(self._on_target_changed)
        self.detail_panel.daily_max_changed.connect(self._on_daily_max_changed)
        self.detail_panel.base_actual_changed.connect(self._on_base_actual_changed)
        self.detail_panel.actual_changed.connect(self._on_actual_changed)
        self.detail_panel.included_toggled.connect(self._on_included_toggled)
        self.detail_panel.planned_changed.connect(self._on_planned_changed)
        self.detail_panel.planned_reset.connect(self._on_planned_reset)

    # ── Month loading ─────────────────────────────────────────────────

    def _load_month(self, year: int, month: int) -> None:
        saved = load_month_state(year, month)

        if saved:
            self.target_minutes = saved.get("target_minutes", DEFAULT_TARGET_MINUTES)
            self.daily_max_minutes = saved.get("daily_max_minutes", DEFAULT_DAILY_MAX_MINUTES)
            self.base_actual_minutes = saved.get("base_actual_minutes", 0)
            saved_entries = {row["date"]: row for row in saved.get("entries", [])}
        else:
            saved_entries = {}

        self.current_year = year
        self.current_month = month
        self.entries = self._build_month_entries(year, month, saved_entries)
        self._recalculate_and_refresh()

    def _build_month_entries(
        self,
        year: int,
        month: int,
        saved_entries: dict,
    ) -> list[DayEntry]:
        """Build a DayEntry list for every calendar day in the given month."""
        today = date.today()
        _, days_in_month = calendar.monthrange(year, month)
        entries: list[DayEntry] = []

        for day in range(1, days_in_month + 1):
            d = date(year, month, day)
            wd = d.weekday()          # 0=Mon … 6=Sun
            is_wknd = wd >= 5
            is_hday = is_holiday(d)
            holiday_nm = get_holiday_name(d)

            # Default: included only if it is a future weekday with no holiday
            default_included = (not is_wknd) and (not is_hday) and (d > today)

            saved = saved_entries.get(d.isoformat())
            if saved:
                is_manual = saved.get("is_planned_manual", False)
                entry = DayEntry(
                    date=d,
                    is_weekend=is_wknd,
                    is_holiday=is_hday,
                    holiday_name=holiday_nm,
                    included=saved.get("included", default_included),
                    # Restore manual planned value; auto-planned will be recalculated
                    planned_minutes=saved.get("planned_minutes", 0) if is_manual else 0,
                    is_planned_manual=is_manual,
                    actual_minutes=saved.get("actual_minutes", 0),
                )
            else:
                entry = DayEntry(
                    date=d,
                    is_weekend=is_wknd,
                    is_holiday=is_hday,
                    holiday_name=holiday_nm,
                    included=default_included,
                    planned_minutes=0,
                    actual_minutes=0,
                )
            entries.append(entry)

        return entries

    # ── Core update cycle ─────────────────────────────────────────────

    def _recalculate_and_refresh(self) -> None:
        today = date.today()
        self.summary = recalculate(
            self.entries,
            self.target_minutes,
            self.daily_max_minutes,
            today,
            self.base_actual_minutes,
        )

        self.calendar_widget.update_month(
            self.current_year,
            self.current_month,
            self.entries,
            self.selected_date,
        )

        self.detail_panel.update_state(
            year=self.current_year,
            month=self.current_month,
            target_minutes=self.target_minutes,
            daily_max_minutes=self.daily_max_minutes,
            base_actual_minutes=self.base_actual_minutes,
            summary=self.summary,
            selected_entry=self._get_selected_entry(),
        )

        save_month_state(
            self.current_year,
            self.current_month,
            self.entries,
            self.target_minutes,
            self.daily_max_minutes,
            self.base_actual_minutes,
        )

    def _get_selected_entry(self) -> DayEntry | None:
        if self.selected_date is None:
            return None
        for e in self.entries:
            if e.date == self.selected_date:
                return e
        return None

    # ── Signal handlers ───────────────────────────────────────────────

    def _on_date_selected(self, d: date) -> None:
        self.selected_date = d
        self._recalculate_and_refresh()

    def _on_prev_month(self) -> None:
        self.selected_date = None
        if self.current_month == 1:
            self._load_month(self.current_year - 1, 12)
        else:
            self._load_month(self.current_year, self.current_month - 1)

    def _on_next_month(self) -> None:
        self.selected_date = None
        if self.current_month == 12:
            self._load_month(self.current_year + 1, 1)
        else:
            self._load_month(self.current_year, self.current_month + 1)

    def _on_target_changed(self, minutes: int) -> None:
        self.target_minutes = minutes
        self._recalculate_and_refresh()

    def _on_daily_max_changed(self, minutes: int) -> None:
        self.daily_max_minutes = minutes
        self._recalculate_and_refresh()

    def _on_base_actual_changed(self, minutes: int) -> None:
        self.base_actual_minutes = minutes
        self._recalculate_and_refresh()

    def _on_actual_changed(self, d: date, minutes: int) -> None:
        for entry in self.entries:
            if entry.date == d:
                entry.actual_minutes = minutes
                break
        self._recalculate_and_refresh()

    def _on_included_toggled(self, d: date) -> None:
        for entry in self.entries:
            if entry.date == d:
                entry.included = not entry.included
                if not entry.included:
                    # Clear manual planned when a day is excluded
                    entry.is_planned_manual = False
                    entry.planned_minutes = 0
                break
        self._recalculate_and_refresh()

    def _on_planned_changed(self, d: date, minutes: int) -> None:
        for entry in self.entries:
            if entry.date == d:
                entry.planned_minutes = minutes
                entry.is_planned_manual = True
                break
        self._recalculate_and_refresh()

    def _on_planned_reset(self, d: date) -> None:
        for entry in self.entries:
            if entry.date == d:
                entry.is_planned_manual = False
                entry.planned_minutes = 0  # will be recalculated
                break
        self._recalculate_and_refresh()
