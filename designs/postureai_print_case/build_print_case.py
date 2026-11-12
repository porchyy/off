"""Build a two-part 3D-printable OffSyn Tech enclosure in Blender.

Dimensions are millimetres; the case is purposely based on the latest
hand-drawn front layout.  The shell and rear cover export separately as STL.
"""

import bpy
import math
import os


# External enclosure dimensions.
W, H, D = 160.0, 240.0, 80.0
WALL = 3.0
CORNER_R = 10.0
CLEARANCE = 0.35

# Front feature locations. Coordinate origin: centre of front, bottom edge.
CAMERA_D = 23.5
CAMERA_Z = 190.0             # requested camera-centre height from the base
LIGHT_D = 6.0                # exposed BH1750 light aperture
LIGHT_Z = 168.0
LCD_W, LCD_H, LCD_Z = 95.0, 33.0, 135.0
LED_D, LED_Z = 8.0, 80.0
SPEAKER_W, SPEAKER_H, SPEAKER_Z = 68.0, 29.0, 38.0

BASE = os.path.dirname(os.path.abspath(__file__))
BLEND = os.path.join(BASE, "postureai-front-layout-case.blend")
SHELL_STL = os.path.join(BASE, "postureai-front-layout-shell.stl")
COVER_STL = os.path.join(BASE, "postureai-front-layout-cover.stl")


def add_box(name, dims, loc):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def add_cylinder(name, diameter, depth, loc, rotation=(math.pi / 2, 0, 0), vertices=64):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=diameter / 2, depth=depth, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    return obj


def bevel(obj, width, segments=5):
    mod = obj.modifiers.new("rounded", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.affect = "EDGES"
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)


