"""Blender（bpy）でアニメ調（トゥーン）の3Dキャラクターを作って描画する（試し：加賀美ハヤト）。

すべてプログラムで作る（モデル・色・陰影・輪郭線）。Cycles（CPU）で描画する。

使い方:
    python3 rofmao_3d.py <出力png>
"""
import math
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector

LIGHT = Vector((-0.45, -0.75, 0.6)).normalized()  # 光の向き（左前上から）


def srgb(c):
    """0-255 の sRGB をリニアに変換（Blender の色はリニア）"""
    def f(v):
        v = v / 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return (f(c[0]), f(c[1]), f(c[2]), 1.0)


# ---------------------------------------------------------------- マテリアル
_mats = {}


def toon(name, base, shade=None, soft=0.06):
    """アニメ塗り：光の当たる面は base、影は shade。境目は少しだけぼかす。"""
    key = (name, base, shade)
    if key in _mats:
        return _mats[key]
    if shade is None:
        shade = tuple(int(v * 0.78) for v in base)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    lv = nt.nodes.new("ShaderNodeCombineXYZ")
    lv.inputs[0].default_value, lv.inputs[1].default_value, lv.inputs[2].default_value = LIGHT
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    nt.links.new(geo.outputs["Normal"], dot.inputs[0])
    nt.links.new(lv.outputs[0], dot.inputs[1])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.interpolation_type = "SMOOTHSTEP"
    mr.inputs["From Min"].default_value = 0.05 - soft
    mr.inputs["From Max"].default_value = 0.05 + soft
    nt.links.new(dot.outputs["Value"], mr.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs[6].default_value = srgb(shade)
    mix.inputs[7].default_value = srgb(base)
    nt.links.new(mr.outputs["Result"], mix.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(mix.outputs[2], em.inputs["Color"])
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs[0])
    _mats[key] = m
    return m


def flat(name, color):
    """陰影なしの単色（目・口などの描き込み用）"""
    key = ("flat", name, color)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = srgb(color)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs[0])
    _mats[key] = m
    return m


def outline_mat(color=(70, 45, 40)):
    """輪郭線：外側に一回り大きい裏返しの殻を作り、裏から見える部分だけ線の色にする"""
    key = ("outline", color)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new("outline")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = srgb(color)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(geo.outputs["Backfacing"], mix.inputs[0])
    nt.links.new(em.outputs[0], mix.inputs[1])
    nt.links.new(tr.outputs[0], mix.inputs[2])
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(mix.outputs[0], out.inputs[0])
    _mats[key] = m
    return m


# ---------------------------------------------------------------- 形を作るヘルパ
def finish(obj, mat, outline=0.012, line_color=(70, 45, 40), shell=0.0):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    obj.select_set(False)
    for p in obj.data.polygons:
        p.use_smooth = True
    obj.data.materials.append(mat)
    if shell:
        mod = obj.modifiers.new("thick", "SOLIDIFY")
        mod.thickness = shell
        mod.offset = -1
    if outline:
        obj.data.materials.append(outline_mat(line_color))
        mod = obj.modifiers.new("outline", "SOLIDIFY")
        mod.thickness = outline
        mod.offset = 1
        mod.use_flip_normals = True
        mod.use_rim = False
        mod.material_offset = len(obj.data.materials) - 1
    return obj


def sphere(loc, scale, mat, seg=48, **kw):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=1, location=loc)
    o = bpy.context.active_object
    o.scale = scale
    return finish(o, mat, **kw)


def cylinder(p0, p1, r0, r1, mat, **kw):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bpy.ops.mesh.primitive_cone_add(vertices=40, radius1=r0, radius2=r1, depth=d.length, location=(p0 + p1) / 2)
    o = bpy.context.active_object
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = d.normalized().to_track_quat("Z", "Y")
    return finish(o, mat, **kw)


def frame_matrix(pos, z_axis, y_hint, scale):
    z = Vector(z_axis).normalized()
    y = (Vector(y_hint) - z * Vector(y_hint).dot(z)).normalized()
    x = y.cross(z)
    rot = Matrix((x, y, z)).transposed().to_4x4()
    return Matrix.Translation(pos) @ rot @ Matrix.Diagonal((*scale, 1))


