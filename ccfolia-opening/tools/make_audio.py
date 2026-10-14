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


def snap(x):
    # 音と映像を合わせる時刻はコマの区切り（1/24秒）に置く。opening/index.html と同じ丸め方
    return np.floor(x * 24 + 0.5) / 24


def card_chars():
    # opening/index.html の cardParts と同じ組み立て
    parts = [EP["no"], f"■ {EP['word']}（{EP['kana']}）", EP["pos"], EP["def"]]
    return sum(len(p) for p in parts)


def lowpass(x, k):
    return np.convolve(x, np.ones(k) / k, "same")


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
    # 蛍光灯が一瞬暗くなる3コマ：ハム音も同じコマで落ち込み、パチッと鳴る（映像と同じ数値）
    lamp = np.ones(n)
    for ft in ESC["flickers"]:
        for k, dim in enumerate((0.55, 0.2, 0.45)):
            a, b = int((snap(ft) + k / 24) * SR), int((snap(ft) + (k + 1) / 24) * SR)
            lamp[a:b] = 1 - dim
        s0 = int(snap(ft) * SR)
        m = int(0.03 * SR)
        out[s0:s0 + m] += rng.normal(0, 1, m) * np.exp(-np.arange(m) / SR * 160) * 0.25
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

    # タイプ音：1文字に1回。低い「コッ」という芯と、控えめな打鍵の擦れを混ぜる。
    # 毎回少しだけ高さと強さを変え、同じ音の機械的な繰り返しにしない。
    # （以前は雑音の高域だけを使っていたため、エネルギーの85%が6kHz以上に偏り、耳に痛かった）
    key_len = int(0.045 * SR)
    kt = np.arange(key_len) / SR
    for j in range(card_chars()):
        f0 = 260 * (0.9 + 0.2 * rng.random())
        body = np.sin(2 * np.pi * f0 * kt) * np.exp(-kt * 90)
        tick = lowpass(rng.normal(0, 1, key_len), 12) * np.exp(-kt * 400) * 0.6
        key = (body + tick) * 0.16 * (0.75 + 0.25 * rng.random())
        s = int((T["card"] + j * T["typeStep"]) * SR)
        out[s:s + key_len] += key[: max(0, n - s)]

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
