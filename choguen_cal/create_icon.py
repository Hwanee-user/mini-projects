"""
아이콘 생성기 — 처음 한 번만 실행하세요.

실행 방법:
    pip install Pillow
    python create_icon.py

결과물: assets/icon.ico  (16 ~ 256px 멀티 사이즈 ICO)
"""

import os
import sys


def make_icon() -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow가 설치되어 있지 않습니다. 먼저 아래 명령을 실행하세요:")
        print("  pip install Pillow")
        sys.exit(1)

    os.makedirs("assets", exist_ok=True)
    out_path = os.path.join("assets", "icon.ico")

    # ICO 파일에 포함할 크기 목록
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images: list[Image.Image] = []

    for s in sizes:
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # ── 파란 원형 배경 ──────────────────────────────────────────
        margin = max(1, s // 16)
        draw.ellipse(
            [margin, margin, s - margin - 1, s - margin - 1],
            fill=(21, 101, 192, 255),   # Material Blue 800
        )

        # ── "OT" 텍스트 ─────────────────────────────────────────────
        text = "OT"
        font_size = max(6, s * 38 // 100)

        font: ImageFont.ImageFont | ImageFont.FreeTypeFont
        for font_name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
            try:
                font = ImageFont.truetype(font_name, font_size)
                break
            except OSError:
                continue
        else:
            font = ImageFont.load_default()

        # textbbox 로 정확한 크기를 구해 중앙 배치
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (s - tw) // 2 - bbox[0]
        ty = (s - th) // 2 - bbox[1]
        draw.text((tx, ty), text, fill=(255, 255, 255, 255), font=font)

        images.append(img)

    # 첫 번째 이미지를 기준으로 저장, 나머지를 append
    images[0].save(
        out_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    print(f"✅  아이콘 생성 완료: {os.path.abspath(out_path)}")
    print("이제 python main.py 또는 PyInstaller 빌드를 실행하면 아이콘이 적용됩니다.")


if __name__ == "__main__":
    make_icon()
