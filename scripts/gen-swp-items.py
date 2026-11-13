#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple Wooden Pipes（classId 15375）物品页 —— 8 管道 + 1 泵。

图标全部来自模型渲染（模组自带 models/block，材质引用原版木板）。
管道用 <wood>_pipe_middle 模型（含十字形管口），泵用 pump 模型。

8 个木材泵（<wood>_pump）没有物品形态、lang 里也没有名称，是内部方块，不建页。
"""
import base64
import io
import json
import random
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
SWP = BASE / "swp"
ICONS128 = BASE / "swp-icons128"
ICONS32 = BASE / "swp-icons32"
OUT = BASE / "swp-物品导入-15375.json"
NS = "simplewoodenpipes"

_PAW = ["呜喵", "喵呜", "喵喵"]

WOODS = [
    ("oak", "橡木", False),
    ("spruce", "云杉", False),
    ("birch", "白桦", False),
    ("acacia", "金合欢", False),
    ("jungle", "丛林", False),
    ("dark_oak", "深色橡木", False),
    ("crimson", "绯红", True),
    ("warped", "诡异", True),
]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def b64(path: Path):
    if not path.exists():
        return ""
    buf = io.BytesIO()
    Image.open(path).convert("RGBA").save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def main() -> int:
    lang = json.loads((SWP / "assets/simplewoodenpipes/lang/en_us.json").read_text(encoding="utf-8"))
    rows = []

    # 8 个管道
    for wood, zh, fire_safe in WOODS:
        name = lang[f"block.{NS}.{wood}_pipe"]
        icon = f"{NS}__block_{wood}_pipe_middle"
        temp = ("<p><strong>耐高温</strong>：可以输送岩浆、熔融金属等高温流体。</p>"
                if fire_safe else
                "<p><strong>耐高温</strong>：不能输送高温流体。材质为普通木材，"
                "通入岩浆这类流体会被破坏。</p>")
        rows.append({
            "id": f"{wood}_pipe",
            "name": name,
            "ename": "",
            "regname": f"{NS}:{wood}_pipe",
            "category": "管道",
            "type": "物品/方块",
            "maxstack": 64,
            "remark": (
                "Simple Wooden Pipes 资料页：名称取自 lang/en_us.json，"
                "耐高温属性取自 SupportedWoodType 枚举的 fireSafe 字段。"
                f"{tail()}"
            ),
            "html": (
                f"<p>{name}是 Simple Wooden Pipes 添加的木制流体管道，材质为{zh}。</p>"
                "<p><strong>连接</strong>：自动与相邻的管道、泵或容器对接，六个方向各自独立判断，"
                "不需要调整朝向。</p>"
                "<p><strong>提取方向</strong>：手持活塞对某一面右键，可把该面设为流体的提取端；"
                "Shift + 右键取消设定，活塞退还。同一根管道可以只有一端抽取、其余端输送。</p>"
                f"{temp}"
                "<p><strong>传输速率</strong>：默认 50，写在配置文件的 transferRate 项里。</p>"
            ),
            "icon32": b64(ICONS32 / f"{icon}.png"),
            "icon128": b64(ICONS128 / f"{icon}.png"),
        })

    # 泵
    name = lang[f"block.{NS}.pump"]
    rows.append({
        "id": "pump",
        "name": name,
        "ename": "",
        "regname": f"{NS}:pump",
        "category": "泵",
        "type": "物品/方块",
        "maxstack": 64,
        "remark": (
            "Simple Wooden Pipes 资料页：名称取自 lang/en_us.json，"
            "泵速率取自 SWPConfig 的 pumpRate 默认值。"
            f"{tail()}"
        ),
        "html": (
            "<p>Pump（泵）是 Simple Wooden Pipes 添加的流体泵，用于给管道里的流体加压。</p>"
            "<p><strong>作用</strong>：把流体推向更高的位置或更远的距离。"
            "管道负责横向传输，泵负责提供动力，两者配合才能让流体在复杂管网里流动。</p>"
            "<p><strong>速率</strong>：默认 25，约为管道传输速率（50）的一半，写在配置文件的 pumpRate 项里。</p>"
            "<p><strong>外观</strong>：竖立的木柱造型，按木材区分材质。物品栏里只有一种通用泵，"
            "放置后可通过其它方式切换外观变体。</p>"
        ),
        "icon32": b64(ICONS32 / f"{NS}__block_oak_pump.png"),
        "icon128": b64(ICONS128 / f"{NS}__block_oak_pump.png"),
    })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)")
    for r in rows:
        print(f"  {r['name']:<22} 32={'有' if r['icon32'] else '无'} 128={'有' if r['icon128'] else '无'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
