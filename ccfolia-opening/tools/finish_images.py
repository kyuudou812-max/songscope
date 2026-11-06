"""ChatGPT から返ってきた zip（16枚）を、1回のコマンドで部屋の素材に仕上げる。

使い方: python3 tools/finish_images.py <返ってきた.zip> [--refs <参考画像フォルダ>] [--spec <指示書.md>] [--sheet <確認シート.png>]
                                      [--no-make]   （make_set_pieces を回さない）

やること:
  1. zip を build/chatgpt_in/<日時>/ に安全に展開する（絶対パス・..・リンク・巨大ファイル・画像以外は捨てる）
  2. ファイル名を「番号＋a/b/c」で対応づける（01_door_a.png → 1-a。多少名前が違っても、番号と末尾の文字で拾う）
  3. 参考画像と同じ大きさに切り抜き・縮小し、構図がずれていれば平行移動で合わせる（差分どうしも1枚目に合わせる）
  4. 参考画像の「明るさ → 色」の対応で色調をそろえる（赤茶。⑧の玉虫色だけ、元の光沢を少し残す）
  5. make_set_pieces / add_set_pieces が見る名前で書き出す（下の OUTPUTS）。届いた絵があれば _draft が本番に替わる
  6. make_set_pieces の該当の素材（vulture・balcony・finale・ep9）を作り直す
  7. 参考画像と結果を並べ、指示書の「必要／不要」を添えた確認シートを書き出す

参考画像（refs）と指示書は、既定では chatgpt.local.refs/ と chatgpt-spec.local.md（どちらも git に入れない）。
"""
import argparse
import datetime
import json
import re
import shutil
import stat
import subprocess
import sys
import unicodedata
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
CC = ROOT / "build" / "ccfolia"
S = CC / "scenes"
FX = CC / "fx"
A = ROOT / "assets"
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}
MAX_FILE = 40 * 1024 * 1024
MAX_TOTAL = 400 * 1024 * 1024

# 番号 → (参考画像, 枚数, 構図を参考画像に合わせるか, 玉虫色を残すか)
ITEMS = {
    1: ("01_conference.jpg", "ab", False, False),
    2: ("02_underpass.jpg", "ab", True, False),
    3: ("03_room.jpg", "abc", True, False),
    4: ("04_corridor.png", "", True, False),
    5: ("05_style_only.jpg", "ab", False, False),
    6: ("06_bluesheet.jpg", "", True, False),
    7: ("07_restaurant.jpg", "", True, False),
    8: ("08_storage.jpg", "", True, True),
}
NAMES = {1: "01_door", 2: "02_vulture", 3: "03_balcony", 4: "04_door_open", 5: "05_film",
         6: "06_bluesheet_items", 7: "07_restaurant_gaze", 8: "08_storage_iridescent"}
# 書き出し先（make_set_pieces.py の FULL_DOOR・FILM・BALCONY・VULTURE、add_set_pieces.py の SCENES が見る名前）
OUTPUTS = {
    (1, "a"): S / "ep1_01_door_a.jpg", (1, "b"): S / "ep1_01_door_b.jpg",
    (2, "a"): A / "ep7_vulture_1.png", (2, "b"): A / "ep7_vulture_2.png",
    (3, "a"): A / "ep8_balcony_0.png", (3, "b"): A / "ep8_balcony_1.png", (3, "c"): A / "ep8_balcony_2.png",
    (4, ""): A / "door" / "stage5_full.png",
    (5, "a"): A / "ep9_film_1.png", (5, "b"): A / "ep9_film_2.png",
    (6, ""): S / "ep4_02_bluesheet_items.jpg",
    (7, ""): S / "ep6_01_restaurant_gaze.jpg",
    (8, ""): S / "ep2_03_storage_iridescent.jpg",
}
GAZE_FLASH = FX / "ep6" / "63_gaze_flash.webp"       # 全員の視線：1秒だけ見えて消える前景（1回再生）
PIECES = {2: ["vulture"], 3: ["balcony", "finale"], 4: ["ep9", "moving"], 5: ["ep9"]}   # moving に暗闇証明が入っている


