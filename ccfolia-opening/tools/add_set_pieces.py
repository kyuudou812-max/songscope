"""ココフォリアの __data.json に、各話の見せ場のシーンとスクリーンパネルを足し、「追加セット」を作る（流し方は SET-PIECES.local.md）。

使い方: python3 tools/add_set_pieces.py <今の部屋から書き出した __data.json> <出力フォルダ>
  → 出力フォルダの __data.json と新しい画像を、手元のルームデータに上書き・追加して zip し直し、今の部屋に読み込む

決まり（README「わかったこと」）:
  - ココフォリアは読み込んだデータを ID で今の部屋に重ねる。ID は名前から決めるので、何度読み込んでも増えない
  - 必ず「今の部屋から書き出した」__data.json を元にする。古いデータを元にすると、その後に部屋で変えた設定（BGM など）が
    古い状態で上書きされる
  - BGM はルームデータに入らない（ココフォリアに上げた音を参照するだけ）ので、ここでは設定しない
  - スクリーンパネルは、はじめは非表示（KP が見せたいときに表示する）

足すもの（一覧は下の SCENES・PANELS）:
  シーン   第1話の居眠り・目を覚ます／第4話の逃走・大通り／第7話のお祝いですよ／第8話の目覚め・何度も／
           最終話のロビー（明滅）・ホール（人数別）・古い映画・暗闇の女・暗闇証明の各段階／エンドAの最後の廊下
  パネル   第3話の人影・チラシ／第5話のスマホ・訃報・震えた文字／第7話の行列／第1〜7話の報酬の札（裏面は切り抜き）／
           第8話の四択（裏面は切り抜き）／第2〜9話の前回のあらすじ
  最終話の「開ききったドア」と「古い映画」の絵が届くまでは、試作版（_draft）の画像で入る
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
E9 = FX / "ep9"
DRAFT = "_draft" if not (E9 / "90_full_door_bg.jpg").exists() else ""      # 開ききったドアの絵が届くまでは試作版
FILM = "_draft" if not (E9 / "92_film_loop.webp").exists() else ""
SCENES = [
    ("第1話 居眠り", "第1話 会議室", S / "ep1_01_conference.jpg", FX / "shared" / "72_blink_close.webp"),
    ("第1話 目を覚ます", "第1話 会議室", S / "ep1_01_conference.jpg", FX / "shared" / "71_blink_reopen.webp"),
    ("第4話 逃走（シート）", "第4話 ブルーシートの現場", S / "ep4_02_bluesheet.jpg", FX / "ep4" / "41_endless_sheet_loop.webp"),
    ("第4話 大通り（仮）", "第4話 ブルーシートの現場", S / "ep3_01_street.jpg", None),
    ("第7話 お祝いですよ", "第7話 水路の合流地点", S / "ep7_04_junction.jpg", FX / "ep7" / "71_oiwai_flood.webp"),
    ("第8話 目覚め", "第8話 家具のない部屋", S / "ep8_01_room.jpg", FX / "shared" / "70_blink_open.webp"),
    ("第8話 何度も", "第8話 家具のない部屋", S / "ep8_01_room.jpg", FX / "ep8" / "84_nandomo.webp"),
    ("第9話 ロビー（明滅）", "第9話 廃劇場のロビー", S / "ep9_01_lobby.jpg", E9 / "98_lobby_flicker_loop.webp"),
    ("第9話 ホール（PC1人）", "第9話 劇場のホール", E9 / "97_hall_1pc.jpg", None),
    ("第9話 ホール（PC2人）", "第9話 劇場のホール", E9 / "97_hall_2pc.jpg", None),
    ("第9話 ホール（PC3人）", "第9話 劇場のホール", E9 / "97_hall_3pc.jpg", None),
    ("第9話 古い映画（上映中）", "第9話 劇場のホール", S / "ep9_02_hall.jpg", E9 / f"92_film_loop{FILM}.webp"),
    ("第9話 古い映画（途切れる）", "第9話 劇場のホール", S / "ep9_02_hall.jpg", E9 / f"93_film_cut{FILM}.webp"),
    ("第9話 暗闇の女", "第9話 劇場のホール", E9 / f"90_full_door_bg{DRAFT}.jpg", E9 / f"91_woman_darkness{DRAFT}.webp"),
    ("第9話 暗闇証明0（完全）", "第9話 劇場のホール", E9 / f"90_full_door_bg{DRAFT}.jpg", E9 / f"99_proof_0{DRAFT}.webp"),
    ("第9話 暗闇証明1（ほどける）", "第9話 劇場のホール", E9 / f"90_full_door_bg{DRAFT}.jpg", E9 / f"99_proof_1{DRAFT}.webp"),
    ("第9話 暗闇証明2（大きくほどける）", "第9話 劇場のホール", E9 / f"90_full_door_bg{DRAFT}.jpg", E9 / f"99_proof_2{DRAFT}.webp"),
    ("第9話 暗闇証明3（何もない）", "第9話 劇場のホール", E9 / f"90_full_door_bg{DRAFT}.jpg", E9 / f"99_proof_3{DRAFT}.webp"),
    ("第9話 暗闇証明（女が近づく）", "第9話 劇場のホール", E9 / f"90_full_door_bg{DRAFT}.jpg", E9 / f"99_proof_reach{DRAFT}.webp"),
    ("エンドA 最後の廊下", "第9話 劇場のホール", CC / "01_bg_corridor.jpg", CC / "room" / "11_grain_loop.webp"),
]
# (メモ, 画像, x, y, 幅, 高さ, 裏面)。フィールドは x -64〜64・y -36〜36。PC の置き場はフィールドの下、NPC の置き場は右
PANELS = [(f"第3話 人影{k}", FX / "ep3" / f"31_edge_figure_{k}.webp", x, -34, 8, 24, None)
          for k, x in zip(range(1, 7), (-74, -84, -94, 132, 142, -104))]
PANELS += [
    ("第3話 チラシ", FX / "ep3" / "32_flyer.webp", -10, -14, 20, 28, None),
    ("第5話 スマホのニュース", FX / "ep5" / "56_phone_news.webp", -7, -14, 14, 27, None),
    ("第5話 新聞の訃報", FX / "ep5" / "54_obituary.webp", -12, -15, 24, 30, None),
    ("第5話 震えた文字", FX / "ep5" / "55_kamisama.webp", -19, -9, 38, 19, None),
    ("第7話 行列（PC の後ろ）", FX / "ep7" / "73_queue_panel.webp", -64, 36, 128, 54, None),
]
# 報酬の札：3枚を横に並べる。裏面は切り抜かれた札（KP が裏返すと切り抜ける）
PANELS += [(f"第{ep}話 報酬{k}", FX / "reward" / f"ep{ep}_reward{k}.webp", -59 + (k - 1) * 41, -11, 37, 21,
            FX / "reward" / f"ep{ep}_reward{k}_cut.webp") for ep in range(1, 8) for k in range(1, 4)]
PANELS += [(f"第8話 四択{k}", FX / "ep8" / f"83_card_{k}.webp", -19, -26 + (k - 1) * 12, 38, 11,
            FX / "ep8" / f"83_card_{k}_cut.webp") for k in range(1, 5)]
PANELS += [(f"第{ep}話 前回のあらすじ", FX / "recap" / f"recap_ep{ep}.webp", -19, -12, 38, 24, None) for ep in range(2, 10)]


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
        sc.update(name=name, backgroundUrl=add(bg), foregroundUrl=add(fg) if fg else None, soundRef=None, mediaRef=None)
        sc["order"] = by_name[base]["order"] + 0.05              # お手本のすぐ後ろに並べる
        ent["scenes"][make_id(name)] = sc

    top = max((i.get("order", 0) for i in ent["items"].values()), default=0)
    template = next(iter(ent["items"].values()))
    for k, (memo, img, x, y, w, h, cover) in enumerate(PANELS, 1):
        it = copy.deepcopy(template)
        it.update(x=x, y=y, z=0 if "行列" in memo else 50, width=w, height=h, memo=memo, imageUrl=add(img),
                  coverImageUrl=add(cover) if cover else None, closed=False, active=False, locked=True,
                  visible=True, freezed=False, type="object", order=top + k)
        ent["items"][make_id("panel:" + memo)] = it

    (out / "__data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"シーン {len(SCENES)} 個・スクリーンパネル {len(PANELS)} 枚、画像 {len(list(out.glob('*'))) - 1} 枚を追加")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
