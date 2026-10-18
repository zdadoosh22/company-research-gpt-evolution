"""Explicit, rebuildable research retrieval. Sources are data; this module runs no workers.

Only manifest-selected approved artifact families are read. The SQLite database is
a disposable projection, never an approval, a source archive or a live gate.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sqlite3
import sys

from research import ROOT, read_json, save_json, sha256, within

SCHEMA = "cr2.research-memory.v1"
TYPES = {"entity", "disposition", "claim"}
EVALUATOR_FIELDS = {"polarity", "expected_exclusion_reason"}
DATE_FIELDS = ("public_source_date", "captured_at", "project_record_created_at",
               "analysis_at", "reviewed_at", "versioned_no_later_than", "valid_until", "superseded_effective_at")


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def baseline_ids(records, query_terms):
    phrases = set(term.casefold() for term in query_terms)
    scored = [(sum(term in r["text"].casefold() for term in phrases), r["id"]) for r in records]
    return [key for score, key in sorted(scored, key=lambda x: (-x[0], x[1])) if score]


def stamp(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Missing date; unknown dates cannot be inferred")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        # A date-only disclosure has no known time: use the end of that day.
        return datetime.fromisoformat(value + "T23:59:59.999999+00:00")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp requires an explicit timezone")
    return result.astimezone(timezone.utc)


def approved_path(value):
    """Allow artifact families, not recursive project/state/private ingestion."""
    path = PurePosixPath(str(value).replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or ":" in str(path):
        raise ValueError("Source path must be a relative approved artifact path")
    text = str(path)
    allowed = (re.fullmatch(r"companies/[a-z0-9-]+/index\.json", text)
               or re.fullmatch(r"companies/[a-z0-9-]+/runs/[a-zA-Z0-9_-]+/(?:run|report|observations|sources|review|research-record)\.json", text)
               or re.fullmatch(r"companies/[a-z0-9-]+/runs/[a-zA-Z0-9_-]+/sources/[a-zA-Z0-9_.-]+\.(?:txt|md|json)", text)
               or re.fullmatch(r"monitoring/studies/[a-zA-Z0-9_./-]+\.(?:md|json|txt)", text)
               or re.fullmatch(r"monitoring/research-engine/cases/[a-z0-9_.-]+/[a-z0-9_.-]+-r[0-9]+\.json", text)
               or text == "lessons/confirmed.md")
    if not allowed or any(part.startswith(".") for part in path.parts):
        raise ValueError("Source is outside approved artifact families: " + text)
    return text


def pointer(document, location):
    if location == "/":
        return document
    value = document
    for part in location.lstrip("/").split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def located_text(data, location):
    """Resolve exact JSON pointers or inclusive one-based lines; no fuzzy matching."""
    if not isinstance(location, str) or not location.strip():
        raise ValueError("Missing precise location")
    text = data.decode("utf-8-sig")
    if location.startswith("/"):
        doc = json.loads(text)
        paths = location.split(" and ")
        try:
            value = ({p.lstrip("/"): pointer(doc, p) for p in paths}
                     if len(paths) > 1 else pointer(doc, paths[0]))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ValueError("Invalid exact JSON location: " + location) from exc
        return value if isinstance(value, str) else json.dumps(value, sort_keys=True)
    match = re.fullmatch(r"lines? (\d+)(?:-(\d+))?(?:; .*)?", location)
    if not match:
        raise ValueError("Unsupported precise location; use JSON pointer or line range")
    start, end = int(match[1]), int(match[2] or match[1])
    lines = text.splitlines(keepends=True)
    if start < 1 or end < start or end > len(lines):
        raise ValueError("Exact line location is outside the source")
    return "".join(lines[start-1:end]).rstrip("\r\n")


def table_rows(text):
    rows = []
    for line in text.splitlines():
        cells = line.split(" | ")
        if len(cells) == 5 and re.match(r"^\d{4}(?:-|$)", cells[0]):
            rows.append(dict(zip(("period", "metric", "value_and_unit", "source_location", "scope"), cells)))
    return rows


def validate_record(record, sources):
    # An unrecognized provided label must not silently bypass conservative
    # context retention. load_bundle defaults an omitted label to unknown.
    if not isinstance(record.get("polarity"), str) or record["polarity"] not in {
            "supporting", "contrary", "supporting-and-contrary", "unknown"}:
        raise ValueError("Invalid polarity; explicitly classify or preserve unknown")
    for field in ("id", "record_type", "entity_id", "question_scope", "source_id",
                  "source_path", "source_sha256", "location", "text", "text_sha256", "review_status",
                  "originating_run"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ValueError("Missing record field: " + field)
    if record["record_type"] not in TYPES:
        raise ValueError("Only entity, disposition and claim records are supported")
    source = sources.get(record["source_id"])
    if source is None:
        raise ValueError("Unknown source reference")
    if (record["source_path"], record["source_sha256"]) != (source["repository_path"], source["sha256"]):
        raise ValueError("Source reference path/hash mismatch")
    data = Path(source["resolved_path"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != source["sha256"]:
        raise ValueError("Source byte hash mismatch")
    if digest(record["text"]) != record["text_sha256"]:
        raise ValueError("Passage text hash mismatch")
    if located_text(data, record["location"]) != record["text"]:
        raise ValueError("Passage does not equal its exact source location")
    for field in DATE_FIELDS:
        if record.get(field) is not None:
            stamp(record[field])
    rows = table_rows(record["text"])
    for row in rows:
        unit = row["value_and_unit"].split(" ", 1)[-1]
        if record.get("declared_unit") and record["declared_unit"] != unit:
            raise ValueError("Incompatible declared unit and source table")
        if record.get("declared_currency") and not unit.startswith(record["declared_currency"] + " "):
            raise ValueError("Incompatible declared currency and source table")
    if record.get("origin_kind") == "methodological-lesson":
        scope = record.get("lesson_applicability", {})
        if record["source_path"] != "lessons/confirmed.md" or record["review_status"] != "confirmed-methodology":
            raise ValueError("Only confirmed methodology lessons can be reused")
        if scope.get("company_fact") is not False:
            raise ValueError("Methodological lessons cannot be company facts")


def load_bundle(project_root, records_path, manifest_path, source_root=None, *, frozen=False):
    root = Path(project_root).resolve()
    records_path = within(root, root / records_path)
    manifest_path = within(root, root / manifest_path)
    source_root = within(root, root / source_root) if source_root else root
    manifest = read_json(manifest_path)
    raw = read_json(records_path)
    if not isinstance(manifest.get("files"), list) or not isinstance(raw.get("records"), list):
        raise ValueError("Explicit source manifest files and normalized records are required")
    sources = {}
    for item in manifest["files"]:
        source = copy.deepcopy(item)
        source["repository_path"] = approved_path(source["repository_path"])
        path = within(source_root, source_root / source.get("frozen_path", source["repository_path"]))
        actual = path.relative_to(root).as_posix()
        if not re.fullmatch(r"validation/[a-zA-Z0-9_-]+/frozen-inputs/[a-zA-Z0-9_.-]+\.(?:txt|md|json)", actual):
            # A manifest alias must not launder a private/state file into an
            # apparently approved repository_path. Resolve symlinks before this.
            approved_path(actual)
        if not re.fullmatch(r"[0-9a-f]{64}", source.get("sha256", "")) or sha256(path) != source["sha256"]:
            raise ValueError("Source byte hash mismatch: " + source["repository_path"])
        if "bytes" in source and path.stat().st_size != source["bytes"]:
            raise ValueError("Source size mismatch")
        if source["source_id"] in sources:
            raise ValueError("Duplicate source identifier")
        source["resolved_path"] = str(path)
        if source['repository_path'].startswith('monitoring/research-engine/cases/'):
            # Case records contain references to original evidence. Validate
            # that graph on import and every rebuild/query, not just the wrapper.
            from research_records import validate_record as validate_engine_record
            validate_engine_record(root,read_json(path))
        sources[source["source_id"]] = source
    # Link exact source-register entries. No source metadata becomes passage text.
    registrations = {}
    for source in sources.values():
        if source["repository_path"].endswith("/sources.json"):
            entries = read_json(source["resolved_path"])
            base = PurePosixPath(source["repository_path"]).parent
            for entry in entries:
                if entry.get("archived_file"):
                    registrations[str(base / entry["archived_file"])] = (entry, source)
    for source in sources.values():
        registered = registrations.get(source["repository_path"])
        if registered:
            entry, register = registered
            if source["sha256"] != entry.get("sha256"):
                raise ValueError("Source register hash mismatch")
            source["publication_date"] = entry.get("publication_date")
            source["register_id"] = register["source_id"]
            source["register_entry_id"] = entry["id"]
    records = []
    for original in raw["records"]:
        record = {k: copy.deepcopy(v) for k, v in original.items() if not frozen or k not in EVALUATOR_FIELDS}
        source = sources.get(record.get("source_id"))
        if source is None:
            raise ValueError("Unknown source reference")
        path = PurePosixPath(source["repository_path"])
        is_public = "sources" in path.parts and path.suffix in {".txt", ".md", ".json"}
        kind = "methodological-lesson" if str(path) == "lessons/confirmed.md" else ("public-source-extract" if is_public else "project-analysis")
        record.setdefault("schema", SCHEMA)
        record.setdefault("origin_kind", kind)
        if record["origin_kind"] != kind:
            raise ValueError("Origin kind disagrees with the approved artifact family")
        record.setdefault("originating_run", str(path.parent.parent if is_public else path.parent))
        for field in DATE_FIELDS:
            record.setdefault(field, None)
        for field in ("event_period", "event_date", "accounting_basis", "scope", "declared_unit", "declared_currency", "review_scope", "disposition"):
            record.setdefault(field, None)
        for field in ("assumptions", "affected_record_ids", "contradicts", "reopen_conditions", "limitations", "source_dependencies"):
            record.setdefault(field, [])
        record.setdefault("polarity", "unknown")
        record.setdefault("claim_kind", "methodology" if kind == "methodological-lesson" else "attributed-project-record")
        record.setdefault("superseded_by", None)
        record.setdefault("readiness_effect", "none")
        record["readiness_effect"] = "none"
        if kind == "methodological-lesson":
            record.setdefault("lesson_applicability", {"entities": ["*"], "methodology_version": None, "company_fact": False, "scope": "methodological caution only"})
        if kind == "public-source-extract" and "publication_date" in source and record["public_source_date"] != source["publication_date"]:
            raise ValueError("Publication date disagrees with preserved source register")
        dependencies = []
        for dep in record["source_dependencies"]:
            dep_id = dep.split(";", 1)[0].strip() if isinstance(dep, str) else dep["source_id"]
            matches = [s for s in sources.values() if s["source_id"] == dep_id or
                       (s.get("register_entry_id") == dep_id and PurePosixPath(s["repository_path"]).parent.parent == path.parent)]
            if len(matches) != 1:
                raise ValueError("Unresolved or ambiguous source dependency: " + dep_id)
            dependencies.append(matches[0]["source_id"])
        record["dependency_source_ids"] = dependencies
        rows = table_rows(record["text"])
        record["table"] = {"rows": rows, "column_labels": ["period", "metric", "value_and_unit", "source_location", "scope"],
                           "original_headers_claimed": False, "original_footnotes_claimed": False} if rows else None
        validate_record(record, sources)
        records.append(record)
    if len({r["id"] for r in records}) != len(records):
        raise ValueError("Duplicate record identifier")
    by_id = {r["id"]: r for r in records}
    for record in records:
        successor = by_id.get(record["superseded_by"])
        if successor and not record["superseded_effective_at"]:
            record["superseded_effective_at"] = successor.get("project_record_created_at") or successor.get("versioned_no_later_than")
    provenance = {"records_path": str(records_path.relative_to(root)), "records_sha256": sha256(records_path),
                  "manifest_path": str(manifest_path.relative_to(root)), "manifest_sha256": sha256(manifest_path),
                  "source_root": str(source_root.relative_to(root)), "frozen": frozen}
    return records, sources, provenance


def eligibility(record, sources, *, evidence_cutoff, entities, security_id=None, question_scope=None,
                record_types=None, review_statuses=None, period=None, accounting_basis=None, unit=None,
                scope=None, include_superseded=False, retrospective=False, methodology_version=None):
    cutoff = stamp(evidence_cutoff)
    # Chronology comes first so a later conclusion is identified even if also out of scope.
    if record["origin_kind"] == "public-source-extract":
        if record.get("public_source_date") is None:
            return "unknown-publication-date"
        if stamp(record["public_source_date"]) > cutoff:
            return "public-source-after-cutoff"
    else:
        available = record.get("project_record_created_at") or record.get("versioned_no_later_than")
        if available is None:
            return "unknown-analytical-availability"
        if stamp(available) > cutoff:
            return "analytical-conclusion-after-cutoff"
    for field in ("analysis_at", "reviewed_at", "project_record_created_at"):
        if record.get(field) and stamp(record[field]) > cutoff:
            return field + "-after-cutoff"
    if not retrospective and record.get("captured_at") and stamp(record["captured_at"]) > cutoff:
        return "captured-after-cutoff-requires-retrospective-label"
    if record.get("valid_until") and stamp(record["valid_until"]) < cutoff:
        return "expired-for-current-reuse"
    if record["entity_id"] not in entities:
        return "wrong-entity"
    if record["origin_kind"] == "methodological-lesson":
        applicability = record["lesson_applicability"]
        if methodology_version and applicability.get("methodology_version") != methodology_version:
            return "lesson-methodology-version-incompatible-or-unknown"
        if "*" not in applicability.get("entities", []) and not set(entities).intersection(applicability.get("entities", [])):
            return "lesson-applicability-mismatch"
    elif security_id is not None and record.get("security_id") != security_id:
        return "wrong-security"
    if question_scope and record["question_scope"] != question_scope:
        return "wrong-question-scope"
    if record_types and record["record_type"] not in record_types:
        return "record-type-filter"
    if review_statuses and record["review_status"] not in review_statuses:
        return "review-status-filter"
    if (record.get("superseded_by") and not include_superseded
            and (not record.get("superseded_effective_at") or stamp(record["superseded_effective_at"]) <= cutoff)):
        return "superseded-for-default-reuse"
    for key, wanted in (("event_period", period), ("accounting_basis", accounting_basis), ("declared_unit", unit), ("scope", scope)):
        if wanted is not None and record.get(key) != wanted:
            return "incompatible-or-unknown-" + key
    for source_id in record.get("dependency_source_ids", []):
        dependency = sources[source_id]
        if dependency.get("publication_date") is None:
            return "dependency-unknown-publication-date:" + source_id
        if stamp(dependency["publication_date"]) > cutoff:
            return "dependency-after-cutoff:" + source_id
    return None


def build_packet(records, sources, ranked_ids, *, query_terms, max_records=16,
                 max_packet_utf8_bytes=32768, historical_label=None, balance=True, **filters):
    if not isinstance(max_records, int) or max_records < 1 or max_packet_utf8_bytes < 256:
        raise ValueError("Packet bounds must be positive and usable")
    if not filters.get("entities"):
        raise ValueError("At least one explicit entity filter is required")
    by_id = {r["id"]: r for r in records}
    # An immutable successor can supersede an old indexed record without
    # rewriting that predecessor's import metadata. Only explicit same-scope
    # links from temporally eligible, hash-verified successors are applied.
    records=copy.deepcopy(records)
    by_id={r['id']:r for r in records}
    successor_filters={**filters,'review_statuses':None,'record_types':None,
                       'period':None,'accounting_basis':None,'unit':None,'scope':None}
    for successor in records:
        links=successor.get('supersedes_record_ids',[])
        if not isinstance(links,list) or any(not isinstance(x,str) for x in links):
            raise ValueError('Explicit supersession record IDs required')
        if not links:continue
        validate_record(successor,sources)
        if eligibility(successor,sources,**successor_filters):continue
        effective=successor.get('superseded_effective_at') or successor.get('project_record_created_at')
        if effective is None or stamp(effective)>stamp(filters['evidence_cutoff']):continue
        for old_id in links:
            old=by_id.get(old_id)
            if old and all(old.get(k)==successor.get(k) for k in ('entity_id','security_id','question_scope')):
                prior=old.get('superseded_effective_at')
                if not old.get('superseded_by') or (prior and stamp(effective)<stamp(prior)):
                    old.update(superseded_by=successor['id'],superseded_effective_at=effective)
    excluded, eligible = {}, {}
    for record in records:
        try:
            validate_record(record, sources)
            reason = eligibility(record, sources, **filters)
        except (ValueError, OSError) as exc:
            reason = "integrity-failure:" + str(exc)
        if reason:
            excluded[record["id"]] = {"record_id": record["id"], "reason": reason,
                "source_id": record["source_id"], "public_source_date": record.get("public_source_date"),
                "versioned_no_later_than": record.get("versioned_no_later_than"), "superseded_by": record.get("superseded_by")}
        else:
            eligible[record["id"]] = record
    ranked_ids = list(ranked_ids)
    initially_matched = set(ranked_ids)
    if balance and any(key in eligible for key in ranked_ids):
        linked = {key for r in eligible.values() if r["id"] in initially_matched
                  for key in r.get("contradicts", []) + r.get("affected_record_ids", [])}
        linked.update(r['id'] for r in eligible.values()
                      if initially_matched.intersection(r.get('contradicts', []) + r.get('affected_record_ids', [])))
        ranked_ids.extend(sorted(key for key, r in eligible.items() if key not in initially_matched
            and (r.get("polarity") in {"contrary", "supporting-and-contrary", "unknown"}
                 or r.get('limitations') or key in linked)))
    ranked_ids = list(dict.fromkeys(ranked_ids))
    ranked_set = set(ranked_ids)
    for key in eligible.keys() - ranked_set:
        excluded[key] = {"record_id": key, "reason": "no-query-match"}
    packet = {"schema": SCHEMA, "query_terms": query_terms, "filters": filters,
              "historical_label": historical_label or ("Retrospective reconstruction; not contemporaneous capture or edge evidence." if filters.get("retrospective") else "Dated project retrieval; not a freshness or approval certification."),
              "source_text_interpretation": "data-only", "readiness_effect": "none", "records": []}
    if len(canonical(packet).encode("utf-8")) > max_packet_utf8_bytes:
        raise ValueError("Packet metadata alone exceeds byte budget")
    for key in ranked_ids:
        if key not in eligible:
            continue
        record = copy.deepcopy(eligible[key])
        match_reason = "query text matched" if key in initially_matched else "explicit contrary or conflicting, uncertain, limited or affected-record context retained within requested scope"
        record["inclusion_reason"] = "Requested entity/security/question and chronology/status checks passed; " + match_reason + "; " + record["origin_kind"] + "; approval is not inferred."
        record["source_reference"] = {"source_id": record["source_id"], "path": record["source_path"], "sha256": record["source_sha256"], "location": record["location"]}
        packet["records"].append(record)
        reason = "record-budget" if len(packet["records"]) > max_records else "byte-budget"
        if len(packet["records"]) > max_records or len(canonical(packet).encode("utf-8")) > max_packet_utf8_bytes:
            packet["records"].pop()
            excluded[key] = {"record_id": key, "reason": reason + "; whole passage omitted"}
    omitted = [eligible[key] for key in ranked_ids if key in eligible and key in excluded]
    # Ordinary retrieval fails closed if caps could hide the contrary case. Frozen
    # comparison retains its prescribed rank/cap algorithm and reports omissions.
    if balance and any(r.get("polarity") in {"contrary", "supporting-and-contrary", "unknown"}
                       or r.get('limitations') or r['id'] not in initially_matched for r in omitted):
        for record in packet["records"]:
            excluded[record["id"]] = {"record_id": record["id"], "reason": "packet-withheld-budget-could-hide-contrary-evidence"}
        packet["records"] = []
    encoded = canonical(packet).encode("utf-8")
    return {"packet": packet, "excluded": [excluded[k] for k in sorted(excluded)],
            "packet_sha256": hashlib.sha256(encoded).hexdigest(), "packet_utf8_bytes": len(encoded),
            "selected_record_ids": [r["id"] for r in packet["records"]],
            "record_count": len(packet["records"]), "network_calls": 0, "worker_calls": 0,
            "complete_within_bounds": not omitted}


class ResearchMemory:
    def __init__(self, project_root=ROOT, state_root=None):
        self.root = Path(project_root).resolve()
        self.state_root = within(self.root, Path(state_root) if state_root else self.root / "state/research-memory")
        # Caller may select an isolated state directory, but never another operational store.
        rel = self.state_root.relative_to(self.root).as_posix()
        if not (rel == "state/research-memory" or rel.startswith("state/research-memory/") or rel == "state/research-engine" or rel.startswith("state/research-engine/")):
            raise ValueError("Derived memory state must stay in state/research-memory or state/research-engine")
        self.state_root.mkdir(parents=True, exist_ok=True)
        self.path = self.state_root / "memory.sqlite"
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY, entity TEXT NOT NULL,
                security TEXT, kind TEXT NOT NULL, review_status TEXT NOT NULL, document TEXT NOT NULL);
            CREATE VIRTUAL TABLE IF NOT EXISTS passages USING fts5(text, tokenize='unicode61 remove_diacritics 2');
            CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY, document TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS bundles(id TEXT PRIMARY KEY, document TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS metadata ON records(entity, security, kind, review_status);
        """)

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def import_bundle(self, records_path, manifest_path, source_root=None, *, frozen=False):
        with self.conn:
            self.conn.execute("BEGIN IMMEDIATE")
            loaded = load_bundle(self.root, records_path, manifest_path, source_root, frozen=frozen)
            return self._store_bundle(*loaded)

    def _store_bundle(self, records, sources, provenance):
        """Write validated inputs inside the caller's transaction; never commit here."""
        bundle_id = digest(canonical(provenance))
        # Validate every collision before inserting anything; reimport is idempotent.
        for table, items in (("records", {r["id"]: r for r in records}), ("sources", sources)):
            for key, value in items.items():
                old = self.conn.execute("SELECT document FROM " + table + " WHERE id=?", (key,)).fetchone()
                if old and old[0] != canonical(value):
                    raise ValueError("Conflicting stable identifier; append a revision instead: " + key)
        for key, source in sorted(sources.items()):
            self.conn.execute("INSERT OR IGNORE INTO sources VALUES (?,?)", (key, canonical(source)))
        for record in sorted(records, key=lambda r: r["id"]):
            if self.conn.execute("SELECT 1 FROM records WHERE id=?", (record["id"],)).fetchone():
                continue
            cur = self.conn.execute("INSERT INTO records VALUES (?,?,?,?,?,?)", (record["id"], record["entity_id"], record.get("security_id"), record["record_type"], record["review_status"], canonical(record)))
            self.conn.execute("INSERT INTO passages(rowid,text) VALUES (?,?)", (cur.lastrowid, record["text"]))
        self.conn.execute("INSERT OR IGNORE INTO bundles VALUES (?,?)", (bundle_id, canonical(provenance)))
        return {"records": len(records), "sources": len(sources), "bundle_sha256": bundle_id, "provenance": provenance}

    def data(self):
        for (document,) in self.conn.execute("SELECT document FROM bundles ORDER BY id"):
            bundle = json.loads(document)
            for key in ("records", "manifest"):
                if sha256(within(self.root, self.root / bundle[key + "_path"])) != bundle[key + "_sha256"]:
                    raise ValueError("Imported bundle changed; rebuild requires an explicit new revision")
        records = [json.loads(row[0]) for row in self.conn.execute("SELECT document FROM records ORDER BY id")]
        sources = {key: json.loads(doc) for key, doc in self.conn.execute("SELECT id,document FROM sources ORDER BY id")}
        # Metadata registers matter even when not selected as answer passages.
        for source in sources.values():
            if sha256(source["resolved_path"]) != source["sha256"]:
                raise ValueError("Source byte hash mismatch: " + source["repository_path"])
        return records, sources

    def query(self, query_terms, *, route="new", fts_query=None, **kwargs):
        if not query_terms or any(not isinstance(x, str) or not x.strip() for x in query_terms):
            raise ValueError("Nonempty explicit query phrases are required")
        records, sources = self.data()
        if route == "baseline":
            ranked = baseline_ids(records, query_terms)
        elif route == "new":
            query = fts_query or " OR ".join('"' + term.replace('"', '""') + '"' for term in query_terms)
            try:
                ranked = [row[0] for row in self.conn.execute("SELECT r.id FROM passages JOIN records r ON r.rowid=passages.rowid WHERE passages MATCH ? ORDER BY bm25(passages),r.id", (query,))]
            except sqlite3.OperationalError as exc:
                raise ValueError("Invalid FTS query") from exc
        else:
            raise ValueError("Unknown retrieval route")
        return build_packet(records, sources, ranked, query_terms=query_terms, **kwargs)

    def rebuild(self):
        # Lock before reading the import registry: a concurrent import cannot
        # disappear between validation and deletion of the preceding index.
        with self.conn:
            self.conn.execute("BEGIN IMMEDIATE")
            bundles = [json.loads(r[0]) for r in self.conn.execute("SELECT document FROM bundles ORDER BY id")]
            self.data()
            prepared = [load_bundle(self.root, b["records_path"], b["manifest_path"], b["source_root"], frozen=b["frozen"])
                        for b in bundles]
            # One transaction includes every deletion, reimport and registry row.
            for table in ("passages", "records", "sources", "bundles"):
                self.conn.execute("DELETE FROM " + table)
            for loaded in prepared:
                self._store_bundle(*loaded)
        return {"bundles": len(bundles), "records": self.conn.execute("SELECT count(*) FROM records").fetchone()[0]}



