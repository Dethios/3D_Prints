"""Blender renders of the delivered reference-based STL files."""
import bpy,struct,math,json
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
positions=json.loads((ROOT/'CAD/assembly_positions.json').read_text())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=False
scene.render.resolution_x=1700;scene.render.resolution_y=1450;scene.render.resolution_percentage=100
scene.world.color=(.7,.7,.7);scene.view_settings.view_transform='Standard';scene.render.image_settings.file_format='PNG'
def material(n,c,metal=0):
 m=bpy.data.materials.new(n);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF')
 p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=.4;p.inputs['Metallic'].default_value=metal
 return m
blue=material('Navy backing',(.023,.055,.17));gold=material('Raised gold',(.84,.54,.075),.25)
white=material('White stars',(.91,.92,.93));black=material('Reference headband/base',(.018,.022,.03));gray=material('Backdrop',(.90,.925,.95))
def meshfile(path,mat,transform=Matrix.Identity(4)):
 data=path.read_bytes();n=struct.unpack_from('<I',data,80)[0];verts=[];faces=[]
 for i in range(n):
  q=struct.unpack_from('<12fH',data,84+i*50);k=len(verts);verts.extend([q[3:6],q[6:9],q[9:12]]);faces.append((k,k+1,k+2))
 me=bpy.data.meshes.new(path.stem);me.from_pydata(verts,[],faces);me.update()
 ob=bpy.data.objects.new(path.stem,me);scene.collection.objects.link(ob);ob.data.materials.append(mat);ob.matrix_world=transform;return ob
def T(x=0,y=0,z=0):return Matrix.Translation(Vector((x,y,z)))
def camera(loc,target,scale):
 bpy.ops.object.camera_add(location=loc);cam=bpy.context.object
 cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=scale;scene.camera=cam
def light(loc,power,size):
 bpy.ops.object.light_add(type='AREA',location=loc);ob=bpy.context.object;ob.data.energy=power;ob.data.shape='DISK';ob.data.size=size
 ob.rotation_euler=(Vector((0,40,0))-ob.location).to_track_quat('-Z','Y').to_euler()
light((-130,160,230),450000,170);light((160,20,150),280000,160)
for family in ['NX3','TimJ']:
 for ob in list(scene.objects):
  if ob.type in {'MESH','CAMERA'}:bpy.data.objects.remove(ob,do_unlink=True)
 folder=ROOT/'STL'/family
 for name in ['left_brooms','right_mouse']:
  mat=Matrix(positions[family][name]);meshfile(folder/'ear_blue_base.stl',blue,mat)
  meshfile(folder/(name+'_raised_gold.stl'),gold,mat)
  if family=='TimJ':meshfile(folder/'glue_on_base_SOURCE_GEOMETRY.stl',black,mat)
 if family=='NX3':
  meshfile(ROOT/'Reference_files/dressyspider_larger_headband_source.stl',black)
 else:
  # Render-only generic band. It is not a supplied print or mounting design.
  vs=[];fs=[]
  for i in range(161):
   a=math.radians(-145+290*i/160)
   for r,z in [(70,0),(73.5,0),(70,10),(73.5,10)]:vs.append((r*math.sin(a),r*math.cos(a),z))
  for i in range(160):
   for j,k in [(0,1),(1,3),(3,2),(2,0)]:fs.append((4*i+j,4*(i+1)+j,4*(i+1)+k,4*i+k))
  fs.extend([(0,2,3,1),(640,641,643,642)])
  me=bpy.data.meshes.new('Store bought band placeholder');me.from_pydata(vs,[],fs);me.update()
  ob=bpy.data.objects.new('Store bought band placeholder',me);scene.collection.objects.link(ob);ob.data.materials.append(black)
 h=Matrix(positions[family]['center_hat']);meshfile(folder/'center_hat_blue_base.stl',blue,h)
 meshfile(folder/'center_hat_raised_white.stl',white,h);meshfile(folder/'center_hat_glue_base_3_of_5.stl',black,h)
 bpy.ops.mesh.primitive_plane_add(size=2000,location=(0,0,-5));bpy.context.object.data.materials.append(gray)
 camera((3,35,500),(3,35,0),285)
 scene.render.filepath=str(ROOT/'previews'/(family+'_assembly_front.png'));bpy.ops.render.render(write_still=True)
 # Actual source interface only, exploded along Y to expose all five bores.
 for ob in list(scene.objects):
  if ob.type in {'MESH','CAMERA'}:bpy.data.objects.remove(ob,do_unlink=True)
 meshfile(folder/'mount_test_strip.stl',blue,T(0,9,0))
 meshfile(folder/'glue_on_base_SOURCE_GEOMETRY.stl',black)
 bpy.ops.mesh.primitive_plane_add(size=1000,location=(0,0,-4));bpy.context.object.data.materials.append(gray)
 camera((55,-100,100),(0,2 if family=='NX3' else -5,5),110)
 scene.render.resolution_x=1500;scene.render.resolution_y=1000
 scene.render.filepath=str(ROOT/'previews'/(family+'_source_mount_exploded.png'));bpy.ops.render.render(write_still=True)
 scene.render.resolution_x=1700;scene.render.resolution_y=1450
