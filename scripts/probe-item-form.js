// probe-item-form.js —— 在百科「新增资料」页控制台里跑，探测表单字段名。
//
// 用途：站方随时可能加字段（例 2026-11-16 审核要求「耐久度」填到字段里而不是正文），
// 批量脚本靠 data-multi-id 定位。这个脚本把当前页面所有可填字段连同标签文本、类型打印出来，
// 顺便给出「根据标签猜字段名」的结果——核对后再改 mcmod-batch.user.js 的候选名列表。
//
// 用法：
//   1. 打开 https://www.mcmod.cn/item/add/<classId>/ ，先手动选好「资料类型」（否则分类下拉不在 DOM）
//   2. F12 → Console → 粘贴本文件全部内容 → 回车
//   3. 复制打印出的 JSON，贴回会话里（或直接对照改脚本）

(() => {
  const rows = [];

  // ① 官方 data-multi-* 字段
  document.querySelectorAll('[data-multi-id]').forEach((el) => {
    const id = el.getAttribute('data-multi-id');
    const box = el.closest('tr, li, .form-group, .mb-3') || el.parentElement;
    const label = box
      ? (box.querySelector('label, th, dt, strong')?.textContent || box.textContent || '').trim().slice(0, 40)
      : '';
    rows.push({
      kind: 'data-multi-id',
      key: id,
      label,
      tag: el.tagName.toLowerCase(),
      type: el.getAttribute('type') || '',
      limit: el.getAttribute('data-limit-type') || '',
      value: (el.value || '').slice(0, 30),
    });
  });

  // ② 普通输入框（没有 data-multi-id 的，例如图标、正文)
  document.querySelectorAll('input[type=text], input:not([type]), textarea, select').forEach((el) => {
    if (el.closest('.CodeMirror')) return;
    const box = el.closest('tr, li, .form-group, .mb-3') || el.parentElement;
    const label = box
      ? (box.querySelector('label, th, dt, strong')?.textContent || '').trim().slice(0, 40)
      : '';
    rows.push({
      kind: 'plain',
      key: el.name || el.id || '',
      label,
      tag: el.tagName.toLowerCase(),
      type: el.getAttribute('type') || '',
      value: (el.value || '').slice(0, 30),
    });
  });

  // ③ 按标签猜：耐久度在哪
  const guess = {};
  const marks = [...document.querySelectorAll('label, th, td, span, dt, strong')]
    .filter((e) => e.children.length === 0)
    .filter((e) => /耐久|堆叠|注册名|次要名称|元数据/.test(e.textContent || ''));
  marks.forEach((m) => {
    const box = m.closest('tr, li, .form-group, .mb-3') || m.parentElement;
    const el = box && box.querySelector('[data-multi-id], input[type=text], input:not([type])');
    const k = (m.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 12);
    guess[k] = el ? (el.getAttribute('data-multi-id') || el.name || el.id || '(无名)') : '(未找到输入框)';
  });

  console.log('%c[字段清单]', 'font-weight:bold', rows);
  console.table(rows);
  console.log('%c[标签→字段]', 'font-weight:bold', guess);
  console.log('JSON:', JSON.stringify({ rows, guess }, null, 1));
  return guess;
})();
