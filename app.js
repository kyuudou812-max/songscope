/* =====================================================================
 * SongScope v0.2 Phase D2 Diagnostic  —  歌唱録音レビュー・解析アプリ
 *
 * 思想:
 *   観測された事実 と 解釈・評価 を分離する。
 *   このアプリは測定器であり、歌の先生ではない。
 *   推定できないものは null にする。それらしい数値を作らない。
 * ===================================================================== */
'use strict';

const APP_VERSION = '0.2.0-phaseD2diag';
const SCHEMA_VERSION = '0.6.2';
const BUILD_ID = '20260810-d2diag-03';
const SONG_IDENTITY_VERSION = 'title_artist_nfkc_v1';
const ALIGN_FEATURE_VERSION = 'stft-chroma-log-l2-smooth-v1';
const ALIGN_MATCH_VERSION = 'global-offset-coarse-refine-v2';

const TAGS = ['高音', '低音', 'リズム', '歌詞', '譜割り', '息', '力み', '音程',
  '語尾', '発音', '表現', '違和感', '良かった', '好き', 'その他'];
const GOOD_TAGS = new Set(['良かった', '好き']);
const ALERT_TAGS = new Set(['違和感']);

const DEFAULT_SETTINGS = {
  frameSizeMs: 40,
  hopSizeMs: 20,
  analysisSampleRate: 22050,
  f0MinHz: 65,
  f0MaxHz: 1200,
  minimumConfidence: 0.55,
  // Phase A-1: 既存の表示/互換閾値とは分離した比較利用候補用の暫定閾値。
  usableF0MinConfidence: 0.70,
  usableF0MinVoicedProbability: 0.45,
  f0IsolatedOutlierWindowFrames: 2,
  f0IsolatedOutlierThresholdCent: 700,
  // Phase A-3: F0を訂正せず、短時間に競合する整数比候補を『曖昧性』として記録する。
  f0AmbiguityLocalWindowSec: 0.12,
  f0AmbiguityRapidWindowSec: 0.04,
  f0AmbiguityRatioToleranceCent: 50,
  yinThreshold: 0.15,
  loudnessReference: 'p95_of_frame_rms_db',
  spectrogramMaxHz: 8000,
  activeSegmentMinDurSec: 0.12,
  activeSegmentMergeGapSec: 0.15,
  recordingSetupPreset: 'カラオケ標準（iPhoneをテーブル・画面上向き・本人から約50cm）'
};

/* ---------------- 小道具 ---------------- */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
const clamp = (v, a, b) => v < a ? a : (v > b ? b : v);
const nowIso = () => new Date().toISOString();

function uid(prefix) {
  const rnd = (self.crypto && crypto.randomUUID) ? crypto.randomUUID().replace(/-/g, '').slice(0, 12)
    : Math.random().toString(36).slice(2, 14);
  return prefix + '_' + Date.now().toString(36) + rnd;
}
function fmtTime(sec, withTenths = true) {
  if (!isFinite(sec) || sec < 0) sec = 0;
  const m = Math.floor(sec / 60);
  const s = sec - m * 60;
  return withTenths
    ? `${m}:${s < 10 ? '0' : ''}${s.toFixed(1)}`
    : `${m}:${String(Math.floor(s)).padStart(2, '0')}`;
}
function fmtClock(sec) { // 00:42.3 形式（report/CSV用）
  if (!isFinite(sec)) return '';
  const m = Math.floor(sec / 60), s = sec - m * 60;
  return `${String(m).padStart(2, '0')}:${s < 10 ? '0' : ''}${s.toFixed(1)}`;
}
function fmtDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d)) return '';
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}
function fmtBytes(n) {
  if (!isFinite(n)) return '—';
  const u = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return n.toFixed(i ? 1 : 0) + ' ' + u[i];
}
function num(v, d = 2) { return (v === null || v === undefined || !isFinite(v)) ? '' : Number(v).toFixed(d); }
async function sha256Hex(arrayBuffer) {
  if (!self.crypto || !crypto.subtle) throw new Error('SHA-256 unavailable');
  const digest = await crypto.subtle.digest('SHA-256', arrayBuffer);
  return Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, '0')).join('');
}

