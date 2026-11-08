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
POSTS_PX = (202, 280, 376, 435)            # 背景の手すりの柱の x

# 時刻（秒、0 = 絵の女から物理の女へ受け渡すコマ）
T_ARM = (0.10, 0.45)                       # 振っていた手を下ろす
T_WALK = (0.25, 1.95)                      # 後ろ向きに歩いて手すりまで下がる
T_CROUCH, T_JUMP, T_SIT = 1.95, 2.10, 2.40 # かがむ → 跳んで手すりに腰かける
T_REL = 2.62                               # 腕を上げて反り、ここから先は物理だけ（重力で後ろへ倒れる）
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
SCALE = HEIGHT / 1.53


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
def fk(root_pos, root_R, local):
    """root_pos: 骨盤の中心の世界位置、root_R: 骨盤の向き、local: {部品: 親に対する回転}。返すのは {部品: 4×4（立ち姿の座標 → 世界）}"""
    T = {}
    for name in ORDER:
        parent, joint, ctr, *_ = SEG[name]
        R = local.get(name, np.eye(3))
        j = np.array(joint) * SCALE
        if parent is None:
            M = np.eye(4)
            M[:3, :3] = root_R @ R
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


def arm_wave_pose():
    """ep8_balcony_1 の手を振る姿：右腕（画面の左）は肩から横・少し前へ、肘から先は上へ。左腕は体の横に下ろす"""
    up = aim((0, 0, -1), (-0.63, -0.68, -0.37))
    fore = up.T @ aim((0, 0, -1), (0.02, -0.62, 0.78))
    return {"uarm_r": up, "farm_r": fore, "uarm_l": aim((0, 0, -1), (0.08, 0.0, -1.0)), "farm_l": rx(-8)}


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