# ---------------------------------------------------------------- 1. 展開
def safe_extract(zp, dest):
    dest.mkdir(parents=True, exist_ok=False)
    total, got = 0, []
    with zipfile.ZipFile(zp) as z:
        for info in z.infolist():
            name = unicodedata.normalize("NFC", info.filename.replace("\\", "/"))
            if info.flag_bits & 0x800 == 0:                       # 古い zip は cp437 で入る（日本語名の救済）
                try:
                    name = unicodedata.normalize("NFC", info.filename.encode("cp437").decode("cp932"))
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pass
            parts = [p for p in name.split("/") if p not in ("", ".")]
            if info.is_dir() or not parts or name.startswith("/") or ".." in parts or re.match(r"^[A-Za-z]:", name):
                continue
            if stat.S_ISLNK(info.external_attr >> 16) or parts[0] == "__MACOSX" or parts[-1].startswith("."):
                continue
            if Path(parts[-1]).suffix.lower() not in IMG_EXT or info.file_size > MAX_FILE:
                print(f"  捨てた: {name}")
                continue
            total += info.file_size
            if total > MAX_TOTAL:
                raise SystemExit("zip の中身が大きすぎる")
            out = dest / f"{len(got):02d}_{re.sub(r'[^0-9A-Za-z_.-]', '_', parts[-1])}"
            with z.open(info) as src, open(out, "wb") as f:
                shutil.copyfileobj(src, f, 1 << 20)
            try:
                Image.open(out).verify()
            except Exception:
                print(f"  画像として読めない: {name}")
                out.unlink()
                continue
            got.append((parts[-1], out))
    return got


# ---------------------------------------------------------------- 2. 対応づけ
def parse(name):
    """ファイル名 → (番号, a/b/c)。全角・大文字・「(1)」・区切りの違いは無視する"""
    s = re.sub(r"\(\d+\)|copy|コピー", " ", unicodedata.normalize("NFKC", Path(name).stem).lower())
    m = re.search(r"(?<!\d)0?([1-8])(?!\d)", s)
    if m:
        num, s = int(m.group(1)), s[:m.start()] + " " + s[m.end():]
    else:
        num = next((n for n, base in sorted(NAMES.items(), key=lambda t: -len(t[1])) if base[3:] in s.replace("-", "_")), None)
    letters = re.findall(r"(?<![a-z])([abc])(?![a-z])", s) or ["abc"[int(d) - 1] for d in re.findall(r"(?<!\d)([123])(?!\d)", s)]
    return num, (letters[-1] if letters else None)


def map_files(got):
    found, by_num = {}, {}
    for orig, path in sorted(got):
        num, letter = parse(orig)
        if num is None:
            print(f"  対応づけられない: {orig}")
            continue
        by_num.setdefault(num, []).append((letter, orig, path))
    for num, lst in by_num.items():
        letters = ITEMS[num][1] or ""
        if not letters:
            found[(num, "")] = lst[0][2]
            if len(lst) > 1:
                print(f"  {NAMES[num]} が {len(lst)} 枚ある。最初の {lst[0][1]} を使う")
            continue
        rest = []
        for letter, orig, path in lst:
            if letter in letters and (num, letter) not in found:
                found[(num, letter)] = path
            else:
                rest.append(path)
        for want in letters:                                      # 文字のないものは名前順に空きへ
            if (num, want) not in found and rest:
                found[(num, want)] = rest.pop(0)
    return found


