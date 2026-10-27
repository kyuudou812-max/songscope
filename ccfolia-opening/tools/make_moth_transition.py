"""第五話「蛾が羽ばたき目の前を通り過ぎた瞬間、まったく別の場所だった」の場面転換を書き出す（手順は scenes.local.md の「蛾の場面転換」）。

ココフォリアでの仕組み（テストA・Bで確かめた性質だけを使う）:
  シーン「第5話 朝・蛾」     … 背景：朝の玄関ドアに止まった蛾（ChatGPT の絵）
  シーン「第5話 夕暮れの廊下」… 背景：夕暮れの団地の廊下
                                前景：この羽ばたき（1回再生。最初のコマは羽で画面が埋まっている）
                                BGM ：「ばさり」＋夕暮れの空気（無音で終わらず、10分続く）
  KP が「ばさり、」と書いた瞬間にシーンを切り替えると、羽が目の前を横切って去り、その向こうに夕暮れの廊下が現れる。
  前景と BGM はシーンの切り替えで同時に始まるので、羽と音はずれない。

出力（build/ccfolia/moth/）:
  52_moth_flap.webp       … 前景（640×360、30fps、約1.6秒、1回再生）
  53_dusk_with_flap.mp3   … BGM（ばさり → 夕暮れの風と遠い踏切。10分）
  preview_moth.mp4        … 確認用（仮の朝の絵 → 切り替え → 夕暮れの廊下）

使い方: python3 tools/make_moth_transition.py [朝の絵.jpg]
"""
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "ccfolia" / "moth"
W, H, FPS, DUR = 640, 360, 30, 1.6
SR = 48000
INK = (26, 16, 12)            # 羽の地：黒に近い焦げ茶（STYLE.md の黒に赤茶を足した色）
SCALE_LIGHT = (196, 170, 140) # 鱗粉・目玉模様：蛍光灯の光を暗くした色


