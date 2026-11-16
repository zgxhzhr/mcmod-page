#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按审核附言批量修 13 个模组介绍页的结构问题。

附言原文：
  统一回复喵：1.适当添加 h2 标题；2.画廊后置；
  3.（部分含有）对单个资料过于详细的介绍需要写到对应的物品里，模组正文仅需摘要

本脚本处理 1 和 2（第 3 点涉及内容判断，逐页人工处理）：
  - 第一个 h1 保留为主标题，其余 h1 降为 h2
  - 画廊块（标题 + 表格/图片）整体移到文末，标题仍用 h1
  - 字数 ≥600 或标题数 >3 时去掉 [ban:title_menu]（此前多半挂在文末，本来就不生效）
"""
import re
from pathlib import Path

BASE = Path(r"E:\Mod\百科-语料\jar-analyze")

FILES = [
    # 审核列表第 12~21 条（Bunny Boots → 挖矿与砍杀拓展）
    "bb-介绍-2674.html",        # 12 Bunny Boots
    "rex-介绍-24724.html",      # 13 Realistic Explosives
    "ts-介绍-646.html",         # 14 RP增强
    "wr-介绍-264.html",         # 15 无线红石
    "entherm-介绍-3976.html",   # 16 无中生有：传承 - 热力扩展
    "ee-介绍-4236.html",        # 17 环境科技-发电机
    "sb-介绍-17728.html",       # 18 Strange Berries
    "trp-介绍-3182.html",       # 19 群峦岩石
    "sdk-介绍-12913.html",      # 20 Self Damage Knife
    "mse-介绍-5180.html",       # 21 挖矿与砍杀拓展
]

HEAD = re.compile(r"<p>\[(h[12])=([^\]]+)\]</p>")


def extract_gallery(t: str):
    """切出画廊块：从画廊标题开始，直到下一个标题段落之前。"""
    m = re.search(r"<p>\[(h[12])=画廊\]</p>", t)
    if not m:
        return t, ""
    start = m.start()
    nxt = HEAD.search(t, m.end())
    end = nxt.start() if nxt else len(t)
    block = t[start:end].rstrip()
    rest = (t[:start] + t[end:]).rstrip()
    return rest, block


def demote(t: str) -> str:
    """第一个 h1 保留，其余 h1 → h2。"""
    seen = [False]

    def repl(m):
        if not seen[0]:
            seen[0] = True
            return m.group(0)
        return f"<p>[h2={m.group(2)}]</p>"

    return HEAD.sub(repl, t)


def strip_ban(t: str) -> str:
    return re.sub(r"<p>\[ban:title_menu\]</p>\s*", "", t)


def wc(t: str) -> int:
    b = re.sub(r"<[^>]+>", "", t)
    b = re.sub(r"\[[^\]]+\]", "", b)
    return len(b.strip())


def main() -> int:
    for f in FILES:
        p = BASE / f
        if not p.exists():
            print(f"跳过 {f}（不存在）")
            continue
        t0 = p.read_text(encoding="utf-8")

        t, gallery = extract_gallery(t0)
        t = demote(t)
        t = strip_ban(t)

        if gallery:
            # 画廊标题统一为 h1，块接到文末
            g = re.sub(r"<p>\[h[12]=画廊\]</p>", "<p>[h1=画廊]</p>", gallery, count=1)
            t = t.rstrip() + "\n" + g + "\n"
        else:
            t = t.rstrip() + "\n"

        p.write_text(t, encoding="utf-8")

        h1 = re.findall(r"\[h1=([^\]]+)\]", t)
        h2 = re.findall(r"\[h2=([^\]]+)\]", t)
        print(f"✓ {f}")
        print(f"    h1 {h1}   h2 {len(h2)} 个   字数 {wc(t)}   画廊 {'有' if gallery else '无'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
