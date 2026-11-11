# VFX-STUDY.local.md の試作（出力は scratchpad/prototypes）。モデルは fxlib.DEPTH_ONNX（既定 build/models/da.onnx）（Depth-Anything V2 small ONNX）
import sys, subprocess, numpy as np
sys.path.insert(0, "/home/user/songscope/ccfolia-opening/tools")
import fxlib as fx
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
S = "/tmp/claude-0/-home-user-songscope/055d0ebe-353c-5b70-98af-84d887ef3993/scratchpad"
P = S + "/prototypes"
bgimg = Image.open("/home/user/songscope/ccfolia-opening/build/ccfolia/scenes/ep8_01_room.jpg").convert("RGB")
bg = np.asarray(bgimg, np.float32) / 255
H, W = bg.shape[:2]
D = fx.depth_map(bgimg, fx.DEPTH_ONNX); np.save(P + "/depth.npy", D)
Image.fromarray((D * 255).astype(np.uint8)).save(P + "/A_depth.png")
def u8(a): return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
def mp4(frames, name, fps=24):
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", f"{P}/{name}.mp4"], stdin=subprocess.PIPE)
    for f in frames: p.stdin.write((np.clip(f, 0, 1) * 255).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait()

def figure_mask(cx, feet, h):
    m = Image.new("L", (W, H), 0); d = ImageDraw.Draw(m)
    hw = h * 0.07; d.ellipse([cx - hw, feet - h, cx + hw, feet - h + hw * 2.4], 255)
    d.polygon([(cx - h*.06, feet - h*.83), (cx + h*.07, feet - h*.83), (cx + h*.11, feet - h*.45),
               (cx + h*.08, feet), (cx - h*.08, feet), (cx - h*.11, feet - h*.45)], 255)
    # 長い髪
    d.polygon([(cx - hw, feet - h*.93), (cx + hw, feet - h*.93), (cx + hw*1.1, feet - h*.6), (cx - hw*1.2, feet - h*.6)], 255)
    return np.asarray(m, np.float32) / 255

# ---- B: 人物の馴染ませ（ドアの前）
a = figure_mask(1115, 468, 330)
fgcol = np.full((H, W, 3), 0.10, np.float32)
naive = bg * (1 - a[..., None]) + fgcol * a[..., None]
good = fx.integrate(bg, fgcol, a, depth_at=float(D[400, 1115]), wrap_px=6, wrap_amt=0.35, soften=1.4, ao_y=462, ao_amt=0.55)
u8(naive).save(P + "/B_figure_naive.png"); u8(good).save(P + "/B_figure_integrated.png")
fin = fx.film_finish([naive, good], seed=3, weave=0)
u8(np.concatenate([fin[0][:, 840:], fin[1][:, 840:]], 1)).save(P + "/B_compare_crop.png")

# ---- A: 奥行きカメラ（12秒、ループ往復）＋人物が少しずつ現れる（Kairo 型：フェードでなく「最初からいた」濃度変化）
N = 24 * 6
frames = []
for i in range(N):
    t = i / (N - 1)
    f = fx.parallax_frame(bg, D, 0.5 - 0.5 * np.cos(np.pi * t), push=0.05, drift=(12, 3))
    frames.append(f)
mp4(fx.film_finish(frames, seed=1), "A_parallax_push")
u8(frames[-1]).save(P + "/A_last_frame.png")

# 人物入り：奥行きカメラに人物を同じ写像で乗せる（人物も plate の一部として動く）
comp = np.concatenate([good, a[..., None]], -1)
frames = []
for i in range(N):
    t = i / (N - 1)
    vis = np.clip((t - 0.25) / 0.6, 0, 1) ** 2      # 気づくと濃くなっている
    plate = bg * (1 - vis) + good * vis
    frames.append(fx.parallax_frame(plate, D, 0.5 - 0.5 * np.cos(np.pi * t), push=0.05, drift=(12, 3)))
fin = fx.film_finish(frames, seed=2, dust=0.15)
mp4(fin, "B_reveal_in_plate"); u8(fin[-1]).save(P + "/B_reveal_last.png")

# ---- C: 窓の外を落ちる人（透過WebP、モーションブラー＋窓枠で切る＋暗く霞む）
win = np.zeros((H, W), np.float32); win[45:440, 205:505] = 1          # 窓ガラス範囲
for x0, x1 in [(258, 280), (466, 484)]: win[:, x0:x1] = 0                 # 窓枠の前に落ちない
win = gaussian_filter(win, 1)
fall = []; NF = 18
for i in range(NF):
    y = -200 + (i / NF) ** 1.6 * 900
    m = figure_mask(370, int(y) + 250, 230)
    rgba = np.concatenate([np.full((H, W, 3), 0.06, np.float32), m[..., None]], -1)
    v = 900 * 1.6 * (i / NF) ** 0.6 / NF
    rgba = fx.fall_blur(rgba, v)
    rgba[..., 3] *= win * 0.85
    fall.append(rgba)
fall += [np.zeros((H, W, 4), np.float32)] * 30
ims = [Image.fromarray((np.clip(f, 0, 1) * 255).astype(np.uint8), "RGBA") for f in fall]
crop = [im.crop((180, 0, 540, 470)) for im in ims]
fx.save_webp_anim(crop, P + "/C_fall_overlay.webp", fps=24, lossless=False, quality=70, loop=0)
pv = []
for f in fall:
    pv.append(bg * (1 - f[..., 3:]) + f[..., :3] * f[..., 3:])
mp4(fx.film_finish(pv, seed=4), "C_fall_preview")
u8(pv[9]).save(P + "/C_fall_frame.png")

# ---- D: 場面全体のフィルム層を透過オーバーレイとして（ココフォリアで全場面に被せる）
NG = 48
ov = []
r = np.random.default_rng(7)
yy, xx = np.mgrid[0:H, 0:W]; rr = ((xx - W/2)/(W/2))**2 + ((yy - H/2)/(H/2))**2
for i in range(NG):
    ph = 2*np.pi*i/NG
    vig = np.clip((0.55 + 0.08*np.sin(ph)) * rr - 0.15, 0, 1)
    g = np.abs(gaussian_filter(r.normal(0, 1, (H, W)), 0.8)) * 0.35
    A = np.clip(vig * 0.85 + g, 0, 1)
    rgba = np.zeros((H, W, 4), np.uint8); rgba[..., :3] = (14, 9, 6); rgba[..., 3] = (A * 255).astype(np.uint8)
    ov.append(Image.fromarray(rgba, "RGBA").resize((640, 360), Image.BILINEAR))
fx.save_webp_anim(ov, P + "/D_film_layer.webp", fps=12, lossless=False, quality=60, loop=0)
