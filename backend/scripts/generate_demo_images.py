"""演示配图生成脚本：为 seed_demo 的每个活动生成封面图和仿真二维码

用法：backend/.venv/bin/python backend/scripts/generate_demo_images.py
依赖：pillow
输出：backend/uploads/activities/demo/cover_XX.png、qr_XX.png

说明：生成的文件属于运行时数据（uploads 目录不入库）；
      seed_demo.py 会检测这些文件，存在则引用，不存在自动跳过（无破图）。
"""
import random
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageDraw, ImageFont

from app.config import ACTIVITY_IMAGE_DIR
import seed_demo

FONT_PATH = "/System/Library/Fonts/STHeiti Light.ttc"
DEMO_DIR = ACTIVITY_IMAGE_DIR / "demo"

# 每个活动的主题色（渐变起止色）
COLORS = [
    ((0x40, 0x9E, 0xFF), (0x79, 0xBB, 0xFF)),  # 蓝
    ((0x8B, 0x5C, 0xF6), (0xC4, 0xB5, 0xFD)),  # 紫
    ((0xF5, 0x9E, 0x0B), (0xFB, 0xBF, 0x24)),  # 橙
    ((0x10, 0xB9, 0x81), (0x6E, 0xE7, 0xB7)),  # 绿
    ((0xEC, 0x48, 0x99), (0xF9, 0xA8, 0xD4)),  # 粉
    ((0xEF, 0x44, 0x44), (0xFC, 0xA5, 0xA5)),  # 红
    ((0x06, 0xB6, 0xD4), (0x67, 0xE8, 0xF9)),  # 青
    ((0x1E, 0x3A, 0x8A), (0x3B, 0x82, 0xF6)),  # 深蓝
    ((0xBE, 0x18, 0x5D), (0xF4, 0x72, 0xB6)),  # 玫红
    ((0x65, 0xA3, 0x0D), (0xA3, 0xE6, 0x35)),  # 黄绿
    ((0x43, 0x38, 0xCA), (0x81, 0x8C, 0xF8)),  # 靛
    ((0xFB, 0x71, 0x85), (0xFD, 0xA4, 0xAF)),  # 珊瑚
    ((0x92, 0x40, 0x0E), (0xD9, 0x77, 0x06)),  # 棕
]


def gradient_bg(width: int, height: int, c1: tuple, c2: tuple) -> Image.Image:
    """垂直渐变背景"""
    img = Image.new("RGB", (width, height))
    for y in range(height):
        t = y / height
        color = tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))
        ImageDraw.Draw(img).line([(0, y), (width, y)], fill=color)
    return img


def make_cover(path: Path, title: str, c1: tuple, c2: tuple) -> None:
    """活动封面：渐变背景 + 标题 + 装饰"""
    w, h = 640, 400
    img = gradient_bg(w, h, c1, c2)
    d = ImageDraw.Draw(img, "RGBA")

    # 装饰圆（右上角半透明）
    d.ellipse([w - 220, -90, w + 60, 190], fill=(255, 255, 255, 36))
    d.ellipse([w - 150, -40, w + 90, 200], fill=(255, 255, 255, 28))

    # 标题（自动换行，最多 3 行）
    font_title = ImageFont.truetype(FONT_PATH, 44)
    lines = textwrap.wrap(title, width=12, max_lines=3, placeholder="…")[:3]
    y = 60
    for line in lines:
        d.text((48, y), line, fill=(255, 255, 255), font=font_title)
        y += 62

    # 底部品牌条
    font_brand = ImageFont.truetype(FONT_PATH, 24)
    d.rectangle([48, h - 68, 250, h - 24], fill=(255, 255, 255, 40))
    d.text((64, h - 60), "RUNing HUB", fill=(255, 255, 255), font=font_brand)

    img.save(path, "PNG")
    print(f"封面 {path.name}: {title}")


def make_qr(path: Path, seed: int) -> None:
    """仿真二维码：三个定位角 + 随机模块（仅装饰，不可扫描）"""
    rng = random.Random(seed)
    cell = 10
    size = cell * 30
    img = Image.new("RGB", (size, size), "white")
    d = ImageDraw.Draw(img)

    def finder(cx: int, cy: int) -> None:
        d.rectangle([cx * cell, cy * cell, (cx + 7) * cell - 1, (cy + 7) * cell - 1], fill="black")
        d.rectangle([(cx + 1) * cell, (cy + 1) * cell, (cx + 6) * cell - 1, (cy + 6) * cell - 1], fill="white")
        d.rectangle([(cx + 2) * cell, (cy + 2) * cell, (cx + 5) * cell - 1, (cy + 5) * cell - 1], fill="black")

    for cx, cy in [(0, 0), (23, 0), (0, 23)]:
        finder(cx, cy)

    for i in range(30):
        for j in range(30):
            # 跳过三个定位角区域
            if (i < 8 and j < 8) or (i > 21 and j < 8) or (i < 8 and j > 21):
                continue
            if rng.random() < 0.45:
                d.rectangle([i * cell, j * cell, (i + 1) * cell - 1, (j + 1) * cell - 1], fill="black")

    img.save(path, "PNG")
    print(f"二维码 {path.name}")


def main() -> None:
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    for i, spec in enumerate(seed_demo.ACTIVITIES, start=1):
        c1, c2 = COLORS[(i - 1) % len(COLORS)]
        make_cover(DEMO_DIR / f"cover_{i:02d}.png", spec["title"], c1, c2)
        make_qr(DEMO_DIR / f"qr_{i:02d}.png", seed=20260900 + i)
    print(f"\n生成完毕，输出目录：{DEMO_DIR}")


if __name__ == "__main__":
    main()
