#!/usr/bin/env python3
"""
Blender Photorealistic 360° Panorama Renderer
=============================================
Deterministic Cycles renderer for apartment floor plans.

- Loads all room JSONs from a directory
- Builds the entire apartment at computed offsets
- Renders one equirectangular panorama per room with Cycles
- Outputs 8192x4096 (or configurable) photorealistic 360° images

Usage:
  blender -b -P blender_photoreal_pano.py -- \
    --floor-plans floor_plans \
    --output-dir unified_renders_8k \
    --width 8192 --height 4096 --samples 256
"""
import bpy
import json
import math
import os
import sys
from pathlib import Path

from mathutils import Vector


def wall_inward_normal(p1, p2):
    """Return the unit vector perpendicular to the wall segment that points toward the room centre (origin)."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    wall_len = math.hypot(dx, dy)
    if wall_len < 1e-3:
        return (0.0, 0.0)
    ux, uy = dx / wall_len, dy / wall_len
    # Two perpendicular candidates; pick the one pointing toward origin (room centre)
    candidates = [(-uy, ux), (uy, -ux)]
    mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
    best = min(candidates, key=lambda n: n[0] * mid[0] + n[1] * mid[1])
    return best


# ─── Material palette ───────────────────────────────────────────────────────

DOOR_COLOR = (0.45, 0.33, 0.22)
TRIM_COLOR = (0.90, 0.88, 0.84)

TEXTURE_ROOT = Path(__file__).parent / 'textures'

FURNITURE_PALETTE = {
    "sofa": (0.75, 0.70, 0.62),
    "armchair": (0.70, 0.64, 0.56),
    "coffee_table": (0.35, 0.25, 0.18),
    "side_table": (0.45, 0.35, 0.25),
    "tv_stand": (0.28, 0.22, 0.18),
    "tv": (0.08, 0.08, 0.10),
    "dining_table": (0.55, 0.40, 0.28),
    "chair": (0.62, 0.55, 0.46),
    "bar_stool": (0.60, 0.54, 0.46),
    "rug": (0.72, 0.62, 0.52),
    "floor_lamp": (0.85, 0.82, 0.76),
    "plant": (0.22, 0.42, 0.20),
    "bookshelf": (0.38, 0.26, 0.18),
    "bed": (0.86, 0.82, 0.76),
    "nightstand": (0.42, 0.32, 0.22),
    "wardrobe": (0.38, 0.28, 0.20),
    "wardrobe_closet": (0.38, 0.28, 0.20),
    "desk": (0.48, 0.34, 0.22),
    "kitchen_counter": (0.88, 0.87, 0.84),
    "upper_cabinet": (0.80, 0.78, 0.74),
    "stove": (0.25, 0.25, 0.27),
    "sink": (0.82, 0.82, 0.84),
    "fridge": (0.92, 0.92, 0.94),
    "bathtub": (0.95, 0.95, 0.98),
    "toilet": (0.96, 0.96, 0.98),
    "sink_vanity": (0.92, 0.92, 0.94),
    "mirror": (0.75, 0.85, 0.95),
    "shower": (0.82, 0.88, 0.92),
    "washing_machine": (0.88, 0.88, 0.90),
    "dryer": (0.86, 0.86, 0.88),
    "bench": (0.68, 0.60, 0.50),
    "storage_cabinet": (0.42, 0.32, 0.22),
    "shoe_rack": (0.48, 0.36, 0.24),
    "unknown": (0.60, 0.55, 0.50),
}


# ─── Scene helpers ──────────────────────────────────────────────────────────

def clear_scene():
    """Remove all mesh objects, materials, and cameras."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for material in bpy.data.materials:
        if material.users == 0:
            bpy.data.materials.remove(material)


