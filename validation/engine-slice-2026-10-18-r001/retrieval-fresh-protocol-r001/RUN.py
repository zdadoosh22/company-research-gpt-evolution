"""Execute only after coordinator review. Offline archival engineering comparison."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import timedelta

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def verify():
    freeze = read(BASE / "FREEZE.json")
    for relative, expected in freeze["files"].items():
        path = (BASE / relative).resolve()
        assert path.is_relative_to(BASE), "Freeze path escape"
        data = path.read_bytes()
        assert sha(data) == expected["sha256"] and len(data) == expected["bytes"], relative
    protocol = read(BASE / "protocol.json")
    assert sha((ROOT / "tools/research_memory.py").read_bytes()) == protocol["implementation_sha256"]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    assert head == protocol["implementation_commit"], "Code revision changed; new reviewed revision required"
    manifest = read(BASE / protocol["source_manifest"])
    register = read(BASE / protocol["source_register"])
    assert len(manifest["files"]) == len(register["files"])
    for source, registered in zip(manifest["files"], register["files"]):
        assert all(source[k] == registered[k] for k in source)
        original = (ROOT / source["repository_path"]).resolve()
        snapshot = (BASE / registered["snapshot_path"]).resolve()
        assert original.is_relative_to(ROOT) and snapshot.is_relative_to(BASE)
        data = original.read_bytes()
        assert data == snapshot.read_bytes()
        assert sha(data) == source["sha256"] and len(data) == source["bytes"]
        git_data = subprocess.check_output(["git", "show", registered["version_commit"] + ":" + source["repository_path"]], cwd=ROOT)
        assert git_data == data
    raw = read(BASE / protocol["normalized_records"])
    for record in raw["records"]:
        assert not {"polarity", "expected_exclusion_reason", "evaluator_role", "gold"}.intersection(record)
    return protocol


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-name", required=True, help="New output subdirectory name")
    args = parser.parse_args()
    assert args.output_name and Path(args.output_name).name == args.output_name
    assert args.output_name not in {".", "..", "raw"}
    protocol = verify()  # No retrieval import/index/ranking before contract verification.
    out = BASE / args.output_name
    out.mkdir(exist_ok=False)
    sys.path.insert(0, str(ROOT / "tools"))
    from research_memory import ResearchMemory, load_bundle, baseline_ids, build_packet, canonical, stamp
    cfg = copy.deepcopy(protocol["shared_route_configuration"])
    terms, fts = cfg.pop("query_terms"), cfg.pop("fts_query")
    assert cfg["balance"] is True and cfg["max_records"] == 16 and cfg["max_packet_utf8_bytes"] == 32768
    assert protocol["worker_calls"] == protocol["network_calls"] == 0
    records_path = (BASE / protocol["normalized_records"]).relative_to(ROOT).as_posix()
    manifest_path = (BASE / protocol["source_manifest"]).relative_to(ROOT).as_posix()
    state = ROOT / "state/research-memory" / ("fresh-nflx-" + sha(str(out).encode())[:20])
    assert not state.exists(), "Use fresh output/state name"
    results = {}
    records, sources, provenance = load_bundle(ROOT, records_path, manifest_path, frozen=False)
    results["direct"] = build_packet(records, sources, baseline_ids(records, terms), query_terms=terms, **cfg)
    write(out / "direct.json", results["direct"])
    with ResearchMemory(ROOT, state) as memory:
        imported = memory.import_bundle(records_path, manifest_path, frozen=False)
        write(out / "import.json", imported)
        results["fts"] = memory.query(terms, route="new", fts_query=fts, **cfg)
        write(out / "fts.json", results["fts"])
        verify()
        write(out / "rebuild.json", memory.rebuild())
        results["rebuilt"] = memory.query(terms, route="new", fts_query=fts, **cfg)
        write(out / "rebuilt.json", results["rebuilt"])
    # Evaluation-only gold is read after all primary retrieval results are fixed.
    rubric = read(BASE / protocol["gold"])
    assessments = {}
    for route, result in results.items():
        returned = {r["id"]: r for r in result["packet"]["records"]}
        excluded = {r["record_id"]: r for r in result["excluded"]}
        exact = [{"record_id": item["record_id"], "passed": item["record_id"] in returned and all(p in returned[item["record_id"]]["text"] for p in item["required_exact_passages"])} for item in rubric["gold"]]
        negatives = [{"record_id": item["record_id"], "passed": item["record_id"] not in returned and excluded.get(item["record_id"], {}).get("reason") == item["reason"]} for item in rubric["negative_controls"]]
        packet_bytes = canonical(result["packet"]).encode("utf-8")
        refs = all(r.get("inclusion_reason") and r.get("source_reference") == {"source_id": r["source_id"], "path": r["source_path"], "sha256": r["source_sha256"], "location": r["location"]} for r in returned.values())
        assessments[route] = dict(gold=exact, negative_controls=negatives, source_reference_checks=refs,
            bounds_pass=len(returned) <= 16 and len(packet_bytes) <= 32768,
            hash_pass=sha(packet_bytes) == result["packet_sha256"],
            byte_count_pass=len(packet_bytes) == result["packet_utf8_bytes"],
            complete_within_bounds=result["complete_within_bounds"])
    # Fault injections remain outside original bundles, FTS index and primary results.
    controls = []
    original = next(r for r in records if r["id"] == "nflx-receipt-reference")
    for label, mutation, reason in [
        ("synthetic-expiry", {"valid_until": "2026-10-09"}, "expired-for-current-reuse"),
        ("synthetic-supersession", {"superseded_by": "synthetic-successor", "superseded_effective_at": "2026-10-10"}, "superseded-for-default-reuse")]:
        changed = copy.deepcopy(original)
        changed.update(mutation)
        result = build_packet([changed], sources, [changed["id"]], query_terms=terms, **cfg)
        passed = not result["packet"]["records"] and any(x["record_id"] == changed["id"] and x["reason"] == reason for x in result["excluded"])
        controls.append(dict(label=label, engineering_fault_injection=True, mutation=mutation, passed=passed, result=result))
    early = copy.deepcopy(cfg)
    early["evidence_cutoff"] = (stamp(original["versioned_no_later_than"]) - timedelta(seconds=1)).isoformat()
    early_result = build_packet(records, sources, baseline_ids(records, terms), query_terms=terms, **early)
    excluded = {x["record_id"]: x["reason"] for x in early_result["excluded"]}
    early_ids = [r["id"] for r in records if r["source_id"] == original["source_id"]]
    controls.append(dict(label="before-preserved-version-availability", passed=all(excluded.get(key) == "analytical-conclusion-after-cutoff" for key in early_ids), result=early_result))
    write(out / "controls.json", controls)
    rebuilt_equal = all(results["fts"][key] == results["rebuilt"][key] for key in ["packet", "packet_sha256", "selected_record_ids", "excluded"])
    verify()
    write(out / "assessment.json", dict(routes=assessments, rebuild_equivalent=rebuilt_equal,
        controls_pass=all(c["passed"] for c in controls), source_provenance=provenance,
        runner_sha256=sha(Path(__file__).read_bytes()), protocol_sha256=sha((BASE / "protocol.json").read_bytes()),
        call_scope="Runner invokes only local filesystem/Git, Python standard library and deterministic research_memory APIs; no model/network transport is invoked. No system-wide transport interception or measurement is claimed.",
        model_calls_in_this_runner=0, network_calls_in_this_runner=0,
        disposition="Archival engineering evidence only; no research/review/trade acceptance promotion."))
    print(str(out / "assessment.json"))


if __name__ == "__main__":
    main()
