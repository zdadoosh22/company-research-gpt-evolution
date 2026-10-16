"""Version-bound software release assessment; never enables live gates."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re

try:
    from .research_checkpoint import (artifact_path, make_reference, requirements_snapshot,
        sha256, timestamp, verify_reference)
    from .research_records import project_case
except ImportError:
    from research_checkpoint import (artifact_path, make_reference, requirements_snapshot,
        sha256, timestamp, verify_reference)
    from research_records import project_case

POINTER = "monitoring/research-engine/releases/current.json"
REQUIRED_RELEASE_FIELDS = {"schema_version", "id", "created_at", "code_files",
    "requirements", "disposition", "engineering_review", "limitations"}
SAFE_FAILURE = "Release evidence is missing, stale, or invalid; software completion is unverified."


def _exact_ref(root, ref):
    if not isinstance(ref, dict) or set(ref) != {"path", "sha256"}:
        raise ValueError("Reference shape")
    verify_reference(root, ref)


def _source_files(root):
    paths = []
    for folder, suffixes in (("tools", (".py", ".ps1")), ("validation/tests", (".py",))):
        base = root / folder
        if base.exists():
            if base.is_symlink():
                raise ValueError("Source directory")
            for path in base.rglob("*"):
                if path.is_symlink():
                    raise ValueError("Source symlink")
                if path.is_file() and path.suffix in suffixes:
                    paths.append(path.relative_to(root).as_posix())
    return sorted(paths)


def _validate_requirements(root, ref, now):
    _exact_ref(root, ref)
    snapshot = requirements_snapshot(root, now=now)
    if snapshot.get("status") != "dated-assessment" or snapshot.get("assessment") != ref:
        raise ValueError("Assessment is not current")
    assessment = json.loads(verify_reference(root, ref).read_text(encoding="utf-8"))
    inventory_ref = assessment.get("inventory")
    _exact_ref(root, inventory_ref)
    inventory = json.loads(verify_reference(root, inventory_ref).read_text(encoding="utf-8"))
    brief_ref = assessment.get("source_brief")
    original_brief = inventory.get("source_brief", {})
    bound_brief = {key: original_brief.get(key) for key in ("path", "sha256")} if isinstance(original_brief, dict) else None
    if not isinstance(brief_ref, dict) or brief_ref != bound_brief:
        raise ValueError("Source brief binding")
    _exact_ref(root, brief_ref)
    original = inventory.get("requirements")
    rows = assessment.get("requirements")
    if not isinstance(original, list) or len(original) != 419 or not isinstance(rows, list):
        raise ValueError("Requirement inventory size")
    original_ids = [row.get("id") for row in original if isinstance(row, dict)]
    if len(original_ids) != 419 or len(set(original_ids)) != 419:
        raise ValueError("Requirement identity set")
    by_id = {row["id"]: row for row in original}
    if len(rows) != 419 or any(not isinstance(row, dict) for row in rows):
        raise ValueError("Assessment coverage")
    entries = {row.get("id"): row for row in rows}
    if len(entries) != 419 or set(entries) != set(by_id):
        raise ValueError("Assessment identity set")
    statuses = {"verified", "implemented-fixture-tested"}
    for req_id, source in by_id.items():
        row = entries[req_id]
        state = row.get("status")
        if type(source.get("required_for_software_acceptance")) is not bool:
            raise ValueError("Requirement applicability")
        if source["required_for_software_acceptance"]:
            if state not in statuses:
                raise ValueError("Required item incomplete")
        elif state not in statuses | {"deferred"}:
            raise ValueError("Optional item unresolved")
        evidence = row.get("evidence")
        if not isinstance(evidence, list) or (state != "not-assessed" and not evidence):
            raise ValueError("Requirement evidence missing")
        for evidence_ref in evidence:
            _exact_ref(root, evidence_ref)


def _validate_case(root, ref, now):
    _exact_ref(root, ref)
    case = project_case(root, ref, now=now)
    if (case.get("review_status") != "independently-reviewed" or
            case.get("research_disposition") not in {"supported", "rejected", "parked"} or
            any(g.get("status") == "invalidated" for g in case.get("gates", []) if g.get("gate") in {"research", "dossier"})):
        raise ValueError("Case review is not current and independent")


def project_release(root, *, now=None):
    """Return software completion evidence only; all non-software gates stay outside scope."""
    root = Path(root).resolve()
    now = now or datetime.now(timezone.utc)
    pending = {"software_completion": "in progress", "status_explanation":
        "No public release assessment is selected; software acceptance remains unproven.",
        "reason": "No public release assessment is selected; software acceptance remains unproven.",
        "authoritative": False, "evidence": [], "limitations": [
            "This projection evaluates software completion only and grants no live or trading authority."]}
    pointer = root / POINTER
    if not pointer.exists():
        return pending
    try:
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise ValueError("Current time")
        selected = json.loads(artifact_path(root, POINTER).read_text(encoding="utf-8"))
        if not isinstance(selected, dict) or set(selected) != {"assessment"}:
            raise ValueError("Pointer shape")
        record_ref = selected["assessment"]
        _exact_ref(root, record_ref)
        record = json.loads(verify_reference(root, record_ref).read_text(encoding="utf-8"))
        if (not isinstance(record, dict) or set(record) != REQUIRED_RELEASE_FIELDS or
                type(record.get("schema_version")) is not int or record["schema_version"] != 1 or
                not isinstance(record.get("id"), str) or not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,119}", record["id"])):
            raise ValueError("Release schema")
        created = timestamp(record["created_at"])
        if created > now:
            raise ValueError("Future release")
        if not isinstance(record["limitations"], list) or any(not isinstance(x, str) or not x.strip() for x in record["limitations"]):
            raise ValueError("Limitations")
        files = record["code_files"]
        if not isinstance(files, list) or any(not isinstance(ref, dict) for ref in files):
            raise ValueError("Source manifest")
        expected = _source_files(root)
        actual = [ref.get("path") for ref in files]
        if not expected or actual != expected or len(set(actual)) != len(actual):
            raise ValueError("Source manifest does not match checkout")
        for ref in files:
            _exact_ref(root, ref)
        _validate_requirements(root, record["requirements"], created)
        _validate_case(root, record["disposition"], created)
        _validate_case(root, record["disposition"], now)
        review = record["engineering_review"]
        if not isinstance(review, dict) or not isinstance(review.get("path"), str) or not review["path"].endswith(".md"):
            raise ValueError("Review reference")
        _exact_ref(root, review)
        return {"software_completion": "complete", "status_explanation":
            "The current source snapshot, requirement assessment, independently reviewed case, and engineering review all validate.",
            "reason": "The current source snapshot, requirement assessment, independently reviewed case, and engineering review all validate.",
            "authoritative": False, "evidence": [record_ref], "limitations":
            record["limitations"] + ["Software completion does not establish operational readiness, trade readiness, edge evidence, or activation."]}
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError):
        return {"software_completion": "blocked", "status_explanation": SAFE_FAILURE,
            "reason": SAFE_FAILURE,
            "authoritative": False, "evidence": [], "limitations":
            ["A supplied release assessment failed current validation.",
             "This projection evaluates software completion only and grants no live or trading authority."]}
