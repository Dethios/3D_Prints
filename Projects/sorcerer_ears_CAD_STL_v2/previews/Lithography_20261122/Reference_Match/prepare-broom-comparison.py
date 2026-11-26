import json, os
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE=Path(os.environ['NX3_MATCH_ROOT'])
old=HERE.parent
paper='#F7F3E9'
navy=(35,62,114)

def cut_asset(path):
    im=Image.open(path).convert('RGB')
    pix=np.asarray(im).astype(np.int16)
    # All four corners are the plain navy background in the dedicated edit.
    sample=np.concatenate([pix[:45,:45].reshape(-1,3),pix[:45,-45:].reshape(-1,3),
                           pix[-45:,:45].reshape(-1,3),pix[-45:,-45:].reshape(-1,3)])
    background=np.median(sample,axis=0)
    diff=np.linalg.norm(pix-background,axis=2)
    mask=diff>35
    labels,n=ndimage.label(mask)
    counts=np.bincount(labels.ravel());counts[0]=0
    mask=counts[labels]>=100
    assert mask.sum()>40000
    result=im.convert('RGBA')
    result.putalpha(Image.fromarray(mask.astype(np.uint8)*255))
    return result.crop(result.getbbox())

def normal(asset,h):
    return asset.resize((round(asset.width*h/asset.height),h),Image.Resampling.LANCZOS)

def arch_from(mask):
    h,w=mask.shape
    for y in range(round(.64*h),round(.9*h)):
        gaps=[]
        for yy in range(y,y+max(3,round(.010*h))):
            xs=np.where(mask[yy])[0]
            if len(xs)<3:
                continue
            spans=xs[1:]-xs[:-1]
            over=np.where(spans>=round(.065*w))[0]
            if len(over):
                a=max(over,key=lambda k:spans[k])
                if xs[a]-xs[0]>=.10*w and xs[-1]-xs[a+1]>=.10*w:
                    gaps.append(yy)
        if len(gaps)>=max(2,round(.006*h)):
            return round(y/h,3)
    return None

pin=Image.open(HERE/'exact-broom-pin-cutout.png').convert('RGBA')
candidate=cut_asset(HERE/'pin-compact-broom-comfy-master.png')
candidate.save(HERE/'compact-broom-candidate-transparent.png')
ra=np.asarray(pin.getchannel('A'))>120
ca=np.asarray(candidate.getchannel('A'))>120
rel={'reference_width_over_height':round(pin.width/pin.height,3),
     'candidate_width_over_height':round(candidate.width/candidate.height,3),
     'reference_split_y_over_height':arch_from(ra),
     'candidate_split_y_over_height':arch_from(ca)}
print(json.dumps(rel,indent=2))
(HERE/'compact-broom-comparison-metrics.json').write_text(json.dumps(rel,indent=2)+'\n')
page=Image.new('RGBA',(1340,800),(247,244,237,255))
d=ImageDraw.Draw(page)
try:
    from PIL import ImageFont
    f=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',29)
except OSError:
    f=None
for i,(name,im) in enumerate([('Supplied enamel-pin reference',pin),('ComfyUI compact broom candidate',candidate)]):
    left=28+i*670
    d.rounded_rectangle((left,56,left+614,745),radius=14,fill=navy)
    chosen=normal(im,615)
    page.alpha_composite(chosen,(left+(614-chosen.width)//2,96))
    d.text((left+8,17),name,fill='#19293F',font=f)
page.convert('RGB').save(HERE/'broom-pin-candidate-comparison.png')
# The two copies of the same validated pin silhouette retain all body parts.
for title,height,center in [('broom-lower-motif',438,(339,536)),('broom-upper-motif',476,(679,444))]:
    sprite=normal(candidate,height)
    canvas=Image.new('RGBA',(1024,1024))
    canvas.alpha_composite(sprite,(round(center[0]-sprite.width/2),round(center[1]-sprite.height/2)))
    canvas.save(HERE/f'{title}.png')
