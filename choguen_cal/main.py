import os
import sys

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def get_resource_path(relative_path: str) -> str:
    """
    개발 환경과 PyInstaller --onefile 환경 모두에서
    올바른 절대 경로를 반환합니다.

    PyInstaller로 패키징된 exe는 실행 시 임시 폴더(_MEIPASS)에
    번들 파일을 풀어 놓습니다. 개발 환경에서는 이 파일의 디렉터리를
    기준으로 경로를 계산합니다.
    """
    if hasattr(sys, "_MEIPASS"):          # PyInstaller onefile 실행 시
        base = sys._MEIPASS               # type: ignore[attr-defined]
    else:                                 # 일반 python 실행 시
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)


def load_app_icon() -> QIcon | None:
    """
    assets/ 폴더에서 아이콘 파일을 찾아 QIcon으로 반환합니다.
    우선순위: icon.ico → icon.png
    둘 다 없으면 None을 반환합니다.
    """
    for filename in ("icon.ico", "icon.png"):
        path = get_resource_path(os.path.join("assets", filename))
        if os.path.isfile(path):
            return QIcon(path)
    return None


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("초과근무 일정 자동 생성기")
    app.setStyle("Fusion")
    app.setFont(QFont("", 13))   # 전체 기본 폰트 크기 13pt

    icon = load_app_icon()
    if icon:
        app.setWindowIcon(icon)   # 작업 표시줄 + 모든 창에 적용

    window = MainWindow()
    if icon:
        window.setWindowIcon(icon)  # 타이틀바에 명시적으로 설정
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
