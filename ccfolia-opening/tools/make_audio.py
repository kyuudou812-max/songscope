"""オープニングの仮の音を合成する（v5）。秒割りは opening/timing.json、話ごとの変化は opening/escalation.json を読む。

使い方: python3 make_audio.py [話数]
出力: build/opening_audio_ep{N}.wav

音の流れ（予告編の定番：盛り上がり → 黒へのカット → 静寂 → 一撃）
  唸り（droneIn〜cut）→ 逆再生の盛り上がり（swell、cut に吸い込まれる）→ 無音（cut〜hit）
  → 一撃（hit。タイトルの映像より少し先に鳴らす＝Jカット）→ 一撃の余韻の下でタイプ音
"""
import json
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SR = 48000
T = json.loads((ROOT / "opening" / "timing.json").read_text(encoding="utf-8"))
ep_no = sys.argv[1] if len(sys.argv) > 1 else "1"
EP = json.loads((ROOT / "episodes.local.json").read_text(encoding="utf-8"))[ep_no]
ESC = json.loads((ROOT / "opening" / "escalation.json").read_text(encoding="utf-8"))["episodes"][ep_no]
FLICKER = json.loads((ROOT / "opening" / "flicker.json").read_text(encoding="utf-8"))["episodes"][ep_no]["frames"]


def snap(x):
    # 音と映像を合わせる時刻はコマの区切り（1/24秒）に置く。opening/index.html と同じ丸め方
    return np.floor(x * 24 + 0.5) / 24


def card_chars():
    # opening/index.html の cardParts と同じ組み立て
    parts = [EP["no"], f"■ {EP['word']}（{EP['kana']}）", EP["pos"], EP["def"]]
    return sum(len(p) for p in parts)


def lowpass(x, k):
    return np.convolve(x, np.ones(k) / k, "same")


def modes(rng, freqs, decays, amps, length):
    """短く減衰する、音程の揃わない（非調和の）共振の束。数ミリ秒で消えるので、耳は音の高さを聞き取れない"""
    tt = np.arange(length) / SR
    return sum(a * np.sin(2 * np.pi * f * tt + rng.uniform(0, 6.28)) * np.exp(-tt * d) for f, d, a in zip(freqs, decays, amps))


def strike(rng, length, scale, lo):
    """1回の当たり：ごく短い雑音の立ち上がり＋キーキャップの共振（1〜5kHz）＋本体のわずかな鳴り（数百Hz）"""
    tt = np.arange(length) / SR
    burst = np.diff(rng.normal(0, 1, length), prepend=0) * np.exp(-tt * 2500) * 0.5
    cap = modes(rng, [rng.uniform(1600, 2400) * lo, rng.uniform(3000, 4200) * lo, rng.uniform(4800, 6200) * lo],
                [rng.uniform(500, 800), rng.uniform(700, 1100), rng.uniform(900, 1400)], [1.0, 0.6, 0.3], length)
    body = modes(rng, [rng.uniform(420, 700) * lo], [rng.uniform(140, 220)], [0.25], length)
    return (burst + cap + body) * scale


def keystroke(rng, big=False):
    """キーボードの1打（構造上の自然な音）：
    ①押し込んで底に当たる「カッ」（主役）
    ②指を離してばねで戻り、上に当たる小さな「カチ」（0.05〜0.11秒後）
    ③大きいキー（Enter）はキーキャップが大きいぶん低めに鳴り、支えの金具がかすかにカタつく
    200Hz未満はほぼ出さない（部品が小さく軽いので、構造上出ない）"""
    lo = 0.7 if big else 1.0
    length = int(0.16 * SR)
    out = np.zeros(length)
    down = strike(rng, int(0.03 * SR), rng.uniform(0.8, 1.0) * (1.3 if big else 1.0), lo)
    out[:len(down)] += down
    if big:  # 金具の揺れ：小さい当たりが2〜3回
        for _ in range(int(rng.integers(2, 4))):
            k = int(rng.uniform(0.004, 0.014) * SR)
            r = strike(rng, int(0.01 * SR), rng.uniform(0.12, 0.25), 1.3)
            out[k:k + len(r)] += r
    k = int(rng.uniform(0.05, 0.11) * SR)
    up = strike(rng, int(0.02 * SR), rng.uniform(0.25, 0.4), 1.15 * lo)
    out[k:k + len(up)] += up
    # 静かな部屋のごくわずかな響き（7〜13ミリ秒後の小さなこだま）
    for dly, g in ((0.007, 0.12), (0.013, 0.07)):
        k = int(dly * SR)
        out[k:] += lowpass(out[:-k], 4) * g
    return out * 0.45  # 一撃より控えめに（タイプ音の一瞬の山が全体で一番大きくならないように）


def place(out, sig, t0, n):
    s0 = int(t0 * SR)
    if 0 <= s0 < n:
        out[s0:s0 + len(sig)] += sig[: n - s0]


def duration():
    # 辞書カードを打ち終わってから2秒は止めて見せる（tools/render_opening.mjs と同じ計算）
    return max(T["duration"], np.ceil((T["card"] + card_chars() * T["typeStep"] + 2.0) * 24) / 24)


