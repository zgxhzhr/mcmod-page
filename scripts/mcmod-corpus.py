#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MC百科模组介绍语料抓取器。

用途
----
批量抓取 https://www.mcmod.cn/class/<id>.html 的模组介绍正文，存成本地语料，
用于学习「百科介绍该怎么写」（段落结构、章节结构、开头句、句长、常用句式）。

子命令
------
    python mcmod-corpus.py ids                       # 从 sitemap 取全部有效 class id
    python mcmod-corpus.py crawl --limit 5000        # 抓取（断点续爬）
    python mcmod-corpus.py export --min-chars 800    # 导出 jsonl + 一本 md
    python mcmod-corpus.py stats                     # 基础统计（字数/浏览量分布）

礼貌与合规
----------
- robots.txt 只禁止 /class/add/ /class/edit/ 等编辑路径，/class/<id>.html 允许抓取；
- 默认限速 1.2~1.6 秒/页（带随机抖动），遇 429/503 自动退避；
- 只抓公开页面，不登录、不改动站点任何内容；
- 抓下来的正文仅作本机语料分析，不要再发布到别处（版权归百科与原作者）。

页面结构要点
------------
- 正文容器：div.class-menu-main（冒号后的 .menu-min 那个是分类菜单，要排除）
- 章节标题：span/div 的 class 含 common-text-title-N，N = 标题级别（1~4）
- 浏览量：div.class-info-right 文本里的「XX万总浏览」「昨日指数: N」
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path

from lxml import html as lhtml

BASE = "https://www.mcmod.cn"
SITEMAP = f"{BASE}/sitemap1.xml"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

DEFAULT_DATA = Path(r"E:\Mod\百科-语料")

COLUMNS = ["id", "name", "short_name", "en", "status", "source", "env",
           "views", "idx", "chars", "n_paras", "n_tables", "n_lists", "n_imgs",
           "n_headings", "headings", "intro_html", "intro_text",
           "fetched_at", "http_status", "error"]

SCHEMA = f"CREATE TABLE IF NOT EXISTS classes ({', '.join(c + (' INTEGER PRIMARY KEY' if c == 'id' else '') for c in COLUMNS)});"
EXTRA_COLUMNS = [("views", "TEXT"), ("idx", "TEXT"), ("n_paras", "INTEGER"),
                 ("n_tables", "INTEGER"), ("n_lists", "INTEGER"), ("n_imgs", "INTEGER"),
                 ("n_headings", "INTEGER"), ("headings", "TEXT")]


# ---------------------------------------------------------------- 网络

