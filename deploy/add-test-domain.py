#!/usr/bin/env python3
"""One-time admin setup: add test.4bytedigi.com to the existing Notebook route."""
from datetime import datetime, timezone
import http.client
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile

CONFIG = Path('/etc/cloudflared/config.yml')
HOSTNAME = 'test.4bytedigi.com'
RULE = '''  - hostname: test.4bytedigi.com
    service: http://127.0.0.1:3080
    originRequest:
      httpHostHeader: notebook.pyiesone.dev
'''


def check_origin():
    for host, path in [('notebook.pyiesone.dev', '/'),
                       ('notebook.pyiesone.dev', '/notes.html'),
                       ('dbstudios.pyiesone.dev', '/api/health'),
                       ('hazrul-evite.pyiesone.dev', '/api/health')]:
        connection = http.client.HTTPConnection('127.0.0.1', 3080, timeout=15)
        connection.request('GET', path, headers={'Host': host, 'X-Forwarded-Proto': 'https'})
        response = connection.getresponse()
        data = response.read()
        assert response.status == 200, (host, path, response.status)
        if host == 'notebook.pyiesone.dev':
            assert b'Little Notes' in data
        connection.close()


def atomic_write(text, metadata):
    descriptor, name = tempfile.mkstemp(prefix='.notebook-alias-', dir=CONFIG.parent)
    try:
        with os.fdopen(descriptor, 'w') as output:
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(name, metadata.st_mode & 0o777)
        os.chown(name, metadata.st_uid, metadata.st_gid)
        os.replace(name, CONFIG)
    finally:
        Path(name).unlink(missing_ok=True)


def main():
    assert os.geteuid() == 0 and socket.gethostname() == '4bytedigi'
    subprocess.run(['systemctl', 'is-active', '--quiet', 'dbstudios-tunnel'], check=True)
    check_origin()
    old = CONFIG.read_text()
    metadata = CONFIG.stat()
    assert 'tunnel: dc054a50-d5b1-4c37-b12a-b2c89d11ca56' in old
    assert 'hostname: notebook.pyiesone.dev' in old
    if HOSTNAME in old:
        assert RULE in old, 'Existing test hostname has a different configuration'
        print('TEST_DOMAIN_ROUTE_ALREADY_READY')
        return
    anchor = '  - service: http_status:404'
    assert old.count(anchor) == 1, 'Unexpected tunnel configuration; no changes made'
    new = old.replace(anchor, RULE + anchor)
    folder = Path('/var/backups/notebook') / datetime.now(timezone.utc).strftime('alias-%Y%m%dT%H%M%SZ')
    folder.mkdir(parents=True, mode=0o700)
    shutil.copy2(CONFIG, folder / 'cloudflared.yml')
    restarted = False
    try:
        atomic_write(new, metadata)
        subprocess.run(['cloudflared', '--config', str(CONFIG), 'tunnel', 'ingress', 'validate'], check=True)
        subprocess.run(['cloudflared', '--config', str(CONFIG), 'tunnel', 'ingress', 'rule', 'https://' + HOSTNAME], check=True)
        restarted = True
        subprocess.run(['systemctl', 'restart', 'dbstudios-tunnel'], check=True)
        subprocess.run(['systemctl', 'is-active', '--quiet', 'dbstudios-tunnel'], check=True)
        check_origin()
    except BaseException:
        atomic_write(old, metadata)
        if restarted:
            subprocess.run(['systemctl', 'restart', 'dbstudios-tunnel'], check=True)
        raise
    print('TEST_DOMAIN_ROUTE_READY; backup=' + str(folder))


if __name__ == '__main__':
    main()
