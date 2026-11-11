"""オープニングの秒割り確認用プレビュー（仮の絵・仮の音）を作る。

使い方: python3 make_animatic.py [話数]   例: python3 make_animatic.py 1
出力: build/animatic_ep{N}.mp4

- 背景のドアは仮の絵（本番は ChatGPT 等で作った画像に差し替える）
- 各話の辞書カードの文面は episodes.local.json から読む（シナリオ本文のため git に入れない）
- フォントは fonts/ に置く（Shippori Mincho / Zen Kaku Gothic New、どちらも OFL）
"""
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
BUILD.mkdir(exist_ok=True)
W, H, FPS, DUR = 1280, 720, 24, 15.0
SR = 48000

# ---- 秒割り（案A） ----
T_BG_IN = (2.0, 3.6)      # ドアが暗闇から浮かび上がる
T_TAG = (5.0, 6.4)        # 一文の1行目・2行目が出る時刻
T_CUT = 8.0               # 真っ黒に切り替え、音も消える
T_TITLE = 8.6             # タイトル
T_CARD = 11.0             # 辞書カードのタイプ打ち開始
TYPE_STEP = 0.055         # 1文字あたりの秒数

GAP = (470, 540, 150, 690)  # ドアの隙間（x0, x1, y0, y1）

ep_no = sys.argv[1] if len(sys.argv) > 1 else "1"
EP = json.loads((ROOT / "episodes.local.json").read_text(encoding="utf-8"))[ep_no]

MINCHO = str(ROOT / "fonts" / "ShipporiMincho-Medium.ttf")
GOTHIC = str(ROOT / "fonts" / "ZenKakuGothicNew-Medium.ttf")


def font(path, size):
    return ImageFont.truetype(path, size)


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


# ---------- 仮の背景（半開きのドア） ----------
def placeholder_door():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    wall = 70 + 40 * (1 - yy / H)
    img = np.stack([wall * 1.05, wall * 0.95, wall * 0.9], -1)
    # 表紙に寄せた赤茶の色かぶり（上中央）
    tint = np.exp(-(((xx - 650) / 260) ** 2 + ((yy - 120) / 260) ** 2))
    img[..., 0] += 45 * tint
    img[..., 1] += 10 * tint
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.rectangle([455, 130, 845, 700], fill=(40, 34, 32))           # 枠
    d.rectangle([540, 145, 830, 700], fill=(96, 78, 70))           # 扉
    d.rectangle([548, 153, 822, 690], outline=(80, 64, 58), width=3)
    d.rectangle([GAP[0], GAP[2], GAP[1], GAP[3]], fill=(6, 5, 5))  # 隙間の暗闇
    d.ellipse([556, 395, 576, 415], fill=(150, 140, 130))          # ドアノブ
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    vign = 1 - 0.75 * np.clip(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2, 0, 1)
    arr = (np.array(im, np.float32) * vign[..., None] * 0.85).astype(np.uint8)
    im = Image.fromarray(arr)
    ImageDraw.Draw(im).text((20, 16), "仮の背景", font=font(GOTHIC, 20), fill=(120, 110, 100))
    return im


BG = placeholder_door()
rng = np.random.default_rng(3)
GRAIN = [rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32) for _ in range(6)]


def grain(i, amount):
    g = GRAIN[i % len(GRAIN)]
    return np.kron(g, np.ones((2, 2), np.float32))[..., None] * amount


# ---------- テキスト ----------
TITLE_COLS = ["暗闇の向こうに", "誰も居ない事を", "証明して下さい"]


def draw_vertical(d, x, y, text, f, fill, pitch):
    for k, ch in enumerate(text):
        d.text((x, y + k * pitch), ch, font=f, fill=fill, anchor="mt")


def card_lines():
    head = f"■ {EP['word']}（{EP['kana']}）"
    d = EP["def"]
    wrap = [d[k:k + 17] for k in range(0, len(d), 17)]
    return [(EP["no"], 22, 210), (head, 34, 255), (EP["pos"], 22, 315)] + \
           [(ln, 24, 365 + 40 * n) for n, ln in enumerate(wrap)]


CARD = card_lines()
CARD_CHARS = sum(len(t) for t, _, _ in CARD)
TYPE_TIMES = [T_CARD + k * TYPE_STEP for k in range(CARD_CHARS)]


