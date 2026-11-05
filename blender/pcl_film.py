"""
Hyperstead Filmstudio: baut EINE Szene aus job.json und rendert sie Bild fuer Bild als PNG.

Aufruf (film_studio.run_blender):
  blender -b --factory-startup --disable-autoexec -noaudio --python-exit-code 3 --python pcl_film.py -- job.json

Das Skript liest nur Daten (Formen, Farben, Positionen je Bild), es fuehrt nichts aus dem Job aus.
Laeuft mit Blender 3.6 bis 5.x. Fertige Bilder werden uebersprungen, ein abgebrochener Lauf setzt also fort.
"""
import json
import math
import os
import sys
import traceback

import bpy

RAD = math.pi / 180


def log(*a):
    print(*a, flush=True)


# ----------------------------------------------------------------------------- Materialien
_mats = {}


def mat(color, name="m", unlit=False, image=None):
    key = (tuple(color), unlit, image)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(name)
    m.diffuse_color = (color[0], color[1], color[2], 1)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    if image:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(image)
        tex.interpolation = "Closest" if tex.image.size[0] < 256 else "Linear"
        emi = nt.nodes.new("ShaderNodeEmission")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(tex.outputs["Color"], emi.inputs["Color"])
        nt.links.new(tex.outputs["Alpha"], mix.inputs[0])
        nt.links.new(tr.outputs[0], mix.inputs[1])
        nt.links.new(emi.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
        if hasattr(m, "surface_render_method"):  # Blender 4.2+
            m.surface_render_method = "DITHERED"
        if hasattr(m, "blend_method"):
            try:
                m.blend_method = "HASHED"
                m.shadow_method = "HASHED"
            except (AttributeError, TypeError):
                pass
    elif unlit:
        emi = nt.nodes.new("ShaderNodeEmission")
        emi.inputs["Color"].default_value = (color[0], color[1], color[2], 1)
        nt.links.new(emi.outputs[0], out.inputs["Surface"])
    else:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1)
        bsdf.inputs["Roughness"].default_value = 0.75
        for k in ("Specular IOR Level", "Specular"):
            if k in bsdf.inputs:
                bsdf.inputs[k].default_value = 0.2
                break
        nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    _mats[key] = m
    return m


_outline = None


def outline_mat():
    global _outline
    if _outline is None:
        _outline = bpy.data.materials.new("umriss")
        _outline.diffuse_color = (0, 0, 0, 1)
        _outline.use_backface_culling = True
        _outline.use_nodes = True
        nt = _outline.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        emi = nt.nodes.new("ShaderNodeEmission")
        emi.inputs["Color"].default_value = (0.02, 0.02, 0.02, 1)
        nt.links.new(emi.outputs[0], nt.nodes.new("ShaderNodeOutputMaterial").inputs["Surface"])
    return _outline


# ----------------------------------------------------------------------------- Grundformen
OUTLINE = True


def empty(name, parent=None, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.parent = parent
    e.location = loc
    return e


def prim(kind, loc, scale, color, parent=None, rot=(0, 0, 0), name="teil", line=True, unlit=False):
    ops = bpy.ops.mesh
    if kind == "kugel":
        ops.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1)
    elif kind == "zylinder":
        ops.primitive_cylinder_add(vertices=16, radius=1, depth=2)
    elif kind == "kegel":
        ops.primitive_cone_add(vertices=16, radius1=1, depth=2)
    elif kind == "dach":
        ops.primitive_cone_add(vertices=4, radius1=1, depth=2)
    elif kind == "ikosa":
        ops.primitive_ico_sphere_add(subdivisions=2, radius=1)
    else:
        ops.primitive_cube_add(size=2)
    o = bpy.context.active_object
    o.name = name
    o.location, o.scale, o.rotation_euler = loc, scale, [r * RAD for r in rot]
    if kind in ("kugel", "zylinder", "kegel", "ikosa"):
        for p in o.data.polygons:
            p.use_smooth = True
    o.data.materials.append(mat(color, name, unlit))
    if OUTLINE and line:
        o.data.materials.append(outline_mat())
        sol = o.modifiers.new("umriss", "SOLIDIFY")
        sol.thickness = 0.022 / max(0.05, min(scale))
        sol.offset = 1
        sol.use_flip_normals = True
        sol.material_offset = 1
    if parent:
        o.parent = parent
    return o