def kinematic(t):
    """受け渡し t=0 〜 手を離す T_REL までの姿勢。返すのは {部品: 4×4}"""
    rail_pt, u = rail_point_on_path()
    yaw0 = 0.0
    face_end = -RAIL_N                                                     # 手すりに背を向ける：顔は手すりの面の内向き
    yaw1 = np.rad2deg(np.arctan2(face_end[0], -face_end[1])) * 0.75        # 視線の向き（-y）からの振れ。最後の 1/4 は物理にまかせる
    rest = {}
    # 腕：手を振った形 → 体の横へ下ろす → 腰かけてから上げる
    wave, down = arm_wave_pose(), {"uarm_r": aim((0, 0, -1), (-0.14, 0.02, -0.99)), "uarm_l": aim((0, 0, -1), (0.14, 0.02, -0.99)),
                                   "farm_r": rx(-10), "farm_l": rx(-10)}
    arms = blend_pose(wave, down, sstep(*T_ARM, t))
    if t > T_SIT - 0.05:
        arms = blend_pose(arms, arms_up_pose(), sstep(T_SIT - 0.05, T_REL, t))
    pose = dict(rest)
    pose.update(arms)
    walk_len = np.linalg.norm(rail_pt - FEET0) - 0.24
    k = sstep(*T_WALK, t)
    dist = walk_len * k
    feet = FEET0 + u * dist
    yaw = lerp(yaw0, yaw1, sstep(T_WALK[0], T_SIT, t))
    # 歩く：進んだ距離に足の運びを結びつける（1歩 0.60m、ももの振れ ±22°）。後ろへ振り出す脚の膝が曲がる
    step = 0.60
    ph = np.pi * dist / step
    amp = 22.0 * min(1.0, dist / 0.25) * min(1.0, (walk_len - dist) / 0.2 + 0.0) if t < T_CROUCH else 0.0
    hip_r, hip_l = amp * np.sin(ph), -amp * np.sin(ph)
    kn_r = 38 * max(0.0, np.cos(ph)) ** 1.5 * (amp / 22)
    kn_l = 38 * max(0.0, -np.cos(ph)) ** 1.5 * (amp / 22)
    lean = 6 * (amp / 22)                                                   # 後ろ歩きは上体をわずかに前へ
    # かがむ → 跳ぶ → 腰かける
    c = sstep(T_CROUCH, T_JUMP, t)
    j = sstep(T_JUMP, T_SIT, t)
    hip_flex = -40 * c * (1 - j) - 85 * j
    knee = 55 * c * (1 - j) + 88 * j
    torso = lean + 18 * c * (1 - j) - 8 * j
    if t > T_SIT - 0.05:
        torso -= 55 * ease_in(T_SIT - 0.05, T_REL, t)                     # 反りは加速しながら（手を離す瞬間に速さを持たせ、物理へ引き継ぐ）
    pose["thigh_r"] = rx(-hip_r + hip_flex)
    pose["thigh_l"] = rx(-hip_l + hip_flex)
    pose["shin_r"] = rx(kn_r + knee)
    pose["shin_l"] = rx(kn_l + knee)
    pose["chest"] = rx(torso * 0.6)
    pose["head"] = rx(-28 * ease_in(T_SIT, T_REL, t) + 4 * (amp / 22))
    pose["hair"] = rx(-10 * sstep(T_SIT, T_REL, t))
    pelvis_tilt = rx(torso * 0.4 - 10 * j)
    R = rz(yaw) @ pelvis_tilt
    p_ground = np.array([feet[0], feet[1], 0.86 * SCALE])
    T = fk(p_ground, R, pose)
    lift = -lowest(T) + 0.004                                               # 足は床に着く（浮かない・沈まない）
    p_ground[2] += lift
    if t <= T_JUMP:
        return fk(p_ground, R, pose)
    # 跳んでいる間：骨盤は放物線で手すりの上へ（地面の拘束は外す）
    sit = np.array([*(rail_pt + RAIL_N * 0.06), RAIL_H + 0.155])
    T0 = kinematic(T_JUMP)
    start = T0["pelvis"] @ np.array([*(np.array(SEG["pelvis"][2]) * SCALE), 1])
    jj = (min(t, T_SIT) - T_JUMP) / (T_SIT - T_JUMP)
    pos = start[:3] + (sit - start[:3]) * sstep(0, 1, jj)
    pos[2] = start[2] + (sit[2] - start[2]) * jj + 4 * 0.06 * jj * (1 - jj)
    if t > T_SIT:
        pos = sit
    return fk(pos, R, pose)


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
    mats = {}
    for name, ob in parts.items():
        if kind == "holdout":
            key = "panel" if name == "panel" else "hold"
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
        mx.inputs[0].default_value = 0.55
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(h.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs[0])
    else:
        col = {"body": (0, 0, 0), "debug_rail": (0.25, 0.3, 0.45), "debug_panel": (0.6, 0.7, 0.85), "debug_slab": (0.55, 0.5, 0.45),
               "solid": (1, 1, 1)}[key]
        e = nt.nodes.new("ShaderNodeEmission")
        e.inputs[0].default_value = (*col, 1)
        e.inputs[1].default_value = 1.0
        nt.links.new(e.outputs[0], out.inputs[0])
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
    sc.cycles.filter_width = 1.6
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
def build_body(sc):
    """部品ごとのメタボールの物体（名前が同じ家族なので、ひとつのなめらかな体にまとまる）。返すのは {部品: 物体}"""
    mat = make_mat("body")
    objs = {}
    for i, name in enumerate(ORDER):
        mb = bpy.data.metaballs.new(f"Body{i}")
        mb.resolution = mb.render_resolution = 0.008
        mb.threshold = 0.6
        ob = bpy.data.objects.new("Body" if i == 0 else f"Body.{i:03d}", mb)
        sc.collection.objects.link(ob)
        ctr = np.array(SEG[name][2]) * SCALE
        for kind, c, r in LOOK[name]:
            e = mb.elements.new()
            c = np.array(c) * SCALE - ctr
            if kind == "E":
                rr = np.array(r) * SCALE
                m = rr.max()
                e.type = "ELLIPSOID"
                e.radius = m / 0.57
                e.size_x, e.size_y, e.size_z = rr / m
            else:                                                            # 縦（z）向きのカプセル
                half, rad = r[0] * SCALE, r[1] * SCALE
                e.type = "CAPSULE"
                e.radius = rad / 0.57
                e.size_x = half
                e.rotation = Quaternion((0, 1, 0), np.pi / 2)
            e.co = c
        if i == 0:
            mb.materials.append(mat)
        objs[name] = ob
    return objs


def pose_body(objs, T):
    for name, ob in objs.items():
        ctr = np.array(SEG[name][2]) * SCALE
        M = T[name].copy()
        M[:3, 3] = M[:3, :3] @ ctr + M[:3, 3]
        ob.matrix_world = Matrix(M.tolist())


