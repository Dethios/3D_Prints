from pathlib import Path
import json,sys,itertools,math
import numpy as np
import cadquery as cq
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'cad'))
import build_crab_v3 as m

def read_stl(path):
    raw=Path(path).read_bytes();n=int.from_bytes(raw[80:84],'little')
    assert len(raw)==84+50*n
    a=np.frombuffer(raw,dtype=np.dtype([('n','<f4',(3,)),('v','<f4',(3,3)),('a','<u2')]),offset=84)
    return a['v'].astype(float)
def mesh_check(path):
    t=read_stl(path);v,i=np.unique(np.round(t.reshape(-1,3),5),axis=0,return_inverse=True);f=i.reshape(-1,3)
    ee=np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]);se=np.sort(ee,axis=1)
    e,inv,count=np.unique(se,axis=0,return_inverse=True,return_counts=True)
    balance=np.bincount(inv,weights=np.where(ee[:,0]<ee[:,1],1,-1))
    parent=np.arange(len(v))
    def root(a):
        while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
        return a
    for a,b in e:
        x,y=root(a),root(b)
        if x!=y:parent[y]=x
    volume=float(np.einsum('ij,ij->i',t[:,0],np.cross(t[:,1],t[:,2])).sum()/6)
    area=np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)/2
    return {'triangles':len(t),'boundary_edges':int(sum(count==1)),'nonmanifold_edges':int(sum(count>2)),
      'orientation_errors':int(sum(balance!=0)),'degenerate_faces':int(sum(area<1e-8)),
      'components':len({root(j) for j in range(len(v))}),'volume_mm3':volume,
      'bounds_mm':[t.reshape(-1,3).min(0).tolist(),t.reshape(-1,3).max(0).tolist()]}
def run():
    meta=json.loads((ROOT/'model_metrics.json').read_text())
    r={'parts':{},'assembly_intersections_mm3':{},'failures':[],'physical_tested':False}
    for name,data in meta['parts'].items():
        folder=ROOT/'stl'/'adapters' if 'adapter_' in name else ROOT/'stl'
        q=mesh_check(folder/(name+'.stl'));r['parts'][name]=q
        if any(q[k] for k in ['boundary_edges','nonmanifold_edges','orientation_errors','degenerate_faces']) or q['components']!=1:
            r['failures'].append('Nonmanifold/disconnected '+name)
        q['mesh_volume_error_percent']=100*abs(q['volume_mm3']-data['volume_mm3'])/data['volume_mm3']
        if q['mesh_volume_error_percent']>.2:r['failures'].append('Volume discrepancy '+name)
    for p in sorted((ROOT/'cad').glob('*.step')):
        if p.stem=='crab_v3_assembly':continue
        shape=cq.importers.importStep(str(p)).val()
        if not shape.isValid() or len(shape.Solids())!=1:r['failures'].append('Invalid CAD '+p.name)
    load=lambda n:cq.importers.importStep(str(ROOT/'cad'/(n+'.step'))).val()
    boot=load('rear_magnet_carrier_print_two')
    adapter=load('ear_adapter_W10_R65_print_two')
    placed={
      'left_face':m.ear_place(load('left_face'),'left',.1),
      'right_face':m.ear_place(load('right_face'),'right',.1),
      'left_carrier':m.ear_place(boot,'left',-10),
      'right_carrier':m.ear_place(boot,'right',-10),
      'left_adapter':m.adapter_place(adapter,'left',10),
      'right_adapter':m.adapter_place(adapter,'right',10),
      'eyes':load('tall_eyes').translate((0,0,.1)),
      'eye_adapter':load('eye_adapter_W10_R65').translate((0,0,-10)),
      'band_reference':m.headband_proxy()}
    for a,b in itertools.combinations(placed,2):
        inter=placed[a].intersect(placed[b]).Volume()
        r['assembly_intersections_mm3'][a+' / '+b]=inter
        if inter>.02:r['failures'].append(f'Assembly collision {a}/{b}: {inter:.4f} mm3')
    # Actual nominal magnet envelopes, not only matching hole counts.
    bad=[]
    for name,p in [('carrier',boot),('receiver',adapter)]:
        for a in m.ANGLES:
            u=(math.sin(a),math.cos(a),0)
            if name=='carrier':
                mag=m.cyl(3,3,((m.BACK_R-3)*u[0],m.ARC_CY+(m.BACK_R-3)*u[1],5),u)
            else:mag=m.cyl(3,3,(80.9*u[0],80.9*u[1],5),u)
            if p.intersect(mag).Volume()>.002:bad.append(name+str(a))
    eyes=load('tall_eyes');ea=load('eye_adapter_W10_R65')
    for x in [-7,7]:
        if eyes.intersect(m.cyl(3,3,(x,69.5,.1))).Volume()>.002:bad.append('eyes')
        if ea.intersect(m.cyl(3,3,(x,69.5,6.9))).Volume()>.002:bad.append('eye_adapter')
    r['magnet_fit_interference']=bad
    if bad:r['failures'].append('Magnet interference')
    # Preserve tall eye proportions and true thicker stems, without a low bridge.
    eye_bounds=np.array(r['parts']['tall_eyes']['bounds_mm'])
    r['eye_total_height_mm']=float(eye_bounds[1,1]-eye_bounds[0,1])
    r['stem_width_mm']=m.STALK_WIDTH;r['stem_backing_thickness_mm']=m.EYE_BASE
    if r['eye_total_height_mm']<50:r['failures'].append('Eyes were shortened relative to image target')
    # Color regions must themselves be closed. Multiple islands are intentional.
    r['color_regions']={}
    for prefix in ['left_face','right_face','tall_eyes']:
        total=0
        for p in sorted((ROOT/'stl').glob(prefix+'_*.stl')):
            q=mesh_check(p);r['color_regions'][p.stem]=q;total+=q['volume_mm3']
            if any(q[k] for k in ['boundary_edges','nonmanifold_edges','orientation_errors','degenerate_faces']):r['failures'].append('Bad color mesh '+p.name)
        q=r['parts'][prefix]
        error=abs(total-q['volume_mm3'])
        if error>1:r['failures'].append(f'Color region volume overlap {prefix}: {error}')
    (ROOT/'validation_report.json').write_text(json.dumps(r,indent=2))
    print(json.dumps(r,indent=2));return int(bool(r['failures']))
if __name__=='__main__':sys.exit(run())
