#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mcauto 能力自检：这台机器现在能做什么、缺什么、下一步装什么。

用法：
    python doctor.py              # 全部检查
    python doctor.py --json       # 机器可读输出（给另一个 AI 用）

设计原则
--------
每一项都对应「一条具体能跑的命令」或「一个具体要装的包」，不说废话。
检查顺序按装配顺序排：环境 → 启动器 → 工具 jar → 版本 → 网络。
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import sys
import urllib.request
from pathlib import Path

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import config as C

OK, WARN, BAD = "OK", "WARN", "MISSING"
rows: list[dict] = []


def add(layer: str, name: str, status: str, detail: str = "", fix: str = ""):
    rows.append({"layer": layer, "name": name, "status": status,
                 "detail": detail, "fix": fix})


# ── 环境 ─────────────────────────────────────────────
def check_env():
    for major, why in (("8", "1.12.2 / 1.7.10 / 1.16.5 编译与运行"),
                       ("17", "1.16.5~1.20.1 运行"),
                       ("21", "1.21.1 运行")):
        exe = C.javaw(major)
        if exe:
            add("环境", f"JDK {major}", OK, exe)
        else:
            add("环境", f"JDK {major}", BAD, f"{C.java_home(major)} 不存在",
                f"装 JDK {major} 并改 config.json 的 java[\"{major}\"]（{why}）")

    # JDK8 必须在工作区外：工作区被标 Low 完整性时，从里面启动的 exe 写不了 %TEMP%
    j8 = C.java_home("8")
    if j8.exists():
        inside_ws = str(j8).lower().startswith(str(Path(os.environ.get("MCAUTO_WORKSPACE", r"E:\Mod"))).lower())
        if inside_ws:
            add("环境", "JDK 8 位置", WARN, f"{j8} 在工作区内",
                "把 JDK 8 移到工作区外（否则 Minecraft 的 jar 重映射会因 %TEMP% 不可写而失败）")
        else:
            add("环境", "JDK 8 位置", OK, "在工作区外")

    for major, why in (("8", "1.21.1 以下 ForgeGradle/Fabric 构建"),):
        g = C.gradle_bat(major)
        add("环境", f"Gradle {major}", OK if g else WARN, g or "未配置",
            f"下载 Gradle {major} 并改 config.json 的 gradle[\"{major}\"]（{why}）")
    for major, why in (("7", "ForgeGradle 5 / 1.16.5 mod"),
                       ("4", "ForgeGradle 2.3 / 1.12.2 mod"),
                       ("2", "ForgeGradle 1.2（1.7.10 已不需要，走 javac）")):
        g = C.gradle_bat(major)
        add("环境", f"Gradle {major}", OK if g else WARN, g or "未配置",
            f"编译 mod 时需要（{why}）")


# ── 启动器 / 版本 ────────────────────────────────────
def check_launcher():
    md = C.mc_dir()
    if not (md / "versions").exists():
        add("启动器", "PCL .minecraft", BAD, f"{md} 下没有 versions/",
            "改 config.json 的 mc_dirs 指向装了版本的 .minecraft")
        return
    vers = [p.name for p in (md / "versions").iterdir() if p.is_dir()]
    add("启动器", "PCL .minecraft", OK, f"{md}（{len(vers)} 个版本）")

    wanted = {
        "1.21.1": ["1.21.1-neoforge", "1.21.1"],
        "1.20.1": ["1.20.1-forge", "fabric-loader-0.15.*-1.20.1"],
        "1.19.2": ["1.19.2-forge", "fabric-loader-*-1.19.2"],
        "1.18.2": ["1.18.2-forge", "fabric-loader-*-1.18.2"],
        "1.16.5": ["1.16.5-forge", "fabric-loader-*-1.16.5"],
        "1.12.2": ["1.12.2-forge"],
        "1.7.10": ["1.7.10-forge", "1.7.10-Forge-mcauto"],
    }
    import fnmatch
    for mc, pats in wanted.items():
        hit = any(any(fnmatch.fnmatch(v, p + "*") or fnmatch.fnmatch(v, p) for p in pats)
                  for v in vers)
        add("启动器", f"版本 {mc}", OK if hit else BAD,
            "已装" if hit else "未找到匹配的版本目录",
            "用 PCL 装该版本（1.7.10 需手工拼版本，见 docs/BOOTSTRAP.md §4）" if not hit else "")


