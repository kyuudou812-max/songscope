"""効果音を、本物の録音から作り直す（合成の効果音は「下手」だったため。README「わかったこと」）。

私は耳で聞けないので、録音を測って候補を絞り、主な音は A・B・C の3通りを作る。どれを使うかは KP が聞いて選ぶ。
加工だけをこちらで行う：切り詰め・音量・こもらせる（ドア越し・遠く）・響き・左右の位置・重ね・ループのつなぎ目。

素材（build/sfxlib/ に置く。git の対象外）
  kenney_impact/  Kenney「Impact Sounds」（CC0）       git clone https://github.com/Boyquotes/kenney-impact-sounds-for-godot
  kenney_rpg/     Kenney「RPG Audio」（CC0）           git clone https://github.com/Boyquotes/kenney-rpg-audio-for-godot
  kenney_more/    Kenney の音素材のまとめ（CC0）        git clone https://github.com/ismetcabbar9-oss/kenney-audio-assets の「Audio (295 files)」
  esc50/          ESC-50（Freesound の録音。CC BY-NC。非営利で、出典の表記が要る）  git clone https://github.com/karolpiczak/ESC-50
  audioaugust/   Inexor「AudioAugust」（CC BY 4.0。鉄のドア）  git clone --sparse https://github.com/inexorgame/audioaugust（doors impacts noise "step sounds"）
  lavender_cc0/  CC0 の音素材のまとめ（紙・食器・鉄のドア・換気口）  git clone --sparse https://github.com/lavenderdotpet/CC0-Public-Domain-Sounds
                 （100-CC0-wood-metal-SFX 100-CC0-SFX "bb - Books, Paper, Writing (Jan 2021)" "BB_Retail Therapy Sample Pack" "bb - Fans and Drones (Jul 2021)"）
  stk_assets/    SuperTuxKart の素材（レストランの録音 lenautile_restaurant.ogg、CC0）  git clone --sparse https://github.com/Pttn/stk-assets（sfx）
  候補ぜんぶの出典は build/ccfolia/fx_real/CREDITS.txt、本番（PICKS で選ばれたもの）の出典は SFX-CREDITS.txt に書き出す

出力: build/ccfolia/fx_real/<元のファイル名>_A/B/C.mp3（候補。作り直しは _v2_A/B/C）と CREDITS.txt。
      PICKS の候補は build/ccfolia/fx/<元のファイル名>.mp3 に上書きして本番にする

使い方: python3 tools/make_sfx_real.py
"""
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fxlib import ROOT, SR, env, filt, loop_seam, noise, norm, place, reverb, sec, silence, smooth_random, write_mp3  # noqa: E402

LIB = ROOT / "build" / "sfxlib"
OUT = ROOT / "build" / "ccfolia" / "fx_real"
RPG = LIB / "kenney_rpg" / "addons" / "kenney rpg audio"
IMP = LIB / "kenney_impact" / "addons" / "kenney impact sounds"
CASINO = LIB / "kenney_more" / "Casino sounds (50 sounds)"
JINGLE = LIB / "kenney_more" / "Jingle sounds (85 sounds)"
ESC = LIB / "esc50" / "audio"
AUG = LIB / "audioaugust"                      # Inexor「AudioAugust」（CC BY 4.0）  git clone https://github.com/inexorgame/audioaugust
LAV = LIB / "lavender_cc0"                     # CC0 の音素材のまとめ  git clone https://github.com/lavenderdotpet/CC0-Public-Domain-Sounds
STK = LIB / "stk_assets" / "sfx"               # SuperTuxKart の素材（ファミレスの録音は CC0）  git clone https://github.com/Pttn/stk-assets
USED_ESC = set()
CUR = set()                                    # いま作っている音に使った録音（書き出すたびに SOURCES に写す）
SOURCES = {}


def begin():
    """ここから別の音を作る（使った録音の記録をまっさらに）"""
    CUR.clear()


def record(path):
    SOURCES[Path(path).resolve()] = set(CUR)


# ---------------------------------------------------------------- 読み込みと加工
def load(path):
    """どの形式でも 48kHz モノラルの配列に"""
    path = Path(path)
    if path.parent == ESC:
        USED_ESC.add(path.name)
    CUR.add(path.absolute())
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def esc(name):
    return load(ESC / name)


def trim(x, thr_db=-50):
    """頭と終わりの無音を切る"""
    a = np.abs(x)
    m = a.max() if a.size else 0
    idx = np.where(a > m * 10 ** (thr_db / 20))[0]
    return x[idx[0]:idx[-1] + 1] if len(idx) else x


def speed(x, f):
    """速さを f 倍に（音の高さも変わる。f<1 で低く重く）"""
    n = int(len(x) / f)
    return np.interp(np.arange(n) * f, np.arange(len(x)), x).astype(np.float32)


def events(x, min_gap=0.15, thr=0.25):
    """録音の中の一つひとつの音（足音など）を切り出す"""
    w = sec(0.01)
    e = np.convolve(np.abs(x), np.ones(w) / w, "same")
    on = np.where((e[1:] > thr * e.max()) & (e[:-1] <= thr * e.max()))[0]
    keep, last = [], -10 ** 9
    for o in on:
        if o - last > sec(min_gap):
            keep.append(o)
            last = o
    out = []
    for i, s in enumerate(keep):
        a = max(0, s - sec(0.01))
        b = min(len(x), keep[i + 1] - sec(0.01) if i + 1 < len(keep) else s + sec(0.4))
        seg = x[a:b] * env(b - a, 0.002, 0.25)
        out.append(seg.astype(np.float32))
    return out


def behind_door(x, hi=2400):
    """ドア越し：高い音が板で削られ、板の低い鳴りが少し乗る"""
    return filt(x, hi=hi, order=2) * 0.85 + filt(x, 140, 320) * 0.3


def distance(x, k):
    """k 部屋むこう（0＝すぐ外）。遠いほど小さく、こもり、外廊下に響く"""
    hi = [5000, 2600, 1600, 1100, 800][k]
    g = [1.0, 0.55, 0.32, 0.18, 0.1][k]
    wet = [0.12, 0.3, 0.45, 0.6, 0.7][k]
    return reverb(filt(x, hi=hi), 0.9, wet, 3000) * g


def pan(x, p):
    a = (np.asarray(p, np.float32) + 1) * np.pi / 4
    return (x * np.cos(a)).astype(np.float32), (x * np.sin(a)).astype(np.float32)


def stereo(path, l, r, peak=0.8, q=3):
    n = max(len(l), len(r))
    l, r = np.pad(l, (0, n - len(l))), np.pad(r, (0, n - len(r)))
    m = max(np.abs(l).max(), np.abs(r).max(), 1e-6)
    write_mp3(path, l / m * peak, q=q, stereo=r / m * peak)
    record(path)


