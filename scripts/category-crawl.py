#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓 MC百科 的模组分类（科技/魔法/冒险/农业/装饰/实用/辅助/魔改/LIB）。

分类页 URL 形如 /class/category/<分类id>-<页码>.html，每页约 44 个模组。
9 个分类合计约 700-900 页，比抓 32,000 个正文页便宜 40 倍。

用法
----
    python category-crawl.py                    # 全抓
    python category-crawl.py --only 1 7 21      # 只抓指定分类（1=科技 7=LIB 21=魔改）
    python category-crawl.py --resume           # 断点续抓

输出
----
    E:\Mod\百科-语料\category-map.json    {id: [分类名...]}
    终端打印统计
"""
from __future__ import annotations

import argparse
import json
import socket
import ssl
import http.client
import re
import threading
import time
from pathlib import Path

DATA = Path(r"E:\Mod\百科-语料")
HOST = "www.mcmod.cn"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
PROXY = ("127.0.0.1", 1080)

CATEGORIES = {
    1: "科技", 2: "魔法", 3: "冒险", 4: "农业", 5: "装饰",
    7: "LIB", 21: "魔改", 23: "实用", 24: "辅助",
}


class SocksHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, port=443, timeout=40):
        super().__init__(host, port, timeout=timeout)

    def connect(self):
        s = socket.create_connection(PROXY, self.timeout)
        s.settimeout(self.timeout)
        s.sendall(b"\x05\x01\x00")
        if s.recv(2) != b"\x05\x00":
            raise OSError("SOCKS5 握手失败")
        hb = self.host.encode()
        s.sendall(b"\x05\x01\x00\x03" + bytes([len(hb)]) + hb + self.port.to_bytes(2, "big"))
        r = s.recv(10)
        if len(r) < 2 or r[1] != 0:
            raise OSError("SOCKS5 CONNECT 失败")
        self.sock = ssl.create_default_context().wrap_socket(s, server_hostname=self.host)


def load_cookie() -> str:
    f = DATA / "cookie-header.txt"
    return f.read_text(encoding="utf-8").strip() if f.exists() else ""


def fetch(conn, path: str, cookie: str) -> tuple[int, str]:
    """每次新建连接：分类页请求量小，连接开销可忽略，但能避免 keep-alive 卡死。"""
    h = {"User-Agent": UA, "Accept": "text/html", "Connection": "close"}
    if cookie:
        h["Cookie"] = cookie
    c = SocksHTTPSConnection(HOST)
    try:
        c.request("GET", path, headers=h)
        r = c.getresponse()
        body = r.read().decode("utf-8", "ignore")
        return r.status, body
    finally:
        try:
            c.close()
        except Exception:
            pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, nargs="*", default=[], help="只抓指定分类 id")
    ap.add_argument("--delay", type=float, default=1.0, help="每页间隔秒数")
    ap.add_argument("--max-pages", type=int, default=3000, help="每分类最大页数（安全上限）")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--out", default=str(DATA / "category-map.json"))
    args = ap.parse_args()

    cookie = load_cookie()
    out = Path(args.out)
    state_file = out.with_suffix(".state.json")

    mapping: dict[str, list[str]] = {}
    done: dict[str, int] = {}   # {分类id: 已抓到的最大页码}
    if args.resume and out.exists():
        mapping = json.loads(out.read_text(encoding="utf-8"))
    if args.resume and state_file.exists():
        done = json.loads(state_file.read_text(encoding="utf-8"))

    targets = args.only or list(CATEGORIES.keys())
    print(f"目标分类: {[(c, CATEGORIES[c]) for c in targets]}")
    print(f"已抓页码: {done}")

    conn = SocksHTTPSConnection(HOST)
    ok_pages = 0
    fail_pages = 0
    t0 = time.time()

    for cid in targets:
        cat_name = CATEGORIES[cid]
        start = done.get(str(cid), 0) + 1
        print(f"\n=== {cat_name}（从第 {start} 页开始）===")
        page = start
        last_page = None
        while page <= args.max_pages:
            path = f"/class/category/{cid}-{page}.html"
            try:
                status, body = fetch(conn, path, cookie)
            except Exception as e:
                print(f"  第 {page} 页异常 {type(e).__name__}，重连")
                try:
                    conn.close()
                except Exception:
                    pass
                conn = SocksHTTPSConnection(HOST)
                fail_pages += 1
                time.sleep(3)
                if fail_pages > 8:
                    print("  连续失败过多，停止")
                    return 2
                continue

            if status == 404:
                print(f"  第 {page} 页 404，本分类结束")
                break
            if status in (301, 302, 303, 307, 308):
                print(f"  第 {page} 页 HTTP {status}（超出范围），本分类结束")
                break
            if status != 200:
                print(f"  第 {page} 页 HTTP {status}，暂停")
                time.sleep(5)
                fail_pages += 1
                continue

            if "安全验证" in body[:3000] or "已被系统封禁" in body:
                print(f"  !! 被拦截（验证/封禁），停止")
                state_file.write_text(json.dumps(done, ensure_ascii=False), encoding="utf-8")
                out.write_text(json.dumps(mapping, ensure_ascii=False, indent=1), encoding="utf-8")
                return 3

            # 只取 class="block" 容器里的模组链接（排除侧边栏固定推荐）
            blocks = re.split(r'<div[^>]*class="block"\b', body)[1:]
            ids = []
            for blk in blocks:
                mm = re.search(r'/class/(\d+)\.html', blk)
                if mm:
                    ids.append(mm.group(1))
            if not ids:
                ids = re.findall(r'/class/(\d+)\.html', body)
            uniq = list(dict.fromkeys(ids))
            if not uniq:
                print(f"  第 {page} 页无 class 链接，结束")
                break

            for i in uniq:
                mapping.setdefault(i, [])
                if cat_name not in mapping[i]:
                    mapping[i].append(cat_name)

            # 总页数只算一次（第 1 页），后续沿用，避免某页解析失败导致提前结束
            if page == 1 or last_page is None:
                tail = re.search(rf'/class/category/{cid}-(\d+)\.html[^>]*>\s*尾页', body)
                if tail:
                    last_page = int(tail.group(1))
                else:
                    pages = [int(x) for x in re.findall(rf'/class/category/{cid}-(\d+)\.html', body)]
                    last_page = max(pages) if pages else 9999

            ok_pages += 1
            done[str(cid)] = page
            if page == 1:
                print(f"  本分类共 {last_page} 页")
            if last_page is None:
                last_page = page + 5000
            if page % 5 == 0 or page == 1:
                el = time.time() - t0
                print(f"  第 {page}/{last_page} 页  本分类 {len(uniq)} 个  "
                      f"累计映射 {len(mapping)} 个  已用 {el/60:.1f} 分")

            if page >= last_page:
                print(f"  到达最后一页 {last_page}，本分类完成")
                break
            page += 1
            time.sleep(args.delay)

            # 每 20 页存一次
            if ok_pages % 20 == 0:
                state_file.write_text(json.dumps(done, ensure_ascii=False), encoding="utf-8")
                out.write_text(json.dumps(mapping, ensure_ascii=False, indent=1), encoding="utf-8")

    try:
        conn.close()
    except Exception:
        pass

    state_file.write_text(json.dumps(done, ensure_ascii=False), encoding="utf-8")
    out.write_text(json.dumps(mapping, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n=== 完成 ===")
    print(f"  抓取页数 {ok_pages}   映射模组 {len(mapping)} 个")
    # 分类统计
    cnt = {}
    for cats in mapping.values():
        for c in cats:
            cnt[c] = cnt.get(c, 0) + 1
    for c, n in sorted(cnt.items(), key=lambda x: -x[1]):
        print(f"    {c:<6} {n:>6}")
    print(f"  输出: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
