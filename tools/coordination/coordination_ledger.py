"""Single-coordinator local ledger; not a native spawn interceptor or sandbox."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import subprocess
import tempfile
import time
import uuid

class LedgerError(ValueError):
    pass

STATES = {'ready','running','awaiting_review','verified','blocked','failed','cancelled'}
EXCLUDED = {'.git','.ssh','.aws','.azure','node_modules','.venv','__pycache__','sessions','logs'}
LEDGER_DIR = '.coordination'
LEGACY_LEDGER_DIR = '.codex/coordination'
SECRET_FILES = {'.env','auth.json','credentials','credentials.json','id_rsa','id_ed25519'}
SECRET = re.compile(r'(?i)((?<![a-z0-9_])sk-(?:proj-|svcacct-)?[a-z0-9_-]{16,}|\bBearer\s+[a-z0-9._~+/-]{16,}|--(?:api-key|password|access-token)\b)')
IDENT = re.compile(r'^[A-Za-z][A-Za-z0-9_.-]{0,79}$')

def require(ok, message):
    if not ok:
        raise LedgerError(message)

def integer(value, name, low=0, high=None):
    require(type(value) is int and value >= low and (high is None or value <= high), 'invalid '+name)
    return value

def text(value, name):
    require(isinstance(value,str) and bool(value.strip()) and not SECRET.search(value), 'invalid/credential-bearing '+name)
    return value.strip()

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def file_digest(path):
    """Hash all bytes with bounded memory, including large visual assets."""
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            value.update(chunk)
    return value.hexdigest()

def fingerprint(value):
    return digest(json.dumps(value,sort_keys=True,separators=(',',':')).encode())

def git(root,*args):
    result = subprocess.run(['git','-C',str(root),*args],capture_output=True,timeout=20)
    require(result.returncode == 0,'Git inspection failed; preserve files and reconcile access')
    output = result.stdout.decode('utf-8',errors='surrogateescape')
    return output if '-z' in args else output.strip()

def inside(root,relative):
    text(relative,'relative path')
    raw = relative.replace('\\','/')
    require(not PureWindowsPath(raw).drive and not raw.startswith('/') and '..' not in raw.split('/'),'path escapes project')
    require(not any(char in raw for char in ['*','?','\x00']),'scopes must be literal paths')
    target = (root/raw).resolve()
    require(target.is_relative_to(root),'symlink/junction escapes project')
    return target

def paths(root,values):
    require(isinstance(values,list),'scope must be a list')
    return sorted({inside(root,v).relative_to(root).as_posix() or '.' for v in values})

def covers(scopes,path):
    key = path.replace('\\','/').casefold().rstrip('/')
    return any(s == '.' or key == s.casefold().rstrip('/') or key.startswith(s.casefold().rstrip('/')+'/') for s in scopes)

def overlap(a,b):
    return any(covers(a,p) for p in b) or any(covers(b,p) for p in a)

def excluded(name):
    relative = name.replace('\\','/').casefold()
    parts = Path(relative).parts
    return (any(p.casefold() in EXCLUDED for p in parts)
            or any(p.casefold() in SECRET_FILES or p.casefold().startswith('.env.') for p in parts)
            or any(relative == directory or relative.startswith(directory + '/')
                   for directory in (LEDGER_DIR, LEGACY_LEDGER_DIR)))

def snapshot(root):
    root = Path(root).resolve()
    try:
        gitroot = Path(git(root,'rev-parse','--show-toplevel')).resolve()
    except (LedgerError,FileNotFoundError):
        gitroot = None
    if gitroot is not None:
        require(gitroot == root,'ledger root must be actual Git project root')
        names = git(root,'ls-files','-c','-o','--exclude-standard','-z').split('\x00')
        head = git(root,'rev-parse','HEAD')
        dirty = git(root,'diff','--name-only','-z','HEAD','--').split('\x00')
        dirty += git(root,'ls-files','--others','--exclude-standard','-z').split('\x00')
    else:
        names = []
        for parent,dirs,files in os.walk(root):
            dirs[:] = [d for d in dirs if d.casefold() not in EXCLUDED and not (Path(parent)/d).is_symlink()]
            names.extend((Path(parent)/f).relative_to(root).as_posix() for f in files)
        head,dirty = None,[]
    names = sorted({n for n in names if n and not excluded(n)})
    require(len(names) <= 10000,'snapshot file budget exceeded')
    files = {}
    for name in names:
        p = inside(root,name)
        if p.is_file():
            files[name] = file_digest(p)
        elif not p.exists():
            files[name] = None
    return {'root':str(root),'head':head,'files':files,'dirty_paths':sorted({n for n in dirty if n and not excluded(n)})}

def scoped(task):
    root = Path(task['execution_root'])
    current = snapshot(root)
    scopes = task['write_scope']+task['input_scope']+task.get('artifact_paths',[])
    files = {n:h for n,h in current['files'].items() if covers(scopes,n)}
    for scope in scopes:
        p = inside(root,scope)
        if p.is_file() and not excluded(scope):
            files[scope] = file_digest(p)
    return {'root':str(root),'head':current['head'],'files':files}

def dag(data):
    visiting,visited = set(),set()
    def visit(name):
        require(name not in visiting,'cyclic dependencies')
        if name in visited:
            return
        visiting.add(name)
        deps = data['tasks'][name].get('dependencies')
        require(isinstance(deps,list) and all(isinstance(d,str) for d in deps),'invalid dependencies')
        for dep in deps:
            require(dep in data['tasks'] and dep != name,'unknown/self dependency')
            visit(dep)
        visiting.remove(name)
        visited.add(name)
    for name in data['tasks']:
        visit(name)

def validate(data):
    require(isinstance(data,dict) and type(data.get('schema_version')) is int and data['schema_version'] == 1,'unsupported ledger schema')
    text(data.get('coordinator'),'coordinator')
    integer(data.get('revision'),'ledger revision')
    require(isinstance(data.get('generation'),str) and re.fullmatch(r'[0-9a-f]{32}',data['generation']),'invalid recovery generation')
    integer(data.get('max_active_workers'),'operating worker limit',1,8)
    require(isinstance(data.get('tasks'),dict),'invalid tasks')
    require(Path(data['project_root']).is_dir(),'project unavailable')
    for name,t in data['tasks'].items():
        require(isinstance(name,str) and IDENT.fullmatch(name) and t.get('id') == name and t.get('state') in STATES,'invalid task identity/state')
        integer(t.get('assignment_revision'),'assignment revision')
        integer(t.get('attempts'),'attempts')
    dag(data)

def unique_object(pairs):
    result = {}
    for key,value in pairs:
        require(key not in result,'duplicate JSON key')
        result[key] = value
    return result

def read_ledger(path):
    try:
        data = json.loads(Path(path).read_text('utf-8'),object_pairs_hook=unique_object)
    except (OSError,ValueError) as exc:
        raise LedgerError('ledger unreadable; use explicit recovery, never overwrite source files') from exc
    validate(data)
    return data

@contextmanager
def lock(path):
    p = Path(path).with_suffix('.lock')
    try:
        fd = os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError as exc:
        raise LedgerError('ledger writer lock exists; reconcile coordinator before retry') from exc
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as handle:
            json.dump({'pid':os.getpid(),'created_at':time.time()},handle)
        yield
    finally:
        p.unlink(missing_ok=True)

def save(path,data):
    validate(data)
    fd,tmp = tempfile.mkstemp(prefix='ledger-',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as handle:
            json.dump(data,handle,indent=2,sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            shutil.copyfile(path,path.with_suffix('.previous.json'))
        os.replace(tmp,path)
    finally:
        Path(tmp).unlink(missing_ok=True)

def create_ledger(path,project_root,coordinator):
    root,path = Path(project_root).resolve(),Path(path).resolve()
    require(root.is_dir() and path.is_relative_to(root / LEDGER_DIR),
            f'ledger must be project-local under {LEDGER_DIR}')
    require(not path.exists(),'ledger exists; read/recover it')
    legacy_dir = root / LEGACY_LEDGER_DIR
    require(not any((legacy_dir / name).exists() for name in
                    ('ledger.json', 'ledger.previous.json', 'ledger.lock')),
            f'legacy ledger state found under {LEGACY_LEDGER_DIR}; '
            f'migrate it to {LEDGER_DIR} before initializing')
    path.parent.mkdir(parents=True,exist_ok=True)
    data = {'schema_version':1,'generation':uuid.uuid4().hex,'coordinator':text(coordinator,'coordinator'),'project_root':str(root),'revision':0,'max_active_workers':8,
            'tasks':{},'runtime_worker_ids':[],'requires_runtime_reconciliation':True,'assignment_history':[],'decisions':[],'created_at':time.time(),'usage':{'tokens':None,'cost':None}}
    with lock(path):
        require(not path.exists(),'ledger appeared during creation')
        save(path,data)
    return data

def task_for(data,p,assignment=False):
    task = data['tasks'].get(p.get('task_id'))
    require(task is not None,'unknown task')
    if assignment:
        require(p.get('generation') == data['generation'],'stale recovery generation in assignment')
        require(type(p.get('task_revision')) is int and p['task_revision'] == task['assignment_revision'],'stale assignment revision')
    return task

def active_ids(data):
    ids = set(data.get('runtime_worker_ids',[]))
    ids.update(t['worker_id'] or f"reserved:{t['id']}:{t['assignment_revision']}" for t in data['tasks'].values() if t['worker_live'])
    return ids

def dependencies(data,task):
    for name in task['dependencies']:
        t = data['tasks'][name]
        require(t['state'] == 'verified' and t.get('accepted_fingerprint') == fingerprint(scoped(t)),'dependency not verified/current')

def verified_worktree(root,requested):
    target = Path(requested).resolve()
    require(target.is_dir() and target != root,'independent worktree required')
    registered = [Path(line[9:]).resolve() for line in git(root,'worktree','list','--porcelain').splitlines() if line.startswith('worktree ')]
    require(target in registered,'worktree is not registered with repository')
    common = (root/git(root,'rev-parse','--git-common-dir')).resolve()
    other = (target/git(target,'rev-parse','--git-common-dir')).resolve()
    require(common == other,'worktree belongs to another repository')
    return target

def routing(data,proposed,approval=None):
    script = Path(__file__).with_name('validate_orchestration.py')
    spec = importlib.util.spec_from_file_location('coordination_routing',script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    home = Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))
    roles = module.load_roles(home) if (home/'agents').is_dir() else {}
    project_home = Path(data['project_root'])/'.codex'
    if (project_home/'agents').is_dir():
        # Project profiles take precedence; native discovery/trust is checked
        # separately by the coordinator before dispatch.
        roles.update(module.load_roles(project_home))
    cache = home/'models_cache.json'
    catalog,defaults = module.load_model_catalog(cache) if cache.is_file() else (None,None)
    tasks = [t for t in data['tasks'].values() if t['worker_live'] and t['id'] != proposed['id']]+[proposed]
    workers = []
    for t in tasks:
        r = t['requested_settings']
        w = {'id':t['id'],'parent':t.get('parent_task') or 'main','role':r['role'],'model':r['model'],'reasoning_effort':r['effort'],'stop_condition':t['objective']}
        if r['effort'] == 'ultra':
            w.update(allowed_children=t.get('allowed_children',[]),max_children=t.get('max_children',0))
        workers.append(w)
    live_assignments = {f"{t['id']}:r{t['assignment_revision']}" for t in tasks if t['worker_live']}
    prior = [h['assignment_id'] for h in data.get('assignment_history',[]) if h['model'] in module.ASTRA_MODELS and h['assignment_id'] not in live_assignments]
    result = module.assess_plan({'workers':workers,'prior_astra_worker_ids':prior},roles,{'model':'gpt-6.2-sol','reasoning_effort':'medium'},catalog,defaults)
    require(not result['errors'],'routing validation: '+'; '.join(result['errors']))
    require(not result['gate_reasons'] or isinstance(approval,str) and bool(approval.strip()),'scoped human approval reference required: '+'; '.join(result['gate_reasons']))
    row = next(w for w in result['resolved_workers'] if w['id'] == proposed['id'])
    require((row['model'],row['reasoning_effort']) == (proposed['requested_settings']['model'],proposed['requested_settings']['effort']),'role pins defeat requested settings; use flexible role or documented fixed pair')
    if row['role'] in {'print-art-designer', 'print-cad-designer'}:
        require(row['reasoning_effort'] in {'high', 'xhigh', 'max'},
                f"{row['role']} requires High reasoning or higher for a design reservation")
    return {'role':row['role'],'model':row['model'],'effort':row['reasoning_effort'],'source':'advisory_resolution','resolution_source':row['resolution_source']}

def invalidate_dependents(data,name):
    queue,seen = [name],set()
    while queue:
        changed = queue.pop()
        if changed in seen:
            continue
        seen.add(changed)
        for t in data['tasks'].values():
            if changed in t['dependencies'] and t['state'] not in {'cancelled','failed'}:
                t['state'],t['blocker'],t['accepted_fingerprint'] = 'blocked',{'category':'dependency','reason':changed+' revised/stale'},None
                queue.append(t['id'])

def changed_paths(before,after):
    return sorted(n for n in set(before)|set(after) if before.get(n) != after.get(n))

def changes_reconciled(task,before,after,allowed):
    """Exact receipts acknowledge ambient edits; never grant new write scope."""
    receipts = task.get('reconciled_changes',[])
    return all(covers(allowed,n) or any(
        receipt['path'] == n and receipt['before_sha256'] == before.get(n)
        and receipt['after_sha256'] == after.get(n)
        and receipt['assignment_revision'] == task['assignment_revision']
        for receipt in receipts) for n in changed_paths(before,after))

def summary(data,task_id=None):
    """Bounded operational output; full ledger remains available for recovery."""
    counts = {state:sum(t['state'] == state for t in data['tasks'].values())
              for state in sorted(STATES)}
    result = {key:data.get(key) for key in (
        'schema_version','generation','revision','coordinator','project_root',
        'max_active_workers','requires_runtime_reconciliation')}
    result.update(task_counts=counts,active_worker_count=len(active_ids(data)))
    if task_id is not None:
        task = data['tasks'].get(task_id)
        require(task is not None,'unknown summary task')
        result['task'] = {key:task.get(key) for key in (
            'id','state','assignment_revision','worker_id','worker_live','attempts',
            'elapsed_seconds','requested_settings','observed_settings')}
        if task.get('blocker'):
            result['task']['blocker'] = {
                'category':task['blocker'].get('category'),
                'reason':str(task['blocker'].get('reason',''))[:1000]}
    return result

def run(data,action,p):
    root = Path(data['project_root'])
    if action == 'worker_limit':
        limit = integer(p.get('max_active_workers'),'operating worker limit',1,8)
        reason = text(p.get('reason'),'worker limit reason')
        require(not data['requires_runtime_reconciliation'],'runtime reconciliation required before changing worker limit')
        require(time.time()-data.get('runtime_observed_at',0) <= 120,'fresh native runtime roster required before changing worker limit')
        require(len(active_ids(data)) <= limit,'cannot lower limit below active/reserved workers')
        previous = data['max_active_workers']
        data['max_active_workers'] = limit
        data['decisions'].append({'note':reason,'previous_worker_limit':previous,'worker_limit':limit,'at':time.time()})
        return True
    if action == 'add':
        name = p.get('task_id')
        require(isinstance(name,str) and IDENT.fullmatch(name) and name not in data['tasks'],'invalid/duplicate task id')
        budget = p.get('budget',{'max_attempts':2,'max_seconds':900})
        require(isinstance(budget,dict),'invalid budget')
        integer(budget.get('max_attempts'),'max_attempts',1,10)
        integer(budget.get('max_seconds'),'max_seconds',1,86400)
        checks = p.get('acceptance_checks',[])
        require(isinstance(checks,list),'invalid acceptance checks')
        seen = set()
        for check in checks:
            require(isinstance(check,dict) and isinstance(check.get('id'),str) and IDENT.fullmatch(check['id']) and check['id'] not in seen,'invalid/duplicate check')
            seen.add(check['id'])
            require(isinstance(check.get('argv'),list) and bool(check['argv']) and all(isinstance(a,str) and not SECRET.search(a) for a in check['argv']),'checks require credential-free argv')
            integer(check.get('timeout_seconds',60),'check timeout',1,60)
        require(type(p.get('needs_review',False)) is bool and type(p.get('requires_worktree',False)) is bool,'invalid flags')
        require(bool(checks) or p.get('needs_review') is True,'meaningful acceptance checks or independent review required')
        data['tasks'][name] = {'id':name,'objective':text(p.get('objective'),'objective'),'context':p.get('context',''),'dependencies':p.get('dependencies',[]),
            'write_scope':paths(root,p.get('write_scope',[])),'input_scope':paths(root,p.get('input_scope',[])),'acceptance_checks':checks,
            'needs_review':p.get('needs_review',False),'requires_worktree':p.get('requires_worktree',False),'budget':budget,
            'attempts':0,'recovery_attempts':0,'elapsed_seconds':0.0,'assignment_revision':0,'state':'ready','owner':None,'worker_id':None,
            'worker_live':False,'requested_settings':None,'resolved_settings':{},'observed_settings':None,'execution_root':str(root),
            'artifact_paths':[],'result':None,'checks':{},'review':None,'accepted_fingerprint':None,'blocker':None}
        dag(data)
        return True
    if action == 'runtime':
        require(p.get('source') == 'native_runtime','runtime roster requires independent native observation')
        text(p.get('evidence'),'runtime roster evidence')
        ids = p.get('worker_ids')
        require(isinstance(ids,list) and all(isinstance(i,str) and i for i in ids) and len(ids) == len(set(ids)),'invalid runtime worker roster')
        known = {t['worker_id'] for t in data['tasks'].values() if t['worker_live'] and t['worker_id']}
        data['runtime_worker_ids'] = ids
        data['unmanaged_worker_ids'] = sorted(set(ids)-known)
        data['requires_runtime_reconciliation'] = bool(data['unmanaged_worker_ids'])
        data['runtime_observed_at'] = time.time()
        return True
    if action == 'checkpoint':
        data['decisions'].append({'note':text(p.get('note'),'decision/resume note'),'repository':snapshot(root),'at':time.time()})
        return True
    if action == 'recover':
        for t in data['tasks'].values():
            stale = t['state'] == 'verified' and t.get('accepted_fingerprint') != fingerprint(scoped(t))
            if t['worker_live'] or stale:
                t['state'],t['blocker'],t['accepted_fingerprint'] = 'blocked',{'category':'reconciliation','reason':'runtime/state reconciliation required'},None
                invalidate_dependents(data,t['id'])
        data['requires_runtime_reconciliation'] = True
        return True
    t = task_for(data,p,action in {'reserve','attach','stopped','result','observe_settings','reconcile_changes'})
    if action == 'reserve':
        require(not data['requires_runtime_reconciliation'],'runtime reconciliation required before dispatch')
        require(time.time()-data.get('runtime_observed_at',0) <= 120,'fresh native runtime roster required before dispatch')
        require(t['state'] in {'ready','blocked'} and not t['worker_live'],'task cannot be reserved')
        require(not t.get('blocker'),'resolve blocker with explicit revision')
        dependencies(data,t)
        require(t['attempts'] < t['budget']['max_attempts'] and t['elapsed_seconds'] < t['budget']['max_seconds'],'attempt/time budget exhausted')
        require(len(active_ids(data)) < data['max_active_workers'],'operating worker limit reached; descendants/reservations count')
        request = {'role':text(p.get('role'),'role'),'model':text(p.get('model'),'model'),'effort':text(p.get('effort'),'effort')}
        parent = p.get('parent_task')
        require(not parent and request['effort'] != 'ultra' and not request['role'].endswith('_ultra'),
                'single-coordinator v1 is leaf-only; use explicit non-Ultra leaf settings, even under an Ultra root')
        execution = verified_worktree(root,p['worktree']) if p.get('worktree') else root
        require(not t['requires_worktree'] or execution != root,'complex independent writes require verified worktree isolation')
        t['execution_root'] = str(execution)
        t['write_scope'],t['input_scope'] = paths(execution,t['write_scope']),paths(execution,t['input_scope'])
        for other in data['tasks'].values():
            if other['id'] != t['id'] and other['worker_live'] and other['execution_root'].casefold() == str(execution).casefold():
                require(not overlap(t['write_scope'],other['write_scope']),'exclusive write ownership collision')
        baseline = snapshot(execution)
        dirty = [n for n in baseline['dirty_paths'] if covers(t['write_scope'],n)]
        acknowledged = paths(execution,p.get('acknowledge_dirty',[]))
        require(all(covers(acknowledged,n) for n in dirty),'preexisting dirty owned files require explicit acknowledgement')
        t.update(requested_settings=request,parent_task=parent,owner=text(p.get('owner'),'owner'),allowed_children=p.get('allowed_children',[]),max_children=p.get('max_children',0))
        t['resolved_settings'] = routing(data,t,p.get('human_approval_reference'))
        t['assignment_revision'] += 1
        t['attempts'] += 1
        data.setdefault('assignment_history',[]).append({'assignment_id':f"{t['id']}:r{t['assignment_revision']}",
            'task_id':t['id'],'assignment_revision':t['assignment_revision'],'model':t['resolved_settings']['model'],
            'effort':t['resolved_settings']['effort'],'requested_settings':dict(request),'at':time.time()})
        t.update(state='running',worker_live=True,worker_id=None,started_at=time.time(),baseline=baseline,result=None,checks={},review=None,
                  artifact_paths=[],accepted_fingerprint=None,observed_settings=None,blocker=None,
                  reconciled_changes=[],stop_observation=None)
        return True
    if action == 'attach':
        require(t['worker_live'] and t['state'] == 'running' and t['worker_id'] is None,'no uncertain reservation to attach')
        worker = text(p.get('worker_id'),'worker id')
        require(not any(x['worker_live'] and x['worker_id'] == worker for x in data['tasks'].values()),'worker owns another live assignment')
        t['worker_id'] = worker
        return True
    if action == 'stopped':
        observation = p.get('observation',{})
        require(p.get('worker_id') == t['worker_id'] and observation.get('source') == 'native_runtime' and observation.get('status') in {'completed','stopped','not_spawned'},'independent runtime stop observation required')
        require(observation['status'] != 'not_spawned' or t['worker_id'] is None,'attached worker cannot be declared not spawned')
        text(observation.get('evidence'),'stop evidence')
        now = time.time()
        completed = observation.get('completed_at',now)
        require(type(completed) in (int,float) and math.isfinite(completed)
                and t['started_at'] <= completed <= now,'invalid runtime completion timestamp')
        if 'completed_at' in observation:
            require(observation['status'] == 'completed','timestamp requires completed runtime observation')
        if not t['worker_live']:
            require(t.get('stop_observation') == observation,'stop already recorded; do not rewrite execution time')
            return False
        if t['worker_live']:
            t['elapsed_seconds'] += completed-t['started_at']
        t['worker_live'],t['stop_observation'] = False,observation
        t['stop_recorded_at'] = now
        data['runtime_worker_ids'] = [i for i in data['runtime_worker_ids'] if i != t['worker_id']]
        return True
    if action == 'reconcile_changes':
        require(t['state'] in {'running','awaiting_review'},'reconcile an active assignment only')
        require(p.get('source') in {'coordinator','external'},'name the observed change source')
        reason = text(p.get('reason'),'reconciliation evidence')
        rows = p.get('changes')
        require(isinstance(rows,list) and bool(rows),'explicit changed paths and hashes required')
        before = (t.get('result') or {}).get('repository_snapshot',t['baseline'])['files']
        after = snapshot(Path(t['execution_root']))['files']
        protected = t['input_scope']+t['write_scope']+t.get('artifact_paths',[])
        records = []
        for row in rows:
            require(isinstance(row,dict),'invalid reconciliation row')
            name = paths(Path(t['execution_root']),[row.get('path')])[0]
            require(not excluded(name) and not covers(protected,name),
                    'cannot reconcile reviewed inputs, owned outputs, or excluded state')
            require(name in changed_paths(before,after),'path has no unreconciled change at this boundary')
            require('before_sha256' in row and 'after_sha256' in row
                    and row['before_sha256'] == before.get(name)
                    and row['after_sha256'] == after.get(name),'reconciliation hash mismatch')
            records.append(dict(path=name,before_sha256=before.get(name),after_sha256=after.get(name),
                                assignment_revision=t['assignment_revision'],source=p['source'],
                                reason=reason,at=time.time()))
        t.setdefault('reconciled_changes',[]).extend(records)
        return True
    if action == 'observe_settings':
        require(p.get('worker_id') == t['worker_id'] and p.get('source') in {'runtime_event','server_metadata','client_child_config'},'worker self-report/root defaults do not prove effective child settings')
        t['observed_settings'] = {'worker_id':t['worker_id'],'model':text(p.get('model'),'observed model'),'effort':text(p.get('effort'),'observed effort'),
                                  'source':p['source'],'evidence':text(p.get('evidence'),'settings evidence')}
        return True
    if action == 'result':
        require(p.get('worker_id') == t['worker_id'] and t['worker_id'] is not None,'result worker does not own assignment')
        result_id = fingerprint(p)
        if (t.get('result') or {}).get('id') == result_id:
            return False
        require(t['state'] == 'running','result is not for active assignment')
        elapsed = t['elapsed_seconds']+(max(0.0,time.time()-t['started_at']) if t['worker_live'] else 0)
        require(elapsed <= t['budget']['max_seconds'],'time budget exhausted; reconcile worker')
        after,allowed = snapshot(Path(t['execution_root'])),list(t['write_scope'])
        for other in data['tasks'].values():
            if other['id'] != t['id'] and other['worker_live'] and other['execution_root'] == t['execution_root']:
                allowed += other['write_scope']
        before = t['baseline']['files']
        changed = changed_paths(before,after['files'])
        require(not any(covers(t['input_scope'],n) and not covers(t['write_scope'],n) for n in changed),
                'review inputs changed since reservation; revise the assignment')
        require(changes_reconciled(t,before,after['files'],allowed),
                'out-of-scope repository changes detected; preserve/reconcile edits')
        t['artifact_paths'] = paths(Path(t['execution_root']),p.get('artifacts',[]))
        require(all(inside(Path(t['execution_root']),n).is_file() and not excluded(n) for n in t['artifact_paths']),'artifact missing/excluded')
        state = scoped(t)
        t['result'] = {'id':result_id,'summary':text(p.get('summary'),'summary'),'fingerprint':fingerprint(state),'snapshot':state,
                       'assignment_revision':t['assignment_revision'],'changed_paths':sorted(changed),'repository_snapshot':after}
        t['state'] = 'awaiting_review'
        return True
    if action == 'check':
        require(t['state'] == 'awaiting_review' and not t['worker_live'],'checks require result and confirmed worker stop')
        require(not any(o['id'] != t['id'] and o['worker_live'] and o['write_scope'] and o['execution_root'] == t['execution_root'] for o in data['tasks'].values()),
                'serialize acceptance checks against other live same-root writers')
        require(t['result']['fingerprint'] == fingerprint(scoped(t)),'result evidence is stale')
        check = next((c for c in t['acceptance_checks'] if c['id'] == p.get('check_id')),None)
        require(check is not None,'unknown check')
        before = snapshot(Path(t['execution_root']))
        started = time.time()
        try:
            result = subprocess.run(check['argv'],cwd=t['execution_root'],capture_output=True,timeout=check.get('timeout_seconds',60),shell=False)
            exit_code,out,err = result.returncode,result.stdout,result.stderr
        except subprocess.TimeoutExpired as exc:
            exit_code,out,err = None,exc.stdout or b'',exc.stderr or b''
        after = snapshot(Path(t['execution_root']))
        allowed = list(t['write_scope'])
        changed = [n for n in set(before['files'])|set(after['files']) if before['files'].get(n) != after['files'].get(n)]
        require(all(covers(allowed,n) for n in changed),'out-of-scope acceptance command edits detected; preserve/reconcile files')
        t['checks'][check['id']] = {'argv':check['argv'],'cwd':t['execution_root'],'exit_code':exit_code,'stdout_sha256':digest(out),'stderr_sha256':digest(err),
                                   'elapsed_seconds':time.time()-started,'assignment_revision':t['assignment_revision'],'fingerprint':fingerprint(scoped(t))}
        return True
    if action == 'review':
        require(t['state'] == 'awaiting_review' and not t['worker_live'],'review requires returned/stopped assignment')
        reviewer = text(p.get('reviewer'),'reviewer')
        require(reviewer not in {t['owner'],t['worker_id']},'review must be independent')
        require(type(p.get('approved')) is bool,'explicit review outcome required')
        t['review'] = {'reviewer':reviewer,'approved':p['approved'],'evidence':text(p.get('evidence'),'review evidence'),
                       'assignment_revision':t['assignment_revision'],'fingerprint':fingerprint(scoped(t))}
        return True
    if action == 'verify':
        require(t['state'] == 'awaiting_review' and not t['worker_live'],'only coordinator verifies returned/stopped work')
        dependencies(data,t)
        current = fingerprint(scoped(t))
        require(t['result']['fingerprint'] == current,'result evidence is stale')
        before,after = t['result']['repository_snapshot']['files'],snapshot(Path(t['execution_root']))['files']
        allowed = list(t['write_scope'])
        for other in data['tasks'].values():
            if other['id'] != t['id'] and other['worker_live'] and other['execution_root'] == t['execution_root']:
                allowed += other['write_scope']
        require(changes_reconciled(t,before,after,allowed),
                'repository changed outside accepted ownership; preserve/reconcile files')
        for c in t['acceptance_checks']:
            e = t['checks'].get(c['id'],{})
            require(e.get('exit_code') == 0 and e.get('fingerprint') == current and e.get('assignment_revision') == t['assignment_revision'],'acceptance checks missing/failed/stale')
        if t['needs_review']:
            review = t.get('review') or {}
            require(review.get('approved') is True and review.get('fingerprint') == current,'independent current review missing')
        t['state'],t['accepted_fingerprint'] = 'verified',current
        return True
    if action in {'cancel','block','fail'}:
        if action == 'cancel':
            t['state'],t['blocker'] = 'cancelled',{'category':'cancelled','reason':text(p.get('reason'),'cancel reason')}
        else:
            category = p.get('category','technical')
            require(category in {'access','requirements','technical','budget','dependency','reconciliation'},'invalid blocker category')
            t['state'],t['blocker'] = ('failed' if action == 'fail' else 'blocked'),{'category':category,'reason':text(p.get('reason'),'blocker reason')}
            if p.get('failed_recovery') is True:
                t['recovery_attempts'] += 1
        t['accepted_fingerprint'] = None
        invalidate_dependents(data,t['id'])
        return True
    if action == 'revise':
        require(not t['worker_live'],'stop/reconcile prior worker before reassigning')
        text(p.get('resolution'),'blocker resolution/reassignment note')
        require(t['recovery_attempts'] < 2 or p.get('extension_reference'),'two failed recovery approaches require scope reassessment')
        if 'dependencies' in p:
            t['dependencies'] = p['dependencies']
        t.update(state='ready',assignment_revision=t['assignment_revision']+1,blocker=None,result=None,checks={},review=None,accepted_fingerprint=None,observed_settings=None)
        dag(data)
        invalidate_dependents(data,t['id'])
        return True
    raise LedgerError('unknown ledger action')

def apply_command(path,actor,expected_revision,action,payload,expected_generation=None):
    path = Path(path).resolve()
    require(isinstance(payload,dict) and not SECRET.search(json.dumps(payload)),'payload must be credential-free object')
    with lock(path):
        data = read_ledger(path)
        require(actor == data['coordinator'],'only configured coordinator writes ledger')
        require(expected_generation == data['generation'],'stale recovery generation')
        require(type(expected_revision) is int and expected_revision == data['revision'],'stale ledger revision')
        if run(data,action,payload):
            data['revision'] += 1
            data['updated_at'] = time.time()
            save(path,data)
        return data

def recover_previous(path,actor):
    path = Path(path).resolve()
    with lock(path):
        previous = read_ledger(path.with_suffix('.previous.json'))
        require(actor == previous['coordinator'],'only coordinator recovers ledger')
        if path.exists():
            shutil.copyfile(path,path.with_name('ledger-damaged-'+uuid.uuid4().hex+'.json'))
        previous['requires_runtime_reconciliation'] = True
        previous['generation'] = uuid.uuid4().hex
        previous['history_incomplete'] = True
        previous['runtime_observed_at'] = None
        for t in previous['tasks'].values():
            if t['worker_live']:
                t['state'],t['blocker'] = 'blocked',{'category':'reconciliation','reason':'recovered generation; reconcile runtime'}
        previous['revision'] += 1
        path.unlink(missing_ok=True)
        save(path,previous)
        return previous

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    init = sub.add_parser('init');init.add_argument('--root',required=True);init.add_argument('--coordinator',required=True)
    status = sub.add_parser('status');status.add_argument('--ledger',required=True)
    apply = sub.add_parser('apply');apply.add_argument('--ledger',required=True);apply.add_argument('--request',required=True)
    recover = sub.add_parser('recover-previous');recover.add_argument('--ledger',required=True);recover.add_argument('--coordinator',required=True)
    for child in (init,status,apply,recover):
        child.add_argument('--summary',action='store_true',help='Print compact state without repository snapshots')
    status.add_argument('--task',help='Include one task in compact status')
    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            result = create_ledger(Path(args.root) / LEDGER_DIR / 'ledger.json',args.root,args.coordinator)
        elif args.command == 'status':
            result = read_ledger(args.ledger)
        elif args.command == 'recover-previous':
            result = recover_previous(args.ledger,args.coordinator)
        else:
            request = json.loads(Path(args.request).read_text('utf-8'),object_pairs_hook=unique_object)
            result = apply_command(args.ledger,request['actor'],request['expected_revision'],request['action'],request.get('payload',{}),request.get('expected_generation'))
        selected = request.get('payload',{}).get('task_id') if args.command == 'apply' else getattr(args,'task',None)
        print(json.dumps(summary(result,selected) if args.summary else result,indent=2))
        return 0
    except (LedgerError,OSError,ValueError,KeyError) as exc:
        print(json.dumps({'error':str(exc)}))
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
