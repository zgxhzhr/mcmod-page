#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 味检测器：给一段百科正文打分，并列出具体问题。

用途
----
1. 写完页面后自查，代替“凭感觉觉得像 AI”；
2. 训练前后对比（AI 味注入器生成的数据也要用它验证）；
3. 批量检查已有稿子。

用法
----
    python ai-tell-check.py 文件.html
    python ai-tell-check.py 文件.md --json
    type 文件.txt | python ai-tell-check.py -

评分
----
100 分起扣，扣分项全部可解释（每条都给出命中的原文片段）。
    ≥85  合格，像人写的
    70-84 轻微 AI 味
    50-69 明显 AI 味，建议改写
    <50  严重，基本是机器腔

检测维度
--------
套话连接词 / 三连排比 / 升华收尾 / 空洞形容词 / 模板结尾 /
句长均匀度（CV）/ 超长句占比 / 名词化抽象词 / 感叹与反问 /
过度口语 / 格式问题（hN 层级、表格无 th、markdown 残留）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- 词表

# 套话：出现即扣分
CLICHES = [
    "值得注意的是", "值得一提的是", "从某种角度", "从某种意义上", "作为一款", "作为一个",
    "可以说", "不难发现", "众所周知", "总而言之", "综上", "总的来看", "总的来说",
    "方面有着", "发挥着", "起到了", "与此同时", "除此之外", "更进一步", "更好地",
    "这就是所谓的", "这正是", "换句话说", "也就是说", "在此基础上", "区别于",
]

# 对仗/对称结构（AI 最爱）：短句成对、编号对称
SYMMETRY = [
    re.compile(r"半[\u4e00-\u9fa5]{1,4}\s*[，,]\s*半[\u4e00-\u9fa5]{1,4}"),
    re.compile(r"其一[^。]{2,30}其二"),
    re.compile(r"首先[^。]{2,40}其次[^。]{2,40}(最后|再次)"),
    re.compile(r"(教学|游戏|玩法|内容|功能)的那一半"),
    re.compile(r"既[^。]{2,20}又[^。]{2,20}"),
]
# 口语化总结/定性句
SUMMARY_VERBS = [
    re.compile(r"(这就是|这便是)[^。]{2,30}(过程|体验|乐趣|意义|价值)"),
    re.compile(r"(而不只是|而不仅仅是|而不是)[^。]{2,30}"),
    re.compile(r"(并非|不是)[^。]{2,20}[，,]?而是[^。]{2,30}"),
]
# 三连排比 / 递进堆叠
PARALLEL = [
    re.compile(r"不仅[^。]{2,30}?而且[^。]{2,30}?更"),
    re.compile(r"不仅[^。]{2,30}?还[^。]{2,30}?更"),
    re.compile(r"既[^。]{2,20}?又[^。]{2,20}?还"),
    re.compile(r"无论是[^。]{2,30}?还是[^。]{2,60}?都"),
]
# 升华收尾：段末出现
SUBLIME = [
    re.compile(r"(体现了|彰显了|展现了|诠释了|堪称|可以说是)[^。]{0,40}。?\s*$"),
    re.compile(r"(这不仅是|不仅仅是)[^。]{2,40}(更是|还是)[^。]{2,40}"),
]
# 空洞形容词
HOLLOW_ADJ = [
    "丰富的", "流畅的", "完善的", "精美的", "强大的", "优秀的", "显著的", "极大的",
    "全面的", "独特的", "出色的", "卓越的", "多样的", "便捷的", "高效的", "灵活的",
    "创新的", "细腻的", "贴心的", "完善的",
]
# 模板结尾
TEMPLATE_END = [
    re.compile(r"以上(内容|介绍|信息)?(基于|根据)[^。]{0,20}版本"),
    re.compile(r"希望(能)?(对你|对大家|帮助)"),
    re.compile(r"欢迎(大家)?(在)?评论区"),
]
# 名词化抽象词（提示「不像人写」）
NOMINALIZATION = ["方面", "程度", "过程", "情况", "相关", "进行", "实现", "具有一定",
                  "具备", "拥有", "存在", "使得", "通过对于"]
# 过度口语（另一个极端，资料页不可有）
COLLOQUIAL = ["嘛", "呗", "说白了", "反正", "贼", "挺", "超级", "哈", "啊", "呀",
              "其实吧", "老实说"]
# 表格/格式检查
RE_H = re.compile(r"<h([1-6])[^>]*>(.*?)</h\1>", re.S | re.I)
RE_TABLE = re.compile(r"<table[^>]*>(.*?)</table>", re.S | re.I)
RE_TH = re.compile(r"<th[\s>]", re.I)
RE_TR = re.compile(r"<tr[\s>]", re.I)
RE_MD_RESIDUE = [
    re.compile(r"(?m)^\s{0,3}#{1,6}\s"),          # markdown 标题残留
    re.compile(r"(?m)^\s*[-*+]\s"),               # markdown 列表残留
    re.compile(r"(?m)^\s*\|.*\|\s*$"),            # markdown 表格残留
    re.compile(r"\*\*[^*\n]+\*\*"),               # **加粗** 残留
    re.compile(r"\[[^\]]{1,20}\]\([^)]+\)"),      # [text](url) 残留
]
SENT_SPLIT = re.compile(r"(?<=[。！？；])")


