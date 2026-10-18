"""Explicit project turn checkpoints and a rebuildable, non-authoritative view.

No model calls, live account reads, trading acceptance, hooks or polling server.
The immutable event files are authoritative; state/research-engine is derived.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
from uuid import uuid4

try:
    from .alert_contract import GATES
    from .scoped_research_adapter import _no_credentials
except ImportError:
    from alert_contract import GATES
    from scoped_research_adapter import _no_credentials

SCHEMA_VERSION = 1
EVENT_DIRECTORY = "monitoring/research-engine/checkpoints"
ALLOWED_ARTIFACT_ROOTS = {"companies", "methodology", "monitoring", "validation",
                          "lessons", "planning", "tools", "workflows", "templates"}
ROOT_DOCUMENTS = {"AGENTS.md", "README.md", "REPOSITORY.md"}
FORBIDDEN_SUFFIXES = {".dpapi", ".sqlite", ".sqlite3", ".db", ".key", ".pem", ".pfx", ".p12"}
FIELDS = {"schema_version", "id", "task_id", "turn_id", "phase", "created_at",
          "observed_at", "origin", "request", "work", "outcome", "artifacts", "checks",
          "blockers", "readiness_impact", "verified_gate_changes", "next_action",
          "unknowns", "supersedes"}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Explicit timezone-aware timestamp required")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Timestamp timezone missing")
    return stamp.astimezone(timezone.utc)


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,119}", value):
        raise ValueError("Lowercase stable identifier required")
    return value


def _text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 20000:
        raise ValueError("Nonempty bounded text required")


def _strings(values):
    if not isinstance(values, list) or len(values) > 1000:
        raise ValueError("Bounded text list required")
    for value in values:
        _text(value)


def artifact_path(root, relative):
    """Resolve only explicitly referenced nonprivate project artifacts."""
    root = Path(root).resolve()
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise ValueError("Project-relative forward-slash artifact path required")
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or any(x.startswith(".") for x in rel.parts):
        raise ValueError("Escaping or hidden artifact rejected")
    if rel.parts[0] not in ALLOWED_ARTIFACT_ROOTS and relative not in ROOT_DOCUMENTS:
        raise ValueError("Artifact family is not allowlisted")
    if any(x.lower() in {"credentials", "secrets", "auth.json", "cookies.json", "token.json"} for x in rel.parts) or rel.suffix.lower() in FORBIDDEN_SUFFIXES:
        raise ValueError("Private artifact rejected")
    candidate = root
    for part in rel.parts:
        candidate /= part
        if candidate.is_symlink():
            raise ValueError("Symlink artifact rejected")
    target = candidate.resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise ValueError("Artifact missing or outside project")
    return target


def verify_reference(root, reference):
    if not isinstance(reference, dict) or set(reference) != {"path", "sha256"}:
        raise ValueError("Exact path/hash artifact reference required")
    if not isinstance(reference["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", reference["sha256"]):
        raise ValueError("Artifact SHA256 required")
    target = artifact_path(root, reference["path"])
    if sha256(target.read_bytes()) != reference["sha256"]:
        raise ValueError("Artifact hash changed")
    return target


def make_reference(root, relative):
    return {"path": relative, "sha256": sha256(artifact_path(root, relative).read_bytes())}


def validate_event(root, event, *, now=None, verify_artifacts=True):
    if not isinstance(event, dict) or set(event) != FIELDS or event["schema_version"] != 1 or isinstance(event["schema_version"], bool):
        raise ValueError("Checkpoint schema mismatch")
    _no_credentials(event)
    if len(canonical(event)) > 1_000_000:
        raise ValueError("Checkpoint exceeds byte bound")
    for field in ("id", "task_id", "turn_id"):
        identifier(event[field])
    if event["phase"] not in {"start", "complete"}:
        raise ValueError("Checkpoint phase required")
    current = now or datetime.now(timezone.utc)
    if not isinstance(current, datetime) or current.tzinfo is None:
        raise ValueError("Current time must be aware")
    if timestamp(event["created_at"]) > current or timestamp(event["observed_at"]) > current:
        raise ValueError("Future checkpoint rejected")
    if timestamp(event["observed_at"]) > timestamp(event["created_at"]):
        raise ValueError("Observation cannot follow record creation")
    for field in ("origin", "request", "next_action"):
        _text(event[field])
    for field in ("work", "unknowns", "supersedes"):
        _strings(event[field])
    if event["phase"] == "start":
        if event["outcome"] is not None or event["work"] or event["checks"]:
            raise ValueError("Start cannot claim completed work")
    elif event["outcome"] not in {"complete", "partial", "failed", "interrupted"}:
        raise ValueError("Completion outcome required")
    if not isinstance(event["artifacts"], list) or len(event["artifacts"]) > 1000:
        raise ValueError("Bounded artifact list required")
    paths = set()
    for ref in event["artifacts"]:
        if verify_artifacts:
            verify_reference(root, ref)
        elif not isinstance(ref, dict) or set(ref) != {"path", "sha256"}:
            raise ValueError("Malformed reference")
        if ref["path"] in paths:
            raise ValueError("Duplicate artifact reference")
        paths.add(ref["path"])
    if not isinstance(event["checks"], list):
        raise ValueError("Check records required")
    check_ids = set()
    for check in event["checks"]:
        if not isinstance(check, dict) or set(check) != {"id", "method", "outcome", "artifact_paths"}:
            raise ValueError("Check record shape differs")
        identifier(check["id"])
        _text(check["method"])
        if check["id"] in check_ids or check["outcome"] not in {"passed", "failed", "not-run", "unavailable"}:
            raise ValueError("Invalid check identity/outcome")
        check_ids.add(check["id"])
        _strings(check["artifact_paths"])
        if not set(check["artifact_paths"]).issubset(paths) or (check["outcome"] in {"passed", "failed"} and not check["artifact_paths"]):
            raise ValueError("Executed check requires bound evidence")
    if not isinstance(event["blockers"], dict) or set(event["blockers"]) != {"resolved", "introduced", "unchanged"}:
        raise ValueError("Explicit blocker changes required")
    for values in event["blockers"].values():
        _strings(values)
    impact = event["readiness_impact"]
    if not isinstance(impact, dict) or set(impact) != {"label", "requirements", "artifact_paths", "explanation"}:
        raise ValueError("Readiness impact shape differs")
    if impact["label"] not in {"improved", "unchanged", "reduced", "not assessed"}:
        raise ValueError("Invalid impact label")
    _text(impact["explanation"])
    _strings(impact["requirements"])
    _strings(impact["artifact_paths"])
    if not set(impact["artifact_paths"]).issubset(paths):
        raise ValueError("Impact evidence must be a bound artifact")
    if impact["label"] in {"improved", "reduced"} and (not impact["requirements"] or not impact["artifact_paths"]):
        raise ValueError("Claimed change requires requirement and evidence")
    # User-written checkpoint prose is not a trusted current-state gate validator.
    if event["verified_gate_changes"] != []:
        raise ValueError("Checkpoint cannot mint verified gate changes")
    return event


def _safe_directory(root, relative):
    root = Path(root).resolve()
    current = root
    for part in Path(relative).parts:
        current /= part
        if current.is_symlink():
            raise ValueError("State/event directory cannot be a symlink")
    if not current.resolve().is_relative_to(root):
        raise ValueError("Directory escapes project")
    current.mkdir(parents=True, exist_ok=True)
    return current


@contextmanager
def _lock(root):
    state = _safe_directory(root, "state/research-engine")
    lock_path = state / "checkpoint.lock"
    if lock_path.is_symlink():
        raise ValueError("Lock cannot be a symlink")
    with lock_path.open("a+b") as handle:
        if lock_path.stat().st_size == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("Another checkpoint writer is active") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _atomic(path, data):
    if path.is_symlink():
        raise ValueError("Output cannot be a symlink")
    # Keep the same directory without extending an already long destination name.
    temporary = path.with_name(uuid4().hex + ".tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def record_checkpoint(root, event, *, now=None):
    root = Path(root).resolve()
    validate_event(root, event, now=now)
    identity = sha256(canonical([event["task_id"], event["turn_id"], event["phase"]]))
    with _lock(root):
        folder = _safe_directory(root, EVENT_DIRECTORY)
        path = folder / (identity + ".json")
        data = canonical(event) + b"\n"
        if path.exists():
            if path.is_symlink() or path.read_bytes() != data:
                raise ValueError("Checkpoint identity already binds different content")
            added = False
        else:
            events = _read_events(root, now=now)
            if any(item["event"]["id"] == event["id"] for item in events if item.get("event")):
                raise ValueError("Checkpoint ID already used")
            if event["phase"] == "complete":
                start = next((item for item in events if item.get("event") and item["event"]["task_id"] == event["task_id"] and item["event"]["turn_id"] == event["turn_id"] and item["event"]["phase"] == "start" and item["valid"]), None)
                if start is None:
                    raise ValueError("Complete requires a valid matching start")
                if timestamp(event["observed_at"]) < timestamp(start["event"]["observed_at"]):
                    raise ValueError("Completion predates start")
            _atomic(path, data)
            added = True
        projection = _rebuild(root, now=now)
    return {"recorded": added, "path": path.relative_to(root).as_posix(),
            "sha256": sha256(data), "projection": projection}


def _read_events(root, *, now=None):
    folder = root / EVENT_DIRECTORY
    if not folder.exists():
        return []
    _safe_directory(root, EVENT_DIRECTORY)
    events = []
    for path in sorted(folder.glob("*.json")):
        event = None
        try:
            if path.is_symlink() or path.stat().st_size > 1_000_000:
                raise ValueError("Invalid event file")
            event = json.loads(path.read_text(encoding="utf-8"))
            validate_event(root, event, now=now, verify_artifacts=False)
            expected = sha256(canonical([event["task_id"], event["turn_id"], event["phase"]])) + ".json"
            if path.name != expected:
                raise ValueError("Event filename identity differs")
            validate_event(root, event, now=now)
            events.append({"event": event, "valid": True, "path": path.relative_to(root).as_posix()})
        except (OSError, ValueError, KeyError, TypeError):
            # Recover identity only after the structural schema passed; malformed
            # source text and private paths never flow into the view as errors.
            identity = None
            if isinstance(event, dict):
                try:
                    identifier(event.get("task_id")); identifier(event.get("turn_id"))
                    identity = {"task_id": event["task_id"], "turn_id": event["turn_id"]}
                except ValueError:
                    pass
            events.append({"event": None, "identity": identity, "valid": False,
                           "path": path.relative_to(root).as_posix(), "reason": "checkpoint or referenced evidence invalid"})
    return events


def _rebuild(root, *, now=None):
    current = now or datetime.now(timezone.utc)
    events = _read_events(root, now=current)
    groups = {}
    for entry in events:
        event = entry.get("event")
        identity = event or entry.get("identity")
        if identity:
            key = (identity["task_id"], identity["turn_id"])
            groups.setdefault(key, []).append(entry)
    tasks = []
    for (task_id, turn_id), group in sorted(groups.items()):
        complete = next((x["event"] for x in group if x.get("event") and x["event"]["phase"] == "complete"), None)
        start = next((x["event"] for x in group if x.get("event") and x["event"]["phase"] == "start"), None)
        valid = all(x["valid"] for x in group)
        latest = complete or start
        outcome = complete["outcome"] if valid and complete and start else "turn ended; outcome not recorded."
        if not valid or (complete and not start):
            outcome = "invalidated checkpoint; outcome unverified"
        tasks.append({"task_id": task_id, "turn_id": turn_id, "outcome": outcome,
                      "request": latest["request"] if latest else "Unavailable checkpoint",
                      "work": complete["work"] if valid and complete and start else [],
                      "readiness_impact": complete["readiness_impact"] if valid and complete and start else None,
                      "next_action": latest["next_action"] if latest else "Repair checkpoint evidence",
                      "blockers": latest["blockers"] if latest else None,
                      "artifacts": latest["artifacts"] if valid and latest else [],
                      "recorded_at": latest["created_at"] if latest else None})
    valid_events = [x["event"] for x in events if x["valid"]]
    invalid_count = sum(not x["valid"] for x in events)
    projection = {"schema_version": 1, "id": "research-engine-status", "origin": "immutable project checkpoint events",
                  "assessed_at": current.isoformat(), "authoritative": False,
                  "software_completion": "in progress" if events else "not started",
                  "research_disposition": "active", "operational_readiness": "evidence incomplete",
                  "trade_readiness": "evidence incomplete", "edge_evidence": "not assessed",
                  "activation": "disabled", "live_recommendations_enabled": False,
                  "gates": [{"gate": gate, "status": "not assessed", "evidence": [],
                             "reason": "No current version-bound acceptance evaluated by this checkpoint projection"}
                            for gate in sorted(GATES)],
                  "counts": {"events": len(events), "invalid_events": invalid_count, "turns": len(tasks),
                             "outcomes": {outcome: sum(t["outcome"] == outcome for t in tasks)
                                          for outcome in ("complete", "partial", "failed", "interrupted")}},
                  "last_recorded_checkpoint": max((x["created_at"] for x in valid_events), key=timestamp, default=None),
                  "freshness": "No live attestations; checkpoints describe dated work only",
                  "tasks": tasks,
                  "limitations": ["Task completion does not establish software acceptance or trading readiness.",
                                  "Active research means the engine assignment is open; no real case is selected by this projection.",
                                  "No live account, quote, phone, monitoring or activation state is read.",
                                  "Research bridge and release acceptance must supply their own verified records."]}
    try:
        try:
            from .research_records import project_cases
        except ImportError:
            from research_records import project_cases
        projection['cases']=project_cases(root,now=current)
    except (ValueError,OSError,KeyError,TypeError):
        projection['cases']=[]
        projection['limitations'].append('Case projection unavailable; no research disposition inferred.')
    cases=projection['cases']
    if len(cases)==1:
        projection['research_disposition']=cases[0]['research_disposition']
        projection['gates']=cases[0]['gates']
    projection['counts']['research_cases']=len(cases)
    projection['requirements']=requirements_snapshot(root,now=current)
    try:
        from .research_release import project_release
    except ImportError:
        from research_release import project_release
    release = project_release(root, now=current)
    projection['software_release'] = release
    if events or release['software_completion'] != 'in progress':
        projection['software_completion'] = release['software_completion']
    state = _safe_directory(root, "state/research-engine")
    _atomic(state / "status.json", canonical(projection) + b"\n")
    rendered = render_html(projection)
    _atomic(state / "status.html", rendered.encode("utf-8"))
    return projection


def rebuild_projection(root, *, now=None):
    root = Path(root).resolve()
    with _lock(root):
        return _rebuild(root, now=now)


def requirements_snapshot(root,*,now=None):
    """Version-bound checklist visibility, never a trading acceptance source."""
    now=now or datetime.now(timezone.utc)
    pointer='monitoring/research-engine/requirements/current.json'
    unavailable=dict(status='unavailable',total=None,counts={},milestones=[],
        limitation='No current hash-verified requirement assessment; completion is unproven.')
    if not (Path(root)/pointer).exists():return unavailable
    try:
        selected=json.loads(artifact_path(root,pointer).read_text(encoding='utf-8'))
        assessment=json.loads(verify_reference(root,selected['assessment']).read_text(encoding='utf-8'))
        inventory=json.loads(verify_reference(root,assessment['inventory']).read_text(encoding='utf-8'))
        if type(assessment.get('schema_version')) is not int or assessment['schema_version']!=1 or timestamp(assessment['created_at'])>now:
            raise ValueError('Requirement assessment version/time invalid')
        by_id={r['id']:r for r in inventory['requirements']}
        entries=assessment['requirements']
        if len(entries)!=len(by_id) or {e['id'] for e in entries}!=set(by_id):
            raise ValueError('Every original requirement must remain visible exactly once')
        statuses={'not-assessed','implemented-fixture-tested','evaluated-failed','blocked','deferred','verified'}
        counts={};milestones=[]
        for entry in entries:
            status=entry['status'];refs=entry['evidence']
            if status not in statuses or not isinstance(refs,list) or (status!='not-assessed' and not refs):
                raise ValueError('Requirement status lacks evidence')
            if status=='deferred' and by_id[entry['id']]['required_for_software_acceptance']:
                raise ValueError('Required work cannot be silently deferred')
            try:
                for ref in refs:verify_reference(root,ref)
            except (ValueError,OSError):status='invalidated'
            counts[status]=counts.get(status,0)+1
            if entry['id'].startswith('COMMAND-'):
                milestones.append(dict(id=entry['id'],name=by_id[entry['id']]['requirement'],status=status))
        return dict(status='dated-assessment',assessment=selected['assessment'],assessed_at=assessment['created_at'],
            total=len(entries),counts=counts,milestones=milestones,
            limitation='Fixture coverage and checklist counts do not establish investment or live gate acceptance.')
    except (ValueError,OSError,KeyError,TypeError):return unavailable


def render_html(projection):
    esc = lambda value: html.escape(str(value), quote=True)
    tasks = "".join("<article><h2>" + esc(t["task_id"]) + " / " + esc(t["turn_id"]) + "</h2><p>" + esc(t["outcome"]) + "</p><p>" + esc(t["request"]) + "</p><ul>" + "".join("<li>" + esc(x) + "</li>" for x in t["work"]) + "</ul><p>Next: " + esc(t["next_action"]) + "</p></article>" for t in projection["tasks"])
    gates = "".join("<tr><td>" + esc(g["gate"]) + "</td><td>" + esc(g["status"]) + "</td></tr>" for g in projection["gates"])
    cases = ''.join('<article><h2>Case: ' + esc(c['case_id']) + '</h2><p>Disposition: ' + esc(c['research_disposition']) +
        ' · Review: ' + esc(c['review_status']) + '</p><ul>' + ''.join('<li>' + esc(x) + '</li>' for x in c['limitations']) + '</ul></article>'
        for c in projection.get('cases', []))
    requirements=projection.get('requirements',{})
    release_reason='<p>Software release: '+esc(projection.get('software_release',{}).get('reason','No release assessment'))+'</p>'
    milestones='<h2>Requirement evidence</h2><p>'+esc(requirements.get('counts',{}))+'</p><ul>'+''.join(
        '<li>'+esc(m['name'])+': '+esc(m['status'])+'</li>' for m in requirements.get('milestones',[]))+'</ul>'
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'"><title>Research engine status</title><style>body{font:16px system-ui;max-width:960px;margin:2rem auto;padding:0 1rem;color:#18302e;background:#f6f8f5}h1{font-size:2rem}article{background:white;padding:1rem;margin:1rem 0;border:1px solid #cbd5cd}td,th{text-align:left;padding:.4rem 1rem}strong{color:#70370d}table{border-collapse:collapse}p{line-height:1.5}</style><main><h1>Research engine status</h1><p><strong>Live recommendations disabled.</strong> This view records dated work; it does not approve a trade.</p><p>Software: ' + esc(projection["software_completion"]) + ' · Research: ' + esc(projection["research_disposition"]) + '</p><p>Operations: ' + esc(projection["operational_readiness"]) + ' · Trade readiness: ' + esc(projection["trade_readiness"]) + ' · Edge: ' + esc(projection["edge_evidence"]) + '</p><p>Assessed: ' + esc(projection["assessed_at"]) + '</p><h2>Ten separate acceptance gates</h2><table><thead><tr><th>Gate</th><th>Status</th></tr></thead><tbody>' + gates + '</tbody></table>' + release_reason + milestones + cases + tasks + '</main></html>'


def load_checkpoint_input(root, path):
    """CLI inputs use the same public-artifact allowlist; no private JSON reads."""
    source = artifact_path(root, path)
    if source.stat().st_size > 1_000_000:
        raise ValueError("Input too large")
    return json.loads(source.read_text(encoding="utf-8"))
