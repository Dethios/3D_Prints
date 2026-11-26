import json,os,urllib.request,urllib.parse,uuid
from pathlib import Path
out=Path(os.environ['SORCERER_LITHO_OUTPUT'])
base='http://127.0.0.1:8188'
session='nx3-litho-'+uuid.uuid4().hex[:10]
def post(route,data,content_type='application/json'):
    if not isinstance(data,bytes):
        data=json.dumps(data).encode()
    req=urllib.request.Request(base+route,data,{'Content-Type':content_type})
    try:
        with urllib.request.urlopen(req,timeout=25) as response:
            return json.load(response)
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode('utf-8','replace')) from e
def upload(name):
    boundary=uuid.uuid4().hex.encode()
    image=out/name
    def text_field(key,val):
        return b'--'+boundary+b'\r\nContent-Disposition: form-data; name="'+key+b'"\r\n\r\n'+val+b'\r\n'
    file_header=b'--'+boundary+b'\r\nContent-Disposition: form-data; name="image"; filename="'+image.name.encode()+b'"\r\nContent-Type: image/png\r\n\r\n'
    p=post('/upload/image',text_field(b'type',b'input')+text_field(b'subfolder',session.encode())+file_header+
           image.read_bytes()+b'\r\n--'+boundary+b'--\r\n','multipart/form-data; boundary='+boundary.decode())
    return '/'.join(filter(None,[p['subfolder'],p['name']]))
def node(cls,**kw):
    return {'class_type':cls,'inputs':kw}
def graph(names, prompt,seed,kind):
    g={
        '1':node('UNETLoader',unet_name='qwen_image_2.1_bf16.safetensors',weight_dtype='default'),
        '2':node('CLIPLoader',clip_name='qwen3vl_8b_bf16.safetensors',type='qwen_image',device='default'),
        '3':node('VAELoader',vae_name='qwen_image_2.1_vae_bf16.safetensors'),
        '4':node('QwenImage21Cache',model=['1',0],device='auto',dtype='default'),
    }
    condition={}
    for number,name in enumerate(names,1):
        i=str(number+4)
        g[i]=node('LoadImage',image=upload(name))
        condition[f'images.image_{number}']=[i,0]
    g.update({
        '10':node('TextEncodeQwenImage21',clip=['2',0],vae=['3',0],resolution=0,
                  prompt=prompt,negative_prompt='',**condition),
        '11':node('KSampler',model=['4',0],seed=seed,steps=40,cfg=1.0,sampler_name='euler',scheduler='simple',
                  denoise=1.0,positive=['10',0],negative=['10',1],latent_image=['10',2]),
        '12':node('VAEDecode',samples=['11',0],vae=['3',0]),
        '13':node('SaveImage',images=['12',0],filename_prefix=f'{session}/{kind}'),
    })
    return g
common=('Produce a polished FRONT VIEW, flat color-lithography master like an enamel pin illustrated as vector art. '
        'Keep the ear-shaped outside contour and bottom inward curve from image 1, at its exact position and scale. '
        'Thin even antique-gold outer rim, solid dark royal navy field, warm off-white outside. '
        'Stay comfortably inside the inner gold rim with about 1.5 mm of navy between any design and the rim. '
        'Use a compact composition that fills the upper and side areas with 6-8 broad, clearly spaced pale-gold twinkling stars sized to the gaps. '
        'Cover the available space through placement, not extra outlines. Crisp uniform dark outlines and restrained fine gold borders between large matte color areas. '
        'Use a small fixed palette of navy, cobalt blue, red, ivory, muted warm peach, golden brown and gold. '
        'Solid untextured fills suitable for conversion to a layered color image. No lettering, shadows, gleam, metallic reflections, gradients, stray marks, narrow wisps, or shapes beyond the rim.')
mickey=('Image 1 gives the exact ear frame and the layout silhouette. Image 2 shows the required character pose and anatomy. '
        'Image 3 gives the enamel pin outlines and coloring style. Paint a single recognizable Sorcerer Mickey, compact and well proportioned, '
        'humane rounded peach cheek and muzzle, two correctly aligned white eyes looking toward his lifted glove, round black ears and nose, cheerful restrained smile. '
        'His vivid cobalt sorcerer hat points upper left with a separate wrapped blue brim and white moon and stars. His right arm reaches up-right with a clearly recognizable white glove '
        'with thumb and fingers, and his lowered left white glove projects left from a red sleeve with its cuff and fingers clear. Both hands are anatomically clean with at most two smooth thin interior finger lines. '
        'Rich scarlet robe flows toward the lower right with only a few intentional seams. Visible shoe rounded golden brown with one clean curved sole seam and the back foot hidden behind the robe near the lower rim. '
        'Match the pose and figure direction from image 2, not the other pose in the pin. Enlarge the good figure within the field and design the stars around the figure; '
        'keep every glove, cap and shoe inside the frame. No other figure or object. ')+common
broom=('Image 1 gives the exact ear frame, two diagonally arranged broom silhouettes and spacing. Image 2 is for how real broom, bucket and straw details should read in flat enamel art. '
       'Design TWO Fantasia enchanted brooms, each clearly carrying TWO pails, four pails total, in the pose and orientation of image 1. '
       'The upper broom is on the right, the lower broom at left; make both large and prominent. Each has a thick warm wood handle, well-defined curved yoke and connected bucket handles, '
       'bright warm straw bristles tapering to a sweeping skirt and four discrete red-brown pails with pale gold horizontal bands and blue water at their openings. '
       'Give each broom recognizable bristle groups and enough width between its elements to keep the outline readable. All handles join to their appropriate pails. '
       'Use ecru and gold stars in the otherwise open areas to balance both brooms. Extract only broom style from image 2, no Mickey on this side. ')+common
results={}
for kind,refs,prompt,seed in [
    ('mickey',['mickey-true-ear-layout.png','mickey-pose-reference.png','mickey-enamel-reference.png'],mickey,20261122123),
    ('brooms',['brooms-true-ear-layout.png','broom-enamel-reference.png'],broom,20261122456)
]:
    g=graph(refs,prompt,seed,kind)
    (out/f'{kind}-comfyui-api.json').write_text(json.dumps(g,indent=2)+'\n')
    reply=post('/prompt',{'prompt':g,'client_id':session})
    results[kind]=reply['prompt_id']
    (out/'comfyui-jobs.json').write_text(json.dumps(results,indent=2)+'\n')
    print('Queued',kind,reply['prompt_id'],flush=True)
