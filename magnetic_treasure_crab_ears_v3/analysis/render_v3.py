"""Blender renders of real exported CAD, not generated concept imagery."""
from pathlib import Path
import bpy,json,sys
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'previews';OUT=ASSETS/'verified';OUT.mkdir(exist_ok=True)
SELECTED=set(sys.argv[sys.argv.index('--')+1:]) if '--' in sys.argv else set()
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=False
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
scene.world.use_nodes=True;bg=scene.world.node_tree.nodes['Background'];bg.inputs['Color'].default_value=(.82,.85,.9,1);bg.inputs['Strength'].default_value=.5
COLORS={'purple':(.105,.018,.20),'violet':(.33,.06,.51),'blue':(.035,.12,.44),
        'gold':(.65,.31,.045),'white':(.85,.80,.64),'black':(.009,.004,.02),'band_reference':(.035,.022,.065)}
def mat(n,c):
    p=bpy.data.materials.new(n);p.use_nodes=True;p.diffuse_color=(*c,1)
    b=p.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*c,1)
    b.inputs['Metallic'].default_value=.62 if n=='gold' else 0
    b.inputs['Roughness'].default_value=.29 if n=='gold' else .38
    return p
MATS={n:mat(n,c) for n,c in COLORS.items()}
def imp(p,n,c):
    bpy.ops.wm.stl_import(filepath=str(p));o=bpy.context.object;o.name=n;o.data.materials.append(MATS[c]);return o
def light(n,pos,power,size):
    d=bpy.data.lights.new(n,'AREA');d.energy=power;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(n,d);scene.collection.objects.link(o);o.location=pos
    o.rotation_euler=(Vector((0,45,0))-o.location).to_track_quat('-Z','Y').to_euler()
light('Key',(-130,140,260),300000,180);light('Fill',(160,-70,180),170000,140);light('Rim',(-40,-160,110),90000,120)
camd=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camd);scene.collection.objects.link(cam);scene.camera=cam;camd.type='ORTHO';camd.clip_end=3000
data=json.loads((ROOT/'model_metrics.json').read_text());objects=[]
for a in data['render']:objects.append(imp(ASSETS/a['path'],a['name'],a['color']))
floor_mat=mat('floor',(.80,.82,.87));bpy.ops.mesh.primitive_plane_add(size=2000,location=(0,0,-11));floor=bpy.context.object;floor.data.materials.append(floor_mat)
def render(name,pos,target,scale,w,h):
    if SELECTED and name not in SELECTED:return
    cam.location=pos;b=(Vector(pos)-Vector(target)).normalized();r=Vector((0,1,0)).cross(b).normalized();u=b.cross(r)
    cam.rotation_euler=Matrix((r,u,b)).transposed().to_euler();camd.ortho_scale=scale
    scene.render.resolution_x=w;scene.render.resolution_y=h;scene.render.filepath=str(OUT/name);bpy.ops.render.render(write_still=True)
render('actual_v3_assembly.png',(38,-65,510),(0,49,-2),290,2200,1600)
render('actual_v3_front.png',(0,49,520),(0,49,0),290,2200,1600)
for o in objects:o.hide_render=True
floor.hide_render=True
rear=imp(ROOT/'stl/rear_magnet_carrier_print_two.stl','Rear magnetic carrier','purple')
receiver=imp(ROOT/'stl/adapters/ear_adapter_W10_R65_print_two.stl','Glue-on ear receiver','purple')
# Translate the native foot's arc center to the receiver's center, then explode.
rear.location.y=122.00625+5
render('ear_adapter_exploded.png',(35,15,165),(0,82,5),108,1800,1300)
rear.hide_render=True;receiver.hide_render=True
regions=[]
for color in ['purple','white','black']:
    regions.append(imp(ROOT/'stl'/('tall_eyes_'+color+'.stl'),'Tall eyes '+color,color))
eye_adapter=imp(ROOT/'stl/adapters/eye_adapter_W10_R65.stl','Eye glue-on saddle','purple');eye_adapter.location.z=-15
render('tall_eyes_and_adapter.png',(45,30,175),(0,93,0),90,1500,1400)
print('RENDERS COMPLETE')
