import json, math, os
from pathlib import Path
from itertools import product
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
import trimesh

P=Path('Projects/sorcerer_ears_CAD_STL_v2').resolve()
OUT=Path(os.environ['NX3_MOUNTED_OUT'])
PRE=OUT.parent
ANGLES={'brooms':40.,'mickey':-40.}
PX=9.22
T=1024
pad=112
W=T+2*pad
C=W/2
size=(W,W)
navy=(35,62,114)
gold=(220,175,84)
paper=(247,244,237)
poses=json.loads((P/'CAD/assembly_positions.json').read_text())['NX3']
source_inner=Image.open(PRE/'ear-interior-alpha.png').convert('L')
source_outer=Image.open(PRE/'ear-outer-alpha.png').convert('L')
flat_inner=np.asarray(source_inner)>127

def rotate_point(x,y,angle):
    a=math.radians(angle)
    dx,dy=x-512,y-512
    return np.array([C+math.cos(a)*dx+math.sin(a)*dy,C-math.sin(a)*dx+math.cos(a)*dy])

def rotate_mask(image,angle):
    im=Image.new('L',size)
    im.paste(image,(pad,pad))
    return im.rotate(angle,Image.Resampling.BICUBIC,center=(C,C))

def dots(name, file=None):
    im=Image.open(file or PRE/f'{name}-artwork-transparent.png').convert('RGBA')
    alpha=np.asarray(im.getchannel('A'))
    lab,_=ndimage.label(alpha>70)
    area=np.bincount(lab.ravel()); area[0]=0
    output=[]
    for k in np.argsort(area)[::-1]:
        if area[k]<250:
            break
        pick=lab==k
        yy,xx=np.where(pick)
        x0,y0,x1,y1=max(0,xx.min()-3),max(0,yy.min()-3),min(T,xx.max()+4),min(T,yy.max()+4)
        crop=im.crop((x0,y0,x1,y1))
        mask=ndimage.binary_dilation(pick[y0:y1,x0:x1],iterations=2)
        crop.putalpha(Image.fromarray(np.where(mask,alpha[y0:y1,x0:x1],0).astype(np.uint8)))
        edge=pick&~ndimage.binary_erosion(pick,iterations=2)
        ey,ex=np.where(edge)
        outline=np.column_stack((ex,ey))[::3]
        # Interior samples prevent candidates with deep cropped features.
        sample=np.column_stack((xx,yy))[::14]
        output.append({'raw':crop,'xy':np.array([x0,y0]),'outline':outline,'sample':sample,
                       'center':np.array([xx.mean(),yy.mean()]),'area':int(area[k]),
                       'bbox':np.array([xx.min(),yy.min(),xx.max(),yy.max()])})
    return output

def pinned_asset(path):
    image=Image.open(path).convert('RGBA')
    alpha=np.asarray(image.getchannel('A'))
    pick=alpha>90
    yy,xx=np.where(pick)
    x0,y0,x1,y1=max(0,xx.min()-3),max(0,yy.min()-3),min(T,xx.max()+4),min(T,yy.max()+4)
    edge=pick&~ndimage.binary_erosion(pick,iterations=2)
    ey,ex=np.where(edge)
    return {'raw':image.crop((x0,y0,x1,y1)), 'xy':np.array([x0,y0]),
            'outline':np.column_stack((ex,ey))[::3], 'sample':np.column_stack((xx,yy))[::14],
            'center':np.array([xx.mean(),yy.mean()]), 'area':int(len(xx)),
            'bbox':np.array([xx.min(),yy.min(),xx.max(),yy.max()])}

def shoe_samples(area,art):
    p=(area-art['xy']).astype(int)
    vals=np.asarray(art['raw']).astype(np.int16)[p[:,1],p[:,0],:3]
    r,g,b=vals.T
    x0,y0,x1,y1=art['bbox']
    base=(area[:,1]>y0+.874*(y1-y0))&(r>100)&(r>g+24)&(g>b+20)&(g>54)
    mid=x0+.43*(x1-x0)
    return [base&(area[:,0]<mid),base&(area[:,0]>=mid)]

