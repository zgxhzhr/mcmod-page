#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复语料库里被重复收集的正文（从已存的 intro_html 就地重解析，不重新抓取）。

问题
----
原解析逻辑对 `node.iter()` 里所有 p/li/td/th 都取 text_content，
而 `<li><p>文字</p></li>` 这种结构会让同一段文字被 li 和 p 各收一次，
导致正文里每句话出现两遍 —— 直接影响训练数据质量。

修复
----
只收「叶子块」：p/h1-h4 直接取文本；li/td/th/div 若内部还有块级子元素则递归，
否则才取自身文本。同时按段去重（相邻重复段只保留一次）。

用法
----
    python repair-corpus.py                 # 默认只修收藏夹那批（推荐）
    python repair-corpus.py --all           # 修全库
    python repair-corpus.py --dry-run       # 只看会改什么，不写库
"""
from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path

from lxml import html as lhtml

DEFAULT_DATA = Path(r"E:\Mod\百科-语料")
BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "li", "td", "th", "div", "table", "tr", "ul", "ol", "pre"}
LEAF_TEXT_TAGS = {"p", "h1", "h2", "h3", "h4", "pre"}


def txt(node) -> str:
    if node.tag == "pre":
        # 代码块保留换行与缩进
        return (node.text_content() or "").strip()
    return " ".join((node.text_content() or "").split())


def extract_text(root) -> tuple[str, int]:
    """从正文容器里提取去重后的段落文本，返回 (text, n_paras)。"""
    parts: list[str] = []

    def has_block_child(el) -> bool:
        return any(isinstance(c.tag, str) and c.tag in BLOCK_TAGS for c in el)

    def walk(el):
        for c in el:
            if not isinstance(c.tag, str):
                continue
            if c.tag in LEAF_TEXT_TAGS:
                t = txt(c)
                if t:
                    parts.append(t)
            elif c.tag in ("li", "td", "th"):
                if has_block_child(c):
                    walk(c)
                else:
                    t = txt(c)
                    if t:
                        parts.append(t)
            else:
                walk(c)

    walk(root)

    # 相邻重复段去重（解析重复的典型表现）
    dedup: list[str] = []
    for p in parts:
        if dedup and p == dedup[-1]:
            continue
        # 整段是上一段的子串也视为重复
        if dedup and len(p) > 20 and p in dedup[-1]:
            continue
        dedup.append(p)

    n_paras = len(dedup)
    return "\n".join(dedup).strip(), n_paras


def parse_from_html(html_text: str) -> tuple[str, int, int, int, int]:
    """返回 (text, chars, n_paras, n_tables, n_imgs)。"""
    try:
        doc = lhtml.fromstring(html_text)
    except Exception:
        return "", 0, 0, 0, 0
    n_tables = len(doc.xpath(".//table"))
    n_imgs = len(doc.xpath(".//img"))
    text, n_paras = extract_text(doc)
    return text, len(re.sub(r"\s", "", text)), n_paras, n_tables, n_imgs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    ap.add_argument("--ids-file", default=str(DEFAULT_DATA / "favorites-full-ids.txt"),
                    help="默认只修收藏夹这批")
    ap.add_argument("--all", action="store_true", help="修全库")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = Path(args.data)
    con = sqlite3.connect(data / "mcmod.db")
    con.execute("PRAGMA journal_mode=WAL")

    if args.all:
        rows = list(con.execute(
            "SELECT id, intro_html, chars FROM classes WHERE intro_html <> ''"))
    else:
        ids = [int(x) for x in re.findall(r"\d+", Path(args.ids_file).read_text(encoding="utf-8"))]
        ph = ",".join("?" * len(ids))
        rows = list(con.execute(
            f"SELECT id, intro_html, chars FROM classes WHERE intro_html <> '' AND id IN ({ph})", ids))

    print(f"待处理 {len(rows)} 条")
    changed = same = shrunk = 0
    total_before = total_after = 0
    samples = []

    for cid, h, old_chars in rows:
        text, chars, n_paras, n_tables, n_imgs = parse_from_html(h or "")
        if not chars:
            same += 1
            continue
        total_before += old_chars or 0
        total_after += chars
        if chars == old_chars:
            same += 1
            continue
        changed += 1
        if chars < (old_chars or 0):
            shrunk += 1
            if len(samples) < 5:
                samples.append((cid, old_chars, chars))
        if not args.dry_run:
            con.execute(
                "UPDATE classes SET intro_text=?, chars=?, n_paras=?, n_tables=?, n_imgs=? WHERE id=?",
                (text, chars, n_paras, n_tables, n_imgs, cid))

    if not args.dry_run:
        con.commit()
    con.close()

    print(f"  改动 {changed} 条，未变 {same} 条（其中变短 {shrunk} 条）")
    if total_before:
        print(f"  总字数：{total_before:,} → {total_after:,}（{total_after/total_before*100:.1f}%）")
    for cid, a, b in samples:
        print(f"    例：id={cid} {a} → {b} 字")
    if args.dry_run:
        print("  （dry-run，未写库）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