function normalizeSongIdentityText(value) {
  return String(value || '').normalize('NFKC').trim().replace(/\s+/g, ' ').toLocaleLowerCase('ja-JP');
}
async function deriveSongIdentity(title, artist) {
  const normalizedTitle = normalizeSongIdentityText(title);
  const normalizedArtist = normalizeSongIdentityText(artist);
  const basis = normalizedArtist ? 'normalized_title_artist' : 'normalized_title_only';
  const key = SONG_IDENTITY_VERSION + '\n' + normalizedTitle + '\n' + normalizedArtist;
  const bytes = new TextEncoder().encode(key);
  const hash = await sha256Hex(bytes.buffer);
  return {
    // songIdentityKey は現在のメタデータから再計算できる「照合キー」。編集で変わり得る。
    // songId は録音を束ねる永続IDなので、既存録音の編集時には再計算しない。
    songIdentityKey: 'skey_' + hash.slice(0, 24),
    defaultSongId: 'song_' + hash.slice(0, 24),
    songIdentityVersion: SONG_IDENTITY_VERSION,
    songIdentityBasis: basis,
    normalizedTitle,
    normalizedArtist
  };
}
function applySongIdentityFields(rec, identity) {
  if (!rec || !identity) return rec;
  rec.songIdentityKey = identity.songIdentityKey || null;
  rec.songIdentityVersion = identity.songIdentityVersion || null;
  rec.songIdentityBasis = identity.songIdentityBasis || null;
  rec.normalizedTitle = identity.normalizedTitle || '';
  rec.normalizedArtist = identity.normalizedArtist || '';
  return rec;
}
function recordingIdFromAudioHash(hash) {
  return hash ? 'rec_' + String(hash).slice(0, 24) : uid('rec');
}
function compactAnalysisHistoryEntry(an) {
  if (!an || !an.analysisId) return null;
  return {
    analysisId: an.analysisId,
    recordingId: an.recordingId,
    schemaVersion: an.schemaVersion || null,
    appVersion: an.appVersion || null,
    buildId: an.buildId || null,
    audioSha256: an.audioSha256 || null,
    audioHashAlgorithm: an.audioHashAlgorithm || 'SHA-256',
    createdAt: an.createdAt || null,
    updatedAt: an.updatedAt || null,
    supersedesAnalysisId: an.supersedesAnalysisId || null,
    settings: an.settings || null,
    engine: an.engine || null,
    summary: an.summary || null
  };
}
function safeName(s) {
  return String(s || 'recording').replace(/[\\/:*?"<>|\s]+/g, '_').slice(0, 40) || 'recording';
}
function haptic() {
  try { if (navigator.vibrate) navigator.vibrate(12); } catch (e) { /* 非対応は無視 */ }
}
let toastTimer = null;
function toast(msg, ms = 2200) {
  const el = $('#toast');
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, ms);
}

/* ---------------- 設定（localStorageは軽量データのみ） ---------------- */
let settings = Object.assign({}, DEFAULT_SETTINGS);
function loadSettings() {
  try {
    const raw = localStorage.getItem('songscope.settings');
    if (raw) settings = Object.assign({}, DEFAULT_SETTINGS, JSON.parse(raw));
  } catch (e) { settings = Object.assign({}, DEFAULT_SETTINGS); }
}
function saveSettings() {
  try { localStorage.setItem('songscope.settings', JSON.stringify(settings)); }
  catch (e) { toast('設定を保存できませんでした'); }
}
function getFlag(key, def) {
  try { const v = localStorage.getItem('songscope.' + key); return v === null ? def : v === '1'; }
  catch (e) { return def; }
}
function setFlag(key, val) {
  try { localStorage.setItem('songscope.' + key, val ? '1' : '0'); } catch (e) { }
}

/* ---------------- IndexedDB ---------------- */
const DB_NAME = 'songscope';
const DB_VER = 5;
let dbp = null;

const DB_BLOCKED_CODE = 'SONGSCOPE_DB_UPGRADE_BLOCKED';
function makeDbBlockedError() {
  const e = new Error('SongScopeのデータベース更新が、別のSongScope画面によって待機中です。');
  e.code = DB_BLOCKED_CODE;
  return e;
}
function isDbBlockedError(e) { return !!(e && e.code === DB_BLOCKED_CODE); }
function dbBlockedUserMessage() {
  return 'SongScopeの別画面が開いたままの可能性があります。SafariのSongScopeタブとホーム画面版SongScopeをすべて閉じてから、もう一度開いてください。録音データは削除しないでください。';
}
function db() {
  if (dbp) return dbp;
  dbp = new Promise((res, rej) => {
    const req = indexedDB.open(DB_NAME, DB_VER);
    let settled = false;
    let blockedTimer = null;
    req.onupgradeneeded = () => {
      const d = req.result;
      const tx = req.transaction;
      let recordings;
      if (!d.objectStoreNames.contains('recordings')) {
        recordings = d.createObjectStore('recordings', { keyPath: 'recordingId' });
      } else recordings = tx.objectStore('recordings');
      if (!recordings.indexNames.contains('byAudioSha256')) recordings.createIndex('byAudioSha256', 'audioSha256', { unique: false });
      if (!recordings.indexNames.contains('bySongId')) recordings.createIndex('bySongId', 'songId', { unique: false });
      if (!recordings.indexNames.contains('bySongIdentityKey')) recordings.createIndex('bySongIdentityKey', 'songIdentityKey', { unique: false });

      if (!d.objectStoreNames.contains('audio')) d.createObjectStore('audio', { keyPath: 'recordingId' });
      if (!d.objectStoreNames.contains('analysis')) d.createObjectStore('analysis', { keyPath: 'recordingId' }); // latest full analysis (compatibility)
      if (!d.objectStoreNames.contains('analysisHistory')) {
        const h = d.createObjectStore('analysisHistory', { keyPath: 'analysisId' });
        h.createIndex('byRec', 'recordingId', { unique: false });
        h.createIndex('byAudioSha256', 'audioSha256', { unique: false });
      }
      if (!d.objectStoreNames.contains('markers')) {
        d.createObjectStore('markers', { keyPath: 'markerId' }).createIndex('byRec', 'recordingId', { unique: false });
      }
      if (!d.objectStoreNames.contains('segments')) {
        d.createObjectStore('segments', { keyPath: 'segmentId' }).createIndex('byRec', 'recordingId', { unique: false });
      }
      if (!d.objectStoreNames.contains('alignmentFeatures')) {
        const af = d.createObjectStore('alignmentFeatures', { keyPath: 'featureKey' });
        af.createIndex('byAudioSha256', 'audioSha256', { unique: false });
      }
      if (!d.objectStoreNames.contains('alignmentDiagnostics')) {
        const ad = d.createObjectStore('alignmentDiagnostics', { keyPath: 'diagnosticId' });
        ad.createIndex('byPairKey', 'pairKey', { unique: false });
      }
      if (!d.objectStoreNames.contains('alignmentResults')) {
        const ar = d.createObjectStore('alignmentResults', { keyPath: 'pairKey' });
        ar.createIndex('byStatus', 'status', { unique: false });
        ar.createIndex('byUpdatedAt', 'updatedAt', { unique: false });
      }
    };
    req.onblocked = () => {
      if (blockedTimer || settled) return;
      console.warn('IndexedDB upgrade blocked by another SongScope context.');
      blockedTimer = setTimeout(() => {
        if (settled) return;
        settled = true;
        dbp = null;
        rej(makeDbBlockedError());
      }, 1500);
    };
    req.onsuccess = () => {
      if (blockedTimer) clearTimeout(blockedTimer);
      const d = req.result;
      d.onversionchange = () => {
        try { d.close(); } catch (e) { }
        dbp = null;
        const msg = 'SongScopeが更新されました。処理中でなければ、この画面を開き直してください。';
        try { toast(msg); } catch (e) { console.warn(msg); }
      };
      // blocked timeout後に古いopen要求が遅れて成功した場合は、接続を残さない。
      if (settled) { try { d.close(); } catch (e) { } return; }
      settled = true;
      res(d);
    };
    req.onerror = () => {
      if (blockedTimer) clearTimeout(blockedTimer);
      if (settled) return;
      settled = true;
      dbp = null;
      rej(req.error);
    };
  });
  return dbp;
}
async function txDo(store, mode, fn) {
  const d = await db();
  return new Promise((res, rej) => {
    const tx = d.transaction(store, mode);
    const os = tx.objectStore(store);
    let out;
    try { out = fn(os); } catch (e) { rej(e); return; }
    tx.oncomplete = () => res(out && typeof out === 'object' && 'readyState' in out ? out.result : out);
    tx.onerror = () => rej(tx.error);
    tx.onabort = () => rej(tx.error || new Error('transaction aborted'));
  });
}
const dbPut = (store, val) => txDo(store, 'readwrite', os => os.put(val));
const dbGet = (store, key) => txDo(store, 'readonly', os => os.get(key));
const dbDel = (store, key) => txDo(store, 'readwrite', os => os.delete(key));
const dbAll = (store) => txDo(store, 'readonly', os => os.getAll());
const dbByRec = (store, recId) => txDo(store, 'readonly', os => os.index('byRec').getAll(IDBKeyRange.only(recId)));
const dbByIndex = (store, indexName, value) => txDo(store, 'readonly', os => os.index(indexName).getAll(IDBKeyRange.only(value)));

async function dbDelByRec(store, recId) {
  const rows = await dbByRec(store, recId);
  const key = store === 'markers' ? 'markerId' : store === 'segments' ? 'segmentId' : 'analysisId';
  for (const r of rows) await dbDel(store, r[key]);
}
async function findRecordingsByAudioHash(hash) {
  if (!hash) return [];
  try { return await dbByIndex('recordings', 'byAudioSha256', hash); }
  catch (e) {
    const rows = await dbAll('recordings');
    return rows.filter(r => r.audioSha256 === hash);
  }
}
async function findRecordingsBySongId(songId) {
  if (!songId) return [];
  try { return await dbByIndex('recordings', 'bySongId', songId); }
  catch (e) {
    const rows = await dbAll('recordings');
    return rows.filter(r => r.songId === songId);
  }
}
async function findRecordingsBySongIdentityKey(songIdentityKey) {
  if (!songIdentityKey) return [];
  try { return await dbByIndex('recordings', 'bySongIdentityKey', songIdentityKey); }
  catch (e) {
    const rows = await dbAll('recordings');
    return rows.filter(r => r.songIdentityKey === songIdentityKey);
  }
}
async function migrateBliteIdentityData() {
  const recs = await dbAll('recordings');
  for (const rec of recs) {
    let changed = false;
    let an = null;
    try { an = await dbGet('analysis', rec.recordingId); } catch (e) { }
    if (!rec.audioSha256 && an && an.audioSha256) {
      rec.audioSha256 = an.audioSha256;
      rec.audioHashAlgorithm = an.audioHashAlgorithm || 'SHA-256';
      changed = true;
    }
    if (rec.audioSha256 && !rec.recordingIdentityBasis) {
      rec.recordingIdentityBasis = rec.recordingId === recordingIdFromAudioHash(rec.audioSha256)
        ? 'audio_sha256_prefix_v1' : 'legacy_id_preserved_audio_sha256';
      changed = true;
    }
    if (!rec.songIdentityKey || !rec.songIdentityVersion) {
      try {
        const identity = await deriveSongIdentity(rec.title, rec.artist);
        applySongIdentityFields(rec, identity);
        // 既存の songId は永続IDとして保存。未採番の旧データだけ初回採番する。
        if (!rec.songId) rec.songId = identity.defaultSongId;
        changed = true;
      } catch (e) { }
    } else if (!rec.songId) {
      try {
        const identity = await deriveSongIdentity(rec.title, rec.artist);
        rec.songId = identity.defaultSongId;
        changed = true;
      } catch (e) { }
    }
    if (an && an.analysisId) {
      const hist = compactAnalysisHistoryEntry(an);
      if (hist) await dbPut('analysisHistory', hist).catch(() => { });
      if (!rec.latestAnalysisId) { rec.latestAnalysisId = an.analysisId; changed = true; }
    }
    try {
      const histRows = await dbByRec('analysisHistory', rec.recordingId);
      if (rec.analysisCount !== histRows.length) { rec.analysisCount = histRows.length; changed = true; }
    } catch (e) { }
    if (changed) {
      rec.updatedAt = rec.updatedAt || nowIso();
      await dbPut('recordings', rec);
    }
  }
}

/* ---------------- ストレージ状況 ---------------- */
async function refreshStorageEstimate() {
  const el = $('#storage-est');
  if (!el) return;
  try {
    if (navigator.storage && navigator.storage.estimate) {
      const est = await navigator.storage.estimate();
      let persisted = false;
      if (navigator.storage.persisted) persisted = await navigator.storage.persisted();
      el.textContent = `使用中 ${fmtBytes(est.usage || 0)} / 割当 ${fmtBytes(est.quota || 0)}　永続化: ${persisted ? '有効' : '未設定'}`;
    } else {
      el.textContent = 'このブラウザでは保存容量を確認できません。';
    }
  } catch (e) { el.textContent = ''; }
}

/* ---------------- シート制御 ---------------- */
function openSheet(id) {
  $('#sheet-wrap').hidden = false;
  $$('.sheet').forEach(s => { s.hidden = s.id !== id; });
}
function closeSheet() {
  $('#sheet-wrap').hidden = true;
  $$('.sheet').forEach(s => { s.hidden = true; });
}
function busy(title, msg, pct) {
  $('#busy-title').textContent = title;
  $('#busy-msg').textContent = msg || '';
  $('#busy-bar').style.width = (pct || 0) + '%';
  openSheet('sheet-busy');
}

/* ---------------- ファイル保存（iOSは共有シート優先） ---------------- */
async function saveBlob(blob, filename) {
  const file = new File([blob], filename, { type: blob.type || 'application/octet-stream' });
  try {
    if (navigator.canShare && navigator.canShare({ files: [file] }) && navigator.share) {
      await navigator.share({ files: [file], title: filename });
      return 'shared';
    }
  } catch (e) {
    if (e && e.name === 'AbortError') return 'cancelled';
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 4000);
  return 'downloaded';
}

/* =====================================================================
 * 状態
 * ===================================================================== */
const state = {
  recordings: [],
  rec: null,           // 現在レビュー中の録音メタ
  analysis: null,      // 現在の解析結果
  markers: [],
  segments: [],
  audio: null,         // HTMLAudioElement
  audioUrl: null,
  loop: { a: null, b: null, on: false },
  pitchUnit: 'hz',
  specTopHz: 8000,
  confMin: DEFAULT_SETTINGS.minimumConfidence,
  pendingFile: null,   // 追加待ちのファイル
  editingRec: false,
  markerDraft: null,   // {timeSec, tag, memo, markerId?}
  segmentDraft: null,
  worker: null,
  analyzing: false,
  rafId: 0
};

/* =====================================================================
 * ホーム画面
 * ===================================================================== */
function showView(id) {
  $$('.view').forEach(v => v.classList.toggle('is-active', v.id === id));
  window.scrollTo(0, 0);
}

async function loadRecordings() {
  let list = [];
  try { list = await dbAll('recordings'); }
  catch (e) { toast('保存データを読み込めませんでした'); }
  list.sort((a, b) => String(b.updatedAt).localeCompare(String(a.updatedAt)));
  state.recordings = list;
  renderHome();
}

function statusPill(rec) {
  if (rec.analysisStatus === 'done') return '<span class="pill ok">解析済み</span>';
  if (rec.analysisStatus === 'running') return '<span class="pill wait">解析中</span>';
  if (rec.analysisStatus === 'failed') return '<span class="pill err">解析失敗</span>';
  if (rec.analysisStatus === 'unsupported') return '<span class="pill err">形式非対応</span>';
  return '<span class="pill wait">未解析</span>';
}

function renderHome() {
  const wrap = $('#recording-list');
  wrap.innerHTML = '';
  for (const rec of state.recordings) {
    const el = document.createElement('div');
    el.className = 'item';
    el.dataset.id = rec.recordingId;
    const extra = [];
    if (rec.damScore) extra.push('DAM ' + rec.damScore);
    if (rec.keyChange) extra.push('Key ' + rec.keyChange);
    el.innerHTML = `
      <div class="item-main">
        <div class="item-title">${escapeHtml(rec.title || '(無題)')}</div>
        <div class="item-sub">${fmtDate(rec.recordedAt || rec.createdAt)}　${fmtTime(rec.durationSec, false)}　レビュー ${(rec.markerCount || 0) + (rec.segmentCount || 0)}件</div>
        <div class="item-sub">${statusPill(rec)}${extra.map(x => `<span class="pill">${escapeHtml(x)}</span>`).join('')}</div>
      </div>
      <span class="icon-btn">開く ›</span>`;
    el.addEventListener('click', () => openRecording(rec.recordingId));
    wrap.appendChild(el);
  }
  $$('.app-ver').forEach(e => e.textContent = APP_VERSION + ' / ' + BUILD_ID);
}

function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/* =====================================================================
 * 録音の追加
 * ===================================================================== */
function openAddSheet(file) {
  state.pendingFile = file;
  state.editingRec = false;
  $('#rec-sheet-title').textContent = '録音を追加';
  $('#f-title').value = file ? file.name.replace(/\.[^.]+$/, '') : '';
  $('#f-artist').value = '';
  $('#f-score').value = '';
  $('#f-key').value = '';
  $('#f-octave').value = '';
  $('#f-device').value = '';
  $('#f-mode').value = '';
  $('#f-memo').value = '';
  $('#f-setup').value = settings.recordingSetupPreset;
  const d = file && file.lastModified ? new Date(file.lastModified) : new Date();
  $('#f-recat').value = toLocalInput(d);
  const det = $('#sheet-rec .details');
  if (det) det.open = false;   // 任意項目は毎回入力させない
  openSheet('sheet-rec');
}
function toLocalInput(d) {
  const p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

function openEditSheet(rec) {
  state.pendingFile = null;
  state.editingRec = true;
  $('#rec-sheet-title').textContent = '録音情報を編集';
  $('#f-title').value = rec.title || '';
  $('#f-artist').value = rec.artist || '';
  $('#f-score').value = rec.damScore || '';
  $('#f-key').value = rec.keyChange || '';
  $('#f-octave').value = rec.octave || '';
  $('#f-device').value = rec.device || '';
  $('#f-mode').value = rec.scoringMode || '';
  $('#f-memo').value = rec.memo || '';
  $('#f-setup').value = rec.recordingSetupPreset || settings.recordingSetupPreset;
  $('#f-recat').value = rec.recordedAt ? toLocalInput(new Date(rec.recordedAt)) : '';
  const det = $('#sheet-rec .details');
  if (det) det.open = true;
  openSheet('sheet-rec');
}

function readRecForm() {
  const t = $('#f-title').value.trim();
  if (!t) { toast('曲名を入力してください'); return null; }
  const at = $('#f-recat').value;
  return {
    title: t,
    artist: $('#f-artist').value.trim(),
    damScore: $('#f-score').value.trim(),
    keyChange: $('#f-key').value.trim(),
    octave: $('#f-octave').value.trim(),
    device: $('#f-device').value.trim(),
    scoringMode: $('#f-mode').value.trim(),
    memo: $('#f-memo').value.trim(),
    recordingSetupPreset: $('#f-setup').value.trim(),
    recordedAt: at ? new Date(at).toISOString() : nowIso()
  };
}

async function onRecSave() {
  const form = readRecForm();
  if (!form) return;

  if (state.editingRec && state.rec) {
    let identity = null;
    try { identity = await deriveSongIdentity(form.title, form.artist); } catch (e) { }
    Object.assign(state.rec, form, { updatedAt: nowIso() });
    if (identity) applySongIdentityFields(state.rec, identity);
    // songId は永続ID。曲名/アーティストの表記修正では変更しない。
    if (!state.rec.songId && identity) state.rec.songId = identity.defaultSongId;
    await dbPut('recordings', state.rec);
    closeSheet();
    renderReviewHeader();
    toast('保存しました');
    loadRecordings();
    return;
  }

  const file = state.pendingFile;
  if (!file) { closeSheet(); return; }
  settings.recordingSetupPreset = form.recordingSetupPreset || settings.recordingSetupPreset;
  saveSettings();

  closeSheet();
  busy('識別中', '音声の同一性を確認しています…', 10);

  // D1でDB schemaを更新するため、別タブ/旧PWAがDB接続を保持している場合は
  // IndexedDB upgradeが無期限待機になり得る。hash処理前に明示的に検出して案内する。
  try {
    await db();
  } catch (e) {
    closeSheet();
    if (isDbBlockedError(e)) { toast(dbBlockedUserMessage()); return; }
    toast('端末内データベースを開けませんでした');
    return;
  }

  let audioSha256 = null;
  let audioHashError = '';
  try {
    const hashBuffer = await file.arrayBuffer();
    audioSha256 = await sha256Hex(hashBuffer);
  } catch (e) {
    audioHashError = (e && e.message) || String(e);
  }

  let identity = null;
  try { identity = await deriveSongIdentity(form.title, form.artist); } catch (e) { }

  // 同じ原音が既にあれば、新しい「歌唱」として増やさず、その recordingId を再利用する。
  // 過去版で重複が複数作られていた場合は、最終更新が新しいものを今後のcanonicalとして使う。
  let matches = [];
  if (audioSha256) matches = await findRecordingsByAudioHash(audioSha256).catch(() => []);
  if (matches.length) {
    matches.sort((a, b) => String(b.updatedAt || b.createdAt || '').localeCompare(String(a.updatedAt || a.createdAt || '')));
    const rec = matches[0];
    // 同一音源の再解析では既存の記録日時や既入力メタデータを原則保持する。
    rec.title = form.title || rec.title;
    if (form.artist) rec.artist = form.artist;
    for (const k of ['damScore', 'keyChange', 'octave', 'device', 'scoringMode', 'memo', 'recordingSetupPreset']) {
      if (form[k]) rec[k] = form[k];
    }
    try { applySongIdentityFields(rec, await deriveSongIdentity(rec.title, rec.artist)); }
    catch (e) { if (identity) applySongIdentityFields(rec, identity); }
    // 同一録音の再解析では既存 songId を維持する。旧データで未採番なら初回だけ採番。
    if (!rec.songId && identity) rec.songId = identity.defaultSongId;
    rec.audioSha256 = audioSha256;
    rec.audioHashAlgorithm = 'SHA-256';
    rec.audioHashError = audioHashError || null;
    rec.recordingIdentityBasis = rec.recordingIdentityBasis || (rec.recordingId === recordingIdFromAudioHash(audioSha256) ? 'audio_sha256_prefix_v1' : 'legacy_id_preserved_audio_sha256');
    rec.fileName = rec.fileName || file.name;
    rec.mimeType = rec.mimeType || file.type || '';
    rec.fileSize = rec.fileSize || file.size;
    rec.analysisStatus = 'pending';
    rec.analysisError = '';
    rec.updatedAt = nowIso();
    try {
      const existingAudio = await dbGet('audio', rec.recordingId);
      if (!existingAudio || !existingAudio.blob) {
        await dbPut('audio', { recordingId: rec.recordingId, blob: file, fileName: file.name, mimeType: file.type || '', savedAt: nowIso() });
      }
      await dbPut('recordings', rec);
    } catch (e) {
      closeSheet(); toast('既存録音の更新に失敗しました'); return;
    }
    closeSheet();
    await loadRecordings();
    await openRecording(rec.recordingId);
    toast(matches.length > 1 ? `同じ音声を既存録音として再解析します（既存重複 ${matches.length}件）` : '同じ音声を既存録音として再解析します');
    startAnalysis(rec, file);
    return;
  }

  const rec = Object.assign({
    schemaVersion: SCHEMA_VERSION,
    recordingId: recordingIdFromAudioHash(audioSha256),
    performanceId: '',
    sessionId: '',
    songId: '',
    songIdentityKey: null,
    arrangementId: '',
    songIdentityVersion: null,
    songIdentityBasis: null,
    normalizedTitle: null,
    normalizedArtist: null,
    audioSha256,
    audioHashAlgorithm: 'SHA-256',
    audioHashError: audioHashError || null,
    recordingIdentityBasis: audioSha256 ? 'audio_sha256_prefix_v1' : 'random_id_hash_unavailable',
    latestAnalysisId: null,
    analysisCount: 0,
    fileName: file.name,
    mimeType: file.type || '',
    fileSize: file.size,
    durationSec: 0,
    sampleRate: null,
    channels: null,
    analysisStatus: 'pending',
    analysisError: '',
    markerCount: 0,
    segmentCount: 0,
    createdAt: nowIso(),
    updatedAt: nowIso()
  }, form);
  if (identity) {
    applySongIdentityFields(rec, identity);
    // 同じ正規化メタデータの既存録音があれば、その永続 songId を再利用する。
    const sameSong = await findRecordingsBySongIdentityKey(identity.songIdentityKey).catch(() => []);
    const existingSongId = sameSong.map(r => r.songId).find(Boolean);
    rec.songId = existingSongId || identity.defaultSongId;
  }

  // 極端に稀なprefix衝突に備え、異なるhashで同じrecordingIdが既にあればランダムIDへ退避。
  if (audioSha256) {
    const collision = await dbGet('recordings', rec.recordingId).catch(() => null);
    if (collision && collision.audioSha256 && collision.audioSha256 !== audioSha256) rec.recordingId = uid('rec');
  }

  $('#busy-bar').style.width = '30%';
  $('#busy-msg').textContent = '端末内に録音を保存しています…';
  try {
    await dbPut('audio', { recordingId: rec.recordingId, blob: file, fileName: file.name, mimeType: file.type || '', savedAt: nowIso() });
    await dbPut('recordings', rec);
  } catch (e) {
    closeSheet();
    toast('保存できませんでした（空き容量をご確認ください）');
    return;
  }
  closeSheet();
  await loadRecordings();
  await openRecording(rec.recordingId);
  startAnalysis(rec, file);
}

/* =====================================================================
 * デコード → 解析
 * ===================================================================== */
function decodeAudio(arrayBuffer) {
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return Promise.reject(new Error('AudioContext 非対応'));
  const ctx = new AC();
  return new Promise((res, rej) => {
    let settled = false;
    const ok = buf => { if (!settled) { settled = true; res({ buf, ctx }); } };
    const ng = err => { if (!settled) { settled = true; rej(err || new Error('decode failed')); } };
    let p;
    try { p = ctx.decodeAudioData(arrayBuffer, ok, ng); } catch (e) { ng(e); return; }
    if (p && typeof p.then === 'function') p.then(ok, ng);
  }).then(r => {
    try { if (r.ctx.close) r.ctx.close(); } catch (e) { }
    return r.buf;
  }, e => {
    try { if (ctx.close) ctx.close(); } catch (x) { }
    throw e;
  });
}

function downmixMono(audioBuffer) {
  const ch = audioBuffer.numberOfChannels;
  const n = audioBuffer.length;
  const out = new Float32Array(n);
  for (let c = 0; c < ch; c++) {
    const d = audioBuffer.getChannelData(c);
    for (let i = 0; i < n; i++) out[i] += d[i];
  }
  if (ch > 1) for (let i = 0; i < n; i++) out[i] /= ch;
  return out;
}

function setAnalysisUi(status, pct, msg) {
  const box = $('#rv-analysis-state');
  const retry = $('#btn-reanalyze');
  if (status === 'hidden') { box.hidden = true; return; }
  box.hidden = false;
  $('#rv-analysis-msg').textContent = msg;
  $('#rv-progress').style.width = (pct || 0) + '%';
  retry.hidden = !(status === 'failed');
}

async function startAnalysis(rec, fileMaybe) {
  if (state.analyzing) { toast('別の解析を実行中です'); return; }
  state.analyzing = true;
  rec.analysisStatus = 'running';
  rec.updatedAt = nowIso();
  await dbPut('recordings', rec).catch(() => { });
  if (state.rec && state.rec.recordingId === rec.recordingId) setAnalysisUi('running', 1, '解析中 1%');

  let file = fileMaybe;
  try {
    if (!file) {
      const a = await dbGet('audio', rec.recordingId);
      if (!a || !a.blob) throw new Error('音声データが見つかりません');
      file = a.blob;
    }
    const ab = await file.arrayBuffer();
    let audioSha256 = rec.audioSha256 || null;
    let audioHashError = rec.audioHashError || '';
    if (!audioSha256) {
      try {
        audioSha256 = await sha256Hex(ab);
        rec.audioSha256 = audioSha256;
        rec.audioHashAlgorithm = 'SHA-256';
        rec.audioHashError = null;
      } catch (hashErr) {
        audioHashError = (hashErr && hashErr.message) || String(hashErr);
        rec.audioSha256 = null;
        rec.audioHashAlgorithm = 'SHA-256';
        rec.audioHashError = audioHashError;
      }
    }
    let audioBuffer;
    try {
      audioBuffer = await decodeAudio(ab);
    } catch (e) {
      throw Object.assign(new Error('この音声形式はこのブラウザでは解析できません'), { unsupported: true });
    }
    rec.durationSec = audioBuffer.duration;
    rec.sampleRate = audioBuffer.sampleRate;
    rec.channels = audioBuffer.numberOfChannels;

    const mono = downmixMono(audioBuffer);
    const srcRate = audioBuffer.sampleRate;
    audioBuffer = null; // 参照を落としてメモリを解放しやすくする

    const cfg = Object.assign({}, settings);
    const result = await runWorker(mono, srcRate, cfg, pct => {
      if (state.rec && state.rec.recordingId === rec.recordingId) setAnalysisUi('running', pct, '解析中 ' + pct + '%');
    });

    const record = {
      recordingId: rec.recordingId,
      analysisId: uid('ana'),
      supersedesAnalysisId: rec.latestAnalysisId || null,
      schemaVersion: SCHEMA_VERSION,
      appVersion: APP_VERSION,
      buildId: BUILD_ID,
      audioSha256,
      audioHashAlgorithm: 'SHA-256',
      audioHashError: audioHashError || null,
      createdAt: nowIso(),
      updatedAt: nowIso(),
      settings: cfg,
      engine: result.engine,
      summary: result.summary,
      frames: result.frames,
      waveform: result.waveform,
      spectrogram: result.spectrogram,
      detectedSegments: result.detectedSegments
    };
    // Full analysis は従来互換の analysis store に最新1件を保持し、
    // compact provenance は analysisHistory に全run残す。
    const histEntry = compactAnalysisHistoryEntry(record);
    if (histEntry) await dbPut('analysisHistory', histEntry);
    await dbPut('analysis', record);
    rec.latestAnalysisId = record.analysisId;
    try { rec.analysisCount = (await dbByRec('analysisHistory', rec.recordingId)).length; }
    catch (e) { rec.analysisCount = Math.max(1, Number(rec.analysisCount || 0) + 1); }
    rec.analysisStatus = 'done';
    rec.analysisError = '';
    rec.updatedAt = nowIso();
    await dbPut('recordings', rec);

    if (state.rec && state.rec.recordingId === rec.recordingId) {
      // openRecording() may have loaded a different object instance than the rec
      // passed to startAnalysis(). Refresh state.rec so export/UI uses the
      // newly persisted latestAnalysisId and analysisCount immediately.
      state.rec = rec;
      state.analysis = record;
      state.confMin = cfg.minimumConfidence;
      $('#conf-slider').value = String(cfg.minimumConfidence);
      $('#conf-val').textContent = cfg.minimumConfidence.toFixed(2);
      setAnalysisUi('hidden');
      renderReviewHeader();
      renderSummary();
      drawAllGraphs();
      renderSegments();
    }
    toast('解析が完了しました');
  } catch (e) {
    rec.analysisStatus = e && e.unsupported ? 'unsupported' : 'failed';
    rec.analysisError = (e && e.message) || String(e);
    rec.updatedAt = nowIso();
    await dbPut('recordings', rec).catch(() => { });
    if (state.rec && state.rec.recordingId === rec.recordingId) {
      setAnalysisUi('failed', 100, rec.analysisError + '（再生と手動レビューはそのまま使えます）');
    } else {
      toast('解析に失敗しました');
    }
  } finally {
    state.analyzing = false;
    refreshStorageEstimate();
    loadRecordings();
  }
}

function runWorker(mono, srcRate, cfg, onProgress) {
  return new Promise((res, rej) => {
    let w;
    try { w = new Worker('audio-analysis-worker.js?v=' + encodeURIComponent(BUILD_ID)); }
    catch (e) { rej(new Error('解析ワーカーを起動できません')); return; }
    state.worker = w;
    w.onmessage = ev => {
      const m = ev.data;
      if (m.type === 'progress') onProgress(m.pct);
      else if (m.type === 'done') { w.terminate(); state.worker = null; res(m.result); }
      else if (m.type === 'error') { w.terminate(); state.worker = null; rej(new Error(m.message)); }
    };
    w.onerror = e => { try { w.terminate(); } catch (x) { } state.worker = null; rej(new Error('解析中にエラーが発生しました')); };
    w.postMessage({ type: 'analyze', pcm: mono, sampleRate: srcRate, settings: cfg }, [mono.buffer]);
  });
}

/* =====================================================================
 * レビュー画面
 * ===================================================================== */
async function openRecording(id) {
  stopPlayback();
  const rec = await dbGet('recordings', id);
  if (!rec) { toast('録音が見つかりません'); return; }
  state.rec = rec;
  state.analysis = null;
  state.loop = { a: null, b: null, on: false };
  state.markers = [];
  state.segments = [];

  showView('view-review');
  renderReviewHeader();
  updateAbReadout();

  // 音声を用意（PCMは保持せず、Blob URL で再生する）
  try {
    const a = await dbGet('audio', id);
    if (a && a.blob) attachAudio(a.blob);
  } catch (e) { toast('音声を読み込めませんでした'); }

  // レビューデータ
  try {
    state.markers = (await dbByRec('markers', id)).sort((x, y) => x.timeSec - y.timeSec);
    state.segments = (await dbByRec('segments', id)).sort((x, y) => x.startSec - y.startSec);
  } catch (e) { }
  renderMarkers();
  renderSegments();

  // 解析結果
  try {
    const an = await dbGet('analysis', id);
    if (an) {
      state.analysis = an;
      state.confMin = (an.settings && an.settings.minimumConfidence) || DEFAULT_SETTINGS.minimumConfidence;
      $('#conf-slider').value = String(state.confMin);
      $('#conf-val').textContent = Number(state.confMin).toFixed(2);
      setAnalysisUi('hidden');
    }
  } catch (e) { }

  if (!state.analysis) {
    if (rec.analysisStatus === 'unsupported' || rec.analysisStatus === 'failed') {
      setAnalysisUi('failed', 100, (rec.analysisError || '解析に失敗しました') + '（再生と手動レビューはそのまま使えます）');
    } else if (rec.analysisStatus === 'running') {
      setAnalysisUi('running', 5, '解析中…');
    } else {
      setAnalysisUi('running', 0, '解析を開始します…');
      startAnalysis(rec);
    }
  }
  renderSummary();
  renderSegments();          // 解析が揃った状態で区間統計を出し直す
  requestAnimationFrame(drawAllGraphs);
}

function renderReviewHeader() {
  const rec = state.rec;
  if (!rec) return;
  $('#rv-title').textContent = rec.title || '(無題)';
  const chips = [];
  chips.push(fmtDate(rec.recordedAt || rec.createdAt));
  chips.push(fmtTime(rec.durationSec, false));
  if (rec.artist) chips.push(rec.artist);
  if (rec.damScore) chips.push('DAM ' + rec.damScore);
  if (rec.keyChange) chips.push('Key ' + rec.keyChange);
  if (rec.octave) chips.push('Oct ' + rec.octave);
  if (rec.device) chips.push(rec.device);
  if (rec.scoringMode) chips.push(rec.scoringMode);
  if (rec.sampleRate) chips.push(rec.sampleRate + ' Hz / ' + rec.channels + 'ch');
  $('#rv-meta').innerHTML = chips.filter(Boolean).map(c => `<span class="pill">${escapeHtml(c)}</span>`).join('');
  $('#t-tot').textContent = fmtTime(rec.durationSec);
}

function renderSummary() {
  const box = $('#rv-summary');
  const an = state.analysis;
  if (!an) { box.textContent = '解析結果はまだありません。'; return; }
  const s = an.summary, e = an.engine, c = an.settings;
  const rows = [
    ['duration', num(s.durationSec, 2) + ' s'],
    ['analysis sampleRate', s.analysisSampleRate + ' Hz'],
    ['frame / hop', s.frameSizeMs + ' ms / ' + s.hopSizeMs + ' ms'],
    ['frames', s.frameCount],
    ['legacy median F0', s.medianF0Hz === null ? 'null' : s.medianF0Hz + ' Hz'],
    ['legacy detected F0 range', s.minF0Hz === null ? 'null' : s.minF0Hz + ' – ' + s.maxF0Hz + ' Hz'],
    ['legacy valid F0 ratio', s.validF0FrameRatio],
    ['F0 candidate p05 / p50 / p95', s.f0CandidateEvidence && s.f0CandidateEvidence.p05Hz !== null ? s.f0CandidateEvidence.p05Hz + ' / ' + s.f0CandidateEvidence.p50Hz + ' / ' + s.f0CandidateEvidence.p95Hz + ' Hz' : 'null'],
    ['F0 candidate ratio', s.f0CandidateEvidence ? s.f0CandidateEvidence.candidateFrameRatio : 'null'],
    ['F0 ambiguity', s.f0CandidateEvidence ? ('strong ' + s.f0CandidateEvidence.ambiguity.strongFrameCount + ' / caution ' + s.f0CandidateEvidence.ambiguity.cautionFrameCount + ' / candidate ' + s.f0CandidateEvidence.candidateFrameCount) : 'null'],
    ['median RMS', s.medianRmsDb + ' dBFS'],
    ['RMS range', s.rmsRangeDb + ' dB'],
    ['peak', s.peakDb + ' dBFS'],
    ['loudness reference', s.loudnessReferenceDb + ' dBFS (' + c.loudnessReference + ')'],
    ['noise floor est.', s.noiseFloorEstimateDb + ' dBFS'],
    ['detected segments', s.detectedSegmentCount + ' 件 / ' + s.detectedSegmentTotalSec + ' s'],
    ['engine', e.analysisEngineName + ' v' + e.analysisEngineVersion],
    ['f0 algorithm', e.algorithmNames.f0 + ' v' + e.algorithmVersions.f0],
    ['minimumConfidence', c.minimumConfidence],
    ['experimental features', 'not implemented (v0.2 Phase A-3)'],
    ['analyzed at', fmtDate(an.createdAt)]
  ];
  box.innerHTML = rows.map(r => `<div>${escapeHtml(r[0])}: <b>${escapeHtml(String(r[1]))}</b></div>`).join('');
}

/* ---------------- 再生 ---------------- */
function attachAudio(blob) {
  if (state.audioUrl) { URL.revokeObjectURL(state.audioUrl); state.audioUrl = null; }
  const url = URL.createObjectURL(blob);
  state.audioUrl = url;
  const a = state.audio || new Audio();
  a.src = url;
  a.preload = 'metadata';
  a.playbackRate = currentSpeed();
  a.onloadedmetadata = async () => {
    if (isFinite(a.duration) && a.duration > 0 && state.rec && Math.abs((state.rec.durationSec || 0) - a.duration) > 0.2) {
      state.rec.durationSec = a.duration;
      state.rec.updatedAt = nowIso();
      await dbPut('recordings', state.rec).catch(() => { });
      renderReviewHeader();
      drawAllGraphs();
    }
    $('#t-tot').textContent = fmtTime(duration());
  };
  a.ontimeupdate = null;
  a.onplay = () => { $('#btn-play').textContent = '❚❚'; tick(); };
  a.onpause = () => { $('#btn-play').textContent = '▶'; };
  a.onended = () => { $('#btn-play').textContent = '▶'; };
  state.audio = a;
}
function duration() {
  const a = state.audio;
  if (a && isFinite(a.duration) && a.duration > 0) return a.duration;
  return (state.rec && state.rec.durationSec) || 0;
}
function currentSpeed() {
  const on = $('#speed-row .spd.is-on');
  return on ? parseFloat(on.dataset.spd) : 1;
}
function seekTo(t) {
  const a = state.audio;
  if (!a) return;
  try { a.currentTime = clamp(t, 0, Math.max(0, duration() - 0.05)); } catch (e) { }
  updatePlayhead();
}
function togglePlay() {
  const a = state.audio;
  if (!a) { toast('音声が読み込まれていません'); return; }
  if (a.paused) {
    a.playbackRate = currentSpeed();
    a.play().catch(() => toast('再生できませんでした'));
  } else a.pause();
}
function stopPlayback() {
  if (state.audio) { try { state.audio.pause(); } catch (e) { } }
  cancelAnimationFrame(state.rafId);
}
function tick() {
  cancelAnimationFrame(state.rafId);
  const loop = () => {
    const a = state.audio;
    if (!a) return;
    // A-Bループ
    if (state.loop.on && state.loop.a !== null && state.loop.b !== null && state.loop.b > state.loop.a) {
      if (a.currentTime >= state.loop.b || a.currentTime < state.loop.a - 0.5) {
        try { a.currentTime = state.loop.a; } catch (e) { }
      }
    }
    updatePlayhead();
    if (!a.paused) state.rafId = requestAnimationFrame(loop);
  };
  state.rafId = requestAnimationFrame(loop);
}
function updatePlayhead() {
  const a = state.audio;
  const t = a ? a.currentTime : 0;
  const dur = duration() || 1;
  $('#t-cur').textContent = fmtTime(t);
  const seek = $('#seek');
  if (!seek.dataset.dragging) seek.value = String(Math.round(t / dur * 1000));
  const stack = $('#graph-stack');
  const ph = $('#playhead');
  const first = $('#cv-wave');
  if (stack && ph && first) {
    const sRect = stack.getBoundingClientRect();
    const cRect = first.getBoundingClientRect();
    const x = (cRect.left - sRect.left) + (t / dur) * cRect.width;
    ph.style.left = x + 'px';
    ph.style.opacity = '1';
  }
}

/* ---------------- マーカー ---------------- */
function openMarkerSheet(timeSec, existing) {
  state.markerDraft = existing
    ? Object.assign({}, existing)
    : { markerId: uid('mk'), timeSec: timeSec, tag: '違和感', memo: '' };
  $('#tag-sheet-title').textContent = existing ? 'マーカーを編集' : 'マーカーのタグ';
  $('#tag-time').textContent = fmtClock(state.markerDraft.timeSec);
  $('#tag-memo').value = state.markerDraft.memo || '';
  buildTagGrid(state.markerDraft.tag);
  openSheet('sheet-tag');
}
function buildTagGrid(selected) {
  const g = $('#tag-grid');
  g.innerHTML = '';
  for (const t of TAGS) {
    const b = document.createElement('button');
    b.className = 'tag-btn' + (GOOD_TAGS.has(t) ? ' good' : ALERT_TAGS.has(t) ? ' alert' : '') + (t === selected ? ' is-on' : '');
    b.textContent = t;
    b.addEventListener('click', () => {
      $$('.tag-btn', g).forEach(x => x.classList.remove('is-on'));
      b.classList.add('is-on');
      if (state.markerDraft) state.markerDraft.tag = t;
      if (state.segmentDraft) state.segmentDraft.tag = t;
    });
    g.appendChild(b);
  }
}
async function saveMarkerDraft() {
  const memo = $('#tag-memo').value.trim();
  if (state.segmentDraft) {
    const seg = state.segmentDraft;
    seg.memo = memo;
    seg.updatedAt = nowIso();
    await dbPut('segments', seg).catch(() => toast('保存できませんでした'));
    state.segments = (await dbByRec('segments', state.rec.recordingId)).sort((a, b) => a.startSec - b.startSec);
    state.segmentDraft = null;
    closeSheet();
    renderSegments();
    drawAllGraphs();
    await bumpCounts();
    toast('区間を保存しました');
    return;
  }
  const mk = state.markerDraft;
  if (!mk) { closeSheet(); return; }
  mk.memo = memo;
  mk.recordingId = state.rec.recordingId;
  mk.schemaVersion = SCHEMA_VERSION;
  mk.createdAt = mk.createdAt || nowIso();
  mk.updatedAt = nowIso();
  mk.timeSec = +Number(mk.timeSec).toFixed(2);
  try { await dbPut('markers', mk); } catch (e) { toast('保存できませんでした'); }
  state.markers = (await dbByRec('markers', state.rec.recordingId)).sort((a, b) => a.timeSec - b.timeSec);
  state.markerDraft = null;
  closeSheet();
  renderMarkers();
  drawAllGraphs();
  await bumpCounts();
}
async function bumpCounts() {
  if (!state.rec) return;
  state.rec.markerCount = state.markers.length;
  state.rec.segmentCount = state.segments.length;
  state.rec.updatedAt = nowIso();
  await dbPut('recordings', state.rec).catch(() => { });
}
function renderMarkers() {
  const wrap = $('#marker-list');
  wrap.innerHTML = '';
  $('#marker-count').textContent = state.markers.length;
  for (const m of state.markers) {
    const el = document.createElement('div');
    el.className = 'item';
    el.innerHTML = `
      <div class="item-main">
        <div class="item-title"><span class="mono">${fmtClock(m.timeSec)}</span>　${escapeHtml(m.tag)}</div>
        ${m.memo ? `<div class="item-sub">${escapeHtml(m.memo)}</div>` : ''}
      </div>
      <div class="item-actions">
        <button class="icon-btn" data-act="play">▶2秒前</button>
        <button class="icon-btn" data-act="edit">編集</button>
        <button class="icon-btn danger" data-act="del">削除</button>
      </div>`;
    el.querySelector('[data-act=play]').addEventListener('click', e => {
      e.stopPropagation();
      seekTo(Math.max(0, m.timeSec - 2));
      if (state.audio && state.audio.paused) togglePlay();
    });
    el.querySelector('[data-act=edit]').addEventListener('click', e => { e.stopPropagation(); openMarkerSheet(m.timeSec, m); });
    el.querySelector('[data-act=del]').addEventListener('click', async e => {
      e.stopPropagation();
      await dbDel('markers', m.markerId).catch(() => { });
      state.markers = state.markers.filter(x => x.markerId !== m.markerId);
      renderMarkers(); drawAllGraphs(); bumpCounts();
    });
    el.addEventListener('click', () => { seekTo(Math.max(0, m.timeSec - 2)); });
    wrap.appendChild(el);
  }
}

/* ---------------- 区間レビュー ---------------- */
function updateAbReadout() {
  const a = state.loop.a, b = state.loop.b;
  $('#ab-readout').textContent = `A: ${a === null ? '—' : fmtClock(a)} / B: ${b === null ? '—' : fmtClock(b)}`;
  $('#btn-loop-toggle').classList.toggle('is-on', state.loop.on);
  $('#btn-loop-toggle').textContent = state.loop.on ? 'ループ停止' : 'ループ開始';
}
async function saveAbAsSegment() {
  if (state.loop.a === null || state.loop.b === null || state.loop.b <= state.loop.a) {
    toast('A地点とB地点を指定してください'); return;
  }
  const seg = {
    segmentId: uid('sg'),
    recordingId: state.rec.recordingId,
    schemaVersion: SCHEMA_VERSION,
    startSec: +state.loop.a.toFixed(2),
    endSec: +state.loop.b.toFixed(2),
    tag: '違和感',
    memo: '',
    createdAt: nowIso(),
    updatedAt: nowIso()
  };
  state.segmentDraft = seg;
  state.markerDraft = null;
  $('#tag-sheet-title').textContent = '区間のタグ';
  $('#tag-time').textContent = `${fmtClock(seg.startSec)} - ${fmtClock(seg.endSec)}`;
  $('#tag-memo').value = '';
  buildTagGrid(seg.tag);
  openSheet('sheet-tag');
}
function segmentStats(seg) {
  const an = state.analysis;
  if (!an) return null;
  return rangeStatsMain(an.frames, seg.startSec, seg.endSec);
}
function renderSegments() {
  const wrap = $('#segment-list');
  wrap.innerHTML = '';
  $('#segment-count').textContent = state.segments.length;
  for (const s of state.segments) {
    const st = segmentStats(s);
    const el = document.createElement('div');
    el.className = 'item';
    const statLine = st
      ? `RMS ${num(st.meanRmsDb)} dB（幅 ${num(st.rmsRangeDb)}）／F0 中央 ${st.medianF0Hz === null ? '—' : st.medianF0Hz + ' Hz'}（${st.minF0Hz === null ? '—' : st.minF0Hz + '–' + st.maxF0Hz}）／conf ${st.meanF0Confidence === null ? '—' : st.meanF0Confidence}／active ${st.activeRatio}`
      : '解析データなし';
    el.innerHTML = `
      <div class="item-main">
        <div class="item-title"><span class="mono">${fmtClock(s.startSec)} - ${fmtClock(s.endSec)}</span>　${escapeHtml(s.tag)}</div>
        ${s.memo ? `<div class="item-sub">${escapeHtml(s.memo)}</div>` : ''}
        <div class="item-sub mono">${escapeHtml(statLine)}</div>
      </div>
      <div class="item-actions">
        <button class="icon-btn" data-act="loop">ループ</button>
        <button class="icon-btn" data-act="edit">編集</button>
        <button class="icon-btn danger" data-act="del">削除</button>
      </div>`;
    el.querySelector('[data-act=loop]').addEventListener('click', e => {
      e.stopPropagation();
      state.loop = { a: s.startSec, b: s.endSec, on: true };
      updateAbReadout(); drawAllGraphs();
      seekTo(s.startSec);
      if (state.audio && state.audio.paused) togglePlay(); else tick();
    });
    el.querySelector('[data-act=edit]').addEventListener('click', e => {
      e.stopPropagation();
      state.segmentDraft = Object.assign({}, s);
      state.markerDraft = null;
      $('#tag-sheet-title').textContent = '区間を編集';
      $('#tag-time').textContent = `${fmtClock(s.startSec)} - ${fmtClock(s.endSec)}`;
      $('#tag-memo').value = s.memo || '';
      buildTagGrid(s.tag);
      openSheet('sheet-tag');
    });
    el.querySelector('[data-act=del]').addEventListener('click', async e => {
      e.stopPropagation();
      await dbDel('segments', s.segmentId).catch(() => { });
      state.segments = state.segments.filter(x => x.segmentId !== s.segmentId);
      renderSegments(); drawAllGraphs(); bumpCounts();
    });
    el.addEventListener('click', () => {
      state.loop = { a: s.startSec, b: s.endSec, on: false };
      updateAbReadout();
      seekTo(s.startSec);
      if (state.audio && state.audio.paused) togglePlay();
    });
    wrap.appendChild(el);
  }
}

/* 区間統計（Worker と同じ定義をメインスレッドでも使う） */
function rangeStatsMain(F, startSec, endSec) {
  const n = F.timeSec.length;
  const rms = [], f0 = [], conf = [], cen = [], flx = [];
  let voiced = 0, total = 0;
  for (let i = 0; i < n; i++) {
    const t = F.timeSec[i];
    if (t < startSec) continue;
    if (t > endSec) break;
    total++;
    if (F.rmsDb[i] > -119) rms.push(F.rmsDb[i]);
    if (isFinite(F.f0Hz[i])) f0.push(F.f0Hz[i]);
    if (isFinite(F.f0Conf[i])) conf.push(F.f0Conf[i]);
    if (isFinite(F.centroid[i])) cen.push(F.centroid[i]);
    if (isFinite(F.flux[i])) flx.push(F.flux[i]);
    if (F.voicedProb[i] >= 0.5) voiced++;
  }
  const mean = a => a.length ? a.reduce((x, y) => x + y, 0) / a.length : NaN;
  const med = a => {
    if (!a.length) return NaN;
    const s = a.slice().sort((p, q) => p - q), m = s.length >> 1;
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
  };
  const r2 = (v, d) => isFinite(v) ? +v.toFixed(d) : null;
  return {
    frameCount: total,
    durationSec: +(endSec - startSec).toFixed(3),
    meanRmsDb: r2(mean(rms), 2),
    maxRmsDb: rms.length ? r2(Math.max.apply(null, rms), 2) : null,
    minRmsDb: rms.length ? r2(Math.min.apply(null, rms), 2) : null,
    rmsRangeDb: rms.length ? r2(Math.max.apply(null, rms) - Math.min.apply(null, rms), 2) : null,
    medianF0Hz: r2(med(f0), 2),
    minF0Hz: f0.length ? r2(Math.min.apply(null, f0), 2) : null,
    maxF0Hz: f0.length ? r2(Math.max.apply(null, f0), 2) : null,
    meanF0Confidence: r2(mean(conf), 3),
    validF0Ratio: total ? +(f0.length / total).toFixed(3) : null,
    activeRatio: total ? +(voiced / total).toFixed(3) : null,
    spectralCentroidMeanHz: r2(mean(cen), 1),
    spectralFluxMean: r2(mean(flx), 4)
  };
}

/* =====================================================================
 * グラフ描画（画面用とPNG書き出し用で同じ関数を使う）
 * ===================================================================== */
function cssVar(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}
function palette(forExport) {
  if (forExport) {
    return {
      bg: '#FFFFFF', panel: '#FFFFFF', grid: '#D8D8DD', text: '#111114', sub: '#55555C',
      wave: '#2B6CB0', rms: '#0A7B34', peak: '#9AA0A6', f0: '#8E24AA',
      good: '#1B8A3A', alert: '#D97706', mark: '#1D4ED8', band: 'rgba(29,78,216,.10)'
    };
  }
  const dark = matchMedia('(prefers-color-scheme: dark)').matches;
  return {
    bg: 'transparent', panel: cssVar('--bg-sunken', dark ? '#2C2C2E' : '#E9E9EE'),
    grid: dark ? 'rgba(235,235,245,.18)' : 'rgba(60,60,67,.18)',
    text: cssVar('--label', dark ? '#fff' : '#000'),
    sub: dark ? 'rgba(235,235,245,.6)' : 'rgba(60,60,67,.6)',
    wave: dark ? '#64B5F6' : '#2B6CB0',
    rms: dark ? '#30D158' : '#0A7B34',
    peak: dark ? 'rgba(235,235,245,.45)' : 'rgba(60,60,67,.4)',
    f0: dark ? '#CE93D8' : '#8E24AA',
    good: cssVar('--green', '#34C759'), alert: cssVar('--orange', '#FF9500'),
    mark: cssVar('--accent', '#007AFF'),
    band: dark ? 'rgba(10,132,255,.16)' : 'rgba(0,122,255,.12)'
  };
}
function tagColor(tag, C) {
  if (GOOD_TAGS.has(tag)) return C.good;
  if (ALERT_TAGS.has(tag)) return C.alert;
  return C.mark;
}
function niceStep(span, targetTicks) {
  const raw = span / Math.max(1, targetTicks);
  const cands = [0.5, 1, 2, 5, 10, 15, 20, 30, 60, 120, 300, 600];
  for (const c of cands) if (c >= raw) return c;
  return 600;
}

/* 描画領域を用意して時間軸を描く */
function beginChart(ctx, o) {
  const { W, H, m, C } = o;
  if (o.forExport) { ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H); }
  else ctx.clearRect(0, 0, W, H);
  const x0 = m.l, y0 = m.t, w = W - m.l - m.r, h = H - m.t - m.b;
  ctx.fillStyle = C.panel;
  ctx.fillRect(x0, y0, w, h);

  if (o.title) {
    ctx.fillStyle = C.text;
    ctx.font = `700 ${o.fs.title}px -apple-system, "Helvetica Neue", sans-serif`;
    ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
    ctx.fillText(o.title, m.l, m.t - o.fs.title * 0.7);
  }
  // 時間グリッド
  const step = niceStep(o.dur, o.forExport ? 12 : 6);
  ctx.strokeStyle = C.grid; ctx.lineWidth = 1;
  ctx.fillStyle = C.sub;
  ctx.font = `${o.fs.axis}px ui-monospace, Menlo, monospace`;
  ctx.textAlign = 'center'; ctx.textBaseline = 'top';
  for (let t = 0; t <= o.dur + 1e-6; t += step) {
    const x = Math.round(x0 + (t / o.dur) * w) + 0.5;
    ctx.beginPath(); ctx.moveTo(x, y0); ctx.lineTo(x, y0 + h); ctx.stroke();
    if (o.showAxis) ctx.fillText(fmtTime(t, false), x, y0 + h + 4);
  }
  return { x0, y0, w, h };
}

function drawOverlays(ctx, o, box) {
  const { C } = o;
  const { x0, y0, w, h } = box;
  // 区間（帯）
  for (const s of (o.segments || [])) {
    const a = clamp(s.startSec / o.dur, 0, 1), b = clamp(s.endSec / o.dur, 0, 1);
    ctx.fillStyle = C.band;
    ctx.fillRect(x0 + a * w, y0, Math.max(1, (b - a) * w), h);
    ctx.strokeStyle = tagColor(s.tag, C);
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(x0 + a * w, y0 + h - 1); ctx.lineTo(x0 + b * w, y0 + h - 1);
    ctx.stroke();
  }
  // A-Bループ範囲
  if (o.loop && o.loop.a !== null && o.loop.b !== null && o.loop.b > o.loop.a) {
    const a = clamp(o.loop.a / o.dur, 0, 1), b = clamp(o.loop.b / o.dur, 0, 1);
    ctx.strokeStyle = C.sub; ctx.setLineDash([4, 3]); ctx.lineWidth = 1;
    ctx.strokeRect(x0 + a * w, y0 + 0.5, Math.max(1, (b - a) * w), h - 1);
    ctx.setLineDash([]);
  }
  // マーカー
  for (const m of (o.markers || [])) {
    const x = x0 + clamp(m.timeSec / o.dur, 0, 1) * w;
    const col = tagColor(m.tag, C);
    ctx.strokeStyle = col; ctx.lineWidth = o.forExport ? 2 : 1.2;
    ctx.beginPath(); ctx.moveTo(x, y0); ctx.lineTo(x, y0 + h); ctx.stroke();
    ctx.fillStyle = col;
    const r = o.forExport ? 5 : 3;
    ctx.beginPath(); ctx.arc(x, y0 + r + 1, r, 0, Math.PI * 2); ctx.fill();
  }
}

function drawLegend(ctx, o, box, items) {
  if (!o.forExport) return;
  const { C } = o;
  let x = box.x0, y = box.y0 + box.h + o.fs.axis + 14;
  ctx.font = `${o.fs.legend}px -apple-system, "Helvetica Neue", sans-serif`;
  ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  for (const it of items) {
    ctx.fillStyle = it.color;
    ctx.fillRect(x, y - 5, 22, 10);
    ctx.fillStyle = C.text;
    ctx.fillText(it.label, x + 28, y);
    x += 28 + ctx.measureText(it.label).width + 26;
  }
}

/* ---------- 波形 ---------- */
function renderWaveform(ctx, o) {
  const box = beginChart(ctx, o);
  const C = o.C, an = o.an;
  if (an && an.waveform) {
    const { min, max, count } = an.waveform;
    const cy = box.y0 + box.h / 2;
    let peakAbs = 0;
    for (let i = 0; i < count; i++) {
      const a = Math.max(Math.abs(min[i]), Math.abs(max[i]));
      if (a > peakAbs) peakAbs = a;
    }
    const scale = (box.h / 2 - 2) / Math.max(0.05, peakAbs);
    ctx.strokeStyle = C.wave; ctx.lineWidth = 1;
    ctx.beginPath();
    for (let i = 0; i < count; i++) {
      const x = box.x0 + (i / (count - 1)) * box.w;
      ctx.moveTo(x, cy - max[i] * scale);
      ctx.lineTo(x, cy - min[i] * scale);
    }
    ctx.stroke();
    ctx.strokeStyle = C.grid;
    ctx.beginPath(); ctx.moveTo(box.x0, cy); ctx.lineTo(box.x0 + box.w, cy); ctx.stroke();
  } else {
    noData(ctx, o, box);
  }
  drawOverlays(ctx, o, box);
  drawLegend(ctx, o, box, [{ color: C.wave, label: 'waveform (normalized amplitude)' }]);
  if (o.forExport) yLabel(ctx, o, box, ['+1', '0', '-1']);
}

/* ---------- 音量エンベロープ ---------- */
function renderLoudness(ctx, o) {
  const box = beginChart(ctx, o);
  const C = o.C, an = o.an;
  const top = 0, bottom = -70;
  const yOf = db => box.y0 + box.h * (1 - (clamp(db, bottom, top) - bottom) / (top - bottom));
  if (an && an.frames) {
    const F = an.frames, n = F.timeSec.length;
    ctx.strokeStyle = C.grid; ctx.lineWidth = 1;
    ctx.fillStyle = C.sub;
    ctx.font = `${o.fs.axis}px ui-monospace, Menlo, monospace`;
    ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
    for (let db = 0; db >= -60; db -= 20) {
      const y = Math.round(yOf(db)) + 0.5;
      ctx.beginPath(); ctx.moveTo(box.x0, y); ctx.lineTo(box.x0 + box.w, y); ctx.stroke();
      ctx.fillText(db + ' dB', box.x0 - 4, y);
    }
    // peak
    ctx.strokeStyle = C.peak; ctx.lineWidth = 1;
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const x = box.x0 + (F.timeSec[i] / o.dur) * box.w;
      const y = yOf(F.peakDb[i]);
      i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    }
    ctx.stroke();
    // rms
    ctx.strokeStyle = C.rms; ctx.lineWidth = o.forExport ? 2 : 1.4;
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const x = box.x0 + (F.timeSec[i] / o.dur) * box.w;
      const y = yOf(F.rmsDb[i]);
      i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    }
    ctx.stroke();
    // 検出区間
    ctx.fillStyle = C.rms;
    ctx.globalAlpha = 0.16;
    for (const s of (an.detectedSegments || [])) {
      const a = clamp(s.startSec / o.dur, 0, 1), b = clamp(s.endSec / o.dur, 0, 1);
      ctx.fillRect(box.x0 + a * box.w, box.y0 + box.h - 4, Math.max(1, (b - a) * box.w), 4);
    }
    ctx.globalAlpha = 1;
  } else noData(ctx, o, box);
  drawOverlays(ctx, o, box);
  drawLegend(ctx, o, box, [
    { color: C.rms, label: 'RMS (dBFS)' },
    { color: C.peak, label: 'peak (dBFS)' },
    { color: C.rms, label: 'detectedActiveSegment' }
  ]);
}

