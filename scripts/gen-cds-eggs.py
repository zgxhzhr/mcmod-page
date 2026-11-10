#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Crafting Dead: Survival 第 4 批：14 个缺失的刷怪蛋资料页。

刷怪蛋图标由游戏按两色程序化生成，没有静态 png，因此 icon32 留空，
批量脚本会自动勾选「删除大图标」。
"""
import json
from pathlib import Path

OUT = Path(r"E:\Mod\百科-语料\jar-analyze\cds-新增刷怪蛋-4397.json")
NS = "craftingdeadsurvival"
REMARK = ("Crafting Dead: Survival 补齐刷怪蛋资料页：与已有 6 个刷怪蛋页保持一致，正文按刷怪蛋的通用说明撰写。"
          "刷怪蛋图标由游戏程序化生成、无静态贴图，已按要求删除大小图标。辛苦喵呜机了")

# (注册名, 中文名, 英文名)
EGGS = [
    ("scout_zombie_spawn_egg", "生成 侦察兵丧尸", "Scout Zombie Spawn Egg"),
    ("sniper_zombie_spawn_egg", "生成 狙击手丧尸", "Sniper Zombie Spawn Egg"),
    ("pilot_zombie_spawn_egg", "生成 飞行员丧尸", "Pilot Zombie Spawn Egg"),
    ("soldier_zombie_spawn_egg", "生成 士兵丧尸", "Soldier Zombie Spawn Egg"),
    ("winter_soldier_zombie_spawn_egg", "生成 冬兵丧尸", "Winter Soldier Zombie Spawn Egg"),
    ("ninja_zombie_spawn_egg", "生成 忍者丧尸", "Ninja Zombie Spawn Egg"),
    ("alfa_zombie_spawn_egg", "生成 ALFA 丧尸", "ALFA Zombie Spawn Egg"),
    ("bounty_hunter_zombie_spawn_egg", "生成 赏金猎人丧尸", "Bounty Hunter Zombie Spawn Egg"),
    ("desert_raider_zombie_spawn_egg", "生成 沙漠掠夺者丧尸", "Desert Raider Zombie Spawn Egg"),
    ("firefighter_zombie_spawn_egg", "生成 消防员丧尸", "Firefighter Zombie Spawn Egg"),
    ("hazmat_zombie_spawn_egg", "生成 危险品处理员丧尸", "Hazmat Zombie Spawn Egg"),
    ("juggernaut_zombie_spawn_egg", "生成 重装兵丧尸", "Juggernaut Zombie Spawn Egg"),
    ("miner_zombie_spawn_egg", "生成 矿工丧尸", "Miner Zombie Spawn Egg"),
    ("swat_zombie_spawn_egg", "生成 SWAT 丧尸", "SWAT Zombie Spawn Egg"),
]


def html_for(mob_zh: str) -> str:
    return (f"<p>刷怪蛋是用于生成{mob_zh}的创造模式物品。</p>"
            f"<p><strong>获取</strong>：只能在创造模式的物品栏里取得，生存模式没有获取途径。</p>"
            f"<p><strong>用法</strong>：右击方块会立即生成一只{mob_zh}，也可以用发射器发射。"
            f"在和平模式下，由刷怪蛋生成的敌对生物会立刻消失。</p>"
            f"<p><strong>切换生物</strong>：创造模式下对着目标生物按鼠标中键，可以直接拿到它对应的刷怪蛋。</p>")


def main() -> int:
    rows = []
    for rid, zh, en in EGGS:
        mob = zh.replace("生成 ", "")
        rows.append({
            "id": rid,
            "name": zh,
            "ename": en,
            "regname": f"{NS}:{rid}",
            "category": "仅创造",
            "type": "物品/方块",
            "maxstack": 1,
            "remark": REMARK,
            "html": html_for(mob),
            "icon32": "",
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
    for r in rows:
        print(f"  {r['regname']:<46} {r['name']:<20} 正文 {len(r['html'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
