#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用模组官方中文名（zh_cn.json）重建食物、工具、刷怪蛋三批 JSON。

修正点：
1. 中文名全部改用 lang/zh_cn.json 的官方译名（skill §6.2 硬要求）
2. 图标保持原图 32×32（模组纹理本身就是 32×32，NEAREST 不放大）
3. 刷怪蛋、丧尸等无静态贴图的物品用原版缺省材质占位；实体留空删除大小图标
"""
import base64
import io
import json
import re
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("需要 Pillow", file=sys.stderr)
    sys.exit(1)

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
JAR = BASE / "cds"
NS = "craftingdeadsurvival"

ZH = json.loads((BASE / "cds-official-zh.json").read_text(encoding="utf-8"))
FOODS = json.loads((BASE / "cds-foods.json").read_text(encoding="utf-8"))
TEX = JAR / "assets" / NS / "textures" / "item"

CONTAINER_ZH = {
    "EMPTY_WATER_BOTTLE": "空水瓶", "EMPTY_WATER_CANTEEN": "空水壶", "EMPTY_FLASK": "空水杯",
    "EMPTY_ICED_TEA": "空冰红茶瓶", "EMPTY_IRON_BREW": "空的铁酿饮料瓶",
    "EMPTY_JUICE_POUCH": "空果汁袋", "EMPTY_LEMON_SODA": "空的柠檬汽水罐",
    "EMPTY_MILK_CARTON": "空牛奶盒", "EMPTY_ORANGE_SODA": "空橙子味汽水瓶",
    "EMPTY_PEPE_SODA": "空的悲伤蛙汽水罐", "EMPTY_SPRITE": "空雪碧瓶",
    "EMPTY_COLA": "空可乐瓶", "EMPTY_ZOMBIE_ENERGY": "空的僵尸能量饮料罐",
}

CANNED = {
    "canned_sweetcorn", "canned_beans", "canned_tuna", "canned_peaches", "canned_pasta",
    "canned_corned_beef", "canned_custard", "canned_pickles", "canned_dog_food",
    "canned_tomato_soup",
}
TOOLS = {
    "can_opener": ("工具", 1), "screwdriver": ("工具", 1),
    "multi_tool": ("工具", 1), "rope": ("工具", 1),
    "morphine_syringe": ("医疗", 3),
}


def fmt(x: float) -> str:
    return str(int(x)) if x == int(x) else str(x)


def b64_png(path: Path, size: int = 32) -> str:
    """模组纹理本身就是 32×32；若小于 32 用 NEAREST，大于 32 用 LANCZOS。"""
    img = Image.open(path).convert("RGBA")
    if img.size != (size, size):
        method = Image.NEAREST if img.width < size else Image.LANCZOS
        img = img.resize((size, size), method)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


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


def icon_of(rid: str) -> str:
    p = TEX / f"{rid}.png"
    return b64_png(p) if p.exists() else ""


def food_html(rid: str, d: dict) -> str:
    zh = ZH.get(rid, rid)
    hunger, sat, water, container, typ = d["hunger"], d["sat"], d["water"], d["container"], d["type"]
    parts = []
    if typ == "ONLY_DRINK":
        parts.append(f"<p>{zh}是模组中的饮品，只能补充水分，不能充饥。</p>")
        parts.append(f"<p><strong>属性</strong>：补水量 {fmt(water)} 点，不提供饱食度。</p>")
        c = CONTAINER_ZH.get(container)
        if c:
            parts.append(f"<p><strong>容器</strong>：喝完留下{c}，空容器可以在水源处重新灌装成对应的满版本。</p>")
    else:
        word = "食物" if typ == "ONLY_FOOD" else "食物兼饮品"
        parts.append(f"<p>{zh}是模组中的{word}。</p>")
        line = f"<p><strong>属性</strong>：饱食度 {fmt(hunger)} 点，饱和度 {fmt(round(hunger * sat, 1))} 点"
        if water > 0:
            line += f"，补水量 {fmt(water)} 点"
        line += "。</p>"
        parts.append(line)
        if rid.startswith("rotten_"):
            parts.append("<p><strong>注意</strong>：这是变质食物，饱食度与补水量都很低，只在没有别的选择时才考虑。</p>")
        elif hunger >= 10:
            parts.append("<p>在本模组的食物里属于饱食度较高的一档，适合长时间外出前食用。</p>")
    parts.append("<p><strong>获取</strong>：从民用战利品、稀有民用战利品、医疗战利品、警用战利品与军用战利品等容器中搜到，"
                 "也可以在创造模式的物品栏里直接取得。</p>")
    return "".join(parts)


def can_html(rid: str) -> str:
    zh = ZH.get(rid, rid)
    open_zh = ZH.get(f"open_{rid}", "")
    return (f"<p>{zh}是未开封的罐头，不能直接食用。</p>"
            f"<p><strong>获取</strong>：从各类战利品容器中搜到。</p>"
            f"<p><strong>用法</strong>：在工作台与开罐器无序合成，变成{open_zh}后才能吃。"
            f"开罐器可用 8 次，用完即损坏。</p>"
            f"<p><strong>堆叠</strong>：三个一组。</p>")


def empty_html(rid: str) -> str:
    zh = ZH.get(rid, rid)
    return (f"<p>{zh}是饮品喝完后留下的空容器。</p>"
            f"<p><strong>获取</strong>：喝完对应的饮品后自动留下，也可从战利品容器中搜到。</p>"
            f"<p><strong>用途</strong>：在水源处右键可以重新灌装，变回对应的满版本。</p>")


def tool_html(rid: str) -> str:
    zh = ZH.get(rid, rid)
    T = {
        "can_opener": (
            f"<p>{zh}是打开罐头食品的工具。</p>"
            "<p><strong>获取</strong>：模组没有提供合成配方，只能从民用战利品、稀有民用战利品等容器中搜到。</p>"
            "<p><strong>用途</strong>：在工作台与未开封的罐头无序合成，把罐头变成可以直接食用的开封版本。</p>"
            "<p><strong>耐久</strong>：可开罐 8 次，用一次消耗一次耐久，用完即损坏。</p>"),
        "screwdriver": (
            f"<p>{zh}是拆解与组装用的手工具。</p>"
            "<p><strong>获取</strong>：模组没有提供合成配方，只能从各类战利品容器中搜到。</p>"
            "<p><strong>耐久</strong>：可用 6 次，每次使用消耗耐久。</p>"),
        "multi_tool": (
            f"<p>{zh}既是工具也是近战武器。</p>"
            "<p><strong>获取</strong>：模组没有提供合成配方，只能从战利品容器中搜到。</p>"
            "<p><strong>属性</strong>：近战伤害 8 点（4 颗心），攻击速度 -2.4，耐久 20。</p>"
            "<p><strong>用途</strong>：兼顾拆解与自卫，在没有合适武器时可临时充当近战手段。</p>"),
        "rope": (
            f"<p>{zh}是制作简易物品的基础材料。</p>"
            "<p><strong>获取</strong>：模组没有提供合成配方，只能从战利品容器中搜到。</p>"
            "<p><strong>用途</strong>：作为合成材料使用，不可堆叠。</p>"),
        "morphine_syringe": (
            f"<p>{zh}是应急用的医疗注射剂。</p>"
            "<p><strong>获取</strong>：从医疗战利品、军用战利品等容器中搜到。</p>"
            "<p><strong>用法</strong>：手持后使用，需要一段操作时间才能完成注射，期间移动或被打断会中止。</p>"
            "<p><strong>堆叠</strong>：最多三个一组。</p>"),
    }
    return T[rid]


def main() -> int:
    # ── 食物 ──
    rows = []
    for d in FOODS:
        rid = d["id"]
        if rid not in ZH:
            print(f"  ⚠ 缺官方名: {rid}")
            continue
        rows.append({
            "id": rid, "name": ZH[rid], "ename": rid,
            "regname": f"{NS}:{rid}", "category": "食物", "type": "物品/方块",
            "maxstack": 3,
            "remark": ("Crafting Dead: Survival 新增资料页：中文名取自模组 lang/zh_cn.json，"
                       "饱食度、饱和度系数、补水量与容器取自 SurvivalItems 里 ConsumableItem 的构造参数。"
                       "辛苦喵呜机了"),
            "html": food_html(rid, d), "icon32": icon_of(rid),
        })
    for rid in sorted(CANNED):
        if rid not in ZH:
            continue
        rows.append({
            "id": rid, "name": ZH[rid], "ename": rid,
            "regname": f"{NS}:{rid}", "category": "食物", "type": "物品/方块",
            "maxstack": 3,
            "remark": ("Crafting Dead: Survival 新增资料页：中文名取自 lang/zh_cn.json，"
                       "开封关系依据 SurvivalRecipeProvider 里的无序合成。辛苦喵呜机了"),
            "html": can_html(rid), "icon32": icon_of(rid),
        })
    for rid in sorted(k for k in ZH if k.startswith("empty_")):
        rows.append({
            "id": rid, "name": ZH[rid], "ename": rid,
            "regname": f"{NS}:{rid}", "category": "食物", "type": "物品/方块",
            "maxstack": 3,
            "remark": ("Crafting Dead: Survival 新增资料页：中文名取自 lang/zh_cn.json，"
                       "空容器与满版本的对应关系取自 ConsumableItem 的 container 参数。辛苦喵呜机了"),
            "html": empty_html(rid), "icon32": icon_of(rid),
        })
    (BASE / "cds-新增食物-4397.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"食物：{len(rows)} 条")

    # ── 工具 ──
    rows = []
    for rid, (cat, stack) in TOOLS.items():
        rows.append({
            "id": rid, "name": ZH.get(rid, rid), "ename": rid,
            "regname": f"{NS}:{rid}", "category": cat, "type": "物品/方块",
            "maxstack": stack,
            "remark": ("Crafting Dead: Survival 新增资料页：中文名取自 lang/zh_cn.json，"
                       "耐久与堆叠取自 SurvivalItems 的注册定义。辛苦喵呜机了"),
            "html": tool_html(rid), "icon32": icon_of(rid),
        })
    (BASE / "cds-新增工具-4397.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"工具：{len(rows)} 条")

    # ── 刷怪蛋（物品，用缺省材质占位）──
    miss_tex = missing_texture(32)
    # 站点已有 5 个刷怪蛋页（快速/坦克/柔弱/警察/医生），跳过避免重复创建
    EXISTING = {
        "fast_zombie_spawn_egg", "tank_zombie_spawn_egg", "weak_zombie_spawn_egg",
        "police_zombie_spawn_egg", "doctor_zombie_spawn_egg",
    }
    eggs = [k for k in ZH if k.endswith("_spawn_egg") and k not in EXISTING]
    rows = []
    for rid in sorted(eggs):
        mob = ZH[rid].replace("刷怪蛋", "")
        rows.append({
            "id": rid, "name": ZH[rid], "ename": rid,
            "regname": f"{NS}:{rid}", "category": "仅创造", "type": "物品/方块",
            "maxstack": 1,
            "remark": ("Crafting Dead: Survival 补齐刷怪蛋资料页：中文名取自 lang/zh_cn.json。"
                       "刷怪蛋图标由游戏按两色程序化绘制、无静态贴图，"
                       "已使用原版缺省材质（品红与黑棋盘格）占位。辛苦喵呜机了"),
            "html": (f"<p>{ZH[rid]}是用于生成{mob}的创造模式物品。</p>"
                     f"<p><strong>获取</strong>：只能在创造模式的物品栏里取得，生存模式没有获取途径。</p>"
                     f"<p><strong>用法</strong>：右击方块会立即生成一只{mob}，也可以用发射器发射。"
                     f"在和平模式下，由刷怪蛋生成的敌对生物会立刻消失。</p>"
                     f"<p><strong>切换生物</strong>：创造模式下对着目标生物按鼠标中键，可以直接拿到它对应的刷怪蛋。</p>"),
            "icon32": miss_tex,
        })
    (BASE / "cds-新增刷怪蛋-4397.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"刷怪蛋：{len(rows)} 条")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
