#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""meowarchive_io.py — 读喵呜档案导出机的产物，抹平字段大小写差异

为什么需要它：meowarchive 为了兼容 LMS，items 与 entities 的字段名大小写不同——

    items:    englishName(小写e)  smallIcon   largeIcon   maxStacksSize   maxDurability
    entities: Englishname(大写E)  Icon        IconSmall   --              --
    effects:  Englishname         Icon        IconSmall   category

直接 .get("Englishname") 读 items 会静默拿空串。本模块统一成一套键：

    regname  name  ename  kind  icon32  icon128  maxstack  durability  category
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

SUFFIX = {"item": "_items.json", "entity": "_entities.json", "effect": "_effects.json"}


def _read_jsonl(p: Path) -> list[dict[str, Any]]:
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _first(d: dict[str, Any], *keys: str, default: Any = "") -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


def norm_item(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "regname": _first(r, "registerName", "regname"),
        "name": _first(r, "name"),
        "ename": _first(r, "englishName", "Englishname"),
        "kind": "item",
        "icon32": _first(r, "smallIcon", "IconSmall"),
        "icon128": _first(r, "largeIcon", "Icon"),
        "maxstack": r.get("maxStacksSize", r.get("maxstack")),
        "durability": r.get("maxDurability", r.get("durability")),
        "type": _first(r, "type"),
        "raw": r,
    }


def norm_entity(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "regname": _first(r, "registerName", "regname"),
        "name": _first(r, "name"),
        "ename": _first(r, "Englishname", "englishName"),
        "kind": "entity",
        "icon32": _first(r, "IconSmall", "smallIcon"),
        "icon128": _first(r, "Icon", "largeIcon"),
        "noVisual": bool(r.get("noVisual")),
        "suspect": bool(r.get("suspect")),
        "suspectReason": _first(r, "suspectReason"),
        "renderer": _first(r, "renderer"),
        "raw": r,
    }


def norm_effect(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "regname": _first(r, "registerName", "regname"),
        "name": _first(r, "name"),
        "ename": _first(r, "Englishname", "englishName"),
        "kind": "effect",
        "icon32": _first(r, "IconSmall", "smallIcon"),
        "icon128": _first(r, "Icon", "largeIcon"),
        "category": _first(r, "category"),
        "effectCategory": _first(r, "effectCategory"),
        "raw": r,
    }


NORMALIZERS = {"item": norm_item, "entity": norm_entity, "effect": norm_effect}


def load_export(path: str | Path) -> dict[str, list[dict[str, Any]]]:
    """读一个导出目录（或单个 _all.json / 单个分文件），返回 {items, entities, effects}。

    优先用 `<ns>_all.json`（带 kind，一次读完）；没有则回落到三个分文件。
    目录里可以有多个命名空间，会被合并。
    """
    p = Path(path)
    out: dict[str, list[dict[str, Any]]] = {"items": [], "entities": [], "effects": []}
    if not p.exists():
        raise FileNotFoundError(p)

    if p.is_file():
        files = [p]
    else:
        files = sorted(p.rglob("*_all.json"))
        if not files:
            files = sorted([q for q in p.rglob("*.json")
                            if any(q.name.endswith(s) for s in SUFFIX.values())])

    for f in files:
        for r in _read_jsonl(f):
            kind = r.get("kind")
            if not kind:
                name = f.name
                kind = ("item" if name.endswith(SUFFIX["item"])
                        else "entity" if name.endswith(SUFFIX["entity"])
                        else "effect" if name.endswith(SUFFIX["effect"]) else "")
            fn = NORMALIZERS.get(kind)
            if fn:
                out[{"item": "items", "entity": "entities", "effect": "effects"}[kind]].append(fn(r))
    return out


def stats(data: dict[str, list[dict[str, Any]]]) -> str:
    lines = []
    for key, rows in data.items():
        empty32 = sum(1 for r in rows if not r.get("icon32"))
        empty128 = sum(1 for r in rows if not r.get("icon128"))
        noreg = sum(1 for r in rows if not r.get("regname"))
        lines.append(f"{key:<9} {len(rows):>4} 条 · 缺 icon32 {empty32} · 缺 icon128 {empty128} · 缺 regname {noreg}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python meowarchive_io.py <导出目录|_all.json>")
        raise SystemExit(2)
    d = load_export(sys.argv[1])
    print(stats(d))
    for k in ("items", "entities", "effects"):
        if d[k]:
            r = d[k][0]
            print(f"\n{k} 样例：{r['regname']} | {r['name']} | {r['ename']} | "
                  f"icon32 {'有' if r['icon32'] else '空'} / icon128 {'有' if r['icon128'] else '空'}")
