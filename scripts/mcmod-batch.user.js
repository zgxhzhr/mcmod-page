// ==UserScript==
// @name         MC百科 批量新增资料（通用）
// @namespace    local.mcmod.batchadd
// @version      2.25
// @description  /item/add/* 批量新增；/item/list/* 读取列表与编辑链接（为批量编辑做准备）
// @match        https://www.mcmod.cn/item/add/*
// @match        https://www1.mcmod.cn/item/add/*
// @match        https://www.mcmod.cn/item/list/*
// @match        https://www.mcmod.cn/item/edit/*
// @match        https://www.mcmod.cn/verify*
// @match        https://www1.mcmod.cn/item/list/*
// @match        https://www1.mcmod.cn/item/edit/*
// @match        https://www1.mcmod.cn/verify*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  // 面板显示用的版本号：只在这里改，三处面板共用
  const MB_VERSION = '2.25';

  // 批量编辑队列：键与读写函数必须放在最前，
  // 因为列表页分支在 IIFE 开头就会执行（放在后面会命中 const 的暂时性死区）
  /** 把面板提升到浏览器顶层：页面若有自己的遮罩层，普通 z-index 压不过，popover 可以。
   *  不支持的浏览器静默退回普通 fixed 定位。 */
  function raiseToTopLayer(panel) {
    try {
      if (typeof panel.showPopover === 'function') {
        panel.setAttribute('popover', 'manual');
        panel.showPopover();
        return true;
      }
    } catch (e) { /* 忽略 */ }
    return false;
  }

  /** 清掉 DOM 里版本不同的旧面板：扩展与篡改猴运行在不同隔离环境，
   *  window 标记互相看不见，但 DOM 共用，所以按面板上的版本号判断。 */
  function removeStalePanels() {
    ['mb-panel', 'mb-list-panel', 'mb-edit-panel'].forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      const txt = el.innerText || '';
      if (txt.indexOf('v' + MB_VERSION) < 0) {
        el.remove();
        console.log('[批量工具] 移除旧版本面板 #' + id + '（当前 v' + MB_VERSION + '）');
      }
    });
  }

  /** 让面板可收起/展开：默认收起，点标题栏切换，状态记在 localStorage。
   *  bodySel 为空时，把标题栏之外的所有兄弟节点包进一个 body 容器。 */
  function makeCollapsible(panel, headSel, bodySel, key) {
    const head = panel.querySelector(headSel);
    if (!head) return;
    let body = bodySel ? panel.querySelector(bodySel) : null;
    if (!body) {
      body = document.createElement('div');
      body.className = 'mb-body-wrap';
      [...panel.children].forEach((el) => { if (el !== head) body.appendChild(el); });
      panel.appendChild(body);
    }
    const STORE = 'mb-collapsed-' + key;
    let ind = head.querySelector('.mb-fold');
    if (!ind) {
      ind = document.createElement('span');
      ind.className = 'mb-fold';
      ind.style.cssText = 'margin-left:8px;font-weight:400;opacity:.9;font-size:12px';
      head.appendChild(ind);
    }
    function apply(collapsed) {
      body.style.display = collapsed ? 'none' : '';
      panel.dataset.collapsed = collapsed ? '1' : '0';
      ind.textContent = collapsed ? '▼ 展开' : '▲ 收起';
      head.style.cursor = 'pointer';
      head.title = collapsed ? '点击展开面板' : '点击收起面板';
    }
    apply(localStorage.getItem(STORE) !== '0');   // 默认收起
    head.addEventListener('click', (ev) => {
      if (ev.target.closest('input,button,a,select,label')) return;   // 不抢头部里的控件
      const next = panel.dataset.collapsed !== '1';
      apply(next);
      localStorage.setItem(STORE, next ? '1' : '0');
    });
  }

  const PLAN_KEY = 'mb-edit-plan';
  function loadEditPlan() {
    try { return JSON.parse(sessionStorage.getItem(PLAN_KEY) || 'null'); } catch (e) { return null; }
  }
  function saveEditPlan(p) { sessionStorage.setItem(PLAN_KEY, JSON.stringify(p)); }

  /** 队列里一条任务对应的落地页：编辑资料走 /item/edit/<id>/，新增资料走 /item/add/<classId>-<verifyId>/ */
  function urlOfTask(item, classId) {
    if (item && item.targetUrl) return item.targetUrl;
    if (item && item.kind === '新增' && item.verifyId) {
      return '/item/add/' + (classId || '31864') + '-' + item.verifyId + '/';
    }
    return '/item/edit/' + (item && item.id) + '/';
  }
  function clearEditPlan() { sessionStorage.removeItem(PLAN_KEY); }



  // 同页可能同时存在「篡改猴旧版」和「扩展新版」：只有版本相同才复用，
  // 否则清掉旧面板由本脚本接管（避免旧版一直显示 v2.6）
  if (window.__mbBatchLoaded) {
    const panels = ['mb-panel', 'mb-list-panel', 'mb-edit-panel']
      .map((id) => document.getElementById(id)).filter(Boolean);
    const sameVer = panels.some((el) => (el.innerText || '').indexOf('v' + MB_VERSION) >= 0);
    if (sameVer) {
      const p = document.getElementById('mb-panel');
      if (p) p.style.display = p.style.display === 'none' ? 'block' : 'none';
      return;
    }
    panels.forEach((el) => el.remove());
    console.log('[批量工具] 检测到旧版本面板，已由 v' + MB_VERSION + ' 接管');
  }
  window.__mbBatchLoaded = true;

  const classId = (location.pathname.match(/\/item\/add\/(\d+)/) || [])[1] || 'unknown';

  // 退回条目重交：URL 形如 /item/add/<classId>-<verifyId>/，若有待执行队列则走队列执行端
  const addQueueMatch = location.pathname.match(/\/item\/add\/\d+-(\d+)/);
  if (addQueueMatch) {
    const pending = loadEditPlan();
    if (pending && pending.items && pending.items[pending.index]) {
      initAddQueueRunner(addQueueMatch[1]);
      return;
    }
  }

  // ---------- 列表页模式（只读：读取分类/名称/资料 id/编辑链接） ----------
  const listMatch = location.pathname.match(/\/item\/list\/(\d+)-(\d+)\.html/);
  if (listMatch) {
    removeStalePanels();
    initListPanel(listMatch[1], listMatch[2]);
    return;
  }

  // ---------- 审核列表模式（/verify*）：读取已退回/审核中/已通过 ----------
  if (/^\/verify/.test(location.pathname)) {
    removeStalePanels();
    initVerifyPanel();
    return;
  }

  // ---------- 编辑页模式（批量编辑队列执行端） ----------
  const editMatch = location.pathname.match(/\/item\/edit\/(\d+)/);
  if (editMatch) {
    removeStalePanels();
    initEditPanel(editMatch[1]);
    return;
  }

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

  // 注意：这三个必须写成 function 声明（会提升），
  // 列表页/编辑页分支在 IIFE 开头就执行，用 const 箭头函数会命中暂时性死区
  function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }
  function q(sel) { return document.querySelector(sel); }
  function qm(k) { return document.querySelector('[data-multi-id="' + k + '"]'); }

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

    // 没有图标时：大图标字段必须清空并勾选「删除大图标/删除大小图标」，
    // 否则审核会以「大图标是空的」退回（实测）
    if (!it.icon32) {
      const delBox = [...document.querySelectorAll('input[type=checkbox], label, span')].find((el) => {
        const txt = (el.innerText || el.value || '').replace(/\s/g, '');
        return /删除(大|大小)图标/.test(txt);
      });
      if (delBox) {
        const box = delBox.tagName === 'INPUT' ? delBox
          : (delBox.querySelector && delBox.querySelector('input[type=checkbox]'));
        if (box && !box.checked) { box.click(); await sleep(200); }
      }
    }

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
      '#mb-panel{position:fixed !important;left:50% !important;top:92px !important;transform:translateX(-50%) !important;',
      'z-index:2147483647 !important;width:480px !important;background:#ffffff !important;color:#111827 !important;',
      'border:2px solid #2563eb !important;border-radius:10px !important;padding:14px 16px !important;',
      'box-shadow:0 12px 36px rgba(0,0,0,.35) !important;font-family:"Microsoft YaHei",sans-serif !important;',
      'font-size:14px !important;line-height:1.6 !important;display:none;text-align:left !important;pointer-events:auto !important;}',
      '#mb-panel *{box-sizing:border-box !important;font-family:inherit !important}',
      '#mb-head{display:flex !important;align-items:center !important;margin-bottom:10px !important}',
      '#mb-title{font-size:16px !important;font-weight:700 !important;color:#111827 !important}',
      '#mb-ver{font-size:12px !important;color:#6b7280 !important;margin-left:6px !important}',
      '#mb-close{margin-left:auto !important;cursor:pointer !important;color:#6b7280 !important;font-size:18px !important}',
      '#mb-status{font-size:13.5px !important;color:#1d4ed8 !important;margin-bottom:10px !important}',
      '#mb-file{width:100% !important;margin-bottom:10px !important;color:#111827 !important;font-size:13px !important;',
      'background:#f3f4f6 !important;border:1px solid #d1d5db !important;border-radius:8px !important;padding:6px 8px !important}',
      '#mb-pick{width:100% !important;margin-bottom:10px !important;padding:6px 8px !important;border-radius:8px !important;',
      'border:1px solid #d1d5db !important;background:#ffffff !important;color:#111827 !important;font-size:13px !important}',
      '#mb-btns{display:flex !important;gap:8px !important;flex-wrap:wrap !important}',
      '#mb-btns button{height:34px !important;border:1px solid #1d4ed8 !important;border-radius:8px !important;cursor:pointer !important;',
      'font-size:13px !important;font-weight:600 !important;padding:0 12px !important}',
      '#mb-fill{background:#0ea5e9 !important;color:#fff !important;border-color:#0284c7 !important}',
      '#mb-run{background:#2563eb !important;color:#fff !important}',
      '#mb-stop{background:#6b7280 !important;color:#fff !important;border-color:#4b5563 !important}',
      '#mb-reset{background:#ffffff !important;color:#111827 !important;border-color:#9ca3af !important}',
      '#mb-log{margin-top:10px !important;height:200px !important;overflow:auto !important;background:#f9fafb !important;',
      'border:1px solid #e5e7eb !important;border-radius:8px !important;padding:10px !important;',
      'font-family:Consolas,monospace !important;font-size:12.5px !important;line-height:1.7 !important;color:#111827 !important;',
      'white-space:pre-wrap !important}',
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
      '<span id="mb-title">MC百科 批量新增</span><span id="mb-ver">v' + MB_VERSION + '</span>' +
      '<span id="mb-close">✕</span>' +
      '</div>' +
      '<div id="mb-status">未载入数据</div>' +
      '<input type="file" id="mb-file" accept=".json">' +
      '<select id="mb-pick"></select>' +
      '<div id="mb-btns">' +
      '<button id="mb-fill">只填充（不提交）</button>' +
      '<button id="mb-run">开始批量</button>' +
      '<button id="mb-stop">暂停</button>' +
      '<button id="mb-reset">重置</button>' +
      '</div>' +
      '<div id="mb-log"></div>';
    document.body.appendChild(d);
    makeCollapsible(d, '#mb-head', null, 'add');

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
          const pick = q('#mb-pick');
          if (pick) {
            pick.innerHTML = '';
            items.forEach((it, i) => {
              const op = document.createElement('option');
              op.value = String(i);
              op.textContent = (it.name || it.regname || ('#' + i)) +
                (it.icon128 ? '' : '（无大图标）');
              pick.appendChild(op);
            });
          }
          log('已载入 ' + items.length + ' 条' + (skip ? '（其中 ' + skip + ' 条本机已提交过，会自动跳过）' : ''));
          updateStatus();
        } catch (err) { log('载入失败：' + err.message, '#f87171'); }
      };
      fr.readAsText(f, 'utf-8');
    });
    q('#mb-fill').onclick = async () => {
      if (!items.length) return log('先选择数据文件', '#f87171');
      const pick = q('#mb-pick');
      const idx = pick ? Number(pick.value || 0) : 0;
      const it = items[idx];
      if (!it) return log('没选到条目', '#f87171');
      log('只填充：' + (it.name || it.regname) + '（不提交）', '#7fb4ff');
      try {
        await fillOne(it);
        log('已填充，请人工检查后点页面上的提交按钮。', '#4ade80');
      } catch (err) {
        log('填充失败：' + err.message, '#f87171');
      }
    };

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

  // ================= 列表页：读取与导出（第一阶段，只读） =================

  function initListPanel(classId, typeId) {
    if (document.getElementById('mb-list-panel')) return;

    const style = document.createElement('style');
    style.id = 'mb-list-style';
    style.textContent = [
      '#mb-list-panel{position:fixed !important;right:18px !important;top:96px !important;',
      'z-index:2147483647 !important;width:430px !important;pointer-events:auto !important;',
      'background:#ffffff !important;color:#111827 !important;border:2px solid #2563eb !important;',
      'border-radius:10px !important;box-shadow:0 10px 30px rgba(0,0,0,.35) !important;',
      'font-size:13.5px !important;font-family:"Microsoft YaHei",sans-serif !important;overflow:hidden !important;}',
      '#mb-list-panel .mb-hd{display:flex !important;justify-content:space-between !important;align-items:center !important;',
      'padding:9px 12px !important;background:#2563eb !important;color:#ffffff !important;font-weight:700 !important;font-size:14px !important;}',
      '#mb-list-panel .mb-bd{padding:10px 12px !important;background:#ffffff !important;color:#111827 !important;max-height:60vh !important;overflow:auto !important;}',
      '#mb-list-panel button{margin:3px 6px 3px 0 !important;padding:6px 12px !important;border-radius:6px !important;',
      'border:1px solid #1d4ed8 !important;background:#2563eb !important;color:#ffffff !important;',
      'font-size:13px !important;font-weight:600 !important;cursor:pointer !important;}',
      '#mb-list-panel button:hover{background:#1d4ed8 !important;}',
      '#mb-list-panel pre{margin:8px 0 0 !important;padding:8px !important;background:#f3f4f6 !important;',
      'color:#111827 !important;border:1px solid #d1d5db !important;border-radius:6px !important;',
      'max-height:34vh !important;overflow:auto !important;font-size:12px !important;white-space:pre-wrap !important;}',
    ].join('');
    document.head.appendChild(style);

    const panel = document.createElement('div');
    panel.id = 'mb-list-panel';
    panel.innerHTML =
      '<div class="mb-hd"><span>MC百科 列表工具 · v' + MB_VERSION + '</span><span style="cursor:pointer" id="mb-list-x">✕</span></div>' +
      '<div class="mb-bd">' +
      '<div id="mb-list-info">未读取</div>' +
      '<div style="margin:8px 0">' +
      '<button id="mb-list-read">读取列表</button>' +
      '<button id="mb-list-copy">复制 JSON</button>' +
      '<button id="mb-list-dl">下载 JSON</button>' +
      '<button id="mb-list-quick">切换快速编辑</button>' +
      '<button id="mb-list-edit">批量编辑…</button>' +
      '<button id="mb-list-harvest">抓取全部原文</button>' +
      '<label style="display:inline-block;margin-left:6px;color:#111827 !important;font-size:13px !important;">' +
      '<input type="checkbox" id="mb-list-auto" style="vertical-align:-2px;margin-right:4px;">自动执行</label>' +
      '<input type="file" id="mb-list-plan" accept=".json" style="display:none">' +
      '</div><pre id="mb-list-out"></pre></div>';
    document.body.appendChild(panel);
    raiseToTopLayer(panel);
    makeCollapsible(panel, '.mb-hd', '.mb-bd', 'list');

    const info = (s) => { const el = document.getElementById('mb-list-info'); if (el) el.textContent = s; };
    const out = (s) => { const el = document.getElementById('mb-list-out'); if (el) el.textContent = s; };

    function parseList() {
      const rows = [];
      document.querySelectorAll('table.item-list-table tbody tr').forEach((tr) => {
        const th = tr.querySelector('th.item-list-type-left');
        const cat = th ? th.innerText.trim() : '';
        tr.querySelectorAll('td.item-list-type-right ul li span a[href*="/item/"]').forEach((a) => {
          const m = (a.getAttribute('href') || '').match(/\/item\/(\d+)\.html/);
          if (!m) return;
          const id = Number(m[1]);
          const name = (a.innerText || '').trim();
          const en = a.getAttribute('data-en') || '';
          const hit = rows.find((r) => r.id === id);
          if (hit) {
            if (!hit.name && name) hit.name = name;
            if (!hit.en && en) hit.en = en;
            return;
          }
          // 编辑页地址可直接由资料 id 推出，不必依赖「快速编辑」
          rows.push({ category: cat, name, en, id, edit: '/item/edit/' + id + '/' });
        });
      });
      // 合并快速编辑暴露的「编辑」链接
      document.querySelectorAll('a[href*="/item/edit/"]').forEach((a) => {
        const m = (a.getAttribute('href') || '').match(/\/item\/edit\/(\d+)/);
        if (!m) return;
        const id = Number(m[1]);
        const hit = rows.find((r) => r.id === id);
        if (hit) hit.edit = a.getAttribute('href');
      });
      return rows;
    }

    let rows = [];
    document.getElementById('mb-list-read').addEventListener('click', () => {
      rows = parseList();
      const byCat = {};
      rows.forEach((r) => { byCat[r.category] = (byCat[r.category] || 0) + 1; });
      const hasEdit = rows.filter((r) => r.edit).length;
      info('已读取 ' + rows.length + ' 条 / ' + Object.keys(byCat).length + ' 个分类' +
           (hasEdit ? '（含 ' + hasEdit + ' 条编辑链接）' : '（无编辑链接，先点「切换快速编辑」）'));
      out(JSON.stringify({ classId, typeId, total: rows.length, byCategory: byCat, rows }, null, 2).slice(0, 4000));
      console.log('[列表工具]', rows);
    });

    document.getElementById('mb-list-copy').addEventListener('click', () => {
      if (!rows.length) return info('先点「读取列表」');
      const txt = JSON.stringify({ classId, typeId, rows }, null, 2);
      navigator.clipboard.writeText(txt).then(() => info('已复制 JSON（' + rows.length + ' 条）'),
                                             () => info('复制失败，请用「下载 JSON」'));
    });

    document.getElementById('mb-list-dl').addEventListener('click', () => {
      if (!rows.length) return info('先点「读取列表」');
      const blob = new Blob([JSON.stringify({ classId, typeId, rows }, null, 2)], { type: 'application/json' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'mcmod-list-' + classId + '-' + typeId + '.json';
      a.click();
      info('已下载 JSON（' + rows.length + ' 条）');
    });

    document.getElementById('mb-list-quick').addEventListener('click', async () => {
      const btn = document.querySelector('.item-list-switch-quickedit');
      if (!btn) return info('没找到「快速编辑」开关');
      btn.click();
      await sleep(900);
      rows = parseList();
      const n = rows.filter((r) => r.edit).length;
      info('已切换快速编辑，收集到 ' + n + ' 条编辑链接（共 ' + rows.length + ' 条）');
    });

    document.getElementById('mb-list-edit').addEventListener('click', () => {
      document.getElementById('mb-list-plan').click();
    });

    document.getElementById('mb-list-plan').addEventListener('change', (e) => {
      const f = e.target.files && e.target.files[0];
      if (!f) return;
      const rd = new FileReader();
      rd.onload = () => {
        try {
        let plan;
        try { plan = JSON.parse(rd.result); } catch (err) { return info('JSON 解析失败：' + err.message); }
        const items = plan.items || plan;
        if (!Array.isArray(items) || !items.length) return info('计划里没有 items');
        if (!rows.length) rows = parseList();
        const queue = [];
        const missed = [];
        items.forEach((it) => {
          const hit = it.id ? rows.find((r) => r.id === Number(it.id))
                            : rows.find((r) => r.name === it.name);
          if (hit) queue.push(Object.assign({ id: hit.id, name: hit.name }, it));
          else missed.push(it.name || it.id);
        });
        if (!queue.length) return info('没有匹配到任何条目（检查 id/name）');
        const autoEl = document.getElementById('mb-list-auto');
        const autoRun = !!(autoEl && autoEl.checked);
        saveEditPlan({ items: queue, index: 0, done: [], missed, autoRun, paused: false });
        info('匹配 ' + queue.length + ' 条' + (missed.length ? '，未匹配 ' + missed.length + ' 条' : '') +
             (autoRun ? '；自动执行已开启' : '；手动模式（每页需点执行）') +
             '，即将跳到第一条编辑页…');
        setTimeout(() => { location.href = '/item/edit/' + queue[0].id + '/'; }, 800);
        } catch (err) {
          info('导入失败：' + err.message);
          console.error('[批量工具] 导入编辑计划失败', err);
        }
      };
      rd.readAsText(f, 'utf-8');
    });

    // 抓取全部原文：逐条 fetch 详情页，取 .item-content 里的渲染后正文
    document.getElementById('mb-list-harvest').addEventListener('click', async () => {
      if (!rows.length) rows = parseList();
      if (!rows.length) return info('先点「读取列表」');
      const out = [];
      for (let i = 0; i < rows.length; i += 1) {
        const r = rows[i];
        info('抓取原文 ' + (i + 1) + '/' + rows.length + '：' + (r.name || r.id));
        try {
          const res = await fetch('/item/' + r.id + '.html', { credentials: 'include' });
          const txt = await res.text();
          const doc = new DOMParser().parseFromString(txt, 'text/html');
          const el = doc.querySelector('.item-content');
          out.push({
            id: r.id, name: r.name, category: r.category,
            html: el ? el.innerHTML.replace(/\s+style="[^"]*"/g, '').trim() : '',
          });
        } catch (e) {
          out.push({ id: r.id, name: r.name, error: String(e) });
        }
        out[out.length - 1]._n = i + 1;
        if (i % 8 === 7) info('抓取原文 ' + (i + 1) + '/' + rows.length + '…');
        await sleep(600);   // 控速
      }
      out.forEach((x) => delete x._n);
      const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
      downloadJson({ classId, typeId, total: out.length, items: out }, 'mcmod-全部原文-' + stamp + '.json');
      info('已抓取 ' + out.length + ' 条原文并下载 JSON');
    });

    document.getElementById('mb-list-x').addEventListener('click', () => panel.remove());
    console.log('[列表工具] 面板已注入', classId, typeId);
  }


  // ================= 批量编辑：执行端（编辑页） =================

  /** 编辑页与新增页的编辑器不同，这里按可能性依次尝试，返回命中的路径名。 */
  function setEditorHtml(html) {
    // 1) CodeMirror：页面可能有多个实例（编辑页实测 2 个 iframe + 多个编辑器），
    //    正文编辑器是高度最大的那个
    const cms = [...document.querySelectorAll('.CodeMirror')]
      .filter((el) => el.CodeMirror && typeof el.CodeMirror.setValue === 'function');
    if (cms.length) {
      cms.sort((a, b) => b.getBoundingClientRect().height - a.getBoundingClientRect().height);
      cms[0].CodeMirror.setValue(html);
      return 'CodeMirror(' + cms.length + ')';
    }
    // 2) UEditor 富文本 iframe
    const iframe = document.querySelector('#ueditor_0');
    if (iframe && iframe.contentDocument && iframe.contentDocument.body) {
      iframe.contentDocument.body.innerHTML = html;
      return 'ueditor-iframe';
    }
    // 3) UEditor「源代码」模式的 textarea
    const ta = document.querySelector('textarea.edui-sourcearea, .edui-sourcearea textarea, #edui1_source textarea, textarea[id*="source"]');
    if (ta) {
      const d = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(ta), 'value');
      if (d && d.set) d.set.call(ta, html); else ta.value = html;
      ta.dispatchEvent(new Event('input', { bubbles: true }));
      ta.dispatchEvent(new Event('change', { bubbles: true }));
      return 'textarea-source';
    }
    return null;
  }

  /** 读取当前正文（覆盖前的存档用），返回 {html, path}。 */
  function getEditorHtml() {
    const cms = [...document.querySelectorAll('.CodeMirror')]
      .filter((el) => el.CodeMirror && typeof el.CodeMirror.getValue === 'function');
    if (cms.length) {
      cms.sort((a, b) => b.getBoundingClientRect().height - a.getBoundingClientRect().height);
      return { html: cms[0].CodeMirror.getValue() || '', path: 'CodeMirror' };
    }
    const iframe = document.querySelector('#ueditor_0');
    if (iframe && iframe.contentDocument && iframe.contentDocument.body) {
      return { html: iframe.contentDocument.body.innerHTML || '', path: 'ueditor-iframe' };
    }
    const ta = document.querySelector('textarea.edui-sourcearea, .edui-sourcearea textarea, textarea[id*="source"]');
    if (ta) return { html: ta.value || '', path: 'textarea-source' };
    return { html: '', path: null };
  }

  /** 下载 JSON（队列结束时的旧正文备份）。 */
  function downloadJson(obj, filename) {
    const blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
  }

  /** 编辑页提交按钮可能叫「完成编辑 / 保存 / 提交」，新增页是 #edit-submit-button。 */
  function findSubmitButton() {
    // 实测：真正能提交的是 #edit-submit-button（文字为空也照样有效），
    // 所以必须先试它；可见的「完成编辑」只是文字外壳，点了不提交。
    const direct = document.querySelector('#edit-submit-button');
    if (direct) return direct;

    // 退化路径：可见且文字精确为「完成编辑/保存」等的最小元素
    const WORDS = ['完成编辑', '保存修改', '确认提交', '保存', '提交'];
    const exact = [...document.querySelectorAll('button,a,div,span,li')]
      .map((el) => ({ el, r: el.getBoundingClientRect(), txt: (el.innerText || '').replace(/\s/g, '') }))
      .filter((x) => x.r.width > 4 && x.r.height > 4 && x.txt.length <= 6 && WORDS.indexOf(x.txt) >= 0);
    if (exact.length) {
      exact.sort((a, b) => a.r.width * a.r.height - b.r.width * b.r.height);
      return exact[0].el;
    }
    return null;
  }

  /** 确认按钮：新增页是「确定提交」，编辑页实测是「编辑资料」（用户组免验证码弹窗）。
   *  优先在弹窗容器里找，词表覆盖两种页面。 */
  function findConfirmAny() {
    const WORDS = ['确定提交', '编辑资料', '确认提交', '确定', '确认', '提交'];
    const DIALOG_SEL = '.layui-layer, .modal, [role="dialog"], .ui-dialog, .dialog, .popup, .el-dialog';
    const vis = (el) => { const r = el.getBoundingClientRect(); return r.width > 4 && r.height > 4; };

    const pick = (root) => {
      const els = [...root.querySelectorAll('button,a,div,span,li')]
        .map((el) => ({ el, r: el.getBoundingClientRect(), txt: (el.innerText || '').replace(/\s/g, '') }))
        .filter((x) => x.r.width > 4 && x.r.height > 4 && x.txt.length <= 8 && WORDS.indexOf(x.txt) >= 0);
      els.sort((a, b) => a.r.width * a.r.height - b.r.width * b.r.height);
      return els.length ? els[0].el : null;
    };

    // 1) 弹窗容器内
    const dialogs = [...document.querySelectorAll(DIALOG_SEL)].filter(vis);
    for (const d of dialogs) {
      const hit = pick(d);
      if (hit) return hit;
    }
    // 2) 全页兜底
    const hit = pick(document);
    if (hit) return hit;
    // 3) 旧接口
    return findConfirm();
  }

  /** 按「标签文字」找对应的输入框：先看属性，再找文本节点向上 4 层。 */
  function findByLabel(keyword) {
    const els = [...document.querySelectorAll('textarea, input[type=text], input:not([type])')];
    const byAttr = els.find((el) => {
      const s = (el.id || '') + ' ' + (el.name || '') + ' ' + (el.placeholder || '');
      return s.indexOf(keyword) >= 0;
    });
    if (byAttr) return { el: byAttr, how: '属性' };

    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (!node.nodeValue || node.nodeValue.indexOf(keyword) < 0) continue;
      let parent = node.parentElement;
      for (let i = 0; i < 4 && parent; i++, parent = parent.parentElement) {
        const el = parent.querySelector('textarea, input[type=text], input:not([type])');
        if (el) return { el, how: '标签文字' };
      }
    }
    return null;
  }

  /** 填「改动附言（给审核看）」与「改动说明（给所有人看）」，返回命中情况。 */
  function fillEditMeta(item) {
    const hits = [];
    if (item.editRemark) {
      const r = findByLabel('改动附言');
      if (r && setVal(r.el, item.editRemark)) hits.push('改动附言(' + r.how + ')');
      else hits.push('改动附言未命中');
    }
    if (item.editNote) {
      const r = findByLabel('改动说明');
      if (r && setVal(r.el, item.editNote)) hits.push('改动说明(' + r.how + ')');
      else hits.push('改动说明未命中');
    }
    return hits;
  }

  async function applyEdit(item) {
    // 只写计划里出现的字段；没出现的保持页面原值（编辑是覆盖式，不能瞎填）
    if (item.regname !== undefined) setVal(qm('regname'), item.regname);
    if (item.ename !== undefined) setVal(qm('ename'), item.ename);
    if (item.remark !== undefined) setVal(qm('remark'), item.remark);
    if (item.maxstack !== undefined) setVal(qm('maxstack'), item.maxstack);
    if (item.damage !== undefined) setVal(qm('damage'), item.damage);
    if (item.icon32) {
      setVal(q('#icon-32x-editor'), item.icon32);
      setVal(q('#icon-32x'), item.icon32);
      await sleep(500);
    }
    if (item.icon128) {
      setVal(q('#icon-128x-editor'), item.icon128);
      setVal(q('#icon-128x'), item.icon128);
      await sleep(400);
    }
    let editorPath = null;
    if (item.html) {
      editorPath = setEditorHtml(item.html);
      if (!editorPath) throw new Error('没找到正文编辑器（CodeMirror / UEditor 都没命中）');
    }
    // 覆盖前先存档旧正文，供回滚与 AI 对比
    try {
      const before = getEditorHtml();
      if (before.path) {
        plan.backup = plan.backup || [];
        plan.backup.push({ id: item.id, name: item.name, path: before.path, oldHtml: before.html });
        saveEditPlan(plan);
      }
    } catch (e) { /* 存档失败不影响主流程 */ }

    const metaHits = fillEditMeta(item);
    await sleep(400);
    return (editorPath || '未改正文') + (metaHits.length ? '，' + metaHits.join('、') : '');
  }

  function initEditPanel(itemId) {
    if (document.getElementById('mb-edit-panel')) return;

    const st = document.createElement('style');
    st.textContent = [
      '#mb-edit-panel{position:fixed !important;right:18px !important;bottom:24px !important;',
      'z-index:2147483647 !important;width:400px !important;pointer-events:auto !important;',
      'background:#ffffff !important;color:#111827 !important;border:2px solid #2563eb !important;',
      'border-radius:10px !important;box-shadow:0 10px 30px rgba(0,0,0,.35) !important;',
      'font-size:13.5px !important;font-family:"Microsoft YaHei",sans-serif !important;overflow:hidden !important;}',
      '#mb-edit-panel .mb-hd{padding:9px 12px !important;background:#2563eb !important;',
      'color:#ffffff !important;font-weight:700 !important;font-size:14px !important;}',
      '#mb-edit-panel .mb-bd{padding:10px 12px !important;background:#ffffff !important;color:#111827 !important;}',
      '#mb-edit-panel #mb-edit-info{color:#111827 !important;font-size:13.5px !important;}',
      '#mb-edit-panel button{margin:3px 6px 3px 0 !important;padding:6px 12px !important;',
      'border-radius:6px !important;border:1px solid #1d4ed8 !important;background:#2563eb !important;',
      'color:#ffffff !important;font-size:13px !important;font-weight:600 !important;cursor:pointer !important;}',
      '#mb-edit-panel button:hover{background:#1d4ed8 !important;}',
      '#mb-edit-panel pre{margin:8px 0 0 !important;padding:8px !important;background:#f3f4f6 !important;',
      'color:#111827 !important;border:1px solid #d1d5db !important;border-radius:6px !important;',
      'max-height:26vh !important;overflow:auto !important;font-size:12px !important;white-space:pre-wrap !important;}',
    ].join('');
    document.head.appendChild(st);

    const panel = document.createElement('div');
    panel.id = 'mb-edit-panel';
    panel.innerHTML = '<div class="mb-hd">批量编辑 · v' + MB_VERSION + '</div><div class="mb-bd">' +
      '<div id="mb-edit-info">无队列</div>' +
      '<div style="margin:8px 0">' +
      '<button id="mb-edit-run">执行本页编辑</button>' +
      '<button id="mb-edit-skip">跳过本条</button>' +
      '<button id="mb-edit-diag">诊断</button>' +
      '<button id="mb-edit-pause">暂停自动</button>' +
      '<button id="mb-edit-import">导入 JSON…</button>' +
      '<input type="file" id="mb-edit-file" accept=".json" style="display:none">' +
      '<button id="mb-edit-clear">清空队列</button>' +
      '</div><pre id="mb-edit-out"></pre></div>';
    document.body.appendChild(panel);
    raiseToTopLayer(panel);
    makeCollapsible(panel, '.mb-hd', '.mb-bd', 'edit');

    const info = (s) => { document.getElementById('mb-edit-info').textContent = s; };
    const out = (s) => { document.getElementById('mb-edit-out').textContent = s; };

    const plan = loadEditPlan();
    const noQueue = !plan || !plan.items || !plan.items[plan.index];
    if (noQueue) {
      info('没有待编辑队列（先从列表页点「批量编辑」）；诊断按钮仍可用');
    }
    const item = noQueue ? null : plan.items[plan.index];
    info('第 ' + (plan.index + 1) + '/' + plan.items.length + ' 条：' + (item.name || item.id) +
         '（资料 id ' + item.id + '，当前页 ' + itemId + '）');
    out('将写入的字段：' + Object.keys(item).filter((k) => ['id', 'name'].indexOf(k) < 0).join(', '));

    function advance() {
      plan.index += 1;
      saveEditPlan(plan);
      if (plan.index >= plan.items.length) {
        if (plan.backup && plan.backup.length) {
          const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
          downloadJson({ classId: plan.classId, typeId: plan.typeId, items: plan.backup },
                       'mcmod-原文备份-' + stamp + '.json');
          info('队列完成，共 ' + plan.items.length + ' 条；旧正文备份已下载');
        } else {
          info('队列完成，共 ' + plan.items.length + ' 条（无旧正文备份）');
        }
        clearEditPlan();
        setTimeout(() => { location.href = '/item/list/' + (plan.classId || '31864') + '-' + (plan.typeId || '1') + '.html'; }, 1200);
        return;
      }
      const nxt = plan.items[plan.index];
      setTimeout(() => { location.href = urlOfTask(nxt, plan.classId); }, 900);
    }

    async function doRun() {
      try {
        if (noQueue) { info('没有待编辑队列：请先在列表页点「批量编辑」载入计划'); return; }
        info('正在填写…');
        const path = await applyEdit(item);
        info('正文已写入（' + (path || '未改正文') + '），正在提交…');
        const btn = findSubmitButton();
        if (!btn) { plan.paused = true; saveEditPlan(plan); info('找不到提交按钮，已暂停自动'); return; }
        btn.click();
        await sleep(2600);
        const ok = findConfirmAny();
        if (!ok) { plan.paused = true; saveEditPlan(plan); info('没等到确认按钮（已找：弹窗内「确定提交/编辑资料/确定/确认」），已暂停自动'); return; }
        ok.click();
        info('已点确认「' + (ok.innerText || '').trim().slice(0, 8) + '」，等待跳转下一条…');
        await sleep(2600);
        advance();
      } catch (err) {
        plan.paused = true;
        saveEditPlan(plan);
        info('执行失败：' + err.message + '（已暂停自动）');
        console.error('[批量工具] 编辑执行失败', err);
      }
    }

    document.getElementById('mb-edit-run').addEventListener('click', doRun);

    // 编辑页直接导入单条 JSON：读入后以当前资料为准建立 1 条队列并刷新
    document.getElementById('mb-edit-import').addEventListener('click', () => {
      document.getElementById('mb-edit-file').click();
    });
    document.getElementById('mb-edit-file').addEventListener('change', (e) => {
      const f = e.target.files && e.target.files[0];
      if (!f) return;
      const rd = new FileReader();
      rd.onload = () => {
        try {
          const raw = JSON.parse(rd.result);
          const list = raw.items || raw;
          const arr = Array.isArray(list) ? list : [list];
          if (!arr.length) return info('JSON 里没有条目');
          // 优先取与当前页面 id 相同的那条；没有就取第一条
          const cur = arr.find((x) => String(x.id) === String(itemId)) || arr[0];
          saveEditPlan({ classId: (raw.classId || '31864'), typeId: (raw.typeId || '1'),
                         items: [Object.assign({}, cur, { id: Number(cur.id || itemId) })],
                         index: 0, autoRun: false, paused: false });
          info('已载入「' + (cur.name || cur.id) + '」，页面即将刷新以应用…');
          setTimeout(() => location.reload(), 800);
        } catch (err) {
          info('导入失败：' + err.message);
          console.error('[批量工具] 导入 JSON 失败', err);
        }
      };
      rd.readAsText(f, 'utf-8');
    });

    document.getElementById('mb-edit-pause').addEventListener('click', () => {
      if (!plan) return;
      plan.paused = true;
      saveEditPlan(plan);
      info('自动执行已暂停（仍可手动点「执行本页编辑」）');
    });

    // 自动执行：队列里带 autoRun 时，到此页自动填写→提交→跳下一条
    if (!noQueue && plan.autoRun && !plan.paused) {
      info('自动执行中：第 ' + (plan.index + 1) + '/' + plan.items.length + ' 条 ' +
           (item.name || item.id) + '，1.5 秒后自动提交…');
      setTimeout(doRun, 1500);
    }

    // 鼠标被页面遮罩挡住时的后备：Alt+Q 执行、Alt+D 诊断、Alt+S 跳过
    if (!window.__mbEditHotkeys) {
      window.__mbEditHotkeys = true;
      document.addEventListener('keydown', (ev) => {
        if (!ev.altKey || ev.ctrlKey || ev.metaKey) return;
        const k = (ev.key || '').toLowerCase();
        const hit = { q: 'mb-edit-run', d: 'mb-edit-diag', s: 'mb-edit-skip' }[k];
        if (!hit) return;
        const btn = document.getElementById(hit);
        if (btn) { ev.preventDefault(); btn.click(); }
      });
    }

    document.getElementById('mb-edit-diag').addEventListener('click', () => {
      const lines = [];
      lines.push('location: ' + location.href);
      lines.push('iframe 数: ' + document.querySelectorAll('iframe').length);
      lines.push('CodeMirror: ' + !!document.querySelector('.CodeMirror'));
      lines.push('#ueditor_0: ' + !!document.querySelector('#ueditor_0'));
      const tas = [...document.querySelectorAll('textarea')].map((t) => (t.id || '-') + '|' + ((t.className || '') + '').slice(0, 24));
      lines.push('textarea(' + tas.length + '): ' + (tas.join(' ; ') || '无'));
      lines.push('contenteditable: ' + document.querySelectorAll('[contenteditable=true]').length);
      const btnWords = /提交|确定|完成|保存|确认|发布/;
      const btns = [...document.querySelectorAll('button,a,div,span')]
        .filter((e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; })
        .map((e) => ({ t: (e.innerText || '').trim().slice(0, 14), id: e.id || '', c: ((e.className || '') + '').slice(0, 20) }))
        .filter((x) => btnWords.test(x.t));
      lines.push('按钮候选(' + btns.length + '):');
      btns.slice(0, 8).forEach((b) => lines.push('  「' + b.t + '」id=' + (b.id || '-') + ' cls=' + (b.c || '-')));
      ['改动附言', '改动说明'].forEach((kw) => {
        const r = findByLabel(kw);
        lines.push(kw + '定位: ' + (r ? ('命中 ' + (r.el.tagName + '#' + (r.el.id || '-') + '.' + ((r.el.className || '') + '').slice(0, 16)) + ' [' + r.how + ']') : '未命中'));
      });
      const done = findSubmitButton();
      lines.push('findSubmitButton: ' + (done
        ? ('命中 ' + done.tagName + ' cls=' + (((done.className || '') + '').slice(0, 18)) + ' 「' + (done.innerText || '').trim().slice(0, 12) + '」')
        : '未命中'));
      out(lines.join('\n'));
      console.log('[批量工具][诊断]\n' + lines.join('\n'));
      info('诊断结果已输出到下方');
    });

    document.getElementById('mb-edit-skip').addEventListener('click', () => {
      if (noQueue) { info('没有待编辑队列，无可跳过'); return; }
      info('跳过本条'); advance();
    });
    document.getElementById('mb-edit-clear').addEventListener('click', () => { clearEditPlan(); info('队列已清空'); });
  }


  // ================= 审核列表（/verify*）：读取与撤回 =================

  function parseVerifyRows() {
    // 实测结构（2026-10）：
    // <tr>
    //   <td><a href="//center.mcmod.cn/…">昵称</a></td>
    //   <td><i class="fa fa-edit"> / fa-plus  <a href="/class/31864.html">模组</a> 中的
    //       <a href="/item/1025008.html">死之核心</a> 物品/方块。</td>
    //   <td>创建时间</td>
    //   <td><p class="text-muted">已撤回/已退回/已通过/审核中</p>…</td>
    // </tr>
    const scope = document.querySelector('.verify-list-list') || document.body;
    const trs = [...scope.querySelectorAll('tr')]
      .filter((tr) => tr.querySelector('a[href*="/item/"]') || tr.querySelector('a[href*="/item/add/"]'));

    const STATUS = /已撤回|已退回|审核中|已通过|待审核|已取消/;
    const KINDS = ['物品/方块', 'BUFF/DEBUFF', '生物/实体', '世界/维度', '绑定热键',
                   '游戏设定', '多方块结构', '自然生成', '附魔/魔咒', '群系/群落'];

    return trs.map((tr, index) => {
      const txt = (tr.innerText || '').replace(/\n+/g, ' | ');
      const tds = [...tr.querySelectorAll('td')];

      // 动作链接（再编辑/新提交/撤回…）不是资料链接，要排除
      const ACTION_WORDS = ['再编辑', '新提交', '撤回', '查看', '编辑', '提交'];
      const anchors = [...tr.querySelectorAll('a[href]')].filter((a) => {
        const txt = (a.innerText || '').trim();
        return ACTION_WORDS.indexOf(txt) < 0;
      });
      // 名称优先用详情页链接（/item/<id>.html）的文字；没有再用 add/edit 链接
      const detailA = anchors.find((a) => /\/item\/\d+\.html/.test(a.getAttribute('href') || ''));
      const itemA = detailA || anchors.find((a) => /\/item\/(add|edit)\/\d+/.test(a.getAttribute('href') || ''));
      const href = itemA ? (itemA.getAttribute('href') || '') : '';
      let id = null, verifyId = null;
      let mm = href.match(/\/item\/(add|edit)\/(\d+)(?:-(\d+))?/);
      if (mm) {
        id = Number(mm[2]);
        verifyId = mm[3] ? Number(mm[3]) : null;
      } else {
        mm = href.match(/\/item\/(\d+)\.html/);
        if (mm) id = Number(mm[1]);
      }

      // 类型：靠操作前的图标 class（fa-edit=编辑，fa-plus=新增）
      let kind = '';
      if (tr.querySelector('.fa-edit')) kind = '编辑';
      else if (tr.querySelector('.fa-plus')) kind = '新增';
      else if (/新增/.test(txt)) kind = '新增';
      else if (/编辑/.test(txt)) kind = '编辑';

      // 名称 = 资料链接自己的文字（优先详情页链接）
      const nameA = detailA || itemA;
      let name = nameA ? (nameA.innerText || '').trim() : '';
      if (!name) {
        // 新增类没有详情链接，名称只出现在「中添加 XXX 类型。」这句里
        const km = txt.match(/中添加\s*([^。|]{1,40}?)\s*(物品\/方块|BUFF\/DEBUFF|生物\/实体|世界\/维度|绑定热键|游戏设定|多方块结构|自然生成|附魔\/魔咒|群系\/群落)/);
        if (km) name = km[1].trim();
      }
      if (!name) {
        const km2 = txt.match(/中的\s*([^。|]{1,40}?)\s*(物品\/方块|BUFF\/DEBUFF|生物\/实体|世界\/维度|绑定热键|游戏设定|多方块结构|自然生成|附魔\/魔咒|群系\/群落)/);
        if (km2) name = km2[1].trim();
      }

      // 状态：优先最后一列，其次全行
      const statusCell = tds.length ? tds[tds.length - 1].innerText : '';
      const sMatch = (statusCell.match(STATUS) || txt.match(STATUS));
      const status = sMatch ? sMatch[0] : '';

      const kindLabel = KINDS.find((k) => txt.indexOf(k) >= 0) || '';
      const timeCell = tds[2] ? (tds[2].innerText || '').trim() : '';

      // 审核项 id：行内若有 /verify/<vid> 之类的链接或 data 属性就取
      if (!verifyId) {
        const vm = tr.innerHTML.match(/\/verify\/(\d+)/) || tr.innerHTML.match(/verify[_-]?id["'=:>\s]+(\d+)/i);
        if (vm) verifyId = Number(vm[1]);
      }

      const pickAction = (word) => [...tr.querySelectorAll('a,button,span,div')]
        .find((x) => (x.innerText || '').trim() === word);
      const retireEl = pickAction('撤回');
      const againEl = pickAction('再编辑') || pickAction('编辑');
      // 「再编辑」通常是 <a>，其 href 就是官方目标页（新增走 /item/add/<classId>-<vid>/）
      const againAnchor = againEl
        ? (againEl.tagName === 'A' ? againEl : (againEl.closest && againEl.closest('a')))
        : null;
      const againHref = againAnchor ? (againAnchor.getAttribute('href') || '') : '';
      if (againHref) {
        const vm2 = againHref.match(/\/item\/(?:add|edit)\/\d+-(\d+)/);
        if (vm2 && !verifyId) verifyId = Number(vm2[1]);
      }

      return {
        index: index + 1, kind, id, verifyId, status, name, kindLabel,
        time: timeCell.replace(/\s+/g, ' ').slice(0, 30),
        hasRetire: !!retireEl,
        hasAgain: !!againEl, againHref,
        _tr: tr, _again: againEl || null, _retire: retireEl || null,
        raw: txt.slice(0, 160),
      };
    });
  }

  function initVerifyPanel() {
    if (document.getElementById('mb-verify-panel')) return;
    const st = document.createElement('style');
    st.textContent = [
      '#mb-verify-panel{position:fixed !important;right:18px !important;top:96px !important;z-index:2147483647 !important;',
      'width:460px !important;background:#ffffff !important;color:#111827 !important;border:2px solid #2563eb !important;',
      'border-radius:10px !important;box-shadow:0 10px 30px rgba(0,0,0,.35) !important;font-size:13.5px !important;',
      'font-family:"Microsoft YaHei",sans-serif !important;pointer-events:auto !important;overflow:hidden !important;}',
      '#mb-verify-panel .mb-hd{padding:9px 12px !important;background:#2563eb !important;color:#fff !important;font-weight:700 !important;}',
      '#mb-verify-panel .mb-bd{padding:10px 12px !important;max-height:64vh !important;overflow:auto !important;}',
      '#mb-verify-panel button{margin:3px 6px 3px 0 !important;padding:6px 12px !important;border-radius:6px !important;',
      'border:1px solid #1d4ed8 !important;background:#2563eb !important;color:#fff !important;font-weight:600 !important;cursor:pointer !important;}',
      '#mb-verify-panel pre{margin:8px 0 0 !important;padding:8px !important;background:#f3f4f6 !important;color:#111827 !important;',
      'border:1px solid #d1d5db !important;border-radius:6px !important;max-height:30vh !important;overflow:auto !important;',
      'font-size:12px !important;white-space:pre-wrap !important;}',
    ].join('');
    document.head.appendChild(st);

    const panel = document.createElement('div');
    panel.id = 'mb-verify-panel';
    panel.innerHTML = '<div class="mb-hd">审核列表工具 · v' + MB_VERSION + '</div><div class="mb-bd">' +
      '<div id="mb-verify-info">未读取</div>' +
      '<div style="margin:8px 0">' +
      '<button id="mb-verify-read">读取审核列表</button>' +
      '<button id="mb-verify-dl">导出 JSON</button>' +
      '<button id="mb-verify-diag">诊断</button>' +
      '<button id="mb-verify-batchretire" style="background:#b91c1c !important;border-color:#991b1b !important">批量撤回</button>' +
      '<button id="mb-verify-batchagain">批量打开编辑页</button>' +
      '<button id="mb-verify-plan" style="background:#0ea5e9 !important;border-color:#0284c7 !important">导入计划并自动再编辑</button>' +
      '<input type="file" id="mb-verify-planfile" accept=".json" style="display:none">' +
      '<label style="display:inline-block;margin-left:6px;font-size:13px !important;color:#111827 !important;">' +
      '<input type="checkbox" id="mb-verify-all" style="vertical-align:-2px;margin-right:4px;">全选</label>' +
      '<label style="display:inline-block;margin-left:6px;font-size:13px !important;color:#111827 !important;">' +
      '<input type="checkbox" id="mb-verify-onlyrej" checked style="vertical-align:-2px;margin-right:4px;">只看已退回/审核中</label>' +
      '</div><div id="mb-verify-rows"></div><pre id="mb-verify-out"></pre></div>';
    document.body.appendChild(panel);
    raiseToTopLayer(panel);
    makeCollapsible(panel, '.mb-hd', '.mb-bd', 'verify');

    const info = (s) => { document.getElementById('mb-verify-info').textContent = s; };
    const out = (s) => { document.getElementById('mb-verify-out').textContent = s; };
    let rows = [];

    function renderRows() {
      const box = document.getElementById('mb-verify-rows');
      const onlyRej = document.getElementById('mb-verify-onlyrej').checked;
      const list = onlyRej
        ? rows.filter((r) => r.status === '已退回' || r.status === '审核中')
        : rows;
      if (!list.length) { box.innerHTML = '<div style="color:#6b7280">（没有符合条件的条目）</div>'; return; }
      box.innerHTML = list.map((r) => {
        const color = r.status === '已退回' ? '#b91c1c' : (r.status === '审核中' ? '#b45309' : '#15803d');
        return '<div class="mb-vrow" data-i="' + r.index + '" style="display:flex;align-items:center;gap:6px;' +
          'padding:4px 0;border-bottom:1px solid #eee;font-size:12.5px">' +
          '<input type="checkbox" class="mb-vsel" data-i="' + r.index + '" style="margin:0;vertical-align:middle">' +
          '<span style="color:' + color + ';min-width:44px">' + (r.status || '?') + '</span>' +
          '<span style="color:#6b7280;min-width:30px">' + r.kind + '</span>' +
          '<span style="flex:1;color:#111827">' + (r.name || ('#' + r.id)) + '</span>' +
          '<button data-act="again" data-i="' + r.index + '" style="padding:3px 8px !important;font-size:12px !important">再编辑</button>' +
          (r.hasRetire ? '<button data-act="retire" data-i="' + r.index + '" style="padding:3px 8px !important;font-size:12px !important;background:#b91c1c !important;border-color:#991b1b !important">撤回</button>' : '') +
          '</div>';
      }).join('');
      box.querySelectorAll('button[data-act]').forEach((btn) => {
        btn.addEventListener('click', () => {
          const r = rows.find((x) => String(x.index) === btn.getAttribute('data-i'));
          if (!r) return;
          if (btn.getAttribute('data-act') === 'again') {
            // 优先用页面自带的「再编辑」入口，退化为直接打开编辑页
            if (r._again) { r._again.click(); info('已点击「再编辑」：' + (r.name || r.id)); }
            else if (r.id) { location.href = '/item/edit/' + r.id + '/'; }
          } else {
            if (!confirm('确认撤回「' + (r.name || r.id) + '」？撤回后需重新提交。')) return;
            if (r._retire) { r._retire.click(); info('已点击「撤回」：' + (r.name || r.id)); }
          }
        });
      });
    }

    document.getElementById('mb-verify-read').addEventListener('click', () => {
      rows = parseVerifyRows();
      const byStatus = {};
      rows.forEach((r) => { byStatus[r.status || '未知'] = (byStatus[r.status || '未知'] || 0) + 1; });
      info('读到 ' + rows.length + ' 条：' + JSON.stringify(byStatus));
      renderRows();
      out('');
    });

    document.getElementById('mb-verify-onlyrej').addEventListener('change', renderRows);

    document.getElementById('mb-verify-all').addEventListener('change', (e) => {
      document.querySelectorAll('.mb-vsel').forEach((c) => { c.checked = e.target.checked; });
    });

    function selectedRows() {
      const ids = [...document.querySelectorAll('.mb-vsel:checked')].map((c) => c.getAttribute('data-i'));
      return rows.filter((r) => ids.indexOf(String(r.index)) >= 0);
    }

    document.getElementById('mb-verify-batchretire').addEventListener('click', async () => {
      const sel = selectedRows().filter((r) => r._retire);
      if (!sel.length) return info('没有选中「可撤回」的条目（先勾选左侧方框）');
      if (!confirm('确认批量撤回 ' + sel.length + ' 条？\n' + sel.map((r) => '· ' + (r.name || r.id)).join('\n'))) return;
      for (let i = 0; i < sel.length; i += 1) {
        info('撤回 ' + (i + 1) + '/' + sel.length + '：' + (sel[i].name || sel[i].id));
        sel[i]._retire.click();
        await sleep(1200);
      }
      info('已提交撤回 ' + sel.length + ' 条，页面即将刷新');
      setTimeout(() => location.reload(), 1500);
    });

    document.getElementById('mb-verify-plan').addEventListener('click', () => {
      document.getElementById('mb-verify-planfile').click();
    });

    document.getElementById('mb-verify-planfile').addEventListener('change', (e) => {
      const f = e.target.files && e.target.files[0];
      if (!f) return;
      const rd = new FileReader();
      rd.onload = () => {
        try {
          const raw = JSON.parse(rd.result);
          const planItems = raw.items || raw;
          if (!Array.isArray(planItems) || !planItems.length) return info('计划里没有 items');
          if (!rows.length) rows = parseVerifyRows();

          const queue = [];
          const missed = [];
          planItems.forEach((it) => {
            const norm = (s) => String(s || '').replace(/\s+/g, '');
            const nm = norm(it.name);
            const row = rows.find((r) => {
              const rn = norm(r.name);
              if (it.id && /^\d+$/.test(String(it.id)) && String(r.id) === String(it.id) && (!nm || rn === nm)) return true;
              if (!nm || !rn) return false;
              return rn === nm || rn.indexOf(nm) >= 0 || nm.indexOf(rn) >= 0;
            });
            if (!row) { missed.push(it.name || it.id); return; }
            queue.push(Object.assign({}, it, {
              id: row.id,
              kind: row.kind,
              verifyId: row.verifyId,
              targetUrl: row.againHref || '',
            }));
          });
          if (!queue.length) return info('没有匹配到审核列表里的条目：' + missed.join('、'));

          // 逐条算出落地页（新增走 /item/add/<classId>-<verifyId>/）
          const classId = (raw.classId || (location.search.match(/classid=(\d+)/) || [])[1] || '31864');
          queue.forEach((q) => {
            if (!q.targetUrl && q.kind === '新增' && !q.verifyId) {
              q._skipReason = '该行没取到「再编辑」链接或审核项 id，无法定位新增页';
            }
          });

          saveEditPlan({ classId, typeId: raw.typeId || '1', items: queue, index: 0,
                         autoRun: true, paused: false });
          info('已匹配 ' + queue.length + ' 条' + (missed.length ? '，未匹配 ' + missed.length + ' 条' : '') +
               '；开始自动再编辑…');
          const first = queue[0];
          const url = first._skipReason ? '' : urlOfTask(first, classId);
          if (!url) return info('第一条无法定位：' + (first._skipReason || '缺少 id'));
          setTimeout(() => { location.href = url; }, 700);
        } catch (err) {
          info('导入失败：' + err.message);
          console.error('[批量工具] 审核列表导入计划失败', err);
        }
      };
      rd.readAsText(f, 'utf-8');
    });

    document.getElementById('mb-verify-batchagain').addEventListener('click', () => {
      const sel = selectedRows().filter((r) => r.id);
      if (!sel.length) return info('没有选中条目');
      info('打开 ' + sel.length + ' 个编辑页…');
      sel.slice(0, 12).forEach((r, i) => {
        setTimeout(() => window.open('/item/edit/' + r.id + '/', '_blank'), i * 400);
      });
      if (sel.length > 12) info('只打开了前 12 个（共 ' + sel.length + ' 条）');
    });

    document.getElementById('mb-verify-dl').addEventListener('click', () => {
      if (!rows.length) rows = parseVerifyRows();
      const clean = rows.map((r) => {
        const o = Object.assign({}, r);
        delete o._tr; delete o._again; delete o._retire;
        return o;
      });
      downloadJson({ total: clean.length, rows: clean }, 'mcmod-审核列表-' +
        new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19) + '.json');
      info('已导出 ' + rows.length + ' 条');
    });

    document.getElementById('mb-verify-diag').addEventListener('click', () => {
      const scope = document.querySelector('.verify-list-list') || document.body;
      const trs = [...scope.querySelectorAll('tr')];
      const lines = ['容器: ' + (scope.className || scope.tagName)];
      lines.push('tr 总数: ' + trs.length + '，其中含资料链接的 tr: ' +
        trs.filter((tr) => tr.querySelector('a[href*="/item/"]')).length);
      lines.push('swiper-slide: ' + scope.querySelectorAll('.swiper-slide').length);
      const allLinks = [...scope.querySelectorAll('a[href]')]
        .filter((a) => /\/item\/(add|edit)\//.test(a.getAttribute('href') || ''));
      lines.push('资料链接数: ' + allLinks.length + '（去重后 ' +
        new Set(allLinks.map((a) => (a.getAttribute('href') || ''))).size + '）');
      const firstTr = trs.find((tr) => tr.querySelector('a[href*="/item/"]'));
      if (firstTr) lines.push('首个数据行 outerHTML(前 700):\n' + firstTr.outerHTML.slice(0, 700));
      lines.push('撤回元素数: ' + [...scope.querySelectorAll('a,button,span')].filter((x) => /撤回/.test((x.innerText || '').trim())).length);
      out(lines.join('\n'));
      console.log('[批量工具][审核列表诊断]\n' + lines.join('\n'));
    });
  }


  // ================= 新增页：队列执行端（退回条目重交，URL 形如 /item/add/31864-809903/） =================

  function initAddQueueRunner(verifyId) {
    if (document.getElementById('mb-addq-panel')) return;
    const plan = loadEditPlan();
    if (!plan || !plan.items || !plan.items[plan.index]) return;
    const item = plan.items[plan.index];

    const st = document.createElement('style');
    st.textContent = [
      '#mb-addq-panel{position:fixed !important;right:18px !important;bottom:24px !important;z-index:2147483647 !important;',
      'width:380px !important;background:#fff !important;color:#111827 !important;border:2px solid #0ea5e9 !important;',
      'border-radius:10px !important;box-shadow:0 10px 30px rgba(0,0,0,.35) !important;font-size:13.5px !important;',
      'font-family:"Microsoft YaHei",sans-serif !important;pointer-events:auto !important;overflow:hidden !important;}',
      '#mb-addq-panel .hd{padding:9px 12px !important;background:#0ea5e9 !important;color:#fff !important;font-weight:700 !important;}',
      '#mb-addq-panel .bd{padding:10px 12px !important;}',
      '#mb-addq-panel button{margin:3px 6px 3px 0 !important;padding:6px 12px !important;border-radius:6px !important;',
      'border:1px solid #0284c7 !important;background:#0ea5e9 !important;color:#fff !important;font-weight:600 !important;cursor:pointer !important;}',
      '#mb-addq-panel pre{margin:8px 0 0 !important;padding:8px !important;background:#f3f4f6 !important;color:#111827 !important;',
      'border:1px solid #d1d5db !important;border-radius:6px !important;max-height:22vh !important;overflow:auto !important;',
      'font-size:12px !important;white-space:pre-wrap !important;}',
    ].join('');
    document.head.appendChild(st);

    const panel = document.createElement('div');
    panel.id = 'mb-addq-panel';
    panel.innerHTML = '<div class="hd">新增页队列 · v' + MB_VERSION + '</div><div class="bd">' +
      '<div id="mb-addq-info"></div>' +
      '<div style="margin:8px 0"><button id="mb-addq-run">执行本条</button>' +
      '<button id="mb-addq-skip">跳过</button><button id="mb-addq-clear">清空队列</button></div>' +
      '<pre id="mb-addq-out"></pre></div>';
    document.body.appendChild(panel);
    raiseToTopLayer(panel);
    makeCollapsible(panel, '.hd', '.bd', 'addq');

    const info = (s) => { document.getElementById('mb-addq-info').textContent = s; };
    const out = (s) => { document.getElementById('mb-addq-out').textContent = s; };

    info('第 ' + (plan.index + 1) + '/' + plan.items.length + ' 条：' + (item.name || item.regname || item.id) +
         '（审核项 ' + verifyId + '）');
    out('将写入的字段：' + Object.keys(item).filter((k) => ['id', 'kind', 'verifyId', 'targetUrl', '_tr'].indexOf(k) < 0).join(', '));

    function advanceAdd() {
      plan.index += 1;
      saveEditPlan(plan);
      if (plan.index >= plan.items.length) {
        clearEditPlan();
        info('队列完成，共 ' + plan.items.length + ' 条');
        return;
      }
      const nxt = plan.items[plan.index];
      setTimeout(() => { location.href = urlOfTask(nxt, plan.classId); }, 900);
    }

    async function runOne() {
      try {
        info('正在填写…');
        const it = Object.assign({}, item);
        if (!it.remark && it.editRemark) it.remark = it.editRemark;   // 附言字段兼容
        await fillOne(it);
        info('已填写，正在提交…');
        const btn = findSubmitButton();
        if (!btn) { info('找不到提交按钮'); return; }
        btn.click();
        await sleep(2400);
        const ok = findConfirmAny();
        if (!ok) { info('点了提交但没等到确认按钮，请手动确认'); return; }
        ok.click();
        info('已提交，跳下一条…');
        await sleep(2400);
        advanceAdd();
      } catch (err) {
        info('执行失败：' + err.message);
        console.error('[批量工具] 新增页队列执行失败', err);
      }
    }

    document.getElementById('mb-addq-run').addEventListener('click', runOne);
    document.getElementById('mb-addq-skip').addEventListener('click', advanceAdd);
    document.getElementById('mb-addq-clear').addEventListener('click', () => { clearEditPlan(); info('队列已清空'); });

    if (plan.autoRun && !plan.paused) {
      info('自动执行中：第 ' + (plan.index + 1) + '/' + plan.items.length + ' 条，1.5 秒后提交…');
      setTimeout(runOne, 1500);
    }
  }

})();