def mono(path, x, peak=0.8, q=3, steady=False):
    """steady=True は環境音：まれな大きな音ではなく、ふだんの大きさ（99.9%）で音量を決める"""
    if steady:
        x = np.clip(x / max(np.percentile(np.abs(x), 99.9), 1e-6) * peak, -0.95, 0.95)
        write_mp3(path, x.astype(np.float32), q=q)
    else:
        write_mp3(path, norm(x, peak), q=q)
    record(path)


def ambience(clips, L=62, xf=1.5, seed=0):
    """5秒ほどの録音を何本も、ばらばらの順でつなぎ（重ねて継ぎ目を消す）、長いループにする"""
    rg = np.random.default_rng(seed)
    parts = [trim(c) for c in clips]
    parts = [p / max(np.sqrt(np.mean(p ** 2)), 1e-6) for p in parts if len(p) > sec(2)]
    out = np.zeros(sec(L + 6), np.float32)
    t, n_x = 0, sec(xf)
    while t < len(out) - sec(1):
        p = parts[rg.integers(len(parts))]
        if rg.random() < 0.5:
            p = p[::-1]                                              # 逆向きにしても、雨や風は自然に聞こえる
        p = p.copy()
        p[:n_x] *= np.linspace(0, 1, n_x)
        p[-n_x:] *= np.linspace(1, 0, n_x)
        e = min(len(out), t + len(p))
        out[t:e] += p[: e - t]
        t += len(p) - n_x
    return loop_seam(out[: sec(L + 2)], 2.0)


def scatter(clips, L, gap, gain, seed, cut=None):
    """短い音を L 秒にまばらに散らし（間隔は gap=(最短, 最長) 秒）、つなぎ目のないループにする"""
    rg = np.random.default_rng(seed)
    x = np.zeros(sec(L + 2), np.float32)
    t = rg.uniform(0, gap[0])
    while t < L + 1:
        c = clips[rg.integers(len(clips))]
        if cut and len(c) > sec(cut):
            c = c[: sec(rg.uniform(cut * 0.5, cut))]
            c = c * env(len(c), 0.005, 0.3)
        place(x, c * rg.uniform(gain[0], gain[1]), t)
        t += rg.uniform(*gap)
    return loop_seam(x, 2.0)


def bed(path, x, peak=0.6, ceil=0.8, q=4):
    """環境音の書き出し：ふだんの大きさ（99.9%）で音量を決め、まれな大きな音はやわらかく ceil 以下に抑える（mp3 にしても 0.85 を超えない）"""
    x = x / max(np.percentile(np.abs(x), 99.9), 1e-6) * peak
    a = np.abs(x)
    k = peak * 0.9
    x = np.where(a > k, np.sign(x) * (k + (ceil - k) * np.tanh((a - k) / (ceil - k))), x)
    write_mp3(path, x.astype(np.float32), q=q)
    record(path)


def mix(*layers):
    """長さをそろえて足す"""
    n = min(len(a) for a in layers)
    return sum(a[:n] for a in layers).astype(np.float32)


def tv(x):
    """テレビの小さなスピーカー：低音と高音が削れ、少し歪む"""
    return np.tanh(filt(x, 350, 4500, order=3) * 1.6) / 1.6


# ---------------------------------------------------------------- 第一話
def ep1():
    d = OUT / "ep1"
    begin()
    # 足音：右から近づき、ドアの前（正面）でぴたりと止まる。硬い靴と床、ドア越し
    sets = {
        "A": [load(IMP / f"footstep_concrete_{i:03d}.ogg") for i in range(5)],
        "B": events(esc("5-51149-A-25.wav")),
        "C": events(esc("1-51147-A-25.wav")),
    }
    for v, steps in sets.items():
        steps = [trim(s) for s in steps if len(s) > sec(0.03)]
        n, rate = 14, 1.75
        x = np.zeros(sec(n / rate + 3), np.float32)
        rg = np.random.default_rng(1)
        for i in range(n):
            k = i / (n - 1)
            s = steps[i % len(steps)] * (0.12 + 0.88 * k ** 1.5) * rg.uniform(0.9, 1.05)
            s = filt(s, hi=1800 + 5000 * k)
            place(x, s, 0.3 + i / rate + rg.normal(0, 0.01))
        wet = reverb(x, 1.3, 1.0, 4000) - x
        kk = np.clip(np.arange(len(x)) / SR / (n / rate), 0, 1)
        x = behind_door(x + wet * (0.9 - 0.6 * kk), hi=4500)
        stereo(d / f"11_footsteps_stop_{v}.mp3", *pan(x, np.clip(np.linspace(0.85, -0.2, len(x)), 0, 1)), peak=0.6)

    begin()
    # ガチャ、ぎい、バタン：ノブ → きしみながら開く → 閉まる（会議室の中で鳴る）
    combos = {"A": ("door_open_1", "creak_1", "door_close_1"), "B": ("door_open_2", "creak_2", "door_close_3"),
              "C": ("door_open_1", "creak_3", "door_close_4")}
    for v, (op, cr, cl) in combos.items():
        x = np.zeros(sec(5), np.float32)
        place(x, trim(load(RPG / "metal_latch.ogg")) * 0.7, 0.2)
        place(x, trim(load(RPG / f"{op}.ogg")), 0.45)
        place(x, speed(trim(load(RPG / f"{cr}.ogg")), 0.85) * 0.8, 0.7)
        place(x, trim(load(RPG / f"{cl}.ogg")), 2.6)
        mono(d / f"12_door_open_close_{v}.mp3", reverb(x, 0.6, 0.25))

    begin()
    # 引っ掻く・擦り付ける：ドアの向こうで何人もが。左右に散らばる。ループ
    srcs = {
        "A": [speed(trim(load(CASINO / f"cardSlide{i}.ogg")), 0.7) for i in range(1, 9)],
        "B": [trim(esc(f)) for f in ("1-68628-A-27.wav", "5-220939-A-27.wav", "1-17092-B-27.wav")],
        "C": [speed(trim(load(CASINO / f"cardSlide{i}.ogg")), 0.55) for i in range(1, 9)]
             + [trim(esc(f)) for f in ("2-135860-A-49.wav", "1-9887-B-49.wav")],
    }
    for v, clips in srcs.items():
        L = 62
        chans = []
        for side in (0, 1):
            x = np.zeros(sec(L + 3), np.float32)
            rg = np.random.default_rng(10 + side)
            t = rg.uniform(0, 1)
            while t < L:
                c = clips[rg.integers(len(clips))]
                c = c[: sec(rg.uniform(0.3, 1.2))] if len(c) > sec(0.4) else c
                c = c * env(len(c), 0.01, 0.4)
                place(x, c * rg.uniform(0.3, 1.0), t)
                t += rg.uniform(0.2, 1.6)
            chans.append(behind_door(loop_seam(x, 2.0), hi=2600))
        l, r = chans
        n = min(len(l), len(r))
        stereo(d / f"13_scratching_loop_{v}.mp3", l[:n] * 0.8 + r[:n] * 0.2, r[:n] * 0.8 + l[:n] * 0.2, peak=0.55)

    begin()
    # ガチャン×3：ノブを強く回す → 手が滑って戻る。ドアが枠の中で揺れる
    knobs = {"A": ("metal_latch", "door_close_2"), "B": ("metal_click", "door_close_3"), "C": ("metal_latch", "door_close_4")}
    knock = trim(esc("1-81001-B-30.wav"))
    for v, (lt, cl) in knobs.items():
        x = np.zeros(sec(7), np.float32)
        for i, t0 in enumerate((0.3, 2.2, 4.0)):
            place(x, trim(load(RPG / f"{lt}.ogg")) * 1.0, t0)
            place(x, filt(trim(load(RPG / f"{cl}.ogg")), hi=2500) * 0.35, t0 + 0.02)
            place(x, filt(knock[: sec(0.15)], hi=1500) * 0.3, t0 + 0.03)
            place(x, speed(trim(load(RPG / f"{lt}.ogg")), 0.9) * 0.45, t0 + 0.7)
        mono(d / f"14_handle_rattle_{v}.mp3", reverb(x, 0.6, 0.25))


