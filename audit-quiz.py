#!/usr/bin/env python3
"""
Audit an M9 Quizlet MCQ JSON for the three biases that make sets too easy.
Usage:  python3 audit-quiz.py quizzes/m9/m9-ch7-ilp-set1.json
Exit code 0 = all pass, 1 = at least one FAIL.
Accepts either a bare array of questions or {"title","passMark","questions":[...]}.
"""
import json, sys, collections

L = "ABCD"
ABSOLUTES = ("always", "never", "all ", "none", "only", "must ", "cannot",
             "automatically", "irrespective", "regardless", "whatever",
             "wholly", "any client", "no possibility", "entirely")


def load(path):
    d = json.load(open(path))
    return d["questions"] if isinstance(d, dict) else d


def main(path):
    qs = load(path)
    n = len(qs)
    fails = []

    # --- structure ---
    if not all(len(q["options"]) == 4 for q in qs):
        fails.append("not every question has exactly 4 options")
    if not all(0 <= q["correctIndex"] <= 3 for q in qs):
        fails.append("correctIndex out of range")
    if len({q.get("id") for q in qs}) != n:
        fails.append("duplicate or missing ids")
    if not all(q.get("explanation") and q.get("reference") for q in qs):
        fails.append("missing explanation or reference")
    print(f"Structure: {n} questions"
          f" | {'OK' if not fails else 'ISSUES: ' + '; '.join(fails)}")

    # --- 1. letter distribution ---
    dist = collections.Counter(L[q["correctIndex"]] for q in qs)
    dev = max(abs(dist[c] - n / 4) for c in L)
    ok1 = dev <= max(1.5, n * 0.075)
    print(f"1) Distribution {dict(sorted(dist.items()))} | max deviation "
          f"{dev:.1f} -> {'PASS' if ok1 else 'FAIL'}")

    # --- 2. length bias ---
    longest = sum(1 for q in qs
                  if len(q["options"][q["correctIndex"]])
                  == max(len(o) for o in q["options"]))
    cl = sum(len(q["options"][q["correctIndex"]]) for q in qs) / n
    dl = sum(len(o) for q in qs for i, o in enumerate(q["options"])
             if i != q["correctIndex"]) / (n * 3)
    ok2a = longest / n <= 0.35
    ok2b = 0.85 <= cl / dl <= 1.15
    print(f"2) Correct is longest {longest}/{n} ({longest/n*100:.0f}%) "
          f"-> {'PASS' if ok2a else 'FAIL'}")
    print(f"   Avg length correct {cl:.1f} vs distractor {dl:.1f} "
          f"(ratio {cl/dl:.2f}) -> {'PASS' if ok2b else 'FAIL'}")

    # --- 3. obviousness: absolutes should sit in distractors ---
    ac = sum(1 for q in qs
             if any(w in q["options"][q["correctIndex"]].lower() for w in ABSOLUTES))
    ad = sum(1 for q in qs for i, o in enumerate(q["options"])
             if i != q["correctIndex"] and any(w in o.lower() for w in ABSOLUTES))
    ok3 = ac < ad
    print(f"3) Absolute language: correct {ac} vs distractors {ad} "
          f"-> {'PASS' if ok3 else 'FAIL'}")

    # --- 4. no long runs of the same letter ---
    seq = "".join(L[q["correctIndex"]] for q in qs)
    run = mx = 1
    for a, b in zip(seq, seq[1:]):
        run = run + 1 if a == b else 1
        mx = max(mx, run)
    ok4 = mx <= 2
    print(f"4) Sequence {seq}")
    print(f"   Longest run {mx} -> {'PASS' if ok4 else 'FAIL'}")

    allok = not fails and all([ok1, ok2a, ok2b, ok3, ok4])
    print("\n" + ("ALL CHECKS PASS" if allok else "FAILURES PRESENT — fix before pushing"))
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "quiz.json"))
