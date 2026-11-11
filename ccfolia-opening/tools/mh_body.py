"""第八話の落ちる女の体：MakeHuman の基本メッシュ（hm08、CC0）を女性・細身・身長 1.53m にして、
fall_sim_blender の 12 部品（骨盤・胸・頭・髪・上腕・前腕・もも・すね）へ重みを集めて皮膚を付ける（線形ブレンドスキニング）。
素材は初回に GitHub の makehumancommunity/makehuman から build/models/makehuman へ取る（出典とライセンスは ASSET-CREDITS.txt）。

座標：fall_sim_blender と同じ（x=画面の右＝本人の左、y=奥、z=上、足もとが原点。カメラの方を向いて立つ）"""
import json
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MH = ROOT / "build" / "models" / "makehuman"
SRC = "https://raw.githubusercontent.com/makehumancommunity/makehuman/master/makehuman/data/"
FILES = {
    "base.obj": "3dobjs/base.obj",
    "female.target": "targets/macrodetails/asian-female-young.target",
    "slim.target": "targets/macrodetails/universal-female-young-averagemuscle-minweight.target",
    "default.mhskel": "rigs/default.mhskel",
    "default_weights.mhw": "rigs/default_weights.mhw",
}
SEGS = ["pelvis", "chest", "head", "hair", "uarm_r", "farm_r", "uarm_l", "farm_l", "thigh_r", "shin_r", "thigh_l", "shin_l"]
HEIGHT = 1.53
SLIM = 0.85                                                              # 細身の度合い（0..1）


def fetch():
    MH.mkdir(parents=True, exist_ok=True)
    for name, rel in FILES.items():
        if not (MH / name).exists():
            subprocess.run(["curl", "-sSfL", "-o", str(MH / name), SRC + rel], check=True)


def read_obj(p):
    v, faces, group = [], [], None
    for line in open(p):
        if line.startswith("v "):
            v.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("g "):
            group = line.split()[1]
        elif line.startswith("f ") and group == "body":
            faces.append([int(t.split("/")[0]) - 1 for t in line.split()[1:]])
    return np.array(v), faces


def read_target(p, n):
    d = np.zeros((n, 3))
    for line in open(p):
        if line[0].isdigit():
            a = line.split()
            d[int(a[0])] = [float(x) for x in a[1:4]]
    return d


def seg_of(bone):
    b = bone.split(".")[0]
    side = "_r" if bone.endswith(".R") else "_l"
    if b in ("root", "spine05", "spine04", "pelvis"):
        return "pelvis"
    if b in ("spine03", "spine02", "spine01", "breast", "clavicle", "shoulder01", "neck01"):
        return "chest"
    if b.startswith("upperarm"):
        return "uarm" + side
    if b.startswith(("lowerarm", "wrist", "metacarpal", "finger")):
        return "farm" + side
    if b.startswith("upperleg"):
        return "thigh" + side
    if b.startswith(("lowerleg", "foot", "toe")):
        return "shin" + side
    return "head"


