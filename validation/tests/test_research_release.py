import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import research_release as release
from research_checkpoint import make_reference

NOW = datetime(2026, 10, 16, 19, tzinfo=timezone.utc)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "tools").mkdir()
        (self.root / "validation/tests").mkdir(parents=True)
        (self.root / "tools/demo.py").write_text("print('source')\n", encoding="utf-8")
        (self.root / "validation/tests/test_demo.py").write_text("pass\n", encoding="utf-8")
        (self.root / "validation").mkdir(exist_ok=True)
        self._save("validation/proof.txt", "dated validation evidence")
        self.review = self._save("validation/public-review.md", "Independent engineering review")
        self.disposition = self._save("monitoring/cases/disposition.json", "synthetic case record")
        self.inventory = self._save("validation/inventory.json", {
            "source_brief": self._save("planning/brief.md", "Preserved requirement source."),
            "requirements": [
                {"id": f"REQ-{i:03}", "required_for_software_acceptance": i < 418}
                for i in range(419)
            ],
        })
        self.assessment = self._assessment()
        self._save("monitoring/research-engine/requirements/current.json", {"assessment": self.assessment})
        (self.root / release.POINTER).parent.mkdir(parents=True, exist_ok=True)
        self._save(release.POINTER, {"assessment": self.assessment})

    def _save(self, path, value):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(value, str):
            target.write_text(value, encoding="utf-8")
        else:
            target.write_text(json.dumps(value, separators=(",", ":")), encoding="utf-8")
        return make_reference(self.root, path)

    def _assessment(self, status="verified"):
        rows = [{"id": f"REQ-{i:03}", "status": status if i < 418 else "deferred",
                 "evidence": [self.proof]}
                for i in range(419)]
        return self._save("validation/assessment.json", {
            "schema_version": 1, "created_at": "2026-10-16T18:00:00Z",
            "inventory": self.inventory,
            "source_brief": json.loads((self.root / self.inventory["path"]).read_text(encoding="utf-8"))["source_brief"],
            "requirements": rows,
        })

    @property
    def proof(self):
        return make_reference(self.root, "validation/proof.txt")

    def _record(self, **overrides):
        code = [make_reference(self.root, p) for p in release._source_files(self.root)]
        record = {
            "schema_version": 1, "id": "release-001", "created_at": "2026-10-16T18:30:00Z",
            "code_files": code, "requirements": self.assessment,
            "disposition": self.disposition, "engineering_review": self.review,
            "limitations": ["Engineering fixture; no real research-cycle claim."],
        }
        record.update(overrides)
        ref = self._save("validation/release.json", record)
        self._save(release.POINTER, {"assessment": ref})
        return ref

    def _case(self, status="independently-reviewed", disposition="supported"):
        return {"review_status": status, "research_disposition": disposition}

    def test_vendor_subtree_is_pruned_before_traversal_but_nested_owned_code_is_bound(self):
        vendor = self.root / "tools/node_modules"
        (vendor / "package/nested").mkdir(parents=True)
        (vendor / "package/vendor.py").write_text("external dependency bytes")
        (vendor / "package/nested/vendor.ps1").write_text("external dependency script")
        (self.root / "tools/owned/nested").mkdir(parents=True)
        owned = self.root / "tools/owned/nested/worker.py"
        owned.write_text("owned worker")
        (self.root / "tools/owned/nested/check.ps1").write_text("owned check")
        (self.root / "validation/tests/nested").mkdir()
        (self.root / "validation/tests/nested/test_owned.py").write_text("pass")
        real_scandir = release.os.scandir
        def guarded_scandir(path):
            self.assertFalse(Path(path).is_relative_to(vendor), "Vendor dependency subtree must never be traversed")
            return real_scandir(path)
        with patch.object(release.os, "scandir", side_effect=guarded_scandir):
            paths = release._source_files(self.root)
            self.assertEqual(paths, sorted(["tools/demo.py", "tools/owned/nested/check.ps1",
                "tools/owned/nested/worker.py", "validation/tests/nested/test_owned.py",
                "validation/tests/test_demo.py"]))
            self._record()
            with patch.object(release, "project_case", return_value=self._case()):
                self.assertEqual(release.project_release(self.root, now=NOW)["software_completion"], "complete")
                owned.write_text("tampered nested owned worker")
                self.assertEqual(release.project_release(self.root, now=NOW)["software_completion"], "blocked")

    def test_nonvendor_junction_and_escape_are_rejected_before_descent(self):
        unsafe = self.root / "tools/linked"
        unsafe.mkdir()
        (unsafe / "external.py").write_text("must not be traversed")
        original_scandir = release.os.scandir
        original_resolve = Path.resolve
        original_junction = Path.is_junction
        entered = []
        def guarded_scandir(path):
            self.assertNotEqual(Path(path), unsafe, "Unsafe directory was traversed before rejection")
            entered.append(Path(path))
            return original_scandir(path)
        def junction(path):
            return path == unsafe or original_junction(path)
        def escaping(path, *args, **kwargs):
            return self.root.parent / "synthetic-external-source" if path == unsafe else original_resolve(path, *args, **kwargs)
        with patch.object(release.os, "scandir", side_effect=guarded_scandir):
            with patch.object(Path, "is_junction", junction):
                with self.assertRaisesRegex(ValueError, "junction"):
                    release._source_files(self.root)
            with patch.object(Path, "resolve", escaping):
                with self.assertRaisesRegex(ValueError, "escapes project"):
                    release._source_files(self.root)
        self.assertNotIn(unsafe, entered)

    def test_nonvendor_symlink_file_is_rejected_before_binding(self):
        source = self.root / "tools/demo.py"
        original = Path.is_symlink
        def symlink(path):
            return path == source or original(path)
        with patch.object(Path, "is_symlink", symlink):
            with self.assertRaisesRegex(ValueError, "symlink"):
                release._source_files(self.root)

    def test_expired_research_gate_cannot_support_software_release(self):
        self._record()
        case=self._case()
        case['gates']=[{'gate':'research','status':'invalidated'}]
        with patch.object(release,'project_case',return_value=case):
            self.assertEqual(release.project_release(self.root,now=NOW)['software_completion'],'blocked')

    def test_backdated_release_cannot_use_later_requirement_assessment(self):
        self._record(created_at='2026-10-16T17:59:00Z')
        with patch.object(release,'project_case',return_value=self._case()):
            self.assertEqual(release.project_release(self.root,now=NOW)['software_completion'],'blocked')

    def test_real_inventory_extra_brief_metadata_is_preserved(self):
        inventory=json.loads((self.root/self.inventory['path']).read_text(encoding='utf-8'))
        inventory['source_brief']['line_count']=625
        self.inventory=self._save(self.inventory['path'],inventory)
        assessment=json.loads((self.root/self.assessment['path']).read_text(encoding='utf-8'))
        assessment['inventory']=self.inventory
        self.assessment=self._save(self.assessment['path'],assessment)
        self._save('monitoring/research-engine/requirements/current.json',{'assessment':self.assessment})
        self._record()
        with patch.object(release,'project_case',return_value=self._case()):
            self.assertEqual(release.project_release(self.root,now=NOW)['software_completion'],'complete')

    def test_absent_public_pointer_remains_in_progress(self):
        (self.root / release.POINTER).unlink()
        result = release.project_release(self.root, now=NOW)
        self.assertEqual(result["software_completion"], "in progress")

    def test_malformed_and_future_release_are_blocked_safely(self):
        for record in ({"schema_version": 2}, {"schema_version": 1, "id": "future",
                "created_at": "2026-10-17T00:00:00Z"}):
            with self.subTest(record=record):
                ref = self._save("validation/release.json", record)
                self._save(release.POINTER, {"assessment": ref})
                result = release.project_release(self.root, now=NOW)
                self.assertEqual(result["software_completion"], "blocked")
                self.assertNotIn(str(self.root), result["status_explanation"])

    def test_code_omission_and_tampering_block_release(self):
        code = [make_reference(self.root, p) for p in release._source_files(self.root)]
        with patch.object(release, "project_case", return_value=self._case()):
            self._record(code_files=code[:-1])
            self.assertEqual(release.project_release(self.root, now=NOW)["software_completion"], "blocked")
            self._record(code_files=code)
            (self.root / "tools/demo.py").write_text("changed\n", encoding="utf-8")
            self.assertEqual(release.project_release(self.root, now=NOW)["software_completion"], "blocked")

    def test_incomplete_required_item_and_stale_requirements_pointer_block(self):
        rows = json.loads((self.root / self.assessment["path"]).read_text(encoding="utf-8"))["requirements"]
        rows[0]["status"] = "not-assessed"
        bad = self._save("validation/incomplete.json", {
            "schema_version": 1, "created_at": "2026-10-16T18:00:00Z",
            "inventory": self.inventory,
            "source_brief": json.loads((self.root / self.inventory["path"]).read_text(encoding="utf-8"))["source_brief"],
            "requirements": rows,
        })
        self._save("monitoring/research-engine/requirements/current.json", {"assessment": bad})
        self._record(requirements=bad)
        with patch.object(release, "project_case", return_value=self._case()):
            self.assertEqual(release.project_release(self.root, now=NOW)["software_completion"], "blocked")
            (self.root / release.POINTER).unlink()
            self._save(release.POINTER, {"assessment": self.assessment})
            self._record(requirements=bad)
            self.assertEqual(release.project_release(self.root, now=NOW)["software_completion"], "blocked")

    def test_fixture_or_invalid_case_never_accepts(self):
        self._record()
        for projection in (self._case("fixture-only"), self._case("invalidated"),
                           self._case(disposition="active")):
            with self.subTest(projection=projection), patch.object(release, "project_case", return_value=projection):
                self.assertEqual(release.project_release(self.root, now=NOW)["software_completion"], "blocked")

    def test_changed_engineering_review_invalidates_release(self):
        ref = self._record()
        with patch.object(release, "project_case", return_value=self._case()):
            self.assertEqual(release.project_release(self.root, now=NOW)["software_completion"], "complete")
            (self.root / self.review["path"]).write_text("changed", encoding="utf-8")
            self.assertEqual(release.project_release(self.root, now=NOW)["software_completion"], "blocked")

    def test_positive_engineering_control_is_software_only(self):
        self._record()
        with patch.object(release, "project_case", return_value=self._case()):
            result = release.project_release(self.root, now=NOW)
        self.assertEqual(result["software_completion"], "complete")
        self.assertFalse(result["authoritative"])
        self.assertNotIn("trade_readiness", result)
        self.assertNotIn("activation", result)


if __name__ == "__main__":
    unittest.main()