def main():
    n = int(duration() * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(1)
    out = np.zeros(n)
    cut = T["cut"]

    # 蛍光灯のハム音：画面に映っている蛍光灯が鳴らしている音（音にも「理由」を持たせる）
    # 電源50Hzの2倍の100Hzと、その倍音。小さいスピーカーでも聞こえるよう、200〜600Hzの倍音で存在感を出す
    # 話が進むほど、音程がわずかに下がり（humDetune）、ジリジリした歪み（humBuzz）が増える
    f0 = 100 + ESC["humDetune"]
    hum = sum(a * np.sin(2 * np.pi * f0 * h * t) for h, a in ((1, 0.20), (2, 0.16), (3, 0.10), (4, 0.07), (5, 0.04), (6, 0.03)))
    hum = np.tanh(hum * (1 + 6 * ESC["humBuzz"])) / (1 + 2 * ESC["humBuzz"])
    hum += lowpass(rng.normal(0, 1, n), 400) * 0.6                   # 建物のごく低い空気の音
    # 蛍光灯の明滅（opening/flicker.json と同じコマ）：暗いコマではハム音が落ち込み、
    # 暗くなり始めるたびに「カチッ」と鳴る。音の強さ・長さ・音色は1回ごとにばらつかせる
    lamp = np.ones(n)
    dims = dict((f, d) for f, d in FLICKER)
    for f, d in FLICKER:
        a, b = int(f / 24 * SR), int((f + 1) / 24 * SR)
        lamp[a:b] = 1 - d
        # ジジッという放電の雑音（暗いコマの間だけ）
        out[a:b] += rng.normal(0, 1, b - a) * 0.05 * d * (0.5 + rng.random())
        if dims.get(f - 1, 0) <= 0.2 < d:                          # 暗くなり始めた瞬間
            m = int(rng.uniform(0.008, 0.03) * SR)
            sm = max(2, int(rng.uniform(2, 10)))                  # 音色：数字が大きいほどこもる
            click = lowpass(rng.normal(0, 1, m), sm) * np.exp(-np.arange(m) / SR * rng.uniform(120, 260))
            out[a:a + m] += click * rng.uniform(0.15, 0.35) * np.sqrt(sm)
    a0, a1 = T["droneIn"]
    out += hum * lamp * np.clip((t - a0) / (a1 - a0), 0, 1) * (t < cut)

    # 鼓動：唸りの底に、ごく小さく。見ている人自身の体の音のように聞かせる（クワイエット・プレイス）
    # 少しずつ速くなり、カットでハム音と一緒に消える
    h0, h1 = T["heart"]
    b0, b1 = ESC["bpm"]                                              # 話が進むほど速い
    bt = h0
    while bt < h1:
        k = (bt - h0) / (h1 - h0)
        for off, f, amp in ((0.0, 52, 1.0), (0.27, 60, 0.7)):        # ドッ、クン
            s = int((bt + off) * SR)
            m = min(int(0.16 * SR), int(h1 * SR) - s)
            if m <= 0:
                continue
            tt = np.arange(m) / SR
            # 小さいスピーカーでも感じられるよう、2倍・3倍の成分を少し足す
            beat = (np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(4 * np.pi * f * tt) + 0.25 * np.sin(6 * np.pi * f * tt)) \
                * np.exp(-tt * 28) * amp
            out[s:s + m] += beat * 0.16 * min(1.0, (bt - h0) / 1.5 + 0.2)
        bt += 60 / (b0 + (b1 - b0) * k)

    # 逆再生の盛り上がり：残響のような尾を作って逆向きにし、カットの瞬間で切る
    s0, s1 = T["swell"]
    m = int((s1 - s0) * SR)
    tt = np.arange(m) / SR
    tail = lowpass(rng.normal(0, 1, m), 30) * 1.4 + 0.5 * np.sin(2 * np.pi * (90 - 30 * tt) * tt)
    tail *= np.exp(-tt * 4.0)
    rev = tail[::-1] * 0.8
    i0 = int(s0 * SR)
    out[i0:i0 + m] += rev[: n - i0]

    # 一撃：胸に響く低い衝撃（重さ）。余韻をカードの下まで残す
    h = T["hit"]
    k = t >= h
    th = t[k] - h
    hit = 0.95 * np.sin(2 * np.pi * (46 - 8 * th) * th) * np.exp(-th * 1.3)
    hit += 0.3 * rng.normal(0, 1, k.sum()) * np.exp(-th * 20)
    out[k] += hit

    # タイプ音：キーボードの構造から組み立てる（tools/make_audio.py の keystroke() を参照）
    parts = [EP["no"], f"■ {EP['word']}（{EP['kana']}）", EP["pos"], EP["def"]]
    line_starts, j = set(), 0
    for p in parts:
        line_starts.add(j)
        j += len(p)
    for j in range(card_chars()):
        t0 = T["card"] + j * T["typeStep"]
        if j in line_starts and j > 0:                               # 行が変わる＝Enter（文字の直前に押す）
            place(out, keystroke(rng, big=True), t0 - rng.uniform(0.05, 0.07), n)
        place(out, keystroke(rng), t0 + rng.uniform(0.0, 0.012), n)  # 人の打鍵らしく、わずかに遅れる

    out = out / max(1e-9, np.abs(out).max()) * 0.85  # 音割れしないよう、最大音量を0.85にそろえる
    path = ROOT / "build" / f"opening_audio_ep{ep_no}.wav"
    path.parent.mkdir(exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out * 32000).astype(np.int16).tobytes())
    print(path)


if __name__ == "__main__":
    main()
