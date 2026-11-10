#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Crafting Dead: Survival 第 3 批：食物 / 饮料 / 罐头 / 空瓶。

数据来源：SurvivalItems.java 里 ConsumableItem 的构造参数
(hunger, saturationModifier, water, container, type) 与普通 Item 的堆叠定义。
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

JAR = Path(r"E:\Mod\百科-语料\jar-analyze\cds")
OUT = Path(r"E:\Mod\百科-语料\jar-analyze\cds-新增食物-4397.json")
NS = "craftingdeadsurvival"
REMARK = ("Crafting Dead: Survival 新增资料页：饱食度、饱和度系数、补水量与容器取自 SurvivalItems "
          "里 ConsumableItem 的构造参数，堆叠取自物品属性定义。辛苦喵呜机了")

# 中文名对照
ZH = {
    # 饮料
    "water_bottle": ("水瓶", "Water Bottle"), "water_canteen": ("水壶", "Water Canteen"),
    "flask": ("烧瓶", "Flask"), "iced_tea": ("冰茶", "Ice Tea"),
    "iron_brew": ("铁酿", "Iron Brew"), "juice_pouch": ("果汁袋", "Juice Pouch"),
    "lemon_soda": ("柠檬苏打", "Lemon Soda"), "milk_carton": ("牛奶盒", "Milk Carton"),
    "orange_soda": ("橙子苏打", "Orange Soda"), "pepe_soda": ("佩佩汽水", "Pepe Soda"),
    "sprite": ("雪碧", "Sprite"), "cola": ("可乐", "Cola"),
    "zombie_energy": ("僵尸能量饮料", "Zombie Energy Can"),
    # 零食 / 主食
    "power_bar": ("能量棒", "Power Bar"), "candy_bar": ("糖果棒", "Candy Bar"),
    "cereal": ("麦片", "Cereal"), "mre": ("军用口粮", "MRE"),
    "rice_bag": ("米袋", "Rice Bag"), "noodles": ("面条", "Noodles"),
    "chips": ("薯片", "Chips"), "ranch_chips": ("牧场薯片", "Ranch Chips"),
    "cheesy_chips": ("芝士薯片", "Cheesy Chips"), "salted_chips": ("盐味薯片", "Salted Chips"),
    "popcorn": ("爆米花", "Popcorn"), "nutty_cereal": ("坚果麦片", "Nutty Cereal"),
    "emerald_cereal": ("翡翠麦片", "Emerald Cereal"), "flake_cereal": ("玉米片", "Flake Cereal"),
    # 水果
    "orange": ("橙子", "Orange"), "rotten_orange": ("腐烂的橙子", "Rotten Orange"),
    "pear": ("梨", "Pear"), "rotten_pear": ("腐烂的梨", "Rotten Pear"),
    "rotten_apple": ("腐烂的苹果", "Rotten Apple"),
    "rotten_melon_slice": ("腐烂的西瓜片", "Rotten Melon Slice"),
    "blueberry": ("蓝莓", "Blueberry"), "rotten_blueberry": ("腐烂的蓝莓", "Rotten Blueberry"),
    "raspberry": ("树莓", "Raspberry"), "rotten_raspberry": ("腐烂的树莓", "Rotten Raspberry"),
    # 开罐版
    "open_canned_sweetcorn": ("开罐甜玉米", "Open Canned Sweetcorn"),
    "open_canned_beans": ("开罐豆子", "Open Canned Beans"),
    "open_canned_tuna": ("开罐金枪鱼", "Open Canned Tuna"),
    "open_canned_peaches": ("开罐桃子", "Open Canned Peaches"),
    "open_canned_pasta": ("开罐意面", "Open Canned Pasta"),
    "open_canned_corned_beef": ("开罐咸牛肉", "Open Canned Corned Beef"),
    "open_canned_custard": ("开罐蛋奶", "Open Canned Custard"),
    "open_canned_pickles": ("开罐腌黄瓜", "Open Canned Pickles"),
    "open_canned_dog_food": ("开罐狗粮", "Open Canned Dog Food"),
    "open_canned_tomato_soup": ("开罐番茄汤", "Open Canned Tomato Soup"),
    # 未开罐
    "canned_sweetcorn": ("甜玉米罐头", "Canned Sweetcorn"),
    "canned_beans": ("豆子罐头", "Canned Beans"),
    "canned_tuna": ("金枪鱼罐头", "Canned Tuna"),
    "canned_peaches": ("桃子罐头", "Canned Peaches"),
    "canned_pasta": ("意面罐头", "Canned Pasta"),
    "canned_corned_beef": ("咸牛肉罐头", "Canned Corned Beef"),
    "canned_custard": ("蛋奶罐头", "Canned Custard"),
    "canned_pickles": ("腌黄瓜罐头", "Canned Pickles"),
    "canned_dog_food": ("狗粮罐头", "Canned Dog Food"),
    "canned_tomato_soup": ("番茄汤罐头", "Canned Tomato Soup"),
    # 空瓶
    "empty_water_bottle": ("空水瓶", "Empty Water Bottle"),
    "empty_water_canteen": ("空水壶", "Empty Water Canteen"),
    "empty_flask": ("空烧瓶", "Empty Flask"),
    "empty_iced_tea": ("空冰茶罐", "Empty Ice Tea"),
    "empty_iron_brew": ("空铁酿瓶", "Empty Iron Brew Bottle"),
    "empty_juice_pouch": ("空果汁袋", "Empty Juice Pouch"),
    "empty_lemon_soda": ("空柠檬苏打瓶", "Empty Lemon Soda"),
    "empty_milk_carton": ("空牛奶盒", "Empty Milk Carton"),
    "empty_orange_soda": ("空橙子苏打瓶", "Empty Orange Soda"),
    "empty_pepe_soda": ("空佩佩汽水瓶", "Empty Pepe Soda"),
    "empty_sprite": ("空雪碧瓶", "Empty Sprite Bottle"),
    "empty_cola": ("空可乐瓶", "Empty Cola Bottle"),
    "empty_zombie_energy": ("空能量饮料罐", "Empty Zombie Energy Can"),
}

