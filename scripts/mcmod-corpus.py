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
import http.client
import json
import random
import re
import socket
import ssl
import sqlite3
import threading
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


class SocksHTTPSConnection(http.client.HTTPSConnection):
    """走 SOCKS5 的 HTTPS 长连接（手动握手，不依赖 PySocks）。

    背景：国内加速器/代理多是 SOCKS5 端口（如 1080），而 Windows 系统代理
    和 Python urllib 只认 HTTP 代理，所以“开了代理却仍然走真实 IP”是常态。
    这里直接对 socket 做 SOCKS5 CONNECT，再在其上包 TLS。
    """

    def __init__(self, host, port=443, proxy=("127.0.0.1", 1080), timeout=40):
        super().__init__(host, port, timeout=timeout)
        self.proxy = proxy

    def connect(self):
        s = socket.create_connection(self.proxy, self.timeout)
        s.settimeout(self.timeout)
        s.sendall(b"\x05\x01\x00")
        if s.recv(2) != b"\x05\x00":
            raise OSError("SOCKS5 握手失败")
        hb = self.host.encode()
        s.sendall(b"\x05\x01\x00\x03" + bytes([len(hb)]) + hb + self.port.to_bytes(2, "big"))
        resp = s.recv(10)
        if len(resp) < 2 or resp[1] != 0:
            raise OSError(f"SOCKS5 连接失败 {resp.hex()}")
        self.sock = ssl.create_default_context().wrap_socket(s, server_hostname=self.host)


class Banned(Exception):
    """站点防火墙永久封禁页（换 IP 才解）。"""


class VerifyRequired(Exception):
    """站点安全验证页（过验证 / 更新 Cookie 即可）。"""


