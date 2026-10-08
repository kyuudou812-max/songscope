"""ココフォリア技術検証キットの生成スクリプト。

使い方: python3 make_test_kit.py <出力ディレクトリ>
ffmpeg (libwebp_anim / apng) と Pillow, numpy が必要。
"""
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "test-kit")
OUT.mkdir(parents=True, exist_ok=True)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"


def font(size, mono=False):
    return ImageFont.truetype(MONO if mono else FONT, size)


def render(frames_fn, n, fps, name, kind, *, loop=True, quality=75, w=1280, h=720):
    """frames_fn(i, t) -> PIL RGBA を n 枚描いて webp / apng に書き出す（既にあれば飛ばす）"""
    out = OUT / name
    if out.exists():
        return out
    tmp = Path(tempfile.mkdtemp())
    for i in range(n):
        frames_fn(i, i / fps).save(tmp / f"f{i:04d}.png")
    src = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(tmp / "f%04d.png")]
    if kind == "webp":
        cmd = src + ["-c:v", "libwebp_anim", "-quality", str(quality), "-pix_fmt", "yuva420p",
                     "-loop", "0" if loop else "1", str(out)]
    else:
        cmd = src + ["-c:v", "apng", "-pred", "mixed", "-plays", "0" if loop else "1", "-f", "apng", str(out)]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp)
    return out


# ---------- A: 同期テスト（10秒・24fps・ループ） ----------
W, H, FPS, SEC = 1280, 720, 24, 10
LANES = [("BG", (80, 160, 255)), ("FG", (255, 80, 80)), ("PANEL", (255, 210, 60)), ("CUTIN", (80, 230, 120))]


def sync_layer(idx, opaque):
    label, color = LANES[idx]
    y0 = 40 + idx * 150

    def fn(i, t):
        img = Image.new("RGBA", (W, H), (12, 16, 30, 255) if opaque else (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        if opaque:  # 目盛り（1秒ごと）は背景だけに描く
            for s in range(SEC + 1):
                x = int(s / SEC * (W - 20)) + 10
                d.line([(x, 20), (x, H - 20)], fill=(60, 70, 100, 255), width=2)
                d.text((x + 4, H - 50), f"{s}s", font=font(22), fill=(140, 150, 180, 255))
        x = int(t / SEC * (W - 20)) + 10
        d.rectangle([x - 6, y0, x + 6, y0 + 120], fill=color + (255,))
        d.text((30, y0 + 30), f"{label}  {t:5.2f}s", font=font(48, True), fill=color + (255,))
        if t < 0.25:
            d.rectangle([0, y0, W, y0 + 120], outline=color + (255,), width=8)
        return img
    return fn


for idx, (label, _) in enumerate(LANES):
    render(sync_layer(idx, idx == 0), FPS * SEC, FPS, f"A{idx+1}_sync_{label.lower()}_1280x720_24fps_10s_loop.webp", "webp")
render(sync_layer(1, False), FPS * SEC, FPS, "A2b_sync_fg_1280x720_24fps_10s_loop.apng.png", "apng")

# 1秒ごとにビープ（0秒と5秒は高い音）
beeps = []
for s in range(SEC):
    f = 1760 if s in (0, 5) else 880
    beeps.append(f"sine=f={f}:d=0.08,apad=whole_dur=1")
beep_out = OUT / "A5_sync_beep_every_1s_10s.mp3"
beep_out.exists() or subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-filter_complex",
                ";".join(f"{b}[a{k}]" for k, b in enumerate(beeps)) + ";" +
                "".join(f"[a{k}]" for k in range(SEC)) + f"concat=n={SEC}:v=0:a=1,volume=0.6",
                "-c:a", "libmp3lame", "-b:a", "128k", str(beep_out)], check=True)


