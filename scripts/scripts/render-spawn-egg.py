#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""刷怪蛋图标渲染：按原版 SpawnEggItem 的两色规则画蛋形。

原版的刷怪蛋图标由两个可调颜色生成——底色（primaryColor）与斑点色（secondaryColor）。
这里按同样的构成绘制：
  1. 蛋形轮廓（上窄下宽的椭圆）
  2. 底色填满蛋形
  3. 斑点点缀（固定分布，保证同一模组内的蛋风格一致）

用法：
  python render-spawn-egg.py <primary_rgb> <secondary_rgb> <输出路径> [尺寸]
  rgb 写 "0,51,102" 这种形式
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

# 蛋形轮廓（在 16×16 网格上的掩码，1=蛋体）
EGG_MASK = [
    "................",
    "................",
    "......####......",
    ".....######.....",
    "....########....",
    "....########....",
    "...##########...",
    "...##########...",
    "...##########...",
    "..############..",
    "..############..",
    "..############..",
    "...##########...",
    "....########....",
    "................",
    "................",
]

# 斑点位置（在蛋形内的相对位置，1=斑点）
SPOT_MASK = [
    "................",
    "................",
    "................",
    "......##........",
    "....##..##......",
    "..........##....",
    "....##..........",
    "........##......",
    "..##......##....",
    "....##..........",
    "..........##....",
    "..##....##......",
    "..............#.",
    "................",
    "................",
    "................",
]


def parse_rgb(s: str):
    parts = [int(x) for x in s.split(",")]
    return tuple(parts[:3])


def render(primary, secondary, size: int = 32) -> Image.Image:
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()
    for y in range(16):
        for x in range(16):
            if EGG_MASK[y][x] == "#":
                px[x, y] = (*primary, 255)
            if SPOT_MASK[y][x] == "#" and EGG_MASK[y][x] == "#":
                px[x, y] = (*secondary, 255)

    # 描边：蛋体外缘加一圈深色，让轮廓在小尺寸下更清楚
    edge = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    epx = edge.load()
    for y in range(16):
        for x in range(16):
            if EGG_MASK[y][x] != "#":
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < 16 and 0 <= ny < 16 and EGG_MASK[ny][nx] != "#":
                    epx[x, y] = (0, 0, 0, 90)
                    break
    img = Image.alpha_composite(edge, img)

    if size != 16:
        img = img.resize((size, size), Image.NEAREST)
    return img


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 1
    primary = parse_rgb(sys.argv[1])
    secondary = parse_rgb(sys.argv[2])
    out = Path(sys.argv[3])
    size = int(sys.argv[4]) if len(sys.argv) > 4 else 32
    img = render(primary, secondary, size)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f"生成 {out}  {img.size}  底色={primary} 斑点={secondary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