# ---------------------------------------------------------------- 2. 物理（手すりに腰かけたところから）
def simulate():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = SIM_FPS
    n = int(round((T_END - T_REL) * SIM_FPS)) + 2
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
        ob.rigid_body.friction = 0.6
        ob.rigid_body.collision_shape = "BOX"
        ob.rigid_body.collision_margin = 0.002
    T = kinematic(T_REL)
    # 手を離す直前の動き（腕を上げる・反る）の速さを、物理の最初の速さとして渡すため、1/120 秒前の姿勢も取っておく
    Tp = kinematic(T_REL - 1 / SIM_FPS)
    bodies = {}
    for name in ORDER:
        parent, joint, ctr, mass, shape, dims = SEG[name]
        bpy.ops.mesh.primitive_cube_add(size=1)
        ob = bpy.context.active_object
        ob.name = "rb_" + name
        ob.scale = np.array(dims) * SCALE
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        c = np.array(ctr) * SCALE
        M = T[name].copy()
        M[:3, 3] = M[:3, :3] @ c + M[:3, 3]
        ob.matrix_world = Matrix(M.tolist())
        bpy.ops.rigidbody.object_add()
        rb = ob.rigid_body
        rb.type = "ACTIVE"
        rb.mass = mass
        rb.collision_shape = shape
        rb.collision_margin = 0.003
        rb.friction = 0.5
        rb.restitution = 0.0
        rb.linear_damping = 0.02
        rb.angular_damping = 0.25 if name != "hair" else 0.6
        bodies[name] = ob
    # 関節（立ち姿からの可動域を、腰かけた姿勢からの差に直して与える）。すべて親の向きにそろえた空の物体で
    lim = {  # 部品: (x の範囲, y の範囲, z の範囲)  度、手を離す瞬間の姿勢からの差
        "chest": ((-35, 55), (-20, 20), (-25, 25)),
        "head": ((-35, 45), (-25, 25), (-40, 40)),
        "hair": ((-70, 50), (-25, 25), (-15, 15)),
        "uarm_r": ((-80, 80), (-70, 70), (-60, 60)), "uarm_l": ((-80, 80), (-70, 70), (-60, 60)),
        "farm_r": ((-130, 12), (0, 0), (-10, 10)), "farm_l": ((-130, 12), (0, 0), (-10, 10)),
        "thigh_r": ((-40, 95), (-15, 35), (-30, 30)), "thigh_l": ((-40, 95), (-35, 15), (-30, 30)),
        "shin_r": ((-88, 55), (0, 0), (0, 0)), "shin_l": ((-88, 55), (0, 0), (0, 0)),
    }
    for name in ORDER:
        parent = SEG[name][0]
        if parent is None:
            continue
        j = np.array(SEG[name][1]) * SCALE
        Mj = T[parent].copy()
        Mj[:3, 3] = T[parent][:3, :3] @ j + T[parent][:3, 3]
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
    # 手を離す直前の動きを渡す：最初の2コマだけ「動かされる物体」として直前の姿勢 → 今の姿勢を通す（Bullet がその速さを引き継ぐ）
    for name, ob in bodies.items():
        c = np.array(SEG[name][2]) * SCALE
        for fr, TT in ((1, Tp), (2, T)):
            M = TT[name].copy()
            M[:3, 3] = M[:3, :3] @ c + M[:3, 3]
            ob.matrix_world = Matrix(M.tolist())
            ob.keyframe_insert("location", frame=fr)
            ob.keyframe_insert("rotation_euler", frame=fr)
            ob.rigid_body.kinematic = True
            ob.rigid_body.keyframe_insert("kinematic", frame=fr)
        ob.rigid_body.kinematic = False
        ob.rigid_body.keyframe_insert("kinematic", frame=3)
    out = []
    for f in range(1, n + 1):
        sc.frame_set(f)
        out.append({name: np.array(ob.matrix_world) for name, ob in bodies.items()})
    # 部品の物体の行列（中心）→ 立ち姿の座標からの 4×4 へ
    track = []
    for st in out[1:]:                                                       # フレーム2 = 手を離す瞬間 (T_REL)
        T2 = {}
        for name, M in st.items():
            c = np.array(SEG[name][2]) * SCALE
            Mm = np.array(M)
            R = Mm[:3, :3] / np.linalg.norm(Mm[:3, :3], axis=0)
            T2[name] = np.eye(4)
            T2[name][:3, :3] = R
            T2[name][:3, 3] = Mm[:3, 3] - R @ c
        track.append(T2)
    return track


