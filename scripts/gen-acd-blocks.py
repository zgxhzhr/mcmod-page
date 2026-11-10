#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Animania Cats & Dogs（classId 3863）7 个方块的批量新增 JSON。

图标来源：assets/catsdogs/animania/textures/items/<id>.png（16×16 独立贴图）。
注意：这些方块放置到世界里显示的是原版方块（作者没做 3D 模型，blockstate 直接指向
minecraft:white_wool / iron_block 等），正文里要点明这一点。
"""
import base64
import io
import json
import random
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
TEX = BASE / "acd/assets/catsdogs/animania/textures/items"
OUT = BASE / "acd-方块导入-3863.json"
NS = "animania"

_PAW = ["呜喵", "喵呜", "喵喵"]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


BLOCKS = [
    {
        "id": "pet_bowl", "name": "Pet Bowl", "tex": "pet_bowl",
        "category": "功能方块",
        "appearance": "铁块",
        "html": "<p>Pet Bowl 是喂食小型动物的容器，作用相当于田里的饲料槽，但只服务猫、狗、仓鼠这类体型小的动物。</p>"
                "<p><strong>用法</strong>：放置后把食物放进去，附近的宠物会自行取食。适合集中投喂，不用一只一只喂。</p>"
                "<p><strong>合成</strong>：4 个铁锭加 2 个铁粒。</p>"
                "<p><strong>外观</strong>：放置后显示为原版铁块，作者没有为它单独制作方块模型。</p>",
    },
    {
        "id": "cat_bed_1", "name": "Cat Bed", "tex": "cat_bed_1",
        "category": "功能方块",
        "appearance": "白色羊毛",
        "html": "<p>Cat Bed 是猫的睡觉地点，白色款式。</p>"
                "<p><strong>用法</strong>：猫会把它当作固定的休息点，夜里或空闲时回到这里睡觉。同系列的还有粉色款。</p>"
                "<p><strong>合成</strong>：5 份羊毛，摆成凹字形。</p>"
                "<p><strong>外观</strong>：放置后显示为白色羊毛方块。</p>",
    },
    {
        "id": "cat_bed_2", "name": "Cat Bed", "tex": "cat_bed_2",
        "category": "功能方块",
        "appearance": "粉色羊毛",
        "html": "<p>Cat Bed 是猫的睡觉地点，粉色款式。</p>"
                "<p><strong>用法</strong>：与白色款功能相同，只差外观。粉色的合成图案比白色款多两格羊毛。</p>"
                "<p><strong>合成</strong>：7 份羊毛，摆成回字形。</p>"
                "<p><strong>外观</strong>：放置后显示为粉色羊毛方块。</p>",
    },
    {
        "id": "cat_tower", "name": "Cat Tower", "tex": "cat_tower",
        "category": "装饰方块",
        "appearance": "橡木木板",
        "html": "<p>Cat Tower 是猫爬架，属于装饰方块。</p>"
                "<p><strong>用法</strong>：没有实际功能，仅作摆设。猫可以把它当作睡觉点之一。</p>"
                "<p><strong>合成</strong>：木板、木棍与羊毛。</p>"
                "<p><strong>外观</strong>：放置后显示为橡木木板方块，看不到爬架造型。</p>",
    },
    {
        "id": "dog_house", "name": "Dog House", "tex": "dog_house",
        "category": "功能方块",
        "appearance": "红色硬化粘土",
        "html": "<p>Dog House 是狗的睡觉地点。</p>"
                "<p><strong>用法</strong>：狗会把它当作固定的休息点，空闲时回来躺下。</p>"
                "<p><strong>合成</strong>：红色与白色硬化粘土，摆成屋形。</p>"
                "<p><strong>外观</strong>：放置后显示为红色硬化粘土方块。</p>",
    },
    {
        "id": "dog_pillow", "name": "Dog Pillow", "tex": "dog_pillow",
        "category": "功能方块",
        "appearance": "白色羊毛",
        "html": "<p>Dog Pillow 是狗垫，另一种狗的睡觉地点。</p>"
                "<p><strong>用法</strong>：与狗屋功能相同，区别是不占立体空间，铺在地面即可。</p>"
                "<p><strong>合成</strong>：6 份羊毛，两行铺满。</p>"
                "<p><strong>外观</strong>：放置后显示为白色羊毛方块。</p>",
    },
    {
        "id": "litter_box", "name": "Litter Box", "tex": "litter_box",
        "category": "装饰方块",
        "appearance": "蓝色硬化粘土",
        "html": "<p>Litter Box 是猫砂盆，属于装饰方块。</p>"
                "<p><strong>用法</strong>：没有实际功能，作者的手册里明确写了这一批装饰方块「暂不具备用途」。</p>"
                "<p><strong>合成</strong>：铁锭与白色硬化粘土。</p>"
                "<p><strong>外观</strong>：放置后显示为蓝色硬化粘土方块。</p>",
    },
]


def b64(name: str) -> str:
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
    for b in BLOCKS:
        rows.append({
            "id": b["id"],
            "name": b["name"],
            "ename": "",
            "regname": f"{NS}:{b['id']}",
            "category": b["category"],
            "type": "物品/方块",
            "maxstack": 64,
            "remark": (
                "Cats & Dogs 新增方块资料页：名称取自 lang/en_us.json（模组只有 en_us）。"
                "功能与合成依据 assets/catsdogs/animania 下的 blockstates、recipes 与手册文本。"
                f"{tail()}"
            ),
            "html": b["html"],
            "icon32": b64(b["tex"]),
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)")
    from collections import Counter
    print("分类:", dict(Counter(r["category"] for r in rows)))
    for r in rows:
        print(f"  {r['name']:<16} {r['icon32'][:20] if r['icon32'] else '无图标'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
