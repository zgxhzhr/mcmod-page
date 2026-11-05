#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 Mcmodder 官方脚本里的跨境 CDN 换成国内可用镜像。

背景（实测 2026-11）：
    Mcmodder 2.4.0 的 supabase-js 走 cdn.jsdmirror.com（约 0.9 s）
    Mcmodder 2.4.1 换成了 fastly.jsdelivr.net（约 3.0 s，且国内时通时不通）
    Tampermonkey 会等所有 @require 加载完成才执行脚本，所以慢/失败的
    @require 会让整个脚本「延迟执行或不执行」——表现为页面样式不变、
    编辑器功能不工作，很容易被误判为「篡改猴版本太低」或「脚本有 bug」。

用法：
    python patch-mcmodder.py <输入.user.js> [输出.user.js]

默认输出为 <输入名>-mirror.user.js。若输出文件已存在会覆盖。
"""
import sys
from pathlib import Path

# 需要替换的跨境 CDN 前缀 → 国内镜像前缀
REPLACEMENTS = [
    ("https://fastly.jsdelivr.net/npm/", "https://cdn.jsdmirror.com/npm/"),
    ("https://cdn.jsdelivr.net/npm/", "https://cdn.jsdmirror.com/npm/"),
    ("https://raw.githubusercontent.com/", "https://raw.gitmirror.com/"),
]


def patch(text: str) -> tuple[str, list[str]]:
    """返回 (替换后的文本, 改动清单)。"""
    changes: list[str] = []
    for old, new in REPLACEMENTS:
        if old in text:
            n = text.count(old)
            text = text.replace(old, new)
            changes.append(f"{old}  ->  {new}   （{n} 处）")

    # 替换后要确保 @connect 放行镜像域名，否则 GM_xmlhttpRequest 会被拦
    for domain in ("cdn.jsdmirror.com", "raw.gitmirror.com"):
        line = f"// @connect      {domain}"
        if domain in text and line not in text:
            anchor = "// @connect      mcmod.cn"
            text = text.replace(anchor, f"{line}\n{anchor}", 1)
            changes.append(f"新增 {line.strip()}")

    return text, changes


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_name(src.stem + "-mirror.user.js")

    text = src.read_text(encoding="utf-8", errors="ignore")
    patched, changes = patch(text)
    if not changes:
        print("没有需要替换的 CDN（脚本可能已经打过补丁）")
        return 0

    dst.write_text(patched, encoding="utf-8")
    print(f"输入：{src}  ({src.stat().st_size / 1024:.1f} KB)")
    print(f"输出：{dst}  ({dst.stat().st_size / 1024:.1f} KB)")
    for c in changes:
        print("  " + c)
    print("\n装好后请完全重启浏览器（篡改猴需重新加载脚本与 @require 缓存）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
