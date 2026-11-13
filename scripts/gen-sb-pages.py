#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Strange Berries（classId 17728）—— 按审核意见改走「综合」。

审核原话：用综合，抽象资料内用一个表格把不同的效果、种植条件列出来就可以了。

数据来源：
  药水效果 / 饥饿值 / 饱和度  items/FoodComponents.java 的 FoodComponent 构造
  种植条件                 各 *BerryBush 类的 canPlaceOn（method_9695）+ lang 的 *_tooltip
  踩踏效果                 各 *BerryBush 类的 onEntityCollision（method_9548）
  图标                     16×16 纹理 NEAREST 放大

产出：
  sb-抽象资料-17728.json   1 条，正文含一张 16 行大表
  sb-子资料-17728.json     32 条（16 浆果 + 16 浆果丛），正文空
"""
import base64
import io
import json
import random
import re
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
SB = BASE / "sb/assets/strangeberries"
SRC = BASE / "sb-src"
ICONS128 = BASE / "sb-icons128"
ICONS32 = BASE / "sb-icons32"
OUT_ABSTRACT = BASE / "sb-抽象资料-17728.json"
OUT_CHILD = BASE / "sb-子资料-17728.json"
NS = "strangeberries"

_PAW = ["呜喵", "喵呜", "喵喵"]

# 效果 field → (中文名, 等级偏移说明)
# 等级 = amplifier + 1
EFFECT_ZH = {
    "field_5904": "速度",
    "field_5917": "急迫",
    "field_5910": "力量",
    "field_5924": "生命恢复",
    "field_5913": "跳跃提升",
    "field_5925": "夜视",
    "field_5918": "抗火",
    "field_5907": "抗性提升",
    "field_5915": "瞬间治疗",
    "field_5902": "漂浮",
    "field_5905": "隐身",
    "field_5923": "水下呼吸",
    "field_5900": "海豚的恩惠",
    "field_5898": "伤害吸收",
    "field_5912": "生命恢复",
}

ROMAN = {0: "I", 1: "II", 2: "III", 3: "IV", 4: "V"}

# 种植条件（从 canPlaceOn 的方块 + lang tooltip 对照得出）
PLANT = {
    "ascending": "草方块、泥土、雪块",
    "crimson_fire": "绯红菌岩、下界岩",
    "dolphin": "沙砾、黏土、沙子（仅水下）",
    "fruitful": "草方块、泥土、粗土",
    "golden": "仅金块",
    "haste": "石头、闪长岩、花岗岩、安山岩、沙砾",
    "healing": "草方块、泥土、粗土",
    "invisibility": "幽匿块、深板岩",
    "leaping": "草方块、泥土、粗土、泥",
    "night": "草方块、泥土、粗土、灰化土",
    "regeneration": "草方块、泥土、粗土",
    "resistance": "仅深板岩",
    "rotten": "草方块、泥土、粗土、灰化土",
    "sea": "沙砾、黏土、沙子（仅水下）",
    "speed": "草方块、泥土、粗土",
    "strength": "草方块、泥土、粗土、灰化土",
    "warped_fire": "诡异菌岩、下界岩",
}

# 16 种浆果： (id 前缀, 英文名, 饥饿, 饱和, [(effect, ticks, amp)])
BERRIES = [
    ("speed", "Speed Berries", 1, 1.0, [("field_5904", 200, 1)]),
    ("haste", "Haste Berries", 1, 1.0, [("field_5917", 200, 1)]),
    ("strength", "Strength Berries", 1, 1.0, [("field_5910", 200, 0)]),
    ("regeneration", "Regeneration Berries", 1, 1.0, [("field_5924", 200, 0)]),
    ("leaping", "Leaping Berries", 1, 1.0, [("field_5913", 200, 3)]),
    ("night", "Night Berries", 1, 1.0, [("field_5925", 400, 0)]),
    ("crimson_fire", "Crimson Fire Berries", 1, 1.0, [("field_5918", 200, 0)]),
    ("warped_fire", "Warped Fire Berries", 1, 1.0, [("field_5918", 200, 0)]),
    ("resistance", "Resist Berries", 1, 1.0, [("field_5907", 200, 0)]),
    ("healing", "Healing Berries", 1, 1.0, [("field_5915", 1, 0)]),
    ("ascending", "Ascending Berries", 1, 1.0, [("field_5902", 200, 0)]),
    ("invisibility", "Invisibility Berries", 1, 1.0, [("field_5905", 200, 0)]),
    ("golden", "Golden Berries", 4, 2.0, [("field_5898", 400, 0), ("field_5912", 400, 0)]),
    ("dolphin", "Dolphin Berries", 1, 1.0, [("field_5900", 200, 0)]),
    ("sea", "Sea Berries", 1, 1.0, [("field_5923", 200, 0)]),
    ("rotten", "Rotten Berries", 1, 1.0, []),
]


def b64(path: Path):
    if not path.exists():
        return ""
    buf = io.BytesIO()
    Image.open(path).convert("RGBA").save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def effect_text(effs) -> str:
    if not effs:
        return "无"
    parts = []
    for f, ticks, amp in effs:
        name = EFFECT_ZH.get(f, f)
        secs = ticks / 20
        lvl = ROMAN.get(amp, str(amp + 1))
        if name == "瞬间治疗":
            parts.append(f"{name} {lvl}")
        else:
            s = f"{secs:g} 秒"
            parts.append(f"{name} {lvl}（{s}）")
    return "、".join(parts)


def main() -> int:
    # ── 抽象资料 ──
    rows_html = ""
    for key, en, hunger, sat, effs in BERRIES:
        rows_html += (
            f"<tr><td>{en}</td><td>{hunger}</td><td>{sat:g}</td>"
            f"<td>{effect_text(effs)}</td><td>{PLANT[key]}</td></tr>"
        )

    abstract_html = (
        "<p>奇异浆果是一组可种植的莓果，共十六种。每种都由「浆果」与「浆果丛」两件组成："
        "浆果是可食用的物品，浆果丛是能种下的方块。</p>"

        "<p><strong>种植</strong>：把浆果种在符合条件的地面上会长成浆果丛，"
        "成熟分四个阶段，长到第三阶段后可以反复采摘。每种浆果对土质的要求各不相同——"
        "多数种在草方块与泥土上，少数只认金块、深板岩或下界岩。</p>"

        "<p><strong>采摘与踩踏</strong>：对成熟的浆果丛右键可采下 1~2 颗浆果；"
        "走上去则会被刺到，同时获得该浆果对应的效果（村民与狐狸除外）。"
        "所以浆果丛既能当作物，也能当一条铺在地上的效果触发带。</p>"

        "<p><strong>药水</strong>：模组新增了「浆果中毒」效果，以及对应的滞留药水、喷溅药水与 tipped arrow。"
        "被浆果丛刺死会有专门的死亡消息。</p>"

        "<table><thead><tr>"
        "<th>浆果</th><th>饥饿值</th><th>饱和度</th><th>食用效果</th><th>可种植于</th>"
        "</tr></thead><tbody>"
        + rows_html +
        "</tbody></table>"

        "<p><strong>说明</strong>：表中「食用效果」是吃下浆果获得的，"
        "踩到成熟的浆果丛也会获得同名效果但时长与等级不同；"
        "所有浆果的饥饿值都是 1（金浆果为 4），且都可以在饱食状态下食用。</p>"
    )

    abstract = [{
        "id": "strange_berries",
        "name": "奇异浆果",
        "ename": "Strange Berries",
        "regname": "",
        "category": "食物",
        "type": "物品/方块",
        "maxstack": 64,
        "remark": (
            "Strange Berries 抽象资料（图标与注册名留空）："
            "十六种浆果的饥饿值、饱和度与药水效果取自 items/FoodComponents.java 的 "
            "FoodComponent 构造，种植条件取自各 *BerryBush 类的 canPlaceOn 与 "
            "lang/en_us.json 下的 *_tooltip 条目，采摘与踩踏机制取自各 Bush 类的 "
            "onUse 与 onEntityCollision。"
            f"{tail()}"
        ),
        "html": abstract_html,
        "icon32": "",
        "icon128": "",
    }]
    OUT_ABSTRACT.write_text(json.dumps(abstract, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 32 条子资料 ──
    children = []
    for key, en, hunger, sat, effs in BERRIES:
        # 浆果（物品）
        children.append({
            "id": f"{key}_berries",
            "name": en,
            "ename": "",
            "regname": f"{NS}:{key}_berries",
            "category": "食物",
            "type": "物品/方块",
            "maxstack": 64,
            "remark": (
                f"Strange Berries 子资料（待综合）：物品 id 为 {NS}:{key}_berries，"
                "正文由抽象资料「奇异浆果」统一提供，本条不单独撰写。"
                f"{tail()}"
            ),
            "html": "",
            "icon32": b64(ICONS32 / f"{NS}__item_{key}_berries.png"),
            "icon128": b64(ICONS128 / f"{NS}__item_{key}_berries.png"),
        })
        # 浆果丛（方块）
        bush_name = en.replace(" Berries", " Berry Bush")
        children.append({
            "id": f"{key}_berry_bush",
            "name": bush_name,
            "ename": "",
            "regname": f"{NS}:{key}_berry_bush",
            "category": "作物",
            "type": "物品/方块",
            "maxstack": 64,
            "remark": (
                f"Strange Berries 子资料（待综合）：方块 id 为 {NS}:{key}_berry_bush，"
                f"模组 lang 里方块显示名与浆果物品相同（{en}），此处按 id 补全为 "
                f"{bush_name} 以免重名。正文由抽象资料「奇异浆果」统一提供。"
                f"{tail()}"
            ),
            "html": "",
            "icon32": b64(ICONS32 / f"{NS}__block_{key}_berry_bush.png"),
            "icon128": b64(ICONS128 / f"{NS}__block_{key}_berry_bush.png"),
        })

    OUT_CHILD.write_text(json.dumps(children, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"抽象资料 1 条 → {OUT_ABSTRACT.name}  ({OUT_ABSTRACT.stat().st_size/1024:.1f} KB)")
    print(f"  正文 {len(abstract_html)} 字符，表格 1 张 {len(BERRIES)} 行")
    print(f"子资料 {len(children)} 条 → {OUT_CHILD.name}  ({OUT_CHILD.stat().st_size/1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