# ---------------------------------------------------------------- 3. 大きさと位置
def gray_small(a, k=4):
    g = a.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
    h, w = g.shape[0] // k * k, g.shape[1] // k * k
    g = g[:h, :w].reshape(h // k, k, w // k, k).mean((1, 3))
    gy, gx = np.gradient(g)
    e = np.hypot(gx, gy)
    win = np.outer(np.hanning(e.shape[0]), np.hanning(e.shape[1]))
    return (e - e.mean()) * win


def shift_between(ref, img, k=4):
    """位相相関で、img を ref に重ねるための平行移動（px）。はっきりしない・大きすぎるときは 0"""
    a, b = gray_small(ref, k), gray_small(img, k)
    F = np.fft.fft2(a) * np.conj(np.fft.fft2(b))
    r = np.fft.ifft2(F / np.maximum(np.abs(F), 1e-6)).real
    y, x = np.unravel_index(np.argmax(r), r.shape)
    peak = r[y, x] / (r.std() + 1e-9)
    if y > r.shape[0] // 2:
        y -= r.shape[0]
    if x > r.shape[1] // 2:
        x -= r.shape[1]
    dy, dx = y * k, x * k
    if peak < 8 or abs(dx) > ref.shape[1] * 0.06 or abs(dy) > ref.shape[0] * 0.06:
        return 0, 0
    return dx, dy


def translate(a, dx, dy):
    if not (dx or dy):
        return a
    pad = np.pad(a, ((abs(dy), abs(dy)), (abs(dx), abs(dx)), (0, 0)), mode="edge")
    h, w = a.shape[:2]
    return pad[abs(dy) - dy:abs(dy) - dy + h, abs(dx) - dx:abs(dx) - dx + w]


# ---------------------------------------------------------------- 4. 色調
def lum(a):
    return a.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)


def color_curve(ref):
    """参考画像の「明るさ → 平均の色」（256段）"""
    L = np.clip(lum(ref), 0, 255).astype(int).ravel()
    rgb = ref.reshape(-1, 3).astype(np.float64)
    cnt = np.bincount(L, minlength=256)
    curve = np.stack([np.bincount(L, rgb[:, c], 256) for c in range(3)], 1) / np.maximum(cnt, 1)[:, None]
    ok = cnt > 20
    xs = np.arange(256)
    for c in range(3):                                            # 画素の少ない明るさは、近い段から補う
        curve[:, c] = np.interp(xs, xs[ok], curve[ok, c]) if ok.any() else xs
    return curve.astype(np.float32)


