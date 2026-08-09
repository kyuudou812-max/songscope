/* SongScope — audio analysis worker (v0.2 Phase A-1)
 * 入力: モノラルPCM (Float32Array) + 元サンプルレート + 解析設定
 * 出力: フレーム特徴量 / 波形ピーク / スペクトログラム / 検出区間 / サマリー
 *
 * 設計原則:
 *  - ここは「測定器」である。良し悪しの判定は一切行わない。
 *  - 推定できない値は null (NaN) にする。それらしい数値を捏造しない。
 *  - 使用アルゴリズム名とバージョンを必ず返し、結果と一緒に保存できるようにする。
 */
'use strict';

const ENGINE = {
  analysisEngineName: 'SongScope Analysis Engine',
  analysisEngineVersion: '0.2.0-phaseA1',
  algorithmNames: {
    resampling: 'linear-interpolation-with-boxcar-antialias',
    windowing: 'hann',
    spectrum: 'radix2-fft',
    f0: 'YIN (fixed-window cross-correlation via FFT, CMND, absolute threshold, parabolic interpolation, sub-multiple octave check)',
    voicedProbability: 'f0Confidence * levelGate(noiseFloor+12dB)',
    loudness: 'frame RMS / peak (dBFS), reference-normalized',
    activeSegments: 'RMS dual-threshold hysteresis relative to per-recording reference/noise-floor, with gap merging'
  },
  algorithmVersions: {
    resampling: '1.0.0',
    windowing: '1.0.0',
    spectrum: '1.0.0',
    f0: '1.1.0-phaseA1',
    voicedProbability: '1.0.0',
    loudness: '1.0.0',
    activeSegments: '1.0.0'
  },
  experimentalFeatures: {
    implemented: false,
    candidates: ['jitter', 'shimmer', 'HNR', 'CPP', 'formants', 'MFCC'],
    reason: 'カラオケ伴奏・室内反響・自動ゲインを含む単一チャンネル録音では、これらの値は本人の声帯振動を表すとは言えず、精密に見える誤った数値になるため v0.1 では出力しない。'
  }
};

/* ================= FFT (radix-2, in-place) ================= */
function FFT(n) {
  this.n = n;
  this.levels = Math.log2(n) | 0;
  if (1 << this.levels !== n) throw new Error('FFT size must be a power of 2');
  this.cos = new Float32Array(n / 2);
  this.sin = new Float32Array(n / 2);
  for (let i = 0; i < n / 2; i++) {
    this.cos[i] = Math.cos(2 * Math.PI * i / n);
    this.sin[i] = Math.sin(2 * Math.PI * i / n);
  }
  this.rev = new Uint32Array(n);
  for (let i = 0; i < n; i++) {
    let x = i, r = 0;
    for (let j = 0; j < this.levels; j++) { r = (r << 1) | (x & 1); x >>= 1; }
    this.rev[i] = r;
  }
}
FFT.prototype.forward = function (re, im) {
  const n = this.n, rev = this.rev;
  for (let i = 0; i < n; i++) {
    const j = rev[i];
    if (j > i) {
      let t = re[i]; re[i] = re[j]; re[j] = t;
      t = im[i]; im[i] = im[j]; im[j] = t;
    }
  }
  for (let size = 2; size <= n; size <<= 1) {
    const half = size >> 1, step = n / size;
    for (let i = 0; i < n; i += size) {
      for (let j = i, k = 0; j < i + half; j++, k += step) {
        const l = j + half;
        const tre = re[l] * this.cos[k] + im[l] * this.sin[k];
        const tim = -re[l] * this.sin[k] + im[l] * this.cos[k];
        re[l] = re[j] - tre; im[l] = im[j] - tim;
        re[j] += tre; im[j] += tim;
      }
    }
  }
};

/* ================= helpers ================= */
const DB_FLOOR = -120;
function toDb(x) { return x > 1e-12 ? 20 * Math.log10(x) : DB_FLOOR; }
function median(arr) {
  if (!arr.length) return NaN;
  const a = Float64Array.from(arr).sort();
  const m = a.length >> 1;
  return a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2;
}
function percentile(arr, p) {
  if (!arr.length) return NaN;
  const a = Float64Array.from(arr).sort();
  const i = Math.min(a.length - 1, Math.max(0, Math.round((a.length - 1) * p)));
  return a[i];
}
function hzToMidi(hz) { return 69 + 12 * Math.log2(hz / 440); }

