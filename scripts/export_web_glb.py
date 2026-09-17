# Export the stage-01 assembly to GLB + web manifest for the Three.js viewer.
# Run: blender -b -noaudio output/stage01_assembly/detector_assembly.blend -P scripts/export_web_glb.py
import bpy, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
os.makedirs(WEB, exist_ok=True)

# ---- part grouping (same rules as build_manifest.py GROUPS) ----
def pcb_obj(name):
    return name.startswith(("PCB_", "PASV", "U1", "U2", "U3", "U5", "U8", "Y1",
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

# ---- story shots: 6 functional beats, same narrative as seismograph project ----
# (id, title, desc, dir, dist, target, mode, subject_parts, subject_obj_prefixes, explode, hide_lid)
SHOTS_B = [
    ("overview", "01 · OVERVIEW", "整机 · MEMS 振动感知 IoT 侦测单元",
     (1, -1, 0.75), 30, (0, 0, 3.0), "full", [], [], 0.0, False),
    ("architecture", "02 · ARCHITECTURE", "结构 · 铝壳体 / 底板 / 翻盖 / 磁吸安装",
     (1, -1, 0.9), 30, (0, 0, 2.6), "isolate",
     ["P01", "P02", "P03", "P04", "P05"], [], 0.55, False),
    ("acquisition", "03 · ACQUISITION", "采集 · MEMS 加速度计 → 前端 → STM32 主控",
     (0.45, -0.9, 1.1), 16, (0, 0, 1.6), "dim", ["P13"], [], 0.0, True),
    ("sensing", "04 · SENSING", "感知 · 磁吸底座耦合地面振动 → MEMS 加速度计",
     (0.3, -0.8, 1.0), 15, (0.6, -0.9, 1.7), "dim",
     ["P02"], ["U3_MEMS"], 0.0, True),
    ("battery", "05 · BATTERY", "供电 · 双锂电组 · 2P JST 上板",
     (0.9, -1, 0.5), 26, (0, 0, 2.6), "isolate",
     ["P11", "P12"], ["Wire_Bat"], 0.0, True),
    ("transmission", "06 · TRANSMISSION", "传输 · Air724 4G 模组 → SMA → 顶部天线帽",
     (1, -0.5, 0.9), 26, (0, 0, 3.2), "dim",
     ["P06", "P07"], ["Coax_ANT", "U2_AIR724", "J3_ANT"], 0.0, False),
]

import mathutils
def to_three(x, y, z):
    return [round(x, 3), round(z, 3), round(-y, 3)]  # blender(x,y,z)->glTF(x,z,-y)

shots = []
for (sid, title, desc, d, dist, tgt, mode, subj, objs, explode,
     hide_lid) in SHOTS_B:
    dv = mathutils.Vector(d).normalized()
    tv = mathutils.Vector(tgt)
    p = tv + dv * dist
    shots.append({"id": sid, "title": title, "desc": desc,
                  "pos": to_three(*p), "target": to_three(*tv),
                  "mode": mode, "subjects": subj, "objects": objs,
                  "explode": explode, "hide_lid": hide_lid})

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
