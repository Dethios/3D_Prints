"""Verify source-mount preservation and prepare nominal assembly positions."""
from pathlib import Path
import sys,json,math,hashlib
ROOT=Path(__file__).resolve().parents[1]
if (ROOT.parent/'.cad_deps').exists():sys.path.insert(0,str(ROOT.parent/'.cad_deps'))
import numpy as np
import trimesh
import cadquery as cq
from shapely import affinity
from shapely.geometry import Point,box
from build_reference_mounts import outline,cut,circular_caps,functional_core

def T(x=0,y=0,z=0):
    m=np.eye(4);m[:3,3]=[x,y,z];return m
def R(a):
    a=math.radians(a);m=np.eye(4);m[:2,:2]=[[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]];return m
def transform(m,mat):
    n=m.copy();n.apply_transform(mat);return n
def intersection_volume(a,b):
    m=trimesh.boolean.intersection([a,b],engine='manifold')
    return 0. if m.is_empty else float(abs(m.volume))

def check():
    report=json.loads((ROOT/'CAD/reference_geometry_report.json').read_text())
    positions={};results=[];step_results=[];fits={}
    poses=json.loads((ROOT/'Reference_files/NX3_poses.json').read_text())
    for family,info in report.items():
        stldir=ROOT/'STL'/family
        meshes={p.stem:trimesh.load_mesh(p) for p in stldir.glob('*.stl')}
        for name,m in meshes.items():
            groups=m.split();expected='separate artwork islands' if 'raised_' in name else 'one connected solid'
            assert m.is_watertight and m.is_winding_consistent and m.volume>0,name
            assert ('raised_' in name) or len(groups)==1,(family,name,len(groups))
            results.append({'family':family,'file':name+'.stl','watertight':True,'winding_consistent':True,
                'solid_components':len(groups),'expected':expected,'size_mm':m.extents.tolist(),
                'volume_mm3':float(m.volume),'solid_equivalent_PLA_g_1p24':float(m.volume*.00124),
                'sha256':hashlib.sha256((stldir/(name+'.stl')).read_bytes()).hexdigest()})
        original=trimesh.load_mesh(ROOT/'Reference_files'/info['source_ear'])
        original.apply_translation((info['source_x_translation_mm'],0,0))
        ymax=info['protected_region_y_max_mm']
        source_footer=max(cut(original,info['source_spec']['cut_y']).split(),key=lambda m:m.volume)
        source_part=functional_core(source_footer,ymax);new_part=functional_core(meshes['ear_blue_base'],ymax)
        # Symmetric difference checks the whole functional strip, not just hole centres.
        lost=trimesh.boolean.difference([source_part,new_part],engine='manifold')
        added=trimesh.boolean.difference([new_part,source_part],engine='manifold')
        lost_v=0. if lost.is_empty else abs(float(lost.volume));added_v=0. if added.is_empty else abs(float(added.volume))
        assert lost_v<.005 and added_v<.005,(family,lost_v,added_v)
        assert len(circular_caps(meshes['mount_test_strip']))==5
        assert len(circular_caps(meshes['center_hat_blue_base']))==3
        # The new objects must not add interference with their original counterpart.
        source_overlap=intersection_volume(source_footer,meshes['glue_on_base_SOURCE_GEOMETRY'])
        new_overlap=intersection_volume(meshes['ear_blue_base'],meshes['glue_on_base_SOURCE_GEOMETRY'])
        assert new_overlap<=source_overlap+.005,(family,source_overlap,new_overlap)
        fits[family]={'protected_mount_missing_mm3':lost_v,'protected_mount_extra_mm3':added_v,
          'source_mount_intersection_with_base_mm3':source_overlap,'revised_mount_intersection_with_base_mm3':new_overlap,
          'all_5_original_bores_preserved':True,'center_hat_uses_3_original_bores':True}
        if family=='NX3':
            band=trimesh.load_mesh(ROOT/'Reference_files/dressyspider_larger_headband_source.stl')
            mats=[np.array(p)@T(.52529784,0,0) for p in poses['dressyspider_larger_headband_source']]
            cx=(band.bounds[0,0]+band.bounds[1,0])/2
            band_geo=outline(band)
        else:
            # A visual stand-in for a store-bought band, not a new mounting part.
            band_geo=Point(0,0).buffer(73.5,quad_segs=128).difference(Point(0,0).buffer(70,quad_segs=128))
            band_geo=band_geo.intersection(box(-80,-59,80,80))
            mats=[R(40)@T(0,87,0),R(-40)@T(0,87,0)];cx=0.
        # The original bases occupy most of the crown arc. A center adapter uses
        # its original flat side for bonding to the FRONT face of the band.
        cap_outline=outline(meshes['center_hat_glue_base_3_of_5'])
        best=max(((band_geo.intersection(affinity.translate(cap_outline,xoff=cx,yoff=y)).area,y)
                   for y in np.arange(45.,105.,.1)),key=lambda v:v[0])
        assert best[0]>35.,('Insufficient nominal crown bonding area',family,best)
        hat_mat=T(cx,float(best[1]),10.4)
        placed=[transform(meshes['left_brooms_assembled'],mats[0]),
                transform(meshes['right_mouse_assembled'],mats[1]),
                transform(meshes['center_hat_assembled'],hat_mat)]
        accessory_overlaps=[]
        for i,j in [(0,1),(0,2),(1,2)]:
            v=intersection_volume(placed[i],placed[j]);assert v<.005,(family,i,j,v)
            accessory_overlaps.append(v)
        fits[family].update(nominal_accessory_intersections_mm3=accessory_overlaps,
                            nominal_center_adapter_front_bond_projection_mm2=float(best[0]))
        positions[family]={'left_brooms':mats[0].tolist(),'right_mouse':mats[1].tolist(),
             'center_hat':hat_mat.tolist(),'center_hat_note':'Front-face bond with 0.4 mm nominal adhesive gap; not a new interface.'}
    for p in sorted((ROOT/'CAD').glob('*/*.step')):
        s=cq.importers.importStep(str(p)).val();assert all(v.isValid() for v in s.Solids()),p
        step_results.append({'file':str(p.relative_to(ROOT)),'valid_solids':len(s.Solids())})
    (ROOT/'CAD/assembly_positions.json').write_text(json.dumps(positions,indent=2))
    data={'status':'PASS','stl_file_count':len(results),'step_file_count':len(step_results),
         'mesh_checks':results,'step_checks':step_results,'source_compatibility_checks':fits,
         'limitations':['No physical print or retention-force testing.',
           'Reference meshes themselves have small tessellation overlaps; compare revised geometry against that baseline.',
           'NX3 and Tim J interfaces are separate; do not mix their bases and ears.',
           'Center hat uses a trimmed three-position subset of each source interface; front-mounted adapter needs physical bonding and clearance checks.']}
    (ROOT/'validation_results.json').write_text(json.dumps(data,indent=2))
    print(json.dumps({'status':'PASS','stl_file_count':len(results),'step_file_count':len(step_results),'source_compatibility_checks':fits},indent=2))

if __name__=='__main__':check()