def evaluate(project_root, protocol_path, output_root=None):
    """Execute the unchanged freeze after ordinary independent fixtures pass."""
    root = Path(project_root).resolve()
    protocol_path = within(root, root / protocol_path)
    base = protocol_path.parent
    freeze = read_json(base / "frozen-inputs/FREEZE.json")
    for path_key, hash_key in (("protocol_path", "protocol_sha256"), ("source_manifest_path", "source_manifest_sha256"), ("normalized_records_path", "normalized_records_sha256")):
        if sha256(within(base, base / freeze[path_key])) != freeze[hash_key]:
            raise ValueError("Frozen contract hash mismatch: " + path_key)
    protocol = read_json(protocol_path)
    if protocol["source_manifest"] != read_json(base / freeze["source_manifest_path"])["files"]:
        raise ValueError("Frozen protocol and source manifest disagree")
    output_root = within(root, root / output_root) if output_root else base / "retrieval-results"
    if output_root.exists() and any(output_root.iterdir()):
        raise ValueError("Evaluation outputs already exist; select a new output directory to preserve them")
    config = protocol["shared_route_configuration"]
    if config["network_calls"] or config["worker_calls"]:
        raise ValueError("Evaluation permits zero external calls only")
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "implementation-snapshot.py").write_bytes(Path(__file__).read_bytes())
    filters = dict(entities=config["entity_filter"], security_id=config["security_filter"].split(";", 1)[0],
                   record_types=config["record_types"], review_statuses=config["review_status_filter"],
                   evidence_cutoff=protocol["evidence_cutoff"], retrospective=True)
    packet_args = dict(max_records=config["max_records"], max_packet_utf8_bytes=config["max_packet_utf8_bytes"],
                       historical_label=protocol["historical_label"], balance=False, **filters)
    state = root / "state/research-memory" / ("evaluation-" + digest(str(output_root))[:16])
    results = {}
    with ResearchMemory(root, state) as memory:
        memory.import_bundle(str((base / freeze["normalized_records_path"]).relative_to(root)),
                             str((base / freeze["source_manifest_path"]).relative_to(root)), str(base.relative_to(root)), frozen=True)
        # Neither gold, expected exclusions nor evaluator polarity enter query inputs.
        for route in ("baseline", "new"):
            if route == "baseline":
                # Independent direct-file route: no FTS/index record projection.
                direct_records, direct_sources, _ = load_bundle(root, str((base / freeze["normalized_records_path"]).relative_to(root)),
                    str((base / freeze["source_manifest_path"]).relative_to(root)), str(base.relative_to(root)), frozen=True)
                result = build_packet(direct_records, direct_sources, baseline_ids(direct_records, config["query_terms"]), query_terms=config["query_terms"], **packet_args)
            else:
                result = memory.query(config["query_terms"], route=route, fts_query=protocol["routes"]["new"]["fts_query"], **packet_args)
            folder = output_root / route
            folder.mkdir(parents=True)
            (folder / "packet.json").write_bytes(canonical(result["packet"]).encode("utf-8"))
            save_json(folder / "exclusions.json", result["excluded"])
            returned = {r["id"]: r for r in result["packet"]["records"]}
            gold_results = []
            for gold in protocol["gold"]:
                record = returned.get(gold["record_id"])
                missing = [s for s in gold["required_exact_passages"] if not record or s not in record["text"]]
                gold_results.append({"id": gold["id"], "passed": not missing, "missing_passages": missing})
            original_records = read_json(base / freeze["normalized_records_path"])["records"]
            original = {r["id"]: r for r in original_records}
            table_id = protocol["table_contract"]["record_id"]
            table = returned.get(table_id)
            table_ok = bool(table and table["text"] == original[table_id]["text"] and len(table["table"]["rows"]) == 6
                            and table["table"]["column_labels"] == protocol["table_contract"]["normalized_column_labels"]
                            and table["table"]["original_headers_claimed"] is False)
            exclusions = {r["record_id"]: r for r in result["excluded"]}
            negative = [{"id": c["record_id"], "passed": c["record_id"] not in returned and c["record_id"] in exclusions,
                         "reason": exclusions.get(c["record_id"], {}).get("reason")} for c in protocol["negative_controls"]]
            records, sources = memory.data()
            source_records = {r["id"]: r for r in records}
            synthetic = []
            for control in protocol["synthetic_controls"]["cases"]:
                mutated = copy.deepcopy(source_records[control["base_record"]])
                mutation = control["mutation"]
                for key, value in mutation.items():
                    if key == "text_replace":
                        mutated["text"] = mutated["text"].replace(*value)
                    elif key not in {"keep_original_hash", "keep_original_text"}:
                        mutated[key] = value
                test = build_packet([mutated], sources, [mutated["id"]], query_terms=config["query_terms"], **packet_args)
                synthetic.append({"id": control["id"], "passed": not test["selected_record_ids"] and bool(test["excluded"]),
                                  "reason": test["excluded"][0]["reason"] if test["excluded"] else None})
            rebuild_result = None
            if route == "new":
                before = result
                memory.rebuild()
                after = memory.query(config["query_terms"], route=route, fts_query=protocol["routes"][route]["fts_query"], **packet_args)
                rebuild_result = all(before[k] == after[k] for k in ("packet_sha256", "selected_record_ids", "excluded"))
            report = dict(protocol_sha256=sha256(protocol_path), baseline_commit=protocol["baseline_commit"],
                evaluation_code_revision={"path": "tools/research_memory.py", "sha256": sha256(Path(__file__))},
                route_id=protocol["routes"][route]["id"], query=protocol["question"], cutoff=protocol["evidence_cutoff"],
                source_set_sha256=freeze["source_manifest_sha256"], normalization_sha256=freeze["normalized_records_sha256"],
                selected_record_ids=result["selected_record_ids"], excluded_record_ids_and_reasons=result["excluded"],
                gold_item_results=gold_results, table_preservation_result=table_ok,
                cutoff_result=negative, stale_supersession_result=[x for x in negative if "superseded" in str(x.get("reason"))],
                inclusion_reason_source_reference_result=all(r.get("inclusion_reason") and r.get("source_reference") for r in returned.values()),
                synthetic_control_results_separate=synthetic, rebuild_result=rebuild_result,
                packet_sha256=result["packet_sha256"], packet_utf8_bytes=result["packet_utf8_bytes"], record_count=result["record_count"],
                network_calls=0, worker_calls=0, actual_usage_if_exposed_otherwise_unavailable={"tokens": None, "cost": None, "reason": "No model calls; unavailable/not applicable"},
                timing_if_measured_with_environment=None, limitations=protocol["known_limitations"])
            report["primary_passed"] = all(x["passed"] for x in gold_results + negative) and table_ok and report["inclusion_reason_source_reference_result"] and result["complete_within_bounds"]
            report["controls_passed"] = all(x["passed"] for x in synthetic) and rebuild_result is not False
            save_json(folder / "evaluation.json", report)
            results[route] = report
    comparison = {"schema": "cr2.retrieval.comparison.v1", "protocol_sha256": sha256(protocol_path),
                  "route_results": {route: {"primary_passed": v["primary_passed"], "controls_passed": v["controls_passed"],
                    "selected_record_ids": v["selected_record_ids"], "packet_sha256": v["packet_sha256"], "packet_utf8_bytes": v["packet_utf8_bytes"]} for route, v in results.items()},
                  "same_selected_set": set(results["baseline"]["selected_record_ids"]) == set(results["new"]["selected_record_ids"]),
                  "efficiency_gain_claimed": False, "worker_calls": 0, "network_calls": 0,
                  "conclusion": "Deterministic historical retrieval only; no timing, cost saving, research approval or edge claim."}
    save_json(output_root / "COMPARISON.json", comparison)
    return comparison


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--state-root")
    sub = parser.add_subparsers(dest="command", required=True)
    imp = sub.add_parser("import", help="Import explicit source manifest and normalized records")
    imp.add_argument("--records", required=True)
    imp.add_argument("--manifest", required=True)
    imp.add_argument("--source-root")
    query = sub.add_parser("query", help="Retrieve exact scoped records with source integrity checks")
    query.add_argument("--term", action="append", required=True)
    query.add_argument("--entity", action="append", required=True)
    query.add_argument("--security")
    query.add_argument("--question-scope")
    query.add_argument("--type", action="append", choices=sorted(TYPES))
    query.add_argument("--review-status", action="append")
    query.add_argument("--cutoff", required=True)
    query.add_argument("--period")
    query.add_argument("--basis")
    query.add_argument("--unit")
    query.add_argument("--scope")
    query.add_argument("--max-records", type=int, default=16)
    query.add_argument("--max-bytes", type=int, default=32768)
    query.add_argument("--include-superseded", action="store_true")
    query.add_argument("--retrospective", action="store_true")
    sub.add_parser("rebuild", help="Delete/reimport only the derived index from explicit bundles")
    ev = sub.add_parser("evaluate", help="Run both frozen routes with zero worker/network calls")
    ev.add_argument("--protocol", required=True)
    ev.add_argument("--output-root")
    args = parser.parse_args(argv)
    try:
        if args.command == "evaluate":
            result = evaluate(args.root, args.protocol, args.output_root)
        else:
            with ResearchMemory(args.root, args.state_root) as memory:
                if args.command == "import":
                    result = memory.import_bundle(args.records, args.manifest, args.source_root)
                elif args.command == "rebuild":
                    result = memory.rebuild()
                else:
                    result = memory.query(args.term, entities=args.entity, security_id=args.security, question_scope=args.question_scope,
                        record_types=args.type, review_statuses=args.review_status, evidence_cutoff=args.cutoff,
                        period=args.period, accounting_basis=args.basis, unit=args.unit, scope=args.scope,
                        max_records=args.max_records, max_packet_utf8_bytes=args.max_bytes,
                        include_superseded=args.include_superseded, retrospective=args.retrospective)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError, sqlite3.Error) as exc:
        print("Research memory refused: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
