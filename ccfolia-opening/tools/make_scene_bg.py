"""ChatGPT で作った場面の背景を、OP・部屋と同じ空気にそろえてココフォリア用に書き出す。

やること（STYLE.md・SCENES.md の方針）:
  1. 1280×720 に切り抜く（16:9 でなければ中央を使う）
  2. 明るさだけを残し、廊下の絵（opening/bg.png）の「明るさ→色」の対応で赤茶をかけ直す（NPCの立ち絵と同じ物差し）
  3. 四隅を少し落とし、全体を少し暗くする（駒・カード・チャットの文字が背景に負けないように）。昼の場面は --light で控えめに
  4. 細かい粒子を混ぜて JPG（画質85）にする（暗いグラデーションの縞を防ぐ）
  5. 確認用に、辞書カードと駒の置き場を重ねた絵も書き出す

使い方: python3 tools/make_scene_bg.py <元の画像> <出力名（例: ep4_alley）> [--light]
出力: build/ccfolia/scenes/<出力名>.jpg と <出力名>_check.jpg
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_npc_portrait import tone_lut  # noqa: E402  同じ色の物差しを使う

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "ccfolia" / "scenes"


def main(src, name, light=False):
    OUT.mkdir(parents=True, exist_ok=True)
    img = ImageOps.fit(Image.open(src).convert("RGB"), (1280, 720), Image.LANCZOS)
    a = np.asarray(img).astype(np.float32)
    lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
    lum = lum / 255 * 236 + 6                                   # 真っ白・真っ黒にしない
    yy, xx = np.mgrid[0:720, 0:1280].astype(np.float32)
    vignette = np.clip(1 - 0.55 * (((xx - 640) / 760) ** 2 + ((yy - 340) / 470) ** 2), 0.35, 1)
    lum = lum * (0.85 if light else 0.62) * vignette             # 夜・室内は暗めに沈める
    rgb = lum[..., None] * tone_lut()[np.clip(lum, 0, 255).astype(int)]
    rgb += np.random.default_rng(4).normal(0, 1.5, rgb.shape[:2])[..., None]
    out = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    out.save(OUT / f"{name}.jpg", quality=85)

    # 確認用：辞書カード（第一話）と、PC・NPC の置き場を重ねる（前景の外も見えるよう広めに）
    room = ROOT / "build" / "ccfolia" / "room"
    U = 10
    canvas = Image.new("RGBA", (1280 + 380, 720 + 500), (4, 4, 4, 255))
    canvas.alpha_composite(out.convert("RGBA"), (0, 0))
    card = room / "21_card_ep1.webp"
    if card.exists():
        canvas.alpha_composite(Image.open(card).resize((38 * U, 24 * U)), (0, 0))
    for k in range(4):
        canvas.alpha_composite(Image.open(room / f"50_slot_pc{k + 1}.webp"), (k * 32 * U, 74 * U))
    canvas.alpha_composite(Image.open(room / "51_slot_npc1.webp"), (130 * U, 26 * U))
    canvas.convert("RGB").resize((830, 610)).save(OUT / f"{name}_check.jpg", quality=85)
    print(OUT / f"{name}.jpg", f"{(OUT / f'{name}.jpg').stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(args[0], args[1], light="--light" in sys.argv)
