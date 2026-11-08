#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全站模组质量普查：找出需要修复的页面，输出可执行的作业清单。

检测项
------
1. **内容严重不足**：正文 <100 字
2. **内容偏少**：100–300 字
3. **无分节**：正文 ≥300 字但没有任何小标题（[hN]），结构不规范
4. **AI 味过重**：ai-tell-check 评分 <70（套话/排比/升华/空洞形容词）
5. **格式问题**：表格缺 th、markdown 残留、标题跨级或不是从 h1 起
6. **纯图片**：正文 <150 字但图片 ≥3 张（内容都在图里，搜不到、不可复制）
7. **截断可疑**：正文以"…"或半句结尾

输出
----
    audit-report.md      汇总报告（按问题类型分组，含 Top 清单）
    audit-problems.jsonl 每条问题一行：{id,name,url,kind,detail,score,suggestion}

用法
----
    python audit-site.py                       # 全库
    python audit-site.py --ids-file fav.txt    # 只查收藏夹
    python audit-site.py --min-chars 0         # 含极短页面
    python audit-site.py --top 50              # 每类列前 50
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_DATA = Path(r"E:\Mod\百科-语料")
SCRIPT_DIR = Path(__file__).parent
BASE_URL = "https://www.mcmod.cn/class/{}.html"

SEVERITY = {
    "empty": 5, "tiny": 4, "no-headings": 3, "ai-tell": 3,
    "format": 2, "image-only": 3, "truncated": 1, "short": 2,
}
KIND_LABEL = {
    "empty": "内容为空/极短（<100字）",
    "short": "内容偏少（100–300字）",
    "no-headings": "无分节（缺 [hN] 标题结构）",
    "ai-tell": "AI 味过重",
    "format": "格式问题",
    "image-only": "纯图片（正文极短但图多）",
    "truncated": "疑似截断",
}
SUGGEST = {
    "empty": "补充基础介绍：是什么、加什么内容、怎么获取",
    "short": "补充玩法细节与数值，或合并到相近条目",
    "no-headings": "按「概述 / 内容 / 获取方式」补 [h1=]/[h2=] 分节",
    "ai-tell": "删套话、排比与升华句，改写成陈述句并保留全部数值",
    "format": "修正表格 th、清理 markdown 残留、标题从 h1 起",
    "image-only": "把图片里的信息写成正文文字",
    "truncated": "检查是否编辑时被截断，补全结尾",
}


