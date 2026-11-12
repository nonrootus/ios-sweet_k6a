import json,re,subprocess,sys,time,urllib.parse,urllib.request
branch,sha=sys.argv[1:]
assert re.fullmatch(r'codex/[a-z0-9-]+',branch) and re.fullmatch(r'[0-9a-f]{40}',sha)
api='https://api.github.com/repos/nonrootus/ios-sweet/actions/workflows/xnu.yml'
params=urllib.parse.urlencode({'branch':branch,'per_page':'10'})
sys.path.insert(0,'D:/ios-sweet/build')
import gh_token
token=gh_token.token()
assert token
headers={'User-Agent':'sweet-k6a-ci-check','Authorization':'Bearer '+token,
         'Accept':'application/vnd.github+json','Content-Type':'application/json'}
def matching():
    req=urllib.request.Request(f'{api}/runs?{params}',headers=headers)
    with urllib.request.urlopen(req,timeout=20) as f:
        return [x for x in json.load(f)['workflow_runs'] if x['head_sha']==sha]
found=matching()
if not found:
    import os
    runner=os.environ.get('SWEET_RUNNER','macos-15-intel')  # arm64 M1; macos-15-intel as fallback
    body=json.dumps({'ref':branch,'inputs':{'runner':runner}}).encode()
    req=urllib.request.Request(api+'/dispatches',data=body,headers=headers,method='POST')
    with urllib.request.urlopen(req,timeout=20) as f:
        assert f.status in (200,204),f.status
    for _ in range(10):
        time.sleep(2)
        found=matching()
        if found:break
assert len(found)==1
r=found[0]
print('Kernel CI',r['id'],r['head_sha'],r['status'],r['html_url'],flush=True)

