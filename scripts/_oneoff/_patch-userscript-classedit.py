#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给 mcmod-batch.user.js 补上「模组介绍编辑页」支持。

问题：脚本只有 /item/edit/、/item/add/、/item/list/、/verify 四个分支，
模组介绍编辑页 /class/edit/<classId>-<subId>/ 没有分支可走，
落到末尾的新增资料页逻辑，于是面板不渲染 —— 表现就是「跳转过去面板消失」。

补丁内容：
  1. removeStalePanels 的面板 id 白名单加上 mb-class-edit-panel
  2. 路由加 /class/edit/<classId> 分支
  3. 新增 initClassEditPanel(classId)：
     - 从 sessionStorage 或导入的 JSON 里按 classId 取正文
     - 「填入本页」复用 setEditorHtml + fillEditMeta（与 item 编辑同一套）
     - 「填入并提交」再走 findSubmitButton + findConfirmAny
     - 「诊断」列出 CodeMirror / UEditor / 附言字段 / 提交按钮的命中情况
     - 「复制正文」兜底，避免编辑器变体导致填不进去
  4. 版本号 2.39 → 2.40
"""
from pathlib import Path

P = Path(r"E:\Mod\模板与工具\发布\mcmod-page\scripts\mcmod-batch.user.js")
t = P.read_text(encoding="utf-8")

# ── 1) 面板 id 白名单 ──
old = "['mb-panel', 'mb-list-panel', 'mb-edit-panel', 'mb-verify-panel', 'mb-addq-panel'].forEach((id) => {"
new = "['mb-panel', 'mb-list-panel', 'mb-edit-panel', 'mb-class-edit-panel', 'mb-verify-panel', 'mb-addq-panel'].forEach((id) => {"
assert old in t, "找不到 removeStalePanels 白名单"
t = t.replace(old, new, 1)

# ── 2) 路由分支 ──
anchor = """  const editMatch = location.pathname.match(/\\/item\\/edit\\/(\\d+)/);
  if (editMatch) {
    removeStalePanels();
    initEditPanel(editMatch[1]);
    return;
  }
"""
route = anchor + """
  // ---------- 模组介绍编辑页（/class/edit/<classId>-<subId>/） ----------
  const classEditMatch = location.pathname.match(/\\/class\\/edit\\/(\\d+)/);
  if (classEditMatch) {
    removeStalePanels();
    initClassEditPanel(classEditMatch[1]);
    return;
  }
