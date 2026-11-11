"""第4話「大通り（仮）」の背景：大通りの絵が届くまでの代わり（新しい絵は使わない）。
第3話の住宅街（ep3_01_street）をそのまま使うと、続けて遊ぶ人には同じ場所に見える（監査2の13）。
→ 左右を裏返し、奥の高い建物の並ぶ通りの方へ 1.45 倍に寄せ（手前の植え込みと住宅街の手すりを外す）、
  昼の明るさへ少し持ち上げる（逃げ切った安心。シートの暗さとの対比）。人の雑踏は音（43_avenue_loop）が受け持つ。
出力: build/ccfolia/scenes/ep4_03_avenue_tmp.jpg"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
S = ROOT / "build" / "ccfolia" / "scenes"


def main():
    im = ImageOps.mirror(Image.open(S / "ep3_01_street.jpg").convert("RGB").resize((1280, 720), Image.LANCZOS))
    z = 1.45
    w, h = 1280 / z, 720 / z
    x0, y0 = 1280 - w - 60, 720 - h - 40                         # 裏返した絵の右下：高い建物の並ぶ通りの奥と路面
    im = im.resize((1280, 720), Image.LANCZOS, box=(x0, y0, x0 + w, y0 + h))
    a = np.asarray(im, np.float32) / 255
    a = 1 - (1 - a) ** 1.08                                      # 暗部を持ち上げて昼の明るさに（色味は元の赤茶のまま）
    a += np.random.default_rng(43).normal(0, 1.2 / 255, a.shape[:2])[..., None]   # 拡大でなめらかになりすぎた所に粒子
    Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8)).save(S / "ep4_03_avenue_tmp.jpg", quality=88)
    print(S / "ep4_03_avenue_tmp.jpg")


if __name__ == "__main__":
    main()
