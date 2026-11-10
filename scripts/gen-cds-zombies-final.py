#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Crafting Dead: Survival 丧尸相关最终产物。

1. 新增 14 种精英丧尸（官方中文名，来自 zh_cn.json）
2. 批量编辑现有 7 个生物页：修正血量数值、补充正文（名称批量脚本改不了，保留原样）

数值来源：ServerConfig.java 的 defineInRange 默认值
  advanced 20 血 / 3 伤害，tank 100 / 15，fast 10 / 1，weak 5 / 2，
  giant 100 / 50，其余精英一律 20 / 3（hazmat、scout 有独立伤害配置，同为 3）
自然生成权重：advanced 40、fast 15、weak 30、tank 5；其余靠刷怪蛋或战利品
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
NS = "craftingdeadsurvival"
ZH = json.loads((BASE / "cds-official-zh.json").read_text(encoding="utf-8"))
ZH_ENT = {
    "scout_zombie": "侦察兵僵尸", "sniper_zombie": "狙击手僵尸", "pilot_zombie": "飞行员僵尸",
    "soldier_zombie": "士兵僵尸", "winter_soldier_zombie": "冬兵僵尸", "ninja_zombie": "忍者僵尸",
    "alfa_zombie": "阿尔法僵尸", "bounty_hunter_zombie": "赏金猎人僵尸",
    "desert_raider_zombie": "沙漠突袭者僵尸", "firefighter_zombie": "消防员僵尸",
    "hazmat_zombie": "防化服僵尸", "juggernaut_zombie": "主宰者僵尸",
    "miner_zombie": "矿工僵尸", "swat_zombie": "特警僵尸",
    "fast_zombie": "迅捷僵尸", "tank_zombie": "坦克僵尸", "weak_zombie": "虚弱僵尸",
    "police_zombie": "警用僵尸", "doctor_zombie": "医生僵尸", "giant_zombie": "巨型僵尸",
}

# 14 种精英：(注册名, 血量, 伤害, 会开枪, 专属背包, 特征描述)
ELITE = [
    ("scout_zombie", 20, 3, False, True, "行动敏捷，通常最先发现玩家"),
    ("sniper_zombie", 20, 3, True, True, "使用枪械远程射击，倾向于保持距离"),
    ("pilot_zombie", 20, 3, True, False, "穿着飞行服出场，会使用枪械"),
    ("soldier_zombie", 20, 3, True, True, "标准武装单位，装备制式枪械"),
    ("winter_soldier_zombie", 20, 3, True, True, "冬季装备的精锐单位，火力较强"),
    ("ninja_zombie", 20, 3, False, False, "贴身近战，移动迅速"),
    ("alfa_zombie", 20, 3, True, True, "特种部队单位，属于最高一级的精英"),
    ("bounty_hunter_zombie", 20, 3, True, False, "装备赏金猎人套装，会使用枪械"),
    ("desert_raider_zombie", 20, 3, True, True, "沙漠风格的突袭单位，使用枪械"),
    ("firefighter_zombie", 20, 3, False, False, "穿着消防服出场，主要进行近战"),
    ("hazmat_zombie", 20, 3, False, False, "穿着防化服出场，近战攻击"),
    ("juggernaut_zombie", 20, 3, True, True, "重甲单位，抗击退能力较强，会使用枪械"),
    ("miner_zombie", 20, 3, False, True, "矿工装备，背包里带有矿物与工具"),
    ("swat_zombie", 20, 3, True, True, "特警单位，装备完整，火力与防护都较高"),
]

# 现有 7 个生物页（批量脚本不支持改 name，只改正文）
EXISTING = [
    ("479769", "高级僵尸", 20, 3, False, False, None,
     "普通僵尸的强化版，自然生成权重最高"),
    ("479770", "迅捷僵尸", 10, 1, False, False, 40,
     "移动速度与玩家疾跑相当，但血量只有 10 点"),
    ("479771", "坦克僵尸", 100, 15, False, False, 5,
     "血量与伤害都远高于普通僵尸，在尸群中少量出现"),
    ("479772", "虚弱僵尸", 5, 2, False, False, 30,
     "移速慢、血量低，对持有任意工具的玩家不构成威胁"),
    ("479773", "警用僵尸", 20, 3, True, True, None,
     "统一穿警服、持手枪出场，追踪玩家时一边追逐一边射击"),
    ("479774", "医生僵尸", 20, 3, False, False, None,
     "统一穿医生服装，手持模组药品"),
    ("479775", "巨型僵尸", 100, 50, False, False, None,
     "体型与伤害都是模组里最高的一档"),
]


