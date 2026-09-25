"""レトロゲーム風「TRPGって？」30秒アニメーションを、プログラムだけで生成する。

絵・動き・効果音はすべてこのファイルのコードで作る（外部素材なし）。
320x180 で描いて 6 倍に最近傍拡大 → 1920x1080 / 30fps の mp4 を書き出す。

使い方:
    python3 trpg_video.py            # trpg_video.mp4 を書き出す
    python3 trpg_video.py --stills   # 確認用の静止画だけ書き出す
"""
import math
import os
import random
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG = "ffmpeg"

W, H = 320, 180
SCALE = 6
FPS = 30
DURATION = 30.0
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = "/usr/share/fonts/opentype/unifont/unifont_jp.otf"
FONT = ImageFont.truetype(FONT_PATH, 16)

# ---------------------------------------------------------------- パレット(16色)
PAL = [
    (0, 0, 0), (29, 43, 83), (126, 37, 83), (0, 135, 81),
    (171, 82, 54), (95, 87, 79), (194, 195, 199), (255, 241, 232),
    (255, 0, 77), (255, 163, 0), (255, 236, 39), (0, 228, 54),
    (41, 173, 255), (131, 118, 156), (255, 119, 168), (255, 204, 170),
]
BLACK, NAVY, PLUM, DGREEN, BROWN, DGRAY, LGRAY, WHITE = range(8)
RED, ORANGE, YELLOW, GREEN, BLUE, LAV, PINK, PEACH = range(8, 16)


def C(i):
    return PAL[i]


# ---------------------------------------------------------------- スプライト
def sprite(rows, cmap):
    h, w = len(rows), len(rows[0])
    assert all(len(r) == w for r in rows), rows
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = im.load()
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch != ".":
                px[x, y] = C(cmap[ch]) + (255,)
    return im


GIRL_ROWS = [
    "....kkkkkkkk.rr.",
    "..kkhhhhhhhhkrrr",
    ".khhhhhhhhhhhkr.",
    ".khhhhhhhhhhhhk.",
    "khhhhhhhhhhhhhhk",
    "khhhshhhhhhshhhk",
    "khsssssssssssshk",
    "khsswksssswksshk",
    "khsskksssskksshk",
    "khpssssssssssphk",
    "khhsssskksssshhk",
    ".khhksssssskhhk.",
    ".khkkddwwddkkhk.",
    "..kddddrrddddk..",
    ".kddddddddddddk.",
    "ksskddddddddkssk",
    "kssddddddddddssk",
    ".kkddddddddddkk.",
    "..kddddddddddk..",
    ".kddddddddddddk.",
    ".kkkkkkkkkkkkkk.",
    "...kssk..kssk...",
    "...kssk..kssk...",
    "..kbbbk..kbbbk..",
]
# まばたき：目の2行を閉じ目に
GIRL_BLINK = list(GIRL_ROWS)
GIRL_BLINK[7] = "khsssssssssssshk"
GIRL_BLINK[8] = "khsskksssskksshk"
# ばんざい：腕を上げる
GIRL_CHEER = list(GIRL_ROWS)
GIRL_CHEER[10] = "khhsssskksssshhk"
GIRL_CHEER[12] = ".khkkddwwddkkhk."
GIRL_CHEER[15] = ".kddddddddddddk."
GIRL_CHEER[16] = ".kddddddddddddk."

GIRL_ROWS = [".." + r + ".." for r in GIRL_ROWS]
GIRL_BLINK = [".." + r + ".." for r in GIRL_BLINK]
GIRL_CHEER = [".." + r + ".." for r in GIRL_CHEER]
# 両腕を頭の横まで上げる
for _y, _l, _r in [(5, "kk", "kk"), (6, "ss", "ss"), (7, "ss", "ss"), (8, "ks", "sk"),
                   (9, "ks", "sk"), (10, "ks", "sk"), (11, "ks", "sk"), (12, ".k", "k."),
                   (13, "..", "..")]:
    _row = GIRL_CHEER[_y]
    GIRL_CHEER[_y] = _l + _row[2:18] + _r

GIRL_CMAP = dict(k=BLACK, h=BROWN, s=PEACH, r=RED, d=BLUE, w=WHITE, p=PINK, b=BROWN)


def make_person(hair, dress, ribbon):
    cm = dict(GIRL_CMAP, h=hair, d=dress, r=ribbon)
    return {
        "idle": sprite(GIRL_ROWS, cm),
        "blink": sprite(GIRL_BLINK, cm),
        "cheer": sprite(GIRL_CHEER, cm),
    }


GIRL = make_person(BROWN, BLUE, RED)
# 最後に見て喜ぶ人たち（主人公とは別の人）
VIEWERS = [
    make_person(BLACK, GREEN, YELLOW),
    make_person(ORANGE, PINK, BLUE),
    make_person(LAV, ORANGE, GREEN),
]

