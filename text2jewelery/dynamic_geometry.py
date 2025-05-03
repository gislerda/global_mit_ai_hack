import sys
import traceback

try:
    import bpy
    import bmesh
    from mathutils import Vector
    from math import pi
    
    def clear_scene():
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
    
    def create_material(name, color, metallic=1.0, roughness=0.25):
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
    
    def create_gem_material():
        # Emerald-like: green and refractive
        mat = bpy.data.materials.new("Emerald")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            if bsdf.inputs.get("Base Color"):
                bsdf.inputs["Base Color"].default_value = (0.08, 0.8, 0.3, 1.0)
            if bsdf.inputs.get("Metallic"):
                bsdf.inputs["Metallic"].default_value = 0.0
            if bsdf.inputs.get("Roughness"):
                bsdf.inputs["Roughness"].default_value = 0.07
            if bsdf.inputs.get("Alpha"):
                bsdf.inputs["Alpha"].default_value = 1.0
            if bsdf.inputs.get("Emission"):
                bsdf.inputs["Emission"].default_value = (0.0, 0.22, 0.08, 1.0)
        return mat
    
    def create_flat_band_ring(outer_radius=1.0, width=0.45, thickness=0.2, bar_gap=0.23, bar_height=0.11):
        """
        Returns a tuple: (ring_band_obj, [upper_bar_obj, lower_bar_obj])
        Band shape: wide, flat; splits on top into two bars.
        """
        # 1. Main Band Body (90% of circumference), with flat sides
        bm = bmesh.new()
        # Create a cross-section (rectangle) for the flat band
        verts2d = [
            Vector((outer_radius - thickness, -width/2)),
            Vector((outer_radius, -width/2)),
            Vector((outer_radius, width/2)),
            Vector((outer_radius - thickness, width/2)),
        ]
        # Sweep this 340 degrees, leaving 40-degree gap for the "split bars"
        arc_res = 128
        arc_angle = 320/360*pi*2  # ~320 deg to leave wide top gap for split
        step = arc_angle / arc_res
        center = Vector((0,0,0))
        ring_verts = []
        for i in range(arc_res+1):
            phi = -pi/2 + i * step  # Start at bottom
            rot = Vector((0,0,1)).rotation_difference(Vector((1,0,0))).to_matrix()
            vset = []
            for v in verts2d:
                local = Vector((v.x * (cos := bpy.app.driver_namespace.setdefault('cos', __import__('math').cos))(phi), v.x * (__import__('math').sin)(phi), v.y))
                vset.append(bm.verts.new(local))
            for prev, curr in zip(vset, vset[1:]+vset[:1]):
                pass  # just to ensure bm.verts.new
            ring_verts.append(vset)
        # Face sides of the band
        for i in range(arc_res):
            for j in range(4):
                v0 = ring_verts[i][j]
                v1 = ring_verts[i][(j+1)%4]
                v2 = ring_verts[i+1][(j+1)%4]
                v3 = ring_verts[i+1][j]
                bm.faces.new([v0, v1, v2, v3])
        band_mesh = bpy.data.meshes.new("FlatBandRing")
        bm.to_mesh(band_mesh)
        band_obj = bpy.data.objects.new("GoldBand", band_mesh)
        bpy.context.collection.objects.link(band_obj)
        bm.free()
        
        # 2. Two Parallel "Bars" that split and arch across the top gap
        bar_len = bar_gap + 0.21
        bar_y = width/2 - bar_height/2
        bar_radius = outer_radius - thickness/2         # Midpoint of the band, so bars rest nicely on band
        bar_res = 32
        bars = []
        for sign in (+1, -1):
            # Each bar is a narrow rectangular prism swept in an arc across the gap
            bar_bm = bmesh.new()
            arc_start = pi/2 - (bar_gap/2)/bar_radius
            arc_end   = pi/2 + (bar_gap/2)/bar_radius
            # Slightly longer arc for each bar
            arc_start -= 0.06
            arc_end   += 0.06
            for seg in range(bar_res+1):
                t = seg / bar_res
                phi = arc_start * (1-t) + arc_end * t
                cx = bar_radius * bpy.app.driver_namespace.setdefault('cos', __import__('math').cos)(phi)
                cz = bar_radius * (__import__('math').sin)(phi)
                offset = sign * bar_y
                p0 = bar_bm.verts.new((cx, offset-bar_height/2, cz))
                p1 = bar_bm.verts.new((cx, offset+bar_height/2, cz))
            for seg in range(bar_res):
                v00 = bar_bm.verts[seg*2]
                v01 = bar_bm.verts[seg*2+1]
                v10 = bar_bm.verts[(seg+1)*2]
                v11 = bar_bm.verts[(seg+1)*2+1]
                bar_bm.faces.new([v00, v01, v11, v10])
            # Cap faces
            bar_bm.faces.new([bar_bm.verts[0], bar_bm.verts[1], bar_bm.verts[-1], bar_bm.verts[-2]])
            bar_mesh = bpy.data.meshes.new(f"UpperBar_{sign}")
            bar_bm.to_mesh(bar_mesh)
            bar_obj = bpy.data.objects.new(f"Bar_{'Upper' if sign>0 else 'Lower'}", bar_mesh)
            bpy.context.collection.objects.link(bar_obj)
            bar_bm.free()
            bars.append(bar_obj)
        return band_obj, bars
    
    def create_emerald_cut_gem(center, gem_size=(0.22, 0.13, 0.10)):
        """
        Make a simplified emerald-cut (rectangular with chamfered corners & table).
        center: (x, y, z)
        gem_size: (x, y, z) tuple for length, width, depth
        """
        lx, ly, lz = gem_size
        # Basic rectangular prism with small corner cut (bevel)
        bm = bmesh.new()
        # Start with a cube
        bmesh.ops.create_cube(bm, size=1.0)
        # Scale to shape
        scale_mat = (
            (lx/2,   0,    0),
            (0,   ly/2,    0),
            (0,     0,  lz/2)
        )
        for v in bm.verts:
            v.co = Vector((v.co[0]*lx/2, v.co[1]*ly/2, v.co[2]*lz/2))
        # Chamfer (bevel) the 8 cube corners, and optionally top/bottom edges
        geom = [v for v in bm.verts]
        bmesh.ops.bevel(bm, geom=geom, offset=min(lx, ly, lz)*0.12, segments=3, profile=0.5, affect='VERTICES')
        # Table: flatten top slightly and shrink
        top_verts = [v for v in bm.verts if abs(v.co[2] - lz/2)<0.03]
        for v in top_verts:
            v.co.xy *= 0.78
            v.co[2] = lz/2 + 0.004
        gem_mesh = bpy.data.meshes.new("EmeraldGem")
        bm.to_mesh(gem_mesh)
        bm.free()
        gem_obj = bpy.data.objects.new("Emerald", gem_mesh)
        gem_obj.location = center
        bpy.context.collection.objects.link(gem_obj)
        return gem_obj
    
    def create_bezel_caps(gem_obj, gem_size, bar_objs, band_outer_radius, bar_offset=0.14, thickness=0.024):
        """
        Create two end bezels that 'cap' the gemstone at each end, integrating with parallel bars.
        They're simple rectangular bridges with a little width to overlap the gem edges.
        """
        lx, ly, lz = gem_size
        bezels = []
        for sign in (-1, +1):
            cap = bpy.data.meshes.new(f"BezelCap_{sign}")
            bm = bmesh.new()
            # Rectangular block: slightly wider than gem facet, about band thickness
            bx = lx*0.17
            by = ly*1.13
            bz = thickness
            x = sign*(lx/2 + bx/2 - 0.005)
            v0 = bm.verts.new((x-bx/2, -by/2, -bz/2))
            v1 = bm.verts.new((x+bx/2, -by/2, -bz/2))
            v2 = bm.verts.new((x+bx/2,  by/2, -bz/2))
            v3 = bm.verts.new((x-bx/2,  by/2, -bz/2))
            v4 = bm.verts.new((x-bx/2, -by/2,  bz/2))
            v5 = bm.verts.new((x+bx/2, -by/2,  bz/2))
            v6 = bm.verts.new((x+bx/2,  by/2,  bz/2))
            v7 = bm.verts.new((x-bx/2,  by/2,  bz/2))
            bm.faces.new([v0, v1, v2, v3])
            bm.faces.new([v4, v5, v6, v7])
            bm.faces.new([v0, v4, v7, v3])
            bm.faces.new([v1, v5, v6, v2])
            bm.faces.new([v3, v2, v6, v7])
            bm.faces.new([v0, v1, v5, v4])
            cap_mesh = cap
            bm.to_mesh(cap_mesh)
            bm.free()
            cap_obj = bpy.data.objects.new(f"Bezel_{'Left' if sign<0 else 'Right'}", cap_mesh)
            # Place at correct position (use gem's loc as center reference)
            cap_obj.location = (
                gem_obj.location[0] + sign*(lx/2 - 0.002),
                gem_obj.location[1],
                gem_obj.location[2]
            )
            bpy.context.collection.objects.link(cap_obj)
            bezels.append(cap_obj)
        return bezels
    
    def main():
        clear_scene()
        
        OUTER_RADIUS = 1.0
        BAND_WIDTH = 0.42         # Distance from lower to upper band edge
        BAND_THICKNESS = 0.21     # Side-wall to out-wall thickness
        BAR_GAP = 0.25            # Distance between bars at split
        BAR_HEIGHT = 0.12
        GOLD_COL = (1.0, 0.85, 0.3)
    
        band_obj, bars = create_flat_band_ring(outer_radius=OUTER_RADIUS, width=BAND_WIDTH, thickness=BAND_THICKNESS, bar_gap=BAR_GAP, bar_height=BAR_HEIGHT)
        band_obj.location = (0, 0, 0)
        gold = create_material("Gold", GOLD_COL, metallic=1.0, roughness=0.19)
        for o in [band_obj] + bars:
            if len(o.data.materials):
                o.data.materials[0] = gold
            else:
                o.data.materials.append(gold)
    
        # Gem & placement
        GEM_SIZE = (0.22, 0.13, 0.10)
        # Center of gemstone: just above ring edge, between bar arches
        # Z: sit nicely above the ring, bar centers near 0, so offset up by half ring thickness + half gem height
        gem_z = OUTER_RADIUS - BAND_THICKNESS/2 + GEM_SIZE[2]/2 + 0.015
        gem_obj = create_emerald_cut_gem(center=(0, 0, gem_z), gem_size=GEM_SIZE)
        emerald_mat = create_gem_material()
        gem_obj.data.materials.append(emerald_mat)
    
        # Bezel/Setting caps
        bezels = create_bezel_caps(gem_obj, GEM_SIZE, bars, band_outer_radius=OUTER_RADIUS, bar_offset=BAR_GAP/2, thickness=0.024)
        for cap in bezels:
            if len(cap.data.materials):
                cap.data.materials[0] = gold
            else:
                cap.data.materials.append(gold)
    
        # Orient everything in XZ
        for obj in [band_obj, gem_obj] + bars + bezels:
            obj.rotation_mode = 'XYZ'
            obj.rotation_euler = (pi/2, 0, 0)
            # Move so the outer edge is at z=0 (top of finger @ 0)
            obj.location[2] -= OUTER_RADIUS
    
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
