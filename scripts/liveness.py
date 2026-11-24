#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""liveness.py — 判断哪些类真的被注册/引用（活代码），哪些是死代码

作者反馈：「AI 肯定读取了很多死代码和注释，全部都有问题」。
闸门需要区分：某个常量所在的类，到底有没有被注册表或入口引用到。

做法（类级可达性，够用且快）：
  1. 解析所有 .java：类名、父类、正文里的"其他类名"引用
  2. 入口根集合：ModEntities/ModItems/ModBlocks 等注册类 + 主类 + @EventBusSubscriber/@Mod 类
  3. 从根做 BFS，得到 reachable 集合；其余为 dead
输出 JSON：{roots, live, dead, dead_count, live_count}

用法： python liveness.py --src <反编译目录> --out liveness.json
"""
import argparse
import json
import re
from pathlib import Path

CLASS_RE = re.compile(r"\b(?:class|interface|enum|record)\s+(\w+)")
EXT_RE = re.compile(r"\b(?:class|interface|enum|record)\s+\w+\s*(?:<[^>]*>)?\s*extends\s+([\w.]+)")
WORD_RE = re.compile(r"\b([A-Z][A-Za-z0-9_]{2,})\b")
ANNOT_RE = re.compile(r"@(EventBusSubscriber|Mod|SubscribeEvent|Mod\.EventBusSubscriber)")
REG_CALL = re.compile(r"(?:register|REGISTER|reg)\w*\([^)]{0,80}?([A-Z][A-Za-z0-9_]{2,})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", default="liveness.json")
    ap.add_argument("--entry", default="", help="逗号分隔的额外入口类名")
    a = ap.parse_args()

    src = Path(a.src)
    files = {}
    for p in src.rglob("*.java"):
        files[p.stem] = p.read_text(encoding="utf-8", errors="replace")
    all_names = set(files)

    # 引用图
    graph = {}
    for name, text in files.items():
        refs = {t for t in WORD_RE.findall(text) if t in all_names and t != name}
        graph[name] = refs

    # 根：注册类 + 主类 + 事件类 + 显式入口
    roots = set()
    for name, text in files.items():
        if re.search(r"ModEntities|ModItems|ModBlocks|ModSounds|ModTabs|ModAttachments", name):
            roots.add(name)
        if ANNOT_RE.search(text):
            roots.add(name)
        if re.search(r"register\w*\(", text) and re.search(r"Registry|EVENT_BUS|EventBus", text):
            roots.add(name)
    for e in [x.strip() for x in a.entry.split(",") if x.strip()]:
        if e in files:
            roots.add(e)

    # BFS
    live, stack = set(), list(roots)
    while stack:
        cur = stack.pop()
        if cur in live or cur not in files:
            continue
        live.add(cur)
        stack.extend(graph.get(cur, ()))

    dead = sorted(all_names - live)
    out = {"roots": sorted(roots), "live_count": len(live), "dead_count": len(dead),
           "live": sorted(live), "dead": dead}
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ {a.out}")
    print(f"  根 {len(roots)} · 活类 {len(live)} · 死类 {len(dead)}（{len(dead)*100//max(1,len(all_names))}%）")
    print("  死类示例:", ", ".join(dead[:12]))


if __name__ == "__main__":
    main()
