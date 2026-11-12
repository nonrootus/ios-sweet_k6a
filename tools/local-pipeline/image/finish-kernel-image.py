"""Usage: finish-kernel-image.py VERSION HEAD KERNEL_RUN RENDERER_RUN
Waits out the slow connection, runs the compact job and builds the temporary boot image. No phone."""
import json
import subprocess
import sys
import time

version, head, kernel_run, renderer_run = sys.argv[1:5]
# a renderer built from another commit, reused with this kernel
renderer_head = sys.argv[5] if len(sys.argv) > 5 else head
REPO = 'nonrootus/ios-sweet'
BRANCH = 'codex/gpu-k6a-bo-macos15'


sys.path.insert(0, 'D:/ios-sweet/build')
import urllib.request
import gh_token
TOKEN = gh_token.token()
API = 'https://api.github.com/repos/' + REPO


def rest(path, body=None):
    request = urllib.request.Request(path if path.startswith('https:') else API + path,
        data=None if body is None else json.dumps(body).encode(), method='GET' if body is None else 'POST',
        headers={'Authorization': 'Bearer ' + TOKEN, 'Accept': 'application/vnd.github+json',
                 'User-Agent': 'sweet-k6a-finish', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=30) as reply:
        text = reply.read().decode()
        return json.loads(text) if text.strip() else {}


def gh(*args):
    """The few gh CLI calls of this script, over the REST API (WSL is not needed)."""
    try:
        if args[:2] == ('workflow', 'run'):
            fields = dict(a.split('=', 1) for a in args[args.index('-f') + 1::2])
            ref = args[args.index('--ref') + 1]
            rest('/actions/workflows/xnu.yml/dispatches', {'ref': ref, 'inputs': fields})
            return 0, ''
        if args[:2] == ('run', 'view'):
            r = rest('/actions/runs/' + args[2])
            return 0, json.dumps({'status': r['status'], 'conclusion': r['conclusion'], 'headSha': r['head_sha']})
        if args[:2] == ('run', 'list'):
            limit = args[args.index('--limit') + 1]
            runs = rest('/actions/workflows/xnu.yml/runs?per_page=' + limit)['workflow_runs']
            return 0, json.dumps([{'databaseId': r['id'], 'headSha': r['head_sha'], 'status': r['status'],
                                   'conclusion': r['conclusion']} for r in runs])
        if args[0] == 'api':
            return 0, json.dumps(rest('/' + args[1].split('/', 3)[3]))
    except Exception as error:  # retried by the callers
        print('GitHub:', error, flush=True)
        return 1, ''
    raise ValueError(args)


def json_of(*args):
    for _ in range(240):  # an hour: the connection here drops for a while
        try:
            code, out = gh(*args)
            if code == 0 and out.strip():
                return json.loads(out)
        except (subprocess.TimeoutExpired, ValueError):
            pass
        time.sleep(15)
    raise SystemExit('GitHub did not answer: ' + ' '.join(args))


def wait(run, expected):
    while True:
        state = json_of('run', 'view', run, '-R', REPO, '--json', 'status,conclusion,headSha')
        if state['status'] == 'completed':
            print('run', run, state['conclusion'], state['headSha'], flush=True)
            assert state['headSha'] == expected, state
            return state['conclusion']
        time.sleep(30)


assert wait(kernel_run, head) == 'success', 'kernel build failed'
assert wait(renderer_run, renderer_head) == 'success', 'renderer build failed'

known = {int(kernel_run), int(renderer_run)}
compact = None
for attempt in range(1, 5):
    # An older compact run at the renderer head must never be taken for this kernel's.
    known |= {r['databaseId'] for r in json_of('run', 'list', '-R', REPO, '-w', 'xnu.yml', '--limit', '30', '--json', 'databaseId,headSha,status,conclusion')}
    for _ in range(10):
        code, _out = gh('workflow', 'run', 'xnu.yml', '-R', REPO, '--ref', BRANCH, '-f', 'compact_only=true', '-f', 'source_run=' + kernel_run)
        if code == 0:
            break
        time.sleep(15)
    found = None
    for _ in range(40):
        time.sleep(10)
        runs = json_of('run', 'list', '-R', REPO, '-w', 'xnu.yml', '--limit', '8', '--json', 'databaseId,headSha,status,conclusion')
        # The compact job takes the kernel by source_run; it runs at the branch head, which may
        # be a later renderer-only commit.
        fresh = [r for r in runs if r['headSha'] in (head, renderer_head) and r['databaseId'] not in known]
        if fresh:
            found = fresh[0]
            if found['status'] == 'completed':
                break
    if found is None or found['status'] != 'completed':
        continue
    known.add(found['databaseId'])
    print('compact attempt', attempt, found['databaseId'], found['conclusion'], flush=True)
    if found['conclusion'] == 'success':
        compact = str(found['databaseId'])
        break
assert compact is not None, 'compact job did not succeed'

artifacts = json_of('api', f'repos/{REPO}/actions/runs/{compact}/artifacts')['artifacts']
artifact = next(a for a in artifacts if a['name'] == 'sweet-compact-development-kernel')
print('artifact', artifact['id'], artifact['size_in_bytes'], flush=True)
subprocess.run([sys.executable, 'D:/ios-sweet/build/prepare-kernel-renderer.py', version, renderer_head, kernel_run, renderer_run, compact,
                str(artifact['id']), version, head], check=True)
print('IMAGE READY', version, flush=True)
