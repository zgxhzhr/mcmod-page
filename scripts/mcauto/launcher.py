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
    # 注意：这个路径必须在**工作区之外**。DSH 把工作区（E:\Mod）标成 Low 完整性，
    # 从工作区里启动的 exe 会继承 Low IL，连 TEMP 都写不了（Minecraft 的
    # zipfs 重映射和 ImageIO 都会 AccessDenied）。
    r"C:\Users\MKIII\jdks\jdk8\bin\javaw.exe",
    r"C:\Program Files\Java\jdk-21.0.12\bin\javaw.exe",
    r"C:\Program Files\Java\jdk-17\bin\javaw.exe",
    r"C:\Program Files\Java\jdk-25\bin\javaw.exe",
]


def mcver_of(version: str) -> str:
    """从 PCL 版本名里取出 MC 版本（可能是 inheritsFrom 形式的 fabric-loader-...-1.19.2）"""
    import re
    m = re.search(r"\b1\.\d+(?:\.\d+)?\b", version)
    return m.group(0) if m else version


def find_java(version: str) -> str:
    """按 MC 版本猜 Java。返回 javaw.exe 路径（无控制台窗口）。

    注意：先归一化版本名 —— PCL 的 Fabric 版本可能叫
    fabric-loader-0.14.12-1.19.2，直接 startswith 判断会落到 else 拿 JDK 21，
    而 loader 0.14.12 的 mixin 在 JDK 21 上会炸（LambdaMetafactory 找不到）。
    """
    version = mcver_of(version)
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
        if want == 8 and (r"_tools\jdk8" in c or "jdk8" in c.replace("-", "")):
            return c
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


LIB_CACHE = Path(r"E:\Mod\百科-语料\mcauto-cache\libraries")


def ensure_library_files(vj: dict, libs_dir: Path) -> list[str]:
    """按 version json 里的 url 补齐缺失的库文件，返回补下来的路径。

    为什么需要：PCL 只下载它装过的版本的库。用 fabric-installer 造出来的版本
    （或者从没装过的 1.18.2 / 1.16.5）本机根本没有 netty / lwjgl 等文件，
    直接启动会 ClassNotFoundException: io/netty/...

    下载到我们自己的缓存目录，不往 PCL 的 .mozilla 里写东西。
    """
    import urllib.request
    extra: list[str] = []
    todo = []

    def want(path_rel: str, url: str | None):
        if not url:
            return
        target = libs_dir / path_rel
        if target.exists():
            return
        cached = LIB_CACHE / path_rel
        if cached.exists():
            extra.append(str(cached))
            return
        todo.append((path_rel, url, cached))

    for lib in vj.get("libraries", []):
        if not rule_allows(lib.get("rules")):
            continue
        dl = lib.get("downloads") or {}
        art = dl.get("artifact")
        if art:
            want(art["path"], art.get("url"))
        # 老格式的原生库：natives 里按 OS 指定 classifier
        nat = lib.get("natives") or {}
        osname = {"windows": "windows", "linux": "linux", "osx": "osx"}.get(
            platform.system().lower(), platform.system().lower())
        cls_name = nat.get(osname)
        if cls_name:
            cls = (dl.get("classifiers") or {}).get(cls_name)
            if cls:
                want(cls["path"], cls.get("url"))

    if todo:
        LIB_CACHE.mkdir(parents=True, exist_ok=True)
        print(f"[launcher] 补下 {len(todo)} 个缺失库文件 …")
        import time as _t
        ok = 0
        for rel, url, cached in todo:
            cached.parent.mkdir(parents=True, exist_ok=True)
            for attempt in range(3):
                try:
                    urllib.request.urlretrieve(url, cached)
                    extra.append(str(cached))
                    ok += 1
                    break
                except Exception:
                    _t.sleep(1)
        print(f"[launcher] 补齐 {ok}/{len(todo)}")
    return extra


VANILLA_CACHE = Path(r"E:\Mod\百科-语料\mcauto-cache\vanilla")


def _mojang_manifest() -> dict:
    import urllib.request
    cache = VANILLA_CACHE / "version_manifest_v2.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    req = urllib.request.Request(
        "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json",
        headers={"User-Agent": "mcauto/1"})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read())
    cache.write_text(json.dumps(data), encoding="utf-8")
    return data


def ensure_vanilla(vid: str) -> tuple[Path, Path | None]:
    """确保原版版本 json 与客户端 jar 在缓存里；返回 (json, jar)。

    为什么要这个：Fabric installer 生成的版本 json 带 inheritsFrom=<原版>，
    而用户机器上可能只装了 Forge/NeoForge 的扁平版本，没有原版目录。
    这里从 Mojang 拉一份放到**我们自己的缓存**，不往 PCL 的 .minecraft 里写东西。
    """
    import urllib.request
    d = VANILLA_CACHE / vid
    d.mkdir(parents=True, exist_ok=True)
    jp = d / f"{vid}.json"
    jj = d / f"{vid}.jar"
    if not jp.exists():
        man = _mojang_manifest()
        ver = next((v for v in man["versions"] if v["id"] == vid), None)
        if not ver:
            raise SystemExit(f"Mojang 清单里没有版本 {vid}")
        meta = json.loads(urllib.request.urlopen(
            urllib.request.Request(ver["url"], headers={"User-Agent": "mcauto/1"}),
            timeout=30).read())
        jp.write_text(json.dumps(meta), encoding="utf-8")
        client = (meta.get("downloads") or {}).get("client")
        if client and not jj.exists():
            print(f"[launcher] 下载原版 {vid} 客户端 jar …")
            urllib.request.urlretrieve(client["url"], jj)
    return jp, (jj if jj.exists() else None)