# ---------------------------------------------------------------- 第四話
def ep4():
    d = OUT / "ep4"
    begin()
    # グシャ：重く湿ったものが背後に落ちる
    combos = {"A": ("impact_soft_heavy_000", "impact_punch_heavy_002"), "B": ("impact_soft_heavy_003", "impact_wood_heavy_001"),
              "C": ("impact_punch_heavy_004", "impact_soft_medium_001")}
    for v, (a, b) in combos.items():
        x = np.zeros(sec(2.5), np.float32)
        place(x, speed(trim(load(IMP / f"{a}.ogg")), 0.8), 0.05)
        place(x, speed(trim(load(IMP / f"{b}.ogg")), 0.7) * 0.6, 0.06)
        place(x, filt(trim(esc("1-84536-A-39.wav"))[: sec(0.3)], 300, 2500) * 0.12, 0.07)   # 細かく潰れる音を、ごく薄く
        mono(d / f"44_gusha_{v}.mp3", reverb(filt(x, hi=6000), 0.9, 0.3), peak=0.85)
    begin()
    # シートをかき分けて走る：布とビニールのこすれ、遠くの大通り
    for v, seed in (("A", 1), ("B", 2), ("C", 3)):
        L = 62
        x = np.zeros(sec(L + 3), np.float32)
        rg = np.random.default_rng(seed)
        clips = [trim(load(RPG / f"cloth_{i}.ogg")) for i in range(1, 5)] + [trim(load(CASINO / f"cardShove{i}.ogg")) for i in range(1, 5)]
        t = 0.0
        while t < L:
            for _ in range(int(rg.integers(2, 4))):
                place(x, speed(clips[rg.integers(len(clips))], rg.uniform(0.6, 0.9)) * rg.uniform(0.5, 1.0), t + rg.uniform(0, 0.4))
            t += 1.4 * rg.uniform(0.85, 1.15)
        steps = [trim(load(IMP / f"footstep_concrete_{i:03d}.ogg")) for i in range(5)]
        for k, t0 in enumerate(np.arange(0.1, L, 0.33)):
            place(x, steps[k % 5] * 0.35, t0)
        mono(d / f"42_tarp_run_loop_{v}.mp3", loop_seam(x, 2.0), peak=0.6)


# ---------------------------------------------------------------- 第五話
def steel_door(seed, close=True, heavy="impact_metal_heavy_000"):
    x = np.zeros(sec(1.6), np.float32)
    place(x, trim(load(RPG / "metal_latch.ogg")) * 0.8, 0.0)
    if close:
        place(x, speed(trim(load(IMP / f"{heavy}.ogg")), 0.75), 0.55)
    return x


def ep5():
    begin()
    d = OUT / "ep5"
    for v, heavy in (("A", "impact_metal_heavy_000"), ("B", "impact_plate_heavy_002"), ("C", "impact_metal_heavy_003")):
        # 一部屋ずつ近づく（左の遠くから正面へ）。「ただいまー」の間は無音で空け、KP がチャットで送る
        x = np.zeros(sec(24), np.float32)
        t = 0.5
        for k in (4, 3, 2, 1):
            t += 2.34
            if k > 1:
                place(x, distance(steel_door(0, True, heavy), k), t)
                t += 1.6
                place(x, distance(steel_door(1, False, heavy), k - 1), t)
                t += 0.7
        x = x[: sec(t + 1.0)]
        stereo(d / f"51_tadaima_approach_{v}.mp3", *pan(x, np.linspace(-0.85, -0.15, len(x))), peak=0.8)
        # この部屋に帰ってきた：ドアが開く → ぎし → 沈黙 → 出ていく
        y = np.zeros(sec(11), np.float32)
        place(y, filt(trim(load(RPG / "door_open_2.ogg")), hi=3000) * 0.8, 0.3)
        place(y, speed(trim(load(RPG / "creak_2.ogg")), 0.7) * 0.5, 2.4)
        place(y, filt(steel_door(2, True, heavy), hi=2500) * 0.6, 6.4)
        mono(d / f"52_tadaima_arrive_{v}.mp3", reverb(y, 0.5, 0.2), peak=0.75)
    begin()
    # 窓に紙が叩きつけられる「バン！」とばたつき
    for v, (a, b) in (("A", ("book_close", "book_flip_1")), ("B", ("book_place_2", "book_flip_2")), ("C", ("book_close", "book_flip_3"))):
        x = np.zeros(sec(2.0), np.float32)
        place(x, trim(load(RPG / f"{a}.ogg")), 0.05)
        place(x, trim(load(IMP / "impact_glass_light_001.ogg")) * 0.35, 0.06)
        for k in range(3):
            place(x, trim(load(RPG / f"{b}.ogg")) * (0.5 - k * 0.12), 0.35 + k * 0.22)
        mono(d / f"57_window_slap_{v}.mp3", reverb(x, 0.5, 0.2))


