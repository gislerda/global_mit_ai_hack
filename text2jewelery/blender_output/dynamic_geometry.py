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
                bsdf.inputs["Base Color"].default_value = (1,1,1,1)
            if bsdf.inputs.get("Metallic"):
                bsdf.inputs["Metallic"].default_value = 0.0
            if bsdf.inputs.get("Roughness"):
                bsdf.inputs["Roughness"].default_value = 0.04
            if bsdf.inputs.get("Emission"):
                bsdf.inputs["Emission"].default_value = (1,1,1,1)
        return mat
    
    def create_split_band_ring():
        outer_radius = 1.0
        base_thickness = 0.21
        top_thickness = 0.13
        base_width = 0.35
        top_width = 0.18
        split_angle = pi/2 * 0.88
    
        segs = 64
        bm = bmesh.new()
        offset_y = 0.07
        for split_factor in (-1,1):
            curve = []
            for i in range(segs+1):
                t = i/segs
                angle = pi/2 + split_factor * split_angle/2 * (1-t)
                rad = outer_radius
                x = rad * cos(angle)
                y = split_factor*offset_y*(1-t)    # band splits near top, close at base
                z = rad * sin(angle)
                curve.append((x, y, z))
            profiles = []
            for i in range(segs+1):
                t = i / segs
                thickness = base_thickness*(1-t) + top_thickness*t
                width = base_width*(1-t) + top_width*t
                # profile at XZ around point/angle
                h = cos(pi/2) # =0, unused, flat across Y for section
                w = width/2
                verts = []
                for j in range(8):
                    th = (j/(8))*2*pi
                    px = thickness/2 * cos(th)
                    py = w * sin(th)
                    verts.append((curve[i][0]+px, curve[i][1]+py, curve[i][2]))
                profiles.append(verts)
            # faces
            for i in range(segs):
                for j in range(8):
                    v0 = bm.verts.new(profiles[i][j])
                    v1 = bm.verts.new(profiles[i][(j+1)%8])
                    v2 = bm.verts.new(profiles[i+1][(j+1)%8])
                    v3 = bm.verts.new(profiles[i+1][j])
                    bm.faces.new([v0,v1,v2,v3])
        mesh = bpy.data.meshes.new("GoldRing")
        bm.to_mesh(mesh)
        bm.free()
        ring = bpy.data.objects.new("GoldRing", mesh)
        bpy.context.collection.objects.link(ring)
        ring.location = (0,0,-outer_radius)
        ring.rotation_mode = 'XYZ'
        ring.rotation_euler = (pi/2,0,0)
        gold = create_material("Gold", (1.0, 0.85, 0.3))
        if len(ring.data.materials)==0:
            ring.data.materials.append(gold)
        else:
            ring.data.materials[0]=gold
        ring.select_set(True)
        bpy.context.view_layer.objects.active = ring
        return ring
    
    def create_oval_gem(center=(0,0,0), rx=0.13, rz=0.20, segs=48):
        bm = bmesh.new()
        # oval/girdle row
        girdle = []
        for i in range(segs):
            a = 2*pi*i/segs
            x = rx*cos(a)
            y = rx*0.74*sin(a)
            z = 0
            girdle.append(bm.verts.new((x, y, z)))
        top = bm.verts.new((0,0,rz))
        bottom = bm.verts.new((0,0,-rz*0.6))
        for i in range(segs):
            bm.faces.new([girdle[i], top, girdle[(i+1)%segs]])
        for i in range(segs):
            bm.faces.new([girdle[i], bottom, girdle[(i+1)%segs]])
        mesh = bpy.data.meshes.new("OvalGem")
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new("OvalGem", mesh)
        obj.location = (center[0], center[1], center[2])
        bpy.context.collection.objects.link(obj)
        gem_mat = create_gem_material()
        if len(obj.data.materials)==0:
            obj.data.materials.append(gem_mat)
        else:
            obj.data.materials[0]=gem_mat
        return obj
    
    def create_prongs(r=1.0, gem_rx=0.13, gem_rz=0.20, n=4):
        prongs = []
        prong_radius = 0.025
        prong_length = 0.14
        z_gem = r + gem_rz-0.007
        for i in range(n):
            ang = pi/2 + i*pi/2
            px = gem_rx*cos(ang)
            py = gem_rx*0.74*sin(ang)
            pz = z_gem
            root = (px*0.98, py*0.95, pz-gem_rz*0.64)
            tip = (px, py, pz+gem_rz*0.25)
            dx,dy,dz = tip[0]-root[0], tip[1]-root[1], tip[2]-root[2]
            mid = ((tip[0]+root[0])/2, (tip[1]+root[1])/2, (tip[2]+root[2])/2)
            length = (dx**2+dy**2+dz**2)**0.5
            bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=prong_radius, depth=length, location=mid)
            prong = bpy.context.object
            prong.name = f"Prong_{i+1}"
            from mathutils import Vector
            v = Vector((dx,dy,dz)).normalized()
            up = Vector((0,0,1))
            if v.dot(up)<0.999999:
                axis = up.cross(v)
                ang = up.angle(v)
                prong.rotation_mode = 'AXIS_ANGLE'
                prong.rotation_axis_angle[0] = ang
                prong.rotation_axis_angle[1] = axis[0]
                prong.rotation_axis_angle[2] = axis[1]
                prong.rotation_axis_angle[3] = axis[2]
            gold = create_material("Gold", (1.0, .85, .3))
            if len(prong.data.materials)==0:
                prong.data.materials.append(gold)
            else:
                prong.data.materials[0]=gold
            prongs.append(prong)
        return prongs
    
    clear_scene()
    ring = create_split_band_ring()
    gem = create_oval_gem(center=(0,0,1.0+0.20-0.013), rx=0.13, rz=0.20, segs=48)
    create_prongs(r=1.0, gem_rx=0.13, gem_rz=0.20, n=4)
    
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
