import sys
import traceback

try:
    import bpy
    import math
    
    def clear_scene():
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
    
    def create_material(name, color, metallic=1.0, roughness=0.3):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            if bsdf.inputs.get("Base Color"):
                bsdf.inputs["Base Color"].default_value = (*color, 1.0)
            if bsdf.inputs.get("Metallic"):
                bsdf.inputs["Metallic"].default_value = metallic
            if bsdf.inputs.get("Roughness"):
                bsdf.inputs["Roughness"].default_value = roughness
        return mat
    
    def create_curb_chain(center_x=0.0, center_z=1.0, link_count=10, link_major=0.14, link_minor=0.04, gap=0.02):
        objs = []
        for i in range(link_count):
            angle = math.radians(10 * i)
            link_x = center_x + (i - link_count // 2) * (link_major + gap)
            link_z = center_z + 0.07 * math.sin(angle)
            bpy.ops.mesh.primitive_torus_add(
                major_radius=link_major,
                minor_radius=link_minor,
                location=(link_x, 0, link_z),
                rotation=(1.5708 if i%2==0 else 0, math.radians(45 if i%2==0 else -45), 0)
            )
            link = bpy.context.active_object
            link.name = f"CurbChainLink_{i:02d}"
            objs.append(link)
        return objs
    
    def create_dollar_sign_pendant(center_x=0.0, center_z=1.22, height=0.66, thickness=0.10):
        curve_data = bpy.data.curves.new("DollarSignCurve", type='CURVE')
        curve_data.dimensions = '3D'
        curve_data.resolution_u = 48
        # S-shape Bezier curve like main $
        bez = curve_data.splines.new('BEZIER')
        bez.bezier_points.add(3)
        p = bez.bezier_points
        h2 = height*0.5
        w = thickness*1.25
        p[0].co = (0, 0, -h2)
        p[0].handle_left = (-w, 0, -h2 - height*0.1)
        p[0].handle_right = (w, 0, -h2 + height*0.14)
        p[1].co = (w*0.9, 0, -h2*0.34)
        p[1].handle_left = (w*2, 0, -h2*0.36)
        p[1].handle_right = (w*1.2, 0, -h2*0.1)
        p[2].co = (-w*0.85, 0, h2*0.3)
        p[2].handle_left = (-w*1.7, 0, h2*0.43)
        p[2].handle_right = (-w*0.7, 0, h2*0.60)
        p[3].co = (0, 0, h2)
        p[3].handle_left = (w*0.2, 0, h2*1.1)
        p[3].handle_right = (-w*0.2, 0, h2*0.9)
        curve_data.bevel_depth = thickness*0.5
        curve_data.bevel_resolution = 24
        obj = bpy.data.objects.new("DollarSign_S", curve_data)
        bpy.context.collection.objects.link(obj)
        obj.location = (center_x, 0, center_z)
        # Main vertical bar
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(center_x, 0, center_z))
        vertbar = bpy.context.active_object
        vertbar.name = "DollarSignBar"
        vertbar.scale = (0.21*thickness, thickness*0.7, height/2.05)
        vertbar.location = (center_x, 0, center_z)
        # Top and bottom bars
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(center_x, 0, center_z + height/2.3))
        topbar = bpy.context.active_object
        topbar.name = "DollarSignTop"
        topbar.scale = (w*1.25, thickness*0.27, thickness*0.20)
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(center_x, 0, center_z - height/2.3))
        bottombar = bpy.context.active_object
        bottombar.name = "DollarSignBottom"
        bottombar.scale = (w*1.25, thickness*0.27, thickness*0.20)
        # Join all dollar objects
        bpy.context.view_layer.objects.active = vertbar
        for o in [obj, topbar, bottombar]:
            o.select_set(True)
        vertbar.select_set(True)
        bpy.ops.object.join()
        pendant = bpy.context.active_object
        pendant.name = "DollarSignPendant"
        # Add ring loop on top for chain
        bpy.ops.mesh.primitive_torus_add(
            major_radius=thickness*0.46, minor_radius=thickness*0.15, 
            location=(center_x, 0, center_z + height*0.53),
            rotation=(math.radians(90), 0, 0)
        )
        loop = bpy.context.active_object
        loop.name = "PendantLoop"
        # Join with the dollar sign
        loop.select_set(True)
        pendant.select_set(True)
        bpy.context.view_layer.objects.active = pendant
        bpy.ops.object.join()
        # Add decorative engraving: textured bump using voronoi
        mat = create_material("GoldPendant", (1.0, 0.85, 0.32))
        mat.use_nodes = True
        nt = mat.node_tree
        tex = nt.nodes.new("ShaderNodeTexVoronoi")
        tex.feature = 'F1'
        tex.inputs["Scale"].default_value = 36.0
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.22
        nt.links.new(tex.outputs['Distance'], bump.inputs['Height'])
        bsdf = nt.nodes.get("Principled BSDF")
        if bsdf and bsdf.inputs.get("Normal"):
            nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
        pendant.data.materials.clear()
        pendant.data.materials.append(mat)
        # Add rivet details along vertical bar
        n_riv = 6
        for i in range(n_riv):
            f = (i+0.5)/n_riv
            rz = center_z + (f-0.5)*height*0.95
            bpy.ops.mesh.primitive_uv_sphere_add(
                radius=thickness*0.18, 
                location=(center_x, 0, rz)
            )
            rivet = bpy.context.active_object
            rivet.name = f"PendantRivet_{i:02d}"
            rivet.data.materials.append(mat)
        # Join rivets to pendant
        for o in bpy.context.selected_objects:
            o.select_set(False)
        pendant.select_set(True)
        for obj_iter in bpy.context.scene.objects:
            if obj_iter.name.startswith("PendantRivet"):
                obj_iter.select_set(True)
        bpy.context.view_layer.objects.active = pendant
        bpy.ops.object.join()
        return pendant
    
    def create_ring_band():
        clear_scene()
        outer_radius = 1.0
        thickness = 0.2
        bpy.ops.mesh.primitive_torus_add(
            major_radius=outer_radius - thickness,
            minor_radius=thickness,
            location=(0, 0, -outer_radius),
            rotation=(1.5708, 0, 0)
        )
        ring = bpy.context.active_object
        ring.name = "GoldRing"
        gold = create_material("Gold", (1.0, 0.85, 0.3))
        ring.data.materials.append(gold)
        return ring
    
    def main():
        create_ring_band()
        create_curb_chain(center_x=0.0, center_z=1.16, link_count=8, link_major=0.15, link_minor=0.036, gap=0.026)
        create_dollar_sign_pendant(center_x=0.0, center_z=1.22, height=0.66, thickness=0.10)
    
    main()
    
    
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
