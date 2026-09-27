"""バラエティ番組風「ROF-MAOって？」40秒アニメーション（非公式ファンメイド）。

絵・動き・効果音・BGM はすべてこのファイルのコードで作る（外部素材・公式ロゴ・立ち絵は使わない）。
1920x1080 / 30fps の mp4 を書き出す。

使い方:
    python3 rofmao_video.py                          # rofmao_video.mp4 を書き出す
    python3 rofmao_video.py --stills <dir> [秒 ...]  # 確認用の静止画だけ書き出す
"""
import math
import os
import random
import subprocess
import sys
import wave
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG = "ffmpeg"

W, H = 1920, 1080
FPS = 30
DURATION = 40.0
SS = 4  # キャラクターを描くときの拡大率（縮小してなめらかにする）
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
BOLD_FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
REG_FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"


@lru_cache(maxsize=None)
def font(size, bold=True):
    if bold and os.path.exists(BOLD_FONT):
        return ImageFont.truetype(BOLD_FONT, size, index=0)  # index 0 = JP
    return ImageFont.truetype(REG_FONT, size)


OUTLINE = (45, 35, 50)
SKIN = (255, 226, 205)
SKIN_SHADE = (240, 196, 176)

# ---------------------------------------------------------------- メンバー
# 見た目は、公式のユニット画像の特徴（髪・目・服・小物）だけをおさえたオリジナルのデフォルメ
MEMBERS = [
    dict(key="kagami", name="加賀美ハヤト", color=(245, 245, 250), text_color=(255, 255, 255),
         hair=(186, 124, 82), hair_dark=(140, 88, 58), eye=(150, 96, 52),
         top=(246, 246, 250), inner=(35, 35, 40), pants=(150, 150, 160), accent=(215, 70, 60)),
    dict(key="kenmochi", name="剣持刀也", color=(128, 80, 220), text_color=(150, 100, 240),
         hair=(84, 56, 150), hair_dark=(56, 36, 110), eye=(110, 185, 70),
         top=(228, 230, 236), inner=(240, 240, 244), pants=(130, 130, 145), accent=(120, 70, 210)),
    dict(key="fuwa", name="不破湊", color=(225, 60, 170), text_color=(240, 90, 180),
         hair=(222, 222, 234), hair_dark=(170, 170, 190), eye=(150, 90, 200),
         top=(150, 70, 190), inner=(248, 248, 250), pants=(210, 210, 220), accent=(240, 90, 160)),
    dict(key="kaida", name="甲斐田晴", color=(60, 170, 235), text_color=(70, 180, 245),
         hair=(196, 186, 182), hair_dark=(150, 140, 138), eye=(120, 200, 240),
         top=(196, 198, 206), inner=(40, 40, 46), pants=(170, 205, 230), accent=(245, 200, 50)),
]


