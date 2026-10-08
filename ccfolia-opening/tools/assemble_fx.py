"""build/fx/ の各演出に名前を入れてつなぎ、1本のサンプル動画にする。
あわせて、ココフォリアに入れた場合の容量の目安（アニメーションWebP）を測る。

使い方: python3 assemble_fx.py
出力: build/fx_reel.mp4, build/fx_sizes.tsv
"""
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FX = ROOT / "build" / "fx"
FONT = ROOT / "fonts" / "ZenKakuGothicNew-Medium.ttf"

LABELS = [
    ("ink", "1 文字がにじみ出る（SVGフィルター）"),
    ("glitch", "2 グリッチ（色ずれ・横ずれ）"),
    ("dissolve", "3 文字が粒になって崩れる（Canvas）"),
    ("kinetic", "4 縦書きが1文字ずつ降りる（GSAP）"),
    ("flicker", "5 蛍光灯の明滅"),
    ("dust", "6 光の筋に舞うほこり"),
    ("smoke", "7 渦巻く煙（WebGLシェーダー）"),
    ("vignette", "8 暗闇が周りから迫る（シェーダー）"),
    ("film", "9 古いフィルムの傷と揺れ"),
    ("vhs", "10 ビデオテープの乱れ"),
    ("parallax", "11 奥へ進むカメラ（Three.js）"),
    ("burn", "12 焼けるように消える（シェーダー）"),
    ("flash", "13 一瞬だけ反転（サブリミナル）"),
    ("torch", "14 懐中電灯で照らす"),
]


def run(*cmd):
    subprocess.run(cmd, check=True)


def main():
    tmp = Path(tempfile.mkdtemp())
    parts, rows = [], ["name\tlabel\twebp_1280x720_24fps_MB\twebp_640x360_12fps_MB"]
    for k, (name, label) in enumerate(LABELS):
        src = FX / name / "f%04d.png"
        if not (FX / name / "f0000.png").exists():
            continue
        part = tmp / f"{k:02d}.mp4"
        text = label.replace(":", r"\:")
        run("ffmpeg", "-loglevel", "error", "-y", "-framerate", "24", "-i", str(src),
            "-vf", f"drawtext=fontfile={FONT}:text='{text}':x=32:y=h-56:fontsize=26:fontcolor=white@0.9:"
                   "box=1:boxcolor=black@0.55:boxborderw=10",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(part))
        parts.append(part)
        sizes = []
        for scale, fps in (("1280:720", 24), ("640:360", 12)):
            w = tmp / f"{name}_{fps}.webp"
            run("ffmpeg", "-loglevel", "error", "-y", "-framerate", "24", "-i", str(src),
                "-vf", f"fps={fps},scale={scale}", "-c:v", "libwebp_anim", "-quality", "75", "-loop", "0", str(w))
            sizes.append(f"{w.stat().st_size / 1e6:.2f}")
        rows.append("\t".join([name, label] + sizes))
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    run("ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
        str(ROOT / "build" / "fx_reel.mp4"))
    (ROOT / "build" / "fx_sizes.tsv").write_text("\n".join(rows) + "\n")
    print("\n".join(rows))


if __name__ == "__main__":
    main()
