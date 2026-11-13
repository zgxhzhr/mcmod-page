#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Crafting Dead: Survival（classId 4397）游戏设定页 —— 战利品表。

关键前提：模组里的「战利品」是**方块名**（民用战利品、军用战利品…），
不是掉落物。每种战利品方块绑定一张表，开箱时从表里抽内容。
配套还有五种「生成器」方块，负责在世界里刷出战利品方块。
"""
import json
import random
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
LOOT = BASE / "cds/data/craftingdeadsurvival/loot_tables"
LANG = BASE / "cds/assets/craftingdeadsurvival/lang"
OUT = BASE / "cds-游戏设定-4397.json"

_PAW = ["呜喵", "喵呜", "喵喵"]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def read(rel):
    return json.loads((LOOT / rel).read_text(encoding="utf-8"))


def stat(rel):
    d = read(rel)
    pools = d.get("pools", [])
    ents = sum(len(p.get("entries", [])) for p in pools)
    rolls = [p.get("rolls") for p in pools]
    return ents, rolls


def rolls_text(rolls):
    out = []
    for r in rolls:
        if isinstance(r, dict):
            out.append(f"{r['min']}~{r['max']}")
        elif isinstance(r, float) and r.is_integer():
            out.append(str(int(r)))
        else:
            out.append(str(r))
    return "、".join(out)


def weight_range(rel):
    d = read(rel)
    ents = d["pools"][0]["entries"]
    ws = [e.get("weight") or 1 for e in ents]
    return min(ws), max(ws)


# (表文件名, 方块中文名, 分布说明)
BOXES = [
    ("civilian_loot", "民用战利品", "最基础的一档，几乎所有建筑里都会出现"),
    ("civilian_rare_loot", "稀有民用战利品", "民用版的稀有变体，好货比例明显更高"),
    ("medic_loot", "医疗战利品", "集中在医院与诊所，以药品和医疗器材为主"),
    ("police_loot", "警用战利品", "警察局专用，含防暴装备与手枪弹药"),
    ("military_loot", "军用战利品", "军事基地与检查站，含步枪、瞄具与军用护甲"),
]

BACKPACKS = [
    ("alfa_zombie_backpack_loot", "阿尔法僵尸背包"),
    ("desert_raider_zombie_backpack_loot", "沙漠突袭者僵尸背包"),
    ("miner_zombie_backpack_loot", "矿工僵尸背包"),
    ("scout_zombie_backpack_loot", "侦察兵僵尸背包"),
    ("soldier_zombie_backpack_loot", "士兵僵尸背包"),
    ("swat_zombie_backpack_loot", "特警僵尸背包"),
    ("winter_soldier_zombie_backpack_loot", "冬兵僵尸背包"),
]

VESTS = [
    ("alfa_zombie_vest_loot", "阿尔法僵尸防弹衣"),
    ("desert_raider_zombie_vest_loot", "沙漠突袭者僵尸防弹衣"),
    ("juggernaut_zombie_vest_loot", "重装僵尸防弹衣"),
    ("pilot_zombie_vest_loot", "飞行员僵尸防弹衣"),
    ("sniper_zombie_vest_loot", "狙击手僵尸防弹衣"),
    ("soldier_zombie_vest_loot", "士兵僵尸防弹衣"),
    ("swat_zombie_vest_loot", "特警僵尸防弹衣"),
    ("winter_soldier_zombie_vest_loot", "冬兵僵尸防弹衣"),
]

ENTITIES = [
    ("weak_zombie", "弱僵尸"),
    ("fast_zombie", "快速僵尸"),
    ("police_zombie", "警察僵尸"),
    ("doctor_zombie", "医生僵尸"),
    ("tank_zombie", "坦克僵尸"),
    ("giant_zombie", "巨型僵尸"),
]

VANILLA_ZH = {
    "rotten_flesh": "腐肉",
    "iron_ingot": "铁锭",
    "carrot": "胡萝卜",
    "potato": "土豆",
}


def main() -> int:
    zh = json.loads((LANG / "zh_cn.json").read_text(encoding="utf-8"))
    en = json.loads((LANG / "en_us.json").read_text(encoding="utf-8"))

    # 五种战利品方块的表
    box_rows = ""
    for f, label, desc in BOXES:
        ents, rolls = stat(f"blocks/{f}.json")
        lo, hi = weight_range(f"blocks/{f}.json")
        box_rows += (
            f"<tr><td>{label}</td><td>{ents}</td><td>{lo}~{hi}</td>"
            f"<td>{rolls_text(rolls)}</td><td>{desc}</td></tr>"
        )

    # 生成器
    gen_rows = ""
    for f, label, _ in BOXES:
        gen = zh.get(f"block.craftingdeadsurvival.{f}_gen", f"{label}生成器")
        ents, _ = stat(f"blocks/{f}_gen.json")
        gen_rows += f"<tr><td>{gen}</td><td>{label}</td><td>{ents}</td></tr>"

    # 僵尸背包
    pack_rows = ""
    for f, label in BACKPACKS:
        ents, rolls = stat(f"backpacks/{f}.json")
        pack_rows += f"<tr><td>{label}</td><td>{ents}</td><td>{rolls_text(rolls)}</td></tr>"

    # 防弹衣
    vest_rows = ""
    for f, label in VESTS:
        ents, rolls = stat(f"vests/{f}.json")
        vest_rows += f"<tr><td>{label}</td><td>{ents}</td><td>{rolls_text(rolls)}</td></tr>"

    # 僵尸掉落
    ent_rows = ""
    for f, label in ENTITIES:
        d = read(f"entities/{f}.json")
        fixed, choice = [], []
        for pl in d.get("pools", []):
            names = [(e.get("name") or "").split(":")[-1] for e in pl.get("entries", [])]
            if len(names) == 1:
                fixed += names
            else:
                choice += names
        ent_rows += (
            f"<tr><td>{label}</td>"
            f"<td>{'、'.join(VANILLA_ZH.get(x, x) for x in fixed) or '—'}</td>"
            f"<td>{'、'.join(VANILLA_ZH.get(x, x) for x in choice) or '—'}</td></tr>"
        )

    med_ents, med_rolls = stat("supply_drops/medical.json")
    mil_ents, mil_rolls = stat("supply_drops/military.json")

    html = (
        "<p>本模组里的「战利品」指<strong>方块</strong>——民用战利品、军用战利品这些名字"
        "对应的都是一种箱子，玩家在世界里找到并打开它们。</p>"

        "<p>箱子里出现什么，由<strong>战利品表</strong>决定：每种战利品方块各绑定一张表，"
        "开箱时从该表里抽取。要查某种箱子的产出，看它对应的表即可。</p>"

        "<p><strong>权重机制</strong>：表中每个条目带一个权重值，被抽中的概率等于"
        "「该条目权重 ÷ 该表所有权重之和」。权重高即常见，与物品本身的稀有度无关——"
        "同为弹药，常见口径的弹匣权重能到 30，冷门口径只有 2。</p>"

        "<p><strong>抽取次数</strong>：五种战利品方块每次只抽一件（rolls = 1）；"
        "背包与防弹衣抽 1 到 3 件；补给空投固定抽 10 件。"
        "空投一次能给一整批物资，而箱子要开很多个才能凑齐。</p>"

        "<h2>战利品方块与对应的表</h2>"
        "<p>五种战利品方块按场所区分档次，各自绑定一张表：</p>"
        "<table><thead><tr><th>方块</th><th>表内条目</th><th>权重范围</th>"
        "<th>抽取次数</th><th>分布</th></tr></thead>"
        f"<tbody>{box_rows}</tbody></table>"

        "<p><strong>权重跨度</strong>：民用 2~30，稀有民用 5~75，医疗 4~40，"
        "警用 5~30，军用 1~25。稀有民用箱的跨度最大——上限 75 比军用箱还高，"
        "所以「稀有民用」这个命名在掉落上确实名副其实。</p>"

        "<h2>战利品生成器</h2>"
        "<p>与战利品方块配套的还有五种<strong>生成器</strong>方块。"
        "它们不装物品，作用是让战利品方块出现在世界里——"
        "生成器本身也有一张表，表里只有一项内容，就是它对应的战利品方块。</p>"
        "<table><thead><tr><th>生成器</th><th>产出</th><th>表内条目</th></tr></thead>"
        f"<tbody>{gen_rows}</tbody></table>"
        "<p>所以链条是：生成器决定战利品方块出现在哪 → 战利品方块被打开 → "
        "从战利品表里抽出内容物。三者各管一段，互不重叠。</p>"

        "<h2>补给空投</h2>"
        "<p>空投有两种，都是固定抽取 10 件、条目之间等概率，不设权重：</p>"
        "<table><thead><tr><th>空投</th><th>条目数</th><th>抽取次数</th><th>内容偏向</th></tr></thead><tbody>"
        f"<tr><td>医疗补给</td><td>{med_ents}</td><td>{rolls_text(med_rolls)}</td>"
        "<td>绷带、急救包、肾上腺素、吗啡、军用医疗服装</td></tr>"
        f"<tr><td>军用补给</td><td>{mil_ents}</td><td>{rolls_text(mil_rolls)}</td>"
        "<td>枪械、弹药、护甲与军用物资</td></tr>"
        "</tbody></table>"
        "<p>等概率意味着空投里每种物品出的机会相同，抽 10 次很容易出现重复。"
        "空投的定位是「一次给足」：量大、可重复，单件品质低于战利品方块。</p>"

        "<h2>僵尸背包</h2>"
        "<p>七种特殊僵尸身上带背包，击杀后掉落背包并从中抽取 1 到 3 件物品。</p>"
        "<table><thead><tr><th>僵尸</th><th>条目数</th><th>抽取次数</th></tr></thead>"
        f"<tbody>{pack_rows}</tbody></table>"
        "<p>背包内容以食物、饮水与基础医疗品为主，越偏军事的僵尸条目越多。"
        "矿工僵尸的背包只有 3 个条目，是最简单的一档。</p>"

        "<h2>僵尸防弹衣</h2>"
        "<p>八种僵尸穿着防弹衣，击杀后可从中抽取 1 到 3 件物品。</p>"
        "<table><thead><tr><th>僵尸</th><th>条目数</th><th>抽取次数</th></tr></thead>"
        f"<tbody>{vest_rows}</tbody></table>"
        "<p>防弹衣的掉落偏向弹药与战术装备——弹匣、手雷、电击枪与电击弹都在这一类里，"
        "是获取弹药的重要来源之一。</p>"

        "<h2>僵尸掉落</h2>"
        "<p>普通僵尸的掉落分两部分：一部分固定，一部分在几个条目里等概率选一个。</p>"
        "<table><thead><tr><th>僵尸</th><th>固定掉落</th><th>随机掉落</th></tr></thead>"
        f"<tbody>{ent_rows}</tbody></table>"
        "<p>六种僵尸的掉落表结构完全一致，差异只在僵尸本身的属性。"
        "固定掉落是腐肉，随机掉落从铁锭、胡萝卜、土豆里取一个。</p>"
    )

    # <h2> → <p>[h2=]</p>（百科用方括号标记，不认 HTML 标题）
    import re
    # 资料页没有原文的 [h1=] 作父级，标题必须从 h1 起；用 h2 会被判「跨级标题」
    html = re.sub(r"<h2>([^<]+)</h2>", r"<p>[h1=\1]</p>", html)

    rows = [{
        "id": "loot_tables",
        "name": "战利品表",
        "ename": "",
        "regname": "",
        "category": "战利品",
        "type": "游戏设定",
        "maxstack": 64,
        "remark": (
            "Crafting Dead: Survival 游戏设定页：条目数、权重与抽取次数取自 "
            "data/craftingdeadsurvival/loot_tables 下 33 个战利品表，"
            "方块名称取自 lang/zh_cn.json 的 loot 条目。"
            f"{tail()}"
        ),
        "html": html,
        "icon32": "",
        "icon128": "",
    }]

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)")
    print(f"  正文 {len(html)} 字符，表格 {html.count('<table')} 张")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
