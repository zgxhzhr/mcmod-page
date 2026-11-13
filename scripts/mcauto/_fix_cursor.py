#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""修「MC 进世界后锁鼠标」：跑一个看门狗线程，持续把光标从 MC 的裁剪区里放出来。

现象：quickPlay 进世界后 MC 调 MouseHandler.grabMouse()，把系统光标裁剪到窗口内，
桌面上鼠标动不了，用户只能强杀进程。

解法：
  1. 每 300ms 调一次 user32.ClipCursor(NULL) —— 解除系统级裁剪
  2. 每 2s 把窗口重新挪回屏幕外（MC 有时会把窗口拉回前台）
  3. 进程结束后自动停止

这不影响 MC 内部渲染与导出，只是不让它独占鼠标。
"""
from pathlib import Path

R = Path(r"E:\Mod\模板与工具\发布\mcmod-page\scripts\mcauto\run.py")

WATCHDOG = '''

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
'''

t = R.read_text(encoding="utf-8")

if "start_cursor_watchdog" in t:
    print("已存在，跳过")
    raise SystemExit(0)

anchor = "\ndef wait_done("
assert anchor in t
t = t.replace(anchor, WATCHDOG + anchor, 1)

old = """    print(f"      pid={proc.pid}")
    if a.hidden:
        hide_window(proc.pid)"""
new = """    print(f"      pid={proc.pid}")
    if a.hidden:
        hide_window(proc.pid)
    # 无论是否 hidden，都要放光标：MC 进世界会把鼠标裁剪到窗口内
    import threading
    stop_ev = threading.Event()
    start_cursor_watchdog(proc.pid, stop_ev)
    print("      光标看门狗已启动（每 300ms 解除一次鼠标裁剪）")"""
assert old in t
t = t.replace(old, new, 1)

old2 = """    ok = wait_done(game, proc, a.timeout)"""
new2 = """    ok = wait_done(game, proc, a.timeout)
    stop_ev.set()"""
assert old2 in t
t = t.replace(old2, new2, 1)

R.write_text(t, encoding="utf-8")
print("✓ run.py 已加光标看门狗")
