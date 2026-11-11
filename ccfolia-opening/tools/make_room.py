"""ココフォリアの部屋で、オープニングの前後に使う素材を書き出す（手順は ROOM-SETUP.md）。

考え方：OPだけが浮かないように、部屋全体を「同じ廊下・同じ黒・同じ文字」でつなぐ。
  待機   … 真っ黒に、隙間の縦線だけがかすかに見える（OPの象徴を先に見せておく）。ざらつきが動くので、OPを最初から流し直す「暗転」も兼ねる
  探索   … OPの廊下をぼかして暗く沈めた背景＋その話の辞書カード（OPで打ち出したものが、そのまま残る）＋蛍光灯のハム音
  休憩   … 待機と同じ縦線と「休憩中」
  終了   … OPと同じ位置のタイトル＋「第N話　終」

出力（build/ccfolia/room/）:
  10_wait.jpg / 11_grain_loop.webp   … 待機（背景／前景）
  20_play.jpg                        … 探索の背景
  21_card_epN.webp                   … 探索に置く辞書カード（マーカーパネル）
  22_ambient_hum_loop.mp3            … 探索のBGM（60秒でつながるループ）
  30_break.jpg                       … 休憩の背景
  40_end_epN.jpg                     … 終了の背景
  50_slot_pcN.webp / 51_slot_npcN.webp … PC1〜4・NPC1〜2の駒の置き場（スクリーンパネル、ラベル入り）

使い方: python3 tools/make_room.py
"""
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
OUT = BUILD / "ccfolia" / "room"
T = json.loads((ROOT / "opening" / "timing.json").read_text(encoding="utf-8"))
EPISODES = json.loads((ROOT / "episodes.local.json").read_text(encoding="utf-8"))
SR = 48000
CARD_W, CARD_H = 570, 360          # 辞書カードの大きさ（ココフォリアのパネル 19×12 マスと同じ比率）


def dither_jpg(img, path, sigma=1.5, seed=1):
    """暗いグラデーションの縞を防ぐため、細かい粒子を混ぜて JPG（画質85）にする"""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    a += np.random.default_rng(seed).normal(0, sigma, a.shape[:2])[..., None]
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(path, quality=85)


def stills():
    """待機・休憩・終了の止め絵を room.html から書き出す"""
    jobs = [("wait", None, "10_wait"), ("break", None, "30_break")]
    jobs += [("end", EPISODES[ep]["no"], f"40_end_ep{ep}") for ep in sorted(EPISODES) if ep.isdigit()]
    script = """
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
let pw; try { pw = require("playwright"); } catch { pw = require("/opt/node22/lib/node_modules/playwright"); }
const [root, jobs, layout] = [process.argv[2], JSON.parse(process.argv[3]), JSON.parse(process.argv[4])];
const browser = await pw.chromium.launch({ args: ["--allow-file-access-from-files"] });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
for (const [view, no, name] of jobs) {
  await page.goto(`file://${root}/opening/room.html?view=${view}`);
  await page.evaluate(async ([lo, no]) => { await document.fonts.ready; window.setLayout(lo); if (no) window.setEnd(no); }, [layout, no]);
  await page.screenshot({ path: `${root}/build/room_${name}.png` });
}
await browser.close();
"""
    tmp = BUILD / "render_room.mjs"
    tmp.write_text(script)
    layout = (ROOT / "opening" / "layout.json").read_text(encoding="utf-8")
    subprocess.run(["node", str(tmp), str(ROOT), json.dumps(jobs, ensure_ascii=False), layout], check=True)
    for _, _, name in jobs:
        dither_jpg(Image.open(BUILD / f"room_{name}.png"), OUT / f"{name}.jpg")


def grain_loop():
    """待機の前景：ごくかすかなざらつき（12fps・10コマのループ）。動く素材なので、OPを最初から流し直す役も兼ねる"""
    rng = np.random.default_rng(5)
    frames = []
    for _ in range(10):
        v = rng.random((360, 640))
        a = np.zeros((360, 640, 4), np.uint8)
        a[..., :3] = (v * 255).astype(np.uint8)[..., None]
        a[..., 3] = (v * 14).astype(np.uint8)              # 最大でも不透明度5%ほど
        frames.append(Image.fromarray(a, "RGBA"))
    frames[0].save(OUT / "11_grain_loop.webp", save_all=True, append_images=frames[1:],
                   duration=83, loop=0, quality=60)


