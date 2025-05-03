import sys
import traceback

try:
    import bpy
    import bmesh
    from math import pi, sin, cos
    
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
    
    def create_gem_material():
        mat = bpy.data.materials.new("Diamond")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            if bsdf.inputs.get("Base Color"):
                bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
            if bsdf.inputs.get("Metallic"):
                bsdf.inputs["Metallic"].default_value = 0.0
            if bsdf.inputs.get("Roughness"):
                bsdf.inputs["Roughness"].default_value = 0.02
            if bsdf.inputs.get("Emission"):
                bsdf.inputs["Emission"].default_value = (1.0, 1.0, 1.0, 1.0)
        return mat
    
    def band_profile(thickness_base, thickness_top, width):
        verts = []
        segs = 8
        for i in range(segs):
            t = i / (segs - 1)
            y = (t - 0.5) * width
            thickness = (1-t)*thickness_base + t*thickness_top
            verts.append((0, y, -thickness/2))
            verts.append((0, y, thickness/2))
        return verts
    
    def swept_curve(radius=1.0, split_angle=pi/2, segs=64):
        # Returns two lists of points for the split strands
        a0 = pi/2 + split_angle/2
        a1 = pi/2 - split_angle/2
        arc1 = []
        arc2 = []
        for i in range(segs+1):
            t = i / segs
            a_top = (1-t)*a0 + t*pi*1.5 # go down to base at -Y
            a_bot = (1-t)*a1 + t*pi*1.5
            r_top = radius - 0.015 * t
            r_bot = radius - 0.015 * t
            arc1.append((r_top*cos(a_top), 0, r_top*sin(a_top)))
            arc2.append((r_bot*cos(a_bot), 0, r_bot*sin(a_bot)))
        return arc1, arc2
    
    def create_split_band_ring():
        # Parameters
        ring_radius = 1.0
        band_width = 0.32         # width between outer faces of band (XZ plane, vertical ring width)
        thickness_base = 0.23     # thickness at ring shank (thickest)
        thickness_top = 0.13      # thickness at stone
        
        split_angle = pi/2 * 0.85 /* strands start split over ~77deg */
    
        arc1, arc2 = swept_curve(ring_radius, split_angle, segs=80)
        
        def profile_verts(a, t):
            # Cross-section is oval at each point, becomes thinner at top
            thickness = (1-t)*thickness_base + t*thickness_top
            width = (1-t)*band_width*1.08 + t*band_width*0.65
            ring_normal = (cos(a), 0, sin(a))
            ring_binormal = (0, 1, 0)
            # 8 verts, distributed along binormal, thickness in normal
            vs = []
            for j in range(-3, 4+1):
                y = (j/4) * width/2
                for s in [-1,1]:
                    pt = (
                        s*thickness/2*ring_normal[0] + 0*ring_binormal[0] + y*ring_binormal[0],
                        s*thickness/2*ring_normal[1] + 0*ring_binormal[1] + y*ring_binormal[1],
                        s*thickness/2*ring_normal[2] + 0*ring_binormal[2] + y*ring_binormal[2]
                    )
                    vs.append(pt)
            return vs
    
        # Prep BMesh for curve sweep
        bm = bmesh.new()
        nsegs = len(arc1)
        prof_pts = 7*2
        prev_verts_1 = []
        prev_verts_2 = []
    
        for i in range(nsegs):
            t = i / (nsegs-1)
            a1 = pi/2 + split_angle/2*(1-t)
            a2 = pi/2 - split_angle/2*(1-t)
            # For both strands (upper and lower)
            v1 = arc1[i]
            v2 = arc2[i]
            mat = (
                # Matrix: place section at proper spot and orientation (XZ plane tangent)
                # here: keep ring in XZ, y=0
                )
            # Place profile oriented with radial normal
            pv1s = []
            pv2s = []
            pf1 = profile_verts(a1, t)
            pf2 = profile_verts(a2, t)
            # The 14 verts of this profile
            for pt in pf1:
                pv = bm.verts.new((v1[0]+pt[0], v1[1]+pt[1], v1[2]+pt[2]))
                pv1s.append(pv)
            for pt in pf2:
                pv = bm.verts.new((v2[0]+pt[0], v2[1]+pt[1], v2[2]+pt[2]))
                pv2s.append(pv)
    
            if i > 0:
                # Create faces for previous profile to this one
                for j in range(prof_pts):
                    v00 = prev_verts_1[j]
                    v01 = prev_verts_1[(j+1)%prof_pts]
                    v10 = pv1s[j]
                    v11 = pv1s[(j+1)%prof_pts]
                    bm.faces.new([v00, v10, v11, v01])
                    v00 = prev_verts_2[j]
                    v01 = prev_verts_2[(j+1)%prof_pts]
                    v10 = pv2s[j]
                    v11 = pv2s[(j+1)%prof_pts]
                    bm.faces.new([v00, v01, v11, v10])
            prev_verts_1 = pv1s
            prev_verts_2 = pv2s
    
        # At the very top, connect the two tops across
        for i in range(prof_pts):
            v1 = prev_verts_1[i]
            v2 = prev_verts_2[i]
            v1p = prev_verts_1[(i+1)%prof_pts]
            v2p = prev_verts_2[(i+1)%prof_pts]
            bm.faces.new([v1, v2, v2p, v1p])
    
        # Mesh object
        mb = bpy.data.meshes.new("GoldRing")
        bm.to_mesh(mb)
        bm.free()
        ring_obj = bpy.data.objects.new("GoldRing", mb)
        bpy.context.collection.objects.link(ring_obj)
    
        gold = create_material("Gold", (1.0, 0.85, 0.3))
        if len(ring_obj.data.materials) == 0:
            ring_obj.data.materials.append(gold)
        else:
            ring_obj.data.materials[0] = gold
        ring_obj.select_set(True)
        bpy.context.view_layer.objects.active = ring_obj
    
        # Set correct orientation (XZ ring, top at (0, 0, 0))
        ring_obj.location = (0, 0, -ring_radius)
        ring_obj.rotation_euler = (pi/2, 0, 0)
        ring_obj.rotation_mode = 'XYZ'
    
        return ring_obj
    
    def create_oval_gem(center=(0, 0, 0.0), rx=0.12, rz=0.17, seg_main=56):
        # Generate an approximated brilliant oval with vertical facet girdle and a peaked pavilion
        bm = bmesh.new()
    
        n_row = 7
        top = bm.verts.new((0, 0, rz*1.07))
        bottom = bm.verts.new((0, 0, -rz*0.67))
        # girdle (thickest and widest oval)
        girdle = []
        for i in range(seg_main):
            a = (2*pi*i)/seg_main
            x = rx * cos(a)
            y = rx*0.86 * sin(a)
            z = 0
            v = bm.verts.new((x, y, z))
            girdle.append(v)
        # crown (top facets)
        crown_row = []
        for i in range(seg_main):
            a = (2*pi*i)/seg_main
            x = rx*0.91 * cos(a)
            y = rx*0.83 * sin(a)
            z = rz*0.42
            v = bm.verts.new((x, y, z))
            crown_row.append(v)
            # Top to crown row
            bm.faces.new([top, crown_row[i], crown_row[(i+1)%seg_main]])
        # Crown facets
        for i in range(seg_main):
            bm.faces.new([crown_row[i], girdle[i], girdle[(i+1)%seg_main], crown_row[(i+1)%seg_main]])
        # Girdle to pavilion (bottom peak)
        for i in range(seg_main):
            bm.faces.new([girdle[i], bottom, girdle[(i+1)%seg_main]])
        mb = bpy.data.meshes.new("OvalGem")
        bm.to_mesh(mb)
        bm.free()
        gem_obj = bpy.data.objects.new("OvalGem", mb)
        gem_obj.location = center
        bpy.context.collection.objects.link(gem_obj)
    
        gem_mat = create_gem_material()
        if len(gem_obj.data.materials) == 0:
            gem_obj.data.materials.append(gem_mat)
        else:
            gem_obj.data.materials[0] = gem_mat
        return gem_obj
    
    def create_prongs(ring_radius=1.0, gem_rx=0.12, gem_rz=0.17, nprongs=4):
        # Prongs are gently flowing posts up from the split band toward the oval edges in X
        # Place two prongs along +X/-X, two at intermediate ~45deg, symmetrical
        prong_objs = []
        z_gem = ring_radius + gem_rz - 0.015
        angles = [0, pi/2, pi, 3*pi/2]
        offsets = []
        # For a natural split-band design, use prong roots tight to strand's top
        tip_dist = gem_rx*0.90
        for i in range(nprongs):
            a = angles[i]
            x = tip_dist * cos(a)
            y = tip_dist * sin(a) * 0.78
            z = z_gem + (sin(a)*0.03)
            offsets.append((x, y, z))
        root_dist_band = ring_radius-0.03
        for i in range(nprongs):
            a = angles[i]
            root_x = root_dist_band * cos(a)
            root_y = root_dist_band * sin(a) * 0.82
            root_z = ring_radius + 0.02
            tip = offsets[i]
            root = (root_x, root_y, root_z)
            Dx = tip[0] - root[0]
            Dy = tip[1] - root[1]
            Dz = tip[2] - root[2]
            length = (Dx**2 + Dy**2 + Dz**2) ** 0.5
            # Create prong as gently curved cylinder toward tip
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=12,
                radius=0.018,
                depth=length,
                location=((root[0]+tip[0])/2, (root[1]+tip[1])/2, (root[2]+tip[2])/2)
            )
            prong = bpy.context.active_object
            prong.name = f"Prong_{i+1}"
            # Orient cylinder to the vector (Dx, Dy, Dz)
            from mathutils import Vector
            direction = Vector((Dx, Dy, Dz)).normalized()
            up = Vector((0,0,1))
            if direction.dot(up) < 0.99999:
                axis = up.cross(direction)
                angle = up.angle(direction)
                prong.rotation_mode = 'AXIS_ANGLE'
                prong.rotation_axis_angle[0] = angle
                prong.rotation_axis_angle[1] = axis[0]; prong.rotation_axis_angle[2] = axis[1]; prong.rotation_axis_angle[3] = axis[2]
            else:
                prong.rotation_mode = 'XYZ'
                prong.rotation_euler = (0,0,0)
            prong_objs.append(prong)
        gold = create_material("Gold", (1.0, 0.85, 0.3))
        for prong in prong_objs:
            if len(prong.data.materials) == 0:
                prong.data.materials.append(gold)
            else:
                prong.data.materials[0] = gold
        return prong_objs
    
    def main():
        clear_scene()
        ring_obj = create_split_band_ring()
        ring_radius = 1.0
        gem_rx, gem_rz = 0.12, 0.17
        # Place diamond so its base sits just above ring top at origin (0,0,0)
        gem_z = ring_radius + gem_rz - 0.022
        gem_obj = create_oval_gem(center=(0, 0, gem_z), rx=gem_rx, rz=gem_rz, seg_main=56)
        create_prongs(ring_radius=ring_radius, gem_rx=gem_rx, gem_rz=gem_rz, nprongs=4)
        # Optional: set shade smooth
        for obj in bpy.context.collection.objects:
            if obj.type == 'MESH':
                try:
                    obj.select_set(True)
                    bpy.context.view_layer.objects.active = obj
                    bpy.ops.object.shade_smooth()
                except Exception as e:
                    pass
    
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