/* ---------- F0 ---------- */
function renderPitch(ctx, o) {
  const box = beginChart(ctx, o);
  const C = o.C, an = o.an;
  if (an && an.frames) {
    const F = an.frames, n = F.timeSec.length;
    let lo = Infinity, hi = -Infinity;
    for (let i = 0; i < n; i++) {
      const v = F.f0Hz[i];
      if (isFinite(v)) { if (v < lo) lo = v; if (v > hi) hi = v; }
    }
    if (!isFinite(lo)) { lo = 80; hi = 800; }
    lo = Math.max(50, lo / 1.15); hi = Math.min(2000, hi * 1.15);
    const yOf = hz => box.y0 + box.h * (1 - (Math.log2(hz) - Math.log2(lo)) / (Math.log2(hi) - Math.log2(lo)));
    // 目盛り
    ctx.strokeStyle = C.grid; ctx.fillStyle = C.sub; ctx.lineWidth = 1;
    ctx.font = `${o.fs.axis}px ui-monospace, Menlo, monospace`;
    ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
    const ticks = [];
    if (o.pitchUnit === 'midi') {
      const m0 = Math.ceil(hzToMidiJs(lo) / 12) * 12, m1 = hzToMidiJs(hi);
      for (let m = m0; m <= m1; m += 12) ticks.push({ hz: 440 * Math.pow(2, (m - 69) / 12), label: 'M' + m });
    } else {
      for (const hz of [65, 100, 150, 220, 330, 440, 660, 880, 1200]) if (hz >= lo && hz <= hi) ticks.push({ hz, label: hz + ' Hz' });
    }
    for (const t of ticks) {
      const y = Math.round(yOf(t.hz)) + 0.5;
      ctx.beginPath(); ctx.moveTo(box.x0, y); ctx.lineTo(box.x0 + box.w, y); ctx.stroke();
      ctx.fillText(t.label, box.x0 - 4, y);
    }
    // 点: confidence で不透明度を変える。閾値未満は描かない。
    const th = o.confMin;
    for (let i = 0; i < n; i++) {
      const hz = F.f0Hz[i];
      if (!isFinite(hz)) continue;
      const c = F.f0Conf[i];
      if (c < th) continue;
      const alpha = clamp((c - th) / Math.max(0.05, 1 - th), 0, 1) * 0.75 + 0.25;
      ctx.globalAlpha = alpha;
      ctx.fillStyle = C.f0;
      const x = box.x0 + (F.timeSec[i] / o.dur) * box.w;
      const r = o.forExport ? 1.8 : 1.2;
      ctx.fillRect(x - r, yOf(hz) - r, r * 2, r * 2);
    }
    ctx.globalAlpha = 1;
  } else noData(ctx, o, box);
  drawOverlays(ctx, o, box);
  drawLegend(ctx, o, box, [
    { color: C.f0, label: `estimated F0 (confidence >= ${o.confMin.toFixed(2)}, darker = higher confidence)` }
  ]);
}
function hzToMidiJs(hz) { return 69 + 12 * Math.log2(hz / 440); }

