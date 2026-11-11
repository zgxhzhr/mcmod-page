#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""判断短页面是否「可剔除」——纯移植/兼容/过于简单，不值得补写。

不靠关键词：让 DeepSeek 逐条判断语义。

用法
----
    python judge-short.py                    # 判断全部（从 xlsx 读）
    python judge-short.py --limit 100        # 先试 100 条
    python judge-short.py --workers 8

输出
----
    E:\\Mod\\百科-语料\\scan\\short-verdicts.jsonl   逐条结果
    E:\\Mod\\百科-语料\\scan\\剔除清单.csv            A+ 类（可直接删）
    E:\\Mod\\百科-语料\\scan\\保留清单.csv            B 类（值得改写）
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib import request as urlreq
from urllib.error import URLError, HTTPError

DATA = Path(r"E:\Mod\百科-语料")
SCAN = DATA / "scan"
XLSX = Path(r"C:\Users\MKIII\Desktop\短页面-待处理.csv.xlsx")

API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-flash"

PROMPT = """判断这个 MC百科 模组页面【有没有值得重写的内容】。

核心问题：**这个模组新增了什么具体的东西吗？**（物品/方块/实体/机制/配方/数值）
没有新增实体内容 = 不值得写介绍，哪怕功能讲得很清楚。

■ X —— 剔除（不值得重写）
  满足任一：
  - 只是**修改原版行为**：移除/禁用/隐藏/关闭某个功能（如"移除受伤动画""禁用局域网作弊"）
  - 只是移植/重置/分支/续作/翻译（不新增内容）
  - 只是兼容补丁/联动（"实现 X 与 Y 兼容"）
  - 只是修复 Bug
  - 只是库/前置/API（给开发者用的接口）
  - 只是调整参数/优化性能（如"让熔炉烧得更快"——只改数值，没新物品）
  - 一句话说完，且没有任何新增物品/方块/机制

■ Y —— 保留（值得重写）
  新增了具体的东西，能展开写：
  - 新物品/装备/工具/食物
  - 新方块/机器/装饰物
  - 新生物/怪物/Boss
  - 新机制系统（如附魔系统、法术体系、能源网络）
  - 新结构/维度/地形
  - 新配方/合成方式（且产出新东西）
  - 有明确数量（"添加 50 幅画""12 种武器"）

■ Z —— 拿不准（信息太少，但可能真有东西）

【关键区分 —— 加法 vs 减法】
- "移除玩家受伤动画" → X（减法，没新东西，写不出 100 字）
- "禁用局域网作弊" → X（减法）
- "让熔炉燃烧速度提升 2 倍" → X（只改参数，无新物品）
- "添加了一个可以跨存档传输物品的袋子" → Y（加法，有具体物品）
- "添加超过 50 幅新画作" → Y（有数量和物品）
- "为神秘遗物添加了两把镰刀武器" → Y（具体物品）
- "允许玩家像放置水和岩浆一样放置牛奶" → Y（**新方块/流体**，属于加法）
- "本模组是 X 的 Forge 移植版" → X
- "本模组是 X 的 Forge 移植版，额外添加了 12 种新方块" → Y（有新增）
- "实现了群峦传说与冷汗的兼容" → X
- "修复传送后卡床的 Bug" → X
- "一本书展示物品合成配方" → Y（新物品：书）
- "用桶装猫并倒出" → Y（新机制 + 可能新物品）

【模组信息】
名称：{name}
正文：
{body}

只输出 JSON：
{{"type": "X 或 Y 或 Z", "reason": "不超过 30 字，说明新增了什么 或 为什么没有新东西"}}"""

_lock = threading.Lock()
_done = [0]


def get_keys() -> list[str]:
    """读取 deepseek-key.txt 与 deepseek-key-2..9.txt，全部轮询使用。"""
    keys = []
    for name in ["deepseek-key.txt"] + [f"deepseek-key-{i}.txt" for i in range(2, 10)]:
        f = DATA / name
        if f.exists():
            k = f.read_text(encoding="utf-8").strip()
            if k and k not in keys:
                keys.append(k)
    return keys


def call_api(key: str, prompt: str, retries: int = 3) -> dict:
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 120,
        "response_format": {"type": "json_object"},
    }).encode()
    hdr = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
    opener = urlreq.build_opener(urlreq.ProxyHandler({}))  # 直连
    last = None
    for i in range(retries):
        try:
            req = urlreq.Request(API_URL, data=body, headers=hdr, method="POST")
            with opener.open(req, timeout=60) as r:
                d = json.loads(r.read())
            txt = d["choices"][0]["message"]["content"]
            return json.loads(txt)
        except (HTTPError, URLError, json.JSONDecodeError, KeyError) as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"API 失败: {last}")


