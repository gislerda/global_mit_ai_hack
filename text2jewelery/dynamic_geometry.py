import sys
import traceback

try:
    import bpy
    import math
    
    # Function to clear the entire scene
    def clear_scene():
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
        for block in bpy.data.meshes:
            bpy.data.meshes.remove(block)
        for block in bpy.data.materials:
            bpy.data.materials.remove(block)
        for block in bpy.data.images:
            bpy.data.images.remove(block)
        for block in bpy.data.lights:
            bpy.data.lights.remove(block)
    
    # Function to create a gold material using the Principled BSDF
    def create_gold_material():
        mat = bpy.data.materials.new(name="Gold")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (1.0, 0.766, 0.336, 1)  # RGB for gold color
            bsdf.inputs['Metallic'].default_value = 1.0
            bsdf.inputs['Roughness'].default_value = 0.2
        return mat
    
    # Function to create the main ring
    def create_ring():
        bpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=0.1,
                                         major_segments=64, minor_segments=16)
        ring = bpy.context.active_object
        ring.name = 'Ring'
        ring.data.materials.append(create_gold_material())
    
        # Smooth shading
        bpy.ops.object.shade_smooth()
        return ring
    
    # Function to create a diamond gem
    def create_diamond():
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, segments=32, ring_count=16)
        diamond = bpy.context.active_object
        diamond.name = 'Diamond'
        diamond.location = (0, 0, 0.15)  # Positioned at the top center
        # Assign a diamond material
        diamond_mat = bpy.data.materials.new(name="Diamond")
        diamond_mat.use_nodes = True
        diamond_bsdf = diamond_mat.node_tree.nodes.get("Principled BSDF")
        if diamond_bsdf:
            diamond_bsdf.inputs['Base Color'].default_value = (0.9, 0.9, 1.0, 1)  # Slightly blue-ish white
            diamond_bsdf.inputs['Metallic'].default_value = 0.0
            diamond_bsdf.inputs['Roughness'].default_value = 0.05
            diamond_bsdf.inputs['Alpha'].default_value = 0.9
        diamond.data.materials.append(diamond_mat)
        
        bpy.ops.object.shade_smooth()
        return diamond
    
    # Main execution
    clear_scene()
    ring = create_ring()
    diamond = create_diamond()
    
    # Parent the diamond to the ring
    diamond.parent = ring
    
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
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
