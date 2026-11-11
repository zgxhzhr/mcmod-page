#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量判断短页面：一次 API 请求判断 10 条，比单条快 8-10 倍。

判据（与 judge-short.py 一致）：
  X = 剔除：没有新增物品/方块/实体/机制，只是修改原版行为（移除/禁用）、移植、兼容、修Bug、库
  Y = 保留：新增了具体东西，有可展开内容
  Z = 拿不准

用法
----
    python judge-batch.py                 # 全量（自动跳过已判定的）
    python judge-batch.py --batch 10 --workers 12
    python judge-batch.py --limit 100     # 先试 100 条
"""
from __future__ import annotations

import argparse
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib import request as urlreq
from urllib.error import HTTPError, URLError

DATA = Path(r"E:\Mod\百科-语料")
SCAN = DATA / "scan"
XLSX = Path(r"C:\Users\MKIII\Desktop\短页面-待处理.csv.xlsx")
API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

BATCH_PROMPT = """判断以下 {n} 个 MC百科 模组页面「是否需要人工重写介绍」。

核心原则：**只有明确是"减法"或"纯工程"的才剔除；含义模糊的一律保留**。
宁可多留，不可误杀——漏掉一个有内容的模组，比多留一个没内容的代价大。

【X = 剔除（明确没有新增内容）】
必须能从正文明确判断出属于以下之一：
- 明确说"移除/禁用/关闭/隐藏/删除"某原版功能（减法）
- 明确说"修复了 XX Bug"（纯修复）
- 明确说"是 X 的移植版/重置版/分支版/翻译版"，且**没有**任何新增内容的说明
- 明确说"是前置库/Lib/API"，只是给开发者用的接口
- 明确说只调整数值/性能（"燃烧更快""伤害更高"），无新物品
- 明确说"仅实现 X 与 Y 的兼容"（纯兼容补丁，无新增内容）

【Y = 保留（可能或明确有新增内容）】
- 明确说"添加/新增/加入"任何东西（哪怕只说"一些物品"）
- 说"为 X 与 Y 添加了**联动**"（联动往往带新物品/配方）
- 是某个模组的**附属/扩展/内容包**（哪怕短，通常有新增内容）
- 提到了具体物品名/方块名/机制名/数值/数量
- 提到"新方块/新物品/新生物/新机制/新维度/新结构/新配方"

【Z = 待定（信息不足，无法判断）】
- 只有一句话且既没说新增什么、也没说移除/修复/移植
- 描述极其笼统（"一些有趣的内容""增强了游戏体验"）

【关键区分】
- "本模组为农夫乐事与婴儿肥添加了联动" → Y（联动带新内容）
- "实现了群峦传说与冷汗的兼容" → X（纯兼容补丁）
- "移除玩家受伤动画" → X（减法）
- "禁用局域网作弊" → X（减法）
- "修复传送后卡床 Bug" → X（修复）
- "是 X 的 Forge 移植版" → X（未提新增）
- "是 X 的移植版，额外添加 12 种新方块" → Y（有新增）
- "环境科技-发电机" → Y（科技模组的机器，通常有具体内容）
- "让熔炉燃烧速度提升 2 倍" → X（只改参数）
- "添加 50 幅画" → Y
- "为神秘遗物添加两把镰刀" → Y
- "允许像放水和岩浆一样放牛奶" → Y（新流体）
- "一本书展示合成配方" → Y（新物品）
- "xx 作者的 Lib 模组" → X（前置库）

【模组信息】
{items}

