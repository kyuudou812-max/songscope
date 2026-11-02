"""各話の見せ場の素材（tools/make_set_pieces.py）で使う、音と絵の共通の道具。

音：48kHz モノラル。合成の音色は、鳴っている物の構造から組み立てる（README「わかったこと」）。
  - 澄んだ音（サイン波）は「可愛い」か「気持ち悪い」になりやすいので、雑音を帯域で絞って作るのを基本にする
  - 響きは短い残響の畳み込みで足す（数ミリ秒のこだまは金属的なうねりになるので使わない）
絵：STYLE.md の書体と色だけを使う。文字の下に四角い地は敷かず、文字の形に沿ったぼんやりした影を敷く。
"""
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.signal import butter, fftconvolve, sosfilt

ROOT = Path(__file__).resolve().parent.parent
SR = 48000
MINCHO = ROOT / "fonts" / "ShipporiMincho-Medium.ttf"
GOTHIC = ROOT / "fonts" / "ZenKakuGothicNew-Medium.ttf"
# STYLE.md の色
BLACK = (4, 4, 4)
TEXT = (225, 220, 214)        # 文字の白 #e1dcd6
QUIET = (185, 177, 170)       # 控えめな文字 #b9b1aa
QUIETEST = (141, 133, 126)    # いちばん控えめな文字 #8d857e
LAMP = (236, 214, 184)        # 蛍光灯の光 #ecd6b8


# ---------------------------------------------------------------- 音
def rng(seed):
    return np.random.default_rng(seed)


def sec(s):
    return int(round(s * SR))


def silence(s):
    return np.zeros(sec(s), np.float32)


def noise(s, seed=0):
    return rng(seed).normal(0, 1, sec(s)).astype(np.float32)


def filt(x, lo=None, hi=None, order=2):
    if lo and hi:
        sos = butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    elif hi:
        sos = butter(order, hi, btype="low", fs=SR, output="sos")
    else:
        sos = butter(order, lo, btype="high", fs=SR, output="sos")
    return sosfilt(sos, x).astype(np.float32)


def smooth_random(s, rate, seed=0):
    """ゆっくり揺れる 0〜1 の値（rate 回/秒くらいの速さで変わる）"""
    n = sec(s)
    k = max(2, int(s * rate) + 2)
    pts = rng(seed).random(k)
    x = np.interp(np.linspace(0, k - 1, n), np.arange(k), pts)
    w = max(1, int(SR / rate / 4))
    return np.convolve(x, np.ones(w) / w, "same").astype(np.float32)


def reverb(x, size=0.6, wet=0.3, bright=4000, seed=9):
    """短い残響を畳み込む（部屋の大きさ size 秒）"""
    n = sec(size)
    ir = rng(seed).normal(0, 1, n) * np.exp(-np.arange(n) / SR / (size / 6))
    ir = filt(ir.astype(np.float32), hi=bright)
    ir /= np.sqrt((ir ** 2).sum())
    return (x + fftconvolve(x, ir)[: len(x)].astype(np.float32) * wet).astype(np.float32)


def place(out, x, t, gain=1.0):
    """out の t 秒の位置に x を足す（はみ出した分は切る）"""
    s = sec(t)
    if s >= len(out):
        return out
    e = min(len(out), s + len(x))
    out[s:e] += x[: e - s] * gain
    return out


def env(n, attack, decay):
    """立ち上がり attack 秒・減衰 decay 秒（指数）の包絡"""
    t = np.arange(n) / SR
    a = np.minimum(1, t / max(attack, 1e-4))
    return (a * np.exp(-np.maximum(0, t - attack) / max(decay, 1e-4))).astype(np.float32)


def thump(freq=90, decay=0.12, seed=0, s=0.5):
    """重い物が当たる低い音：雑音を低く絞り、短く減衰させる"""
    x = noise(s, seed)
    x = filt(x, hi=freq * 2.5, order=4) * env(len(x), 0.002, decay)
    return x / max(np.abs(x).max(), 1e-6)


