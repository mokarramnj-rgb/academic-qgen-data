'use strict';

/* ============================================================
   Question Paper Studio — core (state, storage, filters, lists)
   ============================================================ */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[c]));

const BND = '০১২৩৪৫৬৭৮৯';
const bn = (v) => String(v ?? '').replace(/\d/g, (d) => BND[+d]);
const OPT = ['ক', 'খ', 'গ', 'ঘ'];
const MLAB = ['ক', 'খ', 'গ', 'ঘ', 'ঙ', 'চ', 'ছ', 'জ'];

const TYPES = {
  mcq:    { label: 'MCQ', cls: 'mcq', name: 'বহুনির্বাচনী', defMarks: 1 },
  fill:   { label: 'শূন্যস্থান', cls: 'fill', name: 'শূন্যস্থান পূরণ', defMarks: 1 },
  tf:     { label: 'শুদ্ধ/অশুদ্ধ', cls: 'tf', name: 'শুদ্ধ/অশুদ্ধ', defMarks: 1 },
  match:  { label: 'মিলকরণ', cls: 'match', name: 'মিলকরণ', defMarks: 1 },
  wrq_k:  { label: 'জ্ঞানমূলক', cls: 'k', name: 'জ্ঞানমূলক', defMarks: 1 },
  wrq_kh: { label: 'অনুধাবনমূলক', cls: 'kh', name: 'অনুধাবনমূলক', defMarks: 2 },
  cq:     { label: 'সৃজনশীল', cls: 'cq', name: 'সৃজনশীল', defMarks: 10 },
};

const TYPE_ORDER = ['mcq', 'fill', 'tf', 'match', 'wrq_k', 'wrq_kh', 'cq'];

/* Question types each class actually uses. A class without an entry falls
   back to whatever types its downloaded bank contains. */
const CLASS_TYPES = {
  '3': ['mcq', 'fill', 'tf', 'match', 'wrq_k', 'cq'],
};

function typesForClass(cls) {
  const key = String(cls || '');
  if (CLASS_TYPES[key]) return CLASS_TYPES[key].slice();
  const seen = new Set(
    state.bank.filter((q) => !key || String(q.class_name) === key).map((q) => q.type),
  );
  return TYPE_ORDER.filter((t) => seen.has(t));
}

const BLOOM = {
  remember: 'স্মরণ', understand: 'অনুধাবন', apply: 'প্রয়োগ', analyze: 'বিশ্লেষণ',
};

const SEED = JSON.parse($('#seed').textContent);

const DEFAULT_SETTINGS = {
  title: 'প্রশ্নপত্র',
  exam_name: '',
  institute: '',
  class_label: 'অষ্টম শ্রেণি',
  subject: 'বিজ্ঞান',
  time: '২ ঘণ্টা',
  date: '',
  instructions: [
    'প্রশ্নপত্রে মোট প্রদত্ত নম্বরের বিপরীতে উত্তর দিতে হবে।',
    'বহুনির্বাচনী প্রশ্নের একটিমাত্র উত্তর সঠিক; উত্তরপত্রে সঠিক উত্তরটি লেখো।',
    'প্রতিটি প্রশ্নের পাশে নম্বর উল্লেখ করা আছে।',
  ],
  answer_key: true,
  group: true,
};

const STORE_KEY = 'qpstudio.v1';

const state = {
  bank: [],
  papers: [],
  settings: { ...DEFAULT_SETTINGS },
  cart: [],
};

/* home | studio | answers */
let currentView = 'home';
let browseMode = false;

/* ---------------- storage (IndexedDB → localStorage fallback) ---------------- */

const Storage = (() => {
  let dbPromise = null;

  function openDb() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise((resolve, reject) => {
      if (!('indexedDB' in window)) return reject(new Error('no indexedDB'));
      const req = indexedDB.open('qpstudio', 1);
      req.onupgradeneeded = () => {
        if (!req.result.objectStoreNames.contains('kv')) req.result.createObjectStore('kv');
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error || new Error('indexedDB error'));
    });
    return dbPromise;
  }

  async function idbGet(key) {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('kv', 'readonly');
      const req = tx.objectStore('kv').get(key);
      req.onsuccess = () => resolve(req.result ?? null);
      req.onerror = () => reject(req.error);
    });
  }

  async function idbSet(key, value) {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('kv', 'readwrite');
      tx.objectStore('kv').put(value, key);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  return {
    async get(key) {
      /* localStorage first: synchronous and reliable for file:// URLs.
         IndexedDB is tried afterwards as a secondary store. */
      try {
        const raw = localStorage.getItem(key);
        if (raw) return JSON.parse(raw);
      } catch (_) { /* fall through */ }
      try {
        const v = await idbGet(key);
        if (v != null) return v;
      } catch (_) { /* fall through */ }
      return null;
    },
    async set(key, value) {
      /* localStorage first: synchronous and reliable for file:// URLs */
      try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
      } catch (_) {
        try {
          await idbSet(key, value);
          return true;
        } catch (_) {
          return false;
        }
      }
    },
  };
})();

