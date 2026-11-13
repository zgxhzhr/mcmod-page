#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""从 PCL 的 version json 生成 java 启动命令行。

为什么自己生成而不调 PCL：PCL 修改版的命令行能力未知，且每次换版本都要手点一次
才有 LatestLaunch.bat。version json 里该有的都有（arguments.jvm / arguments.game /
libraries / assetIndex），自己解析就能对任意已安装版本生成同样的命令。

用法：

    # 只打印命令行（不发车）
    python launcher.py --version 1.21.1-NeoForge_21.1.255 --game-dir D:\tmp\irr --dry-run

    # 真正启动
    python launcher.py --version 1.21.1-NeoForge_21.1.255 --game-dir D:\tmp\irr \
        --extra-jvm "-DLET_ME_SEE_EXPORT_PATH=D:\tmp\irr\_export" \
        --javaagent D:\...\mcauto-agent.jar

支持：Forge / NeoForge / Fabric / 原版（只要 json 是标准格式）。
不处理：inheritsFrom 链（PCL 生成的都是扁平化的完整 json；若遇到 inheritsFrom 会提示）
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

DEFAULT_MC = Path(r"E:\PCL\.minecraft")
# 1.21 系要 Java 21；1.16-1.20 要 Java 17；1.12.2 要 Java 8
JAVA_CANDIDATES = [
    r"C:\Program Files\Java\jdk-21.0.12\bin\javaw.exe",
    r"C:\Program Files\Java\jdk-17\bin\javaw.exe",
    r"C:\Program Files\Java\jdk-25\bin\javaw.exe",
]


def find_java(version: str) -> str:
    """按 MC 版本猜 Java。返回 javaw.exe 路径（无控制台窗口）。"""
    if version.startswith(("1.7", "1.8", "1.9", "1.10", "1.11", "1.12")):
        want = 8
    elif version.startswith(("1.13", "1.14", "1.15", "1.16")):
        want = 8  # 1.16.5 用 8 最稳
    elif version.startswith(("1.17", "1.18", "1.19", "1.20")):
        want = 17
    else:
        want = 21
    for c in JAVA_CANDIDATES:
        if not Path(c).exists():
            continue
        if f"jdk-{want}" in c or (want == 21 and "jdk-21" in c):
            return c
    # 找不到就按顺序第一个存在的
    for c in JAVA_CANDIDATES:
        if Path(c).exists():
            return c
    raise SystemExit("找不到 java，请在 JAVA_CANDIDATES 里加一条")


def rule_allows(rules) -> bool:
    """处理 libraries / arguments 里的 rules（只关心 os.name / os.arch / features）。"""
    if not rules:
        return True
    osname = {"windows": "windows", "linux": "linux", "darwin": "osx"}.get(
        platform.system().lower(), platform.system().lower())
    arch = "x86" if platform.machine().lower() in ("x86", "i386", "i686") else "x64"
    allowed = False
    for r in rules:
        action = r.get("action")
        cond = r.get("os") or {}
        ok = True
        if "name" in cond and cond["name"] != osname:
            ok = False
        if "arch" in cond and cond["arch"] != arch:
            ok = False
        if "version" in cond:  # 正则匹 OS 版本，忽略
            ok = False
        if ok:
            allowed = (action == "allow")
    return allowed


