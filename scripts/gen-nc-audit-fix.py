#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nemo's Carpentry（31737）审核中条目的错误修正 —— 用 verifyId 重提。

只包含审计发现、需要修正的条目（介绍页用户已自行再编辑，不在其中）：
  819419  座椅        通用文本：漏原木座椅 9 种、菌柄座椅 2 种
  819420  木工设备     通用文本：梯子写成「两种」，实际 12 种；工作台配方错
  819429  Oak Chair "Felix"           背高写「更高」，实测仍为 16
  819430  Oak Chair "Gregory"         写「有扶手」，实测无扶手
  819431  Oak Chair "Lukas"           背板形态
  819432  Oak Chair "Lukas" - Natural
  819434  Oak Chair "Tommy"           原描述与 Lukas 完全相同
  819436  Oak Chair "Tommy" - Natural

审核中条目没有资料 id，走再编辑路径 /item/add/<classId>-<verifyId>/，
数据格式是「新增」+ verifyId，且要带完整字段（不是编辑的 5 字段）。
"""
import json
import random
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
A = json.loads((BASE / "nc-代表页-31737.json").read_text(encoding="utf-8"))
C = json.loads((BASE / "nc-通用文本-31737.json").read_text(encoding="utf-8"))
OUT = BASE / "nc-修正-审核中-31737.json"

_PAW = ["呜喵", "喵呜", "喵喵"]

# verifyId → 数据来源
TARGETS = [
    (819419, "common", "common_seat"),
    (819420, "common", "common_carpentry"),
    (819429, "item", "block_oak_chair_felix"),
    (819430, "item", "block_oak_chair_gregory"),
    (819431, "item", "block_oak_chair_lukas"),
    (819432, "item", "block_oak_chair_lukas_natural"),
    (819434, "item", "block_oak_chair_tommy"),
    (819436, "item", "block_oak_chair_tommy_natural"),
]

# 每条改了什么（写进 editNote 性质的说明，这里走 remark）
WHY = {
    819419: "补上原木座椅与菌柄座椅，款式说明改完整",
    819420: "梯子数量改为十二种、工作台配方改为两个工作台加四块木板",
    819429: "靠背高度按模型实测改为 16 格，说明其为竖条背板",
    819430: "删去「扶手」的错误描述，改为双层靠背、背高 23 格",
    819431: "背板形态改为竖条结构",
    819432: "同上，Natural 版描述同步",
    819434: "原来与 Lukas 描述重复，改为整块实心背板",
    819436: "同上，Natural 版描述同步",
}


def tail() -> str:
    n = random.choice([1, 1, 2, 3])
    s = "".join(random.choice(_PAW) for _ in range(n))
    if random.random() < 0.03:
        s = "喵娘"
    return f"辛苦{s}机了"


def main() -> int:
    a_by_id = {r["id"]: r for r in A}
    c_by_id = {r["id"]: r for r in C}

    rows = []
    for vid, kind, key in TARGETS:
        src = c_by_id.get(key) if kind == "common" else a_by_id.get(key)
        if not src:
            print(f"  ✗ 找不到 {key}")
            continue
        rows.append({
            "kind": "新增",
            "verifyId": vid,
            "name": src["name"],
            "ename": src["ename"],
            "regname": src["regname"],
            "category": src["category"],
            "type": src["type"],
            "maxstack": src["maxstack"],
            "html": src["html"],
            "icon32": src["icon32"],
            "icon128": src["icon128"],
            "remark": (
                "Nemo's Carpentry 资料页修正："
                f"{WHY[vid]}。名称取自 lang/en_us.json（模组无中文语言文件）。"
                + tail()
            ),
        })

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"生成 {len(rows)} 条 → {OUT.name}  ({OUT.stat().st_size/1024:.1f} KB)\n")
    for r in rows:
        print(f"  {r['verifyId']}  {r['name']:<34} {len(r['html']):>4} 字符  icon={'有' if r['icon32'] else '无'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
