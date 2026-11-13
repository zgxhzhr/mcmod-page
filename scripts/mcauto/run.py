#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""一条命令跑完：准备隔离环境 → 启动客户端 → agent 自动导出 → 收产物。

设计原则（用户要求：最小化 + 完全自动化）
  最小化：
    - 不改 jar、不编 mod（agent 只用 JDK 反射，5 KB）
    - 不动用户 .minecraft 里的 mods / 存档：全部在独立 gameDir 里
    - 不依赖 PCL 点击：自己读 version json 生成命令行
  完全自动化：
    - 服务端预生成超平坦存档 → quickPlay 直接进世界（1.20+）
    - agent 检测到 level+player 非空后，主线程调用导出方法
    - 轮询 _mcauto_done → 收产物 → 杀进程

用法：
    python run.py --version 1.21.1-NeoForge_21.1.255 \
                  --mods "<LMS jar>" "<目标模组 jar>" \
                  --mode lms \
                  --work "E:\Mod\百科-语料\mcauto-run"
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).parent
AGENT = HERE / "mcauto-agent.jar"
WORLDS = Path(r"E:\Mod\百科-语料\mcauto-worlds")
MC_DIR = Path(r"E:\PCL\.minecraft")

# 各 mode 对应工具 modId 与输出目录名
TOOL_INFO = {
    "lms":   {"modid": "let_me_see_see", "out": "let_me_see_see"},   # -D 覆盖后仍以此为准
    "lmsent": {"modid": "let_me_see_see", "out": "let_me_see_see"},   # fork 版：实体导出
    "iconr": {"modid": "iconr",          "out": "IconRendererOutput"},
    "irr":   {"modid": "item_render_rebirth", "out": "export"},
}


def detect_modid(jars: list[Path], tool_modid: str) -> str:
    """从 mods.toml / fabric.mod.json 里读出目标模组的 modId（跳过工具自身）。"""
    import re
    import zipfile
    for j in jars:
        try:
            with zipfile.ZipFile(j) as z:
                names = z.namelist()
                cand = [n for n in names if n.endswith(("mods.toml", "neoforge.mods.toml"))]
                if cand:
                    txt = z.read(cand[0]).decode("utf-8", errors="ignore")
                    ids = re.findall(r'modId\s*=\s*"([^"]+)"', txt)
                    for mid in ids:
                        if mid not in (tool_modid, "minecraft", "neoforge", "forge"):
                            return mid
                fab = [n for n in names if n.endswith("fabric.mod.json")]
                if fab:
                    import json as _json
                    d = _json.loads(z.read(fab[0]).decode("utf-8", errors="ignore"))
                    mid = d.get("id", "")
                    if mid and mid != tool_modid:
                        return mid
        except Exception:
            continue
    return ""


def _supports_quickplay(version: str) -> bool:
    """--quickPlaySingleplayer 是 1.20 引入的。"""
    import re
    m = re.match(r"1\.(\d+)", version)
    if not m:
        return False
    return int(m.group(1)) >= 20


def prepare(work: Path, version: str, mods: list[Path], mode: str) -> Path:
    """建隔离 gameDir。"""
    game = work / "game"
    if game.exists():
        shutil.rmtree(game)
    (game / "mods").mkdir(parents=True)
    (game / "saves").mkdir()
    (game / "config").mkdir()
    (game / "logs").mkdir()

    for m in mods:
        dst = game / "mods" / m.name
        shutil.copy2(m, dst)
        print(f"  装 mod: {m.name}")

    # options.txt：关掉会影响自动化的选项
    (game / "options.txt").write_text("\n".join([
        "pauseOnLostFocus:false",
        "autoJump:false",
        "lang:zh_cn",
        "fov:0.0",
        "guiScale:3",
        "renderDistance:4",
        "maxFps:60",
        "fullscreen:false",
    ]) + "\n", encoding="utf-8")

    # 存档：拷进 saves/
    mcver = version.split("-")[0]
    world = WORLDS / f"{mcver}-flat"
    if not (world / "level.dat").exists():
        raise SystemExit(
            f"缺少存档 {world}\n先跑：python make_world.py --version {mcver}")
    shutil.copytree(world, game / "saves" / "mcauto")
    print(f"  世界: {world.name} → saves/mcauto")

    export_dir = work / "out"
    if export_dir.exists():
        shutil.rmtree(export_dir)
    export_dir.mkdir(parents=True)
    return game



def _window_handles_for_pid(pid: int):
    """枚举属于该 pid 的顶层窗口（用 Win32，纯 ctypes，不装额外库）。"""
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    handles = []
    CB = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        p = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid and user32.IsWindowVisible(hwnd):
            handles.append(hwnd)
        return True

    user32.EnumWindows(CB(cb), 0)
    return handles