/* モノラルPCMを解析用サンプルレートへ変換（簡易アンチエイリアス付き） */
function resample(input, srcRate, dstRate) {
  if (Math.abs(srcRate - dstRate) < 1) return { data: input, rate: srcRate };
  const ratio = srcRate / dstRate;
  const outLen = Math.floor(input.length / ratio);
  const out = new Float32Array(outLen);
  if (ratio > 1) {
    const w = Math.max(1, Math.round(ratio));       // ダウンサンプル: 箱型平均で折返しを抑える
    for (let i = 0; i < outLen; i++) {
      const c = i * ratio, s = Math.max(0, (c - w / 2) | 0), e = Math.min(input.length, s + w);
      let sum = 0;
      for (let j = s; j < e; j++) sum += input[j];
      out[i] = sum / Math.max(1, e - s);
    }
  } else {
    for (let i = 0; i < outLen; i++) {             // アップサンプル: 線形補間
      const c = i * ratio, i0 = c | 0, f = c - i0;
      out[i] = input[i0] * (1 - f) + (input[Math.min(input.length - 1, i0 + 1)] || 0) * f;
    }
  }
  return { data: out, rate: dstRate };
}

/* ================= YIN (FFT自己相関ベース) ================= */
function makeYin(winLen, tauMax, sr, threshold) {
  let fftSize = 1;
  while (fftSize < winLen + tauMax + 1) fftSize <<= 1;
  const fft = new FFT(fftSize);
  const ar = new Float32Array(fftSize), ai = new Float32Array(fftSize);
  const br = new Float32Array(fftSize), bi = new Float32Array(fftSize);
  const d = new Float32Array(tauMax + 1);
  const cmnd = new Float32Array(tauMax + 1);

  return function estimate(buf, offset, tauMin) {
    const total = Math.min(winLen + tauMax, buf.length - offset);
    if (total < winLen + 4) return { f0: NaN, conf: 0 };
    // 固定窓 a = x[0..winLen) と 参照 b = x[0..total) の相互相関を取る。
    // （全区間の自己相関を使うと窓長が tau によって変わり、F0 に系統誤差が出る）
    ar.fill(0); ai.fill(0); br.fill(0); bi.fill(0);
    for (let i = 0; i < winLen; i++) ar[i] = buf[offset + i];
    for (let i = 0; i < total; i++) br[i] = buf[offset + i];
    fft.forward(ar, ai);
    fft.forward(br, bi);
    for (let k = 0; k < fftSize; k++) {   // C = conj(A) * B, 逆FFT用に共役を格納
      const cre = ar[k] * br[k] + ai[k] * bi[k];
      const cim = ar[k] * bi[k] - ai[k] * br[k];
      ar[k] = cre; ai[k] = -cim;
    }
    fft.forward(ar, ai);                  // real(ar)/N = r(tau)
    const scale = 1 / fftSize;

    // 差分関数 d(tau) = pw0 + pwTau - 2*r(tau)
    let pw0 = 0;
    for (let i = 0; i < winLen; i++) pw0 += buf[offset + i] * buf[offset + i];
    let pwTau = pw0;
    d[0] = 0;
    for (let t = 1; t <= tauMax; t++) {
      const outS = buf[offset + t - 1] || 0;
      const j = offset + t + winLen - 1;
      const inS = j < buf.length ? buf[j] : 0;
      pwTau += inS * inS - outS * outS;
      d[t] = pw0 + pwTau - 2 * (ar[t] * scale);
      if (d[t] < 0) d[t] = 0;
    }
    // 累積平均正規化
    cmnd[0] = 1;
    let run = 0;
    for (let t = 1; t <= tauMax; t++) {
      run += d[t];
      cmnd[t] = run > 0 ? d[t] * t / run : 1;
    }
    // 絶対閾値
    let tau = -1;
    for (let t = tauMin; t <= tauMax; t++) {
      if (cmnd[t] < threshold) {
        while (t + 1 <= tauMax && cmnd[t + 1] < cmnd[t]) t++;
        tau = t; break;
      }
    }
    if (tau < 0) { // 閾値未満なし → 最小値を候補にするが信頼度は低く出る
      let best = tauMin, bv = cmnd[tauMin];
      for (let t = tauMin + 1; t <= tauMax; t++) if (cmnd[t] < bv) { bv = cmnd[t]; best = t; }
      tau = best;
    }
    // オクターブ下取り対策: tau/2, tau/3 付近が同程度に良ければ短い周期を採る。
    // （伴奏の低域が混ざると 2T の谷が深くなり、半分の周波数を返しやすいため）
    for (let k = 2; k <= 3; k++) {
      const cand = Math.round(tau / k);
      if (cand < tauMin) continue;
      let bestT = -1, bestV = Infinity;
      for (let t = Math.max(tauMin, cand - 2); t <= Math.min(tauMax, cand + 2); t++) {
        if (cmnd[t] < bestV) { bestV = cmnd[t]; bestT = t; }
      }
      if (bestT > 0 && bestV < Math.max(threshold, cmnd[tau] * 1.15) && bestV < 0.35) { tau = bestT; break; }
    }
    // 放物線補間
    let better = tau;
    if (tau > 0 && tau < tauMax) {
      const y0 = cmnd[tau - 1], y1 = cmnd[tau], y2 = cmnd[tau + 1];
      const den = 2 * (2 * y1 - y2 - y0);
      if (Math.abs(den) > 1e-9) better = tau + (y2 - y0) / den;
    }
    const conf = Math.max(0, Math.min(1, 1 - cmnd[tau]));
    const f0 = sr / better;
    return { f0: isFinite(f0) ? f0 : NaN, conf };
  };
}

