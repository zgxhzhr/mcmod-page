#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给没有静态贴图的条目补上原版 missing texture 占位图标。

依据 skill「缺图标时用原版 missing texture 占位」：
- 品红 #F800F8 与黑 #000000 的 8px 棋盘
- 16×16 原始，NEAREST 放大到 32
- 备注里说明是缺省材质占位

适用：生物（实体渲染，无静态 png）、刷怪蛋（两色程序化绘制）。
"""
import base64
import io
import json
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")

TARGETS = [
    ("cds-新增丧尸-4397.json", "生物（实体渲染，无静态贴图）"),
    ("cds-新增刷怪蛋-4397.json", "刷怪蛋（游戏按两色程序化绘制，无静态贴图）"),
]

NOTE_SUFFIX = "图标使用原版缺省材质（品红与黑的棋盘格）占位，因该条目没有可直接用作图标的静态贴图。"


def missing_texture(size: int = 32) -> str:
    """16×16 的 8px 品红/黑棋盘，NEAREST 放大到 size。"""
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 255))
    for y in range(16):
        for x in range(16):
            if ((x // 8) + (y // 8)) % 2 == 0:
                img.putpixel((x, y), (248, 0, 248, 255))
    img = img.resize((size, size), Image.NEAREST)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def main() -> int:
    b64 = missing_texture(32)
    print(f"missing texture: {len(b64)} 字符 base64")

    # 存一份预览，方便目视确认
    Image.open(io.BytesIO(base64.b64decode(b64))).resize((128, 128), Image.NEAREST).save(
        BASE / "missing-texture-128.png")
    print(f"预览: {BASE / 'missing-texture-128.png'}")

    for fname, reason in TARGETS:
        p = BASE / fname
        rows = json.loads(p.read_text(encoding="utf-8"))
        for r in rows:
            if not r.get("icon32"):
                r["icon32"] = b64
                if NOTE_SUFFIX not in r["remark"]:
                    r["remark"] = r["remark"] + " " + NOTE_SUFFIX
        p.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {fname}: {len(rows)} 条已补图标（{reason}）")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
