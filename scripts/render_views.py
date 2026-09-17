# Render validation views of the stage-01 assembly.
# Run: blender -b -noaudio output/stage01_assembly/detector_assembly.blend -P scripts/render_views.py
import bpy, math, os, sys
import mathutils

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output", "stage01_assembly", "renders")
os.makedirs(OUT, exist_ok=True)

# camera + light rig
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
bpy.context.collection.objects.link(cam)
bpy.context.scene.camera = cam
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
sun.data.energy = 4
sun.rotation_euler = (math.radians(55), 0, math.radians(35))
bpy.context.collection.objects.link(sun)
fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", "SUN"))
fill.data.energy = 1.5
fill.rotation_euler = (math.radians(60), 0, math.radians(-120))
bpy.context.collection.objects.link(fill)

sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "MATERIAL"
sc.display.shading.show_shadows = True
sc.display.shading.show_cavity = True
sc.render.resolution_x = 960
sc.render.resolution_y = 720
sc.render.film_transparent = False
sc.world = bpy.data.worlds.new("W")
sc.world.color = (0.05, 0.05, 0.06)

def shot(name, direction, ortho_scale, target=(0, 0, 3.0), hide=()):
    for h in hide:
        o = bpy.data.objects.get(h)
        if o: o.hide_render = True
    dv = mathutils.Vector(direction).normalized()
    tgt = mathutils.Vector(target)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = ortho_scale
    cam.location = tgt + dv * 60
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name)
    for h in hide:
        o = bpy.data.objects.get(h)
        if o: o.hide_render = False

lid_parts = ["Lid_Plate", "Puck_Antenna", "Antenna_Boss", "Antenna_Stud",
             "Antenna_Washer", "Antenna_Nut", "Coax_ANT"] + \
            [f"Lid_Screw_{i:02d}_{p}" for i in range(1, 5) for p in ("head", "shaft", "hex")]

shot("iso",      (1, -1, 0.75), 24)
shot("front",    (0, -1, 0.12), 22)
shot("top",      (0, 0.01, 1), 21)
shot("side",     (1, 0, 0.12), 20)
shot("bottom",   (0, 0.01, -1), 21)
shot("open_top", (0.15, 0.05, 1), 20, target=(0, 0, 2.5), hide=lid_parts)
shot("open_iso", (1, -1, 1.0), 22, target=(0, 0, 2.5), hide=lid_parts)
print("done ->", OUT)
