#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 味注入器：把真实百科正文改写成"AI 味版本"，用于构造训练对。

为什么要程序化注入
------------------
SFT / ORPO 需要 (差, 好) 成对数据。抓到的语料只有"好"的成品，
差版本可以程序化生成 —— 零标注、零 API 成本、可控可复现，
而且注入的正是我们实际遇到的毛病（套话、排比、升华、模板结尾）。

用法
----
    python ai-tell-inject.py 原文.md                    # 输出 AI 味版
    python ai-tell-inject.py 原文.md --strength 0.8     # 注入强度
    python ai-tell-inject.py 原文.md --json             # 输出 {real, ai}
    python ai-tell-inject.py --dir 目录 --out 数据集.jsonl

输出形式（--json / --out）
--------------------------
    {"real": "原始正文", "ai": "注入后正文"}      # 训练时可组成 ORPO 的 chosen/rejected

注入手法
--------
1. 段首套话（值得注意的是 / 从某种角度来看 / 作为一款…）
2. 并列改三连排比（A、B → 不仅 A，而且 B，更 …）
3. 段尾升华句（这一设计体现了开发者的用心 / 彰显了…）
4. 空洞形容词（丰富的 / 流畅的 / 完善的 …）
5. 句长均匀化（把过短句与相邻句合并）
6. 文末模板结尾（以上内容基于 X 版本编写）
7. 对称口号（把某个并列改写成「X 的那一半」式）
"""
from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

CLICHE_PREFIX = [
    "值得注意的是，", "值得一提的是，", "从某种角度来看，", "从某种意义上说，",
    "作为一款模组，", "可以说，", "不难发现，", "总的来说，", "与此同时，",
    "在此基础上，", "更进一步说，",
]
SUBLIME_TAIL = [
    "这一设计体现了开发者的用心。",
    "可以说是一款不可多得的佳作。",
    "无疑为玩家带来了更好的体验。",
    "彰显了模组的强大实力。",
    "这也是该模组的一大亮点。",
    "让整体体验更加流畅自然。",
    "值得玩家慢慢体会。",
]
HOLLOW_WORDS = ["丰富的", "流畅的", "完善的", "精美的", "强大的", "优秀的",
                "显著的", "全面的", "独特的", "出色的", "高效的", "灵活的"]
TEMPLATE_END = [
    "以上内容基于 {ver} 版本编写。",
    "以上介绍希望能帮助你快速了解这个模组。",
    "欢迎在评论区分享你的游玩体验。",
]
SYMMETRY_TPL = [
    "{a}的那一半：{a1}；{b}的那一半：{b1}。",
]

SENT_SPLIT = re.compile(r"(?<=[。！？])")
RE_HTML_ANY = re.compile(r"<[^>]+>")


def to_plain(raw: str) -> str:
    if "<" not in raw:
        return raw
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", raw)
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = re.sub(r"(?i)</(p|div|li|tr|h[1-6]|table)>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"&nbsp;", " ", t)
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n{2,}", "\n", t).strip()


def paragraphs(text: str) -> list[str]:
    return [p.strip() for p in text.split("\n") if p.strip()]


def sentences(p: str) -> list[str]:
    return [s for s in SENT_SPLIT.split(p) if s.strip()]


def inject(text: str, strength: float = 1.0, seed: int = 0, version: str = "1.0") -> str:
    rnd = random.Random(seed or None)
    paras = paragraphs(text)
    out: list[str] = []

    for p in paras:
        # 跳过标题标记 [h1=...] / [h2=...]、列表碎片、表格残行 —— 这些不是正文段落
        if re.match(r"^\[h\d+=", p) or re.match(r"^\[[a-z]+:", p):
            out.append(p)
            continue
        if len(p) < 24 or p.count("。") == 0:
            out.append(p)
            continue

        sents = sentences(p)
        if not sents:
            out.append(p)
            continue

        # 1) 段首套话
        if rnd.random() < 0.55 * strength:
            sents[0] = rnd.choice(CLICHE_PREFIX) + sents[0]

        # 2) 并列 → 三连排比（找「A、B」或「A，B」结构）
        joined = "".join(sents)
        m = re.search(r"([\u4e00-\u9fa5]{2,8})、([\u4e00-\u9fa5]{2,8})", joined)
        if m and rnd.random() < 0.6 * strength:
            a, b = m.group(1), m.group(2)
            joined = joined.replace(
                m.group(0),
                f"不仅{m.group(1)}，而且{b}，更有完善的其他功能",
                1,
            )
            sents = sentences(joined)

        # 3) 空洞形容词：句末追加评价性短语
        long_idx = [k for k, s in enumerate(sents) if len(s) >= 30]
        if long_idx and rnd.random() < 0.5 * strength:
            adj = rnd.choice(HOLLOW_WORDS)
            idx = rnd.choice(long_idx)
            s = sents[idx].rstrip("。！？")
            sents[idx] = s + f"，整体表现{adj}。"

        # 4) 段尾升华（只对正文段）
        if len(p) >= 60 and rnd.random() < 0.6 * strength:
            tail = rnd.choice(SUBLIME_TAIL)
            if not sents[-1].rstrip("。").endswith(tail.rstrip("。")):
                sents[-1] = sents[-1].rstrip("。") + "。" + tail

        # 5) 句长均匀化：把过短的两句合并
        if rnd.random() < 0.4 * strength and len(sents) >= 3:
            i = next((k for k, s in enumerate(sents[:-1]) if len(s) < 15), None)
            if i is not None:
                a = sents[i].rstrip("。")
                b = sents[i + 1]
                sents[i] = a + "，并且" + b
                del sents[i + 1]

        out.append("".join(sents))

    body = "\n".join(out)

    # 6) 文末模板
    if rnd.random() < 0.7 * strength:
        body = body.rstrip() + "\n" + rnd.choice(TEMPLATE_END).format(ver=version)

    return body


def main() -> int:
    ap = argparse.ArgumentParser(description="AI 味注入器")
    ap.add_argument("path", nargs="?", help="输入文件")
    ap.add_argument("--dir", help="批量：目录下的 .md/.txt 全部处理")
    ap.add_argument("--out", help="批量输出 jsonl 路径")
    ap.add_argument("--strength", type=float, default=1.0, help="注入强度 0-1")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--version", default="1.0", help="模板结尾里用的版本号")
    ap.add_argument("--json", action="store_true", help="输出 {real, ai} JSON")
    args = ap.parse_args()

    if args.dir:
        d = Path(args.dir)
        files = sorted(list(d.glob("*.md")) + list(d.glob("*.txt")) + list(d.glob("*.html")))
        out_path = Path(args.out) if args.out else d / "pairs.jsonl"
        n = 0
        with out_path.open("w", encoding="utf-8") as f:
            for i, fp in enumerate(files):
                raw = fp.read_text(encoding="utf-8-sig", errors="replace")
                real = to_plain(raw)
                if len(re.sub(r"\s", "", real)) < 200:
                    continue
                ai = inject(real, args.strength, seed=(args.seed + i), version=args.version)
                f.write(json.dumps({"src": fp.name, "real": real, "ai": ai},
                                   ensure_ascii=False) + "\n")
                n += 1
        print(f"已处理 {n} 个文件 → {out_path}")
        return 0

    if not args.path:
        ap.print_help()
        return 2

    raw = Path(args.path).read_text(encoding="utf-8-sig", errors="replace")
    real = to_plain(raw)
    ai = inject(real, args.strength, seed=args.seed, version=args.version)
    if args.json:
        print(json.dumps({"real": real, "ai": ai}, ensure_ascii=False, indent=2))
    else:
        print(ai)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
