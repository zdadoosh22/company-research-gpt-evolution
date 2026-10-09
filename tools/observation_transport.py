"""Optional Telegram transport for observation alerts; no account is connected on import.

Official API: https://core.telegram.org/bots/api (sendMessage, editMessageText,
getUpdates, answerCallbackQuery). Incoming updates are retained by Telegram for
at most 24 hours. Cloud messages are historical snapshots, not fresh approval.

enqueue_* and init_transport do not commit: the caller owns that transaction.
dispatch_outbox/ingest_updates own transactions; call with no unrelated pending
writes. An incoming handler(conn, update) must only change this SQLite database
and stage replies, never perform external side effects. Its changes, dedup marker
and offset commit together. No trading or model calls occur in this module.
"""
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import urllib.error
import urllib.request
import uuid


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never forward credential-bearing Telegram URLs to a redirect target."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class TransportError(Exception):
    """Deliberately redacted transport failure (never raw HTTP errors or URLs)."""

    def __init__(self, code="transport_failed", *, retryable=False,
                 uncertain=False, retry_after=None):
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.uncertain = uncertain
        self.retry_after = retry_after


def _chat_id(value):
    if isinstance(value, bool) or not re.fullmatch(r"[1-9]\d*", str(value)):
        raise ValueError("A positive private Telegram chat ID is required")
    return str(int(value))


