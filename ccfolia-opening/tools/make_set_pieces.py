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
  ep8/86_balcony_bg.jpg / 86_balcony_loop.webp … ベランダ（背景）と、手を振る → 反る → まっすぐ落ちて消える → 窓へ寄る（全面の前景ループ、カーテンは絵の布ごと風で動く）。
                                  絵が届くまでは _draft（家具のない部屋に仮の影）
  ep8/84_nandomo.webp           … 「何度も」が画面を埋めて真っ黒になる。奥の窓では女が何度も落ち続ける（前景、1回再生。balcony でも作り直す）
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
  ep9/87_af_card.webp           … AF《とある化身の知識》のカード（スクリーンパネル。各話で決まる所は af_fill、空なら空欄）
  ep9/88_seat_phone.webp        … 座席に返されたスマホ（第七話で盗られたもの。画面は第七話の朝のニュースのまま）
  ep9/89_endb_fall.webp         … エンドB：ファミレスの窓の外を、女が一瞬落ちる（前景、1回再生）。ベランダの絵が届くまでは _draft
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
    """まぶたの形。open_=0 で閉じ、1.3 で画面の外まで開く。
    上まぶたは下より大きく動き、縁はまつ毛でわずかに波打って均一でない。上の縁のすぐ内側に、まつ毛の薄い影の帯。
    開ききる前は、目が明るさに慣れていないので、内側にうっすら暖色の白いもや（露出の順応）"""
    if open_ <= 0.01:
        return Image.new("RGBA", (w, h), BLACK + (255,))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = xx / w
    wob = 0.025 * np.sin(u * 23.0 + 1.3) + 0.018 * np.sin(u * 51.0 + 0.4) + 0.012 * np.sin(u * 97.0)   # まつ毛の不揃い
    cy = h * (0.50 - 0.04 * min(open_, 1))                          # 開くにつれて、すき間の中心が少し上へ
    a = w * (1.25 + 0.4 * open_)                                    # 細いすき間でも視野の端から端まで続く（左右の角を黒くしない）
    b_up = max(h * 0.70 * open_, 0.5)                              # 上まぶた（よく動く）
    b_dn = max(h * 0.48 * open_, 0.5)                              # 下まぶた（あまり動かない）
    b = np.where(yy < cy, b_up, b_dn)
    r = np.sqrt(((xx - w / 2) / a) ** 2 + ((yy - cy) / b) ** 2) * (1 + wob * (yy < cy))
    alpha = smoothstep(1 - feather, 1 + feather, r)
    # まつ毛の線は描かない：まぶたの縁は目に近すぎて大きくぼけ、主観では線として見えない（以前はすき間の内側に二重の縁が出ていた）
    alpha = np.clip(alpha, 0, 1)
    veil = 0.10 * np.clip(1 - open_ / 0.9, 0, 1) * (1 - alpha)         # 慣れていない明るさ
    im = np.zeros((h, w, 4), np.float32)
    im[..., :3] = (np.array(BLACK, np.float32) * alpha[..., None] + np.array([235, 215, 190], np.float32) * veil[..., None]) / np.maximum(alpha + veil, 1e-4)[..., None]
    im[..., 3] = np.clip(alpha + veil, 0, 1) * 255
    return Image.fromarray(im.astype(np.uint8), "RGBA")


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
    文字の奥、開いた窓の向こうでは、ベランダの女（逆光の影）が何度ものけぞって手すりの向こうへ落ち、また立っている。
    文字が増えるほど、繰り返しは速く、間がなくなり、最後は前の回が落ちきる前に次の回が立つ。
    女はベランダと同じ材料（balcony_woman）から作るので、ベランダの絵が届くまでは仮の絵、届けば本番の絵になる。
    同じ時間で上がり続ける音（85_shepard_then_silence.mp3）が、真っ黒のコマで止まる"""
    # 文字は格子に並べず、書き殴るように画面に積もっていく（伊藤潤二のモーションコミックのように、文字が画の一部になる）。
    # 大きさ・濃さ・傾きを1本ずつ揺らし、後半ほど大きく・密に重なる。窓の上だけは控えめにして、落ちる女を最後まで見せる
    head = TXT["ep8_again_head"]
    unit = TXT["ep8_again_unit"]
    rg = np.random.default_rng(84)
    dur = 9.6
    n_fr = int(dur * FPS)
    x0, y0, x1, y1 = WINDOW
    strokes = []                                                 # (出す時刻, 画像, x, y)
    for k, line in enumerate(head):                              # 冒頭の2行は右から、読める大きさで1文字ずつ
        for r, c in enumerate(line):
            strokes.append((0.3 + k * 1.5 + r * 0.09, [c], int(40 + 8 * k + rg.normal(0, 3)), TEXT, 255, rg.normal(0, 1.5),
                            1280 - 100 - k * 70 + rg.normal(0, 2) + r * 1.5 * k, 50 + r * (46 + 6 * k) + rg.normal(0, 3)))
    fw_rail = balcony_woman()[0].box[3] - 10                    # 女の足もとまで
    t = 3.2
    cur = [-1, 0, 0]
    while t < dur - 0.3:
        prog = (t - 3.2) / (dur - 3.5)
        sz = int(np.clip(rg.lognormal(np.log(28 + 26 * prog), 0.4), 16, 110))
        n = int(rg.integers(1, 3 + int(2 * prog)))
        txt = list(unit * n)
        slot = int(t * FPS) // 6                                     # 6コマごとに、書き殴る場所が移る（一度に画面のあちこちが変わると容量が膨らむ）
        if slot != cur[0]:
            cur[:] = [slot, rg.uniform(0, 1280), rg.uniform(0, 720)]
        x = cur[1] + rg.normal(0, 50 + 40 * prog)
        y = cur[2] + rg.normal(0, 50) - sz * n * 0.6
        in_win = x0 - 30 - sz * 1.6 < x < x1 + 30 and y - 20 < fw_rail + 10 and y + sz * 1.05 * n + sz > y0
        if in_win and rg.random() > 0.04 + 0.06 * prog:          # 窓の上は控えめ（落ちる女を最後まで見せる。毎コマ動くところに文字が重なると容量も膨らむ）
            t += 0.002
            continue
        col = [TEXT, QUIET, QUIETEST][int(rg.choice(3, p=[0.45, 0.35, 0.2]))]
        a = int(rg.uniform(120, 255))
        strokes.append((t, txt, sz, col, a, rg.normal(0, 3 + 5 * prog), x, y))
        t += 0.16 * np.exp(-prog * 3.2) + 0.01
    strokes.sort(key=lambda s: s[0])
    print("文字の本数", len(strokes))

    def stroke_img(txt, sz, col, a, ang):
        f = font(sz)
        im = Image.new("RGBA", (int(sz * 1.6), int(sz * 1.05 * len(txt) + sz)), (0, 0, 0, 0))
        dd = ImageDraw.Draw(im)
        for r, c in enumerate(txt):
            vchar(dd, sz * 0.3 + rg.normal(0, sz * 0.03), sz * 0.3 + r * sz * 1.02, c, f, sz, col + (a,))
        im = halo(im, 5, 6, 1.1)
        return im.rotate(ang, resample=Image.BICUBIC, expand=True)

    # 落ちる回の予定：ベランダと同じ「振る → 止まる → 反る → まっすぐ落ちる」。はじめは間をおいて1回ずつ、
    # 文字が増えるにつれて間が縮み、後半は前の回が落ちきる前に次の女がもう立っている
    fw, e, outside, _ = balcony_woman()
    events, ts = [], 0.25
    while ts < dur:
        prog = ts / dur
        speed = 1 + 1.8 * prog ** 1.3
        wave = max(0.15, 1.5 * np.exp(-prog * 3.2)) * (0.85 + 0.3 * rg.random())
        tl = ts + wave
        tf = tl + 0.15 + 0.35 / speed
        events.append((ts, tl, tf, rg.normal(0, 3 + 6 * prog)))
        ts = tf + DROP_T - (0.25 * prog ** 0.7 if prog > 0.4 else -0.5 * (1 - prog))
    print("落ちる回数", len(events))
    cp = CurtainPlate(e)
    mos = BalconyMosaic(e, outside, seed=84)
    layer = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    frames, si, wcache = [], 0, None
    for i in range(n_fr):
        tt = i / FPS
        while si < len(strokes) and strokes[si][0] <= tt and i % 6 == 0:   # 文字は6コマに1回まとめて増やす（容量のため）
            _, txt, sz, col, a, ang, x, y = strokes[si]
            paste_clip(layer, stroke_img(txt, sz, col, a, ang), int(x), int(y))
            si += 1
        if i % 2 == 0 or wcache is None:                                    # 絵（カーテン・女）は1秒15コマ（容量のため。落ちる所は縦のブレでつながる）
            if i % 6 == 0:
                mos.step()
            img = over(cp.warp(over(e.astype(np.float32), mos.cur), tt), drop_layer(fw, tt, events, shutter=1 / 30))
            wcache = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")
        fr = Image.alpha_composite(wcache, layer)                           # 明るい絵のまま（暗くしない）。暗くなるのは最後の真っ黒だけ
        if tt > dur - 0.5:
            fr = Image.blend(fr, Image.new("RGBA", (1280, 720), BLACK + (255,)), 0.5)
        frames.append(fr)
    hold = int(0.2 * FPS)
    frames += [frames[-1]] * hold
    frames.append(Image.new("RGBA", (1280, 720), BLACK + (255,)))     # 真っ黒（ここで音も止まる）
    small = [f.resize((854, 480), Image.LANCZOS) for f in frames]       # 全面が動くので、854×480 で書き出して 5MB に収める（ココフォリアが画面に引き伸ばす）
    save_webp_anim(small, OUT / "ep8" / "84_nandomo.webp", lossless=False, quality=55)
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
    ep8_nandomo()


def ep8_nandomo():
    """「何度も」の前景と上がり続ける音、確認用の動画（背景はベランダの絵。届くまでは _draft）"""
    fr = nandomo()
    dur = (len(fr) - 1) / FPS
    shepard(dur)
    tmp = OUT / "preview" / "tmp2.mp3"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(OUT / "ep8" / "85_shepard_then_silence.mp3"),
                    "-t", f"{dur + 2:.2f}", str(tmp)], check=True)
    bg = OUT / "ep8" / ("86_balcony_bg.jpg" if all(p.exists() for p in BALCONY) else "86_balcony_bg_draft.jpg")
    if not bg.exists():
        balcony_loop()
    preview(bg, fr, tmp, "ep8_5_nandomo", tail=2)


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


def seamless(img, feather=0.22):
    """上下左右につないでも継ぎ目が出ない布にする：半分ずらした自分自身を、縁の近くでだけ溶かし込む。
    （裏返してつなぐと、つなぎ目が鏡の線として縦・横の帯に見えていた）"""
    a = np.asarray(img, np.float32)
    H, W = a.shape[:2]
    rolled = np.roll(np.roll(a, H // 2, 0), W // 2, 1)
    wx = np.minimum(np.arange(W), W - 1 - np.arange(W)) / (W * feather)
    wy = np.minimum(np.arange(H), H - 1 - np.arange(H)) / (H * feather)
    w = np.clip(np.minimum(wx[None, :], wy[:, None]), 0, 1)
    w = (w * w * (3 - 2 * w))[..., None]
    # 半分ずらした方の縁は真ん中に来るので、そこは元の絵が勝つ。縁だけずらした方（＝元の真ん中の布）になる
    return Image.fromarray(np.clip(a * w + rolled * (1 - w), 0, 255).astype(np.uint8))


def sheet_loop(period=1.4, size=(1280, 720)):
    """シートを左右にかき分けると、すぐ奥にまた同じシートがある。1周ごとに、奥のシートが手前のシートの位置まで来るのでつながる"""
    W, H = size
    tex = seamless(sheet_texture().resize(size, Image.LANCZOS))
    n = int(round(period * FPS))
    big = Image.new("RGB", (W * 3, H * 3))
    for i in range(3):
        for j in range(3):
            big.paste(tex, (i * W, j * H))
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
        # 布は板のように平行移動せず、手で押された縁ほど大きく動き、遠い所（吊ってある側）はあまり動かない。
        # その差の分だけ布が縮んで寄り、縦のひだができる（縮んだ所ほどひだが深い）
        u = np.linspace(0, W / 2, 256)
        push = gap / 2 * (0.35 + 0.65 * (u / (W / 2)) ** 1.5)     # 布の点 u が左へ押される量（縁 u=W/2 で gap/2）
        xd = u - push                                            # 画面上の位置（u とともに増える）
        xl = xx - wave
        src_l = np.interp(xl, xd, u, left=-1e4, right=W / 2)      # 画面の x → 布の点（左半分）
        src_r = W - np.interp(W - xl, xd, u, left=-1e4, right=W / 2)
        comp = np.interp(xl, xd, np.gradient(xd, u))             # 1 より小さいほど縮んでいる
        comp_r = np.interp(W - xl, xd, np.gradient(xd, u))
        cmp = np.where(xl < W / 2, comp, comp_r)
        src = np.where(xl < W / 2, src_l, src_r)
        fold = 1 - 0.4 * np.clip(1 - cmp, 0, 1) * (0.5 + 0.5 * np.sin(src / 9.0))   # 縦のひだ
        shade = shade * fold[..., None]
        sx_l = np.clip(src_l, 0, W - 1).astype(int)
        sx_r = np.clip(src_r, 0, W - 1).astype(int)
        yi = yy.astype(int)
        mask_l, mask_r = left[..., None], right[..., None]
        if k > 0.02:                                             # 押しのけられる布には横のモーションブラー（速いほど長く）
            from scipy.ndimage import uniform_filter1d
            front = uniform_filter1d(front, max(1, int(40 * k ** 0.7)), axis=1, mode="nearest")
        moved = np.where(mask_l, front[yi, sx_l], np.where(mask_r, front[yi, sx_r], 0))
        c = np.where(mask_l | mask_r, moved * shade * (1 - 0.25 * k), c)
        # 走っている揺れ
        dy = int(6 * np.sin(2 * np.pi * p * 4))                   # 走る上下動は1歩に1回：1.4秒で4歩（約 2.9 歩/秒。前は 1.4 歩/秒で歩きより遅かった）
        img = Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)).transform(   # 少し寄せてから揺らす（上下に黒い帯を出さない）
            size, Image.AFFINE, (0.98, 0, W * 0.01, 0, 0.98, H * 0.01 + dy * 0.98), Image.BILINEAR)
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
    """人影の立ち絵を強くぼかし、黒い人の形だけにする（顔も服もわからない。誰か特定の人物に見せない）。
    6枚とも同じ形にならないよう、元の立ち絵（4人）・大きさ（遠近）・傾き・半身だけ覗く、を変える。
    縁はむらのあるぼけで暗がりに溶かし、足もとに接地の影、上からの弱い光で頭と肩だけわずかに浮かせ、背景と同じ粒子を焼き込む"""
    from PIL import ImageFilter
    from scipy.ndimage import gaussian_filter
    from fxlib import grain_tex
    npc = ROOT / "build" / "ccfolia" / "npc"
    srcs = [Image.open(npc / f"npc_{n}.webp").getchannel("A") for n in ("figure", "neighbor", "woman", "lecturer")]
    # (元, 高さの割合＝遠近, 傾き, 左右反転, 見える幅の割合（半身だけ覗く）)
    plan = [(0, 0.95, 0.00, False, 1.0), (1, 0.78, -0.05, True, 1.0), (2, 0.88, 0.04, False, 0.55),
            (3, 0.66, 0.02, True, 1.0), (0, 1.00, -0.03, True, 0.6), (1, 0.58, 0.06, False, 1.0)]
    rg = np.random.default_rng(31)
    CW, CH = 200, 600                                               # パネルは 8×24 マス（1:3）
    out = []
    for k in range(count):
        si, hk, shear, flip, vis = plan[k % len(plan)]
        a = srcs[si]
        if flip:
            a = a.transpose(Image.FLIP_LEFT_RIGHT)
        h = int((CH - 40) * hk)
        a = a.resize((int(a.width * h / a.height), h), Image.LANCZOS)
        a = a.transform(a.size, Image.AFFINE, (1, shear, -shear * a.height * 0.5, 0, 1, 0), Image.BICUBIC)   # わずかに傾いて立つ
        canvas = Image.new("L", (CW, CH), 0)
        x = (CW - a.width) // 2 + int(rg.normal(0, 8))
        canvas.paste(a, (x, CH - 30 - h))
        m = np.asarray(canvas, np.float32) / 255
        if vis < 1:                                                 # 画面の端（柱の陰）から半身だけ覗く
            edge = CW * (1 - vis) if flip else CW * vis
            xx = np.arange(CW)[None, :]
            m = m * (smoothstep(edge - 12, edge + 12, xx) if flip else 1 - smoothstep(edge - 12, edge + 12, xx))
        nz = gaussian_filter(rg.random((CH, CW)), 7)
        nz = (nz - nz.min()) / (np.ptp(nz) + 1e-6)
        blur = 6 + 8 * (1 - hk)                                     # 遠いほどぼける（目の端なので、どれも輪郭は合わない）
        m = gaussian_filter(m, blur) * (0.75 + 0.5 * nz)
        m = np.clip(m * 1.4, 0, 1) * rg.uniform(0.62, 0.82) * (0.7 + 0.3 * hk)
        # 接地の影：足もとの横長のにじみ
        ys = np.where(m.max(1) > 0.1)[0]
        foot = ys.max() if len(ys) else CH - 30
        ao = np.zeros((CH, CW), np.float32)
        cols = np.where(m[max(0, foot - 20):foot].max(0) > 0.1)[0]
        if len(cols):
            ao[foot - 3:foot + 3, max(0, cols.min() - 14):cols.max() + 14] = 1
            ao = gaussian_filter(ao, (4, 10))
            ao = ao / (ao.max() + 1e-6) * 0.45 * hk
        alpha = np.clip(np.maximum(m, ao), 0, 1)
        # 色：ほとんど黒。上からの弱い光で、頭と肩の上の縁だけ暗い赤茶に。粒子は背景の絵と同じくらい
        top = np.clip(m - np.roll(m, 6, 0), 0, 1)
        col = np.array([12, 9, 8], np.float32) + np.array([46, 32, 24], np.float32) * np.clip(top * 3, 0, 1)[..., None]
        col = col * (1 + 0.15 * grain_tex(CH, CW, 310 + k)[..., None])
        im = np.dstack([np.clip(col, 0, 255), alpha * 255]).astype(np.uint8)
        img = Image.fromarray(im, "RGBA")
        img.save(OUT / "ep3" / f"31_edge_figure_{k + 1}.webp", quality=88)
        out.append(img)
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
    文字は HUD のように上に貼らず、合流地点の絵の「中」に置く：
      - 奥行き（Depth-Anything）で、奥の文字ほど小さく・ぼけ・霞み、手前の群衆の頭に隠れる
      - 文字の明るさは、その場所の絵の明るさで決まる（暗い水面では沈み、灯りの近くで浮く）。水面には揺れる映り込み
      - 重なるほど、白く飛ばずに墨のように濁って沈む（終わりは白飛びではなく、暗く埋まる）
    1コマで増える文字は、画面の1か所のまわりにまとめる（毎コマ画面全体が変わると、1回再生の素材が 20MB を超えるため）"""
    from scipy.ndimage import gaussian_filter
    from PIL import ImageFilter
    from fxlib import grain_tex, plate_depth
    W, H = 1280, 720
    plate_path = SCENES / "ep7_04_junction.jpg"
    plate = np.asarray(Image.open(plate_path).convert("RGB").resize((W, H)), np.float32) / 255
    D = plate_depth(plate_path)
    D = np.asarray(Image.fromarray(D).resize((W, H)), np.float32)
    light = gaussian_filter(plate.mean(-1), 18)
    light = light / (np.percentile(light, 99) + 1e-6)
    gr = grain_tex(H, W, 711)
    phrase = "「" + TXT["ep7_oiwai"] + "」"
    rg = np.random.default_rng(71)
    buf_c = np.zeros((H, W, 3), np.float32)                      # 文字の層（プリマルチ）
    buf_a = np.zeros((H, W), np.float32)
    ink = np.array(TEXT, np.float32) / 255

    def stamp(x, y, z, alpha):
        size = int(13 + 46 * z ** 1.3)
        f = font(size)
        tw = int(f.getlength(phrase)) + 8
        im = Image.new("L", (tw, size + 10), 0)
        ImageDraw.Draw(im).text((4, 2), phrase, font=f, fill=255)
        blur = 2.2 * (1 - z) ** 2 + 0.3                           # 被写界深度：奥ほどぼける
        m = np.asarray(im.filter(ImageFilter.GaussianBlur(blur)), np.float32) / 255
        refl = None
        if z < 0.75:                                              # 水面への映り込み：上下に裏返し、横に揺らし、薄く
            r = m[::-1]
            r = np.stack([np.roll(row, int(2.5 * np.sin(j * 0.9 + x))) for j, row in enumerate(r)])
            refl = gaussian_filter(r, (2.0, 0.8)) * 0.22
        for mm, yy0 in ((m, y),) + (((refl, y + m.shape[0] + 2),) if refl is not None else ()):
            x0, y0 = int(x), int(yy0)
            xs, ys = slice(max(0, x0), min(W, x0 + mm.shape[1])), slice(max(0, y0), min(H, y0 + mm.shape[0]))
            if xs.start >= xs.stop or ys.start >= ys.stop:
                continue
            mk = mm[ys.start - y0:ys.stop - y0, xs.start - x0:xs.stop - x0]
            occ = np.clip((z + 0.1 - D[ys, xs]) / 0.08, 0, 1)    # 手前の群衆・柱に隠れる
            a = mk * occ * alpha
            lit = np.clip(0.35 + 0.9 * light[ys, xs], 0.3, 1.1)[..., None]
            haze = (1 - z) * 0.45                                 # 空気遠近：奥ほど絵の色に寄る
            col = ink * lit * (1 - haze) + plate[ys, xs] * 1.3 * haze
            col = col * (1 - 0.45 * buf_a[ys, xs][..., None])     # 重なるほど濁って沈む（白飛びさせない）
            col = col * (1 + 0.08 * gr[ys, xs][..., None])
            buf_c[ys, xs] = col * a[..., None] + buf_c[ys, xs] * (1 - a[..., None])
            buf_a[ys, xs] = a + buf_a[ys, xs] * (1 - a)

    frames, placed, acc, t = [], 0, 0.0, 0
    total = 420
    while placed < total:
        rate = 0.12 * np.exp(t / 40)
        acc += rate * 2
        cx, cy = rg.uniform(0, W - 200), rg.uniform(0, H - 40)
        spread = 60 + 160 * min(1, placed / total)
        while acc >= 1 and placed < total:
            x = float(np.clip(cx + rg.normal(0, spread), -60, W - 120))
            y = float(np.clip(cy + rg.normal(0, spread * 0.5), -10, H - 30))
            z = float(np.clip(D[int(np.clip(y + 15, 0, H - 1)), int(np.clip(x + 60, 0, W - 1))] + rg.uniform(0.02, 0.25), 0, 1))
            stamp(x, y, z, rg.uniform(0.5, 0.95))
            placed += 1
            acc -= 1
        dim = 0.80 * min(1, (t // 6 + 1) / 5)                      # 背景を5段で沈める（黒ではなく、絵の暗部の色へ）
        a = buf_a + dim * (1 - buf_a)
        c = (buf_c + np.array(BLACK, np.float32) / 255 * dim * (1 - buf_a)[..., None]) / np.maximum(a, 1e-4)[..., None]
        frame = Image.fromarray(np.dstack([np.clip(c, 0, 1) * 255, a * 255]).astype(np.uint8), "RGBA")
        frames += [frame, frame]                                 # 1秒に15回だけ変える（同じコマが続くと容量をほとんど食わない）
        t += 2
    frames += [frames[-1]] * int(0.5 * FPS)
    save_webp_anim(frames, OUT / "ep7" / "71_oiwai_flood.webp", lossless=False, quality=80)   # 可逆だと 6MB。暗い地の文字なので非可逆でも崩れにくい
    return frames


def reward_mojibake():
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
    reward_mojibake()
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


def woman_ground(bg, m, shape, strength=1.0):
    """暗闇の女を床に「立たせる」：足もとの接地の影（AO）と、つやのある床に映る戸口の光の筋を、女の形が遮る。
    戻り値は床の上に重ねる黒の不透明度（H×W, 0..1）。女の形がほどければ、影と映り込みも一緒に薄れる"""
    from scipy.ndimage import gaussian_filter
    H, W = shape.shape
    ys, xs = np.where(m)
    y1 = ys.max()
    cols = np.where(shape.max(0) > 0.3)[0]
    if len(cols) == 0:
        return np.zeros((H, W), np.float32)
    floor = np.asarray(bg.convert("L"), np.float32) / 255
    # 映り込み：女の形を戸口の下端で上下に裏返し、縦に縮めてにじませる（床の光沢の分だけ）
    refl = np.zeros_like(shape)
    n = min(H - y1 - 1, y1)
    src = shape[y1 - n:y1][::-1]
    idx = (np.arange(n) * 1.6).astype(int)
    keep = idx < n
    refl[y1 + 1:y1 + 1 + keep.sum()] = src[idx[keep]]
    refl = gaussian_filter(refl, (5, 2)) * np.exp(-np.maximum(np.arange(H) - y1, 0) / 60)[:, None]
    lit = np.clip((floor - 0.05) * 8, 0, 1)                         # 床が光っているところほど、遮ったのがわかる
    # 接地の影：足もとの小さな楕円
    ao = np.zeros_like(shape)
    cx = (cols.min() + cols.max()) / 2
    ao[y1 - 2:y1 + 5, int(cx - (cols.max() - cols.min()) * 0.7):int(cx + (cols.max() - cols.min()) * 0.7)] = 1
    ao = gaussian_filter(ao, (3, 7))
    ao = ao / (ao.max() + 1e-6)
    cover = shape.sum() / max((shape > 0.5).sum(), 1)                # ほどけた分だけ薄く
    out = np.clip(refl * lit * 0.9 + ao * 0.55 * min(1, cover), 0, 1) * (1 - m) * strength
    return out.astype(np.float32)


def soft_matte(shape, seed=0):
    """切り抜きの硬い縁を、闇に溶ける縁に（ハーフマット）：縁だけ、むらのある幅でにじませる"""
    from scipy.ndimage import gaussian_filter
    H, W = shape.shape
    nz = gaussian_filter(np.random.default_rng(seed).random((H, W)), 2.5)
    nz = (nz - nz.min()) / (np.ptp(nz) + 1e-6)
    soft = gaussian_filter(shape, 1.8)
    return np.clip(np.maximum(shape * 0.0, soft) * (0.7 + 0.6 * nz), 0, 1) * np.clip(soft * 3, 0, 1)


def grain_title(title, seed=0):
    """題字にも背景と同じ粒子と、ごく軽いハレーション（明るい字の周りに赤茶のにじみ）を乗せる"""
    from PIL import ImageFilter
    from fxlib import grain_tex
    a = np.asarray(title, np.float32)
    g = grain_tex(a.shape[0], a.shape[1], seed)
    a[..., :3] = np.clip(a[..., :3] * (1 + 0.07 * g[..., None]), 0, 255)
    glow = np.asarray(title.getchannel("A").filter(ImageFilter.GaussianBlur(6)), np.float32) / 255
    hal = np.zeros_like(a)
    hal[..., :3] = (150, 70, 45)
    hal[..., 3] = glow * 70
    base = Image.fromarray(hal.astype(np.uint8), "RGBA")
    base.alpha_composite(Image.fromarray(a.astype(np.uint8), "RGBA"))
    return base


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
    shape = soft_matte(np.asarray(shape, np.float32) / 255, 91) * m
    ground = woman_ground(bg, m, shape)
    from fxlib import grain_tex
    # 濁った暗がり：ほんの少しだけ明るい赤茶。縦に流れるむらがあり、ゆっくり揺れる
    H, W = m.shape
    rg = np.random.default_rng(91)
    streak = np.asarray(Image.fromarray((rg.random((H // 24 + 1, W // 3 + 1)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC),
                        np.float32) / 255
    title = Image.open(ROOT / "build" / "ep9_title_still" / "f0000.png").convert("RGBA")
    tb = title.getbbox()
    title = grain_title(title.crop(tb), 913)
    tx = int((x0 + x1) / 2 - (tb[2] - tb[0]) / 2) - (tb[0] - int((x0 + x1) / 2 - (tb[2] - tb[0]) / 2)) * 0  # 戸口の真上にそろえる
    frames = []
    T = 9.0
    for i in range(int(T * FPS)):
        tt = (i - i % 2) / FPS                                    # 1秒に15回だけ変える（容量を5MB以内に）
        k = smoothstep(1.0, 5.5, tt)                              # 暗がりが浮かび上がる
        lum = (30 + 16 * streak + 5 * np.sin(2 * np.pi * (tt / 3.0) + streak * 6)) * k
        rgb = np.clip(lum[..., None] * lut()[np.clip(lum, 0, 255).astype(int)], 0, 255)
        alpha = m * (1 - shape) * k
        fl = ground * (np.round(k * 6) / 6)                                        # 床：女が戸口の光の映り込みを遮り、足もとが沈む
        im = np.zeros((H, W, 4), np.uint8)
        im[..., :3] = (rgb * m[..., None]).astype(np.uint8)       # 透明なところの色は 0 に（毎コマ変わる色が残ると 30MB になる）
        im[..., 3] = (np.maximum(alpha, fl) * 255).astype(np.uint8)
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
    """1コマ分の古いフィルム（960×720 の RGB と、そのコマの明るさ）：揺れ・ちらつき・縦の傷・塵・粒子・周辺の暗さ"""
    from PIL import ImageFilter
    W, H = size
    # フィルムの送りの揺れ（ゲートウィーブ）：毎コマ独立にがたがた跳ねず、ゆっくりうねる揺れに小さな跳ねが乗る。
    # 縦（送りの方向、つめとパーフォレーションの遊び）の方が横より大きい
    dx = 0.9 * np.sin(i * 0.31 + 1.1) + 0.5 * np.sin(i * 0.83) + rg.normal(0, 0.25)
    dy = 1.4 * np.sin(i * 0.23 + 0.4) + 0.8 * np.sin(i * 0.71 + 2.0) + rg.normal(0, 0.4)
    im = src.transform(size, Image.AFFINE, (1, 0, dx, 0, 1, dy), Image.BILINEAR)
    lum = np.asarray(im.convert("L"), np.float32)
    gain = 0.92 + 0.1 * rg.random()
    lum = lum * gain                                               # 明るさのちらつき
    lum += rg.normal(0, 9, (H, W))                                 # 粒子
    # 縦の傷（明るい細い線）：傷はフィルムの長さ方向に続いているので、同じ位置に何十コマも居続け、少しだけ横に揺れる
    # （毎コマ違う位置に出ると、傷ではなく雨のちらつきに見える）
    for j in range(2):
        seg = (i + j * 23) // 40
        srg = np.random.default_rng(9300 + seg * 2 + j)
        if srg.random() < 0.6:
            x = int(srg.integers(40, W - 40) + 3 * np.sin(i * 0.4 + j))
            if rg.random() < 0.85:                                     # ときどき途切れる
                lum[:, x:x + 2] += srg.uniform(30, 70)
    for _ in range(rg.integers(2, 7)):                             # 塵（黒い点やけば）
        x, y, r = rg.integers(0, W), rg.integers(0, H), rg.integers(2, 6)
        lum[max(0, y - r):y + r, max(0, x - r):x + r] *= 0.2
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    lum *= np.clip(1 - 0.7 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 2.2, 0.2, 1)
    lum = np.clip(lum * 0.85, 0, 255)
    rgb = np.clip(lum[..., None] * lut()[lum.astype(int)], 0, 255).astype(np.uint8)
    return Image.fromarray(rgb).filter(ImageFilter.GaussianBlur(0.6)), gain


def lifted(name, **kw):
    """暗すぎて暗いモニタで黒に潰れる背景（ロビー・ホール）の、暗部だけを持ち上げた版（scenes/〜_lift.jpg）。元の絵は上書きしない。
    ルームの背景もこちらに差し替える（add_set_pieces / add_scene_backgrounds。ファイル名はハッシュなので自動で新しくなる）"""
    from fxlib import lift_shadows
    src = SCENES / name
    dst = src.with_name(src.stem + "_lift.jpg")
    lift_shadows(Image.open(src).convert("RGB"), **kw).save(dst, quality=92)
    return dst


# ホールの絵（ep9_02_hall.jpg）のスクリーン：左上・右上・右下・左下。4:3 のフィルムは真ん中に映り、左右は暗いまま
HALL_SCREEN = [(476, 39), (804, 39), (803, 188), (477, 188)]


class Projection:
    """フィルムのコマを、ホールのスクリーンに映写したように前景へ置く。
    スクリーン（台形にコーナーピン）・映写光の円錐（塵の筋）・客席の頭に返る光を、フィルムの明るさに合わせて揺らす"""

    def __init__(self):
        from PIL import ImageFilter
        from fxlib import grain_tex
        hall = Image.open(lifted("ep9_02_hall.jpg", t=0.3, a=2.6))   # ホールはロビーより暗い（20/255 未満が 82%）ので強めに.convert("RGB").resize((1280, 720))
        self.plate = np.asarray(hall, np.float32) / 255
        lum = self.plate.mean(-1)
        (ax, ay), (bx, _), (cx, cy), _ = HALL_SCREEN
        scr = Image.new("L", (1280, 720), 0)
        ImageDraw.Draw(scr).polygon(HALL_SCREEN, fill=255)
        self.screen = np.asarray(scr.filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255
        gw = (cy - ay) * 4 / 3                                       # 4:3 のゲートの幅
        mx = (ax + bx) / 2
        self.gate = [(mx - gw / 2, ay + 1), (mx + gw / 2, ay + 1), (mx + gw / 2, cy - 1), (mx - gw / 2, cy - 1)]
        # 映写光：客席の後ろ上（画面の外）から、スクリーンのゲートへすぼまる光の筋。奥（スクリーン）に近いほど細く明るい
        yy, xx = np.mgrid[0:720, 0:1280].astype(np.float32)
        vx, vy = mx, -900.0                                          # 光の出どころ（画面の上の外、カメラの後ろ）を見かけ上ここに置く
        ang = np.arctan2(xx - vx, yy - vy)
        a0, a1 = np.arctan2(self.gate[0][0] - 60 - vx, cy - vy), np.arctan2(self.gate[1][0] + 60 - vx, cy - vy)
        inside = smoothstep(0, 0.02, ang - a0) * smoothstep(0, 0.02, a1 - ang) * (yy < cy)
        rays = np.interp(ang, np.linspace(a0, a1, 64), gaussian_noise_1d(64, 93)) ** 1.5 * 0.8 + 0.2
        self.beam = (inside * rays * (0.25 + 0.75 * (yy / cy) ** 2)).astype(np.float32)
        # 客席の頭の上の縁（明るい→暗いの境）に、スクリーンの光が返る。スクリーンから遠いほど弱い
        dist = np.hypot(xx - mx, (yy - cy) * 1.4)
        top_edge = np.clip(np.roll(lum, 2, 0) - lum, 0, 1) * 0 + np.clip(lum - np.roll(lum, 3, 0), 0, 1)
        self.bounce = (np.clip(top_edge * 6, 0, 1) * (yy > 230) * np.exp(-dist / 520)).astype(np.float32)
        self.spill = ((yy > 205) * np.exp(-dist / 380) * 0.5).astype(np.float32)
        self.grain = grain_tex(720, 1280, 931)
        self.warm = np.array([1.0, 0.86, 0.68], np.float32)

    def frame(self, film, gain, on=1.0):
        from fxlib import quad_warp
        rgba = np.asarray(quad_warp(film, self.gate, (1280, 720)), np.float32) / 255
        fa = rgba[..., 3:] * on
        scr_dark = self.plate * 0.22                                 # ゲートの外のスクリーンは光が来ない
        col = scr_dark * (1 - fa) + np.clip(rgba[..., :3] * 1.45 + 0.03, 0, 1) * fa   # 映写された画はスクリーンの地より明るい
        a = self.screen.copy()
        b = on                                                       # 円錐と返りの光は揺らさない（揺らすと毎コマ全面が変わり 20MB を超える）
        light = self.warm * b
        # 光の円錐（塵の中の光）と、客席の頭・床に返る光：前景の色を明るい暖色にし、不透明度で量を決める
        haze = self.beam * 0.30 * b
        hb = np.clip(self.bounce * 0.55 + self.spill * 0.12, 0, 1) * b
        rim = np.clip(self.plate * 1.9 + 0.08, 0, 1) * light
        col = np.where(a[..., None] > 0.01, col, rim * hb[..., None] / (hb[..., None] + haze[..., None] + 1e-6)
                       + (0.95 * light) * haze[..., None] / (hb[..., None] + haze[..., None] + 1e-6))
        alpha = np.maximum(a, np.clip(haze + hb, 0, 0.6) * (1 - a))
        col = col * (1 + 0.05 * self.grain[..., None])
        out = np.dstack([np.clip(col, 0, 1) * 255, alpha * 255]).astype(np.uint8)
        out[..., :3] = np.where(out[..., 3:] == 0, 0, out[..., :3])
        return Image.fromarray(out, "RGBA")


def gaussian_noise_1d(n, seed):
    from scipy.ndimage import gaussian_filter1d
    v = gaussian_filter1d(np.random.default_rng(seed).random(n * 2), 1.2, mode="wrap")[:n]
    return (v - v.min()) / (np.ptp(v) + 1e-6)


PUSH_FPS = 12                       # 寄りは動きがゆっくりでぶれがないので 12fps で足りる（容量を抑える）
PUSH_SIZE = (768, 432)  # 寄りきった後も 12fps で映し続けて 5MB 以下に収めるため 960×540 から下げた。            # 前景は全面・不透明。ホールの絵は 1280×720 しかないので、出力も小さめに


class PushCamera:
    """ホールの絵（映写の光込み）に、スクリーンへゆっくり寄るカメラ。奥行き（depth_map）で手前の客席ほど大きく
    拡大して画面の外へ流れ、スクリーンに対して動く（視差）。フィルムそのものは出力の解像度で直接スクリーンに貼るので、
    寄っても絵がぼけない"""

    def __init__(self, pj):
        from fxlib import DEPTH_ONNX, depth_map, grain_tex
        lit = pj.frame(Image.new("RGB", (960, 720), (0, 0, 0)), 0.0, 1.0)      # フィルムを抜いた、光だけのホール
        base = Image.alpha_composite(Image.fromarray((pj.plate * 255).astype(np.uint8)).convert("RGBA"), lit)
        self.lit = np.asarray(base.convert("RGB"), np.float32) / 255
        self.dark = self.lit * 0.0
        onnx = DEPTH_ONNX
        d = depth_map(Image.fromarray((pj.plate * 255).astype(np.uint8)), onnx)
        lo, hi = np.percentile(d, [2, 98])
        d = np.clip((d - lo) / (hi - lo + 1e-6), 0, 1)
        (ax, ay), (bx, _), (cx, cy), _ = HALL_SCREEN
        self.ds = float(np.median(d[ay:cy, ax:bx]))
        self.depth = d
        self.gate = pj.gate
        self.tgt = ((ax + bx) / 2, (ay + cy) / 2)
        self.k = PUSH_SIZE[0] / 1280
        self.grain = [grain_tex(PUSH_SIZE[1], PUSH_SIZE[0], 960 + j) for j in range(4)]

    def view(self, t):
        """t=0（引き）〜1（寄りきり）のカメラ：見る中心と、スクリーンの拡大率"""
        e = t * t * (3 - 2 * t)                                     # ゆっくり出て、ゆっくり止まる
        S = 4.3 ** e                                                # 寄りは等比（体感で一定の速さ）
        cxy = np.array([640, 360]) * (1 - e) + np.array(self.tgt) * e
        return S, cxy

    def warp(self, img, t):
        from scipy.ndimage import map_coordinates
        S, c = self.view(t)
        W, H = PUSH_SIZE
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        qx, qy = xx / self.k - 640, yy / self.k - 360
        s = np.full_like(qx, S)
        for _ in range(3):                                          # 逆写像：引いた先の奥行きで拡大率を決め直す
            sx, sy = c[0] + qx / s, c[1] + qy / s
            d = map_coordinates(self.depth, [sy, sx], order=1, mode="nearest")
            s = S ** (1 + 1.2 * np.clip(d - self.ds, 0, 1))         # 手前ほど速く大きくなる（ドリー）
        return np.dstack([map_coordinates(img[..., ch], [sy, sx], order=1, mode="nearest") for ch in range(3)])

    def gate_quad(self, t):
        S, c = self.view(t)
        return [(((x - c[0]) * S + 640) * self.k, ((y - c[1]) * S + 360) * self.k) for x, y in self.gate]

    def frame(self, t, film, on=1.0, i=0, hall=None):
        from fxlib import quad_warp
        bg = self.warp(self.lit if hall is None else hall, t) if hall is not False else self._bg
        rgba = np.asarray(quad_warp(film, self.gate_quad(t), PUSH_SIZE), np.float32) / 255
        fa = rgba[..., 3:] * on
        # 暗いホールでは、映写された画がいちばん明るいもの（以前の 1.45 倍だと 95% 点でも 59/255 で、暗いモニタでは客席と見分けにくかった）
        col = bg * (1 - fa) + np.clip(rgba[..., :3] * 1.85 + 0.03, 0, 1) * fa
        col = col * (1 + 0.05 * self.grain[i % 4][..., None])       # 粒子は4枚を回す（毎コマ全面を変えない）
        return Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8), "RGB").convert("RGBA")


def old_film():
    """上映中（1回再生：引きのホールからスクリーンへゆっくり寄り、寄りきったらフィルムを映し続ける）と、
    途切れる（1回再生：寄った画のまま、ちらつき → 振り返りはじめの2枚目 → 光が消えて真っ黒）の2つ。
    カメラが動くので前景は全面・不透明（背景のホールは隠れる）"""
    draft = not FILM[0].exists()
    if draft:                                                       # 絵が届くまでは、第五話の玄関で試す
        a = b = Image.open(SCENES / "ep5_02_entrance.jpg").convert("RGB")
    else:
        a, b = (Image.open(p).convert("RGB") for p in FILM)
    fit_ = lambda im: im.resize((int(im.width * 720 / im.height), 720), Image.LANCZOS).crop(
        ((int(im.width * 720 / im.height) - 960) // 2, 0, (int(im.width * 720 / im.height) - 960) // 2 + 960, 720))
    a, b = fit_(a), fit_(b)
    rg = np.random.default_rng(93)
    cam = PushCamera(Projection())
    F = PUSH_FPS
    n_push, n_hold = int(9 * F), int(22 * F)                        # 9秒で寄り、22秒映し続ける（台詞4行×4秒＋間）。最後のコマで止まる
    loop = [cam.frame(i / (n_push - 1), film_frame(a, i, rg)[0], i=i) for i in range(n_push)]
    cam._bg = cam.warp(cam.lit, 1.0)
    for i in range(n_hold):                                         # 映し続ける間も 12fps（以前は3コマずつ同じ画＝実質 4fps で、寄りの途中から急にカクついた）
        loop.append(cam.frame(1.0, film_frame(a, i, rg)[0], i=0, hall=False))   # ホールの粒子は止める（フィルムの粒子は毎コマ動く）。全面が毎コマ変わると 5MB を超える
    sfx = "_draft" if draft else ""
    save_webp_anim(loop, OUT / "ep9" / f"92_film_loop{sfx}.webp", fps=F, lossless=False, quality=30, loop=1)   # 12fps で映し続けても 5MB 未満に
    cut = []
    for i in range(int(1.2 * F)):                                   # ちらつきが強くなる
        f, g = film_frame(a, i, rg)
        cut.append(cam.frame(1.0, f, on=float(np.clip(1 - rg.random() * (0.2 + 0.6 * i / F), 0.15, 1)), i=i, hall=False))
    for i in range(int(0.8 * F)):                                   # 振り返りはじめる
        f, g = film_frame(b, i, rg)
        cut.append(cam.frame(1.0, f, on=float(np.clip(1 - rg.random() * 0.5, 0.3, 1)), i=i, hall=False))
    lit = cam._bg
    n_die = int(0.7 * F)
    for k in range(n_die):                                          # 光がすっと消えて、スクリーンもホールも黒に沈む
        o = (1 - (k + 1) / n_die) ** 2
        cam._bg = lit * (0.15 + 0.85 * o) * o ** 0.5
        cut.append(cam.frame(1.0, film_frame(b, k, rg)[0], on=o, i=k, hall=False))
    cut += [Image.new("RGBA", PUSH_SIZE, (0, 0, 0, 255))] * 3
    cam._bg = lit
    save_webp_anim(cut, OUT / "ep9" / f"93_film_cut{sfx}.webp", fps=F, lossless=False, quality=70, loop=1)
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
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(OUT / "ep9" / "94_projector_loop.mp3"), "-t", "14",
                    "-i", str(OUT / "ep9" / "95_projector_stop_then_silence.mp3"), "-filter_complex",
                    "[0:a]atrim=0:14[a];[1:a]atrim=0:4[b];[a][b]concat=n=2:v=0:a=1", str(t2)], check=True)
    preview(SCENES / "ep9_02_hall_lift.jpg", loop[:int(14 * PUSH_FPS)] + cut, t2, "ep9_old_film", fps=PUSH_FPS, tail=2)



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
    """最終話のロビー：照明が「ちか、ちか」と明滅する（前景、ループ）。暗くなる回数は1秒に3回まで。
    画面全体を一律に暗くせず、絵の中の灯り（シャンデリア・左右の燭台）ごとに別々に瞬かせる：
    消えた灯りの周り（その灯りが照らしていた壁・床）ほど暗く沈み、点いている灯りには光のにじみ（ブルーム）が乗る"""
    from scipy.ndimage import gaussian_filter
    W, H = 640, 360
    plate = np.asarray(Image.open(lifted("ep9_01_lobby.jpg")).convert("RGB").resize((W, H), Image.LANCZOS), np.float32) / 255
    lum = plate.mean(-1)
    core = np.clip((lum - np.percentile(lum, 99.3)) * 12, 0, 1)    # 灯りの芯（いちばん明るい点々）
    xx = np.arange(W)[None, :].repeat(H, 0) / W
    groups = [np.clip(1 - xx * 3, 0, 1), np.clip(1 - np.abs(xx - 0.5) * 4, 0, 1), np.clip(xx * 3 - 2, 0, 1)]   # 左・中央・右
    lit_maps, glow_maps = [], []
    for g in groups:
        c = core * g
        lit = gaussian_filter(c, 40) + gaussian_filter(c, 12) * 0.5    # その灯りが照らしていた範囲
        lit_maps.append(lit / (lit.max() + 1e-6))
        gl = gaussian_filter(c, 6)
        glow_maps.append(gl / (gl.max() + 1e-6))
    rg = np.random.default_rng(97)
    n = int(L * FPS)
    dims = []
    for gi in range(3):
        dim = np.zeros(n)
        f = int(rg.uniform(10, 30)) + gi * 7
        while f < n - 8:
            length = int(rg.integers(2, 6))
            depth = rg.uniform(0.45, 0.9)
            dim[f:f + length] = depth
            if rg.random() < 0.4:                                     # 点き直しに失敗して、もう一度
                dim[f + length + 1:f + length + 3] = depth * 0.8
            f += int(rg.uniform(0.6, 2.8) * FPS) + (int(rg.uniform(0, 1.5) * FPS) if gi != 1 else 0)
        dims.append(dim)
    for k in range(n):                                               # シャンデリアが落ちると、左右も少し引きずられる（同じ回路）
        dims[0][k] = max(dims[0][k], dims[1][k] * 0.4)
        dims[2][k] = max(dims[2][k], dims[1][k] * 0.4)
    # 白熱電球はフィラメントの熱で光が遅れる：一瞬で消えず数十ミリ秒かけて沈み、点き直しも立ち上がりに1〜2コマかかる。
    # ループの継ぎ目でも熱が続くよう、2周つないで後ろの1周を使う
    from fxlib import filament_color, filament_lag
    dims = [filament_lag(np.concatenate([d, d]), FPS)[n:] for d in dims]
    cache, frames = {}, []
    for k in range(n):
        key = tuple(round(d[k] * 20) / 20 for d in dims)
        if key not in cache:
            dark = np.zeros((H, W), np.float32)
            glow = np.zeros((H, W), np.float32)
            gcol = np.zeros((H, W, 3), np.float32)
            for dv, lit, gl in zip(key, lit_maps, glow_maps):
                dark = 1 - (1 - dark) * (1 - dv * (0.25 + 0.7 * np.sqrt(lit)))   # 消えた灯りが照らしていた所ほど暗い
                g = (1 - dv) * gl * 0.45                                 # 点いている灯りのにじみ
                gcol = np.where((g > glow)[..., None], filament_color(1 - dv), gcol)   # 落ちかけの灯りは赤く（色温度が下がる）
                glow = np.maximum(glow, g)
            dark = dark * (1 - glow)
            a = dark + glow
            col = (np.array(BLACK, np.float32) * dark[..., None] + gcol * glow[..., None]) / np.maximum(a, 1e-4)[..., None]
            im = np.dstack([np.clip(col, 0, 255), np.clip(a, 0, 1) * 255]).astype(np.uint8)
            cache[key] = Image.fromarray(im, "RGBA")
        frames.append(cache[key])
    save_webp_anim(frames, OUT / "ep9" / "98_lobby_flicker_loop.webp", lossless=False, quality=85, loop=0)
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
        return np.asarray(s, np.float32) / 255

    noise = np.asarray(Image.fromarray((np.random.default_rng(92).random((H // 10, W // 3)) * 255).astype(np.uint8)).resize(
        (W, H), Image.BICUBIC), np.float32) / 255
    sfx = "_draft" if draft else ""

    from fxlib import grain_tex
    rgb = np.clip(rgb * (1 + 0.12 * grain_tex(H, W, 912)[..., None]), 0, 255)

    def save(shape, name, ground=1.0):
        shape = soft_matte(shape, 91) * m
        fl = woman_ground(bg, m, shape, ground)
        a = (np.maximum(m * (1 - shape), fl) * 255).astype(np.uint8)
        im = np.zeros((H, W, 4), np.uint8)
        im[..., :3] = (rgb * m[..., None]).astype(np.uint8)
        im[..., 3] = a
        Image.fromarray(im, "RGBA").save(OUT / "ep9" / f"99_proof_{name}{sfx}.webp", lossless=True)

    full = shape_at(1.0)
    inside = distance_transform_edt(full > 0.5)                     # 輪郭からの距離（内側ほど大きい）
    inside = inside / (inside.max() + 1e-6)
    # 段階ごとに、残る量をはっきり変える：0＝全身、1＝輪郭から 1/3 ほど欠けて穴が開く、2＝芯の切れ端だけ、3＝何もない
    for k, depth in enumerate((0, 0.45, 0.9)):
        if depth == 0:
            s = full
        else:
            # 輪郭の近くから、むらのある形で欠けていく（糸がほどけるように、縦に流れるむら）
            erode = (inside < depth * (0.4 + 1.2 * noise)) & (full > 0)
            s = full * (1 - erode) * (0.8 if k == 2 else 1.0)
        save(s, str(k))
    save(np.zeros_like(full), "3")
    save(shape_at(1.12), "reach", ground=1.35)                      # 近づく：大きく、足もとの影も濃く
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
        a = a.point(lambda v, o=0.78 - 0.3 * k: int(min(255, v * 1.3) * o))
        # 空気遠近：奥ほど雨の夜の霞の色（暗い赤茶の灰）に寄る。手前は黒に近く、上の縁だけ街灯でわずかに光る
        haze = np.array([12, 9, 9], np.float32) * (1 - k) + np.array([78, 62, 54], np.float32) * k
        am = np.asarray(a, np.float32) / 255
        rim = np.clip(am - np.roll(am, 5, 0), 0, 1)[..., None] * np.array([60, 44, 34], np.float32) * (1 - k)
        col = np.clip(haze + rim, 0, 255)
        layer = Image.fromarray(np.dstack([np.broadcast_to(col, am.shape + (3,)), am * 255]).astype(np.uint8), "RGBA")
        x = int(W * (0.92 - 0.82 * k) - a.width / 2 + rg.normal(0, 12))
        y = int(H - h - k * H * 0.28)
        if x + a.width > 0:
            # 濡れた路面への映り込み：上下に裏返し、縦ににじませ、薄く
            rf = layer.transpose(Image.FLIP_TOP_BOTTOM).resize((a.width, max(1, int(h * 0.35))), Image.LANCZOS)
            rf = rf.filter(ImageFilter.GaussianBlur(3 + 4 * k))
            rf.putalpha(rf.getchannel("A").point(lambda v: int(v * 0.28)))
            img.alpha_composite(rf, (x, min(H - 1, y + h)))
            img.alpha_composite(layer, (x, y))
    # 雨：細い斜めの筋（行列の手前を落ちる）と、全体の粒子
    from fxlib import grain_tex
    arr = np.asarray(img, np.float32)
    streak = np.zeros((H, W), np.float32)
    for _ in range(900):
        x0, y0, ln = rg.uniform(0, W), rg.uniform(0, H), rg.uniform(10, 26)
        for j in range(int(ln)):
            yy, xx = int(y0 + j), int(x0 + j * 0.18)
            if 0 <= yy < H and 0 <= xx < W:
                streak[yy, xx] = max(streak[yy, xx], 0.35 * (1 - j / ln))
    al = arr[..., 3] / 255
    rain_a = streak * 0.6
    a2 = rain_a + al * (1 - rain_a)
    c = (np.array([170, 150, 135], np.float32) * rain_a[..., None] + arr[..., :3] * (al * (1 - rain_a))[..., None]) / np.maximum(a2, 1e-4)[..., None]
    c = c * (1 + 0.12 * grain_tex(H, W, 733)[..., None])
    img = Image.fromarray(np.dstack([np.clip(c, 0, 255), a2 * 255]).astype(np.uint8), "RGBA")
    img.save(OUT / "ep7" / "73_queue_panel.webp", quality=90)
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
BALCONY_ARCH = ROOT / "assets" / "ep8_balcony_3.png"                    # 4枚目（03_fall_1）：反らせて後ろへ倒れはじめる姿。あれば落ちる所を見せずカーテンで隠す
BALCONY = [ROOT / "assets" / f"ep8_balcony_{k}.png" for k in range(3)]   # 届いたらここに置く（0=人なし、1=手を振る、2=のけぞる）
WINDOW_DRAFT = (205, 30, 505, 445)                                     # 窓の範囲（仮：家具のない部屋の構図）
WINDOW_REAL = (130, 40, 495, 425)                                      # 窓の範囲（届いたベランダの絵。1280×720 で測った）
ARM_REAL = (307, 259, 298, 262, 238, 296, 240)                          # 手を振る腕：x<307・y<259 が肘から先（二の腕・肩は入れない）、肘 (298,262)、y<238 が手で手首 (296,240)
FALL_PX = 560                                                          # 落ちる間に重心が下がる量（px）
RAIL_REAL, FLOOR_REAL = 312, 425                                       # 届いた絵の手すりの上端と、ベランダの床の線（ここより下に落ちると見えない）
WINDOW = WINDOW_REAL if all(p.exists() for p in BALCONY) else WINDOW_DRAFT


def toned(src, bright=False):
    """届いた絵を、部屋と同じ赤茶にそろえる（make_scene_bg と同じ物差し）。
    bright=True（ベランダ）：明るさは沈めず元の絵の分布を保つ（窓は白く飛ばし、女の影が黒く浮く）。色味だけ赤茶に寄せる。
    いまの assets は finish_images で暗い部屋の参考に寄せてあるので、窓のハイライトが 245 になるよう、4枚に同じ伸ばしをかける"""
    from PIL import ImageOps
    img = ImageOps.fit(Image.open(src).convert("RGB"), (1280, 720), Image.LANCZOS)
    a = np.asarray(img).astype(np.float32)
    if bright:
        ref = np.asarray(ImageOps.fit(Image.open(BALCONY[0]).convert("RGB"), (1280, 720)), np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
        top = max(float(np.percentile(ref, 99.5)), 1.0)
        lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
        lum = 245 * np.clip(lum / top, 0, 1.05) ** 0.8 if top < 230 else lum
        c = lut()[np.clip(lum, 0, 255).astype(int)]
        c = c / np.maximum(c @ np.array([0.299, 0.587, 0.114], np.float32), 1e-4)[..., None]   # 色味だけ（明るさは変えない）
        hi = smoothstep(200, 250, lum)[..., None]                                                # 白い窓は、ほとんど白のまま
        c = c * (1 - 0.7 * hi) + 0.7 * hi
        return np.clip(lum[..., None] * c, 0, 255).astype(np.uint8)
    lum = (a @ np.array([0.299, 0.587, 0.114], np.float32)) / 255 * 236 + 6
    yy, xx = np.mgrid[0:720, 0:1280].astype(np.float32)
    lum = lum * 0.62 * np.clip(1 - 0.55 * (((xx - 640) / 760) ** 2 + ((yy - 340) / 470) ** 2), 0.35, 1)
    return np.clip(lum[..., None] * lut()[np.clip(lum, 0, 255).astype(int)], 0, 255).astype(np.uint8)


def balcony_inputs():
    """本番は届いた3枚。届くまでは、家具のない部屋の窓の向こうに、女の立ち絵の影を置いた仮の3枚で動きを作る"""
    if all(p.exists() for p in BALCONY):
        return [toned(p, bright=True) for p in BALCONY], False
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


def figure_mask(base, other, region=None, thr=22):
    """2枚の差から、女の形だけを取り出す（いちばん大きくつながった部分）。region=(x0, y0, x1, y1) の外は見ない"""
    from scipy.ndimage import binary_closing, binary_opening, label
    from scipy.ndimage import binary_fill_holes, gaussian_filter
    d = gaussian_filter(np.abs(other.astype(np.float32) - base.astype(np.float32)).mean(-1), 1.5)
    dark = gaussian_filter(other.astype(np.float32).mean(-1), 1.0) < base.astype(np.float32).mean(-1) * 0.8   # 女は逆光で、元の絵より暗い（粒子や揺れたカーテンの差を拾わない）
    if region is not None:
        r = np.zeros(d.shape, bool)
        r[region[1]:region[3], region[0]:region[2]] = True
        dark &= r
    m = binary_fill_holes(binary_opening(binary_closing((d > thr) & dark, iterations=2), iterations=2))
    lab, n = label(m)
    if n == 0:
        raise SystemExit("女の形が見つからない（3枚の構図がずれていないか確認）")
    keep = lab == (np.argmax(np.bincount(lab.ravel())[1:]) + 1)
    return keep


class FallingWoman:
    """窓の向こうで、のけぞって手すりの向こうへ落ちる女（逆光の影）を、背景の絵になじませて描く。
    切り抜きを貼った感じ（平らな黒・四角い縁）を消すために:
      - 形の縁はやわらかく（2枚の差のマスクをぼかしたマット）
      - 色は窓枠のいちばん暗いところにそろえ（黒の高さを絵と同じに）、縁には明るい窓の光を回り込ませる（ライトラップ）
      - 落ちる間は1コマの中で何回か描いて平均する（モーションブラー）
      - 絵と同じ強さの粒子を、毎コマ変えて乗せる
    返すのは 1280×720 の (RGB 0..255, アルファ 0..1) の float の組。透明なところの色は 0"""

    def __init__(self, e, a, b, ma, mb, rail, floor=None, real=False, arch=None):
        from scipy.ndimage import gaussian_filter
        self.gf = gaussian_filter
        x0, y0, x1, y1 = WINDOW
        pad = 60
        self.real = real                                                        # 届いた絵：手を振る → 身を乗り出す（2枚目の姿勢）→ 前へ落ちる
        self.floor = floor if floor is not None else rail                       # ここより下に落ちた体は見えない
        bottom = max(int(np.where(ma | mb)[0].max()), self.floor) + 6
        self.box = (max(0, x0 - pad), max(0, y0 - pad), min(1280, x1 + pad), min(720, bottom))
        bx0, by0, bx1, by1 = self.box
        ef = e.astype(np.float32)
        win = ef[y0:rail, x0:x1].reshape(-1, 3)
        lum = win.mean(-1)
        self.black = np.median(win[lum <= np.percentile(lum, 3)], 0)            # 窓枠の暗さ＝この絵の黒
        if real:                                                                # 明るく保った絵では窓枠も明るいので、逆光の影はほぼ黒に（白い窓にくっきり浮く）
            self.black = np.minimum(self.black, np.array([14, 9, 7], np.float32))
        self.light = gaussian_filter(ef[by0:by1, bx0:bx1], (9, 9, 0))           # 回り込ませる窓の光
        hp = ef[y0:rail, x0:x1].mean(-1) - gaussian_filter(ef[y0:rail, x0:x1].mean(-1), 1.5)
        self.grain = float(np.clip(np.std(hp), 1.2, 6.0))                       # 絵の粒子の強さ
        self.rail = rail
        self.sprites = {}
        for key, img, m in (("stand", a, ma), ("lean", b, mb)):
            ys, xs = np.where(m)
            alpha = gaussian_filter(m.astype(np.float32), 1.1)                  # やわらかい縁
            col = img.astype(np.float32)
            # 逆光：絵の中の女の色を暗く沈め、黒の高さにそろえる（届いた絵の服のしわなどはわずかに残る）
            col = self.black + (col - self.black).clip(0, None) * 0.18
            pre = np.dstack([col * alpha[..., None], alpha])[by0:by1, bx0:bx1]
            self.sprites[key] = (pre, (xs.mean() - bx0, ys.max() - by0), ys.max() - ys.min())
            row = np.where(m[rail])[0]                                          # 手すりにもたれる接点（腰）：手すりの行での体の真ん中
            hip_x = row.mean() if len(row) else xs.mean()
            self.hip = getattr(self, "hip", {})
            self.hip[key] = np.array([rail - by0, hip_x - bx0], np.float64)
            self.com = getattr(self, "com", {})
            self.com[key] = np.array([ys.mean() - by0, xs.mean() - bx0], np.float64)   # 重心
        if arch is not None:                                                    # 反らせて後ろへ倒れはじめる姿（03_fall_1）。足もとは同じ床
            img, m = arch
            alpha = gaussian_filter(m.astype(np.float32), 1.1)
            col = self.black + (img.astype(np.float32) - self.black).clip(0, None) * 0.18
            self.sprites["arch"] = (np.dstack([col * alpha[..., None], alpha])[by0:by1, bx0:bx1], None, None)
            # 手前を横切るカーテン：絵の左のカーテンの布目（縦のひだ）を写し取り、窓の光で透かす
            cr = ef[100:470, 485:775]
            lum = cr.mean(-1)
            ca = smoothstep(np.percentile(lum, 25), np.percentile(lum, 80), gaussian_filter(lum, 1.0))   # 布のところだけ（後ろの暗い壁は抜く）
            hh, ww = ca.shape
            yy_, xx_ = np.mgrid[0:hh, 0:ww]
            wav = 25 * np.sin(yy_ / 31.0) + 12 * np.sin(yy_ / 9.0 + 1)           # 切り取った縁が直線にならないよう、波打たせてぼかす
            ca *= smoothstep(0, 110, xx_ + wav - 20) * smoothstep(ww, ww - 60, xx_ - wav) * smoothstep(0, 40, yy_ + wav) * smoothstep(hh, hh - 50, yy_)
            self.cloth_a = np.clip(ca * 1.15, 0, 0.97).astype(np.float32)
            self.cloth_rgb = np.clip(cr * 1.35 + 6, 0, 255).astype(np.float32)   # 窓の光を受けて、壁の前より少し明るく
        if real:                                                                # 手を振る腕：肘から先だけを切り分けて、肘を支点に振る
            pre = self.sprites["stand"][0]
            ax, ay, ex, ey, hy, wx, wy = ARM_REAL
            yy, xx = np.mgrid[0:pre.shape[0], 0:pre.shape[1]]
            arm = (smoothstep(ax - bx0 + 2, ax - bx0 - 2, xx) * smoothstep(ay - by0 + 2, ay - by0 - 2, yy))[..., None]
            hand = arm * smoothstep(hy - by0 + 2, hy - by0 - 2, yy)[..., None]
            self.arm = (pre * (arm - hand), pre * hand, pre * (1 - arm),
                        np.array([ey - by0, ex - bx0], np.float64), np.array([wy - by0, wx - bx0], np.float64))
        self.rg = np.random.default_rng(84)

    @staticmethod
    def _xform(pre, ang, pivot, d):
        """pivot (y, x) を中心に ang 度回し、d (y, x) ずらす（負の角度で、左にあるものが下がる＝反時計回り）"""
        from scipy.ndimage import affine_transform
        th = np.deg2rad(ang)
        c, s = np.cos(th), np.sin(th)
        R = np.array([[c, -s], [s, c]])                                           # 出力 (y, x) → 入力 (y, x)
        off = pivot - R @ (pivot + np.asarray(d, np.float64))
        return np.dstack([affine_transform(pre[..., k], R, offset=off, order=1, mode="constant") for k in range(4)])

    @staticmethod
    def _yscale(pre, sy, y0):
        """y0 の行を中心に縦だけ sy 倍（負なら上下が返る）。横は動かさない"""
        from scipy.ndimage import affine_transform
        if abs(sy) < 0.02:
            return np.zeros_like(pre)
        M = np.array([[1 / sy, 0], [0, 1]])
        off = np.array([y0 - y0 / sy, 0])
        return np.dstack([affine_transform(pre[..., k], M, offset=off, order=1, mode="constant") for k in range(4)])

    def _clip(self, out, clip):
        if clip is not None:
            yy = np.arange(self.box[1], self.box[3])[:, None, None]
            out = out * np.clip((clip - yy) / 2.0, 0, 1)
        return out

    def _pre(self, p):
        """届いた絵の動きの部品（手を振る・もたれかかる・落ちる）を、前乗算 RGBA にする"""
        kind, v, dx, clip = p[1], p[2], p[3], p[4]
        if kind == "wave":                                                      # v = (腕の角度, 体の傾き)
            fore, hand, body, elbow, wrist = self.arm                           # 肩・二の腕・体は動かさない。肘から先だけを回し、手首は少し遅れて振れる
            th = np.deg2rad(v[0])
            w2 = elbow + np.array([[np.cos(th), np.sin(th)], [-np.sin(th), np.cos(th)]]) @ (wrist - elbow)   # 回したあとの手首の位置
            arm = self._xform(fore, v[0], elbow, (0, 0)) + self._xform(self._xform(hand, v[0], elbow, (0, 0)), v[1], w2, (0, 0))
            return self._xform(body + arm, 0, elbow, (0, dx))
        if kind == "arch":                                                      # v = 0..1：立ち姿 → 反らせた姿へ、形だけを短く移す（位置は動かさない）
            m = v
            A = self.sprites["stand"][0]
            B = self.sprites["arch"][0]
            if not hasattr(self, "_sdf"):                                       # 輪郭の符号付き距離（内側が負）。距離どうしを混ぜると形がなめらかに移る
                from scipy.ndimage import distance_transform_edt as edt
                sd = lambda q: edt(q[..., 3] <= 0.5) - edt(q[..., 3] > 0.5)
                self._sdf = (sd(A), sd(B))
            d = (1 - m) * self._sdf[0] + m * self._sdf[1]
            al = self.gf(np.clip(0.5 - d, 0, 1), 0.9)
            col = (A[..., :3] * (1 - m) + B[..., :3] * m) / np.maximum(A[..., 3:] * (1 - m) + B[..., 3:] * m, 1e-4)
            return self._xform(np.dstack([col * al[..., None], al]), 0, self.hip["stand"], (0, dx))
        if kind == "back":                                                      # v = (構え 0..1, 落ちる 0..1)：画面の中では回さない。カメラから遠ざかる向きに倒れるので、縦に縮める
            pre_k, k = v
            st = self.sprites["stand"][0]
            fore, hand, body, elbow, wrist = self.arm
            pv = self.hip["stand"]
            yy = np.arange(st.shape[0])[:, None, None]
            up = smoothstep(pv[0] + 3, pv[0] - 3, yy)                           # 腰（手すりの高さ）から上
            u = min(1.0, k / 0.55) ** 1.6                                       # はじめはゆっくり
            su = (1 - 0.08 * pre_k) * (1 - 0.45 * u)                            # 上半身：奥へ倒れて縮みながら、
            upper = self._xform(self._yscale(st * up, su, pv[0]), 0, pv, ((pv[0] - self.com["stand"][0]) * 0 + 125 * u, 0))
            upper = upper * smoothstep(pv[0] + 2, pv[0] - 2, yy)                # 手すりの線より下（向こう側）へ沈んで消える
            g = smoothstep(0.22, 0.6, k)
            sl = 1 - 1.4 * g                                                    # 脚：足先が床から浮き、腰を支点に手すりの上へ（負＝足先が上）
            legs = self._yscale(st * (1 - up), sl, pv[0])
            if sl < 0:
                legs = legs * smoothstep(pv[0] + 2, pv[0] - 2, yy)              # 越えた脚は手すりより上だけ見える
            drop = FALL_PX * (max(0.0, k - 0.68) / 0.32) ** 2                    # 最後に、残った脚の影がまっすぐ下へ重力で抜ける
            out = self._xform(upper + legs, 0, pv, (drop, dx))
            return self._clip(out, clip)
        if kind == "morph":                                                     # v = 0..1：腰を支点に前へ傾けながら、立ち姿 → 身を乗り出す姿へ
            tilt, m = smoothstep(0, 0.7, v), smoothstep(0.45, 1, v)            # 先に体ごと傾け、後半で形を移す
            st = self.sprites["stand"][0]                                       # 足は床に固定：腰（手すりの高さ）から上だけを前へ折る
            yy = np.arange(st.shape[0])[:, None, None]
            up = smoothstep(self.hip["stand"][0] + 4, self.hip["stand"][0] - 4, yy)
            A = st * (1 - up) + self._xform(st * up, -34 * tilt, self.hip["stand"], (0, 0))
            A = self._xform(A, 0, self.hip["stand"], (0, dx))
            B = self._xform(self.sprites["lean"][0], 22 * (1 - tilt), self.hip["lean"], (0, dx))
            am = (1 - m) * self.gf(A[..., 3], 3) + m * self.gf(B[..., 3], 3)
            al = self.gf(np.clip((am - 0.5) * 9 + 0.5, 0, 1), 0.8)            # 2つの形の間をなめらかにつなぐ（重ね焼きにしない）
            col = (A[..., :3] * (1 - m) + B[..., :3] * m) / np.maximum(A[..., 3:] * (1 - m) + B[..., 3:] * m, 1e-4)
            return np.dstack([col * al[..., None], al])
        if kind == "fall":                                                      # v = 0..1：手すりを支点に上半身が向こうへ下がり、脚が遅れて手すりを越え、逆さの縦向きで落ちる
            k = v
            pre, pv = self.sprites["lean"][0], self.hip["lean"]
            yy = np.arange(pre.shape[0])[:, None, None]
            leg = smoothstep(pv[0] + 2, pv[0] + 10, yy)                         # 手すりより下＝脚
            torso = self._xform(pre * (1 - leg), -90 * smoothstep(0, 0.4, k), pv, (0, 0))
            legs = self._xform(pre * leg, -180 * smoothstep(0.08, 0.55, k), pv, (0, 0))
            out = torso + legs
            a = out[..., 3]
            cy = (a.sum(1) * np.arange(a.shape[0])).sum() / max(a.sum(), 1e-3)
            drop = 30 * k + FALL_PX * (max(0.0, k - 0.45) / 0.55) ** 2         # 回りきるまではほとんど沈まず、そこから重力で加速
            dy = self.com["lean"][0] + drop - cy                                 # 重心は下へだけ動く（脚が上がっても体は浮かない）
            return self._clip(self._xform(out, 0, pv, (dy, dx)), clip)
        raise ValueError(kind)

    def _place(self, key, ang, dx, dy, clip=None):
        """手すりの高さを中心に ang 度傾け、(dx, dy) ずらした前乗算 RGBA。clip より下は見えない（ベランダの床の向こう）"""
        from scipy.ndimage import affine_transform
        pre, (cx, fy), h = self.sprites[key]
        py = min(fy, self.rail - self.box[1])
        th = np.deg2rad(ang)
        c, s = np.cos(th), np.sin(th)
        R = np.array([[c, -s], [s, c]])                                           # 出力 (y, x) → 入力 (y, x)
        ctr = np.array([py, cx])
        off = ctr - R @ (ctr + np.array([dy, dx]))
        out = np.dstack([affine_transform(pre[..., k], R, offset=off, order=1, mode="constant") for k in range(4)])
        if clip is not None:
            yy = np.arange(self.box[1], self.box[3])[:, None, None]
            out *= np.clip((clip - yy) / 2.0, 0, 1)
        return out

    def render(self, poses):
        """poses: 1コマの中の (key, ang, dx, dy) の並び（複数ならモーションブラー）。None は誰もいない"""
        bx0, by0, bx1, by1 = self.box
        acc = np.zeros((by1 - by0, bx1 - bx0, 4), np.float32)
        poses = [p for p in poses if p is not None]
        if not poses:
            return None
        for p in poses:
            acc += self._pre(p) if p[0] == "real" else self._place(*p)
        acc /= len(poses)
        al = acc[..., 3]
        col = acc[..., :3] / np.maximum(acc[..., 3:], 1e-4)
        # ライトラップ：縁ほど窓の光が回り込む
        inner = self.gf(al, 2.2)
        wrap = np.clip(al - inner, 0, 1) * 2.2 + (1 - np.clip(al, 0, 1)) * 0.0
        wrap = np.clip(wrap, 0, 0.75)[..., None]
        col = col * (1 - wrap) + self.light * wrap
        col = col + self.rg.normal(0, self.grain, col.shape[:2])[..., None]     # 絵と同じ粒子（明るさだけ）
        rgb = np.zeros((720, 1280, 3), np.float32)
        a = np.zeros((720, 1280), np.float32)
        a[by0:by1, bx0:bx1] = np.clip(al, 0, 1)
        rgb[by0:by1, bx0:bx1] = np.clip(col, 0, 255)
        a[a < 1 / 255] = 0
        rgb[a == 0] = 0
        return rgb, a

    def pose(self, t, ev):
        """1回の「立つ → のけぞる → 落ちる」。ev = (立ち始め, のけぞり始め, 落ち始め, 消える, のけぞる角度, 横のずれ)"""
        ts, tl, tf, te, ang, dx = ev
        h = self.sprites["stand"][2]
        if t < ts or t >= te:
            return None
        if self.real:
            if t < tl:                                                            # 肘から先を左右に振り、体もわずかに揺れる
                ph = 2 * np.pi * 1.4 * (t - ts)
                return ("real", "wave", (12 * np.sin(ph), 6 * np.sin(ph - 0.9)), dx, None)
            if t < tf:                                                            # 手が止まり、わずかに後ろへ重心を移す（上半身がほんの少し縮む）
                k = smoothstep(0, 1, (t - tl) / (tf - tl))
                return ("real", "back", (k, 0.0), dx, None)
            k = (t - tf) / (te - tf)                                              # 腰壁（ベランダの床の線）より下は隠す
            return ("real", "back", (1.0, k), dx, self.floor)
        if t < tl:
            return ("stand", 0.0, dx + np.sin(t * 2.3) * 0.6, 0.0, self.rail)
        if t < tf:
            k = smoothstep(0, 1, (t - tl) / (tf - tl))
            return ("stand", -ang * 0.5 * k, dx, -h * 0.04 * k, self.rail)    # 重心を後ろへ（わずかに伸び上がる）
        k = (t - tf) / (te - tf)
        return ("stand", -ang * 0.5 - 3 * k, dx, h * (-0.04 + 0.05 * k + 1.5 * k * k), self.rail)   # 重心が手すりを越えたら、まっすぐ下へ加速して手すりの陰に消える

    def curtain(self, p, t):
        """暴れるカーテンが窓を右から左へ横切る（p = 0..1）。絵の右のカーテン（はためいている本物の布）を写し取り、
        大きく手前へ引き伸ばして波打たせる。2枚重ねて、真ん中では女を隠す。返すのは全画面の (色, アルファ, 布の真ん中の x)"""
        from scipy.ndimage import map_coordinates
        x0, y0, x1, _ = WINDOW
        src, sa = self.cloth_rgb, self.cloth_a
        h, w = sa.shape
        q = smoothstep(0, 1, p)
        rgb = np.zeros((720, 1280, 3), np.float32)
        a = np.zeros((720, 1280), np.float32)
        yy, xx = np.mgrid[0:720, 0:1280].astype(np.float32)
        acc_a = np.zeros((720, 1280), np.float32)
        acc_c = np.zeros((720, 1280, 3), np.float32)
        cx_main = None
        for off, sc, dens, ph in ((150, 1.25, 0.75, 2.0), (0, 1.55, 1.0, 0.0)):
            cx = (x1 + 260) - q * ((x1 + 260) - (x0 - 330)) + off * (1 - q)
            if cx_main is None or off == 0:
                cx_main = cx
            sx, sy = sc * 1.25, sc * 1.05
            top = 20 - 30 * sc + 30
            # 出力の画素 → 布の画素（横の波打ちと、裾ほど遅れるはためき）
            v = (yy - top) / sy
            bow = 80 * np.sin(np.pi * q) * np.clip(v / h, 0, 1) ** 1.5
            u = (xx - cx + bow + 20 * np.sin(yy / 61 + 6.5 * t + ph) + 8 * np.sin(yy / 19 - 9 * t + ph)) / sx + w / 2
            v = v + 6 * np.sin(xx / 47 + 5 * t + ph)
            al = map_coordinates(sa, [v, u], order=1, mode="constant", cval=0) * dens
            col = np.dstack([map_coordinates(src[..., k], [v, u], order=1, mode="constant", cval=0) for k in range(3)])
            acc_c = col * al[..., None] + acc_c * (1 - al[..., None])
            acc_a = al + acc_a * (1 - al)
        rgb = acc_c / np.maximum(acc_a[..., None], 1e-4)
        a = acc_a
        a[a < 1 / 255] = 0                                                      # 粒子は写し取った布目に元から入っている（足すと容量が膨らむ）
        rgb[a == 0] = 0
        return np.clip(rgb, 0, 255), a, cx_main

    def frame_real(self, t, events):
        """届いた絵：手を振る（肘から先）→ 一瞬止まる → 反らせた姿へ移る → カーテンが横切って隠す → いない。落ちる所は見せない。
        ev = (立ち始め, 手を止める, カーテンが来る, カーテンが去る, -, 横のずれ)"""
        rgb = np.zeros((720, 1280, 3), np.float32)
        a = np.zeros((720, 1280), np.float32)
        curt = []
        for ts, tl, tc, te, _, dx in events:
            if not ts <= t < te:
                continue
            p = (t - tc) / (te - tc) if t >= tc else -1
            fade = 1.0
            if p >= 0:
                cr, ca, cx = self.curtain(p, t)
                curt.append((cr, ca))
                wx = self.hip["stand"][1] + self.box[0]
                fade = float(np.clip((cx - (wx - 60)) / 120, 0, 1))             # 布が女の前を通る間に消え、過ぎたらもういない
                if fade <= 0:
                    continue
            if t < tl:
                ph = 2 * np.pi * 1.4 * (t - ts)
                pose = ("real", "wave", (12 * np.sin(ph), 6 * np.sin(ph - 0.9)), dx, None)
            elif t < tl + 0.15:
                pose = ("real", "wave", (0.0, 0.0), dx, None)                   # 一瞬止まる
            else:
                pose = ("real", "arch", smoothstep(0, 1, (t - tl - 0.15) / 0.4), dx, None)
            w = self.render([pose])
            if w is not None:
                wr, wa = w
                wa = wa * fade
                na = wa + a * (1 - wa)
                rgb = (wr * wa[..., None] + rgb * (a * (1 - wa))[..., None]) / np.maximum(na[..., None], 1e-4)
                a = na
        for cr, ca in curt:                                                     # カーテンは女より手前
            na = ca + a * (1 - ca)
            rgb = (cr * ca[..., None] + rgb * (a * (1 - ca))[..., None]) / np.maximum(na[..., None], 1e-4)
            a = na
        if not a.any():
            return None
        rgb[a == 0] = 0
        return rgb, a

    def frame(self, t, events, shutter=1 / 40, n=7):
        """時刻 t のコマ。落ちている間だけ、シャッターの開いている間を n 回描いて平均する"""
        if self.real and "arch" in self.sprites:
            return self.frame_real(t, events)
        poses = []
        for ev in events:
            moving = ev[2] <= t < ev[3]
            ts = [t - shutter * j / (n - 1) for j in range(n)] if moving else [t]   # 過去側だけを重ねる：落ちる体の上に、髪と服がなびくような尾が残る
            ps = [self.pose(u, ev) for u in ts]
            if any(p is not None for p in ps):
                if moving:
                    ps = [p for p in ps if p is not None]   # 消えた瞬間は画面の外へ
                poses.append(ps)
        if not poses:
            return None
        outs = [self.render(ps) for ps in poses]
        outs = [o for o in outs if o is not None]
        if not outs:
            return None
        rgb, a = outs[0]
        for r2, a2 in outs[1:]:                                                   # 重なった回は、手前から上に重ねる
            rgb = r2 * a2[..., None] + rgb * (1 - a2[..., None]) * (a[..., None] > 0)
            na = a2 + a * (1 - a2)
            rgb = np.where(na[..., None] > 0, rgb / np.maximum(na[..., None], 1e-4) * 1.0, 0)
            a = na
        return rgb, a


# ---------------------------------------------------------------- 第八話：カーテン（絵の布をそのまま動かす）と、まっすぐ落ちる女
# カーテンの動きは Blender の布シミュレーション（tools/curtain_sim_blender.py：上辺をレールに固定した 1.4×2.3m の薄布に、
# 外から部屋の中へ 4 秒周期の突風）で確かめた数値に合わせる：
#   ・振れ幅は高さ h（0=レール, 1=裾）の h^1.25 に比例（シミュレーション 0.055/0.111/0.192/0.307m @ h=.25/.5/.75/1）
#   ・平均のふくらみは h について上に凸（0.25/0.39/0.48/0.51m）：上の方がすぐ部屋側へ出て、裾は寝る
#   ・突風に対する遅れ：レール近く 1.33s → 裾 2.0s（レール→裾へ 約0.7s で伝わる。2.3m なら 約3m/s）
#   ・裾は布が寄って幅が 1.4 → 約1.0m に狭まる
# 絵の中では「部屋の中へ」ふくらむ向き＝カメラ側なので、画面では布の流れる向き（左は右下、右は右）への伸びと持ち上がりとして見える
CURTAIN_GUST = 4.6                                                     # 突風の周期（秒）。ループ 9.2 秒にちょうど 2 回
CURTAIN_LAG = 0.7                                                      # レール→裾へ突風が伝わる時間（秒）
CURTAINS = (                                                           # (布の範囲, レールの線（2点）, 裾までの長さ px, 突風で動く向き, 振れ幅 px)
    ([(0, 0), (125, 0), (150, 190), (260, 360), (420, 500), (400, 560), (0, 560)], ((0, 0), (115, 0)), 530, (1.0, -0.45), 26),
    ([(405, 95), (615, 150), (960, 110), (975, 470), (425, 470)], ((418, 115), (612, 172)), 520, (0.35, -1.0), 24),
)


def curtain_gust(t):
    """突風の強さ 0..1（速く立ち上がり、ゆっくり抜ける）。CURTAIN_GUST 秒ごとに繰り返す"""
    ph = ((t - 1.45) % CURTAIN_GUST) / CURTAIN_GUST                    # 2.6 秒あたり（女が反る所）で最も強い
    return float(np.where(ph < 0.25, np.sin(ph / 0.25 * np.pi / 2) ** 2, np.exp(-(ph - 0.25) * 5.0)))


class CurtainPlate:
    """背景の絵（カーテンの画素ごと）を、カーテンの範囲だけゆがめて動かす。布を別に貼らない"""

    def __init__(self, e):
        from scipy.ndimage import gaussian_filter
        self.e = e.astype(np.float32)
        yy, xx = np.mgrid[0:720, 0:1280].astype(np.float32)
        self.yy, self.xx = yy, xx
        self.parts = []
        for poly, (p0, p1), length, dirv, amp in CURTAINS:
            m = Image.new("L", (1280, 720), 0)
            ImageDraw.Draw(m).polygon(poly, fill=255)
            m = gaussian_filter(np.asarray(m, np.float32) / 255, 18)
            ax, ay = np.subtract(p1, p0)                                  # レールからの距離＝高さ h（レールの線への垂直距離）
            nx, ny = -ay, ax
            nn = np.hypot(nx, ny)
            nx, ny = nx / nn, ny / nn
            if ny < 0:
                nx, ny = -nx, -ny
            dist = (xx - p0[0]) * nx + (yy - p0[1]) * ny
            if length == 520:                                             # 右：レールから右へ流れている布なので、流れの向きの距離
                dist = np.hypot(xx - (p0[0] + p1[0]) / 2, (yy - (p0[1] + p1[1]) / 2) * 0.6)
            h = np.clip(dist / length, 0, 1)
            d = np.array(dirv, np.float32)
            d /= np.linalg.norm(d)
            self.parts.append((m, h, d, amp))

    def field(self, t):
        """時刻 t の変位（dy, dx）"""
        dy = np.zeros((720, 1280), np.float32)
        dx = np.zeros((720, 1280), np.float32)
        for m, h, d, amp in self.parts:
            hw = h ** 1.25
            g = np.zeros_like(h)
            for k in range(6):                                            # 高さごとに遅れた突風（6 段で補間）
                hk = k / 5
                w = np.clip(1 - np.abs(h - hk) * 5, 0, 1)
                g += w * (curtain_gust(t - CURTAIN_LAG * hk) - 0.4)
            ph = 2 * np.pi * (0.8 * t - 0.8 * CURTAIN_LAG * h)            # 小さなさざ波：レールから裾へ伝わる
            rip = 0.28 * np.sin(ph) + 0.12 * np.sin(2.1 * ph + 1.3 + self.xx / 90)
            s = m * hw * amp * (g + rip)
            dx += s * d[0] + m * hw * amp * 0.18 * np.sin(ph + 0.8) * -d[1]
            dy += s * d[1] + m * hw * amp * 0.18 * np.sin(ph + 0.8) * d[0]
        return dy, dx

    def warp(self, img, t):
        """img（H×W×3 float）のカーテンの所を、時刻 t の形にゆがめる"""
        from scipy.ndimage import map_coordinates
        dy, dx = self.field(t)
        sy, sx = self.yy - dy, self.xx - dx
        return np.dstack([map_coordinates(img[..., k], [sy, sx], order=1, mode="nearest") for k in range(3)])


RAIL_BASE = 428                                                        # 手すりの下端（ベランダの床の縁）。落ちた体はここより下は見えない
DROP_T = 0.36                                                          # 消えるまでの時間（秒）


def drop_layer(fw, t, events, shutter=1 / 50, n=6):
    """手を振る → 一瞬止まる → 反らせた姿へ（重心は上げない）→ まっすぐ下へ重力で落ちて手すりの下に消える。
    ev = (立ち始め, 手を止める, 落ち始め, 横のずれ)。落ちる間は回さない・手足も動かさない（縦のモーションブラーと、遠ざかるぶんわずかに縮むだけ）。
    重なった回（何度も）は、新しい回を手前に。返すのは全画面の (色, アルファ) か None"""
    from scipy.ndimage import affine_transform
    bx0, by0, bx1, by1 = fw.box
    rgb = np.zeros((720, 1280, 3), np.float32)
    a = np.zeros((720, 1280), np.float32)
    A = fw.sprites["arch"][0]
    al = A[..., 3]
    ys, xs = np.where(al > 0.5)
    ctr = np.array([ys.mean(), xs.mean()])
    span = RAIL_BASE - by0 - ys.min() + 10                                 # 腕の先まで手すりの下へ抜ける距離
    acc_g = 2 * span / DROP_T ** 2
    yb = np.arange(by0, by1)[:, None, None]
    for ts, tl, tf, dx in events:
        if not ts <= t < tf + DROP_T:
            continue
        if t < tf:
            if t < tl:
                ph = 2 * np.pi * 1.4 * (t - ts)
                pose = ("real", "wave", (12 * np.sin(ph), 6 * np.sin(ph - 0.9)), dx, None)
            elif t < tl + 0.15:
                pose = ("real", "wave", (0.0, 0.0), dx, None)             # 一瞬止まる
            else:
                pose = ("real", "arch", smoothstep(0, 1, (t - tl - 0.15) / max(tf - tl - 0.15, 1e-3)), dx, None)
            pre = fw._pre(pose)
        else:
            pre = np.zeros_like(A)
            for j in range(n):                                            # シャッターの開いている間を重ねる（縦のブレ）
                u = max(0.0, t - tf - shutter * j / (n - 1))
                drop = 0.5 * acc_g * u * u
                s = 1 - 0.08 * u / DROP_T                                 # 遠ざかるぶん、わずかに縮む
                M = np.array([[1 / s, 0], [0, 1 / s]])
                off = ctr - M @ (ctr + np.array([drop, dx]))
                pre += np.dstack([affine_transform(A[..., k], M, offset=off, order=1, mode="constant") for k in range(4)])
            pre /= n
            pre = pre * np.clip((RAIL_BASE - yb) / 2.0, 0, 1)            # 手すりの下（ベランダの床の向こう）は見えない
        al2 = np.clip(pre[..., 3], 0, 1)
        col = pre[..., :3] / np.maximum(pre[..., 3:], 1e-4)
        inner = fw.gf(al2, 2.2)                                           # ライトラップ（render と同じ）
        wrap = np.clip(np.clip(al2 - inner, 0, 1) * 2.2, 0, 0.75)[..., None]
        col = col * (1 - wrap) + fw.light * wrap
        wa = np.zeros((720, 1280), np.float32)
        wr = np.zeros((720, 1280, 3), np.float32)
        wa[by0:by1, bx0:bx1] = al2
        wr[by0:by1, bx0:bx1] = col
        na = wa + a * (1 - wa)
        rgb = (wr * wa[..., None] + rgb * (a * (1 - wa))[..., None]) / np.maximum(na[..., None], 1e-4)
        a = na
    if not a.any():
        return None
    return rgb, a


def over(base, layer):
    """base（H×W×3 float）に (色, アルファ) を重ねる"""
    if layer is None:
        return base
    r, a = layer
    return r * a[..., None] + base * (1 - a[..., None])


class BalconyMosaic:
    """窓の外の白いモザイク（1秒に10回変える）"""

    def __init__(self, e, outside, seed=86):
        self.e, self.outside, self.rg, self.cur = e, outside, np.random.default_rng(seed), None

    def step(self):
        blk = int(self.rg.uniform(14, 30))
        sx = int(self.rg.normal(0, 6))
        src = np.roll(self.e, sx, axis=1).astype(np.float32)
        small = Image.fromarray(src.astype(np.uint8)).resize((1280 // blk, 720 // blk), Image.BILINEAR)
        big = np.asarray(small.resize((1280, 720), Image.NEAREST)).astype(np.float32) * 0.55 + 235 * 0.45
        self.cur = (np.clip(big * lut()[np.clip(big.mean(-1), 0, 255).astype(int)] / np.maximum(lut()[200], 1e-3) * 0.97, 0, 255),
                    self.outside * 0.7)
        return self.cur


def balcony_woman():
    """ベランダの3枚（届くまでは仮の3枚）から、落ちる女と手すりの高さ・窓の外のマスクを用意する"""
    (e, a, b), draft = balcony_inputs()
    reg = (WINDOW[0] - 40, 0, WINDOW[2] + 40, 462) if not draft else None    # 明るく伸ばした絵では、ドアやカーテンの差も拾うので窓のまわりだけ
    thr = 22 if draft else 45
    ma, mb = figure_mask(e, a, reg, thr), figure_mask(e, b, reg, thr)
    x0, y0, x1, y1 = WINDOW
    if not draft:
        arch = None
        if BALCONY_ARCH.exists():
            f = toned(BALCONY_ARCH, bright=True)
            from scipy.ndimage import binary_closing, binary_fill_holes
            mk = figure_mask(e, f, reg, thr)
            ys, xs = np.where(mk)
            fl, el = f.astype(np.float32).mean(-1), e.astype(np.float32).mean(-1)
            box = np.zeros_like(mk)
            box[ys.min():ys.max() + 1, xs.min():xs.max() + 1] = True
            mk = mk | (box & (fl < 22) & (el > 35))                             # 手すりに重なって差が出にくい頭・胴も拾う
            arch = (f, binary_fill_holes(binary_closing(mk, iterations=3)))
        return finish_woman(FallingWoman(e, a, b, ma, mb, RAIL_REAL, FLOOR_REAL, real=True, arch=arch), e, draft)
    # 手すりの高さ：窓の高さの 45〜80% の範囲で、横に強い線がいちばん目立つ行（窓の下枠を拾わないように範囲を絞る）
    g = np.abs(np.diff(e[y0:y1, x0:x1].astype(np.float32).mean(-1), axis=0)).mean(1)
    lo, hi = int(len(g) * 0.45), int(len(g) * 0.8)
    rail = y0 + lo + int(np.argmax(g[lo:hi]))
    fw = FallingWoman(e, a, b, ma, mb, rail)
    return finish_woman(fw, e, draft)


def finish_woman(fw, e, draft):
    """窓の外（白くぼやけるところ）のマスクを添える。明るいところだけを、やわらかい縁で（四角く見えないよう、窓の縁に向かって薄くする）"""
    from PIL import ImageFilter
    x0, y0, x1, y1 = WINDOW
    rail = fw.rail
    lum = e.astype(np.float32).mean(-1)
    outside = np.zeros(lum.shape, np.float32)
    ref = lum[y0:rail, x0:x1]
    outside[y0:rail, x0:x1] = smoothstep(np.percentile(ref, 40), np.percentile(ref, 75), ref)
    yy, xx = np.mgrid[0:720, 0:1280].astype(np.float32)
    edge = np.minimum.reduce([xx - x0, x1 - xx, yy - y0, rail - yy])
    outside *= smoothstep(0, 28, edge)
    outside = np.asarray(Image.fromarray((outside * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)), np.float32) / 255
    return fw, e, outside, draft


def balcony_loop():
    """ベランダ（全面の前景、ループ 9.2 秒）：手を振る → 一瞬止まる → 反らせた姿 → まっすぐ落ちて消える → 誰もいない窓（カーテンは息をし続ける）
    → 下をのぞきこみたくなるように、窓へゆっくり寄る → 寄りきった所から、立っている女のいる引きの画へ溶けて戻る。
    音（別のカットイン）との合わせ：消える瞬間 BALCONY_GONE 秒で風を切り、そこから 1.0〜1.5 秒あとに遠く下で重い音"""
    from fxlib import parallax_frame, plate_depth
    fw, e, outside, draft = balcony_woman()
    fps, L = FPS, 9.2
    n_fr = int(round(L * fps))
    ev = [(0.0, 2.2, 2.75, 0)]
    cp = CurtainPlate(e)
    mos = BalconyMosaic(e, outside)
    depth = plate_depth(BALCONY[0])
    push0, push1, fade0 = 5.6, 8.6, 8.6
    frames = []
    for i in range(n_fr):
        tt = i / fps
        if i % 3 == 0:
            mos.step()
        mr, ma = mos.cur
        base = over(e.astype(np.float32), (mr, ma))
        img = over(cp.warp(base, tt), drop_layer(fw, tt, ev))
        if tt >= push0:
            k = smoothstep(push0, push1 + 0.6, tt)
            img = parallax_frame(img, depth, k, push=0.22, drift=(0.0, 0.0), near_gain=0.8,
                                 center=(330, 300 + 70 * k))
            if tt >= fade0:                                            # 溶けて引きの画（立っている女）へ戻る＝ループの継ぎ目
                q = smoothstep(fade0, L, tt)
                wide = over(cp.warp(base, tt), drop_layer(fw, 0.0, ev))
                img = img * (1 - q) + wide * q
        frames.append(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA"))
    sfx = "_draft" if draft else ""
    small = [f.resize((960, 540), Image.LANCZOS) for f in frames]          # 全面が動くので 960×540 で書き出して 5MB に収める
    save_webp_anim(small, OUT / "ep8" / f"86_balcony_loop{sfx}.webp", lossless=False, quality=55, loop=0)
    Image.fromarray(e).save(OUT / "ep8" / f"86_balcony_bg{sfx}.jpg", quality=88)
    return frames, OUT / "ep8" / f"86_balcony_bg{sfx}.jpg"


BALCONY_GONE = 2.75 + DROP_T                                               # ベランダのループで女が手すりの下へ消えきる時刻（秒）


def paste_clip(dst, im, x, y):
    """画面の外にはみ出す位置にも重ねる（alpha_composite は負の位置を受け付けない）"""
    cx, cy = max(0, -x), max(0, -y)
    if cx >= im.width or cy >= im.height or x >= dst.width or y >= dst.height:
        return
    im = im.crop((cx, cy, im.width, im.height))
    if im.width and im.height:
        dst.alpha_composite(im, (x + cx, y + cy))


def to_rgba(rgb, a):
    """float の (色, アルファ 0..1) を、透明なところの色が 0 の RGBA に"""
    a8 = np.clip(np.round(a * 255), 0, 255).astype(np.uint8)
    out = np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), a8])
    out[a8 == 0, :3] = 0
    return Image.fromarray(out, "RGBA")


def balcony():
    fr, bg = balcony_loop()
    write_mp3(OUT / "preview" / "silence.mp3", silence(13))
    preview(bg, fr * 2, OUT / "preview" / "silence.mp3", "ep8_balcony_loop", tail=0)
    ep8_nandomo()                                                  # 「何度も」の窓の向こうも同じ絵から作るので、いっしょに作り直す





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
    if not draft:
        # 本番の絵は頭ごと向きが変わるので、差分は頭全体になる。その中で「明るい白目に囲まれた暗い瞳」を DoG で2つ探す
        from scipy.ndimage import gaussian_filter
        lb = b.astype(np.float32).mean(-1)
        dog = gaussian_filter(lb, 10) - gaussian_filter(lb, 3)
        region = binary_dilation(diff, iterations=20)
        cand = (dog > np.percentile(dog[region], 99.6)) & region
        lab2, n2 = label(cand)
        pts = [(int((lab2 == i).sum()), *np.argwhere(lab2 == i).mean(0)) for i in range(1, n2 + 1)]
        pairs = [(p1[0] + p2[0], p1, p2) for p1 in pts for p2 in pts
                 if p1[2] < p2[2] and abs(p1[1] - p2[1]) < 45 and 70 < p2[2] - p1[2] < 260]
        if pairs:
            _, p1, p2 = max(pairs)
            yy, xx = np.mgrid[0:lb.shape[0], 0:lb.shape[1]]
            r = (p2[2] - p1[2]) * 0.17                                 # 目の大きさは目の間隔から
            eyes = ((yy - p1[1]) ** 2 + (xx - p1[2]) ** 2 < r * r) | ((yy - p2[1]) ** 2 + (xx - p2[2]) ** 2 < r * r)
        eyes = binary_dilation(eyes, iterations=4)
    else:
        eyes = binary_dilation(eyes, iterations=10)
    glow = np.asarray(Image.fromarray((eyes * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(8)), np.float32) / 255
    fps = FPS
    rg = np.random.default_rng(77)
    frames = []
    from scipy.ndimage import gaussian_filter
    from fxlib import grain_tex
    gr = grain_tex(720, 1280, 771)[..., None]
    bloom_k = np.asarray(Image.fromarray((glow * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(28)), np.float32)[..., None] / 255

    def dark_of(img):
        """黒で潰さない暗部：絵そのものを深く沈め（暗部のディテールと粒子を残す）、茶のグレードに寄せる"""
        x = img.astype(np.float32)
        x = x * 0.16 + np.array(BLACK, np.float32) * 2.5
        x = x * (1 + 0.18 * gr)                                      # 暗部にも粒子（他の場面の絵と同じ紙）
        return x

    darks = {}

    def frame(img, eye_gain, light, shift=(0, 0)):
        key = id(img)
        if key not in darks:
            darks[key] = dark_of(img)
        dark = darks[key]
        src = np.roll(np.roll(img.astype(np.float32), shift[1], 0), shift[0], 1) if shift != (0, 0) else img.astype(np.float32)
        g = np.roll(np.roll(glow, shift[1], 0), shift[0], 1)[..., None] if shift != (0, 0) else glow[..., None]
        e = src * g * eye_gain
        bl = (np.roll(np.roll(bloom_k, shift[1], 0), shift[0], 1) if shift != (0, 0) else bloom_k) * eye_gain
        full = img.astype(np.float32) * light
        out = np.maximum(dark * (1 - light) + full, e)
        out = out + bl * np.array([120, 85, 60], np.float32) * (1 - light)   # 目の光が、まわりの顔（頬・くちばし）にかすかに回る
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
        # 背景（同じ絵）の上の「沈んだ層」を透かしていく：最後は透明になり、背景の絵そのものが見える
        # （不透明な全面のコマで浮かばせると、非可逆の差分が積もって最後のコマが崩れていた）
        if b.shape[:2] == (720, 1280):
            fr_ = np.asarray(frame(b, 1.0, 0.0)).copy()
            fr_[..., 3] = int(round(255 * (1 - k * k)))
            frames.append(Image.fromarray(fr_, "RGBA"))
        else:
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


# ================================================================ 終わりの三つ（エンドB・座席のスマホ・AF のカード）
# エンドB の最後の一行（本文 L3411 付近）。ファミレスの左の窓（明るいガラスのところ）だけに、
# ベランダの「のけぞる女」の形を、一瞬だけ上から下へ通す（1回再生の前景。最後のコマは透明）。
# 女の形はベランダと同じ材料（balcony_inputs）から取るので、ベランダの絵が届くまでは _draft、届けば本番に替わる
ENDB_GLASS = (0, 0, 430, 262)                                      # ファミレスの左の窓の範囲（ep6_01_restaurant.jpg）


def endb_fall():
    """ベランダと同じ物理：反らせた姿（回さない・手足も動かさない）が、ガラスの外をまっすぐ重力で一瞬落ちる。縦のブレと、わずかな縮み"""
    from PIL import ImageFilter
    from scipy.ndimage import binary_closing, binary_fill_holes, shift
    (e, _, _), draft = balcony_inputs()
    if BALCONY_ARCH.exists():
        f = toned(BALCONY_ARCH, bright=True)
        mk = binary_fill_holes(binary_closing(figure_mask(e, f), iterations=3))
    else:
        f = balcony_inputs()[0][2]
        mk = figure_mask(e, f)
    ys, xs = np.where(mk)
    fig = Image.fromarray(np.dstack([np.broadcast_to(np.array([22, 15, 11], np.uint8), f.shape),         # 逆光の影（ほぼ黒）
                                     (mk * 255).astype(np.uint8)]), "RGBA").crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    h = 230
    fig = fig.resize((int(fig.width * h / fig.height), h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.8))
    rest = np.asarray(Image.open(SCENES / "ep6_01_restaurant.jpg").convert("L").resize((1280, 720)), np.float32)
    x0, y0, x1, y1 = ENDB_GLASS
    glass = np.zeros((720, 1280), np.float32)
    glass[y0:y1, x0:x1] = smoothstep(115, 150, rest[y0:y1, x0:x1])      # 明るいガラスだけ（窓枠・植木・人の頭は残す）
    glass = np.asarray(Image.fromarray((glass * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 255
    pre, post = int(0.4 * FPS), int(0.6 * FPS)
    T = 0.36                                                            # 窓の上から下まで（ベランダの DROP_T と同じ）
    y_start, y_end = -h - 40, y1 + 10                                   # 上から入ってきて、すでに速い（上の階から落ちてきた）
    v0 = 0.6 * (y_end - y_start) / T                                     # y = y_start + v0 t + a t²/2
    acc = 2 * ((y_end - y_start) - v0 * T) / T ** 2
    fall = int(round(T * FPS)) + 1
    frames = []
    for i in range(pre + fall + post):
        u = (i - pre) / FPS
        if 0 <= u <= T + 1e-6:
            acc_a = np.zeros((720, 1280, 4), np.float32)
            n = 6
            for j in range(n):                                          # シャッターの間を重ねる＝縦のブレ
                uu = max(0.0, u - j / n / 50)
                s = 1 - 0.06 * uu / T
                im = fig.resize((max(1, int(fig.width * s)), max(1, int(h * s))), Image.BILINEAR)
                lay = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
                paste_clip(lay, im, 80, int(y_start + v0 * uu + 0.5 * acc * uu * uu))
                a = np.asarray(lay, np.float32)
                a[..., :3] *= a[..., 3:] / 255
                acc_a += a
            acc_a /= n
            al = acc_a[..., 3] * glass
            col = np.where(acc_a[..., 3:] > 0, acc_a[..., :3] / np.maximum(acc_a[..., 3:], 1e-4) * 255, 0)
            fr = Image.fromarray(np.dstack([np.clip(col, 0, 255), np.clip(al, 0, 255)]).astype(np.uint8), "RGBA")
        else:
            fr = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
        frames.append(clean_alpha(fr))
    sfx = "_draft" if draft else ""
    path = OUT / "ep9" / f"89_endb_fall{sfx}.webp"
    save_webp_anim(frames, path, lossless=True, loop=1)
    return frames


def clean_alpha(img):
    """透明なところの色を 0 にする（ココフォリアで縁ににじまないように）"""
    a = np.asarray(img).copy()
    a[a[..., 3] == 0, :3] = 0
    return Image.fromarray(a, "RGBA")


def seat_phone():
    """最終話：座席に置かれた、第七話で盗られたスマホ（本文 L3027）。
    画面は第七話の朝のニュースのまま。時刻は出さず、画面は少し暗い"""
    W, H = 360, 700
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, W - 1, H - 1], 44, fill=(14, 11, 10, 255), outline=(60, 50, 46, 255), width=3)
    d.rounded_rectangle([14, 14, W - 15, H - 15], 34, fill=(18, 14, 13, 255))
    f1, f2 = font(17), font(12)
    d.text((34, 70), "ニュース", font=font(20), fill=QUIET + (255,))
    y = 120
    for i, s in enumerate(TXT["ep7_phone_news"]):
        d.line([(30, y - 12), (W - 30, y - 12)], fill=(40, 33, 31, 255), width=1)
        assert draw_text(None, (0, 0), s, f1, None) < W - 68, s
        draw_text(d, (34, y), s, f1, (QUIET if "失踪" in s else QUIETEST) + (255,))
        d.text((34, y + 30), TXT["phone_cats"]["ep7_phone_news"][i], font=f2, fill=QUIETEST + (255,))
        y += 82
    img = clean_alpha(img)
    img.save(OUT / "ep9" / "88_seat_phone.webp", lossless=True, exact=True)
    return img


def af_card(W=900):
    """最終話：AF《とある化身の知識》のカード（KP シート L344〜）。報酬の札と同じ紙。各話で決まる所は af_fill から埋め、
    空なら下線の空欄にして KP が読み上げる"""
    import re
    c, fill = TXT["af_card"], TXT.get("af_fill", {})
    f0, f1, f2 = font(26), font(25), font(22)
    lh, ml = int(f1.size * 1.75), W - 150

    def tokens(s):
        for part in re.split(r"(\{\w+\})", s):
            if part.startswith("{"):
                v = fill.get(part[1:-1], "")
                yield ("blank", "　" * 5) if not v else ("text", v)
            else:
                yield from (("text", ch) for ch in part)

    def layout(s, f):
        lines, cur, x = [], [], 0
        for kind, t in tokens(s):
            units = [t] if kind == "blank" else list(t)
            for u in units:
                w = f.getlength(u) + (0 if kind == "blank" else f.size * 0.04)
                if x + w > ml and not (kind == "text" and u in "。、」）"):
                    lines.append(cur); cur, x = [], 0
                cur.append((kind, u, w)); x += w
        lines.append(cur)
        return lines

    paras = [layout(s, f1) for s in c["body"]]
    rews = [layout(s, f2) for s in c["rewards"]]
    h = 120 + sum(len(p) * lh + 18 for p in paras) + 30 + sum(len(r) * int(f2.size * 1.6) for r in rews) + 60
    img, pad = card_paper(W, h, 909)
    d = ImageDraw.Draw(img)
    tw = draw_text(None, (0, 0), c["title"], f0, None, spacing=0.12)
    draw_text(d, (pad + (W - tw) / 2, pad + 44), c["title"], f0, TEXT + (255,), spacing=0.12)
    y = pad + 120

    def put(lines, f, step, color):
        nonlocal y
        for ln in lines:
            x = pad + 75
            for kind, u, w in ln:
                if kind == "blank":
                    d.line([(x + 4, y + f.size * 1.15), (x + w - 4, y + f.size * 1.15)], fill=QUIETEST + (255,), width=2)
                else:
                    d.text((x, y), u, font=f, fill=color + (255,))
                x += w
            y += step

    for p in paras:
        put(p, f1, lh, TEXT)
        y += 18
    y += 30
    for r in rews:
        put(r, f2, int(f2.size * 1.6), QUIET)
    img = clean_alpha(img)
    img.save(OUT / "ep9" / "87_af_card.webp", lossless=True, exact=True)
    return img


def finale():
    (OUT / "ep9").mkdir(parents=True, exist_ok=True)
    endb_fall()
    seat_phone()
    af_card()


PIECES = {"finale": finale, "presence": presence, "vulture": vulture, "balcony": balcony, "ambience": ambience, "moving": moving, "seats": ep9_seats, "props": props, "reward": rewards, "ep6": ep6, "recap": recap, "ep1": ep1, "ep2": ep2, "ep3": ep3, "ep4": ep4, "ep5": ep5, "ep7": ep7, "ep8": ep8, "ep9": ep9}

if __name__ == "__main__":
    for name in sys.argv[1:] or PIECES:
        PIECES[name]()
