'use strict';

/* ============================================================
   Settings, import/export, event wiring, startup
   ============================================================ */

function syncSettingsFromUI() {
  state.settings = {
    ...state.settings,
    title: $('#sTitle').value,
    exam_name: $('#sExam').value,
    institute: $('#sInstitute') ? $('#sInstitute').value : state.settings.institute,
    class_label: $('#sClass').value,
    subject: $('#sSubject').value,
    time: $('#sTime').value,
    date: $('#sDate').value,
    instructions: $('#sInstr').value.split(/\r?\n/).map((x) => x.trim()).filter(Boolean),
    answer_key: $('#sKey').checked,
    group: $('#sGroup').checked,
  };
  persist();
}

function syncSettingsToUI() {
  const s = state.settings;
  $('#sTitle').value = s.title || '';
  $('#sExam').value = s.exam_name || '';
  $('#sClass').value = s.class_label || '';
  $('#sSubject').value = s.subject || '';
  $('#sTime').value = s.time || '';
  $('#sDate').value = s.date || '';
  $('#sInstr').value = Array.isArray(s.instructions) ? s.instructions.join('\n') : String(s.instructions || '');
  $('#sKey').checked = s.answer_key !== false;
  $('#sGroup').checked = s.group !== false;
}

/* ---------------- import / export ---------------- */

function normalizeQuestion(raw, meta, id) {
  const type = TYPES[raw.type] ? raw.type : 'mcq';
  return {
    id,
    type,
    stem: String(raw.stem || ''),
    stimulus: raw.stimulus || '',
    options: Array.isArray(raw.options) ? raw.options : [],
    answer_index: raw.answer_index ?? null,
    answer_text: raw.answer_text || '',
    subquestions: Array.isArray(raw.subquestions) ? raw.subquestions : [],
    left: Array.isArray(raw.left) ? raw.left : [],
    right: Array.isArray(raw.right) ? raw.right : [],
    answer_key: Array.isArray(raw.answer_key) ? raw.answer_key : [],
    answer_bool: typeof raw.answer_bool === 'boolean' ? raw.answer_bool : null,
    explanation: raw.explanation || '',
    marks: Number(raw.marks) || TYPES[type].defMarks,
    bloom: raw.bloom || 'remember',
    difficulty: Math.min(3, Math.max(1, Number(raw.difficulty) || 1)),
    class_name: String(raw.class_name || meta.class_name || ''),
    subject: raw.subject || meta.subject || '',
    chapter: String(raw.chapter || meta.chapter || ''),
    chapter_title: raw.chapter_title || meta.chapter_title || '',
    page: raw.page ?? meta.page ?? null,
    source: raw.source || meta.source || 'NCTB',
  };
}

async function handleImportFile(file) {
  if (!file) return;
  let data;
  try {
    data = JSON.parse(await file.text());
  } catch (err) {
    toast('JSON ফাইলটি পড়া যায়নি');
    return;
  }
  const questions = Array.isArray(data) ? data : (data.questions || []);
  const meta = Array.isArray(data) ? {} : (data.meta || {});
  if (!Array.isArray(questions) || !questions.length) {
    toast('ফাইলে কোনো প্রশ্ন পাওয়া যায়নি');
    return;
  }

  let added = 0;
  let skipped = 0;
  questions.forEach((raw, i) => {
    if (!raw || !raw.stem || !raw.type) { skipped += 1; return; }
    const id = raw.id || `imp-${Date.now().toString(36)}-${i}`;
    if (state.bank.some((q) => q.id === id)) { skipped += 1; return; }
    state.bank.push(normalizeQuestion(raw, meta, id));
    added += 1;
  });

  persist();
  refreshFilters();
  renderList();
  toast(`${bn(added)}টি প্রশ্ন যোগ হয়েছে${skipped ? `, ${bn(skipped)}টি বাদ` : ''}`);
}

function exportBank() {
  const stamp = new Date().toISOString().slice(0, 10);
  download(`question-bank-${stamp}.json`, JSON.stringify({
    version: 1,
    app: 'question-paper-studio',
    exported_at: new Date().toISOString(),
    settings: state.settings,
    questions: state.bank,
    papers: state.papers,
  }, null, 2));
  toast('ব্যাকআপ ফাইল ডাউনলোড হচ্ছে');
}

/* ---------------- views ---------------- */

