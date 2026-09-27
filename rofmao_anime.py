"""アニメイラスト風のバストアップをプログラムだけで描く（試し描き：加賀美ハヤト）。

使い方:
    python3 rofmao_anime.py <出力png>
"""
import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SS = 3            # 拡大して描いてから縮小し、線をなめらかにする
CW, CH = 600, 800  # キャラクター画像の大きさ
LINE = (70, 40, 35)


def catmull(pts, n=12):
    """点列をなめらかな曲線にする"""
    pts = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = map(np.array, pts[i - 1:i + 3])
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                                    + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)))
    out.append(tuple(pts[-2]))
    return out


def strand(center, width, taper_start=0.15):
    """中心線にそって、根元が太く先がとがる毛束の輪郭を作る"""
    c = catmull(center, 10)
    n = len(c)
    left, right = [], []
    for i, (x, y) in enumerate(c):
        a = c[min(i + 1, n - 1)]
        b = c[max(i - 1, 0)]
        dx, dy = a[0] - b[0], a[1] - b[1]
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        u = i / (n - 1)
        w = width * (min(1, u / taper_start) if u < taper_start else (1 - u) ** 0.8)
        w = max(w, 0.3)
        left.append((x + nx * w, y + ny * w))
        right.append((x - nx * w, y - ny * w))
    return left + right[::-1]


