from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np
from scipy import ndimage

out=Path(__file__).resolve().parent
ori=Image.open(out/"sticker-art-navy.png").convert("RGB")
a=np.asarray(ori).astype(int)
r,g,b=np.moveaxis(a,-1,0)
white=(r>165)&(g>148)&(b>121)&(r-g<43)&(r-b<70)
labels,_=ndimage.label(white)
magic=np.isin(labels,[1,154,165,166,169])
upper=[(620,276),(648,279),(673,264),(692,233),(712,231),(722,243),(707,272),
       (723,282),(735,303),(734,322),(718,343),(701,355),(682,365),(655,356),(649,323),(624,308)]
lower=[(408,599),(430,579),(479,576),(507,593),(513,613),(502,636),(476,638),(459,629),
       (434,655),(408,676),(387,681),(375,669),(378,645),(394,619)]
gloves=Image.new("L",ori.size)
draw=ImageDraw.Draw(gloves)
for shape in (upper,lower):draw.polygon(shape,fill=255)
hands=np.asarray(gloves)>0
# Save the separated authoring scopes, including a narrow allowance around the source white outline.
preserve=hands&((g-b)<11)
preserve=ndimage.binary_dilation(ndimage.binary_closing(preserve & white,iterations=2),iterations=3)
core=magic&~preserve
removal=ndimage.binary_dilation(core,iterations=3)&~preserve
Image.fromarray(core).save(out/"magic-source-core.png")
Image.fromarray(removal).save(out/"magic-source-matte.png")
Image.fromarray(preserve).save(out/"glove-protection-matte.png")
dbg=np.array(ori)
dbg[removal]=(0.33*dbg[removal]+.67*np.array([69,216,135])).astype(np.uint8)
Image.fromarray(dbg).save(out/"swirl-mask-inspection.png")