ROBOT_ROWS = [
    ".........yy.........",
    ".........kk.........",
    "......kkkkkkkk......",
    "....kkggggggggkk....",
    "...kggggggggggggk...",
    "...kgkkkkkkkkkkgk...",
    "...kgkeekkkkeekgk...",
    "...kgkeekkkkeekgk...",
    "...kgkkkkkkkkkkgk...",
    "...kggggkkkkggggk...",
    "....kkkkkkkkkkkk....",
    ".kk.kllllllllllk.kk.",
    "kggkllkkkkkkkllkkggk",
    "kggklllrryyblllkkggk",
    "kggkllllllllllllkggk",
    ".kk.kllllllllllk.kk.",
    "....kllllllllllk....",
    "....kkkkkkkkkkkk....",
    ".....kgggk.kgggk....",
    ".....kgggk.kgggk....",
    "....kkkkkk.kkkkkk...",
    "....kkkkkk.kkkkkk...",
]
ROBOT_CMAP = dict(k=BLACK, g=LGRAY, e=BLUE, l=LGRAY, r=RED, y=YELLOW, b=GREEN)
ROBOT = sprite(ROBOT_ROWS, ROBOT_CMAP)
ROBOT_LIT = sprite(ROBOT_ROWS, dict(ROBOT_CMAP, e=GREEN, y=ORANGE))

BULB = sprite([
    "...kkkk...",
    "..kyyyyk..",
    ".kyywyyyk.",
    "kyywyyyyyk",
    "kyyyyyyyyk",
    "kyyyyyyyyk",
    ".kyyyyyyk.",
    "..kyyyyk..",
    "...kggk...",
    "...kggk...",
    "...kkkk...",
], dict(k=BLACK, y=YELLOW, w=WHITE, g=LGRAY))
BULB_OFF = sprite([
    "...kkkk...",
    "..kddddk..",
    ".kddwdddk.",
    "kddwdddddk",
    "kddddddddk",
    "kddddddddk",
    ".kddddddk.",
    "..kddddk..",
    "...kggk...",
    "...kggk...",
    "...kkkk...",
], dict(k=BLACK, d=DGRAY, w=LGRAY, g=LGRAY))

HEART = sprite([
    ".kk.kk.",
    "kppkppk",
    "kppppwk",
    "kpppppk",
    ".kpppk.",
    "..kpk..",
    "...k...",
], dict(k=BLACK, p=RED, w=WHITE))

# カードの絵（TRPG っぽい4枚 + はずれ1枚）
ICON_DRAGON = sprite([
    "............",
    ".......gg...",
    "..g...gggg..",
    ".ggg.gggkgg.",
    "gggggggggggr",
    ".gggggggg...",
    "..gggggggg..",
    "..ggyyyygg..",
    ".gg.yyyy.gg.",
    ".g..g..g..g.",
    "....g..g....",
    "............",
], dict(g=GREEN, k=BLACK, r=RED, y=YELLOW))
ICON_DICE = sprite([
    "............",
    "..kkkkkkkk..",
    ".kwwwwwwwwk.",
    ".kwrwwwwwwk.",
    ".kwwwwwwwwk.",
    ".kwwwwrwwwk.",
    ".kwwwwwwwwk.",
    ".kwwwwwwrwk.",
    ".kwwwwwwwwk.",
    "..kkkkkkkk..",
    "............",
    "............",
], dict(k=BLACK, w=WHITE, r=RED))
ICON_SWORD = sprite([
    "..........w.",
    ".........ww.",
    "........ww..",
    ".......ww...",
    "......ww....",
    ".....ww.....",
    "..y.ww......",
    "...yw.......",
    "...by.......",
    "..b..y......",
    ".b..........",
    "............",
], dict(w=WHITE, y=YELLOW, b=BROWN))
ICON_CHEST = sprite([
    "............",
    "............",
    "..bbbbbbbb..",
    ".bbbbbbbbbb.",
    ".bybbbbbbyb.",
    ".yyyyyyyyyy.",
    ".bbbbyybbbb.",
    ".bybbyybbyb.",
    ".bbbbbbbbbb.",
    ".yyyyyyyyyy.",
    "............",
    "............",
], dict(b=BROWN, y=YELLOW))
ICON_BLUR = sprite([
    "............",
    "..gg....ll..",
    ".glg..llgl..",
    "..g.lgl..g..",
    ".l..gg..lg..",
    "..lg..gl....",
    ".g..lg..gl..",
    "..gl..lg..l.",
    ".l..g..l.g..",
    "..gl..g.l...",
    "....lg..g...",
    "............",
], dict(g=DGRAY, l=LAV))

