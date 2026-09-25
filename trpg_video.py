"""レトロゲーム風「TRPGって？」40秒アニメーションを、プログラムだけで生成する。

テーマ：プレイヤーとして「だれか」になりきって遊ぶ TRPG の楽しさ。
絵・動き・効果音はすべてこのファイルのコードで作る（外部素材なし）。
320x180 で描いて 6 倍に最近傍拡大 → 1920x1080 / 30fps の mp4 を書き出す。

使い方:
    python3 trpg_video.py                          # trpg_video.mp4 を書き出す
    python3 trpg_video.py --stills <dir> [秒 ...]  # 確認用の静止画だけ書き出す
"""
import math
import os
import random
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG = "ffmpeg"

W, H = 320, 180
SCALE = 6
FPS = 30
DURATION = 40.0
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
    w = max(len(r) for r in rows)
    im = Image.new("RGBA", (w, len(rows)), (0, 0, 0, 0))
    px = im.load()
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch != ".":
                px[x, y] = C(cmap[ch]) + (255,)
    return im


def pad(rows, n=2):
    return ["." * n + r + "." * n for r in rows]


# 頭（全員共通の顔。髪・リボン・服の色で人を描き分ける）
HEAD = [
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
]
EYES_CLOSED = ("khsssssssssssshk", "khsskksssskksshk")
EYES_HAPPY = ("khsskksssskksshk", "khsksskssksskshk")