def load_rows(from_xlsx: bool = True) -> list[dict]:
    if from_xlsx and XLSX.exists():
        import openpyxl
        wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
        ws = wb[wb.sheetnames[0]]
        out = []
        for r in ws.iter_rows(min_row=2, values_only=True):
            if not r or r[3] is None:
                continue
            out.append({"seq": r[0], "id": int(r[3]), "name": r[4] or "",
                        "category": r[2] or "", "chars": r[6] or 0,
                        "preview": r[11] or ""})
        wb.close()
        return out
    # 回退：从数据库读
    con = sqlite3.connect(f"file:{DATA/'mcmod.db'}?mode=ro", uri=True, timeout=10)
    rows = list(con.execute("""
        SELECT id,name,COALESCE(category,'未分类'),chars,intro_text
        FROM classes WHERE chars<100
          AND COALESCE(category,'') NOT IN ('LIB','魔改')
        ORDER BY chars, id"""))
    con.close()
    return [{"seq": i, "id": a, "name": b, "category": c, "chars": d,
             "preview": " ".join((e or "").split())} for i, (a, b, c, d, e) in enumerate(rows, 1)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default=str(SCAN / "short-verdicts.jsonl"))
    args = ap.parse_args()

    rows = load_rows()
    print(f"待判断 {len(rows)} 条")

    # 断点续跑
    out = Path(args.out)
    done_ids: set[int] = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            try:
                done_ids.add(json.loads(line)["id"])
            except Exception:
                pass
        print(f"已完成 {len(done_ids)} 条，续跑")
    todo = [r for r in rows if r["id"] not in done_ids]
    if args.limit:
        todo = todo[:args.limit]
    print(f"本轮处理 {len(todo)} 条")

    keys = get_keys()
    print(f"使用 {len(keys)} 个 API key")
    fout = out.open("a", encoding="utf-8")
    _key_i = [0]
    t0 = time.time()

    def work(row):
        p = PROMPT.format(name=row["name"], body=row["preview"][:600])
        with _lock:
            _key_i[0] += 1
            key = keys[_key_i[0] % len(keys)]
        try:
            v = call_api(key, p)
            raw = str(v.get("type", "Z")).strip()[:1].upper()
            rec = {**row, "type": {"X":"A","Y":"B","Z":"C"}.get(raw, "C"),
                   "reason": str(v.get("reason", ""))[:60]}
        except Exception as e:
            rec = {**row, "type": "ERR", "reason": f"{type(e).__name__}"}
        with _lock:
            _done[0] += 1
            n = _done[0]
            if rec["type"] != "ERR":
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fout.flush()
            if n % 100 == 0:
                el = time.time() - t0
                print(f"  {n}/{len(todo)}  类型分布: ", end="")
                print(f"{el:.0f}s")
        return rec

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(work, r) for r in todo]
        for f in as_completed(futs):
            results.append(f.result())
    fout.close()

    # 汇总
    allrecs = []
    for line in out.read_text(encoding="utf-8").splitlines():
        try:
            allrecs.append(json.loads(line))
        except Exception:
            pass
    from collections import Counter
    c = Counter(r["type"] for r in allrecs)
    print(f"\n=== 结果 ===")
    print(f"  已判断 {len(allrecs)} 条")
    for k, n in c.most_common():
        print(f"    {k}: {n}")

    # 导出两份清单
    drop = [r for r in allrecs if r["type"] == "A"]
    keep = [r for r in allrecs if r["type"] == "B"]
    unsure = [r for r in allrecs if r["type"] == "C"]

    def write_csv(path: Path, items: list[dict], cols):
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            for r in sorted(items, key=lambda x: x.get("chars", 0)):
                w.writerow([r.get(c, "") for c in ["id", "name", "category", "chars", "type", "reason"]])

    cols = ["id", "名称", "分类", "字数", "类型", "理由"]
    write_csv(SCAN / "剔除清单.csv", drop, cols)
    write_csv(SCAN / "保留清单.csv", keep, cols)
    write_csv(SCAN / "待定清单.csv", unsure, cols)
    print(f"\n输出:")
    print(f"  剔除 A: {len(drop)} 条 → 剔除清单.csv")
    print(f"  保留 B: {len(keep)} 条 → 保留清单.csv")
    print(f"  待定 C: {len(unsure)} 条 → 待定清单.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
