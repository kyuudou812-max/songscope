"""蛍光灯の明滅パターンを話ごとに作り、opening/flicker.json に書き出す。映像と音の両方がこれを読む。

切れかけた蛍光灯らしく、1回ごとに「長さ・暗くなり方・点き直しの回数・起きる時刻」をばらつかせる。
同じ話なら毎回同じパターンになる（乱数の種を話数で固定）。

光過敏への配慮（WCAG 2.3.1）：どの1秒間をとっても、暗くなる回数が3回を超えないようにする。

使い方: python3 make_flicker.py
"""
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
FPS = json.loads((ROOT / "opening" / "timing.json").read_text(encoding="utf-8"))["fps"]
WINDOW = (3.2, 7.3)        # 明滅してよい時間帯（一文の途中〜カットの手前）
MIN_GAP = 0.75             # 明滅と明滅の間隔（秒）。1秒3回以内かどうかは別に確かめる


def event(rng):
    """1回の明滅：点き直しを1〜3回含む、2〜9コマの暗さの並び（0=普段どおり、1=真っ暗）"""
    frames = []
    for d in range(int(rng.integers(1, 4))):
        if d:  # 点き直す前に、一瞬戻る（1〜2コマ）
            frames += [float(rng.uniform(0.0, 0.15))] * int(rng.integers(1, 3))
        depth = float(rng.uniform(0.25, 0.75))
        length = int(rng.integers(1, 4))
        frames += [round(depth * float(rng.uniform(0.7, 1.0)), 3) for _ in range(length)]
    return frames


def dips_per_second_ok(timeline):
    """どの1秒（FPSコマ）をとっても、暗くなり始める回数が3回以下か"""
    starts = [f for f in range(1, len(timeline)) if timeline[f] > 0.2 >= timeline[f - 1]]
    return all(sum(1 for s in starts if a <= s < a + FPS) <= 3 for a in range(len(timeline)))


def main():
    esc = json.loads((ROOT / "opening" / "escalation.json").read_text(encoding="utf-8"))["episodes"]
    result = {"_comment": "tools/make_flicker.py が escalation.json の flickers（回数と目安の時刻）から作る。frames は [コマ番号, 暗さ]。",
              "fps": FPS, "episodes": {}}
    for ep, p in esc.items():
        rng = np.random.default_rng(1000 + int(ep))
        for _ in range(200):  # 条件を満たすまで作り直す
            times = sorted(float(np.clip(t + rng.uniform(-0.35, 0.35), *WINDOW)) for t in p["flickers"])
            if any(b - a < MIN_GAP for a, b in zip(times, times[1:])):
                continue
            timeline = np.zeros(int(8 * FPS))
            frames = []
            for t in times:
                f0 = int(np.floor(t * FPS + 0.5))
                for k, dim in enumerate(event(rng)):
                    timeline[f0 + k] = dim
                    if dim > 0:
                        frames.append([f0 + k, dim])
            if dips_per_second_ok(list(timeline)):
                break
        else:
            raise SystemExit(f"ep{ep}: 条件を満たす明滅が作れなかった")
        result["episodes"][ep] = {"frames": frames}
        print(f"ep{ep}: {len(p['flickers'])}回  " + "  ".join(f"{t:.2f}s" for t in times))
    (ROOT / "opening" / "flicker.json").write_text(json.dumps(result, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
