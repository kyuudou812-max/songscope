"""ChatGPT で作ったNPCの立ち絵を、部屋の空気にそろえてココフォリア用に書き出す。

やること（STYLE.md と NPC-SETUP.md の方針）:
  1. 背景を抜く：透明でなければ、画像の外周から続く地の色だけを抜く（人物の中の白は残す）
  2. 色味をそろえる：明るさだけを残し、廊下の絵（opening/bg.png）と同じ赤茶の色味をかけ直す。
     ChatGPT は1枚ごとに色味がぶれるため、全員を同じ色の物差しに乗せる
  3. 人物の範囲で切り抜き、高さ 1200px にして WebP で保存する（PNG はココフォリアで256色に変換されるため）
  4. 確認用に、探索シーンのNPCの置き場に立たせた絵も書き出す

使い方: python3 tools/make_npc_portrait.py <元の画像> <出力名（例: npc_lecturer）>
出力: build/ccfolia/npc/<出力名>.webp と build/ccfolia/npc/<出力名>_check.png
"""
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "ccfolia" / "npc"
HEIGHT = 1200


def cut_background(img):
    """外周から続く、地の色に近い画素だけを透明にする（人物の中の同じ色は残す）"""
    a = np.asarray(img.convert("RGBA")).astype(np.float32)
    if (a[..., 3] < 250).mean() > 0.05:                      # すでに透明な背景
        return a
    rgb = a[..., :3]
    h, w = rgb.shape[:2]
    edge = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    ground = np.median(edge, axis=0)
    near = np.abs(rgb - ground).max(-1) < 28                  # 地の色に近い
    bg = np.zeros((h, w), bool)
    q = deque((y, x) for y in (0, h - 1) for x in range(w) if near[y, x])
    q.extend((y, x) for x in (0, w - 1) for y in range(h) if near[y, x])
    for y, x in q:
        bg[y, x] = True
    while q:
        y, x = q.popleft()
        for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if 0 <= ny < h and 0 <= nx < w and near[ny, nx] and not bg[ny, nx]:
                bg[ny, nx] = True
                q.append((ny, nx))
    alpha = Image.fromarray(((~bg) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    a[..., 3] = np.asarray(alpha, np.float32)
    return a


def tone_lut():
    """廊下の絵から「明るさ → 色」の対応を作る（明るさごとの R:G:B の比）"""
    bg = np.asarray(Image.open(ROOT / "opening" / "bg.png").convert("RGB")).astype(np.float32)
    lum = bg @ np.array([0.299, 0.587, 0.114])
    ratio = np.ones((256, 3), np.float32)
    last = np.ones(3, np.float32)
    for v in range(256):
        m = (lum >= v - 3) & (lum <= v + 3)
        if m.sum() > 200 and v > 8:
            c = bg[m].mean(0)
            last = c / max(c @ np.array([0.299, 0.587, 0.114]), 1)
        ratio[v] = last                                       # 絵にない明るさは、いちばん近い明るさの比を使う
    return ratio


def main(src, name):
    OUT.mkdir(parents=True, exist_ok=True)
    a = cut_background(Image.open(src))
    lum = a[..., :3] @ np.array([0.299, 0.587, 0.114], np.float32)
    lo, hi = np.percentile(lum[a[..., 3] > 128], [1, 99.5])
    lum = np.clip((lum - lo) / max(hi - lo, 1), 0, 1) * 236 + 6   # 真っ白・真っ黒にしない（#eeece8 と #040404 の間）
    rgb = lum[..., None] * tone_lut()[lum.astype(int)]
    out = np.dstack([np.clip(rgb, 0, 255), a[..., 3]]).astype(np.uint8)
    img = Image.fromarray(out, "RGBA")
    img = img.crop(img.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox())
    img = img.resize((round(img.width * HEIGHT / img.height), HEIGHT), Image.LANCZOS)
    img.save(OUT / f"{name}.webp", quality=92, alpha_quality=100, method=6)

    # 確認用：探索の背景に、NPC1 の置き場（駒サイズ40）で立たせる
    play = Image.open(ROOT / "build" / "ccfolia" / "room" / "20_play.jpg").convert("RGBA")
    stage = Image.new("RGBA", (1280 + 420, 720), (4, 4, 4, 255))
    stage.alpha_composite(play.resize((1280, 720)), (0, 0))
    slot = Image.open(ROOT / "build" / "ccfolia" / "room" / "51_slot_npc1.webp")
    stage.alpha_composite(slot, (1280 + 20, 260))             # 前景の右（x=66 マス）
    h = 400                                                   # 駒サイズ40（1マス10px）
    fig = img.resize((round(img.width * h / img.height), h), Image.LANCZOS)
    stage.alpha_composite(fig, (1280 + 20 + 160 - fig.width // 2, 260 + 434 - h))
    stage.convert("RGB").save(OUT / f"{name}_check.png")
    print(OUT / f"{name}.webp", f"{(OUT / f'{name}.webp').stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