# ── 工具 jar（站方工具，自备） ────────────────────────
def check_tools():
    found = {}
    jars = []
    for d in [C.mods_cache(), *C.tool_dirs()]:
        if d.exists():
            jars.extend(d.rglob("*.jar"))
    for key, path in (C.CFG.get("tool_jars") or {}).items():
        p = Path(path) if path else None
        if p and p.exists():
            found[key] = str(p)
    for jar in jars:
            n = jar.name.lower()
            if "letmesee" in n or "let_me_see_see" in n:
                found["LMS"] = str(jar)
            elif "irr" in n and "1.7.10" in n:
                found["IRR 1.7.10"] = str(jar)
            elif "irr" in n and "1.12.2" in n:
                found["IRR 1.12.2"] = str(jar)
            elif "irr" in n and ("1.16" in n or "1.16.x" in n):
                found["IRR 1.16.x"] = str(jar)
            elif "iconrenderer" in n and "forge" in n and "1.20.1" in n:
                found["IconRenderer-Forge 1.20.1"] = str(jar)
            elif "iconrenderer" in n and "forge" in n and "1.19.2" in n:
                found["IconRenderer-Forge 1.19.2"] = str(jar)

    need = {
        "LMS": ("1.21.1 NeoForge 导出", "我们的 fork 构建产物；或 CurseForge 上游"),
        "IRR 1.16.x": ("1.16.5 Forge 导出", "CurseForge: Item Render Rebirth 1.16.x"),
        "IRR 1.12.2": ("1.12.2 Forge 导出", "CurseForge: IRR 1.12.2"),
        "IRR 1.7.10": ("1.7.10 Forge 导出", "CurseForge: IRR 1.7.10"),
        "IconRenderer-Forge 1.20.1": ("1.20.1 Forge 导出", "CurseForge: IconRenderer-Forge"),
        "IconRenderer-Forge 1.19.2": ("1.19.2 Forge 导出", "CurseForge: IconRenderer-Forge"),
    }
    for k, (why, where) in need.items():
        if k in found:
            add("工具 jar", k, OK, found[k])
        else:
            add("工具 jar", k, BAD, f"缺（{why}）", f"放进 {cache} 或 config.json 的 tool_jars：{where}")

    # 我们自己的 fork 产物（release 里带）
    for k, why in (("LMS fork", "1.21.1"), ("IconRenderer Fabric fork", "Fabric 各版本")):
        add("工具 jar", k, WARN if k not in found else OK,
            "自编产物（release 资产里有）", f"对应 {why}")


# ── 网络 ─────────────────────────────────────────────
def check_net():
    try:
        with socket.create_connection(("127.0.0.1", 10808), timeout=1):
            add("网络", "本地代理 10808", OK, "可用（下载前置快 30 倍）")
    except OSError:
        add("网络", "本地代理 10808", WARN, "未监听",
            f"开代理后把 config.json 的 proxy 改对；直连 Modrinth 约 0.06 MB/s")

    for name, url in (("Mojang", "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"),
                      ("Modrinth", "https://api.modrinth.com/v2/search?limit=1"),
                      ("Forge maven", "https://maven.minecraftforge.net/")):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "mcauto-doctor/1"})
            with urllib.request.urlopen(req, timeout=6) as r:
                add("网络", name, OK if r.status < 400 else WARN, f"HTTP {r.status}")
        except Exception as e:
            add("网络", name, WARN, type(e).__name__, "可能要开代理")


# ── 能力分层（L1~L6，按装配顺序） ────────────────────
def capability_layers() -> list[tuple[str, str, str]]:
    def ok(layer, prefix):
        return any(r["layer"] == layer and r["name"].startswith(prefix) and r["status"] == OK
                   for r in rows)

    j8 = bool(C.javaw("8"))
    j17 = bool(C.javaw("17"))
    j21 = bool(C.javaw("21"))
    mc = C.mc_dir()
    return [
        ("L1 能起客户端到标题界面",
         OK if (j8 and (mc / "versions").exists()) else BAD,
         "需要 JDK + 至少一个版本目录"),
        ("L2 能进世界（quickPlay / 服务端 / mod）",
         OK if ok("启动器", "版本 1.20.1") or ok("启动器", "版本 1.19.2") else WARN,
         "1.20+ 靠 --quickPlaySingleplayer；1.19.2 及更早靠本地服务端；1.16.5 及更早靠 mod"),
        ("L3 能触发导出拿到 json",
         OK if [r for r in rows if r["layer"] == "工具 jar" and r["status"] == OK] else BAD,
         "需要对应版本的导出工具 jar"),
        ("L4 图标正确",
         WARN, "只能人工抽看（脚本能出图，判断不了像不像）"),
        ("L5 依赖自动补齐（autodeps）",
         OK if ok("网络", "Modrinth") else WARN,
         "需要能访问 Modrinth（或本地已有全部前置）"),
        ("L6 批量编排（batch）",
         OK if (mc / "versions").exists() else WARN,
         "L1~L3 全绿之后才有意义"),
    ]


def main() -> int:
    as_json = "--json" in sys.argv
    check_env()
    check_launcher()
    check_tools()
    check_net()

    if as_json:
        print(json.dumps({"checks": rows,
                          "layers": [{"name": n, "status": s, "note": d}
                                     for n, s, d in capability_layers()]},
                         ensure_ascii=False, indent=2))
        return 0

    icon = {OK: "✓", WARN: "!", BAD: "✗"}
    last = None
    for r in rows:
        if r["layer"] != last:
            print(f"\n[{r['layer']}]")
            last = r["layer"]
        line = f"  {icon[r['status']]} {r['name']:<28} {r['detail']}"
        print(line)
        if r["fix"] and r["status"] != OK:
            print(f"      → {r['fix']}")

    print("\n[能力分层]")
    for name, status, note in capability_layers():
        print(f"  {icon[status]} {name:<40} {note}")

    bad = [r for r in rows if r["status"] == BAD]
    print(f"\n结论：{len(bad)} 项缺失。")
    if bad:
        print("按上面 → 的提示逐个补；补完重跑本命令确认。")
    else:
        print("全部就绪，可以跑 run.py。")
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
