// ==UserScript==
// @name         MC百科 批量新增资料（通用）
// @namespace    local.mcmod.batchadd
// @version      2.4
// @description  在 /item/add/<classId>/ 页面工具栏注入「批量新增」按钮，批量填充并提交资料
// @match        https://www.mcmod.cn/item/add/*
// @match        https://www1.mcmod.cn/item/add/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  if (window.__mbBatchLoaded) {
    const p = document.getElementById('mb-panel');
    if (p) p.style.display = p.style.display === 'none' ? 'block' : 'none';
    return;
  }
  window.__mbBatchLoaded = true;

  const classId = (location.pathname.match(/\/item\/add\/(\d+)/) || [])[1] || 'unknown';
  const STATE_KEY = 'mcmod-batch-v2-' + classId;

  let items = [];
  let running = false;
  let state = loadState();

  function loadState() {
    try {
      const s = JSON.parse(localStorage.getItem(STATE_KEY));
      if (s && Array.isArray(s.done)) return s;
    } catch (e) {}
    return { index: 0, done: [] };
  }
  function saveState() { localStorage.setItem(STATE_KEY, JSON.stringify(state)); }

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const q = (s) => document.querySelector(s);
  const qm = (k) => document.querySelector('[data-multi-id="' + k + '"]');

  function setVal(el, v) {
    if (!el || v === undefined || v === null || v === '') return false;
    const d = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(el), 'value');
    if (d && d.set) d.set.call(el, String(v)); else el.value = String(v);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  }

  function findConfirm() {
    const els = [...document.querySelectorAll('button,a,div,span,p')].filter((el) => {
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0 && (el.innerText || '').trim() === '确定提交';
    });
    if (!els.length) return null;
    els.sort((a, b) => {
      const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
      return ra.width * ra.height - rb.width * rb.height;
    });
    return els[0];
  }

  function log(msg, color) {
    const box = q('#mb-log');
    if (box) {
      const div = document.createElement('div');
      div.textContent = msg;
      if (color) div.style.color = color;
      box.appendChild(div);
      box.scrollTop = box.scrollHeight;
    }
    console.log('[批量新增] ' + msg);
  }

  // ---- 资料类型：默认「物品/方块」，可在数据里用 type 覆盖 ----
  function ensureType(typeName) {
    const want = typeName || '物品/方块';
    const cur = document.querySelector(".common-item-mold-list li a[data-category-selected='true']");
    if (cur && (cur.innerText || '').includes(want)) return true;
    const a = [...document.querySelectorAll('.common-item-mold-list li a')].find((x) => (x.innerText || '').includes(want));
    if (!a) return false;
    a.click();
    return true;
  }

  // ---- 资料分类：已有同名就直接选，没有就自定义新建 ----
  function setCategory(cat) {
    if (!cat) return false;
    const sel = q('#item-type-select');
    if (!sel) return false;
    const has = [...sel.options].some((o) => o.value === cat);
    if (has) {
      setVal(sel, cat);
      try { if (window.jQuery && window.jQuery(sel).selectpicker) window.jQuery(sel).selectpicker('refresh'); } catch (e) {}
      return true;
    }
    setVal(sel, '');
    const custom = q('#item-type-custom');
    if (custom) setVal(custom, cat);
    return true;
  }

  async function fillOne(it) {
    ensureType(it.type);
    await sleep(1200);
    setCategory(it.category);
    await sleep(400);

    setVal(qm('name'), it.name);
    setVal(qm('ename'), it.ename);
    setVal(qm('regname'), it.regname);
    if (it.maxstack) setVal(qm('maxstack'), it.maxstack);
    if (it.damage) setVal(qm('damage'), it.damage);
    if (it.oredict) setVal(qm('oredict'), it.oredict);
    setVal(qm('remark'), it.remark || ('批量录入 ' + classId));

    if (it.icon32) {
      setVal(q('#icon-32x-editor'), it.icon32);
      setVal(q('#icon-32x'), it.icon32);
      await sleep(500);
      if (it.icon128) {
        setVal(q('#icon-128x-editor'), it.icon128);
        setVal(q('#icon-128x'), it.icon128);
        await sleep(400);
      } else {
        const sync = [...document.querySelectorAll('button')].find((b) => (b.innerText || '').includes('同步至大图标'));
        if (sync) sync.click();
        await sleep(600);
      }
    }

    if (it.html) {
      const cm = q('.CodeMirror');
      if (cm && cm.CodeMirror) cm.CodeMirror.setValue(it.html);
      else {
        const frame = q('#ueditor_0');
        if (frame && frame.contentDocument && frame.contentDocument.body) frame.contentDocument.body.innerHTML = it.html;
      }
    }
    await sleep(500);
  }

  async function submitOne() {
    const btn = q('#edit-submit-button');
    if (!btn) { log('找不到提交按钮', '#f87171'); return false; }
    btn.click();
    await sleep(2200);
    const ok = findConfirm();
    if (!ok) { log('没等到确认弹窗（可能被校验拦住）', '#f87171'); return false; }
    ok.click();
    await sleep(3600);
    const success = /成功提交/.test(document.body.innerText);
    const next = findConfirm();
    if (next) { next.click(); await sleep(1500); }
    return success;
  }

  async function runBatch() {
    if (running) return;
    running = true;
    updateStatus();
    const doneSet = new Set(state.done);
    for (let i = state.index; i < items.length; i++) {
      if (!running) { log('已暂停', '#fbbf24'); break; }
      const it = items[i];
      if (!it.force && doneSet.has(it.regname)) { log('跳过（本机已提交）' + (it.name || ''), '#5d6678'); state.index = i + 1; saveState(); continue; }
      state.index = i;
      saveState();
      log('▶ ' + (i + 1) + '/' + items.length + ' ' + (it.name || it.regname || ''));
      try {
        await fillOne(it);
        const ok = await submitOne();
        log((ok ? '✔ 已提交 ' : '✖ 未确认 ') + (it.name || ''), ok ? '#4ade80' : '#f87171');
        if (ok) { state.done.push(it.regname || it.name); state.index = i + 1; saveState(); }
        else { log('停止：避免在失败状态下继续', '#f87171'); break; }
      } catch (e) {
        log('异常：' + e.message, '#f87171');
        break;
      }
      await sleep(700);
    }
    running = false;
    updateStatus();
    log('—— 批次结束 ——');
  }

  function updateStatus() {
    const el = q('#mb-status');
    if (el) {
      el.textContent = 'class ' + classId + ' ｜ 共 ' + items.length + ' 条 ｜ 已提交 ' + state.done.length +
        ' ｜ 下一条 ' + (state.index + 1) + (running ? ' ｜ 运行中…' : '');
    }
  }

  function buildPanel() {
    // 站点 CSS 会覆盖我们的字体/颜色，所以关键属性一律带 !important
    const CSS = [
      '#mb-panel{position:fixed;left:50%;top:92px;transform:translateX(-50%);z-index:2147483600;width:480px;',
      'background:#0f131a !important;color:#e8edf6 !important;border:1px solid #2a3446;border-radius:14px;',
      'padding:16px 18px;box-shadow:0 18px 48px rgba(0,0,0,.7);',
      'font-family:"Microsoft YaHei UI","Microsoft YaHei",sans-serif !important;font-size:14px !important;line-height:1.6 !important;',
      'display:none;text-align:left}',
      '#mb-panel *{box-sizing:border-box;font-family:inherit !important}',
      '#mb-head{display:flex;align-items:center;margin-bottom:12px}',
      '#mb-title{font-size:16px !important;font-weight:700 !important;color:#f2f6fc !important}',
      '#mb-ver{font-size:12px !important;color:#6b7a91 !important;margin-left:6px;font-weight:400 !important}',
      '#mb-close{margin-left:auto;cursor:pointer;color:#8593a8 !important;font-size:18px !important;line-height:1;padding:0 4px}',
      '#mb-close:hover{color:#e8edf6 !important}',
      '#mb-status{font-size:13.5px !important;color:#7fb4ff !important;margin-bottom:12px !important}',
      '#mb-file{width:100%;margin-bottom:12px;color:#cbd5e3 !important;font-size:13px !important;',
      'background:#161c26 !important;border:1px solid #2a3446;border-radius:8px;padding:7px 9px}',
      '#mb-btns{display:flex;gap:8px}',
      '#mb-btns button{height:36px;border:0;border-radius:8px;cursor:pointer;font-size:13.5px !important;font-weight:600 !important}',
      '#mb-run{flex:2;background:#2563eb !important;color:#ffffff !important}',
      '#mb-run:hover{background:#1d4ed8 !important}',
      '#mb-stop{flex:2;background:#2c3547 !important;color:#dfe6f2 !important}',
      '#mb-stop:hover{background:#3a465c !important}',
      '#mb-reset{flex:1;background:#2c3547 !important;color:#dfe6f2 !important}',
      '#mb-reset:hover{background:#3a465c !important}',
      '#mb-log{margin-top:12px;height:200px;overflow:auto;background:#080b10 !important;border:1px solid #1e2635;',
      'border-radius:10px;padding:10px;font-family:Consolas,"Courier New",monospace !important;',
      'font-size:12.5px !important;line-height:1.75 !important;color:#c4cfdf !important;white-space:pre-wrap}',
      '#mb-log div{color:inherit}',
    ].join('');
    if (!document.getElementById('mb-style')) {
      const st = document.createElement('style');
      st.id = 'mb-style';
      st.textContent = CSS;
      document.head.appendChild(st);
    }
    if (document.getElementById('mb-panel')) return;

    const d = document.createElement('div');
    d.id = 'mb-panel';
    d.innerHTML =
      '<div id="mb-head">' +
      '<span id="mb-title">MC百科 批量新增</span><span id="mb-ver">v2.4</span>' +
      '<span id="mb-close">✕</span>' +
      '</div>' +
      '<div id="mb-status">未载入数据</div>' +
      '<input type="file" id="mb-file" accept=".json">' +
      '<div id="mb-btns">' +
      '<button id="mb-run">开始批量</button>' +
      '<button id="mb-stop">暂停</button>' +
      '<button id="mb-reset">重置</button>' +
      '</div>' +
      '<div id="mb-log"></div>';
    document.body.appendChild(d);

    q('#mb-close').onclick = () => { d.style.display = 'none'; };
    q('#mb-file').addEventListener('change', (e) => {
      const f = e.target.files[0];
      if (!f) return;
      const fr = new FileReader();
      fr.onload = () => {
        try {
          const arr = JSON.parse(fr.result);
          if (!Array.isArray(arr)) throw new Error('顶层必须是数组');
          items = arr;
          state.index = 0;
          saveState();
          const doneSet = new Set(state.done);
          const skip = items.filter(function (x) { return doneSet.has(x.regname) && !x.force; }).length;
          log('已载入 ' + items.length + ' 条' + (skip ? '（其中 ' + skip + ' 条本机已提交过，会自动跳过）' : ''));
          updateStatus();
        } catch (err) { log('载入失败：' + err.message, '#f87171'); }
      };
      fr.readAsText(f, 'utf-8');
    });
    q('#mb-run').onclick = () => {
      if (!items.length) return log('先选择数据文件', '#f87171');
      if (!/\/item\/add\//.test(location.pathname)) return log('当前不是新增资料页', '#f87171');
      runBatch();
    };
    q('#mb-stop').onclick = () => { running = false; log('已请求暂停'); };
    q('#mb-reset').onclick = () => {
      if (!confirm('清空本机「已提交」记录？（站点上的资料不受影响）')) return;
      state = { index: 0, done: [] }; saveState(); updateStatus(); log('进度已重置');
    };
  }

  function injectToolbarButton() {
    if (document.getElementById('mb-open')) return true;
    const inNav = (el) => !!el.closest('nav,header,.navbar,.mcmod-header,.header');
    const vis = (el) => el.getBoundingClientRect().width > 0;
    const all = [...document.querySelectorAll('button,a,span,label,div,li,p')];

    const makeBtn = (style) => {
      const btn = document.createElement('button');
      btn.id = 'mb-open';
      btn.textContent = '批量新增';
      btn.className = 'btn btn-sm ' + (style || '');
      btn.type = 'button';
      btn.style.cursor = 'pointer';
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const p = document.getElementById('mb-panel');
        p.style.display = (p.style.display === 'block') ? 'none' : 'block';
      });
      return btn;
    };

    // 1) 首选：编辑帮助里的「批量导入：《如何批量添加资料》」下面
    const importLink = all.find((el) => el.tagName === 'A' && (el.innerText || '').includes('如何批量添加资料'));
    if (importLink) {
      const block = importLink.closest('li') || importLink.closest('p') || importLink.parentElement;
      const btn = makeBtn('btn-secondary');
      btn.style.display = 'inline-block';
      btn.style.marginTop = '8px';
      block.parentElement.insertBefore(btn, block.nextSibling);
      console.log('[批量新增] 按钮已注入：批量导入下方');
      return true;
    }

    // 2) 退路：编辑器工具栏「读取 (Ctrl+O)」后面
    const readBtn = all.find((b) => /Ctrl\s*[\+＋]\s*O/i.test(b.innerText || '') && !inNav(b) && vis(b))
                 || all.find((b) => (b.innerText || '').trim() === '正文预览' && !inNav(b) && vis(b));
    if (readBtn) {
      const btn = makeBtn(readBtn.className && readBtn.className.indexOf('btn') > -1 ? readBtn.className : '');
      btn.style.marginLeft = '10px';
      const holder = readBtn.closest('label') || readBtn;
      holder.parentElement.insertBefore(btn, holder.nextSibling);
      console.log('[批量新增] 按钮已注入：工具栏读取按钮旁');
      return true;
    }

    return false;
  }
  buildPanel();

  let tries = 0;
  const timer = setInterval(() => {
    tries++;
    if (injectToolbarButton() || tries > 60) clearInterval(timer);
  }, 500);

  if (state.done.length) log('本机已提交 ' + state.done.length + ' 条');
  updateStatus();
})();
