#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 gmm 反编译源码里提取每种生物的战斗属性。

createAttributes() 返回的 AttributeSupplier.Builder 用 SRG 名注册属性：
  f_22276_ = MAX_HEALTH         f_22279_ = MOVEMENT_SPEED
  f_22281_ = ATTACK_DAMAGE      f_22277_ = FOLLOW_RANGE
  f_22278_ = KNOCKBACK_RESISTANCE   f_22280_ = FLYING_SPEED
  f_22282_ = ATTACK_KNOCKBACK   f_22283_ = ATTACK_SPEED
  f_22284_ = ARMOR              f_22285_ = ARMOR_TOUGHNESS
"""
import json
import re
from pathlib import Path

SRC = Path(r"E:\Mod\百科-语料\jar-analyze\gmm-src")
BASE = Path(r"E:\Mod\百科-语料\jar-analyze")

ATTR = {
    "f_22276_": "max_health",
    "f_22277_": "follow_range",
    "f_22278_": "knockback_resistance",
    "f_22279_": "movement_speed",
    "f_22280_": "flying_speed",
    "f_22281_": "attack_damage",
    "f_22282_": "attack_knockback",
    "f_22283_": "attack_speed",
    "f_22284_": "armor",
    "f_22285_": "armor_toughness",
}

# 关注 dungeons2 用到的生物（全名 → jar id）
WANTED = {
    "Rat": "rat", "GiantRat": "giant_rat",
    "Shrieker": "shrieker", "VioletFungus": "violet_fungus",
    "SkeletonWarrior": "skeleton_warrior", "WingedSkeleton": "winged_skeleton",
    "IronSkeleton": "iron_skeleton", "MagmaSkeleton": "magma_skeleton",
    "TaintedSkeleton": "tainted_skeleton", "AcidSkeleton": "acid_skeleton",
    "ElectricSkeleton": "electric_skeleton", "BurningSkeleton": "burning_skeleton",
    "BloodyBones": "bloody_bones", "SkeletonChampion": "skeleton_champion",
    "Bloater": "bloater", "GraveZombie": "grave_zombie", "Wight": "wight",
    "Bodak": "bodak", "Beholder": "beholder", "DeathTyrant": "death_tyrant",
    "Spectator": "spectator", "Daemon": "daemon", "Ghoul": "ghoul",
    "GelatinousCube": "gelatinous_cube", "OchreJelly": "ochre_jelly",
    "GrayOoze": "gray_ooze", "BlackPudding": "black_pudding",
    "AnimatedArmor": "animated_armor", "AnimatedWeapon": "animated_weapon",
    "Gargoyle": "gargoyle", "Margoyle": "margoyle",
    "Orc": "orc", "OrcShaman": "orc_shaman", "OrcWarlord": "orc_warlord",
    "AlligatorGar": "alligator_gar", "Leech": "leech", "GiantLeech": "giant_leech",
    "Minotaur": "minotaur", "StoneColossus": "stone_colossus",
    "VanillaChestMimic": "vanilla_chest_mimic", "BarrelMimic": "barrel_mimic",
}


def parse_attrs(text: str) -> dict:
    """从 createAttributes 里抓所有 m_22268_(Attributes.f_XXXXX_, 数值)"""
    out = {}
    for m in re.finditer(r"m_22268_\(\s*Attributes\.(f_\d+_)\s*,\s*([\d.]+)\s*\)", text):
        key = ATTR.get(m.group(1))
        if key:
            out[key] = float(m.group(2))
    return out


def parse_goals(text: str) -> list:
    """抓 addGoal 里的 Goal 类名。"""
    goals = []
    for m in re.finditer(r"new (\w+)(?:<[^>]*>)?\(", text):
        name = m.group(1)
        if name.endswith("Goal"):
            if name not in goals:
                goals.append(name)
    return goals


# Monster.createMonsterAttributes() 的基线值，类里没覆盖时用这些
MONSTER_DEFAULTS = {
    "max_health": 20.0,
    "attack_damage": 2.0,
    "movement_speed": 0.7,
    "follow_range": 16.0,
    "armor": 0.0,
    "armor_toughness": 0.0,
    "knockback_resistance": 0.0,
}


def main() -> int:
    results = {}
    seen_classes = set()
    for f in SRC.rglob("*.java"):
        stem = f.stem
        if stem not in WANTED or stem in seen_classes:
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        # 有些类的属性方法被 CFR 映射成 SRG 名（如 m_21552_），不能只认 createAttributes
        if "m_22268_" not in text and "m_22266_" not in text:
            continue
        attrs = parse_attrs(text)
        if not attrs:
            continue
        seen_classes.add(stem)
        for k, v in MONSTER_DEFAULTS.items():
            attrs.setdefault(k, v)
        results[WANTED[stem]] = {
            "class": stem,
            "file": str(f.relative_to(SRC)),
            "attrs": attrs,
            "goals": parse_goals(text),
            "extends": re.search(r"public class \w+ extends (\w+)", text).group(1)
            if re.search(r"public class \w+ extends (\w+)", text) else "?",
        }

    print(f"提取到 {len(results)} / {len(WANTED)} 种生物的属性\n")
    missing = [v for k, v in WANTED.items() if v not in results]
    if missing:
        print(f"⚠ 未提取到：{missing}\n")

    print(f"{'生物':<22} {'血量':>6} {'伤害':>6} {'速度':>7} {'跟随':>6}  行为")
    print("-" * 90)
    for jar_id, d in sorted(results.items(), key=lambda x: -(x[1]["attrs"].get("max_health", 0))):
        a = d["attrs"]
        goals = ",".join(g.replace("Goal", "") for g in d["goals"][:4])
        print(f"{jar_id:<22} {a.get('max_health', 0):>6.0f} {a.get('attack_damage', 0):>6.1f} "
              f"{a.get('movement_speed', 0):>7.2f} {a.get('follow_range', 0):>6.0f}  {goals}")

    out = BASE / "gmm-mob-attrs.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已保存 → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
