#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 Markdown 草稿转成 mcmod 编辑器可直接粘贴的 HTML。

格式依据：本机已有交付样例（冰之核心-片段.html）
- 标题：[h1=标题]（mcmod 原生标记）
- 段落：<p>…</p>
- 列表：<ul class="list-paddingleft-2"><li><p>…</p></li></ul>
- 粗体：<strong>…</strong>
- 内联代码：<code>…</code>
- 斜体：<em>…</em>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def inline(s: str) -> str:
    """行内标记转换"""
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def convert(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for raw in lines:
        line = raw.rstrip()

        # 空行
        if not line.strip():
            close_list()
            continue

        # [h1=标题] 标题
        m = re.match(r"^\[h([1-4])=(.+?)\]$", line.strip())
        if m:
            close_list()
            out.append(f"[h{m.group(1)}={m.group(2)}]")
            continue

        # markdown 标题
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            close_list()
            lvl = len(m.group(1))
            out.append(f"[h{lvl}={m.group(2).strip()}]")
            continue

        # 列表项（* 或 - 开头）
        m = re.match(r"^\s*[*-]\s+(.*)$", line)
        if m:
            if not in_list:
                out.append('<ul class="list-paddingleft-2">')
                in_list = True
            out.append(f"  <li><p>{inline(m.group(1).strip())}</p></li>")
            continue

        # 普通段落
        close_list()
        out.append(f"<p>{inline(line.strip())}</p>")

    close_list()
    return "\n".join(out)


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        r"E:\Mod\百科-语料\jar-analyze\ue-介绍-草稿.md")
    md = src.read_text(encoding="utf-8")
    html = convert(md)
    dst = src.with_suffix(".html")
    dst.write_text(html, encoding="utf-8")
    print(f"已生成：{dst}")
    print(f"  原文 {len(md)} 字符 → HTML {len(html)} 字符")
    print(f"\n=== 前 30 行 ===\n")
    print("\n".join(html.splitlines()[:30]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