CARD_ICONS = [ICON_DICE, ICON_DRAGON, ICON_BLUR, ICON_SWORD, ICON_CHEST]
CARD_BG = [BLUE, NAVY, DGRAY, PLUM, DGREEN]
GOOD = [True, True, False, True, True]


def make_card(icon, bg):
    cw, ch = 26, 32
    im = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, cw - 1, ch - 1], fill=C(BLACK))
    d.rectangle([1, 1, cw - 2, ch - 2], fill=C(WHITE))
    d.rectangle([3, 3, cw - 4, ch - 4], fill=C(bg))
    im.alpha_composite(icon, ((cw - icon.width) // 2, (ch - icon.height) // 2))
    return im


CARDS = [make_card(i, b) for i, b in zip(CARD_ICONS, CARD_BG)]

# ---------------------------------------------------------------- 描画ヘルパ
_text_cache = {}


def text_mask(s):
    if s not in _text_cache:
        l, t, r, b = FONT.getbbox(s)
        im = Image.new("L", (max(r, 1) + 1, 17), 0)
        d = ImageDraw.Draw(im)
        d.fontmode = "1"
        d.text((0, 0), s, font=FONT, fill=255)
        _text_cache[s] = im
    return _text_cache[s]


def text_width(s):
    return FONT.getbbox(s)[2] if s else 0


def draw_text(img, x, y, s, color, scale=1, outline=None, shadow=None):
    m = text_mask(s)
    if scale != 1:
        m = m.resize((m.width * scale, m.height * scale), Image.NEAREST)
    if outline is not None:
        sol = Image.new("RGB", m.size, C(outline))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx or dy:
                    img.paste(sol, (x + dx, y + dy), m)
    if shadow is not None:
        img.paste(Image.new("RGB", m.size, C(shadow)), (x + scale, y + scale), m)
    img.paste(Image.new("RGB", m.size, C(color)), (x, y), m)


def put(img, spr, x, y, scale=1):
    if scale != 1:
        spr = spr.resize((spr.width * scale, spr.height * scale), Image.NEAREST)
    img.paste(spr, (int(round(x)), int(round(y))), spr)


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def clamp01(t):
    return max(0.0, min(1.0, t))


def blinking(t, seed=0):
    """時々まばたきする"""
    p = (t + seed * 1.3) % 2.6
    return p < 0.12


# ---------------------------------------------------------------- 会話ウィンドウ
CPS = 14.0  # 1秒あたりの文字数
WIN = (6, 128, 313, 175)


def draw_window(img, lines, t_start, t):
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = WIN
    d.rectangle([x0, y0, x1, y1], fill=C(BLACK))
    d.rectangle([x0 + 1, y0 + 1, x1 - 1, y1 - 1], outline=C(WHITE))
    d.rectangle([x0 + 4, y0 + 4, x1 - 4, y1 - 4], outline=C(WHITE))
    n = int(max(0.0, t - t_start) * CPS)
    ty = y0 + 7
    shown_all = True
    for line in lines:
        part = line[:max(0, n)]
        if len(part) < len(line):
            shown_all = False
        if part:
            draw_text(img, x0 + 10, ty, part, WHITE)
        n -= len(line)
        ty += 18
    # 全部出たら ▼ を点滅
    if shown_all and int(t * 3) % 2 == 0:
        cx, cy = x1 - 14, y1 - 12
        d.polygon([(cx, cy), (cx + 6, cy), (cx + 3, cy + 3)], fill=C(WHITE))


def char_times(lines, t_start):
    """1文字ずつの表示時刻（効果音用）"""
    out = []
    i = 0
    for line in lines:
        for ch in line:
            if ch not in " 　":
                out.append(t_start + i / CPS)
            i += 1
    return out


def draw_stage_label(img, label):
    w = text_width(label)
    d = ImageDraw.Draw(img)
    d.rectangle([3, 3, 3 + w + 9, 3 + 21], fill=C(BLACK))
    d.rectangle([4, 4, 3 + w + 8, 3 + 20], outline=C(YELLOW))
    draw_text(img, 8, 6, label, YELLOW)


# ---------------------------------------------------------------- 場面の設定
TITLE_END = 4.0
SCENES = [
    # (開始, 終了, 描画関数名, ラベル, 字幕行)
    (0.0, 4.0, "title", None, None),
    (4.0, 9.0, "plan", "STAGE 1", ["TRPGの楽しさ、どう伝える？", "まずは「企画」を思いつこう！"]),
    (9.0, 14.0, "memo", "STAGE 2", ["思いを言葉にしてメモに書く。", "だれに・雰囲気・伝えたいこと"]),
    (14.0, 19.0, "robot", "STAGE 3", ["AIロボに頼んで", "冒険の絵をつくってもらおう！"]),
    (19.0, 24.0, "select", "STAGE 4", ["いい絵を選んで、つなげると", "ひとつの物語になる！"]),
    (24.0, 30.0, "clear", "STAGE CLEAR", ["見た人の心が動いたら、完成です"]),
]
TEXT_DELAY = 0.55  # 場面開始から字幕が出始めるまで
TRANS = 0.4  # ブロック遷移（閉じ／開き）の長さ


# ---------------------------------------------------------------- 背景
def stars(img, t, seed=1, n=40, ymax=110):
    rnd = random.Random(seed)
    px = img.load()
    for i in range(n):
        x, y = rnd.randrange(W), rnd.randrange(ymax)
        ph = rnd.random() * 6
        if math.sin(t * 4 + ph) > -0.3:
            px[x, y] = C(WHITE if i % 3 else YELLOW)


def room_bg(img, wall=NAVY, floor=BROWN):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 104], fill=C(wall))
    # 壁の模様（チェック）
    for y in range(0, 104, 16):
        for x in range((y // 16 % 2) * 16, W, 32):
            d.rectangle([x, y, x + 15, y + 15], fill=C(PLUM if wall == NAVY else wall))
    d.rectangle([0, 104, W, 127], fill=C(floor))
    for x in range(0, W, 20):
        d.line([x, 104, x - 8, 127], fill=C(BLACK))
    d.line([0, 104, W, 104], fill=C(BLACK))


def draw_girl(img, x, y, t, pose="idle", seed=0, person=None):
    p = person or GIRL
    spr = p[pose]
    if pose == "idle" and blinking(t, seed):
        spr = p["blink"]
    put(img, spr, x - 4, y, 2)  # 腕用の左右2pxの余白ぶん戻す


# ---------------------------------------------------------------- 各場面
def scene_title(img, t):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, H], fill=C(NAVY))
    stars(img, t, seed=3, n=60, ymax=130)
    # 月
    d.ellipse([290, 30, 310, 50], fill=C(YELLOW))
    d.ellipse([297, 26, 317, 46], fill=C(NAVY))
    # 城のシルエット
    d.rectangle([0, 138, W, H], fill=C(DGREEN))
    for bx, bw, bh in [(20, 26, 40), (44, 40, 28), (84, 22, 48), (230, 22, 46), (252, 44, 30), (296, 24, 38)]:
        d.rectangle([bx, 138 - bh, bx + bw, 138], fill=C(BLACK))
        for k in range(bx, bx + bw, 6):
            d.rectangle([k, 138 - bh - 4, k + 2, 138 - bh], fill=C(BLACK))
    # 窓の灯り
    for wx, wy in [(92, 104), (238, 106), (30, 110)]:
        d.rectangle([wx, wy, wx + 3, wy + 5], fill=C(ORANGE))
    # タイトル（落ちてきて止まる）
    title = "TRPGって？"
    tw = text_width(title) * 3
    ty = 14 - int((1 - ease_out(t / 0.8)) * 70)
    draw_text(img, (W - tw) // 2, ty, title, YELLOW, scale=3, outline=BLACK, shadow=ORANGE)
    sub = "〜 みんなで物語をつくる遊び 〜"
    if t > 0.9:
        draw_text(img, (W - text_width(sub)) // 2, 66, sub, WHITE, outline=BLACK)
    # サイコロと主人公
    draw_girl(img, 144, 138 - 48, t)
    dy = int(abs(math.sin(t * 5)) * 6)
    put(img, ICON_DICE, 186, 138 - 24 - dy, 2)
    put(img, ICON_DRAGON, 96, 138 - 26 - int(abs(math.sin(t * 5 + 1.5)) * 4), 2)
    # PRESS START
    pressed = t >= 2.9
    rate = 12 if pressed else 2.5
    if int(t * rate) % 2 == 0:
        s = "PRESS START"
        draw_text(img, (W - text_width(s)) // 2, 152, s, WHITE, outline=BLACK)


def scene_plan(img, t):
    room_bg(img)
    d = ImageDraw.Draw(img)
    # 机と本棚
    d.rectangle([220, 52, 290, 104], fill=C(BROWN))
    d.rectangle([220, 52, 290, 104], outline=C(BLACK))
    for i, col in enumerate([RED, GREEN, BLUE, YELLOW, LAV, ORANGE]):
        d.rectangle([224 + i * 10, 58, 231 + i * 10, 76], fill=C(col))
        d.rectangle([224 + i * 10, 58, 231 + i * 10, 76], outline=C(BLACK))
    d.line([220, 78, 290, 78], fill=C(BLACK))
    put(img, ICON_DICE, 232, 84)
    put(img, ICON_SWORD, 256, 84)
    gx, gy = 144, 56
    lit = t >= 1.6
    pose = "cheer" if lit and t < 3.8 else "idle"
    hop = -int(abs(math.sin((t - 1.6) * 8)) * 4) if 1.6 <= t < 2.2 else 0
    draw_girl(img, gx, gy + hop, t, pose)
    # 考え中 … → 電球ピカッ
    bx, by = gx + 6, gy - 40 + hop
    if not lit:
        dots = int(t * 3) % 4
        for i in range(dots):
            d.rectangle([gx + 8 + i * 6, gy - 8, gx + 10 + i * 6, gy - 6], fill=C(WHITE))
        if t > 0.8:
            put(img, BULB_OFF, bx, by, 2)
    else:
        # 光の線
        k = (t - 1.6)
        cx, cy = bx + 10, by + 10
        rlen = 14 + int(3 * math.sin(k * 10))
        for a in range(8):
            ang = a * math.pi / 4 + k * 0.8
            x0 = cx + math.cos(ang) * 14
            y0 = cy + math.sin(ang) * 14
            x1 = cx + math.cos(ang) * (rlen + 8)
            y1 = cy + math.sin(ang) * (rlen + 8)
            d.line([x0, y0, x1, y1], fill=C(YELLOW if a % 2 else WHITE), width=2)
        put(img, BULB, bx, by, 2)


def scene_memo(img, t):
    room_bg(img, wall=DGREEN, floor=BROWN)
    d = ImageDraw.Draw(img)
    draw_girl(img, 36, 56, t, "idle")
    # メモ用紙
    mx0, my0, mx1, my1 = 106, 16, 300, 118
    d.rectangle([mx0 + 3, my0 + 3, mx1 + 3, my1 + 3], fill=C(BLACK))
    d.rectangle([mx0, my0, mx1, my1], fill=C(WHITE))
    d.rectangle([mx0, my0, mx1, my1], outline=C(BLACK))
    d.rectangle([mx0, my0, mx1, my0 + 18], fill=C(PINK))
    d.rectangle([mx0, my0, mx1, my0 + 18], outline=C(BLACK))
    draw_text(img, mx0 + 6, my0 + 1, "MEMO", WHITE)
    for i in range(3):
        yy = my0 + 22 + i * 28
        d.line([mx0 + 6, yy + 19, mx1 - 6, yy + 19], fill=C(LGRAY))
    items = ["だれに", "雰囲気", "伝えたいこと"]
    pen = None
    for i, head in enumerate(items):
        t0 = 1.0 + i * 1.0
        yy = my0 + 22 + i * 28
        n = int(max(0.0, t - t0) * 10)
        s = "「" + head + "」"
        part = s[:n]
        if part:
            draw_text(img, mx0 + 26, yy, part, NAVY)
        if n > 0:
            # チェックボックス
            d.rectangle([mx0 + 8, yy + 3, mx0 + 18, yy + 13], outline=C(BLACK))
            if n >= len(s):
                d.line([mx0 + 9, yy + 8, mx0 + 12, yy + 11], fill=C(RED), width=2)
                d.line([mx0 + 12, yy + 11, mx0 + 18, yy + 2], fill=C(RED), width=2)
        if 0 < n < len(s) + 1:
            pen = (mx0 + 26 + text_width(part), yy)
    if pen:
        px, py = pen
        wob = int(math.sin(t * 30) * 2)
        d.line([px + 2, py + 12 + wob, px + 14, py - 4 + wob], fill=C(YELLOW), width=3)
        d.line([px + 2, py + 12 + wob, px + 4, py + 9 + wob], fill=C(BLACK), width=2)


ROBOT_POS = (218, 60)
CARD_SLOTS = [(20 + i * 30, 88) for i in range(5)]


def card_fly(i, t):
    """STAGE3 のカードの位置（ロボットの口から飛び出して並ぶ）"""
    t0 = 1.2 + i * 0.55
    rx, ry = ROBOT_POS[0] + 14, ROBOT_POS[1] + 22
    tx, ty = 58 + i * 30, 34
    k = clamp01((t - t0) / 0.45)
    if t < t0:
        return None
    e = ease_out(k)
    x = rx + (tx - rx) * e
    y = ry + (ty - ry) * e - math.sin(k * math.pi) * 30
    return x, y


def scene_robot(img, t):
    room_bg(img, wall=NAVY, floor=DGRAY)
    d = ImageDraw.Draw(img)
    # 研究所っぽいパネル
    for i in range(4):
        col = GREEN if int(t * 4 + i) % 3 else RED
        d.rectangle([290, 20 + i * 12, 296, 26 + i * 12], fill=C(col))
    draw_girl(img, 14, 56, t, "cheer" if t > 2.0 else "idle")
    working = 0.9 < t < 4.2
    shake = int(math.sin(t * 40)) if working else 0
    put(img, ROBOT_LIT if working and int(t * 8) % 2 else ROBOT, ROBOT_POS[0] + shake, ROBOT_POS[1] - 8, 2)
    # ふきだし
    if 0.5 < t < 1.2:
        draw_text(img, ROBOT_POS[0] + 8, ROBOT_POS[1] - 30, "ピピッ", WHITE, outline=BLACK)
    for i in range(5):
        p = card_fly(i, t)
        if p:
            put(img, CARDS[i], p[0], p[1])
            # 出たての瞬間キラッ
            k = t - (1.2 + i * 0.55 + 0.45)
            if 0 <= k < 0.25:
                cx, cy = int(p[0]) + 13, int(p[1]) - 4
                d.line([cx - 4, cy, cx + 4, cy], fill=C(WHITE))
                d.line([cx, cy - 4, cx, cy + 4], fill=C(WHITE))


SELECT_TIMES = [1.1, 1.6, 2.1, 2.6, 3.1]  # カーソルが各カードに乗る時刻


def scene_select(img, t):
    room_bg(img, wall=PLUM, floor=BROWN)
    d = ImageDraw.Draw(img)
    # 並んだカード（STAGE3 から続く位置）
    base = [(58 + i * 30, 34) for i in range(5)]
    connect_t = 3.4
    k = ease_out((t - connect_t) / 0.7)
    good_idx = [i for i in range(5) if GOOD[i]]
    # フィルム帯
    if t >= connect_t:
        fx0 = 64
        d.rectangle([fx0 - 6, 28, fx0 + 4 * 36 + 20, 72], fill=C(BLACK))
        for x in range(fx0 - 4, fx0 + 4 * 36 + 20, 8):
            d.rectangle([x, 30, x + 3, 33], fill=C(LGRAY))
            d.rectangle([x, 67, x + 3, 70], fill=C(LGRAY))
    for i in range(5):
        x, y = base[i]
        chosen = GOOD[i] and t >= SELECT_TIMES[i]
        if not GOOD[i] and t >= SELECT_TIMES[i]:
            # はずれは「×」が付いて落ちていく
            fall = t - SELECT_TIMES[i] - 0.3
            if fall > 0:
                y += fall * fall * 200
                if y > 130:
                    continue
            put(img, CARDS[i], x, y)
            d.line([x + 4, y + 6, x + 22, y + 26], fill=C(RED), width=3)
            d.line([x + 22, y + 6, x + 4, y + 26], fill=C(RED), width=3)
            continue
        if t >= connect_t and GOOD[i]:
            j = good_idx.index(i)
            tx, ty = 64 + j * 36 + 4, 34
            x = x + (tx - x) * k
            y = y + (ty - y) * k
        put(img, CARDS[i], x, y)
        if chosen and t < connect_t:
            d.rectangle([x - 2, y - 2, x + 27, y + 33], outline=C(YELLOW))
    # 矢印でつなぐ
    if k >= 1:
        for j in range(3):
            ax = 64 + j * 36 + 4 + 27
            ay = 50
            if int(t * 4) % 2 == 0 or t > connect_t + 1.2:
                d.polygon([(ax + 1, ay - 3), (ax + 7, ay), (ax + 1, ay + 3)], fill=C(YELLOW))
    # カーソル（▶）
    if SELECT_TIMES[0] - 0.3 <= t < connect_t:
        idx = 0
        for i, st in enumerate(SELECT_TIMES):
            if t >= st - 0.3:
                idx = i
        cx, cy = base[idx][0] + 13, base[idx][1] + 38 + int(abs(math.sin(t * 10)) * 2)
        d.polygon([(cx, cy), (cx - 5, cy + 7), (cx + 5, cy + 7)], fill=C(WHITE))
        d.polygon([(cx, cy), (cx - 5, cy + 7), (cx + 5, cy + 7)], outline=C(BLACK))
    draw_girl(img, 6, 56, t, "cheer" if t > connect_t + 0.8 else "idle")


def scene_clear(img, t):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, H], fill=C(NAVY))
    stars(img, t, seed=9, n=30, ymax=100)
    d.rectangle([0, 104, W, 127], fill=C(DGREEN))
    d.line([0, 104, W, 104], fill=C(BLACK))
    # スクリーン（上映中）
    sx0, sy0, sx1, sy1 = 186, 30, 310, 74
    d.line([sx0 + 30, sy1, sx0 + 22, 104], fill=C(BLACK), width=2)
    d.line([sx1 - 30, sy1, sx1 - 22, 104], fill=C(BLACK), width=2)
    d.rectangle([sx0 - 3, sy0 - 3, sx1 + 3, sy1 + 3], fill=C(LGRAY))
    d.rectangle([sx0 - 3, sy0 - 3, sx1 + 3, sy1 + 3], outline=C(BLACK))
    d.rectangle([sx0, sy0, sx1, sy1], fill=C(BLACK))
    goods = [CARDS[i] for i in range(5) if GOOD[i]]
    for j, c in enumerate(goods):
        put(img, c, sx0 + 4 + j * 30, sy0 + 6)
    # 紙吹雪
    rnd = random.Random(5)
    if t > 0.3:
        for n in range(40):
            x = (rnd.randrange(W) + int(math.sin(t * 2 + n) * 6)) % W
            y = (rnd.random() * 130 + (t - 0.3) * (30 + rnd.random() * 30)) % 128
            col = [RED, YELLOW, GREEN, BLUE, PINK, ORANGE][n % 6]
            d.rectangle([x, int(y), x + 1, int(y) + 1], fill=C(col))

    # 主人公と見た人たち
    happy = t > 0.6
    people = [(12, GIRL), (54, VIEWERS[0]), (96, VIEWERS[1]), (138, VIEWERS[2])]
    for n, (vx, per) in enumerate(people):
        jump = int(abs(math.sin(t * 7 + n * 1.3)) * 7) if happy else 0
        draw_girl(img, vx, 56 - jump, t, "cheer" if happy else "idle", seed=n, person=per)
    # ハート（心が動いた！）：頭の上にふわっと浮かぶ
    if happy:
        for n in range(len(people)):
            for k in range(2):
                ph = (t * 0.9 + n * 0.37 + k * 0.5) % 1
                hx = people[n][0] + 12 + (k * 2 - 1) * 10 + int(math.sin(t * 4 + n + k) * 2)
                hy = 44 - ph * 16
                if ph < 0.85:
                    put(img, HEART, hx, hy)

SCENE_FUNCS = dict(title=scene_title, plan=scene_plan, memo=scene_memo,
                   robot=scene_robot, select=scene_select, clear=scene_clear)


# ---------------------------------------------------------------- 画面切り替え
BLOCK = 16
_order = []
for by in range(0, H, BLOCK):
    for bx in range(0, W, BLOCK):
        _order.append((bx, by))
# 左上から右下へ斜めに、少しゆらぎを加えて埋める
_rng = random.Random(7)
_keys = {b: (b[0] / W + b[1] / H) + _rng.random() * 0.35 for b in _order}
_order.sort(key=lambda b: _keys[b])


def draw_blocks(img, frac):
    """frac: 0..1 の割合だけ黒ブロックで埋める"""
    n = int(round(len(_order) * clamp01(frac)))
    d = ImageDraw.Draw(img)
    for bx, by in _order[:n]:
        d.rectangle([bx, by, bx + BLOCK - 1, by + BLOCK - 1], fill=C(BLACK))


# ---------------------------------------------------------------- フレーム
def render(t):
    img = Image.new("RGB", (W, H), C(BLACK))
    for i, (s, e, name, label, lines) in enumerate(SCENES):
        if s <= t < e or (i == len(SCENES) - 1 and t >= s):
            lt = t - s
            SCENE_FUNCS[name](img, lt)
            if lines:
                draw_window(img, lines, TEXT_DELAY, lt)
            if label:
                draw_stage_label(img, label)
            # 開き
            if i > 0 and lt < TRANS:
                draw_blocks(img, 1 - lt / TRANS)
            # 閉じ
            if i < len(SCENES) - 1 and e - t < TRANS:
                draw_blocks(img, 1 - (e - t) / TRANS)
            break
    return img


# ---------------------------------------------------------------- 効果音(8bit)
SR = 44100


def tone(freq, dur, vol=0.2, duty=0.5, kind="square", decay=0.0, slide=0.0):
    n = int(SR * dur)
    tt = np.arange(n) / SR
    f = freq * (1 + slide * tt / max(dur, 1e-6))
    ph = np.cumsum(f) / SR
    if kind == "square":
        w = np.where((ph % 1) < duty, 1.0, -1.0)
    elif kind == "tri":
        w = 4 * np.abs((ph % 1) - 0.5) - 1
    else:  # noise
        rng = np.random.default_rng(int(freq))
        w = rng.choice([-1.0, 1.0], n)
    env = np.ones(n)
    a = min(n, int(SR * 0.004))
    env[:a] = np.linspace(0, 1, a)
    r = min(n, int(SR * 0.012))
    env[-r:] *= np.linspace(1, 0, r)
    if decay:
        env *= np.exp(-tt * decay)
    return (w * env * vol).astype(np.float32)


def note(name):
    names = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6,
             "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
    p, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[p] + (o - 4) * 12 - 9) / 12)