def ensure_material(name, builder):
    """Get or create a material using a builder callable."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        mat.node_tree.nodes.clear()
        builder(mat)
    return mat


def build_simple_material(mat, base_color, roughness=0.7, metallic=0.0):
    """Simple colored Principled BSDF for furniture."""
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (400, 0)

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = (*base_color, 1.0)
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Specular IOR Level'].default_value = 0.5

    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])


def build_glass_material(mat):
    """Transparent window glass."""
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (400, 0)

    glass = nodes.new('ShaderNodeBsdfGlass')
    glass.location = (0, 0)
    glass.inputs['Color'].default_value = (0.92, 0.96, 1.0, 1.0)
    glass.inputs['Roughness'].default_value = 0.05
    glass.inputs['IOR'].default_value = 1.45

    links.new(glass.outputs['BSDF'], out.inputs['Surface'])


def build_pbr_material(mat, folder_name, scale=(1, 1, 1), tint=(1, 1, 1),
                       normal_strength=0.6, displacement_scale=0.005):
    """Build PBR material from texture folder with object-space box projection."""
    folder = TEXTURE_ROOT / folder_name
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = (900, 0)

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (500, 0)
    bsdf.inputs['Specular IOR Level'].default_value = 0.5

    texcoord = nodes.new('ShaderNodeTexCoord')
    texcoord.location = (-600, 0)

    mapping = nodes.new('ShaderNodeMapping')
    mapping.location = (-400, 0)
    mapping.inputs['Scale'].default_value = scale
    links.new(texcoord.outputs['Object'], mapping.inputs['Vector'])

    def add_image(filename, colorspace, location, non_color=False):
        path = folder / filename
        if not path.exists():
            return None
        img = bpy.data.images.load(str(path), check_existing=True)
        img.colorspace_settings.name = 'Non-Color' if non_color else 'sRGB'
        tex = nodes.new('ShaderNodeTexImage')
        tex.location = location
        tex.image = img
        tex.projection = 'BOX'
        tex.projection_blend = 0.25
        tex.interpolation = 'Linear'
        links.new(mapping.outputs['Vector'], tex.inputs['Vector'])
        return tex

    # Diffuse / Albedo
    diffuse = add_image('diffuse.jpg', 'sRGB', (-200, 300))
    if diffuse:
        mix = nodes.new('ShaderNodeMixRGB')
        mix.location = (250, 300)
        mix.blend_type = 'MULTIPLY'
        mix.inputs['Fac'].default_value = 1.0
        mix.inputs['Color2'].default_value = (*tint, 1.0)
        links.new(diffuse.outputs['Color'], mix.inputs['Color1'])
        links.new(mix.outputs['Color'], bsdf.inputs['Base Color'])

    # Roughness
    rough = add_image('roughness.jpg', 'Non-Color', (-200, 0), non_color=True)
    if rough:
        links.new(rough.outputs['Color'], bsdf.inputs['Roughness'])

    # Normal (only connect when strength is meaningful; avoids invalid tangent-space issues)
    if normal_strength > 0.0:
        normal_tex = add_image('normal.jpg', 'Non-Color', (-200, -300), non_color=True)
        if normal_tex:
            normal_map = nodes.new('ShaderNodeNormalMap')
            normal_map.location = (200, -300)
            normal_map.space = 'TANGENT'
            normal_map.inputs['Strength'].default_value = normal_strength
            links.new(normal_tex.outputs['Color'], normal_map.inputs['Color'])
            links.new(normal_map.outputs['Normal'], bsdf.inputs['Normal'])

    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    # Displacement
    if displacement_scale > 0.0:
        disp_tex = add_image('displacement.jpg', 'Non-Color', (-200, -600), non_color=True)
        if disp_tex:
            disp = nodes.new('ShaderNodeDisplacement')
            disp.location = (500, -500)
            disp.inputs['Scale'].default_value = displacement_scale
            links.new(disp_tex.outputs['Color'], disp.inputs['Height'])
            links.new(disp.outputs['Displacement'], out.inputs['Displacement'])


def get_material(name):
    """Return a cached material by name."""
    return bpy.data.materials.get(name)


def ensure_materials():
    """Pre-create all shared PBR and simple materials."""
    # Architectural materials (PBR textures)
    ensure_material('mat_floor',
                      lambda m: build_pbr_material(m, 'wood_floor', scale=(3.0, 3.0, 1.0), tint=(0.85, 0.78, 0.68)))
    ensure_material('mat_wall',
                      lambda m: build_pbr_material(m, 'plaster', scale=(2.0, 2.0, 2.0), tint=(0.98, 0.96, 0.92),
                                                   normal_strength=0.0, displacement_scale=0.0))
    ensure_material('mat_ceiling',
                      lambda m: build_pbr_material(m, 'plaster', scale=(2.0, 2.0, 2.0), tint=(1.0, 1.0, 0.98),
                                                   normal_strength=0.0, displacement_scale=0.0))
    ensure_material('mat_tile',
                      lambda m: build_pbr_material(m, 'marble_tile', scale=(2.0, 2.0, 2.0), tint=(1.0, 1.0, 1.0),
                                                   normal_strength=0.5, displacement_scale=0.002))
    ensure_material('mat_door', lambda m: build_simple_material(m, DOOR_COLOR, 0.6))
    ensure_material('mat_glass', lambda m: build_glass_material(m))
    ensure_material('mat_trim', lambda m: build_simple_material(m, TRIM_COLOR, 0.7))
    ensure_material('mat_door_backing', lambda m: build_simple_material(m, (0.08, 0.07, 0.06), 0.95))

    # Furniture materials
    for ftype, color in FURNITURE_PALETTE.items():
        rough = 0.4 if ftype in ('mirror', 'sink', 'fridge') else 0.7
        metallic = 0.6 if ftype == 'mirror' else 0.0
        ensure_material(f'mat_{ftype}', lambda m, c=color, r=rough, met=metallic: build_simple_material(m, c, r, met))


def flip_normals(obj):
    """Flip all face normals of an object so backfaces become front-facing."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.flip_normals()
    bpy.ops.object.mode_set(mode='OBJECT')


