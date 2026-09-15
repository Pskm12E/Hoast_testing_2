"""Reject dangerous release archives before any privileged action occurs."""
import importlib.util
import io
from pathlib import Path
import tarfile
import unittest

spec = importlib.util.spec_from_file_location("entry", Path(__file__).with_name("passwordless-entry.py"))
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)


def release(extra=(), omit=None):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        for name in sorted(entry.ASSETS):
            if name == omit:
                continue
            body = b"Little Notes"
            member = tarfile.TarInfo(name)
            member.size = len(body)
            archive.addfile(member, io.BytesIO(body))
        for member, body in extra:
            member.size = len(body)
            archive.addfile(member, io.BytesIO(body))
    return output.getvalue()


class EntryValidation(unittest.TestCase):
    def test_regular_release_and_nonexecuted_repository_code(self):
        member = tarfile.TarInfo("deploy/install.py")
        self.assertEqual(len(entry.validate_archive(release([(member, b"raise Exception('must never run')")]))), 64)

    def test_rejects_traversal_absolute_path_duplicate_and_missing_asset(self):
        for name in ["../escape", "/etc/sudoers", "public/index.html"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                entry.validate_archive(release([(tarfile.TarInfo(name), b"bad")]))
        with self.assertRaises(ValueError):
            entry.validate_archive(release(omit="public/app.js"))

    def test_rejects_symlink(self):
        member = tarfile.TarInfo("link")
        member.type = tarfile.SYMTYPE
        member.linkname = "/etc/shadow"
        with self.assertRaises(ValueError):
            entry.validate_archive(release([(member, b"")]))

    def test_rejects_empty_and_oversized_input(self):
        for raw in [b"", b"x" * (entry.MAX_ARCHIVE + 1)]:
            with self.assertRaises(ValueError):
                entry.validate_archive(raw)


if __name__ == "__main__":
    unittest.main()