def image_plane(path, height, parent=None, loc=(0, 0, 0), name="bild"):
    img = bpy.data.images.load(path)
    w, h = img.size
    aspect = (w / h) if h else 1
    bpy.ops.mesh.primitive_plane_add(size=1)
    o = bpy.context.active_object
    o.name = name
    o.scale = (height * aspect, height, 1)
    o.rotation_euler = (90 * RAD, 0, 0)
    o.location = loc
    o.data.materials.append(mat((1, 1, 1), name, image=path))
    if parent:
        o.parent = parent
    return o, aspect


# ----------------------------------------------------------------------------- Figuren
BLACK, WHITE = (0.01, 0.01, 0.01), (0.95, 0.95, 0.95)


def build_figur(spec):
    f = spec["figur"]
    root = empty(spec["id"])
    parts = {"root": root}
    if f["typ"] == "bild":
        h = f["groesse"]
        pivot = empty(spec["id"] + "_kipp", root)
        image_plane(f["bild"], h, pivot, (0, 0, h / 2), spec["id"] + "_bild")
        parts["kipp"] = pivot
        return parts
    if f["typ"] == "blend":
        load_blend(f, root, parts)
        return parts
    art, c1, c2 = f["art"], f["farbe"], f["farbe2"]
    body = c1
    if art == "mensch":
        skin, hair = c2, f["haar"]
        legs = [x * 0.45 for x in c1]
    else:
        skin, hair, legs = c1, c1, c1
    for sx in (-1, 1):
        prim("kugel", (0.17 * sx, 0, 0.17), (0.14, 0.15, 0.19), legs, root, name="bein")
    prim("kugel", (0, 0, 0.72), (0.42, 0.36, 0.5), body, root, name="koerper")
    if art != "mensch":
        prim("kugel", (0, -0.3, 0.68), (0.27, 0.13, 0.33), c2, root, name="bauch", line=False)  # vor dem Umriss des Koerpers
    else:
        for sx in (-1, 1):
            prim("kugel", (0.07 * sx, -0.33, 0.85), (0.035, 0.02, 0.035), WHITE, root, name="knopf", line=False)
    # Arme (Pivot an der Schulter)
    for side, sx in (("l", -1), ("r", 1)):
        piv = empty(f"{spec['id']}_arm_{side}", root, (0.4 * sx, 0, 1.0))
        prim("kugel", (0, 0, -0.26), (0.085, 0.085, 0.3), body, piv, name="arm")
        prim("kugel", (0, 0, -0.55), (0.1, 0.1, 0.1), skin if art == "mensch" else c2, piv, name="hand")
        parts["arm_" + side] = piv
    # Kopf
    head = empty(spec["id"] + "_kopf", root, (0, 0, 1.15))
    parts["kopf"] = head
    prim("kugel", (0, 0, 0.32), (0.42, 0.4, 0.4), skin, head, name="kopf")
    eyes = []
    for sx in (-1, 1):
        ep = empty(spec["id"] + "_auge", head, (0.15 * sx, -0.33, 0.42))
        prim("kugel", (0, 0, 0), (0.1, 0.06, 0.12), WHITE, ep, name="auge", line=False)
        prim("kugel", (0, -0.05, -0.01), (0.055, 0.03, 0.065), BLACK, ep, name="pupille", line=False)
        eyes.append(ep)
    parts["augen"] = eyes
    if art in ("hund", "katze", "baer", "maus", "hase"):
        prim("kugel", (0, -0.36, 0.2), (0.2, 0.14, 0.13), c2, head, name="schnauze", line=False)
        prim("kugel", (0, -0.5, 0.26), (0.06, 0.04, 0.045), BLACK, head, name="nase", line=False)
        mouth_loc = (0, -0.47, 0.11)
    else:
        mouth_loc = (0, -0.38, 0.17)
    mouth = prim("kugel", mouth_loc, (0.1, 0.04, 0.06), (0.35, 0.02, 0.03), head, name="mund", line=False)
    parts["mund"] = mouth
    # Ohren / Haare
    if art == "hund":
        for sx in (-1, 1):
            prim("kugel", (0.4 * sx, 0.02, 0.36), (0.1, 0.07, 0.26), [x * 0.6 for x in c1], head, rot=(0, -18 * sx, 0), name="ohr")
        prim("kugel", (0, 0.36, 0.55), (0.06, 0.06, 0.24), c1, root, rot=(-35, 0, 0), name="schwanz")
    elif art == "katze":
        for sx in (-1, 1):
            prim("kegel", (0.25 * sx, 0, 0.7), (0.13, 0.13, 0.16), c1, head, rot=(0, 18 * sx, 0), name="ohr")
        prim("kugel", (0, 0.42, 0.75), (0.05, 0.05, 0.36), c1, root, rot=(-25, 0, 0), name="schwanz")
    elif art == "hase":
        for sx in (-1, 1):
            prim("kugel", (0.14 * sx, 0, 0.98), (0.09, 0.055, 0.36), c1, head, rot=(0, 8 * sx, 0), name="ohr")
        prim("kugel", (0, 0.38, 0.45), (0.13, 0.13, 0.13), WHITE, root, name="schwanz")
    elif art == "baer":
        for sx in (-1, 1):
            prim("kugel", (0.3 * sx, 0, 0.64), (0.13, 0.08, 0.13), c1, head, name="ohr")
    elif art == "maus":
        for sx in (-1, 1):
            prim("kugel", (0.36 * sx, 0.02, 0.62), (0.24, 0.05, 0.24), c2, head, name="ohr")
        prim("kugel", (0, 0.4, 0.3), (0.035, 0.035, 0.4), c1, root, rot=(-60, 0, 0), name="schwanz")
    elif art == "mensch":
        prim("kugel", (0, 0.04, 0.47), (0.44, 0.42, 0.3), hair, head, name="haare")
        for sx in (-1, 1):
            prim("kugel", (0.41 * sx, 0, 0.3), (0.06, 0.05, 0.08), skin, head, name="ohr", line=False)
    return parts


