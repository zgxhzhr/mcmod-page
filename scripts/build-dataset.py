#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从语料库构造训练数据集：以「收藏夹高质量语料」为主，输出 ORPO / SFT 两种格式。

数据分层
--------
- **主资料（priority 0）**：收藏夹 1224 条。用户指定的最规范一批，训练优先级最高。
- **补充（priority 1）**：按 id 顺序抓的其余语料，只在主资料不足时使用（默认不混入）。

筛选条件
--------
1. 正文字数 ≥ --min-chars（默认 600）
2. 有分节（n_headings ≥ 1）——说明是规范写法
3. 正文前 200 字指纹去重（同一模组多版本页面会重复）
4. 剔除已知模板：整段只有"暂未添加""待补充"之类

样本切分
--------
长文按小节切成 300–900 字的段落组，避免单条超长被截断；
短文整篇作为一条样本。切分后每条形如：

    输入（AI 味版）→ 输出（规范版）

输出文件
--------
    train.jsonl / val.jsonl / test.jsonl
    - orpo: {"prompt": 指令, "chosen": 规范版, "rejected": AI味版}
    - sft : {"messages":[{user},{assistant}]}
    另附 stats.json（条数、字数分布、来源分布）

用法
----
    python build-dataset.py --ids-file 收藏夹ids.txt
    python build-dataset.py --ids-file fav.txt --min-chars 800 --poison-strength 0.85
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
import re
import sqlite3
from collections import Counter
from pathlib import Path

DEFAULT_DATA = Path(r"E:\Mod\百科-语料")
SCRIPT_DIR = Path(__file__).parent

INSTRUCTION = (
    "你是 MC百科（mcmod.cn）的资深编辑。请把下面这段模组介绍改写成规范、平实、严谨的百科文风：\n"
    "1. 保留全部数值、名称、触发条件与机制，不得删减或改写；\n"
    "2. 去掉套话、排比、升华句、空洞形容词与模板化收尾；\n"
    "3. 句子长短交错，避免每句等长；\n"
    "4. 只输出改写后的正文，不要解释。\n\n"
    "待改写：\n{poisoned}"
)

# 明显是占位/无内容的片段
JUNK_PATTERNS = [
    re.compile(r"暂[无未]"),
    re.compile(r"待补充|敬请期待|稍后补|TODO"),
    re.compile(r"^(如题|同上|见上)$"),
]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def clean_text(t: str) -> str:
    t = re.sub(r"[ \t]+", " ", t or "")
    t = re.sub(r"\n{2,}", "\n", t)
    return t.strip()


def is_junk(t: str) -> bool:
    if len(t) < 40:
        return True
    return any(p.search(t) for p in JUNK_PATTERNS)


def fingerprint(t: str) -> str:
    core = re.sub(r"\s", "", t)[:200]
    return hashlib.md5(core.encode("utf-8")).hexdigest()


def hard_split(para: str, max_len: int = 900) -> list[str]:
    """超长段落按句号切开，保证不会有单段超出上限。"""
    sents = re.split(r"(?<=[。！？；])", para)
    out, buf = [], ""
    for s in sents:
        if len(buf) + len(s) > max_len and buf:
            out.append(buf)
            buf = s
        else:
            buf += s
    if buf:
        out.append(buf)
    # 若单句仍超长（无标点的长串），硬切
    final = []
    for piece in out:
        while len(piece) > max_len:
            final.append(piece[:max_len])
            piece = piece[max_len:]
        if piece.strip():
            final.append(piece)
    return final


