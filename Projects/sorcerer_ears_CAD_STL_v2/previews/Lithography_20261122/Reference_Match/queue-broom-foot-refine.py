import json,os
from pathlib import Path
from PIL import Image, ImageOps
root=Path(os.environ['SORCERER_LITHO_PARENT'])
out=Path(os.environ['SORCERER_LITHO_OUTPUT'])
source=(root/'queue-comfyui.py').read_text(encoding='utf-8-sig')
exec(source.split('\ncommon=',1)[0])
asset=Image.open(out/'compact-broom-candidate-transparent.png').convert('RGBA')
pin=Image.open(out/'exact-broom-pin-cutout.png').convert('RGBA')
size=(896,896)
h=672
w=round(h*.731)
navy=(22,50,99,255)
canvas=Image.new('RGBA',size,navy)
data=asset.resize((w,h),Image.Resampling.LANCZOS)
canvas.alpha_composite(data,((896-w)//2,104))
canvas.convert('RGB').save(out/'broom-widened-edit-guide.png')
ref=Image.new('RGBA',(416,512),navy)
thumb=ImageOps.contain(pin,(380,465),Image.Resampling.LANCZOS)
ref.alpha_composite(thumb,((416-thumb.width)//2,(512-thumb.height)//2))
ref.convert('RGB').save(out/'broom-direct-pin-reference.png')
brief=(
 'Precisely edit image 1, a wide standalone Fantasia enchanted broom, using image 2 as the visual reference for exact shape. '
 'Preserve the width and height of image 1, almost three quarters as wide as tall. Keep the plain navy field and one centered broom. '
 'Specifically change the TWO straw feet below the collar to match image 2: broaden the connected low straw skirt, keep a small smoothly rounded arch between the two feet, '
 'and reshape both toes into short tapering splayed straw sweeps. The LEFT lower toe extends leftward to a soft narrow curl, the RIGHT toe sweeps higher and points outward RIGHT. '
 'Both feet are continuous straw, with fine strands that flow all the way off the toes; there are no oval toe caps, boot soles, hems, cuffs or dividing seams across the straw foot. '
 'Keep the waist collar high, narrow arm wrists and the small golden hands clearly gripping individual gold bucket handles. Tilt the two red buckets slightly OUTWARD as in the pin, left base toward left, right base toward right. '
 'Keep separate little navy holes inside both handles and the wide ivory stripe across each bucket. Solid clean matte enamel colors, crisp outlines, no extra objects or border. '
 'This is a faithful cleanup of the two squat sweeping toes of the reference, not a redesign.'
)
key='pin-broom-swept-feet'
g=graph(['broom-widened-edit-guide.png','broom-direct-pin-reference.png'],brief,20261123488,key)
(out/f'{key}-comfyui-api.json').write_text(json.dumps(g,indent=2)+'\n')
job=post('/prompt',{'prompt':g,'client_id':session})['prompt_id']
(out/'comfyui-refine-jobs.json').write_text(json.dumps({key:job},indent=2)+'\n')
print('Queued widened pin-foot correction',job,flush=True)