def build(mc_dir: Path, version: str, game_dir: Path, username: str,
          java: str, extra_jvm: list[str], width: int, height: int,
          agent: str | None, export_path: str | None) -> list[str]:
    vdir = mc_dir / "versions" / version
    js = list(vdir.glob("*.json"))
    if not js:
        raise SystemExit(f"版本不存在：{vdir}")
    vj = json.loads(js[0].read_text(encoding="utf-8"))
    if vj.get("inheritsFrom"):
        raise SystemExit(f"该 version json 带 inheritsFrom={vj['inheritsFrom']}，"
                         "本脚本只处理 PCL 生成的扁平化 json")
    libs_dir = mc_dir / "libraries"
    assets_dir = mc_dir / "assets"
    natives = game_dir / "_natives"
    natives.mkdir(parents=True, exist_ok=True)

    # ── classpath：libraries 里的 artifact（跳过 natives 分类）──
    cp: list[str] = []
    for lib in vj.get("libraries", []):
        if not rule_allows(lib.get("rules")):
            continue
        art = (lib.get("downloads") or {}).get("artifact")
        if not art:
            continue
        p = libs_dir / art["path"]
        if p.exists():
            cp.append(str(p))
    # 版本自己的 jar（PCL 生成的扁平版本是完整客户端 jar）
    vjar = vdir / f"{version}.jar"
    if vjar.exists():
        cp.append(str(vjar))

    # 去重：1.21.1 的 version json 里同一路径会列两次（原版库 + NeoForge 追加库有重叠），
    # 重复项会让 Bootstraplauncher 的 UnionFileSystem 抛 duplicateKeyException，客户端秒退。
    seen = set()
    dedup = []
    for x in cp:
        key = str(Path(x).resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        dedup.append(x)
    dropped = len(cp) - len(dedup)
    cp = dedup
    if dropped:
        print(f"[launcher] classpath 去重：{dropped} 项重复已移除", file=sys.stderr)

    sep = ";"
    library_directory = str(libs_dir)
    classpath = sep.join(cp)

    # ── jvm 参数：展开占位符（-cp / -p 由 json 自己带）──
    subs = {
        "natives_directory": str(natives),
        "launcher_name": "mcauto",
        "launcher_version": "1",
        "classpath": classpath,
        "classpath_separator": sep,
        "library_directory": library_directory,
        "version_name": version,
    }

    def expand(s: str) -> str:
        for k, v in subs.items():
            s = s.replace("${" + k + "}", v)
        return s

    jvm: list[str] = []
    for a in vj.get("arguments", {}).get("jvm", []):
        if isinstance(a, str):
            jvm.append(expand(a))
        elif rule_allows(a.get("rules")):
            val = a.get("value")
            if isinstance(val, list):
                jvm.extend(expand(x) for x in val)
            else:
                jvm.append(expand(val))

    # 内存 + 编码 + 我们的注入
    jvm += [
        "-Xmx3G", "-Xms1G",
        "-Dfile.encoding=UTF-8",
        "-Dsun.stdout.encoding=UTF-8",
        "-Dsun.stderr.encoding=UTF-8",
        "-Dlog4j2.formatMsgNoLookups=true",
        f"-Dmcauto.gameDir={game_dir}",
    ]
    if export_path:
        jvm.append(f"-DLET_ME_SEE_EXPORT_PATH={export_path}")
    if agent:
        jvm.append(f"-javaagent:{agent}")
    jvm += extra_jvm

    # ── game 参数 ──
    gsubs = {
        "auth_player_name": username,
        "version_name": version,
        "game_directory": str(game_dir),
        "assets_root": str(assets_dir),
        "assets_index_name": vj.get("assetIndex", {}).get("id", "legacy"),
        "auth_uuid": "00000000000000000000000000000000",
        "auth_access_token": "0" * 32,
        "clientid": "",
        "auth_xuid": "",
        "user_type": "legacy",
        "version_type": "release",
        "resolution_width": str(width),
        "resolution_height": str(height),
        "game_assets": str(assets_dir / "virtual" / "legacy"),
        # NeoForge 的 version json 自带 quickPlay 系列占位符，不展开会变成字面量
        "quickPlayPath": "",
        "quickPlaySingleplayer": "",
        "quickPlayMultiplayer": "",
        "quickPlayRealms": "",
    }

    def gexpand(s: str) -> str:
        for k, v in gsubs.items():
            s = s.replace("${" + k + "}", v)
        return s

    game: list[str] = []
    for a in vj.get("arguments", {}).get("game", []):
        if isinstance(a, str):
            game.append(gexpand(a))
        elif rule_allows(a.get("rules")):
            val = a.get("value")
            if isinstance(val, list):
                game.extend(gexpand(x) for x in val)
        else:
            game.append(gexpand(val))

    # 占位符展开成空值的 quickPlay 参数要整对删掉：
    # 留着会和我们后面追加的 --quickPlaySingleplayer 冲突
    # （jopt-simple: Found multiple arguments for option quickPlaySingleplayer）
    cleaned: list[str] = []
    i = 0
    while i < len(game):
        tok = game[i]
        if tok.startswith("--quickPlay") and i + 1 < len(game) and game[i + 1] == "":
            i += 2
            continue
        cleaned.append(tok)
        i += 1
    game = cleaned

    # 确保窗口尺寸（json 里通常已带，没有就补）
    if "--width" not in game:
        game += ["--width", str(width), "--height", str(height)]

    return [java] + jvm + [vj["mainClass"]] + game


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mc-dir", default=str(DEFAULT_MC))
    ap.add_argument("--version", required=True)
    ap.add_argument("--game-dir", required=True)
    ap.add_argument("--username", default="mcauto")
    ap.add_argument("--java", default="")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--extra-jvm", nargs="*", default=[])
    ap.add_argument("--agent", default="")
    ap.add_argument("--export-path", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    mc_dir = Path(a.mc_dir)
    game_dir = Path(a.game_dir)
    game_dir.mkdir(parents=True, exist_ok=True)
    java = a.java or find_java(a.version)

    argv = build(mc_dir, a.version, game_dir, a.username, java,
                 a.extra_jvm, a.width, a.height, a.agent or None,
                 a.export_path or None)

    if a.dry_run:
        # 命令行太长，摘要 + 写文件
        out = game_dir / "_launch_cmd.txt"
        out.write_text("\n".join(argv), encoding="utf-8")
        n_cp = len([x for x in argv if x.endswith(".jar")])
        print(f"java   : {argv[0]}")
        print(f"jvm 参数: {len(argv) - 1} 个")
        print(f"jar 数  : {n_cp}")
        print(f"main    : {argv[-len(argv) + 1] if False else next(x for x in argv if x.endswith('Launcher') or 'Main' in x)}")
        print(f"完整命令行已写入 {out}")
        return 0

    print(f"[mcauto] 启动 {a.version}  gameDir={game_dir}")
    proc = subprocess.Popen(argv, cwd=str(game_dir))
    print(f"[mcauto] pid={proc.pid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