def play_bg():
    """探索の背景：OPの廊下をぼかして暗く沈める。場所を説明する絵ではなく、空気だけを残す"""
    img = Image.open(ROOT / "opening" / "bg.png").convert("RGB").filter(ImageFilter.GaussianBlur(6))
    a = np.asarray(img).astype(np.float32) / 255
    yy, xx = np.mgrid[0:720, 0:1280].astype(np.float32)
    vignette = np.clip(1 - 0.75 * (((xx - 640) / 760) ** 2 + ((yy - 330) / 470) ** 2), 0.15, 1)
    a = a * 0.38 * vignette[..., None]
    dither_jpg(Image.fromarray((a * 255).astype(np.uint8)), OUT / "20_play.jpg", seed=2)


def cards():
    """探索に置く辞書カード：OPの最後のコマから切り出す（カーソルが消えている瞬間）"""
    for ep in sorted(e for e in EPISODES if e.isdigit()):
        e = EPISODES[ep]
        chars = sum(len(s) for s in (e["no"], f"■ {e['word']}（{e['kana']}）", e["pos"], e["def"]))
        end = T["card"] + chars * T["typeStep"]
        t = np.floor(end * 2 + 1) / 2 + 0.1                      # 打ち終わったあと、カーソルが消えている半秒
        if np.floor(t * 2) % 2 == 0:
            t += 0.5
        subprocess.run(["node", "tools/render_opening.mjs", "--ep", ep, "--layer", "card", "--from", f"{t:.3f}",
                        "--to", f"{t + 1 / T['fps']:.3f}", "--out", f"room_card_ep{ep}"], check=True, cwd=ROOT,
                       stdout=subprocess.DEVNULL)
        im = Image.open(BUILD / f"room_card_ep{ep}" / "f0000.png").convert("RGBA")
        text = im.crop(im.getbbox())
        # 全話同じ大きさ（19:12）にそろえる。ココフォリアでパネルの大きさを1つに決めても、話によって縦横比がゆがまない
        pad = 28
        assert text.width + 2 * pad <= CARD_W and text.height + 2 * pad <= CARD_H, (ep, text.size)
        card = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
        card.alpha_composite(text, (pad, pad))
        # 読みやすさのため、文字の形に沿ったぼんやりした影だけを敷く。四角い黒地は背景から浮いて見えるので使わない
        halo = card.getchannel("A").filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(12))
        halo = halo.point(lambda v: min(255, int(v * 1.6)))
        shadow = Image.new("RGBA", card.size, (4, 4, 4, 0))
        shadow.putalpha(halo)
        # PNG はココフォリアで256色に変換されて影に縞が出るため、そのまま保たれる可逆 WebP にする
        Image.alpha_composite(shadow, card).save(OUT / f"21_card_ep{ep}.webp", lossless=True)


def ambient():
    """探索のBGM：OPと同じ蛍光灯のハム音を、ずっと小さく。60秒でつながるループ"""
    n = 60 * SR
    t = np.arange(n) / SR
    rng = np.random.default_rng(3)
    hum = sum(a * np.sin(2 * np.pi * 100 * h * t) for h, a in ((1, 0.20), (2, 0.16), (3, 0.10), (4, 0.07), (5, 0.04), (6, 0.03)))
    hum = np.tanh(hum * 1.6) / 1.2
    # 建物の低い空気の音。ループの継ぎ目が目立たないよう、端を互いに重ねる
    air = np.convolve(rng.normal(0, 1, n + SR), np.ones(120) / 120, "same")
    fade = np.linspace(0, 1, SR)
    air = np.concatenate([air[:SR] * fade + air[n:] * (1 - fade), air[SR:n]]) * 0.6
    # ゆっくり揺れる（止まった音にしない）
    sway = 1 + 0.12 * np.sin(2 * np.pi * t / 20) + 0.05 * np.sin(2 * np.pi * t / 7.5)
    out = (hum * sway + air)
    out = out / np.abs(out).max() * 0.25                        # OPよりずっと小さく。会話の邪魔をしない
    wav = BUILD / "ambient_hum_loop.wav"
    pcm = (out * 32767).astype("<i2").tobytes()
    import wave
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR), w.writeframes(pcm)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(wav), "-c:a", "libmp3lame", "-b:a", "128k",
                    str(OUT / "22_ambient_hum_loop.mp3")], check=True)


