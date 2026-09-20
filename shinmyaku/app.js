(() => {
  "use strict";

  const canvas = document.getElementById("game");
  const ctx = canvas.getContext("2d");

  const diveHud = document.getElementById("diveHud");
  const depthVal = document.getElementById("depthVal");
  const hpBar = document.getElementById("hpBar");
  const fuelBar = document.getElementById("fuelBar");
  const muteBtn = document.getElementById("muteBtn");
  const torchBtn = document.getElementById("torchBtn");
  const torchCost = document.getElementById("torchCost");
  const surfaceBtn = document.getElementById("surfaceBtn");
  const heldTray = document.getElementById("heldTray");
  const kodamaBubble = document.getElementById("kodamaBubble");
  const kodamaText = document.getElementById("kodamaText");

  const joyBase = document.getElementById("joyBase");
  const joyKnob = document.getElementById("joyKnob");

  const toastEl = document.getElementById("toast");
  const discoveryCard = document.getElementById("discoveryCard");
  const dcEmoji = document.getElementById("dcEmoji");
  const dcName = document.getElementById("dcName");
  const dcFlavor = document.getElementById("dcFlavor");

  const baseScreen = document.getElementById("baseScreen");
  const bestDepthVal = document.getElementById("bestDepthVal");
  const tierNames = document.getElementById("tierNames");
  const bagNote = document.getElementById("bagNote");
  const bankGrid = document.getElementById("bankGrid");
  const diveBtn = document.getElementById("diveBtn");
  const goalChip = document.getElementById("goalChip");
  const shopBtn = document.getElementById("shopBtn");
  const logBtn = document.getElementById("logBtn");
  const kodamaBtn = document.getElementById("kodamaBtn");
  const baseHelpBtn = document.getElementById("baseHelpBtn");

  const shopOverlay = document.getElementById("shopOverlay");
  const shopBody = document.getElementById("shopBody");
  const shopClose = document.getElementById("shopClose");

  const logOverlay = document.getElementById("logOverlay");
  const logBody = document.getElementById("logBody");
  const logClose = document.getElementById("logClose");

  const kodamaOverlay = document.getElementById("kodamaOverlay");
  const kodamaLog = document.getElementById("kodamaLog");
  const kodamaHint = document.getElementById("kodamaHint");
  const kodamaForm = document.getElementById("kodamaForm");
  const kodamaInput = document.getElementById("kodamaInput");
  const kodamaClose = document.getElementById("kodamaClose");

  const introOverlay = document.getElementById("introOverlay");
  const introBtn = document.getElementById("introBtn");

  const knockoutOverlay = document.getElementById("knockoutOverlay");
  const koText = document.getElementById("koText");
  const koClose = document.getElementById("koClose");

  const SAVE_KEY = "shinmyaku.save.v1";
  const INTRO_KEY = "shinmyaku.introSeen";
  function safeGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function safeSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }

  // ---------- Data ----------
  const MATERIALS = {
    stone: { name: "石", emoji: "🪨", tier: 0, hardness: null, flavor: "ただの石ころ。でも、あらゆるものの土台になる。" },
    coal: { name: "石炭", emoji: "⚫", tier: 0, hardness: 3, flavor: "燃える石。ランタンの灯りを分けてくれる。" },
    copper: { name: "銅鉱石", emoji: "🟠", tier: 0, hardness: 4, flavor: "赤みを帯びた、どこか温かい鉱石。" },
    iron: { name: "鉄鉱石", emoji: "🔩", tier: 1, hardness: 6, flavor: "ずっしり重い。丈夫な道具の材料になる。" },
    silver: { name: "銀鉱石", emoji: "🥈", tier: 2, hardness: 8, flavor: "冷たい光をたたえた、上質な鉱石。" },
    gold: { name: "金鉱石", emoji: "🥇", tier: 2, hardness: 9, flavor: "見つけると、少し得した気分になる。" },
    ruby: { name: "紅玉", emoji: "💎", tier: 3, hardness: 12, flavor: "深部でしか見つからない、赤い結晶。" },
    deepcrystal: { name: "深層水晶", emoji: "🔷", tier: 3, hardness: 14, flavor: "かすかに脈打っている……気がする。" },
    kodamashard: { name: "コダマの欠片", emoji: "🌟", tier: 3, hardness: 16, flavor: "コダマと同じ気配がする、小さなかけら。" },
    monsterEssence: { name: "魔素", emoji: "🟣", tier: 0, hardness: null, dropOnly: true, flavor: "何かが残していった、不思議な粒子。" },
  };

  const ORE_BANDS = [
    { coal: 10, copper: 6 },
    { coal: 8, copper: 8, iron: 5 },
    { copper: 5, iron: 9, silver: 3 },
    { iron: 6, silver: 6, gold: 4 },
    { silver: 5, gold: 6, ruby: 3 },
    { gold: 4, ruby: 4, deepcrystal: 2, kodamashard: 0.5 },
  ];
  const STONE_WEIGHT = 78;
  function bandOf(row) { return Math.min(ORE_BANDS.length - 1, Math.floor(row / 40)); }
  function rollOre(row) {
    const table = ORE_BANDS[bandOf(row)];
    const entries = Object.entries(table);
    const total = STONE_WEIGHT + entries.reduce((s, [, w]) => s + w, 0);
    let r = Math.random() * total;
    if (r < STONE_WEIGHT) return null;
    r -= STONE_WEIGHT;
    for (const [id, w] of entries) { r -= w; if (r <= 0) return id; }
    return null;
  }
  function baseRockHardness(row) { return Math.min(16, 3 + Math.floor(row / 25) * 1.2); }
  function effectiveHardness(tile, row) { return tile.ore ? MATERIALS[tile.ore].hardness : baseRockHardness(row); }
  function requiredTierFor(tile) { return tile.ore ? MATERIALS[tile.ore].tier : 0; }

  const PICKAXE_LEVELS = [
    { label: "木のつるはし", power: 1.0, dmg: 8, cost: null },
    { label: "石のつるはし", power: 1.6, dmg: 12, cost: { stone: 25, coal: 8 } },
    { label: "鉄のつるはし", power: 2.4, dmg: 18, cost: { iron: 16, silver: 6 } },
    { label: "鋼のつるはし", power: 3.4, dmg: 26, cost: { gold: 14, ruby: 5 } },
  ];
  const LANTERN_LEVELS = [
    { label: "Lv0", radius: 3.2, fuel: 90, cost: null },
    { label: "Lv1", radius: 3.9, fuel: 120, cost: { copper: 14, coal: 10 } },
    { label: "Lv2", radius: 4.6, fuel: 150, cost: { iron: 12, silver: 8 } },
    { label: "Lv3", radius: 5.4, fuel: 190, cost: { gold: 10, deepcrystal: 2 } },
  ];
  const VITALITY_LEVELS = [
    { label: "Lv0", maxHp: 100, cost: null },
    { label: "Lv1", maxHp: 130, cost: { stone: 30, copper: 10 } },
    { label: "Lv2", maxHp: 165, cost: { iron: 14, silver: 6 } },
    { label: "Lv3", maxHp: 205, cost: { gold: 12, ruby: 4 } },
  ];
  const KODAMA_LEVELS = [
    { label: "Lv0", desc: "そばで見守ってくれる。", cost: null },
    { label: "Lv1", desc: "危険が近いと知らせてくれるようになる。", cost: { copper: 10, monsterEssence: 4 } },
    { label: "Lv2", desc: "危険を察知する力が上がる。", cost: { silver: 10, monsterEssence: 8 } },
    { label: "Lv3", desc: "言葉を交わせるようになる(会話を解放)。", cost: { kodamashard: 3, monsterEssence: 12 } },
  ];
  const UPGRADE_DEFS = {
    pickaxe: { name: "つるはし", levels: PICKAXE_LEVELS },
    lantern: { name: "ランタン", levels: LANTERN_LEVELS },
    vitality: { name: "体力", levels: VITALITY_LEVELS },
    kodama: { name: "コダマ", levels: KODAMA_LEVELS },
  };

  const MOB_DEFS = {
    shadowbat: { name: "影コウモリ", emoji: "🦇", hp: 20, dmg: 10, speed: 3.0, fly: true, aggro: 4, wake: 5.5, minBand: 0, essence: 2 },
    rockworm: { name: "岩ワーム", emoji: "🪱", hp: 35, dmg: 16, speed: 1.4, fly: false, aggro: 3, wake: 4.5, minBand: 1, essence: 3 },
    deepwraith: { name: "深部霊", emoji: "👻", hp: 55, dmg: 22, speed: 2.0, fly: true, aggro: 5, wake: 6.5, minBand: 4, essence: 6 },
  };
  function mobTableFor(band) {
    return Object.entries(MOB_DEFS).filter(([, d]) => d.minBand <= band);
  }

  const KODAMA_LINES = {
    diveStart: ["さあ、行こうか。", "今日はどこまで潜る?", "足元、気をつけてね。"],
    lowFuel: ["……灯りが弱くなってきた。石炭を探そう。", "そろそろランタンが心もとない。"],
    lowHp: ["危ない、体力が少ない。無理しないで。", "……大丈夫? 引き返すのも大事だよ。"],
    dangerHigh: ["……なんだか、嫌な予感がする。", "静かすぎる……気をつけて。", "……何かの気配がする。"],
    mobDefeated: ["やった、片付いたね。", "よくやった。"],
    knockout: ["大丈夫!? ……荷物の一部を落としてしまったみたい。回収しに行かなきゃ。"],
    depthRecord: ["ここまで来たのは、はじめてだ。"],
    returnSurface: ["お疲れさま。今回もいい収穫だった。", "無事に戻れてよかった。"],
    torchPlaced: ["灯りを置いておこう。ここはもう安心だ。"],
    bagRecovered: ["よかった、落とし物が戻ってきた。"],
    tierUp: ["いい道具だ。もっと深くまで行けそう。"],
  };
  function kline(cat) { const arr = KODAMA_LINES[cat] || ["……"]; return arr[Math.floor(Math.random() * arr.length)]; }

  // ---------- Audio ----------
  // Layered synthesis (filtered tones + shaped noise) through a shared
  // compressor and a small convolution reverb, instead of raw oscillator
  // beeps straight to the output.
  let audioCtx = null, masterGain = null, reverbSend = null, ambientNodes = null;
  function ensureAudio() {
    if (audioCtx) { if (audioCtx.state === "suspended") audioCtx.resume(); return; }
    const AC = window.AudioContext || window.webkitAudioContext;
    audioCtx = new AC();
    const comp = audioCtx.createDynamicsCompressor();
    comp.threshold.value = -20; comp.knee.value = 14; comp.ratio.value = 3.5;
    comp.attack.value = 0.003; comp.release.value = 0.22;
    masterGain = audioCtx.createGain(); masterGain.gain.value = 0.85;
    masterGain.connect(comp).connect(audioCtx.destination);

    const convolver = audioCtx.createConvolver();
    const rate = audioCtx.sampleRate, len = Math.floor(rate * 1.6);
    const ir = audioCtx.createBuffer(2, len, rate);
    for (let ch = 0; ch < 2; ch++) {
      const d = ir.getChannelData(ch);
      for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 2.6);
    }
    convolver.buffer = ir;
    reverbSend = audioCtx.createGain(); reverbSend.gain.value = 0.3;
    reverbSend.connect(convolver).connect(masterGain);
  }
  function wet(node, amount) {
    if (!amount) return;
    const send = audioCtx.createGain(); send.gain.value = amount;
    node.connect(send).connect(reverbSend);
  }
  // A short pitched blip: filtered oscillator with a soft attack and an
  // optional downward pitch sweep, instead of a bare tone straight to gain.
  function blip(freq, dur, type, gain, opts = {}) {
    if (save.muted) return;
    ensureAudio();
    const t0 = audioCtx.currentTime + (opts.delay || 0);
    const osc = audioCtx.createOscillator();
    const filt = audioCtx.createBiquadFilter();
    filt.type = "lowpass"; filt.Q.value = opts.q ?? 0.6;
    filt.frequency.setValueAtTime(opts.cutoff || freq * 5, t0);
    const g = audioCtx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t0);
    if (opts.pitchTo) osc.frequency.exponentialRampToValueAtTime(Math.max(24, opts.pitchTo), t0 + dur * 0.85);
    const attack = opts.attack ?? 0.01;
    g.gain.setValueAtTime(0, t0);
    g.gain.linearRampToValueAtTime(gain, t0 + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    osc.connect(filt).connect(g).connect(masterGain);
    wet(g, opts.wet);
    osc.start(t0); osc.stop(t0 + dur + 0.05);
  }
  // A textured thump: filtered noise burst, optionally paired with a soft
  // low sine underneath for body.
  function thud(dur, gain, opts = {}) {
    if (save.muted) return;
    ensureAudio();
    const t0 = audioCtx.currentTime + (opts.delay || 0);
    const n = Math.floor(audioCtx.sampleRate * dur);
    const buf = audioCtx.createBuffer(1, n, audioCtx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / n, 1.6);
    const src = audioCtx.createBufferSource(); src.buffer = buf;
    const filt = audioCtx.createBiquadFilter();
    filt.type = opts.hp ? "highpass" : "lowpass";
    filt.frequency.value = opts.cutoff || 900;
    const g = audioCtx.createGain(); g.gain.value = gain;
    src.connect(filt).connect(g).connect(masterGain);
    wet(g, opts.wet);
    src.start(t0);
    if (opts.body) {
      const osc = audioCtx.createOscillator(); osc.type = "sine";
      osc.frequency.setValueAtTime(opts.body, t0);
      osc.frequency.exponentialRampToValueAtTime(opts.body * 0.6, t0 + dur * 0.8);
      const bg = audioCtx.createGain();
      bg.gain.setValueAtTime(0, t0); bg.gain.linearRampToValueAtTime(gain * 0.9, t0 + 0.008);
      bg.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
      osc.connect(bg).connect(masterGain); osc.start(t0); osc.stop(t0 + dur + 0.02);
    }
  }
  // A pleasant run of notes on a pentatonic scale, instead of arbitrary Hz.
  const SCALE = [261.63, 293.66, 329.63, 392.0, 440.0, 523.25, 587.33, 659.25];
  function arpeggio(degrees, dur, gain, opts = {}) {
    degrees.forEach((deg, i) => {
      blip(SCALE[deg] * (opts.octave || 1), dur, opts.type || "triangle", gain, { delay: i * (opts.step ?? 0.085), attack: 0.015, wet: opts.wet ?? 0.22, cutoff: opts.cutoff });
    });
  }
  const sfx = {
    hit: () => thud(0.1, 0.16, { cutoff: 1400, body: 130 }),
    break: () => thud(0.14, 0.14, { cutoff: 700, body: 90 }),
    ore: () => arpeggio([2, 4], 0.28, 0.13, { wet: 0.28 }),
    oreRare: () => arpeggio([0, 2, 4, 7], 0.32, 0.15, { wet: 0.34, octave: 1 }),
    hurt: () => thud(0.22, 0.2, { cutoff: 500, body: 110 }),
    danger: () => blip(146.83, 0.9, "sine", 0.05, { cutoff: 300, wet: 0.4 }),
    torch: () => arpeggio([4, 7], 0.22, 0.12, { step: 0.06, wet: 0.25 }),
    upgrade: () => arpeggio([0, 2, 4, 7], 0.24, 0.15, { wet: 0.3 }),
    ko: () => arpeggio([4, 2, 0], 0.4, 0.14, { step: 0.16, type: "sine", wet: 0.4 }),
  };

  // A faint ever-present cave drone while diving: two slow, detuned
  // low oscillators through a gently wandering filter, well under the sfx.
  function startAmbient() {
    if (save.muted || ambientNodes) return;
    ensureAudio();
    const g = audioCtx.createGain(); g.gain.value = 0;
    g.gain.linearRampToValueAtTime(0.05, audioCtx.currentTime + 1.5);
    const filt = audioCtx.createBiquadFilter(); filt.type = "lowpass"; filt.frequency.value = 320;
    const oscs = [98, 98.6].map((f) => {
      const o = audioCtx.createOscillator(); o.type = "sine"; o.frequency.value = f;
      o.connect(filt); o.start(); return o;
    });
    const lfo = audioCtx.createOscillator(); lfo.type = "sine"; lfo.frequency.value = 0.06;
    const lfoGain = audioCtx.createGain(); lfoGain.gain.value = 60;
    lfo.connect(lfoGain).connect(filt.frequency); lfo.start();
    filt.connect(g).connect(masterGain);
    ambientNodes = { oscs, lfo, g };
  }
  function stopAmbient() {
    if (!ambientNodes) return;
    const { oscs, lfo, g } = ambientNodes;
    const t = audioCtx.currentTime;
    g.gain.cancelScheduledValues(t); g.gain.setValueAtTime(g.gain.value, t);
    g.gain.linearRampToValueAtTime(0, t + 0.8);
    setTimeout(() => { oscs.forEach((o) => o.stop()); lfo.stop(); }, 900);
    ambientNodes = null;
  }
  muteBtn.addEventListener("click", () => {
    save.muted = !save.muted; updateMuteBtn(); scheduleSave();
    if (save.muted) stopAmbient(); else if (dive.state === "diving") startAmbient();
  });
  function updateMuteBtn() { muteBtn.textContent = save.muted ? "🔇" : "🔊"; }

  // ---------- Save/load ----------
  function defaultSave() {
    return {
      bank: {}, upgrades: { pickaxe: 0, lantern: 0, vitality: 0, kodama: 0 },
      discovered: [], bestDepth: 0, muted: false,
      world: { rows: [], torches: [], bags: [], pendingPockets: [] },
    };
  }
  let save = loadSave();
  function loadSave() {
    try {
      const raw = safeGet(SAVE_KEY);
      if (!raw) return defaultSave();
      const parsed = JSON.parse(raw);
      const d = defaultSave();
      return { ...d, ...parsed, upgrades: { ...d.upgrades, ...(parsed.upgrades || {}) }, world: { ...d.world, ...(parsed.world || {}) } };
    } catch (e) { return defaultSave(); }
  }
  let saveTimer = 0;
  function scheduleSave() { saveTimer = 0.01; }
  function flushSave() {
    try { safeSet(SAVE_KEY, JSON.stringify(save)); } catch (e) {}
  }

  // ---------- World ----------
  const COLS = 10;
  const BEDROCK = { solid: true, ore: null, progress: 0, discovered: true, torch: false, boundary: true };
  function newTile() { return { solid: true, ore: null, progress: 0, discovered: false, torch: false }; }

  function ensureRowsUpTo(maxRow) {
    while (save.world.rows.length <= maxRow) generateRow(save.world.rows.length);
  }
  function maybeSchedulePocket(uptoRow) {
    if (uptoRow < 6) return;
    const since = save.world._lastPocket || 0;
    if (uptoRow - since > 12 + Math.random() * 10) {
      save.world.pendingPockets.push({ col: 1 + Math.floor(Math.random() * (COLS - 2)), row: uptoRow + 2 + Math.floor(Math.random() * 5), radius: 2 + Math.random() * 2.2 });
      save.world._lastPocket = uptoRow;
    }
  }
  function generateRow(r) {
    maybeSchedulePocket(r);
    const row = [];
    for (let c = 0; c < COLS; c++) {
      if (r < 4) { row.push(Object.assign(newTile(), { solid: false, discovered: true })); continue; }
      let opened = false;
      for (const p of save.world.pendingPockets) {
        if (Math.abs(r - p.row) <= p.radius) {
          const dist = Math.hypot(c - p.col, r - p.row);
          if (dist < p.radius * (0.55 + Math.random() * 0.5)) { opened = true; break; }
        }
      }
      const t = newTile();
      if (opened) { t.solid = false; }
      else { t.ore = rollOre(r); }
      row.push(t);
    }
    save.world.pendingPockets = save.world.pendingPockets.filter((p) => p.row + p.radius >= r);
    save.world.rows.push(row);
  }
  function getTile(col, row) {
    if (col < 0 || col >= COLS || row < 0) return BEDROCK;
    if (row >= save.world.rows.length) return BEDROCK;
    return save.world.rows[row][col];
  }
  function isSolidAt(px, py) {
    return getTile(Math.floor(px / tileSize), Math.floor(py / tileSize)).solid;
  }

  // ---------- Canvas & camera ----------
  let W = 0, H = 0, DPR = 1, tileSize = 40, boardOffsetX = 0;
  function resize() {
    DPR = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth; H = window.innerHeight;
    canvas.width = Math.floor(W * DPR); canvas.height = Math.floor(H * DPR);
    canvas.style.width = W + "px"; canvas.style.height = H + "px";
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    tileSize = Math.max(30, Math.min(56, W / 10));
    boardOffsetX = (W - tileSize * COLS) / 2;
    speeds.move = 3.2 * tileSize; speeds.climb = 2.6 * tileSize;
    speeds.gravity = 7.2 * tileSize; speeds.termFall = 6.5 * tileSize; speeds.down = 2.6 * tileSize;
  }
  window.addEventListener("resize", resize);
  const speeds = { move: 0, climb: 0, gravity: 0, termFall: 0, down: 0 };

  // ---------- Input ----------
  const keys = new Set();
  window.addEventListener("keydown", (e) => {
    const k = e.key.toLowerCase();
    keys.add(k);
    if (["arrowup", "arrowdown", "arrowleft", "arrowright", "w", "a", "s", "d"].includes(k)) e.preventDefault();
  });
  window.addEventListener("keyup", (e) => keys.delete(e.key.toLowerCase()));

  let joyVec = { x: 0, y: 0 }, joyPointerId = null;
  function joyReset() { joyVec = { x: 0, y: 0 }; joyKnob.style.transform = "translate(-50%, -50%)"; }
  joyBase.addEventListener("pointerdown", (e) => { joyPointerId = e.pointerId; joyBase.setPointerCapture(e.pointerId); updateJoy(e); });
  joyBase.addEventListener("pointermove", (e) => { if (e.pointerId === joyPointerId) updateJoy(e); });
  function endJoy(e) { if (e.pointerId === joyPointerId) { joyPointerId = null; joyReset(); } }
  joyBase.addEventListener("pointerup", endJoy);
  joyBase.addEventListener("pointercancel", endJoy);
  function updateJoy(e) {
    const rect = joyBase.getBoundingClientRect();
    const cx = rect.left + rect.width / 2, cy = rect.top + rect.height / 2;
    let dx = e.clientX - cx, dy = e.clientY - cy;
    const max = rect.width / 2, dist = Math.min(Math.hypot(dx, dy), max);
    const angle = Math.atan2(dy, dx);
    dx = Math.cos(angle) * dist; dy = Math.sin(angle) * dist;
    joyVec = { x: dx / max, y: dy / max };
    joyKnob.style.transform = `translate(${dx - 22}px, ${dy - 22}px)`;
  }
  function inputVector() {
    let x = 0, y = 0;
    if (keys.has("arrowleft") || keys.has("a")) x -= 1;
    if (keys.has("arrowright") || keys.has("d")) x += 1;
    if (keys.has("arrowup") || keys.has("w")) y -= 1;
    if (keys.has("arrowdown") || keys.has("s")) y += 1;
    if (x !== 0 || y !== 0) return { x, y };
    return { x: joyVec.x, y: joyVec.y };
  }

  let mineTarget = null;
  let attackCooldown = 0;
  function screenToWorld(sx, sy) { return { x: sx - boardOffsetX, y: sy + camera.y }; }
  canvas.addEventListener("pointerdown", (e) => {
    if (dive.state !== "diving") return;
    const rect = canvas.getBoundingClientRect();
    const w = screenToWorld(e.clientX - rect.left, e.clientY - rect.top);
    const col = Math.floor(w.x / tileSize), row = Math.floor(w.y / tileSize);
    const pc = Math.floor(player.x / tileSize), pr = Math.floor(player.y / tileSize);
    if (Math.abs(col - pc) <= 1 && Math.abs(row - pr) <= 1) {
      const mob = findMobAt(col, row);
      mineTarget = mob ? { mobRef: mob, pointerId: e.pointerId } : { col, row, pointerId: e.pointerId };
    }
  });
  function endMine(e) { if (mineTarget && e.pointerId === mineTarget.pointerId) mineTarget = null; }
  canvas.addEventListener("pointerup", endMine);
  canvas.addEventListener("pointercancel", endMine);

  // ---------- Game state ----------
  const player = { x: 0, y: 0, vx: 0, vy: 0, hp: 100, maxHp: 100, fuel: 90, maxFuel: 90, invuln: 0, hitFlash: 0 };
  const held = {};
  let mobs = [];
  let bagCollectCheck = 0;
  let danger = 0, spawnTimer = 2, dangerWarned = false;
  const camera = { y: 0 };
  let shakeT = 0, shakeMag = 0;
  function shake(mag, t) { shakeT = Math.max(shakeT, t); shakeMag = Math.max(shakeMag, mag); }
  const particles = [];
  const dive = { state: "base" }; // 'base' | 'diving'

  function pickaxeInfo() { return PICKAXE_LEVELS[save.upgrades.pickaxe]; }
  function lanternInfo() { return LANTERN_LEVELS[save.upgrades.lantern]; }
  function vitalityInfo() { return VITALITY_LEVELS[save.upgrades.vitality]; }
  function kodamaInfo() { return KODAMA_LEVELS[save.upgrades.kodama]; }

  function addHeld(id, n) { held[id] = (held[id] || 0) + n; }
  function canAfford(cost) { return Object.entries(cost).every(([id, n]) => (save.bank[id] || 0) >= n); }
  function spend(cost) { Object.entries(cost).forEach(([id, n]) => { save.bank[id] -= n; }); }

  function isLit(x, y) {
    const lr = lanternRadiusPx();
    if (Math.hypot(x - player.x, y - player.y) <= lr) return true;
    for (const t of save.world.torches) {
      const tx = (t.col + 0.5) * tileSize, ty = (t.row + 0.5) * tileSize;
      if (Math.hypot(x - tx, y - ty) <= TORCH_RADIUS_TILES * tileSize) return true;
    }
    return false;
  }
  const TORCH_RADIUS_TILES = 2.6;
  const COAL_REFUEL = 18;
  function lanternRadiusPx() {
    const base = lanternInfo().radius * tileSize;
    return player.fuel > 0 ? base : base * 0.38;
  }

  // ---------- Toast / discovery / kodama bubble ----------
  let toastTimer = null;
  function showToast(msg) {
    toastEl.textContent = msg; toastEl.classList.remove("hidden");
    clearTimeout(toastTimer); toastTimer = setTimeout(() => toastEl.classList.add("hidden"), 2600);
  }
  let cardTimer = null;
  function showDiscovery(id) {
    const m = MATERIALS[id];
    dcEmoji.textContent = m.emoji; dcName.textContent = m.name; dcFlavor.textContent = m.flavor;
    discoveryCard.classList.remove("hidden");
    clearTimeout(cardTimer);
    cardTimer = setTimeout(() => discoveryCard.classList.add("hidden"), 2600);
  }
  let bubbleTimer = null;
  function kodamaSay(cat, customText) {
    const text = customText || kline(cat);
    if (dive.state === "diving") {
      kodamaText.textContent = text;
      kodamaBubble.classList.remove("hidden");
      clearTimeout(bubbleTimer);
      bubbleTimer = setTimeout(() => kodamaBubble.classList.add("hidden"), 4200);
    } else {
      showToast("🔮 " + text);
    }
  }

  // ---------- AI (sample capability) ----------
  let samplePromise = null;
  function getSample() {
    if (!samplePromise) {
      samplePromise = (window.claude && typeof window.claude.use === "function")
        ? window.claude.use("sample").catch(() => null)
        : Promise.resolve(null);
    }
    return samplePromise;
  }
  function aiFlavorFor(materialId) {
    if (save.upgrades.kodama < 3) return;
    getSample().then((sample) => {
      if (!sample) return;
      const m = MATERIALS[materialId];
      const prompt = `あなたは「コダマ」という、鉱山を探索する主人公に寄り添う小さな灯りの精霊です。優しく簡潔に、日本語で1文だけ喋ってください。\n主人公が「${m.name}」という鉱石をはじめて見つけました。この鉱石について、あなたらしい短い一言を返してください(説明文ではなく、セリフとして)。`;
      sample(prompt, { modelTier: "quick", cache: false }).then((res) => {
        if (res && res.text) kodamaSay(null, res.text.trim().slice(0, 120));
      }).catch(() => {});
    });
  }

  let kodamaTurns = [];
  let aiUnavailable = false;
  function kodamaChatIntro() {
    return "あなたは「コダマ」。地底を探索する主人公にずっと寄り添ってきた、小さな灯りの精霊です。温かく、少し詩的だけれど簡潔に(日本語で2〜3文以内)話してください。説明的になりすぎず、相棒として喋ってください。";
  }
  function localChatReply(msg) {
    const s = msg.toLowerCase();
    if (/危な|怖|やば/.test(msg)) return "大丈夫、ちゃんと見ているから。無理はしないで。";
    if (/なに|何|これ/.test(msg)) return "気になるなら、灯りを近づけてみよう。";
    if (/疲れ|つかれ/.test(msg)) return "少し休もうか。深いところは逃げない。";
    if (/ありがとう|感謝/.test(msg)) return "……そういうの、言われると照れるな。";
    return "……うん、聞いてるよ。";
  }
  function appendKodamaLine(role, text) {
    const div = document.createElement("div");
    div.className = "kLine " + (role === "me" ? "me" : "kodama");
    div.textContent = text;
    kodamaLog.appendChild(div);
    kodamaLog.scrollTop = kodamaLog.scrollHeight;
  }
  kodamaForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const msg = kodamaInput.value.trim();
    if (!msg) return;
    kodamaInput.value = "";
    appendKodamaLine("me", msg);

    if (save.upgrades.kodama < 3) {
      setTimeout(() => appendKodamaLine("kodama", localChatReply(msg)), 250);
      return;
    }
    if (aiUnavailable) {
      setTimeout(() => appendKodamaLine("kodama", localChatReply(msg)), 250);
      return;
    }
    getSample().then((sample) => {
      if (!sample) { aiUnavailable = true; kodamaHint.textContent = ""; appendKodamaLine("kodama", localChatReply(msg)); return; }
      const thinking = document.createElement("div");
      thinking.className = "kLine kodama"; thinking.textContent = "……";
      kodamaLog.appendChild(thinking); kodamaLog.scrollTop = kodamaLog.scrollHeight;

      if (kodamaTurns.length === 0) kodamaTurns.push({ role: "user", content: kodamaChatIntro() });
      kodamaTurns.push({ role: "user", content: msg });
      sample(kodamaTurns.slice(-8), { modelTier: "quick", cache: false, onText: ({ text }) => { thinking.textContent = text; kodamaLog.scrollTop = kodamaLog.scrollHeight; } })
        .then((res) => { kodamaTurns.push({ role: "assistant", content: res.text }); })
        .catch((err) => {
          thinking.remove();
          if (["not_granted", "sampling_disabled", "not_declared", "capability_disabled", "capability_removed"].includes(err.code)) {
            aiUnavailable = true;
            kodamaHint.textContent = "(このビューではAI会話は使えないみたい。コダマの気持ちで返すね)";
          }
          appendKodamaLine("kodama", localChatReply(msg));
        });
    });
  });
  kodamaBtn.addEventListener("click", () => {
    kodamaOverlay.classList.remove("hidden");
    if (save.upgrades.kodama < 3) {
      kodamaHint.textContent = "コダマLv3で、もっと自由に話せるようになる。";
    } else {
      kodamaHint.textContent = "";
    }
  });
  kodamaClose.addEventListener("click", () => kodamaOverlay.classList.add("hidden"));

  // ---------- Discovery / material pickup ----------
  function collectMaterial(id, isOre) {
    addHeld(id, 1);
    if (id === "coal") player.fuel = Math.min(player.maxFuel, player.fuel + COAL_REFUEL);
    if (!save.discovered.includes(id)) {
      save.discovered.push(id);
      showDiscovery(id);
      kodamaSay(null, `はじめて見る${MATERIALS[id].name}だ。${MATERIALS[id].flavor}`);
      aiFlavorFor(id);
      scheduleSave();
    } else if (isOre) {
      MATERIALS[id].tier >= 2 ? sfx.oreRare() : sfx.ore();
    }
  }

  function breakTile(col, row) {
    const tile = getTile(col, row);
    const wasOre = tile.ore;
    tile.solid = false; tile.discovered = true;
    burst((col + 0.5) * tileSize, (row + 0.5) * tileSize, "200,180,150", 10, 90, 0.4);
    sfx.break();
    shake(wasOre ? 4 : 2, 0.16);
    if (tile.ore) { collectMaterial(tile.ore, true); tile.ore = null; }
    else { addHeld("stone", 1); }
    tile.progress = 0;
    scheduleSave();
  }

  // ---------- Mobs ----------
  function findMobAt(col, row) {
    return mobs.find((m) => m.alive && Math.floor(m.x / tileSize) === col && Math.floor(m.y / tileSize) === row);
  }
  function spawnMob(defId, col, row) {
    const def = MOB_DEFS[defId];
    mobs.push({
      defId, x: (col + 0.5) * tileSize, y: (row + 0.5) * tileSize, vx: 0, vy: 0,
      hp: def.hp, alive: true, state: "dormant", hitCooldown: 0, wanderT: Math.random() * Math.PI * 2, wanderTimer: 0, bob: Math.random() * 10,
    });
  }
  function openness(col, row) {
    let air = 0, total = 0;
    for (let dr = -2; dr <= 2; dr++) for (let dc = -2; dc <= 2; dc++) { total++; if (!getTile(col + dc, row + dr).solid) air++; }
    return air / total;
  }
  function attemptSpawn() {
    const band = bandOf(Math.floor(player.y / tileSize));
    const table = mobTableFor(band);
    if (table.length === 0 || mobs.filter((m) => m.alive).length >= 3) return;
    for (let tries = 0; tries < 8; tries++) {
      const dc = (Math.random() < 0.5 ? -1 : 1) * (4 + Math.floor(Math.random() * 5));
      const dr = -3 + Math.floor(Math.random() * 7);
      const col = Math.floor(player.x / tileSize) + dc, row = Math.floor(player.y / tileSize) + dr;
      if (row < 6 || row >= save.world.rows.length) continue;
      const t = getTile(col, row);
      if (t.solid) continue;
      const totalW = table.reduce((s, [, d]) => s + 6, 0);
      let r = Math.random() * totalW, pick = table[0][0];
      for (const [id] of table) { r -= 6; if (r <= 0) { pick = id; break; } }
      spawnMob(pick, col, row);
      return;
    }
  }

  // ---------- Physics ----------
  function moveAndCollide(dt) {
    const halfW = tileSize * 0.26, halfH = tileSize * 0.4;
    let nx = player.x + player.vx * dt;
    if (player.vx !== 0) {
      const dir = Math.sign(player.vx);
      const edgeX = nx + dir * halfW;
      if (isSolidAt(edgeX, player.y - halfH * 0.8) || isSolidAt(edgeX, player.y + halfH * 0.8) || isSolidAt(edgeX, player.y)) {
        const col = Math.floor(edgeX / tileSize);
        nx = dir > 0 ? col * tileSize - halfW - 0.5 : (col + 1) * tileSize + halfW + 0.5;
        player.vx = 0;
      }
    }
    player.x = Math.max(halfW, Math.min(COLS * tileSize - halfW, nx));

    let ny = player.y + player.vy * dt;
    if (player.vy !== 0) {
      const dir = Math.sign(player.vy);
      const edgeY = ny + dir * halfH;
      if (isSolidAt(player.x - halfW * 0.8, edgeY) || isSolidAt(player.x + halfW * 0.8, edgeY) || isSolidAt(player.x, edgeY)) {
        const row = Math.floor(edgeY / tileSize);
        ny = dir > 0 ? row * tileSize - halfH - 0.5 : (row + 1) * tileSize + halfH + 0.5;
        player.vy = 0;
      }
    }
    player.y = Math.max(0.5 * tileSize, ny);
  }

  // ---------- Particles ----------
  function burst(x, y, color, count, speed, life) {
    for (let i = 0; i < count; i++) {
      const a = Math.random() * Math.PI * 2, s = speed * (0.4 + Math.random() * 0.6);
      particles.push({ x, y, vx: Math.cos(a) * s, vy: Math.sin(a) * s, life, maxLife: life, color, size: 2 + Math.random() * 3 });
    }
  }

  // ---------- Dive lifecycle ----------
  function startDive() {
    ensureAudio();
    dive.state = "diving";
    baseScreen.classList.add("hidden");
    diveHud.classList.remove("hidden");
    player.maxHp = vitalityInfo().maxHp; player.hp = player.maxHp;
    player.maxFuel = lanternInfo().fuel; player.fuel = player.maxFuel;
    player.x = (COLS / 2) * tileSize; player.y = 1.5 * tileSize;
    Object.keys(held).forEach((k) => delete held[k]);
    mobs = []; danger = 0; dangerWarned = false; spawnTimer = 3;
    ensureRowsUpTo(20);
    updateTorchCost();
    kodamaSay("diveStart");
    renderHeldTray();
    startAmbient();
  }
  function endDiveToSurface(bankAll) {
    if (bankAll) {
      Object.entries(held).forEach(([id, n]) => { save.bank[id] = (save.bank[id] || 0) + n; });
      Object.keys(held).forEach((k) => delete held[k]);
    }
    dive.state = "base";
    diveHud.classList.add("hidden");
    baseScreen.classList.remove("hidden");
    mobs = [];
    stopAmbient();
    renderBase();
    scheduleSave(); flushSave();
  }
  surfaceBtn.addEventListener("click", () => {
    if (dive.state !== "diving") return;
    kodamaSay("returnSurface");
    setTimeout(() => endDiveToSurface(true), 300);
  });

  function triggerKnockout() {
    dive.state = "knockout";
    sfx.ko();
    shake(12, 0.4);
    stopAmbient();
    const col = Math.floor(player.x / tileSize), row = Math.floor(player.y / tileSize);
    const dropped = {};
    Object.entries(held).forEach(([id, n]) => {
      const drop = Math.floor(n * 0.4);
      const keep = n - drop;
      if (drop > 0) dropped[id] = drop;
      if (keep > 0) save.bank[id] = (save.bank[id] || 0) + keep;
    });
    Object.keys(held).forEach((k) => delete held[k]);
    if (Object.keys(dropped).length > 0) {
      save.world.bags.push({ col, row, items: dropped });
    }
    const summary = Object.keys(dropped).length > 0
      ? "落とし物: " + Object.entries(dropped).map(([id, n]) => `${MATERIALS[id].name}×${n}`).join(" / ")
      : "落とし物はなかった。";
    koText.textContent = kline("knockout") + "\n" + summary;
    knockoutOverlay.classList.remove("hidden");
    scheduleSave();
  }
  koClose.addEventListener("click", () => {
    knockoutOverlay.classList.add("hidden");
    endDiveToSurface(false);
  });

  // ---------- Update ----------
  let lastTime = 0;
  function loop(now) {
    let dt = (now - lastTime) / 1000; lastTime = now;
    if (dt > 0.05) dt = 0.05;
    if (dive.state === "diving") update(dt);
    if (saveTimer > 0) { saveTimer -= dt; if (saveTimer <= 0) flushSave(); }
    draw();
    requestAnimationFrame(loop);
  }

  function update(dt) {
    const curRow = Math.floor(player.y / tileSize);
    ensureRowsUpTo(curRow + 14);

    const iv = inputVector();
    player.vx = iv.x * speeds.move;
    if (iv.y < -0.2) player.vy = iv.y * speeds.climb;
    else {
      player.vy += speeds.gravity * dt;
      if (iv.y > 0.2) player.vy = Math.max(player.vy, speeds.down);
      player.vy = Math.min(player.vy, speeds.termFall);
    }
    moveAndCollide(dt);

    // mining / attack
    attackCooldown = Math.max(0, attackCooldown - dt);
    if (mineTarget && mineTarget.mobRef) {
      const mob = mineTarget.mobRef;
      const dist = Math.hypot(mob.x - player.x, mob.y - player.y);
      if (!mob.alive || dist > tileSize * 1.7) {
        mineTarget = null;
      } else if (attackCooldown <= 0) {
        mob.hp -= pickaxeInfo().dmg; attackCooldown = 0.35;
        burst(mob.x, mob.y, "255,220,150", 8, 100, 0.35); sfx.hit();
        shake(3, 0.1);
        if (mob.hp <= 0) {
          mob.alive = false;
          addHeld("monsterEssence", MOB_DEFS[mob.defId].essence);
          kodamaSay("mobDefeated");
          mineTarget = null;
        }
      }
    } else if (mineTarget) {
      const pc = Math.floor(player.x / tileSize), pr = Math.floor(player.y / tileSize);
      if (Math.abs(mineTarget.col - pc) > 1 || Math.abs(mineTarget.row - pr) > 1) { mineTarget = null; }
      else {
        const { col, row } = mineTarget;
        const tile = getTile(col, row);
        const mob = findMobAt(col, row);
        if (mob && mob.alive) {
          mineTarget = { mobRef: mob, pointerId: mineTarget.pointerId };
        } else if (tile.solid && !tile.boundary) {
          if (save.upgrades.pickaxe < requiredTierFor(tile)) {
            if (!mineTarget._warned) { showToast("つるはしが足りない…"); mineTarget._warned = true; }
          } else {
            tile.progress += pickaxeInfo().power * dt;
            if (tile.progress >= effectiveHardness(tile, row)) breakTile(col, row);
          }
        } else {
          mineTarget = null;
        }
      }
    }

    // bag pickup
    const pcol = Math.floor(player.x / tileSize), prow = Math.floor(player.y / tileSize);
    bagCollectCheck -= dt;
    if (bagCollectCheck <= 0) {
      bagCollectCheck = 0.2;
      const idx = save.world.bags.findIndex((b) => b.col === pcol && b.row === prow);
      if (idx >= 0) {
        const bag = save.world.bags[idx];
        Object.entries(bag.items).forEach(([id, n]) => addHeld(id, n));
        save.world.bags.splice(idx, 1);
        showToast("落とし物を回収した");
        kodamaSay("bagRecovered");
        scheduleSave();
      }
    }

    // fuel
    player.fuel = Math.max(0, player.fuel - dt);
    if (player.fuel < player.maxFuel * 0.2 && Math.random() < dt * 0.15) kodamaSay("lowFuel");

    // danger / spawns
    const band = bandOf(curRow);
    const openFactor = openness(pcol, prow);
    let nearTorch = save.world.torches.some((t) => Math.hypot((t.col - pcol), (t.row - prow)) < TORCH_RADIUS_TILES + 1);
    const gain = (0.7 + band * 0.16) * (0.35 + openFactor * 1.3) * (nearTorch ? 0.15 : 1);
    danger = Math.min(100, danger + gain * dt);
    if (danger >= 62 && !dangerWarned) { dangerWarned = true; kodamaSay("dangerHigh"); sfx.danger(); }
    if (danger < 35) dangerWarned = false;
    spawnTimer -= dt;
    if (spawnTimer <= 0) {
      spawnTimer = 2 + Math.random() * 1.2;
      const prob = (danger / 100) * (0.5 + band * 0.12);
      if (Math.random() < prob) { attemptSpawn(); danger = Math.max(0, danger - 38); }
    }

    // mobs
    for (const m of mobs) {
      if (!m.alive) continue;
      const def = MOB_DEFS[m.defId];
      m.bob += dt * 4;
      m.hitCooldown = Math.max(0, m.hitCooldown - dt);
      const dist = Math.hypot(player.x - m.x, player.y - m.y);
      if (m.state === "dormant") {
        if (dist < def.wake * tileSize) m.state = "wander";
      } else {
        if (dist < def.aggro * tileSize) m.state = "chase";
        else if (m.state === "chase" && dist > def.aggro * tileSize * 1.8) m.state = "wander";
      }
      if (m.state === "chase") {
        const a = Math.atan2(player.y - m.y, player.x - m.x);
        m.vx = Math.cos(a) * def.speed * tileSize; m.vy = Math.sin(a) * def.speed * tileSize * (def.fly ? 1 : 0.2);
      } else if (m.state === "wander") {
        m.wanderTimer -= dt;
        if (m.wanderTimer <= 0) { m.wanderT = Math.random() * Math.PI * 2; m.wanderTimer = 1 + Math.random() * 1.4; }
        m.vx = Math.cos(m.wanderT) * def.speed * tileSize * 0.4;
        m.vy = def.fly ? Math.sin(m.wanderT) * def.speed * tileSize * 0.4 : 0;
      } else { m.vx = 0; m.vy = 0; }

      let nx = m.x + m.vx * dt, ny = m.y + m.vy * dt;
      if (!def.fly) { ny += speeds.gravity * 0.6 * dt * dt; }
      if (isSolidAt(nx, m.y)) { nx = m.x; m.wanderT += Math.PI; }
      if (isSolidAt(m.x, ny)) { ny = m.y; if (m.state === "wander") m.wanderT += Math.PI; }
      m.x = Math.max(tileSize * 0.4, Math.min(COLS * tileSize - tileSize * 0.4, nx));
      m.y = Math.max(tileSize * 0.5, ny);

      if (m.state !== "dormant" && m.hitCooldown <= 0 && player.invuln <= 0 && dist < tileSize * 0.6) {
        player.hp -= def.dmg; player.invuln = 1.0; m.hitCooldown = 1.0; player.hitFlash = 0.35;
        sfx.hurt();
        shake(7, 0.25);
        if (player.hp <= 0) { player.hp = 0; triggerKnockout(); }
      }
    }
    mobs = mobs.filter((m) => m.alive);
    player.invuln = Math.max(0, player.invuln - dt);
    player.hitFlash = Math.max(0, player.hitFlash - dt);
    if (player.hp < player.maxHp * 0.25 && Math.random() < dt * 0.1) kodamaSay("lowHp");

    if (curRow > save.bestDepth) {
      const crossed = curRow;
      save.bestDepth = crossed;
      if (crossed > 8) kodamaSay("depthRecord");
      scheduleSave();
    }

    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i]; p.life -= dt;
      if (p.life <= 0) { particles.splice(i, 1); continue; }
      p.x += p.vx * dt; p.y += p.vy * dt; p.vx *= 0.9; p.vy *= 0.9;
    }

    camera.y = player.y - H * 0.42;
    camera.y = Math.max(-tileSize * 2, camera.y);
    if (shakeT > 0) shakeT = Math.max(0, shakeT - dt);

    updateHud();
  }

  function updateHud() {
    depthVal.textContent = Math.max(0, Math.floor(player.y / tileSize)) + "m";
    hpBar.style.width = Math.max(0, (player.hp / player.maxHp) * 100) + "%";
    fuelBar.style.width = Math.max(0, (player.fuel / player.maxFuel) * 100) + "%";
    renderHeldTray();
    updateTorchCost();
  }
  function renderHeldTray() {
    heldTray.innerHTML = "";
    Object.entries(held).forEach(([id, n]) => {
      if (n <= 0) return;
      const chip = document.createElement("div");
      chip.className = "heldChip";
      chip.textContent = `${MATERIALS[id].emoji}${n}`;
      heldTray.appendChild(chip);
    });
  }
  function updateTorchCost() { torchCost.textContent = `(石炭2 / 所持${held.coal || 0})`; }

  torchBtn.addEventListener("click", () => {
    if (dive.state !== "diving") return;
    if ((held.coal || 0) < 2) { showToast("石炭が足りない"); return; }
    const col = Math.floor(player.x / tileSize), row = Math.floor(player.y / tileSize);
    const tile = getTile(col, row);
    if (tile.solid || tile.boundary) { showToast("ここには置けない"); return; }
    held.coal -= 2;
    tile.torch = true;
    save.world.torches.push({ col, row });
    sfx.torch();
    kodamaSay("torchPlaced");
    scheduleSave();
  });

  // ---------- Draw ----------
  function draw() {
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = "#150f0d";
    ctx.fillRect(0, 0, W, H);
    if (dive.state !== "diving" && dive.state !== "knockout") return;

    ctx.save();
    let shakeX = 0, shakeY = 0;
    if (shakeT > 0) {
      const m = shakeMag * (shakeT / 0.3);
      shakeX = (Math.random() * 2 - 1) * m; shakeY = (Math.random() * 2 - 1) * m;
    } else { shakeMag = 0; }
    ctx.translate(boardOffsetX + shakeX, -camera.y + shakeY);

    const rowFrom = Math.max(0, Math.floor(camera.y / tileSize) - 1);
    const rowTo = Math.min(save.world.rows.length - 1, Math.ceil((camera.y + H) / tileSize) + 1);

    // bedrock walls
    ctx.fillStyle = "#0e0a09";
    ctx.fillRect(-tileSize * 2, rowFrom * tileSize, tileSize * 2, (rowTo - rowFrom + 2) * tileSize);
    ctx.fillRect(COLS * tileSize, rowFrom * tileSize, tileSize * 2, (rowTo - rowFrom + 2) * tileSize);

    for (let r = rowFrom; r <= rowTo; r++) {
      const row = save.world.rows[r];
      if (!row) continue;
      for (let c = 0; c < COLS; c++) {
        const tile = row[c];
        const cx = (c + 0.5) * tileSize, cy = (r + 0.5) * tileSize;
        const lit = isLit(cx, cy);
        if (lit) tile.discovered = true;
        if (!tile.discovered) continue;
        const dim = lit ? 1 : 0.32;
        drawTile(tile, c, r, dim);
      }
    }

    for (const bag of save.world.bags) {
      const cx = (bag.col + 0.5) * tileSize, cy = (bag.row + 0.5) * tileSize;
      if (!isLit(cx, cy)) continue;
      ctx.font = `${tileSize * 0.55}px sans-serif`;
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText("🎒", cx, cy);
    }

    for (const m of mobs) {
      if (!m.alive) continue;
      if (!isLit(m.x, m.y)) continue;
      const def = MOB_DEFS[m.defId];
      const bob = Math.sin(m.bob) * 3;
      ctx.globalAlpha = 0.25; ctx.fillStyle = "#000";
      ctx.beginPath(); ctx.ellipse(m.x, m.y + tileSize * 0.35, tileSize * 0.3, tileSize * 0.1, 0, 0, Math.PI * 2); ctx.fill();
      ctx.globalAlpha = 1;
      ctx.font = `${tileSize * 0.6}px sans-serif`;
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText(def.emoji, m.x, m.y + bob);
      const hpFrac = m.hp / def.hp;
      if (hpFrac < 1) {
        ctx.fillStyle = "rgba(0,0,0,0.5)"; ctx.fillRect(m.x - tileSize * 0.3, m.y - tileSize * 0.5, tileSize * 0.6, 4);
        ctx.fillStyle = "#d1483f"; ctx.fillRect(m.x - tileSize * 0.3, m.y - tileSize * 0.5, tileSize * 0.6 * hpFrac, 4);
      }
    }

    drawPlayer();

    for (const p of particles) {
      const a = Math.max(0, p.life / p.maxLife);
      ctx.fillStyle = `rgba(${p.color},${a})`;
      ctx.beginPath(); ctx.arc(p.x, p.y, p.size * a, 0, Math.PI * 2); ctx.fill();
    }

    ctx.restore();

    if (player.hitFlash > 0) {
      ctx.fillStyle = `rgba(209,72,63,${player.hitFlash * 0.4})`;
      ctx.fillRect(0, 0, W, H);
    }
  }

  function drawTile(tile, c, r, dim) {
    const x = c * tileSize, y = r * tileSize;
    if (tile.solid) {
      const shade = 32 + (r % 5) * 4;
      ctx.fillStyle = `rgba(${shade + 20},${shade + 12},${shade},${dim})`;
      ctx.fillRect(x, y, tileSize, tileSize);
      ctx.strokeStyle = `rgba(0,0,0,${0.25 * dim})`;
      ctx.strokeRect(x + 0.5, y + 0.5, tileSize - 1, tileSize - 1);
      if (tile.ore) {
        const m = MATERIALS[tile.ore];
        ctx.globalAlpha = dim;
        ctx.font = `${tileSize * 0.5}px sans-serif`;
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.fillText(m.emoji, x + tileSize / 2, y + tileSize / 2);
        ctx.globalAlpha = 1;
      }
      if (tile.progress > 0) {
        const frac = Math.min(1, tile.progress / effectiveHardness(tile, r));
        ctx.fillStyle = `rgba(255,255,255,${0.35 * dim})`;
        ctx.fillRect(x, y + tileSize * (1 - frac), tileSize, tileSize * frac * 0.15);
        ctx.strokeStyle = `rgba(255,200,120,${0.8 * dim})`;
        ctx.lineWidth = 3;
        ctx.strokeRect(x + 2, y + 2, tileSize - 4, tileSize - 4);
      }
    } else {
      ctx.fillStyle = `rgba(10,8,7,${dim})`;
      ctx.fillRect(x, y, tileSize, tileSize);
      if (tile.torch) {
        ctx.font = `${tileSize * 0.55}px sans-serif`;
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.globalAlpha = dim;
        ctx.fillText("🔥", x + tileSize / 2, y + tileSize / 2);
        ctx.globalAlpha = 1;
      }
    }
  }

  function drawPlayer() {
    ctx.globalAlpha = 0.25; ctx.fillStyle = "#000";
    ctx.beginPath(); ctx.ellipse(player.x, player.y + tileSize * 0.38, tileSize * 0.26, tileSize * 0.1, 0, 0, Math.PI * 2); ctx.fill();
    ctx.globalAlpha = 1;
    ctx.fillStyle = player.invuln > 0 ? "rgba(240,220,190,0.5)" : "#f0dcc0";
    ctx.beginPath(); ctx.arc(player.x, player.y, tileSize * 0.24, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#e08a3e";
    ctx.beginPath(); ctx.arc(player.x, player.y - tileSize * 0.06, tileSize * 0.16, Math.PI, 0); ctx.fill();
    ctx.fillStyle = "rgba(255,214,140,0.9)";
    ctx.beginPath(); ctx.arc(player.x + tileSize * 0.2, player.y, tileSize * 0.09, 0, Math.PI * 2); ctx.fill();
  }

  // ---------- Base camp UI ----------
  function nextGoalText() {
    let affordable = null, closest = null;
    Object.entries(UPGRADE_DEFS).forEach(([key, def]) => {
      const next = def.levels[save.upgrades[key] + 1];
      if (!next) return;
      if (canAfford(next.cost)) { affordable = def.name; return; }
      const shortfalls = Object.entries(next.cost).map(([id, n]) => ({ id, need: Math.max(0, n - (save.bank[id] || 0)) }));
      const total = shortfalls.reduce((s, x) => s + x.need, 0);
      if (!closest || total < closest.total) {
        const top = shortfalls.sort((a, b) => b.need - a.need)[0];
        closest = { name: def.name, matId: top.id, matNeed: top.need, total };
      }
    });
    if (affordable) return `${affordable}を強化できる。拠点で強化しよう。`;
    if (closest) return `${MATERIALS[closest.matId].name}をあと${closest.matNeed}個集めよう(${closest.name}強化に必要)。`;
    if (save.bestDepth < 40) return `もっと深くへ。まだ見ぬ鉱脈が眠っている。`;
    return `すべての強化が完了した。さらに深くを目指そう。`;
  }
  function renderBase() {
    bestDepthVal.textContent = save.bestDepth + "m";
    tierNames.textContent = PICKAXE_LEVELS[save.upgrades.pickaxe].label.replace("のつるはし", "");
    bagNote.textContent = save.world.bags.length > 0 ? `${save.world.bags.length}件` : "なし";
    goalChip.textContent = nextGoalText();
    renderBank();
  }
  function renderBank() {
    bankGrid.innerHTML = "";
    Object.keys(MATERIALS).forEach((id) => {
      const n = save.bank[id] || 0;
      if (n <= 0 && !save.discovered.includes(id)) return;
      const card = document.createElement("div");
      card.className = "bankCard";
      card.innerHTML = `<div class="em">${MATERIALS[id].emoji}</div><div class="ct">${n}</div><div class="nm">${MATERIALS[id].name}</div>`;
      bankGrid.appendChild(card);
    });
    if (!bankGrid.children.length) bankGrid.innerHTML = `<div style="grid-column:1/-1;color:var(--cream-dim);font-size:12px;">まだ何も持ち帰っていない</div>`;
  }

  function renderShop() {
    shopBody.innerHTML = "";
    Object.entries(UPGRADE_DEFS).forEach(([key, def]) => {
      const lvl = save.upgrades[key];
      const cur = def.levels[lvl];
      const next = def.levels[lvl + 1];
      const row = document.createElement("div");
      row.className = "shopRow";
      let desc = "";
      if (key === "pickaxe") desc = next ? `採掘速度と攻撃力が上がる。${next.label}が掘れる鉱石が増える。` : "最高の一振り。";
      else if (key === "lantern") desc = next ? `明かりの範囲: ${cur.radius}→${next.radius} / 灯り持続: ${cur.fuel}s→${next.fuel}s` : "最大まで明るい。";
      else if (key === "vitality") desc = next ? `最大体力: ${cur.maxHp}→${next.maxHp}` : "十分にタフだ。";
      else if (key === "kodama") desc = next ? next.desc : "コダマとの絆は最大だ。";

      const foot = document.createElement("div");
      foot.className = "shopRowFoot";
      const costEl = document.createElement("div");
      costEl.className = "shopCost";
      const btn = document.createElement("button");
      btn.className = "shopBuyBtn";

      if (!next) {
        costEl.textContent = "MAXレベル";
        btn.textContent = "習得済み"; btn.disabled = true; btn.classList.add("max");
      } else {
        costEl.textContent = Object.entries(next.cost).map(([id, n]) => `${MATERIALS[id].emoji}${n}`).join(" ");
        const afford = canAfford(next.cost);
        btn.textContent = afford ? "強化する" : "素材が足りない";
        btn.disabled = !afford;
        btn.addEventListener("click", () => {
          if (!canAfford(next.cost)) return;
          spend(next.cost);
          save.upgrades[key] += 1;
          sfx.upgrade();
          kodamaSay("tierUp");
          scheduleSave(); flushSave();
          renderShop(); renderBase();
        });
      }
      foot.appendChild(costEl); foot.appendChild(btn);

      row.innerHTML = `<div class="shopRowHead"><div class="shopRowTitle">${def.name}</div><div class="shopRowLevel">${cur.label}</div></div><div class="shopRowDesc">${desc}</div>`;
      row.appendChild(foot);
      shopBody.appendChild(row);
    });
  }
  shopBtn.addEventListener("click", () => { renderShop(); shopOverlay.classList.remove("hidden"); });
  shopClose.addEventListener("click", () => shopOverlay.classList.add("hidden"));

  function renderLog() {
    logBody.innerHTML = "";
    const grid = document.createElement("div");
    grid.className = "logGrid";
    Object.entries(MATERIALS).forEach(([id, m]) => {
      const discovered = save.discovered.includes(id);
      const card = document.createElement("div");
      card.className = "logCard" + (discovered ? "" : " undiscovered");
      card.innerHTML = `<div class="em">${discovered ? m.emoji : "❔"}</div><div class="nm">${discovered ? m.name : "？？？"}</div>`;
      grid.appendChild(card);
    });
    logBody.appendChild(grid);
    const count = document.createElement("div");
    count.style.marginTop = "14px"; count.style.fontSize = "12px"; count.style.color = "var(--cream-dim)";
    count.textContent = `${save.discovered.length} / ${Object.keys(MATERIALS).length} 発見`;
    logBody.appendChild(count);
  }
  logBtn.addEventListener("click", () => { renderLog(); logOverlay.classList.remove("hidden"); });
  logClose.addEventListener("click", () => logOverlay.classList.add("hidden"));

  diveBtn.addEventListener("click", startDive);
  baseHelpBtn.addEventListener("click", () => introOverlay.classList.remove("hidden"));
  introBtn.addEventListener("click", () => {
    ensureAudio();
    introOverlay.classList.add("hidden");
    safeSet(INTRO_KEY, "1");
  });

  // ---------- Init ----------
  updateMuteBtn();
  resize();
  ensureRowsUpTo(20);
  renderBase();
  draw();
  requestAnimationFrame((t) => { lastTime = t; requestAnimationFrame(loop); });

  if (safeGet(INTRO_KEY) !== "1") introOverlay.classList.remove("hidden");
})();