def fetch(url: str, timeout: int = 30) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            enc = r.headers.get_content_charset() or "utf-8"
            return r.status, raw.decode(enc, errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""


# ---------------------------------------------------------------- 数据库

def db(data_dir: Path) -> sqlite3.Connection:
    data_dir.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(data_dir / "mcmod.db")
    con.execute(SCHEMA.replace("id INTEGER PRIMARY KEY,", "id INTEGER PRIMARY KEY,"))
    have = {r[1] for r in con.execute("PRAGMA table_info(classes)")}
    for col, typ in EXTRA_COLUMNS:
        if col not in have:
            con.execute(f"ALTER TABLE classes ADD COLUMN {col} {typ}")
    con.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
    con.commit()
    return con


# ---------------------------------------------------------------- 解析

def txt(node) -> str:
    if node is None:
        return ""
    return " ".join((node.text_content() or "").split())


def parse_class(html_text: str) -> dict:
    d = {k: "" for k in ("name", "short_name", "en", "status", "source", "env", "views", "idx")}
    d.update({"chars": 0, "n_paras": 0, "n_tables": 0, "n_lists": 0,
              "n_imgs": 0, "n_headings": 0, "headings": "[]",
              "intro_html": "", "intro_text": ""})
    try:
        doc = lhtml.fromstring(html_text)
    except Exception:
        return d

    def one(xp):
        r = doc.xpath(xp)
        return txt(r[0]) if r else ""

    d["name"] = one('//div[contains(@class,"class-title")]//h3')
    d["en"] = one('//div[contains(@class,"class-title")]//h4')
    d["short_name"] = one('//span[contains(@class,"short-name")]')
    d["status"] = one('//div[contains(@class,"class-status")]')
    d["source"] = one('//div[contains(@class,"class-source")]')

    left = one('//div[contains(@class,"class-info-left")]')
    m = re.search(r"运行环境[:：]\s*([^收编最相]+)", left)
    if m:
        d["env"] = m.group(1).strip()

    right = one('//div[contains(@class,"class-info-right")]')
    m = re.search(r"([\d.]+万?)总浏览", right.replace(" ", ""))
    if m:
        d["views"] = m.group(1)
    m = re.search(r"昨日指数[:：]\s*(\d+)", right.replace(" ", ""))
    if m:
        d["idx"] = m.group(1)

    body = doc.xpath('//div[contains(@class,"class-menu-main") and not(contains(@class,"menu-min"))]')
    if not body:
        return d
    node = body[0]

    # 列表/表格/图片在删除 tab 条之前统计
    d["n_tables"] = len(node.xpath('.//table'))
    d["n_lists"] = len(node.xpath('.//ul | .//ol'))
    d["n_imgs"] = len(node.xpath('.//img'))

    # 章节标题（common-text-title-N）
    heads = []
    for el in node.xpath('.//*[contains(@class,"common-text-title")]'):
        cls = el.get("class") or ""
        mm = re.search(r"common-text-title-(\d)", cls)
        lvl = int(mm.group(1)) if mm else 1
        t = txt(el)
        if t:
            heads.append(f"h{lvl}:{t[:40]}")
    d["headings"] = json.dumps(heads, ensure_ascii=False)
    d["n_headings"] = len(heads)

    for bad in node.xpath('.//*[contains(@class,"page-ul") or contains(@class,"class-edit-block")]'):
        bad.getparent().remove(bad)

    parts = []
    paras = 0
    for el in node.iter():
        if not isinstance(el.tag, str):
            continue
        if el.tag == "p":
            paras += 1
        if el.tag in ("p", "h1", "h2", "h3", "h4", "li", "td", "th"):
            t = txt(el)
            if t:
                parts.append(t)
    d["n_paras"] = paras
    d["intro_text"] = "\n".join(parts).strip()
    d["chars"] = len(d["intro_text"].replace("\n", ""))
    d["intro_html"] = lhtml.tostring(node, encoding="unicode", method="html").strip()
    return d


# ---------------------------------------------------------------- 子命令

def cmd_ids(args) -> int:
    data = Path(args.data)
    print(f"读取 sitemap: {SITEMAP}")
    code, t = fetch(SITEMAP, timeout=60)
    if code != 200 or not t:
        print(f"  sitemap 获取失败 HTTP {code}")
        return 1
    ids = sorted({int(x) for x in re.findall(r"/class/(\d+)\.html", t)})
    p = data / "ids.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(map(str, ids)) + "\n", encoding="utf-8")
    print(f"  有效 class id: {len(ids)} 个（{ids[0]} ~ {ids[-1]}）→ {p}")
    return 0


def cmd_crawl(args) -> int:
    data = Path(args.data)
    ids_file = data / "ids.txt"
    if not ids_file.exists():
        print("先跑 ids 子命令")
        return 1
    all_ids = [int(x) for x in ids_file.read_text(encoding="utf-8").split()]
    con = db(data)
    done = {r[0] for r in con.execute("SELECT id FROM classes")}
    todo = [i for i in all_ids if i not in done]
    if args.only_id:
        todo = args.only_id
    if args.max_id:
        todo = [i for i in todo if i <= args.max_id]
    if args.limit:
        todo = todo[: args.limit]
    if not todo:
        print("没有待抓的 id")
        return 0

    print(f"待抓 {len(todo)} 个（库中已有 {len(done)}，sitemap 共 {len(all_ids)}）")
    ok = empty = fail = 0
    t0 = time.time()
    sql = f"INSERT OR REPLACE INTO classes ({','.join(COLUMNS)}) VALUES ({','.join('?' * len(COLUMNS))})"
    for n, cid in enumerate(todo, 1):
        url = f"{BASE}/class/{cid}.html"
        code, page = 0, ""
        for attempt in range(3):
            try:
                code, page = fetch(url)
            except Exception:
                code, page = 0, ""
            if code == 200:
                break
            if code in (429, 503):
                time.sleep(8 * (attempt + 1))
                continue
            break

        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        if code == 200 and page:
            d = parse_class(page)
            if d["chars"] < 100:
                empty += 1
                err = "empty"
            else:
                ok += 1
                err = None
            row = [cid, d["name"], d["short_name"], d["en"], d["status"], d["source"], d["env"],
                   d["views"], d["idx"], d["chars"], d["n_paras"], d["n_tables"], d["n_lists"],
                   d["n_imgs"], d["n_headings"], d["headings"], d["intro_html"], d["intro_text"],
                   now, code, err]
            tag = f"{d['chars']}字 {d['views'] or '?'}浏览"
        else:
            fail += 1
            row = [cid] + [""] * 9 + [0, 0, 0, 0, 0, 0, "[]", "", "", now, code, f"HTTP {code}"]
            # 列数对齐
            row = [cid, "", "", "", "", "", "", "", "", 0, 0, 0, 0, 0, 0, "[]", "", "", now, code, f"HTTP {code}"]
            tag = f"失败 HTTP {code}"
        con.execute(sql, row)
        con.commit()

        if n % 25 == 0 or n == len(todo):
            el = time.time() - t0
            rate = n / el if el else 0
            eta = (len(todo) - n) / rate / 60 if rate else 0
            print(f"  [{n}/{len(todo)}] id={cid} {tag} | 成功 {ok} 空 {empty} 失败 {fail} "
                  f"| {rate:.2f}页/秒 剩 {eta:.0f}分", flush=True)

        if n < len(todo):
            time.sleep(args.delay + random.uniform(0, 0.4))
    con.close()
    print(f"\n本轮：成功 {ok}，空/过短 {empty}，失败 {fail}")
    return 0


def cmd_export(args) -> int:
    data = Path(args.data)
    con = db(data)
    rows = list(con.execute(
        "SELECT id,name,en,status,env,views,chars,n_headings,headings,intro_text "
        "FROM classes WHERE chars >= ? ORDER BY chars DESC", (args.min_chars,)))
    con.close()
    if not rows:
        print("没有可导出的数据")
        return 1
    out = data / "corpus"
    out.mkdir(exist_ok=True)

    jl = out / "corpus.jsonl"
    with jl.open("w", encoding="utf-8") as f:
        for cid, name, en, st, env, views, chars, nh, heads, body in rows:
            f.write(json.dumps({
                "id": cid, "name": name, "en": en, "status": st, "env": env,
                "views": views, "chars": chars, "n_headings": nh,
                "headings": json.loads(heads or "[]"), "text": body,
                "url": f"{BASE}/class/{cid}.html",
            }, ensure_ascii=False) + "\n")

    md = out / "corpus.md"
    with md.open("w", encoding="utf-8") as f:
        f.write(f"# MC百科模组介绍语料（{len(rows)} 条，每条 ≥{args.min_chars} 字）\n")
        for cid, name, en, st, env, views, chars, nh, heads, body in rows:
            f.write(f"\n---\n\n## [{cid}] {name}　{en}\n\n")
            f.write(f"> {chars} 字 · {views or '?'} 浏览 · {st or '—'} · {env or '—'} · {nh} 个小标题\n\n")
            if nh:
                hs = [h.split(":", 1)[1] for h in json.loads(heads or "[]")]
                f.write("小标题：" + " / ".join(hs[:10]) + "\n\n")
            f.write(body.strip() + "\n")

    lens = sorted(r[6] for r in rows)
    print(f"导出 {len(rows)} 条")
    print(f"  {jl}  ({jl.stat().st_size/1024/1024:.2f} MB)")
    print(f"  {md}  ({md.stat().st_size/1024/1024:.2f} MB)")
    print(f"  字数：中位 {lens[len(lens)//2]} / 最短 {lens[0]} / 最长 {lens[-1]}")
    return 0


def cmd_stats(args) -> int:
    con = db(Path(args.data))
    n, = con.execute("SELECT COUNT(*) FROM classes WHERE chars>0").fetchone()
    print(f"有效条数: {n}")
    if not n:
        return 0
    for label, sql in [
        ("字数分布", "SELECT chars FROM classes WHERE chars>0 ORDER BY chars"),
        ("小标题数", "SELECT n_headings FROM classes WHERE chars>0 ORDER BY n_headings"),
        ("段落数", "SELECT n_paras FROM classes WHERE chars>0 ORDER BY n_paras"),
    ]:
        vals = [r[0] for r in con.execute(sql)]
        p = lambda q: vals[min(len(vals) - 1, int(len(vals) * q))]
        print(f"  {label}: 中位 {p(.5)} / P10 {p(.1)} / P90 {p(.9)} / 最大 {vals[-1]}")
    print(f"  id 范围: {con.execute('SELECT MIN(id),MAX(id) FROM classes').fetchone()}")
    con.close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="MC百科模组介绍语料抓取器")
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ids")
    p = sub.add_parser("crawl")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--delay", type=float, default=1.2)
    p.add_argument("--max-id", type=int, default=0, help="只抓 id 小于等于该值的（时间老的）")
    p.add_argument("--only-id", type=int, nargs="*")
    e = sub.add_parser("export")
    e.add_argument("--min-chars", type=int, default=800)
    sub.add_parser("stats")
    args = ap.parse_args()
    return {"ids": cmd_ids, "crawl": cmd_crawl, "export": cmd_export, "stats": cmd_stats}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