def disc(pos, normal, up, sx, sy, mat, rot=0.0):
    """顔の表面に貼る平たい楕円（目・口など）"""
    bpy.ops.mesh.primitive_circle_add(vertices=48, radius=1, fill_type="NGON")
    o = bpy.context.active_object
    up = Matrix.Rotation(rot, 3, Vector(normal)) @ Vector(up)
    o.matrix_world = frame_matrix(Vector(pos), normal, up, (sx, sy, 1))
    o.data.materials.append(mat)
    return o


def arc_band(pos, normal, up, w, h, thick, mat, flip=False):
    """にっこり目・眉などの弧（上向きの半円の帯）"""
    bm = bmesh.new()
    n = 24
    outer, inner = [], []
    for i in range(n + 1):
        a = math.pi * i / n
        c, s = math.cos(a), math.sin(a) * (-1 if flip else 1)
        outer.append(bm.verts.new((c * (w + thick / 2), s * (h + thick / 2), 0)))
        inner.append(bm.verts.new((c * (w - thick / 2), s * (h - thick / 2), 0)))
    for i in range(n):
        bm.faces.new((outer[i], outer[i + 1], inner[i + 1], inner[i]))
    me = bpy.data.meshes.new("arc")
    bm.to_mesh(me)
    o = bpy.data.objects.new("arc", me)
    bpy.context.collection.objects.link(o)
    o.matrix_world = frame_matrix(Vector(pos), normal, up, (1, 1, 1))
    me.materials.append(mat)
    return o


# ---------------------------------------------------------------- 頭（楕円体）の表面
HEAD_C = Vector((0, 0, 2.3))
HEAD_R = Vector((0.55, 0.5, 0.58))


def head_point(az, el, out=0.0):
    """方位 az（右が+）・仰角 el の方向にある、頭の表面の点と法線"""
    d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    t = 1 / math.sqrt(sum((d[i] / HEAD_R[i]) ** 2 for i in range(3)))
    p = HEAD_C + d * t
    n = Vector(((p - HEAD_C)[i] / HEAD_R[i] ** 2 for i in range(3))).normalized()
    return p + n * out, n


# ---------------------------------------------------------------- 加賀美ハヤト
KAGAMI = dict(
    hair=(196, 132, 88), hair_sh=(150, 94, 60),
    iris=(150, 96, 52), iris_dark=(80, 46, 22),
    skin=(255, 236, 222), skin_sh=(240, 200, 184),
    jacket=(250, 250, 253), jacket_sh=(206, 208, 222),
    inner=(38, 38, 44), pants=(150, 150, 162), accent=(215, 70, 60),
)


def build_face(m, expr):
    black = flat("lash", (50, 30, 24))
    white = flat("white", (255, 255, 255))
    for side in (-1, 1):
        az, el = 0.36 * side, -0.06
        p, n = head_point(az, el, 0.012)
        up = Vector((0, 0, 1))
        if expr == "laugh":
            arc_band(p + up * 0.01, n, up, 0.075, 0.05, 0.022, black)
        else:
            lower = 0.028 if expr == "serious" else 0.0
            disc(p, n, up, 0.1, 0.125 - lower, white)
            p2, _ = head_point(az, el - 0.02, 0.016)
            disc(p2, n, up, 0.078, 0.105 - lower, flat("iris", m["iris"]))
            p3, _ = head_point(az, el + 0.05, 0.018)
            disc(p3, n, up, 0.074, 0.05, flat("irisd", m["iris_dark"]))
            p4, _ = head_point(az, el - 0.01, 0.02)
            disc(p4, n, up, 0.034, 0.05, flat("pupil", (40, 20, 10)))
            p5, _ = head_point(az - 0.06 * side, el + 0.07 - lower, 0.022)
            disc(p5, n, up, 0.026, 0.028, white)
            p6, _ = head_point(az + 0.04 * side, el - 0.1, 0.022)
            disc(p6, n, up, 0.012, 0.012, white)
            # 上まつげ（目尻が少し上がる）
            pl, _ = head_point(az + 0.015 * side, el + 0.205 - lower * 2.2, 0.024)
            disc(pl, n, up, 0.118, 0.02, black, rot=0.16 * side)
        # 眉
        pb, _ = head_point(az, el + 0.40, 0.014)
        tilt = -0.28 * side if expr == "serious" else 0.0
        disc(pb, n, up, 0.085, 0.012, flat("brow", (130, 80, 52)), rot=tilt)
        # ほっぺ
        pc, nc = head_point(0.46 * side, -0.32, 0.008)
        disc(pc, nc, up, 0.07, 0.03, flat("blush", (255, 208, 204)))
    # 口
    pm, nm = head_point(0, -0.46, 0.012)
    up = Vector((0, 0, 1))
    if expr == "laugh":
        disc(pm, nm, up, 0.07, 0.05, flat("mouth", (180, 60, 72)))
        pt, _ = head_point(0, -0.42, 0.016)
        disc(pt, nm, up, 0.055, 0.014, white)
    elif expr == "serious":
        disc(pm, nm, up, 0.04, 0.007, flat("mline", (150, 80, 70)))
    else:
        arc_band(pm, nm, up, 0.035, 0.012, 0.009, flat("mline", (150, 80, 70)), flip=True)


