---
description: Add a new M9 quiz set JSON to the Quizlet app, register it in manifest.json, audit it, and push
allowed-tools: Bash(git *), Bash(python3 *), Bash(mv *), Bash(ls *), Read, Edit, Glob
---

# Add a quiz set

Deploy a new quiz set to the Interactive Quizlet app.

Arguments: `$ARGUMENTS`

Expected form: `<filename.json> <chapter-number> "<Set title>"`
Example: `/addquiz m9-ch7-ilp-set2.json 7 "Chapter 7 · ILPs · Set 2 (30Q)"`

If any argument is missing, ask me for it before doing anything. Do not guess
a title, a chapter number, or a filename.

## Steps

1. **Locate the file.** Look for the named JSON in `~/Downloads/`. If it is not
   there, check the repo root. If it is in neither place, stop and tell me.

2. **Validate it before moving anything.** Confirm it parses as JSON and that
   every question has exactly 4 options, a `correctIndex` in the range 0–3, and
   a non-empty `explanation` and `reference`. If any check fails, stop and show
   me which question is at fault. Do not move or stage a malformed file.

3. **Move it** into `quizzes/m9/`.

4. **Register it in `manifest.json`.** Insert as the FIRST entry of the M9
   `sets` array, so newest appears first:

   ```json
   {
     "id": "<filename without .json>",
     "title": "<the title I gave you>",
     "file": "quizzes/m9/<filename>",
     "group": "<see mapping below>",
     "detail": "",
     "maxChapter": <chapter number>
   }
   ```

   `group` must exactly match one of the groups in the M9 `chapterMap`.
   Map from the chapter number:
   - Ch 1–3 → `Foundations`
   - Ch 4–6 → `Traditional products`
   - Ch 7–9 → `ILPs`
   - Ch 10 → `Annuities and CPF`
   - Ch 11–14 → `Policy lifecycles`

   A set spanning several groups takes a combined label, matching the existing
   convention (e.g. `Foundations + Traditional products`).

   Leave `detail` empty unless the title lacks information the row needs —
   use `Hard`, `Drill` or `Mega` only when the title does not already say it.
   Do not repeat in `detail` what the title already states.

5. **Check the id is unique** against the existing sets. If it collides, stop
   and tell me rather than overwriting.

6. **Verify.** Run both, and require both to pass:
   ```
   python3 -c "import json; json.load(open('manifest.json')); print('manifest OK')"
   python3 audit-quiz.py quizzes/m9/<filename>
   ```
   `audit-quiz.py` checks answer-letter distribution, length bias in the correct
   option, and whether absolute language clusters in the distractors. If it
   reports any FAIL, stop and show me the output. Do not push a failing set —
   the questions need rebalancing first, which happens back in the chat, not here.

   If `audit-quiz.py` is not in the repo root, say so and carry on with the
   manifest check alone.

7. **Show me the manifest diff** and wait for my go-ahead.

8. **Commit and push**, naming files explicitly rather than using `git add .`,
   so unrelated untracked files are not swept in:
   ```
   git add quizzes/m9/<filename> manifest.json
   git commit -m "add <title>"
   git push
   ```

9. Confirm the push succeeded and remind me the live site is
   https://iceomort.github.io/m9quizlet/ and takes a minute or so to rebuild.
