from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,subprocess,sys,time

version=sys.argv[1]
assert version == '0181'
base=Path('D:/ios-sweet/build')
out=base/f'a618-{version}-device'
image=out/'shim-boot-sweet-a618-gpu.img'
manifest=json.loads((out/f'a618-{version}-image.json').read_text())
assert image.stat().st_size==manifest['image_bytes']
assert hashlib.sha256(image.read_bytes()).hexdigest()==manifest['image_sha256']
assert len(' '.join(manifest['flags']))==580 and 'sweetcagpu=1' in manifest['flags']
assert manifest['flags'][-2] in ('sweetusb=3','sweetusb=4') and manifest['flags'][-1]=='sweetzaplayout=1'
assert manifest['kernel_source']=='ed68c3ca11794cda5978d79a436b6b009c3d65c4'
assert manifest['renderer_disk_sha256']=='16ab131ea40c67ba805c7cc9a63b55feea4c39d6b7fd5e268b0033f3b92a22dd'
flashes=base/'a618-0177-device'
flash=json.loads(max(flashes.glob('flash-*.json'),key=lambda p:p.stat().st_mtime_ns).read_text())
assert flash['flash_exit']==0 and flash['successful_writes']==24
assert flash['root_sha256']=='aefd7d64b39ee96f82ef75f081d6f82f05ba6635b001ef68713b3ebec41aa08e'
tools=Path(__import__('os').environ['LOCALAPPDATA'])/'Android/Sdk/platform-tools'
adb=tools/'adb.exe'
fastboot=tools/'fastboot.exe'
def call(tool,*args,timeout=10):
    try:
        return subprocess.run([tool,*args],capture_output=True,text=True,timeout=timeout)
    except subprocess.TimeoutExpired:
        print(tool.stem, 'timed out during',next((a for a in args if a in ('getvar','boot','devices','reboot')), 'query'),flush=True)
        raise SystemExit(21)
def devices(tool,mode):
    p=call(tool,'devices')
    assert p.returncode==0
    return [line.split()[0] for line in p.stdout.splitlines()
            if len(line.split())==2 and line.split()[1]==mode]
recovery=devices(adb,'recovery')
serials=devices(fastboot,'fastboot')
if recovery and not serials:
    assert len(recovery)==1
    target,=recovery
    boot_serial=call(adb,'-s',target,'shell','getprop','ro.boot.serialno')
    assert boot_serial.returncode==0
    acceptable={target.casefold(),boot_serial.stdout.strip().casefold()}
    assert call(adb,'-s',target,'reboot','bootloader',timeout=20).returncode==0
    for _ in range(16):
        serials=devices(fastboot,'fastboot')
        if serials:break
        time.sleep(1.5)
    assert len(serials)==1 and serials[0].casefold() in acceptable
elif not recovery and len(serials)==1:
    pass
else:
    print('The phone is not available in recovery or fastboot',flush=True)
    raise SystemExit(22)
serial,=serials
r=call(fastboot,'-s',serial,'getvar','product')
assert r.returncode==0 and re.search(r'(?m)^(?:\(bootloader\)\s*)?product:\s*sweet\s*$',r.stdout+r.stderr)
r=call(fastboot,'-s',serial,'getvar','max-download-size')
limit=re.search(r'(?m)^(?:\(bootloader\)\s*)?max-download-size:\s*(0x[0-9a-fA-F]+|[0-9]+)\s*$',r.stdout+r.stderr)
assert r.returncode==0 and limit and image.stat().st_size <= int(limit.group(1),0)
r=call(fastboot,'-s',serial,'boot',str(image),timeout=25)
log=(r.stdout+r.stderr).replace(serial,'[device]')
print(log,flush=True)
record=dict(version=version,image_sha256=manifest['image_sha256'],root_sha256=flash['root_sha256'],
            exit_code=r.returncode,fastboot_output=log)
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
(out/f'boot-{stamp}.json').write_text(json.dumps(record,indent=2)+'\n')
assert r.returncode==0 and re.search(r'(?m)^Booting\s+OKAY',log)