def cut(target, cutter, label):
    mod = target.modifiers.new(label, "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def join(parts, name):
    bpy.ops.object.select_all(action="DESELECT")
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    parts[0].name = name
    return parts[0]


def material(obj, color):
    mat = bpy.data.materials.new(obj.name + " material")
    mat.diffuse_color = (*color, 1.0)
    obj.data.materials.append(mat)


def export(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True)


bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

# Front body: 3 mm front plate, 3 mm side/top/bottom walls; open at rear.
front = add_box("Front panel", (W, WALL, H), (0, -D / 2 + WALL / 2, H / 2))
left = add_box("Left wall", (WALL, D - WALL, H), (-W / 2 + WALL / 2, WALL / 2, H / 2))
right = add_box("Right wall", (WALL, D - WALL, H), (W / 2 - WALL / 2, WALL / 2, H / 2))
top = add_box("Top wall", (W - 2 * WALL, D - WALL, WALL), (0, WALL / 2, H - WALL / 2))
bottom = add_box("Bottom wall", (W - 2 * WALL, D - WALL, WALL), (0, WALL / 2, WALL / 2))
shell = join([front, left, right, top, bottom], "OffSyn Tech front shell")
bevel(shell, 3.0, 4)

# Cut the front apertures. Cutters extend through the front plate only.
front_y = -D / 2
cut(shell, add_cylinder("Camera cutter", CAMERA_D, 10, (0, front_y, CAMERA_Z)), "camera aperture")
cut(shell, add_cylinder("Light cutter", LIGHT_D, 10, (0, front_y, LIGHT_Z)), "light aperture")

lcd = add_box("LCD cutter", (LCD_W, 10, LCD_H), (0, front_y, LCD_Z))
bevel(lcd, 2.0, 4)
cut(shell, lcd, "LCD aperture")
cut(shell, add_cylinder("LED cutter", LED_D, 10, (0, front_y, LED_Z)), "LED aperture")

# Rounded speaker opening with 5 mm perforations.  The hole pattern prints
# cleanly without delicate supports and mirrors the lower section of the sketch.
speaker = add_box("Speaker outline", (SPEAKER_W, 10, SPEAKER_H), (0, front_y, SPEAKER_Z))
bevel(speaker, 6.0, 5)
cut(shell, speaker, "speaker recess")
for row in range(4):
    for col in range(8):
        x = (col - 3.5) * 7.5
        z = SPEAKER_Z + (row - 1.5) * 6.0
        cut(shell, add_cylinder("speaker perforation", 3.4, 10, (x, front_y, z), vertices=24), "speaker perforation")

# Camera and LCD support lips are internal only; they leave all front openings
# exactly at the requested size and provide a surface for tape or screws.
camera_lip = add_cylinder("Camera inner support", CAMERA_D + 8, 2.0, (0, front_y + 4.0, CAMERA_Z))
camera_hole = add_cylinder("Camera support hole", CAMERA_D, 4.0, (0, front_y + 4.0, CAMERA_Z))
cut(camera_lip, camera_hole, "camera opening")
lcd_lip = add_box("LCD inner support", (LCD_W + 8, 2.0, LCD_H + 8), (0, front_y + 4.0, LCD_Z))
lcd_hole = add_box("LCD support hole", (LCD_W, 4.0, LCD_H), (0, front_y + 4.0, LCD_Z))
cut(lcd_lip, lcd_hole, "LCD opening")
shell = join([shell, camera_lip, lcd_lip], "OffSyn Tech front shell")

# Four internal 6 mm standoffs for the removable rear cover. Holes are 2.8 mm
# pilot holes: drill to final screw size or fit heat-set inserts later.
posts = []
for x in (-W / 2 + 11, W / 2 - 11):
    for z in (11, H - 11):
        post = add_cylinder("rear cover standoff", 8.0, 12.0, (x, D / 2 - 9.0, z), rotation=(math.pi / 2, 0, 0), vertices=32)
        hole = add_cylinder("standoff pilot", 2.8, 14.0, (x, D / 2 - 9.0, z), vertices=24)
        cut(post, hole, "pilot hole")
        posts.append(post)
shell = join([shell] + posts, "Ergo Agent front shell")

# ── Production-Grade Ergonomics: Thermal Vents, USB-C Port, & Pi 5 Bosses ──

# 1. USB-C power port cutout on left side wall (recessed for standard cable relief)
usbc_cut = add_box("USB-C power cutter", (14.0, 16.0, 10.0), (-W / 2, 0, 22.0))
bevel(usbc_cut, 1.5, 3)
cut(shell, usbc_cut, "USB-C power port")

# 2. Thermal convection ventilation slots on top (exhaust) and bottom (intake)
for i in range(-3, 4):
    vent_x = i * 16.0
    top_vent = add_box("top vent", (8.0, 30.0, 10.0), (vent_x, 0, H))
    bevel(top_vent, 1.0, 2)
    cut(shell, top_vent, "top thermal exhaust")
    bot_vent = add_box("bottom vent", (8.0, 30.0, 10.0), (vent_x, 0, 0))
    bevel(bot_vent, 1.0, 2)
    cut(shell, bot_vent, "bottom thermal intake")

# 3. Raspberry Pi 5 mounting standoffs (58mm x 49mm standard mounting hole pattern)
pi_posts = []
pi_center_z = 24.0
for px in (-58.0 / 2, 58.0 / 2):
    for py in (-49.0 / 2, 49.0 / 2):
        pi_post = add_cylinder("pi5 standoff", 6.0, 6.0, (px, py, pi_center_z - 3.0), vertices=24)
        pi_hole = add_cylinder("pi5 hole", 2.5, 8.0, (px, py, pi_center_z - 3.0), vertices=16)
        cut(pi_post, pi_hole, "pi5 m2.5 insert hole")
        pi_posts.append(pi_post)
shell = join([shell] + pi_posts, "Ergo Agent front shell")

# Flat removable rear cover. Screw holes are deliberately only on this rear face.
cover = add_box("OffSyn Tech rear cover", (W - 0.4, WALL, H - 0.4), (0, D / 2 - WALL / 2, H / 2))
bevel(cover, 3.0, 4)
for x in (-W / 2 + 11, W / 2 - 11):
    for z in (11, H - 11):
        cut(cover, add_cylinder("cover screw hole", 3.5, 10.0, (x, D / 2, z), vertices=24), "cover screw")

material(shell, (0.05, 0.38, 0.43))
material(cover, (0.05, 0.38, 0.43))

for obj in (shell, cover):
    obj["units"] = "mm"
    obj["enclosure_size_mm"] = "160 x 240 x 80"
    obj["camera_centre_height_mm"] = CAMERA_Z
    obj["camera_cutout_mm"] = CAMERA_D
    obj["lcd_cutout_mm"] = "95 x 33"
    obj["led_cutout_mm"] = LED_D

# Make objects easy to select in Blender.
collection = bpy.data.collections.new("Printable parts")
bpy.context.scene.collection.children.link(collection)
for obj in (shell, cover):
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)

bpy.context.scene.unit_settings.system = "METRIC"
bpy.context.scene.unit_settings.length_unit = "MILLIMETERS"
bpy.context.scene.unit_settings.scale_length = 0.001

bpy.ops.wm.save_as_mainfile(filepath=BLEND)
export(shell, SHELL_STL)
export(cover, COVER_STL)
print(BLEND)
print(SHELL_STL)
print(COVER_STL)
