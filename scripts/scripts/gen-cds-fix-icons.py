#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按审核列表生成「补图标」的修正 JSON。

背景：批量脚本在有图标时没有取消「删除大小图标」勾选，导致已提交条目的小图标被删掉。
实体本来就不该有图标，所以只补物品。

输出格式对准 mcmod-batch.user.js 的落地页逻辑：
  { kind: '新增', verifyId, name, icon32, ... }  →  跳 /item/add/<classId>-<verifyId>/
"""
import json
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")
AUDIT = Path(r"C:\Users\MKIII\Downloads\mcmod-审核列表-2026-11-10T02-56-39 (1).json")
OUT = BASE / "cds-补图标-审核修正.json"

# 本次提交的三批数据，按中文名建索引
SOURCES = ["cds-新增食物-4397.json", "cds-新增工具-4397.json", "cds-新增刷怪蛋-4397.json"]

by_name = {}
for f in SOURCES:
    rows = json.loads((BASE / f).read_text(encoding="utf-8"))
    for r in rows:
        by_name[r["name"]] = r

audit = json.loads(AUDIT.read_text(encoding="utf-8-sig"))
print(f"审核列表 {audit['total']} 条")

fixed, skipped_entity, missing, withdrawn = [], [], [], []
for row in audit["rows"]:
    label = row["name"]                     # "空水壶 (empty_water_canteen)"
    name = label.split(" (")[0].strip()
    is_item = row["kindLabel"] == "物品/方块"
    status = row["status"]

    if not is_item:
        skipped_entity.append(name)
        continue
    if status == "已撤回":
        withdrawn.append(name)
        continue

    src = by_name.get(name)
    if not src or not src.get("icon32"):
        missing.append(name)
        continue

    # fillOne 会按 clearOrSet 清空所有未提供的字段，所以必须给全量字段，
    # 否则 ename / maxstack / html 会被清空。
    fixed.append({
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
        "remark": ("补齐小图标：上一条提交时为「删除大小图标」勾选状态，"
                   "导致图标被清除。本次内容与上一条一致，只补回图标。辛苦喵呜机了"),
    })

print(f"\n可补图标：{len(fixed)} 条")
print(f"实体（本就无图标，跳过）：{len(skipped_entity)} 条")
print(f"已撤回（跳过）：{len(withdrawn)} 条")
if missing:
    print(f"⚠ 数据里找不到对应图标：{len(missing)} 条 → {missing[:10]}")

OUT.write_text(json.dumps(fixed, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n已写出 {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
for r in fixed[:8]:
    print(f"  verifyId={r['verifyId']:<8} {r['name']:<20} 图标 {len(r['icon32'])} 字符")
if len(fixed) > 8:
    print(f"  …共 {len(fixed)} 条")