class Pen:
    """キャラクター用の座標系（200x300 を scale 倍して、さらに SS 倍で描く）"""

    def __init__(self, scale):
        self.k = scale * SS
        self.img = Image.new("RGBA", (int(200 * self.k), int(300 * self.k)), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def p(self, pts):
        return [(x * self.k, y * self.k) for x, y in pts]

    def ellipse(self, cx, cy, rx, ry, fill, outline=OUTLINE, w=3):
        self.d.ellipse([(cx - rx) * self.k, (cy - ry) * self.k, (cx + rx) * self.k, (cy + ry) * self.k],
                       fill=fill, outline=outline, width=int(w * self.k) if outline else 0)

    def poly(self, pts, fill, outline=OUTLINE, w=3):
        pts = self.p(pts)
        self.d.polygon(pts, fill=fill)
        if outline:
            self.d.line(pts + [pts[0]], fill=outline, width=int(w * self.k), joint="curve")

    def rrect(self, x0, y0, x1, y1, r, fill, outline=OUTLINE, w=3):
        self.d.rounded_rectangle([x0 * self.k, y0 * self.k, x1 * self.k, y1 * self.k], radius=r * self.k,
                                 fill=fill, outline=outline, width=int(w * self.k) if outline else 0)

    def line(self, pts, fill=OUTLINE, w=3):
        self.d.line(self.p(pts), fill=fill, width=int(w * self.k), joint="curve")

    def arc(self, cx, cy, rx, ry, a0, a1, fill=OUTLINE, w=3):
        self.d.arc([(cx - rx) * self.k, (cy - ry) * self.k, (cx + rx) * self.k, (cy + ry) * self.k],
                   a0, a1, fill=fill, width=int(w * self.k))

    def done(self):
        return self.img.resize((self.img.width // SS, self.img.height // SS), Image.LANCZOS)


def draw_back_hair(pn, m):
    k = m["key"]
    hc = m["hair"]
    if k == "fuwa":
        # ふわっとはねる髪
        pts = []
        for i in range(19):
            a = math.pi * (0.95 + i / 18 * 1.1)
            r = 80 if i % 2 == 0 else 66
            pts.append((100 + math.cos(a) * r, 92 + math.sin(a) * r * 0.95))
        pts += [(170, 125), (164, 150), (36, 150), (30, 125)]
        pn.poly(pts, hc)
        # ピンクと赤のメッシュ
        pn.poly([(150, 70), (176, 96), (172, 130), (158, 110)], m["accent"], w=2)
        pn.poly([(160, 95), (176, 118), (168, 140), (160, 120)], (220, 50, 80), w=2)
    elif k == "kaida":
        pn.ellipse(100, 92, 74, 72, hc)
        pn.poly([(30, 100), (26, 140), (48, 132)], hc)
        pn.poly([(170, 100), (174, 140), (152, 132)], hc)
    elif k == "kagami":
        pn.ellipse(100, 92, 73, 70, hc)
        # 外はね
        pn.poly([(32, 118), (16, 138), (44, 132)], hc)
        pn.poly([(168, 118), (184, 138), (156, 132)], hc)
    else:  # kenmochi
        pn.ellipse(100, 92, 71, 70, hc)
        pn.poly([(34, 110), (32, 136), (50, 128)], hc)
        pn.poly([(166, 110), (168, 136), (150, 128)], hc)


def draw_bangs(pn, m):
    k = m["key"]
    hc = m["hair"]
    if k == "kagami":
        # センター分け
        pn.poly([(100, 34), (58, 44), (36, 80), (34, 118), (50, 96), (64, 80), (84, 64), (98, 50)], hc)
        pn.poly([(100, 34), (142, 44), (164, 80), (166, 118), (150, 96), (136, 80), (116, 64), (102, 50)], hc)
        pn.line([(100, 34), (100, 52)], m["hair_dark"], 2)
    elif k == "kenmochi":
        # 横に流した前髪
        pn.poly([(40, 60), (70, 34), (120, 30), (160, 50), (168, 92), (150, 70), (120, 78), (96, 70),
                 (70, 92), (52, 84), (38, 104)], hc)
    elif k == "fuwa":
        pn.poly([(36, 66), (60, 38), (100, 30), (140, 38), (166, 66), (164, 100), (150, 78), (140, 100),
                 (126, 72), (112, 96), (100, 70), (86, 94), (76, 70), (62, 98), (48, 78), (36, 102)], hc)
        pn.poly([(126, 72), (140, 100), (150, 78), (144, 64)], m["accent"], w=2)
    else:  # kaida：片目にかかる前髪
        pn.poly([(34, 70), (58, 40), (100, 30), (146, 40), (168, 70), (168, 108), (156, 94),
                 (148, 132), (126, 120), (112, 84), (96, 76), (76, 72), (58, 88), (38, 104)], hc)


def draw_face(pn, m, expr):
    # 顔
    pn.ellipse(100, 104, 60, 58, SKIN)
    # ほっぺ
    pn.ellipse(66, 130, 9, 5, (255, 190, 190), outline=None)
    pn.ellipse(134, 130, 9, 5, (255, 190, 190), outline=None)
    eyes = [(76, 112), (124, 112)]
    if expr in ("normal", "serious", "sweat"):
        for i, (ex, ey) in enumerate(eyes):
            pn.ellipse(ex, ey, 11, 14, (255, 255, 255))
            pn.ellipse(ex, ey + 2, 9, 11, m["eye"], outline=None)
            pn.ellipse(ex, ey + 3, 4.5, 6, (30, 25, 35), outline=None)
            pn.ellipse(ex - 3, ey - 3, 3.5, 3.5, (255, 255, 255), outline=None)
        if expr == "normal":
            pn.arc(100, 136, 10, 7, 20, 160, w=3)
            pn.line([(64, 94), (86, 92)], OUTLINE, 3)
            pn.line([(114, 92), (136, 94)], OUTLINE, 3)
        else:
            pn.line([(88, 142), (112, 142)], OUTLINE, 3)
            pn.line([(62, 90), (88, 98)], OUTLINE, 4)
            pn.line([(112, 98), (138, 90)], OUTLINE, 4)
    elif expr == "laugh":
        for ex, ey in eyes:
            pn.arc(ex, ey + 6, 11, 10, 200, 340, w=4)
        pn.poly([(84, 132), (116, 132), (110, 150), (100, 154), (90, 150)], (200, 60, 80))
        pn.poly([(86, 133), (114, 133), (112, 138), (88, 138)], (255, 255, 255), outline=None)
        pn.line([(64, 92), (86, 88)], OUTLINE, 3)
        pn.line([(114, 88), (136, 92)], OUTLINE, 3)
    elif expr in ("shock", "gloom"):
        for ex, ey in eyes:
            pn.ellipse(ex, ey, 12, 14, (255, 255, 255))
            pn.ellipse(ex, ey, 3, 3, (30, 25, 35), outline=None)
        pn.ellipse(100, 144, 8, 10, (120, 40, 60))
        pn.line([(62, 88), (84, 84)], OUTLINE, 3)
        pn.line([(116, 84), (138, 88)], OUTLINE, 3)
        # 青ざめ線
        for x in (80, 92, 104, 116):
            pn.line([(x, 60), (x, 80)], (110, 120, 220), 3)


def draw_body(pn, m, arms):
    k = m["key"]
    # 剣持：竹刀袋（体の後ろ）
    if k == "kenmochi":
        pn.poly([(112, 200), (160, 30), (190, 38), (142, 208)], (250, 250, 252))
        pn.line([(132, 200), (175, 40)], (205, 205, 215), 3)
        pn.poly([(156, 24), (194, 32), (190, 48), (152, 40)], (120, 70, 210), w=3)
        pn.line([(70, 166), (150, 120)], (120, 70, 210), 7)
    # 脚
    pn.rrect(74, 236, 97, 282, 6, m["pants"])
    pn.rrect(103, 236, 126, 282, 6, m["pants"])
    pn.ellipse(84, 284, 15, 8, (60, 60, 70))
    pn.ellipse(116, 284, 15, 8, (60, 60, 70))

    def arm(side, pose):
        sx = 64 if side < 0 else 136
        col = m["top"]
        hand = SKIN
        sleeve_short = k == "kaida"
        if pose == "down":
            pts = [(sx, 170), (sx + 14 * side, 224)]
        elif pose == "up":
            pts = [(sx, 172), (sx + 22 * side, 110)]
        elif pose == "wave":
            pts = [(sx, 172), (sx + 26 * side, 118)]
        else:  # cook：前に出す
            pts = [(sx, 172), (sx - 12 * side, 212)]
        (x0, y0), (x1, y1) = pts
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        pn.line(pts, OUTLINE, 20)
        if sleeve_short:
            pn.line([(x0, y0), (mx, my)], col, 15)
            pn.line([(mx, my), (x1, y1)], SKIN, 13)
        else:
            pn.line(pts, col, 15)
        pn.ellipse(x1, y1, 9, 9, hand)

    la, ra = arms if isinstance(arms, tuple) else (arms, arms)
    # 胴
    pn.rrect(62, 158, 138, 244, 18, m["top"])
    if k == "kagami":
        pn.poly([(86, 160), (114, 160), (112, 244), (88, 244)], m["inner"], w=2)
        pn.line([(66, 200), (86, 196)], m["accent"], 3)
    elif k == "kenmochi":
        pn.poly([(64, 214), (136, 190), (136, 206), (64, 230)], m["accent"], outline=None)
        pn.line([(100, 160), (100, 244)], (160, 160, 170), 2)
    elif k == "fuwa":
        pn.poly([(70, 162), (100, 206), (130, 162), (136, 240), (64, 240)], m["inner"], w=2)
        pn.poly([(84, 158), (100, 176), (116, 158)], m["top"], w=2)
        pn.ellipse(100, 186, 3, 3, (230, 230, 240))
    else:  # kaida
        pn.poly([(88, 158), (112, 158), (100, 176)], m["inner"], w=2)
        pn.poly([(98, 172), (92, 214), (98, 212)], m["accent"], w=2)
        pn.poly([(102, 172), (108, 214), (102, 212)], m["accent"], w=2)
    # 首元
    if k == "kagami":
        pn.rrect(88, 150, 112, 158, 3, (30, 30, 35), outline=None)
    arm(-1, la)
    arm(1, ra)


@lru_cache(maxsize=None)
def character(idx, expr="normal", arms="down", scale=1.25):
    m = MEMBERS[idx]
    pn = Pen(scale)
    draw_back_hair(pn, m)
    draw_body(pn, m, arms)
    pn.ellipse(100, 152, 12, 8, SKIN, outline=None)  # 首
    draw_face(pn, m, expr)
    draw_bangs(pn, m)
    # 前髪と後ろ髪の継ぎ目を隠す（頭のてっぺんを塗り直して、外側の線だけ引き直す）
    k = pn.k
    rx, ry = 68, 64
    pn.d.chord([(100 - rx) * k, (92 - ry) * k, (100 + rx) * k, (92 + ry) * k], 198, 342, fill=m["hair"])
    pn.arc(100, 92, rx + 3, ry + 3, 196, 344, w=3)
    if m["key"] == "kagami":
        pn.line([(100, 30), (100, 52)], m["hair_dark"], 3)
    if m["key"] == "fuwa":
        pn.poly([(140, 40), (156, 56), (150, 76), (138, 60)], m["accent"], w=2)
    return pn.done()


# ---------------------------------------------------------------- テロップ
@lru_cache(maxsize=None)
def telop(text, size, fill=(255, 235, 40), layers=((22, (30, 20, 40)), (12, (255, 255, 255))), bold=True):
    """縁取り付きのテロップ画像（外側から順に layers で重ねる）"""
    f = font(size, bold)
    pad = max(w for w, _ in layers) + 6
    l, t, r, b = f.getbbox(text)
    im = Image.new("RGBA", (r - l + pad * 2, b - t + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    org = (pad - l, pad - t)
    for w, col in layers:
        d.text(org, text, font=f, fill=col, stroke_width=w, stroke_fill=col)
    d.text(org, text, font=f, fill=fill)
    return im


def pop_scale(t, dur=0.25):
    """ポンッと弾む拡大率"""
    if t < 0:
        return 0
    if t >= dur:
        return 1.0
    x = t / dur
    return 1.18 * math.sin(x * math.pi / 2) if x < 0.7 else 1.18 - (x - 0.7) / 0.3 * 0.18


def paste_center(img, im, cx, cy, s=1.0, rot=0):
    if s <= 0.01:
        return
    if s != 1.0:
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    img.paste(im, (int(cx - im.width / 2), int(cy - im.height / 2)), im)


def paste_bottom(img, im, cx, by, s=1.0, rot=0):
    """下端中央を (cx, by) に合わせて貼る"""
    if s != 1.0:
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    img.paste(im, (int(cx - im.width / 2), int(by - im.height)), im)


def show_telop(img, text, t0, t, cx, cy, size=110, **kw):
    if t < t0:
        return
    paste_center(img, telop(text, size, **kw), cx, cy, pop_scale(t - t0))


# ---------------------------------------------------------------- 番組の枠
LABEL_BG = (230, 40, 90)


@lru_cache(maxsize=None)
def corner_label(text):
    f = font(46)
    l, t, r, b = f.getbbox(text)
    w, h = r - l + 60, 78
    im = Image.new("RGBA", (w + 12, h + 12), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([8, 8, w + 8, h + 8], 16, fill=(30, 20, 40, 160))
    d.rounded_rectangle([0, 0, w, h], 16, fill=LABEL_BG, outline=(255, 255, 255), width=5)
    d.text((30 - l, (h - (b - t)) // 2 - t), text, font=f, fill=(255, 255, 255))
    return im


@lru_cache(maxsize=None)
def logo_small():
    im = Image.new("RGBA", (470, 96), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([6, 6, 464, 90], 44, fill=(255, 255, 255), outline=(30, 20, 40), width=5)
    cols = [m["color"] for m in MEMBERS]
    for i, c in enumerate(cols):
        d.ellipse([28 + i * 22, 38, 46 + i * 22, 56], fill=c, outline=(30, 20, 40), width=2)
    tl = telop("ROF-MAOって？", 40, fill=(120, 60, 200), layers=((4, (255, 255, 255)),))
    im.paste(tl, (128, 48 - tl.height // 2), tl)
    return im


def frame_ui(img, label):
    img.paste(corner_label(label), (30, 28), corner_label(label))
    lg = logo_small()
    img.paste(lg, (W - lg.width - 26, 26), lg)


# ---------------------------------------------------------------- 背景
def gradient(h_top, h_bot, size=(W, H)):
    w, h = size
    a = np.linspace(0, 1, h)[:, None, None]
    top = np.array(h_top, float)[None, None, :]
    bot = np.array(h_bot, float)[None, None, :]
    arr = (top * (1 - a) + bot * a).repeat(w, axis=1)
    return Image.fromarray(arr.astype(np.uint8))


@lru_cache(maxsize=None)
def bg_location():
    img = gradient((110, 190, 255), (200, 235, 255))
    d = ImageDraw.Draw(img)
    for cx, cy, s in [(300, 160, 1.0), (1000, 110, 1.3), (1600, 190, 0.9)]:
        for dx, dy, r in [(-60, 10, 50), (0, -20, 70), (70, 10, 55), (20, 25, 50)]:
            d.ellipse([cx + (dx - r) * s, cy + (dy - r) * s, cx + (dx + r) * s, cy + (dy + r) * s], fill=(255, 255, 255))
    # 山と木
    d.polygon([(-100, 640), (350, 330), (800, 640)], fill=(120, 170, 120))
    d.polygon([(600, 640), (1150, 290), (1700, 640)], fill=(100, 155, 110))
    d.polygon([(1400, 640), (1800, 380), (2200, 640)], fill=(120, 170, 120))
    d.rectangle([0, 620, W, H], fill=(120, 200, 90))
    for x in range(60, W, 240):
        d.rectangle([x + 30, 540, x + 46, 640], fill=(130, 90, 60))
        d.ellipse([x, 460, x + 76, 580], fill=(60, 150, 80))
    # ロケっぽいテント
    d.polygon([(1450, 620), (1560, 470), (1780, 470), (1880, 620)], fill=(250, 250, 250), outline=(80, 80, 90))
    for x in range(1470, 1880, 50):
        d.polygon([(x, 620), (x + 25, 620), (x + 25 + (1560 - 1450) * 0 - 10, 470)], fill=(230, 60, 90))
    return img.filter(ImageFilter.GaussianBlur(2))


@lru_cache(maxsize=None)
def bg_studio():
    img = gradient((50, 30, 90), (120, 60, 150))
    d = ImageDraw.Draw(img)
    # カラフルなパネル
    cols = [m["color"] for m in MEMBERS]
    for i in range(12):
        x = i * 170 - 40
        c = cols[i % 4]
        d.rounded_rectangle([x, 120, x + 140, 560], 26, fill=tuple(int(v * 0.55) for v in c))
        d.rounded_rectangle([x + 16, 136, x + 124, 544], 20, outline=c, width=6)
    d.rectangle([0, 640, W, H], fill=(70, 50, 110))
    d.polygon([(0, 640), (W, 640), (W, 700), (0, 700)], fill=(240, 220, 90))
    for x in range(0, W, 120):
        d.line([(x, 700), (x - 200, H)], fill=(90, 70, 140), width=4)
    return img


@lru_cache(maxsize=None)
def bg_room():
    """配信部屋（VTuberといえば？）"""
    img = gradient((40, 44, 70), (70, 76, 110))
    d = ImageDraw.Draw(img)
    for x in range(0, W, 64):
        d.line([(x, 0), (x, 700)], fill=(55, 60, 90), width=2)
    d.rectangle([0, 700, W, H], fill=(90, 80, 100))
    return img


def rays(img, t, colors, cx=W // 2, cy=H // 2, n=24):
    d = ImageDraw.Draw(img)
    R = 2400
    for i in range(n):
        a0 = (i / n) * math.tau + t * 0.4
        a1 = a0 + math.tau / n
        d.polygon([(cx, cy), (cx + math.cos(a0) * R, cy + math.sin(a0) * R),
                   (cx + math.cos(a1) * R, cy + math.sin(a1) * R)], fill=colors[i % len(colors)])


def speed_lines(img, t, strength=1.0):
    """集中線"""
    d = ImageDraw.Draw(img)
    rnd = random.Random(int(t * 12))
    cx, cy = W // 2, 420
    for _ in range(int(70 * strength)):
        a = rnd.random() * math.tau
        r0 = 620 + rnd.random() * 200
        r1 = 1300
        wdt = rnd.randint(2, 6)
        d.line([(cx + math.cos(a) * r0, cy + math.sin(a) * r0 * 0.7),
                (cx + math.cos(a) * r1, cy + math.sin(a) * r1 * 0.7)], fill=(255, 255, 255), width=wdt)


def sparkles(img, t, seed, n=18, area=(0, 0, W, H), col=(255, 250, 200)):
    d = ImageDraw.Draw(img)
    rnd = random.Random(seed)
    for i in range(n):
        x = rnd.uniform(area[0], area[2])
        y = rnd.uniform(area[1], area[3])
        ph = rnd.random() * 6
        s = (math.sin(t * 6 + ph) + 1) / 2 * 18 + 4
        d.polygon([(x, y - s), (x + s * 0.25, y - s * 0.25), (x + s, y), (x + s * 0.25, y + s * 0.25),
                   (x, y + s), (x - s * 0.25, y + s * 0.25), (x - s, y), (x - s * 0.25, y - s * 0.25)], fill=col)


def confetti(img, t, seed=5, n=120):
    d = ImageDraw.Draw(img)
    rnd = random.Random(seed)
    cols = [m["color"] for m in MEMBERS] + [(255, 230, 60), (255, 120, 120)]
    for i in range(n):
        x = (rnd.uniform(0, W) + math.sin(t * 2 + i) * 30) % W
        y = (rnd.uniform(-H, 0) + t * rnd.uniform(180, 320)) % (H + 40) - 20
        a = t * rnd.uniform(3, 8) + i
        w, h = 16, 8
        pts = [(x + math.cos(a) * w - math.sin(a) * h * 0.5, y + math.sin(a) * w * 0.3 + math.cos(a) * h),
               (x - math.cos(a) * w - math.sin(a) * h * 0.5, y - math.sin(a) * w * 0.3 + math.cos(a) * h),
               (x - math.cos(a) * w + math.sin(a) * h * 0.5, y - math.sin(a) * w * 0.3 - math.cos(a) * h),
               (x + math.cos(a) * w + math.sin(a) * h * 0.5, y + math.sin(a) * w * 0.3 - math.cos(a) * h)]
        d.polygon(pts, fill=cols[i % len(cols)])


def sweat(img, x, y, t, seed=0):
    """汗が飛ぶ"""
    d = ImageDraw.Draw(img)
    for j in range(2):
        ph = (t * 1.6 + seed * 0.37 + j * 0.5) % 1
        sx = x + (j * 2 - 1) * (40 + ph * 60)
        sy = y - ph * 50 + ph * ph * 90
        if ph < 0.8:
            r = 14
            d.polygon([(sx, sy - r * 1.8), (sx - r, sy), (sx + r, sy)], fill=(140, 210, 255))
            d.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(140, 210, 255), outline=(60, 120, 200), width=3)


def bubble(img, text, x, y, tail, t0, t, size=50, fill=(255, 255, 255)):
    """ふきだし（ポンッと出る）。tail はしっぽの先の画面座標。"""
    if t < t0:
        return
    f = font(size)
    l, tp, r, b = f.getbbox(text)
    w, h = r - l + 56, b - tp + 40
    minx, miny = min(x, tail[0]) - 20, min(y, tail[1]) - 20
    maxx, maxy = max(x + w, tail[0]) + 20, max(y + h, tail[1]) + 20
    im = Image.new("RGBA", (int(maxx - minx), int(maxy - miny)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ox, oy = x - minx, y - miny
    tx, ty = tail[0] - minx, tail[1] - miny
    bx = max(ox + 30, min(ox + w - 70, tx - 20))
    by = oy + h - 4 if ty > oy + h / 2 else oy + 4
    d.polygon([(bx, by), (bx + 40, by), (tx, ty)], fill=fill, outline=OUTLINE)
    d.line([(bx, by), (tx, ty), (bx + 40, by)], fill=OUTLINE, width=5)
    d.rounded_rectangle([ox, oy, ox + w, oy + h], 30, fill=fill, outline=OUTLINE, width=5)
    d.polygon([(bx + 4, by), (bx + 36, by), (tx, ty)], fill=fill)
    d.line([(bx + 4, by), (tx, ty)], fill=OUTLINE, width=0)
    d.text((ox + 28 - l, oy + 20 - tp), text, font=f, fill=(30, 20, 40))
    s = pop_scale(t - t0, 0.2)
    if s <= 0.01:
        return
    cx, cy = x + w / 2, y + h / 2
    if s != 1.0:
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
    img.paste(im, (int(cx - (cx - minx) * s), int(cy - (cy - miny) * s)), im)


# ---------------------------------------------------------------- 場面の設定
SCENES = [
    (0.0, 5.0, "opening", None),
    (5.0, 12.0, "vtuber", "VTuberといえば？"),
    (12.0, 20.0, "challenge", "本気の挑戦"),
    (20.0, 27.0, "result", "まさかの結果"),
    (27.0, 34.0, "tsukkomi", "反省会"),
    (34.0, 40.0, "ending", "エンディング"),
]
ROW_X = [360, 760, 1160, 1560]
ROW_BOTTOM = 880


def row_members(img, t, expr="normal", arms="down", hop=None, scale=1.25, bottom=ROW_BOTTOM, xs=ROW_X):
    for i, x in enumerate(xs):
        e = expr(i) if callable(expr) else expr
        a = arms(i) if callable(arms) else arms
        dy = hop(i) if hop else 0
        paste_bottom(img, character(i, e, a, scale), x, bottom - dy)


def scene_opening(img, t):
    cols = [(255, 214, 80), (255, 240, 150)]
    rays(img, t, cols)
    sparkles(img, t, 1, n=30)
    # メンバーが1人ずつポンッと登場
    for i, x in enumerate(ROW_X):
        t0 = 1.5 + i * 0.45
        if t >= t0:
            s = pop_scale(t - t0)
            hop = abs(math.sin((t - t0) * 5)) * 16 if t - t0 > 0.3 else 0
            ch = character(i, "normal", "wave" if i % 2 == 0 else ("down", "wave"), 1.15)
            ch = ch.resize((max(1, int(ch.width * s)), max(1, int(ch.height * s))), Image.BILINEAR)
            paste_bottom(img, ch, x, 930 - hop)
            m = MEMBERS[i]
            nm = telop(m["name"], 50, fill=m["text_color"], layers=((10, (30, 20, 40)),))
            paste_center(img, nm, x, 975, pop_scale(t - t0 - 0.1))
    # タイトル
    s = pop_scale(t - 0.2, 0.35)
    wob = math.sin(t * 3) * 2
    paste_center(img, telop("ROF-MAOって？", 190, fill=(255, 230, 40),
                            layers=((34, (30, 20, 40)), (22, (230, 40, 90)), (10, (255, 255, 255)))),
                 W // 2, 230, s, rot=wob)
    if t >= 0.9:
        paste_center(img, telop("VTuberユニット「ROF-MAO」をご紹介！", 58, fill=(255, 255, 255),
                                layers=((12, (30, 20, 40)),)), W // 2, 420, pop_scale(t - 0.9))


def monitor(img, x, y, w, h, t, hair, label, seed):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x - 14, y - 14, x + w + 14, y + h + 14], 18, fill=(25, 25, 32))
    scr = gradient((70, 90, 160), (140, 110, 190), (w, h))
    sd = ImageDraw.Draw(scr)
    # 一般的なアバター（特定の人ではない）
    cx, cy = w // 2, h // 2 + 30
    bob = math.sin(t * 4 + seed) * 6
    sd.ellipse([cx - 90, cy - 120 + bob, cx + 90, cy + 60 + bob], fill=hair)
    sd.polygon([(cx - 80, cy - 90 + bob), (cx - 60, cy - 160 + bob), (cx - 30, cy - 110 + bob)], fill=hair)
    sd.polygon([(cx + 80, cy - 90 + bob), (cx + 60, cy - 160 + bob), (cx + 30, cy - 110 + bob)], fill=hair)
    sd.ellipse([cx - 66, cy - 80 + bob, cx + 66, cy + 50 + bob], fill=SKIN)
    sd.ellipse([cx - 36, cy - 30 + bob, cx - 16, cy + bob], fill=(40, 30, 50))
    sd.ellipse([cx + 16, cy - 30 + bob, cx + 36, cy + bob], fill=(40, 30, 50))
    if int(t * 5 + seed) % 2:
        sd.ellipse([cx - 12, cy + 16 + bob, cx + 12, cy + 32 + bob], fill=(200, 60, 80))
    else:
        sd.line([cx - 12, cy + 22 + bob, cx + 12, cy + 22 + bob], fill=(40, 30, 50), width=4)
    sd.rectangle([0, h - 70, w, h], fill=(0, 0, 0))
    sd.rounded_rectangle([16, 16, 110, 56], 8, fill=(230, 30, 60))
    sd.text((30, 18), "LIVE", font=font(30), fill=(255, 255, 255))
    img.paste(scr, (x, y))
    lab = telop(label, 44, fill=(255, 255, 255), layers=((8, (30, 20, 40)),))
    paste_center(img, lab, x + w // 2, y + h - 34)


CRASH = 3.6  # ガシャーン（場面内）


def scene_vtuber(img, t):
    if t < CRASH:
        img.paste(bg_room())
        items = [((255, 150, 190), "ゲーム実況"), ((120, 220, 170), "雑談配信"), ((255, 190, 90), "歌枠")]
        for i, (hair, lab) in enumerate(items):
            monitor(img, 150 + i * 560, 220, 500, 380, t, hair, lab, i)
        show_telop(img, "VTuberといえば… 配信！", 0.7, t, W // 2, 850, 96, fill=(255, 255, 255),
                   layers=((20, (30, 20, 40)), (10, (60, 120, 230))))
    else:
        k = t - CRASH
        img.paste(bg_location())
        hop = (lambda i: abs(math.sin((t - 5.2) * 7 + i)) * 26) if t >= 5.2 else None
        row_members(img, t, "laugh" if t >= 5.2 else "normal",
                    lambda i: "up" if t >= 5.2 else "wave", hop)
        show_telop(img, "ROF-MAOは…", 0.5 + CRASH - CRASH + 0.4, k, W // 2, 330, 90, fill=(255, 255, 255),
                   layers=((18, (30, 20, 40)), (8, (230, 40, 90))))
        if t >= 5.2:
            s = pop_scale(t - 5.2, 0.3)
            paste_center(img, telop("ロケに行く。", 200, fill=(255, 230, 40),
                                    layers=((34, (30, 20, 40)), (20, (230, 40, 90)), (8, (255, 255, 255)))),
                         W // 2, 950, s)
        # 割れたガラスの破片
        if k < 0.9:
            rnd = random.Random(4)
            d = ImageDraw.Draw(img)
            for i in range(26):
                a = rnd.random() * math.tau
                sp = rnd.uniform(500, 1400)
                x = W / 2 + math.cos(a) * sp * k
                y = H / 2 + math.sin(a) * sp * k + 900 * k * k
                s = rnd.uniform(40, 110)
                rot = a + k * 6
                pts = [(x + math.cos(rot + j * 2.1) * s * (0.6 + 0.4 * (j % 2)),
                        y + math.sin(rot + j * 2.1) * s * (0.6 + 0.4 * (j % 2))) for j in range(3)]
                d.polygon(pts, fill=(200, 225, 255), outline=(255, 255, 255))
    # 割れる直前のヒビ
    if CRASH - 0.25 <= t < CRASH:
        d = ImageDraw.Draw(img)
        rnd = random.Random(2)
        for i in range(14):
            a = i / 14 * math.tau + rnd.random() * 0.3
            pts = [(W / 2, H / 2)]
            r = 0
            while r < 1200:
                r += rnd.uniform(80, 180)
                aa = a + rnd.uniform(-0.15, 0.15)
                pts.append((W / 2 + math.cos(aa) * r, H / 2 + math.sin(aa) * r))
            d.line(pts, fill=(255, 255, 255), width=6)
    if CRASH <= t < CRASH + 0.12:
        img.paste((255, 255, 255), [0, 0, W, H])


def stove(img, cx, by, t, seed):
    d = ImageDraw.Draw(img)
    # 火
    for j in range(5):
        fx = cx - 60 + j * 30
        fh = 30 + math.sin(t * 20 + j + seed) * 10
        d.polygon([(fx - 12, by - 44), (fx + 12, by - 44), (fx, by - 44 - fh)], fill=(255, 140, 40))
        d.polygon([(fx - 6, by - 44), (fx + 6, by - 44), (fx, by - 44 - fh * 0.6)], fill=(255, 230, 80))
    d.rounded_rectangle([cx - 90, by - 46, cx + 90, by], 10, fill=(90, 90, 100), outline=OUTLINE, width=4)
    # フライパン
    jig = math.sin(t * 16 + seed) * 8
    px, py = cx + jig, by - 70
    d.ellipse([px - 90, py - 20, px + 90, py + 20], fill=(50, 50, 58), outline=OUTLINE, width=4)
    d.ellipse([px - 70, py - 12, px + 70, py + 10], fill=(255, 220, 80))
    d.line([(px + 88, py), (px + 170, py - 26)], fill=(40, 30, 30), width=14)


def counter(img, top=720):
    d = ImageDraw.Draw(img)
    d.rectangle([0, top, W, H], fill=(210, 160, 110))
    d.rectangle([0, top, W, top + 24], fill=(240, 200, 150))
    d.line([(0, top), (W, top)], fill=OUTLINE, width=5)
    d.line([(0, top + 24), (W, top + 24)], fill=OUTLINE, width=3)


def scene_challenge(img, t):
    img.paste(bg_location())
    if t >= 3.2:
        speed_lines(img, t, 1.0)
    expr = "serious" if t >= 1.0 else "normal"
    row_members(img, t, expr, "cook", bottom=800)
    counter(img)
    for i, x in enumerate(ROW_X):
        stove(img, x, 744, t, i)
        if t >= 1.0:
            sweat(img, x, 380, t, i)
    # お題ボード
    if t >= 0.4:
        s = pop_scale(t - 0.4, 0.3)
        board = Image.new("RGBA", (1300, 200), (0, 0, 0, 0))
        bd = ImageDraw.Draw(board)
        bd.rounded_rectangle([8, 8, 1292, 192], 30, fill=(255, 255, 255), outline=(230, 40, 90), width=12)
        tl = telop("お題：ふわふわオムライスを作れ！", 76, fill=(230, 40, 90), layers=((6, (255, 255, 255)),))
        board.paste(tl, ((1300 - tl.width) // 2, (200 - tl.height) // 2), tl)
        y = 230 if t < 3.0 else 230 - min(1, (t - 3.0) / 0.3) * 60
        sc = 1.0 if t < 3.0 else 1 - min(1, (t - 3.0) / 0.3) * 0.3
        paste_center(img, board, W // 2, y + 10, s * sc)
    show_telop(img, "全員、本気。", 3.2, t, W // 2, 940, 150, fill=(255, 255, 255),
               layers=((30, (30, 20, 40)), (16, (230, 40, 90))))


REVEAL = 1.5   # フタを開ける（場面内）
COLLAPSE = 2.8  # 崩れ落ちる


def scene_result(img, t):
    img.paste(bg_location())
    shake = 0
    if REVEAL <= t < REVEAL + 0.4:
        shake = int(math.sin(t * 90) * 18 * (1 - (t - REVEAL) / 0.4))
    collapsed = t >= COLLAPSE
    for i, x in enumerate(ROW_X):
        if t < REVEAL:
            e = "sweat"
        elif not collapsed:
            e = "shock"
        else:
            e = "gloom"
        ch = character(i, e, "down" if not collapsed else "down")
        if collapsed:
            k = min(1.0, (t - COLLAPSE) / 0.35)
            rot = (1 if i % 2 else -1) * 14 * k
            paste_bottom(img, ch, x + shake, ROW_BOTTOM + 60 * k, rot=rot)
        else:
            paste_bottom(img, ch, x + shake, ROW_BOTTOM - 80)
    if t < REVEAL:
        for i, x in enumerate(ROW_X):
            sweat(img, x, 380, t, i)
    # テーブルとお皿
    d = ImageDraw.Draw(img)
    cx, cy = W // 2 + shake, 820
    d.rounded_rectangle([cx - 520, cy + 40, cx + 520, cy + 110], 20, fill=(210, 160, 110), outline=OUTLINE, width=5)
    d.ellipse([cx - 230, cy - 20, cx + 230, cy + 60], fill=(255, 255, 255), outline=OUTLINE, width=5)
    if t >= REVEAL:
        # 黒コゲ
        d.ellipse([cx - 150, cy - 40, cx + 150, cy + 40], fill=(40, 30, 30), outline=(10, 10, 10), width=4)
        for j in range(6):
            ph = (t * 0.7 + j / 6) % 1
            sx = cx - 100 + j * 40 + math.sin(t * 3 + j) * 12
            sy = cy - 50 - ph * 300
            r = 26 + ph * 40
            g = int(150 + ph * 60)
            d.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(g, g, g))
        if t < COLLAPSE + 0.4:
            show_telop(img, "黒コゲ…", REVEAL + 0.4, t, cx, 990, 100, fill=(60, 60, 60),
                       layers=((18, (30, 20, 40)), (10, (255, 255, 255))))
    # フタ（クローシュ）
    lift = 0 if t < REVEAL else min(1.0, (t - REVEAL) / 0.3)
    fy = cy - 10 - lift * 1200
    if fy > -300:
        d.chord([cx - 210, fy - 200, cx + 210, fy + 170], 180, 360, fill=(215, 220, 230), outline=OUTLINE, width=6)
        d.ellipse([cx - 26, fy - 230, cx + 26, fy - 190], fill=(215, 220, 230), outline=OUTLINE, width=6)
        d.arc([cx - 170, fy - 170, cx + 110, fy + 120], 200, 250, fill=(255, 255, 255), width=10)
    if t < REVEAL:
        show_telop(img, "結果は…？", 0.3, t, W // 2, 330, 110, fill=(255, 255, 255),
                   layers=((20, (30, 20, 40)), (8, (60, 120, 230))))
    if collapsed:
        # どんより
        ov = Image.new("RGBA", (W, H), (40, 50, 120, int(90 * min(1, (t - COLLAPSE) / 0.4))))
        img.paste(ov, (0, 0), ov)
        d = ImageDraw.Draw(img)
        for i, x in enumerate(ROW_X):
            for j in range(4):
                lx = x - 70 + j * 45
                d.line([(lx, 340), (lx, 480)], fill=(90, 100, 200), width=6)
    if t >= COLLAPSE + 0.4:
        s = pop_scale(t - COLLAPSE - 0.4, 0.35)
        sh = math.sin(t * 40) * 6 if t < COLLAPSE + 0.9 else 0
        paste_center(img, telop("まさかの結果", 170, fill=(120, 170, 255),
                                layers=((32, (20, 20, 50)), (16, (255, 255, 255)))),
                     W // 2 + sh, 960, s)


LINES = [  # (時刻, 話す人, セリフ, x, y) ふきだしは話す人の頭の上あたりに出す
    (0.6, 1, "火力、強すぎでしょ！", 470, 150),
    (1.1, 0, "いや、レシピ通りです！", 50, 250),
    (1.6, 3, "どのレシピ見たの？", 930, 420),
    (2.1, 2, "逆にすごくない？", 880, 270),
    (2.6, 1, "もう一回やらせて！", 500, 340),
    (3.0, 0, "スタッフさん笑ってる！", 40, 410),
]
WIPE_FACES = [2, 0, 3, 1]


@lru_cache(maxsize=None)
def face_crop(i, expr):
    ch = character(i, expr, "down", 2.0)
    return ch.crop((20, 20, ch.width - 20, 360))


def scene_tsukkomi(img, t):
    img.paste(bg_studio())
    laughing = t >= 4.0

    def expr(i):
        if laughing:
            return "laugh"
        return "laugh" if int(t * 3 + i) % 3 == 0 else "normal"

    def arms(i):
        return ("up", "down") if int(t * 4 + i) % 2 else ("down", "wave")

    hop = lambda i: abs(math.sin(t * 8 + i * 1.3)) * (20 if laughing else 8)
    row_members(img, t, expr, arms, hop)
    # ふきだしがどんどんかぶる
    if t < 4.3:
        for t0, who, text, x, y in LINES:
            bubble(img, text, x, y, (ROW_X[who], 530), t0, t)
    # ワイプ
    if t >= 1.0:
        wx, wy, ww, wh = W - 470, 140, 420, 270
        s = pop_scale(t - 1.0, 0.25)
        wipe = Image.new("RGBA", (ww, wh), (0, 0, 0, 0))
        who = WIPE_FACES[int((t - 1.0) / 1.2) % 4]
        inner = gradient((255, 240, 200), (255, 210, 160), (ww, wh)).convert("RGBA")
        fc = face_crop(who, "laugh")
        fb = abs(math.sin(t * 10)) * 10
        inner.paste(fc, ((ww - fc.width) // 2, int(-45 - fb)), fc)
        mask = Image.new("L", (ww, wh), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, ww - 1, wh - 1], 30, fill=255)
        wipe.paste(inner, (0, 0), mask)
        ImageDraw.Draw(wipe).rounded_rectangle([0, 0, ww - 1, wh - 1], 30, outline=(255, 255, 255), width=10)
        paste_center(img, wipe, wx + ww / 2, wy + wh / 2, s)
        show_telop(img, "（笑）", 1.3, t, wx + ww - 70, wy + wh - 30, 60, fill=(255, 255, 255),
                   layers=((10, (230, 40, 90)),))
    if t >= 3.4:
        s = pop_scale(t - 3.4, 0.3)
        paste_center(img, telop("ツッコミが止まらない", 150, fill=(255, 230, 40),
                                layers=((30, (30, 20, 40)), (16, (230, 40, 90)))),
                     W // 2, 960, s)


FINAL = 2.3  # 最後の一言（場面内）


def scene_ending(img, t):
    rays(img, t * 0.6, [(255, 190, 220), (255, 225, 240)])
    confetti(img, t)
    row_members(img, t, "laugh" if t >= FINAL else "normal",
                lambda i: ("wave", "down") if int(t * 3 + i) % 2 else ("down", "wave"),
                lambda i: abs(math.sin(t * 5 + i)) * 14, bottom=820)
    if t < FINAL:
        show_telop(img, "次回もお楽しみに！", 0.6, t, W // 2, 940, 120, fill=(255, 255, 255),
                   layers=((24, (30, 20, 40)), (12, (230, 40, 90))))
    else:
        s = pop_scale(t - FINAL, 0.4)
        # 帯
        band = Image.new("RGBA", (W, 250), (30, 20, 40, 210))
        paste_center(img, band, W // 2, 930, 1.0 if t - FINAL > 0.15 else max(0.02, (t - FINAL) / 0.15))
        paste_center(img, telop("VTuberの、バラエティ番組。", 118, fill=(255, 235, 60),
                                layers=((20, (255, 255, 255)),)), W // 2, 930, s)
        sparkles(img, t, 8, n=16, area=(200, 800, W - 200, 1060))


SCENE_FUNCS = dict(opening=scene_opening, vtuber=scene_vtuber, challenge=scene_challenge,
                   result=scene_result, tsukkomi=scene_tsukkomi, ending=scene_ending)

# ---------------------------------------------------------------- 画面切り替え（カラフルな帯）
TRANS = 0.3  # 境目の前後それぞれの長さ
BAND_COLS = [(255, 230, 60), (245, 245, 250), (128, 80, 220), (225, 60, 170), (60, 170, 235)]


def draw_bands(img, p):
    """p: 0→1 で帯が左から右へ横切る。p=0.5 で画面が全部おおわれる。"""
    d = ImageDraw.Draw(img)
    bw = 520
    skew = 360
    total = bw * len(BAND_COLS)
    x0 = -total - skew + p * (W + total + skew * 2)
    for i, c in enumerate(BAND_COLS):
        xa = x0 + i * bw
        d.polygon([(xa + skew, 0), (xa + skew + bw + 2, 0), (xa + bw + 2, H), (xa, H)], fill=c)
        d.line([(xa + skew, 0), (xa, H)], fill=OUTLINE, width=6)


# ---------------------------------------------------------------- フレーム
def render(t):
    img = Image.new("RGB", (W, H), (255, 255, 255))
    for i, (s, e, name, label) in enumerate(SCENES):
        if s <= t < e or (i == len(SCENES) - 1 and t >= s):
            lt = t - s
            SCENE_FUNCS[name](img, lt)
            if label:
                frame_ui(img, label)
            break
    # 境目の前後で帯を横切らせる
    for s, e, name, label in SCENES[1:]:
        if abs(t - s) < TRANS:
            draw_bands(img, (t - s + TRANS) / (2 * TRANS))
    return img


# ---------------------------------------------------------------- 効果音・BGM
SR = 44100


def env_decay(n, rate):
    return np.exp(-np.arange(n) / SR * rate)


def sine(freq, dur, vol=0.3, decay=0.0, sweep=None):
    n = int(SR * dur)
    tt = np.arange(n) / SR
    f = np.full(n, float(freq)) if sweep is None else np.geomspace(freq, sweep, n)
    w = np.sin(np.cumsum(f) / SR * math.tau)
    e = np.ones(n) if not decay else env_decay(n, decay)
    a = min(n, 200)
    e[:a] *= np.linspace(0, 1, a)
    return (w * e * vol).astype(np.float32)


def noise(dur, vol=0.3, decay=0.0, smooth=1, seed=0):
    n = int(SR * dur)
    w = np.random.default_rng(seed).uniform(-1, 1, n)
    if smooth > 1:
        w = np.convolve(w, np.ones(smooth) / smooth, mode="same") * math.sqrt(smooth)
    e = np.ones(n) if not decay else env_decay(n, decay)
    return (w * e * vol).astype(np.float32)


def mix(*parts):
    L = max(len(p) for p in parts)
    out = np.zeros(L, np.float32)
    for p in parts:
        out[:len(p)] += p
    return out


def se_pon():
    return sine(900, 0.12, 0.35, decay=30, sweep=380)


def se_don():
    return mix(sine(70, 1.0, 0.7, decay=3.5, sweep=45), noise(0.3, 0.35, decay=14, smooth=24, seed=1))


def se_gashan():
    parts = [noise(0.7, 0.45, decay=7, seed=2)]
    for f in (2100, 3170, 4230, 5600):
        parts.append(sine(f, 0.8, 0.08, decay=6))
    rnd = np.random.default_rng(3)
    for _ in range(14):
        s = np.zeros(int(SR * 0.9), np.float32)
        i = int(rnd.uniform(0.05, 0.8) * SR)
        c = sine(rnd.uniform(2500, 6000), 0.05, 0.12, decay=60)
        s[i:i + len(c)] += c[: len(s) - i]
        parts.append(s)
    return mix(*parts)


def se_chin():
    return mix(sine(1320, 2.2, 0.28, decay=2.0), sine(1320 * 2.76, 1.2, 0.08, decay=4),
               sine(1320 * 5.4, 0.6, 0.04, decay=8))


def se_pinpon():
    return np.concatenate([sine(988, 0.32, 0.3, decay=3), sine(784, 0.8, 0.3, decay=3)])


def saw(freq, dur, vol, decay=0.0):
    n = int(SR * dur)
    tt = np.arange(n) / SR
    w = sum(np.sin(tt * math.tau * freq * h) / h for h in range(1, 8))
    e = np.ones(n) if not decay else env_decay(n, decay)
    return (w * e * vol * 0.5).astype(np.float32)


def se_jan():
    return mix(*[saw(f, 0.7, 0.12, decay=4) for f in (261.6, 329.6, 392.0, 523.3)],
               noise(0.15, 0.2, decay=25, seed=4))


def se_whoosh():
    n = int(SR * 0.6)
    w = noise(0.6, 0.25, smooth=6, seed=5)
    e = np.sin(np.linspace(0, math.pi, n)) ** 2
    return (w * e).astype(np.float32)


def se_drumroll(dur=1.2):
    out = np.zeros(int(SR * dur), np.float32)
    t = 0.0
    k = 0
    while t < dur:
        hit = noise(0.05, 0.18 + 0.12 * t / dur, decay=60, smooth=3, seed=10 + k)
        i = int(t * SR)
        out[i:i + len(hit)] += hit[: len(out) - i]
        t += 0.06
        k += 1
    return out


def se_sizzle(dur):
    w = noise(dur, 0.05, seed=6)
    w = w - np.convolve(w, np.ones(8) / 8, mode="same")  # 高い音だけ
    rnd = np.random.default_rng(7)
    for _ in range(int(dur * 25)):
        i = int(rnd.uniform(0, dur) * SR)
        c = noise(0.01, 0.12, decay=300, seed=int(rnd.integers(1000)))
        w[i:i + len(c)] += c[: len(w) - i]
    return w.astype(np.float32)


def note(name):
    names = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6,
             "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
    return 440.0 * 2 ** ((names[name[:-1]] + (int(name[-1]) - 4) * 12 - 9) / 12)


def pluck(freq, dur, vol):
    return mix(sine(freq, dur, vol, decay=7), sine(freq * 2, dur, vol * 0.3, decay=10))


def se_jingle():
    seq = ["C5", "E5", "G5", "C6", "E6", "G6"]
    out = np.zeros(int(SR * 2.6), np.float32)
    for i, n in enumerate(seq):
        s = mix(sine(note(n), 0.6, 0.18, decay=5), sine(note(n) * 2.76, 0.3, 0.04, decay=9))
        j = int(i * 0.08 * SR)
        out[j:j + len(s)] += s
    j = int(0.55 * SR)
    ch = mix(*[saw(note(n), 1.8, 0.07, decay=1.6) for n in ("C4", "E4", "G4", "C5")],
             sine(note("C6"), 1.8, 0.1, decay=1.5))
    out[j:j + len(ch)] += ch[: len(out) - j]
    return out


def bgm(total):
    """軽快なBGM（ベース＋コード＋ハイハット）"""
    bpm = 128
    beat = 60 / bpm
    out = np.zeros(int(SR * total), np.float32)
    prog = [("C3", ["C4", "E4", "G4"]), ("G2", ["B3", "D4", "G4"]),
            ("A2", ["C4", "E4", "A4"]), ("F2", ["A3", "C4", "F4"])]
    n_beats = int(total / beat)
    for b in range(n_beats):
        bar = (b // 4) % 4
        root, chord = prog[bar]
        t = b * beat
        i = int(t * SR)
        bass = pluck(note(root), beat * 0.9, 0.16)
        out[i:i + len(bass)] += bass[: len(out) - i]
        j = int((t + beat / 2) * SR)
        st = mix(*[pluck(note(n), beat * 0.4, 0.035) for n in chord])
        out[j:j + len(st)] += st[: len(out) - j]
        for h in (0, 0.5):
            k = int((t + h * beat) * SR)
            hh = noise(0.03, 0.05, decay=120, seed=b * 2 + int(h * 2))
            hh = hh - np.convolve(hh, np.ones(4) / 4, mode="same")
            out[k:k + len(hh)] += hh[: len(out) - k]
    return out


def build_audio(path):
    total = DURATION
    buf = np.zeros(int(SR * total) + SR * 3, np.float32)

    def add(t, snd, vol=1.0):
        i = int(t * SR)
        j = min(len(buf), i + len(snd))
        buf[i:j] += snd[: j - i] * vol

    # BGM：結果発表の前後は止める
    music = bgm(total)
    gate = np.ones(len(music), np.float32)
    s0, s1 = int(20.0 * SR), int(23.8 * SR)
    fade = int(0.3 * SR)
    gate[s0 - fade:s0] = np.linspace(1, 0, fade)
    gate[s0:s1] = 0
    gate[s1:s1 + fade] = np.linspace(0, 1, fade)
    # 最後の一言でBGMを下げる
    e0 = int(36.2 * SR)
    gate[e0:] *= 0.35
    buf[:len(music)] += music * gate

    for s, e, name, label in SCENES[1:]:
        add(s - TRANS, se_whoosh())
    # オープニング
    add(0.2, se_jan())
    add(0.2, se_don(), 0.6)
    add(0.9, se_pon())
    for i in range(4):
        add(1.5 + i * 0.45, se_pon())
    # VTuberといえば？
    add(5.7, se_pon())
    add(5.0 + CRASH - 0.25, se_gashan())
    add(5.0 + CRASH + 0.9, se_pon())
    add(5.0 + 5.2, se_don())
    add(5.0 + 5.2, se_jan(), 0.7)
    # 本気の挑戦
    add(12.4, se_jan())
    add(12.3, se_sizzle(7.4))
    add(15.2, se_don(), 0.8)
    # まさかの結果
    add(20.3, se_pon())
    add(20.3, se_drumroll(1.2))
    add(20.0 + REVEAL, se_don())
    add(20.0 + REVEAL + 0.4, se_pon())
    add(20.0 + COLLAPSE + 0.1, se_chin())
    add(20.0 + COLLAPSE + 0.4, se_don(), 0.5)
    # 反省会
    for t0, *_ in LINES:
        add(27.0 + t0, se_pon())
    add(28.0, se_pon())
    add(30.4, se_jan())
    # エンディング
    add(34.6, se_pinpon())
    add(34.0 + FINAL, se_jingle())
    buf = buf[: int(SR * total)]
    # 最後は少しフェードアウト
    fo = int(0.8 * SR)
    buf[-fo:] *= np.linspace(1, 0, fo)
    peak = np.max(np.abs(buf))
    if peak > 0.95:
        buf *= 0.95 / peak
    pcm = (buf * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- 書き出し
def write_stills(times, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for t in times:
        render(t).resize((960, 540), Image.LANCZOS).save(os.path.join(out_dir, f"still_{t:05.2f}.png"))


def main():
    if "--stills" in sys.argv:
        i = sys.argv.index("--stills")
        out = sys.argv[i + 1] if len(sys.argv) > i + 1 else "stills"
        times = [float(x) for x in sys.argv[i + 2:]] or \
            [1.0, 4.0, 7.0, 8.7, 11.0, 13.5, 17.0, 20.8, 22.2, 25.0, 29.0, 32.0, 35.5, 38.5]
        write_stills(times, out)
        return
    wav = os.path.join(OUT_DIR, "_rofmao_audio.wav")
    mp4 = os.path.join(OUT_DIR, "rofmao_video.mp4")
    build_audio(wav)
    cmd = [FFMPEG, "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav,
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", mp4]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(int(DURATION * FPS)):
        p.stdin.write(render(f / FPS).tobytes())
    p.stdin.close()
    p.wait()
    os.remove(wav)
    print("wrote", mp4)


if __name__ == "__main__":
    main()
