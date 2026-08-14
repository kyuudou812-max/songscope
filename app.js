/* =====================================================================
 * SongScope v0.2 Audit Remediation R2  —  歌唱録音レビュー・解析アプリ
 *
 * 思想:
 *   観測された事実 と 解釈・評価 を分離する。
 *   このアプリは測定器であり、歌の先生ではない。
 *   推定できないものは null にする。それらしい数値を作らない。
 * ===================================================================== */
'use strict';

const APP_VERSION = '0.2.0-g0';
const SCHEMA_VERSION = '0.18.6';
const BUILD_ID = '20260814-g0-29';
const EXTERNAL_EVALUATION_SCHEMA = 'songscope-external-evaluation-v1';
const EXTERNAL_EVALUATION_SCHEMA_V2 = 'songscope-external-evaluation-v2';
const EVIDENCE_SET_SCHEMA = 'songscope-evaluation-evidence-set-v1';
const STANDALONE_SCORING_RESULT_SCHEMA_LEGACY = 'songscope-external-scoring-result-v1';
const STANDALONE_SCORING_RESULT_SCHEMA = 'songscope-external-scoring-result-v2';
const STANDALONE_SCORING_FIELD_KEYS = [
  'title','artist','scoringMode','scoringPerformedAt','overallScore','personalBest','nationalAverage','ranking','heartType',
  'pitchAccuracy','expressionScore','dynamicsScore','listeningScore','bonus','techniques','vibrato',
  'longToneSkillDiscrete','vibratoSkillDiscrete','stabilityDiscrete','rhythmDiscrete',
  'vocalRange','pitchGraphVisibleMarkers','analysisReportText'
];
const STANDALONE_SCORING_FIELD_STATUSES = new Set([
  'extracted','not_visible_in_images','unreadable','visible_not_extracted','not_applicable'
]);
const COMPARISON_CONTEXT_SCHEMA = 'songscope-comparison-context-v2';
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
  recordingSetupPreset: 'カラオケ標準（iPhoneをテーブル・画面上向き・本人から約50cm）',
  // R1: 次回入力を1タップで確認できるよう、直近の採点4条件を端末内だけに保持する。
  lastScoringConditions: { device: '', scoringMode: '', keyChange: '', octave: '' }
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
const DB_VER = 8;
let dbp = null;

const DB_BLOCKED_CODE = 'SONGSCOPE_DB_UPGRADE_BLOCKED';
const DB_VERSION_ERROR_CODE = 'SONGSCOPE_DB_VERSION_NEWER';
function makeDbVersionError(original) {
  const e = new Error('この端末には、この画面より新しいSongScopeのデータベースがあります。');
  e.code = DB_VERSION_ERROR_CODE;
  e.originalError = original || null;
  return e;
}
function isDbVersionError(e) { return !!(e && e.code === DB_VERSION_ERROR_CODE); }
function dbVersionUserMessage() {
  return '古いSongScope画面が開かれています。サイトデータを削除せず、SongScopeの全画面を閉じてから最新版を開き直してください。';
}
function makeDbBlockedError() {
  const e = new Error('SongScopeのデータベース更新が、別のSongScope画面によって待機中です。');
  e.code = DB_BLOCKED_CODE;
  return e;
}
function isDbBlockedError(e) { return !!(e && e.code === DB_BLOCKED_CODE); }
function dbBlockedUserMessage() {
  return 'SongScopeの別画面が開いたままの可能性があります。SafariのSongScopeタブとホーム画面版SongScopeをすべて閉じてから、もう一度開いてください。録音データは削除しないでください。';
}

function ensureSongScopeStores(d, tx) {
  let recordings;
  if (!d.objectStoreNames.contains('recordings')) {
    recordings = d.createObjectStore('recordings', { keyPath: 'recordingId' });
  } else recordings = tx.objectStore('recordings');
  if (!recordings.indexNames.contains('byAudioSha256')) recordings.createIndex('byAudioSha256', 'audioSha256', { unique: false });
  if (!recordings.indexNames.contains('bySongId')) recordings.createIndex('bySongId', 'songId', { unique: false });
  if (!recordings.indexNames.contains('bySongIdentityKey')) recordings.createIndex('bySongIdentityKey', 'songIdentityKey', { unique: false });

  if (!d.objectStoreNames.contains('audio')) d.createObjectStore('audio', { keyPath: 'recordingId' });
  if (!d.objectStoreNames.contains('analysis')) d.createObjectStore('analysis', { keyPath: 'recordingId' });
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
  // R1: 人間が確認した時間順・採点条件はalignment algorithmのversionから独立して保存する。
  if (!d.objectStoreNames.contains('pairContexts')) {
    const pc = d.createObjectStore('pairContexts', { keyPath: 'audioPairKey' });
    pc.createIndex('byUpdatedAt', 'updatedAt', { unique: false });
  }
  // G0b03: DAMデンモク採点履歴は録音から独立した一次証拠として先に保存できる。
  if (!d.objectStoreNames.contains('scoringEvidenceSets')) {
    const se = d.createObjectStore('scoringEvidenceSets', { keyPath: 'evidenceSetId' });
    se.createIndex('byCreatedAt', 'createdAt', { unique: false });
    // Legacy non-authoritative field only. build13 derives binding from bindingAssertions.
    se.createIndex('byBindingStatus', 'bindingStatus', { unique: false });
  }
  // G0 build13: same-performance relationship is an append-only user assertion.
  if (!d.objectStoreNames.contains('bindingAssertions')) {
    const ba=d.createObjectStore('bindingAssertions',{keyPath:'assertionId'});
    ba.createIndex('byEvidenceSetId','evidenceSetId',{unique:false});
    ba.createIndex('byRecordingId','recordingId',{unique:false});
    ba.createIndex('byAudioSha256','audioSha256',{unique:false});
    ba.createIndex('byAssertedAt','assertedAt',{unique:false});
  }
}
function db() {
  if (dbp) return dbp;
  dbp = new Promise((res, rej) => {
    const req = indexedDB.open(DB_NAME, DB_VER);
    let settled = false;
    let blockedTimer = null;
    req.onupgradeneeded = () => {
      ensureSongScopeStores(req.result, req.transaction);
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
      const err = req.error;
      rej(err && err.name === 'VersionError' ? makeDbVersionError(err) : err);
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
let songScopeSheetPageScrollY=0;
let songScopeSheetKeyboardActive=false;
let songScopeSheetViewportTimer=null;
let songScopeSheetOpenViewportHeight=0;
let songScopeSheetFocusedControl=null;
let songScopeKeyboardSettleToken=0;

let songScopeKeyboardGeometry={
  phase:'closed', // closed | opening | stable | closing
  samples:[],
  stableVisualHeight:null,
  lastSampleAt:0
};

function songScopeVisibleViewportHeight() {
  const vv=window.visualViewport;
  const h=vv&&Number(vv.height);
  return Math.max(1,Math.floor(Number.isFinite(h)&&h>0?h:(window.innerHeight||1)));
}
function applySongScopeSheetViewportHeight(heightOverride) {
  const h=Math.max(1,Math.floor(Number(heightOverride)||songScopeVisibleViewportHeight()));
  document.documentElement.style.setProperty('--songscope-sheet-vh',`${h}px`);
}
function resetSongScopeKeyboardVisualState() {
  document.documentElement.style.setProperty('--songscope-keyboard-inset','0px');
  document.documentElement.style.setProperty('--songscope-keyboard-shift-y','0px');
  document.documentElement.style.setProperty('--songscope-keyboard-reserve','0px');
  songScopeKeyboardGeometry.phase='closed';
  songScopeKeyboardGeometry.samples.length=0;
  songScopeKeyboardGeometry.stableVisualHeight=null;
  songScopeKeyboardGeometry.lastSampleAt=0;
}
function freezeSongScopeSheetViewportHeight() {
  songScopeSheetOpenViewportHeight=songScopeVisibleViewportHeight();
  applySongScopeSheetViewportHeight(songScopeSheetOpenViewportHeight);
  resetSongScopeKeyboardVisualState();
}
function songScopeCurrentVisualViewportRect() {
  const vv=window.visualViewport;
  if (!vv) {
    const height=Math.max(1,window.innerHeight||songScopeSheetOpenViewportHeight||1);
    return {top:0,bottom:height,height};
  }
  const top=Math.max(0,Number(vv.offsetTop)||0);
  const height=Math.max(1,Number(vv.height)||window.innerHeight||1);
  return {top,bottom:top+height,height};
}
function beginSongScopeKeyboardOpening() {
  songScopeKeyboardGeometry.phase='opening';
  songScopeKeyboardGeometry.samples.length=0;
  songScopeKeyboardGeometry.stableVisualHeight=null;
  songScopeKeyboardGeometry.lastSampleAt=0;
}
function addSongScopeKeyboardSample(vvRect) {
  const h=Math.max(1,Math.round(Number(vvRect&&vvRect.height)||1));
  const top=Math.max(0,Math.round(Number(vvRect&&vvRect.top)||0));
  const now=(typeof performance!=='undefined'&&performance.now)?performance.now():Date.now();
  const sample={height:h,top,at:now};
  songScopeKeyboardGeometry.samples.push(sample);
  if (songScopeKeyboardGeometry.samples.length>12) songScopeKeyboardGeometry.samples.shift();
  songScopeKeyboardGeometry.lastSampleAt=now;
  return sample;
}
function deriveSongScopeStableKeyboardHeight() {
  const s=songScopeKeyboardGeometry.samples;
  if (s.length<3) return null;

  const recent=s.slice(-4).map(x=>x.height);
  const min=Math.min(...recent);
  const max=Math.max(...recent);
  if (max-min>12) return null;

  const sorted=recent.slice().sort((a,b)=>a-b);
  const mid=Math.floor(sorted.length/2);
  const median=sorted.length%2 ? sorted[mid] : Math.round((sorted[mid-1]+sorted[mid])/2);

  const base=Math.max(1,songScopeSheetOpenViewportHeight||songScopeVisibleViewportHeight());
  if (median>=base-80) return null;
  return Math.max(1,Math.min(base,median));
}
function updateSongScopeKeyboardVisualState() {
  const vv=songScopeCurrentVisualViewportRect();
  const base=Math.max(1,songScopeSheetOpenViewportHeight||songScopeVisibleViewportHeight());

  if (songScopeSheetKeyboardActive && songScopeKeyboardGeometry.phase==='closed') {
    beginSongScopeKeyboardOpening();
  }
  if (songScopeSheetKeyboardActive) addSongScopeKeyboardSample(vv);

  const inset=Math.max(0,Math.round(base-vv.height));
  const maxShift=Math.max(0,base-vv.height);
  const shift=Math.max(0,Math.min(Math.round(vv.top),Math.round(maxShift)));

  const derived=deriveSongScopeStableKeyboardHeight();
  if (derived!=null) {
    songScopeKeyboardGeometry.phase='stable';
    songScopeKeyboardGeometry.stableVisualHeight=derived;
  }

  const stableHeight=songScopeKeyboardGeometry.stableVisualHeight;
  const reachReserve=(songScopeSheetKeyboardActive && stableHeight!=null)
    ? Math.max(0,Math.round(base-stableHeight))
    : 0;

  document.documentElement.style.setProperty('--songscope-keyboard-inset',`${inset}px`);
  document.documentElement.style.setProperty('--songscope-keyboard-shift-y',`${shift}px`);
  document.documentElement.style.setProperty('--songscope-keyboard-reserve',`${reachReserve}px`);

  return {
    phase:songScopeKeyboardGeometry.phase,
    inset,shift,
    visualHeight:vv.height,
    stableVisualHeight:stableHeight,
    reachReserve
  };
}
function songScopeKeyboardUsableHeight(vvRect) {
  const base=Math.max(1,songScopeSheetOpenViewportHeight||songScopeVisibleViewportHeight());
  const stable=songScopeKeyboardGeometry.stableVisualHeight;
  if (songScopeSheetKeyboardActive && stable!=null) return stable;
  return Math.max(1,Math.min(base,Number(vvRect&&vvRect.height)||base));
}
function ensureSongScopeFocusedControlVisible(target) {
  const sheet=activeSongScopeSheet();
  if (!sheet||!target||!sheet.contains(target)) {
    return {adjusted:false,scrollTop:Number(sheet&&sheet.scrollTop)||0};
  }

  const vv=songScopeCurrentVisualViewportRect();
  const usableHeight=songScopeKeyboardUsableHeight(vv);
  const sheetRect=sheet.getBoundingClientRect();
  const targetRect=target.getBoundingClientRect();
  const head=sheet.querySelector('.sheet-head');
  const headRect=head?head.getBoundingClientRect():null;
  const margin=16;

  const headerBottomRel=headRect?Math.max(0,headRect.bottom-sheetRect.top):0;
  const targetTopRel=targetRect.top-sheetRect.top;
  const targetBottomRel=targetRect.bottom-sheetRect.top;
  const visibleTop=headerBottomRel+margin;
  const visibleBottom=Math.min(
    Math.max(1,Number(sheet.clientHeight)||sheetRect.height||usableHeight),
    usableHeight
  )-margin;

  // If Safari or the user's existing scroll already leaves the field visible,
  // do nothing. Do not snap every focus to a predetermined resting position.
  let delta=0;
  if (targetBottomRel>visibleBottom) delta=targetBottomRel-visibleBottom;
  else if (targetTopRel<visibleTop) delta=targetTopRel-visibleTop;

  const before=Math.max(0,Number(sheet.scrollTop)||0);
  if (Math.abs(delta)<=0.5) return {adjusted:false,scrollTop:before};

  const maxScroll=Math.max(0,(Number(sheet.scrollHeight)||0)-(Number(sheet.clientHeight)||0));
  const next=Math.max(0,Math.min(maxScroll,before+delta));
  sheet.scrollTop=next;
  return {adjusted:Math.abs(next-before)>0.5,scrollTop:next};
}
function scheduleSongScopeFocusedControlVisibility(target) {
  const control=target||songScopeSheetFocusedControl||document.activeElement;
  const token=++songScopeKeyboardSettleToken;
  let lastSig='';
  let stableCount=0;
  let attempts=0;

  const sample=()=>{
    if (token!==songScopeKeyboardSettleToken) return;
    if (!songScopeSheetIsOpen()||!songScopeSheetKeyboardActive) return;
    attempts++;

    const vv=songScopeCurrentVisualViewportRect();
    updateSongScopeKeyboardVisualState();
    ensureSongScopeFocusedControlVisible(control||songScopeSheetFocusedControl||document.activeElement);

    const reserve=document.documentElement.style.getPropertyValue('--songscope-keyboard-reserve')||'0px';
    const sig=`${Math.round(vv.top)}:${Math.round(vv.height)}:${songScopeKeyboardGeometry.phase}:${songScopeKeyboardGeometry.stableVisualHeight||0}:${reserve}`;
    if (sig===lastSig) stableCount++;
    else { lastSig=sig; stableCount=0; }

    // Safari keyboard/focus animation can settle in stages. Require repeated identical
    // geometry or keep sampling for up to ~720 ms.
    const keyboardStable=!songScopeSheetKeyboardActive || songScopeKeyboardGeometry.phase==='stable';
    if ((stableCount>=2 && keyboardStable) || attempts>=12) return;
    songScopeSheetViewportTimer=setTimeout(sample,80);
  };

  if (songScopeSheetViewportTimer) clearTimeout(songScopeSheetViewportTimer);
  if (typeof requestAnimationFrame==='function') requestAnimationFrame(sample);
  else sample();
}
function songScopeSheetIsOpen() {
  const wrap=$('#sheet-wrap');
  return !!(wrap&&!wrap.hidden);
}
function activeSongScopeSheet() {
  return Array.from(document.querySelectorAll('.sheet')).find(s=>!s.hidden)||null;
}
function elementIsInsideActiveSheet(el) {
  const sheet=activeSongScopeSheet();
  return !!(sheet&&el&&sheet.contains(el));
}

function lockPageForSheet() {
  if (document.documentElement.classList.contains('songscope-sheet-open')) return;
  songScopeSheetPageScrollY=window.scrollY||window.pageYOffset||0;
  document.documentElement.classList.add('songscope-sheet-open');
  document.body.classList.add('songscope-sheet-open');
  document.body.style.top=`-${songScopeSheetPageScrollY}px`;
}
function unlockPageForSheet() {
  if (!document.documentElement.classList.contains('songscope-sheet-open')) return;
  document.documentElement.classList.remove('songscope-sheet-open');
  document.body.classList.remove('songscope-sheet-open');
  document.body.style.top='';
  const y=songScopeSheetPageScrollY;
  songScopeSheetPageScrollY=0;
  window.scrollTo(0,y);
}

function openSheet(id) {
  // Freeze the currently visible viewport height at open. Normal Safari toolbar
  // expansion/collapse while scrolling must not reposition or resize the sheet.
  freezeSongScopeSheetViewportHeight();
  songScopeSheetKeyboardActive=false;
  songScopeSheetFocusedControl=null;
  lockPageForSheet();
  $('#sheet-wrap').hidden=false;
  $$('.sheet').forEach(s=>{
    s.hidden=s.id!==id;
    if (!s.hidden) {
      s.scrollTop=0;
      s.setAttribute('tabindex','-1');
    }
  });
}
function closeSheet() {
  $('#sheet-wrap').hidden=true;
  $$('.sheet').forEach(s=>{s.hidden=true;});
  songScopeSheetKeyboardActive=false;
  songScopeSheetFocusedControl=null;
  songScopeKeyboardSettleToken++;
  songScopeSheetOpenViewportHeight=0;
  resetSongScopeKeyboardVisualState();
  if (songScopeSheetViewportTimer) {
    clearTimeout(songScopeSheetViewportTimer);
    songScopeSheetViewportTimer=null;
  }
  unlockPageForSheet();
  if (typeof clearStandaloneReviewImageUrls === 'function') clearStandaloneReviewImageUrls();
}

function handleSongScopeSheetFocusIn(e) {
  if (!songScopeSheetIsOpen()||!elementIsInsideActiveSheet(e.target)) return;
  const tag=String(e.target&&e.target.tagName||'').toLowerCase();
  const editable=tag==='input'||tag==='textarea'||tag==='select'||(e.target&&e.target.isContentEditable);
  if (!editable) return;
  const wasKeyboardActive=songScopeSheetKeyboardActive;
  songScopeSheetKeyboardActive=true;
  songScopeSheetFocusedControl=e.target;
  if (!wasKeyboardActive) beginSongScopeKeyboardOpening();
  // Keep sheet geometry frozen. Commit whole-form reach reserve only after
  // visualViewport keyboard geometry reaches a stable state.
  updateSongScopeKeyboardVisualState();
  scheduleSongScopeFocusedControlVisibility(e.target);
}
function handleSongScopeSheetFocusOut() {
  if (!songScopeSheetIsOpen()) return;
  if (songScopeSheetViewportTimer) clearTimeout(songScopeSheetViewportTimer);
  songScopeSheetViewportTimer=setTimeout(()=>{
    songScopeSheetViewportTimer=null;
    if (elementIsInsideActiveSheet(document.activeElement)) {
      songScopeSheetFocusedControl=document.activeElement;
      return;
    }
    songScopeSheetKeyboardActive=false;
    songScopeSheetFocusedControl=null;
    songScopeKeyboardSettleToken++;
    resetSongScopeKeyboardVisualState();
    // Sheet geometry remains the original frozen open height.
  },450);
}
function handleSongScopeVisualViewportResize() {
  if (!songScopeSheetIsOpen()||!songScopeSheetKeyboardActive) return;
  updateSongScopeKeyboardVisualState();
  scheduleSongScopeFocusedControlVisibility(songScopeSheetFocusedControl||document.activeElement);
}
function handleSongScopeVisualViewportScroll() {
  if (!songScopeSheetIsOpen()||!songScopeSheetKeyboardActive) return;
  // Safari may pan the visual viewport after focus/keyboard animation without another resize.
  // Compensate only while a sheet control is actively focused.
  updateSongScopeKeyboardVisualState();
  scheduleSongScopeFocusedControlVisibility(songScopeSheetFocusedControl||document.activeElement);
}
function handleSongScopeOrientationChange() {
  if (!songScopeSheetIsOpen()) return;
  setTimeout(()=>{
    // Never capture keyboard-shortened height as the modal's new base height.
    if (songScopeSheetKeyboardActive) return;
    freezeSongScopeSheetViewportHeight();
  },450);
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
  recFormContext: null, // metadata provenance判定用
  evaluationImageMeta: null, // legacy read-only: pre-G0 recording-attached scoring image meta
  evaluationEvidenceImages: [], // legacy read-only: pre-G0 recording-attached scoring image set
  evaluationStructured: null, // legacy read-only: pre-G0 recording-attached structured JSON
  legacyScoringEvidenceMigration: null, // build10 migration audit marker from audio store
  scoringEvidenceCandidates: [], // legacy candidate-only subset retained for UI/audit
  scoringEvidenceContext: null, // build13: derived bound/conflict/legacy relationships from bindingAssertions
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
  catch (e) {
    if (isDbVersionError(e)) toast(dbVersionUserMessage(), 6500);
    else if (isDbBlockedError(e)) toast(dbBlockedUserMessage(), 6500);
    else toast('保存データを読み込めませんでした');
  }
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
  renderNormalWorkflowStatus().catch(e=>console.warn('normal workflow status render failed',e));
}


async function buildNormalWorkflowStatus() {
  const recordings=Array.isArray(state.recordings)?state.recordings:[];
  const all=(await dbAll('scoringEvidenceSets').catch(()=>[])).filter(set=>standaloneLifecycleStatus(set)!=='archived');
  const formal=all.filter(set=>standaloneSourceSupportedForG0(set));
  const bindingStates=await loadBindingStateMap(all);
  const rows=formal.map(set=>({
    set,
    sd:standaloneStructuredDescriptor(set),
    bs:bindingStates.get(set.evidenceSetId)||deriveBindingStateFromAssertions(set.evidenceSetId,[])
  }));

  const conflicts=rows.filter(x=>x.bs.status==='binding_conflict');
  const needsStructure=rows.filter(x=>x.sd.status!=='available');
  const needsReextract=rows.filter(x=>x.sd.status==='available' && (!x.sd.schemaCurrent || !x.sd.verification || x.sd.verification.status!=='source_verified'));
  const needsReview=rows.filter(x=>{
    const review=x.sd.userReview&&x.sd.userReview.status||'unreviewed';
    return x.sd.status==='available' && x.sd.schemaCurrent && x.sd.verification&&x.sd.verification.status==='source_verified' && review==='unreviewed';
  });
  const needsBinding=rows.filter(x=>{
    const review=x.sd.userReview&&x.sd.userReview.status||'unreviewed';
    const reviewed=review==='user_confirmed'||review==='user_confirmed_with_known_gaps';
    return x.bs.status==='unbound' && x.sd.status==='available' && x.sd.schemaCurrent && x.sd.verification&&x.sd.verification.status==='source_verified' && reviewed;
  });
  const bound=rows.filter(x=>x.bs.status==='bound');

  let next={kind:'ready',title:'次の歌唱を追加できます',detail:`録音 ${recordings.length}件 ／ 採点と結び付き済み ${bound.length}件`,tone:'ok'};
  if (!recordings.length && !formal.length) {
    next={kind:'add_recording',title:'まず録音を取り込む',detail:'カラオケ後、ボイスメモの録音を1つ選びます。',tone:'wait'};
  } else if (conflicts.length) {
    next={kind:'binding_conflict',title:'録音との対応を確認してください',detail:`同じ採点結果に複数の録音候補が残っています。${conflicts.length}件を確認してください。`,tone:'err',evidenceSetId:conflicts[0].set.evidenceSetId};
  } else if (needsReview.length) {
    next={kind:'review',title:'採点画像の内容を確認する',detail:'元画像と抽出結果を見比べて、合っていれば1回だけ確認します。',tone:'wait',evidenceSetId:needsReview[0].set.evidenceSetId};
  } else if (needsBinding.length) {
    next={kind:'binding',title:'この採点がどの録音か確認する',detail:'候補をSongScopeが出します。同じ1回の歌唱だと自分で分かる場合だけ選びます。',tone:'wait',evidenceSetId:needsBinding[0].set.evidenceSetId};
  } else if (needsStructure.length || needsReextract.length) {
    const target=(needsStructure[0]||needsReextract[0]);
    next={kind:'structure',title:'採点画像を読み取る',detail:'開発版ではここだけChatGPT経由です。解析用ZIPを書き出し、返った構造化JSONを読み込みます。最終版では通常UIから隠す工程です。',tone:'wait',evidenceSetId:target.set.evidenceSetId};
  } else if (recordings.length && !formal.length) {
    next={kind:'add_scoring',title:'DAM採点画像があれば取り込む',detail:'無ければ次の歌唱まで何もしなくて大丈夫です。',tone:'wait'};
  }
  return {
    recordings:recordings.length,
    formalEvidence:formal.length,
    bound:bound.length,
    pending:conflicts.length+needsStructure.length+needsReextract.length+needsReview.length+needsBinding.length,
    next
  };
}
async function renderNormalWorkflowStatus() {
  const box=$('#workflow-status'),pill=$('#workflow-status-pill');
  if (!box||!pill) return;
  const model=await buildNormalWorkflowStatus();
  const n=model.next;
  pill.className=`pill ${n.tone||'wait'}`;
  pill.textContent=n.tone==='ok'?'準備OK':n.tone==='err'?'要確認':'次の操作';
  let action='';
  if (n.kind==='add_recording'||n.kind==='add_scoring') action='<button class="primary wide" data-workflow-session>今回の記録を取り込む</button>';
  else if (n.kind==='review') action=`<button class="primary wide" data-workflow-review="${escapeHtml(n.evidenceSetId)}">採点内容を確認する</button>`;
  else if (n.kind==='binding'||n.kind==='binding_conflict') action=`<button class="primary wide" data-workflow-binding="${escapeHtml(n.evidenceSetId)}">どの録音か確認する</button>`;
  else if (n.kind==='structure') action=`<div class="workflow-dev-actions"><button class="primary wide" data-workflow-export="${escapeHtml(n.evidenceSetId)}">ChatGPTに渡すファイルを作る</button><button class="mini wide" data-workflow-import="${escapeHtml(n.evidenceSetId)}">読み取り結果をSongScopeへ戻す</button><p class="small">※ ここは開発中の暫定工程です。最終版では通常操作から消します。</p></div>`;
  else action='<button class="primary wide" data-workflow-session>今回の記録を取り込む</button>';
  box.innerHTML=`<p class="workflow-next-title"><b>${escapeHtml(n.title)}</b></p><p class="small">${escapeHtml(n.detail)}</p>${action}<p class="small workflow-counts">${model.pending?`確認待ち ${model.pending}件 ／ `:''}記録済み ${model.recordings}歌唱 ／ 採点付き ${model.bound}歌唱</p>`;
  $$('[data-workflow-session]').forEach(b=>b.addEventListener('click',()=>openSheet('sheet-session-import')));
  $$('[data-workflow-review]').forEach(b=>b.addEventListener('click',async()=>{try{await openStandaloneStructuredReview(b.dataset.workflowReview);}catch(e){toast((e&&e.message)||'レビューを開けませんでした');}}));
  $$('[data-workflow-binding]').forEach(b=>b.addEventListener('click',async()=>{try{await openBindingSheet(b.dataset.workflowBinding);}catch(e){toast((e&&e.message)||'Binding管理を開けませんでした');}}));
  $$('[data-workflow-export]').forEach(b=>b.addEventListener('click',()=>exportStandaloneEvidenceSet(b.dataset.workflowExport)));
  $$('[data-workflow-import]').forEach(b=>b.addEventListener('click',()=>{
    const inp=$('#scoring-structured-input');
    inp.dataset.evidenceSetId=b.dataset.workflowImport;
    inp.click();
  }));
}

function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/* =====================================================================
 * 録音の追加
 * ===================================================================== */

const SCORING_CONDITION_FIELDS = ['device','scoringMode','keyChange','octave'];
function scoringConditionDefaults() {
  const x = settings && settings.lastScoringConditions && typeof settings.lastScoringConditions === 'object' ? settings.lastScoringConditions : {};
  return {
    device: String(x.device || ''), scoringMode: String(x.scoringMode || ''),
    keyChange: String(x.keyChange || ''), octave: String(x.octave || '')
  };
}
function normalizeKeyChangeValue(v) {
  let x = String(v == null ? '' : v).normalize('NFKC').trim();
  if (!x) return '';
  const low = x.toLowerCase().replace(/\s+/g,'');
  if (['original','orig','原曲','原曲キー','±0','+0','-0','0'].includes(low)) return '0';
  const m = low.match(/^([+-]?)(\d{1,2})$/);
  if (!m) return x;
  let n = Number((m[1] || '') + m[2]);
  if (!isFinite(n) || Math.abs(n) > 12) return x;
  if (Object.is(n, -0) || n === 0) return '0';
  return n > 0 ? '+' + n : String(n);
}
function normalizeOctaveValue(v) {
  let x = String(v == null ? '' : v).normalize('NFKC').trim();
  if (!x) return '';
  const m = x.replace(/\s+/g,'').match(/^([+-]?)(\d)$/);
  if (!m) return x;
  const n = Number((m[1] || '') + m[2]);
  if (!isFinite(n) || Math.abs(n) > 3) return x;
  if (Object.is(n, -0) || n === 0) return '0';
  return n > 0 ? '+' + n : String(n);
}
function normalizeScoringText(v) {
  return String(v == null ? '' : v).normalize('NFKC').trim().replace(/\s+/g, ' ').toLowerCase();
}
function canonicalScoringConditionValue(field, value) {
  if (field === 'keyChange') return normalizeKeyChangeValue(value);
  if (field === 'octave') return normalizeOctaveValue(value);
  const raw = String(value == null ? '' : value).normalize('NFKC').trim();
  if (!raw || raw === '__OTHER__') return '';
  const n = normalizeScoringText(raw);
  if (field === 'device') {
    const compact = n.replace(/\s+/g,'');
    if (compact === 'damwao!' || compact === 'damwao') return 'DAM WAO!';
    if (compact === 'livedamair') return 'LIVE DAM AiR';
    if (compact === 'livedamai') return 'LIVE DAM Ai';
    if (compact === 'livedamstadium') return 'LIVE DAM STADIUM';
  }
  if (field === 'scoringMode') {
    const compact = n.replace(/\s+/g,'');
    if (compact === '精密採点aiheart') return '精密採点Ai Heart';
    if (compact === '精密採点ai') return '精密採点Ai';
    if (compact === '精密採点dx-g') return '精密採点DX-G';
    if (compact === '精密採点dx') return '精密採点DX';
  }
  return raw;
}
function scoringConditionComparableValue(field, value) {
  const x = canonicalScoringConditionValue(field, value);
  if (!x || x === '__OTHER__' || x === 'その他' || x === '不明') return '';
  return field === 'device' || field === 'scoringMode' ? normalizeScoringText(x) : x;
}
function setStructuredSelectValue(id, value, field) {
  const el = $(id);
  if (!el) return;
  const canonical = canonicalScoringConditionValue(field, value);
  for (const o of Array.from(el.querySelectorAll('option[data-legacy="1"]'))) o.remove();
  const target = canonical || '';
  if (Array.from(el.options).some(o => o.value === target)) { el.value = target; return; }
  if (target) {
    const o = document.createElement('option'); o.value = target; o.textContent = `旧入力: ${target}`; o.dataset.legacy = '1';
    el.appendChild(o); el.value = target;
  } else el.value = '';
}
function updateRecConfirmationUi() {
  const ctx = state.recFormContext || {};
  const at = $('#f-recat-confirm-status');
  if (at) {
    if (ctx.recordedAtExplicitConfirm) at.textContent = '時系列証拠: 正確な録音日時を本人確認済み';
    else if (ctx.recordedDateExplicitConfirm) at.textContent = '時系列証拠: 録音日だけ本人確認済み';
    else at.textContent = '時系列証拠: 日時未確認（相対順序だけでも可）';
  }
  const sc = $('#f-cond-confirm-status');
  if (sc) sc.textContent = ctx.scoringConditionsExplicitConfirm ? '採点4条件: 本人確認済み' : (ctx.scoringConditionsDefaulted ? '採点4条件: 前回値（未確認）' : '採点4条件: 未確認');
}
function confirmRecordedAtInForm() {
  if (!state.recFormContext) state.recFormContext = {};
  if (!$('#f-recat').value) { toast('録音日時を入力してください'); return; }
  state.recFormContext.recordedAtExplicitConfirm = true;
  state.recFormContext.recordedDateExplicitConfirm = false;
  state.recFormContext.chronologyPrecisionChoice = 'exact';
  updateRecConfirmationUi();
  toast('この録音日時を本人確認済みにしました');
}
function confirmRecordedDateInForm() {
  if (!state.recFormContext) state.recFormContext = {};
  const v = $('#f-recdate').value;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(v||''))) { toast('録音日を入力してください'); return; }
  state.recFormContext.recordedDateExplicitConfirm = true;
  state.recFormContext.recordedAtExplicitConfirm = false;
  state.recFormContext.chronologyPrecisionChoice = 'day';
  updateRecConfirmationUi();
  toast('この録音日だけを本人確認済みにしました');
}
function keepRecordingTimeUnknownInForm() {
  if (!state.recFormContext) state.recFormContext = {};
  state.recFormContext.recordedAtExplicitConfirm = false;
  state.recFormContext.recordedDateExplicitConfirm = false;
  state.recFormContext.chronologyPrecisionChoice = 'unknown';
  updateRecConfirmationUi();
  toast('録音日時は未確認のままにします。相対順序の確認は引き続き利用できます');
}
function confirmScoringConditionsFromPrevious() {
  if (!state.recFormContext) state.recFormContext = {};
  const defs = scoringConditionDefaults();
  if (!SCORING_CONDITION_FIELDS.every(f => defs[f] && defs[f] !== '__OTHER__')) { toast('前回の採点4条件が揃っていません'); return; }
  setStructuredSelectValue('#f-device', defs.device, 'device');
  setStructuredSelectValue('#f-mode', defs.scoringMode, 'scoringMode');
  setStructuredSelectValue('#f-key', defs.keyChange, 'keyChange');
  setStructuredSelectValue('#f-octave', defs.octave, 'octave');
  state.recFormContext.scoringConditionsExplicitConfirm = true;
  state.recFormContext.scoringConditionsDefaulted = true;
  updateRecConfirmationUi();
  toast('前回と同じ採点4条件として確認しました');
}
function confirmCurrentScoringConditions() {
  if (!state.recFormContext) state.recFormContext = {};
  const vals = [$('#f-device').value, $('#f-mode').value, $('#f-key').value, $('#f-octave').value];
  if (vals.some(v => !String(v || '').trim() || v === '__OTHER__')) { toast('4条件すべてを具体的に選んでください'); return; }
  state.recFormContext.scoringConditionsExplicitConfirm = true;
  updateRecConfirmationUi();
  toast('現在の採点4条件を本人確認済みにしました');
}
function persistLastScoringConditions(form) {
  if (!form) return;
  const x = {};
  for (const f of SCORING_CONDITION_FIELDS) x[f] = canonicalScoringConditionValue(f, form[f]);
  if (Object.values(x).some(Boolean)) {
    settings.lastScoringConditions = x;
    saveSettings();
  }
}
function openAddSheet(file) {
  state.pendingFile = file;
  state.editingRec = false;
  $('#rec-sheet-title').textContent = '録音を追加';
  $('#f-title').value = file ? file.name.replace(/\.[^.]+$/, '') : '';
  $('#f-artist').value = '';
  $('#f-score').value = '';
  const scDefaults = scoringConditionDefaults();
  setStructuredSelectValue('#f-key', scDefaults.keyChange, 'keyChange');
  setStructuredSelectValue('#f-octave', scDefaults.octave, 'octave');
  setStructuredSelectValue('#f-device', scDefaults.device, 'device');
  setStructuredSelectValue('#f-mode', scDefaults.scoringMode, 'scoringMode');
  $('#f-memo').value = '';
  $('#f-setup').value = settings.recordingSetupPreset;
  const hasFileModified = !!(file && file.lastModified && isFinite(file.lastModified));
  const d = hasFileModified ? new Date(file.lastModified) : new Date();
  $('#f-recat').value = toLocalInput(d);
  $('#f-recdate').value = '';
  state.recFormContext = {
    mode: 'add', initial: recFormSnapshot(), previousProvenance: {},
    recordedAtDefaultSource: hasFileModified ? 'file_last_modified_unverified' : 'import_time_default',
    recordedAtExplicitConfirm: false,
    recordedDateExplicitConfirm: false,
    chronologyPrecisionChoice: 'unknown',
    scoringConditionsDefaulted: Object.values(scDefaults).some(Boolean),
    scoringConditionsExplicitConfirm: false
  };
  updateRecConfirmationUi();
  const det = $('#sheet-rec .details');
  if (det) det.open = false;   // 任意項目は毎回入力させない
  openSheet('sheet-rec');
}
function toLocalInput(d) {
  const p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

const REC_METADATA_PROVENANCE_FIELDS = ['title','artist','damScore','keyChange','octave','device','scoringMode','memo','recordingSetupPreset','recordedAt','recordedDate'];
function recFormSnapshot() {
  const at = $('#f-recat').value;
  return {
    title: $('#f-title').value.trim(), artist: $('#f-artist').value.trim(), damScore: $('#f-score').value.trim(),
    keyChange: canonicalScoringConditionValue('keyChange', $('#f-key').value),
    octave: canonicalScoringConditionValue('octave', $('#f-octave').value),
    device: canonicalScoringConditionValue('device', $('#f-device').value),
    scoringMode: canonicalScoringConditionValue('scoringMode', $('#f-mode').value),
    memo: $('#f-memo').value.trim(), recordingSetupPreset: $('#f-setup').value.trim(),
    recordedAt: at ? new Date(at).toISOString() : null,
    recordedDate: ($('#f-recdate') && $('#f-recdate').value) ? $('#f-recdate').value : null
  };
}
function provenanceEntry(source, confirmation = 'unknown') {
  return { source, confirmation, updatedAt: nowIso() };
}
function normalizedMetadataProvenance(rec) {
  const src = rec && rec.metadataProvenance && typeof rec.metadataProvenance === 'object' ? rec.metadataProvenance : {};
  const out = {};
  for (const k of REC_METADATA_PROVENANCE_FIELDS) {
    if (src[k] && src[k].source) out[k] = src[k];
    else if (rec && rec[k]) out[k] = { source: 'legacy_unknown', confirmation: 'unknown', updatedAt: rec.updatedAt || rec.createdAt || null };
  }
  return out;
}
function buildMetadataProvenance(form) {
  const ctx = state.recFormContext || {};
  const prev = ctx.previousProvenance || {};
  const initial = ctx.initial || {};
  const out = Object.assign({}, prev);
  if (ctx.chronologyPrecisionChoice === 'unknown') {
    if (out.recordedAt) out.recordedAt = provenanceEntry('user_left_recorded_at_unconfirmed', 'unknown');
    if (out.recordedDate) out.recordedDate = provenanceEntry('user_left_recorded_date_unconfirmed', 'unknown');
  } else if (ctx.chronologyPrecisionChoice === 'day') {
    if (out.recordedAt) out.recordedAt = provenanceEntry('exact_time_not_confirmed_date_only', 'unknown');
  } else if (ctx.chronologyPrecisionChoice === 'exact') {
    if (out.recordedDate) out.recordedDate = provenanceEntry('superseded_by_exact_recorded_at', 'unknown');
  }
  const same = (a,b) => String(a == null ? '' : a) === String(b == null ? '' : b);
  for (const k of REC_METADATA_PROVENANCE_FIELDS) {
    const value = form[k];
    if (!value) { if (ctx.mode === 'edit' && !same(value, initial[k])) delete out[k]; continue; }
    if (ctx.mode === 'add') {
      if (k === 'recordedAt' && ctx.recordedAtExplicitConfirm) out[k] = provenanceEntry('user_confirmed_recorded_at', 'user_confirmed');
      else if (k === 'recordedDate' && ctx.recordedDateExplicitConfirm) out[k] = provenanceEntry('user_confirmed_recorded_date', 'user_confirmed');
      else if (k === 'recordedAt' && same(value, initial[k])) out[k] = provenanceEntry(ctx.recordedAtDefaultSource || 'import_time_default', 'unverified');
      else if (SCORING_CONDITION_FIELDS.includes(k) && ctx.scoringConditionsExplicitConfirm) out[k] = provenanceEntry('user_confirmed_scoring_conditions', 'user_confirmed');
      else if (SCORING_CONDITION_FIELDS.includes(k) && ctx.scoringConditionsDefaulted && same(value, initial[k])) out[k] = provenanceEntry('previous_recording_default', 'unverified');
      else if (k === 'recordingSetupPreset' && same(value, initial[k])) out[k] = provenanceEntry('default_preset', 'unverified');
      else if (k === 'title' && same(value, initial[k])) out[k] = provenanceEntry('file_name_default', 'unverified');
      else out[k] = provenanceEntry('user_input', 'user_confirmed');
    } else if (k === 'recordedAt' && ctx.recordedAtExplicitConfirm) {
      out[k] = provenanceEntry('user_confirmed_recorded_at', 'user_confirmed');
    } else if (k === 'recordedDate' && ctx.recordedDateExplicitConfirm) {
      out[k] = provenanceEntry('user_confirmed_recorded_date', 'user_confirmed');
    } else if (SCORING_CONDITION_FIELDS.includes(k) && ctx.scoringConditionsExplicitConfirm) {
      out[k] = provenanceEntry('user_confirmed_scoring_conditions', 'user_confirmed');
    } else if (!same(value, initial[k])) {
      out[k] = provenanceEntry('user_edited', 'user_confirmed');
    } else if (!out[k] || !out[k].source) {
      out[k] = { source: 'legacy_unknown', confirmation: 'unknown', updatedAt: state.rec && (state.rec.updatedAt || state.rec.createdAt) || null };
    }
  }
  return out;
}
function imageExtFromMeta(meta) {
  const type = String(meta && meta.mimeType || '').toLowerCase();
  if (type.includes('png')) return '.png';
  if (type.includes('webp')) return '.webp';
  if (type.includes('heic') || type.includes('heif')) return '.heic';
  if (type.includes('jpeg') || type.includes('jpg')) return '.jpg';
  const m = String(meta && meta.fileName || '').match(/\.(png|jpe?g|webp|heic|heif)$/i);
  return m ? m[0].toLowerCase().replace('.jpeg','.jpg') : '.img';
}
function normalizeEvaluationEvidenceImages(asset) {
  if (!asset) return [];
  const arr = Array.isArray(asset.evaluationEvidenceImages) ? asset.evaluationEvidenceImages.filter(x => x && x.meta && x.meta.sha256) : [];
  if (arr.length) return arr.map((x,i)=>({ imageId:x.imageId || ('img_'+String(i+1).padStart(2,'0')), meta:x.meta, blob:x.blob || null }));
  if (asset.evaluationImageMeta && asset.evaluationImageMeta.sha256) {
    return [{ imageId:'img_01', meta:asset.evaluationImageMeta, blob:asset.evaluationImageBlob || null }];
  }
  return [];
}
function evaluationEvidenceSetDescriptor(rec, images) {
  const list=(images||[]).map((x,i)=>({
    imageId:x.imageId || ('img_'+String(i+1).padStart(2,'0')),
    sha256:String(x.meta && x.meta.sha256 || '').toLowerCase(),
    fileName:x.meta && x.meta.fileName || null,
    mimeType:x.meta && x.meta.mimeType || null,
    fileSize:x.meta && x.meta.fileSize || null,
    attachedAt:x.meta && x.meta.attachedAt || null,
    source:'dam_denmoku'
  })).filter(x=>x.sha256);
  return {
    schemaVersion:EVIDENCE_SET_SCHEMA,
    status:list.length?'available':'unavailable',
    evidenceSetId: rec && rec.recordingId ? `evalset_${rec.recordingId}` : null,
    recordingId:rec && rec.recordingId || null,
    source:{ provider:'DAM', application:'DAMデンモク', sourceKey:'dam_denmoku' },
    imageCount:list.length,
    images:list,
    interpretation:'One scoring result may be represented by one or more DAMデンモク screenshots. Images are raw evidence; SongScope does not OCR them.'
  };
}
function evidenceSetShaList(images) {
  return (images||[]).map(x=>String(x.meta && x.meta.sha256 || '').toLowerCase()).filter(Boolean);
}
function sameStringSet(a,b) {
  const aa=[...(a||[])].map(String).sort(); const bb=[...(b||[])].map(String).sort();
  return aa.length===bb.length && aa.every((x,i)=>x===bb[i]);
}
function evaluationImageDescriptor(rec, meta) {
  if (!meta || !meta.sha256) return { status: 'unavailable' };
  return {
    status: 'available', type: 'scoring_result_image', source: 'user_attachment',
    recordingId: rec && rec.recordingId || null, fileName: meta.fileName || null, mimeType: meta.mimeType || null,
    fileSize: meta.fileSize || null, sha256: meta.sha256, attachedAt: meta.attachedAt || null,
    parsedByApp: false, interpretation: 'Image evidence only. SongScope does not OCR or infer score/subscores from this image.'
  };
}
function parseStoredScore(v) {
  if (v === null || v === undefined || String(v).trim() === '') return null;
  const n = Number(String(v).replace(/[^0-9.\-]/g, ''));
  return isFinite(n) ? +n.toFixed(3) : null;
}
function structuredEvaluationDocument(stored) {
  if (!stored || typeof stored !== 'object') return null;
  return stored.document && typeof stored.document === 'object' ? stored.document : stored;
}
function structuredOverallScore(stored) {
  const doc = structuredEvaluationDocument(stored);
  const v = doc && doc.result && doc.result.overallScore && doc.result.overallScore.value;
  const n = Number(v);
  return isFinite(n) ? +n.toFixed(3) : null;
}
function structuredPersonalBest(stored) {
  const doc = structuredEvaluationDocument(stored);
  const nobj = doc && doc.result && (doc.result.personalBest || doc.result.personalBestScore || doc.result.bestScore);
  const v = nobj && typeof nobj === 'object' ? nobj.value : nobj;
  const n = Number(v);
  return isFinite(n) ? +n.toFixed(3) : null;
}
function manualVsStructuredScoreConsistency(rec, structuredDesc) {
  const storedScore = parseStoredScore(rec && rec.damScore);
  const extractedScore = structuredDesc && structuredDesc.verification && structuredDesc.verification.status === 'source_verified' ? structuredDesc.overallScore : null;
  if (storedScore === null || extractedScore === null) return { status:'not_comparable', storedScore, extractedScore, delta:null };
  const delta = +(storedScore - extractedScore).toFixed(3);
  if (Math.abs(delta) <= 0.001) return { status:'same_value', storedScore, extractedScore, delta:0 };
  const prov = normalizedMetadataProvenance(rec || {}).damScore || {};
  return { status: prov.confirmation === 'user_confirmed' ? 'conflict_manual_score_vs_source_verified_image' : 'different_value_unconfirmed_manual_score', storedScore, extractedScore, delta };
}
function structuredEvaluationDescriptor(rec, imageMeta, stored) {
  const doc = structuredEvaluationDocument(stored);
  if (!doc) return { status: 'unavailable' };
  const recId = rec && rec.recordingId || null;
  const docRecId = doc.recordingId || null;
  const recordingIdMatch = !!recId && !!docRecId && recId === docRecId;
  const currentImages = state && Array.isArray(state.evaluationEvidenceImages) && state.evaluationEvidenceImages.length ? state.evaluationEvidenceImages : (imageMeta && imageMeta.sha256 ? [{meta:imageMeta}] : []);
  const currentShas = evidenceSetShaList(currentImages);
  const sourceSha = doc.sourceEvidence && doc.sourceEvidence.sha256 ? String(doc.sourceEvidence.sha256).toLowerCase() : null;
  const sourceShas = doc.sourceEvidence && Array.isArray(doc.sourceEvidence.images) ? doc.sourceEvidence.images.map(x=>String(x.sha256||'').toLowerCase()).filter(Boolean) : (sourceSha ? [sourceSha] : []);
  const sourceEvidenceMatch = sameStringSet(sourceShas, currentShas);
  let verificationStatus = 'unverified';
  if (!currentShas.length) verificationStatus = 'source_image_missing';
  else if (!recordingIdMatch) verificationStatus = 'recording_id_mismatch';
  else if (!sourceEvidenceMatch) verificationStatus = 'source_image_set_sha_mismatch';
  else verificationStatus = 'source_verified';
  const currentSha = currentShas.length===1 ? currentShas[0] : null;
  return {
    status: 'available',
    schemaVersion: doc.schemaVersion || null,
    recordingId: docRecId,
    sourceEvidence: doc.sourceEvidence || null,
    extraction: doc.extraction || null,
    result: doc.result || null,
    overallScore: structuredOverallScore(stored),
    personalBest: structuredPersonalBest(stored),
    verification: {
      status: verificationStatus,
      recordingIdMatch,
      sourceEvidenceMatch,
      currentScoringImageSha256: currentSha,
      currentScoringImageSha256s: currentShas
    },
    importMeta: stored.importMeta || null,
    note: 'Externally structured interpretation of the attached scoring-result image. SongScope validates source identity but does not itself OCR or certify extracted values.'
  };
}
function validateStructuredEvaluationDocument(doc, rec, imageMeta) {
  if (!doc || typeof doc !== 'object' || Array.isArray(doc)) throw new Error('評価JSONの形式が正しくありません');
  if (![EXTERNAL_EVALUATION_SCHEMA, EXTERNAL_EVALUATION_SCHEMA_V2].includes(doc.schemaVersion)) throw new Error('未対応の評価JSON schemaです');
  if (!doc.recordingId || !rec || doc.recordingId !== rec.recordingId) throw new Error('この録音用の評価JSONではありません');
  const currentImages = Array.isArray(state.evaluationEvidenceImages) && state.evaluationEvidenceImages.length ? state.evaluationEvidenceImages : (imageMeta && imageMeta.sha256 ? [{meta:imageMeta}] : []);
  const currentShas=evidenceSetShaList(currentImages);
  if (!currentShas.length) throw new Error('先にDAMデンモクの採点履歴画像を添付してください');
  const sourceShas = doc.sourceEvidence && Array.isArray(doc.sourceEvidence.images)
    ? doc.sourceEvidence.images.map(x=>String(x.sha256||'').toLowerCase()).filter(Boolean)
    : (doc.sourceEvidence && doc.sourceEvidence.sha256 ? [String(doc.sourceEvidence.sha256).toLowerCase()] : []);
  if (!sameStringSet(sourceShas,currentShas)) throw new Error('評価JSONの元画像SHA-256集合が現在の採点証拠セットと一致しません');
  if (!doc.result || typeof doc.result !== 'object' || Array.isArray(doc.result)) throw new Error('評価JSONにresultがありません');
  return true;
}
function buildEvaluationExtractionRequest(rec, imageMetaOrImages) {
  if (!rec) return null;
  const images = Array.isArray(imageMetaOrImages) ? imageMetaOrImages : (imageMetaOrImages && imageMetaOrImages.sha256 ? [{imageId:'img_01',meta:imageMetaOrImages}] : []);
  const set=evaluationEvidenceSetDescriptor(rec, images);
  if (!set.imageCount) return null;
  return {
    schemaVersion: 'songscope-evaluation-extraction-request-v2',
    recordingId: rec.recordingId,
    sourceEvidence: {
      type: 'scoring_evidence_set',
      sourceApp: 'dam_denmoku',
      provider: 'DAM',
      application: 'DAMデンモク',
      evidenceSetId:set.evidenceSetId,
      images:set.images.map(x=>({imageId:x.imageId,sha256:x.sha256,fileName:x.fileName,mimeType:x.mimeType}))
    },
    requestedOutputSchemaVersion: EXTERNAL_EVALUATION_SCHEMA_V2,
    evidenceRules: {
      oneScoringResultMayUseMultipleScreenshots: true,
      screenshotsMustBelongToSameScoringResult: true,
      sourceRestrictedToDamDenmokuForG0: true,
      directPhotoOfKaraokeTerminalOutOfScope: true
    },
    instructions: [
      'Treat all attached images in this evidence set as DAMデンモク screenshots for one scoring result.',
      'Structure only values or discrete states that are explicitly visible in one or more screenshots. Do not infer hidden numeric scales.',
      'Return sourceEvidence.images with every imageId and SHA-256 exactly as supplied. Do not omit an image even if it contributes no extracted field.',
      'If multiple screenshots repeat a field, require visible agreement; if they conflict, mark that field ambiguous/conflict instead of choosing silently.',
      'Extract overallScore and personalBest/highestScore as different fields. Never substitute personalBest for overallScore.',
      'If visible, extract scoringPerformedAt as the timestamp displayed by DAMデンモク. Keep it separate from iPhone recordedAt.',
      'If visible, extract ranking.position/ranking.total as context only.',
      'Discrete visual observations may include longToneSkill and vibratoSkill as litCount/totalCount when individual symbols are countable.',
      'Stability and rhythm may be stored only as categorical/ordinal displayed positions plus their endpoint labels; never convert them to percentages or invented scores.',
      'Vocal range may use explicitly printed note/range labels only. Do not infer notes from keyboard geometry alone.',
      'Pitch graph markers may be counted only when visually distinguishable. Preserve section/relative graphical location only; do not convert graphical x-position to audio seconds in G0.',
      'Preserve DAM analysis-report text as external system text, not as SongScope diagnosis.',
      'Do not judge improvement, infer acoustic causes, or recommend practice in this extraction step.'
    ],
    outputTemplate: {
      schemaVersion: EXTERNAL_EVALUATION_SCHEMA_V2,
      recordingId: rec.recordingId,
      sourceEvidence: {
        type:'scoring_evidence_set', sourceApp:'dam_denmoku', evidenceSetId:set.evidenceSetId,
        images:set.images.map(x=>({imageId:x.imageId,sha256:x.sha256}))
      },
      extraction: { method:'external_visual_extraction', producer:null, createdAt:null, userReview:'not_yet_confirmed' },
      result: {
        title:null, artist:null, scoringMode:null, scoringPerformedAt:null,
        overallScore:null, personalBest:null, nationalAverage:null, ranking:null, bonus:null,
        metrics:[], techniques:[], vibrato:null,
        discreteVisualObservations:{ longToneSkill:null, vibratoSkill:null, stability:null, rhythm:null, vocalRange:null, pitchAccuracyGraph:null },
        analysisReport:null, notStructured:[]
      }
    },
    g0Policy: { layer:'observation_only', source:'dam_denmoku', multiImageEvidenceSet:true, noHiddenScaleInference:true, noAudioTimeMappingInG0:true, noCrossTakeJudgementInExtraction:true, noPracticeRecommendationInExtraction:true }
  };
}
function buildRecordingEvaluationAnchors(rec, imageMeta, structured = state.evaluationStructured) {
  const prov = normalizedMetadataProvenance(rec || {});
  const structuredDesc = structuredEvaluationDescriptor(rec, imageMeta, structured);
  const storedScore = parseStoredScore(rec && rec.damScore);
  const scoreCheck = manualVsStructuredScoreConsistency(rec, structuredDesc);
  const extractedScore = scoreCheck.extractedScore;
  const personalBest = structuredDesc.verification && structuredDesc.verification.status === 'source_verified' ? structuredDesc.personalBest : null;
  return {
    schemaVersion: 'songscope-evaluation-anchors-v2',
    recordingId: rec && rec.recordingId || null,
    damScore: {
      status: storedScore === null ? 'unavailable' : 'available',
      value: storedScore, rawStoredValue: rec && rec.damScore || null,
      provenance: prov.damScore || { source: 'absent', confirmation: 'unknown' },
      note: 'External outcome metadata only; it does not identify the acoustic cause of a change.'
    },
    scoringResultImage: evaluationImageDescriptor(rec, imageMeta),
    scoringResultImages: evaluationEvidenceSetDescriptor(rec, state.evaluationEvidenceImages && state.evaluationEvidenceImages.length ? state.evaluationEvidenceImages : (imageMeta ? [{imageId:'img_01',meta:imageMeta}] : [])),
    structuredScoringResult: structuredDesc,
    personalBest: { status: personalBest === null ? 'unavailable' : 'available_source_verified', value: personalBest, interpretation: 'Context from the scoring screen only. It can indicate that SongScope may omit other takes, but it is not used as hard chronology evidence.' },
    consistencyChecks: {
      storedDamScoreVsStructuredOverallScore: scoreCheck.status,
      storedDamScoreMinusStructuredOverallScore: scoreCheck.delta,
      conflictBlocksManualScoreComparison: scoreCheck.status === 'conflict_manual_score_vs_source_verified_image',
      policy: 'A user-confirmed manual score that conflicts with a source-verified image-derived overallScore is explicitly blocked from manual-score comparison; values are never silently reconciled.'
    },
    chronologyMetadata: {
      recordedAt: { value: rec && rec.recordedAt || null, provenance: prov.recordedAt || { source: 'legacy_unknown', confirmation: 'unknown' }, precision: 'datetime' },
      recordedDate: { value: rec && rec.recordedDate || null, provenance: prov.recordedDate || { source: 'absent', confirmation: 'unknown' }, precision: 'day' },
      relativeOrderAvailableSeparately: true
    },
    policy: {
      appDoesNotParseImage: true,
      structuredEvaluationMustReferenceCurrentImageSha256: true,
      noAutomaticImprovementJudgement: true,
      doNotReconcileConflictsSilently: true
    }
  };
}

function openEditSheet(rec) {
  state.pendingFile = null;
  state.editingRec = true;
  $('#rec-sheet-title').textContent = '録音情報を編集';
  $('#f-title').value = rec.title || '';
  $('#f-artist').value = rec.artist || '';
  $('#f-score').value = rec.damScore || '';
  setStructuredSelectValue('#f-key', rec.keyChange || '', 'keyChange');
  setStructuredSelectValue('#f-octave', rec.octave || '', 'octave');
  setStructuredSelectValue('#f-device', rec.device || '', 'device');
  setStructuredSelectValue('#f-mode', rec.scoringMode || '', 'scoringMode');
  $('#f-memo').value = rec.memo || '';
  $('#f-setup').value = rec.recordingSetupPreset || settings.recordingSetupPreset;
  $('#f-recat').value = rec.recordedAt ? toLocalInput(new Date(rec.recordedAt)) : '';
  $('#f-recdate').value = rec.recordedDate || '';
  const existingProv = normalizedMetadataProvenance(rec);
  state.recFormContext = {
    mode: 'edit', initial: recFormSnapshot(), previousProvenance: existingProv,
    recordedAtExplicitConfirm: !!(existingProv.recordedAt && existingProv.recordedAt.confirmation === 'user_confirmed'),
    recordedDateExplicitConfirm: !!(existingProv.recordedDate && existingProv.recordedDate.confirmation === 'user_confirmed'),
    chronologyPrecisionChoice: (existingProv.recordedAt && existingProv.recordedAt.confirmation === 'user_confirmed') ? 'exact' : ((existingProv.recordedDate && existingProv.recordedDate.confirmation === 'user_confirmed') ? 'day' : 'unknown'),
    scoringConditionsDefaulted: false,
    scoringConditionsExplicitConfirm: SCORING_CONDITION_FIELDS.every(k => existingProv[k] && existingProv[k].confirmation === 'user_confirmed')
  };
  updateRecConfirmationUi();
  const det = $('#sheet-rec .details');
  if (det) det.open = true;
  openSheet('sheet-rec');
}

function readRecForm() {
  const t = $('#f-title').value.trim();
  if (!t) { toast('曲名を入力してください'); return null; }
  const at = $('#f-recat').value;
  const form = {
    title: t,
    artist: $('#f-artist').value.trim(),
    damScore: $('#f-score').value.trim(),
    keyChange: canonicalScoringConditionValue('keyChange', $('#f-key').value),
    octave: canonicalScoringConditionValue('octave', $('#f-octave').value),
    device: canonicalScoringConditionValue('device', $('#f-device').value),
    scoringMode: canonicalScoringConditionValue('scoringMode', $('#f-mode').value),
    memo: $('#f-memo').value.trim(),
    recordingSetupPreset: $('#f-setup').value.trim(),
    recordedAt: at ? new Date(at).toISOString() : null,
    recordedDate: ($('#f-recdate') && $('#f-recdate').value) ? $('#f-recdate').value : null
  };
  form.metadataProvenance = buildMetadataProvenance(form);
  return form;
}

async function onRecSave() {
  const form = readRecForm();
  if (!form) return;
  persistLastScoringConditions(form);

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
    rec.metadataProvenance = normalizedMetadataProvenance(rec);
    for (const k of ['damScore', 'keyChange', 'octave', 'device', 'scoringMode', 'memo', 'recordingSetupPreset']) {
      if (form[k]) {
        rec[k] = form[k];
        if (form.metadataProvenance && form.metadataProvenance[k]) rec.metadataProvenance[k] = form.metadataProvenance[k];
      }
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
  state.evaluationImageMeta = null;
  state.evaluationEvidenceImages = [];
  state.evaluationStructured = null;
  state.legacyScoringEvidenceMigration = null;
  state.scoringEvidenceCandidates=[];
  state.scoringEvidenceContext=null;

  showView('view-review');
  renderReviewHeader();
  updateAbReadout();

  // 音声を用意（PCMは保持せず、Blob URL で再生する）
  try {
    const a = await dbGet('audio', id);
    if (a && a.blob) attachAudio(a.blob);
    state.evaluationEvidenceImages = normalizeEvaluationEvidenceImages(a);
    state.evaluationImageMeta = state.evaluationEvidenceImages.length ? state.evaluationEvidenceImages[0].meta : null;
    state.evaluationStructured = a && a.evaluationStructured ? a.evaluationStructured : null;
    state.legacyScoringEvidenceMigration=a&&a.legacyScoringEvidenceMigration?a.legacyScoringEvidenceMigration:null;
    state.scoringEvidenceContext=await scoringEvidenceRelationsForRecording(id);
    state.scoringEvidenceCandidates=state.scoringEvidenceContext.legacyCandidateSets||[];
    renderEvaluationAnchor();
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
  renderEvaluationAnchor();
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

function renderEvaluationAnchor() {
  const box=$('#rv-eval-status');
  if (!box||!state.rec) return;
  const score=parseStoredScore(state.rec.damScore);
  const unified=recordingScoringEvidenceDescriptor(state.rec,state.scoringEvidenceContext);
  const mig=state.legacyScoringEvidenceMigration||{};
  const oldImageCount=(state.evaluationEvidenceImages||[]).length;
  const parts=[
    score===null?'DAM点数: 未登録':`DAM点数: ${score.toFixed(3)}`,
    `Binding: ${unified.status||'unavailable'}`,
    `明示Binding済み証拠: ${Number(unified.boundEvidenceSetCount||0)}件`,
    `旧添付candidate: ${Number(unified.legacyCandidateCount||0)}件`,
    `旧添付raw画像: ${oldImageCount}枚（read-only）`
  ];
  let status='旧添付なし';
  if (mig.status==='migrated_candidate_only') status=`移行済み → ${mig.evidenceSetId} / candidate only / NOT binding`;
  else if (mig.status) status=`移行状態: ${mig.status}${mig.error?' / '+mig.error:''}`;
  box.innerHTML=`<p class="small">${parts.map(escapeHtml).join(' ／ ')}</p><p class="small"><b>build13 authoritative path:</b> ${escapeHtml(status)}</p><p class="small">旧audio store内の採点画像/JSONは災害復旧・監査のため削除していませんが、比較・履歴・exportはscoringEvidenceSets＋append-only bindingAssertionsから関係を導出します。旧添付関係は同一performanceの確認ではありません。</p>`;
  const rm=$('#btn-eval-image-remove'); if(rm)rm.hidden=true;
  const srm=$('#btn-eval-json-remove'); if(srm)srm.hidden=true;
}

async function saveEvaluationImages(files) {
  throw new Error('build08では録音への採点証拠の直接追加・変更を停止しています。ホームのDAMデンモク採点履歴を使用してください。');
  if (!state.rec || !files || !files.length) return;
  try {
    busy('評価アンカー', 'DAMデンモク採点履歴を保存しています…', 20);
    const asset = await dbGet('audio', state.rec.recordingId);
    if (!asset || !asset.blob) throw new Error('元音声の保存データがありません');
    let arr=normalizeEvaluationEvidenceImages(asset);
    const existing=new Set(arr.map(x=>String(x.meta.sha256).toLowerCase()));
    let added=0;
    for (const file of files) {
      const looksImage = String(file.type || '').startsWith('image/') || /\.(png|jpe?g|webp|heic|heif)$/i.test(String(file.name || ''));
      if (!looksImage) continue;
      if (file.size > 30 * 1024 * 1024) throw new Error('30MBを超える画像があります');
      const buf=await file.arrayBuffer(); const sha=await sha256Hex(buf); const key=sha.toLowerCase();
      if (existing.has(key)) continue;
      const idx=arr.length+1;
      arr.push({ imageId:'img_'+String(idx).padStart(2,'0'), blob:file, meta:{
        type:'scoring_result_image', source:'dam_denmoku', sourceApplication:'DAMデンモク', fileName:file.name||`dam_denmoku_${idx}`,
        mimeType:file.type||'application/octet-stream', fileSize:file.size, sha256:sha, attachedAt:nowIso(), parsedByApp:false
      }});
      existing.add(key); added++;
    }
    if (!arr.length) throw new Error('画像ファイルを選んでください');
    // Re-number only the display IDs; SHA is the actual identity.
    arr=arr.map((x,i)=>({...x,imageId:'img_'+String(i+1).padStart(2,'0')}));
    asset.evaluationEvidenceImages=arr;
    // legacy compatibility: first image remains mirrored in old fields.
    asset.evaluationImageBlob=arr[0].blob; asset.evaluationImageMeta=arr[0].meta;
    await dbPut('audio', asset);
    state.evaluationEvidenceImages=arr; state.evaluationImageMeta=arr[0].meta;
    closeSheet(); renderEvaluationAnchor(); toast(added ? `採点履歴画像を${added}枚追加しました` : '同じ画像は追加しませんでした');
  } catch (e) { closeSheet(); console.error(e); toast((e&&e.message)||'採点履歴画像を保存できませんでした'); }
}
async function removeEvaluationImage() {
  throw new Error('build08では録音への採点証拠の直接追加・変更を停止しています。ホームのDAMデンモク採点履歴を使用してください。');
  if (!state.rec || !(state.evaluationEvidenceImages||[]).length) return;
  if (!confirm('この録音に紐づけたDAMデンモク採点履歴画像をすべて外しますか？')) return;
  try {
    const asset=await dbGet('audio',state.rec.recordingId);
    if (asset) { delete asset.evaluationEvidenceImages; delete asset.evaluationImageBlob; delete asset.evaluationImageMeta; await dbPut('audio',asset); }
    state.evaluationEvidenceImages=[]; state.evaluationImageMeta=null; renderEvaluationAnchor(); toast('採点履歴画像をすべて外しました');
  } catch(e){ toast('画像を外せませんでした'); }
}

async function saveStructuredEvaluation(file) {
  throw new Error('build08では録音への採点証拠の直接追加・変更を停止しています。ホームのDAMデンモク採点履歴を使用してください。');
  if (!state.rec || !file) return;
  if (file.size > 1024 * 1024) { toast('評価JSONが大きすぎます（1MB以下）'); return; }
  try {
    const buf = await file.arrayBuffer();
    const text = new TextDecoder('utf-8').decode(buf);
    const doc = JSON.parse(text);
    validateStructuredEvaluationDocument(doc, state.rec, state.evaluationImageMeta);
    if (state.evaluationStructured && !confirm('既存の構造化評価JSONを置き換えますか？')) return;
    const asset = await dbGet('audio', state.rec.recordingId);
    if (!asset || !asset.blob) throw new Error('元音声の保存データがありません');
    asset.evaluationStructured = {
      document: doc,
      importMeta: {
        source: 'external_json_import',
        fileName: file.name || 'structured_evaluation.json',
        fileSha256: await sha256Hex(buf),
        importedAt: nowIso(),
        appVersion: APP_VERSION,
        buildId: BUILD_ID
      }
    };
    await dbPut('audio', asset);
    state.evaluationStructured = asset.evaluationStructured;
    renderEvaluationAnchor(); toast('構造化評価JSONを保存しました');
  } catch (e) {
    console.error(e); toast((e && e.message) || '評価JSONを保存できませんでした');
  }
}
async function removeStructuredEvaluation() {
  throw new Error('build08では録音への採点証拠の直接追加・変更を停止しています。ホームのDAMデンモク採点履歴を使用してください。');
  if (!state.rec || !state.evaluationStructured) return;
  if (!confirm('この録音に紐づけた構造化評価JSONを外しますか？')) return;
  try {
    const asset = await dbGet('audio', state.rec.recordingId);
    if (asset) { delete asset.evaluationStructured; await dbPut('audio', asset); }
    state.evaluationStructured = null; renderEvaluationAnchor(); toast('構造化評価JSONを外しました');
  } catch (e) { toast('構造化評価JSONを外せませんでした'); }
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
    metadataProvenance: normalizedMetadataProvenance(rec),
    evaluationAnchors: buildUnifiedRecordingEvaluationAnchors(rec,state.scoringEvidenceContext),
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
  L.push(`DAM Score provenance: ${((normalizedMetadataProvenance(rec).damScore || {}).source) || ''}`);
  L.push(`RecordedAt provenance: ${((normalizedMetadataProvenance(rec).recordedAt || {}).source) || ''}`);
  const scoringEvidence=recordingScoringEvidenceDescriptor(rec,state.scoringEvidenceContext);
  L.push(`Scoring relationship status: ${scoringEvidence.status||'unavailable'}`);
  L.push(`Explicitly bound scoring evidence sets: ${scoringEvidence.boundEvidenceSetCount||0}`);
  L.push(`Legacy attachment candidates: ${scoringEvidence.legacyCandidateCount||0}`);
  L.push('Legacy recording-attached scoring evidence is preserved read-only but is not treated as a binding.');
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
  L.push('summary.json', 'analysis_history.json', 'evaluation_anchors.json', 'frames.csv', 'markers.csv', 'user_segments.csv', 'detected_segments.csv', '');
  if (state.scoringEvidenceContext && ((state.scoringEvidenceContext.boundSets||[]).length || (state.scoringEvidenceContext.conflictSets||[]).length || (state.scoringEvidenceContext.legacyCandidateSets||[]).length)) L.push('evaluation/scoring_evidence_relations.json');
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
    const binaryAsset=await dbGet('audio',rec.recordingId).catch(()=>null);
    // Legacy fields stay read-only in the audio row; export consumers use scoringEvidenceSets.
    state.legacyScoringEvidenceMigration=binaryAsset&&binaryAsset.legacyScoringEvidenceMigration||null;
    state.scoringEvidenceContext=await scoringEvidenceRelationsForRecording(rec.recordingId);
    state.scoringEvidenceCandidates=state.scoringEvidenceContext.legacyCandidateSets||[];

    files.push({ name: 'report.md', data: buildReportMd(an) });
    files.push({ name: 'summary.json', data: JSON.stringify(buildSummaryJson(an), null, 2) });
    files.push({ name: 'analysis_history.json', data: JSON.stringify({
      schemaVersion: SCHEMA_VERSION,
      recordingId: rec.recordingId,
      audioSha256: rec.audioSha256 || (an && an.audioSha256) || null,
      latestAnalysisId: rec.latestAnalysisId || (an && an.analysisId) || null,
      analyses: analysisHistory
    }, null, 2) });
    files.push({name:'evaluation_anchors.json',data:JSON.stringify(buildUnifiedRecordingEvaluationAnchors(rec,state.scoringEvidenceContext),null,2)});
    const scoringCtx=state.scoringEvidenceContext||{boundSets:[],conflictSets:[],legacyCandidateSets:[],bindingStates:new Map(),assertions:[]};
    const relationSetMap=new Map();
    for (const set of [...(scoringCtx.boundSets||[]),...(scoringCtx.conflictSets||[]),...(scoringCtx.legacyCandidateSets||[])]) {
      if (set&&set.evidenceSetId) relationSetMap.set(set.evidenceSetId,set);
    }
    const relationSets=Array.from(relationSetMap.values());
    if (relationSets.length) {
      files.push({name:'evaluation/scoring_evidence_relations.json',data:JSON.stringify({
        schemaVersion:'songscope-recording-scoring-evidence-relations-v2',
        recordingId:rec.recordingId,
        current:recordingScoringEvidenceDescriptor(rec,scoringCtx),
        bindingAssertions:(scoringCtx.assertions||[]).filter(x=>x&&x.recordingId===rec.recordingId),
        policy:'Current binding state is derived from append-only bindingAssertions. Legacy attachment candidates are not bindings.'
      },null,2)});
      for (const set of relationSets) {
        const bs=scoringCtx.bindingStates instanceof Map?scoringCtx.bindingStates.get(set.evidenceSetId):null;
        const root=`evaluation/relations/${set.evidenceSetId}`;
        files.push({name:`${root}/evidence_set.json`,data:JSON.stringify(standaloneEvidenceSetPublic(set,bs),null,2)});
        const cand=legacyCandidateForRecording(set,rec.recordingId);
        if (cand) files.push({name:`${root}/legacy_attachment_candidate.json`,data:JSON.stringify(legacyCandidatePublic(cand),null,2)});
        const setAssertions=(scoringCtx.assertions||[]).filter(x=>x&&x.evidenceSetId===set.evidenceSetId).sort((a,b)=>bindingAssertionSortKey(a).localeCompare(bindingAssertionSortKey(b)));
        files.push({name:`${root}/binding_assertions.json`,data:JSON.stringify({currentState:bs||null,assertions:setAssertions},null,2)});
        if (set.structuredScoringResult) {
          files.push({name:`${root}/structured_scoring_result.json`,data:JSON.stringify(structuredEvaluationDocument(set.structuredScoringResult),null,2)});
        }
        for (let i=0;i<(set.images||[]).length;i++) {
          const x=set.images[i];
          if (!x||!x.blob) continue;
          const ab=await x.blob.arrayBuffer();
          const got=(await sha256Hex(ab)).toLowerCase();
          if (got!==String(x.meta&&x.meta.sha256||'').toLowerCase()) throw new Error(`relation ${set.evidenceSetId} image SHA mismatch`);
          files.push({name:`${root}/images/${String(i+1).padStart(2,'0')}_${x.imageId}${imageExtFromMeta(x.meta)}`,data:new Uint8Array(ab)});
        }
      }
    }
    files.push({ name: 'markers.csv', data: markersCsv() });
    files.push({ name: 'user_segments.csv', data: userSegmentsCsv() });
    files.push({ name: 'detected_segments.csv', data: detectedSegmentsCsv(an) });
    if (an) files.push({ name: 'frames.csv', data: framesCsv(an) });

    for (const p of pngs) files.push({ name: p.name, data: new Uint8Array(await p.blob.arrayBuffer()) });

    if ($('#chk-include-audio').checked) {
      $('#busy-msg').textContent = '元音声を追加しています…';
      const a = binaryAsset || await dbGet('audio', rec.recordingId);
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


/* ---------------- G0b03: 録音から独立したDAMデンモク採点証拠 ---------------- */
const LEGACY_SCORING_SOURCE_KEY='legacy_recording_attachment_unclassified';
async function scoringEvidenceSetIdForSource(images, sourceKey) {
  const shas=(images||[]).map(x=>x&&x.meta&&x.meta.sha256).filter(Boolean).map(x=>String(x).toLowerCase()).sort();
  if (!shas.length) throw new Error('採点証拠画像のSHA-256がありません');
  const bytes=new TextEncoder().encode(String(sourceKey||'unknown')+':'+shas.join(':'));
  const h=await sha256Hex(bytes.buffer);
  return 'evs_'+h.slice(0,24);
}
async function standaloneEvidenceSetId(images) {
  return scoringEvidenceSetIdForSource(images,'dam_denmoku');
}
function scoringEvidenceSourceKey(set) {
  return String(set&&set.source&&set.source.sourceKey||'unknown');
}
function standaloneSourceSupportedForG0(set) {
  return scoringEvidenceSourceKey(set)==='dam_denmoku';
}

const BINDING_ASSERTION_SCHEMA='songscope-binding-assertion-v1';
function bindingAssertionSortKey(x) {
  return `${String(x&&x.assertedAt||'')}\n${String(x&&x.assertionId||'')}`;
}
function deriveBindingStateFromAssertions(evidenceSetId,assertions) {
  const rows=(assertions||[])
    .filter(x=>x&&x.evidenceSetId===evidenceSetId&&(x.action==='bind'||x.action==='unbind')&&(x.audioSha256||x.recordingId))
    .slice().sort((a,b)=>bindingAssertionSortKey(a).localeCompare(bindingAssertionSortKey(b)));
  const latestByAudioIdentity=new Map();
  for (const x of rows) {
    const target=x.audioSha256?`sha256:${String(x.audioSha256).toLowerCase()}`:`legacy_recording_id:${x.recordingId}`;
    latestByAudioIdentity.set(target,x);
  }
  const active=Array.from(latestByAudioIdentity.values()).filter(x=>x.action==='bind');
  let status='unbound';
  if (active.length===1) status='bound';
  else if (active.length>1) status='binding_conflict';
  return {
    schemaVersion:'songscope-derived-binding-state-v2',
    evidenceSetId,
    status,
    recordingId:active.length===1?active[0].recordingId:null,
    audioSha256:active.length===1?(active[0].audioSha256||null):null,
    activeRecordingIds:active.map(x=>x.recordingId).filter(Boolean).sort(),
    activeAudioSha256s:Array.from(new Set(active.map(x=>x.audioSha256&&String(x.audioSha256).toLowerCase()).filter(Boolean))).sort(),
    activeAssertions:active.map(x=>({
      assertionId:x.assertionId,recordingId:x.recordingId,audioSha256:x.audioSha256||null,assertedAt:x.assertedAt,
      source:x.source||null,basisShownToUser:x.basisShownToUser||[]
    })),
    assertionCount:rows.length,
    derivedAt:nowIso(),
    targetIdentity:'raw_audio_sha256',
    source:'bindingAssertions_append_only'
  };
}
async function allBindingAssertions() {
  return dbAll('bindingAssertions').catch(()=>[]);
}
async function bindingStateForEvidenceSet(evidenceSetId) {
  return deriveBindingStateFromAssertions(evidenceSetId,await allBindingAssertions());
}
function bindingStateMapFromAssertions(assertions,sets) {
  const m=new Map();
  for (const set of (sets||[])) m.set(set.evidenceSetId,deriveBindingStateFromAssertions(set.evidenceSetId,assertions||[]));
  return m;
}
async function loadBindingStateMap(sets) {
  return bindingStateMapFromAssertions(await allBindingAssertions(),sets||[]);
}
function bindingStateLabel(state) {
  if (!state) return 'unknown';
  if (state.status==='bound') return `bound → ${state.recordingId}`;
  if (state.status==='binding_conflict') return `CONFLICT → ${state.activeRecordingIds.join(', ')}`;
  return 'unbound';
}
function activeBindAssertionForAudioSha(state,audioSha256) {
  const sha=String(audioSha256||'').toLowerCase();
  return state&&Array.isArray(state.activeAssertions)?state.activeAssertions.find(x=>String(x.audioSha256||'').toLowerCase()===sha)||null:null;
}
function activeBindAssertionForRecording(state,recordingId) {
  return state&&Array.isArray(state.activeAssertions)?state.activeAssertions.find(x=>x.recordingId===recordingId)||null:null;
}
async function appendBindingAssertion({evidenceSetId,recordingId,action,basisShownToUser,supersedesAssertionId,reason}) {
  if (!evidenceSetId||!recordingId) throw new Error('Binding assertionのevidenceSetId/recordingIdが不足しています');
  if (action!=='bind'&&action!=='unbind') throw new Error('Binding assertion actionが不正です');
  const set=await dbGet('scoringEvidenceSets',evidenceSetId);
  const rec=await dbGet('recordings',recordingId);
  if (!set) throw new Error('採点証拠セットが見つかりません');
  if (!rec) throw new Error('録音が見つかりません');
  const audioSha256=String(rec.audioSha256||'').toLowerCase();
  if (!audioSha256) throw new Error('この録音はraw audio SHA-256を確認できないためBinding対象にできません');
  const assertion={
    schemaVersion:BINDING_ASSERTION_SCHEMA,
    assertionId:uid('bnd'),
    evidenceSetId,
    recordingId,
    audioSha256,
    targetIdentity:'raw_audio_sha256',
    action,
    assertedAt:nowIso(),
    source:'user_explicit_confirmation',
    reason:reason||null,
    basisShownToUser:Array.isArray(basisShownToUser)?basisShownToUser:[],
    supersedesAssertionId:supersedesAssertionId||null,
    appVersion:APP_VERSION,
    buildId:BUILD_ID
  };
  await dbPut('bindingAssertions',assertion);
  return assertion;
}
function bindingComparableText(v) {
  return normalizeSongIdentityText(v||'');
}
function bindingTitleLooseMatch(a,b) {
  const x=bindingComparableText(a),y=bindingComparableText(b);
  if (!x||!y||x===y) return false;
  const strip=s=>s.replace(/[\s　]*(?:take|テイク)?[\s　]*[a-z0-9０-９]+$/iu,'').trim();
  const sx=strip(x),sy=strip(y);
  return !!sx&&sx===sy;
}
function bindingCandidateBasis(set,rec) {
  const sd=standaloneStructuredDescriptor(set);
  const reviewed=!!(sd&&sd.userReview&&(sd.userReview.status==='user_confirmed'||sd.userReview.status==='user_confirmed_with_known_gaps'));
  const eligibleForSuggestion=!!(sd&&sd.status==='available'&&sd.schemaCurrent&&sd.verification&&sd.verification.status==='source_verified'&&reviewed);
  const result=eligibleForSuggestion?(sd.result||{}):{};
  const basis=[];
  let rankScore=0;
  const rt=bindingComparableText(result.title),rrt=bindingComparableText(rec&&rec.title);
  if (rt&&rrt&&rt===rrt) {
    rankScore+=60; basis.push({key:'song_title_exact',detail:`${result.title} = ${rec.title}`,agreed:true,source:'displayed_scoring_result_vs_recording_metadata'});
  } else if (result.title&&rec&&rec.title&&bindingTitleLooseMatch(result.title,rec.title)) {
    rankScore+=20; basis.push({key:'song_title_loose_candidate',detail:`${result.title} ↔ ${rec.title}`,agreed:true,source:'candidate_ordering_only'});
  }
  const ra=bindingComparableText(result.artist),rra=bindingComparableText(rec&&rec.artist);
  if (ra&&rra&&ra===rra) {
    rankScore+=25; basis.push({key:'artist_exact',detail:`${result.artist} = ${rec.artist}`,agreed:true,source:'displayed_scoring_result_vs_recording_metadata'});
  }
  const score=Number(result.overallScore),manual=Number(rec&&rec.damScore);
  if (isFinite(score)&&isFinite(manual)&&Math.abs(score-manual)<=0.001) {
    const prov=normalizedMetadataProvenance(rec||{}).damScore||{};
    rankScore+=70; basis.push({key:'overall_score_exact',detail:`${score.toFixed(3)} = ${manual.toFixed(3)}`,agreed:true,source:'scoring_result_vs_recording_metadata',recordingMetadataConfirmation:prov.confirmation||'unknown'});
  }
  const sm=bindingComparableText(result.scoringMode),rsm=bindingComparableText(rec&&rec.scoringMode);
  if (sm&&rsm&&sm===rsm) {
    rankScore+=15; basis.push({key:'scoring_mode_exact',detail:`${result.scoringMode}`,agreed:true,source:'scoring_result_vs_recording_metadata'});
  }
  const recordedProv=normalizedMetadataProvenance(rec||{}).recordedAt||{};
  if (rec&&rec.recordedAt) {
    basis.push({
      key:'recorded_at_context_only',
      detail:`recordedAt ${rec.recordedAt}`,
      agreed:null,
      source:'recording_metadata',
      confirmation:recordedProv.confirmation||'unknown',
      bindingUse:'display_only_not_ranked'
    });
  }
  if (result.scoringPerformedAt&&result.scoringPerformedAt.localDateTime) {
    basis.push({
      key:'scoring_performed_at_context_only',
      detail:`DAM local ${result.scoringPerformedAt.localDateTime}`,
      agreed:null,
      source:'displayed_by_dam_denmoku',
      timeZone:result.scoringPerformedAt.timeZone??null,
      bindingUse:'display_only_not_ranked_until_timezone_context_confirmed'
    });
  }
  return {rankScore,basis};
}
function bindingRecordingDisplay(rec) {
  return {
    recordingId:rec.recordingId,
    title:rec.title||'',
    artist:rec.artist||'',
    damScore:rec.damScore||null,
    scoringMode:rec.scoringMode||null,
    recordedAt:rec.recordedAt||null,
    fileName:rec.fileName||null
  };
}
async function bindingCandidateRows(set,query) {
  const recs=await dbAll('recordings').catch(()=>[]);
  const q=bindingComparableText(query||'');
  const bySha=new Map();
  for (const rec of recs) {
    if (!rec||!rec.recordingId||!rec.audioSha256) continue;
    const {rankScore,basis}=bindingCandidateBasis(set,rec);
    const hay=bindingComparableText([rec.title,rec.artist,rec.fileName,rec.damScore,rec.recordingId,rec.audioSha256].filter(Boolean).join(' '));
    if (q && !hay.includes(q)) continue;
    if (!q && rankScore<=0) continue;
    const sha=String(rec.audioSha256).toLowerCase();
    const row={rec,rankScore,basis,aliasRecordingIds:[]};
    if (!bySha.has(sha)) bySha.set(sha,row);
    else {
      const cur=bySha.get(sha);
      cur.aliasRecordingIds.push(rec.recordingId);
      if (rankScore>cur.rankScore) {
        row.aliasRecordingIds=[cur.rec.recordingId,...cur.aliasRecordingIds];
        bySha.set(sha,row);
      }
    }
  }
  const rows=Array.from(bySha.values());
  rows.sort((a,b)=>b.rankScore-a.rankScore||String(b.rec.updatedAt||'').localeCompare(String(a.rec.updatedAt||'')));
  return rows.slice(0,q?20:3);
}
async function scoringEvidenceRelationsForRecording(recordingId) {
  const sets=await dbAll('scoringEvidenceSets').catch(()=>[]);
  const assertions=await allBindingAssertions();
  const states=bindingStateMapFromAssertions(assertions,sets);
  const rec=await dbGet('recordings',recordingId).catch(()=>null);
  const recSha=String(rec&&rec.audioSha256||'').toLowerCase();
  const boundSets=[];
  const conflictSets=[];
  const legacyCandidateSets=[];
  for (const set of sets) {
    const st=states.get(set.evidenceSetId);
    if (st&&st.status==='bound'&&recSha&&String(st.audioSha256||'').toLowerCase()===recSha) boundSets.push(set);
    if (st&&st.status==='binding_conflict'&&recSha&&st.activeAudioSha256s.includes(recSha)) conflictSets.push(set);
    if (legacyCandidateForRecording(set,recordingId)) legacyCandidateSets.push(set);
  }
  return {recordingId,audioSha256:recSha||null,allSets:sets,assertions,bindingStates:states,boundSets,conflictSets,legacyCandidateSets};
}
function legacyAttachmentCandidates(set) {
  return Array.isArray(set&&set.legacyAttachmentCandidates) ? set.legacyAttachmentCandidates.filter(x=>x&&x.recordingId) : [];
}
function legacyCandidateForRecording(set,recordingId) {
  return legacyAttachmentCandidates(set).find(x=>x.recordingId===recordingId)||null;
}
async function scoringEvidenceSetsForLegacyCandidateRecording(recordingId) {
  if (!recordingId) return [];
  const all=await dbAll('scoringEvidenceSets').catch(()=>[]);
  return all.filter(set=>!!legacyCandidateForRecording(set,recordingId));
}
function legacyStructuredVerificationSnapshot(rec,images,stored) {
  const doc=structuredEvaluationDocument(stored);
  if (!doc) return {status:'unavailable',recordingIdMatch:false,sourceEvidenceMatch:false};
  const recordingIdMatch=!!(rec&&rec.recordingId&&doc.recordingId===rec.recordingId);
  const currentShas=evidenceSetShaList(images);
  const sourceSha=doc.sourceEvidence&&doc.sourceEvidence.sha256?String(doc.sourceEvidence.sha256).toLowerCase():null;
  const sourceShas=doc.sourceEvidence&&Array.isArray(doc.sourceEvidence.images)
    ? doc.sourceEvidence.images.map(x=>String(x&&x.sha256||'').toLowerCase()).filter(Boolean)
    : (sourceSha?[sourceSha]:[]);
  const sourceEvidenceMatch=sameStringSet(sourceShas,currentShas);
  return {
    status:recordingIdMatch&&currentShas.length&&sourceEvidenceMatch?'source_verified_under_legacy_schema':'legacy_source_mismatch',
    recordingIdMatch,sourceEvidenceMatch,currentImageSha256s:currentShas,
    sourceImageSha256s:sourceShas,checkedAt:nowIso()
  };
}
async function verifyLegacyScoringImageBytes(images) {
  for (let i=0;i<(images||[]).length;i++) {
    const x=images[i];
    if (!x||!x.blob||typeof x.blob.arrayBuffer!=='function'||!x.meta||!x.meta.sha256) throw new Error(`legacy image ${i+1}: raw bytesまたはSHA-256がありません`);
    const ab=await x.blob.arrayBuffer();
    const bytes=new Uint8Array(ab);
    const expectedSize=Number(x.meta.fileSize);
    if (Number.isFinite(expectedSize)&&expectedSize>=0&&bytes.byteLength!==expectedSize) throw new Error(`legacy image ${i+1}: size mismatch`);
    const got=(await sha256Hex(ab)).toLowerCase();
    if (got!==String(x.meta.sha256).toLowerCase()) throw new Error(`legacy image ${i+1}: SHA-256 mismatch`);
  }
  return true;
}
function legacyCandidatePublic(x) {
  if (!x) return null;
  const ls=x.legacyStructuredScoringResult;
  return {
    recordingId:x.recordingId||null,
    relationshipStatus:x.relationshipStatus||'legacy_attachment_candidate_unbound',
    relationshipBasis:x.relationshipBasis||null,
    legacyAttachedAt:x.legacyAttachedAt||null,
    migratedAt:x.migratedAt||null,
    rawImageVerification:x.rawImageVerification||null,
    sourceClassification:x.sourceClassification||LEGACY_SCORING_SOURCE_KEY,
    legacyStructured:{
      present:!!(ls&&ls.document),
      schemaVersion:ls&&ls.document&&ls.document.schemaVersion||null,
      sourceVerificationAtMigration:ls&&ls.sourceVerificationAtMigration||null,
      originalImportMeta:ls&&ls.importMeta||null
    },
    warning:'This records only that older SongScope UI stored this scoring evidence inside the recording row. It is NOT confirmation that the scoring result and audio are the same performance.'
  };
}
async function migrateLegacyRecordingAttachedScoringEvidence() {
  const recs=await dbAll('recordings').catch(()=>[]);
  const recById=new Map(recs.map(r=>[r.recordingId,r]));
  const assets=await dbAll('audio').catch(()=>[]);
  const summary={examined:0,migrated:0,alreadyMigrated:0,blocked:0,createdSets:0,mergedSets:0};
  for (const asset of assets) {
    const images=normalizeEvaluationEvidenceImages(asset);
    if (!images.length) continue;
    summary.examined++;
    const rec=recById.get(asset.recordingId);
    if (!rec) {
      asset.legacyScoringEvidenceMigration={status:'blocked_recording_missing',updatedAt:nowIso(),buildId:BUILD_ID};
      await dbPut('audio',asset).catch(()=>{});
      summary.blocked++;
      continue;
    }
    try {
      await verifyLegacyScoringImageBytes(images);
      // The pre-G0 direct-attachment UI did not reliably distinguish DAMデンモク screenshots
      // from other scoring screens. Do not relabel these legacy bytes as dam_denmoku.
      const sourceKey=LEGACY_SCORING_SOURCE_KEY;
      const evidenceSetId=await scoringEvidenceSetIdForSource(images,sourceKey);
      let set=await dbGet('scoringEvidenceSets',evidenceSetId).catch(()=>null);
      const existed=!!set;
      if (!set) {
        set={
          evidenceSetId,
          schemaVersion:'songscope-scoring-evidence-set-v1',
          source:{provider:'DAM_or_unknown_legacy',application:null,sourceKey},
          bindingStatus:'unbound',boundRecordingId:null,lifecycleStatus:'active',
          createdAt:(images[0]&&images[0].meta&&images[0].meta.attachedAt)||asset.savedAt||rec.updatedAt||rec.createdAt||nowIso(),
          updatedAt:nowIso(),
          images:images.map((x,i)=>({
            imageId:x.imageId||('img_'+String(i+1).padStart(2,'0')),
            blob:x.blob,
            meta:Object.assign({},x.meta,{
              legacyOriginalSourceClaim:x.meta&&x.meta.source||null,
              source:sourceKey,
              migrationClassification:'source_unclassified_due_to_pre_g0_input_not_enforcing_source'
            })
          })),
          note:'Migrated non-destructively from the pre-G0 recording-attached scoring-evidence path. Source is intentionally unclassified and relationship to the recording is candidate-only, not a binding.',
          legacyAttachmentCandidates:[]
        };
        summary.createdSets++;
      } else summary.mergedSets++;
      if (!Array.isArray(set.legacyAttachmentCandidates)) set.legacyAttachmentCandidates=[];
      let candidate=legacyCandidateForRecording(set,rec.recordingId);
      if (!candidate) {
        const stored=asset.evaluationStructured||null;
        candidate={
          recordingId:rec.recordingId,
          relationshipStatus:'legacy_attachment_candidate_unbound',
          relationshipBasis:'pre_g0_recording_attached_ui_without_explicit_same_performance_confirmation',
          legacyAttachedAt:(images[0]&&images[0].meta&&images[0].meta.attachedAt)||null,
          migratedAt:nowIso(),
          rawImageVerification:'sha256_verified_at_migration',
          sourceClassification:sourceKey,
          legacyStructuredScoringResult:stored?{
            document:structuredEvaluationDocument(stored),
            importMeta:stored&&stored.importMeta||null,
            sourceVerificationAtMigration:legacyStructuredVerificationSnapshot(rec,images,stored)
          }:null
        };
        set.legacyAttachmentCandidates.push(candidate);
        summary.migrated++;
      } else summary.alreadyMigrated++;
      // Never promote the candidate to a binding.
      set.bindingStatus='unbound'; set.boundRecordingId=null; set.updatedAt=nowIso();
      await dbPut('scoringEvidenceSets',set);
      asset.legacyScoringEvidenceMigration={
        status:'migrated_candidate_only',
        evidenceSetId,sourceKey,
        relationshipStatus:'legacy_attachment_candidate_unbound',
        migratedAt:candidate&&candidate.migratedAt||nowIso(),
        buildId:BUILD_ID,
        note:'Legacy bytes remain in audio store for non-destructive rollback/audit. scoringEvidenceSets is authoritative for consumers from build10 onward.'
      };
      await dbPut('audio',asset);
    } catch(e) {
      asset.legacyScoringEvidenceMigration={status:'blocked_integrity_check_failed',error:(e&&e.message)||String(e),updatedAt:nowIso(),buildId:BUILD_ID};
      await dbPut('audio',asset).catch(()=>{});
      summary.blocked++;
    }
  }
  return summary;
}
function recordingScoringEvidenceDescriptor(rec,context) {
  const recordingId=rec&&rec.recordingId||null;
  const ctx=context&&typeof context==='object'&&!Array.isArray(context)
    ? context
    : {boundSets:[],conflictSets:[],legacyCandidateSets:Array.isArray(context)?context:[],bindingStates:new Map()};
  const boundSets=Array.isArray(ctx.boundSets)?ctx.boundSets:[];
  const conflictSets=Array.isArray(ctx.conflictSets)?ctx.conflictSets:[];
  const legacySets=Array.isArray(ctx.legacyCandidateSets)?ctx.legacyCandidateSets:[];
  const states=ctx.bindingStates instanceof Map?ctx.bindingStates:new Map();
  const legacyCandidates=legacySets.map(set=>({
    evidenceSet:standaloneEvidenceSetPublic(set,states.get(set.evidenceSetId)),
    relationship:legacyCandidatePublic(legacyCandidateForRecording(set,recordingId))
  }));
  const boundRelationships=boundSets.map(set=>({
    evidenceSet:standaloneEvidenceSetPublic(set,states.get(set.evidenceSetId)),
    relationship:{
      status:'bound_user_confirmed',
      evidenceSetId:set.evidenceSetId,
      recordingId,
      assertion:activeBindAssertionForAudioSha(states.get(set.evidenceSetId),rec&&rec.audioSha256),
      explicitBindingConfirmed:true
    }
  }));
  if (conflictSets.length) {
    return {
      status:'binding_conflict',
      recordingId,
      boundEvidenceSetCount:boundSets.length,
      conflictEvidenceSetCount:conflictSets.length,
      legacyCandidateCount:legacySets.length,
      boundRelationships,
      conflictEvidenceSets:conflictSets.map(set=>standaloneEvidenceSetPublic(set,states.get(set.evidenceSetId))),
      legacyCandidates,
      structuredScoringResult:{status:'unavailable',verification:{status:'binding_conflict'},result:null},
      policy:{explicitBindingRequired:true,conflictsBlockOutcomeUse:true,legacyAttachmentIsNotBinding:true}
    };
  }
  if (boundSets.length>1) {
    return {
      status:'ambiguous_multiple_bound_scoring_evidence_sets',
      recordingId,
      boundEvidenceSetCount:boundSets.length,
      legacyCandidateCount:legacySets.length,
      boundRelationships,legacyCandidates,
      structuredScoringResult:{
        status:'unavailable',
        verification:{status:'multiple_bound_evidence_sets_for_one_recording'},
        result:null,
        note:'Multiple independently identified scoring evidence sets are explicitly bound to this recording. SongScope does not assume they are duplicates of the same scoring result.'
      },
      policy:{explicitBindingRequired:true,multipleBoundSetsBlockOutcomeUse:true,legacyAttachmentIsNotBinding:true}
    };
  }
  if (boundSets.length===1) {
    const set=boundSets[0];
    const bs=states.get(set.evidenceSetId);
    const sd=standaloneStructuredDescriptor(set);
    const eligibleSource=standaloneSourceSupportedForG0(set);
    const sourceVerified=sd.status==='available'&&sd.verification&&sd.verification.status==='source_verified';
    const schemaCurrent=!!sd.schemaCurrent;
    const reviewed=!!(sd.userReview&&(sd.userReview.status==='user_confirmed'||sd.userReview.status==='user_confirmed_with_known_gaps'));
    const doc=structuredEvaluationDocument(set.structuredScoringResult);
    return {
      status:'bound_user_confirmed',
      recordingId,
      boundEvidenceSetCount:1,
      legacyCandidateCount:legacySets.length,
      boundRelationships,legacyCandidates,
      structuredScoringResult:{
        status:doc?'available':'unavailable',
        schemaVersion:doc&&doc.schemaVersion||null,
        sourceEvidence:doc&&doc.sourceEvidence||null,
        extraction:doc&&doc.extraction||null,
        fieldStatus:doc&&doc.fieldStatus||null,
        result:doc&&doc.result||null,
        verification:{
          status:eligibleSource&&sourceVerified&&schemaCurrent?'source_verified':'bound_but_not_eligible_source_verified_result',
          sourceVerification:sd.verification&&sd.verification.status||'unavailable',
          schemaCurrent,
          sourceSupportedForG0:eligibleSource
        },
        relationship:{
          status:'bound_user_confirmed',
          evidenceSetId:set.evidenceSetId,
          recordingId,
          bindingState:bs?{status:bs.status,assertionCount:bs.assertionCount}:null,
          activeBindAssertion:activeBindAssertionForAudioSha(bs,rec&&rec.audioSha256),
          explicitBindingConfirmed:true
        },
        userReview:sd.userReview||null,
        outcomeEligibility:{
          eligible:!!(eligibleSource&&sourceVerified&&schemaCurrent&&reviewed),
          requires:['explicit_user_binding','dam_denmoku_source','source_verified_structured_result','current_schema','user_review'],
          userReviewSatisfied:reviewed,
          note:'Binding proves only the user-confirmed same-performance relationship. It does not by itself certify extraction correctness or scoring-condition comparability.'
        }
      },
      policy:{explicitBindingRequired:true,legacyAttachmentIsNotBinding:true}
    };
  }

  if (legacySets.length) {
    const set=legacySets.length===1?legacySets[0]:null;
    const candidate=set?legacyCandidateForRecording(set,recordingId):null;
    return {
      status:legacySets.length===1?'legacy_attachment_candidate_unbound':'ambiguous_multiple_legacy_candidates',
      recordingId,
      boundEvidenceSetCount:0,
      legacyCandidateCount:legacySets.length,
      boundRelationships:[],
      legacyCandidates,
      structuredScoringResult:{
        status:candidate&&candidate.legacyStructuredScoringResult&&candidate.legacyStructuredScoringResult.document?'available':'unavailable',
        schemaVersion:candidate&&candidate.legacyStructuredScoringResult&&candidate.legacyStructuredScoringResult.document&&candidate.legacyStructuredScoringResult.document.schemaVersion||null,
        sourceEvidence:candidate&&candidate.legacyStructuredScoringResult&&candidate.legacyStructuredScoringResult.document&&candidate.legacyStructuredScoringResult.document.sourceEvidence||null,
        extraction:candidate&&candidate.legacyStructuredScoringResult&&candidate.legacyStructuredScoringResult.document&&candidate.legacyStructuredScoringResult.document.extraction||null,
        result:candidate&&candidate.legacyStructuredScoringResult&&candidate.legacyStructuredScoringResult.document&&candidate.legacyStructuredScoringResult.document.result||null,
        verification:{
          status:legacySets.length===1?'legacy_attachment_candidate_unbound':'legacy_attachment_candidate_conflict_multiple_sets',
          sourceVerificationBeforeRelationshipCheck:candidate&&candidate.legacyStructuredScoringResult&&candidate.legacyStructuredScoringResult.sourceVerificationAtMigration&&candidate.legacyStructuredScoringResult.sourceVerificationAtMigration.status||'unavailable'
        },
        relationship:{
          status:'legacy_attachment_candidate_unbound',
          evidenceSetId:set&&set.evidenceSetId||null,
          recordingId,
          basis:candidate&&candidate.relationshipBasis||null,
          explicitBindingConfirmed:false
        },
        userReview:candidate&&candidate.legacyStructuredScoringResult&&candidate.legacyStructuredScoringResult.document&&candidate.legacyStructuredScoringResult.document.extraction&&candidate.legacyStructuredScoringResult.document.extraction.userReview||null,
        outcomeEligibility:{eligible:false,reason:'legacy_attachment_candidate_is_not_binding'}
      },
      policy:{explicitBindingRequired:true,legacyAttachmentIsNotBinding:true}
    };
  }
  return {
    status:'unavailable',
    recordingId,
    boundEvidenceSetCount:0,legacyCandidateCount:0,
    boundRelationships:[],legacyCandidates:[],
    structuredScoringResult:{status:'unavailable',verification:{status:'unavailable'},result:null},
    policy:{explicitBindingRequired:true,legacyAttachmentIsNotBinding:true}
  };
}
function buildUnifiedRecordingEvaluationAnchors(rec,context) {
  const prov=normalizedMetadataProvenance(rec||{});
  return {
    schemaVersion:'songscope-recording-scoring-evidence-relations-v2',
    recordingId:rec&&rec.recordingId||null,
    manualDamScore:{
      value:parseStoredScore(rec&&rec.damScore),
      rawStoredValue:rec&&rec.damScore||null,
      provenance:prov.damScore||{source:'absent',confirmation:'unknown'}
    },
    scoringEvidence:recordingScoringEvidenceDescriptor(rec,context),
    policy:{
      scoringEvidenceStoredIndependently:true,
      bindingStateDerivedOnlyFromAppendOnlyBindingAssertions:true,
      legacyStoredBindingFieldsAreNonAuthoritative:true,
      legacyAttachmentCandidateDoesNotEqualBinding:true,
      explicitBindingRequiredBeforePerformanceOutcomeUse:true
    }
  };
}
function standaloneLifecycleStatus(set) {
  return set && set.lifecycleStatus === 'archived' ? 'archived' : 'active';
}
function standaloneEvidenceSetPublic(set,bindingState) {
  if (!set) return null;
  const sourceKey=scoringEvidenceSourceKey(set);
  const bs=bindingState||null;
  return {
    schemaVersion:'songscope-scoring-evidence-set-v2',
    evidenceSetId:set.evidenceSetId,
    source:set.source,
    bindingState:bs?{
      status:bs.status,
      recordingId:bs.recordingId||null,
      audioSha256:bs.audioSha256||null,
      activeRecordingIds:bs.activeRecordingIds||[],
      activeAudioSha256s:bs.activeAudioSha256s||[],
      assertionCount:Number(bs.assertionCount||0),
      source:'bindingAssertions_append_only'
    }:{status:'not_computed',recordingId:null,activeRecordingIds:[],assertionCount:null,source:'bindingAssertions_not_loaded'},
    legacyStoredBindingFields:{
      bindingStatus:set.bindingStatus||null,
      boundRecordingId:set.boundRecordingId||null,
      authoritative:false,
      note:'Pre-build13 compatibility fields only; never use these to determine current binding.'
    },
    lifecycleStatus:standaloneLifecycleStatus(set),
    archivedAt:set.archivedAt||null,
    createdAt:set.createdAt,
    imageCount:(set.images||[]).length,
    images:(set.images||[]).map(x=>({imageId:x.imageId,meta:x.meta})),
    legacyAttachmentCandidates:legacyAttachmentCandidates(set).map(legacyCandidatePublic),
    interpretation:sourceKey==='dam_denmoku'
      ? 'A DAMデンモク scoring-history evidence set is independent primary evidence. Same-performance relationship is derived only from append-only user bindingAssertions.'
      : 'Legacy scoring image evidence migrated from the old recording-attached path. Source classification and same-performance relationship are intentionally NOT asserted unless a later explicit bindingAssertion exists.'
  };
}
function standaloneFieldStatusTemplate() {
  const out={};
  for (const key of STANDALONE_SCORING_FIELD_KEYS) out[key]=null;
  return out;
}
function standaloneResultTemplate() {
  return {
    title:null, artist:null, scoringMode:null,
    scoringPerformedAt:null,
    overallScore:null, personalBest:null, nationalAverage:null, ranking:null, heartType:null,
    pitchAccuracy:null, expressionScore:null, dynamicsScore:null, listeningScore:null,
    bonus:null, techniques:null, vibrato:null, longToneSkillDiscrete:null,
    vibratoSkillDiscrete:null, stabilityDiscrete:null, rhythmDiscrete:null,
    vocalRange:null, pitchGraphVisibleMarkers:null, analysisReportText:null
  };
}
function standaloneExtractionRequest(set,bindingState) {
  const pub=standaloneEvidenceSetPublic(set,bindingState);
  return {
    schemaVersion: 'songscope-evaluation-extraction-request-v5',
    evidenceSet: pub,
    requestedOutputSchema: STANDALONE_SCORING_RESULT_SCHEMA,
    requestedOutputTemplate: {
      schemaVersion: STANDALONE_SCORING_RESULT_SCHEMA,
      evidenceSetId: pub.evidenceSetId,
      sourceEvidence: {
        type: 'scoring_evidence_set',
        sourceApp: 'dam_denmoku',
        evidenceSetId: pub.evidenceSetId,
        images: pub.images.map(x => ({ imageId:x.imageId, sha256:x.meta && x.meta.sha256 || null }))
      },
      extraction: { extractedBy:null, extractedAt:null, notes:null },
      fieldStatus: standaloneFieldStatusTemplate(),
      result: standaloneResultTemplate()
    },
    fieldStatusPolicy: {
      requiredForEveryRequestedField: true,
      allowed: Array.from(STANDALONE_SCORING_FIELD_STATUSES),
      meanings: {
        extracted:'Value/state was explicitly visible and was transcribed into result.',
        not_visible_in_images:'The requested field is not visible in any supplied screenshot.',
        unreadable:'The field is visible but cannot be read reliably.',
        visible_not_extracted:'The field is visibly present but was intentionally or accidentally not structured; this is a known extraction gap.',
        not_applicable:'The field does not apply to this scoring mode/result.'
      }
    },
    bindingPolicy: {
      recordingBindingRequiredForPerformanceClaims: true,
      currentBindingStatus: pub.bindingState.status,
      doNotInventRecordingId: true,
      doNotAssumeTheseImagesBelongToAnyExistingRecording: true
    },
    extractionRules: [
      'Treat all images as DAMデンモク screenshots belonging to one scoring result.',
      'Return every sourceEvidence.images item with the supplied imageId AND its matching SHA-256. Do not swap imageId/SHA pairs.',
      'For every requested field, set exactly one fieldStatus value. Never use null alone to hide whether a field was absent, unreadable, or missed.',
      'Extract only explicitly readable text, numeric values, counts, discrete lit/unlit states, and visibly selected discrete positions.',
      'Discrete lit/unlit counts (for example 安定性, ロングトーンの上手さ, ビブラートの上手さ, リズム position) are countable observed states, not inferred hidden geometry. Store observed counts/positions without converting them to percentages or invented scores.',
      'Do not infer hidden numeric values from bars, radar charts, scales, or graphical geometry.',
      'If scoringPerformedAt is visible, store it as {localDateTime,timeZone,precision,source}. localDateTime is the displayed local clock value; timeZone must be null unless a time zone/offset is explicitly displayed. Never infer JST or an offset from context.',
      'Keep scoringPerformedAt separate from iPhone recordedAt.',
      'Separate overallScore from personalBest when both are visible.',
      'Preserve DAM analysis-report text as external-system text, not as SongScope diagnosis.',
      'Do not map pitch-graph x-position to audio seconds.',
      'Do not make cross-take judgments, causal claims, or practice recommendations.'
    ],
    requestedFields: standaloneFieldStatusTemplate()
  };
}
function standaloneCurrentImageBindings(set) {
  return (set && set.images || []).map(x => ({
    imageId:String(x && x.imageId || ''),
    sha256:String(x && x.meta && x.meta.sha256 || '').toLowerCase()
  })).filter(x=>x.imageId && x.sha256);
}
function standaloneDocImageBindings(doc) {
  return (doc && doc.sourceEvidence && Array.isArray(doc.sourceEvidence.images) ? doc.sourceEvidence.images : [])
    .map(x => ({imageId:String(x && x.imageId || ''),sha256:String(x && x.sha256 || '').toLowerCase()}))
    .filter(x=>x.imageId && x.sha256);
}
function imageBindingKey(x) { return String(x.imageId)+'\u0000'+String(x.sha256).toLowerCase(); }
function sameImageBindingSet(a,b) {
  const aa=(a||[]).map(imageBindingKey).sort();
  const bb=(b||[]).map(imageBindingKey).sort();
  return aa.length===bb.length && new Set(aa).size===aa.length && new Set(bb).size===bb.length && aa.every((x,i)=>x===bb[i]);
}
// compatibility helpers used in older exports/descriptors
function standaloneCurrentShaList(set) {
  return standaloneCurrentImageBindings(set).map(x=>x.sha256);
}
function standaloneDocShaList(doc) {
  return standaloneDocImageBindings(doc).map(x=>x.sha256);
}
function validateScoringPerformedAtObservation(value) {
  if (!value || typeof value!=='object' || Array.isArray(value)) throw new Error('scoringPerformedAtは構造化された観測日時である必要があります');
  const local=String(value.localDateTime||'');
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$/.test(local)) throw new Error('scoringPerformedAt.localDateTimeの形式が正しくありません');
  if (!['second','minute'].includes(String(value.precision||''))) throw new Error('scoringPerformedAt.precisionが未対応です');
  if (String(value.source||'')!=='displayed_by_dam_denmoku') throw new Error('scoringPerformedAt.sourceが正しくありません');
  if (value.timeZone !== null && value.timeZone !== undefined && typeof value.timeZone !== 'string') throw new Error('scoringPerformedAt.timeZoneの形式が正しくありません');
}
function validateStandaloneStructuredScoringResult(doc, set) {
  if (!doc || typeof doc !== 'object' || Array.isArray(doc)) throw new Error('構造化採点JSONの形式が正しくありません');
  if (doc.schemaVersion !== STANDALONE_SCORING_RESULT_SCHEMA) throw new Error('build08ではstructured scoring schema v2が必要です');
  if (!set || !set.evidenceSetId || doc.evidenceSetId !== set.evidenceSetId) throw new Error('この採点証拠セット用のJSONではありません');
  if (doc.recordingId) throw new Error('未紐付け採点結果にrecordingIdを含めることはできません');
  const src=doc.sourceEvidence;
  if (!src || src.type !== 'scoring_evidence_set' || src.evidenceSetId !== set.evidenceSetId) throw new Error('sourceEvidenceのevidenceSetIdが一致しません');
  if (src.sourceApp && src.sourceApp !== 'dam_denmoku') throw new Error('G0で対応するsourceはdam_denmokuのみです');
  const current=standaloneCurrentImageBindings(set);
  const supplied=standaloneDocImageBindings(doc);
  if (!current.length || !sameImageBindingSet(current,supplied)) throw new Error('元画像のimageId↔SHA-256対応が現在の採点証拠セットと一致しません');
  if (!doc.result || typeof doc.result !== 'object' || Array.isArray(doc.result)) throw new Error('構造化採点JSONにresultがありません');
  if (!doc.fieldStatus || typeof doc.fieldStatus!=='object' || Array.isArray(doc.fieldStatus)) throw new Error('fieldStatusがありません');
  const allowedKeys=new Set(STANDALONE_SCORING_FIELD_KEYS);
  for (const key of Object.keys(doc.result)) if (!allowedKeys.has(key)) throw new Error(`result.${key}はschema v2のrequested fieldではありません`);
  for (const key of Object.keys(doc.fieldStatus)) if (!allowedKeys.has(key)) throw new Error(`fieldStatus.${key}はschema v2のrequested fieldではありません`);
  for (const key of STANDALONE_SCORING_FIELD_KEYS) {
    if (!Object.prototype.hasOwnProperty.call(doc.fieldStatus,key)) throw new Error(`fieldStatus.${key}がありません`);
    const st=String(doc.fieldStatus[key]||'');
    if (!STANDALONE_SCORING_FIELD_STATUSES.has(st)) throw new Error(`fieldStatus.${key}が未対応です`);
    const value=doc.result[key];
    if (st==='extracted' && (value===null || value===undefined)) throw new Error(`${key}はextractedですがresultが空です`);
    if (st!=='extracted' && value!==null && value!==undefined) throw new Error(`${key}は${st}ですがresultに値があります`);
  }
  if (doc.fieldStatus.scoringPerformedAt==='extracted') validateScoringPerformedAtObservation(doc.result.scoringPerformedAt);
  return true;
}
function standaloneStructuredDescriptor(set) {
  const stored=set && set.structuredScoringResult;
  const doc=structuredEvaluationDocument(stored);
  if (!doc) return {status:'unavailable',verification:{status:'unavailable'},userReview:(set&&set.structuredScoringUserReview)||{status:'unreviewed'}};
  const evidenceSetIdMatch=doc.evidenceSetId===set.evidenceSetId && doc.sourceEvidence && doc.sourceEvidence.evidenceSetId===set.evidenceSetId;
  const sourceEvidenceMatch=sameImageBindingSet(standaloneCurrentImageBindings(set),standaloneDocImageBindings(doc));
  const sourceAppMatch=!doc.sourceEvidence || !doc.sourceEvidence.sourceApp || doc.sourceEvidence.sourceApp==='dam_denmoku';
  const verificationStatus=(evidenceSetIdMatch && sourceEvidenceMatch && sourceAppMatch) ? 'source_verified' : 'source_mismatch';
  const schemaCurrent=doc.schemaVersion===STANDALONE_SCORING_RESULT_SCHEMA;
  let review=(set&&set.structuredScoringUserReview)||{status:'unreviewed'};
  if (!schemaCurrent && review.status && review.status!=='unreviewed') review=Object.assign({},review,{legacyStatus:review.status,status:'legacy_review_needs_reverification'});
  const fs=doc.fieldStatus && typeof doc.fieldStatus==='object' ? doc.fieldStatus : null;
  const knownGapFields=fs ? STANDALONE_SCORING_FIELD_KEYS.filter(k=>fs[k]==='visible_not_extracted') : [];
  return {
    status:'available', schemaVersion:doc.schemaVersion||null, schemaCurrent,
    evidenceSetId:doc.evidenceSetId||null, sourceEvidence:doc.sourceEvidence||null,
    extraction:doc.extraction||null, fieldStatus:fs, result:doc.result||null,
    verification:{status:verificationStatus,evidenceSetIdMatch,sourceEvidenceMatch,sourceAppMatch,currentImageBindings:standaloneCurrentImageBindings(set)},
    userReview:review, knownGapFields, importMeta:stored&&stored.importMeta||null
  };
}
async function importStandaloneStructuredResult(evidenceSetId,file) {
  if (!file) return;
  if (file.size > 1024*1024) throw new Error('構造化採点JSONが大きすぎます（1MB以下）');
  const set=await dbGet('scoringEvidenceSets',evidenceSetId);
  if (!set) throw new Error('採点証拠セットが見つかりません');
  if (!standaloneSourceSupportedForG0(set)) throw new Error('この旧方式証拠はsource未分類のため、G0のDAMデンモク構造化対象にはできません');
  const buf=await file.arrayBuffer();
  const doc=JSON.parse(new TextDecoder('utf-8').decode(buf));
  validateStandaloneStructuredScoringResult(doc,set);
  if (set.structuredScoringResult && !confirm('既存の構造化採点結果を置き換えますか？')) return false;
  set.structuredScoringResult={document:doc,importMeta:{source:'external_json_import',fileName:file.name||'structured_scoring_result.json',fileSha256:await sha256Hex(buf),importedAt:nowIso(),appVersion:APP_VERSION,buildId:BUILD_ID}};
  // New external content must be reviewed again even if a previous result was user-confirmed.
  set.structuredScoringUserReview={status:'unreviewed',updatedAt:nowIso()};
  set.updatedAt=nowIso();
  await dbPut('scoringEvidenceSets',set);
  return true;
}
async function confirmStandaloneStructuredResult(evidenceSetId) {
  const set=await dbGet('scoringEvidenceSets',evidenceSetId);
  if (!set || !set.structuredScoringResult) throw new Error('先に構造化採点JSONを読み込んでください');
  const desc=standaloneStructuredDescriptor(set);
  if (desc.verification.status!=='source_verified') throw new Error('元画像とのsource verificationが通っていません');
  if (!desc.schemaCurrent || !desc.fieldStatus) throw new Error('schema v2で再抽出してから確認してください');
  const knownGapFields=STANDALONE_SCORING_FIELD_KEYS.filter(k=>desc.fieldStatus[k]==='visible_not_extracted');
  set.structuredScoringUserReview={
    status:knownGapFields.length?'user_confirmed_with_known_gaps':'user_confirmed',
    valueReviewStatus:'user_confirmed',
    coverageReviewStatus:knownGapFields.length?'known_visible_gaps':'no_known_visible_gaps',
    reviewedFieldCount:STANDALONE_SCORING_FIELD_KEYS.length,
    knownGapFields,
    confirmedAt:nowIso(),source:'explicit_user_review_after_field_by_field_display',
    appVersion:APP_VERSION,buildId:BUILD_ID
  };
  set.updatedAt=nowIso();
  await dbPut('scoringEvidenceSets',set);
}
async function importStandaloneScoringEvidence(files) {
  const arr=[];
  for (let i=0;i<files.length;i++) {
    const file=files[i];
    if (!file || !file.size) continue;
    const ab=await file.arrayBuffer();
    const sha=await sha256Hex(ab);
    if (arr.some(x=>x.meta.sha256===sha)) continue;
    arr.push({
      imageId:'img_'+String(arr.length+1).padStart(2,'0'),
      blob:file,
      meta:{sha256:sha,fileName:file.name||('dam_denmoku_'+(i+1)),mimeType:file.type||'image/png',fileSize:file.size,source:'dam_denmoku'}
    });
  }
  if (!arr.length) throw new Error('画像が選択されていません');
  const evidenceSetId=await standaloneEvidenceSetId(arr);
  const existing=await dbGet('scoringEvidenceSets',evidenceSetId).catch(()=>null);
  if (existing) return {set:existing, duplicate:true};
  const set={
    evidenceSetId,
    schemaVersion:'songscope-scoring-evidence-set-v1',
    source:{provider:'DAM',application:'DAMデンモク',sourceKey:'dam_denmoku'},
    bindingStatus:'unbound', boundRecordingId:null,
    lifecycleStatus:'active',
    createdAt:nowIso(), updatedAt:nowIso(), images:arr,
    note:'Imported independently from recordings. Explicit binding is required before treating this scoring result as the outcome of a recording.'
  };
  await dbPut('scoringEvidenceSets',set);
  return {set,duplicate:false};
}
let showArchivedScoringEvidence=false;
const STANDALONE_FIELD_LABELS={
  title:'曲名',artist:'歌手名',scoringMode:'採点モード',scoringPerformedAt:'DAM表示の採点日時',
  overallScore:'総合点',personalBest:'自己ベスト/最高点',nationalAverage:'全国平均',ranking:'順位',heartType:'Heartタイプ',
  pitchAccuracy:'音程正確率',expressionScore:'表現力',dynamicsScore:'抑揚',listeningScore:'聴感',
  bonus:'ボーナス',techniques:'テクニック',vibrato:'ビブラート',
  longToneSkillDiscrete:'ロングトーン上手さ',vibratoSkillDiscrete:'ビブラート上手さ',
  stabilityDiscrete:'安定性',rhythmDiscrete:'リズム',vocalRange:'声域',
  pitchGraphVisibleMarkers:'音程グラフ可視マーカー',analysisReportText:'DAM分析レポート'
};
const FIELD_STATUS_LABELS={
  extracted:'抽出済み',not_visible_in_images:'画像に表示なし',unreadable:'表示あり・判読不能',
  visible_not_extracted:'表示あり・未抽出',not_applicable:'対象外'
};
function standaloneReviewValueText(value) {
  if (value===null || value===undefined) return '—';
  if (typeof value==='string' || typeof value==='number' || typeof value==='boolean') return String(value);
  try { return JSON.stringify(value,null,2); } catch(e) { return String(value); }
}
let standaloneReviewImageUrls=[];
function clearStandaloneReviewImageUrls() {
  // build09: review images use short-lived data URLs rather than blob: URLs because
  // iPhone Safari can fail to render IndexedDB-restored Blob object URLs.
  standaloneReviewImageUrls=[];
  const box=$('#scoring-review-images'); if (box) box.innerHTML='';
}
function reviewImageMimeType(x) {
  const metaType=String(x&&x.meta&&x.meta.mimeType||'').toLowerCase();
  if (metaType.startsWith('image/')) return metaType;
  const name=String(x&&x.meta&&x.meta.fileName||'').toLowerCase();
  if (name.endsWith('.jpg') || name.endsWith('.jpeg')) return 'image/jpeg';
  if (name.endsWith('.webp')) return 'image/webp';
  return 'image/png';
}
function blobToDataUrl(blob) {
  return new Promise((resolve,reject)=>{
    const r=new FileReader();
    r.onload=()=>resolve(String(r.result||''));
    r.onerror=()=>reject(r.error||new Error('画像Data URLの生成に失敗しました'));
    r.readAsDataURL(blob);
  });
}
async function standaloneReviewImageDataUrl(x) {
  if (!x || !x.blob || typeof x.blob.arrayBuffer!=='function') throw new Error('raw image bytesがありません');
  const ab=await x.blob.arrayBuffer();
  const bytes=new Uint8Array(ab);
  const expectedSize=Number(x.meta&&x.meta.fileSize);
  if (Number.isFinite(expectedSize) && expectedSize>=0 && bytes.byteLength!==expectedSize) {
    throw new Error(`size mismatch: ${bytes.byteLength} != ${expectedSize}`);
  }
  const expectedSha=String(x.meta&&x.meta.sha256||'').toLowerCase();
  if (expectedSha) {
    const got=(await sha256Hex(ab)).toLowerCase();
    if (got!==expectedSha) throw new Error(`SHA-256 mismatch: ${got.slice(0,12)}…`);
  }
  const canonicalBlob=new Blob([bytes],{type:reviewImageMimeType(x)});
  return blobToDataUrl(canonicalBlob);
}
async function openStandaloneStructuredReview(evidenceSetId) {
  const set=await dbGet('scoringEvidenceSets',evidenceSetId);
  if (!set) throw new Error('採点証拠セットが見つかりません');
  const desc=standaloneStructuredDescriptor(set);
  if (desc.verification.status!=='source_verified') throw new Error('元画像とのsource verificationが通っていません');
  if (!desc.schemaCurrent || !desc.fieldStatus) throw new Error('この結果は旧schemaです。build08用JSONを読み込み直してください');
  clearStandaloneReviewImageUrls();
  const imageBox=$('#scoring-review-images');
  const imageErrors=[];
  for (const x of (set.images||[])) {
    if (!x) continue;
    const wrap=document.createElement('div'); wrap.className='scoring-review-image';
    const label=document.createElement('div'); label.className='small mono'; label.textContent=`${x.imageId} / ${String(x.meta&&x.meta.sha256||'').slice(0,12)}…`;
    wrap.appendChild(label);
    try {
      const dataUrl=await standaloneReviewImageDataUrl(x);
      const img=document.createElement('img');
      img.src=dataUrl; img.alt=`DAMデンモク証拠 ${x.imageId}`; img.loading='eager';
      wrap.appendChild(img);
    } catch(e) {
      imageErrors.push({imageId:x.imageId,error:(e&&e.message)||String(e)});
      const err=document.createElement('div'); err.className='scoring-review-image-error';
      err.textContent=`元画像を表示・検証できません: ${(e&&e.message)||String(e)}`;
      wrap.appendChild(err);
    }
    imageBox.appendChild(wrap);
  }
  const box=$('#scoring-review-fields');
  const gaps=[];
  box.innerHTML=STANDALONE_SCORING_FIELD_KEYS.map(key=>{
    const status=desc.fieldStatus[key];
    if (status==='visible_not_extracted') gaps.push(key);
    const value=desc.result ? desc.result[key] : null;
    const cls=status==='visible_not_extracted'?' review-gap':'';
    return `<div class="scoring-review-row${cls}"><div class="scoring-review-head"><b>${escapeHtml(STANDALONE_FIELD_LABELS[key]||key)}</b><span class="pill ${status==='extracted'?'ok':status==='visible_not_extracted'?'err':'wait'}">${escapeHtml(FIELD_STATUS_LABELS[status]||status)}</span></div><pre class="scoring-review-value">${escapeHtml(standaloneReviewValueText(value))}</pre></div>`;
  }).join('');
  if (imageErrors.length) {
    $('#scoring-review-summary').innerHTML=`<p class="small warn-text"><b>元画像${imageErrors.length}枚を表示・検証できません。</b>raw evidenceを見比べられないため内容確認は保存できません。</p>`;
  } else if (gaps.length) {
    $('#scoring-review-summary').innerHTML=`<p class="small warn-text"><b>未抽出の可視項目が${gaps.length}件あります。</b>確認しても「既知の未抽出あり」として保存されます。</p>`;
  } else {
    $('#scoring-review-summary').innerHTML='<p class="small"><b>全requested fieldの状態が明示されています。</b>下の一覧を確認してから確定してください。</p>';
  }
  const btn=$('#scoring-review-confirm');
  btn.dataset.evidenceSetId=evidenceSetId;
  btn.disabled=imageErrors.length>0;
  btn.textContent=imageErrors.length ? '元画像を確認できないため確定不可' : (gaps.length?'確認する（既知の未抽出あり）':'この抽出内容を確認する');
  openSheet('sheet-scoring-review');
}
const bindingUiState={evidenceSetId:null,query:''};
let bindingSearchTimer=null;
function bindingBasisLabel(row) {
  if (!row) return '';
  const labels={
    song_title_exact:'曲名一致',
    song_title_loose_candidate:'曲名が近い（候補順のみ）',
    artist_exact:'歌手名一致',
    overall_score_exact:'DAM点数一致',
    scoring_mode_exact:'採点モード一致',
    recorded_at_context_only:'録音日時（表示のみ）',
    scoring_performed_at_context_only:'DAM採点日時（TZ未確定・照合未使用）'
  };
  return labels[row.key]||row.key||'';
}
function bindingEvidenceSummaryHtml(set) {
  const sd=standaloneStructuredDescriptor(set);
  const r=sd&&sd.result||{};
  const score=isFinite(Number(r.overallScore))?Number(r.overallScore).toFixed(3):'—';
  const dt=r.scoringPerformedAt&&r.scoringPerformedAt.localDateTime?r.scoringPerformedAt.localDateTime:'—';
  const tz=r.scoringPerformedAt&&r.scoringPerformedAt.timeZone?r.scoringPerformedAt.timeZone:'未確定';
  return `<div class="binding-evidence-summary">
    <div><b>${escapeHtml(r.title||'(曲名未抽出)')}</b>${r.artist?`<span class="sub2">${escapeHtml(r.artist)}</span>`:''}</div>
    <div class="small">DAM ${escapeHtml(score)} ／ ${escapeHtml(r.scoringMode||'採点モード未抽出')}</div>
    <div class="small">採点日時: ${escapeHtml(dt)} ／ timezone: ${escapeHtml(tz)}</div>
    <div class="small mono">${escapeHtml(set.evidenceSetId)}</div>
  </div>`;
}
function bindingRecordingCardHtml(row,mode) {
  const rec=row.rec||row;
  const basis=row.basis||[];
  const prov=normalizedMetadataProvenance(rec||{});
  const score=rec.damScore!==null&&rec.damScore!==undefined&&String(rec.damScore)!==''?String(rec.damScore):'—';
  const modeText=rec.scoringMode||'—';
  const recorded=rec.recordedAt||'—';
  const reasonHtml=basis.length
    ? `<div class="binding-basis">${basis.map(x=>`<div><span class="pill">${escapeHtml(bindingBasisLabel(x))}</span> ${escapeHtml(x.detail||'')}</div>`).join('')}</div>`
    : '<div class="small">自動候補根拠なし。検索結果として表示。</div>';
  const action=mode==='active'
    ? `<button class="mini danger wide" data-binding-unbind="${escapeHtml(rec.recordingId)}">この対応を取り消す</button>`
    : `<button class="primary binding-confirm-btn" data-binding-bind="${escapeHtml(rec.recordingId)}">この録音で確定</button>`;
  return `<div class="binding-recording-card">
    <div class="binding-recording-title">${escapeHtml(rec.title||'(無題)')}</div>
    <div class="small">${escapeHtml(rec.artist||'')} ${rec.artist?'／ ':''}DAM ${escapeHtml(score)} ／ ${escapeHtml(modeText)}</div>
    <div class="small">recordedAt: ${escapeHtml(recorded)} <span class="sub">(${escapeHtml((prov.recordedAt&&prov.recordedAt.confirmation)||'unknown')})</span></div>
    <div class="small mono">${escapeHtml(rec.recordingId||'')}</div>
    <div class="small mono">audio SHA: ${escapeHtml(String(rec.audioSha256||'').slice(0,16))}…${row.aliasRecordingIds&&row.aliasRecordingIds.length?` ／ alias rows ${row.aliasRecordingIds.length}`:''}</div>
    ${reasonHtml}
    ${action}
  </div>`;
}
async function renderBindingSheet() {
  const evidenceSetId=bindingUiState.evidenceSetId;
  const set=await dbGet('scoringEvidenceSets',evidenceSetId);
  if (!set) throw new Error('採点証拠セットが見つかりません');
  const assertions=await allBindingAssertions();
  const bs=deriveBindingStateFromAssertions(evidenceSetId,assertions);
  const recs=await dbAll('recordings').catch(()=>[]);
  const recById=new Map(recs.map(r=>[r.recordingId,r]));
  const resolveAssertionRecording=(active)=>recById.get(active&&active.recordingId)||recs.find(r=>String(r&&r.audioSha256||'').toLowerCase()===String(active&&active.audioSha256||'').toLowerCase())||null;
  $('#binding-evidence-summary').innerHTML=bindingEvidenceSummaryHtml(set);
  const stateBox=$('#binding-current-state');
  if (bs.status==='bound') {
    const active=bs.activeAssertions[0];
    const rec=resolveAssertionRecording(active);
    stateBox.innerHTML=`<div class="note"><p><b>現在: この録音で確定済み</b></p><p class="small">この対応は確認履歴から導出されています。技術詳細はデータ管理・監査に保持します。</p></div>${rec?bindingRecordingCardHtml({rec,basis:active.basisShownToUser||[]},'active'):`<p class="small warn-text">Binding先recordingが見つかりません: ${escapeHtml(active.recordingId)}</p>`}`;
  } else if (bs.status==='binding_conflict') {
    stateBox.innerHTML=`<div class="note warn"><p><b>録音の対応を確認してください</b></p><p class="small">同じ採点結果に複数の録音が対応しています。正しくない方を取り消してください。</p></div>`+
      bs.activeAssertions.map(x=>{
        const rec=resolveAssertionRecording(x);
        return rec?bindingRecordingCardHtml({rec,basis:x.basisShownToUser||[]},'active'):`<p class="small">${escapeHtml(x.recordingId)}（録音なし）</p>`;
      }).join('');
  } else {
    stateBox.innerHTML='<div class="note"><p><b>現在: まだ録音を決めていません</b></p><p class="small">実際に同じ歌唱だったと自分で確認できる場合だけ選んでください。</p></div>';
  }
  const searchWrap=$('#binding-search-wrap');
  searchWrap.hidden=bs.status!=='unbound';
  const results=$('#binding-candidate-list');
  if (bs.status!=='unbound') {
    results.innerHTML='';
  } else {
    const rows=await bindingCandidateRows(set,bindingUiState.query);
    const title=bindingUiState.query?'検索結果':'録音候補（最大3件・自動確定なし）';
    results.innerHTML=`<div class="section-head tight"><span>${escapeHtml(title)}</span></div>`+
      (rows.length?rows.map(row=>bindingRecordingCardHtml(row,'candidate')).join(''):'<p class="small">候補がありません。曲名・録音名・DAM点数などで検索してください。</p>');
  }
  $('#binding-history').innerHTML=`<details class="details"><summary>対応履歴 ${bs.assertionCount}件</summary><pre class="binding-history-pre">${escapeHtml(JSON.stringify(assertions.filter(x=>x&&x.evidenceSetId===evidenceSetId).sort((a,b)=>bindingAssertionSortKey(a).localeCompare(bindingAssertionSortKey(b))),null,2))}</pre></details>`;
  $$('[data-binding-bind]').forEach(b=>b.addEventListener('click',()=>confirmBindingToRecording(b.dataset.bindingBind)));
  $$('[data-binding-unbind]').forEach(b=>b.addEventListener('click',()=>retractBindingFromRecording(b.dataset.bindingUnbind)));
}
async function openBindingSheet(evidenceSetId) {
  const set=await dbGet('scoringEvidenceSets',evidenceSetId);
  if (!set) throw new Error('採点証拠セットが見つかりません');
  bindingUiState.evidenceSetId=evidenceSetId;
  bindingUiState.query='';
  const input=$('#binding-search');
  if (input) input.value='';
  openSheet('sheet-binding');
  await renderBindingSheet();
}
async function confirmBindingToRecording(recordingId) {
  const evidenceSetId=bindingUiState.evidenceSetId;
  const set=await dbGet('scoringEvidenceSets',evidenceSetId);
  const rec=await dbGet('recordings',recordingId);
  if (!set||!rec) throw new Error('採点証拠または録音が見つかりません');
  const current=await bindingStateForEvidenceSet(evidenceSetId);
  if (current.status!=='unbound') throw new Error('Binding状態が変わりました。画面を更新してください');
  const {basis}=bindingCandidateBasis(set,rec);
  const recCtx=await scoringEvidenceRelationsForRecording(recordingId);
  const otherBound=(recCtx.boundSets||[]).filter(x=>x&&x.evidenceSetId!==evidenceSetId);
  const duplicateWarning=otherBound.length
    ? `\n\n注意: このraw audioには別の採点証拠 ${otherBound.length}件が既にBindingされています。追加するとSongScopeは重複/競合解決までOutcome利用を保留します。`
    : '';
  const ok=confirm(`この2つが「同じ1回の歌唱」だったと、あなた自身が確認できますか？\n\n採点証拠: ${set.evidenceSetId}\n録音: ${rec.title||'(無題)'}\n${rec.recordingId}\nraw audio SHA: ${String(rec.audioSha256||'').slice(0,24)}…${duplicateWarning}\n\n似ている・時刻が近いだけでは確定しないでください。`);
  if (!ok) return;
  const basisShownToUser=basis.concat([
    {key:'raw_audio_sha256_target',detail:String(rec.audioSha256||''),agreed:true,source:'SongScope raw audio identity'},
    {
    key:'user_explicit_same_performance_confirmation',
    detail:'User explicitly confirmed that this scoring evidence and recording refer to the same single singing performance.',
    agreed:true,source:'user'
  }]);
  await appendBindingAssertion({
    evidenceSetId,recordingId,action:'bind',basisShownToUser,
    reason:'user_explicit_same_performance_confirmation'
  });
  await renderBindingSheet();
  await renderStandaloneEvidenceSets();
  if (state.rec&&state.rec.recordingId===recordingId) {
    state.scoringEvidenceContext=await scoringEvidenceRelationsForRecording(recordingId);
    state.scoringEvidenceCandidates=state.scoringEvidenceContext.legacyCandidateSets||[];
    renderEvaluationAnchor();
  }
  toast('録音との対応を保存しました。');
}
async function retractBindingFromRecording(recordingId) {
  const evidenceSetId=bindingUiState.evidenceSetId;
  const current=await bindingStateForEvidenceSet(evidenceSetId);
  const rec=await dbGet('recordings',recordingId);
  if (!rec||!rec.audioSha256) throw new Error('撤回対象のraw audio identityを確認できません');
  const active=activeBindAssertionForAudioSha(current,rec.audioSha256);
  if (!active) throw new Error('撤回対象のactive Bindingが見つかりません');
  const ok=confirm(`この録音との対応を取り消しますか？\n\n${rec&&rec.title||recordingId}\n\n過去のbind記録は削除せず、unbind assertionを追記します。`);
  if (!ok) return;
  await appendBindingAssertion({
    evidenceSetId,recordingId,action:'unbind',
    basisShownToUser:[{key:'user_explicit_binding_retraction',detail:'User explicitly retracted the prior same-performance binding.',agreed:true,source:'user'}],
    supersedesAssertionId:active.assertionId,
    reason:'user_explicit_binding_retraction'
  });
  await renderBindingSheet();
  await renderStandaloneEvidenceSets();
  if (state.rec&&state.rec.recordingId===recordingId) {
    state.scoringEvidenceContext=await scoringEvidenceRelationsForRecording(recordingId);
    state.scoringEvidenceCandidates=state.scoringEvidenceContext.legacyCandidateSets||[];
    renderEvaluationAnchor();
  }
  toast('録音との対応を取り消しました。履歴は保持しています。');
}
async function archiveStandaloneEvidenceSet(id) {
  const set=await dbGet('scoringEvidenceSets',id);
  if (!set) return;
  if (!confirm(`この採点証拠セットをアーカイブしますか？\n画像${(set.images||[]).length}枚のraw bytesは削除せず保持します。`)) return;
  set.lifecycleStatus='archived'; set.archivedAt=nowIso(); set.updatedAt=nowIso();
  await dbPut('scoringEvidenceSets',set);
  await renderStandaloneEvidenceSets();
}
async function restoreStandaloneEvidenceSet(id) {
  const set=await dbGet('scoringEvidenceSets',id);
  if (!set) return;
  set.lifecycleStatus='active'; set.restoredAt=nowIso(); set.updatedAt=nowIso();
  await dbPut('scoringEvidenceSets',set);
  await renderStandaloneEvidenceSets();
}
async function renderStandaloneEvidenceSets() {
  const box=$('#scoring-evidence-list');
  if (!box) return;
  const all=(await dbAll('scoringEvidenceSets').catch(()=>[])).sort((a,b)=>String(b.createdAt||'').localeCompare(String(a.createdAt||'')));
  const archivedCount=all.filter(r=>standaloneLifecycleStatus(r)==='archived').length;
  const toggle=$('#btn-scoring-archive-toggle');
  if (toggle) {
    toggle.hidden=archivedCount===0;
    toggle.textContent=showArchivedScoringEvidence ? 'アーカイブ済みを隠す' : `アーカイブ済みを表示（${archivedCount}）`;
  }
  const rows=all.filter(r=>showArchivedScoringEvidence || standaloneLifecycleStatus(r)!=='archived');
  if (!rows.length) {
    box.innerHTML='<p class="small">表示する採点証拠はありません。</p>';
    await renderNormalWorkflowStatus().catch(()=>{});
    return;
  }
  const bindingStates=await loadBindingStateMap(all);
  box.innerHTML=rows.map(r=>{
    const bs=bindingStates.get(r.evidenceSetId)||deriveBindingStateFromAssertions(r.evidenceSetId,[]);
    const p=standaloneEvidenceSetPublic(r,bs),sd=standaloneStructuredDescriptor(r);
    const lifecycle=standaloneLifecycleStatus(r),sourceKey=scoringEvidenceSourceKey(r);
    const supported=standaloneSourceSupportedForG0(r);
    const legacyCount=legacyAttachmentCandidates(r).length;
    let reviewStatus=sd.userReview&&sd.userReview.status||'unreviewed';
    const schemaNote=sd.status==='available'&&!sd.schemaCurrent?' ／ schema: v1→再抽出必要':'';
    let structuredText=sd.status==='available'?`構造化: ${sd.verification.status} ／ 内容確認: ${reviewStatus}${schemaNote}`:'構造化: 未登録';
    if (!supported&&legacyCount) {
      const legacyStructuredCount=legacyAttachmentCandidates(r).filter(x=>x.legacyStructuredScoringResult&&x.legacyStructuredScoringResult.document).length;
      structuredText=`旧方式から移行: candidate ${legacyCount}件 ／ 旧構造化JSON ${legacyStructuredCount}件（監査用・未Binding）`;
    }
    const reviewBtn=supported&&sd.status==='available'&&sd.verification.status==='source_verified'&&sd.schemaCurrent
      ? `<button class="mini" data-ev-review="${escapeHtml(p.evidenceSetId)}">${reviewStatus==='unreviewed'?'抽出内容をレビュー':'レビューを再確認'}</button>`:'';
    const lifecycleBtn=lifecycle==='archived'
      ? `<button class="mini" data-ev-restore="${escapeHtml(p.evidenceSetId)}">アーカイブから戻す</button>`
      : `<button class="mini danger" data-ev-archive="${escapeHtml(p.evidenceSetId)}">アーカイブ</button>`;
    const structuredBtn=supported&&lifecycle!=='archived'?`<button class="mini" data-ev-structured="${escapeHtml(p.evidenceSetId)}">構造化JSON</button>`:'';
    const sourceLabel=supported?'DAMデンモク':'旧方式・source未分類';
    const candidateLine=legacyCount?`<div class="item-sub scoring-evidence-status">旧添付候補: ${legacyCount}録音（candidate only / NOT binding）</div>`:'';
    const bindingClass=bs.status==='bound'?'ok':bs.status==='binding_conflict'?'err':'wait';
    const bindingText=bs.status==='bound'
      ? `対応済み → ${bs.recordingId}`
      : (bs.status==='binding_conflict'?`対応要確認 (${bs.activeRecordingIds.length}録音)`:'録音との対応: 未確定');
    const bindingBtn=`<button class="mini ${bs.status==='bound'?'is-on':''}" data-ev-binding="${escapeHtml(p.evidenceSetId)}">対応を確認</button>`;
    return `<div class="item scoring-evidence-item${lifecycle==='archived'?' is-archived':''}${supported?'':' is-legacy-source'}"><div class="item-main scoring-evidence-main"><div class="item-title scoring-evidence-id">${escapeHtml(p.evidenceSetId)}</div><div class="item-sub scoring-evidence-meta">${escapeHtml(sourceLabel)} ／ ${p.imageCount}枚 ／ ${escapeHtml(lifecycle)}<br>${escapeHtml(String(p.createdAt||''))}</div><div class="item-sub scoring-evidence-status"><span class="pill ${bindingClass}">${escapeHtml(bindingText)}</span></div><div class="item-sub scoring-evidence-status">${escapeHtml(structuredText)}</div>${candidateLine}</div><div class="item-actions scoring-evidence-actions"><button class="mini" data-ev-export="${escapeHtml(p.evidenceSetId)}">${supported?'抽出ZIP':'証拠ZIP'}</button>${structuredBtn}${reviewBtn}${bindingBtn}${lifecycleBtn}</div></div>`;
  }).join('');
  $$('[data-ev-export]').forEach(b=>b.addEventListener('click',()=>exportStandaloneEvidenceSet(b.dataset.evExport)));
  $$('[data-ev-structured]').forEach(b=>b.addEventListener('click',()=>{ const inp=$('#scoring-structured-input'); inp.dataset.evidenceSetId=b.dataset.evStructured; inp.click(); }));
  $$('[data-ev-review]').forEach(b=>b.addEventListener('click',async()=>{ try { await openStandaloneStructuredReview(b.dataset.evReview); } catch(e){ toast((e&&e.message)||'レビューを開けませんでした'); } }));
  $$('[data-ev-binding]').forEach(b=>b.addEventListener('click',async()=>{ try { await openBindingSheet(b.dataset.evBinding); } catch(e){ console.error(e); toast((e&&e.message)||'Binding管理を開けませんでした'); } }));
  $$('[data-ev-archive]').forEach(b=>b.addEventListener('click',()=>archiveStandaloneEvidenceSet(b.dataset.evArchive)));
  $$('[data-ev-restore]').forEach(b=>b.addEventListener('click',()=>restoreStandaloneEvidenceSet(b.dataset.evRestore)));
  await renderNormalWorkflowStatus().catch(()=>{});
}
async function exportStandaloneEvidenceSet(id) {
  try {
    const set=await dbGet('scoringEvidenceSets',id);
    if (!set) throw new Error('証拠セットが見つかりません');
    const allAssertions=await allBindingAssertions();
    const setAssertions=allAssertions.filter(x=>x&&x.evidenceSetId===id).sort((a,b)=>bindingAssertionSortKey(a).localeCompare(bindingAssertionSortKey(b)));
    const bs=deriveBindingStateFromAssertions(id,setAssertions);
    const files=[
      {name:'evaluation/evidence_set.json',data:JSON.stringify(standaloneEvidenceSetPublic(set,bs),null,2)},
      {name:'evaluation/binding_assertions.json',data:JSON.stringify({schemaVersion:'songscope-binding-assertion-history-v1',evidenceSetId:id,currentState:bs,assertions:setAssertions},null,2)}
    ];
    if (standaloneSourceSupportedForG0(set)) {
      files.push({name:'evaluation/extraction_request.json',data:JSON.stringify(standaloneExtractionRequest(set,bs),null,2)});
    }
    if (legacyAttachmentCandidates(set).length) {
      files.push({name:'evaluation/legacy_attachment_candidates.json',data:JSON.stringify({
        schemaVersion:'songscope-legacy-scoring-attachment-candidates-v1',
        evidenceSetId:set.evidenceSetId,
        candidates:legacyAttachmentCandidates(set).map(x=>({
          summary:legacyCandidatePublic(x),
          preservedLegacyStructuredScoringResult:x.legacyStructuredScoringResult||null
        })),
        warning:'Candidate relation is historical UI provenance only and is not a same-performance binding.'
      },null,2)});
    }
    if (set.structuredScoringResult) {
      files.push({name:'evaluation/structured_scoring_result.json',data:JSON.stringify(structuredEvaluationDocument(set.structuredScoringResult),null,2)});
      files.push({name:'evaluation/structured_scoring_verification.json',data:JSON.stringify({verification:standaloneStructuredDescriptor(set).verification,userReview:set.structuredScoringUserReview||{status:'unreviewed'}},null,2)});
    }
    for (let i=0;i<(set.images||[]).length;i++) {
      const x=set.images[i]; const ext=imageExtFromMeta(x.meta);
      if (!x.blob || typeof x.blob.arrayBuffer !== 'function') throw new Error(`採点画像 ${i+1} のraw bytesを読み込めません`);
      const ab=await x.blob.arrayBuffer();
      const bytes=new Uint8Array(ab);
      const expectedSize=Number(x.meta&&x.meta.fileSize);
      if (Number.isFinite(expectedSize) && expectedSize>=0 && bytes.byteLength!==expectedSize) throw new Error(`採点画像 ${i+1} のサイズが保存metadataと一致しません`);
      const expectedSha=String((x.meta&&x.meta.sha256)||'').toLowerCase();
      if (expectedSha) {
        const gotSha=(await sha256Hex(ab)).toLowerCase();
        if (gotSha!==expectedSha) throw new Error(`採点画像 ${i+1} のSHA-256が保存metadataと一致しません`);
      }
      files.push({name:`evaluation/images/${String(i+1).padStart(2,'0')}_${x.imageId}${ext}`,data:bytes});
    }
    const blob=SongScopeZip.createZip(files);
    const stamp=new Date().toISOString().replace(/[-:]/g,'').slice(0,15);
    await saveBlob(blob,`songscope_scoring_evidence_${id}_${stamp}.zip`);
  } catch(e) { console.error(e); toast('採点証拠の書き出しに失敗しました：'+((e&&e.message)||'')); }
}
async function onStandaloneEvidenceInput(fileList) {
  try {
    const files=Array.from(fileList||[]);
    if (!files.length) return;
    busy('DAMデンモク採点履歴','録音とは別の証拠として保存しています…',20);
    const out=await importStandaloneScoringEvidence(files);
    closeSheet();
    await renderStandaloneEvidenceSets();
    toast(out.duplicate ? '同じ画像セットはすでに保存されています' : `${out.set.images.length}枚を未紐付け採点証拠として保存しました`);
  } catch(e) { closeSheet(); console.error(e); toast('採点履歴の保存に失敗しました：'+((e&&e.message)||'')); }
}

/* ---------------- 完全バックアップ / 復元 ---------------- */
const FULL_BACKUP_SCHEMA = 'songscope-full-backup-v1';
const FULL_BACKUP_BINARY_TAG = '__songscopeBackupBinaryV1';
const FULL_BACKUP_STORE_NAMES = [
  'recordings', 'audio', 'analysis', 'analysisHistory', 'markers', 'segments',
  'alignmentFeatures', 'alignmentDiagnostics', 'alignmentResults', 'pairContexts', 'scoringEvidenceSets', 'bindingAssertions'
];

function backupPathToken(v) {
  return String(v || 'item').replace(/[^A-Za-z0-9._-]+/g, '_').slice(0, 80) || 'item';
}
function backupBlobExt(mimeType, name) {
  const n = String(name || '').match(/\.[A-Za-z0-9]{1,8}$/);
  if (n) return n[0].toLowerCase();
  const t = String(mimeType || '').toLowerCase();
  if (t.includes('mp4') || t.includes('m4a')) return '.m4a';
  if (t.includes('mpeg')) return '.mp3';
  if (t.includes('wav')) return '.wav';
  if (t.includes('aac')) return '.aac';
  if (t.includes('png')) return '.png';
  if (t.includes('jpeg') || t.includes('jpg')) return '.jpg';
  if (t.includes('webp')) return '.webp';
  if (t.includes('json')) return '.json';
  return '.bin';
}
function backupSpecialNumber(v) {
  if (Number.isNaN(v)) return { __songscopeSpecialNumberV1: 'NaN' };
  if (v === Infinity) return { __songscopeSpecialNumberV1: 'Infinity' };
  if (v === -Infinity) return { __songscopeSpecialNumberV1: '-Infinity' };
  return v;
}

async function backupEncodeValue(value, ctx, pathHint) {
  if (value === null || value === undefined || typeof value === 'string' || typeof value === 'boolean') return value;
  if (typeof value === 'number') return isFinite(value) ? value : backupSpecialNumber(value);
  if (typeof value === 'bigint') return { __songscopeBigIntV1: String(value) };

  if (typeof Blob !== 'undefined' && value instanceof Blob) {
    const bytes = new Uint8Array(await value.arrayBuffer());
    const isFile = typeof File !== 'undefined' && value instanceof File;
    const originalName = isFile ? value.name : '';
    const ext = backupBlobExt(value.type, originalName);
    const path = `binary/${backupPathToken(pathHint)}_${String(ctx.binaryCounter++).padStart(5, '0')}${ext}`;
    const sha = await sha256Hex(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength));
    ctx.files.push({ name: path, data: bytes });
    ctx.binaryManifest.push({ path, kind: isFile ? 'File' : 'Blob', byteLength: bytes.byteLength, mimeType: value.type || '', fileName: originalName || null, sha256: sha });
    return {
      [FULL_BACKUP_BINARY_TAG]: true,
      kind: isFile ? 'File' : 'Blob', path, byteLength: bytes.byteLength,
      mimeType: value.type || '', fileName: originalName || null,
      lastModified: isFile && isFinite(value.lastModified) ? value.lastModified : null,
      sha256: sha
    };
  }

  if (value instanceof ArrayBuffer) {
    const bytes = new Uint8Array(value.slice(0));
    const path = `binary/${backupPathToken(pathHint)}_${String(ctx.binaryCounter++).padStart(5, '0')}.arraybuffer.bin`;
    ctx.files.push({ name: path, data: bytes });
    return { [FULL_BACKUP_BINARY_TAG]: true, kind: 'ArrayBuffer', path, byteLength: bytes.byteLength };
  }

  if (ArrayBuffer.isView(value)) {
    const bytes = new Uint8Array(value.buffer, value.byteOffset, value.byteLength).slice();
    const ctor = value instanceof DataView ? 'DataView' : (value.constructor && value.constructor.name) || 'Uint8Array';
    const path = `binary/${backupPathToken(pathHint)}_${String(ctx.binaryCounter++).padStart(5, '0')}.${backupPathToken(ctor)}.bin`;
    ctx.files.push({ name: path, data: bytes });
    return { [FULL_BACKUP_BINARY_TAG]: true, kind: 'TypedArray', ctor, path, byteLength: bytes.byteLength };
  }

  if (Array.isArray(value)) {
    const out = [];
    for (let i = 0; i < value.length; i++) out.push(await backupEncodeValue(value[i], ctx, `${pathHint}_${i}`));
    return out;
  }

  if (typeof value === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(value)) out[k] = await backupEncodeValue(v, ctx, `${pathHint}_${k}`);
    return out;
  }
  return null;
}

function backupTypedArrayCtor(name) {
  const map = {
    Int8Array, Uint8Array, Uint8ClampedArray, Int16Array, Uint16Array,
    Int32Array, Uint32Array, Float32Array, Float64Array
  };
  if (typeof BigInt64Array !== 'undefined') map.BigInt64Array = BigInt64Array;
  if (typeof BigUint64Array !== 'undefined') map.BigUint64Array = BigUint64Array;
  return map[name] || null;
}

async function backupDecodeValue(value, entries) {
  if (value === null || value === undefined || typeof value !== 'object') return value;
  if (Object.prototype.hasOwnProperty.call(value, '__songscopeSpecialNumberV1')) {
    if (value.__songscopeSpecialNumberV1 === 'NaN') return NaN;
    if (value.__songscopeSpecialNumberV1 === 'Infinity') return Infinity;
    if (value.__songscopeSpecialNumberV1 === '-Infinity') return -Infinity;
    throw new Error('バックアップ内の特殊数値が不正です');
  }
  if (Object.prototype.hasOwnProperty.call(value, '__songscopeBigIntV1')) return BigInt(value.__songscopeBigIntV1);
  if (value[FULL_BACKUP_BINARY_TAG] === true) {
    const bytes = entries.get(value.path);
    if (!bytes) throw new Error(`バックアップ内のバイナリが見つかりません: ${value.path}`);
    if (Number(value.byteLength) !== bytes.byteLength) throw new Error(`バイナリサイズが一致しません: ${value.path}`);
    const copy = bytes.slice();
    if (value.sha256) {
      const got = await sha256Hex(copy.buffer.slice(copy.byteOffset, copy.byteOffset + copy.byteLength));
      if (got.toLowerCase() !== String(value.sha256).toLowerCase()) throw new Error(`バイナリSHA-256が一致しません: ${value.path}`);
    }
    if (value.kind === 'ArrayBuffer') return copy.buffer;
    if (value.kind === 'TypedArray') {
      if (value.ctor === 'DataView') return new DataView(copy.buffer);
      const C = backupTypedArrayCtor(value.ctor);
      if (!C) throw new Error(`未対応のTypedArrayです: ${value.ctor}`);
      return new C(copy.buffer);
    }
    if (value.kind === 'File' && typeof File !== 'undefined') {
      return new File([copy], value.fileName || 'restored.bin', { type: value.mimeType || '', lastModified: Number(value.lastModified || Date.now()) });
    }
    if (value.kind === 'Blob' || value.kind === 'File') return new Blob([copy], { type: value.mimeType || '' });
    throw new Error(`未対応のバイナリ種別です: ${value.kind}`);
  }
  if (Array.isArray(value)) {
    const out = [];
    for (const v of value) out.push(await backupDecodeValue(v, entries));
    return out;
  }
  const out = {};
  for (const [k, v] of Object.entries(value)) out[k] = await backupDecodeValue(v, entries);
  return out;
}

async function buildFullBackupPackage() {
  const ctx = { files: [], binaryCounter: 0, binaryManifest: [] };
  const storeCounts = {};
  for (let i = 0; i < FULL_BACKUP_STORE_NAMES.length; i++) {
    const store = FULL_BACKUP_STORE_NAMES[i];
    const rows = await dbAll(store).catch(() => []);
    storeCounts[store] = rows.length;
    const encoded = await backupEncodeValue(rows, ctx, `store_${store}`);
    ctx.files.push({ name: `stores/${store}.json`, data: JSON.stringify(encoded) });
    $('#busy-bar').style.width = String(10 + Math.round((i + 1) / FULL_BACKUP_STORE_NAMES.length * 62)) + '%';
    $('#busy-msg').textContent = `${store} を保存しています… (${rows.length}件)`;
  }
  const rawAudio = ctx.binaryManifest.filter(x => /store_audio.*_blob_/i.test(x.path));
  const evalImages = ctx.binaryManifest.filter(x => /evaluationImageBlob/i.test(x.path));
  const manifest = {
    schemaVersion: FULL_BACKUP_SCHEMA,
    app: 'SongScope', appVersion: APP_VERSION, schemaVersionAtExport: SCHEMA_VERSION,
    buildId: BUILD_ID, dbName: DB_NAME, dbVersion: DB_VER, exportedAt: nowIso(),
    restoreMode: 'merge_backup_precedence_for_same_primary_key',
    settings: JSON.parse(JSON.stringify(settings)),
    preferences: { includeAudioInNormalExport: getFlag('includeAudio', false) },
    stores: storeCounts,
    binaryAssets: ctx.binaryManifest,
    rawEvidenceSummary: {
      blobCount: ctx.binaryManifest.filter(x => x.kind === 'Blob' || x.kind === 'File').length,
      audioBlobCount: rawAudio.length,
      evaluationImageBlobCount: evalImages.length,
      totalBinaryBytes: ctx.binaryManifest.reduce((a, x) => a + Number(x.byteLength || 0), 0)
    },
    integrity: {
      zipEntryCrc32VerifiedOnRestore: true,
      blobSha256VerifiedOnRestore: true,
      recordingAudioSha256CrossCheckedOnRestore: true,
      evaluationImageSha256CrossCheckedOnRestore: true
    },
    note: '完全復元用バックアップ。IndexedDB全store、raw audio、採点画像、full analysis、alignment dataを含みます。復元は既存データを削除せず、同一primary keyはバックアップ側で更新します。'
  };
  ctx.files.unshift({ name: 'manifest.json', data: JSON.stringify(manifest, null, 2) });
  return { manifest, files: ctx.files };
}

async function backupAll() {
  try {
    busy('完全バックアップ', 'IndexedDBとraw evidenceを収集しています…', 5);
    const pkg = await buildFullBackupPackage();
    $('#busy-msg').textContent = 'ZIPを作成しています…';
    $('#busy-bar').style.width = '85%';
    const blob = SongScopeZip.createZip(pkg.files);
    $('#busy-bar').style.width = '100%';
    closeSheet();
    const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');
    const name = `songscope_full_backup_${stamp}.zip`;
    const how = await saveBlob(blob, name);
    if (how !== 'cancelled') toast(`完全バックアップを書き出しました（${fmtBytes(blob.size)}）`, 4000);
  } catch (e) {
    closeSheet();
    console.error(e);
    toast('完全バックアップに失敗しました：' + ((e && e.message) || ''), 5500);
  }
}

async function parseFullBackupFile(file) {
  const entries = await SongScopeZip.readZip(file);
  const td = new TextDecoder('utf-8');
  const manifestBytes = entries.get('manifest.json');
  if (!manifestBytes) throw new Error('manifest.json がありません');
  const manifest = JSON.parse(td.decode(manifestBytes));
  if (!manifest || manifest.schemaVersion !== FULL_BACKUP_SCHEMA) throw new Error('SongScope完全バックアップv1ではありません');
  if (Number(manifest.dbVersion || 0) > DB_VER) throw new Error('このバックアップは、より新しいSongScopeで作成されています。最新版を開いてください');

  const stores = {};
  for (const store of FULL_BACKUP_STORE_NAMES) {
    const raw = entries.get(`stores/${store}.json`);
    // R0(DB5)完全バックアップにはpairContexts storeがまだ存在しない。
    // そのバックアップをR1以降でも災害復旧に使えるよう、DB6導入storeだけ空配列として扱う。
    if (!raw && store === 'pairContexts' && Number(manifest.dbVersion || 0) < 6) {
      stores[store] = [];
      continue;
    }
    // G0b03(DB7)で追加した独立採点証拠store。旧backupは空として復元可能。
    if (!raw && store === 'scoringEvidenceSets' && Number(manifest.dbVersion || 0) < 7) {
      stores[store] = [];
      continue;
    }
    if (!raw) throw new Error(`stores/${store}.json がありません`);
    const encoded = JSON.parse(td.decode(raw));
    const decoded = await backupDecodeValue(encoded, entries);
    if (!Array.isArray(decoded)) throw new Error(`${store} の形式が不正です`);
    const expectedRaw = manifest.stores && manifest.stores[store];
    const expected = expectedRaw === undefined ? NaN : Number(expectedRaw);
    if (isFinite(expected) && decoded.length !== expected) throw new Error(`${store} の件数がmanifestと一致しません`);
    stores[store] = decoded;
  }
  return { manifest, stores };
}

async function validateFullBackupEvidence(parsed, opts = {}) {
  const recMap = new Map((parsed.stores.recordings || []).map(r => [r.recordingId, r]));
  for (const asset of parsed.stores.audio || []) {
    if (!asset || !asset.recordingId) throw new Error('audio storeにrecordingIdの無いrecordがあります');
    const rec = recMap.get(asset.recordingId) || null;
    if (asset.blob && rec && rec.audioSha256) {
      const ab = await asset.blob.arrayBuffer();
      const got = await sha256Hex(ab);
      if (got.toLowerCase() !== String(rec.audioSha256).toLowerCase()) throw new Error(`raw audio SHA-256不一致: ${asset.recordingId}`);
    }
    if (asset.evaluationImageBlob && asset.evaluationImageMeta && asset.evaluationImageMeta.sha256) {
      const ab = await asset.evaluationImageBlob.arrayBuffer();
      const got = await sha256Hex(ab);
      if (got.toLowerCase() !== String(asset.evaluationImageMeta.sha256).toLowerCase()) throw new Error(`採点画像SHA-256不一致: ${asset.recordingId}`);
    }
    if (Array.isArray(asset.evaluationEvidenceImages)) {
      for (const x of asset.evaluationEvidenceImages) {
        if (!x || !x.blob || !x.meta || !x.meta.sha256) throw new Error(`採点証拠セット不完全: ${asset.recordingId}`);
        const got=await sha256Hex(await x.blob.arrayBuffer());
        if (got.toLowerCase()!==String(x.meta.sha256).toLowerCase()) throw new Error(`採点証拠セットSHA-256不一致: ${asset.recordingId}`);
      }
    }
    if (asset.evaluationStructured && rec) validateStructuredEvaluationDocument(structuredEvaluationDocument(asset.evaluationStructured), rec, asset.evaluationImageMeta || null);
  }
  for (const set of parsed.stores.scoringEvidenceSets || []) {
    if (!set || !set.evidenceSetId || !Array.isArray(set.images) || !set.images.length) throw new Error('独立採点証拠セットが不完全です');
    for (const x of set.images) {
      if (!x || !x.blob || !x.meta || !x.meta.sha256) throw new Error(`独立採点証拠セット画像が不完全: ${set.evidenceSetId}`);
      const got=await sha256Hex(await x.blob.arrayBuffer());
      if (got.toLowerCase()!==String(x.meta.sha256).toLowerCase()) throw new Error(`独立採点証拠セットSHA-256不一致: ${set.evidenceSetId}`);
    }
  }
  const setIds=new Set((parsed.stores.scoringEvidenceSets||[]).map(x=>x&&x.evidenceSetId).filter(Boolean));
  const recordingRows=parsed.stores.recordings||[];
  const backupRecById=new Map(recordingRows.map(x=>[x&&x.recordingId,x]).filter(x=>x[0]));
  for (const a of parsed.stores.bindingAssertions||[]) {
    if (!a||!a.assertionId||a.schemaVersion!==BINDING_ASSERTION_SCHEMA) throw new Error('Binding assertionが不完全です');
    if (!setIds.has(a.evidenceSetId)) throw new Error(`Binding assertionのevidenceSetIdが存在しません: ${a.assertionId}`);
    if (a.action!=='bind'&&a.action!=='unbind') throw new Error(`Binding assertion action不正: ${a.assertionId}`);
    const sha=String(a.audioSha256||'').toLowerCase();
    if (!sha) throw new Error(`Binding assertionにaudioSha256がありません: ${a.assertionId}`);
    const rec=a.recordingId?backupRecById.get(a.recordingId):null;
    if (rec&&rec.audioSha256&&String(rec.audioSha256).toLowerCase()!==sha) throw new Error(`Binding assertionのrecordingIdとaudioSha256が矛盾しています: ${a.assertionId}`);
    // A deleted/aliased recording row may be absent while the historical raw-audio target identity remains valid.
  }
  // 通常restoreでは、同じrecordingIdに異なる既存SHAがある場合だけ自動mergeを止める。
  if (opts.checkExistingConflicts !== false) {
    for (const rec of parsed.stores.recordings || []) {
      const existing = await dbGet('recordings', rec.recordingId).catch(() => null);
      if (existing && existing.audioSha256 && rec.audioSha256 && String(existing.audioSha256).toLowerCase() !== String(rec.audioSha256).toLowerCase()) {
        throw new Error(`既存データとrecordingIdが衝突しています: ${rec.recordingId}`);
      }
    }
  }
  return true;
}


const FULL_BACKUP_KEY_PATHS = {
  recordings: 'recordingId', audio: 'recordingId', analysis: 'recordingId', analysisHistory: 'analysisId',
  markers: 'markerId', segments: 'segmentId', alignmentFeatures: 'featureKey',
  alignmentDiagnostics:'diagnosticId',alignmentResults:'pairKey',pairContexts:'audioPairKey',
  scoringEvidenceSets:'evidenceSetId',bindingAssertions:'assertionId'
};

function backupRowKey(store, row) {
  const kp = FULL_BACKUP_KEY_PATHS[store];
  return kp && row ? row[kp] : undefined;
}
function restoreDiagnosticError(prefix, detail, txError) {
  const parts = [prefix];
  if (detail) {
    if (detail.store) parts.push(`store=${detail.store}`);
    if (detail.key !== undefined && detail.key !== null) parts.push(`key=${String(detail.key)}`);
    if (detail.errorName) parts.push(`error=${detail.errorName}`);
    if (detail.errorMessage) parts.push(detail.errorMessage);
  }
  if ((!detail || !detail.errorName) && txError && txError.name) parts.push(`transaction=${txError.name}`);
  if ((!detail || !detail.errorMessage) && txError && txError.message) parts.push(txError.message);
  const e = new Error(parts.join(' / '));
  e.code = 'SONGSCOPE_RESTORE_TRANSACTION_FAILED';
  e.detail = detail || null;
  e.transactionError = txError || null;
  return e;
}

async function restoreBackupStoresToDb(parsed, d) {
  const stores = FULL_BACKUP_STORE_NAMES.filter(n => d.objectStoreNames.contains(n));
  await new Promise((resolve, reject) => {
    const tx = d.transaction(stores, 'readwrite');
    let firstRequestError = null;
    try {
      for (const store of stores) {
        const os = tx.objectStore(store);
        for (const row of parsed.stores[store] || []) {
          const key = backupRowKey(store, row);
          let req;
          try {
            req = os.put(row);
          } catch (err) {
            firstRequestError = { store, key, errorName: err && err.name || 'SynchronousError', errorMessage: err && err.message || String(err) };
            try { tx.abort(); } catch (_) { }
            throw err;
          }
          req.onerror = () => {
            if (!firstRequestError) {
              const err = req.error;
              firstRequestError = { store, key, errorName: err && err.name || 'IDBRequestError', errorMessage: err && err.message || '' };
            }
          };
        }
      }
    } catch (e) {
      if (!firstRequestError) firstRequestError = { store: null, key: null, errorName: e && e.name || 'Error', errorMessage: e && e.message || String(e) };
      try { tx.abort(); } catch (_) { }
    }
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(restoreDiagnosticError('復元トランザクションに失敗しました', firstRequestError, tx.error));
    tx.onabort = () => reject(restoreDiagnosticError('復元トランザクションが中断されました', firstRequestError, tx.error));
  });
}

function openStandaloneSongScopeDb(name) {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(name, DB_VER);
    req.onupgradeneeded = () => ensureSongScopeStores(req.result, req.transaction);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error || new Error('一時DBを開けませんでした'));
    req.onblocked = () => reject(new Error('一時DBの作成がblockedになりました'));
  });
}
function deleteStandaloneDb(name, opts = {}) {
  const timeoutMs = Number(opts.timeoutMs || 5000);
  return new Promise((resolve, reject) => {
    const req = indexedDB.deleteDatabase(name);
    let settled = false;
    let blockedObserved = false;
    let timer = null;
    const finish = (fn, value) => {
      if (settled) return;
      settled = true;
      if (timer) clearTimeout(timer);
      fn(value);
    };
    req.onsuccess = () => finish(resolve, { deleted: true, blockedObserved });
    req.onerror = () => finish(reject, req.error || new Error('一時DBを削除できませんでした'));
    // blockedは「削除失敗」ではない。既存connectionがcloseされれば同じrequestが後から成功できる。
    req.onblocked = () => { blockedObserved = true; };
    timer = setTimeout(() => {
      const e = new Error(blockedObserved ? '一時DB削除がblockedのままタイムアウトしました' : '一時DB削除がタイムアウトしました');
      e.code = blockedObserved ? 'SONGSCOPE_TEMP_DB_DELETE_BLOCKED_TIMEOUT' : 'SONGSCOPE_TEMP_DB_DELETE_TIMEOUT';
      e.blockedObserved = blockedObserved;
      finish(reject, e);
    }, timeoutMs);
  });
}
function dbAllFromConnection(d, store) {
  // IDBRequest成功時点ではtransactionがまだactiveな場合がある。
  // self-testで直後にDBをclose/deleteするとSafariでdeleteDatabaseがblockedになり得るため、
  // transaction.oncompleteまで待ってから結果を返す。
  return new Promise((resolve, reject) => {
    const tx = d.transaction(store, 'readonly');
    const req = tx.objectStore(store).getAll();
    let rows = null;
    let requestError = null;
    req.onsuccess = () => { rows = req.result || []; };
    req.onerror = () => { requestError = req.error || new Error(`${store}の読出しに失敗しました`); };
    tx.oncomplete = () => {
      if (requestError) reject(requestError);
      else resolve(rows || []);
    };
    tx.onerror = () => reject(requestError || tx.error || new Error(`${store}の読出しtransactionに失敗しました`));
    tx.onabort = () => reject(requestError || tx.error || new Error(`${store}の読出しtransactionが中断されました`));
  });
}

async function backupValueMismatch(a, b, path = '$') {
  if (typeof a === 'number' || typeof b === 'number') {
    if (typeof a === 'number' && typeof b === 'number' && (Object.is(a, b) || (Number.isNaN(a) && Number.isNaN(b)))) return null;
    return `${path}: number mismatch`;
  }
  if (a === null || b === null || a === undefined || b === undefined || typeof a !== 'object' || typeof b !== 'object') {
    return Object.is(a, b) ? null : `${path}: value mismatch`;
  }
  if (a instanceof Date || b instanceof Date) {
    if (!(a instanceof Date) || !(b instanceof Date) || a.getTime() !== b.getTime()) return `${path}: Date mismatch`;
    return null;
  }
  if (typeof Blob !== 'undefined' && (a instanceof Blob || b instanceof Blob)) {
    if (!(a instanceof Blob) || !(b instanceof Blob)) return `${path}: Blob kind mismatch`;
    if (a.size !== b.size || String(a.type || '') !== String(b.type || '')) return `${path}: Blob metadata mismatch`;
    const [ha, hb] = await Promise.all([sha256Hex(await a.arrayBuffer()), sha256Hex(await b.arrayBuffer())]);
    if (ha !== hb) return `${path}: Blob SHA-256 mismatch`;
    const aIsFile = typeof File !== 'undefined' && a instanceof File;
    const bIsFile = typeof File !== 'undefined' && b instanceof File;
    if (aIsFile !== bIsFile) return `${path}: File/Blob mismatch`;
    if (aIsFile && (a.name !== b.name || Number(a.lastModified) !== Number(b.lastModified))) return `${path}: File metadata mismatch`;
    return null;
  }
  if (a instanceof ArrayBuffer || b instanceof ArrayBuffer) {
    if (!(a instanceof ArrayBuffer) || !(b instanceof ArrayBuffer) || a.byteLength !== b.byteLength) return `${path}: ArrayBuffer mismatch`;
    const [ha, hb] = await Promise.all([sha256Hex(a), sha256Hex(b)]);
    return ha === hb ? null : `${path}: ArrayBuffer SHA-256 mismatch`;
  }
  if (ArrayBuffer.isView(a) || ArrayBuffer.isView(b)) {
    if (!ArrayBuffer.isView(a) || !ArrayBuffer.isView(b)) return `${path}: TypedArray kind mismatch`;
    const ca = a instanceof DataView ? 'DataView' : a.constructor && a.constructor.name;
    const cb = b instanceof DataView ? 'DataView' : b.constructor && b.constructor.name;
    if (ca !== cb || a.byteLength !== b.byteLength) return `${path}: TypedArray metadata mismatch`;
    const aa = a.buffer.slice(a.byteOffset, a.byteOffset + a.byteLength);
    const bb = b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
    const [ha, hb] = await Promise.all([sha256Hex(aa), sha256Hex(bb)]);
    return ha === hb ? null : `${path}: TypedArray SHA-256 mismatch`;
  }
  if (Array.isArray(a) || Array.isArray(b)) {
    if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length) return `${path}: array length mismatch`;
    for (let i = 0; i < a.length; i++) {
      const m = await backupValueMismatch(a[i], b[i], `${path}[${i}]`);
      if (m) return m;
    }
    return null;
  }
  const ka = Object.keys(a).sort(), kb = Object.keys(b).sort();
  if (ka.length !== kb.length || ka.some((k, i) => k !== kb[i])) return `${path}: object keys mismatch`;
  for (const k of ka) {
    const m = await backupValueMismatch(a[k], b[k], `${path}.${k}`);
    if (m) return m;
  }
  return null;
}

async function verifyDbAgainstParsedBackup(d, parsed) {
  const summary = { stores: {}, checkedRows: 0 };
  for (const store of FULL_BACKUP_STORE_NAMES) {
    const expected = parsed.stores[store] || [];
    const actual = await dbAllFromConnection(d, store);
    if (actual.length !== expected.length) throw new Error(`${store}: 復元後件数 ${actual.length} / 期待 ${expected.length}`);
    const byKey = new Map(actual.map(r => [String(backupRowKey(store, r)), r]));
    for (const row of expected) {
      const key = String(backupRowKey(store, row));
      if (!byKey.has(key)) throw new Error(`${store}: 復元後にkey=${key}がありません`);
      const mismatch = await backupValueMismatch(row, byKey.get(key), `${store}[${key}]`);
      if (mismatch) throw new Error(`復元後データ不一致: ${mismatch}`);
      summary.checkedRows++;
    }
    summary.stores[store] = actual.length;
  }
  return summary;
}

async function disasterRecoverySelfTest(file) {
  if (!file) return;
  const testDbName = `${DB_NAME}_restore_test_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  let testDb = null;
  let verificationPassed = false;
  let summary = null;
  let parsed = null;
  let cleanup = { status: 'not_attempted', temporaryDatabaseDeletedAfterVerification: false, blockedObserved: false, error: null };
  try {
    busy('災害復旧セルフテスト', 'バックアップZIPを検証しています…', 7);
    parsed = await parseFullBackupFile(file);
    $('#busy-msg').textContent = 'raw audio・採点画像のSHA-256を検証しています…';
    $('#busy-bar').style.width = '28%';
    await validateFullBackupEvidence(parsed, { checkExistingConflicts: false });
    $('#busy-msg').textContent = '本番データとは別の空DBを作成しています…';
    $('#busy-bar').style.width = '43%';
    // testDbNameは毎回ランダムで一意。事前deleteは不要で、古いconnectionとの競合も避ける。
    testDb = await openStandaloneSongScopeDb(testDbName);
    $('#busy-msg').textContent = '空DBへ完全復元しています…';
    $('#busy-bar').style.width = '58%';
    await restoreBackupStoresToDb(parsed, testDb);
    $('#busy-msg').textContent = '復元後の全store・binaryを元バックアップと照合しています…';
    $('#busy-bar').style.width = '76%';
    summary = await verifyDbAgainstParsedBackup(testDb, parsed);
    verificationPassed = true;

    // 復旧成否はここで確定。cleanupは別の検査項目として扱う。
    $('#busy-msg').textContent = '復旧検証は成功しました。一時DBを後片付けしています…';
    $('#busy-bar').style.width = '92%';
    try { testDb.close(); } catch (_) { }
    testDb = null;
    // WebKitではclose直後にdeleteを投げるとblockedを一度通知することがある。
    // readonly transaction完了を待った上で、さらにevent loopを1回譲る。
    await new Promise(resolve => setTimeout(resolve, 80));
    try {
      const deletion = await deleteStandaloneDb(testDbName, { timeoutMs: 5000 });
      cleanup = {
        status: 'deleted',
        temporaryDatabaseDeletedAfterVerification: true,
        blockedObserved: !!(deletion && deletion.blockedObserved),
        error: null
      };
    } catch (cleanupError) {
      cleanup = {
        status: cleanupError && cleanupError.code === 'SONGSCOPE_TEMP_DB_DELETE_BLOCKED_TIMEOUT' ? 'blocked_timeout_warning' : 'cleanup_warning',
        temporaryDatabaseDeletedAfterVerification: false,
        blockedObserved: !!(cleanupError && cleanupError.blockedObserved),
        error: {
          name: cleanupError && cleanupError.name || 'Error',
          code: cleanupError && cleanupError.code || null,
          message: cleanupError && cleanupError.message || String(cleanupError)
        }
      };
      console.warn('Disaster recovery self-test cleanup warning', cleanupError);
    }

    $('#busy-bar').style.width = '100%';
    closeSheet();
    const recs = Number(summary.stores.recordings || 0);
    const report = {
      schemaVersion: 'songscope-disaster-recovery-selftest-v2',
      status: 'passed',
      verificationStatus: 'passed',
      cleanupStatus: cleanup.status,
      testedAt: nowIso(),
      app: { name: 'SongScope', version: APP_VERSION, buildId: BUILD_ID, schemaVersion: SCHEMA_VERSION, dbVersion: DB_VER },
      inputBackup: {
        fileName: file.name || null, byteLength: Number(file.size || 0),
        schemaVersion: parsed.manifest.schemaVersion, exportedAt: parsed.manifest.exportedAt || null,
        sourceAppVersion: parsed.manifest.appVersion || null, sourceBuildId: parsed.manifest.buildId || null,
        dbVersion: parsed.manifest.dbVersion, stores: parsed.manifest.stores || {}
      },
      isolation: {
        temporaryDatabaseUsed: true,
        productionDatabaseName: DB_NAME,
        productionDatabaseModifiedBySelfTest: false,
        temporaryDatabaseDeletedAfterVerification: cleanup.temporaryDatabaseDeletedAfterVerification,
        cleanupStatus: cleanup.status,
        cleanupBlockedObserved: cleanup.blockedObserved,
        cleanupError: cleanup.error
      },
      verification: {
        zipCrcValidated: true, manifestValidated: true, rawAudioAndScoringImageShaValidated: true,
        emptyTemporaryDatabaseRestoreCompleted: true,
        restoredStoreCountsMatched: true, restoredRowsCompared: summary.checkedRows, restoredValuesAndBinaryMatched: true,
        stores: summary.stores
      }
    };
    const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');
    const reportName = `songscope_restore_selftest_${stamp}.json`;
    const reportBlob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const how = await saveBlob(reportBlob, reportName);
    const cleanupNote = cleanup.temporaryDatabaseDeletedAfterVerification
      ? ''
      : '。復旧検証は成功しましたが、一時DBの削除だけ警告になりました';
    toast(`災害復旧セルフテスト成功：空DBから ${recs}録音を完全復元・照合しました${cleanupNote}${how === 'cancelled' ? '' : '（結果JSONを書き出しました）'}`, 8000);
  } catch (e) {
    // verificationが成立する前の失敗だけを「災害復旧セルフテスト失敗」とする。
    try { if (testDb) testDb.close(); } catch (_) { }
    testDb = null;
    // cleanup失敗はここでも本来のfailure原因を上書きしない。
    try {
      await new Promise(resolve => setTimeout(resolve, 80));
      await deleteStandaloneDb(testDbName, { timeoutMs: 1500 });
    } catch (_) { }
    closeSheet();
    console.error('Disaster recovery self-test failed', e, e && e.detail);
    toast('災害復旧セルフテスト失敗：' + ((e && e.message) || ''), 8000);
  }
}

async function restoreFullBackupAtomic(parsed) {
  const d = await db();
  await restoreBackupStoresToDb(parsed, d);
  // R0(DB5) backupはpairContextsを持たないため、restore直後にもlegacy alignment contextを移行する。
  await migrateR1PairContexts().catch(e => console.warn('R1 pair-context migration after restore skipped:', e));
  if (parsed.manifest.settings && typeof parsed.manifest.settings === 'object') {
    settings = Object.assign({}, DEFAULT_SETTINGS, parsed.manifest.settings);
    saveSettings();
  }
  if (parsed.manifest.preferences && typeof parsed.manifest.preferences.includeAudioInNormalExport === 'boolean') {
    setFlag('includeAudio', parsed.manifest.preferences.includeAudioInNormalExport);
  }
}

async function restoreAll(file) {
  if (!file) return;
  try {
    busy('完全バックアップを検証', 'ZIPのCRCとmanifestを確認しています…', 8);
    const parsed = await parseFullBackupFile(file);
    $('#busy-msg').textContent = 'raw audio・採点画像のSHA-256を検証しています…';
    $('#busy-bar').style.width = '45%';
    await validateFullBackupEvidence(parsed);
    closeSheet();
    const recCount = Number(parsed.manifest.stores && parsed.manifest.stores.recordings || 0);
    const ok = confirm(`完全バックアップを復元します。\n\n録音: ${recCount}件\n作成日時: ${parsed.manifest.exportedAt || '不明'}\n\n既存データは削除しません。同じIDのデータはバックアップ内容で更新します。続行しますか？`);
    if (!ok) return;
    busy('復元中', '検証済みデータを1つのIndexedDBトランザクションで復元しています…', 72);
    await restoreFullBackupAtomic(parsed);
    await migrateLegacyRecordingAttachedScoringEvidence().catch(e=>console.warn('legacy scoring migration after restore skipped:',e));
    $('#busy-bar').style.width='100%';
    closeSheet();
    state.rec = null; state.analysis = null;
    await loadRecordings();
    await renderStandaloneEvidenceSets();
    refreshStorageEstimate();
    toast(`復元しました（録音 ${recCount}件）`, 4500);
  } catch (e) {
    closeSheet();
    console.error(e);
    if (isDbVersionError(e)) toast(dbVersionUserMessage(), 6500);
    else if (isDbBlockedError(e)) toast(dbBlockedUserMessage(), 6500);
    else toast('復元を中止しました：' + ((e && e.message) || ''), 6500);
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
  lastAlignmentResult: null,
  comparisonContext: null
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
  cmp.comparisonContext = null;
  const ar = $('#cmp-align-result'); if (ar) ar.innerHTML = '<p class="small">まだ判定していません。</p>';
  const cx = $('#cmp-context-status'); if (cx) cx.innerHTML = '<p class="small">A/Bを選ぶと、保存済みの比較前提を確認します。</p>';
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
  const scoringEvidenceContext=await scoringEvidenceRelationsForRecording(id);
  cmp[side]={rec,an,audio,url,asset:au||null,scoringEvidenceContext,scoringEvidenceCandidates:scoringEvidenceContext.legacyCandidateSets||[]};
  drawCompare();
  refreshE4ContextUi().catch(() => { });
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
    // R1: human comparison context is stored in pairContexts, never copied into new alignment results.
    cmp.lastAlignmentResult = result;
    if (result) await dbPut('alignmentResults', result).catch(() => { });
    renderAlignmentDiagnostic(diag);
    await refreshE4ContextUi().catch(() => { });
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
/* =====================================================================
 * R1: pair-level comparison context (chronology + scoring conditions)
 *
 * 人間が確認した事実はalignment結果から独立した pairContexts store に保存する。
 * keyはraw audio SHA-256のsorted pairだけで、alignment algorithm/versionを含めない。
 * ===================================================================== */
function comparisonAudioPairKey(hashA, hashB) {
  if (!hashA || !hashB) return null;
  return [String(hashA).toLowerCase(), String(hashB).toLowerCase()].sort().join(':');
}
function currentComparisonAudioIdentity() {
  const a = cmp.a && cmp.a.rec, b = cmp.b && cmp.b.rec;
  if (!a || !b) return null;
  const aHash = a.audioSha256 || (cmp.a.an && cmp.a.an.audioSha256) || null;
  const bHash = b.audioSha256 || (cmp.b.an && cmp.b.an.audioSha256) || null;
  if (!aHash || !bHash) return null;
  return {
    audioPairKey: comparisonAudioPairKey(aHash, bHash),
    pairKey: alignmentPairKey(aHash, bHash), // D1 result lookup用。contextのidentityではない。
    a: { recordingId: a.recordingId || null, audioSha256: aHash, title: a.title || '' },
    b: { recordingId: b.recordingId || null, audioSha256: bHash, title: b.title || '' }
  };
}
function blankComparisonContext(identity) {
  return {
    schemaVersion: COMPARISON_CONTEXT_SCHEMA,
    audioPairKey: identity && identity.audioPairKey || null,
    // pairKeyは過去export互換と診断用。storage identityはaudioPairKeyのみ。
    pairKey: identity && identity.pairKey || null,
    audioPair: identity ? [identity.a.audioSha256, identity.b.audioSha256].map(x => String(x).toLowerCase()).sort() : [],
    chronology: { status: 'unknown' },
    scoringConditions: { status: 'unknown', coveredFields: SCORING_CONDITION_FIELDS.slice() },
    history: [],
    updatedAt: null
  };
}
function normalizeComparisonContext(raw, identity) {
  const base = blankComparisonContext(identity);
  if (!raw || typeof raw !== 'object') return base;
  const pair = Array.isArray(raw.audioPair) ? raw.audioPair.map(x => String(x).toLowerCase()).sort() : [];
  const expected = base.audioPair.slice().sort();
  // R1ではalignment pairKeyのversion差は無視し、raw audio pairだけをidentityとして検証する。
  if (pair.length === 2 && expected.length === 2 && (pair[0] !== expected[0] || pair[1] !== expected[1])) return base;
  return {
    schemaVersion: COMPARISON_CONTEXT_SCHEMA,
    audioPairKey: identity && identity.audioPairKey || raw.audioPairKey || (pair.length === 2 ? comparisonAudioPairKey(pair[0], pair[1]) : null),
    pairKey: identity && identity.pairKey || raw.pairKey || null,
    legacyAlignmentPairKey: raw.legacyAlignmentPairKey || (raw.schemaVersion === 'songscope-comparison-context-v1' ? raw.pairKey || null : null),
    audioPair: expected.length ? expected : pair,
    chronology: raw.chronology && typeof raw.chronology === 'object' ? raw.chronology : { status: 'unknown' },
    scoringConditions: raw.scoringConditions && typeof raw.scoringConditions === 'object' ? raw.scoringConditions : base.scoringConditions,
    history: Array.isArray(raw.history) ? raw.history.slice(-50) : [],
    migratedFromAlignmentResult: !!raw.migratedFromAlignmentResult,
    invalidatedAt: raw.invalidatedAt || raw.lastInvalidatedAt || null,
    lastInvalidatedAt: raw.lastInvalidatedAt || raw.invalidatedAt || null,
    invalidatedByRecordingDeletion: !!raw.invalidatedByRecordingDeletion,
    invalidatedRecordingId: raw.invalidatedRecordingId || null,
    invalidatedAudioSha256: raw.invalidatedAudioSha256 || null,
    reactivatedAt: raw.reactivatedAt || null,
    reactivatedBy: raw.reactivatedBy || null,
    updatedAt: raw.updatedAt || null
  };
}
function e4HistoryPush(ctx, field, action) {
  const h = Array.isArray(ctx.history) ? ctx.history.slice(-49) : [];
  h.push({ field, action, at: nowIso(), source: 'user_pair_confirmation', appVersion: APP_VERSION, buildId: BUILD_ID });
  ctx.history = h;
  ctx.updatedAt = nowIso();
}
function pairContextIsCurrentlyInvalidated(ctx) {
  if (!ctx || !ctx.invalidatedByRecordingDeletion) return false;
  const inv=Date.parse(ctx.invalidatedAt||ctx.lastInvalidatedAt||'')||0;
  if (!inv) return true;
  const reactivated=Date.parse(ctx.reactivatedAt||'')||0;
  return reactivated<inv;
}
function reactivatePairContextForExplicitUserConfirmation(ctx, field) {
  if (!pairContextIsCurrentlyInvalidated(ctx)) return false;
  const at=nowIso();
  const h=Array.isArray(ctx.history)?ctx.history.slice(-49):[];
  h.push({
    field:field||'pairContext',
    action:'reactivated_by_new_explicit_user_confirmation',
    at,source:'user_pair_confirmation',
    priorInvalidatedAt:ctx.invalidatedAt||ctx.lastInvalidatedAt||null,
    priorInvalidatedRecordingId:ctx.invalidatedRecordingId||null,
    priorInvalidatedAudioSha256:ctx.invalidatedAudioSha256||null,
    appVersion:APP_VERSION,buildId:BUILD_ID
  });
  ctx.history=h;
  ctx.reactivatedAt=at;
  ctx.reactivatedBy='new_explicit_user_confirmation';
  ctx.invalidatedByRecordingDeletion=false;
  ctx.updatedAt=at;
  return true;
}
async function legacyComparisonContextForIdentity(identity) {
  if (!identity) return null;
  let best = null, bestAt = -1, bestPairKey = null;
  const all = await dbAll('alignmentResults').catch(() => []);
  const want = identity.audioPairKey;
  for (const ar of all) {
    const pc = ar && ar.comparisonContext;
    const ap = pc && Array.isArray(pc.audioPair) && pc.audioPair.length === 2 ? comparisonAudioPairKey(pc.audioPair[0], pc.audioPair[1]) : null;
    if (!pc || ap !== want) continue;
    const at = Date.parse(pc.updatedAt || (pc.chronology && pc.chronology.confirmedAt) || ar.updatedAt || ar.createdAt || '') || 0;
    if (at >= bestAt) { best = pc; bestAt = at; bestPairKey = ar.pairKey || null; }
  }
  if (!best) return null;
  const ctx = normalizeComparisonContext(best, identity);
  ctx.legacyAlignmentPairKey = bestPairKey || ctx.legacyAlignmentPairKey || null;
  ctx.migratedFromAlignmentResult = true;
  return ctx;
}
async function getComparisonContextForIdentity(identity) {
  if (!identity || !identity.audioPairKey) return blankComparisonContext(identity);
  let row = await dbGet('pairContexts', identity.audioPairKey).catch(() => null);
  if (row) return normalizeComparisonContext(row, identity);
  // DB6移行直後や古いバックアップ復元直後のfallback。見つけたら新storeへ非破壊移行する。
  const legacy = await legacyComparisonContextForIdentity(identity);
  if (legacy) {
    legacy.audioPairKey = identity.audioPairKey;
    await dbPut('pairContexts', legacy).catch(() => {});
    return legacy;
  }
  return blankComparisonContext(identity);
}
async function putComparisonContextForIdentity(identity, ctx) {
  if (!identity || !identity.audioPairKey) throw new Error('A/BのaudioSha256が不足しています');
  const row = normalizeComparisonContext(ctx, identity);
  row.audioPairKey = identity.audioPairKey;
  row.updatedAt = row.updatedAt || nowIso();
  await dbPut('pairContexts', row);
  return row;
}
async function migrateR1PairContexts() {
  const results = await dbAll('alignmentResults').catch(() => []);
  const latest = new Map();
  for (const ar of results) {
    const pc = ar && ar.comparisonContext;
    if (!pc || !Array.isArray(pc.audioPair) || pc.audioPair.length !== 2) continue;
    const audioPairKey = comparisonAudioPairKey(pc.audioPair[0], pc.audioPair[1]);
    if (!audioPairKey) continue;
    const at = Date.parse(pc.updatedAt || (pc.chronology && pc.chronology.confirmedAt) || ar.updatedAt || ar.createdAt || '') || 0;
    const prev = latest.get(audioPairKey);
    if (!prev || at >= prev.at) latest.set(audioPairKey, { pc, ar, at });
  }
  for (const [audioPairKey, x] of latest) {
    const existing = await dbGet('pairContexts', audioPairKey).catch(() => null);
    const existingAt = Date.parse(existing && existing.updatedAt || '') || 0;
    if (existing && existingAt > x.at) continue;
    const pair = x.pc.audioPair.map(v => String(v).toLowerCase()).sort();
    const identity = {
      audioPairKey,
      pairKey: x.ar && x.ar.pairKey || null,
      a: { recordingId: null, audioSha256: pair[0], title: '' },
      b: { recordingId: null, audioSha256: pair[1], title: '' }
    };
    const row = normalizeComparisonContext(x.pc, identity);
    row.audioPairKey = audioPairKey;
    row.legacyAlignmentPairKey = x.ar && x.ar.pairKey || row.legacyAlignmentPairKey || null;
    row.migratedFromAlignmentResult = true;
    await dbPut('pairContexts', row);
  }
}
async function setE4Chronology(choice) {
  try {
    const identity = currentComparisonAudioIdentity();
    if (!identity) throw new Error('A/BのaudioSha256が不足しています');
    const ctx = await getComparisonContextForIdentity(identity);
    if (choice === 'a_first' || choice === 'b_first') {
      reactivatePairContextForExplicitUserConfirmation(ctx,'chronology');
      const earlier = choice === 'a_first' ? identity.a : identity.b;
      const later = choice === 'a_first' ? identity.b : identity.a;
      ctx.chronology = {
        status: 'user_confirmed_order', source: 'user_pair_confirmation',
        earlierRecordingId: earlier.recordingId, earlierAudioSha256: earlier.audioSha256,
        laterRecordingId: later.recordingId, laterAudioSha256: later.audioSha256,
        confirmedAt: nowIso()
      };
    } else {
      ctx.chronology = { status: 'unknown', source: 'user_cleared_pair_confirmation', updatedAt: nowIso() };
    }
    e4HistoryPush(ctx, 'chronology', choice);
    const saved = await putComparisonContextForIdentity(identity, ctx);
    cmp.comparisonContext = saved;
    await refreshE4ContextUi();
    toast(choice === 'clear' ? '補助の時間順確認を解除しました' : '時間順を補助確認として保存しました');
  } catch (e) { toast((e && e.message) || '時間順を保存できませんでした'); }
}
async function setE4ScoringConditions(choice) {
  try {
    const identity = currentComparisonAudioIdentity();
    if (!identity) throw new Error('A/BのaudioSha256が不足しています');
    const ctx = await getComparisonContextForIdentity(identity);
    const covered = SCORING_CONDITION_FIELDS.slice();
    if (choice === 'same') {
      reactivatePairContextForExplicitUserConfirmation(ctx,'scoringConditions');
      ctx.scoringConditions = { status: 'user_confirmed_same', source: 'user_pair_confirmation', coveredFields: covered, meaning: 'all_covered_fields_same', confirmedAt: nowIso() };
    } else if (choice === 'different') {
      reactivatePairContextForExplicitUserConfirmation(ctx,'scoringConditions');
      ctx.scoringConditions = { status: 'user_confirmed_different', source: 'user_pair_confirmation', coveredFields: covered, meaning: 'at_least_one_covered_field_differs', confirmedAt: nowIso() };
    } else {
      ctx.scoringConditions = { status: 'unknown', source: 'user_cleared_pair_confirmation', coveredFields: covered, updatedAt: nowIso() };
    }
    e4HistoryPush(ctx, 'scoringConditions', choice);
    const saved = await putComparisonContextForIdentity(identity, ctx);
    cmp.comparisonContext = saved;
    await refreshE4ContextUi();
    toast(choice === 'clear' ? '補助の採点条件確認を解除しました' : '採点条件を補助確認として保存しました');
  } catch (e) { toast((e && e.message) || '採点条件を保存できませんでした'); }
}
function e4SourceVerifiedResult(desc) {
  const st = desc && desc.evaluationEvidence && desc.evaluationEvidence.structuredScoringResult;
  return e3StructuredIsSourceVerified(st) && st.result && typeof st.result === 'object' ? st.result : null;
}
function e4ReadableScoringDate(result) {
  const x = result && result.scoringDate;
  if (!x || x.status !== 'readable' || !x.value) return null;
  const m = String(x.value).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return null;
  const t = Date.parse(`${m[1]}-${m[2]}-${m[3]}T00:00:00Z`);
  return isFinite(t) ? { value: `${m[1]}-${m[2]}-${m[3]}`, epochDay: Math.floor(t / 86400000) } : null;
}
function e4ConfirmedScoringDate(desc) {
  const st = desc && desc.evaluationEvidence && desc.evaluationEvidence.structuredScoringResult;
  if (!e3StructuredIsSourceVerified(st)) return null;
  if (!st.extraction || st.extraction.userReview !== 'user_confirmed') return null;
  return e4ReadableScoringDate(st.result);
}
function e4ResolveChronology(descA, descB, ctx) {
  const c = ctx && ctx.chronology || {};
  const pairIds = new Set([descA && descA.recordingId, descB && descB.recordingId].filter(Boolean));
  let pairOrder = null;
  if (c.status === 'user_confirmed_order' && pairIds.has(c.earlierRecordingId) && pairIds.has(c.laterRecordingId) && c.earlierRecordingId !== c.laterRecordingId) {
    pairOrder = { earlierRecordingId: c.earlierRecordingId, laterRecordingId: c.laterRecordingId, confirmedAt: c.confirmedAt || null };
  }
  const pa = descA && descA.metadataProvenance && descA.metadataProvenance.recordedAt || {};
  const pb = descB && descB.metadataProvenance && descB.metadataProvenance.recordedAt || {};
  const ta = Date.parse(descA && descA.recordedAt || ''), tb = Date.parse(descB && descB.recordedAt || '');
  let timeOrder = null;
  if (pa.confirmation === 'user_confirmed' && pb.confirmation === 'user_confirmed' && isFinite(ta) && isFinite(tb) && ta !== tb) {
    const aFirst = ta < tb;
    timeOrder = {
      earlierRecordingId: aFirst ? descA.recordingId : descB.recordingId,
      laterRecordingId: aFirst ? descB.recordingId : descA.recordingId,
      aRecordedAt: descA.recordedAt, bRecordedAt: descB.recordedAt
    };
  }
  const pda = descA && descA.metadataProvenance && descA.metadataProvenance.recordedDate || {};
  const pdb = descB && descB.metadataProvenance && descB.metadataProvenance.recordedDate || {};
  const daUser = descA && descA.recordedDate || null, dbUser = descB && descB.recordedDate || null;
  let dateOrder = null;
  if (!timeOrder && pda.confirmation === 'user_confirmed' && pdb.confirmation === 'user_confirmed' && /^\d{4}-\d{2}-\d{2}$/.test(String(daUser||'')) && /^\d{4}-\d{2}-\d{2}$/.test(String(dbUser||'')) && daUser !== dbUser) {
    const aFirst = daUser < dbUser;
    dateOrder = { earlierRecordingId:aFirst?descA.recordingId:descB.recordingId, laterRecordingId:aFirst?descB.recordingId:descA.recordingId, aRecordedDate:daUser, bRecordedDate:dbUser };
  }
  if (dateOrder && pairOrder && (dateOrder.earlierRecordingId !== pairOrder.earlierRecordingId || dateOrder.laterRecordingId !== pairOrder.laterRecordingId)) {
    return { status:'conflict', source:'conflict_user_confirmed_recorded_date_vs_pair_confirmation', resolution:null, earlierRecordingId:null,laterRecordingId:null,earlierSide:null,laterSide:null, recordedDateEvidence:dateOrder,pairConfirmationEvidence:pairOrder, note:'User-confirmed calendar dates and relative-order confirmation disagree. SongScope does not choose one automatically.' };
  }
  if (timeOrder && pairOrder && (timeOrder.earlierRecordingId !== pairOrder.earlierRecordingId || timeOrder.laterRecordingId !== pairOrder.laterRecordingId)) {
    return {
      status: 'conflict', source: 'conflict_user_confirmed_recorded_at_vs_pair_confirmation', resolution: null,
      earlierRecordingId: null, laterRecordingId: null, earlierSide: null, laterSide: null,
      recordedAtEvidence: timeOrder, pairConfirmationEvidence: pairOrder,
      note: 'Two user-confirmed chronology sources disagree. SongScope does not choose one automatically.'
    };
  }
  const selected = timeOrder || dateOrder || pairOrder;
  if (selected) {
    const source = timeOrder ? 'user_confirmed_recorded_at' : (dateOrder ? 'user_confirmed_recorded_date' : 'user_pair_confirmation');
    return {
      status: 'established', source, resolution: timeOrder ? 'timestamp' : (dateOrder ? 'day' : 'explicit_order'),
      earlierRecordingId: selected.earlierRecordingId, laterRecordingId: selected.laterRecordingId,
      earlierSide: selected.earlierRecordingId === descA.recordingId ? 'A' : 'B',
      laterSide: selected.laterRecordingId === descA.recordingId ? 'A' : 'B',
      aRecordedAt: timeOrder && timeOrder.aRecordedAt || null,
      bRecordedAt: timeOrder && timeOrder.bRecordedAt || null,
      aRecordedDate: dateOrder && dateOrder.aRecordedDate || null,
      bRecordedDate: dateOrder && dateOrder.bRecordedDate || null,
      confirmedAt: pairOrder && pairOrder.confirmedAt || null
    };
  }
  // 外部AI抽出日付は、画像SHA bindingだけでは値そのものの本人確認にならない。
  // userReview=user_confirmed の場合だけ補助chronology evidenceとして利用する。
  const da = e4ConfirmedScoringDate(descA), db2 = e4ConfirmedScoringDate(descB);
  if (da && db2 && da.epochDay !== db2.epochDay) {
    const aFirst = da.epochDay < db2.epochDay;
    return {
      status: 'established', source: 'user_reviewed_scoring_date', resolution: 'day',
      earlierRecordingId: aFirst ? descA.recordingId : descB.recordingId,
      laterRecordingId: aFirst ? descB.recordingId : descA.recordingId,
      earlierSide: aFirst ? 'A' : 'B', laterSide: aFirst ? 'B' : 'A',
      aScoringDate: da.value, bScoringDate: db2.value,
      note: 'Order is established at calendar-day resolution only after the extracted scoring dates were user-reviewed.'
    };
  }
  return {
    status: 'not_established', source: 'insufficient_order_evidence', resolution: null,
    earlierRecordingId: null, laterRecordingId: null, earlierSide: null, laterSide: null,
    note: 'SongScope does not infer order from title suffixes, A/B selection order, equal legacy timestamps, or unreviewed AI-extracted scoring dates.'
  };
}
function e4ScoringConditionPairReport(ctx) {
  const s = ctx && ctx.scoringConditions || {};
  if (s.status !== 'user_confirmed_same' && s.status !== 'user_confirmed_different') return null;
  return {
    status: s.status,
    source: s.source || 'user_pair_confirmation',
    coveredFields: Array.isArray(s.coveredFields) ? s.coveredFields : SCORING_CONDITION_FIELDS.slice(),
    confirmedAt: s.confirmedAt || null,
    meaning: s.meaning || (s.status === 'user_confirmed_same' ? 'all_covered_fields_same' : 'at_least_one_covered_field_differs')
  };
}
function e4ContextExport(descA, descB, ctx, chronology, conditions) {
  return {
    schemaVersion: COMPARISON_CONTEXT_SCHEMA,
    pairKey: ctx && ctx.pairKey || null, // backward-compatible alias for alignmentPairKey
    audioPairKey: ctx && ctx.audioPairKey || null,
    alignmentPairKey: ctx && ctx.pairKey || null,
    storedPairContext: ctx || null,
    resolvedChronology: chronology,
    scoringConditionComparability: conditions,
    principles: [
      'Chronology is separate evidence from A/B selection order.',
      'SongScope never infers chronology from a title suffix such as 1, 2, take2, or similar naming.',
      'R1 stores pair-level human context independently from alignment algorithm/version.',
      'User-confirmed recordedAt is the primary chronology route; pair order confirmation is a fallback and conflicts are surfaced.',
      'AI-extracted scoring dates are not hard chronology evidence until userReview is user_confirmed.',
      'Per-recording machine/mode/key/octave values are preferred for comparability; pair-level condition confirmation is a fallback.',
      'Pair-level context does not overwrite per-recording metadata or its provenance.'
    ]
  };
}
function e4ChronologyText(ch, descA, descB) {
  if (ch && ch.status === 'conflict') return '時間順: 本人確認どうしが矛盾しています';
  if (!ch || ch.status !== 'established') return '時間順: 未確定';
  const aTitle = descA && descA.title || 'A', bTitle = descB && descB.title || 'B';
  const early = ch.earlierSide === 'A' ? `A「${aTitle}」` : `B「${bTitle}」`;
  const late = ch.laterSide === 'A' ? `A「${aTitle}」` : `B「${bTitle}」`;
  return `時間順: ${early} → ${late}（${ch.source}）`;
}
function e4ConditionText(c) {
  if (!c) return '採点条件: 未確定';
  if (c.overallStatus === 'confirmed_match') return '採点条件: 同じ（録音別の4条件で確認）';
  if (c.overallStatus === 'confirmed_match_by_pair_report') return '採点条件: 同じ（補助pair確認）';
  if (c.overallStatus === 'confirmed_difference_present') return '採点条件: 違いあり（録音別の4条件）';
  if (c.overallStatus === 'confirmed_difference_present_by_pair_report') return '採点条件: 違いあり（補助pair確認）';
  if (c.overallStatus === 'conflict_pair_report_vs_recording_metadata') return '採点条件: 証拠が矛盾しています';
  return '採点条件: 未確定';
}
async function refreshE4ContextUi() {
  const el = $('#cmp-context-status');
  if (!el) return;
  if (!cmp.a || !cmp.b || !cmp.a.rec || !cmp.b.rec) { el.innerHTML = '<p class="small">A/Bを選択してください。</p>'; return; }
  const identity = currentComparisonAudioIdentity();
  if (!identity) { el.innerHTML = '<p class="small">A/BのaudioSha256が不足しています。</p>'; return; }
  const result = await dbGet('alignmentResults', identity.pairKey).catch(() => null);
  const ctx = await getComparisonContextForIdentity(identity);
  cmp.comparisonContext = ctx;
  const descA = d2RecordingDescriptor('a'), descB = d2RecordingDescriptor('b');
  const chronology = e4ResolveChronology(descA, descB, ctx);
  const conditions = e3StrictScoringConditionComparability(descA, descB, ctx);
  const d1 = result ? `D1: ${result.status}` : 'D1: 未保存';
  const primary = chronology && chronology.source === 'user_confirmed_recorded_at' ? '日時確認が主経路' : 'A/B順序は補助経路';
  el.innerHTML = `<p class="small"><b>${escapeHtml(e4ChronologyText(chronology, descA, descB))}</b></p><p class="small"><b>${escapeHtml(e4ConditionText(conditions))}</b></p><p class="small mono">${escapeHtml(primary)} / ${escapeHtml(d1)} / audio pair ${escapeHtml(identity.audioPairKey.slice(-16))}</p>`;
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
    recordedAt: rec.recordedAt || null,
    recordedDate: rec.recordedDate || null,
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
    },
    metadataProvenance: normalizedMetadataProvenance(rec),
    evaluationEvidence:Object.assign(
      {consumerSource:'scoringEvidenceSets',legacyRecordingAttachedFieldsIgnored:true},
      recordingScoringEvidenceDescriptor(rec,d.scoringEvidenceContext)
    )
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
function d2ReportedFieldComparison(field, aValue, bValue) {
  const raw = v => String(v === null || v === undefined ? '' : v).trim();
  const aRaw = raw(aValue), bRaw = raw(bValue);
  const a = SCORING_CONDITION_FIELDS.includes(field) ? scoringConditionComparableValue(field, aRaw) : aRaw;
  const b = SCORING_CONDITION_FIELDS.includes(field) ? scoringConditionComparableValue(field, bRaw) : bRaw;
  let status = 'unknown';
  if (a && b) status = a === b ? 'same_stored_metadata' : 'different_stored_metadata';
  return { field, status, a: aRaw || null, b: bRaw || null, aCanonical: a || null, bCanonical: b || null, provenance: 'recording_metadata' };
}
function d2ConditionComparison(descA, descB) {
  const a = (descA && descA.userMetadata) || {}, b = (descB && descB.userMetadata) || {};
  const fields = [
    d2ReportedFieldComparison('recordingSetupPreset', a.recordingSetupPreset, b.recordingSetupPreset),
    d2ReportedFieldComparison('device', a.device, b.device),
    d2ReportedFieldComparison('scoringMode', a.scoringMode, b.scoringMode),
    d2ReportedFieldComparison('keyChange', a.keyChange, b.keyChange),
    d2ReportedFieldComparison('octave', a.octave, b.octave)
  ];
  const known = fields.filter(x => x.status !== 'unknown');
  const different = known.filter(x => x.status === 'different_stored_metadata');
  let overallStatus = 'unknown';
  if (different.length) overallStatus = 'stored_metadata_difference_present';
  else if (known.length === fields.length) overallStatus = 'all_listed_fields_same_stored_metadata';
  else if (known.length) overallStatus = 'partially_known_no_stored_difference';
  return {
    overallStatus,
    fields,
    note: 'This is metadata compatibility only. matching stored metadata does not prove identical acoustic conditions or user confirmation; unknown fields must remain unknown.'
  };
}
function d2MetricCatalog() {
  return {
    schemaVersion: 'songscope-d2-metric-semantics-v1',
    packageRole: 'interpretation_guardrails',
    metrics: {
      pairCoverage: {
        source: 'alignment_and_recording_duration',
        signalScope: 'time_mapping',
        interpretationClass: 'structural_evidence',
        allowedInterpretation: [
          'How much common aligned time exists inside a nominal comparison window.',
          'Whether A/B statistics were computed over full, partial, or no common interval.'
        ],
        prohibitedInterpretation: ['Singing quality', 'Pitch accuracy', 'Vocal stability']
      },
      rmsRelativeDb: {
        source: 'audio_derived_mixed_signal',
        signalScope: 'voice_plus_accompaniment_plus_room',
        vocalSpecific: false,
        normalization: "rms_db minus that recording's finite-RMS p95 reference; not a shared calibrated SPL scale",
        interpretationClass: 'diagnostic_only',
        practiceLayerEligible: false,
        allowedInterpretation: [
          'Describe the within-recording relative level distribution in the same aligned song interval.',
          'Compare distribution shape cautiously when recording conditions are sufficiently similar.'
        ],
        prohibitedInterpretation: [
          'Absolute loudness difference between recordings',
          'Singer vocal volume or vocal power',
          'Improvement or deterioration by itself'
        ]
      },
      f0CandidateHz: {
        source: 'audio_derived_mixed_signal_yin_candidate',
        signalScope: 'voice_plus_accompaniment_plus_room',
        vocalSpecific: false,
        interpretationClass: 'diagnostic_only',
        practiceLayerEligible: false,
        safeLabel: 'mixed_audio_periodicity_candidate_hz',
        allowedInterpretation: [
          'Describe the distribution of retained periodicity candidates produced by the current estimator.',
          'Use together with candidate amount, ambiguity evidence, alignment, and other anchors for diagnostic reasoning.'
        ],
        prohibitedInterpretation: [
          'True vocal F0',
          'Vocal range',
          'Pitch accuracy',
          'The singer sang higher or lower',
          'Improvement or deterioration by itself'
        ]
      },
      f0CandidateRatio: {
        source: 'estimator_evidence',
        interpretationClass: 'diagnostic_only',
        practiceLayerEligible: false,
        safeLabel: 'mixed_audio_periodicity_candidate_ratio',
        allowedInterpretation: ['Fraction of available analysis frames that produced a retained F0 candidate under the current estimator settings.'],
        prohibitedInterpretation: ['Voiced ratio', 'Singing duration', 'Correct-pitch ratio', 'Vocal activity probability']
      },
      f0Ambiguity: {
        source: 'heuristic_estimator_diagnostic',
        interpretationClass: 'diagnostic_only',
        practiceLayerEligible: false,
        allowedInterpretation: ['How often the retained candidate was accompanied by a currently detected harmonic/integer-ratio ambiguity pattern.'],
        prohibitedInterpretation: [
          'Probability that F0 is wrong',
          'ambiguity=none means correct',
          'A direct singing-quality score'
        ]
      },
      userReportedMarkersAndSegments: {
        source: 'user_reported',
        interpretationClass: 'evaluation_anchor',
        allowedInterpretation: ['Use as user-reported locations of good/concern/other observations after alignment.'],
        prohibitedInterpretation: ['Objective acoustic ground truth']
      },
      damScore: {
        source: 'recording_metadata_when_present',
        interpretationClass: 'outcome_anchor',
        allowedInterpretation: ['Use as an external scoring outcome when present, while checking machine/mode/key and other provenance.'],
        prohibitedInterpretation: ['Direct acoustic explanation of why the score changed']
      },
      structuredScoringResult: {
        source: 'external_json_linked_to_scoring_result_image_sha256',
        interpretationClass: 'outcome_anchor',
        allowedInterpretation: ['Use readable values extracted from a preserved scoring-result image when recordingId and source image SHA-256 verify.'],
        prohibitedInterpretation: ['Treating externally extracted values as app OCR', 'Silently overriding conflicting manual metadata', 'Direct acoustic explanation of score changes']
      }
    }
  };
}
function d2EvaluationAnchors(descA, descB, strictConditions = null) {
  const a = (descA && descA.userMetadata) || {}, b = (descB && descB.userMetadata) || {};
  const scoreA = parseStoredScore(a.damScore), scoreB = parseStoredScore(b.damScore);
  const provA = descA && descA.metadataProvenance || {}, provB = descB && descB.metadataProvenance || {};
  const confirmed = (prov, key) => prov[key] && prov[key].confirmation === 'user_confirmed';
  const sameKnownConfirmed = key => a[key] && b[key] && String(a[key]).trim() === String(b[key]).trim() && confirmed(provA, key) && confirmed(provB, key);
  const requiredReportedSame = ['device', 'scoringMode', 'keyChange', 'octave'];
  const conditionsConfirmedMatch = !!(strictConditions && (strictConditions.overallStatus === 'confirmed_match' || strictConditions.overallStatus === 'confirmed_match_by_pair_report'));
  const metadataConditionsConfirmedMatch = requiredReportedSame.every(sameKnownConfirmed);
  const confirmedConditionsMatch = conditionsConfirmedMatch || metadataConditionsConfirmedMatch;
  let scoreStatus = 'unavailable';
  if (scoreA !== null && scoreB !== null) {
    const scoresConfirmed = confirmed(provA, 'damScore') && confirmed(provB, 'damScore');
    scoreStatus = scoresConfirmed && confirmedConditionsMatch
      ? 'available_confirmed_conditions_match'
      : 'available_comparability_not_established';
  }
  const imgA = descA && descA.evaluationEvidence ? descA.evaluationEvidence.scoringResultImage : { status: 'unavailable' };
  const imgB = descB && descB.evaluationEvidence ? descB.evaluationEvidence.scoringResultImage : { status: 'unavailable' };
  const stA = descA && descA.evaluationEvidence ? descA.evaluationEvidence.structuredScoringResult : { status: 'unavailable' };
  const stB = descB && descB.evaluationEvidence ? descB.evaluationEvidence.structuredScoringResult : { status: 'unavailable' };
  const verifiedStructured = x => x && x.status === 'available' && x.verification && x.verification.status === 'source_verified';
  const stScoreA = verifiedStructured(stA) ? stA.overallScore : null;
  const stScoreB = verifiedStructured(stB) ? stB.overallScore : null;
  let structuredStatus = 'unavailable';
  if (verifiedStructured(stA) && verifiedStructured(stB)) {
    structuredStatus = confirmedConditionsMatch
      ? 'available_both_confirmed_conditions_match'
      : 'available_both_comparability_not_established';
  } else if (verifiedStructured(stA) || verifiedStructured(stB)) structuredStatus = 'available_one_side';
  const consistency = (recDesc, stored, extracted) => {
    if (stored === null || extracted === null) return 'not_comparable';
    if (Math.abs(stored-extracted) <= 0.001) return 'same_value';
    const p = recDesc && recDesc.metadataProvenance && recDesc.metadataProvenance.damScore || {};
    return p.confirmation === 'user_confirmed' ? 'conflict_manual_score_vs_source_verified_image' : 'different_value_unconfirmed_manual_score';
  };
  const scoreConsistencyA = consistency(descA, scoreA, stScoreA), scoreConsistencyB = consistency(descB, scoreB, stScoreB);
  const manualScoreConflict = scoreConsistencyA === 'conflict_manual_score_vs_source_verified_image' || scoreConsistencyB === 'conflict_manual_score_vs_source_verified_image';
  if (manualScoreConflict) scoreStatus = 'blocked_conflict_manual_score_vs_source_verified_image';
  return {
    scoringConditionComparability: strictConditions || null,
    damScore: {
      status: scoreStatus,
      a: scoreA,
      b: scoreB,
      deltaBminusA: !manualScoreConflict && scoreA !== null && scoreB !== null ? +(scoreB - scoreA).toFixed(3) : null,
      provenance: {
        a: provA.damScore || { source: 'legacy_unknown', confirmation: 'unknown' },
        b: provB.damScore || { source: 'legacy_unknown', confirmation: 'unknown' }
      },
      note: 'Score delta is an outcome observation only. It does not identify the acoustic cause of a change.'
    },
    scoringResultImages: {
      status: imgA.status === 'available' && imgB.status === 'available' ? 'available_both' : (imgA.status === 'available' || imgB.status === 'available' ? 'available_one_side' : 'unavailable'),
      a: imgA,
      b: imgB,
      parsedByApp: false,
      note: 'Attached scoring-result images are preserved as external evidence. SongScope does not OCR, normalize, or silently reconcile them with manually stored score metadata.'
    },
    structuredScoringResults: {
      status: structuredStatus,
      a: stA,
      b: stB,
      overallScoreA: stScoreA,
      overallScoreB: stScoreB,
      deltaBminusA: stScoreA !== null && stScoreB !== null ? +(stScoreB - stScoreA).toFixed(3) : null,
      consistencyWithStoredDamScore: {
        a: scoreConsistencyA,
        b: scoreConsistencyB,
        manualScoreComparisonBlocked: manualScoreConflict
      },
      note: 'Values are externally structured from preserved image evidence and are usable only when source verification passes. Comparison conditions remain a separate question.'
    }
  };
}


/* ---------------- Phase E3: pairwise outcome evidence ---------------- */
function e3StructuredIsSourceVerified(desc) {
  if (!(desc&&desc.status==='available'&&desc.verification&&desc.verification.status==='source_verified')) return false;
  // build13: a source-verified scoring result is a recording outcome only after explicit user Binding.
  if (desc.relationship&&desc.relationship.status!=='bound_user_confirmed') return false;
  if (desc.outcomeEligibility&&desc.outcomeEligibility.eligible===false) return false;
  return true;
}
function e3ReadableNumber(node, valueKey = 'value') {
  if (!node || node.status !== 'readable') return null;
  const n = Number(node[valueKey]);
  return isFinite(n) ? n : null;
}
function e3Number(v, digits = 3) {
  const n = Number(v);
  return isFinite(n) ? +n.toFixed(digits) : null;
}
function e3NumericPair(key, label, a, b, unit, classification, directionality = 'descriptive_only') {
  const av = a === null || a === undefined ? null : e3Number(a);
  const bv = b === null || b === undefined ? null : e3Number(b);
  let status = 'unavailable';
  if (av !== null && bv !== null) status = 'available_both';
  else if (av !== null || bv !== null) status = 'available_one_side';
  return {
    key, label: label || key, status, a: av, b: bv,
    deltaBminusA: av !== null && bv !== null ? e3Number(bv - av) : null,
    unit: unit || null,
    classification,
    directionality,
    interpretation: 'Numeric difference only. This field does not by itself establish overall singing improvement or an acoustic cause.'
  };
}
function e3ArrayMap(result, arrayKey, valueKey) {
  const out = new Map();
  const rows = result && Array.isArray(result[arrayKey]) ? result[arrayKey] : [];
  for (const row of rows) {
    if (!row || !row.key || row.status !== 'readable') continue;
    const n = Number(row[valueKey]);
    if (!isFinite(n)) continue;
    out.set(String(row.key), {
      key: String(row.key),
      label: row.label || String(row.key),
      value: n,
      unit: row.unit || (valueKey === 'count' ? 'count' : null)
    });
  }
  return out;
}
function e3UnionKeys(aMap, bMap) {
  return Array.from(new Set([...aMap.keys(), ...bMap.keys()])).sort();
}
function e3StrictScoringConditionComparability(descA, descB, pairContext = null) {
  const fields = SCORING_CONDITION_FIELDS.slice();
  const a = descA && descA.userMetadata || {}, b = descB && descB.userMetadata || {};
  const pa = descA && descA.metadataProvenance || {}, pb = descB && descB.metadataProvenance || {};
  const rows = fields.map(field => {
    const avRaw = String(a[field] === null || a[field] === undefined ? '' : a[field]).trim();
    const bvRaw = String(b[field] === null || b[field] === undefined ? '' : b[field]).trim();
    const av = scoringConditionComparableValue(field, avRaw);
    const bv = scoringConditionComparableValue(field, bvRaw);
    const ac = !!(pa[field] && pa[field].confirmation === 'user_confirmed');
    const bc = !!(pb[field] && pb[field].confirmation === 'user_confirmed');
    let status = 'not_established';
    if (av && bv && ac && bc) status = av === bv ? 'confirmed_same' : 'confirmed_different';
    return {
      field, status,
      a: avRaw || null, b: bvRaw || null,
      aCanonical: av || null, bCanonical: bv || null,
      aConfirmation: pa[field] && pa[field].confirmation || 'unknown',
      bConfirmation: pb[field] && pb[field].confirmation || 'unknown'
    };
  });
  const pairReport = e4ScoringConditionPairReport(pairContext);
  const metadataDifferent = rows.some(r => r.status === 'confirmed_different');
  const metadataAllSame = rows.every(r => r.status === 'confirmed_same');
  let overallStatus = 'not_established';
  if (metadataDifferent) {
    overallStatus = pairReport && pairReport.status === 'user_confirmed_same'
      ? 'conflict_pair_report_vs_recording_metadata' : 'confirmed_difference_present';
  } else if (metadataAllSame) {
    overallStatus = pairReport && pairReport.status === 'user_confirmed_different'
      ? 'conflict_pair_report_vs_recording_metadata' : 'confirmed_match';
  } else if (pairReport && pairReport.status === 'user_confirmed_same') {
    overallStatus = 'confirmed_match_by_pair_report';
  } else if (pairReport && pairReport.status === 'user_confirmed_different') {
    overallStatus = 'confirmed_difference_present_by_pair_report';
  }
  return {
    overallStatus,
    requiredFields: fields,
    fields: rows,
    pairReport,
    preferredEvidence: metadataAllSame || metadataDifferent ? 'per_recording_user_confirmed_values' : (pairReport ? 'pair_report_fallback' : 'none'),
    note: 'R1 prefers user-confirmed per-recording machine/mode/key/octave values. Pair-level reports remain a fallback for legacy data. Values are canonicalized before equality checks; unknown/other values do not establish comparability.'
  };
}
function e4ProgressionObservation(descA, descB, resultA, resultB, verifiedA, verifiedB, chronology, conditions) {
  const ch = chronology || { status: 'not_established' };
  let status = 'chronology_not_established';
  if (!verifiedA || !verifiedB) status = 'requires_two_source_verified_structured_evaluations';
  else if (ch.status === 'established') {
    if (conditions && (conditions.overallStatus === 'confirmed_match' || conditions.overallStatus === 'confirmed_match_by_pair_report')) status = 'ordered_outcome_observation_comparable';
    else if (conditions && (conditions.overallStatus === 'confirmed_difference_present' || conditions.overallStatus === 'confirmed_difference_present_by_pair_report')) status = 'ordered_outcome_observation_conditions_differ';
    else if (conditions && conditions.overallStatus === 'conflict_pair_report_vs_recording_metadata') status = 'ordered_outcome_observation_condition_evidence_conflict';
    else status = 'ordered_outcome_observation_comparability_not_established';
  }
  if (!verifiedA || !verifiedB || ch.status !== 'established') {
    return {
      status,
      chronology: ch,
      earlier: null,
      later: null,
      laterMinusEarlier: null,
      note: 'A/B deltas remain available elsewhere, but progression requires an established earlier→later order.'
    };
  }
  const earlierIsA = ch.earlierRecordingId === descA.recordingId;
  const er = earlierIsA ? resultA : resultB, lr = earlierIsA ? resultB : resultA;
  const earlierDesc = earlierIsA ? descA : descB, laterDesc = earlierIsA ? descB : descA;
  const metricE = e3ArrayMap(er, 'metrics', 'value'), metricL = e3ArrayMap(lr, 'metrics', 'value');
  const metrics = e3UnionKeys(metricE, metricL).map(key => {
    const e = metricE.get(key), l = metricL.get(key);
    const ev = e ? e.value : null, lv = l ? l.value : null;
    return {
      key,
      label: (e && e.label) || (l && l.label) || key,
      unit: (e && e.unit) || (l && l.unit) || null,
      status: isFinite(Number(ev)) && isFinite(Number(lv)) ? 'available_both' : (isFinite(Number(ev)) || isFinite(Number(lv)) ? 'available_one_side' : 'unavailable'),
      earlier: isFinite(Number(ev)) ? Number(ev) : null,
      later: isFinite(Number(lv)) ? Number(lv) : null,
      deltaLaterMinusEarlier: isFinite(Number(ev)) && isFinite(Number(lv)) ? +(Number(lv) - Number(ev)).toFixed(6) : null,
      interpretation: 'External scoring outcome change only; not an acoustic-cause claim.'
    };
  });
  const eo = e3ReadableNumber(er.overallScore), lo = e3ReadableNumber(lr.overallScore);
  return {
    status,
    chronology: ch,
    earlier: { recordingId: earlierDesc.recordingId, title: earlierDesc.title || '', sideInPackage: earlierIsA ? 'A' : 'B' },
    later: { recordingId: laterDesc.recordingId, title: laterDesc.title || '', sideInPackage: earlierIsA ? 'B' : 'A' },
    laterMinusEarlier: {
      overallScore: {
        status: isFinite(Number(eo)) && isFinite(Number(lo)) ? 'available_both' : 'unavailable',
        earlier: isFinite(Number(eo)) ? eo : null,
        later: isFinite(Number(lo)) ? lo : null,
        delta: isFinite(Number(eo)) && isFinite(Number(lo)) ? +(lo - eo).toFixed(6) : null,
        unit: 'points',
        interpretation: 'Later-minus-earlier external score change. A positive value is not by itself proof of overall singing improvement.'
      },
      metrics
    },
    scoringConditionComparability: conditions,
    interpretationGuardrails: [
      'Chronology is evidence-backed and is never inferred from A/B selection order or title suffixes.',
      'Later-minus-earlier values are external outcome changes, not causal explanations.',
      'Even when scoring conditions are confirmed to match, a single pair is not enough to establish a stable improvement trend.'
    ]
  };
}
function e3AdaptStructuredResultForComparison(st) {
  if (!st||!st.result||typeof st.result!=='object') return {};
  if (st.schemaVersion!==STANDALONE_SCORING_RESULT_SCHEMA) return st.result;
  const r=st.result,fs=st.fieldStatus||{};
  const readable=(key,val)=>{
    if (fs[key]!=='extracted') return {status:'unavailable'};
    const n=Number(val); return isFinite(n)?{status:'readable',value:n}:{status:'unavailable'};
  };
  const metrics=[];
  const pushMetric=(key,label,field,val,unit)=>{
    const x=readable(field,val); if(x.status==='readable') metrics.push({key,label,status:'readable',value:x.value,unit});
  };
  pushMetric('pitch_accuracy','音程正確率','pitchAccuracy',r.pitchAccuracy,'percent');
  pushMetric('expression_score','表現力','expressionScore',r.expressionScore,'points');
  pushMetric('dynamics_score','抑揚','dynamicsScore',r.dynamicsScore,'points');
  pushMetric('listening_score','聴感','listeningScore',r.listeningScore,'points');
  const discrete=[
    ['longToneSkillDiscrete','long_tone_skill','ロングトーン上手さ'],
    ['vibratoSkillDiscrete','vibrato_skill','ビブラート上手さ'],
    ['stabilityDiscrete','stability_display','安定性']
  ];
  for (const [field,key,label] of discrete) {
    const x=r[field];
    if (fs[field]==='extracted'&&x&&isFinite(Number(x.observedLit))) metrics.push({
      key,label,status:'readable',value:Number(x.observedLit),unit:'lit_count',
      observedTotal:isFinite(Number(x.observedTotal))?Number(x.observedTotal):null
    });
  }
  if (fs.rhythmDiscrete==='extracted'&&r.rhythmDiscrete&&isFinite(Number(r.rhythmDiscrete.observedPositionIndex))) {
    metrics.push({
      key:'rhythm_position',label:'リズム表示位置',status:'readable',
      value:Number(r.rhythmDiscrete.observedPositionIndex),unit:'ordinal_position',
      observedPositionCount:isFinite(Number(r.rhythmDiscrete.observedPositionCount))?Number(r.rhythmDiscrete.observedPositionCount):null,
      directionality:'non_monotonic'
    });
  }
  const techniques=[];
  if (fs.techniques==='extracted'&&r.techniques&&typeof r.techniques==='object') {
    const map=[
      ['shakuriCount','shakuri','しゃくり'],['kobushiCount','kobushi','こぶし'],['fallCount','fall','フォール'],
      ['accentCount','accent','アクセント'],['hammeringCount','hammering','ハンマリング']
    ];
    for (const [src,key,label] of map) {
      const n=Number(r.techniques[src]); if(isFinite(n)) techniques.push({key,label,status:'readable',count:n,unit:'count'});
    }
  }
  const vibrato=fs.vibrato==='extracted'&&r.vibrato?{
    status:'readable',
    totalDurationSec:isFinite(Number(r.vibrato.durationSec))?Number(r.vibrato.durationSec):null,
    count:isFinite(Number(r.vibrato.count))?Number(r.vibrato.count):null,
    type:r.vibrato.type||null
  }:{status:'unavailable'};
  const ranking=r.ranking&&isFinite(Number(r.ranking.rank))&&isFinite(Number(r.ranking.population))
    ? {status:'readable',position:Number(r.ranking.rank),total:Number(r.ranking.population)}
    : {status:'unavailable'};
  const bonus=r.bonus&&isFinite(Number(r.bonus.value))?{status:'readable',value:Number(r.bonus.value)}:{status:'unavailable'};
  return {
    overallScore:readable('overallScore',r.overallScore),
    personalBest:readable('personalBest',r.personalBest),
    nationalAverage:readable('nationalAverage',r.nationalAverage),
    heartBonus:bonus,
    ranking,metrics,techniques,vibrato,
    scoringDate:{status:'unavailable'},
    scoringPerformedAt:r.scoringPerformedAt||null
  };
}
function e3StructuredUserReviewStatus(st) {
  return st&&st.userReview&&st.userReview.status
    ? st.userReview.status
    : (st&&st.extraction&&st.extraction.userReview)||'unknown';
}
function e3StructuredImageShaList(st) {
  if (!st||!st.sourceEvidence) return [];
  if (Array.isArray(st.sourceEvidence.images)) return st.sourceEvidence.images.map(x=>x&&x.sha256).filter(Boolean);
  return st.sourceEvidence.sha256?[st.sourceEvidence.sha256]:[];
}
function e3OutcomeComparison(descA, descB, pairContext = null, chronology = null, conditionsOverride = null) {
  const stA = descA && descA.evaluationEvidence && descA.evaluationEvidence.structuredScoringResult || { status: 'unavailable' };
  const stB = descB && descB.evaluationEvidence && descB.evaluationEvidence.structuredScoringResult || { status: 'unavailable' };
  const verifiedA = e3StructuredIsSourceVerified(stA), verifiedB = e3StructuredIsSourceVerified(stB);
  const resultA=verifiedA?e3AdaptStructuredResultForComparison(stA):{};
  const resultB=verifiedB?e3AdaptStructuredResultForComparison(stB):{};
  const conditions = conditionsOverride || e3StrictScoringConditionComparability(descA, descB, pairContext);
  const resolvedChronology = chronology || e4ResolveChronology(descA, descB, pairContext);

  let status = 'requires_structured_evaluations';
  if (verifiedA && verifiedB) {
    if (conditions.overallStatus === 'confirmed_match' || conditions.overallStatus === 'confirmed_match_by_pair_report') status = 'pairwise_outcome_observation_comparable';
    else if (conditions.overallStatus === 'confirmed_difference_present' || conditions.overallStatus === 'confirmed_difference_present_by_pair_report') status = 'pairwise_outcome_observation_conditions_differ';
    else if (conditions.overallStatus === 'conflict_pair_report_vs_recording_metadata') status = 'pairwise_outcome_observation_condition_evidence_conflict';
    else status = 'pairwise_outcome_observation_available_comparability_not_established';
  } else if (verifiedA || verifiedB) status = 'waiting_for_second_structured_evaluation';

  const metricsA = e3ArrayMap(resultA, 'metrics', 'value');
  const metricsB = e3ArrayMap(resultB, 'metrics', 'value');
  const metrics = e3UnionKeys(metricsA, metricsB).map(key => {
    const a = metricsA.get(key), b = metricsB.get(key);
    return e3NumericPair(key, (a && a.label) || (b && b.label) || key,
      a ? a.value : null, b ? b.value : null, (a && a.unit) || (b && b.unit) || null,
      'external_scoring_metric', 'metric_specific_not_assumed');
  });

  const techA = e3ArrayMap(resultA, 'techniques', 'count');
  const techB = e3ArrayMap(resultB, 'techniques', 'count');
  const techniques = e3UnionKeys(techA, techB).map(key => {
    const a = techA.get(key), b = techB.get(key);
    return e3NumericPair(key, (a && a.label) || (b && b.label) || key,
      a ? a.value : null, b ? b.value : null, 'count',
      'technique_occurrence_count', 'non_monotonic');
  });

  const vibA = resultA.vibrato && resultA.vibrato.status === 'readable' ? resultA.vibrato : null;
  const vibB = resultB.vibrato && resultB.vibrato.status === 'readable' ? resultB.vibrato : null;
  const typeA = vibA && vibA.type ? String(vibA.type) : null;
  const typeB = vibB && vibB.type ? String(vibB.type) : null;
  const typeStatus = typeA && typeB ? (typeA === typeB ? 'same_value' : 'different_value') : (typeA || typeB ? 'available_one_side' : 'unavailable');

  const rankingA = resultA.ranking && resultA.ranking.status === 'readable' ? resultA.ranking : null;
  const rankingB = resultB.ranking && resultB.ranking.status === 'readable' ? resultB.ranking : null;
  const progressionObservation = e4ProgressionObservation(descA, descB, resultA, resultB, verifiedA, verifiedB, resolvedChronology, conditions);

  return {
    schemaVersion: 'songscope-outcome-comparison-v2',
    status,
    chronology: resolvedChronology,
    progressionObservation,
    sourceEvidence: {
      a: {
        recordingId: descA && descA.recordingId || null,
        structuredStatus: stA.status || 'unavailable',
        verificationStatus: stA.verification && stA.verification.status || 'unavailable',
        scoringImageSha256: e3StructuredImageShaList(stA).length===1?e3StructuredImageShaList(stA)[0]:null,
        scoringImageSha256s:e3StructuredImageShaList(stA),
        userReview:e3StructuredUserReviewStatus(stA)
      },
      b: {
        recordingId: descB && descB.recordingId || null,
        structuredStatus: stB.status || 'unavailable',
        verificationStatus: stB.verification && stB.verification.status || 'unavailable',
        scoringImageSha256: e3StructuredImageShaList(stB).length===1?e3StructuredImageShaList(stB)[0]:null,
        scoringImageSha256s:e3StructuredImageShaList(stB),
        userReview:e3StructuredUserReviewStatus(stB)
      }
    },
    scoringConditionComparability: conditions,
    outcomeObservations: {
      overallScore: e3NumericPair('overall_score', '総合点', e3ReadableNumber(resultA.overallScore), e3ReadableNumber(resultB.overallScore), 'points', 'overall_external_score', 'higher_score_is_higher_external_outcome_only'),
      heartBonus: e3NumericPair('heart_bonus', 'ハートボーナス', e3ReadableNumber(resultA.heartBonus), e3ReadableNumber(resultB.heartBonus), 'points', 'external_score_component', 'descriptive_only'),
      metrics,
      techniques,
      vibrato: {
        totalDurationSec: e3NumericPair('vibrato_total_duration_sec', 'ビブラート合計時間', vibA && isFinite(Number(vibA.totalDurationSec)) ? Number(vibA.totalDurationSec) : null, vibB && isFinite(Number(vibB.totalDurationSec)) ? Number(vibB.totalDurationSec) : null, 'seconds', 'technique_measurement', 'non_monotonic'),
        count: e3NumericPair('vibrato_count', 'ビブラート回数', vibA && isFinite(Number(vibA.count)) ? Number(vibA.count) : null, vibB && isFinite(Number(vibB.count)) ? Number(vibB.count) : null, 'count', 'technique_occurrence_count', 'non_monotonic'),
        type: { status: typeStatus, a: typeA, b: typeB, interpretation: 'Categorical observation only; a type change is not automatically better or worse.' }
      }
    },
    contextualEvidence: {
      nationalAverage: e3NumericPair('national_average', '全国平均', e3ReadableNumber(resultA.nationalAverage), e3ReadableNumber(resultB.nationalAverage), 'points', 'population_context', 'context_only'),
      ranking: {
        status: rankingA && rankingB ? 'available_both' : (rankingA || rankingB ? 'available_one_side' : 'unavailable'),
        a: rankingA ? { position: Number(rankingA.position), total: Number(rankingA.total) } : null,
        b: rankingB ? { position: Number(rankingB.position), total: Number(rankingB.total) } : null,
        deltaNotComputed: true,
        note: 'Ranking denominator/cohort may differ, so a raw rank delta is not produced.'
      },
      scoringDate: {
        status: resultA.scoringDate && resultB.scoringDate ? 'available_both' : (resultA.scoringDate || resultB.scoringDate ? 'available_one_side' : 'unavailable'),
        a: resultA.scoringDate && resultA.scoringDate.value || null,
        b: resultB.scoringDate && resultB.scoringDate.value || null
      }
    },
    interpretationGuardrails: [
      'This file compares preserved external scoring outcomes; it does not label overall singing improvement.',
      'A positive score delta is an external outcome increase, not proof of a specific acoustic improvement or cause.',
      'Technique-count increases/decreases are non-monotonic and must not be ranked as better/worse by count alone.',
      'Field comparisons require source-verified structured evaluations. Missing values remain missing.',
      'Scoring-condition comparability is separate from source verification and is not inferred from equal unconfirmed stored metadata.',
      'SongScope mixed-audio F0/RMS observations remain separate evidence and are not used to explain score deltas automatically.',
      'Phase E4 separates A/B direction from earlier→later chronology; progression deltas are produced only when chronology is established.'
    ]
  };
}


/* =====================================================================
 * Phase F1: same-song history / progression evidence
 *
 * 同じsongIdのrecordingだけを履歴単位として束ねる。
 * analysisHistoryの再解析runは「別歌唱」として数えない。
 * chronological orderは証拠制約から解き、曖昧/矛盾時は無理に並べない。
 * ===================================================================== */
function f1DescriptorFromStored(rec,an,asset,audioIdentity,scoringEvidenceContext) {
  rec = rec || {}; an = an || {}; asset = asset || {}; audioIdentity = audioIdentity || {};
  const effectiveSha = audioIdentity.sha256 || rec.audioSha256 || an.audioSha256 || null;
  return {
    recordingId: rec.recordingId || null,
    audioSha256: effectiveSha,
    audioIdentityEvidence: {
      status: effectiveSha ? 'exact_sha256_available' : 'identity_unresolved',
      sha256: effectiveSha,
      source: audioIdentity.source || (rec.audioSha256 ? 'recording_metadata' : (an.audioSha256 ? 'latest_analysis' : 'unavailable')),
      storedRecordingAudioSha256: rec.audioSha256 || null,
      latestAnalysisAudioSha256: an.audioSha256 || null,
      storedAudioBlobPresent: !!(asset && asset.blob),
      hashComputationError: audioIdentity.hashComputationError || null,
      note: effectiveSha
        ? 'Exact raw-file SHA-256 is available for physical-recording identity resolution.'
        : 'No exact raw-file SHA-256 could be established. This legacy record is not counted as a physical singing performance in F1 trend readiness.'
    },
    songId: rec.songId || null,
    songIdentityKey: rec.songIdentityKey || null,
    songIdentityBasis: rec.songIdentityBasis || null,
    recordingIdentityBasis: rec.recordingIdentityBasis || null,
    title: rec.title || '',
    artist: rec.artist || '',
    recordedAt: rec.recordedAt || null,
    recordedDate: rec.recordedDate || null,
    durationSec: isFinite(Number(rec.durationSec)) ? Number(rec.durationSec) : null,
    analysisId: an.analysisId || rec.latestAnalysisId || null,
    analysisCount: isFinite(Number(rec.analysisCount)) ? Number(rec.analysisCount) : null,
    userMetadata: {
      damScore: rec.damScore || null,
      keyChange: rec.keyChange || null,
      octave: rec.octave || null,
      device: rec.device || null,
      scoringMode: rec.scoringMode || null,
      recordingSetupPreset: rec.recordingSetupPreset || null,
      source: 'recording_metadata'
    },
    metadataProvenance: normalizedMetadataProvenance(rec),
    evaluationEvidence:Object.assign(
      {consumerSource:'scoringEvidenceSets',legacyRecordingAttachedFieldsIgnored:true},
      recordingScoringEvidenceDescriptor(rec,scoringEvidenceContext)
    )
  };
}
async function f1LoadDescriptorsForSong(songId) {
  const recs = await findRecordingsBySongId(songId);
  const out = [];
  for (const rec of recs) {
    const an = await dbGet('analysis', rec.recordingId).catch(() => null);
    const asset = await dbGet('audio', rec.recordingId).catch(() => null);
    let sha = rec.audioSha256 || (an && an.audioSha256) || null;
    let source = rec.audioSha256 ? 'recording_metadata' : ((an && an.audioSha256) ? 'latest_analysis' : 'unavailable');
    let hashComputationError = null;
    // 旧recordingでSHAが未保存でも、raw audio blobが残っていればF1 export時に非破壊で再計算する。
    // ここではrecordings storeへ書き戻さず、physical identity解決の証拠としてのみ使う。
    if (!sha && asset && asset.blob && typeof asset.blob.arrayBuffer === 'function') {
      try {
        sha = await sha256Hex(await asset.blob.arrayBuffer());
        source = 'stored_audio_blob_sha256_computed_at_history_export';
      } catch (e) {
        hashComputationError = (e && e.message) ? String(e.message) : String(e);
      }
    }
    const scoringEvidenceContext=await scoringEvidenceRelationsForRecording(rec.recordingId);
    out.push(f1DescriptorFromStored(rec,an,asset,{sha256:sha,source,hashComputationError},scoringEvidenceContext));
  }
  // このsortは表示/JSON安定化だけ。chronologyの証拠には使わない。
  out.sort((a,b) => String(a.recordingId || '').localeCompare(String(b.recordingId || '')));
  return out;
}
function f1CanonicalDescriptorScore(desc) {
  let score = 0;
  const st = desc && desc.evaluationEvidence && desc.evaluationEvidence.structuredScoringResult;
  const img = desc && desc.evaluationEvidence && desc.evaluationEvidence.scoringResultImage;
  if (e3StructuredIsSourceVerified(st)) score += 1000000;
  if (img && img.status === 'available') score += 100000;
  const prov = desc && desc.metadataProvenance || {};
  for (const k of ['recordedAt','device','scoringMode','keyChange','octave']) {
    if (prov[k] && prov[k].confirmation === 'user_confirmed') score += 10000;
  }
  if (desc && desc.analysisId) score += 1000;
  score += Math.min(999, Math.max(0, Number(desc && desc.analysisCount || 0)));
  return score;
}
function f1VerifiedOutcomeSignature(desc) {
  const st = desc && desc.evaluationEvidence && desc.evaluationEvidence.structuredScoringResult;
  if (!e3StructuredIsSourceVerified(st)) return null;
  return JSON.stringify({
    sourceImageBindings:st.sourceEvidence&&Array.isArray(st.sourceEvidence.images)
      ? st.sourceEvidence.images.map(x=>({imageId:x&&x.imageId||null,sha256:x&&x.sha256||null})).sort((a,b)=>String(a.imageId).localeCompare(String(b.imageId)))
      : [{imageId:null,sha256:st.sourceEvidence&&st.sourceEvidence.sha256||null}],
    result:st.result||null
  });
}
function f1ResolvePhysicalRecordings(descs) {
  const bySha = new Map();
  const unresolved = [];
  for (const d of descs || []) {
    if (!d || !d.audioSha256) { unresolved.push(d); continue; }
    if (!bySha.has(d.audioSha256)) bySha.set(d.audioSha256, []);
    bySha.get(d.audioSha256).push(d);
  }
  const aliasToCanonical = new Map();
  const physical = [];
  let duplicateAliasCount = 0;
  for (const [sha, group0] of bySha.entries()) {
    const group = group0.slice().sort((a,b) => {
      const ds = f1CanonicalDescriptorScore(b) - f1CanonicalDescriptorScore(a);
      return ds || String(a.recordingId || '').localeCompare(String(b.recordingId || ''));
    });
    const canonical = group[0];
    const aliases = group.slice(1);
    duplicateAliasCount += aliases.length;
    for (const d of group) if (d && d.recordingId) aliasToCanonical.set(d.recordingId, canonical.recordingId);
    const verifiedSignatures = Array.from(new Set(group.map(f1VerifiedOutcomeSignature).filter(Boolean)));
    const evidenceConflict = verifiedSignatures.length > 1;
    const resolved = Object.assign({}, canonical, {
      physicalRecordingId: 'phy_' + sha.slice(0, 24),
      physicalIdentity: {
        status: 'resolved_exact_audio_sha256',
        audioSha256: sha,
        canonicalRecordingId: canonical.recordingId,
        sourceRecordingIds: group.map(x => x.recordingId).filter(Boolean),
        aliasRecordingIds: aliases.map(x => x.recordingId).filter(Boolean),
        sourceRecordCount: group.length,
        canonicalSelection: 'evidence_richness_then_analysis_count_then_recording_id_v1',
        verifiedStructuredOutcomeConflict: evidenceConflict,
        note: group.length > 1
          ? 'Multiple legacy recordingIds share the exact same raw audio SHA-256 and count as one physical singing performance.'
          : 'One exact raw audio SHA-256 maps to one physical singing performance for F1 counting.'
      }
    });
    physical.push(resolved);
  }
  physical.sort((a,b) => String(a.recordingId || '').localeCompare(String(b.recordingId || '')));
  return {
    physicalDescriptors: physical,
    aliasToCanonical,
    audit: {
      status: unresolved.length ? 'resolved_with_unresolved_legacy_records' : 'resolved',
      method: 'exact_raw_audio_sha256_v1',
      storedRecordingRecordCount: (descs || []).length,
      physicalRecordingCount: physical.length,
      duplicateAliasRecordCount: duplicateAliasCount,
      unresolvedIdentityRecordCount: unresolved.length,
      physicalRecordings: physical.map(d => ({
        physicalRecordingId: d.physicalRecordingId,
        audioSha256: d.audioSha256,
        canonicalRecordingId: d.recordingId,
        sourceRecordingIds: d.physicalIdentity.sourceRecordingIds,
        aliasRecordingIds: d.physicalIdentity.aliasRecordingIds,
        verifiedStructuredOutcomeConflict: !!d.physicalIdentity.verifiedStructuredOutcomeConflict
      })),
      unresolvedRecords: unresolved.map(d => ({
        recordingId: d && d.recordingId || null,
        title: d && d.title || '',
        recordedAt: d && d.recordedAt || null,
        durationSec: d && d.durationSec !== undefined ? d.durationSec : null,
        analysisCount: d && d.analysisCount !== undefined ? d.analysisCount : null,
        audioIdentityEvidence: d && d.audioIdentityEvidence || null,
        reason: 'exact_audio_sha256_unavailable_after_stored_blob_hash_attempt',
        countedAsPhysicalRecording: false
      })),
      guardrail: 'recordingId alone is not a physical-performance count. Exact duplicate SHA-256 records are canonicalized; unresolved legacy records are preserved for audit but excluded from history/trend readiness.'
    }
  };
}
function f1VerifiedResult(desc) {
  const st = desc && desc.evaluationEvidence && desc.evaluationEvidence.structuredScoringResult;
  return e3StructuredIsSourceVerified(st) && st.result && typeof st.result === 'object' ? st.result : null;
}
function f1OutcomeFromStandaloneScoringV2(st) {
  if (!e3StructuredIsSourceVerified(st)) return null;
  const r=st&&st.result||{};
  const fs=st&&st.fieldStatus||{};
  const readableNumber=(key)=>{
    if (fs&&fs[key]&&fs[key]!=='extracted') return null;
    const n=Number(r[key]); return isFinite(n)?n:null;
  };
  const metrics={};
  const addMetric=(key,label,value,unit,classification,directionality,meta)=>{
    const n=Number(value); if(!isFinite(n)) return;
    metrics[key]={key,label,value:n,unit:unit||null,classification:classification||'external_scoring_metric',directionality:directionality||'metric_specific_not_assumed',meta:meta||null};
  };
  addMetric('pitch_accuracy','音程正確率',readableNumber('pitchAccuracy'),'percent','external_scoring_metric','higher_external_outcome_only');
  addMetric('expression_score','表現力',readableNumber('expressionScore'),'points','external_scoring_metric','higher_external_outcome_only');
  addMetric('dynamics_score','抑揚',readableNumber('dynamicsScore'),'points','external_scoring_metric','higher_external_outcome_only');
  addMetric('listening_score','聴感',readableNumber('listeningScore'),'points','external_scoring_metric','higher_external_outcome_only');
  const discrete=[
    ['longToneSkillDiscrete','long_tone_skill','ロングトーン上手さ','higher_external_outcome_only'],
    ['vibratoSkillDiscrete','vibrato_skill','ビブラート上手さ','higher_external_outcome_only'],
    ['stabilityDiscrete','stability_display','安定性','higher_external_outcome_only']
  ];
  for (const [field,key,label,directionality] of discrete) {
    const x=r[field];
    if (fs&&fs[field]==='extracted'&&x&&isFinite(Number(x.observedLit))&&isFinite(Number(x.observedTotal))) {
      addMetric(key,label,Number(x.observedLit),'lit_count','external_discrete_display',directionality,{observedTotal:Number(x.observedTotal),displayOnly:true});
    }
  }
  const rhythm=r.rhythmDiscrete;
  if (fs&&fs.rhythmDiscrete==='extracted'&&rhythm&&isFinite(Number(rhythm.observedPositionIndex))&&isFinite(Number(rhythm.observedPositionCount))) {
    addMetric('rhythm_position','リズム表示位置',Number(rhythm.observedPositionIndex),'ordinal_position','external_discrete_display','non_monotonic',{
      observedPositionCount:Number(rhythm.observedPositionCount),leftLabel:rhythm.leftLabel||null,rightLabel:rhythm.rightLabel||null,displayOnly:true
    });
  }
  const techniques={};
  if (fs&&fs.techniques==='extracted'&&r.techniques&&typeof r.techniques==='object') {
    const map=[
      ['shakuriCount','shakuri','しゃくり'],['kobushiCount','kobushi','こぶし'],['fallCount','fall','フォール'],
      ['accentCount','accent','アクセント'],['hammeringCount','hammering','ハンマリング']
    ];
    for (const [src,key,label] of map) {
      const n=Number(r.techniques[src]); if(isFinite(n)) techniques[key]={key,label,count:n,unit:'count'};
    }
  }
  let vibrato=null;
  if (fs&&fs.vibrato==='extracted'&&r.vibrato&&typeof r.vibrato==='object') {
    vibrato={
      totalDurationSec:isFinite(Number(r.vibrato.durationSec))?Number(r.vibrato.durationSec):null,
      count:isFinite(Number(r.vibrato.count))?Number(r.vibrato.count):null,
      type:r.vibrato.type?String(r.vibrato.type):null
    };
  }
  const rank=r.ranking&&typeof r.ranking==='object'&&isFinite(Number(r.ranking.rank))&&isFinite(Number(r.ranking.population))
    ? {position:Number(r.ranking.rank),total:Number(r.ranking.population)}:null;
  const bonus=r.bonus&&typeof r.bonus==='object'&&isFinite(Number(r.bonus.value))?Number(r.bonus.value):null;
  const sourceImageSha256s=st.sourceEvidence&&Array.isArray(st.sourceEvidence.images)
    ? st.sourceEvidence.images.map(x=>x&&x.sha256).filter(Boolean):[];
  return {
    status:'source_verified_structured_outcome',
    sourceVerification:'source_verified',
    sourceImageSha256:sourceImageSha256s.length===1?sourceImageSha256s[0]:null,
    sourceImageSha256s,
    userReview:st.userReview&&st.userReview.status||'unknown',
    scoringDate:null,
    scoringPerformedAt:r.scoringPerformedAt||null,
    overallScore:readableNumber('overallScore'),
    personalBest:readableNumber('personalBest'),
    nationalAverage:readableNumber('nationalAverage'),
    heartBonus:bonus,
    ranking:rank,
    metrics,techniques,vibrato,
    fieldStatus:fs,
    evidenceSetId:st.relationship&&st.relationship.evidenceSetId||null,
    bindingAssertionId:st.relationship&&st.relationship.activeBindAssertion&&st.relationship.activeBindAssertion.assertionId||null,
    note:'External DAM scoring observations from a source-verified structured result explicitly bound by the user to this recording. These remain observations, not a causal or durable skill-change claim.'
  };
}
function f1OutcomeObservation(desc) {
  const st=desc&&desc.evaluationEvidence&&desc.evaluationEvidence.structuredScoringResult||{status:'unavailable'};
  if (st.relationship&&st.relationship.status==='legacy_attachment_candidate_unbound') {
    return {
      status:'legacy_attachment_candidate_unbound',
      sourceVerification:st.verification&&st.verification.sourceVerificationBeforeRelationshipCheck||'unavailable',
      sourceImageSha256:null,userReview:st.userReview||'unknown',scoringDate:null,
      overallScore:null,personalBest:null,nationalAverage:null,heartBonus:null,ranking:null,metrics:{},techniques:{},vibrato:null,
      candidateEvidenceSetId:st.relationship.evidenceSetId||null,
      note:'Scoring evidence was migrated from the old recording-attached UI, but same-performance binding has not been explicitly confirmed. Values are preserved for audit but excluded from Observed History numeric series.'
    };
  }
  if (desc && desc.physicalIdentity && desc.physicalIdentity.verifiedStructuredOutcomeConflict) {
    return {
      status: 'duplicate_alias_evidence_conflict',
      sourceVerification: 'conflict',
      sourceImageSha256: null, userReview: 'unknown', scoringDate: null, overallScore: null, nationalAverage: null, heartBonus: null, ranking: null, metrics: {}, techniques: {}, vibrato: null,
      note: 'Multiple source-verified structured outcomes are attached to recordingId aliases of the same exact raw audio. SongScope does not choose one silently for history analysis.'
    };
  }
  if (st&&st.schemaVersion===STANDALONE_SCORING_RESULT_SCHEMA) {
    const v2=f1OutcomeFromStandaloneScoringV2(st);
    if (v2) return v2;
    return {
      status:'structured_outcome_not_eligible',
      sourceVerification:st.verification&&st.verification.status||'unavailable',
      sourceImageSha256:null,
      sourceImageSha256s:e3StructuredImageShaList(st),
      userReview:e3StructuredUserReviewStatus(st),
      scoringDate:null,overallScore:null,personalBest:null,nationalAverage:null,heartBonus:null,ranking:null,metrics:{},techniques:{},vibrato:null,
      evidenceSetId:st.relationship&&st.relationship.evidenceSetId||null,
      eligibility:st.outcomeEligibility||null,
      note:'A current-schema structured scoring result exists, but it is not eligible as a recording outcome under the current binding/source-review rules.'
    };
  }
  const result = f1VerifiedResult(desc);
  const metrics = {};
  const techniques = {};
  if (result) {
    for (const [key,row] of e3ArrayMap(result, 'metrics', 'value')) metrics[key] = { key, label: row.label, value: e3Number(row.value), unit: row.unit || null };
    for (const [key,row] of e3ArrayMap(result, 'techniques', 'count')) techniques[key] = { key, label: row.label, count: e3Number(row.value), unit: 'count' };
  }
  const vib = result && result.vibrato && result.vibrato.status === 'readable' ? result.vibrato : null;
  const rank = result && result.ranking && result.ranking.status === 'readable' ? result.ranking : null;
  return {
    status: result ? 'source_verified_structured_outcome' : 'unavailable_or_unverified',
    sourceVerification: st.verification && st.verification.status || 'unavailable',
    sourceImageSha256: st.sourceEvidence && st.sourceEvidence.sha256 || null,
    userReview: st.extraction && st.extraction.userReview || 'unknown',
    scoringDate: result && result.scoringDate && result.scoringDate.status === 'readable' ? result.scoringDate.value || null : null,
    overallScore: result ? e3ReadableNumber(result.overallScore) : null,
    personalBest: result ? e3ReadableNumber(result.personalBest || result.personalBestScore || result.bestScore) : null,
    nationalAverage: result ? e3ReadableNumber(result.nationalAverage) : null,
    heartBonus: result ? e3ReadableNumber(result.heartBonus) : null,
    ranking: rank ? { position: Number(rank.position), total: Number(rank.total) } : null,
    metrics,
    techniques,
    vibrato: vib ? {
      totalDurationSec: isFinite(Number(vib.totalDurationSec)) ? Number(vib.totalDurationSec) : null,
      count: isFinite(Number(vib.count)) ? Number(vib.count) : null,
      type: vib.type ? String(vib.type) : null
    } : null
  };
}
function f1PushOrderConstraint(map, earlierId, laterId, evidence) {
  if (!earlierId || !laterId || earlierId === laterId) return;
  const key = earlierId + '>' + laterId;
  if (!map.has(key)) map.set(key, { earlierRecordingId: earlierId, laterRecordingId: laterId, evidence: [] });
  map.get(key).evidence.push(evidence);
}
async function f1ChronologyConstraints(descs, aliasToCanonical) {
  const ids = new Set(descs.map(d => d.recordingId).filter(Boolean));
  const canonicalId = id => (aliasToCanonical && aliasToCanonical.get(id)) || id;
  const edgeMap = new Map();
  // R1: pair-level human context is independent from alignmentResults.
  const contexts = await dbAll('pairContexts').catch(() => []);
  for (const pc of contexts) {
    if (pairContextIsCurrentlyInvalidated(pc)) continue;
    const c=pc&&pc.chronology;
    if (!c || c.status !== 'user_confirmed_order') continue;
    const earlierId = canonicalId(c.earlierRecordingId), laterId = canonicalId(c.laterRecordingId);
    if (!ids.has(earlierId) || !ids.has(laterId) || earlierId === laterId) continue;
    f1PushOrderConstraint(edgeMap, earlierId, laterId, {
      source: 'user_pair_confirmation', audioPairKey: pc.audioPairKey || null, confirmedAt: c.confirmedAt || null,
      originalEarlierRecordingId: c.earlierRecordingId || null,
      originalLaterRecordingId: c.laterRecordingId || null,
      identityCanonicalized: earlierId !== c.earlierRecordingId || laterId !== c.laterRecordingId
    });
  }
  for (let i=0; i<descs.length; i++) for (let j=i+1; j<descs.length; j++) {
    const a=descs[i], b=descs[j];
    const pa=a.metadataProvenance && a.metadataProvenance.recordedAt || {};
    const pb=b.metadataProvenance && b.metadataProvenance.recordedAt || {};
    const ta=Date.parse(a.recordedAt || ''), tb=Date.parse(b.recordedAt || '');
    if (pa.confirmation === 'user_confirmed' && pb.confirmation === 'user_confirmed' && isFinite(ta) && isFinite(tb) && ta !== tb) {
      f1PushOrderConstraint(edgeMap, ta < tb ? a.recordingId : b.recordingId, ta < tb ? b.recordingId : a.recordingId, {
        source: 'user_confirmed_recorded_at', aRecordedAt: a.recordedAt, bRecordedAt: b.recordedAt
      });
    }
    // AI extractionの日付は、source bindingだけでは値の確認にならない。
    const da=e4ConfirmedScoringDate(a), db2=e4ConfirmedScoringDate(b);
    if (da && db2 && da.epochDay !== db2.epochDay) {
      f1PushOrderConstraint(edgeMap, da.epochDay < db2.epochDay ? a.recordingId : b.recordingId, da.epochDay < db2.epochDay ? b.recordingId : a.recordingId, {
        source: 'user_reviewed_scoring_date', aScoringDate: da.value, bScoringDate: db2.value,
        resolution: 'calendar_day'
      });
    }
  }
  return Array.from(edgeMap.values());
}
function f1ResolveOrder(descs, constraints) {
  const ids = descs.map(d => d.recordingId).filter(Boolean);
  if (ids.length === 0) return { status: 'no_recordings', uniqueOrder: false, orderedRecordingIds: [], layers: [], constraints };
  if (ids.length === 1) return { status: 'single_recording', uniqueOrder: true, orderedRecordingIds: ids.slice(), layers: [ids.slice()], constraints };
  const out = new Map(ids.map(id => [id, new Set()]));
  const indeg = new Map(ids.map(id => [id, 0]));
  for (const e of constraints) {
    if (!out.has(e.earlierRecordingId) || !out.has(e.laterRecordingId)) continue;
    const s = out.get(e.earlierRecordingId);
    if (!s.has(e.laterRecordingId)) { s.add(e.laterRecordingId); indeg.set(e.laterRecordingId, indeg.get(e.laterRecordingId)+1); }
  }
  const indegWork = new Map(indeg);
  const remaining = new Set(ids);
  const order = [], layers = [];
  let unique = true;
  while (remaining.size) {
    const zeros = Array.from(remaining).filter(id => indegWork.get(id) === 0).sort();
    if (!zeros.length) {
      return {
        status: 'chronology_evidence_conflict_cycle', uniqueOrder: false, orderedRecordingIds: [], layers,
        unresolvedRecordingIds: Array.from(remaining).sort(), constraints,
        note: 'Chronology evidence contains a cycle/conflict. SongScope does not choose which confirmed source to override.'
      };
    }
    layers.push(zeros.slice());
    if (zeros.length !== 1) unique = false;
    for (const id of zeros) {
      order.push(id); remaining.delete(id);
      for (const to of out.get(id)) indegWork.set(to, indegWork.get(to)-1);
    }
  }
  return {
    status: unique ? 'fully_ordered' : 'partially_ordered',
    uniqueOrder: unique,
    orderedRecordingIds: unique ? order : [],
    topologicalCandidateOrder: order,
    layers,
    constraints,
    note: unique ? 'A unique evidence-compatible total order exists.' : 'Multiple evidence-compatible orders remain; no single chronology is asserted.'
  };
}
async function f1PairContextFor(descA, descB) {
  const ha=descA && descA.audioSha256, hb=descB && descB.audioSha256;
  if (!ha || !hb) return null;
  const audioPairKey = comparisonAudioPairKey(ha, hb);
  const identity={
    audioPairKey,
    pairKey:alignmentPairKey(ha,hb),
    a:{recordingId:descA.recordingId,audioSha256:ha,title:descA.title||''},
    b:{recordingId:descB.recordingId,audioSha256:hb,title:descB.title||''}
  };
  const ctx=await getComparisonContextForIdentity(identity);
  if (!pairContextIsCurrentlyInvalidated(ctx)) return ctx;
  return Object.assign({},ctx,{
    chronology:{status:'unknown',source:'invalidated_by_recording_deletion'},
    scoringConditions:{status:'unknown',source:'invalidated_by_recording_deletion',coveredFields:SCORING_CONDITION_FIELDS.slice()}
  });
}
async function f1ScoringConditionChain(orderedDescs) {
  if (!orderedDescs || orderedDescs.length < 2) return { status: 'not_applicable', adjacentPairs: [] };
  const adjacentPairs=[];
  for (let i=0;i<orderedDescs.length-1;i++) {
    const earlier=orderedDescs[i], later=orderedDescs[i+1];
    const ctx=await f1PairContextFor(earlier,later);
    const cmp=e3StrictScoringConditionComparability(earlier,later,ctx);
    adjacentPairs.push({ earlierRecordingId: earlier.recordingId, laterRecordingId: later.recordingId, comparability: cmp });
  }
  const sts=adjacentPairs.map(x=>x.comparability.overallStatus);
  let status='not_established';
  if (sts.some(x=>x==='conflict_pair_report_vs_recording_metadata')) status='evidence_conflict';
  else if (sts.some(x=>x==='confirmed_difference_present'||x==='confirmed_difference_present_by_pair_report')) status='conditions_differ_in_chain';
  else if (sts.every(x=>x==='confirmed_match'||x==='confirmed_match_by_pair_report')) status='comparable_chain';
  return {
    status,
    coveredFields:['device','scoringMode','keyChange','octave'],
    adjacentPairs,
    note:'History-wide comparability requires every adjacent step in the established chronology to have matching confirmed scoring conditions. This does not assert identical room, microphone placement, or singer state.'
  };
}
function f1FlatNumericOutcome(obs) {
  const out = new Map();
  const add=(key,label,value,unit,classification,directionality)=>{
    const n=Number(value); if(!isFinite(n)) return;
    out.set(key,{key,label,value:+n.toFixed(6),unit:unit||null,classification,directionality});
  };
  if (!obs || obs.status !== 'source_verified_structured_outcome') return out;
  add('overall_score','総合点',obs.overallScore,'points','overall_external_score','higher_external_outcome_only');
  add('heart_bonus','ハートボーナス',obs.heartBonus,'points','external_score_component','descriptive_only');
  for (const key of Object.keys(obs.metrics||{})) {
    const x=obs.metrics[key];
    add('metric:'+key,x.label||key,x.value,x.unit||null,x.classification||'external_scoring_metric',x.directionality||'metric_specific_not_assumed');
  }
  for (const key of Object.keys(obs.techniques||{})) {
    const x=obs.techniques[key]; add('technique:'+key,x.label||key,x.count,'count','technique_occurrence_count','non_monotonic');
  }
  if (obs.vibrato) {
    add('vibrato:duration','ビブラート合計時間',obs.vibrato.totalDurationSec,'seconds','technique_measurement','non_monotonic');
    add('vibrato:count','ビブラート回数',obs.vibrato.count,'count','technique_occurrence_count','non_monotonic');
  }
  return out;
}
function f1SeriesForMetric(key, label, unit, classification, directionality, orderedRows, conditionChain) {
  const points=orderedRows.map((r,i)=>{
    const m=f1FlatNumericOutcome(r.outcome).get(key);
    return { chronologyIndex:i+1, recordingId:r.recording.recordingId, title:r.recording.title||'', value:m?m.value:null };
  });
  const steps=[];
  for(let i=0;i<points.length-1;i++) {
    const a=points[i], b=points[i+1];
    const pairCmp=conditionChain && conditionChain.adjacentPairs && conditionChain.adjacentPairs[i] ? conditionChain.adjacentPairs[i].comparability.overallStatus : 'not_established';
    steps.push({
      earlierRecordingId:a.recordingId,laterRecordingId:b.recordingId,
      earlier:a.value,later:b.value,
      deltaLaterMinusEarlier:a.value!==null&&b.value!==null?+((b.value-a.value).toFixed(6)):null,
      scoringConditionComparability:pairCmp
    });
  }
  const nonNull=points.filter(p=>p.value!==null);
  let patternStatus='insufficient_history_for_pattern', observedDirectionPattern=null, evidenceTier='insufficient';
  const allValuesPresent = nonNull.length===points.length;
  if (points.length>=3 && allValuesPresent && conditionChain && conditionChain.status==='comparable_chain') {
    const ds=steps.map(s=>s.deltaLaterMinusEarlier).filter(x=>x!==null);
    const eps=1e-6;
    if (ds.length===points.length-1) {
      if (directionality === 'non_monotonic') {
        patternStatus='non_monotonic_descriptive_sequence';
        evidenceTier=points.length>=5?'repeated_observation_5_plus':'exploratory_3_to_4_recordings';
      } else {
        if (ds.every(x=>x>eps)) observedDirectionPattern='all_observed_steps_higher';
        else if (ds.every(x=>x<-eps)) observedDirectionPattern='all_observed_steps_lower';
        else if (ds.every(x=>Math.abs(x)<=eps)) observedDirectionPattern='all_observed_steps_same';
        else observedDirectionPattern='mixed_direction';
        evidenceTier=points.length>=5?'repeated_observation_5_plus':'exploratory_3_to_4_recordings';
        patternStatus=points.length>=5?'repeated_observation_pattern_available':'exploratory_pattern_available';
      }
    }
  } else if (points.length>=3 && (!conditionChain || conditionChain.status!=='comparable_chain')) {
    patternStatus='scoring_conditions_not_comparable_across_history';
  } else if (points.length>=3 && !allValuesPresent) patternStatus='missing_metric_values_in_history';
  return {
    key,label,unit,classification,directionality,points,adjacentSteps:steps,
    patternStatus,observedDirectionPattern,evidenceTier,
    interpretation:'History of external outcome observations only. Direction consistency does not by itself establish durable singing-skill improvement or deterioration.'
  };
}
function f1BuildSeries(orderedRows, conditionChain) {
  const union=new Map();
  for(const r of orderedRows) for(const [key,m] of f1FlatNumericOutcome(r.outcome)) if(!union.has(key)) union.set(key,m);
  return Array.from(union.values()).sort((a,b)=>a.key.localeCompare(b.key)).map(m=>f1SeriesForMetric(m.key,m.label,m.unit,m.classification,m.directionality,orderedRows,conditionChain));
}
function f1HistoryCsv(pkg) {
  const rows=pkg.recordings || [];
  const metricKeys=new Set(), techKeys=new Set();
  for(const r of rows){
    Object.keys((r.outcome&&r.outcome.metrics)||{}).forEach(k=>metricKeys.add(k));
    Object.keys((r.outcome&&r.outcome.techniques)||{}).forEach(k=>techKeys.add(k));
  }
  const mks=Array.from(metricKeys).sort(), tks=Array.from(techKeys).sort();
  const head=['chronology_index','physical_recording_id','recording_id','alias_recording_ids','audio_sha256','audio_identity_source','title','recorded_at','recorded_at_confirmation','structured_outcome_status','scoring_date','overall_score','personal_best','national_average','heart_bonus',...mks.map(k=>'metric_'+k),...tks.map(k=>'technique_'+k+'_count'),'vibrato_duration_sec','vibrato_count','vibrato_type'];
  const out=[head.join(',')];
  for(const row of rows){
    const o=row.outcome||{}, p=row.recording.metadataProvenance&&row.recording.metadataProvenance.recordedAt||{};
    const vals=[row.chronologyIndex||'',row.recording.physicalRecordingId||'',row.recording.recordingId,(row.recording.physicalIdentity&&row.recording.physicalIdentity.aliasRecordingIds||[]).join('|'),row.recording.audioSha256||'',row.recording.audioIdentityEvidence&&row.recording.audioIdentityEvidence.source||'',row.recording.title,row.recording.recordedAt||'',p.confirmation||'unknown',o.status,o.scoringDate||'',o.overallScore,o.personalBest,o.nationalAverage,o.heartBonus,
      ...mks.map(k=>o.metrics&&o.metrics[k]?o.metrics[k].value:''),...tks.map(k=>o.techniques&&o.techniques[k]?o.techniques[k].count:''),
      o.vibrato&&o.vibrato.totalDurationSec,o.vibrato&&o.vibrato.count,o.vibrato&&o.vibrato.type];
    out.push(vals.map(v=>v===null||v===undefined?'':csvEscape(v)).join(','));
  }
  return out.join('\n');
}
async function buildF1HistoryPackage() {
  const a=cmp.a&&cmp.a.rec, b=cmp.b&&cmp.b.rec;
  const base=a||b;
  if(!base) throw new Error('AまたはBに履歴対象の録音を選択してください');
  if(!base.songId) throw new Error('選択録音にsongIdがありません');
  if(a&&b&&a.songId&&b.songId&&a.songId!==b.songId) throw new Error('A/BのsongIdが異なります。履歴は同じ曲グループだけを対象にします');
  const storedDescs=await f1LoadDescriptorsForSong(base.songId);
  if(!storedDescs.length) throw new Error('このsongIdの録音が見つかりません');
  const identityResolution=f1ResolvePhysicalRecordings(storedDescs);
  const descs=identityResolution.physicalDescriptors;
  if(!descs.length) throw new Error('exact audio SHA-256を確認できるphysical recordingがありません。旧録音のraw audioが残っているか確認してください');
  const constraints=await f1ChronologyConstraints(descs, identityResolution.aliasToCanonical);
  const chronology=f1ResolveOrder(descs,constraints);
  const byId=new Map(descs.map(d=>[d.recordingId,d]));
  const stable=descs.slice();
  const orderedDescs=chronology.status==='fully_ordered'?chronology.orderedRecordingIds.map(id=>byId.get(id)).filter(Boolean):[];
  const conditionChain=chronology.status==='fully_ordered'?await f1ScoringConditionChain(orderedDescs):{status:'chronology_not_fully_ordered',adjacentPairs:[]};
  const rowOrder=chronology.status==='fully_ordered'?orderedDescs:stable;
  const recordings=rowOrder.map((d,i)=>({ chronologyIndex:chronology.status==='fully_ordered'?i+1:null, recording:d, outcome:f1OutcomeObservation(d) }));
  const verifiedCount=recordings.filter(r=>r.outcome.status==='source_verified_structured_outcome').length;
  const legacyUnboundCandidateCount=recordings.filter(r=>r.outcome.status==='legacy_attachment_candidate_unbound').length;
  // Completeness assessment may use ONLY eligible, source-verified bound outcomes.
  // Absence of eligible evidence is NOT evidence that no missing take exists.
  const completenessEligible=recordings.filter(r=>r.outcome&&r.outcome.status==='source_verified_structured_outcome');
  const observedScores=completenessEligible.map(r=>r.outcome&&r.outcome.overallScore).filter(v=>v!==null&&v!==undefined&&isFinite(Number(v))).map(Number);
  const personalBests=completenessEligible.map(r=>r.outcome&&r.outcome.personalBest).filter(v=>v!==null&&v!==undefined&&isFinite(Number(v))).map(Number);
  const observedMax=observedScores.length?Math.max(...observedScores):null;
  const personalBestMax=personalBests.length?Math.max(...personalBests):null;
  let completenessAssessmentStatus='assessable';
  let completenessSignalStatus='no_missing_take_signal_from_personal_best';
  let completenessReason='Eligible source-verified personalBest and observed overallScore are available.';
  if (!personalBests.length) {
    completenessAssessmentStatus='not_assessable_no_eligible_personal_best_evidence';
    completenessSignalStatus='not_assessed';
    completenessReason='No eligible source-verified personalBest evidence is available under the current binding rules.';
  } else if (!observedScores.length) {
    completenessAssessmentStatus='not_assessable_no_eligible_observed_score';
    completenessSignalStatus='not_assessed';
    completenessReason='No eligible source-verified observed overallScore is available for comparison with personalBest.';
  } else if (personalBestMax>observedMax+0.001) {
    completenessSignalStatus='may_omit_unrecorded_takes';
    completenessReason='The highest eligible source-verified personalBest exceeds the highest eligible SongScope-observed overallScore.';
  }
  const historyCompleteness={
    status:completenessAssessmentStatus==='assessable'?completenessSignalStatus:completenessAssessmentStatus,
    assessmentStatus:completenessAssessmentStatus,
    signalStatus:completenessSignalStatus,
    reason:completenessReason,
    observedRecordingCount:descs.length,
    eligibleSourceVerifiedOutcomeCount:completenessEligible.length,
    eligibleObservedScoreCount:observedScores.length,
    eligiblePersonalBestCount:personalBests.length,
    observedMaxOverallScore:observedMax,
    maxReadablePersonalBest:personalBestMax,
    knownEvidencePolicy:{
      onlyEligibleBoundSourceVerifiedOutcomesUsedForThisAssessment:true,
      unboundOrLegacyCandidateEvidenceExcluded:true,
      exclusionDoesNotMeanEvidenceIsFalse:true,
      note:'Known or preserved evidence outside the eligible bound outcome set may still indicate missing real-world takes, but this assessment does not silently import it across an unconfirmed relationship. Such evidence must be represented in an appropriate independent history/completeness evidence layer before use.'
    },
    note:'SongScope counts observed/imported physical recordings, not every real-world singing attempt. not_assessable means the system lacks eligible evidence to evaluate completeness; it never means the history is complete.'
  };
  let readiness='insufficient_history_for_pattern';
  if(chronology.status!=='fully_ordered') readiness='chronology_not_fully_ordered';
  else if(descs.length>=3 && verifiedCount<3) readiness='insufficient_source_verified_outcomes';
  else if(descs.length>=3 && conditionChain.status!=='comparable_chain') readiness='scoring_conditions_not_comparable_across_history';
  else if(descs.length>=5 && verifiedCount===descs.length) readiness='repeated_observation_pattern_available';
  else if(descs.length>=3 && verifiedCount===descs.length) readiness='exploratory_pattern_available';
  const series=chronology.status==='fully_ordered'?f1BuildSeries(recordings,conditionChain):[];
  return {
    schemaVersion:'songscope-history-0.4.0',
    packageType:'same_song_compact_history_evidence',
    generatedAt:nowIso(),appVersion:APP_VERSION,buildId:BUILD_ID,
    song:{
      songId:base.songId,
      representativeTitle:base.title||'',representativeArtist:base.artist||'',
      recordingCount:descs.length,
      physicalRecordingCount:descs.length,
      storedRecordingRecordCount:storedDescs.length,
      duplicateAliasRecordCount:identityResolution.audit.duplicateAliasRecordCount,
      unresolvedIdentityRecordCount:identityResolution.audit.unresolvedIdentityRecordCount,
      note:'recordingCount is the number of exact-SHA-resolved physical recordings, not the number of legacy recordingId rows. Different display titles may still belong to this manually/explicitly grouped song.'
    },
    identityResolution: identityResolution.audit,
    chronology,
    scoringConditionChain:conditionChain,
    historyCompleteness,
    patternReadiness:{
      status:readiness,
      recordingCount:descs.length,
      physicalRecordingCount:descs.length,
      storedRecordingRecordCount:storedDescs.length,
      unresolvedIdentityRecordCount:identityResolution.audit.unresolvedIdentityRecordCount,
      sourceVerifiedStructuredOutcomeCount:verifiedCount,
      legacyUnboundCandidateOutcomeCount:legacyUnboundCandidateCount,
      minimumOrderedComparableRecordingsForExploratoryPattern:3,
      minimumOrderedComparableRecordingsForRepeatedObservationPattern:5,
      note:descs.length<3?'Two recordings can show a pair difference but cannot separate a repeated pattern from take-to-take variation.': 'Pattern labels remain descriptive evidence, not proof of durable skill improvement.'
    },
    recordings,
    outcomeSeries:series,
    exportPolicy:{
      compactHistory:true,includesAudio:false,includesScoringImages:false,includesFrameLevelAcoustics:false,
      note:'F1 is a compact history package. Source image SHA/provenance is retained, while raw images/audio and D2 frame windows stay in single-recording/pair packages for targeted audit.'
    },
    interpretationGuardrails:[
      'F1 physical-performance counting uses exact raw audio SHA-256, not recordingId count. Legacy recordingId aliases with the same SHA-256 count once; analysisHistory re-runs also do not count as new singing performances.',
      'Legacy records without a recoverable exact audio SHA-256 are preserved in identityResolution.unresolvedRecords but excluded from physical recording count and trend readiness.',
      'No chronology is inferred from title suffixes, A/B selection order, or unverified timestamps.',
      'A two-take difference is not a trend. At least three fully ordered, source-verified, scoring-condition-comparable recordings are required even for an exploratory direction pattern.',
      'Five or more such recordings permit a repeated-observation pattern label, but still do not prove durable singing skill change or causation.',
      'Technique counts and vibrato quantity are non-monotonic observations; more or less is not automatically better.',
      'Migrated legacy recording-attached scoring evidence remains candidate-only and is excluded from numeric outcome series until explicit same-performance binding exists.',
      'F1 does not aggregate mixed-audio D2/F0 observations yet; those remain separate evidence.'
    ]
  };
}
async function exportF1HistoryPackage() {
  const btn=$('#btn-f1-export'); if(btn)btn.disabled=true;
  const note=$('#cmp-f1-result');
  try{
    if(note)note.innerHTML='<p class="small">同じsongIdの録音・評価証拠・E4 chronology制約を集約しています…</p>';
    const pkg=await buildF1HistoryPackage();
    const files=[
      {name:'song_history.json',data:JSON.stringify(pkg,null,2)},
      {name:'history_identity_resolution.json',data:JSON.stringify({song:pkg.song,identityResolution:pkg.identityResolution},null,2)},
      {name:'history_chronology.json',data:JSON.stringify({song:pkg.song,chronology:pkg.chronology,scoringConditionChain:pkg.scoringConditionChain,patternReadiness:pkg.patternReadiness},null,2)},
      {name:'history_outcomes.csv',data:f1HistoryCsv(pkg)}
    ];
    const blob=SongScopeZip.createZip(files);
    const stamp=new Date().toISOString().replace(/[-:]/g,'').slice(0,15);
    const name=`songscope_history_${safeName(pkg.song.representativeTitle||'song')}_${stamp}.zip`;
    const how=await saveBlob(blob,name);
    if(note)note.innerHTML=`<p><b>F1曲履歴パッケージを書き出しました</b></p><p class="small mono">physical recordings ${pkg.song.recordingCount} / stored rows ${pkg.song.storedRecordingRecordCount} / duplicate aliases ${pkg.song.duplicateAliasRecordCount} / unresolved ${pkg.song.unresolvedIdentityRecordCount}</p><p class="small mono">chronology ${escapeHtml(pkg.chronology.status)} / verified outcomes ${pkg.patternReadiness.sourceVerifiedStructuredOutcomeCount}</p><p class="small">pattern readiness: <b>${escapeHtml(pkg.patternReadiness.status)}</b>。recordingIdの重複はexact audio SHA-256で正規化し、SHA不明の旧recordはtrend件数から除外します。</p>`;
    if(how!=='cancelled')toast(`${name}を書き出しました`);
  }catch(e){
    console.error(e); if(note)note.innerHTML=`<p class="small">F1生成に失敗しました: ${escapeHtml((e&&e.message)||String(e))}</p>`; toast('F1曲履歴パッケージを作成できませんでした');
  }finally{if(btn)btn.disabled=false;}
}


/* =====================================================================
 * Audit R2: observed-direction history summary
 *
 * F1のphysical recording / chronology / scoring-condition chainを入力証拠とする。
 * ここで作るのは「時系列に並んだ観測テイクで、外部評価値がどう動いたか」
 * の圧縮表現だけ。trend / signal / improvement / deterioration を判定しない。
 * 3件/5件は証拠量の表示であり、統計的な格付けではない。
 * mixed-audio F0/RMS はPractice/Hypothesis入力から明示的に除外する。
 * ===================================================================== */
function f2DisplayResolution(series) {
  const key=String(series&&series.key||'');
  // This is screen/display granularity, NOT a minimum meaningful singing-skill change.
  if (key==='overall_score') return {step:0.001,basis:'DAM overall score is displayed to 0.001 point',semantic:'display_granularity_only'};
  if (key==='heart_bonus') return {step:0.001,basis:'DAM Heart bonus is displayed to 0.001 point',semantic:'display_granularity_only'};
  if (key.startsWith('metric:')) return {step:1,basis:'Current supported DAM subscore/accuracy fields are displayed as integer points or percent',semantic:'display_granularity_only'};
  if (key.startsWith('technique:')) return {step:1,basis:'Technique occurrence count is displayed as an integer count',semantic:'display_granularity_only'};
  if (key==='vibrato:duration') return {step:1,basis:'Current supported DAM vibrato duration display is integer seconds',semantic:'display_granularity_only'};
  if (key==='vibrato:count') return {step:1,basis:'Vibrato count is displayed as an integer count',semantic:'display_granularity_only'};
  return {step:null,basis:'display resolution not declared for this field',semantic:'unknown'};
}
function f2DirectionFromDelta(delta,displayResolution) {
  // Missing is missing. Never allow Number(null) / Number('') to become an observed zero-delta.
  if (delta===null || delta===undefined || delta==='') return 'unknown';
  const n=Number(delta);
  if(!Number.isFinite(n)) return 'unknown';
  const step=Number(displayResolution&&displayResolution.step);
  // Only absorb floating-point noise far below one display step. A one-step change remains a real observed display change.
  const eps=Number.isFinite(step)&&step>0?Math.max(1e-9,step*1e-6):1e-6;
  if(n>eps) return 'higher';
  if(n<-eps) return 'lower';
  return 'same';
}
function f2DirectionCounts(directions) {
  const out={higher:0,lower:0,same:0,unknown:0};
  for(const d of directions||[]) {
    if(d==='higher'||d==='lower'||d==='same') out[d]++;
    else out.unknown++;
  }
  return out;
}
function f2LongestDirectionRun(directions) {
  let best={direction:null,length:0,startStepIndex:null,endStepIndex:null};
  let cur=null, start=0;
  const ds=directions||[];
  for(let i=0;i<ds.length;i++) {
    const d=ds[i];
    if(d!=='higher'&&d!=='lower'&&d!=='same') { cur=null; continue; }
    if(cur!==d) { cur=d; start=i; }
    const len=i-start+1;
    if(len>best.length) best={direction:d,length:len,startStepIndex:start+1,endStepIndex:i+1};
  }
  return best;
}
function f2MetricPattern(series,evidenceVolume) {
  const points=(series&&series.points)||[];
  const steps=(series&&series.adjacentSteps)||[];
  const displayResolution=f2DisplayResolution(series);
  const values=points.map(p=>p&&p.value!==undefined?p.value:null);
  const allValuesPresent=values.length>0&&values.every(v=>v!==null&&v!==undefined&&isFinite(Number(v)));
  const directions=steps.map(s=>f2DirectionFromDelta(s&&s.deltaLaterMinusEarlier,displayResolution));
  const counts=f2DirectionCounts(directions);
  const longestRun=f2LongestDirectionRun(directions);
  const completeDirections=directions.length===Math.max(0,points.length-1)
    && directions.every(d=>d==='higher'||d==='lower'||d==='same');
  const nonSameDirections=directions.filter(d=>d==='higher'||d==='lower');
  const uniqueNonSame=Array.from(new Set(nonSameDirections));
  const allAdjacentDirectionalSame = completeDirections && directions.length>=2 && directions.every(d=>d==='higher'||d==='lower') && uniqueNonSame.length===1;
  const directionality=series.directionality||null;
  const directionalSummaryEligible = directionality!=='non_monotonic' && directionality!=='descriptive_only';
  let status='not_ready';
  let consistentObservedDirection=null;
  let eligibleForDirectionalSummary=false;
  if(points.length<3) status='waiting_for_third_observed_take';
  else if(!allValuesPresent) status='missing_metric_values';
  else if(!completeDirections) status='incomplete_adjacent_steps';
  else if(directionality==='non_monotonic') status='descriptive_non_monotonic_sequence';
  else if(directionality==='descriptive_only') status='descriptive_only_sequence';
  else if(allAdjacentDirectionalSame) {
    status='same_nonzero_direction_observed_across_all_observed_steps';
    consistentObservedDirection=uniqueNonSame[0]||null;
    eligibleForDirectionalSummary=true;
  } else if(directions.every(d=>d==='same')) {
    status='unchanged_across_all_observed_steps';
  } else {
    status='mixed_or_flat_observed_directions';
  }
  const firstValue=allValuesPresent?Number(values[0]):null;
  const lastValue=allValuesPresent?Number(values[values.length-1]):null;
  const netDelta=firstValue!==null&&lastValue!==null?+((lastValue-firstValue).toFixed(6)):null;
  return {
    key:series.key,label:series.label,unit:series.unit||null,
    classification:series.classification,directionality,
    displayResolution,
    status,evidenceVolume,consistentObservedDirection,eligibleForDirectionalSummary,
    physicalRecordingCount:points.length,adjacentStepCount:steps.length,
    firstValue,lastValue,netDeltaLaterMinusEarlier:netDelta,
    directionCounts:counts,longestSameDirectionRun:longestRun,
    points:points.map(p=>({chronologyIndex:p.chronologyIndex,recordingId:p.recordingId,title:p.title||'',value:p.value})),
    adjacentSteps:steps.map((x,i)=>{
      const rawDelta=x&&x.deltaLaterMinusEarlier;
      const hasNumericDelta=rawDelta!==null&&rawDelta!==undefined&&rawDelta!==''&&Number.isFinite(Number(rawDelta));
      const numericDelta=hasNumericDelta?Number(rawDelta):null;
      const hasResolution=Number.isFinite(Number(displayResolution.step))&&Number(displayResolution.step)>0;
      return {
        stepIndex:i+1,earlierRecordingId:x.earlierRecordingId,laterRecordingId:x.laterRecordingId,
        earlier:x.earlier,later:x.later,deltaLaterMinusEarlier:hasNumericDelta?numericDelta:null,
        deltaInDisplaySteps:hasNumericDelta&&hasResolution
          ? +((numericDelta/Number(displayResolution.step)).toFixed(6)):null,
        isSmallestNonzeroVisibleChange:hasNumericDelta&&hasResolution
          ? Math.abs(Math.abs(numericDelta)-Number(displayResolution.step))<=Number(displayResolution.step)*1e-6:false,
        observedDirection:directions[i],scoringConditionComparability:x.scoringConditionComparability
      };
    }),
    interpretation: directionality==='non_monotonic'
      ? 'Descriptive sequence only. More or less of this technique quantity is not automatically better or worse.'
      : directionality==='descriptive_only'
        ? 'Descriptive external-score component only. Direction is retained but is not promoted to a cross-take directional summary.'
        : 'This is a compression of observed external numeric outcomes across SongScope-observed takes. Display resolution describes only the granularity of the DAM value; even a one-display-step change is not automatically a meaningful singing-skill change. A consistent direction is not a trend, a statistical signal, a durable skill change, or a causal explanation.'
  };
}
function f2BuildPatternEvidence(historyPkg) {
  const h=historyPkg||{};
  const song=h.song||{};
  const pr=h.patternReadiness||{};
  const chronology=h.chronology||{};
  const chain=h.scoringConditionChain||{};
  const n=Number(song.physicalRecordingCount||song.recordingCount||0);
  const verified=Number(pr.sourceVerifiedStructuredOutcomeCount||0);
  const historyCompleteness=h.historyCompleteness&&typeof h.historyCompleteness==='object'
    ? h.historyCompleteness
    : {status:'unknown',assessmentStatus:'unknown',signalStatus:'unknown',note:'F1 did not provide history completeness metadata.'};
  let status='waiting_for_third_observed_take';
  const blockers=[];
  const completenessWarnings=[];
  const completenessAssessment=historyCompleteness.assessmentStatus||(
    String(historyCompleteness.status||'').startsWith('not_assessable_')?historyCompleteness.status:'unknown'
  );
  const completenessSignal=historyCompleteness.signalStatus||(
    historyCompleteness.status==='may_omit_unrecorded_takes'||historyCompleteness.status==='no_missing_take_signal_from_personal_best'
      ? historyCompleteness.status
      : 'not_assessed'
  );
  if (completenessSignal==='may_omit_unrecorded_takes') completenessWarnings.push('history_may_omit_unrecorded_takes');
  if (String(completenessAssessment).startsWith('not_assessable_')) completenessWarnings.push('history_completeness_not_assessable');
  let evidenceVolume='pair_only';
  if(n<3) blockers.push('observed_take_count_below_3');
  else if(chronology.status!=='fully_ordered') { status='blocked_chronology_not_fully_ordered'; blockers.push('chronology_not_fully_ordered'); }
  else if(verified<n) { status='blocked_missing_source_verified_outcomes'; blockers.push('not_all_observed_takes_have_source_verified_structured_outcomes'); }
  else if(chain.status!=='comparable_chain') { status='blocked_scoring_conditions_not_comparable'; blockers.push('scoring_condition_chain_not_comparable'); }
  else {
    evidenceVolume=n>=5?'five_or_more_observed_takes':'three_to_four_observed_takes';
    status='observed_direction_history_available';
  }
  const ready=status==='observed_direction_history_available';
  const series=(h.outcomeSeries||[]).map(s=>f2MetricPattern(s,ready?evidenceVolume:'insufficient'));
  const consistentDirectionalObservations=ready?series.filter(x=>x.eligibleForDirectionalSummary).map(x=>({
    key:x.key,label:x.label,unit:x.unit,direction:x.consistentObservedDirection,
    physicalRecordingCount:x.physicalRecordingCount,adjacentStepCount:x.adjacentStepCount,
    firstValue:x.firstValue,lastValue:x.lastValue,netDeltaLaterMinusEarlier:x.netDeltaLaterMinusEarlier,
    evidenceVolume:x.evidenceVolume,
    interpretation:'Same non-zero observed direction across all SongScope-observed adjacent steps. This is descriptive only; do not call it a trend, signal, improvement, deterioration, or statistical evidence.'
  })) : [];
  const mixedOrFlat=ready?series.filter(x=>x.status==='mixed_or_flat_observed_directions'||x.status==='unchanged_across_all_observed_steps').map(x=>({
    key:x.key,label:x.label,status:x.status,directionCounts:x.directionCounts,longestSameDirectionRun:x.longestSameDirectionRun,
    netDeltaLaterMinusEarlier:x.netDeltaLaterMinusEarlier,evidenceVolume:x.evidenceVolume
  })) : [];
  const descriptiveOnly=ready?series.filter(x=>x.status==='descriptive_non_monotonic_sequence'||x.status==='descriptive_only_sequence').map(x=>({
    key:x.key,label:x.label,status:x.status,directionCounts:x.directionCounts,longestSameDirectionRun:x.longestSameDirectionRun,
    interpretation:x.interpretation
  })) : [];
  return {
    schemaVersion:'songscope-observed-direction-history-0.5.0',
    packageType:'same_song_observed_take_direction_history',
    generatedAt:nowIso(),appVersion:APP_VERSION,buildId:BUILD_ID,
    song:{
      songId:song.songId||null,representativeTitle:song.representativeTitle||'',representativeArtist:song.representativeArtist||'',
      observedPhysicalRecordingCount:n,storedRecordingRecordCount:Number(song.storedRecordingRecordCount||0),
      duplicateAliasRecordCount:Number(song.duplicateAliasRecordCount||0),unresolvedIdentityRecordCount:Number(song.unresolvedIdentityRecordCount||0),
      scopeDefinition:'Count refers only to physical recordings observed/imported by SongScope; it is not the total number of times the user has ever sung the song.'
    },
    readiness:{
      status,evidenceVolume,blockers,completenessWarnings,
      historyCompletenessStatus:historyCompleteness.status||'unknown',
      historyCompletenessAssessmentStatus:completenessAssessment,
      historyCompletenessSignalStatus:completenessSignal,
      observedPhysicalRecordingCount:n,sourceVerifiedStructuredOutcomeCount:verified,
      chronologyStatus:chronology.status||'unknown',scoringConditionChainStatus:chain.status||'unknown',
      minimumObservedTakesForDirectionHistory:3,
      evidenceVolumeLabels:{threeToFour:'descriptive volume only',fiveOrMore:'larger descriptive volume only'},
      note:n<3?'Two observed takes preserve a pair difference; R2 waits for a third before summarizing cross-step direction.':'Availability means the observed history can be compressed descriptively. It is not a statistical tier or skill-change claim.'
    },
    historyCompleteness,
    observedHistoryScope:{
      continuityClaim:'none',
      completenessAssessmentStatus:completenessAssessment,
      completenessSignalStatus:completenessSignal,
      note:completenessSignal==='may_omit_unrecorded_takes'
        ? 'Eligible source-verified personalBest exceeds eligible SongScope-observed scores, so one or more real-world takes may be absent. Direction summaries describe only imported observations and must not be read as consecutive-performance history.'
        : (String(completenessAssessment).startsWith('not_assessable_')
          ? 'Completeness cannot currently be assessed from eligible evidence. This is explicitly different from finding no missing-take signal. Direction summaries, if otherwise available, still describe only imported observations.'
          : 'No personalBest-based missing-take signal was detected within the eligible evidence set, but SongScope still does not claim complete real-world performance coverage.')
    },
    summary:{
      consistentDirectionalObservationCount:consistentDirectionalObservations.length,
      mixedOrFlatObservationCount:mixedOrFlat.length,
      descriptiveOnlySequenceCount:descriptiveOnly.length,
      consistentDirectionalObservations,
      mixedOrFlatObservations:mixedOrFlat,
      descriptiveOnlySequences:descriptiveOnly
    },
    metricPatterns:series,
    practiceLayerPolicy:{
      usableSignalScopes:['source_verified_external_scoring_outcomes','user_reported_markers_and_segments'],
      diagnosticOnlyScopes:['mixed_audio_periodicity_candidate_hz','mixed_audio_periodicity_candidate_ratio','mixed_audio_f0_ambiguity','mixed_audio_rms_relative_db'],
      mixedAudioAcousticFeaturesEligibleForPracticeHypothesis:false,
      reason:'Current D2 F0/RMS features are mixed voice+accompaniment+room observations and are not vocal-specific. They remain available only in diagnostic comparison packages.'
    },
    nextLayerReadiness:{
      status:!ready
        ? 'waiting_for_observed_direction_history'
        : (completenessWarnings.length?'external_outcome_history_available_with_completeness_caution':'external_outcome_history_available_for_hypothesis_layer'),
      completenessWarnings,
      note:'A later hypothesis/practice layer may use verified external scoring outcomes and user-reported evidence, but must preserve any history-completeness warning. It must not use mixed-audio F0/RMS as evidence about the singer.'
    },
    interpretationGuardrails:[
      'R2 summarizes only SongScope-observed/imported physical recordings; missing real-world karaoke takes may exist between observations. R2 carries forward both explicit missing-take signals and not-assessable completeness states. not_assessable is never treated as no_missing_take_signal.',
      'Display resolution is measurement/display granularity only. A one-step visible score change is an observation, not a threshold for meaningful skill change.',
      'A missing metric or missing adjacent-step delta is unknown, never zero and never same-direction evidence.',
      'Two observed recordings are never described as a cross-step directional history. At least three observed takes are required.',
      'A same non-zero direction across observed adjacent steps is a descriptive compression only; it is not called a trend or signal and has no statistical-significance claim.',
      'All-same values are not promoted as directional evidence.',
      'descriptive_only and non_monotonic metrics are excluded from consistent-direction summaries.',
      'Technique counts and vibrato quantity remain non-monotonic descriptive sequences and are never treated as better/worse.',
      'No composite singing score is invented. No weighting is applied across metrics.',
      'Mixed-audio F0/RMS are diagnostic-only and are explicitly ineligible as Practice/Hypothesis evidence about the singer.',
      'No causal explanation or practice prescription is generated in R2.'
    ]
  };
}
function f2PatternSeriesCsv(pkg) {
  const head=['metric_key','label','unit','classification','directionality','display_resolution_step','display_resolution_basis','status','evidence_volume','consistent_observed_direction','eligible_for_directional_summary','physical_recording_count','adjacent_step_count','first_value','last_value','net_delta_later_minus_earlier','higher_step_count','lower_step_count','same_step_count','unknown_step_count','longest_run_direction','longest_run_length'];
  const rows=[head.join(',')];
  for(const x of (pkg&&pkg.metricPatterns)||[]) {
    const c=x.directionCounts||{}, r=x.longestSameDirectionRun||{};
    const dr=x.displayResolution||{};
    const vals=[x.key,x.label,x.unit||'',x.classification||'',x.directionality||'',dr.step??'',dr.basis||'',x.status||'',x.evidenceVolume||'',x.consistentObservedDirection||'',x.eligibleForDirectionalSummary?'true':'false',x.physicalRecordingCount,x.adjacentStepCount,x.firstValue,x.lastValue,x.netDeltaLaterMinusEarlier,c.higher||0,c.lower||0,c.same||0,c.unknown||0,r.direction||'',r.length||0];
    rows.push(vals.map(v=>v===null||v===undefined?'':csvEscape(v)).join(','));
  }
  return rows.join('\n');
}
async function buildF2PatternPackage() {
  const history=await buildF1HistoryPackage();
  const pattern=f2BuildPatternEvidence(history);
  return { history, pattern };
}
async function exportF2PatternPackage() {
  const btn=$('#btn-f2-export'); if(btn)btn.disabled=true;
  const note=$('#cmp-f2-result');
  try{
    if(note)note.innerHTML='<p class="small">F1の観測テイク履歴から、外部評価値の方向推移を記述的に圧縮しています…</p>';
    const built=await buildF2PatternPackage();
    const history=built.history, pattern=built.pattern;
    const files=[
      {name:'pattern_summary.json',data:JSON.stringify(pattern,null,2)},
      {name:'pattern_series.csv',data:f2PatternSeriesCsv(pattern)},
      {name:'history_snapshot.json',data:JSON.stringify(history,null,2)}
    ];
    const blob=SongScopeZip.createZip(files);
    const stamp=new Date().toISOString().replace(/[-:]/g,'').slice(0,15);
    const name=`songscope_observed_history_${safeName(pattern.song.representativeTitle||'song')}_${stamp}.zip`;
    const how=await saveBlob(blob,name);
    const r=pattern.readiness;
    const completenessNote=`<p class="small"><b>履歴完全性:</b> assessment ${escapeHtml(r.historyCompletenessAssessmentStatus||'unknown')} / signal ${escapeHtml(r.historyCompletenessSignalStatus||'unknown')}${(r.completenessWarnings||[]).length?' / '+escapeHtml((r.completenessWarnings||[]).join(', ')):''}</p>`;
    if(note)note.innerHTML=`<p><b>R2 観測方向履歴パッケージを書き出しました</b></p><p class="small mono">observed physical recordings ${r.observedPhysicalRecordingCount} / verified outcomes ${r.sourceVerifiedStructuredOutcomeCount}</p><p class="small">readiness: <b>${escapeHtml(r.status)}</b> / consistent non-zero directions ${pattern.summary.consistentDirectionalObservationCount}</p>${completenessNote}<p class="small">これはtrendやsignalではありません。SongScopeに取り込まれた観測テイクの外部評価推移を圧縮したものです。表示分解能は技能変化の閾値ではありません。mixed-audio F0/RMSはPractice/Hypothesis入力から除外します。</p>`;
    if(how!=='cancelled')toast(`${name}を書き出しました`);
  }catch(e){
    console.error(e); if(note)note.innerHTML=`<p class="small">F2生成に失敗しました: ${escapeHtml((e&&e.message)||String(e))}</p>`; toast('R2観測方向履歴パッケージを作成できませんでした');
  }finally{if(btn)btn.disabled=false;}
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
  const descA = d2RecordingDescriptor('a'), descB = d2RecordingDescriptor('b');
  const pairIdentity = currentComparisonAudioIdentity();
  const pairContext = await getComparisonContextForIdentity(pairIdentity);
  const chronology = e4ResolveChronology(descA, descB, pairContext);
  const strictConditions = e3StrictScoringConditionComparability(descA, descB, pairContext);
  const evalAnchors = d2EvaluationAnchors(descA, descB, strictConditions);
  const comparisonContext = e4ContextExport(descA, descB, pairContext, chronology, strictConditions);
  const outcomeComparison = e3OutcomeComparison(descA, descB, pairContext, chronology, strictConditions);
  const hasOutcomeAnchor = evalAnchors.damScore.status !== 'unavailable' || evalAnchors.scoringResultImages.status !== 'unavailable' || evalAnchors.structuredScoringResults.status !== 'unavailable';
  return {
    schemaVersion: 'songscope-d2-0.7.0',
    packageType: 'pairwise_observation_and_outcome_evidence',
    status: 'aligned_observation_comparison_ready',
    generatedAt: nowIso(),
    appVersion: APP_VERSION,
    buildId: BUILD_ID,
    comparisonPrinciples: [
      'This package is a diagnostic observation package. It reports aligned observations and evidence quantity; it does not label improvement.',
      'Per-window A/B observations are aggregated only over the common aligned interval shared by both recordings.',
      'f0_candidate_hz is a mixed-audio periodicity candidate, not true vocal F0, vocal range, or pitch accuracy.',
      'F0 ambiguity flags are heuristic diagnostics: ambiguity=none does not mean correct, and ambiguity does not provide an error probability.',
      'F0 candidate ratio is estimator evidence, not voiced ratio or singing duration.',
      'rms_relative_db is normalized within each recording and must not be interpreted as absolute loudness or singer vocal volume difference.',
      'Missing or weak evidence remains missing/weak rather than being imputed.',
      'Phase E3 compares source-verified external scoring fields as outcome observations; it never attributes an acoustic cause or labels overall singing improvement.',
      'Phase E4 keeps A/B direction separate from evidence-backed earlier→later chronology and from scoring-condition comparability.',
      'Audit R2 explicitly excludes mixed-audio F0/RMS from Practice/Hypothesis evidence about the singer; these fields remain diagnostic-only.'
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
    recordingA: descA,
    recordingB: descB,
    metricCatalog: d2MetricCatalog(),
    recordingConditionComparison: d2ConditionComparison(descA, descB),
    comparisonContext,
    evaluationAnchors: evalAnchors,
    outcomeComparison,
    practiceLayerPolicy: {
      packageRole: 'diagnostic_observation_only',
      mixedAudioAcousticFeaturesEligibleForPracticeHypothesis: false,
      excludedFromPracticeEvidence: ['rms_relative_db','f0_candidate_hz','f0_candidate_ratio','f0_ambiguity'],
      allowedPracticeEvidenceFromThisPackage: ['user_reported_markers_and_segments','source_verified_external_scoring_outcomes'],
      note: 'D2 mixed-audio acoustic features remain exportable for diagnostics/alignment audit but must not be used to infer singer-specific cause, skill, or practice prescription.'
    },
    comparisonReadiness: {
      temporalAlignment: 'resolved',
      temporalWindowing: 'validated_same_aligned_interval',
      vocalSpecificAcousticMetrics: 'not_available',
      chronology: chronology.status,
      scoringConditionComparability: strictConditions.overallStatus,
      outcomeEvaluation: outcomeComparison.status,
      orderedOutcomeObservation: outcomeComparison.progressionObservation && outcomeComparison.progressionObservation.status || 'unavailable',
      overall: outcomeComparison.progressionObservation && outcomeComparison.progressionObservation.status === 'ordered_outcome_observation_comparable' ? 'observation_and_ordered_comparable_outcome_evidence' : 'observation_comparison_only'
    },
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
      { name: 'metric_catalog.json', data: JSON.stringify(pkg.metricCatalog, null, 2) },
      { name: 'evaluation_anchors.json', data: JSON.stringify(pkg.evaluationAnchors, null, 2) },
      { name: 'comparison_context.json', data: JSON.stringify(pkg.comparisonContext, null, 2) },
      { name: 'outcome_comparison.json', data: JSON.stringify(pkg.outcomeComparison, null, 2) },
      { name: 'comparison_summary.json', data: JSON.stringify(pkg, null, 2) },
      { name: 'comparison_windows.csv', data: d2WindowsCsv(pkg) }
    ];
    for (const pair of [['A',cmp.a],['B',cmp.b]]) {
      const label=pair[0],d=pair[1];
      const ctx=d&&d.scoringEvidenceContext?d.scoringEvidenceContext:{boundSets:[],conflictSets:[],legacyCandidateSets:[],bindingStates:new Map(),assertions:[]};
      files.push({name:`evaluation/${label}_scoring_evidence_relation.json`,data:JSON.stringify(
        d&&d.rec?recordingScoringEvidenceDescriptor(d.rec,ctx):{status:'unavailable'},null,2)});
      const map=new Map();
      for (const set of [...(ctx.boundSets||[]),...(ctx.conflictSets||[]),...(ctx.legacyCandidateSets||[])]) if(set&&set.evidenceSetId) map.set(set.evidenceSetId,set);
      for (const set of map.values()) {
        const bs=ctx.bindingStates instanceof Map?ctx.bindingStates.get(set.evidenceSetId):null;
        const root=`evaluation/${label}_relations/${set.evidenceSetId}`;
        files.push({name:`${root}/evidence_set.json`,data:JSON.stringify(standaloneEvidenceSetPublic(set,bs),null,2)});
        const candidate=d&&d.rec?legacyCandidateForRecording(set,d.rec.recordingId):null;
        if (candidate) files.push({name:`${root}/legacy_attachment_candidate.json`,data:JSON.stringify(legacyCandidatePublic(candidate),null,2)});
        const setAssertions=(ctx.assertions||[]).filter(x=>x&&x.evidenceSetId===set.evidenceSetId).sort((a,b)=>bindingAssertionSortKey(a).localeCompare(bindingAssertionSortKey(b)));
        files.push({name:`${root}/binding_assertions.json`,data:JSON.stringify({currentState:bs||null,assertions:setAssertions},null,2)});
        for (let i=0;i<(set.images||[]).length;i++) {
          const x=set.images[i];
          if (!x||!x.blob) continue;
          const ab=await x.blob.arrayBuffer();
          const got=(await sha256Hex(ab)).toLowerCase();
          if (got!==String(x.meta&&x.meta.sha256||'').toLowerCase()) throw new Error(`${label} relation ${set.evidenceSetId}: image SHA mismatch`);
          files.push({name:`${root}/images/${String(i+1).padStart(2,'0')}_${x.imageId}${imageExtFromMeta(x.meta)}`,data:new Uint8Array(ab)});
        }
      }
    }
    const blob = SongScopeZip.createZip(files);
    const stamp = new Date().toISOString().replace(/[-:]/g,'').slice(0,15);
    const name = `songscope_compare_${safeName(pkg.recordingA.title)}_vs_${safeName(pkg.recordingB.title)}_${stamp}.zip`;
    const how = await saveBlob(blob, name);
    if (note) note.innerHTML = `<p><b>D2比較パッケージを書き出しました</b></p><p class="small mono">offset ${pkg.alignment.offsetSec >= 0 ? '+' : ''}${pkg.alignment.offsetSec.toFixed(1)} s / overlap ${pkg.overlap.durationSec.toFixed(1)} s / windows ${pkg.evidenceSummary.windowCount} / full pair ${pkg.evidenceSummary.fullPairCoverageWindowCount}</p><p class="small">E3 outcome: ${escapeHtml(pkg.outcomeComparison.status)}。改善判定はしません。F0 candidateは混合音声の周期候補として扱い、外部採点との差も原因説明には使いません。</p>`;
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
  $('#btn-session-import').addEventListener('click',()=>openSheet('sheet-session-import'));
  $('#btn-session-add-recording').addEventListener('click',()=>$('#file-input').click());
  $('#btn-session-add-scoring').addEventListener('click',()=>$('#scoring-evidence-input').click());
  $('#btn-scoring-archive-toggle').addEventListener('click', async () => { showArchivedScoringEvidence=!showArchivedScoringEvidence; await renderStandaloneEvidenceSets(); });
  $('#scoring-evidence-input').addEventListener('change', e => {
    // iOS Safariではinput.valueを空にするとFileList自体も空になる場合がある。
    // 非同期処理へ渡す前に通常Arrayへsnapshotしてからinputをresetする。
    const files = Array.from(e.target.files || []);
    e.target.value = '';
    if (files.length) onStandaloneEvidenceInput(files);
  });
  $('#scoring-structured-input').addEventListener('change', async e => {
    const evidenceSetId=e.target.dataset.evidenceSetId||'';
    const file=e.target.files&&e.target.files[0];
    e.target.value=''; delete e.target.dataset.evidenceSetId;
    if (!file || !evidenceSetId) return;
    try { const saved=await importStandaloneStructuredResult(evidenceSetId,file); if(saved){ await renderStandaloneEvidenceSets(); toast('構造化採点JSONを保存しました'); } }
    catch(err){ console.error(err); toast((err&&err.message)||'構造化採点JSONを保存できませんでした'); }
  });
  $('#file-input').addEventListener('change', e => {
    const f = e.target.files && e.target.files[0];
    e.target.value = '';
    if (!f) return;
    if (f.size > 400 * 1024 * 1024) { toast('ファイルが大きすぎます'); return; }
    openAddSheet(f);
  });
  $('#btn-settings').addEventListener('click', openSettingsSheet);
  $('#btn-backup-all').addEventListener('click', backupAll);
  $('#btn-restore-all').addEventListener('click', () => $('#restore-input').click());
  $('#btn-restore-selftest').addEventListener('click', () => $('#restore-selftest-input').click());
  $('#restore-selftest-input').addEventListener('change', e => {
    const f = e.target.files && e.target.files[0];
    e.target.value = '';
    if (f) disasterRecoverySelfTest(f);
  });
  $('#restore-input').addEventListener('change', e => {
    const f = e.target.files && e.target.files[0];
    e.target.value = '';
    if (f) restoreAll(f);
  });
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
  $('#scoring-review-confirm').addEventListener('click', async e => {
    const id=e.currentTarget.dataset.evidenceSetId||'';
    if (!id) return;
    try {
      await confirmStandaloneStructuredResult(id);
      closeSheet();
      await renderStandaloneEvidenceSets();
      const set=await dbGet('scoringEvidenceSets',id);
      const review=set&&set.structuredScoringUserReview;
      toast(review&&review.status==='user_confirmed_with_known_gaps'?'確認済み（既知の未抽出あり）':'抽出内容を確認済みにしました');
    } catch(err) { toast((err&&err.message)||'確認状態を保存できませんでした'); }
  });
  $('#binding-search').addEventListener('input',e=>{
    bindingUiState.query=String(e.target.value||'').trim();
    if (bindingSearchTimer) clearTimeout(bindingSearchTimer);
    bindingSearchTimer=setTimeout(()=>{ renderBindingSheet().catch(err=>{ console.error(err); toast('Binding候補を更新できませんでした'); }); },180);
  });
  $('#f-recat-confirm').addEventListener('click', confirmRecordedAtInForm);
  $('#f-recdate-confirm').addEventListener('click', confirmRecordedDateInForm);
  $('#f-recat-unknown').addEventListener('click', keepRecordingTimeUnknownInForm);
  $('#f-cond-prev').addEventListener('click', confirmScoringConditionsFromPrevious);
  $('#f-cond-confirm').addEventListener('click', confirmCurrentScoringConditions);
  $('#f-recat').addEventListener('input', () => {
    if (state.recFormContext) { state.recFormContext.recordedAtExplicitConfirm = false; state.recFormContext.recordedDateExplicitConfirm = false; }
    updateRecConfirmationUi();
  });
  $('#f-recdate').addEventListener('input', () => {
    if (state.recFormContext) { state.recFormContext.recordedDateExplicitConfirm = false; if (state.recFormContext.chronologyPrecisionChoice === 'day') state.recFormContext.chronologyPrecisionChoice = 'unknown'; }
    updateRecConfirmationUi();
  });
  for (const id of ['#f-device','#f-mode','#f-key','#f-octave']) {
    $(id).addEventListener('change', () => {
      if (state.recFormContext) state.recFormContext.scoringConditionsExplicitConfirm = false;
      updateRecConfirmationUi();
    });
  }
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


async function invalidatePairContextsForDeletedRecording(rec) {
  const sha=String(rec&&rec.audioSha256||'').toLowerCase();
  if (!sha) return {invalidatedCount:0,skippedBecauseSamePhysicalRecordingStillStored:false};
  const recs=await dbAll('recordings').catch(()=>[]);
  const samePhysicalStillStored=recs.some(r=>r&&r.recordingId!==rec.recordingId&&String(r.audioSha256||'').toLowerCase()===sha);
  if (samePhysicalStillStored) {
    return {invalidatedCount:0,skippedBecauseSamePhysicalRecordingStillStored:true};
  }
  const rows=await dbAll('pairContexts').catch(()=>[]);
  let changed=0;
  for (const row of rows) {
    const pair=Array.isArray(row&&row.audioPair)?row.audioPair.map(x=>String(x).toLowerCase()):[];
    if (!pair.includes(sha)) continue;
    const at=nowIso();
    const history=Array.isArray(row.history)?row.history.slice(-49):[];
    history.push({
      field:'pairContext',action:'invalidated_by_recording_deletion',
      at,source:'recording_deletion',
      recordingId:rec.recordingId||null,audioSha256:sha,
      priorChronologyStatus:row.chronology&&row.chronology.status||'unknown',
      priorScoringConditionsStatus:row.scoringConditions&&row.scoringConditions.status||'unknown',
      appVersion:APP_VERSION,buildId:BUILD_ID
    });
    row.history=history;
    row.invalidatedAt=at;
    row.lastInvalidatedAt=at;
    row.invalidatedByRecordingDeletion=true;
    row.invalidatedRecordingId=rec.recordingId||null;
    row.invalidatedAudioSha256=sha;
    row.reactivatedAt=null;
    row.reactivatedBy=null;
    row.chronology={status:'unknown',source:'invalidated_by_recording_deletion',updatedAt:at};
    row.scoringConditions={status:'unknown',source:'invalidated_by_recording_deletion',coveredFields:SCORING_CONDITION_FIELDS.slice(),updatedAt:at};
    row.updatedAt=at;
    await dbPut('pairContexts',row);
    changed++;
  }
  return {invalidatedCount:changed,skippedBecauseSamePhysicalRecordingStillStored:false};
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
  // G0 build10: legacy recording-attached scoring evidence remains read-only for audit/rollback; all consumers use scoringEvidenceSets.
  ['btn-eval-image','btn-eval-image-remove','btn-eval-json','btn-eval-json-remove'].forEach(id=>{ const el=$('#'+id); if(el){ el.disabled=true; el.hidden=true; } });

  $('#btn-delete-rec').addEventListener('click', async () => {
    if (!state.rec) return;
    if (!confirm(`「${state.rec.title}」を削除します。取り消せません。よろしいですか？`)) return;
    const id = state.rec.recordingId;
    stopPlayback();
    let pairInvalidation={invalidatedCount:0,skippedBecauseSamePhysicalRecordingStillStored:false};
    try {
      pairInvalidation=await invalidatePairContextsForDeletedRecording(state.rec);
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
    const pairNote=pairInvalidation.invalidatedCount
      ? ` ／ pair確認 ${pairInvalidation.invalidatedCount}件を無効化`
      : (pairInvalidation.skippedBecauseSamePhysicalRecordingStillStored?' ／ 同一SHAの別recordingが残るためpair確認は維持':'');
    toast('削除しました'+pairNote,5200);
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
  $('#btn-f1-export').addEventListener('click', exportF1HistoryPackage);
  $('#btn-f2-export').addEventListener('click', exportF2PatternPackage);
  $('#btn-context-order-a-first').addEventListener('click', () => setE4Chronology('a_first'));
  $('#btn-context-order-b-first').addEventListener('click', () => setE4Chronology('b_first'));
  $('#btn-context-order-clear').addEventListener('click', () => setE4Chronology('clear'));
  $('#btn-context-cond-same').addEventListener('click', () => setE4ScoringConditions('same'));
  $('#btn-context-cond-diff').addEventListener('click', () => setE4ScoringConditions('different'));
  $('#btn-context-cond-clear').addEventListener('click', () => setE4ScoringConditions('clear'));
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
  document.addEventListener('focusin',handleSongScopeSheetFocusIn,true);
  document.addEventListener('focusout',handleSongScopeSheetFocusOut,true);
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize',handleSongScopeVisualViewportResize,{passive:true});
    window.visualViewport.addEventListener('scroll',handleSongScopeVisualViewportScroll,{passive:true});
  }
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => { drawAllGraphs(); drawCompare(); }, 150);
  });
  window.addEventListener('orientationchange', () => {
    handleSongScopeOrientationChange();
    setTimeout(() => { drawAllGraphs(); drawCompare(); }, 350);
  });
  matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change', () => { specCache = { key: '', canvas: null }; drawAllGraphs(); });
  window.addEventListener('beforeunload', () => { if (state.audioUrl) URL.revokeObjectURL(state.audioUrl); });
  document.addEventListener('gesturestart', e => e.preventDefault()); // 誤ピンチズーム防止
}


let songScopeReloadingForUpdate=false;
function showSongScopeUpdatePrompt(reg) {
  if (!reg || !reg.waiting || !navigator.serviceWorker.controller) return;
  const banner=$('#update-banner');
  if (!banner) return;
  banner.hidden=false;
  const btn=$('#btn-apply-update');
  btn.onclick=()=>{
    if (reg.waiting) reg.waiting.postMessage({type:'SKIP_WAITING'});
  };
}
async function registerSongScopeServiceWorker() {
  const reg=await navigator.serviceWorker.register('service-worker.js?v=' + encodeURIComponent(BUILD_ID));
  if (reg.waiting) showSongScopeUpdatePrompt(reg);
  reg.addEventListener('updatefound',()=>{
    const worker=reg.installing;
    if (!worker) return;
    worker.addEventListener('statechange',()=>{
      if (worker.state==='installed' && navigator.serviceWorker.controller) showSongScopeUpdatePrompt(reg);
    });
  });
  navigator.serviceWorker.addEventListener('controllerchange',()=>{
    if (songScopeReloadingForUpdate) return;
    songScopeReloadingForUpdate=true;
    location.reload();
  });
  // Ask the browser to check now; failure is non-fatal/offline-safe.
  reg.update().catch(()=>{});
}

async function init() {
  loadSettings();
  state.confMin = settings.minimumConfidence;
  wireHome(); wireSheets(); wireReview(); wireCompare(); wireGlobal();
  $$('.app-ver').forEach(e => e.textContent = APP_VERSION + ' / ' + BUILD_ID);
  // build16もDB8を継続使用する。upgrade blocked/version mismatchをgeneric errorに落とさず、
  // 『データを消す』誤対処を誘発しない専用案内にする。
  try { await db(); }
  catch (e) {
    console.error('SongScope DB open failed during R1 migration', e);
    if (isDbBlockedError(e)) toast(dbBlockedUserMessage(), 8000);
    else if (isDbVersionError(e)) toast(dbVersionUserMessage(), 8000);
    else toast('端末内データベースを開けませんでした。サイトデータは削除しないでください。', 8000);
    return;
  }
  await migrateR1PairContexts().catch(e=>console.warn('R1 pair-context migration skipped:',e));
  await migrateBliteIdentityData().catch(e=>console.warn('B-lite migration skipped:',e));
  const legacyScoringMigration=await migrateLegacyRecordingAttachedScoringEvidence().catch(e=>{console.warn('G0 build10 legacy scoring migration skipped:',e);return null;});
  if (legacyScoringMigration&&legacyScoringMigration.examined) console.info('SongScope build10 legacy scoring migration',legacyScoringMigration);
  await loadRecordings();
  await renderStandaloneEvidenceSets();
  await renderNormalWorkflowStatus().catch(()=>{});
  refreshStorageEstimate();
  if ('serviceWorker' in navigator && location.protocol === 'https:') {
    registerSongScopeServiceWorker().catch(e=>console.warn('service worker registration failed',e));
  }
}
document.addEventListener('DOMContentLoaded', init);