def resolve_version_json(mc_dir: Path, version: str) -> tuple[dict, Path | None]:
    """解析 inheritsFrom 链，返回 (合并后的 json, 原版客户端 jar 路径)。"""
    vdir = mc_dir / "versions" / version
    js = list(vdir.glob("*.json"))
    if not js:
        raise SystemExit(f"版本不存在：{vdir}")
    child = json.loads(js[0].read_text(encoding="utf-8"))
    if not child.get("inheritsFrom"):
        return child, None

    parent_id = child["inheritsFrom"]
    parent = None
    pdir = mc_dir / "versions" / parent_id
    pjs = list(pdir.glob("*.json")) if pdir.exists() else []
    if pjs:
        parent = json.loads(pjs[0].read_text(encoding="utf-8"))
        parent_jar = pdir / f"{parent_id}.jar"
        vanilla_jar = parent_jar if parent_jar.exists() else None
    else:
        print(f"[launcher] 本机没有原版 {parent_id}，从 Mojang 补到缓存")
        pj, vanilla_jar = ensure_vanilla(parent_id)
        parent = json.loads(pj.read_text(encoding="utf-8"))

    # 合并：父的库在前、子的库在后（同名后者覆盖）；参数父前子后
    merged = dict(parent)
    for k in ("mainClass", "assetIndex", "assets", "downloads", "logging",
              "javaVersion", "type", "releaseTime", "time", "id"):
        if k in child:
            merged[k] = child[k]
    libs = list(parent.get("libraries") or [])
    child_libs = child.get("libraries") or []
    names_child = {l.get("name") for l in child_libs}
    libs = [l for l in libs if l.get("name") not in names_child] + child_libs
    merged["libraries"] = libs

    pa = parent.get("arguments") or {}
    ca = child.get("arguments") or {}
    merged["arguments"] = {
        "jvm": list(pa.get("jvm") or []) + list(ca.get("jvm") or []),
        "game": list(pa.get("game") or []) + list(ca.get("game") or []),
    }
    if child.get("minecraftArguments"):
        merged["minecraftArguments"] = child["minecraftArguments"]
    if child.get("jar"):
        merged["jar"] = child["jar"]
    print(f"[launcher] 已合并继承链：{version} ← {parent_id}")
    return merged, vanilla_jar


def build(mc_dir: Path, version: str, game_dir: Path, username: str,
          java: str, extra_jvm: list[str], width: int, height: int,
          agent: str | None, export_path: str | None) -> list[str]:
    vdir = mc_dir / "versions" / version
    vj, vanilla_jar = resolve_version_json(mc_dir, version)
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
        if art:
            p = libs_dir / art["path"]
            if p.exists():
                cp.append(str(p))
            continue
        # 没有 downloads.artifact 的条目（Fabric 由 PCL 安装时常见）：
        # 用 Maven 坐标 group:artifact:version[:classifier] 推导本地路径
        name = lib.get("name") or ""
        parts = name.split(":")
        if len(parts) < 3:
            continue
        # 注意：这里不能叫 version —— 会覆盖函数参数的 version，
        # 导致后面拼「版本自己的 jar」时路径全错（踩过：MC jar 因此没进 classpath）
        group, artifact, lib_version = parts[0], parts[1], parts[2]
        classifier = parts[3] if len(parts) > 3 else ""
        fname = f"{artifact}-{lib_version}" + (f"-{classifier}" if classifier else "") + ".jar"
        p = libs_dir / group.replace(".", "/") / artifact / lib_version / fname
        if p.exists():
            cp.append(str(p))
    # 版本自己的 jar（PCL 生成的扁平版本是完整客户端 jar）
    vjar = vdir / f"{version}.jar"
    # Forge/NeoForge 用模块路径自己提供 minecraft 模块（-p 里带目标 jar）。
    # 此时**不能**再把原版 jar 塞进 classpath：会出现两个模块都导出
    # net.minecraft.server，直接 java.lang.module.ResolutionException。
    has_module_path = any(a in ("-p", "--module-path") for a in vj.get("arguments", {}).get("jvm", [])
                          if isinstance(a, str))
    if vjar.exists():
        cp.append(str(vjar))
    elif vanilla_jar is not None and not has_module_path:
        cp.append(str(vanilla_jar))

    # 去重：1.21.1 的 version json 里同一路径会列两次（原版库 + NeoForge 追加库有重叠），
    # 重复项会让 Bootstraplauncher 的 UnionFileSystem 抛 duplicateKeyException，客户端秒退。
    # 补齐缺失库（PCL 没装过的版本本机没有这些文件）
    try:
        for extra_path in ensure_library_files(vj, libs_dir):
            cp.append(extra_path)
    except Exception as e:
        print(f"[launcher] 补库失败: {e}")

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