def frame(i):
    t = i / FPS
    if t < T_CUT:
        a = ease((t - T_BG_IN[0]) / (T_BG_IN[1] - T_BG_IN[0]))
        arr = np.array(BG, np.float32) * a
        # 隙間の暗闇にだけ、ざらつきを強める（目が何かを探し始める）
        x0, x1, y0, y1 = GAP
        noise = rng.normal(0, 1, (y1 - y0, x1 - x0)).astype(np.float32)
        noise = np.array(Image.fromarray(((noise + 3) * 40).clip(0, 255).astype(np.uint8))
                         .filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 40 - 3
        arr[y0:y1, x0:x1] += noise[..., None] * 5 * a
        img = Image.fromarray(np.clip(arr + grain(i, 6), 0, 255).astype(np.uint8)).convert("RGBA")
        d = ImageDraw.Draw(img)
        for n, line in enumerate(["それはどこにでも存在し、", "見つめれば形を成そうとする。"]):
            la = ease((t - T_TAG[n]) / 0.9)
            if la > 0:
                d.text((W // 2, 612 + 44 * n), line, font=font(MINCHO, 28),
                       fill=(222, 216, 210, int(255 * la)), anchor="mm")
        return img.convert("RGB")

    # 切り替え後：黒地にタイトルと辞書カード
    img = Image.fromarray(np.clip(grain(i, 4) + 4, 0, 255).astype(np.uint8).repeat(3, 2)).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ta = ease((t - T_TITLE) / 1.4)
    if ta > 0:
        col = (238, 236, 232, int(255 * ta))
        draw_vertical(d, 1010, 150, "クトゥルフ神話TRPG", font(GOTHIC, 20), col, 26)
        for k, text in enumerate(TITLE_COLS):
            draw_vertical(d, 940 - k * 78, 140, text, font(GOTHIC, 58), col, 64)
    shown = sum(1 for tt in TYPE_TIMES if tt <= t)
    left = shown
    for text, size, y in CARD:
        part = text[:max(0, left)]
        left -= len(text)
        if part:
            d.text((110, y), part, font=font(MINCHO, size), fill=(225, 220, 214, 255))
    blur = 0 if ta >= 1 else 2.5 * (1 - ta)
    if blur:
        layer = layer.filter(ImageFilter.GaussianBlur(blur))
    return Image.alpha_composite(img, layer).convert("RGB")


# ---------- 仮の音 ----------
def audio():
    n = int(DUR * SR)
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    # 耳鳴りのような低い唸り（0〜8秒、切り替えで突然消える）
    drone = 0.22 * np.sin(2 * np.pi * 55 * t) + 0.10 * np.sin(2 * np.pi * 110.7 * t)
    rumble = np.convolve(np.random.default_rng(1).normal(0, 1, n), np.ones(400) / 400, "same") * 2.0
    whine = 0.018 * np.sin(2 * np.pi * 6400 * t) * np.clip((t - 3) / 4, 0, 1)
    env = np.clip(t / 2.0, 0, 1) * (t < T_CUT)
    out += (drone + rumble + whine) * env
    # タイトルの低い一撃
    k = t >= T_TITLE
    tt = t[k] - T_TITLE
    hit = 0.9 * np.sin(2 * np.pi * (48 - 10 * tt) * tt) * np.exp(-tt * 2.2)
    hit += 0.25 * np.random.default_rng(2).normal(0, 1, k.sum()) * np.exp(-tt * 18)
    out[k] += hit
    # タイプ音
    click = np.random.default_rng(4).normal(0, 1, int(0.012 * SR)) * np.exp(-np.linspace(0, 6, int(0.012 * SR)))
    click = np.diff(click, prepend=0) * 0.35
    for tt in TYPE_TIMES:
        s = int(tt * SR)
        out[s:s + len(click)] += click[: n - s]
    out = np.clip(out, -1, 1)
    path = BUILD / "animatic_audio.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out * 32000).astype(np.int16).tobytes())
    return path


def main():
    wav = audio()
    out = BUILD / f"animatic_ep{ep_no}.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(wav),
                          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                          "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)], stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        p.stdin.write(frame(i).tobytes())
    p.stdin.close()
    p.wait()
    print(out)


if __name__ == "__main__":
    main()
