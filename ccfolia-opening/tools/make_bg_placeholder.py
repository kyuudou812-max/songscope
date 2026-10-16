"""仮の背景（v4）：廊下の奥にある、少しだけ開いたドアを遠くから見る構図。

本番は ChatGPT などで作った絵に差し替える。構図の考え方は STORYBOARD.md の指示文と同じ。
  - 遠くから広く撮る（黒沢清・イット・フォローズ）：ドアは小さく、周りに空間を残す
  - 光には理由を（ディーキンス）：手前の天井の蛍光灯だけが光源。奥ほど暗く、隙間が一番暗い
ドアの隙間などの位置は build/layout_placeholder.json に書き出す（--layout で試せる）。

使い方: python3 make_bg_placeholder.py
出力: build/bg_placeholder.png, build/layout_placeholder.json（本番の背景は opening/bg.png と opening/layout.json）
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H = 1280, 720
VP = (530, 385)                       # 消失点
END = (430, 250, 630, 520)            # 突き当たりの壁（x0, y0, x1, y1）
DOOR = (470, 285, 590, 520)           # ドア枠
GAP = (470, 150 + 135, 487, 520)      # ドアの隙間（枠の左端。中は真っ暗）
LAMP = (230, 18, 470, 34)             # 手前の天井の蛍光灯


def main():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # 奥行き：消失点に近いほど遠い（0）、画面の端ほど近い（1）
    near = np.clip(np.maximum(np.abs(xx - VP[0]) / 640, np.abs(yy - VP[1]) / 385), 0, 1)
    # 光：手前の蛍光灯からの距離で減衰。奥ほど暗い
    lx, ly = (LAMP[0] + LAMP[2]) / 2, LAMP[3] + 30
    dist = np.sqrt(((xx - lx) / 700) ** 2 + ((yy - ly) / 520) ** 2)
    light = np.clip(1.15 - dist, 0, 1) ** 1.6
    lum = 18 + 120 * light * (0.35 + 0.65 * near)
    img = np.stack([lum * 1.08, lum * 0.93, lum * 0.86], -1)          # 赤茶色の色かぶり
    base = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))

    d = ImageDraw.Draw(base, "RGBA")
    x0, y0, x1, y1 = END
    # 壁・床・天井の境目（遠近の線）
    for (ax, ay), (bx, by) in [((0, 0), (x0, y0)), ((W, 0), (x1, y0)), ((0, H), (x0, y1)), ((W, H), (x1, y1))]:
        d.line([(ax, ay), (bx, by)], fill=(0, 0, 0, 90), width=3)
    d.rectangle(END, fill=(28, 23, 21, 255))                          # 突き当たりの壁（暗い）
    # 床の目地
    for k in range(1, 9):
        t = k / 9
        y = y1 + (H - y1) * t ** 1.8
        xa = x0 - x0 * t ** 1.8
        xb = x1 + (W - x1) * t ** 1.8
        d.line([(xa, y), (xb, y)], fill=(0, 0, 0, 40), width=1)
    # ドア（光がほとんど届かない）
    d.rectangle(DOOR, fill=(36, 29, 26, 255), outline=(14, 11, 10, 255), width=3)
    d.rectangle((GAP[0] + 2, GAP[1] + 2, GAP[2], GAP[3]), fill=(3, 3, 3, 255))  # 隙間：真っ暗
    d.ellipse((498, 398, 506, 406), fill=(70, 64, 58, 255))           # ドアノブ
    d.rectangle((600, 360, 614, 378), fill=(44, 40, 37, 255))         # インターホン
    d.rectangle((440, 420, 462, 448), fill=(33, 29, 27, 255))         # 郵便受け
    # 蛍光灯（光源そのもの）
    d.rectangle(LAMP, fill=(235, 228, 212, 255))
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).rectangle(LAMP, fill=255)
    glow = glow.filter(ImageFilter.GaussianBlur(28))
    arr = np.array(base, np.float32) + np.array(glow, np.float32)[..., None] * np.array([0.55, 0.5, 0.42])
    arr += np.random.default_rng(5).normal(0, 1.5, arr.shape)        # 細かい粒子（ディザ）：暗いグラデーションの縞を防ぐ
    vign = 1 - 0.55 * np.clip(((xx - W / 2) / (W * 0.65)) ** 2 + ((yy - H / 2) / (H * 0.75)) ** 2, 0, 1)
    out = Image.fromarray(np.clip(arr * vign[..., None], 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    ImageDraw.Draw(out).text((20, 690), "仮の背景", font=ImageFont.truetype(str(ROOT / "fonts" / "ZenKakuGothicNew-Medium.ttf"), 18),
                             fill=(110, 100, 92))
    (ROOT / "build").mkdir(exist_ok=True)
    out.save(ROOT / "build" / "bg_placeholder.png")

    layout = {
        "_comment": "仮の背景に合わせた位置（px、1280×720基準）。render_opening.mjs --layout build/layout_placeholder.json で使う。",
        "bg": "../build/bg_placeholder.png",
        "gap": {"x0": GAP[0], "x1": GAP[2], "y0": GAP[1], "y1": GAP[3]},
        "lamp": {"x0": LAMP[0], "y0": LAMP[1], "x1": LAMP[2], "y1": LAMP[3]},
    }
    (ROOT / "build" / "layout_placeholder.json").write_text(json.dumps(layout, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("build/bg_placeholder.png, build/layout_placeholder.json")


if __name__ == "__main__":
    main()
