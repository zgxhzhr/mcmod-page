#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make-preview.py —— 交付预览页（卡片式，自包含单文件）。

从 18853 批的 preview.html 格式固化而来：每个条目一张卡片，
图、正文、附言一屏看全；介绍页也作为第一张卡片并入。

用法：
    python make-preview.py <交付目录> [输出名=preview.html]
识别：
    *-资料页*.json / *-父资料*.json / *-子资料*.json / *-实体*.json /
    *-通用文本*.json / *-自然生成*.json …（交付目录里的全部 JSON 数组）
    *-介绍*.mcmod.html（有则排第一张卡）
"""
import json
import re
import sys
from pathlib import Path

STYLE = (
    "body{font-family:sans-serif;max-width:860px;margin:0 auto;padding:16px;background:#f6f6f6}"
    ".card{background:#fff;border:1px solid #ddd;border-radius:8px;padding:14px 18px;margin:12px 0}"
    "h3{margin:0 0 4px}small{color:#888;font-weight:normal}"
    ".meta{color:#666;font-size:13px;margin-bottom:8px}"
    "p{line-height:1.7;margin:8px 0}details{margin-top:8px;color:#555;font-size:13px}"
    "table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:6px 10px}"
)


def b_tag(s: str) -> str:
    """百科方括号标题转可视标签；[ban:title_menu] 显示为提示行。"""
    s = re.sub(r"\[h(\d)=([^\]]+)\]", lambda m: f"<h{min(int(m.group(1)) + 2, 6)}>{m.group(2)}</h{min(int(m.group(1)) + 2, 6)}>", s)
    s = re.sub(r"\[ban:[^\]]+\]", '<p style="color:#a86">[ban:title_menu]（预览不渲染，粘贴后生效）</p>', s)
    return s


def esc_icon(r) -> tuple[str, str]:
    has32, has128 = bool(r.get("icon32")), bool(r.get("icon128"))
    if has128:
        return f'<img src="data:image/png;base64,{r["icon128"]}" width=96 height=96>', "有"
    if has32:
        return f'<img src="data:image/png;base64,{r["icon32"]}" width=96 height=96>', "有(仅32)"
    return "", "无(勾删除)"


def card(r, title_note="") -> str:
    img, icon_state = esc_icon(r)
    meta = f'{r.get("type", "")} / {r.get("category", "")} / 图标:{icon_state}'
    if r.get("maxstack") not in ("", None):
        meta += f' / 堆叠:{r["maxstack"]}'
    if r.get("regname") == "" and r.get("html"):
        meta += " / 抽象·通用文本（注册名与图标应空）"
    en = r.get("ename") or ""
    sub = " · ".join(x for x in (en, r.get("regname", "")) if x)
    head = f'<h3>{r.get("name", "?")} <small>{sub}{title_note}</small></h3>'
    html_body = r.get("html") or ""
    body_disp = b_tag(html_body) if html_body else '<p style="color:#b5b5b5">（正文空：子资料，通过后由父资料统一引用）</p>'
    remark = r.get("remark", "")
    det = f'<details><summary>附言</summary><p>{remark}</p></details>' if remark else ""
    return f'<div class="card">{head}<div class="meta">{meta}</div>{img}{body_disp}{det}</div>'


def main() -> int:
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    out_name = sys.argv[2] if len(sys.argv) > 2 else "preview.html"
    cards = []
    intro = next(iter(sorted(d.glob("*介绍*.html"))), None)
    if intro:
        cards.append(f'<div class="card"><h3>模组介绍 <small>{intro.name}</small></h3>'
                     f'<div class="meta">介绍页正文（原文 + 补充）</div>{b_tag(intro.read_text(encoding="utf-8"))}</div>')
    total = 0
    for f in sorted(d.glob("*.json")):
        if f.name.lower().startswith(("config", "info")):
            continue
        try:
            rows = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(rows, list):
            continue
        for r in rows:
            if isinstance(r, dict) and "name" in r:
                cards.append(card(r, title_note=f" <small>[{f.name.split('-')[0]}]</small>"))
                total += 1
    page = (f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>{d.name} 预览</title>'
            f'<style>{STYLE}</style></head><body>{"".join(cards)}</body></html>')
    (d / out_name).write_text(page, encoding="utf-8")
    print(f"✓ {out_name}：{total} 条卡片" + ("" if not intro else " + 介绍页"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
