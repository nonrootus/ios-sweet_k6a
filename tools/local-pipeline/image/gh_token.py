"""GitHub token for the CI scripts without WSL: Windows Git Credential Manager first, then WSL gh."""
import os
import subprocess


def token():
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='never')
    try:
        done = subprocess.run(['git', '-c', 'credential.helper=', '-c', 'credential.helper=manager', 'credential', 'fill'],
                              input=b'protocol=https\nhost=github.com\n\n', capture_output=True, timeout=30, env=env)
        for line in done.stdout.decode().splitlines():
            if line.startswith('password=') and len(line) > 9:
                return line[9:].strip()
    except subprocess.TimeoutExpired:
        pass
    return subprocess.check_output(['wsl', '-d', 'Ubuntu-24.04', '--', 'gh', 'auth', 'token', '--hostname', 'github.com'],
                                   timeout=45).decode().strip()
