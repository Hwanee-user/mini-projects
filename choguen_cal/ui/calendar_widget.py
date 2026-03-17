import calendar
from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models.day_entry import DayEntry


def _fmt_time(minutes: int) -> str:
    """Format minutes as '4시간' (no minutes) or '4시간 30분' (with minutes)."""
    h, m = divmod(minutes, 60)
    if m == 0:
        return f"{h}시간"
    return f"{h}시간 {m:02d}분"


# ── Day cell ─────────────────────────────────────────────────────────────────

class DayCell(QFrame):
    """Single day tile in the monthly calendar grid."""

    clicked = Signal(date)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._entry: DayEntry | None = None
        self._is_selected = False
        self._is_today = False
        self._setup_ui()
        self.setFixedHeight(108)
        self.setCursor(Qt.PointingHandCursor)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(1)

        # Day number
        self.day_label = QLabel()
        self.day_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        bold_font = QFont()
        bold_font.setBold(True)
        bold_font.setPointSize(13)
        self.day_label.setFont(bold_font)

        # Holiday name (shown below day number when applicable)
        self.holiday_label = QLabel()
        self.holiday_label.setAlignment(Qt.AlignCenter)
        self.holiday_label.setStyleSheet("font-size: 13px; color: #C62828;")
        self.holiday_label.setWordWrap(True)

        # Planned overtime (blue)
        self.planned_label = QLabel()
        self.planned_label.setAlignment(Qt.AlignCenter)
        self.planned_label.setStyleSheet("font-size: 13px; color: #1565C0;")

        # Actual overtime (green)
        self.actual_label = QLabel()
        self.actual_label.setAlignment(Qt.AlignCenter)
        self.actual_label.setStyleSheet("font-size: 13px; color: #2E7D32;")

        # Tags line (excluded / etc.)
        self.tag_label = QLabel()
        self.tag_label.setAlignment(Qt.AlignCenter)
        self.tag_label.setStyleSheet("font-size: 13px; color: #9E9E9E;")

        layout.addWidget(self.day_label)
        layout.addWidget(self.holiday_label)
        layout.addWidget(self.planned_label)
        layout.addWidget(self.actual_label)
        layout.addWidget(self.tag_label)
        layout.addStretch()

    # ── Public interface ──────────────────────────────────────────────

    def update_entry(
        self,
        entry: DayEntry | None,
        is_selected: bool,
        is_today: bool,
    ) -> None:
        self._entry = entry
        self._is_selected = is_selected
        self._is_today = is_today
        self._refresh()

    # ── Internal rendering ────────────────────────────────────────────

    def _refresh(self) -> None:
        if self._entry is None:
            self._clear()
            return

        e = self._entry
        today = date.today()
        is_past = e.date < today

        # Day number colour
        wd = e.date.weekday()
        if e.is_holiday or wd == 6:  # Sunday / holiday → red
            day_color = "#C62828"
        elif wd == 5:  # Saturday → blue
            day_color = "#1565C0"
        else:
            day_color = "#212121"
        self.day_label.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {day_color};"
        )
        self.day_label.setText(str(e.date.day))

        # Holiday name
        if e.is_holiday and e.holiday_name:
            name = e.holiday_name
            if len(name) > 6:
                name = name[:5] + "…"
            self.holiday_label.setText(name)
            self.holiday_label.setVisible(True)
        else:
            self.holiday_label.setVisible(False)

        # Planned (orange = manual lock, blue = auto-calculated)
        if e.planned_minutes > 0:
            self.planned_label.setText(f"예정 {_fmt_time(e.planned_minutes)}")
            if e.is_planned_manual:
                self.planned_label.setStyleSheet("font-size: 13px; color: #E65100;")
            else:
                self.planned_label.setStyleSheet("font-size: 13px; color: #1565C0;")
            self.planned_label.setVisible(True)
        else:
            self.planned_label.setVisible(False)

        # Actual
        if e.actual_minutes > 0:
            self.actual_label.setText(f"실제 {_fmt_time(e.actual_minutes)}")
            self.actual_label.setVisible(True)
        else:
            self.actual_label.setVisible(False)

        # Tags
        tags = []
        if not e.included:
            tags.append("제외")
        if is_past and not e.is_weekend and not e.is_holiday:
            tags.append("과거")
        self.tag_label.setText("  ".join(tags))
        self.tag_label.setVisible(bool(tags))

        # Background & border
        bg = self._background_color(e, is_past)
        if self._is_selected:
            border = "2px solid #1565C0"
        elif self._is_today:
            border = "2px solid #FF6F00"
        else:
            border = "1px solid #BDBDBD"

        self.setStyleSheet(
            f"QFrame {{ background-color: {bg}; border: {border}; border-radius: 4px; }}"
        )

    def _clear(self) -> None:
        self.day_label.setText("")
        self.holiday_label.setVisible(False)
        self.planned_label.setVisible(False)
        self.actual_label.setVisible(False)
        self.tag_label.setVisible(False)
        self.setStyleSheet(
            "QFrame { background-color: #F5F5F5; border: none; }"
        )

    @staticmethod
    def _background_color(e: DayEntry, is_past: bool) -> str:
        if not e.included:
            return "#EEEEEE"          # gray  → excluded
        if e.is_holiday:
            return "#FFEBEE"          # light red → holiday
        if e.is_weekend:
            return "#FFF8E1"          # light yellow → weekend
        if is_past:
            return "#FAFAFA"          # very light → past weekday
        return "#FFFFFF"              # white → normal future weekday

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if self._entry is not None:
            self.clicked.emit(self._entry.date)
        super().mousePressEvent(event)


