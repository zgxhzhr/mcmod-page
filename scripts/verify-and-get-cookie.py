#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用浏览器过一次站点安全验证，并导出完整 Cookie 供抓取器使用。

原理
----
MC百科的 WAF 在 IP 被风控后返回「安全验证」页。人工过一次验证后，
站点会签发一组 Cookie（常含 HttpOnly），之后的请求带上它就放行。

为什么用 Playwright 而不是读 Edge 的 Cookies 库
- Edge 127+ 启用 App-Bound Encryption，Cookie 无法用 DPAPI 直接解密；
- Playwright 的 context.cookies() 能直接拿到包含 HttpOnly 的全部 Cookie。

用法
----
    python verify-and-get-cookie.py                 # 默认走 socks5://127.0.0.1:1080
    python verify-and-get-cookie.py --proxy socks5://127.0.0.1:1080
    python verify-and-get-cookie.py --no-proxy      # 直连（真实 IP）

流程：打开窗口 → 你手动过验证 → 脚本自动检测通过 → 导出 Cookie 到 cookies.json
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

DATA = Path(r"E:\Mod\百科-语料")
PROFILE = DATA / "browser-profile"
CHECK_URL = "https://www.mcmod.cn/class/200.html"
BAN_MARK = "已被系统封禁"
VERIFY_MARK = "安全验证"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--proxy", default="socks5://127.0.0.1:1080")
    ap.add_argument("--no-proxy", action="store_true")
    ap.add_argument("--timeout", type=int, default=300, help="等待人工过验证的秒数")
    args = ap.parse_args()

    DATA.mkdir(parents=True, exist_ok=True)
    proxy = None if args.no_proxy else {"server": args.proxy}

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE),
            executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            headless=False,
            proxy=proxy,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        print(f"打开 {CHECK_URL}")
        print(f"代理：{args.proxy if not args.no_proxy else '直连'}")
        page.goto(CHECK_URL, wait_until="domcontentloaded", timeout=60000)

        print("\n>>> 如果看到「安全验证」页面，请在窗口里手动完成验证。")
        print(">>> 脚本会自动检测，通过后自动导出 Cookie。\n")

        ok = False
        start = time.time()
        while time.time() - start < args.timeout:
            try:
                title = page.title()
                body = page.content()
            except Exception:
                time.sleep(2)
                continue

            if BAN_MARK in body:
                print("  当前 IP 是【永久封禁】状态，不是验证页。换节点再试。")
                break
            if VERIFY_MARK in title or VERIFY_MARK in body[:4000]:
                left = int(args.timeout - (time.time() - start))
                print(f"  等待验证… 剩余 {left}s   （当前标题：{title[:40]}）")
            else:
                print(f"  验证通过：{title[:60]}")
                ok = True
                break
            time.sleep(3)

        if not ok:
            print("\n未检测到验证通过，未导出 Cookie。")
            ctx.close()
            return 1

        # 再访问一次确认稳定，并让站点下发全部 Cookie
        try:
            page.goto(CHECK_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(2)
        except Exception:
            pass

        cookies = ctx.cookies()
        ctx.close()

    mc = [c for c in cookies if "mcmod.cn" in c.get("domain", "")]
    header = "; ".join(f"{c['name']}={c['value']}" for c in mc)

    out = DATA / "cookies.json"
    out.write_text(json.dumps(mc, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA / "cookie-header.txt").write_text(header, encoding="utf-8")

    print(f"\n已导出 {len(mc)} 个 mcmod.cn Cookie")
    print(f"  {out}")
    print(f"  {DATA/'cookie-header.txt'}")
    print(f"  Cookie 头长度：{len(header)} 字符")
    for c in mc[:10]:
        print(f"    {c['name']:<28} {'HttpOnly' if c.get('httpOnly') else '        '}  "
              f"{(c.get('value') or '')[:20]}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