"""
assert anchor in t, "找不到 item/edit 路由分支"
t = t.replace(anchor, route, 1)

# ── 3) 新函数，插在 initAddQueueRunner 之前 ──
fn_anchor = "  function initAddQueueRunner(verifyId) {"
assert fn_anchor in t, "找不到 initAddQueueRunner"

FUNC = r"""  // ---------- 模组介绍编辑页（/class/edit/<classId>-<subId>/） ----------
  // 模组页的编辑表单与资料页不同：正文编辑器可能一样，但没有 regname/icon 这些字段，
  // 所以这里只复用 setEditorHtml + fillEditMeta，其余一律走「导入 JSON → 填入 → 提交」。
  function initClassEditPanel(classId) {
    if (document.getElementById('mb-class-edit-panel')) return;

    const st = document.createElement('style');
    st.id = 'mb-ce-style';
    st.textContent = [
      '#mb-class-edit-panel{position:fixed !important;right:18px !important;bottom:24px !important;',
      'z-index:2147483647 !important;width:430px !important;pointer-events:auto !important;',
      'background:#ffffff !important;color:#111827 !important;border:2px solid #0f766e !important;',
      'border-radius:10px !important;box-shadow:0 10px 30px rgba(0,0,0,.35) !important;',
      'font-size:13.5px !important;font-family:"Microsoft YaHei",sans-serif !important;overflow:hidden !important;}',
      '#mb-class-edit-panel .mb-hd{padding:9px 12px !important;background:#0f766e !important;',
      'color:#ffffff !important;font-weight:700 !important;font-size:14px !important;}',
      '#mb-class-edit-panel .mb-bd{padding:10px 12px !important;background:#ffffff !important;color:#111827 !important;}',
      '#mb-class-edit-panel #mb-ce-info{color:#111827 !important;font-size:13px !important;line-height:1.5 !important;}',
      '#mb-class-edit-panel button{margin:3px 6px 3px 0 !important;padding:6px 12px !important;',
      'border-radius:6px !important;border:1px solid #0f766e !important;background:#0f766e !important;',
      'color:#ffffff !important;font-size:13px !important;font-weight:600 !important;cursor:pointer !important;}',
      '#mb-class-edit-panel button:hover{background:#115e59 !important;}',
      '#mb-class-edit-panel pre{margin:8px 0 0 !important;padding:8px !important;background:#f3f4f6 !important;',
      'color:#111827 !important;border:1px solid #d1d5db !important;border-radius:6px !important;',
      'max-height:24vh !important;overflow:auto !important;font-size:12px !important;white-space:pre-wrap !important;}',
    ].join('');
    document.head.appendChild(st);

    const panel = document.createElement('div');
    panel.id = 'mb-class-edit-panel';
    panel.innerHTML = '<div class="mb-hd">模组介绍 · 批量编辑 v' + MB_VERSION + '</div><div class="mb-bd">' +
      '<div id="mb-ce-info">载入中…</div>' +
      '<div style="margin:8px 0">' +
      '<button id="mb-ce-fill">填入本页</button>' +
      '<button id="mb-ce-run">填入并提交</button>' +
      '<button id="mb-ce-diag">诊断</button>' +
      '<button id="mb-ce-import">导入 JSON…</button>' +
      '<input type="file" id="mb-ce-file" accept=".json" style="display:none">' +
      '<button id="mb-ce-copy">复制正文</button>' +
      '</div><pre id="mb-ce-out"></pre></div>';
    document.body.appendChild(panel);
    raiseToTopLayer(panel);
    makeCollapsible(panel, '.mb-hd', '.mb-bd', 'ce');

    const info = (s) => { const e = document.getElementById('mb-ce-info'); if (e) e.textContent = s; };
    const out = (s) => { const e = document.getElementById('mb-ce-out'); if (e) e.textContent = s; };

    const KEY = 'mcmod-class-edit-' + classId;
    let row = null;
    try {
      const raw = sessionStorage.getItem(KEY);
      if (raw) row = JSON.parse(raw);
    } catch (e) { /* 忽略 */ }

    function refresh() {
      if (!row) {
        info('当前模组 classId=' + classId + '，还没有载入正文。点「导入 JSON…」选再编辑 JSON。');
        return;
      }
      const h1 = (row.html.match(/\[h1=/g) || []).length;
      const h2 = (row.html.match(/\[h2=/g) || []).length;
      info('classId=' + classId + ' · ' + (row.name || '') + ' · 正文 ' + row.html.length +
           ' 字符（h1×' + h1 + '，h2×' + h2 + '）');
    }

    function pickFromJson(raw) {
      const list = raw.items || raw;
      const arr = Array.isArray(list) ? list : [list];
      const hit = arr.find((x) => String(x.classId || x.id || '') === String(classId)) || arr[0];
      return hit || null;
    }

    document.getElementById('mb-ce-import').addEventListener('click', () => {
      document.getElementById('mb-ce-file').click();
    });

    document.getElementById('mb-ce-file').addEventListener('change', (e) => {
      const f = e.target.files && e.target.files[0];
      if (!f) return;
      const rd = new FileReader();
      rd.onload = () => {
        try {
          const raw = JSON.parse(rd.result);
          const hit = pickFromJson(raw);
          if (!hit || hit.html === undefined) return info('这份 JSON 里没有 html 字段');
          row = {
            classId: Number(classId),
            name: hit.name || '',
            html: hit.html,
            editRemark: hit.editRemark || '',
            editNote: hit.editNote || '',
          };
          sessionStorage.setItem(KEY, JSON.stringify(row));
          refresh();
          out('已载入「' + (row.name || classId) + '」，点「填入本页」写入编辑器');
        } catch (err) {
          info('导入失败：' + err.message);
        }
      };
      rd.readAsText(f, 'utf-8');
    });

    function doFill() {
      if (!row) { info('还没载入正文：先点「导入 JSON…」'); return false; }
      const path = setEditorHtml(row.html);
      if (!path) {
        info('没找到正文编辑器。点「诊断」看页面结构；也可以用「复制正文」手动粘贴。');
        return false;
      }
      const hits = fillEditMeta(row);
      out('正文已写入（' + path + '）' + (hits.length ? '；' + hits.join('、') : '；附言/说明未命中'));
      return true;
    }

    document.getElementById('mb-ce-fill').addEventListener('click', () => { doFill(); });

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

    document.getElementById('mb-ce-diag').addEventListener('click', () => {
      const cms = document.querySelectorAll('.CodeMirror').length;
      const ue = !!document.querySelector('#ueditor_0');
      const taSrc = !!document.querySelector('textarea.edui-sourcearea, .edui-sourcearea textarea, textarea[id*="source"]');
      const r = findByLabel('改动附言');
      const n = findByLabel('改动说明');
      out('CodeMirror: ' + cms + ' 个' +
          '\nUEditor iframe: ' + (ue ? '有' : '无') +
          '\n源码 textarea: ' + (taSrc ? '有' : '无') +
          '\n改动附言字段: ' + (r ? r.how : '未找到') +
          '\n改动说明字段: ' + (n ? n.how : '未找到') +
          '\n提交按钮: ' + (findSubmitButton() ? '找到' : '未找到') +
          '\n页面 URL: ' + location.pathname);
    });

    document.getElementById('mb-ce-copy').addEventListener('click', async () => {
      if (!row) return info('还没载入正文');
      try {
        await navigator.clipboard.writeText(row.html);
        info('正文已复制到剪贴板，粘贴到「源代码编辑器」即可');
      } catch (e) {
        out(row.html.slice(0, 3000));
        info('复制失败，正文已显示在下方（最多 3000 字）');
      }
    });

    refresh();
  }

"""

t = t.replace(fn_anchor, FUNC + fn_anchor, 1)

# ── 4) 版本号 ──
if "MB_VERSION = '2.39'" in t:
    t = t.replace("MB_VERSION = '2.39'", "MB_VERSION = '2.40'", 1)
elif 'MB_VERSION = "2.39"' in t:
    t = t.replace('MB_VERSION = "2.39"', 'MB_VERSION = "2.40"', 1)
else:
    print("⚠ 没找到版本号 2.39")

P.write_text(t, encoding="utf-8")
print(f"✓ 补丁完成，{len(t)/1024:.1f} KB / {len(t.split(chr(10)))} 行")
