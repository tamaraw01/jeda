# Jeda

Keep the context. Stop repeating the work.

Jeda is a small instruction skill for agents doing multi-step tasks. Before another search, read, or retry, the agent checks what evidence is actually missing. Valid evidence can be reused. Changed requirements, stale sources, and unverified writes still need work.

**Experimental, v0.2.1. Token savings are not established.** The [108-session token trial](evidence/token-trial/README.md) found higher recorded gateway token totals for both Jeda variants, with unequal completion rates. Three timed-out requests have unknown usage. Do not install Jeda on the assumption that it saves tokens or cost.

[Read the skill](SKILL.md) · [Inspect the evidence](evidence/README.md) · [Evaluation protocol](EVALUATION.md) · [Security](SECURITY.md)

## What changes in a task

| Situation | Expected behavior |
| --- | --- |
| Reformat verified invoice data as JSON | Reuse the data when scope and freshness still match. |
| Change the overdue threshold | Recalculate from the complete original data. |
| Ask whether payment arrived today | Retrieve current evidence. |
| Request an exact quotation | Read the original if available context lacks the exact words. |
| Process every record | Cover the entire population, including exceptions and leading-zero IDs. |
| Finish a code edit | Run the required checks after the last edit. |
| Receive an uncertain write result | Inspect state before retrying a potentially duplicate action. |

[Worked examples](examples/decisions.md) explain where reuse stops being valid. They are illustrations, not measured results.

## The procedure

1. Identify the missing fact and what a new call could change.
2. Reuse evidence only when question, source version, scope, permissions, and freshness match.
3. Read a complete relevant unit. Expand when definitions or exceptions are missing.
4. Batch independent reads. Keep dependent actions ordered.
5. Verify the requested deliverable, then stop.

The runtime file is deliberately small. It does not prune history, replace originals with summaries, change model settings, or impose a shorter answer. It asks the agent to retain requested depth and uncertainty. These are instructions, not a guarantee of lossless understanding.

## Recorded results

Three synthetic file tasks, two repetitions, two arms. Live requests used one gateway with the response label `gpt-6.1-sol`. The backend revision was not independently pinned. The runs were not blinded or an industrial benchmark.

| Corrected trial | Jeda | Control |
| --- | ---: | ---: |
| Sessions passing all checks | 6/6 | 5/6 |
| Tool calls | 20 | 24 |
| Aggregate serialized request bytes | 136,072 | 95,587 |

One control output omitted invoice `00158`. The independent verifier detects it. The first trial had a tool-authorization defect in the harness and is retained separately, including failures. The accounting probe reproduced inconsistent-looking usage reports, but does not identify their cause. Raw usage is not billing proof.

These results justify inspection and more testing. They do not establish general quality superiority, lower cost, or production readiness. [Evidence and limitations](evidence/README.md) include recorded traces, fixtures, the exact tested skill, and offline verification.

## Try the skill

Open [SKILL.md](SKILL.md) and review it. Copy that file into your host's documented local skill directory, or supply its body as task instructions. Start a separate session. Do not rewrite a running system prompt or tool inventory.

Only `SKILL.md` belongs in the routine agent context. The evidence, examples, and evaluator are for humans and development. The skill needs no service, API key, runtime dependency, or telemetry. Your host retains control over its own data handling and automatic compaction. Automatic discovery and installation across hosts have not been tested.

Remove the file and start a fresh session to stop loading it. For a one-line request, loading another procedure may cost more than it saves.

## Check the package

Python 3.10 or newer. Standard library only. These commands make no network or model calls.

```sh
python3 -m unittest discover -s tests -v
python3 evidence/verify.py
python3 score.py examples/synthetic.csv --cases examples/cases.json --repeats 1
```

The CSV command is an invented bookkeeping example, not a model benchmark. Its totals are 110 control tokens and 100 Jeda tokens. The evaluator trusts supplied quality labels and usage totals. `eligible: true` is a descriptive arithmetic result, not permission to advertise savings.

## Use in a team

Keep normal authorization, source provenance, freshness checks, audit logs, and review. Never reuse evidence across tenants or permission boundaries. Use reversible tasks for a canary and retain the control path. [EVALUATION.md](EVALUATION.md) defines paired trials, quality review, full-task accounting, and rollout limits.

## Contribute

Submit a minimal task where an agent repeats unnecessary work or skips a necessary check. Include the expected result, a redacted trace, model and host information, and the skill revision. Preserve failed attempts. A changed skill needs held-out evaluation rather than another run tailored to the same fixtures.

Do not submit private conversations, credentials, or production logs. No percentage savings claim belongs in a contribution without comparable usage records and artifact review.

Jeda means a pause in Indonesian. The pause is a decision about whether another action is needed.