# ふだんの服（現実のテーブル）
BODY_CASUAL = [
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
# 剣士のよろい（冒険の世界）
BODY_KNIGHT = [
    ".khkkaayyaakkhk.",
    "..kaaaayyaaaak..",
    ".kcaaaaaaaaaack.",
    "ksskaaaaaaaakssk",
    "ksscaaaayyaacssk",
    ".kkcbbbbbbbbckk.",
    "..kcaaaaaaaack..",
    ".kccaaaaaaaacck.",
    ".kkkkkkkkkkkkkk.",
    "...kaak..kaak...",
    "...kaak..kaak...",
    "..kbbbk..kbbbk..",
]
# 魔法使いのローブ
BODY_WIZARD = [
    ".khkkvvwwvvkkhk.",
    "..kvvvvyvvvvvk..",
    ".kvvvvvvvvvvvvk.",
    "ksskvvvvvvvvkssk",
    "kssvvvvyvvvvvssk",
    ".kkvvvvvvvvvvkk.",
    "..kvvvvvvvvvvk..",
    ".kvvvvvvvvvvvvk.",
    ".kvvvvvvvvvvvvk.",
    ".kkkkkkkkkkkkkk.",
    "....kbbk.kbbk...",
    "....kkkk.kkkk...",
]
WIZ_HAT = [
    "........kk......",
    ".......kvvk.....",
    "......kvvvk.....",
    ".....kvvvvvk....",
    "....kvvyvvvvk...",
    "..kkkyyyyyyyykk.",
]


def arms_up(rows, top):
    """腕をばんざいに（左右2pxの余白に腕を描く）。rows は pad 済み。"""
    rows = list(rows)
    for dy, l, r in [(5, "kk", "kk"), (6, "ss", "ss"), (7, "ss", "ss"), (8, "ks", "sk"),
                     (9, "ks", "sk"), (10, "ks", "sk"), (11, "ks", "sk"), (12, ".k", "k.")]:
        y = top + dy
        rows[y] = l + rows[y][2:18] + r
    # 下がっていた腕を消す
    for dy in (15, 16):
        y = top + dy
        fill = rows[y][2:18][5]
        rows[y] = "...k" + fill * 12 + "k..."
    return rows


def make_person(hair, cloth, ribbon, body=BODY_CASUAL, hat=False, extra=None):
    cm = dict(k=BLACK, h=hair, s=PEACH, r=ribbon, d=cloth, w=WHITE, p=PINK, b=BROWN,
              a=LGRAY, y=YELLOW, c=RED, v=PLUM)
    head = WIZ_HAT + HEAD[2:] if hat else list(HEAD)
    top = 4 if hat else 0  # 帽子で頭が下がる分
    idle = pad(head + body)
    blink = list(idle)
    blink[7 + top] = "..%s.." % EYES_CLOSED[0]
    blink[8 + top] = "..%s.." % EYES_CLOSED[1]
    cheer = arms_up(idle, top)
    happy = list(cheer)
    happy[7 + top] = "..%s.." % EYES_HAPPY[0]
    happy[8 + top] = "..%s.." % EYES_HAPPY[1]
    out = {k: sprite(v, cm) for k, v in
           dict(idle=idle, blink=blink, cheer=cheer, happy=happy).items()}
    if extra:
        for k in out:
            extra(out[k], k)
    return out


SWORD = sprite([
    "..w..",
    ".kwk.",
    ".kwk.",
    ".kwk.",
    ".kwk.",
    ".kwk.",
    ".kwk.",
    "kyyyk",
    ".kbk.",
    ".kbk.",
    "..k..",
], dict(k=BLACK, w=WHITE, y=YELLOW, b=BROWN))


def add_sword(im, pose):
    if pose in ("cheer", "happy"):
        im.alpha_composite(SWORD, (15, 0))
    else:
        im.alpha_composite(SWORD, (15, 7))


# 主人公リナ（現実 / 剣士）…顔と髪型は同じ
RINA = make_person(BROWN, BLUE, RED)
RINA_KNIGHT = make_person(BROWN, BLUE, RED, body=BODY_KNIGHT, extra=add_sword)
# 仲間たち（現実）。1人目は冒険の世界で魔法使いになる
PAL1 = make_person(BLACK, GREEN, YELLOW)
PAL1_WIZ = make_person(BLACK, GREEN, YELLOW, body=BODY_WIZARD, hat=True)
PAL2 = make_person(ORANGE, PINK, BLUE)
GM = make_person(LAV, ORANGE, GREEN)

GUARD = sprite([
    "......rr........",
    ".....rrrr.......",
    "....kkkkkkkk....",
    "...kaaaaaaaak...",
    "..kaaaaaaaaaak..",
    "..kakkkkkkkkak..",
    "..kaksksskskak..",
    "..kaksssssskak..",
    "..kaaaaaaaaaak..",
    ".kaaddddddddaak.",
    "kaaaddddddddaaak",
    "kssaddyyyyddassk",
    "kssaddddddddassk",
    ".kkaddddddddakk.",
    "..kaaaaaaaaaak..",
    "..kaaaakkaaaak..",
    "..kaaak..kaaak..",
    "..kaaak..kaaak..",
    "..kaaak..kaaak..",
    "..kaaak..kaaak..",
    "..kaaak..kaaak..",
    "..kgggk..kgggk..",
    ".kkkkkk..kkkkkk.",
], dict(k=BLACK, a=LGRAY, d=RED, y=YELLOW, s=PEACH, g=DGRAY, r=RED))

DRAGON_ROWS = [
    "..........................kk",
    "........................kkggk",
    "...GG..................kggggk",
    "..GGGG................kggkwgk",
    ".GGGGGG..............kgggkkggkk",
    ".GGGGGGG............kggggggggggk",
    "..GGGGGGG...........kggggggwgwgk",
    "...GGGGGGG.........kgggggkkkkkk",
    "....GGGGGGGk.......kggggk",
    ".....GGGGGGgk.....kgggggk",
    "......GGGGggggkkkkgggggk",
    ".......kggggggggggggggk",
    "......kgggggyyyyyyggggk",
    ".....kggggyyyyyyyyyggk",
    "....kgggggyyyyyyyyyggk",
    "...kggggggyyyyyyyyggk",
    "..kgggk.kgyyyyyyyyggk",
    ".kggk...kggyyyyyygggk",
    "kggk....kgggggggggggk",
    "kgk.....kgggk..kgggk",
    ".k......kgggk..kgggk",
    "........kwkwk..kwkwk",
    "........kkkkk..kkkkk",
]
DRAGON_CMAP = dict(k=BLACK, g=GREEN, G=DGREEN, y=YELLOW, w=WHITE, p=PINK)
# 左向き（主人公たちの方を向く）
DRAGON = ImageOps.mirror(sprite(DRAGON_ROWS, DRAGON_CMAP))
_friendly = list(DRAGON_ROWS)
_friendly[3] = "..GGGG................kggkkgk"   # にっこり目
_friendly[6] = "..GGGGGGG...........kggppggggggk"  # ほっぺ
_friendly[7] = "...GGGGGGG.........kgggggkggggk"   # 口を閉じる
DRAGON_FRIEND = ImageOps.mirror(sprite(_friendly, DRAGON_CMAP))

HEART = sprite([
    ".kk.kk.",
    "kppkppk",
    "kppppwk",
    "kpppppk",
    ".kpppk.",
    "..kpk..",
    "...k...",
], dict(k=BLACK, p=RED, w=WHITE))

BREAD = sprite([
    "..kkkkkk..",
    ".koyoyook.",
    "kooooooook",
    "kyoyoyoyok",
    ".kkkkkkkk.",
], dict(k=BLACK, o=ORANGE, y=YELLOW))

SHEET = sprite([
    "kkkkkkkkkk",
    "kwwwwwwwwk",
    "kwrrwwwwwk",
    "kwwwwwwwwk",
    "kwlllllwwk",
    "kwwwwwwwwk",
    "kwllllwwwk",
    "kwwwwwwwwk",
    "kwlllllwwk",
    "kwwwwwwwwk",
    "kkkkkkkkkk",
], dict(k=BLACK, w=WHITE, r=RED, l=LGRAY))

PIPS = {1: [(1, 1)], 2: [(0, 0), (2, 2)], 3: [(0, 0), (1, 1), (2, 2)],
        4: [(0, 0), (2, 0), (0, 2), (2, 2)], 5: [(0, 0), (2, 0), (1, 1), (0, 2), (2, 2)],
        6: [(0, 0), (0, 1), (0, 2), (2, 0), (2, 1), (2, 2)]}


def die_img(n):
    im = Image.new("RGBA", (15, 15), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 14, 14], fill=C(BLACK))
    d.rectangle([1, 1, 13, 13], fill=C(WHITE))
    for gx, gy in PIPS[n]:
        x, y = 3 + gx * 4, 3 + gy * 4
        if n == 1:
            d.rectangle([x - 1, y - 1, x + 2, y + 2], fill=C(RED))
        else:
            d.rectangle([x, y, x + 1, y + 1], fill=C(BLACK))
    return im


DICE = {n: die_img(n) for n in range(1, 7)}

# ---------------------------------------------------------------- 描画ヘルパ
_text_cache = {}


def text_mask(s):
    if s not in _text_cache:
        im = Image.new("L", (max(text_width(s), 1) + 1, 17), 0)
        d = ImageDraw.Draw(im)
        d.fontmode = "1"
        d.text((0, 0), s, font=FONT, fill=255)
        _text_cache[s] = im
    return _text_cache[s]


def text_width(s):
    return FONT.getbbox(s)[2] if s else 0