# ---------------------------------------------------------------- 第八話
def ep8():
    begin()
    d = OUT / "ep8"
    winds = [esc(f) for f in ("3-134699-B-16.wav", "3-134699-A-16.wav", "3-246513-B-16.wav", "3-246513-A-16.wav",
                              "4-163608-B-16.wav", "4-163609-B-16.wav", "3-134699-C-16.wav")]
    for v, (bang, seed) in (("A", ("impact_wood_heavy_002", 1)), ("B", ("impact_plank_medium_001", 2)), ("C", ("impact_wood_heavy_004", 3))):
        L = 360
        wind = ambience(winds, L, 1.5, seed)
        gust = smooth_random(len(wind) / SR, 0.35, seed + 5)[: len(wind)] ** 1.5
        cloth = np.zeros(len(wind), np.float32)
        clips = [trim(load(RPG / f"cloth_{i}.ogg")) for i in range(1, 5)]
        rg = np.random.default_rng(seed)
        t = 0.5
        while t < L - 1:
            place(cloth, clips[rg.integers(4)] * rg.uniform(0.3, 0.9), t)
            t += rg.uniform(0.08, 0.5)
        cloth *= np.clip(gust * 1.5, 0, 1)
        x = norm(wind) * 0.5 + norm(cloth) * 0.3
        hit = np.zeros(sec(1.5), np.float32)
        place(hit, speed(trim(load(IMP / f"{bang}.ogg")), 0.8), 0)
        place(hit, trim(load(IMP / "impact_glass_medium_002.ogg")) * 0.5, 0.01)    # 窓ガラスが震える
        x = place(x, norm(reverb(hit, 0.7, 0.35)) * 1.2, 0)
        mono(d / f"82_bang_gust_{v}.mp3", x, peak=0.85, q=6)


# ---------------------------------------------------------------- 最終話・全話（映写機）
def projector_from(tick, motor, L):
    """映写機：時計のカチッという本物の音を 1秒24回の送りに並べ、モーターの唸りを重ねる"""
    x = np.zeros(sec(L), np.float32)
    for k in range(int(L * 24)):
        place(x, tick * (0.8 + 0.2 * np.sin(k)), k / 24)
    return x + filt(motor[: len(x)] if len(motor) >= len(x) else np.resize(motor, len(x)), 80, 400) * 0.6


def ep9():
    d = OUT / "ep9"
    ticks = {"A": "4-188033-A-38.wav", "B": "4-181035-A-38.wav", "C": "5-219342-A-38.wav"}
    begin()
    motor = ambience([esc(f) for f in ("3-152020-A-36.wav", "3-152020-C-36.wav", "5-231551-A-36.wav")], 62, 1.5, 7)
    motor_src = set(CUR)
    for v, f in ticks.items():
        begin()
        CUR.update(motor_src)
        ev = events(esc(f), 0.2)
        tick = trim(ev[0])[: sec(0.05)] if ev else trim(esc(f))[: sec(0.05)]
        loop = projector_from(tick, motor, 62)
        mono(d / f"94_projector_loop_{v}.mp3", reverb(loop_seam(loop, 2.0), 1.6, 0.4, 3000), peak=0.5)
        # 気配の音（全話、各話で1回）：映写機が一瞬だけ回り、止まる。遠く、小さく
        p = projector_from(tick, motor, 1.2) * np.sin(np.pi * np.arange(sec(1.2)) / sec(1.2)) ** 2
        mono(OUT / "shared" / f"79_presence_projector_{v}.mp3", reverb(filt(p, hi=3500), 1.6, 0.6, 2500), peak=0.35)
        # ノブが向こうから引き戻される
        begin()
        x = np.zeros(sec(3.4), np.float32)
        for i, t0 in enumerate((0.2, 1.6)):
            place(x, trim(load(RPG / "metal_click.ogg")) * 0.5, t0)
            place(x, speed(trim(load(RPG / "creak_1.ogg")), 1.3)[: sec(0.6)] * 0.4, t0 + 0.08)
            place(x, trim(load(RPG / "metal_latch.ogg")), t0 + 0.75)
        mono(d / f"96_knob_held_{v}.mp3", reverb(x, 0.8, 0.3), peak=0.8)


# ---------------------------------------------------------------- 環境音（1通り）
def ambiences():
    begin()
    rain = ambience([esc(f) for f in ("2-81731-A-10.wav", "4-163264-A-10.wav", "2-87781-A-10.wav", "4-160999-A-10.wav",
                                      "1-29561-A-10.wav", "4-161127-A-10.wav")], 62, 1.5, 1)
    mono(OUT / "ep7" / "74_rain_loop_A.mp3", rain, peak=0.5, q=4, steady=True)
    begin()
    water = ambience([esc(f) for f in ("1-79220-A-17.wav", "5-212734-A-17.wav", "1-61221-A-17.wav", "5-215634-A-17.wav")], 62, 1.5, 2)
    drops = ambience([esc(f) for f in ("5-261433-A-15.wav", "1-90797-A-15.wav", "3-156907-A-15.wav")], 62, 1.0, 3)
    n = min(len(water), len(drops))
    mono(OUT / "ep7" / "75_channel_loop_A.mp3", reverb(filt(water[:n], hi=3000) * 0.8 + drops[:n] * 0.3, 2.0, 0.5, 2500), peak=0.55, q=4, steady=True)
    begin()
    waves = ambience([esc(f) for f in ("3-187710-A-11.wav", "4-195497-B-11.wav", "2-124662-A-11.wav", "4-195497-A-11.wav",
                                       "5-219379-A-11.wav", "2-132157-B-11.wav")], 92, 2.0, 4)
    bugs = ambience([esc(f) for f in ("4-130891-A-7.wav", "1-19501-A-7.wav", "2-99955-B-7.wav", "5-216213-A-13.wav")], 92, 1.0, 5)
    n = min(len(waves), len(bugs))
    mono(OUT / "ep2" / "23_insect_tide_loop_A.mp3", waves[:n] * 0.7 + filt(bugs[:n], 1500, 9000) * 0.35, peak=0.6, q=4, steady=True)


