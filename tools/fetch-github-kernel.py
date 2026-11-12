import sys, json, subprocess, urllib.request, urllib.error, importlib.util, pathlib

def main():
    run=sys.argv[1]; out=pathlib.Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
    meta=json.loads(subprocess.check_output(['gh','api',f'repos/nonrootus/ios-sweet/actions/runs/{run}/artifacts']))
    artifact=next(a for a in meta['artifacts'] if a['name']=='xnu-kernel' and not a['expired'])
    token=subprocess.check_output(['gh','auth','token'],text=True).strip()
    class NoRedirect(urllib.request.HTTPRedirectHandler):
     def redirect_request(self,*args,**kwargs): return None
    req=urllib.request.Request(artifact['archive_download_url'],headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','User-Agent':'ios-sweet-artifact-fetch'})
    try:
     urllib.request.build_opener(NoRedirect).open(req,timeout=25)
     raise RuntimeError('Expected redirect; no file downloaded')
    except urllib.error.HTTPError as e:
     if e.code not in (301,302,303,307,308): raise RuntimeError('Artifact redirect HTTP '+str(e.code)) from None
     signed=e.headers.get('Location')
     if not signed: raise RuntimeError('No artifact redirect')
    spec=importlib.util.spec_from_file_location('remotezip','/mnt/d/ios-sweet/src/ios-sweet/tools/remotezip.py'); rz=importlib.util.module_from_spec(spec);spec.loader.exec_module(rz)
    entries=rz.central_dir(signed)
    for name in ('kernel.development.sweet','SHA256SUMS'):
     matches=[e for e in entries if e[0]==name]
     if len(matches)!=1: raise RuntimeError('Unexpected artifact contents for '+name)
     print(name,'compressed bytes',matches[0][2],flush=True)
     rz.extract(signed,matches[0],str(out))

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Kernel artifact download failed:", type(exc).__name__, file=sys.stderr)
        sys.exit(1)
