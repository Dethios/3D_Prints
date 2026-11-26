from pathlib import Path
from PIL import Image
from scipy import ndimage
import numpy as np
import json

out = Path(__file__).resolve().parent
im = Image.open(out/"sticker-reference.png").convert("RGB")
positions = [(1088,506),(895,747),(397,952),(508,1098),(1121,858),
             (1151,934),(1154,1195),(1100,1308),(472,1306),(332,1506)]
records=[]
sheet=Image.new("RGBA",(600,210),(28,51,99,255))
for i,(x,y) in enumerate(positions):
    source=im.crop((x-34,y-40,x+34,y+40))
    pix=np.asarray(source).astype(float)
    r,g,b=np.moveaxis(pix,-1,0)
    target=(r>164)&(g>187)&(b>157)&((r-b)<45)
    l,_=ndimage.label(target)
    counts=np.bincount(l.ravel());counts[0]=0
    assert counts.max()>35
    yy,xx=np.indices(l.shape)
    near=(l>0)&(counts[l]>35)
    score=np.where(near,(yy-40)**2+(xx-34)**2,1e8)
    primary=(l==l.flat[score.argmin()])
    assert score.min()<110,(i,x,y,score.min())
    alpha=np.clip((np.minimum(r,g)-150)/70,0,1)*ndimage.binary_dilation(primary,iterations=1)
    shape=Image.new("RGBA",source.size,(249,246,221,0))
    shape.putalpha(Image.fromarray(np.rint(alpha*255).astype(np.uint8)))
    shape=shape.crop(shape.getbbox())
    shape.save(out/f"sticker-star-{i+1:02d}.png")
    records.append({"center_px":[x,y],"size":list(shape.size)})
    sheet.alpha_composite(shape,(25+(i%5)*119,24+(i//5)*95))
(out/"sticker-stars.json").write_text(json.dumps(records,indent=2)+"\n")
sheet.convert("RGB").save(out/"sticker-star-reference-sheet.png")
print(records)
