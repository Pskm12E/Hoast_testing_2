#!/usr/bin/env python3
"""Deploy Little Notes into 4bytedigi's existing isolated app VM.

Run as root on 4bytedigi: python3 install.py release.tar SHA256
The tar is produced by git archive. No credentials are included in this repo.
"""
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tarfile
from datetime import datetime, timezone

DOMAIN = "notebook.pyiesone.dev"
MARKER = "# Managed by Little Notes deploy/install.py"
SSH = ["ssh", "-F", "/etc/dbstudios-host/ssh_config"]
SITE = "/etc/nginx/sites-available/notebook"
ENABLED = "/etc/nginx/sites-enabled/notebook"
CF = Path("/etc/cloudflared/config.yml")


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def remote(guest, code):
    return run(SSH + [guest, "sudo -n python3 -"], input=code, text=True,
               stdout=subprocess.PIPE).stdout


def check_http(host, path, expected=200, method="GET"):
    conn = http.client.HTTPConnection("127.0.0.1", 3080, timeout=20)
    conn.request(method, path, headers={"Host": host, "X-Forwarded-Proto": "https"})
    response = conn.getresponse()
    data = response.read()
    assert response.status == expected, (host, path, response.status, expected)
    if host == DOMAIN and expected == 200:
        assert response.getheader("X-Content-Type-Options") == "nosniff"
        assert "default-src 'self'" in response.getheader("Content-Security-Policy", "")
        if path in ("/", "/notes.html"):
            assert b"Little Notes" in data
    conn.close()


def main():
    assert os.geteuid() == 0 and socket.gethostname() == "4bytedigi"
    archive = Path(sys.argv[1]).resolve()
    digest = sys.argv[2].lower()
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    raw = archive.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, "Release checksum mismatch"
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw)) as package:
        for name in ["index.html", "notes.html", "styles.css", "app.js", "favicon.svg"]:
            member = package.getmember("public/" + name)
            assert member.isfile() and member.size < 2_000_000
            files[name] = package.extractfile(member).read().decode("utf-8")

    for unit in ["dbstudios-app", "dbstudios-gateway", "dbstudios-tunnel"]:
        run(["systemctl", "is-active", "--quiet", unit])
    for domain in ["dbstudios.pyiesone.dev", "hazrul-evite.pyiesone.dev"]:
        check_http(domain, "/api/health")
    old_cf = CF.read_text()
    assert "tunnel: dc054a50-d5b1-4c37-b12a-b2c89d11ca56" in old_cf
    new_cf = old_cf
    if DOMAIN not in old_cf:
        anchor = "  - service: http_status:404"
        assert old_cf.count(anchor) == 1
        new_cf = old_cf.replace(anchor,
            f"  - hostname: {DOMAIN}\n    service: http://127.0.0.1:3080\n" + anchor)
    else:
        assert f"  - hostname: {DOMAIN}\n    service: http://127.0.0.1:3080" in old_cf

    backup = Path("/var/backups/notebook") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup.mkdir(parents=True, mode=0o700)
    os.chmod(backup.parent, 0o700)
    (backup / "cloudflared.yml").write_text(old_cf)
    (backup / "release.sha256").write_text(digest + "\n")
    old = {}
    for guest in ["app", "gateway"]:
        old[guest] = json.loads(remote(guest, f'''
from pathlib import Path
import json, os
p=Path({SITE!r}); link=Path({ENABLED!r})
text=p.read_text() if p.exists() else None
assert text is None or text.startswith({MARKER!r}), "Existing unmanaged notebook configuration"
assert not link.exists() or (link.is_symlink() and str(link.resolve()) == str(p))
print(json.dumps({{"text":text,"enabled":link.is_symlink()}}))
'''))
    (backup / "nginx-before.json").write_text(json.dumps(old, indent=2))
    release = f"/srv/notebook/releases/{digest[:16]}"
    app_conf = f"""{MARKER}
server {{
    listen 172.30.12.2:3080;
    server_name {DOMAIN};
    root {release}/public;
    server_tokens off;
    if ($request_method !~ ^(GET|HEAD)$) {{ return 405; }}
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy no-referrer always;
    add_header X-Frame-Options DENY always;
    add_header Cache-Control no-cache always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'" always;
    location = / {{ try_files /index.html =404; }}
    location = /notes {{ try_files /notes.html =404; }}
    location ~ ^/(index\\.html|notes\\.html|styles\\.css|app\\.js|favicon\\.svg)$ {{ try_files $uri =404; }}
    location / {{ return 404; }}
}}
"""
    gateway_conf = f"""{MARKER}
server {{
    listen 10.0.2.15:3080;
    server_name {DOMAIN};
    server_tokens off;
    client_max_body_size 16k;
    location / {{
        proxy_pass http://172.30.12.2:3080;
        proxy_set_header Host {DOMAIN};
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_connect_timeout 5s;
        proxy_read_timeout 30s;
    }}
}}
"""
    changed = []
    tunnel_changed = False
    try:
        remote("app", f'''
from pathlib import Path
import os
p=Path({release!r})/'public'
p.mkdir(parents=True, exist_ok=True)
for parent in [p, p.parent, p.parent.parent, p.parent.parent.parent]: parent.chmod(0o755)
for name,text in {files!r}.items():
    dest=p/name
    if dest.exists(): assert dest.read_text() == text, "Release already exists with different contents"
    dest.write_text(text); dest.chmod(0o644)
''')
        for guest, config in [("app", app_conf), ("gateway", gateway_conf)]:
            changed.append(guest)
            remote(guest, f'''
from pathlib import Path
import subprocess
p=Path({SITE!r}); p.write_text({config!r}); p.chmod(0o644)
link=Path({ENABLED!r})
if not link.is_symlink(): link.symlink_to(p)
subprocess.run(['nginx','-t'],check=True)
subprocess.run(['systemctl','reload','nginx'],check=True)
''')
        for path in ["/", "/notes.html", "/styles.css", "/app.js", "/favicon.svg"]:
            check_http(DOMAIN, path)
        check_http(DOMAIN, "/.env", 404)
        check_http(DOMAIN, "/server.mjs", 404)
        check_http(DOMAIN, "/", 405, "POST")
        for domain in ["dbstudios.pyiesone.dev", "hazrul-evite.pyiesone.dev"]:
            check_http(domain, "/api/health")
        if new_cf != old_cf:
            tunnel_changed = True
            CF.write_text(new_cf)
            run(["cloudflared", "--config", str(CF), "tunnel", "ingress", "validate"])
            run(["systemctl", "restart", "dbstudios-tunnel"])
        run(["systemctl", "is-active", "--quiet", "dbstudios-tunnel"])
    except BaseException:
        if tunnel_changed:
            CF.write_text(old_cf)
            run(["systemctl", "restart", "dbstudios-tunnel"])
        for guest in reversed(changed):
            state = old[guest]
            remote(guest, f'''
from pathlib import Path
import subprocess
p=Path({SITE!r}); link=Path({ENABLED!r}); state={state!r}
if state['text'] is None: p.unlink(missing_ok=True)
else: p.write_text(state['text'])
if not state['enabled']: link.unlink(missing_ok=True)
subprocess.run(['nginx','-t'],check=True)
subprocess.run(['systemctl','reload','nginx'],check=True)
''')
        raise
    print(json.dumps({"installed":True,"domain":DOMAIN,"release":release,
                      "backup":str(backup),"private_checks":"passed"}))


if __name__ == "__main__":
    main()
