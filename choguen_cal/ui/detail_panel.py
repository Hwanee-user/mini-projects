from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from models.day_entry import DayEntry
from scheduler.calculator import minutes_to_str

_WEEKDAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]


class DetailPanel(QWidget):
    """Right-hand settings / summary / date-detail panel."""

    # Emitted when the user changes a setting or date data
    target_changed = Signal(int)        # new target in minutes
    daily_max_changed = Signal(int)     # new daily max in minutes
    base_actual_changed = Signal(int)   # new lump-sum prior actual in minutes
    actual_changed = Signal(date, int)  # (date, new actual minutes)
    included_toggled = Signal(date)
    planned_changed = Signal(date, int) # (date, manually-set planned minutes)
    planned_reset = Signal(date)        # reset planned to auto-calculation

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(370)
        self._current_entry: DayEntry | None = None
        self._setup_ui()

    # ── UI construction ───────────────────────────────────────────────

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Scroll area so it works on small screens
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # ── 사용법 토글 버튼 (최상단) ─────────────────────────────────
        self.help_toggle_btn = QPushButton("📖  사용법 보기  ▼")
        self.help_toggle_btn.setMinimumHeight(36)
        self.help_toggle_btn.setStyleSheet(
            "QPushButton { font-size: 13px; font-weight: bold; "
            "background-color: #E3F2FD; border: 1px solid #90CAF9; "
            "border-radius: 4px; text-align: left; padding-left: 10px; }"
            "QPushButton:hover { background-color: #BBDEFB; }"
        )
        self.help_toggle_btn.clicked.connect(self._toggle_help)
        layout.addWidget(self.help_toggle_btn)

        # ── 사용법 패널 (기본 숨김) ───────────────────────────────────
        self.help_group = self._build_help_group()
        self.help_group.setVisible(False)
        layout.addWidget(self.help_group)

        layout.addWidget(self._build_settings_group())
        layout.addWidget(self._build_summary_group())
        layout.addWidget(self._build_status_area())
        layout.addWidget(self._build_date_group())
        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

        # Connect settings spinboxes
        self.target_h_spin.valueChanged.connect(self._emit_target_changed)
        self.target_m_spin.valueChanged.connect(self._emit_target_changed)
        self.daily_h_spin.valueChanged.connect(self._emit_daily_max_changed)
        self.daily_m_spin.valueChanged.connect(self._emit_daily_max_changed)
        self.base_actual_h_spin.valueChanged.connect(self._emit_base_actual_changed)
        self.base_actual_m_spin.valueChanged.connect(self._emit_base_actual_changed)

        self._set_date_controls_enabled(False)

    def _build_settings_group(self) -> QGroupBox:
        group = QGroupBox("설정")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # Monthly target
        target_row = QHBoxLayout()
        target_row.addWidget(QLabel("월 목표:"))
        self.target_h_spin = QSpinBox()
        self.target_h_spin.setRange(0, 300)
        self.target_h_spin.setValue(57)
        self.target_h_spin.setSuffix(" 시간")
        self.target_m_spin = QSpinBox()
        self.target_m_spin.setRange(0, 59)
        self.target_m_spin.setValue(0)
        self.target_m_spin.setSuffix(" 분")
        target_row.addWidget(self.target_h_spin)
        target_row.addWidget(self.target_m_spin)
        target_row.addStretch()
        layout.addLayout(target_row)

        # Daily max
        daily_row = QHBoxLayout()
        daily_row.addWidget(QLabel("1일 최대:"))
        self.daily_h_spin = QSpinBox()
        self.daily_h_spin.setRange(0, 12)
        self.daily_h_spin.setValue(4)
        self.daily_h_spin.setSuffix(" 시간")
        self.daily_m_spin = QSpinBox()
        self.daily_m_spin.setRange(0, 59)
        self.daily_m_spin.setValue(0)
        self.daily_m_spin.setSuffix(" 분")
        daily_row.addWidget(self.daily_h_spin)
        daily_row.addWidget(self.daily_m_spin)
        daily_row.addStretch()
        layout.addLayout(daily_row)

        # Lump-sum prior actual (월 중 앱 시작 전 이미 기록된 초과근무 합계)
        from PySide6.QtWidgets import QFrame as _QFrame
        sep = _QFrame()
        sep.setFrameShape(_QFrame.HLine)
        sep.setStyleSheet("color: #BDBDBD;")
        layout.addWidget(sep)

        base_lbl = QLabel("이전 실적 누계:")
        base_lbl.setToolTip(
            "달력에 날짜별로 입력하기 전에 이미 진행된 초과근무 시간을\n"
            "여기에 일괄 입력하세요. 달력에는 반영되지 않지만\n"
            "월간 합계 계산에는 포함됩니다."
        )
        layout.addWidget(base_lbl)

        base_row = QHBoxLayout()
        self.base_actual_h_spin = QSpinBox()
        self.base_actual_h_spin.setRange(0, 300)
        self.base_actual_h_spin.setValue(0)
        self.base_actual_h_spin.setSuffix(" 시간")
        self.base_actual_m_spin = QSpinBox()
        self.base_actual_m_spin.setRange(0, 59)
        self.base_actual_m_spin.setValue(0)
        self.base_actual_m_spin.setSuffix(" 분")
        base_row.addWidget(self.base_actual_h_spin)
        base_row.addWidget(self.base_actual_m_spin)
        base_row.addStretch()
        layout.addLayout(base_row)

        return group

    def _build_summary_group(self) -> QGroupBox:
        group = QGroupBox("월간 요약")
        layout = QVBoxLayout(group)
        layout.setSpacing(5)

        self.original_target_lbl = self._stat_value_label()  # hidden — kept for calc reference
        self.actual_total_lbl = self._stat_value_label()
        self.planned_total_lbl = self._stat_value_label()
        self.expected_total_lbl = self._stat_value_label()   # 당월 예상 = 실제 + 예정
        self.remaining_lbl = self._stat_value_label()
        self.max_possible_lbl = self._stat_value_label()      # hidden
        self.effective_target_lbl = self._stat_value_label()  # hidden

        visible_rows = [
            ("이번달 목표 초과근무:", self.original_target_lbl),
            ("실제 초과근무 시간:", self.actual_total_lbl),
            ("예정 초과근무 시간:", self.planned_total_lbl),
            ("당월 예상 초과근무:", self.expected_total_lbl),
            ("남은 목표:", self.remaining_lbl),
        ]
        for key_text, val_lbl in visible_rows:
            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 0, 0, 0)
            key_lbl = QLabel(key_text)
            key_lbl.setMinimumWidth(140)
            row_l.addWidget(key_lbl)
            row_l.addWidget(val_lbl)
            row_l.addStretch()
            layout.addWidget(row_w)

        # 무료봉사 경고 라벨 (당월 예상이 목표 초과 시에만 표시)
        self.overage_warning_lbl = QLabel()
        self.overage_warning_lbl.setWordWrap(True)
        self.overage_warning_lbl.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #C62828; "
            "padding: 4px 0px 2px 0px;"
        )
        self.overage_warning_lbl.setVisible(False)
        layout.addWidget(self.overage_warning_lbl)

        return group

    def _build_status_area(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            "padding: 7px; background: #E8F5E9; border-radius: 4px; font-size: 13px;"
        )
        self.status_label.setVisible(False)

        self.warning_label = QLabel()
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet(
            "padding: 7px; background: #FFF3E0; border-radius: 4px; "
            "font-size: 13px; color: #E65100;"
        )
        self.warning_label.setVisible(False)

        layout.addWidget(self.status_label)
        layout.addWidget(self.warning_label)
        return container

    def _build_date_group(self) -> QGroupBox:
        self.date_group = QGroupBox("선택한 날짜")
        layout = QVBoxLayout(self.date_group)
        layout.setSpacing(8)

        self.date_info_label = QLabel("날짜를 선택하세요.")
        self.date_info_label.setWordWrap(True)
        self.date_info_label.setAlignment(Qt.AlignTop)
        self.date_info_label.setMinimumHeight(60)
        layout.addWidget(self.date_info_label)

        # Include / Exclude toggle button
        self.toggle_btn = QPushButton("포함/제외 토글")
        self.toggle_btn.setMinimumHeight(32)
        self.toggle_btn.clicked.connect(self._on_toggle_clicked)
        layout.addWidget(self.toggle_btn)

        # ── Manual planned time section ───────────────────────────────
        from PySide6.QtWidgets import QFrame as _QF
        sep1 = _QF()
        sep1.setFrameShape(_QF.HLine)
        sep1.setStyleSheet("color: #BDBDBD;")
        layout.addWidget(sep1)

        planned_header = QLabel("예정 시간 수동 설정:")
        planned_header.setStyleSheet("font-weight: bold; color: #424242;")
        layout.addWidget(planned_header)

        planned_spin_row = QHBoxLayout()
        self.planned_h_spin = QSpinBox()
        self.planned_h_spin.setRange(0, 12)
        self.planned_h_spin.setSuffix(" 시간")
        self.planned_m_spin = QSpinBox()
        self.planned_m_spin.setRange(0, 59)
        self.planned_m_spin.setSingleStep(10)
        self.planned_m_spin.setSuffix(" 분")
        planned_spin_row.addWidget(self.planned_h_spin)
        planned_spin_row.addWidget(self.planned_m_spin)
        planned_spin_row.addStretch()
        layout.addLayout(planned_spin_row)

        planned_btn_row = QHBoxLayout()
        self.apply_planned_btn = QPushButton("✏️ 수동 배정 적용")
        self.apply_planned_btn.setMinimumHeight(30)
        self.apply_planned_btn.clicked.connect(self._on_apply_planned)
        self.reset_planned_btn = QPushButton("🔄 자동으로 되돌리기")
        self.reset_planned_btn.setMinimumHeight(30)
        self.reset_planned_btn.clicked.connect(self._on_reset_planned)
        planned_btn_row.addWidget(self.apply_planned_btn)
        planned_btn_row.addWidget(self.reset_planned_btn)
        layout.addLayout(planned_btn_row)

        # ── Actual time section ───────────────────────────────────────
        sep2 = _QF()
        sep2.setFrameShape(_QF.HLine)
        sep2.setStyleSheet("color: #BDBDBD;")
        layout.addWidget(sep2)

        actual_row = QHBoxLayout()
        actual_row.addWidget(QLabel("실제 초과근무:"))
        self.actual_h_spin = QSpinBox()
        self.actual_h_spin.setRange(0, 24)
        self.actual_h_spin.setSuffix(" 시간")
        self.actual_m_spin = QSpinBox()
        self.actual_m_spin.setRange(0, 59)
        self.actual_m_spin.setSuffix(" 분")
        actual_row.addWidget(self.actual_h_spin)
        actual_row.addWidget(self.actual_m_spin)
        actual_row.addStretch()
        layout.addLayout(actual_row)

        self.apply_btn = QPushButton("실제 시간 적용")
        self.apply_btn.setMinimumHeight(32)
        self.apply_btn.clicked.connect(self._on_apply_actual)
        layout.addWidget(self.apply_btn)

        return self.date_group

    def _toggle_help(self) -> None:
        """사용법 패널 표시/숨김 토글."""
        visible = not self.help_group.isVisible()
        self.help_group.setVisible(visible)
        if visible:
            self.help_toggle_btn.setText("📖  사용법 닫기  ▲")
            self.help_toggle_btn.setStyleSheet(
                "QPushButton { font-size: 13px; font-weight: bold; "
                "background-color: #BBDEFB; border: 1px solid #64B5F6; "
                "border-radius: 4px; text-align: left; padding-left: 10px; }"
                "QPushButton:hover { background-color: #90CAF9; }"
            )
        else:
            self.help_toggle_btn.setText("📖  사용법 보기  ▼")
            self.help_toggle_btn.setStyleSheet(
                "QPushButton { font-size: 13px; font-weight: bold; "
                "background-color: #E3F2FD; border: 1px solid #90CAF9; "
                "border-radius: 4px; text-align: left; padding-left: 10px; }"
                "QPushButton:hover { background-color: #BBDEFB; }"
            )

    def _build_help_group(self) -> QGroupBox:
        group = QGroupBox("📖 사용법")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 8, 10, 10)

        help_text = (
            "<style>"
            "  h3  { margin: 8px 0 3px 0; font-size: 14px; color: #1565C0; }"
            "  p   { margin: 2px 0; font-size: 13px; line-height: 150%; }"
            "  ul  { margin: 2px 0 6px 0; padding-left: 16px; font-size: 13px; }"
            "  ol  { margin: 2px 0 6px 0; padding-left: 18px; font-size: 13px; }"
            "  li  { margin: 1px 0; line-height: 150%; }"
            "  .kw { font-weight: bold; color: #212121; }"
            "  .c  { color: #757575; }"
            "</style>"

            "<h3>🚀 기본 흐름</h3>"
            "<ol>"
            "<li>오른쪽 <b>설정</b>에서 월 목표·1일 최대 시간을 확인/변경합니다.</li>"
            "<li>달력을 열면 오늘 이후 평일에 예정 시간이 자동으로 채워집니다.</li>"
            "<li>실제 초과근무가 발생하면 해당 날짜를 클릭해 <b>실제 시간을 입력</b>합니다.</li>"
            "<li>입력한 즉시 남은 예정 시간이 재계산됩니다.</li>"
            "</ol>"

            "<h3>📅 달력 색상 안내</h3>"
            "<ul>"
            "<li><span style='background:#FFFFFF; border:1px solid #bbb; padding:0 4px;'>흰색</span>"
            "  — 평일 (자동 배정 대상)</li>"
            "<li><span style='background:#FFF8E1; border:1px solid #bbb; padding:0 4px;'>연노랑</span>"
            "  — 주말 (기본 제외)</li>"
            "<li><span style='background:#FFEBEE; border:1px solid #bbb; padding:0 4px;'>연빨강</span>"
            "  — 공휴일 (기본 제외)</li>"
            "<li><span style='background:#EEEEEE; border:1px solid #bbb; padding:0 4px;'>회색</span>"
            "  — 수동으로 제외한 날짜</li>"
            "<li>오늘 날짜는 <b style='color:#FF6F00;'>주황색 테두리</b>,"
            "  선택된 날짜는 <b style='color:#1565C0;'>파란색 테두리</b>로 표시됩니다.</li>"
            "</ul>"

            "<h3>🖱️ 날짜 클릭 후 조작</h3>"
            "<ul>"
            "<li><b>포함/제외 토글</b> — 자동 배정 대상에서 해당 날을 추가하거나 뺍니다."
            "  주말·공휴일도 포함 가능합니다.</li>"
            "<li><b>예정 시간 수동 설정</b> — 자동 계산된 값 대신 원하는 시간을 직접 지정합니다."
            "  적용 후에는 달력 셀에 <b style='color:#E65100;'>★</b> 표시가 붙습니다.</li>"
            "<li><b>자동으로 되돌리기</b> — 수동 설정을 해제하고 자동 계산으로 복귀합니다.</li>"
            "<li><b>실제 시간 적용</b> — 실제 초과근무 시간을 기록합니다. 과거·주말·제외 날짜도"
            "  입력할 수 있으며, 월 합계에 즉시 반영됩니다.</li>"
            "</ul>"

            "<h3>📋 이전 실적 누계 (설정 패널)</h3>"
            "<p>앱을 월 중간부터 쓰기 시작했다면, 달력에 날짜별로 입력하는 대신<br>"
            "지금까지의 초과근무 합계를 <b>이전 실적 누계</b>에 일괄 입력하세요.<br>"
            "달력에는 표시되지 않지만 월간 합계 계산에 포함됩니다.</p>"

            "<h3>📊 월간 요약 항목</h3>"
            "<ul>"
            "<li><b>이번달 목표 초과근무</b> — 설정한 원래 목표 시간</li>"
            "<li><b>실제 초과근무 시간</b> — 날짜별 실제 입력 + 이전 실적 누계 합산</li>"
            "<li><b>예정 초과근무 시간</b> — 자동·수동 배정된 예정 시간 합산</li>"
            "<li><b>남은 목표</b> — 목표 달성까지 추가로 필요한 시간"
            "  <span class='c'>(주황=미달, 초록=달성)</span></li>"
            "</ul>"

            "<h3>⚙️ 기타</h3>"
            "<ul>"
            "<li>모든 입력은 자동 저장됩니다 (재실행 시 복원).</li>"
            "<li>상단 <b>◀ 이전 달 / 다음 달 ▶</b> 버튼으로 월을 이동할 수 있습니다.</li>"
            "<li>공휴일 목록은 2023–2028년이 내장되어 있습니다.</li>"
            "</ul>"
        )

        lbl = QLabel(help_text)
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.RichText)
        lbl.setAlignment(Qt.AlignTop)
        lbl.setStyleSheet(
            "QLabel { background: #FAFAFA; border-radius: 4px; padding: 4px; }"
        )
        layout.addWidget(lbl)
        return group

    # ── Helper factories ──────────────────────────────────────────────

    @staticmethod
    def _stat_value_label() -> QLabel:
        lbl = QLabel("—")
        lbl.setStyleSheet("font-weight: bold; font-size: 13px;")
        return lbl

    def _set_date_controls_enabled(self, enabled: bool) -> None:
        """Enable/disable controls that apply to any selected date."""
        self.toggle_btn.setEnabled(enabled)
        self.actual_h_spin.setEnabled(enabled)
        self.actual_m_spin.setEnabled(enabled)
        self.apply_btn.setEnabled(enabled)

    def _set_planned_controls_enabled(self, enabled: bool) -> None:
        """Enable manual planned controls only for future included dates."""
        self.planned_h_spin.setEnabled(enabled)
        self.planned_m_spin.setEnabled(enabled)
        self.apply_planned_btn.setEnabled(enabled)
        self.reset_planned_btn.setEnabled(enabled)

    # ── Public update entry point ─────────────────────────────────────

    def update_state(
        self,
        year: int,
        month: int,
        target_minutes: int,
        daily_max_minutes: int,
        base_actual_minutes: int,
        summary: dict,
        selected_entry: DayEntry | None,
    ) -> None:
        # Settings spinboxes — update without triggering recalculation
        self._block_setting_signals(True)
        self.target_h_spin.setValue(target_minutes // 60)
        self.target_m_spin.setValue(target_minutes % 60)
        self.daily_h_spin.setValue(daily_max_minutes // 60)
        self.daily_m_spin.setValue(daily_max_minutes % 60)
        self.base_actual_h_spin.setValue(base_actual_minutes // 60)
        self.base_actual_m_spin.setValue(base_actual_minutes % 60)
        self._block_setting_signals(False)

        # Summary labels
        original_target = summary.get("original_target", 0)
        actual_total    = summary.get("actual_total", 0)
        planned_total   = summary.get("planned_total", 0)
        expected_total  = actual_total + planned_total   # 당월 예상 = 실제 + 예정

        self.original_target_lbl.setText(minutes_to_str(original_target))
        self.actual_total_lbl.setText(minutes_to_str(actual_total))
        self.planned_total_lbl.setText(minutes_to_str(planned_total))

        # 당월 예상 초과근무: 색상 처리
        overage = expected_total - original_target
        if overage > 0:
            # 목표 초과 → 빨간색 + 무료봉사 경고
            self.expected_total_lbl.setText(minutes_to_str(expected_total))
            self.expected_total_lbl.setStyleSheet(
                "font-weight: bold; font-size: 13px; color: #C62828;"
            )
            self.overage_warning_lbl.setText(
                f"🚨 {minutes_to_str(overage)} 무료 봉사가 예정되어있습니다!"
            )
            self.overage_warning_lbl.setVisible(True)
        elif overage == 0 and expected_total > 0:
            # 목표와 정확히 일치 → 파란색
            self.expected_total_lbl.setText(minutes_to_str(expected_total))
            self.expected_total_lbl.setStyleSheet(
                "font-weight: bold; font-size: 13px; color: #1565C0;"
            )
            self.overage_warning_lbl.setVisible(False)
        else:
            # 목표 미달 → 기본 색상
            self.expected_total_lbl.setText(minutes_to_str(expected_total))
            self.expected_total_lbl.setStyleSheet(
                "font-weight: bold; font-size: 13px;"
            )
            self.overage_warning_lbl.setVisible(False)

        remaining = summary.get("remaining", 0)
        if remaining > 0:
            self.remaining_lbl.setText(minutes_to_str(remaining))
            self.remaining_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #E65100;")
        else:
            self.remaining_lbl.setText(minutes_to_str(0))
            self.remaining_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #2E7D32;")

        # Status / warning
        status = summary.get("status", "")
        warning = summary.get("warning", "")

        self.status_label.setVisible(bool(status))
        self.status_label.setText(status)
        self.warning_label.setVisible(bool(warning))
        self.warning_label.setText(warning)

        # Date detail section
        self._current_entry = selected_entry
        self._refresh_date_section(selected_entry)

    # ── Date detail section ───────────────────────────────────────────

    def _refresh_date_section(self, entry: DayEntry | None) -> None:
        if entry is None:
            self.date_group.setTitle("선택한 날짜")
            self.date_info_label.setText("달력에서 날짜를 클릭하세요.")
            self.toggle_btn.setText("포함/제외 토글")
            self.toggle_btn.setStyleSheet("")
            self._set_date_controls_enabled(False)
            self._set_planned_controls_enabled(False)
            return

        d = entry.date
        today = date.today()
        wday_str = _WEEKDAY_NAMES[d.weekday()]
        is_future = d > today

        self.date_group.setTitle(f"선택한 날짜: {d.year}/{d.month:02d}/{d.day:02d} ({wday_str})")

        # Build info text
        tags: list[str] = []
        if entry.is_holiday:
            tags.append(f"공휴일 ({entry.holiday_name})")
        if entry.is_weekend:
            tags.append("주말")
        if d < today:
            tags.append("과거")
        elif d == today:
            tags.append("오늘")

        included_str = "포함 (자동 배정 대상)" if entry.included else "제외 (자동 배정 제외)"

        if entry.planned_minutes > 0:
            manual_badge = "  [수동설정]" if entry.is_planned_manual else "  [자동]"
            planned_str = minutes_to_str(entry.planned_minutes) + manual_badge
        else:
            planned_str = "없음"

        actual_str = minutes_to_str(entry.actual_minutes) if entry.actual_minutes > 0 else "없음"

        info_parts = [
            f"구분: {', '.join(tags) if tags else '평일'}",
            f"상태: {included_str}",
            f"예정 초과근무: {planned_str}",
            f"실제 초과근무: {actual_str}",
        ]
        self.date_info_label.setText("\n".join(info_parts))

        # Toggle button appearance
        if entry.included:
            self.toggle_btn.setText("⛔  이 날짜 자동 배정 제외")
            self.toggle_btn.setStyleSheet(
                "QPushButton { background-color: #FFCDD2; } "
                "QPushButton:hover { background-color: #EF9A9A; }"
            )
        else:
            self.toggle_btn.setText("✅  이 날짜 자동 배정 포함")
            self.toggle_btn.setStyleSheet(
                "QPushButton { background-color: #C8E6C9; } "
                "QPushButton:hover { background-color: #A5D6A7; }"
            )

        # Planned spinboxes — populate silently, enable only for future included days
        for spin in (self.planned_h_spin, self.planned_m_spin):
            spin.blockSignals(True)
        self.planned_h_spin.setValue(entry.planned_minutes // 60)
        self.planned_m_spin.setValue(entry.planned_minutes % 60)
        for spin in (self.planned_h_spin, self.planned_m_spin):
            spin.blockSignals(False)

        can_edit_planned = is_future and entry.included
        self._set_planned_controls_enabled(can_edit_planned)

        # Colour the apply button to signal manual-lock state
        if entry.is_planned_manual:
            self.apply_planned_btn.setStyleSheet(
                "QPushButton { background-color: #FFE0B2; font-weight: bold; }"
            )
            self.reset_planned_btn.setEnabled(True)
        else:
            self.apply_planned_btn.setStyleSheet("")
            self.reset_planned_btn.setEnabled(can_edit_planned)

        # Actual time spinboxes — update silently
        self._block_actual_signals(True)
        self.actual_h_spin.setValue(entry.actual_minutes // 60)
        self.actual_m_spin.setValue(entry.actual_minutes % 60)
        self._block_actual_signals(False)

        self._set_date_controls_enabled(True)

    # ── Signal handlers ───────────────────────────────────────────────

    def _on_toggle_clicked(self) -> None:
        if self._current_entry is not None:
            self.included_toggled.emit(self._current_entry.date)

    def _on_apply_planned(self) -> None:
        if self._current_entry is not None:
            total = self.planned_h_spin.value() * 60 + self.planned_m_spin.value()
            self.planned_changed.emit(self._current_entry.date, total)

    def _on_reset_planned(self) -> None:
        if self._current_entry is not None:
            self.planned_reset.emit(self._current_entry.date)

    def _on_apply_actual(self) -> None:
        if self._current_entry is not None:
            total = self.actual_h_spin.value() * 60 + self.actual_m_spin.value()
            self.actual_changed.emit(self._current_entry.date, total)

    def _emit_target_changed(self) -> None:
        total = self.target_h_spin.value() * 60 + self.target_m_spin.value()
        self.target_changed.emit(total)

    def _emit_daily_max_changed(self) -> None:
        total = self.daily_h_spin.value() * 60 + self.daily_m_spin.value()
        self.daily_max_changed.emit(total)

    def _emit_base_actual_changed(self) -> None:
        total = self.base_actual_h_spin.value() * 60 + self.base_actual_m_spin.value()
        self.base_actual_changed.emit(total)

    # ── Signal blocking helpers ───────────────────────────────────────

    def _block_setting_signals(self, block: bool) -> None:
        for spin in (self.target_h_spin, self.target_m_spin,
                     self.daily_h_spin, self.daily_m_spin,
                     self.base_actual_h_spin, self.base_actual_m_spin):
            spin.blockSignals(block)

    def _block_actual_signals(self, block: bool) -> None:
        for spin in (self.actual_h_spin, self.actual_m_spin):
            spin.blockSignals(block)