def slots():
    """駒の置き場（スクリーンパネル）：蛍光灯の下に立っているような淡い光の円すいと、足もとの光だまり、その下に小さなラベル。
    四角い枠は暗い背景から浮くので描かない。32×46マス（1マス10px）で、駒サイズ40の全身立ち絵が光だまりに立つ。
    ラベルは頭の上（光の出どころ）に置く。足もとの下はココフォリアが駒の名前を出すので重なる。
    書体と色は STYLE.md のとおり（ラベルはしっぽり明朝、控えめな文字の白。光は蛍光灯の色）"""
    from PIL import ImageDraw, ImageFont
    W, H, FLOOR = 320, 460, 434                       # FLOOR＝足もと（光だまりの中心）
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    font = ImageFont.truetype(str(ROOT / "fonts" / "ShipporiMincho-Medium.ttf"), 22)
    labels = [("50_slot_pc", f"PC {k}", 1.0) for k in range(1, 5)] + [("51_slot_npc", f"NPC {k}", 0.6) for k in range(1, 3)]
    for name, label, light in labels:                 # NPC は同じ色のまま、光を弱くして沈める
        top = 0.35 + 0.65 * (1 - np.clip(yy / FLOOR, 0, 1))
        half = 40 + np.clip(yy / FLOOR, 0, 1) * 110
        cone = np.clip(1 - np.abs(xx - W / 2) / half, 0, 1) ** 1.6 * top * light
        pool = np.exp(-(((xx - W / 2) / 105) ** 2 + ((yy - FLOOR) / 16) ** 2)) * light * 1.4
        shadow = np.exp(-(((xx - W / 2) / 70) ** 2 + ((yy - FLOOR) / 7) ** 2)) * 0.55
        alpha = np.clip(cone * 0.10 + pool * 0.22, 0, 1)
        out_a = alpha + shadow * (1 - alpha)          # 光の上に、足もとの影を黒で重ねる
        rgb = np.array((236, 214, 184), np.float32)[None, None, :] * (alpha / np.maximum(out_a, 1e-6))[..., None]
        out_a = np.clip(out_a + np.random.default_rng(3).normal(0, 0.004, out_a.shape), 0, 1)  # 縞を防ぐ細かい粒子
        img = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), out_a * 255]).astype(np.uint8), "RGBA")
        # ラベル：頭の上に、字間を空けて小さく。文字の形に沿った影だけを敷く
        text = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(text)
        chars = list(label)
        widths = [d.textlength(c, font=font) for c in chars]
        gap = 22 * 0.25
        x = (W - sum(widths) - gap * (len(chars) - 1)) / 2
        for c, w in zip(chars, widths):
            d.text((x, 4), c, font=font, fill=(185, 177, 170, 235))   # #b9b1aa
            x += w + gap
        halo = text.getchannel("A").filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(8))
        shade = Image.new("RGBA", (W, H), (4, 4, 4, 0))
        shade.putalpha(halo.point(lambda v: min(255, int(v * 1.4))))
        img = Image.alpha_composite(Image.alpha_composite(img, shade), text)
        img.save(OUT / f"{name}{label.split()[1]}.webp", lossless=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    stills()
    grain_loop()
    play_bg()
    cards()
    ambient()
    slots()
    for p in sorted(OUT.iterdir()):
        print(f"{p.name:28s} {p.stat().st_size / 1024:7.0f} KB")


if __name__ == "__main__":
    main()
