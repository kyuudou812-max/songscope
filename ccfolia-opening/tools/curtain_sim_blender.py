"""第八話ベランダのカーテンの動きを、Blender（pip の bpy）の布シミュレーションで確かめて数値を取り出す。
最終の絵には使わない（動きの参考と検証だけ）。

  python3 tools/curtain_sim_blender.py   → build/cache/curtain_sim.json と、要約を表示

モデル：幅 1.4m・丈 2.3m の薄いレース（質量 0.15kg/m²相当）、上辺はカーテンレールに固定（ピン）。
窓の外（-Y）から部屋の中（+Y）へ吹く風。風は 0.6〜1.0 の基本に、約4秒周期の突風を重ねる。
取り出すもの：高さごとの部屋側へのふくらみ（Y 変位）の時間変化、突風への遅れ（レール→裾の伝わる速さ）、裾の振れ幅。"""
import json
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FPS, SEC = 24, 16
W, H = 1.4, 2.3
GUST_T = 4.0
import sys
STRENGTH = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0   # 風の強さ（Blender の単位）。140 だと裾が水平近くまで吹き上がる（絵の右のカーテン）

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = FPS
sc.frame_start, sc.frame_end = 1, FPS * SEC

bpy.ops.mesh.primitive_grid_add(x_subdivisions=28, y_subdivisions=46, size=1)
ob = bpy.context.active_object
ob.scale = (W, H, 1)
ob.rotation_euler = (np.pi / 2, 0, 0)                     # XZ 平面に立てる（窓の面）。Z が上、+Y が部屋の中
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
ob.location = (0, 0, H / 2)
vg = ob.vertex_groups.new(name="rail")
top = [v.index for v in ob.data.vertices if v.co.z > H / 2 - 1e-4]
vg.add(top, 1.0, "REPLACE")

cl = ob.modifiers.new("cloth", "CLOTH")
s = cl.settings
s.quality = 8
s.mass = 0.15 * W * H / len(ob.data.vertices) * 10       # Blender の mass は頂点あたり（kg）
s.air_damping = 1.0
s.tension_stiffness = s.compression_stiffness = 8
s.bending_stiffness = 0.05
s.vertex_group_mass = "rail"
cl.point_cache.frame_start, cl.point_cache.frame_end = 1, FPS * SEC

bpy.ops.object.effector_add(type="WIND", location=(0, -2, H / 2))
wind = bpy.context.active_object
wind.rotation_euler = (-np.pi / 2, 0, 0)                  # 力の向き（ローカル Z）を +Y＝部屋の中へ
wind.field.flow = 0.6
wind.field.noise = 0.4
for f in range(1, FPS * SEC + 1, 3):                      # 基本 0.6 ＋ 4秒周期の突風（立ち上がり速く、抜けはゆっくり）
    t = (f - 1) / FPS
    ph = (t % GUST_T) / GUST_T
    g = (ph / 0.25) if ph < 0.25 else np.exp(-(ph - 0.25) * 4)
    wind.field.strength = STRENGTH * (0.6 + 0.4 * g)
    wind.field.keyframe_insert("strength", frame=f)

heights = [0.0, 0.25, 0.5, 0.75, 1.0]                     # 0=レール、1=裾
rows = {}
co0 = np.array([v.co[:] for v in ob.data.vertices])
for hk in heights:
    z = H / 2 - hk * H                                  # ローカル座標（真ん中が 0）
    rows[hk] = np.where(np.abs(co0[:, 2] - z) < H / 46 * 0.6)[0]
dep = bpy.context.evaluated_depsgraph_get()
series = {hk: [] for hk in heights}
xspread = []
for f in range(1, FPS * SEC + 1):
    sc.frame_set(f)
    me = ob.evaluated_get(dep).to_mesh()
    co = np.array([v.co[:] for v in me.vertices])
    for hk in heights:
        series[hk].append(float(co[rows[hk], 1].mean()))
    xspread.append(float(np.ptp(co[rows[1.0], 0])))
    ob.evaluated_get(dep).to_mesh_clear()

t = np.arange(FPS * SEC) / FPS
st = t >= 4                                               # 最初の4秒（垂れ下がって落ち着くまで）は捨てる
res = {"fps": FPS, "gust_period_s": GUST_T, "width_m": W, "height_m": H}
hem = np.array(series[1.0])
for hk in heights:
    y = np.array(series[hk])
    res[f"mean_y_{hk}"] = float(y[st].mean())
    res[f"amp_y_{hk}"] = float(np.ptp(y[st]) / 2)
    # 突風（風の強さの波形）に対する遅れ：相互相関の最大の位置
    if hk > 0:
        ph = (t % GUST_T) / GUST_T
        g = np.where(ph < 0.25, ph / 0.25, np.exp(-(ph - 0.25) * 4))
        a_, b_ = g[st] - g[st].mean(), y[st] - y[st].mean()
        cc = [np.dot(a_[: len(a_) - k], b_[k:]) for k in range(int(GUST_T * FPS))]
        res[f"peak_lag_s_{hk}"] = float(np.argmax(cc) / FPS)
res["hem_width_ptp_m"] = float(np.mean(xspread[FPS * 4:]))
d = hem[st] - hem[st].mean()
spec = np.abs(np.fft.rfft(d))
fr = np.fft.rfftfreq(len(d), 1 / FPS)
hi = fr > 0.6
res["hem_flutter_hz"] = float(fr[hi][np.argmax(spec[hi])])
res["series"] = {str(k): v for k, v in series.items()}
out = ROOT / "build" / "cache" / "curtain_sim.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(res))
for k, v in res.items():
    if k != "series":
        print(k, round(v, 3) if isinstance(v, float) else v)
