"""各話の見せ場の素材を書き出す（どれをいつ流すかは SET-PIECES.md）。

考え方（README「わかったこと」・PREP.local.md「各話の見せ場」）:
  - 1つの見せ場は、ココフォリアのシーンを1回切り替えるだけで、絵と音が同時に動くように作る
  - 動かなくても、KP が本文を読めば成り立つ（演出は上乗せ）
  - シナリオの文は set-pieces.local.json から読む（git の対象外）

出力（build/ccfolia/fx/）:
  shared/70_blink_open.webp     … まぶたが開く（前景、640×360、1回再生）。第八話の目覚め
  shared/71_blink_reopen.webp   … まばたき（閉じた状態から開く。前景、1回再生）。第四話の「瞬きの間に」
  ep8/81_room_tone_loop.mp3     … 家具のない部屋の空気（BGM、ループ）。「妙に静かだ」で KP が止める
  ep8/82_bang_gust.mp3          … 窓が開く「バン」→ 突風とカーテンのはためき（BGM。頭の一撃はシーンの切り替えと同時）
  ep8/83_card_1〜4.webp         … 四択のカード（スクリーンパネル、38×10 マス）
  ep8/84_nandomo.webp           … 「何度も」が画面を埋めて真っ黒になる（前景、1280×720、1回再生）
  ep8/85_shepard_then_silence.mp3 … 上がり続ける音 → 真っ黒になるコマで無音（BGM。前景と同時に始まる）
  preview/*.mp4                 … 確認用（背景に重ねて、音付き）

使い方: python3 tools/make_set_pieces.py [ep8 ep2 ...]   （省略時は全部）
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageSequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fxlib import (BLACK, ROOT, SR, TEXT, click, env, filt, font, halo, loop_seam, noise, norm, place,  # noqa: E402
                   resonate, reverb, save_webp_anim, sec, silence, smooth_random, thump, vchar, write_mp3)

OUT = ROOT / "build" / "ccfolia" / "fx"
SCENES = ROOT / "build" / "ccfolia" / "scenes"
FPS = json.loads((ROOT / "opening" / "timing.json").read_text(encoding="utf-8"))["fps"]
TXT = json.loads((ROOT / "set-pieces.local.json").read_text(encoding="utf-8"))


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def ease_out(x):
    x = np.clip(x, 0, 1)
    return 1 - (1 - x) ** 3


def preview(bg, frames, audio, name, fps=FPS, tail=1.0):
    """確認用の動画：背景の絵に前景のコマを重ね、音を付ける（frames は RGBA の Image の列か、webp のパス）"""
    if isinstance(frames, (str, Path)):
        frames = [f.convert("RGBA") for f in ImageSequence.Iterator(Image.open(frames))]
    base = Image.open(bg).convert("RGBA").resize((1280, 720)) if bg else Image.new("RGBA", (1280, 720), BLACK + (255,))
    d = OUT / "preview"
    d.mkdir(parents=True, exist_ok=True)
    n = len(frames) + int(tail * fps)
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1280x720",
                          "-r", str(fps), "-i", "-", "-i", str(audio), "-map", "0:v", "-map", "1:a", "-t", f"{n / fps:.3f}",
                          "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
                          str(d / f"{name}.mp4")], stdin=subprocess.PIPE)
    for i in range(n):
        f = frames[min(i, len(frames) - 1)].resize((1280, 720))
        p.stdin.write(Image.alpha_composite(base, f).convert("RGB").tobytes())
    p.stdin.close()
    p.wait()
    print(f"preview/{name}.mp4")


# ================================================================ 共通：まぶた
def lids(open_, w=640, h=360, feather=0.3):
    """まぶたの形（横長の楕円の外側が黒）。open_=0 で閉じ、1.3 で画面の外まで開く"""
    if open_ <= 0.01:
        return Image.new("RGBA", (w, h), BLACK + (255,))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a = w * (0.55 + 0.6 * open_)
    b = max(h * 0.62 * open_, 0.5)
    r = np.sqrt(((xx - w / 2) / a) ** 2 + ((yy - h * 0.48) / b) ** 2)
    alpha = smoothstep(1 - feather, 1 + feather, r)
    im = np.zeros((h, w, 4), np.uint8)
    im[..., :3] = BLACK
    im[..., 3] = (alpha * 255).astype(np.uint8)
    return Image.fromarray(im, "RGBA")


def blink_open():
    """目覚め：真っ黒 → 細く開く → 一度閉じかける → ゆっくり開ききる（映画の主観ショットの目覚め）"""
    keys = [(0.0, 0.0), (0.7, 0.0), (1.3, 0.22), (1.6, 0.25), (1.9, 0.04), (2.2, 0.04), (3.4, 1.35)]
    t_end = keys[-1][0] + 0.2
    frames = []
    for i in range(int(t_end * FPS) + 1):
        t = i / FPS
        for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
            if t0 <= t <= t1:
                k = (t - t0) / max(t1 - t0, 1e-6)
                v = v0 + (v1 - v0) * (ease_out(k) if v1 > v0 else k * k * (3 - 2 * k))
                break
        else:
            v = keys[-1][1]
        # 開きかけほど縁がぼやける（焦点が合っていない）
        frames.append(lids(v, feather=0.12 + 0.35 * (1 - min(v, 1))))
    frames.append(Image.new("RGBA", (640, 360), (0, 0, 0, 0)))
    save_webp_anim(frames, OUT / "shared" / "70_blink_open.webp")
    return frames


def blink_reopen():
    """まばたき：閉じたところから、すっと開く（シーンの切り替えと同時に流すと、まばたきの間に景色が変わったように見える）"""
    frames = [lids(0.0)] * 4
    n = int(0.45 * FPS)
    frames += [lids(1.35 * ease_out((i + 1) / n), feather=0.12 + 0.25 * (1 - (i + 1) / n)) for i in range(n)]
    frames.append(Image.new("RGBA", (640, 360), (0, 0, 0, 0)))
    save_webp_anim(frames, OUT / "shared" / "71_blink_reopen.webp")
    return frames


# ================================================================ 第八話
def room_tone():
    """家具のない部屋の空気：低い空気の流れと、耳の奥で鳴るようなごく小さな高い音（雑音を絞ったもの）。
    無音は、それまで鳴っていた音が消えた瞬間にだけ「静けさ」として聞こえる。「妙に静かだ」の一文で KP が止める"""
    L = 62
    air = filt(noise(L, 81), hi=260, order=2) * (0.7 + 0.3 * smooth_random(L, 0.15, 82))
    hiss = filt(noise(L, 83), 5200, 7800, order=2) * 0.05 * (0.6 + 0.4 * smooth_random(L, 0.1, 84))
    x = loop_seam(air + hiss, 2.0)
    write_mp3(OUT / "ep8" / "81_room_tone_loop.mp3", norm(x, 0.22))
    return x


def bang_gust(minutes=6):
    """窓が開け放たれる「バン」→ 突風。カーテンが暴れる音（布がはためく：短い雑音の連なり）を、強い風のときだけ重ねる"""
    L = minutes * 60
    # バン：重いサッシが端に当たる低い音＋硬い衝突＋ガラスと金具の短い鳴り
    hit = thump(70, 0.18, 1, 0.8) * 0.9
    hit = place(hit, click(1200, 7000, 0.01, 2) * 0.7, 0)
    rattle = resonate(noise(0.6, 3) * env(sec(0.6), 0.001, 0.07), [2300, 3100, 4400, 5900], q=60) * 1.2
    hit = place(hit, rattle, 0.004)
    hit = reverb(hit, 0.7, 0.35)
    # 突風：暗い風と明るい風を、風の強さで混ぜる
    gust = smooth_random(L, 0.35, 11) ** 1.6
    gust = np.maximum(gust, 0.05)
    gust[: sec(1.0)] = np.maximum(gust[: sec(1.0)], np.linspace(1, 0.6, sec(1.0)))   # 開いた瞬間がいちばん強い
    dark = filt(noise(L, 12), hi=500, order=2)
    bright = filt(noise(L, 13), 600, 2600, order=2)
    wind = dark * (0.4 + 0.6 * gust) + bright * gust ** 1.5 * 0.8
    # カーテンのはためき：10〜16回/秒の、ばらつきのある布の音
    flap_rate = 10 + 6 * smooth_random(L, 0.5, 14)
    phase = np.cumsum(flap_rate / SR)
    flutter = (0.5 + 0.5 * np.sin(2 * np.pi * phase)) ** 6
    cloth = filt(noise(L, 15), 400, 3500, order=2) * flutter * np.clip(gust - 0.35, 0, 1) * 1.6
    x = norm(wind + cloth, 0.55)
    x = place(x, hit * 0.95, 0.0)
    x[: sec(0.02)] *= np.linspace(0, 1, sec(0.02))
    write_mp3(OUT / "ep8" / "82_bang_gust.mp3", norm(x, 0.85), q=6)     # mp3 にすると山が少し高くなるので余裕を残す
    return x


def cards():
    """四択の問い：横長のカード4枚（辞書カードと同じ文字。760×200、パネル 38×10 マス＝辞書カードと同じ幅）"""
    out = []
    for k, q in enumerate(TXT["ep8_questions"], 1):
        im = Image.new("RGBA", (760, 200), (0, 0, 0, 0))
        f = font(30)
        d = ImageDraw.Draw(im)
        widths = [f.getlength(c) for c in q]
        sp = 30 * 0.15
        w = sum(widths) + sp * (len(q) - 1)
        assert w < 680, q
        x = (760 - w) / 2
        for c, cw in zip(q, widths):
            d.text((x, 80), c, font=f, fill=TEXT + (255,))
            x += cw + sp
        im = halo(im)
        im.save(OUT / "ep8" / f"83_card_{k}.webp", lossless=True)
        out.append(im)
    return out


def nandomo():
    """「何度も」が縦書きで画面を埋めていく。はじめは読める速さで、だんだん加速し、埋まりきった瞬間に真っ黒。
    同じ時間で上がり続ける音（85_shepard_then_silence.mp3）が、真っ黒のコマで止まる"""
    size, pitch, top = 28, 38, 22
    rows = (720 - top * 2) // (size + 4)
    cols = (1280 - 60) // pitch
    head = TXT["ep8_again_head"]
    cells = []                                                  # (列, 行, 文字)
    col = 0
    for line in head:                                           # 冒頭の2行は、それぞれ新しい列から
        for r, c in enumerate(line):
            cells.append((col, r, c))
        col += 1
    total = (cols - col) * rows
    unit = TXT["ep8_again_unit"]
    body = (unit * (total // len(unit) + 1))[: total - 1] + "。"
    for i, c in enumerate(body):
        cells.append((col + i // rows, i % rows, c))
    # 1コマに何文字出すか：冒頭は3コマに1文字、そこから指数的に加速
    n_head = sum(len(s) for s in head)
    sched, t, shown = [], 0, 0
    while shown < len(cells):
        if shown < n_head:
            rate = 1 / 3
        else:
            rate = (1 / 3) * np.exp((t - n_head * 3) / 58)
        shown_f = min(len(cells), (sched[-1][1] if sched else 0) + rate)
        sched.append((t, shown_f))
        shown = int(shown_f)
        t += 1
    f = font(size)
    layer = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    frames, drawn = [], 0
    for t, shown_f in sched:
        for (cl, r, c) in cells[drawn:int(shown_f)]:
            x = 1280 - 50 - (cl + 1) * pitch + (pitch - size) / 2
            vchar(d, x, top + r * (size + 4), c, f, size, TEXT + (255,))
        drawn = int(shown_f)
        dim = Image.new("RGBA", (1280, 720), BLACK + (int(150 * min(1, t / FPS)),))   # 最初の1秒で背景を沈める
        frames.append(Image.alpha_composite(dim, halo(layer, 5, 6, 1.3)) if drawn else dim)
    hold = int(0.35 * FPS)
    frames += [frames[-1]] * hold
    frames.append(Image.new("RGBA", (1280, 720), BLACK + (255,)))     # 真っ黒（ここで音も止まる）
    save_webp_anim(frames, OUT / "ep8" / "84_nandomo.webp")
    return frames


def shepard(duration, pad=600):
    """上がり続ける音（シェパード・トーン）：1オクターブずつ離れた音が、いっしょに上がり続け、
    上の端で消え下の端から現れるので、終わりなく上がって聞こえる（映画『ダンケルク』の緊張の作り方）。
    文字の加速に合わせて上がる速さも増す。前景が真っ黒になるコマで、ぷつりと止めて無音を残す"""
    n = sec(duration)
    t = np.arange(n) / SR
    rate = 1 / 9 + (1 / 2.2 - 1 / 9) * (t / duration) ** 2     # オクターブ/秒
    u = np.cumsum(rate) / SR
    fmin, N = 30.0, 8
    x = np.zeros(n, np.float32)
    for k in range(N):
        pos = (k + u) % N                                       # 下の端から何オクターブ目か
        f = fmin * 2 ** pos
        amp = np.exp(-0.5 * ((pos - 3.6) / 1.25) ** 2)          # 真ん中（約360Hz）がいちばん大きく、端で消える
        ph = np.cumsum(2 * np.pi * f / SR)
        x += (amp * (np.sin(ph) + 0.25 * np.sin(2 * ph + 0.3))).astype(np.float32)
    # 低いうなりと、息のような雑音を薄く重ねて、澄みすぎないようにする
    x += filt(noise(duration, 85), 200, 1200) * 0.35 * (t / duration)
    x *= (0.35 + 0.65 * (t / duration) ** 1.4)                  # だんだん大きく
    x[: sec(0.3)] *= np.linspace(0, 1, sec(0.3))
    x = norm(x, 0.8)
    x[-sec(0.004):] *= np.linspace(1, 0, sec(0.004))            # ぷつりと切る（クリック音が出ない最小限）
    out = np.concatenate([x, silence(pad)])
    write_mp3(OUT / "ep8" / "85_shepard_then_silence.mp3", out, q=5)
    return out


def ep8():
    fr = blink_open()
    tone = room_tone()
    wav = OUT / "preview" / "tmp.wav"
    write_mp3(wav.with_suffix(".mp3"), norm(np.concatenate([tone[: sec(8)]]), 0.22))
    preview(SCENES / "ep8_01_room.jpg", fr, wav.with_suffix(".mp3"), "ep8_1_wake", tail=3)
    bang_gust()
    cards()
    fr = nandomo()
    dur = (len(fr) - 1) / FPS
    shepard(dur)
    tmp = OUT / "preview" / "tmp2.mp3"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(OUT / "ep8" / "85_shepard_then_silence.mp3"),
                    "-t", f"{dur + 2:.2f}", str(tmp)], check=True)
    preview(SCENES / "ep8_01_room.jpg", fr, tmp, "ep8_5_nandomo", tail=2)


PIECES = {"ep8": ep8}

if __name__ == "__main__":
    for name in sys.argv[1:] or PIECES:
        PIECES[name]()
