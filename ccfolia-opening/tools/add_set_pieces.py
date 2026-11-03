"""ココフォリアの __data.json に、各話の見せ場のシーンとスクリーンパネルを足し、「追加セット」を作る（流し方は SET-PIECES.local.md）。

使い方: python3 tools/add_set_pieces.py <今の部屋から書き出した __data.json> <出力フォルダ>
  → 出力フォルダの __data.json と新しい画像を、手元のルームデータに上書き・追加して zip し直し、今の部屋に読み込む

決まり（README「わかったこと」）:
  - ココフォリアは読み込んだデータを ID で今の部屋に重ねる。ID は名前から決めるので、何度読み込んでも増えない
  - 必ず「今の部屋から書き出した」__data.json を元にする。古いデータを元にすると、その後に部屋で変えた設定（BGM など）が
    古い状態で上書きされる
  - BGM はルームデータに入らない（ココフォリアに上げた音を参照するだけ）ので、ここでは設定しない
  - スクリーンパネルは、はじめは非表示（KP が見せたいときに表示する）

足すもの:
  シーン   第4話 逃走（シート）／第7話 お祝いですよ／第8話 目覚め／第8話 何度も
  パネル   第3話 人影1〜6（フィールドの外、左右の端）／第3話 チラシ／第7話 報酬（文字化け）／第8話 四択1〜4
"""
import copy
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CC = ROOT / "build" / "ccfolia"
FX = CC / "fx"
S = CC / "scenes"
TYPES = {".jpg": "image/jpeg", ".webp": "image/webp", ".png": "image/png"}

# (シーン名, お手本にするシーン, 背景, 前景)
SCENES = [
    ("第4話 逃走（シート）", "第4話 ブルーシートの現場", S / "ep4_02_bluesheet.jpg", FX / "ep4" / "41_endless_sheet_loop.webp"),
    ("第7話 お祝いですよ", "第7話 水路の合流地点", S / "ep7_04_junction.jpg", FX / "ep7" / "71_oiwai_flood.webp"),
    ("第8話 目覚め", "第8話 家具のない部屋", S / "ep8_01_room.jpg", FX / "shared" / "70_blink_open.webp"),
    ("第8話 何度も", "第8話 家具のない部屋", S / "ep8_01_room.jpg", FX / "ep8" / "84_nandomo.webp"),
]
# (メモ, 画像, x, y, 幅, 高さ)。フィールドは x -64〜64・y -36〜36。PC の置き場はフィールドの下、NPC の置き場は右
PANELS = [(f"第3話 人影{k}", FX / "ep3" / f"31_edge_figure_{k}.webp", x, -34, 8, 24)
          for k, x in zip(range(1, 7), (-74, -84, -94, 132, 142, -104))]
PANELS += [
    ("第3話 チラシ", FX / "ep3" / "32_flyer.webp", -10, -14, 20, 28),
    ("第7話 報酬（文字化け）", FX / "ep7" / "72_reward_mojibake.webp", -19, -9, 38, 18),
]
PANELS += [(f"第8話 四択{k}", FX / "ep8" / f"83_card_{k}.webp", -19, -24 + (k - 1) * 11, 38, 10) for k in range(1, 5)]


def make_id(name, n=20):
    return hashlib.sha256(name.encode()).hexdigest()[:n]


def main(src, outdir):
    data = json.loads(Path(src).read_text(encoding="utf-8"))
    ent, res = data["entities"], data["resources"]
    out = Path(outdir)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)

    def add(path):
        ext = ".jpeg" if path.suffix == ".jpg" else path.suffix
        name = hashlib.sha256(path.read_bytes()).hexdigest() + ext
        if name not in res:
            shutil.copy(path, out / name)
            res[name] = {"type": TYPES[path.suffix]}
        return name

    by_name = {s["name"]: s for s in ent["scenes"].values()}
    for name, base, bg, fg in SCENES:
        if base not in by_name:
            raise SystemExit(f"お手本のシーンがない: {base}")
        sc = copy.deepcopy(by_name[base])
        sc.update(name=name, backgroundUrl=add(bg), foregroundUrl=add(fg), soundRef=None, mediaRef=None)
        sc["order"] = by_name[base]["order"] + 0.05              # お手本のすぐ後ろに並べる
        ent["scenes"][make_id(name)] = sc

    top = max((i.get("order", 0) for i in ent["items"].values()), default=0)
    template = next(iter(ent["items"].values()))
    for k, (memo, img, x, y, w, h) in enumerate(PANELS, 1):
        it = copy.deepcopy(template)
        it.update(x=x, y=y, z=50, width=w, height=h, memo=memo, imageUrl=add(img), active=False, locked=True,
                  visible=True, freezed=False, type="object", order=top + k)
        ent["items"][make_id("panel:" + memo)] = it

    (out / "__data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"シーン {len(SCENES)} 個・スクリーンパネル {len(PANELS)} 枚、画像 {len(list(out.glob('*'))) - 1} 枚を追加")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
