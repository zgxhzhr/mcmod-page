#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""自动补齐「没声明但硬引用」的依赖，然后重跑。

为什么需要
----------
不少模组的 mods.toml 里不写依赖，但代码里直接 new 别人的类：

    Failure message: Malstone Mod (malstone) has failed to load correctly
        java.lang.NoClassDefFoundError: com/sammy/malum/common/item/IVoidItem

这种只有跑到崩溃才知道。这个脚本把「崩溃 → 缺类 → 找模组 → 下载 → 重跑」
串成闭环，最多重试 N 轮。

用法：
    python autodeps.py --version "1.20.1-Forge_47.4.26" --mode iconr \
        --mc-dir "E:\PCL\.minecraft" --target-modid malstone \
        --mods tool.jar target.jar --work ... --mc 1.20.1 --loader forge
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
CACHE = Path(r"E:\Mod\百科-语料\mcauto-cache\mods")
UA = {"User-Agent": "mcauto/1"}

# 已知「包前缀 → Modrinth/CF slug」。命中就直接下，不用猜。
PKG_TO_SLUG = {
    "top/theillusivec4/curios": ["curios"],
    "com/sammy/malum": ["malum"],
    "com/github/tartaricacid/touhoulittlemaid": ["touhou-little-maid"],
    "software/bernie/geckolib": ["geckolib"],
    "vazkii/patchouli": ["patchouli"],
    "dev/architectury": ["architectury-api"],
    "com/simibubi/create": ["create"],
    "mezz/jei": ["jei"],
    "com/blamejared": ["kubejs", "crafttweaker"],
    "net/darkhax": [],
    # 反直觉的：直查 lodestone 会命中同名的「Lodestone Warps」，真库是 lodestonelib
    "lodestone": ["lodestonelib"],
    "dev/ftb/mods/ftbquests": ["ftb-quests"],
    "dev/ftb/mods/ftbteams": ["ftb-teams"],
    "org/valkyrienskies": ["valkyrien-skies"],
}

# 出现在缺类里也不用补的（加载器/游戏本体/库）
SKIP_PREFIX = (
    "net/minecraft/", "net/minecraftforge/", "net/neoforged/", "cpw/",
    "java/", "javax/", "com/mojang/", "io/netty/", "org/lwjgl/",
    "com/google/", "org/apache/", "org/slf4j/", "it/unimi/", "org/joml/",
    "org/spongepowered/", "net/fabricmc/", "org/quiltmc/",
)


