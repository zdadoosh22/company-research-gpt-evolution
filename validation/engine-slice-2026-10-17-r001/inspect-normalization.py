"""Read-only candidate inspection. Never updates a queue or accepted result."""
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.research_output import normalize_issue_references
from tools.scoped_research_adapter import validate_output

HERE = Path(__file__).resolve().parent
raw_path = HERE / "REAL-CALL3-UNACCEPTED-OUTPUT.json"
job_path = ROOT / "monitoring/research-engine/cases/amd-helion-20261017-r001/inputs/analysis-job-r002.json"
raw_bytes = raw_path.read_bytes()
raw = json.loads(raw_bytes)
before = copy.deepcopy(raw)
job = json.loads(job_path.read_text(encoding="utf-8"))
try:
    validate_output(copy.deepcopy(raw), job, ROOT)
except ValueError as exc:
    raw_failure = str(exc)
else:
    raise AssertionError("Original candidate unexpectedly accepted")
normalized, receipt = normalize_issue_references(raw)
validate_output(normalized, job, ROOT)
assert raw == before and raw_path.read_bytes() == raw_bytes
without_blockers = lambda obj: {
    **obj, "conclusions": [{k: v for k, v in c.items() if k != "blocking_issues"}
                           for c in obj["conclusions"]]}
assert without_blockers(raw) == without_blockers(normalized)
again, no_op = normalize_issue_references(normalized)
assert again == normalized and no_op["edits"] == []
receipt["exact_raw_byte_sha256"] = hashlib.sha256(raw_bytes).hexdigest()
receipt.update({
    "inspection_only": True,
    "raw_validation_failure": raw_failure,
    "processed_strict_validation": "passed in memory only",
    "unchanged_except_blocking_issues": True,
    "idempotent": True,
    "accepted_result_written": False,
    "queue_modified": False,
    "model_calls": 0,
    "job_sha256": hashlib.sha256(job_path.read_bytes()).hexdigest(),
    "helper_sha256": hashlib.sha256((ROOT / "tools/research_output.py").read_bytes()).hexdigest(),
    "remaining_work": "Explicit revalidation, immutable failure lineage, recovery and exported review provenance require implementation and verification before any acceptance.",
})
print(json.dumps(receipt, ensure_ascii=False, indent=2))
