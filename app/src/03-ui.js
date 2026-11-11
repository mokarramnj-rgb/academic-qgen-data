'use strict';

/* ============================================================
   Modals, question form, blueprint, drafts
   ============================================================ */

function openModal(sel) {
  const m = $(sel);
  if (!m) return;
  m.hidden = false;
  document.body.style.overflow = 'hidden';
}

function closeModal(sel) {
  const m = $(sel);
  if (!m) return;
  m.hidden = true;
  if (!$('.modal:not([hidden])')) document.body.style.overflow = '';
}

function closeAllModals() {
  $$('.modal').forEach((m) => { m.hidden = true; });
  document.body.style.overflow = '';
}

/* ---------------- question form ---------------- */

let editingId = null;

function openForm(id) {
  editingId = id || null;
  const q = id ? state.bank.find((x) => x.id === id) : null;
  const type = q ? q.type : 'mcq';
  const subs = (q && q.subquestions && q.subquestions.length) ? q.subquestions : [
    { label: 'ক', text: '', marks: 1 },
    { label: 'খ', text: '', marks: 2 },
    { label: 'গ', text: '', marks: 3 },
    { label: 'ঘ', text: '', marks: 4 },
  ];
  const chapter = q ? q.chapter : ($('#fChapter').value || (SEED.meta && SEED.meta.chapter) || '');
  const chapterTitle = q ? q.chapter_title : (SEED.meta && SEED.meta.chapter_title) || '';

  $('#formTitle').textContent = q ? 'প্রশ্ন সম্পাদনা' : 'নতুন প্রশ্ন';
  $('#formBody').innerHTML = `<form id="qForm" class="form" novalidate>
    <div class="row2">
      <label class="fld"><span>ধরন</span>
        <select name="type">
          ${Object.entries(TYPES).map(([k, t]) => `<option value="${k}" ${k === type ? 'selected' : ''}>${t.name}</option>`).join('')}
        </select>
      </label>
      <label class="fld"><span>নম্বর</span>
        <input name="marks" type="number" min="1" value="${q ? q.marks : (TYPES[type] || TYPES.mcq).defMarks}">
      </label>
    </div>

    <label class="fld"><span>প্রশ্ন</span>
      <textarea name="stem" rows="2" required>${esc(q ? q.stem : '')}</textarea>
    </label>

    <div class="seg" id="segMcq">
      <h4>অপশন — সঠিক উত্তরটি বেছে নিন</h4>
      ${[0, 1, 2, 3].map((i) => `<div class="optrow">
        <span class="lt">${OPT[i]}</span>
        <input type="text" name="o${i}" value="${esc(q && q.options ? (q.options[i] || '') : '')}" placeholder="অপশন ${OPT[i]}">
      </div>`).join('')}
      <label class="fld" style="margin:8px 0 0"><span>সঠিক উত্তর</span>
        <select name="correct">
          ${[1, 2, 3, 4].map((n) => `<option value="${n}" ${q && q.answer_index === n ? 'selected' : ''}>${OPT[n - 1]}</option>`).join('')}
        </select>
      </label>
    </div>

    <div class="seg" id="segCq">
      <h4>উদ্দীপক</h4>
      <textarea name="stimulus" rows="2" placeholder="উদ্দীপক লিখুন">${esc(q ? (q.stimulus || '') : '')}</textarea>
      <h4 style="margin-top:10px">উপ-প্রশ্ন (ক, খ, গ, ঘ)</h4>
      ${[0, 1, 2, 3].map((i) => `<div class="subrow">
        <span class="lt">${OPT[i]}</span>
        <input type="text" name="s${i}" value="${esc(subs[i] ? subs[i].text : '')}" placeholder="উপ-প্রশ্ন ${OPT[i]}">
        <input type="number" name="sm${i}" min="0" value="${subs[i] ? subs[i].marks : 1}">
      </div>`).join('')}
    </div>

    <div class="seg" id="segTf" hidden>
      <h4>সঠিক উত্তর</h4>
      <label class="fld"><span>বাক্যটি</span>
        <select name="tfans">
          <option value="শুদ্ধ" ${q && q.answer_text === 'শুদ্ধ' ? 'selected' : ''}>শুদ্ধ</option>
          <option value="অশুদ্ধ" ${q && q.answer_text === 'অশুদ্ধ' ? 'selected' : ''}>অশুদ্ধ</option>
        </select>
      </label>
    </div>

    <div class="seg" id="segMatch" hidden>
      <h4>বাম পাশ (প্রতি লাইনে একটি)</h4>
      <textarea name="left" rows="4" placeholder="ক-এর ঘর">${esc(q && q.left ? q.left.join('\n') : '')}</textarea>
      <h4 style="margin-top:10px">ডান পাশ (প্রতি লাইনে একটি)</h4>
      <textarea name="right" rows="4" placeholder="১-এর ঘর">${esc(q && q.right ? q.right.join('\n') : '')}</textarea>
      <label class="fld" style="margin-top:10px"><span>উত্তর (বামের ক্রমে ডানের নম্বর, কমা দিয়ে)</span>
        <input name="mkey" value="${esc(q && q.answer_key ? q.answer_key.map((n) => Number(n) + 1).join(',') : '')}" placeholder="যেমন: ৩,১,৪,২">
      </label>
    </div>

    <label class="fld"><span>উত্তর / মডেল উত্তর</span>
      <textarea name="answer" rows="2">${esc(q ? (q.answer_text || '') : '')}</textarea>
    </label>
    <label class="fld"><span>ব্যাখ্যা (ঐচ্ছিক)</span>
      <input type="text" name="explanation" value="${esc(q ? (q.explanation || '') : '')}">
    </label>

    <div class="row2">
      <label class="fld"><span>অধ্যায়</span><input type="text" name="chapter" value="${esc(chapter)}"></label>
      <label class="fld"><span>পৃষ্ঠা</span><input type="number" name="page" min="0" value="${q && q.page ? q.page : ''}"></label>
    </div>
    <div class="row2">
      <label class="fld"><span>অধ্যায়ের নাম</span><input type="text" name="chapter_title" value="${esc(chapterTitle)}"></label>
      <label class="fld"><span>ব্লুম স্তর</span>
        <select name="bloom">
          ${Object.entries(BLOOM).map(([k, v]) => `<option value="${k}" ${q && q.bloom === k ? 'selected' : ''}>${v}</option>`).join('')}
        </select>
      </label>
    </div>
    <label class="fld"><span>কঠিনতার স্তর</span>
      <select name="difficulty">
        <option value="1" ${q && Number(q.difficulty) === 1 ? 'selected' : ''}>সহজ (১)</option>
        <option value="2" ${q && Number(q.difficulty) === 2 ? 'selected' : ''}>মধ্যম (২)</option>
        <option value="3" ${q && Number(q.difficulty) === 3 ? 'selected' : ''}>কঠিন (৩)</option>
      </select>
    </label>
  </form>`;

  const form = $('#qForm');
  const syncType = (setDefaultMarks) => {
    const t = form.type.value;
    $('#segMcq').hidden = t !== 'mcq';
    $('#segCq').hidden = t !== 'cq';
    $('#segTf').hidden = t !== 'tf';
    $('#segMatch').hidden = t !== 'match';
    if (setDefaultMarks) form.marks.value = TYPES[t].defMarks;
  };
  form.type.addEventListener('change', () => syncType(true));
  [0, 1, 2, 3].forEach((i) => {
    form[`sm${i}`].addEventListener('input', () => {
      const sum = [0, 1, 2, 3].reduce((s, k) => s + (Number(form[`sm${k}`].value) || 0), 0);
      if (form.type.value === 'cq') form.marks.value = sum;
    });
  });
  syncType(false);

  $('#formSave').onclick = () => saveQuestionForm();
  openModal('#formModal');
  setTimeout(() => form.stem.focus(), 60);
}