CONTAINER_ZH = {
    "EMPTY_WATER_BOTTLE": "空水瓶", "EMPTY_WATER_CANTEEN": "空水壶", "EMPTY_FLASK": "空烧瓶",
    "EMPTY_ICED_TEA": "空冰茶罐", "EMPTY_IRON_BREW": "空铁酿瓶", "EMPTY_JUICE_POUCH": "空果汁袋",
    "EMPTY_LEMON_SODA": "空柠檬苏打瓶", "EMPTY_MILK_CARTON": "空牛奶盒",
    "EMPTY_ORANGE_SODA": "空橙子苏打瓶", "EMPTY_PEPE_SODA": "空佩佩汽水瓶",
    "EMPTY_SPRITE": "空雪碧瓶", "EMPTY_COLA": "空可乐瓶", "EMPTY_ZOMBIE_ENERGY": "空能量饮料罐",
}


def fmt(x: float) -> str:
    return str(int(x)) if x == int(x) else str(x)


def b64_png(path: Path, size: int = 32) -> str:
    img = Image.open(path).convert("RGBA")
    buf = io.BytesIO()
    img.resize((size, size), Image.NEAREST).save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def build_html(rid: str, d: dict) -> str:
    zh, _ = ZH[rid]
    hunger, sat, water, container, typ = d["hunger"], d["sat"], d["water"], d["container"], d["type"]

    parts = []
    if typ == "ONLY_DRINK":
        parts.append(f"<p>{zh}是模组中的饮品，只能补充水分，不能充饥。</p>")
        parts.append(f"<p><strong>属性</strong>：补水量 {water} 点，不提供饱食度。</p>")
        c = CONTAINER_ZH.get(container)
        if c:
            parts.append(f"<p><strong>容器</strong>：喝完留下{c}，空容器可以在水源处重新灌装成对应的满版本。</p>")
    else:
        food_word = "食物" if typ == "ONLY_FOOD" else "食物兼饮品"
        parts.append(f"<p>{zh}是模组中的{food_word}。</p>")
        real_sat = hunger * sat
        line = f"<p><strong>属性</strong>：饱食度 {fmt(hunger)} 点，饱和度 {fmt(round(real_sat, 1))} 点"
        if water > 0:
            line += f"，补水量 {water} 点"
        line += "。</p>"
        parts.append(line)
        if "rotten" in rid or rid.startswith("open_canned_dog_food"):
            parts.append("<p><strong>注意</strong>：这是变质或不可口的食物，吃下去收益很低，只在没有别的选择时才考虑。</p>")
        elif hunger >= 10:
            parts.append("<p>在本模组的食物里属于饱食度较高的一档，适合长时间外出前食用。</p>")

    parts.append("<p><strong>获取</strong>：从平民物资、稀有平民物资、医用物资、警用物资与军用物资等战利品容器中搜到，"
                 "也可以在创造模式的物品栏里直接取得。</p>")
    return "".join(parts)


