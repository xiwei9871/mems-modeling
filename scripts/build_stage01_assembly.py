# Stage 01 — parametric assembly build for United-M3BW wireless detection unit.
# Run: blender -b --factory-startup -noaudio -P scripts/build_stage01_assembly.py
# Units: 1 BU = 1 cm (per colleague's blend files). All dims traceable to
# data/device_spec.json + data/profiles.json (extracted from references/blend/enclosure.stl).

import bpy
import json
import math
import os
import sys

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
    "housing":  make_mat("DarkGrayAnodized", (0.13, 0.13, 0.145), 0.55, 0.50),
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
    "ceramic":  make_mat("CeramicTan",    (0.62, 0.52, 0.34), 0.05, 0.55),
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

def bool_intersect(target, cutter):
    bpy.context.view_layer.objects.active = target
    mod = target.modifiers.new("int", "BOOLEAN")
    mod.operation = "INTERSECT"
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
# USB-C port hole on +y wall (opposite the bulkhead wall), x=+1.0, z=3.2
p2 = cyl("usbcut", 0.60, 1.2, (1.0, 4.0, 3.2), None)
p2.rotation_euler[0] = math.radians(90)
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
# SMA feedthrough under lid center: machined alu boss + gold stud + nut
cyl("Antenna_Boss", 1.30, 0.28, (0, 0, 4.88), MAT["steel"], verts=48)
cyl("Antenna_Stud", 0.16, 1.1, (0, 0, 4.8), MAT["gold"], verts=24)
cyl("Antenna_Washer", 0.55, 0.06, (0, 0, 4.70), MAT["steel"], verts=32)
hexprism("Antenna_Nut", 0.45, 0.22, (0, 0, 4.55), MAT["brass"])

# ---------- P07 front bulkhead connector (nut+body inside per photo) ----------
# outside: small threaded stub only
cyl("Bulkhead_Stub", 0.38, 0.35, (0, -4.28, 3.2), MAT["port_blk"], verts=32).rotation_euler[0] = math.radians(90)
bpy.context.view_layer.objects.active = bpy.data.objects["Bulkhead_Stub"]
bpy.ops.object.transform_apply(rotation=True)
# inside: hex nut against wall + round knurled body
hexprism("Bulkhead_Nut", 0.85, 0.25, (0, -3.95, 3.2), MAT["steel"]).rotation_euler[0] = math.radians(90)
bpy.context.view_layer.objects.active = bpy.data.objects["Bulkhead_Nut"]
bpy.ops.object.transform_apply(rotation=True)
cyl("Bulkhead_Body", 0.62, 0.55, (0, -3.62, 3.2), MAT["port_blk"], verts=32).rotation_euler[0] = math.radians(90)
bpy.context.view_layer.objects.active = bpy.data.objects["Bulkhead_Body"]
bpy.ops.object.transform_apply(rotation=True)
cyl("Bulkhead_Back", 0.45, 0.4, (0, -3.35, 3.2), MAT["port_blk"], verts=24).rotation_euler[0] = math.radians(90)
bpy.context.view_layer.objects.active = bpy.data.objects["Bulkhead_Back"]
bpy.ops.object.transform_apply(rotation=True)

# ---------- P08 USB-C port + tethered dust cap on +y wall (x=+1.0, z=3.2) ----------
# round rubber grommet surround + recessed USB-C slot
cyl("USB_Port", 0.50, 0.40, (1.0, 4.15, 3.2), MAT["port_blk"], verts=32).rotation_euler[0] = math.radians(90)
bpy.context.view_layer.objects.active = bpy.data.objects["USB_Port"]
bpy.ops.object.transform_apply(rotation=True)
cyl("USB_Collar", 0.66, 0.18, (1.0, 4.28, 3.2), MAT["rubber"], verts=40).rotation_euler[0] = math.radians(90)
bpy.context.view_layer.objects.active = bpy.data.objects["USB_Collar"]
bpy.ops.object.transform_apply(rotation=True)
box("USB_Slot", 0.42, 0.04, 0.15, (1.0, 4.38, 3.2), MAT["port_blk"], bevel=0.05)
# dust cap hangs below the port on its tether
cyl("USB_DustCap", 0.68, 0.35, (1.05, 4.75, 1.25), MAT["rubber"], verts=32).rotation_euler[0] = math.radians(90)
bpy.context.view_layer.objects.active = bpy.data.objects["USB_DustCap"]
bpy.ops.object.transform_apply(rotation=True)
tube("USB_Cap_Tether", [(1.0, 4.45, 2.85), (1.15, 4.68, 2.1), (1.05, 4.74, 1.45)], 0.055, MAT["rubber"])

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
    # chamfer plan-view corners (potted pack) so corners stay inside body chamfer
    cpts = [[cx + x, y] for x, y in chamfered_rect(2.0, 3.75, 0.9)]
    bool_intersect(o, prism("batcut", cpts, -1.0, 6.5, None))
    return o

