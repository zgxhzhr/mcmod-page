#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为 Baby Delight 生成 mcmod 批量新增用的 items.json（按 skill §6.6 字段规范）。

字段：id / name / ename / regname / category / type / remark / html / icon32 / maxstack

正文从 baby-物品正文/ 目录读取 <注册id>.html，没有则留空。
图标从 jar 的 textures/items 与 textures/blocks 读取，最近邻放大到 32×32 转裸 base64。
"""
import base64
import io
import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("需要 Pillow：pip install pillow", file=sys.stderr)
    sys.exit(1)

JAR = Path(r"E:\Mod\百科-语料\jar-analyze\baby")
OUT = Path(r"E:\Mod\百科-语料\jar-analyze\baby-物品导入-10394.json")
HTML_DIR = Path(r"E:\Mod\百科-语料\jar-analyze\baby-物品正文")
NS = "babydelight"
CATEGORY_FOOD = "食物"
CATEGORY_BLOCK = "装饰方块"
REMARK = "Baby Delight 1.0.2 新增（Minecraft 1.19.2）；内容依据 jar 内的 lang、配方与反编译结果整理"

# 5 个物品：(注册id, 图标相对路径, 分类, 堆叠)
ITEMS = [
    ("kelp_salad",         "textures/items/kelp_salad.png",         CATEGORY_FOOD,  64),
    ("ranchu_soup",        "textures/items/ranchu_soup.png",        CATEGORY_FOOD,  1),
    ("river_coleslav",     "textures/items/river_coleslaw.png",     CATEGORY_FOOD,  64),
    ("goldfish_fried_rice","textures/items/goldfish_fried_rice.png",CATEGORY_FOOD,  64),
    ("water_lettuce_crate","textures/blocks/water_lettuce_crate_top.png", CATEGORY_BLOCK, 64),
]


def b64_png(path: Path, size: int = 32) -> str:
    img = Image.open(path).convert("RGBA")
    buf = io.BytesIO()
    img.resize((size, size), Image.NEAREST).save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def b64_iso_64(top: Path, side: Path, size: int = 32) -> str:
    """方块：渲染等轴测立体图标（skill §图标规范第 2 条）。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "iso", Path(__file__).parent / "render-block-iso.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    img = m.render_iso(Image.open(top).convert("RGBA"), Image.open(side).convert("RGBA"), 512)
    img = m.fit(img, size)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def main() -> int:
    assets = JAR / "assets" / NS
    zh = json.loads((assets / "lang" / "zh_cn.json").read_text(encoding="utf-8"))
    en = json.loads((assets / "lang" / "en_us.json").read_text(encoding="utf-8"))
    HTML_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    missing = []
    for item_id, tex, cat, stack in ITEMS:
        zi = zh.get(f"item.{NS}.{item_id}") or zh.get(f"block.{NS}.{item_id}") or ""
        ei = en.get(f"item.{NS}.{item_id}") or en.get(f"block.{NS}.{item_id}") or ""
        # zh_cn.json 缺 goldfish_fried_rice，按 en_us 译名补
        if not zi and item_id == "goldfish_fried_rice":
            zi = "金鱼炒饭"
        if not zi:
            missing.append(item_id)

        html = ""
        hp = HTML_DIR / f"{item_id}.html"
        if hp.exists():
            html = hp.read_text(encoding="utf-8").strip()

        tex_path = assets / tex
        if not tex_path.exists():
            print(f"⚠ 缺纹理：{tex_path}", file=sys.stderr)
            icon = ""
        elif cat == CATEGORY_BLOCK:
            # 方块：用 top+side 渲染等轴测立体图标
            side_path = assets / f"textures/blocks/{item_id}_side.png"
            icon = b64_iso_64(tex_path, side_path)
        else:
            icon = b64_png(tex_path)

        rows.append({
            "id": item_id,
            "name": zi,
            "ename": ei,
            "regname": f"{NS}:{item_id}",
            "category": cat,
            "type": "物品/方块",
            "maxstack": stack,
            "remark": REMARK,
            "html": html,
            "icon32": icon,
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
    for r in rows:
        print(f"  {r['regname']:<32} {r['name']:<10} {r['ename']:<22} "
              f"[{r['category']}] 正文 {len(r['html'])} 字符 图标 {len(r['icon32'])} 字符")
    if missing:
        print(f"⚠ lang 里查不到中文名：{missing}")
    if any(not r["html"] for r in rows):
        print(f"⚠ 有 {sum(1 for r in rows if not r['html'])} 条正文为空")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
