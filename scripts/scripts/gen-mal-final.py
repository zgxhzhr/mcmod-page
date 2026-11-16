#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Malstone Mod（26143）最终定稿 —— 不要通用文本，不写配方明细。

用户决定：
  1. 不建通用文本，19 条各自独立；
  2. 正文只写「在哪里制作」，具体配方不列；
  3. 通用文本那几段（佩戴方式、材料命名）也不写进物品页。

合成地点从 data/malum/recipes 读出：17 件走灵魂灌注，2 件走符文制作。
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


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def where_made(rid: str) -> str:
    """只返回制作地点，不列配方。"""
    if (RECIPES / "spirit_infusion" / f"{rid}.json").exists():
        return "灵灾的灵魂灌注"
    if (RECIPES / "runeworking" / f"{rid}.json").exists():
        return "灵灾的符文制作"
    return ""


def main() -> int:
    rows = json.loads(SRC.read_text(encoding="utf-8"))

    for r in rows:
        # 去掉上一轮加的配方段
        import re
        r["html"] = re.sub(r"<p><strong>合成</strong>.*?</p>", "", r["html"])

        place = where_made(r["id"])
        if place:
            r["html"] += f"<p><strong>制作</strong>：在{place}中制作。</p>"

        r["remark"] = (
            f"Malstone Mod 资料页：名称取自 lang/zh_cn.json 的 item.malstone.{r['id']} 条目，"
            f"英文名取自 en_us.json，品质取自 ItemRegs 中 Item.Properties 的 Rarity 设定，"
            f"效果取自 lang 下的 .text 子项，属性加成取自各物品类 getAttributeModifiers，"
            f"制作地点取自 data/malum/recipes 下的配方文件。"
            f"{tail()}"
        )

    OUT_ITEMS.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    # 删掉通用文本
    if OUT_COMMON.exists():
        OUT_COMMON.unlink()
        print(f"已删除 {OUT_COMMON.name}")

    print(f"物品页 {len(rows)} 条 → {OUT_ITEMS.name}")
    print(f"正文长度 {min(len(r['html']) for r in rows)}~{max(len(r['html']) for r in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
