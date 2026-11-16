#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Crafting Dead: Survival 第 2 批：4 个工具 + 1 个医疗品。"""
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
OUT = Path(r"E:\Mod\百科-语料\jar-analyze\cds-新增工具-4397.json")
NS = "craftingdeadsurvival"
REMARK = ("Crafting Dead: Survival 新增资料页：耐久、伤害与堆叠取自 SurvivalItems 的注册定义，"
          "获取方式依据战利品表与配方文件。辛苦喵呜机了")

# (注册名, 中文名, 英文名, 分类, 堆叠, 正文)
ITEMS = [
    ("can_opener", "开罐器", "Can Opener", "工具", 1,
     "<p>开罐器是打开罐头食品的工具。</p>"
     "<p><strong>获取</strong>：模组没有提供合成配方，只能从平民物资、稀有平民物资等战利品容器中搜到。</p>"
     "<p><strong>用途</strong>：在工作台与未开封的罐头无序合成，把罐头变成可以直接食用的开罐版本。"
     "例如玉米罐头、豆子罐头、金枪鱼罐头都需要先开罐。</p>"
     "<p><strong>耐久</strong>：可开罐 8 次，用完即损坏，使用时会消耗自身耐久。</p>"),
    ("screwdriver", "螺丝刀", "Screwdriver", "工具", 1,
     "<p>螺丝刀是拆解与组装用的手工具。</p>"
     "<p><strong>获取</strong>：模组没有提供合成配方，只能从各类战利品容器中搜到。</p>"
     "<p><strong>耐久</strong>：可用 6 次，会消耗耐久。</p>"),
    ("multi_tool", "多功能工具", "Multi Tool", "工具", 1,
     "<p>多功能工具既是工具也是近战武器。</p>"
     "<p><strong>获取</strong>：模组没有提供合成配方，只能从战利品容器中搜到。</p>"
     "<p><strong>属性</strong>：近战伤害 8 点（4 颗心），攻击速度 -2.4，耐久 20。</p>"
     "<p><strong>用途</strong>：兼顾拆解与自卫，在没有合适武器时可临时充当近战手段。</p>"),
    ("rope", "绳子", "Rope", "工具", 1,
     "<p>绳子是制作简易物品的基础材料。</p>"
     "<p><strong>获取</strong>：模组没有提供合成配方，只能从战利品容器中搜到。</p>"
     "<p><strong>用途</strong>：作为合成材料使用，不可堆叠。</p>"),
    ("morphine_syringe", "吗啡注射器", "Morphine Syringe", "医疗", 3,
     "<p>吗啡注射器是应急用的医疗注射剂。</p>"
     "<p><strong>获取</strong>：从医用物资、军用物资等战利品容器中搜到，也可由其它医疗物品合成。</p>"
     "<p><strong>用法</strong>：手持后使用，需要一段操作时间才能完成注射，期间移动或被打断会中止。</p>"
     "<p><strong>堆叠</strong>：最多三个一组。</p>"),
]


def b64_png(path: Path, size: int = 32) -> str:
    img = Image.open(path).convert("RGBA")
    buf = io.BytesIO()
    img.resize((size, size), Image.NEAREST).save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def main() -> int:
    lang = json.loads((JAR / "assets" / NS / "lang" / "en_us.json").read_text(encoding="utf-8"))
    tex = JAR / "assets" / NS / "textures" / "item"

    rows = []
    for rid, zh, en, cat, stack, html in ITEMS:
        p = tex / f"{rid}.png"
        rows.append({
            "id": rid,
            "name": zh,
            "ename": en,
            "regname": f"{NS}:{rid}",
            "category": cat,
            "type": "物品/方块",
            "maxstack": stack,
            "remark": REMARK,
            "html": html,
            "icon32": b64_png(p) if p.exists() else "",
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
    for r in rows:
        print(f"  {r['regname']:<38} {r['name']:<10} [{r['category']}] 堆叠{r['maxstack']} 正文 {len(r['html'])} 图标 {len(r['icon32'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
