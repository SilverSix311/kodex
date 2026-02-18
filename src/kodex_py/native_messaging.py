"""Kodex Native Messaging Host — com.kodex.context

Implements Chrome's native messaging protocol (stdio, length-prefixed JSON).

Protocol:
  Chrome → Host : 4-byte little-endian length + UTF-8 JSON bytes
  Host → Chrome : same format

On each message received from the extension:
  1. Parse the JSON context payload
  2. Write/merge it to ~/.kodex/freshdesk_context.json
  3. Respond with {"success": true} or {"success": false, "error": "..."}

Usage (not normally called directly — Chrome launches via native_host.bat):
  python -m kodex_py.native_messaging
"""

from __future__ import annotations

import json
import logging
import os
import struct
import sys
from datetime import datetime
from pathlib import Path

# ── Logging (to file only — stdout is reserved for the native messaging protocol) ──

_LOG_DIR = Path.home() / ".kodex"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(_LOG_DIR / "native_messaging.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("kodex.native_messaging")

# ── Context file ───────────────────────────────────────────────────────────────

CONTEXT_FILE = _LOG_DIR / "freshdesk_context.json"


def _write_context(payload: dict) -> None:
    """Write the incoming context payload to disk.

    Structure:
      - Top-level keys from the latest source (for easy %variable% access)
      - Prefixed keys for source-specific access (e.g., %freshdesk_ticket_number%)
      - _sources dict with full data per source
      - _active_source to know which source populated the top-level keys
    """
    # Load existing data if present
    existing: dict = {}
    if CONTEXT_FILE.exists():
        try:
            existing = json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Could not read existing context file: %s", e)

    source = payload.get("source", "unknown")
    now = datetime.now().isoformat()

    # Ensure _sources dict exists
    if "_sources" not in existing:
        existing["_sources"] = {}

    # Store full payload under source key in _sources
    existing["_sources"][source] = {
        **payload,
        "_saved_at": now,
    }

    # Clear old top-level keys (except metadata and _sources)
    keys_to_remove = [k for k in existing.keys() if not k.startswith("_")]
    for k in keys_to_remove:
        del existing[k]

    # Flatten latest source data to top level (for %ticket_number% etc.)
    for key, value in payload.items():
        if not key.startswith("_"):
            existing[key] = value

    # Also add prefixed keys for all sources (for %freshdesk_ticket_number% etc.)
    for src, src_data in existing["_sources"].items():
        for key, value in src_data.items():
            if not key.startswith("_"):
                existing[f"{src}_{key}"] = value

    existing["_active_source"] = source
    existing["_updated_at"] = now

    # Atomic write via temp file
    tmp = CONTEXT_FILE.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(CONTEXT_FILE)
        log.info("Context written to %s (source=%s, ticket=%s)", CONTEXT_FILE, source, payload.get("ticket_number"))
    except OSError as e:
        log.error("Failed to write context file: %s", e)
        raise


# ── Native messaging I/O ───────────────────────────────────────────────────────

def _read_message(stdin) -> dict | None:
    """Read one length-prefixed JSON message from Chrome.

    Returns the parsed dict, or None on EOF/error.
    """
    # Read 4-byte little-endian length prefix
    raw_len = stdin.read(4)
    if len(raw_len) < 4:
        log.info("stdin closed (EOF on length read)")
        return None

    msg_len = struct.unpack("<I", raw_len)[0]

    if msg_len == 0:
        return {}

    if msg_len > 1024 * 1024:  # Sanity check: max 1 MB
        log.error("Message too large: %d bytes — ignoring", msg_len)
        stdin.read(msg_len)  # Drain
        return None

    raw_msg = stdin.read(msg_len)
    if len(raw_msg) < msg_len:
        log.warning("Short read: expected %d bytes, got %d", msg_len, len(raw_msg))
        return None

    try:
        return json.loads(raw_msg.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        log.error("Failed to decode message: %s", e)
        return None


def _write_message(stdout, payload: dict) -> None:
    """Write one length-prefixed JSON message to Chrome."""
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    length_prefix = struct.pack("<I", len(encoded))
    stdout.write(length_prefix)
    stdout.write(encoded)
    stdout.flush()


# ── Main loop ──────────────────────────────────────────────────────────────────

def run() -> None:
    """Main native messaging event loop.

    Reads messages from Chrome, processes them, and writes responses.
    Exits cleanly when Chrome closes the pipe.
    """
    log.info("Kodex native messaging host started (PID %d)", os.getpid())
    log.info("Context file: %s", CONTEXT_FILE)

    # Use raw binary I/O — critical for native messaging protocol correctness.
    # DO NOT wrap in TextIOWrapper; the 4-byte length prefix is binary.
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer

    while True:
        try:
            message = _read_message(stdin)
        except Exception as e:
            log.error("Unexpected error reading message: %s", e, exc_info=True)
            break

        if message is None:
            # EOF — Chrome closed the connection
            log.info("Chrome closed the connection. Exiting.")
            break

        log.debug("Received message: %s", message)

        # Process the message
        try:
            if not message:
                # Empty ping — just acknowledge
                _write_message(stdout, {"success": True, "pong": True})
                continue

            source = message.get("source", "unknown")
            ticket = message.get("ticket_number")
            log.info("Processing context: source=%s ticket=%s", source, ticket)

            _write_context(message)

            _write_message(stdout, {
                "success": True,
                "source": source,
                "ticket_number": ticket,
                "written_to": str(CONTEXT_FILE),
            })

        except Exception as e:
            log.error("Error processing message: %s", e, exc_info=True)
            try:
                _write_message(stdout, {"success": False, "error": str(e)})
            except Exception:
                pass  # Can't write response — just continue

    log.info("Native messaging host exiting.")


def main() -> None:
    """Entry point for `python -m kodex_py.native_messaging`."""
    try:
        run()
    except KeyboardInterrupt:
        log.info("Interrupted by user.")
    except Exception as e:
        log.critical("Fatal error: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
