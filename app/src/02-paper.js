'use strict';

/* ============================================================
   Paper renderer + preview + print/PDF
   ============================================================ */

const SECTIONS = {
  mcq:    { title: 'বহুনির্বাচনী প্রশ্ন', hint: 'সঠিক উত্তরটি উত্তরপত্রে লেখো।' },
  fill:   { title: 'শূন্যস্থান পূরণ', hint: 'শূন্যস্থানে উপযুক্ত শব্দ বসাও।' },
  tf:     { title: 'শুদ্ধ/অশুদ্ধ নির্ণয়', hint: 'বাক্যটি শুদ্ধ হলে “শুদ্ধ”, অশুদ্ধ হলে “অশুদ্ধ” লেখো।' },
  match:  { title: 'বাম-ডান মিলকরণ', hint: 'বাম পাশের সাথে ডান পাশের সঠিক অংশ মিলাও।' },
  wrq_k:  { title: 'জ্ঞানমূলক প্রশ্ন', hint: 'সংক্ষেপে উত্তর দাও।' },
  wrq_kh: { title: 'অনুধাবনমূলক প্রশ্ন', hint: 'সংক্ষেপে ব্যাখ্যা করো।' },
  cq:     { title: 'সৃজনশীল প্রশ্ন', hint: 'উদ্দীপক পড়ে ক, খ, গ ও ঘ প্রশ্নের উত্তর দাও।' },
};

function marksSummary(items) {
  if (!items.length) return '';
  const marks = items.map((q) => Number(q.marks) || 0);
  const total = marks.reduce((a, b) => a + b, 0);
  return marks.every((m) => m === marks[0])
    ? `${bn(marks[0])} × ${bn(marks.length)} = ${bn(total)}`
    : `মোট ${bn(total)}`;
}

/* In preview edit mode these attributes mark the text the teacher can type over. */
function editAttr(editable, field, extra = '') {
  return editable ? ` data-edit="${field}"${extra}` : '';
}

function mcqOptionsHTML(q, editable) {
  const options = q.options || [];
  const longest = options.reduce((m, o) => Math.max(m, String(o).length), 0);
  const layout = longest > 34 ? 'one-col' : 'two-col';
  const body = options.map((o, i) =>
    `<div><span class="ol">${OPT[i]}.</span> <span${editAttr(editable, 'option', ` data-i="${i}"`)}>${esc(o)}</span></div>`).join('');
  return `<div class="opts ${layout}">${body}</div>`;
}

function cqBodyHTML(q, editable) {
  const subs = (q.subquestions || []).map((s, i) => `<div class="sub">
      <span class="sl">${esc(s.label)}.</span>
      <span class="st"${editAttr(editable, 'sub', ` data-i="${i}"`)}>${esc(s.text)}</span>
      <span class="sm">${bn(s.marks)}</span>
    </div>`).join('');
  const stim = q.stimulus
    ? `<div class="stim"><span class="lbl">উদ্দীপক:</span> <span${editAttr(editable, 'stimulus')}>${esc(q.stimulus)}</span></div>`
    : '';
  return `${stim}
    <div class="subs">${subs}</div>
    <div class="cqmarks">মোট নম্বর: ${bn(q.marks)}</div>`;
}

function matchBodyHTML(q, editable) {
  const left = (q.left || []).map((t, i) =>
    `<div class="mrow"><span class="ol">${MLAB[i] || i + 1}.</span> <span${editAttr(editable, 'left', ` data-i="${i}"`)}>${esc(t)}</span></div>`).join('');
  const right = (q.right || []).map((t, i) =>
    `<div class="mrow"><span class="ol">${bn(i + 1)}.</span> <span${editAttr(editable, 'right', ` data-i="${i}"`)}>${esc(t)}</span></div>`).join('');
  return `<div class="match"><div class="mcol">${left}</div><div class="mcol">${right}</div></div>`;
}

function tfAnswer(q) {
  return q.answer_text || (q.answer_bool === true ? 'শুদ্ধ' : q.answer_bool === false ? 'অশুদ্ধ' : '—');
}

