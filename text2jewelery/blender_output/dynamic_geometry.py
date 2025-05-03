import sys
import traceback

try:
    import bpy
    import math
    from mathutils import Vector, Matrix
    
    # --- CLEAR SCENE ---
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        bpy.data.materials.remove(block)
    for block in bpy.data.lights:
        bpy.data.lights.remove(block)
    for block in bpy.data.images:
        bpy.data.images.remove(block)
    for block in bpy.data.curves:
        bpy.data.curves.remove(block)
    
    # --- RING PARAMETERS ---
    inner_radius = 11.0     # mm, inner finger diameter/2
    band_width = 4.0        # mm, wide band for contemporary look
    band_thickness = 2.0    # mm, flat cross-section height
    band_open_angle_deg = 48
    band_open_angle = math.radians(band_open_angle_deg)
    segments = 192
    
    # --- BUILD OPEN RING BY USING A PROFILE + CURVE ---
    # 1. Create a rectangle as profile for the band (to be swept)
    bpy.ops.mesh.primitive_plane_add(size=1)
    profile = bpy.context.active_object
    profile.scale = (band_thickness * 0.5, band_width * 0.5, 1)
    profile.name = "BandProfile"
    # Center profile so sweeping axis is at rectangle center (origin)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    profile.location = (inner_radius + band_width * 0.5, 0, 0)
    bpy.ops.object.transform_apply(location=True, scale=True, rotation=True)
    
    # 2. Create the curve (arc) the profile will be swept along
    bpy.ops.curve.primitive_bezier_circle_add(radius=inner_radius + band_width * 0.5)
    arc = bpy.context.active_object
    arc.data.splines.clear()
    curve = arc
    spline = curve.data.splines.new(type='BEZIER')
    spline.bezier_points.add(count=1)  # 2 total points
    
    # Calculate arc ends for open ring
    angle_start = band_open_angle / 2
    angle_end = 2*math.pi - band_open_angle / 2
    
    points = []
    for angle in [angle_start, angle_end]:
        x = math.cos(angle) * (inner_radius + band_width * 0.5)
        y = math.sin(angle) * (inner_radius + band_width * 0.5)
        points.append((x, y, 0))
    spline.bezier_points[0].co = points[0]
    spline.bezier_points[1].co = points[1]
    for pt in spline.bezier_points:
        pt.handle_left_type = pt.handle_right_type = 'VECTOR'
    
    # Smooth open arc
    curve.data.dimensions = '3D'
    curve.data.resolution_u = 64
    
    # 3. Sweep profile along arc using Curve modifier
    profile_mod = profile.modifiers.new('Curve', 'CURVE')
    profile_mod.object = curve
    profile_mod.deform_axis = 'POS_X'
    
    # 4. Convert swept geometry to mesh (apply all)
    bpy.context.view_layer.objects.active = profile
    bpy.ops.object.modifier_apply(modifier='Curve')
    bpy.ops.object.convert(target='MESH')
    
    # 5. Tidy up curve; remove helper
    bpy.data.objects.remove(curve, do_unlink=True)
    
    ring_obj = profile
    ring_obj.name = "ContemporaryRingBand"
    
    # --- POLISHING ---
    subsurf_mod = ring_obj.modifiers.new("Subdivision", 'SUBSURF')
    subsurf_mod.levels = 2
    subsurf_mod.render_levels = 3
    ring_obj.select_set(True)
    bpy.context.view_layer.objects.active = ring_obj
    bpy.ops.object.shade_smooth()
    
    # --- GOLD MATERIAL ---
    gold_mat = bpy.data.materials.new("GoldMaterial")
    gold_mat.use_nodes = True
    bsdf = gold_mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (1.0, 0.764, 0.336, 1.0)
        bsdf.inputs["Metallic"].default_value = 1.0
        bsdf.inputs["Roughness"].default_value = 0.23
        bsdf.inputs["Alpha"].default_value = 1.0
    
    ring_obj.data.materials.append(gold_mat)
    
    # --- BEZEL-SET GEMS ON EACH OPEN END ---
    gem_radius = 1.14
    bezel_width = 0.38
    bezel_height = band_thickness + 0.4
    gem_segments = 48
    
    for i, angle in enumerate([angle_start, angle_end]):
        # Calculate end center for gem/bezel
        cx = math.cos(angle) * (inner_radius + band_width * 0.5)
        cy = math.sin(angle) * (inner_radius + band_width * 0.5)
        cz = 0
        base_pos = Vector((cx, cy, cz))
        normal = Vector((math.cos(angle), math.sin(angle), 0))
        
        # -- Create bezel (simple short cylinder, slightly larger than stone)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=gem_radius + bezel_width,
            depth=bezel_height,
            vertices=gem_segments,
            location=base_pos + Vector((0,0,bezel_height/2))
        )
        bezel = bpy.context.active_object
        # Rotate to align with band direction
        bezel.rotation_euler = (0, 0, angle)
        
        # Material: Same gold
        bezel.data.materials.append(gold_mat)
        bpy.ops.object.shade_smooth()
    
        # -- Create gem (diamond/cubic zirconia, clear round)
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=gem_radius,
            segments=gem_segments,
            ring_count=gem_segments//2,
            location=base_pos + Vector((0,0,bezel_height*0.7))
        )
        gem = bpy.context.active_object
    
        # Material: Diamond
        diamond_mat = bpy.data.materials.get("DiamondMaterial")
        if not diamond_mat:
            diamond_mat = bpy.data.materials.new("DiamondMaterial")
            diamond_mat.use_nodes = True
            d_bsdf = diamond_mat.node_tree.nodes.get("Principled BSDF")
            if d_bsdf:
                d_bsdf.inputs["Base Color"].default_value = (0.93, 0.97, 1.0, 1.0)
                d_bsdf.inputs["Metallic"].default_value = 0.05
                d_bsdf.inputs["Roughness"].default_value = 0.02
                d_bsdf.inputs["Alpha"].default_value = 1.0
        gem.data.materials.append(diamond_mat)
        bpy.ops.object.shade_smooth()
    
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