HAIR_C = Vector((0, 0.04, 0.05))
HAIR_R = Vector((0.605, 0.575, 0.625))


def hair_cut_kagami(az):
    """方位 az での髪の下端の仰角（前髪の毛先・センター分け・後ろ髪）"""
    a = abs(az)
    if a < math.pi / 2:
        u = a * 4.2 / math.pi + 0.5
        tri = 1 - abs(2 * (u - math.floor(u)) - 1)
        tri = tri ** 1.6                                   # 毛先をとがらせる
        part = 0.42 * max(0.0, 1 - a / 0.15) ** 1.2        # センター分け
        side = 0.12 * max(0.0, (a - 1.0) / 0.57)           # 耳のあたりは少し短く
        return 0.24 - 0.26 * tri + part + side
    return 0.48 - 0.9 * (a - math.pi / 2) / (math.pi / 2)  # 後ろは長め


def hair_shell(cut, n_az=360, n_el=40):
    """頭の上から下端 cut(az) までの殻を、点を並べて作る（縁がなめらかになる）"""
    bm = bmesh.new()
    rows = []
    for i in range(n_az):
        az = -math.pi + 2 * math.pi * i / n_az
        el_end = cut(az)
        col = []
        for j in range(n_el + 1):
            el = math.pi / 2 - 0.001 - (math.pi / 2 - 0.001 - el_end) * (j / n_el)
            d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
            col.append(bm.verts.new(HEAD_C + HAIR_C + Vector((d.x * HAIR_R.x, d.y * HAIR_R.y, d.z * HAIR_R.z))))
        rows.append(col)
    for i in range(n_az):
        a, b = rows[i], rows[(i + 1) % n_az]
        for j in range(n_el):
            bm.faces.new((a[j], b[j], b[j + 1], a[j + 1]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    me = bpy.data.meshes.new("hair")
    bm.to_mesh(me)
    o = bpy.data.objects.new("hair", me)
    bpy.context.collection.objects.link(o)
    return o


def build_hair(m):
    hair = toon("hair", m["hair"], m["hair_sh"])
    o = hair_shell(hair_cut_kagami)
    finish(o, hair, shell=0.035)
    # 天使の輪（ツヤ）
    hi = flat("hairhi", tuple(min(255, int(v * 1.22)) for v in m["hair"]))
    for side in (-1, 1):
        for k in range(5):
            az = side * (0.25 + k * 0.16)
            el = 0.72 - k * 0.04
            d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
            p = HEAD_C + HAIR_C + Vector((d.x * HAIR_R.x, d.y * HAIR_R.y, d.z * HAIR_R.z)) * 1.004
            n = Vector((d.x / HAIR_R.x, d.y / HAIR_R.y, d.z / HAIR_R.z)).normalized()
            disc(p, n, Vector((0, 0, 1)), 0.075, 0.016, hi, rot=-0.35 * side)
    # 外はね
    for side in (-1, 1):
        root, n = head_point(1.42 * side, -0.05, 0.07)
        flow = Vector((0.6 * side, 0.1, -0.8)).normalized()
        bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.11, radius2=0.0, depth=0.3)
        c = bpy.context.active_object
        c.matrix_world = frame_matrix(root + flow * 0.14, flow, n, (1, 0.45, 1))
        finish(c, hair)


def build_body(m):
    skin = toon("skin", m["skin"], m["skin_sh"])
    jacket = toon("jacket", m["jacket"], m["jacket_sh"])
    inner = toon("inner", m["inner"], (20, 20, 24))
    pants = toon("pants", m["pants"])
    shoe = toon("shoe", (60, 60, 70))
    # 頭と耳
    sphere(HEAD_C, HEAD_R, skin)
    for side in (-1, 1):
        p, n = head_point(1.5 * side, -0.12, -0.02)
        sphere(p, (0.06, 0.08, 0.11), skin, seg=24, outline=0.008)
        # ピアス
        pe, _ = head_point(1.52 * side, -0.26, 0.05)
        sphere(pe, (0.018, 0.018, 0.018), toon("pierce", (60, 60, 70)), seg=12, outline=0)
    # 首とチョーカー
    cylinder((0, 0.02, 1.5), (0, 0.02, 1.85), 0.11, 0.1, skin)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.108, minor_radius=0.024, location=(0, 0.02, 1.64))
    finish(bpy.context.active_object, toon("choker", (35, 35, 40)), outline=0.006)
    # 胴（ジャケット）と中の黒いシャツ
    cylinder((0, 0, 0.9), (0, 0, 1.3), 0.44, 0.4, jacket)
    sphere((0, 0, 1.3), (0.4, 0.34, 0.3), jacket)  # なで肩の上半身
    # V字の黒いインナー（平らな三角形を胸に貼る）
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in ((-0.14, 0.12, 0), (0.14, 0.12, 0), (0, -0.2, 0))]
    bm.faces.new(vs)
    me = bpy.data.meshes.new("inner")
    bm.to_mesh(me)
    tri = bpy.data.objects.new("inner", me)
    bpy.context.collection.objects.link(tri)
    tri.matrix_world = frame_matrix(Vector((0, -0.345, 1.42)), Vector((0, -1, 0.35)), Vector((0, 0.35, 1)), (1, 1, 1))
    me.materials.append(flat("innerflat", m["inner"]))
    # 赤いライン（腕）
    # 腕
    for side in (-1, 1):
        sh = Vector((0.36 * side, 0, 1.6))
        hand = Vector((0.55 * side, -0.05, 1.0))
        cylinder(sh, hand, 0.12, 0.1, jacket)
        sphere(sh, (0.125, 0.125, 0.125), jacket, seg=32)  # 丸い肩
        sphere(hand + Vector((0.02 * side, 0, -0.06)), (0.09, 0.09, 0.1), skin, seg=24)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.113, minor_radius=0.012,
                                         location=sh + (hand - sh) * 0.4)
        t = bpy.context.active_object
        t.rotation_mode = "QUATERNION"
        t.rotation_quaternion = (hand - sh).normalized().to_track_quat("Z", "Y")
        finish(t, flat("accent", m["accent"]), outline=0)
    # 脚と靴
    for side in (-1, 1):
        cylinder((0.15 * side, 0, 0.12), (0.15 * side, 0, 0.95), 0.13, 0.15, pants)
        sphere((0.15 * side, -0.06, 0.08), (0.14, 0.2, 0.09), shoe, seg=24)