let saveTimer = null;
function persist() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(async () => {
    const ok = await Storage.set(STORE_KEY, {
      v: 1, bank: state.bank, papers: state.papers,
      settings: state.settings, cart: state.cart,
      bank_version: (SEED.meta && SEED.meta.bank_version) || 0,
    });
    if (!ok) toast('সংরক্ষণ করা যায়নি — ব্রাউজারের স্টোরেজ পূর্ণ হতে পারে');
  }, 250);
}

/* ---------------- seed & defaults ---------------- */

function seedBank() {
  const m = SEED.meta || {};
  const cmap = m.cm || m.chapter_map || {};
  return (SEED.questions || []).map((q) => {
    const ch = String(q.chapter || m.chapter || '');
    return {
      options: [],
      subquestions: [],
      stimulus: '',
      explanation: '',
      answer_index: null,
      left: [],
      right: [],
      answer_key: [],
      answer_bool: null,
      ...q,
      class_name: String(q.class_name || m.class_name || ''),
      subject: q.subject || m.subject || '',
      chapter: ch,
      chapter_title: q.chapter_title || cmap[ch] || m.chapter_title || '',
      page: q.page ?? m.page ?? null,
      source: q.source || m.source || 'NCTB',
      bloom: q.bloom || 'remember',
      difficulty: Math.min(3, Math.max(1, Number(q.difficulty) || 1)),
    };
  });
}

function defaultSettingsForBank() {
  const first = state.bank[0];
  return {
    ...DEFAULT_SETTINGS,
    class_label: first ? classLabel(first.class_name) : DEFAULT_SETTINGS.class_label,
    subject: first ? first.subject : DEFAULT_SETTINGS.subject,
  };
}

function classLabel(c) {
  const map = {
    '1': 'প্রথম শ্রেণি', '2': 'দ্বিতীয় শ্রেণি', '3': 'তৃতীয় শ্রেণি', '4': 'চতুর্থ শ্রেণি',
    '5': 'পঞ্চম শ্রেণি', '6': 'ষষ্ঠ শ্রেণি', '7': 'সপ্তম শ্রেণি', '8': 'অষ্টম শ্রেণি',
    '9': 'নবম শ্রেণি', '10': 'দশম শ্রেণি',
  };
  return map[String(c)] || (`শ্রেণি ${bn(c)}`);
}

/* ---------------- filters ---------------- */

