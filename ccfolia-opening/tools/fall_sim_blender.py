"""第八話ベランダ：女が手すりを後ろ向きに越えて落ちるところを、Blender（pip の bpy）で物理として作り、黒い影（アルファ）として書き出す。

  python3 tools/fall_sim_blender.py calib   → build/cache/fall_sim/calib_overlay.png（カメラと手すりの合わせの確認）
  python3 tools/fall_sim_blender.py         → 全部（キャリブレーション確認・シミュレーション・本番の影・横からの確認・エンドB用）

書き出すもの（build/cache/fall_sim/）
  main/NNNN.png  … 背景の絵（ep8_balcony_0）と同じカメラ・同じ 1280×720 の、女の影のアルファ（8bit グレー）。30fps、
                   1コマを 1/120 秒おきに3回描いて平均（シャッター 180°のモーションブラー）。手すり・腰壁・床は holdout なので、
                   手すりの向こうへ越えた体は、手すりの棒・すりガラスの板・ベランダの床の縁に正しく隠れる
  side/NNNN.png  … 横から見た確認用（物理が正しいか：手すりの上で腰を支点に回り、床の縁の向こうへ落ちる）
  endb/NNNN.png  … エンドB 用：2つ下の階の窓の高さから見た、落ちていく体（holdout なし）
  meta.json      … コマ数・手を離すコマ・消えるコマなど

---- カメラの合わせ（背景 ep8_balcony_0.png、1280×720 で測った数値） ----
  手すりの上端：x=130→y297, 240→306, 300→310, 350→315, 430→319（右へ下がる）
  手すりの下の横棒：x=240→y415, 300→411, 350→408, 430→403（右へ上がる）
  → 2本は右の消失点 (1041, 365) に集まる。窓の上枠（x=250→y84, 410→y140）も同じ点 (≈1050, 365) を通る。
  → 地平線 y=365（カメラは水平、傾き 0）。窓の壁と直交するドアの壁の床の線（傾き 0.069、ドアの下端 (1060,456)）の消失点は x≈-259。
  2つの直交する消失点から 焦点距離 f = sqrt((1041-640)(640+259)) ≈ 605px（水平画角 93°、35mm 換算 17mm）。
  手すり（高さ 1.10m と置く）の上端 y307.5・ベランダの床の線 y425（x=280）→ その奥行き 5.66m、カメラの高さ 0.56m。
  女（ep8_balcony_1 から切り出す影。足もと (340, 458)、頭の上 y205）：奥行き 3.66m → 身長 1.53m。
  女から手すりまで（視線に沿って）2.8m、手すりの面までの垂直距離 2.4m。窓の壁・手すりは画面に対して 34° 振れている。
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
OUTD = ROOT / "build" / "cache" / "fall_sim"
W, H = 1280, 720
F_PX, CX, HORIZON = 605.0, 640.0, 365.0
CAM_H = 0.562
FPS = 30                                   # 本番のコマ
SIM_FPS = 120                              # 物理と、モーションブラーの細かいコマ（1コマ = 1/120 秒）
SUB = SIM_FPS // FPS
HEIGHT = 1.53
RAIL_H = 1.10
RAIL_P0 = np.array([-3.37, 5.66])          # 手すりの線上の1点（x=280 の上端から逆算）
RAIL_D = np.array([0.558, 0.830])          # 手すりの向き（窓の壁と平行。右の消失点へ）
RAIL_N = np.array([-0.830, 0.558])         # 手すりの面の外向き（ベランダの外＝カメラから遠ざかる向き）
FEET0 = np.array([-1.815, 3.66])           # 女の足もと（画面 (340, 458)）
POSTS_PX = (97, 200, 280, 377, 435, 492, 542)   # 背景（カーテンのない部屋 ep8_balcony_nocurtain）の手すりの柱の x
# 窓の壁（カーテンのない部屋の窓の下枠の両端 (30,465)・(575,420) から。消失点 x≈1230 → 画面に対して 44.5° 振れている）
WIN_L = np.array([-3.43, 3.40])
WIN_R = np.array([-0.66, 6.18])
WIN_D = (WIN_R - WIN_L) / np.linalg.norm(WIN_R - WIN_L)
WIN_IN = np.array([WIN_D[1], -WIN_D[0]])   # 部屋の内向き（カメラ側）
WIN_TOP = 2.50                             # 窓の上枠の高さ（両端で 2.53/2.50m）
LOOP = 9.2                                 # ベランダのループ（突風 4.6 秒 × 2）
LOOP_HANDOFF = 0.0                         # ループの頭から人体メッシュの女（絵の女への受け渡しはしない）
GUST_T = 4.6

# 時刻（秒、0 = 絵の女から物理の女へ受け渡すコマ）
PRE = 1.7                                  # ループの頭から、手を振り終えて歩き出すまで（t は歩き出しを 0 とする）
T_ARM = (0.10, 0.45)                       # 振っていた手を下ろす
T_WALK = (0.25, 1.95)                      # 後ろ向きに歩いて手すりまで下がる
T_STOP = 1.95                              # 手すりに腰が当たって止まる
T_SIT = 2.25                               # 腰を手すりに当てたまま反りはじめる（腕は部屋の側へ）
T_REL = 2.40                               # ここから先は物理だけ（重力と反る勢いで、手すりを支点に後ろへ回る）
REL_IDX = int(round((1.7 + 2.40 + 0.12) * 120)) # all_poses の列で、物理（手すりを越える所）が始まる位置（PRE + T_REL、1/120 秒）
ALPHA = 18.0                               # 重心が外へ出てからの角加速度（rad/s²）
SWITCH_DEG = 95                             # ここまで回ったら手すりを離れて落ちる（それ以上回ると頭が部屋の側へ戻ってしまう）
OMEGA0 = 8.0                               # 反る勢いから引き継ぐ、後ろへ回る角速度（rad/s）
G_END = 1.3                                # 歩く間に体を大きくする倍率（growth の説明）
T_END = T_REL + 2.0

SEG = {  # 名前: (親, 関節, 中心, 質量 kg, 当たりの形, 寸法)  立ち姿（カメラの方を向く。x=画面の右、y=奥、z=上、足もとが原点）
    "pelvis": (None, (0, 0, 0.86), (0, 0, 0.86), 11.0, "BOX", (0.30, 0.19, 0.20)),
    "chest": ("pelvis", (0, 0, 0.96), (0, 0, 1.13), 13.0, "BOX", (0.28, 0.17, 0.32)),
    "head": ("chest", (0, 0, 1.31), (0, 0, 1.42), 4.0, "SPHERE", (0.17, 0.19, 0.21)),
    "hair": ("head", (0, 0.05, 1.45), (0, 0.075, 1.29), 0.4, "BOX", (0.17, 0.05, 0.26)),
    "uarm_r": ("chest", (-0.165, 0, 1.27), (-0.175, 0, 1.135), 1.4, "CAPSULE", (0.075, 0.075, 0.30)),
    "farm_r": ("uarm_r", (-0.185, 0, 1.00), (-0.19, 0, 0.81), 1.1, "CAPSULE", (0.06, 0.06, 0.42)),
    "uarm_l": ("chest", (0.165, 0, 1.27), (0.175, 0, 1.135), 1.4, "CAPSULE", (0.075, 0.075, 0.30)),
    "farm_l": ("uarm_l", (0.185, 0, 1.00), (0.19, 0, 0.81), 1.1, "CAPSULE", (0.06, 0.06, 0.42)),
    "thigh_r": ("pelvis", (-0.085, 0, 0.78), (-0.083, 0, 0.605), 5.5, "CAPSULE", (0.13, 0.13, 0.42)),
    "shin_r": ("thigh_r", (-0.08, 0, 0.43), (-0.078, 0, 0.25), 3.0, "CAPSULE", (0.09, 0.09, 0.42)),
    "thigh_l": ("pelvis", (0.085, 0, 0.78), (0.083, 0, 0.605), 5.5, "CAPSULE", (0.13, 0.13, 0.42)),
    "shin_l": ("thigh_l", (0.08, 0, 0.43), (0.078, 0, 0.25), 3.0, "CAPSULE", (0.09, 0.09, 0.42)),
}
ORDER = list(SEG)

# 見た目（メタボール：つながった、なめらかな体の線）。各部品の座標で (種類, 中心, 半径 (x,y,z) か (長さの半分, 太さ)) 。
# 寸法は ep8_balcony_1 の影（肩幅 0.33m・腰の張り・ももの太さ・肩にかかる長い髪）に合わせた
LOOK = {
    "pelvis": [("E", (0, 0.0, 0.86), (0.155, 0.10, 0.10)), ("E", (0, 0.045, 0.82), (0.13, 0.08, 0.08))],
    "chest": [("E", (0, 0, 0.99), (0.115, 0.08, 0.07)), ("E", (0, 0, 1.12), (0.125, 0.085, 0.10)),
              ("E", (0, -0.035, 1.12), (0.12, 0.06, 0.05)), ("E", (0, 0, 1.235), (0.16, 0.075, 0.05)),
              ("C", (0, 0, 1.30), (0.02, 0.035))],
    "head": [("E", (0, 0.005, 1.43), (0.072, 0.09, 0.10))],
    "hair": [("E", (0, 0.035, 1.44), (0.088, 0.075, 0.09)), ("E", (0, 0.07, 1.30), (0.10, 0.045, 0.13)),
             ("E", (0, 0.085, 1.17), (0.085, 0.03, 0.08))],
    "uarm_r": [("C", (-0.175, 0, 1.135), (0.12, 0.035))],
    "farm_r": [("C", (-0.19, 0, 0.85), (0.11, 0.028)), ("E", (-0.195, 0, 0.66), (0.022, 0.035, 0.06))],
    "uarm_l": [("C", (0.175, 0, 1.135), (0.12, 0.035))],
    "farm_l": [("C", (0.19, 0, 0.85), (0.11, 0.028)), ("E", (0.195, 0, 0.66), (0.022, 0.035, 0.06))],
    "thigh_r": [("C", (-0.083, 0, 0.62), (0.13, 0.068)), ("C", (-0.083, 0, 0.48), (0.04, 0.05))],
    "shin_r": [("C", (-0.08, 0, 0.27), (0.14, 0.042)), ("E", (-0.08, -0.06, 0.03), (0.035, 0.10, 0.03))],
    "thigh_l": [("C", (0.083, 0, 0.62), (0.13, 0.068)), ("C", (0.083, 0, 0.48), (0.04, 0.05))],
    "shin_l": [("C", (0.08, 0, 0.27), (0.14, 0.042)), ("E", (0.08, -0.06, 0.03), (0.035, 0.10, 0.03))],
}
SCALE = 1.0

# 本物の人体メッシュ（MakeHuman hm08、CC0。tools/mh_body.py）の関節に、部品の関節・中心を合わせる
sys.path.insert(0, str(Path(__file__).resolve().parent))
import mh_body  # noqa: E402

BODY = mh_body.build()
_J = BODY["joints"]


def _mid(a, b):
    return tuple((np.asarray(a) + np.asarray(b)) / 2)


def _fit_seg():
    J = _J
    hand = lambda s: tuple(np.asarray(J[f"wrist_{s}"]) + np.array([0, 0, -0.17]))
    upd = {
        "pelvis": (J["pelvis_c"], J["pelvis_c"]),
        "chest": (J["lumbar"], _mid(J["lumbar"], J["neck"])),
        "head": (J["neck"], J["head_c"]),
        "hair": (tuple(np.asarray(J["head_c"]) + [0, 0.03, 0.0]), tuple(np.asarray(J["head_c"]) + [0, 0.07, -0.16])),
    }
    for s in "rl":
        upd[f"uarm_{s}"] = (J[f"shoulder_{s}"], _mid(J[f"shoulder_{s}"], J[f"elbow_{s}"]))
        upd[f"farm_{s}"] = (J[f"elbow_{s}"], _mid(J[f"elbow_{s}"], hand(s)))
        upd[f"thigh_{s}"] = (J[f"hip_{s}"], _mid(J[f"hip_{s}"], J[f"knee_{s}"]))
        upd[f"shin_{s}"] = (J[f"knee_{s}"], _mid(J[f"knee_{s}"], J[f"ankle_{s}"]))
    for k, (j, c) in upd.items():
        p, _, _, m, sh, d = SEG[k]
        SEG[k] = (p, tuple(float(x) for x in j), tuple(float(x) for x in c), m, sh, d)


_fit_seg()


# ---------------------------------------------------------------- 小道具
def rx(d):
    return np.array(Matrix.Rotation(np.deg2rad(d), 3, "X"))


def ry(d):
    return np.array(Matrix.Rotation(np.deg2rad(d), 3, "Y"))


def rz(d):
    return np.array(Matrix.Rotation(np.deg2rad(d), 3, "Z"))


def aim(a, b):
    """向き a を向き b へ回す最短の回転"""
    q = Vector(a).normalized().rotation_difference(Vector(b).normalized())
    return np.array(q.to_matrix())


def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return float(t * t * (3 - 2 * t))


def ease_in(e0, e1, x):
    t = float(np.clip((x - e0) / (e1 - e0), 0, 1))
    return t * t


def lerp(a, b, k):
    return a + (b - a) * k


def proj(p):
    """世界の点 → 画面 (x, y)"""
    X, Y, Z = p
    return CX + F_PX * X / Y, HORIZON - F_PX * (Z - CAM_H) / Y


def rail_point_on_path():
    """足もとから視線の奥へ下がる道と、手すりの線の交点"""
    u = np.array([FEET0[0] / FEET0[1], 1.0])
    u = u / np.linalg.norm(u)
    A = np.array([u, -RAIL_D]).T
    s = np.linalg.solve(A, RAIL_P0 - FEET0)
    return FEET0 + u * s[0], u


# ---------------------------------------------------------------- 姿勢（運動学：受け渡し〜手すりに腰かけるまで）
def fk(root_pos, root_R, local, g=1.0):
    """root_pos: 骨盤の中心の世界位置、root_R: 骨盤の向き、local: {部品: 親に対する回転}。返すのは {部品: 4×4（立ち姿の座標 → 世界）}"""
    T = {}
    for name in ORDER:
        parent, joint, ctr, *_ = SEG[name]
        R = local.get(name, np.eye(3))
        j = np.array(joint) * SCALE
        if parent is None:
            M = np.eye(4)
            M[:3, :3] = g * root_R @ R
            M[:3, 3] = root_pos - M[:3, :3] @ (np.array(ctr) * SCALE)
        else:
            L = np.eye(4)
            L[:3, :3] = R
            L[:3, 3] = j - R @ j
            M = T[parent] @ L
        T[name] = M
    return T


def lowest(T):
    """足（かかと・つま先）のいちばん低い z"""
    zs = []
    for s in ("shin_l", "shin_r"):
        x = -0.08 if s.endswith("r") else 0.08
        for p in ((x, 0.03, 0.0), (x, -0.15, 0.0)):
            zs.append((T[s] @ np.array([*(np.array(p) * SCALE), 1.0]))[2])
    return min(zs)


FIT_P = OUTD / "fit.json"                                               # 受け渡しの形を _1 の影に合わせた値（fit で求める）
FIT0 = {"ua": [-0.63, -0.68, -0.37], "fa": [0.02, -0.62, 0.78], "ul": [0.08, 0.0, -1.0], "fl": -8.0,
        "s": 1.0, "tx": 0.0, "ty": 0.0, "wx": 1.0,
        "prof": [1.0] * 9, "gap": 0.0, "sy": 1.0, "hwid": 7.0}                                  # prof：高さごとの体の幅（腕を除く）、gap：脚を内へ寄せる量 (m)
PROF_Z = np.linspace(0.05, 1.50, 9)                    # s,tx,ty：受け渡しのコマで足もと (340,458) を中心に画面上で寄せる量（合成側で最初の 0.6 秒だけ使う）
FOOT_PX = (340.0, 458.0)
REST_V = BODY["verts"].copy()


def fitp():
    return {**FIT0, **(json.loads(FIT_P.read_text()) if FIT_P.exists() else {})}


def shape_verts(P):
    """立ち姿の頂点に、体型の合わせ（全体の幅・高さごとの幅・脚の寄せ）をかける"""
    v = REST_V.copy()
    Wt = BODY["W"]
    arm = Wt[:, [mh_body.SEGS.index(k) for k in ("uarm_r", "farm_r", "uarm_l", "farm_l")]].sum(1)
    leg = Wt[:, [mh_body.SEGS.index(k) for k in ("thigh_r", "shin_r", "thigh_l", "shin_l")]].sum(1)
    prof = np.interp(v[:, 2], PROF_Z, P["prof"])
    k = P["wx"] * (1 + (prof - 1) * (1 - arm))
    v[:, 0] = v[:, 0] * np.where(arm > 0.5, P["wx"], 1) + v[:, 0] * (k - np.where(arm > 0.5, P["wx"], 1)) * (1 - arm)
    v[:, 0] -= np.sign(v[:, 0]) * P["gap"] * leg * np.clip((0.80 - v[:, 2]) / 0.3, 0, 1)
    return v


BODY["verts"] = shape_verts(fitp())


def arm_wave_pose(P=None):
    """ep8_balcony_1 の手を振る姿：右腕（画面の左）は肩から横・前へ、肘から先は上へ。左腕は体の横に下ろす"""
    P = P or fitp()
    up = aim((0, 0, -1), P["ua"])
    fore = up.T @ aim((0, 0, -1), P["fa"])
    ul = aim((0, 0, -1), P["ul"])
    return {"uarm_r": up, "farm_r": fore, "uarm_l": ul, "farm_l": rx(P["fl"])}


def arms_up_pose():
    """両腕を上げて反る（ep8_balcony_3 の姿のこだま）"""
    pose = {}
    for side, sx in (("r", -1), ("l", 1)):
        pose[f"uarm_{side}"] = aim((0, 0, -1), (0.42 * sx, 0.10, 0.90))
        pose[f"farm_{side}"] = rx(-12)
    return pose


def blend_pose(a, b, k):
    out = {}
    for name in set(a) | set(b):
        qa = Matrix(a.get(name, np.eye(3)).tolist()).to_quaternion()
        qb = Matrix(b.get(name, np.eye(3)).tolist()).to_quaternion()
        out[name] = np.array(qa.slerp(qb, k).to_matrix())
    return out


def growth(t):
    """体の大きさの倍率（監査：窓から手すりまでの縮みを 2 割程度に）。絵の女の足もと (340,458) と手すりの線をそのまま使うと、
    遠近だけで 35% 縮む（絵そのものの奥行きの食い違い）。歩く間に体を 1.0 → G_END 倍へゆっくり大きくして、見た目の縮みを 16% に抑える。
    手すり（1.10m）に対して腰（股関節 0.78m × 1.3 ≒ 1.0m）がほぼ手すりの高さになり、腰を当てて後ろへ倒れられる"""
    return lerp(1.0, G_END, sstep(T_WALK[0], T_WALK[1] + 0.1, t))


def kinematic(t, P=None):
    """ループの頭 t=-PRE 〜 手を離す T_REL までの姿勢。t<0 は手を振る（絵の女と同じ姿勢、肘から先を振る）。返すのは {部品: 4×4}"""
    rail_pt, u = rail_point_on_path()
    face_end = -RAIL_N                                                     # 手すりに背を向ける
    yaw1 = np.rad2deg(np.arctan2(face_end[0], -face_end[1])) * 0.75
    P = P or fitp()
    if t < 0:                                                              # 手を振る：前腕を、カメラへ向かう軸のまわりに左右へ（最後の 0.15 秒は止まる）
        ph = 2 * np.pi * 1.4 * (t + PRE)
        w = 14 * np.sin(ph) * (1 - sstep(-0.35, -0.15, t))
        Q = dict(P, fa=list(np.array(Matrix.Rotation(np.deg2rad(w), 3, "Y")) @ np.array(P["fa"])))
        arms = arm_wave_pose(Q)
        t_ = 0.0
    else:
        t_ = t
        wave, down = arm_wave_pose(P), {"uarm_r": aim((0, 0, -1), (-0.14, 0.02, -0.99)), "uarm_l": aim((0, 0, -1), (0.14, 0.02, -0.99)),
                                       "farm_r": rx(-10), "farm_l": rx(-10)}
        arms = blend_pose(wave, down, sstep(*T_ARM, t))
        if t > T_SIT - 0.1:                                                # 倒れはじめ：腕は前（部屋の側）へ伸びる
            reach = {"uarm_r": aim((0, 0, -1), (-0.35, -0.70, -0.62)), "uarm_l": aim((0, 0, -1), (0.35, -0.70, -0.62)),   # つかもうとして：肩の高さで部屋の側（手前）へ、肘を曲げる
                     "farm_r": rx(-55), "farm_l": rx(-55)}
            arms = blend_pose(arms, reach, sstep(T_SIT - 0.1, T_REL, t))
    t = t_
    pose = dict(arms)
    walk_len = np.linalg.norm(rail_pt - FEET0) - 0.13 * G_END              # 尻が手すりに当たる所まで（当たりの箱が手すりにめり込まない距離）
    k = sstep(*T_WALK, t)
    dist = walk_len * k
    feet = FEET0 + u * dist
    yaw = lerp(0.0, yaw1, sstep(T_WALK[0], T_SIT, t))
    g = growth(t)
    step = 0.60 * g
    ph = np.pi * dist / step
    amp = 22.0 * min(1.0, dist / 0.25) * min(1.0, (walk_len - dist) / 0.2) if t < T_STOP else 0.0
    hip_r, hip_l = amp * np.sin(ph), -amp * np.sin(ph)
    kn_r = 38 * max(0.0, np.cos(ph)) ** 1.5 * (amp / 22)
    kn_l = 38 * max(0.0, -np.cos(ph)) ** 1.5 * (amp / 22)
    lean = 6 * (amp / 22)
    # 手すりに腰を当てて、つま先立ちで反りはじめる（加速しながら。手を離す瞬間の勢いを物理へ引き継ぐ）
    torso = lean - 50 * ease_in(T_SIT, T_REL, t)
    pose["thigh_r"] = rx(-hip_r - 10 * ease_in(T_SIT, T_REL, t))
    pose["thigh_l"] = rx(-hip_l - 6 * ease_in(T_SIT, T_REL, t))
    pose["shin_r"] = rx(kn_r + 12 * ease_in(T_SIT, T_REL, t))
    pose["shin_l"] = rx(kn_l + 6 * ease_in(T_SIT, T_REL, t))
    pose["chest"] = rx(torso * 0.6)
    pose["head"] = rx(-25 * ease_in(T_SIT, T_REL, t) + 4 * (amp / 22))
    pose["hair"] = rx(0)
    R = rz(yaw) @ rx(torso * 0.4)
    p_ground = np.array([feet[0], feet[1], 0.86])
    T = fk(p_ground, R, pose, g)
    p_ground[2] += -lowest(T) + 0.004                                      # 足は床に着く（浮かない・沈まない）
    e = ease_in(T_SIT, T_REL, t)                                           # 最後に床を蹴って、腰を手すりの角へ乗せる（後ろ向きの勢いのまま物理へ）
    p_ground[:2] += u * 0.04 * e
    p_ground[2] += 0.06 * e
    return fk(p_ground, R, pose, g)


# ---------------------------------------------------------------- 場面（手すり・床）
def rail_frame():
    M = np.eye(4)
    M[:3, 0] = [*RAIL_D, 0]
    M[:3, 1] = [*RAIL_N, 0]
    M[:3, 2] = [0, 0, 1]
    M[:2, 3] = RAIL_P0
    return M


def box(name, size, loc_local, coll=None):
    """手すりの座標（x=手すりに沿って、y=外向き、z=上）で箱を置く"""
    bpy.ops.mesh.primitive_cube_add(size=1)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = size
    ob.matrix_world = Matrix(rail_frame().tolist()) @ Matrix.Translation(loc_local) @ Matrix.Diagonal((*size, 1))
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if coll is not None:
        coll.objects.link(ob)
        bpy.context.scene.collection.objects.unlink(ob)
    return ob


def post_params():
    """背景の柱の x から、手すりに沿った位置 s を逆算"""
    out = []
    for px in POSTS_PX:
        a = (px - CX) / F_PX                                                # X/Y = a
        s = (a * RAIL_P0[1] - RAIL_P0[0]) / (RAIL_D[0] - a * RAIL_D[1])
        out.append(s)
    return out


def build_set(kind):
    """kind: 'holdout'（本番：手すり・床は透明な穴）／'debug'（横からの確認：灰色で見せる）／'solid'（キャリブレーションの重ね合わせ）"""
    parts = {}
    L = 30.0
    parts["top"] = box("rail_top", (L, 0.05, 0.045), (0, 0, RAIL_H - 0.0225))
    parts["mid"] = box("rail_mid", (L, 0.03, 0.025), (0, 0, RAIL_H - 0.12))
    parts["bot"] = box("rail_bot", (L, 0.03, 0.03), (0, 0, 0.105))
    parts["curb"] = box("rail_curb", (L, 0.12, 0.09), (0, 0, 0.045))
    parts["panel"] = box("rail_panel", (L, 0.01, RAIL_H - 0.12 - 0.12), (0, 0, (RAIL_H - 0.12 + 0.12) / 2))
    for i, s in enumerate(post_params()):
        parts[f"post{i}"] = box(f"post{i}", (0.045, 0.045, RAIL_H), (s, 0, RAIL_H / 2))
    parts["slab"] = box("slab", (L, 20.0, 0.3), (0, 0.15 - 10.0, -0.15))     # 部屋の床・ベランダの床（外の縁は手すりの 15cm 外）
    # 窓の下枠（敷居。越えた足もとを少し隠す）
    bpy.ops.mesh.primitive_cube_add(size=1)
    sill = bpy.context.active_object
    sill.name = "sill"
    c = (WIN_L + WIN_R) / 2
    sill.scale = (np.linalg.norm(WIN_R - WIN_L), 0.07, 0.035)
    sill.rotation_euler = (0, 0, np.arctan2(WIN_D[1], WIN_D[0]))
    sill.location = (c[0], c[1], 0.0175)
    parts["sill"] = sill
    mats = {}
    for name, ob in parts.items():
        if kind == "holdout":
            key = "panel" if name == "panel" else "hold"                     # すりガラスの板の向こうは 35% だけ透けて見える
        else:
            key = "debug_" + ("panel" if name == "panel" else "slab" if name == "slab" else "rail")
        if key not in mats:
            mats[key] = make_mat(key)
        ob.data.materials.append(mats[key])
    return parts


def make_mat(key):
    m = bpy.data.materials.new(key)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    if key == "hold":
        sh = nt.nodes.new("ShaderNodeHoldout")
        nt.links.new(sh.outputs[0], out.inputs[0])
    elif key == "panel":                                                    # すりガラスの板：向こうの影は半分ほど透けて見える
        h = nt.nodes.new("ShaderNodeHoldout")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mx = nt.nodes.new("ShaderNodeMixShader")
        mx.inputs[0].default_value = 0.65
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(h.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs[0])
    else:
        if key in ("lace", "lacehold"):
            return lace_mat(m, key)
        col = {"body": (0, 0, 0), "debug_rail": (0.25, 0.3, 0.45), "debug_panel": (0.6, 0.7, 0.85), "debug_slab": (0.55, 0.5, 0.45),
               "solid": (1, 1, 1)}[key]
        e = nt.nodes.new("ShaderNodeEmission")
        e.inputs[0].default_value = (*col, 1)
        e.inputs[1].default_value = 1.0
        nt.links.new(e.outputs[0], out.inputs[0])
    return m


def lace_mat(m, key):
    """薄いレース：半分ほど透け、窓の光を通して白く光る。lacehold は女の影の側で使う（レースの向こうの影を半分ほど隠す）"""
    nt = m.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader")
    if key == "lacehold":
        h = nt.nodes.new("ShaderNodeHoldout")
        mx.inputs[0].default_value = 0.42
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(h.outputs[0], mx.inputs[2])
    else:
        tl = nt.nodes.new("ShaderNodeBsdfTranslucent")
        tl.inputs[0].default_value = (1, 0.97, 0.93, 1)
        df = nt.nodes.new("ShaderNodeBsdfDiffuse")
        df.inputs[0].default_value = (0.9, 0.86, 0.82, 1)
        m2 = nt.nodes.new("ShaderNodeMixShader")
        m2.inputs[0].default_value = 0.35
        nt.links.new(tl.outputs[0], m2.inputs[1])
        nt.links.new(df.outputs[0], m2.inputs[2])
        # 布の面が視線と平行に近い所（ひだ・縁）ほど濃く見える
        lw = nt.nodes.new("ShaderNodeLayerWeight")
        lw.inputs[0].default_value = 0.35
        ramp = nt.nodes.new("ShaderNodeMath")
        ramp.operation = "MULTIPLY_ADD"
        ramp.inputs[1].default_value = 0.5
        ramp.inputs[2].default_value = 0.16
        nt.links.new(lw.outputs["Facing"], ramp.inputs[0])
        nt.links.new(ramp.outputs[0], mx.inputs[0])
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(m2.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])
    m.use_backface_culling = False
    return m


def camera(name="cam", loc=(0, 0, CAM_H), rot=(90, 0, 0), f_px=F_PX, shift_y=(HORIZON - H / 2) / W, ortho=None):
    cd = bpy.data.cameras.new(name)
    cd.sensor_fit = "HORIZONTAL"
    cd.sensor_width = 36
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    else:
        cd.lens = f_px * 36 / W
    cd.shift_y = shift_y
    cd.clip_start, cd.clip_end = 0.05, 200
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = [np.deg2rad(a) for a in rot]
    return ob


def setup_render(sc, samples=16, transparent=True):
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 0
    sc.cycles.transparent_max_bounces = 8
    sc.cycles.pixel_filter_type = "BLACKMAN_HARRIS"
    sc.cycles.filter_width = 1.0                                           # 縁は 1px のアンチエイリアスだけ（暗い輪を出さない）
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    if sc.world is None:
        sc.world = bpy.data.worlds.new("w")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (1, 1, 1, 1)
    bg.inputs[1].default_value = 1.0


def render_rgba(sc, path):
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    from PIL import Image
    return np.asarray(Image.open(path), np.float32) / 255


# ---------------------------------------------------------------- 1. キャリブレーションの確認
def calib():
    from PIL import Image, ImageDraw
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    setup_render(sc, samples=4)
    build_set("solid")
    for ob in bpy.data.objects:
        if ob.type == "MESH":
            ob.data.materials.clear()
            ob.data.materials.append(make_mat("solid"))
    bpy.data.objects["slab"].hide_render = True
    sc.camera = camera()
    T = kinematic(0.0)
    body = build_body(sc)
    pose_body(body, T)
    tmp = OUTD / "tmp_calib.png"
    rgba = render_rgba(sc, tmp)
    plate = Image.open(ROOT / "assets" / "ep8_balcony_0.png").convert("RGB").resize((W, H))
    fig = Image.open(ROOT / "assets" / "ep8_balcony_1.png").convert("RGB").resize((W, H))
    a = np.asarray(plate, np.float32)
    al = rgba[..., 3]
    from scipy.ndimage import binary_erosion
    edge = (al > 0.5) & ~binary_erosion(al > 0.5, iterations=1)
    a[edge] = [255, 40, 40]
    # 女の影（_1）の輪郭も重ねる（緑）。受け渡しのコマの形の確かめ
    f1 = np.asarray(fig, np.float32).mean(-1)
    p0 = a.mean(-1)
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(out)
    d.line([(0, HORIZON), (W, HORIZON)], fill=(80, 200, 255))
    for (x0, y0, x1, y1) in ((130, 297, 430, 319), (240, 415, 430, 403)):
        d.line([(x0, y0), (x1, y1)], fill=(255, 255, 0))
    out.save(OUTD / "calib_overlay.png")
    # 受け渡しの形：_1 の影（緑）と、物理の女の最初のコマ（赤）
    m1 = (np.asarray(fig, np.float32).mean(-1) < 22)
    b = np.asarray(fig, np.float32) * 0.6
    b[m1 & ~(al > 0.5)] = [40, 220, 40]
    b[(al > 0.5) & ~m1] = [230, 40, 40]
    b[(al > 0.5) & m1] = [240, 240, 240]
    Image.fromarray(np.clip(b, 0, 255).astype(np.uint8)).crop((180, 150, 520, 480)).resize((680, 660)).save(OUTD / "calib_handoff.png")
    print("calib", OUTD / "calib_overlay.png")


# ---------------------------------------------------------------- 体（見た目のメタボール）
HAIR_N, HAIR_P = 140, 12                                                # 髪の束の数と、1本の節の数


def hair_roots():
    """頭の座標（立ち姿）での髪の生え際の点と、垂れる長さ。頭の後ろ半分と横から、肩甲骨の下あたりまで"""
    rg = np.random.default_rng(8)
    hc = np.array(_J["head_c"])
    pts, lens = [], []
    for k in range(HAIR_N):
        th = np.deg2rad(rg.normal(0, 55)) if k % 3 else np.deg2rad(rg.uniform(-120, 120))   # 0 = 真後ろ（後ろに多く、量のある長い髪）
        el = np.deg2rad(rg.uniform(-25, 60))
        d = np.array([np.sin(th) * np.cos(el), np.cos(th) * np.cos(el), np.sin(el)])
        pts.append(hc + d * np.array([0.085, 0.10, 0.11]) + [0, 0.0, 0.01])
        lens.append((0.44 if abs(th) < 1.2 else 0.34) * rg.uniform(0.85, 1.08))
    return np.array(pts), np.array(lens)


def strand_sim(poses, roots, lens, seg_name, colliders, init_dir, n_pts, plane_from=None):
    """ひも（髪の束・ワンピースの裾の筋）を、節をつないだベルレ積分で動かす：長さの拘束・曲げのこわさ・空気の抵抗・体との当たり。
    roots は seg_name の部品の立ち姿の座標。colliders(T) は [(中心, 半径)]。1/120 秒ごと。落ちる間は空気の抵抗で上へなびく。返すのは (コマ, 本, 節, 3)"""
    seg = lens / (n_pts - 1)
    dt = 1 / SIM_FPS / 8
    g = np.array([0, 0, -9.81])
    nst = len(roots)

    def anchors(T):
        return (np.c_[roots, np.ones(nst)] @ T[seg_name].T)[:, :3]

    T0 = poses[0]
    a0 = anchors(T0)
    out = []
    pre = 240                                                          # はじめの姿勢のまま 2 秒なじませてから使う
    poses = [poses[0]] * pre + list(poses)
    x = np.zeros((nst, n_pts, 3))
    d0 = init_dir(T0, a0)
    gscale = np.linalg.norm(T0[seg_name][:3, 0])
    for j in range(n_pts):
        x[:, j] = a0 + d0 * (seg[:, None] * j * gscale)
    xp = x.copy()
    N3 = np.array([*RAIL_N, 0.0])
    o0 = np.array([*RAIL_P0, 0.0])
    for fi, T in enumerate(poses):
        a = anchors(T)
        gs = np.linalg.norm(T[seg_name][:3, 0])
        wall = plane_from is not None and fi - pre >= plane_from
        sg = seg * gs
        cols = colliders(T)
        for _ in range(8):
            v = (x - xp) * 0.998
            sp = np.linalg.norm(v, axis=-1, keepdims=True)
            v = v * np.minimum(1, 0.03 / np.maximum(sp, 1e-9))
            xp = x.copy()
            x = x + v + g * dt * dt - v * 0.004                        # 空気の抵抗（落ちる間は上へなびく）
            x[:, 0] = a
            for _ in range(6):
                d = x[:, 1:] - x[:, :-1]
                L = np.linalg.norm(d, axis=-1, keepdims=True) + 1e-9
                corr = (L - sg[:, None, None]) / L * d * 0.5
                x[:, 1:] -= corr
                x[:, :-1] += corr
                x[:, 0] = a
                d = x[:, 2:] - x[:, :-2]                                # 曲げのこわさ（とげのように折れない）
                L = np.linalg.norm(d, axis=-1, keepdims=True) + 1e-9
                corr = (L - 1.9 * sg[:, None, None]) / L * d * 0.15
                x[:, 2:] -= np.where(L < 1.9 * sg[:, None, None], corr, 0)
                x[:, :-2] += np.where(L < 1.9 * sg[:, None, None], corr, 0)
                x[:, 0] = a
            for c, r in cols:                                           # 体の中へは入らない（根元の節は除く）
                d = x[:, 1:] - c
                L = np.linalg.norm(d, axis=-1, keepdims=True) + 1e-9
                x[:, 1:] = np.where(L < r, c + d / L * r, x[:, 1:])
            if wall:                                                    # 手すりを越えはじめたら、笠木より下の部屋の側（ガラスの手前）へは垂れない：すりガラスの板の外側に沿う
                od = (x - o0) @ N3
                bad = (od < 0.03) & (x[..., 2] < RAIL_H + 0.02)
                x = x + (np.where(bad, 0.03 - od, 0.0))[..., None] * N3
        out.append(x.copy())
    return np.array(out[pre:])


def _pt(T, n, p):
    return (T[n] @ np.array([*p, 1]))[:3]


def hair_sim(poses):
    """髪：肩下まで（_1 の女に合わせた量）。頭と胴に当たる"""
    roots, lens = hair_roots()

    def cols(T):
        gs = np.linalg.norm(T["head"][:3, 0])
        return [(_pt(T, "head", _J["head_c"]), 0.09 * gs), (_pt(T, "chest", SEG["chest"][2]), 0.11 * gs)]

    def init(T, a0):
        back = T["chest"][:3, :3] @ np.array([0, 1, 0])
        return back / np.linalg.norm(back) * 0.04 + np.array([0, 0, -1.0])
    return strand_sim(poses, roots, lens, "head", cols, init, HAIR_P, REL_IDX if len(poses) > REL_IDX else None)


SKIRT_N, SKIRT_P = 60, 9


def skirt_roots():
    """ワンピースの裾の筋：腰回り（骨盤の座標、高さ 0.95m）から膝（0.45m）まで"""
    ang = np.linspace(0, 2 * np.pi, SKIRT_N, endpoint=False)
    z = 0.95
    r = np.array([0.130, 0.100])
    pts = np.stack([np.cos(ang) * r[0], np.sin(ang) * r[1], np.full(SKIRT_N, z)], 1)
    return pts, np.full(SKIRT_N, 0.50)


def skirt_sim(poses):
    roots, lens = skirt_roots()

    def cols(T):
        gs = np.linalg.norm(T["pelvis"][:3, 0])
        out = [(_pt(T, "pelvis", SEG["pelvis"][2]), 0.15 * gs)]
        for sd in "rl":
            for k in np.linspace(0, 1, 4):
                out.append((_pt(T, f"thigh_{sd}", np.array(_J[f"hip_{sd}"]) * (1 - k) + np.array(_J[f"knee_{sd}"]) * k), (0.085 - 0.03 * k) * gs))
            out.append((_pt(T, f"shin_{sd}", np.array(_J[f"knee_{sd}"]) * 0.6 + np.array(_J[f"ankle_{sd}"]) * 0.4), 0.05 * gs))
        return out

    def init(T, a0):
        c = _pt(T, "pelvis", SEG["pelvis"][2])
        d = a0 - c
        d[:, 2] = 0
        d = d / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-9)
        return d * 0.18 + np.array([0, 0, -1.0])
    return strand_sim(poses, roots, lens, "pelvis", cols, init, SKIRT_P, REL_IDX if len(poses) > REL_IDX else None)


def build_body(sc):
    """人体のメッシュ（皮膚付き）と髪のメッシュ。返すのは {"body": 物体, "hair": 物体}"""
    mat = make_mat("body")
    me = bpy.data.meshes.new("woman")
    f = BODY["faces"]
    faces = [list(q) if q[2] != q[3] else list(q[:3]) for q in f]
    me.from_pydata(BODY["verts"].tolist(), [], faces)
    me.materials.append(mat)
    ob = bpy.data.objects.new("woman", me)
    sc.collection.objects.link(ob)
    mod = ob.modifiers.new("smooth", "SUBSURF")
    mod.levels = mod.render_levels = 1
    hv = np.zeros((HAIR_N * HAIR_P * 2, 3))
    hf = []
    for k in range(HAIR_N):
        for j in range(HAIR_P - 1):
            i0 = (k * HAIR_P + j) * 2
            hf.append([i0, i0 + 1, i0 + 3, i0 + 2])
    hm = bpy.data.meshes.new("hair")
    hm.from_pydata(hv.tolist(), [], hf)
    hm.materials.append(mat)
    oh = bpy.data.objects.new("hair", hm)
    sc.collection.objects.link(oh)
    sm = bpy.data.meshes.new("skirt")                                    # ワンピースの裾：筋どうしを面でつないだ筒
    sm.from_pydata(np.zeros((SKIRT_N * SKIRT_P, 3)).tolist(), [], skirt_faces())
    sm.materials.append(mat)
    osk = bpy.data.objects.new("skirt", sm)
    sc.collection.objects.link(osk)
    return {"body": ob, "hair": oh, "skirt": osk}


def skirt_faces():
    f = []
    for k in range(SKIRT_N):
        k2 = (k + 1) % SKIRT_N
        for j in range(SKIRT_P - 1):
            f.append([k * SKIRT_P + j, k2 * SKIRT_P + j, k2 * SKIRT_P + j + 1, k * SKIRT_P + j + 1])
    return f


def ribbon(hp, eye):
    """髪のひもを、見るカメラの方を向いた幅のある帯にする"""
    t = np.gradient(hp, axis=1)
    vd = hp - eye
    side = np.cross(t, vd)
    side /= np.linalg.norm(side, axis=-1, keepdims=True) + 1e-9
    w = np.linspace(0.034, 0.016, HAIR_P)[None, :, None] * fitp().get("hwid", 7.0) / 8.5
    return np.stack([hp - side * w, hp + side * w], 2).reshape(-1, 3)


def pose_body(objs, T, hp=None, eye=(0, 0, CAM_H), sp=None):
    v = mh_body.skin(BODY, T, None)
    me = objs["body"].data
    me.vertices.foreach_set("co", v.ravel())
    me.update()
    oh = objs["hair"]
    if hp is None:
        oh.hide_render = True
    else:
        oh.hide_render = False
        oh.data.vertices.foreach_set("co", ribbon(hp, np.array(eye)).ravel())
        oh.data.update()
    osk = objs.get("skirt")
    if osk is not None:
        osk.hide_render = sp is None
        if sp is not None:
            osk.data.vertices.foreach_set("co", sp.reshape(-1, 3).ravel())
            osk.data.update()


# ---------------------------------------------------------------- 2. 物理（手すりに腰かけたところから）
def pivot_fall():
    """手すりを越える所（再監査の直し）：腰（脚の付け根）を手すりの笠木の高さに置いたまま、笠木を軸に後ろへ回る。
    角度 θ(t) = OMEGA0·t + ½·ALPHA·t²（反る勢い＋重心が外へ出てからの重力の加速）。
    上半身は、頭が笠木の真下（外側）に来た所で止まって外に垂れ、脚はそのまま回り続けて真上（頂点）を越え、外側へ回り込んで消える。
    脚が外に垂れきったら、体ごと真下へ落ちる。返すのは 1/120 秒ごとの {部品: 4×4} の列（T_REL から）"""
    T0 = kinematic(T_REL)
    pts = {n: (T0[n] @ np.array([*SEG[n][2], 1]))[:3] for n in ORDER}
    pel = pts["pelvis"]
    s_ = (pel[:2] - RAIL_P0) @ RAIL_D
    piv = np.array([*(RAIL_P0 + RAIL_D * s_), RAIL_H])
    N3 = np.array([*RAIL_N, 0.0])
    axis = np.cross([0, 0, 1.0], N3)
    axis /= np.linalg.norm(axis)
    rot = lambda th: np.array(Matrix.Rotation(th, 3, Vector(axis)))
    upper = {"pelvis", "chest", "head", "hair", "uarm_r", "farm_r", "uarm_l", "farm_l"}

    def lim(v):
        """v（軸からのベクトル）が真下より少し外を向く角度（最初にそうなる θ）"""
        for th in np.linspace(0, 2 * np.pi, 2000):
            w = rot(th) @ v
            if w[2] < 0 and (w @ N3) > 0 and abs(w @ N3) < 0.25 * abs(w[2]):
                return th
        return np.pi
    head_v = _pt(T0, "head", SEG["head"][2]) - piv
    ank = max((_pt(T0, f"shin_{sd}", _J[f"ankle_{sd}"]) for sd in "rl"), key=lambda p: -p[2])
    th_up = lim(head_v)
    av = ank - piv
    ths = np.linspace(0, 2 * np.pi, 2000)
    th_apex = ths[int(np.argmax([(rot(t) @ av)[2] for t in ths]))]          # 脚が真上（頂点）になる角度
    th_leg = th_apex + np.deg2rad(75)                                     # 頂点を越えて外へ倒れた所で、体ごと落ちる
    out = []
    n = int(round((T_END - T_REL) * SIM_FPS)) + 2
    t_drop = None
    for k in range(n):
        t = k / SIM_FPS
        th = OMEGA0 * t + 0.5 * ALPHA * t * t
        drop = np.zeros(3)
        if th >= th_leg:
            if t_drop is None:
                t_drop = t
            td = t - t_drop
            drop = np.array([0, 0, -0.5 * 9.81 * td * td - 1.5 * td]) + N3 * 1.2 * td
        T = {}
        for nm in ORDER:
            R = rot(min(th, th_up if nm in upper else th_leg))
            Mx = np.eye(4)
            Mx[:3, :3] = R
            Mx[:3, 3] = piv - R @ piv + drop
            T[nm] = Mx @ T0[nm]
        out.append(T)
    print("手すりを越える：上半身が垂れる", round(np.rad2deg(th_up)), "°、脚が回りきる", round(np.rad2deg(th_leg)), "°、",
          round(t_drop or 0, 2), "秒")
    return out


def unscaled(M, p):
    """立ち姿の座標の点 p を中心にした、大きさを外した 4×4（剛体は大きさを持たせず、寸法のほうを G_END 倍にする）"""
    R = M[:3, :3] / np.linalg.norm(M[:3, :3], axis=0)
    out = np.eye(4)
    out[:3, :3] = R
    out[:3, 3] = M[:3, :3] @ np.asarray(p, float) + M[:3, 3]
    return out


def simulate():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = SIM_FPS
    n = int(round((T_END - T_REL) * SIM_FPS)) + 3
    sc.frame_start, sc.frame_end = 1, n
    bpy.ops.rigidbody.world_add()
    rw = sc.rigidbody_world
    rw.substeps_per_frame = 10                                              # 1200Hz
    rw.solver_iterations = 80
    rw.point_cache.frame_start, rw.point_cache.frame_end = 1, n
    col = bpy.data.collections.new("rb")
    sc.collection.children.link(col)
    # 当たり：手すり（一枚の板として）・床
    rail = box("rail_col", (30, 0.05, RAIL_H), (0, 0, RAIL_H / 2))
    slab = box("slab_col", (30, 20.0, 0.3), (0, 0.15 - 10.0, -0.15))
    for ob in (rail, slab):
        bpy.context.view_layer.objects.active = ob
        bpy.ops.rigidbody.object_add()
        ob.rigid_body.type = "PASSIVE"
        ob.rigid_body.friction = 0.25 if ob is rail else 0.6              # 手すりの丸い笠木の上は、体がすべって越える
        ob.rigid_body.collision_shape = "BOX"
        ob.rigid_body.collision_margin = 0.002
    T = kinematic(T_REL)
    # 手を離す直前の動き（腕を上げる・反る）の速さを、物理の最初の速さとして渡すため、1/120 秒前の姿勢も取っておく
    Tp = kinematic(T_REL - 1 / SIM_FPS)
    Tpp = kinematic(T_REL - 2 / SIM_FPS)
    bodies = {}
    for name in ORDER:
        parent, joint, ctr, mass, shape, dims = SEG[name]
        bpy.ops.mesh.primitive_cube_add(size=1)
        ob = bpy.context.active_object
        ob.name = "rb_" + name
        ob.scale = np.array(dims) * G_END
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        ob.matrix_world = Matrix(unscaled(T[name], ctr).tolist())
        bpy.ops.rigidbody.object_add()
        rb = ob.rigid_body
        rb.type = "ACTIVE"
        rb.mass = mass * G_END ** 2
        rb.collision_shape = shape
        rb.collision_margin = 0.003
        rb.friction = 0.5
        rb.restitution = 0.0
        rb.linear_damping = 0.02
        rb.angular_damping = 0.25 if name != "hair" else 0.6
        bodies[name] = ob
    # 関節（立ち姿からの可動域を、腰かけた姿勢からの差に直して与える）。すべて親の向きにそろえた空の物体で
    lim = {  # 部品: (x の範囲, y の範囲, z の範囲)  度、手を離す瞬間の姿勢からの差
        "chest": ((-25, 20), (-12, 12), (-15, 15)),
        "head": ((-35, 45), (-25, 25), (-40, 40)),
        "hair": ((-70, 50), (-25, 25), (-15, 15)),
        "uarm_r": ((-80, 80), (-70, 70), (-60, 60)), "uarm_l": ((-80, 80), (-70, 70), (-60, 60)),
        "farm_r": ((-130, 12), (0, 0), (-10, 10)), "farm_l": ((-130, 12), (0, 0), (-10, 10)),
        "thigh_r": ((-25, 30), (-10, 20), (-15, 15)), "thigh_l": ((-25, 30), (-20, 10), (-15, 15)),   # 落ちる人は体をこわばらせる：脚は体と一緒に回る
        "shin_r": ((-5, 45), (0, 0), (0, 0)), "shin_l": ((-5, 45), (0, 0), (0, 0)),
    }
    for name in ORDER:
        parent = SEG[name][0]
        if parent is None:
            continue
        Mj = unscaled(T[parent], SEG[name][1])
        e = bpy.data.objects.new("j_" + name, None)
        sc.collection.objects.link(e)
        e.matrix_world = Matrix(Mj.tolist())
        bpy.context.view_layer.objects.active = e
        bpy.ops.rigidbody.constraint_add()
        c = e.rigid_body_constraint
        c.type = "GENERIC"
        c.object1, c.object2 = bodies[parent], bodies[name]
        c.disable_collisions = True
        c.use_breaking = False
        for ax in "xyz":
            setattr(c, f"use_limit_lin_{ax}", True)
            setattr(c, f"limit_lin_{ax}_lower", 0)
            setattr(c, f"limit_lin_{ax}_upper", 0)
        for ax, (lo, hi) in zip("xyz", lim[name]):
            setattr(c, f"use_limit_ang_{ax}", True)
            setattr(c, f"limit_ang_{ax}_lower", np.deg2rad(lo))
            setattr(c, f"limit_ang_{ax}_upper", np.deg2rad(hi))
    # 隣どうしでない部品の重なりで弾けないよう、髪と胸・腕と胸・ももどうしも当たりを切る（関節なしの自由な拘束）
    for a, b in (("hair", "chest"), ("hair", "uarm_r"), ("hair", "uarm_l"), ("thigh_r", "thigh_l"), ("uarm_r", "head"), ("uarm_l", "head"),
                 ("farm_r", "head"), ("farm_l", "head"), ("farm_r", "hair"), ("farm_l", "hair"), ("shin_r", "shin_l")):
        e = bpy.data.objects.new(f"nc_{a}_{b}", None)
        sc.collection.objects.link(e)
        bpy.context.view_layer.objects.active = e
        bpy.ops.rigidbody.constraint_add()
        c = e.rigid_body_constraint
        c.type = "GENERIC"
        c.object1, c.object2 = bodies[a], bodies[b]
        c.disable_collisions = True
    # 手を離す直前の動きを渡す：最初の3コマだけ「動かされる物体」として 2/120 秒前 → 1/120 秒前 → 今の姿勢を通す（Bullet がその速さを引き継ぐ。2コマでは引き継がれない）
    for name, ob in bodies.items():
        for fr, TT in ((1, Tpp), (2, Tp), (3, T)):
            ob.matrix_world = Matrix(unscaled(TT[name], SEG[name][2]).tolist())
            ob.keyframe_insert("location", frame=fr)
            ob.keyframe_insert("rotation_euler", frame=fr)
            ob.rigid_body.kinematic = True
            ob.rigid_body.keyframe_insert("kinematic", frame=fr)
        ob.rigid_body.kinematic = False
        ob.rigid_body.keyframe_insert("kinematic", frame=4)
    out = []
    for f in range(1, n + 1):
        sc.frame_set(f)
        out.append({name: np.array(ob.matrix_world) for name, ob in bodies.items()})
    # 部品の物体の行列（中心）→ 立ち姿の座標からの 4×4 へ
    track = []
    for st in out[2:]:                                                       # フレーム3 = 手を離す瞬間 (T_REL)
        T2 = {}
        for name, M in st.items():
            c = np.array(SEG[name][2]) * SCALE
            Mm = np.array(M)
            R = Mm[:3, :3] / np.linalg.norm(Mm[:3, :3], axis=0)
            T2[name] = np.eye(4)
            T2[name][:3, :3] = R * G_END
            T2[name][:3, 3] = Mm[:3, 3] - R * G_END @ c
        track.append(T2)
    return track


# ---------------------------------------------------------------- 2b. カーテン（クロス）
CLOTH_W, CLOTH_H, CLOTH_NX, CLOTH_NY = 1.05, 2.42, 26, 48


def cloth_bake():
    """窓の左右に吊った薄いレース2枚。上辺はレールに固定（ひだを付けて吊る）。外から部屋の中へ吹く風（基本 0.6 ＋ 4.6 秒周期の突風）。
    30fps で 3 周期（13.8 秒）回し、最後の 2 周期（9.2 秒）をループに使う。返すのは (コマ, 頂点, 3) と面"""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    n = int(round(3 * GUST_T * FPS)) + 1
    sc.frame_start, sc.frame_end = 1, n
    obs = []
    for side, s0 in (("L", 0.05), ("R", np.linalg.norm(WIN_R - WIN_L) - 0.05 - CLOTH_W)):
        bpy.ops.mesh.primitive_grid_add(x_subdivisions=CLOTH_NX, y_subdivisions=CLOTH_NY, size=1)
        ob = bpy.context.active_object
        ob.name = "curtain" + side
        me = ob.data
        for v in me.vertices:
            u, w = v.co.x + 0.5, v.co.y + 0.5                              # u: 横 0..1、w: 下 0..上 1
            s_ = s0 + u * CLOTH_W
            pleat = 0.03 * np.sin(u * CLOTH_NX * np.pi / 2)               # 吊ったひだ
            p = WIN_L + WIN_D * s_ + WIN_IN * (0.10 + pleat)
            v.co = (p[0], p[1], WIN_TOP - 0.05 - (1 - w) * CLOTH_H)
        vg = ob.vertex_groups.new(name="rail")
        vg.add([v.index for v in me.vertices if v.co.z > WIN_TOP - 0.06], 1.0, "REPLACE")
        cl = ob.modifiers.new("cloth", "CLOTH")
        st = cl.settings
        st.quality = 8
        st.mass = 0.05 * CLOTH_W * CLOTH_H / len(me.vertices) * 10
        st.air_damping = 1.0
        st.tension_stiffness = st.compression_stiffness = 8
        st.bending_stiffness = 0.4                                         # 裾が絡まって束にならない程度のこし
        st.vertex_group_mass = "rail"
        cl.collision_settings.use_self_collision = False
        cl.point_cache.frame_start, cl.point_cache.frame_end = 1, n
        obs.append(ob)
    # 床と窓の外の壁（カーテンが窓の外へ抜けないよう、窓の面の少し外に）
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 5, 0.0))
    bpy.ops.object.modifier_add(type="COLLISION")
    bpy.ops.object.effector_add(type="WIND", location=(*(WIN_L + WIN_R) / 2, 1.2))
    wind = bpy.context.active_object
    d3 = Vector((*WIN_IN, 0.0))
    wind.rotation_euler = Vector((0, 0, 1)).rotation_difference(d3).to_euler()   # 風（ローカル Z）を部屋の中へ
    wind.field.flow = 0.6
    wind.field.noise = 0.5
    for f in range(1, n + 1, 2):
        t = (f - 1) / FPS
        ph = ((t - 1.45) % GUST_T) / GUST_T
        g = np.sin(ph / 0.25 * np.pi / 2) ** 2 if ph < 0.25 else np.exp(-(ph - 0.25) * 5.0)
        wind.field.strength = 95 * (0.35 + 0.65 * g)                       # 突風で裾ほど大きく部屋の側へ（30〜60cm）、抜けると垂れて開く
        wind.field.keyframe_insert("strength", frame=f)
    dg = bpy.context.evaluated_depsgraph_get()
    frames = []
    for f in range(1, n + 1):
        sc.frame_set(f)
        vv = []
        for ob in obs:
            m = ob.evaluated_get(dg).to_mesh()
            vv.append(np.array([v.co[:] for v in m.vertices]) @ np.array(ob.matrix_world)[:3, :3].T + np.array(ob.matrix_world)[:3, 3])
            ob.evaluated_get(dg).to_mesh_clear()
        frames.append(np.concatenate(vv))
    faces = []
    nv = len(obs[0].data.vertices)
    for k, ob in enumerate(obs):
        faces += [[i + k * nv for i in p.vertices] for p in ob.data.polygons]
    frames = np.array(frames)
    start = n - int(round(LOOP * FPS)) - 1
    np.savez(OUTD / "cloth.npz", verts=frames, faces=np.array(faces), start=start)
    print("cloth", frames.shape, "start", start)


def cloth_frame(C, i):
    """ループの i コマ目（0..275）のカーテンの頂点。継ぎ目の 0.4 秒は、1周前の同じ時刻の形と混ぜて、周期をつなぐ"""
    L = int(round(LOOP * FPS))
    i %= L
    v = C["verts"][C["start"] + i]
    k = (i - (L - 12)) / 12
    if k > 0:
        v = v * (1 - k) + C["verts"][C["start"] + i - L] * k
    return v


# ---------------------------------------------------------------- 3. 書き出し
def all_poses(track):
    """1/120 秒おきの、受け渡しから終わりまでの姿勢の列"""
    n_k = int(round((PRE + T_REL) * SIM_FPS))
    poses = [kinematic(i / SIM_FPS - PRE) for i in range(n_k)] + track
    return poses


def build_curtains(sc, C):
    me = bpy.data.meshes.new("curtains")
    me.from_pydata(C["verts"][C["start"]].tolist(), [], C["faces"].tolist())
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new("curtains", me)
    sc.collection.objects.link(ob)
    return ob


def set_mat(ob, m):
    ob.data.materials.clear()
    ob.data.materials.append(m)


def render_views(poses):
    from PIL import Image
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    setup_render(sc, samples=12)
    body = build_body(sc)
    hold = build_set("holdout")
    C = dict(np.load(OUTD / "cloth.npz"))
    curt = build_curtains(sc, C)
    m_body, m_hold, m_lace, m_lacehold = make_mat("body"), make_mat("hold"), make_mat("lace"), make_mat("lacehold")
    print("髪とワンピースの裾のシミュレーション")
    hair = hair_sim(poses)
    skirt = skirt_sim(poses)
    cam_main = camera("main")
    # 横からの確認：手すりに沿って横から（手すりの面が画面に垂直）。広く引いて、床の縁の下まで
    rail_pt, _ = rail_point_on_path()
    side_loc = np.array([*(rail_pt - RAIL_D * 9.0 - RAIL_N * 1.0), -0.8])
    yaw = np.rad2deg(np.arctan2(RAIL_D[1], RAIL_D[0])) - 90
    cam_side = camera("side", loc=tuple(side_loc), rot=(90, 0, yaw), shift_y=0, ortho=7.0)
    # エンドB：2つ下の階（-6m）から、落ちる線を正面に見る
    endb_loc = np.array([*(rail_pt - RAIL_N * 4.5), -5.6])
    yaw_b = np.rad2deg(np.arctan2(RAIL_N[1], RAIL_N[0])) - 90
    cam_endb = camera("endb", loc=tuple(endb_loc), rot=(90, 0, yaw_b), f_px=560, shift_y=0)   # 窓の高さ 400px ＝ 約 3.2m（体は 9 コマほどで通る）
    n_out = (len(poses) - SUB) // SUB
    meta = {"fps": FPS, "frames": n_out, "t_release": T_REL, "t_sit": T_SIT, "t_walk": list(T_WALK), "loop": LOOP,
            "loop_handoff": LOOP_HANDOFF, "fit": fitp(), "calib": {
        "f_px": F_PX, "horizon_y": HORIZON, "cam_h": CAM_H, "hfov_deg": float(np.rad2deg(2 * np.arctan(CX / F_PX))),
        "height_m": HEIGHT, "rail_h": RAIL_H}}
    for d in ("main", "side", "endb", "curtain", "curtain_only"):
        (OUTD / d).mkdir(parents=True, exist_ok=True)
    tmp = OUTD / "tmp.png"
    L = int(round(LOOP * FPS))
    h0 = int(round(LOOP_HANDOFF * FPS))
    # 女の影（レースの向こうでは半分ほど隠れる）
    sc.camera = cam_main
    curt.hide_render = True                                                 # 女の影にはカーテンを入れない（カーテンは上から重ねるので、レースの透けはそこで出る）
    sc.render.use_border = True
    sc.render.use_crop_to_border = False
    sc.render.border_min_x, sc.render.border_max_x = 20 / W, 700 / W
    sc.render.border_min_y, sc.render.border_max_y = 1 - 560 / H, 1 - 40 / H
    cover = []
    for i in range(n_out):
        k = SUB * i + SUB // 2                                              # このコマの中心
        cv = cloth_frame(C, h0 + i)
        curt.data.vertices.foreach_set("co", cv.ravel())
        curt.data.update()
        acc = np.zeros((H, W), np.float32)
        for dk in (-1, 0, 1):
            pose_body(body, poses[k + dk], hair[k + dk], sp=skirt[k + dk])
            acc += render_rgba(sc, tmp)[..., 3]
        acc /= 3
        Image.fromarray(np.clip(acc * 255 + 0.5, 0, 255).astype(np.uint8)).save(OUTD / "main" / f"{i:04d}.png")
        cover.append(float(acc.sum()))
        print("main", i, n_out, round(cover[-1]))
    rel = int(round((PRE + T_REL) * FPS))
    meta["release_frame"] = rel
    ank = [max(_pt(poses[SUB * i + SUB // 2], f"shin_{sd}", _J[f"ankle_{sd}"])[2] for sd in "rl") for i in range(n_out)]
    meta["ankle_z"] = ank
    meta["apex_frame"] = int(rel + np.argmax(ank[rel:]))                    # 脚がいちばん高い所（合成で 2〜3 コマ止める）
    meta["pre"] = PRE
    finalize_main(meta)
    gone = meta["gone_frame"]
    # カーテン（女の影は holdout：女が手前にいる所ではカーテンを描かない）。ループの全コマ。もうひとつは女なし（「何度も」用）
    sc.render.use_border = False
    sc.cycles.samples = 24
    sc.cycles.max_bounces = 2
    sc.cycles.transmission_bounces = 2
    sc.cycles.diffuse_bounces = 1
    sun_d = bpy.data.lights.new("sun", "SUN")
    sun_d.energy = 2.0
    sun = bpy.data.objects.new("sun", sun_d)
    sc.collection.objects.link(sun)
    sun.rotation_euler = Vector((0, 0, -1)).rotation_difference(Vector((*WIN_IN, -0.35))).to_euler()
    sc.world.node_tree.nodes.get("Background").inputs[1].default_value = 0.35
    for ob in hold.values():
        ob.hide_render = True                                               # 手すりはカーテンより奥なので、カーテンの絵には要らない
    # 床：影だけを受ける（窓からの逆光で、カーテンの裾と女の影が床に手前へ伸びる）
    bpy.ops.mesh.primitive_plane_add(size=1)
    catcher = bpy.context.active_object
    catcher.scale = (12, 12, 1)
    c0 = (WIN_L + WIN_R) / 2 + WIN_IN * 6.0
    catcher.location = (c0[0], c0[1], 0.0)
    catcher.rotation_euler = (0, 0, np.arctan2(WIN_D[1], WIN_D[0]))
    catcher.is_shadow_catcher = True
    sun.rotation_euler = Vector((0, 0, -1)).rotation_difference(Vector((*(WIN_IN * 0.45), -0.9))).to_euler()
    curt.hide_render = False
    set_mat(curt, m_lace)
    set_mat(body["body"], m_hold)
    set_mat(body["hair"], m_hold)
    set_mat(body["skirt"], m_hold)
    for kind in (() if "mainonly" in sys.argv[1:] else ("curtain", "curtain_only")):   # mainonly：カーテンの絵は前のまま（女の影だけ作り直す）
        for li in range(L):
            cv = cloth_frame(C, li)
            curt.data.vertices.foreach_set("co", cv.ravel())
            curt.data.update()
            i = li - h0
            if kind == "curtain" and 0 <= i < n_out and i <= gone + 1:
                body["body"].hide_render = False
                pose_body(body, poses[SUB * i + SUB // 2], hair[SUB * i + SUB // 2], sp=skirt[SUB * i + SUB // 2])
            else:
                body["body"].hide_render = True
                body["hair"].hide_render = True
                body["skirt"].hide_render = True
            sc.render.filepath = str(OUTD / kind / f"{li:04d}.png")
            bpy.ops.render.render(write_still=True)
            print(kind, li, L)
    body["body"].hide_render = False
    for ob in hold.values():
        ob.hide_render = False
    sun.hide_render = True
    catcher.hide_render = True
    sc.world.node_tree.nodes.get("Background").inputs[1].default_value = 1.0
    set_mat(body["body"], m_body)
    set_mat(body["hair"], m_body)
    set_mat(body["skirt"], m_body)
    curt.hide_render = True
    sc.cycles.samples = 12
    sc.cycles.max_bounces = 0
    # 横から（灰色の手すり・床、白地）
    sc.render.use_border = False
    sc.render.film_transparent = False
    sc.camera = cam_side
    for ob in hold.values():
        ob.data.materials.clear()
        nm = ob.name
        ob.data.materials.append(make_mat("debug_panel" if nm == "rail_panel" else "debug_slab" if nm == "slab" else "debug_rail"))
    sc.render.resolution_x, sc.render.resolution_y = 960, 720
    for i in range(0, n_out, 1):
        pose_body(body, poses[SUB * i + SUB // 2], hair[SUB * i + SUB // 2], sp=skirt[SUB * i + SUB // 2])
        rgba = render_rgba(sc, tmp)
        Image.fromarray((rgba[..., :3] * 255).astype(np.uint8)).save(OUTD / "side" / f"{i:04d}.png")
    # エンドB（手すり・床は消す。体だけ）
    for ob in hold.values():
        ob.hide_render = True
    sc.render.film_transparent = True
    sc.render.resolution_x, sc.render.resolution_y = 640, 400
    sc.camera = cam_endb
    eb = []
    for i in range(rel, n_out):
        acc = np.zeros((400, 640), np.float32)
        for dk in (-1, 0, 1):
            pose_body(body, poses[SUB * i + SUB // 2 + dk], hair[SUB * i + SUB // 2 + dk], sp=skirt[SUB * i + SUB // 2 + dk])
            acc += render_rgba(sc, tmp)[..., 3]
        acc /= 3
        if acc.sum() > 1:
            Image.fromarray(np.clip(acc * 255 + 0.5, 0, 255).astype(np.uint8)).save(OUTD / "endb" / f"{i:04d}.png")
            eb.append(i)
    meta["endb_frames"] = eb
    (OUTD / "meta.json").write_text(json.dumps(meta))
    print("gone", gone, "release", rel, "frames", n_out)


def set_shape(P):
    BODY["verts"] = shape_verts(P)


def raster(T, hp=None, P=None, sp=None):
    """メッシュ（と髪）を背景のカメラで投影して塗った 1280×720 のマスク（numpy だけ。合わせ込み用の速い版）"""
    from PIL import Image, ImageDraw
    P = P or {"s": 1, "tx": 0, "ty": 0}
    v = mh_body.skin(BODY, T, None)
    fx, fy = FOOT_PX
    sim2 = lambda x, y: (fx + (x - fx) * P["s"] + P["tx"], fy + (y - fy) * P["s"] * P.get("sy", 1) + P["ty"])
    x, y = sim2(CX + F_PX * v[:, 0] / v[:, 1], HORIZON - F_PX * (v[:, 2] - CAM_H) / v[:, 1])
    im = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(im)
    for q in BODY["faces"]:
        d.polygon([(x[i], y[i]) for i in q], fill=255)
    if sp is not None:
        pp = sp.reshape(-1, 3)
        qx, qy = sim2(CX + F_PX * pp[:, 0] / pp[:, 1], HORIZON - F_PX * (pp[:, 2] - CAM_H) / pp[:, 1])
        for q in skirt_faces():
            d.polygon([(qx[i], qy[i]) for i in q], fill=255)
    if hp is not None:
        for st in hp:
            px, py = sim2(CX + F_PX * st[:, 0] / st[:, 1], HORIZON - F_PX * (st[:, 2] - CAM_H) / st[:, 1])
            d.line(list(zip(px, py)), fill=255, width=int(round(P.get("hwid", 7))))
    return np.asarray(im) > 127


def target_mask():
    """ep8_balcony_1 の女の影（ほぼ黒の、いちばん大きなかたまり）"""
    from PIL import Image
    from scipy.ndimage import binary_fill_holes, label
    a = np.asarray(Image.open(ROOT / "assets" / "ep8_balcony_1.png").convert("L"), np.float32)
    m = np.zeros(a.shape, bool)
    m[190:470, 270:410] = a[190:470, 270:410] < 24
    lab, n = label(m)
    m = lab == (np.argmax(np.bincount(lab.ravel())[1:]) + 1)
    return binary_fill_holes(m)


def iou(a, b):
    return float((a & b).sum() / max(1, (a | b).sum()))


def fit():
    """受け渡しのコマの形を、_1 の影に合わせる（腕の向き。座標をひとつずつ動かして重なりが増える方へ）"""
    tgt = target_mask()
    hp0 = hair_sim([kinematic(-0.2)])[-1]
    sp0 = skirt_sim([kinematic(-0.2)])[-1]
    P = fitp()

    def score(P):
        set_shape(P)
        return iou(raster(kinematic(-0.2, P), hp0, P, sp0), tgt)
    best = score(P)
    print("合わせる前の IoU", round(best, 4))
    for step in (0.1, 0.05, 0.025, 0.012):
        for _ in range(3):
            for key in ("ua", "fa", "ul"):
                for k in range(3):
                    for sgn in (1, -1):
                        Q = json.loads(json.dumps(P))
                        Q[key][k] += sgn * step
                        sc = score(Q)
                        if sc > best:
                            best, P = sc, Q
            for key, sc_ in (("fl", 40), ("s", 0.1), ("tx", 20), ("ty", 20), ("wx", 0.2), ("gap", 0.05), ("sy", 0.1), ("hwid", 10)):
                for sgn in (1, -1):
                    Q = dict(P, **{key: P[key] + sgn * step * sc_})
                    sc = score(Q)
                    if sc > best:
                        best, P = sc, Q
            for k in range(9):
                for sgn in (1, -1):
                    Q = json.loads(json.dumps(P))
                    Q["prof"][k] += sgn * step
                    sc = score(Q)
                    if sc > best:
                        best, P = sc, Q
        print("step", step, "IoU", round(best, 4))
    FIT_P.write_text(json.dumps(P))
    set_shape(P)
    m = raster(kinematic(-0.2, P), hp0, P, sp0)
    from scipy.ndimage import distance_transform_edt as edt, binary_erosion
    bm, bt = m & ~binary_erosion(m), tgt & ~binary_erosion(tgt)
    dd = np.r_[edt(~bt)[bm], edt(~bm)[bt]]
    print("輪郭の差：中央値", round(float(np.median(dd)), 2), "px、95%", round(float(np.percentile(dd, 95)), 2), "px、最大", round(float(dd.max()), 1))
    from PIL import Image
    b = np.zeros((H, W, 3), np.uint8) + 40
    b[tgt & ~m] = (40, 220, 40)
    b[m & ~tgt] = (230, 40, 40)
    b[m & tgt] = (240, 240, 240)
    Image.fromarray(b).crop((230, 170, 450, 480)).resize((440, 620), Image.NEAREST).save(OUTD / "fit_handoff.png")
    return best


def finalize_main(meta):
    """すりガラスの板の縁などに残る、動かないかすかなアルファ（体がいなくなった最後のコマ）を全コマから引き、消えたコマを決める"""
    from PIL import Image
    n = meta["frames"]
    base = np.asarray(Image.open(OUTD / "main" / f"{n - 1:04d}.png"), np.float32)
    cover = []
    for i in range(n):
        p = OUTD / "main" / f"{i:04d}.png"
        a = np.clip(np.asarray(Image.open(p), np.float32) - base, 0, 255)
        a[a < 2] = 0
        Image.fromarray(a.astype(np.uint8)).save(p)
        cover.append(float(a.sum() / 255))
    meta["cover"] = cover
    rel = meta["release_frame"]
    meta["gone_frame"] = next((i for i in range(rel, n) if cover[i] < 0.5), n - 1)   # 手を離したあと、見える所が無くなったコマ


def main():
    if "fit" in sys.argv[1:]:
        OUTD.mkdir(parents=True, exist_ok=True)
        print("IoU", fit())
        return
    if "post" in sys.argv[1:]:
        meta = json.loads((OUTD / "meta.json").read_text())
        finalize_main(meta)
        (OUTD / "meta.json").write_text(json.dumps(meta))
        print("gone", meta["gone_frame"])
        return
    OUTD.mkdir(parents=True, exist_ok=True)
    calib()
    if "calib" in sys.argv[1:]:
        return
    if not (OUTD / "cloth.npz").exists() or "cloth" in sys.argv[1:]:
        cloth_bake()
    track = pivot_fall()
    np.save(OUTD / "track.npy", np.array([[t[n] for n in ORDER] for t in track]))
    poses = all_poses(track)
    render_views(poses)


if __name__ == "__main__":
    main()
