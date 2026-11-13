#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""把改好的 mcmod-batch.user.js 装成浏览器扩展（Edge/Chrome 解压加载）。

已装位置：C:\Users\MKIII\AppData\Local\McmodBatchExt
  content.js     —— 与 skill 里的 mcmod-batch.user.js 是同一份代码，独立副本
  manifest.json  —— MV3，content_scripts 的 matches 必须含 /class/edit/*
                     否则模组介绍编辑页不注入，面板自然「消失」

每次改完 user.js 跑一次本脚本，然后在 edge://extensions 点「重新加载」。
"""
import json
import re
from pathlib import Path

SRC = Path(r"E:\Mod\模板与工具\发布\mcmod-page\scripts\mcmod-batch.user.js")
EXT = Path(r"C:\Users\MKIII\AppData\Local\McmodBatchExt")

MATCHES = [
    "https://www.mcmod.cn/item/add/*",
    "https://www1.mcmod.cn/item/add/*",
    "https://www.mcmod.cn/item/list/*",
    "https://www1.mcmod.cn/item/list/*",
    "https://www.mcmod.cn/item/edit/*",
    "https://www1.mcmod.cn/item/edit/*",
    "https://www.mcmod.cn/class/edit/*",
    "https://www1.mcmod.cn/class/edit/*",
    "https://www.mcmod.cn/verify*",
    "https://www1.mcmod.cn/verify*",
]


def main() -> int:
    src = SRC.read_text(encoding="utf-8")
    m = re.search(r"// @version\s+([\w.]+)", src)
    ver = m.group(1) if m else "0.0"

    EXT.mkdir(parents=True, exist_ok=True)

    # content.js 直接复制 user.js（头部的 UserScript 注释是普通注释，不影响 MV3 执行）
    (EXT / "content.js").write_text(src, encoding="utf-8")

    manifest = {
        "manifest_version": 3,
        "name": "MC百科 批量新增",
        "version": ver,
        "description": "在 MC百科 新增/编辑资料页与模组介绍编辑页注入批量面板，批量填充并提交。",
        "content_scripts": [
            {
                "matches": MATCHES,
                "js": ["content.js"],
                "run_at": "document_idle",
            }
        ],
    }
    (EXT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"✓ 已写入 {EXT}")
    print(f"  content.js    {len(src)/1024:.1f} KB  (v{ver})")
    print(f"  manifest.json v{ver}  matches {len(MATCHES)} 条（含 /class/edit/*）")
    print("\n下一步：打开 edge://extensions → 找到「MC百科 批量新增」→ 点「重新加载」")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
