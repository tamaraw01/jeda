# Recorded evidence

This directory contains live model trial records on synthetic inputs. It also contains offline checks that anyone can run without credentials. A recorded execution is different from an independently replicated live experiment.

## What is included

- `initial/` retains the first 12 sessions, source fixtures, final artifacts, and a runner snapshot.
- `corrected/` retains all 12 sessions after the tool-authorization repair. No failed session was selectively removed.
- `tested-SKILL.md` is the exact runtime file used in the corrected trial. Its SHA-256 matches `corrected/plan.json` and the root `SKILL.md`.
- `probe.json` retains the four-request accounting replay. It used an earlier runtime version, v0.2.0, and is not an outcome benchmark for v0.2.1.
- `SHA256SUMS.json` identifies the exported evidence files. Hashes detect changes; they do not authenticate a provider or prove execution by themselves.
- `verify.py` recalculates corrected-trial outcomes from recorded actions and artifacts. It makes no network requests.

The runner snapshots are historical text, not supported network clients. Local endpoint, credential-variable name, and machine-specific skill path have been replaced with explicit placeholders. The original model route alias and provider response label remain in the records for provenance. No credentials or authorization headers are included. The exported records have not been relabeled as a different model.

## Corrected direct trial

The trial ran three tasks, two repetitions, and two arms, totaling 12 sessions. The exact tasks are visible in the first request of each result file. The control arm lacked the Jeda instructions. Within each task pair, tool authorization and starting fixtures matched.

| Task | Jeda | Control |
| --- | ---: | ---: |
| Extract eligible IDs from 160 invoice rows | 2/2 | 1/2 |
| Fix a comparison boundary and run existing tests | 2/2 | 2/2 |
| Extract policy periods and exceptions | 2/2 | 2/2 |
| All required checks | 6/6 | 5/6 |

Jeda made 20 tool calls and transmitted 136,072 aggregate serialized request bytes. Control made 24 tool calls and transmitted 95,587 bytes. Bytes are not tokens or bills. The incomplete control invoice output contains 74 IDs instead of 75 and omits `00158`.

The verifier checks exact artifacts, recorded source text against saved files, tool success, a nonempty final response, and verification after the last write. For code repair it runs the saved tests only after restricting the generated function to a small comparison-only AST. This is not a general arbitrary-code sandbox.

```sh
python3 evidence/verify.py
```

Expected summary fields include `sessions: 12`, `passes: {control: 5, jeda: 6}`, and `usage_eligible: false`. `release: HOLD` refers to the experiment's production/savings decision, not a prohibition on sharing these experimental records.

## First trial and harness correction

The initial runner advertised `run_tests` for all tasks but denied it outside code repair. Each arm made one denied invoice call. All 12 artifacts were correct, while each arm passed 5/6 full session checks. This was a harness defect, not evidence that either instruction set was unsafe.

The corrected trial offered only tools authorized for the task. A later evaluator correction required successful tests after the final code write. The offline verifier applies that requirement to the recorded traces. The corrected-trial outcome remains 6/6 versus 5/6. The historical runner snapshot is not silently rewritten to include that later fix.

## Why there is no token-savings claim

The four-request probe repeated these reports twice per arm:

| Arm | Request bytes | Reported prompt tokens |
| --- | ---: | ---: |
| Control | 9,745 | 16,936 |
| Jeda | 12,124 | 3,189 |

Both arms returned the model label `gpt-6.1-sol`. That label does not prove an identical upstream route or backend revision. Source inspection of the local gateway found provider-field normalization and persistence, not a local prompt estimator in the paths inspected. It did not establish the path used by these requests.

The corrected direct trial also reported aggregate total tokens of 303,650 for Jeda and 47,095 for control. These are unvalidated usage fields. Neither those totals nor the probe inversion support a trustworthy cost ratio. A diagnosis requires routed request/response provenance and reconciliation with provider accounting. No gateway fix is claimed.

## What these records cannot establish

The trial uses a single gateway, a response model label rather than a pinned backend revision, small synthetic fixtures, and two repetitions. It is not a full host-runtime integration test. The review was not blinded. Invoice work used file read/write tools rather than a general computation tool. Replaying persisted outputs does not reproduce live model behavior.

The attempted operating-system sandbox was unavailable. Execution was restricted to a comparison function and existing fixture tests. Do not expand this harness to unrestricted generated code without real isolation.

The evidence does not establish quality equivalence, general superiority, lower cost, cross-host compatibility, or industrial readiness. Future revisions need held-out workloads, independently reviewed artifacts, and trustworthy whole-task accounting.
