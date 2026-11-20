import hashlib
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from subprocess import TimeoutExpired
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared/tooling"))
import wurst_dependency_receipt as receipt


class WurstDependencyReceiptTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.compile = Path(temporary.name)
        self.dependency = self.compile / "_build/dependencies/wurstStdlib2"
        self.dependency.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(self.dependency)], check=True)
        subprocess.run(["git", "-C", str(self.dependency), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(self.dependency), "config", "user.name", "Test"], check=True)
        (self.dependency / "a.wurst").write_bytes(b"alpha\n")
        (self.dependency / "b.wurst").write_bytes(b"beta\n")
        subprocess.run(["git", "-C", str(self.dependency), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.dependency), "commit", "-qm", "fixture"], check=True)

    def output(self):
        stream = io.StringIO()
        with redirect_stdout(stream):
            receipt.log_installed_stdlib(self.compile)
        return stream.getvalue().strip()

    def test_clean_installed_commit_and_tracked_bytes(self):
        revision = subprocess.check_output(["git", "-C", str(self.dependency), "rev-parse", "HEAD"], text=True).strip()
        rows = [[name, hashlib.sha256((self.dependency / name).read_bytes()).hexdigest()]
                for name in ("a.wurst", "b.wurst")]
        digest = hashlib.sha256(json.dumps(rows, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(self.output(),
                         f"WurstStdlib2 install receipt: status=observed-clean revision={revision} "
                         f"trackedSha256={digest} trackedFiles=2 evidenceOnly=true")

    def test_changed_or_untracked_content_is_unverified(self):
        (self.dependency / "a.wurst").write_bytes(b"altered\n")
        self.assertEqual(self.output(),
                         "WurstStdlib2 install receipt: status=unverified reason=working-tree-dirty")
        subprocess.run(["git", "-C", str(self.dependency), "checkout", "--", "a.wurst"], check=True)
        (self.dependency / "secret.txt").write_text("private content")
        self.assertEqual(self.output(),
                         "WurstStdlib2 install receipt: status=unverified reason=working-tree-dirty")

    def test_absent_ambiguous_and_unavailable_git_never_claim_provenance(self):
        (self.compile / "_build/dependencies/WurstStdlib2").mkdir()
        self.assertEqual(self.output(),
                         "WurstStdlib2 install receipt: status=unverified reason=dependency-absent-or-ambiguous")
        (self.compile / "_build/dependencies/WurstStdlib2").rmdir()
        self.dependency.rename(self.compile / "removed")
        self.assertEqual(self.output(),
                         "WurstStdlib2 install receipt: status=unverified reason=dependency-absent-or-ambiguous")
        (self.compile / "removed").rename(self.dependency)
        dependencies = self.dependency.parent
        dependencies.rename(self.compile / "hidden")
        self.assertEqual(self.output(),
                         "WurstStdlib2 install receipt: status=unverified reason=dependency-absent")
        (self.compile / "hidden").rename(dependencies)
        with patch.object(receipt.subprocess, "run", side_effect=FileNotFoundError("sensitive path")):
            self.assertEqual(self.output(),
                             "WurstStdlib2 install receipt: status=unverified reason=inspection-unavailable")

    def test_optional_inspection_timeout_and_oversized_content_are_nonfatal(self):
        with patch.object(receipt.subprocess, "run", side_effect=TimeoutExpired("git", 30)):
            self.assertEqual(self.output(),
                             "WurstStdlib2 install receipt: status=unverified reason=inspection-unavailable")
        with patch.object(receipt, "MAX_TRACKED_BYTES", 2):
            stream = io.StringIO()
            with redirect_stdout(stream):
                receipt._emit_installed_stdlib(self.compile)
            self.assertEqual(stream.getvalue().strip(),
                             "WurstStdlib2 install receipt: status=unverified reason=tracked-bytes-limit")


if __name__ == "__main__":
    unittest.main()
