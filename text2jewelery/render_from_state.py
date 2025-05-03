import bpy
import json
import sys
import os

# Load JSON from CLI argument
json_path = sys.argv[-1]
with open(json_path, 'r') as f:
    design = json.load(f)

# Clean scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# ----------------------------
# Create ring base
# ----------------------------
bpy.ops.mesh.primitive_torus_add(
    major_radius=1.0,
    minor_radius=0.2,
    location=(0, 0, 0)
)
ring = bpy.context.active_object
ring.name = "RingBase"

# Add gold material
gold_mat = bpy.data.materials.new(name="GoldMaterial")
gold_mat.use_nodes = True
nodes = gold_mat.node_tree.nodes
bsdf = nodes.get("Principled BSDF") or nodes.new(type="ShaderNodeBsdfPrincipled")
bsdf.inputs['Base Color'].default_value = (1.0, 0.766, 0.336, 1)  # gold tone
bsdf.inputs['Metallic'].default_value = 1.0
bsdf.inputs['Roughness'].default_value = 0.2
output = nodes.get("Material Output")
if output:
    gold_mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
ring.data.materials.append(gold_mat)

# ----------------------------
# Add diamond on top
# ----------------------------
for feature in design.get("features", []):
    if feature.get("type") == "gem":
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=4,
            radius=0.15,
            location=(0, 0, 0.35)
        )
        gem = bpy.context.active_object
        gem.name = "Diamond"

        diamond_mat = bpy.data.materials.new(name="DiamondMaterial")
        diamond_mat.use_nodes = True
        nodes = diamond_mat.node_tree.nodes
        links = diamond_mat.node_tree.links

        # Clear default nodes
        for node in nodes:
            nodes.remove(node)

        # Create Principled BSDF
        bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)
        bsdf.inputs["Base Color"].default_value = (1, 1, 1, 1)
        bsdf.inputs["Metallic"].default_value = 0.0
        bsdf.inputs["Roughness"].default_value = 0.02
        bsdf.inputs["Transmission Weight"].default_value = 1.0
        bsdf.inputs["IOR"].default_value = 2.417

        # Connect to Material Output
        output = nodes.new(type="ShaderNodeOutputMaterial")
        output.location = (200, 0)
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

        # Assign material
        gem.data.materials.append(diamond_mat)

# ----------------------------
# Lighting & camera
# ----------------------------
bpy.ops.object.light_add(type='AREA', location=(5, -5, 5))
bpy.context.object.data.energy = 300

bpy.ops.object.camera_add(location=(2.5, -2.5, 1.5), rotation=(1.2, 0, 0.8))
bpy.context.scene.camera = bpy.context.object

# ----------------------------
# Render settings
# ----------------------------
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.device = 'GPU'
# Ensure Cycles settings are used
bpy.context.scene.cycles.samples = 100
bpy.context.scene.render.resolution_x = 1024
bpy.context.scene.render.resolution_y = 1024
bpy.context.scene.render.image_settings.file_format = 'PNG'
bpy.context.scene.render.filepath = "//ring_render.png"

# ----------------------------
# Export GLB
# ----------------------------
glb_path = os.path.join(bpy.path.abspath("//"), "ring_export.glb")
bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB')

# ----------------------------
# Render image
# ----------------------------
bpy.ops.render.render(write_still=True)
