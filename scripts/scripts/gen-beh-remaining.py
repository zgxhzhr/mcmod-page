#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从审核列表里提取「已提交」的 Behgameon 条目，生成剩余待编辑的批次。

审核列表只返回最新的 100 条（跨多个模组），所以按 id 匹配现存的 177 个资料页，
命中即已提交，未命中的就是剩下的。
"""
import json
from pathlib import Path
from collections import Counter

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
FULL = BASE / "beh-编辑-5187.json"
AUDIT = Path(r"C:\Users\MKIII\Downloads\mcmod-审核列表-2026-11-10T05-59-18.json")
OUT = BASE / "beh-编辑-剩余.json"

rows = json.loads(FULL.read_text(encoding="utf-8"))
audit = json.loads(AUDIT.read_text(encoding="utf-8-sig"))

# 审核列表里属于 Behgameon 的：id 落在 535174-535350 区间
BEH_LO, BEH_HI = 535174, 535350
done_ids = set()
other = []
for r in audit["rows"]:
    rid = r.get("id")
    if rid is None:
        other.append(r["name"])
        continue
    try:
        rid_i = int(rid)
    except (TypeError, ValueError):
        other.append(r["name"])
        continue
    if BEH_LO <= rid_i <= BEH_HI:
        done_ids.add(str(rid_i))
    else:
        other.append(r["name"])

print(f"177 条中已提交（在审核列表里）：{len(done_ids)} 条")
print(f"审核列表里其它模组的条目：{len(other)} 条")

remaining = [r for r in rows if r["id"] not in done_ids]
print(f"\n剩余待编辑：{len(remaining)} 条")
print("按名称:", dict(Counter(r["name"] for r in remaining)))

# 已完成的分类统计
done_rows = [r for r in rows if r["id"] in done_ids]
print("\n已完成按名称:", dict(Counter(r["name"] for r in done_rows)))

OUT.write_text(json.dumps(remaining, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n已写出 {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")

# 列出剩余的 id 区间，便于核对顺序
ids = sorted(int(r["id"]) for r in remaining)
print(f"\n剩余 id 范围：{ids[0]} - {ids[-1]}")
# 找连续片段
runs = []
start = prev = ids[0]
for i in ids[1:]:
    if i == prev + 1:
        prev = i
    else:
        runs.append((start, prev))
        start = prev = i
runs.append((start, prev))
print(f"连续区间 {len(runs)} 段：")
for a, b in runs:
    print(f"  {a} - {b}  ({b - a + 1} 条)")