# ---------------------------------------------------------------- 町と部屋の環境音（第四・五・六・八話）
def avenue():
    """第四話 昼の大通り：遠い車の流れ、たくさんの軽い足音、まれに遠くのクラクション。人の声は入れない"""
    begin()
    engines = {"A": ("4-186940-A-44.wav", "4-186938-A-44.wav", "4-186935-A-44.wav"),
               "B": ("1-50455-A-44.wav", "1-50454-A-44.wav", "4-186935-A-44.wav"),
               "C": ("4-186940-A-44.wav", "1-50454-A-44.wav", "3-141240-A-44.wav")}
    horns = {"A": ("4-175845-A-43.wav", "1-26177-A-43.wav"), "B": ("2-144137-A-43.wav", "1-19026-A-43.wav"),
             "C": ("4-175845-A-43.wav", "2-54086-A-43.wav", "1-26176-A-43.wav")}
    far = {"A": ("3-143560-A-47.wav",), "B": ("2-135649-C-45.wav", "1-54065-B-45.wav"), "C": ("3-143560-A-47.wav", "2-98866-A-47.wav")}
    steps = [s for f in ("5-51149-A-25.wav", "5-234263-A-25.wav", "1-51147-A-25.wav") for s in events(esc(f))]
    steps = [filt(trim(s), 150, 5000) for s in steps if len(s) > sec(0.03)]
    for i, v in enumerate("ABC"):
        L = 62
        traffic = filt(ambience([esc(f) for f in engines[v]], L, 1.5, 20 + i), 60, 1800)
        hum = filt(ambience([esc(f) for f in far[v]], L, 2.0, 30 + i), hi=900)          # 電車・飛行機：ごく薄く
        walk = sum(scatter(steps, L, (0.12, 0.45), (0.15, 0.5), 40 + i + k * 7) for k in range(3))   # 何人もが行き交う
        honks = [trim(esc(f))[: sec(1.2)] for f in horns[v]]
        honk = scatter([distance(h * env(len(h), 0.01, 0.3), 3) for h in honks], L, (7, 16), (0.4, 1.0), 50 + i)
        x = mix(norm(traffic) * 0.5, norm(hum) * 0.12, norm(walk) * 0.35, norm(honk) * 0.18)
        bed(OUT / "ep4" / f"43_avenue_loop_{v}.mp3", reverb(x, 1.2, 0.2, 3500), peak=0.6)


def restaurant():
    """第六話 ファミレス：皿とカトラリーの触れ合い、グラス、すする音、低い空調。
    ざわめきは本物の録音がないので、音程のないこもった雑音をごく薄く（声の合成はしない）。C はざわめきなし"""
    begin()
    dish = [trim(load(IMP / f"impact_{k}_light_{i:03d}.ogg")) for k in ("plate", "glass", "metal") for i in range(5)]
    sips = [filt(trim(s), hi=4000) for f in ("1-17295-A-29.wav", "2-102581-A-29.wav") for s in events(esc(f), 0.3)]
    pours = [trim(esc(f)) for f in ("1-61221-A-17.wav", "5-215634-A-17.wav")]
    for i, (v, murmur) in enumerate((("A", 0.12), ("B", 0.07), ("C", 0.0))):
        L = 62
        near = scatter(dish, L, (0.4, 2.2), (0.15, 0.6), 60 + i)
        far = scatter([filt(c, hi=2500) for c in dish], L, (0.2, 1.0), (0.05, 0.25), 70 + i)
        sip = scatter(sips, L, (4, 11), (0.2, 0.5), 80 + i, cut=0.5)
        pour = scatter([filt(p, hi=3000) for p in pours], L, (14, 25), (0.3, 0.6), 90 + i, cut=2.5)
        room = loop_seam(filt(noise(L + 2, 100 + i), 40, 220, order=3), 2.0)                # 空調の低い鳴り
        buzz = loop_seam(filt(noise(L + 2, 110 + i), 250, 1400) * (0.6 + 0.4 * smooth_random(L + 2, 0.7, 120 + i)[: sec(L + 2)]), 2.0)
        x = mix(norm(near) * 0.5, norm(far) * 0.3, norm(sip) * 0.15, norm(pour) * 0.1, norm(room) * 0.1, norm(buzz) * murmur)
        bed(OUT / "ep6" / f"60_restaurant_ambience_loop_{v}.mp3", reverb(x, 0.9, 0.3, 4000), peak=0.55)


def zapping():
    """第五話 チャンネルを次々に替える：短い砂嵐のあいだに、声ではない本物の録音の切れ端。テレビの小さなスピーカーを通す"""
    begin()
    def jingle(n):
        return load(JINGLE / f"jingles_{n.rstrip('0123456789')}" / f"jingles_{n}.ogg")
    combos = {"A": [("3-130330-A-22.wav", 0.8), ("2-78381-A-46.wav", 0.7), ("SAX03", 0.8), ("4-175845-A-43.wav", 0.8)],
              "B": [("STEEL01", 0.8), ("2-57733-A-22.wav", 0.8), ("1-13572-A-46.wav", 0.8), ("2-144137-A-43.wav", 0.7)],
              "C": [("2-25293-A-22.wav", 0.7), ("PIZZA02", 0.8), ("5-219044-A-46.wav", 0.8), ("NES04", 0.8)]}
    for i, (v, seq) in enumerate(combos.items()):
        x = np.zeros(sec(5), np.float32)
        rg = np.random.default_rng(130 + i)
        t = 0.05
        for k, (src, dur) in enumerate(seq):
            st = filt(noise(0.18, 140 + i * 10 + k), 800, 7000) * env(sec(0.18), 0.003, 0.15)    # ザッ（砂嵐）
            place(x, st * 0.6, t)
            t += rg.uniform(0.12, 0.18)
            c = esc(src) if src.endswith(".wav") else jingle(src)
            c = trim(c)
            a = int(rg.uniform(0, max(1, len(c) - sec(dur)) * 0.5)) if src.endswith(".wav") else 0
            c = c[a:a + sec(dur)]
            c = c / max(np.abs(c).max(), 1e-6) * env(len(c), 0.004, 0.25)
            place(x, tv(c) * 0.8, t)
            t += len(c) / SR
        place(x, filt(noise(0.15, 199 + i), 800, 7000) * 0.5 * env(sec(0.15), 0.003, 0.1), t)
        mono(OUT / "ep5" / f"53_zapping_{v}.mp3", x[: sec(t + 0.2)], peak=0.8)


def room_tone():
    """第八話 夜明け前のからっぽの部屋：閉めた窓の外の風が、ごく低く、こもって聞こえるだけ"""
    begin()
    sets = {"A": ("3-246513-A-16.wav", "3-246513-B-16.wav", "4-163609-B-16.wav", "4-163608-B-16.wav"),
            "B": ("3-134699-A-16.wav", "3-134699-B-16.wav", "4-163609-B-16.wav", "2-104952-B-16.wav")}
    for i, (v, files) in enumerate(sets.items()):
        L = 62
        wind = filt(ambience([esc(f) for f in files], L, 2.0, 150 + i), 30, 280, order=3)
        floor = loop_seam(filt(noise(L + 2, 160 + i), 20, 120, order=3), 2.0)            # 部屋そのものの、ほぼ聞こえない低い鳴り
        x = mix(norm(wind) * 0.6, norm(floor) * 0.15)
        bed(OUT / "ep8" / f"81_room_tone_loop_{v}.mp3", x, peak=0.25)


