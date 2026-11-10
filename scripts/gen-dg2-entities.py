#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dungeons 2（classId 2475）实体页批量新增 JSON。

41 种生物的属性来自 gmm（gottsch's Monster Manual）反编译源码：
  createAttributes() 里 m_22268_(Attributes.f_XXXXX_, 数值) 的 SRG 属性映射。
giant_rat / giant_leech 由 dungeons2 自己定义，单列。

模组只有 en_us.json，名称用英文；实体无图标，icon32 留空（脚本会勾选删除大小图标）。
"""
import json
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
OUT = BASE / "dg2-实体导入-2475.json"
NS = "dungeons2"
ATTRS = json.loads((BASE / "gmm-mob-attrs.json").read_text(encoding="utf-8"))
LANG = json.loads((BASE / "dg2/assets/dungeons2/lang/en_us.json").read_text(encoding="utf-8"))

# 分类：敌对 / 非敌对
HOSTILE = {
    "rat", "giant_rat", "skeleton_warrior", "winged_skeleton", "iron_skeleton",
    "magma_skeleton", "tainted_skeleton", "acid_skeleton", "electric_skeleton",
    "burning_skeleton", "bloody_bones", "skeleton_champion", "bloater",
    "grave_zombie", "wight", "bodak", "beholder", "death_tyrant", "spectator",
    "daemon", "ghoul", "gelatinous_cube", "ochre_jelly", "gray_ooze",
    "black_pudding", "animated_armor", "animated_weapon", "gargoyle",
    "margoyle", "orc", "orc_shaman", "orc_warlord", "alligator_gar", "leech",
    "giant_leech", "minotaur", "stone_colossus", "vanilla_chest_mimic",
    "barrel_mimic",
}
NEUTRAL = {"shrieker", "violet_fungus"}

# 中文行为描述映射
GOAL_ZH = {
    "MeleeAttack": "近战攻击",
    "ExtendedReachMeleeAttack": "长距离近战攻击",
    "TallMeleeAttack": "高个子近战攻击",
    "PassiveMeleeAttack": "被动近战",
    "ChargeAttack": "冲锋",
    "GroundSlam": "砸地",
    "ThrowBoulder": "投掷巨石",
    "ThrowProjectile": "投掷投射物",
    "CastSpell": "施放法术",
    "DaemonShootSpells": "发射法术",
    "WeightedChanceSummon": "概率召唤援军",
    "SummonThrall": "召唤仆从",
    "Summon": "召唤",
    "Enthrall": "魅惑",
    "Stalk": "潜行接近",
    "Dormancy": "休眠后苏醒",
    "ProximityActivate": "接近时激活",
    "RaiseShield": "举盾",
    "HuntingBreakDoor": "破门追击",
    "ReturnToWater": "返回水中",
    "RandomSwimming": "随机游动",
    "VolantCombat": "空中战斗",
    "VolantLand": "落地",
    "FlyToMeleeRange": "飞向近战距离",
    "FlyToBowRange": "飞向射击距离",
    "FlyingMeleeAttack": "飞行近战",
    "FlyingBowAttack": "飞行射箭",
    "Float": "浮水防溺",
    "FloatAround": "围绕盘旋",
    "RestrictSun": "避光",
    "FleeSun": "躲避阳光",
    "WaterAvoidingRandomStroll": "避水游荡",
    "LookAtPlayer": "注视玩家",
    "NearestAttackableTarget": "锁定最近目标",
    "AllyAlertHurtByTarget": "同伴受击时援护",
    "AllyAlertNearestAttackableTarget": "同伴协同索敌",
    "MobHurtByTarget": "受击反击",
    "SummonedOwnerTarget": "攻击召唤者指定的目标",
    "AvoidCrowd": "避免扎堆",
    "MoveThroughVillage": "穿过村庄",
    "Bite": "撕咬",
    "GrayOozeMeleeAttack": "腐蚀性近战",
    "GhoulHealGoal": "吸取生命恢复",
    "SpectatorChargeAttack": "冲刺",
    "IronSkeletonFleeSun": "躲避阳光",
    "SkeletonFleeSun": "躲避阳光",
}


def zh_goals(goals: list) -> list:
    out = []
    for g in goals:
        key = g.replace("Goal", "")
        zh = GOAL_ZH.get(key) or GOAL_ZH.get(key.replace("Goal", ""))
        if zh and zh not in out:
            out.append(zh)
    return out


def name_of(jar_id: str) -> str:
    key = f"entity.{NS}.{jar_id}"
    if key in LANG:
        return LANG[key]
    return jar_id.replace("_", " ").title()


def build_html(jar_id: str, d: dict) -> str:
    a = d["attrs"]
    name = name_of(jar_id)
    hp = a.get("max_health", 0)
    dmg = a.get("attack_damage", 0)
    spd = a.get("movement_speed", 0)
    follow = a.get("follow_range", 0)
    armor = a.get("armor", 0)
    tough = a.get("armor_toughness", 0)

    kind = "敌对生物" if jar_id in HOSTILE else "中立生物"
    parts = [f"<p>{name} 是 Dungeons 2 中由 gmm（gottsch's Monster Manual）提供模型的{kind}，"
             f"在地牢里随生物套装生成。</p>"]

    # 属性
    line = f"<p><strong>属性</strong>：生命值 {hp:.0f} 点（{hp/2:g} 颗心），攻击伤害 {dmg:g} 点"
    if armor or tough:
        line += f"，护甲 {armor:g} 点"
        if tough:
            line += f"（韧性 {tough:g}）"
    line += f"，移动速度 {spd:g}，索敌范围 {follow:.0f} 格。</p>"
    parts.append(line)

    # 行为
    goals = zh_goals(d.get("goals", []))
    if goals:
        parts.append(f"<p><strong>行为</strong>：{'、'.join(goals[:6])}。</p>")
    elif jar_id in NEUTRAL:
        parts.append("<p><strong>行为</strong>：不会主动攻击，只作为地牢里的环境装饰出现。</p>")

    # 特殊说明
    special = {
        "stone_colossus": "模组的最高血量单位，会砸地并投掷巨石。地牢里有专门放对抗它的装备。",
        "beholder": "会发射可穿透普通盾牌的射线，要用 Mirror Shield 才能挡下。",
        "death_tyrant": "眼魔的强化版，射线伤害更高，致死提示为「被解离」。",
        "spectator": "小型眼魔，会冲刺攻击并施放法术。",
        "vanilla_chest_mimic": "伪装成箱子的拟态怪，靠近后现身攻击。",
        "barrel_mimic": "伪装成木桶的拟态怪，靠近后现身攻击。",
        "minotaur": "会冲锋的牛头人，掉落 Minotaur Axe。",
        "orc_warlord": "兽人首领，会召唤援军，掉落 Orc Warlord Cleaver。",
        "daemon": "血量第二高的单位，会发射法术。",
        "leech": "不造成直接伤害，靠持续吸附消耗生命。",
        "giant_leech": "水蛭的巨型版本，尺寸更大，血量更高。",
        "giant_rat": "老鼠的巨型版本，与普通老鼠同宽，高度翻倍。",
        "shrieker": "不会移动也不会攻击，玩家靠近时发出尖啸，用于警示。",
        "violet_fungus": "不会移动，靠近时会释放孢子攻击。",
    }
    if jar_id in special:
        parts.append(f"<p>{special[jar_id]}</p>")

    parts.append(f"<p><strong>注册名</strong>：{NS}:{jar_id}。"
                 f"具体出现在哪些地牢、多少权重，由 mob_sets 下的生物套装决定。</p>")
    return "".join(parts)


def main() -> int:
    mob_ids = sorted(jar_id for jar_id in ATTRS if f"entity.{NS}.{jar_id}" in LANG)
    print(f"有 lang 条目的生物：{len(mob_ids)} / {len(ATTRS)}")
    missing = [k for k in ATTRS if f"entity.{NS}.{k}" not in LANG]
    if missing:
        print(f"  无 lang 条目（跳过）：{missing}")

    rows = []
    for jar_id in mob_ids:
        d = ATTRS[jar_id]
        rows.append({
            "id": jar_id,
            "name": name_of(jar_id),
            "ename": "",
            "regname": f"{NS}:{jar_id}",
            "category": "敌对生物" if jar_id in HOSTILE else "中立生物",
            "type": "生物/实体",
            "maxstack": 64,
            "remark": ("Dungeons 2 新增生物资料页：名称取自 lang/en_us.json。"
                       "生命值、攻击伤害、移动速度与护甲取自 gmm 里该生物的 createAttributes()，"
                       "行为取自 registerGoals 注册的 AI 目标。辛苦喵呜机了"),
            "html": build_html(jar_id, d),
            "icon32": "",
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n生成 {len(rows)} 条 → {OUT}  ({OUT.stat().st_size/1024:.1f} KB)")
    from collections import Counter
    print("分类:", dict(Counter(r["category"] for r in rows)))
    print("\n=== 抽样 ===")
    for jid in ["rat", "stone_colossus", "beholder", "shrieker"]:
        r = next((x for x in rows if x["id"] == jid), None)
        if r:
            print(f"\n{r['name']}：")
            print(f"  {r['html'][:200]}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