class Canvas:
    def __init__(self):
        self.img = Image.new("RGBA", (CW * SS, CH * SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def P(self, pts):
        return [(x * SS, y * SS) for x, y in pts]

    def poly(self, pts, fill, outline=None, w=2.2):
        pts = self.P(pts)
        self.d.polygon(pts, fill=fill)
        if outline:
            self.d.line(pts + [pts[0]], fill=outline, width=max(1, int(w * SS)), joint="curve")

    def line(self, pts, fill=LINE, w=2.0, smooth=True):
        pts = catmull(pts, 8) if smooth and len(pts) > 2 else pts
        self.d.line(self.P(pts), fill=fill, width=max(1, int(w * SS)), joint="curve")

    def ellipse(self, cx, cy, rx, ry, fill=None, outline=None, w=2.0):
        self.d.ellipse([(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS],
                       fill=fill, outline=outline, width=int(w * SS) if outline else 0)

    def layer(self):
        return Canvas()

    def paste(self, other, mask=None):
        self.img.alpha_composite(other.img) if mask is None else self.img.paste(other.img, (0, 0), mask)

    def result(self):
        return self.img.resize((CW, CH), Image.LANCZOS)


def clip_to(layer, shape_layer):
    """layer を shape_layer の塗られた部分だけに切り抜く"""
    a = np.array(layer.img)
    m = np.array(shape_layer.img)[:, :, 3]
    a[:, :, 3] = (a[:, :, 3].astype(np.uint16) * m // 255).astype(np.uint8)
    layer.img = Image.fromarray(a)
    return layer


# ---------------------------------------------------------------- 加賀美ハヤト
HAIR = (190, 128, 84)
HAIR_SH = (140, 88, 58)
HAIR_HI = (232, 178, 128)
SKIN = (255, 232, 215)
SKIN_SH = (240, 196, 178)
IRIS_TOP = (96, 56, 26)
IRIS_BOT = (214, 150, 80)
JACKET = (248, 248, 252)
JACKET_SH = (205, 208, 220)
TEE = (38, 38, 44)

FACE = [(226, 250), (224, 300), (230, 360), (252, 410), (300, 452), (348, 410), (370, 360), (376, 300), (374, 250)]


class Narrow:
    """体だけ横幅を細くして描く"""

    def __init__(self, cv, k=0.72):
        self.cv, self.k = cv, k

    def f(self, pts):
        return [(300 + (x - 300) * self.k, y) for x, y in pts]

    def poly(self, pts, *a, **kw):
        self.cv.poly(self.f(pts), *a, **kw)

    def line(self, pts, *a, **kw):
        self.cv.line(self.f(pts), *a, **kw)

    def ellipse(self, cx, cy, *a, **kw):
        self.cv.ellipse(300 + (cx - 300) * self.k, cy, *a, **kw)


def body(cv):
    cv = Narrow(cv)
    # 首
    cv.poly([(272, 420), (328, 420), (334, 520), (266, 520)], SKIN, LINE)
    cv.poly([(272, 440), (328, 440), (330, 470), (270, 478)], SKIN_SH)
    # 黒いTシャツ（V字）
    cv.poly([(170, 560), (430, 560), (470, 800), (130, 800)], TEE, LINE)
    cv.poly([(262, 505), (338, 505), (300, 590)], SKIN, LINE)
    # チョーカー
    cv.poly([(266, 470), (334, 470), (334, 486), (266, 486)], (30, 30, 34), LINE, 1.5)
    cv.ellipse(300, 490, 6, 6, (180, 180, 190), LINE, 1.2)
    # 白いジャケット（前を開けている）
    for side in (-1, 1):
        sx = 300 + side * 40
        pts = [(sx, 500), (300 + side * 150, 520), (300 + side * 260, 600), (300 + side * 290, 800),
               (300 + side * 70, 800), (300 + side * 60, 640), (300 + side * 34, 540)]
        cv.poly(pts, JACKET, LINE)
        # 襟
        cv.poly([(300 + side * 36, 470), (300 + side * 90, 500), (300 + side * 110, 560), (300 + side * 56, 620),
                 (300 + side * 40, 540)], JACKET, LINE)
        # 影
        cv.poly([(300 + side * 70, 640), (300 + side * 110, 580), (300 + side * 140, 800), (300 + side * 70, 800)],
                JACKET_SH)
        cv.line([(300 + side * 200, 640), (300 + side * 230, 800)], JACKET_SH, 3)
    # 赤いライン
    cv.line([(470, 660), (560, 640)], (215, 70, 60), 5, smooth=False)
    cv.line([(470, 676), (560, 656)], (40, 40, 48), 3, smooth=False)


def back_hair(cv):
    pts = [(214, 280), (200, 200), (230, 140), (300, 112), (370, 140), (400, 200), (388, 290), (372, 330),
           (228, 330)]
    cv.poly(catmull(pts, 8), HAIR, LINE)


def face(cv, expr):
    f = catmull(FACE, 10)
    cv.poly(f, SKIN, LINE, 2.4)
    # 耳
    for side in (-1, 1):
        ex = 300 + side * 78
        cv.poly(catmull([(ex, 300), (ex + side * 14, 305), (ex + side * 16, 330), (ex + side * 4, 352), (ex, 350)], 6),
                SKIN, LINE, 2)
    # ピアス（右耳に複数）
    for dy in (338, 350):
        cv.ellipse(391, dy, 3.2, 3.2, (40, 40, 45))
    cv.ellipse(388, 326, 2.6, 2.6, (200, 200, 210), LINE, 1)
    # 前髪の影（おでこ）
    sh = cv.layer()
    sh.poly(catmull([(224, 250), (260, 300), (300, 280), (340, 300), (376, 250), (376, 230), (224, 230)], 8), SKIN_SH)
    shape = cv.layer()
    shape.poly(f, (0, 0, 0))
    cv.paste(clip_to(sh, shape))
    # あご下の影は首側に。ほっぺ
    for side in (-1, 1):
        blush = Image.new("RGBA", (CW * SS, CH * SS), (0, 0, 0, 0))
        bd = ImageDraw.Draw(blush)
        cx, cy = 300 + side * 52, 376
        bd.ellipse([(cx - 20) * SS, (cy - 8) * SS, (cx + 20) * SS, (cy + 8) * SS], fill=(255, 150, 150, 110))
        blush = blush.filter(ImageFilter.GaussianBlur(4 * SS))
        cv.img.alpha_composite(blush)
    eyes(cv, expr)
    # 鼻
    cv.line([(302, 372), (298, 384), (304, 386)], (205, 150, 130), 1.6)
    mouth(cv, expr)


def eye_open(cv, cx, side, lower=0.0):
    """アニメ風の目。lower: 上まぶたを下げる量（真剣な顔）"""
    top = 318 + lower
    # 白目
    white = catmull([(cx - 26 * side, 338), (cx - 14 * side, top + 4), (cx + 12 * side, top + 2),
                     (cx + 26 * side, 334), (cx + 10 * side, 356), (cx - 14 * side, 356)], 8)
    cv.poly(white, (255, 255, 255))
    # 虹彩（上が暗く下が明るいグラデーション）
    ir = cv.layer()
    for k in range(20):
        t = k / 19
        col = tuple(int(IRIS_TOP[i] * (1 - t) + IRIS_BOT[i] * t) for i in range(3))
        ir.d.rectangle([(cx - 16) * SS, (318 + t * 40) * SS, (cx + 16) * SS, (320 + t * 40 + 3) * SS], fill=col)
    oval = cv.layer()
    oval.ellipse(cx, 338, 15, 20, (0, 0, 0))
    ir = clip_to(ir, oval)
    ir.ellipse(cx, 335, 7, 10, (60, 30, 15))
    ir.ellipse(cx, 338, 15, 20, None, (80, 45, 20), 1.6)
    wshape = cv.layer()
    wshape.poly(white, (0, 0, 0))
    cv.paste(clip_to(ir, wshape))
    # ハイライト
    cv.ellipse(cx - 6 * side + 2, 328 + lower * 0.5, 4.5, 5.5, (255, 255, 255))
    cv.ellipse(cx + 6 * side, 346, 2.2, 2.2, (255, 255, 255))
    # 上まつげ（太い）
    cv.line([(cx - 28 * side, 336), (cx - 16 * side, top), (cx + 8 * side, top - 3), (cx + 28 * side, top + 12)],
            (45, 25, 20), 4.2)
    cv.line([(cx + 28 * side, top + 12), (cx + 33 * side, top + 16)], (45, 25, 20), 2.2, smooth=False)
    # 下まつげ（細い）
    cv.line([(cx - 14 * side, 357), (cx + 4 * side, 358), (cx + 20 * side, 352)], (120, 70, 55), 1.4)
    # 二重
    cv.line([(cx - 12 * side, top - 7), (cx + 10 * side, top - 9), (cx + 24 * side, top + 1)], (190, 130, 110), 1.2)


def eyes(cv, expr):
    for side, cx in ((-1, 262), (1, 338)):
        if expr == "laugh":
            cv.line([(cx - 24, 344), (cx - 8, 330), (cx + 8, 330), (cx + 24, 344)], (45, 25, 20), 4)
            cv.line([(cx - 20, 360), (cx - 10, 364)], (230, 120, 120), 1.6, smooth=False)
            cv.line([(cx - 6, 360), (cx + 4, 364)], (230, 120, 120), 1.6, smooth=False)
        else:
            eye_open(cv, cx, side, lower=7 if expr == "serious" else 0)
        # 眉
        if expr == "serious":
            cv.line([(cx - 26 * side, 300), (cx - 4 * side, 304), (cx + 20 * side, 312)], (120, 75, 50), 3.2)
        elif expr == "laugh":
            cv.line([(cx - 24 * side, 300), (cx, 292), (cx + 22 * side, 296)], (120, 75, 50), 2.6)
        else:
            cv.line([(cx - 24 * side, 302), (cx, 296), (cx + 22 * side, 300)], (120, 75, 50), 2.6)


def mouth(cv, expr):
    if expr == "laugh":
        m = catmull([(276, 402), (300, 404), (324, 402), (316, 422), (300, 428), (284, 422)], 8)
        cv.poly(m, (160, 50, 60), LINE, 2)
        cv.poly([(282, 404), (318, 404), (316, 410), (284, 410)], (255, 255, 255))
        cv.ellipse(300, 422, 10, 5, (240, 110, 120))
    elif expr == "serious":
        cv.line([(286, 410), (300, 408), (314, 410)], (150, 80, 70), 2)
    else:
        cv.line([(286, 404), (300, 410), (314, 404)], (150, 80, 70), 2)


def bangs(cv):
    """センター分けの前髪（毛束を重ねる）"""
    cap = catmull([(216, 300), (210, 220), (238, 146), (300, 116), (362, 146), (390, 220), (384, 300),
                   (356, 262), (300, 246), (244, 262)], 8)
    cv.poly(cap, HAIR, LINE, 2)
    col_layers = []
    left = [
        ([(296, 150), (268, 200), (254, 260), (252, 312)], 22),
        ([(292, 170), (282, 220), (280, 270), (286, 306)], 14),
        ([(280, 150), (240, 180), (222, 240), (220, 310), (228, 346)], 20),
        ([(270, 140), (228, 170), (210, 230), (208, 300)], 18),
    ]
    right = [([(600 - x, y) for x, y in c], w) for c, w in left]
    right[1] = ([(308, 170), (318, 220), (322, 268), (316, 300)], 14)
    for center, w in left + right:
        pts = strand(center, w)
        cv.poly(pts, HAIR, LINE, 1.8)
    # 毛先の外はね
    for side in (-1, 1):
        base = 300 + side * 92
        cv.poly(strand([(base, 300), (base + side * 10, 330), (base + side * 26, 342)], 10), HAIR, LINE, 1.8)
    # 影とツヤ
    for side in (-1, 1):
        cv.line([(300 + side * 6, 158), (300 + side * 30, 200), (300 + side * 44, 260)], HAIR_SH, 3)
        cv.line([(300 + side * 40, 150), (300 + side * 64, 176), (300 + side * 80, 214)], HAIR_HI, 5)
    # つむじのライン
    cv.line([(300, 118), (300, 160)], HAIR_SH, 2.2, smooth=False)


def draw_kagami(expr="normal"):
    cv = Canvas()
    back_hair(cv)
    body(cv)
    face(cv, expr)
    bangs(cv)
    return cv.result()


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "kagami_test.png"
    sheet = Image.new("RGB", (CW * 3, CH), (236, 234, 244))
    for i, e in enumerate(["normal", "serious", "laugh"]):
        im = draw_kagami(e)
        sheet.paste(im, (i * CW, 0), im)
    sheet.save(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