# ---------------------------------------------------------------- やり直し（v2）：KP が「全部だめ」とした4つ
# 前の版がだめだった理由の見立て
#  51・52 鉄のドア：Kenney の「掛け金」と「金属を叩く音」を重ねただけで、ドアではなく金属を殴る音だった。
#                   → 本物の鉄扉の録音（AudioAugust の metaldoor_*、CC0 パックの metal_open/close）を使い、
#                     団地の外廊下（コンクリート）の短い跳ね返りをつけ、部屋ごとに遠近と左右を変える
#  57 新聞が窓に：本を閉じる音（厚く重い「ドン」）で、紙らしさがなかった。
#                   → 本物の紙の録音（ばさっ・めくれ・こすれ）を主役に、ガラスは薄い「とん」と窓枠のかたかただけ、風の息を前後に
#  60 ファミレス：人の声の録音がなく、食器の音を散らしただけ＋雑音だった（店のざわめきにならない）。
#                   → 本物のレストランの録音（CC0）を、声が聞き取れなくなるまでこもらせて何枚も重ね、近くの本物の食器の音を足す
def aug(rel):
    return trim(load(AUG / rel))


def lav(rel):
    return trim(load(LAV / rel))


def corridor(x, k, seed=0):
    """団地の外廊下：k 部屋むこう。遠いほど小さくこもる＋コンクリートの壁の短い跳ね返り（約 0.09 秒）"""
    y = distance(x, k)
    slap = np.zeros(len(y) + sec(0.3), np.float32)
    slap[: len(y)] += y
    place(slap, filt(y, hi=2000) * 0.35, 0.09 + 0.01 * k)
    return slap


def iron_door(kind, part):
    """重い鉄の玄関ドア。part='open'：ガチャ（ノブ・錠）→ ぎい（重い蝶番）、'close'：バタン（鉄の板と枠）＋かちゃ"""
    x = np.zeros(sec(2.0), np.float32)
    if kind == "aug":
        if part == "open":
            place(x, aug("doors/metal/metaldoor_lock_2.ogg") * 0.7, 0)
            place(x, speed(aug("doors/metal/metaldoor_open_1.ogg"), 0.85), 0.25)
        else:
            place(x, speed(aug("doors/metal/metaldoor_close_3.ogg"), 0.9), 0)
            place(x, aug("doors/metal/metal_click_1.ogg") * 0.4, 0.45)
    else:
        if part == "open":
            place(x, aug("doors/metal/metaldoor_lock_4.ogg") * 0.6, 0)
            place(x, speed(lav("100-CC0-wood-metal-SFX/metal_open_01.ogg"), 0.9), 0.2)
        else:
            place(x, speed(lav("100-CC0-wood-metal-SFX/metal_close_01.ogg"), 0.9), 0)
            place(x, filt(aug("impacts/metallic/metallic_hit_hall_1.ogg"), 60, 600) * 0.12, 0.01)   # 鉄の板の低い鳴り、ごく薄く
    return trim(x, -60)


def tadaima_approach_v2():
    """第五話：4部屋むこうから隣の部屋まで、一部屋ずつ、ガチャ・ぎい …（「ただいまー」の間）… バタン。約 18 秒。左から正面へ"""
    for v, (kind, steps) in {"A": ("aug", False), "B": ("lav", False), "C": ("aug", True)}.items():
        begin()
        L, t = 18.5, 0.4
        l, r = np.zeros(sec(L + 1), np.float32), np.zeros(sec(L + 1), np.float32)
        walk = [aug(f"step sounds/pavement/pav_step_{i}.flac") for i in range(1, 9)] if steps else []
        for k, p in zip((4, 3, 2, 1), (-0.85, -0.6, -0.4, -0.2)):
            for part, dt in (("open", 2.6), ("close", 1.5)):     # 開けて、声の間、閉めて、次の部屋へ
                a, b = pan(corridor(iron_door(kind, part), k), p)
                place(l, a, t), place(r, b, t)
                t += dt
            if steps and k > 1:                                   # 次の部屋まで歩く（サンダルの軽い足音）
                for j, ts in enumerate(np.arange(t - 1.3, t - 0.1, 0.42)):
                    a, b = pan(corridor(filt(walk[(k * 3 + j) % 8], 200, 5000) * 0.35, k), p + 0.1)
                    place(l, a, ts), place(r, b, ts)
        stereo(OUT / "ep5" / f"51_tadaima_approach_v2_{v}.mp3", l[: sec(t + 0.2)], r[: sec(t + 0.2)], peak=0.8)


def tadaima_arrive_v2():
    """第五話（押入れに隠れた場合）：この部屋の鉄のドアが開く → ぎし、と床 → 沈黙 → バタンと閉まる。押入れの襖越しにこもる"""
    creaks = {"A": [("100-CC0-wood-metal-SFX/wood_squeak_01.ogg", 0.7)],
              "B": [("esc:1-51805-A-33.wav", 0.8)],
              "C": [("100-CC0-wood-metal-SFX/wood_squeak_02.ogg", 0.75), ("100-CC0-wood-metal-SFX/wood_squeak_01.ogg", 0.65)]}
    for v, kind in (("A", "aug"), ("B", "lav"), ("C", "aug")):
        begin()
        x = np.zeros(sec(11), np.float32)
        place(x, iron_door(kind, "open"), 0.3)
        t = 2.4
        for rel, f in creaks[v]:
            c = trim(esc(rel[4:]))[: sec(0.9)] if rel.startswith("esc:") else lav(rel)
            c = speed(c, f)
            place(x, aug("step sounds/room/step2.flac") * 0.35, t - 0.05)     # 体重をかける
            place(x, c * env(len(c), 0.01, 0.4) * 0.8, t)                      # ぎし
            t += 1.3
        place(x, iron_door(kind, "close") * 0.9, 7.0)
        x = reverb(filt(x, hi=2800), 0.5, 0.25)                                # 襖越し、六畳の小さな響き
        mono(OUT / "ep5" / f"52_tadaima_arrive_v2_{v}.mp3", x, peak=0.8)


