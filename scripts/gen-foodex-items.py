#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Food Extend（classId 5439）14 个食物资料页。

mcmod 现有 9 个页面 → 生成编辑 JSON
缺失 5 个          → 生成新增 JSON

属性来源：MyItemRegister 里 food(hunger, saturationModifier) 的构造参数。
satnack 标记对应 snackFood()，吃得比普通食物快。
配方来源：data/foodex/recipes 下 15 个配方文件。
"""
import base64
import io
import json
import random
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
TEX = BASE / "foodex/assets/foodex/textures/item"
OUT_EDIT = BASE / "foodex-编辑-5439.json"
OUT_NEW = BASE / "foodex-新增-5439.json"
NS = "foodex"

# ── 收尾随机化（skill §6.2.3）──
_PAW = ["呜喵", "喵呜", "喵喵"]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


# ── 物品数据 ──
# id, 中文名, hunger, sat_mod, snack, 配方说明, 额外效果
ITEMS = [
    ("honey_porkchop", "蜂蜜猪排", 12, 1.1667, False, "一个熟猪排加一瓶蜂蜜，无序合成", None),
    ("candied_carrot", "糖渍胡萝卜", 3, 1.0, False, "一份糖加一根胡萝卜，无序合成", None),
    ("honey_apple", "蜂蜜苹果", 9, 0.444, True, "一个苹果加一瓶蜂蜜，无序合成",
     "零食类，进食耗时比普通食物短"),
    ("squid_cooked", "熟鱿鱼", 4, 1.0, False, "把鱿鱼放进熔炉烧炼或烟熏炉烟熏", None),
    ("squid", "鱿鱼", 1, 1.5, False, "两个墨囊无序合成", "饱和度系数高，但饥饿值只有 1 点"),
    ("squid_shreds", "鱿鱼丝", 1, 1.1, True, "一个熟鱿鱼拆成四份",
     "零食类，进食耗时比普通食物短"),
    ("honey_beef", "蜂蜜牛排", 12, 1.1667, False, "一个熟牛肉加一瓶蜂蜜，无序合成", None),
    ("night_vision_berries", "明目果", 1, 0.4, True, "一份糖渍胡萝卜加一份发光浆果，一次产出六个",
     "零食类；吃掉后必定获得 120 秒夜视效果，且饥饿值满时也能吃"),
    ("honey_bread", "蜂蜜面包", 10, 0.7, False, "一个面包加一瓶蜂蜜，无序合成", None),
    ("candied_apple", "糖渍苹果", 4, 1.0, False, "一份糖加一个苹果，无序合成", None),
    ("candied_baked_potato", "糖烤马铃薯", 6, 1.0, False, "一份糖加一个烤马铃薯，无序合成", None),
    ("chocolate", "巧克力", 4, 0.6, False, "一份糖加两份可可豆，无序合成", None),
    ("cooked_egg", "煮鸡蛋", 3, 0.6, False, "把鸡蛋放进熔炉烧炼", None),
    ("roasted_carrots", "烤胡萝卜", 4, 1.0, False, "把胡萝卜放进熔炉烧炼", None),
]

# mcmod 现有的 9 个页面（按名称对上）
EXISTING = {
    "蜂蜜猪排": "542993", "糖渍胡萝卜": "542994", "蜂蜜苹果": "542995",
    "熟鱿鱼": "542996", "鱿鱼": "542997", "鱿鱼丝": "542998",
    "蜂蜜牛排": "542999", "明目果": "543000", "蜂蜜面包": "543001",
}


def b64(rid: str):
    p = TEX / f"{rid}.png"
    if not p.exists():
        return ""
    img = Image.open(p).convert("RGBA")
    if img.size != (32, 32):
        method = Image.NEAREST if img.width < 32 else Image.LANCZOS
        img = img.resize((32, 32), method)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def fmt(x: float) -> str:
    return str(int(x)) if x == int(x) else f"{x:.1f}"


def build_html(zh: str, hunger: int, sat: float, snack: bool, recipe: str, extra) -> str:
    real_sat = hunger * sat
    parts = [f"<p>{zh}是 Food Extend 添加的食物，由原版材料加工而成。</p>",
             f"<p><strong>属性</strong>：回复 {hunger} 点饥饿值，{fmt(real_sat)} 点饱和度。</p>"]
    if extra:
        parts.append(f"<p><strong>特点</strong>：{extra}。</p>")
    parts.append(f"<p><strong>获取</strong>：{recipe}。</p>")
    parts.append("<p><strong>堆叠</strong>：与其他食物一样按 64 个一组堆叠。</p>")
    return "".join(parts)


def main() -> int:
    edits, news = [], []
    for rid, zh, hunger, sat, snack, recipe, extra in ITEMS:
        html = build_html(zh, hunger, sat, snack, recipe, extra)
        icon = b64(rid)
        if zh in EXISTING:
            edits.append({
                "id": EXISTING[zh],
                "name": zh,
                "editRemark": (f"补全正文：饥饿值与饱和度取自 MyItemRegister 里该物品的 "
                               f"food({hunger}, {sat}) 构造参数，配方依据 data/foodex/recipes 下的定义。"
                               f"{tail()}"),
                "editNote": f"补全正文：回复 {hunger} 点饥饿值、{fmt(hunger*sat)} 点饱和度，以及获取方式。",
                "html": html,
            })
        else:
            news.append({
                "id": rid,
                "name": zh,
                "ename": rid,
                "regname": f"{NS}:{rid}",
                "category": "食物",
                "type": "物品/方块",
                "maxstack": 64,
                "remark": (f"Food Extend 新增资料页：中文名取自 lang/zh_cn.json，"
                           f"饥饿值与饱和度取自 MyItemRegister 里该物品的 food({hunger}, {sat}) 构造参数，"
                           f"配方依据 data/foodex/recipes 下的定义。{tail()}"),
                "html": html,
                "icon32": icon,
            })

    OUT_EDIT.write_text(json.dumps(edits, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_NEW.write_text(json.dumps(news, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"编辑 {len(edits)} 条 → {OUT_EDIT.name}  ({OUT_EDIT.stat().st_size/1024:.1f} KB)")
    print(f"新增 {len(news)} 条 → {OUT_NEW.name}  ({OUT_NEW.stat().st_size/1024:.1f} KB)")
    print(f"\n缺失的 5 个：{[n['name'] for n in news]}")

    print("\n=== 属性总表 ===")
    print(f"{'物品':<12}{'饥饿值':>6}{'饱和度':>8}{'零食':>6}  配方")
    for rid, zh, h, s, snack, recipe, extra in ITEMS:
        print(f"  {zh:<10}{h:>6}{fmt(h*s):>8}{'✓' if snack else '':>6}  {recipe[:40]}")

    print("\n=== 收尾抽样（轮换检查）===")
    for r in edits[:5]:
        print(f"  …{r['editRemark'][-16:]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
