"""各話の見せ場の素材（tools/make_set_pieces.py）で使う、音と絵の共通の道具。

音：48kHz モノラル。合成の音色は、鳴っている物の構造から組み立てる（README「わかったこと」）。
  - 澄んだ音（サイン波）は「可愛い」か「気持ち悪い」になりやすいので、雑音を帯域で絞って作るのを基本にする
  - 響きは短い残響の畳み込みで足す（数ミリ秒のこだまは金属的なうねりになるので使わない）
絵：STYLE.md の書体と色だけを使う。文字の下に四角い地は敷かず、文字の形に沿ったぼんやりした影を敷く。
"""
import subprocess
import wave
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.signal import butter, fftconvolve, sosfilt

ROOT = Path(__file__).resolve().parent.parent
# 学習済みモデル（Depth-Anything V2 small = da.onnx、rembg の u2net.onnx）の置き場。scratchpad が消えても困らないよう build/models を既定にし、
# $CCFOLIA_MODELS で変えられる。da.onnx だけは $DEPTH_ONNX でも直接指せる
MODELS = Path(os.environ.get("CCFOLIA_MODELS", ROOT / "build" / "models"))
DEPTH_ONNX = Path(os.environ.get("DEPTH_ONNX", MODELS / "da.onnx"))
U2NET_ONNX = MODELS / "u2net.onnx"
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
    rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    print(f"{rel}  {len(x) / SR:6.1f}秒  {path.stat().st_size / 1024:6.0f}KB")


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


def _zero_clear(im):
    if im.mode != "RGBA":
        return im
    a = np.asarray(im).copy()
    a[a[..., 3] == 0] = 0
    return Image.fromarray(a, "RGBA")


