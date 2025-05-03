# Blender Python script to generate realistic GLB base shapes for ring, earring, necklace, and piercing

import bpy
import os

output_dir = bpy.path.abspath("//base_shape")
os.makedirs(output_dir, exist_ok=True)

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

def create_material(name, color, metallic=1.0, roughness=0.25):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat

def save_as_glb(obj_names, file_name):
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(output_dir, file_name),
        export_format='GLB',
        use_selection=True
    )

# ---------------------
# Ring (upright torus)
# ---------------------
clear_scene()
bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.2, location=(0, 0, 0), rotation=(1.5708, 0, 0))
ring = bpy.context.active_object
ring.name = "Ring"
ring.data.materials.append(create_material("Gold", (1.0, 0.85, 0.3)))
ring.select_set(True)
save_as_glb(["Ring"], "ring.glb")

# ---------------------
# Earring (pin + trinket)
# ---------------------
clear_scene()
bpy.ops.mesh.primitive_cylinder_add(radius=0.02, depth=0.6, location=(0, 0, 0.3))
pin = bpy.context.active_object
pin.name = "EarringPin"
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=(0, 0, -0.1))
trinket = bpy.context.active_object
trinket.name = "EarringTrinket"
pin.data.materials.append(create_material("Silver", (0.7, 0.7, 0.7)))
trinket.data.materials.append(create_material("Bronze", (0.6, 0.4, 0.2)))
pin.select_set(True)
trinket.select_set(True)
save_as_glb(["EarringPin", "EarringTrinket"], "earring.glb")

# ---------------------
# Necklace (clean torus collar, upright)
# ---------------------
clear_scene()
bpy.ops.mesh.primitive_torus_add(
    major_radius=1.4,
    minor_radius=0.05,
    location=(0, 0, 0),
    rotation=(1.5708, 0, 0),
    major_segments=48,
    minor_segments=8
)
necklace = bpy.context.active_object
necklace.name = "Necklace"
necklace.data.materials.append(create_material("Silver", (0.8, 0.8, 0.9)))
necklace.select_set(True)
save_as_glb(["Necklace"], "necklace.glb")


# ---------------------
# Piercing (barbell with aligned bar)
# ---------------------
clear_scene()
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=(-0.15, 0, 0))
ball1 = bpy.context.active_object
ball1.name = "PiercingBall1"
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=(0.15, 0, 0))
ball2 = bpy.context.active_object
ball2.name = "PiercingBall2"
bpy.ops.mesh.primitive_cylinder_add(radius=0.02, depth=0.3, location=(0, 0, 0), rotation=(0, 1.5708, 0))
bar = bpy.context.active_object
bar.name = "PiercingBar"
mat = create_material("Titanium", (0.6, 0.6, 0.7))
for part in [ball1, ball2, bar]:
    part.data.materials.append(mat)
    part.select_set(True)
save_as_glb(["PiercingBall1", "PiercingBall2", "PiercingBar"], "piercing.glb")

print(f"Exported all base shapes to {output_dir}")