def window_slap_v2():
    """第五話：強い風で、新聞が窓に叩きつけられる「バサッ！」→ 押しつけられたままばたつく → はがれて飛んでいく。部屋の中から"""
    BOOK = "bb - Books, Paper, Writing (Jan 2021)"
    RET = "BB_Retail Therapy Sample Pack"
    hits = {"A": ("100-CC0-SFX/paper_01.ogg", f"{BOOK}/Riffle Pages 1.wav", "impact_glass_light_001", (0.35,)),
            "B": (f"{RET}/Shoofing Papers 1.wav", f"{BOOK}/Page Turn Fast.wav", "impact_glass_light_003", (0.35,)),
            "C": ("100-CC0-SFX/paper_03.ogg", f"{BOOK}/Riffle Pages 2.wav", "impact_glass_light_000", (0.35, 1.25))}
    winds = ("3-246513-A-16.wav", "4-163609-B-16.wav")
    for i, (v, (slap, flutter, glass, times)) in enumerate(hits.items()):
        begin()
        L = 3.2
        x = np.zeros(sec(L), np.float32)
        w = trim(esc(winds[i % 2]))[: sec(L)]
        w = filt(w, 80, 1800) * np.interp(np.arange(len(w)), [0, sec(0.3), sec(1.0), sec(2.2), len(w) - 1], [0.2, 1.0, 0.6, 0.8, 0.0])
        place(x, w * 0.25, 0)                                                   # 窓の外の風（閉めた窓越し）
        s, fl = lav(slap), lav(flutter)
        for n, t0 in enumerate(times):
            g = 1.0 if n == 0 else 0.7
            place(x, s[: sec(0.5)] * env(min(len(s), sec(0.5)), 0.002, 0.15) * g, t0)          # バサッ（紙が平らにぶつかる）
            place(x, filt(trim(load(IMP / f"{glass}.ogg")), hi=3500) * 0.35 * g, t0 + 0.004)    # ガラスの薄い「とん」
            place(x, lav(f"{RET}/Rattling Cheap Wood 1.wav")[: sec(0.25)] * 0.18 * g, t0 + 0.01)  # 窓枠がかたっ
            fseg = fl[: sec(0.8)] * np.linspace(1, 0.2, min(len(fl), sec(0.8))) ** 2
            place(x, filt(fseg, 300, 7000) * 0.4 * g, t0 + 0.12)               # 押しつけられて、ばたばた
        tail = lav("100-CC0-SFX/paper_04.ogg")
        place(x, filt(tail, 400, 6000) * env(len(tail), 0.05, 0.25) * 0.3, times[-1] + 1.0)      # はがれて飛んでいく
        mono(OUT / "ep5" / f"57_window_slap_v2_{v}.mp3", reverb(filt(x, hi=7000), 0.5, 0.2), peak=0.85)


def restaurant_v2():
    """第六話 ファミレス：本物のレストランの録音（CC0）。言葉が聞き取れないよう、高い音（子音）を削り、時間をずらした何枚かを重ねて
    一人ひとりの声を溶かす。手前に本物の食器・カトラリー・グラスの音。声の合成・歌は一切使わない"""
    begin()
    src = load(STK / "lenautile_restaurant.ogg")
    base_src = set(CUR)
    chunks = [src[a: a + sec(5)] for a in range(0, len(src) - sec(5), sec(2.5))]
    RET = "BB_Retail Therapy Sample Pack"
    near_files = [f"{RET}/Silverware {i}.wav" for i in range(1, 7)] + [f"{RET}/Silverware Ting {i}.wav" for i in range(1, 5)] + \
                 [f"{RET}/Ceramic Bowl {i}.wav" for i in range(1, 8)] + [f"{RET}/Glass Glasses 1.wav"] + [f"100-CC0-SFX/dishes_0{i}.ogg" for i in range(1, 5)]
    vent = "bb - Fans and Drones (Jul 2021)/Air Vent.wav"
    # 種類：（こもらせる上限 Hz, 重ねる枚数, 食器の間隔, 食器の大きさ, 響き）
    kinds = {"A": (900, 3, (0.5, 2.5), 0.35, 0.3), "B": (650, 4, (1.0, 4.0), 0.25, 0.45), "C": (1100, 4, (0.3, 1.5), 0.45, 0.3)}
    for i, (v, (hi, layers, gap, dg, wet)) in enumerate(kinds.items()):
        begin()
        CUR.update(base_src)
        L = 62
        crowd = sum(filt(ambience(chunks, L, 1.5, 300 + i * 10 + k), 120, hi, order=4) for k in range(layers))
        near = scatter([filt(lav(f), 150, 9000) for f in near_files], L, gap, (0.3, 1.0), 320 + i)
        hum = filt(ambience([lav(vent)], L, 2.0, 330 + i), 40, 400)
        x = mix(norm(crowd) * 0.6, norm(near) * dg, norm(hum) * 0.12)
        bed(OUT / "ep6" / f"60_restaurant_ambience_loop_v2_{v}.mp3", reverb(x, 0.9, wet, 4000), peak=0.5)


def window_slap_v3():
    """第五話 v3：新聞紙はそんなに甲高くない。大きな紙が窓ガラスに「ぼすっ」と当たり、低くばたつく。
    閉めた窓越しに部屋の中で聞くので、高い音は強く削る（上限 2〜3kHz）。紙のかさかさは控えめ、やわらかい当たりとはためきが主役"""
    BOOK = "bb - Books, Paper, Writing (Jan 2021)"
    RET = "BB_Retail Therapy Sample Pack"
    # 種類：（当たりの紙, はためきの紙, 上限 Hz, 紙を遅くする倍率, 当たる時刻）
    kinds = {"A": ("100-CC0-SFX/paper_01.ogg", f"{BOOK}/Riffle Pages 1.wav", 2000, 0.7, (0.35,)),
             "B": (f"{RET}/Shoofing Papers 1.wav", f"{BOOK}/Page Turn Fast.wav", 2500, 0.75, (0.35,)),
             "C": ("100-CC0-SFX/paper_03.ogg", f"{BOOK}/Riffle Pages 2.wav", 3000, 0.8, (0.35, 1.3))}
    winds = ("3-246513-A-16.wav", "4-163609-B-16.wav")
    for i, (v, (slap, flutter, hi, f, times)) in enumerate(kinds.items()):
        begin()
        L = 3.4
        x = np.zeros(sec(L), np.float32)
        w = trim(esc(winds[i % 2]))[: sec(L)]
        w = filt(w, 60, 900) * np.interp(np.arange(len(w)), [0, sec(0.3), sec(1.0), sec(2.2), len(w) - 1], [0.2, 1.0, 0.6, 0.8, 0.0])
        place(x, w * 0.3, 0)                                                    # 窓の外の風、低く
        s, fl = speed(lav(slap), f), speed(lav(flutter), f)
        thump = filt(noise(0.25, 400 + i), 50, 350) * env(sec(0.25), 0.004, 0.08)
        for n, t0 in enumerate(times):
            g = 1.0 if n == 0 else 0.65
            place(x, filt(s[: sec(0.6)], 80, hi) * env(min(len(s), sec(0.6)), 0.006, 0.2) * 0.8 * g, t0)   # ぼすっ（紙が平らに当たる）
            place(x, thump * 0.9 * g, t0)                                                                   # ガラス越しの低い当たり
            place(x, filt(lav(f"{RET}/Rattling Cheap Wood 1.wav")[: sec(0.2)], 80, 1200) * 0.12 * g, t0 + 0.01)  # 窓枠がかすかに
            fseg = fl[: sec(1.0)] * np.linspace(1, 0.15, min(len(fl), sec(1.0))) ** 2
            place(x, filt(fseg, 120, hi * 0.8) * 0.45 * g, t0 + 0.12)          # 押しつけられて、ばたばた
        tail = speed(lav("100-CC0-SFX/paper_04.ogg"), f)
        place(x, filt(tail, 120, hi * 0.7) * env(len(tail), 0.05, 0.25) * 0.3, times[-1] + 1.1)        # はがれて飛んでいく
        mono(OUT / "ep5" / f"57_window_slap_v3_{v}.mp3", reverb(filt(x, 40, hi, order=4), 0.5, 0.2), peak=0.82)