/* ================= メイン解析 ================= */
function analyze(pcmIn, srcRate, cfg) {
  const t0 = Date.now();
  post('progress', { pct: 2, label: 'リサンプル中' });
  const rs = resample(pcmIn, srcRate, cfg.analysisSampleRate);
  const x = rs.data, sr = rs.rate;
  const durationSec = pcmIn.length / srcRate;

  const frameLen = Math.max(64, Math.round(sr * cfg.frameSizeMs / 1000));
  const hopLen = Math.max(16, Math.round(sr * cfg.hopSizeMs / 1000));
  const nFrames = Math.max(1, Math.floor((x.length - frameLen) / hopLen) + 1);

  // --- FFT準備（スペクトル用） ---
  let fftSize = 1; while (fftSize < frameLen) fftSize <<= 1;
  fftSize = Math.max(1024, fftSize);
  const fft = new FFT(fftSize);
  const re = new Float32Array(fftSize), im = new Float32Array(fftSize);
  const win = new Float32Array(frameLen);
  for (let i = 0; i < frameLen; i++) win[i] = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / (frameLen - 1));
  const nBins = fftSize / 2;
  const binHz = sr / fftSize;
  const mag = new Float32Array(nBins);
  const prevMag = new Float32Array(nBins);

  // --- YIN準備 ---
  const tauMin = Math.max(2, Math.floor(sr / cfg.f0MaxHz));
  const tauMax = Math.min(Math.ceil(sr / cfg.f0MinHz), frameLen * 2);
  const yin = makeYin(frameLen, tauMax, sr, cfg.yinThreshold);

  // --- 出力バッファ ---
  const F = {
    timeSec: new Float32Array(nFrames),
    rmsDb: new Float32Array(nFrames),
    rmsRelDb: new Float32Array(nFrames),
    peakDb: new Float32Array(nFrames),
    crest: new Float32Array(nFrames),
    // v0.1互換F0（minimumConfidence通過後）。既存UI/出力を壊さないため残す。
    f0Hz: new Float32Array(nFrames),
    f0Midi: new Float32Array(nFrames),
    f0Conf: new Float32Array(nFrames),
    // Phase A-1: YINの生観測と、比較利用候補を別層で保持する。
    rawF0Hz: new Float32Array(nFrames),
    rawF0Midi: new Float32Array(nFrames),
    filteredF0Hz: new Float32Array(nFrames),
    usableVocalF0Hz: new Float32Array(nFrames),
    f0Status: new Uint8Array(nFrames),
    voicedProb: new Float32Array(nFrames),
    centroid: new Float32Array(nFrames),
    bandwidth: new Float32Array(nFrames),
    rolloff: new Float32Array(nFrames),
    flux: new Float32Array(nFrames),
    flatness: new Float32Array(nFrames),
    rmsDelta: new Float32Array(nFrames),
    f0Delta: new Float32Array(nFrames)
  };
  // Float32Array は初期値0なので、「未観測」を0Hzと誤認しないよう NaN で初期化する。
  F.rawF0Hz.fill(NaN);
  F.rawF0Midi.fill(NaN);
  F.filteredF0Hz.fill(NaN);
  F.usableVocalF0Hz.fill(NaN);

  const specMaxHz = Math.min(cfg.spectrogramMaxHz, sr / 2);
  const specBinCount = Math.max(1, Math.floor(specMaxHz / binHz));
  const SPEC_H = 128;
  const SPEC_W = Math.min(1200, nFrames);
  const specAcc = new Float32Array(SPEC_W * SPEC_H);
  const specCnt = new Float32Array(SPEC_W);

  let lastPct = 0;
  for (let n = 0; n < nFrames; n++) {
    const off = n * hopLen;
    F.timeSec[n] = off / sr;

    // --- 音量 ---
    let sum = 0, peak = 0;
    for (let i = 0; i < frameLen; i++) {
      const v = x[off + i] || 0;
      sum += v * v;
      const a = v < 0 ? -v : v;
      if (a > peak) peak = a;
    }
    const rms = Math.sqrt(sum / frameLen);
    F.rmsDb[n] = toDb(rms);
    F.peakDb[n] = toDb(peak);
    F.crest[n] = rms > 1e-9 ? peak / rms : NaN;

    // --- スペクトル ---
    re.fill(0); im.fill(0);
    for (let i = 0; i < frameLen; i++) re[i] = (x[off + i] || 0) * win[i];
    fft.forward(re, im);
    let msum = 0, wsum = 0, logSum = 0, powSum = 0, flux = 0;
    for (let k = 0; k < nBins; k++) {
      const m = Math.sqrt(re[k] * re[k] + im[k] * im[k]);
      mag[k] = m;
      msum += m; wsum += m * (k * binHz);
      const p = m * m + 1e-20;
      logSum += Math.log(p); powSum += p;
      const dfl = m - prevMag[k];
      if (dfl > 0) flux += dfl * dfl;
    }
    if (msum > 1e-9) {
      const cen = wsum / msum;
      F.centroid[n] = cen;
      let bw = 0;
      for (let k = 0; k < nBins; k++) { const df = k * binHz - cen; bw += df * df * mag[k]; }
      F.bandwidth[n] = Math.sqrt(bw / msum);
      let acc = 0, target = msum * 0.85, ro = 0;
      for (let k = 0; k < nBins; k++) { acc += mag[k]; if (acc >= target) { ro = k * binHz; break; } }
      F.rolloff[n] = ro;
      F.flatness[n] = Math.exp(logSum / nBins) / (powSum / nBins);
    } else {
      F.centroid[n] = NaN; F.bandwidth[n] = NaN; F.rolloff[n] = NaN; F.flatness[n] = NaN;
    }
    F.flux[n] = Math.sqrt(flux);
    prevMag.set(mag);

    // --- スペクトログラム格納（時間方向は最大値プーリング） ---
    const col = Math.min(SPEC_W - 1, Math.floor(n * SPEC_W / nFrames));
    specCnt[col]++;
    for (let row = 0; row < SPEC_H; row++) {
      const k0 = Math.floor(row * specBinCount / SPEC_H);
      const k1 = Math.max(k0 + 1, Math.floor((row + 1) * specBinCount / SPEC_H));
      let mx = 0;
      for (let k = k0; k < k1 && k < nBins; k++) if (mag[k] > mx) mx = mag[k];
      const idx = col * SPEC_H + row;
      const db = toDb(mx / (frameLen / 2));
      if (specCnt[col] === 1 || db > specAcc[idx]) specAcc[idx] = db;
    }

    // --- F0 ---
    const y = yin(x, off, tauMin);
    const rawF0Valid = isFinite(y.f0) && y.f0 >= cfg.f0MinHz && y.f0 <= cfg.f0MaxHz;
    if (rawF0Valid) {
      F.rawF0Hz[n] = y.f0;
      F.rawF0Midi[n] = hzToMidi(y.f0);
    }
    // v0.1互換値: minimumConfidence を通過した値だけを残す。
    if (rawF0Valid && y.conf >= cfg.minimumConfidence) {
      F.f0Hz[n] = y.f0;
      F.f0Midi[n] = hzToMidi(y.f0);
    } else {
      F.f0Hz[n] = NaN;
      F.f0Midi[n] = NaN;
    }
    F.f0Conf[n] = isFinite(y.conf) ? y.conf : 0;

    if (n % 64 === 0) {
      const pct = 2 + Math.round(88 * n / nFrames);
      if (pct > lastPct) { lastPct = pct; post('progress', { pct, label: '特徴量を計算中' }); }
    }
  }

  post('progress', { pct: 92, label: '集計中' });

  // --- 正規化音量の基準値 ---
  const finiteRms = [];
  for (let n = 0; n < nFrames; n++) if (F.rmsDb[n] > DB_FLOOR + 1) finiteRms.push(F.rmsDb[n]);
  const refDb = finiteRms.length ? percentile(finiteRms, 0.95) : 0;
  const noiseFloorDb = finiteRms.length ? percentile(finiteRms, 0.05) : DB_FLOOR;
  for (let n = 0; n < nFrames; n++) F.rmsRelDb[n] = F.rmsDb[n] - refDb;

  // --- voiced probability / delta ---
  for (let n = 0; n < nFrames; n++) {
    const gate = Math.max(0, Math.min(1, (F.rmsDb[n] - noiseFloorDb) / 12));
    F.voicedProb[n] = F.f0Conf[n] * gate;
    F.rmsDelta[n] = n === 0 ? 0 : F.rmsDb[n] - F.rmsDb[n - 1];
    F.f0Delta[n] = (n === 0 || !isFinite(F.f0Hz[n]) || !isFinite(F.f0Hz[n - 1])) ? NaN : F.f0Hz[n] - F.f0Hz[n - 1];
  }

  // --- Phase A-1: raw -> filtered -> usable vocal candidate ---
  // f0Status: 0=no_f0, 1=low_confidence, 2=low_voiced_probability,
  //           3=isolated_outlier, 4=usable
  const usableMinConfidence = isFinite(cfg.usableF0MinConfidence) ? cfg.usableF0MinConfidence : 0.70;
  const usableMinVoicedProbability = isFinite(cfg.usableF0MinVoicedProbability) ? cfg.usableF0MinVoicedProbability : 0.45;
  const outlierThresholdCent = isFinite(cfg.f0IsolatedOutlierThresholdCent) ? cfg.f0IsolatedOutlierThresholdCent : 700;
  const outlierRadius = Math.max(1, Math.round(isFinite(cfg.f0IsolatedOutlierWindowFrames) ? cfg.f0IsolatedOutlierWindowFrames : 2));
  const centDistance = (a, b) => (a > 0 && b > 0) ? Math.abs(1200 * Math.log2(a / b)) : Infinity;
  const medianSmall = arr => {
    if (!arr.length) return NaN;
    const b = arr.slice().sort((x, y) => x - y), m = b.length >> 1;
    return b.length & 1 ? b[m] : (b[m - 1] + b[m]) / 2;
  };

  for (let n = 0; n < nFrames; n++) {
    const hz = F.rawF0Hz[n];
    if (!isFinite(hz)) { F.f0Status[n] = 0; continue; }

    // filtered は raw を基本に、周辺から孤立した極端な飛び値だけ除く。
    let isolatedOutlier = false;
    const neigh = [];
    for (let j = Math.max(0, n - outlierRadius); j <= Math.min(nFrames - 1, n + outlierRadius); j++) {
      if (j === n) continue;
      const v = F.rawF0Hz[j];
      if (isFinite(v) && F.f0Conf[j] >= usableMinConfidence) neigh.push(v);
    }
    if (neigh.length >= 2) {
      const med = medianSmall(neigh);
      // 周辺値同士がある程度まとまっている場合だけ、中央の孤立点を除外する。
      const neighCent = neigh.map(v => centDistance(v, med));
      const neighPlausible = Math.max.apply(null, neighCent) <= 350;
      if (neighPlausible && centDistance(hz, med) >= outlierThresholdCent) isolatedOutlier = true;
    }

    if (!isolatedOutlier) F.filteredF0Hz[n] = hz;
    if (F.f0Conf[n] < usableMinConfidence) { F.f0Status[n] = 1; continue; }
    if (F.voicedProb[n] < usableMinVoicedProbability) { F.f0Status[n] = 2; continue; }
    if (isolatedOutlier) { F.f0Status[n] = 3; continue; }
    F.usableVocalF0Hz[n] = hz;
    F.f0Status[n] = 4;
  }

  // --- 活動区間（伴奏を含むため「本人の発声」とは断定しない） ---
  // カラオケ録音は伴奏が鳴り続けるためダイナミックレンジが狭い。
  // 絶対的な「無音」を基準にすると区間が1件も取れないので、その録音自身の
  // レンジに対する相対閾値にする（= 何を基準にしたかは summary に残す）。
  const dynamicDb = Math.max(3, refDb - noiseFloorDb);
  const openDb = refDb - Math.max(6, Math.min(22, dynamicDb * 0.6));
  const closeDb = openDb - Math.max(3, Math.min(8, dynamicDb * 0.15));
  const segs = [];
  let inSeg = false, segStart = 0;
  for (let n = 0; n < nFrames; n++) {
    const v = F.rmsDb[n];
    if (!inSeg && v >= openDb) { inSeg = true; segStart = F.timeSec[n]; }
    else if (inSeg && v < closeDb) { inSeg = false; segs.push([segStart, F.timeSec[n]]); }
  }
  if (inSeg) segs.push([segStart, F.timeSec[nFrames - 1]]);
  const merged = [];
  for (const s of segs) {
    const last = merged[merged.length - 1];
    if (last && s[0] - last[1] <= cfg.activeSegmentMergeGapSec) last[1] = s[1];
    else merged.push([s[0], s[1]]);
  }
  const detectedSegments = merged
    .filter(s => s[1] - s[0] >= cfg.activeSegmentMinDurSec)
    .map((s, i) => Object.assign({
      segmentId: 'ds_' + String(i + 1).padStart(4, '0'),
      startSec: +s[0].toFixed(3),
      endSec: +s[1].toFixed(3),
      durationSec: +(s[1] - s[0]).toFixed(3)
    }, rangeStats(F, nFrames, s[0], s[1])));

  // --- 波形ピーク（描画用に縮約） ---
  const WV = Math.min(4000, Math.max(600, Math.floor(durationSec * 12)));
  const wmin = new Float32Array(WV), wmax = new Float32Array(WV);
  const per = x.length / WV;
  for (let i = 0; i < WV; i++) {
    const s = Math.floor(i * per), e = Math.min(x.length, Math.floor((i + 1) * per));
    let mn = 0, mx = 0;
    for (let j = s; j < e; j++) { const v = x[j]; if (v < mn) mn = v; if (v > mx) mx = v; }
    wmin[i] = mn; wmax[i] = mx;
  }

  // --- スペクトログラム画素化 ---
  let sMin = Infinity, sMax = -Infinity;
  for (let i = 0; i < specAcc.length; i++) {
    const v = specAcc[i];
    if (v > sMax) sMax = v;
    if (v < sMin && v > DB_FLOOR + 1) sMin = v;
  }
  if (!isFinite(sMin)) sMin = DB_FLOOR;
  const floorDb = Math.max(sMin, sMax - 72);
  const specPix = new Uint8Array(SPEC_W * SPEC_H);
  for (let i = 0; i < specAcc.length; i++) {
    const v = (specAcc[i] - floorDb) / Math.max(1, sMax - floorDb);
    specPix[i] = Math.max(0, Math.min(255, Math.round(v * 255)));
  }

  // --- サマリー ---
  const validF0 = [];
  for (let n = 0; n < nFrames; n++) if (isFinite(F.f0Hz[n])) validF0.push(F.f0Hz[n]);
  const rmsVals = finiteRms;
  let peakMax = -Infinity;
  for (let n = 0; n < nFrames; n++) if (F.peakDb[n] > peakMax) peakMax = F.peakDb[n];

  const summary = {
    durationSec: +durationSec.toFixed(3),
    analysisSampleRate: sr,
    frameCount: nFrames,
    frameSizeMs: cfg.frameSizeMs,
    hopSizeMs: cfg.hopSizeMs,
    medianF0Hz: validF0.length ? +median(validF0).toFixed(2) : null,
    minF0Hz: validF0.length ? +Math.min.apply(null, validF0).toFixed(2) : null,
    maxF0Hz: validF0.length ? +Math.max.apply(null, validF0).toFixed(2) : null,
    validF0FrameRatio: +(validF0.length / nFrames).toFixed(4),
    medianRmsDb: rmsVals.length ? +median(rmsVals).toFixed(2) : null,
    minRmsDb: rmsVals.length ? +Math.min.apply(null, rmsVals).toFixed(2) : null,
    maxRmsDb: rmsVals.length ? +Math.max.apply(null, rmsVals).toFixed(2) : null,
    rmsRangeDb: rmsVals.length ? +(Math.max.apply(null, rmsVals) - Math.min.apply(null, rmsVals)).toFixed(2) : null,
    peakDb: isFinite(peakMax) ? +peakMax.toFixed(2) : null,
    loudnessReferenceDb: +refDb.toFixed(2),
    noiseFloorEstimateDb: +noiseFloorDb.toFixed(2),
    detectedSegmentCount: detectedSegments.length,
    detectedSegmentTotalSec: +detectedSegments.reduce((a, s) => a + s.durationSec, 0).toFixed(3),
    detectedSegmentOpenThresholdDb: +openDb.toFixed(2),
    detectedSegmentCloseThresholdDb: +closeDb.toFixed(2),
    computeMs: Date.now() - t0
  };

  post('progress', { pct: 99, label: '保存中' });

  return {
    frames: F,
    waveform: { min: wmin, max: wmax, count: WV },
    spectrogram: { width: SPEC_W, height: SPEC_H, maxHz: SPEC_H * (specBinCount * binHz) / SPEC_H, topHz: specBinCount * binHz, data: specPix, dbFloor: +floorDb.toFixed(1), dbCeil: +sMax.toFixed(1) },
    detectedSegments,
    summary,
    engine: ENGINE
  };
}

