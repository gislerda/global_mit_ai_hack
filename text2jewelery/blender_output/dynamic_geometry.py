import sys
import traceback

try:
    import bpy
    import math
    
    def clear_scene():
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
    
    def create_material(name, color, metallic=1.0, roughness=0.23, alpha=1.0, emission=None):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            if 'Base Color' in bsdf.inputs:
                bsdf.inputs["Base Color"].default_value = (*color, 1.0)
            if 'Metallic' in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = metallic
            if 'Roughness' in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = roughness
            if 'Alpha' in bsdf.inputs:
                bsdf.inputs["Alpha"].default_value = alpha
            if emission is not None and 'Emission' in bsdf.inputs:
                bsdf.inputs['Emission'].default_value = (*emission, 1.0)
        if alpha < 1:
            mat.blend_method = 'BLEND'
        return mat
    
    def create_stud_base(radius=0.16, thickness=0.10):
        bpy.ops.mesh.primitive_cylinder_add(
            radius=radius, 
            depth=thickness, 
            location=(0, 0, thickness/2)
        )
        stud = bpy.context.active_object
        stud.name = "StudBase"
        return stud
    
    def create_gem(radius=0.14, height=0.12):
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=4,
            radius=radius, 
            location=(0, 0, height/2 + 0.10)
        )
        gem = bpy.context.active_object
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.transform.resize(value=(1,1,0.5))
        bpy.ops.object.mode_set(mode='OBJECT')
        gem.location.z = height/2 + 0.10
        gem.name = "FacetedGem"
        return gem
    
    def create_prong_ring(gem_radius, z_top, count=4, prong_height=0.12, prong_radius=0.02):
        prongs = []
        for i in range(count):
            angle = i * (2*math.pi / count)
            x = math.cos(angle) * (gem_radius * 0.8)
            y = math.sin(angle) * (gem_radius * 0.8)
            loc = (x, y, z_top + prong_height/2)
            bpy.ops.mesh.primitive_cylinder_add(
                radius=prong_radius, 
                depth=prong_height, 
                location=loc
            )
            prong = bpy.context.active_object
            prong.rotation_euler[0] = 0
            prong.rotation_euler[1] = 0
            prong.rotation_euler[2] = angle
            prongs.append(prong)
        return prongs
    
    def create_post(length=0.5, radius=0.035, z=0):
        bpy.ops.mesh.primitive_cylinder_add(
            radius=radius, 
            depth=length, 
            location=(0, 0, -length/2 + z)
        )
        post = bpy.context.active_object
        post.name = "StudPost"
        return post
    
    def create_butterfly_clasp(post_length=0.5, post_radius=0.035, offset_z=0.1):
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.07, 
            depth=0.11, 
            location=(0, 0, -post_length - 0.055 + offset_z)
        )
        clasp = bpy.context.active_object
        clasp.name = "ButterflyClasp"
        return clasp
    
    def make_stud_earring(origin=(0,0,0)):
        stud_origin = origin
        steel = create_material("Steel", (0.80, 0.82, 0.85), metallic=1.0, roughness=0.22)
        yellow = create_material("YellowGem", (1.0, 0.95, 0.23), metallic=0.0, roughness=0.07, alpha=0.82, emission=(0.9, 0.8, 0.11))
        stud_base = create_stud_base()
        stud_base.data.materials.append(steel)
        gem = create_gem()
        gem.data.materials.append(yellow)
        prongs = create_prong_ring(0.14, 0.22)
        for prong in prongs:
            prong.data.materials.append(steel)
        post = create_post()
        post.data.materials.append(steel)
        clasp = create_butterfly_clasp()
        clasp.data.materials.append(steel)
        for obj in [stud_base, gem, post, clasp] + prongs:
            obj.location.x += stud_origin[0]
            obj.location.y += stud_origin[1]
            obj.location.z += stud_origin[2]
    
    def make_pair():
        clear_scene()
        make_stud_earring((0.25, 0, 0))
        make_stud_earring((-0.25, 0, 0))
    
    make_pair()
    
    # ----------------------------
    # RENDER AND EXPORT FOOTER
    # ----------------------------
    
    import bpy
    import os
    import math
    from mathutils import Vector
    from bpy_extras.object_utils import world_to_camera_view
    
    # Define absolute base path (adjust this to your actual project root)
    PROJECT_ROOT = "C:/Dev/src/global_mit_ai_hack/text2jewelery"
    FRONTEND_EXPORT_DIR = os.path.join(PROJECT_ROOT, "streamlit_3d", "frontend", "blender_output")
    
    # Ensure export dir exists
    os.makedirs(FRONTEND_EXPORT_DIR, exist_ok=True)
    
    glb_path = os.path.join(FRONTEND_EXPORT_DIR, "ring_export.glb")
    png_path = os.path.join(FRONTEND_EXPORT_DIR, "ring_render.png")
    
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
