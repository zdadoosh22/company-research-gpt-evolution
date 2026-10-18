"""Capture a deterministic suite with durable before/after source evidence."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def snapshot(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for base in (root / "tools", root / "validation/tests")
            for p in sorted(base.rglob("*")) if p.is_file() and p.suffix in {".py", ".ps1"}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--output-base", required=True)
    args = parser.parse_args()
    root, output = Path(args.root).resolve(), Path(args.output_base).resolve()
    files = snapshot(root)
    record = {"started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "files": files, "scope": "Deterministic suite; no live research inference"}
    start = output.with_name(output.name + "-start.json")
    if start.exists():
        raise ValueError("Preserve existing run; choose a new output base")
    start.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    with output.with_suffix(".txt").open("w", encoding="utf-8") as log:
        completed = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "validation/tests"],
                                   cwd=root, stdout=log, stderr=subprocess.STDOUT)
    record.update(completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  exit_code=completed.returncode, source_snapshot_unchanged=snapshot(root) == files)
    output.with_name(output.name + "-manifest.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in record.items() if k != "files"}))