/* 指定範囲の統計（区間統計に共用） */
function rangeStats(F, nFrames, startSec, endSec) {
  const rms = [], f0 = [], conf = [], cen = [], flx = [];
  let voiced = 0, total = 0;
  for (let n = 0; n < nFrames; n++) {
    const t = F.timeSec[n];
    if (t < startSec) continue;
    if (t > endSec) break;
    total++;
    if (F.rmsDb[n] > DB_FLOOR + 1) rms.push(F.rmsDb[n]);
    if (isFinite(F.f0Hz[n])) f0.push(F.f0Hz[n]);
    if (isFinite(F.f0Conf[n])) conf.push(F.f0Conf[n]);
    if (isFinite(F.centroid[n])) cen.push(F.centroid[n]);
    if (isFinite(F.flux[n])) flx.push(F.flux[n]);
    if (F.voicedProb[n] >= 0.5) voiced++;
  }
  const mean = a => a.length ? a.reduce((x, y) => x + y, 0) / a.length : NaN;
  const r = {
    frameCount: total,
    meanRmsDb: rms.length ? +mean(rms).toFixed(2) : null,
    maxRmsDb: rms.length ? +Math.max.apply(null, rms).toFixed(2) : null,
    minRmsDb: rms.length ? +Math.min.apply(null, rms).toFixed(2) : null,
    rmsRangeDb: rms.length ? +(Math.max.apply(null, rms) - Math.min.apply(null, rms)).toFixed(2) : null,
    medianF0Hz: f0.length ? +median(f0).toFixed(2) : null,
    minF0Hz: f0.length ? +Math.min.apply(null, f0).toFixed(2) : null,
    maxF0Hz: f0.length ? +Math.max.apply(null, f0).toFixed(2) : null,
    meanF0Confidence: conf.length ? +mean(conf).toFixed(3) : null,
    validF0Ratio: total ? +(f0.length / total).toFixed(3) : null,
    activeRatio: total ? +(voiced / total).toFixed(3) : null,
    spectralCentroidMeanHz: cen.length ? +mean(cen).toFixed(1) : null,
    spectralFluxMean: flx.length ? +mean(flx).toFixed(4) : null
  };
  return r;
}

/* ================= メッセージ ================= */
function post(type, payload, transfer) {
  self.postMessage(Object.assign({ type }, payload), transfer || []);
}

self.onmessage = function (e) {
  const msg = e.data || {};
  if (msg.type !== 'analyze') return;
  try {
    const result = analyze(msg.pcm, msg.sampleRate, msg.settings);
    const F = result.frames;
    const transfer = Object.keys(F).map(k => F[k].buffer)
      .concat([result.waveform.min.buffer, result.waveform.max.buffer, result.spectrogram.data.buffer]);
    self.postMessage({ type: 'done', result }, transfer);
  } catch (err) {
    self.postMessage({ type: 'error', message: (err && err.message) || String(err) });
  }
};
