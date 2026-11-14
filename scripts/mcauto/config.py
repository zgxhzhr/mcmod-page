#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""mcauto 的路径与工具配置。

为什么需要这个文件
------------------
之前路径散落在 8 个脚本里（`E:\Mod\百科-语料\...`、`I:\PCL\.minecraft`、JDK 路径……），
换一台机器要逐个改，等于不可移植。现在全部收在这里：

  · 优先读环境变量 MCAUTO_CONFIG 指向的 json
  · 否则读本目录的 config.json
  · 都没有就用下面的 DEFAULTS（本机默认值，保持向后兼容）

config.json 的键（写哪些覆盖哪些，没写的用默认）：

    {
      "cache":     "…\\mcauto-cache",          # 前置/原版/服务端 jar 的缓存
      "worlds":    "…\\mcauto-worlds",         # 预生成的超平坦存档
      "mc_dirs":   ["E:\\PCL\\.minecraft"],    # PCL 的 .minecraft（可多个，按顺序找）
      "java":      {"8": "…jdk8", "17": "…", "21": "…", "25": "…"},
      "gradle":    {"8": "…gradle-8.9", "7": "…", "4": "…", "2": "…"},
      "proxy":     "http://127.0.0.1:10808",
      "tool_jars": {"lms": "…", "irr_1_7_10": "…", …}   # 站方工具的本地路径（自备）
    }

**java["8"] 必须放在工作区之外**：DSH 会把工作区标成 Low 完整性级别，
从工作区里启动的 exe 继承 Low IL，连 %TEMP% 都写不了（Minecraft 的 jar 重映射会失败）。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

HERE = Path(__file__).parent

DEFAULTS = {
    "cache": r"E:\Mod\百科-语料\mcauto-cache",
    "worlds": r"E:\Mod\百科-语料\mcauto-worlds",
    "mc_dirs": [r"I:\PCL\.minecraft", r"E:\PCL\.minecraft"],
    "java": {
        "8": r"C:\Users\MKIII\jdks\jdk8",
        "17": r"C:\Program Files\Java\jdk-17",
        "21": r"C:\Program Files\Java\jdk-21.0.12",
        "25": r"C:\Program Files\Java\jdk-25",
    },
    "gradle": {
        "8": r"E:\Mod\其它项目\mcmod-exporters\_tools\gradle-8.9",
        "7": r"E:\Mod\其它项目\mcmod-exporters\_tools\gradle-7.6.4",
        "4": r"E:\Mod\其它项目\mcmod-exporters\_tools\gradle-4.10.3",
        "2": r"E:\Mod\其它项目\mcmod-exporters\_tools\gradle-2.14.1",
    },
    "proxy": "http://127.0.0.1:10808",
    "tool_jars": {},
    # 站方工具 jar 的搜索目录（自备的 jar 放这里，doctor 会扫）
    "tool_dirs": [
        r"E:\Mod\百科-语料\mcauto-cache\mods",
        r"C:\Users\MKIII\Downloads",
        r"E:\Mod\其它项目\mcmod-exporters\LetMeSeeSee\build\libs",
    ],
}


def _merged() -> dict:
    cfg = json.loads(json.dumps(DEFAULTS))  # 深拷贝
    path = os.environ.get("MCAUTO_CONFIG")
    candidate = Path(path) if path else (HERE / "config.json")
    if candidate.exists():
        try:
            user = json.loads(candidate.read_text(encoding="utf-8"))
            for k, v in user.items():
                if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                    cfg[k].update(v)
                else:
                    cfg[k] = v
        except Exception as e:  # 配置坏了不能拖垮主流程
            print(f"[config] 读 {candidate} 失败（用默认值）: {e}")
    return cfg


CFG = _merged()


# ── 目录 ──────────────────────────────────────────────
def cache_dir() -> Path:
    return Path(CFG["cache"])


def mods_cache() -> Path:
    return cache_dir() / "mods"


def worlds_dir() -> Path:
    return Path(CFG["worlds"])


def mc_dirs() -> list[Path]:
    return [Path(p) for p in CFG["mc_dirs"]]


def mc_dir(preferred: str | None = None) -> Path:
    """按顺序找第一个存在的 .minecraft；preferred 优先。"""
    if preferred:
        p = Path(preferred)
        if p.exists():
            return p
    for p in mc_dirs():
        if p.exists():
            return p
    return mc_dirs()[0]  # 都不存在也返回第一个，让调用方报错时路径可读


# ── Java ─────────────────────────────────────────────
def java_home(major: int | str) -> Path:
    return Path(CFG["java"].get(str(major), ""))


def javaw(major: int | str) -> str:
    """返回 javaw.exe（无控制台）。找不到就返回空串，由调用方报错。"""
    h = java_home(major)
    exe = h / "bin" / "javaw.exe"
    if exe.exists():
        return str(exe)
    return ""


def java_exe(major: int | str) -> str:
    return javaw(major).replace("javaw", "java")


# ── Gradle ───────────────────────────────────────────
def gradle_bat(major: int | str) -> str:
    h = Path(CFG["gradle"].get(str(major), ""))
    bat = h / "bin" / "gradle.bat"
    return str(bat) if bat.exists() else ""


# ── 代理 ─────────────────────────────────────────────
def proxy() -> str:
    return CFG.get("proxy", "")


def proxy_env() -> dict:
    p = proxy()
    if not p:
        return {}
    return {"HTTP_PROXY": p, "HTTPS_PROXY": p, "http_proxy": p, "https_proxy": p}


# ── 站方工具 jar（自备） ──────────────────────────────
def tool_dirs() -> list:
    return [Path(p) for p in CFG.get("tool_dirs", [])]


def tool_jar(key: str) -> str:
    return CFG.get("tool_jars", {}).get(key, "")


if __name__ == "__main__":
    print("配置来源:", os.environ.get("MCAUTO_CONFIG") or (HERE / "config.json"))
    print("  cache  :", cache_dir())
    print("  worlds :", worlds_dir())
    print("  mc_dir :", mc_dir())
    for k in ("8", "17", "21", "25"):
        print(f"  java{k:<3}:", javaw(k) or "(缺失)")
    for k in ("8", "7", "4", "2"):
        print(f"  gradle{k}:", gradle_bat(k) or "(缺失)")
