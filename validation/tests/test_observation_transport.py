"""Offline tests: no real accounts, tokens or messages."""
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import observation_transport as transport
from observation_core import Store


class FakeClient:
    allowed_chat_id = "123"

    def __init__(self, failure=None, updates=None):
        self.failure = failure
        self.updates = updates or []
        self.calls = []

    def send_message(self, text, markup=None):
        self.calls.append(("send", text))
        if self.failure:
            raise self.failure
        return 99

    def edit_message(self, message_id, text, markup=None):
        self.calls.append(("edit", message_id, text))
        if self.failure:
            raise self.failure
        return True

    def get_updates(self, offset):
        self.calls.append(("poll", offset))
        return self.updates


class Response(io.BytesIO):
    pass


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        transport.init_transport(self.conn)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def send(self, key="one"):
        with self.conn:
            return transport.enqueue_send(self.conn, "Observation only", key)

    def state(self, ident):
        return self.conn.execute("SELECT state,attempts FROM transport_outbox WHERE id=?", (ident,)).fetchone()

    def test_durable_deduplication_and_completed_send(self):
        ident = self.send()
        self.assertEqual(ident, self.send())
        client = FakeClient()
        result = transport.dispatch_outbox(self.conn, client, now=100)
        self.assertEqual(result[0]["message_id"], 99)
        transport.dispatch_outbox(self.conn, client, now=102)
        self.assertEqual(self.state(ident), ("sent", 1))
        self.assertEqual(len(client.calls), 1)

    def test_uncertain_send_never_blind_retries(self):
        ident = self.send()
        client = FakeClient(transport.TransportError("timeout", retryable=True, uncertain=True))
        transport.dispatch_outbox(self.conn, client, now=100)
        transport.dispatch_outbox(self.conn, client, now=10000)
        self.assertEqual(self.state(ident), ("uncertain", 1))
        self.assertEqual(len(client.calls), 1)

    def test_crashed_send_recovered_as_uncertain(self):
        ident = self.send()
        with self.conn:
            self.conn.execute("UPDATE transport_outbox SET state='inflight' WHERE id=?", (ident,))
        client = FakeClient()
        transport.dispatch_outbox(self.conn, client, now=100)
        self.assertEqual(self.state(ident)[0], "uncertain")
        self.assertFalse(client.calls)

    def test_rejected_rate_limit_retries_bounded_and_delayed(self):
        ident = self.send()
        client = FakeClient(transport.TransportError("rate_limited", retryable=True, retry_after=30))
        transport.dispatch_outbox(self.conn, client, now=100)
        transport.dispatch_outbox(self.conn, client, now=110)
        self.assertEqual(len(client.calls), 1)
        for now in (130, 160, 190, 220):
            transport.dispatch_outbox(self.conn, client, now=now)
        self.assertEqual(self.state(ident), ("failed", 5))

    def test_edit_can_retry_after_uncertain_network_failure(self):
        with self.conn:
            ident = transport.enqueue_edit(self.conn, 99, "WITHDRAWN", "withdraw-one")
        client = FakeClient(transport.TransportError("timeout", retryable=True, uncertain=True))
        transport.dispatch_outbox(self.conn, client, now=100)
        self.assertEqual(self.state(ident), ("pending", 1))
        client.failure = None
        transport.dispatch_outbox(self.conn, client, now=102)
        self.assertEqual(self.state(ident), ("sent", 2))

    def test_single_chat_throttle(self):
        self.send("one")
        self.send("two")
        client = FakeClient()
        transport.dispatch_outbox(self.conn, client, now=100)
        self.assertEqual(len(client.calls), 1)
        transport.dispatch_outbox(self.conn, client, now=100.5)
        self.assertEqual(len(client.calls), 1)
        transport.dispatch_outbox(self.conn, client, now=101)
        self.assertEqual(len(client.calls), 2)

    def test_update_handler_offset_and_replies_commit_together(self):
        update = {"update_id": 4, "message": {"chat": {"id": 123, "type": "private"}, "from": {"id": 123}, "text": "/status"}}
        client = FakeClient(updates=[update, update])
        called = []

        def handler(conn, item):
            called.append(item["update_id"])
            transport.enqueue_send(conn, "Current snapshot", "reply-4")

        self.assertEqual(transport.ingest_updates(self.conn, client, handler, now=100), 1)
        self.assertEqual(transport.ingest_updates(self.conn, client, handler, now=101), 0)
        self.assertEqual(called, [4])
        self.assertEqual(self.conn.execute("SELECT value FROM transport_meta WHERE key='offset'").fetchone()[0], "5")
        self.assertEqual(self.conn.execute("SELECT count(*) FROM transport_outbox").fetchone()[0], 1)

    def test_handler_failure_rolls_back_reply_dedup_and_offset(self):
        client = FakeClient(updates=[{"update_id": 4, "message": {"chat": {"id": 123, "type": "private"}, "from": {"id": 123}}}])

        def bad_handler(conn, update):
            transport.enqueue_send(conn, "reply", "reply-4")
            raise ValueError("bad command")

        with self.assertRaises(ValueError):
            transport.ingest_updates(self.conn, client, bad_handler)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM transport_outbox").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM transport_updates").fetchone()[0], 0)
        self.assertIsNone(self.conn.execute("SELECT value FROM transport_meta WHERE key='offset'").fetchone())

    def test_store_acknowledgement_rolls_back_with_update_failure(self):
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("CREATE TABLE alerts(id TEXT PRIMARY KEY,status TEXT,payload TEXT)")
        self.conn.execute("CREATE TABLE events(id INTEGER PRIMARY KEY,created_at TEXT,kind TEXT,payload TEXT)")
        self.conn.execute("INSERT INTO alerts VALUES('trial','active',?)",
                          (json.dumps({"expires_at": "2099-01-01T00:00:00+00:00"}),))
        self.conn.commit()
        store = Store.__new__(Store)
        store.conn = self.conn
        client = FakeClient(updates=[{"update_id": 4, "message": {"chat": {"id": 123, "type": "private"}, "from": {"id": 123}}}])

        def handler(conn, update):
            store.acknowledge("trial")
            transport.enqueue_send(conn, "acknowledged", "reply-4")
            raise ValueError("failure after nested ledger operation")

        with self.assertRaises(ValueError):
            transport.ingest_updates(self.conn, client, handler)
        self.assertEqual(self.conn.execute("SELECT status FROM alerts WHERE id='trial'").fetchone()[0], "active")
        self.assertEqual(self.conn.execute("SELECT count(*) FROM events").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM transport_outbox").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM transport_updates").fetchone()[0], 0)
        self.assertIsNone(self.conn.execute("SELECT value FROM transport_meta WHERE key='offset'").fetchone())

    def test_incoming_rejects_unrelated_pending_transaction(self):
        self.send()
        self.conn.execute("INSERT INTO transport_meta VALUES('unrelated','pending')")
        client = FakeClient()
        with self.assertRaises(RuntimeError):
            transport.ingest_updates(self.conn, client, lambda *args: None)
        self.assertTrue(self.conn.in_transaction)
        self.assertFalse(client.calls)
        self.conn.rollback()

    def test_unauthorized_chat_never_reaches_handler_or_retains_text(self):
        client = FakeClient(updates=[{"update_id": 1, "message": {"chat": {"id": 456}, "text": "external instructions"}}])
        transport.ingest_updates(self.conn, client, lambda *args: self.fail("unauthorized"))
        payload = self.conn.execute("SELECT payload FROM transport_updates").fetchone()[0]
        self.assertNotIn("external instructions", payload)

    def test_group_missing_identity_and_wrong_sender_are_rejected(self):
        updates = [
            {"update_id": 1, "message": {"chat": {"id": 123, "type": "group"}, "from": {"id": 123}}},
            {"update_id": 2, "message": {"chat": {"id": 123, "type": "private"}, "from": {"id": 456}}},
            {"update_id": 3, "message": {"chat": {"id": 123, "type": "private"}}},
            {"update_id": 4, "message": {"chat": {"id": 123}, "from": {"id": 123}}},
            {"update_id": 5, "callback_query": {"from": {"id": 456}, "message": {"chat": {"id": 123, "type": "private"}, "from": {"id": 123}}}},
        ]
        self.assertEqual(transport.ingest_updates(self.conn, FakeClient(updates=updates),
                         lambda *args: self.fail("unauthorized sender")), 0)

    def test_callback_checks_user_instead_of_bot_message_sender(self):
        updates = [{"update_id": 1, "callback_query": {"from": {"id": 123},
                    "message": {"chat": {"id": 123, "type": "private"}, "from": {"id": 999}}}}]
        called = []
        self.assertEqual(transport.ingest_updates(self.conn, FakeClient(updates=updates),
                         lambda conn, update: called.append(update)), 1)
        self.assertEqual(len(called), 1)

    def test_only_positive_private_chat_ids_can_be_configured(self):
        for value in (-123, "-123", 0, True, "@group", "0123"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                transport.TelegramClient("123:FAKE_TOKEN", value)

    def test_changed_payload_cannot_reuse_deduplication_key(self):
        ident = self.send()
        with self.assertRaises(ValueError):
            transport.enqueue_send(self.conn, "changed text", "one")
        with self.assertRaises(ValueError):
            transport.enqueue_edit(self.conn, 99, "Observation only", "one")
        self.assertEqual(self.state(ident), ("pending", 0))

    def test_dispatch_rejects_pending_unrelated_transaction(self):
        self.send()
        self.conn.execute("INSERT INTO transport_meta VALUES('unrelated','pending')")
        client = FakeClient()
        with self.assertRaises(RuntimeError):
            transport.dispatch_outbox(self.conn, client)
        self.assertFalse(client.calls)
        self.assertTrue(self.conn.in_transaction)
        self.conn.rollback()

    def test_preflight_supersedes_without_network_or_attempt(self):
        ident = self.send()
        client = FakeClient()
        checked = []
        def preflight(conn, item):
            self.assertTrue(conn.in_transaction)
            checked.append(item)
            return False
        result = transport.dispatch_outbox(self.conn, client, now=100, preflight=preflight)
        self.assertEqual(self.state(ident), ("superseded", 0))
        self.assertEqual(result[0]["state"], "superseded")
        self.assertEqual(checked[0]["dedup_key"], "one")
        self.assertFalse(client.calls)

    def test_preflight_failure_rolls_back_check_and_does_not_send(self):
        ident = self.send()
        client = FakeClient()
        def preflight(conn, item):
            conn.execute("INSERT INTO transport_meta VALUES('check-write','rollback')")
            raise ValueError("preflight failed")
        with self.assertRaises(ValueError):
            transport.dispatch_outbox(self.conn, client, now=100, preflight=preflight)
        self.assertEqual(self.state(ident), ("pending", 0))
        self.assertIsNone(self.conn.execute("SELECT value FROM transport_meta WHERE key='check-write'").fetchone())
        self.assertFalse(client.calls)

    def test_callback_answer_runs_after_commit_and_failure_does_not_undo(self):
        update = {"update_id": 1, "callback_query": {"id": "callback1", "from": {"id": 123},
                  "message": {"chat": {"id": 123, "type": "private"}, "from": {"id": 999}}}}
        client = FakeClient(updates=[update])
        answered = []
        def answer(callback_id, text):
            self.assertFalse(self.conn.in_transaction)
            self.assertEqual(self.conn.execute("SELECT count(*) FROM transport_updates").fetchone()[0], 1)
            answered.append(callback_id)
            raise RuntimeError("fake network failed")
        client.answer_callback = answer
        def handler(conn, item):
            transport.enqueue_send(conn, "status reply", "reply-1")
        self.assertEqual(transport.ingest_updates(self.conn, client, handler), 1)
        self.assertEqual(answered, ["callback1"])
        self.assertEqual(self.conn.execute("SELECT count(*) FROM transport_outbox").fetchone()[0], 1)
        self.assertEqual(transport.ingest_updates(self.conn, client, handler), 0)
        self.assertEqual(answered, ["callback1"])

    def test_callback_never_answered_after_rollback_or_wrong_sender(self):
        update = {"update_id": 1, "callback_query": {"id": "callback1", "from": {"id": 123},
                  "message": {"chat": {"id": 123, "type": "private"}}}}
        client = FakeClient(updates=[update])
        client.answer_callback = lambda *args: self.fail("callback should not be answered")
        with self.assertRaises(ValueError):
            transport.ingest_updates(self.conn, client, lambda *args: (_ for _ in ()).throw(ValueError("rollback")))
        update["callback_query"]["from"]["id"] = 456
        self.assertEqual(transport.ingest_updates(self.conn, client, lambda *args: self.fail("unauthorized")), 0)

    def test_invalid_outbox_payload_does_not_send(self):
        ident = self.send()
        with self.conn:
            self.conn.execute("UPDATE transport_outbox SET payload='[]' WHERE id=?", (ident,))
        client = FakeClient()
        transport.dispatch_outbox(self.conn, client, now=100)
        self.assertEqual(self.state(ident), ("failed", 1))
        self.assertFalse(client.calls)

    def test_malformed_updates_do_not_advance_offset(self):
        for value in (None, [None], [{"update_id": True}], [{"update_id": -1}]):
            client = FakeClient()
            client.get_updates = lambda offset: value
            with self.subTest(value=value), self.assertRaises(transport.TransportError):
                transport.ingest_updates(self.conn, client, lambda *args: self.fail("invalid update"))
            self.assertIsNone(self.conn.execute("SELECT value FROM transport_meta WHERE key='offset'").fetchone())

    def test_completed_send_then_process_death_is_not_retried(self):
        ident = self.send()
        class ProcessDeath(BaseException):
            pass
        client = FakeClient()
        def sent_then_died(text, markup=None):
            client.calls.append(("provider accepted", text))
            raise ProcessDeath()
        client.send_message = sent_then_died
        with self.assertRaises(ProcessDeath):
            transport.dispatch_outbox(self.conn, client, now=100)
        self.assertEqual(self.state(ident), ("inflight", 1))
        transport.dispatch_outbox(self.conn, client, now=102)
        self.assertEqual(self.state(ident), ("uncertain", 1))
        self.assertEqual(len(client.calls), 1)

    def test_http_server_failure_and_bad_success_body_are_uncertain(self):
        def failed(request, **kwargs):
            raise urllib.error.HTTPError(request.full_url, 502, "fake", {}, io.BytesIO(b"proxy error"))
        def malformed(request, **kwargs):
            return Response(b"not-json")
        def bad_id(request, **kwargs):
            return Response(b'{"ok":true,"result":{"message_id":true}}')
        for opener in (failed, malformed, bad_id):
            client = transport.TelegramClient("123:FAKE_TOKEN", 123, opener=opener)
            with self.subTest(opener=opener), self.assertRaises(transport.TransportError) as caught:
                client.send_message("Observation only")
            self.assertTrue(caught.exception.uncertain)

    def test_credential_urls_cannot_follow_redirects(self):
        handler = transport._NoRedirect()
        request = urllib.request.Request("https://api.telegram.org/bot123:FAKE_TOKEN/sendMessage")
        self.assertIsNone(handler.redirect_request(request, None, 302, "redirect", {}, "https://external.example/"))

    def test_incoming_marker_write_failure_rolls_back_handler_and_no_callback(self):
        update = {"update_id": 1, "callback_query": {"id": "callback1", "from": {"id": 123},
                  "message": {"chat": {"id": 123, "type": "private"}}}}
        self.conn.execute("CREATE TRIGGER reject_marker BEFORE INSERT ON transport_updates BEGIN SELECT RAISE(ABORT,'fault injection'); END")
        self.conn.commit()
        client = FakeClient(updates=[update])
        client.answer_callback = lambda *args: self.fail("uncommitted callback answered")
        def handler(conn, item):
            transport.enqueue_send(conn, "reply", "reply-1")
        with self.assertRaises(sqlite3.IntegrityError):
            transport.ingest_updates(self.conn, client, handler)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM transport_outbox").fetchone()[0], 0)
        self.assertIsNone(self.conn.execute("SELECT value FROM transport_meta WHERE key='offset'").fetchone())

    def test_claim_write_failure_does_not_contact_provider(self):
        ident = self.send()
        self.conn.execute("CREATE TRIGGER reject_claim BEFORE UPDATE ON transport_outbox WHEN NEW.state='inflight' BEGIN SELECT RAISE(ABORT,'fault injection'); END")
        self.conn.commit()
        client = FakeClient()
        with self.assertRaises(sqlite3.IntegrityError):
            transport.dispatch_outbox(self.conn, client, now=100)
        self.assertFalse(client.calls)
        self.assertEqual(self.state(ident), ("pending", 0))

    def test_result_write_failure_recovers_uncertain_without_duplicate(self):
        ident = self.send()
        self.conn.execute("CREATE TRIGGER reject_result BEFORE UPDATE ON transport_outbox WHEN NEW.state='sent' BEGIN SELECT RAISE(ABORT,'fault injection'); END")
        self.conn.commit()
        client = FakeClient()
        with self.assertRaises(sqlite3.IntegrityError):
            transport.dispatch_outbox(self.conn, client, now=100)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(self.state(ident), ("inflight", 1))
        transport.dispatch_outbox(self.conn, client, now=102)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(self.state(ident), ("uncertain", 1))

    def test_interrupted_fifth_edit_attempt_does_not_exceed_retry_bound(self):
        with self.conn:
            ident = transport.enqueue_edit(self.conn, 99, "WITHDRAWN", "withdraw-one")
            self.conn.execute("UPDATE transport_outbox SET state='inflight',attempts=5 WHERE id=?", (ident,))
        client = FakeClient()
        transport.dispatch_outbox(self.conn, client, now=100)
        self.assertEqual(self.state(ident), ("failed", 5))
        self.assertFalse(client.calls)

    def test_real_client_redacts_network_errors(self):
        def opener(request, **kwargs):
            raise urllib.error.URLError(request.full_url)
        client = transport.TelegramClient("123:FAKE_TOKEN", 123, opener=opener)
        with self.assertRaises(transport.TransportError) as caught:
            client.send_message("Observation only")
        self.assertTrue(caught.exception.uncertain)
        self.assertNotIn("FAKE_TOKEN", str(caught.exception))
        self.assertNotIn("FAKE_TOKEN", repr(client))

    def test_rate_limit_parsing_without_exposing_http_description(self):
        def opener(request, **kwargs):
            raise urllib.error.HTTPError(request.full_url, 429, "secret FAKE_TOKEN", {},
                io.BytesIO(b'{"parameters":{"retry_after":30}}'))
        client = transport.TelegramClient("123:FAKE_TOKEN", 123, opener=opener)
        with self.assertRaises(transport.TransportError) as caught:
            client.send_message("Observation only")
        self.assertFalse(caught.exception.uncertain)
        self.assertEqual(caught.exception.retry_after, 30)
        self.assertNotIn("FAKE_TOKEN", str(caught.exception))

    def test_success_payload_and_no_redirected_chat(self):
        requests = []
        def opener(request, **kwargs):
            requests.append(json.loads(request.data))
            return Response(b'{"ok":true,"result":{"message_id":77}}')
        client = transport.TelegramClient("123:FAKE_TOKEN", 123, opener=opener)
        self.assertEqual(client.send_message("Observation only"), 77)
        self.assertEqual(requests[0]["chat_id"], "123")

    def test_idempotent_edit_response(self):
        def opener(request, **kwargs):
            return Response(b'{"ok":false,"error_code":400,"description":"Bad Request: message is not modified"}')
        client = transport.TelegramClient("123:FAKE_TOKEN", 123, opener=opener)
        self.assertEqual(client.edit_message(77, "WITHDRAWN"), {"message_id": 77})

    def test_idempotent_edit_http_error(self):
        def opener(request, **kwargs):
            raise urllib.error.HTTPError(request.full_url, 400, "Bad Request", {},
                io.BytesIO(b'{"description":"Bad Request: message is not modified"}'))
        client = transport.TelegramClient("123:FAKE_TOKEN", 123, opener=opener)
        self.assertEqual(client.edit_message(77, "WITHDRAWN"), {"message_id": 77})

    def test_configuration_is_offline_and_encrypts_separate_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "telegram.dpapi"
            with patch.object(transport, "_dpapi", return_value=b"encrypted"), patch("urllib.request.urlopen") as network:
                transport.configure_credentials(path, "123:FAKE_TOKEN", 123)
                network.assert_not_called()
            self.assertEqual(path.read_bytes(), b"encrypted")

    @unittest.skipUnless(sys.platform == "win32", "Windows DPAPI only")
    def test_windows_dpapi_round_trip(self):
        clear = b"fake local test credential"
        protected = transport._dpapi(clear)
        self.assertNotEqual(clear, protected)
        self.assertEqual(transport._dpapi(protected, decrypt=True), clear)


if __name__ == "__main__":
    unittest.main()
