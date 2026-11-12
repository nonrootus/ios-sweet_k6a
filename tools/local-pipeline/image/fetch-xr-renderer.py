from pathlib import Path
import hashlib
import json
import re
import struct
import subprocess
import sys

base = Path('D:/ios-sweet')
run = int(sys.argv[1])
source = '78c3db86ec79e71152142d6b4dd147888c529662'
import urllib.request
import urllib.parse
import zipfile
import time

api = 'https://api.github.com/repos/nonrootus/ios-sweet'
sys.path.insert(0, 'D:/ios-sweet/build')
import gh_token
token = gh_token.token()
assert token
headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
         'User-Agent':'sweet-k6a-renderer'}
def metadata(suffix):
    with urllib.request.urlopen(urllib.request.Request(api + suffix, headers=headers),timeout=30) as response:
        return json.load(response)
class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, response_headers, new_url):
        result = super().redirect_request(request, fp, code, message, response_headers, new_url)
        if result is not None and urllib.parse.urlparse(new_url).hostname != 'api.github.com':
            result.remove_header('Authorization')
        return result
opener=urllib.request.build_opener(Redirect())
meta=metadata(f'/actions/runs/{run}')
assert meta['head_sha'] == source and meta['conclusion'] == 'success'
items=metadata(f'/actions/runs/{run}/artifacts')['artifacts']
artifact,=[x for x in items if x['name']=='sweet-ios16-renderer-arm64' and not x['expired']]
assert artifact['size_in_bytes'] < 32*1024**2
out=base/'artifacts'/f'sweet-renderer-{run}'
out.mkdir(exist_ok=True)
partial=out/'renderer.partial.zip'
for attempt in range(1,5):
    try:
        req=urllib.request.Request(artifact['archive_download_url'],headers=headers)
        with opener.open(req,timeout=35) as resp,partial.open('wb') as stream:
            digest=hashlib.sha256()
            while chunk:=resp.read(256*1024):
                stream.write(chunk)
                digest.update(chunk)
        assert 'sha256:'+digest.hexdigest()==artifact['digest']
        break
    except Exception as error:
        print('Renderer download attempt',attempt,type(error).__name__,flush=True)
        if attempt==4: raise
        time.sleep(2*attempt)
with zipfile.ZipFile(partial) as archive:
    allowed={'SHA256SUMS','CREDITS.md','Mesa-license.rst','SOURCES.txt',
             'sweet/lib/libOSMesa.8.dylib','sweet/lib/libSweetEAGL.dylib',
             'sweet/lib/libSweetRendererLoader.dylib'}
    # Renderers from d89c963 on also carry sweetnet (jailbreak root, USB network).
    if 'sweet/bin/sweetnet' in archive.namelist():
        allowed.add('sweet/bin/sweetnet')
    assert set(archive.namelist())==allowed
    archive.extractall(out)
partial.rename(out/'renderer.zip')

expected = {f'sweet/lib/{filename}' for filename in (
    'libOSMesa.8.dylib', 'libSweetEAGL.dylib', 'libSweetRendererLoader.dylib')}
seen = set()
for line in (out / 'SHA256SUMS').read_text().splitlines():
    digest, filename = line.split(maxsplit=1)
    if filename == 'sweet/bin/sweetnet':
        data = (out / filename).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest, filename
        assert struct.unpack_from('<4I', data)[:2] == (0xfeedfacf, 0x0100000c) and struct.unpack_from('<4I', data)[3] == 2
        print('Verified arm64 executable', filename, len(data), digest, flush=True)
        continue
    assert filename in expected and filename not in seen and re.fullmatch('[0-9a-f]{64}', digest)
    seen.add(filename)
    data = (out / filename).read_bytes()
    assert hashlib.sha256(data).hexdigest() == digest, filename
    magic, cpu, _, filetype, ncmds, cmds_size, _, _ = struct.unpack_from('<8I', data)
    assert (magic, cpu, filetype) == (0xfeedfacf, 0x0100000c, 6), filename
    assert 32 + cmds_size <= len(data)
    pos = 32
    names, builds, signatures = [], [], []
    for _ in range(ncmds):
        command, size = struct.unpack_from('<II', data, pos)
        assert size >= 8 and pos + size <= 32 + cmds_size
        if command == 0x0d:
            name_at, = struct.unpack_from('<I', data, pos + 8)
            names.append(data[pos + name_at:pos + size].split(b'\0', 1)[0].decode())
        elif command == 0x32:
            builds.append(struct.unpack_from('<II', data, pos + 8))
        elif command == 0x1d:
            sig_at, sig_size = struct.unpack_from('<II', data, pos + 8)
            signatures.append(sig_size > 0 and sig_at + sig_size <= len(data))
        pos += size
    assert names == ['/' + filename] and builds == [(2, 0x100000)] and signatures == [True], filename
    print('Verified arm64 iOS 16 signed dylib', filename, len(data), digest, flush=True)
assert seen == expected
(out / 'ci-evidence.json').write_text(json.dumps(meta, indent=2) + '\n')
print(out)
