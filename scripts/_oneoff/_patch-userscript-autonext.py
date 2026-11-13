#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给模组介绍批量面板加「连续执行 + 自动跳下一条」。

背景：面板能填能提交，但每次都要手动打开下一个模组的编辑页。
跳转目标不能靠猜 —— /class/edit/<classId>-<verifyId>/ 里的第二段是随机 id，
所以把审核列表里的 againHref 写进队列条目的 targetUrl，脚本照着跳。

补丁：
  1. 按钮区加「连续执行」「停止」
  2. 状态里存 autoRun / paused（和 items 同一个 sessionStorage 键）
  3. submitAndNext()：填入 → 提交 → 确认 → 等下一条跳转
  4. advance()：按 targetUrl 跳到下一条，没有就跑完收工
  5. 页面加载时若 autoRun 且未 paused，2 秒后自动开始
"""
from pathlib import Path

P = Path(r"E:\Mod\模板与工具\发布\mcmod-page\scripts\mcmod-batch.user.js")
t = P.read_text(encoding="utf-8")

# ── 1) 按钮 ──
old_btn = """      '<button id="mb-ce-run">填入并提交</button>' +
      '<button id="mb-ce-diag">诊断</button>' +"""
new_btn = """      '<button id="mb-ce-run">填入并提交</button>' +
      '<button id="mb-ce-auto">连续执行</button>' +
      '<button id="mb-ce-stop">停止</button>' +
      '<button id="mb-ce-diag">诊断</button>' +"""
assert old_btn in t, "按钮段没找到"
t = t.replace(old_btn, new_btn, 1)

# ── 2) 替换 fill→run 段，加入状态与跳转 ──
old_run = """    document.getElementById('mb-ce-fill').addEventListener('click', () => { doFill(); });

    document.getElementById('mb-ce-run').addEventListener('click', async () => {
      if (!doFill()) return;
      info('正在提交…');
      const btn = findSubmitButton();
      if (!btn) return info('找不到提交按钮，请手动提交');
      btn.click();
      await sleep(2600);
      const ok = findConfirmAny();
      if (!ok) return info('没等到确认按钮，请手动点确认');
      ok.click();
      info('已点确认「' + (ok.innerText || '').trim().slice(0, 8) + '」');
    });
"""

new_run = r"""    // ---------- 队列状态（autoRun / paused 与 items 同一个键） ----------
    function curIndex() {
      return planList.findIndex((x) => String(x.classId || x.id || '') === String(classId));
    }
    function loadFlags() {
      try {
        const d = JSON.parse(sessionStorage.getItem(KEY) || '{}');
        return { autoRun: !!d.autoRun, paused: !!d.paused };
      } catch (e) { return { autoRun: false, paused: false }; }
    }
    function saveFlags(patch) {
      const d = Object.assign({ items: planList }, loadFlags(), patch);
      sessionStorage.setItem(KEY, JSON.stringify(d));
    }

    function advance() {
      const i = curIndex();
      const next = (i >= 0 && i + 1 < planList.length) ? planList[i + 1] : null;
      if (!next) {
        saveFlags({ autoRun: false });
        info('队列完成，共 ' + planList.length + ' 条');
        return;
      }
      const url = next.targetUrl || ('/class/edit/' + next.classId + '/');
      info('第 ' + (i + 2) + '/' + planList.length + ' 条：' + (next.name || next.classId) + '，跳转中…');
      setTimeout(() => { location.href = url; }, 700);
    }

    async function submitAndNext() {
      if (!doFill()) { saveFlags({ paused: true }); return; }
      await sleep(300);
      info('正在提交…');
      const btn = findSubmitButton();
      if (!btn) { saveFlags({ paused: true }); return info('找不到提交按钮，已暂停'); }
      btn.click();
      await sleep(2600);
      const ok = findConfirmAny();
      if (!ok) { saveFlags({ paused: true }); return info('没等到确认按钮，已暂停（手动点确认后可继续）'); }
      ok.click();
      info('已确认「' + (ok.innerText || '').trim().slice(0, 8) + '」，等页面跳转…');
      await sleep(2800);
      advance();
    }

    document.getElementById('mb-ce-fill').addEventListener('click', () => { doFill(); });
    document.getElementById('mb-ce-run').addEventListener('click', () => { submitAndNext(); });

    document.getElementById('mb-ce-auto').addEventListener('click', () => {
      if (!row) return info('还没载入正文');
      saveFlags({ autoRun: true, paused: false });
      info('连续执行已开启：' + (curIndex() + 1) + '/' + planList.length);
      submitAndNext();
    });

    document.getElementById('mb-ce-stop').addEventListener('click', () => {
      saveFlags({ autoRun: false, paused: true });
      info('已停止（队列保留，可再点「连续执行」继续）');
    });
"""
assert old_run in t, "fill→run 段没找到"
t = t.replace(old_run, new_run, 1)

# ── 3) 加载时自动开始 ──
old_tail = """    refresh();
  }

"""
new_tail = """    refresh();

    // 连续模式下，进页面 2 秒后自动开填（留点时间让编辑器初始化）
    const flags = loadFlags();
    if (flags.autoRun && !flags.paused && row) {
      info('连续模式：第 ' + (curIndex() + 1) + '/' + planList.length + ' 条，2 秒后自动执行…');
      setTimeout(() => { submitAndNext(); }, 2000);
    }
  }

"""
assert old_tail in t, "函数结尾没找到"
t = t.replace(old_tail, new_tail, 1)

# ── 4) 版本号 ──
t = t.replace("MB_VERSION = '2.40'", "MB_VERSION = '2.41'", 1)
t = t.replace("// @version      2.40", "// @version      2.41", 1)

P.write_text(t, encoding="utf-8")
print(f"✓ 补丁完成 {len(t)/1024:.1f} KB（字符计）")
