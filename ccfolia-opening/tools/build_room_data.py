"""ココフォリアから書き出したルームデータ（zip）に、まだ作っていない話のシーンを足して、読み込める zip にする。

ルームデータの中身（2026-10 時点、meta.version 1.1.0）:
  __data.json … entities.scenes に各シーン（背景・前景・パネル）、resources に画像の一覧
  画像         … 中身の SHA-256 をファイル名にしたもの（例: 83a3…b7.jpeg）
  .token       … 書き出し元の情報。手を付けずにそのまま入れ直す
BGM（mediaRef / soundRef）は書き出しに含まれないため、ここでは扱わない（ココフォリアで設定する）。

やること:
  - 第3話まで作ってある「OP第N話」「探索第N話」「終了第N話」をお手本に、第4話〜第9話を足す
  - 終了第N話の背景を、その話の「第N話　終」の絵にそろえる
  - 探索の辞書カードを、全話同じ大きさの新しいカード（21_card_epN.webp）に差し替え、パネルを 38×24 マスにする
  - シーンの並び順を「待機・休憩・第1話（OP・探索・終了）・第2話…」に整える
  - どこからも使われなくなった画像を外す

使い方: python3 tools/build_room_data.py <書き出したルーム.zip> <出力.zip>
"""
import copy
import hashlib
import json
import re
import secrets
import string
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CC = ROOT / "build" / "ccfolia"
TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
ID_CHARS = string.ascii_letters + string.digits
CARD_SIZE = (38, 24)              # 探索の辞書カードのパネル（マス）。19×12 では字が小さすぎた


def episode_of(name):
    """「OP第１話」「探索第3話」などから、種類と話数を取り出す（全角数字も読む）"""
    m = re.match(r"(OP|探索|終了)\s*第\s*([0-9０-９]+)\s*話", name.translate(str.maketrans("０１２３４５６７８９", "0123456789")))
    return (m.group(1), int(m.group(2))) if m else (None, None)


def main(src, dst):
    work = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(src) as z:
        for info in z.infolist():                   # zip の中のパスは信用せず、ファイル名だけを使う
            name = Path(info.filename).name
            if name and not info.is_dir():
                (work / name).write_bytes(z.read(info))
    data = json.loads((work / "__data.json").read_text(encoding="utf-8"))
    scenes = data["entities"]["scenes"]
    resources = data["resources"]

    def add(path):
        """画像をルームデータに入れ、ココフォリアと同じ名前（中身の SHA-256＋拡張子）を返す"""
        ext = ".jpeg" if path.suffix == ".jpg" else path.suffix
        name = hashlib.sha256(path.read_bytes()).hexdigest() + ext
        (work / name).write_bytes(path.read_bytes())
        resources[name] = {"type": TYPES[path.suffix]}
        return name

    def assets(ep):
        return {"dark": add(CC / f"ep{ep}" / f"02_dark_ep{ep}.webp"), "panel": add(CC / f"ep{ep}" / f"03_panel_ep{ep}.webp"),
                "card": add(CC / "room" / f"21_card_ep{ep}.webp"), "end": add(CC / "room" / f"40_end_ep{ep}.jpg")}

    def apply(kind, scene, a):
        if kind == "OP":
            scene["foregroundUrl"] = a["dark"]
            for m in scene["markers"].values():
                m["imageUrl"] = a["panel"]
        elif kind == "探索":
            for m in scene["markers"].values():
                m["imageUrl"] = a["card"]
                m["width"], m["height"] = CARD_SIZE
        elif kind == "終了":
            scene["backgroundUrl"] = a["end"]

    # 既にある話：中身をその話の素材にそろえる（終了の絵の取り違えや、カードの大きさの違いを直す）
    have = {}
    for sid, s in scenes.items():
        kind, ep = episode_of(s["name"])
        if kind:
            have[(kind, ep)] = sid
            apply(kind, s, assets(ep))
    last = max(ep for _, ep in have)
    # 足りない話：いちばん新しい話のシーンをお手本に作る
    for ep in range(1, 10):
        a = None
        for kind in ("OP", "探索", "終了"):
            if (kind, ep) in have:
                continue
            a = a or assets(ep)
            s = copy.deepcopy(scenes[have[(kind, last)]])
            s["name"] = f"{kind}第{ep}話"
            apply(kind, s, a)
            sid = "".join(secrets.choice(ID_CHARS) for _ in range(20))
            scenes[sid] = s
            have[(kind, ep)] = sid
    # 並び順：待機・休憩・各話（OP・探索・終了）。それ以外のシーンは最後に残す
    fixed = {"待機": 1, "休憩": 2}
    for sid, s in scenes.items():
        kind, ep = episode_of(s["name"])
        s["order"] = fixed.get(s["name"], 10 * ep + ("OP", "探索", "終了").index(kind) if kind else 1000 + s["order"])

    # どこからも使われていない画像を外す
    text = json.dumps(data["entities"], ensure_ascii=False)
    for name in [n for n in resources if n not in text]:
        del resources[name]
        (work / name).unlink(missing_ok=True)
    (work / "__data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(work.iterdir()):
            z.write(p, p.name)
    for sid, s in sorted(scenes.items(), key=lambda kv: kv[1]["order"]):
        print(f"{s['order']:>7}  {s['name'] or '（名前なし）'}")
    print(f"→ {dst}（{Path(dst).stat().st_size / 1024 / 1024:.1f} MB、画像 {len(resources)} 枚）")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
