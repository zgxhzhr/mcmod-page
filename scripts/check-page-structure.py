#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mcmod 页面结构自检 —— 提交前跑一遍。

检查项：
  1. 标题层级跨级（首个标题必须是 h1；不能从 h2 起）
  2. 百科不支持的标签（<code> <blockquote> <hr>）
  3. 标签闭合平衡
  4. <h2> 这类 HTML 标题写成 [h1=] 方括号标记
  5. [ban:title_menu] 与标题的关系

用法：
  python check-page-structure.py 文件.html
  python check-page-structure.py 文件.html --kind page     # 模组页
  python check-page-structure.py 文件.html --kind item     # 资料页
"""
import argparse
import re
import sys
from pathlib import Path

BAD_TAGS = ["<code", "<blockquote", "<hr"]
PAIR_TAGS = ["p", "table", "tbody", "thead", "tr", "td", "th", "ul", "li", "strong", "span", "div"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--kind", default="page", choices=["page", "item", "tutorial"])
    args = ap.parse_args()

    p = Path(args.path)
    if not p.exists():
        print(f"文件不存在：{p}")
        return 1
    t = p.read_text(encoding="utf-8")

    problems = []
    warns = []

    # 1. 标题层级
    heads = [(int(m.group(1)), m.group(2)) for m in re.finditer(r"\[h([1-6])=([^\]]+)\]", t)]
    if heads:
        if heads[0][0] != 1:
            problems.append(
                f"跨级标题：首个标题是 h{heads[0][0]}「{heads[0][1]}」，必须从 h1 起。"
                "资料页没有原文 h1 → 自己补充的也要用 h1；"
                "若整页不需要目录，索性不加标题。"
            )
        for i in range(1, len(heads)):
            prev, cur = heads[i - 1][0], heads[i][0]
            if cur > prev + 1:
                problems.append(f"跨级标题：「{heads[i][1]}」是 h{cur}，上一级是 h{prev}")
        print(f"标题：{len(heads)} 个 → " + " / ".join(f"h{l}:{n}" for l, n in heads))
    else:
        print("标题：无")

    # 2. 不支持的标签
    for tag in BAD_TAGS:
        if tag in t:
            problems.append(f"百科不支持的标签：{tag}>")

    # 3. HTML 标题标签
    for m in re.finditer(r"<h([1-6])>", t):
        problems.append(f"用了 HTML 标题 <h{m.group(1)}>，应写成 [h{m.group(1)}=标题]")

    # 4. 标签平衡
    for tag in PAIR_TAGS:
        op = len(re.findall(rf"<{tag}[\s>]", t))
        cl = len(re.findall(rf"</{tag}>", t))
        if op != cl:
            problems.append(f"标签不平衡：<{tag}> {op} 个，</{tag}> {cl} 个")

    # 4.5 列表标点（审核附言 2026-11-14：各项「；」，末项「。」）
    lis = re.findall(r"<li[^>]*>(.*?)</li>", t, re.S)
    if lis:
        for i, inner in enumerate(lis, 1):
            plain_li = re.sub(r"<[^>]+>", "", inner).strip()
            if not plain_li:
                continue
            last = plain_li[-1]
            is_last_item = (i == len(lis))
            if is_last_item and last != "。":
                problems.append(
                    f"列表末项应以「。」结尾，实际是「{last}」：{plain_li[:24]}…"
                    "（rules/01 §2.1.2）")
            elif not is_last_item and last != "；":
                problems.append(
                    f"列表非末项应以「；」结尾，实际是「{last}」：{plain_li[:24]}…"
                    "（rules/01 §2.1.2）")

    # 5. ban 与标题
    has_ban = "[ban:title_menu]" in t
    if heads and has_ban:
        warns.append("有标题又禁用了标题栏（[ban:title_menu]）——目录会消失，确认是有意的")
    if not heads and not has_ban:
        warns.append("既没有标题也没禁用标题栏——目录为空，通常应该加 [ban:title_menu]")

    # 6. 空段落
    if re.search(r"<p>\s*</p>", t):
        warns.append("存在空段落 <p></p>")

    # 输出
    print(f"字数：{len(re.sub(r'<[^>]+>|\[[^\]]+\]|\s', '', t))}")
    print()
    if problems:
        print(f"结构异常 {len(problems)} 项：")
        for x in problems:
            print(f"  ✗ {x}")
    else:
        print("结构：✓ 正常")
    if warns:
        print(f"\n提醒 {len(warns)} 项：")
        for x in warns:
            print(f"  · {x}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
