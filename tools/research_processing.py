"""Public, replayable formatting provenance; not an analytical approval."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path

FIELDS = {"receipt", "raw_output", "failure_projection", "events"}


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _stamp(value):
    if not isinstance(value, str):
        raise ValueError("Processing timestamp missing")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Processing timestamp must include timezone")
    return stamp


def processing_context(root, binding, target_bytes, *, execution=None, now=None):
    """Verify published bytes and replay only the permitted reference repair.

    The private metadata digest is an attributed local audit anchor. Public
    files cannot independently establish its contents or a backend identity.
    Paths are deliberately excluded from model-visible processing context.
    """
    try:
        from .scoped_research_adapter import _file, _no_credentials, MODELS
        from .research_output import normalize_issue_references
        from .scoped_research_queue import _validate_sanitized_events
    except ImportError:
        from scoped_research_adapter import _file, _no_credentials, MODELS
        from research_output import normalize_issue_references
        from scoped_research_queue import _validate_sanitized_events
    root = Path(root).resolve()
    if not isinstance(binding, dict) or set(binding) != FIELDS:
        raise ValueError("Exact explicit processing references required")
    documents, manifest, hashes = {}, {}, {}
    for key, ref in binding.items():
        if not isinstance(ref, dict) or set(ref) != {"path", "sha256"}:
            raise ValueError("Exact processing artifact reference required")
        if not isinstance(ref["path"], str) or not ref["path"].startswith(("monitoring/research-engine/cases/", "validation/")):
            raise ValueError("Processing evidence must be a public research artifact")
        path = _file(root, ref)
        if path.stat().st_size > 2_000_000:
            raise ValueError("Processing artifact exceeds byte limit")
        data = path.read_bytes()
        if _hash(data) != ref["sha256"]:
            raise ValueError("Processing bytes changed during read")
        documents[key] = json.loads(data.decode("utf-8"))
        _no_credentials(documents[key])
        manifest[str(path)] = hashes[key] = _hash(data)
    receipt, failure = documents["receipt"], documents["failure_projection"]
    if not isinstance(receipt, dict) or not isinstance(failure, dict):
        raise ValueError("Processing receipt or failure projection malformed")
    expected = {"raw_output_sha256": hashes["raw_output"],
        "failure_projection_sha256": hashes["failure_projection"],
        "events_sha256": hashes["events"], "processed_result_sha256": _hash(target_bytes),
        "algorithm_sha256": _hash(Path(__file__).with_name("research_output.py").read_bytes())}
    if receipt.get("schema_version") != 1 or any(receipt.get(k) != v for k, v in expected.items()):
        raise ValueError("Public processing receipt binding differs")
    for key in ('failure_metadata_sha256', 'target_sha256', 'packet_sha256', 'input_manifest_sha256'):
        if not isinstance(receipt.get(key), str) or not re.fullmatch('[0-9a-f]{64}', receipt[key]):
            raise ValueError('Processing receipt lacks required input hashes')
    staged = receipt.get('staged_input_manifest')
    if (not isinstance(staged, dict) or set(staged) != {'packet.json','schema.json','model_catalog.json'} or
            any(not isinstance(v,str) or not re.fullmatch('[0-9a-f]{64}',v) for v in staged.values()) or
            staged['packet.json'] != receipt['packet_sha256']):
        raise ValueError('Processing staged input hashes differ')
    for key in ("job_id", "dispatch_id", "attempt", "role"):
        if receipt.get(key) != failure.get(key):
            raise ValueError("Processing failure identity differs")
    if (failure.get("role") not in MODELS or receipt.get("model") != MODELS[failure["role"]] or
            failure.get("model_requested") != receipt["model"] or
            failure.get("authentication") != "chatgpt-subscription" or
            failure.get("reasoning_effort") != "high" or failure.get("speed") != "standard" or
            failure.get("returncode") != 0 or failure.get("selected_route_completed") is not False or
            failure.get("reason") != "invalid-output-input-or-unauthorized-event" or
            failure.get("validation_stage") != "output-schema-and-provenance" or
            failure.get("actual_model") not in {None, receipt["model"]} or
            failure.get("backend_independently_verified") is not False or
            failure.get("unaccepted_output_sha256") != hashes["raw_output"] or
            failure.get("original_private_metadata_sha256") != receipt.get("failure_metadata_sha256")):
        raise ValueError("Public original failure route or provenance differs")
    live = failure.get('engineering_test') is False and failure.get('runtime_verified_live') is True
    fixture = (failure.get('engineering_test') is True and failure.get('runtime_verified_live') is False and
               failure.get('actual_model') is None and failure.get('models_observed') == [])
    if not (live or fixture) or receipt.get('engineering_fixture_only', False) is not fixture:
        raise ValueError('Public processing fixture or runtime flags differ')
    if type(receipt.get("attempt")) is not int or not 1 <= receipt["attempt"] <= 4 or not receipt.get("dispatch_id"):
        raise ValueError("Invalid processing attempt or dispatch")
    for key in ("target_sha256", "packet_sha256", "input_manifest_sha256", "staged_input_manifest"):
        if receipt.get(key) != failure.get(key):
            raise ValueError("Processing input provenance differs")
    normalized, edits = normalize_issue_references(documents["raw_output"])
    if not edits['edits'] or receipt.get("normalization") != edits or normalized != json.loads(target_bytes.decode("utf-8")):
        raise ValueError("Published result differs from permitted deterministic repair")
    reported = failure.get('actual_model')
    if (failure.get('actual_model_verification') != ('reported' if reported else 'not-reported') or
            failure.get('models_observed') != ([reported] if reported else [])):
        raise ValueError('Public model reporting fields differ')
    usage = _validate_sanitized_events(documents["events"])
    normalized_at = _stamp(receipt.get("normalization_timestamp"))
    if not (_stamp(failure.get("started_at")) <= _stamp(failure.get("completed_at")) <= normalized_at <=
            (now or datetime.now(timezone.utc))):
        raise ValueError("Processing chronology differs")
    if execution is not None:
        for key in ("job_id", "dispatch_id", "attempt", "role", "model_requested", "authentication",
                    "reasoning_effort", "speed", "actual_model", "actual_model_verification", "models_observed",
                    "backend_independently_verified", "started_at", "completed_at", "engineering_test", "runtime_verified_live",
                    "target_sha256", "packet_sha256", "packet_utf8_bytes", "original_bytes", "prompt_sha256", "prompt_utf8_bytes"):
            if execution.get(key) != failure.get(key):
                raise ValueError("Processed execution changed original route facts")
        if (execution.get("normalization_timestamp") != receipt["normalization_timestamp"] or
                execution.get("output_sha256") != _hash(target_bytes) or execution.get("usage") != usage):
            raise ValueError("Processed execution receipt or usage differs")
    return {"context": {"kind": "deterministic-reference-formatting-only", "engineering_fixture_only": fixture, "artifact_hashes": hashes,
                "artifacts": {key: documents[key] for key in ('receipt','failure_projection')},
                "usage": usage, "limitations": [
                    "Processing context is not citable issuer evidence or analytical approval.",
                    "Raw output and sanitized events remain explicitly hash-bound and locally replayed; their full bytes are omitted from model context to avoid duplicating the target.",
                    "Private metadata contents, dispatch authority and backend identity are not independently proven by these public projections."]},
            "input_manifest": manifest}
