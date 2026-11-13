#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""用官方服务端生成一个超平坦存档，供客户端 quickPlay 加载。

为什么不用客户端造世界：客户端造世界要走 GUI（选类型、点创建），与「完全自动」冲突。
服务端一条命令就能生成，且存档格式与客户端通用（同 MC 版本 DataVersion 一致）。

用法：
    python make_world.py --version 1.21.1 --java "C:\Program Files\Java\jdk-21.0.12\bin\java.exe"

产物：
    <mcauto-work>\worlds\<version>-flat\   ← 可直接拷进 saves/
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

CACHE = Path(r"E:\Mod\百科-语料\mcauto-cache")
WORLDS = Path(r"E:\Mod\百科-语料\mcauto-worlds")


def download_server(version: str) -> Path:
    """从 Mojang 版本清单拿 server.jar。"""
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / f"server-{version}.jar"
    if out.exists() and out.stat().st_size > 1_000_000:
        print(f"  已有 {out.name}（{out.stat().st_size//1024//1024} MB）")
        return out
    print("  查询版本清单…")
    req = urllib.request.Request(
        "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json",
        headers={"User-Agent": "mcauto/1"})
    manifest = json.loads(urllib.request.urlopen(req, timeout=30).read())
    ver = next((v for v in manifest["versions"] if v["id"] == version), None)
    if not ver:
        raise SystemExit(f"版本 {version} 不在清单里")
    meta = json.loads(urllib.request.urlopen(
        urllib.request.Request(ver["url"], headers={"User-Agent": "mcauto/1"}),
        timeout=30).read())
    url = meta["downloads"]["server"]["url"]
    print(f"  下载 server.jar … {url[:70]}")
    urllib.request.urlretrieve(url, out)
    print(f"  ✓ {out.name}（{out.stat().st_size//1024//1024} MB）")
    return out


def generate(jar: Path, version: str, java: str) -> Path:
    target = WORLDS / f"{version}-flat"
    if (target / "level.dat").exists():
        print(f"  已有存档 {target}")
        return target
    work = CACHE / f"server-run-{version}"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    (work / "eula.txt").write_text("eula=true\n", encoding="utf-8")
    (work / "server.properties").write_text("\n".join([
        "level-type=minecraft:flat",
        "level-name=world",
        "generate-structures=false",
        "spawn-protection=0",
        "online-mode=false",
        "allow-nether=false",
        "max-tick-time=-1",
        "sync-chunk-writes=false",
        "view-distance=4",
        "difficulty=peaceful",
        "gamemode=creative",
        "enable-command-block=true",
    ]) + "\n", encoding="utf-8")

    print("  启动服务端生成世界（约 20~60 秒）…")
    proc = subprocess.Popen(
        [java, "-Xmx1G", "-jar", str(jar), "--nogui"],
        cwd=str(work), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")

    ok = False
    deadline = time.time() + 180
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            break
        if "Done (" in line or "For help, type" in line:
            print("  服务端就绪，发送 stop …")
            ok = True
            try:
                proc.stdin.write("stop\n")
                proc.stdin.flush()
            except Exception:
                pass
            break
    try:
        proc.wait(timeout=60)
    except subprocess.TimeoutExpired:
        proc.kill()
    if not ok:
        raise SystemExit("服务端没有正常启动，检查日志")

    src = work / "world"
    if not (src / "level.dat").exists():
        raise SystemExit(f"没有生成 world 目录：{src}")
    WORLDS.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(src, target)
    for junk in ("session.lock", "playerdata", "advancements", "stats"):
        p = target / junk
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.exists():
            p.unlink()
    print(f"  ✓ 存档已就绪：{target}")
    return target


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="MC 版本，如 1.21.1")
    ap.add_argument("--java", default=r"C:\Program Files\Java\jdk-21.0.12\bin\java.exe")
    a = ap.parse_args()
    print(f"生成超平坦存档：MC {a.version}")
    jar = download_server(a.version)
    generate(jar, a.version, a.java)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
