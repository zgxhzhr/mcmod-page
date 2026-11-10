#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TFC Rocks+（classId 3182）12 种岩石的批量新增 JSON。

按岩石合并：每种岩石一页，正文列出该岩石的全部方块形态，不是每个方块一页。

数据来源：
- 岩石名与形态名：assets/tfc/lang/en_us.lang（模组覆盖了群峦的语言文件）
- 方块形态：lang 里 tile.tfc.*.<rock>.name 的键
- 纹理：assets/tfc/textures/blocks/stonetypes/<形态>/<rock>.png

图标用 raw（原始石）纹理做等轴测立方体。
"""
import base64
import io
import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
MOD = BASE / "trp"
TEXROOT = MOD / "assets/tfc/textures/blocks/stonetypes"
OUT = BASE / "trp-方块导入-3182.json"

_PAW = ["呜喵", "喵呜", "喵喵"]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


# 岩石：id, 英文名, 地质学对应, 分类
ROCKS = [
    ("arkose",      "Arkose Rock",      "长石砂岩，含大量长石碎屑的砂岩类",        "沉积岩"),
    ("blaimorite",  "Blaimorite Rock",  "作者自创名称，没有对应的现实岩类",        "—"),
    ("blueschist",  "Blueschist Rock",  "蓝片岩，低温高压变质岩",                  "变质岩"),
    ("boninite",    "Boninite Rock",    "玻安岩，富镁的火山岩",                    "火成岩"),
    ("carbonatite", "Carbonatite Rock", "碳酸岩，以碳酸盐矿物为主的火成岩",        "火成岩"),
    ("cataclasite", "Cataclasite Rock", "碎裂岩，断层带常见的动力变质岩",          "变质岩"),
    ("foidolite",   "Foidolite Rock",   "似长石岩，含似长石类矿物的火成岩",        "火成岩"),
    ("greenschist", "Greenschist Rock", "绿片岩，低级变质岩",                      "变质岩"),
    ("jaspillite",  "Jaspillite Rock",  "碧玉铁质岩，条带状铁建造的一种",          "沉积岩"),
    ("mylonite",    "Mylonite Rock",    "糜棱岩，强剪切作用下的细粒变质岩",        "变质岩"),
    ("travertine",  "Travertine Rock",  "石灰华，温泉沉积形成的碳酸钙",            "沉积岩"),
    ("wackestone",  "Wackestone Rock",  "瓦克岩，含颗粒的碳酸盐岩",                "沉积岩"),
]

# 该岩石拥有的方块形态（从 lang 里 tile.tfc.*.<rock> 提取，各岩石一致）
FORMS = [
    ("raw",      "石块"),
    ("cobble",   "圆石"),
    ("smooth",   "平滑石"),
    ("bricks",   "石砖"),
    ("gravel",   "沙砾"),
    ("sand",     "沙"),
    ("clay",     "粘土"),
    ("dirt",     "土"),
    ("farmland", "耕地"),
    ("path",     "路径"),
    ("stairs",   "楼梯"),
    ("slab",     "台阶"),
    ("double_slab", "双台阶"),
    ("wall",     "墙"),
    ("button",   "按钮"),
    ("pressure_plate", "压力板"),
]


def iso_icon(tex_path: Path, size: int = 32) -> str:
    """单纹理等轴测立方体。"""
    if not tex_path.exists():
        return ""
    tex = Image.open(tex_path).convert("RGBA")
    S = 256
    # 等轴测顶点
    cx, cy = S / 2, S / 2
    w = S * 0.40
    h = w
    top_p = [(cx, cy - h), (cx + w, cy - h / 2), (cx, cy), (cx - w, cy - h / 2)]
    left_p = [(cx - w, cy - h / 2), (cx, cy), (cx, cy + h), (cx - w, cy + h / 2)]
    right_p = [(cx, cy), (cx + w, cy - h / 2), (cx + w, cy + h / 2), (cx, cy + h)]

    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    def shade(img, f):
        a = img.copy()
        px = a.load()
        for y in range(a.height):
            for x in range(a.width):
                r, g, b, al = px[x, y]
                px[x, y] = (int(r * f), int(g * f), int(b * f), al)
        return a

    def draw(poly, factor):
        t = shade(tex, factor)
        xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
        x0, x1 = int(min(xs)), int(max(xs)); y0, y1 = int(min(ys)), int(max(ys))
        if x1 <= x0 or y1 <= y0: return
        small = t.resize((x1 - x0, y1 - y0), Image.NEAREST)
        mask = Image.new("L", (S, S), 0)
        ImageDraw.Draw(mask).polygon([(p[0], p[1]) for p in poly], fill=255)
        layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        layer.paste(small, (x0, y0))
        canvas.paste(layer, (0, 0), mask)

    draw(top_p, 1.0)
    draw(left_p, 0.8)
    draw(right_p, 0.6)

    out = canvas.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def build_html(name: str, geo: str, kind: str, rid: str) -> str:
    parts = [f"<p>{name}是 TFC Rocks+ 向群峦传说添加的岩石类型。</p>", f"<p><strong>岩类</strong>：{geo}。</p>"]

    # 方块形态表
    rows = "".join(f"<tr><td>{zh}</td><td>tile.tfc.{f}.{rid}</td></tr>" for f, zh in FORMS)
    parts.append("<p><strong>方块形态</strong>：该岩石配有完整的一套建材，与原版岩石规格一致。</p>"
                 "<table><thead><tr><th>形态</th><th>注册名</th></tr></thead>"
                 f"<tbody>{rows}</tbody></table>")

    # 矿石
    parts.append("<p><strong>矿石伴生</strong>：群峦的矿石依附于岩石生成，这种岩石同样支持。"
                 "它会生成群峦全部矿物类型的伴生矿，从铜、锡、金、银等常见矿到铀、锰、铂、钨、钴等稀有品种。</p>")

    # 特有矿脉
    if rid == "jaspillite":
        parts.append("<p><strong>独有矿脉</strong>：Jaspillite Hematite（碧玉铁质岩赤铁矿）。"
                     "尺寸宽 10、高 5，簇状分布，生成于 Y 128 至 140，稀有度 90，密度 10，母岩仅限本岩石。</p>")

    parts.append("<p><strong>获取</strong>：与群峦原版岩石相同——地表可采碎石堆，或直接开采岩层。"
                 "石料加工沿用它那套系统，凿制与抛光配方通用。</p>")
    return "".join(parts)


def main() -> int:
    rows = []
    for rid, name, geo, kind in ROCKS:
        icon = iso_icon(TEXROOT / "raw" / f"{rid}.png")
        rows.append({
            "id": rid,
            "name": name,
            "ename": "",
            "regname": f"tfc:{rid}",
            "category": "岩石",
            "type": "物品/方块",
            "maxstack": 64,
            "remark": (
                "TFC Rocks+ 新增岩石资料页：名称与方块形态取自模组覆盖的 assets/tfc/lang/en_us.lang，"
                "矿脉参数取自 assets/tfc_rocksplus/config/tfc_rocks_plus_ores.json。"
                "一种岩石的多种方块形态合并在同一页，没有为每个形态单独建页。"
                f"{tail()}"
            ),
            "html": build_html(name, geo, kind, rid),
            "icon32": icon,
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)")
    noicon = [r["id"] for r in rows if not r["icon32"]]
    print(f"无图标 {len(noicon)} 个" + (f": {noicon}" if noicon else " ✓"))
    # 预览
    canvas = Image.new("RGBA", (len(rows) * 90, 100), (40, 40, 40, 255))
    for i, r in enumerate(rows):
        if r["icon32"]:
            im = Image.open(io.BytesIO(base64.b64decode(r["icon32"])))
            canvas.paste(im.resize((64, 64), Image.NEAREST), (i * 90 + 12, 18))
    prev = BASE / "trp-rocks-preview.png"
    canvas.save(prev)
    print(f"预览 → {prev}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
