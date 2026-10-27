"""ココフォリアに入れる素材を、話ごとに書き出す。

技術検証（test-kit）の結果から決めた形：
  - 背景・前景・マーカーパネル・BGM は、シーンを切り替えた瞬間に同時に動き出す → 1つのシーンに全部入れる
  - カットインは前回の続きから再生されてしまう → 使わない
  - 1回だけ再生する素材は、動く素材のある別のシーンを経由すると最初からやり直す → 「暗転」シーンを経由する
  - APNG は再生が少しずつ速くなる（1コマの長さが切り捨てられる）→ WebP だけを使う
  - 半透明の層は小さく作って引き伸ばしても自然 → 暗闇の層は 640×360

出力（build/ccfolia/）:
  00_reset_black.webp      … 「暗転」シーンの前景（真っ黒、ループ）
  01_bg_corridor.jpg       … 背景（細かい粒子入り、第一話の形）
  epN/01_bg_corridor_epN.jpg … その話の背景（ドアの隙間がその話の広さ）
  epN/02_dark_epN.webp     … 前景：暗闇が引く・蛍光灯の明滅・カット後の黒（640×360、1回再生）
  epN/03_panel_epN.webp    … マーカーパネル：塵・隙間・一文・タイトル・辞書カード（1280×720、1回再生）
  epN/04_sound_epN.mp3     … BGM：オープニングの音＋無音10分（ループで頭に戻らないように）

使い方: python3 tools/export_ccfolia.py [話数 ...]   （省略時は全9話）
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
OUT = BUILD / "ccfolia"
FPS = json.loads((ROOT / "opening" / "timing.json").read_text(encoding="utf-8"))["fps"]   # 技術検証で24より30がなめらかだった
PAD_SEC = 600                    # OPの音のあとにつなげる無音（秒）
LIMIT = 5 * 1024 * 1024          # PRO の1ファイルの上限
DARK = "reveal,flicker,cutblack"
PANEL = "dust,gap,tagline,title,card"


def run(*cmd):
    subprocess.run(cmd, check=True, cwd=ROOT)


def render(ep, layer, name):
    for attempt in range(3):     # ページの読み込みが時々タイムアウトするため、やり直す
        try:
            run("node", "tools/render_opening.mjs", "--ep", ep, "--layer", layer, "--out", name)
            return
        except subprocess.CalledProcessError:
            if attempt == 2:
                raise


def webp(src, dst, *vf):
    # 可逆圧縮：文字がくっきりし、暗いグラデーションの縞も出ず、この内容では非可逆の画質90より小さい
    run("ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", str(src / "f%04d.png"), *vf,
        "-c:v", "libwebp_anim", "-lossless", "1", "-compression_level", "6", "-loop", "1", str(dst))


def episode(ep):
    d = OUT / f"ep{ep}"
    d.mkdir(parents=True, exist_ok=True)
    background(ep, d / f"01_bg_corridor_ep{ep}.jpg")
    render(ep, DARK, f"cc_dark_ep{ep}")
    webp(BUILD / f"cc_dark_ep{ep}", d / f"02_dark_ep{ep}.webp", "-vf", "scale=640:360:flags=area")
    render(ep, PANEL, f"cc_panel_ep{ep}")
    webp(BUILD / f"cc_panel_ep{ep}", d / f"03_panel_ep{ep}.webp")
    run("python3", "tools/make_audio.py", ep)
    # BGMはループするので、OPのあとに無音を10分つなげて、頭から鳴り直さないようにする。
    # カットインの効果音なら1回で止まるが、シーンの切り替えとは別のクリックになり、映像と音がずれる
    # （可変ビットレートにすると、無音の部分はほとんど容量を食わない）
    run("ffmpeg", "-loglevel", "error", "-y", "-i", str(BUILD / f"opening_audio_ep{ep}.wav"),
        "-af", f"apad=whole_dur={PAD_SEC}", "-c:a", "libmp3lame", "-q:a", "2", str(d / f"04_sound_ep{ep}.mp3"))
    return [(p.relative_to(OUT), p.stat().st_size) for p in sorted(d.iterdir())]


def swing_leaf(img, L, e):
    """ドアの板を、蝶番（左）を軸にこちら側へ開いた形に描き直す（日本の玄関は外開き＝廊下側へ開く）。
    横に縮めるだけだと「細い板の横に黒い板」に見えたため、開いた角度に合わせて
      ・自由端（右）がこちらへ近づく分だけ背が高くなる（台形になり、上下の枠からはみ出す）
      ・自由端に板の厚みの小口が細く見える
      ・板の面は蛍光灯からの光を斜めに受けて少し暗くなる
    空いた分は、部屋の中の暗闇にする（上ほど暗い）"""
    w, h = L["x1"] - L["x0"], L["y1"] - L["y0"]
    cos = (w - e) / w
    sin = (1 - cos ** 2) ** 0.5
    D = 12.0                                                    # カメラまでの距離（板の幅いくつ分か）。遠くのドアなので控えめな遠近
    grow = h * (D / (D - sin) - 1) / 2                          # 自由端の上下への伸び（px）
    thick = max(0.0, 3.0 * sin)                                 # 板の厚みの見え幅（px）
    src = np.asarray(img.crop((L["x0"], L["y0"], L["x1"], L["y1"]))).astype(np.float32)
    a = np.asarray(img).astype(np.float32)
    x0, y0 = L["x0"], L["y0"]
    # 開いた先の暗闇（部屋の中）：上ほど暗く、床の近くだけわずかに廊下の光が差し込む
    for y in range(h):
        k = y / h
        a[y0 + y, x0:x0 + w] = np.array([4, 3, 3]) + np.array([10, 7, 5]) * max(0, k - 0.85) / 0.15
    fw = w - e                                                  # 板の面の見え幅
    for x in range(int(np.ceil(fw + thick)) + 1):
        u = x / max(fw, 1e-6)
        top = -grow * min(u, 1)
        bot = h + grow * min(u, 1)
        if x <= fw:                                             # 板の面：元の板を引き伸ばして写す
            sx = min(int(u * (w - 1)), w - 1)
            col = src[:, sx]
            shade = 1 - 0.35 * sin
        else:                                                   # 小口（板の厚み）：やや明るい細い面
            col = src[:, w - 2] * 0 + np.array([62, 48, 40])
            shade = 1.0
        ys = np.arange(int(np.floor(top)), int(np.ceil(bot)))
        vv = np.clip(((ys - top) / (bot - top) * (h - 1)).astype(int), 0, h - 1)
        X = x0 + x
        if X >= a.shape[1]:
            continue
        for y, v in zip(ys, vv):
            Y = y0 + y
            if 0 <= Y < a.shape[0]:
                a[Y, X] = col[v] * shade
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def background(ep, path):
    """背景：JPG（画質85）＋細かい粒子で、暗いグラデーションの縞を防ぐ。
    話が進むほどドアが開いていく（swing_leaf）。動く層ではなく、話ごとの背景に焼き込む"""
    img = Image.open(ROOT / "opening" / "bg.png").convert("RGB")
    lay = json.loads((ROOT / "opening" / "layout.json").read_text(encoding="utf-8"))
    e = json.loads((ROOT / "opening" / "escalation.json").read_text(encoding="utf-8"))["episodes"][str(ep)]["gapExtra"]
    if lay.get("leaf") and e > 0:
        img = swing_leaf(img, lay["leaf"], e)
    a = np.asarray(img).astype(np.float32)
    a += np.random.default_rng(1).normal(0, 1.5, a.shape[:2])[..., None]
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(path, quality=85)

def shared():
    OUT.mkdir(parents=True, exist_ok=True)
    background(1, OUT / "01_bg_corridor.jpg")                    # 第一話（隙間が広がる前）の背景。部屋の素材にも使う
    # 暗転シーン用：真っ黒の2コマをループ。動く素材のあるシーンを経由すると、1回再生の素材が最初に戻るため
    frames = [Image.new("RGB", (1280, 720), (4, 4, 4)), Image.new("RGB", (1280, 720), (5, 5, 5))]
    frames[0].save(OUT / "00_reset_black.webp", save_all=True, append_images=frames[1:],
                   duration=500, loop=0, lossless=True)


def main():
    eps = sys.argv[1:] or [str(n) for n in range(1, 10)]
    shared()
    with ThreadPoolExecutor(3) as pool:
        results = list(pool.map(episode, eps))
    over = []
    for files in results:
        for name, size in files:
            print(f"{str(name):28s} {size / 1024 / 1024:5.2f} MB")
            if size > LIMIT:
                over.append(name)
    if over:
        raise SystemExit(f"5MB を超えたファイル: {over}")


if __name__ == "__main__":
    main()
