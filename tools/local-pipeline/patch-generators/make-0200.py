"""Patch 0200: SpringBoard gets the Sweet renderer loader, which keeps its CoreImage on the CPU.

SpringBoard crashed at every start in CI::GLContext::init (Apple's OpenGL ES has no driver
here, and without Metal CoreImage takes that path for CoreUI's styled lock screen images).
With sweetcagpu=1 the kernel adds DYLD_INSERT_LIBRARIES=/sweet/lib/libSweetRendererLoader.dylib
to SpringBoard's environment at exec (no file on the root changes), and the "AMFI" policy's
dyld query (0x5a) answers for SpringBoard as it does for the real backboardd, so dyld honours
it. The loader then sets "software_renderer" on every CIContext of SpringBoard.
Bases: tree for kern_exec.c (0042 is the only earlier patch on it); tree + 0175 + 0192 for
sweet_amfi.c.
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path('D:/ios-sweet/src/ios-sweet')
TREE = Path('D:/ios-sweet/build/xnu-buildtree-40478936434/xnu')
GIT = ['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false']
NAME = '0200-sweet-springboard-coreimage-cpu.patch'
EXEC = 'bsd/kern/kern_exec.c'
AMFI = 'bsd/kern/sweet_amfi.c'
FILES = [EXEC, AMFI]

with tempfile.TemporaryDirectory(prefix='make-0200-', dir='D:/ios-sweet/build') as scratch:
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
    base = {f: (work / f).read_bytes().decode() for f in FILES}

new = dict(base)


def edit(path, before, after):
    assert new[path].count(before) == 1, (path, new[path].count(before), before[:80])
    new[path] = new[path].replace(before, after)


edit(EXEC, '''__attribute__((noinline))
static int
exec_extract_strings(struct image_params *imgp)
{''', '''#if defined(ARM64_BOARD_CONFIG_SWEET)
/* sweetcagpu=1 and the image is SpringBoard: see the environment entry added below. */
static bool
sweet_exec_wants_loader(struct image_params *imgp)
{
	static int requested = -1;

	if (requested < 0) {
		int value = 0;
		requested = PE_parse_boot_argn("sweetcagpu", &value, sizeof(value)) && value == 1;
	}
	return requested && imgp->ip_strings != NULL &&
	       strcmp(imgp->ip_strings + strlen(EXECUTABLE_KEY),
	       "/System/Library/CoreServices/SpringBoard.app/SpringBoard") == 0;
}
#endif

__attribute__((noinline))
static int
exec_extract_strings(struct image_params *imgp)
{''')
edit(EXEC, '''		imgp->ip_argspace -= new_ptr_size; /* to hold envv[] entry */
		imgp->ip_envc++;
	}

	/* Save space for envv[] NULL terminator */''', '''		imgp->ip_argspace -= new_ptr_size; /* to hold envv[] entry */
		imgp->ip_envc++;
	}

#if defined(ARM64_BOARD_CONFIG_SWEET)
	/*
	 * SpringBoard gets the Sweet renderer loader, which keeps its CoreImage contexts on the CPU:
	 * without Metal they take Apple's OpenGL ES, which has no driver here, and SpringBoard
	 * crashed at every start. The "AMFI" policy (sweet_amfi.c) lets dyld honour the variable.
	 */
	if (sweet_exec_wants_loader(imgp)) {
		static const char loader[] = "DYLD_INSERT_LIBRARIES=/sweet/lib/libSweetRendererLoader.dylib";

		error = exec_add_user_string(imgp, CAST_USER_ADDR_T(loader), UIO_SYSSPACE, TRUE);
		if (error) {
			goto bad;
		}
		if (imgp->ip_argspace < new_ptr_size) {
			error = E2BIG;
			goto bad;
		}
		imgp->ip_argspace -= new_ptr_size; /* to hold its envv[] entry */
		imgp->ip_envc++;
		printf("SWEET CI: SpringBoard starts with the renderer loader\\n");
	}
#endif

	/* Save space for envv[] NULL terminator */''')

edit(AMFI, '''	static const unsigned char expected[CS_CDHASH_LEN] = {
		0x89, 0xe6, 0x32, 0x85, 0x41, 0xc2, 0xe3, 0x75, 0x22, 0xd9,
		0x0f, 0xa4, 0xa6, 0x93, 0xc7, 0x46, 0x82, 0x5b, 0x22, 0xa8,
	};
	unsigned char actual[CS_CDHASH_LEN];
	if (call != 0x5a || !proc_is64bit(p) || proc_ppid(p) != 1 ||
	    proc_getcdhash(p, actual) != 0 || memcmp(actual, expected, sizeof(expected)) != 0) {
		return ENOPOLICY;
	}

	vnode_t executable = proc_getexecutablevnode(p);
	if (executable == NULLVP) {
		return ENOPOLICY;
	}
	char path[MAXPATHLEN];
	int length = sizeof(path);
	int error = vn_getpath(executable, path, &length);
	vnode_put(executable);
	if (error != 0 || strcmp(path, "/usr/libexec/real/backboardd") != 0) {
		printf("SWEET CA: dyld policy did not match the renderer executable path (%d)\\n", error);
		return ENOPOLICY;
	}
''', '''	static const unsigned char expected[CS_CDHASH_LEN] = {
		0x89, 0xe6, 0x32, 0x85, 0x41, 0xc2, 0xe3, 0x75, 0x22, 0xd9,
		0x0f, 0xa4, 0xa6, 0x93, 0xc7, 0x46, 0x82, 0x5b, 0x22, 0xa8,
	};
	unsigned char actual[CS_CDHASH_LEN];
	if (call != 0x5a || !proc_is64bit(p) || proc_ppid(p) != 1) {
		return ENOPOLICY;
	}

	vnode_t executable = proc_getexecutablevnode(p);
	if (executable == NULLVP) {
		return ENOPOLICY;
	}
	char path[MAXPATHLEN];
	int length = sizeof(path);
	int error = vn_getpath(executable, path, &length);
	vnode_put(executable);
	/*
	 * The signed window server from the GPU test root, or SpringBoard, which the kernel starts
	 * with the renderer loader (kern_exec.c) to keep its CoreImage on the CPU.
	 */
	bool backboardd = error == 0 && strcmp(path, "/usr/libexec/real/backboardd") == 0 &&
	    proc_getcdhash(p, actual) == 0 && memcmp(actual, expected, sizeof(expected)) == 0;
	bool springboard = error == 0 && strcmp(path, "/System/Library/CoreServices/SpringBoard.app/SpringBoard") == 0;
	if (!backboardd && !springboard) {
		static unsigned mismatches;
		if (mismatches++ < 4) {
			printf("SWEET CA: dyld policy did not match the renderer executable path (%d)\\n", error);
		}
		return ENOPOLICY;
	}
''')

with tempfile.TemporaryDirectory(prefix='make-0200-', dir='D:/ios-sweet/build') as scratch:
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
    out = Path('D:/ios-sweet/build/recon-0200')
    for f in FILES:
        (out / Path(f).name.replace('.c', '.0200.c')).write_bytes(new[f].encode())
print(NAME, len(text.splitlines()), 'lines, forward and reverse verified')

script = REPO / 'tools/check-sweet-patch-reversal.sh'
lines = script.read_bytes().decode().replace('\r\n', '\n').split('\n')
lines = [line for line in lines if NAME not in line and '# 0200:' not in line]
at = [i for i, line in enumerate(lines) if '0192-sweet-amfi-bootarg-state.patch' in line and 'apply --reverse' in line]
assert len(at) == 1
if '--exclude=' + AMFI not in lines[at[0]]:
    lines[at[0]] = lines[at[0]].replace(' --check ', ' --check --exclude=' + AMFI + ' ', 1)
last = max(i for i, line in enumerate(lines) if 'apply --reverse --check' in line or 'grep -F' in line)
lines.insert(last + 1, '# 0200: SpringBoard starts with the renderer loader (CoreImage on the CPU).')
lines.insert(last + 2, 'git -C dxb/xnu apply --reverse --check "$GITHUB_WORKSPACE/xnu/patches/' + NAME + '"')
script.write_bytes('\n'.join(lines).encode())
print('reversal script updated')