【输出】
只输出一个 JSON 对象，results 数组里必须包含全部 {n} 项：
{{"results": [{{"n": 1, "type": "X", "reason": "不超过25字"}}, ...]}}"""


_lock = threading.Lock()
_stat = {"ok": 0, "fail": 0}


def get_keys() -> list[str]:
    keys = []
    for name in ["deepseek-key.txt"] + [f"deepseek-key-{i}.txt" for i in range(2, 10)]:
        f = DATA / name
        if f.exists():
            k = f.read_text(encoding="utf-8").strip()
            if k and k not in keys:
                keys.append(k)
    return keys


def call_api(key: str, prompt: str, max_tokens: int = 900, retries: int = 3) -> str:
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }).encode()
    hdr = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
    opener = urlreq.build_opener(urlreq.ProxyHandler({}))
    last = None
    for i in range(retries):
        try:
            req = urlreq.Request(API_URL, data=body, headers=hdr, method="POST")
            with opener.open(req, timeout=120) as r:
                d = json.loads(r.read())
            return d["choices"][0]["message"]["content"]
        except (HTTPError, URLError, json.JSONDecodeError, KeyError) as e:
            last = e
            time.sleep(1.0 * (i + 1))
    raise RuntimeError(f"{type(last).__name__}")


def parse_verdicts(txt: str, n: int) -> dict[int, dict]:
    """兼容几种返回形状：[{...}] / {"results": [...]}"""
    try:
        d = json.loads(txt)
    except Exception:
        return {}
    items = d if isinstance(d, list) else (d.get("results") or d.get("items") or [])
    out = {}
    if isinstance(items, list):
        for it in items:
            if not isinstance(it, dict):
                continue
            idx = it.get("n") or it.get("index") or it.get("i")
            t = str(it.get("type", "")).strip()[:1].upper()
            if idx is None or t not in ("X", "Y", "Z"):
                continue
            try:
                out[int(idx)] = {"type": t, "reason": str(it.get("reason", ""))[:60]}
            except (TypeError, ValueError):
                continue
    return out


def load_rows() -> list[dict]:
    if XLSX.exists():
        import openpyxl
        wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
        ws = wb[wb.sheetnames[0]]
        out = []
        for r in ws.iter_rows(min_row=2, values_only=True):
            if not r or r[3] is None:
                continue
            out.append({"id": int(r[3]), "name": r[4] or "", "category": r[2] or "",
                        "chars": r[6] or 0, "preview": r[11] or ""})
        wb.close()
        return out
    raise SystemExit("找不到 xlsx")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=10)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-tokens", type=int, default=800)
    ap.add_argument("--out", default=str(SCAN / "short-verdicts.jsonl"))
    args = ap.parse_args()

    rows = load_rows()
    out = Path(args.out)
    done: set[int] = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            try:
                done.add(json.loads(line)["id"])
            except Exception:
                pass
    todo = [r for r in rows if r["id"] not in done]
    if args.limit:
        todo = todo[:args.limit]
    print(f"待判断 {len(rows)}  已完成 {len(done)}  本轮 {len(todo)}  批次 {args.batch}  并发 {args.workers}")

    if not todo:
        print("全部已完成")
        return summarize(out)

    keys = get_keys()
    print(f"使用 {len(keys)} 个 key")
    batches = [todo[i:i + args.batch] for i in range(0, len(todo), args.batch)]
    print(f"共 {len(batches)} 批")

    fout = out.open("a", encoding="utf-8")
    t0 = time.time()
    kcount = [0]

    def work(bi_batch):
        bi, batch = bi_batch
        items = "\n".join(
            f'{i}. id={r["id"]} 《{(r["name"] or "")[:20]}》: {(r["preview"] or "")[:120]}'
            for i, r in enumerate(batch, 1))
        prompt = BATCH_PROMPT.format(n=len(batch), items=items)
        recs = []
        for attempt in range(3):
            with _lock:
                kcount[0] += 1
                key = keys[kcount[0] % len(keys)]
            try:
                txt = call_api(key, prompt, args.max_tokens)
                v = parse_verdicts(txt, len(batch))
                if len(v) >= max(1, len(batch) // 2):
                    for i, r in enumerate(batch, 1):
                        vv = v.get(i)
                        if vv:
                            recs.append({**r, "type": {"X": "A", "Y": "B", "Z": "C"}[vv["type"]],
                                         "reason": vv["reason"]})
                    break
            except Exception:
                time.sleep(1.5 * (attempt + 1))
        with _lock:
            for rec in recs:
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fout.flush()
            if recs:
                _stat["ok"] += len(recs)
            else:
                _stat["fail"] += len(batch)
            n = _stat["ok"]
            if n % 500 == 0 or bi == len(batches):
                el = time.time() - t0
                speed = n / el if el > 0 else 0
                print(f"  {n}/{len(todo)}  {speed:.1f}条/秒  剩余约 {(len(todo)-n)/speed/60:.1f}分" if speed > 0 else "")
        return len(recs)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(work, (i, b)) for i, b in enumerate(batches, 1)]
        for f in as_completed(futs):
            f.result()
    fout.close()
    el = time.time() - t0
    print(f"\n本轮: 成功 {_stat['ok']}  失败 {_stat['fail']}  用时 {el/60:.1f} 分")
    return summarize(out)


def summarize(out: Path) -> int:
    from collections import Counter
    recs = []
    for line in out.read_text(encoding="utf-8").splitlines():
        try:
            recs.append(json.loads(line))
        except Exception:
            pass
    c = Counter(r["type"] for r in recs)
    print(f"\n=== 累计 {len(recs)} 条 ===")
    print(f"  A剔除 {c['A']}   B保留 {c['B']}   C待定 {c['C']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
