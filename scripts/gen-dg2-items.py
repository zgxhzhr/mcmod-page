#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dungeons 2（classId 2475）物品页批量新增 JSON。

14 个物品，其中 9 个有独立纹理可直接出图标，其余 5 个法术物品与 Rock 无独立贴图。

属性来源：DungeonsItems.java 的构造参数 + DungeonsArmorMaterials 的护甲定义。
模组只有 en_us.json，按规则名称用英文，ename 留空。
"""
import base64
import io
import json
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
JAR = BASE / "dg2"
TEX = JAR / "assets/dungeons2/textures/item"
OUT = BASE / "dg2-物品导入-2475.json"
NS = "dungeons2"

LOOT = "在地牢的箱子、木桶、石棺、书架与祭坛中随机开出"
NO_RECIPE = "模组没有提供合成配方"

# name, 分类, 堆叠, 图标名（None=无图标）, 正文
ITEMS = [
    {
        "id": "club", "name": "Club", "category": "武器", "maxstack": 1, "icon": "club",
        "html": "<p>Club 是 Dungeons 2 添加的木制钝器，按剑类物品处理。</p>"
                "<p><strong>属性</strong>：攻击伤害 7 点（3.5 颗心），攻击速度 -3.0。"
                "以木剑为底材，因为基础伤害加成较高，实际输出接近石剑。</p>"
                f"<p><strong>获取</strong>：{NO_RECIPE}，{LOOT}。</p>",
    },
    {
        "id": "spiked_club", "name": "Spiked Club", "category": "武器", "maxstack": 1, "icon": "spiked_club",
        "html": "<p>Spiked Club 是 Dungeons 2 添加的木制钉头棍，按剑类物品处理。</p>"
                "<p><strong>属性</strong>：攻击伤害 8 点（4 颗心），攻击速度 -3.0。"
                "比普通 Club 多 1 点伤害，代价相同。</p>"
                f"<p><strong>获取</strong>：{NO_RECIPE}，{LOOT}。</p>",
    },
    {
        "id": "orc_warlord_cleaver", "name": "Orc Warlord Cleaver", "category": "武器", "maxstack": 1,
        "icon": "orc_warlord_cleaver",
        "html": "<p>Orc Warlord Cleaver 是 Dungeons 2 添加的铁制砍刀，兽人督军的武器，按剑类物品处理。</p>"
                "<p><strong>属性</strong>：攻击伤害 9 点（4.5 颗心），攻击速度 -2.6。"
                "伤害与铁剑相当，但挥动更快，是模组内 DPS 最高的单手近战武器之一。</p>"
                f"<p><strong>获取</strong>：{NO_RECIPE}，{LOOT}。也可以从兽人督军身上拿到。</p>",
    },
    {
        "id": "minotaur_axe", "name": "Minotaur Axe", "category": "武器", "maxstack": 1, "icon": "minotaur_axe",
        "html": "<p>Minotaur Axe 是 Dungeons 2 添加的铁制巨斧，牛头人的武器，按斧类物品处理。</p>"
                "<p><strong>属性</strong>：攻击伤害 12 点（6 颗心），攻击速度 -3.4。"
                "单发伤害是全模组最高的近战武器，代价是挥动很慢，适合配合减震靴打重击。</p>"
                f"<p><strong>获取</strong>：{NO_RECIPE}，{LOOT}。也可以从牛头人身上拿到。</p>",
    },
    {
        "id": "boots_of_shock_absorption", "name": "Boots of Shock Absorption", "category": "防具",
        "maxstack": 1, "icon": "boots_of_shock_absorption",
        "html": "<p>Boots of Shock Absorption 是 Dungeons 2 添加的靴子，专门用来应对地牢里的砸地攻击与地面塌陷。</p>"
                "<p><strong>属性</strong>：护甲值 3 点（1.5 格），护甲韧性 1.0，击退抗性 0.1，附魔能力 12。"
                "耐久倍率 26，比铁靴略高。</p>"
                "<p><strong>效果</strong>：削弱砸地造成的伤害，以及地面塌陷时摔落造成的伤害。"
                "石像巨人这类会砸地的敌人，穿上它之后威胁会明显下降。</p>"
                f"<p><strong>获取</strong>：{NO_RECIPE}，{LOOT}。"
                "地牢里有一处专门放对抗石像巨人的装备，通常能开出这件。</p>",
    },
    {
        "id": "mirror_shield", "name": "Mirror Shield", "category": "防具", "maxstack": 1,
        "icon": "mirror_shield",
        "html": "<p>Mirror Shield 是 Dungeons 2 添加的盾牌，针对眼魔的射线类攻击。</p>"
                "<p><strong>属性</strong>：耐久 336，可以像原版盾一样举起格挡。</p>"
                "<p><strong>效果</strong>：把眼魔的射线与凝视类法术反弹回去。"
                "这些攻击会穿透普通盾牌，举起原版盾时命中会提示「法术穿过你的盾」，而镜盾能挡住并返还。</p>"
                "<p><strong>注意</strong>：镜盾只能挡住正面的射线，放下盾时依然会被夺走。"
                "对付眼魔要一直举着，别在中途放下。</p>"
                f"<p><strong>获取</strong>：{NO_RECIPE}，{LOOT}。地牢里有专门放对抗眼魔装备的箱子。</p>",
    },
    {
        "id": "delvers_companion", "name": "The Delver's Companion", "category": "工具",
        "maxstack": 1, "icon": "delvers_companion",
        "html": "<p>The Delver's Companion 是 Dungeons 2 附带的地牢指南书，由 gottschbooks 提供阅读界面。</p>"
                "<p><strong>用法</strong>：手持右击打开，书页里讲的是这套地牢怎么运转——结构、怪物、装备的来历。"
                "内容是模组自带的设定文本，不是玩家写上去的。</p>"
                "<p><strong>属性</strong>：堆叠上限 1，不能附魔，也不会被消耗。</p>"
                f"<p><strong>获取</strong>：{NO_RECIPE}，{LOOT}。属于稀有读物。</p>"
                "<p><strong>同系列</strong>：另有 A Delver's Last Pages，是前一位探索者留下的日记，"
                "找齐它能解锁对应成就。</p>",
    },
    {
        "id": "blank_dungeon_map", "name": "Blank Dungeon Map", "category": "工具", "maxstack": 1,
        "icon": "blank_dungeon_map",
        "html": "<p>Blank Dungeon Map 是 Dungeons 2 添加的空白地图，用来记录地牢的单层布局。</p>"
                "<p><strong>用法</strong>：站在地牢楼层的范围里右击，开始绘制这一层。"
                "绘制只在楼层范围内生效，在地面上用会提示必须先进入地牢。</p>"
                "<p><strong>结果</strong>：绘制完成后变成 Dungeon Map，按层记录已经走过的区域。"
                "每层需要各自的地图，换层之后要重新开一张。</p>"
                "<p><strong>获取</strong>：这是模组内少数有合成配方的物品之一，"
                f"在工作台按固定形状合成。也可以{LOOT}。</p>",
    },
    {
        "id": "dungeon_compass", "name": "Dungeon Compass", "category": "工具", "maxstack": 1,
        "icon": "dungeon_compass_16",
        "html": "<p>Dungeon Compass 是 Dungeons 2 添加的指南针，指向附近的地牢入口。</p>"
                "<p><strong>用法</strong>：拿在手上会显示最近一座地牢的方向与距离。"
                "不在同一座地牢里时提示「你不在这个地牢里」，层数不同时提示「你不在这一层」。</p>"
                "<p><strong>外观</strong>：指针有 32 帧动画，随朝向连续变化。</p>"
                "<p><strong>限制</strong>：只能堆叠 1 个，不能附魔。</p>"
                f"<p><strong>获取</strong>：{NO_RECIPE}，{LOOT}。</p>",
    }
]


def missing_texture(size: int = 32) -> str:
    """原版缺省材质：品红 + 黑棋盘格（8px 一格，NEAREST 放大）"""
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 255))
    for y in range(16):
        for x in range(16):
            if ((x // 8) + (y // 8)) % 2 == 0:
                img.putpixel((x, y), (248, 0, 248, 255))
    img = img.resize((size, size), Image.NEAREST)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def b64(name: str):
    p = TEX / f"{name}.png"
    if not p.exists():
        return ""
    img = Image.open(p).convert("RGBA")
    if img.size != (32, 32):
        method = Image.NEAREST if img.width < 32 else Image.LANCZOS
        img = img.resize((32, 32), method)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def main() -> int:
    rows = []
    for it in ITEMS:
        icon = b64(it["icon"]) if it["icon"] else missing_texture(32)
        rows.append({
            "id": it["id"],
            "name": it["name"],
            "ename": "",
            "regname": f"{NS}:{it['id']}",
            "category": it["category"],
            "type": "物品/方块",
            "maxstack": it["maxstack"],
            "remark": ("Dungeons 2 新增资料页：名称取自 lang/en_us.json（模组没有 zh_cn，按规则只写英文）。"
                       "属性取自 DungeonsItems 的构造参数与 DungeonsArmorMaterials 的护甲定义，"
                       "掉落来源依据 loot_tables 下的箱子配置。"
                       + "辛苦喵呜机了"),
            "html": it["html"],
            "icon32": icon,
        })
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT}  ({OUT.stat().st_size/1024:.1f} KB)")
    from collections import Counter
    print("分类:", dict(Counter(r["category"] for r in rows)))
    noicon = [r["id"] for r in rows if not r["icon32"]]
    print(f"无图标 {len(noicon)} 个: {noicon}")
    for r in rows[:4]:
        print(f"  {r['name']:<28} [{r['category']}] 图标 {len(r['icon32'])} 字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