/* ---------- スペクトログラム ---------- */
let specCache = { key: '', canvas: null };
function specImageCanvas(an, topHz) {
  const key = an.recordingId + '|' + an.createdAt + '|' + topHz;
  if (specCache.key === key && specCache.canvas) return specCache.canvas;
  const sp = an.spectrogram;
  const rows = Math.max(1, Math.round(sp.height * Math.min(1, topHz / sp.topHz)));
  const cv = document.createElement('canvas');
  cv.width = sp.width; cv.height = rows;
  const c = cv.getContext('2d');
  const img = c.createImageData(sp.width, rows);
  for (let y = 0; y < rows; y++) {
    const srcRow = rows - 1 - y; // 上が高域
    for (let x = 0; x < sp.width; x++) {
      const v = sp.data[x * sp.height + srcRow] / 255;
      const col = magma(v);
      const p = (y * sp.width + x) * 4;
      img.data[p] = col[0]; img.data[p + 1] = col[1]; img.data[p + 2] = col[2]; img.data[p + 3] = 255;
    }
  }
  c.putImageData(img, 0, 0);
  specCache = { key, canvas: cv };
  return cv;
}
function magma(v) {
  v = clamp(v, 0, 1);
  const stops = [
    [0.00, 0, 0, 12], [0.15, 40, 15, 80], [0.35, 110, 30, 110],
    [0.55, 180, 55, 90], [0.75, 235, 110, 60], [0.90, 250, 180, 70], [1.00, 252, 253, 191]
  ];
  for (let i = 1; i < stops.length; i++) {
    if (v <= stops[i][0]) {
      const a = stops[i - 1], b = stops[i];
      const f = (v - a[0]) / (b[0] - a[0]);
      return [a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f, a[3] + (b[3] - a[3]) * f];
    }
  }
  return [252, 253, 191];
}
function renderSpectrogram(ctx, o) {
  const box = beginChart(ctx, o);
  const C = o.C, an = o.an;
  if (an && an.spectrogram) {
    const topHz = Math.min(o.specTopHz, an.spectrogram.topHz);
    const cv = specImageCanvas(an, topHz);
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(cv, box.x0, box.y0, box.w, box.h);
    ctx.strokeStyle = C.grid; ctx.fillStyle = C.sub;
    ctx.font = `${o.fs.axis}px ui-monospace, Menlo, monospace`;
    ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
    const stepHz = topHz > 5000 ? 2000 : 1000;
    for (let f = 0; f <= topHz; f += stepHz) {
      const y = box.y0 + box.h * (1 - f / topHz);
      ctx.fillText((f / 1000) + 'k', box.x0 - 4, clamp(y, box.y0 + 6, box.y0 + box.h - 6));
    }
  } else noData(ctx, o, box);
  drawOverlays(ctx, o, box);
  drawLegend(ctx, o, box, [
    { color: 'rgb(252,253,191)', label: `magnitude high (${an && an.spectrogram ? an.spectrogram.dbCeil : ''} dB)` },
    { color: 'rgb(0,0,12)', label: `low (${an && an.spectrogram ? an.spectrogram.dbFloor : ''} dB)` }
  ]);
}

function noData(ctx, o, box) {
  ctx.fillStyle = o.C.sub;
  ctx.font = `${o.fs.legend}px -apple-system, sans-serif`;
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText('解析データなし（再生と手動レビューは利用できます）', box.x0 + box.w / 2, box.y0 + box.h / 2);
}
function yLabel(ctx, o, box, labels) {
  ctx.fillStyle = o.C.sub;
  ctx.font = `${o.fs.axis}px ui-monospace, Menlo, monospace`;
  ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
  labels.forEach((l, i) => {
    const y = box.y0 + box.h * (i / (labels.length - 1));
    ctx.fillText(l, box.x0 - 4, clamp(y, box.y0 + 6, box.y0 + box.h - 6));
  });
}

/* ---------- 画面へ描画 ---------- */
function setupCanvas(cv) {
  const dpr = Math.min(3, window.devicePixelRatio || 1);
  const rect = cv.getBoundingClientRect();
  const w = Math.max(240, Math.round(rect.width));
  const h = Math.max(60, Math.round(rect.height));
  if (cv.width !== w * dpr || cv.height !== h * dpr) {
    cv.width = w * dpr; cv.height = h * dpr;
  }
  const ctx = cv.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, W: w, H: h };
}
function screenOpts(cv) {
  const { ctx, W, H } = setupCanvas(cv);
  return {
    ctx,
    o: {
      W, H, C: palette(false), forExport: false,
      m: { l: 38, r: 6, t: 2, b: 14 },
      fs: { title: 13, axis: 9, legend: 11 },
      showAxis: true,
      dur: Math.max(0.1, duration()),
      an: state.analysis,
      markers: state.markers,
      segments: state.segments,
      loop: state.loop,
      confMin: state.confMin,
      pitchUnit: state.pitchUnit,
      specTopHz: state.specTopHz
    }
  };
}
function drawAllGraphs() {
  if (!$('#view-review').classList.contains('is-active')) return;
  try {
    let g = screenOpts($('#cv-wave')); renderWaveform(g.ctx, g.o);
    g = screenOpts($('#cv-loud')); renderLoudness(g.ctx, g.o);
    g = screenOpts($('#cv-pitch')); renderPitch(g.ctx, g.o);
    g = screenOpts($('#cv-spec')); renderSpectrogram(g.ctx, g.o);
    updatePlayhead();
  } catch (e) {
    console.error('draw failed', e);
  }
}

/* =====================================================================
 * 書き出し（PNG / CSV / report.md / summary.json / ZIP）
 * ===================================================================== */
const ACCOMP_NOTE_EN =
  'This recording may contain karaoke accompaniment, room reflections and automatic microphone gain processing. ' +
  'Audio-derived measurements should therefore be interpreted primarily as within-user / within-condition comparison data.';

function exportOpts(kind, headline) {
  const W = 1600;
  const H = kind === 'spectrogram' ? 560 : (kind === 'pitch' ? 500 : 440);
  const cv = document.createElement('canvas');
  cv.width = W; cv.height = H;
  const ctx = cv.getContext('2d');
  return {
    cv, ctx,
    o: {
      W, H, C: palette(true), forExport: true,
      m: { l: 110, r: 40, t: 86, b: 104 },
      fs: { title: 26, axis: 17, legend: 18 },
      showAxis: true,
      title: headline,
      dur: Math.max(0.1, duration()),
      an: state.analysis,
      markers: state.markers,
      segments: state.segments,
      loop: null,
      confMin: Number(state.confMin),
      pitchUnit: state.pitchUnit,
      specTopHz: state.specTopHz
    }
  };
}
function stampFooter(ctx, o, extra) {
  const C = o.C;
  ctx.fillStyle = C.sub;
  ctx.font = `16px -apple-system, "Helvetica Neue", sans-serif`;
  ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
  ctx.fillText('SongScope v' + APP_VERSION + ' — observation only, not a singing evaluation. ' + (extra || ''), o.m.l, o.H - 18);
  // マーカー凡例（色の意味）
  ctx.textAlign = 'right';
  ctx.fillText('marker: blue = neutral / orange = 違和感 / green = 良かった・好き', o.W - o.m.r, o.H - 18);
}
function canvasToBlob(cv) {
  return new Promise(res => {
    if (cv.toBlob) cv.toBlob(b => res(b), 'image/png');
    else {
      const url = cv.toDataURL('image/png');
      const bin = atob(url.split(',')[1]);
      const u8 = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
      res(new Blob([u8], { type: 'image/png' }));
    }
  });
}
async function buildPngs() {
  const rec = state.rec;
  const head = (label) => `${rec.title || '(無題)'} — ${label}　|　duration ${fmtClock(duration())}　|　recorded ${fmtDate(rec.recordedAt || rec.createdAt)}${rec.damScore ? '　|　DAM ' + rec.damScore : ''}`;
  const out = [];
  const jobs = [
    ['waveform', 'waveform', renderWaveform],
    ['loudness', 'loudness envelope (RMS / peak)', renderLoudness],
    ['pitch', 'estimated F0', renderPitch],
    ['spectrogram', `spectrogram 0–${Math.round(Math.min(state.specTopHz, state.analysis ? state.analysis.spectrogram.topHz : state.specTopHz) / 1000)} kHz`, renderSpectrogram]
  ];
  for (const [name, label, fn] of jobs) {
    try {
      const g = exportOpts(name, head(label));
      fn(g.ctx, g.o);
      stampFooter(g.ctx, g.o, name === 'pitch' || name === 'spectrogram' ? 'Karaoke accompaniment may be mixed into pitch / spectral data.' : '');
      const blob = await canvasToBlob(g.cv);
      if (blob) out.push({ name: name + '.png', blob });
    } catch (e) {
      console.error('png failed', name, e);
    }
  }
  return out;
}

/* ---------------- CSV ---------------- */
function csvEscape(v) {
  if (v === null || v === undefined) return '';
  const s = String(v);
  return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}
function f0StatusLabel(code) {
  switch (code) {
    case 0: return 'no_f0';
    case 1: return 'low_confidence';
    case 2: return 'low_voiced_probability';
    case 3: return 'isolated_outlier';
    case 4: return 'usable';
    default: return '';
  }
}
function yinCandidateSourceLabel(code) {
  switch (code) {
    case 1: return 'threshold_first_min';
    case 2: return 'global_cmnd_min';
    case 3: return 'submultiple_2';
    case 4: return 'submultiple_3';
    default: return '';
  }
}
function f0CandidateStatusLabel(code) {
  switch (code) {
    case 0: return 'no_f0';
    case 1: return 'low_confidence';
    case 2: return 'candidate';
    default: return '';
  }
}
function f0AmbiguityLevelLabel(code) {
  switch (code) {
    case 0: return 'none';
    case 1: return 'caution';
    case 2: return 'strong';
    default: return '';
  }
}
function f0AmbiguityFlagsLabel(mask) {
  const a = [];
  if (mask & 1) a.push('local_2x_relation');
  if (mask & 2) a.push('local_3x_relation');
  if (mask & 4) a.push('local_4x_relation');
  if (mask & 8) a.push('rapid_relation');
  if (mask & 16) a.push('legacy_isolated_disagreement');
  return a.join('|');
}
function framesCsv(an) {
  const F = an.frames, n = F.timeSec.length;
  // 既存16列は順序・意味を維持し、Phase A-1列を末尾に追加する。
  const head = ['time_sec', 'rms_db', 'rms_relative_db', 'peak_db', 'crest_factor', 'f0_hz', 'f0_midi',
    'f0_confidence', 'voiced_probability', 'spectral_centroid_hz', 'spectral_bandwidth_hz',
    'spectral_rolloff_hz', 'spectral_flux', 'spectral_flatness', 'rms_delta', 'f0_delta',
    'raw_f0_hz', 'raw_f0_midi', 'filtered_f0_hz', 'usable_vocal_f0_hz', 'f0_status',
    'yin_initial_f0_hz', 'yin_selected_f0_hz', 'yin_selection_divisor',
    'yin_initial_cmnd', 'yin_selected_cmnd', 'yin_candidate_source',
    'f0_candidate_hz', 'f0_candidate_status', 'f0_ambiguity_level', 'f0_ambiguity_flags'];
  const rows = new Array(n + 1);
  rows[0] = head.join(',');
  for (let i = 0; i < n; i++) {
    rows[i + 1] = [
      F.timeSec[i].toFixed(3), num(F.rmsDb[i], 2), num(F.rmsRelDb[i], 2), num(F.peakDb[i], 2), num(F.crest[i], 3),
      num(F.f0Hz[i], 2), num(F.f0Midi[i], 3), num(F.f0Conf[i], 3), num(F.voicedProb[i], 3),
      num(F.centroid[i], 1), num(F.bandwidth[i], 1), num(F.rolloff[i], 1), num(F.flux[i], 5), num(F.flatness[i], 5),
      num(F.rmsDelta[i], 3), num(F.f0Delta[i], 3),
      num(F.rawF0Hz && F.rawF0Hz[i], 2), num(F.rawF0Midi && F.rawF0Midi[i], 3),
      num(F.filteredF0Hz && F.filteredF0Hz[i], 2), num(F.usableVocalF0Hz && F.usableVocalF0Hz[i], 2),
      f0StatusLabel(F.f0Status ? F.f0Status[i] : null),
      num(F.yinInitialF0Hz && F.yinInitialF0Hz[i], 2),
      num(F.yinSelectedF0Hz && F.yinSelectedF0Hz[i], 2),
      num(F.yinSelectionDivisor && F.yinSelectionDivisor[i], 0),
      num(F.yinInitialCmnd && F.yinInitialCmnd[i], 5),
      num(F.yinSelectedCmnd && F.yinSelectedCmnd[i], 5),
      yinCandidateSourceLabel(F.yinCandidateSource ? F.yinCandidateSource[i] : null),
      num(F.f0CandidateHz && F.f0CandidateHz[i], 2),
      f0CandidateStatusLabel(F.f0CandidateStatus ? F.f0CandidateStatus[i] : null),
      f0AmbiguityLevelLabel(F.f0AmbiguityLevel ? F.f0AmbiguityLevel[i] : null),
      f0AmbiguityFlagsLabel(F.f0AmbiguityFlags ? F.f0AmbiguityFlags[i] : 0)
    ].join(',');
  }
  return rows.join('\n') + '\n';
}
function markersCsv() {
  const rows = ['marker_id,time_sec,tag,memo,created_at'];
  for (const m of state.markers) {
    rows.push([m.markerId, m.timeSec.toFixed(2), csvEscape(m.tag), csvEscape(m.memo), m.createdAt].join(','));
  }
  return rows.join('\n') + '\n';
}
function userSegmentsCsv() {
  const head = ['segment_id', 'start_sec', 'end_sec', 'duration_sec', 'tag', 'memo', 'mean_rms_db', 'max_rms_db',
    'rms_range_db', 'median_f0_hz', 'min_f0_hz', 'max_f0_hz', 'mean_f0_confidence', 'active_ratio',
    'spectral_centroid_mean_hz', 'spectral_flux_mean'];
  const rows = [head.join(',')];
  for (const s of state.segments) {
    const st = segmentStats(s) || {};
    rows.push([s.segmentId, s.startSec.toFixed(2), s.endSec.toFixed(2), (s.endSec - s.startSec).toFixed(2),
      csvEscape(s.tag), csvEscape(s.memo), st.meanRmsDb, st.maxRmsDb, st.rmsRangeDb, st.medianF0Hz,
      st.minF0Hz, st.maxF0Hz, st.meanF0Confidence, st.activeRatio, st.spectralCentroidMeanHz, st.spectralFluxMean]
      .map(v => v === undefined || v === null ? '' : v).join(','));
  }
  return rows.join('\n') + '\n';
}
function detectedSegmentsCsv(an) {
  const head = ['segment_id', 'start_sec', 'end_sec', 'duration_sec', 'mean_rms_db', 'max_rms_db', 'rms_range_db',
    'median_f0_hz', 'min_f0_hz', 'max_f0_hz', 'mean_f0_confidence', 'active_ratio'];
  const rows = [head.join(',')];
  for (const s of (an ? an.detectedSegments : [])) {
    rows.push([s.segmentId, s.startSec, s.endSec, s.durationSec, s.meanRmsDb, s.maxRmsDb, s.rmsRangeDb,
      s.medianF0Hz, s.minF0Hz, s.maxF0Hz, s.meanF0Confidence, s.activeRatio]
      .map(v => v === undefined || v === null ? '' : v).join(','));
  }
  return rows.join('\n') + '\n';
}