function questionBodyHTML(q, editable) {
  const stem = `<span class="qt"${editAttr(editable, 'stem')}>${esc(q.stem)}</span>`;
  if (q.type === 'mcq') {
    return `<div class="qline">${stem}<span class="qm">${bn(q.marks)}</span></div>${mcqOptionsHTML(q, editable)}`;
  }
  if (q.type === 'cq') {
    return cqBodyHTML(q, editable);
  }
  if (q.type === 'tf') {
    return `<div class="qline">${stem}<span class="qm">${bn(q.marks)}</span></div>
      <div class="tf-choices"><span class="tf-box">শুদ্ধ</span><span class="tf-box">অশুদ্ধ</span></div>`;
  }
  if (q.type === 'match') {
    return `<div class="qline">${stem}<span class="qm">${bn(q.marks)}</span></div>${matchBodyHTML(q, editable)}`;
  }
  return `<div class="qline">${stem}<span class="qm">${bn(q.marks)}</span></div>`;
}

function questionLI(q, editable) {
  if (!editable) return `<li>${questionBodyHTML(q, false)}</li>`;
  return `<li class="pe-q" data-qid="${esc(q.id)}">
    <div class="pe-qb">
      <button class="pe-qedit" type="button" data-qid="${esc(q.id)}" title="প্রশ্ন সম্পাদনা">✎</button>
      <button class="pe-qdel" type="button" data-qid="${esc(q.id)}" title="প্রশ্নপত্র থেকে সরাও">✕</button>
    </div>
    ${questionBodyHTML(q, true)}
  </li>`;
}

function sectionHTML(key, items, editable, letter) {
  const s = SECTIONS[key];
  const body = items.map((q) => questionLI(q, editable)).join('');
  return `<section class="sec">
    <h2><span class="sl2">${letter || ''}</span> ${s.title}<span class="sum">${marksSummary(items)}</span></h2>
    <p class="hint">${s.hint}</p>
    <ol${key === 'cq' ? ' class="cqlist"' : ''}>${body}</ol>
  </section>`;
}

function mixedSectionHTML(items, editable) {
  const body = items.map((q) => questionLI(q, editable)).join('');
  return `<section class="sec">
    <h2>প্রশ্ন<span class="sum">মোট ${bn(items.reduce((s, q) => s + Number(q.marks || 0), 0))}</span></h2>
    <ol>${body}</ol>
  </section>`;
}

function answerKeyHTML(groups, editable) {
  const parts = ['<section class="key"><h2>উত্তরমালা</h2>'];

  if (groups.mcq.length) {
    const cells = groups.mcq.map((q, i) => {
      const idx = q.answer_index;
      const letter = idx >= 1 && idx <= 4 ? OPT[idx - 1] : '—';
      return `<div class="kc"><span>${bn(i + 1)}.</span> ${letter}</div>`;
    }).join('');
    parts.push(`<h3>বহুনির্বাচনী</h3><div class="kgrid">${cells}</div>`);
  }

  if (groups.fill.length) {
    const body = groups.fill.map((q, i) => `<li${editable ? ` data-qid="${esc(q.id)}"` : ''}><span class="kn">${bn(i + 1)}.</span> <span${editAttr(editable, 'answer')}>${esc(q.answer_text || '—')}</span></li>`).join('');
    parts.push(`<h3>শূন্যস্থান</h3><ol class="klist">${body}</ol>`);
  }

  if (groups.tf.length) {
    const body = groups.tf.map((q, i) => `<li${editable ? ` data-qid="${esc(q.id)}"` : ''}><span class="kn">${bn(i + 1)}.</span> <span${editAttr(editable, 'answer')}>${esc(tfAnswer(q))}</span></li>`).join('');
    parts.push(`<h3>শুদ্ধ/অশুদ্ধ</h3><ol class="klist">${body}</ol>`);
  }

  if (groups.match.length) {
    const body = groups.match.map((q, i) => `<li><span class="kn">${bn(i + 1)}.</span> ${esc(matchAnswerText(q) || '—')}</li>`).join('');
    parts.push(`<h3>বাম-ডান মিলকরণ</h3><ol class="klist">${body}</ol>`);
  }

  [['wrq_k', 'জ্ঞানমূলক'], ['wrq_kh', 'অনুধাবনমূলক']].forEach(([key, label]) => {
    const rows = groups[key];
    if (!rows.length) return;
    const body = rows.map((q, i) => `<li${editable ? ` data-qid="${esc(q.id)}"` : ''}><span class="kn">${bn(i + 1)}.</span> <span${editAttr(editable, 'answer')}>${esc(q.answer_text || '—')}</span></li>`).join('');
    parts.push(`<h3>${label}</h3><ol class="klist">${body}</ol>`);
  });

  if (groups.cq.length) {
    const body = groups.cq.map((q, i) => `<li${editable ? ` data-qid="${esc(q.id)}"` : ''}><span class="kn">${bn(i + 1)}.</span> <span${editAttr(editable, 'answer')}>${esc(q.answer_text || '—')}</span></li>`).join('');
    parts.push(`<h3>সৃজনশীল</h3><ol class="klist">${body}</ol>`);
  }

  parts.push('</section>');
  return parts.join('');
}

