#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按审核列表的当前进度，生成「剩余待处理」的补图标修正 JSON。

进度约定：审核列表倒序排列，index 41（变质的橙子）及之前已处理完毕。
本脚本取 index > 41 中「审核中 + 物品/方块」的条目。

已撤回的条目不处理（它们是旧版英文名提交，站点已作废）。
生物/实体不需要图标，跳过。
"""
import json
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
AUDIT = Path(r"C:\Users\MKIII\Downloads\mcmod-审核列表-2026-11-10T02-56-39 (1).json")
DONE_THROUGH_INDEX = 41          # 变质的橙子

SOURCES = ["cds-新增食物-4397.json", "cds-新增工具-4397.json", "cds-新增刷怪蛋-4397.json"]


def main() -> int:
    # 1) 源数据按中文名建索引
    by_name = {}
    for f in SOURCES:
        for r in json.loads((BASE / f).read_text(encoding="utf-8")):
            by_name[r["name"]] = r
            # 兼容审核列表里的英文名写法
            by_name.setdefault(r["ename"], r)

    # 2) 审核列表
    audit = json.loads(AUDIT.read_text(encoding="utf-8-sig"))
    rest = [r for r in audit["rows"] if r["index"] > DONE_THROUGH_INDEX]
    todo = [r for r in rest if r["status"] == "审核中" and r["kindLabel"] == "物品/方块"]

    items, missed = [], []
    for row in todo:
        name = row["name"].split(" (")[0].strip()
        src = by_name.get(name)
        if not src or not src.get("icon32"):
            missed.append(name)
            continue
        items.append({
            "kind": "新增",
            "verifyId": row["verifyId"],
            "name": src["name"],
            "ename": src["ename"],
            "regname": src["regname"],
            "category": src["category"],
            "type": src["type"],
            "maxstack": src["maxstack"],
            "html": src["html"],
            "icon32": src["icon32"],
            "remark": ("补齐小图标：上一条提交时为「删除大小图标」勾选状态，导致图标被清除。"
                       "本次内容与上一条一致，只补回图标。辛苦喵呜机了"),
        })

    out = {
        "classId": "4397",
        "typeId": "1",
        "total": len(items),
        "items": items,
    }
    p = BASE / "cds-补图标-剩余33条.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"审核列表 {audit['total']} 条，已处理 index ≤ {DONE_THROUGH_INDEX}")
    print(f"剩余 index > {DONE_THROUGH_INDEX}：{len(rest)} 条")
    print(f"  审核中·物品 {sum(1 for r in rest if r['status']=='审核中' and r['kindLabel']=='物品/方块')} 条")
    print(f"  审核中·实体 {sum(1 for r in rest if r['status']=='审核中' and r['kindLabel']=='生物/实体')} 条")
    print(f"  已撤回      {sum(1 for r in rest if r['status']=='已撤回')} 条（跳过）")
    print(f"\n生成 {len(items)} 条 → {p}  ({p.stat().st_size/1024:.0f} KB)")
    if missed:
        print(f"⚠ 数据里找不到：{missed}")
    for it in items[:5]:
        print(f"  verifyId={it['verifyId']}  {it['name']}")
    if len(items) > 5:
        print(f"  …共 {len(items)} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
