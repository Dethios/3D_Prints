#!/usr/bin/env python3
"""Two-layer sorcerer artwork on unscaled source magnetic interfaces.

The functional lower strips are CLIPPED FROM THE ORIGINAL STL FILES.
No mounting curve, bore position, diameter or depth is invented here.
NX3 and Tim J are distinct interfaces and must not be mixed.
"""
from pathlib import Path
import sys,json,math,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1]
if (ROOT.parent/'.cad_deps').exists():sys.path.insert(0,str(ROOT.parent/'.cad_deps'))
import numpy as np
import trimesh
import cadquery as cq
from shapely.geometry import Polygon,box,shape,mapping
from shapely import affinity
from shapely.ops import unary_union
from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing,BRepBuilderAPI_MakeFace

BACKING=2.0
RELIEF=1.2
EAR_ANGLE=40.0
STL_TOLERANCE=.045
MAGNET_DIAMETER=6.0
MAGNET_THICKNESS=3.0

def load(name):return trimesh.load_mesh(ROOT/'Reference_files'/name)
def polygons(g):return [g] if g.geom_type=='Polygon' else list(g.geoms)
def planar_solid(g,z,h):
    solids=[]
    for p in polygons(g):
        if p.is_empty or p.area<.02:continue
        outer=cq.Wire.makePolygon([cq.Vector(x,y,z) for x,y in list(p.exterior.coords)[:-1]],close=True)
        holes=[cq.Wire.makePolygon([cq.Vector(x,y,z) for x,y in list(r.coords)[:-1]],close=True) for r in p.interiors]
        solids.append(cq.Solid.extrudeLinear(outer,holes,cq.Vector(0,0,h)))
    return solids[0] if len(solids)==1 else cq.Compound.makeCompound(solids)
def mesh_from_cq(s):
    v,f=s.tessellate(STL_TOLERANCE,.12)
    return trimesh.Trimesh([[p.x,p.y,p.z] for p in v],f,process=True)
def step_from_mesh(m):
    """A sewn, closed faceted BRep preserves the supplied STL surface."""
    sewing=BRepBuilderAPI_Sewing(1e-5)
    for tri in m.triangles:
        wire=cq.Wire.makePolygon([cq.Vector(*p) for p in tri],close=True)
        sewing.Add(BRepBuilderAPI_MakeFace(wire.wrapped).Face())
    sewing.Perform(); sewn=cq.Shape.cast(sewing.SewedShape())
    ss=[cq.Solid.makeSolid(shell) for shell in sewn.Shells()]
    s=ss[0] if len(ss)==1 else cq.Compound.makeCompound(ss)
    s=s.fix().clean()
    assert all(t.isValid() for t in s.Solids()),'Invalid faceted BRep'
    return s
def clipping_box(m,ymax=None,xhalf=None):
    lo=m.bounds[0]-1;hi=m.bounds[1]+1
    if ymax is not None:hi[1]=ymax
    if xhalf is not None:lo[0]=-xhalf;hi[0]=xhalf
    return trimesh.creation.box(bounds=np.array([lo,hi]))
def cut(m,ymax=None,xhalf=None):
    return trimesh.boolean.intersection([m,clipping_box(m,ymax,xhalf)],engine='manifold')
def union(meshes):return trimesh.boolean.union(meshes,engine='manifold')
def functional_core(m,ymax):
    lo=m.bounds[0]-1;hi=m.bounds[1]+1
    lo[2]=BACKING+.01;hi[1]=ymax
    return trimesh.boolean.intersection([m,trimesh.creation.box(bounds=np.array([lo,hi]))],engine='manifold')
def outline(m):
    # Project triangles, then fill only internal silhouette openings.
    ps=[]
    for t in m.triangles[:,:,:2]:
        p=Polygon(t)
        if p.area>1e-9:ps.append(p)
    g=unary_union(ps).buffer(.00001).buffer(-.00001)
    p=max(polygons(g),key=lambda q:q.area)
    return Polygon(p.exterior).simplify(.012,preserve_topology=True)
def circular_caps(m):
    caps=[]
    for i,a in enumerate(m.facets_area):
        fs=m.facets[i]
        if 26<a<29 and len(fs)>=17 and abs(m.facets_normal[i,2])<.03:
            c=np.average(m.triangles_center[fs],axis=0,weights=m.area_faces[fs])
            caps.append({'center':c.tolist(),'normal':m.facets_normal[i].tolist()})
    return sorted(caps,key=lambda c:c['center'][0])
