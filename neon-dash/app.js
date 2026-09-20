(() => {
  "use strict";

  const canvas = document.getElementById("game");
  const ctx = canvas.getContext("2d");

  const scoreEl = document.getElementById("score");
  const bestEl = document.getElementById("best");
  const comboEl = document.getElementById("combo");
  const comboWrap = document.getElementById("comboWrap");
  const startScreen = document.getElementById("startScreen");
  const overScreen = document.getElementById("overScreen");
  const overTitle = document.getElementById("overTitle");
  const finalScoreEl = document.getElementById("finalScore");
  const overBestEl = document.getElementById("overBest");
  const recordBanner = document.getElementById("recordBanner");
  const startBtn = document.getElementById("startBtn");
  const retryBtn = document.getElementById("retryBtn");
  const muteBtn = document.getElementById("muteBtn");
  const zoneLeft = document.getElementById("zoneLeft");
  const zoneRight = document.getElementById("zoneRight");

  const STORAGE_BEST = "neonDash.best";
  const STORAGE_MUTE = "neonDash.muted";

  // ---------- Audio ----------
  let audioCtx = null;
  let muted = localStorage.getItem(STORAGE_MUTE) === "1";
  updateMuteBtn();

  function ensureAudio() {
    if (!audioCtx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      audioCtx = new AC();
    }
    if (audioCtx.state === "suspended") audioCtx.resume();
  }

  function tone(freq, dur, type = "sine", gain = 0.2, delay = 0) {
    if (muted) return;
    ensureAudio();
    const t0 = audioCtx.currentTime + delay;
    const osc = audioCtx.createOscillator();
    const g = audioCtx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t0);
    g.gain.setValueAtTime(0, t0);
    g.gain.linearRampToValueAtTime(gain, t0 + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    osc.connect(g).connect(audioCtx.destination);
    osc.start(t0);
    osc.stop(t0 + dur + 0.02);
  }

  function noiseBurst(dur, gain = 0.25) {
    if (muted) return;
    ensureAudio();
    const bufferSize = Math.floor(audioCtx.sampleRate * dur);
    const buffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = (Math.random() * 2 - 1) * (1 - i / bufferSize);
    }
    const src = audioCtx.createBufferSource();
    src.buffer = buffer;
    const g = audioCtx.createGain();
    g.gain.setValueAtTime(gain, audioCtx.currentTime);
    src.connect(g).connect(audioCtx.destination);
    src.start();
  }

  const sfx = {
    switch: () => tone(520, 0.06, "square", 0.06),
    collect: (comboLevel) => {
      const base = 660 + Math.min(comboLevel, 10) * 40;
      tone(base, 0.09, "triangle", 0.16);
    },
    shield: () => { tone(300, 0.12, "sawtooth", 0.15); tone(600, 0.16, "sine", 0.12, 0.05); },
    hit: () => { noiseBurst(0.25, 0.3); tone(120, 0.3, "sawtooth", 0.2); },
    record: () => {
      [523, 659, 784, 1046].forEach((f, i) => tone(f, 0.18, "triangle", 0.18, i * 0.09));
    },
  };

  function updateMuteBtn() {
    muteBtn.textContent = muted ? "🔇" : "🔊";
  }
  muteBtn.addEventListener("click", () => {
    muted = !muted;
    localStorage.setItem(STORAGE_MUTE, muted ? "1" : "0");
    updateMuteBtn();
  });

  // ---------- Canvas sizing ----------
  let W = 0, H = 0, DPR = 1;
  function resize() {
    DPR = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth;
    H = window.innerHeight;
    canvas.width = Math.floor(W * DPR);
    canvas.height = Math.floor(H * DPR);
    canvas.style.width = W + "px";
    canvas.style.height = H + "px";
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    laneX = [W * 0.25, W * 0.5, W * 0.75];
    playerY = H * 0.78;
  }
  window.addEventListener("resize", resize);

  // ---------- Game constants ----------
  const LANES = 3;
  let laneX = [0, 0, 0];
  let playerY = 0;
  const PLAYER_R = 16;
  const OBSTACLE_H = 26;
  const GEM_R = 12;

  const BASE_FALL_SPEED = 340;   // px/s
  const MAX_FALL_SPEED = 900;
  const SPEED_RAMP = 6;          // px/s per second survived

  const BASE_SPAWN_INTERVAL = 1.05;
  const MIN_SPAWN_INTERVAL = 0.42;
  const SPAWN_RAMP = 0.012;

  const LANE_SWITCH_TIME = 0.10; // seconds to glide between lanes

  // ---------- State ----------
  let state = null;

  function freshState() {
    return {
      running: false,
      over: false,
      lane: 1,
      targetLane: 1,
      laneAnimT: 1,
      fromX: laneX[1],
      toX: laneX[1],
      playerX: laneX[1],
      shield: false,
      shieldPulse: 0,
      entities: [],
      particles: [],
      spawnTimer: 0,
      elapsed: 0,
      score: 0,
      combo: 0,
      bestCombo: 0,
      shakeT: 0,
      shakeMag: 0,
      flashT: 0,
      flashColor: "255,77,94",
      bgScroll: 0,
    };
  }

  function getBest() {
    return parseInt(localStorage.getItem(STORAGE_BEST) || "0", 10);
  }
  function setBest(v) {
    localStorage.setItem(STORAGE_BEST, String(v));
  }
  bestEl.textContent = getBest();

  // ---------- Input ----------
  function moveLane(dir) {
    if (!state || !state.running) return;
    const next = state.lane + dir;
    if (next < 0 || next >= LANES) return;
    state.lane = next;
    state.targetLane = next;
    state.fromX = state.playerX;
    state.toX = laneX[next];
    state.laneAnimT = 0;
    sfx.switch();
  }

  window.addEventListener("keydown", (e) => {
    if (["ArrowLeft", "a", "A"].includes(e.key)) { moveLane(-1); e.preventDefault(); }
    else if (["ArrowRight", "d", "D"].includes(e.key)) { moveLane(1); e.preventDefault(); }
    else if (e.key === " " || e.key === "Enter") {
      e.preventDefault();
      if (!state || (!state.running && !overScreen.classList.contains("hidden"))) startGame();
      else if (!state || (!state.running && !startScreen.classList.contains("hidden"))) startGame();
    }
  });

  zoneLeft.addEventListener("pointerdown", () => moveLane(-1));
  zoneRight.addEventListener("pointerdown", () => moveLane(1));

  startBtn.addEventListener("click", startGame);
  retryBtn.addEventListener("click", startGame);

  // ---------- Spawning ----------
  function spawnWave() {
    const t = state.elapsed;
    const doubleChance = Math.min(0.35, t * 0.01);
    const gemChance = 0.55;

    if (Math.random() < doubleChance) {
      // blocked lanes: pick 2 adjacent-or-any lanes blocked, 1 safe lane guaranteed
      const safeLane = Math.floor(Math.random() * LANES);
      const lanes = [0, 1, 2].filter((l) => l !== safeLane);
      state.entities.push({ type: "obstacle", lanes, y: -OBSTACLE_H });
      if (Math.random() < 0.5) {
        state.entities.push({ type: "gem", lane: safeLane, y: -OBSTACLE_H - 60, big: Math.random() < 0.2 });
      }
    } else {
      const lane = Math.floor(Math.random() * LANES);
      if (Math.random() < gemChance) {
        state.entities.push({ type: "gem", lane, y: -GEM_R * 2, big: Math.random() < 0.15 });
        if (Math.random() < 0.25) {
          state.entities.push({ type: "shield", lane: (lane + 1 + Math.floor(Math.random() * 2)) % LANES, y: -GEM_R * 4 });
        }
      } else {
        state.entities.push({ type: "obstacle", lanes: [lane], y: -OBSTACLE_H });
      }
    }
  }

  // ---------- Particles ----------
  function burst(x, y, color, count, speed = 220, life = 0.5) {
    for (let i = 0; i < count; i++) {
      const a = Math.random() * Math.PI * 2;
      const s = speed * (0.4 + Math.random() * 0.6);
      state.particles.push({
        x, y,
        vx: Math.cos(a) * s,
        vy: Math.sin(a) * s,
        life,
        maxLife: life,
        color,
        size: 2 + Math.random() * 3,
      });
    }
  }

  // ---------- Game flow ----------
  function startGame() {
    ensureAudio();
    resize();
    state = freshState();
    state.running = true;
    state.playerX = laneX[1];
    startScreen.classList.add("hidden");
    overScreen.classList.add("hidden");
    comboWrap.style.opacity = 0;
    scoreEl.textContent = "0";
    lastTime = performance.now();
    requestAnimationFrame(loop);
  }

  function endGame() {
    state.running = false;
    state.over = true;
    sfx.hit();
    state.shakeT = 0.35;
    state.shakeMag = 18;
    state.flashT = 0.4;
    state.flashColor = "255,77,94";
    burst(state.playerX, playerY, "255,77,94", 40, 320, 0.7);

    const finalScore = Math.floor(state.score);
    const best = getBest();
    const isRecord = finalScore > best;
    if (isRecord) setBest(finalScore);

    setTimeout(() => {
      finalScoreEl.textContent = finalScore;
      overBestEl.textContent = isRecord ? finalScore : best;
      recordBanner.style.visibility = isRecord ? "visible" : "hidden";
      overTitle.textContent = "GAME OVER";
      bestEl.textContent = isRecord ? finalScore : best;
      overScreen.classList.remove("hidden");
      if (isRecord) sfx.record();
    }, 550);
  }

  // ---------- Update ----------
  let lastTime = 0;
  function loop(now) {
    let dt = (now - lastTime) / 1000;
    lastTime = now;
    if (dt > 0.05) dt = 0.05; // clamp for tab-switch etc.

    if (state) {
      if (state.running) update(dt);
      draw();
    }
    requestAnimationFrame(loop);
  }

  function currentFallSpeed() {
    return Math.min(MAX_FALL_SPEED, BASE_FALL_SPEED + state.elapsed * SPEED_RAMP);
  }
  function currentSpawnInterval() {
    return Math.max(MIN_SPAWN_INTERVAL, BASE_SPAWN_INTERVAL - state.elapsed * SPAWN_RAMP);
  }

  function update(dt) {
    state.elapsed += dt;
    state.bgScroll += currentFallSpeed() * dt;

    // lane glide
    if (state.laneAnimT < 1) {
      state.laneAnimT = Math.min(1, state.laneAnimT + dt / LANE_SWITCH_TIME);
      const e = 1 - Math.pow(1 - state.laneAnimT, 3);
      state.playerX = state.fromX + (state.toX - state.fromX) * e;
    } else {
      state.playerX = laneX[state.lane];
    }

    // score from survival
    state.score += dt * (10 + state.combo * 1.2);
    scoreEl.textContent = Math.floor(state.score);

    // spawn
    state.spawnTimer -= dt;
    if (state.spawnTimer <= 0) {
      spawnWave();
      state.spawnTimer = currentSpawnInterval();
    }

    // shield pulse
    if (state.shield) state.shieldPulse += dt * 6;

    // move entities & collisions
    const fallSpeed = currentFallSpeed();
    for (let i = state.entities.length - 1; i >= 0; i--) {
      const e = state.entities[i];
      e.y += fallSpeed * dt;

      const hitRow = e.y >= playerY - 20 && e.y <= playerY + 20;

      if (e.type === "obstacle") {
        if (hitRow && e.lanes.includes(state.lane) && !e._resolved) {
          e._resolved = true;
          if (state.shield) {
            state.shield = false;
            burst(state.playerX, playerY, "78,242,255", 26, 260, 0.5);
            sfx.switch();
          } else {
            endGame();
          }
        }
      } else if (e.type === "gem") {
        if (hitRow && e.lane === state.lane && !e._resolved) {
          e._resolved = true;
          state.combo += 1;
          state.bestCombo = Math.max(state.bestCombo, state.combo);
          const value = (e.big ? 60 : 20) * (1 + Math.min(state.combo, 20) * 0.08);
          state.score += value;
          burst(laneX[e.lane], playerY, e.big ? "255,213,74" : "78,242,255", e.big ? 22 : 12, 200, 0.45);
          sfx.collect(state.combo);
          comboWrap.style.opacity = 1;
          comboEl.textContent = "x" + state.combo;
        }
      } else if (e.type === "shield") {
        if (hitRow && e.lane === state.lane && !e._resolved) {
          e._resolved = true;
          state.shield = true;
          state.shieldPulse = 0;
          burst(laneX[e.lane], playerY, "78,242,255", 24, 220, 0.5);
          sfx.shield();
        }
      }

      if (e.y > H + 60) {
        if (e.type === "obstacle" && !e._resolved) {
          // survived an obstacle in a different lane -> keep/increase combo softly
        }
        if ((e.type === "gem" || e.type === "shield") && !e._resolved && state.combo > 0) {
          state.combo = 0;
          comboEl.textContent = "x0";
          comboWrap.style.opacity = 0.35;
        }
        state.entities.splice(i, 1);
      }
    }

    // particles
    for (let i = state.particles.length - 1; i >= 0; i--) {
      const p = state.particles[i];
      p.life -= dt;
      if (p.life <= 0) { state.particles.splice(i, 1); continue; }
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.vx *= 0.94;
      p.vy *= 0.94;
    }

    if (state.shakeT > 0) state.shakeT = Math.max(0, state.shakeT - dt);
    if (state.flashT > 0) state.flashT = Math.max(0, state.flashT - dt);
  }

  // ---------- Draw ----------
  function draw() {
    ctx.clearRect(0, 0, W, H);

    let ox = 0, oy = 0;
    if (state.shakeT > 0) {
      const m = state.shakeMag * (state.shakeT / 0.35);
      ox = (Math.random() * 2 - 1) * m;
      oy = (Math.random() * 2 - 1) * m;
    }
    ctx.save();
    ctx.translate(ox, oy);

    drawBackground();
    drawLanes();
    drawEntities();
    drawPlayer();
    drawParticles();

    ctx.restore();

    if (state.flashT > 0) {
      ctx.fillStyle = `rgba(${state.flashColor}, ${(state.flashT / 0.4) * 0.35})`;
      ctx.fillRect(0, 0, W, H);
    }
  }

  function drawBackground() {
    const grad = ctx.createLinearGradient(0, 0, 0, H);
    grad.addColorStop(0, "#0a0d1c");
    grad.addColorStop(1, "#06070f");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);

    ctx.strokeStyle = "rgba(78,242,255,0.08)";
    ctx.lineWidth = 1;
    const spacing = 46;
    const offset = state.bgScroll % spacing;
    for (let y = -spacing + offset; y < H; y += spacing) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(W, y);
      ctx.stroke();
    }
  }

  function drawLanes() {
    ctx.strokeStyle = "rgba(255,255,255,0.06)";
    ctx.lineWidth = 1;
    for (let i = 0; i < LANES - 1; i++) {
      const x = (laneX[i] + laneX[i + 1]) / 2;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, H);
      ctx.stroke();
    }
    ctx.fillStyle = "rgba(78,242,255,0.5)";
    ctx.fillRect(0, playerY + 22, W, 2);
  }

  function drawEntities() {
    for (const e of state.entities) {
      if (e.type === "obstacle") {
        ctx.fillStyle = "rgba(255,77,94,0.9)";
        ctx.shadowColor = "rgba(255,77,94,0.8)";
        ctx.shadowBlur = 18;
        for (const lane of e.lanes) {
          const x = laneX[lane];
          const w = (W / LANES) * 0.72;
          ctx.beginPath();
          ctx.moveTo(x, e.y - OBSTACLE_H / 2);
          ctx.lineTo(x - w / 2, e.y + OBSTACLE_H / 2);
          ctx.lineTo(x + w / 2, e.y + OBSTACLE_H / 2);
          ctx.closePath();
          ctx.fill();
        }
        ctx.shadowBlur = 0;
      } else if (e.type === "gem") {
        const r = e.big ? GEM_R * 1.6 : GEM_R;
        const color = e.big ? "255,213,74" : "78,242,255";
        ctx.fillStyle = `rgba(${color},0.95)`;
        ctx.shadowColor = `rgba(${color},0.9)`;
        ctx.shadowBlur = e.big ? 22 : 14;
        ctx.beginPath();
        ctx.arc(laneX[e.lane], e.y, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
      } else if (e.type === "shield") {
        ctx.strokeStyle = "rgba(78,242,255,0.9)";
        ctx.lineWidth = 3;
        ctx.shadowColor = "rgba(78,242,255,0.8)";
        ctx.shadowBlur = 16;
        ctx.beginPath();
        ctx.arc(laneX[e.lane], e.y, GEM_R + 4, 0, Math.PI * 2);
        ctx.stroke();
        ctx.shadowBlur = 0;
      }
    }
  }

  function drawPlayer() {
    if (state.shield) {
      const pulse = 4 * Math.sin(state.shieldPulse);
      ctx.strokeStyle = "rgba(78,242,255,0.8)";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(state.playerX, playerY, PLAYER_R + 10 + pulse, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.fillStyle = "#eaf6ff";
    ctx.shadowColor = "rgba(78,242,255,0.9)";
    ctx.shadowBlur = 22;
    ctx.beginPath();
    ctx.arc(state.playerX, playerY, PLAYER_R, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;
  }

  function drawParticles() {
    for (const p of state.particles) {
      const a = Math.max(0, p.life / p.maxLife);
      ctx.fillStyle = `rgba(${p.color},${a})`;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size * a, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  // ---------- Init ----------
  resize();
  state = freshState();
  draw();
})();
