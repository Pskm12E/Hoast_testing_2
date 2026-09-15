#!/usr/bin/env python3
"""Root-owned entry point: accept static Notebook assets on stdin, never code."""
import fcntl
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import socket
import subprocess
import sys
import tarfile
import tempfile

MAX_ARCHIVE = 12 * 1024 * 1024
ASSETS = {"public/" + name for name in (
    "index.html", "notes.html", "styles.css", "app.js", "favicon.svg")}


def validate_archive(raw):
    if not raw or len(raw) > MAX_ARCHIVE:
        raise ValueError("Release archive is empty or exceeds 12 MiB")
    found = set()
    # Uncompressed tar only: no decompression or archive extraction as root.
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        for count, member in enumerate(archive, start=1):
            path = PurePosixPath(member.name)
            if count > 256 or path.is_absolute() or ".." in path.parts:
                raise ValueError("Invalid release member path or too many files")
            if not (member.isfile() or member.isdir()):
                raise ValueError("Links and special files are not allowed")
            if member.name in ASSETS:
                if member.name in found or not member.isfile() or not 0 < member.size < 2_000_000:
                    raise ValueError("Invalid or duplicate public asset")
                archive.extractfile(member).read().decode("utf-8")
                found.add(member.name)
    if found != ASSETS:
        raise ValueError("Release must contain all five Notebook public assets")
    return hashlib.sha256(raw).hexdigest()


def main():
    if len(sys.argv) != 1:
        raise ValueError("This command accepts a release archive on stdin and no arguments")
    if os.geteuid() != 0 or socket.gethostname() != "4bytedigi":
        raise ValueError("This command is installed only on 4bytedigi")
    os.umask(0o077)
    os.chdir("/")
    fd = os.open("/run/notebook-deploy.lock", os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        raw = sys.stdin.buffer.read(MAX_ARCHIVE + 1)
        digest = validate_archive(raw)
        with tempfile.TemporaryDirectory(prefix="notebook-deploy-", dir="/run") as folder:
            archive = Path(folder) / "release.tar"
            archive.write_bytes(raw)
            # This installer is installed by the administrator, not taken from the archive.
            subprocess.run([
                "/usr/bin/python3", "-I", "/usr/local/lib/notebook-deploy/install.py",
                str(archive), digest,
            ], cwd="/", env={"PATH": "/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                             "HOME": "/root", "LANG": "C.UTF-8"}, check=True, timeout=180)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, tarfile.TarError, UnicodeError, BlockingIOError) as error:
        print(f"Notebook deployment rejected: {error}", file=sys.stderr)
        sys.exit(64)
