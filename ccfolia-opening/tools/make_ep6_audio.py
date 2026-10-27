"""第六話（ファミリーレストラン）で流す音を合成する。台詞は ep6-voice.local.json（シナリオ本文を含むため git の対象外）。

声は Open JTalk（pyopenjtalk、オフラインで動く日本語の音声合成）。声は1種類しかないので、高さ・速さ・音の通り道（スマホのスピーカー、
隣の席の距離、耳元）を変えて役を分ける。機械っぽさは「隣の席のスマホから漏れてくる音」の質感で目立たなくなる。

出力（build/ccfolia/ep6_voice/）:
  60_restaurant_loop.mp3  … BGM：昼のファミレスのざわめき（聞き取れない話し声と食器の音。60秒でつながるループ）
  61_ads.mp3              … 隣の席の動画の広告3本（スマホのスピーカー越し）
  62_news.mp3             … 《聞き耳》成功：犯罪考察チャンネル（名前は放送禁止音で伏せる）
  63_cocktail.mp3         … カクテルパーティー効果の解説
  64_fragments.mp3        … ばらばらの会話の断片 → 『聞こえ』『てる』『わたしは』が別々の声でつながる
  65_nee.mp3              … 『ねえ』×3（だんだん近く、だんだん一つの声に）
  66_kikoetane.mp3        … 《POW*4》失敗：すぐ近くで『聞こえたね』
  67_sugu.mp3             … 『ここまで聞こえているならもう』『すぐ近くに』（雑踏から一つの声が抜け出す）
  68_arigatou.mp3         … 《POW*3》失敗：耳元のささやき「ありがとう、ここまで来られたよ」

使い方: pip install pyopenjtalk scipy; python3 tools/make_ep6_audio.py
"""
import json
import subprocess
import wave
from pathlib import Path

import numpy as np
import pyopenjtalk
from scipy.signal import butter, fftconvolve, resample_poly, sosfilt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "ccfolia" / "ep6_voice"
SR = 48000
LINES = json.loads((ROOT / "ep6-voice.local.json").read_text(encoding="utf-8"))
RNG = np.random.default_rng(6)

# 役 → (声の高さ（半音）, 速さ)
VOICES = {
    "beauty": (5, 0.88), "child": (10, 1.15), "mom": (5, 1.2), "announcer": (0, 1.3), "chant": (7, 1.25),
    "beer": (1, 1.25), "beer2": (6, 1.1), "news": (-1, 1.0), "explainer": (4, 1.05),
    "guy": (-2, 1.0), "guy2": (-3, 0.95), "streamer": (3, 1.35), "streamer2": (1, 1.4), "old": (-4, 0.85),
    "girl": (7, 1.0), "it": (3, 0.82),
}


def tts(text, voice):
    tone, speed = VOICES[voice]
    x, sr = pyopenjtalk.tts(text, half_tone=tone, speed=speed)
    x = np.asarray(x, np.float32) / 32768.0
    if sr != SR:
        x = resample_poly(x, SR, sr).astype(np.float32)
    return x


def filt(x, lo=None, hi=None):
    if lo and hi:
        sos = butter(2, [lo, hi], btype="band", fs=SR, output="sos")
    elif hi:
        sos = butter(2, hi, btype="low", fs=SR, output="sos")
    else:
        sos = butter(2, lo, btype="high", fs=SR, output="sos")
    return sosfilt(sos, x).astype(np.float32)


def room(x, size=0.35, wet=0.35):
    """店内の響き（短い残響を畳み込む）"""
    n = int(size * SR)
    ir = RNG.normal(0, 1, n) * np.exp(-np.arange(n) / SR / (size / 5))
    ir = filt(ir.astype(np.float32), hi=3500)
    ir /= np.abs(ir).sum()
    return (x + fftconvolve(x, ir * 6)[: len(x)] * wet).astype(np.float32)


def phone(x):
    """隣の席のスマホのスピーカー：低音と高音がなく、少し割れていて、少し離れている"""
    y = filt(x, 350, 3800)
    y = np.tanh(y * 3) / 3
    return room(filt(y, hi=3200) * 0.9, 0.3, 0.45)


def near(x):
    """すぐ近く：響きが少なく、低音が残る"""
    return room(filt(x, lo=90), 0.2, 0.12)


def whisper(x):
    """耳元のささやき：声の強弱で、息の雑音をなぞる"""
    env = np.convolve(np.abs(x), np.ones(240) / 240, "same")
    breath = filt(RNG.normal(0, 1, len(x)).astype(np.float32), 900, 7000) * env * 3.5
    return (breath * 0.75 + filt(x, lo=150) * 0.35).astype(np.float32)


def gap(sec):
    return np.zeros(int(sec * SR), np.float32)


def beep(sec=0.55):
    t = np.arange(int(sec * SR)) / SR
    return (np.sin(2 * np.pi * 1000 * t) * 0.35 * np.minimum(1, np.minimum(t, sec - t) / 0.01)).astype(np.float32)


def jingle():
    """広告の頭の短い合図（明るい3音。広告らしさだけ出す）"""
    out = []
    for f in (1046, 1318, 1568):
        t = np.arange(int(0.13 * SR)) / SR
        out.append(((np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 14) * 0.25).astype(np.float32))
    return np.concatenate(out)


def cat(parts):
    return np.concatenate([p for p in parts if len(p)])


def norm(x, peak=0.85):
    return (x / max(np.abs(x).max(), 1e-6) * peak).astype(np.float32)


def write(name, x):
    tmp = OUT / (name + ".wav")
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    with wave.open(str(tmp), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR), w.writeframes(pcm)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(tmp), "-c:a", "libmp3lame", "-b:a", "96k",
                    str(OUT / (name + ".mp3"))], check=True)
    tmp.unlink()
    print(f"{name}.mp3  {len(x) / SR:5.1f}秒")