def load_blend(f, root, parts):
    with bpy.data.libraries.load(f["datei"], link=False) as (src, dst):
        dst.objects = list(src.objects)
        if f.get("aktion") and f["aktion"] in src.actions:
            dst.actions = [f["aktion"]]
    objs = [o for o in dst.objects if o is not None]
    if f.get("objekt"):
        top = next((o for o in objs if o.name == f["objekt"] or o.name.startswith(f["objekt"] + ".")), None)
        if top is None:
            raise RuntimeError(f"Object '{f['objekt']}' not in {os.path.basename(f['datei'])}. Available: "
                               + ", ".join(o.name for o in objs[:20]))
        keep = {top} | set(top.children_recursive) if hasattr(top, "children_recursive") else {top}
        objs = [o for o in objs if o in keep]
    keys = []
    for o in objs:
        bpy.context.scene.collection.objects.link(o)
        if o.parent is None or o.parent not in objs:
            o.parent = root
        if o.type == "MESH" and o.data.shape_keys:
            for kb in o.data.shape_keys.key_blocks:
                if kb.name.lower() in ("mund", "mouth", "mouthopen", "mund_auf", "mouth_open"):
                    keys.append(kb)
    parts["shape_mund"] = keys
    act = bpy.data.actions.get(f.get("aktion") or "")
    if act:
        for o in objs:
            if o.type == "ARMATURE":
                ad = o.animation_data_create()
                tr = ad.nla_tracks.new()
                st = tr.strips.new(act.name, int(act.frame_range[0]), act)
                st.repeat = 500
                ad.action = None


