"""カードの外側の黒い縁を、紙の縁から 10px ほどの柔らかい落ち影に作り直す（後処理。文字は描き直さない）。
STYLE「文字の下に四角い地を敷かない」：紙は作中の物なので残し、外側の幅 30px の黒い影（盤面の上で「黒い板の上の紙」に見えた）を細くする。
画像の大きさは変えない（ルームのパネルのマス数がそのまま使える）。何度かけても同じ結果になる。
使い方: python3 tools/card_shadow.py [画像 ...]   （省略時は reward/*、ep8/83_card_*、ep9/87_af_card）"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, label

ROOT = Path(__file__).resolve().parent.parent
FX = ROOT / "build" / "ccfolia" / "fx"


def reshadow(path, reach=10.0, peak=70.0, offset=(2, 3)):
    a = np.asarray(Image.open(path).convert("RGBA")).astype(np.float32)
    al = a[..., 3]
    shadowish = (np.abs(a[..., :3] - 4).max(-1) <= 2) & (al < 250)          # 影（#040404）の画素
    paper = ~shadowish & (al > 0)
    # 外側だけ：画像の縁につながる「紙でない」領域（切り抜きの穴の中の影は残す）
    lab, _ = label(~paper)
    border = np.setdiff1d(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])), [0])
    outer = np.isin(lab, border)
    # 落ち影：紙を少し右下へずらした形から、外へ柔らかく減る（幅 10px ほど）
    pm = np.roll(np.roll(paper, offset[1], 0), offset[0], 1)
    d = distance_transform_edt(~pm)
    sh = peak * np.exp(-(d / (reach / 2.2)) ** 1.5) * pm.any() * outer
    sh = np.where(pm & outer, peak, sh)
    out = a.copy()
    out[..., 3] = np.where(outer, sh, al)
    out[..., :3] = np.where(outer[..., None], 4, a[..., :3])
    out[out[..., 3] < 0.5] = 0                                               # alpha 0 の所は RGB も 0
    img = Image.fromarray(np.clip(np.round(out), 0, 255).astype(np.uint8), "RGBA")
    img.save(path, lossless=True, exact=True)
    return img


if __name__ == "__main__":
    paths = [Path(p) for p in sys.argv[1:]] or (sorted(FX.glob("reward/*.webp")) + sorted(FX.glob("ep8/83_card_*.webp"))
                                                + [FX / "ep9" / "87_af_card.webp"])
    for p in paths:
        reshadow(p)
        print(p)
