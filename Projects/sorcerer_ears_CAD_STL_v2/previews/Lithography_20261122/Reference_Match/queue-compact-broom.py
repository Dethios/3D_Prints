import json,os
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from scipy import ndimage
out=Path(os.environ['SORCERER_LITHO_OUTPUT'])
root=Path(os.environ['SORCERER_LITHO_PARENT'])
code=(root/'queue-comfyui.py').read_text(encoding='utf-8-sig')
exec(code.split('\ncommon=',1)[0])
pin=Image.open(os.environ['SORCERER_BROOM_PIN']).convert('RGB')
assert pin.width==352 and 230<pin.height<252,pin.size
mask=Image.new('L',pin.size)
ImageDraw.Draw(mask).polygon([
 (207,99),(215,89),(226,77),(235,56),(252,54),(263,57),
 (266,26),(276,12),(289,12),(299,19),(299,51),(317,48),
 (321,85),(328,102),(342,113),(342,142),(338,154),(345,173),
 (352,176),(352,192),(331,196),(301,196),(283,208),(263,218),
 (220,218),(212,210),(213,184),(224,165),(239,148),(211,153),(204,140)
],fill=255)
pixels=np.asarray(pin).astype(np.int16)
lum=pixels.max(axis=2)
scope=np.asarray(mask)>127
candidate=scope&(lum>70)
lab,num=ndimage.label(candidate)
areas=np.bincount(lab.ravel());areas[0]=0
selected=lab==areas.argmax()
selected=ndimage.binary_dilation(selected,iterations=1)&scope
selected=ndimage.binary_fill_holes(selected)&scope
assert selected.sum()>7500
alpha=np.clip((lum-37)*5.0,0,255).astype(np.uint8)
alpha=np.where(selected,alpha,0).astype(np.uint8)
cut=pin.convert('RGBA')
cut.putalpha(Image.fromarray(alpha))
cropped=cut.crop(cut.getbbox())
cropped.save(out/'exact-broom-pin-cutout.png')
dim=896
factor=650/cropped.height
large=cropped.resize((round(cropped.width*factor),650),Image.Resampling.LANCZOS)
back=Image.new('RGBA',(dim,dim),(22,50,99,255))
back.alpha_composite(large,((dim-large.width)//2,120))
back.convert('RGB').save(out/'exact-broom-pin-contour-guide.png')
prompt=(
 'Make a meticulous enlarged flat enamel illustration traced from image 1, a close isolated photograph of one specific enchanted broom pin. '
 'Keep the SAME outline, same posture, same arm angles, same short broad proportions, same leg silhouette and color placement of that broom. '
 'One broom only, total, centrally set against the plain uniform deep navy background as shown. Do not redesign or elongate the shape. '
 'The total silhouette is broad, about 72 percent as wide as it is high. The bent angular thin arms branch at roughly one quarter of the full height from its handle tip. '
 'The straight amber neck reaches an ample straw waist slightly above midheight. Both compact wooden mittens hold separate small arched bucket handles close to the bucket rims; visible navy openings inside the handles, two red buckets total, with one wide warm ivory stripe on each. '
 'The buckets tilt outward to either side and their bottoms reach into the top third of the straw skirt, as shown. '
 'The straw is one broad continuous bell-shaped waist and skirt that splits late into two SHORT, WIDE splayed feet through a small smoothly rounded central U-shaped arch. '
 'The arch starts at around 78 percent of full height, NOT up at the waist. The two feet have different poses: left foot sweeps lower to the left with a rounded curled toe, right foot lifts slightly higher and sweeps right. '
 'Carefully match the two broad foot silhouettes in the actual reference. Avoid long spindly separated legs, a deep V divide, a narrow waist or giant human gloves. '
 'Treat it as high-resolution enamel color master art, with solid warm amber wood, light golden straw, red and cream buckets and restrained gold edges. '
 'Clean crisp closed smooth outline. Plain solid navy background with no stars, labels, prop artifacts or original photography texture. Preserve the image size and position.'
)
key='pin-compact-broom'
g=graph(['exact-broom-pin-contour-guide.png'],prompt,20261123277,key)
(out/f'{key}-comfyui-api.json').write_text(json.dumps(g,indent=2)+'\n')
job=post('/prompt',{'prompt':g,'client_id':session})['prompt_id']
(out/'comfyui-broom-jobs.json').write_text(json.dumps({key:job},indent=2)+'\n')
print('Queued direct broom pin trace:',job,flush=True)
