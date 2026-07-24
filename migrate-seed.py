#!/usr/bin/env python3
"""One-off migration: bulk-insert seed-results.json into the Supabase
`attempts` table, then it can be deleted (separately, not by this script).

Reads seed-results.json, validates it's a flat array of _version 2
cmfas-quiz-attempt objects, and inserts each one as {"attempt": <object>}
via the Supabase REST API (PostgREST) in batches of 100, preserving order.
Does not read, delete, or modify seed-results.json in any way beyond
parsing it in memory.
"""
import json
import subprocess
import sys
import tempfile
import os

# Same project URL and publishable (anon) key as supabase-client.js.
SUPABASE_URL = "https://uvipjhiuxrihrdyohrtc.supabase.co"
SUPABASE_ANON_KEY = "sb_publishable_oukcLGNC7CyZY3M_mOytuw_7Dtiy7JK"

SEED_FILE = "seed-results.json"
BATCH_SIZE = 100
REST_ENDPOINT = SUPABASE_URL.rstrip("/") + "/rest/v1/attempts"


def load_and_validate(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        sys.exit(f"error: {path} does not contain a JSON array")

    valid, invalid = [], []
    for i, rec in enumerate(data):
        if (
            isinstance(rec, dict)
            and rec.get("_type") == "cmfas-quiz-attempt"
            and rec.get("_version") == 2
        ):
            valid.append(rec)
        else:
            invalid.append(i)
    return data, valid, invalid


def insert_batch(batch):
    # Shells out to curl (rather than urllib) because this machine's Python
    # lacks a usable CA bundle for TLS verification; curl uses the system
    # trust store and works fine.
    payload = json.dumps([{"attempt": rec} for rec in batch])
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write(payload)
        payload_path = f.name
    try:
        result = subprocess.run(
            [
                "curl", "-s", "-o", "/dev/stderr", "-w", "%{http_code}",
                "-X", "POST", REST_ENDPOINT,
                "-H", f"apikey: {SUPABASE_ANON_KEY}",
                "-H", f"Authorization: Bearer {SUPABASE_ANON_KEY}",
                "-H", "Content-Type: application/json",
                "-H", "Prefer: return=minimal",
                "--data-binary", f"@{payload_path}",
            ],
            capture_output=True, text=True,
        )
    finally:
        os.unlink(payload_path)

    status = result.stdout.strip()
    if status.startswith("2"):
        return None
    return f"HTTP {status}: {result.stderr.strip()}"


def main():
    data, valid, invalid = load_and_validate(SEED_FILE)
    print(f"Read:    {len(data)} record(s) from {SEED_FILE}")
    if invalid:
        print(f"Skipped {len(invalid)} record(s) that aren't _version 2 cmfas-quiz-attempt objects: {invalid}")

    inserted = 0
    failures = []
    for start in range(0, len(valid), BATCH_SIZE):
        batch = valid[start:start + BATCH_SIZE]
        error = insert_batch(batch)
        if error:
            failures.append({"batch_start_index": start, "batch_size": len(batch), "error": error})
        else:
            inserted += len(batch)

    print(f"Inserted: {inserted}")
    if failures:
        print(f"Failures: {len(failures)}")
        for f in failures:
            print(f"  - batch starting at index {f['batch_start_index']} (size {f['batch_size']}): {f['error']}")
    else:
        print("Failures: 0")


if __name__ == "__main__":
    main()
