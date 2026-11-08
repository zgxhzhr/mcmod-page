#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析 MC百科模组介绍语料，产出「该怎么写」的统计报告。

读 mcmod.db（由 mcmod-corpus.py 抓取），输出：
    corpus/分析报告.md     人读版（结论 + 表格）
    corpus/stats.json      机读版（全部原始统计）

分析维度
--------
1. 章节结构：小标题数量分布、各位置高频标题、常见骨架序列、标题词频
2. 段落结构：段落数、每段句数、段长分布；按字数分档对比
3. 开头句：首句长度、开头模板分类、首段常用写法
4. 句长：句子总数、平均/中位/P90、过长句比例
5. 常用句式：高频动词与连接词、句式模板命中率
6. 排版习惯：表格/列表/图片使用率、首图率
7. 相关性：字数 × 小标题数、浏览量 × 字数

用法
----
    python analyze-corpus.py                  # 全量
    python analyze-corpus.py --min-chars 800  # 只看正文够长的
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import statistics
from collections import Counter
from pathlib import Path

DEFAULT_DATA = Path(r"E:\Mod\百科-语料")

SENT_SPLIT = re.compile(r"(?<=[。！？；])")
SENT_CLEAN = re.compile(r"[ \t\n\r]+")

# 开头句模板（顺序敏感：从最具体到最宽泛）
OPEN_PATTERNS = [
    ("X 是一个/一款 … 的模组", re.compile(r"^(?:.{2,30}?)(?:是|为)(?:一个|一款|一套|一种)[^。]{0,40}?(?:模组|MOD|mod)")),
    ("X 是 … 的附属/前置", re.compile(r"^(?:.{2,30}?)(?:是|为)[^。]{0,30}?(?:附属|附属模组|前置|扩展|分支)")),
    ("X 添加/加入 …", re.compile(r"^(?:[^。]{2,30}?)(?:添加|加入|增加|引入了?)[^。]{0,60}")),
    ("X 提供/支持 …", re.compile(r"^(?:[^。]{2,30}?)(?:提供|支持)[^。]{0,60}")),
    ("X 可以/能够 …", re.compile(r"^(?:[^。]{2,30}?)(?:可以|能够|能让)[^。]{0,60}")),
    ("X 基于/源自 …", re.compile(r"^(?:[^。]{2,30}?)(?:基于|源自|脱胎于)")),
]

VERBS = ["添加", "加入", "增加", "提供", "支持", "允许", "可以", "能够", "用于", "包括",
         "包含", "需要", "通过", "使用", "获得", "触发", "造成", "使得", "替换", "整合"]
CONNS = ["此外", "同时", "因此", "但是", "并且", "以及", "或者", "例如", "比如", "其中",
         "另外", "由于", "如果", "当", "目前", "主要", "其他", "相关"]

FORMULA = [
    ("X 可以通过 Y 来 Z", re.compile(r"可以通过[^。]{1,40}?(?:来|以)[^。]{1,30}")),
    ("在 X 时/后，Y", re.compile(r"在[^。]{1,25}?(?:时|后|前)[，,][^。]{1,40}")),
    ("X 会 Y", re.compile(r"[^。]{1,20}?会[^。]{1,40}")),
    ("如果 X，则 Y", re.compile(r"如果[^。]{1,40}?[，,][^。]{1,40}")),
    ("X 需要 Y", re.compile(r"[^。]{1,20}?需要[^。]{1,30}")),
    ("与 X 不同/相比", re.compile(r"(?:与|和)[^。]{1,25}?(?:不同|相比|类似)")),
]


def sentences(text: str):
    out = []
    for s in SENT_SPLIT.split(text):
        s = SENT_CLEAN.sub("", s).strip()
        if len(s) >= 5:
            out.append(s)
    return out


def pct(vals, q):
    if not vals:
        return 0
    return vals[min(len(vals) - 1, int(len(vals) * q))]


