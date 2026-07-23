#!/usr/bin/env python3
"""
audit-quiz.py — quality audit for M9 quiz JSON sets.

Four checks:
  1. Answer letter distribution near-even across A/B/C/D
  2. Correct answer must not be the longest option
  3. Absolute language clusters in distractors, not correct answers
  4. No long run of consecutive identical answer letters

CHANGE (2026-07): check 2 now counts only UNIQUELY-longest correct answers.
Previously a correct answer tying another option for longest counted as a
failure. On computational sets — where options are short numerics like
"S$12.50" and "1,500 units" — exact-length ties are frequent and carry no
information, so tie-counting produced large false positives (67% on a set
whose correct answers were on average SHORTER than its distractors). A tie
gives a test-taker nothing to guess on; only a strictly longest correct
answer is a real tell.

Usage: python3 audit-quiz.py <file.json> [more.json ...]
Exit code 0 = all checks pass, 1 = any failure.
"""
import json
import sys

LETTERS = "ABCD"

DIST_TOL_FLOOR = 1.5
DIST_TOL_PCT = 0.075
LONGEST_CAP_PCT = 35.0
RATIO_MIN, RATIO_MAX = 0.85, 1.15
ABS_SHARE_CAP = 25.0
MAX_RUN = 2

ABSOLUTES = [
    "always", "never", "only", "must", "cannot", "can not", "regardless",
    "automatically", "all ", "none ", "every ", "no exception", "guaranteed",
    "entirely", "solely", "without exception", "impossible",
]


def find_absolutes(text):
    t = text.lower()
    return [w for w in ABSOLUTES if w in t]


def longest_run(seq):
    best = cur = 1
    for a, b in zip(seq, seq[1:]):
        cur = cur + 1 if a == b else 1
        best = max(best, cur)
    return best


def audit(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    qs = data["questions"]
    n = len(qs)
    print("=" * 74)
    print(f"AUDIT: {data.get('title', path)}")
    print(f"File:  {path}   ({n} questions, passMark {data.get('passMark')})")
    print("=" * 74)

    failures = []

    errs = []
    ids = set()
    for i, q in enumerate(qs, 1):
        opts = q.get("options", [])
        if len(opts) != 4:
            errs.append(f"Q{i}: {len(opts)} options, expected 4")
        if not (0 <= q.get("correctIndex", -1) <= 3):
            errs.append(f"Q{i}: correctIndex out of range")
        for k in ("id", "chapter", "question", "explanation", "reference"):
            if not q.get(k):
                errs.append(f"Q{i}: missing/empty '{k}'")
        if q.get("id") in ids:
            errs.append(f"Q{i}: duplicate id {q.get('id')}")
        ids.add(q.get("id"))
        if len(set(o.strip().lower() for o in opts)) != len(opts):
            errs.append(f"Q{i}: duplicate option text")

    if errs:
        print(f"\nStructure: {n} questions | FAIL")
        for e in errs:
            print("   ", e)
        failures.append("structure")
    else:
        print(f"\nStructure: {n} questions | OK")

    letters = [LETTERS[q["correctIndex"]] for q in qs]

    counts = {L: letters.count(L) for L in LETTERS}
    even = n / 4
    tol = max(DIST_TOL_FLOOR, DIST_TOL_PCT * n)
    max_dev = max(abs(counts[L] - even) for L in LETTERS)
    ok1 = max_dev <= tol
    print(f"1) Distribution {{'A': {counts['A']}, 'B': {counts['B']}, "
          f"'C': {counts['C']}, 'D': {counts['D']}}} | "
          f"max deviation {max_dev:.1f} -> {'PASS' if ok1 else 'FAIL'}")
    if not ok1:
        print(f"     tolerance {tol:.2f}")
        failures.append("distribution")

    uniquely_longest = []
    ties = 0
    correct_lens, distractor_lens = [], []
    for i, q in enumerate(qs, 1):
        opts, ci = q["options"], q["correctIndex"]
        lens = [len(o) for o in opts]
        correct_lens.append(lens[ci])
        distractor_lens.extend(l for j, l in enumerate(lens) if j != ci)
        if lens[ci] == max(lens):
            if lens.count(max(lens)) == 1:
                uniquely_longest.append(i)
            else:
                ties += 1

    pct = 100.0 * len(uniquely_longest) / n
    avg_c = sum(correct_lens) / len(correct_lens)
    avg_d = sum(distractor_lens) / len(distractor_lens)
    ratio = avg_c / avg_d
    ratio_ok = RATIO_MIN <= ratio <= RATIO_MAX
    ok2 = pct <= LONGEST_CAP_PCT and ratio_ok

    print(f"2) Correct is longest {len(uniquely_longest)}/{n} ({pct:.0f}%) "
          f"-> {'PASS' if pct <= LONGEST_CAP_PCT else 'FAIL'}")
    print(f"     Avg length correct {avg_c:.1f} vs distractor {avg_d:.1f} "
          f"(ratio {ratio:.2f}) -> {'PASS' if ratio_ok else 'FAIL'}")
    if ties:
        print(f"     ({ties} joint-longest ties ignored - no guessable tell)")
    if uniquely_longest:
        print(f"     -> Q{uniquely_longest}")
    if not ok2:
        failures.append("length")

    corr_abs = dist_abs = 0
    flagged = []
    for i, q in enumerate(qs, 1):
        ci = q["correctIndex"]
        for j, o in enumerate(q["options"]):
            hits = find_absolutes(o)
            if not hits:
                continue
            if j == ci:
                corr_abs += 1
                flagged.append(f"Q{i} ({LETTERS[j]}) {hits}: {o[:60]}")
            else:
                dist_abs += 1
    total_abs = corr_abs + dist_abs
    share = (100.0 * corr_abs / total_abs) if total_abs else 0.0
    ok3 = corr_abs == 0 or share <= ABS_SHARE_CAP
    print(f"3) Absolute language: correct {corr_abs} vs distractors {dist_abs} "
          f"-> {'PASS' if ok3 else 'FAIL'}")
    if not ok3:
        for f_ in flagged:
            print("     !", f_)
        failures.append("absolutes")

    run = longest_run(letters)
    ok4 = run <= MAX_RUN
    print(f"4) Sequence {''.join(letters)}")
    print(f"     Longest run {run} -> {'PASS' if ok4 else 'FAIL'}")
    if not ok4:
        failures.append("runs")

    print("\nVERIFY - read every correct answer against the source:")
    for i, q in enumerate(qs, 1):
        ci = q["correctIndex"]
        print(f"  {i:>2}. [{LETTERS[ci]}] {q['options'][ci]}")

    print()
    if failures:
        print(f"FAILURES PRESENT - fix before pushing ({', '.join(failures)})")
    else:
        print("ALL CHECKS PASS")
    print()
    return not failures


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(0 if all(audit(p) for p in sys.argv[1:]) else 1)