def build():
    """返すのは dict：verts（立ち姿・腕を下ろした形、m）、faces（四角/三角の並び）、W（頂点×12 の重み）、joints（名前→位置）"""
    cache = MH / "body_cache.npz"
    if cache.exists():
        z = np.load(cache, allow_pickle=True)
        return {k: z[k].item() if z[k].dtype == object and z[k].shape == () else z[k] for k in z.files}
    fetch()
    v, faces = read_obj(MH / "base.obj")
    n = len(v)
    v = v + read_target(MH / "female.target", n) + SLIM * read_target(MH / "slim.target", n)
    skel = json.loads((MH / "default.mhskel").read_text())
    J = {k: v[idx].mean(0) for k, idx in skel["joints"].items()}
    wts = json.loads((MH / "default_weights.mhw").read_text())["weights"]
    W = np.zeros((n, len(SEGS)))
    for bone, lst in wts.items():
        k = SEGS.index(seg_of(bone))
        for i, w in lst:
            W[i, k] += w
    used = sorted({i for f in faces for i in f})
    # MakeHuman（y=上、+z=前、単位 dm）→ ここの座標（z=上、-y=前＝カメラ側、m）
    def conv(p):
        p = np.asarray(p, float)
        return np.stack([p[..., 0], -p[..., 2], p[..., 1]], -1)
    v = conv(v)
    J = {k: conv(p) for k, p in J.items()}
    foot = v[used, 2].min()
    top = v[used, 2].max()
    s = HEIGHT / (top - foot)
    cx = v[used, 0].mean()
    cy = v[used][v[used, 2] < foot + 0.3 / s * 0 + (top - foot) * 0.05, 1].mean()
    off = np.array([cx, cy, foot])
    v = (v - off) * s
    J = {k: (p - off) * s for k, p in J.items()}
    jn = lambda b, e="head": J[f"{b}____{e}"]
    joints = {
        "lumbar": jn("spine03"), "neck": jn("neck01"), "head_c": (jn("head") + jn("head", "tail")) / 2,
        "shoulder_r": jn("upperarm01.R"), "elbow_r": jn("lowerarm01.R"), "wrist_r": jn("wrist.R"),
        "shoulder_l": jn("upperarm01.L"), "elbow_l": jn("lowerarm01.L"), "wrist_l": jn("wrist.L"),
        "hip_r": jn("upperleg01.R"), "knee_r": jn("lowerleg01.R"), "ankle_r": jn("foot.R"),
        "hip_l": jn("upperleg01.L"), "knee_l": jn("lowerleg01.L"), "ankle_l": jn("foot.L"),
        "pelvis_c": (jn("upperleg01.R") + jn("upperleg01.L")) / 2 + np.array([0, 0, 0.07]),
    }
    # A ポーズの腕を、体の横へまっすぐ下ろす（上腕・前腕の重みで肩を中心に回す）
    import bpy  # noqa: F401（mathutils を使えるようにする）
    from mathutils import Vector
    for side in "rl":
        sh, el, wr = joints[f"shoulder_{side}"], joints[f"elbow_{side}"], joints[f"wrist_{side}"]
        sx = -1 if side == "r" else 1
        R = np.array(Vector(el - sh).normalized().rotation_difference(Vector((0.03 * sx, 0.0, -1.0)).normalized()).to_matrix())
        w = W[:, SEGS.index(f"uarm_{side}")] + W[:, SEGS.index(f"farm_{side}")]
        # 肩の付け根がちぎれないよう、上腕の重みが薄い所はなめらかに
        v = v + w[:, None] * ((v - sh) @ R.T + sh - v)
        for k in ("elbow", "wrist"):
            joints[f"{k}_{side}"] = (joints[f"{k}_{side}"] - sh) @ R.T + sh
        # 前腕もまっすぐ（肘で少しだけ曲がっているのを伸ばす）
        el, wr = joints[f"elbow_{side}"], joints[f"wrist_{side}"]
        R2 = np.array(Vector(wr - el).normalized().rotation_difference(Vector((0.0, -0.02, -1.0)).normalized()).to_matrix())
        w2 = W[:, SEGS.index(f"farm_{side}")]
        v = v + w2[:, None] * ((v - el) @ R2.T + el - v)
        joints[f"wrist_{side}"] = (wr - el) @ R2.T + el
    # 開いた脚を閉じる（_1 の影は足をほぼそろえて立つ）：ももとすねの重みで股関節を中心に回す
    for side in "rl":
        hp, kn, an = joints[f"hip_{side}"], joints[f"knee_{side}"], joints[f"ankle_{side}"]
        sx = -1 if side == "r" else 1
        R = np.array(Vector(an - hp).normalized().rotation_difference(Vector((sx * 0.035 - hp[0] + hp[0] * 0.55, 0.0, -1.0)).normalized()).to_matrix())
        w = W[:, SEGS.index(f"thigh_{side}")] + W[:, SEGS.index(f"shin_{side}")]
        v = v + w[:, None] * ((v - hp) @ R.T + hp - v)
        for k in ("knee", "ankle"):
            joints[f"{k}_{side}"] = (joints[f"{k}_{side}"] - hp) @ R.T + hp
    # 前後の中心を骨盤に、足の裏を床に
    dy = joints["pelvis_c"][1]
    v[:, 1] -= dy
    for k in joints:
        joints[k] = joints[k] - np.array([0, dy, 0])
    v[:, 2] -= v[used, 2].min()
    W = W / np.maximum(W.sum(1, keepdims=True), 1e-6)
    out = {"verts": v[used], "W": W[used], "joints": joints}
    remap = -np.ones(n, int)
    remap[used] = np.arange(len(used))
    out["faces"] = np.array([[remap[i] for i in (f if len(f) == 4 else f + [f[-1]])] for f in faces])
    np.savez(cache, verts=out["verts"], W=out["W"], faces=out["faces"], joints=np.array(joints, dtype=object))
    return out


def skin(body, T, centers):
    """T: {部品: 4×4（立ち姿の座標 → 世界）}。返すのは世界の頂点"""
    v = body["verts"]
    vh = np.c_[v, np.ones(len(v))]
    out = np.zeros_like(v)
    for k, s in enumerate(SEGS):
        w = body["W"][:, k]
        if s not in T or not w.any():
            continue
        out += w[:, None] * (vh @ T[s].T)[:, :3]
    return out