def click(lo=1500, hi=6000, decay=0.006, seed=0):
    """硬い部品が当たる短い音"""
    x = filt(noise(0.08, seed), lo, hi) * env(sec(0.08), 0.0005, decay)
    return x / max(np.abs(x).max(), 1e-6)


def resonate(x, freqs, q=40.0):
    """雑音を鋭い共振に通して、物の鳴り（ガラス・金具）を作る。数ミリ秒で消せば音程は目立たない"""
    out = np.zeros_like(x)
    for f in freqs:
        bw = f / q
        out += filt(x, max(20, f - bw), f + bw, order=2)
    return out


def loop_seam(x, xfade=2.0):
    """終わりと頭を重ねて、ループの継ぎ目を消す（長さは xfade 秒短くなる）"""
    n = sec(xfade)
    f = np.linspace(0, 1, n, dtype=np.float32)
    y = x[:-n].copy()
    y[:n] = x[:n] * f + x[-n:] * (1 - f)
    return y


def norm(x, peak=0.8):
    return (x / max(np.abs(x).max(), 1e-6) * peak).astype(np.float32)


def write_mp3(path, x, q=4, stereo=None):
    """mp3（可変ビットレート）で書き出す。stereo に右チャンネルを渡すとステレオ"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".wav")
    ch = 1 if stereo is None else 2
    data = x if stereo is None else np.stack([x, stereo], 1).reshape(-1)
    with wave.open(str(tmp), "wb") as w:
        w.setnchannels(ch), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes((np.clip(data, -1, 1) * 32767).astype("<i2").tobytes())
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(tmp), "-c:a", "libmp3lame", "-q:a", str(q),
                    str(path)], check=True)
    tmp.unlink()
    print(f"{path.relative_to(ROOT)}  {len(x) / SR:6.1f}秒  {path.stat().st_size / 1024:6.0f}KB")


# ---------------------------------------------------------------- 絵
def font(size, gothic=False):
    return ImageFont.truetype(str(GOTHIC if gothic else MINCHO), size)


def halo(img, grow=9, blur=12, strength=1.6):
    """文字の形に沿った、ぼんやりした黒い影を下に敷く"""
    a = img.getchannel("A").filter(ImageFilter.MaxFilter(grow)).filter(ImageFilter.GaussianBlur(blur))
    a = a.point(lambda v: min(255, int(v * strength)))
    sh = Image.new("RGBA", img.size, BLACK + (0,))
    sh.putalpha(a)
    return Image.alpha_composite(sh, img)


def text_line(text, size, color=TEXT, spacing=0.15, pad=40):
    """横書き1行（字間 spacing em）。透明の上に文字だけ"""
    f = font(size)
    widths = [f.getlength(c) for c in text]
    w = int(sum(widths) + size * spacing * (len(text) - 1)) + pad * 2
    h = int(size * 1.5) + pad * 2
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = pad
    for c, cw in zip(text, widths):
        d.text((x, pad), c, font=f, fill=color + (255,))
        x += cw + size * spacing
    return im


def vchar(d, x, y, c, f, size, fill):
    """縦書きの1文字を、幅 size のマスの中に置く（句読点はマスの右上へ）"""
    if c in "。、":
        d.text((x + size * 0.55, y - size * 0.45), c, font=f, fill=fill)
    else:
        w = f.getlength(c)
        d.text((x + (size - w) / 2, y), c, font=f, fill=fill)


def save_webp_anim(frames, path, fps=30, lossless=True, quality=80, loop=1):
    """アニメーション WebP。loop=1 で1回だけ再生（ココフォリアの1回再生の素材）、0 でずっとループ"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    dur = [int(round(1000 * (i + 1) / fps)) - int(round(1000 * i / fps)) for i in range(len(frames))]   # 33/34ms を混ぜて合計を保つ
    kw = dict(lossless=True) if lossless else dict(quality=quality)
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=dur, loop=loop,
                   minimize_size=True, **kw)
    print(f"{path.relative_to(ROOT)}  {len(frames)}コマ  {path.stat().st_size / 1024 / 1024:5.2f}MB")
