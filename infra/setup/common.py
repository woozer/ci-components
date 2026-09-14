"""Shared process, state and local API helpers for the demo installer."""
import importlib.util
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[2]
INFRA = ROOT / 'infra'
STATE = INFRA / '.state'
ADMIN_HOST = os.environ.get('DEMO_ADMIN_HOST', '127.0.0.1')
HTTP = build_opener(ProxyHandler({}))
PROJECT_RECORDS = {
    'hello-world': INFRA / 'gitlab-ce/secrets/project.json',
    'ci-components': INFRA / 'gitlab-ce/secrets/components-project.json',
    'ci-samples': INFRA / 'gitlab-runner/secrets/samples-project.json',
}


def save(path, value):
    """Write private state atomically, including credentials."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + '.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(value)
    temporary.chmod(0o600)
    temporary.replace(path)


def save_json(path, value):
    save(path, json.dumps(value, indent=2) + '\n')


def load_json(path, default=None):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else default


def run(args, *, capture=False, input=None, cwd=ROOT, env=None):
    result = subprocess.run([str(arg) for arg in args], cwd=cwd,
        input=input, text=True, stdout=subprocess.PIPE if capture else None,
        env={**os.environ, **(env or {})})
    if result.returncode:
        # Commands and captured data can contain private configuration.
        raise RuntimeError(f'{args[0]} failed with exit code {result.returncode}')
    return result.stdout if capture else None


def compose(service, *args, capture=False, input=None):
    return run(['docker', 'compose', '-f', INFRA / service / 'compose.yml', *args],
               capture=capture, input=input)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def project_id(name):
    return load_json(PROJECT_RECORDS[name])['id']


def local_url(port, path=''):
    return f'http://{ADMIN_HOST}:{port}{path}'


def request_json(url, *, method='GET', data=None, headers=None, allowed=()):
    request = Request(url, method=method,
        data=None if data is None else json.dumps(data).encode(),
        headers={'Content-Type': 'application/json', **(headers or {})})
    try:
        with HTTP.open(request, timeout=30) as response:
            body = response.read()
            return json.loads(body) if body else None
    except HTTPError as error:
        if error.code in allowed:
            return None
        raise RuntimeError(f'Local API returned HTTP {error.code}') from None


def gitlab(path, method='GET', data=None, allowed=()):
    token = (INFRA / 'gitlab-ce/secrets/provisioning-token').read_text().strip()
    return request_json(local_url(8929, '/api/v4' + path), method=method, data=data,
                        headers={'PRIVATE-TOKEN': token}, allowed=allowed)


def wait_ready(name, check, timeout=900):
    deadline = time.monotonic() + timeout
    print(f'Waiting for {name}...', flush=True)
    while time.monotonic() < deadline:
        try:
            if check():
                print(f'{name} is ready.', flush=True)
                return
        except (URLError, TimeoutError, ConnectionError, RuntimeError):
            pass
        time.sleep(5)
    raise RuntimeError(f'{name} did not become ready within {timeout} seconds')


def ensure_env_password(path, key):
    path = Path(path)
    if not path.exists():
        save(path, f'{key}={secrets.token_urlsafe(32)}\n')


def announce(message):
    print(message, flush=True)


def architecture(value):
    aliases = {'aarch64': 'arm64', 'arm64': 'arm64',
               'x86_64': 'amd64', 'amd64': 'amd64'}
    try:
        return aliases[value]
    except KeyError:
        raise RuntimeError(f'Unsupported Docker architecture: {value}') from None


def docker_architecture():
    return architecture(run(['docker', 'info', '--format', '{{.Architecture}}'], capture=True).strip())


def kubectl(*args, input=None):
    return run(['docker', 'exec', '-i', 'desktop-control-plane', 'kubectl',
                '--kubeconfig', '/etc/kubernetes/admin.conf', *args], capture=True, input=input)