def bucket_stats(vals):
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        return {}
    return {
        "n": len(vals),
        "mean": round(statistics.mean(vals), 1),
        "median": pct(vals, 0.5),
        "p10": pct(vals, 0.1),
        "p90": pct(vals, 0.9),
        "max": vals[-1],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    ap.add_argument("--min-chars", type=int, default=600)
    args = ap.parse_args()
    data = Path(args.data)

    con = sqlite3.connect(data / "mcmod.db")
    rows = list(con.execute(
        "SELECT id,name,views,chars,n_paras,n_tables,n_lists,n_imgs,n_headings,headings,intro_text "
        "FROM classes WHERE chars >= ? ORDER BY chars DESC", (args.min_chars,)))
    con.close()
    if not rows:
        print(f"没有 chars>={args.min_chars} 的数据")
        return 1

    print(f"分析 {len(rows)} 条（chars >= {args.min_chars}）")

    heads_all, first_heads, head_words = [], [], Counter()
    skeletons = Counter()
    first_sent_tpl = Counter()
    sent_lens, para_lens, paras_per_doc = [], [], []
    verb_hits, conn_hits = Counter(), Counter()
    formula_hits = Counter()
    table_docs = list_docs = img_docs = 0
    first_sent_lens = []
    docs_with_h1 = 0

    for cid, name, views, chars, n_paras, n_tables, n_lists, n_imgs, n_heads, heads_json, body in rows:
        heads = json.loads(heads_json or "[]")
        heads_all.append(len(heads))
        if heads:
            docs_with_h1 += 1
            first_heads.append(heads[0].split(":", 1)[1])
            for h in heads:
                t = h.split(":", 1)[1]
                head_words[t] += 1
            skeletons[" → ".join(h.split(":", 1)[1] for h in heads[:3])] += 1
        if n_tables:
            table_docs += 1
        if n_lists:
            list_docs += 1
        if n_imgs:
            img_docs += 1

        # 段落
        paras = [p for p in (body or "").split("\n") if p.strip()]
        paras_per_doc.append(len(paras))
        for p in paras:
            para_lens.append(len(p))

        # 句子
        sents = sentences(body or "")
        for s in sents:
            sent_lens.append(len(s))
        if sents:
            fs = sents[0]
            first_sent_lens.append(len(fs))
            matched = False
            for label, pat in OPEN_PATTERNS:
                if pat.search(fs):
                    first_sent_tpl[label] += 1
                    matched = True
                    break
            if not matched:
                first_sent_tpl["其他/无法归类"] += 1

        for v in VERBS:
            verb_hits[v] += (body or "").count(v)
        for c in CONNS:
            conn_hits[c] += (body or "").count(c)
        for label, pat in FORMULA:
            if pat.search(body or ""):
                formula_hits[label] += 1

    n = len(rows)
    first_heads_top = Counter(first_heads).most_common(15)
    stats = {
        "docs": n,
        "min_chars": args.min_chars,
        "chars": bucket_stats([r[3] for r in rows]),
        "n_headings": bucket_stats(heads_all),
        "n_paras": bucket_stats(paras_per_doc),
        "para_len": bucket_stats(para_lens),
        "sent_len": bucket_stats(sent_lens),
        "first_sent_len": bucket_stats(first_sent_lens),
        "average_sentences_per_doc": round(len(sent_lens) / n, 1),
        "headings_count_dist": dict(sorted(Counter(heads_all).items())),
        "top_first_heading": first_heads_top,
        "top_all_heading": head_words.most_common(25),
        "top_skeletons": skeletons.most_common(15),
        "open_patterns": first_sent_tpl.most_common(),
        "verbs": verb_hits.most_common(12),
        "conns": conn_hits.most_common(12),
        "formulas": formula_hits.most_common(),
        "pct_with_headings": round(100 * docs_with_h1 / n, 1),
        "pct_with_table": round(100 * table_docs / n, 1),
        "pct_with_list": round(100 * list_docs / n, 1),
        "pct_with_img": round(100 * img_docs / n, 1),
    }

    # 长短对比（写作质量参照）
    def seg(lo, hi):
        g = [r for r in rows if lo <= r[3] < hi]
        if not g:
            return {}
        return {
            "docs": len(g),
            "median_headings": statistics.median([r[8] for r in g]),
            "median_paras": statistics.median([r[4] for r in g]),
            "pct_table": round(100 * sum(1 for r in g if r[5]) / len(g), 1),
            "pct_heading": round(100 * sum(1 for r in g if r[8]) / len(g), 1),
        }

    stats["segments"] = {"short<800": seg(0, 800), "mid800-2500": seg(800, 2500),
                         "long>=2500": seg(2500, 10 ** 9)}

    out = data / "corpus"
    out.mkdir(exist_ok=True)
    (out / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    s = stats
    md = [f"# MC百科模组介绍 · 语料分析报告\n",
          f"- 样本：**{n} 条**（正文 ≥ {args.min_chars} 字）",
          f"- 字数：中位 **{s['chars']['median']}** 字（P10 {s['chars']['p10']} / P90 {s['chars']['p90']} / 最长 {s['chars']['max']}）\n",
          "## 1. 章节结构\n",
          f"- 有分节的比例：**{s['pct_with_headings']}%**",
          f"- 小标题数量：中位 **{s['n_headings']['median']}** 个（P90 {s['n_headings']['p90']} / 最多 {s['n_headings']['max']}）",
          f"- 小标题数量分布：" + "，".join(f"{k} 个→{v} 篇" for k, v in list(s["headings_count_dist"].items())[:8]),
          "",
          "**最常见的第一个小标题**（即最常用开篇章节）\n",
          "| 标题 | 出现次数 |", "|---|---|"]
    for t, c in s["top_first_heading"]:
        md.append(f"| {t} | {c} |")
    md += ["", "**所有小标题词频 Top 15**\n", "| 标题 | 次数 |", "|---|---|"]
    for t, c in s["top_all_heading"][:15]:
        md.append(f"| {t} | {c} |")
    md += ["", "**常见骨架（前三个小标题的组合）**\n", "| 骨架 | 篇数 |", "|---|---|"]
    for k, c in s["top_skeletons"]:
        md.append(f"| {k} | {c} |")

    md += ["\n## 2. 段落结构\n",
           f"- 段落数：中位 **{s['n_paras']['median']}** 段（P90 {s['n_paras']['p90']}）",
           f"- 单段长度：中位 **{s['para_len']['median']}** 字（P90 {s['para_len']['p90']}）",
           f"- 每篇句子总数：平均 **{s['average_sentences_per_doc']}** 句",
           "\n**按正文长度分档对比**\n",
           "| 档位 | 篇数 | 小标题中位数 | 段落中位数 | 有表格比例 | 有分节比例 |",
           "|---|---|---|---|---|---|"]
    for label, g in s["segments"].items():
        if g:
            md.append(f"| {label} | {g['docs']} | {g['median_headings']} | {g['median_paras']} "
                      f"| {g['pct_table']}% | {g['pct_heading']}% |")

    md += ["\n## 3. 开头句写法\n",
           f"- 首句长度：中位 **{s['first_sent_len']['median']}** 字（P90 {s['first_sent_len']['p90']}）",
           "\n| 开头模板 | 篇数 | 占比 |", "|---|---|---|"]
    for label, c in s["open_patterns"]:
        md.append(f"| {label} | {c} | {round(100 * c / n, 1)}% |")

    md += ["\n## 4. 句长\n",
           f"- 单句长度：平均 **{s['sent_len']['mean']}** 字 / 中位 **{s['sent_len']['median']}** 字",
           f"- P90 **{s['sent_len']['p90']}** 字，最长 {s['sent_len']['max']} 字",
           f"- 全样本句子总数：{s['sent_len']['n']}",
           "\n## 5. 常用句式\n",
           "**高频动词**\n", "| 词 | 次数 |", "|---|---|"]
    for w, c in s["verbs"]:
        md.append(f"| {w} | {c} |")
    md += ["", "**高频连接词**\n", "| 词 | 次数 |", "|---|---|"]
    for w, c in s["conns"]:
        md.append(f"| {w} | {c} |")
    md += ["", "**句式模板命中率**（命中该句式的篇章占比）\n", "| 句式 | 篇数 | 占比 |", "|---|---|---|"]
    for label, c in s["formulas"]:
        md.append(f"| {label} | {c} | {round(100 * c / n, 1)}% |")

    md += ["\n## 6. 排版习惯\n",
           f"- 含表格：**{s['pct_with_table']}%**",
           f"- 含列表：**{s['pct_with_list']}%**",
           f"- 含图片：**{s['pct_with_img']}%**",
           "\n---\n", "*由 analyze-corpus.py 自动生成；stats.json 为完整数据。*"]

    rp = out / "分析报告.md"
    rp.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"已生成 {rp}")
    print(f"  {out/'stats.json'}")
    print(f"\n关键结果：中位 {s['chars']['median']} 字 / {s['n_headings']['median']} 个小标题 / "
          f"句长中位 {s['sent_len']['median']} 字 / 分节率 {s['pct_with_headings']}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