def mask_hit(grid,p):
    v=np.round(p).astype(int)
    valid=np.all((v>=0)&(v<W),axis=1)
    hit=np.zeros(len(v),dtype=bool)
    hit[valid]=grid[v[valid,1],v[valid,0]]
    return hit

def extent_points(xs, angle,depth):
    for x in xs:
        y=int(np.where(flat_inner[:,x])[0][-1])
        yield x, rotate_point(x,y+depth,angle)

def is_protected(source,name,art):
    bbox=art['bbox']
    x0,y0,x1,y1=bbox
    h=y1-y0
    if name=='mickey':
        # Keep the gloves, face, belt and visible forward shoe clear.
        return (source[:,1] < y0+.83*h)|((source[:,0]>x0+.55*(x1-x0))&(source[:,1]>y0+.895*h))
    # Keep both broom legs readable; clipping is limited to the bottom fringe.
    return source[:,1] < y0+.87*h

def relative_anchor(art,name):
    x0,y0,x1,y1=art['bbox']
    if name=='mickey':
        gx=x0+.24*(x1-x0)
        outline=art['outline']
        local=outline[np.abs(outline[:,0]-gx)<max(14,(x1-x0)*.06)]
        ly=np.max(local[:,1]) if len(local) else y1-(y1-y0)*.08
        return np.array([gx,ly])
    fringe=art['outline'][art['outline'][:,1] >= y1-11]
    gx=float(np.median(fringe[:,0])) if len(fringe) else (x0+x1)*.5
    return np.array([gx,y1-5.])

def turning(degrees):
    rad=math.radians(degrees)
    return np.array([[math.cos(rad),-math.sin(rad)],[math.sin(rad),math.cos(rad)]])

def candidates(art,anchor,angle,mask,xrange,preferred,preferred_scale,name,tilt=0.):
    boundary=art['outline']
    area=art['sample']
    bad_protect=is_protected(area,name,art)
    protected_edge=is_protected(boundary,name,art)
    shoes=shoe_samples(area,art) if name=='mickey' else []
    if shoes and min(v.sum() for v in shoes)<25:
        raise RuntimeError('New Mickey asset does not contain two detectable gold shoes')
    choices=[]
    for s in np.arange(preferred_scale, .62, -.025):
        q=(area-anchor)@turning(tilt)*s
        edge=(boundary-anchor)@turning(tilt)*s
        for depth in ((-12,-8,-4,0,4,8,12,16,20) if name=='mickey' else (8,12,16,20)):
            for x,anchor_to in extent_points(xrange,angle,depth):
                hit=mask_hit(mask,q+anchor_to)
                if hit[bad_protect].mean() < .997:
                    continue
                footprints=[float(hit[v].mean()) for v in shoes]
                if shoes and (footprints[0]<.84 or footprints[1]<.95):
                    continue
                cut=(~hit).mean()
                if not ((.00025 if name=='mickey' else .0015)<cut<.072):
                    continue
                e_hit=mask_hit(mask,edge+anchor_to)
                if e_hit[protected_edge].mean()<.993:
                    continue
                score=(preferred_scale-s)*6+.0017*abs(x-preferred)+abs(cut-.024)*4+.0015*abs(depth-15)
                minimum=edge.min(axis=0)+anchor_to
                maximum=edge.max(axis=0)+anchor_to
                choices.append({'scale':float(s),'anchor':anchor,'target':anchor_to,'rim_x':x,
                                'cut_fraction':float(cut),'rank':float(score),'lo':minimum,'hi':maximum,'tilt':tilt,'both_shoes_kept':footprints})
    return sorted(choices,key=lambda item:item['rank'])

def stamp(art,item):
    tilt=item.get('tilt',0.)
    s=item['scale']
    inverse=np.linalg.inv(turning(tilt).T*s)
    offset=item['anchor']-inverse@item['target']-art['xy']
    matrix=(inverse[0,0],inverse[0,1],offset[0],inverse[1,0],inverse[1,1],offset[1])
    return art['raw'].transform(size,Image.Transform.AFFINE,matrix,Image.Resampling.BICUBIC)

