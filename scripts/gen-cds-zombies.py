#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Crafting Dead: Survival（classId 4397）14 种精英丧尸的批量新增 JSON。

字段按 skill §6.6：name / ename / regname / category / type / remark / html / icon32
生物没有可用的静态图标，icon32 留空——批量脚本 v2.5 起会自动点「删除大图标」。
"""
import json
import sys
from pathlib import Path

OUT = Path(r"E:\Mod\百科-语料\jar-analyze\cds-新增丧尸-4397.json")
NS = "craftingdeadsurvival"
REMARK = ("Crafting Dead: Survival 新增生物资料页：血量与伤害取自模组 ServerConfig 的默认值，"
          "行为与掉落依据各 ZombieHandler 与 loot_tables 下的定义。生物无静态图标，已按要求删除大小图标。辛苦喵呜机了")

# (注册名, 中文名, 英文名, 血量, 伤害, 远程, 专属背包, 一句话特征)
ZOMBIES = [
    ("scout_zombie", "侦察兵丧尸", "Scout Zombie", 20, 3, False, True,
     "行动敏捷，通常在最前面发现玩家"),
    ("sniper_zombie", "狙击手丧尸", "Sniper Zombie", 20, 3, True, True,
     "使用枪械远程射击，倾向于占据有利距离"),
    ("pilot_zombie", "飞行员丧尸", "Pilot Zombie", 20, 3, True, False,
     "穿着飞行服出场，会使用枪械"),
    ("soldier_zombie", "士兵丧尸", "Soldier Zombie", 20, 3, True, True,
     "标准武装单位，装备制式枪械"),
    ("winter_soldier_zombie", "冬兵丧尸", "Winter Soldier Zombie", 20, 3, True, True,
     "冬季装备的精锐单位，火力较强"),
    ("ninja_zombie", "忍者丧尸", "Ninja Zombie", 20, 3, False, False,
     "贴身近战，移动迅速"),
    ("alfa_zombie", "ALFA 丧尸", "ALFA Zombie", 20, 3, True, True,
     "特种部队单位，属于最高一级的精英丧尸"),
    ("bounty_hunter_zombie", "赏金猎人丧尸", "Bounty Hunter Zombie", 20, 3, True, False,
     "装备赏金猎人套装，会使用枪械"),
    ("desert_raider_zombie", "沙漠掠夺者丧尸", "Desert Raider Zombie", 20, 3, True, True,
     "沙漠风格的掠夺单位，使用枪械"),
    ("firefighter_zombie", "消防员丧尸", "Firefighter Zombie", 20, 3, False, False,
     "穿着消防服出场，主要进行近战"),
    ("hazmat_zombie", "危险品处理员丧尸", "Hazmat Zombie", 20, 3, False, False,
     "穿着防护服出场，近战攻击"),
    ("juggernaut_zombie", "重装兵丧尸", "Juggernaut Zombie", 20, 3, True, True,
     "重甲单位，抗击退能力较强，会使用枪械"),
    ("miner_zombie", "矿工丧尸", "Miner Zombie", 20, 3, False, True,
     "矿工装备，背包里带有矿物与工具"),
    ("swat_zombie", "SWAT 丧尸", "SWAT Zombie", 20, 3, True, True,
     "特警单位，装备完整，火力与防护都较高"),
]


def html_for(zh: str, hp: float, dmg: float, ranged: bool, backpack: bool, trait: str) -> str:
    hearts = hp / 2
    dh = dmg / 2
    parts = [
        f"<p>{zh}是行尸走肉：生存添加的精英丧尸，{trait}。</p>",
        f"<p><strong>属性</strong>：血量 {int(hp) if hp == int(hp) else hp} 点（{int(hearts) if hearts == int(hearts) else hearts} 颗心），"
        f"攻击伤害 {int(dmg) if dmg == int(dmg) else dmg} 点（{int(dh) if dh == int(dh) else dh} 颗心）。</p>",
    ]
    if ranged:
        parts.append("<p><strong>攻击方式</strong>：除了近身攻击，还会使用枪械远程射击，需要在开阔地小心应对。"
                     "枪械与弹药取决于它携带的武装配置。</p>")
    else:
        parts.append("<p><strong>攻击方式</strong>：以近身攻击为主，不会开枪。</p>")
    if backpack:
        parts.append("<p><strong>掉落</strong>：穿着职业对应的装备出场，击杀后按掉落概率掉落装备与背包。"
                     f"背包内容取自该职业专属的战利品表（{zh}背包）。</p>")
    else:
        parts.append("<p><strong>掉落</strong>：穿着职业对应的装备出场，击杀后按掉落概率掉落身上的装备，"
                     "没有专属背包战利品表。</p>")
    parts.append("<p><strong>配置</strong>：血量、伤害、装备掉落概率、生成开关与权重都可以在服务器的配置文件里单独调整，"
                 "因此同一个精英丧尸在不同整合包里强度可能完全不同。</p>")
    return "".join(parts)


def main() -> int:
    lang = json.loads(
        (Path(r"E:\Mod\百科-语料\jar-analyze\cds\assets")
         / NS / "lang" / "en_us.json").read_text(encoding="utf-8"))

    rows = []
    for rid, zh, en, hp, dmg, ranged, backpack, trait in ZOMBIES:
        regname = f"{NS}:{rid}"
        rows.append({
            "id": rid,
            "name": zh,
            "ename": en,
            "regname": regname,
            "category": "敌对生物",
            "type": "生物/实体",
            "remark": REMARK,
            "html": html_for(zh, hp, dmg, ranged, backpack, trait),
            "icon32": "",
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
    for r in rows:
        print(f"  {r['regname']:<36} {r['name']:<16} {r['ename']:<26} 正文 {len(r['html'])} 字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
