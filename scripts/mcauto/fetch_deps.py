#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""按 mods.toml / fabric.mod.json 的依赖声明，自动下载前置模组。

两个源，按顺序试：
  1. **Modrinth**（首选）：开放 API，返回直链，无防盗链
       https://api.modrinth.com/v2/search?query=<modid>&facets=[["project_type:mod"]]
       https://api.modrinth.com/v2/project/<slug>/version?loaders=[..]&game_versions=[..]
  2. **CurseForge**（兜底）：cfwidget 拿文件 id → forgecdn 直链
       https://api.cfwidget.com/minecraft/mc-mods/<slug>
       https://mediafilez.forgecdn.net/files/<id//1000>/<id%1000>/<file>

下载后要**回读 jar 的 modId 校验**——名字对不上就丢掉，防止下错包。

用法：
    python fetch_deps.py --jar <目标.json> --mc 1.21.1 --loader neoforge
    python fetch_deps.py --jar <目标.jar> --dry-run     # 只看要下什么
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import time
import urllib.request
import zipfile
from pathlib import Path

CACHE = Path(r"E:\Mod\百科-语料\mcauto-cache\mods")
UA = {"User-Agent": "mcauto/1 (mcmod page tooling)"}

# 已知 modId → 下载 slug 的映射（Modrinth/CF 的 slug 常与 modId 不同）
SLUG_HINTS = {
    "touhou_little_maid": "touhou-little-maid",
    "curios": "curios",
    "patchouli": "patchouli",
    "geckolib": "geckolib",
    "create": "create",
    "architectury": "architectury-api",
    "cloth_config": "cloth-config",
    "fabric_api": "fabric-api",
    "kubejs": "kubejs",
}

# 不该去下载的（由加载器/游戏本体提供）
SKIP = {"minecraft", "neoforge", "forge", "fabricloader", "fabric", "java"}


