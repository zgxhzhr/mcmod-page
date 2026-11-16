#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nemo's Carpentry（classId 31737）物品/方块批量新增 JSON。

632 条 = 620 方块 + 12 门框物品。

正文规则（skill §「同类物品只写一条正文」）：
  - 按「家具类型」分组，每类只写第一条的正文（选 oak 那条作代表）
  - 同类其余留空，附言写明「需协助创建抽象类」
  - 页数照建，不因正文重复就少建

图标：icon32 + icon128 都给（新规则），来自 nc-icons128 下的模型渲染结果。
"""
import base64
import io
import json
import random
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
NC = BASE / "nc/assets/nemos-carpentry"
ICONS = BASE / "nc-icons128"
OUT = BASE / "nc-物品导入-31737.json"
NS = "nemos-carpentry"

_PAW = ["呜喵", "喵呜", "喵喵"]

WOODS = ["acacia", "bamboo", "birch", "cherry", "crimson", "dark_oak",
         "jungle", "mangrove", "oak", "pale_oak", "spruce", "warped"]

WOOD_ZH = {
    "acacia": "金合欢", "bamboo": "竹", "birch": "白桦", "cherry": "樱花",
    "crimson": "绯红", "dark_oak": "深色橡木", "jungle": "丛林",
    "mangrove": "红树", "oak": "橡木", "pale_oak": "苍白橡木",
    "spruce": "云杉", "warped": "诡异",
}

# 家具类型的说明模板
TYPE_DESC = {
    "chair": ("椅子", "模组的基础款椅子，直靠背、四条腿，没有软垫。"),
    "chair_pascal": ("Pascal 椅", "带软垫的椅子，软垫可染成十六种颜色。造型圆润，靠背略矮。"),
    "chair_felix": ("Felix 椅", "靠背更高的椅款，椅背延伸到头部以上。"),
    "chair_gregory": ("Gregory 椅", "造型较宽的椅款，座面与扶手都更开阔。"),
    "chair_lukas": ("Lukas 椅", "带软垫的椅款，另有纯木版本（Natural）。"),
    "chair_lukas_natural": ("Lukas 椅（纯木）", "Lukas 椅去掉软垫的版本，全木制作。"),
    "chair_tommy": ("Tommy 椅", "带软垫的椅款，靠背为竖条板结构。"),
    "chair_tommy_natural": ("Tommy 椅（纯木）", "Tommy 椅去掉软垫的版本，全木制作。"),
    "coffee_table": ("咖啡桌", "矮桌，桌面大而腿短，适合放在沙发或椅子前。"),
    "coffee_table_pascal": ("Pascal 咖啡桌", "咖啡桌的 Pascal 设计款。"),
    "standing_table": ("立桌", "高脚桌，只有一根中心柱支撑，适合吧台或站立使用。"),
    "table_the_classic": ("经典桌", "桌面较厚、单柱支撑的桌款。"),
    "park_bench": ("公园长椅", "长条形座椅，可坐多人，常用于户外场景。"),
    "barrel_seat": ("木桶座椅", "以木桶为造型的座椅，上沿有金属箍。"),
    "glass_door": ("玻璃门", "带玻璃的门，需要先放置配套门框。可双开，支持红石控制。"),
}

COLOR_ZH = {
    "white": "白色", "orange": "橙色", "magenta": "品红", "light_blue": "淡蓝",
    "yellow": "黄色", "lime": "黄绿", "pink": "粉色", "gray": "灰色",
    "light_gray": "淡灰", "cyan": "青色", "purple": "紫色", "blue": "蓝色",
    "brown": "棕色", "green": "绿色", "red": "红色", "black": "黑色",
}


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def b64(path: Path, size: int) -> str:
    if not path.exists():
        return ""
    im = Image.open(path).convert("RGBA")
    if im.size != (size, size):
        method = Image.NEAREST if im.width < size else Image.LANCZOS
        im = im.resize((size, size), method)
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def split_id(block_id: str):
    """拆成 (wood, type)。没有木种前缀的返回 (None, block_id)。"""
    for w in sorted(WOODS, key=len, reverse=True):
        if block_id.startswith(w + "_"):
            return w, block_id[len(w) + 1:]
    return None, block_id


def main() -> int:
    lang = json.loads((NC / "lang/en_us.json").read_text(encoding="utf-8"))
    blocks = [k.replace(f"block.{NS}.", "") for k in lang if k.startswith(f"block.{NS}.")]
    items = [k.replace(f"item.{NS}.", "") for k in lang if k.startswith(f"item.{NS}.")]

    rows = []
    # 每类是否已写过正文
    written = set()

    # ── 620 个方块 ──
    for bid in sorted(blocks):
        wood, ftype = split_id(bid)
        en_name = lang[f"block.{NS}.{bid}"]

        icon128 = ICONS / f"{NS}__block_{bid}.png"
        icon32 = b64(icon128, 32)
        icon128b = b64(icon128, 128)

        # 分组键：有木种按类型分组，无木种各自独立
        group = ftype if wood else bid

        if group in written:
            html = ""
            note = (f"同类家具的正文已集中在「{group}」的首条页面，本条留空，"
                    "需协助创建抽象类以统一展示。")
        else:
            written.add(group)
            html = ""
            note = ""
            if wood and ftype in TYPE_DESC:
                zh, desc = TYPE_DESC[ftype]
                html = (
                    f"<p>{en_name}是 Nemo's Carpentry 添加的{zh}，材质为"
                    f"{WOOD_ZH.get(wood, wood)}。</p>"
                    f"<p><strong>造型</strong>：{desc}</p>"
                    "<p><strong>木材</strong>：同一种造型有十二种木材可选，本条目为其中一种。"
                    "更换木材只改变材质，几何形状完全一致。</p>"
                    "<p><strong>合成</strong>：在木工工作台中制作，用对应木材加工而成。</p>"
                )
                note = f"本条为「{group}」类的正文代表页，同类其余木材变体留空。"
            elif ftype.startswith("stained_glass_door"):
                color = ftype.replace("_stained_glass_door", "")
                zh, _ = TYPE_DESC["glass_door"]
                html = (
                    f"<p>{en_name}是 Nemo's Carpentry 添加的染色玻璃门，"
                    f"门框材质为{WOOD_ZH.get(wood, wood)}，玻璃为{COLOR_ZH.get(color, color)}。</p>"
                    f"<p><strong>用途</strong>：与原版门功能一致，可双开，支持红石控制。"
                    "安装前需要先在地面放置配套的门框。</p>"
                    "<p><strong>颜色</strong>：玻璃有十六种染色版本，另有不染色的普通玻璃门。</p>"
                )
                note = f"本条为「{group}」类的正文代表页。"
            elif ftype.startswith("glass_door") or ftype.startswith("_chair_pascal"):
                zh, desc = TYPE_DESC.get("glass_door", ("门", ""))
                html = (
                    f"<p>{en_name}是 Nemo's Carpentry 添加的{zh}，"
                    f"门框材质为{WOOD_ZH.get(wood, wood)}。</p>"
                    f"<p><strong>说明</strong>：{desc}</p>"
                )
                note = f"本条为「{group}」类的正文代表页。"
            elif ftype.endswith("_chair_pascal"):
                color = ftype.replace("_chair_pascal", "")
                html = (
                    f"<p>{en_name}是 Nemo's Carpentry 添加的 Pascal 椅，"
                    f"木材为{WOOD_ZH.get(wood, wood)}，软垫为{COLOR_ZH.get(color, color)}。</p>"
                    "<p><strong>造型</strong>：带软垫的椅款，靠背略矮、整体圆润。"
                    "软垫有十六种染色版本。</p>"
                    "<p><strong>合成</strong>：在木工工作台中制作。</p>"
                )
                note = f"本条为「{group}」类的正文代表页。"
            else:
                html = (
                    f"<p>{en_name}是 Nemo's Carpentry 添加的家具，"
                    f"木材为{WOOD_ZH.get(wood, wood)}。</p>"
                    "<p><strong>合成</strong>：在木工工作台中制作。</p>"
                )
                note = f"本条为「{group}」类的正文代表页。"

        rows.append({
            "id": f"block_{bid}",
            "name": en_name,
            "ename": "",
            "regname": f"{NS}:{bid}",
            "category": "家具",
            "type": "物品/方块",
            "maxstack": 64,
            "remark": (
                "Nemo's Carpentry 新增方块资料页：名称取自 lang/en_us.json，"
                "图标由该方块的 blockstate → 模型按 elements 与 UV 渲染，还原游戏内实际外观。"
                + note + tail()
            ),
            "html": html,
            "icon32": icon32,
            "icon128": icon128b,
        })

    # ── 12 个门框物品 ──
    for it in sorted(items):
        en_name = lang[f"item.{NS}.{it}"]
        wood = it.replace("_glass_door_frame", "")
        icon128 = ICONS / f"{NS}__item_{it}.png"

        if "door_frame" in written:
            html = ""
            note = ("同类物品的正文已集中在首条页面，本条留空，"
                    "需协助创建抽象类以统一展示。")
        else:
            written.add("door_frame")
            html = (
                "<p>玻璃门框是 Nemo's Carpentry 添加的门配件，是安装玻璃门的前提。</p>"
                "<p><strong>用途</strong>：先在地面放置门框，再把玻璃门装到门框上。"
                "没有门框的门无法直接放置。</p>"
                "<p><strong>木材</strong>：十二种木材各有一种门框，材质需要与门保持一致。</p>"
                "<p><strong>合成</strong>：在木工工作台中制作。</p>"
            )
            note = "本条为「门框」类的正文代表页，同类其余木材变体留空。"

        rows.append({
            "id": f"item_{it}",
            "name": en_name,
            "ename": "",
            "regname": f"{NS}:{it}",
            "category": "门配件",
            "type": "物品/方块",
            "maxstack": 64,
            "remark": (
                "Nemo's Carpentry 新增资料页：名称取自 lang/en_us.json，"
                "图标使用该物品的独立纹理（平面物品，按 NEAREST 放大）。"
                + note + tail()
            ),
            "html": html,
            "icon32": b64(icon128, 32),
            "icon128": b64(icon128, 128),
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT.name}  ({OUT.stat().st_size/1024/1024:.2f} MB)")
    print(f"有正文的 {sum(1 for r in rows if r['html'])} 条")
    noicon = [r["id"] for r in rows if not r["icon32"] or not r["icon128"]]
    print(f"缺图标 {len(noicon)} 个" + (f": {noicon[:5]}" if noicon else " ✓"))
    from collections import Counter
    print("分类:", dict(Counter(r["category"] for r in rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
