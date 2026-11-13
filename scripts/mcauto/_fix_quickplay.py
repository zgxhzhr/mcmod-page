#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""修两个问题：
1. launcher：quickPlay 占位符未展开 + 参数重复（崩溃原因）
2. run：客户端窗口弹到前台（用户要求不打扰）

崩溃原话：
  joptsimple.MultipleArgumentsForOptionException:
  Found multiple arguments for option quickPlaySingleplayer, but you asked for only one
NeoForge 的 version json 自带 --quickPlaySingleplayer ${quickPlaySingleplayer}，
占位符没展开就成了字面量，我们再追加一条 → 同一个 option 传了两次。
"""
from pathlib import Path

L = Path(r"E:\Mod\模板与工具\发布\mcmod-page\scripts\mcauto\launcher.py")
R = Path(r"E:\Mod\模板与工具\发布\mcmod-page\scripts\mcauto\run.py")

# ── launcher.py ──
t = L.read_text(encoding="utf-8")
if "quickPlayPath" in t:
    print("launcher 已修，跳过")
else:
    old = '''        "game_assets": str(assets_dir / "virtual" / "legacy"),
    }'''
    new = '''        "game_assets": str(assets_dir / "virtual" / "legacy"),
        # NeoForge 的 version json 自带 quickPlay 系列占位符，不展开会变成字面量
        "quickPlayPath": "",
        "quickPlaySingleplayer": "",
        "quickPlayMultiplayer": "",
        "quickPlayRealms": "",
    }'''
    assert old in t, "找不到 game_assets 锚点"
    t = t.replace(old, new, 1)

    old2 = '''    # 确保窗口尺寸（json 里通常已带，没有就补）
    if "--width" not in game:'''
    new2 = '''    # 占位符展开成空值的 quickPlay 参数要整对删掉：
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
    if "--width" not in game:'''
    assert old2 in t, "找不到窗口尺寸锚点"
    t = t.replace(old2, new2, 1)
    L.write_text(t, encoding="utf-8")
    print("✓ launcher.py 已修（quickPlay 展开 + 空值参数对清除）")

# ── run.py：窗口不打扰 ──
r = R.read_text(encoding="utf-8")
if "_minimize_window" in r:
    print("run 已修，跳过")
else:
    helper = '''

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
'''
    anchor = "\ndef wait_done("
    assert anchor in r
    r = r.replace(anchor, helper + anchor, 1)

    old3 = '''    print(f"      pid={proc.pid}")'''
    new3 = '''    print(f"      pid={proc.pid}")
    if a.hidden:
        hide_window(proc.pid)'''
    assert old3 in r
    r = r.replace(old3, new3, 1)

    old4 = '''    ap.add_argument("--keep-open", action="store_true", help="导出后不杀进程，方便看界面")'''
    new4 = '''    ap.add_argument("--keep-open", action="store_true", help="导出后不杀进程，方便看界面")
    ap.add_argument("--hidden", action="store_true", help="把客户端窗口移到屏幕外，不抢前台")
    ap.add_argument("--size", default="854x480", help="窗口尺寸，默认 854x480（小窗口省显卡）")'''
    assert old4 in r
    r = r.replace(old4, new4, 1)

    old5 = '''        launcher.find_java(a.version), [], 1280, 720,
        None, str(export_dir))'''
    new5 = '''        launcher.find_java(a.version), [], w, h,
        None, str(export_dir))'''
    assert old5 in r
    r = r.replace(old5, new5, 1)

    old6 = '''    export_dir = work / "out"'''
    new6 = '''    try:
        w, h = (int(x) for x in a.size.lower().split("x"))
    except Exception:
        w, h = 854, 480
    export_dir = work / "out"'''
    assert old6 in r
    r = r.replace(old6, new6, 1)
    R.write_text(r, encoding="utf-8")
    print("✓ run.py 已修（--hidden 移出屏幕 + --size 小窗口）")
