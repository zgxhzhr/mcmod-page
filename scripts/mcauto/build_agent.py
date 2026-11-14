#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""编译 mcauto-agent.jar（只需 JDK，不需要 MC 依赖、不需要 MDK、不需要映射）。

agent 只 import JDK 类（java.lang.reflect / java.nio.file / java.lang.instrument），
所有 MC 与 mod 的类都是运行时反射拿的，所以编译期零依赖。

用法：
    python build_agent.py
产物：
    scripts/mcauto/mcauto-agent.jar
"""
from __future__ import annotations

# ── 路径配置：统一从 config.py 读（换机器只改 config.json）──
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import config as _cfg

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "agent" / "AgentMain.java"
OUT_DIR = HERE / "agent-build"
JAR = HERE / "mcauto-agent.jar"
JAR8 = HERE / "mcauto-agent8.jar"   # Java 8 版：1.12.2 / 1.7.10 用

JDKS = [str(_cfg.java_home(k)) for k in ("21", "17", "25") if _cfg.java_home(k).exists()]

MANIFEST = """Manifest-Version: 1.0
Premain-Class: mcauto.AgentMain
Can-Redefine-Classes: false
Can-Retransform-Classes: false
"""


def find_jdk() -> Path:
    for d in JDKS:
        p = Path(d)
        if (p / "bin" / "javac.exe").exists():
            return p
    raise SystemExit("找不到 JDK（需要 javac），请检查 JDKS 列表")


def run(cmd: list[str]) -> None:
    print("  $ " + " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr)
        raise SystemExit(f"命令失败（{r.returncode}）")
    if r.stdout.strip():
        print(r.stdout.strip())


def main() -> int:
    jdk = find_jdk()
    print(f"JDK: {jdk}")
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)
    classes = OUT_DIR / "classes"
    classes.mkdir()

    run([str(jdk / "bin" / "javac.exe"), "-encoding", "UTF-8",
         "-source", "17", "-target", "17",
         "-d", str(classes), str(SRC)])

    mf = OUT_DIR / "MANIFEST.MF"
    mf.write_text(MANIFEST, encoding="utf-8")
    if JAR.exists():
        JAR.unlink()
    run([str(jdk / "bin" / "jar.exe"), "cfm", str(JAR), str(mf), "-C", str(classes), "."])

    size = JAR.stat().st_size
    print(f"\n✓ {JAR.name}  {size} bytes")

    # ---- Java 8 版：给 1.12.2 / 1.7.10 用（那些版本的 JVM 只认 class 52）----
    classes8 = OUT_DIR / "classes8"
    if classes8.exists():
        shutil.rmtree(classes8)
    classes8.mkdir()
    run([str(jdk / "bin" / "javac.exe"), "-encoding", "UTF-8", "--release", "8",
         "-d", str(classes8), str(SRC)])
    if JAR8.exists():
        JAR8.unlink()
    run([str(jdk / "bin" / "jar.exe"), "cfm", str(JAR8), str(mf), "-C", str(classes8), "."])
    print(f"✓ {JAR8.name}  {JAR8.stat().st_size} bytes（Java 8 字节码）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
