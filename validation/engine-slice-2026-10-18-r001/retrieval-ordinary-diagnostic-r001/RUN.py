"""One non-held-out diagnostic; no changes to original protocol or implementation."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from research_memory import ResearchMemory, load_bundle, build_packet, baseline_ids, canonical


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(name, value):
    path = HERE / name
    if path.exists():
        raise ValueError("Preserve existing diagnostic output")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


protocol = read(HERE / "PROTOCOL.json")
for key in ("original_protocol", "freeze", "implementation"):
    ref = protocol[key]
    assert hashlib.sha256((ROOT / ref["path"]).read_bytes()).hexdigest() == ref["sha256"]
original_path = ROOT / protocol["original_protocol"]["path"]
base = original_path.parent
original = read(original_path)
freeze = read(ROOT / protocol["freeze"]["path"])
for path_key, hash_key in (("protocol_path", "protocol_sha256"),
                          ("source_manifest_path", "source_manifest_sha256"),
                          ("normalized_records_path", "normalized_records_sha256")):
    assert hashlib.sha256((base / freeze[path_key]).read_bytes()).hexdigest() == freeze[hash_key]
config = protocol["shared_configuration"]
assert config == original["shared_route_configuration"]
args = dict(entities=config["entity_filter"], security_id=config["security_filter"].split(";", 1)[0],
            record_types=config["record_types"], review_statuses=config["review_status_filter"],
            evidence_cutoff=protocol["evidence_cutoff"], retrospective=True,
            max_records=config["max_records"], max_packet_utf8_bytes=config["max_packet_utf8_bytes"],
            historical_label=original["historical_label"], balance=True)
bundle = (str((base / freeze["normalized_records_path"]).relative_to(ROOT)),
          str((base / freeze["source_manifest_path"]).relative_to(ROOT)), str(base.relative_to(ROOT)))
records, sources, _ = load_bundle(ROOT, *bundle, frozen=True)
state = ROOT / "state/research-memory/ordinary-diagnostic-20261018-r001"
results = {}
with ResearchMemory(ROOT, state) as memory:
    memory.import_bundle(*bundle, frozen=True)
    results["direct"] = build_packet(records, sources, baseline_ids(records, config["query_terms"]),
                                    query_terms=config["query_terms"], **args)
    results["fts"] = memory.query(config["query_terms"], fts_query=original["routes"]["new"]["fts_query"], **args)
    memory.rebuild()
    rebuilt = memory.query(config["query_terms"], fts_query=original["routes"]["new"]["fts_query"], **args)
    rebuild_equal = all(rebuilt[k] == results["fts"][k] for k in
                        ("packet_sha256", "selected_record_ids", "excluded"))

# Scoring is downstream of packet selection; gold never enters either route.
reports = {}
source_records = {r["id"]: r for r in read(base / freeze["normalized_records_path"])["records"]}
for route, result in results.items():
    save(route + "-packet.json", result["packet"])
    save(route + "-exclusions.json", result["excluded"])
    returned = {r["id"]: r for r in result["packet"]["records"]}
    exclusions = {r["record_id"]: r for r in result["excluded"]}
    gold = [{"id": g["id"], "record_id": g["record_id"],
             "passed": g["record_id"] in returned and all(
                 text in returned[g["record_id"]]["text"] for text in g["required_exact_passages"])}
            for g in original["gold"]]
    negatives = [{"id": n["record_id"], "passed": n["record_id"] not in returned and n["record_id"] in exclusions,
                  "reason": exclusions.get(n["record_id"], {}).get("reason")}
                 for n in original["negative_controls"]]
    table_id = original["table_contract"]["record_id"]
    table = returned.get(table_id)
    table_ok = bool(table and table["text"] == source_records[table_id]["text"] and
                    len(table["table"]["rows"]) == 6 and
                    table["table"]["column_labels"] == original["table_contract"]["normalized_column_labels"] and
                    table["table"]["original_headers_claimed"] is False)
    reports[route] = dict(selected_record_ids=result["selected_record_ids"], gold=gold,
                         negatives=negatives, table_preserved=table_ok,
                         packet_sha256=result["packet_sha256"], packet_utf8_bytes=result["packet_utf8_bytes"],
                         source_refs_and_reasons=all(r.get("source_reference") and r.get("inclusion_reason") for r in returned.values()))
save("RESULT.json", dict(label=protocol["label"], routes=reports, rebuild_equal=rebuild_equal,
                         worker_calls=0, network_calls=0, original_frozen_result="unchanged:4/5each route",
                         limitations=protocol["limitations"]))
print(json.dumps({k: {"gold_passed": sum(x["passed"] for x in v["gold"]),
                      "negative_controls_passed": sum(x["passed"] for x in v["negatives"]),
                      "table_preserved": v["table_preserved"], "bytes": v["packet_utf8_bytes"]}
                  for k, v in reports.items()}))