def build_prop(spec):
    root = empty(spec["id"])
    c, g, typ = spec["farbe"], spec["groesse"], spec["prop"]
    holder = empty(spec["id"] + "_g", root)
    holder.scale = (g, g, g)
    if typ == "baum":
        prim("zylinder", (0, 0, 0.6), (0.15, 0.15, 0.6), (0.25, 0.12, 0.05), holder, name="stamm")
        prim("ikosa", (0, 0, 1.65), (0.8, 0.8, 0.85), c, holder, name="krone")
    elif typ == "busch":
        prim("ikosa", (0, 0, 0.35), (0.55, 0.45, 0.4), c, holder, name="busch")
    elif typ == "haus":
        prim("wuerfel", (0, 0, 0.8), (1, 1, 0.8), c, holder, name="haus")
        prim("dach", (0, 0, 2.05), (1.5, 1.5, 0.45), (0.6, 0.08, 0.05), holder, rot=(0, 0, 45), name="dach")
        prim("wuerfel", (0, -1.0, 0.45), (0.25, 0.02, 0.45), (0.25, 0.12, 0.05), holder, name="tuer", line=False)
        for sx in (-1, 1):
            prim("wuerfel", (0.55 * sx, -1.0, 1.0), (0.2, 0.02, 0.2), (0.55, 0.8, 1.0), holder, name="fenster", line=False)
    elif typ == "stein":
        prim("ikosa", (0, 0, 0.25), (0.45, 0.35, 0.3), c, holder, name="stein")
    elif typ == "ball":
        prim("kugel", (0, 0, 0.25), (0.25, 0.25, 0.25), c, holder, name="ball")
    elif typ == "wolke":
        for x, z, r in ((-0.6, 0, 0.5), (0, 0.15, 0.7), (0.6, 0, 0.5)):
            prim("kugel", (x, 0, 4.5 + z), (r, r * 0.8, r * 0.8), c, holder, name="wolke", line=False)
    elif typ == "blume":
        prim("zylinder", (0, 0, 0.2), (0.02, 0.02, 0.2), (0.1, 0.45, 0.1), holder, name="stiel", line=False)
        prim("kugel", (0, 0, 0.42), (0.1, 0.05, 0.1), c, holder, name="bluete")
        prim("kugel", (0, -0.04, 0.42), (0.04, 0.03, 0.04), (1, 0.85, 0.1), holder, name="mitte", line=False)
    elif typ == "kiste":
        prim("wuerfel", (0, 0, 0.3), (0.3, 0.3, 0.3), c, holder, name="kiste")
    elif typ == "bild" and spec.get("bild"):
        image_plane(spec["bild"], 1.5, holder, (0, 0, 0.75), spec["id"] + "_bild")
    return {"root": root}


# ----------------------------------------------------------------------------- Welt, Licht, Kamera
def setup_world(job):
    sc = bpy.context.scene
    ort = job["ort"]
    w = bpy.data.worlds.new("welt")
    sc.world = w
    w.color = ort["himmel"]
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (*ort["himmel"], 1)
    bg.inputs["Strength"].default_value = {"tag": 1.0, "abend": 0.8, "nacht": 0.35}[ort["licht"]]
    sun_d = bpy.data.lights.new("sonne", "SUN")
    sun_d.energy = {"tag": 3.2, "abend": 2.2, "nacht": 0.7}[ort["licht"]]
    sun_d.color = {"tag": (1, 0.97, 0.9), "abend": (1, 0.62, 0.38), "nacht": (0.55, 0.65, 1)}[ort["licht"]]
    if hasattr(sun_d, "angle"):
        sun_d.angle = 8 * RAD
    sun = bpy.data.objects.new("sonne", sun_d)
    sc.collection.objects.link(sun)
    sun.rotation_euler = ({"tag": 50, "abend": 72, "nacht": 55}[ort["licht"]] * RAD, 0, 28 * RAD)
    if ort.get("boden"):
        bpy.ops.mesh.primitive_plane_add(size=400)
        g = bpy.context.active_object
        g.name = "boden"
        g.data.materials.append(mat(ort["boden"], "boden"))


