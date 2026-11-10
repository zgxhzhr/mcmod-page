#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三维扫描：AI 腔 + 空洞 + 格式，尽量多揪出问题页面。

三个维度独立打标签，一个页面可以同时命中多项。

用法
----
    python scan-all.py                    # 全库规则扫描（快，秒级）
    python scan-all.py --with-llm         # 加上 LLM 空洞判断（慢，需 API）
    python scan-all.py --ids-file fav.txt # 只扫指定范围

输出
----
    scan/scan-report.md        分类清单（可直接当作业表）
    scan/scan-problems.jsonl   每条问题一行
    scan/scan-summary.json     统计
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path(r"E:\Mod\百科-语料")

# ── 格式类（确定性最高）──────────────────────────────────
EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]")
STACKED = re.compile(r"[！？]{2,}|[。]{3,}")
DIVIDER = re.compile(r"[-=_*~]{8,}|[━─═]{4,}|[\\/]{6,}|[·•◆◇■□▲△●○]{4,}")
MD_RESIDUE = re.compile(r"(?m)^\s*#{1,6}\s|\*\*[^*\n]{2,40}\*\*|`{3}")
PS_SUFFIX = re.compile(r"(?m)^\s*(PS[:：.]|PSS[:：.]|注[:：]|附[:：])")

# ── AI 腔类（统计特征）──────────────────────────────────
ABSTRACT = ["节奏", "决策", "体验", "感受", "意义", "价值", "精髓", "灵魂",
            "氛围", "张力", "沉浸", "代入", "维度", "层面", "闭环", "生态",
            "节奏感", "层次感", "仪式感", "沉浸感", "代入感"]
# 有些抽象词用在正常句子里不算问题，这里只取密度异常
UNIT_NUM = re.compile(r"\d+(?:\.\d+)?\s*(?:tick|t|秒|分钟|小时|天|格|点|%|倍|个|级|件|次|层|颗|块|种|条)")
# 具体名词线索：引号内容、英文词、括号内容
QUOTED = re.compile(r"[「『\"\"]([^」』\"\"]{2,20})[」』\"\"]")
EN_WORD = re.compile(r"\b[A-Za-z][A-Za-z0-9_\-]{2,}\b")


def plain_text(html: str, text: str) -> str:
    return text or re.sub(r"<[^>]+>", " ", html or "")


