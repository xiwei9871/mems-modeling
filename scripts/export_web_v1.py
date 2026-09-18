"""Export the V1 interactive product scene: semantic GLB + manifest_v1.json.

Blender-only script — run:
    blender -b detector_assembly.blend -P scripts/export_web_v1.py

What it does (mirrors the seismograph project's export_story_glb_v1.py):
  1. reparents every object under per-part Empties (anchor = part origin)
  2. writes glTF extras: semanticId/systemId/sourcePart/role/flags
  3. clones materials per object so runtime fades never bleed across parts,
     and darkens housing/battery clones (env light washes them out on web)
  4. exports detector_assembly.glb (extras on, no animation/cameras)
  5. emits web/manifest_v1.json: systems + components(assembled/inspect/
     extract/explodeOffset) + cameraPresets — all coords Blender Z-up -> Y-up
"""

import json
import math
import os
import sys

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import semantic_map_m3bw as SM  # noqa: E402

WEB = os.path.join(ROOT, "web")
GLB_OUT = os.path.join(WEB, "detector_assembly.glb")
MANIFEST_OUT = os.path.join(WEB, "manifest_v1.json")

# material clones that wash out under three.js env light -> scale base color
DARKEN = {"DarkGrayAnodized": 0.30, "BatteryGray": 0.45}


def yup(v):
    return [round(v[0], 4), round(v[2], 4), round(-v[1], 4)]


def reparent_keep_world(obj, parent):
    # matrix_parent_inverse cancels the parent's transform so the child's
    # world position is preserved (the standard "parent without moving")
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()


def new_empty(name, loc):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.location = loc
    return e


def tag(obj, extras):
    for k, v in extras.items():
        obj[k] = v


def main():
    SM.validate()
    scene = bpy.context.scene
    objects = list(scene.objects)

    # ---- 1. resolve every object to a part ---------------------------------
    assignment = {}                       # obj -> partId
    leftovers = []
    for o in objects:
        pid = SM.part_of(o.name)
        if pid:
            assignment[o] = pid
        else:
            leftovers.append(o)
    for o in leftovers:                   # catch-all -> board
        assignment[o] = "PRT_PCB"
    print(f"parts: {len(set(assignment.values()))}, "
          f"objects: {len(objects)}, board catch-all: {len(leftovers)}")

    # ---- 2. part empties + reparent + component extras ---------------------
    part_empties = {}
    for pid, spec in SM.PARTS.items():
        e = new_empty(pid, spec["anchor"])
        role = spec["role"]
        tag(e, {
            "semanticId": spec["semanticId"],
            "type": "component",
            "systemId": spec["systemId"],
            "sourcePart": pid,
            "displayName": spec["displayName"],
            "role": role,
            "selectable": True,
            "hoverable": True,
            "inspectable": bool(spec.get("inspectable", True)),
            "presentationPriority": {"HERO": 100, "PRIMARY": 70,
                                     "SECONDARY": 40, "SUPPORT": 20}[role],
        })
        part_empties[pid] = e

    bpy.context.view_layer.update()   # evaluate empty matrices before inverting
    for o, pid in assignment.items():
        reparent_keep_world(o, part_empties[pid])

    # ---- 3. child semantic tags (single primary object per tag) ------------
    tagged = 0
    for tid, spec in SM.CHILD_TAGS.items():
        cands = [o for o in objects
                 if any(o.name == m or o.name.startswith(m)
                        for m in spec["members"])]
        if not cands:
            print(f"WARNING: child tag {tid} matched nothing")
            continue
        primary = min(cands, key=lambda o: len(o.name))   # base object, not pins
        tag(primary, {
            "semanticId": spec["semanticId"],
            "type": spec["type"],
            "systemId": spec["systemId"],
            "sourcePart": spec["sourcePart"],
            "displayName": spec["displayName"],
            "role": spec["role"],
            "selectable": True,
            "hoverable": True,
            "inspectable": False,
            "presentationPriority": 30,
        })
        tagged += 1
    print(f"child tags: {tagged}")

    # ---- 4. DEVICE_ROOT + SYS_* anchors -------------------------------------
    root = new_empty("DEVICE_ROOT", (0, 0, 0))
    tag(root, {"semanticId": "DEVICE_ROOT", "type": "device",
               "displayName": "United-M3BW MEMS Vibration Unit"})
    for sys_id, spec in SM.SYSTEMS.items():
        e = new_empty(sys_id, (0, 0, 0))
        e.parent = root
        tag(e, {"semanticId": sys_id, "type": "system",
                "displayName": spec["displayName"],
                "oneLiner": spec["oneLiner"]})

    # ---- 5. per-object material clones + selective darken -------------------
    cloned = 0
    for o in objects:
        if o.type != "MESH":
            continue
        for slot in o.material_slots:
            if not slot.material:
                continue
            orig_name = slot.material.name.split(".")[0]
            m = slot.material.copy()
            slot.material = m
            cloned += 1
            if orig_name in DARKEN:
                bsdf = m.node_tree.nodes.get("Principled BSDF")
                if bsdf:
                    c = bsdf.inputs["Base Color"].default_value
                    f = DARKEN[orig_name]
                    bsdf.inputs["Base Color"].default_value = (
                        c[0] * f, c[1] * f, c[2] * f, c[3])
    print(f"materials cloned: {cloned}")

    # ---- 6. export GLB -------------------------------------------------------
    os.makedirs(WEB, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=GLB_OUT, export_format="GLB",
        export_animations=False, export_extras=True,
        export_cameras=False, export_yup=True, use_visible=True,
    )
    print(f"glb -> {GLB_OUT} ({os.path.getsize(GLB_OUT) / 1e6:.1f} MB)")

    # ---- 7. manifest_v1.json -------------------------------------------------
    components = {}
    for pid, spec in SM.PARTS.items():
        e = part_empties[pid]
        comp = {
            "semanticId": spec["semanticId"],
            "systemId": spec["systemId"],
            "displayName": spec["displayName"],
            "role": spec["role"],
            "inspectable": bool(spec.get("inspectable", True)),
            "assembled": yup(e.location),
        }
        if "inspect" in spec:
            comp["inspect"] = yup(spec["inspect"])
        if "extractDirection" in spec:
            comp["extractDirection"] = yup(spec["extractDirection"])
        if "explodeOffset" in spec:
            comp["explodeOffset"] = yup(spec["explodeOffset"])
        components[pid] = comp

    systems = {}
    for sys_id, spec in SM.SYSTEMS.items():
        systems[sys_id] = {
            "displayName": spec["displayName"],
            "oneLiner": spec["oneLiner"],
            "order": spec["order"],
            "parts": list(spec["parts"]),
            "explodeVector": yup(spec["explode"]),
        }

    def conv_preset(p):
        out = {"position": yup(p["position"]), "target": yup(p["target"])}
        if p.get("lens_mm"):
            out["lens_mm"] = p["lens_mm"]
        return out

    presets = {}
    for name, p in SM.CAMERA_PRESETS.items():
        if "position" in p:
            presets[name] = conv_preset(p)
        else:
            presets[name] = {k: conv_preset(v) for k, v in p.items()}

    manifest = {
        "version": 1,
        "glb": "detector_assembly.glb",
        "unit": "cm",
        "systems": systems,
        "components": components,
        "cameraPresets": presets,
    }
    with open(MANIFEST_OUT, "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"manifest -> {MANIFEST_OUT} "
          f"({len(components)} components, {len(systems)} systems)")


main()