def build_can_html(rid: str) -> str:
    zh, _ = ZH[rid]
    return (f"<p>{zh}是未开封的罐头，不能直接食用。</p>"
            f"<p><strong>获取</strong>：从各类战利品容器中搜到。</p>"
            f"<p><strong>用法</strong>：在工作台与开罐器无序合成，变成对应的开罐版本后才能吃。"
            f"开罐器可用 8 次，用完即损坏。</p>"
            f"<p><strong>堆叠</strong>：三个一组。</p>")


def build_empty_html(rid: str) -> str:
    zh, _ = ZH[rid]
    return (f"<p>{zh}是饮品喝完后留下的空容器。</p>"
            f"<p><strong>获取</strong>：喝完对应的饮品后自动留下，也可从战利品容器中搜到。</p>"
            f"<p><strong>用途</strong>：在水源处右键可以重新灌装，变回对应的满版本。</p>")


def main() -> int:
    foods = json.loads((JAR.parent / "cds-foods.json").read_text(encoding="utf-8"))
    tex = JAR / "assets" / NS / "textures" / "item"

    # 未开罐与空瓶：普通 Item，堆叠 3
    plain = {
        "canned_sweetcorn", "canned_beans", "canned_tuna", "canned_peaches", "canned_pasta",
        "canned_corned_beef", "canned_custard", "canned_pickles", "canned_dog_food",
        "canned_tomato_soup",
    }
    empties = {k for k in ZH if k.startswith("empty_")}

    rows = []
    for d in foods:
        rid = d["id"]
        if rid not in ZH:
            print(f"  ⚠ 缺中文名: {rid}")
            continue
        zh, en = ZH[rid]
        p = tex / f"{rid}.png"
        rows.append({
            "id": rid, "name": zh, "ename": en,
            "regname": f"{NS}:{rid}", "category": "食物",
            "type": "物品/方块", "maxstack": 3,
            "remark": REMARK,
            "html": build_html(rid, d),
            "icon32": b64_png(p) if p.exists() else "",
        })

    for rid in sorted(plain):
        if rid not in ZH:
            continue
        zh, en = ZH[rid]
        p = tex / f"{rid}.png"
        rows.append({
            "id": rid, "name": zh, "ename": en,
            "regname": f"{NS}:{rid}", "category": "食物",
            "type": "物品/方块", "maxstack": 3,
            "remark": REMARK,
            "html": build_can_html(rid),
            "icon32": b64_png(p) if p.exists() else "",
        })

    for rid in sorted(empties):
        zh, en = ZH[rid]
        p = tex / f"{rid}.png"
        rows.append({
            "id": rid, "name": zh, "ename": en,
            "regname": f"{NS}:{rid}", "category": "食物",
            "type": "物品/方块", "maxstack": 3,
            "remark": REMARK,
            "html": build_empty_html(rid),
            "icon32": b64_png(p) if p.exists() else "",
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
    from collections import Counter
    print("分类:", dict(Counter(r["category"] for r in rows)))
    no_icon = [r["id"] for r in rows if not r["icon32"]]
    if no_icon:
        print(f"⚠ 无图标 {len(no_icon)} 个: {no_icon}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
