"""オープニングの仮の音を合成する（v3）。秒割りは opening/timing.json を読む。

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


def card_chars():
    # opening/index.html の cardParts と同じ組み立て
    parts = [EP["no"], f"■ {EP['word']}（{EP['kana']}）", EP["pos"], EP["def"]]
    return sum(len(p) for p in parts)


def lowpass(x, k):
    return np.convolve(x, np.ones(k) / k, "same")


def main():
    n = int(T["duration"] * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(1)
    out = np.zeros(n)
    cut = T["cut"]

    # 唸り：低い2音＋ごろごろした雑音。カットで突然消える
    drone = 0.22 * np.sin(2 * np.pi * 55 * t) + 0.10 * np.sin(2 * np.pi * 110.7 * t)
    drone += lowpass(rng.normal(0, 1, n), 400) * 2.0
    drone += 0.016 * np.sin(2 * np.pi * 6400 * t) * np.clip((t - 2.0) / 4, 0, 1)
    a0, a1 = T["droneIn"]
    out += drone * np.clip((t - a0) / (a1 - a0), 0, 1) * (t < cut)

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
