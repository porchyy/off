import bpy
import os
from mathutils import Vector

# All dimensions are millimetres. This is deliberately a blank shell so that
# component apertures can be drilled/cut after final hardware placement.
OUTER_W = 160.0
OUTER_H = 240.0
OUTER_D = 80.0
WALL = 3.0
CORNER_RADIUS = 10.0
LIP_DEPTH = 6.0
CLEARANCE = 0.45

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
BLEND_PATH = os.path.join(OUT_DIR, "postureai-empty-enclosure.blend")
SHELL_STL_PATH = os.path.join(OUT_DIR, "postureai-empty-enclosure-shell.stl")
COVER_STL_PATH = os.path.join(OUT_DIR, "postureai-empty-enclosure-cover.stl")
PREVIEW_PATH = os.path.join(OUT_DIR, "postureai-empty-enclosure-preview.png")


def cube(name, dimensions, location):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def bevel(obj, amount, segments=6):
    modifier = obj.modifiers.new("Rounded corners", "BEVEL")
    modifier.width = amount
    modifier.segments = segments
    modifier.affect = "EDGES"
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def difference(target, cutter):
    modifier = target.modifiers.new("Hollow interior", "BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.solver = "EXACT"
    modifier.object = cutter
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def add_material(obj):
    material = bpy.data.materials.new(obj.name + " material")
    material.diffuse_color = (0.06, 0.42, 0.45, 1.0)
    obj.data.materials.append(material)


def export_stl(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True)


def look_at(obj, target):
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

# Coordinate system: X = width, Y = depth, Z = height. The front is -Y.
# The shell is open at the rear and every outside surface is intentionally blank.
shell_depth = OUTER_D - WALL
shell = cube(
    "Front shell — blank exterior",
    (OUTER_W, shell_depth, OUTER_H),
    (0, -WALL / 2, OUTER_H / 2),
)
bevel(shell, CORNER_RADIUS)

interior = cube(
    "Interior clearance",
    (OUTER_W - 2 * WALL, OUTER_D - WALL, OUTER_H - 2 * WALL),
    (0, WALL / 2, OUTER_H / 2),
)
bevel(interior, CORNER_RADIUS - WALL)
difference(shell, interior)

# The rear cover has no screw holes or connectors. It uses a plain insertion lip
# and remains a separate printable component.
cover = cube(
    "Rear cover — blank exterior",
    (OUTER_W, WALL, OUTER_H),
    (0, OUTER_D / 2 - WALL / 2, OUTER_H / 2),
)
bevel(cover, CORNER_RADIUS)

lip = cube(
    "Rear cover insertion lip",
    (
        OUTER_W - 2 * (WALL + CLEARANCE),
        LIP_DEPTH,
        OUTER_H - 2 * (WALL + CLEARANCE),
    ),
    (0, OUTER_D / 2 - WALL - LIP_DEPTH / 2, OUTER_H / 2),
)
bevel(lip, max(1.0, CORNER_RADIUS - WALL - CLEARANCE), 5)
bpy.ops.object.select_all(action="DESELECT")
cover.select_set(True)
lip.select_set(True)
bpy.context.view_layer.objects.active = cover
bpy.ops.object.join()
cover.name = "Rear cover — blank exterior"

for obj in (shell, cover):
    add_material(obj)
    obj["external_dimensions_mm"] = "160 x 240 x 80"
    obj["wall_thickness_mm"] = WALL
    obj["interior_dimensions_mm"] = "154 x 234 x 74"
    obj["camera_center_height_mm"] = 190
    obj["design_note"] = "Blank enclosure: create all component openings later."

reference = cube(
    "Internal usable volume reference",
    (OUTER_W - 2 * WALL, OUTER_D - 2 * WALL, OUTER_H - 2 * WALL),
    (0, 0, OUTER_H / 2),
)
reference.display_type = "WIRE"
reference.hide_render = True
reference.hide_viewport = True

parts = bpy.data.collections.new("Printable parts")
bpy.context.scene.collection.children.link(parts)
for obj in (shell, cover):
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    parts.objects.link(obj)

bpy.context.scene.unit_settings.system = "METRIC"
bpy.context.scene.unit_settings.length_unit = "MILLIMETERS"
bpy.context.scene.unit_settings.scale_length = 0.001

# A simple render preview, mainly to make the blank construction easy to check.
bpy.context.scene.render.engine = "BLENDER_WORKBENCH"
bpy.context.scene.render.resolution_x = 900
bpy.context.scene.render.resolution_y = 700
bpy.context.scene.render.resolution_percentage = 100
bpy.context.scene.render.film_transparent = False
bpy.context.scene.render.image_settings.color_mode = "RGBA"
bpy.context.scene.display.shading.light = "STUDIO"
bpy.context.scene.display.shading.studio_light = "paint.sl"
bpy.context.scene.display.shading.color_type = "MATERIAL"
bpy.context.scene.display.shading.show_shadows = True
bpy.context.scene.display.shading.show_cavity = True
bpy.context.scene.display.shading.cavity_type = "WORLD"

bpy.ops.object.camera_add(location=(520, -750, 410))
camera = bpy.context.object
camera.data.lens = 52
look_at(camera, shell.location)
bpy.context.scene.camera = camera
bpy.context.scene.render.image_settings.file_format = "PNG"

# Keep the cover next to the shell in the preview; models remain separate.
cover.location.x = 115
cover.location.y = 0
bpy.context.view_layer.objects.active = shell
bpy.ops.render.render(write_still=False)
bpy.data.images["Render Result"].save_render(PREVIEW_PATH)
cover.location.x = 0
cover.location.y = OUTER_D / 2 - WALL / 2

bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
export_stl(shell, SHELL_STL_PATH)
export_stl(cover, COVER_STL_PATH)

print("Saved:", BLEND_PATH)
print("Saved:", SHELL_STL_PATH)
print("Saved:", COVER_STL_PATH)