class TelegramClient:
    def __init__(self, token, allowed_chat_id, *, timeout=20, opener=None):
        if not isinstance(token, str) or not re.fullmatch(r"\d+:[A-Za-z0-9_-]+", token):
            raise ValueError("Invalid Telegram token format")
        self._token = token
        self.allowed_chat_id = _chat_id(allowed_chat_id)
        self.timeout = timeout
        self._opener = opener or urllib.request.build_opener(_NoRedirect()).open

    def __repr__(self):
        return "TelegramClient(token=<redacted>)"

    def _call(self, method, payload, *, sending=False):
        request = urllib.request.Request(
            "https://api.telegram.org/bot" + self._token + "/" + method,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with self._opener(request, timeout=self.timeout) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError("response limit")
            body = json.loads(raw)
        except urllib.error.HTTPError as exc:
            # An HTTP 429 explicitly rejects the request; ambiguous server/network
            # failures may follow a successful send and must not be blind-retried.
            retry_after = None
            error_body = {}
            try:
                error_body = json.loads(exc.read(10000))
                if not isinstance(error_body, dict):
                    error_body = {}
                if exc.code == 429:
                    retry_after = int(error_body.get("parameters", {}).get("retry_after", 0)) or None
            except Exception:
                pass
            status = exc.code
            exc.close()
            if (method == "editMessageText" and status == 400 and
                    "message is not modified" in str(error_body.get("description", ""))):
                return {"message_id": payload["message_id"]}
            raise TransportError("rate_limited" if status == 429 else "http_failed",
                                 retryable=status == 429 or status >= 500,
                                 uncertain=sending and status >= 500,
                                 retry_after=retry_after) from None
        except Exception:
            raise TransportError("network_or_response_failed", retryable=True,
                                 uncertain=sending) from None
        if not isinstance(body, dict) or body.get("ok") is not True:
            error_code = body.get("error_code") if isinstance(body, dict) else None
            # Editing identical text is already the desired state.
            description = str(body.get("description", "")) if isinstance(body, dict) else ""
            if method == "editMessageText" and "message is not modified" in description:
                return {"message_id": payload["message_id"]}
            parameters = body.get("parameters") if isinstance(body, dict) else None
            retry_after = parameters.get("retry_after") if isinstance(parameters, dict) else None
            raise TransportError("rate_limited" if error_code == 429 else "api_rejected",
                                 retryable=error_code == 429 or (isinstance(error_code, int) and error_code >= 500),
                                 uncertain=sending and (not isinstance(error_code, int) or error_code >= 500),
                                 retry_after=retry_after)
        return body.get("result")

    def send_message(self, text, reply_markup=None):
        payload = {"chat_id": self.allowed_chat_id, "text": text,
                   "disable_web_page_preview": True}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        result = self._call("sendMessage", payload, sending=True)
        if (not isinstance(result, dict) or type(result.get("message_id")) is not int or
                result["message_id"] <= 0):
            raise TransportError("invalid_send_response", uncertain=True)
        return result["message_id"]

    def edit_message(self, message_id, text, reply_markup=None):
        payload = {"chat_id": self.allowed_chat_id, "message_id": int(message_id),
                   "text": text, "disable_web_page_preview": True}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return self._call("editMessageText", payload)

    def get_updates(self, offset=0):
        result = self._call("getUpdates", {"offset": int(offset), "timeout": 0,
                            "allowed_updates": ["message", "callback_query"]})
        if not isinstance(result, list):
            raise TransportError("invalid_update_response", retryable=True)
        return result

    def answer_callback(self, callback_id, text="Recorded; check the latest status before acting"):
        return self._call("answerCallbackQuery", {"callback_query_id": callback_id,
                                                   "text": text, "cache_time": 0})


def _dpapi(data, *, decrypt=False):
    if os.name != "nt":
        raise RuntimeError("Credential protection requires Windows DPAPI")
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if decrypt:
        fn = crypt.CryptUnprotectData
        fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                       ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
        args = (ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target))
    else:
        fn = crypt.CryptProtectData
        fn.argtypes = [ctypes.POINTER(Blob), wintypes.LPCWSTR, ctypes.c_void_p,
                       ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
        args = (ctypes.byref(source), "Company research observation transport", None,
                None, None, 1, ctypes.byref(target))
    fn.restype = wintypes.BOOL
    if not fn(*args):
        raise RuntimeError("Windows credential protection failed")
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        kernel.LocalFree(ctypes.cast(target.pbData, ctypes.c_void_p))


def configure_credentials(secret_path, token, allowed_chat_id):
    """Offline helper: encrypt credentials for this Windows user; no API call.

    Use a separate ignored local-state path, not SQLite/project configuration.
    Do not supply tokens on shell command lines; use a hidden interactive prompt.
    """
    TelegramClient(token, allowed_chat_id)  # validation only
    protected = _dpapi(json.dumps({"token": token, "chat_id": _chat_id(allowed_chat_id)}).encode())
    path = Path(secret_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_bytes(protected)
    os.replace(temp, path)


def load_credentials(secret_path):
    try:
        data = json.loads(_dpapi(Path(secret_path).read_bytes(), decrypt=True))
        return TelegramClient(data["token"], data["chat_id"])
    except Exception:
        raise RuntimeError("Telegram credentials unavailable; configure for this Windows user") from None


def init_transport(conn):
    # Individual statements preserve any enclosing transaction (executescript commits).
    conn.execute("""CREATE TABLE IF NOT EXISTS transport_outbox (
        id TEXT PRIMARY KEY, dedup_key TEXT UNIQUE NOT NULL, operation TEXT NOT NULL,
        payload TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'pending',
        attempts INTEGER NOT NULL DEFAULT 0, next_attempt REAL NOT NULL DEFAULT 0,
        message_id INTEGER, error_code TEXT, created REAL NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS transport_updates (
        update_id INTEGER PRIMARY KEY, payload TEXT NOT NULL, processed REAL NOT NULL)""")
    conn.execute("CREATE TABLE IF NOT EXISTS transport_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")


def _enqueue(conn, operation, payload, dedup_key):
    if not isinstance(dedup_key, str) or not dedup_key:
        raise ValueError("A durable deduplication key is required")
    if not isinstance(payload["text"], str) or not 1 <= len(payload["text"]) <= 4096:
        raise ValueError("Telegram text must contain 1 to 4096 characters")
    encoded = json.dumps(payload, sort_keys=True)
    existing = conn.execute("SELECT id,operation,payload FROM transport_outbox WHERE dedup_key=?", (dedup_key,)).fetchone()
    if existing:
        if existing[1] != operation or json.loads(existing[2]) != payload:
            raise ValueError("Deduplication key already identifies a different notification")
        return existing[0]
    candidate = uuid.uuid4().hex
    conn.execute("INSERT OR IGNORE INTO transport_outbox(id,dedup_key,operation,payload,created) VALUES(?,?,?,?,?)",
                 (candidate, dedup_key, operation, encoded, time.time()))
    saved = conn.execute("SELECT id,operation,payload FROM transport_outbox WHERE dedup_key=?", (dedup_key,)).fetchone()
    if saved[1] != operation or json.loads(saved[2]) != payload:
        raise ValueError("Deduplication key already identifies a different notification")
    return saved[0]


def enqueue_send(conn, text, dedup_key, reply_markup=None):
    return _enqueue(conn, "send", {"text": text, "reply_markup": reply_markup}, dedup_key)


def enqueue_edit(conn, message_id, text, dedup_key, reply_markup=None):
    return _enqueue(conn, "edit", {"message_id": int(message_id), "text": text,
                                  "reply_markup": reply_markup}, dedup_key)


def dispatch_outbox(conn, client, *, now=None, max_items=10, preflight=None):
    """One bounded pass, no sleeping. Sends with uncertain outcomes never repeat.

    Run with a single-process lock owned by the observation engine. On recovery,
    interrupted sends become uncertain; edits can safely retry. Operator reconciles
    uncertain sends explicitly; this module never claims phone delivery or reading.
    Optional preflight(conn, item) is a DB-only check called under the claim
    transaction before network work. False marks the row superseded without an
    attempt. item exposes id, dedup_key, operation, payload and message_id. It
    must not commit or perform external side effects.
    """
    if conn.in_transaction:
        raise RuntimeError("Outbox dispatch requires no pending transaction")
    now = time.time() if now is None else now
    with conn:
        conn.execute("UPDATE transport_outbox SET state='uncertain',error_code='interrupted_send' WHERE state='inflight' AND operation='send'")
        conn.execute("UPDATE transport_outbox SET state=CASE WHEN attempts>=5 THEN 'failed' ELSE 'pending' END WHERE state='inflight' AND operation='edit'")
    outcomes = []
    for _ in range(max_items):
        # Keep one-chat throughput below the provider's 1 message/sec guidance.
        last = conn.execute("SELECT value FROM transport_meta WHERE key='last_attempt'").fetchone()
        if last and now - float(last[0]) < 1:
            break
        row = conn.execute("SELECT id,operation,payload,attempts,dedup_key,message_id FROM transport_outbox WHERE state='pending' AND next_attempt<=? ORDER BY created,id LIMIT 1", (now,)).fetchone()
        if row is None:
            break
        ident, operation, raw, attempts, dedup_key, prior_message_id = row
        conn.execute("BEGIN IMMEDIATE")
        superseded = False
        with conn:
            if preflight and not preflight(conn, {"id": ident, "dedup_key": dedup_key,
                    "operation": operation, "payload": json.loads(raw), "message_id": prior_message_id}):
                conn.execute("UPDATE transport_outbox SET state='superseded' WHERE id=?", (ident,))
                superseded = True
            else:
                conn.execute("UPDATE transport_outbox SET state='inflight',attempts=attempts+1 WHERE id=?", (ident,))
                conn.execute("INSERT OR REPLACE INTO transport_meta VALUES('last_attempt',?)", (str(now),))
        if superseded:
            outcomes.append({"id": ident, "state": "superseded", "message_id": prior_message_id, "error_code": None})
            continue
        payload = {}
        try:
            try:
                decoded = json.loads(raw)
            except (ValueError, TypeError):
                raise TransportError("invalid_outbox_payload") from None
            if operation not in ("send", "edit") or not isinstance(decoded, dict):
                raise TransportError("invalid_outbox_payload")
            payload = decoded
            if operation == "send":
                message_id = client.send_message(payload["text"], payload.get("reply_markup"))
            else:
                client.edit_message(payload["message_id"], payload["text"], payload.get("reply_markup"))
                message_id = payload["message_id"]
            state, code, delay = "sent", None, 0
        except TransportError as exc:
            message_id = payload.get("message_id")
            state = "uncertain" if operation == "send" and exc.uncertain else (
                "pending" if exc.retryable and attempts + 1 < 5 else "failed")
            code = exc.code if exc.code in {"transport_failed", "rate_limited", "http_failed",
                "network_or_response_failed", "api_rejected", "invalid_send_response",
                "invalid_update_response", "invalid_outbox_payload"} else "transport_failed"
            try:
                requested_delay = max(0, int(exc.retry_after or 0))
            except (ValueError, TypeError):
                requested_delay = 0
            delay = max(2 ** (attempts + 1), requested_delay)
        except Exception:
            # A caller-supplied client must not leak credentials through exceptions.
            state = "uncertain" if operation == "send" else "failed"
            message_id, code, delay = payload.get("message_id"), "client_failed", 0
        with conn:
            conn.execute("UPDATE transport_outbox SET state=?,message_id=?,error_code=?,next_attempt=? WHERE id=?",
                         (state, message_id, code, now + delay, ident))
        outcomes.append({"id": ident, "state": state, "message_id": message_id, "error_code": code})
    return outcomes


def ingest_updates(conn, client, handler, *, now=None):
    """Atomic handler/dedup/offset processing; unauthorised chats never reach handler."""
    if conn.in_transaction:
        raise RuntimeError("Incoming update processing requires no pending transaction")
    offset_row = conn.execute("SELECT value FROM transport_meta WHERE key='offset'").fetchone()
    offset = int(offset_row[0]) if offset_row else 0
    updates = client.get_updates(offset)
    if not isinstance(updates, list) or any(not isinstance(update, dict) or
            type(update.get("update_id")) is not int or update["update_id"] < 0 for update in updates):
        raise TransportError("invalid_update_response", retryable=True)
    processed = 0
    callbacks = []
    # sqlite3's context manager does not start a transaction on entry. Establish
    # one before calling a nested Store._atomic handler, so that its savepoint
    # cannot commit ledger effects before the dedup marker and offset.
    conn.execute("BEGIN IMMEDIATE")
    with conn:
        for update in sorted(updates, key=lambda item: item.get("update_id", -1)):
            ident = update.get("update_id")
            if not isinstance(ident, int) or ident < offset:
                continue
            if conn.execute("SELECT 1 FROM transport_updates WHERE update_id=?", (ident,)).fetchone():
                offset = max(offset, ident + 1)
                continue
            callback = update.get("callback_query") or {}
            callback = callback if isinstance(callback, dict) else {}
            message = update.get("message") or callback.get("message") or {}
            message = message if isinstance(message, dict) else {}
            chat = message.get("chat") or {}
            chat = chat if isinstance(chat, dict) else {}
            sender = callback.get("from") if callback else message.get("from")
            sender = sender if isinstance(sender, dict) else {}
            authorized = (chat.get("type") == "private" and
                          str(chat.get("id")) == client.allowed_chat_id and
                          str(sender.get("id")) == client.allowed_chat_id)
            if authorized:
                handler(conn, update)
                processed += 1
                if isinstance(callback.get("id"), str) and callback["id"]:
                    callbacks.append(callback["id"])
            # Do not retain unsolicited external text from unauthorised accounts.
            saved = update if authorized else {"update_id": ident, "ignored": "unauthorized_chat"}
            conn.execute("INSERT INTO transport_updates VALUES(?,?,?)",
                         (ident, json.dumps(saved), time.time() if now is None else now))
            offset = max(offset, ident + 1)
        conn.execute("INSERT OR REPLACE INTO transport_meta VALUES('offset',?)", (str(offset),))
    # A callback answer is an ephemeral UI response, not a durable acknowledgement
    # or trade confirmation. Its failure must not roll back committed commands.
    answer = getattr(client, "answer_callback", None)
    if answer:
        for callback_id in callbacks:
            try:
                answer(callback_id, "Request recorded; read the new reply for current status")
            except Exception:
                pass
    return processed