# ---------------------------------------------------------------- 处理

def strip_html(text: str) -> tuple[str, str]:
    """返回 (纯文本, 原 HTML)；纯文本保留段落换行。"""
    is_html = "<" in text and ">" in text
    if not is_html:
        return text, text
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", text)
    # 表格内容单独剔除：单元格里的短句会把句长分布和段尾判断拉歪
    t = re.sub(r"(?is)<table[^>]*>.*?</table>", "\n", t)
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = re.sub(r"(?i)</(p|div|li|tr|h[1-6]|table)>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"&nbsp;", " ", t)
    t = re.sub(r"&amp;", "&", t)
    t = re.sub(r"&lt;", "<", t)
    t = re.sub(r"&gt;", ">", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{2,}", "\n", t)
    return t.strip(), text


def sentences(text: str) -> list[str]:
    out = []
    for s in SENT_SPLIT.split(text.replace("\n", "")):
        s = s.strip()
        if len(s) >= 4:
            out.append(s)
    return out


def paragraphs(text: str) -> list[str]:
    return [p.strip() for p in text.split("\n") if p.strip()]


def cv(values: list[float]) -> float:
    """变异系数：标准差 / 均值。人写通常 0.35+，AI 常 <0.25。"""
    if len(values) < 3:
        return 1.0
    mean = sum(values) / len(values)
    if mean <= 0:
        return 0.0
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return (var ** 0.5) / mean


def snippets(text: str, pattern: str, limit: int = 3) -> list[str]:
    out = []
    for m in re.finditer(pattern, text):
        s = max(0, m.start() - 12)
        out.append(text[s:m.end() + 12].replace("\n", " "))
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------- 主检测

def check(raw: str, page_type: str = "page") -> dict:
    plain, original = strip_html(raw)
    sents = sentences(plain)
    paras = paragraphs(plain)
    total_chars = len(re.sub(r"\s", "", plain))

    issues: list[dict] = []

    def add(kind: str, penalty: int, detail: str, samples: list[str] | None = None):
        issues.append({"kind": kind, "penalty": penalty, "detail": detail,
                       "samples": samples or []})

    # 1. 套话连接词
    hit = []
    for w in CLICHES:
        if "..." in w:
            continue
        n = plain.count(w)
        if n:
            hit.append((w, n))
    if hit:
        cnt = sum(n for _, n in hit)
        add("套话连接词", min(20, 4 * cnt),
            f"命中 {cnt} 处：" + "、".join(f"{w}×{n}" for w, n in hit),
            [w for w, _ in hit[:3]])

    # 2. 三连排比 / 对称结构（同一区间只算一次）
    spans = []
    for pat in PARALLEL + SYMMETRY + SUMMARY_VERBS:
        for m in pat.finditer(plain):
            spans.append((m.start(), m.end(), m.group(0)))
    spans.sort()
    merged = []
    for s, e, g in spans:
        if merged and s <= merged[-1][1]:
            if e > merged[-1][1]:
                merged[-1] = (merged[-1][0], e, merged[-1][2])
        else:
            merged.append((s, e, g))
    if merged:
        add("排比/对称/定性句式", min(24, 6 * len(merged)),
            f"命中 {len(merged)} 处",
            [g.replace("\n", " ")[:50] for _, _, g in merged[:3]])

    # 3. 升华收尾（按段尾判断）
    sublime_hits = []
    for p in paras:
        for pat in SUBLIME:
            if pat.search(p):
                sublime_hits.append(p[-40:])
                break
    if sublime_hits:
        add("升华/总结式收尾", min(20, 5 * len(sublime_hits)),
            f"{len(sublime_hits)} 个段落以升华句结尾", sublime_hits[:3])

    # 4. 空洞形容词密度
    hollow = [(w, plain.count(w)) for w in set(HOLLOW_ADJ) if plain.count(w)]
    if hollow:
        cnt = sum(n for _, n in hollow)
        per_k = cnt / max(total_chars, 1) * 1000
        if per_k >= 1.0:
            add("空洞形容词", min(15, int(per_k * 3)),
                f"{cnt} 处（每千字 {per_k:.1f} 个）：" +
                "、".join(f"{w}×{n}" for w, n in sorted(hollow, key=lambda x: -x[1])[:5]),
                [w for w, _ in hollow[:3]])

    # 5. 模板结尾
    tail = plain[-200:]
    for pat in TEMPLATE_END:
        m = pat.search(tail)
        if m:
            add("模板化结尾", 10, "文末出现模板化收尾句", [m.group(0)])

    # 6. 句长均匀度
    lens = [len(s) for s in sents]
    if len(lens) >= 5:
        c = cv(lens)
        if c < 0.22:
            add("句长过于均匀", 15,
                f"句长变异系数 {c:.2f}（人写通常 ≥0.30，AI 常 <0.22）")
        elif c < 0.28:
            add("句长偏均匀", 8, f"句长变异系数 {c:.2f}")

    # 6.5 段落长度均匀度
    p_lens = [len(p) for p in paras if len(p) >= 10]
    if len(p_lens) >= 5:
        pc = cv(p_lens)
        if pc < 0.30:
            add("段落长度过于均匀", 8, f"段落变异系数 {pc:.2f}（人写通常 ≥0.40）")

    # 7. 超长句
    if lens:
        long_n = sum(1 for L in lens if L > 60)
        ratio = long_n / len(lens)
        if ratio > 0.25:
            add("超长句过多", 8,
                f"{long_n}/{len(lens)} 句超过 60 字（{ratio*100:.0f}%）")

    # 8. 名词化抽象词
    nom = [(w, plain.count(w)) for w in NOMINALIZATION if plain.count(w)]
    if nom:
        cnt = sum(n for _, n in nom)
        per_k = cnt / max(total_chars, 1) * 1000
        if per_k >= 3.0:
            add("名词化抽象表达", min(12, int(per_k)),
                f"{cnt} 处（每千字 {per_k:.1f}）：" +
                "、".join(f"{w}×{n}" for w, n in sorted(nom, key=lambda x: -x[1])[:4]))

    # 9. 感叹与反问
    exclam = plain.count("！") + plain.count("!")
    question = len(re.findall(r"[^。]{2,}？", plain))
    if exclam or question:
        add("感叹句/反问句", min(12, 3 * (exclam + question)),
            f"感叹 {exclam} 处、反问 {question} 处（资料页应为 0）")

    # 10. 过度口语（仅资料页严格要求）
    col = [(w, plain.count(w)) for w in COLLOQUIAL if plain.count(w)]
    if col:
        cnt = sum(n for _, n in col)
        limit = 0 if page_type == "item" else 2
        if cnt > limit:
            add("过度口语", min(16, 4 * (cnt - limit)),
                f"{cnt} 处口语词（本页类型允许 ≤{limit}）：" +
                "、".join(f"{w}×{n}" for w, n in sorted(col, key=lambda x: -x[1])[:5]))

    # 11. 格式检查（真有 HTML 时才做）
    if "<" in original:
        heads = RE_H.findall(original)
        levels = [int(h[0]) for h in heads]
        if levels:
            if levels[0] != 1:
                add("标题起始级别", 8, f"首个标题是 h{levels[0]}，应从 h1 开始")
            for a, b in zip(levels, levels[1:]):
                if b - a > 1:
                    add("标题跨级", 6, f"出现 h{a} → h{b} 的跨级")
                    break
        for tbl in RE_TABLE.findall(original):
            if RE_TR.search(tbl) and not RE_TH.search(tbl):
                add("表格缺表头", 6, "存在没有 <th> 的表格")
                break
    for pat in RE_MD_RESIDUE:
        m = pat.search(original)
        if m:
            add("markdown 残留", 6, "正文里残留 markdown 语法", [m.group(0)[:40]])
            break

    penalty = sum(i["penalty"] for i in issues)
    score = max(0, 100 - penalty)

    if score >= 85:
        level = "合格（像人写的）"
    elif score >= 70:
        level = "轻微 AI 味"
    elif score >= 50:
        level = "明显 AI 味，建议改写"
    else:
        level = "严重，基本是机器腔"

    return {
        "score": score,
        "level": level,
        "chars": total_chars,
        "sentences": len(sents),
        "paragraphs": len(paras),
        "sent_len_median": sorted(lens)[len(lens) // 2] if lens else 0,
        "sent_len_cv": round(cv(lens), 3) if len(lens) >= 3 else None,
        "issues": issues,
    }


def render(r: dict) -> str:
    lines = [
        f"AI 味评分：{r['score']}/100  —  {r['level']}",
        f"  字数 {r['chars']} · 句子 {r['sentences']} · 段落 {r['paragraphs']} · "
        f"句长中位 {r['sent_len_median']} · 变异系数 {r['sent_len_cv']}",
    ]
    if not r["issues"]:
        lines.append("  未发现明显问题。")
    else:
        lines.append(f"\n发现 {len(r['issues'])} 类问题（共扣 {100 - r['score']} 分）：")
        for i, it in enumerate(r["issues"], 1):
            lines.append(f"  {i}. [{it['kind']}] -{it['penalty']}分：{it['detail']}")
            for s in it["samples"]:
                lines.append(f"       · {s}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="AI 味检测器")
    ap.add_argument("path", help="文件路径，或 - 表示从标准输入读")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--page-type", default="page",
                    choices=["page", "item", "tutorial"],
                    help="资料页(item) 对口语零容忍；page=介绍页；tutorial=教程")
    args = ap.parse_args()

    if args.path == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(args.path).read_text(encoding="utf-8-sig", errors="replace")

    r = check(raw, args.page_type)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(render(r))
    return 0 if r["score"] >= 70 else 1


if __name__ == "__main__":
    raise SystemExit(main())
