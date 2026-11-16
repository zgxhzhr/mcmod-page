#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 LLM 通读语料，判断哪些页面可疑（AI 生成 / 空洞 / 营销腔 / 结构问题）。

规则检测器只能抓表面特征，误报率高；语义判断交给模型。
本脚本把每条正文送给 DeepSeek，返回结构化判断，汇总成可疑清单。

用法
----
    python llm-audit.py --ids-file 收藏夹ids.txt
    python llm-audit.py --ids-file fav.txt --workers 8 --limit 100
    python llm-audit.py --resume            # 断点续跑

输出
----
    audit/llm-verdicts.jsonl   每条判断结果
    audit/llm-suspects.md      可疑清单（按分数升序）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

DEFAULT_DATA = Path(r"E:\Mod\百科-语料")
API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-flash"

PROMPT = """你是 MC百科（mcmod.cn）的资深审核编辑。判断下面这篇模组介绍是否【内容空洞】。

【核心判据：区分"提到"和"讲清"】
- **提到**：只说了有这么个东西，但读者照着做不出来 → 属空洞
- **讲清**：说出了具体名称/数量/条件/步骤，读者能照着操作 → 不算空洞

示例：
  ✗ "可以驯服僵尸指挥作战"        → 提到（怎么驯服？用什么道具？有什么条件？）
  ✓ "用僵尸头骨对僵尸右键即可驯服，驯服后按 G 键下达指令" → 讲清
  ✗ "新增许多装饰性方块"          → 提到（哪些方块？）
  ✓ "新增 12 种木纹墙板、4 种石质地板，用工作台合成" → 讲清

【以下统统不构成可疑（人类写作的正常风格）】
营销腔、口号、感叹号、反问句、emoji、抽象词、排比句式、口语化、玩梗、
没有数值（装饰/维度类天然无数字）、短文、停更说明、画廊占位。

【参考案例】

■ 案例 A：**可疑**（AI 生成，通篇"提到"而无一条"讲清"）
"此模组是 You Are The Zombie 的精神延续版本。在这个模组里你将以僵尸阵营身份生存在僵尸、尸壳、溺尸之间随环境变化……你将更频繁地看到阵营冲突在世界中自然发生。整个世界会因为你的亡者身份而改变互动节奏。这使得每一次出行都更像一次战术决策，而不是简单跑图。你可以驯服并指挥僵尸作战，让它们成为你的前排、护卫或火力补充。"
→ 判可疑。理由：虽然提到"驯服僵尸"，但全篇没有说清任何一种 NPC/物品/数值/条件/操作步骤。读者看完不知道怎么驯服、形态怎么转化、军团有几种。

■ 案例 B：**不可疑**（人类写作，短但讲清）
"Revolution 是为喜欢玩僵尸相关游戏的社区创建的一个模组。新增了许多物品，包括武器、杂物。玩家会出生在安全区内，你的使命是去搜刮城市、城镇和更多地方，找到战利品来保护自己。你也可以通过创建队伍并邀请其它玩家加入，来与伙伴合作。"
→ 不可疑。理由："出生在安全区""去搜刮城市""组队合作"三步讲清了玩法流程。

■ 案例 C：**不可疑**（有口号，但数据具体）
"GT3 赛车包将赛车运动的激情带入 MC！车辆包括 梅赛德斯-AMG GT3 EVO：拥有 8 种涂装；保时捷 GT3 R：拥有 6 种独特涂装；法拉利 296GT3：拥有 6 款涂装。"
→ 不可疑。理由：3 款车型 + 各自的涂装数量，数字可查证。

■ 案例 D：**不可疑**（营销腔浓，但有规则说明）
"模组改进锻造机制……现在，物品从零耐久修复到满耐久所需的材料数量与制作该物品所需的材料数量相同，而不是始终为 4。"
→ 不可疑。理由："材料数量 = 制作材料数"这条规则读者能照着用。

【模组信息】
名称：{name}
正文：
{body}

【输出要求】
只输出一个 JSON：
{{"score": 0-100 的整数（100=大量"讲清"，0=全篇"提到"）, "suspect": true 或 false, "reason": "不超过 40 字，指出它讲清了什么 或 缺哪些关键细节"}}"""


def load_key() -> str:
    k = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if k:
        return k
    f = DEFAULT_DATA / "deepseek-key.txt"
    if f.exists():
        return f.read_text(encoding="utf-8").strip()
    raise SystemExit("缺少 API key：设 DEEPSEEK_API_KEY 或写入 deepseek-key.txt")


