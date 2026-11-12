"""Fetch the small verified development-kernel artifact over a timed connection."""
from pathlib import Path
from urllib.parse import urlparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
import zipfile

run = int(sys.argv[1])
artifact_id = int(sys.argv[2])
out = Path(f'D:/ios-sweet/artifacts/xnu-0181-compact-{run}')
out.mkdir(exist_ok=True)
partial = out / 'compact.partial.zip'
sys.path.insert(0, 'D:/ios-sweet/build')
import gh_token
headers = {'Authorization':'Bearer '+gh_token.token(),
           'Accept':'application/vnd.github+json',
           'User-Agent':'sweet-k6a-compact-kernel'}
api = 'https://api.github.com/repos/nonrootus/ios-sweet'

class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, response_headers, new_url):
        result = super().redirect_request(request, fp, code, message, response_headers, new_url)
        if result is not None and urlparse(new_url).hostname != 'api.github.com':
            result.remove_header('Authorization')
        return result

opener = urllib.request.build_opener(Redirect())
def metadata(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=30) as response:
        return json.load(response)

state = metadata(f'{api}/actions/runs/{run}')
assert state['status']=='completed' and state['conclusion']=='success'
assert state['head_sha']=='ed68c3ca11794cda5978d79a436b6b009c3d65c4'
artifact = metadata(f'{api}/actions/artifacts/{artifact_id}')
assert artifact['workflow_run']['id']==run
assert artifact['name']=='sweet-compact-development-kernel'
assert artifact['size_in_bytes'] < 6 * 1024 * 1024
expected = artifact['digest'].removeprefix('sha256:')
for attempt in range(1,6):
    print('Compact download attempt',attempt,flush=True)
    try:
        request=urllib.request.Request(artifact['archive_download_url'],headers=headers)
        with opener.open(request,timeout=45) as response,partial.open('wb') as file:
            digest=hashlib.sha256();total=0
            while chunk:=response.read(256 * 1024):
                file.write(chunk);digest.update(chunk);total+=len(chunk)
                if total%(1024*1024)<len(chunk):print('Downloaded MiB',total//(1024*1024),flush=True)
        assert digest.hexdigest()==expected,'ZIP SHA-256 mismatch'
        print('Verified compact ZIP',total,expected,flush=True)
        break
    except Exception as error:
        print('Retry after',type(error).__name__,str(error)[:120],flush=True)
        if attempt==5:raise
        time.sleep(2*attempt)

with zipfile.ZipFile(partial) as archive:
    names=set(archive.namelist())
    assert {'kernel.development.sweet.xz','SHA256SUMS','COMPRESSED-SHA256SUMS'} <= names
    assert all(not (name.startswith('/') or '..' in Path(name).parts) for name in names)
    archive.extractall(out)
print('READY compact 0181 kernel archive',out,flush=True)
