#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""批量导出：一堆模组 jar → 每个模组一个文件夹，里面是**工具原样产出**的文件。

为什么要批处理而不是转换
------------------------
这些导出工具（LMS / IconRenderer）和它们的 JSON 格式都是 mcmod 站方提供的，
产物站方直接能吃。所以这里**不做任何格式转换**，只负责：

  1. 找到每个模组的 modId（没有就自动读）
  2. 调 autodeps.py：缺前置自己补，最多补 N 轮
  3. 正常导出后，把工具的输出目录**原样**拷进 out/<modid>/native/
  4. 记一份 manifest（哪个 jar、哪个版本、几条、多大），方便交付核对

一个模组可能要跑两趟（NeoForge 的 LMS：物品用 lms、实体用 lmsent），
所以 job 里的 mode 支持写数组。

用法：
    python batch.py --jobs jobs.json --out "E:\Mod\百科-语料\handover"
    python batch.py --jobs jobs.json --out ... --dry-run     # 只检查任务
"""
from __future__ import annotations

# ── 路径配置：统一从 config.py 读（换机器只改 config.json）──
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import config as _cfg

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).parent

# 各 mode 的产物目录（相对 gameDir），与 run.py 的 TOOL_INFO 保持一致
OUT_DIRS = {
    "lms": "let_me_see_see",
    "lmsent": "let_me_see_see",
    "iconr": "IconRendererOutput",
    "iconr2": "IconRenderer",
    "irr": "export",
}


def read_modid(jar: Path) -> str:
    """从 mods.toml / fabric.mod.json 读 modId（跳过工具自身）"""
    try:
        with zipfile.ZipFile(jar) as z:
            names = z.namelist()
            for n in names:
                if n.endswith(("neoforge.mods.toml", "mods.toml")):
                    txt = z.read(n).decode("utf-8", errors="ignore")
                    for mid in re.findall(r'modId\s*=\s*"([^"]+)"', txt):
                        if mid not in ("minecraft", "forge", "neoforge"):
                            return mid
            for n in names:
                if n.endswith("fabric.mod.json"):
                    d = json.loads(z.read(n).decode("utf-8", errors="ignore"))
                    return d.get("id", "")
    except Exception:
        pass
    return ""


def run(cmd: list[str], cwd: Path | None = None) -> int:
    print("  $ " + " ".join(f'"{c}"' if " " in c else c for c in cmd[:8]) + (" …" if len(cmd) > 8 else ""),
          flush=True)
    return subprocess.call(cmd, cwd=str(cwd) if cwd else None)


def copy_native(game: Path, mode: str, dest: Path) -> list[str]:
    """把某个 mode 的工具输出目录原样拷到 dest/<mode>/<工具输出目录>。

    按 mode 分子目录：NeoForge 的 LMS 物品和实体是两个入口，
    输出都落在同一个 let_me_see_see/ 下，不分目录会互相覆盖（踩过）。
    """
    rel = OUT_DIRS.get(mode)
    if not rel:
        return []
    src = game / rel
    if not src.is_dir():
        return []
    target = dest / mode / rel.replace("/", "_")
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, target)
    return [str(f) for f in target.rglob("*") if f.is_file()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", required=True, help="任务 JSON 文件")
    ap.add_argument("--out", required=True, help="交付目录")
    ap.add_argument("--rounds", type=int, default=3, help="每个模组最多补几轮依赖")
    ap.add_argument("--timeout", default="300")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--keep-work", action="store_true",
                    help="保留 _work 下的临时 game 目录（几十 GB，交付前应删）")
    a = ap.parse_args()

    jobs = json.loads(Path(a.jobs).read_text(encoding="utf-8"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"共 {len(jobs)} 个任务\n")
    results = []
    for i, job in enumerate(jobs, 1):
        jar = Path(job["jar"])
        tools = [Path(t) for t in job.get("tools", [])]
        modes = job.get("mode") or ["iconr"]
        if isinstance(modes, str):
            modes = [modes]
        modid = job.get("modid") or read_modid(jar)
        mc = job["mc"]
        loader = job["loader"]
        version = job["version"]

        print(f"=== [{i}/{len(jobs)}] {modid or jar.name}  ({mc} / {loader}) ===")
        if not jar.exists():
            print(f"  ✗ jar 不存在：{jar}")
            results.append({"modid": modid, "jar": str(jar), "status": "missing_jar"})
            continue
        if not modid:
            print("  ✗ 读不出 modId")
            results.append({"modid": "", "jar": str(jar), "status": "no_modid"})
            continue
        if a.dry_run:
            print(f"  ok（modes={modes}, tools={[t.name for t in tools]}）")
            continue

        work = out / "_work" / modid
        started = time.time()
        # 每个 mode 跑一次（LMS 物品/实体是两个入口）
        ok_all = True
        per_mode = {}
        for mode in modes:
            autodeps = [sys.executable, str(HERE / "autodeps.py"),
                        "--version", version, "--mode", mode,
                        "--target-modid", modid,
                        "--mods", *[str(t) for t in tools], str(jar),
                        "--work", str(work / mode),
                        "--mc", mc, "--loader", loader,
                        "--rounds", str(a.rounds), "--timeout", a.timeout]
            code = run(autodeps)
            per_mode[mode] = code
            if code != 0:
                ok_all = False
                print(f"  ✗ mode={mode} 失败（退出码 {code}）")

        native_root = out / modid / "native"
        native: list[str] = []
        for mode in modes:
            native += copy_native(work / mode / "game", mode, native_root)

        files = [Path(p) for p in native]
        size = sum(f.stat().st_size for f in files if f.exists())
        manifest = {
            "modid": modid,
            "jar": str(jar),
            "mc": mc,
            "loader": loader,
            "version": version,
            "modes": per_mode,
            "status": "ok" if ok_all and native else ("partial" if native else "failed"),
            "files": len(files),
            "size_kb": round(size / 1024, 1),
            "seconds": round(time.time() - started),
            "native_dir": str((out / modid / "native").relative_to(out)),
        }
        (out / modid).mkdir(parents=True, exist_ok=True)
        (out / modid / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        results.append(manifest)
        print(f"  → {manifest['status']}：{manifest['files']} 个文件，{manifest['size_kb']} KB，"
              f"{manifest['seconds']} 秒")
        if not a.keep_work:
            shutil.rmtree(work, ignore_errors=True)
            print("  （已清理临时 game 目录）\n")

    with open(out / "manifest.jsonl", "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    ok = [r for r in results if r.get("status") == "ok"]
    print("=" * 50)
    print(f"完成 {len(ok)}/{len(results)}")
    print(f"{'模组':<34}{'状态':<10}{'文件':>6}{'KB':>9}{'秒':>6}")
    for r in results:
        print(f"  {r.get('modid',''):<32}{r.get('status',''):<10}"
              f"{r.get('files',0):>6}{r.get('size_kb',0):>9}{r.get('seconds',0):>6}")
    print(f"\n交付目录：{out}")
    return 0 if len(ok) == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