def wing_sprite():
    """蛾を真上から見た形（前翅・後翅・胴）に、ペン画のような線と三つの丸の模様を描いた絵（RGBA）"""
    S = 1400
    mask = Image.new("L", (S, S // 2 + 200), 0)
    d = ImageDraw.Draw(mask)
    cx, cy = S // 2, 330
    for side in (-1, 1):
        fore = [(cx, cy - 20), (cx + side * 200, cy - 230), (cx + side * 520, cy - 250),
                (cx + side * 660, cy - 150), (cx + side * 600, cy + 10), (cx + side * 300, cy + 40)]
        hind = [(cx, cy + 10), (cx + side * 260, cy + 30), (cx + side * 470, cy + 140),
                (cx + side * 420, cy + 300), (cx + side * 180, cy + 330), (cx + side * 40, cy + 200)]
        d.polygon(fore, fill=255)
        d.polygon(hind, fill=255)
    d.ellipse((cx - 38, cy - 120, cx + 38, cy + 300), fill=255)          # 胴
    mask = mask.filter(ImageFilter.GaussianBlur(3))

    rng = np.random.default_rng(11)
    h, w = mask.size[1], mask.size[0]
    tex = np.zeros((h, w, 3), np.float32) + np.array(INK, np.float32)
    # ペン画の線：胴から放射する翅脈と、細かいハッチング
    lines = Image.new("L", (w, h), 0)
    ld = ImageDraw.Draw(lines)
    for side in (-1, 1):
        for k in range(14):
            a = np.deg2rad(-60 + k * 10)                         # 胴から外へ扇形に広がる翅脈
            ld.line((cx, cy, cx + side * np.cos(a) * 700, cy + np.sin(a) * 420), fill=28, width=2)
    for _ in range(2600):
        x, y = rng.integers(0, w), rng.integers(0, h)
        ld.line((x, y, x + rng.integers(6, 18), y + rng.integers(-3, 4)), fill=int(rng.integers(10, 30)), width=1)
    tex += np.asarray(lines, np.float32)[..., None] * np.array([0.9, 0.75, 0.6])
    img = Image.fromarray(np.clip(tex, 0, 255).astype(np.uint8))
    # 三つの丸：前翅に二つ（目）、後翅の合わせ目に一つ（口）。本文の「三つの丸の模様」「顔のようなもの」
    dots = Image.new("L", (w, h), 0)
    dd = ImageDraw.Draw(dots)
    for (x, y, r) in ((cx - 330, cy - 110, 62), (cx + 330, cy - 110, 62), (cx, cy + 190, 50)):
        dd.ellipse((x - r, y - r, x + r, y + r), fill=90)          # 目玉模様は控えめに：輪は鈍く、芯だけ少し明るい
        dd.ellipse((x - r * 0.7, y - r * 0.7, x + r * 0.7, y + r * 0.7), fill=20)
        dd.ellipse((x - r * 0.25, y - r * 0.25, x + r * 0.25, y + r * 0.25), fill=150)
    dots = dots.filter(ImageFilter.GaussianBlur(7))
    img = Image.composite(Image.new("RGB", (w, h), SCALE_LIGHT), img, ImageChops.multiply(dots, mask))
    img.putalpha(mask)
    return img


def ease_in(x):
    return np.clip(x, 0, 1) ** 2.2


def frames():
    """羽が画面を覆った状態から始まり、左上へ払われるように去る。鱗粉が光りながら舞い落ちる"""
    sprite = wing_sprite()
    rng = np.random.default_rng(5)
    dust = [dict(x=rng.uniform(0, W), y=rng.uniform(-20, H * 0.8), vx=rng.uniform(-30, 10), vy=rng.uniform(15, 45),
                 r=rng.uniform(0.6, 1.8), ph=rng.uniform(0, 6.28), born=rng.uniform(0.08, 0.5)) for _ in range(160)]
    n = int(DUR * FPS)
    out = []
    for f in range(n):
        acc = np.zeros((H, W, 4), np.float32)
        sub = 6                                                  # 動きのぶれ：1コマの間を6回に分けて重ねる
        for s in range(sub):
            t = (f + s / sub) / FPS
            k = ease_in((t - 0.05) / 0.5)                        # 0.05秒だけ画面を覆い、0.55秒で去る
            scale = 2.6 - 1.6 * k                                # 目の前を払うので、最初は画面より大きい
            ang = -8 - 38 * k
            cxp = W * 0.5 - k * W * 1.25
            cyp = H * 0.55 - k * H * 1.15
            sw = int(sprite.width * scale * W / 1400)
            sh = int(sprite.height * scale * W / 1400)
            spr = sprite.resize((max(sw, 1), max(sh, 1)), Image.BILINEAR).rotate(ang, expand=True, resample=Image.BILINEAR)
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            layer.alpha_composite(spr, (int(cxp - spr.width / 2), int(cyp - spr.height / 2)) if
                                  -spr.width < cxp - spr.width / 2 < W and -spr.height < cyp - spr.height / 2 < H else (W, H))
            acc += np.asarray(layer, np.float32)
        acc /= sub
        # 鱗粉
        t = f / FPS
        dl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dd = ImageDraw.Draw(dl)
        for p in dust:
            age = t - p["born"]
            if age < 0:
                continue
            a = max(0.0, 1 - age / 1.1) * (0.5 + 0.5 * np.sin(age * 9 + p["ph"]))
            x, y = p["x"] + p["vx"] * age, p["y"] + p["vy"] * age
            dd.ellipse((x - p["r"], y - p["r"], x + p["r"], y + p["r"]), fill=SCALE_LIGHT + (int(200 * a),))
        frame = Image.fromarray(acc.astype(np.uint8), "RGBA")
        # 羽の影：最初の数コマは画面全体を暗く覆い、切り替えの瞬間を隠す
        shade = max(0.0, 1 - t / 0.22) ** 1.5
        if shade > 0:
            frame = Image.alpha_composite(Image.new("RGBA", (W, H), INK + (int(255 * shade),)), frame)
        frame = Image.alpha_composite(frame, dl)
        out.append(frame)
    out[-1] = Image.new("RGBA", (W, H), (0, 0, 0, 0))            # 最後は何も残さない
    return out


def write_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR), w.writeframes(pcm)


def sound(minutes=10):
    """「ばさり」（大きな羽が顔の前を払う、柔らかく重い風切り）＋夕暮れの風と、遠くの踏切"""
    from scipy.signal import butter, sosfilt, fftconvolve
    rng = np.random.default_rng(8)
    n = int(minutes * 60 * SR)
    out = np.zeros(n, np.float32)

    def band(x, lo, hi):
        return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)

    # ばさり：羽の打ち下ろし2回（重い→軽い）。音程のない雑音だけで作る（短い音程は可愛く聞こえるため）
    for t0, amp, length in ((0.00, 1.0, 0.32), (0.11, 0.55, 0.24)):
        m = int(length * SR)
        tt = np.arange(m) / SR
        env = (1 - np.exp(-tt / 0.012)) * np.exp(-tt / (length / 3.2))
        whoosh = band(rng.normal(0, 1, m), 120, 1600) * env * amp
        s = int(t0 * SR)
        out[s:s + m] += whoosh * 0.9
    thump = band(rng.normal(0, 1, int(0.12 * SR)), 50, 160) * np.exp(-np.arange(int(0.12 * SR)) / SR / 0.03)
    out[: len(thump)] += thump * 0.8
    # 鱗粉のかすかなさらさら（ばさりの直後だけ）
    m = int(1.4 * SR)
    out[int(0.15 * SR): int(0.15 * SR) + m] += band(rng.normal(0, 1, m), 3000, 7000) * np.exp(-np.arange(m) / SR / 0.4) * 0.03

    # 夕暮れの空気：低い風（ゆっくり強弱）。ばさりのあとに立ち上がる
    t = np.arange(n) / SR
    wind = band(rng.normal(0, 1, n), 80, 500).astype(np.float32)
    sway = 0.6 + 0.4 * np.sin(2 * np.pi * t / 23) * np.sin(2 * np.pi * t / 7.3)
    out += wind * sway * 0.12 * np.clip((t - 0.4) / 2.5, 0, 1)
    # 遠くの踏切：「カン、カン」と交互に鳴る鐘を、こもらせて小さく。2分おきに十数秒だけ
    bell_len = int(0.35 * SR)
    bt = np.arange(bell_len) / SR
    for start in np.arange(4.0, minutes * 60 - 20, 120.0):
        dur = rng.uniform(12, 18)
        k = 0
        while k * 0.42 < dur:
            f0 = (720, 650)[k % 2]
            ring = sum(a * np.sin(2 * np.pi * f0 * h * bt) for h, a in ((1, 1), (2.76, 0.4), (5.4, 0.15))) * np.exp(-bt * 9)
            fade = min(1, k * 0.42 / 2, (dur - k * 0.42) / 3)
            s = int((start + k * 0.42) * SR)
            out[s:s + bell_len] += ring * 0.035 * fade
            k += 1
    # 遠さ：高い音を削り、短い響きを足す
    out = sosfilt(butter(2, 2400, btype="low", fs=SR, output="sos"), out).astype(np.float32)
    ir = rng.normal(0, 1, int(0.4 * SR)) * np.exp(-np.arange(int(0.4 * SR)) / SR / 0.09)
    head = 20 * SR                                               # 響きは「ばさり」と最初の踏切のところだけ足せば十分
    out[:head] += fftconvolve(out[:head], ir / np.abs(ir).sum() * 3)[:head].astype(np.float32)
    out = out / np.abs(out).max() * 0.8
    return out


