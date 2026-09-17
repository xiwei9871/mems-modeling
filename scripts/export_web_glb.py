# Export the stage-01 assembly to GLB + web manifest for the Three.js viewer.
# Run: blender -b -noaudio output/stage01_assembly/detector_assembly.blend -P scripts/export_web_glb.py
import bpy, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
os.makedirs(WEB, exist_ok=True)

# ---- part grouping (same rules as build_manifest.py GROUPS) ----
def pcb_obj(name):
    return name.startswith(("PCB_", "PASV", "U1", "U2", "U5", "U8", "Y1",
                            "Q1", "Q2", "L1", "L2", "J1", "J2", "J3", "J4",
                            "J6", "J7", "JB", "XT1"))

def wire_obj(name):
    return name.startswith(("Wire_", "Harness_", "Coax", "USB_H"))

GROUPS = [
    ("P01", "Base_Plate",     lambda n: n == "Base_Plate",        (0, 0, 0)),
    ("P02", "Magnet_Feet",    lambda n: n.startswith("Magnet_Foot"), (0, 0, -1.4)),
    ("P03", "Body_Shell",     lambda n: n == "Body_Shell",        (0, 0, 0)),
    ("P04", "Lid_Plate",      lambda n: n == "Lid_Plate",         (0, 0, 4.0)),
    ("P05", "Lid_Screws",     lambda n: n.startswith("Lid_Screw"),(0, 0, 4.8)),
    ("P06", "Puck_Antenna",   lambda n: n == "Puck_Antenna",      (0, 0, 6.0)),
    ("P07", "Antenna_Mount",  lambda n: n.startswith("Antenna_"), (0, 0, 4.4)),
    ("P08", "Front_Bulkhead", lambda n: n.startswith("Bulkhead_"),(0, -2.5, 0)),
    ("P09", "USB_Port",       lambda n: n in ("USB_Port", "USB_Collar", "USB_Slot"), (0, 2.5, 0)),
    ("P10", "USB_DustCap",    lambda n: n.startswith("USB_Dust") or n == "USB_Cap_Tether", (0, 3.2, -0.6)),
    ("P11", "Battery_L",      lambda n: n == "Battery_L",         (-3.5, 0, 0)),
    ("P12", "Battery_R",      lambda n: n == "Battery_R",         (3.5, 0, 0)),
    ("P13", "PCB_Assembly",   pcb_obj,                            (0, 0, 1.6)),
    ("P14", "Wiring",         wire_obj,                           (0, 0, 0.4)),
]

parts = []
assigned = set()
for pid, name, pred, explode in GROUPS:
    objs = sorted(o.name for o in bpy.data.objects if pred(o.name))
    assigned.update(objs)
    parts.append({"id": pid, "name": name, "objects": objs,
                  "explode": list(explode)})
leftover = sorted(o.name for o in bpy.data.objects
                  if o.type == "MESH" and o.name not in assigned)
if leftover:
    parts.append({"id": "PXX", "name": "Ungrouped", "objects": leftover,
                  "explode": [0, 0, 0]})
    print("WARNING ungrouped objects:", leftover)

LID_HIDE = (["Lid_Plate", "Puck_Antenna", "Antenna_Boss", "Antenna_Stud",
             "Antenna_Washer", "Antenna_Nut", "Coax_ANT"] +
            [n for p in parts if p["id"] == "P05" for n in p["objects"]])

# ---- shots: direction/dist/target in BLENDER coords -> converted below ----
SHOTS_B = [
    ("iso",   "整机 ISO",   (1, -1, 0.75),  30, (0, 0, 3.0), False),
    ("front", "正面 · 连接器", (0, -1, 0.15), 26, (0, 0, 3.0), False),
    ("back",  "背面 · USB",  (0.15, 1, 0.18), 26, (0, 0, 3.0), False),
    ("top",   "顶视",        (0, 0, 1),      30, (0, 0, 2.5), False),
    ("bottom","底部 · 磁脚",  (0.3, -0.8, -1), 28, (0, 0, 1.0), False),
    ("open",  "开盖内构",    (1, -1, 1.0),   26, (0, 0, 2.5), True),
    ("pcb",   "PCB 特写",    (0.45, -0.9, 1.1), 15, (0, 0, 1.6), True),
]

import mathutils
def to_three(x, y, z):
    return [round(x, 3), round(z, 3), round(-y, 3)]  # blender(x,y,z)->glTF(x,z,-y)

shots = []
for sid, title, d, dist, tgt, hide_lid in SHOTS_B:
    dv = mathutils.Vector(d).normalized()
    tv = mathutils.Vector(tgt)
    p = tv + dv * dist
    shots.append({"id": sid, "title": title,
                  "pos": to_three(*p), "target": to_three(*tv),
                  "hide_lid": hide_lid})

manifest = {
    "glb": "detector_assembly.glb",
    "title": "UNITED-M3BW 智能无线侦测单元",
    "subtitle": "mems_modeling · stage-01 assembly",
    "units": "cm",
    "lid_hide": LID_HIDE,
    "parts": parts,
    "shots": shots,
}
mpath = os.path.join(WEB, "manifest.json")
json.dump(manifest, open(mpath, "w"), indent=1, ensure_ascii=False)
print("manifest ->", mpath, f"({len(parts)} parts, {len(shots)} shots)")

gpath = os.path.join(WEB, "detector_assembly.glb")
bpy.ops.export_scene.gltf(
    filepath=gpath,
    export_format="GLB",
    export_apply=True,
    export_yup=True,
    export_texcoords=True,
    export_normals=True,
    export_materials="EXPORT",
    export_image_format="AUTO",
)
print("glb ->", gpath, f"({os.path.getsize(gpath)/1e6:.1f} MB)")