def call_llm(opener, key: str, name: str, body: str, retries: int = 3) -> dict:
    prompt = PROMPT.format(name=name or "(无名)", body=body[:2500])
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }).encode()
    last = ""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(API_URL, data=payload, headers={
                "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            with opener.open(req, timeout=90) as r:
                j = json.loads(r.read().decode())
            content = j["choices"][0]["message"]["content"] or ""
            if not content.strip():
                raise ValueError("空响应")
            m = re.search(r"\{.*\}", content, re.S)
            if not m:
                raise ValueError(f"无 JSON：{content[:80]}")
            d = json.loads(m.group(0))
            return {
                "score": int(d.get("score", 50)),
                "suspect": bool(d.get("suspect", False)),
                "reason": str(d.get("reason", ""))[:120],
                "tokens": j.get("usage", {}).get("total_tokens", 0),
            }
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode()[:100]}"
            time.sleep(2 * (attempt + 1))
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:100]}"
            time.sleep(1.5 * (attempt + 1))
    return {"score": -1, "suspect": False, "reason": f"失败 {last}", "tokens": 0}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    ap.add_argument("--ids-file", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--min-chars", type=int, default=200)
    ap.add_argument("--out", default="")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    key = load_key()
    data = Path(args.data)
    out_dir = Path(args.out) if args.out else data / "audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    verdict_file = out_dir / "llm-verdicts.jsonl"

    done: dict[int, dict] = {}
    if args.resume and verdict_file.exists():
        for line in verdict_file.read_text(encoding="utf-8").splitlines():
            try:
                d = json.loads(line)
                done[d["id"]] = d
            except Exception:
                pass
        print(f"断点续跑：已有 {len(done)} 条结果")

    ids = [int(x) for x in re.findall(r"\d+", Path(args.ids_file).read_text(encoding="utf-8"))]
    con = sqlite3.connect(f"file:{data/'mcmod.db'}?mode=ro", uri=True, timeout=10)
    ph = ",".join("?" * len(ids))
    rows = list(con.execute(
        f"SELECT id,name,chars,intro_text FROM classes WHERE id IN ({ph}) AND chars>=?",
        (*ids, args.min_chars)))
    con.close()

    todo = [r for r in rows if r[0] not in done]
    if args.limit:
        todo = todo[: args.limit]
    print(f"待判断 {len(todo)} 条（共 {len(rows)} 条符合字数要求），并发 {args.workers}")

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 直连，不走系统代理
    lock = threading.Lock()
    counter = {"done": 0, "fail": 0, "tokens": 0}
    t0 = time.time()

    with verdict_file.open("a" if args.resume else "w", encoding="utf-8") as fout, \
         ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(call_llm, opener, key, r[1], r[3]): r for r in todo}
        for fut in as_completed(futs):
            r = futs[fut]
            res = fut.result()
            rec = {"id": r[0], "name": r[1], "chars": r[2], **res}
            with lock:
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fout.flush()
                counter["done"] += 1
                if res["score"] < 0:
                    counter["fail"] += 1
                counter["tokens"] += res.get("tokens", 0)
                n = counter["done"]
            if n % 50 == 0:
                el = time.time() - t0
                print(f"  {n}/{len(todo)}  {n/el:.1f} 条/秒  失败 {counter['fail']}  tokens {counter['tokens']:,}", flush=True)

    # 汇总
    all_recs = [json.loads(l) for l in verdict_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    all_recs = [r for r in all_recs if r["score"] >= 0]
    all_recs.sort(key=lambda x: x["score"])
    suspects = [r for r in all_recs if r["suspect"]]

    md = ["# LLM 通读结果：可疑页面清单", "",
          f"- 判断总数：**{len(all_recs)}** 条",
          f"- 疑似可疑：**{len(suspects)}** 条（{len(suspects)/max(len(all_recs),1)*100:.1f}%）",
          f"- 模型：{MODEL}　token 消耗：{counter['tokens']:,}", "",
          "## 可疑清单（分数升序，越低越可疑）", "",
          "| 分数 | id | 名称 | 字数 | 理由 | 链接 |", "|---|---|---|---|---|---|"]
    for r in suspects:
        md.append(f"| {r['score']} | {r['id']} | {(r['name'] or '')[:18]} | {r['chars']} | "
                  f"{r['reason']} | [打开](https://www.mcmod.cn/class/{r['id']}.html) |")
    md += ["", "## 分数分布", "", "| 区间 | 条数 |", "|---|---|"]
    for lo, hi in [(0, 40), (40, 60), (60, 80), (80, 90), (90, 101)]:
        n = sum(1 for r in all_recs if lo <= r["score"] < hi)
        md.append(f"| {lo}–{hi-1} | {n} |")

    rp = out_dir / "llm-suspects.md"
    rp.write_text("\n".join(md), encoding="utf-8")

    print(f"\n完成 {counter['done']} 条，失败 {counter['fail']}，tokens {counter['tokens']:,}")
    print(f"可疑 {len(suspects)} 条 / 共 {len(all_recs)} 条")
    print(f"输出：{rp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
