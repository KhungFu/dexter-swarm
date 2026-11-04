"""Erzeugt das Hyperstead-Logo (Molekuelnetz) mit Blender/Cycles. Aufruf siehe docs/logo-prompt.md."""
import bpy, math, sys, random
from mathutils import Vector
out=sys.argv[-1]; size=int(sys.argv[-2]); samples=int(sys.argv[-3])
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
def hexc(h,a=1): h=h.lstrip('#'); c=[int(h[i:i+2],16)/255 for i in (0,2,4)]; return [((x+0.055)/1.055)**2.4 if x>0.04045 else x/12.92 for x in c]+[a]
def mat(name,col,rough=.12,coat=1.0,emit=0.0,trans=0.0):
    m=bpy.data.materials.new(name); m.use_nodes=True; b=m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value=hexc(col); b.inputs['Roughness'].default_value=rough
    b.inputs['Coat Weight'].default_value=coat; b.inputs['Coat Roughness'].default_value=.03
    if emit: b.inputs['Emission Color'].default_value=hexc(col); b.inputs['Emission Strength'].default_value=emit
    if trans: b.inputs['Transmission Weight'].default_value=trans; b.inputs['IOR'].default_value=1.45
    return m
def sphere(p,r,m):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96,ring_count=48,radius=r,location=p); o=bpy.context.object
    bpy.ops.object.shade_smooth(); o.data.materials.append(m); return o
rodm=mat('rod','#e8f1ff',rough=.18,coat=1,trans=.35)
def rod(a,b,r):
    a,b=Vector(a),Vector(b); d=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=r,depth=d.length,location=(a+b)/2); o=bpy.context.object
    o.rotation_mode='QUATERNION'; o.rotation_quaternion=d.to_track_quat('Z','Y'); bpy.ops.object.shade_smooth(); o.data.materials.append(rodm)
# Hierarchie: Zentrum -> 4 Leiter -> Agenten (organisch verteilt)
C=(0,0,0); sphere(C,1.0,mat('core','#0099ff',rough=.05,emit=.0))
leaders=[('#ff8a1f',(2.05,0.5,1.05),3),('#14d6c8',(-2.0,0.9,0.85),2),('#8b5cf6',(-1.15,-0.6,-1.95),3),('#34d97b',(1.55,1.0,-1.6),2)]
small=['#ff4fa3','#ffd23f','#ff6b5e','#5eead4','#c4f15a','#f472b6','#60a5fa','#fbbf24','#a78bfa','#fb7185']
rnd=random.Random(7); k=0
for col,p,n in leaders:
    P=Vector(p); rod(C,P,.11); sphere(P,.56,mat('l'+col,col))
    out_dir=P.normalized()
    for j in range(n):
        ang=(j-(n-1)/2)*1.05+rnd.uniform(-.25,.25)
        side=out_dir.cross(Vector((0,1,0))).normalized(); up=Vector((0,1,0))
        d=(out_dir*1.0+side*math.sin(ang)*1.15+up*(rnd.uniform(-.7,.7))).normalized()
        Q=P+d*rnd.uniform(1.15,1.45); rod(P,Q,.065); sphere(Q,.3,mat('s%d'%k,small[k%len(small)])); k+=1
# Welt: dunkles Navy
w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=hexc('#0d1d4a'); w.node_tree.nodes['Background'].inputs[1].default_value=1.0
def light(loc,e,sz,col='#ffffff'):
    bpy.ops.object.light_add(type='AREA',location=loc); L=bpy.context.object; L.data.energy=e; L.data.size=sz; L.data.color=hexc(col)[:3]
    L.rotation_mode='QUATERNION'; L.rotation_quaternion=(Vector((0,0,0))-Vector(loc)).to_track_quat('-Z','Y')
light((-5,-6,8),1800,6); light((7,-3,3),900,4,'#9fd8ff'); light((-3,6,2),260,5,'#c9a7ff'); light((0,-6,-7),220,6,'#6ab0ff')
# weicher Schein hinter dem Zentrum
bpy.ops.mesh.primitive_plane_add(size=40,location=(0,9,0),rotation=(math.pi/2,0,0)); bg=bpy.context.object
bm=bpy.data.materials.new('bg'); bm.use_nodes=True; nt=bm.node_tree; nt.nodes.clear()
tc=nt.nodes.new('ShaderNodeTexCoord'); mp=nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value=(0.09,0.09,0.09)
gr=nt.nodes.new('ShaderNodeTexGradient'); gr.gradient_type='SPHERICAL'; cr=nt.nodes.new('ShaderNodeValToRGB')
cr.color_ramp.elements[0].color=hexc('#050b20'); cr.color_ramp.elements[1].color=hexc('#132a66'); cr.color_ramp.elements[1].position=.85
em=nt.nodes.new('ShaderNodeEmission'); em.inputs[1].default_value=.55; o=nt.nodes.new('ShaderNodeOutputMaterial')
nt.links.new(tc.outputs['Object'],mp.inputs[0]); nt.links.new(mp.outputs[0],gr.inputs[0]); nt.links.new(gr.outputs['Fac'],cr.inputs[0]); nt.links.new(cr.outputs[0],em.inputs[0]); nt.links.new(em.outputs[0],o.inputs[0])
bg.data.materials.append(bm); bg.visible_shadow=False; bg.visible_diffuse=False; bg.visible_glossy=False
bpy.ops.object.camera_add(location=(0.6,-11.5,2.4)); cam=bpy.context.object; sc.camera=cam
cam.rotation_mode='QUATERNION'; cam.rotation_quaternion=(Vector((0.0,0,-0.15))-cam.location).to_track_quat('-Z','Y'); cam.data.lens=55
sc.render.engine='CYCLES'; sc.cycles.samples=samples; sc.cycles.use_denoising=True; sc.cycles.device='CPU'
sc.render.resolution_x=sc.render.resolution_y=size; sc.render.film_transparent=False
sc.view_settings.view_transform='AgX'; sc.view_settings.look='AgX - Punchy'
sc.render.filepath=out; bpy.ops.render.render(write_still=True); print('FERTIG',out)
