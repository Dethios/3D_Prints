import json,os,shutil
from pathlib import Path
out=Path(os.environ['SORCERER_LITHO_OUTPUT'])
root=Path(os.environ['SORCERER_LITHO_PARENT'])
code=(root/'queue-comfyui.py').read_text(encoding='utf-8-sig')
exec(code.split('\ncommon=',1)[0])
for n in ('mickey-gloves-and-belt-comfy-master.png','mickey-gloves-belt-pose.png'):
    shutil.copyfile(root/'Anatomy_Revision'/n,out/n)
prompt=(
 'One surgical edit to image 1, the existing Mickey enamel illustration. Preserve the face, hat, eye direction, both glove shapes, wrist cuffs, red split robe, tied belt, all stars, ear framing and the shoe already shown on the lower right. '
 'Add the one MISSING left/rear shoe at the lower LEFT below the red hem, just as the two visible shoes in image 2. '
 'This second shoe is a short rounded golden-brown boot with a broad toe pointing LEFT, secured under the hem. It should emerge naturally from the dark trouser area under the split robe and visibly sit beneath the LEFT coat panel. '
 'The new left shoe is about the same size as the current right shoe, with a smooth thin gold perimeter line and one clean curved sole seam. '
 'Do not change any part of the figure except to draw that missing second shoe in the space immediately below the left robe. The result has exactly TWO visible shoes, two hands, same exact expression and head, same pose. '
 'Keep the original flat enamel pin color treatment and exact 1024-square ear framing.'
)
key='mickey-two-shoes'
g=graph(['mickey-gloves-and-belt-comfy-master.png','mickey-gloves-belt-pose.png'],prompt,20261123201,key)
(out/f'{key}-comfyui-api.json').write_text(json.dumps(g,indent=2)+'\n')
job=post('/prompt',{'prompt':g,'client_id':session})['prompt_id']
(out/'comfyui-mickey-jobs.json').write_text(json.dumps({key:job},indent=2)+'\n')
print('Queued Mickey second shoe:',job)