def hide_window(pid: int) -> bool:
    """把客户端窗口移到屏幕外并禁用激活，避免抢前台。

    不用 SW_MINIMIZE：最小化的 GLFW 窗口往往停止渲染，FBO 导出会失败。
    移到屏幕外既能继续渲染，又不打扰用户。
    """
    import ctypes
    import time as _t
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    SWP_NOACTIVATE, SWP_NOSIZE = 0x0010, 0x0001
    deadline = _t.time() + 60
    while _t.time() < deadline:
        hs = _window_handles_for_pid(pid)
        if hs:
            ok = False
            for h in hs:
                # 移到 -3000 以外的位置，保留尺寸
                ok = user32.SetWindowPos(h, 0, -3000, 0, 0, 0,
                                         SWP_NOSIZE | SWP_NOACTIVATE) or ok
            if ok:
                print(f"  窗口已移到屏幕外（{len(hs)} 个）")
                return True
        _t.sleep(1)
    print("  ⚠ 没找到客户端窗口，可能仍在正常显示")
    return False


def start_cursor_watchdog(pid: int, stop_event):
    """持续解除 MC 的鼠标裁剪，并把窗口保持在屏幕外。"""
    import ctypes
    import threading
    import time as _t

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    SWP_NOACTIVATE, SWP_NOSIZE = 0x0010, 0x0001

    def loop():
        n = 0
        while not stop_event.is_set():
            try:
                # 关键：解除系统光标裁剪
                user32.ClipCursor(None)
                # 每 2 秒把窗口挪回屏幕外（MC 可能把窗口拉回）
                if n % 6 == 0:
                    for h in _window_handles_for_pid(pid):
                        user32.SetWindowPos(h, 0, -3000, -3000, 0, 0,
                                            SWP_NOSIZE | SWP_NOACTIVATE)
            except Exception:
                pass
            n += 1
            _t.sleep(0.3)

    th = threading.Thread(target=loop, name="cursor-watchdog", daemon=True)
    th.start()
    return th

