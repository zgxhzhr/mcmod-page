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
AGENT8 = HERE / "mcauto-agent8.jar"   # Java 8 字节码，1.12.2 / 1.7.10 用
WORLDS = Path(r"E:\Mod\百科-语料\mcauto-worlds")
MC_DIR = Path(r"E:\PCL\.minecraft")

# 各 mode 对应工具 modId 与输出目录名
TOOL_INFO = {
    "lms":   {"modid": "let_me_see_see", "out": "let_me_see_see"},   # -D 覆盖后仍以此为准
    "lmsent": {"modid": "let_me_see_see", "out": "let_me_see_see"},   # fork 版：实体导出
    "iconrd": {"modid": "iconr",         "out": "IconRendererOutput"},   # Forge：直接调 FileHelper
    "iconr": {"modid": "iconr",          "out": "IconRendererOutput"},   # Forge 版
    "iconr2": {"modid": "iconr",         "out": "IconRenderer/Json"},  # fork 版：自触发
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


def _start_local_server(game: Path, version: str, java: str, tool_modid: str = "",
                        port: int = 25566,
                        timeout_s: int = 240) -> subprocess.Popen | None:
    """起一个本地专用服务端，供 1.20 以下的客户端连入。

    为什么需要：--quickPlaySingleplayer 是 1.20 才有的参数。
    1.19.2 及更早的客户端只能停在标题界面，不会自己进世界，
    而导出要求 Minecraft.level 非空。

    做法：用 make_world 缓存里的 server.jar 在 game 目录外起一个服务端，
    客户端用 --server 127.0.0.1 --port <port> 连进去 —— 连服务器也算进世界。
    """
    mcver = mc_version_of(version)
    jar = Path(r"E:\Mod\百科-语料\mcauto-cache") / f"server-{mcver}.jar"
    if not jar.exists():
        print(f"      没有 {jar.name}，先用 make_world.py --version {mcver} 生成本地服务端")
        return None

    sdir = game.parent / ("_server_%d" % port)
    if sdir.exists():
        # 上一轮的服务端可能还在占文件；忽略失败，换个新目录名
        shutil.rmtree(sdir, ignore_errors=True)
        if sdir.exists():
            sdir = game.parent / ("_server_%d_%d" % (port, int(time.time())))
    sdir.mkdir(parents=True)
    (sdir / "eula.txt").write_text("eula=true\n", encoding="utf-8")
    (sdir / "server.properties").write_text("\n".join([
        "level-type=minecraft:flat",
        "level-name=world",
        "online-mode=false",
        "server-port=%d" % port,
        "spawn-protection=0",
        "allow-nether=false",
        "max-tick-time=-1",
        "sync-chunk-writes=false",
        "view-distance=4",
        "difficulty=peaceful",
        "gamemode=creative",
    ]) + "\n", encoding="utf-8")
    # 服务端装同一批 mod，但**跳过工具模组**：LMS / IconRenderer / IRR 都是纯客户端的，
    # 塞进专用服务端会因找不到客户端类直接崩（1.12.2 / 1.7.10 上尤其明显）。
    src_mods = game / "mods"
    if src_mods.is_dir():
        dst_mods = sdir / "mods"
        dst_mods.mkdir(parents=True, exist_ok=True)
        import zipfile as _zf
        for jar in src_mods.glob("*.jar"):
            skip = False
            try:
                with _zf.ZipFile(jar) as z:
                    names = z.namelist()
                    for n in names:
                        if n.endswith(("mcmod.info", "mods.toml", "fabric.mod.json")):
                            txt = z.read(n).decode("utf-8", errors="ignore").lower()
                            if tool_modid and tool_modid.lower() in txt:
                                skip = True
                            break
            except Exception:
                pass
            if not skip:
                shutil.copy2(jar, dst_mods / jar.name)

    print(f"      启动本地服务端（端口 {port}）…")
    proc = subprocess.Popen([java, "-Xmx1G", "-jar", str(jar), "--nogui"],
                            cwd=str(sdir), stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace")
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        line = proc.stdout.readline()
        if not line:
            break
        if "Done (" in line or "For help, type" in line:
            print(f"      服务端就绪（{int(time.time()-t0)}s）")
            return proc
    print("      服务端没起来")
    proc.kill()
    return None


def _supports_quickplay(version: str) -> bool:
    """--quickPlaySingleplayer 是 1.20 引入的。"""
    import re
    m = re.match(r"1\.(\d+)", version)
    if not m:
        return False
    return int(m.group(1)) >= 20


def mc_version_of(version_name: str) -> str:
    """从 PCL 的版本名里推出 MC 版本。

    PCL 的版本名五花八门：
      1.20.1-Forge_47.4.26          → 1.20.1
      1.21.1-NeoForge_21.1.255      → 1.21.1
      fabric-loader-0.14.12-1.19.2  → 1.19.2   ← 不能简单 split("-")[0]
      1.20.1-Fabric 0.19.3          → 1.20.1
    MC 版本都以 1. 开头，所以取第一个形如 1.x[.y] 的片段。
    """
    import re as _re
    m = _re.search(r"\b1\.\d+(?:\.\d+)?\b", version_name)
    if m:
        return m.group(0)
    return version_name.split("-")[0]


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
    mcver = mc_version_of(version)
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


def restore_cursor() -> None:
    """把系统光标彻底恢复：计数器归零、形状重置、解除裁剪。

    GLFW 被 kill 时不会帮我们恢复光标，所以退出路径必须显式调用，
    否则用户桌面上的鼠标会「消失」（已踩过两次）。
    """
    try:
        import ctypes
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.ShowCursor.restype = ctypes.c_int
        guard = 0
        while user32.ShowCursor(True) < 0 and guard < 100:
            guard += 1
        user32.SetCursor(user32.LoadCursorW(None, ctypes.c_void_p(32512)))  # IDC_ARROW
        user32.ClipCursor(None)
    except Exception:
        pass


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
                # GLFW 每次隐藏都调一次 ShowCursor(FALSE)，内部计数器会被压成负数；
                # 固定调几次没用，必须循环到返回值 >= 0
                user32.ShowCursor.restype = ctypes.c_int
                guard = 0
                while user32.ShowCursor(True) < 0 and guard < 50:
                    guard += 1
                # 把焦点从游戏窗口抢走：MC 只有失焦后才会真正松开鼠标
                if n % 3 == 0:
                    try:
                        user32.SetForegroundWindow(user32.GetShellWindow())
                    except Exception:
                        pass
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

FAIL_MARKERS = (
    "Mod Loading has failed",
    "Mod loading error has occurred",
    "A fatal error has been detected",
    "Exception in thread \"main\"",
    "Failed to start the game",
    "Minecraft game provider couldn't locate the game",
)


def _scan_failure(log_path: Path) -> str:
    """扫启动日志里的致命错误标记，命中就立刻返回原因（免得干等超时）"""
    try:
        txt = log_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    tail = txt[-20000:]
    for m in FAIL_MARKERS:
        i = tail.find(m)
        if i >= 0:
            snippet = tail[i:i + 400].replace("\n", " ")
            return snippet
    return ""


def agent_jar_for(version: str) -> Path:
    """1.12.2 及更早的 JVM 只认 class 52（Java 8），必须用 agent8。"""
    import re
    m = re.search(r"(\d+)\.(\d+)", version)
    if m:
        major, minor = int(m.group(1)), int(m.group(2))
        # 1.16 及更早都跑在 JDK 8 上（find_java 也是这么选的），
        # agent 必须同为 class 52，否则 UnsupportedClassVersionError。
        if major == 1 and minor <= 16:
            return AGENT8
    return AGENT


def wait_done(game: Path, proc: subprocess.Popen, timeout_s: int,
              out_dir: Path | None = None, log_path: Path | None = None) -> bool:
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
    last_report = 0.0
    while time.time() < deadline:
        # 致命错误立刻失败，不要干等
        if log_path is not None and log_path.exists():
            why = _scan_failure(log_path)
            if why:
                print(f"\n✗ 启动失败（{int(time.time()-t0)}s）：{why[:300]}")
                return False
        if time.time() - last_report > 10:
            last_report = time.time()
            size = log_path.stat().st_size if (log_path and log_path.exists()) else 0
            print(f"      … {int(time.time()-t0)}s  日志 {size//1024} KB", flush=True)
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
    ap.add_argument("--delay", type=int, default=60, help="自触发模式下进世界后等多少 tick")
    ap.add_argument("--self-trigger", action="store_true",
                    help="模组自己触发导出（读 -Dmcauto.modid），不注入 agent。"
                         "Fabric 版 IconRenderer fork 用这个：运行时是 intermediary 名字，"
                         "agent 按 mojmap 反射会失效")
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
    # 1.12.2 及更早：没有 quickPlay，也不方便起 Forge 服务端，
    # 直接让 agent 调 launchIntegratedServer 载入本地存档。
    import re as _re
    _mm = _re.search(r"(\d+)\.(\d+)", a.version)
    legacy_world = bool(_mm) and int(_mm.group(1)) == 1 and int(_mm.group(2)) <= 12
    if legacy_world:
        print("      老版本：由 agent 自己载入本地存档（不走服务端）")

    print(f"[2/4] 组装命令行（agent mode={a.mode}，输出目录 {export_dir}）")
    sys_path = str(HERE)
    import sys
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    import launcher  # noqa: E402

    if a.self_trigger:
        # 模组自己在客户端 tick 里等世界加载完再导出；只传 -D
        agent_arg = f"-Dmcauto.modid={target}"
        extra = [f"-Dmcauto.delay={getattr(a, 'delay', 60)}"]
    else:
        chosen_agent = agent_jar_for(a.version)
        if not chosen_agent.exists():
            raise SystemExit(f"缺 agent：{chosen_agent}，先跑 build_agent.py")
        _wa = ",world=mcauto" if legacy_world else ""
        agent_arg = (f"-javaagent:{chosen_agent}=mode={a.mode},timeout={a.timeout}{_wa},"
                     f"gameDir={game}")
        extra = []
    if legacy_world and not a.self_trigger:
        extra = list(extra) + ["-Dmcauto.world=mcauto"]

    argv = launcher.build(
        Path(a.mc_dir), a.version, game, a.username,
        launcher.find_java(a.version),
        ([f"-Dmcauto.modid={target}"] if target else []), w, h,
        None, None)  # 不覆盖输出目录：工具默认就写在 gameDir 下
    # 把 agent 插到 mainClass 之前（-javaagent 必须在 -jar/-cp 语境里靠前）
    # 主类必须从 version json 里读，不能靠名字猜：
    # Forge 1.12.2 的主类是 net.minecraft.launchwrapper.Launch，既没有 Launcher 也没有 Main。
    _vj, _ = launcher.resolve_version_json(Path(a.mc_dir), a.version)
    main_class = _vj.get("mainClass", "")
    try:
        mi = argv.index(main_class)
    except ValueError:
        mi = argv.index(next(x for x in argv if "Launcher" in x or "Main" in x))
    argv = argv[:mi] + [agent_arg] + extra + argv[mi:]
    # 1.20+ 才有 quickPlay：直接进世界，跳过主菜单
    server_proc = None
    if _supports_quickplay(a.version):
        argv += ["--quickPlaySingleplayer", "mcauto"]
    else:
        # 1.20 以下没有 quickPlay：起本地服务端，客户端连进去
        _tool_modid = TOOL_INFO.get(a.mode, {}).get("modid", "")
        server_proc = None if legacy_world else _start_local_server(game, a.version,
                                          launcher.find_java(a.version).replace("javaw", "java"),
                                          _tool_modid)
        if server_proc is None:
            print("  ⚠ 起不了本地服务端，客户端会停在标题界面")
        else:
            argv += ["--server", "127.0.0.1", "--port", "25566"]

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
    ok = wait_done(game, proc, a.timeout, prod_dir,
                  (work / 'agent.log') if a.console else None)
    stop_ev.set()
    # 导出完成后再解析实际产物目录：IconRenderer 是 Json/<modid>/<modid>-items.json，
    # 导出前这个子目录还不存在
    if target and (prod_dir / target).is_dir():
        prod_dir = prod_dir / target

    restore_cursor()
    if server_proc is not None and server_proc.poll() is None:
        try:
            server_proc.stdin.write("stop\n")
            server_proc.stdin.flush()
        except Exception:
            pass
        try:
            server_proc.wait(timeout=20)
        except Exception:
            server_proc.kill()
    if not a.keep_open and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("  已关闭客户端")
    restore_cursor()

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
    import atexit
    # 任何退出路径都把光标还回去：JVM fatal 崩溃时 GLFW 不会恢复，
    # 用户的鼠标会「消失」（已经踩到三次）
    atexit.register(restore_cursor)
    try:
        raise SystemExit(main())
    finally:
        restore_cursor()