def missing_texture(size: int = 32) -> str:
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 255))
    for y in range(16):
        for x in range(16):
            if ((x // 8) + (y // 8)) % 2 == 0:
                img.putpixel((x, y), (248, 0, 248, 255))
    img = img.resize((size, size), Image.NEAREST)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def body(zh: str, hp: float, dmg: float, ranged: bool, backpack: bool,
         weight, trait: str) -> str:
    def n(x):
        return int(x) if float(x) == int(x) else x
    parts = [f"<p>{zh}是行尸走肉：生存添加的丧尸，{trait}。</p>",
             f"<p><strong>属性</strong>：血量 {n(hp)} 点（{n(hp/2)} 颗心），攻击伤害 {n(dmg)} 点（{n(dmg/2)} 颗心）。</p>"]
    if ranged:
        parts.append("<p><strong>攻击方式</strong>：除了近身攻击，还会使用枪械远程射击，"
                     "枪械与弹药取决于它携带的武装配置。遇到时不要站在开阔地。</p>")
    else:
        parts.append("<p><strong>攻击方式</strong>：以近身攻击为主，不会开枪。</p>")
    if weight:
        parts.append(f"<p><strong>生成</strong>：会自然生成，在尸群中的生成权重为 {weight}。</p>")
    else:
        parts.append("<p><strong>生成</strong>：不参与自然生成，只能通过刷怪蛋或战利品机制出现。</p>")
    if backpack:
        parts.append("<p><strong>掉落</strong>：穿着职业对应的装备出场，击杀后按概率掉落装备与背包，"
                     f"背包内容取自该职业专属的战利品表（{zh}背包）。</p>")
    else:
        parts.append("<p><strong>掉落</strong>：穿着职业对应的装备出场，击杀后按概率掉落身上的装备。</p>")
    parts.append("<p><strong>配置</strong>：血量、伤害、装备掉落概率、生成开关与权重都可以在服务器的配置文件里单独调整，"
                 "不同整合包里同一只丧尸的强度可能差别很大。</p>")
    return "".join(parts)


def main() -> int:
    miss = missing_texture(32)

    # ── 1. 新增 14 条 ──
    rows = []
    for rid, hp, dmg, ranged, bp, trait in ELITE:
        zh = ZH_ENT[rid]
        rows.append({
            "id": rid, "name": zh, "ename": rid,
            "regname": f"{NS}:{rid}", "category": "敌对生物", "type": "生物/实体",
            "remark": ("Crafting Dead: Survival 新增生物资料页：中文名取自 lang/zh_cn.json，"
                       "血量与伤害取自 ServerConfig 的默认值，行为与掉落依据各 ZombieHandler 与 "
                       "loot_tables 下的定义。实体没有静态贴图，已勾选删除大小图标。辛苦喵呜机了"),
            "html": body(zh, hp, dmg, ranged, bp, None, trait),
            "icon32": "",
        })
    (BASE / "cds-新增丧尸-4397.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"新增丧尸：{len(rows)} 条")

    # ── 2. 编辑现有 7 个生物页 ──
    edits = []
    for mid, zh, hp, dmg, ranged, bp, weight, trait in EXISTING:
        edits.append({
            "id": mid,
            "name": zh,
            "editRemark": ("按模组源码的默认配置校正数值并规范正文：血量与伤害取自 ServerConfig.java "
                           f"的 defineInRange 默认值（{zh}：{hp} 血、{dmg} 伤害），生成权重取自同一文件；"
                           "正文按「属性 / 攻击方式 / 生成 / 掉落 / 配置」统一编排。辛苦喵呜机了"),
            "editNote": f"补全正文：血量 {hp}、伤害 {dmg}、生成方式与掉落说明。",
            "html": body(zh, hp, dmg, ranged, bp, weight, trait),
        })
    (BASE / "cds-编辑丧尸-4397.json").write_text(
        json.dumps(edits, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"编辑丧尸：{len(edits)} 条")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