def fit_art(g,usable,cx,cy):
    # Fit without clipping any silhouette or star. Only artwork may be scaled.
    for scale in np.arange(1.00,.54,-.02):
        a=affinity.scale(g,scale,scale,origin=(0,0))
        for dy in np.arange(0,24.1,.5):
            candidate=affinity.translate(a,xoff=cx,yoff=cy+dy)
            if usable.buffer(.001).covers(candidate):return candidate,{'scale':float(scale),'radial_offset_mm':float(dy)}
    raise ValueError('Artwork does not fit template')
def matrix_shift(dx=0,dy=0,dz=0):
    m=np.eye(4);m[:3,3]=[dx,dy,dz];return m
def save_step(s,path):
    assert all(t.isValid() for t in s.Solids())
    cq.exporters.export(s,str(path))
def save_mesh(m,path):
    assert m.is_watertight and m.is_winding_consistent and m.volume>0,path
    m.export(path)

def build():
    arts=json.loads((ROOT/'CAD/artwork.json').read_text())
    # Circle centre is only used to position artwork; no source mount is scaled.
    specs={
      'NX3':dict(ear='NX3_Mickey_Fantasia_source.stl',base='Titanhunter_NX3_glue_adapter_source.stl',
                 cx=.52529784,cy=38.79776001,cut_y=14.5,hat_halfwidth=20.0),
      'TimJ':dict(ear='TimJ_MickeyEar_Blank_source.stl',base='TimJ_MickeyEar_Base_source.stl',
                  cx=0.,cy=20.,cut_y=0.,hat_halfwidth=24.5)}
    report={};out={}
    poses=json.loads((ROOT/'Reference_files/NX3_poses.json').read_text())
    for family,spec in specs.items():
        print('Building reference family',family,flush=True)
        stldir=ROOT/'STL'/family;caddir=ROOT/'CAD'/family
        stldir.mkdir(parents=True,exist_ok=True);caddir.mkdir(exist_ok=True)
        original=load(spec['ear']); original.apply_translation((-spec['cx'],0,0))
        footprint=outline(original)
        strip_components=cut(original,spec['cut_y']).split()
        # The NX3 file has a small disconnected shoe fragment in this crop.
        # Keep the actual five-bore strip, not unrelated source artwork.
        footer=max(strip_components,key=lambda m:m.volume)
        assert len(circular_caps(footer))==5
        # The blue backing begins just above the protected mounting strip.
        plate_region=footprint.intersection(box(-60,spec['cut_y']-.05,60,120))
        plate=planar_solid(plate_region,0,BACKING)
        # Close the visual gap above the source bar with the same 2 mm backing.
        # Its lower edge is inset 1.1 mm from the source outline, safely away
        # from the mating face. It adds nothing above the pocket-floor height.
        gap_fill=planar_solid(footprint.buffer(-1.10),0,BACKING)
        blue=union([footer,mesh_from_cq(plate),mesh_from_cq(gap_fill)])
        print('Converting source strip to CAD',family,flush=True)
        blue_cad=step_from_mesh(blue)
        save_mesh(blue,stldir/'ear_blue_base.stl');save_step(blue_cad,caddir/'ear_blue_base.step')
        save_mesh(footer,stldir/'mount_test_strip.stl')
        adapter=load(spec['base'])
        if family=='NX3':
            # Put the downloaded glue-on adapter into the ear's reference frame.
            pose=np.array(poses[spec['base'].removesuffix('.stl')][0])
            adapter.apply_transform(np.linalg.inv(pose));adapter.apply_translation((-spec['cx'],0,0))
        save_mesh(adapter,stldir/'glue_on_base_SOURCE_GEOMETRY.stl')
        save_step(step_from_mesh(adapter),caddir/'glue_on_base_SOURCE_GEOMETRY.step')
        usable=footprint.buffer(-3).intersection(box(-60,spec['cut_y']+.5,60,120))
        border=footprint.difference(footprint.buffer(-3)).intersection(box(-60,spec['cut_y']+.3,60,120))
        generated={'blue_base':blue,'source_footer':footer,'adapter':adapter}
        placements={}
        for name,key,rotation in [('left_brooms','brooms',-EAR_ANGLE),('right_mouse','mouse',EAR_ANGLE)]:
            print('Artwork',family,name,flush=True)
            g=affinity.rotate(shape(arts[key]),rotation,origin=(0,0))
            g,fit=fit_art(g,usable,0,spec['cy'])
            g=unary_union([g,border]).simplify(.025,preserve_topology=True)
            gold=planar_solid(g,BACKING,RELIEF);gold_m=mesh_from_cq(gold)
            assembled=union([blue,gold_m])
            save_mesh(gold_m,stldir/(name+'_raised_gold.stl'))
            save_mesh(assembled,stldir/(name+'_assembled.stl'))
            save_step(gold,caddir/(name+'_raised_gold.step'))
            save_step(cq.Compound.makeCompound([blue_cad,gold]),caddir/(name+'_layer_assembly.step'))
            generated[name]=assembled;generated[name+'_gold']=gold_m
            placements[name]=fit
        # Center hat: only the middle THREE existing positions of this family.
        # The full original mating surface is simply trimmed at the ends.
        hat_strip=cut(footer,xhalf=spec['hat_halfwidth'])
        hat_adapter=cut(adapter,xhalf=spec['hat_halfwidth'])
        # The existing artwork outline, with no custom rectangular foot.
        import svgpathtools
        def pathpoly(d):
            p=svgpathtools.parse_path(d);pts=[]
            for seg in p:
                n=max(3,math.ceil(seg.length(error=1e-4)/.25))
                pts += [(seg.point(i/n).real,seg.point(i/n).imag) for i in range(n)]
            return Polygon(pts).buffer(0)
        cone=pathpoly('M -17 -15 C -13 -3 -11 20 -6 32 C -3 39 1 31 2 28 C 6 10 11 -3 16 -15 Z')
        from shapely.geometry import Point
        brim=affinity.scale(Point(0,-16).buffer(1,quad_segs=40),20,4.5,origin=(0,-16))
        # Tim J's strip has a lower central attachment edge than the crop
        # plane. Seat the existing brim into that strip so the hat is connected.
        hat_shift=spec['cut_y']+(14.0 if family=='TimJ' else 18.5)
        hat2d=affinity.translate(cone.union(brim),yoff=hat_shift)
        hatplate=hat2d if family=='TimJ' else hat2d.intersection(box(-60,spec['cut_y']-.05,60,120))
        hatblue=union([hat_strip,mesh_from_cq(planar_solid(hatplate,0,BACKING))])
        white2d=affinity.translate(shape(arts['hat']),yoff=hat_shift)
        white=planar_solid(white2d,BACKING,RELIEF);white_m=mesh_from_cq(white)
        hat=union([hatblue,white_m])
        for n,m in [('center_hat_blue_base',hatblue),('center_hat_raised_white',white_m),
                    ('center_hat_assembled',hat),('center_hat_glue_base_3_of_5',hat_adapter)]:
            save_mesh(m,stldir/(n+'.stl'))
            save_step(white if n=='center_hat_raised_white' else step_from_mesh(m),caddir/(n+'.step'))
        generated.update(hat_blue=hatblue,hat_white=white_m,hat=hat,hat_adapter=hat_adapter)
        out[family]=generated
        # Region well below the seam must be IDENTICAL to original geometry.
        protected=functional_core(blue,spec['cut_y']-.10)
        expected=functional_core(footer,spec['cut_y']-.10)
        missing=trimesh.boolean.difference([expected,protected],engine='manifold').volume
        extra=trimesh.boolean.difference([protected,expected],engine='manifold').volume
        assert abs(missing)<.005 and abs(extra)<.005,(family,missing,extra)
        report[family]={'source_ear':spec['ear'],'source_glue_base':spec['base'],
           'source_ear_sha256':hashlib.sha256((ROOT/'Reference_files'/spec['ear']).read_bytes()).hexdigest(),
           'source_base_sha256':hashlib.sha256((ROOT/'Reference_files'/spec['base']).read_bytes()).hexdigest(),
           'mount_geometry_method':'Unscaled original mesh clipped below specified Y; base rigidly transformed only',
           'source_x_translation_mm':-spec['cx'],'protected_region_y_max_mm':spec['cut_y']-.10,
           'protected_region_z_min_mm':BACKING+.01,
           'non_mount_artwork_fragments_removed':len(strip_components)-1,
           'protected_mount_missing_volume_mm3':float(missing),'protected_mount_extra_volume_mm3':float(extra),
           'bore_caps':circular_caps(footer),'hat_bore_caps':circular_caps(hat_strip),
           'artwork_placement':placements,'source_spec':spec,
           'center_hat_note':'Trimmed source curve using only the central three of five original bores; mount at crown front to avoid the ear frames.'}
    (ROOT/'CAD'/'reference_geometry_report.json').write_text(json.dumps(report,indent=2))
    return out,report

if __name__=='__main__':build()