function showView(name) {
  currentView = name;
  browseMode = name === 'answers';
  document.body.className = `mode-${name}`;
  $('#homeView').hidden = name !== 'home';
  $('#setupView').hidden = name !== 'setup';
  $('#paperView').hidden = name !== 'paper';
  $('#studioView').hidden = !(name === 'studio' || name === 'answers');
  window.scrollTo(0, 0);
  if (name === 'setup') initSetupForm();
  if (name === 'studio' || name === 'answers') renderList();
}

function toggleAnswer(card, btn) {
  const on = card.classList.toggle('showans');
  if (btn) btn.textContent = on ? 'উত্তর লুকাও' : 'উত্তর দেখাও';
}

/* ---------------- events ---------------- */

function bindEvents() {
  const rerender = debounce(() => renderList(), 120);

  $('#btnGoPrepare').addEventListener('click', () => showView('setup'));
  $('#btnDownloadClass').addEventListener('click', downloadSelectedClasses);
  $('#homeClassPicks').addEventListener('change', () => { saveHomePicks(); refreshHomeClassNote(); });
  $('#btnHome').addEventListener('click', () => showView('home'));
  $('#btnSetupHome').addEventListener('click', () => showView('home'));
  $('#btnGenerate').addEventListener('click', generateFromSetup);
  $('#suClass').addEventListener('change', refreshSetupSubjects);
  $('#suSubject').addEventListener('change', refreshSetupChapters);
  $('#suChapterDrop').addEventListener('change', (e) => {
    const all = $('#suChaptersAll');
    const items = $$('#suChapterDrop input[type=checkbox]:not(#suChaptersAll)');
    if (e.target === all) {
      items.forEach((c) => { c.checked = all.checked; });
    } else if (all) {
      all.checked = items.length > 0 && items.every((c) => c.checked);
    }
    refreshSetupTypes();
  });
  $('#suTypes').addEventListener('input', (e) => {
    const row = e.target.closest('.type-row');
    if (!row) return;
    if (e.target.classList.contains('type-num')) {
      row.dataset.touched = '1';
      const cb = row.querySelector('input[type=checkbox]');
      if (cb && !cb.checked) cb.checked = true;
    }
    updateSetupTotal();
  });
  $('#suTypes').addEventListener('change', (e) => {
    const row = e.target.closest('.type-row');
    if (!row) { updateSetupTotal(); return; }
    if (e.target.type === 'checkbox') {
      const num = row.querySelector('.type-num');
      if (num && !e.target.checked) num.value = '';
      if (num && e.target.checked) num.focus();
    }
    updateSetupTotal();
  });

  $$('.msel-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const drop = btn.parentElement.querySelector('.msel-drop');
      if (!drop) return;
      const opening = drop.hidden;
      $$('.msel-drop').forEach((d) => { d.hidden = true; });
      drop.hidden = !opening;
    });
  });
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.msel')) $$('.msel-drop').forEach((d) => { d.hidden = true; });
  });

  $('#fSearch').addEventListener('input', rerender);

  ['#fClass', '#fSubject', '#fChapter', '#fBloom'].forEach((sel) => {
    $(sel).addEventListener('change', () => {
      if (sel === '#fClass' || sel === '#fSubject') refreshFilters();
      renderList();
    });
  });

  $('#fTypes').addEventListener('click', (e) => {
    const chip = e.target.closest('.chip');
    if (!chip) return;
    chip.classList.toggle('on');
    renderList();
  });
  $('#fDifficulty').addEventListener('click', (e) => {
    const chip = e.target.closest('.chip');
    if (!chip) return;
    chip.classList.toggle('on');
    renderList();
  });
  $('#suDifficulty').addEventListener('click', (e) => {
    const chip = e.target.closest('.chip');
    if (!chip) return;
    const chips = $$('#suDifficulty .chip[data-diff]');
    const diffs = chips.filter((c) => c.dataset.diff !== 'all');
    const random = chips.find((c) => c.dataset.diff === 'all');

    if (chip.dataset.diff === 'all') {
      /* random is exclusive: only the random chip stays selected */
      const turnOn = !chip.classList.contains('on');
      diffs.forEach((c) => c.classList.remove('on'));
      chip.classList.toggle('on', turnOn);
    } else {
      chip.classList.toggle('on');
      if (random) random.classList.remove('on');
    }
    refreshSetupTypes();
  });

  $('#fReset').addEventListener('click', () => {
    $('#fSearch').value = '';
    $('#fBloom').value = '';
    $$('#fTypes .chip, #fDifficulty .chip').forEach((c) => c.classList.add('on'));
    refreshFilters(false);
    renderList();
  });

  $('#btnSelectAll').addEventListener('click', selectAllFiltered);
  $('#btnClear').addEventListener('click', clearCart);

  $('#btnBlueprint').addEventListener('click', openBlueprint);
  $('#btnRunBlueprint').addEventListener('click', runBlueprint);

  $('#btnPreview').addEventListener('click', openPreview);
  $('#btnPreview2').addEventListener('click', openPreview);
  $('#btnPrint').addEventListener('click', printPaper);
  $('#btnPrint2').addEventListener('click', printPaper);
  $('#btnPreviewEdit').addEventListener('click', togglePreviewEdit);
  $('#btnLineMode').addEventListener('click', toggleLineMode);
  $('#btnPaperEdit').addEventListener('click', togglePreviewEdit);
  $('#btnPaperLines').addEventListener('click', toggleLineMode);
  $('#btnPaperPrint').addEventListener('click', printPaper);
  $('#btnPaperSetup').addEventListener('click', () => showView('setup'));
  $('#btnPaperHome').addEventListener('click', () => showView('home'));

  /* in-place paper editing */
  ['#peBar', '#paperEditBar'].forEach((sel) => {
    const el = $(sel);
    if (!el) return;
    el.addEventListener('input', onPreviewBarInput);
    el.addEventListener('change', onPreviewBarInput);
  });
  ['#previewBody', '#paperViewBody'].forEach((sel) => {
    const root = $(sel);
    if (!root) return;
    root.addEventListener('focusout', (e) => {
      const el = e.target.closest('[data-edit]');
      if (el && el.getAttribute('contenteditable') === 'true') savePreviewField(el);
    });
    root.addEventListener('click', (e) => {
      const del = e.target.closest('.pe-qdel');
      if (del) { e.preventDefault(); removeFromPaper(del.dataset.qid); return; }
      const b = e.target.closest('.pe-qedit');
      if (b) { e.preventDefault(); openForm(b.dataset.qid); }
    });
  });

  $('#btnDraft').addEventListener('click', saveDraft);
  $('#btnDrafts').addEventListener('click', openDrafts);

  $('#btnNewQuestion').addEventListener('click', () => openForm(null));
  $('#btnImport').addEventListener('click', () => $('#importFile').click());
  $('#importFile').addEventListener('change', (e) => {
    const file = e.target.files && e.target.files[0];
    e.target.value = '';
    handleImportFile(file);
  });
  $('#btnExport').addEventListener('click', exportBank);

  /* cart */
  $('#cartList').addEventListener('click', (e) => {
    const row = e.target.closest('.crow');
    if (!row) return;
    const act = e.target.closest('[data-act]');
    if (!act) return;
    const id = row.dataset.id;
    if (act.dataset.act === 'rm') removeCart(id);
    if (act.dataset.act === 'up') moveCart(id, -1);
    if (act.dataset.act === 'down') moveCart(id, 1);
  });

  $('#btnOpenCart').addEventListener('click', () => {
    $('#cartPanel').classList.add('open');
    $('#backdrop').hidden = false;
  });
  $('#btnCloseCart').addEventListener('click', closeCartPanel);
  $('#backdrop').addEventListener('click', closeCartPanel);

  /* settings */
  $('#cartSettings').addEventListener('input', syncSettingsFromUI);
  $('#cartSettings').addEventListener('change', syncSettingsFromUI);

  /* drafts */
  $('#draftsBody').addEventListener('click', (e) => {
    const row = e.target.closest('.draft');
    if (!row) return;
    const act = e.target.closest('[data-act]');
    if (!act) return;
    if (act.dataset.act === 'load') loadDraft(row.dataset.id);
    if (act.dataset.act === 'remove') removeDraft(row.dataset.id);
  });

  /* question cards */
  const list = $('#list');
  list.addEventListener('click', (e) => {
    const card = e.target.closest('.qcard');
    if (!card) return;
    const act = e.target.closest('[data-act]');
    if (act) {
      if (act.dataset.act === 'edit') openForm(card.dataset.id);
      if (act.dataset.act === 'del') deleteQuestion(card.dataset.id);
      if (act.dataset.act === 'reveal') toggleAnswer(card, act);
      return;
    }
    if (browseMode) { toggleAnswer(card, card.querySelector('.link')); return; }
    if (e.target.closest('.chk')) return;
    toggleCart(card.dataset.id);
  });
  list.addEventListener('change', (e) => {
    if (e.target.matches('.chk input')) toggleCart(e.target.closest('.qcard').dataset.id);
  });

  /* modals */
  $$('.modal').forEach((m) => {
    m.addEventListener('click', (e) => { if (e.target === m) closeModal(`#${m.id}`); });
  });
  $$('[data-close]').forEach((b) => b.addEventListener('click', (e) => {
    const m = e.target.closest('.modal');
    if (m) closeModal(`#${m.id}`);
  }));

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const open = $('.modal:not([hidden])');
      if (open) closeModal(`#${open.id}`);
      closeCartPanel();
    }
  });
}

