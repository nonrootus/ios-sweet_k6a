"""Patch 0213: jailbreak tweak injection: no kernel loader in SpringBoard; DYLD variables for all.

- 0200 made the kernel add DYLD_INSERT_LIBRARIES=/sweet/lib/libSweetRendererLoader.dylib to
  SpringBoard's environment. Its CoreImage hook never ran (0200/0200b), and a jailbroken root sets
  SpringBoard's DYLD_INSERT_LIBRARIES=/usr/lib/TweakInject.dylib (ElleKit) in launchd.plist: the
  kernel's entry, appended later, would override it. The kernel adds it now only with
  boot-arg sweetsbloader=1 (absent: off).
- The "AMFI" dyld query (0x5a) allowed DYLD_* variables only for backboardd and SpringBoard. ElleKit
  injects tweaks into apps and daemons through launchd: every 64-bit child of launchd now gets the same
  answer (path variables allowed, a library that fails to load is skipped).
Bases: as for 0200, plus 0200 itself.
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
TREE = Path('D:/ios-sweet/build/xnu-buildtree-40478936434/xnu')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0213-sweet-jailbreak-tweak-injection.patch'
EXEC = 'bsd/kern/kern_exec.c'
AMFI = 'bsd/kern/sweet_amfi.c'
FILES = [EXEC, AMFI]

with tempfile.TemporaryDirectory(prefix='make-0213-', dir='D:/ios-sweet/build') as scratch:
    work = Path(scratch)
    for f in FILES:
        (work / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(TREE / f, work / f)
    p42 = work / '0042.patch'
    p42.write_bytes(subprocess.check_output(GIT + ['show', 'HEAD:xnu/patches/0042-sweet-short-exec-log.patch'], cwd=REPO))
    subprocess.run(GIT + ['apply', '--reverse', '--check', '--include=' + EXEC, p42.name], cwd=work, check=True)
    for earlier in ('0175-sweet-backboardd-dyld-policy.patch', '0192-sweet-amfi-bootarg-state.patch'):
        patch = work / earlier
        patch.write_bytes(subprocess.check_output(GIT + ['show', 'HEAD:xnu/patches/' + earlier], cwd=REPO))
        subprocess.run(GIT + ['apply', '--include=' + AMFI, patch.name], cwd=work, check=True)
    p200 = work / '0200.patch'
    p200.write_bytes(subprocess.check_output(GIT + ['show', 'HEAD:xnu/patches/0200-sweet-springboard-coreimage-cpu.patch'], cwd=REPO))
    subprocess.run(GIT + ['apply', p200.name], cwd=work, check=True)
    base = {f: (work / f).read_bytes().decode() for f in FILES}

new = dict(base)


def edit(path, before, after):
    assert new[path].count(before) == 1, (path, new[path].count(before), before[:80])
    new[path] = new[path].replace(before, after)


edit(EXEC, """		requested = PE_parse_boot_argn("sweetcagpu", &value, sizeof(value)) && value == 1;
""", """		/* Off unless sweetsbloader=1: a jailbroken root injects SpringBoard's tweaks itself. */
		requested = PE_parse_boot_argn("sweetsbloader", &value, sizeof(value)) && value == 1;
""")
start = new[AMFI].index("	static const unsigned char expected[CS_CDHASH_LEN] = {")
stop = new[AMFI].index("\tstruct {\n\t\tuint64_t input_flags;")
assert start < stop and new[AMFI].count("	static const unsigned char expected[CS_CDHASH_LEN] = {") == 1
new[AMFI] = new[AMFI][:start] + """	if (call != 0x5a || !proc_is64bit(p) || proc_ppid(p) != 1) {
		return ENOPOLICY;
	}
	/*
	 * Every child of launchd: backboardd's renderer loader, SpringBoard's and the apps' tweaks
	 * (ElleKit's TweakInject.dylib, set in launchd.plist and by its launchd hook).
	 */
	int error;
""" + new[AMFI][stop:]
edit(AMFI, r"""	error = copyout(&flags, query.output_flags, sizeof(flags));
	printf("SWEET CA: backboardd dyld policy input=0x%llx rc=%d\n",
	    (unsigned long long)query.input_flags, error);
	return error;
""", r"""	error = copyout(&flags, query.output_flags, sizeof(flags));
	static unsigned answered;
	if (answered++ < 16) {
		char name[32];
		proc_name(proc_pid(p), name, sizeof(name));
		printf("SWEET CA: dyld policy for %s input=0x%llx rc=%d\n", name,
		    (unsigned long long)query.input_flags, error);
	}
	return error;
""")
with tempfile.TemporaryDirectory(prefix='make-0213-', dir='D:/ios-sweet/build') as scratch:
    work = Path(scratch)
    for side, data in (('a', base), ('b', new)):
        for f in FILES:
            path = work / side / f
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data[f].encode())
    done = subprocess.run(GIT + ['diff', '--no-index', '--no-color', '--no-prefix', '-U3', 'a', 'b'], cwd=work, capture_output=True)
    assert done.returncode == 1, done.stderr
    text = re.sub(r'^diff --git .*\n(index .*\n)?', '', done.stdout.decode(), flags=re.M)
    assert text.startswith('--- a/') and '\r' not in text
    output = REPO / 'xnu/patches' / NAME
    output.write_bytes(text.encode())
    for f in FILES:
        path = work / 'check' / f
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base[f].encode())
    subprocess.run(GIT + ['apply', str(output)], cwd=work / 'check', check=True)
    assert all((work / 'check' / f).read_bytes() == new[f].encode() for f in FILES)
    subprocess.run(GIT + ['apply', '--reverse', str(output)], cwd=work / 'check', check=True)
    for f in FILES:
        (TREE / f).with_name(Path(f).name.replace('.c', '.new0213.c')).write_bytes(new[f].encode())
        (TREE / f).with_name(Path(f).name.replace('.c', '.base0213.c')).write_bytes(base[f].encode())
print(NAME, len(text.splitlines()), 'lines, forward and reverse verified')

script = REPO / 'tools/check-sweet-patch-reversal.sh'
lines = script.read_bytes().decode().replace('\r\n', '\n').split('\n')
lines = [line for line in lines if NAME not in line and '# 0213:' not in line]
at = [i for i, line in enumerate(lines) if '0200-sweet-springboard-coreimage-cpu.patch' in line and 'apply --reverse' in line]
assert len(at) == 1
lines[at[0]] = lines[at[0]].replace(' --check ', ' --check --exclude=' + EXEC + ' --exclude=' + AMFI + ' ', 1)
last = max(i for i, line in enumerate(lines) if 'apply --reverse --check' in line or 'grep -F' in line)
lines.insert(last + 1, '# 0213: no kernel loader in SpringBoard; DYLD variables for every launchd child (tweaks).')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())
print('reversal script updated')