def draw_text(img, x, y, s, color, scale=1, outline=None, shadow=None):
    if not s:
        return
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
    return (t + seed * 1.3) % 2.6 < 0.12


def draw_person(img, person, x, y, t, pose="idle", seed=0, scale=2, crop=None):
    """x は体の左端（腕用の余白2pxを除いた位置）"""
    spr = person[pose]
    if pose == "idle" and blinking(t, seed):
        spr = person["blink"]
    if crop:
        spr = spr.crop((0, 0, spr.width, crop))
    put(img, spr, x - 2 * scale, y, scale)


def sparkle(d, x, y, s, col=WHITE):
    d.line([x - s, y, x + s, y], fill=C(col))
    d.line([x, y - s, x, y + s], fill=C(col))


# ---------------------------------------------------------------- 会話ウィンドウ・ふきだし
CPS = 14.0   # 字幕：1秒あたりの文字数
BCPS = 16.0  # ふきだし
WIN = (6, 128, 313, 175)


def typed(lines, t_start, t, cps):
    n = int(max(0.0, t - t_start) * cps)
    out = []
    for line in lines:
        out.append(line[:max(0, n)])
        n -= len(line)
    return out, n >= 0


def draw_window(img, lines, t_start, t):
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = WIN
    d.rectangle([x0, y0, x1, y1], fill=C(BLACK))
    d.rectangle([x0 + 1, y0 + 1, x1 - 1, y1 - 1], outline=C(WHITE))
    d.rectangle([x0 + 4, y0 + 4, x1 - 4, y1 - 4], outline=C(WHITE))
    shown, done = typed(lines, t_start, t, CPS)
    ty = y0 + 7 if len(lines) > 1 else y0 + 16
    for part in shown:
        draw_text(img, x0 + 10, ty, part, WHITE)
        ty += 18
    if done and int(t * 3) % 2 == 0:
        cx, cy = x1 - 14, y1 - 12
        d.polygon([(cx, cy), (cx + 6, cy), (cx + 3, cy + 3)], fill=C(WHITE))


def draw_bubble(img, x, y, lines, t_start, t, tail):
    """キャラクターのふきだし。(x, y) は左上、tail はしっぽの先。"""
    d = ImageDraw.Draw(img)
    w = max(text_width(s) for s in lines) + 10
    h = 18 * len(lines) + 4
    x = max(2, min(W - 3 - w, x))
    tx, ty = tail
    bx = max(x + 4, min(x + w - 11, tx - 3))
    by = y + h if ty > y else y
    d.polygon([(bx, by), (bx + 7, by), (tx, ty)], fill=C(WHITE), outline=C(BLACK))
    d.rectangle([x, y, x + w, y + h], fill=C(WHITE), outline=C(BLACK))
    d.line([bx + 1, by, bx + 6, by], fill=C(WHITE))
    shown, _ = typed(lines, t_start, t, BCPS)
    for i, part in enumerate(shown):
        draw_text(img, x + 5, y + 3 + i * 18, part, BLACK)


def char_times(lines, t_start, cps):
    out = []
    i = 0
    for line in lines:
        for ch in line:
            if ch not in " 　…":
                out.append(t_start + i / cps)
            i += 1
    return out


def draw_stage_label(img, label):
    w = text_width(label)
    d = ImageDraw.Draw(img)
    d.rectangle([3, 3, 3 + w + 9, 3 + 21], fill=C(BLACK))
    d.rectangle([4, 4, 3 + w + 8, 3 + 20], outline=C(YELLOW))
    draw_text(img, 8, 6, label, YELLOW)


# ---------------------------------------------------------------- 場面の設定
# (開始, 終了, 関数名, ラベル, 字幕行)
SCENES = [
    (0.0, 5.0, "title", None, None),
    (5.0, 11.0, "become", "STAGE 1", ["自分じゃない「だれか」に", "なりきって、冒険へ出よう！"]),
    (11.0, 19.0, "talk", "STAGE 2", ["決まった選択肢はいらない。", "自分の言葉で話していい！"]),
    (19.0, 27.0, "dice", "STAGE 3", ["ドキドキの判定は、", "サイコロで決まる！"]),
    (27.0, 34.0, "friends", "STAGE 4", ["仲間の一言で、物語は", "思いもよらない方向へ！"]),
    (34.0, 40.0, "clear", "STAGE CLEAR", ["次の冒険の主人公は、あなたです"]),
]
TEXT_DELAY = 0.55
TRANS = 0.4

# ふきだし：場面名 -> [(開始, 終了, x, y, 行, しっぽ先)]（時刻は場面内）
BUBBLES = {
    "become": [
        (2.3, 3.0, 104, 18, ["今日のわたしは…"], (100, 60)),
        (3.9, 6.0, 104, 18, ["剣士リナ、参上！"], (100, 60)),
    ],
    "talk": [
        (0.8, 2.0, 150, 30, ["とまれ！"], (206, 58)),
        (3.6, 5.4, 82, 8, ["おなかすいてない？", "パンあげる！"], (72, 55)),
        (5.5, 7.6, 150, 26, ["…いいやつだな！"], (206, 58)),
    ],
    "dice": [
        (3.5, 4.9, 118, 22, ["おおー！"], (135, 58)),
        (6.3, 7.6, 176, 20, ["成功！"], (230, 40)),
    ],
    "friends": [
        (0.4, 1.3, 200, 30, ["ガオー！"], (222, 58)),
        (1.3, 2.5, 74, 22, ["友だちに", "なろう！"], (92, 60)),
        (2.75, 4.3, 100, 24, ["まさかの展開！？"], (176, 60)),
        (4.7, 6.6, 196, 26, ["ガオ♪"], (222, 56)),
    ],
}

