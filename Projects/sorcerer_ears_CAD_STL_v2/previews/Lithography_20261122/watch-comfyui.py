import json, os,time,urllib.request,urllib.parse
from pathlib import Path
out=Path(os.environ['SORCERER_LITHO_OUTPUT'])
ids=json.loads((out/'comfyui-jobs.json').read_text())
base='http://127.0.0.1:8188'
def get(p):
    with urllib.request.urlopen(base+p,timeout=12) as r:
        return json.load(r)
deadline=time.monotonic()+840
done={}
last=None
while time.monotonic()<deadline and len(done)<len(ids):
    states=[]
    for name,id in ids.items():
        if name in done:
            continue
        h=get('/history/'+id).get(id)
        if not h:
            continue
        status=h.get('status',{})
        if status.get('status_str')=='error':
            print(name,'error',[(k,v.get('exception_message','')) for k,v in status.get('messages',[]) if k=='execution_error'],flush=True)
            done[name]='error'
            continue
        vals=[image for node in h.get('outputs',{}).values() for image in node.get('images',[])]
        if status.get('completed') and vals:
            query=urllib.parse.urlencode({k:vals[0][k] for k in ('filename','subfolder','type')})
            with urllib.request.urlopen(base+'/view?'+query,timeout=18) as f:
                data=f.read()
            dest=out/f'{name}-comfy-master.png'
            dest.write_bytes(data)
            print(name,'finished',dest,len(data),flush=True)
            done[name]='success'
    q=get('/queue')
    current=([[k, v[1]] for k in ('queue_running','queue_pending') for v in q[k] if v[1] in ids.values()],done.copy())
    if current!=last:
        print('Queue:',current,flush=True)
        last=current
    if len(done)<len(ids):
        time.sleep(5)
(out/'comfyui-results.json').write_text(json.dumps(done,indent=2)+'\n')
if set(done.values())!={'success'} or len(done)!=len(ids):
    raise SystemExit(1)