def match_tone(img, ref, keep_chroma=0.0):
    li, lr = lum(img), lum(ref)
    qs = np.linspace(0, 100, 257)                                 # 明るさの分布を参考画像にそろえる
    mapped = np.interp(li, np.percentile(li, qs), np.percentile(lr, qs))
    out = color_curve(ref)[np.clip(mapped, 0, 255).astype(int)]
    if keep_chroma:                                              # 玉虫色：元の絵の「色のずれ」の強いところだけ戻す
        dev = img.astype(np.float32) - color_curve(img)[np.clip(li, 0, 255).astype(int)]
        w = np.clip((np.abs(dev).max(2) - 12) / 40, 0, 1)[..., None]
        out = out + dev * keep_chroma * w
    return np.clip(out, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- 5〜7
def gaze_flash(path, gaze):
    """全員の視線：1秒だけ映り、消える（ファミレスのシーンの前景、1回再生）"""
    path.parent.mkdir(parents=True, exist_ok=True)
    f1 = Image.open(gaze).convert("RGBA")
    f2 = Image.new("RGBA", f1.size, (0, 0, 0, 0))
    f1.save(path, save_all=True, append_images=[f2], duration=[1000, 100], loop=1, quality=82)


def spec_notes(spec):
    """指示書から、保存名ごとの「必要／不要」"""
    notes = {}
    if not spec or not spec.exists():
        return notes
    for sec in re.split(r"\n## ", spec.read_text(encoding="utf-8")):
        names = re.findall(r"(0[1-8]_[a-z_]+?)\.png", sec)
        need = re.search(r"必要：(.*)", sec)
        no = re.search(r"不要：(.*)", sec)
        for n in names:
            notes[n] = ("必要：" + need.group(1) if need else "") + "\n" + ("不要：" + no.group(1) if no else "")
    return notes


def wrap(d, text, f, width):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for ch in para:
            if d.textlength(cur + ch, font=f) > width:
                lines.append(cur)
                cur = "　" + ch
            else:
                cur += ch
        lines.append(cur)
    return lines


def check_sheet(rows, notes, path):
    TW, TH, TXT_W, PAD = 480, 270, 560, 14
    fpath = ROOT / "fonts" / "ZenKakuGothicNew-Medium.ttf"
    f = ImageFont.truetype(str(fpath), 17) if fpath.exists() else ImageFont.load_default()
    fb = ImageFont.truetype(str(fpath), 21) if fpath.exists() else f
    H = PAD + len(rows) * (TH + 30 + PAD)
    sheet = Image.new("RGB", (PAD * 4 + TW * 2 + TXT_W, H), (24, 20, 18))
    d = ImageDraw.Draw(sheet)
    y = PAD
    for key, ref, res, info in rows:
        d.text((PAD, y), f"{key}  {info}", font=fb, fill=(240, 220, 190))
        for k, im in enumerate((ref, res)):
            if im is not None:
                sheet.paste(ImageOps.fit(Image.fromarray(im), (TW, TH)), (PAD + k * (TW + PAD), y + 30))
            else:
                d.rectangle([PAD + k * (TW + PAD), y + 30, PAD + k * (TW + PAD) + TW, y + 30 + TH], outline=(200, 60, 50), width=3)
                d.text((PAD + k * (TW + PAD) + 20, y + 40), "（なし）", font=fb, fill=(220, 80, 60))
        ty = y + 34
        for line in wrap(d, notes.get(key, ""), f, TXT_W):
            d.text((PAD * 3 + TW * 2, ty), line, font=f, fill=(225, 210, 190))
            ty += 22
        y += TH + 30 + PAD
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, optimize=True)
    print(f"確認シート: {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("zip")
    ap.add_argument("--refs", default=str(ROOT / "chatgpt.local.refs"))
    ap.add_argument("--spec", default=str(ROOT / "chatgpt-spec.local.md"))
    ap.add_argument("--sheet", default=str(ROOT / "build" / "chatgpt_check.png"))
    ap.add_argument("--no-make", action="store_true")
    o = ap.parse_args()
    refs = Path(o.refs)
    if not refs.is_dir():
        raise SystemExit(f"参考画像のフォルダがない: {refs}（--refs で指定）")

    dest = ROOT / "build" / "chatgpt_in" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"展開: {dest.relative_to(ROOT)}")
    found = map_files(safe_extract(Path(o.zip), dest))

    rows, done = [], set()
    for num, (refname, letters, align, irid) in ITEMS.items():
        ref = np.asarray(Image.open(refs / refname).convert("RGB"))
        size = (ref.shape[1], ref.shape[0])
        first = None
        for letter in (letters or [""]):
            key = NAMES[num] + (f"_{letter}" if letter else "")
            src = found.get((num, letter))
            if src is None:
                print(f"  ない: {key}")
                rows.append((key, ref, None, "届いていない"))
                continue
            img = np.asarray(ImageOps.fit(Image.open(src).convert("RGB"), size, Image.LANCZOS))
            anchor = ref if align else first                     # 構図の基準：参考画像、または同じ項目の1枚目
            dx, dy = shift_between(anchor, img) if anchor is not None else (0, 0)
            img = translate(img, dx, dy)
            img = match_tone(img, ref, keep_chroma=0.6 if irid else 0.0)
            if first is None:
                first = img
            out = OUTPUTS[(num, letter)]
            out.parent.mkdir(parents=True, exist_ok=True)
            if out.suffix == ".jpg":
                Image.fromarray(img).save(out, quality=88)
            else:
                Image.fromarray(img).save(out, optimize=True)
            mb = out.stat().st_size / 1024 / 1024
            print(f"  {key} ← {src.name}  ずれ({dx},{dy})  → {out.relative_to(ROOT)}  {mb:.2f}MB")
            rows.append((key, ref, img, f"ずれ補正 ({dx},{dy})"))
            done.add(num)
    if 7 in done:
        gaze_flash(GAZE_FLASH, OUTPUTS[(7, "")])
    if not o.no_make:
        pieces = []
        for n in sorted(done):
            pieces += [p for p in PIECES.get(n, []) if p not in pieces]
        if pieces:
            print("make_set_pieces:", " ".join(pieces))
            subprocess.run([sys.executable, str(ROOT / "tools" / "make_set_pieces.py"), *pieces], check=True, cwd=ROOT)
    check_sheet(rows, spec_notes(Path(o.spec)), Path(o.sheet))
    json.dump({k[0] * 10 + "abc".find(k[1]) + 1 if k[1] else k[0] * 10: str(v) for k, v in found.items()},
              open(dest / "_map.json", "w"), indent=1)


if __name__ == "__main__":
    main()
