"""効果音を、本物の録音から作り直す（合成の効果音は「下手」だったため。README「わかったこと」）。

私は耳で聞けないので、録音を測って候補を絞り、主な音は A・B・C の3通りを作る。どれを使うかは KP が聞いて選ぶ。
加工だけをこちらで行う：切り詰め・音量・こもらせる（ドア越し・遠く）・響き・左右の位置・重ね・ループのつなぎ目。

素材（build/sfxlib/ に置く。git の対象外）
  kenney_impact/  Kenney「Impact Sounds」（CC0）       git clone https://github.com/Boyquotes/kenney-impact-sounds-for-godot
  kenney_rpg/     Kenney「RPG Audio」（CC0）           git clone https://github.com/Boyquotes/kenney-rpg-audio-for-godot
  kenney_more/    Kenney の音素材のまとめ（CC0）        git clone https://github.com/ismetcabbar9-oss/kenney-audio-assets の「Audio (295 files)」
  esc50/          ESC-50（Freesound の録音。CC BY-NC。非営利で、出典の表記が要る）  git clone https://github.com/karolpiczak/ESC-50
  使った ESC-50 の録音の出典は build/ccfolia/fx_real/CREDITS.txt に書き出す

出力: build/ccfolia/fx_real/<元のファイル名>_A/B/C.mp3（候補）と CREDITS.txt
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
USED_ESC = set()


# ---------------------------------------------------------------- 読み込みと加工
def load(path):
    """どの形式でも 48kHz モノラルの配列に"""
    path = Path(path)
    if path.parent == ESC:
        USED_ESC.add(path.name)
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


def mono(path, x, peak=0.8, q=3, steady=False):
    """steady=True は環境音：まれな大きな音ではなく、ふだんの大きさ（99.9%）で音量を決める"""
    if steady:
        x = np.clip(x / max(np.percentile(np.abs(x), 99.9), 1e-6) * peak, -0.95, 0.95)
        write_mp3(path, x.astype(np.float32), q=q)
    else:
        write_mp3(path, norm(x, peak), q=q)


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
    # グシャ：重く湿ったものが背後に落ちる
    combos = {"A": ("impact_soft_heavy_000", "impact_punch_heavy_002"), "B": ("impact_soft_heavy_003", "impact_wood_heavy_001"),
              "C": ("impact_punch_heavy_004", "impact_soft_medium_001")}
    for v, (a, b) in combos.items():
        x = np.zeros(sec(2.5), np.float32)
        place(x, speed(trim(load(IMP / f"{a}.ogg")), 0.8), 0.05)
        place(x, speed(trim(load(IMP / f"{b}.ogg")), 0.7) * 0.6, 0.06)
        place(x, filt(trim(esc("1-84536-A-39.wav"))[: sec(0.3)], 300, 2500) * 0.12, 0.07)   # 細かく潰れる音を、ごく薄く
        mono(d / f"44_gusha_{v}.mp3", reverb(filt(x, hi=6000), 0.9, 0.3), peak=0.85)
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
    motor = ambience([esc(f) for f in ("3-152020-A-36.wav", "3-152020-C-36.wav", "5-231551-A-36.wav")], 62, 1.5, 7)
    for v, f in ticks.items():
        ev = events(esc(f), 0.2)
        tick = trim(ev[0])[: sec(0.05)] if ev else trim(esc(f))[: sec(0.05)]
        loop = projector_from(tick, motor, 62)
        mono(d / f"94_projector_loop_{v}.mp3", reverb(loop_seam(loop, 2.0), 1.6, 0.4, 3000), peak=0.5)
        # 気配の音（全話、各話で1回）：映写機が一瞬だけ回り、止まる。遠く、小さく
        p = projector_from(tick, motor, 1.2) * np.sin(np.pi * np.arange(sec(1.2)) / sec(1.2)) ** 2
        mono(OUT / "shared" / f"79_presence_projector_{v}.mp3", reverb(filt(p, hi=3500), 1.6, 0.6, 2500), peak=0.35)
        # ノブが向こうから引き戻される
        x = np.zeros(sec(3.4), np.float32)
        for i, t0 in enumerate((0.2, 1.6)):
            place(x, trim(load(RPG / "metal_click.ogg")) * 0.5, t0)
            place(x, speed(trim(load(RPG / "creak_1.ogg")), 1.3)[: sec(0.6)] * 0.4, t0 + 0.08)
            place(x, trim(load(RPG / "metal_latch.ogg")), t0 + 0.75)
        mono(d / f"96_knob_held_{v}.mp3", reverb(x, 0.8, 0.3), peak=0.8)


# ---------------------------------------------------------------- 環境音（1通り）
def ambiences():
    rain = ambience([esc(f) for f in ("2-81731-A-10.wav", "4-163264-A-10.wav", "2-87781-A-10.wav", "4-160999-A-10.wav",
                                      "1-29561-A-10.wav", "4-161127-A-10.wav")], 62, 1.5, 1)
    mono(OUT / "ep7" / "74_rain_loop_A.mp3", rain, peak=0.5, q=4, steady=True)
    water = ambience([esc(f) for f in ("1-79220-A-17.wav", "5-212734-A-17.wav", "1-61221-A-17.wav", "5-215634-A-17.wav")], 62, 1.5, 2)
    drops = ambience([esc(f) for f in ("5-261433-A-15.wav", "1-90797-A-15.wav", "3-156907-A-15.wav")], 62, 1.0, 3)
    n = min(len(water), len(drops))
    mono(OUT / "ep7" / "75_channel_loop_A.mp3", reverb(filt(water[:n], hi=3000) * 0.8 + drops[:n] * 0.3, 2.0, 0.5, 2500), peak=0.55, q=4, steady=True)
    waves = ambience([esc(f) for f in ("3-187710-A-11.wav", "4-195497-B-11.wav", "2-124662-A-11.wav", "4-195497-A-11.wav",
                                       "5-219379-A-11.wav", "2-132157-B-11.wav")], 92, 2.0, 4)
    bugs = ambience([esc(f) for f in ("4-130891-A-7.wav", "1-19501-A-7.wav", "2-99955-B-7.wav", "5-216213-A-13.wav")], 92, 1.0, 5)
    n = min(len(waves), len(bugs))
    mono(OUT / "ep2" / "23_insect_tide_loop_A.mp3", waves[:n] * 0.7 + filt(bugs[:n], 1500, 9000) * 0.35, peak=0.6, q=4, steady=True)


# ---------------------------------------------------------------- 町と部屋の環境音（第四・五・六・八話）
def avenue():
    """第四話 昼の大通り：遠い車の流れ、たくさんの軽い足音、まれに遠くのクラクション。人の声は入れない"""
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
        mono(OUT / "ep4" / f"43_avenue_loop_{v}.mp3", reverb(x, 1.2, 0.2, 3500), peak=0.6, q=4, steady=True)


def restaurant():
    """第六話 ファミレス：皿とカトラリーの触れ合い、グラス、すする音、低い空調。
    ざわめきは本物の録音がないので、音程のないこもった雑音をごく薄く（声の合成はしない）。C はざわめきなし"""
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
        x = mix(norm(near) * 0.5, norm(far) * 0.3, norm(sip) * 0.15, norm(pour) * 0.1, norm(room) * 0.25, norm(buzz) * murmur)
        mono(OUT / "ep6" / f"60_restaurant_ambience_loop_{v}.mp3", reverb(x, 0.9, 0.3, 4000), peak=0.55, q=4, steady=True)


def zapping():
    """第五話 チャンネルを次々に替える：短い砂嵐のあいだに、声ではない本物の録音の切れ端。テレビの小さなスピーカーを通す"""
    def jingle(n):
        return load(JINGLE / f"jingles_{n.rstrip('0123456789')}" / f"jingles_{n}.ogg")
    combos = {"A": [("3-130330-A-22.wav", 0.5), ("2-78381-A-46.wav", 0.4), ("SAX03", 0.5), ("4-175845-A-43.wav", 0.6)],
              "B": [("STEEL01", 0.6), ("2-57733-A-22.wav", 0.5), ("1-13572-A-46.wav", 0.5), ("2-144137-A-43.wav", 0.4)],
              "C": [("2-25293-A-22.wav", 0.4), ("PIZZA02", 0.5), ("5-219044-A-46.wav", 0.6), ("NES04", 0.5)]}
    for i, (v, seq) in enumerate(combos.items()):
        x = np.zeros(sec(4.2), np.float32)
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
    sets = {"A": ("3-246513-A-16.wav", "3-246513-B-16.wav", "4-163609-B-16.wav", "4-163608-B-16.wav"),
            "B": ("3-134699-A-16.wav", "3-134699-B-16.wav", "4-163609-B-16.wav", "2-104952-B-16.wav")}
    for i, (v, files) in enumerate(sets.items()):
        L = 62
        wind = filt(ambience([esc(f) for f in files], L, 2.0, 150 + i), 30, 280, order=3)
        floor = loop_seam(filt(noise(L + 2, 160 + i), 20, 120, order=3), 2.0)            # 部屋そのものの、ほぼ聞こえない低い鳴り
        x = mix(norm(wind) * 0.6, norm(floor) * 0.15)
        mono(OUT / "ep8" / f"81_room_tone_loop_{v}.mp3", x, peak=0.25, q=4, steady=True)


def credits():
    """使った ESC-50 の録音の出典（CC BY / CC BY-NC の表記）"""
    lic = (LIB / "esc50" / "LICENSE").read_text(encoding="utf-8", errors="ignore")
    lines = ["効果音の出典", "", "Kenney「Impact Sounds」「RPG Audio」「Casino Sounds」（CC0） https://kenney.nl", "",
             "ESC-50（K. J. Piczak, CC BY-NC 3.0） https://github.com/karolpiczak/ESC-50 より、次の録音を加工して使用:"]
    for f in sorted(USED_ESC):
        stem = "-".join(f.split("-")[:3])
        m = re.search(r"\[" + re.escape(stem) + r"\.ogg\]: (.+)", lic)
        lines.append(f"- {m.group(1).strip() if m else f}")
    (OUT / "CREDITS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"CREDITS.txt（ESC-50 の録音 {len(USED_ESC)} 本）")


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
    credits()


if __name__ == "__main__":
    main()
