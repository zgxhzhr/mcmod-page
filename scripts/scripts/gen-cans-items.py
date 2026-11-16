#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canned Food and Drinks（classId 14363）物品页 —— 31 件。

数据来源：
  食物属性  Item* 类的 ItemFood 构造参数 super(饥饿值, 饱和修正, 是否喂狼)
            实际饱和度 = 饥饿值 × 饱和修正 × 2
  药水效果  Procedure* 里的 PotionEffect（golden apple / enchanted golden apple）
  配方      assets/cannedfoodanddrinks/recipes 下 31 个 json
  图标      16×16 纹理 NEAREST 放大到 128 与 32

模组只有 en_us.lang，无中文语言文件，所以主名用英文原名、次要名留空。
"""
import base64
import io
import json
import random
import re
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
CANS = BASE / "cans/assets/cannedfoodanddrinks"
SRC = BASE / "cans-src"
ICONS128 = BASE / "cans-icons128"
ICONS32 = BASE / "cans-icons32"
OUT = BASE / "cans-物品导入-14363.json"
NS = "cannedfoodanddrinks"

_PAW = ["呜喵", "喵呜", "喵喵"]

# 原版食物中文名（供正文描述用；物品主名仍用英文原名）
VANILLA_ZH = {
    "apple": "苹果", "baked_potato": "烤土豆", "beetroot": "甜菜根",
    "beetroot_soup": "甜菜汤", "bread": "面包", "cake": "蛋糕",
    "carrot": "胡萝卜", "cooked_beef": "牛排", "cooked_chicken": "熟鸡肉",
    "cooked_fish": "熟鱼", "cooked_mutton": "熟羊肉", "cooked_porkchop": "熟猪排",
    "cooked_rabbit": "熟兔肉", "golden_apple": "金苹果", "golden_carrot": "金胡萝卜",
    "melon": "西瓜片", "mushroom_stew": "蘑菇煲", "potato": "土豆",
    "pumpkin_pie": "南瓜派", "rabbit_stew": "兔肉煲",
}

# 食物主名对应关系（从 Item 类扫出来）
FOOD_INFO = {}
for p in sorted(SRC.rglob("Item*.java")):
    t = p.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"super\((\d+),\s*([\d.]+)f,\s*(true|false)\)", t)
    if m:
        FOOD_INFO[p.stem] = (int(m.group(1)), float(m.group(2)))

# classId → registry id
CLASS2ID = {
    "ItemCannedapple": "cannedapple", "ItemCannedbakedpotato": "cannedbakedpotato",
    "ItemCannedBeetroot": "cannedbeetroot", "ItemCannedBeetrotSoup": "cannedbeetrotsoup",
    "ItemCannedBread": "cannedbread", "ItemCannedCake": "cannedcake",
    "ItemCannedCarrot": "cannedcarrot", "ItemCannedChicken": "cannedchicken",
    "ItemCannedCod": "cannedcod",
    "ItemCannedEnchantedGoldenApple": "cannedenchantedgoldenapple",
    "ItemCannedGoldenApple": "cannedgoldenapple",
    "ItemCannedGoldenCarrot": "cannedgoldencarrot", "ItemCannedMelon": "cannedmelon",
    "ItemCannedMushroomStew": "cannedmushroomstew", "ItemCannedMutton": "cannedmutton",
    "ItemCannedPorkchop": "cannedporkchop", "ItemCannedPotato": "cannedpotato",
    "ItemCannedPumpkinPie": "cannedpumpkinpie", "ItemCannedRabbit": "cannedrabbit",
    "ItemCannedRabbitStew": "cannedrabbitstew", "ItemCannedSalmon": "cannedsalmon",
    "ItemCannedSteak": "cannedsteak",
    "ItemAppleJuice": "applejuice", "ItemBeetrootJuice": "beetrootjuice",
    "ItemCarrotJuice": "carrotjuice", "ItemMelonJuice": "melonjuice",
    "ItemGoldenCarrotJuice": "goldencarrotjuice",
    "ItemGoldenAppleJuice": "goldenapplejuice",
    "ItemEnchantedGoldenAppleJuice": "enchantedgoldenapplejuice",
    "ItemFoodCan": "foodcan", "ItemDrinkingCan": "drinkingcan",
}

# 药水效果（从 Procedure* 提取）
GOLDEN_EFFECT = "食用后获得伤害吸收 II（125 秒）与生命恢复 III（5 秒）"
ENCHANTED_EFFECT = (
    "食用后获得伤害吸收 V（120 秒）、生命恢复 III（20 秒）、"
    "抗性提升 II 与抗火 II（各 300 秒）"
)


def b64(path: Path):
    if not path.exists():
        return ""
    buf = io.BytesIO()
    Image.open(path).convert("RGBA").save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def title_case(s: str) -> str:
    small = {"of", "the", "and", "a", "an", "to", "in", "on", "for", "with"}
    out = []
    for i, w in enumerate(s.split()):
        lw = w.lower()
        if i > 0 and lw in small:
            out.append(lw)
        elif "-" in w:
            out.append("-".join(x[:1].upper() + x[1:] for x in w.split("-")))
        else:
            out.append(lw[:1].upper() + lw[1:])
    return " ".join(out)


def main() -> int:
    lang = {}
    for line in (CANS / "lang/en_us.lang").read_text(encoding="utf-8", errors="ignore").split("\n"):
        if "=" in line and line.startswith("item."):
            k, v = line.split("=", 1)
            # lang 里有两个物品名带 §d / §b 颜色代码（附魔金苹果的紫色、金苹果的蓝色），
            # 页面标题不能带这些控制字符
            zh = re.sub(r"§.", "", v.strip())
            lang[k.replace("item.", "").replace(".name", "")] = zh

    # 配方
    recipes = {}
    for p in (CANS / "recipes").glob("*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        out_item = d.get("result", {}).get("item", "").replace(NS + ":", "")
        if "ingredients" in d:
            ingredients = [
                i.get("item", "?").replace("minecraft:", "").replace(NS + ":", "")
                for i in d["ingredients"]
            ]
            recipes[out_item] = ("无序", ingredients)
        elif "pattern" in d:
            key = d.get("key", {})
            items = sorted(set(
                v.get("item", "?").replace("minecraft:", "").replace(NS + ":", "")
                for v in key.values()
            ))
            recipes[out_item] = ("有序", items, d.get("pattern"))

    # 模组里 cannedgoldenapple 与 cannedenchantedgoldenapple 的显示名完全相同
    # （只靠 §b / §d 颜色区分），去掉颜色后必须手动区分
    NAME_FIX = {"cannedenchantedgoldenapple": "Canned Enchanted Golden Apple"}

    rows = []
    for cls, rid in CLASS2ID.items():
        name = NAME_FIX.get(rid) or lang.get(rid, rid)
        ename = ""
        is_food = rid.startswith("canned")
        is_juice = rid.endswith("juice")
        is_can = rid in ("foodcan", "drinkingcan")

        # 正文
        if is_can:
            n_nugget = 8 if rid == "foodcan" else 6
            use = "与食物合成罐装食品" if rid == "foodcan" else "与食物合成果汁"
            shape = "八颗铁粒围成一圈" if rid == "foodcan" else "六颗铁粒分两行"
            html = (
                f"<p>{name}是 Canned Food and Drinks 添加的空罐子，用于{use}。</p>"
                f"<p><strong>合成</strong>：{shape}，一次产出八个。</p>"
                "<p><strong>消耗</strong>：合成时消耗掉，不回收。</p>"
            )
            cat = "罐子"
        else:
            hunger, sat_mod = FOOD_INFO.get(cls, (0, 0.0))
            sat = round(hunger * sat_mod * 2, 1)
            kind = "果汁" if is_juice else "罐装食品"
            verb = "饮用" if is_juice else "食用"
            act = "drink" if is_juice else "eat"

            # 原料
            ing = recipes.get(rid)
            src_food = ""
            if ing:
                for x in ing[1]:
                    if x not in ("foodcan", "drinkingcan", "iron_nugget"):
                        src_food = VANILLA_ZH.get(x, x)
                        break

            html = f"<p>{name}是 Canned Food and Drinks 添加的{kind}，"
            html += f"把原版的{src_food}装进罐子里做成。" if src_food else "由罐子加工而成。"
            html += "</p>"

            if hunger or sat:
                html += (
                    f'<p><strong>饥饿值</strong>：[icon:hunger-level={hunger},点]　'
                    f'<strong>饱和度</strong>：[icon:saturation-level={sat},点]</p>'
                )
            else:
                html += "<p><strong>恢复</strong>：不恢复饥饿值与饱和度。</p>"

            if rid in ("cannedgoldenapple", "goldenapplejuice"):
                html += f"<p><strong>额外效果</strong>：{GOLDEN_EFFECT}。</p>"
            elif rid in ("cannedenchantedgoldenapple", "enchantedgoldenapplejuice"):
                html += f"<p><strong>额外效果</strong>：{ENCHANTED_EFFECT}。</p>"

            html += "<p><strong>合成</strong>：罐子加原版食材，无序合成，摆位随意。</p>"
            cat = "果汁" if is_juice else "罐装食品"

        rows.append({
            "id": rid,
            "name": name,
            "ename": ename,
            "regname": f"{NS}:{rid}",
            "category": cat,
            "type": "物品/方块",
            "maxstack": 64,
            "remark": (
                f"Canned Food and Drinks 资料页：名称取自 lang/en_us.lang 的 item.{rid}.name 条目"
                f"（模组无中文语言文件），"
                + (f"饥饿值与饱和度取自 ItemFood 构造参数，"
                   if not is_can else "")
                + "配方取自 assets/recipes 下的 json。"
                + tail()
            ),
            "html": html,
            "icon32": b64(ICONS32 / f"{NS}__{rid}.png"),
            "icon128": b64(ICONS128 / f"{NS}__{rid}.png"),
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)\n")
    for r in rows:
        print(f"  {r['name']:<32}{r['category']:<6}{len(r['html']):>4} 字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
