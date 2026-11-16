#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tax' Village Architect（15261）自然生成页 —— 补注册名与原名。

退回理由：需要补充注册名/原名。

注册名来自 data/<ns>/worldgen/structure/ 下的结构定义文件：
  minecraft:village_plains / village_desert / village_savanna
  minecraft:village_snowy  / village_taiga
  vsrevamped:village_cherry
  minecraft:pillager_outpost（原版结构，模组只替换了模板）
  minecraft:village/common（模板池，不是独立结构）

模组自己的 lang 是空对象 {}，没有任何自定义名称，所以英文原名沿用原版：
原版五个村庄的英文名都是 "Village"，加了括号区分群系；樱花是 vsrevamped 的扩展。
"""
import json
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
SRC = BASE / "tva-自然生成-15261.json"
OUT = BASE / "tva-自然生成-15261.json"

# id → (注册名, 英文原名)
META = {
    "village_plains": ("minecraft:village_plains", "Village (Plains)"),
    "village_desert": ("minecraft:village_desert", "Village (Desert)"),
    "village_savanna": ("minecraft:village_savanna", "Village (Savanna)"),
    "village_snowy": ("minecraft:village_snowy", "Village (Snowy)"),
    "village_taiga": ("minecraft:village_taiga", "Village (Taiga)"),
    "village_cherry": ("vsrevamped:village_cherry", "Cherry Village"),
    "pillager_outpost": ("minecraft:pillager_outpost", "Pillager Outpost"),
    "common": ("minecraft:village/common", "Village (Common Parts)"),
}


def main() -> int:
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    miss = []
    for r in rows:
        meta = META.get(r["id"])
        if not meta:
            miss.append(r["id"])
            continue
        r["regname"], r["ename"] = meta
        # 自然生成无图标：两个字段都显式给空字符串
        r["icon32"] = ""
        r["icon128"] = ""
        # remark 里补一句注册名来源，便于审核核对
        if "注册名取自" not in r["remark"]:
            r["remark"] = r["remark"].replace(
                "新增自然生成页：",
                "新增自然生成页：注册名取自 data 下 worldgen/structure 的结构定义文件，",
            )

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"补完 {len(rows) - len(miss)} 条 → {OUT.name}")
    if miss:
        print(f"  未匹配: {miss}")
    print(f"\n{'名称':<14}{'ename':<26}{'regname'}")
    for r in rows:
        print(f"  {r['name']:<12}{r['ename']:<26}{r['regname']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