# ── Calendar widget ───────────────────────────────────────────────────────────

class CalendarWidget(QWidget):
    """Monthly calendar grid with navigation."""

    date_selected = Signal(date)
    prev_month = Signal()
    next_month = Signal()

    _WEEKDAY_HEADERS = ["일", "월", "화", "수", "목", "금", "토"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cells: list[DayCell] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # ── Navigation header ─────────────────────────────────────────
        nav_widget = QWidget()
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)

        self.prev_btn = QPushButton("◀ 이전 달")
        self.prev_btn.setFixedWidth(90)
        self.month_label = QLabel()
        self.month_label.setAlignment(Qt.AlignCenter)
        self.month_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.next_btn = QPushButton("다음 달 ▶")
        self.next_btn.setFixedWidth(90)

        self.prev_btn.clicked.connect(self.prev_month.emit)
        self.next_btn.clicked.connect(self.next_month.emit)

        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.month_label, 1)
        nav_layout.addWidget(self.next_btn)
        main_layout.addWidget(nav_widget)

        # ── Weekday header row ────────────────────────────────────────
        header_widget = QWidget()
        header_layout = QGridLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)
        for col, name in enumerate(self._WEEKDAY_HEADERS):
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignCenter)
            if col == 0:   # 일요일 (Sunday) → red
                lbl.setStyleSheet("font-weight: bold; color: #C62828; font-size: 13px;")
            elif col == 6:  # 토요일 (Saturday) → blue
                lbl.setStyleSheet("font-weight: bold; color: #1565C0; font-size: 13px;")
            else:
                lbl.setStyleSheet("font-weight: bold; font-size: 13px;")
            header_layout.addWidget(lbl, 0, col)
        main_layout.addWidget(header_widget)

        # ── Day-cell grid (6 rows × 7 cols = 42 cells) ───────────────
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(2)

        for row in range(6):
            for col in range(7):
                cell = DayCell()
                cell.clicked.connect(self.date_selected.emit)
                self._cells.append(cell)
                self.grid_layout.addWidget(cell, row, col)

        main_layout.addWidget(self.grid_widget, 1)

    # ── Public interface ──────────────────────────────────────────────

    def update_month(
        self,
        year: int,
        month: int,
        entries: list[DayEntry],
        selected_date: date | None,
    ) -> None:
        self.month_label.setText(f"{year}년 {month}월")

        today = date.today()
        entry_map: dict[date, DayEntry] = {e.date: e for e in entries}
        first_weekday, days_in_month = calendar.monthrange(year, month)
        # Python's calendar.monthrange: 0=Monday … 6=Sunday
        # Convert to Sunday-start (Sun=0, Mon=1 … Sat=6)
        first_col = (first_weekday + 1) % 7

        cell_idx = 0

        # Empty cells before the 1st
        for _ in range(first_col):
            self._cells[cell_idx].update_entry(None, False, False)
            cell_idx += 1

        # Day cells
        for day in range(1, days_in_month + 1):
            d = date(year, month, day)
            entry = entry_map.get(d)
            self._cells[cell_idx].update_entry(
                entry,
                is_selected=(d == selected_date),
                is_today=(d == today),
            )
            cell_idx += 1

        # Remaining empty cells
        while cell_idx < 42:
            self._cells[cell_idx].update_entry(None, False, False)
            cell_idx += 1
