"""各話の見せ場の素材を書き出す（どれをいつ流すかは SET-PIECES.md）。

考え方（README「わかったこと」・PREP.local.md「各話の見せ場」）:
  - 1つの見せ場は、ココフォリアのシーンを1回切り替えるだけで、絵と音が同時に動くように作る
  - 動かなくても、KP が本文を読めば成り立つ（演出は上乗せ）
  - シナリオの文は set-pieces.local.json から読む（git の対象外）

出力（build/ccfolia/fx/）:
  shared/70_blink_open.webp     … まぶたが開く（前景、640×360、1回再生）。第八話の目覚め
  shared/71_blink_reopen.webp   … まばたき（閉じた状態から開く。前景、1回再生）。第四話の「瞬きの間に」
  ep3/31_edge_figure_1〜6.webp  … 視界の端に立つ人の形（スクリーンパネル。画面の端に置き、1枚ずつ表示）
  ep3/32_flyer.webp             … わら半紙のチラシ（スクリーンパネル、20×28 マス）
  ep4/41_endless_sheet_loop.webp … シートをかき分けても、奥にまたシート（前景、1280×720、ずっとループ）
  ep4/42_tarp_run_loop.mp3      … シートをかき分けて走る音・息・遠くの大通り（BGM、ループ）
  ep4/43_avenue_loop.mp3        … 人で溢れた大通り（BGM、ループ）。逃げ切った安心
  ep4/44_gusha.mp3              … 背後で何かが落ちた「グシャ」（カットイン）
  ep5/51_tadaima_approach.mp3   … ドアの開け閉めが一部屋ずつ近づいてくる（カットイン）。「ただいまー」は KP がチャットで
  ep5/52_tadaima_arrive.mp3     … この部屋のドアが開き、ぎし、沈黙、出ていく（カットイン。押入れに隠れた場合）
  ep5/53_zapping.mp3            … 終わりのテレビのザッピング（カットイン）
  ep6/60_restaurant_ambience_loop.mp3 … ファミレスのざわめき（BGM、ループ。声の高さを持たない雑音で作る）
  ep5/54_obituary.webp          … 新聞の訃報の切り抜き（縦書き。スクリーンパネル）
  ep5/55_kamisama.webp          … 剥がれた記事の下の、震えた文字（スクリーンパネル。目星成功）
  ep5/56_phone_news.webp        … 朝のスマホのニュース（スクリーンパネル）
  ep5/57_window_slap.mp3        … スクラップブックが窓に叩きつけられる「バン！」（カットイン）
  ep6/62_beep_short/long.mp3    … 放送禁止音（カットイン。声は使わず、伏せ字の位置で鳴らす）
  ep9/98_lobby_flicker_loop.webp … ロビーの照明の明滅（前景、640×360、ずっとループ）
  ep9/99_proof_0〜3,reach.webp  … 【暗闇証明】：女の形の輪郭がほどけていく4段階と、近づく形（前景）
  ep9/97_hall_Npc.jpg           … 劇場のホール：空席を遊ぶ人数（1〜3人）にそろえた背景（4人は元の絵のまま）
  ep9/96_knob_held.mp3          … 非常口のノブが、向こうから引き戻される（カットイン）
  ep5/58_dusk_loop.mp3          … 夕暮れの団地（風と遠くの踏切。羽ばたきなし）。玄関・台所・奥の部屋のシーン用
  ep7/74_rain_loop.mp3          … 雨の町（BGM、ループ）
  ep7/75_channel_loop.mp3       … 地下水路の濁流（BGM、ループ）
  ep7/76_vulture_bg.jpg / 76_vulture_eyes.webp … 高架下のハゲタカ（背景）と、目だけ → 見据える → 全体が浮かぶ（前景、1回再生）。
                                  絵が届くまでは _draft（高架下に仮の目）
  ep7/71_oiwai_flood.webp       … 「お祝いですよ」が画面を埋め尽くす（前景、1回再生）
  ep7/72_reward_mojibake.webp   … 文字化けしたままの報酬のカード（スクリーンパネル、38×18 マス）
  shared/79_presence_projector.mp3 … 全話を通す「気配の音」：映写機が一瞬だけ回る、ごく小さな音（カットイン。各話で1回だけ）
  ep5/55b_kamisama_under.webp   … 新聞の切り抜きの裏面（めくると、その下に書かれていた震えた文字）
  ep7/77_phone_news.webp        … 第七話の朝のスマホのニュース（第五話と同じ画面で、今度は自分たちのこと）
  shared/72_blink_close.webp    … まぶたがとろんと重くなり、ストンと閉じて真っ暗のまま（前景、1回再生。第一話の居眠り）
  ep7/73_queue_panel.webp       … PC の置き場の後ろに出す、行列の後ろ姿（スクリーンパネル 128×54 マス）
  ep8/81_room_tone_loop.mp3     … 家具のない部屋の空気（BGM、ループ）。「妙に静かだ」で KP が止める
  ep8/82_bang_gust.mp3          … 窓が開く「バン」→ 突風とカーテンのはためき（BGM。頭の一撃はシーンの切り替えと同時）
  ep8/83_card_1〜4.webp         … 四択のカード（スクリーンパネル、38×10 マス）
  ep8/86_balcony_bg.jpg / 86_balcony_loop.webp … ベランダ（背景）と、手を振る → のけぞる → 沈んで消える女＋白いモザイクのループ（前景）。
                                  絵が届くまでは _draft（家具のない部屋に仮の影）
  ep8/84_nandomo.webp           … 「何度も」が画面を埋めて真っ黒になる（前景、1280×720、1回再生）
  ep8/85_shepard_then_silence.mp3 … 上がり続ける音 → 真っ黒になるコマで無音（BGM。前景と同時に始まる）
  ep1/11_footsteps_stop.mp3     … コツ、コツと廊下を近づき、ドアの前で止まる（カットイン）
  ep1/12_door_open_close.mp3    … ガチャ、ぎい、バタン（カットイン）。誰も入ってこない
  ep1/13_scratching_loop.mp3    … ドアの向こうで、何人もが引っ掻き、額を擦り付ける（BGM、ループ）
  ep1/14_handle_rattle.mp3      … ガチャン×3（カットイン）。開く前にずるりと手が落ちて、もう一度
  ep2/21_event_bgm_loop.mp3     … 会場の BGM（ループ）。陽気な音楽の下に、潮騒をごく小さく混ぜてある
  ep2/22_tent_bgm.mp3           … 休憩所の BGM（10分）。遠くの音楽と扇風機 → 2〜5分かけて楽器が抜け、伸びたテープのように揺れる旋律と潮騒だけになる
  ep2/23_insect_tide_loop.mp3   … 資材置き場・玉虫色の地面の BGM（ループ）。潮騒が羽音のつぶでできている
  ep9/90_full_door_bg.jpg       … 開ききったドアの廊下（背景）。絵が届くまでは _draft（第9話のドアで代用）
  ep9/91_woman_darkness.webp    … 戸口の暗闇に、女の形の「さらに暗い暗闇」が浮かび、OP のタイトルが重なる（前景、1回再生）
  ep9/92_film_loop.webp         … 舞台の古い映画（前景、ループ）。絵が届くまでは _draft
  ep9/93_film_cut.webp          … 振り返りはじめた瞬間に途切れて真っ黒（前景、1回再生）
  ep9/94_projector_loop.mp3     … 映写機の音（BGM、ループ）
  ep9/95_projector_stop_then_silence.mp3 … フィルムが外れて映写機が止まる → 無音（BGM。途切れる前景と同時に始まる）
  reward/epN_rewardK(_cut).webp … 報酬の札（第1〜7話、各3枚。_cut は切り抜かれた裏。スクリーンパネルの裏面に入れる）
  recap/recap_epN.webp          … 前回のあらすじ（スクリーンパネル、38×24 マス。第2話〜最終話の冒頭）
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
from fxlib import (BLACK, QUIET, QUIETEST, ROOT, SR, TEXT, click, env, filt, font, halo, loop_seam, noise, norm, place,  # noqa: E402
                   resonate, reverb, save_webp_anim, sec, silence, smooth_random, thump, vchar, write_mp3)

OUT = ROOT / "build" / "ccfolia" / "fx"
SCENES = ROOT / "build" / "ccfolia" / "scenes"
FPS = json.loads((ROOT / "opening" / "timing.json").read_text(encoding="utf-8"))["fps"]
TXT = json.loads((ROOT / "set-pieces.local.json").read_text(encoding="utf-8"))


_LUT = []


def lut():
    """廊下の絵の「明るさ → 色」の対応（make_npc_portrait.tone_lut）。毎コマ作り直すと遅いので一度だけ作る"""
    if not _LUT:
        from make_npc_portrait import tone_lut
        _LUT.append(tone_lut())
    return _LUT[0]


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


def event_music(beats=LOOP_BEATS, detune=0.0, parts=("melody", "bass", "drums")):
    """遠くの会場スピーカーから流れる、陽気な BGM（木琴の旋律・ベース・軽い太鼓）"""
    L = beats * BEAT
    x = np.zeros(sec(L + 2), np.float32)
    for b, d, m in MELODY if "melody" in parts else []:
        if b < beats:
            place(x, additive(midi(m + detune), d * BEAT + 0.6, [(1, 1), (2, .35), (3, .5), (4, .12), (6, .08)], 3.2) * 0.5,
                  b * BEAT)
    for i, root in enumerate(CHORDS[: beats // 8 * 2] if "bass" in parts else []):
        for k in range(4):                                       # 2拍ごとにベース
            place(x, additive(midi(root - 12 + detune) * (1.5 if k % 2 else 1), 2 * BEAT, [(1, 1), (2, .5), (3, .2)], 2.0) * 0.45,
                  (i * 8 + k * 2) * BEAT)
    for b in range(beats if "drums" in parts else 0):            # 表拍にバスドラム、裏に軽い打ち物
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


def rng_noise(n, seed):
    return np.random.default_rng(seed).normal(0, 1, n).astype(np.float32)


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


def murmur(L, people=24, muffle=1400, seed=0):
    """人のざわめき：声の高さ（音程）を持たない雑音で作る。合成の声は笑えてしまうので使わない（README「わかったこと」）。
    1人分＝話す区切り（1〜3秒話して、0.5〜2秒黙る）と、1秒に4〜6回の音節の強弱を、話し声くらいの帯域の雑音に乗せる。
    何人分も重ねてこもらせると、言葉は聞き取れないが「人がいる」とわかる"""
    n = sec(L)
    out = np.zeros(n, np.float32)
    rg = np.random.default_rng(seed)
    t = np.arange(n) / SR
    for p in range(people):
        talk = np.zeros(n, np.float32)
        s = rg.uniform(0, 2)
        while s < L:
            d = rg.uniform(1.0, 3.0)
            a, b = sec(s), min(n, sec(s + d))
            talk[a:b] = 1
            s += d + rg.uniform(0.5, 2.0)
        w = sec(0.08)                                            # 話し始め・終わりをなめらかに（移動平均。畳み込みだと10分の音で遅すぎる）
        c = np.concatenate([[0], np.cumsum(talk)])
        sm = (c[w:] - c[:-w]) / w
        talk = np.pad(sm, (w // 2, n - len(sm) - w // 2)).astype(np.float32)
        rate = rg.uniform(4, 6)
        syl = (0.5 + 0.5 * np.sin(2 * np.pi * rate * t + rg.uniform(0, 6) + 0.8 * np.sin(2 * np.pi * 0.7 * t))) ** 2
        lo = rg.uniform(250, 450)
        body = filt(noise(L, seed * 100 + p), lo, lo * 5)
        out += body[:n] * talk * syl * rg.uniform(0.4, 1.0)
    return filt(out, hi=muffle)


def crowd(L, seed=0):
    """屋外のにぎわい（声の高さを持たないざわめき）"""
    return murmur(L, people=20, muffle=2200, seed=seed + 7)


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
    # 会場：音楽が主役。潮騒は、気づかないくらい小さく（音楽の約 -30dB）
    a = norm(music) * 0.8 + cr * 0.35 + td * 0.03
    write_mp3(OUT / "ep2" / "21_event_bgm_loop.mp3", norm(a, 0.6))

    # 休憩所：遠くの音楽と扇風機。数分かけて、太鼓とベースが抜け、旋律だけが伸びたテープのように揺れながら残り、
    # 潮騒が大きくなる（10分）。「歌」は KP の描写に任せる（合成の声は使わない）
    T = 600
    N = sec(T)
    t = np.arange(N) / SR
    k = lambda a0, a1: np.clip((t - a0) / (a1 - a0), 0, 1).astype(np.float32)
    reps = int(np.ceil(T / L))
    full = filt(np.tile(event_music(), reps)[:N], 300, 3500)
    mel = filt(np.tile(event_music(parts=("melody",)), reps)[:N], 300, 3500)
    # テープが伸びたように、音楽の高さがだんだん揺れ、遅れていく（ゆっくり変わる遅れで読み出す）
    wow = (0.004 + 0.03 * k(120, 300)) * np.sin(2 * np.pi * t / 3.1) + 0.05 * k(150, 400) * t / T
    rd = lambda x: np.interp(np.arange(N) - wow * SR, np.arange(N), x).astype(np.float32)
    full, mel = rd(full), rd(mel)
    td = fit(norm(tide(T, 24)), N)
    cr = fit(norm(crowd(T)), N)
    b = (norm(full) * 0.55 * (1 - k(140, 290))
         + norm(mel) * 0.45 * k(140, 290) * (1 - 0.6 * k(320, 600))
         + td * (0.06 + 0.45 * k(100, 320))
         + cr * 0.25 * (1 - 0.8 * k(30, 240))
         + fit(norm(fan(T, 25)), N) * 0.12)
    write_mp3(OUT / "ep2" / "22_tent_bgm.mp3", norm(b, 0.6), q=6)

    # 資材置き場・玉虫色の地面：潮騒は羽音でできている（ループ）
    L3 = 90
    c = loop_seam(norm(tide(L3 + xf, 26, insect=1.0)), xf)
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


def pan(x, p):
    """左右の位置（p：-1＝左、0＝正面、1＝右。時間で変える配列でもよい）。等パワーで振り分ける"""
    a = (np.asarray(p, np.float32) + 1) * np.pi / 4
    return (x * np.cos(a)).astype(np.float32), (x * np.sin(a)).astype(np.float32)


def write_stereo(path, l, r, peak=0.8, q=4):
    m = max(np.abs(l).max(), np.abs(r).max(), 1e-6)
    write_mp3(path, l / m * peak, q=q, stereo=r / m * peak)


def ep1():
    d = OUT / "ep1"
    # 音の位置（ラジオドラマの考え方）：足音は右から近づいて、ドアの前（正面）で止まる。引っ掻く音は左右に散らばる
    fs = footsteps(seed=110)
    write_stereo(d / "11_footsteps_stop.mp3", *pan(fs, np.clip(np.linspace(0.85, -0.2, len(fs)), 0, 1)), peak=0.6)
    write_mp3(d / "12_door_open_close.mp3", norm(door_open_close(120), 0.8))
    xf = 2.0
    l = loop_seam(scratching(62, 130), xf)
    r = loop_seam(scratching(62, 131), xf)
    n = min(len(l), len(r))
    write_stereo(d / "13_scratching_loop.mp3", l[:n] * 0.8 + r[:n] * 0.2, r[:n] * 0.8 + l[:n] * 0.2, peak=0.55)
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
            g = filt(noise(0.006, int(t * 1e4) + _), 1200, 5500) * env(sec(0.006), 0.0005, 0.002)
            place(x, g * rg.uniform(0.2, 1.0), t + abs(rg.normal(0.1, 0.12)))
        place(x, filt(noise(0.5, int(t * 100)), 300, 3000) * env(sec(0.5), 0.05, 0.15) * 0.25, t)   # ばさっ
        t += period * rg.uniform(0.85, 1.15)
    breath = filt(noise(L, seed + 1), 400, 1800) * (0.5 + 0.5 * np.sin(2 * np.pi * np.arange(n) / SR / 0.9)) ** 3 * 0.12
    far = filt(fit(murmur(L, people=16, muffle=900, seed=seed + 2), n), hi=700) * 1.2
    return x + breath + far


def avenue(L=60):
    """人で溢れた昼の大通り：近くて明るい雑踏と、車の行き交う音"""
    n = sec(L)
    crowd = fit(murmur(L, people=40, muffle=3000, seed=404), n)
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


def ep4():
    d = OUT / "ep4"
    fr = sheet_loop()
    write_mp3(d / "42_tarp_run_loop.mp3", norm(loop_seam(tarp_rustle(62, seed=420), 2.0), 0.6))
    write_mp3(d / "43_avenue_loop.mp3", norm(loop_seam(avenue(62), 2.0), 0.6))
    write_mp3(d / "44_gusha.mp3", norm(gusha(440), 0.85))
    tmp = OUT / "preview" / "tmp4.mp3"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(d / "42_tarp_run_loop.mp3"), "-t", "6", str(tmp)], check=True)
    preview(None, fr * 4, tmp, "ep4_endless_sheet", tail=0)


# ================================================================ 第三話
# 立ち去ろうとすると、視界の端に人が増えていく（L1093〜）。目の端に見えるものがいちばん気味が悪い（周辺視野）。
# 画面の端（フィールドの外、チャット欄のそば）にスクリーンパネルで置き、離れようとするたびに KP が1枚ずつ表示する
def edge_figures(count=6):
    """人影の立ち絵を強くぼかし、黒い人の形だけにする（顔も服もわからない。誰か特定の人物に見せない）"""
    from PIL import ImageFilter
    src = Image.open(ROOT / "build" / "ccfolia" / "npc" / "npc_figure.webp").convert("RGBA")
    rg = np.random.default_rng(31)
    out = []
    for k in range(count):
        a = src.getchannel("A")
        sx = rg.uniform(0.8, 1.15)                                # 体格を変える
        a = a.resize((int(a.width * sx), a.height), Image.LANCZOS)
        if k % 2:
            a = a.transpose(Image.FLIP_LEFT_RIGHT)
        a = a.filter(ImageFilter.GaussianBlur(rg.uniform(9, 16)))  # 目の端なので、輪郭は合わない
        a = a.point(lambda v, o=rg.uniform(0.55, 0.8): int(min(255, v * 1.3) * o))
        pad = 40
        im = Image.new("RGBA", (a.width + pad * 2, a.height + pad * 2), (10, 8, 8, 0))
        layer = Image.new("RGBA", a.size, (10, 8, 8, 255))
        layer.putalpha(a)
        im.alpha_composite(layer, (pad, pad))
        im = im.resize((im.width * 600 // im.height, 600), Image.LANCZOS)
        im.save(OUT / "ep3" / f"31_edge_figure_{k + 1}.webp", lossless=True)
        out.append(im)
    return out


def paper(w, h, seed=0, lum=205):
    """わら半紙：少し灰色がかった明るい紙に、細かい繊維とむら。廊下の絵と同じ赤茶の色味をかける"""
    from PIL import ImageFilter
    from make_npc_portrait import tone_lut
    rg = np.random.default_rng(seed)
    base = np.full((h, w), lum, np.float32)
    base += np.asarray(Image.fromarray((rg.random((h // 8, w // 8)) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC),
                       np.float32) / 255 * 18 - 9                 # 大きなむら
    fib = rg.normal(0, 1, (h, w)).astype(np.float32)
    fib = np.asarray(Image.fromarray(((fib - fib.min()) / np.ptp(fib) * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(0.6)), np.float32) / 255 * 22 - 11
    base += fib
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    base *= 1 - 0.18 * (((xx - w / 2) / w) ** 2 + ((yy - h / 2) / h) ** 2) * 2   # 端ほど少し暗く（古び）
    return base


def tone(lum):
    from make_npc_portrait import tone_lut
    l = np.clip(lum, 0, 255)
    return np.clip(l[..., None] * tone_lut()[l.astype(int)], 0, 255).astype(np.uint8)


def flyer():
    """わら半紙のような紙に、少し滲んだインクで大きく印刷された問題（L1110〜）"""
    from PIL import ImageFilter
    W, H = 640, 896
    lum = paper(W, H, 32)
    ink = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(ink)
    q = TXT["ep3_flyer"]["q"]
    head, body = q.split("：", 1)
    f1, f2, f3 = font(44), font(42), font(27)
    d.text((64, 200), head + "：", font=f1, fill=255)
    cut = body.index("って") + 2 if "って" in body else len(body) // 2   # 「〜って」で改行
    for i, s in enumerate([body[:cut], body[cut:]]):
        w = sum(f2.getlength(c) for c in s) + 42 * 0.06 * (len(s) - 1)
        assert w < W - 80, s
        x = (W - w) / 2
        for c in s:
            d.text((x, 300 + i * 80), c, font=f2, fill=255)
            x += f2.getlength(c) + 42 * 0.06
    hint = TXT["ep3_flyer"]["hint"]
    w = sum(f3.getlength(c) for c in hint)
    d.text(((W - w) / 2, 640), hint, font=f3, fill=255)
    # 滲み：ぼかしてから、紙の繊維に沿ってむらのある濃さにする。版が少しずれて二重になる
    a = np.asarray(ink.filter(ImageFilter.GaussianBlur(1.3)), np.float32) / 255
    a = np.clip(a * 1.6, 0, 1) * (0.75 + 0.25 * np.random.default_rng(33).random((H, W)))
    ghost = np.roll(np.roll(a, 2, 1), 1, 0) * 0.25
    a = np.maximum(a, ghost)
    lum = lum * (1 - a * 0.85)
    img = Image.fromarray(tone(lum)).convert("RGBA")
    img.save(OUT / "ep3" / "32_flyer.webp", lossless=True)
    return img


def ep3():
    (OUT / "ep3").mkdir(parents=True, exist_ok=True)
    edge_figures()
    flyer()


# ================================================================ 第五話
# 「ただいまー」が一部屋ずつ近づいてくる（L1915〜）。声は合成すると笑えてしまうので入れない。
# 音はドアの開け閉めだけにし、「ただいまー」は KP がチャットで、ドアの音の合間に送る（時刻は DIRECTION.local.md）
def steel_door(seed=0, close=True):
    """団地の鉄の玄関ドア：ガチャ（ノブ）と、バタン（重い鉄板が枠に当たる鈍い響き）"""
    x = np.zeros(sec(1.2), np.float32)
    place(x, latch(seed), 0.0)
    if close:
        slam = mix(thump(75, 0.14, seed + 1, 0.8), resonate(noise(0.8, seed + 2) * env(sec(0.8), 0.001, 0.12), [190, 430, 960], q=18) * 0.7)
        place(x, slam, 0.55)
    return x


def at_distance(x, k):
    """k 部屋むこう（0 ならこの部屋のドアのすぐ外）。遠いほど小さく、こもり、外廊下に響く"""
    hi = [3800, 2400, 1500, 1000, 700][k]
    g = [1.0, 0.55, 0.32, 0.18, 0.1][k]
    wet = [0.15, 0.3, 0.45, 0.6, 0.7][k]
    return reverb(filt(x, hi=hi), 0.9, wet, 2500) * g


def tadaima_approach():
    """ガチャ、バタン。ガチャ、…（4部屋むこうから、隣の部屋まで）。声が入る「間」は無音で空けてある"""
    x = np.zeros(sec(24), np.float32)
    t = 0.5
    for k in (4, 3, 2, 1):
        t += 2.34                                                        # 「ただいまー」の間（KP がチャットで送る）
        if k > 1:
            place(x, at_distance(steel_door(500 + k), k), t)                 # その部屋を出る
            t += 1.6
            place(x, at_distance(steel_door(510 + k, close=False), k - 1), t)   # 次の部屋を開ける
            t += 0.7
    return x[: sec(t + 1.0)]


def tadaima_arrive():
    """（押入れに隠れた場合）この部屋のドアが開き、（KP が「ただいまー」）、ぎし、と床を踏む音、数秒の沈黙、そして出ていく"""
    x = np.zeros(sec(11), np.float32)
    place(x, reverb(filt(steel_door(520, close=False), hi=3000), 0.5, 0.2) * 0.8, 0.3)
    place(x, filt(creak(0.5, 521), hi=2500) * 0.35, 2.4)              # ぎし
    t = 2.4 + 0.5 + 3.5                                                # 沈黙
    place(x, reverb(filt(steel_door(522), hi=2500), 0.5, 0.2) * 0.6, t)
    return x


def zapping(seed=0):
    """第五話の終わり：テレビのザッピングの音。砂嵐の切れ目に、番組の断片（明るい和音・笑い声のような拍手のざわめき・ジングル）。
    人の声は入れない"""
    x = np.zeros(sec(5.0), np.float32)
    t = 0.2
    bits = [
        additive(midi(72), 0.5, [(1, 1), (2, .4), (3, .3)], 4) + additive(midi(76), 0.5, [(1, 1), (2, .4)], 4),   # 明るい和音
        filt(noise(0.6, seed + 1), 800, 5000) * (0.5 + 0.5 * np.sin(2 * np.pi * 13 * np.arange(sec(0.6)) / SR)) ** 2,  # 拍手のざわめき
        np.concatenate([additive(midi(m), 0.13, [(1, 1), (2, .3)], 12) for m in (84, 88, 91)]),                  # ジングル
        filt(noise(0.5, seed + 2), 100, 900) * 0.8,                                                            # こもった低い音（ドラマの効果音）
    ]
    for i, v in enumerate(bits):
        place(x, mix(filt(noise(0.12, seed + i), 300, 6000) * 0.25, click(800, 4000, 0.003, seed + 10 + i) * 0.6), t)
        v = np.tanh(filt(v.astype(np.float32), 350, 4000) * 2) / 2      # テレビの小さなスピーカー
        place(x, norm(v, 0.6), t + 0.12)
        t += 0.12 + len(v) / SR + 0.05
    place(x, filt(noise(0.25, seed + 20), 300, 6000) * 0.25, t)
    return reverb(x[: sec(t + 0.6)], 0.5, 0.2)


def ep5():
    d = OUT / "ep5"
    ta = tadaima_approach()                                          # 左の遠くの部屋から、だんだん正面へ
    write_stereo(d / "51_tadaima_approach.mp3", *pan(ta, np.linspace(-0.85, -0.15, len(ta))), peak=0.8)
    write_mp3(d / "52_tadaima_arrive.mp3", norm(tadaima_arrive(), 0.75))
    write_mp3(d / "53_zapping.mp3", norm(zapping(530), 0.7))


# ================================================================ 第七話
def oiwai_flood():
    """「お祝いですよ」が四方から重なり、画面を埋め尽くす（DEX 失敗、L2580〜）。最後のコマで止まる。
    1コマで増える文字は、画面の1か所のまわりにまとめる（毎コマ画面全体が変わると、1回再生の素材が 20MB を超えるため）"""
    W, H = 1280, 720
    phrase = "「" + TXT["ep7_oiwai"] + "」"
    rg = np.random.default_rng(71)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    frames, placed, acc, t = [], 0, 0.0, 0
    total = 420
    while placed < total:
        rate = 0.12 * np.exp(t / 40)
        acc += rate * 2
        cx, cy = rg.uniform(0, W - 200), rg.uniform(0, H - 40)
        spread = 60 + 160 * min(1, placed / total)
        while acc >= 1 and placed < total:
            size = int(rg.uniform(18, 36))
            f = font(size)
            x = np.clip(cx + rg.normal(0, spread), -60, W - 120)
            y = np.clip(cy + rg.normal(0, spread * 0.5), -10, H - 30)
            d.text((x, y), phrase, font=f, fill=TEXT + (int(rg.uniform(120, 255)),))
            placed += 1
            acc -= 1
        dim = Image.new("RGBA", (W, H), BLACK + (int(140 * min(1, (t // 6 + 1) / 5)),))   # 背景を5段で沈める
        frame = Image.alpha_composite(dim, halo(layer, 5, 6, 1.2))
        frames += [frame, frame]                                 # 1秒に15回だけ変える（同じコマが続くと容量をほとんど食わない）
        t += 2
    frames += [frames[-1]] * int(0.5 * FPS)
    save_webp_anim(frames, OUT / "ep7" / "71_oiwai_flood.webp", lossless=False, quality=80)   # 可逆だと 6MB。暗い地の文字なので非可逆でも崩れにくい
    return frames


def reward_card():
    """第七話の報酬：《どんな恩恵が欲しい？》が文字化けしたまま出る（辞書カードと同じ文字・大きさ）"""
    W, H = 760, 360
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f1, f2 = font(30), font(28)
    g1 = font(30, gothic=True)
    title = TXT["ep7_reward_title"]
    # しっぽり明朝にない半角カナなどは、タイトルの書体（Zen Kaku Gothic）で補う。書体が混ざるのも本物の文字化けらしい
    notdef = bytes(f1.getmask("\U000F0000"))
    fonts = [g1 if bytes(f1.getmask(c)) == notdef else f1 for c in title]
    w = sum(f.getlength(c) for f, c in zip(fonts, title))
    x = (W - w) / 2
    for f, c in zip(fonts, title):
        d.text((x, 110), c, font=f, fill=TEXT + (255,))
        x += f.getlength(c)
    ch = "　　".join(TXT["ep7_reward_choices"])
    w = f2.getlength(ch)
    d.text(((W - w) / 2, 200), ch, font=f2, fill=TEXT + (255,))
    im = halo(im)
    im.save(OUT / "ep7" / "72_reward_mojibake.webp", lossless=True)
    return im


def ep7():
    (OUT / "ep7").mkdir(parents=True, exist_ok=True)
    fr = oiwai_flood()
    reward_card()
    tmp = OUT / "preview" / "silence.mp3"
    write_mp3(tmp, silence(len(fr) / FPS + 1))
    preview(SCENES / "ep7_04_junction.jpg", fr, tmp, "ep7_oiwai", tail=1)


# ================================================================ 最終話
# 暗闇の形をした女（L3100〜）：9話かけて開いてきた OP の廊下のドアが開ききり、戸口の暗闇の中で、
# 女の形をしたところだけが、まわりの暗闇よりさらに暗い。そこへ OP と同じタイトルが重なる（題の回収）
FULL_DOOR = ROOT / "assets" / "door" / "stage5_full.png"         # ChatGPT の「開ききったドア」（届いたらここに置く）


def doorway_mask(img):
    """戸口の中の真っ暗なところ（ドアのまわりで、いちばん大きくつながった暗い部分）"""
    from scipy.ndimage import binary_closing, label
    lay = json.loads((ROOT / "opening" / "layout.json").read_text(encoding="utf-8"))["door"]
    a = np.asarray(img.convert("L")).astype(np.float32)
    m = np.zeros(a.shape, bool)
    box = (slice(lay["y0"], lay["y1"]), slice(lay["x0"] - 40, lay["x1"] + 10))
    m[box] = a[box] < 5                                         # 戸口の中はほぼ真っ黒（扉の板は 10〜20 くらいなので入らない）
    m = binary_closing(m, iterations=2)
    lab, n = label(m)
    if n == 0:
        raise SystemExit("戸口の暗いところが見つからない")
    sizes = np.bincount(lab.ravel())[1:]
    return lab == (np.argmax(sizes) + 1)


def woman_in_darkness():
    """戸口の暗闇が、ゆっくりわずかに明るい「濁った暗がり」に変わっていき、女の形のところだけが真っ黒のまま残る。
    最後に OP のタイトルが、同じ書体・同じ位置の決め方（戸口の真上）で浮かぶ。前景（1回再生）"""
    sys.path.insert(0, str(ROOT / "tools"))
    from export_ccfolia import door
    from PIL import ImageFilter
    draft = not FULL_DOOR.exists()
    base = Image.open(ROOT / "opening" / "bg.png").convert("RGB")
    bg = door(base, 9) if draft else door(base, 9, FULL_DOOR)    # 絵が届くまでは、第9話のドア（4段階目）で試す
    m = doorway_mask(bg)
    ys, xs = np.where(m)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    # 女の形：立ち絵の輪郭だけ。戸口の高さの 9 割、足もとは戸口の下端
    w_src = Image.open(ROOT / "build" / "ccfolia" / "npc" / "npc_woman.webp").getchannel("A")
    h = int((y1 - y0) * 0.9)
    w = int(w_src.width * h / w_src.height)
    shape = Image.new("L", bg.size, 0)
    shape.paste(w_src.resize((w, h), Image.LANCZOS), (int((x0 + x1) / 2 - w / 2), int(y1 - h - 1)))
    shape = np.asarray(shape.filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255 * m
    # 濁った暗がり：ほんの少しだけ明るい赤茶。縦に流れるむらがあり、ゆっくり揺れる
    H, W = m.shape
    rg = np.random.default_rng(91)
    streak = np.asarray(Image.fromarray((rg.random((H // 24 + 1, W // 3 + 1)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC),
                        np.float32) / 255
    title = Image.open(ROOT / "build" / "ep9_title_still" / "f0000.png").convert("RGBA")
    tb = title.getbbox()
    title = title.crop(tb)
    tx = int((x0 + x1) / 2 - (tb[2] - tb[0]) / 2) - (tb[0] - int((x0 + x1) / 2 - (tb[2] - tb[0]) / 2)) * 0  # 戸口の真上にそろえる
    frames = []
    T = 9.0
    for i in range(int(T * FPS)):
        tt = i / FPS
        k = smoothstep(1.0, 5.5, tt)                              # 暗がりが浮かび上がる
        lum = (30 + 16 * streak + 5 * np.sin(2 * np.pi * (tt / 3.0) + streak * 6)) * k
        rgb = np.clip(lum[..., None] * lut()[np.clip(lum, 0, 255).astype(int)], 0, 255)
        alpha = (m * (1 - shape) * k * 255).astype(np.uint8)
        im = np.zeros((H, W, 4), np.uint8)
        im[..., :3] = (rgb * m[..., None]).astype(np.uint8)       # 透明なところの色は 0 に（毎コマ変わる色が残ると 30MB になる）
        im[..., 3] = alpha
        frame = Image.fromarray(im, "RGBA")
        ta = smoothstep(6.0, 7.5, tt)
        if ta > 0:
            t2 = title.copy()
            t2.putalpha(t2.getchannel("A").point(lambda v, a=ta: int(v * a)))
            frame.alpha_composite(t2, (tx, tb[1]))
        frames.append(frame)
    name = "91_woman_darkness" + ("_draft" if draft else "")
    save_webp_anim(frames, OUT / "ep9" / f"{name}.webp")
    bg_path = OUT / "ep9" / f"90_full_door_bg{'_draft' if draft else ''}.jpg"
    bg.save(bg_path, quality=88)
    return frames, bg_path


# 古い映画（L3030〜）：傷・揺れ・明滅のある古いフィルム。女の後ろ姿。振り返りはじめた瞬間に途切れる
FILM = (ROOT / "assets" / "ep9_film_1.png", ROOT / "assets" / "ep9_film_2.png")   # ChatGPT の2枚（届いたらここに置く）


def film_frame(src, i, rg, size=(960, 720)):
    """1コマ分の古いフィルム：上下左右の揺れ・明るさのちらつき・縦の傷・塵・粒子・周辺の暗さ"""
    from PIL import ImageFilter
    W, H = size
    dx, dy = rg.normal(0, 1.2), rg.normal(0, 2.0)                   # フィルムの送りの揺れ
    im = src.transform(size, Image.AFFINE, (1, 0, dx, 0, 1, dy), Image.BILINEAR)
    lum = np.asarray(im.convert("L"), np.float32)
    lum = lum * (0.92 + 0.1 * rg.random())                         # 明るさのちらつき
    lum += rg.normal(0, 9, (H, W))                                 # 粒子
    for _ in range(rg.integers(0, 3)):                             # 縦の傷（明るい細い線）
        x = rg.integers(0, W)
        lum[:, x:x + 1] += rg.uniform(30, 70)
    for _ in range(rg.integers(2, 7)):                             # 塵（黒い点やけば）
        x, y, r = rg.integers(0, W), rg.integers(0, H), rg.integers(1, 4)
        lum[max(0, y - r):y + r, max(0, x - r):x + r] *= 0.2
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    lum *= np.clip(1 - 0.7 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 2.2, 0.2, 1)
    lum = np.clip(lum * 0.85, 0, 255)
    rgb = np.clip(lum[..., None] * lut()[lum.astype(int)], 0, 255).astype(np.uint8)
    out = Image.new("RGBA", (1280, 720), BLACK + (255,))           # 4:3 の古い映画。左右は黒
    out.paste(Image.fromarray(rgb).filter(ImageFilter.GaussianBlur(0.6)), ((1280 - W) // 2, 0))
    return out


def old_film():
    """上映中（ループ）と、途切れる（1回再生：1枚目 → 振り返りはじめの2枚目に変わって 5 コマで真っ黒）の2つ"""
    draft = not FILM[0].exists()
    if draft:                                                       # 絵が届くまでは、第五話の玄関で試す
        a = b = Image.open(SCENES / "ep5_02_entrance.jpg").convert("RGB")
    else:
        a, b = (Image.open(p).convert("RGB") for p in FILM)
    fit_ = lambda im: im.resize((int(im.width * 720 / im.height), 720), Image.LANCZOS).crop(
        ((int(im.width * 720 / im.height) - 960) // 2, 0, (int(im.width * 720 / im.height) - 960) // 2 + 960, 720))
    a, b = fit_(a), fit_(b)
    rg = np.random.default_rng(93)
    loop = [film_frame(a, i, rg) for i in range(int(2.0 * FPS))]   # 2秒のループ（ばらつきなので、つなぎ目は見えない）
    sfx = "_draft" if draft else ""
    save_webp_anim(loop, OUT / "ep9" / f"92_film_loop{sfx}.webp", lossless=False, quality=78, loop=0)
    cut = [film_frame(a, i, rg) for i in range(int(1.0 * FPS))] + [film_frame(b, i, rg) for i in range(5)]
    cut.append(Image.new("RGBA", (1280, 720), BLACK + (255,)))
    save_webp_anim(cut, OUT / "ep9" / f"93_film_cut{sfx}.webp", lossless=False, quality=78)
    return loop, cut


def projector(L=60, seed=0):
    """映写機の回る音：送りの規則正しいカタカタ（1秒24回）と、モーターの唸り、フィルムのぱちぱち"""
    n = sec(L)
    x = np.zeros(n, np.float32)
    for k in range(int(L * 24)):
        place(x, click(1500, 5000, 0.004, seed + k % 50) * 0.25, k / 24)
    motor = filt(noise(L, seed + 1), 90, 300, order=4) * 0.6
    crackle = np.zeros(n, np.float32)
    rg = np.random.default_rng(seed + 2)
    for t0 in rg.uniform(0, L, int(L * 8)):
        place(crackle, click(600, 4000, 0.002, int(t0 * 1000)) * rg.uniform(0.1, 0.5), t0)
    return reverb(x + motor + crackle, 1.6, 0.4, 3000)             # 劇場の大きな響き


def projector_stop(seed=0):
    """途切れる：フィルムが外れてばたばたと空回りし、映写機が止まる。そのあとは無音（10分）"""
    x = np.zeros(sec(3.0), np.float32)
    for k in range(30):                                            # フィルムの端が回転に当たって、ばたばた（だんだん遅く）
        place(x, click(400, 3000, 0.01, seed + k) * 0.6 * (1 - k / 30), 0.03 + k * 0.035 * (1 + k / 20))
    motor = filt(noise(2.5, seed + 1), 90, 300, order=4) * np.linspace(0.6, 0, sec(2.5)) ** 2
    place(x, motor, 0)
    return np.concatenate([reverb(x, 1.6, 0.4, 3000), silence(600)])


def ep9():
    (OUT / "ep9").mkdir(parents=True, exist_ok=True)
    fr, bg = woman_in_darkness()
    tmp = OUT / "preview" / "silence.mp3"
    write_mp3(tmp, silence(10))
    preview(bg, fr, tmp, "ep9_woman_darkness", tail=1)
    loop, cut = old_film()
    write_mp3(OUT / "ep9" / "94_projector_loop.mp3", norm(loop_seam(projector(62, 940), 2.0), 0.5))
    write_mp3(OUT / "ep9" / "95_projector_stop_then_silence.mp3", norm(projector_stop(950), 0.6), q=6)
    t2 = OUT / "preview" / "tmp9.mp3"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(OUT / "ep9" / "94_projector_loop.mp3"), "-t", "4",
                    "-i", str(OUT / "ep9" / "95_projector_stop_then_silence.mp3"), "-filter_complex",
                    "[0:a]atrim=0:4[a];[1:a]atrim=0:4[b];[a][b]concat=n=2:v=0:a=1", str(t2)], check=True)
    preview(None, loop * 2 + cut, t2, "ep9_old_film", tail=2)



# ================================================================ 前回のあらすじ
def recap():
    """各話の冒頭に出す「前回のあらすじ」のカード（辞書カードと同じ文字・色。38×24 マス）。文は recaps.local.json"""
    data = json.loads((ROOT / "recaps.local.json").read_text(encoding="utf-8"))
    W, H = 760, 480
    for ep, lines in data.items():
        if not ep.isdigit():
            continue
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        head, body = font(20), font(24)
        d.text((50, 52), "前回のあらすじ", font=head, fill=QUIET + (255,))
        y = 110
        for s in lines:
            assert body.getlength(s) < W - 100, s
            d.text((50, y), s, font=body, fill=TEXT + (255,))
            y += 52
        assert y < H - 20, ep
        halo(im).save(OUT / "recap" / f"recap_ep{ep}.webp", lossless=True)
    print(f"fx/recap/ に {sum(k.isdigit() for k in data)} 枚")


# ================================================================ 第六話
def ep6():
    """昼のファミレスの空気：声の高さを持たないざわめきと、食器の音。第六話の声（パッチワーク）は、チャットだけで見せる"""
    L = 62
    n = sec(L)
    mur = murmur(L, people=36, muffle=1600, seed=601)
    dishes = np.zeros(n, np.float32)
    rg = np.random.default_rng(602)
    for t0 in rg.uniform(0, L, int(L * 1.2)):                       # 食器が触れ合う：短い明るい鳴り
        g = resonate(noise(0.15, int(t0 * 100)) * env(sec(0.15), 0.0005, 0.03), [2600, 3900, 5200], q=40)
        place(dishes, g * rg.uniform(0.05, 0.2), t0)
    hum = filt(noise(L, 603), 60, 160, order=4) * 0.5                 # 空調と厨房の低い音
    x = norm(fit(mur, n)) * 0.7 + dishes + norm(hum) * 0.12
    write_mp3(OUT / "ep6" / "60_restaurant_ambience_loop.mp3", norm(reverb(loop_seam(x, 2.0), 0.8, 0.3), 0.5))



# ================================================================ 報酬の儀式（全話）
# 各話の終わりの報酬（L233〜）を、毎回同じ形で出す：3枚のカード → PL が選ぶ → 選ばれなかったカードは、
# ハサミで切り抜かれて中身がなくなる（第五話の、顔を切り抜かれたポスターと同じ切り口）→「選ばなかったものはいらないね」。
# カードは古い紙の札。表＝選択肢、裏＝切り抜かれた札。ココフォリアのスクリーンパネルの「裏面」に切り抜き版を入れておけば、
# KP は札を裏返すだけで切り抜ける。第六・七話は、見出しが文字化けしていく（本文のとおり）
def draw_text(d, xy, s, f, fill, fallback=None, spacing=0.0):
    """1字ずつ組む。しっぽり明朝にない字（半角カナなど）は、タイトルの書体で補う。幅を返す"""
    fallback = fallback or font(f.size, gothic=True)
    notdef = bytes(f.getmask("\U000F0000"))
    x, y = xy
    for c in s:
        ff = fallback if bytes(f.getmask(c)) == notdef else f
        if d is not None:
            d.text((x, y), c, font=ff, fill=fill)
        x += ff.getlength(c) + f.size * spacing
    return x - xy[0] - (f.size * spacing if s else 0)


def card_paper(w, h, seed):
    """暗く古びた紙の札（廊下の赤茶）。縁は少し不揃いで、下に柔らかい影"""
    from PIL import ImageFilter
    pad = 28
    rg0 = np.random.default_rng(seed + 7)
    fine = np.asarray(Image.fromarray((rg0.random((h, w)) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)),
                      np.float32) / 255
    soft = np.asarray(Image.fromarray((rg0.random((h // 40 + 2, w // 40 + 2)) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC),
                      np.float32) / 255
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    edge = np.minimum(np.minimum(xx, w - xx), np.minimum(yy, h - yy))
    lum = 44 + 8 * (fine - 0.5) + 5 * (soft - 0.5) - 10 * np.exp(-edge / 18)   # 細かい繊維・ゆるいむら・縁の汚れ
    rgb = tone(lum)
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    rg = np.random.default_rng(seed)
    pts = [(rg.uniform(0, 3), rg.uniform(0, 3)), (w - rg.uniform(0, 3), rg.uniform(0, 3)),
           (w - rg.uniform(0, 3), h - rg.uniform(0, 3)), (rg.uniform(0, 3), h - rg.uniform(0, 3))]
    md.polygon(pts, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(0.7))
    card = Image.fromarray(rgb).convert("RGBA")
    card.putalpha(mask)
    out = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, BLACK + (0,))
    sm = Image.new("L", out.size, 0)
    sm.paste(mask.point(lambda v: int(v * 0.75)), (pad + 4, pad + 8))
    sh.putalpha(sm.filter(ImageFilter.GaussianBlur(10)))
    out.alpha_composite(sh)
    out.alpha_composite(card, (pad, pad))
    return out, pad


def scissor_hole(img, box, seed):
    """box のまわりを、ハサミで何度か切ったように不揃いな直線でくり抜く（穴は透明）。切り口は紙の地が白っぽく見える"""
    from PIL import ImageFilter
    x0, y0, x1, y1 = box
    rg = np.random.default_rng(seed)
    pts = []
    for (ax, ay), (bx, by) in zip([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], [(x1, y0), (x1, y1), (x0, y1), (x0, y0)]):
        for k in range(int(rg.integers(2, 4))):                 # 1辺を2〜3回のハサミで切る
            f = k / 3 + rg.uniform(0, 0.1)
            pts.append((ax + (bx - ax) * f + rg.normal(0, 5), ay + (by - ay) * f + rg.normal(0, 5)))
    hole = Image.new("L", img.size, 0)
    ImageDraw.Draw(hole).polygon(pts, fill=255)
    edge = Image.new("L", img.size, 0)
    ImageDraw.Draw(edge).line(pts + [pts[0]], fill=255, width=3)
    edge = edge.filter(ImageFilter.GaussianBlur(0.8))
    out = img.copy()
    lit = Image.new("RGBA", img.size, (150, 128, 112, 0))           # 切り口：紙の繊維が明るく見える
    lit.putalpha(Image.fromarray((np.asarray(edge, np.float32) * (np.asarray(img.getchannel("A")) > 0) * 0.7).astype(np.uint8)))
    out.alpha_composite(lit)
    a = np.asarray(out.getchannel("A")).astype(np.float32) * (1 - np.asarray(hole, np.float32) / 255)
    out.putalpha(Image.fromarray(a.astype(np.uint8)))
    return out


def reward_card(title, choice, seed, size=(720, 380)):
    """報酬の札：上に小さく見出し、真ん中に選択肢。表と、切り抜かれた裏の2枚を返す"""
    w, h = size
    img, pad = card_paper(w, h, seed)
    d = ImageDraw.Draw(img)
    if title:
        f1 = font(20)
        tw = draw_text(None, (0, 0), title, f1, None, spacing=0.12)
        draw_text(d, (pad + (w - tw) / 2, pad + 34), title, f1, QUIET + (255,), spacing=0.12)
    f2 = font(34 if len(choice) < 14 else 30)
    cw = draw_text(None, (0, 0), choice, f2, None, spacing=0.08)
    assert cw < w - 60, choice
    cy = pad + (h - f2.size) / 2 + (14 if title else 0)
    draw_text(d, (pad + (w - cw) / 2, cy), choice, f2, TEXT + (255,), spacing=0.08)
    m = 26
    cut = scissor_hole(img, (pad + (w - cw) / 2 - m, cy - m, pad + (w + cw) / 2 + m, cy + f2.size * 1.2 + m), seed + 1)
    return img, cut


def rewards():
    """第1〜7話の報酬の札（各話3枚）と、第八話の四択の札（4枚）。表と切り抜き"""
    d = OUT / "reward"
    d.mkdir(parents=True, exist_ok=True)
    for ep, r in TXT["rewards"].items():
        for k, ch in enumerate(r["choices"], 1):
            img, cut = reward_card(r["title"], ch, int(ep) * 10 + k)
            img.save(d / f"ep{ep}_reward{k}.webp", lossless=True)
            cut.save(d / f"ep{ep}_reward{k}_cut.webp", lossless=True)
    for k, q in enumerate(TXT["ep8_questions"], 1):                  # 第八話：ドアの向こうの問い。見出しはない
        img, cut = reward_card("", q, 80 + k, size=(760, 170))
        img.save(OUT / "ep8" / f"83_card_{k}.webp", lossless=True)
        cut.save(OUT / "ep8" / f"83_card_{k}_cut.webp", lossless=True)
    print("fx/reward/ と ep8/83_card_* を書き出し")



# ================================================================ 小物（文字の物）
VERT = str.maketrans({"『": "﹃", "』": "﹄", "「": "﹁", "」": "﹂", "（": "︵", "）": "︶", "ー": "｜", "《": "︽", "》": "︾"})


def vtext(d, x, y, s, f, fill, pitch=None, max_rows=None):
    """縦書き：x の列に上から。句読点はマスの右上、括弧は縦用の字形。max_rows で折り返し（次の列は左へ）。最後の列の x を返す"""
    pitch = pitch or f.size * 1.05
    row = 0
    for c in s.translate(VERT):
        if max_rows and row >= max_rows:
            x -= f.size * 1.35
            row = 0
        cy = y + row * pitch
        if c in "、。":
            d.text((x + f.size * 0.55, cy - f.size * 0.45), c, font=f, fill=fill)
        else:
            draw_text(d, (x + (f.size - font(f.size).getlength(c)) / 2, cy), c, f, fill)
        row += 1
    return x


def newspaper():
    """第五話：スクラップブックの、剥がれずに残った新聞記事（L1831〜）。縦書きの訃報の切り抜き。写真の欄は空白"""
    from PIL import ImageFilter
    o = TXT["ep5_obit"]
    W, H = 560, 720
    lum = paper(W, H, 51, lum=196)
    img = Image.fromarray(tone(lum)).convert("RGBA")
    d = ImageDraw.Draw(img)
    ink = (38, 30, 28, 255)
    fh, fk, fs, fb, fm = font(40), font(22), font(19), font(14), font(13)
    x = W - 70
    vtext(d, x, 40, o["kicker"], fk, ink)
    x -= 52
    vtext(d, x, 40, o["head"], fh, ink)
    x -= 40
    vtext(d, x, 60, o["sub"], fs, ink)
    d.line([(x - 14, 30), (x - 14, H - 40)], fill=ink, width=1)
    # 写真の欄（空白。本文に写真はないので、灰色の四角に「写真」とも書かない）
    d.rectangle([64, 40, x - 34, 220], outline=(90, 78, 72, 255), width=1)
    x = x - 46
    last = vtext(d, x, 250, o["body"], fb, ink, pitch=15, max_rows=29)
    assert last > 50, last
    vtext(d, 30, 40, o["masthead"], fm, (90, 78, 72, 255))
    # 切り抜きの縁（少し斜め・不揃い）と古び
    mask = Image.new("L", (W, H), 0)
    rg = np.random.default_rng(52)
    ImageDraw.Draw(mask).polygon([(rg.uniform(4, 12), rg.uniform(4, 12)), (W - rg.uniform(4, 12), rg.uniform(4, 12)),
                                  (W - rg.uniform(4, 12), H - rg.uniform(4, 12)), (rg.uniform(4, 12), H - rg.uniform(4, 12))], fill=255)
    img.putalpha(mask.filter(ImageFilter.GaussianBlur(0.6)))
    img = img.rotate(-2.0, resample=Image.BICUBIC, expand=True)
    img.save(OUT / "ep5" / "54_obituary.webp", lossless=True)
    return img


def kamisama(W=940, H=460, sizes=(54, 54, 64), steps=(110, 110, 150), x0=60, y0=90, name="55_kamisama", lum0=150, glue=False):
    """第五話：剥がれた記事の下の、酷く震えた文字（目星成功、L1860〜）。明朝を一字ずつ揺らし、筆圧のむらを付ける。
    glue=True は、新聞の切り抜きの裏面用（切り抜きを PL がめくると、その下に書かれていた文字が出る。糊の跡つき）"""
    from PIL import ImageFilter
    lines = TXT["ep5_kamisama"]
    lum = paper(W, H, 55, lum=lum0)                                 # 記事が剥がれた跡：少し暗い台紙
    if glue:                                                        # 切り抜きが貼ってあった跡：縁に沿った糊のむら
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        edge = np.minimum(np.minimum(xx, W - xx), np.minimum(yy, H - yy))
        lum = lum * (1 - 0.18 * np.exp(-edge / 22)) - 10 * (np.random.default_rng(57).random((H, W)) < 0.002)
    rg = np.random.default_rng(56)
    layer = Image.new("L", (W * 2, H * 2), 0)                      # 2倍で書いて縮める（線のがたつきを細かく）
    y = y0
    for li, s in enumerate(lines):
        size = sizes[li]
        x = x0 + rg.uniform(-10, 30)
        for c in s:
            f = font(int(size * rg.uniform(0.85, 1.18)))
            g = Image.new("L", (size * 2, size * 2), 0)
            ImageDraw.Draw(g).text((size * 0.4, size * 0.3), c, font=f, fill=int(rg.uniform(170, 255)))
            g = g.rotate(rg.normal(0, 8), resample=Image.BICUBIC)
            # 震え：字の形を、細かくずらした2枚を重ねる
            g2 = g.transform(g.size, Image.AFFINE, (1, rg.normal(0, .03), rg.normal(0, 1.2), rg.normal(0, .03), 1, rg.normal(0, 1.2)))
            g = Image.fromarray(np.maximum(np.asarray(g), (np.asarray(g2) * 0.7).astype(np.uint8)))
            layer.paste(255, (int(x * 2), int((y + rg.normal(0, 7)) * 2)), g.resize((g.width * 2, g.height * 2)))
            x += f.getlength(c) * rg.uniform(0.95, 1.15)
        assert x < W + 20, (s, x)
        y += steps[li] + rg.uniform(-6, 6)
    layer = layer.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.5))
    a = np.asarray(layer, np.float32) / 255 * (0.65 + 0.35 * rg.random((H, W)))   # 鉛筆の濃淡
    lum2 = lum * (1 - a * 0.8)
    out = Image.fromarray(tone(lum2)).convert("RGBA")
    out.save(OUT / "ep5" / f"{name}.webp", lossless=True)
    return out


def kamisama_under():
    """新聞の切り抜き（54_obituary）と同じ大きさの、切り抜きの下の台紙。スクリーンパネルの裏面に入れ、PL にめくらせる（漫画のめくり）"""
    ob = Image.open(OUT / "ep5" / "54_obituary.webp")
    W, H = ob.size
    img = kamisama(W, H, sizes=(34, 34, 44), steps=(90, 90, 120), x0=40, y0=int(H * 0.28), name="55b_kamisama_under",
                   lum0=140, glue=True)
    img.putalpha(ob.getchannel("A"))                                # 切り抜きと同じ外形
    img.save(OUT / "ep5" / "55b_kamisama_under.webp", lossless=True)
    return img


def phone_news(key="ep5_phone_news", clock="7:12", name="ep5/56_phone_news.webp"):
    """第五話の朝：手元のスマホに流れてくるニュースの見出し（L1543）。一つだけ「失踪」。色は部屋の色だけ（青は使わない）"""
    W, H = 360, 700
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, W - 1, H - 1], 44, fill=(14, 11, 10, 255), outline=(60, 50, 46, 255), width=3)
    d.rounded_rectangle([14, 14, W - 15, H - 15], 34, fill=(24, 19, 17, 255))
    f0, f1, f2 = font(15), font(17), font(12)
    d.text((34, 32), clock, font=f0, fill=QUIET + (255,))
    d.text((34, 70), "ニュース", font=font(20), fill=TEXT + (255,))
    y = 120
    for i, s in enumerate(TXT[key]):
        d.line([(30, y - 12), (W - 30, y - 12)], fill=(48, 40, 37, 255), width=1)
        assert draw_text(None, (0, 0), s, f1, None) < W - 68, s       # 画面からはみ出さない
        draw_text(d, (34, y), s, f1, (TEXT if "失踪" in s else QUIET) + (255,))
        d.text((34, y + 30), TXT["phone_cats"][key][i] + "　・　" + f"{(i + 1) * 7}分前", font=f2,
               fill=QUIETEST + (255,))
        y += 82
    img.save(OUT / name, lossless=True)
    return img


# ================================================================ 効果音（声なし）
def window_slap(seed=0):
    """第五話：強風で、開いたスクラップブックが窓に叩きつけられる「バン！」（聞き耳 全員失敗）"""
    x = np.zeros(sec(1.6), np.float32)
    place(x, mix(filt(noise(0.12, seed), 300, 4000) * env(sec(0.12), 0.001, 0.03), thump(140, 0.05, seed + 1, 0.3) * 0.6), 0.05)
    place(x, resonate(noise(0.5, seed + 2) * env(sec(0.5), 0.001, 0.08), [1900, 2800, 4200], q=50) * 0.5, 0.055)   # 窓ガラスの震え
    for k in range(6):                                                                                 # 紙がばたつく
        place(x, filt(noise(0.05, seed + 10 + k), 600, 4000) * env(sec(0.05), 0.002, 0.015) * (0.5 - k * 0.07), 0.25 + k * 0.09)
    return reverb(x, 0.5, 0.2)


def beep(sec_=0.6):
    """第六話：犯罪考察チャンネルの放送禁止音（声ではないので使う）。テレビの小さなスピーカー越し"""
    t = np.arange(sec(sec_)) / SR
    x = np.sin(2 * np.pi * 1000 * t) * np.minimum(1, np.minimum(t, sec_ - t) / 0.008)
    return reverb(np.tanh(filt(x.astype(np.float32), 350, 4000) * 1.5) / 1.5, 0.3, 0.2)


def knob_held(seed=0):
    """最終話の非常口：ノブを回そうとしても、途中で止まり、向こうから引き戻される（第一話の「ガチャン」の逆）"""
    x = np.zeros(sec(3.2), np.float32)
    for i, t0 in enumerate((0.2, 1.5)):
        place(x, click(1800, 7000, 0.004, seed + i) * 0.4, t0)                       # 回しはじめ
        strain = resonate(noise(0.6, seed + 5 + i) * env(sec(0.6), 0.05, 0.3), [1300, 2100, 3300], q=30) * 0.25
        place(x, strain * (np.linspace(0.3, 1, sec(0.6)) ** 2), t0 + 0.05)          # 金具がきしむ（力がかかっている）
        place(x, latch(seed + 20 + i, 1.4) * 0.8, t0 + 0.7)                          # がちり、と戻される
    return reverb(x, 0.8, 0.3)


def props():
    (OUT / "ep5").mkdir(parents=True, exist_ok=True)
    newspaper()
    kamisama()
    phone_news()
    phone_news("ep7_phone_news", "8:40", "ep7/77_phone_news.webp")   # 第七話：同じスマホの画面が、今度は自分たちのこと
    kamisama_under()
    write_mp3(OUT / "ep5" / "57_window_slap.mp3", norm(window_slap(570), 0.8))
    write_mp3(OUT / "ep6" / "62_beep_short.mp3", norm(beep(0.5), 0.6))
    write_mp3(OUT / "ep6" / "62_beep_long.mp3", norm(beep(1.1), 0.6))
    write_mp3(OUT / "ep9" / "96_knob_held.mp3", norm(knob_held(960), 0.8))



# ================================================================ 最終話：人数分の空席
# 劇場のホールは、いちばん後ろの列に空席が4つ。遊ぶ人数が少ないときは、余った空席に同じ列の観客を写して埋め、
# 空席の数を PC の人数にそろえる（「空いているのは、ちょうどあなたたちの分」）
SEATS = [(352, 492), (497, 636), (641, 778), (782, 920)]          # 空席の左右（1280×720。背もたれの上端 y≈545）
DONORS = [(190, 345), (932, 1092)]                                  # 同じ列の、座っている観客（左・右）


def hall_for(players):
    from PIL import ImageFilter
    src = Image.open(SCENES / "ep9_02_hall.jpg").convert("RGB")
    fill = {1: [0, 2, 3], 2: [0, 3], 3: [3], 4: []}[players]          # 残す空席が真ん中に寄るように埋める
    out = src.copy()
    for i, s in enumerate(fill):
        dx0, dx1 = DONORS[i % 2]
        patch = src.crop((dx0, 425, dx1, 610))
        if i % 2 == 0:
            patch = patch.transpose(Image.FLIP_LEFT_RIGHT)              # 同じ人が並ばないよう、左右を返す
        x0, x1 = SEATS[s]
        w = x1 - x0 + 16
        patch = patch.resize((w, int(patch.height * w / patch.width)), Image.LANCZOS)
        m = Image.new("L", patch.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([10, 0, patch.width - 10, patch.height], 30, fill=255)
        m = m.filter(ImageFilter.GaussianBlur(8))
        out.paste(patch, (x0 - 8, 610 - patch.height), m)
    out.save(OUT / "ep9" / f"97_hall_{players}pc.jpg", quality=88)
    return out


def ep9_seats():
    for n in (1, 2, 3):
        hall_for(n)



# ================================================================ 動く素材（追加）
def blink_close():
    """第一話の講演：POW 失敗で「目蓋がストンと落ちて開かない」。とろんと重くなり、一度持ち直し、ストンと閉じて真っ暗のまま"""
    keys = [(0.0, 1.35), (0.4, 1.35), (1.6, 0.38), (1.9, 0.6), (2.8, 0.16), (2.92, 0.0)]
    frames = []
    for i in range(int(keys[-1][0] * FPS) + 1):
        tt = i / FPS
        for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
            if t0 <= tt <= t1:
                k = (tt - t0) / max(t1 - t0, 1e-6)
                v = v0 + (v1 - v0) * (k * k * (3 - 2 * k))
                break
        else:
            v = 0.0
        frames.append(lids(v, feather=0.12 + 0.35 * (1 - min(v, 1))))
    frames += [lids(0.0)] * int(0.5 * FPS)
    save_webp_anim(frames, OUT / "shared" / "72_blink_close.webp")
    return frames


def lobby_flicker(L=10.0):
    """最終話のロビー：入口の照明が「ちか、ちか」と明滅する（前景、ループ）。暗くなる回数は1秒に3回まで"""
    rg = np.random.default_rng(97)
    n = int(L * FPS)
    dim = np.zeros(n)
    f = int(rg.uniform(10, 30))
    while f < n - 8:
        length = int(rg.integers(2, 6))
        depth = rg.uniform(0.35, 0.75)
        dim[f:f + length] = depth
        if rg.random() < 0.4:                                     # 点き直しに失敗して、もう一度
            dim[f + length + 1:f + length + 3] = depth * 0.8
        f += int(rg.uniform(0.6, 2.8) * FPS)                       # 次まで 0.6〜2.8 秒（1秒に3回を超えない）
    cache = {}
    frames = []
    for v in dim:
        key = round(v, 2)
        if key not in cache:
            cache[key] = Image.new("RGBA", (640, 360), BLACK + (int(255 * key),))
        frames.append(cache[key])
    save_webp_anim(frames, OUT / "ep9" / "98_lobby_flicker_loop.webp", loop=0)
    return frames


def darkness_proof():
    """【暗闇証明】（L3240〜）：POW*5・*4・*3 に成功するたびに、女の形の輪郭がほどけていく。
    0＝完全、1＝少しほどける、2＝大きくほどける、3＝何もない戸口。reach＝《女》が判定するとき（女の形が少し近づく）"""
    from PIL import ImageFilter
    from scipy.ndimage import distance_transform_edt
    sys.path.insert(0, str(ROOT / "tools"))
    from export_ccfolia import door
    draft = not FULL_DOOR.exists()
    base = Image.open(ROOT / "opening" / "bg.png").convert("RGB")
    bg = door(base, 9) if draft else door(base, 9, FULL_DOOR)
    m = doorway_mask(bg)
    ys, xs = np.where(m)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    w_src = Image.open(ROOT / "build" / "ccfolia" / "npc" / "npc_woman.webp").getchannel("A")
    H, W = m.shape
    rg = np.random.default_rng(91)
    streak = np.asarray(Image.fromarray((rg.random((H // 24 + 1, W // 3 + 1)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC),
                        np.float32) / 255
    lum = 30 + 16 * streak
    rgb = np.clip(lum[..., None] * lut()[np.clip(lum, 0, 255).astype(int)], 0, 255)

    def shape_at(scale):
        h = int((y1 - y0) * 0.9 * scale)
        w = int(w_src.width * h / w_src.height)
        s = Image.new("L", (W, H), 0)
        s.paste(w_src.resize((w, h), Image.LANCZOS), (int((x0 + x1) / 2 - w / 2), int(y1 - h - 1)))
        return np.asarray(s.filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255

    noise = np.asarray(Image.fromarray((np.random.default_rng(92).random((H // 2, W // 2)) * 255).astype(np.uint8)).resize(
        (W, H), Image.BICUBIC), np.float32) / 255
    sfx = "_draft" if draft else ""

    def save(shape, name):
        a = (m * (1 - shape) * 255).astype(np.uint8)
        im = np.zeros((H, W, 4), np.uint8)
        im[..., :3] = (rgb * m[..., None]).astype(np.uint8)
        im[..., 3] = a
        Image.fromarray(im, "RGBA").save(OUT / "ep9" / f"99_proof_{name}{sfx}.webp", lossless=True)

    full = shape_at(1.0)
    inside = distance_transform_edt(full > 0.5)                     # 輪郭からの距離（内側ほど大きい）
    for k, depth in enumerate((0, 4, 10)):                           # ほどける深さ（px）
        if depth == 0:
            s = full
        else:
            # 輪郭の近くから、むらのある形で欠けていく（糸がほどけるように、縦に流れるむら）
            erode = (inside < depth * (0.4 + 1.2 * noise)) & (full > 0)
            s = full * (1 - erode) * (0.85 if k == 2 else 1.0)
        save(s, str(k))
    save(np.zeros_like(full), "3")
    save(shape_at(1.12), "reach")
    bg.save(OUT / "ep9" / f"90_full_door_bg{sfx}.jpg", quality=88)


def queue_panel():
    """第七話：「町中だろうが、家の中に居ようが、ふと見れば行列」（L2290〜）。PC の置き場の後ろに出す、
    楽しげに並ぶ人々の後ろ姿の列（顔は見せない）。スクリーンパネル 128×54 マス（PC の置き場と同じ範囲）"""
    from PIL import ImageFilter
    src = Image.open(ROOT / "build" / "ccfolia" / "npc" / "npc_figure.webp").getchannel("A")
    W, H = 1280, 540
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rg = np.random.default_rng(73)
    n = 22
    for i in range(n):                                             # 右手前から左奥へ、だんだん小さく
        k = i / (n - 1)
        scale = 1.0 - 0.72 * k
        h = int(H * 0.95 * scale)
        a = src.resize((int(src.width * h / src.height * rg.uniform(0.85, 1.1)), h), Image.LANCZOS)
        if rg.random() < 0.5:
            a = a.transpose(Image.FLIP_LEFT_RIGHT)
        a = a.filter(ImageFilter.GaussianBlur(4 + 6 * k))
        a = a.point(lambda v, o=0.7 - 0.35 * k: int(min(255, v * 1.3) * o))
        layer = Image.new("RGBA", a.size, (12, 9, 9, 255))
        layer.putalpha(a)
        x = int(W * (0.92 - 0.82 * k) - a.width / 2 + rg.normal(0, 12))
        y = int(H - h - k * H * 0.28)
        img.alpha_composite(layer, (x, y)) if x + a.width > 0 else None
    img.save(OUT / "ep7" / "73_queue_panel.webp", lossless=True)
    return img


def moving():
    blink_close()
    lobby_flicker()
    darkness_proof()
    queue_panel()



# ================================================================ 環境音（BGM の穴埋め。声なし）
def rain(L=62, seed=0):
    """第七話：厚い雲の雨の町。屋根や路面を打つ細かい雨粒と、低いざあという音、ときどき雨どいの滴り"""
    n = sec(L)
    wash = filt(noise(L, seed), 300, 6000) * (0.8 + 0.2 * smooth_random(L, 0.3, seed + 1))
    drops = np.zeros(n, np.float32)
    rg = np.random.default_rng(seed + 2)
    for t0 in rg.uniform(0, L, int(L * 60)):
        place(drops, click(1500, 6000, 0.004, int(t0 * 1000) % 997) * rg.uniform(0.03, 0.12), t0)
    gutter = np.zeros(n, np.float32)
    for t0 in np.arange(rg.uniform(0, 1), L, 0.9) + rg.normal(0, 0.08, int(L / 0.9) + 1)[: len(np.arange(0, L, 0.9))]:
        place(gutter, resonate(noise(0.1, int(t0 * 100)) * env(sec(0.1), 0.001, 0.02), [900, 1400], q=30) * 0.15, max(0, t0))
    low = filt(noise(L, seed + 3), 60, 300) * 0.6
    return loop_seam(norm(wash) * 0.5 + drops + gutter + norm(low) * 0.2, 2.0)


def channel(L=62, seed=0):
    """第七話：地下水路。増水した濁流の低いうなりと、コンクリートに響く水音"""
    flow = filt(noise(L, seed), 80, 1200) * (0.7 + 0.3 * smooth_random(L, 0.5, seed + 1))
    splash = filt(noise(L, seed + 2), 1200, 5000) * smooth_random(L, 2.0, seed + 3) ** 3 * 0.6
    return loop_seam(reverb(norm(flow) * 0.8 + splash, 2.0, 0.5, 2500), 2.0)


def ambience():
    write_mp3(OUT / "ep7" / "74_rain_loop.mp3", norm(rain(seed=740), 0.5))
    write_mp3(OUT / "ep7" / "75_channel_loop.mp3", norm(channel(seed=750), 0.55))
    dusk = ROOT / "build" / "ccfolia" / "moth" / "dusk.wav"
    if dusk.exists():                                               # 第五話の夕暮れ（羽ばたきの音なし）。部屋の中のシーン用
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", "0.6", "-i", str(dusk), "-af", "afade=t=in:d=2",   # 頭の羽ばたきを切る
                        "-c:a", "libmp3lame", "-q:a", "5",
                        str(OUT / "ep5" / "58_dusk_loop.mp3")], check=True)
        print("ep5/58_dusk_loop.mp3")



# ================================================================ 第八話：ベランダのループ（絵が届いたら本番）
# ChatGPT の3枚（人なし／手を振る女／のけぞる女。同じ構図）の差から女の形だけを切り出し、
# 手を振って立つ → のけぞる → 手すりの向こうへ沈んで消える → 誰もいない、を6秒でループさせる（『回路』のように、遠くから淡々と）。
# 窓の外の白くぼやけた景色は、こちらで白いモザイク（画素の粗いブロック）にして揺らす（本文「白いモザイクをかけていた」）
BALCONY = [ROOT / "assets" / f"ep8_balcony_{k}.png" for k in range(3)]   # 届いたらここに置く（0=人なし、1=手を振る、2=のけぞる）
WINDOW = (205, 30, 505, 445)                                           # 窓の範囲（家具のない部屋の構図。届いた絵で測り直す）


def toned(src):
    """届いた絵を、部屋と同じ赤茶にそろえる（make_scene_bg と同じ物差し）"""
    from PIL import ImageOps
    img = ImageOps.fit(Image.open(src).convert("RGB"), (1280, 720), Image.LANCZOS)
    a = np.asarray(img).astype(np.float32)
    lum = (a @ np.array([0.299, 0.587, 0.114], np.float32)) / 255 * 236 + 6
    yy, xx = np.mgrid[0:720, 0:1280].astype(np.float32)
    lum = lum * 0.62 * np.clip(1 - 0.55 * (((xx - 640) / 760) ** 2 + ((yy - 340) / 470) ** 2), 0.35, 1)
    return np.clip(lum[..., None] * lut()[np.clip(lum, 0, 255).astype(int)], 0, 255).astype(np.uint8)


def balcony_inputs():
    """本番は届いた3枚。届くまでは、家具のない部屋の窓の向こうに、女の立ち絵の影を置いた仮の3枚で動きを作る"""
    if all(p.exists() for p in BALCONY):
        return [toned(p) for p in BALCONY], False
    from PIL import ImageFilter
    e = np.asarray(Image.open(SCENES / "ep8_01_room.jpg").convert("RGB"))
    w_src = Image.open(ROOT / "build" / "ccfolia" / "npc" / "npc_woman.webp").getchannel("A")
    out = [e]
    for lean in (0, 22):
        h = 230
        a = w_src.resize((int(w_src.width * h / w_src.height), h), Image.LANCZOS)
        a = a.rotate(lean, resample=Image.BICUBIC, expand=True, center=(a.width / 2, h * 0.55))
        m = Image.new("L", (1280, 720), 0)
        m.paste(a, (360 - a.width // 2, 432 - a.height))
        m = np.asarray(m.filter(ImageFilter.GaussianBlur(0.8)), np.float32)[..., None] / 255
        out.append((e * (1 - m) + np.array([8, 6, 6]) * m).astype(np.uint8))
    return out, True


def figure_mask(base, other):
    """2枚の差から、女の形だけを取り出す（いちばん大きくつながった部分）"""
    from scipy.ndimage import binary_closing, binary_opening, label
    d = np.abs(other.astype(np.float32) - base.astype(np.float32)).mean(-1)
    m = binary_opening(binary_closing(d > 18, iterations=3), iterations=1)
    lab, n = label(m)
    if n == 0:
        raise SystemExit("女の形が見つからない（3枚の構図がずれていないか確認）")
    keep = lab == (np.argmax(np.bincount(lab.ravel())[1:]) + 1)
    return keep


def balcony_loop():
    from PIL import ImageFilter
    (e, a, b), draft = balcony_inputs()
    ma, mb = figure_mask(e, a), figure_mask(e, b)
    x0, y0, x1, y1 = WINDOW
    # 手すりの高さ：窓の中で、横に強い線がいちばん目立つ行（下半分）
    # 手すりの高さ：窓の高さの 45〜80% の範囲で、横に強い線がいちばん目立つ行（窓の下枠を拾わないように範囲を絞る）
    g = np.abs(np.diff(e[y0:y1, x0:x1].astype(np.float32).mean(-1), axis=0)).mean(1)
    lo, hi = int(len(g) * 0.45), int(len(g) * 0.8)
    rail = y0 + lo + int(np.argmax(g[lo:hi]))
    # 窓の外（白くぼやけるところ）：窓の範囲で、手すりより上の明るいところ
    lum = e.astype(np.float32).mean(-1)
    outside = np.zeros(lum.shape, bool)
    outside[y0:rail, x0:x1] = lum[y0:rail, x0:x1] > np.percentile(lum[y0:rail, x0:x1], 35)
    sa = Image.fromarray(np.dstack([a, (ma * 255).astype(np.uint8)]), "RGBA")
    sb = Image.fromarray(np.dstack([b, (mb * 255).astype(np.uint8)]), "RGBA")
    ys = np.where(mb)[0]
    fps, L = FPS, 6.0
    frames, mosaic = [], None
    rg = np.random.default_rng(86)
    for i in range(int(L * fps)):
        tt = i / fps
        fr = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
        if i % 3 == 0:                                            # モザイクは1秒に10回だけ変える（容量のため）
            blk = int(rg.uniform(14, 30))
            sx = int(rg.normal(0, 6))
            src = np.roll(e, sx, axis=1).astype(np.float32)
            small = Image.fromarray(src.astype(np.uint8)).resize((1280 // blk, 720 // blk), Image.BILINEAR)
            big = np.asarray(small.resize((1280, 720), Image.NEAREST)).astype(np.float32)
            big = big * 0.4 + 210 * 0.6                            # 白っぽく飛ばす
            mosaic = np.zeros((720, 1280, 4), np.uint8)
            mosaic[..., :3] = np.clip(big * lut()[np.clip(big.mean(-1), 0, 255).astype(int)] / np.maximum(lut()[200], 1e-3) * 0.8, 0, 255)
            mosaic[..., 3] = (outside * 255).astype(np.uint8)
        fr.alpha_composite(Image.fromarray(mosaic, "RGBA"))
        tw = np.floor(tt * 8) / 8                                  # 女の動きは1秒8コマ（パラパラ漫画のようにカクつかせる。人ではないものの動き）
        if tw < 2.4:                                               # 手を振って立っている（わずかに揺れる）
            fr.alpha_composite(sa, (int(round(np.sin(tw * 2.2))), 0))
        elif tw < 2.9:                                             # のけぞる
            fr.alpha_composite(sb)
        elif tw < 3.5:                                             # 手すりの向こうへ沈む（加速して落ちる）
            k = (tw - 2.9) / 0.6
            dy = int((ys.max() - ys.min()) * 1.1 * k * k)
            moved = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
            moved.alpha_composite(sb.rotate(-25 * k, resample=Image.BICUBIC, center=(int(np.where(mb)[1].mean()), rail)), (0, dy))
            arr = np.asarray(moved).copy()
            arr[rail:, :, 3] = 0                                   # 手すりより下（外）は見えない
            fr.alpha_composite(Image.fromarray(arr, "RGBA"))
        frames.append(fr)
    print("手すりの高さ", rail)
    sfx = "_draft" if draft else ""
    save_webp_anim(frames, OUT / "ep8" / f"86_balcony_loop{sfx}.webp", lossless=False, quality=80, loop=0)
    Image.fromarray(e).save(OUT / "ep8" / f"86_balcony_bg{sfx}.jpg", quality=88)
    return frames, OUT / "ep8" / f"86_balcony_bg{sfx}.jpg"


def balcony():
    fr, bg = balcony_loop()
    write_mp3(OUT / "preview" / "silence.mp3", silence(13))
    preview(bg, fr * 2, OUT / "preview" / "silence.mp3", "ep8_balcony_loop", tail=0)



# ================================================================ 第七話：ハゲタカの目（絵が届いたら本番）
# ChatGPT の2枚（目が左右ばらばら／目がこちらを見据える。ほかは同じ）の差から目のところだけを見つけ、
# 暗闇の中で目だけが忙しなく動く → ぴたりとこちらで止まる → 3秒 → 全体がゆっくり浮かび上がる、の1回再生の前景にする
VULTURE = [ROOT / "assets" / f"ep7_vulture_{k}.png" for k in (1, 2)]   # 届いたらここに置く（1=ばらばら、2=こちら）


def vulture_inputs():
    if all(p.exists() for p in VULTURE):
        return [toned(p) for p in VULTURE], False
    base = np.asarray(Image.open(SCENES / "ep7_02_underpass.jpg").convert("RGB")).copy()   # 仮：高架下に、目を2つ描くだけ
    out = []
    for look in (((-6, -2), (5, 3)), ((0, 2), (0, 2))):
        im = Image.fromarray(base.copy())
        d = ImageDraw.Draw(im)
        for (cx, cy), (px, py) in zip(((600, 250), (690, 255)), look):
            d.ellipse([cx - 18, cy - 12, cx + 18, cy + 12], fill=(205, 180, 150))
            d.ellipse([cx + px - 6, cy + py - 6, cx + px + 6, cy + py + 6], fill=(10, 8, 8))
        out.append(np.asarray(im))
    return out, True


def vulture_eyes():
    from PIL import ImageFilter
    from scipy.ndimage import binary_dilation, label
    (a, b), draft = vulture_inputs()
    diff = np.abs(a.astype(np.float32) - b.astype(np.float32)).mean(-1) > 20
    lab, n = label(binary_dilation(diff, iterations=6))
    sizes = np.bincount(lab.ravel())[1:]
    eyes = np.isin(lab, np.argsort(sizes)[-2:] + 1)                 # いちばん大きい2か所＝二つの目
    eyes = binary_dilation(eyes, iterations=10)
    glow = np.asarray(Image.fromarray((eyes * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(8)), np.float32) / 255
    fps = FPS
    rg = np.random.default_rng(77)
    frames = []
    dark = np.zeros((720, 1280, 3), np.float32) + np.array(BLACK, np.float32)

    def frame(img, eye_gain, light, shift=(0, 0)):
        src = np.roll(np.roll(img.astype(np.float32), shift[1], 0), shift[0], 1) if shift != (0, 0) else img.astype(np.float32)
        e = src * glow[..., None] * eye_gain
        full = img.astype(np.float32) * light
        out = np.maximum(dark * (1 - light) + full, e)
        return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).convert("RGBA")

    for i in range(int(2.5 * fps)):                                 # 目だけ。忙しなく動く（小さく跳ねるように）
        sh = (int(rg.normal(0, 2)), int(rg.normal(0, 1))) if i % 4 == 0 else (0, 0)
        frames.append(frame(a, 0.9, 0.0, sh))
    ys_, xs_ = np.where(eyes)
    cx, cy = xs_.mean(), ys_.mean()
    for z in (1.4, 2.0, 2.8):                                       # ぴたり。目のアップを3回、だんだん近く（出崎統の繰り返しのショット）
        f0 = frame(b, 1.0, 0.0)
        w, h = int(1280 / z), int(720 / z)
        x0, y0 = int(np.clip(cx - w / 2, 0, 1280 - w)), int(np.clip(cy - h / 2, 0, 720 - h))
        frames += [f0.crop((x0, y0, x0 + w, y0 + h)).resize((1280, 720), Image.LANCZOS)] * int(0.3 * fps)
    frames += [frame(b, 1.0, 0.0)] * int(2.1 * fps)                # 引いて、こちらを見据えたまま
    for i in range(int(1.8 * fps)):                                 # 全体がゆっくり浮かぶ
        k = (i + 1) / int(1.8 * fps)
        frames.append(frame(b, 1.0, k * k))
    sfx = "_draft" if draft else ""
    save_webp_anim(frames, OUT / "ep7" / f"76_vulture_eyes{sfx}.webp", lossless=False, quality=80)
    Image.fromarray(b).save(OUT / "ep7" / f"76_vulture_bg{sfx}.jpg", quality=88)
    return frames, OUT / "ep7" / f"76_vulture_bg{sfx}.jpg"


def vulture():
    fr, bg = vulture_eyes()
    write_mp3(OUT / "preview" / "silence.mp3", silence(13))
    preview(bg, fr, OUT / "preview" / "silence.mp3", "ep7_vulture_eyes", tail=1)


# ================================================================ 全話：気配の音
def presence():
    """全話を通す「気配の音」（怪談の「カラン、コロン」の考え方）：映写機が一瞬だけカタカタと回る、ごく小さな音。
    化身がそばにいる瞬間に、各話で1回だけ鳴らす。説明はしない。最終話の劇場で映写機が回り出したとき、正体がわかる"""
    n = sec(1.4)
    x = np.zeros(n, np.float32)
    for k in range(22):                                             # 1秒24回の送り。回り始めて、すぐ止まる
        t0 = 0.15 + k / 24 * (1 + 0.6 * (k / 22) ** 2)
        place(x, click(1200, 4500, 0.004, 790 + k % 7) * 0.4 * np.sin(np.pi * k / 22) ** 0.7, t0)
    motor = filt(noise(1.4, 791), 90, 300, order=4) * np.sin(np.pi * np.arange(n) / n) ** 2 * 0.5
    x = reverb(filt(x + motor, hi=3500), 1.6, 0.6, 2500)            # 遠く、広いところで鳴っているように
    write_mp3(OUT / "shared" / "79_presence_projector.mp3", norm(x, 0.35))


PIECES = {"presence": presence, "vulture": vulture, "balcony": balcony, "ambience": ambience, "moving": moving, "seats": ep9_seats, "props": props, "reward": rewards, "ep6": ep6, "recap": recap, "ep1": ep1, "ep2": ep2, "ep3": ep3, "ep4": ep4, "ep5": ep5, "ep7": ep7, "ep8": ep8, "ep9": ep9}

if __name__ == "__main__":
    for name in sys.argv[1:] or PIECES:
        PIECES[name]()