def setup_camera(job):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new("kamera")
    cd.lens, cd.sensor_width, cd.clip_end = 35, 36, 500
    cam = bpy.data.objects.new("kamera", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    tgt = empty("kamera_ziel")
    con = cam.constraints.new("TRACK_TO")
    con.target = tgt
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    if job["ort"].get("hintergrund"):  # gemalter Hintergrund haengt an der Kamera und fuellt immer das Bild
        d = 150.0
        plane, aspect = image_plane(job["ort"]["hintergrund"], 1, cam, (0, 0, -d), "hintergrund")
        plane.rotation_euler = (0, 0, 0)
        view_w = 2 * d * (cd.sensor_width / 2) / cd.lens
        view_h = view_w * job["hoehe"] / job["breite"]
        s = max(view_w / aspect, view_h) * 1.02  # "cover": Bildhoehe so, dass Breite und Hoehe gefuellt sind
        plane.scale = (s * aspect, s, 1)
        if hasattr(plane, "visible_shadow"):
            plane.visible_shadow = False
    return cam, tgt


def setup_render(job):
    sc = bpy.context.scene
    r = sc.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = job["breite"], job["hoehe"], 100
    r.fps = job["fps"]
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    r.image_settings.compression = 15
    if job.get("threads"):
        r.threads_mode, r.threads = "FIXED", job["threads"]
    try:
        sc.view_settings.view_transform = "Standard"  # kraeftige Cartoon-Farben statt Filmic/AgX
    except TypeError:
        pass
    eng = job["renderer"]
    if eng == "cycles":
        r.engine = "CYCLES"
        sc.cycles.device = "CPU"
        sc.cycles.samples = job["samples"]
        sc.cycles.use_denoising = True
        r.use_persistent_data = True
    elif eng == "workbench":
        r.engine = "BLENDER_WORKBENCH"
        sh = sc.display.shading
        sh.light, sh.color_type = "STUDIO", "TEXTURE"
        sh.show_shadows = True
        sh.show_object_outline = True
        sh.show_backface_culling = True
    else:
        for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
            try:
                r.engine = e
                break
            except TypeError:
                continue
        sc.eevee.taa_render_samples = job["samples"]
        if hasattr(sc.eevee, "use_soft_shadows"):
            sc.eevee.use_soft_shadows = True


# ----------------------------------------------------------------------------- Pro Bild einstellen
def apply(parts, spec, row):
    x, y, z, rot, s, sz, swing, wave, nod, mouth, eyes, tilt, flip = row
    root = parts["root"]
    s = max(s, 0.001)
    g = spec.get("figur", {}).get("groesse", 1.0) if spec.get("figur", {}).get("typ") in ("figur", "blend") else 1.0
    root.location = (x, y, z)
    root.rotation_euler = (0, 0, rot * RAD)
    root.scale = (s * g * flip, s * g, s * g * sz)
    if "kipp" in parts:
        parts["kipp"].rotation_euler = (0, tilt * RAD, 0)
    if "arm_l" in parts:
        parts["arm_l"].rotation_euler = (swing * RAD, 0, 0)
        parts["arm_r"].rotation_euler = (-swing * RAD, -wave * RAD, 0)
    if "kopf" in parts:
        parts["kopf"].rotation_euler = (nod * RAD, 0, 0)
    if "mund" in parts:
        parts["mund"].scale = (0.1 * (1 - 0.25 * mouth), 0.04, 0.015 + 0.085 * mouth)
    for e in parts.get("augen", []):
        e.scale = (1, 1, eyes)
    for kb in parts.get("shape_mund", []):
        kb.value = mouth


def main():
    global OUTLINE
    job = json.load(open(sys.argv[sys.argv.index("--") + 1], encoding="utf-8"))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    OUTLINE = job["umriss"] and job["renderer"] != "cycles"
    setup_render(job)
    setup_world(job)
    cam, tgt = setup_camera(job)
    built = []
    for spec in job["entities"]:
        parts = build_figur(spec) if "figur" in spec else build_prop(spec)
        built.append((parts, spec))
    out = job["ausgabe"]
    os.makedirs(out, exist_ok=True)
    sc = bpy.context.scene
    done = 0
    for i in range(job["frames"]):
        path = os.path.join(out, f"{i:05d}.png")
        if os.path.exists(path) and os.path.getsize(path) > 0:
            continue
        sc.frame_set(job["erstes"] + i + 1)
        for parts, spec in built:
            apply(parts, spec, spec["frames"][i])
        cx, cy, cz, tx, ty, tz, lens = job["kamera"][i]
        cam.location, tgt.location, cam.data.lens = (cx, cy, cz), (tx, ty, tz), lens
        sc.render.filepath = path + ".tmp.png"
        bpy.ops.render.render(write_still=True)
        os.replace(path + ".tmp.png", path)  # nur fertige Bilder tragen den echten Namen
        done += 1
        if done % 10 == 0:
            log(f"PCL_FORTSCHRITT {i + 1}/{job['frames']}")
    log(f"PCL_FERTIG {done} neu gerendert")


try:
    main()
except Exception as e:
    traceback.print_exc()
    log(f"PCL_FEHLER {type(e).__name__}: {e}")
    sys.exit(3)
