import json,os,shutil,urllib.request
from pathlib import Path
from PIL import Image,ImageOps

parent=Path(os.environ['SORCERER_LITHO_PARENT'])
out=Path(os.environ['SORCERER_LITHO_OUTPUT'])
helper=(parent/'queue-comfyui.py').read_text(encoding='utf-8-sig')
exec(helper.split('\ncommon=',1)[0])
with urllib.request.urlopen(base+'/queue',timeout=8) as f:
    q=json.load(f)
print('ComfyUI queue:',len(q['queue_running']),'running,',len(q['queue_pending']),'pending',flush=True)

for name in ('mickey-hidden-rear-shoe-comfy-master.png','brooms-comfy-master.png','mickey-enamel-reference.png'):
    dst=out/name
    if not dst.exists():
        shutil.copyfile(parent/name,dst)

def reference(source,filename,crop=None,target=None):
    im=Image.open(os.environ[source]).convert('RGB')
    if crop:
        im=im.crop(tuple(round(v*m) for v,m in zip(crop,(*im.size,*im.size))))
    if target:
        im=ImageOps.pad(im,target,Image.Resampling.LANCZOS,color=(28,30,41))
    im.save(out/filename)

reference('SORCERER_NEW_REF','mickey-gloves-belt-pose.png',target=(448,512))
reference('SORCERER_BROOM_REF','broom-hands-and-bristle-legs.png',crop=(.49,0,1,1),target=(288,416))

mickey=(
 'Edit image 1, the approved flat-enamel Sorcerer Mickey ear illustration, as a focused anatomy correction. Use image 2 as the exact gesture and clothing reference; '
 'image 3 is a pin style reference only. Preserve the original cobalt hat and facial expression, navy color field, all surrounding stars, gold rim, large central figure, pose direction and 1024 square framing of image 1. '
 'Replace the raised white glove with the SPECIFIC open hand in image 2: at the end of a short dark wrist above the red raised sleeve, the palm is turned upward and toward the right, '
 'the rounded thumb sticks UP on the left side of the hand shape, and four softly rounded finger tips extend together to the RIGHT above the palm, with a subtle even curve to separate them. '
 'The lowered white glove at the lower left, at the end of the red sleeve, is lightly curled with its fingers pointing down and the thumb against its side, compact like the fist in image 2. '
 'Neither glove resembles a mitten, a flipper or an unconnected blob. Small clean glove cuffs. Both hands keep their positions; draw anatomically readable glove shapes and only a few purposeful, even engraved lines. '
 'Add a clearly visible narrow warm ochre-brown tied fabric BELT with a centered knot and short hanging tails at his natural waist, like image 2. Below the belt the scarlet ROBE SPLITS OPEN in a clear V, '
 'showing a dark charcoal-purple garment between two distinct scarlet coat panels. The two edges of the robe opening have clean fine dark-and-gold contours and the panels flare separately as in image 2. '
 'Show his one visible golden-brown shoe at the lower right. The rear shoe remains hidden by the coat and the rim. Leave the rest of the character composition and stars alone. '
 'Paint flat saturated enamel colors with restrained precise gold edges, no speckles, glows, diffuse shading, extra limbs, extra fingers, letters or annotations.'
)
brooms=(
 'Edit image 1, the approved two-broom Fantasia ear illustration, using the cropped enamel pin in image 2 as the construction reference. '
 'Preserve the exact circular ear outline with the concave bottom, gold rim, solid navy field, gold stars, sizing, arrangement of the two broom figures, four reddish wood buckets with blue water, and warm straw and amber palette of image 1. '
 'Correct ONLY the connecting anatomy and the straw feet of BOTH broom figures. Each broom has two thin curved wooden arms. '
 'At the termination of each arm draw a clearly shaped small four-finger wooden hand, with a rounded thumb and readable fingers closed AROUND a separate raised U-shaped bucket handle. The HANDS GRIP the handles, four hands total. '
 'Leave visible open space inside each handle, between the hand and the lip of the bucket where the slender handle spans. The bucket is hanging from that handle. '
 'The actual wrist or branch ends at the hand and never merges into the bucket rim, water, or staves. The handle is an independent narrow gold-outline element below and through the grasp. '
 'At the bottom of BOTH broom figures, the straw skirt splits into TWO separate bundles like short legs and splayed feet, exactly as the broom pin reference. '
 'Each pair diverges from the tied straw waist and has a deep clearly visible triangular gap of navy between the two legs; bristle tufts flare at each foot and toe. Four separate broom feet total, two per figure. '
 'Keep the clean fine gold outlines and large definite shapes of a printed hard-enamel design. No blurry blended connections, single brush-head skirts, extra pails, extra arms, person, text or framing changes.'
)

ids={}
for name,refs,prompt,seed in (
 ('mickey-gloves-and-belt',['mickey-hidden-rear-shoe-comfy-master.png','mickey-gloves-belt-pose.png','mickey-enamel-reference.png'],mickey,20261122914),
 ('brooms-grips-and-feet',['brooms-comfy-master.png','broom-hands-and-bristle-legs.png'],brooms,20261122961),
):
    g=graph(refs,prompt,seed,name)
    (out/f'{name}-comfyui-api.json').write_text(json.dumps(g,indent=2)+'\n')
    ids[name]=post('/prompt',{'prompt':g,'client_id':session})['prompt_id']
    (out/'comfyui-jobs.json').write_text(json.dumps(ids,indent=2)+'\n')
    print('Queued',name,ids[name],flush=True)