def add_box(name, location, size, material_name, rotation=0.0, flip=False):
    """Add a box with given material. size is full width/depth/height."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.active_object
    obj.name = name
    # primitive_cube_add(size=1) produces a 1 m cube; scale by the desired full dimensions
    obj.scale = size
    if abs(rotation) > 1e-4:
        obj.rotation_euler = (0, 0, rotation)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    if flip:
        flip_normals(obj)
    mat = get_material(material_name)
    if mat:
        obj.data.materials.append(mat)
    return obj


def add_wall_segment(name, p1_world, p2_world, bottom, top, thickness, material_name,
                     has_glass=False, glass_z=None, glass_height=None, glass_thickness=0.02,
                     room_center=(0.0, 0.0)):
    """Build a vertical wall segment. Solid walls use thin boxes with inward-facing normals
    so Cycles lights the interior correctly and floor/wall seams are hidden."""
    x1, y1 = p1_world
    x2, y2 = p2_world
    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx * dx + dy * dy)
    if length < 1e-3:
        return None

    mid_x = (x1 + x2) / 2
    mid_y = (y1 + y2) / 2
    angle = math.atan2(dy, dx)
    is_glass = material_name == 'mat_glass'

    if is_glass:
        # Glass stays a single plane at the exact opening size
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)
        verts = [(x1, y1, glass_z), (x2, y2, glass_z),
                 (x2, y2, glass_z + glass_height), (x1, y1, glass_z + glass_height)]
        mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
        mesh.update(calc_edges=True)
        bpy.context.collection.objects.link(obj)

        face = mesh.polygons[0]
        to_center = Vector((room_center[0] - mid_x, room_center[1] - mid_y, 0.0))
        if face.normal.dot(to_center) < 0:
            flip_normals(obj)
    else:
        # Solid wall: thin box centered on the wall centreline, shifted inward so the inner
        # face sits at the room boundary and meets the floor/ceiling edges exactly.
        to_center = Vector((room_center[0] - mid_x, room_center[1] - mid_y, 0.0))
        inward = to_center.normalized()
        cx = mid_x + inward.x * (thickness / 2)
        cy = mid_y + inward.y * (thickness / 2)
        height = (top - bottom) + 0.10
        cz = (bottom + top) / 2
        add_box(name, (cx, cy, cz), (length, thickness, height), material_name,
                rotation=angle, flip=True)
        return bpy.data.objects.get(name)

    mat = get_material(material_name)
    if mat:
        obj.data.materials.append(mat)

    return obj


def build_room_walls(fp, offset, H):
    """Build walls, doors, and windows for one room."""
    ox, oy = offset
    W = fp['dimensions']['width']
    D = fp['dimensions']['depth']
    walls = fp.get('walls', [])
    doors = fp.get('doors', [])
    windows = fp.get('windows', [])
    room_type = fp.get('room_type', 'room')
    wall_mat = 'mat_tile' if room_type in ('bathroom', 'wc_laundry') else 'mat_wall'

    # Balcony special case: only railings on 3 sides, back open to living
    if room_type == 'balcony' or not walls:
        railing_h = 1.1
        railing_thick = 0.05
        hw, hd = W / 2, D / 2
        # Front railing
        add_wall_segment('balcony_railing_n', (ox - hw, oy + hd), (ox + hw, oy + hd),
                         0, railing_h, railing_thick, wall_mat, room_center=(ox, oy))
        # Side railings
        add_wall_segment('balcony_railing_w', (ox - hw, oy - hd), (ox - hw, oy + hd),
                         0, railing_h, railing_thick, wall_mat, room_center=(ox, oy))
        add_wall_segment('balcony_railing_e', (ox + hw, oy + hd), (ox + hw, oy - hd),
                         0, railing_h, railing_thick, wall_mat, room_center=(ox, oy))
        # Back wall (sliding door frame, full height but mostly open)
        add_wall_segment('balcony_back', (ox - hw, oy - hd), (ox + hw, oy - hd),
                         0, H, 0.10, wall_mat, room_center=(ox, oy))
        return

    wall_dict = {w['id']: w for w in walls}

    for wall in walls:
        wid = wall['id']
        p1_raw = wall['p1']
        p2_raw = wall['p2']
        thickness = wall.get('thickness', 0.15)

        p1 = p1_raw
        p2 = p2_raw

        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        wall_len = math.sqrt(dx * dx + dy * dy)
        if wall_len < 1e-3:
            continue

        # Door/window openings on this wall
        wall_doors = [d for d in doors if d.get('wall_id') == wid]
        wall_windows = [w for w in windows if w.get('wall_id') == wid]

        openings = []
        # Internal doors stay closed: walls remain solid and a door slab is placed on the surface.
        # Only glass doors (sliding/balcony) are treated as windows so they remain transparent.
        for door in wall_doors:
            dw = door.get('width', 0.9)
            dh = door.get('height', 2.1)
            da = max(0.0, min(door.get('offset_along_wall', 0.0), wall_len))
            db = max(da, min(da + dw, wall_len))
            if db - da > 0.02:
                if door.get('type') in ('sliding_glass', 'glass'):
                    # Treat as a full-height glass window so it stays transparent
                    openings.append((da, db, 0, dh, 'window_glass', 0.0, dh))
                # else: leave wall solid for this opening

        for win in wall_windows:
            ww = win.get('width', 1.0)
            wh = win.get('height', 1.0)
            sill = win.get('sill_height', 0.9)
            wa = max(0.0, min(win.get('offset_along_wall', 0.0), wall_len))
            wb = max(wa, min(wa + ww, wall_len))
            if wb - wa > 0.02:
                openings.append((wa, wb, sill, sill + wh, 'window_glass', sill, wh))

        openings.sort(key=lambda o: o[0])

        segments = []
        prev_end = 0.0
        for item in openings:
            op_start, op_end, op_bottom, op_top, op_type = item[:5]
            if len(item) == 5:
                glass_z, glass_h = None, None
            else:
                glass_z, glass_h = item[5], item[6]
            if op_start > prev_end:
                segments.append((prev_end, op_start, 0, H, 'wall'))
            if op_type == 'door':
                if op_top < H:
                    segments.append((op_start, op_end, op_top, H, 'wall'))
                # Door opening is kept empty; a door slab can be added separately
            elif op_type == 'window_glass':
                if op_bottom > 0:
                    segments.append((op_start, op_end, 0, op_bottom, 'wall'))
                if op_top < H:
                    segments.append((op_start, op_end, op_top, H, 'wall'))
                segments.append((op_start, op_end, op_bottom, op_top, 'window_glass',
                                 glass_z, glass_h))
            prev_end = op_end

        if prev_end < wall_len:
            segments.append((prev_end, wall_len, 0, H, 'wall'))

        # Build each segment
        ux = dx / wall_len
        uy = dy / wall_len
        for seg in segments:
            if len(seg) == 5:
                seg_start, seg_end, seg_bottom, seg_top, seg_type = seg
                glass_z = None
                glass_h = None
            else:
                seg_start, seg_end, seg_bottom, seg_top, seg_type, glass_z, glass_h = seg

            seg_len = seg_end - seg_start
            seg_h = seg_top - seg_bottom
            if seg_len < 0.02 or seg_h < 0.02:
                continue

            mid = (seg_start + seg_end) / 2
            cx_local = p1[0] + ux * mid
            cy_local = p1[1] + uy * mid
            p1_world = (cx_local - ux * seg_len / 2 + ox,
                        cy_local - uy * seg_len / 2 + oy)
            p2_world = (cx_local + ux * seg_len / 2 + ox,
                        cy_local + uy * seg_len / 2 + oy)

            if seg_type == 'door':
                mat = 'mat_door'
            elif seg_type == 'window_glass':
                mat = 'mat_glass'
            else:
                mat = wall_mat

            add_wall_segment(f"wall_{wid}_{seg_start:.2f}", p1_world, p2_world,
                             seg_bottom, seg_top, thickness, mat,
                             has_glass=(seg_type == 'window_glass'),
                             glass_z=glass_z, glass_height=glass_h,
                             room_center=(ox, oy))


def build_door_backings(fp, offset, H, thickness=0.15):
    """Place door/window slabs in openings, flush with the inner wall face."""
    ox, oy = offset
    walls = fp.get('walls', [])
    doors = fp.get('doors', [])
    room_type = fp.get('room_type', 'room')
    if room_type == 'balcony' or not walls:
        return

    def inward_offset(p1, p2, ox_, oy_):
        """Return unit vector pointing from wall centre toward room centre."""
        cx_local = (p1[0] + p2[0]) / 2
        cy_local = (p1[1] + p2[1]) / 2
        dx_ = p2[0] - p1[0]
        dy_ = p2[1] - p1[1]
        wall_len_ = math.hypot(dx_, dy_)
        if wall_len_ < 1e-3:
            return (0.0, 0.0)
        ux_, uy_ = dx_ / wall_len_, dy_ / wall_len_
        # Outward normal (perpendicular); choose the one pointing away from room centre
        px, py = -uy_, ux_
        to_wall = (cx_local, cy_local)
        if px * to_wall[0] + py * to_wall[1] > 0:
            px, py = -px, -py
        return (px, py)

    for idx, door in enumerate(doors):
        wid = door.get('wall_id', '')
        wall = next((w for w in walls if w['id'] == wid), None)
        if wall is None:
            continue

        p1 = wall['p1']
        p2 = wall['p2']
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        wall_len = math.hypot(dx, dy)
        if wall_len < 1e-3:
            continue

        ux, uy = dx / wall_len, dy / wall_len
        dw = door.get('width', 0.9)
        dh = door.get('height', 2.1)
        da = max(0.0, min(door.get('offset_along_wall', 0.0), wall_len))
        db = max(da, min(da + dw, wall_len))
        if db - da < 0.02:
            continue

        mid_along = da + (db - da) / 2
        cx_local = p1[0] + ux * mid_along
        cy_local = p1[1] + uy * mid_along
        angle = math.atan2(dy, dx)

        # Inward normal so slab face points into the room and is lit
        ix, iy = inward_offset(p1, p2, ox, oy)
        cx = cx_local + ox + ix * (thickness / 2 - 0.02)
        cy = cy_local + oy + iy * (thickness / 2 - 0.02)
        cz = dh / 2

        is_glass = door.get('type') in ('sliding_glass', 'glass')
        mat = 'mat_glass' if is_glass else 'mat_door'
        slab_thick = 0.04 if is_glass else 0.05
        # Shrink slightly so edges don't z-fight with surrounding wall segments
        sw = max(0.02, db - da - 0.02)
        sh = max(0.02, dh - 0.02)

        add_box(f"door_{wid}_{idx}", (cx, cy, cz), (sw, slab_thick, sh), mat, rotation=angle, flip=True)


def build_floor_ceiling(fp, offset, H):
    """Build floor and ceiling for a room."""
    ox, oy = offset
    W = fp['dimensions']['width']
    D = fp['dimensions']['depth']
    room_type = fp.get('room_type', 'room')
    floor_mat = 'mat_tile' if room_type in ('bathroom', 'wc_laundry') else 'mat_floor'
    # Extend floor/ceiling slightly beyond wall centerline so they meet the inner wall faces
    wall_overhang = 0.10
    # Floor (slightly sunken so walls sit on top of it)
    add_box(f"floor_{room_type}", (ox, oy, -0.005), (W + wall_overhang * 2, D + wall_overhang * 2, 0.05), floor_mat)
    # Ceiling (skip balcony)
    if room_type != 'balcony' and fp.get('walls'):
        add_box(f"ceiling_{room_type}", (ox, oy, H + 0.005), (W + wall_overhang * 2, D + wall_overhang * 2, 0.05), 'mat_ceiling')


def load_asset_catalog():
    """Load the AI asset catalog. Returns dict or empty if missing."""
    catalog_path = Path(__file__).parent / 'asset_catalog.json'
    if not catalog_path.exists():
        return {}
    try:
        return json.loads(catalog_path.read_text())
    except Exception:
        return {}


def place_glb_asset(name, glb_path, location, rotation_z=0.0, target_size=None):
    """Import a GLB asset and place it at the given world location.

    target_size: optional (w, d, h) full dimensions in meters to scale the asset.
    The asset's geometry is NEVER modified; only its transform is changed.
    """
    import bpy
    glb_path = Path(glb_path)
    if not glb_path.exists():
        print(f"[warn] asset not found: {glb_path}")
        return None

    bpy.ops.import_scene.gltf(filepath=str(glb_path.resolve()))
    imported = bpy.context.selected_objects[:]
    if not imported:
        return None

    # Group under an empty to treat as single object
    empty = bpy.data.objects.new(name, None)
    empty.location = location
    empty.rotation_euler = (0, 0, rotation_z)
    bpy.context.collection.objects.link(empty)

    for obj in imported:
        # Parent to empty while preserving transform
        obj.parent = empty
        obj.matrix_parent_inverse = empty.matrix_world.inverted()

    if target_size:
        # Scale the empty so the asset's bounding box matches target_size
        bbox = [empty.matrix_world @ Vector(obj.bound_box[i]) for obj in imported for i in range(8)]
        if bbox:
            xs = [v.x for v in bbox]
            ys = [v.y for v in bbox]
            zs = [v.z for v in bbox]
            cur_w = max(xs) - min(xs)
            cur_d = max(ys) - min(ys)
            cur_h = max(zs) - min(zs)
            sx = target_size[0] / cur_w if cur_w > 1e-6 else 1.0
            sy = target_size[1] / cur_d if cur_d > 1e-6 else 1.0
            sz = target_size[2] / cur_h if cur_h > 1e-6 else 1.0
            empty.scale = (sx, sy, sz)

    return empty


def build_furniture(fp, offset):
    """Place furniture: prefer cached GLB assets, fall back to boxes."""
    ox, oy = offset
    catalog = load_asset_catalog()

    for idx, item in enumerate(fp.get('furniture', [])):
        t = item.get('type', 'unknown')
        x = item.get('x', 0) + ox
        y = item.get('y', 0) + oy
        z = item.get('z', 0)
        w = item.get('w', 0.5)
        d = item.get('d', 0.5)
        h = item.get('h', 0.5)
        rot = item.get('rotation', 0)

        entry = catalog.get(t)
        if entry and entry.get('default'):
            glb_path = Path(entry['default'])
            if not glb_path.is_absolute():
                glb_path = Path(__file__).parent / glb_path
            print(f"[asset] {t} using GLB: {glb_path}")
            place_glb_asset(f"furn_{t}_{idx}", glb_path, (x, y, z), rotation_z=rot, target_size=(w, d, h))
        else:
            print(f"[fallback] {t} using box primitive")
            mat_name = f"mat_{t}" if f"mat_{t}" in bpy.data.materials else 'mat_unknown'
            add_box(f"furn_{t}_{idx}", (x, y, z + h / 2), (w, d, h), mat_name, rotation=rot)


def build_baseboards(fp, offset, H):
    """Add baseboard trim around the room perimeter."""
    ox, oy = offset
    W = fp['dimensions']['width']
    D = fp['dimensions']['depth']
    if fp.get('room_type') == 'balcony' or not fp.get('walls'):
        return
    h = 0.08
    th = 0.03
    half_w = W / 2
    half_d = D / 2
    segments = [
        ((ox - half_w, oy - half_d), (ox + half_w, oy - half_d)),
        ((ox + half_w, oy - half_d), (ox + half_w, oy + half_d)),
        ((ox + half_w, oy + half_d), (ox - half_w, oy + half_d)),
        ((ox - half_w, oy + half_d), (ox - half_w, oy - half_d)),
    ]
    for i, (p1, p2) in enumerate(segments):
        add_wall_segment(f"baseboard_{i}", p1, p2, 0, h, th, 'mat_trim', room_center=(ox, oy))


def add_fill_light(room_type, ox, oy, H, W, D):
    """Add a soft omnidirectional fill light so interior walls/doors are visible."""
    light_data = bpy.data.lights.new(name=f'fill_{room_type}', type='POINT')
    # Scale light to room size so small rooms don't blow out
    light_data.energy = 120 * max(1.0, (W * D) / 6.0)
    light_data.shadow_soft_size = 0.5
    light = bpy.data.objects.new(f'fill_{room_type}', light_data)
    light.location = (ox, oy, H - 0.4)
    bpy.context.collection.objects.link(light)


def build_room(fp, offset):
    """Build one room: floor, ceiling, walls, openings, furniture, trim."""
    H = fp['dimensions'].get('height', 3.0)
    W = fp['dimensions']['width']
    D = fp['dimensions']['depth']
    build_floor_ceiling(fp, offset, H)
    build_room_walls(fp, offset, H)
    # Door slabs disabled for now: walls are kept solid so every room is watertight
    # build_door_backings(fp, offset, H)
    build_furniture(fp, offset)
    build_baseboards(fp, offset, H)
    add_fill_light(fp.get('room_type', 'room'), *offset, H, W, D)


def setup_lighting(scene):
    """Setup Cycles lighting: warm HDRI-like world, strong sun, soft fill."""
    world = scene.world
    if world is None:
        world = bpy.data.worlds.new('World')
        scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    # HDRI environment lighting
    hdri_path = TEXTURE_ROOT / 'hdri' / 'kloppenheim_06_2k.hdr'
    if hdri_path.exists():
        env_tex = nodes.new('ShaderNodeTexEnvironment')
        env_tex.location = (-300, 0)
        env_tex.image = bpy.data.images.load(str(hdri_path), check_existing=True)
        env_tex.image.colorspace_settings.name = 'Linear Rec.709'

        bg = nodes.new('ShaderNodeBackground')
        bg.location = (0, 0)
        bg.inputs['Strength'].default_value = 1.0
        links.new(env_tex.outputs['Color'], bg.inputs['Color'])
    else:
        # Fallback gradient
        bg = nodes.new('ShaderNodeBackground')
        bg.location = (0, 0)
        bg.inputs['Color'].default_value = (0.65, 0.75, 0.85, 1.0)
        bg.inputs['Strength'].default_value = 0.8

    out = nodes.new('ShaderNodeOutputWorld')
    out.location = (300, 0)
    links.new(bg.outputs['Background'], out.inputs['Surface'])

    # Key sun light - strong directional with soft edge
    sun_data = bpy.data.lights.new(name='sun', type='SUN')
    sun_data.energy = 3.0
    sun_data.color = (1.0, 0.96, 0.88)
    sun_data.angle = math.radians(8)
    sun = bpy.data.objects.new('sun', sun_data)
    sun.location = (8, 8, 12)
    sun.rotation_euler = (math.radians(55), 0, math.radians(35))
    scene.collection.objects.link(sun)



def setup_camera(fp, offset, look_dir=(0, 1, 0)):
    """Place equirectangular camera in active room."""
    ox, oy = offset
    cam_cfg = fp.get('camera', {'x': 0, 'y': 0, 'z': 1.6})
    cam_z = cam_cfg.get('z', 1.6)

    cam_data = bpy.data.cameras.new('panocam')
    cam_data.type = 'PANO'
    cam_data.panorama_type = 'EQUIRECTANGULAR'

    cam = bpy.data.objects.new('panocam', cam_data)
    cam.location = (ox + cam_cfg.get('x', 0), oy + cam_cfg.get('y', 0), cam_z)
    # Orient camera so panorama center looks along look_dir
    cam.rotation_euler = Vector(look_dir).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    print(f"[camera] {fp.get('room_type')} at ({cam.location.x:.2f}, {cam.location.y:.2f}, {cam.location.z:.2f})")


def setup_render(scene, width, height, output_path, samples=256):
    """Configure Cycles for equirectangular panorama."""
    scene.render.engine = 'CYCLES'
    # Prefer GPU if available, otherwise CPU
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.get_devices()
    gpu_device = next((d for d in prefs.devices if d.type in ('METAL', 'CUDA', 'HIP', 'OPTIX', 'OPENCL') and d.use), None)
    if gpu_device:
        prefs.compute_device_type = gpu_device.type
        scene.cycles.device = 'GPU'
        print(f"[cycles] using GPU: {gpu_device.name}")
    else:
        scene.cycles.device = 'CPU'
        print("[cycles] using CPU")
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.filepath = output_path
    scene.render.use_overwrite = True

    # Color management
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'


def render_room(active_fp, all_fps, offsets, output_dir, width=4096, height=2048,
                samples=128, look_dir=(0, 1, 0)):
    """Render one room panorama."""
    scene = bpy.context.scene
    clear_scene()
    ensure_materials()

    active_room = active_fp.get('room_type', 'room')

    # Build only the active room to guarantee clean geometry and avoid
    # door-alignment gaps between rooms.
    active_offset = offsets.get(active_room, (0.0, 0.0))
    build_room(active_fp, active_offset)

    # Place camera in active room
    setup_camera(active_fp, active_offset, look_dir=look_dir)

    # Lighting
    setup_lighting(scene)

    # Output
    out_path = str(Path(output_dir) / f"{active_room}_8k.png")
    setup_render(scene, width, height, out_path, samples=samples)

    print(f"[render] {active_room} {width}x{height} samples={samples} -> {out_path}")
    bpy.ops.render.render(write_still=True)
    print(f"[done] {active_room} saved {out_path}")
    return out_path


def load_floor_plans(fp_dir):
    """Load all room JSONs from directory."""
    fps = {}
    for p in Path(fp_dir).glob('*.json'):
        if p.name in ('computed_offsets.json', 'adjacency.json'):
            continue
        try:
            data = json.loads(p.read_text())
            if 'dimensions' not in data:
                continue
            rt = data.get('room_type', p.stem)
            fps[rt] = data
        except Exception as e:
            print(f"[warn] failed to load {p}: {e}")
    return fps


def load_offsets(offsets_path):
    """Load computed offsets JSON."""
    offsets = {}
    with open(offsets_path) as f:
        raw = json.load(f)
    for k, v in raw.items():
        if isinstance(v, dict):
            offsets[k] = (v.get('x', 0.0), v.get('y', 0.0))
        elif isinstance(v, (list, tuple)) and len(v) >= 2:
            offsets[k] = (float(v[0]), float(v[1]))
    return offsets


def main():
    argv = sys.argv
    args = argv[argv.index('--') + 1:] if '--' in argv else []

    fp_dir = 'floor_plans'
    output_dir = 'unified_renders_8k'
    width = 4096
    height = 2048
    samples = 128
    room = None
    look_dir = (0, 1, 0)

    i = 0
    while i < len(args):
        if args[i] == '--floor-plans' and i + 1 < len(args):
            fp_dir = args[i + 1]
            i += 2
        elif args[i] == '--output-dir' and i + 1 < len(args):
            output_dir = args[i + 1]
            i += 2
        elif args[i] == '--width' and i + 1 < len(args):
            width = int(args[i + 1])
            i += 2
        elif args[i] == '--height' and i + 1 < len(args):
            height = int(args[i + 1])
            i += 2
        elif args[i] == '--samples' and i + 1 < len(args):
            samples = int(args[i + 1])
            i += 2
        elif args[i] == '--room' and i + 1 < len(args):
            room = args[i + 1]
            i += 2
        elif args[i] == '--look' and i + 1 < len(args):
            vals = args[i + 1].split(',')
            look_dir = tuple(float(v) for v in vals)
            i += 2
        else:
            i += 1

    fp_dir = Path(fp_dir).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    offsets_path = fp_dir / 'computed_offsets.json'
    if not offsets_path.exists():
        print(f"[error] offsets file not found: {offsets_path}")
        sys.exit(1)

    offsets = load_offsets(offsets_path)
    all_fps = load_floor_plans(fp_dir)
    print(f"[loaded] {len(all_fps)} rooms: {', '.join(all_fps.keys())}")

    if room:
        if room not in all_fps:
            print(f"[error] room {room} not found")
            sys.exit(1)
        render_room(all_fps[room], all_fps, offsets, output_dir, width, height, samples, look_dir)
    else:
        for room_name in all_fps:
            render_room(all_fps[room_name], all_fps, offsets, output_dir, width, height, samples, look_dir)


if __name__ == '__main__':
    main()
