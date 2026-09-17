# Stage 01 — parametric assembly build for United-M3BW wireless detection unit.
# Run: blender -b --factory-startup -noaudio -P scripts/build_stage01_assembly.py
# Units: 1 BU = 1 cm (per colleague's blend files). All dims traceable to
# data/device_spec.json + data/profiles.json (extracted from references/blend/enclosure.stl).

import bpy
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output", "stage01_assembly")
os.makedirs(OUT, exist_ok=True)
profiles = json.load(open(os.path.join(ROOT, "data", "profiles.json")))

# ---------- clean scene ----------
bpy.ops.wm.read_factory_settings(use_empty=True)

# ---------- materials ----------
def make_mat(name, color, metallic=0.0, roughness=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = (*color, 1.0)
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return m

MAT = {
    "housing":  make_mat("BlackAnodized", (0.020, 0.020, 0.024), 0.65, 0.42),
    "magnet":   make_mat("MagnetSilver",  (0.60, 0.62, 0.65), 0.95, 0.25),
    "steel":    make_mat("Steel",         (0.50, 0.51, 0.53), 0.95, 0.30),
    "brass":    make_mat("Brass",         (0.55, 0.40, 0.15), 0.90, 0.35),
    "gold":     make_mat("GoldPlated",    (0.83, 0.60, 0.20), 1.00, 0.25),
    "pcb":      make_mat("PCBGreen",      (0.02, 0.24, 0.07), 0.10, 0.60),
    "chip":     make_mat("ChipBlack",     (0.012, 0.012, 0.014), 0.20, 0.40),
    "white":    make_mat("JSTWhite",      (0.88, 0.86, 0.82), 0.00, 0.50),
    "battery":  make_mat("BatteryGray",   (0.35, 0.36, 0.38), 0.05, 0.55),
    "rubber":   make_mat("Rubber",        (0.030, 0.030, 0.032), 0.00, 0.90),
    "port_blk": make_mat("PortBlack",     (0.045, 0.045, 0.050), 0.30, 0.55),
    "wire_red": make_mat("WireRed",       (0.65, 0.05, 0.04), 0.00, 0.60),
    "wire_wht": make_mat("WireWhite",     (0.85, 0.85, 0.83), 0.00, 0.60),
    "wire_blu": make_mat("WireBlue",      (0.05, 0.10, 0.70), 0.00, 0.60),
    "wire_blk": make_mat("WireBlack",     (0.02, 0.02, 0.02), 0.00, 0.60),
    "coax":     make_mat("CoaxBlack",     (0.05, 0.05, 0.055), 0.10, 0.60),
    "module":   make_mat("ModuleSilver",  (0.62, 0.62, 0.64), 0.85, 0.35),
    "copper":   make_mat("Copper",        (0.72, 0.33, 0.14), 0.90, 0.35),
}

# ---------- helpers ----------
def link_obj(obj):
    bpy.context.collection.objects.link(obj)
    return obj

def prism(name, pts, z0, z1, mat):
    """Extrude 2D polygon (list of [x,y]) from z0 to z1."""
    n = len(pts)
    verts = [(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts]
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    obj = link_obj(bpy.data.objects.new(name, me))
    if mat: obj.data.materials.append(mat)
    return obj

def box(name, sx, sy, sz, loc, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    if mat: o.data.materials.append(mat)
    if bevel:
        mod = o.modifiers.new("edge", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    return o

def cyl(name, r, h, loc, mat, verts=32, bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc)
    o = bpy.context.object
    o.name = name
    if mat: o.data.materials.append(mat)
    if bevel:
        mod = o.modifiers.new("edge", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    return o

def cone(name, r1, r2, h, loc, mat, verts=32):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=h, location=loc)
    o = bpy.context.object
    o.name = name
    if mat: o.data.materials.append(mat)
    return o

def hexprism(name, r, h, loc, mat):
    return cyl(name, r, h, loc, mat, verts=6)

def bool_cut(target, cutter):
    bpy.context.view_layer.objects.active = target
    mod = target.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter)

def bool_union(target, joiner):
    bpy.context.view_layer.objects.active = target
    mod = target.modifiers.new("uni", "BOOLEAN")
    mod.operation = "UNION"
    mod.solver = "EXACT"
    mod.object = joiner
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(joiner)

def lathe(name, profile, mat, segments=48):
    """Spin (r,z) profile around Z axis. profile = list of (r, z)."""
    verts = []
    for r, z in profile:
        for i in range(segments):
            a = 2 * math.pi * i / segments
            verts.append((r * math.cos(a), r * math.sin(a), z))
    np_ = len(profile)
    faces = []
    for j in range(np_ - 1):
        for i in range(segments):
            a, b = j * segments + i, j * segments + (i + 1) % segments
            faces.append((a, b, b + segments, a + segments))
    # cap top/bottom with ngon if profile ends on axis handled by r=0 rows
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    obj = link_obj(bpy.data.objects.new(name, me))
    if mat: obj.data.materials.append(mat)
    for p in obj.data.polygons: p.use_smooth = True
    return obj

def tube(name, pts, r, mat):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = 2
    sp = cu.splines.new("NURBS")
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (*p, 1.0)
    sp.use_endpoint_u = True
    obj = link_obj(bpy.data.objects.new(name, cu))
    if mat: obj.data.materials.append(mat)
    return obj

def chamfered_rect(hx, hy, c):
    """8-pt outline, 45-deg corner chamfers of leg c."""
    return [[-hx + c, -hy], [hx - c, -hy], [hx, -hy + c], [hx, hy - c],
            [hx - c, hy], [-hx + c, hy], [-hx, hy - c], [-hx, -hy + c]]

# ---------- P01 base plate ----------
base = prism("Base_Plate", profiles["base"], 0.0, 0.67, MAT["housing"])
for sx in (-1, 1):
    for sy in (-1, 1):
        c = cyl("earhole", 0.28, 1.5, (8.11 * sx, 2.60 * sy, 0.33), None)
        bool_cut(base, c)

# ---------- P02 magnet feet x4 ----------
mag_pos = [(4.5, 2.5), (-4.5, 2.5), (4.5, -2.5), (-4.5, -2.5)]
for i, (x, y) in enumerate(mag_pos, 1):
    cyl(f"Magnet_Foot_{i:02d}", 1.25, 0.5, (x, y, -0.25), MAT["magnet"], verts=40, bevel=0.05)

# ---------- P03 body shell ----------
body = prism("Body_Shell", profiles["body"], 0.67, 4.57, MAT["housing"])
inner = prism("inner", chamfered_rect(6.65, 3.85, 0.8), 0.60, 4.90, None)
bool_cut(body, inner)
# front bulkhead port hole (dia 1.5 at x=0, z=3.2)
p1 = cyl("portcut", 0.75, 1.2, (0, -4.0, 3.2), None)
p1.rotation_euler[0] = math.radians(90)
bpy.context.view_layer.objects.active = p1
bpy.ops.object.transform_apply(rotation=True)
bool_cut(body, p1)
# USB port hole on left wall (dia 1.2 at y=-0.8, z=2.3)
p2 = cyl("usbcut", 0.60, 1.2, (-6.8, -0.8, 2.3), None)
p2.rotation_euler[1] = math.radians(90)
bpy.context.view_layer.objects.active = p2
bpy.ops.object.transform_apply(rotation=True)
bool_cut(body, p2)

# ---------- P04 lid (inverted tray) ----------
lid = prism("Lid_Plate", profiles["lid"], 4.57, 5.22, MAT["housing"])
# underside recess: skirt 0.65 deep, recess floor at 5.02 (clears battery tops at 4.87)
recess = prism("recess", chamfered_rect(7.02, 4.22, 0.92), 4.56, 5.02, None)
bool_cut(lid, recess)
# 4 countersunk screw holes at (+-6.26, +-3.66)
for sx in (-1, 1):
    for sy in (-1, 1):
        c = cyl("scut", 0.17, 1.2, (6.26 * sx, 3.66 * sy, 4.95), None)
        bool_cut(lid, c)
        cs = cone("csink", 0.36, 0.17, 0.2, (6.26 * sx, 3.66 * sy, 5.22), None)
        bool_cut(lid, cs)
# center SMA stud hole
c = cyl("smacut", 0.32, 1.4, (0, 0, 4.9), None)
bool_cut(lid, c)

# ---------- P05 lid screws x4 ----------
i = 0
for sx in (-1, 1):
    for sy in (-1, 1):
        i += 1
        x, y = 6.26 * sx, 3.66 * sy
        cone(f"Lid_Screw_{i:02d}_head", 0.36, 0.17, 0.2, (x, y, 5.12), MAT["steel"])
        cyl(f"Lid_Screw_{i:02d}_shaft", 0.17, 0.45, (x, y, 4.85), MAT["steel"])
        hexprism(f"Lid_Screw_{i:02d}_hex", 0.14, 0.06, (x, y, 5.20), MAT["port_blk"])

# ---------- P06 puck antenna (lathe) ----------
prof = [(0.0, 5.22), (2.95, 5.22), (3.0, 5.30), (3.0, 6.70),
        (2.96, 6.95), (2.86, 7.12), (2.70, 7.24), (2.45, 7.30), (0.0, 7.30)]
lathe("Puck_Antenna", prof, MAT["housing"])
# SMA feedthrough under lid center: stud + washer + nut
cyl("Antenna_Stud", 0.16, 0.9, (0, 0, 4.9), MAT["gold"], verts=24)
cyl("Antenna_Washer", 0.55, 0.06, (0, 0, 5.15), MAT["steel"], verts=32)
hexprism("Antenna_Nut", 0.45, 0.22, (0, 0, 4.72), MAT["brass"])

# ---------- P07 front bulkhead connector ----------
cyl("Bulkhead_Collar", 0.75, 0.35, (0, -4.32, 3.2), MAT["port_blk"], verts=32).rotation_euler[0] = math.radians(90)
bpy.context.view_layer.objects.active = bpy.data.objects["Bulkhead_Collar"]
bpy.ops.object.transform_apply(rotation=True)
hexprism("Bulkhead_Nut", 0.85, 0.22, (0, -4.42, 3.2), MAT["steel"]).rotation_euler[0] = math.radians(90)
bpy.context.view_layer.objects.active = bpy.data.objects["Bulkhead_Nut"]
bpy.ops.object.transform_apply(rotation=True)
cyl("Bulkhead_Inner", 0.45, 0.5, (0, -3.95, 3.2), MAT["port_blk"], verts=24).rotation_euler[0] = math.radians(90)
bpy.context.view_layer.objects.active = bpy.data.objects["Bulkhead_Inner"]
bpy.ops.object.transform_apply(rotation=True)

# ---------- P08 USB port + dust cap ----------
cyl("USB_Port", 0.55, 0.45, (-6.95, -0.8, 2.3), MAT["port_blk"], verts=32).rotation_euler[1] = math.radians(90)
bpy.context.view_layer.objects.active = bpy.data.objects["USB_Port"]
bpy.ops.object.transform_apply(rotation=True)
cyl("USB_Collar", 0.62, 0.12, (-7.02, -0.8, 2.3), MAT["port_blk"], verts=32).rotation_euler[1] = math.radians(90)
bpy.context.view_layer.objects.active = bpy.data.objects["USB_Collar"]
bpy.ops.object.transform_apply(rotation=True)
# dust cap hanging below, tethered
cyl("USB_DustCap", 0.72, 0.45, (-7.55, -0.8, 1.15), MAT["rubber"], verts=32).rotation_euler[1] = math.radians(90)
bpy.context.view_layer.objects.active = bpy.data.objects["USB_DustCap"]
bpy.ops.object.transform_apply(rotation=True)
tube("USB_Cap_Tether", [(-7.3, -0.8, 2.1), (-7.62, -0.8, 1.6), (-7.55, -0.8, 1.35)], 0.05, MAT["rubber"])

# ---------- P09..P10 batteries (colleague profile, 7.5x4x4.2) ----------
# Hex cross-section in (u=z-height vs w): bottom 7.5, sides 3.2, 1x1 chamfers, top 5.5
# lying flat: length 7.5 along y, width 4.0 along x, height 4.2
# original profile pts in (long, height) plane:
bat_profile = [(-3.75, 0.0), (3.75, 0.0), (3.75, 3.2), (2.75, 4.2),
               (-2.75, 4.2), (-3.75, 3.2)]
def make_battery(name, cx):
    # extrude profile along x, depth 4.0; rotate so profile long-axis -> y
    n = len(bat_profile)
    verts = []
    for xi in (-2.0, 2.0):
        for u, w in bat_profile:
            verts.append((xi, u, w))
    faces = []
    faces.append(tuple(range(n - 1, -1, -1)))
    faces.append(tuple(range(n, 2 * n)))
    for i in range(n):
        faces.append((i, (i + 1) % n, (i + 1) % n + n, i + n))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    o = link_obj(bpy.data.objects.new(name, me))
    o.data.materials.append(MAT["battery"])
    o.location = (cx, 0, 0.67)
    return o

make_battery("Battery_L", -4.62)
make_battery("Battery_R", 4.62)

# ---------- P11 PCB + components ----------
# board 5.2(x) x 7.5(y) x 0.16, top at z=1.51, on 4 standoffs
box("PCB_Board", 2.6, 3.75, 0.08, (0, 0, 1.43), MAT["pcb"], bevel=0.05)
for sx in (-1, 1):
    for sy in (-1, 1):
        hexprism(f"PCB_Standoff_{sx}_{sy}", 0.28, 0.68, (2.2 * sx, 3.3 * sy, 1.01), MAT["brass"])
        cyl(f"PCB_Screw_{sx}_{sy}", 0.14, 0.12, (2.2 * sx, 3.3 * sy, 1.55), MAT["steel"], verts=20)
        cyl(f"PCB_Pad_{sx}_{sy}", 0.30, 0.03, (2.2 * sx, 3.3 * sy, 1.52), MAT["gold"], verts=24)
# STM32 QFP100 center-top
box("U1_STM32", 0.75, 0.75, 0.07, (-0.3, 0.9, 1.55), MAT["chip"], bevel=0.03)
box("U1_frame", 0.82, 0.82, 0.025, (-0.3, 0.9, 1.51), MAT["steel"])
# Air724UG 4G module (right-lower)
box("U2_Air724", 1.55, 1.25, 0.12, (0.9, -1.3, 1.57), MAT["module"], bevel=0.04)
box("U2_label", 0.7, 0.7, 0.02, (0.9, -1.3, 1.64), MAT["white"])
# 2x SMA edge-mount vertical jacks
for nm, x, y in [("SMA_ANT", 0.6, 3.45), ("SMA_GNSS", 1.7, -3.45)]:
    cyl(nm, 0.32, 0.55, (x, y, 1.78), MAT["gold"], verts=24)
    cyl(nm + "_tip", 0.10, 0.15, (x, y, 2.08), MAT["gold"], verts=16)
# 3x JST PH on left edge (VBUS/batt/ext)
for j, y in enumerate([-2.4, -0.9, 1.2], 1):
    box(f"JST_{j}", 0.30, 0.42, 0.28, (-2.25, y, 1.65), MAT["white"], bevel=0.04)
# 2x 3R3 shielded inductors
for j, y in enumerate([2.3, 1.5]):
    box(f"IND_{j}", 0.36, 0.36, 0.18, (-1.3, y, 1.60), MAT["chip"], bevel=0.05)
# misc passives strip near bottom edge + regulator
for j, (x, y) in enumerate([(-1.8, -3.0), (-0.9, -3.1), (0.0, -3.0), (1.9, 0.5), (-1.9, 2.9)]):
    box(f"PASS_{j}", 0.16, 0.10, 0.06, (x, y, 1.54), MAT["steel"])
box("XTAL", 0.35, 0.25, 0.08, (-1.3, 0.1, 1.55), MAT["module"])
# header for front bulkhead harness
box("HDR_BULK", 0.5, 0.2, 0.25, (0.0, -3.3, 1.64), MAT["port_blk"])

# ---------- P12 cables ----------
# battery leads: red+black from each battery inner-top corner to JST
tube("Wire_BatL_R", [(-2.7, 1.4, 4.0), (-2.4, 1.2, 2.6), (-2.25, 1.2, 1.75)], 0.045, MAT["wire_red"])
tube("Wire_BatL_B", [(-2.7, 1.55, 4.0), (-2.4, 1.35, 2.6), (-2.25, 1.35, 1.75)], 0.045, MAT["wire_blk"])
tube("Wire_BatR_R", [(2.7, -2.2, 4.0), (2.4, -2.3, 2.6), (0.2, -2.6, 1.7), (-2.25, -2.4, 1.75)], 0.045, MAT["wire_red"])
tube("Wire_BatR_B", [(2.7, -2.05, 4.0), (2.4, -2.15, 2.6), (0.2, -2.45, 1.7), (-2.25, -2.55, 1.75)], 0.045, MAT["wire_blk"])
# 4-wire harness: front bulkhead -> HDR_BULK
for k, (mm, dz) in enumerate([("wire_red", 0.0), ("wire_wht", 0.10), ("wire_blu", 0.20), ("wire_blk", 0.30)]):
    xo = (k - 1.5) * 0.09
    tube(f"Harness_{mm}", [(xo * 0.4, -3.95, 3.1 + dz * 0.3), (xo, -3.6, 2.4), (xo * 0.6, -3.35, 1.8)],
         0.04, MAT[mm])
# coax: SMA_ANT -> up over edge -> lid center stud
tube("Coax_ANT", [(0.6, 3.45, 2.1), (0.7, 3.6, 3.4), (1.6, 3.0, 4.4), (0.6, 1.2, 4.85), (0.0, 0.0, 4.95)],
     0.075, MAT["coax"])

# ---------- organize into collections ----------
asm = bpy.data.collections.new("Assembly")
bpy.context.scene.collection.children.link(asm)
for o in list(bpy.context.collection.objects):
    for c in o.users_collection:
        c.objects.unlink(o)
    asm.objects.link(o)

# ---------- save ----------
blend_out = os.path.join(OUT, "detector_assembly.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_out)
print("saved", blend_out, "objects:", len(bpy.data.objects))