def clip(image,mask):
    actual=np.asarray(image.getchannel('A')).astype(np.uint16)
    crop=np.asarray(mask).astype(np.uint16)
    image.putalpha(Image.fromarray(((actual*crop+127)//255).astype(np.uint8)))
    return image

def solid_canvas(mask,color):
    im=Image.new('RGBA',mask.size,(*color,0))
    im.putalpha(mask)
    return im

def stars_on_mount(art,occupied,stars,inner):
    from scipy.ndimage import distance_transform_edt
    result=Image.new('RGBA',size)
    used=np.asarray(occupied.getchannel('A'))>65
    open_mask=ndimage.binary_erosion(inner,iterations=14)
    shifts=sorted((dx*dx+dy*dy,dx,dy) for dx in range(-156,157,12) for dy in range(-156,157,12))
    kept=0
    for star in stars:
        preferred=star['center']+pad
        free=open_mask & (distance_transform_edt(~used)>16)
        found=None
        for _,dx,dy in shifts:
            try_pos=preferred+[dx,dy]
            for s in (1.0,.91,.82):
                projected=(star['outline']-star['center'])*s+try_pos
                if mask_hit(free,projected).all():
                    found={'scale':s,'anchor':star['center'],'target':try_pos}
                    break
            if found:
                break
        if not found:
            continue
        layer=stamp(star,found)
        result.alpha_composite(layer)
        used=used | (np.asarray(layer.getchannel('A'))>65)
        kept+=1
    return result,kept

def bbox_overlap(a,b):
    return np.all(a['lo']<b['hi']+11)&np.all(b['lo']<a['hi']+11)

def placement(art,pose):
    return (art['sample']-pose['anchor'])@turning(pose.get('tilt',0.))*pose['scale']+pose['target']

mounted={}
details={}
for side,angle in ANGLES.items():
    array=dots(side) if side=="mickey" else []
    imask=rotate_mask(source_inner,angle)
    omask=rotate_mask(source_outer,angle)
    grid=np.asarray(imask)>136
    if side=='mickey':
        items=[array[0]]
        choices=candidates(items[0],relative_anchor(items[0],'mickey'),angle,grid,range(350,761,3),573,1.04,'mickey')
        if not choices: raise RuntimeError('Mickey anchor did not fit')
        pick=[choices[0]]
        stars=array[1:]
    else:
        leaning=pinned_asset(PRE/'broom-lower-motif.png')
        upright=pinned_asset(PRE/'broom-upper-motif.png')
        items=[leaning,upright]
        left=candidates(leaning,relative_anchor(leaning,'broom'),angle,grid,range(243,471,5),364,1.035,'broom-leaning',tilt=16.)
        left+=candidates(leaning,relative_anchor(leaning,'broom'),angle,grid,range(243,471,5),364,1.035,'broom-leaning',tilt=23.)
        left.sort(key=lambda z:z['rank'])
        right=candidates(upright,relative_anchor(upright,'broom'),angle,grid,range(510,766,5),650,1.03,'broom-upright')
        print('broom candidate counts',len(left),len(right),flush=True)
        print('left ranges',[(min(z[k] for z in left),max(z[k] for z in left)) for k in ('scale','rim_x')],flush=True)
        print('right ranges',[(min(z[k] for z in right),max(z[k] for z in right)) for k in ('scale','rim_x')],flush=True)
        pick=None
        best=999.
        halos={}
        for a,b in product(left[:350],right):
            score=a['rank']+b['rank']+abs(a['scale']-b['scale'])*2.8
            if score>=best:
                continue
            if bbox_overlap(a,b):
                # Reject overlapping and almost-touching foreground silhouettes.
                if id(a) not in halos:
                    zero=np.zeros(size,dtype=bool)
                    pts=np.rint(placement(leaning,a)).astype(int)
                    valid=np.all((pts>=0)&(pts<W),axis=1)
                    pts=pts[valid]
                    zero[pts[:,1],pts[:,0]]=True
                    halos[id(a)]=ndimage.binary_dilation(zero,iterations=9)
                halo=halos[id(a)]
                if mask_hit(halo,placement(upright,b)).any():
                    continue
            best=score
            pick=[a,b]
        if not pick:
            raise RuntimeError('Two anchored brooms do not fit with this spacing')
        stars=dots(side,PRE.parent/'brooms-artwork-transparent.png')[2:]
    scene=Image.new('RGBA',size)
    collar=np.asarray(imask)>200
    outside_ring=ndimage.binary_dilation(collar,iterations=2)&~collar
    checks=[]
    for art,item in zip(items,pick):
        image=stamp(art,item)
        aa=np.asarray(image.getchannel('A'))
        contact=int(np.sum((aa>100)&outside_ring))
        assert contact>(8 if side=='mickey' else 22),(side,contact)
        checks.append({'art_scale':round(item['scale'],3),'rim_x_in_flat_pixels':item['rim_x'],
                       'graphic_tilt_deg':item.get('tilt',0.),'rim_contact_samples':contact,'occluded_sample_ratio':round(item['cut_fraction'],4), 'shoe_retention':item['both_shoes_kept']})
        scene.alpha_composite(clip(image,imask))
    star_layer,kept=stars_on_mount(array,scene,stars,grid)
    scene.alpha_composite(star_layer)
    # Convert from the viewer-facing mounted coordinate space back to the
    # individual ear's flat fabrication coordinate space before exporting.
    flat=scene.rotate(-angle,Image.Resampling.BICUBIC,center=(C,C))
    flat=flat.crop((pad,pad,pad+T,pad+T))
    flat=clip(flat,source_inner)
    assert not np.any(np.asarray(flat.getchannel('A'))[~flat_inner])
    flat.save(OUT/f'{side}-mounted-layout-artwork-transparent.png')
    l=solid_canvas(source_inner,navy)
    l.alpha_composite(flat)
    l.putalpha(source_inner)
    l.save(OUT/f'{side}-mounted-layout-lithography.png')
    e=solid_canvas(source_outer,gold)
    e.alpha_composite(l)
    e.save(OUT/f'{side}-flat-ear-preview.png')
    mounted[side]=e
    details[side]={'mount_angle_deg':angle,'print_counter_rotation_deg':-angle,'main_art':checks,
                   'stars':kept,'input_stars':len(stars),'art_clear_of_outer_rim':True}
    print(side,details[side],flush=True)

# Project the actual larger NX3 band and apply the recorded 3D assembly poses
# as a common orthographic front-view transform.
SS=7.25
canvas=(1810,1280)
WX,WY=905.,1030.
paper_full=Image.new('RGBA',canvas,(*paper,255))
mesh=trimesh.load_mesh(P/'Reference_files/dressyspider_larger_headband_source.stl')
d=ImageDraw.Draw(paper_full)
for t in mesh.triangles:
    d.polygon([(WX+SS*x,WY-SS*y) for x,y in t[:,:2]],fill='#222633')
for side,key in [('brooms','left_brooms'),('mickey','right_mouse')]:
    pose=np.asarray(poses[key])
    R=pose[:2,:2]
    w=pose[:2,3]
    # Destination screen pixel -> world millimeters -> local ear -> flat artwork pixel.
    w_linear=np.array([[1/SS,0],[0,-1/SS]])
    w_offset=np.array([-WX/SS,WY/SS])
    pix_linear=np.diag([PX,-PX])
    aff=pix_linear@R.T@w_linear
    offset=pix_linear@R.T@(w_offset-w)+[512,917]
    xform=(aff[0,0],aff[0,1],offset[0],aff[1,0],aff[1,1],offset[1])
    cover=mounted[side].transform(canvas,Image.Transform.AFFINE,xform,Image.Resampling.BICUBIC)
    paper_full.alpha_composite(cover)
paper_full.convert('RGB').save(OUT/'nx3-anchored-headband-preview.png')
(OUT/'mount-fit-verification.json').write_text(json.dumps(details,indent=2)+'\n')


