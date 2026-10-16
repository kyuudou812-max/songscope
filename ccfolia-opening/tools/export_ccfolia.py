"""ココフォリアに入れる素材を、話ごとに書き出す。

技術検証（test-kit）の結果から決めた形：
  - 背景・前景・マーカーパネル・BGM は、シーンを切り替えた瞬間に同時に動き出す → 1つのシーンに全部入れる
  - カットインは前回の続きから再生されてしまう → 使わない
  - 1回だけ再生する素材は、動く素材のある別のシーンを経由すると最初からやり直す → 「暗転」シーンを経由する
  - APNG は再生が少しずつ速くなる（1コマの長さが切り捨てられる）→ WebP だけを使う
  - 半透明の層は小さく作って引き伸ばしても自然 → 暗闇の層は 640×360

出力（build/ccfolia/）:
  00_reset_black.webp      … 「暗転」シーンの前景（真っ黒、ループ）
  01_bg_corridor.jpg       … 背景（細かい粒子入り）
  epN/02_dark_epN.webp     … 前景：暗闇が引く・蛍光灯の明滅・カット後の黒（640×360、1回再生）
  epN/03_panel_epN.webp    … マーカーパネル：塵・隙間・一文・タイトル・辞書カード（1280×720、1回再生）
  epN/04_sound_epN.mp3     … BGM：オープニングの音

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
    run("ffmpeg", "-loglevel", "error", "-y", "-framerate", "24", "-i", str(src / "f%04d.png"), *vf,
        "-c:v", "libwebp_anim", "-lossless", "1", "-compression_level", "6", "-loop", "1", str(dst))


def episode(ep):
    d = OUT / f"ep{ep}"
    d.mkdir(parents=True, exist_ok=True)
    render(ep, DARK, f"cc_dark_ep{ep}")
    webp(BUILD / f"cc_dark_ep{ep}", d / f"02_dark_ep{ep}.webp", "-vf", "scale=640:360:flags=area")
    render(ep, PANEL, f"cc_panel_ep{ep}")
    webp(BUILD / f"cc_panel_ep{ep}", d / f"03_panel_ep{ep}.webp")
    run("python3", "tools/make_audio.py", ep)
    run("ffmpeg", "-loglevel", "error", "-y", "-i", str(BUILD / f"opening_audio_ep{ep}.wav"),
        "-c:a", "libmp3lame", "-b:a", "192k", str(d / f"04_sound_ep{ep}.mp3"))
    return [(p.relative_to(OUT), p.stat().st_size) for p in sorted(d.iterdir())]


def shared():
    OUT.mkdir(parents=True, exist_ok=True)
    # 背景：JPG（画質85）＋細かい粒子で、暗いグラデーションの縞を防ぐ
    a = np.asarray(Image.open(ROOT / "opening" / "bg.png").convert("RGB")).astype(np.float32)
    a += np.random.default_rng(1).normal(0, 1.5, a.shape[:2])[..., None]
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(OUT / "01_bg_corridor.jpg", quality=85)
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