# ---------------------------------------------------------------- 3. 書き出し
def all_poses(track):
    """1/120 秒おきの、受け渡しから終わりまでの姿勢の列"""
    n_k = int(round(T_REL * SIM_FPS))
    poses = [kinematic(i / SIM_FPS) for i in range(n_k)] + track
    return poses


def render_views(poses):
    from PIL import Image
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    setup_render(sc, samples=12)
    body = build_body(sc)
    hold = build_set("holdout")
    cam_main = camera("main")
    # 横からの確認：手すりに沿って横から（手すりの面が画面に垂直）。広く引いて、床の縁の下まで
    rail_pt, _ = rail_point_on_path()
    side_loc = np.array([*(rail_pt - RAIL_D * 9.0 - RAIL_N * 1.0), -0.8])
    yaw = np.rad2deg(np.arctan2(RAIL_D[1], RAIL_D[0])) - 90
    cam_side = camera("side", loc=tuple(side_loc), rot=(90, 0, yaw), shift_y=0, ortho=7.0)
    # エンドB：2つ下の階（-6m）から、落ちる線を正面に見る
    endb_loc = np.array([*(rail_pt - RAIL_N * 4.5), -5.6])
    yaw_b = np.rad2deg(np.arctan2(RAIL_N[1], RAIL_N[0])) - 90
    cam_endb = camera("endb", loc=tuple(endb_loc), rot=(90, 0, yaw_b), f_px=900, shift_y=0)
    n_out = (len(poses) - SUB) // SUB
    meta = {"fps": FPS, "frames": n_out, "t_release": T_REL, "t_sit": T_SIT, "t_walk": list(T_WALK), "calib": {
        "f_px": F_PX, "horizon_y": HORIZON, "cam_h": CAM_H, "hfov_deg": float(np.rad2deg(2 * np.arctan(CX / F_PX))),
        "height_m": HEIGHT, "rail_h": RAIL_H}}
    for d in ("main", "side", "endb"):
        (OUTD / d).mkdir(parents=True, exist_ok=True)
    tmp = OUTD / "tmp.png"
    sc.camera = cam_main
    sc.render.use_border = True
    sc.render.use_crop_to_border = False
    sc.render.border_min_x, sc.render.border_max_x = 40 / W, 640 / W
    sc.render.border_min_y, sc.render.border_max_y = 1 - 540 / H, 1 - 60 / H
    cover = []
    for i in range(n_out):
        k = SUB * i + SUB // 2                                              # このコマの中心
        acc = np.zeros((H, W), np.float32)
        for dk in (-1, 0, 1):
            pose_body(body, poses[k + dk])
            acc += render_rgba(sc, tmp)[..., 3]
        acc /= 3
        Image.fromarray(np.clip(acc * 255 + 0.5, 0, 255).astype(np.uint8)).save(OUTD / "main" / f"{i:04d}.png")
        cover.append(float(acc.sum()))
        print("main", i, n_out, round(cover[-1]))
    rel = int(T_REL * FPS)
    meta["release_frame"] = rel
    finalize_main(meta)
    gone = meta["gone_frame"]
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
        pose_body(body, poses[SUB * i + SUB // 2])
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
            pose_body(body, poses[SUB * i + SUB // 2 + dk])
            acc += render_rgba(sc, tmp)[..., 3]
        acc /= 3
        if acc.sum() > 1:
            Image.fromarray(np.clip(acc * 255 + 0.5, 0, 255).astype(np.uint8)).save(OUTD / "endb" / f"{i:04d}.png")
            eb.append(i)
    meta["endb_frames"] = eb
    (OUTD / "meta.json").write_text(json.dumps(meta))
    print("gone", gone, "release", rel, "frames", n_out)


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
    track = simulate()
    np.save(OUTD / "track.npy", np.array([[t[n] for n in ORDER] for t in track]))
    poses = all_poses(track)
    render_views(poses)


if __name__ == "__main__":
    main()