class Session:
    """单线程复用的 HTTPS 长连接（可走 SOCKS5）。

    实测（2026-11）：
    - 直连：urllib 每页新建 TLS 约 0.51 s，长连接约 0.12 s（差 4 倍）
    - 代理：SOCKS5 长连接可复用隧道，避免每次重新握手
    """

    def __init__(self, host: str = "www.mcmod.cn", timeout: int = 40, proxy: str = "",
                 cookie: str = ""):
        self.host = host
        self.timeout = timeout
        self.proxy = proxy
        self.cookie = cookie
        self.conn = None

    def _new(self):
        # 硬保护：抓 mcmod 时禁止无代理直连，避免暴露本机真实 IP
        if not self.proxy and self.host.endswith("mcmod.cn"):
            raise RuntimeError("禁止直连抓取 mcmod.cn（会暴露本机真实 IP），请配置 --proxy")
        if self.proxy:
            ph, pp = self.proxy.split(":")
            return SocksHTTPSConnection(self.host, 443, (ph, int(pp)), self.timeout)
        return http.client.HTTPSConnection(self.host, 443, timeout=self.timeout)

    def get(self, path: str) -> tuple[int, str]:
        if self.conn is None:
            self.conn = self._new()
        try:
            headers = {
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Connection": "keep-alive",
            }
            if self.cookie:
                headers["Cookie"] = self.cookie
            self.conn.request("GET", path, headers=headers)
            r = self.conn.getresponse()
            body = r.read()
            status = r.status
            if r.will_close:
                self.conn.close()
                self.conn = None
            enc = r.headers.get_content_charset() or "utf-8"
            text = body.decode(enc, errors="replace")
            if "已被系统封禁" in text:
                raise Banned("站点防火墙封禁（换 IP 或等解封）")
            if status == 403 or "安全验证" in text[:3000]:
                raise VerifyRequired("站点要求安全验证（更新 Cookie 或过验证）")
            return status, text
        except Banned:
            raise
        except Exception:
            try:
                if self.conn:
                    self.conn.close()
            except Exception:
                pass
            self.conn = None
            raise

    def close(self):
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass
        self.conn = None


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

    # 只收「叶子块」：<li><p>x</p></li> 这种结构若同时收 li 与 p，正文会重复两遍
    BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "li", "td", "th", "div", "table", "tr", "ul", "ol", "pre"}
    LEAF_TAGS = {"p", "h1", "h2", "h3", "h4", "pre"}
    parts: list = []
    paras = 0

    def walk(el):
        nonlocal paras
        for c in el:
            if not isinstance(c.tag, str):
                continue
            if c.tag in LEAF_TAGS:
                if c.tag == "p":
                    paras += 1
                t = txt(c)
                if t:
                    parts.append(t)
            elif c.tag in ("li", "td", "th"):
                if any(isinstance(x.tag, str) and x.tag in BLOCK_TAGS for x in c):
                    walk(c)
                else:
                    t = txt(c)
                    if t:
                        parts.append(t)
            else:
                walk(c)

    walk(node)

    # 相邻重复段去重（解析重复的典型表现）
    dedup: list = []
    for piece in parts:
        if dedup and (piece == dedup[-1] or (len(piece) > 20 and piece in dedup[-1])):
            continue
        dedup.append(piece)
    parts = dedup
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
    """多线程并发抓取。每个线程独占一个 sqlite 连接，写库串行化（WAL + timeout）。"""
    data = Path(args.data)
    ids_file = data / "ids.txt"
    if not ids_file.exists():
        print("先跑 ids 子命令")
        return 1
    all_ids = [int(x) for x in ids_file.read_text(encoding="utf-8").split()]

    # 主连接负责读已有 id 和最终统计；WAL 模式让只读进度查询不被阻塞
    con0 = db(data)
    con0.execute("PRAGMA journal_mode=WAL")
    # 空页（error=empty）允许重抓一次；empty2 表示重抓后仍空，永久跳过
    # 注：error=empty 允许重抓一次；http_status=0（请求失败）也允许重抓
    done = {r[0] for r in con0.execute(
        "SELECT id FROM classes WHERE (error IS NULL OR error NOT IN ('empty')) "
        "AND (http_status IS NULL OR http_status <> 0)")}
    con0.close()

    todo = [i for i in all_ids if i not in done]
    if args.ids_file:
        fp = Path(args.ids_file)
        if not fp.exists():
            print(f"!! ids 文件不存在：{fp}")
            return 5
        todo = [int(x) for x in re.findall(r"\d+", fp.read_text(encoding="utf-8"))]
        # 文件里是完整 URL 也能解析
        print(f"从 {fp.name} 读到 {len(todo)} 个 id")
    elif args.only_id:
        todo = args.only_id
    if args.max_id:
        todo = [i for i in todo if i <= args.max_id]
    if args.limit:
        todo = todo[: args.limit]
    if not todo:
        print("没有待抓的 id")
        return 0

    # 载入 Cookie（过验证后导出，用于绕过 WAF 安全验证）
    cookie_str = ""
    if args.cookie_file:
        cf = Path(args.cookie_file)
        if cf.exists():
            cookie_str = cf.read_text(encoding="utf-8").strip()
            print(f"已载入 Cookie：{len(cookie_str)} 字符（{cf.name}）")
        else:
            print(f"!! Cookie 文件不存在：{cf}")
    args.cookie_str = cookie_str

    # ---- 启动自检：必须走代理，且代理链路与站点都可用 ----
    if not args.proxy:
        print("!! 拒绝启动：未指定 --proxy。抓取 mcmod 必须走代理，否则会暴露本机真实 IP。")
        print("   如确需直连（不推荐），请显式加 --allow-direct。")
        if not getattr(args, "allow_direct", False):
            return 2
    else:
        print("启动自检：")
        try:
            chk = Session(host="myip.ipip.net", proxy=args.proxy, cookie=args.cookie_str, timeout=20)
            _, ip_text = chk.get("/")
            chk.close()
            ip_line = " ".join(ip_text.split())[:90]
            print(f"  代理出口 IP：{ip_line}")
        except Exception as e:
            print(f"  !! 代理不可用：{e}")
            print("  请检查爱加速是否运行、端口是否正确（默认 127.0.0.1:1080）。")
            return 3
        try:
            chk2 = Session(proxy=args.proxy, cookie=args.cookie_str, timeout=25)
            code, body = chk2.get("/class/1.html")
            chk2.close()
            if code != 200:
                print(f"  !! 站点自检异常：HTTP {code}")
                return 4
            print(f"  站点自检通过：HTTP {code}，{len(body)//1024} KB")
        except Exception as e:
            print(f"  !! 站点自检失败：{type(e).__name__} {str(e)[:80]}")
            return 4

    workers = max(1, args.workers)
    print(f"待抓 {len(todo)} 个（库中已有 {len(done)}，sitemap 共 {len(all_ids)}）")
    print(f"并发 {workers} 线程，每线程间隔 {args.delay}s，全局上限 {args.max_qps} 条/秒，"
          f"代理 {args.proxy or '直连'}")

    lock = threading.Lock()
    counters = {"ok": 0, "empty": 0, "fail": 0, "done": 0, "ban": 0, "streak": 0}
    # 全局限速令牌：保证总速率不超过 max_qps
    min_interval = 1.0 / args.max_qps if args.max_qps > 0 else 0.0
    next_slot = [time.time()]
    stop = threading.Event()
    t0 = time.time()

    sql = (f"INSERT OR REPLACE INTO classes ({','.join(COLUMNS)}) "
           f"VALUES ({','.join('?' * len(COLUMNS))})")

    def wait_slot():
        """全局节拍：所有线程排队取时间片，避免瞬时并发过高。"""
        if min_interval <= 0:
            return
        with lock:
            now = time.time()
            if next_slot[0] < now:
                next_slot[0] = now
            slot = next_slot[0]
            next_slot[0] = slot + min_interval
        delay = slot - time.time()
        if delay > 0:
            time.sleep(delay)

    def worker(chunk):
        sess = Session(proxy=args.proxy, cookie=args.cookie_str)
        con = db(data)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=8000")
        for cid in chunk:
            if stop.is_set():
                break
            wait_slot()
            code, page, err = 0, "", ""
            for attempt in range(3):
                try:
                    code, page = sess.get(f"/class/{cid}.html")
                except Banned as e:
                    if not stop.is_set():
                        print(f"\n!! 检测到封禁页（{e}），立即停止所有线程", flush=True)
                    stop.set()
                    with lock:
                        counters["ban"] = counters.get("ban", 0) + 1
                    break
                except VerifyRequired as e:
                    if not stop.is_set():
                        print(f"\n!! {e}，立即停止所有线程", flush=True)
                        print("   处理：跑 verify-and-get-cookie.py 重新过验证，再用 --cookie-file 重试", flush=True)
                    stop.set()
                    with lock:
                        counters["ban"] = counters.get("ban", 0) + 1
                    break
                except Exception as e:
                    code, page = 0, ""
                    err = str(e)[:120]
                if code == 200:
                    break
                if code in (429, 503):
                    time.sleep(6 * (attempt + 1))
                    continue
                break

            now = time.strftime("%Y-%m-%dT%H:%M:%S")
            if code == 200 and page:
                d = parse_class(page)
                if d["chars"] < 20:
                    # 第一次空页记 empty（下次重抓），第二次仍空记 empty2（放弃）
                    prev = con.execute("SELECT error FROM classes WHERE id=?", (cid,)).fetchone()
                    err = "empty2" if prev and prev[0] == "empty" else "empty"
                    row = [cid, d["name"], d["short_name"], d["en"], d["status"], d["source"],
                           d["env"], d["views"], d["idx"], d["chars"], d["n_paras"],
                           d["n_tables"], d["n_lists"], d["n_imgs"], d["n_headings"],
                           d["headings"], d["intro_html"], d["intro_text"], now, code, err]
                    with lock:
                        counters["empty"] += 1
                elif d["chars"] < 100:
                    # 20~99 字：页面拿到了，但内容太短，对语料无价值，标记为 short 保留
                    err = "short"
                    row = [cid, d["name"], d["short_name"], d["en"], d["status"], d["source"],
                           d["env"], d["views"], d["idx"], d["chars"], d["n_paras"],
                           d["n_tables"], d["n_lists"], d["n_imgs"], d["n_headings"],
                           d["headings"], d["intro_html"], d["intro_text"], now, code, err]
                    with lock:
                        counters["empty"] += 1
                else:
                    err = ""
                    row = [cid, d["name"], d["short_name"], d["en"], d["status"], d["source"],
                           d["env"], d["views"], d["idx"], d["chars"], d["n_paras"],
                           d["n_tables"], d["n_lists"], d["n_imgs"], d["n_headings"],
                           d["headings"], d["intro_html"], d["intro_text"], now, code, None]
                    with lock:
                        counters["ok"] += 1
            else:
                row = [cid, "", "", "", "", "", "", "", "", 0, 0, 0, 0, 0, 0,
                       "[]", "", "", now, code, f"HTTP {code}"]
                with lock:
                    counters["fail"] += 1

            for _ in range(3):
                try:
                    con.execute(sql, row)
                    con.commit()
                    break
                except sqlite3.OperationalError:
                    time.sleep(0.8)
            with lock:
                counters["done"] += 1
                # 连续失败熔断：连续 12 次拿不到页面，说明代理/站点异常，停止
                if code == 200 and page:
                    counters["streak"] = 0
                else:
                    counters["streak"] = counters.get("streak", 0) + 1
                    if counters["streak"] >= 12 and not stop.is_set():
                        print(f"\n!! 连续 {counters['streak']} 次请求失败，疑似代理断开或站点异常，停止", flush=True)
                        stop.set()
                n = counters["done"]
                if n % 25 == 0 or n == len(todo):
                    el = time.time() - t0
                    rate = n / el if el else 0
                    eta = (len(todo) - n) / rate / 60 if rate else 0
                    print(f"  [{n}/{len(todo)}] 成功 {counters['ok']} 空 {counters['empty']} "
                          f"失败 {counters['fail']} | {rate:.2f}条/秒 剩 {eta:.0f}分", flush=True)
            if args.delay:
                time.sleep(args.delay + random.uniform(0, 0.25))
        sess.close()
        con.close()

    # 轮转发牌，让 id 小的先抓
    chunks = [todo[k::workers] for k in range(workers)]
    threads = [threading.Thread(target=worker, args=(c,), daemon=True) for c in chunks if c]
    try:
        for th in threads:
            th.start()
        for th in threads:
            th.join()
    except KeyboardInterrupt:
        stop.set()
        print("\n已中断，正在收尾…")
        for th in threads:
            th.join(timeout=5)

    print(f"\n本轮：成功 {counters['ok']}，空/过短 {counters['empty']}，失败 {counters['fail']}")
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
    p.add_argument("--proxy", default="", help="SOCKS5 代理 host:port（如 127.0.0.1:1080），留空为直连")
    p.add_argument("--cookie-file", default="", help="Cookie 文件（如 E:\\Mod\\百科-语料\\cookie-header.txt）")
    p.add_argument("--allow-direct", action="store_true", help="允许直连（危险：暴露本机真实 IP）")
    p.add_argument("--workers", type=int, default=2, help="并发线程数（默认 2，保守）")
    p.add_argument("--max-qps", type=float, default=1.0, help="全局每秒最多请求数（默认 1.0，保守）")
    p.add_argument("--only-id", type=int, nargs="*")
    p.add_argument("--ids-file", default="", help="id 列表文件（每行一个 id，或含 /class/N.html 的 URL 列表）")
    e = sub.add_parser("export")
    e.add_argument("--min-chars", type=int, default=800)
    sub.add_parser("stats")
    args = ap.parse_args()
    return {"ids": cmd_ids, "crawl": cmd_crawl, "export": cmd_export, "stats": cmd_stats}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
