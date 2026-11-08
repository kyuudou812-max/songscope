"""ChatGPT の差分の絵（tools/finish_images.py が書き出す）を、ただの差し替えでなく「演出」にする前景を書き出す。

使い方: python3 tools/make_diff_fx.py [ground|door|items|gaze ...]（省略で全部）

出力（build/ccfolia/fx/）:
  ep2/24_iridescent_ground_loop.webp … 第2話 玉虫色の地面：地面だけがゆっくりうねり、玉虫色の照りが流れる（前景、ずっとループ）。
                                       色（緑・紫・金の照り）は地面の上だけ（STYLE の例外として決めたもの）
  ep1/15_gap_shadow_loop.webp        … 第1話 ドア：隙間の光の中を、影が横切ってはまた消える（前景、ずっとループ。背景は door_a）
  ep4/45_blink_items.webp            … 第4話 遺留品：まばたき。閉じている間にシーンが切り替わり、開くと遺留品がある（前景、1回再生）
  ep6/63_gaze_flash.webp             … 第6話 全員の視線：1秒だけ、わずかに寄りながら映り、切れる（前景、1回再生）
  preview/*.mp4・*_strip.jpg          … 確認用

考え方（VFX-STUDY.local.md）: 動かす部分だけを前景にし、背景と同じ絵の画素から作る（貼り絵に見えない）。
地面の範囲は fxlib.plate_depth の奥行きが「下に行くほど手前になる」ところ（床の面）で決める。ループは全ての動きを周期の整数倍にして継ぎ目をなくす。
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageSequence
from scipy.ndimage import gaussian_filter, map_coordinates

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fxlib import ROOT, grain_tex, plate_depth, save_webp_anim  # noqa: E402

CC = ROOT / "build" / "ccfolia"
S = CC / "scenes"
OUT = CC / "fx"
PRE = OUT / "preview"


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def arr(p):
    return np.asarray(Image.open(p).convert("RGB").resize((1280, 720)), np.float32) / 255


def rgba(rgb, a):
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 1) * 255, np.clip(a, 0, 1) * 255]).astype(np.uint8), "RGBA")


def check(bg, frames, name, fps, tail=1.0, loops=1, strip_n=8):
    """確認用：背景に前景を重ねた MP4 と、コマを並べた帯（strip）"""
    if isinstance(frames, (str, Path)):
        im = Image.open(frames)
        frames, durs = [], []
        for f in ImageSequence.Iterator(im):
            frames.append(f.convert("RGBA"))
            durs.append(f.info.get("duration", 1000 / fps))
    else:
        durs = [1000 / fps] * len(frames)
    base = Image.open(bg).convert("RGBA").resize((1280, 720))
    PRE.mkdir(parents=True, exist_ok=True)
    seq = []                                               # 30fps に並べ直す（1コマの長さが違う webp も正しく）
    t, k = 0.0, 0
    for _ in range(loops):
        for f, d in zip(frames, durs):
            t += d
            while k * 1000 / 30 < t:
                seq.append(f)
                k += 1
    seq += [None] * int(tail * 30)
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1280x720",
                          "-r", "30", "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                          str(PRE / f"{name}.mp4")], stdin=subprocess.PIPE)
    shots = []
    for f in seq:
        img = base if f is None else Image.alpha_composite(base, f.resize((1280, 720)))
        p.stdin.write(img.convert("RGB").tobytes())
        shots.append(img)
    p.stdin.close()
    p.wait()
    idx = np.linspace(0, len(shots) - 1, strip_n).astype(int)
    strip = Image.new("RGB", (320 * 4, 180 * ((strip_n + 3) // 4)))
    for j, i in enumerate(idx):
        strip.paste(shots[i].convert("RGB").resize((320, 180)), (320 * (j % 4), 180 * (j // 4)))
    strip.save(PRE / f"{name}_strip.jpg", quality=88)
    print(f"preview/{name}.mp4  preview/{name}_strip.jpg")


# ================================================================ 第2話 玉虫色の地面
def ground_mask(path):
    """床の面：奥行きが下へ行くほど手前に増える所（立っている物は縦に奥行きが変わらない）"""
    d = plate_depth(path)
    H, W = d.shape
    gy = gaussian_filter(np.gradient(gaussian_filter(d, 3), axis=0), 4)
    m = smoothstep(0.25, 0.6, gy / np.percentile(gy, 95))
    yy = np.mgrid[0:H, 0:W][0]
    m[H - 40:] = m[H - 40]                                  # 下端は勾配が切れるので延ばす
    m *= smoothstep(H * 0.47, H * 0.56, yy)                 # 地平より上（テントの屋根など）は使わない
    from scipy.ndimage import binary_opening
    m = gaussian_filter(binary_opening(m > 0.5, iterations=4).astype(np.float32), 2.5)
    return m, d


def iridescent_ground(n=60, fps=15):
    src = S / "ep2_03_storage_iridescent.jpg"
    img = arr(src)
    m, d = ground_mask(src)
    H, W = m.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    hz = H * 0.44                                            # 地平線（消失点の高さ）
    zw = 260.0 / np.maximum(yy - hz, 8)                      # 地面の上の奥行き（遠いほど大きい）
    X = (xx - W * 0.52) * zw / 260                          # 地面の上の横位置
    near = np.clip(1 / zw, 0, 1.6)                           # 手前ほど大きく動く
    rg = np.random.default_rng(3)
    noise = gaussian_filter(rg.normal(0, 1, (H, W)), 1.2)
    noise /= noise.std()
    glint_seed = rg.random((H, W)).astype(np.float32)
    glint_mask = (gaussian_filter(rg.normal(0, 1, (H, W)), 0.6) > 1.9).astype(np.float32)
    lum0 = img.mean(-1)
    frames = []
    for i in range(n):
        ph = 2 * np.pi * i / n
        # うねり：地面の座標で進む3つの波（周期の整数倍で戻る）
        a1, a2, a3 = zw * 2.1 - ph + X * 0.6, zw * 1.3 + X * 1.7 + ph * 2, zw * 3.7 - X * 0.9 - ph
        w = np.sin(a1) * 0.55 + np.sin(a2) * 0.3 + np.sin(a3) * 0.15
        # 斜面は地面の座標で（画面の勾配だと遠くほど急になり、照りが地平に固まる）
        slope = (np.cos(a1) * 0.55 * 2.1 + np.cos(a2) * 0.3 * 1.3 + np.cos(a3) * 0.15 * 3.7) * 0.6 \
            + (np.cos(a1) * 0.55 * 0.6 + np.cos(a2) * 0.3 * 1.7 - np.cos(a3) * 0.15 * 0.9) * 0.4
        dy = 2.6 * near * w
        dx = 0.8 * near * np.cos(zw * 1.3 + X * 1.7 + ph * 2)
        g = np.stack([map_coordinates(img[..., c], [yy + dy, xx + dx], order=1, mode="nearest") for c in range(3)], -1)
        shade = 1 + 0.06 * np.clip(slope, -1.5, 1.5) * smoothstep(0.05, 0.5, near)
        g = g * shade[..., None]
        # 玉虫色の照り：斜面の向きと時間で色相が回る。照りは明るい筋の上だけ
        hue = ph + slope * 2.0 + zw * 0.8 + noise * 0.25
        tint = np.stack([0.5 + 0.5 * np.cos(hue), 0.5 + 0.5 * np.cos(hue - 2.1), 0.5 + 0.5 * np.cos(hue + 2.1)], -1)
        tint = tint * np.array([0.78, 1.0, 0.85], np.float32)          # 緑・紫・金に寄せ、赤すぎない
        spec = smoothstep(0.3, 1.1, slope + noise * 0.15) * (0.4 + lum0) * smoothstep(0.08, 0.6, near)
        g = g + (tint - 0.35) * spec[..., None] * 0.17
        # 細かいきらめき（羽の擦れ）：点ごとにずれた位相で瞬く
        tw = np.clip(np.sin(ph * 3 + glint_seed * 2 * np.pi), 0, 1) ** 4 * glint_mask * smoothstep(0.1, 0.9, near) * (0.3 + spec)
        g = g + gaussian_filter(tw, 0.7)[..., None] * (0.25 + 0.6 * tint) * 1.4
        g = g + grain_tex(H, W, seed=100 + i, sigma=0.6)[..., None] * 0.012
        frames.append(rgba(g, m))
    path = OUT / "ep2" / "24_iridescent_ground_loop.webp"
    save_webp_anim(frames, path, fps=fps, lossless=False, quality=50, loop=0)
    check(src, path, "24_iridescent_ground", fps, tail=0, loops=2)


# ================================================================ 第1話 ドアの隙間の影
def gap_shadow(n=72, fps=15):
    """背景は door_a（光だけ）。door_b の隙間の部分だけを前景にし、影が横に流れ、濃くなっては薄れる"""
    a, b = arr(S / "ep1_01_door_a.jpg"), arr(S / "ep1_01_door_b.jpg")
    H, W = a.shape[:2]
    diff = gaussian_filter(np.abs(a - b).mean(-1), 3)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # 隙間の線だけでなく、手前の床に伸びる光の舌（720 まで）も含める：向こうで光が遮られれば、床に落ちる光も同時に暗くなる
    # （以前は 660 で切っていて、隙間が影でふさがっても床の下半分の光が明るいまま残っていた）
    region = ((yy > 570) & (xx > 480) & (xx < 800)).astype(np.float32)
    m = gaussian_filter(smoothstep(0.03, 0.10, diff) * region, 4)
    m = np.clip(m / (m.max() + 1e-6) * 1.4, 0, 1)
    rg = np.random.default_rng(7)
    k = np.fft.rfft(rg.normal(0, 1, n * 4))                  # 周期 n のなめらかな乱数（ループで継ぎ目なし）
    k[6:] = 0
    vis = np.fft.irfft(k, n * 4)[::4]
    vis = smoothstep(-0.45, 0.7, vis / np.abs(vis).max())
    frames = []
    for i in range(n):
        ph = 2 * np.pi * i / n
        sx = 14 * np.sin(ph) + 5 * np.sin(ph * 3 + 1)        # 向こうを何かが行き来する
        # 影は隙間の線の上で横にずれる（光の床への反射も同じだけ）
        bs = np.stack([map_coordinates(b[..., c], [yy, xx - sx], order=1, mode="nearest") for c in range(3)], -1)
        as_ = np.stack([map_coordinates(a[..., c], [yy, xx - sx], order=1, mode="nearest") for c in range(3)], -1)
        # 320px でも「光が影で欠ける」のが読めるよう、door_b の暗くなった分（a−b）を 1.8 倍に強め、出ている間はほぼ不透明に
        bs = np.clip(as_ - np.clip(as_ - bs, 0, 1) * 1.8, 0, 1)
        al = np.clip(m * 1.3, 0, 1) * np.clip(vis[i] * 1.25, 0, 1) * (0.9 + 0.1 * np.sin(ph * 5))
        frames.append(rgba(bs, al))
    path = OUT / "ep1" / "15_gap_shadow_loop.webp"
    save_webp_anim(frames, path, fps=fps, lossless=False, quality=80, loop=0)
    check(S / "ep1_01_door_a.jpg", path, "15_gap_shadow", fps, tail=0, loops=1)


# ================================================================ 第4話 遺留品（まばたきの間に）
def blink_items():
    """シーンを遺留品の絵に切り替えると同時に流す。閉じたまま 0.4 秒（切り替えの瞬間を隠す）→ 半分開いて一度つむる → 開ききる。
    閉じている間に「景色が変わった」ことに、開いた瞬間に気づく"""
    from make_set_pieces import ease_out, lids
    fps = 30
    frames = [lids(0.0)] * int(0.4 * fps)
    n = int(0.25 * fps)
    frames += [lids(0.35 * ease_out((i + 1) / n), feather=0.35) for i in range(n)]
    frames += [lids(0.35 * (1 - (i + 1) / 4)) for i in range(4)]
    frames += [lids(0.0)] * 3
    n = int(0.5 * fps)
    frames += [lids(1.35 * ease_out((i + 1) / n), feather=0.12 + 0.25 * (1 - (i + 1) / n)) for i in range(n)]
    frames.append(Image.new("RGBA", (640, 360), (0, 0, 0, 0)))
    path = OUT / "ep4" / "45_blink_items.webp"
    save_webp_anim(frames, path, fps=fps)
    check(S / "ep4_02_bluesheet_items.jpg", path, "45_blink_items", fps, tail=1.0)


# ================================================================ 第6話 全員の視線（1秒）
def gaze_flash():
    """ファミレスのシーンの上に、こちらを見る全員の絵を1秒だけ。入りも切れもカット。1秒かけて 3% だけ寄る（気づいた瞬間の息をのむ感じ）"""
    src = S / "ep6_01_restaurant_gaze.jpg"
    img = Image.open(src).convert("RGB").resize((1280, 720))
    fps, n = 30, 30
    frames = []
    for i in range(n):
        z = 1 + 0.03 * (1 - (1 - i / (n - 1)) ** 2)
        w, h = 1280 / z, 720 / z
        x0, y0 = (1280 - w) / 2, (720 - h) * 0.42
        frames.append(img.resize((1280, 720), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h)).convert("RGBA"))
    frames.append(Image.new("RGBA", (1280, 720), (0, 0, 0, 0)))
    path = OUT / "ep6" / "63_gaze_flash.webp"
    save_webp_anim(frames, path, fps=fps, lossless=False, quality=82, loop=1)
    check(S / "ep6_01_restaurant.jpg", path, "63_gaze_flash", fps, tail=1.0)


PIECES = {"ground": iridescent_ground, "door": gap_shadow, "items": blink_items, "gaze": gaze_flash}

if __name__ == "__main__":
    for k in sys.argv[1:] or PIECES:
        PIECES[k]()
