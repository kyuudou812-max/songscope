(function () {
  "use strict";

  var STORAGE_KEY = "sga_state_v1";

  var BODY_POOL = ["体重を記録する", "今日の1食を記録する", "10分歩く"];
  var ENGLISH_POOL = ["テキストを開く", "単語を5個復習する", "文法問題を1問解く", "リスニングを3分聞く"];
  var BODY_RECOVERY_ITEM = "体重だけ記録する";
  var ENGLISH_RECOVERY_ITEM = "前回の教材を5分だけ開く";
  var REASON_OPTIONS = ["忙しかった", "体調・気分", "記録を忘れた", "その他"];

  function todayStr() {
    var d = new Date();
    var m = String(d.getMonth() + 1).padStart(2, "0");
    var day = String(d.getDate()).padStart(2, "0");
    return d.getFullYear() + "-" + m + "-" + day;
  }

  function daysBetween(dateStrA, dateStrB) {
    var a = new Date(dateStrA + "T00:00:00");
    var b = new Date(dateStrB + "T00:00:00");
    return Math.round((b - a) / 86400000);
  }

  function defaultState() {
    return {
      schemaVersion: 1,
      body: { weights: [], actions: [] },
      english: { events: [] },
      growth: { ideas: [], projects: [] },
      log: []
    };
  }

  function loadState() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return defaultState();
      var parsed = JSON.parse(raw);
      var base = defaultState();
      return Object.assign(base, parsed, {
        body: Object.assign(base.body, parsed.body),
        english: Object.assign(base.english, parsed.english),
        growth: Object.assign(base.growth, parsed.growth)
      });
    } catch (e) {
      return defaultState();
    }
  }

  function saveState() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  var state = loadState();

  function uid() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
  }

  // ---- area helpers -------------------------------------------------

  function lastEventDate(area) {
    var dates = [];
    if (area === "body") {
      state.body.weights.forEach(function (w) { dates.push(w.date); });
      state.body.actions.forEach(function (a) { dates.push(a.date); });
    } else if (area === "english") {
      state.english.events.forEach(function (e) { dates.push(e.date); });
    } else if (area === "growth") {
      state.growth.projects.forEach(function (p) {
        if (p.lastStepDate) dates.push(p.lastStepDate);
      });
    }
    if (dates.length === 0) return null;
    dates.sort();
    return dates[dates.length - 1];
  }

  function daysSinceLast(area) {
    var last = lastEventDate(area);
    if (!last) return Infinity;
    return daysBetween(last, todayStr());
  }

  function isDoneToday(area) {
    return daysSinceLast(area) === 0;
  }

  // Recovery only applies once an area has a history and then goes quiet for
  // 7+ days. A never-started area is "not started yet", not "recovering".
  function isInRecovery(area) {
    var days = daysSinceLast(area);
    return Number.isFinite(days) && days >= 7;
  }

  function pickPoolItem(pool, areaKey) {
    var seed = todayStr() + areaKey;
    var hash = 0;
    for (var i = 0; i < seed.length; i++) {
      hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
    }
    return pool[hash % pool.length];
  }

  function reasonLoggedToday(area) {
    var t = todayStr();
    return state.log.some(function (l) {
      return l.type === "reason" && l.area === area && l.date === t;
    });
  }

  function logReason(area, text) {
    state.log.push({ id: uid(), date: todayStr(), ts: Date.now(), type: "reason", area: area, text: text });
    saveState();
    render();
  }

  // ---- NEXT ACTION ----------------------------------------------------

  function computeNextActions() {
    var actions = [];

    if (!isDoneToday("body")) {
      if (isInRecovery("body")) {
        actions.push({ area: "body", text: BODY_RECOVERY_ITEM, recovery: true });
      } else {
        actions.push({ area: "body", text: pickPoolItem(BODY_POOL, "body"), recovery: false });
      }
    }

    if (!isDoneToday("english")) {
      if (isInRecovery("english")) {
        actions.push({ area: "english", text: ENGLISH_RECOVERY_ITEM, recovery: true });
      } else {
        actions.push({ area: "english", text: pickPoolItem(ENGLISH_POOL, "english"), recovery: false });
      }
    }

    var activeProject = state.growth.projects.find(function (p) { return p.status === "active"; });
    if (activeProject && !isDoneToday("growth")) {
      var text = activeProject.nextStep
        ? "「" + activeProject.name + "」: " + activeProject.nextStep
        : "「" + activeProject.name + "」の次の一歩を決めて進める";
      actions.push({ area: "growth", text: text, recovery: false });
    }

    return actions;
  }

  // ---- rendering --------------------------------------------------------

  var AREA_LABEL = { body: "BODY", english: "ENGLISH", growth: "GROWTH" };

  function render() {
    renderHome();
    renderBody();
    renderEnglish();
    renderGrowth();
  }

  function renderHome() {
    var wrap = document.getElementById("next-actions");
    var actions = computeNextActions();
    wrap.innerHTML = "";
    if (actions.length === 0) {
      var empty = document.createElement("p");
      empty.className = "empty-state";
      empty.textContent = "今日のMain Goal行動は完了しています。";
      wrap.appendChild(empty);
    } else {
      actions.forEach(function (a) {
        var card = document.createElement("div");
        card.className = "next-action-card" + (a.recovery ? " is-recovery" : "");
        var textWrap = document.createElement("div");
        var label = document.createElement("span");
        label.className = "label";
        label.textContent = a.text;
        var tag = document.createElement("span");
        tag.className = "tag";
        tag.textContent = a.recovery ? "Recovery · " + AREA_LABEL[a.area] : AREA_LABEL[a.area];
        textWrap.appendChild(label);
        textWrap.appendChild(tag);
        var btn = document.createElement("button");
        btn.textContent = "開く";
        btn.addEventListener("click", function () { switchTab(a.area); });
        card.appendChild(textWrap);
        card.appendChild(btn);
        wrap.appendChild(card);
      });
    }

    renderTodayRow("today-body", "body", "BODY");
    renderTodayRow("today-english", "english", "ENGLISH");
    renderTodayRow("today-growth", "growth", "GROWTH");
  }

  function renderTodayRow(elId, areaKey, areaLabel) {
    var row = document.getElementById(elId);
    row.innerHTML = "";

    var labelEl = document.createElement("span");
    labelEl.className = "area-label";
    labelEl.textContent = areaLabel;
    row.appendChild(labelEl);

    var days = daysSinceLast(areaKey);
    var statusEl = document.createElement("span");
    if (days === 0) {
      statusEl.className = "status is-done";
      statusEl.textContent = "○ 実施済み";
    } else if (!Number.isFinite(days)) {
      statusEl.className = "status";
      statusEl.textContent = "まだ記録がありません";
    } else if (days >= 7) {
      statusEl.className = "status is-recovery";
      statusEl.textContent = "Recovery（" + days + "日）";
    } else {
      statusEl.className = "status";
      statusEl.textContent = "－ " + days + "日未実施";
    }
    row.appendChild(statusEl);

    if (Number.isFinite(days) && days >= 3 && days < 7 && !reasonLoggedToday(areaKey)) {
      var picker = document.createElement("div");
      picker.className = "reason-picker";
      REASON_OPTIONS.forEach(function (opt) {
        var b = document.createElement("button");
        b.type = "button";
        b.textContent = opt;
        b.addEventListener("click", function () { logReason(areaKey, opt); });
        picker.appendChild(b);
      });
      row.appendChild(picker);
    }
  }

  function renderBody() {
    var weights = state.body.weights.slice().sort(function (a, b) { return a.date < b.date ? 1 : -1; });
    var trendEl = document.getElementById("body-trend");
    if (weights.length < 2) {
      trendEl.textContent = "記録が少ないため傾向はまだ表示できません。";
    } else {
      var latest = weights[0];
      var cutoff = todayStr();
      var sevenDaysAgo = new Date();
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
      var recent = weights.filter(function (w) { return new Date(w.date) >= sevenDaysAgo; });
      var avg = recent.reduce(function (s, w) { return s + w.kg; }, 0) / recent.length;
      trendEl.textContent = "直近7日平均: " + avg.toFixed(1) + "kg（最新記録: " + latest.kg + "kg, " + latest.date + "）";
    }

    var historyEl = document.getElementById("body-history");
    historyEl.innerHTML = "";
    var entries = weights.slice(0, 5).map(function (w) {
      return { date: w.date, text: w.kg + "kg" };
    }).concat(
      state.body.actions.slice().sort(function (a, b) { return a.date < b.date ? 1 : -1; }).slice(0, 5).map(function (a) {
        return { date: a.date, text: "行動: " + (a.note || "（記録のみ）") };
      })
    ).sort(function (a, b) { return a.date < b.date ? 1 : -1; }).slice(0, 8);

    entries.forEach(function (e) {
      var li = document.createElement("li");
      var span = document.createElement("span");
      span.textContent = e.text;
      var meta = document.createElement("span");
      meta.className = "meta";
      meta.textContent = e.date;
      li.appendChild(span);
      li.appendChild(meta);
      historyEl.appendChild(li);
    });
  }

  function renderEnglish() {
    var historyEl = document.getElementById("english-history");
    historyEl.innerHTML = "";
    var LAYER_LABEL = { input: "学習時間", process: "問題数", output: "模試スコア", outcome: "本番スコア" };
    var events = state.english.events.slice().sort(function (a, b) { return b.ts - a.ts; }).slice(0, 10);
    events.forEach(function (e) {
      var li = document.createElement("li");
      var span = document.createElement("span");
      span.textContent = LAYER_LABEL[e.layer] + ": " + e.value;
      var meta = document.createElement("span");
      meta.className = "meta";
      meta.textContent = e.date;
      li.appendChild(span);
      li.appendChild(meta);
      historyEl.appendChild(li);
    });
  }

  function renderGrowth() {
    var activeWrap = document.getElementById("growth-active");
    activeWrap.innerHTML = "";
    var activeProject = state.growth.projects.find(function (p) { return p.status === "active"; });

    if (!activeProject) {
      var empty = document.createElement("p");
      empty.className = "empty-state";
      empty.textContent = "Active Projectはありません。Ideaから選ぶか、下の一覧から追加してください。";
      activeWrap.appendChild(empty);
    } else {
      var card = document.createElement("div");
      card.className = "project-card";

      var h4 = document.createElement("h4");
      h4.textContent = activeProject.name;
      card.appendChild(h4);

      var input = document.createElement("input");
      input.type = "text";
      input.placeholder = "次の一歩";
      input.value = activeProject.nextStep || "";
      input.addEventListener("change", function () {
        activeProject.nextStep = input.value;
        saveState();
      });
      card.appendChild(input);

      var actionsWrap = document.createElement("div");
      actionsWrap.className = "project-actions";

      var progressBtn = document.createElement("button");
      progressBtn.textContent = "今日進めた";
      progressBtn.addEventListener("click", function () {
        activeProject.lastStepDate = todayStr();
        saveState();
        render();
      });
      actionsWrap.appendChild(progressBtn);

      [["done", "Finish"], ["waiting", "Pause"], ["dropped", "Drop"]].forEach(function (pair) {
        var b = document.createElement("button");
        b.className = "secondary";
        b.textContent = pair[1];
        b.addEventListener("click", function () {
          activeProject.status = pair[0];
          saveState();
          render();
        });
        actionsWrap.appendChild(b);
      });

      card.appendChild(actionsWrap);
      activeWrap.appendChild(card);
    }

    var ideaList = document.getElementById("idea-list");
    ideaList.innerHTML = "";
    state.growth.ideas.slice().sort(function (a, b) { return b.createdAt - a.createdAt; }).forEach(function (idea) {
      var li = document.createElement("li");
      var span = document.createElement("span");
      span.textContent = idea.text;
      li.appendChild(span);

      if (!activeProject) {
        var promoteBtn = document.createElement("button");
        promoteBtn.className = "idea-promote";
        promoteBtn.textContent = "Activeにする";
        promoteBtn.addEventListener("click", function () {
          promoteIdea(idea.id);
        });
        li.appendChild(promoteBtn);
      } else {
        var meta = document.createElement("span");
        meta.className = "meta";
        meta.textContent = "待機中";
        li.appendChild(meta);
      }
      ideaList.appendChild(li);
    });
  }

  function promoteIdea(ideaId) {
    var activeProject = state.growth.projects.find(function (p) { return p.status === "active"; });
    if (activeProject) {
      alert("Growth Activeは1件までです。先に現在のプロジェクトをFinish/Pause/Dropしてください。");
      return;
    }
    var idea = state.growth.ideas.find(function (i) { return i.id === ideaId; });
    if (!idea) return;
    state.growth.projects.push({
      id: uid(),
      name: idea.text,
      status: "active",
      createdAt: Date.now(),
      lastStepDate: null,
      nextStep: ""
    });
    state.growth.ideas = state.growth.ideas.filter(function (i) { return i.id !== ideaId; });
    saveState();
    render();
  }

  // ---- tabs ---------------------------------------------------------

  function switchTab(name) {
    document.querySelectorAll(".panel").forEach(function (p) {
      p.hidden = p.getAttribute("data-panel") !== name;
    });
    document.querySelectorAll(".tab-btn").forEach(function (b) {
      b.classList.toggle("is-active", b.getAttribute("data-tab") === name);
    });
  }

  document.querySelectorAll(".tab-btn").forEach(function (b) {
    b.addEventListener("click", function () { switchTab(b.getAttribute("data-tab")); });
  });

  // ---- forms ---------------------------------------------------------

  document.getElementById("form-weight").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var input = document.getElementById("input-weight");
    var kg = parseFloat(input.value);
    if (isNaN(kg)) return;
    state.body.weights.push({ date: todayStr(), ts: Date.now(), kg: kg });
    input.value = "";
    saveState();
    render();
  });

  document.getElementById("btn-body-action").addEventListener("click", function () {
    var noteInput = document.getElementById("input-body-note");
    state.body.actions.push({ date: todayStr(), ts: Date.now(), note: noteInput.value.trim() });
    noteInput.value = "";
    saveState();
    render();
  });

  function bindEnglishForm(formId, layer) {
    document.getElementById(formId).addEventListener("submit", function (ev) {
      ev.preventDefault();
      var input = ev.target.querySelector("input");
      var value = parseFloat(input.value);
      if (isNaN(value)) return;
      state.english.events.push({ date: todayStr(), ts: Date.now(), layer: layer, value: value });
      input.value = "";
      saveState();
      render();
    });
  }
  bindEnglishForm("form-english-input", "input");
  bindEnglishForm("form-english-process", "process");
  bindEnglishForm("form-english-output", "output");
  bindEnglishForm("form-english-outcome", "outcome");

  document.getElementById("form-idea").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var input = document.getElementById("input-idea");
    var text = input.value.trim();
    if (!text) return;
    state.growth.ideas.push({ id: uid(), text: text, createdAt: Date.now() });
    input.value = "";
    saveState();
    render();
  });

  render();
})();
