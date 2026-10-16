import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from research_packet import prepare_packet, stage_packet


class ResearchPacketTests(unittest.TestCase):
    def test_loaded_bytes_must_still_match_verified_file(self):
        from scoped_research_adapter import _file
        changed=[]
        def verified_then_changed(root,record):
            path=_file(root,record)
            if record.get('source_id')=='filing' and not changed:
                path.write_bytes(path.read_bytes()+b'Changed after manifest verification.');changed.append(True)
            return path
        with patch('scoped_research_adapter._file',side_effect=verified_then_changed):
            with self.assertRaisesRegex(ValueError,'Original bytes changed'):
                prepare_packet(self.root,self.job,self.schema)

    def test_late_capture_is_labelled_retrospective(self):
        self.job['as_of']='2020-01-15T00:00:00Z'
        packet=prepare_packet(self.root,self.job,self.schema)
        self.assertTrue(packet['content']['historical_reconstruction'])
        self.assertIn('not contemporaneous',packet['content']['capture_label'])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.context = {"entity": "Example plc", "security": "EXAMPLE:ORD", "period": "FY2020",
                        "basis": "reported", "unit": "million", "currency": "GBP"}

        def artifact(relative, data):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
            return {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

        self.method = artifact("method.md", "Approved method")
        self.scoped = artifact("scoped.md", "Scoped method")
        self.target = artifact("target.md", "Review target")
        source_data = "Revenue\tFY2020\n10\nNote 1: reported in GBP.\n".encode()
        self.source = artifact("source.txt", source_data)
        self.source.update(source_id="filing", published_at="2020-01-01", accessed_at="2020-02-01",
                           read_locations=["Page 1, Revenue"])
        passage_range = (source_data.index(b"10\n"), source_data.index(b"10\n") + len(b"10\n"))
        header = b"Revenue\tFY2020\n"
        footnote = b"Note 1: reported in GBP.\n"
        self.schema = {"type": "object", "required": ["status"]}
        self.job = {
            "schema_version": 2, "job_id": "packet-test", "role": "analysis",
            "as_of": "2020-03-01T00:00:00Z", "scope": {"required_categories": ["revenue"]},
            "methodology": {"base": self.method, "scoped": self.scoped}, "target": self.target,
            "sources": [self.source],
            "packet": {"schema_version": 1, "context": copy.deepcopy(self.context), "max_utf8_bytes": 20000,
                "passages": [{"source_id": "filing", "location": "Page 1, Revenue",
                    "text_file": {"path": self.source["path"], "sha256": self.source["sha256"]},
                    "range": {"start_byte": passage_range[0], "end_byte": passage_range[1],
                              "sha256": hashlib.sha256(source_data[slice(*passage_range)]).hexdigest()},
                    "metadata": copy.deepcopy(self.context),
                    "extraction": {"method": "utf8-byte-range", "version": "1", "status": "complete",
                                   "original_sha256": self.source["sha256"]},
                    "table_context": {"kind": "table",
                        "headers": [{"start_byte": 0, "end_byte": len(header), "sha256": hashlib.sha256(header).hexdigest()}],
                        "footnotes": [{"start_byte": source_data.index(footnote),
                                       "end_byte": source_data.index(footnote) + len(footnote),
                                       "sha256": hashlib.sha256(footnote).hexdigest()}]}}]},
        }

    def tearDown(self):
        self.temp.cleanup()

    def prepare(self, job=None):
        return prepare_packet(self.root, self.job if job is None else job, self.schema)

    def test_exact_passage_headers_footnotes_and_hashes_are_frozen(self):
        packet = self.prepare()
        passage = packet["content"]["passages"][0]
        self.assertEqual(passage["content"]["text"], "10\n")
        self.assertEqual(passage["table_context"]["headers"][0]["text"], "Revenue\tFY2020\n")
        self.assertEqual(passage["table_context"]["footnotes"][0]["text"], "Note 1: reported in GBP.\n")
        self.assertTrue(passage["qualifying_evidence"])
        self.assertEqual(packet["sha256"], hashlib.sha256(packet["bytes"]).hexdigest())

    def test_direct_call_rejects_future_scope_publication_and_access(self):
        for field, value in (("as_of", "2099-01-01T00:00:00Z"),
                             ("published_at", "2099-01-01"),
                             ("accessed_at", "2099-01-01T00:00:00Z")):
            with self.subTest(field=field):
                job = copy.deepcopy(self.job)
                if field == "as_of":
                    job[field] = value
                else:
                    job["sources"][0][field] = value
                with self.assertRaises(ValueError):
                    self.prepare(job)

    def test_unknown_publication_requires_valid_snapshot_provenance(self):
        job = copy.deepcopy(self.job)
        job["sources"][0]["published_at"] = None
        with self.assertRaises(ValueError):
            self.prepare(job)
        job["sources"][0].update(date_status="publication-date-unknown-snapshot",
                                 captured_at="2020-02-01T00:00:00Z")
        packet = self.prepare(job)
        self.assertIn("publication-date-unknown", packet["content"]["passages"][0]["gaps"])
        self.assertFalse(packet["eligibility"][("filing", "Page 1, Revenue")])
        job["sources"][0]["captured_at"] = "2020-04-01T00:00:00Z"
        with self.assertRaises(ValueError):
            self.prepare(job)

    def test_unknown_and_incompatible_context_are_explicit_gaps(self):
        job = copy.deepcopy(self.job)
        job["packet"]["passages"][0]["metadata"]["currency"] = None
        packet = self.prepare(job)
        self.assertIn("unknown-currency", packet["content"]["passages"][0]["gaps"])
        self.assertFalse(packet["eligibility"][("filing", "Page 1, Revenue")])
        job["packet"]["passages"][0]["metadata"]["currency"] = "USD"
        packet = self.prepare(job)
        self.assertIn("incompatible-currency", packet["content"]["passages"][0]["gaps"])

    def test_tampered_ranges_and_manifest_path_escape_fail_closed(self):
        job = copy.deepcopy(self.job)
        job["packet"]["passages"][0]["range"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Passage bytes differ"):
            self.prepare(job)
        job = copy.deepcopy(self.job)
        job["target"]["path"] = "../outside.md"
        with self.assertRaises(ValueError):
            self.prepare(job)

    def test_omitted_authorized_source_location_is_rejected(self):
        extra = self.root / "source2.txt"
        extra.write_text("Additional source", encoding="utf-8")
        source = {"source_id": "second", "path": "source2.txt",
                  "sha256": hashlib.sha256(extra.read_bytes()).hexdigest(),
                  "published_at": "2020-01-01", "accessed_at": "2020-02-01",
                  "read_locations": ["Page 2"]}
        job = copy.deepcopy(self.job)
        job["sources"].append(source)
        with self.assertRaisesRegex(ValueError, "omitted an authorized"):
            self.prepare(job)

    def test_staging_rejects_packet_or_schema_mutation(self):
        packet = self.prepare()
        directory = Path(self.temp.name) / "stage"
        directory.mkdir()
        changed = copy.deepcopy(packet)
        changed["content"]["job_id"] = "mutated"
        with self.assertRaisesRegex(ValueError, "content changed"):
            stage_packet(changed, self.schema, directory)
        with self.assertRaisesRegex(ValueError, "schema changed"):
            stage_packet(packet, {"type": "string"}, directory)
        self.assertEqual(list(directory.iterdir()), [])
        hashes = stage_packet(packet, self.schema, directory)
        self.assertEqual(set(hashes), {"packet.json", "schema.json"})


if __name__ == "__main__":
    unittest.main()
