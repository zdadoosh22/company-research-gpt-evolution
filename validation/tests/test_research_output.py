import copy
import hashlib
import json
import unittest

from tools.research_output import normalize_issue_references


def sample_output():
    return {
        "status": "partial",
        "summary": "Bounded fixture.",
        "sources": [{"source_id": "src1", "location": "p. 1", "extra": {"keep": True}}],
        "coverage": [],
        "findings": [{
            "id": "G1", "severity": "material", "claim": "Unresolved fixture issue",
            "evidence": [], "proposed_correction": "Withhold the conclusion",
            "outcome": "unresolved", "affected_conclusions": ["C1"],
        }],
        "gaps": [],
        "conclusions": [{
            "id": "C1", "claim": "Fixture conclusion", "status": "withheld",
            "evidence": [], "blocking_issues": [], "numerical_inputs": [],
        }],
        "continuation": "Strict revalidation required.",
    }


class ResearchOutputNormalizerTests(unittest.TestCase):
    def test_labelled_known_id_is_repaired_on_copy_only(self):
        raw = sample_output()
        raw["conclusions"][0]["blocking_issues"] = ["G1: explanation from model"]
        before = copy.deepcopy(raw)
        expected = copy.deepcopy(raw)
        expected["conclusions"][0]["blocking_issues"] = ["G1"]

        normalized, receipt = normalize_issue_references(raw)

        self.assertEqual(raw, before)
        self.assertIsNot(normalized, raw)
        self.assertIsNot(normalized["sources"], raw["sources"])
        self.assertEqual(normalized, expected)
        self.assertEqual(normalized["conclusions"][0]["blocking_issues"], ["G1"])
        self.assertEqual(normalized["status"], raw["status"])
        self.assertEqual(normalized["findings"], raw["findings"])
        self.assertEqual(normalized["sources"], raw["sources"])
        self.assertEqual(receipt["edits"], [{
            "pointer": "/conclusions/0/blocking_issues/0",
            "before": "G1: explanation from model", "after": "G1",
            "reason": "Exact known issue ID followed by a nonempty ': ' label.",
        }])
        self.assertEqual(receipt["canonical_raw_sha256"], hashlib.sha256(
            json.dumps(before, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        ).hexdigest())
        self.assertNotEqual(receipt["canonical_raw_sha256"], receipt["canonical_processed_sha256"])
        self.assertIsNone(receipt["exact_raw_byte_sha256"])
        self.assertTrue(any("unchanged strict validator" in x for x in receipt["limitations"]))

    def test_prefix_collision_uses_exact_known_id(self):
        raw = sample_output()
        raw["findings"].append({
            "id": "G10", "severity": "minor", "claim": "Separate issue",
            "evidence": [], "proposed_correction": "Review separately",
            "outcome": "unresolved", "affected_conclusions": [],
        })
        raw["conclusions"][0]["blocking_issues"] = ["G10: exact longer ID"]

        normalized, receipt = normalize_issue_references(raw)

        self.assertEqual(normalized["conclusions"][0]["blocking_issues"], ["G10", "G1"])
        self.assertEqual(receipt["edits"][0]["after"], "G10")
        self.assertEqual(receipt["edits"][1]["after"], "G1")

    def test_unknown_labels_and_duplicate_ids_fail_closed(self):
        for mutate in (
            lambda x: x["conclusions"][0].update(blocking_issues=["g1: wrong case"]),
            lambda x: x["conclusions"][0].update(blocking_issues=["G1: "]),
            lambda x: x["conclusions"][0].update(blocking_issues=["G2"]),
            lambda x: x["findings"].append(copy.deepcopy(x["findings"][0])),
            lambda x: x["conclusions"].append(copy.deepcopy(x["conclusions"][0])),
        ):
            with self.subTest(mutate=mutate):
                raw = sample_output()
                mutate(raw)
                with self.assertRaises(ValueError):
                    normalize_issue_references(raw)

    def test_supported_affected_conclusion_is_never_downgraded_or_rewritten(self):
        raw = sample_output()
        raw["conclusions"][0]["status"] = "supported"
        before = copy.deepcopy(raw)

        with self.assertRaisesRegex(ValueError, "supported conclusion"):
            normalize_issue_references(raw)

        self.assertEqual(raw, before)

    def test_only_existing_material_unresolved_edge_gets_backlink(self):
        raw = sample_output()
        raw["findings"].append({
            "id": "F2", "severity": "material", "claim": "Resolved issue",
            "evidence": [], "proposed_correction": "Resolved with evidence",
            "outcome": "resolved", "affected_conclusions": ["C1"],
        })
        raw["gaps"].append({
            "id": "G3", "description": "Material gap", "material": True,
            "affected_conclusions": ["C1"],
        })
        raw["gaps"].append({
            "id": "G4", "description": "Nonmaterial gap", "material": False,
            "affected_conclusions": ["C1"],
        })

        normalized, receipt = normalize_issue_references(raw)

        self.assertEqual(normalized["conclusions"][0]["status"], "withheld")
        self.assertEqual(normalized["conclusions"][0]["blocking_issues"], ["G1", "G3"])
        self.assertEqual([e["after"] for e in receipt["edits"]], ["G1", "G3"])
        self.assertEqual([e["reason"] for e in receipt["edits"]], [
            "Existing material unresolved issue names this already-withheld conclusion.",
            "Existing material unresolved issue names this already-withheld conclusion.",
        ])

    def test_noop_has_zero_edits_and_equal_canonical_hashes(self):
        raw = sample_output()
        raw["conclusions"][0]["blocking_issues"] = ["G1"]

        normalized, receipt = normalize_issue_references(raw)

        self.assertEqual(normalized, raw)
        self.assertEqual(receipt["edits"], [])
        self.assertEqual(receipt["canonical_raw_sha256"], receipt["canonical_processed_sha256"])

    def test_nondict_and_malformed_structure_are_rejected(self):
        for raw in (None, [], {"findings": [], "gaps": [], "conclusions": {}}):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                normalize_issue_references(raw)

    def test_unrelated_extra_source_fields_survive_for_strict_validator(self):
        raw = sample_output()
        raw["sources"][0]["unexpected_validator_field"] = {"x": [1, 2]}

        normalized, _ = normalize_issue_references(raw)

        self.assertEqual(normalized["sources"], raw["sources"])
        self.assertIn("unexpected_validator_field", normalized["sources"][0])


if __name__ == "__main__":
    unittest.main()