def http_json(url: str, timeout: int = 25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def installed_package_prefixes(jars: list[Path]) -> set[str]:
    """扫已安装 jar 里出现的包前缀（取到第三段）。

    用来排除**误报**：比如 LMS 自己会尝试加载 com.xkball.let_me_see_see.LMSAgent
    并抛 ClassNotFoundException（它自带的 attach 逻辑，属于正常现象），
    这个类其实就在 LMS 自己 jar 里，不该被当成缺依赖。
    """
    prefixes: set[str] = set()
    for j in jars:
        if not j.exists():
            continue
        try:
            import zipfile
            with zipfile.ZipFile(j) as z:
                n = 0
                for name in z.namelist():
                    if not name.endswith(".class"):
                        continue
                    parts = name[:-6].split("/")
                    if len(parts) >= 3:
                        prefixes.add("/".join(parts[:3]))
                    elif len(parts) >= 2:
                        prefixes.add("/".join(parts[:2]))
                    n += 1
                    if n > 4000:
                        break
        except Exception:
            continue
    return prefixes


def scan_missing(work: Path) -> list[str]:
    """从 agent.log 和 crash-reports 里扫出缺失的全限定类名。"""
    found: list[str] = []
    patterns = [
        # 硬引用：NoClassDefFoundError: com/sammy/malum/...
        re.compile(r"NoClassDefFoundError:\s*([\w/$]+)"),
        re.compile(r"ClassNotFoundException:\s*([\w.$]+)"),
        # 声明式：Mod malum requires lodestone 1.20.1-1.6.4 or above
        re.compile(r"requires\s+([a-z0-9_]{3,})\s+[\d.]"),
        # 声明式：Currently, lodestone is not installed
        re.compile(r"Currently,\s+([a-z0-9_]{3,})\s+is not installed"),
    ]
    candidates = []
    log = work / "agent.log"
    if log.exists():
        candidates.append(log)
    game = work / "game"
    if game.exists():
        candidates += list(game.glob("crash-reports/*.txt"))
        candidates.append(game / "logs" / "latest.log")
    for f in candidates:
        if not f.exists():
            continue
        try:
            txt = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for pat in patterns:
            for m in pat.finditer(txt):
                name = m.group(1).replace(".", "/")
                if name not in found:
                    found.append(name)
    return found


def pkg_candidates(fqcn: str) -> list[str]:
    """全限定类名 → 可能的包前缀（由长到短，最多三段）"""
    parts = fqcn.split("/")
    out = []
    for n in range(min(4, len(parts)), 1, -1):
        out.append("/".join(parts[:n]))
    return out


def slugs_for(fqcn: str) -> list[str]:
    """把缺类/缺 modId 映射到可能的 Modrinth slug。

    两种输入：
      - 全限定类名  com/sammy/malum/common/item/IVoidItem
      - 纯 modId     lodestone
    """
    if "/" not in fqcn and "." not in fqcn:
        # 纯 modId：直接当 slug 试（下划线换连字符）
        return [fqcn.replace("_", "-"), fqcn]
    for pkg in pkg_candidates(fqcn):
        if pkg in PKG_TO_SLUG:
            return list(PKG_TO_SLUG[pkg])
    # 猜：第二段通常是组织（theillusivec4 / sammy / tartaricacid），第三段才是模组名
    parts = fqcn.split("/")
    guesses = []
    if len(parts) >= 3:
        guesses.append(parts[2])
    if len(parts) >= 2:
        guesses.append(parts[1])
    STOP = {"mods", "api", "core", "lib", "common", "client", "server",
            "utils", "util", "event", "events", "data", "base", "main", "init"}
    cleaned = []
    for g in guesses:
        g = g.lower().replace("_", "-")
        if g and g not in cleaned and len(g) > 2 and g not in STOP:
            cleaned.append(g)
    return cleaned


def search_slugs(query: str, mc: str, loader: str) -> list[str]:
    """Modrinth 搜索兜底：按下载量排序返回候选 slug。

    有些 modId 跟项目 slug 对不上（lodestone → lodestonelib），
    直查会命中同名但无关的项目，所以失败后必须搜索。
    """
    try:
        res = http_json("https://api.modrinth.com/v2/search?" + urllib.parse.urlencode({
            "query": query, "limit": 8,
            "facets": json.dumps([["project_type:mod"], [f"versions:{mc}"]]),
        }), timeout=25)
    except Exception:
        return []
    hits = sorted(res.get("hits", []), key=lambda h: -h.get("downloads", 0))
    return [h["slug"] for h in hits if h.get("slug")]


def jar_provides(jar: Path, expected_prefix: str) -> bool:
    """校验下载到的 jar 里确实有缺失的包路径，防止下错同名/无关模组"""
    if not expected_prefix:
        return True
    try:
        import zipfile
        with zipfile.ZipFile(jar) as z:
            return any(n.startswith(expected_prefix.rstrip("/") + "/") for n in z.namelist())
    except Exception:
        return False


def fetch_slug(slug: str, mc: str, loader: str, expect_prefix: str = "") -> Path | None:
    """按 slug 下最新匹配版本，返回本地 jar 路径；直查失败则搜索兜底"""
    if not slug:
        return None
    tried = [slug, slug.replace("-", "")]
    for cand in search_slugs(slug, mc, loader):
        if cand not in tried:
            tried.append(cand)

    qs = urllib.parse.urlencode({
        "loaders": json.dumps([loader]),
        "game_versions": json.dumps([mc]),
    })
    for s in tried:
        try:
            vs = http_json(f"https://api.modrinth.com/v2/project/{s}/version?{qs}", timeout=20)
        except Exception:
            continue
        if not vs:
            continue
        v = vs[0]
        files = v.get("files") or []
        if not files:
            continue
        f = next((x for x in files if x.get("primary")), files[0])
        fname = urllib.parse.unquote(f["url"].split("/")[-1].split("?")[0])
        dest = CACHE / s / fname
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            print(f"    下载 {fname} …", flush=True)
            req = urllib.request.Request(f["url"], headers=UA)
            with urllib.request.urlopen(req, timeout=180) as r, open(dest, "wb") as out:
                shutil.copyfileobj(r, out)
        if expect_prefix and not jar_provides(dest, expect_prefix):
            print(f"    ✗ {dest.name} 里没有 {expect_prefix}，丢弃")
            dest.unlink(missing_ok=True)
            continue
        print(f"    ✓ {dest.name}  {dest.stat().st_size/1024/1024:.1f} MB（{v.get('version_number')}）")
        return dest
    return None


def run_once(argv: list[str]) -> int:
    print("  $ " + " ".join(f'"{a}"' if " " in a else a for a in argv[:6]) + " …", flush=True)
    return subprocess.call(argv)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--mode", required=True)
    ap.add_argument("--mc-dir", default=r"E:\PCL\.minecraft")
    ap.add_argument("--target-modid", required=True)
    ap.add_argument("--mods", nargs="+", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--mc", required=True, help="MC 版本，如 1.20.1")
    ap.add_argument("--loader", required=True, help="forge / neoforge / fabric")
    ap.add_argument("--rounds", type=int, default=3, help="最多补几轮依赖")
    ap.add_argument("--timeout", default="300")
    a = ap.parse_args()

    mods = [Path(m) for m in a.mods]
    for r in range(a.rounds + 1):
        argv = [sys.executable, str(HERE / "run.py"),
                "--version", a.version, "--mode", a.mode,
                "--mc-dir", a.mc_dir, "--target-modid", a.target_modid,
                "--mods", *[str(m) for m in mods],
                "--work", a.work, "--timeout", a.timeout]
        if a.mode.endswith("2"):
            argv.append("--self-trigger")
        argv.append("--console")

        print(f"\n=== 第 {r+1} 轮 ===", flush=True)
        code = run_once(argv)
        if code == 0:
            print("\n✓ 完成")
            return 0
        if r == a.rounds:
            break

        work = Path(a.work)
        missing = scan_missing(work)
        # 已经安装的模组自己带的包不算缺失（常见误报）
        installed = installed_package_prefixes(mods)
        before = len(missing)
        missing = [m for m in missing
                   if not any(m.startswith(p + "/") or m == p for p in installed)]
        if before != len(missing):
            print(f"  忽略 {before - len(missing)} 个已安装模组自带的类（误报）")
        missing = [m for m in missing
                   if not any(m.startswith(p) for p in SKIP_PREFIX)
                   and m not in ("minecraft", "forge", "neoforge", "fabricloader", "java")]
        if not missing:
            print("✗ 失败，但日志里没有缺类信息，无法自动补依赖")
            return 1
        print(f"\n检测到缺类 {len(missing)} 个：")
        for m in missing[:6]:
            print(f"  {m}")

        added = False
        seen_slugs: set[str] = set()
        for fqcn in missing:
            slugs = slugs_for(fqcn)
            print(f"\n[{fqcn}] 候选 slug: {slugs}")
            for slug in slugs:
                if slug in seen_slugs:
                    continue
                seen_slugs.add(slug)
                expect = "" if "/" not in fqcn and "." not in fqcn else \
                    "/".join(fqcn.replace(".", "/").split("/")[:3])
                jar = fetch_slug(slug, a.mc, a.loader, expect)
                if jar and jar not in mods:
                    mods.append(jar)
                    added = True
                    break
        if not added:
            print("✗ 没能自动补上依赖")
            return 1

    print("✗ 重试用尽")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
