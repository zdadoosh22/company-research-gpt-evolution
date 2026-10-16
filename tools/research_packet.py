"""Deterministic authorized passages for version 2 scoped jobs.

Original files stay in the archive. Only exact UTF-8 byte ranges and their
explicit table context enter the worker packet; no discovery/search is done.
Metadata compatibility is a necessary check, not semantic fact certification.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

MAX_PACKET_BYTES = 262144
CONTEXT_FIELDS = {"entity", "security", "period", "basis", "unit", "currency"}


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _exact(value, fields, label):
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("Malformed " + label)


def _context(value):
    _exact(value, CONTEXT_FIELDS, "evidence context")
    for item in value.values():
        if item is not None and (not isinstance(item, str) or not item.strip() or item.lower() in {"unknown", "n/a", "none"}):
            raise ValueError("Unknown metadata must be explicit null")


def _range(data, spec):
    _exact(spec, {"start_byte", "end_byte", "sha256"}, "passage range")
    start, end = spec["start_byte"], spec["end_byte"]
    if any(isinstance(x, bool) or not isinstance(x, int) for x in (start, end)) or not 0 <= start < end <= len(data):
        raise ValueError("Passage range outside source bytes")
    selected = data[start:end]
    if sha256(selected) != spec["sha256"]:
        raise ValueError("Passage bytes differ")
    try:
        text = selected.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Passage must be an exact UTF-8 boundary") from exc
    return {**spec, "text": text, "utf8_bytes": len(selected)}


def _validate_chronology(job):
    """Recheck source dates here so direct packet callers get adapter guarantees.

    Importing timestamp parsers is safe; calling validate_package here would
    recurse because the adapter validates compact packets through this module.
    """
    try:
        from .scoped_research_adapter import _stamp, _evidence_stamp
    except ImportError:
        from scoped_research_adapter import _stamp, _evidence_stamp

    now = datetime.now(timezone.utc)
    cutoff = _stamp(job["as_of"])
    if cutoff > now:
        raise ValueError("Future as-of scope")
    for source in job["sources"]:
        accessed = _evidence_stamp(source["accessed_at"])
        if accessed > now:
            raise ValueError("Future source access")
        if source["published_at"] is None:
            if source.get("date_status") != "publication-date-unknown-snapshot" or "captured_at" not in source:
                raise ValueError("Unknown publication needs explicit snapshot provenance")
            captured = _stamp(source["captured_at"])
            if captured > cutoff or captured > accessed:
                raise ValueError("Snapshot capture violates as-of chronology")
        else:
            if "date_status" in source or "captured_at" in source:
                raise ValueError("Unknown-date snapshot cannot be relabelled as published")
            published = _evidence_stamp(source["published_at"])
            if published > cutoff or published > accessed:
                raise ValueError("Source chronology violates as-of scope")


def prepare_packet(root, job, output_schema):
    """Return content, frozen hashes and eligibility for already authorized files.

