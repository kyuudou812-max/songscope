"""ココフォリアの __data.json に、各話の場面の背景シーンを足し、「追加セット」（__data.json と新しい画像だけ）を作る。

ルームデータ全体は大きいので、やりとりは __data.json だけにする。画像は中身の SHA-256 が名前なので、
新しく足す画像だけを入れれば、手元の展開したフォルダに上書き・追加して zip し直すだけで読み込める。

各場面のシーンは、その話の「探索第N話」をお手本に背景だけ差し替える（辞書カードのパネルもそのまま）。
第五話の「夕暮れの団地の廊下」だけは、蛾の羽ばたきの前景を付ける（BGM はココフォリアで設定）。

使い方: python3 tools/add_scene_backgrounds.py <__data.json> <出力フォルダ>
"""
import copy
import hashlib
import json
import re
import secrets
import shutil
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CC = ROOT / "build" / "ccfolia"
S = CC / "scenes"
M = CC / "moth"
SCENES = {   # 話 → [(シーン名, 背景, 前景)]
    1: [("会議室", S / "ep1_01_conference.jpg", None)],
    2: [("イベント会場", S / "ep2_01_event.jpg", None), ("休憩所のテント", S / "ep2_02_tent.jpg", None),
        ("資材置き場", S / "ep2_03_storage.jpg", None)],
    3: [("住宅街の道", S / "ep3_01_street.jpg", None), ("町内掲示板", S / "ep3_02_board.jpg", None)],
    4: [("路地と規制線", S / "ep4_01_alley.jpg", None), ("ブルーシートの現場", S / "ep4_02_bluesheet.jpg", None)],
    5: [("朝・蛾", S / "ep5_00_morning_moth.jpg", None), ("蛾のドアップ", M / "54_moth_closeup.jpg", None),
        ("夕暮れの廊下（羽ばたき）", S / "ep5_01_corridor.jpg", M / "52_moth_flap.webp"),
        ("玄関", S / "ep5_02_entrance.jpg", None), ("ダイニングキッチン", S / "ep5_03_kitchen.jpg", None),
        ("奥の部屋", S / "ep5_04_backroom.jpg", None)],
    6: [("ファミレス", S / "ep6_01_restaurant.jpg", None)],
    7: [("雨の町と行列", S / "ep7_01_rain.jpg", None), ("高架下と階段", S / "ep7_02_underpass.jpg", None),
        ("地下水路", S / "ep7_03_channel.jpg", None), ("水路の合流地点", S / "ep7_04_junction.jpg", None)],
    8: [("家具のない部屋", S / "ep8_01_room.jpg", None)],
    9: [("廃劇場のロビー", S / "ep9_01_lobby.jpg", None), ("劇場のホール", S / "ep9_02_hall.jpg", None)],
}
TYPES = {".jpg": "image/jpeg", ".webp": "image/webp", ".png": "image/png"}


def ep_of(name):
    m = re.match(r"探索\s*第\s*([0-9０-９]+)\s*話", name.translate(str.maketrans("０１２３４５６７８９", "0123456789")))
    return int(m.group(1)) if m else None


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

    play = {ep_of(s["name"]): (sid, s) for sid, s in ent["scenes"].items() if ep_of(s["name"])}
    have = {s["name"] for s in ent["scenes"].values()}
    added = []
    for ep, rows in SCENES.items():
        base = play[ep][1]
        for k, (title, bg, fg) in enumerate(rows, 1):
            name = f"第{ep}話 {title}"
            if name in have:
                continue
            sc = copy.deepcopy(base)
            sc["name"] = name
            sc["backgroundUrl"] = add(bg)
            sc["foregroundUrl"] = add(fg) if fg else None
            sc["order"] = base["order"] + k / 10                 # 探索第N話 と 終了第N話 の間に並べる
            ent["scenes"]["".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(20))] = sc
            added.append(name)
    # 場面の切り替えはクロスフェード（ふわっと重ねる）。第五話の羽ばたきは最初のコマが暗いので、重ねても成り立つ
    ent["room"]["enableCrossfade"] = True
    ent["room"]["crossfadeDuration"] = 1
    (out / "__data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"シーン {len(added)} 個、画像 {len(list(out.glob('*'))) - 1} 枚を追加")
    for n in added:
        print(" ", n)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
