# ----------------------------
# RENDER AND EXPORT FOOTER
# ----------------------------

import bpy
import os
import math
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

# ----------------------------
# Setup paths
# ----------------------------
glb_path = r"./blender_output/ring_export.glb"
png_path = r"./blender_output/ring_export.png"

# ----------------------------
# Add camera (if not exists)
# ----------------------------
if "Camera" not in bpy.data.objects:
    bpy.ops.object.camera_add()
camera = bpy.data.objects["Camera"]

# ----------------------------
# Add light (if not exists)
# ----------------------------
if not any(obj.type == 'LIGHT' for obj in bpy.data.objects):
    bpy.ops.object.light_add(type='AREA', location=(5, -5, 5))
    bpy.context.active_object.data.energy = 1000

# ----------------------------
# Set camera to fit all visible mesh objects
# ----------------------------
def get_combined_bounds():
    objs = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    bbox_min = Vector((float('inf'),) * 3)
    bbox_max = Vector((float('-inf'),) * 3)
    for obj in objs:
        for v in obj.bound_box:
            world_v = obj.matrix_world @ Vector(v)
            bbox_min = Vector(map(min, bbox_min, world_v))
            bbox_max = Vector(map(max, bbox_max, world_v))
    return (bbox_min + bbox_max) / 2, bbox_max - bbox_min

center, size = get_combined_bounds()
max_dim = max(size)
cam_distance = max_dim * 1.8

camera.location = center + Vector((cam_distance, -cam_distance, cam_distance))
camera.rotation_euler = (math.radians(60), 0, math.radians(45))
bpy.context.scene.camera = camera

# ----------------------------
# Render settings
# ----------------------------
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'GPU'
scene.cycles.samples = 100
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = png_path

# ----------------------------
# Export GLB
# ----------------------------
bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB')

# ----------------------------
# Render image
# ----------------------------
bpy.ops.render.render(write_still=True)

print(f"✅ Rendered image saved to {png_path}")
print(f"✅ 3D model saved to {glb_path}")
