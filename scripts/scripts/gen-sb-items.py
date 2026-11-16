#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Strange Berries（classId 17728）16 浆果 + 16 灌木，共 32 条批量新增 JSON。

数据来源：
- 名称：assets/strangeberries/lang/en_us.json（只有 en_us，无 zh_cn）
- 效果：FoodComponents 里每个浆果的 StatusEffectInstance（时长 + 等级）
- 食物属性：hunger / saturationModifier
- 种植基质：lang 里各 *_tooltip 的说明
- 灌木生长：blockstates/render_type 为 cross 模型，4 个阶段（stage0-3）

图标：浆果用 textures/item/<id>.png；灌木用成熟的 stage3 纹理直接放大（cross 模型不适合等轴测）。
"""
import base64
import io
import json
import random
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
MOD = BASE / "sb"
ASSETS = MOD / "assets/strangeberries"
OUT = BASE / "sb-物品导入-17728.json"
NS = "strangeberries"

_PAW = ["呜喵", "喵呜", "喵喵"]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


# id, 显示名, 饥饿值, 饱和系数, 效果, 时长(秒), 等级, 基质
BERRIES = [
    ("speed_berries",             "Speed Berries",             1, 1.0, "速度提升",           10, "II", "草方块、泥土、粗土"),
    ("haste_berries",             "Haste Berries",             1, 1.0, "急迫",               10, "II", "石头、闪长岩、花岗岩、安山岩、沙砾"),
    ("strength_berries",          "Strength Berries",          1, 1.0, "力量",               10, "I",  "草方块、泥土、粗土、灰化土"),
    ("regeneration_berries",      "Regeneration Berries",      1, 1.0, "生命恢复",           10, "I",  "草方块、泥土、粗土、灰化土"),
    ("leaping_berries",           "Leaping Berries",           1, 1.0, "跳跃提升",           10, "IV", "草方块、泥土、粗土、泥巴"),
    ("night_berries",             "Night Berries",             1, 1.0, "夜视",               20, "I",  "草方块、泥土、粗土、灰化土"),
    ("crimson_fire_berries",      "Crimson Fire Berries",      1, 1.0, "抗火",               10, "I",  "绯红菌岩、下界岩"),
    ("warped_fire_berries",       "Warped Fire Berries",       1, 1.0, "抗火",               10, "I",  "诡异菌岩、下界岩"),
    ("resistance_berries",        "Resist Berries",            1, 1.0, "抗性提升",           10, "I",  "仅深板岩"),
    ("healing_berries",           "Healing Berries",           1, 1.0, "瞬间治疗",            0, "I",  "草方块、泥土、粗土、灰化土"),
    ("ascending_berries",         "Ascending Berries",         1, 1.0, "漂浮",               10, "I",  "草方块、泥土、雪块"),
    ("invisibility_berries",      "Invisibility Berries",      1, 1.0, "隐身",               10, "I",  "幽匿块、深板岩"),
    ("dolphin_berries",           "Dolphin Berries",           1, 1.0, "海豚的恩惠",         10, "I",  "沙砾、粘土、沙（须在水下）"),
    ("sea_berries",               "Sea Berries",               1, 1.0, "水下呼吸",           10, "I",  "沙砾、粘土、沙（须在水下）"),
    ("golden_berries",            "Golden Berries",            4, 2.0, "生命提升 + 伤害吸收", 20, "I",  "仅金块"),
    ("rotten_berries",            "Rotten Berries",            1, 1.0, None,                  0, None, "草方块、泥土、粗土、灰化土"),
]


def b64(path: Path) -> str:
    if not path.exists():
        return ""
    img = Image.open(path).convert("RGBA")
    if img.size != (32, 32):
        method = Image.NEAREST if img.width < 32 else Image.LANCZOS
        img = img.resize((32, 32), method)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def berry_html(name: str, hunger: int, sat: float, effect, secs: int, level, soil: str) -> str:
    parts = [f"<p>{name}是 Strange Berries 添加的浆果，食用后获得状态效果。</p>"]
    if effect:
        if secs > 0:
            parts.append(f"<p><strong>效果</strong>：食用后获得 {secs} 秒的{effect} {level}。</p>")
        else:
            parts.append(f"<p><strong>效果</strong>：食用后立即获得{effect} {level}。</p>")
    else:
        parts.append("<p><strong>效果</strong>：不附带任何状态效果。</p>")
    parts.append(f"<p><strong>食物属性</strong>：回复 {hunger} 点饥饿值，{hunger * sat:g} 点饱和度。</p>")
    parts.append(f"<p><strong>种植</strong>：种下后灌木长在该方块上，可用基质为{soil}。</p>")
    parts.append("<p><strong>获取</strong>：在野外找到对应灌木直接采摘，或把采到的浆果种在可用基质上繁殖。</p>")
    return "".join(parts)


def bush_html(name: str, effect, secs: int, level, soil: str) -> str:
    parts = [f"<p>{name}对应的灌木方块，是 Strange Berries 中该品种的生长形态。</p>",
             f"<p><strong>生长</strong>：经历 4 个阶段长成，成熟后右击采摘，掉落 1 到 2 个浆果，随后退回未成熟状态重新生长。</p>",
             f"<p><strong>种植条件</strong>：只能种在{soil}上，基质不符时不生长。</p>"]
    if effect:
        parts.append(f"<p><strong>可获得的浆果</strong>：食用后提供{effect}"
                     + (f" {level}，持续 {secs} 秒" if secs > 0 else "，立即生效")
                     + "。</p>")
    else:
        parts.append("<p><strong>可获得的浆果</strong>：该品种的浆果不附带任何状态效果。</p>")
    parts.append("<p><strong>注意</strong>：灌木带刺，接触会持续受到伤害。</p>")
    return "".join(parts)


def main() -> int:
    rows = []
    TEXBLOCK = ASSETS / "textures/block"
    TEXITEM = ASSETS / "textures/item"

    for rid, name, hunger, sat, effect, secs, level, soil in BERRIES:
        # 浆果
        rows.append({
            "id": rid,
            "name": name,
            "ename": "",
            "regname": f"{NS}:{rid}",
            "category": "食物",
            "type": "物品/方块",
            "maxstack": 64,
            "remark": (
                "Strange Berries 新增资料页：名称取自 lang/en_us.json（模组只有 en_us）。"
                "饥饿值与饱和度系数取自 FoodComponents 里该浆果的 FoodComponent，"
                "效果时长与等级取自同处的 StatusEffectInstance，可用基质取自 lang 里的 tooltip。"
                f"{tail()}"
            ),
            "html": berry_html(name, hunger, sat, effect, secs, level, soil),
            "icon32": b64(TEXITEM / f"{rid}.png"),
        })

        # 灌木：block id 是去掉 _berries 换成 _berry_bush
        bush_id = rid.replace("_berries", "_berry_bush")
        rows.append({
            "id": bush_id,
            "name": name,
            "ename": "",
            "regname": f"{NS}:{bush_id}",
            "category": "植物",
            "type": "物品/方块",
            "maxstack": 64,
            "remark": (
                "Strange Berries 新增方块资料页：名称取自 lang/en_us.json 里该灌木的 block 条目。"
                "四个生长阶段与可种植基质取自 blockstates 与 lang 的 tooltip；"
                "图标使用成熟阶段 stage3 的纹理。"
                f"{tail()}"
            ),
            "html": bush_html(name, effect, secs, level, soil),
            "icon32": b64(TEXBLOCK / f"{bush_id}_stage3.png"),
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)")
    from collections import Counter
    print("分类:", dict(Counter(r["category"] for r in rows)))
    noicon = [r["id"] for r in rows if not r["icon32"]]
    print(f"无图标 {len(noicon)} 个" + (f": {noicon}" if noicon else " ✓"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