function closeCartPanel() {
  $('#cartPanel').classList.remove('open');
  $('#backdrop').hidden = true;
}

/* ---------------- demo / startup ---------------- */

function autoSelectDemo() {
  const want = { mcq: 12, wrq_k: 4, wrq_kh: 4, cq: 2 };
  state.cart = [];
  TYPE_ORDER.forEach((t) => {
    state.cart.push(...state.bank.filter((q) => q.type === t).slice(0, want[t]).map((q) => q.id));
  });
  persist();
  renderList();
  renderCart();
}

function handleQueryParams() {
  const params = new URLSearchParams(location.search);
  if (params.has('printdemo')) {
    showView('studio');
    autoSelectDemo();
    $('#printArea').innerHTML = renderPaper(cartItems(), state.settings);
  } else if (params.has('demo')) {
    showView('studio');
    autoSelectDemo();
    openPreview();
    updateLineModeUI();
    if (params.get('lines') === '1') toggleLineMode();
    if (params.get('edit') === '1') togglePreviewEdit();
  } else if (params.has('preview')) {
    showView('studio');
    openPreview();
  } else if (params.get('view') === 'studio') {
    showView('studio');
  } else if (params.get('view') === 'answers') {
    showView('answers');
  }
}

function paint() {
  refreshFilters(false);
  renderBloomOptions();
  syncSettingsToUI();
  renderList();
  renderCart();
}

