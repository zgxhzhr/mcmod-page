#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 CtE Custom Uniques（classId 5182）36 件独特装备的批量新增 JSON。

数据来源：
- 名称与描述：assets/ctecu/lang/en_us.json
- 属性、稀有度、阶级：data/mmorpg/unique_gears/<type>/<id>.json
- 图标：assets/ctecu/textures/items/<id>.png（弓弩取主纹理，不用 pulling 变体）

分类：武器（弓弩匕剑法杖魔杖）/ 防具（胸甲）/ 饰品（项链戒指护符火把）
"""
import base64
import io
import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("需要 Pillow", file=sys.stderr)
    sys.exit(1)

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
JAR = BASE / "ctecu"
ITEMS = json.loads((BASE / "ctecu-items.json").read_text(encoding="utf-8"))
TEX = JAR / "assets/ctecu/textures/items"
OUT = BASE / "ctecu-物品导入-5182.json"
NS = "ctecu"

# 装备类型 → 分类
CATEGORY = {
    "bow": "武器", "crossbow": "武器", "dagger": "武器", "sword": "武器",
    "staff": "武器", "wand": "武器", "gauntlets": "武器",
    "plate_chest": "防具", "chest": "防具",
    "charm": "饰品", "necklace": "饰品", "ring": "饰品", "torch": "饰品", "shield": "防具",
}

# 纹理文件名特例（装备 id 与纹理名不一致时）
TEX_ALIAS = {
    "unburstable_balloon_sword_frost": "unburstable_balloon_sword",
    "unburstable_balloon_sword_light": "unburstable_balloon_sword",
    # 弩的待机纹理才适合当图标（其余是 pulling_0/1/2 拉弦帧）
    "buriza_do_kyanon_crossbow": "buriza_do_kyanon_crossbow_standby",
    "doomslinger_crossbow": "doomslinger_crossbow_standby",
    "ichorstring_crossbow": "ichorstring_crossbow_standby",
}

# 属性 key 前缀 → 中文量级
MAGNITUDE = [
    ("very_high_", "极高"),
    ("slightly_high_", "较高"),
    ("high_", "高"),
    ("low_", "低"),
    ("very_low_", "很低"),
    ("tiny_", "微量"),
    ("major_plus_", "大幅提升"),
    ("plus_", "提升"),
    ("", ""),
]

STAT_ZH = {
    "physical_damage_flat": "物理伤害",
    "physical_damage_percent": "物理伤害百分比",
    "spell_damage_flat": "法术伤害",
    "attack_fire_damage_flat": "攻击火焰伤害",
    "attack_water_damage_flat": "攻击冰霜伤害",
    "attack_thunder_damage_flat": "攻击雷电伤害",
    "attack_nature_damage_flat": "攻击自然伤害",
    "spell_fire_damage_flat": "法术火焰伤害",
    "spell_water_damage_flat": "法术冰霜伤害",
    "increase_healing_flat": "治疗量",
    "critical_hit_percent": "暴击率",
    "critical_hit_flat": "暴击值",
    "critical_damage_percent": "暴击伤害",
    "health_flat": "生命值",
    "armor_flat": "护甲",
    "dexterity_flat": "敏捷",
    "strength_flat": "力量",
    "intelligence_flat": "智力",
    "all_attributes_flat": "全属性",
    "dodge_flat": "闪避",
    "lifesteal_flat": "生命偷取",
    "energy_regen_flat": "能量回复",
    "cdr_flat": "冷却缩减",
    "elemental_resist_flat": "元素抗性",
    "water_resist_flat": "冰霜抗性",
    "bonus_all_drops_flat": "掉落加成",
    "divine_skill_lvls_flat": "神圣技能等级",
    "ocean_skill_lvls_flat": "海洋技能等级",
    "hunting_skill_lvls_flat": "狩猎技能等级",
    "unholy_skill_lvls_flat": "邪恶技能等级",
    "physical_skill_lvls_flat": "物理技能等级",
}


def stat_zh(key: str) -> str:
    """把 Mine and Slash 的 stat key 转成可读中文。"""
    mag = ""
    body = key
    for prefix, label in MAGNITUDE:
        if prefix and key.startswith(prefix):
            mag = label
            body = key[len(prefix):]
            break
    if body.endswith("_percent"):
        name = body[: -len("_percent")] + "_percent"
    elif body.endswith("_flat"):
        name = body[: -len("_flat")] + "_flat"
    else:
        name = body
    cn = STAT_ZH.get(name) or STAT_ZH.get(body) or body.replace("_", " ")
    return f"{mag}{cn}"


def b64_png(path: Path, size: int = 32) -> str:
    img = Image.open(path).convert("RGBA")
    if img.size != (size, size):
        method = Image.NEAREST if img.width < size else Image.LANCZOS
        img = img.resize((size, size), method)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def build_html(r: dict) -> str:
    parts = [f"<p>{r['name']} 是 CtE Custom Uniques 添加的独特{ {'武器': '武器', '防具': '胸甲', '饰品': '饰品'}[CATEGORY[r['gear_type']]] }，"
             f"为 Mine and Slash 的装备体系提供，只能通过战利品掉落获得。</p>"]
    if r["desc"]:
        parts.append(f"<p><strong>物品描述</strong>：{r['desc']}</p>")
    # 属性
    prim = [stat_zh(s) for s in r["primary"]]
    uniq = [stat_zh(s) for s in r["unique"]]
    if prim:
        parts.append(f"<p><strong>主属性</strong>：{'、'.join(prim)}。掉落时固定带出。</p>")
    if uniq:
        parts.append(f"<p><strong>独特属性</strong>：{'、'.join(uniq)}。是这件装备专属的随机词条池。</p>")
    # 稀有度与阶级
    parts.append(f"<p><strong>稀有度</strong>：{r['rarity']}；<strong>阶级</strong>：{r['tier']}。"
                 f"稀有度越高越少见，阶级决定词条数值的档位。</p>")
    # 需求
    if r["req"]:
        need = []
        for k, v in r["req"].items():
            need.append(f"{ {'dexterity': '敏捷', 'strength': '力量', 'intelligence': '智力'}.get(k, k) } {v}")
        parts.append(f"<p><strong>装备需求</strong>：{'、'.join(need)}。</p>")
    return "".join(parts)


def main() -> int:
    rows, missing_tex = [], []
    for r in ITEMS:
        cat = CATEGORY.get(r["gear_type"], "饰品")
        tex_name = TEX_ALIAS.get(r["id"], r["id"])
        p = TEX / f"{tex_name}.png"
        if p.exists():
            icon = b64_png(p)
        else:
            icon = ""
            missing_tex.append(r["id"])
        rows.append({
            "id": r["id"],
            "name": r["name"],
            "ename": "",
            "regname": f"{NS}:{r['id']}",
            "category": cat,
            "type": "物品/方块",
            "maxstack": 1,
            "remark": ("CtE Custom Uniques 新增资料页：名称与描述取自 lang/en_us.json，"
                       "属性、稀有度与阶级取自 data/mmorpg/unique_gears 下的定义。辛苦喵呜机了"),
            "html": build_html(r),
            "icon32": icon,
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
    from collections import Counter
    print("分类:", dict(Counter(r["category"] for r in rows)))
    no_icon = [r["id"] for r in rows if not r["icon32"]]
    if no_icon:
        print(f"⚠ 无图标 {len(no_icon)} 个: {no_icon}")
    print()
    for r in rows[:5]:
        print(f"  {r['name']:<28} [{r['category']}] {len(r['html'])} 字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
