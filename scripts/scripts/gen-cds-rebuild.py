#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Crafting Dead: Survival（classId 4397）重建物品页 —— 修正 ename 格式。

重建原因（用户要求）：
  之前的 ename 是「小写 + 下划线」的注册名风格（water_bottle），
  应该改成「首字母大写 + 去下划线」的标题格式（Water Bottle）。

不重建：刷怪蛋 15 条、实体 14 条（用户明确说不用重提）。

重建范围：食物 70 + 工具 5 = 75 条。

图标：
  icon32  —— 原纹理 32×32 直接用；64×64 的用 LANCZOS 缩小
  icon128 —— 原纹理 NEAREST 放大到 128（放大必须 NEAREST，避免模糊）
"""
import base64
import io
import json
import random
from pathlib import Path

from PIL import Image

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
TEX = BASE / "cds"
OUT_FOOD = BASE / "cds-重建-食物-4397.json"
OUT_TOOL = BASE / "cds-重建-工具-4397.json"

_PAW = ["呜喵", "喵呜", "喵喵"]


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def title_case(ename: str) -> str:
    """water_bottle → Water Bottle"""
    return " ".join(w.capitalize() for w in ename.split("_") if w)


def b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def icons(tex_path: Path):
    """返回 (icon32, icon128)。"""
    if not tex_path.exists():
        return "", ""
    src = Image.open(tex_path).convert("RGBA")
    # icon32：缩小用 LANCZOS，原图就是 32 的直接用
    if src.size == (32, 32):
        i32 = src
    elif src.width > 32:
        i32 = src.resize((32, 32), Image.LANCZOS)
    else:
        i32 = src.resize((32, 32), Image.NEAREST)
    # icon128：放大用 NEAREST
    if src.size == (128, 128):
        i128 = src
    elif src.width < 128:
        i128 = src.resize((128, 128), Image.NEAREST)
    else:
        i128 = src.resize((128, 128), Image.LANCZOS)
    return b64(i32), b64(i128)


def main() -> int:
    tex_map = {p.stem: p for p in TEX.rglob("textures/item/*.png")}
    print(f"纹理库 {len(tex_map)} 张\n")

    total_fixed = 0
    for src_file, out_file, label in [
        ("cds-新增食物-4397.json", OUT_FOOD, "食物"),
        ("cds-新增工具-4397.json", OUT_TOOL, "工具"),
    ]:
        rows = json.loads((BASE / src_file).read_text(encoding="utf-8"))
        out = []

        for r in rows:
            rid = r["regname"].split(":")[-1]
            old_ename = r["ename"]
            new_ename = title_case(old_ename)
            if old_ename != new_ename:
                total_fixed += 1

            icon32, icon128 = icons(tex_map.get(rid))

            out.append({
                "id": r["id"],
                "name": r["name"],
                "ename": new_ename,
                "regname": r["regname"],
                "category": r["category"],
                "type": r["type"],
                "maxstack": r["maxstack"],
                "remark": (
                    "Crafting Dead: Survival 资料页重建：中文名取自 lang/zh_cn.json，"
                    "次要名称改为首字母大写、去下划线的形式（原为注册名写法）。"
                    f"{tail()}"
                ),
                "html": r["html"],
                "icon32": icon32,
                "icon128": icon128,
            })

        out_file.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{label}：{len(out)} 条 → {out_file.name}  ({out_file.stat().st_size/1024:.1f} KB)")

        # 抽样对比
        for r in out[:3]:
            print(f"    {r['name']:<12} ename: {r['ename']}")
        noicon = [r["name"] for r in out if not r["icon32"] or not r["icon128"]]
        print(f"    缺图标: {len(noicon)}" + (f" {noicon[:3]}" if noicon else " ✓"))
        print()

    print(f"ename 修正合计 {total_fixed} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
