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
    # 音と映像を合わせる時刻はコマの区切り（1/fps秒）に置く。opening/index.html と同じ丸め方
    return np.floor(x * T["fps"] + 0.5) / T["fps"]


def card_chars():
    # opening/index.html の cardParts と同じ組み立て
    parts = [EP["no"], f"■ {EP['word']}（{EP['kana']}）", EP["pos"], EP["def"]]
    return sum(len(p) for p in parts)


def lowpass(x, k):
    return np.convolve(x, np.ones(k) / k, "same")


def bandnoise(rng, length, lo, hi, decay):
    """帯域を絞った雑音を、指数的に減衰させる（自然な「当たり」の素材）"""
    from scipy.signal import butter, sosfilt
    sos = butter(2, [lo, hi], btype="band", fs=SR, output="sos")
    tt = np.arange(length) / SR
    return sosfilt(sos, rng.normal(0, 1, length)) * np.exp(-tt * decay)


def ring(rng, length, freqs, q, decay):
    """鉄の本体の短い余韻：雑音を鋭い共振フィルターに通す（澄んだ音を足すより自然な金属の響きになる）"""
    from scipy.signal import iirpeak, lfilter
    tt = np.arange(length) / SR
    exc = rng.normal(0, 1, length) * np.exp(-tt * 3000)
    out = np.zeros(length)
    for f in freqs:
        bb, aa = iirpeak(f, q, fs=SR)
        out += lfilter(bb, aa, exc)
    return out * np.exp(-tt * decay)


def typewriter_strike(rng):
    """古い手動タイプライターの1打（構造から組み立てる）：
    ①活字が紙越しにゴムの胴（プラテン）を叩く「タッ」：乾いた高めの当たり＋ゴムの厚み（主役）
    ②鉄の本体の短い金属の余韻
    （構造上は③紙送りの「チッ」④活字の腕の戻りもあるが、音の密度が上がりすぎるので鳴らさない）
    澄んだ音（サイン波）や短い遅れのこだまは使わない（人工的・金属的なうねりになって気持ち悪く聞こえるため）"""
    L = int(0.16 * SR)
    out = np.zeros(L)
    force = rng.uniform(0.75, 1.0)
    slap = bandnoise(rng, int(0.02 * SR), 1500, 5500, rng.uniform(600, 900)) * 1.0
    platen = bandnoise(rng, int(0.03 * SR), 250, 900, rng.uniform(160, 240)) * 0.55
    body = ring(rng, int(0.06 * SR), [rng.uniform(900, 1300), rng.uniform(1700, 2300), rng.uniform(2600, 3300)],
                rng.uniform(25, 40), rng.uniform(70, 110)) * 0.035
    for sig in (slap, platen, body):
        out[:len(sig)] += sig * force
    # ③紙送りの爪 ④活字の腕の戻り は入れない（聞き比べで決定）。
    # 1文字に小さな音が3つ鳴ると1秒に約36回になり、虫がうごめくような気持ち悪さになったため
    return out


def typewriter_linefeed(rng):
    """行が変わる：紙を1行送るラチェットの「カラカラ」（3〜4回）＋台が滑る短い音"""
    L = int(0.3 * SR)
    out = np.zeros(L)
    t = 0.0
    for _ in range(int(rng.integers(3, 5))):
        k = int(t * SR)
        c = bandnoise(rng, int(0.012 * SR), 1800, 6000, 700) * rng.uniform(0.35, 0.5)
        out[k:k + len(c)] += c
        t += rng.uniform(0.018, 0.028)
    k = int(t * SR)
    slide = bandnoise(rng, int(0.15 * SR), 500, 2000, 18)
    slide *= np.clip(np.arange(len(slide)) / (0.03 * SR), 0, 1) * 0.12
    out[k:k + len(slide)] += slide[: L - k]
    return out


def room(sig, rng):
    """静かな小部屋の響き：短く減衰するこもった雑音を畳み込む（こだまの繰り返しにしない）"""
    from scipy.signal import fftconvolve
    ir_len = int(0.18 * SR)
    ir = np.convolve(rng.normal(0, 1, ir_len), np.ones(8) / 8, "same") * np.exp(-np.arange(ir_len) / SR * 28)
    ir /= np.abs(ir).sum()
    wet = fftconvolve(sig, ir)[: len(sig)]
    return sig + wet * 2.5


def place(out, sig, t0, n):
    s0 = int(t0 * SR)
    if 0 <= s0 < n:
        out[s0:s0 + len(sig)] += sig[: n - s0]


def duration():
    # 辞書カードを打ち終わってから2秒は止めて見せる（tools/render_opening.mjs と同じ計算）
    return max(T["duration"], np.ceil((T["card"] + card_chars() * T["typeStep"] + 2.0) * T["fps"]) / T["fps"])


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
        a, b = int(f / T["fps"] * SR), int((f + 1) / T["fps"] * SR)
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

    # タイプ音：古い手動タイプライターの「タッ」を1文字に1つだけ（聞き比べでB案に決定）
    parts = [EP["no"], f"■ {EP['word']}（{EP['kana']}）", EP["pos"], EP["def"]]
    line_starts, j = set(), 0
    for p in parts:
        line_starts.add(j)
        j += len(p)
    typing = np.zeros(n)
    for j in range(card_chars()):
        t0 = T["card"] + j * T["typeStep"]
        place(typing, typewriter_strike(rng), t0 + rng.uniform(0.0, 0.010), n)  # 人の打鍵らしく、わずかに遅れる
    out += room(typing, rng) * 1.1

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
