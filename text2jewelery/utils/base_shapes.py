import bpy
import os

# Utility: Clear the current scene
def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

# Utility: Save selected objects to GLB
def save_as_glb(file_name, output_dir="//base_shape"):
    output_dir = bpy.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(output_dir, file_name),
        export_format='GLB',
        use_selection=True
    )

# Utility: Create a metallic material
def create_material(name, color, metallic=1.0, roughness=0.25):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat

# Base shape: Ring (torus)
def create_ring(thickness=0.2, radius=1.0):
    clear_scene()
    bpy.ops.mesh.primitive_torus_add(major_radius=radius, minor_radius=thickness, rotation=(1.5708, 0, 0))
    ring = bpy.context.active_object
    ring.name = "Ring"
    ring.data.materials.append(create_material("Gold", (1.0, 0.85, 0.3)))
    ring.select_set(True)
    save_as_glb("ring.glb")

# Base shape: Earring (pin + trinket)
def create_earring(pin_length=0.6, pin_radius=0.02, trinket_radius=0.1):
    clear_scene()
    bpy.ops.mesh.primitive_cylinder_add(radius=pin_radius, depth=pin_length, location=(0, 0, pin_length / 2))
    pin = bpy.context.active_object
    pin.name = "EarringPin"
    bpy.ops.mesh.primitive_uv_sphere_add(radius=trinket_radius, location=(0, 0, -trinket_radius))
    trinket = bpy.context.active_object
    trinket.name = "EarringTrinket"
    pin.data.materials.append(create_material("Silver", (0.7, 0.7, 0.7)))
    trinket.data.materials.append(create_material("Bronze", (0.6, 0.4, 0.2)))
    pin.select_set(True)
    trinket.select_set(True)
    save_as_glb("earring.glb")

# Base shape: Necklace (torus-like collar)
def create_necklace(radius=1.4, thickness=0.05):
    clear_scene()
    bpy.ops.mesh.primitive_torus_add(
        major_radius=radius,
        minor_radius=thickness,
        rotation=(1.5708, 0, 0),
        major_segments=48,
        minor_segments=8
    )
    necklace = bpy.context.active_object
    necklace.name = "Necklace"
    necklace.data.materials.append(create_material("Silver", (0.8, 0.8, 0.9)))
    necklace.select_set(True)
    save_as_glb("necklace.glb")

# Base shape: Piercing (barbell)
def create_piercing(ball_radius=0.05, bar_radius=0.02, bar_length=0.3):
    clear_scene()
    bpy.ops.mesh.primitive_uv_sphere_add(radius=ball_radius, location=(-bar_length / 2, 0, 0))
    ball1 = bpy.context.active_object
    ball1.name = "PiercingBall1"
    bpy.ops.mesh.primitive_uv_sphere_add(radius=ball_radius, location=(bar_length / 2, 0, 0))
    ball2 = bpy.context.active_object
    ball2.name = "PiercingBall2"
    bpy.ops.mesh.primitive_cylinder_add(radius=bar_radius, depth=bar_length, location=(0, 0, 0), rotation=(0, 1.5708, 0))
    bar = bpy.context.active_object
    bar.name = "PiercingBar"
    mat = create_material("Titanium", (0.6, 0.6, 0.7))
    for part in [ball1, ball2, bar]:
        part.data.materials.append(mat)
        part.select_set(True)
    save_as_glb("piercing.glb")

# Example usage:
#create_ring()
#create_earring()
#create_necklace()
#create_piercing()