function renderPaper(items, settings, opts = {}) {
  const editable = !!opts.interactive;
  const cfg = { ...DEFAULT_SETTINGS, ...(settings || {}) };
  const ordered = cfg.group
    ? TYPE_ORDER.flatMap((t) => items.filter((q) => q.type === t))
    : items.slice();

  const groups = Object.fromEntries(TYPE_ORDER.map((t) => [t, ordered.filter((q) => q.type === t)]));
  const total = ordered.reduce((s, q) => s + Number(q.marks || 0), 0);

  let instructions = cfg.instructions;
  if (typeof instructions === 'string') instructions = instructions.split(/\r?\n/);
  if (!Array.isArray(instructions) || !instructions.filter((x) => String(x).trim()).length) {
    instructions = DEFAULT_SETTINGS.instructions;
  }
  instructions = instructions.filter((line) => String(line).trim());

  const meta = [
    ['subject', 'বিষয়', cfg.subject, true],
  ];
  if (cfg.date) meta.push(['date', 'তারিখ', cfg.date, true]);
  meta.push(['time', 'সময়', cfg.time, true], ['total', 'পূর্ণমান', bn(total), false]);

  const sections = cfg.group
    ? TYPE_ORDER.filter((t) => groups[t].length)
        .map((t, i) => sectionHTML(t, groups[t], editable, MLAB[i]))
        .join('')
    : mixedSectionHTML(ordered, editable);

  const key = cfg.answer_key !== false ? answerKeyHTML(groups, editable) : '';
  const source = (items[0] && items[0].source) || 'NCTB পাঠ্যপুস্তক';
  const headline = cfg.class_label || cfg.title || 'প্রশ্নপত্র';

  return `<div class="paper">
    <div class="head">
      ${cfg.institute ? `<div class="exam institute"${editAttr(editable, 'institute')}>${esc(cfg.institute)}</div>` : ''}
      ${cfg.exam_name ? `<div class="exam"${editAttr(editable, 'exam')}>${esc(cfg.exam_name)}</div>` : ''}
      <h1${editAttr(editable, 'class')}>${esc(headline)}</h1>
      <div class="meta">${meta.map(([field, label, value, canEdit]) => `<span>${esc(label)}: ${canEdit ? `<span${editAttr(editable, field)}>${esc(value)}</span>` : esc(value)}</span>`).join('')}</div>
    </div>
    <div class="instr">
      <div class="t">নির্দেশনা</div>
      <ol>${instructions.map((line, i) => `<li${editAttr(editable, 'instr', ` data-i="${i}"`)}>${esc(line)}</li>`).join('')}</ol>
    </div>
    ${sections}
    ${key}
    <div class="foot">উৎস: ${esc(source)} · প্রশ্নপত্র প্রস্তুতি: প্রশ্নপত্র স্টুডিও</div>
  </div>`;
}

/* ---------------- preview + paper view + in-place editing ---------------- */

let previewEditing = false;
let lineMode = false;

function paperContainers() {
  return [$('#paperViewBody'), $('#previewPaper')].filter(Boolean);
}

function renderInteractivePaper() {
  const items = cartItems();
  if (!items.length) return;
  const html = renderPaper(items, state.settings, { interactive: true });
  paperContainers().forEach((c) => { c.innerHTML = html; });
  applyPreviewEditing();
  applyLineMode();
}

const rerenderPreview = debounce(() => renderInteractivePaper(), 180);