def se_text():
    return tone(1200, 0.03, vol=0.08, duty=0.25)


def se_decide():
    return np.concatenate([tone(note("B5"), 0.05, 0.16, 0.5), tone(note("E6"), 0.11, 0.16, 0.5, decay=8)])


def se_item():
    seq = ["C5", "E5", "G5", "C6", "E6", "G6"]
    parts = [tone(note(s), 0.05, 0.15, 0.25) for s in seq]
    parts.append(tone(note("C7"), 0.25, 0.14, 0.25, decay=6))
    return np.concatenate(parts)


def se_card():
    return np.concatenate([tone(note("G5"), 0.04, 0.12, 0.125),
                           tone(note("D6"), 0.04, 0.12, 0.125),
                           tone(note("G6"), 0.1, 0.12, 0.125, decay=12)])


def se_miss():
    return tone(300, 0.2, 0.12, 0.5, slide=-0.6)


def se_whoosh():
    return tone(3000, 0.35, 0.05, kind="noise", decay=6)


def se_fanfare():
    beat = 0.11
    mel = [("C5", 1), ("E5", 1), ("G5", 1), ("C6", 3),
           ("A5", 1), ("B5", 1), ("C6", 1), ("D6", 3),
           ("E6", 2), ("D6", 1), ("C6", 1), ("E6", 1), ("G6", 6)]
    bass = [("C3", 6), ("F3", 6), ("G3", 5), ("C4", 10)]
    m = np.concatenate([tone(note(n), beat * d, 0.15, 0.5, decay=1.5) for n, d in mel])
    b = np.concatenate([tone(note(n), beat * d, 0.22, kind="tri") for n, d in bass])
    L = max(len(m), len(b))
    out = np.zeros(L, np.float32)
    out[:len(m)] += m
    out[:len(b)] += b
    # ハモリ(3度下)
    h = np.concatenate([tone(note(n) * 0.8409, beat * d, 0.07, 0.25, decay=1.5) for n, d in mel])
    out[:len(h)] += h
    return out


