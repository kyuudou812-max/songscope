(() => {
  "use strict";

  const canvas = document.getElementById("game");
  const ctx = canvas.getContext("2d");

  const biomeTabsEl = document.getElementById("biomeTabs");
  const clockChip = document.getElementById("clockChip");
  const zukanBtn = document.getElementById("zukanBtn");
  const zukanCountEl = document.getElementById("zukanCount");
  const helpBtn = document.getElementById("helpBtn");
  const muteBtn = document.getElementById("muteBtn");
  const joyBase = document.getElementById("joyBase");
  const joyKnob = document.getElementById("joyKnob");
  const discoveryCard = document.getElementById("discoveryCard");
  const dcEmoji = document.getElementById("dcEmoji");
  const dcTag = document.getElementById("dcTag");
  const dcName = document.getElementById("dcName");
  const dcFlavor = document.getElementById("dcFlavor");
  const toastEl = document.getElementById("toast");
  const introOverlay = document.getElementById("introOverlay");
  const introBtn = document.getElementById("introBtn");
  const zukanOverlay = document.getElementById("zukanOverlay");
  const zukanClose = document.getElementById("zukanClose");
  const zukanBody = document.getElementById("zukanBody");

  const STORAGE_DISCOVERED = "komorebi.discovered";
  const STORAGE_INTRO = "komorebi.introSeen";
  const STORAGE_MUTE = "komorebi.muted";

  function safeGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function safeSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }

  // ---------- Data ----------
  const RARITY = {
    common:   { weight: 10, hold: 0.5, particles: 10 },
    uncommon: { weight: 4,  hold: 0.8, particles: 16 },
    rare:     { weight: 1.2, hold: 1.2, particles: 24 },
    ultra:    { weight: 0.3, hold: 1.6, particles: 40 },
  };

  const BIOMES = [
    { id: "meadow", name: "草地", unlockAt: 0, ground: "#a9cf7c", ground2: "#94bd68" },
    { id: "pond", name: "池のほとり", unlockAt: 6, ground: "#bcd98f", ground2: "#a7c67a" },
    { id: "night", name: "夜の森", unlockAt: 12, ground: "#2c3b2f", ground2: "#24322a" },
  ];

  const CREATURES = [
    { id: "sparrow", name: "スズメ", emoji: "🐦", biome: "meadow", rarity: "common", time: ["day"], weather: "any", behavior: "passive", flavor: "庭先でもよく見かける、身近な鳥。" },
    { id: "butterfly", name: "モンシロチョウ", emoji: "🦋", biome: "meadow", rarity: "common", time: ["day"], weather: "clear", behavior: "passive", flavor: "花から花へ、ひらひらと渡り歩く。" },
    { id: "ladybug", name: "テントウムシ", emoji: "🐞", biome: "meadow", rarity: "common", time: ["day"], weather: "any", behavior: "passive", flavor: "見つけると少し嬉しくなる、小さな幸運。" },
    { id: "snail", name: "カタツムリ", emoji: "🐌", biome: "meadow", rarity: "common", time: ["any"], weather: "rain", behavior: "passive", flavor: "雨の匂いがすると、そっと顔を出す。" },
    { id: "squirrel", name: "リス", emoji: "🐿️", biome: "meadow", rarity: "uncommon", time: ["day"], weather: "any", behavior: "skittish", flavor: "物音にとても敏感。木の実を探して忙しい。" },
    { id: "bee", name: "ミツバチ", emoji: "🐝", biome: "meadow", rarity: "common", time: ["day"], weather: "clear", behavior: "passive", flavor: "羽音が近づくと、少しどきっとする。" },
    { id: "frog", name: "アマガエル", emoji: "🐸", biome: "meadow", rarity: "uncommon", time: ["any"], weather: "rain", behavior: "passive", flavor: "雨の日だけ、草の上で会える。" },
    { id: "fox", name: "キツネ", emoji: "🦊", biome: "meadow", rarity: "rare", time: ["dusk"], weather: "any", behavior: "skittish", flavor: "夕暮れにしか姿を見せない、用心深い狩人。" },

    { id: "duck", name: "アヒル", emoji: "🦆", biome: "pond", rarity: "common", time: ["day"], weather: "any", behavior: "passive", flavor: "水面をのんびり漂う、平和の象徴。" },
    { id: "turtle", name: "カメ", emoji: "🐢", biome: "pond", rarity: "common", time: ["day"], weather: "any", behavior: "passive", flavor: "岩の上で日向ぼっこをするのが好き。" },
    { id: "koi", name: "コイ", emoji: "🐠", biome: "pond", rarity: "common", time: ["any"], weather: "any", behavior: "passive", flavor: "水面の影に、ゆらりと泳ぐ姿が見える。" },
    { id: "swan", name: "ハクチョウ", emoji: "🦢", biome: "pond", rarity: "uncommon", time: ["dawn", "dusk"], weather: "clear", behavior: "skittish", flavor: "朝と夕方、静かな水面にだけ現れる。" },
    { id: "otter", name: "カワウソ", emoji: "🦦", biome: "pond", rarity: "rare", time: ["day"], weather: "any", behavior: "skittish", flavor: "遊び好きだが、警戒心も強い。" },

    { id: "bat", name: "コウモリ", emoji: "🦇", biome: "night", rarity: "common", time: ["night"], weather: "any", behavior: "skittish", flavor: "夜空を忙しく飛び回る。" },
    { id: "owl", name: "フクロウ", emoji: "🦉", biome: "night", rarity: "uncommon", time: ["night"], weather: "any", behavior: "passive", flavor: "木の枝で、静かにこちらを見ている。" },
    { id: "firefly", name: "ホタル", emoji: "", biome: "night", rarity: "uncommon", time: ["night"], weather: "clear", behavior: "passive", custom: "firefly", flavor: "光の点滅だけが、闇の中の合図。" },
    { id: "spirit", name: "森の精霊", emoji: "", biome: "night", rarity: "ultra", time: ["night"], weather: "clear", behavior: "skittish", custom: "spirit", flavor: "本当にいるのか、誰も確かめられない。" },
  ];
  const CREATURE_BY_ID = Object.fromEntries(CREATURES.map((c) => [c.id, c]));
  const TOTAL_COUNT = CREATURES.length;

  const DAY_LEN = 150; // seconds per full day cycle
  const PHASES = [
    { end: 15, name: "dawn", label: "🌅 明け方" },
    { end: 75, name: "day", label: "☀️ 昼" },
    { end: 95, name: "dusk", label: "🌇 夕暮れ" },
    { end: DAY_LEN, name: "night", label: "🌙 夜" },
  ];
  function phaseAt(t) {
    for (const p of PHASES) if (t < p.end) return p;
    return PHASES[PHASES.length - 1];
  }

  const TINT_ANCHORS = [
    { t: 7.5, c: [255, 198, 150, 0.20] },
    { t: 45, c: [255, 255, 255, 0.0] },
    { t: 85, c: [255, 120, 90, 0.26] },
    { t: 122, c: [15, 20, 60, 0.6] },
  ];
  function tintAt(t) {
    const ext = [
      { t: TINT_ANCHORS[3].t - DAY_LEN, c: TINT_ANCHORS[3].c },
      ...TINT_ANCHORS,
      { t: TINT_ANCHORS[0].t + DAY_LEN, c: TINT_ANCHORS[0].c },
    ];
    for (let i = 0; i < ext.length - 1; i++) {
      const a = ext[i], b = ext[i + 1];
      if (t >= a.t && t <= b.t) {
        const f = (t - a.t) / (b.t - a.t);
        return a.c.map((v, i2) => v + (b.c[i2] - v) * f);
      }
    }
    return [0, 0, 0, 0];
  }

  // ---------- Audio ----------
  let audioCtx = null;
  let muted = safeGet(STORAGE_MUTE) === "1";
  function updateMuteBtn() { muteBtn.textContent = muted ? "🔇" : "🔊"; }
  updateMuteBtn();
  function ensureAudio() {
    if (!audioCtx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      audioCtx = new AC();
    }
    if (audioCtx.state === "suspended") audioCtx.resume();
  }
  function tone(freq, dur, type, gain, delay = 0) {
    if (muted) return;
    ensureAudio();
    const t0 = audioCtx.currentTime + delay;
    const osc = audioCtx.createOscillator();
    const g = audioCtx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t0);
    g.gain.setValueAtTime(0, t0);
    g.gain.linearRampToValueAtTime(gain, t0 + 0.02);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    osc.connect(g).connect(audioCtx.destination);
    osc.start(t0);
    osc.stop(t0 + dur + 0.02);
  }
  function softNoise(dur, gain) {
    if (muted) return;
    ensureAudio();
    const n = Math.floor(audioCtx.sampleRate * dur);
    const buf = audioCtx.createBuffer(1, n, audioCtx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / n) * 0.6;
    const src = audioCtx.createBufferSource();
    src.buffer = buf;
    const filt = audioCtx.createBiquadFilter();
    filt.type = "lowpass";
    filt.frequency.value = 1200;
    const g = audioCtx.createGain();
    g.gain.value = gain;
    src.connect(filt).connect(g).connect(audioCtx.destination);
    src.start();
  }
  const sfx = {
    discover: (rarity) => {
      const seq = { common: [660, 880], uncommon: [523, 659, 880], rare: [440, 587, 740, 987], ultra: [392, 523, 659, 880, 1175] }[rarity] || [660, 880];
      seq.forEach((f, i) => tone(f, 0.22, "triangle", 0.14, i * 0.09));
    },
    unlock: () => { [392, 494, 587, 784].forEach((f, i) => tone(f, 0.28, "sine", 0.13, i * 0.11)); },
    tab: () => tone(500, 0.06, "sine", 0.05),
    rain: () => softNoise(0.9, 0.05),
  };
  muteBtn.addEventListener("click", () => {
    muted = !muted;
    safeSet(STORAGE_MUTE, muted ? "1" : "0");
    updateMuteBtn();
  });

  // ---------- Canvas sizing ----------
  let W = 0, H = 0, DPR = 1, playTop = 90, playBottom = 30;
  function resize() {
    DPR = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth;
    H = window.innerHeight;
    canvas.width = Math.floor(W * DPR);
    canvas.height = Math.floor(H * DPR);
    canvas.style.width = W + "px";
    canvas.style.height = H + "px";
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    playTop = 86;
    playBottom = 28;
    game.player.x = Math.min(Math.max(game.player.x, 30), W - 30);
    game.player.y = Math.min(Math.max(game.player.y, playTop + 20), H - playBottom - 20);
  }
  window.addEventListener("resize", resize);

  // ---------- Persistence ----------
  function loadDiscovered() {
    try {
      const raw = safeGet(STORAGE_DISCOVERED);
      return new Set(raw ? JSON.parse(raw) : []);
    } catch (e) { return new Set(); }
  }
  function saveDiscovered() {
    safeSet(STORAGE_DISCOVERED, JSON.stringify([...game.discovered]));
  }

  // ---------- Game state ----------
  const game = {
    discovered: loadDiscovered(),
    currentBiome: "meadow",
    worldTime: 40,
    rain: { active: false, timer: 25 + Math.random() * 30 },
    player: { x: 0, y: 0, vx: 0, vy: 0 },
    active: [],
    ambient: [],
    particles: [],
    spawnCooldown: 0,
    toastQueue: [],
    discoveryQueue: [],
    running: false,
  };

  function unlockedBiomes() {
    return BIOMES.filter((b) => game.discovered.size >= b.unlockAt);
  }

  // ---------- Input ----------
  const keys = new Set();
  window.addEventListener("keydown", (e) => {
    keys.add(e.key.toLowerCase());
    if (["arrowup", "arrowdown", "arrowleft", "arrowright", "w", "a", "s", "d"].includes(e.key.toLowerCase())) e.preventDefault();
  });
  window.addEventListener("keyup", (e) => keys.delete(e.key.toLowerCase()));

  let joyVec = { x: 0, y: 0 };
  let joyPointerId = null;
  function joyReset() {
    joyVec = { x: 0, y: 0 };
    joyKnob.style.transform = "translate(-50%, -50%)";
  }
  joyBase.addEventListener("pointerdown", (e) => {
    joyPointerId = e.pointerId;
    joyBase.setPointerCapture(e.pointerId);
    updateJoy(e);
  });
  joyBase.addEventListener("pointermove", (e) => {
    if (e.pointerId === joyPointerId) updateJoy(e);
  });
  function endJoy(e) {
    if (e.pointerId === joyPointerId) { joyPointerId = null; joyReset(); }
  }
  joyBase.addEventListener("pointerup", endJoy);
  joyBase.addEventListener("pointercancel", endJoy);
  function updateJoy(e) {
    const rect = joyBase.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    let dx = e.clientX - cx, dy = e.clientY - cy;
    const max = rect.width / 2;
    const dist = Math.min(Math.hypot(dx, dy), max);
    const angle = Math.atan2(dy, dx);
    dx = Math.cos(angle) * dist;
    dy = Math.sin(angle) * dist;
    joyVec = { x: dx / max, y: dy / max };
    joyKnob.style.transform = `translate(${dx - 23}px, ${dy - 23}px)`;
  }

  function inputVector() {
    let x = 0, y = 0;
    if (keys.has("arrowleft") || keys.has("a")) x -= 1;
    if (keys.has("arrowright") || keys.has("d")) x += 1;
    if (keys.has("arrowup") || keys.has("w")) y -= 1;
    if (keys.has("arrowdown") || keys.has("s")) y += 1;
    if (x !== 0 || y !== 0) {
      const len = Math.hypot(x, y) || 1;
      return { x: x / len, y: y / len };
    }
    return { x: joyVec.x, y: joyVec.y };
  }

  // ---------- Biome tabs ----------
  function renderTabs() {
    biomeTabsEl.innerHTML = "";
    BIOMES.forEach((b) => {
      const unlocked = game.discovered.size >= b.unlockAt;
      const btn = document.createElement("button");
      btn.className = "tab" + (b.id === game.currentBiome ? " active" : "") + (!unlocked ? " locked" : "");
      btn.textContent = unlocked ? b.name : `🔒 ${b.name}`;
      btn.addEventListener("click", () => {
        if (!unlocked) {
          showToast(`あと${b.unlockAt - game.discovered.size}匹の発見で解放`);
          return;
        }
        if (game.currentBiome !== b.id) {
          game.currentBiome = b.id;
          game.active = [];
          sfx.tab();
          renderTabs();
        }
      });
      biomeTabsEl.appendChild(btn);
    });
  }

  function glowTabIfNewlyUnlocked(biomeId) {
    renderTabs();
    const idx = BIOMES.findIndex((b) => b.id === biomeId);
    const btn = biomeTabsEl.children[idx];
    if (btn) {
      btn.classList.add("glow");
      setTimeout(() => btn.classList.remove("glow"), 5000);
    }
  }

  // ---------- Toast / discovery card ----------
  let toastTimer = null;
  function showToast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.remove("hidden");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.add("hidden"), 2600);
  }

  let cardTimer = null;
  let cardShowing = false;
  function processDiscoveryQueue() {
    if (cardShowing || game.discoveryQueue.length === 0) return;
    const item = game.discoveryQueue.shift();
    cardShowing = true;
    dcEmoji.textContent = item.def.custom === "spirit" ? "🌫️" : item.def.custom === "firefly" ? "🌟" : item.def.emoji;
    dcTag.textContent = "はじめて出会った";
    dcName.textContent = item.def.name;
    dcFlavor.textContent = item.def.flavor;
    discoveryCard.classList.remove("hidden");
    zukanCountEl.textContent = `${game.discovered.size}/${TOTAL_COUNT}`;
    sfx.discover(item.def.rarity);
    clearTimeout(cardTimer);
    cardTimer = setTimeout(() => {
      discoveryCard.classList.add("hidden");
      cardShowing = false;
      setTimeout(processDiscoveryQueue, 350);
    }, 2400);
  }

  // ---------- Zukan ----------
  function renderZukan() {
    zukanBody.innerHTML = "";
    BIOMES.forEach((b) => {
      const section = document.createElement("div");
      section.className = "zukanSection";
      const unlocked = game.discovered.size >= b.unlockAt;
      const title = document.createElement("div");
      title.className = "zukanSectionTitle";
      title.textContent = `${b.name}`;
      section.appendChild(title);

      if (!unlocked) {
        const lock = document.createElement("div");
        lock.className = "zukanLock";
        lock.textContent = `🔒 あと${b.unlockAt - game.discovered.size}匹の発見で解放されます`;
        section.appendChild(lock);
      } else {
        const grid = document.createElement("div");
        grid.className = "zukanGrid";
        CREATURES.filter((c) => c.biome === b.id).forEach((c) => {
          const discovered = game.discovered.has(c.id);
          const card = document.createElement("div");
          card.className = "zukanCard" + (discovered ? ` rarity-${c.rarity}` : " undiscovered");
          const em = document.createElement("div");
          em.className = "em";
          em.textContent = discovered ? (c.custom === "spirit" ? "🌫️" : c.custom === "firefly" ? "🌟" : c.emoji) : "❔";
          const nm = document.createElement("div");
          nm.className = "nm";
          nm.textContent = discovered ? c.name : "？？？";
          card.appendChild(em);
          card.appendChild(nm);
          grid.appendChild(card);
        });
        section.appendChild(grid);
      }
      zukanBody.appendChild(section);
    });
  }

  zukanBtn.addEventListener("click", () => { renderZukan(); zukanOverlay.classList.remove("hidden"); });
  zukanClose.addEventListener("click", () => zukanOverlay.classList.add("hidden"));

  // ---------- Intro ----------
  helpBtn.addEventListener("click", () => introOverlay.classList.remove("hidden"));
  introBtn.addEventListener("click", () => {
    ensureAudio();
    introOverlay.classList.add("hidden");
    safeSet(STORAGE_INTRO, "1");
    start();
  });
  if (safeGet(STORAGE_INTRO) === "1") {
    introOverlay.classList.add("hidden");
  }

  // ---------- Spawning ----------
  function eligibleDefs(phaseName) {
    const weatherNow = game.rain.active ? "rain" : "clear";
    return CREATURES.filter((c) => {
      if (c.biome !== game.currentBiome) return false;
      const timeOk = c.time.includes("any") || c.time.includes(phaseName);
      const weatherOk = c.weather === "any" || c.weather === weatherNow;
      const alreadyActive = game.active.some((a) => a.defId === c.id);
      return timeOk && weatherOk && !alreadyActive;
    });
  }

  function weightedPick(defs) {
    const total = defs.reduce((s, d) => s + RARITY[d.rarity].weight, 0);
    let r = Math.random() * total;
    for (const d of defs) {
      r -= RARITY[d.rarity].weight;
      if (r <= 0) return d;
    }
    return defs[defs.length - 1];
  }

  function spawnCreature(def) {
    const edge = Math.floor(Math.random() * 4);
    let x, y;
    const top = playTop + 20, bottom = H - playBottom - 20;
    if (edge === 0) { x = 20; y = top + Math.random() * (bottom - top); }
    else if (edge === 1) { x = W - 20; y = top + Math.random() * (bottom - top); }
    else if (edge === 2) { x = 20 + Math.random() * (W - 40); y = top; }
    else { x = 20 + Math.random() * (W - 40); y = bottom; }
    game.active.push({
      defId: def.id, x, y, vx: 0, vy: 0,
      state: "wander", wanderTimer: 0, holdTimer: 0, fleeTimer: 0,
      dirT: Math.random() * Math.PI * 2, bob: Math.random() * Math.PI * 2,
      speed: def.behavior === "skittish" ? 46 : 30,
      alertRadius: def.behavior === "skittish" ? 120 : 74,
      observeRadius: def.behavior === "skittish" ? 58 : 74,
    });
  }

  function updateSpawns(dt) {
    game.spawnCooldown -= dt;
    const target = 4;
    if (game.active.length < target && game.spawnCooldown <= 0) {
      const phase = phaseAt(game.worldTime).name;
      const defs = eligibleDefs(phase);
      if (defs.length > 0) {
        spawnCreature(weightedPick(defs));
        game.spawnCooldown = 1.1 + Math.random() * 0.8;
      } else {
        game.spawnCooldown = 2;
      }
    }
  }

  // ---------- Weather ----------
  function updateWeather(dt) {
    game.rain.timer -= dt;
    if (game.rain.timer <= 0) {
      if (!game.rain.active) {
        if (Math.random() < 0.45) {
          game.rain.active = true;
          game.rain.timer = 18 + Math.random() * 22;
        } else {
          game.rain.timer = 12 + Math.random() * 15;
        }
      } else {
        game.rain.active = false;
        game.rain.timer = 45 + Math.random() * 50;
      }
    }
    if (game.rain.active) {
      game.rainSoundTimer = (game.rainSoundTimer || 0) - dt;
      if (game.rainSoundTimer <= 0) { sfx.rain(); game.rainSoundTimer = 1.6; }
      for (let i = 0; i < 2; i++) {
        game.particles.push({ kind: "rain", x: Math.random() * W, y: -10, vx: -40, vy: 420 + Math.random() * 120, life: 2, maxLife: 2 });
      }
    }
  }

  // ---------- Particle helpers ----------
  function burst(x, y, color, count, speed = 160, life = 0.6) {
    for (let i = 0; i < count; i++) {
      const a = Math.random() * Math.PI * 2;
      const s = speed * (0.4 + Math.random() * 0.6);
      game.particles.push({ kind: "spark", x, y, vx: Math.cos(a) * s, vy: Math.sin(a) * s, life, maxLife: life, color, size: 2 + Math.random() * 3 });
    }
  }

  // ---------- Discovery logic ----------
  function discover(defId) {
    const def = CREATURE_BY_ID[defId];
    const isNew = !game.discovered.has(defId);
    if (isNew) {
      game.discovered.add(defId);
      saveDiscovered();
      game.discoveryQueue.push({ def });
      processDiscoveryQueue();
      const newlyUnlocked = BIOMES.find((b) => b.unlockAt === game.discovered.size);
      if (newlyUnlocked) {
        setTimeout(() => {
          showToast(`新しいエリア『${newlyUnlocked.name}』が解放されました`);
          sfx.unlock();
          glowTabIfNewlyUnlocked(newlyUnlocked.id);
        }, 2500);
      }
    }
  }

  // ---------- Update ----------
  let lastTime = 0;
  function loop(now) {
    let dt = (now - lastTime) / 1000;
    lastTime = now;
    if (dt > 0.05) dt = 0.05;
    if (game.running) update(dt);
    draw();
    requestAnimationFrame(loop);
  }

  function update(dt) {
    game.worldTime = (game.worldTime + dt) % DAY_LEN;
    updateWeather(dt);
    updateSpawns(dt);

    const iv = inputVector();
    const speed = 150;
    game.player.vx = iv.x * speed;
    game.player.vy = iv.y * speed;
    game.player.x = Math.min(Math.max(game.player.x + game.player.vx * dt, 26), W - 26);
    game.player.y = Math.min(Math.max(game.player.y + game.player.vy * dt, playTop + 16), H - playBottom - 16);
    const playerSpeed = Math.hypot(game.player.vx, game.player.vy);

    for (let i = game.active.length - 1; i >= 0; i--) {
      const e = game.active[i];
      const def = CREATURE_BY_ID[e.defId];
      const dx = game.player.x - e.x, dy = game.player.y - e.y;
      const dist = Math.hypot(dx, dy);
      e.bob += dt * 3;

      if (e.state === "fleeing") {
        e.fleeTimer -= dt;
        const a = Math.atan2(e.y - game.player.y, e.x - game.player.x);
        e.vx = Math.cos(a) * e.speed * 2.2;
        e.vy = Math.sin(a) * e.speed * 2.2;
        if (e.fleeTimer <= 0) e.state = "wander";
      } else {
        const skittish = def.behavior === "skittish";
        if (skittish && dist < e.alertRadius && playerSpeed > 95) {
          e.state = "fleeing"; e.fleeTimer = 1.1; e.holdTimer = 0;
        } else if (dist < e.observeRadius) {
          e.state = "alert";
          if (playerSpeed < 20) {
            e.holdTimer += dt;
            const req = RARITY[def.rarity].hold;
            if (e.holdTimer >= req) {
              const wasNew = !game.discovered.has(e.defId);
              discover(e.defId);
              burst(e.x, e.y, wasNew ? "255,213,120" : "170,220,180", RARITY[def.rarity].particles, 130, 0.7);
              game.active.splice(i, 1);
              continue;
            }
          } else {
            e.holdTimer = Math.max(0, e.holdTimer - dt * 1.5);
          }
        } else {
          e.state = "wander";
          e.holdTimer = Math.max(0, e.holdTimer - dt);
        }

        if (e.state !== "alert" || dist >= e.observeRadius) {
          e.wanderTimer -= dt;
          if (e.wanderTimer <= 0) {
            e.dirT = Math.random() * Math.PI * 2;
            e.wanderTimer = 1.2 + Math.random() * 1.6;
          }
          e.vx = Math.cos(e.dirT) * e.speed * 0.5;
          e.vy = Math.sin(e.dirT) * e.speed * 0.5;
        } else {
          e.vx *= 0.8; e.vy *= 0.8;
        }
      }

      e.x += e.vx * dt;
      e.y += e.vy * dt;
      const top = playTop + 16, bottom = H - playBottom - 16;
      if (e.x < 10 || e.x > W - 10 || e.y < top - 10 || e.y > bottom + 10) {
        if (e.state !== "fleeing" || dist > 400) {
          game.active.splice(i, 1);
        }
      }
    }

    for (let i = game.particles.length - 1; i >= 0; i--) {
      const p = game.particles[i];
      p.life -= dt;
      if (p.life <= 0 || p.y > H + 30) { game.particles.splice(i, 1); continue; }
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      if (p.kind === "spark") { p.vx *= 0.94; p.vy *= 0.94; }
    }

    if (Math.random() < 0.02 && game.ambient.length < 14) {
      game.ambient.push({ x: Math.random() * W, y: playTop + Math.random() * (H - playTop - playBottom), t: Math.random() * Math.PI * 2, kind: phaseAt(game.worldTime).name === "night" ? "mote" : "pollen" });
    }
    game.ambient.forEach((a) => { a.t += dt; a.y -= dt * 6; a.x += Math.sin(a.t) * 8 * dt; });
    game.ambient = game.ambient.filter((a) => a.y > playTop - 20);
  }

  // ---------- Draw ----------
  function draw() {
    ctx.clearRect(0, 0, W, H);
    const biome = BIOMES.find((b) => b.id === game.currentBiome);
    const phase = phaseAt(game.worldTime);

    drawGround(biome, phase);
    drawAmbient(phase);
    drawCreatures();
    drawPlayer();
    drawParticles();
    drawTint(phase);

    clockChip.textContent = phase.label + (game.rain.active ? " 🌧" : "");
  }

  function drawGround(biome, phase) {
    const g = ctx.createLinearGradient(0, playTop, 0, H);
    g.addColorStop(0, biome.ground);
    g.addColorStop(1, biome.ground2);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);

    if (biome.id === "pond") {
      ctx.fillStyle = "rgba(111,179,201,0.75)";
      ctx.beginPath();
      ctx.ellipse(W * 0.55, H * 0.55, W * 0.4, H * 0.28, 0, 0, Math.PI * 2);
      ctx.fill();
    }
    if (biome.id === "night") {
      if (phase.name === "night") {
        ctx.fillStyle = "rgba(255,255,255,0.5)";
        (game._stars = game._stars || Array.from({ length: 40 }, () => ({ x: Math.random() * W, y: playTop + Math.random() * (H * 0.5), s: Math.random() * 1.6 })));
        game._stars.forEach((s) => { ctx.globalAlpha = 0.4 + 0.4 * Math.sin(game.worldTime + s.x); ctx.beginPath(); ctx.arc(s.x, s.y, s.s, 0, Math.PI * 2); ctx.fill(); });
        ctx.globalAlpha = 1;
      }
      ctx.fillStyle = "rgba(20,30,20,0.5)";
      for (let i = 0; i < 6; i++) {
        const x = (i / 6) * W + 30;
        ctx.beginPath();
        ctx.ellipse(x, H - 10, 34, 60, 0, 0, Math.PI * 2);
        ctx.fill();
      }
    } else {
      ctx.fillStyle = "rgba(255,255,255,0.18)";
      for (let i = 0; i < 5; i++) {
        ctx.beginPath();
        ctx.ellipse((i * 197 + 60) % W, playTop + ((i * 133) % (H - playTop - playBottom)), 3, 3, 0, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  function drawAmbient(phase) {
    game.ambient.forEach((a) => {
      ctx.globalAlpha = 0.5;
      ctx.fillStyle = a.kind === "mote" ? "rgba(255,240,180,0.8)" : "rgba(255,255,255,0.8)";
      ctx.beginPath();
      ctx.arc(a.x, a.y, a.kind === "mote" ? 2 : 2.4, 0, Math.PI * 2);
      ctx.fill();
    });
    ctx.globalAlpha = 1;
  }

  function drawCreatures() {
    game.active.forEach((e) => {
      const def = CREATURE_BY_ID[e.defId];
      const bobY = Math.sin(e.bob) * 3;
      ctx.globalAlpha = 0.22;
      ctx.fillStyle = "#000";
      ctx.beginPath();
      ctx.ellipse(e.x, e.y + 16, 14, 5, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;

      if (def.custom === "firefly") {
        const glow = 0.5 + 0.5 * Math.sin(e.bob * 2);
        ctx.fillStyle = `rgba(255,240,140,${0.5 + glow * 0.5})`;
        ctx.shadowColor = "rgba(255,240,140,0.9)";
        ctx.shadowBlur = 16 + glow * 10;
        ctx.beginPath();
        ctx.arc(e.x, e.y + bobY, 5, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
      } else if (def.custom === "spirit") {
        const pulse = 0.6 + 0.4 * Math.sin(e.bob);
        ctx.fillStyle = `rgba(210,190,255,${0.35 * pulse})`;
        ctx.shadowColor = "rgba(210,190,255,0.8)";
        ctx.shadowBlur = 26;
        ctx.beginPath();
        ctx.arc(e.x, e.y + bobY, 22, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = `rgba(255,255,255,${0.8 * pulse})`;
        ctx.beginPath();
        ctx.arc(e.x - 6, e.y + bobY - 2, 2, 0, Math.PI * 2);
        ctx.arc(e.x + 6, e.y + bobY - 2, 2, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
      } else {
        ctx.font = "28px 'Apple Color Emoji','Segoe UI Emoji',sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(def.emoji, e.x, e.y + bobY);
      }

      if (e.state === "alert" && e.holdTimer > 0) {
        const req = RARITY[def.rarity].hold;
        const frac = Math.min(1, e.holdTimer / req);
        ctx.strokeStyle = "rgba(233,138,78,0.9)";
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(e.x, e.y + bobY, 22, -Math.PI / 2, -Math.PI / 2 + frac * Math.PI * 2);
        ctx.stroke();
      }
    });
  }

  function drawPlayer() {
    const p = game.player;
    ctx.globalAlpha = 0.25;
    ctx.fillStyle = "#000";
    ctx.beginPath();
    ctx.ellipse(p.x, p.y + 16, 15, 5, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;

    ctx.fillStyle = "#f3d9a4";
    ctx.beginPath();
    ctx.arc(p.x, p.y, 15, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#e98a4e";
    ctx.beginPath();
    ctx.arc(p.x, p.y - 4, 10, Math.PI, 0);
    ctx.fill();
  }

  function drawParticles() {
    game.particles.forEach((p) => {
      if (p.kind === "rain") {
        ctx.strokeStyle = "rgba(210,225,235,0.5)";
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(p.x + p.vx * 0.03, p.y + p.vy * 0.03);
        ctx.stroke();
      } else {
        const a = Math.max(0, p.life / p.maxLife);
        ctx.fillStyle = `rgba(${p.color},${a})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * a, 0, Math.PI * 2);
        ctx.fill();
      }
    });
  }

  function drawTint(phase) {
    const [r, g, b, a] = tintAt(game.worldTime);
    if (a > 0.01) {
      ctx.fillStyle = `rgba(${r | 0},${g | 0},${b | 0},${a})`;
      ctx.fillRect(0, 0, W, H);
    }
    if (game.rain.active) {
      ctx.fillStyle = "rgba(40,55,70,0.12)";
      ctx.fillRect(0, 0, W, H);
    }
  }

  // ---------- Init ----------
  function start() {
    game.running = true;
    resize();
    game.player.x = W / 2;
    game.player.y = H * 0.6;
    renderTabs();
    zukanCountEl.textContent = `${game.discovered.size}/${TOTAL_COUNT}`;
    lastTime = performance.now();
    requestAnimationFrame(loop);
  }

  resize();
  renderTabs();
  zukanCountEl.textContent = `${game.discovered.size}/${TOTAL_COUNT}`;
  draw();

  if (safeGet(STORAGE_INTRO) === "1") {
    start();
  }
})();