function applyPreviewEditing() {
  paperContainers().forEach((container) => {
    const paper = container.querySelector('.paper');
    if (!paper) return;
    paper.classList.toggle('editing', previewEditing);
    $$('[data-edit]', paper).forEach((el) => {
      if (previewEditing) el.setAttribute('contenteditable', 'true');
      else el.removeAttribute('contenteditable');
    });
  });
  $$('.pe-bar').forEach((bar) => { bar.hidden = !previewEditing; });
  ['#btnPreviewEdit', '#btnPaperEdit'].forEach((id) => {
    const btn = $(id);
    if (!btn) return;
    btn.classList.toggle('primary', previewEditing);
    btn.textContent = previewEditing ? '✓ সম্পাদনা বন্ধ' : '✎ সম্পাদনা';
  });
}

/* Numbered boxes around every line of the paper, for pointing at a specific line. */
function applyLineMode() {
  paperContainers().forEach((container) => {
    const paper = container.querySelector('.paper');
    if (!paper) return;
    paper.classList.toggle('lines', lineMode);
    paper.querySelectorAll('[data-line]').forEach((el) => el.removeAttribute('data-line'));
    if (!lineMode) return;
    const targets = paper.querySelectorAll(
      '[data-edit], .sec > h2, .sec > .hint, .key > h2, .key > h3, .key .kc, .foot',
    );
    let n = 0;
    targets.forEach((el) => { n += 1; el.dataset.line = bn(n); });
  });
  ['#btnLineMode', '#btnPaperLines'].forEach((id) => {
    const btn = $(id);
    if (!btn) return;
    btn.classList.toggle('primary', lineMode);
    btn.textContent = lineMode ? '▦ লাইন বন্ধ' : '▦ লাইন';
  });
}

function toggleLineMode() {
  lineMode = !lineMode;
  applyLineMode();
}

function updateLineModeUI() {
  applyLineMode();
}

function syncPreviewBar() {
  const s = state.settings;
  const fields = [
    ['Title', s.title],
    ['Institute', s.institute],
    ['Exam', s.exam_name],
    ['Class', s.class_label],
    ['Subject', s.subject],
    ['Time', s.time],
    ['Date', s.date],
    ['Instr', Array.isArray(s.instructions) ? s.instructions.join('\n') : String(s.instructions || '')],
  ];
  fields.forEach(([name, value]) => {
    ['#pe', '#pv'].forEach((pfx) => {
      const el = $(pfx + name);
      if (el) el.value = value || '';
    });
  });
}

function updatePreviewEditUI() {
  applyPreviewEditing();
}

function togglePreviewEdit() {
  previewEditing = !previewEditing;
  syncPreviewBar();
  applyPreviewEditing();
}

function openPaperView() {
  const items = cartItems();
  if (!items.length) {
    toast('আগে অন্তত একটি প্রশ্ন নির্বাচন করুন');
    return;
  }
  previewEditing = false;
  if (typeof showView === 'function') showView('paper');
  renderInteractivePaper();
  syncPreviewBar();
}

function openPreview() {
  const items = cartItems();
  if (!items.length) {
    toast('আগে অন্তত একটি প্রশ্ন নির্বাচন করুন');
    return;
  }
  previewEditing = false;
  renderInteractivePaper();
  syncPreviewBar();
  openModal('#previewModal');
}

/* Back-compat for old call sites */
function renderPreviewPaper() { renderInteractivePaper(); }

function isPaperVisible() {
  const pv = $('#paperView');
  const pm = $('#previewModal');
  return (pv && !pv.hidden) || (pm && !pm.hidden);
}

/* Called after a question is edited/deleted through the full form. */
function refreshPreview() {
  if (!isPaperVisible()) return;
  renderInteractivePaper();
}

/* Remove a question from the paper and auto-replace it with another of the same type. */
function removeFromPaper(qid) {
  const idx = state.cart.indexOf(qid);
  if (idx < 0) return;
  const removed = state.bank.find((q) => q.id === qid);

  state.cart.splice(idx, 1);

  let replacement = null;
  if (removed) {
    const used = new Set(state.cart);
    const sameType = state.bank.filter((q) => q.type === removed.type && q.id !== qid && !used.has(q.id));
    const pick = (arr) => arr.length ? arr[Math.floor(Math.random() * arr.length)] : null;
    replacement =
      pick(sameType.filter((q) => q.class_name === removed.class_name && q.subject === removed.subject && String(q.chapter) === String(removed.chapter))) ||
      pick(sameType.filter((q) => q.class_name === removed.class_name && q.subject === removed.subject)) ||
      pick(sameType);
    if (replacement) state.cart.splice(idx, 0, replacement.id);
  }

  persist();
  renderList();
  renderCart();
  if (!state.cart.length) {
    closeModal('#previewModal');
    if (typeof showView === 'function') showView('setup');
    toast('প্রশ্নপত্র খালি হয়ে গেছে');
    return;
  }
  renderInteractivePaper();
  toast(replacement ? 'প্রশ্ন বদলানো হয়েছে (একই ধরনের নতুন প্রশ্ন যোগ হয়েছে)' : 'প্রশ্নটি সরানো হয়েছে — একই ধরনের আর প্রশ্ন নেই');
}