def save_webp_anim(frames, path, fps=30, lossless=True, quality=80, loop=1):
    """アニメーション WebP。loop=1 で1回だけ再生（ココフォリアの1回再生の素材）、0 でずっとループ"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    dur = [int(round(1000 * (i + 1) / fps)) - int(round(1000 * i / fps)) for i in range(len(frames))]   # 33/34ms を混ぜて合計を保つ
    kw = dict(lossless=True) if lossless else dict(quality=quality)
    frames = [_zero_clear(f) for f in frames]                   # alpha 0 の所は RGB も 0（exact で、エンコーダに色を作らせない）
    kw["exact"] = True
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=dur, loop=loop,
                   minimize_size=True, **kw)
    rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    print(f"{rel}  {len(frames)}コマ  {path.stat().st_size / 1024 / 1024:5.2f}MB")


# ---------------------------------------------------------------- 合成（VFX-STUDY.local.md）
# 「貼り絵」に見えないための道具。背景と前景を、同じ光・同じ粒子・同じカメラに通す。

def depth_map(img, onnx_path, size=518):
    """Depth-Anything V2（ONNX, GitHub releases の fabio-sim/Depth-Anything-ONNX）で奥行き。
    戻り値は 0（奥）〜1（手前）の float32、img と同じ大きさ。onnxruntime だけで動く"""
    import onnxruntime as ort
    W, H = img.size
    x = np.asarray(img.convert("RGB").resize((size, size), Image.BICUBIC), np.float32) / 255
    x = (x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    x = x.transpose(2, 0, 1)[None].astype(np.float32)
    s = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    d = s.run(None, {s.get_inputs()[0].name: x})[0][0]
    d = (d - d.min()) / (np.ptp(d) + 1e-6)
    return np.asarray(Image.fromarray(d.astype(np.float32)).resize((W, H), Image.BICUBIC), np.float32)


def parallax_frame(img_arr, depth, t, push=0.06, drift=(10.0, 4.0), near_gain=1.0, center=None):
    """奥行きで画素をずらす 2.5D カメラ。t=0..1。push は奥への寄り（手前ほど大きく拡大）、
    drift は手前の横揺れ px。center (x, y) は寄る先（既定は画面の真ん中やや上）。逆写像（背景から引く）なので穴が開かず、端は複製で埋まる"""
    from scipy.ndimage import map_coordinates
    H, W = depth.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = center if center is not None else (W / 2, H * 0.45)
    z = 1 + push * t * (0.35 + near_gain * depth)
    dx = drift[0] * np.sin(t * np.pi) * depth
    dy = drift[1] * np.sin(t * np.pi * 0.5) * depth
    sx = cx + (xx - cx) / z - dx
    sy = cy + (yy - cy) / z - dy
    out = np.empty_like(img_arr)
    for c in range(img_arr.shape[2]):
        out[..., c] = map_coordinates(img_arr[..., c], [sy, sx], order=1, mode="nearest")
    return out


def integrate(bg, fg_rgb, alpha, depth_at=0.5, haze=(70, 52, 40), haze_amt=0.35,
              wrap_px=10, wrap_amt=0.45, soften=1.2, ao_amt=0.5, ao_y=None):
    """前景（人物など）を背景の「中」に置く。全部 float32 0..1、H×W×3 / H×W。
    1. 縁をぼかす（AIの切り抜きの硬い縁は一番の貼り絵感）
    2. 背景の明るさで前景を染める（色合わせ：背景のぼかしを掛け合わせる）
    3. ライトラップ：背景の光が縁に回り込む
    4. 空気遠近：奥行きぶん霞の色へ寄せる
    5. 接地の影（足元の AO）"""
    from scipy.ndimage import gaussian_filter
    a = gaussian_filter(alpha, soften)
    blur_bg = np.stack([gaussian_filter(bg[..., c], 40) for c in range(3)], -1)
    lum = blur_bg.mean(-1, keepdims=True)
    fg = fg_rgb * (0.35 + 1.3 * lum) * (blur_bg / (lum + 1e-4)) ** 0.6
    edge = np.clip(gaussian_filter(1 - a, wrap_px) * a, 0, 1)[..., None]
    fg = fg + blur_bg * edge * wrap_amt * 2
    fg = fg * (1 - haze_amt * (1 - depth_at)) + np.array(haze, np.float32) / 255 * haze_amt * (1 - depth_at)
    out = bg.copy()
    if ao_y is not None:
        H, W = alpha.shape
        cols = alpha.max(0)
        xs = np.where(cols > 0.5)[0]
        if len(xs):
            ao = np.zeros_like(alpha)
            ao[int(ao_y):int(ao_y) + 6, xs.min():xs.max()] = 1
            ao = gaussian_filter(ao, (4, (xs.max() - xs.min()) * 0.25))
            out = out * (1 - ao_amt * np.clip(ao / (ao.max() + 1e-6), 0, 1))[..., None]
    return out * (1 - a[..., None]) + fg * a[..., None]


def film_finish(frames, seed=0, grain=0.05, weave=0.8, vignette=0.45, breathe=0.06,
                flicker=0.04, dust=0.0, tone=(1.0, 0.86, 0.70)):
    """場面全体を一本のフィルムに通す：粒子・ゲートの揺れ・周辺減光の呼吸・露光ゆらぎ・ゴミ。
    前景も背景も同じ処理を通すことが「同じ画に住んでいる」感の大半。frames は float32 0..1 のリスト"""
    from scipy.ndimage import gaussian_filter, shift
    r = np.random.default_rng(seed)
    H, W = frames[0].shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    rr = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
    n = len(frames)
    flick = gaussian_filter(r.normal(0, 1, n * 3), 1.5)[:n]
    out = []
    for i, f in enumerate(frames):
        ph = 2 * np.pi * i / n                      # ループで継ぎ目が出ない周期
        g = f
        if weave:
            g = shift(g, (weave * np.sin(ph * 3 + r.normal(0, .3)), weave * 0.5 * r.normal(), 0), order=1, mode="nearest")
        v = 1 - (vignette + breathe * np.sin(ph)) * rr
        g = g * np.clip(v, 0, 1)[..., None] * (1 + flicker * flick[i] / (np.abs(flick).max() + 1e-6))
        gn = gaussian_filter(r.normal(0, 1, (H, W)), 0.7)
        lum = g.mean(-1, keepdims=True)
        g = g + grain * gn[..., None] * (0.4 + lum) * 1.6     # 明るい所にもしっかり乗る銀塩寄りの粒子
        if dust and r.random() < dust:
            for _ in range(r.integers(1, 4)):
                y, x = r.integers(0, H), r.integers(0, W)
                rad = r.uniform(1, 3)
                g = g * (1 - 0.6 * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * rad ** 2)))[..., None]
        g = g.mean(-1, keepdims=True) * np.array(tone, np.float32) * 0.4 + g * 0.6
        out.append(np.clip(g, 0, 1))
    return out


def fall_blur(fg_rgba, dy, steps=12):
    """落下する物体の縦モーションブラー（シャッター開角180°相当＝1コマ移動量の半分）。
    fg_rgba: H×W×4 float、dy: このコマの移動量 px。プリマルチで足すので縁が汚れない"""
    from scipy.ndimage import shift
    pm = fg_rgba.copy()
    pm[..., :3] *= pm[..., 3:]
    acc = np.zeros_like(pm)
    L = max(1, int(abs(dy) * 0.5))
    k = min(steps, L)
    for j in range(k):
        acc += shift(pm, (L * j / max(k - 1, 1), 0, 0), order=1, mode="constant")
    acc /= k
    a = acc[..., 3:]
    acc[..., :3] = np.where(a > 1e-4, acc[..., :3] / np.maximum(a, 1e-4), 0)
    return acc


# ---------------------------------------------------------------- 合成の下ごしらえ（VFX の適用：make_set_pieces から使う）

def plate_depth(path, onnx=None):
    """背景の絵の奥行き（0=奥〜1=手前）。一度計算したら build/cache に置く。
    モデルは DEPTH_ONNX（$DEPTH_ONNX か $CCFOLIA_MODELS/da.onnx、既定 build/models/da.onnx）（Depth-Anything V2 small）。無ければ「下ほど手前」で代用"""
    import hashlib
    import os
    path = Path(path)
    cache = ROOT / "build" / "cache" / f"depth_{hashlib.sha256(path.read_bytes()).hexdigest()[:16]}.npy"
    if cache.exists():
        return np.load(cache)
    img = Image.open(path).convert("RGB")
    onnx = Path(onnx or DEPTH_ONNX)
    if onnx.exists():
        d = depth_map(img, onnx)
        lo, hi = np.percentile(d, (1, 99))                           # 外れ値（カーテンの縁など）を切る
        d = np.clip((d - lo) / (hi - lo + 1e-6), 0, 1).astype(np.float32)
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.save(cache, d)
        return d
    return np.repeat(np.linspace(0, 1, img.height, dtype=np.float32)[:, None], img.width, 1)


def grain_tex(h, w, seed=0, sigma=0.7):
    """背景の AI 絵の細かい質感に合わせる粒子（平均 0・標準偏差 1）。前景に焼き込むと背景と同じ紙に見える"""
    from scipy.ndimage import gaussian_filter
    g = gaussian_filter(np.random.default_rng(seed).normal(0, 1, (h, w)), sigma)
    return (g / (g.std() + 1e-6)).astype(np.float32)


def quad_warp(src, quad, size):
    """src（PIL）を、出力 size の中の四角形 quad（左上・右上・右下・左下）に貼る（コーナーピン）。外は透明"""
    w, h = src.size
    A, B = [], []
    for (x, y), (u, v) in zip(quad, [(0, 0), (w, 0), (w, h), (0, h)]):
        A += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
        B += [u, v]
    coef = np.linalg.solve(np.array(A, float), np.array(B, float))
    return src.convert("RGBA").transform(size, Image.PERSPECTIVE, tuple(coef), Image.BICUBIC)


# ---------------------------------------------------------------- 灯りの物理（QUALITY-AUDIT.local.md）
def filament_lag(dim, fps=30, tau_heat=0.035, tau_cool=0.07):
    """白熱電球の明るさの遅れ。dim（0＝点灯、1＝消灯）の段の並びを、フィラメントの熱の慣性に通す。
    電気が切れても光は一瞬では消えず（冷えるのに数十ミリ秒）、点き直しも少し遅れて立ち上がる。
    小さな燭台・シャンデリア球（15〜40W）で、冷える時定数 50〜80ms、温まる時定数 30〜40ms ほど"""
    dim = np.asarray(dim, np.float64)
    out = np.empty_like(dim)
    y = dim[0]
    for i, x in enumerate(dim):
        tau = tau_cool if x > y else tau_heat
        y += (x - y) * (1 - np.exp(-1 / (fps * tau)))
        out[i] = y
    return out


def filament_color(level, warm=(255, 196, 140)):
    """白熱電球の色温度は明るさとともに下がる（暗くなるほど赤い）。level＝0（消灯）〜1（点灯）の光の色"""
    level = float(np.clip(level, 0, 1))
    deep = np.array([255, 110, 40], np.float32)                     # 1000K 前後の、消えかけのフィラメントの色
    return deep + (np.array(warm, np.float32) - deep) * level ** 0.5



def lift_shadows(img, t=0.25, a=1.2):
    """暗いモニタでも形が読めるよう、暗部だけを持ち上げるトーンカーブ。黒（0）は黒のまま、t より明るい所は変えない。
    y = x + a·x·(1 − x/t)²（x < t）。10/255 → 約19/255、t でなめらかにつながる"""
    x = np.asarray(img, np.float32) / 255
    k = np.clip(1 - x / t, 0, 1)
    y = x + a * x * k * k
    return Image.fromarray((np.clip(y, 0, 1) * 255 + 0.5).astype(np.uint8))
