#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mine & Slash Expansion（classId 5180）物品批量新增 JSON。

共 80 件：8 法术 + 54 工具（9 类 × 6 级）+ 18 材料（3 种 × 6 级）

名称来源：lang/zh_cn.json。注意该文件有若干语法错误（`un普通ingot` 键名混入中文、
重复键、多余引号），这里只取其中有效的译名，坏掉的键回退到 en_us 的正常写法。
Excalator 系列在 zh_cn 里被错译成 "Hamavator"，没有可用中文，按规则保留英文。

图标来源：models/item/*.json 的 textures.layer0，纹理是 64×64（不是 16×16）。
"""
import base64
import io
import json
import random
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
MOD = BASE / "mse"
ASSETS = MOD / "assets/mineandslashexpansion"
TEX = ASSETS / "textures"
OUT = BASE / "mse-物品导入-5180.json"
NS = "mineandslashexpansion"

_PAW = ["呜喵", "喵呜", "喵喵"]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


# ── 等级 ──
# (注册名片段, 中文前缀, 采集等级, 耐久, 挖掘速度, 攻击伤害)
TIERS = [
    ("common",    "普通", 0, 128,  4.0,  1.0),
    ("uncommon",  "罕见", 1, 256,  8.0,  2.0),
    ("rare",      "稀有", 2, 512,  12.0, 4.0),
    ("epic",      "史诗", 3, 1024, 16.0, 8.0),
    ("legendary", "传说", 4, 2048, 20.0, 16.0),
    ("mythical",  "神话", 5, 4096, 24.0, 32.0),
]

# ── 工具：注册名后缀, 中文名, 说明, 是否范围工具
TOOLS = [
    ("pickaxe",   "镐子",   "常规采矿工具，可以挖掘石头与矿石", False, "pickaxe"),
    ("axe",       "斧子",   "伐木工具，也能当武器用", False, "axe"),
    ("shovel",    "铲子",   "挖掘泥土、沙与沙砾", False, "shovel"),
    ("hoe",       "锄头",   "耕地工具", False, "hoe"),
    ("fishingrod", "鱼竿",  "钓鱼工具", False, "fishingrod"),
    ("hammer",    "锤子",   "一次破坏正对方位的 3×3 方块，适合开采矿脉", True, "hammer"),
    ("excavator", "挖掘器", "一次破坏正对方位的 3×3 方块，适合清理土方", True, "excavator"),
    ("stairs",    "Excalator", "阶梯式挖掘，一次破出斜向通道", True, "excalator"),
    ("hamavator", "Hamavator", "锤与锹的合体，用于范围挖掘的通用款", True, "hamavator"),
]

# ── 材料：注册名片段, 中文名
MATERIALS = [
    # 注册名片段, 中文名, 纹理目录名（注意目录是复数）, 说明
    ("ingot",           "锭",     "ingots",           "对应某一稀有度工具的基础材料"),
    ("mixedingot",      "混合锭", "mixedingots",      "由多种材料熔合而成，用于中高档工具"),
    ("compressedingot", "压缩锭", "compressedingots", "密度更高的一档材料，用于高阶工具"),
]

# ── 法术：注册名, 中文名, 效果, 图标
SPELLS = [
    ("spell_selffeed",            "饱腹",         "恢复饥饿值",           "spellbookicon"),
    ("spell_selfhaste",           "急促",         "提升挖掘速度",         "spellbookicon2"),
    ("spell_selfjump",            "跳跃提升",     "提升跳跃高度",         "spellbookicon3"),
    ("spell_selfspeed",           "迅疾",         "提升移动速度",         "spellbookicon4"),
    ("spell_selffeather",         "羽落",         "减免摔落伤害",         "spellbookicon5"),
    ("spell_selfnightvision",     "全体夜视",     "获得夜视效果",         "spellbookicon"),
    ("spell_selfbreath",          "全体水肺",     "获得水下呼吸",         "spellbookicon2"),
    ("spell_selffireprotection",  "全体火焰保护", "获得抗火效果",         "spellbookicon3"),
]


def load_icon(rel: str) -> str:
    """rel 形如 'items/tools/pickaxe/common'，不含扩展名。"""
    p = TEX / f"{rel}.png"
    if not p.exists():
        return ""
    img = Image.open(p).convert("RGBA")
    if img.size != (32, 32):
        img = img.resize((32, 32), Image.LANCZOS if img.width > 32 else Image.NEAREST)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def tier_rows() -> str:
    rows = []
    for _, zh, harvest, uses, eff, dmg in TIERS:
        rows.append(f"<tr><td>{zh}</td><td>{harvest}</td><td>{uses}</td><td>{eff}</td><td>{dmg}</td></tr>")
    return "".join(rows)


def tool_html(zh_full: str, desc: str, harvest: int, uses: int, eff: float, dmg: float, ranged: bool) -> str:
    parts = [f"<p>{zh_full}是 Mine &amp; Slash Expansion 添加的工具，按稀有度分为六档，这一件是其中一档。</p>",
             f"<p><strong>属性</strong>：采集等级 {harvest}，耐久 {uses}，挖掘速度 {eff}，攻击伤害 {dmg}，附魔能力 30。</p>",
             f"<p><strong>用途</strong>：{desc}。</p>"]
    if ranged:
        parts.append("<p><strong>范围挖掘</strong>：一次破掉正对方向上的 3×3 方块（跳过中心），"
                     "掉落走正常判定，时运与精准采集都生效。</p>")
    parts.append("<p><strong>等级对比</strong>：同系列六档的耐久与攻击伤害逐级翻倍，挖掘速度每级 +4。</p>"
                 "<table><thead><tr><th>等级</th><th>采集</th><th>耐久</th><th>挖掘速度</th><th>攻击</th></tr></thead>"
                 f"<tbody>{tier_rows()}</tbody></table>")
    parts.append("<p><strong>获取</strong>：由对应等级的金属锭合成，材料见模组页。</p>")
    return "".join(parts)


def material_html(zh_full: str, desc: str, tier_zh: str, uses: int) -> str:
    return (f"<p>{zh_full}是 Mine &amp; Slash Expansion 添加的材料，用于合成对应等级的工具。</p>"
            f"<p><strong>用途</strong>：{desc}。该档材料对应{uses} 耐久那一级的工具。</p>"
            f"<p><strong>等级</strong>：本材料属于{ tier_zh }档，同系列共六档（普通至神话）。</p>"
            "<p><strong>获取</strong>：由其他材料合成或从战利品中取得，具体配方见模组页。</p>")


def spell_html(zh_full: str, effect: str) -> str:
    return (f"<p>{zh_full}是 Mine &amp; Slash Expansion 添加的自身增益法术。</p>"
            f"<p><strong>效果</strong>：使用后{effect}，只作用于使用者本人。</p>"
            "<p><strong>用法</strong>：像挖矿与砍杀本体的法术一样使用，一次性消耗。</p>"
            "<p><strong>属性显示</strong>：效果会挂在本体的属性条目上，因此能吃属性加成与词条体系。</p>")


def main() -> int:
    rows = []

    # 工具 54
    for suffix, tool_zh, tool_desc, ranged, tdir in TOOLS:
        for tid, tier_zh, harvest, uses, eff, dmg in TIERS:
            rid = f"{tid}{suffix}"
            # 英文名用于 ename：Common Pickaxe 这种
            en = f"{tid.capitalize()} {tool_zh if tool_zh.isascii() else {'pickaxe':'Pickaxe','axe':'Axe','shovel':'Shovel','hoe':'Hoe','fishingrod':'Fishing Rod','hammer':'Hammer','excavator':'Excavator','stairs':'Excalator','hamavator':'Hamavator'}[suffix]}"
            zh_full = f"{tier_zh} {tool_zh}"
            rows.append({
                "id": rid,
                "name": zh_full,
                "ename": en,
                "regname": f"{NS}:{rid}",
                "category": "工具",
                "type": "物品/方块",
                "maxstack": 1,
                "remark": (
                    "Mine & Slash Expansion 新增资料页：中文名取自 lang/zh_cn.json。"
                    "采集等级、耐久、挖掘速度与攻击伤害取自 ToolTier 枚举里该档的构造参数，"
                    "范围挖掘逻辑取自 ToolsFuntionNormal.attemptBreakNeighbors。"
                    f"{tail()}"
                ),
                "html": tool_html(zh_full, tool_desc, harvest, uses, eff, dmg, ranged),
                "icon32": load_icon(f"items/tools/{tdir}/{tid}"),
            })

    # 材料 18
    for msuffix, mzh, mdir, mdesc in MATERIALS:
        for tid, tier_zh, harvest, uses, eff, dmg in TIERS:
            rid = f"{tid}{msuffix}"
            en = f"{tid.capitalize()} {mzh if mzh.isascii() else {'锭':'Ingot','混合锭':'Mixed Ingot','压缩锭':'Compressed Ingot'}[mzh]}"
            zh_full = f"{tier_zh} {mzh}"
            rows.append({
                "id": rid,
                "name": zh_full,
                "ename": en,
                "regname": f"{NS}:{rid}",
                "category": "材料",
                "type": "物品/方块",
                "maxstack": 64,
                "remark": (
                    "Mine & Slash Expansion 新增资料页：中文名取自 lang/zh_cn.json"
                    "（其中 uncommon 锭的键名在 lang 里被误写成中文，已按 en_us 的写法对齐）。"
                    "材料与工具等级的对应关系取自 ToolTier 枚举。"
                    f"{tail()}"
                ),
                "html": material_html(zh_full, mdesc, tier_zh, uses),
                "icon32": load_icon(f"items/ingredents/{mdir}/{tid}"),
            })

    # 法术 8
    for rid, zh, effect, icon in SPELLS:
        rows.append({
            "id": rid,
            "name": zh,
            "ename": "",
            "regname": f"{NS}:{rid}",
            "category": "法术",
            "type": "物品/方块",
            "maxstack": 1,
            "remark": (
                "Mine & Slash Expansion 新增资料页：中文名取自 lang/zh_cn.json。"
                "效果依据 mmorpg.stat 下的属性条目与法术注册定义。"
                f"{tail()}"
            ),
            "html": spell_html(zh, effect),
            "icon32": load_icon(f"items/spells/{icon}"),
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)")
    from collections import Counter
    print("分类:", dict(Counter(r["category"] for r in rows)))
    noicon = [r["id"] for r in rows if not r["icon32"]]
    print(f"无图标 {len(noicon)} 个" + (f": {noicon[:8]}" if noicon else " ✓"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
