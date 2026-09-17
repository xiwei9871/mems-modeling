# Generate parts manifest from the stage-01 assembly blend.
# Run: blender -b -noaudio output/stage01_assembly/detector_assembly.blend -P scripts/build_manifest.py
import bpy, json, os, csv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GROUPS = [
    ("P01", "Base_Plate",        ["Base_Plate"],                          "aluminum, black anodized", "measured: 17x9x0.67 + 4 ear tabs w/ holes", "colleague STL outline"),
    ("P02", "Magnet_Feet",       ["Magnet_Foot_01","Magnet_Foot_02","Magnet_Foot_03","Magnet_Foot_04"], "magnet, silver", "user: dia~2.5 x h0.5, under base corners", "measured from STL"),
    ("P03", "Body_Shell",        ["Body_Shell"],                          "aluminum, black anodized", "13.8x8.4 chamfered, wall ~0.25-0.35", "colleague STL + wall t est."),
    ("P04", "Lid_Plate",         ["Lid_Plate"],                           "aluminum, black anodized", "14.5x9x0.65 inverted tray, skirt 0.5", "colleague STL"),
    ("P05", "Lid_Screws",        [o.name for o in bpy.data.objects if o.name.startswith("Lid_Screw")], "steel", "4x flathead hex-socket", "measured hole pos"),
    ("P06", "Puck_Antenna",      ["Puck_Antenna"],                        "housing plastic/metal", "dia 6 x h2 dome, 4G antenna", "user + colleague STL"),
    ("P07", "Antenna_Mount",     ["Antenna_Stud","Antenna_Washer","Antenna_Nut"], "gold/brass/steel", "SMA feedthrough thru lid", "inferred from photo"),
    ("P08", "Front_Bulkhead",    ["Bulkhead_Collar","Bulkhead_Nut","Bulkhead_Inner"], "black+steel", "round panel connector dia~1.5, front wall z=3.2", "measured from STL"),
    ("P09", "USB_Port",          ["USB_Port","USB_Collar"],               "black+steel", "round USB-C jack dia~1.1, left wall", "estimated from photo"),
    ("P10", "USB_DustCap",       ["USB_DustCap","USB_Cap_Tether"],        "rubber", "tethered cap, hangs at left wall", "estimated from photo"),
    ("P11", "Battery_L",         ["Battery_L"],                           "gray potted pack", "7.5x4.0x4.2 hex prism (colleague)", "colleague blend, mirrored pos"),
    ("P12", "Battery_R",         ["Battery_R"],                           "gray potted pack", "7.5x4.0x4.2 hex prism (colleague)", "colleague blend, mirrored pos"),
    ("P13", "PCB_Assembly",      [o.name for o in bpy.data.objects if o.name.startswith(("PCB_","U1","U2","SMA","JST","IND","PASS","XTAL","HDR"))], "FR4 green + parts", "~5.2x7.5x0.16 on 4 standoffs; STM32+Air724+2SMA+3JST+2x3R3", "estimated from photo"),
    ("P14", "Wiring",            [o.name for o in bpy.data.objects if o.name.startswith(("Wire_","Harness_","Coax"))], "wire/coax", "battery leads, bulkhead 4-wire, antenna coax", "estimated from photo"),
]

rows = []
for pid, name, objs, mat, desc, basis in GROUPS:
    xs=[];ys=[];zs=[]
    for n in objs:
        o = bpy.data.objects.get(n)
        if not o: continue
        for c in o.bound_box:
            w = o.matrix_world @ __import__("mathutils").Vector(c)
            xs.append(w.x); ys.append(w.y); zs.append(w.z)
    if not xs: continue
    rows.append({"part_id": pid, "name": name, "objects": len(objs), "material": mat,
                 "desc": desc, "basis": basis,
                 "bbox": {"x": [round(min(xs),2), round(max(xs),2)],
                          "y": [round(min(ys),2), round(max(ys),2)],
                          "z": [round(min(zs),2), round(max(zs),2)]}})

js = os.path.join(ROOT, "data", "parts_manifest.json")
json.dump({"assembly": "United-M3BW detector", "units": "cm", "parts": rows}, open(js, "w"), indent=1, ensure_ascii=False)
csvf = os.path.join(ROOT, "data", "parts_manifest.csv")
with open(csvf, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["part_id","name","objects","material","desc","basis","bbox_x","bbox_y","bbox_z"])
    for r in rows:
        w.writerow([r["part_id"], r["name"], r["objects"], r["material"], r["desc"], r["basis"],
                    r["bbox"]["x"], r["bbox"]["y"], r["bbox"]["z"]])
print("manifest:", len(rows), "parts ->", js)
