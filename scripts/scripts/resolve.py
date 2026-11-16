#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""短页面处理进度管理：标记"已改好"或"不需要改"，后续清单自动排除。

用法
----
    # 标记为「已改好」
    python resolve.py 2222 2880 5404 --as resolved

    # 标记为「不需要改」（前置库之类）
    python resolve.py 795 1359 --as skip

    # 看进度
    python resolve.py --status

    # 列出还没处理的短页面（导出 CSV）
    python resolve.py --export

    # 撤销标记
    python resolve.py 2222 --unmark
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from pathlib import Path

DATA = Path(r"E:\Mod\百科-语料")
SCAN = DATA / "scan"
STATE = SCAN / "short-page-state.json"   # {id: "resolved" | "skip"}


def load_state() -> dict[str, str]:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_state(st: dict[str, str]) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


def fetch_short_pages() -> list[dict]:
    con = sqlite3.connect(f"file:{DATA/'mcmod.db'}?mode=ro", uri=True, timeout=10)
    rows = list(con.execute("""
        SELECT id,name,chars,n_headings,n_imgs,n_tables,en,intro_text
        FROM classes WHERE chars < 100 ORDER BY chars ASC, id"""))
    con.close()
    out = []
    for cid, name, ch, nh, ni, nt, en, body in rows:
        out.append({"id": cid, "name": name or "", "en": en or "", "chars": ch or 0,
                    "n_headings": nh or 0, "n_imgs": ni or 0, "n_tables": nt or 0,
                    "preview": " ".join((body or "").split())[:70]})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*", type=int)
    ap.add_argument("--as", dest="kind", choices=["resolved", "skip"], default="resolved",
                    help="resolved=已改好；skip=不需要改")
    ap.add_argument("--unmark", action="store_true", help="撤销标记")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--export", action="store_true", help="导出未处理清单 CSV")
    ap.add_argument("--csv", default=str(SCAN / "短页面-待处理.csv"))
    args = ap.parse_args()

    st = load_state()
    pages = fetch_short_pages()
    by_id = {p["id"]: p for p in pages}

    if args.unmark and args.ids:
        n = 0
        for i in args.ids:
            if st.pop(str(i), None):
                n += 1
        save_state(st)
        print(f"已撤销 {n} 条的标记")
        return 0

    if args.ids and not args.status and not args.export:
        added, missing = 0, []
        for i in args.ids:
            if i not in by_id:
                missing.append(i)
                continue
            st[str(i)] = args.kind
            added += 1
        save_state(st)
        label = "已改好" if args.kind == "resolved" else "不需要改"
        print(f"标记 {added} 条为「{label}」")
        if missing:
            print(f"  ⚠ {len(missing)} 条不在短页面清单里（可能字数已超 100）：{missing[:10]}")
        return 0

    # 统计
    total = len(pages)
    resolved = sum(1 for p in pages if st.get(str(p["id"])) == "resolved")
    skipped = sum(1 for p in pages if st.get(str(p["id"])) == "skip")
    remaining = [p for p in pages if str(p["id"]) not in st]

    if args.status:
        print(f"=== 短页面处理进度 ===")
        print(f"  总数     {total}")
        print(f"  已改好   {resolved}")
        print(f"  不需要改 {skipped}")
        print(f"  待处理   {len(remaining)}")
        pct = (resolved + skipped) / total * 100 if total else 0
        bar = "█" * int(pct / 2.5) + "░" * (40 - int(pct / 2.5))
        print(f"  [{bar}] {pct:.1f}%")
        return 0

    if args.export:
        with open(args.csv, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "名称", "英文名", "字数", "小标题", "图片数", "链接", "正文预览"])
            for p in remaining:
                w.writerow([p["id"], p["name"], p["en"], p["chars"], p["n_headings"],
                            p["n_imgs"], f"https://www.mcmod.cn/class/{p['id']}.html",
                            p["preview"]])
        print(f"已导出待处理清单（{len(remaining)} 条）: {args.csv}")
        return 0

    print(f"总数 {total}｜已改好 {resolved}｜不需要改 {skipped}｜待处理 {len(remaining)}")
    print("用法：resolve.py 2222 2880 --as resolved | --status | --export")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