/* ---------------- summary.json ---------------- */
function buildSummaryJson(an) {
  const rec = state.rec;
  return {
    schemaVersion: SCHEMA_VERSION,
    app: { name: 'SongScope', version: APP_VERSION, buildId: BUILD_ID },
    exportedAt: nowIso(),
    recording: {
      recordingId: rec.recordingId,
      recordingIdentityBasis: rec.recordingIdentityBasis || null,
      performanceId: rec.performanceId || null,
      sessionId: rec.sessionId || null,
      songId: rec.songId || null,
      songIdentityKey: rec.songIdentityKey || null,
      songIdentityVersion: rec.songIdentityVersion || null,
      songIdentityBasis: rec.songIdentityBasis || null,
      songGroupingHistory: Array.isArray(rec.songGroupingHistory) ? rec.songGroupingHistory : [],
      arrangementId: rec.arrangementId || null,
      title: rec.title || null,
      artist: rec.artist || null,
      recordedAt: rec.recordedAt || null,
      durationSec: rec.durationSec || null,
      sampleRate: rec.sampleRate || null,
      channels: rec.channels || null,
      fileName: rec.fileName || null,
      mimeType: rec.mimeType || null,
      fileSize: rec.fileSize || null,
      audioSha256: (an && an.audioSha256) || rec.audioSha256 || null,
      audioHashAlgorithm: (an && an.audioHashAlgorithm) || rec.audioHashAlgorithm || 'SHA-256',
      latestAnalysisId: rec.latestAnalysisId || (an && an.analysisId) || null,
      analysisCount: Number(rec.analysisCount || (an ? 1 : 0))
    },
    metadata: {
      damScore: rec.damScore || null,
      keyChange: rec.keyChange || null,
      octave: rec.octave || null,
      device: rec.device || null,
      scoringMode: rec.scoringMode || null,
      memo: rec.memo || null,
      recordingSetupPreset: rec.recordingSetupPreset || null
    },
    recordingLimitations: {
      containsAccompaniment: 'likely',
      note: ACCOMP_NOTE_EN,
      noteJa: 'カラオケ伴奏・部屋の反響・自動マイクゲインを含む可能性があります。ピッチ／スペクトル系の値は本人の声だけを表すものではありません。'
    },
    analysis: an ? Object.assign({}, an.summary, {
      settings: an.settings,
      analyzedAt: an.createdAt,
      analysisId: an.analysisId || null
    }) : null,
    analysisProvenance: an ? {
      analysisId: an.analysisId || null,
      appVersion: an.appVersion || APP_VERSION,
      buildId: an.buildId || BUILD_ID,
      schemaVersion: an.schemaVersion || SCHEMA_VERSION,
      audioSha256: an.audioSha256 || rec.audioSha256 || null,
      audioHashAlgorithm: an.audioHashAlgorithm || rec.audioHashAlgorithm || 'SHA-256',
      audioHashError: an.audioHashError || null,
      f0AlgorithmVersion: an.engine && an.engine.algorithmVersions ? an.engine.algorithmVersions.f0 : null,
      f0AmbiguityAlgorithmVersion: an.engine && an.engine.algorithmVersions ? an.engine.algorithmVersions.f0Ambiguity : null
    } : null,
    identityPolicy: {
      recordingIdentity: 'Same raw-audio SHA-256 reuses the same recordingId. Different analysis runs use different analysisId values.',
      songIdentity: 'songId is a persistent grouping ID once assigned. songIdentityKey is derived from NFKC-normalized title + artist (title only when artist is blank) and may change when metadata is edited. Neither asserts arrangement identity.',
      manualSongGrouping: 'A user-confirmed song-group merge may reassign songId without changing title, audio identity, or analysis history. Provenance is kept in songGroupingHistory.',
      songIdentityVersion: SONG_IDENTITY_VERSION
    },
    markers: state.markers.map(m => ({
      markerId: m.markerId, timeSec: m.timeSec, tag: m.tag, memo: m.memo || '', createdAt: m.createdAt
    })),
    userSegments: state.segments.map(s => ({
      segmentId: s.segmentId, startSec: s.startSec, endSec: s.endSec,
      durationSec: +(s.endSec - s.startSec).toFixed(3), tag: s.tag, memo: s.memo || '',
      createdAt: s.createdAt, stats: segmentStats(s)
    })),
    detectedSegments: an ? an.detectedSegments : [],
    engine: an ? Object.assign({}, an.engine, { analysisSettings: an.settings, createdAt: an.createdAt }) : null,
    interpretationPolicy: {
      principle: 'Observations only. This file contains measurements, not judgements.',
      doNot: ['歌唱力・上手さの判定', '測定値からの断定的な因果推論', '録音間の絶対dB比較', 'f0_candidate_hz を本人声の確定F0・声域として扱うこと'],
      recommended: ['同一条件に近い録音同士の比較', '仮説 → 実験 → 検証のループ']
    }
  };
}

/* ---------------- report.md ---------------- */
function buildReportMd(an) {
  const rec = state.rec;
  const s = an ? an.summary : null;
  const L = [];
  L.push('# SongScope Analysis Report', '');
  L.push('## Recording', '');
  L.push(`Title: ${rec.title || ''}`);
  L.push(`Artist: ${rec.artist || ''}`);
  L.push(`RecordedAt: ${rec.recordedAt ? fmtDate(rec.recordedAt) : ''}`);
  L.push(`Duration: ${fmtClock(rec.durationSec || 0)} (${num(rec.durationSec, 2)} s)`);
  L.push(`DAM Score: ${rec.damScore || ''}`);
  L.push(`Key: ${rec.keyChange || ''}`);
  L.push(`Octave: ${rec.octave || ''}`);
  L.push(`Device: ${rec.device || ''}`);
  L.push(`ScoringMode: ${rec.scoringMode || ''}`);
  L.push(`RecordingSetup: ${rec.recordingSetupPreset || ''}`);
  L.push(`RecordingId: ${rec.recordingId}`);
  L.push(`RecordingIdentity: ${rec.recordingIdentityBasis || ''}`);
  L.push(`SongId: ${rec.songId || ''}`);
  L.push(`SongIdentityKey: ${rec.songIdentityKey || ''}`);
  L.push(`SongIdentity: ${rec.songIdentityBasis || ''} / ${rec.songIdentityVersion || ''}`);
  if (Array.isArray(rec.songGroupingHistory) && rec.songGroupingHistory.length) {
    const g = rec.songGroupingHistory[rec.songGroupingHistory.length - 1];
    L.push(`SongGrouping: manual merge ${g.fromSongId || ''} -> ${g.toSongId || ''} (${g.mergedAt || ''})`);
  }
  L.push(`AudioSHA256: ${(an && an.audioSha256) || rec.audioSha256 || ''}`);
  L.push(`LatestAnalysisId: ${rec.latestAnalysisId || (an && an.analysisId) || ''}`);
  L.push(`AnalysisCount: ${Number(rec.analysisCount || (an ? 1 : 0))}`);
  if (rec.memo) L.push('', `Memo: ${rec.memo}`);
  L.push('', '## Recording limitations', '');
  L.push(ACCOMP_NOTE_EN, '');
  L.push('## Analysis', '');
  if (s) {
    L.push(`Legacy median F0: ${s.medianF0Hz === null ? 'null' : s.medianF0Hz + ' Hz'}`);
    L.push(`Legacy detected F0 range: ${s.minF0Hz === null ? 'null' : s.minF0Hz + ' – ' + s.maxF0Hz + ' Hz'} (do not interpret as vocal range)`);
    L.push(`Legacy valid F0 ratio: ${s.validF0FrameRatio}`);
    if (s.f0CandidateEvidence) {
      const q = s.f0CandidateEvidence;
      L.push(`F0 candidate robust distribution p05 / p50 / p95: ${q.p05Hz} / ${q.p50Hz} / ${q.p95Hz} Hz`);
      L.push(`F0 candidate evidence: ${q.candidateFrameCount}/${q.totalFrameCount} frames (${q.candidateFrameRatio}), approx ${q.candidateDurationSec} s`);
      L.push(`F0 ambiguity heuristic: strong=${q.ambiguity.strongFrameCount}, caution=${q.ambiguity.cautionFrameCount}, any=${q.ambiguity.anyFrameCount} (${q.ambiguity.anyRatioOfCandidate} of candidates)`);
      L.push('F0 candidate note: candidate/ambiguity values are observations from mixed karaoke audio; they do not identify the singer and are not a confirmed vocal range.');
    }
    L.push('');
    L.push(`Median RMS: ${s.medianRmsDb} dBFS`);
    L.push(`RMS Range: ${s.rmsRangeDb} dB`);
    L.push(`Peak: ${s.peakDb} dBFS`);
    L.push(`Loudness reference (0 dB of rms_relative_db): ${s.loudnessReferenceDb} dBFS`);
    L.push('');
    L.push(`Detected segments: ${s.detectedSegmentCount} (total ${s.detectedSegmentTotalSec} s)`);
    L.push('');
    L.push('Frame settings: ' + s.frameSizeMs + ' ms frame / ' + s.hopSizeMs + ' ms hop @ ' + s.analysisSampleRate + ' Hz');
    L.push('AnalysisId: ' + (an.analysisId || ''));
    L.push('AppVersion: ' + (an.appVersion || APP_VERSION));
    L.push('BuildId: ' + (an.buildId || BUILD_ID));
    L.push('SchemaVersion: ' + (an.schemaVersion || SCHEMA_VERSION));
    L.push('Engine: ' + an.engine.analysisEngineName + ' v' + an.engine.analysisEngineVersion);
    L.push('F0 algorithm: ' + an.engine.algorithmNames.f0 + ' v' + an.engine.algorithmVersions.f0);
    L.push('minimumConfidence: ' + an.settings.minimumConfidence);
    if (s.yinDiagnostics) {
      L.push('YIN selection counts: unchanged=' + s.yinDiagnostics.unchanged +
        ', divisor2=' + s.yinDiagnostics.divisor2 +
        ', divisor3=' + s.yinDiagnostics.divisor3 +
        ', noCandidate=' + s.yinDiagnostics.noCandidate);
    }
    L.push('Phase B-lite keeps Phase A-3 audio measurements unchanged and adds stable recording/song identity plus compact analysis-run history. songId remains stable after assignment; songIdentityKey tracks editable normalized metadata.');
    if (an.engine.algorithmVersions.f0Ambiguity) L.push('F0 ambiguity heuristic: ' + an.engine.algorithmNames.f0Ambiguity + ' v' + an.engine.algorithmVersions.f0Ambiguity);
    L.push('Experimental features (jitter / shimmer / HNR / CPP / formants / MFCC): not implemented in v0.2 Phase B-lite.');
  } else {
    L.push('Analysis not available for this recording (decode or analysis failed).');
    L.push('User markers and segments below are still valid observations.');
  }
  L.push('', '## User markers', '');
  if (!state.markers.length) L.push('(none)');
  for (const m of state.markers) {
    L.push(fmtClock(m.timeSec));
    L.push(`Tag: ${m.tag}`);
    if (m.memo) L.push(`Memo: ${m.memo}`);
    L.push('');
  }
  L.push('## User segments', '');
  if (!state.segments.length) L.push('(none)');
  for (const sg of state.segments) {
    const st = segmentStats(sg);
    L.push(`${fmtClock(sg.startSec)} - ${fmtClock(sg.endSec)}`);
    L.push(`Tag: ${sg.tag}`);
    if (sg.memo) L.push(`Memo: ${sg.memo}`);
    L.push('');
    if (st) {
      L.push(`Mean RMS: ${st.meanRmsDb} dBFS`);
      L.push(`RMS Range: ${st.rmsRangeDb} dB`);
      L.push(`Median F0: ${st.medianF0Hz === null ? 'null' : st.medianF0Hz + ' Hz'}`);
      L.push(`F0 range: ${st.minF0Hz === null ? 'null' : st.minF0Hz + ' – ' + st.maxF0Hz + ' Hz'}`);
      L.push(`Mean F0 confidence: ${st.meanF0Confidence}`);
      L.push(`Active ratio: ${st.activeRatio}`);
      L.push('');
    }
  }
  L.push('## Detected active segments (engine)', '');
  if (an && an.detectedSegments.length) {
    L.push('| start | end | dur | mean RMS dB | median F0 Hz | mean F0 conf |');
    L.push('|---|---|---|---|---|---|');
    for (const d of an.detectedSegments.slice(0, 200)) {
      L.push(`| ${fmtClock(d.startSec)} | ${fmtClock(d.endSec)} | ${d.durationSec} | ${d.meanRmsDb} | ${d.medianF0Hz === null ? 'null' : d.medianF0Hz} | ${d.meanF0Confidence} |`);
    }
    if (an.detectedSegments.length > 200) L.push(`| … | | | | | | (${an.detectedSegments.length} segments in detected_segments.csv) |`);
  } else L.push('(none)');
  L.push('', '## Files', '');
  L.push('summary.json', 'analysis_history.json', 'frames.csv', 'markers.csv', 'user_segments.csv', 'detected_segments.csv', '');
  L.push('waveform.png', 'loudness.png', 'pitch.png', 'spectrogram.png');
  L.push('', '## Important', '');
  L.push('This application does not diagnose singing ability.');
  L.push('The measurements above are observations for later comparison and hypothesis testing.');
  L.push('');
  L.push('Suggested use: treat every number as an observation, form a hypothesis, design the next recording as an experiment, then compare against this file.');
  L.push('');
  return L.join('\n');
}

/* ---------------- ZIP ---------------- */
async function doExport() {
  if (!state.rec) return;
  const an = state.analysis;
  const rec = state.rec;
  try {
    busy('書き出し中', 'グラフ画像を生成しています…', 10);
    const files = [];
    const pngs = await buildPngs();
    $('#busy-bar').style.width = '45%';
    $('#busy-msg').textContent = 'データファイルを作成しています…';
    await new Promise(r => setTimeout(r, 10));

    // analysisHistory を先に取得し、export直前にもrecording側の最新情報を同期する。
    // これにより、同一音源の再取込→即exportでも stale な latestAnalysisId / analysisCount を出さない。
    let analysisHistory = [];
    try { analysisHistory = (await dbByRec('analysisHistory', rec.recordingId)).sort((a, b) => String(a.createdAt || '').localeCompare(String(b.createdAt || ''))); }
    catch (e) { }
    if (an && an.analysisId) rec.latestAnalysisId = an.analysisId;
    if (analysisHistory.length) rec.analysisCount = analysisHistory.length;

    files.push({ name: 'report.md', data: buildReportMd(an) });
    files.push({ name: 'summary.json', data: JSON.stringify(buildSummaryJson(an), null, 2) });
    files.push({ name: 'analysis_history.json', data: JSON.stringify({
      schemaVersion: SCHEMA_VERSION,
      recordingId: rec.recordingId,
      audioSha256: rec.audioSha256 || (an && an.audioSha256) || null,
      latestAnalysisId: rec.latestAnalysisId || (an && an.analysisId) || null,
      analyses: analysisHistory
    }, null, 2) });
    files.push({ name: 'markers.csv', data: markersCsv() });
    files.push({ name: 'user_segments.csv', data: userSegmentsCsv() });
    files.push({ name: 'detected_segments.csv', data: detectedSegmentsCsv(an) });
    if (an) files.push({ name: 'frames.csv', data: framesCsv(an) });

    for (const p of pngs) files.push({ name: p.name, data: new Uint8Array(await p.blob.arrayBuffer()) });

    if ($('#chk-include-audio').checked) {
      $('#busy-msg').textContent = '元音声を追加しています…';
      const a = await dbGet('audio', rec.recordingId);
      if (a && a.blob) {
        const ext = (rec.fileName && rec.fileName.match(/\.[a-z0-9]+$/i)) ? rec.fileName.match(/\.[a-z0-9]+$/i)[0] : '.m4a';
        files.push({ name: 'original_audio' + ext, data: new Uint8Array(await a.blob.arrayBuffer()) });
      }
    }
    $('#busy-bar').style.width = '80%';
    $('#busy-msg').textContent = 'ZIPをまとめています…';
    await new Promise(r => setTimeout(r, 10));

    const stamp = new Date().toISOString().replace(/[-:]/g, '').slice(0, 15);
    const zipName = `songscope_${safeName(rec.title)}_${stamp}.zip`;
    const blob = SongScopeZip.createZip(files);
    $('#busy-bar').style.width = '100%';
    closeSheet();
    const how = await saveBlob(blob, zipName);
    if (how !== 'cancelled') toast(`${zipName}（${fmtBytes(blob.size)}）を書き出しました`);
  } catch (e) {
    closeSheet();
    console.error(e);
    toast('書き出しに失敗しました：' + ((e && e.message) || ''));
  }
}

/* ---------------- 全データバックアップ ---------------- */
async function backupAll() {
  try {
    busy('バックアップ', '全プロジェクトを収集しています…', 20);
    const recs = await dbAll('recordings');
    const out = { schemaVersion: SCHEMA_VERSION, app: 'SongScope', appVersion: APP_VERSION, exportedAt: nowIso(), settings, recordings: [] };
    for (const r of recs) {
      const mk = await dbByRec('markers', r.recordingId);
      const sg = await dbByRec('segments', r.recordingId);
      const an = await dbGet('analysis', r.recordingId);
      const hist = await dbByRec('analysisHistory', r.recordingId).catch(() => []);
      out.recordings.push({
        recording: r,
        markers: mk,
        segments: sg,
        analysisHistory: hist,
        analysisSummary: an ? {
          analysisId: an.analysisId || null, appVersion: an.appVersion || null, buildId: an.buildId || null,
          audioSha256: an.audioSha256 || null, summary: an.summary, settings: an.settings,
          engine: an.engine, detectedSegments: an.detectedSegments, createdAt: an.createdAt
        } : null
      });
    }
    try { out.alignmentDiagnostics = await dbAll('alignmentDiagnostics'); } catch (e) { out.alignmentDiagnostics = []; }
    try { out.alignmentResults = await dbAll('alignmentResults'); } catch (e) { out.alignmentResults = []; }
    out.note = 'analysisHistoryは各解析runのcompact provenanceです。alignmentDiagnosticsは候補証拠、alignmentResultsはD1判定結果です。frames等のフレーム単位データは最新analysis以外バックアップに含めません。原本音声を保持していれば再解析できます。';
    closeSheet();
    const blob = new Blob([JSON.stringify(out, null, 2)], { type: 'application/json' });
    await saveBlob(blob, `songscope_backup_${new Date().toISOString().slice(0, 10)}.json`);
    toast('バックアップを書き出しました');
  } catch (e) {
    closeSheet();
    toast('バックアップに失敗しました');
  }
}

/* =====================================================================
 * A/B比較
 * ===================================================================== */
const cmp = {
  a: null, b: null,           // {rec, an, audio, url}
  // D1-prep time convention (fixed): reference(A) time = target(B) time + offset.
  // Therefore target(B) time = reference(A) time - offset.
  offset: 0,
  normalized: true,
  loop: { a: null, b: null, on: false }, // reference(A) time axis: start/end
  playing: null,               // 'a' | 'b' | null
  lastTime: 0,                 // reference(A) time
  rafId: 0,
  alignmentBusy: false,
  lastAlignmentDiagnostic: null,
  lastAlignmentResult: null
};