def build_kagami(expr):
    m = KAGAMI
    build_body(m)
    build_face(m, expr)
    build_hair(m)


# ---------------------------------------------------------------- シーン
def setup_scene(res=(900, 900), samples=24):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.cycles.transparent_max_bounces = 32
    sc.cycles.max_bounces = 0
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.view_settings.view_transform = "Standard"
    sc.render.film_transparent = False
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = srgb((236, 235, 244))
    sc.world = world
    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = 50
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    return sc, cam


def aim(cam, pos, target):
    cam.location = pos
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = (Vector(target) - Vector(pos)).to_track_quat("-Z", "Y")


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "kagami_3d_test.png"
    from PIL import Image
    shots = [("normal", (0, -6.2, 1.9), (0, 0, 1.55)),
             ("serious", (0, -3.0, 2.35), (0, 0, 2.2)),
             ("laugh", (2.6, -5.4, 2.2), (0, 0, 1.6))]
    ims = []
    for i, (expr, cpos, tgt) in enumerate(shots):
        clear()
        sc, cam = setup_scene()
        build_kagami(expr)
        aim(cam, cpos, tgt)
        path = out.replace(".png", f"_{i}.png")
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        ims.append(Image.open(path).convert("RGB"))
    sheet = Image.new("RGB", (900 * len(ims), 900))
    for i, im in enumerate(ims):
        sheet.paste(im, (i * 900, 0))
    sheet.save(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
