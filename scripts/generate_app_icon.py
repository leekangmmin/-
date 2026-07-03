#!/usr/bin/env python3
"""앱 아이콘 생성 — 자체 제작 디자인 (TOEFL/ETS/토스 로고 미사용).

디자인: 파란색(브랜드 primary #3182f6) 라운드 사각형 배경 위에
흰 답안지(라운드 카드)와 텍스트 줄 3개, 우하단에 채점 완료를 뜻하는
체크 배지. Writing(답안지) + 평가(체크)를 간결하게 표현하며 16px에서도
"파란 바탕의 흰 카드 + 체크"로 인식된다.

산출물:
  packaging/resources/app-icon-source.png   (1024px 마스터)
  packaging/resources/AppIcon.iconset/      (macOS 필수 크기 10종)
  packaging/resources/app.icns              (iconutil 변환)

Pillow만 사용한다(이미 fpdf2 의존성으로 설치돼 있음).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESOURCES = PROJECT_ROOT / "packaging" / "resources"

# 브랜드 색 (static/styles.css 디자인 토큰과 동일 계열)
PRIMARY = (49, 130, 246, 255)        # #3182f6
PRIMARY_DARK = (27, 100, 218, 255)   # #1b64da
WHITE = (255, 255, 255, 255)
LINE_BLUE = (200, 222, 252, 255)     # 답안지 텍스트 줄
CHECK_GREEN = (23, 160, 93, 255)     # #17a05d (성공색)

CANVAS = 1024
# macOS Big Sur 스타일: 1024 캔버스에 여백을 두고 ~832px 라운드 사각형
BG_MARGIN = 96
BG_RADIUS = 186


def draw_master() -> Image.Image:
    img = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 배경 라운드 사각형 (위→아래 미세한 세로 그라데이션으로 평면감 완화)
    bg_box = (BG_MARGIN, BG_MARGIN, CANVAS - BG_MARGIN, CANVAS - BG_MARGIN)
    grad = Image.new("RGBA", (1, CANVAS), (0, 0, 0, 0))
    for y in range(CANVAS):
        t = y / CANVAS
        r = int(PRIMARY[0] + (PRIMARY_DARK[0] - PRIMARY[0]) * t)
        g = int(PRIMARY[1] + (PRIMARY_DARK[1] - PRIMARY[1]) * t)
        b = int(PRIMARY[2] + (PRIMARY_DARK[2] - PRIMARY[2]) * t)
        grad.putpixel((0, y), (r, g, b, 255))
    grad = grad.resize((CANVAS, CANVAS))
    mask = Image.new("L", (CANVAS, CANVAS), 0)
    ImageDraw.Draw(mask).rounded_rectangle(bg_box, radius=BG_RADIUS, fill=255)
    img.paste(grad, (0, 0), mask)

    # 답안지 (흰 라운드 카드, 살짝 왼쪽 위로 치우쳐 체크 배지 공간 확보)
    card = (300, 250, 724, 774)
    d.rounded_rectangle(card, radius=48, fill=WHITE)

    # 텍스트 줄 3개 (마지막 줄은 짧게 — 문단 느낌)
    line_x0, line_w, line_h, gap = 356, 312, 34, 64
    line_y = 340
    for i, w in enumerate((line_w, line_w, int(line_w * 0.62))):
        d.rounded_rectangle(
            (line_x0, line_y + i * (line_h + gap), line_x0 + w, line_y + i * (line_h + gap) + line_h),
            radius=line_h // 2, fill=LINE_BLUE,
        )

    # 체크 배지 (우하단, 흰 테두리로 카드와 분리)
    badge_c, badge_r = (700, 730), 148
    d.ellipse(
        (badge_c[0] - badge_r - 22, badge_c[1] - badge_r - 22,
         badge_c[0] + badge_r + 22, badge_c[1] + badge_r + 22),
        fill=WHITE,
    )
    d.ellipse(
        (badge_c[0] - badge_r, badge_c[1] - badge_r, badge_c[0] + badge_r, badge_c[1] + badge_r),
        fill=CHECK_GREEN,
    )
    # 체크 마크 (두꺼운 폴리라인)
    check = [(626, 730), (676, 786), (778, 668)]
    d.line(check, fill=WHITE, width=44, joint="curve")
    for p in check:
        d.ellipse((p[0] - 22, p[1] - 22, p[0] + 22, p[1] + 22), fill=WHITE)

    return img


# macOS iconset 필수 구성
ICONSET_SIZES = [
    ("icon_16x16.png", 16), ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32), ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128), ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256), ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512), ("icon_512x512@2x.png", 1024),
]


def main() -> int:
    RESOURCES.mkdir(parents=True, exist_ok=True)
    master = draw_master()
    source_png = RESOURCES / "app-icon-source.png"
    master.save(source_png)
    print(f"master: {source_png}")

    iconset = RESOURCES / "AppIcon.iconset"
    iconset.mkdir(exist_ok=True)
    for name, size in ICONSET_SIZES:
        master.resize((size, size), Image.LANCZOS).save(iconset / name)
    print(f"iconset: {iconset} ({len(ICONSET_SIZES)} sizes)")

    icns = RESOURCES / "app.icns"
    result = subprocess.run(
        ["iconutil", "-c", "icns", str(iconset), "-o", str(icns)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"iconutil 실패: {result.stderr}", file=sys.stderr)
        return 1
    print(f"icns: {icns} ({icns.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