function saveQuestionForm() {
  const form = $('#qForm');
  const type = form.type.value;
  const stem = form.stem.value.trim();
  if (!stem) { toast('প্রশ্ন লিখুন'); form.stem.focus(); return; }

  let options = [];
  let answerIndex = null;
  let answerText = form.answer.value.trim();
  let answerBool = null;
  let left = [];
  let right = [];
  let answerKey = [];

  if (type === 'mcq') {
    options = [0, 1, 2, 3].map((i) => form[`o${i}`].value.trim());
    if (options.some((o) => !o)) { toast('চারটি অপশনই পূরণ করুন'); return; }
    answerIndex = Number(form.correct.value);
    answerText = options[answerIndex - 1];
  }

  if (type === 'tf') {
    answerText = form.tfans.value;
    answerBool = answerText === 'শুদ্ধ';
  }

  if (type === 'match') {
    left = form.left.value.split(/\r?\n/).map((x) => x.trim()).filter(Boolean);
    right = form.right.value.split(/\r?\n/).map((x) => x.trim()).filter(Boolean);
    answerKey = form.mkey.value.split(/[\s,]+/).filter(Boolean).map((n) => Number(n) - 1);
    if (left.length < 2) { toast('বাম পাশে অন্তত দুটি অংশ দিন'); return; }
    if (right.length < left.length) { toast('ডান পাশে বাম পাশের সমান বা বেশি অংশ দিন'); return; }
    if (answerKey.length !== left.length || answerKey.some((n) => !Number.isInteger(n) || n < 0 || n >= right.length)) {
      toast('উত্তরের ক্রম বাম পাশের সমান সংখ্যক হতে হবে'); return;
    }
  }

  let subquestions = [];
  let stimulus = '';
  let marks = Math.max(1, Number(form.marks.value) || TYPES[type].defMarks);
  if (type === 'cq') {
    stimulus = form.stimulus.value.trim();
    subquestions = [0, 1, 2, 3].map((i) => ({
      label: OPT[i],
      text: form[`s${i}`].value.trim(),
      marks: Math.max(0, Number(form[`sm${i}`].value) || 1),
    }));
    if (!stimulus) { toast('উদ্দীপক লিখুন'); return; }
    if (subquestions.some((s) => !s.text)) { toast('চারটি উপ-প্রশ্নই লিখুন'); return; }
    marks = subquestions.reduce((s, x) => s + x.marks, 0);
  }

  const existing = editingId ? state.bank.find((x) => x.id === editingId) : null;
  const id = editingId || `q-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;

  const item = {
    id,
    type,
    stem,
    marks,
    bloom: form.bloom.value,
    difficulty: Math.min(3, Math.max(1, Number(form.difficulty.value) || 1)),
    chapter: form.chapter.value.trim(),
    chapter_title: form.chapter_title.value.trim(),
    page: form.page.value ? Number(form.page.value) : null,
    answer_text: answerText,
    explanation: form.explanation.value.trim(),
    options: type === 'mcq' ? options : [],
    answer_index: type === 'mcq' ? answerIndex : null,
    answer_bool: type === 'tf' ? answerBool : null,
    left: type === 'match' ? left : [],
    right: type === 'match' ? right : [],
    answer_key: type === 'match' ? answerKey : [],
    stimulus,
    subquestions,
    class_name: (existing && existing.class_name) || $('#fClass').value || (SEED.meta && SEED.meta.class_name) || '',
    subject: (existing && existing.subject) || $('#fSubject').value || (SEED.meta && SEED.meta.subject) || '',
    source: (existing && existing.source) || (SEED.meta && SEED.meta.source) || 'NCTB',
  };

  if (editingId) {
    const i = state.bank.findIndex((x) => x.id === editingId);
    if (i >= 0) state.bank[i] = item;
  } else {
    state.bank.push(item);
  }

  persist();
  closeModal('#formModal');
  refreshFilters();
  renderList();
  renderCart();
  refreshPreview();
  toast(editingId ? 'প্রশ্ন আপডেট হয়েছে' : 'প্রশ্ন যোগ হয়েছে');
  editingId = null;
}

function deleteQuestion(id) {
  const q = state.bank.find((x) => x.id === id);
  if (!q) return;
  if (!confirm('প্রশ্নটি স্থায়ীভাবে মুছে ফেলবেন?')) return;
  state.bank = state.bank.filter((x) => x.id !== id);
  state.cart = state.cart.filter((x) => x !== id);
  persist();
  refreshFilters();
  renderList();
  renderCart();
  refreshPreview();
  toast('প্রশ্ন মুছে ফেলা হয়েছে');
}

/* ---------------- blueprint (auto pick) ---------------- */

function shuffle(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function openBlueprint() {
  const pool = currentPool();
  const counts = {};
  pool.forEach((q) => { counts[q.type] = (counts[q.type] || 0) + 1; });
  $('#bpAvail').textContent =
    'বর্তমান ফিল্টারে আছে — ' +
    TYPE_ORDER.filter((t) => counts[t]).map((t) => `${TYPES[t].label} ${bn(counts[t])}`).join(', ');
  openModal('#blueprintModal');
}

function runBlueprint() {
  const fields = {
    mcq: '#bpMcq', fill: '#bpFill', tf: '#bpTf', match: '#bpMatch',
    wrq_k: '#bpK', wrq_kh: '#bpKh', cq: '#bpCq',
  };
  const counts = {};
  Object.entries(fields).forEach(([type, sel]) => {
    const el = $(sel);
    counts[type] = el ? Math.max(0, Number(el.value) || 0) : 0;
  });
  const pool = currentPool();
  const picked = [];
  TYPE_ORDER.forEach((t) => {
    const arr = shuffle(pool.filter((q) => q.type === t)).slice(0, counts[t]);
    picked.push(...arr.map((q) => q.id));
  });
  if (!picked.length) { toast('এই ফিল্টারে প্রশ্ন পাওয়া যায়নি'); return; }
  if ($('#bpReplace').checked) state.cart = picked;
  else state.cart = [...new Set([...state.cart, ...picked])];
  persist();
  renderList();
  renderCart();
  closeModal('#blueprintModal');
  toast(`${bn(state.cart.length)}টি প্রশ্ন নির্বাচিত হয়েছে`);
}

/* ---------------- drafts ---------------- */

function saveDraft() {
  if (!state.cart.length) { toast('আগে প্রশ্ন নির্বাচন করুন'); return; }
  const now = new Date();
  const paper = {
    id: `paper-${now.getTime().toString(36)}`,
    title: state.settings.title || 'প্রশ্নপত্র',
    config: { ...state.settings },
    item_ids: [...state.cart],
    total_marks: cartMarks(),
    updated_at: now.toISOString(),
  };
  state.papers.unshift(paper);
  state.papers = state.papers.slice(0, 100);
  persist();
  toast('খসড়া সংরক্ষিত হয়েছে');
}

function openDrafts() {
  renderDrafts();
  openModal('#draftsModal');
}

function renderDrafts() {
  const body = $('#draftsBody');
  if (!state.papers.length) {
    body.innerHTML = '<div class="empty"><div class="big">📄</div><div>এখনো কোনো খসড়া সংরক্ষণ করা হয়নি।</div></div>';
    return;
  }
  body.innerHTML = `<div class="draft-list">${state.papers.map((p) => `
    <div class="draft" data-id="${esc(p.id)}">
      <div class="draft-main">
        <b>${esc(p.title)}</b>
        <small>${bn(p.item_ids.length)} প্রশ্ন · ${bn(p.total_marks)} নম্বর · ${esc(formatDate(p.updated_at))}</small>
      </div>
      <button class="btn small" data-act="load">খুলুন</button>
      <button class="icon danger" data-act="remove" title="মুছুন">✕</button>
    </div>`).join('')}</div>`;
}

function formatDate(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString('bn-BD', { year: 'numeric', month: 'long', day: 'numeric' }) +
      ' ' + d.toLocaleTimeString('bn-BD', { hour: '2-digit', minute: '2-digit' });
  } catch (_) {
    return iso || '';
  }
}

function loadDraft(id) {
  const p = state.papers.find((x) => x.id === id);
  if (!p) return;
  state.cart = (p.item_ids || []).filter((qid) => state.bank.some((q) => q.id === qid));
  state.settings = { ...DEFAULT_SETTINGS, ...(p.config || {}) };
  syncSettingsToUI();
  persist();
  renderList();
  renderCart();
  closeAllModals();
  toast('খসড়া খোলা হয়েছে');
}

function removeDraft(id) {
  if (!confirm('খসড়াটি মুছে ফেলবেন?')) return;
  state.papers = state.papers.filter((p) => p.id !== id);
  persist();
  renderDrafts();
}

/* ---------------- setup / prepare form ---------------- */

function setupOptions() {
  const clsSel = $('#suClass');
  const subSel = $('#suSubject');
  if (!clsSel || !subSel) return;

  /* only the classes picked on the home page, limited to classes that have data */
  const bankClasses = uniqueSorted(state.bank.map((q) => q.class_name));
  const picked = homePickedClasses();
  const allowed = bankClasses.filter((c) => picked.includes(String(c)));
  const classes = allowed.length ? allowed : bankClasses;

  fillSelect(clsSel, classes.map((c) => [c, classLabel(c)]));
  if (classes.length && !classes.includes(clsSel.value)) clsSel.value = classes[0];
  refreshSetupSubjects();
}

function refreshSetupSubjects() {
  const cls = $('#suClass').value;
  const subSel = $('#suSubject');
  const scoped = state.bank.filter((q) => !cls || q.class_name === cls);
  const subjects = uniqueSorted(scoped.map((q) => q.subject));
  fillSelect(subSel, subjects.map((s) => [s, s]));
  if (subjects.length) subSel.value = subjects[0];
  refreshSetupChapters();
}

function refreshSetupChapters() {
  const cls = $('#suClass').value;
  const sub = $('#suSubject').value;
  const drop = $('#suChapterDrop');
  if (!drop) return;
  const seen = new Set();
  const chapters = [];
  state.bank.forEach((q) => {
    if (cls && q.class_name !== cls) return;
    if (sub && q.subject !== sub) return;
    const key = String(q.chapter || '');
    if (!key || seen.has(key)) return;
    seen.add(key);
    chapters.push({ key, title: q.chapter_title || '' });
  });
  chapters.sort((a, b) => Number(a.key) - Number(b.key));

  if (!chapters.length) {
    drop.innerHTML = '<div class="chapter-empty">এই শ্রেণি ও বিষয়ে কোনো অধ্যায় পাওয়া যায়নি।</div>';
    refreshSetupTypes();
    return;
  }
  drop.innerHTML = chapters.map((ch) => `<label class="chapter-opt">
      <input type="checkbox" value="${esc(ch.key)}">
      <span>অধ্যায় ${bn(ch.key)}${ch.title ? ` — ${esc(ch.title)}` : ''}</span>
    </label>`).join('')
    + `<label class="chapter-opt chapter-all">
      <input type="checkbox" id="suChaptersAll">
      <span>সকল অধ্যায়</span>
    </label>`;
  refreshSetupTypes();
}

function selectedSetupDifficulties() {
  const random = $('#suDifficulty .chip.on[data-diff="all"]');
  if (random) return [1, 2, 3];
  return $$('#suDifficulty .chip.on[data-diff]')
    .map((c) => Number(c.dataset.diff))
    .filter(Boolean);
}

function refreshSetupTypes() {
  const cls = $('#suClass')?.value || '';
  const sub = $('#suSubject')?.value || '';
  const chapters = selectedSetupChapters();
  const diffs = selectedSetupDifficulties();
  const pool = state.bank.filter((q) => {
    if (cls && q.class_name !== cls) return false;
    if (sub && q.subject !== sub) return false;
    if (chapters.length && !chapters.includes(String(q.chapter || ''))) return false;
    if (diffs.length && !diffs.includes(Number(q.difficulty || 1))) return false;
    return true;
  });
  const counts = {};
  pool.forEach((q) => { counts[q.type] = (counts[q.type] || 0) + 1; });

  const allowed = new Set(typesForClass(cls));

  $$('#suTypes .type-row').forEach((row) => {
    const type = row.dataset.type;
    /* only the types this class actually uses are offered */
    row.hidden = !allowed.has(type);
    const avail = counts[type] || 0;
    const totalEl = row.querySelector('.type-total');
    const num = row.querySelector('.type-num');
    const cb = row.querySelector('input[type=checkbox]');
    if (totalEl) totalEl.textContent = bn(avail);
    if (num) {
      num.max = String(avail);
      const raw = num.value;
      if (raw !== '' && !Number.isNaN(Number(raw))) {
        const n = Math.max(0, Math.floor(Number(raw)));
        if (n > avail) num.value = String(avail);
      }
      if (avail === 0 && raw !== '') num.value = '';
    }
    if (row.hidden && cb) cb.checked = false;
  });
  updateSetupTotal();
}

function updateSetupTotal() {
  const el = $('#suTotalCount');
  if (!el) return;
  let sum = 0;
  $$('#suTypes .type-row').forEach((row) => {
    if (row.hidden) return;
    const cb = row.querySelector('input[type=checkbox]');
    const num = row.querySelector('.type-num');
    if (cb && cb.checked && num) sum += Math.max(0, Number(num.value || 0));
  });
  el.textContent = bn(sum);
}

/* ---------------- setup time (hours + minutes boxes) ---------------- */

function bnToNum(v) {
  return Number(String(v ?? '').replace(/[০-৯]/g, (d) => String(BND.indexOf(d)))) || 0;
}

function parseTimeText(text) {
  const s = String(text || '');
  const h = s.match(/([০-৯0-9]+)\s*ঘণ্টা/);
  const m = s.match(/([০-৯0-9]+)\s*মিনিট/);
  let hours = h ? bnToNum(h[1]) : 0;
  let minutes = m ? bnToNum(m[1]) : 0;
  if (!h && !m) hours = bnToNum(s);
  return { hours, minutes };
}

function setupTimeText() {
  const hours = Math.max(0, Math.floor(Number($('#suHours')?.value) || 0));
  const minutes = Math.max(0, Math.floor(Number($('#suMinutes')?.value) || 0));
  const parts = [];
  if (hours) parts.push(`${bn(hours)} ঘণ্টা`);
  if (minutes) parts.push(`${bn(minutes)} মিনিট`);
  return parts.join(' ');
}

function initSetupForm() {
  if ($('#suExam') && !$('#suExam').dataset.init) {
    $('#suExam').value = state.settings.exam_name || '';
    $('#suInstitute').value = state.settings.institute || '';
    const t = parseTimeText(state.settings.time);
    $('#suHours').value = t.hours ? String(t.hours) : '';
    $('#suMinutes').value = t.minutes ? String(t.minutes) : '';
    $('#suExam').dataset.init = '1';
  }
  setupOptions();
  refreshSetupTypes();
}

function selectedSetupChapters() {
  return $$('#suChapterDrop input[type=checkbox]:checked:not(#suChaptersAll)').map((c) => c.value);
}

function selectedSetupTypes() {
  /* types the user wants (checked); counts read separately */
  return $$('#suTypes .type-row').filter((row) => {
    if (row.hidden) return false;
    const cb = row.querySelector('input[type=checkbox]');
    const num = row.querySelector('.type-num');
    return cb && cb.checked && Number(num?.value || 0) > 0;
  }).map((row) => row.dataset.type);
}

function setupTypeCounts() {
  const out = {};
  $$('#suTypes .type-row').forEach((row) => {
    if (row.hidden) return;
    const cb = row.querySelector('input[type=checkbox]');
    const num = row.querySelector('.type-num');
    const n = (cb && cb.checked) ? Math.max(0, Number(num?.value || 0)) : 0;
    out[row.dataset.type] = n;
  });
  return out;
}

function updateTypeLabel() {
  const all = $$('#suTypeDrop input[type=checkbox]');
  const sel = all.filter((c) => c.checked);
  const label = $('#suTypeLabel');
  if (!label) return;
  if (!sel.length) label.textContent = 'কোনো ধরন নির্বাচিত নয়';
  else if (sel.length === all.length) label.textContent = 'সব ধরন নির্বাচিত';
  else {
    const names = { mcq: 'MCQ', fill: 'শূন্যস্থান', tf: 'শুদ্ধ/অশুদ্ধ', match: 'মিলকরণ', wrq_k: 'জ্ঞানমূলক', wrq_kh: 'অনুধাবনমূলক', cq: 'সৃজনশীল' };
    label.textContent = sel.map((c) => names[c.value] || c.value).join(', ');
  }
}

function closeTypeDrop(e) {
  const ms = $('#suTypeMs');
  const drop = $('#suTypeDrop');
  if (!ms || !drop) return;
  if (e && ms.contains(e.target)) return;
  drop.hidden = true;
}

function generateFromSetup() {
  const want = setupTypeCounts();
  const types = TYPE_ORDER.filter((t) => (want[t] || 0) > 0);
  if (!types.length) { toast('অন্তত একটি প্রশ্নের ধরন ও সংখ্যা নির্বাচন করুন'); return; }

  const cls = $('#suClass').value;
  const sub = $('#suSubject').value;
  const chapters = selectedSetupChapters();
  if (!chapters.length) { toast('অন্তত একটি অধ্যায় নির্বাচন করুন'); return; }

  const exam = $('#suExam').value.trim();
  const institute = $('#suInstitute').value.trim();
  const duration = setupTimeText() || state.settings.time;

  const diffs = selectedSetupDifficulties();
  if (!diffs.length) { toast('অন্তত একটি কঠিনতার স্তর নির্বাচন করুন'); return; }

  state.settings = {
    ...state.settings,
    exam_name: exam,
    institute,
    time: duration,
    class_label: cls ? classLabel(cls) : state.settings.class_label,
    subject: sub || state.settings.subject,
  };

  const pool = state.bank.filter((q) => {
    if (cls && q.class_name !== cls) return false;
    if (sub && q.subject !== sub) return false;
    if (!chapters.includes(String(q.chapter || ''))) return false;
    if (!diffs.includes(Number(q.difficulty || 1))) return false;
    return true;
  });

  const picked = [];
  TYPE_ORDER.forEach((t) => {
    const take = Math.max(0, Number(want[t] || 0));
    if (!take) return;
    picked.push(...shuffle(pool.filter((q) => q.type === t)).slice(0, take).map((q) => q.id));
  });
  if (!picked.length) { toast('এই নির্বাচনে কোনো প্রশ্ন পাওয়া যায়নি'); return; }

  state.cart = picked;
  persist();
  syncSettingsToUI();
  openPaperView();
  toast(`${bn(picked.length)}টি প্রশ্ন নিয়ে প্রশ্নপত্র তৈরি হয়েছে`);
}

/* ============================================================
   On-demand class data download (GitHub -> local app storage)
   ============================================================ */

const DATA_SOURCES = [
  'https://raw.githubusercontent.com/mokarramnj-rgb/academic-qgen-data/main/classes/',
  'https://cdn.jsdelivr.net/gh/mokarramnj-rgb/academic-qgen-data@main/classes/',
];

let dlBusy = false;
let dlHideTimer = null;

function homePickedClasses() {
  return $$('#homeClassPicks input:checked').map((el) => String(el.value));
}

function saveHomePicks() {
  const picked = homePickedClasses();
  if (!picked.length) return;
  state.settings.selected_classes = picked;
  persist();
}

function restoreHomePicks() {
  const picks = state.settings.selected_classes;
  if (!Array.isArray(picks) || !picks.length) return;
  $$('#homeClassPicks .class-pick').forEach((label) => {
    const input = label.querySelector('input');
    if (input) input.checked = picks.includes(String(input.value));
  });
}

function bankClassCounts() {
  const counts = {};
  state.bank.forEach((q) => {
    const c = String(q.class_name || '');
    if (c) counts[c] = (counts[c] || 0) + 1;
  });
  return counts;
}

function missingSelectedClasses() {
  const have = new Set(state.bank.map((q) => String(q.class_name || '')));
  return homePickedClasses().filter((c) => !have.has(c));
}

function setDownloadProgress(ratio, text) {
  const wrap = $('#homeDl');
  const fill = $('#homeDlFill');
  const label = $('#homeDlText');
  if (!wrap || !fill) return;
  wrap.hidden = false;
  const pct = Math.round(Math.max(0, Math.min(1, ratio || 0)) * 100);
  fill.style.width = `${pct}%`;
  if (label && text != null) label.textContent = text;
}

function readStreamJson(res, onProgress) {
  const total = Number(res.headers.get('content-length')) || 0;
  if (!res.body || !total) return res.json();

  const reader = res.body.getReader();
  const chunks = [];
  let received = 0;

  return new Promise((resolve, reject) => {
    let timer = null;
    const arm = () => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => {
        try { reader.cancel(); } catch (_) { /* ignore */ }
        reject(new Error('stream stalled'));
      }, 10000);
    };
    const done = (fn, arg) => { if (timer) clearTimeout(timer); fn(arg); };

    const pump = () => reader.read().then(({ done: fin, value }) => {
      if (fin) {
        const bytes = new Uint8Array(received);
        let offset = 0;
        chunks.forEach((c) => { bytes.set(c, offset); offset += c.length; });
        try { done(resolve, JSON.parse(new TextDecoder('utf-8').decode(bytes))); }
        catch (err) { done(reject, err); }
        return;
      }
      chunks.push(value);
      received += value.length;
      if (onProgress) onProgress(received / total);
      arm();
      pump();
    }).catch((err) => done(reject, err));

    arm();
    pump();
  });
}

async function fetchClassJson(cls, onProgress) {
  const file = `class-${cls}.json`;
  let lastErr = null;

  for (const base of DATA_SOURCES) {
    const url = base + file;
    try {
      const res = await fetch(url, { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      try {
        return await readStreamJson(res, onProgress);
      } catch (_) {
        /* streaming unsupported or stalled: read the whole file instead */
        const plain = await fetch(url, { cache: 'no-store' });
        if (!plain.ok) throw new Error(`HTTP ${plain.status}`);
        return await plain.json();
      }
    } catch (err) {
      lastErr = err;
    }
  }
  throw lastErr || new Error('ডাউনলোড ব্যর্থ');
}

function normalizeClassData(data, cls) {
  const meta = (data && data.meta) || {};
  const cmap = meta.chapter_map || meta.cm || {};
  const base = {
    class_name: String(meta.class_name || cls),
    subject: meta.subject || '',
    source: meta.source || 'NCTB',
  };
  const rows = Array.isArray(data) ? data : (data && data.questions) || [];

  return rows.map((q) => {
    const ch = String(q.chapter ?? '');
    const diff = Math.min(3, Math.max(1, Number(q.difficulty) || 1));
    return {
      id: q.id || '',
      type: q.type || 'mcq',
      stem: q.stem || '',
      options: Array.isArray(q.options) ? q.options : [],
      answer_index: q.answer_index ?? null,
      answer_text: q.answer_text || '',
      marks: Number(q.marks) || 1,
      bloom: q.bloom || 'remember',
      explanation: q.explanation || '',
      difficulty: diff,
      class_name: String(q.class_name || base.class_name || cls),
      subject: q.subject || base.subject,
      chapter: ch,
      chapter_title: q.chapter_title || cmap[ch] || '',
      page: q.page ?? null,
      source: q.source || base.source,
      stimulus: q.stimulus || '',
      subquestions: Array.isArray(q.subquestions) ? q.subquestions : [],
      left: Array.isArray(q.left) ? q.left : [],
      right: Array.isArray(q.right) ? q.right : [],
      answer_key: Array.isArray(q.answer_key) ? q.answer_key : [],
      answer_bool: typeof q.answer_bool === 'boolean' ? q.answer_bool : null,
    };
  }).filter((q) => q.stem);
}

function mergeBankQuestions(list) {
  const ids = new Set(state.bank.map((q) => q.id));
  let added = 0;
  list.forEach((q) => {
    if (!q.id) return;
    if (ids.has(q.id)) return;
    state.bank.push(q);
    ids.add(q.id);
    added++;
  });
  return added;
}

async function downloadSelectedClasses() {
  const missing = missingSelectedClasses();
  if (!missing.length || dlBusy) return;

  dlBusy = true;
  if (dlHideTimer) clearTimeout(dlHideTimer);
  refreshHomeClassNote();

  const added = [];
  const failed = [];
  let totalAdded = 0;

  setDownloadProgress(0, 'ডাউনলোড শুরু হচ্ছে…');

  for (let i = 0; i < missing.length; i++) {
    const cls = missing[i];
    setDownloadProgress(i / missing.length, `${classLabel(cls)} ডাউনলোড হচ্ছে…`);
    try {
      const data = await fetchClassJson(cls, (frac) => {
        setDownloadProgress((i + frac) / missing.length, `${classLabel(cls)} ডাউনলোড হচ্ছে… ${bn(Math.round(frac * 100))}%`);
      });
      const questions = normalizeClassData(data, cls);
      if (!questions.length) throw new Error('empty');
      totalAdded += mergeBankQuestions(questions);
      added.push(cls);
    } catch (_) {
      failed.push(cls);
    }
    setDownloadProgress((i + 1) / missing.length, `${classLabel(cls)} শেষ`);
  }

  if (added.length) {
    persist();
    refreshFilters(false);
    if (currentView === 'studio' || currentView === 'answers') renderList();
  }

  dlBusy = false;
  refreshHomeClassNote();

  const parts = [];
  if (added.length) parts.push(`${added.map((c) => classLabel(c)).join(', ')} যোগ হয়েছে (${bn(totalAdded)} প্রশ্ন)`);
  if (failed.length) parts.push(`${failed.map((c) => classLabel(c)).join(', ')} পাওয়া যায়নি`);
  setDownloadProgress(1, parts.join(' · '));

  dlHideTimer = setTimeout(() => {
    if (dlBusy) return;
    const wrap = $('#homeDl');
    if (wrap) wrap.hidden = true;
  }, failed.length ? 8000 : 4000);
}

function refreshHomeClassNote() {
  const counts = bankClassCounts();
  $$('#homeClassPicks .class-pick').forEach((label) => {
    const input = label.querySelector('input');
    if (!input) return;
    const cls = String(input.value);
    const n = counts[cls] || 0;
    label.classList.toggle('no-data', !n);
    label.title = n ? `${bn(n)}টি প্রশ্ন আছে` : 'এখনো ডাউনলোড করা হয়নি';
  });

  const missing = missingSelectedClasses();
  const btn = $('#btnDownloadClass');
  if (btn) {
    btn.disabled = dlBusy || !missing.length;
    btn.title = missing.length ? 'নির্বাচিত শ্রেণির ডেটা ডাউনলোড করুন' : 'নির্বাচিত শ্রেণির ডেটা আগেই আছে';
  }

  const note = $('#homeClassNote');
  if (!note || dlBusy) return;

  const available = Object.keys(counts).sort((a, b) => Number(a) - Number(b));
  const have = available.map((c) => `<b>${esc(classLabel(c))}</b> (${bn(counts[c])})`).join(', ');
  note.innerHTML = (have ? `এই অ্যাপে আছে: ${have}। ` : '')
    + (missing.length
      ? `নির্বাচিত ${missing.map((c) => esc(classLabel(c))).join(', ')} ডাউনলোড করতে ইন্টারনেট লাগবে।`
      : 'নির্বাচিত শ্রেণির সব ডেটা এই অ্যাপে আছে।');
}