The adapter validates the legacy manifest first. This function also verifies
all files independently so it can safely serve deterministic packet callers.
"""
    try:
        from .scoped_research_adapter import _file, _no_credentials
    except ImportError:
        from scoped_research_adapter import _file, _no_credentials
    root = Path(root).resolve()
    if not isinstance(job, dict) or job.get("schema_version") != 2 or isinstance(job.get("schema_version"), bool):
        raise ValueError("New dispatch requires compact job schema version 2")
    _no_credentials(job)
    if not isinstance(job.get("sources"), list) or not job["sources"]:
        raise ValueError("Archived sources required")
    _validate_chronology(job)
    spec = job.get("packet")
    _exact(spec, {"schema_version", "context", "passages", "max_utf8_bytes"}, "compact packet specification")
    if type(spec["schema_version"]) is not int or spec["schema_version"] != 1:
        raise ValueError("Unsupported packet version")
    _context(spec["context"])
    maximum = spec["max_utf8_bytes"]
    if type(maximum) is not int or not 1 <= maximum <= MAX_PACKET_BYTES:
        raise ValueError("Invalid packet byte ceiling")
    if not isinstance(spec["passages"], list) or not spec["passages"]:
        raise ValueError("Authorized source passages required")
    sources = {s["source_id"]: s for s in job["sources"]}
    manifest, passages, eligibility, seen = {}, [], {}, set()
    originals = {}
    for source_id, source in sources.items():
        path = _file(root, source)
        data = path.read_bytes()
        if sha256(data) != source['sha256']:
            raise ValueError('Original bytes changed during extraction')
        manifest[str(path)] = source["sha256"]
        originals[source_id] = {"source_id": source_id, "sha256": source["sha256"],
            "original_bytes": len(data), "published_at": source["published_at"],
            "accessed_at": source["accessed_at"], "date_status": source.get("date_status", "published"),
            "captured_at": source.get("captured_at")}
    for passage in spec["passages"]:
        _exact(passage, {"source_id", "location", "text_file", "range", "metadata", "extraction", "table_context"}, "authorized passage")
        sid, location = passage["source_id"], passage["location"]
        if sid not in sources or location not in sources[sid]["read_locations"] or (sid, location) in seen:
            raise ValueError("Omitted, duplicate or unauthorized source/location")
        seen.add((sid, location))
        _exact(passage["text_file"], {"path", "sha256"}, "extracted text file")
        path = _file(root, passage["text_file"])
        data = path.read_bytes()
        if sha256(data) != passage['text_file']['sha256']:
            raise ValueError('Extract bytes changed during extraction')
        manifest[str(path)] = passage["text_file"]["sha256"]
        selected = _range(data, passage["range"])
        _context(passage["metadata"])
        extraction = passage["extraction"]
        _exact(extraction, {"method", "version", "status", "original_sha256"}, "extraction provenance")
        if any(not isinstance(extraction[x], str) or not extraction[x].strip() for x in ("method", "version")) or extraction["status"] not in {"complete", "incomplete", "unknown"}:
            raise ValueError("Extraction provenance unavailable")
        if extraction["original_sha256"] != sources[sid]["sha256"]:
            raise ValueError("Extraction bound to another original")
        # Direct extraction is independently reproducible; other methods retain
        # declared provenance without pretending to verify PDF/OCR semantics.
        if extraction["method"] == "utf8-byte-range" and passage["text_file"]["sha256"] != sources[sid]["sha256"]:
            raise ValueError("Direct byte extraction must use original bytes")
        table = passage["table_context"]
        _exact(table, {"kind", "headers", "footnotes"}, "table context")
        if table["kind"] not in {"prose", "table"} or not isinstance(table["headers"], list) or not isinstance(table["footnotes"], list):
            raise ValueError("Invalid table context")
        if table["kind"] == "table" and not table["headers"]:
            raise ValueError("Table headings must be preserved")
        context = {"kind": table["kind"], "headers": [_range(data, x) for x in table["headers"]],
                   "footnotes": [_range(data, x) for x in table["footnotes"]]}
        gaps = []
        for key in sorted(CONTEXT_FIELDS):
            expected, observed = spec["context"][key], passage["metadata"][key]
            if expected is None or observed is None:
                gaps.append("unknown-" + key)
            elif expected != observed:
                gaps.append("incompatible-" + key)
        if extraction["status"] != "complete":
            gaps.append("extraction-" + extraction["status"])
        if sources[sid]["published_at"] is None:
            gaps.append("publication-date-unknown")
        eligibility[(sid, location)] = not gaps
        passages.append({"source_id": sid, "location": location, "content": selected,
            "text_sha256": passage["text_file"]["sha256"], "text_file_bytes": len(data),
            "metadata": passage["metadata"], "extraction": extraction, "table_context": context,
            "qualifying_evidence": not gaps, "gaps": gaps})
    # No manifest source or declared read location may disappear during compacting.
    if seen != {(sid, loc) for sid, s in sources.items() for loc in s["read_locations"]}:
        raise ValueError("Compact packet omitted an authorized source/location")
    methods = {}
    for name, record in job["methodology"].items():
        path = _file(root, record)
        data = path.read_bytes()
        if sha256(data) != record['sha256']:
            raise ValueError('Methodology bytes changed during extraction')
        manifest[str(path)] = record["sha256"]
        methods[name] = {"sha256": record["sha256"], "utf8_bytes": len(data), "text": data.decode("utf-8")}
    target_path = _file(root, job["target"])
    target = target_path.read_bytes()
    if sha256(target) != job['target']['sha256']:
        raise ValueError('Target bytes changed during extraction')
    manifest[str(target_path)] = job["target"]["sha256"]
    content = {"schema_version": 1, "job_schema_version": 2, "job_id": job["job_id"], "role": job["role"],
        "as_of": job["as_of"], "scope": job["scope"], "context": spec["context"],
        "prefix": {"methodology": methods, "output_schema": output_schema},
        "target": {"sha256": job["target"]["sha256"], "utf8_bytes": len(target), "text": target.decode("utf-8")},
        "sources": list(originals.values()), "passages": passages}
    try:
        from .scoped_research_adapter import _stamp, _evidence_stamp
    except ImportError:
        from scoped_research_adapter import _stamp, _evidence_stamp
    retrospective = any(_evidence_stamp(s['accessed_at']) > _stamp(job['as_of']) for s in job['sources'])
    content['historical_reconstruction'] = retrospective
    content['capture_label'] = ('Retrospective capture; earlier publication metadata is not contemporaneous project observation.'
        if retrospective else 'Dated capture metadata; not a current-price or analytical acceptance certification.')
    _no_credentials(content)
    encoded = canonical_bytes(content)
    if len(encoded) > maximum:
        raise ValueError("Compact packet exceeds frozen byte ceiling")
    return {"content": content, "bytes": encoded, "sha256": sha256(encoded), "utf8_bytes": len(encoded),
        "original_bytes": sum(s["original_bytes"] for s in originals.values()),
        "input_manifest": manifest, "eligibility": eligibility}


def stage_packet(packet, output_schema, directory):
    """Stage only two hash-checked inputs. A temporary cwd is not isolation."""
    directory = Path(directory).resolve()
    if any(directory.iterdir()):
        raise ValueError("Packet staging directory must start empty")
    content = canonical_bytes(packet["content"])
    if content != packet["bytes"] or sha256(content) != packet["sha256"]:
        raise ValueError("Packet content changed before staging")
    schema = canonical_bytes(output_schema)
    if canonical_bytes(packet["content"].get("prefix", {}).get("output_schema")) != schema:
        raise ValueError("Output schema changed before staging")
    files = {"packet.json": content, "schema.json": schema}
    staged = {}
    for name, data in files.items():
        path = directory / name
        path.write_bytes(data)
        staged[name] = sha256(data)
        if sha256(path.read_bytes()) != staged[name]:
            raise ValueError("Staged bytes differ")
    return staged