function cmpSideDuration(side) {
  const d = cmp[side];
  if (!d) return 0;
  const recDur = d.rec && isFinite(d.rec.durationSec) ? Number(d.rec.durationSec) : 0;
  const audioDur = d.audio && isFinite(d.audio.duration) ? Number(d.audio.duration) : 0;
  return Math.max(0, recDur || audioDur || 0);
}
function cmpLocalToReference(side, localTimeSec) {
  return side === 'b' ? localTimeSec + cmp.offset : localTimeSec;
}
function cmpReferenceToLocal(side, referenceTimeSec) {
  return side === 'b' ? referenceTimeSec - cmp.offset : referenceTimeSec;
}
function cmpReferenceTimeAvailable(side, referenceTimeSec) {
  const dur = cmpSideDuration(side);
  if (!(dur > 0) || !isFinite(referenceTimeSec)) return false;
  const local = cmpReferenceToLocal(side, referenceTimeSec);
  return local >= 0 && local <= dur;
}
function cmpResetMapping() {
  cmp.offset = 0;
  cmp.loop = { a: null, b: null, on: false };
  cmp.lastTime = 0;
  cmp.playing = null;
  cmp.lastAlignmentDiagnostic = null;
  cmp.lastAlignmentResult = null;
  const ar = $('#cmp-align-result'); if (ar) ar.innerHTML = '<p class="small">まだ判定していません。</p>';
  const ex = $('#btn-align-export'); if (ex) ex.hidden = true;
  const ap = $('#btn-align-apply'); if (ap) ap.hidden = true;
  const slider = $('#offset-slider');
  if (slider) slider.value = '0';
}
function cmpIdentityCheck() {
  const a = cmp.a && cmp.a.rec, b = cmp.b && cmp.b.rec;
  if (!a || !b) return { status: 'select_both', blocked: false, autoAlignmentEligible: false, message: 'AとBを選択してください。' };
  if (a.recordingId && b.recordingId && a.recordingId === b.recordingId) {
    return { status: 'same_recording', blocked: true, autoAlignmentEligible: false, message: '同じrecordingIdです。これは別歌唱比較ではありません。' };
  }
  if (a.audioSha256 && b.audioSha256 && a.audioSha256 === b.audioSha256) {
    return { status: 'same_source_audio', blocked: true, autoAlignmentEligible: false, message: 'recordingIdは異なりますがraw音声SHA-256が同一です。過去版由来の重複録音として扱い、別歌唱比較には使いません。' };
  }
  if (a.songId && b.songId && a.songId === b.songId) {
    return { status: 'same_song_candidate', blocked: false, autoAlignmentEligible: true, message: '同じsongId・別音声です。D1の自動alignment候補にできます。' };
  }
  if (a.songIdentityKey && b.songIdentityKey && a.songIdentityKey === b.songIdentityKey) {
    return { status: 'identity_uncertain', blocked: false, autoAlignmentEligible: false, message: '正規化メタデータは一致しますがsongIdが異なります。自動alignment前にidentity確認が必要です。' };
  }
  return { status: 'metadata_mismatch', blocked: false, autoAlignmentEligible: false, message: 'songIdが異なります。自動alignment対象外で、現在は手動比較のみです。' };
}
async function mergeCmpSongGroupBIntoA() {
  const a = cmp.a && cmp.a.rec, b = cmp.b && cmp.b.rec;
  if (!a || !b) { toast('AとBを選択してください'); return; }
  if (a.recordingId === b.recordingId || (a.audioSha256 && b.audioSha256 && a.audioSha256 === b.audioSha256)) {
    toast('同じ録音は曲グループ統合の対象にしません'); return;
  }
  if (!a.songId || !b.songId) { toast('songIdが不足しています'); return; }
  if (a.songId === b.songId) { toast('すでに同じ曲グループです'); updateCmpIdentityUi(); return; }

  const fromSongId = b.songId;
  const toSongId = a.songId;
  let group = await findRecordingsBySongId(fromSongId).catch(() => []);
  if (!group.length) group = [b];
  const count = group.length;
  const msg = `B側「${b.title || '(無題)'}」の曲グループ（${count}録音）を、A側「${a.title || '(無題)'}」と同じ曲としてまとめます。\n\n曲名・音声・recordingId・解析履歴は変更しません。songIdだけをA側へ統合します。よろしいですか？`;
  if (!confirm(msg)) return;

  const btn = $('#btn-song-merge-b-to-a');
  if (btn) btn.disabled = true;
  const mergedAt = nowIso();
  try {
    for (const rec of group) {
      if (!rec || rec.songId !== fromSongId) continue;
      const history = Array.isArray(rec.songGroupingHistory) ? rec.songGroupingHistory.slice() : [];
      history.push({
        method: 'manual_compare_group_merge_v1',
        mergedAt,
        fromSongId,
        toSongId,
        referenceRecordingId: a.recordingId || null,
        initiatedFromRecordingId: b.recordingId || null,
        appVersion: APP_VERSION,
        buildId: BUILD_ID
      });
      rec.songGroupingHistory = history;
      rec.songId = toSongId;
      rec.updatedAt = mergedAt;
      await dbPut('recordings', rec);
    }

    await loadRecordings();
    const freshA = await dbGet('recordings', a.recordingId).catch(() => a);
    const freshB = await dbGet('recordings', b.recordingId).catch(() => b);
    if (cmp.a) cmp.a.rec = freshA || a;
    if (cmp.b) cmp.b.rec = freshB || b;
    if (state.rec) {
      const freshState = await dbGet('recordings', state.rec.recordingId).catch(() => null);
      if (freshState) state.rec = freshState;
    }
    updateCmpIdentityUi();
    drawCompare();
    toast(`${count}録音をA側の曲グループへまとめました`);
  } catch (e) {
    console.error(e);
    toast('曲グループの統合に失敗しました');
    updateCmpIdentityUi();
  }
}

function updateCmpIdentityUi() {
  const check = cmpIdentityCheck();
  const el = $('#cmp-identity-status');
  if (el) el.textContent = '比較対象: ' + check.message;
  const ids = ['#cmp-play-a', '#cmp-play-b', '#cmp-swap', '#cmp-loop'];
  for (const id of ids) { const e = $(id); if (e) e.disabled = !!check.blocked; }
  const off = $('#offset-slider');
  if (off) off.disabled = !!check.blocked;
  const on = $('#offset-number'); if (on) on.disabled = !!check.blocked;
  const dg = $('#btn-align-diagnose'); if (dg) dg.disabled = !!check.blocked || !check.autoAlignmentEligible || cmp.alignmentBusy;
  const merge = $('#btn-song-merge-b-to-a');
  if (merge) {
    const a = cmp.a && cmp.a.rec, b = cmp.b && cmp.b.rec;
    const canMerge = !!a && !!b && !check.blocked && !!a.songId && !!b.songId && a.songId !== b.songId;
    merge.hidden = !canMerge;
    merge.disabled = !canMerge || cmp.alignmentBusy;
  }
  const mergeNote = $('#cmp-song-merge-note');
  if (mergeNote) mergeNote.hidden = !(merge && !merge.hidden);
  return check;
}
function updateCmpOffsetSliderRange() {
  const slider = $('#offset-slider');
  if (!slider) return;
  const da = cmpSideDuration('a'), db2 = cmpSideDuration('b');
  // Any overlapping global offset must satisfy -durationB <= offset <= durationA.
  const min = db2 > 0 ? -db2 : -10;
  const max = da > 0 ? da : 10;
  slider.min = String(Math.floor(min * 10) / 10);
  slider.max = String(Math.ceil(max * 10) / 10);
  if (cmp.offset < min || cmp.offset > max) cmp.offset = clamp(cmp.offset, min, max);
  slider.value = String(cmp.offset);
  const number = $('#offset-number');
  if (number) { number.min = slider.min; number.max = slider.max; number.value = cmp.offset.toFixed(1); }
}

async function openCompare() {
  stopPlayback();
  cmpStop();
  cmpResetMapping();
  showView('view-compare');
  const recs = state.recordings;
  if (recs.length < 2) toast('比較には録音が2件必要です');
  for (const id of ['#sel-a', '#sel-b']) {
    const sel = $(id);
    sel.innerHTML = '<option value="">選択してください</option>' +
      recs.map(r => `<option value="${r.recordingId}">${escapeHtml(r.title || '(無題)')} ${r.damScore ? '／' + escapeHtml(r.damScore) : ''} ${fmtDate(r.recordedAt || r.createdAt)}</option>`).join('');
  }
  if (recs[0]) { $('#sel-a').value = recs[0].recordingId; await loadCmpSide('a', recs[0].recordingId); }
  if (recs[1]) { $('#sel-b').value = recs[1].recordingId; await loadCmpSide('b', recs[1].recordingId); }
  drawCompare();
}

async function loadCmpSide(side, id) {
  const prev = cmp[side];
  if (prev) {
    try { prev.audio.pause(); } catch (e) { }
    if (prev.url) URL.revokeObjectURL(prev.url);
  }
  cmp[side] = null;
  if (!id) { drawCompare(); return; }
  const rec = await dbGet('recordings', id);
  const an = await dbGet('analysis', id).catch(() => null);
  const au = await dbGet('audio', id).catch(() => null);
  let audio = null, url = null;
  if (au && au.blob) {
    url = URL.createObjectURL(au.blob);
    audio = new Audio(url);
    audio.preload = 'metadata';
  }
  cmp[side] = { rec, an, audio, url };
  drawCompare();
}

function alignmentFeatureKey(audioSha256) {
  return audioSha256 ? `${audioSha256}:${ALIGN_FEATURE_VERSION}` : null;
}
function alignmentPairKey(hashA, hashB) {
  if (!hashA || !hashB) return null;
  const pair = [hashA, hashB].sort();
  return `${pair[0]}:${pair[1]}:${ALIGN_FEATURE_VERSION}:${ALIGN_MATCH_VERSION}`;
}
function runAlignmentWorker(message, transfer, onProgress) {
  return new Promise((resolve, reject) => {
    let w;
    try { w = new Worker('alignment-worker.js?v=' + encodeURIComponent(BUILD_ID)); }
    catch (e) { reject(new Error('alignment workerを起動できません')); return; }
    w.onmessage = ev => {
      const m = ev.data || {};
      if (m.type === 'progress') { if (onProgress) onProgress(m); }
      else if (m.type === 'feature') { w.terminate(); resolve(m.feature); }
      else if (m.type === 'done') { w.terminate(); resolve(m.result); }
      else if (m.type === 'error') { w.terminate(); reject(new Error(m.message || 'alignment worker error')); }
    };
    w.onerror = () => { try { w.terminate(); } catch (e) { } reject(new Error('alignment処理中にエラーが発生しました')); };
    w.postMessage(message, transfer || []);
  });
}
async function getAlignmentFeature(side, progressLabel) {
  const d = cmp[side];
  if (!d || !d.rec) throw new Error('録音が選択されていません');
  let hash = d.rec.audioSha256 || (d.an && d.an.audioSha256) || null;
  const au = await dbGet('audio', d.rec.recordingId).catch(() => null);
  if (!au || !au.blob) throw new Error((side === 'a' ? 'A' : 'B') + 'の原音が端末内にありません');
  if (!hash) {
    const hab = await au.blob.arrayBuffer();
    hash = await sha256Hex(hab);
    d.rec.audioSha256 = hash;
    d.rec.audioHashAlgorithm = 'SHA-256';
    await dbPut('recordings', d.rec).catch(() => { });
  }
  const key = alignmentFeatureKey(hash);
  const cached = key ? await dbGet('alignmentFeatures', key).catch(() => null) : null;
  if (cached && cached.featureAlgorithmVersion === ALIGN_FEATURE_VERSION && cached.chroma && cached.valid) return cached;

  const ab = await au.blob.arrayBuffer();
  const audioBuffer = await decodeAudio(ab);
  const mono = downmixMono(audioBuffer);
  const srcRate = audioBuffer.sampleRate;
  const feature = await runAlignmentWorker({ type: 'extract', pcm: mono, sampleRate: srcRate, config: {} }, [mono.buffer], m => {
    const pct = Math.max(1, Math.min(99, Number(m.pct || 0)));
    const el = $('#cmp-align-result'); if (el) el.innerHTML = `<p class="small">${escapeHtml(progressLabel)} 特徴抽出中… ${pct}%</p>`;
  });
  feature.featureKey = key;
  feature.audioSha256 = hash;
  feature.recordingId = d.rec.recordingId;
  feature.createdAt = nowIso();
  await dbPut('alignmentFeatures', feature);
  return feature;
}
function alignmentCandidateHtml(c) {
  if (!c) return '';
  const sign = c.offsetSec >= 0 ? '+' : '';
  const rot = c.chromaRotationSemitones >= 0 ? '+' + c.chromaRotationSemitones : String(c.chromaRotationSemitones);
  return `<div class="small mono">#${c.rank} offset ${sign}${c.offsetSec.toFixed(1)} s / chroma回転 ${rot} st / similarity ${c.meanSimilarity.toFixed(3)} / overlap ${c.overlapSec.toFixed(1)} s / target ${(c.targetCoverageRatio*100).toFixed(1)}%</div>`;
}
function alignmentStatusLabel(status) {
  if (status === 'resolved') return 'resolved（位置合わせ成立）';
  if (status === 'ambiguous') return 'ambiguous（複数候補）';
  return 'unresolved（十分に確定できない）';
}
function renderAlignmentDiagnostic(diag) {
  const el = $('#cmp-align-result'); if (!el) return;
  const candidates = (diag && diag.candidates) || [];
  const decision = (diag && diag.decision) || { status: 'unresolved' };
  const apply = $('#btn-align-apply');
  if (!candidates.length) {
    el.innerHTML = '<p><b>unresolved</b></p><p class="small">有効な候補を作れませんでした。手動オフセットは引き続き利用できます。</p>';
    if (apply) apply.hidden = true;
    return;
  }
  const rev = diag.reverseCheck;
  const drift = diag.driftProbe;
  const selected = candidates[0];
  let html = `<p><b>${escapeHtml(alignmentStatusLabel(decision.status))}</b></p>`;
  if (decision.status === 'resolved' && selected) {
    html += `<p class="small mono">採用候補: ${selected.offsetSec >= 0 ? '+' : ''}${selected.offsetSec.toFixed(1)} s / chroma回転 ${selected.chromaRotationSemitones >= 0 ? '+' : ''}${selected.chromaRotationSemitones} st</p>`;
  }
  html += '<p class="small"><b>上位候補</b></p>' + candidates.map(alignmentCandidateHtml).join('');
  if (decision.candidateClusters && decision.candidateClusters.length) {
    const cls = decision.candidateClusters.slice(0,4).map(c => `#${c.rank} ${c.representativeOffsetSec >= 0 ? '+' : ''}${c.representativeOffsetSec.toFixed(1)}s/${c.chromaRotationSemitones >= 0 ? '+' : ''}${c.chromaRotationSemitones}st peak ${c.peakRankingScore.toFixed(3)}`);
    html += `<p class="small mono">独立候補cluster: ${cls.join(' / ')}</p>`;
  }
  if (rev) html += `<p class="small mono">逆向き検査: offset ${rev.bestOffsetSec >= 0 ? '+' : ''}${rev.bestOffsetSec.toFixed(1)} s / 往復残差 ${rev.inverseOffsetResidualSec === null ? '—' : rev.inverseOffsetResidualSec.toFixed(1)+' s'}</p>`;
  if (drift && drift.segments && drift.segments.length) html += `<p class="small mono">drift probe: ${drift.segments.map(x => `${x.label} ${x.offsetSec >= 0 ? '+' : ''}${x.offsetSec.toFixed(1)}s`).join(' / ')} / range ${drift.offsetRangeSec === null ? '—' : drift.offsetRangeSec.toFixed(1)+'s'}</p>`;
  if (decision.reasons && decision.reasons.length) html += `<p class="small">判定理由: ${escapeHtml(decision.reasons.join(', '))}</p>`;
  html += '<p class="small">similarityは確率ではありません。D1は候補の質・証拠量・往復整合性・drift・独立候補clusterをまとめて保守的に判定します。</p>';
  el.innerHTML = html;
  if (apply) apply.hidden = decision.status !== 'resolved';
}
function buildCanonicalAlignmentResult(diag) {
  if (!diag || !diag.decision) return null;
  const best = diag.candidates && diag.candidates.length ? diag.candidates[0] : null;
  const ah = diag.reference && diag.reference.audioSha256, bh = diag.target && diag.target.audioSha256;
  if (!ah || !bh) return null;
  const lowFirst = ah < bh;
  const lowHash = lowFirst ? ah : bh, highHash = lowFirst ? bh : ah;
  let canonical = null;
  if (diag.decision.status === 'resolved' && best) {
    // Current convention: A(reference) = B(target) + offset.
    // Canonical convention: high_time = low_time + canonicalOffsetHighFromLowSec.
    const canonicalOffset = lowFirst ? -best.offsetSec : best.offsetSec;
    const canonicalSemitone = lowFirst ? -best.chromaRotationSemitones : best.chromaRotationSemitones;
    canonical = {
      lowAudioSha256: lowHash,
      highAudioSha256: highHash,
      mappingConvention: 'high_time_sec = low_time_sec + canonical_offset_high_from_low_sec',
      canonicalOffsetHighFromLowSec: +canonicalOffset.toFixed(3),
      canonicalChromaSemitoneHighRelativeToLow: canonicalSemitone
    };
  }
  return {
    pairKey: diag.pairKey,
    alignmentId: uid('aln'),
    status: diag.decision.status,
    algorithm: { featureVersion: diag.featureAlgorithmVersion, matchingVersion: diag.matchingAlgorithmVersion },
    canonical,
    latestDecision: diag.decision,
    sourceDiagnosticId: diag.diagnosticId,
    reference: diag.reference,
    target: diag.target,
    updatedAt: nowIso(),
    appVersion: APP_VERSION,
    buildId: BUILD_ID
  };
}
function applyResolvedAlignment() {
  const d = cmp.lastAlignmentDiagnostic;
  if (!d || !d.decision || d.decision.status !== 'resolved' || !d.candidates || !d.candidates.length) { toast('resolvedの位置合わせ結果がありません'); return; }
  const best = d.candidates[0];
  cmp.offset = Math.round(best.offsetSec * 10) / 10;
  const sl = $('#offset-slider'), numel = $('#offset-number');
  updateCmpOffsetSliderRange();
  if (sl) sl.value = String(cmp.offset);
  if (numel) numel.value = cmp.offset.toFixed(1);
  drawCompare();
  toast(`位置合わせ ${cmp.offset >= 0 ? '+' : ''}${cmp.offset.toFixed(1)}秒を反映しました`);
}
async function diagnoseAlignment() {
  if (cmp.alignmentBusy) return;
  const check = cmpIdentityCheck();
  if (!check.autoAlignmentEligible) { toast(check.message); return; }
  if (!cmp.a || !cmp.b) { toast('AとBを選択してください'); return; }
  cmp.alignmentBusy = true;
  const btn = $('#btn-align-diagnose'); if (btn) btn.disabled = true;
  const ex = $('#btn-align-export'); if (ex) ex.hidden = true;
  const ap = $('#btn-align-apply'); if (ap) ap.hidden = true;
  try {
    const fa = await getAlignmentFeature('a', 'A');
    const fb = await getAlignmentFeature('b', 'B');
    const el = $('#cmp-align-result'); if (el) el.innerHTML = '<p class="small">global offsetを探索し、D1判定中…</p>';
    const diagCore = await runAlignmentWorker({ type: 'match', reference: fa, target: fb, config: {} }, [], m => {
      const pct = Math.max(1, Math.min(99, Number(m.pct || 0)));
      const e = $('#cmp-align-result'); if (e) e.innerHTML = `<p class="small">global offsetを探索し、D1判定中… ${pct}%</p>`;
    });
    const diag = Object.assign({}, diagCore, {
      diagnosticId: uid('aldiag'),
      pairKey: alignmentPairKey(fa.audioSha256, fb.audioSha256),
      createdAt: nowIso(),
      appVersion: APP_VERSION,
      buildId: BUILD_ID,
      reference: { recordingId: cmp.a.rec.recordingId, audioSha256: fa.audioSha256, title: cmp.a.rec.title || '' },
      target: { recordingId: cmp.b.rec.recordingId, audioSha256: fb.audioSha256, title: cmp.b.rec.title || '' },
      featureSummary: {
        reference: { frameCount: fa.frameCount, hopSec: fa.hopSec, durationSec: fa.durationSec },
        target: { frameCount: fb.frameCount, hopSec: fb.hopSec, durationSec: fb.durationSec }
      }
    });
    cmp.lastAlignmentDiagnostic = diag;
    await dbPut('alignmentDiagnostics', diag).catch(() => { });
    const result = buildCanonicalAlignmentResult(diag);
    cmp.lastAlignmentResult = result;
    if (result) await dbPut('alignmentResults', result).catch(() => { });
    renderAlignmentDiagnostic(diag);
    if (ex) ex.hidden = false;
    toast(diag.decision && diag.decision.status === 'resolved' ? 'D1位置合わせが resolved になりました' : 'D1位置合わせの判定が完了しました');
  } catch (e) {
    const el = $('#cmp-align-result'); if (el) el.innerHTML = `<p class="small">診断に失敗しました: ${escapeHtml((e && e.message) || String(e))}</p>`;
    toast('位置合わせ診断に失敗しました');
  } finally {
    cmp.alignmentBusy = false;
    updateCmpIdentityUi();
  }
}
async function exportAlignmentDiagnostic() {
  const d = cmp.lastAlignmentDiagnostic;
  if (!d) { toast('先に位置合わせを診断してください'); return; }
  const a = safeName((d.reference && d.reference.title) || 'A');
  const b = safeName((d.target && d.target.title) || 'B');
  await saveBlob(new Blob([JSON.stringify(d, null, 2)], { type: 'application/json' }), `songscope_alignment_${a}_vs_${b}_${new Date().toISOString().replace(/[-:]/g,'').slice(0,15)}.json`);
}