def http_json(url: str, timeout: int = 25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def read_deps(jar: Path) -> tuple[str, list[tuple[str, str, bool]]]:
    """返回 (自身modId, [(depId, versionRange, required), ...])"""
    with zipfile.ZipFile(jar) as z:
        names = z.namelist()
        toml = [n for n in names if n.endswith(("neoforge.mods.toml", "mods.toml"))]
        if toml:
            t = z.read(toml[0]).decode("utf-8", errors="ignore")
            own = None
            # 第一个 modId 是自身；dependencies 块里的才算依赖
            m_all = re.findall(r'\[\[mods\]\]([\s\S]*?)(?=\[\[|\Z)', t)
            if m_all:
                mm = re.search(r'modId\s*=\s*"([^"]+)"', m_all[0])
                own = mm.group(1) if mm else None
            deps = []
            for blk in re.findall(r'\[\[dependencies\.[^\]]+\]\]([\s\S]*?)(?=\[\[|\Z)', t):
                mid = re.search(r'modId\s*=\s*"([^"]+)"', blk)
                if not mid:
                    continue
                vr = re.search(r'versionRange\s*=\s*"([^"]+)"', blk)
                mand = re.search(r'mandatory\s*=\s*(\w+)', blk)
                typ = re.search(r'type\s*=\s*"([^"]+)"', blk)
                required = (mand.group(1).lower() != "false") if mand else (
                    (typ.group(1) == "required") if typ else True)
                deps.append((mid.group(1), vr.group(1) if vr else "", required))
            return own or jar.stem, deps

        fab = [n for n in names if n.endswith("fabric.mod.json")]
        if fab:
            d = json.loads(z.read(fab[0]).decode("utf-8", errors="ignore"))
            deps = [(k, str(v), True) for k, v in (d.get("depends") or {}).items()]
            return d.get("id", jar.stem), deps
    return jar.stem, []


def modrinth_find(modid: str, mc: str, loader: str) -> tuple[str, str, str] | None:
    """返回 (slug, version_number, download_url)。

    先按 slug **直接查**（1 次请求，4 秒左右）；
    只有直查 404 才退回搜索。之前一上来就 search，每命中一次再查一遍 version，
    串行十几次请求 + 25 秒超时 = 看起来像卡死。
    """
    slug = SLUG_HINTS.get(modid, modid.replace("_", "-"))
    qs = urllib.parse.urlencode({
        "loaders": json.dumps([loader]),
        "game_versions": json.dumps([mc]),
    })
    for s in (slug, modid.replace("_", "-")):
        try:
            vs = http_json(f"https://api.modrinth.com/v2/project/{s}/version?{qs}", timeout=12)
        except Exception as e:
            print(f"    直查 {s} 失败: {type(e).__name__}")
            continue
        if vs:
            v = vs[0]
            files = v.get("files") or []
            if files:
                f = next((x for x in files if x.get("primary")), files[0])
                return s, v.get("version_number", ""), f["url"]

    # 兜底：搜索（限制命中数，每个只查一次）
    try:
        res = http_json("https://api.modrinth.com/v2/search?"
                        + urllib.parse.urlencode({"query": modid, "limit": 5}), timeout=12)
    except Exception:
        return None
    for hit in res.get("hits", [])[:5]:
        s = hit.get("slug")
        if not s:
            continue
        try:
            vs = http_json(f"https://api.modrinth.com/v2/project/{s}/version?{qs}", timeout=12)
        except Exception:
            continue
        if vs and vs[0].get("files"):
            v = vs[0]
            f = next((x for x in v["files"] if x.get("primary")), v["files"][0])
            return s, v.get("version_number", ""), f["url"]
    return None


def cf_find(modid: str, mc: str) -> tuple[str, str] | None:
    """CurseForge 兜底：cfwidget 拿 files → forgecdn 直链。返回 (slug, url)"""
    slug = SLUG_HINTS.get(modid, modid.replace("_", "-"))
    try:
        d = http_json(f"https://api.cfwidget.com/minecraft/mc-mods/{slug}")
    except Exception:
        return None
    files = d.get("files") or []
    cand = [f for f in files if mc in (f.get("versions") or [])]
    if not cand:
        cand = files
    if not cand:
        return None
    f = cand[-1]
    fid = f["id"]
    name = f.get("display") or f.get("name") or f"{slug}.jar"
    url = f"https://mediafilez.forgecdn.net/files/{fid//1000}/{fid%1000}/{urllib.parse.quote(name)}"
    return slug, url


def verify(jar: Path, expect_modid: str) -> bool:
    try:
        own, _ = read_deps(jar)
        return own == expect_modid
    except Exception:
        return False


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"    下载 {url.split('/')[-1][:70]}", flush=True)
    req = urllib.request.Request(url, headers=UA)
    t0 = time.time()
    done = 0
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            pct = f"{done*100//total}%" if total else "?"
            spd = done / max(time.time() - t0, 0.001) / 1024 / 1024
            print(f"      {pct:>4}  {done/1024/1024:5.1f}/"
                  f"{total/1024/1024:5.1f} MB  {spd:4.1f} MB/s", end="\r", flush=True)
    print(f"\n    完成 {dest.stat().st_size/1024/1024:.1f} MB，用时 {time.time()-t0:.0f}s", flush=True)
    return dest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True, help="目标模组 jar")
    ap.add_argument("--mc", required=True, help="MC 版本，如 1.21.1")
    ap.add_argument("--loader", default="neoforge", help="neoforge / forge / fabric")
    ap.add_argument("--include-optional", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    jar = Path(a.jar)
    own, deps = read_deps(jar)
    print(f"目标: {jar.name}")
    print(f"自身 modId: {own}\n")
    if not deps:
        print("没有声明依赖")
        return 0

    need = [d for d in deps if d[0] not in SKIP and (d[2] or a.include_optional)]
    print(f"需要前置 {len(need)} 个：")
    for mid, vr, req in need:
        print(f"  {mid:28} range={vr or '-':24} {'必需' if req else '可选'}")

    got: list[Path] = []
    for mid, vr, req in need:
        if a.dry_run:
            continue
        print(f"\n[{mid}]")
        hit = modrinth_find(mid, a.mc, a.loader)
        src = "modrinth"
        if not hit:
            print("    Modrinth 没找到，试 CurseForge")
            cf = cf_find(mid, a.mc)
            if not cf:
                print(f"    ✗ {mid} 两个源都没找到")
                continue
            slug, url = cf
            hit = (slug, "", url)
            src = "curseforge"
        slug, ver, url = hit
        fname = urllib.parse.unquote(url.split("/")[-1].split("?")[0])
        dest = CACHE / f"{mid}" / fname
        if dest.exists() and verify(dest, mid):
            print(f"    已有缓存 {dest.name}")
            got.append(dest)
            continue
        try:
            download(url, dest)
        except Exception as e:
            print(f"    ✗ 下载失败: {e}")
            continue
        if verify(dest, mid):
            print(f"    ✓ {dest.name}（modId 校验通过，来源 {src}）")
            got.append(dest)
        else:
            print(f"    ✗ {dest.name} modId 校验失败，删除")
            dest.unlink(missing_ok=True)

    print(f"\n拿到 {len(got)} 个前置：")
    for g in got:
        print(f"  {g}")
    return 0 if got or a.dry_run else 1


if __name__ == "__main__":
    raise SystemExit(main())