function onPreviewBarInput(e) {
  /* read from whichever bar fired (pe* in modal, pv* in paper view), fall back to current */
  const inPaper = e && e.target && e.target.closest('#paperView');
  const pfx = inPaper ? '#pv' : '#pe';
  const v = (name, fb = '') => {
    const el = $(pfx + name) || $((pfx === '#pv' ? '#pe' : '#pv') + name);
    return el ? el.value : fb;
  };
  state.settings = {
    ...state.settings,
    title: v('Title', state.settings.title),
    institute: v('Institute', state.settings.institute),
    exam_name: v('Exam', state.settings.exam_name),
    class_label: v('Class', state.settings.class_label),
    subject: v('Subject', state.settings.subject),
    time: v('Time', state.settings.time),
    date: v('Date', state.settings.date),
    instructions: v('Instr', (state.settings.instructions || []).join('\n')).split(/\r?\n/).map((x) => x.trim()),
  };
  persist();
  syncSettingsToUI();
  syncPreviewBar();
  rerenderPreview();
}

function savePreviewField(el) {
  const field = el.dataset.edit;
  const text = el.textContent.replace(/\u00a0/g, ' ').trim();
  const li = el.closest('[data-qid]');
  const q = li ? state.bank.find((x) => x.id === li.dataset.qid) : null;
  const i = Number(el.dataset.i);

  /* clear out browser leftovers so an emptied field leaves no dashed box */
  if (!text) el.innerHTML = '';

  if (field === 'title') {
    if (text) state.settings.title = text;
  } else if (field === 'institute') {
    state.settings.institute = text;
  } else if (field === 'exam') {
    state.settings.exam_name = text;
  } else if (field === 'class') {
    if (text) state.settings.class_label = text;
  } else if (field === 'subject') {
    if (text) state.settings.subject = text;
  } else if (field === 'time') {
    if (text) state.settings.time = text;
  } else if (field === 'date') {
    state.settings.date = text;
  } else if (field === 'instr') {
    const arr = Array.isArray(state.settings.instructions) ? [...state.settings.instructions] : [];
    arr[i] = text;
    state.settings.instructions = arr;
  } else if (q) {
    if (field === 'stem') {
      if (text) q.stem = text;
    } else if (field === 'option' && q.options) {
      if (text) q.options[i] = text;
    } else if (field === 'stimulus') {
      q.stimulus = text;
    } else if (field === 'sub' && q.subquestions && q.subquestions[i]) {
      if (text) q.subquestions[i].text = text;
    } else if (field === 'left' && q.left && q.left[i] != null) {
      if (text) q.left[i] = text;
    } else if (field === 'right' && q.right && q.right[i] != null) {
      if (text) q.right[i] = text;
    } else if (field === 'answer') {
      q.answer_text = text;
    }
  } else {
    return;
  }

  persist();
  syncSettingsToUI();
  renderList();
  renderCart();
}

function safeFilename(name) {
  return String(name || 'প্রশ্নপত্র').replace(/[\\/:*?"<>|\n\r]+/g, ' ').trim() || 'প্রশ্নপত্র';
}

function printPaper() {
  const items = cartItems();
  if (!items.length) {
    toast('আগে অন্তত একটি প্রশ্ন নির্বাচন করুন');
    return;
  }
  $('#printArea').innerHTML = renderPaper(items, state.settings);

  const oldTitle = document.title;
  document.title = safeFilename(state.settings.title);

  let done = false;
  const restore = () => {
    if (done) return;
    done = true;
    document.title = oldTitle;
    window.removeEventListener('afterprint', restore);
  };
  window.addEventListener('afterprint', restore);

  setTimeout(() => {
    try {
      window.print();
    } catch (err) {
      toast('প্রিন্ট শুরু করা যায়নি: ' + err.message);
    }
  }, 80);
  setTimeout(restore, 120000);
}
