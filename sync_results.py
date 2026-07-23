#!/usr/bin/env python3
"""Merge a quiz-results export into seed-results.json additively.

Called by sync-results.sh. Not meant to be run standalone, but takes
plain --seed/--export/--dry-run flags so it can be if needed.
"""
import argparse
import json
import sys
from datetime import datetime

ATTEMPT_TYPE = "cmfas-quiz-attempt"


def parse_time_key(date_str, time_str):
    try:
        return datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return datetime.min


def dedup_key(rec):
    return (rec.get("tag"), rec.get("date"), rec.get("timeOfDay"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", required=True)
    ap.add_argument("--export", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(args.seed, encoding="utf-8") as f:
        seed = json.load(f)
    if not isinstance(seed, list):
        sys.exit(f"error: {args.seed} does not contain a JSON array")

    with open(args.export, encoding="utf-8") as f:
        export_data = json.load(f)
    export_records = export_data if isinstance(export_data, list) else [export_data]

    merged = {}
    skipped_wrong_type = 0

    for rec in seed:
        if rec.get("_type") != ATTEMPT_TYPE:
            skipped_wrong_type += 1
            continue
        merged[dedup_key(rec)] = rec

    starting_total = len(merged)
    added = 0
    duplicates = 0

    for rec in export_records:
        if rec.get("_type") != ATTEMPT_TYPE:
            skipped_wrong_type += 1
            continue
        key = dedup_key(rec)
        if key in merged:
            duplicates += 1
            continue
        merged[key] = rec
        added += 1

    result = sorted(
        merged.values(),
        key=lambda r: parse_time_key(r.get("date"), r.get("timeOfDay")),
        reverse=True,
    )

    print(f"Added:               {added}")
    print(f"Duplicates skipped:  {duplicates}")
    if skipped_wrong_type:
        print(f"Wrong _type skipped: {skipped_wrong_type}")
    print(f"New total:           {len(result)} (was {starting_total})")

    if args.dry_run:
        print("Dry run — seed-results.json not written.")
    else:
        with open(args.seed, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Wrote {args.seed}")

    # Machine-readable line for the calling shell script.
    print(f"SUMMARY added={added} duplicates={duplicates} total={len(result)}")


if __name__ == "__main__":
    main()