BABBLE = ["それでさ、きのうの話なんだけど", "えー、ほんとに？", "すみません、お水ください", "このあとどうする？",
          "いやいや、それは違うって", "あはは、なにそれ", "ちょっと待って、いま見るから", "うちの子がね",
          "来週の会議の件ですけど", "おいしいね、これ", "ドリンクバー行ってくる", "それって高くない？",
          "ほら、あの店の", "へえ、そうなんだ", "で、結局どうなったの", "いらっしゃいませ", "お待たせいたしました"]


def babble(seconds, density=7, muffle=1400):
    """聞き取れないざわめき：生活の言葉を何人分も重ね、こもらせる"""
    n = int(seconds * SR)
    out = np.zeros(n, np.float32)
    voices = list(VOICES)
    for _ in range(int(seconds * density / 2.2)):
        x = tts(RNG.choice(BABBLE), RNG.choice(voices)) * RNG.uniform(0.25, 0.6)
        s = int(RNG.uniform(-1, seconds) * SR)
        a, b = max(0, s), min(n, s + len(x))
        if b > a:
            out[a:b] += x[a - s:b - s]
    out = filt(out, hi=muffle)
    # 食器の音：短く明るい雑音（音程は付けない）
    for _ in range(int(seconds * 0.7)):
        m = int(RNG.uniform(0.02, 0.06) * SR)
        click = filt(RNG.normal(0, 1, m).astype(np.float32), 2500, 7000) * np.exp(-np.arange(m) / SR / 0.012)
        s = int(RNG.uniform(0, seconds - 0.1) * SR)
        out[s:s + m] += click * RNG.uniform(0.05, 0.15)
    return room(out, 0.5, 0.5)


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # BGM：60秒のざわめき。端を互いに重ねて、ループの継ぎ目を消す
    L, X = 60, 3
    b = babble(L + X)
    fade = np.linspace(0, 1, X * SR, dtype=np.float32)
    loop = b[: L * SR].copy()
    loop[: X * SR] = b[: X * SR] * fade + b[L * SR:] * (1 - fade)
    write("60_restaurant_loop", norm(loop, 0.5))

    # 広告
    parts = [jingle(), gap(0.2)]
    for v, text in LINES["ads"]:
        if v == "_gap":
            parts += [gap(text), jingle(), gap(0.2)]
        else:
            parts += [tts(text, v), gap(0.18)]
    write("61_ads", norm(phone(cat(parts)), 0.8))

    # ニュース：伏せ字は放送禁止音
    parts = []
    for line in LINES["news"]:
        v = line[0]
        for seg in line[1:]:
            parts.append(beep() if seg == "BEEP" else tts(seg, v))
        parts.append(gap(0.4))
    write("62_news", norm(phone(cat(parts)), 0.75))

    parts = []
    for v, text in LINES["cocktail"]:
        parts += [tts(text, v), gap(0.45)]
    write("63_cocktail", norm(phone(cat(parts)), 0.75))

    # 断片：ざわめきの中から、別々の人の声が拾われる。最後の三つは別々の声なのに一つの文になる
    bed = babble(24, density=9)
    out = bed * 0.6
    t = 1.0
    for item in LINES["fragments"]:
        if item[0] == "_patch":
            t += 1.2
            for v, text in item[1:]:
                x = near(tts(text, v)) * 0.9
                s = int(t * SR)
                out[s:s + len(x)] += x[: len(out) - s]
                t += len(x) / SR + 0.05                        # すき間なくつなげる：ちぐはぐなのに一続き
            continue
        v, text = item
        x = phone(tts(text, v)) * RNG.uniform(0.6, 0.9)
        s = int(t * SR)
        out[s:s + len(x)] += x[: len(out) - s]
        t += len(x) / SR * RNG.uniform(0.5, 0.9)                # 少しずつ重なる
    write("64_fragments", norm(out[: int((t + 2.5) * SR)], 0.8))

    # 『ねえ』×3：遠く・ばらばらの声 → 近く・一つの声へ
    bed = babble(9, density=6) * 0.45
    out = bed.copy()
    for k, (v, f) in enumerate((("girl", phone), ("beauty", lambda x: room(x, 0.35, 0.3)), ("it", near))):
        x = f(tts(LINES["nee"][k], v)) * (0.5 + 0.25 * k)
        s = int((1.2 + k * 2.4) * SR)
        out[s:s + len(x)] += x
    write("65_nee", norm(out, 0.8))

    write("66_kikoetane", norm(cat([gap(0.3), near(tts(LINES["kikoetane"], "it")), gap(1.2)]), 0.8))

    # 雑踏から一つの声が抜け出す：一言目はスマホ越しの声と重なり、二言目は「それ」の声だけ
    bed = babble(8, density=8)
    a = tts(LINES["sugu"][0], "it")
    b = tts(LINES["sugu"][1], "it")
    out = bed * np.linspace(0.6, 0.05, len(bed), dtype=np.float32)
    s = int(1.0 * SR)
    out[s:s + len(a)] += phone(a) * 0.5 + near(a) * 0.4
    s2 = s + len(a) + int(0.6 * SR)
    out[s2:s2 + len(b)] += near(b) * 0.9
    write("67_sugu", norm(out[: s2 + len(b) + SR], 0.8))

    # 最後は「」の声：店の音がすべて消え、耳元だけ
    write("68_arigatou", norm(cat([gap(0.6), whisper(tts(LINES["arigatou"], "it")), gap(1.5)]), 0.7))


if __name__ == "__main__":
    main()