def build_audio(path):
    buf = np.zeros(int(SR * DURATION) + SR, np.float32)

    def add(t, snd):
        i = int(t * SR)
        j = min(len(buf), i + len(snd))
        buf[i:j] += snd[: j - i]

    # タイトル：START 決定
    add(2.9, se_decide())
    for i, (s, e, name, label, lines) in enumerate(SCENES):
        if i < len(SCENES) - 1:
            add(e - TRANS, se_whoosh())
        if lines:
            for ct in char_times(lines, s + TEXT_DELAY):
                add(ct, se_text())
    add(4.0 + 1.6, se_item())  # 電球ピカッ
    for k in range(3):  # メモのチェック
        add(9.0 + 1.0 + k * 1.0 + 0.8, se_decide())
    for i in range(5):  # カードが出てくる
        add(14.0 + 1.2 + i * 0.55 + 0.4, se_card())
    add(14.0 + 1.2 + 4 * 0.55 + 0.7, se_item())
    for i, st in enumerate(SELECT_TIMES):  # 選ぶ
        add(19.0 + st, se_decide() if GOOD[i] else se_miss())
    add(19.0 + 3.4 + 0.7, se_item())  # つながった
    add(24.0 + 0.35, se_fanfare())
    buf = buf[: int(SR * DURATION)]
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
def upscale(img):
    a = np.asarray(img, dtype=np.uint8)
    return np.repeat(np.repeat(a, SCALE, axis=0), SCALE, axis=1)


def write_stills(times, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for t in times:
        Image.fromarray(upscale(render(t))).resize((960, 540), Image.NEAREST) \
            .save(os.path.join(out_dir, f"still_{t:05.2f}.png"))


def main():
    if "--stills" in sys.argv:
        out = sys.argv[sys.argv.index("--stills") + 1] if len(sys.argv) > 2 else "stills"
        times = [1.0, 3.0, 4.2, 6.5, 8.8, 12.8, 17.5, 21.5, 23.5, 27.5]
        write_stills(times, out)
        return
    wav = os.path.join(OUT_DIR, "_trpg_audio.wav")
    mp4 = os.path.join(OUT_DIR, "trpg_video.mp4")
    build_audio(wav)
    cmd = [FFMPEG, "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W * SCALE}x{H * SCALE}", "-r", str(FPS), "-i", "-",
           "-i", wav,
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", mp4]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    total = int(DURATION * FPS)
    for f in range(total):
        p.stdin.write(upscale(render(f / FPS)).tobytes())
    p.stdin.close()
    p.wait()
    os.remove(wav)
    print("wrote", mp4)


if __name__ == "__main__":
    main()