# 現実と冒険の世界を行き来する時刻（場面内）
WORLD_SWITCH = {
    "dice": [1.35, 4.95],
    "friends": [2.6, 4.45],
}
WOBBLE = 0.3  # ゆらぎの長さ（片側）


def world_of(name, t):
    """場面内の時刻 t で、冒険('adv') か 現実('real') か"""
    k = sum(1 for s in WORLD_SWITCH.get(name, []) if t >= s)
    return "adv" if k % 2 == 0 else "real"


def wobble_amount(name, t):
    a = 0.0
    for s in WORLD_SWITCH.get(name, []):
        a = max(a, 1 - abs(t - s) / WOBBLE)
    return a


def apply_wobble(img, amt, t):
    """画面をゆらゆらさせる（行ごとに横へずらす）。会話ウィンドウより上だけ。"""
    if amt <= 0:
        return img
    a = np.asarray(img).copy()
    for y in range(128):
        sh = int(math.sin(y * 0.25 + t * 30) * 18 * amt)
        a[y] = np.roll(a[y], sh, axis=0)
    if amt > 0.6:
        add = int(90 * (amt - 0.6) / 0.4)
        a[:128] = np.minimum(255, a[:128].astype(np.int16) + add).astype(np.uint8)
    return Image.fromarray(a)


# ---------------------------------------------------------------- 背景
def stars(img, t, seed=1, n=40, ymax=110):
    rnd = random.Random(seed)
    px = img.load()
    for i in range(n):
        x, y = rnd.randrange(W), rnd.randrange(ymax)
        if math.sin(t * 4 + rnd.random() * 6) > -0.3:
            px[x, y] = C(WHITE if i % 3 else YELLOW)


def sky_field(img, t, sky=BLUE, ground=104):
    """冒険の世界（草原）"""
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, ground], fill=C(sky))
    for cx, cy in [(60, 30), (170, 18), (270, 36)]:
        x = (cx + t * 6) % (W + 60) - 30
        d.rectangle([x, cy, x + 26, cy + 6], fill=C(WHITE))
        d.rectangle([x + 6, cy - 4, x + 18, cy], fill=C(WHITE))
    for mx in range(-20, W, 70):
        d.polygon([(mx, ground), (mx + 35, ground - 34), (mx + 70, ground)], fill=C(LAV))
    d.rectangle([0, ground, W, 127], fill=C(GREEN))
    d.line([0, ground, W, ground], fill=C(DGREEN))
    rnd = random.Random(3)
    for _ in range(26):
        x, y = rnd.randrange(W), rnd.randrange(ground + 4, 125)
        d.line([x, y, x + 1, y - 2], fill=C(DGREEN))
        d.line([x + 2, y, x + 3, y - 2], fill=C(DGREEN))


def warm_room(img):
    """現実の部屋（暖かい色）"""
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 104], fill=C(BROWN))
    for x in range(8, W, 24):
        d.line([x, 0, x, 104], fill=C(ORANGE))
    d.rectangle([0, 104, W, 127], fill=C(PEACH))
    for x in range(0, W, 20):
        d.line([x, 104, x - 8, 127], fill=C(BROWN))
    d.line([0, 104, W, 104], fill=C(BLACK))


TABLE_PEOPLE = [(34, GM), (98, RINA), (184, PAL1), (248, PAL2)]  # x, 人


def draw_table(img, t, table_y=92, pose_fn=None, bob_fn=None, lamp=True):
    """現実のテーブル。4人（GM + プレイヤー3人）がテーブルを囲んでいる。"""
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, table_y + 36], fill=C(BROWN))
    for x in range(8, W, 24):
        d.line([x, 0, x, table_y], fill=C(ORANGE))
    if lamp:
        d.line([160, 0, 160, 8], fill=C(BLACK))
        d.polygon([(148, 16), (172, 16), (166, 8), (154, 8)], fill=C(YELLOW), outline=C(BLACK))
    for i, (px, per) in enumerate(TABLE_PEOPLE):
        pose = pose_fn(i) if pose_fn else "idle"
        bob = bob_fn(i) if bob_fn else 0
        draw_person(img, per, px, table_y - 34 - bob, t, pose, seed=i, crop=17)
    d.rectangle([0, table_y, W, table_y + 12], fill=C(PEACH))
    d.line([0, table_y, W, table_y], fill=C(BLACK))
    d.rectangle([0, table_y + 12, W, table_y + 36], fill=C(BROWN))
    d.line([0, table_y + 12, W, table_y + 12], fill=C(BLACK))
    # キャラクターシート
    for px, _ in TABLE_PEOPLE[1:]:
        put(img, SHEET.resize((10, 7), Image.NEAREST), px + 10, table_y + 3)
    # GM のついたて
    gx = TABLE_PEOPLE[0][0] - 2
    d.rectangle([gx, table_y - 10, gx + 36, table_y + 8], fill=C(NAVY), outline=C(BLACK))
    draw_text(img, gx + 11, table_y - 9, "GM", YELLOW)


def draw_dream(img, box, content):
    """テーブルの上に浮かぶ「冒険の世界」"""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if w < 4 or h < 4:
        return
    scene = Image.new("RGB", (w, h), C(BLUE))
    content(scene)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=10, fill=255)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x0 - 3, y0 - 3, x1 + 2, y1 + 2], radius=12, fill=C(WHITE), outline=C(BLACK))
    img.paste(scene, (x0, y0), mask)


