#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Malstone Mod（26143）配方补充 + 通用文本精简。

从 data/malum/recipes 读出 19 件饰品的实际合成方式：
  17 件走灵灾的「灵魂灌注」（spirit_infusion）
   2 件走灵灾的「符文制作」（runeworking）

材料名说明：灵灾（malum）那 18 种材料本机没有它的 jar，取不到官方中文名，
保留英文 id 以免写错；原版材料（金剑、铁斧、铁锭）译成中文。
"""
import json
import random
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
RECIPES = BASE / "mal/data/malum/recipes"
SRC = BASE / "mal-物品导入-26143.json"
OUT_ITEMS = BASE / "mal-物品导入-26143.json"
OUT_COMMON = BASE / "mal-通用文本-26143.json"

_PAW = ["呜喵", "喵呜", "喵喵"]

# 原版材料中文名（其余保留 id）
VANILLA_ZH = {
    "minecraft:golden_sword": "金剑",
    "minecraft:iron_axe": "铁斧",
    "#forge:ingots/iron": "铁锭",
    "#malum:scythe": "镰刀类武器（任选）",
}

# 精魂类型中文说明
SPIRIT_ZH = {
    "infernal": "infernal（狱火）",
    "earthen": "earthen（大地）",
    "eldritch": "eldritch（邪异）",
    "arcane": "arcane（奥术）",
    "wicked": "wicked（邪恶）",
}

# 通用文本（去掉「品质」「归属」两段，获取改为说明合成方式）
COMMON_HTML = (
    "<p>这些物品是 Malstone Mod 添加的饰品。</p>"
    "<p><strong>佩戴</strong>：放在 Curios 的饰品栏里生效，戴在身上即可，"
    "不需要拿在手上。模组新增的哭泣槽位也在饰品栏内。</p>"
    "<p><strong>合成</strong>：全部在灵灾的两个工作站里制作，不是普通工作台。"
    "多数饰品走<strong>灵魂灌注</strong>（Spirit Infusion），"
    "少部分走<strong>符文制作</strong>（Runeworking）。"
    "灵魂灌注需要以一件物品为核心，另加若干辅助材料，再消耗指定数量与种类的精魂；"
    "符文制作只需主材与副材两样。</p>"
    "<p><strong>材料命名</strong>：配方里不带前缀的材料名指灵灾的物品，"
    "与灵灾各物品页的注册名一致；原版材料（金剑、铁斧、铁锭）已译成中文。</p>"
)


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def mat_name(x) -> str:
    """材料名：原版译中文，灵灾材料去掉 malum: 前缀（通用文本里已说明）。"""
    if isinstance(x, dict):
        if "item" in x:
            it = x["item"]
            if it in VANILLA_ZH:
                return VANILLA_ZH[it]
            return it.replace("malum:", "").replace("malstone:", "")
        if "tag" in x:
            tg = "#" + x["tag"]
            if tg in VANILLA_ZH:
                return VANILLA_ZH[tg]
            return tg.replace("malum:", "").replace("malstone:", "")
    return str(x)


def recipe_html(rid: str):
    """返回该物品的合成说明段；找不到配方就返回空。"""
    inf = RECIPES / "spirit_infusion" / f"{rid}.json"
    run = RECIPES / "runeworking" / f"{rid}.json"

    if inf.exists():
        d = json.loads(inf.read_text(encoding="utf-8"))
        inp = d["input"]
        extras = d.get("extra_items", [])
        spirits = d.get("spirits", [])
        parts = [f"<p><strong>合成</strong>：在灵灾的灵魂灌注中制作。"
                 f"以{mat_name(inp)}×{inp.get('count', 1)}为核心"]
        if extras:
            parts.append("，另加 " + "、".join(
                f"{mat_name(e)}×{e.get('count', 1)}" for e in extras))
        if spirits:
            parts.append("；消耗精魂 " + "、".join(
                f"{SPIRIT_ZH.get(s['type'], s['type'])}×{s['count']}" for s in spirits))
        parts.append("。</p>")
        return "".join(parts)

    if run.exists():
        d = json.loads(run.read_text(encoding="utf-8"))
        p1 = d.get("primaryInput")
        p2 = d.get("secondaryInput")
        s = "<p><strong>合成</strong>：在灵灾的符文制作中制作。"
        if p1:
            s += f"主材为 {mat_name(p1)}×{p1.get('count', 1)}"
        if p2:
            s += f"，副材为 {mat_name(p2)}×{p2.get('count', 1)}"
        return s + "。</p>"

    return ""


def main() -> int:
    rows = json.loads(SRC.read_text(encoding="utf-8"))

    common = [{
        "id": "common_accessory",
        "name": "饰品",
        "ename": "Accessory",
        "regname": "",
        "category": "{文本}",
        "type": "物品/方块",
        "maxstack": 64,
        "remark": (
            "Malstone Mod 通用文本：本条不针对具体物品，"
            "用于承接十九件饰品的共通说明（佩戴方式与合成途径），"
            "供各饰品页在附言中引用。合成途径取自 data/malum/recipes 下的配方文件。"
            f"{tail()}"
        ),
        "html": COMMON_HTML,
        "icon32": "",
        "icon128": "",
    }]
    OUT_COMMON.write_text(json.dumps(common, ensure_ascii=False, indent=2), encoding="utf-8")

    n_recipe = 0
    for r in rows:
        rc = recipe_html(r["id"])
        if rc:
            r["html"] = r["html"] + rc
            n_recipe += 1
        r["remark"] = (
            f"Malstone Mod 资料页：名称取自 lang/zh_cn.json 的 item.malstone.{r['id']} 条目，"
            f"英文名取自 en_us.json，品质取自 ItemRegs 中 Item.Properties 的 Rarity 设定，"
            f"效果取自 lang 下的 .text 子项，属性加成取自各物品类 getAttributeModifiers，"
            f"合成配方取自 data/malum/recipes。"
            f"佩戴方式与合成途径需引用通用文本「饰品」。"
            f"{tail()}"
        )

    OUT_ITEMS.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"通用文本 1 条 → {OUT_COMMON.name}")
    print(f"物品页 {len(rows)} 条 → {OUT_ITEMS.name}，其中 {n_recipe} 条带配方")
    print(f"\n正文长度 {min(len(r['html']) for r in rows)}~{max(len(r['html']) for r in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
