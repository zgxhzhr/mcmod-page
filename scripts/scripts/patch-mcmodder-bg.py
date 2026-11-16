#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给 Mcmodder 的白天背景加"随机轮换"：原图 + 指定文件夹里的图片，每次加载随机取一张。

用法：
    python patch-mcmodder-bg.py <基脚本.user.js> <图片目录> [输出文件]

说明：
- 图片以 base64 内嵌进脚本，不依赖图床/本地服务；
- 随机在脚本执行时求值一次，也就是**每次打开新页面抽一张**；
- 夜间背景（nightMode.bg）不动。
"""
import base64
import re
import sys
from pathlib import Path

EXTS = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}

# 原脚本里白天背景那一行（形如 bg: "https://...",）
BG_LINE = re.compile(r'\n(\s*)bg:\s*"[^"]+",\n')


def collect(folder: Path) -> list[tuple[str, str]]:
    out = []
    for f in sorted(folder.iterdir()):
        if not f.is_file() or f.suffix.lower() not in EXTS:
            continue
        b64 = base64.b64encode(f.read_bytes()).decode()
        out.append((f.name, f"data:{EXTS[f.suffix.lower()]};base64,{b64}"))
    return out


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    src = Path(sys.argv[1])
    img_dir = Path(sys.argv[2])
    dst = Path(sys.argv[3]) if len(sys.argv) > 3 else src.with_name(src.stem + "-bg.user.js")

    text = src.read_text(encoding="utf-8", errors="ignore")
    m = BG_LINE.search(text)
    if not m:
        print("未找到 bg: 行，脚本可能已打过补丁或结构变了")
        return 1

    indent = m.group(1)
    keep = img_dir / "none"
    images = collect(img_dir)
    if not images:
        print(f"{img_dir} 里没有可用图片")
        return 1

    parts = ['"https://s21.ax1x.com/2025/01/05/pE9Avh4.jpg"'] + [f'"{u}"' for _, u in images]
    expr = (
        f"\n{indent}// [本地补丁] 白天背景：原图 + {len(images)} 张本地图，每次加载随机取一张\n"
        f"{indent}bg: (() => {{ const a = [\n"
        f"{indent}  " + (",\n" + indent + "  ").join(parts) + f"\n{indent}]; return a[Math.floor(Math.random() * a.length)]; }})(),\n"
    )
    text = text[: m.start()] + expr + text[m.end():]

    dst.write_text(text, encoding="utf-8")
    print(f"输入：{src}  ({src.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f"输出：{dst}  ({dst.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f"背景候选：{len(parts)} 张（原图 1 + 本地 {len(images)}）")
    for name, uri in images:
        print(f"  {name:<34} base64 {len(uri) / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