def mini_world(scene, t, friendly=False):
    d = ImageDraw.Draw(scene)
    w, h = scene.size
    for cx in (20, w - 60):
        d.rectangle([cx, 6, cx + 16, 10], fill=C(WHITE))
    d.rectangle([0, h - 12, w, h], fill=C(GREEN))
    # お城
    d.rectangle([w // 2 - 10, h - 34, w // 2 + 10, h - 12], fill=C(LGRAY))
    for k in range(w // 2 - 10, w // 2 + 10, 6):
        d.rectangle([k, h - 38, k + 3, h - 34], fill=C(LGRAY))
    d.rectangle([w // 2 - 3, h - 22, w // 2 + 3, h - 12], fill=C(BROWN))
    hop = int(abs(math.sin(t * 6)) * 2) if friendly else 0
    put(scene, RINA_KNIGHT["cheer" if friendly else "idle"], 10, h - 36 - hop)
    put(scene, PAL1_WIZ["cheer" if friendly else "idle"], 32, h - 40 - hop)
    put(scene, DRAGON_FRIEND if friendly else DRAGON, w - 44, h - 35)
    if friendly:
        put(scene, HEART, w - 52, h - 46 - int(abs(math.sin(t * 4)) * 4))


# ---------------------------------------------------------------- 各場面
def scene_title(img, t):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, H], fill=C(NAVY))
    stars(img, t, seed=3, n=50, ymax=128)
    # タイトル（落ちてきて止まる）
    title = "TRPGって？"
    tw = text_width(title) * 3
    ty = 4 - int((1 - ease_out(t / 0.8)) * 70)
    draw_text(img, (W - tw) // 2, ty, title, YELLOW, scale=3, outline=BLACK, shadow=ORANGE)
    # テーブルの上に冒険の世界が浮かぶ
    k = ease_out((t - 0.9) / 0.6)
    if k > 0:
        hh = int(50 * k)
        draw_dream(img, (70, 78 - hh // 2, 250, 78 + hh // 2), lambda s: mini_world(s, t))
        for bx, by, r in [(106, 114, 3), (110, 122, 2)]:
            d.ellipse([bx - r, by - r, bx + r, by + r], fill=C(WHITE), outline=C(BLACK))
    # テーブルを囲む4人
    tbl = Image.new("RGB", (W, 60), C(BROWN))
    draw_table(tbl, t, table_y=36, lamp=False)
    img.paste(tbl.crop((0, 0, W, 50)), (0, 130))
    # PRESS START
    pressed = t >= 3.9
    if int(t * (12 if pressed else 2.5)) % 2 == 0:
        s = "PRESS START"
        draw_text(img, (W - text_width(s)) // 2, 108, s, WHITE, outline=BLACK)


def poof(img, t, cx, cy):
    """変身のけむり"""
    d = ImageDraw.Draw(img)
    rnd = random.Random(11)
    k = clamp01(t / 0.6)
    for i in range(12):
        ang = rnd.random() * math.tau
        dist = 4 + k * 20 * (0.5 + rnd.random())
        r = int((1 - abs(k - 0.4)) * 12) + 2
        x, y = cx + math.cos(ang) * dist, cy + math.sin(ang) * dist
        d.ellipse([x - r, y - r, x + r, y + r], fill=C(WHITE if i % 2 else LGRAY), outline=C(BLACK))


def scene_become(img, t):
    warm_room(img)
    d = ImageDraw.Draw(img)
    # 後ろのテーブルと仲間
    for i, (px, per) in enumerate([(206, PAL1), (262, PAL2)]):
        draw_person(img, per, px, 42, t, "idle", seed=i + 2, crop=17)
    d.rectangle([196, 76, 316, 84], fill=C(PEACH), outline=C(BLACK))
    d.rectangle([196, 84, 316, 104], fill=C(BROWN), outline=C(BLACK))
    gx, gy = 60, 56
    if t < 3.3:
        draw_person(img, RINA, gx, gy, t, "idle")
        if t >= 0.8:
            # キャラクターシートを持ち上げる
            lift = ease_out((t - 0.8) / 0.5)
            put(img, SHEET, gx + 30, gy + 26 - lift * 14, 2)
            if lift >= 1 and int(t * 6) % 2 == 0:
                sparkle(d, gx + 54, gy + 4, 3, YELLOW)
    else:
        pose = "cheer" if t >= 3.8 else "idle"
        hop = int(abs(math.sin((t - 3.8) * 9)) * 5) if 3.8 <= t < 4.5 else 0
        draw_person(img, RINA_KNIGHT, gx, gy - hop, t, pose)
        if t >= 3.8:
            for i in range(5):
                ph = (t * 1.5 + i / 5) % 1
                sparkle(d, gx - 8 + i * 12, int(gy + 40 - ph * 50), 2, YELLOW if i % 2 else WHITE)
    if 3.0 <= t < 3.7:
        poof(img, t - 3.0, gx + 16, gy + 24)


GATE_X = 236


def scene_talk(img, t):
    sky_field(img, t)
    d = ImageDraw.Draw(img)
    # 城壁と門
    d.rectangle([GATE_X, 8, W, 104], fill=C(LGRAY))
    for y in range(8, 104, 8):
        off = 0 if (y // 8) % 2 else 8
        for x in range(GATE_X - off, W, 16):
            d.rectangle([max(GATE_X, x), y, x + 15, y + 7], outline=C(DGRAY))
    for x in range(GATE_X, W, 12):
        d.rectangle([x, 2, x + 6, 8], fill=C(LGRAY), outline=C(DGRAY))
    gx0, gx1, gy0 = GATE_X + 24, GATE_X + 68, 44
    d.rectangle([gx0, gy0, gx1, 104], fill=C(YELLOW))
    open_k = ease_out((t - 6.2) / 1.0)
    door_bottom = 104 - int(open_k * 60)
    if door_bottom > gy0:
        d.rectangle([gx0, gy0, gx1, door_bottom], fill=C(BROWN))
        for x in range(gx0 + 6, gx1, 8):
            d.line([x, gy0, x, door_bottom], fill=C(BLACK))
    d.rectangle([gx0, gy0, gx1, 104], outline=C(BLACK))
    # 門番と槍
    vx, vy = 190, 58
    d.line([vx + 30, vy - 16, vx + 30, vy + 46], fill=C(BROWN), width=2)
    d.polygon([(vx + 27, vy - 16), (vx + 34, vy - 16), (vx + 30, vy - 26)], fill=C(LGRAY), outline=C(BLACK))
    nod = int(abs(math.sin(t * 8)) * 2) if 5.5 <= t < 6.5 else 0
    put(img, GUARD, vx, vy + 2 - nod, 2)
    # 主人公
    draw_person(img, RINA_KNIGHT, 44, 56, t, "idle")
    if t >= 4.4:
        put(img, BREAD, 78, 82 - int(ease_out((t - 4.4) / 0.3) * 4), 2)
    # 昔のゲームの選択肢 → 押しのける
    if 1.6 <= t < 3.9:
        mx, my = 96, 36
        if t >= 3.2:
            k = t - 3.2
            if k < 0.3:
                mx += int(math.sin(k * 60) * 3)
            else:
                my -= int((k - 0.3) ** 2 * 900)
                mx += int((k - 0.3) * 200)
        mw, mh = 92, 48
        d.rectangle([mx, my, mx + mw, my + mh], fill=C(BLACK))
        d.rectangle([mx + 1, my + 1, mx + mw - 1, my + mh - 1], outline=C(WHITE))
        d.rectangle([mx + 4, my + 4, mx + mw - 4, my + mh - 4], outline=C(WHITE))
        draw_text(img, mx + 22, my + 7, "たたかう", WHITE)
        draw_text(img, mx + 22, my + 25, "にげる", WHITE)
        sel = 1 if 2.3 <= t < 2.8 else 0
        if int(t * 5) % 2 == 0 or t >= 3.2:
            cy = my + 11 + sel * 18
            d.polygon([(mx + 10, cy), (mx + 10, cy + 8), (mx + 16, cy + 4)], fill=C(WHITE))
        if t >= 3.2:
            draw_text(img, 34, 36, "えいっ", YELLOW, outline=BLACK)


CLIFF_Y = 92


def scene_dice(img, t):
    if world_of("dice", t) == "adv":
        sky_field(img, t, ground=CLIFF_Y)
        d = ImageDraw.Draw(img)
        # 崖
        d.rectangle([120, CLIFF_Y, 206, 127], fill=C(NAVY))
        d.rectangle([116, CLIFF_Y, 120, 127], fill=C(BROWN))
        d.rectangle([206, CLIFF_Y, 210, 127], fill=C(BROWN))
        d.line([120, CLIFF_Y, 120, 127], fill=C(BLACK))
        d.line([206, CLIFF_Y, 206, 127], fill=C(BLACK))
        if t < 3:
            draw_person(img, RINA_KNIGHT, 76, CLIFF_Y - 48, t, "idle")
            if int(t * 4) % 2 == 0:
                draw_text(img, 88, CLIFF_Y - 70, "！", YELLOW, outline=BLACK)
        else:
            k = clamp01((t - 5.3) / 0.9)
            gx = 76 + (230 - 76) * k
            gy = CLIFF_Y - 48 - math.sin(k * math.pi) * 40
            draw_person(img, RINA_KNIGHT, gx, gy, t, "cheer" if k > 0 else "idle")
            if t >= 6.2:
                for i in range(6):
                    ang = i * math.pi / 3 + t * 2
                    r = 26 + (t - 6.2) * 20
                    sparkle(d, int(gx + 16 + math.cos(ang) * r), int(gy + 24 + math.sin(ang) * r * 0.6), 3, YELLOW)
    else:
        done = t >= 3.4

        def pose(i):
            return "cheer" if done else "idle"

        def bob(i):
            return int(abs(math.sin(t * 9 + i)) * 4) if done else 0

        draw_table(img, t, pose_fn=pose, bob_fn=bob)
        d = ImageDraw.Draw(img)
        if 1.35 <= t < 1.8:
            put(img, DICE[3], 118, 74, 2)  # リナがサイコロを手にする
        if t >= 1.8:
            k = clamp01((t - 1.8) / 1.6)
            x = 118 + (150 - 118) * ease_out(k)
            y = 74 - abs(math.sin(k * math.pi * 3)) * 22 * (1 - k)
            face = 6 if done else 1 + int(t * 14) % 6
            put(img, DICE[face], x, y, 2)
            if done:
                for i in range(8):
                    ang = i * math.pi / 4
                    r = 20 + int(3 * math.sin(t * 12))
                    cx, cy = 165, 89
                    d.line([cx + math.cos(ang) * r, cy + math.sin(ang) * r * 0.7,
                            cx + math.cos(ang) * (r + 6), cy + math.sin(ang) * (r + 6) * 0.7],
                           fill=C(YELLOW), width=2)


def scene_friends(img, t):
    if world_of("friends", t) == "adv":
        after = t >= 4.45
        sky_field(img, t, sky=BLUE if after else PLUM)
        d = ImageDraw.Draw(img)
        draw_person(img, RINA_KNIGHT, 24, 56, t, "cheer" if after else "idle")
        wpose = "cheer" if (1.3 <= t < 2.6 or after) else "idle"
        draw_person(img, PAL1_WIZ, 76, 48, t, wpose, seed=1)
        # 杖
        d.line([70, 70, 70, 104], fill=C(BROWN), width=2)
        d.ellipse([66, 62, 74, 70], fill=C(ORANGE if int(t * 6) % 2 else YELLOW), outline=C(BLACK))
        shake = int(math.sin(t * 50) * 2) if 0.4 <= t < 1.3 else 0
        put(img, DRAGON_FRIEND if after else DRAGON, 196 + shake, 104 - 46, 2)
        if after:
            for n in range(4):
                ph = (t * 0.8 + n / 4) % 1
                put(img, HEART, 130 + n * 16, int(84 - ph * 36))
        if 0.4 <= t < 1.3:
            # 火の息
            for i in range(5):
                fx = 188 - i * 8 - (t * 60 % 8)
                d.rectangle([fx, 74 + (i % 2) * 3, fx + 5, 78 + (i % 2) * 3], fill=C(ORANGE if i % 2 else RED))
    else:
        def bob(i):
            return int(abs(math.sin(t * 12 + i * 1.7)) * 4)

        draw_table(img, t, pose_fn=lambda i: "happy", bob_fn=bob)
        for i, (px, _) in enumerate(TABLE_PEOPLE):
            if i in (0, 3):
                draw_text(img, px - 2, 30, "わはは", WHITE, outline=BLACK)


def scene_clear(img, t):
    def bob(i):
        return int(abs(math.sin(t * 7 + i * 1.3)) * 5) if t >= 0.6 else 0

    draw_table(img, t, pose_fn=lambda i: "happy" if t >= 0.6 else "idle", bob_fn=bob, lamp=False)
    d = ImageDraw.Draw(img)
    # 冒険の思い出
    draw_dream(img, (118, 6, 312, 50), lambda s: mini_world(s, t, friendly=True))
    for bx, by, r in [(300, 56, 3), (305, 63, 2)]:
        d.ellipse([bx - r, by - r, bx + r, by + r], fill=C(WHITE), outline=C(BLACK))
    # ハイタッチ
    if 0.6 <= t < 1.4:
        k = t - 0.6
        r = int(4 + min(k, 0.4) * 30)
        for i in range(8):
            ang = i * math.pi / 4
            d.line([157 + math.cos(ang) * r * 0.5, 78 + math.sin(ang) * r * 0.5,
                    157 + math.cos(ang) * r, 78 + math.sin(ang) * r], fill=C(YELLOW), width=2)
        draw_text(img, 136, 56, "パン！", WHITE, outline=BLACK)
    # 紙吹雪
    rnd = random.Random(5)
    if t > 0.5:
        for n in range(40):
            x = (rnd.randrange(W) + int(math.sin(t * 2 + n) * 6)) % W
            y = (rnd.random() * 130 + (t - 0.5) * (30 + rnd.random() * 30)) % 126
            col = [RED, YELLOW, GREEN, BLUE, PINK, WHITE][n % 6]
            d.rectangle([x, int(y), x + 1, int(y) + 1], fill=C(col))


SCENE_FUNCS = dict(title=scene_title, become=scene_become, talk=scene_talk,
                   dice=scene_dice, friends=scene_friends, clear=scene_clear)

# ---------------------------------------------------------------- 画面切り替え
BLOCK = 16
_order = [(bx, by) for by in range(0, H, BLOCK) for bx in range(0, W, BLOCK)]
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
            for b0, b1, bx, by, blines, tail in BUBBLES.get(name, []):
                if b0 <= lt < b1:
                    draw_bubble(img, bx, by, blines, b0, lt, tail)
            img = apply_wobble(img, wobble_amount(name, lt), lt)
            if lines:
                draw_window(img, lines, TEXT_DELAY, lt)
            if label:
                draw_stage_label(img, label)
            if i > 0 and lt < TRANS:
                draw_blocks(img, 1 - lt / TRANS)
            if i < len(SCENES) - 1 and e - t < TRANS:
                draw_blocks(img, 1 - (e - t) / TRANS)
            break
    return img


# ---------------------------------------------------------------- 効果音(8bit)
SR = 44100


def tone(freq, dur, vol=0.2, duty=0.5, kind="square", decay=0.0, slide=0.0, vib=0.0):
    n = int(SR * dur)
    tt = np.arange(n) / SR
    f = freq * (1 + slide * tt / max(dur, 1e-6))
    if vib:
        f = f * (1 + vib * np.sin(tt * 2 * math.pi * 18))
    ph = np.cumsum(f) / SR
    if kind == "square":
        w = np.where((ph % 1) < duty, 1.0, -1.0)
    elif kind == "tri":
        w = 4 * np.abs((ph % 1) - 0.5) - 1
    else:  # noise（ファミコン風に一定間隔で値を保持）
        rng = np.random.default_rng(int(freq))
        hold = max(1, int(SR / freq))
        w = np.repeat(rng.choice([-1.0, 1.0], n // hold + 1), hold)[:n]
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


def seq(notes, beat, vol=0.14, duty=0.5, decay=0.0):
    return np.concatenate([tone(note(n), beat * d, vol, duty, decay=decay) for n, d in notes])


def silence(sec):
    return np.zeros(int(SR * sec), np.float32)


def se_text():
    return tone(1200, 0.03, vol=0.07, duty=0.25)


def se_voice():
    return tone(620, 0.035, vol=0.08, duty=0.5)


def se_decide():
    return np.concatenate([tone(note("B5"), 0.05, 0.15), tone(note("E6"), 0.11, 0.15, decay=8)])


def se_cursor():
    return tone(note("A5"), 0.04, 0.1, 0.25)


def se_transform():
    up = tone(300, 0.45, 0.13, 0.25, slide=4.0)
    return np.concatenate([up, seq([("C6", 1), ("E6", 1), ("G6", 1), ("C7", 4)], 0.05, 0.12, 0.25, decay=3)])


def se_push():
    return np.concatenate([tone(200, 0.08, 0.15, 0.5, slide=1.5), tone(900, 0.25, 0.1, 0.5, slide=-0.8)])


def se_gate():
    return tone(90, 1.0, 0.12, kind="noise", decay=1.5) + tone(55, 1.0, 0.1, kind="tri", decay=1.5)


def se_wobble():
    return tone(700, 0.6, 0.08, 0.5, vib=0.25, slide=-0.5)


def se_dice():
    parts = []
    for i in range(12):
        parts.append(tone(1800 + (i % 3) * 400, 0.025, 0.14, kind="noise", decay=40))
        parts.append(silence(0.06 + i * 0.006))
    return np.concatenate(parts)


def se_success():
    return seq([("G5", 1), ("C6", 1), ("E6", 1), ("G6", 1), ("C7", 4)], 0.06, 0.14, 0.25, decay=2)


def se_jump():
    return tone(300, 0.3, 0.12, 0.5, slide=2.0)


def se_roar():
    return tone(120, 0.7, 0.18, kind="noise", decay=2.5) + tone(80, 0.7, 0.1, 0.5, slide=-0.3, decay=3)


def se_whoosh():
    return tone(3000, 0.35, 0.05, kind="noise", decay=6)


def se_clap():
    return tone(2500, 0.12, 0.2, kind="noise", decay=25)


def se_laugh():
    out = []
    for i in range(6):
        out.append(tone(note("E5") * (1.0 + 0.06 * (i % 2)), 0.07, 0.07, 0.25))
        out.append(silence(0.04))
    return np.concatenate(out)


def se_fanfare():
    beat = 0.12
    mel = [("C5", 1), ("E5", 1), ("G5", 1), ("C6", 3),
           ("A5", 1), ("B5", 1), ("C6", 1), ("D6", 3),
           ("E6", 2), ("D6", 1), ("C6", 1), ("E6", 1), ("G6", 6)]
    bass = [("C3", 6), ("F3", 6), ("G3", 5), ("C4", 10)]
    m = seq(mel, beat, 0.15, 0.5, decay=1.5)
    b = np.concatenate([tone(note(n), beat * d, 0.22, kind="tri") for n, d in bass])
    h = np.concatenate([tone(note(n) * 0.8409, beat * d, 0.07, 0.25, decay=1.5) for n, d in mel])
    out = np.zeros(max(len(m), len(b)), np.float32)
    out[:len(m)] += m
    out[:len(b)] += b
    out[:len(h)] += h
    return out


def build_audio(path):
    buf = np.zeros(int(SR * DURATION) + SR * 2, np.float32)

    def add(t, snd):
        i = int(t * SR)
        j = min(len(buf), i + len(snd))
        buf[i:j] += snd[: j - i]

    start = {name: s for s, e, name, _, _ in SCENES}
    for i, (s, e, name, label, lines) in enumerate(SCENES):
        if i < len(SCENES) - 1:
            add(e - TRANS, se_whoosh())
        if lines:
            for ct in char_times(lines, s + TEXT_DELAY, CPS):
                add(ct, se_text())
        for b0, b1, _, _, blines, _ in BUBBLES.get(name, []):
            for ct in char_times(blines, s + b0, BCPS):
                add(ct, se_voice())
        for sw in WORLD_SWITCH.get(name, []):
            add(s + sw - WOBBLE, se_wobble())
    add(3.9, se_decide())                       # PRESS START
    b = start["become"]                         # STAGE 1 なりきる
    add(b + 1.3, se_cursor())
    add(b + 3.0, se_transform())
    b = start["talk"]                           # STAGE 2 自分の言葉で
    add(b + 1.6, se_decide())
    add(b + 2.3, se_cursor())
    add(b + 2.8, se_cursor())
    add(b + 3.2, se_push())
    add(b + 4.4, se_decide())
    add(b + 6.2, se_gate())
    add(b + 6.6, se_success())
    b = start["dice"]                           # STAGE 3 サイコロ
    add(b + 1.8, se_dice())
    add(b + 3.4, se_success())
    add(b + 3.6, se_laugh())
    add(b + 5.3, se_jump())
    add(b + 6.2, se_success())
    b = start["friends"]                        # STAGE 4 仲間
    add(b + 0.4, se_roar())
    add(b + 2.75, se_laugh())
    add(b + 4.7, se_success())
    b = start["clear"]                          # STAGE CLEAR
    add(b + 0.4, se_fanfare())
    add(b + 0.6, se_clap())
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
        i = sys.argv.index("--stills")
        out = sys.argv[i + 1] if len(sys.argv) > i + 1 else "stills"
        times = [float(x) for x in sys.argv[i + 2:]] or \
            [2.5, 4.5, 7.0, 9.5, 13.0, 15.5, 17.5, 20.0, 22.8, 25.5, 28.0, 30.0, 32.5, 37.0]
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
    for f in range(int(DURATION * FPS)):
        p.stdin.write(upscale(render(f / FPS)).tobytes())
    p.stdin.close()
    p.wait()
    os.remove(wav)
    print("wrote", mp4)


if __name__ == "__main__":
    main()