async function init() {
  /* paint the shipped bank instantly, then swap in saved data if any */
  state.bank = seedBank();
  state.settings = defaultSettingsForBank();
  paint();
  bindEvents();
  showView('home');
  restoreHomePicks();
  refreshHomeClassNote();

  let saved = null;
  try {
    saved = await Promise.race([
      Storage.get(STORE_KEY),
      new Promise((resolve) => setTimeout(() => resolve(null), 1200)),
    ]);
  } catch (_) { /* ignore */ }

  if (saved && Array.isArray(saved.bank) && saved.bank.length) {
    const seed = seedBank();
    const seedVersion = (SEED.meta && SEED.meta.bank_version) || 0;
    const savedVersion = (saved.meta && saved.meta.bank_version) || 0;

    if (savedVersion && savedVersion !== seedVersion) {
      /* data format/bank changed: replace persisted questions with the
         embedded seed so a rebuilt bank never stacks on top of an old one */
      state.bank = seed.slice();
    } else {
      /* same bank version: dedupe persisted content and merge new seed items */
      const dedupeSaved = [];
      const savedStems = new Set();
      saved.bank.forEach((q) => {
        const key = normStem(q.stem) + '|' + q.type;
        if (!savedStems.has(key)) { savedStems.add(key); dedupeSaved.push(q); }
      });
      const merged = dedupeSaved.slice();
      seed.forEach((q) => {
        const key = normStem(q.stem) + '|' + q.type;
        if (!savedStems.has(key)) merged.push(q);
      });
      state.bank = merged;
    }
    state.papers = Array.isArray(saved.papers) ? saved.papers : [];
    state.settings = { ...DEFAULT_SETTINGS, ...(saved.settings || {}) };
    state.cart = Array.isArray(saved.cart) ? saved.cart : [];
    state.cart = state.cart.filter((id) => state.bank.some((q) => q.id === id));
    paint();
    restoreHomePicks();
    refreshHomeClassNote();
  }

  handleQueryParams();
  persist();
}

document.addEventListener('DOMContentLoaded', init);