function normStem(s) {
  return String(s ?? '').toLowerCase()
    .replace(/[^\w\u0980-\u09FF]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function uniqueSorted(values) {
  return [...new Set(values.filter((v) => v !== '' && v != null))].sort((a, b) => {
    const na = Number(a), nb = Number(b);
    if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
    return String(a).localeCompare(String(b), 'bn');
  });
}

function fillSelect(sel, entries) {
  const current = sel.value;
  sel.innerHTML = entries.map(([value, label]) => `<option value="${esc(value)}">${esc(label)}</option>`).join('');
  if (entries.some(([v]) => v === current)) sel.value = current;
}

function refreshFilters(keep = true) {
  const clsSel = $('#fClass');
  const subSel = $('#fSubject');
  const chSel = $('#fChapter');
  const prev = keep ? { c: clsSel.value, s: subSel.value, ch: chSel.value } : { c: '', s: '', ch: '' };

  const classes = uniqueSorted(state.bank.map((q) => q.class_name));
  fillSelect(clsSel, [['', 'সব শ্রেণি'], ...classes.map((c) => [c, classLabel(c)])]);
  if (keep && classes.includes(prev.c)) clsSel.value = prev.c;

  const scoped = state.bank.filter((q) => !clsSel.value || q.class_name === clsSel.value);
  const subjects = uniqueSorted(scoped.map((q) => q.subject));
  fillSelect(subSel, [['', 'সব বিষয়'], ...subjects.map((s) => [s, s])]);
  if (keep && subjects.includes(prev.s)) subSel.value = prev.s;

  const scoped2 = scoped.filter((q) => !subSel.value || q.subject === subSel.value);
  const chapters = [];
  const seen = new Set();
  scoped2.forEach((q) => {
    const key = String(q.chapter);
    if (seen.has(key)) return;
    seen.add(key);
    chapters.push([key, q.chapter_title ? `${bn(key)}. ${q.chapter_title}` : `অধ্যায় ${bn(key)}`]);
  });
  chapters.sort((a, b) => Number(a[0]) - Number(b[0]));
  fillSelect(chSel, [['', 'সব অধ্যায়'], ...chapters]);
  if (keep && chapters.some(([v]) => v === prev.ch)) chSel.value = prev.ch;

  renderBloomOptions();
}

function renderBloomOptions() {
  const sel = $('#fBloom');
  const cur = sel.value;
  const options = [['', 'সব স্তর'], ...Object.entries(BLOOM).map(([k, v]) => [k, v])];
  sel.innerHTML = options.map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join('');
  if (options.some(([v]) => v === cur)) sel.value = cur;
}

function activeTypes() {
  return $$('#fTypes .chip.on').map((b) => b.dataset.type);
}

function activeDifficulties() {
  return $$('#fDifficulty .chip.on').map((b) => Number(b.dataset.diff)).filter(Boolean);
}

function currentPool() {
  const cls = $('#fClass').value;
  const sub = $('#fSubject').value;
  const ch = $('#fChapter').value;
  const types = activeTypes();
  const diffs = activeDifficulties();
  const bloom = $('#fBloom').value;
  const text = $('#fSearch').value.trim().toLowerCase();

  return state.bank.filter((q) => {
    if (cls && q.class_name !== cls) return false;
    if (sub && q.subject !== sub) return false;
    if (ch && String(q.chapter) !== ch) return false;
    if (types.length && !types.includes(q.type)) return false;
    if (diffs.length && !diffs.includes(Number(q.difficulty || 1))) return false;
    if (bloom && q.bloom !== bloom) return false;
    if (text) {
      const hay = [q.stem, q.answer_text, q.stimulus, ...(q.options || [])].join(' ').toLowerCase();
      if (!hay.includes(text)) return false;
    }
    return true;
  });
}

/* ---------------- bank list ---------------- */

function matchAnswerText(q) {
  const key = Array.isArray(q.answer_key) ? q.answer_key : [];
  return key.map((r, i) => `${MLAB[i] || i + 1}→${bn(Number(r) + 1)}`).join(', ');
}

function cardHTML(q) {
  const t = TYPES[q.type] || TYPES.mcq;
  const sel = state.cart.includes(q.id);
  const opts = (q.type === 'mcq' && q.options && q.options.length)
    ? `<div class="q-opts">${q.options.map((o, i) => `<div><span class="ol">${OPT[i]}.</span> ${esc(o)}</div>`).join('')}</div>`
    : '';
  const match = q.type === 'match'
    ? `<div class="q-match">
        <div>${(q.left || []).map((x, i) => `<div><span class="ol">${MLAB[i] || i + 1}.</span> ${esc(x)}</div>`).join('')}</div>
        <div>${(q.right || []).map((x, i) => `<div><span class="ol">${bn(i + 1)}.</span> ${esc(x)}</div>`).join('')}</div>
      </div>`
    : '';
  const stim = (q.type === 'cq' && q.stimulus) ? `<div class="q-stim">${esc(q.stimulus)}</div>` : '';
  const subs = (q.type === 'cq' && q.subquestions && q.subquestions.length)
    ? `<div class="q-subs">${q.subquestions.map((s) => `<div><b>${esc(s.label)}.</b> ${esc(s.text)}</div>`).join('')}</div>`
    : '';
  const idx = q.answer_index;
  const ans = q.type === 'mcq'
    ? (idx >= 1 && idx <= 4 ? `${OPT[idx - 1]}. ${esc((q.options || [])[idx - 1] || '')}` : '—')
    : q.type === 'match'
      ? esc(matchAnswerText(q) || '—')
      : q.type === 'tf'
        ? esc(q.answer_text || (q.answer_bool === true ? 'শুদ্ধ' : q.answer_bool === false ? 'অশুদ্ধ' : '—'))
        : esc(q.answer_text || '—');
  const diff = Math.min(3, Math.max(1, Number(q.difficulty) || 1));
  const diffName = ['', 'সহজ', 'মধ্যম', 'কঠিন'][diff];

  return `<article class="qcard ${sel ? 'sel' : ''} ${browseMode ? 'showans' : ''}" data-id="${esc(q.id)}">
    <div class="qtop">
      <label class="chk"><input type="checkbox" ${sel ? 'checked' : ''} aria-label="নির্বাচন"></label>
      <span class="badge ${t.cls}">${t.name}</span>
      <span class="pill">${bn(q.marks)} নম্বর</span>
      <span class="pill ghost">${esc(BLOOM[q.bloom] || q.bloom || '')}</span>
      <span class="pill diff${diff}">${esc(diffName)}</span>
      <span class="src">অধ্যায় ${bn(q.chapter || '—')} · পৃষ্ঠা ${bn(q.page ?? '—')}</span>
      <span class="spacer"></span>
      <button class="icon" data-act="edit" title="সম্পাদনা">✎</button>
      <button class="icon danger" data-act="del" title="মুছুন">✕</button>
    </div>
    <div class="stem">${esc(q.stem)}</div>
    ${stim}${subs}${match}${opts}
    <div class="answer"><b>উত্তর:</b> ${ans}</div>
    <button class="link" data-act="reveal">${browseMode ? 'উত্তর লুকাও' : 'উত্তর দেখাও'}</button>
  </article>`;
}

function renderList() {
  const pool = currentPool();
  const list = $('#list');
  list.innerHTML = pool.length
    ? pool.map(cardHTML).join('')
    : '<div class="empty"><div class="big">🔍</div><div>এই ফিল্টারে কোনো প্রশ্ন নেই।</div><div style="font-size:12px;margin-top:6px">ফিল্টার বদলান, অথবা “নতুন প্রশ্ন” যোগ করুন।</div></div>';

  $('#shownCount').textContent = bn(pool.length);
  $('#totalCount').textContent = bn(state.bank.length);
  $('#statTotal').textContent = bn(state.bank.length);
  $('#statShown').textContent = bn(pool.length);
  updateCartStats();
}

function selectAllFiltered() {
  const pool = currentPool();
  const set = new Set(state.cart);
  pool.forEach((q) => set.add(q.id));
  state.cart = [...set];
  persist();
  renderList();
  renderCart();
}

function clearCart() {
  state.cart = [];
  persist();
  renderList();
  renderCart();
}

/* ---------------- cart ---------------- */

function cartItems() {
  return state.cart.map((id) => state.bank.find((q) => q.id === id)).filter(Boolean);
}

function cartMarks() {
  return cartItems().reduce((sum, q) => sum + Number(q.marks || 0), 0);
}

function toggleCart(id) {
  const i = state.cart.indexOf(id);
  if (i >= 0) state.cart.splice(i, 1);
  else state.cart.push(id);
  persist();

  const card = document.querySelector(`.qcard[data-id="${cssEscape(id)}"]`);
  if (card) {
    const on = state.cart.includes(id);
    card.classList.toggle('sel', on);
    const cb = card.querySelector('.chk input');
    if (cb) cb.checked = on;
  }
  renderCart();
}

function removeCart(id) {
  state.cart = state.cart.filter((x) => x !== id);
  persist();
  renderCart();
  const card = document.querySelector(`.qcard[data-id="${cssEscape(id)}"]`);
  if (card) {
    card.classList.remove('sel');
    const cb = card.querySelector('.chk input');
    if (cb) cb.checked = false;
  }
}

function moveCart(id, delta) {
  const i = state.cart.indexOf(id);
  const j = i + delta;
  if (i < 0 || j < 0 || j >= state.cart.length) return;
  [state.cart[i], state.cart[j]] = [state.cart[j], state.cart[i]];
  persist();
  renderCart();
}

function renderCart() {
  const items = cartItems();
  const list = $('#cartList');
  list.innerHTML = items.map((q, i) => `<li class="crow" data-id="${esc(q.id)}">
      <span class="n">${bn(i + 1)}</span>
      <span class="t" title="${esc(q.stem)}">${esc(q.stem)}</span>
      <span class="m">${bn(q.marks)}</span>
      <button data-act="up" title="উপরে">↑</button>
      <button data-act="down" title="নিচে">↓</button>
      <button data-act="rm" title="সরাও">✕</button>
    </li>`).join('');
  $('#cartEmpty').hidden = items.length > 0;
  updateCartStats();
  $('#barCount').textContent = bn(items.length);
  $('#barMarks').textContent = bn(cartMarks());
}

function updateCartStats() {
  const items = cartItems();
  $('#cartMarks').textContent = bn(cartMarks());
  $('#statSel').textContent = bn(items.length);
  $('#statMarks').textContent = bn(cartMarks());
}

function cssEscape(s) {
  if (window.CSS && CSS.escape) return CSS.escape(s);
  return String(s).replace(/["\\]/g, '\\$&');
}

/* ---------------- misc ---------------- */

let toastTimer = null;
function toast(msg) {
  const el = $('#toast');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 2400);
}

function download(filename, text) {
  const blob = new Blob([text], { type: 'application/json;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

function debounce(fn, ms = 150) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}
