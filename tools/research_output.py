"""Conservative normalization for a narrow worker-output reference defect.

This module does not validate or approve research output. Callers must retain
the original object and run the unchanged strict validator on the normalized
copy before any further use.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re


_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}\Z")


def _canonical_sha256(value):
    try:
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("Output is not canonical JSON data") from exc
    return hashlib.sha256(payload).hexdigest()


def _pointer_token(value):
    return str(value).replace("~", "~0").replace("/", "~1")


def _require_object(value, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")


def _require_id(value, label):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError(f"{label} must be a stable simple ID")


def normalize_issue_references(result):
    """Return a deep-copied output with only safe issue-reference repairs.

    Repairs are limited to blocker strings exactly shaped as ``ID: label``
    where ``ID`` exists in findings/gaps, and missing backlinks for an
    existing material unresolved issue whose existing target is already
    withheld. The original object is never mutated.
    """
    _require_object(result, "Output")
    raw_hash = _canonical_sha256(result)
    normalized = copy.deepcopy(result)

    for key in ("findings", "gaps", "conclusions"):
        if not isinstance(normalized.get(key), list):
            raise ValueError(f"{key} must be an array")

    conclusions = {}
    for index, conclusion in enumerate(normalized["conclusions"]):
        _require_object(conclusion, f"Conclusion at index {index}")
        ident = conclusion.get("id")
        _require_id(ident, "Conclusion ID")
        if ident in conclusions:
            raise ValueError("Duplicate conclusion IDs")
        if conclusion.get("status") not in {"supported", "withheld"}:
            raise ValueError("Malformed conclusion status")
        blockers = conclusion.get("blocking_issues")
        if not isinstance(blockers, list) or any(not isinstance(x, str) for x in blockers):
            raise ValueError("Conclusion blocking_issues must be an array of strings")
        conclusions[ident] = conclusion

    issues = []
    seen_issue_ids = set()
    for section in ("findings", "gaps"):
        for index, issue in enumerate(normalized[section]):
            _require_object(issue, f"{section} item at index {index}")
            ident = issue.get("id")
            _require_id(ident, "Issue ID")
            if ident in seen_issue_ids:
                raise ValueError("Duplicate issue IDs")
            seen_issue_ids.add(ident)
            targets = issue.get("affected_conclusions")
            if not isinstance(targets, list) or any(not isinstance(x, str) for x in targets):
                raise ValueError("Issue affected_conclusions must be an array of strings")
            if len(targets) != len(set(targets)):
                raise ValueError("Duplicate affected conclusion IDs")
            if any(target not in conclusions for target in targets):
                raise ValueError("Issue references unknown conclusion")
            if section == "findings":
                if issue.get("severity") not in {"minor", "material"} or issue.get("outcome") not in {"unresolved", "resolved", "withheld"}:
                    raise ValueError("Malformed finding materiality or outcome")
                material_unresolved = issue["severity"] == "material" and issue["outcome"] != "resolved"
            else:
                if not isinstance(issue.get("material"), bool):
                    raise ValueError("Malformed gap materiality")
                material_unresolved = issue["material"]
            issues.append((section, index, issue, material_unresolved))

    # A blocker must identify one existing issue. Parsing is exact and
    # anchored, so prefix collisions and arbitrary label text cannot guess IDs.
    edits = []
    for index, conclusion in enumerate(normalized["conclusions"]):
        blockers = conclusion["blocking_issues"]
        canonical = []
        for offset, value in enumerate(blockers):
            if value in seen_issue_ids:
                ident = value
            else:
                matches = [issue_id for issue_id in seen_issue_ids
                           if value.startswith(issue_id + ": ") and
                           value[len(issue_id) + 2:].strip()]
                if len(matches) != 1:
                    raise ValueError("Unknown or ambiguous blocking issue reference")
                ident = matches[0]
                pointer = f"/conclusions/{index}/blocking_issues/{offset}"
                edits.append({"pointer": pointer, "before": value, "after": ident,
                              "reason": "Exact known issue ID followed by a nonempty ': ' label."})
            canonical.append(ident)
        if len(canonical) != len(set(canonical)):
            raise ValueError("Duplicate blocking issue references")
        conclusion["blocking_issues"] = canonical

    # Derive only the reverse edge already stated by an issue's affected list.
    for section, issue_index, issue, material_unresolved in issues:
        if not material_unresolved:
            continue
        for target_id in issue["affected_conclusions"]:
            conclusion_index = next(i for i, c in enumerate(normalized["conclusions"])
                                    if c["id"] == target_id)
            conclusion = normalized["conclusions"][conclusion_index]
            if conclusion["status"] == "supported":
                raise ValueError("Material unresolved issue targets a supported conclusion")
            blockers = conclusion["blocking_issues"]
            if issue["id"] not in blockers:
                blockers.append(issue["id"])
                pointer = f"/conclusions/{conclusion_index}/blocking_issues/{len(blockers) - 1}"
                edits.append({"pointer": pointer, "before": None, "after": issue["id"],
                              "reason": "Existing material unresolved issue names this already-withheld conclusion."})

    processed_hash = _canonical_sha256(normalized)
    receipt = {
        "schema_version": 1,
        "edits": edits,
        "canonical_raw_sha256": raw_hash,
        "canonical_processed_sha256": processed_hash,
        "exact_raw_byte_sha256": None,
        "limitations": [
            "Canonical JSON hashes identify parsed objects; exact source-byte hashing requires the caller to retain and hash the original bytes.",
            "This helper does not certify schema, provenance, analytical validity, readiness, or approval.",
            "The normalized copy must pass the unchanged strict validator before use.",
        ],
    }
    return normalized, receipt
