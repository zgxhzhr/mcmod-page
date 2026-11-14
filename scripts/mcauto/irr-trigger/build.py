#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""编译 IRR 自动化触发器 mod（IRR-mcauto）。

产物：build/irr-mcauto-<mcver>.jar
依赖：只需要 Forge 的 universal jar 当编译 classpath ——
      代码里只 import Forge 自己的类，MC 的东西全走反射，所以不需要 MC jar、
      不需要 ForgeGradle、不需要映射，javac + jar 两条命令就够。

用法：
    python build.py --forge "I:\PCL\.minecraft\libraries\net\minecraftforge\forge\1.16.5-36.2.39\forge-1.16.5-36.2.39-universal.jar" --mc 1.16.5
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SRC_DIR = HERE / "src"
BUILD = HERE / "build"

JDKS = [
    r"C:\Program Files\Java\jdk-21.0.12",
    r"C:\Program Files\Java\jdk-17",
]

MODS_TOML = """modLoader="javafml"
loaderVersion="[36,)"
license="MIT"
[[mods]]
modId="irrmcauto"
version="1.0.0"
displayName="IRR mcauto Trigger"
description=<<<DESC>>>
给 IRR 加自动化的辅助模组：进世界后自动调用 IRR 的导出。
读 -Dmcauto.modid / -Dmcauto.world / -Dmcauto.delay。
<<<DESC>>>
[[dependencies.irrmcauto]]
    modId="forge"
    mandatory=true
    versionRange="[36,)"
    ordering="NONE"
    side="CLIENT"
[[dependencies.irrmcauto]]
    modId="minecraft"
    mandatory=true
    versionRange="[1.16.5,1.17)"
    ordering="NONE"
    side="CLIENT"
""".replace("<<<DESC>>>", chr(39)*3)


def find_jdk() -> Path:
    for d in JDKS:
        p = Path(d)
        if (p / "bin" / "javac.exe").exists():
            return p
    raise SystemExit("找不到 JDK")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--forge", required=True, help="Forge universal jar 路径")
    ap.add_argument("--mc", default="1.16.5")
    ap.add_argument("--extra-cp", default="", help="额外的 classpath，分号分隔")
    a = ap.parse_args()

    forge = Path(a.forge)
    if not forge.exists():
        raise SystemExit(f"找不到 Forge jar：{forge}")

    jdk = find_jdk()
    print(f"JDK: {jdk}")
    if BUILD.exists():
        shutil.rmtree(BUILD)
    classes = BUILD / "classes"
    classes.mkdir(parents=True)

    srcs = [str(p) for p in SRC_DIR.rglob("*.java")]
    cmd = [str(jdk / "bin" / "javac.exe"), "-encoding", "UTF-8", "--release", "8",
           "-cp", str(forge) + (";" + a.extra_cp if a.extra_cp else ""),
           "-d", str(classes)] + srcs
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr)
        raise SystemExit("编译失败")
    print(f"✓ 编译 {len(srcs)} 个源文件")

    (classes / "META-INF").mkdir(exist_ok=True)
    (classes / "META-INF" / "mods.toml").write_text(MODS_TOML, encoding="utf-8")
    # 1.16.5 的模组 jar 同时也是资源包，缺 pack.mcmeta 可能被跳过
    (classes / "pack.mcmeta").write_text(
        '{"pack": {"description": "irr-mcauto", "pack_format": 6}}', encoding="utf-8")

    jar = BUILD / f"irr-mcauto-{a.mc}.jar"
    r = subprocess.run([str(jdk / "bin" / "jar.exe"), "cf", str(jar), "-C", str(classes), "."],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        raise SystemExit("打包失败")
    print(f"✓ {jar}  {jar.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