async function getResolvedAlignmentForCurrentPair() {
  if (!cmp.a || !cmp.b || !cmp.a.rec || !cmp.b.rec) throw new Error('AとBを選択してください');
  const aHash = cmp.a.rec.audioSha256 || (cmp.a.an && cmp.a.an.audioSha256) || null;
  const bHash = cmp.b.rec.audioSha256 || (cmp.b.an && cmp.b.an.audioSha256) || null;
  if (!aHash || !bHash) throw new Error('A/BのaudioSha256が不足しています');
  const key = alignmentPairKey(aHash, bHash);
  const result = await dbGet('alignmentResults', key).catch(() => null);
  if (!result || result.status !== 'resolved' || !result.canonical) {
    throw new Error('このA/Bには保存済みのresolved D1位置合わせがありません。先に「位置合わせを判定」を実行してください');
  }
  const c = result.canonical;
  const canonicalOffset = Number(c.canonicalOffsetHighFromLowSec);
  if (!isFinite(canonicalOffset)) throw new Error('保存済みD1のoffsetが不正です');
  let offsetSec;
  if (aHash === c.highAudioSha256 && bHash === c.lowAudioSha256) offsetSec = canonicalOffset;
  else if (aHash === c.lowAudioSha256 && bHash === c.highAudioSha256) offsetSec = -canonicalOffset;
  else throw new Error('保存済みD1の音声pairと現在のA/Bが一致しません');
  return { result, offsetSec: +offsetSec.toFixed(3), aHash, bHash };
}

function finiteQuantile(values, p) {
  const a = values.filter(v => isFinite(v)).sort((x, y) => x - y);
  if (!a.length) return null;
  if (a.length === 1) return +a[0].toFixed(6);
  const pos = (a.length - 1) * p;
  const lo = Math.floor(pos), hi = Math.ceil(pos), f = pos - lo;
  const v = lo === hi ? a[lo] : a[lo] * (1 - f) + a[hi] * f;
  return +v.toFixed(6);
}
function d2FrameHopSec(an) {
  const configured = an && an.settings && Number(an.settings.hopSizeMs);
  if (isFinite(configured) && configured > 0) return configured / 1000;
  const t = an && an.frames && an.frames.timeSec;
  if (t && t.length > 1) {
    const diffs = [];
    for (let i = 1; i < Math.min(t.length, 101); i++) {
      const d = Number(t[i]) - Number(t[i - 1]);
      if (isFinite(d) && d > 0) diffs.push(d);
    }
    const q = finiteQuantile(diffs, 0.5);
    if (isFinite(q) && q > 0) return q;
  }
  return 0.02;
}
function d2AnalysisDurationSec(side) {
  const d = cmp[side];
  if (!d) return 0;
  const recDur = d.rec && Number(d.rec.durationSec);
  if (isFinite(recDur) && recDur > 0) return recDur;
  const F = d.an && d.an.frames;
  const hop = d2FrameHopSec(d.an);
  if (F && F.timeSec && F.timeSec.length) return Math.max(0, Number(F.timeSec[F.timeSec.length - 1]) + hop);
  return cmpSideDuration(side);
}
function d2SideWindowStats(side, requestedReferenceStartSec, requestedReferenceEndSec, pairReferenceStartSec, pairReferenceEndSec, offsetSec) {
  const d = cmp[side];
  if (!d || !d.an || !d.an.frames) return null;
  const F = d.an.frames;
  const hop = d2FrameHopSec(d.an);
  const dur = d2AnalysisDurationSec(side);
  const requestedLocalStart = side === 'b' ? requestedReferenceStartSec - offsetSec : requestedReferenceStartSec;
  const requestedLocalEnd = side === 'b' ? requestedReferenceEndSec - offsetSec : requestedReferenceEndSec;
  const hasPair = isFinite(pairReferenceStartSec) && isFinite(pairReferenceEndSec) && pairReferenceEndSec > pairReferenceStartSec;
  const localStart = hasPair ? (side === 'b' ? pairReferenceStartSec - offsetSec : pairReferenceStartSec) : null;
  const localEnd = hasPair ? (side === 'b' ? pairReferenceEndSec - offsetSec : pairReferenceEndSec) : null;
  const clippedStart = hasPair ? Math.max(0, localStart) : 0;
  const clippedEnd = hasPair ? Math.min(dur, localEnd) : 0;
  const availableDurationSec = hasPair ? Math.max(0, clippedEnd - clippedStart) : 0;
  const windowDurationSec = Math.max(0, requestedReferenceEndSec - requestedReferenceStartSec);
  const rmsRel = [], f0Candidate = [], f0ConfCandidate = [];
  let frameCount = 0, candidateFrameCount = 0, ambiguityFrameCount = 0, cautionFrameCount = 0, strongFrameCount = 0;
  // time_sec is a floating-point frame grid. Use a tiny tolerance so an intended
  // [start,end) boundary does not randomly become 499/501 frames after offset mapping.
  // Frame times are stored in Float32 in memory; at ~260 s their rounding error can be
  // several 1e-5 s, so 1e-7 s was too small. Keep the tolerance tiny relative to the
  // 20 ms frame hop while safely covering Float32 quantization.
  const timeEpsSec = Math.max(1e-4, hop * 0.001);
  if (availableDurationSec > 0) {
    const n = F.timeSec.length;
    for (let i = 0; i < n; i++) {
      const t = Number(F.timeSec[i]);
      if (t < clippedStart - timeEpsSec) continue;
      if (t >= clippedEnd - timeEpsSec) break;
      frameCount++;
      const r = Number(F.rmsRelDb && F.rmsRelDb[i]);
      if (isFinite(r)) rmsRel.push(r);
      const hz = Number(F.f0CandidateHz && F.f0CandidateHz[i]);
      if (isFinite(hz)) {
        candidateFrameCount++;
        f0Candidate.push(hz);
        const conf = Number(F.f0Conf && F.f0Conf[i]);
        if (isFinite(conf)) f0ConfCandidate.push(conf);
        const amb = Number(F.f0AmbiguityLevel && F.f0AmbiguityLevel[i]) || 0;
        if (amb > 0) ambiguityFrameCount++;
        if (amb === 1) cautionFrameCount++;
        if (amb >= 2) strongFrameCount++;
      }
    }
  }
  const r = (v, d = 6) => isFinite(v) ? +Number(v).toFixed(d) : null;
  return {
    requestedLocalStartSec: r(requestedLocalStart, 3),
    requestedLocalEndSec: r(requestedLocalEnd, 3),
    localStartSec: localStart === null ? null : r(localStart, 3),
    localEndSec: localEnd === null ? null : r(localEnd, 3),
    availableDurationSec: r(availableDurationSec, 3),
    coverageRatio: windowDurationSec > 0 ? r(availableDurationSec / windowDurationSec, 6) : null,
    frameHopSec: r(hop, 6),
    frameCount,
    f0CandidateEvidence: {
      candidateFrameCount,
      candidateDurationSec: r(candidateFrameCount * hop, 3),
      candidateRatioAmongAvailableFrames: frameCount ? r(candidateFrameCount / frameCount, 6) : null,
      ambiguityFrameCount,
      ambiguityDurationSec: r(ambiguityFrameCount * hop, 3),
      ambiguityRatioAmongCandidates: candidateFrameCount ? r(ambiguityFrameCount / candidateFrameCount, 6) : null,
      cautionFrameCount,
      strongFrameCount,
      strongAmbiguityRatioAmongCandidates: candidateFrameCount ? r(strongFrameCount / candidateFrameCount, 6) : null
    },
    observations: {
      rmsRelativeDb: {
        p10: finiteQuantile(rmsRel, 0.10),
        p50: finiteQuantile(rmsRel, 0.50),
        p90: finiteQuantile(rmsRel, 0.90)
      },
      f0CandidateHz: {
        p10: finiteQuantile(f0Candidate, 0.10),
        p50: finiteQuantile(f0Candidate, 0.50),
        p90: finiteQuantile(f0Candidate, 0.90),
        confidenceP50: finiteQuantile(f0ConfCandidate, 0.50)
      }
    }
  };
}
function d2RecordingDescriptor(side) {
  const d = cmp[side] || {}, rec = d.rec || {}, an = d.an || {};
  return {
    role: side === 'a' ? 'reference_A' : 'target_B',
    recordingId: rec.recordingId || null,
    audioSha256: rec.audioSha256 || an.audioSha256 || null,
    songId: rec.songId || null,
    songIdentityKey: rec.songIdentityKey || null,
    title: rec.title || '',
    artist: rec.artist || '',
    recordedAt: rec.recordedAt || rec.createdAt || null,
    durationSec: d2AnalysisDurationSec(side),
    analysisId: an.analysisId || rec.latestAnalysisId || null,
    analysisSchemaVersion: an.schemaVersion || null,
    analysisAppVersion: an.appVersion || null,
    analysisBuildId: an.buildId || null,
    userMetadata: {
      damScore: rec.damScore || null,
      keyChange: rec.keyChange || null,
      octave: rec.octave || null,
      device: rec.device || null,
      scoringMode: rec.scoringMode || null,
      recordingSetupPreset: rec.recordingSetupPreset || null,
      source: 'recording_metadata'
    }
  };
}
function d2MapMarkers(rows, side, offsetSec) {
  return (rows || []).map(m => ({
    markerId: m.markerId || null,
    localTimeSec: isFinite(Number(m.timeSec)) ? +Number(m.timeSec).toFixed(3) : null,
    referenceTimeSec: isFinite(Number(m.timeSec)) ? +(side === 'b' ? Number(m.timeSec) + offsetSec : Number(m.timeSec)).toFixed(3) : null,
    tag: m.tag || '', memo: m.memo || '', createdAt: m.createdAt || null,
    evidenceType: 'user_reported_marker'
  }));
}
function d2MapUserSegments(rows, side, offsetSec) {
  return (rows || []).map(x => ({
    segmentId: x.segmentId || null,
    localStartSec: isFinite(Number(x.startSec)) ? +Number(x.startSec).toFixed(3) : null,
    localEndSec: isFinite(Number(x.endSec)) ? +Number(x.endSec).toFixed(3) : null,
    referenceStartSec: isFinite(Number(x.startSec)) ? +(side === 'b' ? Number(x.startSec) + offsetSec : Number(x.startSec)).toFixed(3) : null,
    referenceEndSec: isFinite(Number(x.endSec)) ? +(side === 'b' ? Number(x.endSec) + offsetSec : Number(x.endSec)).toFixed(3) : null,
    tag: x.tag || '', memo: x.memo || '', createdAt: x.createdAt || null,
    evidenceType: 'user_reported_segment'
  }));
}
function d2WindowsCsv(pkg) {
  const head = [
    'window_index','reference_start_sec','reference_end_sec','pair_reference_start_sec','pair_reference_end_sec','pair_available_duration_sec','pair_coverage_ratio','comparison_coverage_status',
    'a_requested_local_start_sec','a_requested_local_end_sec','a_local_start_sec','a_local_end_sec','a_available_duration_sec','a_coverage_ratio','a_frame_count','a_f0_candidate_frames','a_f0_candidate_ratio','a_f0_ambiguity_frames','a_f0_ambiguity_ratio','a_f0_strong_ambiguity_ratio','a_rms_rel_p10','a_rms_rel_p50','a_rms_rel_p90','a_f0_candidate_p10_hz','a_f0_candidate_p50_hz','a_f0_candidate_p90_hz','a_f0_confidence_p50',
    'b_requested_local_start_sec','b_requested_local_end_sec','b_local_start_sec','b_local_end_sec','b_available_duration_sec','b_coverage_ratio','b_frame_count','b_f0_candidate_frames','b_f0_candidate_ratio','b_f0_ambiguity_frames','b_f0_ambiguity_ratio','b_f0_strong_ambiguity_ratio','b_rms_rel_p10','b_rms_rel_p50','b_rms_rel_p90','b_f0_candidate_p10_hz','b_f0_candidate_p50_hz','b_f0_candidate_p90_hz','b_f0_confidence_p50'
  ];
  const rows = [head.join(',')];
  const val = v => { if (v === null || v === undefined) return ''; if (typeof v === 'number') return isFinite(v) ? String(v) : ''; return String(v); };
  for (const w of pkg.windows || []) {
    const a=w.a, b=w.b, ae=a.f0CandidateEvidence, be=b.f0CandidateEvidence, ao=a.observations, bo=b.observations;
    rows.push([
      w.windowIndex,w.referenceStartSec,w.referenceEndSec,w.pairReferenceStartSec,w.pairReferenceEndSec,w.pairAvailableDurationSec,w.pairCoverageRatio,w.comparisonCoverageStatus,
      a.requestedLocalStartSec,a.requestedLocalEndSec,a.localStartSec,a.localEndSec,a.availableDurationSec,a.coverageRatio,a.frameCount,ae.candidateFrameCount,ae.candidateRatioAmongAvailableFrames,ae.ambiguityFrameCount,ae.ambiguityRatioAmongCandidates,ae.strongAmbiguityRatioAmongCandidates,ao.rmsRelativeDb.p10,ao.rmsRelativeDb.p50,ao.rmsRelativeDb.p90,ao.f0CandidateHz.p10,ao.f0CandidateHz.p50,ao.f0CandidateHz.p90,ao.f0CandidateHz.confidenceP50,
      b.requestedLocalStartSec,b.requestedLocalEndSec,b.localStartSec,b.localEndSec,b.availableDurationSec,b.coverageRatio,b.frameCount,be.candidateFrameCount,be.candidateRatioAmongAvailableFrames,be.ambiguityFrameCount,be.ambiguityRatioAmongCandidates,be.strongAmbiguityRatioAmongCandidates,bo.rmsRelativeDb.p10,bo.rmsRelativeDb.p50,bo.rmsRelativeDb.p90,bo.f0CandidateHz.p10,bo.f0CandidateHz.p50,bo.f0CandidateHz.p90,bo.f0CandidateHz.confidenceP50
    ].map(val).join(','));
  }
  return rows.join('\n') + '\n';
}
async function buildD2DiagnosticPackage() {
  if (!cmp.a || !cmp.b || !cmp.a.an || !cmp.b.an) throw new Error('A/B両方の解析結果が必要です');
  const check = cmpIdentityCheck();
  if (check.blocked) throw new Error(check.message);
  const resolved = await getResolvedAlignmentForCurrentPair();
  const offsetSec = resolved.offsetSec;
  const windowSec = 10, hopSec = 5, referenceAnchorSec = 0;
  const durA = d2AnalysisDurationSec('a'), durB = d2AnalysisDurationSec('b');
  if (!(durA > 0) || !(durB > 0)) throw new Error('録音時間を取得できません');
  const overlapStartSec = Math.max(0, offsetSec);
  const overlapEndSec = Math.min(durA, durB + offsetSec);
  const overlapDurationSec = Math.max(0, overlapEndSec - overlapStartSec);
  const windows = [];
  let idx = 0;
  for (let start = referenceAnchorSec; start + windowSec <= durA + 1e-6; start += hopSec) {
    const end = start + windowSec;
    const pairStart = Math.max(start, 0, offsetSec);
    const pairEnd = Math.min(end, durA, durB + offsetSec);
    const pairAvailable = Math.max(0, pairEnd - pairStart);
    const pairCoverageRatio = +(pairAvailable / windowSec).toFixed(6);
    // D2 compares only the common aligned interval. Never aggregate A over a
    // longer interval than B in partial-coverage windows.
    const a = d2SideWindowStats('a', start, end, pairStart, pairEnd, offsetSec);
    const b = d2SideWindowStats('b', start, end, pairStart, pairEnd, offsetSec);
    windows.push({
      windowIndex: idx++,
      referenceStartSec: +start.toFixed(3),
      referenceEndSec: +end.toFixed(3),
      pairReferenceStartSec: pairAvailable > 0 ? +pairStart.toFixed(3) : null,
      pairReferenceEndSec: pairAvailable > 0 ? +pairEnd.toFixed(3) : null,
      pairAvailableDurationSec: +pairAvailable.toFixed(3),
      pairCoverageRatio,
      comparisonCoverageStatus: pairCoverageRatio >= 0.999 ? 'full' : (pairCoverageRatio > 0 ? 'partial' : 'none'),
      a, b
    });
  }
  const markersA = await dbByRec('markers', cmp.a.rec.recordingId).catch(() => []);
  const markersB = await dbByRec('markers', cmp.b.rec.recordingId).catch(() => []);
  const segmentsA = await dbByRec('segments', cmp.a.rec.recordingId).catch(() => []);
  const segmentsB = await dbByRec('segments', cmp.b.rec.recordingId).catch(() => []);
  const fullPair = windows.filter(w => w.pairCoverageRatio >= 0.999).length;
  const partialPair = windows.filter(w => w.pairCoverageRatio > 0 && w.pairCoverageRatio < 0.999).length;
  const zeroPair = windows.filter(w => w.pairCoverageRatio === 0).length;
  const candidateBoth = windows.filter(w => w.a.f0CandidateEvidence.candidateFrameCount > 0 && w.b.f0CandidateEvidence.candidateFrameCount > 0 && w.pairCoverageRatio > 0).length;
  return {
    schemaVersion: 'songscope-d2diag-0.1.2',
    packageType: 'pairwise_observation_comparison',
    status: 'diagnostic_only',
    generatedAt: nowIso(),
    appVersion: APP_VERSION,
    buildId: BUILD_ID,
    comparisonPrinciples: [
      'This package reports aligned observations and evidence quantity; it does not label improvement.',
      'Per-window A/B observations are aggregated only over the common aligned interval shared by both recordings.',
      'F0 candidate values are not corrected or deleted because of ambiguity flags; ambiguity is reported separately as evidence.',
      'rms_relative_db is normalized within each recording and must not be interpreted as absolute loudness difference.',
      'Missing or weak evidence remains missing/weak rather than being imputed.'
    ],
    alignment: {
      status: resolved.result.status,
      pairKey: resolved.result.pairKey,
      alignmentId: resolved.result.alignmentId || null,
      sourceDiagnosticId: resolved.result.sourceDiagnosticId || null,
      mappingConvention: 'reference_A_time_sec = target_B_time_sec + offset_sec',
      offsetSec,
      canonical: resolved.result.canonical,
      latestDecision: resolved.result.latestDecision || null,
      algorithm: resolved.result.algorithm || null
    },
    referenceAxis: {
      type: 'recording_A_time',
      recordingId: cmp.a.rec.recordingId,
      windowSec,
      hopSec,
      anchorSec: referenceAnchorSec,
      intervalConvention: '[start,end)'
    },
    windowingCoverage: {
      policy: 'full_nominal_windows_only',
      lastWindowEndSec: windows.length ? windows[windows.length - 1].referenceEndSec : 0,
      unwindowedReferenceTailSec: windows.length ? +Math.max(0, durA - windows[windows.length - 1].referenceEndSec).toFixed(3) : +durA.toFixed(3),
      note: 'A final tail shorter than the 10 s nominal window is not summarized in this diagnostic build.'
    },
    recordingA: d2RecordingDescriptor('a'),
    recordingB: d2RecordingDescriptor('b'),
    overlap: {
      referenceStartSec: +overlapStartSec.toFixed(3),
      referenceEndSec: +overlapEndSec.toFixed(3),
      durationSec: +overlapDurationSec.toFixed(3),
      referenceCoverageRatio: +(overlapDurationSec / durA).toFixed(6),
      targetCoverageRatio: +(overlapDurationSec / durB).toFixed(6)
    },
    evidenceSummary: {
      windowCount: windows.length,
      fullPairCoverageWindowCount: fullPair,
      partialPairCoverageWindowCount: partialPair,
      zeroPairCoverageWindowCount: zeroPair,
      windowsWithF0CandidateEvidenceBoth: candidateBoth
    },
    userReportedEvidence: {
      markersA: d2MapMarkers(markersA, 'a', offsetSec),
      markersB: d2MapMarkers(markersB, 'b', offsetSec),
      segmentsA: d2MapUserSegments(segmentsA, 'a', offsetSec),
      segmentsB: d2MapUserSegments(segmentsB, 'b', offsetSec)
    },
    windows
  };
}
async function exportD2DiagnosticPackage() {
  const btn = $('#btn-d2-export');
  if (btn) btn.disabled = true;
  try {
    const note = $('#cmp-d2-result');
    if (note) note.innerHTML = '<p class="small">resolved D1を読み込み、10秒窓 / 5秒hopで同一区間の観測証拠を集計しています…</p>';
    const pkg = await buildD2DiagnosticPackage();
    const files = [
      { name: 'comparison_summary.json', data: JSON.stringify(pkg, null, 2) },
      { name: 'comparison_windows.csv', data: d2WindowsCsv(pkg) }
    ];
    const blob = SongScopeZip.createZip(files);
    const stamp = new Date().toISOString().replace(/[-:]/g,'').slice(0,15);
    const name = `songscope_compare_${safeName(pkg.recordingA.title)}_vs_${safeName(pkg.recordingB.title)}_${stamp}.zip`;
    const how = await saveBlob(blob, name);
    if (note) note.innerHTML = `<p><b>D2 Diagnosticを書き出しました</b></p><p class="small mono">offset ${pkg.alignment.offsetSec >= 0 ? '+' : ''}${pkg.alignment.offsetSec.toFixed(1)} s / overlap ${pkg.overlap.durationSec.toFixed(1)} s / windows ${pkg.evidenceSummary.windowCount} / full pair ${pkg.evidenceSummary.fullPairCoverageWindowCount}</p><p class="small">まだ改善判定はしません。F0 ambiguityを含む候補値は訂正せず、証拠量と別に保持しています。</p>`;
    if (how !== 'cancelled') toast(`${name}を書き出しました`);
  } catch (e) {
    console.error(e);
    const note = $('#cmp-d2-result');
    if (note) note.innerHTML = `<p class="small">D2生成に失敗しました: ${escapeHtml((e && e.message) || String(e))}</p>`;
    toast('D2比較パッケージを作成できませんでした');
  } finally {
    if (btn) btn.disabled = false;
  }
}