def wait_done(game: Path, proc: subprocess.Popen, timeout_s: int,
              out_dir: Path | None = None) -> bool:
    """等 agent 的哨兵文件；同时兜底：产物连续 20 秒不再变化也算完成。

    LMS 的 runExportMcMod 在返回前就把 json 写完了，但 1.21.1 里 1290 个物品的
    PNG 图标编码很慢，容易在哨兵写出前就撞上超时 —— 所以用产物稳定性做第二判据。
    """
    done = game / "_mcauto_done"
    err = game / "_mcauto_error.txt"
    deadline = time.time() + timeout_s
    t0 = time.time()
    last_sig = None
    stable_since = None
    while time.time() < deadline:
        if out_dir is not None:
            # 只认 .json 产物：导出目录里还有 _icons 之类的辅助目录，
            # 把它们算进稳定性判定会导致「刚启动就判完成」并提前杀进程
            sig = []
            for f in sorted(out_dir.glob("*.json")):
                st = f.stat()
                sig.append((f.name, st.st_size))
            sig = tuple(sig)
            if sig and sig == last_sig:
                if stable_since is None:
                    stable_since = time.time()
                elif time.time() - stable_since > 20:
                    print(f"\n✓ 产物已稳定 20 秒（{int(time.time()-t0)}s），视为完成")
                    return True
            else:
                stable_since = None
                last_sig = sig
        if done.exists():
            print(f"\n✓ 导出完成（{int(time.time()-t0)}s）")
            return True
        if err.exists():
            print(f"\n✗ agent 报错：{err.read_text(encoding='utf-8', errors='replace')}")
            return False
        if proc.poll() is not None:
            print(f"\n✗ 客户端已退出（code={proc.returncode}）")
            log = game / "logs" / "latest.log"
            if log.exists():
                tail = log.read_text(encoding="utf-8", errors="replace")[-1500:]
                print("--- latest.log 末尾 ---")
                print(tail)
            return False
        time.sleep(1)
    print(f"\n✗ 超时 {timeout_s}s")
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="PCL 里的版本名，如 1.21.1-NeoForge_21.1.255")
    ap.add_argument("--mods", nargs="+", required=True, help="要装进 mods/ 的 jar")
    ap.add_argument("--mode", default="lms", choices=list(TOOL_INFO))
    ap.add_argument("--work", default=r"E:\Mod\百科-语料\mcauto-run")
    ap.add_argument("--mc-dir", default=str(MC_DIR))
    ap.add_argument("--username", default="mcauto")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--keep-open", action="store_true", help="导出后不杀进程，方便看界面")
    ap.add_argument("--hidden", action="store_true", help="把客户端窗口移到屏幕外，不抢前台")
    ap.add_argument("--console", action="store_true",
                    help="用 java.exe 启动并把 agent 的 stdout 落盘到 work/agent.log（调试用）")
    ap.add_argument("--overrides", default=r"E:\Mod\百科-语料\mcauto-overrides",
                    help="手工图标覆盖目录：<overrides>/<modid>/<path>.png")
    ap.add_argument("--target-modid", default="",
                    help="只导出这个命名空间（modid）。留空则自动从非工具 jar 里读")
    ap.add_argument("--size", default="854x480", help="窗口尺寸，默认 854x480（小窗口省显卡）")
    a = ap.parse_args()

    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    if not AGENT.exists():
        raise SystemExit(f"缺 agent，先跑 build_agent.py（{AGENT}）")

    mods = [Path(m) for m in a.mods]
    for m in mods:
        if not m.exists():
            raise SystemExit(f"mod 不存在：{m}")

    try:
        w, h = (int(x) for x in a.size.lower().split("x"))
    except Exception:
        w, h = 854, 480

    tool_modid = TOOL_INFO[a.mode]["modid"]
    target = a.target_modid or detect_modid(mods, tool_modid)
    print(f"      目标命名空间: {target or '（全部，较慢）'}")

    print(f"[1/4] 准备隔离环境  {work}")
    game = prepare(work, a.version, mods, a.mode)

    # 手工图标覆盖要拷进来：prepare() 会整个删掉 game 目录，
    # 所以覆盖图不能直接放在里面，必须在外部持久目录维护
    ov_src = Path(a.overrides) / (target or a.mode)
    if ov_src.is_dir():
        ov_dst = game / TOOL_INFO[a.mode]["out"] / "_icons"
        if target:
            ov_dst = ov_dst / target
        ov_dst.mkdir(parents=True, exist_ok=True)
        n = 0
        for f in ov_src.glob("*.png"):
            shutil.copy2(f, ov_dst / f.name)
            n += 1
        print(f"      覆盖图标 {n} 个 → {ov_dst.name}")
    else:
        print(f"      无覆盖目录（{ov_src}）")

    export_dir = work / "out"
    print(f"[2/4] 组装命令行（agent mode={a.mode}，输出目录 {export_dir}）")
    sys_path = str(HERE)
    import sys
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    import launcher  # noqa: E402

    agent_arg = (f"-javaagent:{AGENT}=mode={a.mode},timeout={a.timeout},"
                 f"gameDir={game}")
    argv = launcher.build(
        Path(a.mc_dir), a.version, game, a.username,
        launcher.find_java(a.version),
        ([f"-Dmcauto.modid={target}"] if target else []), w, h,
        None, None)  # 不覆盖输出目录：工具默认就写在 gameDir 下
    # 把 agent 插到 mainClass 之前（-javaagent 必须在 -jar/-cp 语境里靠前）
    mi = argv.index(next(x for x in argv if "Launcher" in x or "Main" in x))
    argv = argv[:mi] + [agent_arg] + argv[mi:]
    # 1.20+ 才有 quickPlay：直接进世界，跳过主菜单
    if _supports_quickplay(a.version):
        argv += ["--quickPlaySingleplayer", "mcauto"]
    else:
        print("  ⚠ 该版本不支持 --quickPlaySingleplayer，需要别的进世界手段")

    print(f"[3/4] 启动客户端  pid 待定")
    agent_log = None
    if a.console:
        # 用 java.exe（有控制台）并把 stdout 写文件，否则 agent 的 System.out 看不见
        argv[0] = str(Path(argv[0]).with_name("java.exe"))
        agent_log = open(work / "agent.log", "w", encoding="utf-8", errors="replace")
        print(f"      agent 输出 → {agent_log.name}")
    proc = subprocess.Popen(argv, cwd=str(game),
                            stdout=agent_log, stderr=subprocess.STDOUT if agent_log else None)
    print(f"      pid={proc.pid}")
    if a.hidden:
        hide_window(proc.pid)
    # 无论是否 hidden，都要放光标：MC 进世界会把鼠标裁剪到窗口内
    import threading
    stop_ev = threading.Event()
    start_cursor_watchdog(proc.pid, stop_ev)
    print("      光标看门狗已启动（每 300ms 解除一次鼠标裁剪）")

    print(f"[4/4] 等待导出（最多 {a.timeout}s）")
    # 产物目录：工具默认写在 gameDir 下，按 mode 取
    prod_dir = game / TOOL_INFO[a.mode]["out"]
    ok = wait_done(game, proc, a.timeout, prod_dir)
    stop_ev.set()

    if not a.keep_open and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("  已关闭客户端")

    files = sorted(prod_dir.glob("*")) if prod_dir.exists() else []
    if files:
        total = sum(f.stat().st_size for f in files)
        print(f"\n产物 {len(files)} 个，共 {total/1024:.1f} KB：")
        for f in files[:20]:
            print(f"  {f.name}  {f.stat().st_size/1024:.1f} KB  → {f}")
        if len(files) > 20:
            print(f"  … 共 {len(files)} 个")
    else:
        print("\n没有产物")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