def scan_row(cid, name, chars, n_headings, n_imgs, html, text) -> list[dict]:
    issues = []
    body = plain_text(html, text)
    n_chars = max(len(re.sub(r"\s", "", body)), 1)

    def add(kind: str, detail: str):
        issues.append({"id": cid, "name": name, "kind": kind,
                       "detail": detail, "chars": chars})

    # ── 1. 格式 ──
    em = len(EMOJI.findall(body))
    if em >= 1:
        add("格式·emoji", f"{em} 个")
    st = len(STACKED.findall(body))
    if st >= 2:
        add("格式·堆叠标点", f"{st} 处")
    if DIVIDER.search(body):
        add("格式·分割线", "出现字符或图片拼成的分割线")
    if MD_RESIDUE.search(html or ""):
        add("格式·markdown残留", "出现 #/**/``` 等标记")
    if PS_SUFFIX.search(body):
        add("格式·PS/注前后缀", "用了 PS./注：等前后缀")

    # ── 2. AI 腔 ──
    abs_n = sum(body.count(w) for w in ABSTRACT)
    unit_n = len(UNIT_NUM.findall(body))
    quoted_n = len(QUOTED.findall(body))
    en_n = len(EN_WORD.findall(body))
    concrete = unit_n + quoted_n + en_n

    per_k = abs_n / n_chars * 1000
    if abs_n >= 3 and per_k >= 3.0 and concrete <= 2:
        add("AI腔·抽象词堆砌无数值",
            f"抽象词 {abs_n} 个（每千字 {per_k:.1f}），具体线索仅 {concrete} 个")
    elif abs_n >= 6 and per_k >= 5.0:
        add("AI腔·抽象词密度过高", f"抽象词 {abs_n} 个（每千字 {per_k:.1f}）")

    # 句式工整：大量"你将/你会/你需要"开头
    you_sent = len(re.findall(r"[。；\n]\s*你将|[。；\n]\s*你会|[。；\n]\s*你可以|^\s*你将", body))
    if you_sent >= 3:
        add("AI腔·第二人称说教", f"「你将/你会/你可以」开头 {you_sent} 处")

    # 三段式对比（不是A，而是B / 不只是A，而是B）
    contrast = len(re.findall(r"(不是|并非|不仅仅?是)[^。]{2,20}(而是|更是)[^。]{2,20}", body))
    if contrast >= 2:
        add("AI腔·三段式对比", f"{contrast} 处")

    # ── 3. 空洞（规则近似）──
    # 无任何数字、无英文词、无引号内容 → 缺少可验证信息
    all_nums = len(re.findall(r"\d", body))
    if chars >= 200 and all_nums == 0 and en_n == 0 and quoted_n == 0:
        add("空洞·零可验证信息", "全文无数字、无英文专名、无引号引述")
    elif chars >= 400 and all_nums == 0:
        add("空洞·无任何数字", f"{chars} 字却没有任何数字")

    # 纯图片（内容都在图里）
    if chars < 150 and (n_imgs or 0) >= 3:
        add("空洞·纯图片", f"{chars} 字 + {n_imgs} 张图")

    return issues


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DATA))
    ap.add_argument("--ids-file", default="")
    ap.add_argument("--min-chars", type=int, default=100)
    ap.add_argument("--out", default=str(DATA / "scan"))
    args = ap.parse_args()

    data = Path(args.data)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(f"file:{data/'mcmod.db'}?mode=ro", uri=True, timeout=10)
    sql = ("SELECT id,name,chars,n_headings,n_imgs,intro_html,intro_text "
           "FROM classes WHERE chars>=?")
    params: tuple = (args.min_chars,)
    if args.ids_file:
        ids = [int(x) for x in re.findall(r"\d+", Path(args.ids_file).read_text(encoding="utf-8"))]
        sql += f" AND id IN ({','.join('?'*len(ids))})"
        params = params + tuple(ids)
    rows = list(con.execute(sql, params))
    con.close()
    print(f"扫描 {len(rows)} 条（≥{args.min_chars} 字）")

    all_issues: list[dict] = []
    for r in rows:
        all_issues.extend(scan_row(*r))

    # 统计
    by_kind = Counter(i["kind"] for i in all_issues)
    by_page = defaultdict(list)
    for i in all_issues:
        by_page[i["id"]].append(i["kind"])

    # 输出 jsonl
    jl = out / "scan-problems.jsonl"
    with jl.open("w", encoding="utf-8") as f:
        for i in all_issues:
            f.write(json.dumps(i, ensure_ascii=False) + "\n")

    # 汇总
    summary = {
        "scanned": len(rows),
        "issues_total": len(all_issues),
        "pages_with_issues": len(by_page),
        "by_kind": dict(by_kind),
    }
    (out / "scan-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # 报告
    md = [f"# 三维扫描报告", "",
          f"- 扫描页面：**{len(rows)}** 条（≥{args.min_chars} 字）",
          f"- 命中问题：**{len(all_issues)}** 条记录",
          f"- 有问题页面：**{len(by_page)}** 条（{len(by_page)/len(rows)*100:.1f}%）", "",
          "## 问题分布", "",
          "| 类别 | 命中数 | 占比 |", "|---|---|---|"]
    for kind, n in by_kind.most_common():
        md.append(f"| {kind} | {n} | {n/len(rows)*100:.1f}% |")

    md += ["", "## 各类清单（每类前 40 条）", ""]
    by_kind_items = defaultdict(list)
    for i in all_issues:
        by_kind_items[i["kind"]].append(i)

    for kind, _ in by_kind.most_common():
        items = by_kind_items[kind]
        md.append(f"\n### {kind}（共 {len(items)} 条）\n")
        md.append("| id | 名称 | 字数 | 详情 | 链接 |")
        md.append("|---|---|---|---|---|")
        for it in items[:40]:
            url = f"https://www.mcmod.cn/class/{it['id']}.html"
            md.append(f"| {it['id']} | {(it['name'] or '')[:18]} | {it['chars']} | "
                      f"{it['detail'][:40]} | [打开]({url}) |")
        if len(items) > 40:
            md.append(f"\n*（其余 {len(items)-40} 条见 scan-problems.jsonl）*")

    rp = out / "scan-report.md"
    rp.write_text("\n".join(md), encoding="utf-8")

    print("\n=== 问题分布 ===")
    for kind, n in by_kind.most_common():
        print(f"  {kind:<24} {n:>5}")
    print(f"\n有问题的页面：{len(by_page)} / {len(rows)}（{len(by_page)/len(rows)*100:.1f}%）")
    print(f"\n输出：\n  {rp}\n  {jl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