def load_checker():
    spec = importlib.util.spec_from_file_location("chk", SCRIPT_DIR / "ai-tell-check.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    ap.add_argument("--ids-file", default="")
    ap.add_argument("--min-chars", type=int, default=0, help="只检查字数 ≥ 该值的页面")
    ap.add_argument("--top", type=int, default=30, help="每类列出前 N 条")
    ap.add_argument("--out", default=str(DEFAULT_DATA / "audit"))
    args = ap.parse_args()

    chk = load_checker()
    data = Path(args.data)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(f"file:{data/'mcmod.db'}?mode=ro", uri=True, timeout=5)
    con.row_factory = sqlite3.Row

    sql = ("SELECT id,name,chars,n_headings,n_tables,n_imgs,intro_html,intro_text "
           "FROM classes WHERE chars IS NOT NULL")
    params: tuple = ()
    if args.ids_file:
        ids = [int(x) for x in re.findall(r"\d+", Path(args.ids_file).read_text(encoding="utf-8"))]
        sql += f" AND id IN ({','.join('?'*len(ids))})"
        params = tuple(ids)
    if args.min_chars:
        sql += " AND chars >= ?"
        params = params + (args.min_chars,)

    rows = list(con.execute(sql, params))
    con.close()
    print(f"检查 {len(rows)} 条页面")

    problems: list[dict] = []
    counter: Counter = Counter()
    by_kind: dict[str, list[dict]] = defaultdict(list)

    for r in rows:
        cid = r["id"]
        name = r["name"] or ""
        chars = r["chars"] or 0
        nh = r["n_headings"] or 0
        nimg = r["n_imgs"] or 0
        body = r["intro_text"] or ""
        html = r["intro_html"] or ""
        url = BASE_URL.format(cid)

        def emit(kind: str, detail: str, score: int | None = None):
            counter[kind] += 1
            item = {"id": cid, "name": name, "url": url, "kind": kind,
                    "detail": detail, "score": score,
                    "chars": chars, "severity": SEVERITY.get(kind, 1),
                    "suggestion": SUGGEST[kind]}
            problems.append(item)
            by_kind[kind].append(item)

        # 1/2. 内容量
        if chars < 100:
            emit("empty", f"{chars} 字")
            continue
        if chars < 300:
            emit("short", f"{chars} 字")

        # 3. 无分节（内容够多却没结构）
        if chars >= 300 and nh == 0:
            emit("no-headings", f"{chars} 字、0 个小标题")

        # 4. AI 味
        res = chk.check(html or body)
        if res["score"] < 70:
            kinds = "、".join(i["kind"] for i in res["issues"][:3])
            emit("ai-tell", f"评分 {res['score']}：{kinds}", res["score"])

        # 5. 格式
        fmt = []
        if re.search(r"(?m)^\s*#{1,6}\s", html) or re.search(r"\*\*[^*\n]{2,40}\*\*", html):
            fmt.append("markdown 残留")
        heads = [int(m.group(1)) for m in re.finditer(r"<h([1-6])[^>]*>", html, re.I)]
        if heads:
            if heads[0] != 1:
                fmt.append(f"首个标题是 h{heads[0]}")
            for a, b in zip(heads, heads[1:]):
                if b - a > 1:
                    fmt.append(f"跨级 h{a}→h{b}")
                    break
        if fmt:
            emit("format", "；".join(dict.fromkeys(fmt)))

        # 6. 纯图片
        if chars < 150 and nimg >= 3:
            emit("image-only", f"{chars} 字 + {nimg} 张图")

        # 7. 截断
        tail = body.rstrip()[-30:]
        if tail.endswith("…") or tail.endswith("...") or re.search(r"[，、：；]$", tail):
            emit("truncated", f"结尾：{tail[-16:]!r}")

    # 排序：严重度高、字数少的优先
    problems.sort(key=lambda x: (-x["severity"], x["chars"]))

    jl = out_dir / "audit-problems.jsonl"
    with jl.open("w", encoding="utf-8") as f:
        for p in problems:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    # 报告
    total = len(rows)
    md = [f"# 全站模组质量普查报告\n",
          f"- 检查页面：**{total}** 条",
          f"- 问题记录：**{len(problems)}** 条（同一页面可能命中多项）",
          f"- 有问题页面：**{len({p['id'] for p in problems})}** 条\n",
          "## 问题分布\n",
          "| 问题类型 | 页数 | 占比 | 严重度 |", "|---|---|---|---|"]
    for kind, n in counter.most_common():
        md.append(f"| {KIND_LABEL.get(kind, kind)} | {n} | {n/total*100:.1f}% | "
                  f"{'★'*SEVERITY.get(kind,1)} |")

    md.append("\n## 各类型清单（前 {} 条）\n".format(args.top))
    for kind, _ in counter.most_common():
        items = by_kind[kind][: args.top]
        md.append(f"\n### {KIND_LABEL.get(kind, kind)}（共 {counter[kind]} 条）\n")
        md.append("| id | 名称 | 字数 | 详情 | 链接 |")
        md.append("|---|---|---|---|---|")
        for it in items:
            md.append(f"| {it['id']} | {(it['name'] or '')[:20]} | {it['chars']} | "
                      f"{it['detail'][:36]} | [打开]({it['url']}) |")
        md.append(f"\n**建议**：{SUGGEST[kind]}\n")

    md.append("\n---\n*由 audit-site.py 生成，完整清单见 audit-problems.jsonl*")
    rp = out_dir / "audit-report.md"
    rp.write_text("\n".join(md), encoding="utf-8")

    print(f"\n问题分布：")
    for kind, n in counter.most_common():
        print(f"  {KIND_LABEL.get(kind, kind):<26} {n:>6}")
    print(f"\n输出：")
    print(f"  {rp}  ({rp.stat().st_size/1024:.0f} KB)")
    print(f"  {jl}  ({jl.stat().st_size/1024/1024:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