function cmpDuration() {
  // Shared comparison axis is Recording A (reference) time. B-only regions outside A are not comparison time.
  const da = cmpSideDuration('a');
  if (da > 0) return Math.max(1, da);
  const db2 = cmpSideDuration('b');
  return Math.max(1, db2 > 0 ? db2 + Math.max(0, cmp.offset) : 1);
}

function drawCompare() {
  if (!$('#view-compare').classList.contains('is-active')) return;
  updateCmpOffsetSliderRange();
  updateCmpIdentityUi();
  const dur = cmpDuration();
  drawCmpChart($('#cv-cmp-loud'), 'loud', dur);
  drawCmpChart($('#cv-cmp-pitch'), 'pitch', dur);
  $('#cmp-ab-readout').textContent = `開始: ${cmp.loop.a === null ? '—' : fmtClock(cmp.loop.a)} / 終了: ${cmp.loop.b === null ? '—' : fmtClock(cmp.loop.b)}`;
  $('#cmp-loop').classList.toggle('is-on', cmp.loop.on);
  $('#cmp-loop').textContent = cmp.loop.on ? 'ループ停止' : 'ループ開始';
  $('#offset-val').textContent = (cmp.offset >= 0 ? '+' : '') + cmp.offset.toFixed(1) + ' s';
}

function drawCmpChart(cv, kind, dur) {
  const { ctx, W, H } = setupCanvas(cv);
  const C = palette(false);
  const o = { W, H, C, forExport: false, m: { l: 40, r: 8, t: 4, b: 16 }, fs: { title: 12, axis: 9, legend: 11 }, showAxis: true, dur };
  const box = beginChart(ctx, o);
  const sides = [
    { d: cmp.a, color: C.mark, off: 0 },
    { d: cmp.b, color: C.alert, off: cmp.offset }
  ];
  let any = false;
  for (const s of sides) {
    if (!s.d || !s.d.an) continue;
    any = true;
    const F = s.d.an.frames, n = F.timeSec.length;
    ctx.strokeStyle = s.color;
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    let started = false;
    for (let i = 0; i < n; i++) {
      const t = F.timeSec[i] + s.off;
      if (t < 0 || t > dur) continue;
      const x = box.x0 + (t / dur) * box.w;
      let y;
      if (kind === 'loud') {
        const v = cmp.normalized ? F.rmsRelDb[i] : F.rmsDb[i];
        const top = cmp.normalized ? 6 : 0, bottom = cmp.normalized ? -60 : -70;
        y = box.y0 + box.h * (1 - (clamp(v, bottom, top) - bottom) / (top - bottom));
      } else {
        const hz = F.f0Hz[i];
        if (!isFinite(hz)) { started = false; continue; }
        const lo = 60, hi = 1200;
        y = box.y0 + box.h * (1 - (Math.log2(clamp(hz, lo, hi)) - Math.log2(lo)) / (Math.log2(hi) - Math.log2(lo)));
        // ピッチは点で描く（線でつなぐと存在しない滑らかさを作ってしまう）
        ctx.fillStyle = s.color;
        ctx.globalAlpha = 0.8;
        ctx.fillRect(x - 1, y - 1, 2, 2);
        continue;
      }
      if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
    }
    if (kind === 'loud') ctx.stroke();
    ctx.globalAlpha = 1;
  }
  if (!any) noData(ctx, o, box);
  // ループ範囲
  if (cmp.loop.a !== null && cmp.loop.b !== null && cmp.loop.b > cmp.loop.a) {
    ctx.strokeStyle = C.sub; ctx.setLineDash([4, 3]);
    ctx.strokeRect(box.x0 + (cmp.loop.a / dur) * box.w, box.y0 + 0.5, Math.max(1, ((cmp.loop.b - cmp.loop.a) / dur) * box.w), box.h - 1);
    ctx.setLineDash([]);
  }
  // 現在位置
  const t = cmpTime();
  if (t > 0) {
    ctx.strokeStyle = '#FF3B30'; ctx.lineWidth = 1.5;
    const x = box.x0 + clamp(t / dur, 0, 1) * box.w;
    ctx.beginPath(); ctx.moveTo(x, box.y0); ctx.lineTo(x, box.y0 + box.h); ctx.stroke();
  }
}

function cmpTime() {
  if (cmp.playing === 'a' && cmp.a && cmp.a.audio) return cmpLocalToReference('a', cmp.a.audio.currentTime);
  if (cmp.playing === 'b' && cmp.b && cmp.b.audio) return cmpLocalToReference('b', cmp.b.audio.currentTime);
  return cmp.lastTime || 0;
}
function cmpPlay(side, atTime) {
  const check = cmpIdentityCheck();
  if (check.blocked) { toast(check.status === 'same_recording' ? '同じ録音は別歌唱比較できません' : '同一元音声は別歌唱比較できません'); return; }
  const d = cmp[side];
  if (!d || !d.audio) { toast((side === 'a' ? 'A' : 'B') + 'の音声がありません'); return; }
  const other = cmp[side === 'a' ? 'b' : 'a'];
  if (other && other.audio) { try { other.audio.pause(); } catch (e) { } }
  const t = atTime === undefined ? cmpTime() : atTime; // reference(A) time
  const local = cmpReferenceToLocal(side, t);
  const localDur = cmpSideDuration(side);
  if (!(localDur > 0) || local < 0 || local > localDur) {
    toast((side === 'a' ? 'A' : 'B') + 'にはこの基準時刻に対応する音声がありません');
    return;
  }
  try { d.audio.currentTime = clamp(local, 0, Math.max(0, localDur - 0.05)); } catch (e) { }
  d.audio.play().then(() => {
    cmp.playing = side;
    $('#cmp-which').textContent = side === 'a' ? 'A を再生中' : 'B を再生中';
    cmpTick();
  }).catch(() => toast('再生できませんでした'));
}
function cmpStop() {
  cmp.lastTime = cmpTime();
  for (const s of ['a', 'b']) if (cmp[s] && cmp[s].audio) { try { cmp[s].audio.pause(); } catch (e) { } }
  cmp.playing = null;
  $('#cmp-which').textContent = '停止中';
  cancelAnimationFrame(cmp.rafId);
  drawCompare();
}
function cmpTick() {
  cancelAnimationFrame(cmp.rafId);
  const loop = () => {
    if (!cmp.playing) return;
    const d = cmp[cmp.playing];
    if (!d || !d.audio) return;
    const t = cmpTime();
    cmp.lastTime = t;
    if (cmp.loop.on && cmp.loop.a !== null && cmp.loop.b !== null && cmp.loop.b > cmp.loop.a) {
      if (t >= cmp.loop.b || t < cmp.loop.a - 0.5) {
        const local = cmpReferenceToLocal(cmp.playing, cmp.loop.a);
        const localDur = cmpSideDuration(cmp.playing);
        if (!(localDur > 0) || local < 0 || local > localDur) {
          try { d.audio.pause(); } catch (e) { }
          cmp.playing = null;
          $('#cmp-which').textContent = '停止中';
          toast('ループ開始時刻が再生中の録音範囲外です');
          return;
        }
        try { d.audio.currentTime = Math.min(Math.max(0, local), Math.max(0, localDur - 0.05)); } catch (e) { }
      }
    }
    $('#cmp-time').textContent = fmtTime(t);
    const dur = cmpDuration();
    const seek = $('#cmp-seek');
    if (!seek.dataset.dragging) seek.value = String(Math.round(clamp(t / dur, 0, 1) * 1000));
    drawCompare();
    if (!d.audio.paused) cmp.rafId = requestAnimationFrame(loop);
    else { cmp.playing = null; $('#cmp-which').textContent = '停止中'; }
  };
  cmp.rafId = requestAnimationFrame(loop);
}

/* =====================================================================
 * イベント配線 / 初期化
 * ===================================================================== */
function wireHome() {
  $('#btn-add').addEventListener('click', () => $('#file-input').click());
  $('#file-input').addEventListener('change', e => {
    const f = e.target.files && e.target.files[0];
    e.target.value = '';
    if (!f) return;
    if (f.size > 400 * 1024 * 1024) { toast('ファイルが大きすぎます'); return; }
    openAddSheet(f);
  });
  $('#btn-settings').addEventListener('click', openSettingsSheet);
  $('#btn-backup-all').addEventListener('click', backupAll);
  $('#btn-compare-open').addEventListener('click', openCompare);
  $('#btn-persist').addEventListener('click', async () => {
    try {
      if (navigator.storage && navigator.storage.persist) {
        const ok = await navigator.storage.persist();
        toast(ok ? '永続化が有効になりました' : 'この端末では永続化を保証できません');
      } else toast('このブラウザは永続化に対応していません');
    } catch (e) { toast('永続化を要求できませんでした'); }
    refreshStorageEstimate();
  });
}

function wireSheets() {
  $('#sheet-bg').addEventListener('click', () => {
    if (!$('#sheet-busy').hidden) return; // 処理中は閉じない
    state.markerDraft = null; state.segmentDraft = null;
    closeSheet();
  });
  $$('[data-close]').forEach(b => b.addEventListener('click', () => {
    state.markerDraft = null; state.segmentDraft = null;
    closeSheet();
  }));
  $('#rec-save').addEventListener('click', onRecSave);
  $('#tag-save').addEventListener('click', saveMarkerDraft);
  $('#settings-save').addEventListener('click', () => {
    const g = (id, def) => {
      const v = parseFloat($(id).value);
      return isFinite(v) ? v : def;
    };
    settings.frameSizeMs = clamp(g('#s-frame', 40), 10, 100);
    settings.hopSizeMs = clamp(g('#s-hop', 20), 5, settings.frameSizeMs);
    settings.analysisSampleRate = clamp(g('#s-sr', 22050), 8000, 48000);
    settings.f0MinHz = clamp(g('#s-f0min', 65), 40, 200);
    settings.f0MaxHz = clamp(g('#s-f0max', 1200), 400, 2000);
    settings.minimumConfidence = clamp(g('#s-conf', 0.55), 0, 0.95);
    settings.recordingSetupPreset = $('#s-setup').value.trim() || DEFAULT_SETTINGS.recordingSetupPreset;
    saveSettings();
    closeSheet();
    toast('設定を保存しました（次回の解析から反映）');
  });
  $('#settings-reset').addEventListener('click', () => {
    settings = Object.assign({}, DEFAULT_SETTINGS);
    saveSettings();
    openSettingsSheet();
    toast('初期値に戻しました');
  });
}
function openSettingsSheet() {
  $('#s-frame').value = settings.frameSizeMs;
  $('#s-hop').value = settings.hopSizeMs;
  $('#s-sr').value = settings.analysisSampleRate;
  $('#s-f0min').value = settings.f0MinHz;
  $('#s-f0max').value = settings.f0MaxHz;
  $('#s-conf').value = settings.minimumConfidence;
  $('#s-setup').value = settings.recordingSetupPreset;
  openSheet('sheet-settings');
}

function wireReview() {
  $('#btn-back-home').addEventListener('click', async () => {
    stopPlayback();
    showView('view-home');
    await loadRecordings();
    refreshStorageEstimate();
  });
  $('#btn-rec-edit').addEventListener('click', () => state.rec && openEditSheet(state.rec));
  $('#btn-reanalyze').addEventListener('click', () => state.rec && startAnalysis(state.rec));

  $('#btn-play').addEventListener('click', togglePlay);
  $('#btn-b10').addEventListener('click', () => nudge(-10));
  $('#btn-b5').addEventListener('click', () => nudge(-5));
  $('#btn-f5').addEventListener('click', () => nudge(5));
  $('#btn-f10').addEventListener('click', () => nudge(10));
  $$('#speed-row .spd').forEach(b => b.addEventListener('click', () => {
    $$('#speed-row .spd').forEach(x => x.classList.remove('is-on'));
    b.classList.add('is-on');
    if (state.audio) state.audio.playbackRate = parseFloat(b.dataset.spd);
  }));

  const seek = $('#seek');
  const applySeek = () => seekTo(parseInt(seek.value, 10) / 1000 * duration());
  seek.addEventListener('input', () => { seek.dataset.dragging = '1'; applySeek(); });
  seek.addEventListener('change', () => { applySeek(); delete seek.dataset.dragging; });

  $('#btn-marker').addEventListener('click', () => {
    if (!state.rec) return;
    haptic();
    openMarkerSheet(state.audio ? state.audio.currentTime : 0);
  });

  $('#btn-set-a').addEventListener('click', () => { state.loop.a = +(state.audio ? state.audio.currentTime : 0).toFixed(1); updateAbReadout(); drawAllGraphs(); haptic(); });
  $('#btn-set-b').addEventListener('click', () => { state.loop.b = +(state.audio ? state.audio.currentTime : 0).toFixed(1); updateAbReadout(); drawAllGraphs(); haptic(); });
  $('#btn-loop-toggle').addEventListener('click', () => {
    if (state.loop.a === null || state.loop.b === null || state.loop.b <= state.loop.a) { toast('A地点とB地点を指定してください'); return; }
    state.loop.on = !state.loop.on;
    updateAbReadout();
    if (state.loop.on) {
      seekTo(state.loop.a);
      if (state.audio && state.audio.paused) togglePlay(); else tick();
    }
  });
  $('#btn-ab-clear').addEventListener('click', () => { state.loop = { a: null, b: null, on: false }; updateAbReadout(); drawAllGraphs(); });
  $('#btn-ab-save').addEventListener('click', saveAbAsSegment);
  $$('[data-nudge]').forEach(b => b.addEventListener('click', () => {
    const [which, delta] = b.dataset.nudge.split(',');
    if (state.loop[which] === null) { toast(which.toUpperCase() + '地点が未設定です'); return; }
    state.loop[which] = +Math.max(0, state.loop[which] + parseFloat(delta)).toFixed(1);
    updateAbReadout(); drawAllGraphs();
  }));

  $('#conf-slider').addEventListener('input', e => {
    state.confMin = parseFloat(e.target.value);
    $('#conf-val').textContent = state.confMin.toFixed(2);
    drawAllGraphs();
  });
  $('#btn-pitch-unit').addEventListener('click', () => {
    state.pitchUnit = state.pitchUnit === 'hz' ? 'midi' : 'hz';
    $('#btn-pitch-unit').textContent = state.pitchUnit === 'hz' ? 'MIDI表示' : 'Hz表示';
    $('#pitch-unit-label').textContent = state.pitchUnit === 'hz' ? 'Hz' : 'MIDI note';
    drawAllGraphs();
  });
  $('#btn-spec-range').addEventListener('click', () => {
    state.specTopHz = state.specTopHz === 8000 ? 4000 : 8000;
    $('#btn-spec-range').textContent = state.specTopHz === 8000 ? '0–4kHz' : '0–8kHz';
    $('#spec-range-label').textContent = `0–${state.specTopHz / 1000} kHz`;
    specCache = { key: '', canvas: null };
    drawAllGraphs();
  });

  ['#cv-wave', '#cv-loud', '#cv-pitch', '#cv-spec'].forEach(sel => {
    const cv = $(sel);
    cv.addEventListener('click', ev => {
      const r = cv.getBoundingClientRect();
      const left = 38, right = 6;
      const x = ev.clientX - r.left - left;
      const w = r.width - left - right;
      if (w <= 0) return;
      seekTo(clamp(x / w, 0, 1) * duration());
    });
  });

  $('#chk-include-audio').checked = getFlag('includeAudio', false);
  $('#chk-include-audio').addEventListener('change', e => setFlag('includeAudio', e.target.checked));
  $('#btn-export').addEventListener('click', doExport);

  $('#btn-delete-rec').addEventListener('click', async () => {
    if (!state.rec) return;
    if (!confirm(`「${state.rec.title}」を削除します。取り消せません。よろしいですか？`)) return;
    const id = state.rec.recordingId;
    stopPlayback();
    try {
      await dbDelByRec('markers', id);
      await dbDelByRec('segments', id);
      await dbDelByRec('analysisHistory', id);
      await dbDel('analysis', id);
      await dbDel('audio', id);
      await dbDel('recordings', id);
    } catch (e) { toast('削除に失敗しました'); return; }
    state.rec = null; state.analysis = null;
    showView('view-home');
    await loadRecordings();
    refreshStorageEstimate();
    toast('削除しました');
  });
}

function nudge(d) {
  if (!state.audio) return;
  seekTo(state.audio.currentTime + d);
}

function wireCompare() {
  $('#btn-back-home2').addEventListener('click', () => { cmpStop(); showView('view-home'); loadRecordings(); });
  $('#sel-a').addEventListener('change', async e => { cmpStop(); cmpResetMapping(); await loadCmpSide('a', e.target.value); });
  $('#sel-b').addEventListener('change', async e => { cmpStop(); cmpResetMapping(); await loadCmpSide('b', e.target.value); });
  $('#btn-norm').addEventListener('click', () => {
    cmp.normalized = true;
    $('#btn-norm').classList.add('is-on'); $('#btn-raw').classList.remove('is-on');
    drawCompare();
  });
  $('#btn-raw').addEventListener('click', () => {
    cmp.normalized = false;
    $('#btn-raw').classList.add('is-on'); $('#btn-norm').classList.remove('is-on');
    drawCompare();
  });
  $('#offset-slider').addEventListener('input', e => { cmp.offset = parseFloat(e.target.value); const n=$('#offset-number'); if(n)n.value=cmp.offset.toFixed(1); drawCompare(); });
  $('#offset-number').addEventListener('change', e => { const sl=$('#offset-slider'); const v=clamp(parseFloat(e.target.value)||0,parseFloat(sl.min),parseFloat(sl.max)); cmp.offset=Math.round(v*10)/10; sl.value=String(cmp.offset); e.target.value=cmp.offset.toFixed(1); drawCompare(); });
  $('#btn-song-merge-b-to-a').addEventListener('click', mergeCmpSongGroupBIntoA);
  $('#btn-align-diagnose').addEventListener('click', diagnoseAlignment);
  $('#btn-align-export').addEventListener('click', exportAlignmentDiagnostic);
  $('#btn-align-apply').addEventListener('click', applyResolvedAlignment);
  $('#btn-d2-export').addEventListener('click', exportD2DiagnosticPackage);
  $('#cmp-play-a').addEventListener('click', () => cmpPlay('a'));
  $('#cmp-play-b').addEventListener('click', () => cmpPlay('b'));
  $('#cmp-stop').addEventListener('click', cmpStop);
  $('#cmp-swap').addEventListener('click', () => {
    const t = cmpTime();
    const to = cmp.playing === 'a' ? 'b' : 'a';
    cmpPlay(to, t);
  });
  $('#cmp-set-a').addEventListener('click', () => { cmp.loop.a = +cmpTime().toFixed(1); drawCompare(); });
  $('#cmp-set-b').addEventListener('click', () => { cmp.loop.b = +cmpTime().toFixed(1); drawCompare(); });
  $('#cmp-ab-clear').addEventListener('click', () => { cmp.loop = { a: null, b: null, on: false }; drawCompare(); });
  $('#cmp-loop').addEventListener('click', () => {
    if (cmp.loop.a === null || cmp.loop.b === null || cmp.loop.b <= cmp.loop.a) { toast('A地点とB地点を指定してください'); return; }
    cmp.loop.on = !cmp.loop.on;
    drawCompare();
    if (cmp.loop.on) cmpPlay(cmp.playing || 'a', cmp.loop.a);
  });
  const cs = $('#cmp-seek');
  const applyCmpSeek = () => {
    const t = parseInt(cs.value, 10) / 1000 * cmpDuration();
    cmp.lastTime = t;
    if (cmp.playing) cmpPlay(cmp.playing, t); else drawCompare();
  };
  cs.addEventListener('input', () => { cs.dataset.dragging = '1'; cmp.lastTime = parseInt(cs.value, 10) / 1000 * cmpDuration(); drawCompare(); });
  cs.addEventListener('change', () => { applyCmpSeek(); delete cs.dataset.dragging; });
}

let resizeTimer = null;
function wireGlobal() {
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => { drawAllGraphs(); drawCompare(); }, 150);
  });
  window.addEventListener('orientationchange', () => {
    setTimeout(() => { drawAllGraphs(); drawCompare(); }, 350);
  });
  matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change', () => { specCache = { key: '', canvas: null }; drawAllGraphs(); });
  window.addEventListener('beforeunload', () => { if (state.audioUrl) URL.revokeObjectURL(state.audioUrl); });
  document.addEventListener('gesturestart', e => e.preventDefault()); // 誤ピンチズーム防止
}

async function init() {
  loadSettings();
  state.confMin = settings.minimumConfidence;
  wireHome(); wireSheets(); wireReview(); wireCompare(); wireGlobal();
  $$('.app-ver').forEach(e => e.textContent = APP_VERSION + ' / ' + BUILD_ID);
  await migrateBliteIdentityData().catch(e => console.warn('B-lite migration skipped:', e));
  await loadRecordings();
  refreshStorageEstimate();
  if ('serviceWorker' in navigator && location.protocol === 'https:') {
    navigator.serviceWorker.register('service-worker.js?v=' + encodeURIComponent(BUILD_ID)).catch(() => { });
  }
}
document.addEventListener('DOMContentLoaded', init);