make_battery("Battery_L", -4.62)
make_battery("Battery_R", 4.62)

# ---------- P11 PCB assembly (per scripts/pcb_layout.py) ----------
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import pcb_layout as PL

ZB = PL.BOARD_TOP_Z                      # 1.51 (board top surface)
HX, HY = PL.BOARD["x"] / 2, PL.BOARD["y"] / 2

# board mesh: manual box so the top face gets a full-bleed UV + texture
bx = [-HX, HX, HX, -HX]
by = [-HY, -HY, HY, HY]
z0, z1 = ZB - PL.BOARD["t"], ZB
verts = [(x, y, z0) for x, y in zip(bx, by)] + [(x, y, z1) for x, y in zip(bx, by)]
faces = [(0, 3, 2, 1), (4, 5, 6, 7),
         (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
me = bpy.data.meshes.new("PCB_Board")
me.from_pydata(verts, [], faces)
me.update()
board = link_obj(bpy.data.objects.new("PCB_Board", me))
board.data.materials.append(MAT["pcb"])                       # sides/bottom
topmat = bpy.data.materials.new("PCBTop")
topmat.use_nodes = True
topmat.diffuse_color = (0.02, 0.24, 0.07, 1)
_bsdf = topmat.node_tree.nodes["Principled BSDF"]
_tex = topmat.node_tree.nodes.new("ShaderNodeTexImage")
_tex.image = bpy.data.images.load(os.path.join(ROOT, "assets", "pcb_surface.png"))
topmat.node_tree.links.new(_tex.outputs["Color"], _bsdf.inputs["Base Color"])
_bsdf.inputs["Roughness"].default_value = 0.62
board.data.materials.append(topmat)                           # top face index 1
board.data.polygons[1].material_index = 1
uv = board.data.uv_layers.new(name="UVTop")
for poly in board.data.polygons:
    for li in poly.loop_indices:
        if poly.index == 1:
            vx, vy, _ = board.data.vertices[board.data.loops[li].vertex_index].co
            uv.data[li].uv = ((vx + HX) / (2 * HX), (vy + HY) / (2 * HY))
        else:
            uv.data[li].uv = (0.012, 0.012)                   # border = plain green
# 4 mounting holes + plated rings + standoffs + screws
for i, (hx, hy) in enumerate(PL.MOUNT_HOLES, 1):
    c = cyl(f"mhcut{i}", PL.MOUNT_HOLE_R, 0.5, (hx, hy, ZB - 0.08), None, verts=20)
    bool_cut(board, c)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.27, minor_radius=0.055,
                                   major_segments=24, minor_segments=8,
                                   location=(hx, hy, ZB))
    ring = bpy.context.object; ring.name = f"PCB_Ring_{i}"
    ring.data.materials.append(MAT["gold"])
    hexprism(f"PCB_Standoff_{i}", 0.28, 0.68, (hx, hy, 1.01), MAT["brass"])
    cyl(f"PCB_Screw_{i}", 0.15, 0.12, (hx, hy, ZB + 0.04), MAT["steel"], verts=20)

def comp_box(name, c, hoff=0.0):
    w, d, h = c["size"]
    return box(name, w / 2, d / 2, h / 2, (c["pos"][0], c["pos"][1], ZB + h / 2 + hoff), None)

for c in PL.COMPONENTS:
    t, (cx, cy) = c["type"], c["pos"]
    if t == "qfp":
        o = comp_box(c["id"], c, 0.02); o.data.materials.append(MAT["chip"])
        o.modifiers.new("edge", "BEVEL").width = 0.03
        w, d = c["size"][0], c["size"][1]
        for sx in (-1, 1):
            box(f"{c['id']}_pins_x{sx}", 0.06, d / 2 + 0.08, 0.02,
                (cx + sx * (w / 2 + 0.09), cy, ZB + 0.02), MAT["steel"])
        for sy in (-1, 1):
            box(f"{c['id']}_pins_y{sy}", w / 2 + 0.08, 0.06, 0.02,
                (cx, cy + sy * (d / 2 + 0.09), ZB + 0.02), MAT["steel"])
    elif t == "module":
        o = comp_box(c["id"], c); o.data.materials.append(MAT["module"])
        o.modifiers.new("edge", "BEVEL").width = 0.04
        w, d, h = c["size"]
        box(c["id"] + "_label", w * 0.28, d * 0.30, 0.015,
            (cx, cy, ZB + h + 0.008), MAT["white"])
        # castellated edge bumps along -y and +y
        for sy in (-1, 1):
            for k in range(10):
                px = cx - w / 2 + (k + 0.5) * w / 10
                box(f"{c['id']}_pad{sy}_{k}", 0.05, 0.05, 0.03,
                    (px, cy + sy * (d / 2 - 0.03), ZB + 0.015), MAT["gold"])
    elif t == "sensor":
        # ADI MEMS accelerometer: beige ceramic LCC body + dark lid + pins
        o = comp_box(c["id"], c); o.data.materials.append(MAT["ceramic"])
        o.modifiers.new("edge", "BEVEL").width = 0.02
        w, d, h = c["size"]
        box(c["id"] + "_lid", w * 0.32, d * 0.32, 0.012,
            (cx, cy, ZB + h + 0.006), MAT["port_blk"])
        for sx in (-1, 1):
            for k in range(4):
                py = cy - d * 0.32 + k * d * 0.21
                box(f"{c['id']}_pin{sx}_{k}", 0.045, 0.05, 0.02,
                    (cx + sx * (w / 2 + 0.005), py, ZB + 0.01), MAT["gold"])
    elif t in ("ic", "block", "xtal"):
        o = comp_box(c["id"], c); o.data.materials.append(MAT["chip"] if t != "xtal" else MAT["module"])
        o.modifiers.new("edge", "BEVEL").width = 0.02
    elif t == "sot223":
        o = comp_box(c["id"], c); o.data.materials.append(MAT["chip"])
        box(c["id"] + "_tab", c["size"][0] / 3, 0.06, 0.02,
            (cx, cy - c["size"][1] / 2 - 0.05, ZB + 0.01), MAT["steel"])
    elif t == "sma":
        hexprism(c["id"] + "_base", 0.45, 0.5, (cx, cy, ZB + 0.25), MAT["gold"])
        cyl(c["id"] + "_body", 0.31, 0.62, (cx, cy, ZB + 0.31), MAT["gold"], verts=24)
        cyl(c["id"] + "_diel", 0.20, 0.03, (cx, cy, ZB + 0.63), MAT["white"], verts=20)
        cyl(c["id"] + "_pin", 0.05, 0.05, (cx, cy, ZB + 0.64), MAT["gold"], verts=12)
    elif t in ("jst", "jst_sm"):
        s = 1.0 if t == "jst" else 0.75
        npins = c.get("pins", 4)
        long_ = 0.14 * npins * s + 0.1          # housing length along pin row
        dep, hgt = 0.30 * s, 0.30 * s
        along_y = c.get("dir", "y") == "y"      # edge JSTs: pin row along y
        o = box(c["id"], dep / 2 if along_y else long_ / 2,
                long_ / 2 if along_y else dep / 2,
                hgt, (cx, cy, ZB + hgt), MAT["white"], bevel=0.03)
        # contact bumps along the pin row
        for k in range(npins):
            off = (k - (npins - 1) / 2) * 0.135 * s
            px, py = (cx, cy + off) if along_y else (cx + off, cy)
            box(f"{c['id']}_p{k}", 0.06 * s, 0.06 * s, 0.05,
                (px, py, ZB + 2 * hgt - 0.03), MAT["port_blk"])
    elif t == "inductor":
        o = comp_box(c["id"], c); o.data.materials.append(MAT["chip"])
        o.modifiers.new("edge", "BEVEL").width = 0.06

# deterministic passive sprinkle in zones, skipping component footprints
import random as _r
def _fp(c):
    if c["type"] == "sma": s = 0.55
    elif c["type"] in ("jst", "jst_sm"): s = None
    else: s = None
    if s is not None:
        return (c["pos"][0]-s, c["pos"][1]-s, c["pos"][0]+s, c["pos"][1]+s)
    if "size" in c:
        w, d = c["size"][0], c["size"][1]
    else:
        w = d = 0.6 * len(str(c.get("pins", 4)))
    m = 0.16
    return (c["pos"][0]-w/2-m, c["pos"][1]-d/2-m, c["pos"][0]+w/2+m, c["pos"][1]+d/2+m)
_fps = [_fp(c) for c in PL.COMPONENTS]
_rg = _r.Random(PL.PASSIVE_SEED)
_pi = 0
for zx0, zy0, zx1, zy1, n in PL.PASSIVE_ZONES:
    placed = 0
    tries = 0
    while placed < n and tries < 200:
        tries += 1
        px = _rg.uniform(zx0, zx1); py = _rg.uniform(zy0, zy1)
        if any(a <= px <= b and c0 <= py <= d0 for a, c0, b, d0 in _fps):
            continue
        w = _rg.choice([0.16, 0.20, 0.10]); dp = _rg.choice([0.08, 0.10, 0.16])
        if _rg.random() < 0.5: w, dp = dp, w
        o = box(f"PASV_{_pi:02d}", w / 2, dp / 2, 0.045, (px, py, ZB + 0.045), MAT["chip"])
        _pi += 1; placed += 1

# ---------- P12 cables ----------
# battery leads: +x pack -> J1 on +x edge; -x pack -> J7 on -x edge
tube("Wire_BatR_R", [(2.65, -1.6, 4.1), (2.55, 0.2, 2.7), (2.3, 0.82, 1.75)], 0.045, MAT["wire_red"])
tube("Wire_BatR_B", [(2.65, -1.45, 4.1), (2.55, 0.35, 2.7), (2.3, 0.98, 1.75)], 0.045, MAT["wire_blk"])
tube("Wire_BatL_R", [(-2.65, -3.0, 4.1), (-2.5, -2.7, 2.7), (-2.3, -2.47, 1.75)], 0.045, MAT["wire_red"])
tube("Wire_BatL_B", [(-2.65, -2.85, 4.1), (-2.5, -2.55, 2.7), (-2.3, -2.32, 1.75)], 0.045, MAT["wire_blk"])
# 4-wire harness: bulkhead inside back shell -> JB_BULK jst
for k, (mm, dz) in enumerate([("wire_red", 0.0), ("wire_wht", 0.10), ("wire_blu", 0.20), ("wire_blk", 0.30)]):
    xo = (k - 1.5) * 0.09
    tube(f"Harness_{mm}", [(xo * 0.3, -3.3, 3.3 + dz), (0.15 + xo, -3.3, 2.4), (0.4 + xo * 0.5, -3.0, 1.72)],
         0.04, MAT[mm])
# USB internal harness: +y-wall port -> down -> along +x wall floor -> J1
tube("USB_Harness", [(1.0, 3.95, 3.1), (1.1, 3.8, 1.6), (2.2, 3.4, 1.0),
                     (2.45, 1.2, 1.0), (2.35, -0.2, 1.45)],
     0.075, MAT["wire_wht"])
# coax: J3 ANT sma (+x edge) -> up to lid stud
tube("Coax_ANT", [(2.1, -2.0, 2.15), (2.3, -1.9, 3.5), (1.3, -0.8, 4.6),
                  (0.3, -0.1, 4.9), (0.0, 0.0, 4.97)], 0.075, MAT["coax"])

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
