# Token trial, 2026-11-20

Jeda did not demonstrate token savings in this trial. Do not install it on the
assumption that it reduces tokens or cost.

## Results

Each split contains six synthetic cases, three repeats and three arms. That is
54 sessions per split, 108 in the frozen evaluation. Requests used
`ag/gemini-3.8-flash-low`; every recorded response identified
`gemini-3.8-flash-n`. We did not mix these results with Sonnet probes.

| Split | Arm | Recorded tokens | Quality passes | Recorded calls |
|---|---|---:|---:|---:|
| Development | Control | 337,628 | 16/18 | 85 |
| Development | Current skill | 367,623 | 16/18 | 83 |
| Development | Minimal candidate | 364,292 | 18/18 | 90 |
| Held-out | Control | 241,386 | 8/18 | 62 |
| Held-out | Current skill | 380,741 | 17/18 | 87 |
| Held-out | Minimal candidate | 311,777 | 14/18 | 78 |

These are sums of returned gateway `prompt_tokens + completion_tokens`, not
bytes, independently tokenized prompts or reconciled billing. Two development
sessions and one held-out session timed out. Their unanswered requests have
unknown usage. Consequently, even the recorded totals do not account for every
possibly billable request.

On development tasks the current skill used 8.88% more recorded tokens; the
minimal candidate used 7.90% more. Held-out differences were +57.73% and +29.16%.
Those differences are not comparisons at equal quality. Control often stopped
without producing an artifact. Its lower token count is not an efficiency win.
Conversely, better completion rates do not establish token savings for Jeda.

Exploratory case-cluster bootstrap intervals are in each `audit.json`. They use
only six clusters. They are not population-level or industrial guarantees.

## What was fixed before the frozen runs

The first development run had 54 sessions. It exposed rejected extra tool
arguments and premature empty responses. Its quality rule also rejected
recovered tool mistakes. Source files changed while that run was in progress,
so it is retained in `invalidated-dev/` but excluded from comparisons.

For the frozen evaluation, a recovered tool error remains in the log and its
tokens remain counted. It does not fail final quality if the artifact, source
requirements and read-back checks pass. An unauthorized source attempt still
fails. Source IDs are listed for the model, stale sources must be read before
the final write, and tenant Y tasks reject tenant X access.

No candidate tuning used held-out responses. We launched development and
held-out inference concurrently after freezing the same implementation. Each
runner allowed two concurrent requests, so the two processes together allowed
four. This is not a sequential development-then-validation optimization study.
The archived history is synthetic irrelevant text, identical across arms. This
experiment does not establish preservation of arbitrary real conversation facts.

## Audit without an API key

From the repository root:

```sh
python3 evidence/token-trial/audit.py evidence/token-trial/dev-fixed evidence/token-trial/heldout
python3 -m unittest discover -s benchmarks -v
```

The audit verifies frozen source hashes, the complete 54-session matrix per
split, unique sessions, response/request hashes and byte lengths. It replays
tool calls from raw responses against virtual sources, compares recorded actions,
and recomputes artifact quality and token sums. It does not trust saved quality
flags or session token totals. Frozen source files are under each split's
`frozen/` directory.

Fixtures and outputs contain synthetic data. Authorization headers and API keys
are not recorded. `calibration/` retains the initial route probes, including
failed requests. Identical-input probes checked repeatability, not billing.
A few points consistent with a byte/token linear relationship do not prove a
universal formula. Earlier chat wording overstated that inference.

## Decision

Neither variant passes the savings claim. No production release or automatic
installation follows this experiment. The candidate stays experimental and does
not replace `SKILL.md`.

The next useful experiment needs reliable tool completion, independently checked
accounting, and a baseline that finishes the same work. Repair costs must be
counted through comparable completion; selective successful-session averages
would conceal failures. A runtime mechanism should be considered only if it
removes repeated work without deleting context and beats its own overhead.
Repeating this prompt-only benchmark until a favorable result appears would
not provide that evidence.