def split_into_samples(body: str, min_len: int = 300, max_len: int = 900) -> list[str]:
    """按段落累积切成 300-900 字的样本；超长段落按句切开。"""
    raw_paras = [p for p in body.split("\n") if p.strip()]
    paras: list[str] = []
    for p in raw_paras:
        if len(re.sub(r"\s", "", p)) > max_len:
            paras.extend(hard_split(p, max_len))
        else:
            paras.append(p)
    out, buf, cur = [], [], 0
    for p in paras:
        plen = len(re.sub(r"\s", "", p))
        if cur + plen > max_len and buf:
            out.append("\n".join(buf))
            buf, cur = [], 0
        buf.append(p)
        cur += plen
        if cur >= min_len and plen <= max_len:
            # 达到下限且当前段不长，收一个样本
            continue
    if buf:
        joined = "\n".join(buf)
        if len(re.sub(r"\s", "", joined)) >= min_len:
            out.append(joined)
        elif out:
            out[-1] = out[-1] + "\n" + joined  # 尾部太短就并入上一条
    return [s for s in out if len(re.sub(r"\s", "", s)) >= min_len * 0.8]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    ap.add_argument("--ids-file", required=True, help="主资料 id 列表（收藏夹 1224 条）")
    ap.add_argument("--extra-ids", default="", help="补充资料 id 列表（可选）")
    ap.add_argument("--min-chars", type=int, default=600)
    ap.add_argument("--require-headings", action="store_true", default=True)
    ap.add_argument("--poison-strength", type=float, default=0.85)
    ap.add_argument("--split", default="0.8,0.1,0.1", help="train,val,test 比例")
    ap.add_argument("--out", default=str(DEFAULT_DATA / "dataset"))
    ap.add_argument("--seed", type=int, default=20261108)
    args = ap.parse_args()

    inj = load_module("aitell", SCRIPT_DIR / "ai-tell-inject.py")
    data = Path(args.data)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    primary = [int(x) for x in re.findall(r"\d+", Path(args.ids_file).read_text(encoding="utf-8"))]
    extra = [int(x) for x in re.findall(r"\d+", Path(args.extra_ids).read_text(encoding="utf-8"))] if args.extra_ids else []
    print(f"主资料 {len(primary)} 个 id" + (f"，补充 {len(extra)} 个" if extra else ""))

    con = sqlite3.connect(f"file:{data/'mcmod.db'}?mode=ro", uri=True, timeout=5)
    con.row_factory = sqlite3.Row

    def fetch_rows(ids: list[int]):
        q = ",".join("?" * len(ids))
        return list(con.execute(
            f"SELECT id,name,chars,n_headings,n_tables,intro_html,intro_text FROM classes "
            f"WHERE id IN ({q}) AND chars >= ?", (*ids, args.min_chars)))

    rows = [(r, 0) for r in fetch_rows(primary)]
    if extra:
        got = {r["id"] for r, _ in rows}
        rows += [(r, 1) for r in fetch_rows(extra) if r["id"] not in got]
    con.close()

    # 去重 + 垃圾过滤
    seen = set()
    kept, dropped = [], Counter()
    for r, prio in rows:
        body = clean_text(r["intro_text"])
        if is_junk(body):
            dropped["垃圾/过短"] += 1
            continue
        if args.require_headings and (r["n_headings"] or 0) < 1:
            dropped["无分节"] += 1
            continue
        fp = fingerprint(body)
        if fp in seen:
            dropped["重复"] += 1
            continue
        seen.add(fp)
        kept.append((r, prio, body))

    print(f"入库 {len(rows)} → 保留 {len(kept)}（丢弃：{dict(dropped)}）")

    # 切样本并注入
    rnd = random.Random(args.seed)
    samples = []
    for r, prio, body in kept:
        for piece in split_into_samples(body):
            real = clean_text(piece)
            if len(re.sub(r"\s", "", real)) < args.min_chars * 0.5:
                continue
            ai = inj.inject(real, args.poison_strength, seed=r["id"] + len(real))
            samples.append({
                "src_id": r["id"],
                "src_name": r["name"] or "",
                "priority": prio,
                "chars": len(re.sub(r"\s", "", real)),
                "real": real,
                "ai": clean_text(ai),
            })

    if not samples:
        print("没有可用样本")
        return 1

    # 按优先级排序后划分（主资料优先进入 train）
    samples.sort(key=lambda s: (s["priority"], s["src_id"]))
    rnd.shuffle(samples)
    # 先按模组 id 分组，避免同模组跨集
    by_id: dict[int, list] = {}
    for s in samples:
        by_id.setdefault(s["src_id"], []).append(s)
    ids = list(by_id.keys())
    rnd.shuffle(ids)

    tr, va, te = (float(x) for x in args.split.split(","))
    n = len(ids)
    n_tr, n_va = int(n * tr), int(n * va)
    split_ids = {
        "train": ids[:n_tr],
        "val": ids[n_tr:n_tr + n_va],
        "test": ids[n_tr + n_va:],
    }

    stats = {"splits": {}, "source": {}, "chars": []}
    for name, sel in split_ids.items():
        items = [s for i in sel for s in by_id[i]]
        orpo = out_dir / f"{name}.jsonl"
        with orpo.open("w", encoding="utf-8") as f:
            for s in items:
                prompt = INSTRUCTION.format(poisoned=s["ai"])
                f.write(json.dumps({
                    "prompt": prompt,
                    "chosen": s["real"],
                    "rejected": s["ai"],
                    "meta": {"src_id": s["src_id"], "name": s["src_name"],
                             "priority": s["priority"], "chars": s["chars"]},
                }, ensure_ascii=False) + "\n")
        stats["splits"][name] = {"samples": len(items), "docs": len(sel)}
        for s in items:
            stats["chars"].append(s["chars"])
            stats["source"][f"p{s['priority']}"] = stats["source"].get(f"p{s['priority']}", 0) + 1

    # SFT 格式（同一批数据，改成 messages）
    sft = out_dir / "train-sft.jsonl"
    with sft.open("w", encoding="utf-8") as f:
        for i in split_ids["train"]:
            for s in by_id[i]:
                f.write(json.dumps({"messages": [
                    {"role": "user", "content": INSTRUCTION.format(poisoned=s["ai"])},
                    {"role": "assistant", "content": s["real"]},
                ]}, ensure_ascii=False) + "\n")

    cl = sorted(stats["chars"])
    summary = {
        "docs_used": len(ids),
        "samples_total": len(samples),
        "splits": stats["splits"],
        "by_priority": stats["source"],
        "chars": {"median": cl[len(cl) // 2], "p10": cl[int(len(cl) * .1)],
                  "p90": cl[int(len(cl) * .9)], "max": cl[-1]},
        "poison_strength": args.poison_strength,
        "min_chars": args.min_chars,
    }
    (out_dir / "stats.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== 数据集 ===")
    for k, v in summary["splits"].items():
        print(f"  {k:<6} {v['samples']:>5} 条样本 / {v['docs']:>4} 个模组")
    print(f"  来源分布: {summary['by_priority']}")
    print(f"  样本字数: 中位 {summary['chars']['median']} / P90 {summary['chars']['p90']} / 最长 {summary['chars']['max']}")
    print(f"\n输出目录: {out_dir}")
    for f in sorted(out_dir.glob("*.jsonl")):
        print(f"  {f.name:<20} {f.stat().st_size/1024/1024:.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