# ---------- B: 1回だけ再生（ループなし） ----------
def once(i, t):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    txt = str(3 - int(t)) if t < 3 else "END"
    d.text((W // 2, H // 2), txt, font=font(220), fill=(255, 255, 255, 255), anchor="mm")
    d.text((W // 2, H // 2 + 170), f"ONCE {min(t, 3.0):4.2f}s", font=font(36, True), fill=(255, 255, 255, 200), anchor="mm")
    return img


render(once, FPS * 3 + 1, FPS, "B1_once_countdown_3s_noloop.webp", "webp", loop=False)
render(once, FPS * 3 + 1, FPS, "B2_once_countdown_3s_noloop.apng.png", "apng", loop=False)


# ---------- C: 容量・画質テスト（PROで劣化しないか） ----------
def rich(w, h):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rng = np.random.default_rng(1)
    pts = rng.random((40, 4)) * [w, h, 2 * math.pi, 1]

    def fn(i, t):
        r = 0.5 + 0.5 * np.sin(xx / w * 6 + t * 1.3)
        g = 0.5 + 0.5 * np.sin(yy / h * 5 - t * 0.9)
        b = 0.5 + 0.5 * np.sin((xx + yy) / (w + h) * 8 + t)
        base = np.stack([r * 120 + 20, g * 60 + 10, b * 160 + 30], -1)
        img = Image.fromarray(base.astype(np.uint8)).convert("RGBA")
        d = ImageDraw.Draw(img)
        for px, py, ph, s in pts:
            x = (px + t * 80 * (s + 0.3)) % w
            y = py + 30 * math.sin(t * 2 + ph)
            rad = 6 + 18 * s
            d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=(255, 230, 180, int(120 + 120 * s)))
        d.text((30, 30), f"{w}x{h}  {t:4.2f}s", font=font(40, True), fill=(255, 255, 255, 255))
        return img
    return fn


def size_cases(w, h, targets_mb, qualities):
    """フレームは1回だけ描き、quality を変えて各目標容量に最も近い（超えない）ものを残す"""
    tmp = Path(tempfile.mkdtemp())
    fn = rich(w, h)
    for i in range(FPS * 5):
        fn(i, i / FPS).save(tmp / f"f{i:04d}.png")
    sizes = {}
    if any(OUT.glob(f"C_size_{w}x{h}_*")):
        return
    for q in qualities:
        out = tmp / f"q{q}.webp"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%04d.png"),
                        "-c:v", "libwebp_anim", "-quality", str(q), "-loop", "0", str(out)], check=True)
        sizes[q] = out.stat().st_size / 1e6
    for target in targets_mb:
        fits = [q for q, mb in sizes.items() if mb <= target]
        q = max(fits) if fits else min(sizes)
        shutil.copy(tmp / f"q{q}.webp", OUT / f"C_size_{w}x{h}_q{q}_{sizes[q]:.2f}MB_5s.webp")
    shutil.rmtree(tmp)


size_cases(1280, 720, [0.95, 2.5], [30, 60, 75, 90])
size_cases(1920, 1080, [4.8], [60, 80, 95])


# ---------- D: 半透明（霧）WebP と APNG の比較 ----------
def fog(w, h, sec):
    """半透明の霧。画面全体サイズだと 14〜25MB になったため、小さく作ってココフォリア側で拡大する"""
    rng = np.random.default_rng(7)
    small = rng.random((9, 16)).astype(np.float32)
    layer = np.array(Image.fromarray((small * 255).astype(np.uint8)).resize((w * 2, h), Image.BICUBIC)
                     .filter(ImageFilter.GaussianBlur(w / 32)), dtype=np.float32) / 255

    def fn(i, t):
        off = int((t / sec) * w) % w
        a = np.roll(layer, -off, axis=1)[:, :w]
        alpha = np.clip((a - 0.3) * 1.6, 0, 1) * 170
        rgba = np.zeros((h, w, 4), np.uint8)
        rgba[..., :3] = 210
        rgba[..., 3] = alpha.astype(np.uint8)
        return Image.fromarray(rgba)
    return fn


render(fog(640, 360, 4), 12 * 4, 12, "D1_fog_alpha_640x360_12fps_4s_loop.webp", "webp", w=640, h=360)
render(fog(640, 360, 4), 12 * 4, 12, "D2_fog_alpha_640x360_12fps_4s_loop.apng.png", "apng", w=640, h=360)


# ---------- E: フレームレート比較 ----------
def ball(fps):
    def fn(i, t):
        img = Image.new("RGBA", (W, 240), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        x = 60 + (t / 3) * (W - 120)
        d.ellipse([x - 40, 80, x + 40, 160], fill=(255, 255, 255, 255))
        d.text((20, 10), f"{fps}fps", font=font(40, True), fill=(255, 255, 255, 255))
        return img
    return fn


for f in (12, 24, 30):
    render(ball(f), f * 3, f, f"E_fps{f}_ball_1280x240_3s_loop.webp", "webp", w=W, h=240)

for p in sorted(OUT.iterdir()):
    print(f"{p.stat().st_size/1e6:7.2f} MB  {p.name}")