def restaurant_v3():
    """第六話 ファミレス v3：金属音は食べている人にしか気にならない。主役は部屋全体のこもったざわめき＋空調。
    カトラリーの音は遠く、まれに、鈍く（A ごく小さく / B ほとんどなし / C なし）。声の合成は一切しない"""
    begin()
    src = load(STK / "lenautile_restaurant.ogg")
    base_src = set(CUR)
    chunks = [src[a: a + sec(5)] for a in range(0, len(src) - sec(5), sec(2.5))]
    RET = "BB_Retail Therapy Sample Pack"
    clink_files = [f"{RET}/Silverware {i}.wav" for i in range(1, 7)] + [f"{RET}/Ceramic Bowl {i}.wav" for i in range(1, 8)]
    vent = "bb - Fans and Drones (Jul 2021)/Air Vent.wav"
    kinds = {"A": (0.06, (6, 14)), "B": (0.025, (15, 30)), "C": (0.0, None)}
    for i, (v, (dg, gap)) in enumerate(kinds.items()):
        begin()
        CUR.update(base_src)
        L = 62
        crowd = sum(filt(ambience(chunks, L, 1.5, 400 + i * 10 + k), 100, 700, order=4) for k in range(4))
        hum = filt(ambience([lav(vent)], L, 2.0, 430 + i), 40, 600)
        layers = [norm(crowd) * 0.6, norm(hum) * 0.25]
        if dg:
            clinks = scatter([distance(filt(lav(c), 150, 1800), 2) for c in clink_files], L, gap, (0.4, 1.0), 420 + i)
            layers.append(norm(clinks) * dg)
        bed(OUT / "ep6" / f"60_restaurant_ambience_loop_v3_{v}.mp3", reverb(mix(*layers), 1.0, 0.45, 2500), peak=0.5)


def redo():
    tadaima_approach_v2()
    tadaima_arrive_v2()
    window_slap_v2()
    restaurant_v2()
    window_slap_v3()
    restaurant_v3()


# KP が聞いて選んだ候補（本番の build/ccfolia/fx/ に、合成版と同じ名前で上書きする）。51/52 は v2 の C に決定。57/60 は v3 を検討中
PICKS = {
    "ep1/11_footsteps_stop": "A", "ep1/12_door_open_close": "A", "ep1/13_scratching_loop": "B", "ep1/14_handle_rattle": "A",
    "ep2/23_insect_tide_loop": "A",
    "ep4/42_tarp_run_loop": "A", "ep4/43_avenue_loop": "A", "ep4/44_gusha": "C",
    "ep5/51_tadaima_approach": "v2_C", "ep5/52_tadaima_arrive": "v2_C", "ep5/53_zapping": "A",
    "ep7/74_rain_loop": "A", "ep7/75_channel_loop": "A",
    "ep8/81_room_tone_loop": "A", "ep8/82_bang_gust": "C",
    "ep9/94_projector_loop": "B", "ep9/96_knob_held": "B",
    "shared/79_presence_projector": "B",
}
PROD = ROOT / "build" / "ccfolia" / "fx"


def credit_lines(paths):
    """録音の一覧から出典の文を作る（ライブラリごと。ESC-50 は録音ごと）"""
    used = set().union(*(SOURCES.get(Path(p).resolve(), set()) for p in paths))
    libs = {q.relative_to(LIB.absolute()).parts[0] for q in used}
    lic = (LIB / "esc50" / "LICENSE").read_text(encoding="utf-8", errors="ignore")
    lines = ["効果音の出典", ""]
    if libs & {"kenney_impact", "kenney_rpg", "kenney_more"}:
        lines += ["Kenney「Impact Sounds」「RPG Audio」「Casino Sounds」「Music Jingles」（CC0） https://kenney.nl", ""]
    if "audioaugust" in libs:
        lines += ["AudioAugust（Johannes \"Hanni\" Schneider / Inexor, CC BY 4.0） https://github.com/inexorgame/audioaugust", ""]
    if "lavender_cc0" in libs:
        lines += ["CC0 Public Domain Sounds（まとめ: lavenderdotpet。Ben Burnes の素材パックほか、CC0） https://github.com/lavenderdotpet/CC0-Public-Domain-Sounds", ""]
    if "stk_assets" in libs:
        lines += ["レストランの録音: Alcappuccino（CC0） https://freesound.org/people/Alcappuccino/sounds/263528/ （SuperTuxKart の素材より）", ""]
    escs = sorted({q.name for q in used if q.parent == ESC.absolute()})
    if escs:
        lines.append("ESC-50（K. J. Piczak, CC BY-NC 3.0） https://github.com/karolpiczak/ESC-50 より、次の録音を加工して使用:")
        seen = []
        for f in escs:
            stem = "-".join(f.split("-")[:3])
            m = re.search(r"\[" + re.escape(stem) + r"\.ogg\]: (.+)", lic)
            t = f"- {m.group(1).strip() if m else f}"
            if t not in seen:
                seen.append(t)
        lines += seen
    return lines


def credits():
    """候補ぜんぶの出典（fx_real/CREDITS.txt）"""
    (OUT / "CREDITS.txt").write_text("\n".join(credit_lines(list(SOURCES))) + "\n", encoding="utf-8")
    print(f"CREDITS.txt（候補 {len(SOURCES)} 本）")


def install():
    """選ばれた候補を本番の名前で fx/ に写し、本番で使う音だけの出典を SFX-CREDITS.txt に書く"""
    import shutil
    used = []
    for name, v in PICKS.items():
        src = OUT / f"{name}_{v}.mp3"
        dst = PROD / f"{name}.mp3"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        used.append(src)
    (ROOT / "SFX-CREDITS.txt").write_text("\n".join(credit_lines(used)) + "\n", encoding="utf-8")
    print(f"本番に {len(used)} 本を入れた（SFX-CREDITS.txt を更新）")


def main():
    for k in ("ep1", "ep2", "ep4", "ep5", "ep6", "ep7", "ep8", "ep9", "shared"):
        (OUT / k).mkdir(parents=True, exist_ok=True)
    ep1()
    ep4()
    ep5()
    ep8()
    ep9()
    ambiences()
    avenue()
    restaurant()
    zapping()
    room_tone()
    redo()
    credits()
    install()


if __name__ == "__main__":
    main()
