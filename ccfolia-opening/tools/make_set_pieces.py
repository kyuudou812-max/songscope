"""各話の見せ場の素材を書き出す（どれをいつ流すかは SET-PIECES.md）。

考え方（README「わかったこと」・PREP.local.md「各話の見せ場」）:
  - 1つの見せ場は、ココフォリアのシーンを1回切り替えるだけで、絵と音が同時に動くように作る
  - 動かなくても、KP が本文を読めば成り立つ（演出は上乗せ）
  - シナリオの文は set-pieces.local.json から読む（git の対象外）

出力（build/ccfolia/fx/）:
  shared/70_blink_open.webp     … まぶたが開く（前景、640×360、1回再生）。第八話の目覚め
  shared/71_blink_reopen.webp   … まばたき（閉じた状態から開く。前景、1回再生）。第四話の「瞬きの間に」
  ep4/41_endless_sheet_loop.webp … シートをかき分けても、奥にまたシート（前景、1280×720、ずっとループ）
  ep4/42_tarp_run_loop.mp3      … シートをかき分けて走る音・息・遠くの大通り（BGM、ループ）
  ep4/43_avenue_loop.mp3        … 人で溢れた大通り（BGM、ループ）。逃げ切った安心
  ep4/44_gusha.mp3              … 背後で何かが落ちた「グシャ」（カットイン）
  ep4/45_tape_voice.mp3         … 上から降ってくる、間延びしたテープのような「あとひとつ」（カットイン、POW 失敗）
  ep8/81_room_tone_loop.mp3     … 家具のない部屋の空気（BGM、ループ）。「妙に静かだ」で KP が止める
  ep8/82_bang_gust.mp3          … 窓が開く「バン」→ 突風とカーテンのはためき（BGM。頭の一撃はシーンの切り替えと同時）
  ep8/83_card_1〜4.webp         … 四択のカード（スクリーンパネル、38×10 マス）
  ep8/84_nandomo.webp           … 「何度も」が画面を埋めて真っ黒になる（前景、1280×720、1回再生）
  ep8/85_shepard_then_silence.mp3 … 上がり続ける音 → 真っ黒になるコマで無音（BGM。前景と同時に始まる）
  ep1/11_footsteps_stop.mp3     … コツ、コツと廊下を近づき、ドアの前で止まる（カットイン）
  ep1/12_door_open_close.mp3    … ガチャ、ぎい、バタン（カットイン）。誰も入ってこない
  ep1/13_scratching_loop.mp3    … ドアの向こうで、何人もが引っ掻き、額を擦り付ける（BGM、ループ）
  ep1/14_handle_rattle.mp3      … ガチャン×3（カットイン）。開く前にずるりと手が落ちて、もう一度
  ep2/21_event_bgm_loop.mp3     … 会場の BGM（ループ）。陽気な音楽の下に、潮騒と歌をごく小さく混ぜてある
  ep2/22_tent_bgm.mp3           … 休憩所の BGM（10分）。遠くの音楽と扇風機 → 2〜5分かけて楽器が抜け、言葉のない歌と潮騒だけになる
  ep2/23_insect_tide_loop.mp3   … 資材置き場・玉虫色の地面の BGM（ループ）。潮騒が羽音のつぶでできている＋すぐそばの歌
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


# ================================================================ 第二話
# 会場の陽気な BGM は、はじめから「声」でできていた。部屋の実際の BGM に、潮騒と歌をごく小さく混ぜておき、
# 「こんな BGM は最初から会場に流れていただろうか」（L835〜）で PL 自身に気づかせる
BPM = 116
BEAT = 60 / BPM
# 旋律（拍, 長さ, 音の高さ MIDI）。明るい五音音階、8小節を2回（後半は少し変える）
_A = [(0, 1, 72), (1, 1, 74), (2, 1, 76), (3, 1, 79), (4, 2, 81), (6, 2, 79), (8, 1, 76), (9, 1, 74), (10, 1, 72),
      (11, 1, 74), (12, 3, 76), (16, 1, 79), (17, 1, 81), (18, 1, 79), (19, 1, 76), (20, 2, 74), (22, 2, 72),
      (24, 1, 74), (25, 1, 76), (26, 1, 74), (27, 1, 72), (28, 4, 69)]
_B = [(0, 1, 72), (1, 1, 74), (2, 1, 76), (3, 1, 79), (4, 2, 81), (6, 2, 84), (8, 1, 81), (9, 1, 79), (10, 1, 76),
      (11, 1, 79), (12, 3, 81), (16, 1, 79), (17, 1, 76), (18, 1, 74), (19, 1, 76), (20, 2, 79), (22, 2, 76),
      (24, 1, 74), (25, 1, 72), (26, 1, 74), (27, 1, 76), (28, 4, 72)]
MELODY = _A + [(b + 32, d, m) for b, d, m in _B]
CHORDS = [60, 55, 57, 53] * 4                                    # I–V–vi–IV（ベース、2小節ずつ）
LOOP_BEATS = 64


def midi(m):
    return 440 * 2 ** ((m - 69) / 12)


def additive(f, dur, partials, decay, attack=0.004, vib=0.0, seed=0):
    """倍音を足して作る音（マリンバや木琴のような明るい音）。高い倍音ほど早く消える"""
    n = sec(dur)
    t = np.arange(n) / SR
    ph = 2 * np.pi * f * (t + vib * np.sin(2 * np.pi * 5.5 * t) / (2 * np.pi * 5.5))
    x = sum(a * np.sin(k * ph) * np.exp(-t * decay * k ** 0.7) for k, a in partials)
    return (x * np.minimum(1, t / attack)).astype(np.float32)


def event_music(beats=LOOP_BEATS, detune=0.0):
    """遠くの会場スピーカーから流れる、陽気な BGM（木琴の旋律・ベース・軽い太鼓）"""
    L = beats * BEAT
    x = np.zeros(sec(L + 2), np.float32)
    for b, d, m in MELODY:
        if b < beats:
            place(x, additive(midi(m + detune), d * BEAT + 0.6, [(1, 1), (2, .35), (3, .5), (4, .12), (6, .08)], 3.2) * 0.5,
                  b * BEAT)
    for i, root in enumerate(CHORDS[: beats // 8 * 2]):
        for k in range(4):                                       # 2拍ごとにベース
            place(x, additive(midi(root - 12 + detune) * (1.5 if k % 2 else 1), 2 * BEAT, [(1, 1), (2, .5), (3, .2)], 2.0) * 0.45,
                  (i * 8 + k * 2) * BEAT)
    for b in range(beats):                                       # 表拍にバスドラム、裏に軽い打ち物
        place(x, thump(110, 0.09, 200 + b, 0.3) * 0.5, b * BEAT)
        place(x, click(4000, 9000, 0.02, 300 + b) * 0.12, (b + 0.5) * BEAT)
        if b % 2 == 1:
            place(x, filt(noise(0.2, 400 + b), 1500, 6000) * env(sec(0.2), 0.001, 0.05) * 0.35, b * BEAT)
    # 拡声器：低音と高音が落ち、少し割れ、建物に一度跳ね返る（120ms。数ミリ秒のこだまは金属的になるので使わない）
    x = np.tanh(filt(x, 250, 5000) * 1.8) / 1.8
    x = place(x.copy(), x * 0.25, 0.12)
    x = reverb(x, 1.2, 0.35, 3500)
    return wrap(x, sec(L))


def wrap(x, n):
    """ループ用：n サンプルを超えた残響を頭に重ねる"""
    y = x[:n].copy()
    tail = x[n:]
    y[: len(tail)] += tail[: n]
    return y


def glottal(f0, seed=0):
    """声の元の音：f0 の動きに沿った、倍音の多いのこぎり波（帯域を制限して耳に痛くしない）"""
    ph = np.cumsum(2 * np.pi * f0 / SR)
    x = np.zeros(len(f0), np.float32)
    for k in range(1, 28):
        x += (np.sin(k * ph) / k * (k * f0 < 5000)).astype(np.float32)
    x += filt(rng_noise(len(f0), seed), 1500, 6000) * 0.05      # 息
    return x


def rng_noise(n, seed):
    return np.random.default_rng(seed).normal(0, 1, n).astype(np.float32)


VOWELS = {"u": (325, 700, 2530), "o": (450, 800, 2830), "a": (730, 1090, 2440), "e": (530, 1840, 2480)}


def formant(x, vowel, shift=1.0):
    f1, f2, f3 = (v * shift for v in VOWELS[vowel])
    return filt(x, f1 * .8, f1 * 1.2) * 1.0 + filt(x, f2 * .85, f2 * 1.15) * 0.6 + filt(x, f3 * .9, f3 * 1.1) * 0.3


def voices(L, instability, seed=0, beats_offset=0.0):
    """会場の旋律をなぞる、言葉のない歌。子供のような高い声と、老人のような低い声が重なり、
    instability（時間 → 0〜1）が大きいほど、音程がうねり・外れ・遅れる（獣が人の声を真似ているように）"""
    n = sec(L)
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    rg = np.random.default_rng(seed)
    for vi, (oct_, shift, vowel, gain) in enumerate([(12, 1.25, "u", 0.6), (0, 1.0, "o", 0.7), (-12, 0.85, "a", 0.55)]):
        # 旋律から、その声の高さの線（f0）を作る：音と音の間は滑らかにつなぐ
        target = np.full(n, np.nan, np.float32)
        loops = int(np.ceil(L / (LOOP_BEATS * BEAT))) + 1
        for lp in range(loops):
            for b, d, m in MELODY:
                s = (lp * LOOP_BEATS + b) * BEAT + beats_offset + vi * 0.03
                a, e = sec(s), sec(s + d * BEAT)
                if a >= n:
                    break
                target[a:min(e, n)] = m + oct_
        idx = np.where(~np.isnan(target))[0]
        target = np.interp(np.arange(n), idx, target[idx]).astype(np.float32)
        glide = sec(0.06)
        target = np.convolve(target, np.ones(glide) / glide, "same")
        ins = instability(t)
        wob = (np.interp(t, np.arange(0, L + 2, 0.7), rg.normal(0, 1, len(np.arange(0, L + 2, 0.7)))) * 1.6 * ins
               + np.sin(2 * np.pi * 5.2 * t + vi) * (0.15 + 0.5 * ins))
        jump = np.interp(t, np.arange(0, L + 9, 9.0), rg.choice([0, 0, 0, 12, -12, 7], len(np.arange(0, L + 9, 9.0)))) * ins ** 2
        f0 = midi(target + wob + jump).astype(np.float32)
        src = glottal(f0, seed + vi)
        amp = (0.6 + 0.4 * np.sin(2 * np.pi * t / (2.5 + vi))) * (1 + ins * 0.6 * np.sin(2 * np.pi * 0.37 * t + vi))
        out += formant(src, vowel, shift) * amp.astype(np.float32) * gain
    return out


def tide(L, seed=0, insect=0.0):
    """潮騒：ゆっくり寄せては返す波。insect（0〜1）が大きいほど、波の音が無数の羽音のつぶ（玉虫が羽を擦らせる音）でできていく"""
    n = sec(L)
    t = np.arange(n) / SR
    rg = np.random.default_rng(seed)
    swell = np.zeros(n, np.float32)
    s = 0.0
    while s < L:                                                 # 1つの波：寄せて（2秒）、崩れて、引く（4〜6秒）
        period = rg.uniform(6, 9)
        a = sec(s)
        k = np.arange(sec(period)) / SR
        w = np.where(k < 2.2, (k / 2.2) ** 2, np.exp(-(k - 2.2) / 1.6))
        e = min(n, a + len(w))
        swell[a:e] += (w[: e - a] * rg.uniform(0.7, 1.0)).astype(np.float32)
        s += period * rg.uniform(0.75, 0.95)
    wash = filt(rng_noise(n, seed + 1), hi=900) * 0.9 + filt(rng_noise(n, seed + 2), 900, 4500) * 0.4 * swell
    x = wash * (0.15 + swell)
    if insect > 0:
        # 羽音のつぶ：2〜6ms の短い明るい音を、波の強さに合わせた密度でばらまく
        grains = np.zeros(n, np.float32)
        dens = 900 * swell / max(swell.max(), 1e-6) + 60
        cnt = int(dens.mean() * L)
        pos = rg.random(cnt) * n
        keep = rg.random(cnt) < np.interp(pos, np.arange(n), dens) / dens.max()
        g = filt(rng_noise(sec(0.006) * 64, seed + 3), 2500, 7500).reshape(64, -1) * np.hanning(sec(0.006))
        for p in pos[keep].astype(int):
            gi = g[rg.integers(64)]
            e = min(n, p + len(gi))
            grains[p:e] += gi[: e - p] * rg.uniform(0.3, 1.0)
        x = x * (1 - 0.6 * insect) + grains * insect * 0.35
    return x


def crowd(L, seed=0):
    """屋外のにぎわい：聞き取れない話し声（第六話のざわめきと同じ作り方を、屋外向けに薄く・明るく）"""
    from make_ep6_audio import babble
    return babble(L, density=4, muffle=2200)


def fan(L, seed=0):
    """首振りの扇風機：モーターの低い唸りと、首を振るたびに近づいては離れる風の音"""
    n = sec(L)
    t = np.arange(n) / SR
    sweep = 0.5 + 0.5 * np.sin(2 * np.pi * t / 9)
    air = filt(rng_noise(n, seed), 200, 2500) * (0.3 + 0.7 * sweep)
    motor = filt(rng_noise(n, seed + 1), 90, 130, order=4) * 2.0
    return air * 0.5 + motor * 0.3


def fit(x, n):
    """長さを n にそろえる（丸めの誤差で1〜2サンプルずれるため）"""
    return np.pad(x, (0, max(0, n - len(x))))[:n].astype(np.float32)


def ep2():
    L = LOOP_BEATS * BEAT                                        # 約33秒
    loops = 4
    LL = L * loops                                               # 約132秒のループ
    music = np.tile(event_music(), loops)
    xf = 3.0
    n = len(music)
    cr = fit(loop_seam(norm(crowd(LL + xf)), xf), n)
    td = fit(loop_seam(norm(tide(LL + xf, 21)), xf), n)
    vo = fit(norm(filt(voices(LL, lambda t: np.zeros_like(t) + 0.05, seed=22), 250, 5000)), n)
    # 会場：音楽が主役。潮騒と歌は、気づかないくらい小さく（音楽の約 -30dB）
    a = norm(music) * 0.8 + cr * 0.35 + td * 0.03 + vo * 0.025
    write_mp3(OUT / "ep2" / "21_event_bgm_loop.mp3", norm(a, 0.6))

    # 休憩所：遠くの音楽と扇風機。数分かけて、楽器が抜け、歌と潮騒だけが残る（10分）
    T = 600
    t = np.arange(sec(T)) / SR
    k = lambda a0, a1: np.clip((t - a0) / (a1 - a0), 0, 1).astype(np.float32)
    far = filt(np.tile(event_music(), int(np.ceil(T / L)))[: sec(T)], 300, 3500)
    # テープが伸びたように、音楽の高さがだんだん揺れる（ゆっくり変わる遅れで読み出す）
    wow = (0.004 + 0.02 * k(120, 260)) * np.sin(2 * np.pi * t / 3.1) + 0.03 * k(150, 280) * t / T
    far = np.interp(np.arange(sec(T)) - wow * SR, np.arange(sec(T)), far).astype(np.float32)
    N = sec(T)
    vo = fit(norm(filt(voices(T, lambda tt: np.clip((tt - 90) / 220, 0, 1) * 0.9 + 0.05, seed=23), 200, 5000)), N)
    td = fit(norm(tide(T, 24)), N)
    cr = fit(norm(crowd(T)), N)
    b = (norm(far) * 0.55 * (1 - k(140, 290))
         + vo * (0.02 + 0.5 * k(80, 300))
         + td * (0.06 + 0.4 * k(100, 320))
         + cr * 0.25 * (1 - 0.8 * k(30, 240))
         + fit(norm(fan(T, 25)), N) * 0.12)
    write_mp3(OUT / "ep2" / "22_tent_bgm.mp3", norm(b, 0.6), q=6)

    # 資材置き場・玉虫色の地面：潮騒は羽音でできている。歌はすぐそばまで来ている（ループ）
    L3 = 90
    td = tide(L3 + xf, 26, insect=1.0)
    vo = fit(voices(L3 + xf, lambda tt: np.zeros_like(tt) + 1.0, seed=27), len(td))
    c = loop_seam(norm(td) * 0.7 + norm(filt(vo, 150, 6000)) * 0.45, xf)
    write_mp3(OUT / "ep2" / "23_insect_tide_loop.mp3", norm(c, 0.65), q=5)


# ================================================================ 第一話
# ドアの向こう（L560〜）：何も見せず、音だけで。会議室の中から、閉じた一枚板のドア越しに聞いている
def mix(*xs):
    """長さの違う音を、頭をそろえて足す"""
    out = np.zeros(max(len(x) for x in xs), np.float32)
    for x in xs:
        out[: len(x)] += x
    return out


def behind_door(x, hi=2200):
    """ドア越しの音：高い音が板で削られ、板の低い鳴りが少し乗る"""
    return filt(x, hi=hi, order=2) * 0.8 + resonate(x, [170, 240], q=8) * 0.6


def footsteps(n_steps=14, rate=1.75, seed=0):
    """廊下の足音（硬い靴底・硬い床）：遠くから規則正しく近づき、ドアの前でぴたりと止まる"""
    L = n_steps / rate + 2.5
    x = np.zeros(sec(L), np.float32)
    rg = np.random.default_rng(seed)
    for i in range(n_steps):
        d = i / (n_steps - 1)                                    # 0=遠い, 1=ドアの前
        # コツ：硬い靴底のかかとが当たる、短く明るい音が主役（低い音を主役にすると地団駄に聞こえる）
        step = mix(click(1200, 6000, 0.007, seed + i), thump(450, 0.02, seed + 50 + i, 0.15) * 0.2)
        step = filt(step, hi=1500 + 4500 * d)
        gain = (0.12 + 0.88 * d ** 1.5) * rg.uniform(0.9, 1.05)
        place(x, step * gain, 0.3 + i / rate + rg.normal(0, 0.008))
    # 廊下の響き：遠いほど響きが多い（近づくほど乾いて聞こえるよう、2本を混ぜる）
    wet = reverb(x, 1.3, 1.0, 4000) - x
    k = np.clip(np.arange(len(x)) / SR / (n_steps / rate), 0, 1)
    return behind_door(x + wet * (0.9 - 0.6 * k), hi=4000)


def latch(seed=0, force=1.0):
    """ドアノブを回す「ガチャ」：金具が外れる硬い音と、バネの戻り"""
    x = click(1800, 8000, 0.004, seed) * 0.6
    x = place(np.pad(x, (0, sec(0.3))), resonate(noise(0.25, seed + 1) * env(sec(0.25), 0.001, 0.03 * force), [1800, 2650, 4100], q=50) * 0.8, 0.002)
    x = place(x, click(2500, 7000, 0.003, seed + 2) * 0.35, 0.07 + 0.05 * force)
    return x


def creak(dur=1.3, seed=0):
    """蝶番がきしむ「ぎい」：引っかかっては滑る小さな衝撃の連なり（速さが揺れる）を、金具と板の鳴りに通す"""
    n = sec(dur)
    t = np.arange(n) / SR
    rate = 45 + 40 * np.sin(np.pi * t / dur) + 12 * np.sin(2 * np.pi * 3.1 * t)
    ph = np.cumsum(rate / SR)
    pulses = (np.diff(np.floor(ph), prepend=0) > 0).astype(np.float32)
    pulses *= np.random.default_rng(seed).uniform(0.5, 1.0, n).astype(np.float32)
    x = resonate(pulses, [620, 1150, 1720, 2400], q=25) + resonate(pulses, [280], q=6) * 0.5
    return norm(x * np.sin(np.pi * t / dur) ** 0.5, 1.0)


def door_open_close(seed=0):
    """ガチャ、ぎい、バタン。——しかし誰も入ってこない"""
    x = np.zeros(sec(4.0), np.float32)
    place(x, latch(seed), 0.2)
    place(x, creak(1.3, seed + 1) * 0.5, 0.55)
    slam = thump(80, 0.16, seed + 2, 0.6) * 1.0
    slam = place(slam, latch(seed + 3, 1.6) * 0.7, 0.0)
    place(x, slam, 2.3)
    return reverb(x, 0.6, 0.25)                                  # 会議室の中の響き（ドアはこちら側で開閉する）


def scratching(L=60, seed=0):
    """ドアの向こう：複数の爪が、上・ドアノブ・床近くを引っ掻く（カリ、カリ）。額を擦り付ける音（ごり、じゃり）。
    引っ掻く場所の高さを、音の明るさで分ける（上ほど明るく小さく、床近くはこもる）"""
    n = sec(L)
    x = np.zeros(n, np.float32)
    rg = np.random.default_rng(seed)
    for who in range(5):                                         # 何人もの人間
        bright = rg.uniform(3500, 7000)
        t = rg.uniform(0, 2)
        while t < L:
            burst = int(rg.integers(2, 6))                       # カリ、カリ、カリ
            for _ in range(burst):
                g = filt(noise(0.05, int(t * 1000) + who), 1500, bright) * env(sec(0.05), 0.003, 0.018)
                g *= (0.5 + 0.5 * np.random.default_rng(int(t * 997)).random(len(g))) ** 2   # ざらつき
                place(x, g * rg.uniform(0.3, 0.8), t)
                t += rg.uniform(0.11, 0.2)
            t += rg.uniform(0.4, 2.5)
    # 額を擦り付ける：ゆっくりした往復、ざらざらした中くらいの高さの音（引っかかっては滑る）
    k = np.arange(n) / SR
    stroke = np.clip(np.sin(2 * np.pi * k / rg.uniform(1.6, 2.4)), 0, 1) ** 2 * smooth_random(L, 0.2, seed + 9)
    grit = filt(noise(L, seed + 10), 250, 1800) * (0.4 + 0.6 * (np.random.default_rng(seed + 11).random(n) < 0.08))
    x += grit.astype(np.float32) * stroke.astype(np.float32) * 0.5
    return behind_door(x)


def handle_rattle(seed=0):
    """ガチャン、ガチャン、ガチャン。ドアノブが捻られては、開く前にずるりと手が落ちて、もう一度"""
    x = np.zeros(sec(6.5), np.float32)
    for i, t0 in enumerate((0.3, 2.2, 4.0)):
        place(x, latch(seed + i * 10, 1.8) * 0.9, t0)
        place(x, thump(120, 0.06, seed + i * 10 + 5, 0.3) * 0.4, t0 + 0.01)               # ドアが枠の中で揺れる
        slide = filt(noise(0.35, seed + i), 300, 2500) * env(sec(0.35), 0.05, 0.12) * 0.25  # ずるり
        place(x, slide, t0 + 0.35)
        place(x, latch(seed + i * 10 + 7, 0.8) * 0.5, t0 + 0.75)                          # 戻るノブ
    return reverb(x, 0.6, 0.25)


def ep1():
    d = OUT / "ep1"
    write_mp3(d / "11_footsteps_stop.mp3", norm(footsteps(seed=110), 0.6))
    write_mp3(d / "12_door_open_close.mp3", norm(door_open_close(120), 0.8))
    xf = 2.0
    write_mp3(d / "13_scratching_loop.mp3", norm(loop_seam(scratching(62, 130), xf), 0.55))
    write_mp3(d / "14_handle_rattle.mp3", norm(handle_rattle(140), 0.8))


# ================================================================ 第四話
# どこまでも続くブルーシート（L1367〜・L1440〜）：めくっても、めくっても、その向こうにまたシート。
# → 急に明るい大通りの雑踏（ほっとさせる）→ 背後で「グシャ」
def sheet_texture():
    """ブルーシートの現場の絵から、奥のシートだけを切り出して画面いっぱいの布にする"""
    im = Image.open(SCENES / "ep4_02_bluesheet.jpg").convert("RGB")
    return im.crop((285, 40, 755, 330)).resize((1280, 720), Image.LANCZOS)


def sheet_loop(period=1.4, size=(1280, 720)):
    """シートを左右にかき分けると、すぐ奥にまた同じシートがある。1周ごとに、奥のシートが手前のシートの位置まで来るのでつながる"""
    W, H = size
    tex = sheet_texture().resize(size, Image.LANCZOS)
    n = int(round(period * FPS))
    big = Image.new("RGB", (W * 3, H * 3))
    for i in range(3):
        for j in range(3):
            tile = tex.transpose(Image.FLIP_LEFT_RIGHT) if i % 2 != 1 else tex
            tile = tile.transpose(Image.FLIP_TOP_BOTTOM) if j % 2 != 1 else tile
            big.paste(tile, (i * W, j * H))
    frames = []
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    for i in range(n):
        p = i / n
        # 奥のシート：小さく暗いところから、手前の大きさ・明るさまで近づいてくる
        # （縮めたときに黒い縁が出ないよう、裏返してつないだ大きな布から切り出す）
        sb = 0.62 + 0.38 * ease_out(p)
        bw, bh = int(big.width * sb), int(big.height * sb)
        back = big.resize((bw, bh), Image.LANCZOS).crop(((bw - W) // 2, (bh - H) // 2, (bw - W) // 2 + W, (bh - H) // 2 + H))
        c = np.asarray(back).astype(np.float32) * (0.45 + 0.55 * p)
        # 手前のシート：真ん中から左右に分かれて押しのけられ、少し大きくなりながら画面の外へ
        k = p ** 1.6
        sf = 1 + 0.35 * k
        front = np.asarray(tex.resize((int(W * sf), int(H * sf)), Image.LANCZOS)).astype(np.float32)
        fy0, fx0 = (front.shape[0] - H) // 2, (front.shape[1] - W) // 2
        front = front[fy0:fy0 + H, fx0:fx0 + W]
        gap = W * 1.25 * k                                       # かき分けた幅（1周の終わりには画面の外まで）
        wave = 18 * np.sin(yy / H * np.pi * 2.3 + 0.7) * (0.3 + k)   # 布の縁は波打つ
        left = xx < W / 2 - gap / 2 + wave
        right = xx > W / 2 + gap / 2 + wave
        # 左右の布：縁に向かって暗くなる（めくれて光が当たらない）
        edge = np.minimum(np.abs(xx - (W / 2 - gap / 2 + wave)), np.abs(xx - (W / 2 + gap / 2 + wave)))
        shade = (1 - 0.45 * min(1, k * 6) * (1 - np.clip(edge / 140, 0, 1)))[..., None]   # 分け始めは影なし（ループの継ぎ目をなくす）
        sx_l = np.clip(xx + gap / 2, 0, W - 1).astype(int)       # 左の布は左へずれる
        sx_r = np.clip(xx - gap / 2, 0, W - 1).astype(int)
        yi = yy.astype(int)
        mask_l, mask_r = left[..., None], right[..., None]
        moved = np.where(mask_l, front[yi, sx_l], np.where(mask_r, front[yi, sx_r], 0))
        c = np.where(mask_l | mask_r, moved * shade * (1 - 0.25 * k), c)
        # 走っている揺れ
        dy = int(6 * np.sin(2 * np.pi * p * 2))
        img = Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)).transform(size, Image.AFFINE, (1, 0, 0, 0, 1, dy))
        frames.append(img.convert("RGBA"))
    save_webp_anim(frames, OUT / "ep4" / "41_endless_sheet_loop.webp", lossless=False, quality=72, loop=0)
    return frames


def tarp_rustle(L=60, period=1.4, seed=0):
    """ビニールシートをかき分ける音：くしゃっとした細かい破裂音の束を、1.4秒ごとに。遠くに大通りのざわめき"""
    n = sec(L)
    x = np.zeros(n, np.float32)
    rg = np.random.default_rng(seed)
    t = 0.0
    while t < L:
        for _ in range(int(rg.integers(25, 45))):                 # ぱりぱり：2〜5ms の明るい破裂音
            g = filt(noise(0.006, int(t * 1e4) + _), 1500, 8000) * env(sec(0.006), 0.0005, 0.002)
            place(x, g * rg.uniform(0.2, 1.0), t + abs(rg.normal(0.1, 0.12)))
        place(x, filt(noise(0.5, int(t * 100)), 300, 3000) * env(sec(0.5), 0.05, 0.15) * 0.25, t)   # ばさっ
        t += period * rg.uniform(0.85, 1.15)
    breath = filt(noise(L, seed + 1), 400, 1800) * (0.5 + 0.5 * np.sin(2 * np.pi * np.arange(n) / SR / 0.9)) ** 3 * 0.12
    from make_ep6_audio import babble
    far = filt(fit(babble(L, density=5, muffle=900), n), hi=700) * 0.6
    return x + breath + far


def avenue(L=60):
    """人で溢れた昼の大通り：近くて明るい雑踏と、車の行き交う音"""
    from make_ep6_audio import babble
    n = sec(L)
    crowd = fit(babble(L, density=10, muffle=3200), n)
    traffic = filt(noise(L, 401), 80, 1200) * (0.4 + 0.6 * smooth_random(L, 0.25, 402))
    steps = np.zeros(n, np.float32)
    rg = np.random.default_rng(403)
    for t0 in rg.uniform(0, L, int(L * 6)):
        place(steps, click(1500, 6000, 0.006, int(t0 * 100)) * rg.uniform(0.05, 0.15), t0)
    return norm(crowd) * 0.7 + norm(traffic) * 0.35 + steps


def gusha(seed=0):
    """背後で何かが落ちた「グシャ」：重く湿った低い衝撃と、潰れる細かい音の束（明るすぎない）"""
    x = np.zeros(sec(2.0), np.float32)
    place(x, thump(60, 0.22, seed, 1.0) * 1.0, 0.05)
    rg = np.random.default_rng(seed)
    for k in range(70):                                           # 潰れる：1〜4kHz の細かい割れ、20ms の間に集中
        g = filt(noise(0.008, seed + k), 700, 3500) * env(sec(0.008), 0.0005, 0.003)
        place(x, g * rg.uniform(0.2, 0.8), 0.05 + abs(rg.normal(0, 0.025)))
    place(x, filt(noise(0.4, seed + 99), 200, 1200) * env(sec(0.4), 0.01, 0.12) * 0.35, 0.07)   # 湿った重さ
    return reverb(x, 0.9, 0.3, 3000)


def tape_voice(text="あとひとつ", seed=0):
    """上から降ってくる、酷く間延びしたテープのような声（POW 失敗）：合成の声を半分の速さに伸ばし、回転のむらで揺らす"""
    import pyopenjtalk
    from scipy.signal import resample_poly
    x, sr = pyopenjtalk.tts(text, half_tone=-2, speed=0.9)
    x = resample_poly(np.asarray(x, np.float32) / 32768.0, SR, sr).astype(np.float32)
    n = len(x) * 2                                                # 2倍に伸ばす（高さも下がる＝伸びたテープ）
    t = np.arange(n) / SR
    pos = np.arange(n) / 2.0 + 0.012 * SR * np.sin(2 * np.pi * 0.7 * t)   # 回転のむら
    y = np.interp(pos, np.arange(len(x)), x).astype(np.float32)
    y = filt(y, 250, 3000) + filt(noise(len(y) / SR, seed), 2000, 6000) * 0.01   # こもり＋テープの擦れ
    y = reverb(y, 1.4, 0.6, 2500)                                 # ビルの上から、壁に響いて降ってくる
    return np.concatenate([silence(0.3), y, silence(1.0)])


def ep4():
    d = OUT / "ep4"
    fr = sheet_loop()
    write_mp3(d / "42_tarp_run_loop.mp3", norm(loop_seam(tarp_rustle(62, seed=420), 2.0), 0.6))
    write_mp3(d / "43_avenue_loop.mp3", norm(loop_seam(avenue(62), 2.0), 0.6))
    write_mp3(d / "44_gusha.mp3", norm(gusha(440), 0.85))
    write_mp3(d / "45_tape_voice.mp3", norm(tape_voice(seed=450), 0.7))
    tmp = OUT / "preview" / "tmp4.mp3"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(d / "42_tarp_run_loop.mp3"), "-t", "6", str(tmp)], check=True)
    preview(None, fr * 4, tmp, "ep4_endless_sheet", tail=0)


PIECES = {"ep1": ep1, "ep2": ep2, "ep4": ep4, "ep8": ep8}

if __name__ == "__main__":
    for name in sys.argv[1:] or PIECES:
        PIECES[name]()
