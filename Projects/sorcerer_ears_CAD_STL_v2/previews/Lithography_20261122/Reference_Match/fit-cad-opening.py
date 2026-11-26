import json, os, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

root=Path(os.environ['SORCERER_LITHO_OUTPUT'])
inner=Image.open(root/'ear-interior-alpha.png').convert('L')
outer=Image.open(root/'ear-outer-alpha.png').convert('L')
safe=np.asarray(Image.open(root/'ear-content-safe-alpha.png').convert('L'))>127
size=inner.size
reference=np.asarray(inner)>127
py,px=np.where(reference)
target_bounds=np.array([px.min(),py.min(),px.max(),py.max()])
target_center=(target_bounds[:2]+target_bounds[2:])/2
target_spans=target_bounds[2:]-target_bounds[:2]
navy=(35,62,114)
gold=(220,175,84)

def largest(mask):
    lab,n=ndimage.label(mask)
    votes=np.bincount(lab.ravel())
    votes[0]=0
    assert n and votes.max()>10000
    return lab==votes.argmax()

def extract(name, source):
    img=Image.open(source).convert('RGB')
    values=np.asarray(img).astype(np.int16)
    r,g,b=np.moveaxis(values,-1,0)
    blue=(r<100)&(g>=r+6)&(b>=r+35)&(b>65)
    main=largest(blue)
    field=ndimage.binary_fill_holes(main)
    y,x=np.where(field)
    bbox=np.array([x.min(),y.min(),x.max(),y.max()])
    position=(bbox[:2]+bbox[2:])/2
    source_spans=bbox[2:]-bbox[:2]
    base_scale=min(target_spans/source_spans)
    color=np.median(values[main],axis=0)
    delta=np.linalg.norm(values-color,axis=2)
    foreground=field & (delta>25)
    # Discard any isolated raster specks while preserving the linework and stars.
    lbl,no=ndimage.label(foreground)
    amount=np.bincount(lbl.ravel())
    amount[0]=0
    art=amount[lbl]>=65
    edges=art&~ndimage.binary_erosion(art,iterations=2)
    yy,xx=np.where(edges)
    candidates=np.column_stack((xx,yy))
    chosen=None
    for factor in np.arange(1.0,.7499,-.005):
        scale=base_scale*factor
        placed=(candidates-position)*scale
        for dx,dy in ((0,0),(0,-5),(0,-10),(0,-15),(0,-20),(0,-25),(0,-30),(0,-35),(0,-40),(5,-10),(-5,-10)):
            center=target_center+[dx,dy]
            fit=np.round(placed+center).astype(int)
            x,y=fit.T
            valid=(x>=0)&(x<size[0])&(y>=0)&(y<size[1])
            if np.all(valid) and np.all(safe[y,x]):
                chosen=(scale,center)
                break
        if chosen:
            break
    assert chosen, (name,'art could not be fitted')
    scale, center=chosen
    ox,oy=position-center/scale
    transform=(1/scale,0,ox,0,1/scale,oy)
    src=img.convert('RGBA')
    src.putalpha(Image.fromarray(art.astype(np.uint8)*255))
    image=src.transform(size,Image.Transform.AFFINE,transform,Image.Resampling.BICUBIC)
    alpha=np.asarray(image.getchannel('A'))
    assert np.sum((alpha>117)&~safe)<=3
    image.putalpha(Image.fromarray(np.where(safe,alpha,0).astype(np.uint8)))
    fig=Image.new('RGBA',size,(*navy,0))
    fig.putalpha(inner)
    fig.alpha_composite(image)
    # Keep every output outside the original opening transparent irrespective
    # of the framing ComfyUI drew; the exact rim is a separate preview only.
    fig.putalpha(inner)
    frame=Image.new('RGBA',size,(*gold,0))
    frame.putalpha(outer)
    frame.alpha_composite(fig)
    image.save(root/f'{name}-artwork-transparent.png')
    fig.save(root/f'{name}-lithography.png')
    frame.save(root/f'{name}-fitted-preview.png')
    paper=Image.new('RGBA',size,(247,245,239,255))
    paper.alpha_composite(frame)
    paper.convert('RGB').save(root/f'{name}-review-on-paper.png')
    return {'source':source.name,'rescale':round(scale,4),'art_pixels':int((alpha>117).sum()),
            'opening_fill_percent':round(100*float((alpha>117).sum())/float(reference.sum()),2),
            'pixels_above_46_percent_alpha_outside_lip_clearance':int(np.sum((alpha>117)&~safe))}

usage=[('mickey','mickey-two-shoes-comfy-master.png'),('brooms','brooms-separated-grips-legs-source.png')]
if len(sys.argv)>1 and sys.argv[1] in ('mickey','brooms'):
    usage=[(key,src) for key,src in usage if key==sys.argv[1]]
report={}
for name,src in usage:
    report[name]=extract(name,root/src)
if len(usage)==2:
    page=Image.new('RGBA',(2030,1024),(247,245,239,255))
    for i,name in enumerate(('brooms','mickey')):
        x=-5 if i==0 else 1012
        page.alpha_composite(Image.open(root/f'{name}-fitted-preview.png'),(x,0))
    page.convert('RGB').save(root/'sorcerer-lithography-pair.png')
    (root/'fit-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))