def main(morning=None):
    OUT.mkdir(parents=True, exist_ok=True)
    fs = frames()
    tmp = OUT / "frames"
    tmp.mkdir(exist_ok=True)
    for i, im in enumerate(fs):
        im.save(tmp / f"f{i:04d}.png")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", str(tmp / "f%04d.png"),
                    "-c:v", "libwebp_anim", "-lossless", "1", "-loop", "1", str(OUT / "52_moth_flap.webp")], check=True)

    snd = sound()
    write_wav(OUT / "dusk.wav", snd)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(OUT / "dusk.wav"), "-c:a", "libmp3lame",
                    "-b:a", "48k", str(OUT / "53_dusk_with_flap.mp3")], check=True)

    # 確認用：朝の絵（なければ仮）を2秒 → 切り替え → 夕暮れの廊下＋羽ばたき（ココフォリアの重ね方を再現）
    scenes = ROOT / "build" / "ccfolia" / "scenes"
    dusk = Image.open(scenes / "ep5_01_corridor.jpg").convert("RGBA").resize((1280, 720))
    am = Image.open(morning).convert("RGBA").resize((1280, 720)) if morning else \
        Image.open(scenes / "ep3_01_street.jpg").convert("RGBA").resize((1280, 720))
    vid = OUT / "pv"
    vid.mkdir(exist_ok=True)
    k = 0
    for _ in range(int(2.0 * FPS)):
        am.convert("RGB").save(vid / f"v{k:04d}.png"); k += 1
    for i in range(int(4.0 * FPS)):
        fr = dusk.copy()
        if i < len(fs):
            fr.alpha_composite(fs[i].resize((1280, 720), Image.BILINEAR))
        fr.convert("RGB").save(vid / f"v{k:04d}.png"); k += 1
    lead = np.zeros(int(2.0 * SR), np.float32)
    write_wav(OUT / "pv.wav", np.concatenate([lead, snd[: int(4.0 * SR)]]))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", str(vid / "v%04d.png"),
                    "-i", str(OUT / "pv.wav"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                    "-c:a", "aac", "-shortest", str(OUT / "preview_moth.mp4")], check=True)
    for p in ("52_moth_flap.webp", "53_dusk_with_flap.mp3", "preview_moth.mp4"):
        print(p, f"{(OUT / p).stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
